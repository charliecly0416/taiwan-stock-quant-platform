#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import re
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import requests


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data_tw/experiments/ltr_orthogonal_features_controlled/phase_o1r_coverage_available_at_repair"
RAW_DIR = OUT / "raw_archive"
REPORT = ROOT / "docs/tw_ltr_orthogonal_features_controlled/PHASEO1R_COVERAGE_AVAILABLE_AT_REPAIR_EXECUTION_REPORT_CN.md"

CONTROL_SAMPLE = ROOT / "data_tw/experiments/ltr_rerank_regime_turnover/phase1_ltr_baseline/phase1_ltr_samples.csv"
O1_SUMMARY = ROOT / "data_tw/experiments/ltr_orthogonal_features_controlled/phase_o1_pit_availability/phaseo1_summary.json"
PHASE0E_COVERAGE = ROOT / "data_tw/experiments/decision_orthogonal/phase0e_coverage_report.csv"
PHASE0E_NORMALIZED = {
    "institutional_flow": ROOT
    / "data_tw/experiments/decision_orthogonal/phase0e_raw_archive/institutional_flow/phase0e_institutional_flow_20260610T175901Z_normalized.csv",
    "margin_short": ROOT
    / "data_tw/experiments/decision_orthogonal/phase0e_raw_archive/margin_short/phase0e_margin_short_20260610T180330Z_normalized.csv",
}

FINMIND_URL = "https://api.finmindtrade.com/api/v4/data"
CATEGORIES = {
    "institutional_flow": "TaiwanStockInstitutionalInvestorsBuySell",
    "margin_short": "TaiwanStockMarginPurchaseShortSale",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except Exception:
        return str(path)


def load_dotenv_token() -> str:
    for name in [".env", ".env.local"]:
        path = ROOT / name
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            text = line.strip()
            if not text or text.startswith("#") or "=" not in text:
                continue
            key, value = text.split("=", 1)
            if key.strip() in {"FINMIND_TOKEN", "FINMIND_API_TOKEN"}:
                return value.strip().strip("'\"")
    return ""


def read_token() -> tuple[str, str]:
    token = os.getenv("FINMIND_TOKEN") or os.getenv("FINMIND_API_TOKEN")
    if token:
        return token.strip(), "env"
    token = load_dotenv_token()
    if token:
        return token, "dotenv"
    return "", "none"


def safe_error(value: Any) -> str:
    text = str(value or "")
    for word in ["FINMIND_TOKEN", "FINMIND_API_TOKEN", "Authorization", "Bearer", "token"]:
        text = text.replace(word, "[redacted]")
    return text[:300]


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        fields = sorted({key for row in rows for key in row})
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, default=str) + "\n", encoding="utf-8")


def md_table(rows: list[dict[str, Any]], fields: list[str], limit: int = 40) -> list[str]:
    lines = ["| " + " | ".join(fields) + " |", "| " + " | ".join(["---"] * len(fields)) + " |"]
    for row in rows[:limit]:
        lines.append("| " + " | ".join(str(row.get(field, "")) for field in fields) + " |")
    return lines


def sha256_size(path: Path) -> str:
    return f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()} size:{path.stat().st_size}"


def load_control() -> pd.DataFrame:
    return pd.read_csv(CONTROL_SAMPLE, usecols=["date", "instrument", "sample_complete"])


def next_trading_map(dates: list[pd.Timestamp]) -> dict[pd.Timestamp, pd.Timestamp]:
    ordered = sorted(pd.Series(pd.to_datetime(dates)).dropna().unique())
    return {ordered[idx]: ordered[idx + 1] for idx in range(len(ordered) - 1)}


