#!/usr/bin/env python3
"""Static/no-write and post-training checks for B19R2R LambdaRank."""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b19r2r_training_20260916"
FREEZE = RUN / "B19R2R_TRAINING_FREEZE.json"
TRAINER = ROOT / "scripts/train_modelb_b19r2r_lambdarank.py"
OUTPUT = RUN / "training_output_v1"
EXPECTED_SOURCES = {
    "data_tw/experiments/project_runtime_convergence/modelb_b19r2r_historical_exact50_20260916/materialized_v2/HISTORICAL_EXACT50_TRAINING_SAMPLE.parquet",
    "data_tw/experiments/project_runtime_convergence/modelb_b19r2r_historical_exact50_20260916/materialized_v2/HISTORICAL_EXACT50_MANIFEST.json",
    "data_tw/experiments/project_runtime_convergence/modelb_b19r2r_pretraining_materialization_20260916/FEATURE_ARTIFACT_78_RAW.parquet",
    "data_tw/experiments/project_runtime_convergence/modelb_b19r2r_pretraining_materialization_20260916/outcome_materialization_v1/development/DEVELOPMENT_EXACT50_LABELS.parquet",
    "data_tw/experiments/project_runtime_convergence/modelb_b19r2r_pretraining_materialization_20260916/NESTED_WALK_FORWARD_SPLIT_AMENDMENT_03.csv",
    "data_tw/experiments/project_runtime_convergence/modelb_b2_canonical_pit_features_20260913/FEATURE_SCHEMA.json",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def call_name(node: ast.Call) -> str | None:
    if isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node.func, ast.Attribute):
        return node.func.attr
    return None


def precheck() -> dict[str, bool]:
    checks = {"freeze_exists": FREEZE.is_file(), "trainer_exists": TRAINER.is_file()}
    if not all(checks.values()):
        return checks
    freeze = json.loads(FREEZE.read_text(encoding="utf-8"))
    source = TRAINER.read_text(encoding="utf-8")
    tree = ast.parse(source)
    main_node = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "main")
    preflight = next(
        node for node in main_node.body
        if isinstance(node, ast.If) and isinstance(node.test, ast.Attribute)
        and isinstance(node.test.value, ast.Name) and node.test.value.id == "args"
        and node.test.attr == "preflight_no_write"
    )
    preflight_calls = {call_name(node) for node in ast.walk(preflight) if isinstance(node, ast.Call)}
    main_calls = [node for node in ast.walk(main_node) if isinstance(node, ast.Call)]
    mkdir_line = next(node.lineno for node in main_calls if call_name(node) == "mkdir")
    schema_read_line = next(
        node.lineno for node in main_calls
        if call_name(node) == "read_text" and isinstance(node.func, ast.Attribute)
    )
    load_development_line = next(node.lineno for node in main_calls if call_name(node) == "load_development")
    bindings = freeze.get("source_bindings", [])
    paths = [item.get("path") for item in bindings if isinstance(item, dict)]
    checks["freeze_closed"] = freeze.get("status") == "CLOSED_BEFORE_TRAINING"
    checks["trainer_hash"] = freeze.get("implementation_bindings", {}).get("trainer", {}).get("sha256") == sha256(TRAINER)
    checks["validator_hash"] = freeze.get("implementation_bindings", {}).get("validator", {}).get("sha256") == sha256(Path(__file__))
    checks["source_allowlist_exact"] = len(paths) == len(EXPECTED_SOURCES) and set(paths) == EXPECTED_SOURCES
    checks["sources_hash_bound"] = checks["source_allowlist_exact"] and all(
        (ROOT / item["path"]).is_file() and sha256(ROOT / item["path"]) == item["sha256"] for item in bindings
    )
    review = freeze.get("historical_post_review", {})
    review_path = ROOT / review.get("path", "__missing__")
    checks["historical_post_review_bound"] = (
        review.get("verdict") == "PASS_V4_HISTORICAL_EXACT50"
        and review_path.is_file() and sha256(review_path) == review.get("sha256")
    )
    checks["exact50_inputs_static"] = (
        "HISTORICAL_EXACT50_TRAINING_SAMPLE.parquet" in source
        and "DEVELOPMENT_EXACT50_LABELS.parquet" in source
        and "B4_CANONICAL_TRAIN_SAMPLE" not in source and "B4_CANONICAL_TEST_SAMPLE" not in source
    )
    checks["combined_shape_static"] = all(token in source for token in [
        "len(historical) != 39350", "historical.date.nunique() != 787",
        "len(development_labels) != 2000", "development_labels.date.nunique() != 40",
        "len(data) != 41350", "data.date.nunique() != 827", 'data.groupby("date").size().ne(50)',
    ])
    checks["label_roles_static"] = (
        'RELEVANCE_LABEL = "relevance_10d_top_heavy_canonical"' in source
        and 'CONTINUOUS_LABEL = "future_excess_return_10d_canonical"' in source
        and "frame[RELEVANCE_LABEL].astype(int)" in source
        and "spearmanr(prediction, continuous)" in source
        and "ndcg_score(relevance[None, :]" in source
    )
    checks["sixteen_candidates"] = freeze.get("candidate_count") == 16 and len(freeze.get("candidate_grid", [])) == 16
    checks["feature_order"] = (
        freeze.get("feature_count") == 78
        and freeze.get("feature_order_sha256") == "2e0c169fb7762240aa20bc31ea53ac21b6a69db99dabea2f897421121105f2ca"
    )
    checks["fold_contract"] = (
        set(freeze.get("folds", {})) == {"inner_1", "inner_2", "outer_1", "outer_2"}
        and freeze.get("selection_policy", {}).get("outer_folds_may_change_hyperparameters") is False
        and freeze.get("final_refit_end") == "2026-07-06"
    )
    checks["parent_weights_not_reused"] = freeze.get("parent_weights_reused") is False and "MODEL_B_CANONICAL_LGBM_RANKER.pkl" not in source
    checks["write_once_before_value_read"] = mkdir_line < schema_read_line and mkdir_line < load_development_line
    checks["no_write_preflight_ast"] = (
        "load_protocol" in preflight_calls
        and not {"mkdir", "read_parquet", "read_csv", "fit_model", "dump", "to_csv", "write_text"}.intersection(preflight_calls)
    )
    checks["sealed_paths_absent"] = checks["source_allowlist_exact"] and not any(
        token in path for path in paths for token in ("sealed_embargo", "sealed_confirmation", "CONFIRMATION", "EMBARGO")
    )
    checks["output_absent"] = not OUTPUT.exists()
    checks["authorization_absent"] = not (RUN / "B19R2R_TRAINING_INDEPENDENT_AUTHORIZATION.json").exists()
    checks["training_not_authorized_at_freeze"] = freeze.get("safety_at_close", {}).get("training_authorized") is False
    return checks


