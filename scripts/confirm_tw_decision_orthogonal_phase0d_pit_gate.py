#!/usr/bin/env python3
"""Confirm Phase 0D PIT gate for orthogonal TW Decision data.

This script is offline-only. It reads Phase 0C normalized raw archives and the
local qlib/yahoo-adjusted price calendar, repairs missing conservative T+1
available_at where the next local trading day exists, and writes Phase 0D gate
artifacts. It does not download data, materialize derived features, build Phase
1 samples, write qlib providers, train models, touch frontend/API, or interact
with trading state.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import math
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
QLIB = ROOT / "qlib_pipeline"
NORMALIZED_DIR = QLIB / "data_tw/experiments/yahoo_adjusted_primary/normalized_nonempty"
OUT_DIR = ROOT / "data_tw/experiments/decision_orthogonal"
RAW_DIR = OUT_DIR / "phase0c_raw_archive"
PHASE0D_CLEAN_DIR = OUT_DIR / "phase0d_pit_clean"
DOC_DIR = ROOT / "docs/tw_decision_model_orthogonal"

PHASE0C_MANIFEST_PATH = OUT_DIR / "phase0c_pit_snapshot_manifest.csv"
PHASE0D_MANIFEST_PATH = OUT_DIR / "phase0d_pit_clean_manifest.csv"
PHASE0D_COVERAGE_PATH = OUT_DIR / "phase0d_pit_valid_coverage_report.csv"
PHASE0D_QUALITY_PATH = OUT_DIR / "phase0d_quality_flags_summary.csv"
PHASE0D_ALLOWED_FIELDS_PATH = OUT_DIR / "phase0d_phase1_allowed_fields.csv"
PHASE0D_REPORT_PATH = DOC_DIR / "PHASE0D_EXECUTION_REPORT_CN.md"

CATEGORY_FIELDS = {
    "institutional_flow": "foreign_net_buy / investment_trust_net_buy / dealer_net_buy / institutional_total_net_buy",
    "margin_short": "margin_balance / margin_balance_change / short_balance / short_balance_change",
}
DEFERRED_FIELDS = {
    "monthly_revenue": "all monthly revenue fields",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except Exception:
        return str(path)


def sha256_size(path: Path) -> str:
    return f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()} size:{path.stat().st_size}"


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


def load_phase0c_inputs() -> list[dict[str, Any]]:
    manifest = pd.read_csv(PHASE0C_MANIFEST_PATH)
    rows = []
    for _, row in manifest.iterrows():
        category = str(row["category"])
        archive_path = ROOT / str(row["archive_path"])
        if category not in CATEGORY_FIELDS:
            continue
        if not archive_path.exists():
            raise FileNotFoundError(f"Missing Phase 0C archive: {archive_path}")
        rows.append(
            {
                "category": category,
                "raw_snapshot_id": str(row["raw_snapshot_id"]),
                "archive_path": archive_path,
                "source_row_count": int(row["row_count"]),
                "source_first_trade_date": str(row["first_trade_date"]),
                "source_last_trade_date": str(row["last_trade_date"]),
                "data_source": str(row["data_source"]),
            }
        )
    return rows


def load_symbol_calendar(symbol: str, min_date: pd.Timestamp, max_date: pd.Timestamp) -> list[pd.Timestamp]:
    path = NORMALIZED_DIR / f"{symbol}.csv"
    if not path.exists():
        return []
    try:
        df = pd.read_csv(path, usecols=["date"])
    except Exception:
        return []
    dates = pd.to_datetime(df["date"], errors="coerce").dropna()
    out = []
    for value in dates:
        day = pd.Timestamp(value).normalize()
        if min_date <= day <= max_date:
            out.append(day)
    return sorted(set(out))


def next_trading_day(day: pd.Timestamp, calendar: list[pd.Timestamp]) -> pd.Timestamp | None:
    for candidate in calendar:
        if candidate > day:
            return candidate
    return None


def split_flags(value: Any) -> list[str]:
    text = "" if pd.isna(value) else str(value).strip()
    if not text:
        return []
    return [part.strip() for part in text.split(";") if part.strip()]


def join_flags(flags: list[str]) -> str:
    return ";".join(sorted(dict.fromkeys([flag for flag in flags if flag])))


def normalize_date(value: Any) -> pd.Timestamp | None:
    try:
        ts = pd.Timestamp(value)
    except Exception:
        return None
    if pd.isna(ts):
        return None
    return ts.normalize()


def clean_one_archive(category: str, source_path: Path, post_end_calendar_days: int) -> tuple[pd.DataFrame, dict[str, Any]]:
    df = pd.read_csv(source_path, dtype={"stock_id": str})
    raw_rows = int(len(df))
    if df.empty:
        df["phase1_allowed"] = False
        df["phase0d_action"] = "empty_source"
        return df, {
            "raw_rows": raw_rows,
            "available_at_repaired_rows": 0,
            "excluded_missing_available_at_rows": 0,
            "calendar_missing_symbols": 0,
        }

    trade_dates = pd.to_datetime(df["trade_date"], errors="coerce")
    min_trade = pd.Timestamp(trade_dates.min()).normalize()
    max_trade = pd.Timestamp(trade_dates.max()).normalize()
    calendar_min = min_trade
    calendar_max = max_trade + timedelta(days=post_end_calendar_days)

    calendars = {
        symbol: load_symbol_calendar(symbol, calendar_min, calendar_max)
        for symbol in sorted(df["symbol"].dropna().astype(str).unique())
    }
    calendar_missing_symbols = sum(1 for dates in calendars.values() if not dates)

    repaired = 0
    excluded_missing = 0
    cleaned_rows: list[dict[str, Any]] = []
    for _, row in df.iterrows():
        out = row.to_dict()
        flags = split_flags(out.get("quality_flags"))
        trade_day = normalize_date(out.get("trade_date"))
        available_day = normalize_date(out.get("available_at"))
        action = "kept_existing_available_at"

        if available_day is None and trade_day is not None:
            candidate = next_trading_day(trade_day, calendars.get(str(out.get("symbol")), []))
            if candidate is not None:
                available_day = candidate
                repaired += 1
                flags = [flag for flag in flags if flag != "available_at_missing_no_next_trading_day"]
                flags.append("phase0d_available_at_repaired_from_local_calendar")
                action = "repaired_available_at_from_local_calendar"
            else:
                flags.append("phase0d_excluded_missing_available_at")
                action = "excluded_missing_available_at"

        if available_day is not None:
            out["available_at"] = available_day.strftime("%Y-%m-%d")
            out["phase1_allowed"] = True
        else:
            out["available_at"] = ""
            out["phase1_allowed"] = False
            excluded_missing += 1

        out["quality_flags"] = join_flags(flags)
        out["phase0d_action"] = action
        cleaned_rows.append(out)

    cleaned = pd.DataFrame(cleaned_rows)
    allowed = cleaned[cleaned["phase1_allowed"] == True].copy()  # noqa: E712
    return allowed, {
        "raw_rows": raw_rows,
        "available_at_repaired_rows": repaired,
        "excluded_missing_available_at_rows": excluded_missing,
        "calendar_missing_symbols": calendar_missing_symbols,
    }


def expected_dates(symbol: str, start: str, end: str) -> set[str]:
    dates = load_symbol_calendar(symbol, pd.Timestamp(start), pd.Timestamp(end))
    return {date.strftime("%Y-%m-%d") for date in dates}


def coverage_rows(category: str, raw_df: pd.DataFrame, clean_df: pd.DataFrame, start: str, end: str) -> list[dict[str, Any]]:
    rows = []
    symbols = sorted(set(raw_df["symbol"].dropna().astype(str)) | set(clean_df["symbol"].dropna().astype(str)))
    for symbol in symbols:
        expected = expected_dates(symbol, start, end)
        raw_g = raw_df[raw_df["symbol"].astype(str) == symbol] if not raw_df.empty else pd.DataFrame()
        clean_g = clean_df[clean_df["symbol"].astype(str) == symbol] if not clean_df.empty else pd.DataFrame()
        raw_dates = set(raw_g["trade_date"].astype(str)) if not raw_g.empty else set()
        clean_dates = set(clean_g["trade_date"].astype(str)) if not clean_g.empty else set()
        raw_in_expected = raw_dates & expected
        clean_in_expected = clean_dates & expected
        extra_dates = raw_dates - expected
        rows.append(
            {
                "category": category,
                "symbol": symbol,
                "expected_trading_days": len(expected),
                "raw_rows": int(len(raw_g)),
                "raw_observed_dates": len(raw_dates),
                "raw_observed_coverage_rate": float(len(raw_in_expected) / len(expected)) if expected else 0.0,
                "pit_valid_rows": int(len(clean_g)),
                "pit_valid_dates": len(clean_dates),
                "pit_valid_coverage_rate": float(len(clean_in_expected) / len(expected)) if expected else 0.0,
                "rows_with_non_empty_available_at": int(clean_g["available_at"].astype(str).ne("").sum()) if not clean_g.empty else 0,
                "rows_excluded_due_to_missing_available_at": max(0, int(len(raw_g) - len(clean_g))),
                "extra_dates_count": len(extra_dates),
                "missing_dates_count": len(expected - clean_dates),
                "duplicate_rows_count": int(clean_g.duplicated(["symbol", "trade_date"]).sum()) if not clean_g.empty else 0,
                "quality_issue_count": int(clean_g["quality_flags"].fillna("").astype(str).ne("").sum()) if not clean_g.empty else 0,
                "first_trade_date": min(clean_dates) if clean_dates else "",
                "last_trade_date": max(clean_dates) if clean_dates else "",
            }
        )
    return rows


def quality_summary(category: str, clean_df: pd.DataFrame, raw_df: pd.DataFrame) -> list[dict[str, Any]]:
    counter: Counter[tuple[str, str]] = Counter()
    for _, row in clean_df.iterrows():
        flags = split_flags(row.get("quality_flags"))
        if not flags:
            counter[(str(row.get("symbol")), "none")] += 1
        for flag in flags:
            counter[(str(row.get("symbol")), flag)] += 1

    raw_missing = raw_df[raw_df["available_at"].fillna("").astype(str).eq("")]
    for _, row in raw_missing.iterrows():
        counter[(str(row.get("symbol")), "phase0c_missing_available_at_before_phase0d_repair")] += 1

    rows = []
    for (symbol, reason), count in sorted(counter.items()):
        rows.append({"category": category, "symbol": symbol, "quality_flag_reason": reason, "row_count": count})
    return rows


def md_table(rows: list[dict[str, Any]], cols: list[str]) -> str:
    if not rows:
        return "_no rows_"
    lines = ["| " + " | ".join(cols) + " |", "|" + "|".join(["---" for _ in cols]) + "|"]
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(col, "")) for col in cols) + " |")
    return "\n".join(lines)


def aggregate_category(coverage: list[dict[str, Any]], manifest: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    cov_df = pd.DataFrame(coverage)
    man_df = pd.DataFrame(manifest)
    for category in sorted(CATEGORY_FIELDS):
        c = cov_df[cov_df["category"] == category] if not cov_df.empty else pd.DataFrame()
        m = man_df[man_df["category"] == category] if not man_df.empty else pd.DataFrame()
        rows.append(
            {
                "category": category,
                "raw_rows": int(m["raw_rows"].sum()) if not m.empty else 0,
                "rows_with_non_empty_available_at": int(m["pit_valid_rows"].sum()) if not m.empty else 0,
                "rows_excluded_due_to_missing_available_at": int(m["excluded_missing_available_at_rows"].sum()) if not m.empty else 0,
                "available_at_repaired_rows": int(m["available_at_repaired_rows"].sum()) if not m.empty else 0,
                "avg_pit_valid_coverage_rate": float(c["pit_valid_coverage_rate"].mean()) if not c.empty else 0.0,
                "avg_raw_observed_coverage_rate": float(c["raw_observed_coverage_rate"].mean()) if not c.empty else 0.0,
                "extra_dates_count": int(c["extra_dates_count"].sum()) if not c.empty else 0,
                "missing_dates_count": int(c["missing_dates_count"].sum()) if not c.empty else 0,
                "duplicate_rows_count": int(c["duplicate_rows_count"].sum()) if not c.empty else 0,
                "quality_issue_count": int(c["quality_issue_count"].sum()) if not c.empty else 0,
            }
        )
    return rows


def allowed_fields_rows(category_summary: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    by_category = {row["category"]: row for row in category_summary}
    for category, fields in CATEGORY_FIELDS.items():
        summary = by_category.get(category, {})
        phase1_allowed = (
            int(summary.get("raw_rows", 0)) > 0
            and int(summary.get("rows_with_non_empty_available_at", 0)) > 0
            and int(summary.get("rows_excluded_due_to_missing_available_at", 0)) == 0
            and int(summary.get("duplicate_rows_count", 0)) == 0
        )
        rows.append(
            {
                "category": category,
                "field": fields,
                "phase1_allowed": str(bool(phase1_allowed)).lower(),
                "status": "review_required_phase0d_pass" if phase1_allowed else "blocked_by_phase0d_gate",
                "available_at_rule": "available_at = next_trading_day(trade_date), repaired from local price calendar when missing",
                "notes": "T+1 is conservative visibility, not official publication timestamp.",
            }
        )
    for category, fields in DEFERRED_FIELDS.items():
        rows.append(
            {
                "category": category,
                "field": fields,
                "phase1_allowed": "false",
                "status": "deferred_not_authorized",
                "available_at_rule": "",
                "notes": "Phase0C/Phase0D did not authorize monthly revenue data.",
            }
        )
    return rows


def write_report(
    args: argparse.Namespace,
    category_summary: list[dict[str, Any]],
    manifest_rows: list[dict[str, Any]],
    coverage_rows_out: list[dict[str, Any]],
    quality_rows: list[dict[str, Any]],
    allowed_rows: list[dict[str, Any]],
    phase0d_gate: bool,
) -> None:
    DOC_DIR.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Phase 0D PIT 修复与 Gate Confirmation 执行报告",
        "",
        "## 1. 执行范围",
        "",
        f"- 执行日期：`{utc_now()}`",
        "- 阶段目标：基于既有 Phase0C raw archive 做不联网 PIT 修复与 gate confirmation。",
        "- 本阶段未联网、未重跑 FinMind、未新增数据源、未扩大时间范围或 symbol universe。",
        "- 未执行：月营收、materialize derived features、Qlib bin/provider、accepted latest switching、Phase1 样本、单因子检验、模型训练、规则 baseline、前端/API、broker/orders/quick-trade/target position/target weight。",
        "",
        "## 2. 修改文件",
        "",
        "- 新增 `scripts/confirm_tw_decision_orthogonal_phase0d_pit_gate.py`。",
        "- 新增 `docs/tw_decision_model_orthogonal/PHASE0D_EXECUTION_REPORT_CN.md`。",
        "",
        "## 3. 生成文件",
        "",
        f"- `{rel(PHASE0D_CLEAN_DIR)}/`",
        f"- `{rel(PHASE0D_MANIFEST_PATH)}`",
        f"- `{rel(PHASE0D_COVERAGE_PATH)}`",
        f"- `{rel(PHASE0D_QUALITY_PATH)}`",
        f"- `{rel(PHASE0D_ALLOWED_FIELDS_PATH)}`",
        f"- `{rel(PHASE0D_REPORT_PATH)}`",
        "",
        "## 4. 数据来源",
        "",
        "- Phase0C normalized raw archive：`data_tw/experiments/decision_orthogonal/phase0c_raw_archive/`。",
        "- 本地交易日历来源：`qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/normalized_nonempty/*.csv` 的 `date` 列。",
        f"- 交易日历窗口：从 raw archive 最早交易日至最后交易日后 `{args.post_end_calendar_days}` 个自然日。",
        "",
        "## 5. Point-in-Time 处理",
        "",
        "- 保守可见性规则继续采用：`available_at = next_trading_day(trade_date)`。",
        "- `available_at` 不是官方发布时间声明，只是 Phase0D 继续验证所用的保守 T+1 可见性规则。",
        "- 对 Phase0C 尾部缺失 `available_at` 的行，首选从本地价格交易日历补下一交易日。",
        "- 不使用 `trade_date` 回填 `available_at`，不使用 `fetched_at` 作为历史可见时间。",
        "- cleaned view 只保留 `phase1_allowed=true` 且 `available_at` 非空的行；如无法补出下一交易日则排除。",
        "",
        "## 6. Category 汇总",
        "",
        md_table(
            category_summary,
            [
                "category",
                "raw_rows",
                "rows_with_non_empty_available_at",
                "rows_excluded_due_to_missing_available_at",
                "available_at_repaired_rows",
                "avg_pit_valid_coverage_rate",
                "avg_raw_observed_coverage_rate",
                "extra_dates_count",
                "missing_dates_count",
                "duplicate_rows_count",
                "quality_issue_count",
            ],
        ),
        "",
        "## 7. Per-Symbol 覆盖率样例",
        "",
        md_table(
            coverage_rows_out[:30],
            [
                "category",
                "symbol",
                "expected_trading_days",
                "raw_rows",
                "pit_valid_rows",
                "pit_valid_coverage_rate",
                "raw_observed_coverage_rate",
                "extra_dates_count",
                "missing_dates_count",
                "duplicate_rows_count",
                "quality_issue_count",
            ],
        ),
        "",
        "## 8. Quality Flags 汇总样例",
        "",
        md_table(quality_rows[:40], ["category", "symbol", "quality_flag_reason", "row_count"]),
        "",
        "## 9. 可进入后续审查字段",
        "",
        md_table(allowed_rows, ["category", "field", "phase1_allowed", "status", "notes"]),
        "",
        "## 10. Phase 0D Gate",
        "",
        f"- 是否满足 Phase0D PIT gate：`{str(phase0d_gate)}`。",
        "- 即使 Phase0D gate 为 true，也不代表已进入 Phase1；必须等待审查者给出下一步授权。",
        "",
        "## 11. 安全边界",
        "",
        "- 禁止联网：未触碰。",
        "- provider refresh/publish：未触碰。",
        "- accepted latest switching：未触碰。",
        "- materialize/screen/ablation：未执行。",
        "- Phase1 样本：未构建。",
        "- 单因子检验/模型训练：未执行。",
        "- broker/orders/quick-trade/target position/target weight：未触碰。",
        "- 前端/API：未触碰。",
        "- 真实交易建议语义：未生成。",
        "",
        "## 12. 风险与待审查问题",
        "",
        "- T+1 规则仍是保守可见性 proxy，不是官方发布时间证据；是否接受进入 Phase1 仍需审查者确认。",
        "- 月营收仍未授权且 deferred。",
        "- Phase0D 只确认 POC archive 的 PIT-clean 可用性，不代表允许扩大 universe、补齐历史或构建 Phase1 样本。",
        "",
    ]
    PHASE0D_REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Offline Phase 0D PIT gate confirmation.")
    parser.add_argument("--post-end-calendar-days", type=int, default=10)
    args = parser.parse_args()

    PHASE0D_CLEAN_DIR.mkdir(parents=True, exist_ok=True)
    inputs = load_phase0c_inputs()
    manifest_rows: list[dict[str, Any]] = []
    all_coverage: list[dict[str, Any]] = []
    all_quality: list[dict[str, Any]] = []

    for item in inputs:
        category = item["category"]
        raw_df = pd.read_csv(item["archive_path"], dtype={"stock_id": str})
        clean_df, stats = clean_one_archive(category, item["archive_path"], args.post_end_calendar_days)
        clean_path = PHASE0D_CLEAN_DIR / f"phase0d_{category}_pit_clean.csv"
        clean_df.to_csv(clean_path, index=False)

        start = str(pd.to_datetime(raw_df["trade_date"], errors="coerce").min().date())
        end = str(pd.to_datetime(raw_df["trade_date"], errors="coerce").max().date())
        all_coverage.extend(coverage_rows(category, raw_df, clean_df, start, end))
        all_quality.extend(quality_summary(category, clean_df, raw_df))

        manifest_rows.append(
            {
                "category": category,
                "source_raw_snapshot_id": item["raw_snapshot_id"],
                "source_archive_path": rel(item["archive_path"]),
                "clean_archive_path": rel(clean_path),
                "raw_rows": stats["raw_rows"],
                "pit_valid_rows": int(len(clean_df)),
                "rows_with_non_empty_available_at": int(clean_df["available_at"].astype(str).ne("").sum()) if not clean_df.empty else 0,
                "available_at_repaired_rows": stats["available_at_repaired_rows"],
                "excluded_missing_available_at_rows": stats["excluded_missing_available_at_rows"],
                "calendar_missing_symbols": stats["calendar_missing_symbols"],
                "first_trade_date": clean_df["trade_date"].astype(str).min() if not clean_df.empty else "",
                "last_trade_date": clean_df["trade_date"].astype(str).max() if not clean_df.empty else "",
                "available_at_rule": "available_at = next_trading_day(trade_date)",
                "checksum_or_size": sha256_size(clean_path),
            }
        )

    category_summary = aggregate_category(all_coverage, manifest_rows)
    allowed_rows = allowed_fields_rows(category_summary)
    phase0d_gate = all(row["phase1_allowed"] == "true" for row in allowed_rows if row["category"] in CATEGORY_FIELDS)

    write_csv(PHASE0D_MANIFEST_PATH, manifest_rows)
    write_csv(PHASE0D_COVERAGE_PATH, all_coverage)
    write_csv(PHASE0D_QUALITY_PATH, all_quality)
    write_csv(PHASE0D_ALLOWED_FIELDS_PATH, allowed_rows)
    write_report(args, category_summary, manifest_rows, all_coverage, all_quality, allowed_rows, phase0d_gate)

    print(
        {
            "status": "ok",
            "scope": "phase0d_offline_pit_gate_only",
            "phase0d_gate": phase0d_gate,
            "outputs": [
                rel(PHASE0D_CLEAN_DIR),
                rel(PHASE0D_MANIFEST_PATH),
                rel(PHASE0D_COVERAGE_PATH),
                rel(PHASE0D_QUALITY_PATH),
                rel(PHASE0D_ALLOWED_FIELDS_PATH),
                rel(PHASE0D_REPORT_PATH),
            ],
            "safety": {
                "network": False,
                "finmind_rerun": False,
                "provider_refresh_publish": False,
                "accepted_latest_switching": False,
                "phase1_samples": False,
                "factor_test": False,
                "model_training": False,
                "frontend_api": False,
                "broker_orders_quick_trade_target_positions": False,
            },
        }
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
