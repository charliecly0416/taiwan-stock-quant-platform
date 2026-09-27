#!/usr/bin/env python3
"""Static/no-write and post-materialization checks for historical Exact-50 V4."""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path

import pyarrow.parquet as pq


ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b19r2r_historical_exact50_20260916"
FREEZE = RUN / "HISTORICAL_EXACT50_FREEZE_V4.json"
BUILDER = ROOT / "scripts/build_modelb_b19r2r_historical_exact50.py"
OUTPUT = RUN / "materialized_v2"
V3_OUTPUT = RUN / "materialized_v1"
V3_FREEZE = RUN / "HISTORICAL_EXACT50_FREEZE_V3.json"
V3_AUTH = RUN / "HISTORICAL_EXACT50_INDEPENDENT_AUTHORIZATION_V3.json"
V3_FAILURE = RUN / "HISTORICAL_EXACT50_V3_MATERIALIZATION_FAILURE.json"
V3_FREEZE_SHA256 = "47c8452c79679549f172e07d40b3058f2aed69b63327ffdf329ef04e8dff3b96"
V3_AUTH_SHA256 = "a21283cc76149b92674216f1288a3ae797246854e5b590b9d803ddd4e3c23460"
V3_FAILURE_SHA256 = "b06be354bdbbd41b428846f66e18e1731ed0473f8a0290132db05141869caeb2"
FEATURE_ORDER_SHA256 = "2e0c169fb7762240aa20bc31ea53ac21b6a69db99dabea2f897421121105f2ca"
MODEL_A_STACKING_FEATURES = [
    "qlib_score_raw", "qlib_rank", "qlib_score_percentile_by_date", "qlib_score_zscore_by_date",
    "rank_change_1d", "rank_change_3d", "rank_change_5d", "top10_flag", "top30_flag", "top50_flag",
    "top30_streak", "top50_streak",
]
EXPECTED_SOURCE_PATHS = {
    "data_tw/experiments/project_runtime_convergence/modelb_b4_canonical_label_samples_20260914/B4_CANONICAL_TRAIN_SAMPLE.parquet",
    "data_tw/experiments/project_runtime_convergence/modelb_b4_canonical_label_samples_20260914/B4_CANONICAL_TEST_SAMPLE.parquet",
    "data_tw/experiments/project_runtime_convergence/modelb_b4_canonical_label_samples_20260914/B4_CANONICAL_EXECUTOR_MANIFEST.json",
    "data_tw/experiments/project_runtime_convergence/modelb_b3_frozen_modela_oos_score_20260913/MODEL_A_FROZEN_OOS_SCORE.parquet",
    "data_tw/experiments/project_runtime_convergence/modelb_b3_frozen_modela_oos_score_20260913/B3_MODEL_A_OOS_MANIFEST.json",
    "data_tw/experiments/project_runtime_convergence/modelb_canonical_labels_20260914/CANONICAL_LABEL_ARTIFACT.csv",
    "data_tw/experiments/project_runtime_convergence/modelb_b18r2_historical_pit_paired_replay_20260916/signals.csv",
    "data_tw/experiments/project_runtime_convergence/modelb_b2_canonical_pit_features_20260913/FEATURE_SCHEMA.json",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def subscript_path(node: ast.AST) -> tuple[str, ...] | None:
    if isinstance(node, ast.Name):
        return (node.id,)
    if not isinstance(node, ast.Subscript):
        return None
    parent = subscript_path(node.value)
    if parent is None or not isinstance(node.slice, ast.Constant) or not isinstance(node.slice.value, str):
        return None
    return parent + (node.slice.value,)


def call_name(node: ast.Call) -> str | None:
    if isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node.func, ast.Attribute):
        return node.func.attr
    return None


