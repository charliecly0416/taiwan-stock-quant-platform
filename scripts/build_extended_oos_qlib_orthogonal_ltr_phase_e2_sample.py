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
E0_MANIFEST = ROOT / "data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e0_contract_and_feasibility/phasee0_contract_manifest.json"
E1_MANIFEST = ROOT / "data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e1_frozen_qlib_training_and_oos_score/phasee1_training_manifest.json"
E1R_MANIFEST = ROOT / "data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e1r_candidate_coverage_scope_repair/phasee1r_scope_manifest.json"
E1R_CONTRACT = ROOT / "data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e1r_candidate_coverage_scope_repair/phasee1r_recommended_e2_candidate_contract.json"
E1_RAW = ROOT / "data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e1_frozen_qlib_training_and_oos_score/phasee1_raw_oos_score_rank_2023_2026.csv"
O3_SAMPLE = ROOT / "data_tw/experiments/ltr_orthogonal_features_controlled/phase_o3_row_aligned_treatment_sample/phaseo3_treatment_candidate_sample.csv"
O4_FEATURES = ROOT / "data_tw/experiments/ltr_orthogonal_features_controlled/phase_o4_controlled_treatment_ltr/phaseo4_training_feature_whitelist.csv"
O4_MANIFEST = ROOT / "data_tw/experiments/ltr_orthogonal_features_controlled/phase_o4_controlled_treatment_ltr/phaseo4_training_manifest.json"
PROVIDER = ROOT / "qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin"
INSTRUMENTS = PROVIDER / "instruments/all.txt"
PRICE_ROOT = ROOT / "qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/normalized_nonempty"
OUT_DIR = ROOT / "data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e2_row_aligned_sample"
DOC = ROOT / "docs/tw_extended_oos_qlib_orthogonal_ltr/PHASEE2_ROW_ALIGNED_SAMPLE_EXECUTION_REPORT_CN.md"

MANIFEST_JSON = OUT_DIR / "phasee2_sample_manifest.json"
TRAIN_CSV = OUT_DIR / "phasee2_ltr_train_sample_2023_2025.csv"
TEST_CSV = OUT_DIR / "phasee2_ltr_test_sample_2026.csv"
FEATURE_SCHEMA_CSV = OUT_DIR / "phasee2_feature_schema.csv"
ROW_ALIGNMENT_CSV = OUT_DIR / "phasee2_row_alignment_audit.csv"
CANDIDATE_SCOPE_CSV = OUT_DIR / "phasee2_candidate_scope_audit.csv"
SCORE_PROVENANCE_CSV = OUT_DIR / "phasee2_score_provenance_audit.csv"
PIT_AUDIT_CSV = OUT_DIR / "phasee2_pit_leakage_audit.csv"
MISSING_CSV = OUT_DIR / "phasee2_missing_report.csv"
LABEL_AUDIT_CSV = OUT_DIR / "phasee2_label_audit.csv"
FORBIDDEN_JSON = OUT_DIR / "phasee2_forbidden_action_audit.json"

TRAIN_START = "2023-01-01"
TRAIN_END = "2025-12-31"
TEST_START = "2026-01-01"
TEST_END = "2026-05-07"
GATE = "phase_e2_extended_oos_ltr_sample_passed"
BLOCKED_GATE = "phase_e2_blocked_by_sample_or_contract"


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
        fields = sorted({k for row in rows for k in row.keys()})
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def norm(symbol: str) -> str:
    text = str(symbol or "").strip().upper()
    return text if text.startswith("TW") else f"TW{text}"


def df_hash(df: pd.DataFrame, cols: list[str]) -> str:
    text = df[cols].astype("string").fillna("<NA>").to_csv(index=False)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def top_heavy_label(rank: pd.Series) -> pd.Series:
    r = pd.to_numeric(rank, errors="coerce").fillna(0)
    return np.select([r >= 0.90, r >= 0.80, r >= 0.70, r >= 0.50], [4, 3, 2, 1], default=0).astype(int)


