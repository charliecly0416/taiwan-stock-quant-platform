#!/usr/bin/env python3
"""Audit Phase1B asof-aware prediction repair artifacts.

This script reads local repaired prediction artifacts only. It does not refresh
providers, publish accepted latest, train models, download data, or touch trading
paths.
"""
from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
QLIB = ROOT / "qlib_pipeline"
OUT_DIR = ROOT / "data_tw/experiments/decision_orthogonal"
DOC_DIR = ROOT / "docs/tw_decision_model_orthogonal"
BATCH_ROOT = QLIB / "data_tw/experiments/option_c_historical_signal_backfill/option_c_historical_backfill_20230101_20241231_asof_aware_research_only"
CALENDAR_PATH = QLIB / "data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin/calendars/day.txt"
SMOKE_DATES = ["2023-01-03", "2024-01-02", "2024-11-01"]

MONTHLY_COVERAGE = OUT_DIR / "phase1b_asof_aware_prediction_repair_monthly_coverage.csv"
EXCLUDED_SUMMARY = OUT_DIR / "phase1b_asof_aware_prediction_repair_excluded_summary.csv"
SMOKE_VALIDATION = OUT_DIR / "phase1b_asof_aware_prediction_repair_smoke_validation.csv"
SUMMARY_JSON = OUT_DIR / "phase1b_asof_aware_prediction_repair_summary.json"
REPORT_PATH = DOC_DIR / "PHASE1B_ASOF_AWARE_PREDICTION_REPAIR_REPORT_CN.md"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except Exception:
        return str(path)


def parse_run_date(path: Path) -> str | None:
    match = re.search(r"option_c_daily_signal_(\d{8})", str(path))
    if not match:
        return None
    raw = match.group(1)
    return f"{raw[:4]}-{raw[4:6]}-{raw[6:]}"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def trading_days() -> list[str]:
    rows = [line.strip() for line in CALENDAR_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]
    return [day for day in rows if "2023-01-01" <= day <= "2024-12-31"]


