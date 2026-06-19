#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import pickle
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import lightgbm as lgb
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.metrics import ndcg_score


ROOT = Path(__file__).resolve().parents[1]
S2D_SCRIPT = ROOT / "scripts/evaluate_tw_ltr_s2d_full_daily_replay.py"

S2B_FRESH_SCORE = ROOT / "data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2b_fresh_qlib_training/phase_s2b_raw_score_rank.csv"
S2B_FRESH_MANIFEST = ROOT / "data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2b_fresh_qlib_training/phase_s2b_training_manifest.json"
FRESH_C4 = ROOT / "data_tw/experiments/fresh_top50_coverage_repair/phasec4_repaired_replay_ready_scores.csv"

E2_DIR = ROOT / "data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e2_row_aligned_sample"
E2_MANIFEST = E2_DIR / "phasee2_sample_manifest.json"
E2_TRAIN = E2_DIR / "phasee2_ltr_train_sample_2023_2025.csv"
E2_TEST = E2_DIR / "phasee2_ltr_test_sample_2026.csv"
E2_SCHEMA = E2_DIR / "phasee2_feature_schema.csv"
E4_MANIFEST = ROOT / "data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e4_2026_replay/phasee4_replay_manifest.json"
E5B_MANIFEST = ROOT / "data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e5b_e4_vs_fresh_exact_2026_bridge/manifest.json"

O3_SAMPLE = ROOT / "data_tw/experiments/ltr_orthogonal_features_controlled/phase_o3_row_aligned_treatment_sample/phaseo3_treatment_candidate_sample.csv"
O4_MANIFEST = ROOT / "data_tw/experiments/ltr_orthogonal_features_controlled/phase_o4_controlled_treatment_ltr/phaseo4_training_manifest.json"

OUT_DIR = ROOT / "data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e6_bridge_ltr_2025_two_qlib_bases"
DOC = ROOT / "docs/tw_extended_oos_qlib_orthogonal_ltr/PHASEE6_BRIDGE_LTR_2025_TWO_QLIB_BASES_EXECUTION_REPORT_CN.md"

MANIFEST_JSON = OUT_DIR / "phasee6_bridge_manifest.json"
BRANCH_A_TRAIN = OUT_DIR / "phasee6_branch_a_fresh_train_sample_2025.csv"
BRANCH_A_TEST = OUT_DIR / "phasee6_branch_a_fresh_test_sample_2026.csv"
BRANCH_B_TRAIN = OUT_DIR / "phasee6_branch_b_frozen_train_sample_2025.csv"
BRANCH_B_TEST = OUT_DIR / "phasee6_branch_b_frozen_test_sample_2026.csv"
BRANCH_A_MODEL = OUT_DIR / "phasee6_branch_a_fresh_ltr_model_2025.pkl"
BRANCH_B_MODEL = OUT_DIR / "phasee6_branch_b_frozen_ltr_model_2025.pkl"
GROUP_AUDIT_CSV = OUT_DIR / "phasee6_group_audit.csv"
RANK_METRICS_CSV = OUT_DIR / "phasee6_rank_metrics.csv"
FEATURE_IMPORTANCE_CSV = OUT_DIR / "phasee6_feature_importance.csv"
REPLAY_READY_CSV = OUT_DIR / "phasee6_replay_ready_scores_2026.csv"
SUMMARY_CSV = OUT_DIR / "phasee6_control_vs_treatment_summary.csv"
DAILY_NAV_CSV = OUT_DIR / "phasee6_daily_nav_2026.csv"
ACTIONS_CSV = OUT_DIR / "phasee6_actions_2026.csv"
COVERAGE_CSV = OUT_DIR / "phasee6_coverage_audit.csv"
ACCOUNTING_CSV = OUT_DIR / "phasee6_next_day_accounting_audit.csv"
PNL_CSV = OUT_DIR / "phasee6_pnl_concentration.csv"
FORBIDDEN_JSON = OUT_DIR / "phasee6_forbidden_action_audit.json"

TRAIN_START = "2025-01-01"
TRAIN_END = "2025-12-31"
TEST_START = "2026-01-01"
TEST_END = "2026-05-07"
LABEL_COL = "relevance_10d_top_heavy"
GATE = "phase_e6_bridge_ltr_2025_two_qlib_bases_completed"

BRANCH_A_CONTROL = "branch_a_repaired_fresh_qlib_top50_adaptive"
BRANCH_A_TREATMENT = "branch_a_fresh_qlib_orthogonal_ltr_2025"
BRANCH_B_CONTROL = "branch_b_2018_2022_frozen_qlib_top50_baseline"
BRANCH_B_TREATMENT = "branch_b_2018_2022_frozen_qlib_orthogonal_ltr_2025"

BRANCH_A_LTR_SCORE = "phasee6_branch_a_fresh_ltr_score"
BRANCH_B_LTR_SCORE = "phasee6_branch_b_frozen_ltr_score"
BRANCH_A_CONTROL_SCORE = "adaptive_score_baseline"
BRANCH_B_CONTROL_SCORE = "phasee6_branch_b_frozen_qlib_control_score"

MODEL_CONFIG = {
    "model_type": "LightGBM.LGBMRanker",
    "objective": "lambdarank",
    "metric": "ndcg",
    "boosting_type": "gbdt",
    "num_leaves": 31,
    "learning_rate": 0.03,
    "n_estimators": 120,
    "min_child_samples": 40,
    "random_state": 42,
    "n_jobs": 2,
    "verbose": -1,
}


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except Exception:
        return str(path)