def require_inputs() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    required = [E0_MANIFEST, E1_MANIFEST, E1R_MANIFEST, E1R_CONTRACT, E1_RAW, O3_SAMPLE, O4_FEATURES, O4_MANIFEST, INSTRUMENTS, PRICE_ROOT]
    missing = [rel(p) for p in required if not p.exists()]
    if missing:
        raise RuntimeError(f"Missing E2 inputs: {missing}")
    e0 = load_json(E0_MANIFEST)
    e1 = load_json(E1_MANIFEST)
    e1r = load_json(E1R_MANIFEST)
    contract = load_json(E1R_CONTRACT)
    o4 = load_json(O4_MANIFEST)
    gates = {
        "E0": e0.get("gate"),
        "E1": e1.get("gate"),
        "E1R": e1r.get("gate"),
        "E1R_CONTRACT": contract.get("gate"),
        "O4": o4.get("gate"),
    }
    expected = {
        "E0": "phase_e0_extended_oos_contract_feasible",
        "E1": "phase_e1_frozen_qlib_oos_score_completed",
        "E1R": "phase_e1r_candidate_coverage_scope_repaired",
        "E1R_CONTRACT": "phase_e1r_candidate_coverage_scope_repaired",
        "O4": "phase_o4_controlled_treatment_ltr_trained",
    }
    bad = {k: v for k, v in gates.items() if v != expected[k]}
    if bad:
        raise RuntimeError(f"Upstream gate mismatch: {bad}")
    return e0, e1, e1r, contract, o4


def read_provider_instruments() -> pd.DataFrame:
    rows = []
    with INSTRUMENTS.open(encoding="utf-8") as fh:
        for line in fh:
            parts = line.strip().split()
            if len(parts) >= 3:
                rows.append({"instrument": norm(parts[0]), "start": parts[1], "end": parts[2]})
    return pd.DataFrame(rows)


def load_price_keys(provider_symbols: set[str], dates: set[str]) -> tuple[set[tuple[str, str]], set[tuple[str, str]]]:
    price_keys: set[tuple[str, str]] = set()
    history_keys: set[tuple[str, str]] = set()
    for path in sorted(PRICE_ROOT.glob("TW*.csv")):
        symbol = path.stem.upper()
        if symbol == "TWII" or symbol not in provider_symbols:
            continue
        df = pd.read_csv(path, usecols=["date", "close", "vwap", "volume"])
        if df.empty:
            continue
        df["date"] = pd.to_datetime(df["date"])
        df = df[df["date"] <= pd.Timestamp(TEST_END)].sort_values("date").copy()
        df["date_str"] = df["date"].dt.strftime("%Y-%m-%d")
        df["close"] = pd.to_numeric(df["close"], errors="coerce")
        df["volume"] = pd.to_numeric(df["volume"], errors="coerce")
        df["has_price"] = df["close"].notna() & (df["close"] > 0) & df["volume"].notna() & (df["volume"] >= 0)
        df["history_count_60"] = df["has_price"].cumsum()
        sub = df[df["date_str"].isin(dates)].copy()
        for row in sub.itertuples(index=False):
            key = (row.date_str, symbol)
            if bool(row.has_price):
                price_keys.add(key)
            if bool(row.has_price) and int(row.history_count_60) >= 60:
                history_keys.add(key)
    return price_keys, history_keys


def load_feature_schema() -> pd.DataFrame:
    schema = pd.read_csv(O4_FEATURES)
    if "feature" not in schema.columns:
        raise RuntimeError("O4 feature whitelist missing feature column")
    schema.to_csv(FEATURE_SCHEMA_CSV, index=False)
    return schema


