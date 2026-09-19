#!/usr/bin/env python3
"""Freeze the exact implementation for the B19R2R development comparison."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b19r2r_comparative_evaluation_20260916"
FREEZE = RUN / "B19R2R_COMPARATIVE_IMPLEMENTATION_FREEZE_V2.json"
REPORT = RUN / "B19R2R_COMPARATIVE_IMPLEMENTATION_FREEZE_V2_CN.md"
AUTH = RUN / "B19R2R_COMPARATIVE_EXECUTION_AUTHORIZATION_V2.json"
OUTPUT = RUN / "evaluation_output_v2"
V1_FREEZE = RUN / "B19R2R_COMPARATIVE_IMPLEMENTATION_FREEZE.json"
V1_AUTH = RUN / "B19R2R_COMPARATIVE_EXECUTION_AUTHORIZATION.json"
V1_FAILURE = RUN / "B19R2R_COMPARATIVE_EXECUTION_FAILURE_V1.json"

PROTOCOL = RUN / "B19R2R_COMPARATIVE_FREEZE.json"
ADAPTER = RUN / "B19R2R_COMPARATIVE_FREEZE_AMENDMENT_01.json"
R2R = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b19r2r_pretraining_materialization_20260916"
HISTORICAL_RUN = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b19r2r_historical_exact50_20260916"
TRAINING_RUN = ROOT / "data_tw/experiments/project_runtime_convergence/modelb_b19r2r_training_20260916"

IMPLEMENTATIONS = {
    "implementation_freeze_builder": Path(__file__),
    "evaluator": ROOT / "scripts/run_modelb_b19r2r_development_comparison.py",
    "validator": ROOT / "scripts/validate_modelb_b19r2r_development_comparison.py",
}
SOURCES = {
    "v1_failed_implementation_freeze": V1_FREEZE,
    "v1_consumed_execution_authorization": V1_AUTH,
    "v1_execution_failure_report": V1_FAILURE,
    "comparative_protocol": PROTOCOL,
    "sole_adapter_amendment": ADAPTER,
    "historical_exact50_training_sample": HISTORICAL_RUN
    / "materialized_v2/HISTORICAL_EXACT50_TRAINING_SAMPLE.parquet",
    "historical_exact50_post_review": HISTORICAL_RUN
    / "HISTORICAL_EXACT50_V4_POST_MATERIALIZATION_INDEPENDENT_REVIEW.json",
    "development_features_78f": R2R / "FEATURE_ARTIFACT_78_RAW.parquet",
    "development_exact50_keys": R2R / "EXACT50_KEYSETS.csv",
    "model_a_development_scores": R2R / "MODEL_A_FULL_CROSS_SECTION.parquet",
    "development_exact50_labels": R2R
    / "outcome_materialization_v1/development/DEVELOPMENT_EXACT50_LABELS.parquet",
    "development_execution_grid": R2R
    / "outcome_materialization_v1/development/DEVELOPMENT_EXECUTION_GRID.parquet",
    "feature_schema": ROOT
    / "data_tw/experiments/project_runtime_convergence/modelb_b2_canonical_pit_features_20260913/FEATURE_SCHEMA.json",
    "training_manifest": TRAINING_RUN / "training_output_v1/TRAINING_MANIFEST.json",
    "post_training_review": TRAINING_RUN / "B19R2R_POST_TRAINING_INDEPENDENT_REVIEW.json",
    "strategy_dependency": ROOT / "configs/strategy_dependencies/top50_exit_one_worst_sell.yaml",
    "paired_replay_reference": ROOT / "scripts/run_modelb_b18_historical_pit_paired_replay.py",
    "modular_replay_engine": ROOT / "scripts/run_tw_modular_order_intent_replay.py",
}
EXPECTED_PROTOCOL_SHA256 = "7283f87f640a4cb8576f1038e823b6e9fd2c07e869239bd7fe61d65ba74e8fad"
EXPECTED_ADAPTER_SHA256 = "d50daf9efba797a11d38f4d70da63447ab118eb4f5d2625f0647a31b1984202e"
FORBIDDEN_SOURCE_FRAGMENTS = ("sealed_embargo", "sealed_confirmation", "EMBARGO_", "CONFIRMATION_")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def rel(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT.resolve()))


def binding(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise RuntimeError(f"missing binding: {rel(path)}")
    return {"path": rel(path), "sha256": sha256(path), "bytes": path.stat().st_size}


def write_once(path: Path, payload: str) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o444)
    try:
        data = payload.encode("utf-8")
        offset = 0
        while offset < len(data):
            offset += os.write(descriptor, data[offset:])
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def validate_inputs() -> None:
    if FREEZE.exists() or REPORT.exists():
        raise RuntimeError("implementation freeze artifacts already exist; refusing overwrite")
    if AUTH.exists() or OUTPUT.exists():
        raise RuntimeError("authorization or evaluation output already exists")
    for path in [*IMPLEMENTATIONS.values(), *SOURCES.values()]:
        if not path.is_file():
            raise RuntimeError(f"missing required file: {rel(path)}")
    if sha256(PROTOCOL) != EXPECTED_PROTOCOL_SHA256:
        raise RuntimeError("comparative protocol hash drifted")
    if sha256(ADAPTER) != EXPECTED_ADAPTER_SHA256:
        raise RuntimeError("adapter amendment hash drifted")
    for path in SOURCES.values():
        if any(token in rel(path) for token in FORBIDDEN_SOURCE_FRAGMENTS):
            raise RuntimeError(f"sealed source forbidden: {rel(path)}")

    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    adapter = json.loads(ADAPTER.read_text(encoding="utf-8"))
    historical_review = json.loads(SOURCES["historical_exact50_post_review"].read_text(encoding="utf-8"))
    training_review = json.loads(SOURCES["post_training_review"].read_text(encoding="utf-8"))
    training_manifest = json.loads(SOURCES["training_manifest"].read_text(encoding="utf-8"))
    v1_failure = json.loads(V1_FAILURE.read_text(encoding="utf-8"))
    if protocol.get("status") != "CLOSED_DEVELOPMENT_DIAGNOSTIC_COMPARISON_NOT_AUTHORIZED":
        raise RuntimeError("comparative protocol is not closed")
    if adapter.get("status") != "ADDITIVE_CLOSED_BEFORE_ANY_COMPARATIVE_PREDICTION_OR_EVALUATION":
        raise RuntimeError("adapter amendment is not closed")
    if adapter.get("sole_treatment_adapter", {}).get("model_b_weight") != 1.0:
        raise RuntimeError("sole treatment adapter drifted")
    if historical_review.get("verdict") != "PASS_V4_HISTORICAL_EXACT50":
        raise RuntimeError("historical materialization review is not PASS")
    if training_review.get("verdict") != "PASS_TRAINED_MODEL_ARTIFACT":
        raise RuntimeError("post-training review is not PASS")
    if training_manifest.get("selected_candidate_id") != 14 or training_manifest.get("feature_count") != 78:
        raise RuntimeError("selected training contract drifted")
    if (
        v1_failure.get("status") != "FAILED_SINGLE_AUTHORIZED_ATTEMPT_NO_RETRY"
        or v1_failure.get("safety_after_failure", {}).get("old_authorization_reusable") is not False
        or v1_failure.get("safety_after_failure", {}).get("evaluation_output_v1_exists") is not False
        or v1_failure.get("bindings", {}).get("implementation_freeze", {}).get("sha256") != sha256(V1_FREEZE)
        or v1_failure.get("bindings", {}).get("execution_authorization", {}).get("sha256") != sha256(V1_AUTH)
    ):
        raise RuntimeError("V1 failure evidence binding failed")


def build_payload() -> dict[str, Any]:
    return {
        "schema_version": "modelb.b19r2r.comparative_implementation_freeze.v2",
        "status": "CLOSED_BEFORE_COMPARATIVE_EXECUTION",
        "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "purpose": "Bind the repaired V2 development-only A versus A+B evaluator after preserving the failed V1 attempt.",
        "v1_failure_disposition": {
            "failure_report_path": rel(V1_FAILURE),
            "failure_report_sha256": sha256(V1_FAILURE),
            "v1_authorization_consumed": True,
            "v1_retry_allowed": False,
            "v2_namespace_required": True,
        },
        "implementation_bindings": {name: binding(path) for name, path in IMPLEMENTATIONS.items()},
        "source_bindings": {name: binding(path) for name, path in SOURCES.items()},
        "execution_contract": {
            "mode": "execute_frozen_comparison",
            "namespace": "V2",
            "attempts_authorized": 0,
            "independent_single_attempt_authorization_required": True,
            "authorization_must_bind_this_freeze_sha256": True,
            "output_write_once": True,
            "primary_scope": "combined_development_continuous_40_signal_days",
            "outer_fold_reset_scopes": "diagnostic_only",
            "development_result_role": "diagnostic_and_readiness_only",
            "automatic_baseline_admission_allowed": False,
        },
        "confirmation_only_reserved_gates": {
            "confirmation_after_cost_return_delta_b_minus_a": "RESERVED_FOR_CONFIRMATION_NOT_EVALUATED",
            "confirmation_paired_moving_block_bootstrap_95pct_lower_bound": "RESERVED_FOR_CONFIRMATION_NOT_EVALUATED",
            "development_admission_effect": "NONE",
        },
        "bootstrap_contract": {
            "scope": "sealed_confirmation_only",
            "generator": "numpy.random.Generator(PCG64)",
            "seed": 20260916,
            "noncircular": True,
            "series_length": 30,
            "block_length": 10,
            "valid_start_indices_inclusive": [0, 20],
            "blocks_per_replication": 3,
            "replications": 10000,
            "lower_bound": "numpy.quantile(bootstrap_means, 0.05, method='linear')",
            "development_bootstrap_allowed": False,
        },
        "safety_at_close": {
            "comparison_execution_authorized": False,
            "authorization_file_present": False,
            "evaluation_output_present": False,
            "fit_prediction_replay_or_metric_performed_by_freezer": False,
            "sealed_embargo_or_confirmation_access_allowed": False,
            "final_refit_pickle_allowed_for_development": False,
            "training_or_tuning_allowed": False,
            "baseline_or_production_write_authorized": False,
            "provider_publish_or_accepted_latest_switch_authorized": False,
            "frontend_database_or_broker_write_authorized": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--freeze-implementation", action="store_true")
    args = parser.parse_args()
    if not args.freeze_implementation:
        raise SystemExit("Use --freeze-implementation")
    validate_inputs()
    payload = build_payload()
    report = (
        "# B19R2R comparative implementation freeze V2\n\n"
        "V1 单次授权失败已固化且禁止重试。现冻结修复后的 development-only Model A 与 Model A+B 比较器、validator 及全部输入的 SHA256。\n\n"
        "当前没有比较执行授权；未进行拟合、预测、回放或指标计算。禁止读取 sealed embargo/confirmation，"
        "禁止 baseline、latest、provider、前端、数据库或生产写入。\n"
    )
    RUN.mkdir(parents=True, exist_ok=True)
    write_once(FREEZE, json.dumps(payload, indent=2, ensure_ascii=True) + "\n")
    write_once(REPORT, report)
    print(json.dumps({"status": payload["status"], "freeze": rel(FREEZE), "sha256": sha256(FREEZE)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
