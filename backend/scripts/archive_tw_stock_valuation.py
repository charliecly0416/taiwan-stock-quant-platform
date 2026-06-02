#!/usr/bin/env python3
"""Archive Taiwan daily valuation metrics into PostgreSQL.

Dry-run by default. Source dataset is FinMind TaiwanStockPER. It provides PER,
PBR and dividend_yield. Market cap is not part of this source.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta
from typing import Any, Dict, Iterable, List, Optional, Sequence

import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.setdefault("SECRET_KEY", "archive-tw-stock-valuation")
os.environ.setdefault("ADMIN_USER", "archive")
os.environ.setdefault("ADMIN_PASSWORD", "archivepass")

from app.data_sources.tw_stock import FINMIND_BASE_URL, TWStockDataSource  # noqa: E402

DATASET = "TaiwanStockPER"


@dataclass(frozen=True)
class ValuationRecord:
    symbol: str
    trade_date: str
    pe: Optional[float]
    pb: Optional[float]
    dividend_yield: Optional[float]
    source: str
    quality_flags: str
    raw_json: str


def _num_or_none(value: Any) -> Optional[float]:
    text = str(value or "").replace(",", "").strip()
    if text in ("", "--", "-", "nan", "None"):
        return None
    try:
        return float(text)
    except Exception:
        return None


def validate_record(record: ValuationRecord) -> List[str]:
    flags: List[str] = []
    try:
        datetime.strptime(record.trade_date, "%Y-%m-%d")
    except Exception:
        flags.append("bad_trade_date")
    for field in ("pe", "pb", "dividend_yield"):
        value = getattr(record, field)
        if value is not None and value < 0:
            flags.append(f"negative_{field}")
    if record.pe is None and record.pb is None and record.dividend_yield is None:
        flags.append("all_metrics_missing")
    return flags


def parse_finmind_rows(rows: Iterable[Dict[str, Any]], *, symbol: str) -> List[ValuationRecord]:
    norm = TWStockDataSource.normalize_symbol(symbol)
    fallback_symbol = norm.symbol or str(symbol or "").strip().upper()
    out: List[ValuationRecord] = []
    seen_dates = set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        trade_date = str(row.get("date") or "").strip()
        if not trade_date or trade_date in seen_dates:
            continue
        seen_dates.add(trade_date)
        row_symbol = TWStockDataSource.normalize_symbol(row.get("stock_id") or fallback_symbol).symbol or fallback_symbol
        record = ValuationRecord(
            symbol=row_symbol,
            trade_date=trade_date,
            pe=_num_or_none(row.get("PER")),
            pb=_num_or_none(row.get("PBR")),
            dividend_yield=_num_or_none(row.get("dividend_yield")),
            source="finmind",
            quality_flags="",
            raw_json=json.dumps(row, ensure_ascii=False, separators=(",", ":")),
        )
        flags = validate_record(record)
        if flags:
            record = ValuationRecord(**{**asdict(record), "quality_flags": ",".join(flags)})
        out.append(record)
    out.sort(key=lambda item: item.trade_date)
    return out


def fetch_finmind_rows(symbol: str, start: str, end: str, *, base_url: str = FINMIND_BASE_URL, timeout: int = 20) -> List[Dict[str, Any]]:
    params: Dict[str, Any] = {
        "dataset": DATASET,
        "data_id": TWStockDataSource.normalize_symbol(symbol).symbol or symbol,
        "start_date": start,
        "end_date": end,
    }
    token = os.getenv("FINMIND_TOKEN") or os.getenv("FINMIND_API_TOKEN")
    if token:
        params["token"] = token.strip()
    response = requests.get(base_url, params=params, timeout=timeout)
    response.raise_for_status()
    payload = response.json()
    if payload.get("status") not in (None, 200, "200", True):
        raise ValueError(f"FinMind returned non-ok status for {symbol}: {payload.get('status')}")
    data = payload.get("data") or []
    if not isinstance(data, list):
        raise ValueError(f"FinMind data must be a list for {symbol}")
    return data


def archive_symbols(symbols: Sequence[str], start: str, end: str) -> List[ValuationRecord]:
    records: List[ValuationRecord] = []
    for symbol in symbols:
        rows = fetch_finmind_rows(symbol, start, end)
        records.extend(parse_finmind_rows(rows, symbol=symbol))
    return records


def upsert_records(records: Sequence[ValuationRecord]) -> int:
    from app.utils.db import get_db_connection  # noqa: WPS433

    if not records:
        return 0
    with get_db_connection() as db:
        cur = db.cursor()
        for item in records:
            cur.execute(
                """
                INSERT INTO qd_tw_stock_valuation (
                    symbol, trade_date, pe, pb, dividend_yield,
                    source, quality_flags, raw_json, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?::jsonb, NOW())
                ON CONFLICT (symbol, trade_date, source) DO UPDATE SET
                    pe = EXCLUDED.pe,
                    pb = EXCLUDED.pb,
                    dividend_yield = EXCLUDED.dividend_yield,
                    quality_flags = EXCLUDED.quality_flags,
                    raw_json = EXCLUDED.raw_json,
                    updated_at = NOW()
                """,
                (
                    item.symbol,
                    item.trade_date,
                    item.pe,
                    item.pb,
                    item.dividend_yield,
                    item.source,
                    item.quality_flags,
                    item.raw_json,
                ),
            )
        db.commit()
        cur.close()
    return len(records)


def summarize(records: Sequence[ValuationRecord]) -> Dict[str, Any]:
    flagged = [item for item in records if item.quality_flags]
    return {
        "count": len(records),
        "symbols": sorted({item.symbol for item in records}),
        "date_min": min((item.trade_date for item in records), default=None),
        "date_max": max((item.trade_date for item in records), default=None),
        "flagged_count": len(flagged),
        "sample": [asdict(item) for item in records[:5]],
    }


def _default_start() -> str:
    return (date.today() - timedelta(days=45)).isoformat()


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Archive TWStock valuation metrics into PostgreSQL.")
    parser.add_argument("--symbol", action="append", default=[], help="Taiwan stock code. Can be repeated.")
    parser.add_argument("--start", default=_default_start(), help="Start date YYYY-MM-DD. Default: today-45d.")
    parser.add_argument("--end", default=date.today().isoformat(), help="End date YYYY-MM-DD. Default: today.")
    parser.add_argument("--apply", action="store_true", help="Write parsed valuation metrics to qd_tw_stock_valuation.")
    parser.add_argument("--dry-run", action="store_true", help="Fetch and validate only; do not write DB.")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_arg_parser().parse_args(argv)
    symbols = [s.strip() for s in args.symbol if s and s.strip()] or ["2330", "2317"]
    records = archive_symbols(symbols, args.start, args.end)
    print(json.dumps(summarize(records), ensure_ascii=False, indent=2))
    if not records:
        print("ERROR: no TWStock valuation records parsed")
        return 2
    if args.apply and not args.dry_run:
        print(f"applied={upsert_records(records)}")
    else:
        print("dry_run=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
