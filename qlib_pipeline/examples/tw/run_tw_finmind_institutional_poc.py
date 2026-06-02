#!/usr/bin/env python3
from __future__ import annotations

import argparse
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
EXPECTED_DATES = ["2025-05-19", "2025-05-20", "2025-05-21", "2025-05-22", "2025-05-23"]
OFFICIAL_PROBES = [
    "https://www.twse.com.tw/rwd/en/fund/T86?date=20250519&selectType=ALLBUT0999&response=json",
    "https://www.twse.com.tw/rwd/zh/fund/T86?date=20250519&selectType=ALLBUT0999&response=json",
    "https://www.tpex.org.tw/openapi/v1/tpex_3insti_daily_trading?date=20250519",
]


def load_active_symbols(asof: str) -> pd.DataFrame:
    rows = []
    with UNIVERSE_PATH.open(encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split("\t")
            if len(parts) == 3:
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
    headers = {"User-Agent": "Mozilla/5.0 qlib-finmind-institutional-poc/1.0"}
    if token:
        headers["Authorization"] = f"Bearer {token.strip()}"
    try:
        resp = requests.get(FINMIND_URL, params=params, timeout=timeout, headers=headers)
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


def probe_official(timeout: float) -> pd.DataFrame:
    rows = []
    for url in OFFICIAL_PROBES:
        try:
            resp = requests.get(url, timeout=timeout, headers={"User-Agent": "Mozilla/5.0"})
            rows.append({"url": url, "http_status": resp.status_code, "ok": bool(resp.ok), "error": "", "body_prefix": resp.text[:160].replace("\n", " ")})
        except Exception as exc:
            rows.append({"url": url, "http_status": np.nan, "ok": False, "error": f"{type(exc).__name__}: {exc}", "body_prefix": ""})
    return pd.DataFrame(rows)


def load_volume(symbols: list[str], dates: list[str]) -> pd.DataFrame:
    frames = []
    for symbol in symbols:
        path = NORMALIZED_DIR / f"{symbol}.csv"
        if not path.exists():
            continue
        df = pd.read_csv(path, usecols=["symbol", "date", "volume"])
        df = df[df["date"].isin(dates)]
        if not df.empty:
            frames.append(df.rename(columns={"symbol": "qlib_symbol"}))
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=["qlib_symbol", "date", "volume"])


def build_unit_quality(raw: pd.DataFrame, volume: pd.DataFrame) -> pd.DataFrame:
    if raw.empty:
        return pd.DataFrame()
    data = raw.copy()
    data["buy"] = pd.to_numeric(data["buy"], errors="coerce")
    data["sell"] = pd.to_numeric(data["sell"], errors="coerce")
    daily = data.groupby(["qlib_symbol", "stock_id", "exchange", "date"], as_index=False).agg(
        investor_rows=("name", "count"),
        total_buy=("buy", "sum"),
        total_sell=("sell", "sum"),
        max_single_buy=("buy", "max"),
        max_single_sell=("sell", "max"),
        net_buy=("buy", lambda s: float(s.sum())),
    )
    sells = data.groupby(["qlib_symbol", "date"])["sell"].sum().reset_index(name="_sell_sum")
    daily = daily.merge(sells, on=["qlib_symbol", "date"], how="left")
    daily["net_buy"] = daily["total_buy"] - daily["_sell_sum"]
    daily = daily.drop(columns=["_sell_sum"])
    daily = daily.merge(volume, on=["qlib_symbol", "date"], how="left")
    daily["max_side_raw"] = daily[["max_single_buy", "max_single_sell"]].max(axis=1)
    daily["total_side_raw"] = daily[["total_buy", "total_sell"]].max(axis=1)
    daily["max_side_raw_to_volume"] = daily["max_side_raw"] / daily["volume"].replace(0, np.nan)
    daily["max_side_raw_x1000_to_volume"] = daily["max_side_raw"] * 1000.0 / daily["volume"].replace(0, np.nan)
    daily["total_side_raw_to_volume"] = daily["total_side_raw"] / daily["volume"].replace(0, np.nan)
    daily["total_side_raw_x1000_to_volume"] = daily["total_side_raw"] * 1000.0 / daily["volume"].replace(0, np.nan)
    daily["raw_negative_fields"] = ((daily[["total_buy", "total_sell", "max_single_buy", "max_single_sell"]] < 0).sum(axis=1)).astype(int)
    return daily


