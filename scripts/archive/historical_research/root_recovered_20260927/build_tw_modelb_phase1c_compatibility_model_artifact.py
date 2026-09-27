#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import pickle
from datetime import datetime, timezone
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "data_tw/experiments/ltr_rerank_regime_turnover/phase1_ltr_baseline"
SAMPLE = SOURCE_DIR / "phase1_ltr_samples.csv"
SCHEMA = SOURCE_DIR / "phase1_sample_schema.json"
REFERENCE = ROOT / "data_tw/experiments/ltr_rerank_regime_turnover/phase3a0_frozen_phase1c_scores/phase3a0_frozen_phase1c_row_scores.csv"
OUT = ROOT / "data_tw/experiments/model_b_compatibility_daily_shadow/model_artifact_phase1c_20260905"
MODEL = OUT / "phase1c_head10_all_l31_model.pkl"
SCORE = "score_head10_all_l31_alpha0.7_top50_only"
TOLERANCE = 1e-12

IDENTITY = {
    "candidate_id": "head10_all_l31_alpha0.7_top50_only",
    "model_id": "head10_all_l31",
    "model_family": "lightgbm_lambdarank",
    "objective": "lambdarank",
    "metric": "ndcg",
    "num_leaves": 31,
    "learning_rate": 0.03,
    "n_estimators": 120,
    "min_child_samples": 40,
    "random_state": 42,
    "n_jobs": 2,
    "blend_alpha": 0.7,
    "preserve_scope": "top50_only",
    "training_label": "relevance_10d_top_heavy",
}


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, default=str) + "\n", encoding="utf-8")


def top_heavy_label(rank: pd.Series) -> np.ndarray:
    values = rank.fillna(0)
    return np.select([values >= 0.90, values >= 0.80, values >= 0.70, values >= 0.50], [4, 3, 2, 1], default=0).astype(int)


def group_sizes(frame: pd.DataFrame) -> list[int]:
    return frame.sort_values(["date", "instrument"]).groupby("date").size().astype(int).tolist()


