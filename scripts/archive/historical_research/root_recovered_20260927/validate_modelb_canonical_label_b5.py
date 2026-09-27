#!/usr/bin/env python3
"""Independent readonly validator for the canonical-label B5 run."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b5_canonical_label_lgbm_20260914"
B4 = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b4_canonical_label_samples_20260914"
SCHEMA = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b2_canonical_pit_features_20260913/FEATURE_SCHEMA.json"
LABEL = "relevance_10d_top_heavy_canonical"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    schema = json.loads(SCHEMA.read_text()); features = schema["feature_order"]
    train = pd.read_parquet(B4 / "B4_CANONICAL_TRAIN_SAMPLE.parquet")
    test = pd.read_parquet(B4 / "B4_CANONICAL_TEST_SAMPLE.parquet")
    fit = train[train.b4_split.eq("fit_train")].sort_values(["date", "instrument"], kind="mergesort").reset_index(drop=True)
    valid = train[train.b4_split.eq("validation")].sort_values(["date", "instrument"], kind="mergesort").reset_index(drop=True)
    test = test.sort_values(["date", "instrument"], kind="mergesort").reset_index(drop=True)
    model = joblib.load(RUN / "MODEL_B_CANONICAL_LGBM_RANKER.pkl")
    checks = {
        "model_type": type(model).__name__ == "LGBMRanker",
        "feature_count": int(model.n_features_in_) == 78,
        "objective": model.get_params().get("objective") == "lambdarank",
        "fit_split_only": fit.date.min() == "2023-01-10" and fit.date.max() == "2024-12-17" and len(fit) == 65741,
        "validation_boundary": valid.date.min() == "2025-01-02" and valid.date.max() == "2025-12-31" and len(valid) == 34939,
        "test_tail_explicitly_excluded": test.date.min() == "2026-01-02" and test.date.max() == "2026-04-22" and test.date.nunique() == 69 and len(test) == 10212,
        "unique_keys": not pd.concat([fit, valid, test]).duplicated(["date", "instrument"]).any(),
        "finite_features": bool(np.isfinite(pd.concat([fit, valid, test])[features].to_numpy(float)).all()),
        "finite_labels": bool(pd.concat([fit, valid, test])[LABEL].notna().all()),
    }
    predictions = {"fit_train": model.predict(fit[features]), "validation": model.predict(valid[features]), "test_2026": model.predict(test[features])}
    saved = pd.read_parquet(RUN / "CANONICAL_B5_RAW_SCORES.parquet")
    score_errors = {}
    for split, frame, pred in [("fit_train", fit, predictions["fit_train"]), ("validation", valid, predictions["validation"]), ("test_2026", test, predictions["test_2026"])]:
        existing = saved[saved.split.eq(split)].sort_values(["date", "instrument"], kind="mergesort").score.to_numpy(float)
        score_errors[split] = float(np.max(np.abs(existing - pred))) if len(existing) == len(pred) else None
    checks["saved_score_replay_exact"] = all(v is not None and v == 0.0 for v in score_errors.values())
    artifacts = [RUN / "B5_CANONICAL_RUN_FREEZE.json", RUN / "MODEL_B_CANONICAL_LGBM_RANKER.pkl", RUN / "CANONICAL_B5_RANK_METRICS.csv", RUN / "CANONICAL_B5_RAW_SCORES.parquet", RUN / "CANONICAL_B5_FEATURE_IMPORTANCE.csv", RUN / "B5_CANONICAL_EXECUTOR_MANIFEST.json"]
    hashes = {str(p.relative_to(ROOT)): {"sha256": sha256(p), "bytes": p.stat().st_size} for p in artifacts}
    review = {"schema_version": "modelb.b5.canonical_label.independent_review.v1", "verdict": "PASS_WITH_CONDITIONS" if all(checks.values()) else "FAIL", "checks": checks, "score_max_abs_error": score_errors, "artifact_hashes": hashes, "research_only": True, "diagnostic_only": True, "production_allowed": False, "conditions": ["test covers 69/79 historical test dates; tail 10 dates lack canonical TWII t+10 and are excluded", "verbosity=-1 is logging-only and does not change ranking parameters", "not approved for baseline/default/latest/production"]}
    (RUN / "B5_CANONICAL_INDEPENDENT_REVIEW.json").write_text(json.dumps(review, indent=2, ensure_ascii=True, default=str) + "\n", encoding="utf-8")
    lines = ["# B5 canonical label 独立审查", "", f"结论：`{review['verdict']}`。", "", *[f"- {k}: `{v}`" for k, v in checks.items()], "", "条件：测试只覆盖 69/79 个日期；canonical TWII 的 test+10 末端窗口仍未补齐。该模型仍是 diagnostic-only，不进入 baseline/default/latest。", ""]
    (RUN / "B5_CANONICAL_INDEPENDENT_REVIEW_CN.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"verdict": review["verdict"], "checks": checks, "score_max_abs_error": score_errors}, ensure_ascii=True))
    return 0 if review["verdict"] != "FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
