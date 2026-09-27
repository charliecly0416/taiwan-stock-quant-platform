#!/usr/bin/env python3
"""Run an isolated, preregistered Model B retraining from canonical B4 samples."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import joblib
import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.metrics import ndcg_score

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b9_canonical_label_retrain_20260914"
B4 = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b4_canonical_label_samples_20260914"
B2_SCHEMA = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b2_canonical_pit_features_20260913/FEATURE_SCHEMA.json"
LABEL = "relevance_10d_top_heavy_canonical"
KEY = ["date", "instrument"]
CONFIG = {"objective": "lambdarank", "metric": "ndcg", "boosting_type": "gbdt", "num_leaves": 31,
          "learning_rate": 0.03, "n_estimators": 120, "min_child_samples": 40,
          "random_state": 42, "n_jobs": 2, "verbosity": -1}


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def split_metrics(frame: pd.DataFrame, scores: np.ndarray, split: str) -> dict[str, object]:
    work = frame[KEY + [LABEL]].copy()
    work["score"] = scores
    values = {10: [], 30: [], 50: []}
    for _, group in work.groupby("date", sort=True):
        y = group[LABEL].to_numpy(float)
        s = group["score"].to_numpy(float)
        for k in values:
            values[k].append(float(ndcg_score(y[None, :], s[None, :], k=min(k, len(group)))))
    return {"split": split, "rows": int(len(work)), "dates": int(work.date.nunique()),
            "ndcg_at_10": float(np.mean(values[10])), "ndcg_at_30": float(np.mean(values[30])),
            "ndcg_at_50": float(np.mean(values[50])), "audit_only": split == "test_2026"}


def main() -> int:
    if OUT.exists() and any(OUT.iterdir()):
        raise RuntimeError(f"refusing to overwrite non-empty output: {OUT}")
    OUT.mkdir(parents=True, exist_ok=True)
    b4_manifest = B4 / "B4_CANONICAL_EXECUTOR_MANIFEST.json"
    train_path = B4 / "B4_CANONICAL_TRAIN_SAMPLE.parquet"
    test_path = B4 / "B4_CANONICAL_TEST_SAMPLE.parquet"
    b4_meta = json.loads(b4_manifest.read_text(encoding="utf-8"))
    schema = json.loads(B2_SCHEMA.read_text(encoding="utf-8"))
    features = list(schema["feature_order"])
    if b4_meta.get("status") != "PASS" or b4_meta.get("production_allowed") is not False:
        raise RuntimeError("canonical B4 gate is not PASS/research-only")
    train_all = pd.read_parquet(train_path)
    test = pd.read_parquet(test_path)
    for frame in (train_all, test):
        frame["date"] = pd.to_datetime(frame["date"]).dt.strftime("%Y-%m-%d")
        frame[features] = frame[features].astype(float)
        frame[LABEL] = frame[LABEL].astype(float)
        if not np.isfinite(frame[features].to_numpy()).all() or not np.isfinite(frame[LABEL].to_numpy()).all():
            raise RuntimeError("non-finite feature or label")
    fit = train_all[train_all["b4_split"].eq("fit_train")].sort_values(KEY, kind="mergesort").reset_index(drop=True)
    valid = train_all[train_all["b4_split"].eq("validation")].sort_values(KEY, kind="mergesort").reset_index(drop=True)
    test = test.sort_values(KEY, kind="mergesort").reset_index(drop=True)
    expected = {"fit_min": "2023-01-10", "fit_max": "2024-12-17", "valid_min": "2025-01-02", "valid_max": "2025-12-31", "test_min": "2026-01-02", "test_max": "2026-04-22"}
    actual = {"fit_min": fit.date.min(), "fit_max": fit.date.max(), "valid_min": valid.date.min(), "valid_max": valid.date.max(), "test_min": test.date.min(), "test_max": test.date.max()}
    if actual != expected:
        raise RuntimeError(f"split boundary mismatch: {actual}")
    freeze = {"schema_version": "modelb.b9.canonical_label_retrain.freeze.v1", "status": "PREREGISTERED_BEFORE_TRAINING",
              "research_only": True, "diagnostic_only": True, "production_allowed": False, "label": LABEL,
              "feature_count": len(features), "feature_order_sha256": hashlib.sha256(json.dumps(features, separators=(",", ":")).encode()).hexdigest(),
              "model_config": CONFIG, "fit_train": [expected["fit_min"], expected["fit_max"]],
              "validation": [expected["valid_min"], expected["valid_max"]], "untouched_test": [expected["test_min"], expected["test_max"]],
              "test_tail_excluded": True, "input_universe": "canonical B4 complete-case rows; TW7769 excluded upstream",
              "upstream": {"b4_manifest_sha256": sha(b4_manifest), "b2_schema_sha256": sha(B2_SCHEMA)},
              "no_default_or_latest_switch": True, "no_production_write": True}
    freeze_path = OUT / "B9_CANONICAL_RETRAIN_RUN_FREEZE.json"
    freeze_path.write_text(json.dumps(freeze, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
    model = lgb.LGBMRanker(**CONFIG)
    model.fit(fit[features], fit[LABEL], group=fit.groupby("date", sort=True).size().tolist())
    model_path = OUT / "MODEL_B_CANONICAL_LGBM_RANKER.pkl"
    joblib.dump(model, model_path, compress=("zlib", 3))
    metrics = []
    scored = []
    for name, frame in (("fit_train", fit), ("validation", valid), ("test_2026", test)):
        scores = model.predict(frame[features])
        metrics.append(split_metrics(frame, scores, name))
        out = frame[KEY + [LABEL]].copy(); out["score"] = scores
        out["score_rank"] = out.groupby("date")["score"].rank(ascending=False, method="first").astype(int)
        out["split"] = name; scored.append(out)
    metrics_path = OUT / "B9_RANK_METRICS.csv"
    pd.DataFrame(metrics).to_csv(metrics_path, index=False)
    scores_path = OUT / "B9_RAW_SCORES.parquet"
    pd.concat(scored, ignore_index=True).to_parquet(scores_path, index=False)
    importance_path = OUT / "B9_FEATURE_IMPORTANCE.csv"
    pd.DataFrame({"feature": features, "importance_split": model.booster_.feature_importance(importance_type="split"),
                  "importance_gain": model.booster_.feature_importance(importance_type="gain")}).sort_values("importance_gain", ascending=False).to_csv(importance_path, index=False)
    loaded = joblib.load(model_path)
    load_probe = loaded.predict(test[features][: min(10, len(test))])
    if not np.allclose(load_probe, model.predict(test[features][: min(10, len(test))])):
        raise RuntimeError("saved model reload prediction mismatch")
    manifest = {"schema_version": "modelb.b9.canonical_label_retrain.executor_manifest.v1", "status": "EXECUTED_AWAITING_INDEPENDENT_REVIEW",
                "research_only": True, "diagnostic_only": True, "production_allowed": False, "feature_count": len(features), "label": LABEL,
                "model_config": CONFIG, "rows": {"fit": len(fit), "validation": len(valid), "test": len(test)}, "dates": {"fit": int(fit.date.nunique()), "validation": int(valid.date.nunique()), "test": int(test.date.nunique())},
                "split_metrics": metrics, "excluded_symbols": ["TW7769", "TW6919"], "artifacts": {"freeze": str(freeze_path.relative_to(ROOT)), "model": str(model_path.relative_to(ROOT)), "metrics": str(metrics_path.relative_to(ROOT)), "scores": str(scores_path.relative_to(ROOT)), "importance": str(importance_path.relative_to(ROOT))},
                "model_reload_verified": True, "no_replay": True, "no_default_or_latest_switch": True, "no_production_write": True, "independent_review_required": True}
    manifest_path = OUT / "B9_CANONICAL_RETRAIN_EXECUTOR_MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=True, indent=2, default=str) + "\n", encoding="utf-8")
    report = ["# B9 canonical label retrain 执行报告", "", "本次为隔离研究重训，未覆盖 B5，未切换 baseline/latest/default。", "", f"状态：`{manifest['status']}`。", f"fit：{len(fit)} 行/{fit.date.nunique()} 日；validation：{len(valid)} 行/{valid.date.nunique()} 日；test：{len(test)} 行/{test.date.nunique()} 日。", "训练仅使用 fit_train；embargo 和 validation 未用于拟合。", "B4 已排除 TW7769（以及结构性不适用的 TW6919）；没有补造标签或中性填充。", "保存模型重新加载并复预测一致。", ""]
    (OUT / "B9_CANONICAL_RETRAIN_EXECUTION_REPORT_CN.md").write_text("\n".join(report), encoding="utf-8")
    print(json.dumps({"status": manifest["status"], "output": str(OUT.relative_to(ROOT)), "metrics": metrics}, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
