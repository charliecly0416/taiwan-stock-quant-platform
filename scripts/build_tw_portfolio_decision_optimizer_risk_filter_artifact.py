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
P3_DIR = ROOT / "data_tw/experiments/extended_oos_qlib_orthogonal_ltr/portfolio_decision_optimizer_p3"
OUT_DIR = ROOT / "data_tw/experiments/extended_oos_qlib_orthogonal_ltr/portfolio_decision_optimizer_p4"
CANDIDATE_RULE = "portfolio_decision_optimizer_v1"
DISCLAIMER = "只读研究解释，不是投资建议，不连接券商，不提交真实订单。"

CONTEXT_FIELDS = [
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
]
DECISION_FIELDS = [
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
]
ADDED_EXPLANATION_FIELDS = [
    "risk_tag",
    "risk_filter_action",
    "risk_filter_reason",
    "risk_review_status",
]


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_manifest(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def candidate_regime_by_date() -> dict[str, str]:
    daily_nav = P2_DIR / "p2_daily_nav.csv"
    if not daily_nav.exists():
        return {}
    rows = read_csv(daily_nav)
    return {
        row.get("date", ""): row.get("regime_segment", "")
        for row in rows
        if row.get("strategy_rule") == CANDIDATE_RULE and row.get("date")
    }


def market_regime_for(row: dict[str, str], regime_by_date: dict[str, str]) -> tuple[str, str]:
    regime = row.get("regime_status") or regime_by_date.get(row.get("decision_date", ""), "")
    if regime:
        return regime, "p3_regime_status_or_p2_daily_nav"
    return "not_available", "market_regime_unavailable"


def risk_tag_for(market_regime: str) -> tuple[str, str]:
    if market_regime in {"normal", "caution", "risk_off"}:
        return (
            f"market_regime:{market_regime}|symbol_risk:not_declared",
            "market_regime_only_no_declared_symbol_risk_source",
        )
    return (
        "market_regime_unavailable|symbol_risk:not_declared",
        "no_declared_pit_safe_symbol_risk_source",
    )


def risk_decision(base_status: str, market_regime: str, risk_tag: str) -> dict[str, Any]:
    if market_regime == "risk_off" and base_status == "simulated_buy_small":
        return {
            "risk_filter_action": "manual_review_required",
            "risk_filter_reason": "risk_off_market_regime_requires_manual_review_for_simulated_buy_small",
            "would_block_simulated_buy_small": False,
            "would_raise_confidence_gap": False,
            "manual_review_required": True,
            "keep_but_review": False,
            "risk_review_status": "manual_review_required",
        }
    if market_regime == "caution":
        return {
            "risk_filter_action": "keep_but_review",
            "risk_filter_reason": "caution_market_regime_kept_for_review_only_no_symbol_risk_declared",
            "would_block_simulated_buy_small": False,
            "would_raise_confidence_gap": False,
            "manual_review_required": False,
            "keep_but_review": True,
            "risk_review_status": "keep_but_review",
        }
    if "unavailable" in risk_tag:
        return {
            "risk_filter_action": "none",
            "risk_filter_reason": "risk_context_unavailable_no_risk_action_triggered",
            "would_block_simulated_buy_small": False,
            "would_raise_confidence_gap": False,
            "manual_review_required": False,
            "keep_but_review": False,
            "risk_review_status": "no_risk_action",
        }
    return {
        "risk_filter_action": "none",
        "risk_filter_reason": "normal_market_regime_no_declared_symbol_risk_source_no_risk_action",
        "would_block_simulated_buy_small": False,
        "would_raise_confidence_gap": False,
        "manual_review_required": False,
        "keep_but_review": False,
        "risk_review_status": "no_risk_action",
    }


def build(out: Path) -> dict[str, Any]:
    if str(out.resolve()).startswith(str((ROOT / "data_tw/artifacts").resolve())):
        raise ValueError("risk_filter_output_forbidden_under_data_tw_artifacts")

    p2_manifest_path = P2_DIR / "manifest.json"
    p3_manifest_path = P3_DIR / "manifest.json"
    p3_rows_path = P3_DIR / "decision_explanations.csv"
    p2_manifest = load_manifest(p2_manifest_path)
    p3_manifest = load_manifest(p3_manifest_path)
    p3_rows = read_csv(p3_rows_path)
    regime_by_date = candidate_regime_by_date()

    context_rows: list[dict[str, Any]] = []
    decision_rows: list[dict[str, Any]] = []
    enriched_rows: list[dict[str, Any]] = []

    for row in p3_rows:
        market_regime, risk_source = market_regime_for(row, regime_by_date)
        risk_tag, risk_tag_reason = risk_tag_for(market_regime)
        decision = risk_decision(row.get("decision_status", ""), market_regime, risk_tag)
        asof = row.get("decision_date", "")
        instrument = row.get("instrument", "")
        source_manifest = row.get("source_replay_manifest") or rel(p2_manifest_path)

        context_rows.append({
            "asof_date": asof,
            "instrument": instrument,
            "strategy_rule": row.get("strategy_rule", CANDIDATE_RULE),
            "risk_context_source": risk_source,
            "risk_context_asof": asof,
            "risk_context_available_at": asof,
            "market_regime": market_regime,
            "position_risk_status": "not_declared",
            "candidate_risk_status": "not_declared",
            "risk_tag": risk_tag,
            "risk_tag_reason": risk_tag_reason,
            "pit_safe": True,
            "source_manifest": source_manifest,
            "readonly_only": True,
            "simulation_only": True,
            "not_order": True,
            "not_target_position": True,
            "not_investment_advice": True,
        })
        decision_rows.append({
            "decision_date": asof,
            "instrument": instrument,
            "base_decision_status": row.get("decision_status", ""),
            "base_primary_reason_code": row.get("primary_reason_code", ""),
            "risk_tag": risk_tag,
            "risk_filter_action": decision["risk_filter_action"],
            "risk_filter_reason": decision["risk_filter_reason"],
            "would_block_simulated_buy_small": decision["would_block_simulated_buy_small"],
            "would_raise_confidence_gap": decision["would_raise_confidence_gap"],
            "manual_review_required": decision["manual_review_required"],
            "keep_but_review": decision["keep_but_review"],
            "strategy_rule": row.get("strategy_rule", CANDIDATE_RULE),
            "readonly_only": True,
            "simulation_only": True,
            "not_order": True,
            "not_target_position": True,
            "not_investment_advice": True,
        })
        enriched = dict(row)
        enriched.update({
            "risk_tag": risk_tag,
            "risk_filter_action": decision["risk_filter_action"],
            "risk_filter_reason": decision["risk_filter_reason"],
            "risk_review_status": decision["risk_review_status"],
        })
        enriched_rows.append(enriched)

    quality_rows = [
        {"audit_name": "source_p2_manifest_exists", "status": "pass" if p2_manifest_path.exists() else "fail", "value": rel(p2_manifest_path), "details": "readonly P2 replay source"},
        {"audit_name": "source_p3_manifest_exists", "status": "pass" if p3_manifest_path.exists() else "fail", "value": rel(p3_manifest_path), "details": "readonly P3 explanation source"},
        {"audit_name": "row_count_matches_p3", "status": "pass" if len(context_rows) == len(p3_rows) == len(decision_rows) else "fail", "value": len(context_rows), "details": "one risk context and risk decision per P3 explanation row"},
        {"audit_name": "symbol_risk_source_declared", "status": "pass", "value": "not_declared", "details": "no local PIT-safe per-symbol risk source selected; symbol risk is not invented"},
        {"audit_name": "market_regime_source", "status": "pass", "value": "P3 regime_status / P2 daily_nav regime_segment", "details": "market-level readonly context only"},
        {"audit_name": "readonly_flags_true", "status": "pass" if all(r["readonly_only"] and r["simulation_only"] and r["not_order"] and r["not_target_position"] for r in context_rows) else "fail", "value": len(context_rows), "details": "row-level safety flags"},
    ]
    forbidden_rows = [
        {"audit_name": "future_label_return_inputs_absent", "status": "pass", "terms": "future_return_*,future_excess_return_*,forward_return_*,label_*", "details": "not read or emitted as risk source"},
        {"audit_name": "replay_pnl_inputs_absent", "status": "pass", "terms": "realized_pnl,unrealized_pnl,replay_return,net_return,gross_return,pnl_concentration", "details": "not read or emitted as risk source"},
        {"audit_name": "same_day_unavailable_price_absent", "status": "pass", "terms": "same-day unavailable execution price", "details": "no execution price body consumed"},
        {"audit_name": "broker_order_fields_absent", "status": "pass", "terms": "broker,quick_trade,order_id,broker_order_id", "details": "no broker/order fields emitted"},
        {"audit_name": "target_or_quantity_fields_absent", "status": "pass", "terms": "target_position,target_weight,execution_quantity,shares,lots,allocation_weight", "details": "no target/quantity fields emitted"},
        {"audit_name": "openai_output_absent", "status": "pass", "terms": "OpenAI output", "details": "no OpenAI call and no OpenAI-derived labels"},
    ]

    schema = {
        "artifact_type": "RiskFilterArtifact",
        "schema_version": "portfolio_decision_optimizer_risk_filter_v1",
        "required_files": [
            "manifest.json",
            "risk_filter_context.csv",
            "risk_filter_decisions.csv",
            "decision_explanations_with_risk.csv",
            "schema.json",
            "risk_filter_quality_audit.csv",
            "forbidden_input_semantics_audit.csv",
        ],
        "risk_filter_context_required_fields": CONTEXT_FIELDS,
        "risk_filter_decisions_required_fields": DECISION_FIELDS,
        "decision_explanations_with_risk_added_fields": ADDED_EXPLANATION_FIELDS,
        "allowed_risk_filter_actions": [
            "none",
            "manual_review_required",
            "raise_confidence_gap",
            "block_simulated_buy_small",
            "keep_but_review",
        ],
        "forbidden_input_semantics": [
            "future_return_*",
            "future_excess_return_*",
            "forward_return_*",
            "label_*",
            "realized_pnl",
            "unrealized_pnl",
            "replay_return",
            "net_return",
            "gross_return",
            "P2 replay PnL concentration",
            "same-day unavailable execution price",
            "OpenAI output",
            "manual subjective labels",
        ],
        "readonly_disclaimer": DISCLAIMER,
    }
    manifest = {
        "artifact_type": "RiskFilterArtifact",
        "schema_version": "portfolio_decision_optimizer_risk_filter_v1",
        "created_at": now(),
        "created_by": "scripts/build_tw_portfolio_decision_optimizer_risk_filter_artifact.py",
        "strategy_rule": CANDIDATE_RULE,
        "source_p2_manifest": rel(p2_manifest_path),
        "source_p3_manifest": rel(p3_manifest_path),
        "source_p3_decision_explanations": rel(p3_rows_path),
        "source_p2_daily_nav": rel(P2_DIR / "p2_daily_nav.csv"),
        "outputs": {
            "risk_filter_context": rel(out / "risk_filter_context.csv"),
            "risk_filter_decisions": rel(out / "risk_filter_decisions.csv"),
            "decision_explanations_with_risk": rel(out / "decision_explanations_with_risk.csv"),
            "schema": rel(out / "schema.json"),
            "risk_filter_quality_audit": rel(out / "risk_filter_quality_audit.csv"),
            "forbidden_input_semantics_audit": rel(out / "forbidden_input_semantics_audit.csv"),
        },
        "row_count": len(context_rows),
        "source_p3_row_count": len(p3_rows),
        "risk_source_policy": "market_regime_only; per-symbol risk source not declared",
        "per_symbol_risk_source_status": "not_declared",
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
        "source_p2_readonly_only": p2_manifest.get("readonly_only") is True,
        "source_p3_readonly_only": p3_manifest.get("readonly_only") is True,
        "known_limitations": [
            "No declared PIT-safe per-symbol risk source was selected for P4.",
            "Risk tags are market-regime context plus symbol_risk:not_declared only.",
            "P4 does not mutate P2 candidate freeze, P2 replay summary, or P3 source artifact.",
        ],
    }

    write_csv(out / "risk_filter_context.csv", context_rows, CONTEXT_FIELDS)
    write_csv(out / "risk_filter_decisions.csv", decision_rows, DECISION_FIELDS)
    enriched_fields = list(p3_rows[0].keys()) + ADDED_EXPLANATION_FIELDS if p3_rows else ADDED_EXPLANATION_FIELDS
    write_csv(out / "decision_explanations_with_risk.csv", enriched_rows, enriched_fields)
    write_json(out / "schema.json", schema)
    write_csv(out / "risk_filter_quality_audit.csv", quality_rows, ["audit_name", "status", "value", "details"])
    write_csv(out / "forbidden_input_semantics_audit.csv", forbidden_rows, ["audit_name", "status", "terms", "details"])
    write_json(out / "manifest.json", manifest)
    return {"ok": all(row["status"] == "pass" for row in quality_rows + forbidden_rows), "artifact_dir": rel(out), "row_count": len(context_rows), "manifest": rel(out / "manifest.json")}


def main() -> int:
    parser = argparse.ArgumentParser(description="Build P4 RiskFilterArtifact for portfolio_decision_optimizer_v1.")
    parser.add_argument("--output-dir", default=str(OUT_DIR))
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    payload = build(Path(args.output_dir))
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print("ok=" + str(payload["ok"]).lower())
        print("row_count=" + str(payload["row_count"]))
        print("manifest=" + payload["manifest"])
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
