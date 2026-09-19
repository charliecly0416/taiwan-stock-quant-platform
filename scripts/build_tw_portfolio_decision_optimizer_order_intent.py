#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


FORBIDDEN_PRICE_FIELDS = {"next_open", "next_close", "execution_price", "fallback_price", "signal_close"}
FORBIDDEN_ORDER_INTENT_FIELDS = {
    "execution_date",
    "execution_price",
    "execution_quantity",
    "commission",
    "tax",
    "cash",
    "cash_after",
    "equity",
    "daily_return",
    "realized_pnl",
    "unrealized_pnl",
    "broker_order_id",
    "target_position",
    "target_weight",
    "quantity_to_buy",
    "quantity_to_sell",
    "shares",
    "lots",
    "allocation_weight",
    "nav",
    "fee",
    "broker",
    "order_id",
    "quick_trade",
    "replay_return",
}
PARTIAL_ADJUSTMENT_SELL_REASON = "simulated_reduce_partial"
PARTIAL_ADJUSTMENT_BUY_REASON = "simulated_buy_small"


def norm(symbol: Any) -> str:
    text = str(symbol or "").strip().upper()
    return text if text.startswith("TW") else f"TW{text}"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_output_path(path: Path) -> None:
    resolved = path.resolve()
    cwd = Path.cwd().resolve()
    try:
        rel = resolved.relative_to(cwd)
    except ValueError:
        rel = resolved
    parts = rel.parts
    if len(parts) >= 2 and parts[0] == "data_tw" and parts[1] == "artifacts":
        raise ValueError("dry_run_output_forbidden_under_data_tw_artifacts")
    if path.name in {"manifest.json", "order_intents.csv"}:
        raise ValueError("dry_run_output_forbidden_formal_artifact_filename")


def signal_maps(rows: list[dict[str, Any]]) -> tuple[dict[str, dict[str, Any]], list[str]]:
    by_symbol: dict[str, dict[str, Any]] = {}
    for row in rows:
        item = dict(row)
        item["instrument"] = norm(item.get("instrument"))
        by_symbol[item["instrument"]] = item
    buy_order = sorted(
        [row for row in by_symbol.values() if float(row.get("candidate_rank", 999999)) <= 50],
        key=lambda row: (-float(row.get("buy_score", 0)), norm(row.get("instrument"))),
    )
    return by_symbol, [norm(row["instrument"]) for row in buy_order]


def baseline_top50_exit_one_worst_sell(fixture: dict[str, Any]) -> list[dict[str, Any]]:
    signal_by_symbol, buy_order = signal_maps(fixture.get("model_signal_rows") or [])
    target_holding_count = int((fixture.get("strategy_config") or {}).get("target_holding_count", 10))
    held = sorted(
        norm(row.get("instrument"))
        for row in fixture.get("portfolio_state_rows", [])
        if int(row.get("quantity") or 0) > 0
    )
    candidate_set = set(buy_order)
    outside = sorted(
        [symbol for symbol in held if symbol not in candidate_set],
        key=lambda symbol: (float(signal_by_symbol.get(symbol, {}).get("full_qlib_rank", 999999)), symbol),
        reverse=True,
    )
    sells = outside[:1]
    remaining = set(held) - set(sells)
    open_slots = max(0, target_holding_count - len(remaining))
    buys: list[str] = []
    for symbol in buy_order:
        if len(buys) >= min(1, open_slots):
            break
        if symbol not in remaining:
            buys.append(symbol)
    holds = [symbol for symbol in held if symbol not in sells]
    rows: list[dict[str, Any]] = []
    for action, symbols in (("sell", sells), ("buy", buys), ("hold", holds)):
        for symbol in symbols:
            sig = signal_by_symbol.get(symbol, {})
            rows.append({
                "signal_date": fixture.get("signal_date", "2026-06-19"),
                "instrument": symbol,
                "intent_action": action,
                "intent_reason": f"top50_exit_one_worst_sell_{action}",
                "primary_reason_code": f"top50_exit_one_worst_sell_{action}",
                "strategy_rule": "portfolio_decision_optimizer_v1",
                "candidate_rank": sig.get("candidate_rank", ""),
                "buy_rank": sig.get("score_rank", -1 if action == "sell" else ""),
                "full_qlib_rank": sig.get("full_qlib_rank", ""),
                "max_buy_count": 1,
                "max_sell_count": 1,
                "model_name": fixture.get("model_name", "fixture_model"),
                "signal_artifact": fixture.get("signal_artifact", "golden_fixture"),
                "readonly_only": True,
                "simulation_only": True,
                "not_order": True,
                "not_target_position": True,
                "not_investment_advice": True,
            })
    return rows


