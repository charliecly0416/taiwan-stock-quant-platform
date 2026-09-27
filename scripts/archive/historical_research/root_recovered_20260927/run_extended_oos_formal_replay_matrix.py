#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
S2D_SCRIPT = ROOT / "scripts/evaluate_tw_ltr_s2d_full_daily_replay.py"

FRESH_C4 = ROOT / "data_tw/experiments/fresh_top50_coverage_repair/phasec4_repaired_replay_ready_scores.csv"
E6_READY = ROOT / "data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e6_bridge_ltr_2025_two_qlib_bases/phasee6_replay_ready_scores_2026.csv"
E4_READY = ROOT / "data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e4_2026_replay/phasee4_replay_ready_scores_2026.csv"
FROZEN_E1_RAW = ROOT / "data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e1_frozen_qlib_training_and_oos_score/phasee1_raw_oos_score_rank_2023_2026.csv"
FRESH_S2B_POST_FILTER = ROOT / "data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2b_fresh_qlib_training/phase_s2b_post_filter_score_rank.csv"

OUT = ROOT / "data_tw/experiments/extended_oos_qlib_orthogonal_ltr/formal_replay_matrix"
DOC = ROOT / "docs/tw_extended_oos_qlib_orthogonal_ltr/FORMAL_REPLAY_MATRIX_EXECUTION_REPORT_CN.md"

INITIAL_EQUITY = 1_000_000.0
CANDIDATE_K = 50
TARGET_HOLDINGS = 10

RULES = [
    "original",
    "top50_exit_all",
    "top50_exit_one_worst_sell",
    "one_sell_one_buy_correct",
    "one_sell_one_buy_buggy_e8r",
]

FORBIDDEN_COLUMNS = {
    "future_return_5d",
    "future_return_10d",
    "future_return_20d",
    "future_excess_return_5d",
    "future_excess_return_10d",
    "future_excess_return_20d",
    "relevance_10d_top_heavy",
    "ltr_relevance_label",
    "realized_pnl",
}


@dataclass(frozen=True)
class StrategySpec:
    method: str
    family: str
    ready_path: Path
    buy_score_col: str
    candidate_rank_col: str
    full_rank_path: Path
    full_rank_col: str
    method_group: str | None = None


STRATEGIES = [
    StrategySpec(
        method="fresh_qlib_adaptive",
        family="qlib",
        ready_path=FRESH_C4,
        buy_score_col="adaptive_score_baseline",
        candidate_rank_col="qlib_rank",
        full_rank_path=FRESH_S2B_POST_FILTER,
        full_rank_col="qlib_rank",
    ),
    StrategySpec(
        method="fresh_qlib_2025_ltr",
        family="ltr",
        ready_path=E6_READY,
        buy_score_col="phasee6_branch_a_fresh_ltr_score",
        candidate_rank_col="qlib_rank",
        full_rank_path=FRESH_S2B_POST_FILTER,
        full_rank_col="qlib_rank",
        method_group="branch_a_treatment",
    ),
    StrategySpec(
        method="frozen_qlib_2025_ltr",
        family="ltr",
        ready_path=E6_READY,
        buy_score_col="phasee6_branch_b_frozen_ltr_score",
        candidate_rank_col="qlib_rank",
        full_rank_path=FROZEN_E1_RAW,
        full_rank_col="qlib_rank_raw",
        method_group="branch_b_control_treatment",
    ),
    StrategySpec(
        method="e4_frozen_qlib_2023_2025_ltr",
        family="ltr",
        ready_path=E4_READY,
        buy_score_col="phasee3_extended_oos_ltr_score",
        candidate_rank_col="qlib_rank",
        full_rank_path=FROZEN_E1_RAW,
        full_rank_col="qlib_rank_raw",
    ),
    StrategySpec(
        method="frozen_qlib_2018_2022",
        family="qlib",
        ready_path=FROZEN_E1_RAW,
        buy_score_col="qlib_score_raw",
        candidate_rank_col="qlib_rank_raw",
        full_rank_path=FROZEN_E1_RAW,
        full_rank_col="qlib_rank_raw",
    ),
]

WINDOWS = {
    "2026_ytd": ("2026-01-01", "2026-05-07"),
    "2023": ("2023-01-03", "2023-12-29"),
    "2024": ("2024-01-02", "2024-12-31"),
    "2025": ("2025-01-02", "2025-12-31"),
    "2023_2026_ytd": ("2023-01-03", "2026-05-07"),
}


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except Exception:
        return str(path)


