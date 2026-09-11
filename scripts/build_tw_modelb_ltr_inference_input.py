#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from tw_modelb_ltr_score_common import (
    BLOCKED_STATUS,
    DEFAULT_RUN_ID,
    DNG3_ORTHOGONAL_STORE_DIR,
    DNG3_READINESS_MATRIX,
    DNG7_MODELA_SIGNAL_DIR,
    FALLBACK_ALLOWED,
    FORBIDDEN_ACTIONS_FALSE,
    INPUT_BASE,
    LTR_FEATURE_IMPORTANCE,
    LTR_MODEL_ARTIFACT,
    LTR_TRAINING_DIR,
    LTR_TRAINING_MANIFEST,
    MODEL_ID,
    TARGET_ASOF,
    collect_ltr_artifact_readiness,
    collect_modela_readiness,
    collect_orthogonal_readiness,
    file_entry,
    rel,
    utc_now,
    write_csv,
    write_json,
)


def build(asof: str, run_id: str) -> dict[str, Any]:
    out_dir = INPUT_BASE / run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    modela = collect_modela_readiness(asof)
    orthogonal = collect_orthogonal_readiness(asof)
    ltr_artifact = collect_ltr_artifact_readiness()
    blocking_datasets = orthogonal.get("blocking_datasets", [])

    errors: list[str] = []
    errors.extend(modela.get("errors", []))
    errors.extend(orthogonal.get("errors", []))
    errors.extend(ltr_artifact.get("errors", []))

    model_b_ltr_ready = (
        modela["can_continue"]
        and orthogonal.get("can_continue_to_model_b_ltr") is True
        and not blocking_datasets
        and not ltr_artifact.get("errors")
    )
    status = "READY" if model_b_ltr_ready else BLOCKED_STATUS

    schema = {
        "schema_version": "dng8.modelb_ltr_inference_input.v1",
        "artifact_type": "ModelInferenceInput",
        "model_id": MODEL_ID,
        "mode": "blocked_readiness_gate" if not model_b_ltr_ready else "ltr_top50_inference_input",
        "primary_key": ["date", "instrument"],
        "ready_required_files": ["inference_frame.csv"],
        "blocked_required_files": ["blocker_input_readiness.json"],
        "contract_docs": [
            "docs/tw_modular_contracts/MODEL_SIGNAL_CONTRACT_CN.md",
            "docs/tw_data_governance/DNG8_MODELB_LTR_SCORE_PIPELINE_WORK_CN.md",
        ],
        "ltr_semantics": {
            "candidate_rank": "must come from DNG7 Model A qlib signal",
            "full_qlib_rank": "must come from DNG7 Model A qlib signal",
            "buy_score": "must come from LTR only when ready",
            "score_rank": "must rank LTR buy_score only when ready",
            "top50_scope": "LTR may rerank qlib top50 only",
        },
        "forbidden_fields": [
            "future_return_*",
            "future_excess_return_*",
            "forward_return_*",
            "label_*",
            "relevance_10d_top_heavy",
            "ltr_relevance_label",
            "realized_pnl",
            "realized_return",
            "action",
            "holding",
            "position",
            "target_position",
            "target_weight",
            "order_qty",
            "execution_price",
            "execution_date",
            "broker_order_id",
        ],
    }
    write_json(out_dir / "schema.json", schema)

    blocker = {
        "artifact_type": "ModelB LTR blocker input readiness",
        "schema_version": "dng8.modelb_ltr.blocker_input_readiness.v1",
        "model_id": MODEL_ID,
        "run_id": run_id,
        "asof": asof,
        "created_at": utc_now(),
        "score_status": status,
        "model_b_ltr_ready": model_b_ltr_ready,
        "fallback_allowed": FALLBACK_ALLOWED,
        "fallback_signal_artifact": rel(DNG7_MODELA_SIGNAL_DIR),
        "fallback_semantics": "fallback qlib-only can only consume DNG7 Model A signal if an explicit downstream strategy contract allows qlib-only fallback",
        "no_ltr_signal_generated": not model_b_ltr_ready,
        "do_not_substitute_qlib_score_as_ltr_score": True,
        "blocking_datasets": blocking_datasets,
        "blocker_reasons": errors,
        "input_dependencies": {
            "modela": modela,
            "orthogonal_feature_store": orthogonal,
            "ltr_artifact": ltr_artifact,
        },
        "required_to_unblock": [
            "DNG3 readiness must report can_continue_to_model_b_ltr=true",
            "corporate_actions/monthly_revenue/valuation must be repaired as PIT-safe canonical features",
            "trained LTR feature schema must match available canonical feature families",
            "PIT audit must pass for the target asof",
        ],
        "forbidden_actions": FORBIDDEN_ACTIONS_FALSE,
    }
    write_json(out_dir / "blocker_input_readiness.json", blocker)

    source_readiness = {
        "status": status,
        "asof": asof,
        "model_id": MODEL_ID,
        "score_status": status,
        "model_b_ltr_ready": model_b_ltr_ready,
        "fallback_allowed": FALLBACK_ALLOWED,
        "blocking_datasets": blocking_datasets,
        "dependencies": [modela, orthogonal, ltr_artifact],
        "errors": errors,
        "forbidden_actions": FORBIDDEN_ACTIONS_FALSE,
    }
    write_json(out_dir / "source_readiness.json", source_readiness)

    feature_lineage = {
        "model_id": MODEL_ID,
        "asof": asof,
        "status": status,
        "lineage_mode": "blocked_gate_no_inference" if not model_b_ltr_ready else "ltr_top50_inference",
        "base_modela_signal": rel(DNG7_MODELA_SIGNAL_DIR),
        "orthogonal_feature_store": rel(DNG3_ORTHOGONAL_STORE_DIR),
        "orthogonal_readiness_matrix": rel(DNG3_READINESS_MATRIX),
        "ltr_training_dir": rel(LTR_TRAINING_DIR),
        "ltr_training_manifest": rel(LTR_TRAINING_MANIFEST),
        "ltr_model_artifact": rel(LTR_MODEL_ARTIFACT),
        "ltr_feature_importance": rel(LTR_FEATURE_IMPORTANCE),
        "ltr_feature_schema_status": "BLOCKED_BY_DNG3_ORTHOGONAL_READINESS" if not model_b_ltr_ready else "READY",
        "candidate_rank_source": "DNG7 Model A qlib signal",
        "full_qlib_rank_source": "DNG7 Model A qlib signal",
        "buy_score_source": "not generated; LTR blocked" if not model_b_ltr_ready else "LTR model inference",
        "pit_policy": "No Model B inference is run unless DNG3 canonical features are complete and PIT-safe at target asof.",
    }
    write_json(out_dir / "feature_lineage.json", feature_lineage)

    pit_rows = [
        {
            "check": "dng7_modela_signal_ready",
            "status": "PASS" if modela["can_continue"] else "FAIL",
            "details": ";".join(modela.get("errors", [])) or rel(DNG7_MODELA_SIGNAL_DIR),
        },
        {
            "check": "dng3_can_continue_to_model_b_ltr",
            "status": "PASS" if orthogonal.get("can_continue_to_model_b_ltr") is True else "FAIL",
            "details": "blocking_datasets=" + ",".join(blocking_datasets),
        },
        {
            "check": "required_orthogonal_feature_families",
            "status": "PASS" if not blocking_datasets else "FAIL",
            "details": "required families include institutional_flow, margin_short, corporate_actions, monthly_revenue, valuation",
        },
        {
            "check": "trained_ltr_model_artifact_present",
            "status": "PASS" if not ltr_artifact.get("errors") else "FAIL",
            "details": ";".join(ltr_artifact.get("errors", [])) or rel(LTR_MODEL_ARTIFACT),
        },
        {
            "check": "no_ltr_inference_when_blocked",
            "status": "PASS",
            "details": "builder wrote blocker_input_readiness.json and did not write inference_frame.csv",
        },
    ]
    write_csv(out_dir / "pit_audit.csv", pit_rows, ["check", "status", "details"])

    manifest = {
        "artifact_type": "ModelInferenceInput",
        "schema_version": "dng8.modelb_ltr_inference_input.v1",
        "model_id": MODEL_ID,
        "model_name": MODEL_ID,
        "model_family": "ltr",
        "run_id": run_id,
        "created_at": utc_now(),
        "created_by": "scripts/build_tw_modelb_ltr_inference_input.py",
        "asof": asof,
        "status": status,
        "score_status": status,
        "model_b_ltr_ready": model_b_ltr_ready,
        "fallback_allowed": FALLBACK_ALLOWED,
        "fallback_signal_artifact": rel(DNG7_MODELA_SIGNAL_DIR),
        "blocking_datasets": blocking_datasets,
        "row_count": 0,
        "symbol_count": 0,
        "files": {
            "manifest": "manifest.json",
            "blocker_input_readiness": "blocker_input_readiness.json",
            "schema": "schema.json",
            "source_readiness": "source_readiness.json",
            "feature_lineage": "feature_lineage.json",
            "pit_audit": "pit_audit.csv",
            "validator_report": "validator_report.json",
        },
        "omitted_files": {
            "inference_frame": "not generated because score_status=BLOCKED_INPUT_NOT_READY",
        },
        "source_artifacts": [
            rel(DNG7_MODELA_SIGNAL_DIR),
            rel(DNG3_ORTHOGONAL_STORE_DIR),
            rel(DNG3_READINESS_MATRIX),
            rel(LTR_TRAINING_MANIFEST),
            rel(LTR_MODEL_ARTIFACT),
        ],
        "required_file_entries": [
            file_entry(DNG7_MODELA_SIGNAL_DIR / "manifest.json", "dng7_modela_signal_manifest"),
            file_entry(DNG7_MODELA_SIGNAL_DIR / "signals.csv", "dng7_modela_signals"),
            file_entry(DNG3_ORTHOGONAL_STORE_DIR / "manifest.json", "dng3_orthogonal_manifest"),
            file_entry(DNG3_ORTHOGONAL_STORE_DIR / "features.csv", "dng3_orthogonal_features"),
            file_entry(DNG3_READINESS_MATRIX, "dng3_readiness_matrix"),
            file_entry(LTR_TRAINING_MANIFEST, "ltr_training_manifest"),
            file_entry(LTR_MODEL_ARTIFACT, "ltr_model_artifact"),
            file_entry(LTR_FEATURE_IMPORTANCE, "ltr_feature_importance"),
        ],
        "forbidden_actions": FORBIDDEN_ACTIONS_FALSE,
        "production_allowed": False,
        "not_published_latest": True,
        "errors": errors,
    }
    write_json(out_dir / "manifest.json", manifest)

    return {
        "run_id": run_id,
        "status": status,
        "score_status": status,
        "model_b_ltr_ready": model_b_ltr_ready,
        "asof": asof,
        "path": rel(out_dir),
        "blocking_datasets": blocking_datasets,
        "fallback_allowed": FALLBACK_ALLOWED,
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build DNG8 Model B LTR inference input or blocker readiness artifact.")
    parser.add_argument("--asof", default=TARGET_ASOF)
    parser.add_argument("--run-id", default=DEFAULT_RUN_ID)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = build(args.asof, args.run_id)
    if args.json:
        print(json.dumps(result, ensure_ascii=True, indent=2))
    else:
        print(f"{result['status']} {result['path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
