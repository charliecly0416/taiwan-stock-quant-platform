#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import pickle
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import lightgbm as lgb
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.metrics import ndcg_score

ROOT = Path(__file__).resolve().parents[1]
E2_DIR = ROOT / "data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e2_row_aligned_sample"
E2_MANIFEST = E2_DIR / "phasee2_sample_manifest.json"
E2_TRAIN = E2_DIR / "phasee2_ltr_train_sample_2023_2025.csv"
E2_TEST = E2_DIR / "phasee2_ltr_test_sample_2026.csv"
E2_SCHEMA = E2_DIR / "phasee2_feature_schema.csv"
O4_MANIFEST = ROOT / "data_tw/experiments/ltr_orthogonal_features_controlled/phase_o4_controlled_treatment_ltr/phaseo4_training_manifest.json"
OUT_DIR = ROOT / "data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e3_orthogonal_ltr_training"
DOC = ROOT / "docs/tw_extended_oos_qlib_orthogonal_ltr/PHASEE3_ORTHOGONAL_LTR_TRAINING_EXECUTION_REPORT_CN.md"
MANIFEST_JSON = OUT_DIR / "phasee3_training_manifest.json"
MODEL_PATH = OUT_DIR / "phasee3_ltr_model.pkl"
TRAIN_SCORES_CSV = OUT_DIR / "phasee3_train_row_scores.csv"
TEST_SCORES_CSV = OUT_DIR / "phasee3_test_row_scores_2026.csv"
IMPORTANCE_CSV = OUT_DIR / "phasee3_feature_importance.csv"
METRICS_CSV = OUT_DIR / "phasee3_rank_metrics.csv"
GROUP_AUDIT_CSV = OUT_DIR / "phasee3_group_audit.csv"
TRAINING_LOG_TXT = OUT_DIR / "phasee3_training_log.txt"
FORBIDDEN_JSON = OUT_DIR / "phasee3_forbidden_action_audit.json"
TRAIN_START = "2023-01-01"
TRAIN_END = "2025-12-31"
TEST_START = "2026-01-01"
TEST_END = "2026-05-07"
LABEL_COL = "relevance_10d_top_heavy"
SCORE_COL = "phasee3_extended_oos_ltr_score"
RANK_COL = "phasee3_extended_oos_ltr_rank"
GATE = "phase_e3_extended_oos_ltr_trained"
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
    import hashlib
    text = df[cols].astype("string").fillna("<NA>").to_csv(index=False)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def require_inputs() -> tuple[dict[str, Any], dict[str, Any]]:
    required = [E2_MANIFEST, E2_TRAIN, E2_TEST, E2_SCHEMA, O4_MANIFEST]
    missing = [rel(path) for path in required if not path.exists()]
    if missing:
        raise RuntimeError(f"Missing E3 inputs: {missing}")
    e2 = load_json(E2_MANIFEST)
    if e2.get("gate") != "phase_e2_extended_oos_ltr_sample_passed":
        raise RuntimeError(f"E2 gate is not passed: {e2.get('gate')}")
    o4 = load_json(O4_MANIFEST)
    if o4.get("model_config") != MODEL_CONFIG:
        raise RuntimeError("O4 model config does not match frozen E3 MODEL_CONFIG")
    if o4.get("label_col") != LABEL_COL:
        raise RuntimeError("O4 label col does not match E3 label contract")
    return e2, o4

def group_sizes(df: pd.DataFrame) -> list[int]:
    return df.sort_values(["date", "instrument"]).groupby("date").size().astype(int).tolist()

def coerce_features(df: pd.DataFrame, feature_cols: list[str]) -> pd.DataFrame:
    out = df.copy()
    for col in feature_cols:
        out[col] = pd.to_numeric(out[col], errors="coerce").replace([np.inf, -np.inf], np.nan).fillna(0.0)
    return out

def spearman_by_date(df: pd.DataFrame, score_col: str) -> tuple[float, int]:
    values: list[float] = []
    for _, group in df.groupby("date"):
        if group[score_col].nunique() < 2 or group["future_excess_return_rank_10d"].nunique() < 2:
            continue
        corr = spearmanr(group[score_col], group["future_excess_return_rank_10d"]).correlation
        if pd.notna(corr):
            values.append(float(corr))
    return (float(np.mean(values)), len(values)) if values else (0.0, 0)

def ndcg_by_date(df: pd.DataFrame, score_col: str, k: int) -> float:
    values: list[float] = []
    for _, group in df.groupby("date"):
        if group.shape[0] < 2:
            continue
        y_true = group[LABEL_COL].to_numpy(dtype=float).reshape(1, -1)
        y_score = group[score_col].to_numpy(dtype=float).reshape(1, -1)
        try:
            values.append(float(ndcg_score(y_true, y_score, k=min(k, group.shape[0]))))
        except Exception:
            continue
    return float(np.mean(values)) if values else 0.0

