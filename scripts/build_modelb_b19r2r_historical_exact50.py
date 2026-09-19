#!/usr/bin/env python3
"""Materialize the V4 historical deterministic exact-50 Model B sample."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b19r2r_historical_exact50_20260916"
FREEZE = RUN / "HISTORICAL_EXACT50_FREEZE_V4.json"
AUTH = RUN / "HISTORICAL_EXACT50_INDEPENDENT_AUTHORIZATION_V4.json"
VALIDATOR = ROOT / "scripts/validate_modelb_b19r2r_historical_exact50.py"
FAILED_V3_RUN = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b19r2r_historical_exact50_20260916"
FAILED_V3_EVIDENCE = FAILED_V3_RUN / "HISTORICAL_EXACT50_V3_MATERIALIZATION_FAILURE.json"
FAILED_V3_OUTPUT = FAILED_V3_RUN / "materialized_v1"
B4 = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b4_canonical_label_samples_20260914"
B4_TRAIN = B4 / "B4_CANONICAL_TRAIN_SAMPLE.parquet"
B4_TEST = B4 / "B4_CANONICAL_TEST_SAMPLE.parquet"
B4_MANIFEST = B4 / "B4_CANONICAL_EXECUTOR_MANIFEST.json"
B3_DIR = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b3_frozen_modela_oos_score_20260913"
B3 = B3_DIR / "MODEL_A_FROZEN_OOS_SCORE.parquet"
B3_MANIFEST = B3_DIR / "B3_MODEL_A_OOS_MANIFEST.json"
LABELS = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_canonical_labels_20260914/CANONICAL_LABEL_ARTIFACT.csv"
B18_KEYS = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b18r2_historical_pit_paired_replay_20260916/signals.csv"
SCHEMA = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b2_canonical_pit_features_20260913/FEATURE_SCHEMA.json"
OUTPUT = RUN / "materialized_v2"
KEY = ["date", "instrument"]
EXCLUDED = {"TW6919", "TW7769"}
FEATURE_ORDER_SHA256 = "2e0c169fb7762240aa20bc31ea53ac21b6a69db99dabea2f897421121105f2ca"
FAILED_V3_EVIDENCE_SHA256 = "b06be354bdbbd41b428846f66e18e1731ed0473f8a0290132db05141869caeb2"
MODEL_A_STACKING_FEATURES = [
    "qlib_score_raw", "qlib_rank", "qlib_score_percentile_by_date", "qlib_score_zscore_by_date",
    "rank_change_1d", "rank_change_3d", "rank_change_5d", "top10_flag", "top30_flag", "top50_flag",
    "top30_streak", "top50_streak",
]
EXPECTED_SOURCE_PATHS = {
    str(path.relative_to(ROOT))
    for path in (B4_TRAIN, B4_TEST, B4_MANIFEST, B3, B3_MANIFEST, LABELS, B18_KEYS, SCHEMA)
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def rel(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT.resolve()))


def key_hash(frame: pd.DataFrame) -> str:
    text = "".join(f"{row.date}|{row.instrument}\n" for row in frame.sort_values(KEY).itertuples())
    return hashlib.sha256(text.encode("ascii")).hexdigest()


def validate_protocol(*, require_authorization: bool = True) -> dict[str, Any]:
    if not FREEZE.is_file():
        raise RuntimeError("V4 freeze missing")
    freeze = json.loads(FREEZE.read_text(encoding="utf-8"))
    if freeze.get("status") != "CLOSED_AFTER_V3_DIAGNOSIS_BEFORE_V4_MATERIALIZATION":
        raise RuntimeError("V4 freeze status mismatch")
    feature_contract = freeze.get("feature_contract", {})
    if (
        feature_contract.get("feature_count") != 78
        or feature_contract.get("feature_order_sha256") != FEATURE_ORDER_SHA256
        or feature_contract.get("model_a_derived_stacking_features") != MODEL_A_STACKING_FEATURES
        or feature_contract.get("non_model_a_feature_count") != 66
    ):
        raise RuntimeError("feature order binding mismatch")
    for name, path in {"builder": Path(__file__), "validator": VALIDATOR}.items():
        if freeze["implementation_bindings"][name]["sha256"] != sha256(path):
            raise RuntimeError(f"implementation binding mismatch: {name}")
    source_bindings = freeze.get("source_bindings")
    if not isinstance(source_bindings, list):
        raise RuntimeError("source bindings missing")
    bound_paths = [item.get("path") for item in source_bindings if isinstance(item, dict)]
    if len(bound_paths) != len(EXPECTED_SOURCE_PATHS) or set(bound_paths) != EXPECTED_SOURCE_PATHS:
        raise RuntimeError("source bindings do not exactly match the V4 allowlist")
    for item in source_bindings:
        path = ROOT / item["path"]
        if not path.is_file() or sha256(path) != item["sha256"]:
            raise RuntimeError(f"source binding mismatch: {item['path']}")
    if not FAILED_V3_EVIDENCE.is_file() or sha256(FAILED_V3_EVIDENCE) != FAILED_V3_EVIDENCE_SHA256:
        raise RuntimeError("V3 failure evidence mismatch")
    if not FAILED_V3_OUTPUT.is_dir() or any(FAILED_V3_OUTPUT.iterdir()):
        raise RuntimeError("V3 failed footprint was removed or modified")
    if require_authorization:
        if not AUTH.is_file():
            raise RuntimeError("V4 independent authorization missing")
        auth = json.loads(AUTH.read_text(encoding="utf-8"))
        if auth.get("authorized") is not True or auth.get("attempts_authorized") != 1 or auth.get("freeze_sha256") != sha256(FREEZE):
            raise RuntimeError("V4 materialization not independently authorized")
    return freeze


def normalize_keys(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.copy()
    frame["date"] = frame.date.astype(str).str[:10]
    frame["instrument"] = frame.instrument.astype(str).str.upper()
    return frame


def materialize() -> dict[str, Any]:
    freeze = validate_protocol()
    if OUTPUT.exists():
        raise RuntimeError("refusing to overwrite V4 historical exact50 output")
    OUTPUT.mkdir(parents=True, exist_ok=False)

    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    features = schema["feature_order"]
    feature_order_sha = hashlib.sha256(json.dumps(features, separators=(",", ":")).encode()).hexdigest()
    if (
        len(features) != 78
        or len(set(features)) != 78
        or feature_order_sha != FEATURE_ORDER_SHA256
        or features[:12] != MODEL_A_STACKING_FEATURES
    ):
        raise RuntimeError("78F feature order or qlib_rank multiplicity failed")
    b4_manifest = json.loads(B4_MANIFEST.read_text(encoding="utf-8"))
    if (
        b4_manifest.get("status") != "PASS"
        or b4_manifest.get("feature_order_sha256") != FEATURE_ORDER_SHA256
        or b4_manifest.get("rank_universe") != "B2 raw unique (date,instrument) key set; rank denominator is frozen before primary feature filtering"
    ):
        raise RuntimeError("B4 rank-feature semantics mismatch")
    b3_manifest = json.loads(B3_MANIFEST.read_text(encoding="utf-8"))
    if (
        b3_manifest.get("status") != "PASS"
        or b3_manifest.get("rows") != 119862
        or b3_manifest.get("dates") != 802
        or b3_manifest.get("model_a", {}).get("source_score_repackaged_only") is not True
    ):
        raise RuntimeError("B3 full-cross-section semantics mismatch")

    b4 = normalize_keys(pd.concat([pd.read_parquet(B4_TRAIN), pd.read_parquet(B4_TEST)], ignore_index=True))
    b4 = b4[b4.date.between("2023-01-10", "2026-04-22")].copy()
    if b4.duplicated(KEY).any() or not b4.feature_raw_complete_78.all() or not b4.label_complete.all():
        raise RuntimeError("B4 canonical sample completeness failed")
    finite = np.isfinite(b4[features].to_numpy(float)).all(axis=1)
    eligible = b4[finite & ~b4.instrument.isin(EXCLUDED)].copy()
    b4_rank = eligible.qlib_rank.to_numpy(float)
    if not np.isfinite(b4_rank).all() or (b4_rank <= 0).any() or not np.equal(b4_rank, np.floor(b4_rank)).all():
        raise RuntimeError("B4 qlib_rank feature domain failed")

    b3 = normalize_keys(pd.read_parquet(B3, columns=KEY + ["raw_score", "qlib_rank", "dynamic_qlib_rank"]))
    b3 = b3.rename(columns={"raw_score": "selection_raw_score_b3", "qlib_rank": "full_qlib_rank"})
    eligible = eligible.merge(b3, on=KEY, how="left", validate="one_to_one")
    b3_score = eligible.selection_raw_score_b3.to_numpy(float)
    b4_score = eligible.qlib_score_raw.to_numpy(float)
    if not np.isfinite(b3_score).all() or not np.isfinite(b4_score).all():
        raise RuntimeError("B3/B4 Model A score completeness failed")
    score_diff = np.abs(b4_score - b3_score)
    score_mismatch = b4_score.view(np.uint64) != b3_score.view(np.uint64)
    mismatch_rows = eligible.loc[score_mismatch, KEY + ["qlib_score_raw", "selection_raw_score_b3"]]
    if int(score_mismatch.sum()) != 1:
        raise RuntimeError("B3/B4 frozen score tolerance contract failed")
    mismatch = mismatch_rows.iloc[0]
    if [mismatch.date, mismatch.instrument] != ["2026-03-04", "TW2324"]:
        raise RuntimeError("B3/B4 frozen score mismatch key drifted")
    if np.nextafter(float(mismatch.selection_raw_score_b3), float(mismatch.qlib_score_raw)) != float(mismatch.qlib_score_raw):
        raise RuntimeError("B3/B4 frozen score mismatch is not exactly one ULP")

    dynamic_rank = eligible.dynamic_qlib_rank.to_numpy(float)
    if not np.array_equal(b4_rank, dynamic_rank):
        raise RuntimeError("B4 qlib_rank does not match B3 dynamic_qlib_rank")
    b3_rank = eligible.full_qlib_rank.to_numpy(float)
    if not np.isfinite(b3_rank).all() or (b3_rank <= 0).any() or not np.equal(b3_rank, np.floor(b3_rank)).all():
        raise RuntimeError("B3 full_qlib_rank domain failed")
    rank_mismatch = b3_rank != b4_rank
    rank_delta = b3_rank[rank_mismatch] - b4_rank[rank_mismatch]
    if int(rank_mismatch.sum()) != 33379 or eligible.loc[rank_mismatch, "date"].nunique() != 367 or not np.equal(rank_delta, 1.0).all():
        raise RuntimeError("B3/B4 distinct rank-semantics diagnostic drifted")

    selected: list[pd.DataFrame] = []
    audit: list[dict[str, Any]] = []
    selected_rank_mismatches = 0
    selected_score_mismatches = 0
    for day, group in eligible.groupby("date", sort=True):
        b3_order = group.sort_values(["selection_raw_score_b3", "instrument"], ascending=[False, True], kind="mergesort")
        b4_order = group.sort_values(["qlib_score_raw", "instrument"], ascending=[False, True], kind="mergesort")
        if b3_order.instrument.tolist() != b4_order.instrument.tolist():
            raise RuntimeError(f"B3/B4 daily score ordering parity failed on {day}")
        pick = b3_order.head(50).copy()
        if len(pick) != 50:
            raise RuntimeError(f"cannot form exact50 on {day}")
        pick["candidate_rank"] = np.arange(1, 51)
        selected_rank_mismatches += int((pick.full_qlib_rank.to_numpy(float) != pick.qlib_rank.to_numpy(float)).sum())
        selected_score_mismatches += int((pick.selection_raw_score_b3.to_numpy(float).view(np.uint64) != pick.qlib_score_raw.to_numpy(float).view(np.uint64)).sum())
        selected.append(pick)
        audit.append({
            "date": day,
            "eligible_rows": len(group),
            "selected_rows": len(pick),
            "score_order_parity": True,
            "excluded_symbol_selected": bool(pick.instrument.isin(EXCLUDED).any()),
            "all_78_finite": True,
            "key_sha256": key_hash(pick),
        })
    exact50 = pd.concat(selected, ignore_index=True)
    if exact50.date.nunique() != 787 or len(exact50) != 39350 or exact50.groupby("date").size().ne(50).any():
        raise RuntimeError("historical exact50 shape mismatch")
    if selected_rank_mismatches != 5832 or selected_score_mismatches != 0:
        raise RuntimeError("selected rank/score diagnostic mismatch")

    labels = normalize_keys(pd.read_csv(
        LABELS,
        usecols=KEY + ["future_excess_return_10d_canonical", "relevance_10d_top_heavy_canonical", "label_complete_10d_canonical"],
    ))
    exact50 = exact50.merge(labels, on=KEY, how="left", validate="one_to_one", suffixes=("_b4", ""))
    if not exact50.label_complete_10d_canonical.all() or not np.isfinite(exact50.future_excess_return_10d_canonical.to_numpy(float)).all():
        raise RuntimeError("canonical continuous label join failed")
    if not np.array_equal(exact50.relevance_10d_top_heavy_canonical_b4.to_numpy(float), exact50.relevance_10d_top_heavy_canonical.to_numpy(float)):
        raise RuntimeError("canonical relevance parity failed")
    if not set(exact50.relevance_10d_top_heavy_canonical.unique()).issubset({0, 1, 2, 3, 4}):
        raise RuntimeError("canonical relevance value domain failed")

    b18 = normalize_keys(pd.read_csv(B18_KEYS, usecols=KEY))
    if b18.duplicated(KEY).any() or b18.date.nunique() != 321 or len(b18) != 16050 or b18.groupby("date").size().ne(50).any():
        raise RuntimeError("B18 comparison key contract failed")
    overlap = exact50[exact50.date.between("2025-01-02", "2026-04-22")][KEY]
    b18_overlap = b18[b18.date.between("2025-01-02", "2026-04-22")]
    overlap_hash = key_hash(overlap)
    if (
        overlap.date.nunique() != 311
        or len(overlap) != 15550
        or b18_overlap.date.nunique() != 311
        or len(b18_overlap) != 15550
        or b18_overlap.groupby("date").size().ne(50).any()
        or overlap_hash != key_hash(b18_overlap)
        or overlap_hash != "b4c5de21d8cc382297b3eb30c4e671ba0116e3973f2ab1d5f54a3f77676344a3"
    ):
        raise RuntimeError("B18 overlap exact50 key parity failed")

    keep = KEY + ["b4_split", "candidate_rank"] + features + [
        "selection_raw_score_b3",
        "full_qlib_rank",
        "future_excess_return_10d_canonical",
        "relevance_10d_top_heavy_canonical",
    ]
    if len(keep) != len(set(keep)):
        raise RuntimeError("duplicate output column contract")
    output = exact50[keep].sort_values(["date", "candidate_rank", "instrument"], kind="mergesort")
    sample_path = OUTPUT / "HISTORICAL_EXACT50_TRAINING_SAMPLE.parquet"
    keys_path = OUTPUT / "HISTORICAL_EXACT50_KEYSETS.csv"
    audit_path = OUTPUT / "HISTORICAL_EXACT50_AUDIT.csv"
    output.to_parquet(sample_path, index=False)
    output[KEY + ["candidate_rank", "qlib_rank", "full_qlib_rank"]].to_csv(keys_path, index=False)
    pd.DataFrame(audit).to_csv(audit_path, index=False)
    manifest = {
        "schema_version": "modelb.b19r2r.historical_exact50.v4",
        "status": "PASS_AWAITING_INDEPENDENT_REVIEW",
        "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "rows": 39350,
        "dates": 787,
        "rows_each_date": 50,
        "feature_count": 78,
        "feature_order_sha256": freeze["feature_contract"]["feature_order_sha256"],
        "output_columns_unique": True,
        "b4_rank_feature_preserved": True,
        "model_a_stacking_feature_count": 12,
        "non_model_a_feature_count": 66,
        "b4_rank_matches_b3_dynamic_rank": True,
        "b3_full_rank_provenance_field": "full_qlib_rank",
        "raw_score_exact_mismatch_rows": 1,
        "raw_score_max_abs_diff": float(score_diff.max()),
        "raw_score_order_parity_all_dates": True,
        "selected_score_mismatch_rows": selected_score_mismatches,
        "rank_semantic_mismatch_rows": int(rank_mismatch.sum()),
        "selected_rank_semantic_mismatch_rows": selected_rank_mismatches,
        "b18_overlap_dates": 311,
        "b18_overlap_key_sha256": overlap_hash,
        "b18_key_parity": True,
        "artifacts": {
            name: {"path": rel(path), "sha256": sha256(path), "bytes": path.stat().st_size}
            for name, path in {"sample": sample_path, "keys": keys_path, "audit": audit_path}.items()
        },
        "sealed_outcome_accessed": False,
        "training_performed": False,
        "production_write_performed": False,
    }
    manifest_path = OUTPUT / "HISTORICAL_EXACT50_MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": manifest["status"], "rows": 39350, "dates": 787, "b18_key_parity": True}))
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preflight-no-write", action="store_true")
    parser.add_argument("--materialize-historical-exact50", action="store_true")
    args = parser.parse_args()
    if args.preflight_no_write == args.materialize_historical_exact50:
        raise SystemExit("Select exactly one mode")
    if args.preflight_no_write:
        validate_protocol(require_authorization=False)
        if OUTPUT.exists():
            raise RuntimeError("V4 historical exact50 output already exists")
        print(json.dumps({"status": "PASS_NO_WRITE_V4", "output_absent": True, "authorization_checked": False}))
        return 0
    materialize()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
