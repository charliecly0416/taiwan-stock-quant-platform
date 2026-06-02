#!/usr/bin/env python3
"""Simulate a TWStock cross-sectional portfolio from daily bars.

This is a Phase 3 research simulator. It uses close-to-close returns and
rebalances at the close of scheduled trading dates. It can run either a simple
weight model or an approximate Taiwan whole-lot model for 1000-share orders.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.setdefault("SECRET_KEY", "simulate-tw-stock-portfolio")
os.environ.setdefault("ADMIN_USER", "simulate")
os.environ.setdefault("ADMIN_PASSWORD", "simulatepass")

from scripts.archive_tw_stock_daily import DailyBarRecord, fetch_finmind_rows, parse_finmind_rows  # noqa: E402
from scripts.plan_tw_stock_rebalance import build_rebalance_plan, parse_ranked_items  # noqa: E402
from scripts.rank_tw_stock_universe import compute_raw_metrics, parse_config_symbols, _percentile_scores  # noqa: E402


@dataclass(frozen=True)
class EquityPoint:
    date: str
    equity: float
    daily_return: float
    cost: float
    turnover: float


@dataclass(frozen=True)
class RebalanceEvent:
    date: str
    selected: List[str]
    turnover: float
    cost: float
    weights: Dict[str, float]
    shares: Dict[str, int]
    cash_weight: float
    buy_value: float
    sell_value: float
    buy_commission: float
    sell_commission: float
    sell_tax: float
    blocked_buys: List[str]
    blocked_sells: List[str]


@dataclass(frozen=True)
class LotRebalanceResult:
    weights: Dict[str, float]
    shares: Dict[str, int]
    cash_weight: float
    turnover: float
    cost_weight: float
    buy_value: float
    sell_value: float
    buy_commission: float
    sell_commission: float
    sell_tax: float
    blocked_buys: List[str]
    blocked_sells: List[str]


def load_symbols(path: str, raw_symbols: Sequence[str]) -> List[str]:
    symbols = parse_config_symbols(raw_symbols)
    if path:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        for symbol in parse_ranked_items(payload):
            plain = str(symbol.get("symbol") or "")
            if plain and plain not in symbols:
                symbols.append(plain)
        for symbol in parse_config_symbols(payload.get("symbol_list") or payload.get("symbols") or payload.get("rankings") or []):
            if symbol not in symbols:
                symbols.append(symbol)
    return symbols


def fetch_symbol_records(symbol: str, start: str, end: str) -> List[DailyBarRecord]:
    return parse_finmind_rows(fetch_finmind_rows(symbol, start, end), symbol=symbol)


def _parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def _filter_records(records: Sequence[DailyBarRecord], start: str, end: str) -> List[DailyBarRecord]:
    return [
        item for item in records
        if not item.quality_flags and start <= item.trade_date <= end and float(item.close or 0) > 0
    ]


def _close_map(records_by_symbol: Dict[str, Sequence[DailyBarRecord]]) -> Dict[str, Dict[str, float]]:
    out: Dict[str, Dict[str, float]] = {}
    for symbol, records in records_by_symbol.items():
        out[symbol] = {item.trade_date: float(item.close) for item in records if not item.quality_flags and item.close > 0}
    return out


def _trading_dates(records_by_symbol: Dict[str, Sequence[DailyBarRecord]], start: str, end: str) -> List[str]:
    dates = {
        item.trade_date
        for records in records_by_symbol.values()
        for item in records
        if not item.quality_flags and start <= item.trade_date <= end and item.close > 0
    }
    return sorted(dates)


def _is_rebalance_date(current: str, previous: Optional[str], frequency: str) -> bool:
    if previous is None:
        return True
    cur = _parse_date(current)
    prev = _parse_date(previous)
    if frequency == "daily":
        return True
    if frequency == "weekly":
        return cur.isocalendar()[:2] != prev.isocalendar()[:2]
    if frequency == "monthly":
        return (cur.year, cur.month) != (prev.year, prev.month)
    raise ValueError(f"unsupported rebalance frequency: {frequency}")


def rank_records_for_date(
    records_by_symbol: Dict[str, Sequence[DailyBarRecord]],
    *,
    as_of: str,
    lookback_days: int,
    momentum_window: int,
    volatility_window: int,
    min_bars: int,
    weights: Dict[str, float],
) -> Dict[str, Any]:
    start = (_parse_date(as_of) - timedelta(days=max(lookback_days, 1))).isoformat()
    raw: Dict[str, Dict[str, Any]] = {}
    for symbol, records in records_by_symbol.items():
        metrics = compute_raw_metrics(
            _filter_records(records, start, as_of),
            momentum_window=momentum_window,
            volatility_window=volatility_window,
        )
        if int(metrics.get("bars") or 0) < min_bars:
            metrics.setdefault("reasons", []).append("below_min_bars")
        raw[symbol] = metrics

    eligible = {
        symbol: metrics for symbol, metrics in raw.items()
        if not metrics.get("reasons") and metrics.get("momentum") is not None and metrics.get("volatility") is not None
    }
    momentum_scores = _percentile_scores({s: float(m["momentum"]) for s, m in eligible.items()}, reverse=True)
    low_vol_scores = _percentile_scores({s: float(m["volatility"]) for s, m in eligible.items()})
    liquidity_scores = _percentile_scores({s: float(m["avg_trading_money"]) for s, m in eligible.items()}, reverse=True)

    items = []
    for symbol, metrics in raw.items():
        composite = round(
            momentum_scores.get(symbol, 0.0) * weights.get("momentum", 0.0)
            + low_vol_scores.get(symbol, 0.0) * weights.get("low_volatility", 0.0)
            + liquidity_scores.get(symbol, 0.0) * weights.get("liquidity", 0.0),
            8,
        )
        items.append({
            "symbol": symbol,
            "config_symbol": f"TWStock:{symbol}",
            "rank": 0,
            "composite_score": composite,
            "momentum": metrics.get("momentum"),
            "volatility": metrics.get("volatility"),
            "avg_trading_money": metrics.get("avg_trading_money", 0.0),
            "bars": metrics.get("bars", 0),
            "reasons": list(metrics.get("reasons") or []),
        })
    items.sort(key=lambda item: (item["composite_score"], item["avg_trading_money"]), reverse=True)
    for idx, item in enumerate(items, start=1):
        item["rank"] = idx
    return {
        "as_of": as_of,
        "eligible_count": len(eligible),
        "rankings": [item["config_symbol"] for item in items if not item["reasons"]],
        "items": items,
    }


def _turnover(old_weights: Dict[str, float], new_weights: Dict[str, float]) -> float:
    symbols = set(old_weights) | set(new_weights)
    return round(sum(abs(float(new_weights.get(symbol, 0.0)) - float(old_weights.get(symbol, 0.0))) for symbol in symbols), 8)


def _portfolio_return(weights: Dict[str, float], closes: Dict[str, Dict[str, float]], current: str, next_date: str) -> float:
    total = 0.0
    for symbol, weight in weights.items():
        prev_close = closes.get(symbol, {}).get(current)
        next_close = closes.get(symbol, {}).get(next_date)
        if prev_close and next_close:
            total += weight * (next_close / prev_close - 1.0)
    return total


def _price_limit_flags(
    *,
    symbols: Sequence[str],
    closes: Dict[str, Dict[str, float]],
    previous_date: Optional[str],
    current_date: str,
    limit_pct: float,
) -> Dict[str, str]:
    if not previous_date or limit_pct <= 0:
        return {}
    flags: Dict[str, str] = {}
    for symbol in symbols:
        prev_close = float(closes.get(symbol, {}).get(previous_date) or 0.0)
        current_close = float(closes.get(symbol, {}).get(current_date) or 0.0)
        if prev_close <= 0 or current_close <= 0:
            continue
        if current_close >= prev_close * (1.0 + limit_pct) - 1e-9:
            flags[symbol] = "limit_up"
        elif current_close <= prev_close * (1.0 - limit_pct) + 1e-9:
            flags[symbol] = "limit_down"
    return flags


def _apply_price_limit_to_weights(
    *,
    current_weights: Dict[str, float],
    target_weights: Dict[str, float],
    limit_flags: Dict[str, str],
) -> tuple[Dict[str, float], List[str], List[str]]:
    adjusted = dict(target_weights)
    blocked_buys: List[str] = []
    blocked_sells: List[str] = []
    for symbol in sorted(set(current_weights) | set(target_weights)):
        old_weight = float(current_weights.get(symbol, 0.0))
        new_weight = float(target_weights.get(symbol, 0.0))
        flag = limit_flags.get(symbol)
        if flag == "limit_up" and new_weight > old_weight:
            adjusted[symbol] = old_weight
            blocked_buys.append(symbol)
        elif flag == "limit_down" and new_weight < old_weight:
            adjusted[symbol] = old_weight
            blocked_sells.append(symbol)
    return {key: value for key, value in adjusted.items() if value > 0}, blocked_buys, blocked_sells


def _rebalance_whole_lots(
    *,
    current_shares: Dict[str, int],
    target_weights: Dict[str, float],
    prices: Dict[str, float],
    equity_value: float,
    lot_size: int,
    commission_rate: float,
    sell_tax_rate: float,
    limit_flags: Optional[Dict[str, str]] = None,
) -> LotRebalanceResult:
    lot = max(int(lot_size or 1), 1)
    equity = max(float(equity_value or 0.0), 0.0)
    limit_flags = limit_flags or {}
    blocked_buys: List[str] = []
    blocked_sells: List[str] = []
    target_shares: Dict[str, int] = {}
    for symbol, target_weight in target_weights.items():
        price = float(prices.get(symbol) or 0.0)
        if price <= 0 or equity <= 0:
            continue
        raw_shares = equity * max(float(target_weight or 0.0), 0.0) / price
        lots = int(raw_shares // lot)
        if lots > 0:
            target_shares[symbol] = lots * lot

    for symbol in sorted(set(current_shares) | set(target_shares)):
        old_qty = int(current_shares.get(symbol, 0) or 0)
        new_qty = int(target_shares.get(symbol, 0) or 0)
        flag = limit_flags.get(symbol)
        if flag == "limit_up" and new_qty > old_qty:
            if old_qty > 0:
                target_shares[symbol] = old_qty
            else:
                target_shares.pop(symbol, None)
            blocked_buys.append(symbol)
        elif flag == "limit_down" and new_qty < old_qty:
            target_shares[symbol] = old_qty
            blocked_sells.append(symbol)

    symbols = set(current_shares) | set(target_shares)
    buy_value = 0.0
    sell_value = 0.0
    traded_value = 0.0
    for symbol in symbols:
        price = float(prices.get(symbol) or 0.0)
        if price <= 0:
            continue
        old_qty = int(current_shares.get(symbol, 0) or 0)
        new_qty = int(target_shares.get(symbol, 0) or 0)
        delta = new_qty - old_qty
        traded_value += abs(delta) * price
        if delta > 0:
            buy_value += delta * price
        elif delta < 0:
            sell_value += abs(delta) * price

    buy_commission = buy_value * max(float(commission_rate or 0.0), 0.0)
    sell_commission = sell_value * max(float(commission_rate or 0.0), 0.0)
    sell_tax = sell_value * max(float(sell_tax_rate or 0.0), 0.0)
    cost_value = buy_commission + sell_commission + sell_tax
    weights = {
        symbol: round(qty * float(prices.get(symbol) or 0.0) / equity, 8)
        for symbol, qty in target_shares.items()
        if equity > 0 and float(prices.get(symbol) or 0.0) > 0
    }
    cash_weight = round(max(1.0 - sum(weights.values()) - (cost_value / equity if equity > 0 else 0.0), 0.0), 8)
    return LotRebalanceResult(
        weights=weights,
        shares={key: target_shares[key] for key in sorted(target_shares)},
        cash_weight=cash_weight,
        turnover=round(traded_value / equity, 8) if equity > 0 else 0.0,
        cost_weight=round(cost_value / equity, 8) if equity > 0 else 0.0,
        buy_value=round(buy_value, 2),
        sell_value=round(sell_value, 2),
        buy_commission=round(buy_commission, 2),
        sell_commission=round(sell_commission, 2),
        sell_tax=round(sell_tax, 2),
        blocked_buys=blocked_buys,
        blocked_sells=blocked_sells,
    )


def _max_drawdown(equity: Sequence[float]) -> float:
    peak = 0.0
    max_dd = 0.0
    for value in equity:
        peak = max(peak, value)
        if peak > 0:
            max_dd = min(max_dd, value / peak - 1.0)
    return round(max_dd, 8)


def _std(values: Sequence[float]) -> float:
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    return math.sqrt(sum((value - mean) ** 2 for value in values) / (len(values) - 1))


def simulate_portfolio(
    *,
    symbols: Sequence[str],
    start: str,
    end: str,
    rebalance_frequency: str = "monthly",
    lookback_days: int = 90,
    momentum_window: int = 20,
    volatility_window: int = 20,
    min_bars: int = 30,
    top_n: int = 5,
    cash_weight: float = 0.0,
    max_weight: float = 0.25,
    transaction_cost: float = 0.003925,
    enforce_lot_size: bool = False,
    initial_capital: float = 1_000_000.0,
    lot_size: int = 1000,
    commission_rate: float = 0.001425,
    sell_tax_rate: float = 0.003,
    enforce_price_limit: bool = False,
    price_limit_pct: float = 0.10,
    factor_weights: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    clean_symbols = parse_config_symbols(symbols)
    fetch_start = (_parse_date(start) - timedelta(days=max(lookback_days, 1) + 10)).isoformat()
    records_by_symbol = {symbol: fetch_symbol_records(symbol, fetch_start, end) for symbol in clean_symbols}
    dates = _trading_dates(records_by_symbol, start, end)
    if len(dates) < 2:
        return {"start": start, "end": end, "symbols": clean_symbols, "error": "insufficient_trading_dates", "equity_curve": []}

    factor_weights = factor_weights or {"momentum": 0.5, "low_volatility": 0.3, "liquidity": 0.2}
    closes = _close_map(records_by_symbol)
    current_weights: Dict[str, float] = {}
    current_shares: Dict[str, int] = {}
    equity = 1.0
    equity_curve = [EquityPoint(date=dates[0], equity=equity, daily_return=0.0, cost=0.0, turnover=0.0)]
    events: List[RebalanceEvent] = []

    for idx, current in enumerate(dates[:-1]):
        previous = dates[idx - 1] if idx > 0 else None
        cost = 0.0
        turnover = 0.0
        if _is_rebalance_date(current, previous, rebalance_frequency) or (not current_weights and not events):
            ranking = rank_records_for_date(
                records_by_symbol,
                as_of=current,
                lookback_days=lookback_days,
                momentum_window=momentum_window,
                volatility_window=volatility_window,
                min_bars=min_bars,
                weights=factor_weights,
            )
            plan = build_rebalance_plan(
                parse_ranked_items(ranking),
                top_n=top_n,
                cash_weight=cash_weight,
                max_weight=max_weight,
                as_of=current,
            )
            new_weights = {item["symbol"]: float(item["target_weight"]) for item in plan.get("target_positions", [])}
            if not new_weights and not current_weights:
                next_date = dates[idx + 1]
                equity_curve.append(EquityPoint(
                    date=next_date,
                    equity=round(equity, 8),
                    daily_return=0.0,
                    cost=0.0,
                    turnover=0.0,
                ))
                continue
            shares: Dict[str, int] = {}
            event_cash_weight = round(max(1.0 - sum(new_weights.values()), 0.0), 8)
            buy_value = sell_value = buy_commission = sell_commission = sell_tax = 0.0
            limit_flags = _price_limit_flags(
                symbols=list(set(current_weights) | set(new_weights)),
                closes=closes,
                previous_date=previous,
                current_date=current,
                limit_pct=float(price_limit_pct or 0.0),
            ) if enforce_price_limit else {}
            blocked_buys: List[str] = []
            blocked_sells: List[str] = []
            if enforce_lot_size:
                price_map = {symbol: closes.get(symbol, {}).get(current, 0.0) for symbol in set(current_weights) | set(new_weights)}
                lot_result = _rebalance_whole_lots(
                    current_shares=current_shares,
                    target_weights=new_weights,
                    prices=price_map,
                    equity_value=equity * max(float(initial_capital or 0.0), 0.0),
                    lot_size=lot_size,
                    commission_rate=commission_rate,
                    sell_tax_rate=sell_tax_rate,
                    limit_flags=limit_flags,
                )
                new_weights = lot_result.weights
                shares = lot_result.shares
                current_shares = shares
                turnover = lot_result.turnover
                cost = lot_result.cost_weight
                event_cash_weight = lot_result.cash_weight
                buy_value = lot_result.buy_value
                sell_value = lot_result.sell_value
                buy_commission = lot_result.buy_commission
                sell_commission = lot_result.sell_commission
                sell_tax = lot_result.sell_tax
                blocked_buys = lot_result.blocked_buys
                blocked_sells = lot_result.blocked_sells
            else:
                if limit_flags:
                    new_weights, blocked_buys, blocked_sells = _apply_price_limit_to_weights(
                        current_weights=current_weights,
                        target_weights=new_weights,
                        limit_flags=limit_flags,
                    )
                    event_cash_weight = round(max(1.0 - sum(new_weights.values()), 0.0), 8)
                turnover = _turnover(current_weights, new_weights)
                cost = round(turnover * max(float(transaction_cost or 0.0), 0.0), 8)
            equity *= max(1.0 - cost, 0.0)
            current_weights = new_weights
            events.append(RebalanceEvent(
                date=current,
                selected=list(new_weights),
                turnover=turnover,
                cost=cost,
                weights={key: round(value, 8) for key, value in sorted(new_weights.items())},
                shares=shares,
                cash_weight=event_cash_weight,
                buy_value=buy_value,
                sell_value=sell_value,
                buy_commission=buy_commission,
                sell_commission=sell_commission,
                sell_tax=sell_tax,
                blocked_buys=blocked_buys,
                blocked_sells=blocked_sells,
            ))

        next_date = dates[idx + 1]
        daily_return = _portfolio_return(current_weights, closes, current, next_date)
        equity *= 1.0 + daily_return
        equity_curve.append(EquityPoint(
            date=next_date,
            equity=round(equity, 8),
            daily_return=round(daily_return, 8),
            cost=cost,
            turnover=turnover,
        ))

    daily_returns = [point.daily_return for point in equity_curve[1:]]
    total_return = equity_curve[-1].equity - 1.0
    annualized_return = (equity_curve[-1].equity ** (252 / max(len(daily_returns), 1)) - 1.0) if equity_curve[-1].equity > 0 else -1.0
    return {
        "start": start,
        "end": end,
        "symbols": clean_symbols,
        "rebalance_frequency": rebalance_frequency,
        "assumptions": {
            "market": "TWStock",
            "currency": "TWD",
            "return_model": "close_to_close",
            "rebalance_timing": "close",
            "long_only": True,
            "lot_size_enforced": bool(enforce_lot_size),
            "lot_size": int(lot_size),
            "initial_capital": float(initial_capital),
            "transaction_cost": transaction_cost,
            "commission_rate": commission_rate,
            "sell_tax_rate": sell_tax_rate,
            "price_limit_enforced": bool(enforce_price_limit),
            "price_limit_pct": float(price_limit_pct),
        },
        "metrics": {
            "total_return": round(total_return, 8),
            "annualized_return": round(annualized_return, 8),
            "annualized_volatility": round(_std(daily_returns) * math.sqrt(252), 8),
            "max_drawdown": _max_drawdown([point.equity for point in equity_curve]),
            "rebalance_count": len(events),
            "average_turnover": round(sum(event.turnover for event in events) / len(events), 8) if events else 0.0,
            "final_equity": equity_curve[-1].equity,
        },
        "rebalance_events": [asdict(item) for item in events],
        "equity_curve": [asdict(item) for item in equity_curve],
    }


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Simulate a TWStock cross-sectional portfolio.")
    parser.add_argument("--symbol", action="append", default=[], help="TWStock:2330/2330 list. Can be repeated or comma-separated.")
    parser.add_argument("--universe-json", default="", help="JSON with symbol_list/rankings/items.")
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    parser.add_argument("--rebalance-frequency", default="monthly", choices=("daily", "weekly", "monthly"))
    parser.add_argument("--lookback-days", type=int, default=90)
    parser.add_argument("--momentum-window", type=int, default=20)
    parser.add_argument("--volatility-window", type=int, default=20)
    parser.add_argument("--min-bars", type=int, default=30)
    parser.add_argument("--top-n", type=int, default=5)
    parser.add_argument("--cash-weight", type=float, default=0.0)
    parser.add_argument("--max-weight", type=float, default=0.25)
    parser.add_argument("--transaction-cost", type=float, default=0.003925)
    parser.add_argument("--enforce-lot-size", action="store_true", help="Approximate TWStock whole-lot execution using --lot-size.")
    parser.add_argument("--initial-capital", type=float, default=1_000_000.0)
    parser.add_argument("--lot-size", type=int, default=1000)
    parser.add_argument("--commission-rate", type=float, default=0.001425)
    parser.add_argument("--sell-tax-rate", type=float, default=0.003)
    parser.add_argument("--enforce-price-limit", action="store_true", help="Conservatively block buys at limit-up and sells at limit-down.")
    parser.add_argument("--price-limit-pct", type=float, default=0.10)
    parser.add_argument("--output-json", default="")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_arg_parser().parse_args(argv)
    symbols = load_symbols(args.universe_json, args.symbol)
    if not symbols:
        print(json.dumps({"error": "no symbols to simulate"}, ensure_ascii=False, indent=2))
        return 2
    report = simulate_portfolio(
        symbols=symbols,
        start=args.start,
        end=args.end,
        rebalance_frequency=args.rebalance_frequency,
        lookback_days=args.lookback_days,
        momentum_window=args.momentum_window,
        volatility_window=args.volatility_window,
        min_bars=args.min_bars,
        top_n=args.top_n,
        cash_weight=args.cash_weight,
        max_weight=args.max_weight,
        transaction_cost=args.transaction_cost,
        enforce_lot_size=args.enforce_lot_size,
        initial_capital=args.initial_capital,
        lot_size=args.lot_size,
        commission_rate=args.commission_rate,
        sell_tax_rate=args.sell_tax_rate,
        enforce_price_limit=args.enforce_price_limit,
        price_limit_pct=args.price_limit_pct,
    )
    text = json.dumps(report, ensure_ascii=False, indent=2)
    print(text)
    if args.output_json:
        path = Path(args.output_json)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text + "\n", encoding="utf-8")
    return 0 if not report.get("error") else 1


if __name__ == "__main__":
    raise SystemExit(main())
