#!/usr/bin/env python3
"""Export Taiwan daily bars to Qlib-style normalized CSV files.

Default target format follows docs/data.txt:
    symbol,date,open,high,low,close,volume,vwap,factor

Data source:
- FinMind TaiwanStockPrice for stocks/ETFs and TAIEX.
- TWII is exported as symbol TWII, but queried from FinMind as TAIEX.

Dry-run is not used here because the output is local CSV files. Use --limit-symbols
or --symbol for small smoke exports.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import time
from dataclasses import asdict, dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.setdefault("SECRET_KEY", "export-tw-qlib-normalized")
os.environ.setdefault("ADMIN_USER", "export")
os.environ.setdefault("ADMIN_PASSWORD", "exportpass")

from app.data_sources.tw_stock import FINMIND_BASE_URL, TWStockDataSource  # noqa: E402

DEFAULT_DATA_SPEC = Path(__file__).resolve().parents[2] / "docs" / "data.txt"
DEFAULT_OUTPUT_DIR = Path("/home/chuliyang/qlib/data_tw/normalized")
OUTPUT_COLUMNS = ["symbol", "date", "open", "high", "low", "close", "volume", "vwap", "factor"]
INDEX_QUERY_MAP = {"TWII": "TAIEX"}


@dataclass(frozen=True)
class QlibRow:
    symbol: str
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: int
    vwap: float
    factor: float


@dataclass(frozen=True)
class ExportReportItem:
    symbol: str
    query_symbol: str
    output_file: str
    rows: int
    date_min: Optional[str]
    date_max: Optional[str]
    flagged_count: int
    flags: List[str]
    error: str = ""


def _num(value: Any) -> float:
    text = str(value or "").replace(",", "").strip()
    if text in ("", "--", "-"):
        return 0.0
    return float(text)


def _int_num(value: Any) -> int:
    return int(round(_num(value)))


def normalize_output_symbol(symbol: str) -> str:
    raw = str(symbol or "").strip().upper()
    if not raw:
        return ""
    if raw == "TAIEX":
        return "TWII"
    if raw == "TWII":
        return "TWII"
    if raw.startswith("TW") and raw[2:].isdigit():
        return raw
    norm = TWStockDataSource.normalize_symbol(raw).symbol
    if norm:
        return f"TW{norm}"
    return ""


def query_symbol_for_output(output_symbol: str) -> str:
    out = normalize_output_symbol(output_symbol)
    if out in INDEX_QUERY_MAP:
        return INDEX_QUERY_MAP[out]
    if out.startswith("TW") and out[2:].isdigit():
        return out[2:]
    return out


def parse_symbols_from_data_spec(path: Path = DEFAULT_DATA_SPEC) -> List[str]:
    if not path.exists():
        return []
    symbols: List[str] = []
    in_list = False
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("最低建议先准备这些"):
            in_list = True
            continue
        if not in_list or not stripped:
            continue
        token = stripped.split("#", 1)[0].strip().split()[0] if stripped.split("#", 1)[0].strip() else ""
        out = normalize_output_symbol(token)
        if out and out not in symbols:
            symbols.append(out)
    return symbols


def parse_symbols(raw_symbols: Sequence[str]) -> List[str]:
    out: List[str] = []
    for raw in raw_symbols or []:
        for part in str(raw or "").replace("\n", ",").split(","):
            symbol = normalize_output_symbol(part)
            if symbol and symbol not in out:
                out.append(symbol)
    return out


def fetch_finmind_rows(
    query_symbol: str,
    start: str,
    end: str,
    *,
    base_url: str = FINMIND_BASE_URL,
    timeout: int = 20,
    retries: int = 3,
    retry_sleep: float = 1.0,
) -> List[Dict[str, Any]]:
    params: Dict[str, Any] = {
        "dataset": "TaiwanStockPrice",
        "data_id": query_symbol,
        "start_date": start,
        "end_date": end,
    }
    token = os.getenv("FINMIND_TOKEN") or os.getenv("FINMIND_API_TOKEN")
    if token:
        params["token"] = token.strip()
    last_error: Optional[Exception] = None
    for attempt in range(max(int(retries or 1), 1)):
        try:
            response = requests.get(base_url, params=params, timeout=timeout)
            response.raise_for_status()
            payload = response.json()
            break
        except Exception as exc:
            last_error = exc
            if attempt + 1 >= max(int(retries or 1), 1):
                raise
            time.sleep(max(float(retry_sleep), 0.0) * (attempt + 1))
    else:
        raise last_error or RuntimeError(f"failed to fetch {query_symbol}")
    if payload.get("status") not in (None, 200, "200", True):
        raise ValueError(f"FinMind returned non-ok status for {query_symbol}: {payload.get('status')}")
    data = payload.get("data") or []
    if not isinstance(data, list):
        raise ValueError(f"FinMind data must be a list for {query_symbol}")
    return data


def _fallback_vwap(open_price: float, high: float, low: float, close: float) -> float:
    return (open_price + high + low + close) / 4.0


def parse_qlib_rows(
    rows: Iterable[Dict[str, Any]],
    output_symbol: str,
    *,
    factor: float = 1.0,
    prefer_money_vwap: bool = True,
) -> Tuple[List[QlibRow], List[str]]:
    out_symbol = normalize_output_symbol(output_symbol)
    out: List[QlibRow] = []
    flags: List[str] = []
    seen_dates = set()
    for row in rows:
        if not isinstance(row, dict):
            flags.append("bad_row_type")
            continue
        trade_date = str(row.get("date") or "").strip()
        if not trade_date:
            flags.append("missing_date")
            continue
        if trade_date in seen_dates:
            flags.append("duplicate_date")
            continue
        seen_dates.add(trade_date)
        open_price = _num(row.get("open"))
        high = _num(row.get("max"))
        low = _num(row.get("min"))
        close = _num(row.get("close"))
        volume = _int_num(row.get("Trading_Volume"))
        trading_money = _num(row.get("Trading_money"))
        if min(open_price, high, low, close) <= 0:
            flags.append("non_positive_ohlc")
            continue
        if high < max(open_price, close):
            flags.append("high_below_open_close")
        if low > min(open_price, close):
            flags.append("low_above_open_close")
        if volume < 0:
            flags.append("negative_volume")
            continue
        if prefer_money_vwap and volume > 0 and trading_money > 0:
            vwap = trading_money / volume
        else:
            if prefer_money_vwap:
                flags.append("fallback_vwap")
            vwap = _fallback_vwap(open_price, high, low, close)
        out.append(QlibRow(
            symbol=out_symbol,
            date=trade_date,
            open=round(open_price * factor, 6),
            high=round(high * factor, 6),
            low=round(low * factor, 6),
            close=round(close * factor, 6),
            volume=volume,
            vwap=round(vwap * factor, 6),
            factor=round(float(factor), 12),
        ))
    out.sort(key=lambda item: item.date)
    return out, flags


def write_csv(path: Path, rows: Sequence[QlibRow]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))


def export_symbol(output_symbol: str, start: str, end: str, output_dir: Path, *, continue_on_error: bool = False) -> ExportReportItem:
    normalized = normalize_output_symbol(output_symbol)
    query_symbol = query_symbol_for_output(normalized)
    output_file = output_dir / f"{normalized}.csv"
    try:
        rows_raw = fetch_finmind_rows(query_symbol, start, end)
        rows, flags = parse_qlib_rows(rows_raw, normalized, prefer_money_vwap=(normalized != "TWII"))
        write_csv(output_file, rows)
        return ExportReportItem(
            symbol=normalized,
            query_symbol=query_symbol,
            output_file=str(output_file),
            rows=len(rows),
            date_min=min((item.date for item in rows), default=None),
            date_max=max((item.date for item in rows), default=None),
            flagged_count=len(flags),
            flags=sorted(set(flags)),
        )
    except Exception as exc:
        if not continue_on_error:
            raise
        write_csv(output_file, [])
        return ExportReportItem(
            symbol=normalized,
            query_symbol=query_symbol,
            output_file=str(output_file),
            rows=0,
            date_min=None,
            date_max=None,
            flagged_count=1,
            flags=["fetch_error"],
            error=str(exc),
        )


def export_symbols(
    symbols: Sequence[str],
    start: str,
    end: str,
    output_dir: Path,
    *,
    continue_on_error: bool = False,
) -> Dict[str, Any]:
    items: List[ExportReportItem] = []
    for symbol in symbols:
        items.append(export_symbol(symbol, start, end, output_dir, continue_on_error=continue_on_error))
    return {
        "output_dir": str(output_dir),
        "start": start,
        "end": end,
        "count": len(items),
        "symbols": [item.symbol for item in items],
        "total_rows": sum(item.rows for item in items),
        "empty_symbols": [item.symbol for item in items if item.rows <= 0],
        "flagged_symbols": [item.symbol for item in items if item.flagged_count > 0],
        "failed_symbols": [item.symbol for item in items if item.error],
        "items": [asdict(item) for item in items],
    }


def _default_start() -> str:
    return (date.today() - timedelta(days=365 * 3)).isoformat()


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Export TWStock/TWII daily bars to Qlib normalized CSV files.")
    parser.add_argument("--symbol", action="append", default=[], help="TW2330/2330/TWII/TAIEX. Can be repeated or comma-separated.")
    parser.add_argument("--symbols-file", default="", help="Optional file with one or comma-separated symbol per line.")
    parser.add_argument("--data-spec", default=str(DEFAULT_DATA_SPEC), help="docs/data.txt-like file used when --symbol is omitted.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Target normalized CSV directory.")
    parser.add_argument("--start", default=_default_start(), help="Start date YYYY-MM-DD. Default: today-3y.")
    parser.add_argument("--end", default=date.today().isoformat(), help="End date YYYY-MM-DD. Default: today.")
    parser.add_argument("--limit-symbols", type=int, default=0, help="Limit symbols for smoke runs.")
    parser.add_argument("--continue-on-error", action="store_true", help="Write empty CSV and continue when one symbol fails.")
    return parser


def _load_symbols_file(path: str) -> List[str]:
    if not path:
        return []
    symbols: List[str] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.strip().startswith("#"):
            continue
        for symbol in parse_symbols([line.split("#", 1)[0]]):
            if symbol not in symbols:
                symbols.append(symbol)
    return symbols


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_arg_parser().parse_args(argv)
    symbols = parse_symbols(args.symbol)
    for symbol in _load_symbols_file(args.symbols_file):
        if symbol not in symbols:
            symbols.append(symbol)
    if not symbols:
        symbols = parse_symbols_from_data_spec(Path(args.data_spec))
    if args.limit_symbols and args.limit_symbols > 0:
        symbols = symbols[: args.limit_symbols]
    if not symbols:
        print(json.dumps({"error": "no symbols to export"}, ensure_ascii=False, indent=2))
        return 2
    report = export_symbols(symbols, args.start, args.end, Path(args.output_dir), continue_on_error=args.continue_on_error)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if report["empty_symbols"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
