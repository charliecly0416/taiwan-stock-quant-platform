#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DIR = ROOT / "data_tw/experiments/extended_oos_qlib_orthogonal_ltr/portfolio_decision_optimizer_p4"
REQUIRED_FILES = [
    "manifest.json",
    "risk_filter_context.csv",
    "risk_filter_decisions.csv",
    "decision_explanations_with_risk.csv",
    "schema.json",
    "risk_filter_quality_audit.csv",
    "forbidden_input_semantics_audit.csv",
]
CONTEXT_FIELDS = {
    "asof_date",
    "instrument",
    "strategy_rule",
    "risk_context_source",
    "risk_context_asof",
    "risk_context_available_at",
    "market_regime",
    "position_risk_status",
    "candidate_risk_status",
    "risk_tag",
    "risk_tag_reason",
    "pit_safe",
    "source_manifest",
    "readonly_only",
    "simulation_only",
    "not_order",
    "not_target_position",
    "not_investment_advice",
}
DECISION_FIELDS = {
    "decision_date",
    "instrument",
    "base_decision_status",
    "base_primary_reason_code",
    "risk_tag",
    "risk_filter_action",
    "risk_filter_reason",
    "would_block_simulated_buy_small",
    "would_raise_confidence_gap",
    "manual_review_required",
    "keep_but_review",
    "strategy_rule",
    "readonly_only",
    "simulation_only",
    "not_order",
    "not_target_position",
    "not_investment_advice",
}
ADDED_EXPLANATION_FIELDS = {"risk_tag", "risk_filter_action", "risk_filter_reason", "risk_review_status"}
REQUIRED_FLAGS = ["readonly_only", "simulation_only", "not_order", "not_target_position", "not_investment_advice"]
ALLOWED_ACTIONS = {"none", "manual_review_required", "raise_confidence_gap", "block_simulated_buy_small", "keep_but_review"}
FORBIDDEN_ACTIONS = {"sell", "buy", "exit_full", "target_position", "target_weight", "order", "submit_order", "provider_publish", "accepted_latest_switch"}
FORBIDDEN_FIELDS = {
    "future_return",
    "future_excess_return",
    "forward_return",
    "label",
    "realized_pnl",
    "unrealized_pnl",
    "replay_return",
    "net_return",
    "gross_return",
    "target_position",
    "target_weight",
    "execution_quantity",
    "shares",
    "lots",
    "allocation_weight",
    "broker",
    "quick_trade",
    "order_id",
    "broker_order_id",
}
UNSAFE_TEXT = ["应买入", "应卖出", "该买", "该卖", "目标仓位", "目标权重", "保证收益", "上涨概率", "胜率", "买入概率", "自动买入", "自动卖出"]


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


def flags_true(rows: list[dict[str, str]]) -> bool:
    return all(str(row.get(flag, "")).lower() == "true" for row in rows for flag in REQUIRED_FLAGS)


def forbidden_field_hits(fields: set[str]) -> set[str]:
    hits: set[str] = set()
    for field in fields:
        lowered = field.lower()
        for forbidden in FORBIDDEN_FIELDS:
            if lowered == forbidden or lowered.startswith(forbidden + "_"):
                hits.add(field)
    return hits


