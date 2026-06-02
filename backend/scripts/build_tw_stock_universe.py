#!/usr/bin/env python3
"""Build a Taiwan stock universe for cross-sectional strategies.

Phase 3 starts with a conservative universe builder instead of changing the
large backtest engine. It filters stock/ETF metadata, fetches recent daily bars,
computes liquidity metrics, and emits a symbol_list compatible with existing
cross-sectional trading_config: ["TWStock:2330", ...].
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict, dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.setdefault("SECRET_KEY", "build-tw-stock-universe")
os.environ.setdefault("ADMIN_USER", "universe")
os.environ.setdefault("ADMIN_PASSWORD", "universepass")

from app.data.market_symbols_seed import get_all_symbols  # noqa: E402
from app.data_sources.tw_stock import TWStockDataSource  # noqa: E402
from scripts.archive_tw_stock_daily import fetch_finmind_rows, parse_finmind_rows  # noqa: E402


@dataclass(frozen=True)
class UniverseCandidate:
    symbol: str
    config_symbol: str
    name: str
    exchange: str
    instrument_type: str
    bars: int
    last_trade_date: str
    last_close: float
    avg_volume: float
    avg_trading_money: float
    passes: bool
    reasons: List[str]
    rank_score: float


def parse_symbols(raw_symbols: Sequence[str]) -> List[str]:
    out: List[str] = []
    for raw in raw_symbols or []:
        for part in str(raw or "").replace("\n", ",").split(","):
            symbol = TWStockDataSource.normalize_symbol(part).symbol
            if symbol and symbol not in out:
                out.append(symbol)
    return out


def normalize_symbol_metadata(rows: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    seen = set()
    for row in rows or []:
        symbol = TWStockDataSource.normalize_symbol(row.get("symbol") or "").symbol
        if not symbol or symbol in seen:
            continue
        seen.add(symbol)
        instrument_type = str(row.get("instrument_type") or "").strip().lower()
        if not instrument_type:
            if symbol.startswith(("00", "006", "007", "008", "009")):
                instrument_type = "etf"
            else:
                instrument_type = "stock"
        out.append({
            "symbol": symbol,
            "name": str(row.get("name") or "").strip(),
            "exchange": str(row.get("exchange") or "TWSE").strip() or "TWSE",
            "instrument_type": instrument_type,
        })
    out.sort(key=lambda item: item["symbol"])
    return out


def load_candidate_symbols(raw_symbols: Sequence[str], *, include_etf: bool = False, limit_candidates: int = 0) -> List[Dict[str, Any]]:
    explicit = parse_symbols(raw_symbols)
    if explicit:
        rows = [{"symbol": s, "name": "", "exchange": "", "instrument_type": ""} for s in explicit]
    else:
        rows = get_all_symbols("TWStock")
    candidates = normalize_symbol_metadata(rows)
    if not include_etf:
        candidates = [item for item in candidates if item.get("instrument_type") != "etf"]
    if limit_candidates and limit_candidates > 0:
        candidates = candidates[:limit_candidates]
    return candidates


def evaluate_candidate(
    meta: Dict[str, Any],
    *,
    start: str,
    end: str,
    min_bars: int,
    min_avg_volume: float,
    min_avg_trading_money: float,
) -> UniverseCandidate:
    symbol = meta["symbol"]
    reasons: List[str] = []
    try:
        records = parse_finmind_rows(fetch_finmind_rows(symbol, start, end), symbol=symbol)
    except Exception as exc:
        return UniverseCandidate(
            symbol=symbol,
            config_symbol=f"TWStock:{symbol}",
            name=str(meta.get("name") or ""),
            exchange=str(meta.get("exchange") or ""),
            instrument_type=str(meta.get("instrument_type") or ""),
            bars=0,
            last_trade_date="",
            last_close=0.0,
            avg_volume=0.0,
            avg_trading_money=0.0,
            passes=False,
            reasons=[f"fetch_error:{type(exc).__name__}"],
            rank_score=0.0,
        )

    clean = [r for r in records if not r.quality_flags]
    bars = len(clean)
    avg_volume = round(sum(r.volume for r in clean) / bars, 2) if bars else 0.0
    avg_money = round(sum(r.trading_money for r in clean) / bars, 2) if bars else 0.0
    last = clean[-1] if clean else None
    if bars < min_bars:
        reasons.append("insufficient_bars")
    if avg_volume < min_avg_volume:
        reasons.append("low_avg_volume")
    if avg_money < min_avg_trading_money:
        reasons.append("low_avg_trading_money")
    return UniverseCandidate(
        symbol=symbol,
        config_symbol=f"TWStock:{symbol}",
        name=str(meta.get("name") or ""),
        exchange=str(meta.get("exchange") or ""),
        instrument_type=str(meta.get("instrument_type") or ""),
        bars=bars,
        last_trade_date=last.trade_date if last else "",
        last_close=float(last.close) if last else 0.0,
        avg_volume=avg_volume,
        avg_trading_money=avg_money,
        passes=not reasons,
        reasons=reasons,
        rank_score=avg_money,
    )


def build_monitor_config_payload(
    symbols: Sequence[str],
    *,
    name: str = "default",
    limit_bars: int = 120,
    refresh_interval_sec: int = 300,
    score_change_threshold: float = 8.0,
    enabled: bool = False,
) -> Dict[str, Any]:
    """Return a monitor config JSON payload for manual review/import.

    The payload is disabled by default and is not written to the database by
    this builder. Users can copy it into POST /api/tw-stock/monitor/config
    after reviewing the selected symbols.
    """
    clean_symbols = parse_symbols(symbols)[:50]
    return {
        "name": str(name or "default")[:80],
        "symbols": clean_symbols,
        "limit_bars": max(20, min(int(limit_bars or 120), 500)),
        "refresh_interval_sec": max(0, min(int(refresh_interval_sec or 300), 86400)),
        "score_change_threshold": max(0.0, min(float(score_change_threshold or 8.0), 100.0)),
        "enabled": bool(enabled),
        "notes": "Generated by build_tw_stock_universe.py for manual research review; no automatic trading.",
    }


def build_manual_review_payload(*, monitor_config_path: str = "/tmp/tw_stock_monitor_universe.json") -> Dict[str, Any]:
    path = str(monitor_config_path or "/tmp/tw_stock_monitor_universe.json")
    return {
        "required": True,
        "steps": [
            "review_universe_selection",
            "run_quality_gate_preflight",
            "run_import_dry_run",
            "apply_only_after_manual_approval",
        ],
        "quality_gate_command": (
            "PYTHONPATH=backend python "
            "backend/scripts/preflight_tw_stock_monitor_config.py "
            f"--input-json {path} --limit 120 --min-bars 60 --max-stale-days 5 --fail-on-quality-gate"
        ),
        "dry_run_import_command": (
            "PYTHONPATH=backend python "
            "backend/scripts/import_tw_stock_monitor_config.py "
            f"--input-json {path} --dry-run"
        ),
        "apply_command_template": (
            "PYTHONPATH=backend python "
            "backend/scripts/import_tw_stock_monitor_config.py "
            f"--input-json {path} --apply"
        ),
        "orders_enabled": False,
        "connects_to_broker": False,
        "db_written_by_universe_builder": False,
    }


def build_universe(
    *,
    symbols: Sequence[str],
    start: str,
    end: str,
    include_etf: bool = False,
    limit_candidates: int = 0,
    min_bars: int = 10,
    min_avg_volume: float = 1_000_000,
    min_avg_trading_money: float = 100_000_000,
    max_universe: int = 50,
) -> Dict[str, Any]:
    metas = load_candidate_symbols(symbols, include_etf=include_etf, limit_candidates=limit_candidates)
    candidates = [
        evaluate_candidate(
            meta,
            start=start,
            end=end,
            min_bars=min_bars,
            min_avg_volume=min_avg_volume,
            min_avg_trading_money=min_avg_trading_money,
        )
        for meta in metas
    ]
    passed = [item for item in candidates if item.passes]
    passed.sort(key=lambda item: item.rank_score, reverse=True)
    if max_universe and max_universe > 0:
        selected = passed[:max_universe]
    else:
        selected = passed
    return {
        "start": start,
        "end": end,
        "include_etf": bool(include_etf),
        "candidate_count": len(candidates),
        "passed_count": len(passed),
        "selected_count": len(selected),
        "symbol_list": [item.config_symbol for item in selected],
        "symbols": [item.symbol for item in selected],
        "filters": {
            "min_bars": min_bars,
            "min_avg_volume": min_avg_volume,
            "min_avg_trading_money": min_avg_trading_money,
            "max_universe": max_universe,
        },
        "selected": [asdict(item) for item in selected],
        "rejected": [asdict(item) for item in candidates if not item.passes],
        "monitor_config": build_monitor_config_payload([item.symbol for item in selected]),
        "manual_review": build_manual_review_payload(),
        "trading": {"orders_enabled": False, "note": "Universe output is research-only and does not submit orders."},
    }


def _default_start() -> str:
    return (date.today() - timedelta(days=90)).isoformat()


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build TWStock universe for cross-sectional strategies.")
    parser.add_argument("--symbol", action="append", default=[], help="Optional symbol whitelist. Can be repeated or comma-separated.")
    parser.add_argument("--start", default=_default_start(), help="Start date YYYY-MM-DD. Default: today-90d.")
    parser.add_argument("--end", default=date.today().isoformat(), help="End date YYYY-MM-DD. Default: today.")
    parser.add_argument("--include-etf", action="store_true", help="Include ETF candidates. Default: stock only.")
    parser.add_argument("--limit-candidates", type=int, default=0, help="Limit raw candidates, useful for smoke runs.")
    parser.add_argument("--min-bars", type=int, default=10)
    parser.add_argument("--min-avg-volume", type=float, default=1_000_000)
    parser.add_argument("--min-avg-trading-money", type=float, default=100_000_000)
    parser.add_argument("--max-universe", type=int, default=50)
    parser.add_argument("--monitor-config-json", default="", help="Optional output path for monitor config JSON payload. Disabled by default.")
    parser.add_argument("--monitor-name", default="default", help="Monitor config name used with --monitor-config-json.")
    parser.add_argument("--monitor-enabled", action="store_true", help="Mark generated monitor config enabled. Default keeps it disabled for manual review.")
    parser.add_argument("--output-json", default="", help="Optional output JSON path.")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_arg_parser().parse_args(argv)
    report = build_universe(
        symbols=parse_symbols(args.symbol),
        start=args.start,
        end=args.end,
        include_etf=args.include_etf,
        limit_candidates=args.limit_candidates,
        min_bars=args.min_bars,
        min_avg_volume=args.min_avg_volume,
        min_avg_trading_money=args.min_avg_trading_money,
        max_universe=args.max_universe,
    )
    if args.monitor_config_json:
        report["manual_review"] = build_manual_review_payload(monitor_config_path=args.monitor_config_json)
    text = json.dumps(report, ensure_ascii=False, indent=2)
    print(text)
    if args.output_json:
        path = Path(args.output_json)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text + "\n", encoding="utf-8")
    if args.monitor_config_json:
        payload = build_monitor_config_payload(
            report.get("symbols") or [],
            name=args.monitor_name,
            enabled=bool(args.monitor_enabled),
        )
        path = Path(args.monitor_config_json)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0 if report["selected_count"] > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
