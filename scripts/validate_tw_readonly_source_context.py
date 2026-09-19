#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

ASOF = "2026-06-25"
STRATEGY_BUNDLE = ROOT / "data_tw/artifacts/strategy_input_bundles/top50_exit_one_worst_sell_dng10_modela/dng10_strategy_input_bundle_20260625"
READONLY_CONTEXT = ROOT / "data_tw/artifacts/readonly_source_context/dng10_modela_20260625"
AGENT_CONTEXT = ROOT / "data_tw/artifacts/agent_daily_prompt_source_context/dng10_modela_20260625"
CATALOG_VALIDATION = ROOT / "data_tw/catalog/dng10_strategy_readonly_context_validation.json"

FORBIDDEN_ACTION_KEYS = [
    "real_data_fetch_triggered",
    "provider_refresh_triggered",
    "provider_publish_triggered",
    "qlib_accepted_latest_switched",
    "readonly_latest_published",
    "agent_prompt_published",
    "model_training_triggered",
    "model_tuning_triggered",
    "model_inference_triggered",
    "model_score_generated",
    "ltr_score_generated",
    "strategy_replay_triggered",
    "replay_result_nav_generated",
    "broker_order_quick_trade_triggered",
    "target_position_or_weight_generated",
]
FORBIDDEN_EXACT_FIELDS = {
    "target_position",
    "target_weight",
    "allocation_weight",
    "execution_price",
    "execution_quantity",
    "broker",
    "broker_order_id",
    "order_id",
    "quick_trade",
    "cash_after",
    "nav",
    "equity",
    "daily_return",
    "realized_pnl",
    "unrealized_pnl",
    "replay_return",
    "total_return",
    "max_drawdown",
}
FORBIDDEN_PREFIXES = ("future_return_", "future_excess_return_", "forward_return_", "label_")
FORBIDDEN_FILES = {
    "summary.csv",
    "actions.csv",
    "daily_nav.csv",
    "position_snapshots.csv",
    "order_intents.csv",
    "target_positions.csv",
    "target_weights.csv",
    "latest.json",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rel(path: Path | str) -> str:
    path_obj = Path(path)
    try:
        return str(path_obj.resolve().relative_to(ROOT.resolve()))
    except (FileNotFoundError, ValueError):
        return str(path)


def read_json(path: Path, errors: list[str]) -> dict[str, Any]:
    if not path.exists():
        errors.append(f"missing json: {rel(path)}")
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        errors.append(f"invalid json {rel(path)}: {exc}")
        return {}
    if not isinstance(payload, dict):
        errors.append(f"json must be object: {rel(path)}")
        return {}
    return payload


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def csv_header_and_count(path: Path, errors: list[str]) -> tuple[list[str], int]:
    if not path.exists():
        errors.append(f"missing csv: {rel(path)}")
        return [], 0
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle)
        try:
            header = next(reader)
        except StopIteration:
            return [], 0
        return header, sum(1 for _ in reader)


def forbidden_columns(header: list[str]) -> list[str]:
    found = [field for field in header if field in FORBIDDEN_EXACT_FIELDS]
    found.extend(field for field in header if any(field.startswith(prefix) for prefix in FORBIDDEN_PREFIXES))
    return sorted(set(found))


def validate_flags(label: str, payload: dict[str, Any], errors: list[str]) -> None:
    flags = payload.get("forbidden_action_flags", {})
    if not isinstance(flags, dict):
        errors.append(f"{label}.forbidden_action_flags missing")
        return
    for key in FORBIDDEN_ACTION_KEYS:
        if flags.get(key) is not False:
            errors.append(f"{label}.forbidden_action_flags.{key} must be false")


def require_true(label: str, payload: dict[str, Any], key: str, errors: list[str]) -> None:
    if payload.get(key) is not True:
        errors.append(f"{label}.{key} must be true")


def require_false(label: str, payload: dict[str, Any], key: str, errors: list[str]) -> None:
    if payload.get(key) is not False:
        errors.append(f"{label}.{key} must be false")


