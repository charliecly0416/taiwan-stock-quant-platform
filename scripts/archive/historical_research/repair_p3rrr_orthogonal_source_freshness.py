#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import math
import os
import time
import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "data_tw/experiments/ltr_orthogonal_features_controlled/daily_ltr_rerank"
RAW = OUT / "source_freshness_raw_archive"
LATEST_SIGNAL = ROOT / "qlib_pipeline/data_tw/experiments/option_c_daily_signal/latest_signal.json"
CALENDAR = ROOT / "qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin/calendars/day.txt"
FINMIND_URL = "https://api.finmindtrade.com/api/v4/data"
CATEGORIES = {
    "institutional_flow": "TaiwanStockInstitutionalInvestorsBuySell",
    "margin_short": "TaiwanStockMarginPurchaseShortSale",
}


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except Exception:
        return str(path)


def read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, default=str) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        fields = sorted({k for row in rows for k in row}) if rows else ["status"]
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def norm(raw: Any) -> str:
    text = str(raw or "").strip().upper()
    return text if text.startswith("TW") else f"TW{text}"


def latest_top50(asof_override: str = "", symbols_file: Path | None = None) -> tuple[str, list[str]]:
    latest = read_json(LATEST_SIGNAL)
    asof = str(asof_override or latest.get("asof") or "")[:10]
    if symbols_file is not None:
        top50 = pd.read_csv(symbols_file)
    else:
        run_dir = ROOT / "qlib_pipeline" / str(latest.get("run_dir", ""))
        top50 = pd.read_csv(run_dir / "top50_signals.csv")
    if "instrument" not in top50.columns:
        raise RuntimeError(f"symbols file must contain instrument column: {symbols_file}")
    symbols = sorted({norm(x) for x in top50["instrument"].astype(str).tolist()})
    return asof, symbols


def calendar_next_map() -> dict[pd.Timestamp, pd.Timestamp]:
    days = [pd.Timestamp(x.strip()).normalize() for x in CALENDAR.read_text(encoding="utf-8").splitlines() if x.strip()]
    days = sorted(set(days))
    return {days[i]: days[i + 1] for i in range(len(days) - 1)}


def token() -> str:
    if os.getenv("FINMIND_TOKEN") or os.getenv("FINMIND_API_TOKEN"):
        return (os.getenv("FINMIND_TOKEN") or os.getenv("FINMIND_API_TOKEN") or "").strip()
    for env in [ROOT / ".env", ROOT / ".env.local", ROOT / "backend/.env"]:
        if not env.exists():
            continue
        for line in env.read_text(encoding="utf-8", errors="ignore").splitlines():
            if "=" not in line or line.strip().startswith("#"):
                continue
            k, v = line.split("=", 1)
            if k.strip() in {"FINMIND_TOKEN", "FINMIND_API_TOKEN"}:
                return v.strip().strip("'\"")
    return ""