def validate(out: Path) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    for filename in REQUIRED_FILES:
        checks.append(check(f"required_file_exists:{filename}", (out / filename).exists(), rel(out / filename)))
    if any(row["status"] == "fail" for row in checks):
        return {"ok": False, "artifact_dir": rel(out), "checks": checks}

    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    schema = json.loads((out / "schema.json").read_text(encoding="utf-8"))
    context = read_csv(out / "risk_filter_context.csv")
    decisions = read_csv(out / "risk_filter_decisions.csv")
    enriched = read_csv(out / "decision_explanations_with_risk.csv")
    quality = read_csv(out / "risk_filter_quality_audit.csv")
    forbidden_audit = read_csv(out / "forbidden_input_semantics_audit.csv")

    context_fields = set(context[0].keys()) if context else set()
    decision_fields = set(decisions[0].keys()) if decisions else set()
    enriched_fields = set(enriched[0].keys()) if enriched else set()
    all_fields = context_fields | decision_fields | enriched_fields
    action_values = {row.get("risk_filter_action", "") for row in decisions}
    text_blob = "\n".join(row.get("explanation_text_cn", "") for row in enriched)

    checks.append(check("output_not_under_data_tw_artifacts", not str(out.resolve()).startswith(str((ROOT / "data_tw/artifacts").resolve())), rel(out)))
    checks.append(check("manifest_readonly_flags", all(manifest.get(flag) is True for flag in REQUIRED_FLAGS), "manifest safety flags"))
    checks.append(check("manifest_forbidden_action_flags", all(manifest.get(key) is True for key in ["no_openai_call", "no_provider_publish", "no_accepted_latest_switch", "no_monitor_write", "no_broker_quick_trade_order"]), "manifest forbidden action flags"))
    checks.append(check("source_p2_manifest_experiment", "data_tw/experiments/" in str(manifest.get("source_p2_manifest", "")) and "portfolio_decision_optimizer_p2/manifest.json" in str(manifest.get("source_p2_manifest", "")), str(manifest.get("source_p2_manifest", ""))))
    checks.append(check("source_p3_manifest_experiment", "data_tw/experiments/" in str(manifest.get("source_p3_manifest", "")) and "portfolio_decision_optimizer_p3/manifest.json" in str(manifest.get("source_p3_manifest", "")), str(manifest.get("source_p3_manifest", ""))))
    checks.append(check("required_context_fields_present", CONTEXT_FIELDS.issubset(context_fields), ",".join(sorted(CONTEXT_FIELDS - context_fields))))
    checks.append(check("required_decision_fields_present", DECISION_FIELDS.issubset(decision_fields), ",".join(sorted(DECISION_FIELDS - decision_fields))))
    checks.append(check("enriched_added_fields_present", ADDED_EXPLANATION_FIELDS.issubset(enriched_fields), ",".join(sorted(ADDED_EXPLANATION_FIELDS - enriched_fields))))
    checks.append(check("row_counts_match", len(context) == len(decisions) == len(enriched) == int(manifest.get("row_count", -1)), f"context={len(context)}, decisions={len(decisions)}, enriched={len(enriched)}"))
    checks.append(check("row_level_flags_true", flags_true(context) and flags_true(decisions), "risk context and risk decisions safety flags"))
    checks.append(check("risk_context_asof_available_at_present", all(row.get("asof_date") and row.get("risk_context_asof") and row.get("risk_context_available_at") and row.get("source_manifest") for row in context), "asof/available_at/source_manifest"))
    checks.append(check("pit_safe_true", all(str(row.get("pit_safe", "")).lower() == "true" for row in context), "pit_safe must be true for emitted market-regime context"))
    checks.append(check("symbol_risk_not_declared", all(row.get("position_risk_status") == "not_declared" and row.get("candidate_risk_status") == "not_declared" and "symbol_risk:not_declared" in row.get("risk_tag", "") for row in context), "no invented per-symbol risk tag"))
    checks.append(check("risk_action_enum_allowed", action_values.issubset(ALLOWED_ACTIONS), ",".join(sorted(action_values - ALLOWED_ACTIONS))))
    checks.append(check("risk_action_forbidden_absent", not (action_values & FORBIDDEN_ACTIONS), ",".join(sorted(action_values & FORBIDDEN_ACTIONS))))
    hits = forbidden_field_hits(all_fields)
    checks.append(check("forbidden_fields_absent", not hits, ",".join(sorted(hits))))
    checks.append(check("forbidden_input_semantics_audit_pass", all(row.get("status") == "pass" for row in forbidden_audit), "forbidden_input_semantics_audit.csv"))
    checks.append(check("risk_filter_quality_audit_pass", all(row.get("status") == "pass" for row in quality), "risk_filter_quality_audit.csv"))
    checks.append(check("schema_required_fields_match", CONTEXT_FIELDS.issubset(set(schema.get("risk_filter_context_required_fields", []))) and DECISION_FIELDS.issubset(set(schema.get("risk_filter_decisions_required_fields", []))), "schema.json"))
    checks.append(check("schema_allowed_actions_match", set(schema.get("allowed_risk_filter_actions", [])) == ALLOWED_ACTIONS, "allowed action enum"))
    checks.append(check("p3_rank_fields_preserved", all(row.get("candidate_rank", "") == src.get("candidate_rank", "") and row.get("buy_score_bucket", "") == src.get("buy_score_bucket", "") for row, src in zip(enriched, read_csv(ROOT / "data_tw/experiments/extended_oos_qlib_orthogonal_ltr/portfolio_decision_optimizer_p3/decision_explanations.csv"))), "candidate_rank and buy_score_bucket unchanged"))
    checks.append(check("unsafe_explanation_text_absent", not any(term in text_blob for term in UNSAFE_TEXT), "no unsafe buy/sell/position/return semantics"))
    checks.append(check("no_data_tw_artifacts_output_paths", "data_tw/artifacts/" not in json.dumps(manifest.get("outputs", {}), ensure_ascii=False), "manifest outputs"))

    ok = all(row["status"] == "pass" for row in checks)
    return {"ok": ok, "artifact_dir": rel(out), "row_count": len(context), "check_count": len(checks), "checks": checks}


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate P4 RiskFilterArtifact for portfolio_decision_optimizer_v1.")
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