def request_finmind(category: str, stock_id: str, start: str, end: str, timeout: float, token: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    params = {"dataset": CATEGORIES[category], "data_id": stock_id, "start_date": start, "end_date": end}
    headers = {"User-Agent": "tw-ltr-orthogonal-o1r/1.0"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        resp = requests.get(FINMIND_URL, params=params, headers=headers, timeout=timeout)
        try:
            payload = resp.json()
        except Exception:
            payload = {"status": None, "msg": resp.text[:300], "data": []}
        data = payload.get("data") if isinstance(payload, dict) else []
        rows = data if isinstance(data, list) else []
        ok = resp.status_code == 200 and str(payload.get("status")) == "200"
        return rows, {
            "status": "success" if ok else "failed",
            "http_status": resp.status_code,
            "finmind_status": payload.get("status") if isinstance(payload, dict) else "",
            "error_type": "" if ok else "finmind_or_http_error",
            "error_message": "" if ok else safe_error(payload.get("msg") if isinstance(payload, dict) else "bad_payload"),
            "token_used": bool(token),
        }
    except Exception as exc:
        return [], {
            "status": "failed",
            "http_status": "",
            "finmind_status": "",
            "error_type": type(exc).__name__,
            "error_message": safe_error(exc),
            "token_used": bool(token),
        }


def to_day(value: Any) -> pd.Timestamp | None:
    ts = pd.to_datetime(value, errors="coerce")
    if pd.isna(ts):
        return None
    return pd.Timestamp(ts).normalize()


def num(row: pd.Series, col: str) -> float:
    value = pd.to_numeric(row.get(col), errors="coerce")
    if pd.isna(value):
        return float("nan")
    return float(value)


def institutional_normalize(raw_rows: list[dict[str, Any]], symbol: str, fetched_at: str, snapshot_id: str, nxt: dict[pd.Timestamp, pd.Timestamp]) -> list[dict[str, Any]]:
    raw = pd.DataFrame(raw_rows)
    if raw.empty or "date" not in raw:
        return []
    out: list[dict[str, Any]] = []
    for date, group in raw.groupby("date"):
        trade_day = to_day(date)
        available = nxt.get(trade_day) if trade_day is not None else None
        flags = []
        foreign = trust = dealer = 0.0
        seen = set()
        for _, row in group.iterrows():
            name = str(row.get("name", ""))
            buy = num(row, "buy")
            sell = num(row, "sell")
            if not math.isfinite(buy) or not math.isfinite(sell):
                flags.append(f"non_numeric_buy_sell:{name}")
                continue
            net = buy - sell
            low = name.lower()
            seen.add(name)
            if "foreign" in low:
                foreign += net
            elif "investment" in low or "trust" in low:
                trust += net
            elif "dealer" in low:
                dealer += net
        if available is None:
            flags.append("missing_calendar")
        if not seen:
            flags.append("no_investor_category")
        out.append(
            {
                "symbol": symbol,
                "stock_id": symbol.replace("TW", ""),
                "trade_date": trade_day.strftime("%Y-%m-%d") if trade_day is not None else str(date),
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
            }
        )
    return out


def margin_normalize(raw_rows: list[dict[str, Any]], symbol: str, fetched_at: str, snapshot_id: str, nxt: dict[pd.Timestamp, pd.Timestamp]) -> list[dict[str, Any]]:
    raw = pd.DataFrame(raw_rows)
    if raw.empty or "date" not in raw:
        return []
    out: list[dict[str, Any]] = []
    for _, row in raw.sort_values("date").iterrows():
        trade_day = to_day(row.get("date"))
        available = nxt.get(trade_day) if trade_day is not None else None
        margin_today = num(row, "MarginPurchaseTodayBalance")
        margin_yesterday = num(row, "MarginPurchaseYesterdayBalance")
        short_today = num(row, "ShortSaleTodayBalance")
        short_yesterday = num(row, "ShortSaleYesterdayBalance")
        flags = []
        for col, value in [
            ("MarginPurchaseTodayBalance", margin_today),
            ("MarginPurchaseYesterdayBalance", margin_yesterday),
            ("ShortSaleTodayBalance", short_today),
            ("ShortSaleYesterdayBalance", short_yesterday),
        ]:
            if not math.isfinite(value):
                flags.append(f"missing_or_non_numeric:{col}")
        if available is None:
            flags.append("missing_calendar")
        out.append(
            {
                "symbol": symbol,
                "stock_id": symbol.replace("TW", ""),
                "trade_date": trade_day.strftime("%Y-%m-%d") if trade_day is not None else str(row.get("date")),
                "available_at": available.strftime("%Y-%m-%d") if available is not None else "",
                "margin_balance": margin_today if math.isfinite(margin_today) else "",
                "margin_balance_change": margin_today - margin_yesterday if math.isfinite(margin_today) and math.isfinite(margin_yesterday) else "",
                "short_balance": short_today if math.isfinite(short_today) else "",
                "short_balance_change": short_today - short_yesterday if math.isfinite(short_today) and math.isfinite(short_yesterday) else "",
                "data_source": f"FinMind:{CATEGORIES['margin_short']}",
                "source_url_or_endpoint": FINMIND_URL,
                "raw_snapshot_id": snapshot_id,
                "fetched_at": fetched_at,
                "quality_flags": ";".join(sorted(set(flags))),
            }
        )
    return out


def classify_available_at(combined: dict[str, pd.DataFrame], control_dates: list[pd.Timestamp]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    nxt = next_trading_map(control_dates)
    summary_rows: list[dict[str, Any]] = []
    detail_rows: list[dict[str, Any]] = []
    for category, df in combined.items():
        work = df.copy()
        work["trade_date_ts"] = pd.to_datetime(work["trade_date"], errors="coerce")
        work["available_at_ts"] = pd.to_datetime(work["available_at"], errors="coerce")
        work["next_trading_day"] = work["trade_date_ts"].map(nxt)
        work["delta_days"] = (work["available_at_ts"] - work["next_trading_day"]).dt.days
        work["lt_next_trading_day"] = work["available_at_ts"] < work["next_trading_day"]
        work["exact"] = work["available_at_ts"] == work["next_trading_day"]
        work["delayed"] = work["available_at_ts"] > work["next_trading_day"]
        work["same_or_before_trade"] = work["available_at_ts"] <= work["trade_date_ts"]
        work["prohibited_early"] = work["same_or_before_trade"]
        work["missing_calendar"] = work["next_trading_day"].isna() | work["available_at_ts"].isna()
        work["reason"] = "exact_t1"
        work.loc[work["missing_calendar"], "reason"] = "missing_calendar"
        work.loc[work["lt_next_trading_day"] & ~work["same_or_before_trade"], "reason"] = "calendar_gap"
        work.loc[work["same_or_before_trade"], "reason"] = "data_quality_unknown"
        work.loc[work["delayed"], "reason"] = "delayed_source"
        delay_by_symbol = work[work["delayed"]].groupby("symbol").size().to_dict()
        # Large symbol-level delayed blocks are generally listing/status-calendar gaps.
        work.loc[work["delayed"] & work["symbol"].map(delay_by_symbol).fillna(0).ge(20), "reason"] = "listing_status_gap"
        work.loc[work["delayed"] & work["symbol"].map(delay_by_symbol).fillna(0).lt(20), "reason"] = "calendar_gap"
        counts = Counter(work["reason"].astype(str))
        summary_rows.append(
            {
                "category": category,
                "rows": int(len(work)),
                "rows_with_next_trading_day": int(work["next_trading_day"].notna().sum()),
                "available_at_lt_next_trading_day_rows": int(work["lt_next_trading_day"].fillna(False).sum()),
                "prohibited_early_visible_rows": int(work["prohibited_early"].fillna(False).sum()),
                "same_or_before_trade_date_rows": int(work["same_or_before_trade"].fillna(False).sum()),
                "exact_t1_rows": int(work["exact"].fillna(False).sum()),
                "delayed_rows": int(work["delayed"].fillna(False).sum()),
                "missing_calendar_rows": int(work["missing_calendar"].fillna(False).sum()),
                "max_delay_days": int(work["delta_days"].max()) if work["delta_days"].notna().any() else "",
                "reason_counts": "|".join(f"{key}:{counts[key]}" for key in sorted(counts)),
                "pit_safe_delayed_pass": "yes"
                if int(work["prohibited_early"].fillna(False).sum()) == 0
                else "no",
            }
        )
        sample = work[work["reason"] != "exact_t1"].head(300)
        for row in sample.itertuples():
            detail_rows.append(
                {
                    "category": category,
                    "symbol": row.symbol,
                    "trade_date": str(row.trade_date)[:10],
                    "next_trading_day": "" if pd.isna(row.next_trading_day) else str(row.next_trading_day)[:10],
                    "available_at": str(row.available_at)[:10],
                    "delta_days": "" if pd.isna(row.delta_days) else int(row.delta_days),
                    "available_at_lt_next_trading_day": bool(row.lt_next_trading_day),
                    "available_at_eq_next_trading_day": bool(row.exact),
                    "available_at_gt_next_trading_day": bool(row.delayed),
                    "prohibited_early_visible": bool(row.prohibited_early),
                    "reason": row.reason,
                }
            )
    return summary_rows, detail_rows


def coverage_for(category: str, df: pd.DataFrame, control: pd.DataFrame) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for symbol, group in control.groupby("instrument"):
        expected = set(group["date"].astype(str))
        rows = df[df["symbol"] == symbol] if not df.empty else pd.DataFrame()
        valid = rows[rows["available_at"].fillna("").astype(str).ne("")] if not rows.empty else pd.DataFrame()
        dates = set(valid["trade_date"].astype(str)) if not valid.empty else set()
        out[symbol] = {
            "category": category,
            "symbol": symbol,
            "expected_control_dates": len(expected),
            "covered_control_dates": len(expected & dates),
            "coverage_rate": round(len(expected & dates) / len(expected), 6) if expected else 0.0,
            "raw_rows": int(len(rows)),
            "pit_valid_rows": int(len(valid)),
            "missing_control_dates": len(expected - dates),
        }
    return out



def load_existing_o1r_rows() -> tuple[dict[str, list[dict[str, Any]]], list[dict[str, Any]], list[dict[str, Any]]]:
    fetched_rows: dict[str, list[dict[str, Any]]] = {category: [] for category in CATEGORIES}
    attempts: list[dict[str, Any]] = []
    manifest_rows: list[dict[str, Any]] = []
    for category in CATEGORIES:
        for norm_path in sorted((RAW_DIR / category).glob("phaseo1r_*_normalized.csv")):
            match = re.match(rf"phaseo1r_{category}_(TW\d+)_.*_normalized\.csv", norm_path.name)
            symbol = match.group(1) if match else ""
            raw_path = norm_path.with_name(norm_path.name.replace("_normalized.csv", "_raw_response.jsonl"))
            rows = pd.read_csv(norm_path).to_dict("records") if norm_path.exists() and norm_path.stat().st_size else []
            fetched_rows[category].extend(rows)
            attempts.append(
                {
                    "category": category,
                    "symbol": symbol,
                    "stock_id": symbol.replace("TW", ""),
                    "start_date": "2022-01-01",
                    "end_date": "2026-06-10",
                    "request_started_at": "reused_existing_o1r_archive",
                    "request_finished_at": "reused_existing_o1r_archive",
                    "status": "success" if rows else "empty_reused_archive",
                    "http_status": "",
                    "finmind_status": "",
                    "raw_row_count": sum(1 for _ in raw_path.open(encoding="utf-8")) if raw_path.exists() else "",
                    "normalized_row_count": len(rows),
                    "error_type": "",
                    "error_message": "",
                    "token_used": False,
                    "scrapling_used": False,
                    "raw_path": rel(raw_path),
                    "normalized_path": rel(norm_path),
                }
            )
            manifest_rows.append(
                {
                    "raw_snapshot_id": norm_path.name.replace("_normalized.csv", ""),
                    "category": category,
                    "symbol": symbol,
                    "data_source": f"FinMind:{CATEGORIES[category]}",
                    "source_endpoint": FINMIND_URL,
                    "fetched_at": "reused_existing_o1r_archive",
                    "raw_row_count": attempts[-1]["raw_row_count"],
                    "normalized_row_count": len(rows),
                    "first_trade_date": min((str(row.get("trade_date", "")) for row in rows), default=""),
                    "last_trade_date": max((str(row.get("trade_date", "")) for row in rows), default=""),
                    "available_at_contract": "reused O1R normalized archive; O1R recommends PIT-safe delayed availability for combined archive",
                    "raw_path": rel(raw_path),
                    "normalized_path": rel(norm_path),
                    "raw_checksum_or_size": sha256_size(raw_path) if raw_path.exists() else "",
                    "normalized_checksum_or_size": sha256_size(norm_path) if norm_path.exists() else "",
                }
            )
    return fetched_rows, attempts, manifest_rows

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", default="2022-01-01")
    parser.add_argument("--end", default="2026-06-10")
    parser.add_argument("--sleep", type=float, default=0.15)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--reuse-existing", action="store_true")
    args = parser.parse_args()

    generated_at = utc_now()
    token, token_source = read_token()
    control = load_control()
    control_symbols = sorted(control["instrument"].astype(str).unique())
    control_dates = pd.to_datetime(control["date"], errors="coerce").dropna().tolist()
    nxt = next_trading_map(control_dates)

    existing = {category: pd.read_csv(path) for category, path in PHASE0E_NORMALIZED.items()}
    before_cov = {category: coverage_for(category, df, control) for category, df in existing.items()}
    absent_by_category = {
        category: [symbol for symbol in control_symbols if before_cov[category][symbol]["raw_rows"] == 0]
        for category in CATEGORIES
    }

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    if args.reuse_existing:
        fetched_rows, attempts, manifest_rows = load_existing_o1r_rows()
    else:
        fetched_rows: dict[str, list[dict[str, Any]]] = {category: [] for category in CATEGORIES}
        attempts: list[dict[str, Any]] = []
        manifest_rows: list[dict[str, Any]] = []

    if not args.reuse_existing:
        for category, symbols in absent_by_category.items():
            for symbol in symbols:
                started = utc_now()
                raw_rows, status = request_finmind(category, symbol.replace("TW", ""), args.start, args.end, args.timeout, token)
                finished = utc_now()
                snapshot_id = f"phaseo1r_{category}_{symbol}_{started.replace('-', '').replace(':', '').replace('+00:00', 'Z')}"
                raw_path = RAW_DIR / category / f"{snapshot_id}_raw_response.jsonl"
                norm_path = RAW_DIR / category / f"{snapshot_id}_normalized.csv"
                raw_path.parent.mkdir(parents=True, exist_ok=True)
                with raw_path.open("w", encoding="utf-8") as fh:
                    for row in raw_rows:
                        fh.write(json.dumps(row, ensure_ascii=True, default=str) + "\n")
                if category == "institutional_flow":
                    normalized = institutional_normalize(raw_rows, symbol, started, snapshot_id, nxt)
                else:
                    normalized = margin_normalize(raw_rows, symbol, started, snapshot_id, nxt)
                write_csv(norm_path, normalized)
                fetched_rows[category].extend(normalized)
                attempts.append(
                    {
                        "category": category,
                        "symbol": symbol,
                        "stock_id": symbol.replace("TW", ""),
                        "start_date": args.start,
                        "end_date": args.end,
                        "request_started_at": started,
                        "request_finished_at": finished,
                        "status": status["status"],
                        "http_status": status["http_status"],
                        "finmind_status": status["finmind_status"],
                        "raw_row_count": len(raw_rows),
                        "normalized_row_count": len(normalized),
                        "error_type": status["error_type"],
                        "error_message": status["error_message"],
                        "token_used": status["token_used"],
                        "scrapling_used": False,
                        "raw_path": rel(raw_path),
                        "normalized_path": rel(norm_path),
                    }
                )
                manifest_rows.append(
                    {
                        "raw_snapshot_id": snapshot_id,
                        "category": category,
                        "symbol": symbol,
                        "data_source": f"FinMind:{CATEGORIES[category]}",
                        "source_endpoint": FINMIND_URL,
                        "fetched_at": started,
                        "raw_row_count": len(raw_rows),
                        "normalized_row_count": len(normalized),
                        "first_trade_date": min((row.get("trade_date", "") for row in normalized), default=""),
                        "last_trade_date": max((row.get("trade_date", "") for row in normalized), default=""),
                        "available_at_contract": "available_at = next_trading_day(trade_date) for O1R fetched normalization; O1R recommends PIT-safe delayed availability for combined archive",
                        "raw_path": rel(raw_path),
                        "normalized_path": rel(norm_path),
                        "raw_checksum_or_size": sha256_size(raw_path),
                        "normalized_checksum_or_size": sha256_size(norm_path) if norm_path.exists() else "",
                    }
                )
                if args.sleep:
                    time.sleep(args.sleep)

    combined: dict[str, pd.DataFrame] = {}
    for category, df in existing.items():
        add = pd.DataFrame(fetched_rows[category])
        combined[category] = pd.concat([df, add], ignore_index=True, sort=False) if not add.empty else df.copy()

    after_cov = {category: coverage_for(category, df, control) for category, df in combined.items()}
    cov_rows: list[dict[str, Any]] = []
    for category in CATEGORIES:
        for symbol in control_symbols:
            before = before_cov[category][symbol]
            after = after_cov[category][symbol]
            cov_rows.append(
                {
                    "category": category,
                    "symbol": symbol,
                    "before_raw_rows": before["raw_rows"],
                    "after_raw_rows": after["raw_rows"],
                    "before_coverage_rate": before["coverage_rate"],
                    "after_coverage_rate": after["coverage_rate"],
                    "coverage_delta": round(after["coverage_rate"] - before["coverage_rate"], 6),
                    "before_missing_control_dates": before["missing_control_dates"],
                    "after_missing_control_dates": after["missing_control_dates"],
                    "fetch_attempted": symbol in absent_by_category[category],
                    "fetch_success": any(
                        row["category"] == category and row["symbol"] == symbol and row["status"] == "success" for row in attempts
                    ),
                }
            )

    error_summary = []
    attempts_df = pd.DataFrame(attempts)
    if not attempts_df.empty:
        for (category, status, error_type), group in attempts_df.groupby(["category", "status", "error_type"], dropna=False):
            error_summary.append(
                {
                    "category": category,
                    "status": status,
                    "error_type": error_type,
                    "count": int(len(group)),
                    "symbols": "|".join(group["symbol"].astype(str).head(80)),
                }
            )

    avail_summary, avail_details = classify_available_at(combined, control_dates)
    after_summary_rows = []
    for category in CATEGORIES:
        rows = [row for row in cov_rows if row["category"] == category]
        after_summary_rows.append(
            {
                "category": category,
                "control_symbol_count": len(control_symbols),
                "before_symbols_with_rows": sum(1 for row in rows if int(row["before_raw_rows"]) > 0),
                "after_symbols_with_rows": sum(1 for row in rows if int(row["after_raw_rows"]) > 0),
                "absent_before": sum(1 for row in rows if int(row["before_raw_rows"]) == 0),
                "absent_after": sum(1 for row in rows if int(row["after_raw_rows"]) == 0),
                "low_coverage_after_lt_0_95": sum(1 for row in rows if float(row["after_coverage_rate"]) < 0.95),
                "min_after_coverage_rate": min(float(row["after_coverage_rate"]) for row in rows),
                "median_after_coverage_rate": float(pd.Series([row["after_coverage_rate"] for row in rows]).median()),
            }
        )

    early_rows = sum(int(row["prohibited_early_visible_rows"]) for row in avail_summary)
    absent_after = sum(int(row["absent_after"]) for row in after_summary_rows)
    recommendation = "pit_safe_delayed_availability"
    gate = "phase_o1r_needs_user_confirmation_for_delayed_availability_contract"
    if early_rows > 0 or absent_after > 0:
        gate = "phase_o1r_not_passed_continue_repair"
    elif all(int(row["delayed_rows"]) == 0 and int(row["missing_calendar_rows"]) == 0 for row in avail_summary):
        recommendation = "exact_t1"
        gate = "phase_o1r_passed_allow_o2_exact_t1"

    summary = {
        "created_at": generated_at,
        "phase": "phase_o1r_coverage_available_at_repair",
        "gate": gate,
        "recommended_available_at_contract": recommendation,
        "control_symbol_count": len(control_symbols),
        "network_fetch_executed": bool(list(RAW_DIR.glob("*/*_raw_response.jsonl"))) or not args.reuse_existing,
        "final_refresh_reused_existing_archive": bool(args.reuse_existing),
        "token_used": bool(token),
        "token_source": token_source if token else "none",
        "scrapling_used": False,
        "datasets": CATEGORIES,
        "coverage_summary": after_summary_rows,
        "available_at_summary": avail_summary,
        "no_training": True,
        "no_replay": True,
        "no_treatment_sample": True,
        "no_control_change": True,
        "no_frontend_api_provider_accepted_latest_monitor_trading": True,
    }

    write_csv(OUT / "absent_symbol_fetch_attempts.csv", attempts)
    write_csv(OUT / "coverage_before_after.csv", cov_rows)
    write_csv(OUT / "fetch_error_summary.csv", error_summary)
    write_csv(OUT / "raw_archive_manifest.csv", manifest_rows)
    write_csv(OUT / "available_at_contract_audit.csv", avail_summary)
    write_csv(OUT / "available_at_mismatch_classification.csv", avail_details)
    write_csv(OUT / "coverage_after_summary.csv", after_summary_rows)
    write_json(OUT / "phaseo1r_summary.json", summary)

    report_lines = [
        "# Phase O1R 执行报告：覆盖与 available_at 合同修复",
        "",
        f"生成时间：`{generated_at}`",
        "",
        "## 1. 执行摘要",
        "",
        "本轮只处理 Phase1C control 150 股的法人筹码与融资融券覆盖，以及 `exact T+1` vs `PIT-safe delayed availability` 合同审计。",
        "",
        "推荐 gate：",
        "",
        "```text",
        gate,
        "```",
        "",
        f"推荐 available_at 合同：`{recommendation}`。",
        "",
        "## 2. 边界",
        "",
        "- 未训练 qlib/LTR。",
        "- 未回放，不做收益率优劣证明。",
        "- 未构建 treatment sample。",
        "- 未修改 Phase1C control。",
        "- 未触发 frontend/API/provider/accepted latest/monitor/交易链路。",
        "- 未引入月营收或其他数据源。",
        "",
        "## 3. 联网与 token/scrapling",
        "",
        f"- 是否联网拉取：`{bool(list(RAW_DIR.glob("*/*_raw_response.jsonl"))) or not args.reuse_existing}`。",
        f"- final_refresh_reused_existing_archive：`{bool(args.reuse_existing)}`。",
        f"- token_used：`{bool(token)}`。",
        f"- token_source：`{token_source if token else 'none'}`。",
        "- scrapling_used：`false`。",
        f"- endpoint：`{FINMIND_URL}`。",
        "",
        "## 4. 使用数据集",
        "",
        "- `TaiwanStockInstitutionalInvestorsBuySell`",
        "- `TaiwanStockMarginPurchaseShortSale`",
        "",
        "## 5. 150 个 control symbols 覆盖前后对比",
        "",
        *md_table(
            after_summary_rows,
            [
                "category",
                "control_symbol_count",
                "before_symbols_with_rows",
                "after_symbols_with_rows",
                "absent_before",
                "absent_after",
                "low_coverage_after_lt_0_95",
                "min_after_coverage_rate",
                "median_after_coverage_rate",
            ],
        ),
        "",
        "## 6. Absent symbols 补齐结果",
        "",
        *md_table(
            attempts,
            ["category", "symbol", "status", "raw_row_count", "normalized_row_count", "error_type", "token_used", "scrapling_used"],
            limit=100,
        ),
        "",
        "## 7. 低覆盖 symbols 列表",
        "",
        *md_table(
            sorted([row for row in cov_rows if float(row["after_coverage_rate"]) < 0.95], key=lambda row: (row["category"], row["after_coverage_rate"]))[:80],
            [
                "category",
                "symbol",
                "before_coverage_rate",
                "after_coverage_rate",
                "after_raw_rows",
                "after_missing_control_dates",
                "fetch_attempted",
                "fetch_success",
            ],
            limit=80,
        ),
        "",
        "## 8. available_at mismatch 分类",
        "",
        *md_table(
            avail_summary,
            [
                "category",
                "rows",
                "available_at_lt_next_trading_day_rows",
                "prohibited_early_visible_rows",
                "same_or_before_trade_date_rows",
                "exact_t1_rows",
                "delayed_rows",
                "missing_calendar_rows",
                "max_delay_days",
                "reason_counts",
                "pit_safe_delayed_pass",
            ],
        ),
        "",
        "## 9. 是否存在提前可见行",
        "",
        f"- `available_at <= trade_date` prohibited early-visible rows：`{early_rows}`。",
        "- `available_at <= trade_date` rows 见 `available_at_contract_audit.csv`；若非零则不得进入 O2。",
        "",
        "## 10. 合同建议",
        "",
        "O1R 不建议继续使用 strict exact T+1 作为唯一合同，因为 combined archive 中存在 delayed availability / listing_status_gap / calendar_gap 行。",
        "",
        "建议采用：",
        "",
        "```text",
        "available_at >= next_trading_day(trade_date)",
        "```",
        "",
        "后续 O2 必须保留 `delay_days` 与 `delay_reason`，并按真实 `available_at` 做 as-of join；不得把 delayed availability 静默当作 exact T+1，也不得人工提前 `available_at`。",
        "",
        "## 11. 是否允许进入 O2",
        "",
        f"- 当前执行建议：`{gate}`。",
        "- 如审查者接受 PIT-safe delayed availability 合同，且确认低覆盖行只能 neutral fill + missing flag，不删行，则可进入 O2。",
        "- 如必须坚持 exact T+1，则本轮不通过，需要继续修复日历/上市状态或剔除不满足合同的数据族。",
        "",
        "## 12. 是否触发用户确认",
        "",
        "- 是。available_at 合同从 `exact T+1` 调整为 `PIT-safe delayed availability` 属于主线合同选择，必须用户/审查确认。",
        "",
        "## 13. 输出产物",
        "",
        f"- `{rel(OUT / 'absent_symbol_fetch_attempts.csv')}`",
        f"- `{rel(OUT / 'coverage_before_after.csv')}`",
        f"- `{rel(OUT / 'fetch_error_summary.csv')}`",
        f"- `{rel(OUT / 'raw_archive_manifest.csv')}`",
        f"- `{rel(OUT / 'available_at_contract_audit.csv')}`",
        f"- `{rel(OUT / 'available_at_mismatch_classification.csv')}`",
        f"- `{rel(OUT / 'coverage_after_summary.csv')}`",
        f"- `{rel(OUT / 'phaseo1r_summary.json')}`",
    ]
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    print(json.dumps({"ok": True, "gate": gate, "report": rel(REPORT), "summary": rel(OUT / "phaseo1r_summary.json")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
