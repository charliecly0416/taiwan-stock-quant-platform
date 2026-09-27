#!/usr/bin/env python3
"""Validate DNG11 observation and blocker burn-down artifacts.

This validator is intentionally static: it only reads local DNG11 outputs and
does not call provider, model, replay, publish, or trading code paths.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


REQUIRED_BLOCKERS = {
    "formal_qlib_accepted_latest_stale",
    "model_signal_latest_stale",
    "agent_prompt_latest_missing",
    "model_b_ltr_blocked_by_orthogonal_data",
    "monthly_revenue_blocked_quota",
    "valuation_blocked_quota",
    "corporate_actions_not_daily_feature_ready",
    "replay_shadow_next_day_execution_pending",
    "production_publish_not_authorized",
    "multi_day_observation_insufficient",
}

FORBIDDEN_ACTION_KEYS = {
    "real_data_fetch_triggered",
    "provider_refresh_triggered",
    "provider_publish_triggered",
    "qlib_accepted_latest_switched",
    "readonly_latest_published",
    "agent_prompt_published",
    "model_training_triggered",
    "model_tuning_triggered",
    "model_score_generated",
    "ltr_score_generated",
    "strategy_replay_triggered",
    "replay_result_nav_generated",
    "broker_order_quick_trade_triggered",
    "target_position_or_weight_generated",
}


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def validate(
    observation_path: Path,
    burn_down_path: Path,
    report_path: Path,
) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    obs = load_json(observation_path)

    for key in [
        "schema_version",
        "generated_at",
        "scope",
        "single_day_chain_ready",
        "multi_day_observation_ready",
        "observed_trade_days",
        "required_additional_trade_days",
        "recommendation",
        "forbidden_actions_audit",
        "dng0_to_dng10_summary",
    ]:
        if key not in obs:
            errors.append(f"missing observation field: {key}")

    observed_days = obs.get("observed_trade_days", [])
    if not isinstance(observed_days, list):
        errors.append("observed_trade_days must be a list")
        observed_days = []

    if obs.get("multi_day_observation_ready") is True and len(observed_days) < 5:
        errors.append("multi_day_observation_ready cannot be true with fewer than 5 observed trade days")

    if obs.get("single_day_chain_ready") is not True:
        errors.append("DNG11 expected single_day_chain_ready=true for current evidence package")

    required_additional = obs.get("required_additional_trade_days")
    if isinstance(required_additional, int) and required_additional < 0:
        errors.append("required_additional_trade_days must be non-negative")

    recommendation = obs.get("recommendation")
    allowed_recommendations = {
        "PASS_SINGLE_DAY_CHAIN_GO_DNG12_DESIGN_ONLY",
        "PASS_MULTI_DAY_OBSERVATION_GO_DNG12_GO_NO_GO",
        "BLOCKED_WAIT_MORE_TRADE_DAYS",
        "FAIL_NEEDS_REPAIR",
    }
    if recommendation not in allowed_recommendations:
        errors.append(f"invalid recommendation: {recommendation}")

    audit = obs.get("forbidden_actions_audit", {})
    actions = audit.get("actions", {}) if isinstance(audit, dict) else {}
    missing_action_keys = sorted(FORBIDDEN_ACTION_KEYS - set(actions))
    if missing_action_keys:
        errors.append(f"missing forbidden action keys: {','.join(missing_action_keys)}")
    true_actions = sorted(k for k, v in actions.items() if v is True)
    if true_actions:
        errors.append(f"forbidden actions marked true: {','.join(true_actions)}")
    if audit.get("all_false") is not True:
        errors.append("forbidden_actions_audit.all_false must be true")

    if not burn_down_path.exists():
        errors.append(f"missing burn-down csv: {burn_down_path}")
        rows: list[dict[str, str]] = []
    else:
        with burn_down_path.open("r", encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f))
        if not rows:
            errors.append("burn-down csv has no rows")

    blocker_ids = {row.get("blocker_id", "") for row in rows}
    missing_blockers = sorted(REQUIRED_BLOCKERS - blocker_ids)
    if missing_blockers:
        errors.append(f"missing required blockers: {','.join(missing_blockers)}")

    for row in rows:
        if row.get("status") == "CLOSED" and row.get("blocks_multi_day_observation") == "true":
            warnings.append(f"closed blocker still marked as blocking multi-day observation: {row.get('blocker_id')}")

    if not report_path.exists():
        errors.append(f"missing execution report: {report_path}")
        report_text = ""
    else:
        report_text = report_path.read_text(encoding="utf-8")

    for required_text in [
        "single_day_chain_ready=true",
        "multi_day_observation_ready=false",
        "required_additional_trade_days=4",
        str(recommendation),
    ]:
        if required_text and required_text not in report_text:
            errors.append(f"execution report missing text: {required_text}")

    return {
        "schema_version": "v1.dng11.observation.validation",
        "ok": not errors,
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "warnings": warnings,
        "observation_path": str(observation_path),
        "burn_down_path": str(burn_down_path),
        "report_path": str(report_path),
        "observed_trade_day_count": len(observed_days),
        "required_blocker_count": len(REQUIRED_BLOCKERS),
        "burn_down_row_count": len(rows),
        "recommendation": recommendation,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--observation", default="data_tw/catalog/dng11_multi_day_observation.json")
    parser.add_argument("--burn-down", default="data_tw/catalog/dng11_blocker_burn_down.csv")
    parser.add_argument("--report", default="docs/tw_data_governance/DNG11_MULTI_DAY_OBSERVATION_EXECUTION_REPORT_CN.md")
    parser.add_argument("--output", default="data_tw/catalog/dng11_multi_day_observation_validation.json")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    result = validate(Path(args.observation), Path(args.burn_down), Path(args.report))
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"status={result['status']} ok={result['ok']} errors={len(result['errors'])}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
