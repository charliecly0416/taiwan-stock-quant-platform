#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DIR = ROOT / "data_tw/experiments/portfolio_decision_optimizer_b_q_qlib_only_oos_control"
REQUIRED_FILES = ["manifest.json", "p2_summary.csv", "p2_daily_nav.csv", "p2_actions.csv", "p2_order_intents_dry_run.csv", "p2_position_snapshots.csv", "p2_regime_segment_metrics.csv", "p2_yearly_metrics.csv", "p2_rolling_3m_metrics.csv", "p2_rolling_6m_metrics.csv", "p2_pnl_concentration.csv", "p2_symbol_turnover_concentration.csv", "p2_forbidden_input_output_audit.csv", "p2_coverage_audit.csv", "signal_usage_audit.csv", "OOS_boundary_audit.csv"]
REQUIRED_SUMMARY_FIELDS = {"window", "model_name", "model_family", "strategy_rule", "start_date", "end_date", "net_return_after_fee_tax", "gross_return", "max_drawdown", "action_count", "buy_count", "sell_count", "skip_count", "no_action_days", "blocked_days", "turnover_proxy", "fee_and_tax", "average_holding_days", "median_holding_days", "missing_next_open_count", "execution_block_count", "readonly_only", "simulation_only", "not_order", "not_target_position", "not_investment_advice"}
REQUIRED_WINDOWS = {"2023_2025_qlib_oos_control", "2026H1_qlib_reference"}
REQUIRED_STRATEGIES = {"top50_exit_one_worst_sell", "portfolio_decision_optimizer_v1"}
REQUIRED_FLAGS = ["readonly_only", "simulation_only", "not_order", "not_target_position", "not_investment_advice"]
FORBIDDEN_OUTPUT_FIELDS = {"target_position", "target_weight", "execution_quantity", "shares", "lots", "allocation_weight", "broker", "broker_order_id", "order_id", "quick_trade"}


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except Exception:
        return str(path)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def check(name: str, ok: bool, details: str = "") -> dict[str, Any]:
    return {"name": name, "status": "pass" if ok else "fail", "details": details}


def audit_pass(rows: list[dict[str, str]]) -> bool:
    return all(str(row.get("status", "")).lower() != "fail" for row in rows)


def validate(out: Path) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    for name in REQUIRED_FILES:
        checks.append(check(f"required_file_exists:{name}", (out / name).exists(), rel(out / name)))
    if any(row["status"] == "fail" for row in checks):
        return {"ok": False, "artifact_dir": rel(out), "checks": checks}
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    summary = read_csv(out / "p2_summary.csv")
    coverage = read_csv(out / "p2_coverage_audit.csv")
    forbidden = read_csv(out / "p2_forbidden_input_output_audit.csv")
    signal_usage = read_csv(out / "signal_usage_audit.csv")
    oos = read_csv(out / "OOS_boundary_audit.csv")
    order_intents = read_csv(out / "p2_order_intents_dry_run.csv")
    actions = read_csv(out / "p2_actions.csv")
    summary_fields = set(summary[0].keys()) if summary else set()
    windows = {row.get("window", "") for row in summary}
    strategies = {row.get("strategy_rule", "") for row in summary}
    order_fields = set(order_intents[0].keys()) if order_intents else set()
    action_fields = set(actions[0].keys()) if actions else set()
    forbidden_hits = (order_fields | action_fields) & FORBIDDEN_OUTPUT_FIELDS
    checks.append(check("output_not_under_data_tw_artifacts", not str(out.resolve()).startswith(str((ROOT / "data_tw/artifacts").resolve())), rel(out)))
    checks.append(check("artifact_type", manifest.get("artifact_type") == "portfolio_decision_optimizer_bq_qlib_only_oos_control_replay", str(manifest.get("artifact_type"))))
    checks.append(check("qlib_only_model", manifest.get("model_name") == "frozen_qlib_2018_2022" and manifest.get("model_family") == "qlib", f"{manifest.get('model_name')} {manifest.get('model_family')}"))
    checks.append(check("signal_manifest", "data_tw/artifacts/signals/frozen_qlib_2018_2022" in str(manifest.get("signal_manifest", "")), str(manifest.get("signal_manifest", ""))))
    checks.append(check("required_summary_fields", REQUIRED_SUMMARY_FIELDS.issubset(summary_fields), ",".join(sorted(REQUIRED_SUMMARY_FIELDS - summary_fields))))
    checks.append(check("summary_windows", windows == REQUIRED_WINDOWS, ",".join(sorted(windows))))
    checks.append(check("summary_strategy_pairs", strategies == REQUIRED_STRATEGIES and len(summary) == 4, f"rows={len(summary)} strategies={strategies}"))
    checks.append(check("row_level_flags_true", all(str(row.get(flag, "")).lower() == "true" for row in summary for flag in REQUIRED_FLAGS), "summary flags"))
    checks.append(check("coverage_windows", {row.get("window", "") for row in coverage} == REQUIRED_WINDOWS, ",".join(row.get("window", "") for row in coverage)))
    checks.append(check("coverage_pass", audit_pass(coverage), "p2_coverage_audit.csv"))
    checks.append(check("forbidden_audit_pass", audit_pass(forbidden), "p2_forbidden_input_output_audit.csv"))
    checks.append(check("signal_usage_audit_pass", audit_pass(signal_usage), "signal_usage_audit.csv"))
    checks.append(check("oos_boundary_audit_pass", audit_pass(oos), "OOS_boundary_audit.csv"))
    checks.append(check("forbidden_output_fields_absent", not forbidden_hits, ",".join(sorted(forbidden_hits))))
    checks.append(check("manifest_forbidden_action_flags", all(manifest.get(key) is True for key in ["readonly_only", "simulation_only", "not_order", "not_target_position", "not_investment_advice", "no_provider_publish", "no_accepted_latest_switch", "no_monitor_write", "no_broker_quick_trade_order", "no_training", "no_ltr_artifact_repair", "no_score_recompute", "no_p5"]), "manifest forbidden flags"))
    checks.append(check("candidate_freeze_not_result_selected", (manifest.get("candidate_freeze") or {}).get("no_replay_result_selection") is True and (manifest.get("candidate_freeze") or {}).get("no_post_replay_rule_adjustment") is True, "candidate freeze"))
    ok = all(row["status"] == "pass" for row in checks)
    return {"ok": ok, "artifact_dir": rel(out), "row_count": len(summary), "check_count": len(checks), "checks": checks}


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Branch B-Q qlib-only OOS control replay artifact.")
    parser.add_argument("--artifact-dir", default=str(DEFAULT_DIR))
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    payload = validate(Path(args.artifact_dir))
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print("ok=" + str(payload["ok"]).lower())
        print("check_count=" + str(payload.get("check_count", 0)))
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