def request_finmind(category: str, symbol: str, start: str, end: str, token_value: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    params = {"dataset": CATEGORIES[category], "data_id": symbol.replace("TW", ""), "start_date": start, "end_date": end}
    headers = {"User-Agent": "tw-ltr-p3rrr-source-freshness/1.0"}
    if token_value:
        headers["Authorization"] = f"Bearer {token_value}"
    try:
        resp = requests.get(FINMIND_URL, params=params, headers=headers, timeout=20)
        payload = resp.json()
        rows = payload.get("data") if isinstance(payload, dict) else []
        rows = rows if isinstance(rows, list) else []
        ok = resp.status_code == 200 and str(payload.get("status")) == "200"
        return rows, {"status": "success" if ok else "failed", "http_status": resp.status_code, "finmind_status": payload.get("status"), "message": str(payload.get("msg") or "")[:240], "row_count": len(rows)}
    except Exception as exc:
        return [], {"status": "failed", "http_status": "", "finmind_status": "", "message": f"{type(exc).__name__}: {str(exc)[:220]}", "row_count": 0}


def to_day(value: Any) -> pd.Timestamp | None:
    ts = pd.to_datetime(value, errors="coerce")
    if pd.isna(ts):
        return None
    return pd.Timestamp(ts).normalize()


def next_weekday(day: pd.Timestamp | None) -> pd.Timestamp | None:
    if day is None:
        return None
    available = day + pd.Timedelta(days=1)
    while available.weekday() >= 5:
        available += pd.Timedelta(days=1)
    return available


def num(row: pd.Series, col: str) -> float:
    val = pd.to_numeric(row.get(col), errors="coerce")
    return float(val) if pd.notna(val) else float("nan")


def institutional_normalize(raw_rows: list[dict[str, Any]], symbol: str, fetched_at: str, snapshot_id: str, nxt: dict[pd.Timestamp, pd.Timestamp]) -> list[dict[str, Any]]:
    raw = pd.DataFrame(raw_rows)
    if raw.empty or "date" not in raw:
        return []
    out = []
    for day, group in raw.groupby("date"):
        trade = to_day(day)
        available = nxt.get(trade) if trade is not None else None
        foreign = trust = dealer = 0.0
        flags = []
        for _, row in group.iterrows():
            buy = num(row, "buy"); sell = num(row, "sell")
            name = str(row.get("name", "")).lower()
            if not math.isfinite(buy) or not math.isfinite(sell):
                flags.append("non_numeric_buy_sell")
                continue
            net = buy - sell
            if "foreign" in name:
                foreign += net
            elif "investment" in name or "trust" in name:
                trust += net
            elif "dealer" in name:
                dealer += net
        if available is None:
            available = next_weekday(trade)
            flags.append("calendar_fallback_next_weekday_after_qlib_calendar_end")
        out.append({
            "symbol": symbol,
            "stock_id": symbol.replace("TW", ""),
            "trade_date": trade.strftime("%Y-%m-%d") if trade is not None else str(day),
            "available_at": available.strftime("%Y-%m-%d") if available is not None else "",
            "foreign_net_buy": foreign,
            "investment_trust_net_buy": trust,
            "dealer_net_buy": dealer,
            "institutional_total_net_buy": foreign + trust + dealer,
            "data_source": f"FinMind:{CATEGORIES['institutional_flow']}",
            "source_url_or_endpoint": FINMIND_URL,
            "raw_snapshot_id": snapshot_id,
            "fetched_at": fetched_at,
            "quality_flags": ";".join(sorted(set(flags))),
        })
    return out


def margin_normalize(raw_rows: list[dict[str, Any]], symbol: str, fetched_at: str, snapshot_id: str, nxt: dict[pd.Timestamp, pd.Timestamp]) -> list[dict[str, Any]]:
    raw = pd.DataFrame(raw_rows)
    if raw.empty or "date" not in raw:
        return []
    out = []
    for _, row in raw.sort_values("date").iterrows():
        trade = to_day(row.get("date"))
        available = nxt.get(trade) if trade is not None else None
        mt = num(row, "MarginPurchaseTodayBalance"); my = num(row, "MarginPurchaseYesterdayBalance")
        st = num(row, "ShortSaleTodayBalance"); sy = num(row, "ShortSaleYesterdayBalance")
        flags = []
        if available is None:
            available = next_weekday(trade)
            flags.append("calendar_fallback_next_weekday_after_qlib_calendar_end")
        out.append({
            "symbol": symbol,
            "stock_id": symbol.replace("TW", ""),
            "trade_date": trade.strftime("%Y-%m-%d") if trade is not None else str(row.get("date")),
            "available_at": available.strftime("%Y-%m-%d") if available is not None else "",
            "margin_balance": mt if math.isfinite(mt) else "",
            "margin_balance_change": mt - my if math.isfinite(mt) and math.isfinite(my) else "",
            "short_balance": st if math.isfinite(st) else "",
            "short_balance_change": st - sy if math.isfinite(st) and math.isfinite(sy) else "",
            "data_source": f"FinMind:{CATEGORIES['margin_short']}",
            "source_url_or_endpoint": FINMIND_URL,
            "raw_snapshot_id": snapshot_id,
            "fetched_at": fetched_at,
            "quality_flags": ";".join(sorted(set(flags))),
        })
    return out


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch isolated P3RRR orthogonal source freshness raw archive.")
    parser.add_argument("--asof", default="", help="Artifact asof/end date label. Defaults to accepted latest_signal asof.")
    parser.add_argument("--start-date", default="2026-06-11", help="FinMind request start_date.")
    parser.add_argument("--end-date", default="", help="FinMind request end_date. Defaults to --asof/latest asof.")
    parser.add_argument(
        "--symbols-file",
        type=Path,
        default=None,
        help="Optional CSV with instrument column. Defaults to accepted latest top50_signals.csv.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    created_at = now()
    asof, symbols = latest_top50(args.asof, args.symbols_file)
    if not asof:
        raise RuntimeError("missing latest asof")
    start = args.start_date
    end = args.end_date or asof
    nxt = calendar_next_map()
    token_value = token()
    attempts = []
    manifests = []
    for family in ["institutional_flow", "margin_short"]:
        for idx, symbol in enumerate(symbols):
            started = now()
            rows, status = request_finmind(family, symbol, start, end, token_value)
            finished = now()
            snapshot_id = f"phasep3rrr_{family}_{symbol}_{started.replace('-', '').replace(':', '').replace('+00:00', 'Z')}"
            raw_path = RAW / family / f"{snapshot_id}_raw_response.jsonl"
            norm_path = RAW / family / f"{snapshot_id}_normalized.csv"
            raw_path.parent.mkdir(parents=True, exist_ok=True)
            with raw_path.open("w", encoding="utf-8") as fh:
                for row in rows:
                    fh.write(json.dumps(row, ensure_ascii=True, default=str) + "\n")
            normalized = institutional_normalize(rows, symbol, started, snapshot_id, nxt) if family == "institutional_flow" else margin_normalize(rows, symbol, started, snapshot_id, nxt)
            write_csv(norm_path, normalized)
            dates = [r.get("trade_date", "") for r in normalized]
            attempts.append({
                "feature_family": family,
                "symbol": symbol,
                "start_date": start,
                "end_date": end,
                "status": status["status"],
                "http_status": status["http_status"],
                "finmind_status": status["finmind_status"],
                "message": status["message"],
                "raw_row_count": len(rows),
                "normalized_row_count": len(normalized),
                "first_trade_date": min(dates) if dates else "",
                "last_trade_date": max(dates) if dates else "",
                "raw_path": rel(raw_path),
                "normalized_path": rel(norm_path),
                "token_used": bool(token_value),
            })
            manifests.append(attempts[-1])
            if idx % 10 == 9:
                time.sleep(0.2)
    write_csv(OUT / f"source_freshness_attempts_{asof}.csv", attempts)
    write_json(OUT / f"source_freshness_manifest_{asof}.json", {"created_at": created_at, "asof": asof, "start": start, "end": end, "attempt_count": len(attempts), "attempts": attempts, "no_provider_accepted_latest_monitor_trading": True})
    df = pd.DataFrame(attempts)
    summary_rows = []
    if not df.empty:
        for family, group in df.groupby("feature_family"):
            summary_rows.append({
                "feature_family": family,
                "attempts": int(len(group)),
                "success_attempts": int((group["status"] == "success").sum()),
                "raw_rows": int(pd.to_numeric(group["raw_row_count"], errors="coerce").sum()),
                "normalized_rows": int(pd.to_numeric(group["normalized_row_count"], errors="coerce").sum()),
                "latest_trade_date": max([x for x in group["last_trade_date"].astype(str).tolist() if x], default=""),
                "empty_symbols": "|".join(group.loc[pd.to_numeric(group["normalized_row_count"], errors="coerce").fillna(0).eq(0), "symbol"].astype(str).tolist()[:80]),
            })
    write_csv(OUT / f"source_freshness_summary_{asof}.csv", summary_rows)
    print(json.dumps({"ok": True, "asof": asof, "summary": rel(OUT / f"source_freshness_summary_{asof}.csv"), "attempts": len(attempts)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
