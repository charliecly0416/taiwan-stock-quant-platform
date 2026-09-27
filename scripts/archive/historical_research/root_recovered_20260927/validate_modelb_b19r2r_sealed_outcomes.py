#!/usr/bin/env python3
"""Metadata-only protocol and artifact validator for B19R2R sealed outcomes."""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import stat
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq


ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b19r2r_pretraining_materialization_20260916"
A6 = RUN / "B19R2R_PREOUTCOME_FREEZE_AMENDMENT_06.json"
A7 = RUN / "B19R2R_PREOUTCOME_FREEZE_AMENDMENT_07_ERRATA.json"
OUTPUT = RUN / "outcome_materialization_v1"
BUILDER = ROOT / "scripts/build_modelb_b19r2r_sealed_outcomes.py"
ADAPTER = ROOT / "scripts/modelb_b19r2r_twse_twii_20260915_adapter.py"
ISOLATED_PROVIDER = RUN / "isolated_model_a_provider_no_nontrading_placeholders"
PROTECTED_SNAPSHOT = RUN / "A6_PROTECTED_LATEST_BEFORE.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def rel(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT.resolve()))


def provider_feature_tree_hash() -> tuple[str, int]:
    digest = hashlib.sha256()
    paths = sorted(ISOLATED_PROVIDER.glob("features/*/*.day.bin"), key=lambda path: path.relative_to(ISOLATED_PROVIDER).as_posix())
    for path in paths:
        relative_path = path.relative_to(ISOLATED_PROVIDER).as_posix()
        digest.update(f"{relative_path}\0{sha256(path)}\0{path.stat().st_size}\n".encode("ascii"))
    return digest.hexdigest(), len(paths)


def protected_latest_unchanged() -> bool:
    snapshot = json.loads(PROTECTED_SNAPSHOT.read_text(encoding="utf-8"))
    for relative_path, expected in snapshot.get("paths", {}).items():
        path = ROOT / relative_path
        if not path.is_file() or sha256(path) != expected.get("sha256") or path.stat().st_size != expected.get("bytes"):
            return False
    return True


