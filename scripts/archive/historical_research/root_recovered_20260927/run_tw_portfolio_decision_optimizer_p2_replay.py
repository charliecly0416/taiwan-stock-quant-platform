#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import statistics
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PRICE_ROOT = ROOT / "qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/normalized_nonempty"
SIGNAL_MANIFEST = ROOT / "data_tw/artifacts/signals/e4_frozen_qlib_2023_2025_ltr/r1_legacy_signal_adapter_20260616/manifest.json"
DEFAULT_OUT = ROOT / "data_tw/experiments/extended_oos_qlib_orthogonal_ltr/portfolio_decision_optimizer_p2"
MODEL_NAME = "e4_frozen_qlib_2023_2025_ltr"
MODEL_FAMILY = "ltr"
DEFAULT_RULE = "top50_exit_one_worst_sell"
CANDIDATE_RULE = "portfolio_decision_optimizer_v1"
INITIAL_EQUITY = 1_000_000.0
TARGET_HOLDINGS = 10
CANDIDATE_K = 50
LOT_SIZE = 10
FEE_RATE = 0.001425
SELL_TAX_RATE = 0.003
PARTIAL_REDUCE_RATIO = 0.5
PARTIAL_BUY_CASH_RATIO = 0.5

FREEZE = {
    "candidate": CANDIDATE_RULE,
    "candidate_freeze_time": "2026-06-21T00:00:00+00:00",
    "source": "P1B reviewed mechanisms only",
    "no_replay_result_selection": True,
    "no_post_replay_rule_adjustment": True,
    "mechanisms": [
        "execution_price_gate",
        "tiny_no_trade_buffer",
        "confidence_gap",
        "min_holding_days_with_exception",
        "turnover_budget",
        "risk_off_raised_threshold",
        "partial_adjustment_after_contract_support",
    ],
    "thresholds": {
        "tiny_min_rank_gap": 1,
        "tiny_min_score_gap": 0.0001,
        "confidence_min_rank_gap": 5,
        "confidence_min_score_gap": 0.01,
        "min_holding_days": 5,
        "deep_exit_full_qlib_rank_threshold": 80,
        "weekly_action_budget": 4,
        "strong_signal_rank_improvement_min": 30,
        "risk_off_weak_signal_rank_improvement_min": 45,
    },
}

FORBIDDEN_INPUT_FIELDS = {
    "future_return_5d", "future_return_10d", "future_return_20d", "replay_return",
    "realized_pnl", "unrealized_pnl", "net_return", "gross_return", "execution_price",
    "next_open", "next_close", "target_position", "target_weight",
}
FORBIDDEN_ORDER_INTENT_FIELDS = {
    "execution_date", "execution_price", "execution_quantity", "quantity_to_buy", "quantity_to_sell",
    "shares", "lots", "target_position", "target_weight", "allocation_weight", "commission",
    "fee", "tax", "cash", "cash_after", "nav", "equity", "daily_return", "realized_pnl",
    "unrealized_pnl", "replay_return", "broker", "broker_order_id", "order_id", "quick_trade",
}


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except Exception:
        return str(path)


def norm(symbol: Any) -> str:
    text = str(symbol or "").strip().upper()
    return text if text.startswith("TW") else f"TW{text}"


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        fields = sorted({key for row in rows for key in row}) if rows else ["status"]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


class PriceStore:
    def __init__(self, symbols: set[str]) -> None:
        self.by_symbol: dict[str, list[dict[str, float | str]]] = {}
        for symbol in sorted(norm(s) for s in symbols):
            path = PRICE_ROOT / f"{symbol}.csv"
            if not path.exists():
                continue
            rows: list[dict[str, float | str]] = []
            with path.open(encoding="utf-8", newline="") as fh:
                for row in csv.DictReader(fh):
                    day = str(row.get("date") or "")[:10]
                    try:
                        open_price = float(row.get("open") or 0.0)
                        close = float(row.get("close") or 0.0)
                    except Exception:
                        open_price = 0.0
                        close = 0.0
                    if day and open_price > 0 and close > 0:
                        rows.append({"date": day, "open": open_price, "close": close})
            if rows:
                self.by_symbol[symbol] = rows

    def close_on_or_before(self, symbol: str, asof: str) -> float | None:
        out = None
        for row in self.by_symbol.get(norm(symbol), []):
            day = str(row["date"])
            if day <= asof:
                out = float(row["close"])
            else:
                break
        return out

    def next_after(self, symbol: str, asof: str) -> tuple[str, float] | None:
        for row in self.by_symbol.get(norm(symbol), []):
            day = str(row["date"])
            if day > asof:
                return day, float(row["open"])
        return None


