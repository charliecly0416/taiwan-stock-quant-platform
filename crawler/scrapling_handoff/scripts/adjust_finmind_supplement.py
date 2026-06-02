#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import csv
import json
import math
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

import pandas as pd
from scrapling.fetchers import Fetcher

COLUMNS = ["symbol", "date", "open", "high", "low", "close", "volume", "vwap", "factor"]
FINMIND_URL = "https://api.finmindtrade.com/api/v4/data"


@dataclass(frozen=True)
class CorporateAction:
    date: str
    before_price: float
    after_price: float
    adjustment_factor: float


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Forward-adjust FinMind supplement symbols with TaiwanStockDividendResult.")
    parser.add_argument("--finmind-report", default="crawl_report_finmind_supplement.json")
    parser.add_argument("--symbol", action="append", help="Limit to one or more TW symbols.")
    parser.add_argument("--symbols-file", default=None, help="Optional symbols file; one TW symbol per line.")
    parser.add_argument("--start", default="2015-01-01")
    parser.add_argument("--end", default="2026-05-21")
    parser.add_argument("--output-dir", default="normalized_full_market_stocks_adjusted")
    parser.add_argument("--report-file", default="adjust_finmind_supplement_report.json")
    parser.add_argument("--proxy", default="http://127.0.0.1:7890")
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--sleep-seconds", type=float, default=1.0)
    parser.add_argument("--continue-on-error", action="store_true")
    return parser.parse_args()


def clean_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        val = float(str(value).replace(",", "").strip())
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


def load_symbols(args: argparse.Namespace) -> list[str]:
    if args.symbol:
        return [item.strip().upper() for item in args.symbol]
    if args.symbols_file:
        return [line.strip().upper() for line in Path(args.symbols_file).read_text(encoding="utf-8").splitlines() if line.strip()]
    report = json.loads(Path(args.finmind_report).read_text(encoding="utf-8"))
    failed = set(report.get("symbols_failed", {}).keys())
    empty = set(report.get("symbols_empty", []))
    # The report does not currently persist a success list; infer it from requested missing symbols minus failures.
    source_symbols = [line.strip().upper() for line in Path("crawler_handoff_tw_full_market/yahoo_missing_symbols.txt").read_text(encoding="utf-8").splitlines() if line.strip()]
    return [symbol for symbol in source_symbols if symbol not in failed and symbol not in empty]


def fetch_finmind(dataset: str, symbol: str, start: str, end: str, proxy: str | None, timeout: float) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    code = symbol.removeprefix("TW")
    params = {"dataset": dataset, "data_id": code, "start_date": start, "end_date": end}
    token = os.getenv("FINMIND_TOKEN") or os.getenv("FINMIND_API_TOKEN")
    if token:
        params["token"] = token.strip()
    kwargs: dict[str, Any] = {"proxy": proxy} if proxy else {}
    try:
        page = Fetcher.get(FINMIND_URL, params=params, timeout=timeout, retries=1, impersonate="chrome", **kwargs)
        payload = page.json()
    except Exception as exc:
        return [], {"status": None, "error": f"{type(exc).__name__}:{exc}"}
    status = payload.get("status") if isinstance(payload, dict) else None
    if page.status >= 400 or status not in {200, "200"}:
        return [], {"status": page.status, "finmind_status": status, "error": payload.get("msg") if isinstance(payload, dict) else "bad_payload"}
    data = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(data, list):
        return [], {"status": page.status, "finmind_status": status, "error": "missing_data"}
    return data, None


def parse_actions(rows: Iterable[dict[str, Any]]) -> tuple[list[CorporateAction], list[str]]:
    actions: list[CorporateAction] = []
    flags: list[str] = []
    seen: set[tuple[str, float, float]] = set()
    for row in rows:
        day = str(row.get("date") or "").strip()
        before = clean_float(row.get("before_price"))
        after = clean_float(row.get("after_price"))
        if not day or before is None or after is None:
            flags.append("bad_corporate_action_row")
            continue
        if before <= 0 or after <= 0:
            flags.append("bad_corporate_action_price")
            continue
        key = (day, before, after)
        if key in seen:
            continue
        seen.add(key)
        actions.append(CorporateAction(day, before, after, after / before))
    actions.sort(key=lambda item: item.date)
    return actions, sorted(set(flags))


def factor_for_date(trade_date: str, actions: Sequence[CorporateAction]) -> float:
    factor = 1.0
    for action in actions:
        if trade_date < action.date:
            factor *= action.adjustment_factor
    return factor


