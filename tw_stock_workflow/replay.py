from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import yaml

from .artifacts import ArtifactError, ArtifactRef, ArtifactResolver
from .modules import ModuleBlocked
from .types import ExecutionContext, WorkflowError, validate_asof


READONLY_ROOT = Path("data_tw/artifacts/readonly_replay_windows")
REQUIRED_REPLAY_FILES = {
    "summary",
    "daily_nav",
    "actions",
    "snapshots",
    "decision_source_audit",
    "forbidden_scope_audit",
    "action_lineage_audit",
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_sha256(payload: Any) -> str:
    encoded = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class ReadonlyReplayWindowAdapter:
    adapter_id = "readonly_replay_window.v1"

    def __init__(
        self,
        repo_root: Path,
        *,
        product_registry_path: Path | None = None,
        replay_policy_path: Path | None = None,
    ) -> None:
        self.repo_root = Path(repo_root).resolve()
        self._resolver = ArtifactResolver(self.repo_root)
        self.product_registry_path = self._contained_path(
            product_registry_path or Path("configs/tw_product_artifact_registry.yaml")
        )
        self.replay_policy_path = self._contained_path(
            replay_policy_path or Path("configs/tw_replay_window_policy.yaml")
        )

    def _contained_path(self, raw_path: str | Path) -> Path:
        path = Path(raw_path)
        try:
            return self._resolver.resolve_path(str(path))
        except ArtifactError as exc:
            raise ArtifactError(
                f"replay configuration path escapes repository: {raw_path}"
            ) from exc

    def _readonly_path(self, raw_path: str | Path) -> Path:
        try:
            path = self._resolver.resolve_path(str(raw_path))
        except ArtifactError as exc:
            raise ArtifactError(
                f"replay artifact is outside the readonly product root: {raw_path}"
            ) from exc
        allowed_root = (self.repo_root / READONLY_ROOT).resolve()
        try:
            path.relative_to(allowed_root)
        except ValueError as exc:
            raise ArtifactError(
                f"replay artifact is outside the readonly product root: {raw_path}"
            ) from exc
        return path

    def _relative(self, path: Path) -> str:
        return str(path.resolve().relative_to(self.repo_root))

    @staticmethod
    def _load_json(path: Path) -> dict[str, Any]:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ArtifactError(f"invalid replay JSON: {path}") from exc
        if not isinstance(payload, dict):
            raise ArtifactError(f"replay JSON must be an object: {path}")
        return payload

    @staticmethod
    def _load_yaml(path: Path) -> dict[str, Any]:
        try:
            payload = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as exc:
            raise ArtifactError(f"invalid replay YAML: {path}") from exc
        if not isinstance(payload, dict):
            raise ArtifactError(f"replay YAML must be an object: {path}")
        return payload

    def _checksum_path(self, manifest_path: Path, raw_path: Any) -> Path:
        if not isinstance(raw_path, str) or not raw_path:
            raise ArtifactError(f"checksum manifest is not declared: {manifest_path}")
        candidate = (manifest_path.parent / raw_path).resolve()
        if candidate.is_file():
            return self._readonly_path(candidate)
        return self._readonly_path(raw_path)

    def _validate_checksums(
        self,
        checksum_path: Path,
        *,
        artifact_type: str,
        schema_version: str,
        required_paths: set[Path],
    ) -> dict[str, str]:
        payload = self._load_json(checksum_path)
        if (
            payload.get("artifact_type") != artifact_type
            or payload.get("schema_version") != schema_version
        ):
            raise ArtifactError(f"unexpected checksum contract: {checksum_path}")
        files = payload.get("files")
        if not isinstance(files, list) or not files:
            raise ArtifactError(f"checksum manifest has no files: {checksum_path}")
        checksums: dict[str, str] = {}
        for item in files:
            if not isinstance(item, dict):
                raise ArtifactError(f"invalid checksum entry: {checksum_path}")
            raw_path = item.get("path")
            declared = item.get("sha256")
            if (
                not isinstance(raw_path, str)
                or not raw_path
                or not isinstance(declared, str)
            ):
                raise ArtifactError(f"invalid checksum identity: {checksum_path}")
            target = self._readonly_path(raw_path)
            relative = self._relative(target)
            if relative in checksums:
                raise ArtifactError(f"duplicate checksum path: {relative}")
            if not target.is_file() or _sha256(target) != declared:
                raise ArtifactError(f"replay checksum mismatch: {relative}")
            if (
                not isinstance(item.get("bytes"), int)
                or item["bytes"] != target.stat().st_size
            ):
                raise ArtifactError(f"replay byte count mismatch: {relative}")
            checksums[relative] = declared
        missing = sorted(
            self._relative(path)
            for path in required_paths
            if self._relative(path) not in checksums
        )
        if missing:
            raise ArtifactError(
                f"required replay checksums missing: {', '.join(missing)}"
            )
        return checksums

    @staticmethod
    def _full_contract_gaps(manifest: dict[str, Any]) -> list[str]:
        validation = manifest.get("replay_window_policy_validation")
        validation = validation if isinstance(validation, dict) else {}
        gaps: list[str] = []
        if manifest.get("not_copied_from_legacy_replay") is not True:
            gaps.append("not_copied_from_legacy_replay")
        if validation.get("model_training_windows_traceable") is not True:
            gaps.append("model_training_windows_traceable")
        if not manifest.get("order_intent_artifacts"):
            gaps.append("source_order_intents_exist")
        return gaps

    def _product_index_path(self) -> Path:
        registry = self._load_yaml(self.product_registry_path)
        if (
            registry.get("schema_version") != "tw_product_artifact_registry_v1"
            or registry.get("readonly_only") is not True
        ):
            raise ArtifactError("product artifact registry is not readonly v1")
        artifacts = registry.get("artifacts")
        if not isinstance(artifacts, dict):
            raise ArtifactError("product artifact registry artifacts are missing")
        safety = registry.get("safety")
        required_safety = (
            "no_training_in_product_context",
            "no_provider_publish",
            "no_accepted_latest_switch",
            "no_monitor_write",
            "no_broker_order",
        )
        if not isinstance(safety, dict) or any(
            type(safety.get(key)) is not bool or safety[key] is not True
            for key in required_safety
        ):
            raise ArtifactError("product artifact registry safety contract is invalid")
        raw_path = artifacts.get("readonly_replay_window_index_manifest")
        return self._readonly_path(raw_path)

    def _allowed_pairs(self) -> tuple[set[tuple[str, str]], set[tuple[str, str, str]]]:
        policy = self._load_yaml(self.replay_policy_path)
        models = policy.get("models")
        if not isinstance(models, dict):
            raise ArtifactError("replay policy models are missing")
        strategy = policy.get("default_strategy_rule")
        if not isinstance(strategy, str) or not strategy:
            raise ArtifactError("replay policy default strategy is missing")
        pairs = {
            (model_id, strategy)
            for model_id, model in models.items()
            if isinstance(model_id, str)
            and isinstance(model, dict)
            and model.get("production_selectable") is True
        }
        windows: set[tuple[str, str, str]] = set()
        for window in policy.get("allowed_windows") or []:
            if not isinstance(window, dict):
                raise ArtifactError("replay policy window is invalid")
            name = window.get("name")
            start = window.get("start")
            end = window.get("end")
            if not all(isinstance(item, str) and item for item in (name, start, end)):
                raise ArtifactError("replay policy window identity is incomplete")
            validate_asof(start)
            validate_asof(end)
            windows.add((name, start, end))
        if not pairs or not windows:
            raise ArtifactError("replay policy has no selectable pair or window")
        return pairs, windows

    def _entry_ref(
        self,
        *,
        entry: dict[str, Any],
        index_manifest_path: Path,
        index_manifest_sha256: str,
        index_checksum_path: Path,
        allowed_windows: set[tuple[str, str, str]],
    ) -> ArtifactRef:
        required_entry = {
            "window_key",
            "model_id",
            "strategy_rule",
            "start",
            "end",
            "artifact_manifest",
            "validation",
            "execution_price_mode",
        }
        if not required_entry.issubset(entry):
            raise ArtifactError("readonly replay index entry is incomplete")
        model_id = entry["model_id"]
        strategy = entry["strategy_rule"]
        start = entry["start"]
        end = entry["end"]
        window_key = entry["window_key"]
        if not all(
            isinstance(item, str) and item
            for item in (model_id, strategy, start, end, window_key)
        ):
            raise ArtifactError("readonly replay index identity fields are invalid")
        validate_asof(start)
        validate_asof(end)
        if (window_key, start, end) not in allowed_windows:
            raise ArtifactError("readonly replay index window is outside policy")
        validation = entry["validation"]
        if not isinstance(validation, dict) or validation.get("ok") is not True:
            raise ArtifactError("readonly replay index entry validation is not ok")
        if entry["execution_price_mode"] != "next_open":
            raise ArtifactError("readonly replay index execution mode is not next_open")
        policy_relative = self._relative(self.replay_policy_path)
        sources = entry.get("sources")
        if (
            not isinstance(sources, dict)
            or sources.get("replay_window_policy") != policy_relative
        ):
            raise ArtifactError("readonly replay index policy reference mismatch")

        manifest_path = self._readonly_path(entry["artifact_manifest"])
        manifest = self._load_json(manifest_path)
        if manifest.get("artifact_type") != "replay_result":
            raise ArtifactError("indexed artifact is not a replay_result")
        if manifest.get("schema_version") != "readonly_replay_result_d6_v1":
            raise ArtifactError("unsupported readonly replay result schema")
        expected_identity = {
            "model_id": model_id,
            "requested_model_id": model_id,
            "strategy_rule": strategy,
            "requested_strategy_rule": strategy,
            "window_start": start,
            "window_end": end,
        }
        for key, expected in expected_identity.items():
            if manifest.get(key) != expected:
                raise ArtifactError(
                    f"readonly replay manifest identity mismatch: {key}"
                )
        window = manifest.get("window")
        if not isinstance(window, dict) or (
            window.get("name"),
            window.get("start"),
            window.get("end"),
        ) != (window_key, start, end):
            raise ArtifactError("readonly replay manifest window mismatch")
        safety = {
            "readonly_only": True,
            "production_trade_enabled": False,
            "not_order": True,
            "not_target_position": True,
            "no_order_action": True,
            "no_provider_publish": True,
            "no_accepted_latest_switch": True,
            "no_monitor_broker_order": True,
            "execution_price_mode": "next_open",
            "decision_source": "order_intent_artifact",
        }
        for key, expected in safety.items():
            actual = manifest.get(key)
            if isinstance(expected, bool):
                matches = type(actual) is bool and actual is expected
            else:
                matches = actual == expected
            if not matches:
                raise ArtifactError(f"readonly replay safety mismatch: {key}")
        policy_validation = manifest.get("replay_window_policy_validation")
        if manifest.get("replay_window_policy") != policy_relative:
            raise ArtifactError("readonly replay manifest policy reference mismatch")
        if (
            not isinstance(policy_validation, dict)
            or policy_validation.get("ok") is not True
        ):
            raise ArtifactError("readonly replay policy validation is not ok")
        for key, expected in {
            "model_id": model_id,
            "strategy_rule": strategy,
            "requested_start": start,
            "requested_end": end,
        }.items():
            if policy_validation.get(key) != expected:
                raise ArtifactError(f"readonly replay policy identity mismatch: {key}")

        artifacts = manifest.get("artifacts")
        if not isinstance(artifacts, dict) or set(artifacts) != REQUIRED_REPLAY_FILES:
            raise ArtifactError("readonly replay artifact file set is invalid")
        artifact_paths = {
            self._readonly_path(raw_path) for raw_path in artifacts.values()
        }
        forbidden_json_path = self._readonly_path(
            manifest.get("forbidden_scope_audit_json")
        )
        checksum_path = self._checksum_path(
            manifest_path, manifest.get("checksum_manifest")
        )
        replay_checksums = self._validate_checksums(
            checksum_path,
            artifact_type="readonly_replay_checksum_manifest",
            schema_version="readonly_replay_checksum_d6_v1",
            required_paths={manifest_path, forbidden_json_path, *artifact_paths},
        )
        manifest_sha256 = replay_checksums[self._relative(manifest_path)]
        forbidden = self._load_json(forbidden_json_path)
        if forbidden.get("status") != "pass" or any(
            forbidden.get(key) is not True
            for key in (
                "no_provider_publish",
                "no_accepted_latest_switch",
                "no_monitor_broker_order",
            )
        ):
            raise ArtifactError("readonly replay forbidden scope audit did not pass")

        validation_path = self._readonly_path(
            manifest_path.parent / "validation_report.json"
        )
        validation_report = self._load_json(validation_path)
        if set(validation_report) != {
            "artifact_type",
            "created_at",
            "manifest",
            "schema_version",
            "status",
        } or (
            validation_report.get("artifact_type")
            != "readonly_replay_validation_report"
            or validation_report.get("schema_version")
            != "readonly_replay_validation_d6_v1"
            or validation_report.get("status") != "pass"
            or validation_report.get("manifest") != self._relative(manifest_path)
        ):
            raise ArtifactError("readonly replay narrow validation evidence is invalid")
        gaps = self._full_contract_gaps(manifest)
        combined_identity = _canonical_sha256(
            {
                "index_manifest_sha256": index_manifest_sha256,
                "replay_manifest_sha256": manifest_sha256,
                "model_id": model_id,
                "strategy_rule": strategy,
                "window_start": start,
                "window_end": end,
            }
        )
        return ArtifactRef(
            adapter_id=self.adapter_id,
            artifact_type="ReadonlyReplayWindowArtifact",
            model_id=model_id,
            asof=end,
            status="INDEXED_READONLY",
            run_id=f"replay_window_{combined_identity[:24]}",
            path=self._relative(manifest_path.parent),
            manifest_path=self._relative(manifest_path),
            manifest_sha256=manifest_sha256,
            metadata={
                "strategy_rule": strategy,
                "window_key": window_key,
                "window_start": start,
                "window_end": end,
                "execution_price_mode": "next_open",
                "product_registry_path": self._relative(self.product_registry_path),
                "product_registry_sha256": _sha256(self.product_registry_path),
                "replay_policy_path": policy_relative,
                "replay_policy_sha256": _sha256(self.replay_policy_path),
                "index_manifest_path": self._relative(index_manifest_path),
                "index_manifest_sha256": index_manifest_sha256,
                "index_checksum_manifest_path": self._relative(index_checksum_path),
                "index_checksum_manifest_sha256": _sha256(index_checksum_path),
                "replay_checksum_manifest_path": self._relative(checksum_path),
                "replay_checksum_manifest_sha256": _sha256(checksum_path),
                "validation_report_path": self._relative(validation_path),
                "validation_report_sha256": _sha256(validation_path),
                "validation_scope": "LEGACY_NARROW_READONLY_WINDOW",
                "full_replay_contract_status": "HOLD",
                "full_replay_contract_gaps": gaps,
                "no_recompute": True,
                "no_switch": True,
            },
        )

    def query(
        self,
        *,
        artifact_type: str | None = None,
        model_id: str | None = None,
        asof: str | None = None,
        status: str | None = None,
        strategy_rule: str | None = None,
        window_start: str | None = None,
        window_end: str | None = None,
    ) -> list[ArtifactRef]:
        if asof is not None:
            validate_asof(asof)
        index_manifest_path = self._product_index_path()
        index_manifest = self._load_json(index_manifest_path)
        if (
            index_manifest.get("artifact_type") != "readonly_replay_window_index"
            or index_manifest.get("schema_version")
            != "readonly_replay_window_index_d7_v1"
            or index_manifest.get("readonly_only") is not True
            or index_manifest.get("production_trade_enabled") is not False
            or index_manifest.get("indexed_windows_only") is not True
        ):
            raise ArtifactError("readonly replay window index contract is invalid")
        if index_manifest.get("execution_price_mode") != "next_open":
            raise ArtifactError("readonly replay index execution mode is not next_open")
        entries = index_manifest.get("windows")
        if not isinstance(entries, list) or not entries:
            raise ArtifactError("readonly replay window index has no entries")
        identities: set[tuple[Any, Any, Any, Any]] = set()
        for entry in entries:
            if not isinstance(entry, dict):
                raise ArtifactError("readonly replay window index entry is invalid")
            identity = (
                entry.get("model_id"),
                entry.get("strategy_rule"),
                entry.get("start"),
                entry.get("end"),
            )
            if identity in identities:
                raise ArtifactError("duplicate readonly replay window identity")
            identities.add(identity)
        index_checksum_path = self._checksum_path(
            index_manifest_path, index_manifest.get("checksum_manifest")
        )
        indexed_manifests = {
            self._readonly_path(entry.get("artifact_manifest"))
            for entry in entries
            if isinstance(entry, dict)
        }
        index_checksums = self._validate_checksums(
            index_checksum_path,
            artifact_type="readonly_replay_window_index_checksum",
            schema_version="readonly_replay_window_index_checksum_d7_v1",
            required_paths={index_manifest_path, *indexed_manifests},
        )
        index_manifest_sha256 = index_checksums[self._relative(index_manifest_path)]
        allowed_pairs, allowed_windows = self._allowed_pairs()
        refs: list[ArtifactRef] = []
        for entry in entries:
            if not isinstance(entry, dict):
                raise ArtifactError("readonly replay window index entry is invalid")
            pair = (entry.get("model_id"), entry.get("strategy_rule"))
            if pair not in allowed_pairs:
                continue
            ref = self._entry_ref(
                entry=entry,
                index_manifest_path=index_manifest_path,
                index_manifest_sha256=index_manifest_sha256,
                index_checksum_path=index_checksum_path,
                allowed_windows=allowed_windows,
            )
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
                continue
            if (
                strategy_rule is not None
                and ref.metadata["strategy_rule"] != strategy_rule
            ):
                continue
            if (
                window_start is not None
                and ref.metadata["window_start"] != window_start
            ):
                continue
            if window_end is not None and ref.metadata["window_end"] != window_end:
                continue
            refs.append(ref)
        return sorted(refs, key=lambda ref: (ref.asof, ref.model_id, ref.run_id))


class ReadonlyReplayWindowObservation:
    module_id = "replay_window.observe"
    required_permissions = frozenset({"replay.read"})

    def __init__(self, adapter: ReadonlyReplayWindowAdapter) -> None:
        self.adapter = adapter

    @staticmethod
    def _validate_config(config: dict[str, Any]) -> None:
        allowed = {
            "model_id",
            "strategy_rule",
            "window_start",
            "window_end",
            "status",
            "min_count",
        }
        unknown = sorted(set(config) - allowed)
        if unknown:
            raise WorkflowError(
                f"unknown replay observation config fields: {', '.join(unknown)}"
            )
        for key in ("model_id", "strategy_rule", "window_start"):
            if not isinstance(config.get(key), str) or not config[key]:
                raise WorkflowError(f"replay observation {key} is required")
        if "window_end" in config and (
            not isinstance(config["window_end"], str) or not config["window_end"]
        ):
            raise WorkflowError(
                "replay observation window_end must be a non-empty string"
            )
        if config.get("status", "INDEXED_READONLY") != "INDEXED_READONLY":
            raise WorkflowError("replay observation status must be INDEXED_READONLY")
        min_count = config.get("min_count", 1)
        if (
            not isinstance(min_count, int)
            or isinstance(min_count, bool)
            or min_count < 0
        ):
            raise WorkflowError(
                "replay observation min_count must be a non-negative integer"
            )

    def _query(
        self, context: ExecutionContext, config: dict[str, Any]
    ) -> list[ArtifactRef]:
        self._validate_config(config)
        return self.adapter.query(
            artifact_type="ReadonlyReplayWindowArtifact",
            model_id=config["model_id"],
            asof=str(config.get("window_end") or context.asof),
            status="INDEXED_READONLY",
            strategy_rule=config["strategy_rule"],
            window_start=config["window_start"],
            window_end=str(config.get("window_end") or context.asof),
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
        refs = self._query(context, config)
        min_count = int(config.get("min_count", 1))
        if len(refs) < min_count:
            raise ModuleBlocked(
                f"only {len(refs)} indexed readonly replay windows found; {min_count} required"
            )
        return {
            "count": len(refs),
            "observation_kind": "READONLY_REPLAY_WINDOW_INDEX",
            "full_replay_contract_admission": False,
            "artifacts": [ref.to_dict() for ref in refs],
        }
