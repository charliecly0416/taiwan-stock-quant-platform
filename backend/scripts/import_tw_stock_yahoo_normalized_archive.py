#!/usr/bin/env python3
"""Import local Yahoo/Scrapling normalized TWStock CSVs into qd_tw_stock_daily_bars.

This is an offline backfill bridge for the TWStock cross-analysis trend service.
It does not fetch network data and does not create orders or broker state.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from pathlib import Path
from typing import Any, Iterable, Sequence

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.utils.db import get_db_connection  # noqa: E402

DEFAULT_NORMALIZED_DIR = Path("qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/normalized_nonempty")


def normalize_symbol(raw: str) -> str:
    symbol = str(raw or "").strip().upper()
    if symbol.startswith("TWSE:") or symbol.startswith("TPEX:"):
        symbol = symbol.split(":", 1)[1]
    if symbol.startswith("TW") and symbol[2:].isdigit():
        symbol = symbol[2:]
    for suffix in (".TWSE", ".TPEX", ".TWO", ".TW"):
        if symbol.endswith(suffix):
            symbol = symbol[: -len(suffix)]
            break
    return symbol


def parse_symbols(raw_symbols: Sequence[str]) -> list[str]:
    out: list[str] = []
    for raw in raw_symbols or []:
        for part in str(raw or "").replace("\n", ",").split(","):
            symbol = normalize_symbol(part)
            if symbol and symbol not in out:
                out.append(symbol)
    return out


def load_symbols_from_file(path: str) -> list[str]:
    if not path:
        return []
    p = Path(path)
    if not p.exists():
        return []
    return parse_symbols(p.read_text(encoding="utf-8").splitlines())


def as_float(value: Any) -> float:
    try:
        return float(str(value).replace(",", "").strip())
    except Exception:
        return 0.0


def as_int(value: Any) -> int:
    return int(round(as_float(value)))


def iter_rows(path: Path, *, symbol: str, start: str, end: str) -> Iterable[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            trade_date = str(row.get("date") or "").strip()
            if not trade_date or trade_date < start or trade_date > end:
                continue
            open_ = as_float(row.get("open"))
            high = as_float(row.get("high"))
            low = as_float(row.get("low"))
            close = as_float(row.get("close"))
            if min(open_, high, low, close) <= 0:
                continue
            yield {
                "symbol": symbol,
                "exchange": "",
                "instrument_type": "",
                "trade_date": trade_date,
                "open": open_,
                "high": high,
                "low": low,
                "close": close,
                "volume": as_int(row.get("volume")),
                "trading_money": round(as_float(row.get("vwap")) * as_float(row.get("volume")), 2),
                "trading_turnover": 0,
                "spread": round(close - open_, 6),
                "source": "yahoo_adjusted",
                "official_checked": 0,
                "official_match": 0,
                "quality_flags": "",
                "raw_json": json.dumps({"source_file": str(path), "factor": row.get("factor")}, ensure_ascii=False),
            }


def upsert(rows: list[dict[str, Any]]) -> int:
    if not rows:
        return 0
    sql = """
        INSERT INTO qd_tw_stock_daily_bars (
            symbol, exchange, instrument_type, trade_date, open, high, low, close, volume,
            trading_money, trading_turnover, spread, source, official_checked, official_match,
            quality_flags, raw_json, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?::jsonb, NOW())
        ON CONFLICT (symbol, trade_date, source) DO UPDATE SET
            open = EXCLUDED.open,
            high = EXCLUDED.high,
            low = EXCLUDED.low,
            close = EXCLUDED.close,
            volume = EXCLUDED.volume,
            trading_money = EXCLUDED.trading_money,
            trading_turnover = EXCLUDED.trading_turnover,
            spread = EXCLUDED.spread,
            quality_flags = EXCLUDED.quality_flags,
            raw_json = EXCLUDED.raw_json,
            updated_at = NOW()
    """
    with get_db_connection() as db:
        cur = db.cursor()
        for row in rows:
            cur.execute(sql, (
                row["symbol"], row["exchange"], row["instrument_type"], row["trade_date"],
                row["open"], row["high"], row["low"], row["close"], row["volume"],
                row["trading_money"], row["trading_turnover"], row["spread"], row["source"],
                row["official_checked"], row["official_match"], row["quality_flags"], row["raw_json"],
            ))
        cur.close()
        db.commit()
    return len(rows)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Import local Yahoo adjusted normalized TWStock CSVs into qd_tw_stock_daily_bars.")
    parser.add_argument("--symbol", action="append", default=[])
    parser.add_argument("--symbols-file", default="")
    parser.add_argument("--normalized-dir", default=str(DEFAULT_NORMALIZED_DIR))
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)

    symbols = parse_symbols(args.symbol)
    symbols.extend(sym for sym in load_symbols_from_file(args.symbols_file) if sym not in symbols)
    normalized_dir = Path(args.normalized_dir)
    rows: list[dict[str, Any]] = []
    missing: list[str] = []
    per_symbol: list[dict[str, Any]] = []
    for symbol in symbols:
        path = normalized_dir / f"TW{symbol}.csv"
        if not path.exists():
            missing.append(symbol)
            per_symbol.append({"symbol": symbol, "rows": 0, "missing_file": True})
            continue
        symbol_rows = list(iter_rows(path, symbol=symbol, start=args.start, end=args.end))
        rows.extend(symbol_rows)
        per_symbol.append({"symbol": symbol, "rows": len(symbol_rows), "date_min": min((r["trade_date"] for r in symbol_rows), default=None), "date_max": max((r["trade_date"] for r in symbol_rows), default=None)})
    written = upsert(rows) if args.apply else 0
    report = {
        "ok": bool(rows),
        "apply": bool(args.apply),
        "source": "yahoo_adjusted",
        "symbols": symbols,
        "symbol_count": len(symbols),
        "row_count": len(rows),
        "written_count": written,
        "missing_symbols": missing,
        "per_symbol_sample": per_symbol[:20],
        "start": args.start,
        "end": args.end,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if rows else 2


if __name__ == "__main__":
    raise SystemExit(main())
