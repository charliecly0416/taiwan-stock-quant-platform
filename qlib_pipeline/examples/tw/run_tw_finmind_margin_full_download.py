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
DATASET = "TaiwanStockMarginPurchaseShortSale"
START_DATE = "2015-01-01"
END_DATE = "2025-06-30"
NONNEGATIVE_FIELDS = [
    "MarginPurchaseBuy",
    "MarginPurchaseCashRepayment",
    "MarginPurchaseLimit",
    "MarginPurchaseSell",
    "MarginPurchaseTodayBalance",
    "MarginPurchaseYesterdayBalance",
    "OffsetLoanAndShort",
    "ShortSaleBuy",
    "ShortSaleCashRepayment",
    "ShortSaleLimit",
    "ShortSaleSell",
    "ShortSaleTodayBalance",
    "ShortSaleYesterdayBalance",
]
RAW_COLUMNS = [
    "date",
    "stock_id",
    "MarginPurchaseBuy",
    "MarginPurchaseCashRepayment",
    "MarginPurchaseLimit",
    "MarginPurchaseSell",
    "MarginPurchaseTodayBalance",
    "MarginPurchaseYesterdayBalance",
    "OffsetLoanAndShort",
    "ShortSaleBuy",
    "ShortSaleCashRepayment",
    "ShortSaleLimit",
    "ShortSaleSell",
    "ShortSaleTodayBalance",
    "ShortSaleYesterdayBalance",
    "qlib_symbol",
    "exchange",
]


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
    headers = {"User-Agent": "Mozilla/5.0 qlib-finmind-margin-full/1.0"}
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
    df = df[RAW_COLUMNS].sort_values("date") if "date" in df.columns else df[RAW_COLUMNS]
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


def fnum(df: pd.DataFrame, field: str) -> pd.Series:
    return pd.to_numeric(df.get(field), errors="coerce")


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
    return raw


def expected_price_coverage(symbols: pd.DataFrame, start: str, end: str) -> pd.DataFrame:
    rows = []
    for _, row in symbols.iterrows():
        path = NORMALIZED_DIR / f"{row['qlib_symbol']}.csv"
        expected = set()
        if path.exists():
            try:
                px = pd.read_csv(path, usecols=["date"])
                px["date"] = px["date"].astype(str)
                expected = set(px.loc[(px["date"] >= start) & (px["date"] <= end), "date"])
            except Exception:
                expected = set()
        rows.append({"qlib_symbol": row["qlib_symbol"], "expected_price_days": len(expected), "expected_dates": expected})
    return pd.DataFrame(rows)