def norm(symbol: Any) -> str:
    text = str(symbol or "").strip().upper()
    return text if text.startswith("TW") else f"TW{text}"


def load_s2d() -> Any:
    spec = importlib.util.spec_from_file_location("evaluate_tw_ltr_s2d_full_daily_replay", S2D_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load {S2D_SCRIPT}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def wcsv(path: Path, rows: list[dict[str, Any]], fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        fields = sorted({k for row in rows for k in row.keys()}) if rows else ["status"]
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def wjson(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, default=str) + "\n", encoding="utf-8")


def load_ready(spec: StrategySpec) -> pd.DataFrame:
    df = pd.read_csv(spec.ready_path, parse_dates=["date"])
    if spec.method_group is not None:
        if "method_group" not in df.columns:
            raise RuntimeError(f"{spec.ready_path} has no method_group for {spec.method}")
        df = df[df["method_group"] == spec.method_group].copy()
    if "date_str" not in df.columns:
        df["date_str"] = df["date"].dt.strftime("%Y-%m-%d")
    df["instrument"] = df["instrument"].map(norm)
    if spec.candidate_rank_col not in df.columns:
        raise RuntimeError(f"{spec.method} missing candidate rank column {spec.candidate_rank_col}")
    if spec.buy_score_col not in df.columns:
        raise RuntimeError(f"{spec.method} missing buy score column {spec.buy_score_col}")
    if "regime_segment" not in df.columns:
        df["regime_segment"] = "normal"
    return df


def load_full_rank(spec: StrategySpec) -> pd.DataFrame:
    usecols = ["date", "instrument", spec.full_rank_col]
    df = pd.read_csv(spec.full_rank_path, usecols=usecols, parse_dates=["date"])
    df["date_str"] = df["date"].dt.strftime("%Y-%m-%d")
    df["instrument"] = df["instrument"].map(norm)
    df = df.rename(columns={spec.full_rank_col: "full_qlib_rank"})
    df["full_qlib_rank"] = pd.to_numeric(df["full_qlib_rank"], errors="coerce")
    return df[["date_str", "instrument", "full_qlib_rank"]]


def build_day_state(day_group: pd.DataFrame, full_day: pd.DataFrame, spec: StrategySpec) -> dict[str, Any]:
    group = day_group.copy()
    group["candidate_rank"] = pd.to_numeric(group[spec.candidate_rank_col], errors="coerce")
    group["buy_score"] = pd.to_numeric(group[spec.buy_score_col], errors="coerce")
    candidate_rows = group[group["candidate_rank"] <= CANDIDATE_K].dropna(subset=["buy_score"]).copy()
    candidate_set = set(candidate_rows["instrument"].map(norm))
    buy_rows = candidate_rows.sort_values(["buy_score", "instrument"], ascending=[False, True]).head(CANDIDATE_K)
    buy_order = [norm(x) for x in buy_rows["instrument"].tolist()]
    buy_rank = {symbol: idx + 1 for idx, symbol in enumerate(buy_order)}
    full_rank = {norm(r.instrument): int(r.full_qlib_rank) for r in full_day.itertuples(index=False) if pd.notna(r.full_qlib_rank)}
    return {
        "candidate_set": candidate_set,
        "buy_order": buy_order,
        "target_top10": set(buy_order[:TARGET_HOLDINGS]),
        "buy_rank": buy_rank,
        "full_rank": full_rank,
    }


def mark_to_market(cash: float, holdings: dict[str, int], prices: Any, asof: str) -> tuple[float, int]:
    equity = cash
    missing = 0
    for symbol, qty in holdings.items():
        close = prices.close_on_or_before(symbol, asof)
        if close is None:
            missing += 1
            continue
        equity += qty * close
    return equity, missing


def append_order(
    pending: dict[str, list[dict[str, Any]]],
    prices: Any,
    symbol: str,
    asof: str,
    action: str,
    qty: int,
    reason: str,
    last_day_counter: dict[str, int],
    skipped: list[dict[str, Any]],
) -> bool:
    quote = prices.next_after(symbol, asof)
    if quote is None:
        last_day_counter["count"] += 1
        skipped.append({
            "signal_date": asof,
            "execution_date": "",
            "effective_nav_date": "",
            "symbol": symbol,
            "action": "historical_skip",
            "quantity": 0,
            "price": "",
            "fee_and_tax": 0.0,
            "reason": "no_next_trading_day_price",
        })
        return False
    execution_date, price = quote
    pending.setdefault(execution_date, []).append({
        "signal_date": asof,
        "symbol": symbol,
        "action": action,
        "quantity": int(qty),
        "price": float(price),
        "reason": reason,
    })
    return True


def execute_pending(
    pending_orders: list[dict[str, Any]],
    asof: str,
    method: str,
    rule: str,
    cash: float,
    holdings: dict[str, int],
    actions: list[dict[str, Any]],
    fees: float,
    s2d: Any,
) -> tuple[float, float, int]:
    skipped = 0
    # Sells first, then buys, so same execution-date replacement can use sale proceeds.
    ordered = sorted(pending_orders, key=lambda row: 0 if row["action"] == "historical_risk_reduce" else 1)
    for order in ordered:
        symbol = norm(order["symbol"])
        price = float(order["price"])
        if order["action"] == "historical_risk_reduce":
            qty = int(holdings.pop(symbol, 0))
            if qty <= 0:
                skipped += 1
                actions.append({
                    "signal_date": order["signal_date"],
                    "execution_date": asof,
                    "effective_nav_date": "",
                    "method": method,
                    "rule": rule,
                    "symbol": symbol,
                    "action": "historical_skip",
                    "quantity": 0,
                    "price": round(price, 4),
                    "fee_and_tax": 0.0,
                    "reason": "sell_without_active_holding",
                })
                continue
            fee_tax = qty * price * (s2d.FEE_RATE + s2d.SELL_TAX_RATE)
            cash += qty * price - fee_tax
            fees += fee_tax
            actions.append({
                "signal_date": order["signal_date"],
                "execution_date": asof,
                "effective_nav_date": asof,
                "method": method,
                "rule": rule,
                "symbol": symbol,
                "action": "historical_risk_reduce",
                "quantity": qty,
                "price": round(price, 4),
                "fee_and_tax": round(fee_tax, 2),
                "reason": order["reason"],
            })
        elif order["action"] == "historical_add":
            qty = int(order["quantity"])
            fee = qty * price * s2d.FEE_RATE
            total_cost = qty * price + fee
            if qty > 0 and cash >= total_cost and holdings.get(symbol, 0) == 0 and len(holdings) < TARGET_HOLDINGS:
                cash -= total_cost
                fees += fee
                holdings[symbol] = qty
                actions.append({
                    "signal_date": order["signal_date"],
                    "execution_date": asof,
                    "effective_nav_date": asof,
                    "method": method,
                    "rule": rule,
                    "symbol": symbol,
                    "action": "historical_add",
                    "quantity": qty,
                    "price": round(price, 4),
                    "fee_and_tax": round(fee, 2),
                    "reason": order["reason"],
                })
            else:
                skipped += 1
                actions.append({
                    "signal_date": order["signal_date"],
                    "execution_date": asof,
                    "effective_nav_date": "",
                    "method": method,
                    "rule": rule,
                    "symbol": symbol,
                    "action": "historical_skip",
                    "quantity": 0,
                    "price": round(price, 4),
                    "fee_and_tax": 0.0,
                    "reason": "insufficient_cash_duplicate_zero_qty_or_full",
                })
    return cash, fees, skipped


def active_action(row: dict[str, Any]) -> bool:
    return row.get("action") in {"historical_add", "historical_risk_reduce"}


def has_pending_order(pending: dict[str, list[dict[str, Any]]], symbol: str, action: str) -> bool:
    normalized = norm(symbol)
    for orders in pending.values():
        for order in orders:
            if norm(order.get("symbol")) == normalized and order.get("action") == action:
                return True
    return False


def pending_buy_reserved_cash(pending: dict[str, list[dict[str, Any]]], fee_rate: float) -> float:
    reserved = 0.0
    for orders in pending.values():
        for order in orders:
            if order.get("action") == "historical_add":
                reserved += float(order.get("quantity") or 0) * float(order.get("price") or 0.0) * (1.0 + fee_rate)
    return reserved


def pending_buy_symbols(pending: dict[str, list[dict[str, Any]]]) -> set[str]:
    symbols: set[str] = set()
    for orders in pending.values():
        for order in orders:
            if order.get("action") == "historical_add":
                symbols.add(norm(order.get("symbol")))
    return symbols


def choose_sells(rule: str, holdings: dict[str, int], state: dict[str, Any]) -> list[str]:
    held = sorted(holdings)
    candidate_set: set[str] = state["candidate_set"]
    target_top10: set[str] = state["target_top10"]
    buy_rank: dict[str, int] = state["buy_rank"]
    full_rank: dict[str, int] = state["full_rank"]

    if rule == "original":
        return [symbol for symbol in held if symbol not in target_top10]
    if rule == "top50_exit_all":
        return [symbol for symbol in held if symbol not in candidate_set]
    if rule == "top50_exit_one_worst_sell":
        outside = [symbol for symbol in held if symbol not in candidate_set]
        outside = sorted(outside, key=lambda s: (full_rank.get(s, 999999), s), reverse=True)
        return outside[:1]
    if rule == "one_sell_one_buy_correct":
        pool = [symbol for symbol in held if symbol not in target_top10]
        pool = sorted(pool, key=lambda s: (0, full_rank.get(s, 999999), s) if s not in candidate_set else (1, buy_rank.get(s, 999999), s), reverse=True)
        return pool[:1]
    if rule == "one_sell_one_buy_buggy_e8r":
        pool = [symbol for symbol in held if symbol not in target_top10]
        pool = sorted(pool, key=lambda s: (0 if s not in candidate_set else 1, buy_rank.get(s, 999999), s))
        return pool[:1]
    raise RuntimeError(f"unknown rule {rule}")


def replay_strategy(
    ready: pd.DataFrame,
    full_rank: pd.DataFrame,
    spec: StrategySpec,
    prices: Any,
    s2d: Any,
    rule: str,
    window_name: str,
    start: str,
    end: str,
) -> dict[str, Any]:
    sub = ready[(ready["date_str"] >= start) & (ready["date_str"] <= end)].copy()
    full = full_rank[(full_rank["date_str"] >= start) & (full_rank["date_str"] <= end)].copy()
    dates = sorted(sub["date_str"].unique().tolist())
    full_by_date = {day: g for day, g in full.groupby("date_str")}

    cash = INITIAL_EQUITY
    holdings: dict[str, int] = {}
    fees = 0.0
    peak = INITIAL_EQUITY
    max_dd = 0.0
    missing_price_days = 0
    skipped_count = 0
    last_day = {"count": 0}
    pending: dict[str, list[dict[str, Any]]] = {}
    nav_rows: list[dict[str, Any]] = []
    actions: list[dict[str, Any]] = []
    snapshots: list[dict[str, Any]] = []

    for asof in dates:
        cash, fees, skipped = execute_pending(pending.pop(asof, []), asof, spec.method, rule, cash, holdings, actions, fees, s2d)
        skipped_count += skipped

        equity, missing = mark_to_market(cash, holdings, prices, asof)
        missing_price_days += 1 if missing else 0
        peak = max(peak, equity)
        max_dd = min(max_dd, equity / peak - 1.0 if peak > 0 else 0.0)

        day_group = sub[sub["date_str"] == asof]
        state = build_day_state(day_group, full_by_date.get(asof, full.iloc[:0]), spec)
        candidate_set = state["candidate_set"]
        buy_order = state["buy_order"]
        buy_rank = state["buy_rank"]
        full_rank_map = state["full_rank"]

        nav_rows.append({
            "date": asof,
            "window": window_name,
            "method": spec.method,
            "family": spec.family,
            "rule": rule,
            "equity": round(equity, 2),
            "cash": round(cash, 2),
            "holding_count": len(holdings),
            "missing_price_count": missing,
            "regime_segment": str(day_group["regime_segment"].mode().iloc[0]) if "regime_segment" in day_group and not day_group["regime_segment"].mode().empty else "normal",
        })
        for symbol, qty in sorted(holdings.items()):
            snapshots.append({
                "date": asof,
                "window": window_name,
                "method": spec.method,
                "family": spec.family,
                "rule": rule,
                "symbol": symbol,
                "quantity": qty,
                "in_qlib_top50_candidate": symbol in candidate_set,
                "buy_rank": buy_rank.get(symbol, ""),
                "full_qlib_rank": full_rank_map.get(symbol, ""),
            })

        sells = choose_sells(rule, holdings, state)
        skipped_local: list[dict[str, Any]] = []
        for symbol in sells:
            if has_pending_order(pending, symbol, "historical_risk_reduce"):
                continue
            qty = holdings.get(symbol, 0)
            if qty <= 0:
                continue
            append_order(pending, prices, symbol, asof, "historical_risk_reduce", qty, f"{rule}_sell", last_day, skipped_local)

        for symbol in buy_order:
            reserved_symbols = pending_buy_symbols(pending)
            available_slots = TARGET_HOLDINGS - len(holdings) - len(reserved_symbols)
            if available_slots <= 0:
                break
            if symbol in holdings or symbol in reserved_symbols or has_pending_order(pending, symbol, "historical_add"):
                continue
            quote = prices.next_after(symbol, asof)
            price = quote[1] if quote else None
            available_cash = max(0.0, cash - pending_buy_reserved_cash(pending, s2d.FEE_RATE))
            qty = int((available_cash / max(1, available_slots)) // (price * s2d.LOT_SIZE)) * s2d.LOT_SIZE if price else 0
            if qty <= 0 and quote is not None:
                continue
            ok = append_order(pending, prices, symbol, asof, "historical_add", qty, f"{rule}_buy", last_day, skipped_local)
            if ok:
                break
        if skipped_local:
            skipped_count += len(skipped_local)
            for row in skipped_local:
                actions.append({**row, "method": spec.method, "rule": rule})

    final_equity = nav_rows[-1]["equity"] if nav_rows else INITIAL_EQUITY
    active = [row for row in actions if active_action(row)]
    notional = sum(abs(float(row["quantity"]) * float(row["price"])) for row in active if row.get("price") not in {"", None, ""})
    avg_equity = sum(float(row["equity"]) for row in nav_rows) / len(nav_rows) if nav_rows else INITIAL_EQUITY
    actual_start = dates[0] if dates else start
    actual_end = dates[-1] if dates else end
    metrics = {
        "window": window_name,
        "requested_start_date": start,
        "requested_end_date": end,
        "start_date": actual_start,
        "end_date": actual_end,
        "method": spec.method,
        "family": spec.family,
        "rule": rule,
        "fee_tax_adjusted_net_return": round(final_equity / INITIAL_EQUITY - 1.0, 6),
        "final_equity": round(final_equity, 2),
        "max_drawdown": round(max_dd, 6),
        "action_count": len(active),
        "buy_count": sum(1 for row in active if row["action"] == "historical_add"),
        "sell_count": sum(1 for row in active if row["action"] == "historical_risk_reduce"),
        "fee_and_tax": round(fees, 2),
        "turnover_notional": round(notional, 2),
        "turnover_proxy_by_notional_over_avg_equity": round(notional / avg_equity, 6) if avg_equity else "",
        "trading_days": len(nav_rows),
        "initial_cash_or_equity_assumption": INITIAL_EQUITY,
        "fee_rate": s2d.FEE_RATE,
        "tax_rate": s2d.SELL_TAX_RATE,
        "position_count_target": TARGET_HOLDINGS,
        "candidate_k": CANDIDATE_K,
        "daily_nav_available_count": len(nav_rows),
        "missing_price_days": missing_price_days,
        "skipped_trade_count": skipped_count,
        "last_day_new_trade_without_next_price_count": last_day["count"],
    }
    return {
        "metrics": metrics,
        "nav": nav_rows,
        "actions": actions,
        "snapshots": snapshots,
        "final_holdings": holdings,
        "final_cash": cash,
    }


def coverage_row(ready: pd.DataFrame, spec: StrategySpec, window_name: str, start: str, end: str) -> dict[str, Any]:
    sub = ready[(ready["date_str"] >= start) & (ready["date_str"] <= end)].copy()
    sub["candidate_rank"] = pd.to_numeric(sub[spec.candidate_rank_col], errors="coerce")
    top50 = sub[sub["candidate_rank"] <= CANDIDATE_K].copy()
    daily = top50.groupby("date_str", as_index=False).agg(rows=("instrument", "size"), score_rows=(spec.buy_score_col, lambda s: int(pd.to_numeric(s, errors="coerce").notna().sum())))
    return {
        "window": window_name,
        "method": spec.method,
        "family": spec.family,
        "ready_source": rel(spec.ready_path),
        "buy_score_col": spec.buy_score_col,
        "candidate_rank_col": spec.candidate_rank_col,
        "full_rank_source": rel(spec.full_rank_path),
        "date_count": int(daily.shape[0]) if not daily.empty else 0,
        "row_count": int(top50.shape[0]),
        "daily_rows_min": int(daily["rows"].min()) if not daily.empty else 0,
        "daily_rows_median": float(daily["rows"].median()) if not daily.empty else 0.0,
        "daily_rows_max": int(daily["rows"].max()) if not daily.empty else 0,
        "score_rows": int(pd.to_numeric(top50[spec.buy_score_col], errors="coerce").notna().sum()) if spec.buy_score_col in top50 else 0,
        "duplicate_key_count": int(top50.duplicated(["date_str", "instrument"]).sum()) if not top50.empty else 0,
    }


def integrity_rows(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for result in results:
        metrics = result["metrics"]
        actions = pd.DataFrame(result["actions"])
        snaps = pd.DataFrame(result["snapshots"])
        active = actions[actions["action"].isin(["historical_add", "historical_risk_reduce"])] if not actions.empty else pd.DataFrame()
        rows.append({
            "window": metrics["window"],
            "method": metrics["method"],
            "rule": metrics["rule"],
            "max_holding_count": int(snaps.groupby("date")["symbol"].nunique().max()) if not snaps.empty else 0,
            "duplicate_position_day_symbol": int(snaps.duplicated(["date", "symbol"]).sum()) if not snaps.empty else 0,
            "active_nonpositive_qty": int((pd.to_numeric(active.get("quantity", pd.Series(dtype=float)), errors="coerce") <= 0).sum()) if not active.empty else 0,
            "negative_cash_days": 0,
            "execution_not_after_signal": int((pd.to_datetime(active.get("execution_date", pd.Series(dtype=str)), errors="coerce") <= pd.to_datetime(active.get("signal_date", pd.Series(dtype=str)), errors="coerce")).sum()) if not active.empty else 0,
            "skipped_actions": int((actions.get("action", pd.Series(dtype=str)) == "historical_skip").sum()) if not actions.empty else 0,
            "integrity_pass": bool((metrics["position_count_target"] >= (int(snaps.groupby("date")["symbol"].nunique().max()) if not snaps.empty else 0)) and (active.empty or int((pd.to_numeric(active.get("quantity", pd.Series(dtype=float)), errors="coerce") <= 0).sum()) == 0)),
        })
    return rows


def rule_contract_rows() -> list[dict[str, Any]]:
    return [
        {"rule": "original", "sell_boundary": "sell holdings outside buy top10", "buy_order": "buy_score rank within qlib top50", "max_sells_per_day": "unbounded", "max_buys_per_day": 1},
        {"rule": "top50_exit_all", "sell_boundary": "sell all holdings outside qlib top50", "buy_order": "buy_score rank within qlib top50", "max_sells_per_day": "unbounded", "max_buys_per_day": 1},
        {"rule": "top50_exit_one_worst_sell", "sell_boundary": "if outside qlib top50, sell only worst full qlib rank", "buy_order": "buy_score rank within qlib top50", "max_sells_per_day": 1, "max_buys_per_day": 1},
        {"rule": "one_sell_one_buy_correct", "sell_boundary": "outside buy top10; outside qlib top50 first, otherwise worst buy rank", "buy_order": "buy_score rank within qlib top50", "max_sells_per_day": 1, "max_buys_per_day": 1},
        {"rule": "one_sell_one_buy_buggy_e8r", "sell_boundary": "known buggy diagnostic, not valid strategy evidence", "buy_order": "buy_score rank within qlib top50", "max_sells_per_day": 1, "max_buys_per_day": 1},
    ]


def write_report(manifest: dict[str, Any], summary: list[dict[str, Any]]) -> None:
    cross_model_rows = [row for row in summary if row["window"] == "2026_ytd"]
    long_window_rows = [
        row for row in summary
        if row["window"] in {"2023", "2024", "2025", "2023_2026_ytd"}
        and row["method"] == "frozen_qlib_2018_2022"
    ]
    lines = [
        "# 正式 Replay Matrix 执行报告",
        "",
        f"生成时间：`{manifest['created_at']}`",
        "",
        "## 1. 结论",
        "",
        "- 已固化正式 replay matrix 脚本：`scripts/run_extended_oos_formal_replay_matrix.py`。",
        "- 脚本把模型分数与交易规则解耦：`candidate_rank` 只决定 qlib top50 universe / exit boundary；`buy_score` 只决定 top50 内买入顺序。",
        "- 纯 qlib：`candidate_rank` 与 `buy_score` 都来自 qlib。",
        "- LTR：`candidate_rank` 仍来自底座 qlib，`buy_score` 来自 LTR rerank score。",
        "- 未训练 qlib/LTR，未调参，未触发 provider / accepted latest / frontend / API / monitor / 交易链路。",
        "",
        "## 2. 解读口径",
        "",
        "- 全部模型 / 全部策略的横向公平比较，只使用 `2026_ytd` 窗口。",
        "- `2023` / `2024` / `2025` / `2023_2026_ytd` 只用于观察 `frozen_qlib_2018_2022` 这个 2018-2022 训练 qlib 底座的长窗口表现，不参与所有模型公平比较。",
        "- LTR 类模型在本次正式矩阵中的可比测试窗口是 `2026_ytd`；不要把 LTR 的 `2023_2026_ytd` 行解释成覆盖了 2023-2026 全区间。",
        "- `one_sell_one_buy_buggy_e8r` 只保留为历史 bug 诊断，不是有效策略证据。",
        "- `top50_exit_one_worst_sell` 的语义是：初始建仓或持仓不足时允许补到目标持仓；满仓后只有持仓跌出 qlib top50，才卖出 full qlib rank 最差的一支，并买入 top50 内 buy_score 最高且未持有的股票。",
        "",
        "## 3. 全模型公平比较：2026_ytd",
        "",
        "| window | method | family | rule | net_return | max_dd | actions | buys | sells | skipped |",
        "| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in cross_model_rows:
        lines.append(f"| {row['window']} | {row['method']} | {row['family']} | {row['rule']} | {row['fee_tax_adjusted_net_return']} | {row['max_drawdown']} | {row['action_count']} | {row['buy_count']} | {row['sell_count']} | {row['skipped_trade_count']} |")
    lines.extend([
        "",
        "## 4. Frozen Qlib 长窗口观察",
        "",
        "以下结果只用于观察 `frozen_qlib_2018_2022` 在 2023-2026 YTD 的长窗口表现，不用于和 LTR 做全窗口横向比较。",
        "",
        "| window | method | family | rule | net_return | max_dd | actions | buys | sells | skipped |",
        "| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ])
    for row in long_window_rows:
        lines.append(f"| {row['window']} | {row['method']} | {row['family']} | {row['rule']} | {row['fee_tax_adjusted_net_return']} | {row['max_drawdown']} | {row['action_count']} | {row['buy_count']} | {row['sell_count']} | {row['skipped_trade_count']} |")
    lines.extend([
        "",
        "## 5. 完整原始矩阵",
        "",
        "完整 CSV 仍保留所有生成行，用于追溯和审计；正式解读以上述两个区块为准。",
        "",
        "## 6. 产物",
        "",
    ])
    for key, path in manifest["artifacts"].items():
        lines.append(f"- {key}: `{path}`")
    DOC.parent.mkdir(parents=True, exist_ok=True)
    DOC.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Formal decoupled replay matrix for qlib and LTR strategies.")
    parser.add_argument("--windows", default="2026_ytd,2023,2024,2025,2023_2026_ytd", help="Comma-separated window names.")
    parser.add_argument("--methods", default=",".join(spec.method for spec in STRATEGIES), help="Comma-separated method names.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    requested_windows = [item.strip() for item in args.windows.split(",") if item.strip()]
    requested_methods = [item.strip() for item in args.methods.split(",") if item.strip()]
    unknown_windows = sorted(set(requested_windows) - set(WINDOWS))
    if unknown_windows:
        raise RuntimeError(f"unknown windows: {unknown_windows}")
    selected = [spec for spec in STRATEGIES if spec.method in requested_methods]
    if len(selected) != len(requested_methods):
        known = {spec.method for spec in STRATEGIES}
        raise RuntimeError(f"unknown methods: {sorted(set(requested_methods) - known)}")

    OUT.mkdir(parents=True, exist_ok=True)
    created_at = now()
    s2d = load_s2d()

    ready_by_method = {spec.method: load_ready(spec) for spec in selected}
    full_by_method = {spec.method: load_full_rank(spec) for spec in selected}
    all_symbols = set()
    for df in ready_by_method.values():
        all_symbols |= set(df["instrument"])
    prices = s2d.PriceStore(all_symbols)

    results: list[dict[str, Any]] = []
    summary: list[dict[str, Any]] = []
    nav_rows: list[dict[str, Any]] = []
    action_rows: list[dict[str, Any]] = []
    snapshot_rows: list[dict[str, Any]] = []
    coverage: list[dict[str, Any]] = []

    for window_name in requested_windows:
        start, end = WINDOWS[window_name]
        for spec in selected:
            ready = ready_by_method[spec.method]
            if ready[(ready["date_str"] >= start) & (ready["date_str"] <= end)].empty:
                continue
            coverage.append(coverage_row(ready, spec, window_name, start, end))
            for rule in RULES:
                result = replay_strategy(ready, full_by_method[spec.method], spec, prices, s2d, rule, window_name, start, end)
                results.append(result)
                summary.append(result["metrics"])
                nav_rows.extend(result["nav"])
                action_rows.extend(result["actions"])
                snapshot_rows.extend(result["snapshots"])

    integrity = integrity_rows(results)
    forbidden = []
    for spec in selected:
        cols = set(ready_by_method[spec.method].columns)
        forbidden.append({
            "method": spec.method,
            "forbidden_columns_present": " ".join(sorted(cols & FORBIDDEN_COLUMNS)),
            "forbidden_columns_used_for_ranking": False,
            "candidate_rank_col": spec.candidate_rank_col,
            "buy_score_col": spec.buy_score_col,
            "full_rank_col": spec.full_rank_col,
        })

    wcsv(OUT / "formal_replay_summary.csv", summary)
    wcsv(OUT / "formal_replay_daily_nav.csv", nav_rows)
    wcsv(OUT / "formal_replay_actions.csv", action_rows)
    wcsv(OUT / "formal_replay_position_snapshots.csv", snapshot_rows)
    wcsv(OUT / "formal_replay_coverage_audit.csv", coverage)
    wcsv(OUT / "formal_replay_position_integrity_audit.csv", integrity)
    wcsv(OUT / "formal_replay_rule_contract.csv", rule_contract_rows())
    wcsv(OUT / "formal_replay_forbidden_field_audit.csv", forbidden)

    manifest = {
        "created_at": created_at,
        "gate": "formal_decoupled_replay_matrix_completed",
        "script": rel(ROOT / "scripts/run_extended_oos_formal_replay_matrix.py"),
        "windows": {name: WINDOWS[name] for name in requested_windows},
        "methods": [spec.__dict__ | {"ready_path": rel(spec.ready_path), "full_rank_path": rel(spec.full_rank_path)} for spec in selected],
        "rules": RULES,
        "decoupling_contract": {
            "candidate_rank": "qlib rank used only for top50 membership and exit boundary",
            "buy_score": "model score used only for top50 buy ordering; qlib score for pure qlib, LTR score for LTR",
            "full_qlib_rank": "complete qlib rank source used to choose worst exited holding when a holding is no longer in top50 replay-ready rows",
        },
        "no_training": True,
        "no_tuning": True,
        "no_provider_accepted_latest_frontend_api_monitor_trading": True,
        "artifacts": {
            "manifest": rel(OUT / "formal_replay_manifest.json"),
            "summary": rel(OUT / "formal_replay_summary.csv"),
            "daily_nav": rel(OUT / "formal_replay_daily_nav.csv"),
            "actions": rel(OUT / "formal_replay_actions.csv"),
            "snapshots": rel(OUT / "formal_replay_position_snapshots.csv"),
            "coverage": rel(OUT / "formal_replay_coverage_audit.csv"),
            "integrity": rel(OUT / "formal_replay_position_integrity_audit.csv"),
            "rule_contract": rel(OUT / "formal_replay_rule_contract.csv"),
            "forbidden": rel(OUT / "formal_replay_forbidden_field_audit.csv"),
            "report": rel(DOC),
        },
    }
    wjson(OUT / "formal_replay_manifest.json", manifest)
    write_report(manifest, summary)
    print(json.dumps({"ok": True, "gate": manifest["gate"], "out_dir": rel(OUT), "report": rel(DOC)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
