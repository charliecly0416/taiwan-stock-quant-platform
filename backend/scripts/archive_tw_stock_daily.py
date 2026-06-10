#!/usr/bin/env python3
"""Archive Taiwan stock daily bars into qd_tw_stock_daily_bars.

Phase 2 starts with a conservative FinMind -> PostgreSQL cache path. The script
is dry-run by default; use --apply to write. Official TWSE/TPEx reconciliation
is kept as a separate validation step so data can be archived even when TPEx is
blocked from the current network.

Examples:
    python scripts/archive_tw_stock_daily.py --symbol 2330 --start 2026-05-01 --end 2026-05-22
    python scripts/archive_tw_stock_daily.py --symbol 2330 --symbol 0050 --start 2026-05-01 --apply
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta
from typing import Any, Dict, Iterable, List, Optional, Sequence

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.setdefault("SECRET_KEY", "archive-tw-stock-daily")
os.environ.setdefault("ADMIN_USER", "archive")
os.environ.setdefault("ADMIN_PASSWORD", "archivepass")

from app.data_sources.tw_stock import FINMIND_BASE_URL, TWStockDataSource  # noqa: E402


@dataclass(frozen=True)
class DailyBarRecord:
    symbol: str
    exchange: str
    instrument_type: str
    trade_date: str
    open: float
    high: float
    low: float
    close: float
    volume: int
    trading_money: float
    trading_turnover: int
    spread: float
    source: str
    official_checked: int
    official_match: int
    quality_flags: str
    raw_json: str


def _num(value: Any) -> float:
    text = str(value or "").replace(",", "").strip()
    if text in ("", "--", "-"):
        return 0.0
    return float(text)


def _int_num(value: Any) -> int:
    return int(round(_num(value)))


def classify_instrument(symbol: str) -> str:
    code = str(symbol or "").strip()
    if code.startswith(("00", "006", "007", "008", "009")):
        return "etf"
    if len(code) == 4 and code.isdigit():
        return "stock"
    return ""


def validate_bar(record: DailyBarRecord) -> List[str]:
    flags: List[str] = []
    if record.open <= 0 or record.high <= 0 or record.low <= 0 or record.close <= 0:
        flags.append("non_positive_ohlc")
    if record.high < max(record.open, record.close):
        flags.append("high_below_open_close")
    if record.low > min(record.open, record.close):
        flags.append("low_above_open_close")
    if record.volume < 0:
        flags.append("negative_volume")
    try:
        datetime.strptime(record.trade_date, "%Y-%m-%d")
    except Exception:
        flags.append("bad_trade_date")
    return flags


def parse_finmind_rows(rows: Iterable[Dict[str, Any]], *, symbol: str, exchange: str = "") -> List[DailyBarRecord]:
    norm = TWStockDataSource.normalize_symbol(symbol)
    sym = norm.symbol or str(symbol or "").strip().upper()
    exch = exchange or norm.exchange or ("TWSE" if classify_instrument(sym) in ("stock", "etf") else "")
    out: List[DailyBarRecord] = []
    seen_dates = set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        trade_date = str(row.get("date") or "").strip()
        if not trade_date or trade_date in seen_dates:
            continue
        seen_dates.add(trade_date)
        record = DailyBarRecord(
            symbol=sym,
            exchange=exch,
            instrument_type=classify_instrument(sym),
            trade_date=trade_date,
            open=round(_num(row.get("open")), 6),
            high=round(_num(row.get("max")), 6),
            low=round(_num(row.get("min")), 6),
            close=round(_num(row.get("close")), 6),
            volume=_int_num(row.get("Trading_Volume")),
            trading_money=round(_num(row.get("Trading_money")), 2),
            trading_turnover=_int_num(row.get("Trading_turnover")),
            spread=round(_num(row.get("spread")), 6),
            source="finmind",
            official_checked=0,
            official_match=0,
            quality_flags="",
            raw_json=json.dumps(row, ensure_ascii=False, separators=(",", ":")),
        )
        flags = validate_bar(record)
        if flags:
            record = DailyBarRecord(**{**asdict(record), "quality_flags": ",".join(flags)})
        out.append(record)
    out.sort(key=lambda item: item.trade_date)
    return out


def fetch_finmind_rows(symbol: str, start: str, end: str, *, base_url: str = FINMIND_BASE_URL, timeout: int = 20) -> List[Dict[str, Any]]:
    params: Dict[str, Any] = {
        "dataset": "TaiwanStockPrice",
        "data_id": TWStockDataSource.normalize_symbol(symbol).symbol or symbol,
        "start_date": start,
        "end_date": end,
    }
    token = os.getenv("FINMIND_TOKEN") or os.getenv("FINMIND_API_TOKEN")
    if token:
        params["token"] = token.strip()
    source = TWStockDataSource(base_url=base_url)
    payload = source._http_get(params)
    if not payload:
        raise ValueError(f"FinMind request failed for {symbol}")
    if payload.get("status") not in (None, 200, "200", True):
        raise ValueError(f"FinMind returned non-ok status for {symbol}: {payload.get('status')}")
    data = payload.get("data") or []
    if not isinstance(data, list):
        raise ValueError(f"FinMind data must be a list for {symbol}")
    return data


def upsert_records(records: Sequence[DailyBarRecord]) -> int:
    from app.utils.db import get_db_connection  # noqa: WPS433

    if not records:
        return 0
    with get_db_connection() as db:
        cur = db.cursor()
        for item in records:
            cur.execute(
                """
                INSERT INTO qd_tw_stock_daily_bars (
                    symbol, exchange, instrument_type, trade_date,
                    open, high, low, close, volume,
                    trading_money, trading_turnover, spread,
                    source, official_checked, official_match,
                    quality_flags, raw_json, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?::jsonb, NOW())
                ON CONFLICT (symbol, trade_date, source) DO UPDATE SET
                    exchange = EXCLUDED.exchange,
                    instrument_type = EXCLUDED.instrument_type,
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
                """,
                (
                    item.symbol,
                    item.exchange,
                    item.instrument_type,
                    item.trade_date,
                    item.open,
                    item.high,
                    item.low,
                    item.close,
                    item.volume,
                    item.trading_money,
                    item.trading_turnover,
                    item.spread,
                    item.source,
                    item.official_checked,
                    item.official_match,
                    item.quality_flags,
                    item.raw_json,
                ),
            )
        db.commit()
        cur.close()
    return len(records)


def summarize(records: Sequence[DailyBarRecord]) -> Dict[str, Any]:
    symbols = sorted({item.symbol for item in records})
    flagged = [item for item in records if item.quality_flags]
    return {
        "count": len(records),
        "symbols": symbols,
        "date_min": min((item.trade_date for item in records), default=None),
        "date_max": max((item.trade_date for item in records), default=None),
        "flagged_count": len(flagged),
        "sample": [asdict(item) for item in records[:3]],
    }


def _default_start() -> str:
    return (date.today() - timedelta(days=45)).isoformat()


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Archive TWStock daily bars into PostgreSQL.")
    parser.add_argument("--symbol", action="append", default=[], help="Taiwan stock code. Can be repeated.")
    parser.add_argument("--start", default=_default_start(), help="Start date YYYY-MM-DD. Default: today-45d.")
    parser.add_argument("--end", default=date.today().isoformat(), help="End date YYYY-MM-DD. Default: today.")
    parser.add_argument("--apply", action="store_true", help="Write parsed bars to qd_tw_stock_daily_bars.")
    parser.add_argument("--dry-run", action="store_true", help="Fetch and validate only; do not write DB.")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_arg_parser().parse_args(argv)
    symbols = [s.strip() for s in args.symbol if s and s.strip()] or ["2330", "0050"]
    records: List[DailyBarRecord] = []
    for symbol in symbols:
        rows = fetch_finmind_rows(symbol, args.start, args.end)
        records.extend(parse_finmind_rows(rows, symbol=symbol))
    print(json.dumps(summarize(records), ensure_ascii=False, indent=2))
    if not records:
        print("ERROR: no TWStock daily bars parsed")
        return 2
    if args.apply and not args.dry_run:
        print(f"applied={upsert_records(records)}")
    else:
        print("dry_run=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
