#!/usr/bin/env python3
"""Build Phase 0C limited raw archive for orthogonal TW Decision data.

This script only downloads FinMind institutional-flow and margin/short POC raw
rows into the Phase 0C research directory and writes PIT audit files. It does
not materialize derived features, write Qlib bins/providers, switch accepted
latest, build Phase 1 samples, train models, run backtests, touch frontend/API,
or interact with trading state.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import requests


ROOT = Path(__file__).resolve().parents[1]
QLIB = ROOT / "qlib_pipeline"
UNIVERSE_PATH = QLIB / "data_tw/experiments/yahoo_adjusted_primary/universe/tw_liquid_dyn.txt"
NORMALIZED_DIR = QLIB / "data_tw/experiments/yahoo_adjusted_primary/normalized_nonempty"
OUT_DIR = ROOT / "data_tw/experiments/decision_orthogonal"
RAW_DIR = OUT_DIR / "phase0c_raw_archive"
DOC_DIR = ROOT / "docs/tw_decision_model_orthogonal"

DOWNLOAD_STATUS_PATH = OUT_DIR / "phase0c_download_status.csv"
MANIFEST_PATH = OUT_DIR / "phase0c_pit_snapshot_manifest.csv"
COVERAGE_PATH = OUT_DIR / "phase0c_coverage_report.csv"
PIT_SAMPLES_PATH = OUT_DIR / "phase0c_pit_validation_samples.csv"
EXEC_REPORT_PATH = DOC_DIR / "PHASE0C_EXECUTION_REPORT_CN.md"

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


def load_universe(asof: str, max_symbols: int) -> pd.DataFrame:
    rows = []
    with UNIVERSE_PATH.open(encoding="utf-8") as fh:
        for line in fh:
            parts = line.strip().split("\t")
            if len(parts) != 3:
                continue
            symbol, start, end = parts
            rows.append({"symbol": symbol, "start": pd.Timestamp(start), "end": pd.Timestamp(end)})
    seg = pd.DataFrame(rows)
    active = seg[(seg["start"] <= pd.Timestamp(asof)) & (seg["end"] >= pd.Timestamp(asof))][["symbol"]].drop_duplicates()
    if "TW2330" in set(active["symbol"]):
        preferred = pd.DataFrame({"symbol": ["TW2330"]})
        active = pd.concat([preferred, active[active["symbol"] != "TW2330"]], ignore_index=True)
    active = active.sort_values("symbol").head(max_symbols).reset_index(drop=True)
    if "TW2330" in set(seg["symbol"]) and "TW2330" not in set(active["symbol"]) and len(active) >= max_symbols:
        active.iloc[-1, active.columns.get_loc("symbol")] = "TW2330"
        active = active.drop_duplicates("symbol").sort_values("symbol").reset_index(drop=True)
    active["stock_id"] = active["symbol"].str.replace("TW", "", regex=False)
    return active


def load_calendar(symbols: list[str], start: str, end: str) -> list[pd.Timestamp]:
    dates = set()
    for symbol in symbols:
        path = NORMALIZED_DIR / f"{symbol}.csv"
        if not path.exists():
            continue
        try:
            df = pd.read_csv(path, usecols=["date"])
        except Exception:
            continue
        for date in pd.to_datetime(df["date"], errors="coerce").dropna():
            day = pd.Timestamp(date).normalize()
            if pd.Timestamp(start) <= day <= pd.Timestamp(end):
                dates.add(day)
    return sorted(dates)


def next_trading_day(day: pd.Timestamp, calendar: list[pd.Timestamp]) -> pd.Timestamp | None:
    for candidate in calendar:
        if candidate > day:
            return candidate
    return None


def request_finmind(category: str, stock_id: str, start: str, end: str, timeout: float) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    dataset = CATEGORIES[category]
    params = {"dataset": dataset, "data_id": stock_id, "start_date": start, "end_date": end}
    token = os.getenv("FINMIND_TOKEN") or os.getenv("FINMIND_API_TOKEN")
    headers = {"User-Agent": "Mozilla/5.0 decision-orthogonal-phase0c/1.0"}
    if token:
        headers["Authorization"] = f"Bearer {token.strip()}"
    try:
        resp = requests.get(FINMIND_URL, params=params, headers=headers, timeout=timeout)
        try:
            payload = resp.json()
        except Exception:
            payload = {"status": None, "msg": resp.text[:500], "data": []}
        data = payload.get("data") if isinstance(payload, dict) else None
        rows = data if isinstance(data, list) else []
        status = "success" if resp.status_code == 200 and str(payload.get("status")) == "200" else "failed"
        return rows, {
            "status": status,
            "http_status": resp.status_code,
            "finmind_status": payload.get("status") if isinstance(payload, dict) else None,
            "error_type": "" if status == "success" else "finmind_or_http_error",
            "error_message": "" if status == "success" else str(payload.get("msg") if isinstance(payload, dict) else "bad_payload"),
            "token_used": bool(token),
        }
    except Exception as exc:
        return [], {
            "status": "failed",
            "http_status": "",
            "finmind_status": "",
            "error_type": type(exc).__name__,
            "error_message": str(exc),
            "token_used": bool(token),
        }


def num(row: pd.Series, col: str) -> float:
    try:
        value = pd.to_numeric(row.get(col), errors="coerce")
        if pd.isna(value):
            return float("nan")
        return float(value)
    except Exception:
        return float("nan")


def institutional_to_archive(raw: pd.DataFrame, symbol: str, stock_id: str, fetched_at: str, snapshot_id: str, calendar: list[pd.Timestamp]) -> list[dict[str, Any]]:
    if raw.empty:
        return []
    rows = []
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
        rows.append({
            "symbol": symbol,
            "stock_id": stock_id,
            "trade_date": trade_day.strftime("%Y-%m-%d") if trade_day is not None else str(date),
            "available_at": available.strftime("%Y-%m-%d") if available is not None else "",
            "foreign_net_buy": foreign,
            "investment_trust_net_buy": trust,
            "dealer_net_buy": dealer,
            "institutional_total_net_buy": foreign + trust + dealer,
            "data_source": "FinMind:TaiwanStockInstitutionalInvestorsBuySell",
            "raw_snapshot_id": snapshot_id,
            "fetched_at": fetched_at,
            "quality_flags": ";".join(sorted(set(flags))),
        })
    return rows


def margin_to_archive(raw: pd.DataFrame, symbol: str, stock_id: str, fetched_at: str, snapshot_id: str, calendar: list[pd.Timestamp]) -> list[dict[str, Any]]:
    if raw.empty:
        return []
    rows = []
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
        rows.append({
            "symbol": symbol,
            "stock_id": stock_id,
            "trade_date": trade_day.strftime("%Y-%m-%d") if trade_day is not None else str(r.get("date")),
            "available_at": available.strftime("%Y-%m-%d") if available is not None else "",
            "margin_balance": margin_today if math.isfinite(margin_today) else "",
            "margin_balance_change": margin_today - margin_yesterday if math.isfinite(margin_today) and math.isfinite(margin_yesterday) else "",
            "short_balance": short_today if math.isfinite(short_today) else "",
            "short_balance_change": short_today - short_yesterday if math.isfinite(short_today) and math.isfinite(short_yesterday) else "",
            "data_source": "FinMind:TaiwanStockMarginPurchaseShortSale",
            "raw_snapshot_id": snapshot_id,
            "fetched_at": fetched_at,
            "quality_flags": ";".join(sorted(set(flags))),
        })
    return rows


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def file_size(path: Path) -> int:
    return path.stat().st_size if path.exists() else 0


def expected_dates_for_symbol(symbol: str, start: str, end: str) -> set[str]:
    path = NORMALIZED_DIR / f"{symbol}.csv"
    if not path.exists():
        return set()
    try:
        df = pd.read_csv(path, usecols=["date"])
    except Exception:
        return set()
    dates = pd.to_datetime(df["date"], errors="coerce").dropna()
    return {d.strftime("%Y-%m-%d") for d in dates if pd.Timestamp(start) <= d <= pd.Timestamp(end)}


def coverage_rows(category: str, symbols: pd.DataFrame, rows: list[dict[str, Any]], start: str, end: str) -> list[dict[str, Any]]:
    out = []
    df = pd.DataFrame(rows)
    for _, sym in symbols.iterrows():
        symbol = sym["symbol"]
        expected = expected_dates_for_symbol(symbol, start, end)
        g = df[df["symbol"] == symbol] if not df.empty else pd.DataFrame()
        observed_dates = set(g["trade_date"].astype(str)) if not g.empty else set()
        duplicate_rows = int(g.duplicated(["symbol", "trade_date"]).sum()) if not g.empty else 0
        quality_issue_count = int(g["quality_flags"].astype(str).ne("").sum()) if not g.empty and "quality_flags" in g else 0
        out.append({
            "category": category,
            "symbol": symbol,
            "expected_trading_days": len(expected),
            "observed_rows": int(len(g)),
            "coverage_rate": float(len(observed_dates & expected) / len(expected)) if expected else 0.0,
            "first_trade_date": min(observed_dates) if observed_dates else "",
            "last_trade_date": max(observed_dates) if observed_dates else "",
            "missing_dates_count": len(expected - observed_dates),
            "duplicate_rows_count": duplicate_rows,
            "quality_issue_count": quality_issue_count,
        })
    return out


def pit_samples(category: str, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    valid = [r for r in rows if r.get("trade_date") and r.get("available_at")]
    for r in valid[:8]:
        out.append({
            "category": category,
            "symbol": r["symbol"],
            "trade_date": r["trade_date"],
            "available_at": r["available_at"],
            "asof_example": r["trade_date"],
            "visible_at_asof": False,
            "raw_snapshot_id": r["raw_snapshot_id"],
            "validation_result": "pass" if r["trade_date"] < r["available_at"] else "fail",
            "validation_note": "Boundary sample: trade_date asof is before conservative T+1 available_at.",
        })
        out.append({
            "category": category,
            "symbol": r["symbol"],
            "trade_date": r["trade_date"],
            "available_at": r["available_at"],
            "asof_example": r["available_at"],
            "visible_at_asof": True,
            "raw_snapshot_id": r["raw_snapshot_id"],
            "validation_result": "pass",
            "validation_note": "Positive sample: asof is available_at, row is visible.",
        })
    return out


def md_table(rows: list[dict[str, Any]], cols: list[str]) -> str:
    if not rows:
        return "_no rows_"
    lines = ["| " + " | ".join(cols) + " |", "|" + "|".join(["---" for _ in cols]) + "|"]
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(col, "")) for col in cols) + " |")
    return "\n".join(lines)


def write_report(args: argparse.Namespace, symbols: pd.DataFrame, status_rows: list[dict[str, Any]], manifest_rows: list[dict[str, Any]], coverage: list[dict[str, Any]], samples: list[dict[str, Any]]) -> None:
    status_df = pd.DataFrame(status_rows)
    coverage_df = pd.DataFrame(coverage)
    manifest_df = pd.DataFrame(manifest_rows)
    summary = []
    for category in CATEGORIES:
        c_status = status_df[status_df["category"] == category] if not status_df.empty else pd.DataFrame()
        c_cov = coverage_df[coverage_df["category"] == category] if not coverage_df.empty else pd.DataFrame()
        c_manifest = manifest_df[manifest_df["category"] == category] if not manifest_df.empty else pd.DataFrame()
        summary.append({
            "category": category,
            "request_count": int(len(c_status)),
            "success_count": int((c_status["status"] == "success").sum()) if not c_status.empty else 0,
            "failed_count": int((c_status["status"] != "success").sum()) if not c_status.empty else 0,
            "raw_rows": int(c_manifest["row_count"].sum()) if not c_manifest.empty else 0,
            "symbol_count": int(c_manifest["symbol_count"].sum()) if not c_manifest.empty else 0,
            "avg_coverage_rate": float(c_cov["coverage_rate"].mean()) if not c_cov.empty else 0.0,
        })
    phase0c_gate = any(row["raw_rows"] > 0 for row in summary) and bool(samples)
    allowed_fields = [
        {"category": "institutional_flow", "field": "foreign_net_buy / investment_trust_net_buy / dealer_net_buy / institutional_total_net_buy", "status": "review_required" if any(r["category"] == "institutional_flow" and r["raw_rows"] > 0 for r in summary) else "fail"},
        {"category": "margin_short", "field": "margin_balance / margin_balance_change / short_balance / short_balance_change", "status": "review_required" if any(r["category"] == "margin_short" and r["raw_rows"] > 0 for r in summary) else "fail"},
        {"category": "monthly_revenue", "field": "all monthly revenue fields", "status": "deferred_phase0c_not_authorized"},
    ]
    lines = [
        "# Phase 0C 受限 POC Raw Archive 执行报告",
        "",
        "## 1. 执行范围",
        "",
        f"- 执行日期：`{utc_now()}`",
        "- 范围：仅对法人筹码与融资融券做 FinMind POC raw archive，并生成 PIT 审计产物。",
        "- 未执行：月营收、materialize derived features、Qlib bin/provider、accepted latest switching、Phase 1 样本、单因子检验、模型训练、规则 baseline、组合回放、前端/API、broker/orders/quick-trade/target position。",
        "",
        "## 2. 实际联网/下载命令",
        "",
        f"- `python scripts/build_tw_decision_orthogonal_phase0c_raw_archive.py --start {args.start} --end {args.end} --max-symbols {args.max_symbols} --sleep {args.sleep} --timeout {args.timeout}`",
        "",
        "## 3. 修改文件",
        "",
        "- 新增 `scripts/build_tw_decision_orthogonal_phase0c_raw_archive.py`。",
        "",
        "## 4. 生成文件",
        "",
        f"- `{rel(RAW_DIR)}/`",
        f"- `{rel(DOWNLOAD_STATUS_PATH)}`",
        f"- `{rel(MANIFEST_PATH)}`",
        f"- `{rel(COVERAGE_PATH)}`",
        f"- `{rel(PIT_SAMPLES_PATH)}`",
        f"- `{rel(EXEC_REPORT_PATH)}`",
        "",
        "## 5. 数据源与 endpoint",
        "",
        f"- endpoint：`{FINMIND_URL}`",
        "- institutional dataset：`TaiwanStockInstitutionalInvestorsBuySell`",
        "- margin dataset：`TaiwanStockMarginPurchaseShortSale`",
        "",
        "## 6. 时间范围与股票范围",
        "",
        f"- start：`{args.start}`",
        f"- end：`{args.end}`",
        f"- max_symbols：`{args.max_symbols}`",
        f"- actual_symbols：`{len(symbols)}`",
        "",
        "## 7. Raw Archive 摘要",
        "",
        md_table(summary, ["category", "request_count", "success_count", "failed_count", "raw_rows", "symbol_count", "avg_coverage_rate"]),
        "",
        "## 8. 下载成功/失败统计",
        "",
        md_table(status_rows[:20], ["category", "symbol", "stock_id", "status", "row_count", "error_type", "error_message"]),
        "",
        "## 9. 覆盖率与缺失率",
        "",
        md_table(coverage[:20], ["category", "symbol", "expected_trading_days", "observed_rows", "coverage_rate", "missing_dates_count", "duplicate_rows_count", "quality_issue_count"]),
        "",
        "## 10. available_at 规则与证据",
        "",
        "- 规则：`available_at = next_trading_day(trade_date)`。",
        "- 不能直接使用 `trade_date`：法人筹码与融资融券通常为盘后/日后可见数据；若在同一交易日收盘前用于 asof，会产生未来函数风险。",
        "- FinMind/TWSE/TPEx 可见时间证据：既有仓库 POC 文档和脚本注释记录法人数据按交易日盘后发布，需要 T+1；融资融券同属日频盘后统计，本 Phase0C 采用保守 T+1，等待审查者复核。",
        "- `fetched_at` 只表示本地抓取时间，晚于历史交易日，不能替代历史当时的官方可见时间。",
        "- 若审查者不接受 T+1 规则，则相关字段必须 deferred，不得进入 Phase 1。",
        "",
        "## 11. PIT validation samples 摘要",
        "",
        md_table(samples[:20], ["category", "symbol", "trade_date", "available_at", "asof_example", "visible_at_asof", "validation_result", "validation_note"]),
        "",
        "## 12. 可进入后续审查的字段",
        "",
        md_table(allowed_fields, ["category", "field", "status"]),
        "",
        "## 13. Deferred / Fail 字段与原因",
        "",
        "- 月营收：Phase0C 未授权，全部 deferred。",
        "- 若任一类别 raw_rows=0，则该类别 fail，等待审查者判断是否重试或停止。",
        "- 若 T+1 `available_at` 证据不被接受，则法人/融资融券字段 deferred。",
        "",
        "## 14. Phase 0C Gate",
        "",
        f"- 是否满足 Phase 0C Gate：`{phase0c_gate}`。",
        "- 即使 Gate 为 true，也不能进入 Phase 1，必须等待审查者审查 PIT、覆盖率和未来函数风险。",
        "",
        "## 15. 安全边界",
        "",
        "- provider refresh/publish：未触碰。",
        "- accepted latest switching：未触碰。",
        "- materialize/screen/ablation：未执行。",
        "- broker/orders/quick-trade/target position/target weight：未触碰。",
        "- 前端/API：未触碰。",
        "- 真实交易建议语义：未生成。",
        "",
        "## 16. 需要审查者或用户确认的问题",
        "",
        "- 是否接受法人筹码与融资融券的保守 T+1 `available_at` 规则。",
        "- 当前 POC 覆盖率是否足以进入更大范围补齐审查。",
        "- 是否允许后续补齐更长时间范围或更多 symbol。",
        "- 月营收是否继续暂缓，或另行授权新增具备公告日期的数据源。",
        "",
    ]
    EXEC_REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build limited Phase 0C raw archive for institutional and margin/short POC.")
    parser.add_argument("--start", default="2026-01-01")
    parser.add_argument("--end", default="2026-06-10")
    parser.add_argument("--max-symbols", type=int, default=50)
    parser.add_argument("--sleep", type=float, default=0.15)
    parser.add_argument("--timeout", type=float, default=30.0)
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    DOC_DIR.mkdir(parents=True, exist_ok=True)

    symbols = load_universe(args.end, args.max_symbols)
    calendar = load_calendar(symbols["symbol"].tolist(), args.start, args.end)
    status_rows: list[dict[str, Any]] = []
    manifest_rows: list[dict[str, Any]] = []
    coverage: list[dict[str, Any]] = []
    samples: list[dict[str, Any]] = []

    for category, dataset in CATEGORIES.items():
        snapshot_id = f"phase0c_{category}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
        fetched_at = utc_now()
        archive_rows: list[dict[str, Any]] = []
        raw_jsonl_path = RAW_DIR / category / f"{snapshot_id}_raw_response.jsonl"
        raw_jsonl_path.parent.mkdir(parents=True, exist_ok=True)
        normalized_path = RAW_DIR / category / f"{snapshot_id}_normalized.csv"
        with raw_jsonl_path.open("w", encoding="utf-8") as raw_fh:
            for i, sym in symbols.iterrows():
                started = utc_now()
                rows, status = request_finmind(category, sym["stock_id"], args.start, args.end, args.timeout)
                finished = utc_now()
                raw_fh.write(json.dumps({
                    "category": category,
                    "dataset": dataset,
                    "symbol": sym["symbol"],
                    "stock_id": sym["stock_id"],
                    "start": args.start,
                    "end": args.end,
                    "fetched_at": finished,
                    "status": status,
                    "rows": rows,
                }, ensure_ascii=False) + "\n")
                raw_df = pd.DataFrame(rows)
                if not raw_df.empty:
                    if category == "institutional_flow":
                        archive_rows.extend(institutional_to_archive(raw_df, sym["symbol"], sym["stock_id"], fetched_at, snapshot_id, calendar))
                    else:
                        archive_rows.extend(margin_to_archive(raw_df, sym["symbol"], sym["stock_id"], fetched_at, snapshot_id, calendar))
                status_rows.append({
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
                    "output_path": rel(raw_jsonl_path),
                })
                print(f"[{category} {i + 1}/{len(symbols)}] {sym['symbol']} rows={len(rows)} status={status['status']}", flush=True)
                if args.sleep > 0 and i + 1 < len(symbols):
                    time.sleep(args.sleep)
        write_csv(normalized_path, archive_rows)
        coverage.extend(coverage_rows(category, symbols, archive_rows, args.start, args.end))
        samples.extend(pit_samples(category, archive_rows))
        manifest_rows.append({
            "raw_snapshot_id": snapshot_id,
            "category": category,
            "data_source": f"FinMind:{dataset}",
            "fetched_at": fetched_at,
            "source_endpoint": FINMIND_URL,
            "symbol_count": len({r["symbol"] for r in archive_rows}),
            "row_count": len(archive_rows),
            "first_trade_date": min([r["trade_date"] for r in archive_rows], default=""),
            "last_trade_date": max([r["trade_date"] for r in archive_rows], default=""),
            "available_at_rule": "available_at = next_trading_day(trade_date)",
            "archive_path": rel(normalized_path),
            "checksum_or_size": f"sha256:{hashlib.sha256(normalized_path.read_bytes()).hexdigest()} size:{file_size(normalized_path)}",
        })

    write_csv(DOWNLOAD_STATUS_PATH, status_rows)
    write_csv(MANIFEST_PATH, manifest_rows)
    write_csv(COVERAGE_PATH, coverage)
    write_csv(PIT_SAMPLES_PATH, samples)
    write_report(args, symbols, status_rows, manifest_rows, coverage, samples)

    print(json.dumps({
        "status": "ok",
        "scope": "phase0c_limited_raw_archive_only",
        "symbols": int(len(symbols)),
        "status_rows": len(status_rows),
        "manifest_rows": len(manifest_rows),
        "pit_samples": len(samples),
        "raw_rows_by_category": {row["category"]: row["row_count"] for row in manifest_rows},
        "outputs": [
            rel(Path("scripts/build_tw_decision_orthogonal_phase0c_raw_archive.py")),
            rel(RAW_DIR),
            rel(DOWNLOAD_STATUS_PATH),
            rel(MANIFEST_PATH),
            rel(COVERAGE_PATH),
            rel(PIT_SAMPLES_PATH),
            rel(EXEC_REPORT_PATH),
        ],
        "safety": {
            "materialize": False,
            "provider_refresh_publish": False,
            "accepted_latest_switching": False,
            "phase1_samples": False,
            "factor_test": False,
            "model_training": False,
            "frontend_api": False,
            "broker_orders_quick_trade_target_positions": False,
        },
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
