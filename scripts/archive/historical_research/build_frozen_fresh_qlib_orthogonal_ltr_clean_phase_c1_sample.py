#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
C0_MANIFEST = ROOT / "data_tw/experiments/frozen_fresh_qlib_orthogonal_ltr_clean/phase_c0_contract_and_feasibility/phasec0_contract_manifest.json"
S2B_SCORE = ROOT / "data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2b_fresh_qlib_training/phase_s2b_post_filter_score_rank.csv"
O3_SAMPLE = ROOT / "data_tw/experiments/ltr_orthogonal_features_controlled/phase_o3_row_aligned_treatment_sample/phaseo3_treatment_candidate_sample.csv"
O4_FEATURES = ROOT / "data_tw/experiments/ltr_orthogonal_features_controlled/phase_o4_controlled_treatment_ltr/phaseo4_training_feature_whitelist.csv"
O4_MANIFEST = ROOT / "data_tw/experiments/ltr_orthogonal_features_controlled/phase_o4_controlled_treatment_ltr/phaseo4_training_manifest.json"

OUT_DIR = ROOT / "data_tw/experiments/frozen_fresh_qlib_orthogonal_ltr_clean/phase_c1_row_aligned_sample"
DOC = ROOT / "docs/tw_frozen_fresh_qlib_orthogonal_ltr_clean/PHASEC1_ROW_ALIGNED_SAMPLE_EXECUTION_REPORT_CN.md"

MANIFEST_JSON = OUT_DIR / "phasec1_sample_manifest.json"
TRAIN_CSV = OUT_DIR / "phasec1_ltr_train_sample_2025.csv"
TEST_CSV = OUT_DIR / "phasec1_ltr_test_sample_2026.csv"
FEATURE_SCHEMA_CSV = OUT_DIR / "phasec1_feature_schema.csv"
ROW_ALIGNMENT_CSV = OUT_DIR / "phasec1_row_alignment_audit.csv"
SCORE_PROVENANCE_CSV = OUT_DIR / "phasec1_score_provenance_audit.csv"
PIT_AUDIT_CSV = OUT_DIR / "phasec1_pit_leakage_audit.csv"
MISSING_CSV = OUT_DIR / "phasec1_missing_report.csv"
LABEL_AUDIT_CSV = OUT_DIR / "phasec1_label_audit.csv"
FORBIDDEN_JSON = OUT_DIR / "phasec1_forbidden_action_audit.json"

QLIB_TRAIN_END = "2024-12-31"
TRAIN_START = "2025-01-01"
TRAIN_END = "2025-12-31"
TEST_START = "2026-01-01"
TEST_END = "2026-05-07"
GATE = "phase_c1_clean_stacking_sample_passed"


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except Exception:
        return str(path)


def wjson(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, default=str) + "\n", encoding="utf-8")


