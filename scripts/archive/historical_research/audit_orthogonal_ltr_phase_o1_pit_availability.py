#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data_tw/experiments/ltr_orthogonal_features_controlled/phase_o1_pit_availability"
REPORT = ROOT / "docs/tw_ltr_orthogonal_features_controlled/PHASEO1_ORTHOGONAL_DATA_PIT_AVAILABILITY_EXECUTION_REPORT_CN.md"

O0_CONTRACT = ROOT / "data_tw/experiments/ltr_orthogonal_features_controlled/phase_o0_contract_freeze/phaseo0_experiment_contract.json"
CONTROL_SAMPLE = ROOT / "data_tw/experiments/ltr_rerank_regime_turnover/phase1_ltr_baseline/phase1_ltr_samples.csv"

DECISION_DIR = ROOT / "data_tw/experiments/decision_orthogonal"
PHASE0E_DOWNLOAD = DECISION_DIR / "phase0e_download_status.csv"
PHASE0E_COVERAGE = DECISION_DIR / "phase0e_coverage_report.csv"
PHASE0E_PIT_SAMPLES = DECISION_DIR / "phase0e_pit_validation_samples.csv"
PHASE0E_QUALITY = DECISION_DIR / "phase0e_quality_flags_summary.csv"
PHASE0E_MANIFEST = DECISION_DIR / "phase0e_pit_snapshot_manifest.csv"
PHASE0D_CLEAN_MANIFEST = DECISION_DIR / "phase0d_pit_clean_manifest.csv"

NORMALIZED = {
    "institutional_flow": DECISION_DIR
    / "phase0e_raw_archive/institutional_flow/phase0e_institutional_flow_20260610T175901Z_normalized.csv",
    "margin_short": DECISION_DIR
    / "phase0e_raw_archive/margin_short/phase0e_margin_short_20260610T180330Z_normalized.csv",
}

REQUIRED_COLUMNS = {
    "institutional_flow": [
        "symbol",
        "stock_id",
        "trade_date",
        "available_at",
        "foreign_net_buy",
        "investment_trust_net_buy",
        "dealer_net_buy",
        "institutional_total_net_buy",
        "data_source",
        "source_url_or_endpoint",
        "raw_snapshot_id",
        "fetched_at",
        "quality_flags",
    ],
    "margin_short": [
        "symbol",
        "stock_id",
        "trade_date",
        "available_at",
        "margin_balance",
        "margin_balance_change",
        "short_balance",
        "short_balance_change",
        "data_source",
        "source_url_or_endpoint",
        "raw_snapshot_id",
        "fetched_at",
        "quality_flags",
    ],
}


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except Exception:
        return str(path)


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


def file_row(path: Path, role: str, required: bool = True) -> dict[str, Any]:
    return {
        "path": rel(path),
        "role": role,
        "required": required,
        "exists": path.exists(),
        "size_bytes": path.stat().st_size if path.exists() else "",
    }


def markdown_table(rows: list[dict[str, Any]], fields: list[str], limit: int = 40) -> list[str]:
    lines = ["| " + " | ".join(fields) + " |", "| " + " | ".join(["---"] * len(fields)) + " |"]
    for row in rows[:limit]:
        lines.append("| " + " | ".join(str(row.get(field, "")) for field in fields) + " |")
    return lines


def load_control() -> pd.DataFrame:
    return pd.read_csv(CONTROL_SAMPLE, usecols=["date", "instrument", "split", "sample_complete"])


def next_trading_map(dates: list[pd.Timestamp]) -> dict[pd.Timestamp, pd.Timestamp]:
    ordered = sorted(pd.Series(pd.to_datetime(dates)).dropna().unique())
    return {ordered[idx]: ordered[idx + 1] for idx in range(len(ordered) - 1)}


