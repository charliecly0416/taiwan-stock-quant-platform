#!/usr/bin/env python3
"""Train the frozen B19R2R LambdaRank model from Exact-50 development data."""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
from pathlib import Path
from typing import Any

import joblib
import lightgbm as lgb
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.metrics import ndcg_score


ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b19r2r_training_20260916"
FREEZE = RUN / "B19R2R_TRAINING_FREEZE.json"
AUTHORIZATION = RUN / "B19R2R_TRAINING_INDEPENDENT_AUTHORIZATION.json"
VALIDATOR = ROOT / "scripts/validate_modelb_b19r2r_training.py"
HISTORICAL = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b19r2r_historical_exact50_20260916/materialized_v2/HISTORICAL_EXACT50_TRAINING_SAMPLE.parquet"
HISTORICAL_MANIFEST = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b19r2r_historical_exact50_20260916/materialized_v2/HISTORICAL_EXACT50_MANIFEST.json"
HISTORICAL_REVIEW = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b19r2r_historical_exact50_20260916/HISTORICAL_EXACT50_V4_POST_MATERIALIZATION_INDEPENDENT_REVIEW.json"
R2R = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b19r2r_pretraining_materialization_20260916"
DEVELOPMENT_FEATURES = R2R / "FEATURE_ARTIFACT_78_RAW.parquet"
DEVELOPMENT_LABELS = R2R / "outcome_materialization_v1/development/DEVELOPMENT_EXACT50_LABELS.parquet"
SPLIT_PROTOCOL = R2R / "NESTED_WALK_FORWARD_SPLIT_AMENDMENT_03.csv"
B2_SCHEMA = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b2_canonical_pit_features_20260913/FEATURE_SCHEMA.json"
OUTPUT = RUN / "training_output_v1"
RELEVANCE_LABEL = "relevance_10d_top_heavy_canonical"
CONTINUOUS_LABEL = "future_excess_return_10d_canonical"
KEY = ["date", "instrument"]
EXPECTED_SOURCE_PATHS = {
    str(path.relative_to(ROOT))
    for path in (HISTORICAL, HISTORICAL_MANIFEST, DEVELOPMENT_FEATURES, DEVELOPMENT_LABELS, SPLIT_PROTOCOL, B2_SCHEMA)
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def rel(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT.resolve()))


def load_protocol(*, require_authorization: bool = True) -> dict[str, Any]:
    if not FREEZE.is_file():
        raise RuntimeError("training freeze is missing")
    freeze = json.loads(FREEZE.read_text(encoding="utf-8"))
    if freeze.get("status") != "CLOSED_BEFORE_TRAINING":
        raise RuntimeError("training freeze is not closed")
    for name, path in {"trainer": Path(__file__), "validator": VALIDATOR}.items():
        if freeze["implementation_bindings"][name]["sha256"] != sha256(path):
            raise RuntimeError(f"implementation binding mismatch: {name}")
    bindings = freeze.get("source_bindings", [])
    bound_paths = [item.get("path") for item in bindings if isinstance(item, dict)]
    if len(bound_paths) != len(EXPECTED_SOURCE_PATHS) or set(bound_paths) != EXPECTED_SOURCE_PATHS:
        raise RuntimeError("training source allowlist mismatch")
    for item in bindings:
        path = ROOT / item["path"]
        if not path.is_file() or sha256(path) != item["sha256"]:
            raise RuntimeError(f"training source binding mismatch: {item['path']}")
    review_binding = freeze.get("historical_post_review", {})
    if review_binding.get("sha256") != sha256(HISTORICAL_REVIEW):
        raise RuntimeError("historical post-review binding mismatch")
    if require_authorization:
        if not AUTHORIZATION.is_file():
            raise RuntimeError("training independent authorization is missing")
        authorization = json.loads(AUTHORIZATION.read_text(encoding="utf-8"))
        if (
            authorization.get("authorized") is not True
            or authorization.get("attempts_authorized") != 1
            or authorization.get("training_freeze_sha256") != sha256(FREEZE)
        ):
            raise RuntimeError("training is not independently authorized")
    return freeze


def candidate_configs() -> list[dict[str, Any]]:
    return [
        {
            "objective": "lambdarank", "metric": "ndcg", "boosting_type": "gbdt",
            "num_leaves": leaves, "learning_rate": rate, "n_estimators": estimators,
            "min_child_samples": children, "random_state": 42, "n_jobs": 2, "verbosity": -1,
        }
        for leaves, rate, estimators, children in itertools.product(
            [15, 31], [0.02, 0.03], [80, 120], [40, 80]
        )
    ]