def load_signals() -> tuple[dict[str, Any], pd.DataFrame]:
    manifest = json.loads(SIGNAL_MANIFEST.read_text(encoding="utf-8"))
    path = ROOT / manifest["output_files"]["signals"]
    df = pd.read_csv(path)
    forbidden = sorted(set(df.columns) & FORBIDDEN_INPUT_FIELDS)
    if forbidden:
        raise RuntimeError("forbidden_signal_fields:" + "|".join(forbidden))
    df["date"] = df["date"].astype(str)
    df["instrument"] = df["instrument"].map(norm)
    for col in ["candidate_rank", "buy_score", "score_rank", "full_qlib_rank"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return manifest, df


def build_state(day: pd.DataFrame) -> dict[str, Any]:
    candidates = day[day["candidate_rank"] <= CANDIDATE_K].dropna(subset=["buy_score"]).copy()
    candidates = candidates.sort_values(["buy_score", "instrument"], ascending=[False, True])
    buy_order = [norm(x) for x in candidates["instrument"].tolist()]
    return {
        "candidate_set": set(day.loc[day["candidate_rank"] <= CANDIDATE_K, "instrument"].map(norm)),
        "buy_order": buy_order,
        "buy_rank": {sym: idx + 1 for idx, sym in enumerate(buy_order)},
        "signal": {norm(row.instrument): row for row in day.itertuples(index=False)},
        "full_rank": {norm(row.instrument): int(row.full_qlib_rank) for row in day.itertuples(index=False) if pd.notna(row.full_qlib_rank)},
    }


def regime_for_day(prices: PriceStore, asof: str) -> str:
    rows = prices.by_symbol.get("TWII", [])
    idx = next((i for i, row in enumerate(rows) if row["date"] == asof), None)
    if idx is None or idx < 20:
        return "normal"
    current = float(rows[idx]["close"])
    prev20 = float(rows[idx - 20]["close"])
    trailing = [float(row["close"]) for row in rows[max(0, idx - 60):idx + 1]]
    drawdown = current / max(trailing) - 1.0 if trailing else 0.0
    ret20 = current / prev20 - 1.0 if prev20 else 0.0
    if drawdown <= -0.12 or ret20 <= -0.08:
        return "risk_off"
    if drawdown <= -0.06 or ret20 <= -0.03:
        return "caution"
    return "normal"


def mark_to_market(cash: float, holdings: dict[str, dict[str, Any]], prices: PriceStore, asof: str) -> tuple[float, float, int]:
    market = 0.0
    missing = 0
    for symbol, pos in holdings.items():
        close = prices.close_on_or_before(symbol, asof)
        if close is None:
            missing += 1
        else:
            market += int(pos["quantity"]) * close
    return cash + market, market, missing


def intent_row(asof: str, symbol: str, action: str, reason: str, state: dict[str, Any], *, rule: str, manifest: dict[str, Any]) -> dict[str, Any]:
    sig = state["signal"].get(norm(symbol))
    return {
        "signal_date": asof,
        "instrument": norm(symbol),
        "intent_action": action,
        "intent_reason": reason,
        "primary_reason_code": reason,
        "strategy_rule": rule,
        "candidate_rank": getattr(sig, "candidate_rank", "") if sig is not None else "",
        "buy_rank": state["buy_rank"].get(norm(symbol), getattr(sig, "score_rank", "") if sig is not None else ""),
        "full_qlib_rank": state["full_rank"].get(norm(symbol), ""),
        "max_buy_count": 1,
        "max_sell_count": 1,
        "model_name": MODEL_NAME,
        "signal_artifact": manifest["output_files"]["signals"],
        "readonly_only": True,
        "simulation_only": True,
        "not_order": True,
        "not_target_position": True,
        "not_investment_advice": True,
    }


def decide_default(asof: str, holdings: dict[str, dict[str, Any]], state: dict[str, Any], manifest: dict[str, Any]) -> list[dict[str, Any]]:
    held = sorted(holdings)
    outside = sorted([s for s in held if s not in state["candidate_set"]], key=lambda s: (state["full_rank"].get(s, 999999), s), reverse=True)
    sells = outside[:1]
    remaining = set(held) - set(sells)
    buys = []
    if len(remaining) < TARGET_HOLDINGS:
        for symbol in state["buy_order"]:
            if symbol not in remaining:
                buys = [symbol]
                break
    rows = [intent_row(asof, s, "sell", "top50_exit_one_worst_sell_sell", state, rule=DEFAULT_RULE, manifest=manifest) for s in sells]
    rows += [intent_row(asof, b, "buy", "top50_exit_one_worst_sell_buy", state, rule=DEFAULT_RULE, manifest=manifest) for b in buys]
    return rows


def weekly_action_count(actions: list[dict[str, Any]], asof: str) -> int:
    day = pd.Timestamp(asof)
    start = day - pd.Timedelta(days=6)
    count = 0
    for row in actions:
        d = pd.to_datetime(row.get("signal_date"), errors="coerce")
        if pd.notna(d) and start <= d <= day and row.get("action") in {"historical_add", "historical_risk_reduce"}:
            count += 1
    return count


def decide_candidate(asof: str, holdings: dict[str, dict[str, Any]], state: dict[str, Any], manifest: dict[str, Any], prices: PriceStore, actions: list[dict[str, Any]], regime: str) -> list[dict[str, Any]]:
    baseline = decide_default(asof, holdings, state, manifest)
    trade_rows = [r for r in baseline if r["intent_action"] in {"buy", "sell"}]
    if not trade_rows:
        return [intent_row(asof, "PORTFOLIO", "skip", "no_action", state, rule=CANDIDATE_RULE, manifest=manifest)]
    if any(prices.next_after(row["instrument"], asof) is None for row in trade_rows):
        return [intent_row(asof, row["instrument"], "skip", "blocked_execution_price_unavailable", state, rule=CANDIDATE_RULE, manifest=manifest) for row in trade_rows]

    sells = [r for r in baseline if r["intent_action"] == "sell"]
    buys = [r for r in baseline if r["intent_action"] == "buy"]
    if sells and buys:
        sell = sells[0]
        buy = buys[0]
        sell_sym = sell["instrument"]
        buy_sym = buy["instrument"]
        sell_sig = state["signal"].get(sell_sym)
        buy_sig = state["signal"].get(buy_sym)
        sell_full = float(state["full_rank"].get(sell_sym, 999999))
        buy_rank = float(getattr(buy_sig, "candidate_rank", 999999) if buy_sig is not None else 999999)
        sell_score = float(getattr(sell_sig, "buy_score", 0.0) if sell_sig is not None and pd.notna(getattr(sell_sig, "buy_score", None)) else 0.0)
        buy_score = float(getattr(buy_sig, "buy_score", 0.0) if buy_sig is not None and pd.notna(getattr(buy_sig, "buy_score", None)) else 0.0)
        rank_improvement = sell_full - buy_rank
        score_gap = buy_score - sell_score
        holding_days = max(0, (pd.Timestamp(asof) - pd.Timestamp(holdings.get(sell_sym, {}).get("entry_date", asof))).days)
        if abs(buy_rank - sell_full) <= FREEZE["thresholds"]["tiny_min_rank_gap"] and score_gap <= FREEZE["thresholds"]["tiny_min_score_gap"]:
            return [intent_row(asof, row["instrument"], "skip", "blocked_tiny_no_trade_buffer", state, rule=CANDIDATE_RULE, manifest=manifest) for row in trade_rows]
        if rank_improvement < FREEZE["thresholds"]["confidence_min_rank_gap"] and score_gap < FREEZE["thresholds"]["confidence_min_score_gap"]:
            return [intent_row(asof, row["instrument"], "skip", "blocked_confidence_gap", state, rule=CANDIDATE_RULE, manifest=manifest) for row in trade_rows]
        if holding_days < FREEZE["thresholds"]["min_holding_days"] and sell_full < FREEZE["thresholds"]["deep_exit_full_qlib_rank_threshold"]:
            return [intent_row(asof, row["instrument"], "skip", "blocked_min_holding_days", state, rule=CANDIDATE_RULE, manifest=manifest) for row in trade_rows]
        strong = rank_improvement >= FREEZE["thresholds"]["strong_signal_rank_improvement_min"]
        if weekly_action_count(actions, asof) >= FREEZE["thresholds"]["weekly_action_budget"] and not strong:
            return [intent_row(asof, row["instrument"], "skip", "blocked_turnover_budget", state, rule=CANDIDATE_RULE, manifest=manifest) for row in trade_rows]
        if regime == "risk_off" and rank_improvement < FREEZE["thresholds"]["risk_off_weak_signal_rank_improvement_min"]:
            return [intent_row(asof, row["instrument"], "skip", "blocked_risk_off_raised_threshold", state, rule=CANDIDATE_RULE, manifest=manifest) for row in trade_rows]

    out = []
    for row in baseline:
        if row["intent_action"] == "sell":
            item = intent_row(asof, row["instrument"], "sell", "simulated_reduce_partial", state, rule=CANDIDATE_RULE, manifest=manifest)
            item["partial_intent_kind"] = "simulated_reduce_partial"
            item["partial_intent_policy"] = "simulation_only_partial_intent"
            item["partial_intent_note"] = "replay_execution_keeps_order_intent_quantity_free"
            out.append(item)
        elif row["intent_action"] == "buy":
            item = intent_row(asof, row["instrument"], "buy", "simulated_buy_small", state, rule=CANDIDATE_RULE, manifest=manifest)
            item["partial_intent_kind"] = "simulated_buy_small"
            item["partial_intent_policy"] = "simulation_only_partial_intent"
            item["partial_intent_note"] = "replay_execution_keeps_order_intent_quantity_free"
            out.append(item)
    return out


def execute_pending(pending: list[dict[str, Any]], asof: str, cash: float, holdings: dict[str, dict[str, Any]], actions: list[dict[str, Any]], rule: str) -> tuple[float, float, int]:
    fee_total = 0.0
    skipped = 0
    for order in sorted(pending, key=lambda x: 0 if x["intent_action"] == "sell" else 1):
        symbol = order["instrument"]
        price = float(order["execution_price"])
        if order["intent_action"] == "sell":
            held_qty = int(holdings.get(symbol, {}).get("quantity", 0))
            qty = held_qty
            if order.get("intent_reason") == "simulated_reduce_partial":
                qty = int((held_qty * PARTIAL_REDUCE_RATIO) // LOT_SIZE) * LOT_SIZE
            if qty <= 0:
                skipped += 1
                actions.append({**order, "action": "historical_skip", "quantity": 0, "fee_and_tax": 0.0, "realized_pnl_after_fee_tax": 0.0, "cash_after": round(cash, 2), "reason": "sell_without_active_holding"})
                continue
            cost_basis = float(holdings.get(symbol, {}).get("cost_basis") or price)
            fee_tax = qty * price * (FEE_RATE + SELL_TAX_RATE)
            realized_pnl = (price - cost_basis) * qty - fee_tax
            cash += qty * price - fee_tax
            fee_total += fee_tax
            remaining_qty = held_qty - qty
            if remaining_qty > 0:
                holdings[symbol]["quantity"] = remaining_qty
            else:
                del holdings[symbol]
            actions.append({**order, "action": "historical_risk_reduce", "quantity": qty, "fee_and_tax": round(fee_tax, 2), "realized_pnl_after_fee_tax": round(realized_pnl, 2), "cash_after": round(cash, 2), "reason": order["intent_reason"]})
        elif order["intent_action"] == "buy":
            slots = max(1, TARGET_HOLDINGS - len(holdings))
            cash_budget = cash / slots
            if order.get("intent_reason") == "simulated_buy_small":
                cash_budget *= PARTIAL_BUY_CASH_RATIO
            qty = int(cash_budget // (price * LOT_SIZE)) * LOT_SIZE
            fee = qty * price * FEE_RATE
            total = qty * price + fee
            if qty <= 0 or cash < total or symbol in holdings or len(holdings) >= TARGET_HOLDINGS:
                skipped += 1
                actions.append({**order, "action": "historical_skip", "quantity": 0, "fee_and_tax": 0.0, "realized_pnl_after_fee_tax": 0.0, "cash_after": round(cash, 2), "reason": "insufficient_cash_duplicate_zero_qty_or_full"})
                continue
            cash -= total
            fee_total += fee
            holdings[symbol] = {"quantity": qty, "entry_date": asof, "cost_basis": price}
            actions.append({**order, "action": "historical_add", "quantity": qty, "fee_and_tax": round(fee, 2), "realized_pnl_after_fee_tax": round(-fee, 2), "cash_after": round(cash, 2), "reason": order["intent_reason"]})
    return cash, fee_total, skipped


def replay(signals: pd.DataFrame, manifest: dict[str, Any], prices: PriceStore, rule: str, start: str, end: str) -> dict[str, Any]:
    sub = signals[(signals["date"] >= start) & (signals["date"] <= end)].copy()
    dates = sorted(sub["date"].unique().tolist())
    holdings: dict[str, dict[str, Any]] = {}
    cash = INITIAL_EQUITY
    fees = 0.0
    skipped = 0
    missing_next_open = 0
    peak = INITIAL_EQUITY
    max_dd = 0.0
    pending_by_date: dict[str, list[dict[str, Any]]] = defaultdict(list)
    actions: list[dict[str, Any]] = []
    order_intents: list[dict[str, Any]] = []
    nav: list[dict[str, Any]] = []
    snapshots: list[dict[str, Any]] = []
    holding_durations: list[int] = []
    no_action_days = 0
    blocked_days = 0

    for asof in dates:
        cash, fee_add, skip_add = execute_pending(pending_by_date.pop(asof, []), asof, cash, holdings, actions, rule)
        fees += fee_add
        skipped += skip_add
        day = sub[sub["date"] == asof]
        state = build_state(day)
        regime = regime_for_day(prices, asof)
        equity, market, missing = mark_to_market(cash, holdings, prices, asof)
        peak = max(peak, equity)
        max_dd = min(max_dd, equity / peak - 1.0 if peak else 0.0)
        prev_equity = float(nav[-1]["equity"]) if nav else equity
        nav.append({
            "date": asof,
            "strategy_rule": rule,
            "model_name": MODEL_NAME,
            "model_family": MODEL_FAMILY,
            "cash": round(cash, 2),
            "market_value": round(market, 2),
            "equity": round(equity, 2),
            "daily_return": round(equity / prev_equity - 1.0, 8) if prev_equity else 0.0,
            "holding_count": len(holdings),
            "missing_price_count": missing,
            "regime_segment": regime,
        })
        for symbol, pos in sorted(holdings.items()):
            mark = prices.close_on_or_before(symbol, asof) or 0.0
            snapshots.append({
                "date": asof,
                "strategy_rule": rule,
                "model_name": MODEL_NAME,
                "instrument": symbol,
                "quantity": int(pos["quantity"]),
                "cost_basis": round(float(pos.get("cost_basis") or 0.0), 4),
                "mark_price": round(mark, 4),
                "market_value": round(int(pos["quantity"]) * mark, 2),
                "unrealized_pnl": round(int(pos["quantity"]) * (mark - float(pos.get("cost_basis") or mark)), 2),
                "holding_days": max(0, (pd.Timestamp(asof) - pd.Timestamp(pos.get("entry_date", asof))).days),
            })
        intents = decide_default(asof, holdings, state, manifest) if rule == DEFAULT_RULE else decide_candidate(asof, holdings, state, manifest, prices, actions, regime)
        if not any(i["intent_action"] in {"buy", "sell"} for i in intents):
            no_action_days += 1
        if any(str(i["intent_reason"]).startswith("blocked_") for i in intents):
            blocked_days += 1
        for intent in intents:
            order_intents.append(intent)
            if intent["intent_action"] not in {"buy", "sell"}:
                continue
            quote = prices.next_after(intent["instrument"], asof)
            if quote is None:
                missing_next_open += 1
                skipped += 1
                continue
            execution_date, execution_price = quote
            pending_by_date[execution_date].append({
                "strategy_rule": rule,
                "model_name": MODEL_NAME,
                "signal_date": asof,
                "execution_date": execution_date,
                "instrument": intent["instrument"],
                "intent_action": intent["intent_action"],
                "intent_reason": intent["intent_reason"],
                "execution_price": round(float(execution_price), 4),
                "execution_price_mode": "next_open",
                "regime_segment": regime,
            })

    # Execute any pending orders whose next execution date is still inside the observed price calendar and after final signal.
    for ex_date in sorted(pending_by_date):
        if ex_date <= end:
            cash, fee_add, skip_add = execute_pending(pending_by_date[ex_date], ex_date, cash, holdings, actions, rule)
            fees += fee_add
            skipped += skip_add
    for row in actions:
        if row.get("action") == "historical_risk_reduce":
            symbol = row["instrument"]
            # Duration is approximated from snapshots prior to sell date.
            ss = [s for s in snapshots if s["instrument"] == symbol and s["date"] <= row["signal_date"]]
            if ss:
                holding_durations.append(int(ss[-1].get("holding_days") or 0))

    active = [a for a in actions if a.get("action") in {"historical_add", "historical_risk_reduce"}]
    notional = sum(abs(float(a.get("quantity") or 0) * float(a.get("execution_price") or 0.0)) for a in active)
    avg_equity = sum(float(n["equity"]) for n in nav) / len(nav) if nav else INITIAL_EQUITY
    final_equity = float(nav[-1]["equity"]) if nav else INITIAL_EQUITY
    summary = {
        "window": "2026H1_forward_readonly_acceptance_partial_to_2026_05_07",
        "model_name": MODEL_NAME,
        "model_family": MODEL_FAMILY,
        "strategy_rule": rule,
        "start_date": dates[0] if dates else start,
        "end_date": dates[-1] if dates else end,
        "initial_cash": INITIAL_EQUITY,
        "final_equity": round(final_equity, 2),
        "net_return_after_fee_tax": round(final_equity / INITIAL_EQUITY - 1.0, 8),
        "gross_return": round((final_equity + fees) / INITIAL_EQUITY - 1.0, 8),
        "max_drawdown": round(max_dd, 8),
        "action_count": len(active),
        "buy_count": sum(1 for a in active if a["action"] == "historical_add"),
        "sell_count": sum(1 for a in active if a["action"] == "historical_risk_reduce"),
        "skip_count": skipped + sum(1 for i in order_intents if i["intent_action"] == "skip"),
        "no_action_days": no_action_days,
        "blocked_days": blocked_days,
        "turnover_proxy": round(notional / avg_equity, 8) if avg_equity else 0.0,
        "turnover_notional": round(notional, 2),
        "fee_and_tax": round(fees, 2),
        "average_holding_days": round(statistics.mean(holding_durations), 4) if holding_durations else 0.0,
        "median_holding_days": round(statistics.median(holding_durations), 4) if holding_durations else 0.0,
        "missing_next_open_count": missing_next_open,
        "execution_block_count": sum(1 for i in order_intents if str(i["intent_reason"]).startswith("blocked_execution")),
        "trading_days": len(nav),
        "readonly_only": True,
        "simulation_only": True,
        "not_order": True,
        "not_target_position": True,
        "not_investment_advice": True,
    }
    return {"summary": summary, "nav": nav, "actions": actions, "snapshots": snapshots, "order_intents": order_intents}


def aggregate_regime(nav: list[dict[str, Any]], summary: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for regime, items in sorted(defaultdict(list, {r: [n for n in nav if n["regime_segment"] == r] for r in {n["regime_segment"] for n in nav}}).items()):
        if not items:
            continue
        start_eq = float(items[0]["equity"])
        end_eq = float(items[-1]["equity"])
        rows.append({"strategy_rule": summary["strategy_rule"], "regime_segment": regime, "day_count": len(items), "segment_return": round(end_eq / start_eq - 1.0, 8) if start_eq else 0.0, "avg_daily_return": round(statistics.mean(float(i["daily_return"]) for i in items), 8)})
    return rows


def yearly(nav: list[dict[str, Any]], summary: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    by_year: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for n in nav:
        by_year[str(n["date"])[:4]].append(n)
    for year, items in sorted(by_year.items()):
        start_eq = float(items[0]["equity"])
        end_eq = float(items[-1]["equity"])
        rows.append({"strategy_rule": summary["strategy_rule"], "year": year, "start_date": items[0]["date"], "end_date": items[-1]["date"], "trading_days": len(items), "return": round(end_eq / start_eq - 1.0, 8) if start_eq else 0.0})
    return rows


def rolling(nav: list[dict[str, Any]], summary: dict[str, Any], window: int, name: str) -> list[dict[str, Any]]:
    rows = []
    if len(nav) < 2:
        return rows
    step = max(1, window // 3)
    for start in range(0, len(nav), step):
        chunk = nav[start:start + window]
        if len(chunk) < min(window, len(nav)) and start != 0:
            continue
        start_eq = float(chunk[0]["equity"])
        end_eq = float(chunk[-1]["equity"])
        peak = start_eq
        dd = 0.0
        for row in chunk:
            eq = float(row["equity"])
            peak = max(peak, eq)
            dd = min(dd, eq / peak - 1.0 if peak else 0.0)
        rows.append({"strategy_rule": summary["strategy_rule"], "rolling_window": name, "start_date": chunk[0]["date"], "end_date": chunk[-1]["date"], "day_count": len(chunk), "return": round(end_eq / start_eq - 1.0, 8) if start_eq else 0.0, "max_drawdown": round(dd, 8)})
    return rows


def concentration(actions: list[dict[str, Any]], snapshots: list[dict[str, Any]], summary: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    realized: dict[str, float] = defaultdict(float)
    cost: dict[str, float] = defaultdict(float)
    turnover: dict[str, float] = defaultdict(float)
    for a in actions:
        if a.get("action") not in {"historical_add", "historical_risk_reduce"}:
            continue
        symbol = a["instrument"]
        notional = abs(float(a.get("quantity") or 0) * float(a.get("execution_price") or 0.0))
        turnover[symbol] += notional
        cost[symbol] += -float(a.get("fee_and_tax") or 0.0)
        realized[symbol] += float(a.get("realized_pnl_after_fee_tax") or 0.0)
    latest_snapshot_by_symbol: dict[str, dict[str, Any]] = {}
    for row in snapshots:
        latest_snapshot_by_symbol[row["instrument"]] = row
    unrealized = {symbol: float(row.get("unrealized_pnl") or 0.0) for symbol, row in latest_snapshot_by_symbol.items()}
    symbols = set(realized) | set(unrealized)
    total_by_symbol = {symbol: realized.get(symbol, 0.0) + unrealized.get(symbol, 0.0) for symbol in symbols}
    total_abs_pnl = sum(abs(value) for value in total_by_symbol.values()) or 1.0
    total_turnover = sum(turnover.values()) or 1.0
    pnl_rows = [{
        "strategy_rule": summary["strategy_rule"],
        "instrument": s,
        "realized_pnl_after_fee_tax": round(realized.get(s, 0.0), 2),
        "unrealized_pnl": round(unrealized.get(s, 0.0), 2),
        "total_pnl_after_fee_tax": round(total_by_symbol[s], 2),
        "pnl_contribution_share": round(abs(total_by_symbol[s]) / total_abs_pnl, 8),
    } for s in sorted(total_by_symbol, key=lambda symbol: abs(total_by_symbol[symbol]), reverse=True)[:20]]
    cost_rows = [{"strategy_rule": summary["strategy_rule"], "instrument": s, "cost_after_fee_tax": round(v, 2)} for s, v in sorted(cost.items(), key=lambda kv: abs(kv[1]), reverse=True)[:20]]
    turn_rows = [{"strategy_rule": summary["strategy_rule"], "instrument": s, "turnover_notional": round(v, 2), "turnover_share": round(v / total_turnover, 8)} for s, v in sorted(turnover.items(), key=lambda kv: kv[1], reverse=True)[:20]]
    return pnl_rows, cost_rows, turn_rows


def forbidden_audit(order_intents: list[dict[str, Any]], signal_columns: list[str]) -> list[dict[str, Any]]:
    rows = []
    for field in sorted(FORBIDDEN_INPUT_FIELDS):
        rows.append({"audit_name": "forbidden_input_field", "artifact": rel(SIGNAL_MANIFEST), "field_name": field, "present": field in signal_columns, "used_for_ranking": False, "status": "fail" if field in signal_columns else "pass"})
    fields = {k for row in order_intents for k in row}
    for field in sorted(FORBIDDEN_ORDER_INTENT_FIELDS):
        rows.append({"audit_name": "forbidden_order_intent_field", "artifact": "p2_dry_run_order_intents", "field_name": field, "present": field in fields, "used_for_ranking": False, "status": "fail" if field in fields else "pass"})
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Run readonly P2 replay pressure test for portfolio_decision_optimizer_v1.")
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT))
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    manifest, signals = load_signals()
    start = "2026-01-01"
    end = "2026-05-07"
    symbols = set(signals["instrument"].map(norm)) | {"TWII"}
    prices = PriceStore(symbols)
    if not prices.by_symbol:
        raise RuntimeError("price_store_empty")

    default = replay(signals, manifest, prices, DEFAULT_RULE, start, end)
    candidate = replay(signals, manifest, prices, CANDIDATE_RULE, start, end)
    results = [default, candidate]

    summary = [r["summary"] for r in results]
    nav = [row for r in results for row in r["nav"]]
    actions = [row for r in results for row in r["actions"]]
    order_intents = [row for r in results for row in r["order_intents"]]
    snapshots = [row for r in results for row in r["snapshots"]]
    regime_rows = [row for r in results for row in aggregate_regime(r["nav"], r["summary"])]
    yearly_rows = [row for r in results for row in yearly(r["nav"], r["summary"])]
    rolling3 = [row for r in results for row in rolling(r["nav"], r["summary"], 63, "3m")]
    rolling6 = [row for r in results for row in rolling(r["nav"], r["summary"], 126, "6m_or_available")]
    pnl_rows: list[dict[str, Any]] = []
    cost_rows: list[dict[str, Any]] = []
    turn_rows: list[dict[str, Any]] = []
    for r in results:
        p, c, t = concentration(r["actions"], r["snapshots"], r["summary"])
        pnl_rows.extend(p)
        cost_rows.extend(c)
        turn_rows.extend(t)
    audit = forbidden_audit(order_intents, list(signals.columns))
    coverage = [{
        "window": "2026H1_forward_readonly_acceptance_partial_to_2026_05_07",
        "requested_start_date": start,
        "requested_end_date": end,
        "actual_start_date": min(signals["date"]),
        "actual_end_date": max(signals["date"]),
        "signal_row_count": int(len(signals)),
        "price_symbol_count": int(len(prices.by_symbol)),
        "strict_forward_acceptance": True,
        "2023_2025_engineering_diagnostic_available": False,
        "2023_2025_gap_reason": "No local standard ModelSignalArtifact for portfolio_decision_optimizer_v1 candidate over 2023-2025; no provider refresh or network fetch performed.",
        "status": "pass_with_documented_2023_2025_gap",
    }]

    write_csv(out / "p2_summary.csv", summary)
    write_csv(out / "p2_daily_nav.csv", nav)
    write_csv(out / "p2_actions.csv", actions)
    write_csv(out / "p2_order_intents_dry_run.csv", order_intents)
    write_csv(out / "p2_position_snapshots.csv", snapshots)
    write_csv(out / "p2_regime_segment_metrics.csv", regime_rows)
    write_csv(out / "p2_yearly_metrics.csv", yearly_rows)
    write_csv(out / "p2_rolling_3m_metrics.csv", rolling3)
    write_csv(out / "p2_rolling_6m_metrics.csv", rolling6)
    write_csv(out / "p2_pnl_concentration.csv", pnl_rows)
    write_csv(out / "p2_cost_concentration.csv", cost_rows)
    write_csv(out / "p2_symbol_turnover_concentration.csv", turn_rows)
    write_csv(out / "p2_forbidden_input_output_audit.csv", audit)
    write_csv(out / "p2_coverage_audit.csv", coverage)
    write_json(out / "p2_candidate_freeze.json", FREEZE)
    run_manifest = {
        "artifact_type": "portfolio_decision_optimizer_p2_readonly_replay_pressure_test",
        "created_at": now(),
        "created_by": rel(Path(__file__)),
        "output_dir": rel(out),
        "default": DEFAULT_RULE,
        "candidate": CANDIDATE_RULE,
        "candidate_freeze": FREEZE,
        "model_name": MODEL_NAME,
        "signal_manifest": rel(SIGNAL_MANIFEST),
        "price_root": rel(PRICE_ROOT),
        "outputs": {
            "summary": rel(out / "p2_summary.csv"),
            "daily_nav": rel(out / "p2_daily_nav.csv"),
            "actions": rel(out / "p2_actions.csv"),
            "dry_run_order_intents": rel(out / "p2_order_intents_dry_run.csv"),
            "regime_segment_metrics": rel(out / "p2_regime_segment_metrics.csv"),
            "yearly_metrics": rel(out / "p2_yearly_metrics.csv"),
            "rolling_3m_metrics": rel(out / "p2_rolling_3m_metrics.csv"),
            "rolling_6m_metrics": rel(out / "p2_rolling_6m_metrics.csv"),
            "pnl_concentration": rel(out / "p2_pnl_concentration.csv"),
            "cost_concentration": rel(out / "p2_cost_concentration.csv"),
            "symbol_turnover_concentration": rel(out / "p2_symbol_turnover_concentration.csv"),
            "forbidden_input_output_audit": rel(out / "p2_forbidden_input_output_audit.csv"),
            "coverage_audit": rel(out / "p2_coverage_audit.csv"),
        },
        "readonly_only": True,
        "simulation_only": True,
        "not_order": True,
        "not_target_position": True,
        "not_investment_advice": True,
        "no_provider_publish": True,
        "no_accepted_latest_switch": True,
        "no_monitor_write": True,
        "no_broker_quick_trade_order": True,
        "execution_price_mode": "next_open",
        "partial_replay_mapping": {
            "simulated_reduce_partial": f"sell {PARTIAL_REDUCE_RATIO:.2f} of active replay quantity, rounded down to lot size",
            "simulated_buy_small": f"use {PARTIAL_BUY_CASH_RATIO:.2f} of replay slot cash budget, rounded down to lot size",
        },
        "pnl_concentration_method": {
            "realized_pnl_after_fee_tax": "sum replay action realized_pnl_after_fee_tax by instrument; buys contribute negative buy fee, sells/reductions contribute (execution_price - cost_basis) * quantity minus sell fee and tax",
            "unrealized_pnl": "latest replay position snapshot unrealized_pnl by instrument at final available replay date",
            "total_pnl_after_fee_tax": "realized_pnl_after_fee_tax + unrealized_pnl",
            "pnl_contribution_share": "abs(total_pnl_after_fee_tax) divided by sum abs(total_pnl_after_fee_tax) within the same strategy_rule",
            "cost_concentration": "fee/tax concentration preserved separately in p2_cost_concentration.csv and no longer labeled as PnL concentration",
        },
    }
    write_json(out / "manifest.json", run_manifest)
    payload = {"ok": True, "manifest": rel(out / "manifest.json"), "summary": summary, "coverage": coverage[0]}
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print("ok=true")
        print("manifest=" + payload["manifest"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