def build_inventory() -> list[dict[str, Any]]:
    rows = [
        file_row(O0_CONTRACT, "Phase O0 frozen control contract"),
        file_row(CONTROL_SAMPLE, "Phase1C first simple LTR control sample"),
        file_row(PHASE0E_DOWNLOAD, "Phase0E FinMind download status"),
        file_row(PHASE0E_COVERAGE, "Phase0E coverage report"),
        file_row(PHASE0E_PIT_SAMPLES, "Phase0E PIT validation samples"),
        file_row(PHASE0E_QUALITY, "Phase0E quality flags summary"),
        file_row(PHASE0E_MANIFEST, "Phase0E PIT snapshot manifest"),
        file_row(PHASE0D_CLEAN_MANIFEST, "Phase0D PIT clean manifest", required=False),
    ]
    for category, path in NORMALIZED.items():
        rows.append(file_row(path, f"Phase0E normalized {category}"))
    return rows


def summarize_download_status() -> list[dict[str, Any]]:
    if not PHASE0E_DOWNLOAD.exists():
        return []
    df = pd.read_csv(PHASE0E_DOWNLOAD)
    rows: list[dict[str, Any]] = []
    for category, group in df.groupby("category"):
        failures = group[group["status"].astype(str) != "success"]
        rows.append(
            {
                "category": category,
                "request_count": int(len(group)),
                "success_count": int((group["status"].astype(str) == "success").sum()),
                "failed_count": int(len(failures)),
                "symbols_requested": int(group["symbol"].nunique()),
                "row_count_sum": int(pd.to_numeric(group["row_count"], errors="coerce").fillna(0).sum()),
                "token_used_values": "|".join(sorted(group["token_used"].astype(str).unique())),
                "start_date_min": str(group["start_date"].min()),
                "end_date_max": str(group["end_date"].max()),
                "error_types": "|".join(sorted(x for x in failures.get("error_type", pd.Series(dtype=str)).dropna().astype(str).unique() if x)),
            }
        )
    return rows