def normalize_keys(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.copy()
    frame["date"] = frame.date.astype(str).str[:10]
    frame["instrument"] = frame.instrument.astype(str).str.upper()
    return frame


def load_development(features: list[str]) -> pd.DataFrame:
    keep = KEY + features + [CONTINUOUS_LABEL, RELEVANCE_LABEL]
    historical = normalize_keys(pd.read_parquet(HISTORICAL, columns=keep))
    if (
        len(historical) != 39350 or historical.date.nunique() != 787
        or historical.groupby("date").size().ne(50).any() or historical.duplicated(KEY).any()
    ):
        raise RuntimeError("historical Exact-50 shape failed")

    development_features = normalize_keys(pd.read_parquet(
        DEVELOPMENT_FEATURES,
        columns=KEY + ["signal_asof", "available_at", "feature_raw_complete_78"] + features,
    ))
    development_labels = normalize_keys(pd.read_parquet(
        DEVELOPMENT_LABELS,
        columns=KEY + [CONTINUOUS_LABEL, RELEVANCE_LABEL, "label_complete"],
    ))
    if (
        len(development_labels) != 2000 or development_labels.date.nunique() != 40
        or development_labels.groupby("date").size().ne(50).any() or development_labels.duplicated(KEY).any()
    ):
        raise RuntimeError("development Exact-50 label shape failed")
    development = development_labels.merge(development_features, on=KEY, how="left", validate="one_to_one")
    if len(development) != 2000 or development[features].isna().any().any():
        raise RuntimeError("development Exact-50 feature join failed")
    if not development.feature_raw_complete_78.all() or not development.label_complete.all():
        raise RuntimeError("development Exact-50 completeness failed")
    if not (
        development.signal_asof.astype(str).str[:10].eq(development.date).all()
        and development.available_at.astype(str).str[:10].le(development.date).all()
    ):
        raise RuntimeError("development PIT availability failed")
    development = development[keep].copy()

    data = pd.concat([historical, development], ignore_index=True)
    data = data.sort_values(KEY, kind="mergesort").reset_index(drop=True)
    if (
        len(data) != 41350 or data.date.nunique() != 827
        or data.groupby("date").size().ne(50).any() or data.duplicated(KEY).any()
        or data.date.min() != "2023-01-10" or data.date.max() != "2026-07-06"
    ):
        raise RuntimeError("combined development Exact-50 shape failed")
    if not np.isfinite(data[features + [CONTINUOUS_LABEL, RELEVANCE_LABEL]].to_numpy(float)).all():
        raise RuntimeError("combined development feature or label finiteness failed")
    if not set(data[RELEVANCE_LABEL].unique()).issubset({0, 1, 2, 3, 4}):
        raise RuntimeError("combined relevance domain failed")
    return data


def frame_between(data: pd.DataFrame, start: str | None, end: str) -> pd.DataFrame:
    selected = data[data.date.le(end) & (True if start is None else data.date.ge(start))].copy()
    return selected.sort_values(KEY, kind="mergesort").reset_index(drop=True)


def fit_model(frame: pd.DataFrame, features: list[str], config: dict[str, Any]) -> lgb.LGBMRanker:
    groups = frame.groupby("date", sort=True).size().tolist()
    if not groups or sum(groups) != len(frame) or set(groups) != {50}:
        raise RuntimeError("invalid Exact-50 LambdaRank groups")
    model = lgb.LGBMRanker(**config)
    model.fit(frame[features], frame[RELEVANCE_LABEL].astype(int), group=groups)
    return model


def rank_metrics(frame: pd.DataFrame, scores: np.ndarray) -> tuple[float, float]:
    scored = frame[KEY + [RELEVANCE_LABEL, CONTINUOUS_LABEL]].copy()
    scored["score"] = scores
    ndcg: list[float] = []
    rank_ic: list[float] = []
    for _, day in scored.groupby("date", sort=True):
        relevance = day[RELEVANCE_LABEL].to_numpy(float)
        continuous = day[CONTINUOUS_LABEL].to_numpy(float)
        prediction = day.score.to_numpy(float)
        ndcg.append(float(ndcg_score(relevance[None, :], prediction[None, :], k=10)))
        rho = spearmanr(prediction, continuous).statistic
        if not np.isfinite(rho):
            raise RuntimeError("nonfinite daily continuous-label RankIC")
        rank_ic.append(float(rho))
    if not ndcg or not rank_ic or not np.isfinite(ndcg + rank_ic).all():
        raise RuntimeError("nonfinite development metric")
    return float(np.mean(ndcg)), float(np.mean(rank_ic))


def select_candidate(rows: list[dict[str, Any]]) -> int:
    summary = pd.DataFrame(rows).groupby("candidate_id", as_index=False).agg(
        median_inner_ndcg10=("ndcg10", "median"),
        median_inner_rank_ic=("rank_ic_continuous", "median"),
    )
    best_ndcg = summary.median_inner_ndcg10.max()
    summary = summary[best_ndcg - summary.median_inner_ndcg10 <= 1e-12]
    best_ic = summary.median_inner_rank_ic.max()
    ids = set(summary[best_ic - summary.median_inner_rank_ic <= 1e-12].candidate_id.astype(int))
    configs = candidate_configs()
    return min(ids, key=lambda i: (
        configs[i]["num_leaves"], configs[i]["n_estimators"],
        configs[i]["learning_rate"], -configs[i]["min_child_samples"],
    ))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preflight-no-write", action="store_true")
    parser.add_argument("--train-frozen-model", action="store_true")
    args = parser.parse_args()
    if args.preflight_no_write == args.train_frozen_model:
        raise SystemExit("Select exactly one mode")
    if args.preflight_no_write:
        load_protocol(require_authorization=False)
        if OUTPUT.exists():
            raise RuntimeError("training output already exists")
        print(json.dumps({"status": "PASS_NO_WRITE", "training_output_absent": True}))
        return 0

    freeze = load_protocol()
    if OUTPUT.exists():
        raise RuntimeError("refusing to overwrite training output")
    OUTPUT.mkdir(parents=True, exist_ok=False)
    features = json.loads(B2_SCHEMA.read_text(encoding="utf-8"))["feature_order"]
    data = load_development(features)
    folds = freeze["folds"]
    configs = candidate_configs()
    inner_rows: list[dict[str, Any]] = []
    for fold_name in ("inner_1", "inner_2"):
        fold = folds[fold_name]
        train = frame_between(data, None, fold["train_end"])
        valid = frame_between(data, fold["validation_start"], fold["validation_end"])
        for candidate_id, config in enumerate(configs):
            model = fit_model(train, features, config)
            ndcg10, rank_ic = rank_metrics(valid, model.predict(valid[features]))
            inner_rows.append({
                "fold": fold_name, "candidate_id": candidate_id,
                "train_dates": train.date.nunique(), "validation_dates": valid.date.nunique(),
                "ndcg10": ndcg10, "rank_ic_continuous": rank_ic,
            })
    selected_id = select_candidate(inner_rows)
    selected = configs[selected_id]

    outer_rows: list[dict[str, Any]] = []
    for fold_name in ("outer_1", "outer_2"):
        fold = folds[fold_name]
        train = frame_between(data, None, fold["train_end"])
        valid = frame_between(data, fold["validation_start"], fold["validation_end"])
        model = fit_model(train, features, selected)
        ndcg10, rank_ic = rank_metrics(valid, model.predict(valid[features]))
        outer_rows.append({
            "fold": fold_name, "candidate_id": selected_id,
            "train_dates": train.date.nunique(), "validation_dates": valid.date.nunique(),
            "ndcg10": ndcg10, "rank_ic_continuous": rank_ic, "selection_effect": "NONE",
        })

    final_train = frame_between(data, None, freeze["final_refit_end"])
    model = fit_model(final_train, features, selected)
    inner_path = OUTPUT / "INNER_SELECTION_METRICS.csv"
    outer_path = OUTPUT / "OUTER_DEVELOPMENT_CHECKS.csv"
    importance_path = OUTPUT / "FEATURE_IMPORTANCE.csv"
    model_path = OUTPUT / "MODEL_B_B19R2R_LGBM_RANKER.pkl"
    pd.DataFrame(inner_rows).to_csv(inner_path, index=False)
    pd.DataFrame(outer_rows).to_csv(outer_path, index=False)
    joblib.dump(model, model_path, compress=("zlib", 3))
    probe = final_train.iloc[:50]
    loaded = joblib.load(model_path)
    if not np.array_equal(model.predict(probe[features]), loaded.predict(probe[features])):
        raise RuntimeError("model reload mismatch")
    pd.DataFrame({
        "feature": features,
        "split": model.booster_.feature_importance("split"),
        "gain": model.booster_.feature_importance("gain"),
    }).to_csv(importance_path, index=False)
    artifacts = {
        name: {"path": rel(path), "sha256": sha256(path), "bytes": path.stat().st_size}
        for name, path in {
            "model": model_path, "inner_metrics": inner_path,
            "outer_checks": outer_path, "feature_importance": importance_path,
        }.items()
    }
    manifest = {
        "schema_version": "modelb.b19r2r.training_manifest.v2",
        "status": "TRAINED_AWAITING_INDEPENDENT_REVIEW",
        "model_id": "modelb_b19r2r_lambdarank_exact50_78f_v2",
        "parent_weights_reused": False,
        "historical_rows": 39350, "development_rows": 2000,
        "combined_rows": 41350, "combined_dates": 827, "rows_each_date": 50,
        "selected_candidate_id": selected_id, "selected_config": selected,
        "fit_label": RELEVANCE_LABEL, "ndcg_label": RELEVANCE_LABEL,
        "rank_ic_label": CONTINUOUS_LABEL,
        "selection_source": "INNER_1_AND_INNER_2_ONLY", "outer_selection_effect": "NONE",
        "final_refit_end": freeze["final_refit_end"], "final_train_rows": len(final_train),
        "final_train_dates": final_train.date.nunique(), "feature_count": 78,
        "artifacts": artifacts,
        "confirmation_accessed": False, "embargo_accessed": False,
        "replay_performed": False, "baseline_or_latest_write_performed": False,
        "production_write_performed": False, "independent_review_required": True,
    }
    (OUTPUT / "TRAINING_MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=True) + "\n", encoding="utf-8"
    )
    print(json.dumps({
        "status": manifest["status"], "selected_candidate_id": selected_id,
        "model_sha256": artifacts["model"]["sha256"],
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
