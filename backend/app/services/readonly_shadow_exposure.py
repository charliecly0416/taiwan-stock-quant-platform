"""Read-only loader for MTRP8 shadow exposure artifacts."""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_STRATEGY_RULE = "top50_hold_rank_buffer_100"
MTRP8_ROOT = (
    REPO_ROOT
    / "data_tw/artifacts/shadow_readiness"
    / DEFAULT_STRATEGY_RULE
    / "mtrp8_shadow_review_readonly_exposure_design"
)
MTRP9_CONTRACT_ROOT = (
    REPO_ROOT
    / "data_tw/artifacts/shadow_readiness"
    / DEFAULT_STRATEGY_RULE
    / "mtrp9_readonly_exposure_implementation_contract"
)

FORBIDDEN_RESPONSE_FIELDS = {
    "target_position",
    "target_weight",
    "allocation_weight",
    "quantity",
    "shares",
    "lots",
    "broker",
    "broker_order_id",
    "order_id",
    "quick_trade",
    "provider_publish_status",
    "accepted_latest_status",
    "latest_pointer_mutation",
    "paper_apply_payload",
}


class ReadonlyShadowExposureError(Exception):
    """Raised when the MTRP8 readonly exposure cannot be served safely."""

    def __init__(self, status: str, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists() or not path.is_file():
        raise ReadonlyShadowExposureError("missing_artifact", f"Missing readonly artifact: {_rel(path)}")
    return json.loads(path.read_text(encoding="utf-8"))


def _load_csv(path: Path) -> list[dict[str, Any]]:
    if not path.exists() or not path.is_file():
        raise ReadonlyShadowExposureError("missing_artifact", f"Missing readonly artifact: {_rel(path)}")
    with path.open("r", encoding="utf-8", newline="") as f:
        return [dict(row) for row in csv.DictReader(f)]


def _csv_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"true", "1", "yes", "y"}:
        return True
    if text in {"false", "0", "no", "n"}:
        return False
    return None


def _csv_number(value: Any) -> Any:
    if value is None:
        return None
    text = str(value).strip()
    if text == "":
        return ""
    try:
        if "." not in text and "e" not in text.lower():
            return int(text)
        return float(text)
    except ValueError:
        return value


