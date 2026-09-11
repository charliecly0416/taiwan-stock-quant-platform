from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = ROOT / "scripts/run_tw_pbpr3_modela_no_publish_dry_run.py"
spec = importlib.util.spec_from_file_location("pbpr3_modela_entrypoint", SCRIPT_PATH)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
sys.modules[spec.name] = module
spec.loader.exec_module(module)


ACCEPTED = (
    ROOT
    / "data_tw/experiments/provider_bridge_productionization/"
    "pbpr2a_ac_provider_candidate_readiness_review/provider_candidate_readiness_accepted.json"
)
PBPR2R_ACCEPTED = (
    ROOT
    / "data_tw/experiments/provider_bridge_productionization/"
    "pbpr2r_20260720_provider_candidate_acceptance_and_daily_auto_gate_design_no_publish/"
    "provider_candidate_readiness_accepted.json"
)
PROVIDER = (
    ROOT
    / "data_tw/experiments/provider_bridge_productionization/"
    "pbpr2a_w_proxy_provider_only_rerun/pbpr2a_w_yahoo_proxy_provider_only_20260708/staged_qlib_bin"
)
PBPR2R_PROVIDER = (
    ROOT
    / "data_tw/experiments/provider_bridge_productionization/"
    "pbpr2_20260720_target_asof_provider_bridge_candidate/"
    "pbpr2_yahoo_proxy_provider_only_20260720/staged_qlib_bin"
)
NORMALIZED = (
    ROOT
    / "data_tw/experiments/provider_bridge_productionization/"
    "pbpr2a_w_proxy_provider_only_rerun/pbpr2a_w_yahoo_proxy_provider_only_20260708/candidate_normalized"
)
PBPR2R_NORMALIZED = (
    ROOT
    / "data_tw/experiments/provider_bridge_productionization/"
    "pbpr2_20260720_target_asof_provider_bridge_candidate/"
    "pbpr2_yahoo_proxy_provider_only_20260720/candidate_normalized"
)
PBPR3_ROOT = (
    ROOT
    / "data_tw/experiments/provider_bridge_productionization/"
    "pbpr3_target_asof_model_a_no_publish_dry_run"
)
PBPR3_PARAMETERIZATION_ROOT = (
    ROOT
    / "data_tw/experiments/provider_bridge_productionization/"
    "pbpr3_20260720_safe_entrypoint_parameterization_latest_target"
)


def safe_flags():
    return module.SafetyFlags(
        no_publish=True,
        no_catalog=True,
        no_latest=True,
        no_target_output=True,
        preflight_only=True,
    )


def test_preflight_accepts_ac_lineage_and_pbpr3_root() -> None:
    report = module.validate_preflight(
        target_asof="2026-07-08",
        accepted_readiness=ACCEPTED,
        provider_root=PROVIDER,
        normalized_root=NORMALIZED,
        output_root=PBPR3_ROOT,
        flags=safe_flags(),
    )
    assert report["status"] == "pass"
    assert report["provider_calendar_max"] == "2026-07-08"
    assert report["normalized_csv_count"] == 150
    assert report["qlib_scoring_executed"] is False
    assert report["qlib_scoring_reachable"] is False
    assert report["model_signal_artifact_built"] is False


def test_preflight_accepts_pbpr2r_explicit_20260720_lineage() -> None:
    report = module.validate_preflight(
        target_asof="2026-07-20",
        accepted_readiness=PBPR2R_ACCEPTED,
        provider_root=PBPR2R_PROVIDER,
        normalized_root=PBPR2R_NORMALIZED,
        output_root=PBPR3_ROOT / "pbpr2r_explicit_20260720",
        preflight_report=PBPR3_PARAMETERIZATION_ROOT / "pbpr2r_20260720_preflight_report.json",
        flags=safe_flags(),
    )
    assert report["status"] == "pass"
    assert report["requested_target_asof"] == "2026-07-20"
    assert report["target_asof"] == "2026-07-20"
    assert report["target_resolution_mode"] == "explicit"
    assert report["accepted_target_asof"] == "2026-07-20"
    assert report["accepted_candidate_asof"] == "2026-07-20"
    assert report["provider_calendar_max"] == "2026-07-20"
    assert report["normalized_csv_count"] == 150


def test_preflight_resolves_pbpr2r_auto_and_latest_from_accepted_readiness() -> None:
    for requested in ("auto", "latest"):
        report = module.validate_preflight(
            target_asof=requested,
            accepted_readiness=PBPR2R_ACCEPTED,
            provider_root=PBPR2R_PROVIDER,
            normalized_root=PBPR2R_NORMALIZED,
            output_root=PBPR3_ROOT / f"pbpr2r_{requested}_20260720",
            preflight_report=PBPR3_PARAMETERIZATION_ROOT / f"pbpr2r_{requested}_preflight_report.json",
            flags=safe_flags(),
        )
        assert report["status"] == "pass", requested
        assert report["requested_target_asof"] == requested
        assert report["target_asof"] == "2026-07-20"
        assert report["target_resolution_mode"] == requested
        assert report["accepted_target_asof"] == "2026-07-20"
        assert report["accepted_candidate_asof"] == "2026-07-20"


