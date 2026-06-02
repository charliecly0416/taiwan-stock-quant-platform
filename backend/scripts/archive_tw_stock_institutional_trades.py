#!/usr/bin/env python3
"""Archive Taiwan institutional buy/sell data into PostgreSQL.

Dry-run by default. Source dataset is FinMind
TaiwanStockInstitutionalInvestorsBuySell. One output record is aggregated per
symbol/date, preserving raw rows for audit.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict, dataclass
from datetime import date, timedelta
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.setdefault("SECRET_KEY", "archive-tw-stock-institutional-trades")
os.environ.setdefault("ADMIN_USER", "archive")
os.environ.setdefault("ADMIN_PASSWORD", "archivepass")

from app.data_sources.tw_stock import FINMIND_BASE_URL, TWStockDataSource  # noqa: E402

DATASET = "TaiwanStockInstitutionalInvestorsBuySell"
CATEGORY_MAP = {
    "Foreign_Investor": "foreign",
    "Foreign_Dealer_Self": "foreign",
    "Investment_Trust": "investment_trust",
    "Dealer_self": "dealer_self",
    "Dealer_Hedging": "dealer_hedging",
}


@dataclass(frozen=True)
class InstitutionalTradeRecord:
    symbol: str
    trade_date: str
    foreign_buy: int
    foreign_sell: int
    foreign_net_buy: int
    investment_trust_buy: int
    investment_trust_sell: int
    investment_trust_net_buy: int
    dealer_self_buy: int
    dealer_self_sell: int
    dealer_self_net_buy: int
    dealer_hedging_buy: int
    dealer_hedging_sell: int
    dealer_hedging_net_buy: int
    dealer_net_buy: int
    total_institutional_net_buy: int
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


def _empty_bucket() -> Dict[str, int]:
    return {
        "foreign_buy": 0,
        "foreign_sell": 0,
        "investment_trust_buy": 0,
        "investment_trust_sell": 0,
        "dealer_self_buy": 0,
        "dealer_self_sell": 0,
        "dealer_hedging_buy": 0,
        "dealer_hedging_sell": 0,
    }


def validate_record(record: InstitutionalTradeRecord) -> List[str]:
    flags: List[str] = []
    numeric_fields = [
        "foreign_buy",
        "foreign_sell",
        "investment_trust_buy",
        "investment_trust_sell",
        "dealer_self_buy",
        "dealer_self_sell",
        "dealer_hedging_buy",
        "dealer_hedging_sell",
    ]
    for field in numeric_fields:
        if getattr(record, field) < 0:
            flags.append(f"negative_{field}")
    if not record.trade_date:
        flags.append("missing_trade_date")
    return flags


def parse_finmind_rows(rows: Iterable[Dict[str, Any]], *, symbol: str) -> List[InstitutionalTradeRecord]:
    norm = TWStockDataSource.normalize_symbol(symbol)
    fallback_symbol = norm.symbol or str(symbol or "").strip().upper()
    grouped: Dict[Tuple[str, str], Dict[str, Any]] = {}
    unknown_categories = set()

    for row in rows:
        if not isinstance(row, dict):
            continue
        row_symbol = TWStockDataSource.normalize_symbol(row.get("stock_id") or fallback_symbol).symbol or fallback_symbol
        trade_date = str(row.get("date") or "").strip()
        if not row_symbol or not trade_date:
            continue
        key = (row_symbol, trade_date)
        bucket = grouped.setdefault(key, {**_empty_bucket(), "raw_rows": []})
        bucket["raw_rows"].append(row)
        category = CATEGORY_MAP.get(str(row.get("name") or "").strip())
        if not category:
            unknown_categories.add(str(row.get("name") or "").strip() or "unknown")
            continue
        buy = _int_num(row.get("buy"))
        sell = _int_num(row.get("sell"))
        bucket[f"{category}_buy"] += buy
        bucket[f"{category}_sell"] += sell

    records: List[InstitutionalTradeRecord] = []
    for (row_symbol, trade_date), bucket in grouped.items():
        foreign_net = bucket["foreign_buy"] - bucket["foreign_sell"]
        trust_net = bucket["investment_trust_buy"] - bucket["investment_trust_sell"]
        dealer_self_net = bucket["dealer_self_buy"] - bucket["dealer_self_sell"]
        dealer_hedging_net = bucket["dealer_hedging_buy"] - bucket["dealer_hedging_sell"]
        dealer_net = dealer_self_net + dealer_hedging_net
        total_net = foreign_net + trust_net + dealer_net
        flags: List[str] = []
        if unknown_categories:
            flags.append("unknown_category")
        record = InstitutionalTradeRecord(
            symbol=row_symbol,
            trade_date=trade_date,
            foreign_buy=bucket["foreign_buy"],
            foreign_sell=bucket["foreign_sell"],
            foreign_net_buy=foreign_net,
            investment_trust_buy=bucket["investment_trust_buy"],
            investment_trust_sell=bucket["investment_trust_sell"],
            investment_trust_net_buy=trust_net,
            dealer_self_buy=bucket["dealer_self_buy"],
            dealer_self_sell=bucket["dealer_self_sell"],
            dealer_self_net_buy=dealer_self_net,
            dealer_hedging_buy=bucket["dealer_hedging_buy"],
            dealer_hedging_sell=bucket["dealer_hedging_sell"],
            dealer_hedging_net_buy=dealer_hedging_net,
            dealer_net_buy=dealer_net,
            total_institutional_net_buy=total_net,
            source="finmind",
            quality_flags=",".join(flags),
            raw_json=json.dumps(bucket["raw_rows"], ensure_ascii=False, separators=(",", ":")),
        )
        record_flags = validate_record(record)
        if record_flags:
            merged = [f for f in (record.quality_flags.split(",") if record.quality_flags else []) if f]
            merged.extend(record_flags)
            record = InstitutionalTradeRecord(**{**asdict(record), "quality_flags": ",".join(sorted(set(merged)))})
        records.append(record)
    records.sort(key=lambda item: (item.symbol, item.trade_date))
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


def archive_symbols(symbols: Sequence[str], start: str, end: str) -> List[InstitutionalTradeRecord]:
    records: List[InstitutionalTradeRecord] = []
    for symbol in symbols:
        rows = fetch_finmind_rows(symbol, start, end)
        records.extend(parse_finmind_rows(rows, symbol=symbol))
    return records


def upsert_records(records: Sequence[InstitutionalTradeRecord]) -> int:
    from app.utils.db import get_db_connection  # noqa: WPS433

    if not records:
        return 0
    with get_db_connection() as db:
        cur = db.cursor()
        for item in records:
            cur.execute(
                """
                INSERT INTO qd_tw_stock_institutional_trades (
                    symbol, trade_date,
                    foreign_buy, foreign_sell, foreign_net_buy,
                    investment_trust_buy, investment_trust_sell, investment_trust_net_buy,
                    dealer_self_buy, dealer_self_sell, dealer_self_net_buy,
                    dealer_hedging_buy, dealer_hedging_sell, dealer_hedging_net_buy,
                    dealer_net_buy, total_institutional_net_buy,
                    source, quality_flags, raw_json, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?::jsonb, NOW())
                ON CONFLICT (symbol, trade_date, source) DO UPDATE SET
                    foreign_buy = EXCLUDED.foreign_buy,
                    foreign_sell = EXCLUDED.foreign_sell,
                    foreign_net_buy = EXCLUDED.foreign_net_buy,
                    investment_trust_buy = EXCLUDED.investment_trust_buy,
                    investment_trust_sell = EXCLUDED.investment_trust_sell,
                    investment_trust_net_buy = EXCLUDED.investment_trust_net_buy,
                    dealer_self_buy = EXCLUDED.dealer_self_buy,
                    dealer_self_sell = EXCLUDED.dealer_self_sell,
                    dealer_self_net_buy = EXCLUDED.dealer_self_net_buy,
                    dealer_hedging_buy = EXCLUDED.dealer_hedging_buy,
                    dealer_hedging_sell = EXCLUDED.dealer_hedging_sell,
                    dealer_hedging_net_buy = EXCLUDED.dealer_hedging_net_buy,
                    dealer_net_buy = EXCLUDED.dealer_net_buy,
                    total_institutional_net_buy = EXCLUDED.total_institutional_net_buy,
                    quality_flags = EXCLUDED.quality_flags,
                    raw_json = EXCLUDED.raw_json,
                    updated_at = NOW()
                """,
                (
                    item.symbol,
                    item.trade_date,
                    item.foreign_buy,
                    item.foreign_sell,
                    item.foreign_net_buy,
                    item.investment_trust_buy,
                    item.investment_trust_sell,
                    item.investment_trust_net_buy,
                    item.dealer_self_buy,
                    item.dealer_self_sell,
                    item.dealer_self_net_buy,
                    item.dealer_hedging_buy,
                    item.dealer_hedging_sell,
                    item.dealer_hedging_net_buy,
                    item.dealer_net_buy,
                    item.total_institutional_net_buy,
                    item.source,
                    item.quality_flags,
                    item.raw_json,
                ),
            )
        db.commit()
        cur.close()
    return len(records)


def summarize(records: Sequence[InstitutionalTradeRecord]) -> Dict[str, Any]:
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
    parser = argparse.ArgumentParser(description="Archive TWStock institutional buy/sell data into PostgreSQL.")
    parser.add_argument("--symbol", action="append", default=[], help="Taiwan stock code. Can be repeated.")
    parser.add_argument("--start", default=_default_start(), help="Start date YYYY-MM-DD. Default: today-14d.")
    parser.add_argument("--end", default=date.today().isoformat(), help="End date YYYY-MM-DD. Default: today.")
    parser.add_argument("--apply", action="store_true", help="Write parsed institutional trades to qd_tw_stock_institutional_trades.")
    parser.add_argument("--dry-run", action="store_true", help="Fetch and validate only; do not write DB.")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_arg_parser().parse_args(argv)
    symbols = [s.strip() for s in args.symbol if s and s.strip()] or ["2330", "0050"]
    records = archive_symbols(symbols, args.start, args.end)
    print(json.dumps(summarize(records), ensure_ascii=False, indent=2))
    if not records:
        print("ERROR: no TWStock institutional trade records parsed")
        return 2
    if args.apply and not args.dry_run:
        print(f"applied={upsert_records(records)}")
    else:
        print("dry_run=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
