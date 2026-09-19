#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
P2_DIR = ROOT / "data_tw/experiments/extended_oos_qlib_orthogonal_ltr/portfolio_decision_optimizer_p2"
OUT_DIR = ROOT / "data_tw/experiments/extended_oos_qlib_orthogonal_ltr/portfolio_decision_optimizer_p3"
CANDIDATE_RULE = "portfolio_decision_optimizer_v1"
DISCLAIMER = "只读研究解释，不是投资建议，不连接券商，不提交真实订单。"
REQUIRED_FIELDS = [
    "decision_date",
    "portfolio_state_asof",
    "instrument",
    "decision_status",
    "primary_reason_code",
    "secondary_reason_codes",
    "candidate_rank",
    "buy_score_bucket",
    "current_holding_flag",
    "holding_days",
    "rank_gap_vs_weakest_holding",
    "cost_gate_status",
    "turnover_budget_status",
    "regime_status",
    "execution_price_status",
    "readonly_disclaimer",
    "not_investment_advice",
]
OPTIONAL_FIELDS = [
    "strategy_rule",
    "model_name",
    "source_order_intent_row_id",
    "source_replay_manifest",
    "explanation_text_cn",
    "evidence_fields",
    "manual_review_required",
    "readonly_only",
    "simulation_only",
    "not_order",
    "not_target_position",
]
FIELDS = REQUIRED_FIELDS + OPTIONAL_FIELDS
SCHEMA_FIELDS = {
    "decision_date": "Signal date that produced the explanation.",
    "portfolio_state_asof": "Readonly portfolio state as-of date used for explanation context.",
    "instrument": "TW symbol or PORTFOLIO for portfolio-level no-action explanations.",
    "decision_status": "Readonly explanation status; not a trading status.",
    "primary_reason_code": "Primary strategy reason code from P2 dry-run OrderIntent.",
    "secondary_reason_codes": "Pipe-delimited explanatory reason tags.",
    "candidate_rank": "Qlib candidate-rank audit value, never a probability or return.",
    "buy_score_bucket": "Discrete score/rank explanation bucket, never a return/probability/position size.",
    "current_holding_flag": "Whether the instrument appeared in replay position snapshots at or before the decision date.",
    "holding_days": "Latest replay holding-days audit value at or before decision date, if available.",
    "rank_gap_vs_weakest_holding": "Audit-only rank-gap proxy derived from available rank fields; not a return forecast.",
    "cost_gate_status": "Readonly cost/no-trade-buffer gate explanation status.",
    "turnover_budget_status": "Readonly turnover budget gate explanation status.",
    "regime_status": "Market-regime explanation status when available from P2 replay action rows.",
    "execution_price_status": "Execution readiness/execution audit status; no execution price value is emitted.",
    "readonly_disclaimer": "Mandatory readonly safety disclaimer.",
    "not_investment_advice": "Boolean safety flag.",
}
ALLOWED_STATUSES = {
    "no_action",
    "blocked",
    "pending_execution_price",
    "simulated_buy_small",
    "simulated_reduce_partial",
    "keep_existing_position",
    "manual_review_required",
    "historical_executed_in_replay",
}


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except Exception:
        return str(path)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        fields = sorted({k for row in rows for k in row}) if rows else ["status"]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def bucket(candidate_rank: str) -> str:
    try:
        rank = int(float(candidate_rank))
    except Exception:
        return "not_applicable"
    if rank <= 10:
        return "high_rank_signal"
    if rank <= 30:
        return "medium_rank_signal"
    return "low_rank_signal"


def to_int_text(value: str) -> str:
    try:
        return str(int(float(value)))
    except Exception:
        return ""


def latest_snapshot_by_key(snapshots: list[dict[str, str]]) -> dict[tuple[str, str, str], dict[str, str]]:
    latest: dict[tuple[str, str, str], dict[str, str]] = {}
    ordered = sorted(snapshots, key=lambda r: (r.get("strategy_rule", ""), r.get("instrument", ""), r.get("date", "")))
    for row in ordered:
        latest[(row.get("strategy_rule", ""), row.get("instrument", ""), row.get("date", ""))] = row
    return latest


def snapshot_context(snapshots: list[dict[str, str]], rule: str, instrument: str, asof: str) -> dict[str, str] | None:
    rows = [r for r in snapshots if r.get("strategy_rule") == rule and r.get("instrument") == instrument and r.get("date", "") <= asof]
    if not rows:
        return None
    return sorted(rows, key=lambda r: r.get("date", ""))[-1]


