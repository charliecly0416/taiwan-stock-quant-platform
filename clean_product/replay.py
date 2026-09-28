from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd

from .models import ModelRunner
from .config import trading_days
from .strategy import top50_exit_one_worst_sell


def _price_table(prices: pd.DataFrame) -> pd.DataFrame:
    frame = prices.copy()
    if "instrument" not in frame and "stock_id" in frame:
        frame = frame.rename(columns={"stock_id": "instrument"})
    frame["instrument"] = frame.instrument.astype(str).str.extract(r"(\d+)")[0].str.zfill(4).radd("TW")
    frame["date"] = frame.date.astype(str).str[:10]
    frame["open"] = pd.to_numeric(frame.get("open", np.nan), errors="coerce")
    frame["close"] = pd.to_numeric(frame.close, errors="coerce")
    return frame.drop_duplicates(["date", "instrument"], keep="last").set_index(["date", "instrument"]).sort_index()


def _drawdown(values: list[float]) -> float:
    if not values:
        return 0.0
    series = pd.Series(values, dtype=float)
    return float((series / series.cummax() - 1).min())


def _valid_price(table: pd.DataFrame, day: str, symbol: str, field: str) -> bool:
    key = (day, symbol)
    return key in table.index and np.isfinite(table.loc[key, field]) and table.loc[key, field] > 0


