#!/usr/bin/env python3
"""Sync Taiwan listed stock/ETF symbols into qd_market_symbols.

Phase 1 intentionally starts with TWSE because its OpenAPI is reachable from
the current environment and can be cross-checked. TPEx support can reuse the
same parser/upsert path once its official endpoint is accessible.

Examples:
    python scripts/sync_tw_stock_symbols.py --dry-run
    python scripts/sync_tw_stock_symbols.py --apply
    python scripts/sync_tw_stock_symbols.py --source twse --limit 20 --dry-run
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence

import requests


sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.setdefault("SECRET_KEY", "sync-tw-stock-symbols")
os.environ.setdefault("ADMIN_USER", "sync")
os.environ.setdefault("ADMIN_PASSWORD", "syncpass")


TWSE_STOCK_DAY_ALL_URL = "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL"
MARKET = "TWStock"
TWD = "TWD"
DEFAULT_LOT_SIZE = 1000
DEFAULT_PRICE_TICK_META = {
    "source": "twse_default",
    "note": "Use official TWSE/TPEx tick-size table before live trading.",
}


@dataclass(frozen=True)
class TwSymbolRecord:
    market: str
    symbol: str
    name: str
    exchange: str
    currency: str
    is_active: int
    is_hot: int
    sort_order: int
    instrument_type: str
    lot_size: int
    price_tick_json: str


def _first_text(row: Dict[str, Any], keys: Sequence[str]) -> str:
    for key in keys:
        value = row.get(key)
        if value is not None:
            text = str(value).strip()
            if text and text != "--":
                return text
    return ""


def _to_number(value: Any) -> float:
    text = str(value or "").replace(",", "").strip()
    if text in ("", "--"):
        return 0.0
    return float(text)


def classify_tw_instrument(symbol: str, name: str) -> str:
    """Best-effort TWSE instrument classification for Phase 1.

    TWSE OpenAPI rows do not expose a normalized security type in
    STOCK_DAY_ALL. Code prefixes and product names are enough to distinguish
    the stock/ETF universe used by this phase; warrants and ETNs are excluded.
    """
    code = (symbol or "").strip()
    nm = (name or "").strip().upper()
    if not code:
        return "unknown"
    if "ETN" in nm:
        return "etn"
    if code.startswith(("00", "006", "007", "008", "009")):
        return "etf"
    if code.startswith(("03", "04", "05", "06", "07", "08", "09")):
        return "warrant"
    if len(code) == 4 and code.isdigit():
        return "stock"
    return "unknown"


def parse_twse_stock_day_all(rows: Iterable[Dict[str, Any]], *, include_non_stock_etf: bool = False) -> List[TwSymbolRecord]:
    records: List[TwSymbolRecord] = []
    for row in rows:
        symbol = _first_text(row, ("Code", "證券代號", "股票代號"))
        name = _first_text(row, ("Name", "證券名稱", "股票名稱"))
        if not symbol or not name:
            continue
        if not symbol.isdigit():
            continue

        instrument_type = classify_tw_instrument(symbol, name)
        if instrument_type not in ("stock", "etf") and not include_non_stock_etf:
            continue

        trade_volume = _to_number(_first_text(row, ("TradeVolume", "成交股數", "成交量")))
        sort_order = int(min(max(trade_volume, 0), 999_999_999))
        records.append(
            TwSymbolRecord(
                market=MARKET,
                symbol=symbol,
                name=name,
                exchange="TWSE",
                currency=TWD,
                is_active=1,
                is_hot=0,
                sort_order=sort_order,
                instrument_type=instrument_type,
                lot_size=DEFAULT_LOT_SIZE,
                price_tick_json=json.dumps(DEFAULT_PRICE_TICK_META, ensure_ascii=False, separators=(",", ":")),
            )
        )

    records.sort(key=lambda item: (item.instrument_type != "stock", item.symbol))
    return records


def fetch_twse_rows(url: str = TWSE_STOCK_DAY_ALL_URL, *, timeout: int = 20) -> List[Dict[str, Any]]:
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()
    data = response.json()
    if not isinstance(data, list):
        raise ValueError(f"TWSE response must be a list, got {type(data).__name__}")
    return data


def upsert_records(records: Sequence[TwSymbolRecord]) -> int:
    from app.utils.db import get_db_connection  # noqa: WPS433

    if not records:
        return 0

    with get_db_connection() as db:
        cur = db.cursor()
        for item in records:
            cur.execute(
                """
                INSERT INTO qd_market_symbols (
                    market, symbol, name, exchange, currency,
                    is_active, is_hot, sort_order,
                    instrument_type, lot_size, price_tick_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (market, symbol) DO UPDATE SET
                    name = EXCLUDED.name,
                    exchange = EXCLUDED.exchange,
                    currency = EXCLUDED.currency,
                    is_active = EXCLUDED.is_active,
                    sort_order = EXCLUDED.sort_order,
                    instrument_type = EXCLUDED.instrument_type,
                    lot_size = EXCLUDED.lot_size,
                    price_tick_json = CASE
                        WHEN qd_market_symbols.price_tick_json IS NULL
                          OR qd_market_symbols.price_tick_json = ''
                        THEN EXCLUDED.price_tick_json
                        ELSE qd_market_symbols.price_tick_json
                    END
                """,
                (
                    item.market,
                    item.symbol,
                    item.name,
                    item.exchange,
                    item.currency,
                    item.is_active,
                    item.is_hot,
                    item.sort_order,
                    item.instrument_type,
                    item.lot_size,
                    item.price_tick_json,
                ),
            )
        db.commit()
        cur.close()
    return len(records)


def summarize(records: Sequence[TwSymbolRecord]) -> Dict[str, Any]:
    by_type: Dict[str, int] = {}
    for item in records:
        by_type[item.instrument_type] = by_type.get(item.instrument_type, 0) + 1
    return {
        "count": len(records),
        "by_type": by_type,
        "first_symbols": [item.symbol for item in records[:10]],
        "sample": [
            {
                "symbol": item.symbol,
                "name": item.name,
                "exchange": item.exchange,
                "instrument_type": item.instrument_type,
                "lot_size": item.lot_size,
            }
            for item in records[:5]
        ],
    }


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Sync TWSE listed Taiwan stock/ETF symbols.")
    parser.add_argument("--source", choices=("twse",), default="twse")
    parser.add_argument("--apply", action="store_true", help="Write parsed symbols to qd_market_symbols.")
    parser.add_argument("--dry-run", action="store_true", help="Fetch and parse only; do not write the database.")
    parser.add_argument("--limit", type=int, default=0, help="Optional max records after parsing, useful for smoke tests.")
    parser.add_argument(
        "--include-non-stock-etf",
        action="store_true",
        help="Keep records classified as warrant/etn/unknown. Default only keeps stock and ETF.",
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_arg_parser().parse_args(argv)
    apply_changes = bool(args.apply)
    if args.dry_run:
        apply_changes = False

    rows = fetch_twse_rows()
    records = parse_twse_stock_day_all(rows, include_non_stock_etf=args.include_non_stock_etf)
    if args.limit and args.limit > 0:
        records = records[: args.limit]

    print(json.dumps(summarize(records), ensure_ascii=False, indent=2))
    if not records:
        print("ERROR: no TWSE stock/ETF symbols parsed")
        return 2

    if apply_changes:
        count = upsert_records(records)
        print(f"applied={count}")
    else:
        print("dry_run=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
