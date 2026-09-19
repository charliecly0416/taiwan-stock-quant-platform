from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Protocol

from .types import WorkflowError, validate_asof


class ArtifactError(WorkflowError):
    pass


@dataclass(frozen=True)
class ArtifactRef:
    adapter_id: str
    artifact_type: str
    model_id: str
    asof: str
    status: str
    run_id: str
    path: str
    manifest_path: str
    manifest_sha256: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        required = {
            "adapter_id": self.adapter_id,
            "artifact_type": self.artifact_type,
            "model_id": self.model_id,
            "status": self.status,
            "run_id": self.run_id,
            "path": self.path,
            "manifest_path": self.manifest_path,
        }
        missing = sorted(
            key for key, value in required.items() if not str(value).strip()
        )
        if missing:
            raise ArtifactError(
                f"artifact reference fields are required: {', '.join(missing)}"
            )
        validate_asof(self.asof)
        if not re.fullmatch(r"[0-9a-fA-F]{64}", self.manifest_sha256):
            raise ArtifactError(
                "artifact manifest_sha256 must contain 64 hexadecimal characters"
            )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ArtifactAdapter(Protocol):
    adapter_id: str

    def query(
        self,
        *,
        artifact_type: str | None,
        model_id: str | None,
        asof: str | None,
        status: str | None,
    ) -> list[ArtifactRef]: ...


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class ArtifactResolver:
    def __init__(self, repo_root: Path) -> None:
        self.repo_root = Path(repo_root).resolve()
        self._adapters: dict[str, ArtifactAdapter] = {}

    def register(self, adapter: ArtifactAdapter) -> None:
        adapter_id = str(adapter.adapter_id)
        if adapter_id in self._adapters:
            raise ArtifactError(f"duplicate artifact adapter: {adapter_id}")
        self._adapters[adapter_id] = adapter

    def resolve_path(self, raw_path: str) -> Path:
        candidate = Path(raw_path)
        resolved = (
            candidate if candidate.is_absolute() else self.repo_root / candidate
        ).resolve()
        try:
            resolved.relative_to(self.repo_root)
        except ValueError as exc:
            raise ArtifactError(
                f"artifact path escapes repository: {raw_path}"
            ) from exc
        return resolved

    def query(
        self,
        *,
        artifact_type: str | None = None,
        model_id: str | None = None,
        asof: str | None = None,
        status: str | None = None,
    ) -> list[ArtifactRef]:
        if asof is not None:
            validate_asof(asof)
        refs: list[ArtifactRef] = []
        for adapter_id in sorted(self._adapters):
            adapter_refs = self._adapters[adapter_id].query(
                artifact_type=artifact_type,
                model_id=model_id,
                asof=asof,
                status=status,
            )
            for ref in adapter_refs:
                self._validate_ref(ref)
                filters = {
                    "artifact_type": artifact_type,
                    "model_id": model_id,
                    "asof": asof,
                    "status": status,
                }
                if any(
                    value is not None and getattr(ref, key) != value
                    for key, value in filters.items()
                ):
                    raise ArtifactError(
                        f"artifact adapter ignored query filters: {adapter_id}"
                    )
                refs.append(ref)
        return sorted(
            refs,
            key=lambda item: (
                item.asof,
                item.model_id,
                item.artifact_type,
                item.run_id,
            ),
        )

    def _validate_ref(self, ref: ArtifactRef) -> None:
        if ref.adapter_id not in self._adapters:
            raise ArtifactError(
                f"unregistered adapter in artifact reference: {ref.adapter_id}"
            )
        artifact_path = self.resolve_path(ref.path)
        manifest_path = self.resolve_path(ref.manifest_path)
        if not artifact_path.exists():
            raise ArtifactError(f"artifact path does not exist: {ref.path}")
        if not manifest_path.is_file():
            raise ArtifactError(
                f"artifact manifest does not exist: {ref.manifest_path}"
            )
        try:
            manifest_path.relative_to(
                artifact_path if artifact_path.is_dir() else artifact_path.parent
            )
        except ValueError as exc:
            raise ArtifactError(
                "artifact manifest is outside the artifact path"
            ) from exc
        if (
            len(ref.manifest_sha256) != 64
            or _sha256(manifest_path) != ref.manifest_sha256.lower()
        ):
            raise ArtifactError(f"manifest checksum mismatch: {ref.manifest_path}")
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ArtifactError(
                f"invalid artifact manifest: {ref.manifest_path}"
            ) from exc
        if not isinstance(manifest, dict):
            raise ArtifactError(
                f"artifact manifest must be an object: {ref.manifest_path}"
            )
        expected = {
            "artifact_type": ref.artifact_type,
            "model_id": ref.model_id,
            "asof": ref.asof,
            "status": ref.status,
            "run_id": ref.run_id,
        }
        for key, value in expected.items():
            if key not in manifest:
                raise ArtifactError(
                    f"manifest identity field missing for {key}: {ref.manifest_path}"
                )
            if str(manifest[key]) != value:
                raise ArtifactError(
                    f"manifest identity mismatch for {key}: {ref.manifest_path}"
                )


