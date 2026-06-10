#!/usr/bin/env python3
"""Run local-only TW rank rotation stress replay from historical signal artifacts.

This script is research-only. It reads isolated historical top50 signal
artifacts and local Yahoo-adjusted normalized CSV prices. It never updates
latest_signal.json, publishes providers, calls FinMind, or writes trading state.
"""
from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from datetime import date, datetime, timezone
from math import floor
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SIGNAL_ROOT = ROOT / "qlib_pipeline/data_tw/experiments/option_c_historical_signal_backfill"
DEFAULT_PRICE_ROOT = ROOT / "qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_normalized"
DEFAULT_OUTPUT_ROOT = ROOT / "data_tw/experiments/strategy_stress_replay"


@dataclass
class PriceStore:
    by_symbol: dict[str, dict[str, float]]
    dates: list[str]

    def close_after(self, symbol: str, asof: str) -> tuple[str, float] | None:
        rows = self.by_symbol.get(symbol) or self.by_symbol.get(f"TW{symbol}")
        if not rows:
            return None
        for day in self.dates:
            if day > asof and day in rows:
                return day, rows[day]
        return None


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def parse_date(raw: str) -> date:
    return date.fromisoformat(str(raw)[:10])


def load_prices(price_root: Path) -> PriceStore:
    by_symbol: dict[str, dict[str, float]] = {}
    all_dates: set[str] = set()
    for path in sorted(price_root.glob("TW*.csv")):
        symbol = path.stem
        rows: dict[str, float] = {}
        with path.open("r", encoding="utf-8", newline="") as fh:
            for row in csv.DictReader(fh):
                day = str(row.get("date") or "")
                try:
                    close = float(row.get("close") or 0)
                except Exception:
                    close = 0.0
                if day and close > 0:
                    rows[day] = close
                    all_dates.add(day)
        if rows:
            by_symbol[symbol] = rows
            by_symbol[symbol[2:]] = rows
    return PriceStore(by_symbol=by_symbol, dates=sorted(all_dates))


def signal_dirs(signal_root: Path, start: str, end: str) -> list[Path]:
    out: list[Path] = []
    for path in sorted(signal_root.glob("option_c_daily_signal_*_historical_backfill")):
        summary = path / "signal_summary.json"
        top50 = path / "top50_signals.csv"
        if not summary.exists() or not top50.exists():
            continue
        try:
            payload = json.loads(summary.read_text(encoding="utf-8"))
        except Exception:
            continue
        asof = str(payload.get("asof") or "")
        if start <= asof <= end and payload.get("status") == "accepted":
            out.append(path)
    return out