def price_rows_to_frame(symbol: str, rows: Iterable[dict[str, Any]], actions: Sequence[CorporateAction]) -> tuple[pd.DataFrame, list[str]]:
    out: list[dict[str, Any]] = []
    flags: list[str] = []
    seen_dates: set[str] = set()
    for row in rows:
        trade_date = str(row.get("date") or "").strip()
        if not trade_date or trade_date in seen_dates:
            flags.append("missing_or_duplicate_date")
            continue
        seen_dates.add(trade_date)
        open_ = clean_float(row.get("open"))
        high = clean_float(row.get("max"))
        low = clean_float(row.get("min"))
        close = clean_float(row.get("close"))
        volume = clean_int(row.get("Trading_Volume"))
        trade_money = clean_float(row.get("Trading_money"))
        if None in {open_, high, low, close, volume}:
            flags.append("bad_price_row")
            continue
        if min(open_, high, low, close) <= 0:
            flags.append("non_positive_ohlc")
            continue
        high = max(high, open_, close)
        low = min(low, open_, close)
        vwap = trade_money / volume if trade_money and volume and volume > 0 else (open_ + high + low + close) / 4
        factor = factor_for_date(trade_date, actions)
        if factor <= 0 or math.isnan(factor) or math.isinf(factor):
            flags.append("bad_factor")
            continue
        open_adj = open_ * factor
        high_adj = high * factor
        low_adj = low * factor
        close_adj = close * factor
        high_adj = max(high_adj, open_adj, close_adj)
        low_adj = min(low_adj, open_adj, close_adj)
        out.append({
            "symbol": symbol,
            "date": trade_date,
            "open": round(open_adj, 6),
            "high": round(high_adj, 6),
            "low": round(low_adj, 6),
            "close": round(close_adj, 6),
            "volume": max(volume, 0),
            "vwap": round(vwap * factor, 6),
            "factor": round(factor, 12),
        })
    df = pd.DataFrame(out, columns=COLUMNS)
    if not df.empty:
        df = df.drop_duplicates(subset=["symbol", "date"]).sort_values("date")
    return df, sorted(set(flags))


def write_csv(path: Path, df: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, columns=COLUMNS, quoting=csv.QUOTE_MINIMAL)


def main() -> int:
    args = parse_args()
    symbols = load_symbols(args)
    output_dir = Path(args.output_dir)
    success: list[str] = []
    empty: list[str] = []
    failed: dict[str, dict[str, Any]] = {}
    items: list[dict[str, Any]] = []
    rows_written = 0

    for symbol in symbols:
        print(f"[adjust] {symbol}")
        price_rows, price_error = fetch_finmind("TaiwanStockPrice", symbol, args.start, args.end, args.proxy, args.timeout)
        action_rows, action_error = fetch_finmind("TaiwanStockDividendResult", symbol, args.start, args.end, args.proxy, args.timeout)
        if price_error or action_error:
            err = {"price_error": price_error, "action_error": action_error}
            failed[symbol] = err
            empty.append(symbol)
            print(f"[error] {symbol} {err}")
            if not args.continue_on_error:
                break
        else:
            actions, action_flags = parse_actions(action_rows)
            df, row_flags = price_rows_to_frame(symbol, price_rows, actions)
            if df.empty:
                failed[symbol] = {"error": "no_rows_after_adjustment", "raw_rows": len(price_rows)}
                empty.append(symbol)
                print(f"[empty] {symbol} raw_rows={len(price_rows)}")
                if not args.continue_on_error:
                    break
            else:
                out_path = output_dir / f"{symbol}.csv"
                write_csv(out_path, df)
                success.append(symbol)
                rows_written += len(df)
                item = {
                    "symbol": symbol,
                    "rows": len(df),
                    "actions": len(actions),
                    "date_min": str(df["date"].min()),
                    "date_max": str(df["date"].max()),
                    "factor_min": float(df["factor"].min()),
                    "factor_max": float(df["factor"].max()),
                    "flags": sorted(set(action_flags + row_flags)),
                    "output_file": str(out_path),
                }
                items.append(item)
                print(f"[ok] {symbol} rows={len(df)} actions={len(actions)} factor=({item['factor_min']},{item['factor_max']})")
        if args.sleep_seconds > 0:
            time.sleep(args.sleep_seconds)

    report = {
        "source": "FinMind TaiwanStockPrice + TaiwanStockDividendResult via Scrapling and local mihomo proxy",
        "start": args.start,
        "end": args.end,
        "symbols_requested": len(symbols),
        "symbols_success": len(success),
        "symbols_empty": empty,
        "symbols_failed": failed,
        "rows_written": rows_written,
        "items": items,
        "adjustment": "forward_adjusted_by_after_price_over_before_price",
        "notes": "For each corporate action, dates earlier than the action date are multiplied by after_price / before_price. OHLC and VWAP are adjusted; volume is unchanged.",
    }
    report_path = Path(args.report_file)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