def test_preflight_rejects_non_ac_provider_root() -> None:
    report = module.validate_preflight(
        target_asof="2026-07-08",
        accepted_readiness=ACCEPTED,
        provider_root=ROOT / "qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin",
        normalized_root=NORMALIZED,
        output_root=PBPR3_ROOT,
        flags=safe_flags(),
    )
    assert report["status"] == "fail"
    assert "provider_root_not_ac_accepted_staged_qlib_bin" in report["errors"]


def test_preflight_rejects_out_of_scope_output_root() -> None:
    report = module.validate_preflight(
        target_asof="2026-07-08",
        accepted_readiness=ACCEPTED,
        provider_root=PROVIDER,
        normalized_root=NORMALIZED,
        output_root=ROOT / "data_tw/artifacts/score_jobs/e4_frozen_qlib_2018_2022",
        flags=safe_flags(),
    )
    assert report["status"] == "fail"
    assert "output_root_not_under_pbpr3_isolated_root" in report["errors"]
    assert any(error.startswith("output_root_forbidden_path_fragment:data_tw/artifacts") for error in report["errors"])


def test_preflight_requires_all_safety_flags() -> None:
    report = module.validate_preflight(
        target_asof="2026-07-08",
        accepted_readiness=ACCEPTED,
        provider_root=PROVIDER,
        normalized_root=NORMALIZED,
        output_root=PBPR3_ROOT,
        flags=module.SafetyFlags(
            no_publish=False,
            no_catalog=True,
            no_latest=True,
            no_target_output=True,
            preflight_only=True,
        ),
    )
    assert report["status"] == "fail"
    assert "required_safety_flag_missing:no_publish" in report["errors"]


def test_adapter_plan_declares_only_pbpr3_output_artifacts() -> None:
    report = module.validate_adapter_plan(
        target_asof="2026-07-08",
        accepted_readiness=ACCEPTED,
        provider_root=PROVIDER,
        normalized_root=NORMALIZED,
        output_root=PBPR3_ROOT / "rerun_after_pbpr3s",
        flags=safe_flags(),
    )
    assert report["status"] == "pass"
    assert report["preflight_status"] == "pass"
    assert report["execution_flags"]["adapter_plan_only"] is True
    assert report["execution_flags"]["real_qlib_scoring_executed"] is False
    assert report["execution_flags"]["model_inference_input_built"] is False
    assert report["execution_flags"]["score_job_built"] is False
    assert report["execution_flags"]["model_signal_artifact_built"] is False
    assert [step["step"] for step in report["planned_execution_order"]] == [
        "pbpr3r_preflight",
        "model_inference_input_build",
        "score_job_build",
        "model_signal_artifact_no_publish_build",
        "validator_run",
    ]
    assert report["planned_execution_order"][0]["enabled_in_pbpr3s"] is True
    assert report["planned_execution_order"][0]["output_path"].endswith(
        "path_containment_validator_report.json"
    )
    for step in report["planned_execution_order"][1:]:
        assert step["enabled_in_pbpr3s"] is False
        assert step["future_reviewed_rerun_only"] is True
    for path in report["planned_artifacts"].values():
        assert path.startswith(
            "data_tw/experiments/provider_bridge_productionization/"
            "pbpr3_target_asof_model_a_no_publish_dry_run/rerun_after_pbpr3s/"
        )
    assert report["future_adapter_contract"]["model_inference_input_manifest_path"].endswith(
        "model_inference_input_manifest.json"
    )
    assert report["planned_artifacts"]["model_inference_input_manifest"].endswith(
        "model_inference_input_manifest.json"
    )
    assert report["planned_artifacts"]["score_job_manifest"].endswith("score_job_manifest.json")
    assert report["planned_artifacts"]["model_signal_artifact_no_publish"].endswith(
        "model_signal_artifact_no_publish.json"
    )


def test_adapter_plan_rejects_report_outside_pbpr3s_or_output_root() -> None:
    report = module.validate_adapter_plan(
        target_asof="2026-07-08",
        accepted_readiness=ACCEPTED,
        provider_root=PROVIDER,
        normalized_root=NORMALIZED,
        output_root=PBPR3_ROOT / "rerun_after_pbpr3s",
        adapter_plan_report=ROOT / "tmp/pbpr3s_adapter_plan.json",
        flags=safe_flags(),
    )
    assert report["status"] == "fail"
    assert "adapter_plan_report_not_under_pbpr3s_or_output_root" in report["errors"]


