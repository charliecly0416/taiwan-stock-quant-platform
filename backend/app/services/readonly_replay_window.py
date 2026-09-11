"""Read-only replay window query service for audited TW modular artifacts."""
from __future__ import annotations

import csv
import hashlib
import json
from datetime import date
from pathlib import Path
from typing import Any

import yaml

from app.services import readonly_replay_window_index as replay_index
from scripts.tw_daily_runtime_stages import runtime_truth

REPO_ROOT = Path(__file__).resolve().parents[3]
POLICY = REPO_ROOT / "configs/tw_replay_window_policy.yaml"
REGISTRY = REPO_ROOT / "configs/tw_modular_registry.yaml"


class ReadonlyReplayWindowError(Exception):
    """Raised when a readonly replay window request is rejected."""

    def __init__(self, status: str, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.status = status
        self.message = message
        self.details = details or {}


def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def _resolve_repo_path(path: str) -> Path:
    resolved = (REPO_ROOT / path).resolve()
    if not resolved.is_relative_to(REPO_ROOT.resolve()):
        raise ReadonlyReplayWindowError("path_outside_root", f"Path outside repo root: {path}")
    return resolved


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists() or not path.is_file():
        raise ReadonlyReplayWindowError("missing_artifact", f"Missing readonly artifact: {_rel(path)}")
    return json.loads(path.read_text(encoding="utf-8"))


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists() or not path.is_file():
        raise ReadonlyReplayWindowError("missing_policy", f"Missing replay window policy: {_rel(path)}")
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}



def _production_model_ids(policy: dict[str, Any]) -> set[str]:
    models = policy.get("models") or {}
    return {key for key, value in models.items() if (value or {}).get("production_selectable") is True}


def _clean_strategy_sets(registry: dict[str, Any]) -> dict[str, set[str]]:
    strategies = registry.get("strategies") or {}
    return {
        "production_selectable": set((strategies.get("production_selectable") or {}).keys()),
        "research_only": set((strategies.get("research_only") or {}).keys()),
        "deprecated": set((strategies.get("deprecated") or {}).keys()),
    }


def _clean_default_request(policy: dict[str, Any] | None = None) -> dict[str, str]:
    payload = policy or _load_yaml(POLICY)
    models = payload.get("models") or {}
    truth = runtime_truth()
    default_model = str(truth.active_model_id or payload.get("default_model_id") or next(iter(models.keys()), ""))
    default_strategy = str(truth.strategy_rule or payload.get("default_strategy_rule") or "")
    if not default_strategy:
        registry = _load_yaml(REGISTRY)
        production = sorted(_clean_strategy_sets(registry)["production_selectable"])
        default_strategy = production[0] if production else ""
    return {"model_id": default_model, "strategy_rule": default_strategy}


def default_replay_model_id() -> str:
    return _clean_default_request()["model_id"]


def default_replay_strategy_rule() -> str:
    return _clean_default_request()["strategy_rule"]


def _validate_strategy_rule_from_registry(strategy_rule: str) -> None:
    registry = _load_yaml(REGISTRY)
    sets = _clean_strategy_sets(registry)
    if strategy_rule in sets["production_selectable"]:
        return
    if strategy_rule in sets["research_only"]:
        detail = ((registry.get("strategies") or {}).get("research_only") or {}).get(strategy_rule) or {}
        raise ReadonlyReplayWindowError(
            "research_only_strategy_not_valid_strategy_evidence",
            "research-only strategy cannot be queried as production strategy evidence",
            {"strategy_rule": strategy_rule, "display_name": detail.get("display_name")},
        )
    if strategy_rule in sets["deprecated"]:
        raise ReadonlyReplayWindowError(
            "deprecated_strategy_rule",
            "deprecated strategy_rule is not product selectable",
            {"strategy_rule": strategy_rule},
        )
    raise ReadonlyReplayWindowError("unknown_strategy_rule", "strategy_rule is not registered in clean registry", {"strategy_rule": strategy_rule})


def _parse_date(value: str, field: str) -> date:
    try:
        return date.fromisoformat(str(value))
    except Exception as exc:  # noqa: BLE001
        raise ReadonlyReplayWindowError("invalid_date", f"Invalid {field}: {value}", {field: value}) from exc


def _date_or_none(value: Any) -> date | None:
    if value in (None, ""):
        return None
    return date.fromisoformat(str(value))


def _overlaps(start: date, end: date, other_start: date | None, other_end: date | None) -> bool:
    if other_start is None or other_end is None:
        return False
    return start <= other_end and other_start <= end


def _read_summary(replay_manifest: dict[str, Any], model_id: str, strategy_rule: str) -> dict[str, Any]:
    path = _resolve_repo_path(str((replay_manifest.get("artifacts") or {}).get("summary", "")))
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            if str(row.get("method")) == model_id and str(row.get("rule")) == strategy_rule:
                return row
    return {}