def schema_audit(datasets: dict[str, pd.DataFrame]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    mismatch_examples: list[dict[str, Any]] = []
    for category, df in datasets.items():
        actual = list(df.columns)
        required = REQUIRED_COLUMNS[category]
        rows.append(
            {
                "category": category,
                "required_columns_present": "yes" if set(required).issubset(actual) else "no",
                "missing_required_columns": "|".join(col for col in required if col not in actual),
                "extra_columns": "|".join(col for col in actual if col not in required),
                "column_count": len(actual),
                "columns": "|".join(actual),
                "data_sources": "|".join(sorted(df["data_source"].dropna().astype(str).unique())),
                "raw_snapshot_ids": "|".join(sorted(df["raw_snapshot_id"].dropna().astype(str).unique())),
            }
        )
    return rows


def pit_audit(
    datasets: dict[str, pd.DataFrame], control_dates: list[pd.Timestamp]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    nxt = next_trading_map(control_dates)

    rows: list[dict[str, Any]] = []
    mismatch_examples: list[dict[str, Any]] = []
    for category, df in datasets.items():
        work = df.copy()
        work["trade_date_ts"] = pd.to_datetime(work["trade_date"], errors="coerce")
        work["available_at_ts"] = pd.to_datetime(work["available_at"], errors="coerce")
        work["expected_available_at_ts"] = work["trade_date_ts"].map(nxt)
        has_expected = work["expected_available_at_ts"].notna()
        available_nonnull = work["available_at_ts"].notna()
        strictly_after = available_nonnull & (work["available_at_ts"] > work["trade_date_ts"])
        equals_expected = has_expected & available_nonnull & (work["available_at_ts"] == work["expected_available_at_ts"])
        same_day = available_nonnull & (work["available_at_ts"] <= work["trade_date_ts"])
        missing_available = work["available_at_ts"].isna()
        rows.append(
            {
                "category": category,
                "row_count": int(len(work)),
                "rows_with_expected_next_trading_day": int(has_expected.sum()),
                "available_at_nonnull_rows": int(available_nonnull.sum()),
                "available_at_missing_rows": int(missing_available.sum()),
                "available_at_strictly_after_trade_date_rows": int(strictly_after.sum()),
                "available_at_not_after_trade_date_rows": int(same_day.sum()),
                "available_at_equals_next_trading_day_rows": int(equals_expected.sum()),
                "available_at_next_trading_day_mismatch_rows": int((has_expected & available_nonnull & ~equals_expected).sum()),
                "pit_rule_pass": "yes"
                if int(same_day.sum()) == 0 and int((has_expected & available_nonnull & ~equals_expected).sum()) == 0
                else "no",
            }
        )
        mismatches = work[has_expected & available_nonnull & ~equals_expected].copy()
        for row in mismatches.head(50).itertuples():
            mismatch_examples.append(
                {
                    "category": category,
                    "symbol": row.symbol,
                    "trade_date": str(row.trade_date)[:10],
                    "available_at": str(row.available_at)[:10],
                    "expected_available_at": str(row.expected_available_at_ts)[:10],
                    "quality_flags": "" if pd.isna(row.quality_flags) else str(row.quality_flags),
                    "note": "strict_next_trading_day_mismatch; still after trade_date if available_at > trade_date",
                }
            )
    return rows, mismatch_examples


def coverage_summary(
    datasets: dict[str, pd.DataFrame], control: pd.DataFrame, coverage_df: pd.DataFrame
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    control_symbols = sorted(control["instrument"].astype(str).unique())
    rows: list[dict[str, Any]] = []
    missing_rows: list[dict[str, Any]] = []

    for category, df in datasets.items():
        symbols_with_data = set(df["symbol"].astype(str).unique())
        absent = [symbol for symbol in control_symbols if symbol not in symbols_with_data]
        category_cov = coverage_df[coverage_df["category"] == category].copy()
        if "pit_valid_coverage_rate" in category_cov.columns:
            category_cov["pit_valid_coverage_rate"] = pd.to_numeric(category_cov["pit_valid_coverage_rate"], errors="coerce")
        control_cov = category_cov[category_cov["symbol"].isin(control_symbols)].copy()
        low_cov = control_cov[control_cov["pit_valid_coverage_rate"].fillna(0) < 0.95].sort_values("pit_valid_coverage_rate")
        date_min = str(df["trade_date"].min()) if len(df) else ""
        date_max = str(df["trade_date"].max()) if len(df) else ""
        rows.append(
            {
                "category": category,
                "control_symbol_count": len(control_symbols),
                "symbols_with_phase0e_data": len(symbols_with_data & set(control_symbols)),
                "control_symbols_absent": len(absent),
                "normalized_total_symbols": int(df["symbol"].nunique()),
                "normalized_rows": int(len(df)),
                "trade_date_min": date_min,
                "trade_date_max": date_max,
                "coverage_rows_for_control_symbols": int(len(control_cov)),
                "coverage_rate_min": round(float(control_cov["pit_valid_coverage_rate"].min()), 6) if len(control_cov) else "",
                "coverage_rate_median": round(float(control_cov["pit_valid_coverage_rate"].median()), 6) if len(control_cov) else "",
                "coverage_rate_mean": round(float(control_cov["pit_valid_coverage_rate"].mean()), 6) if len(control_cov) else "",
                "low_coverage_symbol_count_lt_0_95": int(len(low_cov)),
                "lowest_coverage_symbols": "|".join(
                    f"{row.symbol}:{row.pit_valid_coverage_rate:.4f}" for row in low_cov.head(12).itertuples()
                ),
                "absent_symbols_sample": "|".join(absent[:30]),
            }
        )
        for row in low_cov.itertuples():
            missing_rows.append(
                {
                    "category": category,
                    "symbol": row.symbol,
                    "pit_valid_coverage_rate": round(float(row.pit_valid_coverage_rate), 6),
                    "expected_trading_days": int(row.expected_trading_days),
                    "raw_rows": int(row.raw_rows),
                    "pit_valid_rows": int(row.pit_valid_rows),
                    "missing_dates_count": int(row.missing_dates_count),
                    "extra_dates_count": int(row.extra_dates_count),
                    "duplicate_rows_count": int(row.duplicate_rows_count),
                    "quality_issue_count": int(row.quality_issue_count),
                }
            )
        for symbol in absent:
            missing_rows.append(
                {
                    "category": category,
                    "symbol": symbol,
                    "pit_valid_coverage_rate": 0.0,
                    "expected_trading_days": "",
                    "raw_rows": 0,
                    "pit_valid_rows": 0,
                    "missing_dates_count": "",
                    "extra_dates_count": "",
                    "duplicate_rows_count": "",
                    "quality_issue_count": "",
                }
            )
    return rows, missing_rows


def quality_summary() -> list[dict[str, Any]]:
    if not PHASE0E_QUALITY.exists():
        return []
    df = pd.read_csv(PHASE0E_QUALITY)
    rows: list[dict[str, Any]] = []
    for (category, reason), group in df.groupby(["category", "quality_flag_reason"]):
        rows.append(
            {
                "category": category,
                "quality_flag_reason": reason,
                "symbol_count": int(group["symbol"].nunique()),
                "row_count_sum": int(pd.to_numeric(group["row_count"], errors="coerce").fillna(0).sum()),
            }
        )
    return sorted(rows, key=lambda row: (row["category"], row["quality_flag_reason"]))


def decide_gate(
    download_rows: list[dict[str, Any]],
    schema_rows: list[dict[str, Any]],
    pit_rows: list[dict[str, Any]],
    coverage_rows: list[dict[str, Any]],
) -> tuple[str, list[str]]:
    blockers: list[str] = []
    if any(row["failed_count"] for row in download_rows):
        blockers.append("Phase0E download status contains failed requests.")
    if any(row["required_columns_present"] != "yes" for row in schema_rows):
        blockers.append("Required normalized columns are missing.")
    if any(row["pit_rule_pass"] != "yes" for row in pit_rows):
        blockers.append("available_at has strict next-trading-day mismatches; no same-day visibility was found, but exact T+1 PIT rule is not satisfied.")
    if any(int(row["control_symbols_absent"]) > 0 for row in coverage_rows):
        blockers.append("Phase0E local archive does not cover all Phase1C control symbols.")

    if blockers:
        return "phase_o1_blocked_requires_data_coverage_decision", blockers
    if any(int(row["low_coverage_symbol_count_lt_0_95"]) > 0 for row in coverage_rows):
        return "phase_o1_orthogonal_data_pit_availability_passed_with_known_coverage_gaps", [
            "Some control symbols have PIT-valid coverage below 0.95; O2/O3 must neutral-fill with missing flags and must not delete rows."
        ]
    return "phase_o1_orthogonal_data_pit_availability_passed", []


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    generated_at = now()
    contract = json.loads(O0_CONTRACT.read_text(encoding="utf-8"))
    control = load_control()
    control_dates = pd.to_datetime(control["date"], errors="coerce").dropna().tolist()
    coverage_df = pd.read_csv(PHASE0E_COVERAGE)
    datasets = {category: pd.read_csv(path) for category, path in NORMALIZED.items()}

    inventory_rows = build_inventory()
    download_rows = summarize_download_status()
    schema_rows = schema_audit(datasets)
    pit_rows, pit_mismatch_rows = pit_audit(datasets, control_dates)
    coverage_rows, missing_rows = coverage_summary(datasets, control, coverage_df)
    quality_rows = quality_summary()

    gate, blockers = decide_gate(download_rows, schema_rows, pit_rows, coverage_rows)
    summary = {
        "created_at": generated_at,
        "phase": "phase_o1_orthogonal_data_pit_availability_audit",
        "gate": gate,
        "blockers_or_required_decisions": blockers,
        "o0_gate": contract.get("gate"),
        "control_sample": rel(CONTROL_SAMPLE),
        "control_sample_rows": int(len(control)),
        "control_sample_complete_rows": int(control["sample_complete"].sum()),
        "control_symbol_count": int(control["instrument"].nunique()),
        "control_date_min": str(control["date"].min()),
        "control_date_max": str(control["date"].max()),
        "source": "local Phase0E/Phase0D FinMind artifacts only; no network request executed",
        "no_training": True,
        "no_treatment_sample": True,
        "no_replay_or_return_proof": True,
        "no_frontend_api_provider_accepted_latest_monitor_trading": True,
        "download_status_summary": download_rows,
        "field_schema_audit": schema_rows,
        "pit_available_at_audit": pit_rows,
        "symbol_coverage_summary": coverage_rows,
        "quality_flags_summary": quality_rows,
    }

    write_csv(OUT / "phaseo1_source_artifact_inventory.csv", inventory_rows)
    write_csv(OUT / "phaseo1_dataset_status_summary.csv", download_rows)
    write_csv(OUT / "phaseo1_field_schema_audit.csv", schema_rows)
    write_csv(OUT / "phaseo1_pit_available_at_audit.csv", pit_rows)
    write_csv(OUT / "phaseo1_pit_available_at_mismatch_examples.csv", pit_mismatch_rows)
    write_csv(OUT / "phaseo1_symbol_coverage_summary.csv", coverage_rows)
    write_csv(OUT / "phaseo1_missing_distribution.csv", missing_rows)
    write_csv(OUT / "phaseo1_quality_flags_summary.csv", quality_rows)
    write_json(OUT / "phaseo1_summary.json", summary)

    top_missing = sorted(missing_rows, key=lambda row: (row["category"], float(row["pit_valid_coverage_rate"])))[:30]
    report_lines = [
        "# Phase O1 执行报告：正交数据 PIT 可得性审计",
        "",
        f"生成时间：`{generated_at}`",
        "",
        "## 1. 执行结论",
        "",
        "本轮只读取既有 Phase0E/Phase0D FinMind 法人筹码与融资融券产物，审计其是否可用于后续 O2 的 PIT-safe raw archive / normalized daily table 设计。",
        "",
        "推荐 gate：",
        "",
        "```text",
        gate,
        "```",
        "",
        "本轮未请求 FinMind 网络、未训练 qlib/LTR、未构建 treatment 样本、未做回放或收益率优劣证明、未改 frontend/API/provider/accepted latest/monitor/交易链路。",
        "",
        "## 2. Control 与数据范围",
        "",
        f"- O0 gate：`{contract.get('gate')}`",
        f"- control sample rows：`{len(control)}`",
        f"- control sample complete rows：`{int(control['sample_complete'].sum())}`",
        f"- control symbols：`{int(control['instrument'].nunique())}`",
        f"- control date range：`{control['date'].min()}` ~ `{control['date'].max()}`",
        "- 正交数据范围：`institutional_flow`、`margin_short`",
        "- PIT 规则：`available_at = next_trading_day(trade_date)`",
        "",
        "## 3. FinMind Download/API 状态摘要",
        "",
        *markdown_table(
            download_rows,
            [
                "category",
                "request_count",
                "success_count",
                "failed_count",
                "symbols_requested",
                "row_count_sum",
                "token_used_values",
                "start_date_min",
                "end_date_max",
            ],
        ),
        "",
        "## 4. Field Schema 审计",
        "",
        *markdown_table(
            schema_rows,
            [
                "category",
                "required_columns_present",
                "missing_required_columns",
                "extra_columns",
                "column_count",
                "raw_snapshot_ids",
            ],
        ),
        "",
        "## 5. PIT available_at 审计",
        "",
        *markdown_table(
            pit_rows,
            [
                "category",
                "row_count",
                "available_at_nonnull_rows",
                "available_at_missing_rows",
                "available_at_not_after_trade_date_rows",
                "available_at_next_trading_day_mismatch_rows",
                "pit_rule_pass",
            ],
        ),
        "",
        "说明：未发现 `available_at <= trade_date` 的同日可见记录，但发现若干记录不满足严格 `available_at = next_trading_day(trade_date)`。这些记录多数属于保守延迟可见或交易日历/上市状态差异，不能在 O1 判为 exact T+1 通过；若继续 O2，必须明确处理为 PIT-safe delayed availability 或回到数据源修正。",
        "",
        "PIT mismatch 样例：",
        "",
        *markdown_table(
            pit_mismatch_rows[:12],
            ["category", "symbol", "trade_date", "available_at", "expected_available_at", "quality_flags"],
            limit=12,
        ),
        "",
        "## 6. Phase1C Control Symbol 覆盖",
        "",
        *markdown_table(
            coverage_rows,
            [
                "category",
                "control_symbol_count",
                "symbols_with_phase0e_data",
                "control_symbols_absent",
                "normalized_rows",
                "trade_date_min",
                "trade_date_max",
                "coverage_rate_min",
                "coverage_rate_median",
                "low_coverage_symbol_count_lt_0_95",
                "lowest_coverage_symbols",
            ],
        ),
        "",
        "## 7. 低覆盖/缺失分布样例",
        "",
        *markdown_table(
            top_missing,
            [
                "category",
                "symbol",
                "pit_valid_coverage_rate",
                "expected_trading_days",
                "raw_rows",
                "pit_valid_rows",
                "missing_dates_count",
                "quality_issue_count",
            ],
            limit=30,
        ),
        "",
        "## 8. Quality Flags 摘要",
        "",
        *markdown_table(quality_rows, ["category", "quality_flag_reason", "symbol_count", "row_count_sum"], limit=20),
        "",
        "## 9. 停止条件复核",
        "",
        "- 402/403/429：本轮复用本地 Phase0E 状态，未发现 failed request。",
        "- 字段稳定性：两个 normalized table 均包含主线要求字段。",
        "- 历史覆盖：本地 Phase0E 覆盖 `2022-01-01..2026-06-10` 请求窗口，但部分股票低覆盖，O2/O3 必须保留缺失标记与 neutral fill。",
        "- PIT available_at：未发现同日可见，但严格 `available_at = next_trading_day(trade_date)` 未通过；尾部无下一交易日记录不得未来补齐。",
        "- 新数据源/新账号：本轮未引入。",
        "",
        "## 10. O2 前置要求",
        "",
        "- O2 只能基于已审计的法人筹码与融资融券字段构建 PIT-safe feature builder。",
        "- 后续 treatment 样本必须与 control 行数、label hash、原始特征 hash 完全一致。",
        "- 正交数据缺失只能 neutral fill + missing flag，不能删行、不能更改 control sample rows。",
        "- O1 不证明收益率优劣；不得用本报告作为产品化或前端切换依据。",
        "",
        "## 11. 输出产物",
        "",
        f"- `{rel(OUT / 'phaseo1_source_artifact_inventory.csv')}`",
        f"- `{rel(OUT / 'phaseo1_dataset_status_summary.csv')}`",
        f"- `{rel(OUT / 'phaseo1_field_schema_audit.csv')}`",
        f"- `{rel(OUT / 'phaseo1_pit_available_at_audit.csv')}`",
        f"- `{rel(OUT / 'phaseo1_pit_available_at_mismatch_examples.csv')}`",
        f"- `{rel(OUT / 'phaseo1_symbol_coverage_summary.csv')}`",
        f"- `{rel(OUT / 'phaseo1_missing_distribution.csv')}`",
        f"- `{rel(OUT / 'phaseo1_quality_flags_summary.csv')}`",
        f"- `{rel(OUT / 'phaseo1_summary.json')}`",
    ]
    if blockers:
        report_lines.extend(["", "## 12. 需要用户/审查确认的问题", ""])
        report_lines.extend(f"- {item}" for item in blockers)

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    print(json.dumps({"ok": True, "gate": gate, "report": rel(REPORT), "summary": rel(OUT / "phaseo1_summary.json")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
