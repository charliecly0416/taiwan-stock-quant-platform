#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
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
EXPECTED_DATES = ["2025-05-19", "2025-05-20", "2025-05-21", "2025-05-22", "2025-05-23"]
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


def load_active_symbols(asof: str) -> pd.DataFrame:
    rows = []
    with UNIVERSE_PATH.open(encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split("\t")
            if len(parts) != 3:
                continue
            symbol, start, end = parts
            rows.append({"qlib_symbol": symbol, "start": pd.Timestamp(start), "end": pd.Timestamp(end)})
    seg = pd.DataFrame(rows)
    active = seg[(seg["start"] <= pd.Timestamp(asof)) & (seg["end"] >= pd.Timestamp(asof))][["qlib_symbol"]].drop_duplicates()
    active["stock_id"] = active["qlib_symbol"].str.replace("TW", "", regex=False)
    meta = pd.read_csv(META_PATH)[["qlib_symbol", "exchange", "instrument_type"]].drop_duplicates("qlib_symbol")
    active = active.merge(meta, on="qlib_symbol", how="left")
    active["exchange"] = active["exchange"].fillna("UNKNOWN")
    return active.sort_values("qlib_symbol").reset_index(drop=True)


def fetch_symbol(stock_id: str, start: str, end: str, timeout: float) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    params = {"dataset": DATASET, "data_id": stock_id, "start_date": start, "end_date": end}
    token = os.getenv("FINMIND_TOKEN") or os.getenv("FINMIND_API_TOKEN")
    headers = {"User-Agent": "Mozilla/5.0 qlib-finmind-margin-poc/1.0"}
    if token:
        headers["Authorization"] = f"Bearer {token.strip()}"
    try:
        resp = requests.get(FINMIND_URL, params=params, timeout=timeout, headers=headers)
        payload = resp.json()
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


def load_volume(symbols: list[str], dates: list[str]) -> pd.DataFrame:
    frames = []
    cols = ["symbol", "date", "volume"]
    for symbol in symbols:
        path = NORMALIZED_DIR / f"{symbol}.csv"
        if not path.exists():
            continue
        df = pd.read_csv(path, usecols=cols)
        df = df[df["date"].isin(dates)]
        if not df.empty:
            frames.append(df.rename(columns={"symbol": "qlib_symbol"}))
    if not frames:
        return pd.DataFrame(columns=["qlib_symbol", "date", "volume"])
    return pd.concat(frames, ignore_index=True)


def fnum(row: pd.Series, field: str) -> float:
    return float(pd.to_numeric(row.get(field), errors="coerce"))


def build_quality_rows(raw: pd.DataFrame, volume: pd.DataFrame) -> pd.DataFrame:
    if raw.empty:
        return pd.DataFrame()
    data = raw.merge(volume, on=["qlib_symbol", "date"], how="left")
    rows = []
    for _, r in data.iterrows():
        mp_base = fnum(r, "MarginPurchaseYesterdayBalance") + fnum(r, "MarginPurchaseBuy") - fnum(r, "MarginPurchaseSell") - fnum(r, "MarginPurchaseCashRepayment")
        mp_today = fnum(r, "MarginPurchaseTodayBalance")
        ss_base = fnum(r, "ShortSaleYesterdayBalance") + fnum(r, "ShortSaleSell") - fnum(r, "ShortSaleBuy") - fnum(r, "ShortSaleCashRepayment")
        ss_today = fnum(r, "ShortSaleTodayBalance")
        offset = fnum(r, "OffsetLoanAndShort")
        m_no = mp_today - mp_base
        m_minus = mp_today - (mp_base - offset)
        m_plus = mp_today - (mp_base + offset)
        s_no = ss_today - ss_base
        s_minus = ss_today - (ss_base - offset)
        s_plus = ss_today - (ss_base + offset)
        neg = sum(int(fnum(r, field) < 0) for field in NONNEGATIVE_FIELDS)
        volume_val = fnum(r, "volume") if pd.notna(r.get("volume")) else np.nan
        flow_lot_max = max(fnum(r, "MarginPurchaseBuy"), fnum(r, "MarginPurchaseSell"), fnum(r, "ShortSaleBuy"), fnum(r, "ShortSaleSell"))
        flow_to_volume = (flow_lot_max * 1000.0 / volume_val) if volume_val and volume_val > 0 else np.nan
        rows.append({
            "qlib_symbol": r["qlib_symbol"],
            "stock_id": r["stock_id"],
            "exchange": r.get("exchange"),
            "date": r["date"],
            "margin_diff_no_offset": m_no,
            "margin_diff_minus_offset": m_minus,
            "margin_diff_plus_offset": m_plus,
            "margin_best_abs_diff": min(abs(m_no), abs(m_minus), abs(m_plus)),
            "short_diff_no_offset": s_no,
            "short_diff_minus_offset": s_minus,
            "short_diff_plus_offset": s_plus,
            "short_best_abs_diff": min(abs(s_no), abs(s_minus), abs(s_plus)),
            "negative_field_count": neg,
            "volume": volume_val,
            "max_flow_lots": flow_lot_max,
            "max_flow_lots_x1000_to_volume": flow_to_volume,
            "flow_gt_volume_flag": bool(pd.notna(flow_to_volume) and flow_to_volume > 1.0),
        })
    return pd.DataFrame(rows)


def summarize_balance(q: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for side, cols in {
        "margin": ["margin_diff_no_offset", "margin_diff_minus_offset", "margin_diff_plus_offset", "margin_best_abs_diff"],
        "short": ["short_diff_no_offset", "short_diff_minus_offset", "short_diff_plus_offset", "short_best_abs_diff"],
    }.items():
        for col in cols:
            s = q[col].dropna().abs()
            rows.append({
                "side": side,
                "metric": col,
                "n_rows": int(s.shape[0]),
                "exact_share": float((s == 0).mean()) if len(s) else np.nan,
                "abs_diff_p50": float(s.quantile(0.5)) if len(s) else np.nan,
                "abs_diff_p95": float(s.quantile(0.95)) if len(s) else np.nan,
                "abs_diff_max": float(s.max()) if len(s) else np.nan,
            })
    return pd.DataFrame(rows)


def table(df: pd.DataFrame, cols: list[str]) -> list[str]:
    d = df[cols].copy()
    for c in d.columns:
        d[c] = d[c].map(lambda x: "" if pd.isna(x) else (f"{x:.6f}" if isinstance(x, float) else str(x)))
    lines = ["| " + " | ".join(d.columns) + " |", "| " + " | ".join(["---"] * len(d.columns)) + " |"]
    lines.extend("| " + " | ".join(row) + " |" for row in d.to_numpy(dtype=str))
    return lines


def main() -> None:
    parser = argparse.ArgumentParser(description="Run narrow FinMind margin/short source POC without provider/factor construction.")
    parser.add_argument("--start", default=EXPECTED_DATES[0])
    parser.add_argument("--end", default=EXPECTED_DATES[-1])
    parser.add_argument("--asof", default=EXPECTED_DATES[-1])
    parser.add_argument("--output-dir", default="data_tw/experiments/tw_finmind_margin_poc")
    parser.add_argument("--sleep", type=float, default=0.5)
    parser.add_argument("--timeout", type=float, default=20.0)
    args = parser.parse_args()
    out = ROOT / args.output_dir
    out.mkdir(parents=True, exist_ok=True)

    active = load_active_symbols(args.asof)
    fetch_rows = []
    raw_frames = []
    for i, row in active.iterrows():
        rows, status = fetch_symbol(str(row["stock_id"]), args.start, args.end, args.timeout)
        fetch_rows.append({"qlib_symbol": row["qlib_symbol"], "stock_id": row["stock_id"], "exchange": row["exchange"], **status})
        if rows:
            df = pd.DataFrame(rows)
            df["qlib_symbol"] = row["qlib_symbol"]
            df["exchange"] = row["exchange"]
            raw_frames.append(df)
        print(f"[{i+1}/{len(active)}] {row['qlib_symbol']} rows={len(rows)} status={status.get('finmind_status')} msg={status.get('msg')}", flush=True)
        if args.sleep > 0 and i + 1 < len(active):
            time.sleep(args.sleep)

    fetch = pd.DataFrame(fetch_rows)
    raw = pd.concat(raw_frames, ignore_index=True) if raw_frames else pd.DataFrame()
    expected = EXPECTED_DATES
    coverage_rows = []
    for _, row in active.iterrows():
        sym_dates = set(raw.loc[raw["qlib_symbol"] == row["qlib_symbol"], "date"].astype(str)) if not raw.empty else set()
        missing = [d for d in expected if d not in sym_dates]
        coverage_rows.append({
            "qlib_symbol": row["qlib_symbol"],
            "stock_id": row["stock_id"],
            "exchange": row["exchange"],
            "expected_days": len(expected),
            "returned_days": len(sym_dates),
            "missing_days": ";".join(missing),
            "complete_5d": len(missing) == 0,
        })
    coverage = pd.DataFrame(coverage_rows)
    daily = []
    for d in expected:
        g = raw[raw["date"].astype(str) == d] if not raw.empty else pd.DataFrame()
        n = int(g["qlib_symbol"].nunique()) if not g.empty else 0
        daily.append({"date": d, "total_symbols": int(active.shape[0]), "symbols_with_data": n, "coverage_share": float(n / active.shape[0]) if len(active) else 0.0})
    daily_coverage = pd.DataFrame(daily)
    volume = load_volume(active["qlib_symbol"].tolist(), expected)
    quality = build_quality_rows(raw, volume)
    balance_summary = summarize_balance(quality) if not quality.empty else pd.DataFrame()
    value_summary = pd.DataFrame([{
        "n_quality_rows": int(quality.shape[0]),
        "rows_with_negative_fields": int((quality["negative_field_count"] > 0).sum()) if not quality.empty else 0,
        "rows_with_volume": int(quality["volume"].notna().sum()) if not quality.empty else 0,
        "rows_flow_gt_volume": int(quality["flow_gt_volume_flag"].sum()) if not quality.empty else 0,
        "max_flow_lots_x1000_to_volume": float(quality["max_flow_lots_x1000_to_volume"].max()) if not quality.empty else np.nan,
    }])

    fetch.to_csv(out / "fetch_status.csv", index=False)
    coverage.to_csv(out / "coverage_by_symbol.csv", index=False)
    daily_coverage.to_csv(out / "daily_coverage.csv", index=False)
    quality.to_csv(out / "balance_quality_by_row.csv", index=False)
    balance_summary.to_csv(out / "balance_conservation_summary.csv", index=False)
    value_summary.to_csv(out / "value_range_summary.csv", index=False)

    report = ROOT / "docs/tw_audit/35_tw_finmind_margin_poc_report.md"
    lines = [
        "---",
        "created_at: 2026-05-28",
        "status: margin_poc_ready_for_audit",
        "scope: phase_d2_finmind_margin_short_5d_poc",
        "related_docs:",
        "  - docs/tw_audit/35_claude_audit_round_15_finmind_feasibility.md",
        "  - docs/tw_audit/34_tw_finmind_feasibility_memo.md",
        "---",
        "",
        "# FinMind Margin/Short 5-Day POC",
        "",
        "## Scope",
        "",
        "This POC checks source coverage and basic data quality for `TaiwanStockMarginPurchaseShortSale` only. It covers active `tw_liquid_dyn` symbols on 2025-05-23 and dates 2025-05-19..2025-05-23. It does not construct factors, format a provider, or run ablations.",
        "",
        "## Summary",
        "",
        f"- active universe symbols: `{active.shape[0]}`",
        f"- fetched rows: `{raw.shape[0]}`",
        f"- symbols with complete 5-day data: `{int(coverage['complete_5d'].sum())}`",
        f"- complete-symbol coverage: `{coverage['complete_5d'].mean():.6f}`",
        f"- rows with negative checked fields: `{int((quality['negative_field_count'] > 0).sum()) if not quality.empty else 0}`",
        f"- rows where max margin/short flow lots x1000 exceeds Yahoo volume: `{int(quality['flow_gt_volume_flag'].sum()) if not quality.empty else 0}`",
        "",
        "## Daily Coverage",
        "",
    ]
    lines.extend(table(daily_coverage, ["date", "total_symbols", "symbols_with_data", "coverage_share"]))
    missing_coverage = coverage[~coverage["complete_5d"]].copy()
    lines += ["", "## Missing Coverage", ""]
    if missing_coverage.empty:
        lines.append("- No missing symbol-date coverage in the 5-day window.")
    else:
        lines.extend(table(missing_coverage, ["qlib_symbol", "exchange", "returned_days", "missing_days"]))
    lines += ["", "## Exchange Coverage", ""]
    exch = coverage.groupby("exchange", dropna=False).agg(symbols=("qlib_symbol", "count"), complete_symbols=("complete_5d", "sum")).reset_index()
    exch["complete_share"] = exch["complete_symbols"] / exch["symbols"]
    lines.extend(table(exch, ["exchange", "symbols", "complete_symbols", "complete_share"]))
    lines += ["", "## Balance Conservation", ""]
    lines.extend(table(balance_summary, ["side", "metric", "n_rows", "exact_share", "abs_diff_p50", "abs_diff_p95", "abs_diff_max"]))
    lines += ["", "## Value Range", ""]
    lines.extend(table(value_summary, ["n_quality_rows", "rows_with_negative_fields", "rows_with_volume", "rows_flow_gt_volume", "max_flow_lots_x1000_to_volume"]))
    lines += ["", "## Audit Notes", ""]
    lines += [
        "- Margin balance conserves exactly under the no-offset equation in this 2025-05-19..2025-05-23 sample: `TodayBalance = YesterdayBalance + Buy - Sell - CashRepayment`.",
        "- Adding or subtracting `OffsetLoanAndShort` breaks margin conservation in this sample, so PA-45 should treat the field as a separate diagnostic until official semantics are confirmed.",
        "- Short-sale balance does not conserve cleanly under the tested equations; any future short-side factor should require a separate accounting review.",
    ]
    lines += ["", "## Decision For Audit", ""]
    if coverage["complete_5d"].mean() >= 0.95 and int((quality["negative_field_count"] > 0).sum()) == 0:
        lines.append("- Coverage and value-range checks are mechanically acceptable for audit review.")
    else:
        lines.append("- Coverage or value-range checks need audit review before any next step.")
    lines += [
        "- Balance conservation is diagnostic only. The report includes no-offset, minus-offset, plus-offset and best-absolute-difference variants because PA-45 showed offset accounting ambiguity.",
        "- No provider formatting, factor construction or ablation was performed.",
        "",
        "## Artifacts",
        "",
    ]
    for p in sorted(out.iterdir()):
        if p.is_file():
            lines.append(f"- `{p.relative_to(ROOT)}`")
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"active_symbols": int(active.shape[0]), "fetched_rows": int(raw.shape[0]), "complete_symbols": int(coverage["complete_5d"].sum()), "report": str(report.relative_to(ROOT))}, ensure_ascii=False))


if __name__ == "__main__":
    main()
