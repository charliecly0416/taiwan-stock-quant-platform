#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[2]
UNIVERSE_PATH = ROOT / "data_tw/experiments/yahoo_adjusted_primary/universe/tw_liquid_dyn.txt"
META_PATH = ROOT / "data_tw/meta/tw_current_market_stock_symbols.csv"
NORMALIZED_DIR = ROOT / "data_tw/experiments/yahoo_adjusted_primary/normalized_nonempty"
FINMIND_URL = "https://api.finmindtrade.com/api/v4/data"
DATASET = "TaiwanStockInstitutionalInvestorsBuySell"
START_DATE = "2015-01-01"
END_DATE = "2025-05-28"
RAW_COLUMNS = ["date", "stock_id", "name", "buy", "sell", "qlib_symbol", "exchange"]
EXPECTED_CATEGORIES = {
    "Foreign_Investor",
    "Investment_Trust",
    "Dealer_self",
    "Dealer_Hedging",
    "Foreign_Dealer_Self",
}


def load_historical_symbols() -> pd.DataFrame:
    rows = []
    with UNIVERSE_PATH.open(encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split("\t")
            if len(parts) != 3:
                continue
            symbol, start, end = parts
            rows.append({"qlib_symbol": symbol, "start": start, "end": end})
    seg = pd.DataFrame(rows)
    symbols = seg.groupby("qlib_symbol", as_index=False).agg(universe_start=("start", "min"), universe_end=("end", "max"))
    symbols["stock_id"] = symbols["qlib_symbol"].str.replace("TW", "", regex=False)
    if META_PATH.exists():
        meta = pd.read_csv(META_PATH)[["qlib_symbol", "exchange", "instrument_type"]].drop_duplicates("qlib_symbol")
        symbols = symbols.merge(meta, on="qlib_symbol", how="left")
    else:
        symbols["exchange"] = np.nan
        symbols["instrument_type"] = np.nan
    symbols["exchange"] = symbols["exchange"].fillna("UNKNOWN")
    symbols["instrument_type"] = symbols["instrument_type"].fillna("UNKNOWN")
    return symbols.sort_values("qlib_symbol").reset_index(drop=True)


def request_finmind(stock_id: str, start: str, end: str, timeout: float) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    params = {"dataset": DATASET, "data_id": stock_id, "start_date": start, "end_date": end}
    token = os.getenv("FINMIND_TOKEN") or os.getenv("FINMIND_API_TOKEN")
    headers = {"User-Agent": "Mozilla/5.0 qlib-finmind-institutional-full/1.0"}
    if token:
        headers["Authorization"] = f"Bearer {token.strip()}"
    try:
        resp = requests.get(FINMIND_URL, params=params, headers=headers, timeout=timeout)
        try:
            payload = resp.json()
        except Exception:
            payload = {"status": None, "msg": resp.text[:200], "data": []}
        data = payload.get("data") if isinstance(payload, dict) else None
        rows = data if isinstance(data, list) else []
        return rows, {
            "http_status": resp.status_code,
            "finmind_status": payload.get("status") if isinstance(payload, dict) else None,
            "msg": payload.get("msg") if isinstance(payload, dict) else "bad_payload",
            "row_count": len(rows),
            "token_used": bool(token),
        }
    except Exception as exc:
        return [], {"http_status": None, "finmind_status": None, "msg": f"{type(exc).__name__}: {exc}", "row_count": 0, "token_used": bool(token)}


def raw_file_has_rows(path: Path) -> bool:
    if not path.exists() or path.stat().st_size == 0:
        return False
    try:
        return pd.read_csv(path, usecols=["date"], nrows=1).shape[0] > 0
    except Exception:
        return False


def save_raw(path: Path, rows: list[dict[str, Any]], symbol: str, stock_id: str, exchange: str) -> None:
    df = pd.DataFrame(rows)
    if df.empty:
        df = pd.DataFrame(columns=RAW_COLUMNS)
    df["qlib_symbol"] = symbol
    df["stock_id"] = stock_id
    df["exchange"] = exchange
    for col in RAW_COLUMNS:
        if col not in df.columns:
            df[col] = np.nan
    sort_cols = [c for c in ["date", "name"] if c in df.columns]
    df = df[RAW_COLUMNS].sort_values(sort_cols) if sort_cols else df[RAW_COLUMNS]
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


def load_all_raw(raw_dir: Path) -> pd.DataFrame:
    frames = []
    for path in sorted(raw_dir.glob("*.csv")):
        try:
            df = pd.read_csv(path)
        except Exception:
            continue
        if not df.empty:
            frames.append(df)
    if not frames:
        return pd.DataFrame(columns=RAW_COLUMNS)
    raw = pd.concat(frames, ignore_index=True)
    raw["date"] = raw["date"].astype(str)
    raw["buy"] = pd.to_numeric(raw["buy"], errors="coerce")
    raw["sell"] = pd.to_numeric(raw["sell"], errors="coerce")
    return raw


def expected_price_coverage(symbols: pd.DataFrame, start: str, end: str) -> pd.DataFrame:
    rows = []
    for _, row in symbols.iterrows():
        path = NORMALIZED_DIR / f"{row['qlib_symbol']}.csv"
        expected: set[str] = set()
        if path.exists():
            try:
                px = pd.read_csv(path, usecols=["date"])
                px["date"] = px["date"].astype(str)
                expected = set(px.loc[(px["date"] >= start) & (px["date"] <= end), "date"])
            except Exception:
                expected = set()
        rows.append({"qlib_symbol": row["qlib_symbol"], "expected_price_days": len(expected), "expected_dates": expected})
    return pd.DataFrame(rows)


def build_diagnostics(raw: pd.DataFrame) -> dict[str, pd.DataFrame]:
    if raw.empty:
        empty = pd.DataFrame()
        return {
            "category_summary": empty,
            "category_by_exchange": empty,
            "schema_by_symbol_date": empty,
            "schema_summary": empty,
            "first_date_summary": empty,
        }
    raw = raw.copy()
    raw["net_buy"] = raw["buy"] - raw["sell"]
    category_summary = raw.groupby("name", as_index=False).agg(
        rows=("date", "count"),
        symbols=("qlib_symbol", "nunique"),
        first_date=("date", "min"),
        last_date=("date", "max"),
        buy_sum=("buy", "sum"),
        sell_sum=("sell", "sum"),
        net_buy_sum=("net_buy", "sum"),
        nonzero_rows=("net_buy", lambda s: int((s != 0).sum())),
        buy_nonzero_rows=("buy", lambda s: int((s != 0).sum())),
        sell_nonzero_rows=("sell", lambda s: int((s != 0).sum())),
    ).sort_values("name")
    category_by_exchange = raw.groupby(["exchange", "name"], as_index=False).agg(
        rows=("date", "count"),
        symbols=("qlib_symbol", "nunique"),
        buy_sum=("buy", "sum"),
        sell_sum=("sell", "sum"),
        net_buy_sum=("net_buy", "sum"),
        nonzero_rows=("net_buy", lambda s: int((s != 0).sum())),
    ).sort_values(["exchange", "name"])
    schema = raw.groupby(["qlib_symbol", "stock_id", "exchange", "date"], as_index=False).agg(
        row_count=("name", "count"),
        category_count=("name", "nunique"),
        categories=("name", lambda s: ";".join(sorted(map(str, s.dropna().unique())))),
        buy_nulls=("buy", lambda s: int(s.isna().sum())),
        sell_nulls=("sell", lambda s: int(s.isna().sum())),
        negative_fields=("buy", lambda s: 0),
    )
    neg = raw.assign(_neg=((raw[["buy", "sell"]] < 0).sum(axis=1))).groupby(["qlib_symbol", "date"], as_index=False)["_neg"].sum()
    schema = schema.merge(neg, on=["qlib_symbol", "date"], how="left").drop(columns=["negative_fields"])
    schema = schema.rename(columns={"_neg": "negative_fields"})
    schema["has_expected_5_categories"] = schema["category_count"] == len(EXPECTED_CATEGORIES)
    schema["category_set_matches_poc"] = schema["categories"] == ";".join(sorted(EXPECTED_CATEGORIES))
    schema_summary = pd.DataFrame([{
        "symbol_date_rows": int(schema.shape[0]),
        "expected_5_category_share": float(schema["has_expected_5_categories"].mean()) if not schema.empty else np.nan,
        "poc_category_set_share": float(schema["category_set_matches_poc"].mean()) if not schema.empty else np.nan,
        "rows_with_null_buy_sell": int(((schema["buy_nulls"] + schema["sell_nulls"]) > 0).sum()),
        "rows_with_negative_fields": int((schema["negative_fields"] > 0).sum()),
    }])
    first_dates = raw.groupby(["qlib_symbol", "exchange"], as_index=False).agg(first_date=("date", "min"), last_date=("date", "max"))
    first_date_summary = first_dates.groupby(["exchange", "first_date"], as_index=False).agg(symbols=("qlib_symbol", "nunique")).sort_values(["symbols", "exchange", "first_date"], ascending=[False, True, True])
    return {
        "category_summary": category_summary,
        "category_by_exchange": category_by_exchange,
        "schema_by_symbol_date": schema,
        "schema_summary": schema_summary,
        "first_date_summary": first_date_summary,
    }


def table(df: pd.DataFrame, cols: list[str], limit: int | None = None) -> list[str]:
    if df.empty:
        return ["(empty)"]
    d = df[cols].copy()
    if limit is not None:
        d = d.head(limit)
    for c in d.columns:
        d[c] = d[c].map(lambda x: "" if pd.isna(x) else (f"{x:.6f}" if isinstance(x, float) else str(x)))
    lines = ["| " + " | ".join(d.columns) + " |", "| " + " | ".join(["---"] * len(d.columns)) + " |"]
    lines.extend("| " + " | ".join(row) + " |" for row in d.to_numpy(dtype=str))
    return lines


def write_report(report_path: Path, symbols: pd.DataFrame, probe: dict[str, Any], status: pd.DataFrame, raw: pd.DataFrame, coverage: pd.DataFrame, diagnostics: dict[str, pd.DataFrame], out_dir: Path, raw_dir: Path, args: argparse.Namespace) -> None:
    status_ok_mask = ((status["http_status"] == 200) & (status["finmind_status"].astype(str) == "200")) | (status["finmind_status"].astype(str) == "skipped")
    ok_status = status[status_ok_mask]
    nonempty = status[status["row_count"] > 0]
    failed = status[~status_ok_mask]
    empty_200 = status[(status["http_status"] == 200) & (status["finmind_status"].astype(str) == "200") & (status["row_count"] == 0)]
    quota_mask = (status["finmind_status"].astype(str) == "402") | status["msg"].astype(str).str.contains("upper limit", case=False, na=False)
    quota_count = int(quota_mask.sum())
    quota_blocked = quota_count > 0
    complete = (ok_status.shape[0] == symbols.shape[0]) and not quota_blocked and failed.empty
    cov_expected = coverage[coverage["expected_price_days"] > 0].copy()
    total_expected = int(cov_expected["expected_price_days"].sum()) if not cov_expected.empty else 0
    total_matched = int(cov_expected["matched_institutional_days"].sum()) if not cov_expected.empty else 0
    symbol_complete_share = float(cov_expected["complete_vs_price_days"].mean()) if not cov_expected.empty else np.nan
    row_coverage_share = float(total_matched / total_expected) if total_expected else np.nan
    cat = diagnostics["category_summary"]
    fds = cat[cat["name"] == "Foreign_Dealer_Self"] if not cat.empty else pd.DataFrame()
    if fds.empty:
        pa53_decision = "foreign_dealer_self_missing_from_history"
    else:
        fds_buy = float(fds["buy_sum"].iloc[0])
        fds_sell = float(fds["sell_sum"].iloc[0])
        fds_nonzero = int(fds["buy_nonzero_rows"].iloc[0]) + int(fds["sell_nonzero_rows"].iloc[0])
        pa53_decision = "foreign_dealer_self_all_zero_exclude_from_factor_design" if fds_buy == 0 and fds_sell == 0 and fds_nonzero == 0 else "foreign_dealer_self_has_nonzero_history_review_before_excluding"
    lines = [
        "---",
        "created_at: 2026-05-28",
        f"status: {'institutional_full_download_ready_for_audit' if complete else 'institutional_full_download_incomplete_for_audit'}",
        "scope: phase_e2_finmind_institutional_full_download",
        "related_docs:",
        "  - docs/tw_audit/43_claude_audit_round_23_institutional_poc.md",
        "  - docs/tw_audit/42_tw_finmind_institutional_poc_report.md",
        "---",
        "",
        "# FinMind Institutional Full Historical Download",
        "",
        "## Scope",
        "",
        f"This run downloads `{DATASET}` for the historical `tw_liquid_dyn` universe only. Date range is {args.start}..{args.end}. It stores raw per-symbol CSV files and runs coverage/schema/category diagnostics, including PA-53. It does not construct factors, format a Qlib provider, run IC, or run ablations.",
        "",
        "## Long-Span Probe",
        "",
        f"- probe stock_id: `{probe.get('stock_id')}`",
        f"- requested range: `{probe.get('start')}`..`{probe.get('end')}`",
        f"- http_status: `{probe.get('http_status')}`",
        f"- finmind_status: `{probe.get('finmind_status')}`",
        f"- rows: `{probe.get('row_count')}`",
        f"- first_date: `{probe.get('first_date')}`",
        f"- last_date: `{probe.get('last_date')}`",
        f"- decision: `{'single_request_ok' if probe.get('single_request_ok') else 'needs_chunking_or_review'}`",
        "",
        "## Download Summary",
        "",
        f"- historical universe symbols: `{symbols.shape[0]}`",
        f"- successful or skipped-available statuses: `{ok_status.shape[0]}`",
        f"- non-empty raw files: `{nonempty.shape[0]}`",
        f"- true-empty 200-status symbols: `{empty_200.shape[0]}`",
        f"- raw rows: `{raw.shape[0]}`",
        f"- raw date range: `{raw['date'].min() if not raw.empty else ''}`..`{raw['date'].max() if not raw.empty else ''}`",
        f"- failed statuses: `{failed.shape[0]}`",
        f"- quota-blocked statuses: `{quota_count}`",
        f"- token used: `{bool(status['token_used'].any()) if not status.empty else False}`",
        f"- output raw dir: `{raw_dir.relative_to(ROOT)}`",
        "",
        "## Coverage Vs Yahoo Price Calendar",
        "",
        f"- symbols with expected price days: `{cov_expected.shape[0]}`",
        f"- expected symbol-date rows: `{total_expected}`",
        f"- matched institutional symbol-date rows: `{total_matched}`",
        f"- row coverage share: `{row_coverage_share:.6f}`",
        f"- complete symbol share: `{symbol_complete_share:.6f}`",
        "",
    ]
    lines.extend(table(coverage.sort_values(["missing_institutional_days", "expected_price_days"], ascending=[False, False]), ["qlib_symbol", "exchange", "expected_price_days", "matched_institutional_days", "missing_institutional_days", "complete_vs_price_days"], limit=25))
    lines += ["", "## Investor Category Summary", ""]
    lines.extend(table(cat, ["name", "rows", "symbols", "first_date", "last_date", "buy_sum", "sell_sum", "net_buy_sum", "buy_nonzero_rows", "sell_nonzero_rows"]))
    lines += ["", "## PA-53 Foreign_Dealer_Self", "", f"decision: `{pa53_decision}`", ""]
    if not fds.empty:
        lines.extend(table(fds, ["name", "rows", "symbols", "buy_sum", "sell_sum", "net_buy_sum", "buy_nonzero_rows", "sell_nonzero_rows"]))
    else:
        lines.append("- Foreign_Dealer_Self category is absent from the downloaded history.")
    lines += ["", "## Schema Diagnostics", ""]
    lines.extend(table(diagnostics["schema_summary"], ["symbol_date_rows", "expected_5_category_share", "poc_category_set_share", "rows_with_null_buy_sell", "rows_with_negative_fields"]))
    bad_schema = diagnostics["schema_by_symbol_date"]
    if not bad_schema.empty:
        bad_schema = bad_schema[(~bad_schema["has_expected_5_categories"]) | (~bad_schema["category_set_matches_poc"]) | (bad_schema["buy_nulls"] > 0) | (bad_schema["sell_nulls"] > 0) | (bad_schema["negative_fields"] > 0)]
    lines += ["", "Schema exceptions:", ""]
    if bad_schema.empty:
        lines.append("- No schema exceptions: every downloaded symbol-date has the five POC categories, non-null buy/sell, and no negative buy/sell fields.")
    else:
        lines.extend(table(bad_schema, ["qlib_symbol", "stock_id", "exchange", "date", "row_count", "category_count", "categories", "buy_nulls", "sell_nulls", "negative_fields"], limit=50))
    lines += ["", "## Data Start Distribution", ""]
    lines.extend(table(diagnostics["first_date_summary"], ["exchange", "first_date", "symbols"], limit=30))
    lines += ["", "## Failed Or Empty Requests", ""]
    empty_or_failed = status[(status["row_count"] == 0) | ~status_ok_mask]
    if empty_or_failed.empty:
        lines.append("- No failed or empty requests.")
    else:
        lines.extend(table(empty_or_failed, ["qlib_symbol", "stock_id", "exchange", "http_status", "finmind_status", "row_count", "msg"], limit=80))
    lines += ["", "## Decision For Audit", ""]
    if complete:
        lines.append("- Full historical institutional download is complete at request/status level: no quota-blocked or failed statuses remain.")
    else:
        lines.append("- Full historical institutional download is not complete; rerun with resume before factor design unless Claude accepts the partial state as a blocker node.")
    lines += [
        f"- PA-53 decision from downloaded history: `{pa53_decision}`.",
        "- PA-43 remains closed from round 23: institutional buy/sell values are treated as shares.",
        "- Any future factor materialization must apply T+1 availability shift because FinMind publishes this dataset after market close.",
        "- No factor construction, provider formatting, IC screening, or ablation was performed.",
        "- Request Claude review of this download report and PA-53 before institutional factor design.",
        "",
        "## Artifacts",
        "",
    ]
    large_csv_names = {"full_schema_by_symbol_date.csv"}
    for p in sorted(out_dir.glob("*.csv")):
        if p.name not in large_csv_names:
            lines.append(f"- `{p.relative_to(ROOT)}`")
    if (out_dir / "pa44_2330_long_span_probe.json").exists():
        lines.append(f"- `{(out_dir / 'pa44_2330_long_span_probe.json').relative_to(ROOT)}`")
    large_items = [f"`{raw_dir.relative_to(ROOT)}/` ({len(list(raw_dir.glob('*.csv')))} raw CSV files)"]
    for name in sorted(large_csv_names):
        p = out_dir / name
        if p.exists():
            large_items.append(f"`{p.relative_to(ROOT)}`")
    lines.append("- local large artifacts: " + ", ".join(large_items))
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Download FinMind institutional full history for tw_liquid_dyn historical universe without factor/provider work.")
    parser.add_argument("--start", default=START_DATE)
    parser.add_argument("--end", default=END_DATE)
    parser.add_argument("--output-dir", default="data_tw/finmind_institutional")
    parser.add_argument("--sleep", type=float, default=0.8)
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--refresh-probe", action="store_true")
    parser.add_argument("--max-consecutive-quota-errors", type=int, default=5)
    args = parser.parse_args()

    out_dir = ROOT / args.output_dir
    raw_dir = out_dir / "raw"
    out_dir.mkdir(parents=True, exist_ok=True)
    raw_dir.mkdir(parents=True, exist_ok=True)
    symbols = load_historical_symbols()

    probe_path = out_dir / "pa44_2330_long_span_probe.json"
    probe = None
    if probe_path.exists() and not args.refresh_probe:
        try:
            cached_probe = json.loads(probe_path.read_text(encoding="utf-8"))
            if cached_probe.get("single_request_ok"):
                probe = cached_probe
        except Exception:
            probe = None
    if probe is None:
        probe_rows, probe_status = request_finmind("2330", args.start, args.end, args.timeout)
        probe_dates = sorted({str(r.get("date")) for r in probe_rows if r.get("date")})
        probe = {
            "stock_id": "2330",
            "start": args.start,
            "end": args.end,
            **probe_status,
            "first_date": probe_dates[0] if probe_dates else None,
            "last_date": probe_dates[-1] if probe_dates else None,
            "single_request_ok": bool(probe_dates and probe_dates[0] <= "2015-01-05" and probe_dates[-1] >= args.end),
        }
        if probe["single_request_ok"]:
            probe_path.write_text(json.dumps(probe, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if not probe["single_request_ok"]:
        print(json.dumps({"probe": probe, "error": "long_span_probe_failed_or_quota_blocked", "hint": "use cached successful probe or rerun after quota reset"}, ensure_ascii=False), flush=True)
        return

    statuses = []
    consecutive_quota_errors = 0
    for i, row in symbols.iterrows():
        symbol = row["qlib_symbol"]
        stock_id = str(row["stock_id"])
        path = raw_dir / f"{stock_id}.csv"
        if not args.refresh and raw_file_has_rows(path):
            try:
                n = int(pd.read_csv(path, usecols=["date"]).shape[0])
            except Exception:
                n = 0
            status = {"http_status": "skipped", "finmind_status": "skipped", "msg": "existing_nonempty", "row_count": n, "token_used": bool(os.getenv("FINMIND_TOKEN") or os.getenv("FINMIND_API_TOKEN"))}
        else:
            rows, status = request_finmind(stock_id, args.start, args.end, args.timeout)
            is_quota_error = str(status.get("finmind_status")) == "402" or "upper limit" in str(status.get("msg", "")).lower()
            if is_quota_error:
                consecutive_quota_errors += 1
            else:
                consecutive_quota_errors = 0
            save_raw(path, rows, symbol, stock_id, row["exchange"])
        statuses.append({"qlib_symbol": symbol, "stock_id": stock_id, "exchange": row["exchange"], **status})
        print(f"[{i+1}/{len(symbols)}] {symbol} rows={status.get('row_count')} status={status.get('finmind_status')} msg={status.get('msg')}", flush=True)
        if consecutive_quota_errors >= args.max_consecutive_quota_errors:
            print(f"stopping after {consecutive_quota_errors} consecutive quota errors; rerun later to resume", flush=True)
            break
        if status.get("finmind_status") != "skipped" and args.sleep > 0 and i + 1 < len(symbols):
            time.sleep(args.sleep)

    status_df = pd.DataFrame(statuses)
    status_df.to_csv(out_dir / "download_status.csv", index=False)
    raw = load_all_raw(raw_dir)
    diagnostics = build_diagnostics(raw)
    diagnostics["category_summary"].to_csv(out_dir / "full_category_summary.csv", index=False)
    diagnostics["category_by_exchange"].to_csv(out_dir / "full_category_by_exchange.csv", index=False)
    diagnostics["schema_by_symbol_date"].to_csv(out_dir / "full_schema_by_symbol_date.csv", index=False)
    diagnostics["schema_summary"].to_csv(out_dir / "full_schema_summary.csv", index=False)
    diagnostics["first_date_summary"].to_csv(out_dir / "full_first_date_summary.csv", index=False)

    expected = expected_price_coverage(symbols, args.start, args.end)
    raw_dates = raw.groupby("qlib_symbol")["date"].agg(lambda x: set(x.astype(str))).to_dict() if not raw.empty else {}
    coverage_rows = []
    for _, row in symbols.iterrows():
        sym = row["qlib_symbol"]
        exp = expected.loc[expected["qlib_symbol"] == sym, "expected_dates"].iloc[0]
        got = raw_dates.get(sym, set())
        matched = len(exp & got)
        missing = len(exp - got)
        coverage_rows.append({
            "qlib_symbol": sym,
            "stock_id": row["stock_id"],
            "exchange": row["exchange"],
            "expected_price_days": len(exp),
            "matched_institutional_days": matched,
            "missing_institutional_days": missing,
            "complete_vs_price_days": missing == 0 if len(exp) else True,
        })
    coverage = pd.DataFrame(coverage_rows)
    coverage.to_csv(out_dir / "full_coverage_vs_price_calendar.csv", index=False)

    report_path = ROOT / "docs/tw_audit/43_tw_finmind_institutional_full_download_report.md"
    write_report(report_path, symbols, probe, status_df, raw, coverage, diagnostics, out_dir, raw_dir, args)
    print(json.dumps({"symbols": int(symbols.shape[0]), "raw_rows": int(raw.shape[0]), "report": str(report_path.relative_to(ROOT))}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
