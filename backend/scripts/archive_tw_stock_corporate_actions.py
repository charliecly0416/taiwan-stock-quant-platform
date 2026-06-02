#!/usr/bin/env python3
"""Archive Taiwan stock dividend/ex-right actions into PostgreSQL.

Dry-run by default. The data source is FinMind TaiwanStockDividendResult, which
contains the exchange-published ex-dividend/ex-right reference prices used to
build adjustment factors for research.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict, dataclass
from datetime import date, timedelta
from typing import Any, Dict, Iterable, List, Optional, Sequence

import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.setdefault("SECRET_KEY", "archive-tw-stock-corporate-actions")
os.environ.setdefault("ADMIN_USER", "archive")
os.environ.setdefault("ADMIN_PASSWORD", "archivepass")

from app.data_sources.tw_stock import FINMIND_BASE_URL, TWStockDataSource  # noqa: E402


@dataclass(frozen=True)
class CorporateActionRecord:
    symbol: str
    action_date: str
    action_type: str
    before_price: float
    after_price: float
    cash_or_stock_dividend: float
    adjustment_factor: float
    source: str
    quality_flags: str
    raw_json: str


def _num(value: Any) -> float:
    text = str(value or "").replace(",", "").strip()
    if text in ("", "--", "-"):
        return 0.0
    return float(text)


def validate_action(record: CorporateActionRecord) -> List[str]:
    flags: List[str] = []
    if record.before_price <= 0 or record.after_price <= 0:
        flags.append("non_positive_reference_price")
    if record.adjustment_factor <= 0:
        flags.append("non_positive_adjustment_factor")
    if not record.action_date:
        flags.append("missing_action_date")
    return flags


def parse_finmind_rows(rows: Iterable[Dict[str, Any]], *, symbol: str) -> List[CorporateActionRecord]:
    norm = TWStockDataSource.normalize_symbol(symbol)
    fallback_symbol = norm.symbol or str(symbol or "").strip().upper()
    out: List[CorporateActionRecord] = []
    seen = set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        row_symbol = TWStockDataSource.normalize_symbol(row.get("stock_id") or fallback_symbol).symbol or fallback_symbol
        action_date = str(row.get("date") or "").strip()
        key = (row_symbol, action_date)
        if not row_symbol or not action_date or key in seen:
            continue
        seen.add(key)
        before_price = _num(row.get("before_price"))
        after_price = _num(row.get("after_price"))
        factor = after_price / before_price if before_price > 0 and after_price > 0 else 0.0
        record = CorporateActionRecord(
            symbol=row_symbol,
            action_date=action_date,
            action_type=str(row.get("stock_or_cache_dividend") or "").strip(),
            before_price=round(before_price, 6),
            after_price=round(after_price, 6),
            cash_or_stock_dividend=round(_num(row.get("stock_and_cache_dividend")), 6),
            adjustment_factor=round(factor, 12),
            source="finmind",
            quality_flags="",
            raw_json=json.dumps(row, ensure_ascii=False, separators=(",", ":")),
        )
        flags = validate_action(record)
        if flags:
            record = CorporateActionRecord(**{**asdict(record), "quality_flags": ",".join(flags)})
        out.append(record)
    out.sort(key=lambda item: item.action_date)
    return out


def fetch_finmind_rows(symbol: str, start: str, end: str, *, base_url: str = FINMIND_BASE_URL, timeout: int = 20) -> List[Dict[str, Any]]:
    params: Dict[str, Any] = {
        "dataset": "TaiwanStockDividendResult",
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


def archive_symbols(symbols: Sequence[str], start: str, end: str) -> List[CorporateActionRecord]:
    records: List[CorporateActionRecord] = []
    for symbol in symbols:
        records.extend(parse_finmind_rows(fetch_finmind_rows(symbol, start, end), symbol=symbol))
    return records


def upsert_records(records: Sequence[CorporateActionRecord]) -> int:
    from app.utils.db import get_db_connection  # noqa: WPS433

    if not records:
        return 0
    with get_db_connection() as db:
        cur = db.cursor()
        for item in records:
            cur.execute(
                """
                INSERT INTO qd_tw_stock_corporate_actions (
                    symbol, action_date, action_type, before_price, after_price,
                    cash_or_stock_dividend, adjustment_factor, source,
                    quality_flags, raw_json, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?::jsonb, NOW())
                ON CONFLICT (symbol, action_date, source) DO UPDATE SET
                    action_type = EXCLUDED.action_type,
                    before_price = EXCLUDED.before_price,
                    after_price = EXCLUDED.after_price,
                    cash_or_stock_dividend = EXCLUDED.cash_or_stock_dividend,
                    adjustment_factor = EXCLUDED.adjustment_factor,
                    quality_flags = EXCLUDED.quality_flags,
                    raw_json = EXCLUDED.raw_json,
                    updated_at = NOW()
                """,
                (
                    item.symbol,
                    item.action_date,
                    item.action_type,
                    item.before_price,
                    item.after_price,
                    item.cash_or_stock_dividend,
                    item.adjustment_factor,
                    item.source,
                    item.quality_flags,
                    item.raw_json,
                ),
            )
        db.commit()
        cur.close()
    return len(records)


def summarize(records: Sequence[CorporateActionRecord]) -> Dict[str, Any]:
    flagged = [item for item in records if item.quality_flags]
    return {
        "count": len(records),
        "symbols": sorted({item.symbol for item in records}),
        "date_min": min((item.action_date for item in records), default=None),
        "date_max": max((item.action_date for item in records), default=None),
        "flagged_count": len(flagged),
        "sample": [asdict(item) for item in records[:5]],
    }


def _default_start() -> str:
    return (date.today() - timedelta(days=365 * 5)).isoformat()


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Archive TWStock corporate actions into PostgreSQL.")
    parser.add_argument("--symbol", action="append", default=[], help="Taiwan stock code. Can be repeated.")
    parser.add_argument("--start", default=_default_start(), help="Start date YYYY-MM-DD. Default: today-5y.")
    parser.add_argument("--end", default=date.today().isoformat(), help="End date YYYY-MM-DD. Default: today.")
    parser.add_argument("--apply", action="store_true", help="Write parsed corporate actions to qd_tw_stock_corporate_actions.")
    parser.add_argument("--dry-run", action="store_true", help="Fetch and validate only; do not write DB.")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_arg_parser().parse_args(argv)
    symbols = [s.strip() for s in args.symbol if s and s.strip()] or ["2330", "0050"]
    records = archive_symbols(symbols, args.start, args.end)
    print(json.dumps(summarize(records), ensure_ascii=False, indent=2))
    if args.apply and not args.dry_run:
        print(f"applied={upsert_records(records)}")
    else:
        print("dry_run=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