def _window_validation(policy: dict[str, Any], model_id: str, strategy_rule: str, start: str, end: str) -> dict[str, Any]:
    start_date = _parse_date(start, "start")
    end_date = _parse_date(end, "end")
    if start_date > end_date:
        raise ReadonlyReplayWindowError("invalid_window", "start_date must be <= end_date", {"requested_start": start, "requested_end": end})
    models = policy.get("models") or {}
    if model_id == "e4_frozen_qlib_2023_2025_ltr":
        raise ReadonlyReplayWindowError("deprecated_model_id", "model_id is not product selectable in clean ReplayWindowPolicy", {"model_id": model_id})
    if model_id not in models:
        raise ReadonlyReplayWindowError("unknown_model", "model_id is not registered in ReplayWindowPolicy", {"model_id": model_id})
    if model_id not in _production_model_ids(policy):
        raise ReadonlyReplayWindowError("deprecated_model_id", "model_id is not product selectable in clean ReplayWindowPolicy", {"model_id": model_id})
    _validate_strategy_rule_from_registry(strategy_rule)
    diagnostic = (policy.get("diagnostic_rules") or {}).get(strategy_rule) or {}
    if diagnostic.get("not_valid_strategy_evidence") is True:
        raise ReadonlyReplayWindowError("research_only_strategy_not_valid_strategy_evidence", "research-only rule cannot be queried as valid strategy evidence", {"strategy_rule": strategy_rule})
    meta = models[model_id]
    allowed_min = _parse_date(str(meta.get("allowed_replay_start_min") or policy.get("allowed_replay_start_min")), "allowed_replay_start_min")
    latest = _parse_date(str(policy.get("latest_available_signal_date")), "latest_available_signal_date")
    if start_date < allowed_min:
        raise ReadonlyReplayWindowError("requested_window_before_allowed_replay_start", "requested window overlaps training or pre-approved period", {"model_id": model_id, "requested_start": start, "requested_end": end, "allowed_replay_start_min": str(allowed_min)})
    if end_date > latest:
        raise ReadonlyReplayWindowError("requested_window_beyond_latest_signal", "requested window is beyond latest available signal date", {"requested_end": end, "latest_available_signal_date": str(latest)})
    q_start = _date_or_none(meta.get("qlib_train_start"))
    q_end = _date_or_none(meta.get("qlib_train_end"))
    l_start = _date_or_none(meta.get("ltr_train_start"))
    l_end = _date_or_none(meta.get("ltr_train_end"))
    if _overlaps(start_date, end_date, q_start, q_end):
        raise ReadonlyReplayWindowError("requested_window_overlaps_qlib_training_window", "requested window overlaps qlib training window", {"model_id": model_id, "requested_start": start, "requested_end": end, "qlib_train_start": str(q_start), "qlib_train_end": str(q_end), "allowed_replay_start_min": str(allowed_min)})
    if _overlaps(start_date, end_date, l_start, l_end):
        raise ReadonlyReplayWindowError("requested_window_overlaps_ltr_training_window", "requested window overlaps LTR training window", {"model_id": model_id, "requested_start": start, "requested_end": end, "ltr_train_start": str(l_start), "ltr_train_end": str(l_end), "allowed_replay_start_min": str(allowed_min)})
    return {
        "ok": True,
        "model_id": model_id,
        "strategy_rule": strategy_rule,
        "requested_start": start,
        "requested_end": end,
        "allowed_replay_start_min": str(allowed_min),
        "latest_available_signal_date": str(latest),
        "backend_window_validator_exists": True,
        "model_training_windows_traceable": bool(meta.get("source_manifest") and meta.get("source_training_report")),
        "training_overlap_rejected": True,
    }


def _load_index_entry(model_id: str, strategy_rule: str, start: str, end: str) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    try:
        index_payload = replay_index.load_readonly_replay_window_index()
    except replay_index.ReadonlyReplayWindowIndexError as exc:
        raise ReadonlyReplayWindowError(exc.status, exc.message, exc.details) from exc
    matched = None
    for row in index_payload.get("windows", []):
        if str(row.get("model_id")) == model_id and str(row.get("strategy_rule")) == strategy_rule and str(row.get("start")) == start and str(row.get("end")) == end:
            matched = row
            break
    if matched is None:
        raise ReadonlyReplayWindowError("no_audited_replay_artifact_for_window", "Requested replay window is not registered in D7 readonly replay window index", {"requested_model_id": model_id, "requested_strategy_rule": strategy_rule, "requested_start": start, "requested_end": end})
    raw_entry = None
    for row in (index_payload.get("manifest") or {}).get("windows", []):
        if row.get("window_key") == matched.get("window_key") and row.get("model_id") == matched.get("model_id") and row.get("strategy_rule") == matched.get("strategy_rule"):
            raw_entry = row
            break
    if raw_entry is None:
        raise ReadonlyReplayWindowError("index_entry_mismatch", "Readonly replay window index entry mismatch", {"window_key": matched.get("window_key")})
    artifact = _load_json(_resolve_repo_path(str(raw_entry.get("artifact_manifest", ""))))
    return index_payload, matched, raw_entry, artifact