def test_adapter_plan_rejects_missing_preflight_only_flag() -> None:
    report = module.validate_adapter_plan(
        target_asof="2026-07-08",
        accepted_readiness=ACCEPTED,
        provider_root=PROVIDER,
        normalized_root=NORMALIZED,
        output_root=PBPR3_ROOT / "rerun_after_pbpr3s",
        flags=module.SafetyFlags(
            no_publish=True,
            no_catalog=True,
            no_latest=True,
            no_target_output=True,
            preflight_only=False,
        ),
    )
    assert report["status"] == "fail"
    assert "preflight_only_required_in_pbpr3r" in report["errors"]


def test_contained_adapter_contract_accepts_ac_roots_and_required_flags() -> None:
    report = module.validate_contained_adapter_contract(
        target_asof="2026-07-08",
        accepted_readiness=ACCEPTED,
        provider_root=PROVIDER,
        normalized_root=NORMALIZED,
        output_root=PBPR3_ROOT / "rerun_after_pbpr3u",
        contained_contract_report=(
            ROOT
            / "data_tw/experiments/provider_bridge_productionization/"
            "pbpr3u_contained_modela_scoring_build_adapter_repair/adapter_contract_summary.json"
        ),
        flags=safe_flags(),
    )
    assert report["status"] == "pass"
    assert report["fixture_or_mock_only"] is True
    assert report["real_artifacts_built"] == {
        "model_inference_input": False,
        "score_job": False,
        "model_signal_artifact": False,
    }
    assert report["default_runtime_reachability"]["real_qlib_scoring_reachable"] is False
    assert report["default_runtime_reachability"]["subprocess_reachable"] is False
    assert report["default_runtime_reachability"]["build_tw_model_inference_input_reachable"] is False
    assert report["default_runtime_reachability"]["run_tw_model_score_job_reachable"] is False
    assert report["default_runtime_reachability"]["validate_tw_score_job_on_real_artifacts_reachable"] is False
    for path in report["planned_future_outputs"].values():
        assert path.startswith(
            "data_tw/experiments/provider_bridge_productionization/"
            "pbpr3_target_asof_model_a_no_publish_dry_run/rerun_after_pbpr3u/"
        )


def test_contained_adapter_contract_rejects_legacy_provider_root() -> None:
    report = module.validate_contained_adapter_contract(
        target_asof="2026-07-08",
        accepted_readiness=ACCEPTED,
        provider_root=ROOT / "qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin",
        normalized_root=NORMALIZED,
        output_root=PBPR3_ROOT / "rerun_after_pbpr3u",
        flags=safe_flags(),
    )
    assert report["status"] == "fail"
    assert "provider_root_not_ac_accepted_staged_qlib_bin" in report["errors"]


def test_contained_adapter_contract_rejects_legacy_output_roots() -> None:
    for bad_root, expected in [
        (
            ROOT / "data_tw/canonical/model_inference_input/e4_frozen_qlib_2018_2022",
            "output_root_forbidden_path_fragment:data_tw/canonical",
        ),
        (
            ROOT / "data_tw/artifacts/signals/e4_frozen_qlib_2018_2022",
            "output_root_forbidden_path_fragment:data_tw/artifacts",
        ),
        (ROOT / "data_tw/catalog/pbpr3u", "output_root_forbidden_path_part:catalog"),
    ]:
        report = module.validate_contained_adapter_contract(
            target_asof="2026-07-08",
            accepted_readiness=ACCEPTED,
            provider_root=PROVIDER,
            normalized_root=NORMALIZED,
            output_root=bad_root,
            flags=safe_flags(),
        )
        assert report["status"] == "fail"
        assert "output_root_not_under_pbpr3_isolated_root" in report["errors"]
        assert expected in report["errors"]


def test_contained_adapter_contract_rejects_forbidden_planned_paths() -> None:
    forbidden_parts = [
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
    ]
    for part in forbidden_parts:
        report = module.validate_contained_adapter_contract(
            target_asof="2026-07-08",
            accepted_readiness=ACCEPTED,
            provider_root=PROVIDER,
            normalized_root=NORMALIZED,
            output_root=PBPR3_ROOT / "rerun_after_pbpr3u",
            flags=safe_flags(),
            planned_artifact_overrides={
                "score_job_manifest": PBPR3_ROOT
                / "rerun_after_pbpr3u"
                / "planned_future_outputs"
                / part
                / "score_job_manifest.json"
            },
        )
        assert report["status"] == "fail", part
        assert any("planned_artifact_score_job_manifest_forbidden_path_part" in error for error in report["errors"])