def rank_metrics(df: pd.DataFrame, split: str) -> dict[str, Any]:
    rank_ic, date_count = spearman_by_date(df, SCORE_COL)
    return {"split": split, "score_column": SCORE_COL, "row_count": int(df.shape[0]), "date_count": int(date_count), "mean_daily_spearman_rank_ic_10d": rank_ic, "ndcg_at_10": ndcg_by_date(df, SCORE_COL, 10), "ndcg_at_30": ndcg_by_date(df, SCORE_COL, 30), "ndcg_at_50": ndcg_by_date(df, SCORE_COL, 50), "audit_only": split == "test_2026"}

def group_audit(df: pd.DataFrame, split: str) -> dict[str, Any]:
    sizes = group_sizes(df)
    max_rank_by_day = df.groupby("date")["qlib_rank"].max()
    return {"split": split, "date_count": int(df["date"].nunique()), "row_count": int(df.shape[0]), "group_size_min": int(min(sizes)) if sizes else 0, "group_size_median": float(np.median(sizes)) if sizes else 0.0, "group_size_max": int(max(sizes)) if sizes else 0, "median_daily_max_qlib_rank": float(max_rank_by_day.median()) if not max_rank_by_day.empty else 0.0, "empty_group_count": 0, "top50_only_group": bool(max(sizes) <= 50) if sizes else True, "non_top50_rows": int((pd.to_numeric(df["qlib_rank"], errors="coerce") > 50).sum()), "full_market_top150_intersection_compressed": False}

def write_report(manifest: dict[str, Any], group_rows: list[dict[str, Any]], metrics_rows: list[dict[str, Any]], importance_rows: list[dict[str, Any]]) -> None:
    lines = ["# Phase E3 执行报告：Orthogonal LTR Training", "", f"生成时间：`{manifest['created_at']}`", "", "## 1. 结论", "", f"- gate：`{manifest['gate']}`。", "- 仅使用 E2 通过审计的 2023-2025 宽候选 row-aligned 样本训练一个 extended OOS qlib + orthogonal LTR treatment。", "- 2026 样本只用于 score / rank metric audit，不用于训练、调参、early stopping、模型选择或阈值选择。", "- 未训练 qlib，未调参，未训练多个版本，未回放。", "", "## 2. 使用 Artifact", "", f"- E2 manifest：`{rel(E2_MANIFEST)}`", f"- train sample：`{rel(E2_TRAIN)}`", f"- test score sample：`{rel(E2_TEST)}`", f"- feature schema：`{rel(E2_SCHEMA)}`", f"- O4 model config：`{rel(O4_MANIFEST)}`", "", "## 3. Train / Test", "", f"- train period：`{manifest['train_period'][0]}..{manifest['train_period'][1]}`，rows：`{manifest['train_rows']}`。", f"- test period：`{manifest['test_period'][0]}..{manifest['test_period'][1]}`，rows：`{manifest['test_rows']}`。", "- candidate scope：`E1R broad candidate rows`。", "- future replay boundary：`qlib top50 rerank only`。", "", "## 4. Model Config Audit", "", "| field | value |", "| --- | --- |"]
    for key, value in manifest["model_config"].items():
        lines.append(f"| {key} | {value} |")
    lines.extend(["", "## 5. Feature / Label", "", f"- label：`{LABEL_COL}`，沿用 O4 / Phase1C。", f"- feature count：`{manifest['feature_count']}`。", f"- feature hash：`{manifest['feature_hash']}`。", "- feature whitelist 来自 E2 / O4，未新增特征族。", "", "## 6. Group Audit", "", "| split | rows | dates | group min/median/max | median max rank | top50-only | non top50 rows |", "| --- | ---: | ---: | --- | ---: | --- | ---: |"])
    for row in group_rows:
        lines.append(f"| {row['split']} | {row['row_count']} | {row['date_count']} | {row['group_size_min']}/{row['group_size_median']}/{row['group_size_max']} | {row['median_daily_max_qlib_rank']} | {row['top50_only_group']} | {row['non_top50_rows']} |")
    lines.extend(["", "## 7. Rank Metrics", "", "| split | rows | dates | spearman_ic_10d | ndcg@10 | ndcg@30 | ndcg@50 | audit_only |", "| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |"])
    for row in metrics_rows:
        lines.append(f"| {row['split']} | {row['row_count']} | {row['date_count']} | {row['mean_daily_spearman_rank_ic_10d']} | {row['ndcg_at_10']} | {row['ndcg_at_30']} | {row['ndcg_at_50']} | {row['audit_only']} |")
    lines.extend(["", "## 8. Feature Importance Top20", "", "| feature | family | importance_split | importance_gain |", "| --- | --- | ---: | ---: |"])
    for row in importance_rows[:20]:
        lines.append(f"| {row['feature']} | {row['family']} | {row['importance_split']} | {row['importance_gain']} |")
    lines.extend(["", "## 9. 边界审计", "", "- 只训练了一个 treatment。", "- 模型家族和参数完全沿用 O4。", "- train 只来自 2023-2025。", "- 训练 group 是宽候选集合，不是 top50-only。", "- 2026 未用于训练、调参或选择。", "- 未使用 qlib 2018..2022 in-sample score。", "- 未引入 walk-forward 或多模型 score。", "- 未回放。", "- 未触发 frontend/API/provider/accepted latest/monitor/交易链路。", "", "## 10. 输出 Artifact", "", f"- `{rel(MANIFEST_JSON)}`", f"- `{rel(MODEL_PATH)}`", f"- `{rel(TRAIN_SCORES_CSV)}`", f"- `{rel(TEST_SCORES_CSV)}`", f"- `{rel(IMPORTANCE_CSV)}`", f"- `{rel(METRICS_CSV)}`", f"- `{rel(GROUP_AUDIT_CSV)}`", f"- `{rel(TRAINING_LOG_TXT)}`", f"- `{rel(FORBIDDEN_JSON)}`", "", "## 11. 是否建议进入 E4", "", f"- 建议：允许进入 E4，gate 为 `{manifest['gate']}`。"])
    DOC.parent.mkdir(parents=True, exist_ok=True)
    DOC.write_text("\n".join(lines) + "\n", encoding="utf-8")