def protocol_checks() -> dict[str, bool]:
    checks = {"freeze_exists": FREEZE.is_file(), "builder_exists": BUILDER.is_file()}
    if not all(checks.values()):
        return checks
    freeze = json.loads(FREEZE.read_text(encoding="utf-8"))
    source = BUILDER.read_text(encoding="utf-8")
    tree = ast.parse(source)
    paths = {path for node in ast.walk(tree) if (path := subscript_path(node)) is not None}
    main_node = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "main")
    preflight_branch = next(
        node
        for node in main_node.body
        if isinstance(node, ast.If)
        and isinstance(node.test, ast.Attribute)
        and isinstance(node.test.value, ast.Name)
        and node.test.value.id == "args"
        and node.test.attr == "preflight_no_write"
    )
    preflight_calls = {call_name(node) for node in ast.walk(preflight_branch) if isinstance(node, ast.Call)}
    bindings = freeze.get("source_bindings", [])
    bound_paths = [item.get("path") for item in bindings if isinstance(item, dict)]
    lineage = freeze.get("lineage", {}).get("v3_failed_attempt", {})
    feature = freeze.get("feature_contract", {})

    checks["freeze_closed"] = freeze.get("status") == "CLOSED_AFTER_V3_DIAGNOSIS_BEFORE_V4_MATERIALIZATION"
    checks["builder_hash"] = freeze.get("implementation_bindings", {}).get("builder", {}).get("sha256") == sha256(BUILDER)
    checks["validator_hash"] = freeze.get("implementation_bindings", {}).get("validator", {}).get("sha256") == sha256(Path(__file__))
    checks["v3_failure_lineage_preserved"] = (
        lineage.get("freeze_sha256") == V3_FREEZE_SHA256
        and lineage.get("authorization_sha256") == V3_AUTH_SHA256
        and lineage.get("failure_sha256") == V3_FAILURE_SHA256
        and lineage.get("attempt_consumed") is True
        and lineage.get("authorization_independence_accepted") is False
        and V3_FREEZE.is_file() and sha256(V3_FREEZE) == V3_FREEZE_SHA256
        and V3_AUTH.is_file() and sha256(V3_AUTH) == V3_AUTH_SHA256
        and V3_FAILURE.is_file() and sha256(V3_FAILURE) == V3_FAILURE_SHA256
        and V3_OUTPUT.is_dir() and not any(V3_OUTPUT.iterdir())
    )
    checks["source_allowlist_exact"] = len(bound_paths) == len(EXPECTED_SOURCE_PATHS) and set(bound_paths) == EXPECTED_SOURCE_PATHS
    checks["sources_hash_bound"] = checks["source_allowlist_exact"] and all(
        (ROOT / item["path"]).is_file() and sha256(ROOT / item["path"]) == item["sha256"]
        for item in bindings
    )
    checks["feature_contract_corrected"] = (
        feature.get("feature_count") == 78
        and feature.get("feature_order_sha256") == FEATURE_ORDER_SHA256
        and feature.get("model_a_derived_stacking_features") == MODEL_A_STACKING_FEATURES
        and feature.get("model_a_derived_stacking_feature_count") == 12
        and feature.get("non_model_a_feature_count") == 66
        and "model_a_features_allowed" not in feature
        and "only_orthogonal_78f_allowed" not in feature
    )
    checks["feature_manifest_path_static"] = (
        ("freeze", "feature_contract", "feature_order_sha256") in paths
        and ("freeze", "feature_order_sha256") not in paths
    )
    checks["v4_paths_static"] = (
        'HISTORICAL_EXACT50_FREEZE_V4.json' in source
        and 'HISTORICAL_EXACT50_INDEPENDENT_AUTHORIZATION_V4.json' in source
        and 'OUTPUT = RUN / "materialized_v2"' in source
    )
    checks["dynamic_and_full_rank_static"] = (
        '["raw_score", "qlib_rank", "dynamic_qlib_rank"]' in source
        and '"qlib_rank": "full_qlib_rank"' in source
        and "np.array_equal(b4_rank, dynamic_rank)" in source
        and '"full_qlib_rank"' in source
    )
    checks["raw_score_authority_and_order_static"] = (
        'sort_values(["selection_raw_score_b3", "instrument"]' in source
        and 'sort_values(["qlib_score_raw", "instrument"]' in source
        and "daily score ordering parity failed" in source
        and "np.nextafter(" in source
        and "np.allclose(" not in source
    )
    checks["selected_score_exact_static"] = (
        "selected_score_mismatches" in source
        and "selected_score_mismatches != 0" in source
    )
    checks["shape_and_b18_static"] = all(token in source for token in [
        "exact50.date.nunique() != 787", "len(exact50) != 39350", "b18.date.nunique() != 321",
        "len(b18) != 16050", "overlap.date.nunique() != 311", "len(overlap) != 15550",
        "b4c5de21d8cc382297b3eb30c4e671ba0116e3973f2ab1d5f54a3f77676344a3",
    ])
    checks["label_contract_static"] = (
        "future_excess_return_10d_canonical" in source
        and "relevance_10d_top_heavy_canonical" in source
        and ".issubset({0, 1, 2, 3, 4})" in source
    )
    checks["write_once_before_value_read"] = (
        source.index("OUTPUT.mkdir(parents=True, exist_ok=False)") < source.index("SCHEMA.read_text")
        and source.index("OUTPUT.mkdir(parents=True, exist_ok=False)") < source.index("pd.read_parquet")
        and source.index("OUTPUT.mkdir(parents=True, exist_ok=False)") < source.index("pd.read_csv")
    )
    checks["no_write_preflight_ast"] = (
        'parser.add_argument("--preflight-no-write", action="store_true")' in source
        and "validate_protocol" in preflight_calls
        and not {"materialize", "mkdir", "write_text", "to_csv", "to_parquet", "read_csv", "read_parquet"}.intersection(preflight_calls)
    )
    checks["sealed_sources_absent"] = checks["source_allowlist_exact"] and not any(
        token in path for path in bound_paths for token in ("sealed_embargo", "sealed_confirmation", "CONFIRMATION", "EMBARGO")
    )
    checks["v4_output_absent"] = not OUTPUT.exists()
    checks["v4_authorization_absent"] = not (RUN / "HISTORICAL_EXACT50_INDEPENDENT_AUTHORIZATION_V4.json").exists()
    checks["materialization_not_authorized_at_freeze"] = freeze.get("safety_at_close", {}).get("materialization_authorized") is False
    checks["training_not_authorized_at_freeze"] = freeze.get("safety_at_close", {}).get("training_authorized") is False
    return checks