def load_ranks(run_dir: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with (run_dir / "top50_signals.csv").open("r", encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            symbol = str(row.get("symbol") or row.get("instrument") or "").replace("TW", "")
            try:
                rank = int(float(row.get("rank") or 999999))
            except Exception:
                rank = 999999
            try:
                score = float(row.get("score") or 0.0)
            except Exception:
                score = 0.0
            rows.append({"symbol": symbol, "instrument": f"TW{symbol}", "rank": rank, "score": score})
    rows.sort(key=lambda item: (item["rank"], item["symbol"]))
    return rows


def build_market_proxy(prices: PriceStore, symbols: list[str]) -> dict[str, float]:
    bases: dict[str, float] = {}
    rows_by_symbol: dict[str, dict[str, float]] = {}
    for symbol in symbols:
        rows = prices.by_symbol.get(symbol) or prices.by_symbol.get(f"TW{symbol}")
        if not rows:
            continue
        first_day = next((day for day in prices.dates if day in rows and rows[day] > 0), None)
        if first_day:
            bases[symbol] = rows[first_day]
            rows_by_symbol[symbol] = rows
    curve: dict[str, float] = {}
    for day in prices.dates:
        values = [rows[day] / bases[symbol] for symbol, rows in rows_by_symbol.items() if day in rows and bases.get(symbol, 0) > 0]
        if values:
            curve[day] = sum(values) / len(values)
    return curve


def market_state_for_asof(market_proxy: dict[str, float], asof: str) -> str:
    days = [day for day in sorted(market_proxy) if day <= asof]
    if len(days) < 120:
        return "normal"
    values = [market_proxy[day] for day in days]
    close = values[-1]
    ma60 = sum(values[-60:]) / 60.0
    ma120 = sum(values[-120:]) / 120.0
    ret20 = close / values[-21] - 1.0 if len(values) > 20 and values[-21] > 0 else 0.0
    ret60 = close / values[-61] - 1.0 if len(values) > 60 and values[-61] > 0 else 0.0
    if close > ma120 and ma60 > ma120 and ret60 > 0:
        return "normal"
    if (close < ma120 and ret20 < -0.08) or ret60 < -0.15:
        return "severe"
    if (close < ma60 and ma60 < ma120) or ret20 < -0.06 or ret60 < -0.10:
        return "caution"
    return "normal"


def affordable_qty(cash_budget: float, price: float, lot_size: int, fee_rate: float) -> int:
    gross_unit = price * (1.0 + fee_rate)
    if gross_unit <= 0:
        return 0
    return floor(cash_budget / gross_unit / lot_size) * lot_size


def replay_rank_rotation(
    *,
    runs: list[Path],
    prices: PriceStore,
    threshold: int,
    initial_cash: float,
    max_holdings: int,
    lot_size: int,
    fee_rate: float,
    sell_tax_rate: float,
    market_proxy: dict[str, float] | None = None,
    risk_control: bool = False,
    adaptive_score: bool = False,
) -> dict[str, Any]:
    cash = initial_cash
    holdings: dict[str, int] = {}
    fees = 0.0
    actions: list[dict[str, Any]] = []
    curve: list[dict[str, Any]] = []
    missing_prices: list[str] = []
    peak = initial_cash
    max_drawdown = 0.0
    risk_paused = False
    risk_pause_days = 0
    risk_blocked_buys = 0

    for run_dir in runs:
        summary = json.loads((run_dir / "signal_summary.json").read_text(encoding="utf-8"))
        asof = str(summary.get("asof") or "")
        ranks_list = load_ranks(run_dir)
        rank_map = {item["symbol"]: item["rank"] for item in ranks_list}
        pre_equity = cash
        for symbol, qty in holdings.items():
            quote = prices.close_after(symbol, asof)
            if quote is not None:
                pre_equity += qty * quote[1]
        pre_drawdown = pre_equity / peak - 1.0 if peak > 0 else 0.0
        market_state = market_state_for_asof(market_proxy or {}, asof) if market_proxy else "normal"
        if risk_control and market_state != "normal" and pre_drawdown <= -0.08:
            risk_paused = True
        elif risk_control and (market_state == "normal" or pre_drawdown >= -0.04):
            risk_paused = False

        sell_candidates = [(rank_map.get(symbol, 999999), symbol) for symbol in holdings if rank_map.get(symbol, 999999) > threshold]
        sell_candidates.sort(reverse=True)
        if sell_candidates:
            _, symbol = sell_candidates[0]
            quote = prices.close_after(symbol, asof)
            if quote is None:
                missing_prices.append(f"{asof}:{symbol}:sell")
            else:
                trade_date, price = quote
                qty = holdings.pop(symbol)
                proceeds = qty * price
                fee_tax = proceeds * (fee_rate + sell_tax_rate)
                cash += proceeds - fee_tax
                fees += fee_tax
                actions.append({"asof": asof, "trade_date": trade_date, "symbol": symbol, "action": "sell", "quantity": qty, "price": round(price, 4), "reason": f"dropped_out_top{threshold}"})

        buy_item = None
        blocked_by_score = 0
        for candidate in (item for item in ranks_list if item["rank"] <= 10 and item["symbol"] not in holdings):
            if adaptive_score and market_state != "normal" and not (0.04 <= float(candidate.get("score") or 0.0) <= 0.08):
                blocked_by_score += 1
                actions.append({"asof": asof, "trade_date": None, "symbol": candidate["symbol"], "action": "skip_buy", "quantity": 0, "price": None, "reason": "adaptive_score_out_of_004_008"})
                continue
            buy_item = candidate
            break
        if risk_control and risk_paused:
            risk_pause_days += 1
            if buy_item and len(holdings) < max_holdings:
                risk_blocked_buys += 1
                actions.append({"asof": asof, "trade_date": None, "symbol": buy_item["symbol"], "action": "skip_buy", "quantity": 0, "price": None, "reason": "portfolio_drawdown_pause"})
            buy_item = None
        if buy_item and len(holdings) < max_holdings:
            symbol = buy_item["symbol"]
            quote = prices.close_after(symbol, asof)
            if quote is None:
                missing_prices.append(f"{asof}:{symbol}:buy")
            else:
                trade_date, price = quote
                remaining_slots = max(1, max_holdings - len(holdings))
                qty = affordable_qty(cash / remaining_slots, price, lot_size, fee_rate)
                cost = qty * price
                fee = cost * fee_rate
                if qty > 0 and cash >= cost + fee:
                    cash -= cost + fee
                    fees += fee
                    holdings[symbol] = holdings.get(symbol, 0) + qty
                    actions.append({"asof": asof, "trade_date": trade_date, "symbol": symbol, "action": "buy", "quantity": qty, "price": round(price, 4), "reason": "highest_ranked_top10_not_held"})

        equity = cash
        for symbol, qty in holdings.items():
            quote = prices.close_after(symbol, asof)
            if quote is not None:
                equity += qty * quote[1]
        peak = max(peak, equity)
        if peak > 0:
            max_drawdown = min(max_drawdown, equity / peak - 1.0)
        curve.append({"date": asof, "equity": round(equity, 2), "cash": round(cash, 2), "holding_count": len(holdings)})

    final_equity = curve[-1]["equity"] if curve else initial_cash
    return {
        "strategy": f"rank_rotate_top{threshold}{'_adaptive_score' if adaptive_score else ''}{'_risk_control' if risk_control else ''}",
        "label": f"跌出 Top{threshold} 轮动{' + 自适应 score' if adaptive_score else ''}{' + 回撤暂停补仓' if risk_control else ''}",
        "metrics": {
            "total_return": round(final_equity / initial_cash - 1.0, 6) if initial_cash > 0 else 0.0,
            "max_drawdown": round(max_drawdown, 6),
            "action_count": len(actions),
            "buy_count": sum(1 for item in actions if item["action"] == "buy"),
            "sell_count": sum(1 for item in actions if item["action"] == "sell"),
            "fee_and_tax": round(fees, 2),
            "final_equity": round(final_equity, 2),
        },
        "holdings": holdings,
        "actions": actions,
        "equity_curve": curve,
        "risk_control": {"enabled": risk_control, "pause_days": risk_pause_days, "blocked_buys": risk_blocked_buys, "trigger": "market_caution_or_severe_and_portfolio_drawdown_below_8pct" if risk_control else "disabled"},
        "adaptive_score": {"enabled": adaptive_score},
        "data_quality": {"missing_price_count": len(missing_prices), "missing_price_sample": missing_prices[:20]},
    }


def equal_weight_benchmark(*, start: str, end: str, prices: PriceStore, symbols: list[str]) -> dict[str, Any]:
    returns: list[float] = []
    for symbol in symbols:
        rows = prices.by_symbol.get(symbol) or prices.by_symbol.get(f"TW{symbol}")
        if not rows:
            continue
        start_days = [day for day in prices.dates if day >= start and day in rows]
        end_days = [day for day in prices.dates if day <= end and day in rows]
        if not start_days or not end_days:
            continue
        first = rows[start_days[0]]
        last = rows[end_days[-1]]
        if first > 0 and last > 0:
            returns.append(last / first - 1.0)
    avg = sum(returns) / len(returns) if returns else 0.0
    return {"type": "equal_weight_150_universe_proxy", "return": round(avg, 6), "sample_size": len(returns)}


def write_outputs(output_dir: Path, payload: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "summary.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# TW Rank Rotation Stress Replay Report",
        "",
        f"- created_at: `{payload['created_at']}`",
        f"- range: `{payload['config']['start_date']}` to `{payload['config']['end_date']}`",
        f"- signal_root: `{payload['config']['signal_root']}`",
        f"- price_root: `{payload['config']['price_root']}`",
        f"- trading_days_used: `{payload['source']['trading_days_used']}`",
        f"- simulation_only: `{payload['safety']['simulation_only']}`",
        f"- local_only_prices: `{payload['safety']['local_only_prices']}`",
        "",
        "| 策略 | 收益率 | 最大回撤 | 动作次数 | 买入 | 卖出 | 费用税费 | 期末权益 | 净超额收益率* |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    benchmark = float((payload.get("benchmark") or {}).get("return") or 0.0)
    for item in payload["results"]:
        m = item["metrics"]
        net_excess = float(m["total_return"]) - benchmark
        lines.append(
            f"| {item['label']} | {m['total_return']:.2%} | {m['max_drawdown']:.2%} | {m['action_count']} | {m['buy_count']} | {m['sell_count']} | {m['fee_and_tax']:.2f} | {m['final_equity']:.2f} | {net_excess:.2%} |"
        )
    lines.extend([
        "",
        f"\\* 净超额收益率 = 已含手续费/交易税后的策略收益率 - 150 支台股 universe 等权买入持有代理收益率（{benchmark:.2%}）。这不是官方大盘指数。",
        "",
        "## Safety",
        "",
        "- research_signal_not_order: `true`",
        "- latest_signal_updated: `false`",
        "- provider_publish_triggered: `false`",
        "- broker_or_order_action: `false`",
    ])
    (output_dir / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Local-only TW rank rotation stress replay.")
    parser.add_argument("--signal-root", required=True)
    parser.add_argument("--start-date", required=True)
    parser.add_argument("--end-date", required=True)
    parser.add_argument("--price-root", default=str(DEFAULT_PRICE_ROOT))
    parser.add_argument("--output-dir", default="")
    parser.add_argument("--initial-cash", type=float, default=1_000_000.0)
    parser.add_argument("--max-holdings", type=int, default=10)
    parser.add_argument("--lot-size", type=int, default=10)
    parser.add_argument("--fee-rate", type=float, default=0.001425)
    parser.add_argument("--sell-tax-rate", type=float, default=0.003)
    args = parser.parse_args()

    start = args.start_date[:10]
    end = args.end_date[:10]
    if parse_date(end) < parse_date(start):
        start, end = end, start
    signal_root = Path(args.signal_root).expanduser().resolve(strict=False)
    price_root = Path(args.price_root).expanduser().resolve(strict=False)
    output_dir = Path(args.output_dir).expanduser().resolve(strict=False) if args.output_dir else DEFAULT_OUTPUT_ROOT / f"rank_rotation_{start.replace('-', '')}_{end.replace('-', '')}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"

    runs = signal_dirs(signal_root, start, end)
    prices = load_prices(price_root)
    symbols = sorted({item["symbol"] for run_dir in runs for item in load_ranks(run_dir)})
    market_proxy = build_market_proxy(prices, symbols)
    results = [
        replay_rank_rotation(runs=runs, prices=prices, threshold=30, initial_cash=args.initial_cash, max_holdings=args.max_holdings, lot_size=args.lot_size, fee_rate=args.fee_rate, sell_tax_rate=args.sell_tax_rate, market_proxy=market_proxy),
        replay_rank_rotation(runs=runs, prices=prices, threshold=50, initial_cash=args.initial_cash, max_holdings=args.max_holdings, lot_size=args.lot_size, fee_rate=args.fee_rate, sell_tax_rate=args.sell_tax_rate, market_proxy=market_proxy),
        replay_rank_rotation(runs=runs, prices=prices, threshold=30, initial_cash=args.initial_cash, max_holdings=args.max_holdings, lot_size=args.lot_size, fee_rate=args.fee_rate, sell_tax_rate=args.sell_tax_rate, market_proxy=market_proxy, risk_control=True),
        replay_rank_rotation(runs=runs, prices=prices, threshold=50, initial_cash=args.initial_cash, max_holdings=args.max_holdings, lot_size=args.lot_size, fee_rate=args.fee_rate, sell_tax_rate=args.sell_tax_rate, market_proxy=market_proxy, risk_control=True),
        replay_rank_rotation(runs=runs, prices=prices, threshold=30, initial_cash=args.initial_cash, max_holdings=args.max_holdings, lot_size=args.lot_size, fee_rate=args.fee_rate, sell_tax_rate=args.sell_tax_rate, market_proxy=market_proxy, adaptive_score=True),
        replay_rank_rotation(runs=runs, prices=prices, threshold=50, initial_cash=args.initial_cash, max_holdings=args.max_holdings, lot_size=args.lot_size, fee_rate=args.fee_rate, sell_tax_rate=args.sell_tax_rate, market_proxy=market_proxy, adaptive_score=True),
        replay_rank_rotation(runs=runs, prices=prices, threshold=30, initial_cash=args.initial_cash, max_holdings=args.max_holdings, lot_size=args.lot_size, fee_rate=args.fee_rate, sell_tax_rate=args.sell_tax_rate, market_proxy=market_proxy, adaptive_score=True, risk_control=True),
        replay_rank_rotation(runs=runs, prices=prices, threshold=50, initial_cash=args.initial_cash, max_holdings=args.max_holdings, lot_size=args.lot_size, fee_rate=args.fee_rate, sell_tax_rate=args.sell_tax_rate, market_proxy=market_proxy, adaptive_score=True, risk_control=True),
    ]
    payload = {
        "ok": bool(runs),
        "created_at": utc_now(),
        "config": {
            "start_date": start,
            "end_date": end,
            "signal_root": str(signal_root),
            "price_root": str(price_root),
            "initial_cash": args.initial_cash,
            "max_holdings": args.max_holdings,
            "lot_size": args.lot_size,
            "fee_rate": args.fee_rate,
            "sell_tax_rate": args.sell_tax_rate,
        },
        "source": {"trading_days_used": len(runs), "symbols_used": len(symbols)},
        "benchmark": equal_weight_benchmark(start=start, end=end, prices=prices, symbols=symbols),
        "results": results,
        "safety": {
            "simulation_only": True,
            "research_signal_not_order": True,
            "local_only_prices": True,
            "finmind_called": False,
            "latest_signal_updated": False,
            "provider_publish_triggered": False,
            "broker_or_order_action": False,
        },
    }
    write_outputs(output_dir, payload)
    print(json.dumps({"ok": payload["ok"], "output_dir": str(output_dir), "trading_days_used": len(runs), "benchmark": payload["benchmark"], "results": [{"strategy": item["strategy"], "metrics": item["metrics"], "data_quality": item["data_quality"]} for item in results]}, ensure_ascii=False, indent=2))
    return 0 if runs else 2


if __name__ == "__main__":
    raise SystemExit(main())
