#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import math
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd
from scrapling.fetchers import Fetcher

COLUMNS = ["symbol", "date", "open", "high", "low", "close", "volume", "vwap", "factor"]
YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Crawl TW stock history from Yahoo Finance with Scrapling.")
    parser.add_argument("--symbols-file", default="crawler_handoff_tw_full_market/symbols_stock_only.txt")
    parser.add_argument("--symbol", action="append", help="Limit to one or more TW symbols.")
    parser.add_argument("--start", default="2015-01-01")
    parser.add_argument("--end", default="2026-05-21")
    parser.add_argument("--output-dir", default="normalized_full_market_stocks")
    parser.add_argument("--report-file", default="crawl_report.json")
    parser.add_argument("--proxy", default="http://127.0.0.1:7890")
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--sleep-seconds", type=float, default=0.5)
    parser.add_argument("--max-symbols", type=int, default=None)
    parser.add_argument("--skip-existing", action="store_true")
    parser.add_argument("--continue-on-error", action="store_true")
    parser.add_argument("--suffix", choices=["auto", "TW", "TWO"], default="auto")
    return parser.parse_args()


def to_epoch(day: str, end: bool = False) -> int:
    dt = datetime.strptime(day, "%Y-%m-%d").replace(tzinfo=UTC)
    if end:
        dt = dt + timedelta(days=1)
    return int(dt.timestamp())


def yahoo_tickers(symbol: str, suffix: str) -> list[str]:
    code = symbol.removeprefix("TW")
    if suffix == "TW":
        return [f"{code}.TW"]
    if suffix == "TWO":
        return [f"{code}.TWO"]
    return [f"{code}.TW", f"{code}.TWO"]


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


def fetch_chart(ticker: str, start: str, end: str, proxy: str | None, timeout: float) -> tuple[dict[str, Any] | None, str | None, int | None]:
    params = {
        "period1": str(to_epoch(start)),
        "period2": str(to_epoch(end, end=True)),
        "interval": "1d",
        "events": "history",
        "includeAdjustedClose": "true",
    }
    kwargs: dict[str, Any] = {"proxy": proxy} if proxy else {}
    try:
        page = Fetcher.get(
            YAHOO_CHART_URL.format(ticker=ticker),
            params=params,
            timeout=timeout,
            retries=1,
            impersonate="chrome",
            **kwargs,
        )
        if page.status >= 400:
            return None, f"http_status:{page.status}:{page.text[:120]}", page.status
        payload = page.json()
    except Exception as exc:
        return None, f"{type(exc).__name__}:{exc}", None
    error = payload.get("chart", {}).get("error") if isinstance(payload, dict) else "bad_payload"
    if error:
        return None, f"chart_error:{error}", page.status
    result = (payload.get("chart", {}).get("result") or [None])[0]
    if not result:
        return None, "empty_result", page.status
    return result, None, page.status


