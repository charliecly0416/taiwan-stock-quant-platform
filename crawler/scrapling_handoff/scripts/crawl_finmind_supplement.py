#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import time
from pathlib import Path
from typing import Any

import pandas as pd
from scrapling.fetchers import Fetcher

COLUMNS = ["symbol", "date", "open", "high", "low", "close", "volume", "vwap", "factor"]
FINMIND_URL = "https://api.finmindtrade.com/api/v4/data"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Supplement missing TW stock CSVs from FinMind via Scrapling.")
    parser.add_argument("--symbols-file", default="crawler_handoff_tw_full_market/yahoo_missing_symbols.txt")
    parser.add_argument("--symbol", action="append", help="Limit to one or more TW symbols.")
    parser.add_argument("--start", default="2015-01-01")
    parser.add_argument("--end", default="2026-05-21")
    parser.add_argument("--output-dir", default="normalized_full_market_stocks")
    parser.add_argument("--report-file", default="crawl_report_finmind_supplement.json")
    parser.add_argument("--proxy", default="http://127.0.0.1:7890")
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--sleep-seconds", type=float, default=1.0)
    parser.add_argument("--max-symbols", type=int, default=None)
    parser.add_argument("--skip-existing", action="store_true")
    parser.add_argument("--continue-on-error", action="store_true")
    return parser.parse_args()


def load_symbols(args: argparse.Namespace) -> list[str]:
    if args.symbol:
        symbols = [item.strip().upper() for item in args.symbol]
    else:
        symbols = [line.strip().upper() for line in Path(args.symbols_file).read_text(encoding="utf-8").splitlines() if line.strip()]
    if args.max_symbols is not None:
        symbols = symbols[: args.max_symbols]
    return symbols


def clean_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        val = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(val) or math.isinf(val):
        return None
    return val


def clean_int(value: Any) -> int | None:
    val = clean_float(value)
    if val is None:
        return None
    return int(round(val))


def fetch_price(symbol: str, start: str, end: str, proxy: str | None, timeout: float) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    code = symbol.removeprefix("TW")
    params = {
        "dataset": "TaiwanStockPrice",
        "data_id": code,
        "start_date": start,
        "end_date": end,
    }
    token = os.getenv("FINMIND_TOKEN") or os.getenv("FINMIND_API_TOKEN")
    if token:
        params["token"] = token.strip()
    kwargs: dict[str, Any] = {"proxy": proxy} if proxy else {}
    try:
        page = Fetcher.get(
            FINMIND_URL,
            params=params,
            timeout=timeout,
            retries=1,
            impersonate="chrome",
            **kwargs,
        )
        payload = page.json()
    except Exception as exc:
        return [], {"status": None, "error": f"{type(exc).__name__}:{exc}"}
    status = payload.get("status") if isinstance(payload, dict) else None
    msg = payload.get("msg") if isinstance(payload, dict) else "bad_payload"
    if page.status >= 400 or status not in {200, "200"}:
        return [], {"status": page.status, "finmind_status": status, "error": msg}
    data = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(data, list):
        return [], {"status": page.status, "finmind_status": status, "error": "missing_data"}
    return data, None


def rows_to_frame(symbol: str, data: list[dict[str, Any]]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for item in data:
        open_ = clean_float(item.get("open"))
        high = clean_float(item.get("max"))
        low = clean_float(item.get("min"))
        close = clean_float(item.get("close"))
        volume = clean_int(item.get("Trading_Volume"))
        trade_money = clean_float(item.get("Trading_money"))
        if None in {open_, high, low, close, volume}:
            continue
        if min(open_, high, low, close) <= 0:
            continue
        high = max(high, open_, close)
        low = min(low, open_, close)
        vwap = trade_money / volume if trade_money and volume and volume > 0 else (open_ + high + low + close) / 4
        rows.append(
            {
                "symbol": symbol,
                "date": str(item.get("date")),
                "open": open_,
                "high": high,
                "low": low,
                "close": close,
                "volume": max(volume, 0),
                "vwap": vwap,
                "factor": 1.0,
            }
        )
    df = pd.DataFrame(rows, columns=COLUMNS)
    if not df.empty:
        df = df.drop_duplicates(subset=["symbol", "date"]).sort_values("date")
    return df


def write_csv(path: Path, df: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, columns=COLUMNS, quoting=csv.QUOTE_MINIMAL)


def main() -> int:
    args = parse_args()
    output_dir = Path(args.output_dir)
    symbols = load_symbols(args)
    success: list[str] = []
    empty: list[str] = []
    failed: dict[str, dict[str, Any]] = {}
    rows_written = 0

    for symbol in symbols:
        out_path = output_dir / f"{symbol}.csv"
        if args.skip_existing and out_path.exists() and out_path.stat().st_size > 0:
            success.append(symbol)
            continue
        print(f"[crawl] {symbol} source=FinMind")
        data, error = fetch_price(symbol, args.start, args.end, args.proxy, args.timeout)
        if error:
            failed[symbol] = error
            empty.append(symbol)
            print(f"[error] {symbol} {error}")
            if not args.continue_on_error:
                break
        else:
            df = rows_to_frame(symbol, data)
            if df.empty:
                empty.append(symbol)
                failed[symbol] = {"error": "no_rows_after_filter", "raw_rows": len(data)}
                print(f"[empty] {symbol} raw_rows={len(data)}")
                if not args.continue_on_error:
                    break
            else:
                write_csv(out_path, df)
                success.append(symbol)
                rows_written += len(df)
                print(f"[ok] {symbol} rows={len(df)} file={out_path}")
        if args.sleep_seconds > 0:
            time.sleep(args.sleep_seconds)

    report = {
        "source": "FinMind TaiwanStockPrice via Scrapling and local mihomo proxy",
        "start": args.start,
        "end": args.end,
        "symbols_requested": len(symbols),
        "symbols_success": len(success),
        "symbols_empty": empty,
        "symbols_failed": failed,
        "rows_written": rows_written,
        "adjustment": "raw_unadjusted",
        "notes": "Supplement for Yahoo-missing symbols. OHLCV are raw FinMind prices; factor=1.0. Non-positive OHLC rows are filtered.",
    }
    report_path = Path(args.report_file)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