def _artifact_flags_ok(window_type: str, artifact: dict[str, Any]) -> bool:
    common = artifact.get("readonly_only") is True and artifact.get("production_trade_enabled") is False
    if window_type == "fixed_standard":
        return common and artifact.get("artifact_type") == "readonly_standard_artifact_index" and artifact.get("schema_version") == "readonly_standard_artifact_index_d4_v1"
    if window_type == "generated_readonly":
        return (
            common
            and artifact.get("artifact_type") == "replay_result"
            and artifact.get("schema_version") == "readonly_replay_result_d6_v1"
            and artifact.get("not_generated_in_api_handler") is True
            and artifact.get("generated_by") == "replay_execution_engine"
            and artifact.get("decision_source") == "order_intent_artifact"
            and artifact.get("execution_input_source") == "order_intent_artifact"
        )
    return False


def _payload_from_index_entry(*, model_id: str, strategy_rule: str, start: str, end: str, validation: dict[str, Any]) -> dict[str, Any]:
    index_payload, entry, raw_entry, artifact = _load_index_entry(model_id, strategy_rule, start, end)
    window_type = str(entry.get("window_type"))
    if not _artifact_flags_ok(window_type, artifact):
        raise ReadonlyReplayWindowError("unsafe_replay_artifact", "Readonly replay artifact safety/source flags are invalid", {"manifest": entry.get("artifact_manifest")})
    checksum = entry.get("checksum") or {}
    if checksum.get("ok") is not True:
        raise ReadonlyReplayWindowError("checksum_failed", "Readonly replay artifact checksum validation failed", checksum)

    replay_manifest = artifact
    if window_type == "fixed_standard":
        replay_manifest = _load_json(_resolve_repo_path(str(artifact.get("order_intent_replay_result_manifest", ""))))
        parity_status = artifact.get("parity_status")
        row_counts = artifact.get("row_counts")
        generated_by = artifact.get("generated_by")
        decision_source = artifact.get("decision_source")
        execution_input_source = artifact.get("execution_input_source")
    else:
        parity_status = "not_applicable_indexed_generated_window"
        row_counts = artifact.get("row_counts")
        generated_by = artifact.get("generated_by")
        decision_source = artifact.get("decision_source")
        execution_input_source = artifact.get("execution_input_source")

    summary = _read_summary(replay_manifest, model_id, strategy_rule)
    return {
        "ok": True,
        "schema_version": "readonly_replay_window_api_d7r_v1",
        "readonly_only": True,
        "not_order": True,
        "no_order_action": True,
        "not_target_position": True,
        "not_investment_advice": True,
        "production_trade_enabled": False,
        "model_id": model_id,
        "strategy_rule": strategy_rule,
        "execution_price_mode": artifact.get("execution_price_mode") or replay_manifest.get("execution_price_mode") or "next_open",
        "window": {"name": entry.get("window_key"), "start": start, "end": end},
        "window_index": {"window_key": entry.get("window_key"), "window_type": window_type, "display_label": entry.get("display_label")},
        "validation": validation,
        "summary": summary,
        "parity_status": parity_status,
        "row_counts": row_counts,
        "generated_by": generated_by,
        "decision_source": decision_source,
        "execution_input_source": execution_input_source,
        "diagnostic_rule_excluded_from_valid_strategy_evidence": True,
        "checksum": checksum,
        "sources": {
            "readonly_replay_manifest": entry.get("artifact_manifest"),
            "window_index_manifest": index_payload.get("sources", {}).get("manifest"),
            "window_index_entry_manifest": raw_entry.get("artifact_manifest"),
            "order_intent_artifacts": artifact.get("order_intent_artifacts", []),
            "replay_window_policy": artifact.get("replay_window_policy") or raw_entry.get("sources", {}).get("replay_window_policy"),
            "standard_artifact_index_manifest": entry.get("artifact_manifest") if window_type == "fixed_standard" else None,
            "order_intent_replay_result_manifest": artifact.get("order_intent_replay_result_manifest") if window_type == "fixed_standard" else None,
        },
        "no_write_guarantees": {
            "read_only_http_method": True,
            "reads_indexed_audited_artifact_only": True,
            "fixed_window_requires_d7_index": True,
            "does_not_generate_replay_on_demand": True,
            "does_not_touch_provider_accepted_latest": True,
            "does_not_touch_monitor_or_alerts": True,
            "does_not_touch_broker_or_orders": True,
        },
    }


def load_readonly_replay_window(*, model_id: str, strategy_rule: str, start: str, end: str) -> dict[str, Any]:
    """Validate and return an audited readonly replay window result without generating new artifacts."""
    policy = _load_yaml(POLICY)
    validation = _window_validation(policy, model_id, strategy_rule, start, end)
    return _payload_from_index_entry(model_id=model_id, strategy_rule=strategy_rule, start=start, end=end, validation=validation)