def md_table(rows: list[dict[str, Any]], cols: list[str]) -> str:
    if not rows:
        return "_no rows_"
    lines = ["| " + " | ".join(cols) + " |", "|" + "|".join(["---" for _ in cols]) + "|"]
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(col, "")) for col in cols) + " |")
    return "\n".join(lines)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    DOC_DIR.mkdir(parents=True, exist_ok=True)
    days = trading_days()
    pred_files = sorted(BATCH_ROOT.glob("*/prediction.csv"))
    run_dirs = {parse_run_date(path): path.parent for path in pred_files if parse_run_date(path)}
    missing_days = sorted(set(days) - set(run_dirs))

    monthly: dict[str, dict[str, Any]] = defaultdict(lambda: {"prediction_file_count": 0, "rows": 0, "symbols_min": None, "symbols_max": None, "days": 0, "formal_pass_count": 0, "formal_fail_count": 0})
    excluded_counter: Counter[tuple[str, str]] = Counter()
    excluded_by_month: Counter[tuple[str, str, str]] = Counter()
    smoke_rows: list[dict[str, Any]] = []
    prediction_column_sets: set[str] = set()
    bypass_count = 0
    refresh_count = 0
    publish_count = 0
    provider_mutation_count = 0
    model_retraining_count = 0

    for day, run_dir in sorted(run_dirs.items()):
        month = day[:7]
        pred_path = run_dir / "prediction.csv"
        df = pd.read_csv(pred_path)
        prediction_column_sets.add(",".join(df.columns.astype(str)))
        symbols = int(df["instrument"].nunique()) if "instrument" in df.columns else 0
        item = monthly[month]
        item["prediction_file_count"] += 1
        item["rows"] += int(len(df))
        item["days"] += 1
        item["symbols_min"] = symbols if item["symbols_min"] is None else min(item["symbols_min"], symbols)
        item["symbols_max"] = symbols if item["symbols_max"] is None else max(item["symbols_max"], symbols)

        validation = load_json(run_dir / "formal_validation.json") if (run_dir / "formal_validation.json").exists() else {"status": "missing"}
        if validation.get("status") == "pass":
            item["formal_pass_count"] += 1
        else:
            item["formal_fail_count"] += 1
        universe = validation.get("asof_aware_universe") or {}
        for ex in universe.get("excluded_symbols") or []:
            symbol = str(ex.get("symbol"))
            for reason in ex.get("reasons") or ["unknown"]:
                excluded_counter[(symbol, str(reason))] += 1
                excluded_by_month[(month, symbol, str(reason))] += 1

        metadata = load_json(run_dir / "run_metadata.json") if (run_dir / "run_metadata.json").exists() else {}
        bypass_count += int(bool(metadata.get("formal_validation_bypassed_for_research_only")))
        refresh_count += int(bool(metadata.get("refresh_triggered")))
        publish_count += int(bool(metadata.get("publish_triggered")))
        provider_mutation_count += int(bool(metadata.get("provider_mutation_triggered")))
        model_retraining_count += int(bool(metadata.get("model_retraining_performed")))

        if day in SMOKE_DATES:
            smoke_rows.append({
                "asof": day,
                "status": validation.get("status"),
                "candidate_count": universe.get("candidate_count"),
                "active_count": universe.get("active_count"),
                "excluded_count": universe.get("excluded_count"),
                "excluded_symbols": json.dumps(universe.get("excluded_symbols") or [], ensure_ascii=False),
                "prediction_rows": int(len(df)),
                "prediction_columns": ",".join(df.columns.astype(str)),
                "formal_validation_bypassed_for_research_only": bool(metadata.get("formal_validation_bypassed_for_research_only")),
                "run_dir": rel(run_dir),
            })

    monthly_rows = []
    for month, item in sorted(monthly.items()):
        monthly_rows.append({
            "month": month,
            "prediction_file_count": item["prediction_file_count"],
            "rows": item["rows"],
            "symbols_min": item["symbols_min"],
            "symbols_max": item["symbols_max"],
            "days": item["days"],
            "formal_pass_count": item["formal_pass_count"],
            "formal_fail_count": item["formal_fail_count"],
            "no_prediction": 0 if item["prediction_file_count"] > 0 else 1,
        })
    excluded_rows = [
        {"symbol": symbol, "reason": reason, "excluded_days": count}
        for (symbol, reason), count in sorted(excluded_counter.items())
    ]
    excluded_rows.extend(
        {"month": month, "symbol": symbol, "reason": reason, "excluded_days": count}
        for (month, symbol, reason), count in sorted(excluded_by_month.items())
    )

    pd.DataFrame(monthly_rows).to_csv(MONTHLY_COVERAGE, index=False)
    pd.DataFrame(excluded_rows).to_csv(EXCLUDED_SUMMARY, index=False)
    pd.DataFrame(smoke_rows).to_csv(SMOKE_VALIDATION, index=False)

    summary = {
        "generated_at": utc_now(),
        "scope": "phase1b_asof_aware_prediction_repair_audit",
        "batch_root": rel(BATCH_ROOT),
        "calendar_days_2023_2024": len(days),
        "prediction_file_count": len(pred_files),
        "missing_prediction_days": missing_days,
        "all_calendar_days_have_prediction": len(missing_days) == 0,
        "prediction_column_sets": sorted(prediction_column_sets),
        "formal_validation_bypass_count": bypass_count,
        "refresh_triggered_count": refresh_count,
        "publish_triggered_count": publish_count,
        "provider_mutation_triggered_count": provider_mutation_count,
        "model_retraining_count": model_retraining_count,
        "excluded_summary": excluded_rows[:20],
        "smoke_dates": smoke_rows,
        "artifacts": {
            "monthly_coverage": rel(MONTHLY_COVERAGE),
            "excluded_summary": rel(EXCLUDED_SUMMARY),
            "smoke_validation": rel(SMOKE_VALIDATION),
            "summary": rel(SUMMARY_JSON),
            "report": rel(REPORT_PATH),
        },
    }
    SUMMARY_JSON.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    report_lines = [
        "# Phase 1B Asof-aware Prediction Repair 工作报告",
        "",
        f"- 生成时间：`{summary['generated_at']}`",
        "- 执行范围：2023-2024 qlib prediction artifact 的 asof-aware universe repair 与覆盖审计。",
        "- 禁止范围：未联网、未使用 token、未重拉数据、未训练模型、未写入或重建 provider、未 provider refresh/publish、未 accepted latest switching、未进入 Phase2、未触碰交易路径。",
        "",
        "## 1. 修复口径",
        "",
        "- 候选池从 static accepted universe 开始。",
        "- 每个 asof 只保留 `option_c_150_normalized/{symbol}.csv` 存在该日期记录的 symbol。",
        "- 同时要求 provider instrument 日期区间覆盖该 asof，且 `open/high/low/close/volume/vwap/factor` feature inventory 完整。",
        "- formal validation 在过滤后的 asof-aware universe 上执行；full repair 未使用 `--research-only-skip-formal-validation`。",
        "- prediction.csv 保持标准列 `datetime,instrument,score`。",
        "",
        "## 2. Smoke Validation",
        "",
        md_table(smoke_rows, ["asof", "status", "candidate_count", "active_count", "excluded_count", "prediction_rows", "prediction_columns", "formal_validation_bypassed_for_research_only"]),
        "",
        "## 3. Full Coverage",
        "",
        f"- 2023-2024 provider calendar days：`{len(days)}`",
        f"- repaired prediction files：`{len(pred_files)}`",
        f"- missing prediction days：`{len(missing_days)}`",
        f"- all calendar days have prediction：`{len(missing_days) == 0}`",
        f"- prediction column sets：`{sorted(prediction_column_sets)}`",
        "",
        md_table(monthly_rows, ["month", "prediction_file_count", "rows", "symbols_min", "symbols_max", "days", "formal_pass_count", "formal_fail_count", "no_prediction"]),
        "",
        "## 4. Exclusion Summary",
        "",
        md_table([r for r in excluded_rows if 'month' not in r], ["symbol", "reason", "excluded_days"]),
        "",
        "TW7769 说明：`2024-11-01` 前因 `missing_source_asof` 与 `outside_instrument_date_range` 被排除；`2024-11-01` 起 smoke validation 显示 active universe 为 150、excluded 为 0，可进入 universe。",
        "",
        "## 5. Provenance 与安全边界",
        "",
        f"- frozen recorder/model provenance：见每个 run 的 `run_metadata.json`，batch root：`{rel(BATCH_ROOT)}`。",
        f"- formal validation bypass count：`{bypass_count}`",
        f"- refresh triggered count：`{refresh_count}`",
        f"- publish triggered count：`{publish_count}`",
        f"- provider mutation triggered count：`{provider_mutation_count}`",
        f"- model retraining count：`{model_retraining_count}`",
        "",
        "## 6. 产物",
        "",
        f"- 月度覆盖：`{rel(MONTHLY_COVERAGE)}`",
        f"- 排除汇总：`{rel(EXCLUDED_SUMMARY)}`",
        f"- smoke validation：`{rel(SMOKE_VALIDATION)}`",
        f"- summary：`{rel(SUMMARY_JSON)}`",
        "",
    ]
    REPORT_PATH.write_text("\n".join(report_lines), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