def _normalize_csv_row(row: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in row.items():
        boolean = _csv_bool(value)
        out[key] = boolean if boolean is not None else _csv_number(value)
    return out


def _validate_contract_flags(payload: dict[str, Any]) -> None:
    expected = {
        "readonly_only": True,
        "simulation_only": True,
        "not_order": True,
        "not_target_position": True,
        "not_investment_advice": True,
        "production_allowed": False,
        "production_ready": False,
        "default_switch_allowed": False,
        "paper_apply_allowed": False,
    }
    for key, value in expected.items():
        if payload.get(key) is not value:
            raise ReadonlyShadowExposureError("unsafe_flags", f"Unsafe readonly exposure flag: {key}")
    present_forbidden = sorted(field for field in FORBIDDEN_RESPONSE_FIELDS if field in payload)
    if present_forbidden:
        raise ReadonlyShadowExposureError("forbidden_response_field", f"Forbidden response fields present: {present_forbidden}")


def load_readonly_shadow_exposure(strategy_rule: str | None = None, include_rows: bool = True) -> dict[str, Any]:
    """Return the MTRP9 readonly-shadow-exposure API payload from MTRP8 artifacts only."""
    normalized_rule = (strategy_rule or DEFAULT_STRATEGY_RULE).strip() or DEFAULT_STRATEGY_RULE
    if normalized_rule != DEFAULT_STRATEGY_RULE:
        raise ReadonlyShadowExposureError("unknown_strategy_rule", f"Unknown readonly shadow strategy_rule: {normalized_rule}")

    manifest_path = MTRP8_ROOT / "manifest.json"
    validator_path = MTRP8_ROOT / "validator_report.json"
    exposure_path = MTRP8_ROOT / "readonly_exposure_index.csv"
    gate_path = MTRP8_ROOT / "shadow_review_gate.csv"
    citations_path = MTRP8_ROOT / "artifact_citation_map.csv"
    blockers_path = MTRP8_ROOT / "production_blocker_register.csv"
    schema_contract_path = MTRP9_CONTRACT_ROOT / "response_schema_contract.json"

    manifest = _load_json(manifest_path)
    validator = _load_json(validator_path)
    schema_contract = _load_json(schema_contract_path)
    all_rows = [_normalize_csv_row(row) for row in _load_csv(exposure_path)]
    gate_rows = [_normalize_csv_row(row) for row in _load_csv(gate_path)]
    citations = [_normalize_csv_row(row) for row in _load_csv(citations_path)]
    blockers = [_normalize_csv_row(row) for row in _load_csv(blockers_path)]
    open_blockers = [row for row in blockers if str(row.get("status", "")).strip().lower() == "open"]

    if manifest.get("strategy_candidate") != DEFAULT_STRATEGY_RULE:
        raise ReadonlyShadowExposureError("invalid_manifest", "MTRP8 manifest strategy candidate mismatch")
    if manifest.get("readonly_only") is not True or manifest.get("simulation_only") is not True:
        raise ReadonlyShadowExposureError("unsafe_manifest", "MTRP8 manifest readonly/simulation flags are not true")
    if manifest.get("production_allowed") is not False or manifest.get("production_ready") is not False:
        raise ReadonlyShadowExposureError("unsafe_manifest", "MTRP8 manifest production flags are not false")
    if validator.get("status") != "pass":
        raise ReadonlyShadowExposureError("validator_not_pass", "MTRP8 validator report is not pass")

    gate_pass = bool(gate_rows) and all(str(row.get("status", "")).strip().lower() == "pass" for row in gate_rows)
    payload: dict[str, Any] = {
        "ok": True,
        "status": "pass" if gate_pass else "review_required",
        "schema_version": schema_contract.get("schema_version", "mtrp9_readonly_shadow_exposure_api_v1"),
        "strategy_candidate": DEFAULT_STRATEGY_RULE,
        "baseline_strategy": manifest.get("baseline_strategy"),
        "readonly_only": True,
        "simulation_only": True,
        "not_order": True,
        "not_target_position": True,
        "not_investment_advice": True,
        "production_allowed": False,
        "production_ready": False,
        "default_switch_allowed": False,
        "paper_apply_allowed": False,
        "source_manifest": _rel(manifest_path),
        "gate": {
            "ok": gate_pass,
            "status": "pass" if gate_pass else "review_required",
            "rows": gate_rows,
            "validator": {
                "status": validator.get("status"),
                "verdict": validator.get("verdict"),
                "covered_shadow_signal_days": validator.get("covered_shadow_signal_days"),
                "open_production_blockers": validator.get("open_production_blockers"),
                "path": _rel(validator_path),
            },
        },
        "rows": all_rows if include_rows else [],
        "row_count": len(all_rows),
        "rows_included": bool(include_rows),
        "citations": citations,
        "open_blockers": open_blockers,
        "warnings": [
            "shadow observation only",
            "not investment advice",
            "does not connect broker",
            "does not submit orders",
            "paper_apply_allowed=false",
        ],
        "dates": {
            "covered_dates": manifest.get("covered_dates", []),
            "covered_shadow_signal_days": manifest.get("covered_shadow_signal_days"),
            "created_at": manifest.get("created_at"),
        },
        "sources": {
            "manifest": _rel(manifest_path),
            "validator": _rel(validator_path),
            "readonly_exposure_index": _rel(exposure_path),
            "shadow_review_gate": _rel(gate_path),
            "artifact_citation_map": _rel(citations_path),
            "production_blocker_register": _rel(blockers_path),
            "response_schema_contract": _rel(schema_contract_path),
        },
    }
    _validate_contract_flags(payload)
    return payload