def protocol_checks() -> dict[str, bool]:
    checks: dict[str, bool] = {"a6_exists": A6.is_file(), "a7_errata_exists": A7.is_file()}
    if not A6.is_file() or not A7.is_file():
        return checks
    protocol = json.loads(A6.read_text(encoding="utf-8"))
    errata = json.loads(A7.read_text(encoding="utf-8"))
    bindings = errata.get("implementation_bindings", {})
    checks["a6_closed_before_outcome_read"] = protocol.get("status") == "CLOSED_BEFORE_ANY_A6_OUTCOME_VALUE_READ"
    checks["a7_errata_closed_before_materialization"] = errata.get("status") == "ERRATA_CLOSED_BEFORE_MATERIALIZATION"
    checks["a7_binds_retained_a6"] = errata.get("supersedes_a6_sha256") == sha256(A6)
    disclosure = errata.get("corrected_prior_source_row_read_disclosure", {})
    checks["prior_twii_close_observation_disclosed"] = (
        disclosure.get("numeric_close_value_semantically_observed") is True
        and disclosure.get("return_label_metric_generated") is False
        and disclosure.get("used_for_model_parameter_or_threshold_selection") is False
    )
    checks["builder_hash_matches"] = bindings.get("outcome_builder", {}).get("sha256") == sha256(BUILDER)
    checks["adapter_hash_matches"] = bindings.get("twse_twii_adapter", {}).get("sha256") == sha256(ADAPTER)
    checks["validator_hash_matches"] = bindings.get("metadata_validator", {}).get("sha256") == sha256(Path(__file__))
    checks["all_source_hashes_match"] = all(
        (ROOT / item["path"]).is_file() and sha256(ROOT / item["path"]) == item["sha256"]
        for item in protocol.get("source_bindings", [])
    )
    provider_binding = protocol.get("directory_bindings", {}).get("isolated_provider_features", {})
    provider_tree_hash, provider_file_count = provider_feature_tree_hash()
    checks["isolated_provider_tree_hash_matches"] = (
        provider_tree_hash == provider_binding.get("canonical_tree_sha256")
        and provider_file_count == provider_binding.get("file_count") == 1050
    )
    checks["protected_latest_matches_a6_snapshot"] = protected_latest_unchanged()
    builder_source = BUILDER.read_text(encoding="utf-8")
    adapter_source = ADAPTER.read_text(encoding="utf-8")
    checks["adapter_exact_identity_and_roc_date"] = (
        'EXPECTED_INDEX = "發行量加權股價指數"' in adapter_source
        and 'EXPECTED_ROC_DATE = "1150915"' in adapter_source
        and 'EXPECTED_DATE = "2026-09-15"' in adapter_source
        and 'prior.get("target_asof") != "2026-09-16"' in adapter_source
        and '["target_date_mismatch"]' in adapter_source
    )
    checks["full_cross_section_label_contract_static"] = (
        'len(keys) != 12000 or keys.groupby("date").size().ne(150).any()' in builder_source
        and 'rank(pct=True, method="average")' in builder_source
        and 'dates[index[signal_date] + 10]' in builder_source
        and 'np.select([rank >= .90, rank >= .80, rank >= .70, rank >= .50]' in builder_source
    )
    checks["role_separation_static"] = all(token in builder_source for token in [
        'development/DEVELOPMENT_LABELS.parquet',
        'development/DEVELOPMENT_EXECUTION_GRID.parquet',
        'sealed_embargo/EMBARGO_OUTCOMES.parquet',
        'sealed_embargo/EMBARGO_EXECUTION_GRID.parquet',
        'sealed_confirmation/CONFIRMATION_OUTCOMES.parquet',
        'sealed_confirmation/CONFIRMATION_EXECUTION_GRID.parquet',
    ])
    checks["isolated_next_price_and_terminal_static"] = (
        'decode_field(symbol, "open"' in builder_source
        and 'decode_field(symbol, "close"' in builder_source
        and '"2026-09-02"' in builder_source
        and "option_c_150_normalized" not in builder_source
    )
    checks["metadata_only_manifest_contract"] = (
        '"value_distribution_or_metric_exposed": False' in builder_source
        and '"outcome_evaluation_performed": False' in builder_source
        and '"training_performed": False' in builder_source
    )
    checks["frozen_execution_grid_only_static"] = (
        '"future_evaluator_must_consume_frozen_grid": True' in builder_source
        and '"live_price_reread_allowed": False' in builder_source
        and '"missing_price_fallback_allowed": False' in builder_source
    )
    validator_tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))
    called_names = {
        node.func.attr if isinstance(node.func, ast.Attribute) else node.func.id
        for node in ast.walk(validator_tree)
        if isinstance(node, ast.Call) and isinstance(node.func, (ast.Attribute, ast.Name))
    }
    accessed_attributes = {node.attr for node in ast.walk(validator_tree) if isinstance(node, ast.Attribute)}
    checks["validator_uses_parquet_footer_only"] = (
        "ParquetFile" in called_names
        and not {"read_table", "read_parquet"}.intersection(called_names)
        and "statistics" not in accessed_attributes
    )
    checks["sealed_policy_deny_by_default"] = protocol.get("sealed_access_policy", {}).get("confirmation_access") == "DENY_BY_DEFAULT"
    checks["no_training_or_evaluation_authorization"] = (
        errata.get("safety_at_close", {}).get("training_authorized") is False
        and errata.get("safety_at_close", {}).get("outcome_evaluation_authorized") is False
        and errata.get("safety_at_close", {}).get("materialization_execution_authorized") is False
    )
    return checks