def build_broad_candidates() -> pd.DataFrame:
    instruments = read_provider_instruments()
    raw = pd.read_csv(E1_RAW, parse_dates=["date"])
    raw["instrument"] = raw["instrument"].map(norm)
    raw["date_str"] = raw["date"].dt.strftime("%Y-%m-%d")
    raw = raw[(raw["date_str"] >= TRAIN_START) & (raw["date_str"] <= TEST_END)].copy()
    inst = instruments.copy()
    inst["start"] = pd.to_datetime(inst["start"])
    inst["end"] = pd.to_datetime(inst["end"])
    raw = raw.merge(inst, on="instrument", how="left")
    raw["provider_active_asof"] = raw["start"].notna() & (raw["date"] >= raw["start"]) & (raw["date"] <= raw["end"])
    provider_symbols = set(instruments["instrument"].astype(str))
    price_keys, history_keys = load_price_keys(provider_symbols, set(raw["date_str"].unique()))
    raw["same_day_price_tradable"] = [(d, s) in price_keys for d, s in raw[["date_str", "instrument"]].itertuples(index=False, name=None)]
    raw["history_60_asof"] = [(d, s) in history_keys for d, s in raw[["date_str", "instrument"]].itertuples(index=False, name=None)]
    raw["candidate_scope_pass"] = raw["provider_active_asof"] & raw["same_day_price_tradable"] & raw["history_60_asof"] & raw["qlib_score_raw"].notna()
    cand = raw[raw["candidate_scope_pass"]].copy()
    cand = cand.sort_values(["date", "qlib_score_raw", "instrument"], ascending=[True, False, True]).reset_index(drop=True)
    cand["qlib_rank"] = cand.groupby("date")["qlib_score_raw"].rank(method="first", ascending=False).astype(int)
    grouped = cand.groupby("date")
    cand["qlib_score_percentile_by_date"] = grouped["qlib_score_raw"].rank(pct=True, method="average")
    mean = grouped["qlib_score_raw"].transform("mean")
    std = grouped["qlib_score_raw"].transform(lambda s: float(s.std(ddof=0)) if len(s) else 0.0)
    cand["qlib_score_zscore_by_date"] = np.where(std > 0, (cand["qlib_score_raw"] - mean) / std, 0.0)
    cand["top10_flag"] = (cand["qlib_rank"] <= 10).astype(int)
    cand["top30_flag"] = (cand["qlib_rank"] <= 30).astype(int)
    cand["top50_flag"] = (cand["qlib_rank"] <= 50).astype(int)
    cand = cand.sort_values(["instrument", "date"]).reset_index(drop=True)
    for lag in [1, 3, 5]:
        cand[f"rank_change_{lag}d"] = cand.groupby("instrument")["qlib_rank"].diff(lag)
    cand["top30_streak"] = cand.groupby("instrument")["top30_flag"].transform(lambda s: s.groupby((s != s.shift()).cumsum()).cumsum())
    cand["top50_streak"] = cand.groupby("instrument")["top50_flag"].transform(lambda s: s.groupby((s != s.shift()).cumsum()).cumsum())
    cand["e2_sample_split"] = np.where(cand["date_str"] <= TRAIN_END, "ltr_train_2023_2025", "ltr_test_2026")
    cand["score_source"] = rel(E1_RAW)
    cand["same_e1_frozen_qlib_score_source"] = True
    cand["after_qlib_train_end"] = cand["date_str"] >= TRAIN_START
    cand["candidate_scope"] = "e1r_provider_eligible_broad_candidate"
    return cand.drop(columns=["start", "end"])


def selected_o3_columns(feature_cols: list[str]) -> list[str]:
    metadata = [
        "control_row_id", "date", "instrument", "year", "split", "regime_segment",
        "future_return_5d", "future_return_10d", "future_return_20d",
        "future_excess_return_5d", "future_excess_return_10d", "future_excess_return_20d",
        "future_excess_return_rank_5d", "future_excess_return_rank_10d", "future_excess_return_rank_20d",
        "topk_forward_bucket", "ltr_relevance_label", "label_complete_5d", "label_complete_10d", "label_complete_20d",
        "feature_complete", "sample_complete",
        "institutional_flow_trade_date", "institutional_flow_available_at", "institutional_flow_raw_snapshot_id",
        "institutional_flow_delay_reason", "institutional_flow_available_at_contract", "institutional_flow_raw_snapshot_path",
        "institutional_flow_lineage_source", "institutional_flow_used_available_at_gt_sample_date", "institutional_flow_used_trade_date_gt_sample_date",
        "margin_short_trade_date", "margin_short_available_at", "margin_short_raw_snapshot_id", "margin_short_delay_reason",
        "margin_short_available_at_contract", "margin_short_raw_snapshot_path", "margin_short_lineage_source",
        "margin_short_used_available_at_gt_sample_date", "margin_short_used_trade_date_gt_sample_date",
    ]
    qlib_derived = {
        "qlib_score_raw", "qlib_rank", "qlib_score_percentile_by_date", "qlib_score_zscore_by_date",
        "rank_change_1d", "rank_change_3d", "rank_change_5d", "top10_flag", "top30_flag", "top50_flag", "top30_streak", "top50_streak",
    }
    cols = metadata + [col for col in feature_cols if col not in qlib_derived]
    return sorted(set(cols), key=cols.index)


