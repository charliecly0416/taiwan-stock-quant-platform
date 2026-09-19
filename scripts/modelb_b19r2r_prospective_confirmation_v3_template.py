#!/usr/bin/env python3
"""Prospective V3 replay-core template with frozen affordability skip semantics."""
from __future__ import annotations

import argparse
import json
import math
from typing import Any

import numpy as np
import pandas as pd


INITIAL = 1_000_000.0
FEE = 0.001425
TAX = 0.003
LOT = 10
TARGET = 10
KEY = ["date", "instrument"]
SKIP_STATUS = "SKIPPED_ZERO_OR_INSUFFICIENT_CASH"
ACTION_COLUMNS = [
    "signal_date", "instrument", "action", "reason", "scope", "method",
    "execution_date", "execution_price", "quantity", "commission", "sell_tax",
    "net_pnl", "status",
]
CONTRIBUTION_COLUMNS = [
    "scope", "method", "instrument", "action_net_pnl",
    "terminal_unrealized_pnl", "total_contribution",
]


def resolve_buy_affordability(
    allocation: float,
    cash: float,
    price: float,
) -> tuple[int, float, float, bool]:
    quantity = int(allocation // (price * (1 + FEE) * LOT)) * LOT
    commission = quantity * price * FEE
    total_cash = quantity * price + commission
    if quantity <= 0 or total_cash > cash:
        return 0, 0.0, 0.0, False
    return quantity, commission, total_cash, True


def replay(
    signals: pd.DataFrame,
    grid: pd.DataFrame,
    full_ranks: pd.DataFrame,
    score_field: str,
    method: str,
    scope: str,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Replay one prospective window without reading any artifact from disk."""
    signal_days = sorted(signals.date.unique().tolist())
    if not signal_days:
        raise RuntimeError("prospective replay requires at least one signal day")
    grid_lookup = grid.set_index(KEY)
    holdings: dict[str, int] = {}
    basis: dict[str, float] = {}
    cash = INITIAL
    pending: list[dict[str, Any]] = []
    actions: list[dict[str, Any]] = []
    nav: list[dict[str, Any]] = []
    price_audit: list[dict[str, Any]] = []
    full_rank_lookup = full_ranks.set_index(KEY).full_qlib_rank

    def execute_and_mark(signal_day: str) -> None:
        nonlocal cash, pending
        decision_count = len(pending)
        executed_count = 0
        skip_count = 0
        day_grid = grid[grid.date.eq(signal_day)]
        execution_dates = set(day_grid.next_trade_date.astype(str).str[:10])
        if len(day_grid) != 150 or len(execution_dates) != 1:
            raise RuntimeError("execution grid does not define one complete next trade date")
        execution_date = next(iter(execution_dates))
        for order in pending:
            row = grid_lookup.loc[(signal_day, order["instrument"])]
            if str(row.next_trade_date)[:10] != execution_date:
                raise RuntimeError("action execution date does not match the frozen daily grid")
            price = float(row.next_open)
            if not math.isfinite(price) or price <= 0:
                raise RuntimeError("missing next_open; no fallback")
            symbol = order["instrument"]
            price_audit.append({
                "scope": scope,
                "method": method,
                "signal_date": signal_day,
                "instrument": symbol,
                "action": order["action"],
                "execution_date": execution_date,
                "next_open": price,
                "fallback_used": False,
            })
            if order["action"] == "sell":
                quantity = holdings.pop(symbol)
                old_basis = basis.pop(symbol)
                commission = quantity * price * FEE
                tax = quantity * price * TAX
                cash += quantity * price - commission - tax
                net_pnl = quantity * price - old_basis - commission - tax
            else:
                allocation = cash / max(1, TARGET - len(holdings))
                quantity, commission, total_cash, affordable = resolve_buy_affordability(
                    allocation,
                    cash,
                    price,
                )
                if not affordable:
                    actions.append({
                        **order,
                        "scope": scope,
                        "method": method,
                        "execution_date": execution_date,
                        "execution_price": price,
                        "quantity": 0,
                        "commission": 0.0,
                        "sell_tax": 0.0,
                        "net_pnl": 0.0,
                        "status": SKIP_STATUS,
                    })
                    skip_count += 1
                    continue
                tax = 0.0
                cash -= total_cash
                holdings[symbol] = quantity
                basis[symbol] = quantity * price
                net_pnl = -commission
            executed_count += 1
            actions.append({
                **order,
                "scope": scope,
                "method": method,
                "execution_date": execution_date,
                "execution_price": price,
                "quantity": quantity,
                "commission": commission,
                "sell_tax": tax,
                "net_pnl": net_pnl,
                "status": "EXECUTED",
            })
        market_value = 0.0
        for symbol, quantity in holdings.items():
            row = grid_lookup.loc[(signal_day, symbol)]
            close = float(row.next_close)
            if not math.isfinite(close) or close <= 0 or str(row.next_trade_date)[:10] != execution_date:
                raise RuntimeError("missing exact next_close terminal mark")
            market_value += quantity * close
        nav.append({
            "scope": scope,
            "method": method,
            "signal_date": signal_day,
            "date": execution_date,
            "cash": cash,
            "market_value": market_value,
            "equity": cash + market_value,
            "holding_count": len(holdings),
            "decision_count": decision_count,
            "emitted_action_count": executed_count,
            "executed_action_count": executed_count,
            "skip_count": skip_count,
            "pending_count": 0,
            "fallback_count": 0,
        })
        pending = []

    for index, day in enumerate(signal_days):
        if index:
            execute_and_mark(signal_days[index - 1])
        group = signals[signals.date.eq(day)].copy()
        candidates = set(group.instrument)
        outside = [symbol for symbol in holdings if symbol not in candidates]
        if outside:
            ranks: dict[str, float] = {}
            for symbol in outside:
                try:
                    ranks[symbol] = float(full_rank_lookup.loc[(day, symbol)])
                except KeyError as error:
                    raise RuntimeError(f"missing frozen full rank: {day} {symbol}") from error
            worst = max(outside, key=lambda symbol: (ranks[symbol], symbol))
            pending.append({
                "signal_date": day,
                "instrument": worst,
                "action": "sell",
                "reason": "top50_exit_one_worst_sell",
            })
        projected = len(holdings) - sum(order["action"] == "sell" for order in pending)
        if projected < TARGET:
            ranked = group.sort_values(
                [score_field, "instrument"],
                ascending=[False, True],
                kind="mergesort",
            )
            for row in ranked.itertuples(index=False):
                if row.instrument not in holdings:
                    pending.append({
                        "signal_date": day,
                        "instrument": row.instrument,
                        "action": "buy",
                        "reason": "top50_buy_score_rank",
                    })
                    break
        if sum(order["action"] == "buy" for order in pending) > 1 or sum(
            order["action"] == "sell" for order in pending
        ) > 1:
            raise RuntimeError("daily action limit exceeded")
    execute_and_mark(signal_days[-1])
    if len(nav) != len(signal_days):
        raise RuntimeError("daily ledger is incomplete")

    action_frame = pd.DataFrame(actions, columns=ACTION_COLUMNS)
    nav_frame = pd.DataFrame(nav)
    nav_frame["daily_return"] = nav_frame.equity.pct_change().fillna(
        nav_frame.equity.iloc[0] / INITIAL - 1
    )
    equity_values = nav_frame.equity.to_numpy(float)
    peaks = np.maximum.accumulate(np.r_[INITIAL, equity_values])[1:]
    nav_frame["drawdown"] = equity_values / peaks - 1.0
    contribution: list[dict[str, Any]] = []
    instruments = set(action_frame.instrument).union(holdings)
    for symbol in sorted(instruments):
        action_pnl = float(action_frame.loc[action_frame.instrument.eq(symbol), "net_pnl"].sum())
        unrealized = 0.0
        if symbol in holdings:
            terminal_close = float(grid_lookup.loc[(signal_days[-1], symbol)].next_close)
            unrealized = holdings[symbol] * terminal_close - basis[symbol]
        contribution.append({
            "scope": scope,
            "method": method,
            "instrument": symbol,
            "action_net_pnl": action_pnl,
            "terminal_unrealized_pnl": unrealized,
            "total_contribution": action_pnl + unrealized,
        })
    contribution_frame = pd.DataFrame(contribution, columns=CONTRIBUTION_COLUMNS)
    if not math.isclose(
        float(contribution_frame.total_contribution.sum()),
        float(nav_frame.equity.iloc[-1] - INITIAL),
        abs_tol=1e-6,
    ):
        raise RuntimeError("PnL contribution does not reconcile")
    return action_frame, nav_frame, pd.DataFrame(price_audit), contribution_frame


def summarize(
    scope: str,
    method: str,
    actions: pd.DataFrame,
    nav: pd.DataFrame,
    contribution: pd.DataFrame,
) -> dict[str, Any]:
    executed = actions[actions.status.eq("EXECUTED")]
    skipped = actions[actions.status.eq(SKIP_STATUS)]
    positive = actions[actions.quantity.gt(0)]
    buys = executed[executed.action.eq("buy")]
    sells = executed[executed.action.eq("sell")]
    notionals = (executed.quantity * executed.execution_price).sum()
    abs_contribution = contribution.total_contribution.abs()
    contribution_denominator = float(abs_contribution.sum())
    shares = (
        abs_contribution / contribution_denominator
        if contribution_denominator > 0
        else pd.Series(dtype=float)
    )
    skip_integrity_violations = int((
        skipped.quantity.ne(0)
        | skipped.commission.ne(0.0)
        | skipped.sell_tax.ne(0.0)
        | skipped.net_pnl.ne(0.0)
    ).sum())
    all_positive_executed = bool(
        positive.status.eq("EXECUTED").all()
        and len(positive) == int(nav.emitted_action_count.sum())
        and len(executed) == int(nav.executed_action_count.sum())
    )
    return {
        "scope": scope,
        "method": method,
        "final_equity": float(nav.equity.iloc[-1]),
        "net_return": float(nav.equity.iloc[-1] / INITIAL - 1),
        "max_drawdown": float(nav.drawdown.min()),
        "turnover": float(notionals / INITIAL),
        "buy_count": int(len(buys)),
        "sell_count": int(len(sells)),
        "action_count": int(len(executed)),
        "skip_count": int(len(skipped)),
        "decision_count": int(nav.decision_count.sum()),
        "commission": float(executed.commission.sum()),
        "sell_tax": float(executed.sell_tax.sum()),
        "fee_tax": float(executed.commission.sum() + executed.sell_tax.sum()),
        "contribution_denominator": contribution_denominator,
        "contribution_denominator_valid": bool(
            math.isfinite(contribution_denominator) and contribution_denominator > 0
        ),
        "top1_abs_contribution_share": float(shares.nlargest(1).sum()) if len(shares) else None,
        "top5_abs_contribution_share": float(shares.nlargest(5).sum()) if len(shares) else None,
        "abs_contribution_hhi": float((shares**2).sum()) if len(shares) else None,
        "fallback_count": int(nav.fallback_count.sum()),
        "pending_count": int(nav.pending_count.sum()),
        "emitted_action_count": int(nav.emitted_action_count.sum()),
        "executed_action_count": int(nav.executed_action_count.sum()),
        "all_emitted_positive_quantity_actions_must_execute": all_positive_executed,
        "skip_audit_integrity_violation_count": skip_integrity_violations,
        "reconciliation_delta": float(
            contribution.total_contribution.sum() - (nav.equity.iloc[-1] - INITIAL)
        ),
    }


def synthetic_high_price_fixture() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    signal_date = "2099-01-05"
    next_date = "2099-01-06"
    universe = [f"TW{i:04d}" for i in range(1, 151)]
    signals = pd.DataFrame({
        "date": [signal_date] * 50,
        "instrument": universe[:50],
        "buy_score": np.arange(50, 0, -1, dtype=float),
    })
    grid = pd.DataFrame({
        "date": [signal_date] * 150,
        "instrument": universe,
        "next_trade_date": [next_date] * 150,
        "next_open": [20_000.0] * 150,
        "next_close": [20_000.0] * 150,
    })
    full_ranks = pd.DataFrame(columns=["date", "instrument", "full_qlib_rank"])
    return signals, grid, full_ranks


def run_synthetic_affordability_check() -> dict[str, Any]:
    signals, grid, full_ranks = synthetic_high_price_fixture()
    actions, nav, price_audit, contribution = replay(
        signals,
        grid,
        full_ranks,
        "buy_score",
        "SYNTHETIC",
        "prospective_v3_synthetic_only",
    )
    summary = summarize(
        "prospective_v3_synthetic_only",
        "SYNTHETIC",
        actions,
        nav,
        contribution,
    )
    insufficient = resolve_buy_affordability(100_000.0, 99_000.0, 100.0)
    checks = {
        "one_skip_row": bool(len(actions) == 1 and actions.status.eq(SKIP_STATUS).all()),
        "zero_quantity_and_costs": bool(
            actions.quantity.eq(0).all()
            and actions.commission.eq(0.0).all()
            and actions.sell_tax.eq(0.0).all()
            and actions.net_pnl.eq(0.0).all()
        ),
        "not_added_to_holdings": int(nav.holding_count.iloc[-1]) == 0,
        "price_audit_retained": len(price_audit) == 1 and not bool(price_audit.fallback_used.any()),
        "executed_count_not_increased": int(nav.executed_action_count.sum()) == 0,
        "emitted_positive_count_not_increased": int(nav.emitted_action_count.sum()) == 0,
        "skip_count_increased": int(nav.skip_count.sum()) == 1 and summary["skip_count"] == 1,
        "pending_and_fallback_zero": summary["pending_count"] == 0 and summary["fallback_count"] == 0,
        "positive_action_gate_passes_vacuously": summary[
            "all_emitted_positive_quantity_actions_must_execute"
        ],
        "skip_integrity_gate_passes": summary["skip_audit_integrity_violation_count"] == 0,
        "cash_and_equity_unchanged": bool(
            math.isclose(float(nav.cash.iloc[-1]), INITIAL)
            and math.isclose(float(nav.equity.iloc[-1]), INITIAL)
        ),
        "reconciliation_exact": math.isclose(summary["reconciliation_delta"], 0.0, abs_tol=1e-12),
        "insufficient_cash_guard_returns_zero": insufficient == (0, 0.0, 0.0, False),
    }
    return {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "template_only": True,
        "real_artifact_io_supported": False,
        "checks": checks,
        "summary": summary,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--synthetic-affordability-check", action="store_true")
    args = parser.parse_args()
    if not args.synthetic_affordability_check:
        raise SystemExit("Template-only: select --synthetic-affordability-check")
    result = run_synthetic_affordability_check()
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
