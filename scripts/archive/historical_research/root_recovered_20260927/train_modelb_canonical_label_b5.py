#!/usr/bin/env python3
"""Train an isolated Model B with canonical labels after a new run freeze."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import joblib
import lightgbm as lgb
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.metrics import ndcg_score

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b5_canonical_label_lgbm_20260914"
B4_DIR = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b4_canonical_label_samples_20260914"
B4_MANIFEST = B4_DIR / "B4_CANONICAL_EXECUTOR_MANIFEST.json"
B4_TRAIN = B4_DIR / "B4_CANONICAL_TRAIN_SAMPLE.parquet"
B4_TEST = B4_DIR / "B4_CANONICAL_TEST_SAMPLE.parquet"
B2_SCHEMA = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b2_canonical_pit_features_20260913/FEATURE_SCHEMA.json"
LABEL_MANIFEST = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_canonical_labels_20260914/CANONICAL_LABEL_MANIFEST.json"
LABEL = "relevance_10d_top_heavy_canonical"
KEY = ["date", "instrument"]
FIT_START, FIT_END = "2023-01-10", "2024-12-17"
EMBARGO_START, EMBARGO_END = "2024-12-18", "2024-12-31"
VALID_START, VALID_END = "2025-01-02", "2025-12-31"
TEST_START, TEST_END = "2026-01-02", "2026-04-22"
CONFIG = {"objective": "lambdarank", "metric": "ndcg", "boosting_type": "gbdt", "num_leaves": 31, "learning_rate": 0.03, "n_estimators": 120, "min_child_samples": 40, "random_state": 42, "n_jobs": 2, "verbosity": -1}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def metrics(frame: pd.DataFrame, scores: np.ndarray, split: str) -> dict[str, object]:
    x = frame[KEY + [LABEL]].copy(); x["score"] = scores
    nd = {10: [], 30: [], 50: []}; ic = []
    for _, g in x.groupby("date", sort=True):
        y, s = g[LABEL].to_numpy(float), g.score.to_numpy(float)
        for k in nd: nd[k].append(float(ndcg_score(y[None, :], s[None, :], k=min(k, len(g)))))
        rho = spearmanr(s, y).statistic
        if np.isfinite(rho): ic.append(float(rho))
    return {"split": split, "rows": int(len(x)), "dates": int(x.date.nunique()), "ndcg_at_10": float(np.mean(nd[10])), "ndcg_at_30": float(np.mean(nd[30])), "ndcg_at_50": float(np.mean(nd[50])), "mean_daily_spearman_label": float(np.mean(ic)), "audit_only": split == "test_2026"}


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    freeze_path = OUT / "B5_CANONICAL_RUN_FREEZE.json"
    if freeze_path.exists() or (OUT / "MODEL_B_CANONICAL_LGBM_RANKER.pkl").exists():
        raise RuntimeError("canonical B5 output already exists; refusing overwrite")
    b4 = json.loads(B4_MANIFEST.read_text()); labels = json.loads(LABEL_MANIFEST.read_text())
    if b4.get("status") != "PASS" or labels.get("status") != "PASS": raise RuntimeError("upstream canonical B4/label gate failed")
    schema = json.loads(B2_SCHEMA.read_text()); features = list(schema["feature_order"])
    train_all = pd.read_parquet(B4_TRAIN); test = pd.read_parquet(B4_TEST)
    for frame in [train_all, test]:
        frame["date"] = pd.to_datetime(frame.date).dt.strftime("%Y-%m-%d")
        frame[features] = frame[features].astype(float)
        frame[LABEL] = frame[LABEL].astype(float)
        if not np.isfinite(frame[features].to_numpy()).all(): raise RuntimeError("non-finite canonical feature")
    fit = train_all[train_all.b4_split.eq("fit_train")].sort_values(KEY, kind="mergesort").reset_index(drop=True)
    embargo = train_all[train_all.b4_split.eq("embargo_10_trade_dates")].sort_values(KEY, kind="mergesort").reset_index(drop=True)
    valid = train_all[train_all.b4_split.eq("validation")].sort_values(KEY, kind="mergesort").reset_index(drop=True)
    test = test.sort_values(KEY, kind="mergesort").reset_index(drop=True)
    if fit.date.min() != FIT_START or fit.date.max() != FIT_END or valid.date.min() != VALID_START or valid.date.max() != VALID_END: raise RuntimeError("split boundary mismatch")
    freeze = {"schema_version": "modelb.b5.canonical_label.run_freeze.v1", "status": "PREREGISTERED_BEFORE_TRAINING", "research_only": True, "diagnostic_only": True, "production_allowed": False, "label": LABEL, "feature_count": len(features), "feature_order_sha256": hashlib.sha256(json.dumps(features, separators=(",", ":")).encode()).hexdigest(), "model_config": CONFIG, "fit_train": [FIT_START, FIT_END], "embargo": [EMBARGO_START, EMBARGO_END], "validation": [VALID_START, VALID_END], "untouched_test": [TEST_START, TEST_END], "test_date_count": int(test.date.nunique()), "test_tail_excluded": True, "upstream": {"b4_manifest": sha256(B4_MANIFEST), "label_manifest": sha256(LABEL_MANIFEST), "b2_schema": sha256(B2_SCHEMA)}, "no_default_or_latest_switch": True, "no_replay": True}
    freeze_path.write_text(json.dumps(freeze, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    model = lgb.LGBMRanker(**CONFIG)
    model.fit(fit[features], fit[LABEL], group=fit.groupby("date", sort=True).size().tolist())
    model_path = OUT / "MODEL_B_CANONICAL_LGBM_RANKER.pkl"; joblib.dump(model, model_path, compress=("zlib", 3))
    predictions = []
    metric_rows = []
    for name, frame in [("fit_train", fit), ("validation", valid), ("test_2026", test)]:
        scores = model.predict(frame[features]); metric_rows.append(metrics(frame, scores, name)); predictions.append(frame[KEY + [LABEL]].assign(score=scores, score_rank=frame.assign(score=scores).groupby("date").score.rank(ascending=False, method="first").astype(int), split=name))
    pd.DataFrame(metric_rows).to_csv(OUT / "CANONICAL_B5_RANK_METRICS.csv", index=False)
    pd.concat(predictions, ignore_index=True).to_parquet(OUT / "CANONICAL_B5_RAW_SCORES.parquet", index=False)
    importance = pd.DataFrame({"feature": features, "importance_split": model.booster_.feature_importance(importance_type="split"), "importance_gain": model.booster_.feature_importance(importance_type="gain")}).sort_values("importance_gain", ascending=False)
    importance.to_csv(OUT / "CANONICAL_B5_FEATURE_IMPORTANCE.csv", index=False)
    manifest = {"schema_version": "modelb.b5.canonical_label.executor_manifest.v1", "status": "EXECUTED_AWAITING_INDEPENDENT_REVIEW", "research_only": True, "diagnostic_only": True, "production_allowed": False, "label": LABEL, "model_config": CONFIG, "feature_count": len(features), "split_metrics": metric_rows, "rows": {"fit": len(fit), "embargo": len(embargo), "validation": len(valid), "test": len(test)}, "test_dates": int(test.date.nunique()), "test_tail_excluded": True, "artifacts": {"freeze": str(freeze_path.relative_to(ROOT)), "model": str(model_path.relative_to(ROOT)), "metrics": str((OUT / "CANONICAL_B5_RANK_METRICS.csv").relative_to(ROOT)), "scores": str((OUT / "CANONICAL_B5_RAW_SCORES.parquet").relative_to(ROOT)), "importance": str((OUT / "CANONICAL_B5_FEATURE_IMPORTANCE.csv").relative_to(ROOT))}, "no_replay": True, "no_default_or_latest_switch": True, "no_production_write": True, "independent_review_required": True}
    (OUT / "B5_CANONICAL_EXECUTOR_MANIFEST.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=True, default=str) + "\n", encoding="utf-8")
    report = ["# B5 canonical label 执行报告", "", "仅用于隔离研究；未切换 baseline/latest/default。", "", f"状态：`{manifest['status']}`。", f"fit rows：`{len(fit)}`；validation rows：`{len(valid)}`；test rows：`{len(test)}`；test dates：`{test.date.nunique()}`。", "", "测试尾部 10 个日期没有 canonical 10 日标签，因此没有参与 test metric；该限制写入 freeze 和 manifest。", ""]
    (OUT / "B5_CANONICAL_EXECUTION_REPORT_CN.md").write_text("\n".join(report), encoding="utf-8")
    print(json.dumps({"status": manifest["status"], "output": str(OUT.relative_to(ROOT)), "metrics": metric_rows}, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