def replay(config: dict, data: dict[str, pd.DataFrame], model_name: str, start: str, end: str, *, fixture: bool = False) -> dict[str, Any]:
    blocked = {"status": "BLOCKED", "model": model_name, "start": start, "end": end,
               "readonly": True, "simulation_only": True, "fixture": fixture}
    calendar = trading_days(config) if not fixture else []
    if not fixture and not calendar:
        return {**blocked, "reason": "PROVIDER_CALENDAR_UNAVAILABLE"}
    table = _price_table(data.get("prices", pd.DataFrame()))
    days = sorted(day for day in table.index.get_level_values("date").unique() if start <= day <= end)
    if not fixture:
        expected = {day for day in calendar if start <= day <= end}
        if expected - set(days):
            return {**blocked, "reason": "REPLAY_PRICE_DATES_MISSING", "missing_dates": sorted(expected - set(days))}
        if set(days) - expected:
            return {**blocked, "reason": "REPLAY_PRICE_DATES_OUTSIDE_CALENDAR", "unexpected_dates": sorted(set(days) - expected)}
    if len(days) < 2:
        raise ValueError("replay needs at least two trading days")
    simulation = config.get("simulation") or {}
    cash = float(simulation.get("initial_cash", 1_000_000)); initial_cash = cash
    max_positions = int(simulation.get("max_positions", 50))
    buy_rate = float(simulation.get("buy_cost_rate", .001425)); sell_rate = float(simulation.get("sell_cost_rate", .004425)); min_cost = float(simulation.get("min_cost", 20))
    if (not all(math.isfinite(value) for value in (cash, buy_rate, sell_rate, min_cost))
            or cash <= 0 or min(buy_rate, sell_rate, min_cost) < 0 or not 1 <= max_positions <= 50):
        raise ValueError("invalid simulation cash, fees, or position limit")
    holdings: dict[str, int] = {}
    nav_rows: list[dict[str, Any]] = [{"date": days[0], "cash": cash, "market_value": 0.0, "nav": cash, "positions": 0}]
    trades: list[dict[str, Any]] = []; rankings: list[dict[str, Any]] = []

    def blocked_price(day: str, symbol: str, field: str) -> dict[str, Any]:
        return {"status": "BLOCKED", "model": model_name, "start": start, "end": end,
                "blocked_on": day, "reason": f"REPLAY_PRICE_UNAVAILABLE: {symbol} {field} on {day}",
                "readonly": True, "simulation_only": True, "fixture": fixture}
    runner = ModelRunner(config)
    try:
        runner.precompute(days[:-1], data=data, fixture=fixture)
    except (ValueError, RuntimeError, OSError, KeyError) as exc:
        return {"status": "BLOCKED", "model": model_name, "start": start, "end": end,
                "reason": str(exc), "readonly": True, "simulation_only": True, "fixture": fixture}
    for index, signal_day in enumerate(days[:-1]):
        execute_day = days[index + 1]
        result = runner.run(model_name, signal_day, data=data, fixture=fixture, write=False)
        if result.status != "READY":
            return {"status": "BLOCKED", "model": model_name, "start": start, "end": end, "blocked_on": signal_day, "reason": result.reason, "readonly": True, "simulation_only": True}
        ranking = result.rows.head(50)
        rankings.append({"date": signal_day, "top_symbol": str(ranking.iloc[0].instrument), "top50_count": len(ranking)})
        intents = top50_exit_one_worst_sell(result.rows, set(holdings), max_positions=max_positions, full_ranks=result.full_ranks)
        for symbol in intents.instrument:
            if not _valid_price(table, execute_day, symbol, "open"):
                return blocked_price(execute_day, symbol, "open")
        for intent in intents[intents.action.eq("sell")].itertuples(index=False):
            key = (execute_day, intent.instrument)
            quantity = holdings.pop(intent.instrument); price = float(table.loc[key, "open"]); gross = quantity * price; fee = max(min_cost, gross * sell_rate); cash += gross - fee
            trades.append({"signal_date": signal_day, "execute_date": execute_day, "instrument": intent.instrument, "action": "sell", "quantity": quantity, "price": price, "fee": fee, "reason": intent.reason})
        buys = list(intents[intents.action.eq("buy")].itertuples(index=False))
        for offset, intent in enumerate(buys):
            key = (execute_day, intent.instrument)
            price = float(table.loc[key, "open"]); slots = max(1, len(buys) - offset); budget = cash / slots
            # Both percentage commission and the minimum fee must fit this slot.
            quantity = min(math.floor(budget / (price * (1 + buy_rate))),
                           math.floor((budget - min_cost) / price))
            if quantity <= 0: continue
            gross = quantity * price; fee = max(min_cost, gross * buy_rate)
            if gross + fee > cash: continue
            cash -= gross + fee; holdings[intent.instrument] = holdings.get(intent.instrument, 0) + quantity
            trades.append({"signal_date": signal_day, "execute_date": execute_day, "instrument": intent.instrument, "action": "buy", "quantity": quantity, "price": price, "fee": fee, "reason": intent.reason})
        for symbol in holdings:
            if not _valid_price(table, execute_day, symbol, "close"):
                return blocked_price(execute_day, symbol, "close")
        market_value = sum(quantity * float(table.loc[(execute_day, symbol), "close"]) for symbol, quantity in holdings.items())
        nav_rows.append({"date": execute_day, "cash": cash, "market_value": market_value, "nav": cash + market_value, "positions": len(holdings)})
    nav = [row["nav"] for row in nav_rows]; final_nav = nav[-1]; daily_returns = pd.Series(nav, dtype=float).pct_change(fill_method=None).dropna()
    total_fees = float(sum(float(item.get("fee", 0.0)) for item in trades))
    turnover = float(sum(abs(float(item.get("quantity", 0))) * float(item.get("price", 0.0)) for item in trades) / initial_cash) if initial_cash else 0.0
    return {
        "status": "READY", "model": model_name, "strategy": config.get("strategy"), "execution": config.get("execution"), "start": start, "end": end,
        "trading_days": len(days), "initial_cash": initial_cash, "final_nav": final_nav, "cumulative_return": final_nav / initial_cash - 1,
        "max_drawdown": _drawdown(nav), "annualized_volatility": float(daily_returns.std(ddof=1) * np.sqrt(252)) if len(daily_returns) > 1 else 0.0,
        "trade_count": len(trades), "total_fees": total_fees, "turnover": turnover, "nav": nav_rows, "trades": trades, "rankings": rankings,
        "account": {"cash": cash, "market_value": nav_rows[-1]["market_value"] if nav_rows else 0.0, "nav": final_nav, "positions": sorted(holdings), "mode": "simulation_only"},
        "readonly": True, "simulation_only": True, "fixture": fixture,
    }
