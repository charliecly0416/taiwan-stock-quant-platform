#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_VALIDATION = ROOT / "data_tw/catalog/dng6_daily_readiness_dashboard_validation.json"

REQUIRED_FIELDS = [
    "schema_version",
    "generated_at",
    "asof",
    "provider_raw_latest_by_dataset",
    "normalized_latest_by_dataset",
    "price_store_latest",
    "feature_store_latest",
    "qlib_accepted_latest",
    "model_signal_latest_by_model",
    "readonly_snapshot_latest",
    "agent_prompt_latest",
    "pending_asof",
    "provider_quota_status",
    "holiday_status",
    "next_retry_hint",
    "readiness_by_layer",
    "route_dependency_summary",
    "known_blockers",
    "allowed_next_steps",
    "forbidden_actions_audit",
]

LATEST_FIELDS = [
    "price_store_latest",
    "feature_store_latest",
    "qlib_accepted_latest",
    "readonly_snapshot_latest",
    "agent_prompt_latest",
]

REQUIRED_READINESS_LAYERS = ["price", "market", "orthogonal", "bundle", "route_dependency"]

FORBIDDEN_ACTION_KEYS = [
    "real_data_fetch_triggered",
    "provider_refresh_triggered",
    "provider_publish_triggered",
    "qlib_accepted_latest_switched",
    "readonly_latest_published",
    "agent_prompt_published",
    "model_training_triggered",
    "model_inference_triggered",
    "model_score_generation_triggered",
    "strategy_replay_triggered",
    "replay_result_nav_generated",
    "broker_order_quick_trade_triggered",
    "target_position_or_weight_generated",
]