def trained_checks() -> dict[str, bool]:
    manifest_path = OUTPUT / "TRAINING_MANIFEST.json"
    checks = {"manifest_exists": manifest_path.is_file()}
    if not manifest_path.is_file():
        return checks
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    artifacts = manifest.get("artifacts", {})
    checks["status"] = manifest.get("status") == "TRAINED_AWAITING_INDEPENDENT_REVIEW"
    checks["artifact_hashes"] = bool(artifacts) and all(
        (ROOT / item["path"]).is_file() and sha256(ROOT / item["path"]) == item["sha256"] for item in artifacts.values()
    )
    checks["data_shape"] = (
        manifest.get("historical_rows") == 39350 and manifest.get("development_rows") == 2000
        and manifest.get("combined_rows") == 41350 and manifest.get("combined_dates") == 827
        and manifest.get("rows_each_date") == 50
    )
    checks["label_roles"] = (
        manifest.get("fit_label") == "relevance_10d_top_heavy_canonical"
        and manifest.get("ndcg_label") == "relevance_10d_top_heavy_canonical"
        and manifest.get("rank_ic_label") == "future_excess_return_10d_canonical"
    )
    checks["selection_contract"] = (
        manifest.get("selection_source") == "INNER_1_AND_INNER_2_ONLY"
        and manifest.get("outer_selection_effect") == "NONE"
        and isinstance(manifest.get("selected_candidate_id"), int)
        and 0 <= manifest["selected_candidate_id"] < 16
    )
    checks["metric_tables"] = (
        len(pd.read_csv(OUTPUT / "INNER_SELECTION_METRICS.csv")) == 32
        and len(pd.read_csv(OUTPUT / "OUTER_DEVELOPMENT_CHECKS.csv")) == 2
    )
    checks["boundaries"] = manifest.get("final_refit_end") == "2026-07-06" and manifest.get("feature_count") == 78
    checks["safety"] = all(manifest.get(key) is False for key in [
        "confirmation_accessed", "embargo_accessed", "replay_performed",
        "baseline_or_latest_write_performed", "production_write_performed",
    ])
    return checks


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--precheck", action="store_true")
    parser.add_argument("--validate-trained", action="store_true")
    args = parser.parse_args()
    if args.precheck == args.validate_trained:
        raise SystemExit("Select exactly one mode")
    protocol = precheck()
    result = {
        "protocol_checks": protocol,
        "protocol_verdict": "PASS" if protocol and all(protocol.values()) else "HOLD",
        "training_status": "NOT_RUN" if not OUTPUT.exists() else "FOOTPRINT_PRESENT",
    }
    if args.validate_trained:
        trained = trained_checks()
        result["trained_checks"] = trained
        result["trained_verdict"] = "PASS" if trained and all(trained.values()) else "HOLD"
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result.get("trained_verdict", result["protocol_verdict"]) == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