def validate_manifest_common(label: str, payload: dict[str, Any], errors: list[str]) -> None:
    if payload.get("signal_asof") != ASOF and payload.get("asof") != ASOF:
        errors.append(f"{label} signal/asof must be {ASOF}")
    for key in ["readonly_only", "not_order", "no_target_position", "no_target_weight"]:
        if key in payload and payload.get(key) is not True:
            errors.append(f"{label}.{key} must be true")
    for key in ["latest_pointer_updated", "readonly_latest_updated", "agent_prompt_latest_updated"]:
        if key in payload and payload.get(key) is not False:
            errors.append(f"{label}.{key} must be false")
    if payload.get("model_a_ready") is not True and label != "strategy_manifest":
        errors.append(f"{label}.model_a_ready must be true")
    if payload.get("model_b_ltr_ready") is not False:
        errors.append(f"{label}.model_b_ltr_ready must be false")
    if payload.get("fallback_model") != "qlib_only_model_a":
        errors.append(f"{label}.fallback_model must be qlib_only_model_a")
    validate_flags(label, payload, errors)


def validate_strategy(errors: list[str], warnings: list[str]) -> dict[str, Any]:
    required_files = [
        "manifest.json",
        "signals.csv",
        "current_holdings.csv",
        "price_context.csv",
        "market_context.csv",
        "calendar.csv",
        "dependency_readiness.json",
        "lineage.json",
        "validator_report.json",
    ]
    for name in required_files:
        if not (STRATEGY_BUNDLE / name).exists():
            errors.append(f"missing strategy bundle file: {rel(STRATEGY_BUNDLE / name)}")

    manifest = read_json(STRATEGY_BUNDLE / "manifest.json", errors)
    dependency = read_json(STRATEGY_BUNDLE / "dependency_readiness.json", errors)
    lineage = read_json(STRATEGY_BUNDLE / "lineage.json", errors)
    validate_manifest_common("strategy_manifest", manifest, errors)
    if manifest.get("artifact_type") != "strategy_input_bundle":
        errors.append("strategy_manifest.artifact_type must be strategy_input_bundle")
    if manifest.get("status") != "READY_FOR_SOURCE_CONTEXT_DRY_RUN":
        errors.append("strategy_manifest.status must be READY_FOR_SOURCE_CONTEXT_DRY_RUN")
    if manifest.get("signal_asof") != ASOF or manifest.get("model_signal_asof") != ASOF:
        errors.append("strategy_manifest signal_asof/model_signal_asof must be 2026-06-25")
    require_true("strategy_manifest", manifest, "model_a_ready", errors)
    require_false("strategy_manifest", manifest, "model_b_ltr_ready", errors)
    require_true("strategy_manifest", manifest, "not_replay_result", errors)
    validate_flags("dependency_readiness", dependency, errors)
    if dependency.get("can_continue_to_source_context") is not True:
        errors.append("dependency_readiness.can_continue_to_source_context must be true")
    for key in ["can_continue_to_order_intent", "can_continue_to_replay", "can_continue_to_publish_latest"]:
        if dependency.get(key) is not False:
            errors.append(f"dependency_readiness.{key} must be false")
    if dependency.get("model_b_ltr_ready") is not False:
        errors.append("dependency_readiness.model_b_ltr_ready must be false")
    if lineage.get("lineage_type") != "local_source_context_bundle_no_fetch_no_score_no_order":
        errors.append("lineage.lineage_type must be local_source_context_bundle_no_fetch_no_score_no_order")
    validate_flags("lineage", lineage, errors)

    csv_results: dict[str, Any] = {}
    for name in ["signals", "current_holdings", "price_context", "market_context", "calendar"]:
        header, rows = csv_header_and_count(STRATEGY_BUNDLE / f"{name}.csv", errors)
        bad = forbidden_columns(header)
        if bad:
            errors.append(f"{rel(STRATEGY_BUNDLE / f'{name}.csv')} contains forbidden fields: {bad}")
        csv_results[name] = {"row_count": rows, "forbidden_columns": bad}
    if csv_results.get("signals", {}).get("row_count") != 150:
        errors.append("strategy signals.csv row_count must be 150")
    for name in ["price_context", "market_context", "calendar"]:
        if csv_results.get(name, {}).get("row_count", 0) <= 0:
            errors.append(f"strategy {name}.csv row_count must be > 0")
    warnings.append("current_holdings.csv is a DNG10 placeholder; no OrderIntentArtifact generated")
    return {"manifest": manifest, "row_counts": {key: value["row_count"] for key, value in csv_results.items()}}