def main() -> int:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    features = list(schema["input_columns"])
    raw = pd.read_csv(SAMPLE, parse_dates=["date"])
    complete = raw[raw["sample_complete"] == True].copy()  # noqa: E712
    complete = complete.sort_values(["date", "instrument"]).reset_index(drop=True)
    medians = (
        complete[complete["split"] == "train"][features]
        .replace([np.inf, -np.inf], np.nan)
        .median(numeric_only=True)
        .fillna(0.0)
    )
    complete[features] = complete[features].replace([np.inf, -np.inf], np.nan).fillna(medians).fillna(0.0)
    complete[IDENTITY["training_label"]] = top_heavy_label(complete["future_excess_return_rank_10d"])
    train = complete[complete["split"] == "train"].sort_values(["date", "instrument"])
    valid = complete[complete["split"] == "validation"].sort_values(["date", "instrument"])

    model = lgb.LGBMRanker(
        objective=IDENTITY["objective"],
        metric=IDENTITY["metric"],
        boosting_type="gbdt",
        n_estimators=IDENTITY["n_estimators"],
        learning_rate=IDENTITY["learning_rate"],
        num_leaves=IDENTITY["num_leaves"],
        min_child_samples=IDENTITY["min_child_samples"],
        random_state=IDENTITY["random_state"],
        n_jobs=IDENTITY["n_jobs"],
        verbose=-1,
    )
    model.fit(
        train[features],
        train[IDENTITY["training_label"]],
        group=group_sizes(train),
        eval_set=[(valid[features], valid[IDENTITY["training_label"]])],
        eval_group=[group_sizes(valid)],
        eval_at=[10, 30, 50],
    )

    produced = complete[["date", "instrument", "qlib_score_raw", "qlib_rank"]].copy()
    produced["phase1c_model_score_head10_all_l31"] = model.predict(complete[features])
    produced["qlib_pct"] = produced.groupby("date")["qlib_score_raw"].rank(pct=True)
    produced["phase1c_model_pct"] = produced.groupby("date")["phase1c_model_score_head10_all_l31"].rank(pct=True)
    blend = 0.7 * produced["qlib_pct"] + 0.3 * produced["phase1c_model_pct"]
    produced[SCORE] = blend.where(produced["qlib_rank"] <= 50, -1.0 + produced["qlib_pct"] * 0.000001)
    produced["date"] = produced["date"].dt.strftime("%Y-%m-%d")

    reference = pd.read_csv(
        REFERENCE,
        usecols=["date", "instrument", "phase1c_model_score_head10_all_l31", "qlib_pct", "phase1c_model_pct", SCORE],
    )
    joined = reference.merge(produced, on=["date", "instrument"], suffixes=("_reference", "_produced"), validate="one_to_one")
    audit_rows = []
    for column in ["phase1c_model_score_head10_all_l31", "qlib_pct", "phase1c_model_pct", SCORE]:
        diff = (
            pd.to_numeric(joined[f"{column}_reference"], errors="coerce")
            - pd.to_numeric(joined[f"{column}_produced"], errors="coerce")
        ).abs()
        audit_rows.append(
            {
                "field": column,
                "rows": int(diff.shape[0]),
                "max_abs_diff": float(diff.max()),
                "mean_abs_diff": float(diff.mean()),
                "tolerance": TOLERANCE,
                "pass": bool(diff.max() <= TOLERANCE),
            }
        )
    reproduction_ok = len(joined) == len(reference) == len(produced) and all(row["pass"] for row in audit_rows)

    OUT.mkdir(parents=True, exist_ok=True)
    with MODEL.open("wb") as handle:
        pickle.dump(model, handle, protocol=pickle.HIGHEST_PROTOCOL)
    pd.DataFrame(audit_rows).to_csv(OUT / "score_reproduction_audit.csv", index=False)
    write_json(OUT / "training_medians.json", {feature: float(medians.get(feature, 0.0)) for feature in features})
    write_json(
        OUT / "model_contract.json",
        {
            "created_at": now(),
            "identity": IDENTITY,
            "features": features,
            "feature_count": len(features),
            "source_sample": str(SAMPLE.relative_to(ROOT)),
            "source_schema": str(SCHEMA.relative_to(ROOT)),
            "reference_scores": str(REFERENCE.relative_to(ROOT)),
            "training_rows": int(train.shape[0]),
            "validation_rows": int(valid.shape[0]),
            "all_complete_rows": int(complete.shape[0]),
            "historical_labels_used_for_model_reconstruction_only": True,
            "labels_allowed_in_daily_inference": False,
            "legacy_compatible": True,
            "strict_pit_oos": False,
            "production_allowed": False,
        },
    )
    artifact_files = [MODEL, OUT / "score_reproduction_audit.csv", OUT / "training_medians.json", OUT / "model_contract.json"]
    write_json(OUT / "checksum_manifest.json", {str(path.relative_to(ROOT)): sha256(path) for path in artifact_files})
    gate = {
        "created_at": now(),
        "phase": "MBCDS1_EXACT_PHASE1C_MODEL_MATERIALIZATION",
        "ok": reproduction_ok,
        "decision": "READY_FOR_MBCDS2_INPUT_PREFLIGHT" if reproduction_ok else "STOP_MODEL_REPRODUCTION_FAILED",
        "reference_rows": int(reference.shape[0]),
        "produced_rows": int(produced.shape[0]),
        "joined_rows": int(joined.shape[0]),
        "score_reproduction_pass": reproduction_ok,
        "max_abs_diff": max(row["max_abs_diff"] for row in audit_rows),
        "model_sha256": sha256(MODEL),
        "no_daily_scoring": True,
        "no_production_latest_cron_provider_frontend_write": True,
        "strict_pit_oos": False,
        "production_allowed": False,
    }
    write_json(OUT / "gate_summary.json", gate)
    print(json.dumps(gate, ensure_ascii=False, indent=2))
    return 0 if reproduction_ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
