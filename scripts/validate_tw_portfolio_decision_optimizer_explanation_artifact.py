#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DIR = ROOT / "data_tw/experiments/extended_oos_qlib_orthogonal_ltr/portfolio_decision_optimizer_p3"
REQUIRED_FILES = ["manifest.json", "decision_explanations.csv", "schema.json", "explanation_quality_audit.csv", "forbidden_semantics_audit.csv"]
REQUIRED_FIELDS = [
    "decision_date", "portfolio_state_asof", "instrument", "decision_status", "primary_reason_code",
    "secondary_reason_codes", "candidate_rank", "buy_score_bucket", "current_holding_flag",
    "holding_days", "rank_gap_vs_weakest_holding", "cost_gate_status", "turnover_budget_status",
    "regime_status", "execution_price_status", "readonly_disclaimer", "not_investment_advice",
]
REQUIRED_FLAGS = ["readonly_only", "simulation_only", "not_order", "not_target_position", "not_investment_advice"]
FORBIDDEN_FIELDS = {
    "target_position", "target_weight", "execution_quantity", "shares", "lots", "allocation_weight",
    "broker", "quick_trade", "order_id", "broker_order_id", "provider_publish_status",
    "accepted_latest_status", "monitor_write_status",
}
UNSAFE_TEXT = ["应买入", "应卖出", "目标仓位", "目标权重", "保证收益", "上涨概率", "胜率", "买入概率", "自动买入", "自动卖出"]
UNSAFE_BUCKET_TERMS = ["return", "probability", "win_rate", "position_size", "收益", "概率", "胜率", "仓位"]
ALLOWED_STATUSES = {
    "no_action", "blocked", "pending_execution_price", "simulated_buy_small", "simulated_reduce_partial",
    "keep_existing_position", "manual_review_required", "historical_executed_in_replay",
}


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except Exception:
        return str(path)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def check(name: str, ok: bool, details: str = "") -> dict[str, Any]:
    return {"name": name, "status": "pass" if ok else "fail", "details": details}


def validate(out: Path) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    for filename in REQUIRED_FILES:
        checks.append(check(f"required_file_exists:{filename}", (out / filename).exists(), rel(out / filename)))
    if any(c["status"] == "fail" for c in checks):
        return {"ok": False, "checks": checks}
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    schema = json.loads((out / "schema.json").read_text(encoding="utf-8"))
    rows = read_csv(out / "decision_explanations.csv")
    quality = read_csv(out / "explanation_quality_audit.csv")
    forbidden = read_csv(out / "forbidden_semantics_audit.csv")
    fields = set(rows[0].keys()) if rows else set()
    checks.append(check("output_not_under_data_tw_artifacts", not str(out.resolve()).startswith(str((ROOT / "data_tw/artifacts").resolve())), rel(out)))
    checks.append(check("manifest_readonly_flags", all(manifest.get(flag) is True for flag in REQUIRED_FLAGS), "manifest safety flags"))
    checks.append(check("manifest_source_p2_readonly_replay", "portfolio_decision_optimizer_p2/manifest.json" in str(manifest.get("source_p2_manifest", "")), str(manifest.get("source_p2_manifest", ""))))
    checks.append(check("required_fields_present", set(REQUIRED_FIELDS).issubset(fields), ",".join(sorted(set(REQUIRED_FIELDS) - fields))))
    checks.append(check("row_level_safety_flags_present", set(REQUIRED_FLAGS).issubset(fields), ",".join(sorted(set(REQUIRED_FLAGS) - fields))))
    checks.append(check("row_level_safety_flags_true", all(str(row.get(flag, "")).lower() == "true" for row in rows for flag in REQUIRED_FLAGS), "all rows carry readonly/simulation/not-order flags"))
    checks.append(check("forbidden_fields_absent", not (fields & FORBIDDEN_FIELDS), ",".join(sorted(fields & FORBIDDEN_FIELDS))))
    statuses = {row.get("decision_status", "") for row in rows}
    checks.append(check("decision_status_allowed", statuses.issubset(ALLOWED_STATUSES), ",".join(sorted(statuses - ALLOWED_STATUSES))))
    text_blob = "\n".join(row.get("explanation_text_cn", "") for row in rows)
    checks.append(check("unsafe_text_absent", not any(term in text_blob for term in UNSAFE_TEXT), "unsafe Chinese trading semantics absent"))
    bucket_blob = "\n".join(row.get("buy_score_bucket", "") for row in rows)
    checks.append(check("buy_score_bucket_safe_semantics", not any(term in bucket_blob for term in UNSAFE_BUCKET_TERMS), "bucket labels do not imply returns/probability/position"))
    checks.append(check("quality_audit_pass", all(row.get("status") == "pass" for row in quality), "explanation_quality_audit.csv"))
    checks.append(check("forbidden_semantics_audit_pass", all(row.get("status") == "pass" for row in forbidden), "forbidden_semantics_audit.csv"))
    checks.append(check("schema_required_fields_match", set(REQUIRED_FIELDS).issubset(set(schema.get("required_fields", []))), "schema.json"))
    checks.append(check("no_openai_call_declared", manifest.get("no_openai_call") is True, "manifest no_openai_call"))
    checks.append(check("no_provider_latest_monitor_broker_declared", all(manifest.get(k) is True for k in ["no_provider_publish", "no_accepted_latest_switch", "no_monitor_write", "no_broker_quick_trade_order"]), "manifest forbidden action flags"))
    ok = all(c["status"] == "pass" for c in checks)
    return {"ok": ok, "artifact_dir": rel(out), "row_count": len(rows), "check_count": len(checks), "checks": checks}


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate P3 DecisionExplanationArtifact for portfolio_decision_optimizer_v1.")
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
