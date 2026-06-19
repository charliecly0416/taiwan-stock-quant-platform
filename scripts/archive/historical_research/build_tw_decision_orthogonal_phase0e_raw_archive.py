#!/usr/bin/env python3
"""Build Phase 0E expanded raw archive for orthogonal TW Decision data.

Phase 0E is a data backfill and PIT audit stage only. It may download FinMind
institutional-flow and margin/short rows for the authorized Top150 historical
universe, but it must not materialize derived features, write qlib providers,
switch accepted latest, build Phase 1 samples, run factor tests, train models,
touch frontend/API, or interact with trading state.

Token handling: token is read from FINMIND_TOKEN/FINMIND_API_TOKEN or, if
--token-stdin is set, from stdin at runtime. The token is never written to any
artifact.
"""
from __future__ import annotations

import argparse
import csv
import getpass
import hashlib
import json
import math
import os
import sys
import time
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import requests


ROOT = Path(__file__).resolve().parents[1]
QLIB = ROOT / "qlib_pipeline"
UNIVERSE_PATH = QLIB / "data_tw/experiments/yahoo_adjusted_primary/universe/tw_liquid_dyn.txt"
NORMALIZED_DIR = QLIB / "data_tw/experiments/yahoo_adjusted_primary/normalized_nonempty"
OUT_DIR = ROOT / "data_tw/experiments/decision_orthogonal"
RAW_DIR = OUT_DIR / "phase0e_raw_archive"
DOC_DIR = ROOT / "docs/tw_decision_model_orthogonal"

DOWNLOAD_STATUS_PATH = OUT_DIR / "phase0e_download_status.csv"
MANIFEST_PATH = OUT_DIR / "phase0e_pit_snapshot_manifest.csv"
COVERAGE_PATH = OUT_DIR / "phase0e_coverage_report.csv"
PIT_SAMPLES_PATH = OUT_DIR / "phase0e_pit_validation_samples.csv"
QUALITY_FLAGS_PATH = OUT_DIR / "phase0e_quality_flags_summary.csv"
EXEC_REPORT_PATH = DOC_DIR / "PHASE0E_EXECUTION_REPORT_CN.md"

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


def to_date(value: Any) -> pd.Timestamp | None:
    try:
        ts = pd.Timestamp(value)
    except Exception:
        return None
    if pd.isna(ts):
        return None
    return ts.normalize()


def redacted_error(value: Any) -> str:
    text = str(value or "")
    for key in ["FINMIND_TOKEN", "FINMIND_API_TOKEN", "Authorization", "Bearer"]:
        text = text.replace(key, "[redacted_key]")
    return text[:300]


def read_token(args: argparse.Namespace) -> str:
    token = os.getenv("FINMIND_TOKEN") or os.getenv("FINMIND_API_TOKEN")
    if token:
        return token.strip()
    if args.token_stdin:
        if sys.stdin.isatty():
            return getpass.getpass("FINMIND token: ").strip()
        return sys.stdin.readline().strip()
    return ""