def test_contained_adapter_contract_rejects_missing_safety_flags() -> None:
    report = module.validate_contained_adapter_contract(
        target_asof="2026-07-08",
        accepted_readiness=ACCEPTED,
        provider_root=PROVIDER,
        normalized_root=NORMALIZED,
        output_root=PBPR3_ROOT / "rerun_after_pbpr3u",
        flags=module.SafetyFlags(
            no_publish=True,
            no_catalog=True,
            no_latest=False,
            no_target_output=False,
            preflight_only=True,
        ),
    )
    assert report["status"] == "fail"
    assert "required_safety_flag_missing:no_latest" in report["errors"]
    assert "required_safety_flag_missing:no_target_output" in report["errors"]


def test_contained_adapter_contract_rejects_non_target_asof() -> None:
    report = module.validate_contained_adapter_contract(
        target_asof="2026-07-09",
        accepted_readiness=ACCEPTED,
        provider_root=PROVIDER,
        normalized_root=NORMALIZED,
        output_root=PBPR3_ROOT / "rerun_after_pbpr3u",
        flags=safe_flags(),
    )
    assert report["status"] == "fail"
    assert "accepted_readiness_target_asof_mismatch" in report["errors"]
    assert "accepted_readiness_candidate_asof_mismatch" in report["errors"]


def test_contained_real_runtime_contract_accepts_and_plans_pbpr3w_paths() -> None:
    report = module.validate_contained_real_runtime_contract(
        target_asof="2026-07-08",
        accepted_readiness=ACCEPTED,
        provider_root=PROVIDER,
        normalized_root=NORMALIZED,
        output_root=PBPR3_ROOT / "rerun_after_pbpr3w",
        runtime_contract_report=(
            ROOT
            / "data_tw/experiments/provider_bridge_productionization/"
            "pbpr3w_contained_real_runtime_repair/runtime_config_contract.json"
        ),
        flags=safe_flags(),
    )
    assert report["status"] == "pass"
    assert report["runtime_config_contract"]["status"] == "pass"
    assert report["runtime_reachability"]["pbpr3w_contract_only"] is True
    assert report["runtime_reachability"]["allow_real_execution_default"] is False
    assert report["runtime_reachability"]["real_qlib_scoring_executed"] is False
    assert report["runtime_reachability"]["contained_direct_qlib_runtime_available_for_later_gate"] is True
    expected_prefix = (
        "data_tw/experiments/provider_bridge_productionization/"
        "pbpr3_target_asof_model_a_no_publish_dry_run/"
        "rerun_after_pbpr3w/planned_future_outputs/"
    )
    for path in report["runtime_paths"].values():
        assert path.startswith(expected_prefix)


def test_contained_real_runtime_contract_rejects_legacy_output_root() -> None:
    report = module.validate_contained_real_runtime_contract(
        target_asof="2026-07-08",
        accepted_readiness=ACCEPTED,
        provider_root=PROVIDER,
        normalized_root=NORMALIZED,
        output_root=ROOT / "data_tw/artifacts/score_jobs/e4_frozen_qlib_2018_2022",
        flags=safe_flags(),
    )
    assert report["status"] == "fail"
    assert "output_root_not_under_pbpr3_isolated_root" in report["errors"]
    assert any("data_tw/artifacts" in error for error in report["errors"])


def test_contained_real_runtime_contract_rejects_missing_runtime_flags() -> None:
    report = module.validate_contained_real_runtime_contract(
        target_asof="2026-07-08",
        accepted_readiness=ACCEPTED,
        provider_root=PROVIDER,
        normalized_root=NORMALIZED,
        output_root=PBPR3_ROOT / "rerun_after_pbpr3w",
        flags=module.SafetyFlags(
            no_publish=True,
            no_catalog=False,
            no_latest=True,
            no_target_output=True,
            preflight_only=True,
        ),
    )
    assert report["status"] == "fail"
    assert "required_safety_flag_missing:no_catalog" in report["errors"]


def test_contained_real_runtime_contract_rejects_forbidden_runtime_path_override() -> None:
    report = module.validate_contained_real_runtime_contract(
        target_asof="2026-07-08",
        accepted_readiness=ACCEPTED,
        provider_root=PROVIDER,
        normalized_root=NORMALIZED,
        output_root=PBPR3_ROOT / "rerun_after_pbpr3w",
        flags=safe_flags(),
        planned_runtime_overrides={
            "model_signal_manifest": PBPR3_ROOT
            / "rerun_after_pbpr3w"
            / "planned_future_outputs"
            / "latest"
            / "manifest.json"
        },
    )
    assert report["status"] == "fail"
    assert any("runtime_path_model_signal_manifest_forbidden_path_part:latest" in error for error in report["errors"])
