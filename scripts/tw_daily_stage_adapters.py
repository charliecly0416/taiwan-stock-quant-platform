"""Named stage adapters for the legacy daily orchestrator migration.

Each adapter is intentionally callback-based.  The callback remains owned by
the legacy entrypoint until that stage has an independently verified parity
fixture; this module supplies the stable ownership boundary and common result
shape without changing default execution.
"""
from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping

try:  # Support both ``python scripts/run_...py`` and package imports in tests.
    from .tw_daily_runtime_stages import StageFacade, fingerprints_unchanged
except ImportError:  # pragma: no cover - script execution path
    from tw_daily_runtime_stages import StageFacade, fingerprints_unchanged


StageCallback = Callable[[Mapping[str, Any]], Mapping[str, Any] | Any]
MODEL_A_SIGNAL_FIELDS = {
    "date", "instrument", "model_name", "model_family", "candidate_rank",
    "buy_score", "raw_score", "score_rank", "full_qlib_rank", "signal_asof",
    "available_at", "source_artifact", "source_model_artifact", "source_feature_artifact",
}


def validate_model_a_top50(rows: list[Mapping[str, Any]]) -> dict[str, Any]:
    """Strictly validate the Model A candidate boundary consumed by shadows."""
    top50 = list(rows)
    ranks = [int(str(row.get("full_qlib_rank"))) for row in top50 if str(row.get("full_qlib_rank") or "").isdigit()]
    candidate_ids = [str(row.get("instrument") or "") for row in top50]
    errors: list[str] = []
    if len(top50) != 50:
        errors.append("top50_row_count_not_50")
    if len(ranks) != 50 or len(set(ranks)) != 50:
        errors.append("top50_rank_not_unique")
    if set(ranks) != set(range(1, 51)):
        errors.append("top50_rank_key_set_not_1_to_50")
    if len(candidate_ids) != 50 or any(not value for value in candidate_ids) or len(set(candidate_ids)) != 50:
        errors.append("top50_candidate_id_not_unique")
    candidate_key_set = sorted(candidate_ids)
    candidate_key_set_sha256 = hashlib.sha256("\n".join(candidate_key_set).encode("utf-8")).hexdigest()
    return {
        "ok": not errors,
        "errors": errors,
        "row_count": len(top50),
        "rank_count": len(ranks),
        "candidate_id_count": len(candidate_ids),
        "candidate_key_set_sha256": candidate_key_set_sha256,
        "rank_key_set": sorted(set(ranks)),
    }


def build_staged_artifact_publish_callback(*, rollback_source: Path | str) -> StageCallback:
    """Create a candidate-only publish callback with explicit authorization.

    The callback never writes a protected pointer. It writes candidate and
    rollback manifests beneath the caller-provided job directory only.
    """
    rollback_source = Path(rollback_source)

    def callback(context: Mapping[str, Any]) -> Mapping[str, Any]:
        job_dir = Path(str(context.get("job_dir") or ""))
        candidate_path = Path(str(context.get("candidate_path") or ""))
        auth = context.get("authorization") if isinstance(context.get("authorization"), Mapping) else {}
        before = context.get("protected_before") if isinstance(context.get("protected_before"), Mapping) else None
        after = context.get("protected_after") if isinstance(context.get("protected_after"), Mapping) else None
        base = {"ok": False, "published": False, "publish_allowed": False, "protected_pointer_write": False, "model_b_active_selection": False}
        if not job_dir or not candidate_path or not job_dir.is_absolute() or not candidate_path.is_file():
            return {**base, "status": "BLOCKED_CANDIDATE_ARTIFACT_MISSING"}
        if auth.get("allow_candidate_publish") is not True or str(auth.get("authorization_id") or "").strip() == "":
            return {**base, "status": "BLOCKED_UNAUTHORIZED_CANDIDATE_PUBLISH"}
        if auth.get("publish_mode") != "candidate_only":
            return {**base, "status": "BLOCKED_PUBLISH_MODE"}
        if before is not None and after is not None:
            audit = fingerprints_unchanged(before, after)
            if not audit.get("all_protected_paths_unchanged"):
                return {**base, "status": "BLOCKED_PROTECTED_FINGERPRINT_DRIFT", "protected_fingerprint_audit": audit}
        if not rollback_source.is_file():
            return {**base, "status": "BLOCKED_ROLLBACK_SOURCE_MISSING"}
        rollback_checksum = _sha256(rollback_source)
        expected_rollback_checksum = str(context.get("rollback_checksum") or rollback_checksum or "")
        if not rollback_checksum or rollback_checksum != expected_rollback_checksum:
            return {**base, "status": "BLOCKED_ROLLBACK_CHECKSUM_MISMATCH", "rollback_checksum": rollback_checksum, "expected_rollback_checksum": expected_rollback_checksum}
        if not candidate_path.resolve().is_relative_to(job_dir.resolve()):
            return {**base, "status": "BLOCKED_CANDIDATE_PATH_OUTSIDE_JOB_DIR"}
        publish_dir = job_dir / "candidate_publish"
        publish_dir.mkdir(parents=True, exist_ok=True)
        candidate_checksum = _sha256(candidate_path)
        rollback_manifest = {"model_id": "e4_frozen_qlib_2018_2022", "source_path": str(rollback_source), "sha256": rollback_checksum, "rollback_allowed": True, "protected_pointer_write": False}
        candidate_manifest = {"status": "CANDIDATE_ONLY_PUBLISHED", "authorization_id": str(auth["authorization_id"]), "candidate_path": str(candidate_path), "candidate_sha256": candidate_checksum, "rollback_manifest": "rollback_manifest.json", "published": False, "protected_pointer_write": False, "model_b_active_selection": False}
        (publish_dir / "rollback_manifest.json").write_text(json.dumps(rollback_manifest, indent=2) + "\n", encoding="utf-8")
        (publish_dir / "candidate_publish_manifest.json").write_text(json.dumps(candidate_manifest, indent=2) + "\n", encoding="utf-8")
        return {**base, "ok": True, "status": "CANDIDATE_ONLY_PUBLISHED", "publish_allowed": True, "candidate_sha256": candidate_checksum, "rollback_checksum": rollback_checksum, "manifest_path": str(publish_dir / "candidate_publish_manifest.json")}
    return callback


