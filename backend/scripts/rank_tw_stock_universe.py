#!/usr/bin/env python3
"""Rank a Taiwan stock universe for cross-sectional strategies.

This Phase 3 script scores a symbol list with a conservative long-only research
factor set: momentum, low volatility and liquidity. Optional archived factor
joins can be added later without changing the output contract.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.setdefault("SECRET_KEY", "rank-tw-stock-universe")
os.environ.setdefault("ADMIN_USER", "rank")
os.environ.setdefault("ADMIN_PASSWORD", "rankpass")

from app.data_sources.tw_stock import TWStockDataSource  # noqa: E402
from scripts.archive_tw_stock_daily import DailyBarRecord, fetch_finmind_rows, parse_finmind_rows  # noqa: E402
from scripts.build_tw_stock_universe import parse_symbols as parse_tw_symbols  # noqa: E402


@dataclass(frozen=True)
class RankedSymbol:
    symbol: str
    config_symbol: str
    bars: int
    last_trade_date: str
    last_close: float
    momentum: Optional[float]
    volatility: Optional[float]
    avg_trading_money: float
    momentum_score: float
    low_volatility_score: float
    liquidity_score: float
    composite_score: float
    rank: int
    reasons: List[str]


def parse_config_symbols(raw_symbols: Sequence[str]) -> List[str]:
    out: List[str] = []
    for raw in raw_symbols or []:
        for part in str(raw or "").replace("\n", ",").split(","):
            text = part.strip()
            if not text:
                continue
            if text.upper().startswith("TWSTOCK:"):
                text = text.split(":", 1)[1]
            symbol = TWStockDataSource.normalize_symbol(text).symbol
            if symbol and symbol not in out:
                out.append(symbol)
    return out


def load_symbols_from_universe_json(path: str) -> List[str]:
    if not path:
        return []
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    raw = payload.get("symbol_list") or payload.get("symbols") or []
    if not isinstance(raw, list):
        return []
    return parse_config_symbols(raw)


def _returns(records: Sequence[DailyBarRecord]) -> List[float]:
    out: List[float] = []
    prev: Optional[float] = None
    for item in records:
        close = float(item.close or 0)
        if prev and prev > 0 and close > 0:
            out.append(close / prev - 1.0)
        prev = close
    return out


def _std(values: Sequence[float]) -> Optional[float]:
    if len(values) < 2:
        return None
    mean = sum(values) / len(values)
    var = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
    return math.sqrt(var)


def _percentile_scores(values: Dict[str, float], *, reverse: bool = False) -> Dict[str, float]:
    if not values:
        return {}
    ordered = sorted(values.items(), key=lambda item: item[1], reverse=reverse)
    n = len(ordered)
    if n == 1:
        return {ordered[0][0]: 1.0}
    scores: Dict[str, float] = {}
    for idx, (symbol, _value) in enumerate(ordered):
        scores[symbol] = round(1.0 - idx / (n - 1), 8)
    return scores


def compute_raw_metrics(records: Sequence[DailyBarRecord], *, momentum_window: int, volatility_window: int) -> Dict[str, Any]:
    clean = [item for item in records if not item.quality_flags]
    clean.sort(key=lambda item: item.trade_date)
    if not clean:
        return {"bars": 0, "reasons": ["no_clean_bars"]}
    reasons: List[str] = []
    momentum = None
    if len(clean) > momentum_window:
        base = float(clean[-momentum_window - 1].close or 0)
        last = float(clean[-1].close or 0)
        if base > 0 and last > 0:
            momentum = round(last / base - 1.0, 8)
    else:
        reasons.append("insufficient_momentum_bars")
    rets = _returns(clean[-(volatility_window + 1):])
    volatility = _std(rets)
    if volatility is None:
        reasons.append("insufficient_volatility_bars")
    avg_money = sum(float(item.trading_money or 0) for item in clean) / len(clean)
    return {
        "bars": len(clean),
        "last_trade_date": clean[-1].trade_date,
        "last_close": float(clean[-1].close),
        "momentum": momentum,
        "volatility": round(volatility, 8) if volatility is not None else None,
        "avg_trading_money": round(avg_money, 2),
        "reasons": reasons,
    }


def fetch_symbol_records(symbol: str, start: str, end: str) -> List[DailyBarRecord]:
    return parse_finmind_rows(fetch_finmind_rows(symbol, start, end), symbol=symbol)


def rank_symbols(
    *,
    symbols: Sequence[str],
    start: str,
    end: str,
    momentum_window: int = 20,
    volatility_window: int = 20,
    min_bars: int = 30,
    weights: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    weights = weights or {"momentum": 0.5, "low_volatility": 0.3, "liquidity": 0.2}
    raw: Dict[str, Dict[str, Any]] = {}
    for symbol in parse_config_symbols(symbols):
        try:
            metrics = compute_raw_metrics(fetch_symbol_records(symbol, start, end), momentum_window=momentum_window, volatility_window=volatility_window)
        except Exception as exc:
            metrics = {"bars": 0, "reasons": [f"fetch_error:{type(exc).__name__}"]}
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

    ranked: List[RankedSymbol] = []
    for symbol, metrics in raw.items():
        ms = momentum_scores.get(symbol, 0.0)
        vs = low_vol_scores.get(symbol, 0.0)
        ls = liquidity_scores.get(symbol, 0.0)
        composite = round(
            ms * float(weights.get("momentum", 0))
            + vs * float(weights.get("low_volatility", 0))
            + ls * float(weights.get("liquidity", 0)),
            8,
        )
        ranked.append(RankedSymbol(
            symbol=symbol,
            config_symbol=f"TWStock:{symbol}",
            bars=int(metrics.get("bars") or 0),
            last_trade_date=str(metrics.get("last_trade_date") or ""),
            last_close=float(metrics.get("last_close") or 0),
            momentum=metrics.get("momentum"),
            volatility=metrics.get("volatility"),
            avg_trading_money=float(metrics.get("avg_trading_money") or 0),
            momentum_score=ms,
            low_volatility_score=vs,
            liquidity_score=ls,
            composite_score=composite,
            rank=0,
            reasons=list(metrics.get("reasons") or []),
        ))
    ranked.sort(key=lambda item: (item.composite_score, item.avg_trading_money), reverse=True)
    final: List[RankedSymbol] = []
    for idx, item in enumerate(ranked, start=1):
        final.append(RankedSymbol(**{**asdict(item), "rank": idx}))
    return {
        "start": start,
        "end": end,
        "count": len(final),
        "eligible_count": len(eligible),
        "weights": weights,
        "momentum_window": momentum_window,
        "volatility_window": volatility_window,
        "min_bars": min_bars,
        "rankings": [item.config_symbol for item in final if not item.reasons],
        "items": [asdict(item) for item in final],
    }


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Rank TWStock universe for cross-sectional strategies.")
    parser.add_argument("--symbol", action="append", default=[], help="TWStock:2330/2330 list. Can be repeated or comma-separated.")
    parser.add_argument("--universe-json", default="", help="JSON output from build_tw_stock_universe.py.")
    parser.add_argument("--start", required=True, help="Start date YYYY-MM-DD.")
    parser.add_argument("--end", required=True, help="End date YYYY-MM-DD.")
    parser.add_argument("--momentum-window", type=int, default=20)
    parser.add_argument("--volatility-window", type=int, default=20)
    parser.add_argument("--min-bars", type=int, default=30)
    parser.add_argument("--momentum-weight", type=float, default=0.5)
    parser.add_argument("--low-volatility-weight", type=float, default=0.3)
    parser.add_argument("--liquidity-weight", type=float, default=0.2)
    parser.add_argument("--output-json", default="", help="Optional output JSON path.")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_arg_parser().parse_args(argv)
    symbols = parse_config_symbols(args.symbol)
    for symbol in load_symbols_from_universe_json(args.universe_json):
        if symbol not in symbols:
            symbols.append(symbol)
    if not symbols:
        print(json.dumps({"error": "no symbols to rank"}, ensure_ascii=False, indent=2))
        return 2
    report = rank_symbols(
        symbols=symbols,
        start=args.start,
        end=args.end,
        momentum_window=args.momentum_window,
        volatility_window=args.volatility_window,
        min_bars=args.min_bars,
        weights={
            "momentum": args.momentum_weight,
            "low_volatility": args.low_volatility_weight,
            "liquidity": args.liquidity_weight,
        },
    )
    text = json.dumps(report, ensure_ascii=False, indent=2)
    print(text)
    if args.output_json:
        path = Path(args.output_json)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text + "\n", encoding="utf-8")
    return 0 if report["eligible_count"] > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