def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    created_at = now()
    e2, o4 = require_inputs()
    schema = pd.read_csv(E2_SCHEMA)
    feature_cols = schema[schema["status"] == "training_feature"]["feature"].astype(str).tolist()
    if len(feature_cols) != 78:
        raise RuntimeError(f"Expected 78 training features, got {len(feature_cols)}")
    train = pd.read_csv(E2_TRAIN, parse_dates=["date"])
    test = pd.read_csv(E2_TEST, parse_dates=["date"])
    train["date_str"] = train["date"].dt.strftime("%Y-%m-%d")
    test["date_str"] = test["date"].dt.strftime("%Y-%m-%d")
    if not train["date_str"].between(TRAIN_START, TRAIN_END).all():
        raise RuntimeError("E3 train rows are not only 2023-2025")
    if not test["date_str"].between(TEST_START, TEST_END).all():
        raise RuntimeError("E3 test rows are not only 2026")
    if train[LABEL_COL].isna().any():
        raise RuntimeError("E3 training label has missing rows")
    if any(col not in train.columns or col not in test.columns for col in feature_cols):
        raise RuntimeError("E3 feature whitelist is not fully present in train/test samples")
    if not train["same_e1_frozen_qlib_score_source"].all() or not test["same_e1_frozen_qlib_score_source"].all():
        raise RuntimeError("E3 samples do not all use same E1 frozen qlib score source")
    train = coerce_features(train.sort_values(["date", "instrument"]), feature_cols)
    test = coerce_features(test.sort_values(["date", "instrument"]), feature_cols)
    train_groups = group_sizes(train)
    test_groups = group_sizes(test)
    if not train_groups or min(train_groups) <= 50 or np.median(train_groups) <= 100:
        raise RuntimeError(f"E3 train group sizes are not broad candidates: min={min(train_groups) if train_groups else 0}, median={np.median(train_groups) if train_groups else 0}")
    if not test_groups or min(test_groups) <= 50 or np.median(test_groups) <= 100:
        raise RuntimeError(f"E3 test group sizes are not broad candidates: min={min(test_groups) if test_groups else 0}, median={np.median(test_groups) if test_groups else 0}")
    model_params = {key: value for key, value in MODEL_CONFIG.items() if key != "model_type"}
    model = lgb.LGBMRanker(**model_params)
    model.fit(train[feature_cols], train[LABEL_COL], group=train_groups)
    with MODEL_PATH.open("wb") as fh:
        pickle.dump(model, fh)
    base_cols = ["control_row_id", "date", "date_str", "instrument", "e2_sample_split", "qlib_score_raw", "qlib_rank", "top50_flag", "future_excess_return_rank_10d", LABEL_COL]
    train_scores = train[base_cols].copy()
    train_scores[SCORE_COL] = model.predict(train[feature_cols])
    train_scores[RANK_COL] = train_scores.groupby("date")[SCORE_COL].rank(ascending=False, method="first").astype(int)
    test_scores = test[base_cols].copy()
    test_scores[SCORE_COL] = model.predict(test[feature_cols])
    test_scores[RANK_COL] = test_scores.groupby("date")[SCORE_COL].rank(ascending=False, method="first").astype(int)
    train_scores.to_csv(TRAIN_SCORES_CSV, index=False)
    test_scores.to_csv(TEST_SCORES_CSV, index=False)
    scored_train = train.merge(train_scores[["control_row_id", SCORE_COL]], on="control_row_id", how="left")
    scored_test = test.merge(test_scores[["control_row_id", SCORE_COL]], on="control_row_id", how="left")
    metrics_rows = [rank_metrics(scored_train, "train_2023_2025"), rank_metrics(scored_test, "test_2026")]
    wcsv(METRICS_CSV, metrics_rows)
    group_rows = [group_audit(train, "train_2023_2025"), group_audit(test, "test_2026")]
    wcsv(GROUP_AUDIT_CSV, group_rows)
    importance = pd.DataFrame({"feature": feature_cols, "importance_split": model.booster_.feature_importance(importance_type="split"), "importance_gain": model.booster_.feature_importance(importance_type="gain")})
    family_map = dict(zip(schema["feature"].astype(str), schema["family"].astype(str)))
    importance["family"] = importance["feature"].map(family_map)
    importance = importance.sort_values("importance_gain", ascending=False)
    importance.to_csv(IMPORTANCE_CSV, index=False)
    if float(importance["importance_gain"].sum()) <= 0:
        raise RuntimeError("E3 feature importance is all zero")
    if any(row["top50_only_group"] for row in group_rows):
        raise RuntimeError("E3 group audit detected top50-only group")
    feature_hash = df_hash(schema, ["order", "feature", "family", "status"])
    training_log = {"created_at": created_at, "phase": "phase_e3_orthogonal_ltr_training", "rows_used_for_training": int(train.shape[0]), "rows_scored_train": int(train_scores.shape[0]), "rows_scored_test": int(test_scores.shape[0]), "lightgbm_best_iteration": int(getattr(model, "best_iteration_", 0) or MODEL_CONFIG["n_estimators"]), "trained_single_treatment": True, "no_eval_set_from_2026": True, "no_early_stopping": True, "group_source": "date-level broad candidate rows"}
    TRAINING_LOG_TXT.write_text(json.dumps(training_log, ensure_ascii=True, indent=2, default=str) + "\n", encoding="utf-8")
    forbidden = {"created_at": created_at, "phase": "phase_e3_orthogonal_ltr_training", "no_qlib_training": True, "no_ltr_parameter_search": True, "single_ltr_treatment_trained": True, "no_model_family_change": True, "no_label_split_change": True, "no_2026_training_tuning_or_selection": True, "no_top50_only_training": True, "no_full_market_top150_intersection_compression": True, "no_qlib_in_sample_score": True, "no_walk_forward_oos_or_multi_model_score": True, "no_replay": True, "no_frontend_api_provider_accepted_latest_monitor_trading": True, "no_broker_quick_trade_orders": True}
    wjson(FORBIDDEN_JSON, forbidden)
    manifest = {"created_at": created_at, "phase": "phase_e3_orthogonal_ltr_training", "gate": GATE, "upstream_gates": {"e2": e2.get("gate")}, "train_period": [TRAIN_START, TRAIN_END], "test_period": [TEST_START, TEST_END], "train_rows": int(train.shape[0]), "test_rows": int(test.shape[0]), "model_config": MODEL_CONFIG, "model_config_equals_o4": o4.get("model_config") == MODEL_CONFIG, "label_col": LABEL_COL, "label_equals_o4": o4.get("label_col") == LABEL_COL, "feature_count": len(feature_cols), "feature_hash": feature_hash, "group_audit": group_rows, "rank_metrics": metrics_rows, "feature_importance_top20": importance.head(20).to_dict("records"), "score_provenance": e2.get("score_provenance"), "candidate_scope": "E2 broad candidate rows", "future_replay_boundary": "qlib top50 rerank only", "no_2026_training_tuning_or_selection": True, "single_treatment_trained": True, "no_replay": True, "artifacts": {"training_manifest": rel(MANIFEST_JSON), "model_artifact": rel(MODEL_PATH), "train_row_scores": rel(TRAIN_SCORES_CSV), "test_row_scores_2026": rel(TEST_SCORES_CSV), "feature_importance": rel(IMPORTANCE_CSV), "rank_metrics": rel(METRICS_CSV), "group_audit": rel(GROUP_AUDIT_CSV), "training_log": rel(TRAINING_LOG_TXT), "forbidden_action_audit": rel(FORBIDDEN_JSON), "report": rel(DOC)}}
    wjson(MANIFEST_JSON, manifest)
    write_report(manifest, group_rows, metrics_rows, importance.to_dict("records"))
    print(json.dumps({"ok": True, "gate": GATE, "report": rel(DOC), "out_dir": rel(OUT_DIR)}, ensure_ascii=False, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