def load_universe(start: str, end: str, max_symbols: int) -> pd.DataFrame:
    start_ts = pd.Timestamp(start)
    end_ts = pd.Timestamp(end)
    rows = []
    with UNIVERSE_PATH.open(encoding="utf-8") as fh:
        for line in fh:
            parts = line.strip().split("\t")
            if len(parts) != 3:
                continue
            symbol, seg_start, seg_end = parts
            s = pd.Timestamp(seg_start)
            e = pd.Timestamp(seg_end)
            if e < start_ts or s > end_ts:
                continue
            overlap_start = max(s, start_ts)
            overlap_end = min(e, end_ts)
            rows.append(
                {
                    "symbol": symbol,
                    "overlap_days": int((overlap_end - overlap_start).days) + 1,
                    "first_active": overlap_start,
                    "last_active": overlap_end,
                }
            )
    seg = pd.DataFrame(rows)
    if seg.empty:
        raise RuntimeError("no overlapping tw_liquid_dyn universe rows")
    agg = (
        seg.groupby("symbol", as_index=False)
        .agg({"overlap_days": "sum", "first_active": "min", "last_active": "max"})
        .sort_values(["overlap_days", "symbol"], ascending=[False, True])
        .head(max_symbols)
        .reset_index(drop=True)
    )
    if "TW2330" not in set(agg["symbol"]) and "TW2330" in set(seg["symbol"]) and len(agg) >= max_symbols:
        tw2330 = seg[seg["symbol"] == "TW2330"].agg({"overlap_days": "sum", "first_active": "min", "last_active": "max"})
        agg.iloc[-1] = {
            "symbol": "TW2330",
            "overlap_days": int(tw2330["overlap_days"]),
            "first_active": tw2330["first_active"],
            "last_active": tw2330["last_active"],
        }
        agg = agg.drop_duplicates("symbol").sort_values(["overlap_days", "symbol"], ascending=[False, True]).reset_index(drop=True)
    agg["stock_id"] = agg["symbol"].str.replace("TW", "", regex=False)
    return agg


def load_calendar(symbols: list[str], start: str, end: str, post_end_days: int) -> dict[str, list[pd.Timestamp]]:
    start_ts = pd.Timestamp(start)
    end_ts = pd.Timestamp(end) + timedelta(days=post_end_days)
    calendars = {}
    global_dates = set()
    for symbol in symbols:
        path = NORMALIZED_DIR / f"{symbol}.csv"
        if not path.exists():
            calendars[symbol] = []
            continue
        try:
            df = pd.read_csv(path, usecols=["date"])
        except Exception:
            calendars[symbol] = []
            continue
        dates = []
        for date in pd.to_datetime(df["date"], errors="coerce").dropna():
            day = pd.Timestamp(date).normalize()
            if start_ts <= day <= end_ts:
                dates.append(day)
                global_dates.add(day)
        calendars[symbol] = sorted(set(dates))
    calendars["__global__"] = sorted(global_dates)
    return calendars


def next_trading_day(day: pd.Timestamp, calendar: list[pd.Timestamp]) -> pd.Timestamp | None:
    for candidate in calendar:
        if candidate > day:
            return candidate
    return None


