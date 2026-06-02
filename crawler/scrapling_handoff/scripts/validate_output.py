#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

COLUMNS = ["symbol", "date", "open", "high", "low", "close", "volume", "vwap", "factor"]


def check_file(path: Path) -> tuple[dict, list[str]]:
    issues: list[str] = []
    symbol = path.stem.upper()
    try:
        df = pd.read_csv(path)
    except Exception as exc:
        return {"symbol": symbol, "rows": 0, "start": "", "end": ""}, [f"read_error:{exc}"]

    if list(df.columns) != COLUMNS:
        issues.append(f"bad_columns:{list(df.columns)}")
    if df.empty:
        return {"symbol": symbol, "rows": 0, "start": "", "end": ""}, issues + ["empty"]

    if "symbol" in df.columns:
        bad_symbol = df["symbol"].astype(str).str.upper() != symbol
        if bool(bad_symbol.any()):
            issues.append("symbol_mismatch")
    try:
        dates = pd.to_datetime(df["date"])
    except Exception as exc:
        issues.append(f"bad_date:{exc}")
        dates = pd.Series(dtype="datetime64[ns]")
    if len(dates) and not dates.is_monotonic_increasing:
        issues.append("date_not_ascending")
    if len(dates) and dates.duplicated().any():
        issues.append("duplicate_dates")

    for col in ["open", "high", "low", "close", "vwap", "factor"]:
        vals = pd.to_numeric(df[col], errors="coerce") if col in df.columns else pd.Series(dtype=float)
        if vals.isna().any():
            issues.append(f"{col}_nan_or_non_numeric")
        if col in ["open", "high", "low", "close", "vwap", "factor"] and (vals <= 0).any():
            issues.append(f"{col}_non_positive")
    if "volume" in df.columns:
        vol = pd.to_numeric(df["volume"], errors="coerce")
        if vol.isna().any():
            issues.append("volume_nan_or_non_numeric")
        if (vol < 0).any():
            issues.append("volume_negative")

    if all(c in df.columns for c in ["open", "high", "low", "close"]):
        o = pd.to_numeric(df["open"], errors="coerce")
        h = pd.to_numeric(df["high"], errors="coerce")
        l = pd.to_numeric(df["low"], errors="coerce")
        c = pd.to_numeric(df["close"], errors="coerce")
        if (h < pd.concat([o, c], axis=1).max(axis=1)).any():
            issues.append("high_below_open_close")
        if (l > pd.concat([o, c], axis=1).min(axis=1)).any():
            issues.append("low_above_open_close")

    return {
        "symbol": symbol,
        "rows": int(len(df)),
        "start": dates.min().date().isoformat() if len(dates) else "",
        "end": dates.max().date().isoformat() if len(dates) else "",
    }, sorted(set(issues))


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate TW normalized CSV output for Qlib handoff.")
    parser.add_argument("--data-dir", required=True)
    parser.add_argument("--symbols-file", required=True)
    parser.add_argument("--report", default="validation_report.json")
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    symbols = [line.strip().upper() for line in Path(args.symbols_file).read_text(encoding="utf-8").splitlines() if line.strip()]
    summaries = []
    issue_map = {}
    missing = []
    empty = []
    for sym in symbols:
        path = data_dir / f"{sym}.csv"
        if not path.exists():
            missing.append(sym)
            continue
        summary, issues = check_file(path)
        summaries.append(summary)
        if summary["rows"] <= 0:
            empty.append(sym)
        if issues:
            issue_map[sym] = issues

    result = {
        "data_dir": str(data_dir),
        "symbols_expected": len(symbols),
        "files_found": len(summaries),
        "missing_count": len(missing),
        "empty_count": len(empty),
        "issue_symbol_count": len(issue_map),
        "total_rows": sum(item["rows"] for item in summaries),
        "missing_symbols": missing[:200],
        "empty_symbols": empty[:200],
        "issues_sample": dict(list(issue_map.items())[:100]),
    }
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if missing or issue_map else 0


if __name__ == "__main__":
    raise SystemExit(main())