def action_index(actions: list[dict[str, str]]) -> dict[tuple[str, str, str, str], dict[str, str]]:
    idx: dict[tuple[str, str, str, str], dict[str, str]] = {}
    for row in actions:
        key = (row.get("strategy_rule", ""), row.get("signal_date", ""), row.get("instrument", ""), row.get("intent_reason", ""))
        idx[key] = row
    return idx


def status_for(intent: dict[str, str], action: dict[str, str] | None) -> str:
    reason = intent.get("intent_reason", "")
    if action and action.get("action") in {"historical_add", "historical_risk_reduce"}:
        if reason == "simulated_buy_small":
            return "simulated_buy_small"
        if reason == "simulated_reduce_partial":
            return "simulated_reduce_partial"
        return "historical_executed_in_replay"
    if reason == "blocked_execution_price_unavailable":
        return "pending_execution_price"
    if reason.startswith("blocked_"):
        return "blocked"
    if intent.get("intent_action") == "skip" or reason == "no_action":
        return "no_action"
    if intent.get("intent_action") == "hold":
        return "keep_existing_position"
    if reason in {"simulated_buy_small", "simulated_reduce_partial"}:
        return reason
    return "manual_review_required"


def gate_status(reason: str, gate: str) -> str:
    if gate == "cost":
        if reason == "blocked_tiny_no_trade_buffer":
            return "blocked_by_cost_or_tiny_gap"
        if reason.startswith("blocked_") or reason in {"no_action", "simulated_buy_small", "simulated_reduce_partial"}:
            return "checked_or_not_triggered"
    if gate == "turnover":
        if reason == "blocked_turnover_budget":
            return "blocked_by_turnover_budget"
        if reason.startswith("blocked_") or reason in {"no_action", "simulated_buy_small", "simulated_reduce_partial"}:
            return "checked_or_not_triggered"
    return "not_applicable"


def explanation_text(status: str, reason: str, instrument: str) -> str:
    prefix = f"{instrument} 只读研究解释："
    if status == "simulated_buy_small":
        return prefix + "候选调入意图以小额模拟方式进入回放审计，原因来自已冻结的 portfolio decision optimizer 规则；这不是交易建议。"
    if status == "simulated_reduce_partial":
        return prefix + "调出复核意图以部分模拟方式进入回放审计，原因来自已冻结的 portfolio decision optimizer 规则；这不是交易建议。"
    if status == "pending_execution_price":
        return prefix + "执行价可得性未满足，解释状态为 pending/block；不产生真实成交。"
    if status == "blocked":
        return prefix + f"规则门槛触发暂缓，primary_reason_code={reason}；保留人工复盘语义。"
    if status == "no_action":
        return prefix + "当日没有需要解释为动作的 candidate intent，保持只读观察。"
    if status == "historical_executed_in_replay":
        return prefix + "该意图在历史只读回放中有模拟执行记录，用于解释审计而非真实操作。"
    return prefix + "进入人工复盘解释状态，需结合只读证据查看原因。"