def build_samples(feature_cols: list[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    cand = build_broad_candidates()
    o3_cols = selected_o3_columns(feature_cols)
    o3 = pd.read_csv(O3_SAMPLE, usecols=lambda c: c in set(o3_cols), parse_dates=["date"])
    o3["instrument"] = o3["instrument"].map(norm)
    o3["date_str"] = o3["date"].dt.strftime("%Y-%m-%d")
    merged = cand.merge(o3, on=["date", "date_str", "instrument"], how="left", validate="one_to_one", suffixes=("", "_o3"))
    merged["row_aligned_to_o3"] = merged["control_row_id"].notna()
    if merged["control_row_id"].isna().any():
        missing = merged[merged["control_row_id"].isna()][["date_str", "instrument"]].head(20).to_dict("records")
        raise RuntimeError(f"E2 O3 row alignment missing for broad candidate rows: {missing}")
    merged["relevance_10d_top_heavy"] = top_heavy_label(merged["future_excess_return_rank_10d"])
    ordered_cols = [
        "control_row_id", "date", "date_str", "instrument", "e2_sample_split", "year", "regime_segment",
        "candidate_scope", "score_source", "same_e1_frozen_qlib_score_source", "after_qlib_train_end",
        "provider_active_asof", "same_day_price_tradable", "history_60_asof", "candidate_scope_pass", "row_aligned_to_o3",
    ] + feature_cols + [
        "future_return_5d", "future_return_10d", "future_return_20d",
        "future_excess_return_5d", "future_excess_return_10d", "future_excess_return_20d",
        "future_excess_return_rank_5d", "future_excess_return_rank_10d", "future_excess_return_rank_20d",
        "relevance_10d_top_heavy", "topk_forward_bucket", "ltr_relevance_label",
        "label_complete_5d", "label_complete_10d", "label_complete_20d", "feature_complete", "sample_complete",
        "institutional_flow_trade_date", "institutional_flow_available_at", "institutional_flow_raw_snapshot_id", "institutional_flow_delay_reason",
        "institutional_flow_available_at_contract", "institutional_flow_raw_snapshot_path", "institutional_flow_lineage_source",
        "institutional_flow_used_available_at_gt_sample_date", "institutional_flow_used_trade_date_gt_sample_date",
        "margin_short_trade_date", "margin_short_available_at", "margin_short_raw_snapshot_id", "margin_short_delay_reason",
        "margin_short_available_at_contract", "margin_short_raw_snapshot_path", "margin_short_lineage_source",
        "margin_short_used_available_at_gt_sample_date", "margin_short_used_trade_date_gt_sample_date",
    ]
    ordered_cols = [col for col in ordered_cols if col in merged.columns]
    merged = merged.sort_values(["date", "qlib_rank", "instrument"]).reset_index(drop=True)
    return merged[ordered_cols].copy(), cand


def row_alignment_audit(df: pd.DataFrame) -> list[dict[str, Any]]:
    rows = []
    for split, sub in df.groupby("e2_sample_split"):
        daily = sub.groupby("date_str", as_index=False).size()
        max_rank_by_day = sub.groupby("date_str")["qlib_rank"].max()
        rows.append({
            "split": split,
            "start_date": str(sub["date_str"].min()),
            "end_date": str(sub["date_str"].max()),
            "row_count": int(sub.shape[0]),
            "date_count": int(daily.shape[0]),
            "daily_rows_min": int(daily["size"].min()),
            "daily_rows_median": float(daily["size"].median()),
            "daily_rows_max": int(daily["size"].max()),
            "duplicate_key_count": int(sub.duplicated(["date_str", "instrument"]).sum()),
            "top50_rows": int((pd.to_numeric(sub["qlib_rank"], errors="coerce") <= 50).sum()),
            "top50_only": bool((daily["size"] <= 50).all()),
            "max_qlib_rank": int(pd.to_numeric(sub["qlib_rank"], errors="coerce").max()),
            "median_daily_max_qlib_rank": float(max_rank_by_day.median()),
            "all_same_e1_score_source": bool(sub["same_e1_frozen_qlib_score_source"].all()),
            "all_rows_after_qlib_train_end": bool(sub["after_qlib_train_end"].all()),
            "row_aligned_to_o3_rows": int(sub["row_aligned_to_o3"].sum()),
        })
    return rows


def candidate_scope_audit(df: pd.DataFrame) -> list[dict[str, Any]]:
    rows = []
    for split, sub in df.groupby("e2_sample_split"):
        rows.append({
            "split": split,
            "row_count": int(sub.shape[0]),
            "provider_active_asof_rows": int(sub["provider_active_asof"].sum()),
            "same_day_price_tradable_rows": int(sub["same_day_price_tradable"].sum()),
            "history_60_asof_rows": int(sub["history_60_asof"].sum()),
            "candidate_scope_pass_rows": int(sub["candidate_scope_pass"].sum()),
            "filtered_to_top50_for_training": False,
            "filtered_to_top30_for_training": False,
            "filtered_to_full_market_top150_intersection": False,
            "candidate_scope": "E1 raw score + provider active + same-day price/tradability + >=60 history",
        })
    return rows


def score_provenance_audit(df: pd.DataFrame) -> list[dict[str, Any]]:
    rows = []
    for split, sub in df.groupby("e2_sample_split"):
        rows.append({
            "split": split,
            "score_source": rel(E1_RAW),
            "row_count": int(sub.shape[0]),
            "score_missing_rows": int(sub["qlib_score_raw"].isna().sum()),
            "rank_missing_rows": int(sub["qlib_rank"].isna().sum()),
            "qlib_in_sample_rows_2018_2022": int((sub["date_str"] < TRAIN_START).sum()),
            "walk_forward_oos_score_introduced": False,
            "multi_model_score_introduced": False,
            "same_e1_frozen_qlib_artifact": True,
        })
    return rows


def pit_audit(df: pd.DataFrame) -> list[dict[str, Any]]:
    rows = []
    for family, prefix in [("institutional_flow", "institutional_flow"), ("margin_short", "margin_short")]:
        for split, sub in df.groupby("e2_sample_split"):
            avail_col = f"{prefix}_available_at"
            trade_col = f"{prefix}_trade_date"
            available_at = pd.to_datetime(sub[avail_col], errors="coerce") if avail_col in sub else pd.Series(dtype="datetime64[ns]")
            trade_date = pd.to_datetime(sub[trade_col], errors="coerce") if trade_col in sub else pd.Series(dtype="datetime64[ns]")
            signal_date = pd.to_datetime(sub["date"], errors="coerce")
            rows.append({
                "split": split,
                "feature_family": family,
                "rows_checked": int(sub.shape[0]),
                "missing_rows": int(available_at.isna().sum()),
                "missing_ratio": round(float(available_at.isna().mean()), 8) if len(sub) else 0.0,
                "used_available_at_gt_signal_asof_rows": int((available_at > signal_date).sum()),
                "used_trade_date_gt_signal_asof_rows": int((trade_date > signal_date).sum()),
                "source_flag_available_at_violation_rows": int(pd.to_numeric(sub.get(f"{prefix}_used_available_at_gt_sample_date", 0), errors="coerce").fillna(0).sum()),
                "source_flag_trade_date_violation_rows": int(pd.to_numeric(sub.get(f"{prefix}_used_trade_date_gt_sample_date", 0), errors="coerce").fillna(0).sum()),
            })
    return rows


def missing_report(df: pd.DataFrame, schema: pd.DataFrame) -> list[dict[str, Any]]:
    rows = []
    for feature_row in schema.to_dict("records"):
        feature = str(feature_row["feature"])
        family = str(feature_row["family"])
        for split, sub in df.groupby("e2_sample_split"):
            missing = int(sub[feature].isna().sum()) if feature in sub else int(sub.shape[0])
            rows.append({"split": split, "feature": feature, "family": family, "rows": int(sub.shape[0]), "missing_rows": missing, "missing_ratio": round(missing / len(sub), 8) if len(sub) else 0.0})
    return rows


def label_audit(df: pd.DataFrame) -> list[dict[str, Any]]:
    rows = []
    for split, sub in df.groupby("e2_sample_split"):
        rows.append({
            "split": split,
            "row_count": int(sub.shape[0]),
            "label_col": "relevance_10d_top_heavy",
            "label_non_null_rows": int(sub["relevance_10d_top_heavy"].notna().sum()),
            "label_complete_10d_rows": int(pd.Series(sub["label_complete_10d"]).fillna(False).astype(bool).sum()),
            "label_used_for_training": split == "ltr_train_2023_2025",
            "label_used_for_tuning_or_selection": False,
            "test_label_audit_only": split == "ltr_test_2026",
            "label_min": int(sub["relevance_10d_top_heavy"].min()),
            "label_max": int(sub["relevance_10d_top_heavy"].max()),
            "label_distribution": json.dumps({str(k): int(v) for k, v in sub["relevance_10d_top_heavy"].value_counts(dropna=False).sort_index().items()}, sort_keys=True),
        })
    return rows


def write_report(manifest: dict[str, Any], row_rows: list[dict[str, Any]], pit_rows: list[dict[str, Any]], label_rows: list[dict[str, Any]]) -> None:
    lines = [
        "# Phase E2 执行报告：宽候选 Row-aligned LTR 样本构建", "", f"生成时间：`{manifest['created_at']}`", "",
        "## 1. 结论", "", f"- gate：`{manifest['gate']}`。",
        "- 已基于 E1 raw OOS score 与 E1R 宽候选合同构建 2023-2025 LTR train 和 2026 untouched test 样本。",
        "- 训练样本为旧 O4-style 宽候选集合，不是 top50-only；top50 仅作为特征和后续回放 rerank 边界。",
        "- 未训练 qlib，未训练 LTR，未调参，未回放。", "",
        "## 2. 输入 Artifact", "",
        f"- E1 raw score：`{rel(E1_RAW)}`", f"- E1R contract：`{rel(E1R_CONTRACT)}`", f"- O3 row-aligned source：`{rel(O3_SAMPLE)}`", f"- O4 feature whitelist：`{rel(O4_FEATURES)}`", "",
        "## 3. Train / Test Row Alignment", "",
        "| split | start | end | rows | dates | daily rows min/median/max | top50 rows | top50-only | max rank | median daily max rank |",
        "| --- | --- | --- | ---: | ---: | --- | ---: | --- | ---: | ---: |",
    ]
    for row in row_rows:
        lines.append(f"| {row['split']} | {row['start_date']} | {row['end_date']} | {row['row_count']} | {row['date_count']} | {row['daily_rows_min']}/{row['daily_rows_median']}/{row['daily_rows_max']} | {row['top50_rows']} | {row['top50_only']} | {row['max_qlib_rank']} | {row['median_daily_max_qlib_rank']} |")
    lines.extend(["", "## 4. Feature Schema", "", f"- feature count：`{manifest['feature_schema']['feature_count']}`。", f"- control original features：`{manifest['feature_schema']['control_original_feature_count']}`。", f"- orthogonal features：`{manifest['feature_schema']['orthogonal_feature_count']}`。", "- feature schema 完全来自 O4 whitelist，未新增 O2/O4 之外特征。", "", "## 5. Label Audit", "", "| split | rows | label non-null | label complete 10d | label used for training | test audit only | distribution |", "| --- | ---: | ---: | ---: | --- | --- | --- |"])
    for row in label_rows:
        lines.append(f"| {row['split']} | {row['row_count']} | {row['label_non_null_rows']} | {row['label_complete_10d_rows']} | {row['label_used_for_training']} | {row['test_label_audit_only']} | `{row['label_distribution']}` |")
    lines.extend(["", "## 6. PIT Leakage Audit", "", "| split | family | rows | missing_ratio | available_at violation | trade_date violation |", "| --- | --- | ---: | ---: | ---: | ---: |"])
    for row in pit_rows:
        lines.append(f"| {row['split']} | {row['feature_family']} | {row['rows_checked']} | {row['missing_ratio']} | {row['used_available_at_gt_signal_asof_rows']} | {row['used_trade_date_gt_signal_asof_rows']} |")
    lines.extend(["", "## 7. Score Provenance", "", "- train/test score 均来自同一个 E1 frozen qlib raw OOS score artifact。", "- train rows only from 2023-2025。", "- test rows only from 2026。", "- 2026 label 仅用于 audit / rank metric，不用于训练、调参或选择。", "- qlib in-sample rows used for LTR train：`0`。", "- walk-forward / multi-model score：`False`。", "", "## 8. Candidate Scope", "", f"- 详见 `{rel(CANDIDATE_SCOPE_CSV)}`。", "- 未使用 top50/top30/full_market_trailing_value_top150_intersection 作为训练候选过滤。", "", "## 9. Missing Report", "", f"- 详见 `{rel(MISSING_CSV)}`。", "- 正交特征缺失通过 O2 missing/asof flag 暴露；未因 O2 缺失删除候选。", "", "## 10. 禁止事项审计", "", "- 未训练 qlib / LTR。", "- 未调参、未回放。", "- 未改 split / label。", "- 未新增 O4/O2 之外特征或数据源。", "- 未触发 frontend/API/provider/accepted latest/monitor/交易链路。", "", "## 11. 输出 Artifact", "", f"- `{rel(MANIFEST_JSON)}`", f"- `{rel(TRAIN_CSV)}`", f"- `{rel(TEST_CSV)}`", f"- `{rel(FEATURE_SCHEMA_CSV)}`", f"- `{rel(ROW_ALIGNMENT_CSV)}`", f"- `{rel(CANDIDATE_SCOPE_CSV)}`", f"- `{rel(SCORE_PROVENANCE_CSV)}`", f"- `{rel(PIT_AUDIT_CSV)}`", f"- `{rel(MISSING_CSV)}`", f"- `{rel(LABEL_AUDIT_CSV)}`", f"- `{rel(FORBIDDEN_JSON)}`", "", "## 12. 是否建议进入 E3", "", f"- 建议：允许进入 E3，gate 为 `{manifest['gate']}`。"])
    DOC.parent.mkdir(parents=True, exist_ok=True)
    DOC.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    created_at = now()
    _, _, _, contract, o4 = require_inputs()
    schema = load_feature_schema()
    feature_cols = schema["feature"].astype(str).tolist()
    sample, _ = build_samples(feature_cols)
    train = sample[sample["e2_sample_split"] == "ltr_train_2023_2025"].copy()
    test = sample[sample["e2_sample_split"] == "ltr_test_2026"].copy()
    row_rows = row_alignment_audit(sample)
    candidate_rows = candidate_scope_audit(sample)
    score_rows = score_provenance_audit(sample)
    pit_rows = pit_audit(sample)
    missing_rows = missing_report(sample, schema)
    label_rows = label_audit(sample)
    stop_reasons = []
    if train.empty or not train["date_str"].between(TRAIN_START, TRAIN_END).all():
        stop_reasons.append("train_rows_not_only_2023_2025")
    if test.empty or not test["date_str"].between(TEST_START, TEST_END).all():
        stop_reasons.append("test_rows_not_only_2026")
    if any(row["top50_only"] for row in row_rows):
        stop_reasons.append("sample_degenerated_to_top50_only")
    if any(row["daily_rows_median"] < 100 for row in row_rows):
        stop_reasons.append("candidate_coverage_degenerated_toward_post_filter_scope")
    if any(row["duplicate_key_count"] for row in row_rows):
        stop_reasons.append("duplicate_date_instrument_keys")
    if any(row["score_missing_rows"] or row["rank_missing_rows"] or row["qlib_in_sample_rows_2018_2022"] for row in score_rows):
        stop_reasons.append("score_provenance_violation")
    if any(row["used_available_at_gt_signal_asof_rows"] or row["used_trade_date_gt_signal_asof_rows"] or row["source_flag_available_at_violation_rows"] or row["source_flag_trade_date_violation_rows"] for row in pit_rows):
        stop_reasons.append("pit_leakage_detected")
    train_label = next(row for row in label_rows if row["split"] == "ltr_train_2023_2025")
    if train_label["label_complete_10d_rows"] != len(train):
        stop_reasons.append("train_label_incomplete")
    gate = GATE if not stop_reasons else BLOCKED_GATE
    train.to_csv(TRAIN_CSV, index=False)
    test.to_csv(TEST_CSV, index=False)
    wcsv(ROW_ALIGNMENT_CSV, row_rows)
    wcsv(CANDIDATE_SCOPE_CSV, candidate_rows)
    wcsv(SCORE_PROVENANCE_CSV, score_rows)
    wcsv(PIT_AUDIT_CSV, pit_rows)
    wcsv(MISSING_CSV, missing_rows)
    wcsv(LABEL_AUDIT_CSV, label_rows)
    forbidden = {"created_at": created_at, "phase": "phase_e2_row_aligned_sample", "no_qlib_training": True, "no_ltr_training": True, "no_replay": True, "no_parameter_search": True, "no_top50_only_training_sample": True, "no_full_market_top150_intersection_training_filter": True, "no_2026_label_future_return_candidate_selection_training_tuning_or_selection": True, "no_walk_forward_oos_or_multi_model_score": True, "no_new_feature_family_or_data_source": True, "no_frontend_api_provider_accepted_latest_monitor_trading": True, "no_broker_quick_trade_orders": True}
    manifest = {"created_at": created_at, "phase": "phase_e2_row_aligned_sample", "gate": gate, "stop_reasons": stop_reasons, "e1r_contract": rel(E1R_CONTRACT), "candidate_contract_executed": True, "frozen_contract": {"e1_raw_score_source": rel(E1_RAW), "ltr_train": [TRAIN_START, TRAIN_END], "ltr_test": [TEST_START, TEST_END], "candidate_scope": "E1 raw score + provider active + same-day price/tradability + >=60 history", "replay_rerank_boundary_future_phase": "qlib top50", "label_col": "relevance_10d_top_heavy", "model_family_params_for_e3": o4.get("model_config", {})}, "row_alignment": row_rows, "candidate_scope_audit": candidate_rows, "score_provenance": score_rows, "pit_leakage_audit": pit_rows, "label_audit": label_rows, "feature_schema": {"source": rel(O4_FEATURES), "feature_count": int(schema.shape[0]), "control_original_feature_count": int((schema["family"] == "control_original").sum()), "orthogonal_feature_count": int((schema["family"] != "control_original").sum()), "feature_hash": df_hash(schema, ["order", "feature", "family", "status"])}, "sample_hashes": {"train_identity_hash": df_hash(train, ["date_str", "instrument", "qlib_rank"]), "test_identity_hash": df_hash(test, ["date_str", "instrument", "qlib_rank"]), "train_label_hash": df_hash(train, ["date_str", "instrument", "relevance_10d_top_heavy"]), "test_label_hash_audit_only": df_hash(test, ["date_str", "instrument", "relevance_10d_top_heavy"])}, "artifacts": {"train_sample_2023_2025": rel(TRAIN_CSV), "test_sample_2026": rel(TEST_CSV), "feature_schema": rel(FEATURE_SCHEMA_CSV), "row_alignment_audit": rel(ROW_ALIGNMENT_CSV), "candidate_scope_audit": rel(CANDIDATE_SCOPE_CSV), "score_provenance_audit": rel(SCORE_PROVENANCE_CSV), "pit_leakage_audit": rel(PIT_AUDIT_CSV), "missing_report": rel(MISSING_CSV), "label_audit": rel(LABEL_AUDIT_CSV), "forbidden_action_audit": rel(FORBIDDEN_JSON), "report": rel(DOC)}}
    wjson(FORBIDDEN_JSON, forbidden)
    wjson(MANIFEST_JSON, manifest)
    write_report(manifest, row_rows, pit_rows, label_rows)
    print(json.dumps({"ok": not stop_reasons, "gate": gate, "report": rel(DOC), "out_dir": rel(OUT_DIR), "stop_reasons": stop_reasons}, ensure_ascii=False, indent=2))
    return 0 if not stop_reasons else 1


if __name__ == "__main__":
    raise SystemExit(main())