def materialized_checks() -> dict[str, bool]:
    manifest_path = OUTPUT / "HISTORICAL_EXACT50_MANIFEST.json"
    checks = {"manifest_exists": manifest_path.is_file()}
    if not manifest_path.is_file():
        return checks
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    artifacts = manifest.get("artifacts", {})
    sample_item = artifacts.get("sample", {})
    sample = ROOT / sample_item.get("path", "__missing__")
    checks["status"] = manifest.get("status") == "PASS_AWAITING_INDEPENDENT_REVIEW"
    checks["shape"] = (
        sample.is_file()
        and pq.ParquetFile(sample).metadata.num_rows == 39350
        and manifest.get("rows") == 39350
        and manifest.get("dates") == 787
        and manifest.get("rows_each_date") == 50
    )
    checks["artifact_hashes"] = bool(artifacts) and all(
        (ROOT / item["path"]).is_file() and sha256(ROOT / item["path"]) == item["sha256"]
        for item in artifacts.values()
    )
    checks["feature_semantics"] = (
        manifest.get("feature_count") == 78
        and manifest.get("model_a_stacking_feature_count") == 12
        and manifest.get("non_model_a_feature_count") == 66
        and manifest.get("b4_rank_matches_b3_dynamic_rank") is True
        and manifest.get("b3_full_rank_provenance_field") == "full_qlib_rank"
    )
    checks["selection_and_parity"] = (
        manifest.get("raw_score_exact_mismatch_rows") == 1
        and manifest.get("raw_score_order_parity_all_dates") is True
        and manifest.get("selected_score_mismatch_rows") == 0
        and manifest.get("b18_overlap_dates") == 311
        and manifest.get("b18_key_parity") is True
    )
    checks["safety"] = all(manifest.get(key) is False for key in [
        "sealed_outcome_accessed", "training_performed", "production_write_performed",
    ])
    return checks


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--precheck", action="store_true")
    parser.add_argument("--validate-materialized", action="store_true")
    args = parser.parse_args()
    if args.precheck == args.validate_materialized:
        raise SystemExit("Select exactly one mode")
    protocol = protocol_checks()
    result = {
        "protocol_checks": protocol,
        "protocol_verdict": "PASS" if protocol and all(protocol.values()) else "HOLD",
        "materialization_status": "NOT_RUN" if not OUTPUT.exists() else "FOOTPRINT_PRESENT",
        "training_go_no_go": "NO_GO_TRAINING",
    }
    if args.validate_materialized:
        materialized = materialized_checks()
        result["materialized_checks"] = materialized
        result["materialization_verdict"] = "PASS" if materialized and all(materialized.values()) else "HOLD"
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result.get("materialization_verdict", result["protocol_verdict"]) == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