def summarize_unit_quality(q: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for exchange, g in q.groupby("exchange", dropna=False):
        rows.append({
            "exchange": exchange,
            "rows": int(g.shape[0]),
            "symbols": int(g["qlib_symbol"].nunique()),
            "rows_with_volume": int(g["volume"].notna().sum()),
            "negative_field_rows": int((g["raw_negative_fields"] > 0).sum()),
            "max_raw_to_volume_p50": float(g["max_side_raw_to_volume"].quantile(0.5)),
            "max_raw_to_volume_p95": float(g["max_side_raw_to_volume"].quantile(0.95)),
            "max_raw_to_volume_max": float(g["max_side_raw_to_volume"].max()),
            "max_raw_x1000_to_volume_p50": float(g["max_side_raw_x1000_to_volume"].quantile(0.5)),
            "max_raw_x1000_to_volume_p95": float(g["max_side_raw_x1000_to_volume"].quantile(0.95)),
            "max_raw_x1000_to_volume_max": float(g["max_side_raw_x1000_to_volume"].max()),
            "total_raw_to_volume_p95": float(g["total_side_raw_to_volume"].quantile(0.95)),
            "total_raw_x1000_to_volume_p95": float(g["total_side_raw_x1000_to_volume"].quantile(0.95)),
        })
    return pd.DataFrame(rows)


def table(df: pd.DataFrame, cols: list[str], limit: int | None = None) -> list[str]:
    d = df[cols].copy()
    if limit is not None:
        d = d.head(limit)
    for c in d.columns:
        d[c] = d[c].map(lambda x: "" if pd.isna(x) else (f"{x:.6f}" if isinstance(x, float) else str(x)))
    lines = ["| " + " | ".join(d.columns) + " |", "| " + " | ".join(["---"] * len(d.columns)) + " |"]
    lines.extend("| " + " | ".join(row) + " |" for row in d.to_numpy(dtype=str))
    return lines


def main() -> None:
    parser = argparse.ArgumentParser(description="Run narrow FinMind institutional-flow POC and PA-43 unit diagnostics.")
    parser.add_argument("--start", default=EXPECTED_DATES[0])
    parser.add_argument("--end", default=EXPECTED_DATES[-1])
    parser.add_argument("--asof", default=EXPECTED_DATES[-1])
    parser.add_argument("--output-dir", default="data_tw/experiments/tw_finmind_institutional_poc")
    parser.add_argument("--sleep", type=float, default=0.2)
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--official-timeout", type=float, default=8.0)
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
    expected = pd.date_range(args.start, args.end, freq="B").strftime("%Y-%m-%d").tolist()
    # Keep the fixed expected list if the requested window is the default trading week.
    if args.start == EXPECTED_DATES[0] and args.end == EXPECTED_DATES[-1]:
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
    daily_coverage = []
    for d in expected:
        g = raw[raw["date"].astype(str) == d] if not raw.empty else pd.DataFrame()
        daily_coverage.append({"date": d, "total_symbols": int(active.shape[0]), "symbols_with_data": int(g["qlib_symbol"].nunique()) if not g.empty else 0, "coverage_share": float(g["qlib_symbol"].nunique() / active.shape[0]) if not g.empty else 0.0})
    daily_coverage = pd.DataFrame(daily_coverage)

    volume = load_volume(active["qlib_symbol"].tolist(), expected)
    unit_quality = build_unit_quality(raw, volume)
    unit_summary = summarize_unit_quality(unit_quality) if not unit_quality.empty else pd.DataFrame()
    investor_summary = raw.groupby(["name"], as_index=False).agg(rows=("date", "count"), symbols=("qlib_symbol", "nunique"), buy_sum=("buy", "sum"), sell_sum=("sell", "sum")) if not raw.empty else pd.DataFrame()
    official = probe_official(args.official_timeout)

    fetch.to_csv(out / "fetch_status.csv", index=False)
    raw.to_csv(out / "raw_institutional_poc.csv", index=False)
    coverage.to_csv(out / "coverage_by_symbol.csv", index=False)
    daily_coverage.to_csv(out / "daily_coverage.csv", index=False)
    unit_quality.to_csv(out / "unit_quality_by_symbol_date.csv", index=False)
    unit_summary.to_csv(out / "unit_quality_summary.csv", index=False)
    investor_summary.to_csv(out / "investor_category_summary.csv", index=False)
    official.to_csv(out / "official_endpoint_probe.csv", index=False)

    ok_status = fetch[(fetch["http_status"] == 200) & (fetch["finmind_status"].astype(str) == "200")]
    complete_share = float(coverage["complete_5d"].mean()) if len(coverage) else np.nan
    total_expected = int(coverage["expected_days"].sum()) if len(coverage) else 0
    total_returned = int(coverage["returned_days"].sum()) if len(coverage) else 0
    row_coverage = float(total_returned / total_expected) if total_expected else np.nan
    unit_decision = "shares_likely_pa43_not_fully_closed_official_blocked"
    if not unit_summary.empty and unit_summary["max_raw_x1000_to_volume_p50"].min() > 10 and unit_summary["max_raw_to_volume_p95"].max() < 5:
        unit_decision = "shares_strongly_supported_official_blocked"

    report = ROOT / "docs/tw_audit/42_tw_finmind_institutional_poc_report.md"
    lines = [
        "---",
        "created_at: 2026-05-28",
        "status: institutional_poc_ready_for_audit",
        "scope: phase_e1_finmind_institutional_poc_pa43",
        "related_docs:",
        "  - docs/tw_audit/42_claude_audit_round_22_margin_util_ablation.md",
        "  - docs/tw_audit/34_tw_finmind_feasibility_memo.md",
        "---",
        "",
        "# FinMind Institutional Flow POC + PA-43 Unit Check",
        "",
        "## Scope",
        "",
        f"This POC follows option A from round 22. It requests `{DATASET}` for the active `tw_liquid_dyn` universe over {args.start}..{args.end}. It checks coverage, schema, investor categories, PIT assumptions, and PA-43 buy/sell unit semantics. It does not construct factors, format a provider, run IC, or run ablation.",
        "",
        "## Fetch Summary",
        "",
        f"- active symbols: `{active.shape[0]}`",
        f"- successful API statuses: `{ok_status.shape[0]}` / `{fetch.shape[0]}`",
        f"- raw rows: `{raw.shape[0]}`",
        f"- complete symbol share: `{complete_share:.6f}`",
        f"- row coverage: `{row_coverage:.6f}`",
        f"- token used: `{bool(fetch['token_used'].any()) if not fetch.empty else False}`",
        "",
        "## Daily Coverage",
        "",
    ]
    lines.extend(table(daily_coverage, ["date", "total_symbols", "symbols_with_data", "coverage_share"]))
    lines += ["", "## Investor Categories", ""]
    if not investor_summary.empty:
        lines.extend(table(investor_summary, ["name", "rows", "symbols", "buy_sum", "sell_sum"]))
    else:
        lines.append("(empty)")
    lines += ["", "## PA-43 Unit Diagnostics", "", f"unit decision: `{unit_decision}`", ""]
    if not unit_summary.empty:
        lines.extend(table(unit_summary, ["exchange", "rows", "symbols", "rows_with_volume", "negative_field_rows", "max_raw_to_volume_p50", "max_raw_to_volume_p95", "max_raw_x1000_to_volume_p50", "max_raw_x1000_to_volume_p95", "total_raw_to_volume_p95", "total_raw_x1000_to_volume_p95"]))
    else:
        lines.append("(empty)")
    lines += [
        "",
        "Interpretation: if FinMind buy/sell were lots, multiplying by 1000 would produce institutional single-side activity far above Yahoo daily volume on typical rows. The raw values themselves are comparable to share volume, supporting the prior that FinMind institutional buy/sell is in shares. Official TWSE/TPEx cross-check remains blocked in this environment, so PA-43 should be reviewed rather than silently closed.",
        "",
        "## Official Endpoint Probe",
        "",
    ]
    lines.extend(table(official, ["url", "http_status", "ok", "error"], limit=5))
    lines += [
        "",
        "## PIT Policy",
        "",
        "FinMind documentation previously recorded institutional updates at 20:00 on trading days. Treat each row date as trade date and apply a T+1 availability shift before any factor materialization.",
        "",
        "## Decision",
        "",
        "Institutional flow is feasible for TWSE+TPEX coverage at POC scale. Request Claude review of this POC and PA-43 unit evidence before full historical download or factor design.",
        "",
        "## Artifacts",
        "",
        f"- `{out.relative_to(ROOT) / 'fetch_status.csv'}`",
        f"- `{out.relative_to(ROOT) / 'raw_institutional_poc.csv'}`",
        f"- `{out.relative_to(ROOT) / 'coverage_by_symbol.csv'}`",
        f"- `{out.relative_to(ROOT) / 'daily_coverage.csv'}`",
        f"- `{out.relative_to(ROOT) / 'unit_quality_by_symbol_date.csv'}`",
        f"- `{out.relative_to(ROOT) / 'unit_quality_summary.csv'}`",
        f"- `{out.relative_to(ROOT) / 'investor_category_summary.csv'}`",
        f"- `{out.relative_to(ROOT) / 'official_endpoint_probe.csv'}`",
    ]
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"active_symbols={active.shape[0]}")
    print(f"successful_statuses={ok_status.shape[0]}/{fetch.shape[0]}")
    print(f"raw_rows={raw.shape[0]}")
    print(f"row_coverage={row_coverage:.6f}")
    print(f"unit_decision={unit_decision}")
    print(f"wrote {out.relative_to(ROOT)}")
    print(f"wrote {report.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