def validate_source_context_dir(label: str, root: Path, context_name: str, errors: list[str]) -> dict[str, Any]:
    manifest = read_json(root / "manifest.json", errors)
    context = read_json(root / context_name, errors)
    validate_manifest_common(f"{label}_manifest", manifest, errors)
    validate_flags(f"{label}_context", context, errors)
    if context.get("signal_asof") and context.get("signal_asof") != ASOF:
        errors.append(f"{label}_context.signal_asof must be {ASOF}")
    safety = context.get("safety") or {}
    if safety:
        for key in ["readonly_only", "not_order", "not_target_position", "not_target_weight"]:
            if safety.get(key) is not True:
                errors.append(f"{label}_context.safety.{key} must be true")
    model_context = context.get("model_context") or {}
    if model_context.get("model_a_ready") is not True:
        errors.append(f"{label}_context.model_context.model_a_ready must be true")
    if model_context.get("model_b_ltr_ready") is not False:
        errors.append(f"{label}_context.model_context.model_b_ltr_ready must be false")
    if model_context.get("fallback_model") != "qlib_only_model_a":
        errors.append(f"{label}_context.model_context.fallback_model must be qlib_only_model_a")
    if "BLOCKED_INPUT_NOT_READY" not in json.dumps(context, ensure_ascii=False):
        errors.append(f"{label}_context must expose Model B BLOCKED_INPUT_NOT_READY")
    serialized = json.dumps(context, ensure_ascii=False)
    for allowed in ("not_target_position", "target_position_or_weight_generated", "target_position_request"):
        serialized = serialized.replace(allowed, "")
    if "target_position" in serialized:
        errors.append(f"{label}_context contains target_position outside safety flag")
    return {"manifest": manifest, "context": context}


def validate_no_forbidden_files(errors: list[str]) -> None:
    roots = [STRATEGY_BUNDLE, READONLY_CONTEXT, AGENT_CONTEXT]
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if path.is_file() and path.name in FORBIDDEN_FILES:
                errors.append(f"forbidden DNG10 output file present: {rel(path)}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate DNG10 StrategyInputBundle and readonly/Agent source context dry-run artifacts.")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    errors: list[str] = []
    warnings: list[str] = []
    strategy = validate_strategy(errors, warnings)
    readonly = validate_source_context_dir("readonly", READONLY_CONTEXT, "context.json", errors)
    agent = validate_source_context_dir("agent", AGENT_CONTEXT, "prompt_source_context.json", errors)
    validate_no_forbidden_files(errors)

    validation = {
        "schema_version": "v1.dng10.strategy_readonly_context.validation",
        "generated_at": utc_now(),
        "ok": not errors,
        "status": "PASS" if not errors else "BLOCKED_VALIDATOR",
        "errors": errors,
        "warnings": warnings,
        "signal_asof": ASOF,
        "model_a_ready": True,
        "model_b_ltr_ready": False,
        "fallback_model": "qlib_only_model_a",
        "latest_pointer_updated": False,
        "readonly_latest_updated": False,
        "agent_prompt_latest_updated": False,
        "not_order": True,
        "not_target_position": True,
        "not_target_weight": True,
        "not_replay_result": True,
        "strategy_input_bundle": {
            "root": rel(STRATEGY_BUNDLE),
            "manifest": rel(STRATEGY_BUNDLE / "manifest.json"),
            "row_counts": strategy.get("row_counts", {}),
            "status": (strategy.get("manifest") or {}).get("status"),
        },
        "readonly_source_context": {
            "root": rel(READONLY_CONTEXT),
            "manifest": rel(READONLY_CONTEXT / "manifest.json"),
            "context": rel(READONLY_CONTEXT / "context.json"),
            "artifact_type": (readonly.get("manifest") or {}).get("artifact_type"),
        },
        "agent_daily_prompt_source_context": {
            "root": rel(AGENT_CONTEXT),
            "manifest": rel(AGENT_CONTEXT / "manifest.json"),
            "prompt_source_context": rel(AGENT_CONTEXT / "prompt_source_context.json"),
            "artifact_type": (agent.get("manifest") or {}).get("artifact_type"),
        },
        "forbidden_action_flags": {key: False for key in FORBIDDEN_ACTION_KEYS},
    }
    write_json(CATALOG_VALIDATION, validation)
    strategy_report = dict(validation)
    strategy_report["schema_version"] = "v1.dng10.strategy_input_bundle.validation"
    strategy_report["bundle_root"] = rel(STRATEGY_BUNDLE)
    write_json(STRATEGY_BUNDLE / "validator_report.json", strategy_report)

    if args.json:
        print(json.dumps(validation, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"ok={validation['ok']} status={validation['status']} errors={len(errors)} warnings={len(warnings)}")
    return 0 if validation["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