def apply_execution_price_gate(baseline_rows: list[dict[str, Any]], fixture: dict[str, Any]) -> list[dict[str, Any]]:
    readiness = fixture.get("execution_readiness") or {}
    if any(field in readiness for field in FORBIDDEN_PRICE_FIELDS):
        raise ValueError("execution_readiness_contains_price_value")
    if readiness.get("next_open_ready") is not False:
        return [dict(row) for row in baseline_rows]
    gated: list[dict[str, Any]] = []
    for row in baseline_rows:
        item = dict(row)
        if item.get("intent_action") in {"buy", "sell"}:
            item["intent_action"] = "skip"
            item["intent_reason"] = "blocked_execution_price_unavailable"
            item["primary_reason_code"] = "blocked_execution_price_unavailable"
        gated.append(item)
    return gated


def apply_tiny_no_trade_buffer(baseline_rows: list[dict[str, Any]], fixture: dict[str, Any]) -> list[dict[str, Any]]:
    readiness = fixture.get("execution_readiness") or {}
    if any(field in readiness for field in FORBIDDEN_PRICE_FIELDS):
        raise ValueError("execution_readiness_contains_price_value")
    if readiness.get("next_open_ready") is False:
        raise ValueError("tiny_no_trade_buffer_must_not_use_execution_price_gate")
    config = (fixture.get("strategy_config") or {}).get("tiny_no_trade_buffer") or {}
    min_rank_gap = float(config.get("min_rank_gap", 1))
    min_score_gap = float(config.get("min_score_gap", 0.0001))
    by_symbol = {norm(row.get("instrument")): row for row in fixture.get("model_signal_rows") or []}
    sells = [row for row in baseline_rows if row.get("intent_action") == "sell"]
    buys = [row for row in baseline_rows if row.get("intent_action") == "buy"]
    if not sells or not buys:
        return [dict(row) for row in baseline_rows]
    sell = sells[0]
    buy = buys[0]
    buy_sig = by_symbol.get(norm(buy.get("instrument")), {})
    sell_sig = by_symbol.get(norm(sell.get("instrument")), {})
    rank_gap = abs(float(buy.get("candidate_rank") or buy_sig.get("candidate_rank") or 999999) - float(sell.get("full_qlib_rank") or sell_sig.get("full_qlib_rank") or 999999))
    score_gap = float(buy_sig.get("buy_score", 0)) - float(sell_sig.get("buy_score", 0))
    should_block = rank_gap <= min_rank_gap and score_gap <= min_score_gap
    candidate: list[dict[str, Any]] = []
    for row in baseline_rows:
        item = dict(row)
        if should_block and item.get("intent_action") in {"buy", "sell"}:
            item["intent_action"] = "skip"
            item["intent_reason"] = "blocked_tiny_no_trade_buffer"
            item["primary_reason_code"] = "blocked_tiny_no_trade_buffer"
            item["rank_gap_vs_exit_candidate"] = rank_gap
            item["score_gap_vs_exit_candidate"] = score_gap
        candidate.append(item)
    return candidate