def _sha256(path: Path) -> str | None:
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def inspect_model_a_signal_artifact(signal_dir: Path | str, *, expected_model_id: str = "e4_frozen_qlib_2018_2022") -> dict[str, Any]:
    """Read-only ModelSignalArtifact observation used by the signal stage."""
    root = Path(signal_dir)
    manifest_path, signals_path = root / "manifest.json", root / "signals.csv"
    result: dict[str, Any] = {
        "stage": "signal", "stage_contract": "model_a_signal.v1", "model_id": expected_model_id,
        "status": "BLOCKED_SIGNAL_INPUT_MISSING", "ok": False, "signal_checksum": _sha256(signals_path),
        "manifest_checksum": _sha256(manifest_path), "row_count": 0, "schema_fields": [],
        "source_dir": str(root), "model_b_active_selection": False,
    }
    if not manifest_path.is_file() or not signals_path.is_file():
        result["error"] = "manifest_or_signals_missing"
        return result
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        with signals_path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            fields = set(reader.fieldnames or [])
            rows = list(reader)
    except (OSError, ValueError, csv.Error) as exc:
        result["status"] = "BLOCKED_SIGNAL_SCHEMA_MISMATCH"
        result["error"] = f"{type(exc).__name__}:{exc}"
        return result
    errors: list[str] = []
    if manifest.get("model_id") != expected_model_id:
        errors.append("model_id_mismatch")
    if manifest.get("status") != "READY":
        errors.append(f"manifest_status:{manifest.get('status')}")
    missing = sorted(MODEL_A_SIGNAL_FIELDS - fields)
    if missing:
        errors.append("missing_fields:" + ",".join(missing))
    if not rows:
        errors.append("empty_signal_rows")
    result.update({
        "manifest_status": manifest.get("status"), "signal_asof": manifest.get("signal_asof") or manifest.get("asof"),
        "available_at": manifest.get("available_at"), "row_count": len(rows), "schema_fields": sorted(fields),
        "errors": errors, "ok": not errors, "status": "READY" if not errors else "BLOCKED_SIGNAL_SCHEMA_MISMATCH",
    })
    return result


def project_legacy_model_a_signal_contract(signal_dir: Path | str, *, expected_model_id: str = "e4_frozen_qlib_2018_2022") -> dict[str, Any]:
    """Independent legacy producer projection for parity; does not call inspect()."""
    root = Path(signal_dir)
    manifest_path, signals_path = root / "manifest.json", root / "signals.csv"
    payload: dict[str, Any] = {"ok": False, "status": "BLOCKED_SIGNAL_INPUT_MISSING", "model_id": expected_model_id, "row_count": 0, "signal_checksum": _sha256(signals_path), "schema_fields": []}
    if not manifest_path.is_file() or not signals_path.is_file():
        return payload
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        with signals_path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            fields = sorted(reader.fieldnames or [])
            rows = list(reader)
    except (OSError, ValueError, csv.Error):
        payload["status"] = "BLOCKED_SIGNAL_SCHEMA_MISMATCH"
        return payload
    errors = []
    if manifest.get("model_id") != expected_model_id:
        errors.append("model_id_mismatch")
    if manifest.get("status") != "READY":
        errors.append("manifest_not_ready")
    if not MODEL_A_SIGNAL_FIELDS.issubset(fields):
        errors.append("required_fields_missing")
    payload.update({"ok": not errors, "status": "READY" if not errors else "BLOCKED_SIGNAL_SCHEMA_MISMATCH", "row_count": len(rows), "schema_fields": fields})
    return payload


def build_model_a_signal_callback(signal_dir: Path | str, *, expected_model_id: str = "e4_frozen_qlib_2018_2022") -> StageCallback:
    """Bind an existing Model A artifact without invoking scoring or writes."""
    def callback(context: Mapping[str, Any]) -> Mapping[str, Any]:
        return inspect_model_a_signal_artifact(signal_dir, expected_model_id=expected_model_id)
    return callback


