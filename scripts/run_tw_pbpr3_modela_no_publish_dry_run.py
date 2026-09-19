#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from tw_modela_score_common import (  # noqa: E402
    make_modela_runtime_config,
    validate_modela_runtime_config,
)

PBPR3_OUTPUT_ROOT = (
    ROOT
    / "data_tw/experiments/provider_bridge_productionization/"
    "pbpr3_target_asof_model_a_no_publish_dry_run"
)
PBPR3R_EVIDENCE_ROOT = (
    ROOT
    / "data_tw/experiments/provider_bridge_productionization/"
    "pbpr3r_safe_isolated_modela_dry_run_entrypoint_repair"
)
DEFAULT_ACCEPTED_READINESS = (
    ROOT
    / "data_tw/experiments/provider_bridge_productionization/"
    "pbpr2a_ac_provider_candidate_readiness_review/provider_candidate_readiness_accepted.json"
)
PBPR3S_EVIDENCE_ROOT = (
    ROOT
    / "data_tw/experiments/provider_bridge_productionization/"
    "pbpr3s_safe_isolated_modela_scoring_adapter"
)
PBPR3U_EVIDENCE_ROOT = (
    ROOT
    / "data_tw/experiments/provider_bridge_productionization/"
    "pbpr3u_contained_modela_scoring_build_adapter_repair"
)
PBPR3W_EVIDENCE_ROOT = (
    ROOT
    / "data_tw/experiments/provider_bridge_productionization/"
    "pbpr3w_contained_real_runtime_repair"
)
PBPR3_PARAMETERIZATION_EVIDENCE_ROOT = (
    ROOT
    / "data_tw/experiments/provider_bridge_productionization/"
    "pbpr3_20260720_safe_entrypoint_parameterization_latest_target"
)

FORBIDDEN_PATH_PARTS = {
    "latest",
    "catalog",
    "publish",
    "published",
    "accepted_latest",
    "readonly",
    "agent",
    "agent_daily_prompt",
    "monitor",
    "broker",
    "order",
    "target_position",
    "target_weight",
    "target_output",
}
FORBIDDEN_PATH_FRAGMENTS = (
    "data_tw/artifacts/",
    "data_tw/canonical/",
    "qlib_pipeline/data_tw/experiments/option_c_daily_signal",
)


@dataclass(frozen=True)
class SafetyFlags:
    no_publish: bool
    no_catalog: bool
    no_latest: bool
    no_target_output: bool
    preflight_only: bool


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except Exception:
        return str(path)


def resolve_repo_path(path: Path | str) -> Path:
    p = Path(path)
    if not p.is_absolute():
        p = ROOT / p
    return p.resolve(strict=False)


def is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.resolve(strict=False).relative_to(root.resolve(strict=False))
        return True
    except ValueError:
        return False


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")


def path_forbidden_reason(path: Path) -> str | None:
    rel_text = rel(path).replace("\\", "/")
    lowered_parts = {part.lower() for part in path.parts}
    for part in sorted(FORBIDDEN_PATH_PARTS):
        if part in lowered_parts:
            return f"forbidden_path_part:{part}"
    for fragment in FORBIDDEN_PATH_FRAGMENTS:
        if fragment in rel_text:
            return f"forbidden_path_fragment:{fragment.rstrip('/')}"
    return None


