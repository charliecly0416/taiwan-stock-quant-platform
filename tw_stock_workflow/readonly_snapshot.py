from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from collections.abc import Callable
from typing import Any

import yaml

from .artifacts import ArtifactError, ArtifactRef, ArtifactResolver
from .modules import ModuleBlocked
from .types import ExecutionContext, WorkflowError, validate_asof


ARTIFACT_TYPE = "ReadonlyStrategySnapshot"
OBSERVATION_STATUS = "VALIDATED_READONLY"
PUBLISH_ROOT = Path("data_tw/artifacts/publish/readonly_strategy_snapshot")
SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
PATH_SEGMENT_PATTERN = re.compile(r"[A-Za-z0-9._-]+")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class ReadonlyStrategySnapshotAdapter:
    adapter_id = "readonly_strategy_snapshot.v1"

    def __init__(
        self,
        repo_root: Path,
        *,
        product_registry_path: Path | None = None,
        baseline_descriptor_path: Path | None = None,
    ) -> None:
        self.repo_root = Path(repo_root).resolve()
        self._resolver = ArtifactResolver(self.repo_root)
        self.product_registry_path = self._regular_repo_file(
            product_registry_path or Path("configs/tw_product_artifact_registry.yaml"),
            label="product artifact registry",
        )
        self.baseline_descriptor_path = self._regular_repo_file(
            baseline_descriptor_path or Path("configs/active_baseline_descriptor.yaml"),
            label="active baseline descriptor",
        )
        self.publish_root = (self.repo_root / PUBLISH_ROOT).resolve()

    def _relative(self, path: Path) -> str:
        return str(path.resolve().relative_to(self.repo_root))

    def _regular_repo_file(self, raw_path: str | Path, *, label: str) -> Path:
        raw = Path(raw_path)
        candidate = raw if raw.is_absolute() else self.repo_root / raw
        if candidate.is_symlink():
            raise ArtifactError(f"{label} may not be a symlink: {raw_path}")
        try:
            resolved = candidate.resolve(strict=True)
            resolved.relative_to(self.repo_root)
        except (OSError, ValueError) as exc:
            raise ArtifactError(f"{label} is outside the repository: {raw_path}") from exc
        if not resolved.is_file():
            raise ArtifactError(f"{label} is not a regular file: {raw_path}")
        if not raw.is_absolute() and str(resolved.relative_to(self.repo_root)) != str(raw):
            raise ArtifactError(f"{label} path is not canonical: {raw_path}")
        return resolved

    def _readonly_file(self, raw_path: str | Path, *, label: str) -> Path:
        path = self._regular_repo_file(raw_path, label=label)
        try:
            path.relative_to(self.publish_root)
        except ValueError as exc:
            raise ArtifactError(f"{label} is outside the readonly snapshot root") from exc
        return path

    @staticmethod
    def _load_json(path: Path, *, label: str) -> dict[str, Any]:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ArtifactError(f"invalid {label}: {path}") from exc
        if not isinstance(payload, dict):
            raise ArtifactError(f"{label} must be an object: {path}")
        return payload

    @staticmethod
    def _load_yaml(path: Path, *, label: str) -> dict[str, Any]:
        try:
            payload = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as exc:
            raise ArtifactError(f"invalid {label}: {path}") from exc
        if not isinstance(payload, dict):
            raise ArtifactError(f"{label} must be an object: {path}")
        return payload

    def _file_record(self, path: Path) -> dict[str, Any]:
        return {
            "path": self._relative(path),
            "size_bytes": path.stat().st_size,
            "sha256": _sha256(path),
        }

    def _registry_latest(self) -> tuple[Path, dict[str, Any]]:
        registry = self._load_yaml(
            self.product_registry_path, label="product artifact registry"
        )
        safety = registry.get("safety")
        required_safety = {
            "no_training_in_product_context",
            "no_provider_publish",
            "no_accepted_latest_switch",
            "no_monitor_write",
            "no_broker_order",
        }
        if (
            registry.get("schema_version") != "tw_product_artifact_registry_v1"
            or registry.get("readonly_only") is not True
            or not isinstance(safety, dict)
            or any(type(safety.get(key)) is not bool or safety[key] is not True for key in required_safety)
        ):
            raise ArtifactError("product artifact registry safety contract is invalid")
        artifacts = registry.get("artifacts")
        if not isinstance(artifacts, dict):
            raise ArtifactError("product artifact registry artifacts are missing")
        latest = self._readonly_file(
            artifacts.get("readonly_strategy_latest", ""),
            label="readonly snapshot latest pointer",
        )
        return latest, registry

    def _baseline_model_id(self) -> tuple[str, dict[str, Any]]:
        descriptor = self._load_yaml(
            self.baseline_descriptor_path, label="active baseline descriptor"
        )
        active = descriptor.get("active_baseline")
        model_a = active.get("model_a") if isinstance(active, dict) else None
        if (
            descriptor.get("schema_version") != "arch1.active_baseline_descriptor.v1"
            or descriptor.get("readonly_only") is not True
            or descriptor.get("simulation_only") is not True
            or not isinstance(active, dict)
            or active.get("status") != "MODEL_A_ONLY"
            or active.get("model_b") is not None
            or not isinstance(model_a, dict)
            or not str(model_a.get("model_id") or "")
        ):
            raise ArtifactError("active baseline is not the Model A readonly baseline")
        return str(model_a["model_id"]), descriptor

    def _checksum_files(
        self, manifest_path: Path, manifest: dict[str, Any]
    ) -> tuple[Path, dict[str, dict[str, Any]]]:
        checksum_path = self._readonly_file(
            manifest_path.parent / str(manifest.get("checksum_manifest") or ""),
            label="readonly snapshot checksum manifest",
        )
        payload = self._load_json(checksum_path, label="snapshot checksum manifest")
        if payload.get("artifact_type") != "readonly_strategy_snapshot_checksum_manifest":
            raise ArtifactError("unexpected readonly snapshot checksum contract")
        raw_files = payload.get("files")
        if isinstance(raw_files, dict):
            entries = [
                {"path": str(name), "sha256": digest}
                for name, digest in raw_files.items()
            ]
        elif isinstance(raw_files, list):
            entries = raw_files
        else:
            raise ArtifactError("readonly snapshot checksum files are invalid")
        records: dict[str, dict[str, Any]] = {}
        for item in entries:
            if not isinstance(item, dict):
                raise ArtifactError("readonly snapshot checksum entry is invalid")
            raw_path = str(item.get("path") or "")
            declared = str(item.get("sha256") or "")
            if not raw_path or SHA256_PATTERN.fullmatch(declared) is None:
                raise ArtifactError("readonly snapshot checksum identity is invalid")
            candidate = Path(raw_path)
            path = self._readonly_file(
                candidate if candidate.is_absolute() or raw_path.startswith("data_tw/") else manifest_path.parent / candidate,
                label="readonly snapshot declared file",
            )
            relative_name = str(path.relative_to(manifest_path.parent))
            if relative_name in records or relative_name == "checksum_manifest.json":
                raise ArtifactError("readonly snapshot checksum closure is invalid")
            if _sha256(path) != declared:
                raise ArtifactError(f"readonly snapshot checksum mismatch: {relative_name}")
            if "bytes" in item and item.get("bytes") != path.stat().st_size:
                raise ArtifactError(f"readonly snapshot byte count mismatch: {relative_name}")
            records[relative_name] = self._file_record(path)
        required = {
            "manifest.json",
            str(manifest.get("snapshot") or ""),
            str(manifest.get("validation_report") or ""),
            str(manifest.get("forbidden_scope_audit") or ""),
        }
        missing = sorted(required - set(records))
        if "" in required or missing:
            raise ArtifactError(
                "readonly snapshot checksum closure is incomplete: " + ", ".join(missing)
            )
        return checksum_path, records

    def _source_signal(
        self,
        manifest: dict[str, Any],
        snapshot_latest: dict[str, Any],
        *,
        asof: str,
        model_id: str,
    ) -> tuple[str, dict[str, dict[str, Any]], dict[str, Any]]:
        source_manifest = self._regular_repo_file(
            str(manifest.get("source_signal_manifest") or ""),
            label="snapshot source signal manifest",
        )
        source_csv = self._regular_repo_file(
            str(manifest.get("source_signal_csv") or ""),
            label="snapshot source signal CSV",
        )
        expected_manifest_sha = str(manifest.get("source_signal_manifest_sha256") or "")
        expected_csv_sha = str(manifest.get("source_signal_csv_sha256") or "")
        if _sha256(source_manifest) != expected_manifest_sha or _sha256(source_csv) != expected_csv_sha:
            raise ArtifactError("readonly snapshot source signal checksum mismatch")
        source = self._load_json(source_manifest, label="snapshot source signal manifest")
        files = source.get("files")
        run_id = str(source.get("run_id") or "")
        if (
            PATH_SEGMENT_PATTERN.fullmatch(run_id) is None
            or run_id in {".", ".."}
            or PATH_SEGMENT_PATTERN.fullmatch(model_id) is None
            or model_id in {".", ".."}
        ):
            raise ArtifactError("readonly snapshot source signal run identity is invalid")
        controlled_model_root = (
            self.repo_root / "data_tw/artifacts/signals" / model_id
        ).resolve()
        controlled_latest_relative = Path(
            "data_tw/artifacts/signals"
        ) / model_id / "latest.json"
        declared_latest = str(manifest.get("source_signal_latest") or "")
        expected_latest_sha = str(
            manifest.get("source_signal_latest_sha256") or ""
        )
        if (
            declared_latest != str(controlled_latest_relative)
            or snapshot_latest.get("source_signal_latest") != declared_latest
            or snapshot_latest.get("source_signal_latest_sha256")
            != expected_latest_sha
            or SHA256_PATTERN.fullmatch(expected_latest_sha) is None
        ):
            raise ArtifactError(
                "readonly snapshot controlled signal latest identity is invalid"
            )
        controlled_latest_path = self._regular_repo_file(
            declared_latest, label="snapshot controlled signal latest pointer"
        )
        if _sha256(controlled_latest_path) != expected_latest_sha:
            raise ArtifactError(
                "readonly snapshot controlled signal latest checksum mismatch"
            )
        controlled_latest = self._load_json(
            controlled_latest_path, label="snapshot controlled signal latest pointer"
        )
        expected_source_dir = (
            controlled_model_root / run_id
        ).resolve()
        try:
            expected_source_dir.relative_to(controlled_model_root)
        except ValueError as exc:
            raise ArtifactError(
                "readonly snapshot source signal escapes the controlled model root"
            ) from exc
        if (
            source.get("artifact_type") != "ModelSignalArtifact"
            or source.get("model_id") != model_id
            or source.get("asof") != asof
            or source.get("status") != "READY"
            or source.get("production_allowed") is not False
            or source.get("not_published_latest") is not True
            or source.get("no_latest") is not True
            or not isinstance(files, dict)
            or source_csv != (source_manifest.parent / str(files.get("signals") or "")).resolve()
            or not run_id
            or source_manifest.parent != expected_source_dir
            or source_csv.parent != expected_source_dir
        ):
            raise ArtifactError("readonly snapshot source signal identity is invalid")
        source_dir_relative = self._relative(expected_source_dir)
        source_manifest_relative = self._relative(source_manifest)
        source_csv_relative = self._relative(source_csv)
        if (
            controlled_latest.get("artifact_type")
            != "controlled_model_signal_latest_pointer"
            or controlled_latest.get("schema_version")
            != "clpr.controlled_signal_latest_pointer.v1"
            or controlled_latest.get("model_id") != model_id
            or controlled_latest.get("model_name") != model_id
            or controlled_latest.get("asof") != asof
            or controlled_latest.get("signal_asof") != asof
            or controlled_latest.get("run_id") != run_id
            or controlled_latest.get("canonical_artifact_dir")
            != source_dir_relative
            or controlled_latest.get("source_artifact_dir") != source_dir_relative
            or controlled_latest.get("canonical_manifest")
            != source_manifest_relative
            or controlled_latest.get("canonical_manifest_sha256")
            != expected_manifest_sha
            or controlled_latest.get("source_manifest_sha256")
            != expected_manifest_sha
            or controlled_latest.get("canonical_signals") != source_csv_relative
            or controlled_latest.get("canonical_signals_sha256") != expected_csv_sha
            or controlled_latest.get("source_signals_sha256") != expected_csv_sha
            or controlled_latest.get("readonly_only") is not True
            or controlled_latest.get("production_trade_enabled") is not False
            or controlled_latest.get("provider_publish") is not False
            or controlled_latest.get("provider_accepted_latest_switch") is not False
            or controlled_latest.get("qlib_accepted_latest_switch") is not False
            or controlled_latest.get("frontend_default_switch") is not False
        ):
            raise ArtifactError(
                "readonly snapshot controlled signal latest identity is invalid"
            )
        return (
            run_id,
            {
                "manifest.json": self._file_record(source_manifest),
                "signals.csv": self._file_record(source_csv),
            },
            self._file_record(controlled_latest_path),
        )

    def _snapshot_ref(self, *, asof: str) -> ArtifactRef:
        latest_path, _ = self._registry_latest()
        model_id, _ = self._baseline_model_id()
        latest = self._load_json(latest_path, label="readonly snapshot latest pointer")
        expected_manifest = PUBLISH_ROOT / asof / "manifest.json"
        manifest_path = self._readonly_file(
            expected_manifest, label="readonly snapshot manifest"
        )
        manifest_sha256 = _sha256(manifest_path)
        manifest = self._load_json(manifest_path, label="readonly snapshot manifest")
        if (
            latest.get("artifact_type") != "readonly_strategy_snapshot_latest_pointer"
            or latest.get("asof") != asof
            or latest.get("readonly_only") is not True
            or latest.get("production_trade_enabled") is not False
            or latest.get("not_provider_accepted_latest") is not True
            or latest.get("not_trade_target_latest") is not True
            or latest.get("snapshot_manifest") != str(expected_manifest)
            or latest.get("candidate_only") is not True
            or latest.get("data_asof") != asof
            or latest.get("signal_asof") != asof
            or latest.get("source_signal_manifest_sha256")
            != manifest.get("source_signal_manifest_sha256")
            or latest.get("source_signal_csv_sha256")
            != manifest.get("source_signal_csv_sha256")
            or latest.get("source_signal_latest")
            != manifest.get("source_signal_latest")
            or latest.get("source_signal_latest_sha256")
            != manifest.get("source_signal_latest_sha256")
            or latest.get("planned_manifest_payload_sha256") != manifest_sha256
        ):
            raise ArtifactError("readonly snapshot latest pointer identity is invalid")
        if (
            manifest.get("artifact_type") != "readonly_strategy_snapshot"
            or manifest.get("schema_version") != "readonly_strategy_snapshot_r13_v1"
            or manifest.get("asof") != asof
            or manifest.get("model_id") != model_id
            or manifest.get("base_model_id") != model_id
            or manifest.get("readonly_only") is not True
            or manifest.get("production_trade_enabled") is not False
            or manifest.get("no_order_action") is not True
            or manifest.get("not_target_position") is not True
            or manifest.get("not_investment_advice") is not True
            or manifest.get("is_production_trading_default") is not False
            or manifest.get("candidate_only") is not True
            or manifest.get("strategy_rule") != "candidate_only_no_strategy_replay"
            or manifest.get("order_intent_status") != "not_built_forbidden_in_rsppr"
            or manifest.get("replay_result_status") != "not_built_forbidden_in_rsppr"
        ):
            raise ArtifactError("readonly snapshot manifest identity/safety is invalid")
        checksum_path, declared_files = self._checksum_files(manifest_path, manifest)
        snapshot_path = manifest_path.parent / str(manifest["snapshot"])
        snapshot = self._load_json(snapshot_path, label="readonly snapshot payload")
        shared_identity = (
            "asof",
            "model_id",
            "base_model_id",
            "strategy_rule",
            "candidate_boundary",
            "ranking_source",
            "display_role",
        )
        if any(snapshot.get(key) != manifest.get(key) for key in shared_identity) or (
            snapshot.get("data_asof") != asof
            or snapshot.get("signal_asof") != asof
            or snapshot.get("candidate_only") is not True
            or snapshot.get("readonly_only") is not True
            or snapshot.get("production_trade_enabled") is not False
            or snapshot.get("no_order_action") is not True
            or snapshot.get("not_order") is not True
            or snapshot.get("not_target_position") is not True
            or snapshot.get("not_investment_advice") is not True
            or snapshot.get("is_production_trading_default") is not False
        ):
            raise ArtifactError("readonly snapshot payload identity/safety is invalid")
        validation_path = manifest_path.parent / str(manifest["validation_report"])
        validation = self._load_json(validation_path, label="snapshot validation report")
        forbidden_path = manifest_path.parent / str(manifest["forbidden_scope_audit"])
        forbidden = self._load_json(forbidden_path, label="snapshot forbidden scope audit")
        flags = forbidden.get("flags")
        if (
            validation.get("status") != "pass"
            or validation.get("readonly_snapshot_validator_ok") is not True
            or validation.get("checksum_ok") is not True
            or forbidden.get("status") != "pass"
            or forbidden.get("all_forbidden_false") is not True
            or not isinstance(flags, dict)
            or not flags
            or any(type(value) is not bool or value is not False for value in flags.values())
        ):
            raise ArtifactError("readonly snapshot validation/safety evidence failed")
        source_run_id, source_files, source_latest = self._source_signal(
            manifest, latest, asof=asof, model_id=model_id
        )
        return ArtifactRef(
            adapter_id=self.adapter_id,
            artifact_type=ARTIFACT_TYPE,
            model_id=model_id,
            asof=asof,
            status=OBSERVATION_STATUS,
            run_id=source_run_id,
            path=self._relative(manifest_path.parent),
            manifest_path=self._relative(manifest_path),
            manifest_sha256=manifest_sha256,
            metadata={
                "candidate_only": True,
                "full_strategy_status": "NOT_BUILT",
                "strategy_rule": "candidate_only_no_strategy_replay",
                "production_allowed": False,
                "no_apply": True,
                "mainline_blocking": False,
                "product_registry": self._file_record(self.product_registry_path),
                "baseline_descriptor": self._file_record(self.baseline_descriptor_path),
                "latest_pointer": self._file_record(latest_path),
                "checksum_manifest": self._file_record(checksum_path),
                "declared_files": declared_files,
                "source_signal_latest": source_latest,
                "source_signal_files": source_files,
            },
        )

    def query(
        self,
        *,
        artifact_type: str | None,
        model_id: str | None,
        asof: str | None,
        status: str | None,
    ) -> list[ArtifactRef]:
        if asof is None:
            raise ArtifactError("readonly snapshot observation requires an explicit asof")
        validate_asof(asof)
        ref = self._snapshot_ref(asof=asof)
        filters = {
            "artifact_type": artifact_type,
            "model_id": model_id,
            "asof": asof,
            "status": status,
        }
        if any(value is not None and getattr(ref, key) != value for key, value in filters.items()):
            return []
        return [ref]