def apply_confidence_gap(baseline_rows: list[dict[str, Any]], fixture: dict[str, Any]) -> list[dict[str, Any]]:
    readiness = fixture.get("execution_readiness") or {}
    if any(field in readiness for field in FORBIDDEN_PRICE_FIELDS):
        raise ValueError("execution_readiness_contains_price_value")
    if readiness.get("next_open_ready") is False:
        raise ValueError("confidence_gap_must_not_use_execution_price_gate")
    config = (fixture.get("strategy_config") or {}).get("confidence_gap") or {}
    min_rank_gap = float(config.get("min_rank_gap", 5))
    min_score_gap = float(config.get("min_score_gap", 0.01))
    by_symbol = {norm(row.get("instrument")): row for row in fixture.get("model_signal_rows") or []}
    sells = [row for row in baseline_rows if row.get("intent_action") == "sell"]
    buys = [row for row in baseline_rows if row.get("intent_action") == "buy"]
    if not sells or not buys:
        return [dict(row) for row in baseline_rows]
    sell = sells[0]
    buy = buys[0]
    buy_sig = by_symbol.get(norm(buy.get("instrument")), {})
    sell_sig = by_symbol.get(norm(sell.get("instrument")), {})
    rank_gap = float(sell.get("full_qlib_rank") or sell_sig.get("full_qlib_rank") or 999999) - float(buy.get("candidate_rank") or buy_sig.get("candidate_rank") or 999999)
    score_gap = float(buy_sig.get("buy_score", 0)) - float(sell_sig.get("buy_score", 0))
    should_block = score_gap < min_score_gap and rank_gap < min_rank_gap
    candidate: list[dict[str, Any]] = []
    for row in baseline_rows:
        item = dict(row)
        if should_block and item.get("intent_action") in {"buy", "sell"}:
            item["intent_action"] = "skip"
            item["intent_reason"] = "blocked_confidence_gap"
            item["primary_reason_code"] = "blocked_confidence_gap"
            item["rank_gap_vs_exit_candidate"] = rank_gap
            item["score_gap_vs_exit_candidate"] = score_gap
        candidate.append(item)
    return candidate


def apply_min_holding_days_with_exception(baseline_rows: list[dict[str, Any]], fixture: dict[str, Any]) -> list[dict[str, Any]]:
    readiness = fixture.get("execution_readiness") or {}
    if any(field in readiness for field in FORBIDDEN_PRICE_FIELDS):
        raise ValueError("execution_readiness_contains_price_value")
    if readiness.get("next_open_ready") is False:
        raise ValueError("min_holding_days_must_not_use_execution_price_gate")
    config = (fixture.get("strategy_config") or {}).get("min_holding_days_with_exception") or {}
    min_holding_days = int(config.get("min_holding_days", 5))
    deep_exit_threshold = float(config.get("deep_exit_full_qlib_rank_threshold", 80))
    portfolio_by_symbol = {norm(row.get("instrument")): row for row in fixture.get("portfolio_state_rows") or []}
    sells = [row for row in baseline_rows if row.get("intent_action") == "sell"]
    buys = [row for row in baseline_rows if row.get("intent_action") == "buy"]
    if not sells or not buys:
        return [dict(row) for row in baseline_rows]
    sell = sells[0]
    sell_symbol = norm(sell.get("instrument"))
    portfolio_row = portfolio_by_symbol.get(sell_symbol, {})
    holding_days = int(portfolio_row.get("holding_days") or 0)
    full_rank = float(sell.get("full_qlib_rank") or 999999)
    short_holding = holding_days < min_holding_days
    exception = full_rank >= deep_exit_threshold
    should_block = short_holding and not exception
    candidate: list[dict[str, Any]] = []
    for row in baseline_rows:
        item = dict(row)
        if should_block and item.get("intent_action") in {"buy", "sell"}:
            item["intent_action"] = "skip"
            item["intent_reason"] = "blocked_min_holding_days"
            item["primary_reason_code"] = "blocked_min_holding_days"
            item["holding_days"] = holding_days
            item["min_holding_days"] = min_holding_days
            item["deep_exit_full_qlib_rank_threshold"] = deep_exit_threshold
        candidate.append(item)
    return candidate