def wcsv(path: Path, rows: list[dict[str, Any]], fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        fields = sorted({key for row in rows for key in row.keys()})
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def df_hash(df: pd.DataFrame, cols: list[str]) -> str:
    text = df[cols].astype("string").fillna("<NA>").to_csv(index=False)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def top_heavy_label(rank: pd.Series) -> pd.Series:
    r = pd.to_numeric(rank, errors="coerce").fillna(0)
    return np.select([r >= 0.90, r >= 0.80, r >= 0.70, r >= 0.50], [4, 3, 2, 1], default=0).astype(int)


def require_inputs() -> tuple[dict[str, Any], dict[str, Any]]:
    required = [C0_MANIFEST, S2B_SCORE, O3_SAMPLE, O4_FEATURES, O4_MANIFEST]
    missing = [rel(path) for path in required if not path.exists()]
    if missing:
        raise RuntimeError(f"Missing C1 inputs: {missing}")
    c0 = load_json(C0_MANIFEST)
    if c0.get("gate") != "phase_c0_clean_stacking_contract_feasible":
        raise RuntimeError(f"C0 gate is not feasible: {c0.get('gate')}")
    o4 = load_json(O4_MANIFEST)
    if o4.get("gate") != "phase_o4_controlled_treatment_ltr_trained":
        raise RuntimeError(f"O4 manifest gate unavailable: {o4.get('gate')}")
    return c0, o4


def norm(symbol: str) -> str:
    text = str(symbol or "").strip().upper()
    return text if text.startswith("TW") else f"TW{text}"


def load_feature_schema() -> pd.DataFrame:
    schema = pd.read_csv(O4_FEATURES)
    if "feature" not in schema.columns:
        raise RuntimeError("O4 feature whitelist missing feature column")
    return schema


def frozen_top50_scores() -> pd.DataFrame:
    score = pd.read_csv(S2B_SCORE, parse_dates=["date"])
    score["instrument"] = score["instrument"].map(norm)
    score["date_str"] = score["date"].dt.strftime("%Y-%m-%d")
    score = score[(score["date_str"] >= TRAIN_START) & (score["date_str"] <= TEST_END)].copy()
    score = score[pd.to_numeric(score["qlib_rank"], errors="coerce") <= 50].copy()
    score = score.sort_values(["date", "qlib_rank", "instrument"]).reset_index(drop=True)
    score["clean_ltr_split"] = np.where(score["date_str"] <= TRAIN_END, "train", "test")

    grouped = score.groupby("date")
    score["qlib_score_percentile_by_date"] = grouped["qlib_score_raw"].rank(pct=True, method="average")
    mean = grouped["qlib_score_raw"].transform("mean")
    std = grouped["qlib_score_raw"].transform(lambda s: float(s.std(ddof=0)) if len(s) else 0.0)
    score["qlib_score_zscore_by_date"] = np.where(std > 0, (score["qlib_score_raw"] - mean) / std, 0.0)
    score["top10_flag"] = (score["qlib_rank"] <= 10).astype(int)
    score["top30_flag"] = (score["qlib_rank"] <= 30).astype(int)
    score["top50_flag"] = (score["qlib_rank"] <= 50).astype(int)
    score = score.sort_values(["instrument", "date"]).reset_index(drop=True)
    for lag in [1, 3, 5]:
        score[f"rank_change_{lag}d"] = score.groupby("instrument")["qlib_rank"].diff(lag)
    score["top30_streak"] = score.groupby("instrument")["top30_flag"].transform(lambda s: s.groupby((s != s.shift()).cumsum()).cumsum())
    score["top50_streak"] = score.groupby("instrument")["top50_flag"].transform(lambda s: s.groupby((s != s.shift()).cumsum()).cumsum())
    return score.sort_values(["date", "qlib_rank", "instrument"]).reset_index(drop=True)


def selected_o3_columns(feature_cols: list[str]) -> list[str]:
    metadata = [
        "control_row_id",
        "date",
        "instrument",
        "year",
        "split",
        "regime_segment",
        "future_return_5d",
        "future_return_10d",
        "future_return_20d",
        "future_excess_return_5d",
        "future_excess_return_10d",
        "future_excess_return_20d",
        "future_excess_return_rank_5d",
        "future_excess_return_rank_10d",
        "future_excess_return_rank_20d",
        "topk_forward_bucket",
        "ltr_relevance_label",
        "label_complete_5d",
        "label_complete_10d",
        "label_complete_20d",
        "feature_complete",
        "sample_complete",
        "institutional_flow_trade_date",
        "institutional_flow_available_at",
        "institutional_flow_raw_snapshot_id",
        "institutional_flow_delay_reason",
        "institutional_flow_available_at_contract",
        "institutional_flow_raw_snapshot_path",
        "institutional_flow_lineage_source",
        "institutional_flow_used_available_at_gt_sample_date",
        "institutional_flow_used_trade_date_gt_sample_date",
        "margin_short_trade_date",
        "margin_short_available_at",
        "margin_short_raw_snapshot_id",
        "margin_short_delay_reason",
        "margin_short_available_at_contract",
        "margin_short_raw_snapshot_path",
        "margin_short_lineage_source",
        "margin_short_used_available_at_gt_sample_date",
        "margin_short_used_trade_date_gt_sample_date",
    ]
    qlib_derived = {
        "qlib_score_raw",
        "qlib_rank",
        "qlib_score_percentile_by_date",
        "qlib_score_zscore_by_date",
        "rank_change_1d",
        "rank_change_3d",
        "rank_change_5d",
        "top10_flag",
        "top30_flag",
        "top50_flag",
        "top30_streak",
        "top50_streak",
    }
    cols = metadata + [col for col in feature_cols if col not in qlib_derived]
    return sorted(set(cols), key=cols.index)


def build_samples(feature_cols: list[str]) -> pd.DataFrame:
    top50 = frozen_top50_scores()
    o3_cols = selected_o3_columns(feature_cols)
    o3 = pd.read_csv(O3_SAMPLE, usecols=lambda c: c in set(o3_cols), parse_dates=["date"])
    o3["instrument"] = o3["instrument"].map(norm)
    o3["date_str"] = o3["date"].dt.strftime("%Y-%m-%d")
    merged = top50.merge(o3, on=["date", "date_str", "instrument"], how="left", validate="one_to_one", suffixes=("", "_o3"))
    if merged["control_row_id"].isna().any():
        missing = merged[merged["control_row_id"].isna()][["date_str", "instrument"]].head(20).to_dict("records")
        raise RuntimeError(f"C1 O3 row alignment missing for frozen top50 rows: {missing}")
    merged["relevance_10d_top_heavy"] = top_heavy_label(merged["future_excess_return_rank_10d"])
    merged["c1_sample_split"] = merged["clean_ltr_split"].map({"train": "ltr_train_2025", "test": "ltr_test_2026"})
    merged["score_source"] = rel(S2B_SCORE)
    merged["same_frozen_fresh_qlib_score_source"] = True
    merged["after_fresh_qlib_train_end"] = merged["date_str"] > QLIB_TRAIN_END
    merged["preserve_scope"] = "top50_only"
    merged = merged.sort_values(["date", "qlib_rank", "instrument"]).reset_index(drop=True)
    ordered_cols = [
        "control_row_id",
        "date",
        "date_str",
        "instrument",
        "c1_sample_split",
        "year",
        "regime_segment",
        "preserve_scope",
        "score_source",
        "same_frozen_fresh_qlib_score_source",
        "after_fresh_qlib_train_end",
    ] + feature_cols + [
        "future_return_5d",
        "future_return_10d",
        "future_return_20d",
        "future_excess_return_5d",
        "future_excess_return_10d",
        "future_excess_return_20d",
        "future_excess_return_rank_5d",
        "future_excess_return_rank_10d",
        "future_excess_return_rank_20d",
        "relevance_10d_top_heavy",
        "topk_forward_bucket",
        "ltr_relevance_label",
        "label_complete_5d",
        "label_complete_10d",
        "label_complete_20d",
        "feature_complete",
        "sample_complete",
        "institutional_flow_trade_date",
        "institutional_flow_available_at",
        "institutional_flow_raw_snapshot_id",
        "institutional_flow_delay_reason",
        "institutional_flow_available_at_contract",
        "institutional_flow_raw_snapshot_path",
        "institutional_flow_lineage_source",
        "institutional_flow_used_available_at_gt_sample_date",
        "institutional_flow_used_trade_date_gt_sample_date",
        "margin_short_trade_date",
        "margin_short_available_at",
        "margin_short_raw_snapshot_id",
        "margin_short_delay_reason",
        "margin_short_available_at_contract",
        "margin_short_raw_snapshot_path",
        "margin_short_lineage_source",
        "margin_short_used_available_at_gt_sample_date",
        "margin_short_used_trade_date_gt_sample_date",
    ]
    ordered_cols = [col for col in ordered_cols if col in merged.columns]
    return merged[ordered_cols].copy()


def row_alignment_audit(df: pd.DataFrame) -> list[dict[str, Any]]:
    rows = []
    for split, sub in df.groupby("c1_sample_split"):
        daily = sub.groupby("date_str", as_index=False).size()
        rows.append(
            {
                "split": split,
                "start_date": str(sub["date_str"].min()),
                "end_date": str(sub["date_str"].max()),
                "row_count": int(sub.shape[0]),
                "date_count": int(daily.shape[0]),
                "daily_rows_min": int(daily["size"].min()),
                "daily_rows_median": float(daily["size"].median()),
                "daily_rows_max": int(daily["size"].max()),
                "duplicate_key_count": int(sub.duplicated(["date_str", "instrument"]).sum()),
                "top50_scope_rows": int((sub["qlib_rank"].astype(float) <= 50).sum()),
                "all_rows_after_qlib_train_end": bool(sub["after_fresh_qlib_train_end"].all()),
                "all_same_frozen_score_source": bool(sub["same_frozen_fresh_qlib_score_source"].all()),
            }
        )
    return rows


def score_provenance_audit(df: pd.DataFrame) -> list[dict[str, Any]]:
    rows = []
    for split, sub in df.groupby("c1_sample_split"):
        rows.append(
            {
                "split": split,
                "score_source": rel(S2B_SCORE),
                "row_count": int(sub.shape[0]),
                "score_missing_rows": int(sub["qlib_score_raw"].isna().sum()),
                "rank_missing_rows": int(sub["qlib_rank"].isna().sum()),
                "qlib_in_sample_rows_2017_2024": int((sub["date_str"] <= QLIB_TRAIN_END).sum()),
                "walk_forward_oos_score_introduced": False,
                "multi_model_score_introduced": False,
                "same_frozen_fresh_qlib_artifact": True,
            }
        )
    return rows


def pit_audit(df: pd.DataFrame) -> list[dict[str, Any]]:
    rows = []
    for family, prefix in [("institutional_flow", "institutional_flow"), ("margin_short", "margin_short")]:
        for split, sub in df.groupby("c1_sample_split"):
            avail_col = f"{prefix}_available_at"
            trade_col = f"{prefix}_trade_date"
            available_at = pd.to_datetime(sub[avail_col], errors="coerce") if avail_col in sub else pd.Series(dtype="datetime64[ns]")
            trade_date = pd.to_datetime(sub[trade_col], errors="coerce") if trade_col in sub else pd.Series(dtype="datetime64[ns]")
            signal_date = pd.to_datetime(sub["date"], errors="coerce")
            missing = int(available_at.isna().sum())
            rows.append(
                {
                    "split": split,
                    "feature_family": family,
                    "rows_checked": int(sub.shape[0]),
                    "missing_rows": missing,
                    "missing_ratio": round(missing / len(sub), 8) if len(sub) else 0.0,
                    "used_available_at_gt_signal_asof_rows": int((available_at > signal_date).sum()),
                    "used_trade_date_gt_signal_asof_rows": int((trade_date > signal_date).sum()),
                    "source_flag_available_at_violation_rows": int(pd.to_numeric(sub.get(f"{prefix}_used_available_at_gt_sample_date", 0), errors="coerce").fillna(0).sum()),
                    "source_flag_trade_date_violation_rows": int(pd.to_numeric(sub.get(f"{prefix}_used_trade_date_gt_sample_date", 0), errors="coerce").fillna(0).sum()),
                }
            )
    return rows


def missing_report(df: pd.DataFrame, feature_schema: pd.DataFrame) -> list[dict[str, Any]]:
    rows = []
    for feature_row in feature_schema.to_dict("records"):
        feature = str(feature_row["feature"])
        family = str(feature_row["family"])
        for split, sub in df.groupby("c1_sample_split"):
            missing = int(sub[feature].isna().sum()) if feature in sub else int(sub.shape[0])
            rows.append(
                {
                    "split": split,
                    "feature": feature,
                    "family": family,
                    "rows": int(sub.shape[0]),
                    "missing_rows": missing,
                    "missing_ratio": round(missing / len(sub), 8) if len(sub) else 0.0,
                }
            )
    return rows


def label_audit(df: pd.DataFrame) -> list[dict[str, Any]]:
    rows = []
    for split, sub in df.groupby("c1_sample_split"):
        rows.append(
            {
                "split": split,
                "row_count": int(sub.shape[0]),
                "label_col": "relevance_10d_top_heavy",
                "label_non_null_rows": int(sub["relevance_10d_top_heavy"].notna().sum()),
                "label_complete_10d_rows": int(pd.Series(sub["label_complete_10d"]).fillna(False).astype(bool).sum()),
                "label_used_for_training": split == "ltr_train_2025",
                "label_used_for_tuning_or_selection": False,
                "test_label_audit_only": split == "ltr_test_2026",
                "label_min": int(sub["relevance_10d_top_heavy"].min()),
                "label_max": int(sub["relevance_10d_top_heavy"].max()),
                "label_distribution": json.dumps({str(k): int(v) for k, v in sub["relevance_10d_top_heavy"].value_counts(dropna=False).sort_index().items()}, sort_keys=True),
            }
        )
    return rows


def write_report(manifest: dict[str, Any], row_rows: list[dict[str, Any]], pit_rows: list[dict[str, Any]], label_rows: list[dict[str, Any]]) -> None:
    lines = [
        "# Phase C1 执行报告：Row-aligned LTR 样本构建",
        "",
        f"生成时间：`{manifest['created_at']}`",
        "",
        "## 1. 结论",
        "",
        f"- gate：`{manifest['gate']}`。",
        "- 已基于同一个 frozen fresh qlib S2B OOS score 构建 2025 train 与 2026 untouched test 的 top50 row-aligned 样本。",
        "- 未训练 qlib，未训练 LTR，未调参，未回放。",
        "- 未使用 qlib 2017..2024 in-sample score，未引入 walk-forward OOS 或多模型 score。",
        "",
        "## 2. 输入 Artifact",
        "",
        f"- C0 manifest：`{rel(C0_MANIFEST)}`",
        f"- frozen fresh qlib score：`{rel(S2B_SCORE)}`",
        f"- O3 row-aligned source：`{rel(O3_SAMPLE)}`",
        f"- O4 feature whitelist：`{rel(O4_FEATURES)}`",
        f"- O4 model config source：`{rel(O4_MANIFEST)}`",
        "",
        "## 3. Train / Test Row Alignment",
        "",
        "| split | start | end | rows | dates | daily rows min/median/max | duplicate keys | top50 rows | after qlib train end |",
        "| --- | --- | --- | ---: | ---: | --- | ---: | ---: | --- |",
    ]
    for row in row_rows:
        lines.append(
            f"| {row['split']} | {row['start_date']} | {row['end_date']} | {row['row_count']} | {row['date_count']} | {row['daily_rows_min']}/{row['daily_rows_median']}/{row['daily_rows_max']} | {row['duplicate_key_count']} | {row['top50_scope_rows']} | {row['all_rows_after_qlib_train_end']} |"
        )
    lines.extend(
        [
            "",
            "## 4. Feature Schema",
            "",
            f"- feature count：`{manifest['feature_schema']['feature_count']}`。",
            f"- control original features：`{manifest['feature_schema']['control_original_feature_count']}`。",
            f"- orthogonal features：`{manifest['feature_schema']['orthogonal_feature_count']}`。",
            "- feature schema 完全来自 O4 whitelist，未新增 O4/O2 之外特征族。",
            "",
            "## 5. Label Audit",
            "",
            "| split | rows | label non-null | label complete 10d | label used for training | test audit only | distribution |",
            "| --- | ---: | ---: | ---: | --- | --- | --- |",
        ]
    )
    for row in label_rows:
        lines.append(
            f"| {row['split']} | {row['row_count']} | {row['label_non_null_rows']} | {row['label_complete_10d_rows']} | {row['label_used_for_training']} | {row['test_label_audit_only']} | `{row['label_distribution']}` |"
        )
    lines.extend(
        [
            "",
            "## 6. PIT Leakage Audit",
            "",
            "| split | family | rows | missing_ratio | available_at violation | trade_date violation |",
            "| --- | --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in pit_rows:
        lines.append(
            f"| {row['split']} | {row['feature_family']} | {row['rows_checked']} | {row['missing_ratio']} | {row['used_available_at_gt_signal_asof_rows']} | {row['used_trade_date_gt_signal_asof_rows']} |"
        )
    lines.extend(
        [
            "",
            "## 7. Score Provenance",
            "",
            "- train/test score 均来自同一个 frozen fresh qlib S2B post-filter score artifact。",
            "- train rows only from 2025。",
            "- test rows only from 2026。",
            "- 2026 label 仅用于 audit / rank metric，不用于训练、调参或选择。",
            "- qlib in-sample rows used for LTR train：`0`。",
            "- walk-forward / multi-model score：`False`。",
            "",
            "## 8. Missing Report",
            "",
            f"- 详见 `{rel(MISSING_CSV)}`。",
            "- 正交特征缺失通过 O2 missing/asof flag 暴露；未新增补数规则。",
            "",
            "## 9. 禁止事项审计",
            "",
            "- 未训练 qlib / LTR。",
            "- 未调参、未回放。",
            "- 未改 split / label。",
            "- 未新增 O4/O2 之外特征或数据源。",
            "- 未触发 frontend/API/provider/accepted latest/monitor/交易链路。",
            "",
            "## 10. 输出 Artifact",
            "",
            f"- `{rel(MANIFEST_JSON)}`",
            f"- `{rel(TRAIN_CSV)}`",
            f"- `{rel(TEST_CSV)}`",
            f"- `{rel(FEATURE_SCHEMA_CSV)}`",
            f"- `{rel(ROW_ALIGNMENT_CSV)}`",
            f"- `{rel(SCORE_PROVENANCE_CSV)}`",
            f"- `{rel(PIT_AUDIT_CSV)}`",
            f"- `{rel(MISSING_CSV)}`",
            f"- `{rel(LABEL_AUDIT_CSV)}`",
            f"- `{rel(FORBIDDEN_JSON)}`",
            "",
            "## 11. 是否建议进入 C2",
            "",
            f"- 建议：允许进入 C2，gate 为 `{manifest['gate']}`。",
        ]
    )
    DOC.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    created_at = now()
    c0, o4 = require_inputs()
    schema = load_feature_schema()
    feature_cols = schema["feature"].astype(str).tolist()
    sample = build_samples(feature_cols)
    train = sample[sample["c1_sample_split"] == "ltr_train_2025"].copy()
    test = sample[sample["c1_sample_split"] == "ltr_test_2026"].copy()

    stop_reasons = []
    if train.empty or not train["date_str"].between(TRAIN_START, TRAIN_END).all():
        stop_reasons.append("train_rows_not_only_2025")
    if test.empty or not test["date_str"].between(TEST_START, TEST_END).all():
        stop_reasons.append("test_rows_not_only_2026")
    if not train["after_fresh_qlib_train_end"].all() or not test["after_fresh_qlib_train_end"].all():
        stop_reasons.append("qlib_in_sample_score_used")
    row_rows = row_alignment_audit(sample)
    if any(row["daily_rows_min"] < 50 for row in row_rows):
        stop_reasons.append("daily_top50_coverage_incomplete")
    pit_rows = pit_audit(sample)
    if any(row["used_available_at_gt_signal_asof_rows"] or row["used_trade_date_gt_signal_asof_rows"] for row in pit_rows):
        stop_reasons.append("pit_leakage_detected")
    label_rows = label_audit(sample)
    if next(row for row in label_rows if row["split"] == "ltr_train_2025")["label_complete_10d_rows"] != len(train):
        stop_reasons.append("2025_label_incomplete")

    score_rows = score_provenance_audit(sample)
    missing_rows = missing_report(sample, schema)
    schema.to_csv(FEATURE_SCHEMA_CSV, index=False)
    train.to_csv(TRAIN_CSV, index=False)
    test.to_csv(TEST_CSV, index=False)
    wcsv(ROW_ALIGNMENT_CSV, row_rows)
    wcsv(SCORE_PROVENANCE_CSV, score_rows)
    wcsv(PIT_AUDIT_CSV, pit_rows)
    wcsv(MISSING_CSV, missing_rows)
    wcsv(LABEL_AUDIT_CSV, label_rows)
    forbidden = {
        "created_at": created_at,
        "phase": "phase_c1_row_aligned_sample",
        "no_qlib_training": True,
        "no_ltr_training": True,
        "no_replay": True,
        "no_parameter_search": True,
        "no_split_label_change": True,
        "no_qlib_in_sample_score_for_ltr_train": True,
        "no_walk_forward_oos_or_multi_model_score": True,
        "no_new_feature_family_or_data_source": True,
        "no_frontend_api_provider_accepted_latest_monitor_trading": True,
        "no_broker_quick_trade_orders": True,
    }
    manifest = {
        "created_at": created_at,
        "phase": "phase_c1_row_aligned_sample",
        "gate": GATE if not stop_reasons else "clean_stacking_blocked_by_sample_or_contract",
        "stop_reasons": stop_reasons,
        "upstream_gate": c0.get("gate"),
        "frozen_contract": {
            "fresh_qlib_score_source": rel(S2B_SCORE),
            "fresh_qlib_train_end": QLIB_TRAIN_END,
            "ltr_train": [TRAIN_START, TRAIN_END],
            "ltr_test": [TEST_START, TEST_END],
            "preserve_scope": "top50_only",
            "label_col": "relevance_10d_top_heavy",
            "model_family_params_for_c2": o4.get("model_config", {}),
        },
        "row_alignment": row_rows,
        "score_provenance": score_rows,
        "pit_leakage_audit": pit_rows,
        "label_audit": label_rows,
        "feature_schema": {
            "source": rel(O4_FEATURES),
            "feature_count": int(schema.shape[0]),
            "control_original_feature_count": int((schema["family"] == "control_original").sum()),
            "orthogonal_feature_count": int((schema["family"] != "control_original").sum()),
            "feature_hash": df_hash(schema, ["order", "feature", "family", "status"]),
        },
        "sample_hashes": {
            "train_identity_hash": df_hash(train, ["date_str", "instrument", "qlib_rank"]),
            "test_identity_hash": df_hash(test, ["date_str", "instrument", "qlib_rank"]),
            "train_label_hash": df_hash(train, ["date_str", "instrument", "relevance_10d_top_heavy"]),
            "test_label_hash_audit_only": df_hash(test, ["date_str", "instrument", "relevance_10d_top_heavy"]),
        },
        "artifacts": {
            "train_sample_2025": rel(TRAIN_CSV),
            "test_sample_2026": rel(TEST_CSV),
            "feature_schema": rel(FEATURE_SCHEMA_CSV),
            "row_alignment_audit": rel(ROW_ALIGNMENT_CSV),
            "score_provenance_audit": rel(SCORE_PROVENANCE_CSV),
            "pit_leakage_audit": rel(PIT_AUDIT_CSV),
            "missing_report": rel(MISSING_CSV),
            "label_audit": rel(LABEL_AUDIT_CSV),
            "forbidden_action_audit": rel(FORBIDDEN_JSON),
            "report": rel(DOC),
        },
    }
    wjson(FORBIDDEN_JSON, forbidden)
    wjson(MANIFEST_JSON, manifest)
    write_report(manifest, row_rows, pit_rows, label_rows)
    print(json.dumps({"ok": not stop_reasons, "gate": manifest["gate"], "report": rel(DOC), "out_dir": rel(OUT_DIR), "stop_reasons": stop_reasons}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