class ResearchHistoryAdapter:
    adapter_id = "research_data_history.v1"

    def __init__(self, repo_root: Path, index_path: Path | None = None) -> None:
        self.repo_root = Path(repo_root).resolve()
        candidate = Path(
            index_path
            or self.repo_root / "data_tw/catalog/research_data_history/index.json"
        )
        self.index_path = (
            candidate if candidate.is_absolute() else self.repo_root / candidate
        ).resolve()
        try:
            self.index_path.relative_to(self.repo_root)
        except ValueError as exc:
            raise ArtifactError(
                f"research history index escapes repository: {candidate}"
            ) from exc

    def _load(self) -> dict[str, Any]:
        try:
            payload = json.loads(self.index_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ArtifactError(
                f"invalid research history index: {self.index_path}"
            ) from exc
        if (
            not isinstance(payload, dict)
            or payload.get("schema_version") != "tw.research_data_history.index.v1"
            or not isinstance(payload.get("days"), dict)
        ):
            raise ArtifactError(
                f"unsupported research history index: {self.index_path}"
            )
        return payload

    @staticmethod
    def _matches(ref: ArtifactRef, filters: dict[str, str | None]) -> bool:
        return all(
            value is None or getattr(ref, key) == value
            for key, value in filters.items()
        )

    def _model_a_refs(self, day_asof: str, day: dict[str, Any]) -> list[ArtifactRef]:
        model_a = day.get("model_a")
        if not isinstance(model_a, dict):
            return []
        if model_a.get("asof") != day_asof or model_a.get("status") != "READY":
            raise ArtifactError(f"invalid Model A day identity: {day_asof}")
        refs: list[ArtifactRef] = []
        for key in ("inference_input", "signal"):
            item = model_a.get(key)
            if not isinstance(item, dict):
                continue
            files = item.get("files") if isinstance(item.get("files"), dict) else {}
            manifest_record = files.get("manifest.json")
            if not isinstance(manifest_record, dict):
                raise ArtifactError(
                    f"manifest record missing for {day_asof} model_a.{key}"
                )
            refs.append(
                ArtifactRef(
                    adapter_id=self.adapter_id,
                    artifact_type=str(item.get("artifact_type") or ""),
                    model_id=str(model_a.get("model_id") or ""),
                    asof=str(model_a.get("asof") or day_asof),
                    status=str(model_a.get("status") or ""),
                    run_id=str(item.get("run_id") or ""),
                    path=str(item.get("path") or ""),
                    manifest_path=str(manifest_record.get("path") or ""),
                    manifest_sha256=str(manifest_record.get("sha256") or ""),
                    metadata={
                        "history_day_status": str(day.get("status") or ""),
                        "history_slot": key,
                    },
                )
            )
        return refs

    def query(
        self,
        *,
        artifact_type: str | None,
        model_id: str | None,
        asof: str | None,
        status: str | None,
    ) -> list[ArtifactRef]:
        payload = self._load()
        filters = {
            "artifact_type": artifact_type,
            "model_id": model_id,
            "asof": asof,
            "status": status,
        }
        result: list[ArtifactRef] = []
        for day_asof, raw_day in sorted(payload["days"].items()):
            validate_asof(str(day_asof))
            if not isinstance(raw_day, dict) or raw_day.get("asof") != day_asof:
                raise ArtifactError(f"invalid research history day entry: {day_asof}")
            if raw_day.get("status") not in {
                "READY_MODELA_ONLY",
                "READY_MODELA_MODELB",
            }:
                raise ArtifactError(f"invalid research history day status: {day_asof}")
            # Model B history is a multi-file research bundle whose manifest does
            # not yet expose the standard run_id identity required by ArtifactRef.
            # A dedicated adapter will onboard that bundle without weakening the
            # generic manifest checks used for Model A artifacts.
            refs = self._model_a_refs(day_asof, raw_day)
            result.extend(ref for ref in refs if self._matches(ref, filters))
        return result
