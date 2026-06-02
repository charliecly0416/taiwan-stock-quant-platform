#!/usr/bin/env python3
"""Archive Taiwan monthly revenue data into PostgreSQL.

Dry-run by default. Source dataset is FinMind TaiwanStockMonthRevenue. MoM and
YoY growth are derived from the parsed monthly revenue series per symbol.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.setdefault("SECRET_KEY", "archive-tw-stock-monthly-revenue")
os.environ.setdefault("ADMIN_USER", "archive")
os.environ.setdefault("ADMIN_PASSWORD", "archivepass")

from app.data_sources.tw_stock import FINMIND_BASE_URL, TWStockDataSource  # noqa: E402

DATASET = "TaiwanStockMonthRevenue"


@dataclass(frozen=True)
class MonthlyRevenueRecord:
    symbol: str
    report_date: str
    revenue_year: int
    revenue_month: int
    revenue_period: str
    monthly_revenue: int
    mom_growth: Optional[float]
    yoy_growth: Optional[float]
    country: str
    create_time: str
    source: str
    quality_flags: str
    raw_json: str


def _num(value: Any) -> float:
    text = str(value or "").replace(",", "").strip()
    if text in ("", "--", "-"):
        return 0.0
    return float(text)


def _int_num(value: Any) -> int:
    return int(round(_num(value)))


def _pct_change(current: int, previous: Optional[int]) -> Optional[float]:
    if previous in (None, 0):
        return None
    return round((float(current) - float(previous)) / abs(float(previous)) * 100.0, 8)


def _period(year: int, month: int) -> str:
    return f"{year:04d}-{month:02d}"


def validate_record(record: MonthlyRevenueRecord) -> List[str]:
    flags: List[str] = []
    if record.monthly_revenue < 0:
        flags.append("negative_revenue")
    if record.revenue_month < 1 or record.revenue_month > 12:
        flags.append("bad_revenue_month")
    try:
        datetime.strptime(record.report_date, "%Y-%m-%d")
    except Exception:
        flags.append("bad_report_date")
    return flags


def parse_finmind_rows(rows: Iterable[Dict[str, Any]], *, symbol: str) -> List[MonthlyRevenueRecord]:
    norm = TWStockDataSource.normalize_symbol(symbol)
    fallback_symbol = norm.symbol or str(symbol or "").strip().upper()
    base_rows: List[Tuple[str, str, Dict[str, Any], int, int, int]] = []
    seen = set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        row_symbol = TWStockDataSource.normalize_symbol(row.get("stock_id") or fallback_symbol).symbol or fallback_symbol
        revenue_year = _int_num(row.get("revenue_year"))
        revenue_month = _int_num(row.get("revenue_month"))
        revenue_period = _period(revenue_year, revenue_month) if revenue_year and revenue_month else ""
        key = (row_symbol, revenue_period)
        if not row_symbol or not revenue_period or key in seen:
            continue
        seen.add(key)
        base_rows.append((row_symbol, revenue_period, row, revenue_year, revenue_month, _int_num(row.get("revenue"))))
    base_rows.sort(key=lambda item: (item[0], item[1]))

    revenue_by_symbol_period: Dict[Tuple[str, str], int] = {(sym, period): revenue for sym, period, _row, _year, _month, revenue in base_rows}
    records: List[MonthlyRevenueRecord] = []
    for row_symbol, revenue_period, row, revenue_year, revenue_month, revenue in base_rows:
        prev_month = revenue_month - 1
        prev_year = revenue_year
        if prev_month <= 0:
            prev_month = 12
            prev_year -= 1
        mom = _pct_change(revenue, revenue_by_symbol_period.get((row_symbol, _period(prev_year, prev_month))))
        yoy = _pct_change(revenue, revenue_by_symbol_period.get((row_symbol, _period(revenue_year - 1, revenue_month))))
        record = MonthlyRevenueRecord(
            symbol=row_symbol,
            report_date=str(row.get("date") or "").strip(),
            revenue_year=revenue_year,
            revenue_month=revenue_month,
            revenue_period=revenue_period,
            monthly_revenue=revenue,
            mom_growth=mom,
            yoy_growth=yoy,
            country=str(row.get("country") or "").strip(),
            create_time=str(row.get("create_time") or "").strip(),
            source="finmind",
            quality_flags="",
            raw_json=json.dumps(row, ensure_ascii=False, separators=(",", ":")),
        )
        flags = validate_record(record)
        if flags:
            record = MonthlyRevenueRecord(**{**asdict(record), "quality_flags": ",".join(flags)})
        records.append(record)
    return records


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


def archive_symbols(symbols: Sequence[str], start: str, end: str) -> List[MonthlyRevenueRecord]:
    records: List[MonthlyRevenueRecord] = []
    for symbol in symbols:
        rows = fetch_finmind_rows(symbol, start, end)
        records.extend(parse_finmind_rows(rows, symbol=symbol))
    return records


def upsert_records(records: Sequence[MonthlyRevenueRecord]) -> int:
    from app.utils.db import get_db_connection  # noqa: WPS433

    if not records:
        return 0
    with get_db_connection() as db:
        cur = db.cursor()
        for item in records:
            cur.execute(
                """
                INSERT INTO qd_tw_stock_monthly_revenue (
                    symbol, report_date, revenue_year, revenue_month, revenue_period,
                    monthly_revenue, mom_growth, yoy_growth,
                    country, create_time, source, quality_flags, raw_json, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?::jsonb, NOW())
                ON CONFLICT (symbol, revenue_period, source) DO UPDATE SET
                    report_date = EXCLUDED.report_date,
                    revenue_year = EXCLUDED.revenue_year,
                    revenue_month = EXCLUDED.revenue_month,
                    monthly_revenue = EXCLUDED.monthly_revenue,
                    mom_growth = EXCLUDED.mom_growth,
                    yoy_growth = EXCLUDED.yoy_growth,
                    country = EXCLUDED.country,
                    create_time = EXCLUDED.create_time,
                    quality_flags = EXCLUDED.quality_flags,
                    raw_json = EXCLUDED.raw_json,
                    updated_at = NOW()
                """,
                (
                    item.symbol,
                    item.report_date,
                    item.revenue_year,
                    item.revenue_month,
                    item.revenue_period,
                    item.monthly_revenue,
                    item.mom_growth,
                    item.yoy_growth,
                    item.country,
                    item.create_time,
                    item.source,
                    item.quality_flags,
                    item.raw_json,
                ),
            )
        db.commit()
        cur.close()
    return len(records)


def summarize(records: Sequence[MonthlyRevenueRecord]) -> Dict[str, Any]:
    flagged = [item for item in records if item.quality_flags]
    return {
        "count": len(records),
        "symbols": sorted({item.symbol for item in records}),
        "period_min": min((item.revenue_period for item in records), default=None),
        "period_max": max((item.revenue_period for item in records), default=None),
        "flagged_count": len(flagged),
        "sample": [asdict(item) for item in records[:5]],
    }


def _default_start() -> str:
    return (date.today() - timedelta(days=365 * 2)).isoformat()


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Archive TWStock monthly revenue into PostgreSQL.")
    parser.add_argument("--symbol", action="append", default=[], help="Taiwan stock code. Can be repeated.")
    parser.add_argument("--start", default=_default_start(), help="Start date YYYY-MM-DD. Default: today-2y.")
    parser.add_argument("--end", default=date.today().isoformat(), help="End date YYYY-MM-DD. Default: today.")
    parser.add_argument("--apply", action="store_true", help="Write parsed monthly revenue to qd_tw_stock_monthly_revenue.")
    parser.add_argument("--dry-run", action="store_true", help="Fetch and validate only; do not write DB.")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_arg_parser().parse_args(argv)
    symbols = [s.strip() for s in args.symbol if s and s.strip()] or ["2330", "2317"]
    records = archive_symbols(symbols, args.start, args.end)
    print(json.dumps(summarize(records), ensure_ascii=False, indent=2))
    if not records:
        print("ERROR: no TWStock monthly revenue records parsed")
        return 2
    if args.apply and not args.dry_run:
        print(f"applied={upsert_records(records)}")
    else:
        print("dry_run=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