def build(out: Path) -> dict[str, Any]:
    if str(out.resolve()).startswith(str((ROOT / "data_tw/artifacts").resolve())):
        raise ValueError("decision_explanation_output_forbidden_under_data_tw_artifacts")
    p2_manifest_path = P2_DIR / "manifest.json"
    p2_manifest = json.loads(p2_manifest_path.read_text(encoding="utf-8"))
    intents = [r for r in read_csv(P2_DIR / "p2_order_intents_dry_run.csv") if r.get("strategy_rule") == CANDIDATE_RULE]
    actions = read_csv(P2_DIR / "p2_actions.csv")
    snapshots = read_csv(P2_DIR / "p2_position_snapshots.csv")
    coverage = read_csv(P2_DIR / "p2_coverage_audit.csv")
    actions_by_key = action_index(actions)
    rows: list[dict[str, Any]] = []
    for row_id, intent in enumerate(intents, start=1):
        instrument = intent.get("instrument", "")
        decision_date = intent.get("signal_date", "")
        reason = intent.get("primary_reason_code") or intent.get("intent_reason", "")
        action = actions_by_key.get((CANDIDATE_RULE, decision_date, instrument, intent.get("intent_reason", "")))
        snap = snapshot_context(snapshots, CANDIDATE_RULE, instrument, decision_date)
        status = status_for(intent, action)
        candidate_rank = to_int_text(intent.get("candidate_rank", ""))
        full_rank = to_int_text(intent.get("full_qlib_rank", ""))
        rank_gap = ""
        try:
            rank_gap = str(int(float(full_rank)) - int(float(candidate_rank))) if full_rank and candidate_rank else ""
        except Exception:
            rank_gap = ""
        secondary = []
        if intent.get("partial_intent_kind"):
            secondary.append(intent["partial_intent_kind"])
        if action:
            secondary.append("historical_replay_action_linked")
        if reason.startswith("blocked_"):
            secondary.append("manual_review_required")
        evidence = {
            "intent_action": intent.get("intent_action", ""),
            "intent_reason": intent.get("intent_reason", ""),
            "candidate_rank": candidate_rank,
            "buy_rank": to_int_text(intent.get("buy_rank", "")),
            "full_qlib_rank": full_rank,
            "action_linked": bool(action),
            "coverage_status": coverage[0].get("status", "") if coverage else "",
        }
        rows.append({
            "decision_date": decision_date,
            "portfolio_state_asof": decision_date,
            "instrument": instrument,
            "decision_status": status,
            "primary_reason_code": reason,
            "secondary_reason_codes": "|".join(secondary) if secondary else "not_applicable",
            "candidate_rank": candidate_rank,
            "buy_score_bucket": bucket(candidate_rank),
            "current_holding_flag": "true" if snap else "false",
            "holding_days": to_int_text(snap.get("holding_days", "")) if snap else "0",
            "rank_gap_vs_weakest_holding": rank_gap,
            "cost_gate_status": gate_status(reason, "cost"),
            "turnover_budget_status": gate_status(reason, "turnover"),
            "regime_status": action.get("regime_segment", "not_available") if action else "not_available",
            "execution_price_status": "unavailable" if status == "pending_execution_price" else ("historical_replay_executed" if action else "not_required_or_not_linked"),
            "readonly_disclaimer": DISCLAIMER,
            "not_investment_advice": True,
            "strategy_rule": CANDIDATE_RULE,
            "model_name": intent.get("model_name", p2_manifest.get("model_name", "")),
            "source_order_intent_row_id": row_id,
            "source_replay_manifest": rel(p2_manifest_path),
            "explanation_text_cn": explanation_text(status, reason, instrument),
            "evidence_fields": json.dumps(evidence, ensure_ascii=False, sort_keys=True),
            "manual_review_required": status in {"blocked", "manual_review_required", "pending_execution_price"},
            "readonly_only": True,
            "simulation_only": True,
            "not_order": True,
            "not_target_position": True,
        })
    quality = [
        {"audit_name": "required_rows_present", "status": "pass" if rows else "fail", "value": len(rows), "details": "candidate decision explanations"},
        {"audit_name": "source_p2_manifest_exists", "status": "pass" if p2_manifest_path.exists() else "fail", "value": rel(p2_manifest_path), "details": "readonly P2 replay source"},
        {"audit_name": "candidate_rule_only", "status": "pass" if all(r["strategy_rule"] == CANDIDATE_RULE for r in rows) else "fail", "value": CANDIDATE_RULE, "details": "no default rows emitted"},
        {"audit_name": "allowed_status_values", "status": "pass" if all(r["decision_status"] in ALLOWED_STATUSES for r in rows) else "fail", "value": len({r["decision_status"] for r in rows}), "details": "DecisionExplanation status enum"},
    ]
    forbidden = build_forbidden_audit(rows, out)
    schema = {
        "artifact_type": "DecisionExplanationArtifact",
        "schema_version": "portfolio_decision_optimizer_decision_explanation_v1",
        "required_fields": REQUIRED_FIELDS,
        "optional_fields": OPTIONAL_FIELDS,
        "field_descriptions": SCHEMA_FIELDS,
        "allowed_decision_status": sorted(ALLOWED_STATUSES),
        "forbidden_fields": ["target_position", "target_weight", "execution_quantity", "shares", "lots", "allocation_weight", "broker", "quick_trade", "order_id", "broker_order_id"],
        "score_semantics": "candidate_rank and buy_score_bucket are research ranking explanations only, not return, win-rate, upward-probability, buy-probability, or position-size estimates.",
    }
    out.mkdir(parents=True, exist_ok=True)
    write_csv(out / "decision_explanations.csv", rows, FIELDS)
    write_json(out / "schema.json", schema)
    write_csv(out / "explanation_quality_audit.csv", quality, ["audit_name", "status", "value", "details"])
    write_csv(out / "forbidden_semantics_audit.csv", forbidden, ["audit_name", "artifact", "field_name", "present", "status", "details"])
    manifest = {
        "artifact_type": "DecisionExplanationArtifact",
        "schema_version": "portfolio_decision_optimizer_decision_explanation_v1",
        "created_at": now(),
        "created_by": rel(Path(__file__)),
        "strategy_rule": CANDIDATE_RULE,
        "source_p2_manifest": rel(p2_manifest_path),
        "source_order_intents": rel(P2_DIR / "p2_order_intents_dry_run.csv"),
        "source_actions": rel(P2_DIR / "p2_actions.csv"),
        "source_position_snapshots": rel(P2_DIR / "p2_position_snapshots.csv"),
        "source_summary": rel(P2_DIR / "p2_summary.csv"),
        "source_coverage_audit": rel(P2_DIR / "p2_coverage_audit.csv"),
        "outputs": {
            "decision_explanations": rel(out / "decision_explanations.csv"),
            "schema": rel(out / "schema.json"),
            "explanation_quality_audit": rel(out / "explanation_quality_audit.csv"),
            "forbidden_semantics_audit": rel(out / "forbidden_semantics_audit.csv"),
        },
        "row_count": len(rows),
        "readonly_only": True,
        "simulation_only": True,
        "not_order": True,
        "not_target_position": True,
        "not_investment_advice": True,
        "no_provider_publish": True,
        "no_accepted_latest_switch": True,
        "no_monitor_write": True,
        "no_broker_quick_trade_order": True,
        "no_openai_call": True,
        "score_semantics": schema["score_semantics"],
        "known_limitations": [
            "P2 source window remains 2026H1 partial forward readonly acceptance through 2026-05-07.",
            "2023-2025 standard ModelSignalArtifact gap remains documented in P2 coverage audit.",
            "Explanations are generated from P2 readonly replay artifacts and do not adjust strategy rules.",
        ],
    }
    write_json(out / "manifest.json", manifest)
    return {"ok": all(r["status"] == "pass" for r in quality + forbidden), "manifest": rel(out / "manifest.json"), "row_count": len(rows)}