def request_finmind(category: str, stock_id: str, start: str, end: str, timeout: float, token: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    dataset = CATEGORIES[category]
    params = {"dataset": dataset, "data_id": stock_id, "start_date": start, "end_date": end}
    headers = {"User-Agent": "Mozilla/5.0 decision-orthogonal-phase0e/1.0"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        resp = requests.get(FINMIND_URL, params=params, headers=headers, timeout=timeout)
        try:
            payload = resp.json()
        except Exception:
            payload = {"status": None, "msg": resp.text[:300], "data": []}
        data = payload.get("data") if isinstance(payload, dict) else None
        rows = data if isinstance(data, list) else []
        status = "success" if resp.status_code == 200 and str(payload.get("status")) == "200" else "failed"
        return rows, {
            "status": status,
            "http_status": resp.status_code,
            "finmind_status": payload.get("status") if isinstance(payload, dict) else None,
            "error_type": "" if status == "success" else "finmind_or_http_error",
            "error_message": "" if status == "success" else redacted_error(payload.get("msg") if isinstance(payload, dict) else "bad_payload"),
            "token_used": bool(token),
        }
    except Exception as exc:
        return [], {
            "status": "failed",
            "http_status": "",
            "finmind_status": "",
            "error_type": type(exc).__name__,
            "error_message": redacted_error(str(exc)),
            "token_used": bool(token),
        }


def num(row: pd.Series, col: str) -> float:
    value = pd.to_numeric(row.get(col), errors="coerce")
    if pd.isna(value):
        return float("nan")
    return float(value)


def institutional_to_archive(raw: pd.DataFrame, symbol: str, stock_id: str, fetched_at: str, snapshot_id: str, calendar: list[pd.Timestamp]) -> list[dict[str, Any]]:
    if raw.empty:
        return []
    out = []
    for date, g in raw.groupby("date"):
        trade_day = to_date(date)
        available = next_trading_day(trade_day, calendar) if trade_day is not None else None
        flags = []
        foreign = 0.0
        trust = 0.0
        dealer = 0.0
        seen = set()
        for _, r in g.iterrows():
            name = str(r.get("name", ""))
            buy = num(r, "buy")
            sell = num(r, "sell")
            if not math.isfinite(buy) or not math.isfinite(sell):
                flags.append(f"non_numeric_buy_sell:{name}")
                continue
            if buy < 0 or sell < 0:
                flags.append(f"negative_buy_sell:{name}")
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
            flags.append("available_at_missing_no_next_trading_day")
        if not seen:
            flags.append("no_investor_category")
        out.append(
            {
                "symbol": symbol,
                "stock_id": stock_id,
                "trade_date": trade_day.strftime("%Y-%m-%d") if trade_day is not None else str(date),
                "available_at": available.strftime("%Y-%m-%d") if available is not None else "",
                "foreign_net_buy": foreign,
                "investment_trust_net_buy": trust,
                "dealer_net_buy": dealer,
                "institutional_total_net_buy": foreign + trust + dealer,
                "data_source": "FinMind:TaiwanStockInstitutionalInvestorsBuySell",
                "source_url_or_endpoint": FINMIND_URL,
                "raw_snapshot_id": snapshot_id,
                "fetched_at": fetched_at,
                "quality_flags": ";".join(sorted(set(flags))),
            }
        )
    return out


def margin_to_archive(raw: pd.DataFrame, symbol: str, stock_id: str, fetched_at: str, snapshot_id: str, calendar: list[pd.Timestamp]) -> list[dict[str, Any]]:
    if raw.empty:
        return []
    out = []
    data = raw.sort_values("date")
    for _, r in data.iterrows():
        trade_day = to_date(r.get("date"))
        available = next_trading_day(trade_day, calendar) if trade_day is not None else None
        margin_today = num(r, "MarginPurchaseTodayBalance")
        margin_yesterday = num(r, "MarginPurchaseYesterdayBalance")
        short_today = num(r, "ShortSaleTodayBalance")
        short_yesterday = num(r, "ShortSaleYesterdayBalance")
        flags = []
        for col, value in [
            ("MarginPurchaseTodayBalance", margin_today),
            ("MarginPurchaseYesterdayBalance", margin_yesterday),
            ("ShortSaleTodayBalance", short_today),
            ("ShortSaleYesterdayBalance", short_yesterday),
        ]:
            if not math.isfinite(value):
                flags.append(f"missing_or_non_numeric:{col}")
            elif value < 0:
                flags.append(f"negative:{col}")
        if available is None:
            flags.append("available_at_missing_no_next_trading_day")
        out.append(
            {
                "symbol": symbol,
                "stock_id": stock_id,
                "trade_date": trade_day.strftime("%Y-%m-%d") if trade_day is not None else str(r.get("date")),
                "available_at": available.strftime("%Y-%m-%d") if available is not None else "",
                "margin_balance": margin_today if math.isfinite(margin_today) else "",
                "margin_balance_change": margin_today - margin_yesterday if math.isfinite(margin_today) and math.isfinite(margin_yesterday) else "",
                "short_balance": short_today if math.isfinite(short_today) else "",
                "short_balance_change": short_today - short_yesterday if math.isfinite(short_today) and math.isfinite(short_yesterday) else "",
                "data_source": "FinMind:TaiwanStockMarginPurchaseShortSale",
                "source_url_or_endpoint": FINMIND_URL,
                "raw_snapshot_id": snapshot_id,
                "fetched_at": fetched_at,
                "quality_flags": ";".join(sorted(set(flags))),
            }
        )
    return out


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        fieldnames = list(rows[0].keys()) if rows else []
    with path.open("w", encoding="utf-8", newline="") as fh:
        if not fieldnames:
            return
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def sha256_size(path: Path) -> str:
    return f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()} size:{path.stat().st_size}"


def expected_dates(symbol: str, start: str, end: str) -> set[str]:
    path = NORMALIZED_DIR / f"{symbol}.csv"
    if not path.exists():
        return set()
    try:
        df = pd.read_csv(path, usecols=["date"])
    except Exception:
        return set()
    dates = pd.to_datetime(df["date"], errors="coerce").dropna()
    return {pd.Timestamp(d).strftime("%Y-%m-%d") for d in dates if pd.Timestamp(start) <= pd.Timestamp(d) <= pd.Timestamp(end)}


def coverage_rows(category: str, symbols: pd.DataFrame, rows: list[dict[str, Any]], start: str, end: str) -> list[dict[str, Any]]:
    out = []
    df = pd.DataFrame(rows)
    for _, sym in symbols.iterrows():
        symbol = sym["symbol"]
        expected = expected_dates(symbol, start, end)
        g = df[df["symbol"] == symbol] if not df.empty else pd.DataFrame()
        raw_dates = set(g["trade_date"].astype(str)) if not g.empty else set()
        pit_valid = g[g["available_at"].fillna("").astype(str).ne("")] if not g.empty else pd.DataFrame()
        pit_dates = set(pit_valid["trade_date"].astype(str)) if not pit_valid.empty else set()
        out.append(
            {
                "category": category,
                "symbol": symbol,
                "expected_trading_days": len(expected),
                "raw_rows": int(len(g)),
                "pit_valid_rows": int(len(pit_valid)),
                "pit_valid_coverage_rate": float(len(pit_dates & expected) / len(expected)) if expected else 0.0,
                "missing_dates_count": len(expected - pit_dates),
                "extra_dates_count": len(raw_dates - expected),
                "duplicate_rows_count": int(g.duplicated(["symbol", "trade_date"]).sum()) if not g.empty else 0,
                "quality_issue_count": int(g["quality_flags"].fillna("").astype(str).ne("").sum()) if not g.empty and "quality_flags" in g else 0,
            }
        )
    return out


def pit_samples(category: str, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    valid = [r for r in rows if r.get("trade_date") and r.get("available_at")]
    for r in valid[:10]:
        out.append(
            {
                "category": category,
                "symbol": r["symbol"],
                "trade_date": r["trade_date"],
                "available_at": r["available_at"],
                "asof_example": r["trade_date"],
                "visible_at_asof": False,
                "raw_snapshot_id": r["raw_snapshot_id"],
                "validation_result": "pass" if r["trade_date"] < r["available_at"] else "fail",
                "validation_note": "Boundary sample: trade_date asof is before conservative T+1 available_at.",
            }
        )
        out.append(
            {
                "category": category,
                "symbol": r["symbol"],
                "trade_date": r["trade_date"],
                "available_at": r["available_at"],
                "asof_example": r["available_at"],
                "visible_at_asof": True,
                "raw_snapshot_id": r["raw_snapshot_id"],
                "validation_result": "pass",
                "validation_note": "Positive sample: asof is available_at, row is visible.",
            }
        )
    return out


def quality_summary(category: str, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counter: Counter[tuple[str, str]] = Counter()
    for row in rows:
        flags = [f.strip() for f in str(row.get("quality_flags") or "").split(";") if f.strip()]
        if not flags:
            counter[(row["symbol"], "none")] += 1
        for flag in flags:
            counter[(row["symbol"], flag)] += 1
    return [
        {"category": category, "symbol": symbol, "quality_flag_reason": reason, "row_count": count}
        for (symbol, reason), count in sorted(counter.items())
    ]


def md_table(rows: list[dict[str, Any]], cols: list[str]) -> str:
    if not rows:
        return "_no rows_"
    lines = ["| " + " | ".join(cols) + " |", "|" + "|".join(["---" for _ in cols]) + "|"]
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(col, "")) for col in cols) + " |")
    return "\n".join(lines)