def apply_turnover_budget(baseline_rows: list[dict[str, Any]], fixture: dict[str, Any]) -> list[dict[str, Any]]:
    readiness = fixture.get("execution_readiness") or {}
    if any(field in readiness for field in FORBIDDEN_PRICE_FIELDS):
        raise ValueError("execution_readiness_contains_price_value")
    if readiness.get("next_open_ready") is False:
        raise ValueError("turnover_budget_must_not_use_execution_price_gate")
    config = (fixture.get("strategy_config") or {}).get("turnover_budget") or {}
    max_action_count = int(config.get("max_action_count", 2))
    low_priority_rank_improvement_max = float(config.get("low_priority_rank_improvement_max", 5))
    strong_signal_rank_improvement_min = float(config.get("strong_signal_rank_improvement_min", 30))
    strong_signal_candidate_rank_max = float(config.get("strong_signal_candidate_rank_max", 10))
    turnover_state = fixture.get("turnover_state") or {}
    weekly_action_count = int(turnover_state.get("weekly_action_count") or 0)
    sells = [row for row in baseline_rows if row.get("intent_action") == "sell"]
    buys = [row for row in baseline_rows if row.get("intent_action") == "buy"]
    if not sells or not buys:
        return [dict(row) for row in baseline_rows]
    sell = sells[0]
    buy = buys[0]
    rank_improvement = float(sell.get("full_qlib_rank") or 999999) - float(buy.get("candidate_rank") or 999999)
    budget_exceeded = weekly_action_count >= max_action_count
    low_priority = rank_improvement <= low_priority_rank_improvement_max
    strong_signal = rank_improvement >= strong_signal_rank_improvement_min or float(buy.get("candidate_rank") or 999999) <= strong_signal_candidate_rank_max
    should_block = budget_exceeded and low_priority and not strong_signal
    candidate: list[dict[str, Any]] = []
    for row in baseline_rows:
        item = dict(row)
        if should_block and item.get("intent_action") in {"buy", "sell"}:
            item["intent_action"] = "skip"
            item["intent_reason"] = "blocked_turnover_budget"
            item["primary_reason_code"] = "blocked_turnover_budget"
            item["weekly_action_count"] = weekly_action_count
            item["max_action_count"] = max_action_count
            item["rank_improvement"] = rank_improvement
        candidate.append(item)
    return candidate


def apply_risk_off_raised_threshold(baseline_rows: list[dict[str, Any]], fixture: dict[str, Any]) -> list[dict[str, Any]]:
    readiness = fixture.get("execution_readiness") or {}
    if any(field in readiness for field in FORBIDDEN_PRICE_FIELDS):
        raise ValueError("execution_readiness_contains_price_value")
    if readiness.get("next_open_ready") is False:
        raise ValueError("risk_off_raised_threshold_must_not_use_execution_price_gate")
    config = (fixture.get("strategy_config") or {}).get("risk_off_raised_threshold") or {}
    risk_off_regimes = {str(item) for item in config.get("risk_off_regimes", ["risk_off"])}
    weak_signal_rank_improvement_min = float(config.get("weak_signal_rank_improvement_min", 30))
    strong_signal_candidate_rank_max = float(config.get("strong_signal_candidate_rank_max", 10))
    market_regime = fixture.get("market_regime") or {}
    regime_label = str(market_regime.get("regime_label") or "normal")
    sells = [row for row in baseline_rows if row.get("intent_action") == "sell"]
    buys = [row for row in baseline_rows if row.get("intent_action") == "buy"]
    if not sells or not buys:
        return [dict(row) for row in baseline_rows]
    sell = sells[0]
    buy = buys[0]
    rank_improvement = float(sell.get("full_qlib_rank") or 999999) - float(buy.get("candidate_rank") or 999999)
    buy_candidate_rank = float(buy.get("candidate_rank") or 999999)
    is_risk_off = regime_label in risk_off_regimes
    weak_signal = rank_improvement < weak_signal_rank_improvement_min and buy_candidate_rank > strong_signal_candidate_rank_max
    should_block = is_risk_off and weak_signal
    candidate: list[dict[str, Any]] = []
    for row in baseline_rows:
        item = dict(row)
        if should_block and item.get("intent_action") in {"buy", "sell"}:
            item["intent_action"] = "skip"
            item["intent_reason"] = "blocked_risk_off_raised_threshold"
            item["primary_reason_code"] = "blocked_risk_off_raised_threshold"
            item["market_regime_label"] = regime_label
            item["rank_improvement"] = rank_improvement
            item["weak_signal_rank_improvement_min"] = weak_signal_rank_improvement_min
        candidate.append(item)
    return candidate