def result_to_frame(symbol: str, result: dict[str, Any]) -> pd.DataFrame:
    timestamps = result.get("timestamp") or []
    quote = (result.get("indicators", {}).get("quote") or [{}])[0]
    adj = (result.get("indicators", {}).get("adjclose") or [{}])[0]
    rows: list[dict[str, Any]] = []
    for i, ts in enumerate(timestamps):
        open_raw = clean_float((quote.get("open") or [None] * len(timestamps))[i])
        high_raw = clean_float((quote.get("high") or [None] * len(timestamps))[i])
        low_raw = clean_float((quote.get("low") or [None] * len(timestamps))[i])
        close_raw = clean_float((quote.get("close") or [None] * len(timestamps))[i])
        volume_raw = (quote.get("volume") or [None] * len(timestamps))[i]
        adj_close = clean_float((adj.get("adjclose") or [None] * len(timestamps))[i])
        if None in {open_raw, high_raw, low_raw, close_raw, adj_close}:
            continue
        if min(open_raw, high_raw, low_raw, close_raw, adj_close) <= 0:
            continue
        try:
            volume = int(volume_raw or 0)
        except (TypeError, ValueError):
            volume = 0
        factor = adj_close / close_raw
        if factor <= 0 or math.isnan(factor) or math.isinf(factor):
            continue
        open_adj = open_raw * factor
        high_adj = high_raw * factor
        low_adj = low_raw * factor
        close_adj = close_raw * factor
        high_adj = max(high_adj, open_adj, close_adj)
        low_adj = min(low_adj, open_adj, close_adj)
        rows.append(
            {
                "symbol": symbol,
                "date": datetime.fromtimestamp(int(ts), UTC).date().isoformat(),
                "open": open_adj,
                "high": high_adj,
                "low": low_adj,
                "close": close_adj,
                "volume": volume,
                "vwap": (open_adj + high_adj + low_adj + close_adj) / 4,
                "factor": factor,
            }
        )
    df = pd.DataFrame(rows, columns=COLUMNS)
    if not df.empty:
        df = df.drop_duplicates(subset=["symbol", "date"]).sort_values("date")
    return df


def load_symbols(args: argparse.Namespace) -> list[str]:
    if args.symbol:
        symbols = [item.strip().upper() for item in args.symbol]
    else:
        symbols = [line.strip().upper() for line in Path(args.symbols_file).read_text(encoding="utf-8").splitlines() if line.strip()]
    if args.max_symbols is not None:
        symbols = symbols[: args.max_symbols]
    return symbols


def write_csv(path: Path, df: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, columns=COLUMNS, quoting=csv.QUOTE_MINIMAL)


def main() -> int:
    args = parse_args()
    output_dir = Path(args.output_dir)
    symbols = load_symbols(args)
    success: list[str] = []
    empty: list[str] = []
    failed: dict[str, list[dict[str, Any]]] = {}
    suffix_used: dict[str, str] = {}
    rows_written = 0

    for symbol in symbols:
        out_path = output_dir / f"{symbol}.csv"
        if args.skip_existing and out_path.exists() and out_path.stat().st_size > 0:
            success.append(symbol)
            continue
        attempts: list[dict[str, Any]] = []
        df = pd.DataFrame(columns=COLUMNS)
        used_ticker = ""
        for ticker in yahoo_tickers(symbol, args.suffix):
            print(f"[crawl] {symbol} ticker={ticker}")
            result, error, status = fetch_chart(ticker, args.start, args.end, args.proxy, args.timeout)
            if result is None:
                attempts.append({"ticker": ticker, "status": status, "error": error})
                continue
            df = result_to_frame(symbol, result)
            if not df.empty:
                used_ticker = ticker
                break
            attempts.append({"ticker": ticker, "status": status, "error": "no_rows_after_parse"})
        if not df.empty:
            write_csv(out_path, df)
            success.append(symbol)
            suffix_used[symbol] = used_ticker
            rows_written += len(df)
            print(f"[ok] {symbol} ticker={used_ticker} rows={len(df)} file={out_path}")
        else:
            empty.append(symbol)
            failed[symbol] = attempts
            print(f"[empty] {symbol} attempts={attempts}")
            if not args.continue_on_error:
                break
        if args.sleep_seconds > 0:
            time.sleep(args.sleep_seconds)

    report = {
        "source": "Yahoo Finance chart API via Scrapling and local mihomo proxy",
        "start": args.start,
        "end": args.end,
        "symbols_requested": len(symbols),
        "symbols_success": len(success),
        "symbols_empty": empty,
        "symbols_failed": failed,
        "rows_written": rows_written,
        "suffix_used": suffix_used,
        "adjustment": "yahoo_adjusted_ohlc_factor_adjclose_over_close",
        "notes": "OHLC/VWAP are multiplied by Yahoo Adj Close / Close. VWAP uses adjusted OHLC average because Yahoo does not provide trading value.",
    }
    report_path = Path(args.report_file)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