def build_quality(raw: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    if raw.empty:
        empty = pd.DataFrame()
        return empty, empty, empty
    q = raw.copy()
    mp_base = fnum(q, "MarginPurchaseYesterdayBalance") + fnum(q, "MarginPurchaseBuy") - fnum(q, "MarginPurchaseSell") - fnum(q, "MarginPurchaseCashRepayment")
    ss_base = fnum(q, "ShortSaleYesterdayBalance") + fnum(q, "ShortSaleSell") - fnum(q, "ShortSaleBuy") - fnum(q, "ShortSaleCashRepayment")
    q["margin_diff_no_offset"] = fnum(q, "MarginPurchaseTodayBalance") - mp_base
    q["short_diff_no_offset"] = fnum(q, "ShortSaleTodayBalance") - ss_base
    q["negative_field_count"] = 0
    for field in NONNEGATIVE_FIELDS:
        q["negative_field_count"] += (fnum(q, field) < 0).astype(int)
    summaries = []
    for side, col in [("margin", "margin_diff_no_offset"), ("short", "short_diff_no_offset")]:
        s = q[col].dropna().abs()
        summaries.append({
            "side": side,
            "metric": col,
            "n_rows": int(s.shape[0]),
            "exact_share": float((s == 0).mean()) if len(s) else np.nan,
            "abs_diff_p50": float(s.quantile(0.5)) if len(s) else np.nan,
            "abs_diff_p95": float(s.quantile(0.95)) if len(s) else np.nan,
            "abs_diff_max": float(s.max()) if len(s) else np.nan,
        })
    by_exchange = []
    for exchange, g in q.groupby("exchange", dropna=False):
        m = g["margin_diff_no_offset"].abs()
        sh = g["short_diff_no_offset"].abs()
        by_exchange.append({
            "exchange": exchange,
            "rows": int(g.shape[0]),
            "symbols": int(g["qlib_symbol"].nunique()),
            "margin_exact_share": float((m == 0).mean()) if len(m) else np.nan,
            "short_exact_share": float((sh == 0).mean()) if len(sh) else np.nan,
            "rows_with_negative_fields": int((g["negative_field_count"] > 0).sum()),
        })
    return q, pd.DataFrame(summaries), pd.DataFrame(by_exchange)


def table(df: pd.DataFrame, cols: list[str], limit: int | None = None) -> list[str]:
    d = df[cols].copy()
    if limit is not None:
        d = d.head(limit)
    for c in d.columns:
        d[c] = d[c].map(lambda x: "" if pd.isna(x) else (f"{x:.6f}" if isinstance(x, float) else str(x)))
    lines = ["| " + " | ".join(d.columns) + " |", "| " + " | ".join(["---"] * len(d.columns)) + " |"]
    lines.extend("| " + " | ".join(row) + " |" for row in d.to_numpy(dtype=str))
    return lines


def write_report(report_path: Path, symbols: pd.DataFrame, probe: dict[str, Any], status: pd.DataFrame, raw: pd.DataFrame, coverage: pd.DataFrame, balance_summary: pd.DataFrame, by_exchange: pd.DataFrame, out_dir: Path, raw_dir: Path, args: argparse.Namespace) -> None:
    status_ok_mask = ((status["http_status"] == 200) & (status["finmind_status"].astype(str) == "200")) | (status["finmind_status"].astype(str) == "skipped")
    ok_status = status[status_ok_mask]
    nonempty = status[status["row_count"] > 0]
    failed = status[~status_ok_mask]
    quota_mask = (status["finmind_status"].astype(str) == "402") | status["msg"].astype(str).str.contains("upper limit", case=False, na=False)
    quota_count = int(quota_mask.sum())
    quota_blocked = quota_count > 0
    quota_note = "This run hit the FinMind quota during the full-universe pass. The raw files and quality metrics below are partial, not a complete full-universe dataset. The script supports resume/skip-existing and stops early after consecutive quota errors." if quota_blocked else "This run completed without FinMind quota-limit statuses."
    cov_expected = coverage[coverage["expected_price_days"] > 0].copy()
    total_expected = int(cov_expected["expected_price_days"].sum()) if not cov_expected.empty else 0
    total_matched = int(cov_expected["matched_margin_days"].sum()) if not cov_expected.empty else 0
    symbol_complete_share = float(cov_expected["complete_vs_price_days"].mean()) if not cov_expected.empty else np.nan
    row_coverage_share = float(total_matched / total_expected) if total_expected else np.nan
    missing_top = cov_expected.sort_values(["missing_margin_days", "expected_price_days"], ascending=[False, False])
    missing_top = missing_top[missing_top["missing_margin_days"] > 0]
    lines = [
        "---",
        "created_at: 2026-05-28",
        f"status: {'margin_full_download_quota_blocked_for_audit' if quota_blocked else 'margin_full_download_ready_for_audit'}",
        "scope: phase_d3_finmind_margin_full_download",
        "related_docs:",
        "  - docs/tw_audit/36_claude_audit_round_16_margin_poc.md",
        "  - docs/tw_audit/35_tw_finmind_margin_poc_report.md",
        "---",
        "",
        f"# FinMind Margin Full Historical Download{' Attempt' if quota_blocked else ''}",
        "",
        "## Scope",
        "",
        f"This run downloads `{DATASET}` for the historical `tw_liquid_dyn` universe only. Date range is {args.start}..{args.end}. It stores raw per-symbol CSV files and runs source quality checks. It does not construct factors, format a Qlib provider, or run ablations.",
        "",
        "## PA-44 Long-Span Probe",
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
        quota_note,
        "",
        f"- historical universe symbols: `{symbols.shape[0]}`",
        f"- successful API statuses: `{ok_status.shape[0]}`",
        f"- non-empty raw files: `{nonempty.shape[0]}`",
        f"- raw rows: `{raw.shape[0]}`",
        f"- raw date range: `{raw['date'].min() if not raw.empty else ''}`..`{raw['date'].max() if not raw.empty else ''}`",
        f"- failed statuses: `{failed.shape[0]}`",
        f"- quota-blocked statuses: `{quota_count}`",
        f"- output raw dir: `{raw_dir.relative_to(ROOT)}`",
        "",
        "## Coverage Vs Yahoo Price Calendar",
        "",
        "Coverage should be treated as a final source coverage judgment only when the run has no quota-blocked statuses.",
        "",
        f"- symbols with expected price days: `{cov_expected.shape[0]}`",
        f"- expected symbol-date rows: `{total_expected}`",
        f"- matched margin symbol-date rows: `{total_matched}`",
        f"- row coverage share: `{row_coverage_share:.6f}`",
        f"- complete symbol share: `{symbol_complete_share:.6f}`",
        "",
    ]
    lines.extend(table(coverage.sort_values(["missing_margin_days", "expected_price_days"], ascending=[False, False]), ["qlib_symbol", "exchange", "expected_price_days", "matched_margin_days", "missing_margin_days", "complete_vs_price_days"], limit=20))
    lines += ["", "## Balance Conservation", ""]
    lines.extend(table(balance_summary, ["side", "metric", "n_rows", "exact_share", "abs_diff_p50", "abs_diff_p95", "abs_diff_max"]))
    lines += ["", "## Exchange Diagnostics", ""]
    lines.extend(table(by_exchange.sort_values("exchange"), ["exchange", "rows", "symbols", "margin_exact_share", "short_exact_share", "rows_with_negative_fields"]))
    lines += ["", "## Failed Or Empty Requests", ""]
    empty_or_failed = status[(status["row_count"] == 0) | ~status_ok_mask]
    if empty_or_failed.empty:
        lines.append("- No failed or empty requests.")
    else:
        lines.extend(table(empty_or_failed, ["qlib_symbol", "stock_id", "exchange", "http_status", "finmind_status", "row_count", "msg"], limit=50))
    lines += ["", "## Decision For Audit", ""]
    if probe.get("single_request_ok") and raw.shape[0] > 0:
        lines.append("- PA-44 is mechanically closed for this dataset and range: one 10.5-year symbol request returned the full requested span.")
    else:
        lines.append("- PA-44 needs audit review before relying on single-request full-history downloads.")
    if quota_blocked:
        lines.append(f"- Full download is not complete under quota: `{ok_status.shape[0]}/{symbols.shape[0]}` API requests succeeded and `{quota_count}` requests returned quota-limit statuses; rerun after quota reset or with a token to resume.")
    lines += [
        "- Margin no-offset balance conservation is the relevant gate for margin-side factor construction.",
        "- Short-side diagnostics are reported for visibility only; PA-48 remains open and no short-side delta factor should be built from this report.",
        "- No factor construction, provider formatting or ablation was performed.",
        "",
        "## Artifacts",
        "",
    ]
    for p in sorted(out_dir.glob("*.csv")):
        lines.append(f"- `{p.relative_to(ROOT)}`")
    lines.append(f"- `{raw_dir.relative_to(ROOT)}/` ({len(list(raw_dir.glob('*.csv')))} raw CSV files)")
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Download FinMind margin/short full history for tw_liquid_dyn historical universe without factor/provider work.")
    parser.add_argument("--start", default=START_DATE)
    parser.add_argument("--end", default=END_DATE)
    parser.add_argument("--output-dir", default="data_tw/finmind_margin")
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
            "single_request_ok": bool(probe_dates and probe_dates[0] <= "2015-01-05" and probe_dates[-1] >= "2025-06-30"),
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
    q, balance_summary, by_exchange = build_quality(raw)
    q.to_csv(out_dir / "full_balance_quality_by_row.csv", index=False)
    balance_summary.to_csv(out_dir / "full_balance_conservation_summary.csv", index=False)
    by_exchange.to_csv(out_dir / "full_exchange_diagnostics.csv", index=False)

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
            "matched_margin_days": matched,
            "missing_margin_days": missing,
            "complete_vs_price_days": missing == 0 if len(exp) else True,
        })
    coverage = pd.DataFrame(coverage_rows)
    coverage.to_csv(out_dir / "full_coverage_vs_price_calendar.csv", index=False)

    report_path = ROOT / "docs/tw_audit/36_tw_finmind_margin_full_download_report.md"
    write_report(report_path, symbols, probe, status_df, raw, coverage, balance_summary, by_exchange, out_dir, raw_dir, args)
    print(json.dumps({"symbols": int(symbols.shape[0]), "raw_rows": int(raw.shape[0]), "report": str(report_path.relative_to(ROOT))}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