def calendar_max(provider_root: Path) -> str | None:
    path = provider_root / "calendars/day.txt"
    if not path.exists():
        return None
    values = [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return max(values) if values else None


def load_accepted_lineage(path: Path) -> dict[str, Any]:
    payload = read_json(path)
    lineage = payload.get("lineage", {})
    feature_path = lineage.get("feature_path", "")
    normalized_paths = lineage.get("normalized_output_paths", [])
    if not feature_path:
        raise ValueError("accepted_readiness_missing_feature_path")
    if not normalized_paths:
        raise ValueError("accepted_readiness_missing_normalized_output_paths")
    expected_provider_root = resolve_repo_path(Path(feature_path).parent)
    expected_normalized_root = resolve_repo_path(normalized_paths[0])
    return {
        "payload": payload,
        "expected_provider_root": expected_provider_root,
        "expected_normalized_root": expected_normalized_root,
    }


def is_valid_asof(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        return datetime.strptime(value, "%Y-%m-%d").date().isoformat() == value
    except ValueError:
        return False


def resolve_target_asof(
    requested_target_asof: str,
    accepted_payload: dict[str, Any],
    errors: list[str],
) -> tuple[str, str]:
    accepted_target_asof = accepted_payload.get("target_asof")
    accepted_candidate_asof = accepted_payload.get("candidate_asof")
    if not is_valid_asof(accepted_target_asof):
        errors.append(f"accepted_readiness_invalid_target_asof:{accepted_target_asof}")
    if not is_valid_asof(accepted_candidate_asof):
        errors.append(f"accepted_readiness_invalid_candidate_asof:{accepted_candidate_asof}")
    if accepted_target_asof != accepted_candidate_asof:
        errors.append("accepted_readiness_target_candidate_asof_mismatch")

    if requested_target_asof in {"auto", "latest"}:
        if is_valid_asof(accepted_target_asof):
            return accepted_target_asof, requested_target_asof
        return requested_target_asof, requested_target_asof

    if not is_valid_asof(requested_target_asof):
        errors.append(f"target_asof_invalid:{requested_target_asof}")
        return requested_target_asof, "explicit"
    return requested_target_asof, "explicit"


def accepted_forbidden_actions_all_false(accepted_payload: dict[str, Any]) -> bool:
    forbidden_actions = accepted_payload.get("forbidden_actions")
    if isinstance(forbidden_actions, dict) and forbidden_actions.get("all_false") is True:
        return True
    forbidden_action_summary = accepted_payload.get("forbidden_action_summary")
    if isinstance(forbidden_action_summary, dict) and forbidden_action_summary:
        return all(value is False for value in forbidden_action_summary.values())
    return False


def validate_preflight(
    *,
    target_asof: str,
    accepted_readiness: Path,
    provider_root: Path,
    normalized_root: Path,
    output_root: Path,
    flags: SafetyFlags,
    preflight_report: Path | None = None,
) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    requested_target_asof = target_asof

    accepted_readiness = resolve_repo_path(accepted_readiness)
    provider_root = resolve_repo_path(provider_root)
    normalized_root = resolve_repo_path(normalized_root)
    output_root = resolve_repo_path(output_root)
    preflight_report = resolve_repo_path(preflight_report) if preflight_report else None

    if not flags.preflight_only:
        errors.append("preflight_only_required_in_pbpr3r")
    for name in ("no_publish", "no_catalog", "no_latest", "no_target_output"):
        if getattr(flags, name) is not True:
            errors.append(f"required_safety_flag_missing:{name}")

    accepted_payload: dict[str, Any] = {}
    expected_provider_root = Path()
    expected_normalized_root = Path()
    try:
        lineage = load_accepted_lineage(accepted_readiness)
        accepted_payload = lineage["payload"]
        expected_provider_root = lineage["expected_provider_root"]
        expected_normalized_root = lineage["expected_normalized_root"]
    except Exception as exc:
        errors.append(f"accepted_readiness_load_failed:{exc}")

    target_resolution_mode = "unresolved"
    if accepted_payload:
        target_asof, target_resolution_mode = resolve_target_asof(
            requested_target_asof, accepted_payload, errors
        )
        if accepted_payload.get("target_asof") != target_asof:
            errors.append("accepted_readiness_target_asof_mismatch")
        if accepted_payload.get("candidate_asof") != target_asof:
            errors.append("accepted_readiness_candidate_asof_mismatch")
        required_flags = {
            "production_allowed": False,
            "not_published_latest": True,
            "publish_latest_allowed": False,
            "model_scoring_allowed": False,
            "not_final_production_readiness": True,
            "not_catalog_published": True,
            "not_latest_pointer": True,
        }
        for key, expected in required_flags.items():
            if key in accepted_payload and accepted_payload.get(key) is not expected:
                errors.append(f"accepted_readiness_flag_mismatch:{key}")
        optional_false_authorizations = (
            "ready_for_provider_publish",
            "ready_for_latest_switch",
            "ready_for_qlib_refresh",
            "ready_for_readonly_snapshot_publish",
            "ready_for_agent_prompt_publish",
        )
        for key in optional_false_authorizations:
            if key in accepted_payload and accepted_payload.get(key) is not False:
                errors.append(f"accepted_readiness_authorization_mismatch:{key}")
        if not accepted_forbidden_actions_all_false(accepted_payload):
            errors.append("accepted_readiness_forbidden_actions_not_all_false")
        if provider_root != expected_provider_root:
            errors.append("provider_root_not_ac_accepted_staged_qlib_bin")
        if normalized_root != expected_normalized_root:
            errors.append("normalized_root_not_ac_accepted_candidate_normalized")
    elif requested_target_asof in {"auto", "latest"}:
        errors.append("target_asof_auto_latest_requires_accepted_readiness")

    if not is_relative_to(output_root, PBPR3_OUTPUT_ROOT):
        errors.append("output_root_not_under_pbpr3_isolated_root")
    for role, path in (
        ("provider_root", provider_root),
        ("normalized_root", normalized_root),
        ("output_root", output_root),
    ):
        reason = path_forbidden_reason(path)
        if reason:
            errors.append(f"{role}_{reason}")

    if preflight_report is not None:
        report_allowed = (
            is_relative_to(preflight_report, PBPR3R_EVIDENCE_ROOT)
            or is_relative_to(preflight_report, PBPR3S_EVIDENCE_ROOT)
            or is_relative_to(preflight_report, PBPR3_PARAMETERIZATION_EVIDENCE_ROOT)
            or is_relative_to(preflight_report, output_root)
        )
        if not report_allowed:
            errors.append("preflight_report_not_under_pbpr3r_pbpr3s_pbpr3_parameterization_or_output_root")
        reason = path_forbidden_reason(preflight_report)
        if reason:
            errors.append(f"preflight_report_{reason}")

    required_provider_paths = {
        "calendar": provider_root / "calendars/day.txt",
        "instruments": provider_root / "instruments/all.txt",
        "features": provider_root / "features",
    }
    for key, path in required_provider_paths.items():
        if not path.exists():
            errors.append(f"missing_provider_path:{key}")
    normalized_csv_count = len(list(normalized_root.glob("TW*.csv"))) if normalized_root.exists() else 0
    if normalized_csv_count != 150:
        errors.append(f"normalized_csv_count_not_150:{normalized_csv_count}")
    cal_max = calendar_max(provider_root)
    if cal_max != target_asof:
        errors.append(f"provider_calendar_max_not_target:{cal_max}")

    report = {
        "schema_version": "pbpr3r.modela_no_publish_preflight.v1",
        "created_at": utc_now(),
        "status": "pass" if not errors else "fail",
        "requested_target_asof": requested_target_asof,
        "target_asof": target_asof,
        "target_resolution_mode": target_resolution_mode,
        "accepted_target_asof": accepted_payload.get("target_asof") if accepted_payload else "",
        "accepted_candidate_asof": accepted_payload.get("candidate_asof") if accepted_payload else "",
        "accepted_readiness": rel(accepted_readiness),
        "provider_root": rel(provider_root),
        "normalized_root": rel(normalized_root),
        "output_root": rel(output_root),
        "preflight_report": rel(preflight_report) if preflight_report else "",
        "expected_provider_root": rel(expected_provider_root) if str(expected_provider_root) != "." else "",
        "expected_normalized_root": rel(expected_normalized_root) if str(expected_normalized_root) != "." else "",
        "provider_calendar_max": cal_max,
        "normalized_csv_count": normalized_csv_count,
        "safety_flags": {
            "no_publish": flags.no_publish,
            "no_catalog": flags.no_catalog,
            "no_latest": flags.no_latest,
            "no_target_output": flags.no_target_output,
            "preflight_only": flags.preflight_only,
        },
        "qlib_scoring_executed": False,
        "qlib_scoring_reachable": False,
        "model_inference_input_built": False,
        "score_job_built": False,
        "model_signal_artifact_built": False,
        "provider_network_pull": False,
        "publish_or_latest_write": False,
        "target_output_generated": False,
        "errors": errors,
        "warnings": warnings,
    }
    return report


def pbpr3_artifact_paths(output_root: Path) -> dict[str, str]:
    output_root = resolve_repo_path(output_root)
    return {
        "path_containment_validator_report": rel(output_root / "path_containment_validator_report.json"),
        "model_inference_input_manifest": rel(output_root / "model_inference_input_manifest.json"),
        "score_job_manifest": rel(output_root / "score_job_manifest.json"),
        "model_signal_artifact_no_publish": rel(output_root / "model_signal_artifact_no_publish.json"),
        "validator_report": rel(output_root / "validator_report.json"),
        "static_safety_audit": rel(output_root / "static_safety_audit.json"),
        "forbidden_action_audit": rel(output_root / "forbidden_action_audit.json"),
        "artifact_manifest": rel(output_root / "artifact_manifest.json"),
        "execution_report_supporting_summary": rel(output_root / "execution_report_supporting_summary.json"),
    }


def pbpr3_contained_future_output_paths(output_root: Path) -> dict[str, str]:
    output_root = resolve_repo_path(output_root)
    base = output_root / "planned_future_outputs"
    return {
        "model_inference_input_manifest": rel(base / "model_inference_input_manifest.json"),
        "model_inference_input_frame": rel(base / "model_inference_input_frame.csv"),
        "model_inference_input_schema": rel(base / "model_inference_input_schema.json"),
        "score_job_manifest": rel(base / "score_job_manifest.json"),
        "score_job_raw_scores": rel(base / "score_job_raw_scores.csv"),
        "score_job_rank_audit": rel(base / "score_job_rank_audit.csv"),
        "model_signal_artifact_manifest": rel(base / "model_signal_artifact_manifest.json"),
        "model_signal_signals": rel(base / "model_signal_signals.csv"),
        "model_signal_schema": rel(base / "model_signal_schema.json"),
        "validator_report": rel(base / "validator_report.json"),
    }


def validate_planned_output_paths(
    *,
    output_root: Path,
    planned_artifacts: dict[str, str],
) -> list[str]:
    errors: list[str] = []
    output_root = resolve_repo_path(output_root)
    for key, value in planned_artifacts.items():
        path = resolve_repo_path(value)
        if not is_relative_to(path, output_root):
            errors.append(f"planned_artifact_not_under_output_root:{key}")
        reason = path_forbidden_reason(path)
        if reason:
            errors.append(f"planned_artifact_{key}_{reason}")
    return errors


def validate_adapter_plan(
    *,
    target_asof: str,
    accepted_readiness: Path,
    provider_root: Path,
    normalized_root: Path,
    output_root: Path,
    flags: SafetyFlags,
    adapter_plan_report: Path | None = None,
) -> dict[str, Any]:
    preflight = validate_preflight(
        target_asof=target_asof,
        accepted_readiness=accepted_readiness,
        provider_root=provider_root,
        normalized_root=normalized_root,
        output_root=output_root,
        flags=flags,
        preflight_report=None,
    )
    errors = list(preflight["errors"])
    output_root = resolve_repo_path(output_root)
    adapter_plan_report = resolve_repo_path(adapter_plan_report) if adapter_plan_report else None
    if adapter_plan_report is not None:
        report_allowed = is_relative_to(adapter_plan_report, PBPR3S_EVIDENCE_ROOT) or is_relative_to(
            adapter_plan_report, output_root
        )
        if not report_allowed:
            errors.append("adapter_plan_report_not_under_pbpr3s_or_output_root")
        reason = path_forbidden_reason(adapter_plan_report)
        if reason:
            errors.append(f"adapter_plan_report_{reason}")

    artifact_paths = pbpr3_artifact_paths(output_root)
    for key, value in artifact_paths.items():
        path = resolve_repo_path(value)
        if not is_relative_to(path, output_root):
            errors.append(f"planned_artifact_not_under_output_root:{key}")
        reason = path_forbidden_reason(path)
        if reason:
            errors.append(f"planned_artifact_{key}_{reason}")

    future_steps = [
        {
            "step": "pbpr3r_preflight",
            "enabled_in_pbpr3s": True,
            "must_pass_before": [
                "model_inference_input_build",
                "score_job_build",
                "model_signal_artifact_build",
                "validator_run",
            ],
            "output_path": artifact_paths["path_containment_validator_report"],
        },
        {
            "step": "model_inference_input_build",
            "enabled_in_pbpr3s": False,
            "future_reviewed_rerun_only": True,
            "output_path": artifact_paths["model_inference_input_manifest"],
        },
        {
            "step": "score_job_build",
            "enabled_in_pbpr3s": False,
            "future_reviewed_rerun_only": True,
            "output_path": artifact_paths["score_job_manifest"],
        },
        {
            "step": "model_signal_artifact_no_publish_build",
            "enabled_in_pbpr3s": False,
            "future_reviewed_rerun_only": True,
            "output_path": artifact_paths["model_signal_artifact_no_publish"],
        },
        {
            "step": "validator_run",
            "enabled_in_pbpr3s": False,
            "future_reviewed_rerun_only": True,
            "output_path": artifact_paths["validator_report"],
        },
    ]

    return {
        "schema_version": "pbpr3s.modela_scoring_adapter_plan.v1",
        "created_at": utc_now(),
        "status": "pass" if not errors else "fail",
        "target_asof": target_asof,
        "preflight_status": preflight["status"],
        "accepted_readiness": preflight["accepted_readiness"],
        "provider_root": preflight["provider_root"],
        "normalized_root": preflight["normalized_root"],
        "output_root": rel(output_root),
        "adapter_plan_report": rel(adapter_plan_report) if adapter_plan_report else "",
        "planned_artifacts": artifact_paths,
        "planned_execution_order": future_steps,
        "future_adapter_contract": {
            "must_run_preflight_before_build_or_scoring": True,
            "must_consume_only_accepted_provider_root": True,
            "must_consume_only_accepted_normalized_root": True,
            "must_write_only_planned_artifacts_under_output_root": True,
            "model_inference_input_manifest_path": artifact_paths["model_inference_input_manifest"],
            "score_job_manifest_path": artifact_paths["score_job_manifest"],
            "model_signal_artifact_no_publish_path": artifact_paths["model_signal_artifact_no_publish"],
            "validator_report_path": artifact_paths["validator_report"],
            "no_publish": flags.no_publish,
            "no_catalog": flags.no_catalog,
            "no_latest": flags.no_latest,
            "no_target_output": flags.no_target_output,
            "preflight_only_in_pbpr3s": flags.preflight_only,
        },
        "execution_flags": {
            "adapter_plan_only": True,
            "real_qlib_scoring_executed": False,
            "model_inference_input_built": False,
            "score_job_built": False,
            "model_signal_artifact_built": False,
            "provider_network_pull": False,
            "publish_or_latest_write": False,
            "target_output_generated": False,
        },
        "blocked_runtime_actions": [
            "real qlib scoring execution",
            "real ModelInferenceInput build",
            "real ScoreJob build",
            "real ModelSignalArtifact build",
            "provider/network pull",
            "provider publish",
            "accepted/latest switch",
            "qlib refresh",
            "readonly/Agent publish",
            "monitor/broker/order/target output",
        ],
        "errors": errors,
        "warnings": preflight["warnings"],
    }


def validate_contained_adapter_contract(
    *,
    target_asof: str,
    accepted_readiness: Path,
    provider_root: Path,
    normalized_root: Path,
    output_root: Path,
    flags: SafetyFlags,
    contained_contract_report: Path | None = None,
    planned_artifact_overrides: dict[str, str | Path] | None = None,
) -> dict[str, Any]:
    preflight = validate_preflight(
        target_asof=target_asof,
        accepted_readiness=accepted_readiness,
        provider_root=provider_root,
        normalized_root=normalized_root,
        output_root=output_root,
        flags=flags,
        preflight_report=None,
    )
    errors = list(preflight["errors"])
    output_root = resolve_repo_path(output_root)
    contained_contract_report = (
        resolve_repo_path(contained_contract_report) if contained_contract_report else None
    )
    if contained_contract_report is not None:
        report_allowed = is_relative_to(contained_contract_report, PBPR3U_EVIDENCE_ROOT) or is_relative_to(
            contained_contract_report, output_root
        )
        if not report_allowed:
            errors.append("contained_contract_report_not_under_pbpr3u_or_output_root")
        reason = path_forbidden_reason(contained_contract_report)
        if reason:
            errors.append(f"contained_contract_report_{reason}")

    planned_artifacts = pbpr3_contained_future_output_paths(output_root)
    if planned_artifact_overrides:
        planned_artifacts.update(
            {key: rel(resolve_repo_path(value)) for key, value in planned_artifact_overrides.items()}
        )
    errors.extend(validate_planned_output_paths(output_root=output_root, planned_artifacts=planned_artifacts))

    future_steps = [
        {
            "step": "contract_and_path_containment_validation",
            "enabled_in_pbpr3u": True,
            "fixture_or_static_only": True,
            "output_path": rel(contained_contract_report) if contained_contract_report else "",
        },
        {
            "step": "model_inference_input_build",
            "enabled_in_pbpr3u": False,
            "future_reviewed_rerun_only": True,
            "requires_explicit_later_gate": True,
            "output_path": planned_artifacts["model_inference_input_manifest"],
        },
        {
            "step": "score_job_build_and_qlib_scoring",
            "enabled_in_pbpr3u": False,
            "future_reviewed_rerun_only": True,
            "requires_explicit_later_gate": True,
            "output_path": planned_artifacts["score_job_manifest"],
        },
        {
            "step": "model_signal_artifact_no_publish_build",
            "enabled_in_pbpr3u": False,
            "future_reviewed_rerun_only": True,
            "requires_explicit_later_gate": True,
            "output_path": planned_artifacts["model_signal_artifact_manifest"],
        },
        {
            "step": "validator_run_on_future_contained_artifacts",
            "enabled_in_pbpr3u": False,
            "future_reviewed_rerun_only": True,
            "requires_explicit_later_gate": True,
            "output_path": planned_artifacts["validator_report"],
        },
    ]

    return {
        "schema_version": "pbpr3u.contained_modela_scoring_build_adapter_contract.v1",
        "created_at": utc_now(),
        "status": "pass" if not errors else "fail",
        "phase": "PBPR3_U_CONTAINED_MODELA_SCORING_BUILD_ADAPTER_REPAIR",
        "target_asof": target_asof,
        "preflight_status": preflight["status"],
        "accepted_readiness": preflight["accepted_readiness"],
        "provider_root": preflight["provider_root"],
        "normalized_root": preflight["normalized_root"],
        "output_root": rel(output_root),
        "contained_contract_report": rel(contained_contract_report) if contained_contract_report else "",
        "required_runtime_parameters": [
            "target_asof",
            "provider_root",
            "normalized_root",
            "output_root",
            "no_publish",
            "no_catalog",
            "no_latest",
            "no_target_output",
        ],
        "required_safety_flags": {
            "no_publish": flags.no_publish,
            "no_catalog": flags.no_catalog,
            "no_latest": flags.no_latest,
            "no_target_output": flags.no_target_output,
            "preflight_only_for_pbpr3u_contract_mode": flags.preflight_only,
        },
        "planned_future_outputs": planned_artifacts,
        "planned_execution_order": future_steps,
        "default_runtime_reachability": {
            "real_qlib_scoring_reachable": False,
            "subprocess_reachable": False,
            "build_tw_model_inference_input_reachable": False,
            "run_tw_model_score_job_reachable": False,
            "validate_tw_score_job_on_real_artifacts_reachable": False,
            "model_inference_input_build_reachable": False,
            "score_job_build_reachable": False,
            "model_signal_artifact_build_reachable": False,
            "provider_network_reachable": False,
            "publish_latest_reachable": False,
            "target_output_reachable": False,
        },
        "future_rerun_contract": {
            "must_consume_only_accepted_provider_root": True,
            "must_consume_only_accepted_normalized_root": True,
            "must_write_only_under_output_root": True,
            "must_not_write_legacy_canonical_artifacts_catalog": True,
            "must_not_write_latest_publish_readonly_agent_monitor_broker_order_or_target_paths": True,
            "must_keep_no_publish": True,
            "must_keep_no_catalog": True,
            "must_keep_no_latest": True,
            "must_keep_no_target_output": True,
            "production_allowed": False,
        },
        "fixture_or_mock_only": True,
        "real_artifacts_built": {
            "model_inference_input": False,
            "score_job": False,
            "model_signal_artifact": False,
        },
        "errors": errors,
        "warnings": preflight["warnings"],
    }


def contained_adapter_path_containment_matrix(
    *,
    accepted_readiness: Path,
    provider_root: Path,
    normalized_root: Path,
    output_root: Path,
    flags: SafetyFlags,
) -> dict[str, Any]:
    cases = [
        {
            "case": "accept_ac_roots_and_pbpr3_output_root",
            "expected_status": "pass",
            "kwargs": {},
        },
        {
            "case": "reject_legacy_provider_root",
            "expected_status": "fail",
            "kwargs": {
                "provider_root": ROOT
                / "qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin"
            },
        },
        {
            "case": "reject_legacy_artifacts_output_root",
            "expected_status": "fail",
            "kwargs": {"output_root": ROOT / "data_tw/artifacts/score_jobs/e4_frozen_qlib_2018_2022"},
        },
        {
            "case": "reject_catalog_output_root",
            "expected_status": "fail",
            "kwargs": {"output_root": ROOT / "data_tw/catalog/pbpr3u"},
        },
        {
            "case": "reject_latest_planned_artifact_path",
            "expected_status": "fail",
            "kwargs": {
                "planned_artifact_overrides": {
                    "score_job_manifest": output_root / "planned_future_outputs/latest/score_job_manifest.json"
                }
            },
        },
        {
            "case": "reject_target_position_planned_artifact_path",
            "expected_status": "fail",
            "kwargs": {
                "planned_artifact_overrides": {
                    "model_signal_artifact_manifest": output_root
                    / "planned_future_outputs/target_position/model_signal_manifest.json"
                }
            },
        },
    ]
    results = []
    for case in cases:
        kwargs = {
            "target_asof": "2026-07-08",
            "accepted_readiness": accepted_readiness,
            "provider_root": provider_root,
            "normalized_root": normalized_root,
            "output_root": output_root,
            "flags": flags,
        }
        kwargs.update(case["kwargs"])
        report = validate_contained_adapter_contract(**kwargs)
        results.append(
            {
                "case": case["case"],
                "expected_status": case["expected_status"],
                "observed_status": report["status"],
                "passed": report["status"] == case["expected_status"],
                "errors": report["errors"],
            }
        )
    return {
        "schema_version": "pbpr3u.path_containment_matrix.v1",
        "created_at": utc_now(),
        "status": "pass" if all(row["passed"] for row in results) else "fail",
        "target_asof": "2026-07-08",
        "cases": results,
    }


def validate_contained_real_runtime_contract(
    *,
    target_asof: str,
    accepted_readiness: Path,
    provider_root: Path,
    normalized_root: Path,
    output_root: Path,
    flags: SafetyFlags,
    runtime_contract_report: Path | None = None,
    planned_runtime_overrides: dict[str, str | Path] | None = None,
) -> dict[str, Any]:
    preflight = validate_preflight(
        target_asof=target_asof,
        accepted_readiness=accepted_readiness,
        provider_root=provider_root,
        normalized_root=normalized_root,
        output_root=output_root,
        flags=flags,
        preflight_report=None,
    )
    errors = list(preflight["errors"])
    output_root = resolve_repo_path(output_root)
    runtime_contract_report = resolve_repo_path(runtime_contract_report) if runtime_contract_report else None
    if runtime_contract_report is not None:
        report_allowed = is_relative_to(runtime_contract_report, PBPR3W_EVIDENCE_ROOT) or is_relative_to(
            runtime_contract_report, output_root
        )
        if not report_allowed:
            errors.append("runtime_contract_report_not_under_pbpr3w_or_output_root")
        reason = path_forbidden_reason(runtime_contract_report)
        if reason:
            errors.append(f"runtime_contract_report_{reason}")

    runtime_config = make_modela_runtime_config(
        target_asof=target_asof,
        provider_root=provider_root,
        normalized_root=normalized_root,
        output_root=output_root,
        no_publish=flags.no_publish,
        no_catalog=flags.no_catalog,
        no_latest=flags.no_latest,
        no_target_output=flags.no_target_output,
        allow_real_execution=False,
    )
    runtime_report = validate_modela_runtime_config(runtime_config, run_id="pbpr3w_fixture")
    errors.extend(runtime_report["errors"])
    runtime_paths = dict(runtime_report["runtime_paths"])
    if planned_runtime_overrides:
        runtime_paths.update(
            {key: rel(resolve_repo_path(value)) for key, value in planned_runtime_overrides.items()}
        )
    for key, value in runtime_paths.items():
        path = resolve_repo_path(value)
        if not is_relative_to(path, output_root):
            errors.append(f"runtime_path_not_under_output_root:{key}")
        reason = path_forbidden_reason(path)
        if reason:
            errors.append(f"runtime_path_{key}_{reason}")

    future_steps = [
        {
            "step": "runtime_config_contract_validation",
            "enabled_in_pbpr3w": True,
            "fixture_or_static_only": True,
            "output_path": rel(runtime_contract_report) if runtime_contract_report else "",
        },
        {
            "step": "model_inference_input_real_build",
            "enabled_in_pbpr3w": False,
            "future_reviewed_rerun_only": True,
            "requires_allow_real_execution": True,
            "output_path": runtime_paths["model_inference_input_manifest"],
        },
        {
            "step": "contained_qlib_scoring_and_score_job_real_build",
            "enabled_in_pbpr3w": False,
            "future_reviewed_rerun_only": True,
            "requires_allow_real_execution": True,
            "output_path": runtime_paths["score_job_manifest"],
        },
        {
            "step": "model_signal_artifact_no_publish_real_build",
            "enabled_in_pbpr3w": False,
            "future_reviewed_rerun_only": True,
            "requires_allow_real_execution": True,
            "output_path": runtime_paths["model_signal_manifest"],
        },
        {
            "step": "validator_run_on_contained_artifacts",
            "enabled_in_pbpr3w": False,
            "future_reviewed_rerun_only": True,
            "requires_contained_artifact_dirs": True,
            "output_path": runtime_paths["pipeline_validation"],
        },
    ]

    return {
        "schema_version": "pbpr3w.contained_real_runtime_contract.v1",
        "created_at": utc_now(),
        "status": "pass" if not errors else "fail",
        "phase": "PBPR3_W_CONTAINED_REAL_RUNTIME_REPAIR",
        "target_asof": target_asof,
        "preflight_status": preflight["status"],
        "accepted_readiness": preflight["accepted_readiness"],
        "provider_root": preflight["provider_root"],
        "normalized_root": preflight["normalized_root"],
        "output_root": rel(output_root),
        "runtime_contract_report": rel(runtime_contract_report) if runtime_contract_report else "",
        "runtime_config_contract": runtime_report,
        "required_runtime_parameters": [
            "target_asof",
            "provider_root",
            "normalized_root",
            "output_root",
            "no_publish",
            "no_catalog",
            "no_latest",
            "no_target_output",
        ],
        "runtime_paths": runtime_paths,
        "planned_execution_order": future_steps,
        "runtime_reachability": {
            "pbpr3w_contract_only": True,
            "allow_real_execution_default": False,
            "real_qlib_scoring_executed": False,
            "model_inference_input_build_executed": False,
            "score_job_build_executed": False,
            "model_signal_artifact_build_executed": False,
            "validator_on_real_artifacts_executed": False,
            "subprocess_legacy_scoring_required": False,
            "contained_direct_qlib_runtime_available_for_later_gate": True,
        },
        "future_rerun_contract": {
            "must_pass_this_contract_first": True,
            "must_consume_only_accepted_provider_root": True,
            "must_consume_only_accepted_normalized_root": True,
            "must_write_only_under_output_root": True,
            "must_keep_no_publish": True,
            "must_keep_no_catalog": True,
            "must_keep_no_latest": True,
            "must_keep_no_target_output": True,
            "must_use_allow_real_execution_only_in_later_reviewed_rerun": True,
            "production_allowed": False,
        },
        "errors": errors,
        "warnings": preflight["warnings"],
    }


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="PBPR3-safe Model A no-publish dry-run preflight. Does not run qlib scoring."
    )
    parser.add_argument("--target-asof", required=True)
    parser.add_argument("--accepted-readiness", default=str(DEFAULT_ACCEPTED_READINESS))
    parser.add_argument("--provider-root", required=True)
    parser.add_argument("--normalized-root", required=True)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--preflight-report", default=None)
    parser.add_argument("--adapter-plan-report", default=None)
    parser.add_argument("--contained-adapter-contract-report", default=None)
    parser.add_argument("--contained-runtime-contract-report", default=None)
    parser.add_argument("--no-publish", action="store_true")
    parser.add_argument("--no-catalog", action="store_true")
    parser.add_argument("--no-latest", action="store_true")
    parser.add_argument("--no-target-output", action="store_true")
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--adapter-plan-only", action="store_true")
    parser.add_argument("--contained-adapter-contract-only", action="store_true")
    parser.add_argument("--contained-runtime-contract-only", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> int:
    args = build_arg_parser().parse_args()
    flags = SafetyFlags(
        no_publish=args.no_publish,
        no_catalog=args.no_catalog,
        no_latest=args.no_latest,
        no_target_output=args.no_target_output,
        preflight_only=args.preflight_only,
    )
    if args.contained_runtime_contract_only:
        report = validate_contained_real_runtime_contract(
            target_asof=args.target_asof,
            accepted_readiness=Path(args.accepted_readiness),
            provider_root=Path(args.provider_root),
            normalized_root=Path(args.normalized_root),
            output_root=Path(args.output_root),
            runtime_contract_report=Path(args.contained_runtime_contract_report)
            if args.contained_runtime_contract_report
            else None,
            flags=flags,
        )
        if args.contained_runtime_contract_report:
            write_json(resolve_repo_path(args.contained_runtime_contract_report), report)
    elif args.contained_adapter_contract_only:
        report = validate_contained_adapter_contract(
            target_asof=args.target_asof,
            accepted_readiness=Path(args.accepted_readiness),
            provider_root=Path(args.provider_root),
            normalized_root=Path(args.normalized_root),
            output_root=Path(args.output_root),
            contained_contract_report=Path(args.contained_adapter_contract_report)
            if args.contained_adapter_contract_report
            else None,
            flags=flags,
        )
        if args.contained_adapter_contract_report:
            write_json(resolve_repo_path(args.contained_adapter_contract_report), report)
    elif args.adapter_plan_only:
        report = validate_adapter_plan(
            target_asof=args.target_asof,
            accepted_readiness=Path(args.accepted_readiness),
            provider_root=Path(args.provider_root),
            normalized_root=Path(args.normalized_root),
            output_root=Path(args.output_root),
            adapter_plan_report=Path(args.adapter_plan_report) if args.adapter_plan_report else None,
            flags=flags,
        )
        if args.adapter_plan_report:
            write_json(resolve_repo_path(args.adapter_plan_report), report)
    else:
        report = validate_preflight(
            target_asof=args.target_asof,
            accepted_readiness=Path(args.accepted_readiness),
            provider_root=Path(args.provider_root),
            normalized_root=Path(args.normalized_root),
            output_root=Path(args.output_root),
            preflight_report=Path(args.preflight_report) if args.preflight_report else None,
            flags=flags,
        )
        if args.preflight_report:
            write_json(resolve_repo_path(args.preflight_report), report)
    if args.json:
        print(json.dumps(report, ensure_ascii=True, indent=2))
    else:
        print(f"{report['status']} {report['target_asof']} {report['output_root']}")
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