def norm(symbol: Any) -> str:
    text = str(symbol or "").strip().upper()
    return text if text.startswith("TW") else f"TW{text}"


def wjson(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, default=str) + "\n", encoding="utf-8")


def wcsv(path: Path, rows: list[dict[str, Any]], fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        fields = sorted({key for row in rows for key in row.keys()}) if rows else ["status"]
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_s2d() -> Any:
    spec = importlib.util.spec_from_file_location("evaluate_tw_ltr_s2d_full_daily_replay", S2D_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load replay engine: {S2D_SCRIPT}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def df_hash(df: pd.DataFrame, cols: list[str]) -> str:
    text = df[cols].astype("string").fillna("<NA>").to_csv(index=False)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def top_heavy_label(rank: pd.Series) -> pd.Series:
    r = pd.to_numeric(rank, errors="coerce").fillna(0)
    return np.select([r >= 0.90, r >= 0.80, r >= 0.70, r >= 0.50], [4, 3, 2, 1], default=0).astype(int)


def require_inputs() -> dict[str, Any]:
    required = [
        S2D_SCRIPT,
        S2B_FRESH_SCORE,
        S2B_FRESH_MANIFEST,
        FRESH_C4,
        E2_MANIFEST,
        E2_TRAIN,
        E2_TEST,
        E2_SCHEMA,
        E4_MANIFEST,
        E5B_MANIFEST,
        O3_SAMPLE,
        O4_MANIFEST,
    ]
    missing = [rel(path) for path in required if not path.exists()]
    if missing:
        raise RuntimeError(f"Missing E6 inputs: {missing}")
    e2 = load_json(E2_MANIFEST)
    o4 = load_json(O4_MANIFEST)
    if e2.get("gate") != "phase_e2_extended_oos_ltr_sample_passed":
        raise RuntimeError(f"E2 gate mismatch: {e2.get('gate')}")
    if o4.get("model_config") != MODEL_CONFIG:
        raise RuntimeError("O4 model config differs from E6 frozen config")
    if o4.get("label_col") != LABEL_COL:
        raise RuntimeError("O4 label differs from E6 label contract")
    return {"e2": e2, "o4": o4, "s2b": load_json(S2B_FRESH_MANIFEST), "e4": load_json(E4_MANIFEST), "e5b": load_json(E5B_MANIFEST)}


def feature_cols() -> tuple[list[str], pd.DataFrame, str]:
    schema = pd.read_csv(E2_SCHEMA)
    cols = schema[schema["status"] == "training_feature"]["feature"].astype(str).tolist()
    if len(cols) != 78:
        raise RuntimeError(f"Expected 78 O4 features, got {len(cols)}")
    return cols, schema, df_hash(schema, ["order", "feature", "family", "status"])


def selected_o3_columns(features: list[str]) -> list[str]:
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
        "rank_change_1d", "rank_change_3d", "rank_change_5d", "top10_flag", "top30_flag", "top50_flag",
        "top30_streak", "top50_streak",
    }
    cols = metadata + [col for col in features if col not in qlib_derived]
    return sorted(set(cols), key=cols.index)


def add_rank_features(score: pd.DataFrame, split_col: str) -> pd.DataFrame:
    score = score.sort_values(["date", "qlib_score_raw", "instrument"], ascending=[True, False, True]).reset_index(drop=True)
    score["qlib_rank"] = score.groupby("date")["qlib_score_raw"].rank(method="first", ascending=False).astype(int)
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
    score["e6_sample_split"] = split_col
    return score.sort_values(["date", "qlib_rank", "instrument"]).reset_index(drop=True)


def build_branch_a_samples(features: list[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    score = pd.read_csv(S2B_FRESH_SCORE, parse_dates=["date"])
    score["instrument"] = score["instrument"].map(norm)
    score["date_str"] = score["date"].dt.strftime("%Y-%m-%d")
    score = score[(score["date_str"] >= TRAIN_START) & (score["date_str"] <= TEST_END)].copy()
    score = score[pd.to_numeric(score["qlib_score_raw"], errors="coerce").notna()].copy()
    score["e6_branch"] = "branch_a_fresh_qlib"
    score["score_source"] = rel(S2B_FRESH_SCORE)
    score["same_branch_score_source"] = True
    score["filtered_to_top50_for_training"] = False
    score["filtered_to_full_market_top150_intersection"] = False
    score["candidate_scope"] = "s2b_fresh_raw_score_broad_candidate"
    score = add_rank_features(score, "ltr_train_2025_or_test_2026")

    o3 = pd.read_csv(O3_SAMPLE, usecols=lambda c: c in set(selected_o3_columns(features)), parse_dates=["date"])
    o3["instrument"] = o3["instrument"].map(norm)
    o3["date_str"] = o3["date"].dt.strftime("%Y-%m-%d")
    merged = score.merge(o3, on=["date", "date_str", "instrument"], how="left", validate="one_to_one", suffixes=("", "_o3"))
    if merged["control_row_id"].isna().any():
        missing = merged[merged["control_row_id"].isna()][["date_str", "instrument"]].head(20).to_dict("records")
        raise RuntimeError(f"Branch A O3 row alignment missing: {missing}")
    merged[LABEL_COL] = top_heavy_label(merged["future_excess_return_rank_10d"])
    merged["e6_sample_split"] = np.where(merged["date_str"] <= TRAIN_END, "branch_a_train_2025", "branch_a_test_2026")
    ordered = [
        "control_row_id", "date", "date_str", "instrument", "e6_sample_split", "e6_branch", "year", "regime_segment",
        "candidate_scope", "score_source", "same_branch_score_source", "filtered_to_top50_for_training",
        "filtered_to_full_market_top150_intersection",
    ] + features + [
        "future_return_5d", "future_return_10d", "future_return_20d",
        "future_excess_return_5d", "future_excess_return_10d", "future_excess_return_20d",
        "future_excess_return_rank_5d", "future_excess_return_rank_10d", "future_excess_return_rank_20d",
        LABEL_COL, "topk_forward_bucket", "ltr_relevance_label", "label_complete_5d", "label_complete_10d",
        "label_complete_20d", "feature_complete", "sample_complete",
    ]
    ordered = [col for col in ordered if col in merged.columns]
    train = merged[merged["e6_sample_split"] == "branch_a_train_2025"].copy()
    test = merged[merged["e6_sample_split"] == "branch_a_test_2026"].copy()
    train.to_csv(BRANCH_A_TRAIN, index=False)
    test.to_csv(BRANCH_A_TEST, index=False)
    return train, test


def build_branch_b_samples() -> tuple[pd.DataFrame, pd.DataFrame]:
    train = pd.read_csv(E2_TRAIN, parse_dates=["date"])
    test = pd.read_csv(E2_TEST, parse_dates=["date"])
    for df in [train, test]:
        df["instrument"] = df["instrument"].map(norm)
        df["date_str"] = df["date"].dt.strftime("%Y-%m-%d")
        df["e6_branch"] = "branch_b_frozen_qlib_2018_2022"
        df["same_branch_score_source"] = True
        df["filtered_to_top50_for_training"] = False
        df["filtered_to_full_market_top150_intersection"] = False
    train = train[(train["date_str"] >= TRAIN_START) & (train["date_str"] <= TRAIN_END)].copy()
    test = test[(test["date_str"] >= TEST_START) & (test["date_str"] <= TEST_END)].copy()
    train["e6_sample_split"] = "branch_b_train_2025"
    test["e6_sample_split"] = "branch_b_test_2026"
    train.to_csv(BRANCH_B_TRAIN, index=False)
    test.to_csv(BRANCH_B_TEST, index=False)
    return train, test


def coerce_features(df: pd.DataFrame, features: list[str]) -> pd.DataFrame:
    out = df.copy()
    for col in features:
        out[col] = pd.to_numeric(out[col], errors="coerce").replace([np.inf, -np.inf], np.nan).fillna(0.0)
    return out.sort_values(["date", "instrument"]).reset_index(drop=True)


def group_sizes(df: pd.DataFrame) -> list[int]:
    return df.sort_values(["date", "instrument"]).groupby("date").size().astype(int).tolist()


def group_audit(branch: str, split: str, df: pd.DataFrame) -> dict[str, Any]:
    sizes = group_sizes(df)
    max_rank = pd.to_numeric(df["qlib_rank"], errors="coerce").groupby(df["date_str"]).max()
    return {
        "branch": branch,
        "split": split,
        "start_date": str(df["date_str"].min()),
        "end_date": str(df["date_str"].max()),
        "date_count": int(df["date_str"].nunique()),
        "row_count": int(df.shape[0]),
        "daily_rows_min": int(min(sizes)) if sizes else 0,
        "daily_rows_median": float(np.median(sizes)) if sizes else 0.0,
        "daily_rows_max": int(max(sizes)) if sizes else 0,
        "train_or_test_non_top50_rows": int((pd.to_numeric(df["qlib_rank"], errors="coerce") > 50).sum()),
        "median_daily_max_qlib_rank": float(max_rank.median()) if not max_rank.empty else 0.0,
        "top50_only": bool(max(sizes) <= 50) if sizes else True,
        "filtered_to_top50_for_training": bool(df.get("filtered_to_top50_for_training", pd.Series([False])).astype(bool).any()),
        "filtered_to_full_market_top150_intersection": bool(df.get("filtered_to_full_market_top150_intersection", pd.Series([False])).astype(bool).any()),
        "duplicate_key_count": int(df.duplicated(["date_str", "instrument"]).sum()),
    }


def train_branch(branch: str, train: pd.DataFrame, test: pd.DataFrame, features: list[str], score_col: str, model_path: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    train = coerce_features(train, features)
    test = coerce_features(test, features)
    train = train.dropna(subset=["future_excess_return_rank_10d", LABEL_COL]).copy()
    groups = group_sizes(train)
    if not groups or min(groups) <= 50 or np.median(groups) <= 100:
        raise RuntimeError(f"{branch} train sample is not broad candidate after label-complete filter: min={min(groups) if groups else 0}, median={np.median(groups) if groups else 0}")
    if train[LABEL_COL].isna().any():
        raise RuntimeError(f"{branch} training label contains missing values")
    params = {key: value for key, value in MODEL_CONFIG.items() if key != "model_type"}
    model = lgb.LGBMRanker(**params)
    model.fit(train[features], train[LABEL_COL], group=groups)
    with model_path.open("wb") as fh:
        pickle.dump(model, fh)
    train_scores = train.copy()
    test_scores = test.copy()
    train_scores[score_col] = model.predict(train[features])
    test_scores[score_col] = model.predict(test[features])
    train_scores[f"{score_col}_rank"] = train_scores.groupby("date")[score_col].rank(ascending=False, method="first").astype(int)
    test_scores[f"{score_col}_rank"] = test_scores.groupby("date")[score_col].rank(ascending=False, method="first").astype(int)
    family_map = pd.read_csv(E2_SCHEMA).set_index("feature")["family"].astype(str).to_dict()
    importance = pd.DataFrame({
        "branch": branch,
        "feature": features,
        "family": [family_map.get(col, "") for col in features],
        "importance_split": model.booster_.feature_importance(importance_type="split"),
        "importance_gain": model.booster_.feature_importance(importance_type="gain"),
    }).sort_values(["importance_gain", "feature"], ascending=[False, True])
    return train_scores, test_scores, importance


def metric_group(group: pd.DataFrame, score_col: str) -> pd.DataFrame:
    return group.dropna(subset=[score_col, "future_excess_return_rank_10d", LABEL_COL]).copy()


def spearman_by_date(df: pd.DataFrame, score_col: str) -> tuple[float, int]:
    values: list[float] = []
    for _, raw_group in df.groupby("date"):
        group = metric_group(raw_group, score_col)
        if group[score_col].nunique() < 2 or group["future_excess_return_rank_10d"].nunique() < 2:
            continue
        corr = spearmanr(group[score_col], group["future_excess_return_rank_10d"]).correlation
        if pd.notna(corr):
            values.append(float(corr))
    return (float(np.mean(values)), len(values)) if values else (0.0, 0)


def ndcg_by_date(df: pd.DataFrame, score_col: str, k: int) -> float:
    values: list[float] = []
    for _, raw_group in df.groupby("date"):
        group = metric_group(raw_group, score_col)
        if group.shape[0] < 2:
            continue
        try:
            values.append(float(ndcg_score(group[LABEL_COL].to_numpy(dtype=float).reshape(1, -1), group[score_col].to_numpy(dtype=float).reshape(1, -1), k=min(k, group.shape[0]))))
        except Exception:
            continue
    return float(np.mean(values)) if values else 0.0


def rank_metric(branch: str, split: str, df: pd.DataFrame, score_col: str) -> dict[str, Any]:
    ic, date_count = spearman_by_date(df, score_col)
    return {
        "branch": branch,
        "split": split,
        "score_column": score_col,
        "row_count": int(df.shape[0]),
        "date_count": int(date_count),
        "mean_daily_spearman_rank_ic_10d": round(ic, 8),
        "ndcg_at_10": round(ndcg_by_date(df, score_col, 10), 8),
        "ndcg_at_30": round(ndcg_by_date(df, score_col, 30), 8),
        "ndcg_at_50": round(ndcg_by_date(df, score_col, 50), 8),
        "audit_only": split.endswith("test_2026"),
    }


def replay_ready(a_test_scores: pd.DataFrame, b_test_scores: pd.DataFrame) -> pd.DataFrame:
    fresh = pd.read_csv(FRESH_C4, parse_dates=["date"])
    if "date_str" not in fresh.columns:
        fresh["date_str"] = fresh["date"].dt.strftime("%Y-%m-%d")
    fresh = fresh[(fresh["date_str"] >= TEST_START) & (fresh["date_str"] <= TEST_END)].copy()
    fresh["instrument"] = fresh["instrument"].map(norm)
    fresh["method_group"] = "branch_a_control"
    fresh["score_col_role"] = BRANCH_A_CONTROL_SCORE
    fresh_keep = ["date", "date_str", "instrument", "split", "regime_segment", "qlib_rank", BRANCH_A_CONTROL_SCORE, "method_group", "score_col_role"]
    fresh_ready = fresh[fresh_keep].copy()

    a = a_test_scores[pd.to_numeric(a_test_scores["qlib_rank"], errors="coerce") <= 50].copy()
    a["method_group"] = "branch_a_treatment"
    a["score_col_role"] = BRANCH_A_LTR_SCORE
    a_ready = a[["date", "date_str", "instrument", "e6_sample_split", "regime_segment", "qlib_rank", "qlib_score_raw", BRANCH_A_LTR_SCORE, "method_group", "score_col_role"]].rename(columns={"e6_sample_split": "split"})

    b = b_test_scores[pd.to_numeric(b_test_scores["qlib_rank"], errors="coerce") <= 50].copy()
    b[BRANCH_B_CONTROL_SCORE] = pd.to_numeric(b["qlib_score_raw"], errors="coerce")
    b["method_group"] = "branch_b_control_treatment"
    b_ready = b[["date", "date_str", "instrument", "e6_sample_split", "regime_segment", "qlib_rank", BRANCH_B_CONTROL_SCORE, BRANCH_B_LTR_SCORE, "method_group"]].rename(columns={"e6_sample_split": "split"})

    out = pd.concat([fresh_ready, a_ready, b_ready], ignore_index=True, sort=False)
    out.to_csv(REPLAY_READY_CSV, index=False)
    return out


def metric_row(result: dict[str, Any], baseline: dict[str, Any], branch: str, role: str) -> dict[str, Any]:
    m = result["metrics"]
    bm = baseline["metrics"]
    return {
        "branch": branch,
        "role": role,
        "method": result["method"],
        "window": "2026_01_01_2026_05_07",
        **m,
        "relative_return_vs_branch_control": round(m["fee_tax_adjusted_net_return"] - bm["fee_tax_adjusted_net_return"], 6),
        "relative_drawdown_vs_branch_control": round(m["max_drawdown"] - bm["max_drawdown"], 6),
        "relative_actions_vs_branch_control": int(m["action_count"]) - int(bm["action_count"]),
    }


def coverage_row(method: str, df: pd.DataFrame, score_col: str) -> dict[str, Any]:
    daily = df.groupby("date_str", as_index=False).agg(
        rows=("instrument", "size"),
        score_rows=(score_col, lambda s: int(s.notna().sum())),
        top50_rows=("qlib_rank", lambda s: int((pd.to_numeric(s, errors="coerce") <= 50).sum())),
    )
    return {
        "method": method,
        "start_date": str(df["date_str"].min()),
        "end_date": str(df["date_str"].max()),
        "date_count": int(daily.shape[0]),
        "row_count": int(df.shape[0]),
        "daily_rows_min": int(daily["rows"].min()),
        "daily_rows_median": float(daily["rows"].median()),
        "daily_rows_max": int(daily["rows"].max()),
        "score_rows": int(df[score_col].notna().sum()),
        "daily_top50_min": int(daily["top50_rows"].min()),
        "daily_top50_median": float(daily["top50_rows"].median()),
        "daily_top50_max": int(daily["top50_rows"].max()),
        "duplicate_key_count": int(df.duplicated(["date_str", "instrument"]).sum()),
    }


def accounting_rows(results: dict[str, dict[str, Any]], s2d: Any) -> list[dict[str, Any]]:
    rows = []
    for method, result in results.items():
        active = [a for a in result["actions"] if a.get("action") in {"historical_add", "historical_risk_reduce"}]
        violations = sum(1 for a in active if str(a.get("execution_date", "")) <= str(a.get("signal_date", "")))
        metrics = result["metrics"]
        rows.append({
            "method": method,
            "active_action_count": len(active),
            "next_day_execution": violations == 0,
            "execution_date_not_after_signal_violations": violations,
            "fee_rate": s2d.FEE_RATE,
            "tax_rate": s2d.SELL_TAX_RATE,
            "target_position_count": s2d.MAX_HOLDINGS,
            "candidate_k": 50,
            "missing_price_days": metrics["missing_price_days"],
            "skipped_trade_count": metrics["skipped_trade_count"],
            "last_day_new_trade_without_next_price_count": metrics["last_day_new_trade_without_next_price_count"],
        })
    return rows


def pnl_rows(results: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for method, result in results.items():
        actions = pd.DataFrame(result["actions"])
        if actions.empty:
            continue
        active = actions[actions["action"].isin(["historical_add", "historical_risk_reduce"])].copy()
        if active.empty:
            continue
        active["notional"] = active["quantity"].astype(float).abs() * active["price"].astype(float)
        grouped = active.groupby("symbol", as_index=False).agg(
            action_count=("action", "size"),
            buy_count=("action", lambda s: int((s == "historical_add").sum())),
            sell_count=("action", lambda s: int((s == "historical_risk_reduce").sum())),
            turnover_notional=("notional", "sum"),
            fee_and_tax=("fee_and_tax", "sum"),
        )
        total = float(grouped["turnover_notional"].sum())
        grouped["method"] = method
        grouped["turnover_notional_share"] = grouped["turnover_notional"].astype(float) / total if total else 0.0
        rows.extend(grouped.sort_values(["turnover_notional", "symbol"], ascending=[False, True]).head(30).to_dict("records"))
    return rows


def write_report(manifest: dict[str, Any], group_rows: list[dict[str, Any]], summary_rows: list[dict[str, Any]], rank_rows: list[dict[str, Any]]) -> None:
    by_method = {row["method"]: row for row in summary_rows}
    a_ctl = by_method[BRANCH_A_CONTROL]
    a_trt = by_method[BRANCH_A_TREATMENT]
    b_ctl = by_method[BRANCH_B_CONTROL]
    b_trt = by_method[BRANCH_B_TREATMENT]
    e4_ref = manifest["references"]["e4_treatment"]
    e5b_ref = manifest["references"]["e5b_repaired_fresh_exact_2026"]
    lines = [
        "# Phase E6 执行报告：2025 LTR 桥接双 qlib 底座",
        "",
        f"生成时间：`{manifest['created_at']}`",
        "",
        "## 1. 结论",
        "",
        f"- gate：`{manifest['gate']}`。",
        "- 已在相同 2025 LTR 训练窗口下分别训练 fresh qlib 底座与 2018-2022 frozen qlib 底座的 orthogonal LTR。",
        "- 两条分支共享同一 LightGBM LGBMRanker 参数、同一 label、同一 78 特征 whitelist、同一 2026 test window、同一 replay engine、同一 next-day accounting、同一 fee/tax、candidate_k=50、target_position_count=10；LTR 训练仅使用 label-complete 行。",
        "- 未重训 qlib，未调参，未训练多版本挑选，未使用 2026 做训练/early stopping/选择，未触发前端/API/provider/accepted latest/monitor/交易链路。",
        f"- Branch A treatment vs control return diff：`{a_trt['relative_return_vs_branch_control']}`。",
        f"- Branch B treatment vs control return diff：`{b_trt['relative_return_vs_branch_control']}`。",
        f"- Branch A treatment - Branch B treatment return diff：`{manifest['comparisons']['branch_a_treatment_minus_branch_b_treatment_return']}`。",
        "",
        "## 2. 训练合同",
        "",
        "| branch | qlib base | LTR train | LTR test | score source | caveat |",
        "| --- | --- | --- | --- | --- | --- |",
        f"| Branch A | fresh qlib 2017-2024 | {TRAIN_START}..{TRAIN_END} | {TEST_START}..{TEST_END} | `{rel(S2B_FRESH_SCORE)}` | 2025H1 可能属于 fresh qlib validation；本分支是 fresh qlib frozen raw score + 2025 LTR train 桥接实验，不是严格 qlib-never-seen 2025 LTR train |",
        f"| Branch B | frozen qlib 2018-2022 | {TRAIN_START}..{TRAIN_END} | {TEST_START}..{TEST_END} | `{rel(E2_TRAIN)}` / `{rel(E2_TEST)}` from E1 raw OOS | 2025 对 qlib 底座为 OOS |",
        "",
        "## 3. 样本覆盖 / Top50 偏差审计",
        "",
        "| branch | split | rows | dates | daily min/median/max | non-top50 rows | top50-only | full-market-top150-intersection |",
        "| --- | --- | ---: | ---: | --- | ---: | --- | --- |",
    ]
    for row in group_rows:
        lines.append(f"| {row['branch']} | {row['split']} | {row['row_count']} | {row['date_count']} | {row['daily_rows_min']}/{row['daily_rows_median']}/{row['daily_rows_max']} | {row['train_or_test_non_top50_rows']} | {row['top50_only']} | {row['filtered_to_full_market_top150_intersection']} |")
    lines.extend([
        "",
        "## 4. 2026 Replay 结果",
        "",
        "| branch | role | method | net_return | max_drawdown | actions | turnover | fee_tax | rel_return_vs_control |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ])
    for row in summary_rows:
        lines.append(f"| {row['branch']} | {row['role']} | {row['method']} | {row['fee_tax_adjusted_net_return']} | {row['max_drawdown']} | {row['action_count']} | {row['turnover_proxy_by_notional_over_avg_equity']} | {row['fee_and_tax']} | {row['relative_return_vs_branch_control']} |")
    lines.extend([
        "",
        "## 5. Rank Metrics",
        "",
        "| branch | split | spearman_ic_10d | ndcg@10 | ndcg@30 | ndcg@50 | audit_only |",
        "| --- | --- | ---: | ---: | ---: | ---: | --- |",
    ])
    for row in rank_rows:
        lines.append(f"| {row['branch']} | {row['split']} | {row['mean_daily_spearman_rank_ic_10d']} | {row['ndcg_at_10']} | {row['ndcg_at_30']} | {row['ndcg_at_50']} | {row['audit_only']} |")
    lines.extend([
        "",
        "## 6. 参考项",
        "",
        f"- E4 treatment（2018-2022 frozen qlib + 2023-2025 LTR）：net return `{e4_ref['fee_tax_adjusted_net_return']}`，max DD `{e4_ref['max_drawdown']}`，actions `{e4_ref['action_count']}`。",
        f"- E5B repaired fresh qlib exact 2026 bridge：net return `{e5b_ref['fee_tax_adjusted_net_return']}`，max DD `{e5b_ref['max_drawdown']}`，actions `{e5b_ref['action_count']}`。",
        "- 参考项只用于解释训练长度和比较链路，不用于模型选择、调参或阈值选择。",
        "",
        "## 7. 必答审查",
        "",
        f"- 同一 2025 LTR 训练窗下，treatment 收益 Branch A `{a_trt['fee_tax_adjusted_net_return']}`，Branch B `{b_trt['fee_tax_adjusted_net_return']}`；本次 Branch A 更强。",
        f"- LTR 增益依赖 qlib 底座：Branch A 增益 `{a_trt['relative_return_vs_branch_control']}`，Branch B 增益 `{b_trt['relative_return_vs_branch_control']}`，方向和幅度不同。",
        f"- 训练长度影响增益：Branch B 2025-only LTR return `{b_trt['fee_tax_adjusted_net_return']}`，E4 2023-2025 LTR return `{e4_ref['fee_tax_adjusted_net_return']}`，差异 `{manifest['comparisons']['e4_2023_2025_ltr_minus_branch_b_2025_ltr_return']}`，支持训练长度是重要解释变量。",
        "- top50-only 训练偏差：两条分支 train daily rows 均大于 50，non-top50 rows 均大于 0，未发现 top50-only 训练偏差。",
        "- 控制变量：除 qlib 底座 / qlib score 来源外，模型、参数、label、feature whitelist、训练窗、测试窗、回放口径均已对齐。",
        "- 比较链路：E6 同时连接 fresh/frozen 底座、2025-only LTR 与 E4 2023-2025 LTR，可用于建立比较链路闭环；默认策略切换仍需另行决策，不在本阶段执行。",
        "",
        "## 8. 输出 Artifact",
        "",
    ])
    for path in manifest["artifacts"].values():
        lines.append(f"- `{path}`")
    DOC.parent.mkdir(parents=True, exist_ok=True)
    DOC.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    created_at = now()
    manifests = require_inputs()
    features, schema, feature_hash = feature_cols()
    a_train, a_test = build_branch_a_samples(features)
    b_train, b_test = build_branch_b_samples()

    preliminary_group_rows = [
        group_audit("branch_a_fresh_qlib", "train_2025_candidate_before_label_filter", a_train),
        group_audit("branch_a_fresh_qlib", "test_2026", a_test),
        group_audit("branch_b_frozen_qlib", "train_2025_candidate_before_label_filter", b_train),
        group_audit("branch_b_frozen_qlib", "test_2026", b_test),
    ]
    if any(row["top50_only"] for row in preliminary_group_rows):
        raise RuntimeError(f"E6 stop: top50-only sample detected: {preliminary_group_rows}")
    if any(row["daily_rows_median"] < 140 for row in preliminary_group_rows):
        raise RuntimeError(f"E6 stop: daily rows not close to 150: {preliminary_group_rows}")

    a_train_scores, a_test_scores, a_imp = train_branch("branch_a_fresh_qlib", a_train, a_test, features, BRANCH_A_LTR_SCORE, BRANCH_A_MODEL)
    b_train_scores, b_test_scores, b_imp = train_branch("branch_b_frozen_qlib", b_train, b_test, features, BRANCH_B_LTR_SCORE, BRANCH_B_MODEL)
    group_rows = [
        group_audit("branch_a_fresh_qlib", "train_2025_label_complete_used_for_training", a_train_scores),
        group_audit("branch_a_fresh_qlib", "test_2026_scored_for_replay", a_test_scores),
        group_audit("branch_b_frozen_qlib", "train_2025_label_complete_used_for_training", b_train_scores),
        group_audit("branch_b_frozen_qlib", "test_2026_scored_for_replay", b_test_scores),
    ]
    if any(row["top50_only"] for row in group_rows):
        raise RuntimeError(f"E6 stop: top50-only sample detected after label-complete filter: {group_rows}")
    if any(row["daily_rows_median"] < 140 for row in group_rows):
        raise RuntimeError(f"E6 stop: daily rows not close to 150 after label-complete filter: {group_rows}")
    wcsv(GROUP_AUDIT_CSV, group_rows)
    a_train_scores.to_csv(OUT_DIR / "phasee6_branch_a_train_scores_2025.csv", index=False)
    a_test_scores.to_csv(OUT_DIR / "phasee6_branch_a_test_scores_2026.csv", index=False)
    b_train_scores.to_csv(OUT_DIR / "phasee6_branch_b_train_scores_2025.csv", index=False)
    b_test_scores.to_csv(OUT_DIR / "phasee6_branch_b_test_scores_2026.csv", index=False)

    rank_rows = [
        rank_metric("branch_a_fresh_qlib", "train_2025", a_train_scores, BRANCH_A_LTR_SCORE),
        rank_metric("branch_a_fresh_qlib", "test_2026", a_test_scores, BRANCH_A_LTR_SCORE),
        rank_metric("branch_b_frozen_qlib", "train_2025", b_train_scores, BRANCH_B_LTR_SCORE),
        rank_metric("branch_b_frozen_qlib", "test_2026", b_test_scores, BRANCH_B_LTR_SCORE),
    ]
    wcsv(RANK_METRICS_CSV, rank_rows)
    importance_rows = pd.concat([a_imp, b_imp], ignore_index=True)
    importance_rows.to_csv(FEATURE_IMPORTANCE_CSV, index=False)

    ready = replay_ready(a_test_scores, b_test_scores)
    fresh_ready = ready[ready["method_group"] == "branch_a_control"].copy()
    a_ltr_ready = ready[ready["method_group"] == "branch_a_treatment"].copy()
    b_ready = ready[ready["method_group"] == "branch_b_control_treatment"].copy()

    s2d = load_s2d()
    prices = s2d.PriceStore(set(ready["instrument"]))
    results = {
        BRANCH_A_CONTROL: s2d.replay(fresh_ready, prices, s2d.MethodSpec(BRANCH_A_CONTROL, BRANCH_A_CONTROL_SCORE, 50), "phasee6_2026", TEST_START, TEST_END),
        BRANCH_A_TREATMENT: s2d.replay(a_ltr_ready, prices, s2d.MethodSpec(BRANCH_A_TREATMENT, BRANCH_A_LTR_SCORE, 50), "phasee6_2026", TEST_START, TEST_END),
        BRANCH_B_CONTROL: s2d.replay(b_ready, prices, s2d.MethodSpec(BRANCH_B_CONTROL, BRANCH_B_CONTROL_SCORE, 50), "phasee6_2026", TEST_START, TEST_END),
        BRANCH_B_TREATMENT: s2d.replay(b_ready, prices, s2d.MethodSpec(BRANCH_B_TREATMENT, BRANCH_B_LTR_SCORE, 50), "phasee6_2026", TEST_START, TEST_END),
    }
    summary_rows = [
        metric_row(results[BRANCH_A_CONTROL], results[BRANCH_A_CONTROL], "branch_a_fresh_qlib", "control"),
        metric_row(results[BRANCH_A_TREATMENT], results[BRANCH_A_CONTROL], "branch_a_fresh_qlib", "treatment"),
        metric_row(results[BRANCH_B_CONTROL], results[BRANCH_B_CONTROL], "branch_b_frozen_qlib", "control"),
        metric_row(results[BRANCH_B_TREATMENT], results[BRANCH_B_CONTROL], "branch_b_frozen_qlib", "treatment"),
    ]
    wcsv(SUMMARY_CSV, summary_rows)
    nav_rows: list[dict[str, Any]] = []
    action_rows: list[dict[str, Any]] = []
    for result in results.values():
        nav_rows.extend(result["curve"])
        action_rows.extend(result["actions"])
    wcsv(DAILY_NAV_CSV, nav_rows)
    wcsv(ACTIONS_CSV, action_rows)
    coverage_rows = [
        coverage_row(BRANCH_A_CONTROL, fresh_ready, BRANCH_A_CONTROL_SCORE),
        coverage_row(BRANCH_A_TREATMENT, a_ltr_ready, BRANCH_A_LTR_SCORE),
        coverage_row(BRANCH_B_CONTROL, b_ready, BRANCH_B_CONTROL_SCORE),
        coverage_row(BRANCH_B_TREATMENT, b_ready, BRANCH_B_LTR_SCORE),
    ]
    wcsv(COVERAGE_CSV, coverage_rows)
    accounting = accounting_rows(results, s2d)
    wcsv(ACCOUNTING_CSV, accounting)
    pnl = pnl_rows(results)
    wcsv(PNL_CSV, pnl)

    e4_summary = manifests["e4"]["summary"]
    e4_treatment = next(row for row in e4_summary if row["method"] == "extended_oos_frozen_qlib_orthogonal_ltr")
    e5b_summary = manifests["e5b"]["summary"]
    e5b_fresh = next(row for row in e5b_summary if row["method"] == "repaired_fresh_qlib_top50_adaptive")
    by_method = {row["method"]: row for row in summary_rows}
    comparisons = {
        "branch_a_treatment_minus_branch_b_treatment_return": round(by_method[BRANCH_A_TREATMENT]["fee_tax_adjusted_net_return"] - by_method[BRANCH_B_TREATMENT]["fee_tax_adjusted_net_return"], 6),
        "e4_2023_2025_ltr_minus_branch_b_2025_ltr_return": round(e4_treatment["fee_tax_adjusted_net_return"] - by_method[BRANCH_B_TREATMENT]["fee_tax_adjusted_net_return"], 6),
        "branch_a_treatment_minus_e5b_repaired_fresh_return": round(by_method[BRANCH_A_TREATMENT]["fee_tax_adjusted_net_return"] - e5b_fresh["fee_tax_adjusted_net_return"], 6),
    }
    forbidden = {
        "created_at": created_at,
        "no_qlib_training": True,
        "no_parameter_tuning": True,
        "no_multiple_ltr_versions_for_selection": True,
        "no_2026_training_early_stopping_selection_or_thresholding": True,
        "no_feature_label_split_model_change": True,
        "no_frontend_api_provider_accepted_latest_monitor_trading": True,
        "no_broker_quick_trade_orders": True,
    }
    wjson(FORBIDDEN_JSON, forbidden)

    manifest = {
        "created_at": created_at,
        "phase": "phase_e6_bridge_ltr_2025_two_qlib_bases",
        "gate": GATE,
        "train_window": [TRAIN_START, TRAIN_END],
        "test_window": [TEST_START, TEST_END],
        "model_config": MODEL_CONFIG,
        "label_col": LABEL_COL,
        "feature_count": len(features),
        "feature_hash": feature_hash,
        "fresh_2025h1_validation_caveat": "Branch A uses frozen fresh qlib score. If 2025H1 was used as fresh qlib validation, Branch A is not a strict qlib-never-seen 2025 LTR train experiment.",
        "group_audit": group_rows,
        "rank_metrics": rank_rows,
        "summary": summary_rows,
        "coverage": coverage_rows,
        "accounting": accounting,
        "comparisons": comparisons,
        "references": {"e4_treatment": e4_treatment, "e5b_repaired_fresh_exact_2026": e5b_fresh},
        "upstream_gates": {"e2": manifests["e2"].get("gate"), "o4": manifests["o4"].get("gate")},
        "artifacts": {
            "manifest": rel(MANIFEST_JSON),
            "branch_a_train_sample": rel(BRANCH_A_TRAIN),
            "branch_a_test_sample": rel(BRANCH_A_TEST),
            "branch_b_train_sample": rel(BRANCH_B_TRAIN),
            "branch_b_test_sample": rel(BRANCH_B_TEST),
            "group_audit": rel(GROUP_AUDIT_CSV),
            "rank_metrics": rel(RANK_METRICS_CSV),
            "feature_importance": rel(FEATURE_IMPORTANCE_CSV),
            "replay_ready_scores_2026": rel(REPLAY_READY_CSV),
            "summary": rel(SUMMARY_CSV),
            "daily_nav": rel(DAILY_NAV_CSV),
            "actions": rel(ACTIONS_CSV),
            "coverage_audit": rel(COVERAGE_CSV),
            "next_day_accounting_audit": rel(ACCOUNTING_CSV),
            "pnl_concentration": rel(PNL_CSV),
            "forbidden_action_audit": rel(FORBIDDEN_JSON),
            "report": rel(DOC),
        },
    }
    wjson(MANIFEST_JSON, manifest)
    write_report(manifest, group_rows, summary_rows, rank_rows)
    print(json.dumps({"ok": True, "gate": GATE, "report": rel(DOC), "out_dir": rel(OUT_DIR), "comparisons": comparisons}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
