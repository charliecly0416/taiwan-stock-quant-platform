#!/usr/bin/env python3
"""Archive Taiwan margin purchase / short sale data into PostgreSQL.

Dry-run by default. Source dataset is FinMind TaiwanStockMarginPurchaseShortSale.
Source units are preserved without converting board lots to shares.
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

os.environ.setdefault("SECRET_KEY", "archive-tw-stock-margin-trading")
os.environ.setdefault("ADMIN_USER", "archive")
os.environ.setdefault("ADMIN_PASSWORD", "archivepass")

from app.data_sources.tw_stock import FINMIND_BASE_URL, TWStockDataSource  # noqa: E402

DATASET = "TaiwanStockMarginPurchaseShortSale"


@dataclass(frozen=True)
class MarginTradingRecord:
    symbol: str
    trade_date: str
    margin_purchase_buy: int
    margin_purchase_sell: int
    margin_purchase_cash_repayment: int
    margin_purchase_yesterday_balance: int
    margin_purchase_today_balance: int
    margin_purchase_limit: int
    short_sale_buy: int
    short_sale_sell: int
    short_sale_cash_repayment: int
    short_sale_yesterday_balance: int
    short_sale_today_balance: int
    short_sale_limit: int
    offset_loan_and_short: int
    note: str
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


def validate_record(record: MarginTradingRecord) -> List[str]:
    flags: List[str] = []
    numeric_fields = [
        "margin_purchase_buy",
        "margin_purchase_sell",
        "margin_purchase_cash_repayment",
        "margin_purchase_yesterday_balance",
        "margin_purchase_today_balance",
        "margin_purchase_limit",
        "short_sale_buy",
        "short_sale_sell",
        "short_sale_cash_repayment",
        "short_sale_yesterday_balance",
        "short_sale_today_balance",
        "short_sale_limit",
        "offset_loan_and_short",
    ]
    for field in numeric_fields:
        if getattr(record, field) < 0:
            flags.append(f"negative_{field}")
    try:
        datetime.strptime(record.trade_date, "%Y-%m-%d")
    except Exception:
        flags.append("bad_trade_date")
    return flags


def parse_finmind_rows(rows: Iterable[Dict[str, Any]], *, symbol: str) -> List[MarginTradingRecord]:
    norm = TWStockDataSource.normalize_symbol(symbol)
    fallback_symbol = norm.symbol or str(symbol or "").strip().upper()
    out: List[MarginTradingRecord] = []
    seen_dates = set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        trade_date = str(row.get("date") or "").strip()
        if not trade_date or trade_date in seen_dates:
            continue
        seen_dates.add(trade_date)
        row_symbol = TWStockDataSource.normalize_symbol(row.get("stock_id") or fallback_symbol).symbol or fallback_symbol
        record = MarginTradingRecord(
            symbol=row_symbol,
            trade_date=trade_date,
            margin_purchase_buy=_int_num(row.get("MarginPurchaseBuy")),
            margin_purchase_sell=_int_num(row.get("MarginPurchaseSell")),
            margin_purchase_cash_repayment=_int_num(row.get("MarginPurchaseCashRepayment")),
            margin_purchase_yesterday_balance=_int_num(row.get("MarginPurchaseYesterdayBalance")),
            margin_purchase_today_balance=_int_num(row.get("MarginPurchaseTodayBalance")),
            margin_purchase_limit=_int_num(row.get("MarginPurchaseLimit")),
            short_sale_buy=_int_num(row.get("ShortSaleBuy")),
            short_sale_sell=_int_num(row.get("ShortSaleSell")),
            short_sale_cash_repayment=_int_num(row.get("ShortSaleCashRepayment")),
            short_sale_yesterday_balance=_int_num(row.get("ShortSaleYesterdayBalance")),
            short_sale_today_balance=_int_num(row.get("ShortSaleTodayBalance")),
            short_sale_limit=_int_num(row.get("ShortSaleLimit")),
            offset_loan_and_short=_int_num(row.get("OffsetLoanAndShort")),
            note=str(row.get("Note") or "").strip(),
            source="finmind",
            quality_flags="",
            raw_json=json.dumps(row, ensure_ascii=False, separators=(",", ":")),
        )
        flags = validate_record(record)
        if flags:
            record = MarginTradingRecord(**{**asdict(record), "quality_flags": ",".join(flags)})
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


def archive_symbols(symbols: Sequence[str], start: str, end: str) -> List[MarginTradingRecord]:
    records: List[MarginTradingRecord] = []
    for symbol in symbols:
        rows = fetch_finmind_rows(symbol, start, end)
        records.extend(parse_finmind_rows(rows, symbol=symbol))
    return records


def upsert_records(records: Sequence[MarginTradingRecord]) -> int:
    from app.utils.db import get_db_connection  # noqa: WPS433

    if not records:
        return 0
    with get_db_connection() as db:
        cur = db.cursor()
        for item in records:
            cur.execute(
                """
                INSERT INTO qd_tw_stock_margin_trading (
                    symbol, trade_date,
                    margin_purchase_buy, margin_purchase_sell, margin_purchase_cash_repayment,
                    margin_purchase_yesterday_balance, margin_purchase_today_balance, margin_purchase_limit,
                    short_sale_buy, short_sale_sell, short_sale_cash_repayment,
                    short_sale_yesterday_balance, short_sale_today_balance, short_sale_limit,
                    offset_loan_and_short, note,
                    source, quality_flags, raw_json, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?::jsonb, NOW())
                ON CONFLICT (symbol, trade_date, source) DO UPDATE SET
                    margin_purchase_buy = EXCLUDED.margin_purchase_buy,
                    margin_purchase_sell = EXCLUDED.margin_purchase_sell,
                    margin_purchase_cash_repayment = EXCLUDED.margin_purchase_cash_repayment,
                    margin_purchase_yesterday_balance = EXCLUDED.margin_purchase_yesterday_balance,
                    margin_purchase_today_balance = EXCLUDED.margin_purchase_today_balance,
                    margin_purchase_limit = EXCLUDED.margin_purchase_limit,
                    short_sale_buy = EXCLUDED.short_sale_buy,
                    short_sale_sell = EXCLUDED.short_sale_sell,
                    short_sale_cash_repayment = EXCLUDED.short_sale_cash_repayment,
                    short_sale_yesterday_balance = EXCLUDED.short_sale_yesterday_balance,
                    short_sale_today_balance = EXCLUDED.short_sale_today_balance,
                    short_sale_limit = EXCLUDED.short_sale_limit,
                    offset_loan_and_short = EXCLUDED.offset_loan_and_short,
                    note = EXCLUDED.note,
                    quality_flags = EXCLUDED.quality_flags,
                    raw_json = EXCLUDED.raw_json,
                    updated_at = NOW()
                """,
                (
                    item.symbol,
                    item.trade_date,
                    item.margin_purchase_buy,
                    item.margin_purchase_sell,
                    item.margin_purchase_cash_repayment,
                    item.margin_purchase_yesterday_balance,
                    item.margin_purchase_today_balance,
                    item.margin_purchase_limit,
                    item.short_sale_buy,
                    item.short_sale_sell,
                    item.short_sale_cash_repayment,
                    item.short_sale_yesterday_balance,
                    item.short_sale_today_balance,
                    item.short_sale_limit,
                    item.offset_loan_and_short,
                    item.note,
                    item.source,
                    item.quality_flags,
                    item.raw_json,
                ),
            )
        db.commit()
        cur.close()
    return len(records)


def summarize(records: Sequence[MarginTradingRecord]) -> Dict[str, Any]:
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
    return (date.today() - timedelta(days=14)).isoformat()


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Archive TWStock margin trading data into PostgreSQL.")
    parser.add_argument("--symbol", action="append", default=[], help="Taiwan stock code. Can be repeated.")
    parser.add_argument("--start", default=_default_start(), help="Start date YYYY-MM-DD. Default: today-14d.")
    parser.add_argument("--end", default=date.today().isoformat(), help="End date YYYY-MM-DD. Default: today.")
    parser.add_argument("--apply", action="store_true", help="Write parsed margin trading data to qd_tw_stock_margin_trading.")
    parser.add_argument("--dry-run", action="store_true", help="Fetch and validate only; do not write DB.")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_arg_parser().parse_args(argv)
    symbols = [s.strip() for s in args.symbol if s and s.strip()] or ["2330", "0050"]
    records = archive_symbols(symbols, args.start, args.end)
    print(json.dumps(summarize(records), ensure_ascii=False, indent=2))
    if not records:
        print("ERROR: no TWStock margin trading records parsed")
        return 2
    if args.apply and not args.dry_run:
        print(f"applied={upsert_records(records)}")
    else:
        print("dry_run=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