def build_forbidden_audit(rows: list[dict[str, Any]], out: Path) -> list[dict[str, Any]]:
    forbidden_fields = {
        "target_position", "target_weight", "execution_quantity", "shares", "lots", "allocation_weight",
        "broker", "quick_trade", "order_id", "broker_order_id", "provider_publish_status",
        "accepted_latest_status", "monitor_write_status",
    }
    fields = set(FIELDS)
    audit = []
    for field in sorted(forbidden_fields):
        audit.append({
            "audit_name": "forbidden_field_absent",
            "artifact": "decision_explanations.csv",
            "field_name": field,
            "present": field in fields,
            "status": "fail" if field in fields else "pass",
            "details": "field must not appear in DecisionExplanationArtifact rows",
        })
    unsafe_phrases = ["应买入", "应卖出", "目标仓位", "目标权重", "保证收益", "上涨概率", "胜率", "买入概率", "自动买入", "自动卖出"]
    text = "\n".join(str(row.get("explanation_text_cn", "")) for row in rows)
    for phrase in unsafe_phrases:
        present = phrase in text
        audit.append({
            "audit_name": "unsafe_text_absent",
            "artifact": "decision_explanations.csv",
            "field_name": phrase,
            "present": present,
            "status": "fail" if present else "pass",
            "details": "explanation text must remain readonly research wording",
        })
    under_artifacts = str(out.resolve()).startswith(str((ROOT / "data_tw/artifacts").resolve()))
    audit.append({
        "audit_name": "output_not_under_data_tw_artifacts",
        "artifact": rel(out),
        "field_name": "output_dir",
        "present": under_artifacts,
        "status": "fail" if under_artifacts else "pass",
        "details": "P3 writes only experiment artifacts",
    })
    return audit


def main() -> int:
    parser = argparse.ArgumentParser(description="Build P3 DecisionExplanationArtifact for portfolio_decision_optimizer_v1.")
    parser.add_argument("--out-dir", default=str(OUT_DIR))
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    payload = build(Path(args.out_dir))
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print("ok=" + str(payload["ok"]).lower())
        print("manifest=" + payload["manifest"])
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