def build_model_b_shadow_callback(*, expected_model_id: str = "e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025") -> StageCallback:
    """Build an isolated, non-scoring Model B top50 staging observation."""
    def callback(context: Mapping[str, Any]) -> Mapping[str, Any]:
        model_a = context.get("model_a_signal") if isinstance(context.get("model_a_signal"), Mapping) else context
        if not isinstance(model_a, Mapping) or not model_a.get("ok"):
            return {"ok": False, "status": "BLOCKED_MODEL_A_SIGNAL", "model_b_active_selection": False, "published": False}
        if model_a.get("model_id") != "e4_frozen_qlib_2018_2022":
            return {"ok": False, "status": "BLOCKED_MODEL_A_ID_MISMATCH", "model_b_active_selection": False, "published": False}
        signal_dir = Path(str(model_a.get("source_dir") or ""))
        signals_path = signal_dir / "signals.csv"
        try:
            with signals_path.open(newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
        except (OSError, csv.Error) as exc:
            return {"ok": False, "status": "BLOCKED_MODEL_A_ROWS_MISSING", "error": str(exc), "model_b_active_selection": False, "published": False}
        top50 = [row for row in rows if str(row.get("full_qlib_rank") or "").isdigit() and int(row["full_qlib_rank"]) <= 50]
        top50_validation = validate_model_a_top50(top50)
        top50_valid = bool(top50_validation["ok"])
        result: dict[str, Any] = {
            "ok": top50_valid, "status": "READY_FOR_SHADOW_STAGING" if top50_valid else "BLOCKED_TOP50_UNIVERSE",
            "model_id": expected_model_id, "base_model_id": model_a.get("model_id"), "candidate_universe": "model_a_top50_only",
            "candidate_universe_count": len(top50), "model_a_row_count": len(rows), "published": False,
            "candidate_universe_valid": top50_valid,
            "top50_validation": top50_validation,
            "latest_modified": False, "provider_modified": False, "model_b_active_selection": False,
            "signal_checksum": model_a.get("signal_checksum"), "shadow_score_generated": False,
        }
        job_dir = context.get("job_dir")
        if job_dir:
            stage_dir = Path(job_dir) / "model_b_shadow"
            stage_dir.mkdir(parents=True, exist_ok=True)
            result["staging_path"] = str(stage_dir / "shadow_observation.json")
            (stage_dir / "shadow_observation.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return result
    return callback


@dataclass
class NamedStageAdapter(StageFacade):
    """StageFacade with a contract name suitable for evidence and routing."""

    contract: str = "legacy_compatible"

    def run(self, context: Mapping[str, Any] | None = None) -> Any:
        if self.callback is None and self.name == "signal":
            return {
                "ok": False,
                "status": "model_a_signal_callback_missing",
                "stage": self.name,
                "stage_contract": self.contract,
                "model_b_active_selection": False,
            }
        result = super().run(context or {})
        if isinstance(result, Mapping):
            payload = dict(result)
            payload.setdefault("stage_contract", self.contract)
            payload.setdefault("stage", self.name)
            return payload
        return result


def _adapter(name: str, callback: StageCallback | None, contract: str) -> NamedStageAdapter:
    return NamedStageAdapter(name=name, callback=callback, contract=contract)


def build_named_stage_adapters(
    *,
    acquisition: StageCallback | None = None,
    readiness: StageCallback | None = None,
    model_a_signal: StageCallback | None = None,
    model_b_shadow: StageCallback | None = None,
    strategy: StageCallback | None = None,
    artifact_publish: StageCallback | None = None,
    ops_status: StageCallback | None = None,
) -> dict[str, NamedStageAdapter]:
    """Build explicit stage APIs while preserving callback injection semantics."""
    # Model B is represented as an independent shadow sub-stage. It is never
    # used as a fallback for Model A signal; a missing Model A callback fails
    # closed and cannot activate Model B implicitly.
    signal = model_a_signal
    return {
        "acquisition": _adapter("acquisition", acquisition, "acquisition.v1"),
        "readiness": _adapter("readiness", readiness, "readiness.v1"),
        "signal": _adapter("signal", signal, "model_a_signal.v1"),
        "model_b_shadow": _adapter("model_b_shadow", model_b_shadow, "model_b_shadow.v1"),
        "strategy": _adapter("strategy", strategy, "strategy.v1"),
        "artifact_publish": _adapter("artifact_publish", artifact_publish, "artifact_publish.v1"),
        "ops_status": _adapter("ops_status", ops_status, "ops_status.v1"),
    }


def stage_contract_summary(adapters: Mapping[str, NamedStageAdapter]) -> dict[str, Any]:
    """Return an evidence-safe map of adapter ownership and callback presence."""
    return {
        "schema_version": "arch2.named_stage_adapters.v1",
        "stages": {
            name: {"contract": adapter.contract, "callback_bound": adapter.callback is not None}
            for name, adapter in sorted(adapters.items())
        },
        "model_b_active_selection": False,
    }
