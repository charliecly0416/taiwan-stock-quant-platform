#!/usr/bin/env python3
"""Validate archived/FinMind Taiwan daily bars against TWSE official data.

Dry-run by default. With --apply, updates qd_tw_stock_daily_bars rows for the
official TWSE report date by setting official_checked/official_match and
appending quality flags when mismatches are found.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, Iterable, List, Optional, Sequence

import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.setdefault("SECRET_KEY", "validate-tw-stock-daily")
os.environ.setdefault("ADMIN_USER", "validate")
os.environ.setdefault("ADMIN_PASSWORD", "validatepass")

from app.data_sources.tw_stock import TAIPEI_TZ, TWStockDataSource  # noqa: E402
from scripts.archive_tw_stock_daily import DailyBarRecord, fetch_finmind_rows, parse_finmind_rows  # noqa: E402

TWSE_STOCK_DAY_ALL_URL = "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL"


@dataclass(frozen=True)
class OfficialTwseRow:
    symbol: str
    name: str
    trade_date: str
    close: float
    volume: int
    raw_json: str


@dataclass(frozen=True)
class ValidationResult:
    symbol: str
    trade_date: str
    source: str
    official_checked: int
    official_match: int
    quality_flags: str
    local_close: float
    official_close: float
    local_volume: int
    official_volume: int


def _num(value: Any) -> float:
    return float(str(value or "").replace(",", "").strip() or 0)


def _int_num(value: Any) -> int:
    return int(round(_num(value)))


def roc_yyyymmdd_to_iso(value: str) -> str:
    s = str(value or "").strip()
    if len(s) != 7 or not s.isdigit():
        raise ValueError(f"Unexpected ROC date: {value!r}")
    year = int(s[:3]) + 1911
    month = int(s[3:5])
    day = int(s[5:7])
    return f"{year:04d}-{month:02d}-{day:02d}"


def parse_twse_rows(rows: Iterable[Dict[str, Any]]) -> Dict[str, OfficialTwseRow]:
    out: Dict[str, OfficialTwseRow] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        symbol = str(row.get("Code") or row.get("證券代號") or "").strip()
        if not symbol:
            continue
        try:
            trade_date = roc_yyyymmdd_to_iso(str(row.get("Date") or row.get("日期") or ""))
            close = _num(row.get("ClosingPrice") or row.get("收盤價"))
            volume = _int_num(row.get("TradeVolume") or row.get("成交股數"))
        except Exception:
            continue
        out[symbol] = OfficialTwseRow(
            symbol=symbol,
            name=str(row.get("Name") or row.get("證券名稱") or "").strip(),
            trade_date=trade_date,
            close=close,
            volume=volume,
            raw_json=json.dumps(row, ensure_ascii=False, separators=(",", ":")),
        )
    return out


def fetch_twse_rows(url: str = TWSE_STOCK_DAY_ALL_URL, *, timeout: int = 20) -> Dict[str, OfficialTwseRow]:
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()
    data = response.json()
    if not isinstance(data, list):
        raise ValueError(f"TWSE response must be a list, got {type(data).__name__}")
    return parse_twse_rows(data)


def compare_record_to_official(record: DailyBarRecord, official: Optional[OfficialTwseRow]) -> ValidationResult:
    flags: List[str] = []
    official_checked = 1 if official else 0
    official_match = 0
    official_close = 0.0
    official_volume = 0
    if not official:
        flags.append("official_missing")
    else:
        official_close = official.close
        official_volume = official.volume
        if record.trade_date != official.trade_date:
            flags.append("date_mismatch")
        if abs(float(record.close) - float(official.close)) > 1e-9:
            flags.append("close_mismatch")
        if int(record.volume) != int(official.volume):
            flags.append("volume_mismatch")
        official_match = 1 if not flags else 0
    return ValidationResult(
        symbol=record.symbol,
        trade_date=record.trade_date,
        source=record.source,
        official_checked=official_checked,
        official_match=official_match,
        quality_flags=",".join(flags),
        local_close=float(record.close),
        official_close=float(official_close),
        local_volume=int(record.volume),
        official_volume=int(official_volume),
    )


def latest_records_by_symbol(records: Iterable[DailyBarRecord]) -> Dict[str, DailyBarRecord]:
    latest: Dict[str, DailyBarRecord] = {}
    for record in records:
        cur = latest.get(record.symbol)
        if cur is None or record.trade_date > cur.trade_date:
            latest[record.symbol] = record
    return latest


def load_latest_archived_records(symbols: Sequence[str], trade_date: str = "") -> List[DailyBarRecord]:
    from app.utils.db import get_db_connection  # noqa: WPS433

    if not symbols:
        return []
    placeholders = ",".join(["?"] * len(symbols))
    params: List[Any] = list(symbols)
    date_filter = ""
    if trade_date:
        date_filter = "AND trade_date = ?"
        params.append(trade_date)
    sql = f"""
        SELECT symbol, exchange, instrument_type, trade_date::text AS trade_date,
               open, high, low, close, volume, trading_money, trading_turnover,
               spread, source, official_checked, official_match,
               COALESCE(quality_flags, '') AS quality_flags,
               COALESCE(raw_json::text, '{{}}') AS raw_json
        FROM qd_tw_stock_daily_bars
        WHERE symbol IN ({placeholders}) {date_filter}
          AND source = 'finmind'
        ORDER BY symbol, trade_date DESC
    """
    rows: List[Dict[str, Any]] = []
    with get_db_connection() as db:
        cur = db.cursor()
        cur.execute(sql, tuple(params))
        rows = cur.fetchall() or []
        cur.close()
    latest: Dict[str, DailyBarRecord] = {}
    for row in rows:
        symbol = str(row.get("symbol") or "")
        if symbol in latest:
            continue
        latest[symbol] = DailyBarRecord(
            symbol=symbol,
            exchange=str(row.get("exchange") or ""),
            instrument_type=str(row.get("instrument_type") or ""),
            trade_date=str(row.get("trade_date") or ""),
            open=float(row.get("open") or 0),
            high=float(row.get("high") or 0),
            low=float(row.get("low") or 0),
            close=float(row.get("close") or 0),
            volume=int(row.get("volume") or 0),
            trading_money=float(row.get("trading_money") or 0),
            trading_turnover=int(row.get("trading_turnover") or 0),
            spread=float(row.get("spread") or 0),
            source=str(row.get("source") or "finmind"),
            official_checked=int(row.get("official_checked") or 0),
            official_match=int(row.get("official_match") or 0),
            quality_flags=str(row.get("quality_flags") or ""),
            raw_json=str(row.get("raw_json") or "{}"),
        )
    return list(latest.values())


def update_archive_validation(results: Sequence[ValidationResult]) -> int:
    from app.utils.db import get_db_connection  # noqa: WPS433

    if not results:
        return 0
    with get_db_connection() as db:
        cur = db.cursor()
        for item in results:
            cur.execute(
                """
                UPDATE qd_tw_stock_daily_bars
                SET official_checked = ?,
                    official_match = ?,
                    quality_flags = ?,
                    updated_at = NOW()
                WHERE symbol = ? AND trade_date = ? AND source = ?
                """,
                (
                    item.official_checked,
                    item.official_match,
                    item.quality_flags,
                    item.symbol,
                    item.trade_date,
                    item.source,
                ),
            )
        db.commit()
        cur.close()
    return len(results)


def fetch_latest_finmind_records(symbols: Sequence[str], trade_date: str = "") -> List[DailyBarRecord]:
    end_dt = datetime.now(TAIPEI_TZ).date()
    start_dt = end_dt - timedelta(days=14)
    records: List[DailyBarRecord] = []
    for symbol in symbols:
        rows = fetch_finmind_rows(symbol, start_dt.isoformat(), end_dt.isoformat())
        parsed = parse_finmind_rows(rows, symbol=symbol)
        if trade_date:
            parsed = [item for item in parsed if item.trade_date == trade_date]
        latest = latest_records_by_symbol(parsed).get(TWStockDataSource.normalize_symbol(symbol).symbol or symbol)
        if latest:
            records.append(latest)
    return records


def summarize(results: Sequence[ValidationResult]) -> Dict[str, Any]:
    return {
        "count": len(results),
        "matched": sum(1 for item in results if item.official_match),
        "mismatched": sum(1 for item in results if item.official_checked and not item.official_match),
        "unchecked": sum(1 for item in results if not item.official_checked),
        "sample": [asdict(item) for item in results[:10]],
    }


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate TWStock daily bars against TWSE official STOCK_DAY_ALL.")
    parser.add_argument("--symbol", action="append", default=[], help="Taiwan stock code. Can be repeated.")
    parser.add_argument("--source", choices=("finmind", "archive"), default="finmind", help="Compare latest FinMind records or archived DB records.")
    parser.add_argument("--date", default="", help="Optional official trade date YYYY-MM-DD.")
    parser.add_argument("--apply", action="store_true", help="Update qd_tw_stock_daily_bars validation fields.")
    parser.add_argument("--dry-run", action="store_true", help="Do not update DB.")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_arg_parser().parse_args(argv)
    symbols = [s.strip() for s in args.symbol if s and s.strip()] or ["2330", "0050", "0056", "00878"]
    official_by_symbol = fetch_twse_rows()
    official_date = args.date or next((row.trade_date for row in official_by_symbol.values()), "")
    if args.source == "archive":
        records = load_latest_archived_records(symbols, official_date)
    else:
        records = fetch_latest_finmind_records(symbols, official_date)
    latest = latest_records_by_symbol(records)
    results = [compare_record_to_official(latest.get(symbol), official_by_symbol.get(symbol)) for symbol in symbols if latest.get(symbol)]
    print(json.dumps(summarize(results), ensure_ascii=False, indent=2))
    if not results:
        print("ERROR: no records validated")
        return 2
    if args.apply and not args.dry_run:
        print(f"updated={update_archive_validation(results)}")
    else:
        print("dry_run=true")
    return 0 if all(item.official_match for item in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