class ReadonlyStrategySnapshotObservation:
    module_id = "readonly_strategy_snapshot.observe"
    required_permissions = frozenset({"artifact.read"})

    def __init__(
        self,
        repo_root: Path,
        *,
        adapter_factory: Callable[[Path], ReadonlyStrategySnapshotAdapter]
        | None = None,
    ) -> None:
        self.repo_root = Path(repo_root)
        self._adapter_factory = adapter_factory or ReadonlyStrategySnapshotAdapter

    def _adapter(self) -> ReadonlyStrategySnapshotAdapter:
        # Snapshot configuration is intentionally loaded only when this module runs.
        return self._adapter_factory(self.repo_root)

    def _query(
        self, context: ExecutionContext, config: dict[str, Any]
    ) -> list[ArtifactRef]:
        return self._adapter().query(
            artifact_type=str(config.get("artifact_type") or ""),
            model_id=str(config.get("model_id") or ""),
            asof=str(config.get("asof") or context.asof),
            status=str(config.get("status") or ""),
        )

    def resolve_artifact_inputs(
        self,
        context: ExecutionContext,
        config: dict[str, Any],
        resolver: ArtifactResolver,
    ) -> list[ArtifactRef]:
        return self._query(context, config)

    def execute(
        self,
        context: ExecutionContext,
        config: dict[str, Any],
        inputs: dict[str, dict[str, Any]],
        resolver: ArtifactResolver,
    ) -> dict[str, Any]:
        allowed = {
            "artifact_type",
            "model_id",
            "asof",
            "status",
            "min_count",
            "require_candidate_only",
        }
        unknown = sorted(set(config) - allowed)
        if unknown:
            raise WorkflowError(
                f"unknown readonly snapshot config fields: {', '.join(unknown)}"
            )
        min_count = config.get("min_count", 1)
        if not isinstance(min_count, int) or isinstance(min_count, bool) or min_count < 0:
            raise WorkflowError("min_count must be a non-negative integer")
        refs = self._query(context, config)
        if len(refs) < min_count:
            raise ModuleBlocked(
                f"only {len(refs)} matching snapshots found; at least {min_count} required"
            )
        if config.get("require_candidate_only") is True and any(
            ref.metadata.get("candidate_only") is not True for ref in refs
        ):
            raise ModuleBlocked("readonly snapshot is not candidate-only")
        return {
            "count": len(refs),
            "query": {
                "artifact_type": str(config.get("artifact_type") or ""),
                "model_id": str(config.get("model_id") or ""),
                "asof": str(config.get("asof") or context.asof),
                "status": str(config.get("status") or ""),
                "require_candidate_only": config.get("require_candidate_only") is True,
            },
            "artifacts": [ref.to_dict() for ref in refs],
            "full_strategy_admission": False,
        }