def apply_partial_adjustment(baseline_rows: list[dict[str, Any]], fixture: dict[str, Any]) -> list[dict[str, Any]]:
    readiness = fixture.get("execution_readiness") or {}
    if any(field in readiness for field in FORBIDDEN_PRICE_FIELDS):
        raise ValueError("execution_readiness_contains_price_value")
    if readiness.get("next_open_ready") is False:
        raise ValueError("partial_adjustment_must_not_use_execution_price_gate")
    strategy_config = fixture.get("strategy_config") or {}
    prior_gate_keys = {
        "execution_price_gate",
        "tiny_no_trade_buffer",
        "confidence_gap",
        "min_holding_days_with_exception",
        "turnover_budget",
        "risk_off_raised_threshold",
    }
    prior_used = sorted(key for key in prior_gate_keys if key in strategy_config)
    if prior_used:
        raise ValueError("partial_adjustment_must_not_use_prior_gates:" + "|".join(prior_used))
    config = strategy_config.get("partial_adjustment") or {}
    sell_reason = str(config.get("sell_reason") or PARTIAL_ADJUSTMENT_SELL_REASON)
    buy_reason = str(config.get("buy_reason") or PARTIAL_ADJUSTMENT_BUY_REASON)
    if sell_reason != PARTIAL_ADJUSTMENT_SELL_REASON:
        raise ValueError("partial_adjustment_unknown_sell_reason")
    if buy_reason != PARTIAL_ADJUSTMENT_BUY_REASON:
        raise ValueError("partial_adjustment_unknown_buy_reason")
    policy = str(config.get("policy") or "simulation_only_partial_intent")
    candidate: list[dict[str, Any]] = []
    for row in baseline_rows:
        item = dict(row)
        if item.get("intent_action") == "sell":
            item["intent_reason"] = sell_reason
            item["primary_reason_code"] = sell_reason
            item["partial_intent_kind"] = sell_reason
            item["partial_intent_policy"] = policy
            item["partial_intent_note"] = "simulation_only_partial_intent_without_quantity_weight_cash_execution_or_broker_fields"
        elif item.get("intent_action") == "buy":
            item["intent_reason"] = buy_reason
            item["primary_reason_code"] = buy_reason
            item["partial_intent_kind"] = buy_reason
            item["partial_intent_policy"] = policy
            item["partial_intent_note"] = "simulation_only_partial_intent_without_quantity_weight_cash_execution_or_broker_fields"
        candidate.append(item)
    return candidate


def forbidden_order_intent_fields(rows: list[dict[str, Any]]) -> list[str]:
    found: set[str] = set()
    for row in rows:
        found.update(set(row) & FORBIDDEN_ORDER_INTENT_FIELDS)
    return sorted(found)


def build_from_fixture(fixture: dict[str, Any]) -> dict[str, Any]:
    mechanism = str(fixture.get("mechanism") or "execution_price_gate")
    if mechanism == "partial_adjustment" and fixture.get("baseline_order_intents"):
        baseline = [dict(row) for row in fixture.get("baseline_order_intents", [])]
    else:
        baseline = baseline_top50_exit_one_worst_sell(fixture)
    if mechanism == "execution_price_gate":
        candidate = apply_execution_price_gate(baseline, fixture)
    elif mechanism == "tiny_no_trade_buffer":
        candidate = apply_tiny_no_trade_buffer(baseline, fixture)
    elif mechanism == "confidence_gap":
        candidate = apply_confidence_gap(baseline, fixture)
    elif mechanism == "min_holding_days_with_exception":
        candidate = apply_min_holding_days_with_exception(baseline, fixture)
    elif mechanism == "turnover_budget":
        candidate = apply_turnover_budget(baseline, fixture)
    elif mechanism == "risk_off_raised_threshold":
        candidate = apply_risk_off_raised_threshold(baseline, fixture)
    elif mechanism == "partial_adjustment":
        candidate = apply_partial_adjustment(baseline, fixture)
    else:
        raise ValueError(f"unsupported_mechanism:{mechanism}")
    forbidden = forbidden_order_intent_fields(candidate)
    return {
        "ok": not forbidden,
        "mechanism": mechanism,
        "baseline_order_intents": baseline,
        "candidate_order_intents": candidate,
        "forbidden_order_intent_fields": forbidden,
        "readonly_only": True,
        "simulation_only": True,
        "not_order": True,
        "not_target_position": True,
        "not_investment_advice": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Portfolio Decision Optimizer dry-run OrderIntent rows from a local golden fixture.")
    parser.add_argument("--fixture", required=True)
    parser.add_argument("--out", default="")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = build_from_fixture(load_json(Path(args.fixture)))
    if args.out:
        out = Path(args.out)
        validate_output_path(out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.json or not args.out:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