NOT_PRODUCTION_STATUSES = {
    "PARTIAL",
    "PARTIAL_READY",
    "BLOCK",
    "BLOCKED",
    "BLOCKED_FOR_MODEL_B_LTR",
    "BLOCKED_OR_PARTIAL_NOT_PRODUCTION_READY",
    "MISSING",
    "STALE",
    "RESEARCH_ONLY",
    "TEMPORARY_BRIDGE",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except Exception:
        return str(path)


def resolve(path_text: str | Path) -> Path:
    path = Path(path_text)
    return path if path.is_absolute() else ROOT / path


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def issue(code: str, message: str, field: str = "", severity: str = "error") -> dict[str, str]:
    return {
        "severity": severity,
        "code": code,
        "message": message,
        "field": field,
    }


def status_is_not_production_ready(status: str) -> bool:
    normalized = str(status or "").upper()
    return normalized in NOT_PRODUCTION_STATUSES or normalized.startswith("BLOCK")


def validate_dashboard(path: Path) -> dict[str, Any]:
    errors: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []
    dashboard = read_json(path)
    if not isinstance(dashboard, dict):
        errors.append(issue("dashboard_not_object", "dashboard must be a JSON object"))
        dashboard = {}

    for field in REQUIRED_FIELDS:
        if field not in dashboard:
            errors.append(issue("required_field_missing", f"{field} is required", field))

    latest_concepts = dashboard.get("latest_concepts") if isinstance(dashboard.get("latest_concepts"), dict) else {}
    for field in LATEST_FIELDS:
        value = dashboard.get(field)
        if not isinstance(value, dict):
            errors.append(issue("latest_field_not_object", f"{field} must be an object", field))
            continue
        for subfield in ["asof", "status", "path", "status_reason"]:
            if subfield not in value:
                errors.append(issue("latest_subfield_missing", f"{field}.{subfield} is required", f"{field}.{subfield}"))
    for concept in [
        "provider_raw_latest",
        "normalized_latest",
        "price_store_latest",
        "feature_store_latest",
        "qlib_accepted_latest",
        "model_signal_latest",
        "readonly_snapshot_latest",
        "agent_prompt_latest",
    ]:
        if concept not in latest_concepts:
            errors.append(issue("latest_concept_missing", f"{concept} missing from latest_concepts", f"latest_concepts.{concept}"))

    if not isinstance(dashboard.get("provider_raw_latest_by_dataset"), dict):
        errors.append(issue("provider_latest_not_object", "provider_raw_latest_by_dataset must be an object", "provider_raw_latest_by_dataset"))
    if not isinstance(dashboard.get("normalized_latest_by_dataset"), dict):
        errors.append(issue("normalized_latest_not_object", "normalized_latest_by_dataset must be an object", "normalized_latest_by_dataset"))
    if not isinstance(dashboard.get("model_signal_latest_by_model"), dict):
        errors.append(issue("model_signal_latest_not_object", "model_signal_latest_by_model must be an object", "model_signal_latest_by_model"))

    readiness = dashboard.get("readiness_by_layer") if isinstance(dashboard.get("readiness_by_layer"), dict) else {}
    for layer in REQUIRED_READINESS_LAYERS:
        if layer not in readiness:
            errors.append(issue("readiness_layer_missing", f"{layer} must exist in readiness_by_layer", f"readiness_by_layer.{layer}"))
            continue
        if not isinstance(readiness[layer], dict):
            errors.append(issue("readiness_layer_not_object", f"{layer} readiness must be an object", f"readiness_by_layer.{layer}"))
            continue
        layer_status = str(readiness[layer].get("status") or "")
        if status_is_not_production_ready(layer_status) and readiness[layer].get("production_ready") is True:
            errors.append(issue("partial_block_marked_production_ready", f"{layer} has status={layer_status} but production_ready=true", f"readiness_by_layer.{layer}.production_ready"))

    if dashboard.get("production_ready") is True:
        blocking_layers = [
            layer
            for layer, payload in readiness.items()
            if isinstance(payload, dict) and status_is_not_production_ready(str(payload.get("status") or ""))
        ]
        if blocking_layers or dashboard.get("known_blockers"):
            errors.append(issue("dashboard_marked_production_ready", f"dashboard production_ready=true with blockers/layers={blocking_layers}", "production_ready"))

    route_summary = dashboard.get("route_dependency_summary") if isinstance(dashboard.get("route_dependency_summary"), dict) else {}
    if route_summary.get("all_gate_pass") is not False:
        warnings.append(issue("route_gate_not_false", "DNG6 expected DNG5 all_gate_pass=false for current evidence", "route_dependency_summary.all_gate_pass", "warning"))
    for route_id, payload in (route_summary.get("routes") or {}).items():
        if isinstance(payload, dict) and payload.get("gate_pass") is False and payload.get("production_ready") is True:
            errors.append(issue("route_block_marked_production_ready", f"{route_id} gate_pass=false but production_ready=true", f"route_dependency_summary.routes.{route_id}.production_ready"))

    audit = dashboard.get("forbidden_actions_audit") if isinstance(dashboard.get("forbidden_actions_audit"), dict) else {}
    actions = audit.get("actions") if isinstance(audit.get("actions"), dict) else {}
    for key in FORBIDDEN_ACTION_KEYS:
        if key not in actions:
            errors.append(issue("forbidden_action_key_missing", f"{key} missing from forbidden action audit", f"forbidden_actions_audit.actions.{key}"))
        elif actions.get(key) is not False:
            errors.append(issue("forbidden_action_triggered", f"{key} must be false", f"forbidden_actions_audit.actions.{key}"))
    if audit.get("all_false") is not True:
        errors.append(issue("forbidden_action_audit_not_all_false", "forbidden_actions_audit.all_false must be true", "forbidden_actions_audit.all_false"))

    allowed_next_steps = dashboard.get("allowed_next_steps")
    if not isinstance(allowed_next_steps, list) or not allowed_next_steps:
        errors.append(issue("allowed_next_steps_missing", "allowed_next_steps must be a non-empty list", "allowed_next_steps"))
    known_blockers = dashboard.get("known_blockers")
    if not isinstance(known_blockers, list):
        errors.append(issue("known_blockers_not_list", "known_blockers must be a list", "known_blockers"))

    status_counts = Counter(
        str(payload.get("status") or "")
        for payload in readiness.values()
        if isinstance(payload, dict)
    )
    ok = not errors
    return {
        "schema_version": "v1.dng6.daily_readiness_dashboard.validation",
        "generated_at": utc_now(),
        "ok": ok,
        "status": "PASS" if ok else "FAIL",
        "dashboard": rel(path),
        "dashboard_status": dashboard.get("dashboard_status", ""),
        "production_ready": bool(dashboard.get("production_ready")),
        "readiness_layer_status_counts": dict(sorted(status_counts.items())),
        "route_dependency_all_gate_pass": bool(route_summary.get("all_gate_pass")),
        "forbidden_actions_all_false": audit.get("all_false") is True,
        "error_count": len(errors),
        "warning_count": len(warnings),
        "errors": errors,
        "warnings": warnings,
        "checked_requirements": [
            "DNG6 required fields",
            "latest concept completeness",
            "readiness_by_layer includes price/market/orthogonal/bundle/route_dependency",
            "partial/block/missing evidence is not marked production ready",
            "forbidden action audit keys all false",
            "JSON output contract",
        ],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate the DNG6 Taiwan daily readiness dashboard.")
    parser.add_argument("--dashboard", default="data_tw/catalog/daily_readiness_dashboard.json")
    parser.add_argument("--output", default=str(DEFAULT_VALIDATION.relative_to(ROOT)))
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = validate_dashboard(resolve(args.dashboard))
    if args.output:
        write_json(resolve(args.output), report)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"{report['status']} {report['dashboard']} errors={report['error_count']}")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