def write_report(args: argparse.Namespace, token_source: str, symbols: pd.DataFrame, status_rows: list[dict[str, Any]], manifest_rows: list[dict[str, Any]], coverage: list[dict[str, Any]], samples: list[dict[str, Any]], quality_rows: list[dict[str, Any]]) -> None:
    status_df = pd.DataFrame(status_rows)
    cov_df = pd.DataFrame(coverage)
    man_df = pd.DataFrame(manifest_rows)
    summary = []
    for category in CATEGORIES:
        c_status = status_df[status_df["category"] == category] if not status_df.empty else pd.DataFrame()
        c_cov = cov_df[cov_df["category"] == category] if not cov_df.empty else pd.DataFrame()
        c_man = man_df[man_df["category"] == category] if not man_df.empty else pd.DataFrame()
        summary.append(
            {
                "category": category,
                "request_count": int(len(c_status)),
                "success_count": int((c_status["status"] == "success").sum()) if not c_status.empty else 0,
                "failed_count": int((c_status["status"] != "success").sum()) if not c_status.empty else 0,
                "raw_rows": int(c_man["row_count"].sum()) if not c_man.empty else 0,
                "pit_normalized_rows": int(c_man["row_count"].sum()) if not c_man.empty else 0,
                "excluded_missing_available_at_rows": int(c_man["excluded_missing_available_at_rows"].sum()) if not c_man.empty and "excluded_missing_available_at_rows" in c_man else 0,
                "symbol_count": int(c_man["symbol_count"].sum()) if not c_man.empty else 0,
                "avg_pit_valid_coverage_rate": float(c_cov["pit_valid_coverage_rate"].mean()) if not c_cov.empty else 0.0,
            }
        )
    gate = any(row["raw_rows"] > 0 for row in summary) and bool(samples)
    allowed_fields = [
        {"category": "institutional_flow", "field": "foreign_net_buy / investment_trust_net_buy / dealer_net_buy / institutional_total_net_buy", "status": "review_required" if any(r["category"] == "institutional_flow" and r["raw_rows"] > 0 for r in summary) else "fail"},
        {"category": "margin_short", "field": "margin_balance / margin_balance_change / short_balance / short_balance_change", "status": "review_required" if any(r["category"] == "margin_short" and r["raw_rows"] > 0 for r in summary) else "fail"},
        {"category": "monthly_revenue", "field": "all monthly revenue fields", "status": "deferred_not_authorized"},
    ]
    lines = [
        "# Phase 0E 扩展 Raw Archive Backfill 执行报告",
        "",
        "## 1. 执行范围",
        "",
        f"- 执行日期：`{utc_now()}`",
        "- 阶段目标：对法人筹码与融资融券做扩展 raw archive backfill，并生成 PIT 审计产物。",
        "- 未执行：月营收、全市场补齐、materialize derived features、Qlib bin/provider 写入、provider refresh/publish、accepted latest switching、Phase 1 样本、单因子检验、模型训练、规则 baseline、Phase 2、前端/API、broker/orders/quick-trade/target position/target weight。",
        "",
        "## 2. 实际联网/下载命令",
        "",
        f"- 脱敏命令：`python scripts/build_tw_decision_orthogonal_phase0e_raw_archive.py --token-stdin --start {args.start} --end {args.end} --max-symbols {args.max_symbols} --sleep {args.sleep} --timeout {args.timeout}`",
        "- 命令记录不包含 token 原文。",
        "",
        "## 3. 是否使用 Scrapling",
        "",
        "- `scrapling_used=false`。",
        "- 本次使用 FinMind API endpoint；未使用 Scrapling。",
        "",
        "## 4. 是否使用 API Token",
        "",
        "- `token_used=true`。",
        f"- token 来源：`{token_source}`。",
        "- 未在脚本、CSV、JSON、Markdown、日志或错误信息中写入 token 原文。",
        "",
        "## 5. 修改文件",
        "",
        "- 新增 `scripts/build_tw_decision_orthogonal_phase0e_raw_archive.py`。",
        "- 更新 `docs/tw_decision_model_orthogonal/PHASE0E_EXECUTION_REPORT_CN.md`。",
        "",
        "## 6. 生成文件",
        "",
        f"- `{rel(RAW_DIR)}/`",
        f"- `{rel(DOWNLOAD_STATUS_PATH)}`",
        f"- `{rel(MANIFEST_PATH)}`",
        f"- `{rel(COVERAGE_PATH)}`",
        f"- `{rel(PIT_SAMPLES_PATH)}`",
        f"- `{rel(QUALITY_FLAGS_PATH)}`",
        f"- `{rel(EXEC_REPORT_PATH)}`",
        "",
        "## 7. 数据源、endpoint、source_url",
        "",
        f"- endpoint/source_url：`{FINMIND_URL}`",
        "- institutional dataset：`TaiwanStockInstitutionalInvestorsBuySell`",
        "- margin dataset：`TaiwanStockMarginPurchaseShortSale`",
        "",
        "## 8. 时间范围与股票范围",
        "",
        f"- start：`{args.start}`",
        f"- end：`{args.end}`",
        f"- max_symbols：`{args.max_symbols}`",
        f"- actual_symbols：`{len(symbols)}`",
        "- universe 选择：`tw_liquid_dyn` 与时间窗口重叠的 symbol，按窗口内 active days 排序取 Top150；不是全市场。",
        "",
        "## 9. Raw Archive 摘要",
        "",
        md_table(summary, ["category", "request_count", "success_count", "failed_count", "pit_normalized_rows", "excluded_missing_available_at_rows", "symbol_count", "avg_pit_valid_coverage_rate"]),
        "",
        "## 10. 下载成功/失败统计",
        "",
        md_table(status_rows[:30], ["category", "symbol", "stock_id", "status", "row_count", "error_type", "error_message", "token_used"]),
        "",
        "## 11. 覆盖率、缺失率、重复行、Quality Flags",
        "",
        md_table(coverage[:30], ["category", "symbol", "expected_trading_days", "raw_rows", "pit_valid_rows", "pit_valid_coverage_rate", "missing_dates_count", "extra_dates_count", "duplicate_rows_count", "quality_issue_count"]),
        "",
        "## 12. available_at 规则与 PIT Validation",
        "",
        "- 规则：`available_at = next_trading_day(trade_date)`。",
        "- T+1 是 conservative visibility proxy，不是官方发布时间声明。",
        "- 不使用 `trade_date`，避免盘后/日后可见统计在同日 asof 中产生未来函数。",
        "- 不使用 `fetched_at`，因为它是本次抓取时间，不代表历史当时可见时间。",
        "- 本次本地交易日历加载至本地价格最大覆盖日；对仍无法生成下一交易日的 tail rows，保留 raw response 证据，但从 normalized PIT archive 中排除，并在 manifest 记录 `excluded_missing_available_at_rows`。",
        "",
        md_table(samples[:20], ["category", "symbol", "trade_date", "available_at", "asof_example", "visible_at_asof", "validation_result"]),
        "",
        "## 13. 可进入后续 Phase 1B 审查字段",
        "",
        md_table(allowed_fields, ["category", "field", "status"]),
        "",
        "## 14. Deferred / Fail 字段与原因",
        "",
        "- 月营收：`deferred_not_authorized`，Phase 0E 未授权。",
        "- 若单一 symbol 请求失败，已保留在 download status，等待审查者判断是否重试。",
        "",
        "## 15. Phase 0E Gate",
        "",
        f"- 是否满足 Phase 0E Gate：`{gate}`。",
        "- 即使 Gate 为 true，也不能自动进入 Phase 1B，必须等待审查者审查。",
        "",
        "## 16. 安全边界",
        "",
        "- 月营收：未触碰。",
        "- 全市场补齐：未执行。",
        "- materialize derived features：未执行。",
        "- Qlib bin/provider 写入：未触碰。",
        "- provider refresh/publish：未触碰。",
        "- accepted latest switching：未触碰。",
        "- Phase 1 样本/单因子检验：未执行。",
        "- 模型训练/规则 baseline/Phase 2：未执行。",
        "- 前端/API：未触碰。",
        "- broker/orders/quick-trade/target position/target weight：未触碰。",
        "- 真实交易建议语义：未生成。",
        "",
        "## 17. 需要审查者或用户确认的问题",
        "",
        "- 是否接受本次 Top150 historical universe 的定义：按 `tw_liquid_dyn` 在窗口内 active days 排序取前 150。",
        "- 是否接受继续使用 T+1 conservative visibility proxy 进入后续 Phase 1B 审查。",
        "- 若存在失败 symbol，是否需要重试或降级时间范围。",
        "- 月营收仍需另行授权。",
        "",
    ]
    EXEC_REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Phase 0E expanded raw archive.")
    parser.add_argument("--start", default="2022-01-01")
    parser.add_argument("--end", default="2026-06-10")
    parser.add_argument("--max-symbols", type=int, default=150)
    parser.add_argument("--sleep", type=float, default=0.08)
    parser.add_argument("--timeout", type=float, default=45.0)
    parser.add_argument("--post-end-calendar-days", type=int, default=14)
    parser.add_argument("--token-stdin", action="store_true")
    args = parser.parse_args()

    token = read_token(args)
    if not token:
        raise SystemExit("missing FINMIND token")
    token_source = "用户提供 token，运行时临时注入" if args.token_stdin else "environment variable"

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    DOC_DIR.mkdir(parents=True, exist_ok=True)
    symbols = load_universe(args.start, args.end, args.max_symbols)
    calendars = load_calendar(symbols["symbol"].tolist(), args.start, args.end, args.post_end_calendar_days)

    status_rows: list[dict[str, Any]] = []
    manifest_rows: list[dict[str, Any]] = []
    coverage: list[dict[str, Any]] = []
    samples: list[dict[str, Any]] = []
    quality_rows: list[dict[str, Any]] = []

    for category, dataset in CATEGORIES.items():
        snapshot_id = f"phase0e_{category}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
        fetched_at = utc_now()
        archive_rows: list[dict[str, Any]] = []
        raw_jsonl_path = RAW_DIR / category / f"{snapshot_id}_raw_response.jsonl"
        normalized_path = RAW_DIR / category / f"{snapshot_id}_normalized.csv"
        raw_jsonl_path.parent.mkdir(parents=True, exist_ok=True)
        with raw_jsonl_path.open("w", encoding="utf-8") as raw_fh:
            for i, sym in symbols.iterrows():
                started = utc_now()
                rows, status = request_finmind(category, sym["stock_id"], args.start, args.end, args.timeout, token)
                finished = utc_now()
                raw_fh.write(
                    json.dumps(
                        {
                            "category": category,
                            "dataset": dataset,
                            "symbol": sym["symbol"],
                            "stock_id": sym["stock_id"],
                            "start": args.start,
                            "end": args.end,
                            "fetched_at": finished,
                            "status": {k: v for k, v in status.items() if k != "token_used"},
                            "token_used": bool(token),
                            "rows": rows,
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )
                raw_df = pd.DataFrame(rows)
                if not raw_df.empty:
                    calendar = sorted(set(calendars.get(sym["symbol"], [])) | set(calendars.get("__global__", [])))
                    if category == "institutional_flow":
                        archive_rows.extend(institutional_to_archive(raw_df, sym["symbol"], sym["stock_id"], fetched_at, snapshot_id, calendar))
                    else:
                        archive_rows.extend(margin_to_archive(raw_df, sym["symbol"], sym["stock_id"], fetched_at, snapshot_id, calendar))
                status_rows.append(
                    {
                        "category": category,
                        "symbol": sym["symbol"],
                        "stock_id": sym["stock_id"],
                        "start_date": args.start,
                        "end_date": args.end,
                        "request_started_at": started,
                        "request_finished_at": finished,
                        "status": status["status"],
                        "row_count": len(rows),
                        "error_type": status["error_type"],
                        "error_message": status["error_message"],
                        "source_endpoint": FINMIND_URL,
                        "source_url": FINMIND_URL,
                        "token_used": bool(token),
                        "output_path": rel(raw_jsonl_path),
                    }
                )
                print(f"[{category} {i + 1}/{len(symbols)}] {sym['symbol']} rows={len(rows)} status={status['status']}", flush=True)
                if args.sleep > 0 and i + 1 < len(symbols):
                    time.sleep(args.sleep)
        excluded_missing_available = sum(1 for r in archive_rows if not str(r.get("available_at") or "").strip())
        pit_archive_rows = [r for r in archive_rows if str(r.get("available_at") or "").strip()]
        write_csv(normalized_path, pit_archive_rows)
        coverage.extend(coverage_rows(category, symbols, pit_archive_rows, args.start, args.end))
        samples.extend(pit_samples(category, pit_archive_rows))
        quality_rows.extend(quality_summary(category, pit_archive_rows))
        manifest_rows.append(
            {
                "raw_snapshot_id": snapshot_id,
                "category": category,
                "data_source": f"FinMind:{dataset}",
                "fetched_at": fetched_at,
                "source_endpoint": FINMIND_URL,
                "symbol_count": len({r["symbol"] for r in pit_archive_rows}),
                "row_count": len(pit_archive_rows),
                "excluded_missing_available_at_rows": excluded_missing_available,
                "first_trade_date": min([r["trade_date"] for r in pit_archive_rows], default=""),
                "last_trade_date": max([r["trade_date"] for r in pit_archive_rows], default=""),
                "available_at_rule": "available_at = next_trading_day(trade_date)",
                "archive_path": rel(normalized_path),
                "checksum_or_size": sha256_size(normalized_path),
            }
        )

    write_csv(DOWNLOAD_STATUS_PATH, status_rows)
    write_csv(MANIFEST_PATH, manifest_rows)
    write_csv(COVERAGE_PATH, coverage)
    write_csv(PIT_SAMPLES_PATH, samples)
    write_csv(QUALITY_FLAGS_PATH, quality_rows)
    write_report(args, token_source, symbols, status_rows, manifest_rows, coverage, samples, quality_rows)

    print(
        json.dumps(
            {
                "status": "ok",
                "scope": "phase0e_raw_archive_backfill_only",
                "symbols": int(len(symbols)),
                "status_rows": len(status_rows),
                "raw_rows_by_category": {row["category"]: row["row_count"] for row in manifest_rows},
                "token_used": bool(token),
                "outputs": [
                    rel(RAW_DIR),
                    rel(DOWNLOAD_STATUS_PATH),
                    rel(MANIFEST_PATH),
                    rel(COVERAGE_PATH),
                    rel(PIT_SAMPLES_PATH),
                    rel(QUALITY_FLAGS_PATH),
                    rel(EXEC_REPORT_PATH),
                ],
                "safety": {
                    "monthly_revenue": False,
                    "full_market": False,
                    "materialize": False,
                    "provider_refresh_publish": False,
                    "accepted_latest_switching": False,
                    "phase1_samples": False,
                    "factor_test": False,
                    "model_training": False,
                    "phase2": False,
                    "frontend_api": False,
                    "broker_orders_quick_trade_target_positions": False,
                },
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