def materialized_checks() -> dict[str, bool]:
    manifest_path = OUTPUT / "OUTCOME_MATERIALIZATION_MANIFEST.json"
    checks: dict[str, bool] = {"manifest_exists": manifest_path.is_file()}
    if not manifest_path.is_file():
        return checks
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    checks["manifest_status_sealed_no_evaluation"] = manifest.get("status") == "PASS_SEALED_NO_EVALUATION"
    checks["manifest_no_evaluation_training_replay_production"] = (
        manifest.get("value_distribution_or_metric_exposed") is False
        and manifest.get("outcome_evaluation_performed") is False
        and manifest.get("training_performed") is False
        and manifest.get("model_b_or_b9_inference_performed") is False
        and manifest.get("replay_performed") is False
        and manifest.get("production_write_performed") is False
        and manifest.get("protected_latest_unchanged") is True
    )
    checks["protected_latest_still_unchanged"] = protected_latest_unchanged()
    label_schema = [
        "date", "instrument", "role", "target_date_10d",
        "stock_return_10d_canonical", "market_return_10d_canonical",
        "future_excess_return_10d_canonical",
        "future_excess_return_rank_10d_canonical",
        "relevance_10d_top_heavy_canonical", "label_complete",
    ]
    execution_schema = [
        "date", "instrument", "role", "next_trade_date", "next_open", "next_close",
        "terminal_mark_date", "terminal_2026_09_02_close", "execution_grid_complete",
    ]
    exact50_schema = [
        "date", "instrument", "target_date_10d", "future_excess_return_10d_canonical",
        "future_excess_return_rank_10d_canonical", "relevance_10d_top_heavy_canonical",
        "label_complete",
    ]
    expected = {
        "development_labels": (6000, 40, False, label_schema),
        "development_exact50_labels": (2000, 40, False, exact50_schema),
        "development_execution_grid": (6000, 40, False, execution_schema),
        "embargo_outcomes": (1500, 10, True, label_schema),
        "embargo_execution_grid": (1500, 10, True, execution_schema),
        "confirmation_outcomes": (4500, 30, True, label_schema),
        "confirmation_execution_grid": (4500, 30, True, execution_schema),
    }
    artifacts = manifest.get("artifacts", {})
    for name, (rows, dates, sealed, expected_schema) in expected.items():
        item = artifacts.get(name, {})
        path = ROOT / item.get("path", "__missing__")
        prefix = f"artifact_{name}"
        checks[f"{prefix}_exists"] = path.is_file()
        if not path.is_file():
            continue
        parquet = pq.ParquetFile(path)
        checks[f"{prefix}_hash_bytes"] = sha256(path) == item.get("sha256") and path.stat().st_size == item.get("bytes")
        checks[f"{prefix}_metadata_counts"] = parquet.metadata.num_rows == item.get("row_count") == rows and item.get("date_count") == dates
        checks[f"{prefix}_schema"] = parquet.schema_arrow.names == item.get("schema") == expected_schema
        checks[f"{prefix}_complete"] = item.get("completeness_boolean") is True
        checks[f"{prefix}_permissions"] = (stat.S_IMODE(path.stat().st_mode) == 0o600) if sealed else True
    access_path = OUTPUT / "SEALED_ACCESS_LOG.json"
    checks["sealed_access_log_exists"] = access_path.is_file()
    if access_path.is_file():
        access = json.loads(access_path.read_text(encoding="utf-8"))
        checks["sealed_access_log_no_evaluation"] = access.get("confirmation_evaluation_performed") is False and access.get("post_write_value_read_allowed") is False
    adapter_manifest_path = OUTPUT / "twii_20260915_adapter/TWII_20260915_ADAPTER_MANIFEST.json"
    checks["twii_adapter_manifest_exists"] = adapter_manifest_path.is_file()
    if adapter_manifest_path.is_file():
        adapter_manifest = json.loads(adapter_manifest_path.read_text(encoding="utf-8"))
        checks["twii_adapter_metadata_only_complete"] = (
            adapter_manifest.get("source_identity") == "發行量加權股價指數"
            and adapter_manifest.get("normalized_date") == "2026-09-15"
            and adapter_manifest.get("row_count") == 1
            and adapter_manifest.get("completeness_boolean") is True
            and adapter_manifest.get("value_or_distribution_exposed_in_manifest") is False
        )
    execution_policy = manifest.get("execution_grid_policy", {})
    checks["frozen_execution_grid_only"] = (
        execution_policy.get("future_evaluator_must_consume_frozen_grid") is True
        and execution_policy.get("live_price_reread_allowed") is False
        and execution_policy.get("missing_price_fallback_allowed") is False
    )
    return checks


def validate(include_materialized: bool) -> dict[str, Any]:
    protocol = protocol_checks()
    result: dict[str, Any] = {
        "schema_version": "modelb.b19r2r.sealed_outcome_metadata_validator.v1",
        "protocol_checks": protocol,
        "protocol_precheck_verdict": "PASS" if protocol and all(protocol.values()) else "HOLD",
        "materialization_status": "NOT_RUN" if not OUTPUT.exists() else "FOOTPRINT_PRESENT",
        "training_go_no_go": "NO_GO_TRAINING",
    }
    if include_materialized:
        artifacts = materialized_checks()
        result["materialized_checks"] = artifacts
        result["materialization_verdict"] = "PASS" if artifacts and all(artifacts.values()) else "HOLD"
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--precheck", action="store_true")
    parser.add_argument("--validate-materialized", action="store_true")
    args = parser.parse_args()
    if args.precheck == args.validate_materialized:
        raise SystemExit("Select exactly one of --precheck or --validate-materialized")
    result = validate(include_materialized=args.validate_materialized)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    verdict = result.get("materialization_verdict", result["protocol_precheck_verdict"])
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
