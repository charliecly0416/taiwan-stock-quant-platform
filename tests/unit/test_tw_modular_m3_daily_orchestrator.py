from __future__ import annotations

import json
import importlib.util
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VALIDATOR = ROOT / "scripts/validate_tw_daily_orchestrator_m3.py"
GOLDEN_ROOT = ROOT / "data_tw/golden_samples/modular_contracts/m3"
DAILY_SCRIPT = ROOT / "scripts/run_daily_tw_stock_auto_update.py"


def write_payload(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_daily_module():
    spec = importlib.util.spec_from_file_location("run_daily_tw_stock_auto_update", DAILY_SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_validator(*args: str) -> tuple[int, dict]:
    proc = subprocess.run(
        [sys.executable, str(VALIDATOR), *args, "--json"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert proc.stdout.strip(), proc.stderr
    return proc.returncode, json.loads(proc.stdout)


def test_m3_golden_batch_passes_and_counts_all_samples() -> None:
    code, result = run_validator("--run-golden")
    assert code == 0
    assert result["ok"] is True
    assert result["schema_version"] == "m3.0.0"
    assert result["sample_count"] == 16
    assert {row["contract"] for row in result["results"]} == {
        "daily_orchestrator",
        "run_registry",
        "auto_update",
    }


def test_m3_latest_pointer_state_machine_samples() -> None:
    cases = [
        ("daily_orchestrator/no_new_data_noop_preserves_previous_latest", "readonly_latest_20260616"),
        ("daily_orchestrator/fresh_data_success_validators_passed_updates_readonly_latest", "readonly_latest_20260617"),
        ("daily_orchestrator/validator_failed_preserves_previous_latest", "readonly_latest_20260616"),
        ("daily_orchestrator/module_failed_preserves_previous_latest", "readonly_latest_20260616"),
        ("run_registry/success_records_previous_proposed_committed_checksum", "readonly_latest_20260617"),
    ]
    for rel_sample, expected_committed in cases:
        sample = GOLDEN_ROOT / rel_sample
        contract = rel_sample.split("/", 1)[0]
        code, result = run_validator("--contract", contract, "--artifact-path", str(sample))
        assert code == 0, rel_sample
        assert result["ok"] is True, rel_sample
        assert result["previous_latest"] == "readonly_latest_20260616", rel_sample
        assert result["committed_latest"] == expected_committed, rel_sample
        assert result["latest_pointer_policy"] == "readonly_after_all_validators_pass_keep_previous_on_failure"


def test_m3_negative_samples_fail_with_expected_codes() -> None:
    cases = {
        "daily_orchestrator/forbidden_provider_publish_rejected": "forbidden_action",
        "daily_orchestrator/forbidden_accepted_latest_switch_rejected": "accepted_latest_changed",
        "daily_orchestrator/forbidden_monitor_broker_order_rejected": "forbidden_action",
        "auto_update/forbidden_provider_publish_rejected": "forbidden_action",
        "auto_update/forbidden_accepted_latest_switch_rejected": "accepted_latest_changed",
        "auto_update/forbidden_monitor_broker_order_rejected": "forbidden_action",
    }
    for rel_sample, expected_code in cases.items():
        sample = GOLDEN_ROOT / rel_sample
        contract = rel_sample.split("/", 1)[0]
        code, result = run_validator("--contract", contract, "--artifact-path", str(sample))
        assert code != 0, rel_sample
        assert result["ok"] is False, rel_sample
        assert expected_code in {err["code"] for err in result["errors"]}


def test_m3_daily_auto_update_script_audit_passes_only_when_legacy_path_is_gated() -> None:
    code, result = run_validator("--audit-script", str(DAILY_SCRIPT))
    assert code == 0
    assert result["ok"] is True
    warning_codes = {item["code"] for item in result["warnings"]}
    assert warning_codes == {
        "legacy_provider_publish_path_present",
        "legacy_accepted_latest_path_present",
    }
    audit = result["script_audit"]
    assert audit["has_wait_noop"] is True
    assert audit["has_already_up_to_date_noop"] is True
    assert audit["has_pending_retry"] is True
    assert audit["has_readonly_snapshot_dry_run_default"] is True
    assert audit["readonly_latest_pointer_distinct"] is True
    assert audit["daily_full_capture_accounting_present"] is True
    assert audit["daily_full_capture_finalized_before_returns"] is True
    assert audit["daily_full_capture_blocks_production_trade"] is True
    assert audit["daily_full_capture_records_accepted_latest_boundary"] is True
    assert audit["daily_full_capture_missing_categories"] == []
    assert audit["daily_source_inventory_present"] is True
    assert audit["daily_source_inventory_missing_patterns"] == []
    assert audit["daily_source_inventory_reads_finmind_stdout"] is True
    assert audit["daily_source_inventory_has_source_metrics"] is True
    assert audit["finmind_segmented_tolerant_update_present"] is True
    assert audit["finmind_segmented_merged_stdout_present"] is True
    assert audit["finmind_quota_scope_control_present"] is True
    assert audit["finmind_segment_cache_present"] is True
    assert audit["finmind_segment_cache_origin_gate_present"] is True
    assert audit["pbpr0_daily_chain_schema_fields_present"] is True
    assert audit["pbpr0_daily_chain_schema_missing_patterns"] == []
    assert audit["pbpr0_daily_chain_refined_blocker_present"] is True
    assert audit["pbpr0_daily_chain_provider_bridge_state_present"] is True
    assert audit["pbpr0_skipped_asof_ledger_schema_fields_present"] is True
    source = DAILY_SCRIPT.read_text(encoding="utf-8")
    assert "finmind_orthogonal_batch_state_v1" in source
    assert "TW_DAILY_AUTO_FINMIND_ORTHOGONAL_BATCH_SIZE" in source
    assert "orthogonal_batch_control" in source
    assert "quota_exhausted_retry_next_day" in source
    assert set(audit["daily_full_capture_categories_present"]) == {
        "stock_ohlcv_adjusted_price",
        "twii_market_index",
        "finmind_raw_daily_price",
        "institutional_flow",
        "margin_short",
        "orthogonal_raw_archive",
        "daily_ltr_source_freshness",
        "readonly_price_twii_calendar_bridge",
        "execution_price_readiness",
        "schema_coverage_holiday_pending_evidence",
    }
    assert audit["production_provider_refresh_path_present"] is True
    assert audit["production_provider_publish_path_present"] is True
    assert audit["production_accepted_latest_path_present"] is True
    assert audit["legacy_provider_gate_present"] is True
    assert audit["legacy_provider_gate_default_disabled"] is True
    assert audit["workflow_readonly_shadow_gate_present"] is True
    assert audit["workflow_readonly_shadow_gate_default_disabled"] is True
    assert audit["workflow_readonly_shadow_spec_exact"] is True
    assert audit["workflow_readonly_shadow_modules"] == ["replay_window.observe"]
    assert audit["workflow_readonly_shadow_only_replay_read"] is True
    assert audit["workflow_readonly_shadow_no_candidate_execution"] is True
    assert audit["workflow_readonly_shadow_job_local_workspace"] is True
    assert audit["workflow_readonly_shadow_fixed_timeout"] is True
    assert audit["workflow_readonly_shadow_nonblocking_states"] is True
    assert audit["workflow_readonly_shadow_finalize_call_count"] == 1
    assert audit["workflow_readonly_shadow_dng9_early_exit_precedes_job"] is True
    assert audit["workflow_readonly_shadow_runner_pinned"] is True
    assert audit["workflow_readonly_shadow_persisted_record_validated"] is True
    assert audit["legacy_provider_block_guarded"] is True
    assert audit["default_provider_refresh_reachable"] is False
    assert audit["default_provider_publish_reachable"] is False
    assert audit["default_accepted_latest_reachable"] is False
    assert audit["broker_order_patterns_present"] == []
    assert audit["monitor_write_patterns_present"] == []


def test_wf3_daily_wiring_is_thin_default_off_and_after_dng9_early_exit() -> None:
    source = DAILY_SCRIPT.read_text(encoding="utf-8")
    helper = (ROOT / "scripts/tw_daily_workflow_readonly_shadow.py").read_text(
        encoding="utf-8"
    )

    assert (
        'default=env_flag("TW_DAILY_AUTO_ENABLE_WORKFLOW_READONLY_SHADOW", False)'
        in source
    )
    assert source.count("run_daily_workflow_readonly_shadow(") == 1
    assert (
        'WORKFLOW_READONLY_SHADOW_SPEC = ROOT / "configs/workflows/replay_window_observation.yaml"'
        in source
    )
    assert '"formal_provider_calendar": CALENDAR' in source
    assert '"qlib_accepted_latest": LATEST' in source
    assert '"controlled_model_signal_latest": CONTROLLED_MODEL_SIGNAL_LATEST' in source
    assert 'return 0 if validation.get("ok") else 2' in source
    assert source.index('return 0 if validation.get("ok") else 2') < source.index(
        "job: dict[str, Any] = {"
    )
    assert 'WORKFLOW_PERMISSION = "replay.read"' in helper
    assert 'WORKFLOW_MODULE = "replay_window.observe"' in helper
    assert "replay_candidate.build_validate" not in helper
    assert "replay.candidate.write" not in helper
    assert "WORKFLOW_TIMEOUT_SECONDS = 60" in helper
    assert "set_pending_asof" not in helper
    assert "clear_pending_asof" not in helper


def test_daily_entrypoint_help_loads_without_external_pythonpath() -> None:
    completed = subprocess.run(
        [sys.executable, str(DAILY_SCRIPT), "--help"],
        cwd=ROOT,
        env={key: value for key, value in os.environ.items() if key != "PYTHONPATH"},
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert "--enable-workflow-readonly-shadow" in completed.stdout


def test_pbpr0_daily_chain_blocked_case_emits_dasf_fields() -> None:
    module = load_daily_module()
    decision = module.build_pbpr0_daily_chain_decision_fields(
        raw_status="READY",
        formal_calendar_covers=False,
        model_a_inference_status="BLOCKED_PROVIDER_VIEW_STALE",
        model_a_score_status="BLOCKED_PROVIDER_VIEW_STALE",
        model_a_signal_status="BLOCKED_PROVIDER_VIEW_STALE",
        blocked_at="qlib_provider_view_or_formal_calendar",
        blocker_reason="provider stale",
    )

    assert decision["state"] == "RAW_READY_PROVIDER_STALE"
    assert decision["provider_bridge_readiness_state"] == "BLOCKED_NEEDS_TARGET_ASOF_PROVIDER_OR_BRIDGE"
    assert decision["refined_blocker"] == {
        "blocked_at": "validated_provider_candidate_or_existing_isolated_modela_artifact",
        "reason": "no_validated_target_asof_provider_candidate_or_bridge_or_modela_artifact",
    }
    assert decision["required_inputs"] == [
        "raw_daily_source_inventory",
        "formal_qlib_calendar_or_validated_provider_bridge",
        "model_inference_input",
        "score_job",
        "model_signal_artifact",
    ]

    chain_status = {
        "asof": "2026-07-08",
        "job_id": "daily_tw_stock_auto_update_20260708_20260708T123001Z",
        "is_trading_day": True,
        "data_window_status": "DATA_WINDOW_OBSERVED",
        "raw_status": "READY",
        "qlib_provider_view_status": "BLOCKED_PROVIDER_VIEW_STALE",
        "model_a_score_status": "BLOCKED_PROVIDER_VIEW_STALE",
        "strategy_input_bundle_status": "BLOCKED_MODEL_A_SIGNAL",
        "blocker_reason": "provider stale",
        "blocked_at": "qlib_provider_view_or_formal_calendar",
        "next_retry_hint": "retry_after_provider_view_refresh_or_canonical_bridge",
        "next_required_action": "refresh_formal_qlib_provider_view_or_build_validated_canonical_bridge_then_run_model_a_score",
        "lineage_evidence": {
            "formal_calendar_path": "calendar/day.txt",
            "latest_signal_path": "latest_signal.json",
            "raw_evidence_paths": ["finmind_stdout.txt"],
        },
        "forbidden_actions": {"all_false": True, "actions": {}},
        **decision,
    }
    ledger = module.build_skipped_asof_ledger_payload(chain_status)
    row = ledger["ledger_rows"][0]
    assert row["state"] == "RAW_READY_PROVIDER_STALE"
    assert row["refined_blocker"]["blocked_at"] == "validated_provider_candidate_or_existing_isolated_modela_artifact"
    assert row["provider_bridge_readiness_state"] == "BLOCKED_NEEDS_TARGET_ASOF_PROVIDER_OR_BRIDGE"
    assert ledger["state"] == "RAW_READY_PROVIDER_STALE"
    assert ledger["refined_blocker"]["reason"] == "no_validated_target_asof_provider_candidate_or_bridge_or_modela_artifact"


def test_daily_strict_e4_chain_is_explicit_readonly_and_preserves_orthogonal_sources() -> None:
    source = DAILY_SCRIPT.read_text(encoding="utf-8")
    assert "TW_DAILY_AUTO_ENABLE_STRICT_E4_READONLY_CHAIN" in source
    assert "default=env_flag(\"TW_DAILY_AUTO_ENABLE_STRICT_E4_READONLY_CHAIN\", False)" in source
    assert "run_strict_e4_readonly_chain(" in source
    assert "provider_publish_triggered\": False" in source
    assert "accepted_latest_switch_triggered\": False" in source
    assert "qlib_accepted_latest_switch_triggered\": False" in source
    assert "if args.finmind_scope == \"daily\" and args.enable_strict_e4_readonly_chain:" in source
    assert "daily_scope_would_skip_institutional_margin" in source
    assert "run_finmind_segmented_update(" in source
    assert '"institutional"' in source
    assert '"margin"' in source


def test_full_orthogonal_refresh_continues_into_downstream_chain_when_ready() -> None:
    source = DAILY_SCRIPT.read_text(encoding="utf-8")
    assert 'job["full_orthogonal_refresh_status"] = "PASSED_CONTINUE_DOWNSTREAM"' in source
    assert 'job["full_orthogonal_refresh_downstream_continued"] = True' in source
    assert "downstream signal/strategy/artifact stages were not entered" in source


def test_dapr18_controlled_latest_gate_requires_exact_authorized_auto_publish_scope_in_cron() -> None:
    source = DAILY_SCRIPT.read_text(encoding="utf-8")
    cron = (ROOT / "data_tw/ops/daily_auto_update/tw-daily-auto-update.installed.cron").read_text(encoding="utf-8")

    assert "ENABLE_TW_DAPR18_CONTROLLED_LATEST_ORCHESTRATION" in source
    assert 'default=env_flag("ENABLE_TW_DAPR18_CONTROLLED_LATEST_ORCHESTRATION", False)' in source
    assert 'default=env_flag("TW_DAPR18_CONTROLLED_LATEST_DRY_RUN", True)' in source
    assert 'default=env_flag("TW_DAPR18_BUILD_CANDIDATES", False)' in source
    assert 'default=env_flag("TW_DAPR18_PUBLISH_CONTROLLED_SIGNAL_LATEST", False)' in source
    assert 'default=env_flag("TW_DAPR18_PUBLISH_READONLY_SNAPSHOT_LATEST", False)' in source
    assert 'default=env_flag("TW_DAPR18_PUBLISH_AGENT_PROMPT_LATEST", False)' in source
    assert "run_dapr18_controlled_latest_orchestration(" in source
    assert '"controlled_signal_latest_write": False' in source
    assert '"readonly_snapshot_latest_write": False' in source
    assert '"agent_prompt_latest_write": False' in source
    assert "DAPR18_AUTO_PUBLISH_CHAIN_" in source
    assert "dapr18_auto_publish_requires_all_three_product_latest_flags" in source
    assert "run_dapr18_auto_publish_chain(" in source
    assert "build_tw_dapr9_controlled_latest_publish_preflight_or_stop.py" in source
    assert "build_tw_dapr17_actual_controlled_agent_prompt_publish.py" in source
    assert "TW_DAILY_AUTO_ENABLE_PROVIDER_CANDIDATE_REFRESH=true" in cron
    assert "TW_DAILY_AUTO_ENABLE_MODEL_SIGNAL_GATE=true" in cron
    authorization_id = "DAPR18_AUTO_PUBLISH_CHAIN_CRON_20260910_USER_AUTHORIZED_STABLE_OPS"
    assert "TW_DAPR18_CONTROLLED_LATEST_DRY_RUN=false" in cron
    assert "TW_DAPR18_PUBLISH_CONTROLLED_SIGNAL_LATEST=true" in cron
    assert "TW_DAPR18_PUBLISH_READONLY_SNAPSHOT_LATEST=true" in cron
    assert "TW_DAPR18_PUBLISH_AGENT_PROMPT_LATEST=true" in cron
    assert "TW_DAILY_AUTO_ENABLE_LEGACY_PROVIDER_PUBLISH=true" in cron
    assert f"TW_DAPR18_EXACT_AUTHORIZATION_ID={authorization_id}" in cron
    assert "ENABLE_TW_AGENT_DAILY_PROMPT_PUBLISH=false" in cron
    assert "TW_AGENT_DAILY_PROMPT_PUBLISH_LATEST=false" in cron

    publish_lines = [
        line
        for line in cron.splitlines()
        if "run_daily_tw_stock_auto_update.py" in line
    ]
    assert len(publish_lines) == 2
    required_scope = [
        "TW_DAPR18_CONTROLLED_LATEST_DRY_RUN=false",
        "TW_DAPR18_BUILD_CANDIDATES=true",
        "TW_DAPR18_PUBLISH_CONTROLLED_SIGNAL_LATEST=true",
        "TW_DAPR18_PUBLISH_READONLY_SNAPSHOT_LATEST=true",
        "TW_DAPR18_PUBLISH_AGENT_PROMPT_LATEST=true",
        f"TW_DAPR18_EXACT_AUTHORIZATION_ID={authorization_id}",
        "TW_DAILY_AUTO_ENABLE_LEGACY_PROVIDER_PUBLISH=true",
    ]
    for line in publish_lines:
        assert all(token in line for token in required_scope)


def test_b19r2r_shadow_wrapper_enabled_passes_same_run_inputs(tmp_path: Path) -> None:
    module = load_daily_module()
    model_a = tmp_path / "model_a"
    model_a.mkdir()
    handoff = tmp_path / "same_run_handoff_validation.json"
    handoff.write_text("{}", encoding="utf-8")
    provider = tmp_path / "option_c_yahoo_scrapling_publish_x" / "tmp" / "formal_provider_rebuild"
    provider.mkdir(parents=True)
    (tmp_path / "job").mkdir()
    captured: dict[str, object] = {"calls": []}

    def fake_runner(argv, **kwargs):
        captured["calls"].append({"argv": argv, "kwargs": kwargs})
        captured["argv"] = argv
        kwargs["stdout_path"].write_text(json.dumps({"ok": True, "status": "READY_RESEARCH_SHADOW"}), encoding="utf-8")
        return {"ok": True, "returncode": 0, "stdout_path": str(kwargs["stdout_path"]), "stderr_tail": ""}

    result = module.run_b19r2r_daily_shadow_nonblocking(
        enabled=True,
        asof="2026-09-17",
        job_id="job-1",
        job_dir=tmp_path / "job",
        model_signal_gate={"ok": True, "summary": {"model_a_signal_path": str(model_a)}},
        same_run_handoff_validation=handoff,
        source_acquisition_run_id="logical-run-1",
        provider_snapshot=provider,
        decision_cutoff="2026-09-17T08:00:00+00:00",
        next_session_open="2026-09-18T01:00:00+00:00",
        command_runner=fake_runner,
    )
    argv = captured["argv"]
    assert result["shadow_ok"] is True
    assert result["mainline_blocking"] is False
    assert result["production_allowed"] is False
    assert result["no_apply"] is True
    assert len(captured["calls"]) == 2
    capture_call = captured["calls"][0]
    assert str(module.B19R2R_TWII_CAPTURE_RUNNER.relative_to(module.ROOT)) in capture_call["argv"]
    assert capture_call["kwargs"]["env"]["B19YTWII_ACQUISITION_RUN_ID"] == "logical-run-1"
    assert result["requested_decision_cutoff"] == "2026-09-17T08:00:00+00:00"
    assert result["decision_cutoff"] != result["requested_decision_cutoff"]
    assert "--model-a-signal-dir" in argv
    assert str(model_a) in argv
    assert "--handoff-validation" in argv
    assert str(handoff) in argv
    assert "--provider-snapshot" in argv
    assert str(provider) in argv
    assert "--twii-csv" in argv
    assert "--twii-manifest" in argv


def test_b19r2r_shadow_wrapper_disabled_does_not_invoke_runner(tmp_path: Path) -> None:
    module = load_daily_module()
    called = False

    def fake_runner(*args, **kwargs):
        nonlocal called
        called = True
        return {"ok": True, "returncode": 0}

    result = module.run_b19r2r_daily_shadow_nonblocking(
        enabled=False,
        asof="2026-09-17",
        job_id="job-1",
        job_dir=tmp_path,
        model_signal_gate={"ok": True},
        same_run_handoff_validation=tmp_path / "missing-handoff.json",
        source_acquisition_run_id="run",
        provider_snapshot=tmp_path / "missing-provider",
        decision_cutoff="cutoff",
        next_session_open="open",
        command_runner=fake_runner,
    )
    assert result["status"] == "DISABLED_BY_DEFAULT"
    assert result["attempted"] is False
    assert called is False


def test_b19r2r_shadow_capture_failure_is_nonblocking_and_does_not_score(tmp_path: Path) -> None:
    module = load_daily_module()
    model_a = tmp_path / "model_a"
    model_a.mkdir()
    handoff = tmp_path / "handoff.json"
    handoff.write_text("{}", encoding="utf-8")
    provider = tmp_path / "provider"
    provider.mkdir()

    calls = []

    def failed_runner(argv, **kwargs):
        calls.append(argv)
        kwargs["stdout_path"].write_text(json.dumps({"ok": False, "status": "B19R2R_BLOCKED_VALIDATOR"}), encoding="utf-8")
        return {"ok": False, "returncode": 2, "stdout_path": str(kwargs["stdout_path"]), "stderr_tail": "blocked"}

    result = module.run_b19r2r_daily_shadow_nonblocking(
        enabled=True,
        asof="2026-09-17",
        job_id="job-1",
        job_dir=tmp_path,
        model_signal_gate={"ok": True, "summary": {"model_a_signal_path": str(model_a)}},
        same_run_handoff_validation=handoff,
        source_acquisition_run_id="run",
        provider_snapshot=provider,
        decision_cutoff="2026-09-17T08:00:00+00:00",
        next_session_open="2026-09-18T01:00:00+00:00",
        command_runner=failed_runner,
    )
    assert result["ok"] is True
    assert result["shadow_ok"] is False
    assert result["mainline_blocking"] is False
    assert result["pending_asof_set"] is False
    assert result["status"] == "B19R2R_BLOCKED_TWII_CAPTURE"
    assert result["runner_returncode"] == 2
    assert len(calls) == 1
    assert str(module.B19R2R_TWII_CAPTURE_RUNNER.relative_to(module.ROOT)) in calls[0]


def test_b19r2r_cron_gate_is_full_scope_only() -> None:
    cron = (ROOT / "data_tw/ops/daily_auto_update/tw-daily-auto-update.installed.cron").read_text(encoding="utf-8")
    lines = [line for line in cron.splitlines() if "run_daily_tw_stock_auto_update.py" in line]
    assert len(lines) >= 2
    daily = next(line for line in lines if "TW_DAILY_AUTO_FINMIND_SCOPE=daily" in line)
    full = next(line for line in lines if "TW_DAILY_AUTO_FINMIND_SCOPE=full" in line)
    assert "TW_DAILY_AUTO_ENABLE_B19R2R_SHADOW=true" not in daily
    assert "TW_DAILY_AUTO_ENABLE_B19R2R_SHADOW=true" in full


def test_b19r2r_cutoff_is_captured_after_model_a_gate() -> None:
    source = DAILY_SCRIPT.read_text(encoding="utf-8")
    gate_failure = source.index("if args.enable_model_signal_gate and not model_signal_gate.get(\"ok\"):")
    cutoff_capture = source.index("b19r2r_cutoff = utc_now()")
    assert cutoff_capture > gate_failure
    assert "cutoff_value = b19r2r_cutoff" in source


def test_b19r2r_uses_the_publish_stage_qlib_snapshot_root() -> None:
    source = DAILY_SCRIPT.read_text(encoding="utf-8")
    assert 'QLIB / "data_tw/experiments/option_c_ops" / publish_job_id / "tmp/formal_provider_rebuild"' in source
    assert 'ROOT / "data_tw/experiments/option_c_ops" / publish_job_id' not in source


def test_fpala_formal_accepted_latest_gate_is_dedicated_default_off_no_publish() -> None:
    source = DAILY_SCRIPT.read_text(encoding="utf-8")

    assert "ENABLE_TW_FPALA_FORMAL_ACCEPTED_LATEST_AUTOMATION" in source
    assert 'default=env_flag("ENABLE_TW_FPALA_FORMAL_ACCEPTED_LATEST_AUTOMATION", False)' in source
    assert 'default=env_flag("TW_FPALA_NO_PUBLISH", True)' in source
    assert 'default=env_flag("TW_FPALA_ALLOW_FORMAL_PROVIDER_PUBLISH", False)' in source
    assert 'default=env_flag("TW_FPALA_ALLOW_ACCEPTED_LATEST_SWITCH", False)' in source
    assert "run_fpala_formal_accepted_latest_no_publish_preflight(" in source
    assert "validate_tw_fpala_no_publish_decision" in source
    assert "TW_DAILY_AUTO_ENABLE_LEGACY_PROVIDER_PUBLISH" in source
    assert "legacy_provider_publish_enabled=bool((job or {}).get(\"legacy_provider_publish_enabled\"))" in source
    assert '"provider_publish_triggered": False' in source
    assert '"accepted_latest_switch_triggered": False' in source
    assert '"latest_signal_updated": False' in source
    assert '"dapr18_publish_triggered": False' in source


def test_fpala_daily_auto_gate_runs_before_early_return_finalize_points() -> None:
    source = DAILY_SCRIPT.read_text(encoding="utf-8")
    already_start = source.index('job.update({"status": "already_up_to_date"')
    already_end = source.index("finalize_job(job, job_dir=job_dir, asof=asof, args=args)", already_start)
    assert "attach_fpala_formal_accepted_latest_preflight(" in source[already_start:already_end]

    wait_start = source.index('"today_data_window_open": False')
    wait_end = source.index("finalize_job(job, job_dir=job_dir, asof=asof, args=args)", wait_start)
    assert "attach_fpala_formal_accepted_latest_preflight(" in source[wait_start:wait_end]


def make_fpala_paths(tmp_path: Path, asof: str) -> dict[str, Path]:
    candidate_dir = tmp_path / "candidate"
    write_payload(
        candidate_dir / "provider_candidate_readiness.json",
        {
            "candidate_asof": asof,
            "asof": asof,
            "candidate_source": "unit",
            "staged_provider_calendar_max": asof,
            "staged_provider_calendar_has_asof": True,
            "candidate_normalized_symbols_expected": 150,
            "candidate_normalized_symbols_success": 150,
            "candidate_normalized_symbols_with_asof": 150,
            "staged_provider_validation_status": "pass",
            "candidate_model_smoke_status": "pass",
            "production_allowed": False,
            "publish_latest_authorized": False,
            "formal_provider_mutated": False,
            "formal_normalized_mutated": False,
            "latest_signal_updated": False,
            "forbidden_actions": {"formal_publish": False, "accepted_latest_switch": False},
        },
    )
    calendar = tmp_path / "formal/calendars/day.txt"
    calendar.parent.mkdir(parents=True, exist_ok=True)
    calendar.write_text(f"2026-08-01\n{asof}\n", encoding="utf-8")
    paths = {
        "candidate_dir": candidate_dir,
        "formal_provider_calendar_path": calendar,
        "qlib_accepted_latest_path": tmp_path / "qlib_latest.json",
        "legacy_latest_path": tmp_path / "legacy_latest.json",
        "dapr18_signal_latest_path": tmp_path / "dapr18_signal_latest.json",
        "readonly_snapshot_latest_path": tmp_path / "readonly_snapshot_latest.json",
        "agent_prompt_latest_path": tmp_path / "agent_prompt_latest.json",
        "installed_cron_path": tmp_path / "tw-daily-auto-update.installed.cron",
        "pending_asof_path": tmp_path / "pending_asof.json",
        "output_root": tmp_path / "fpala_out",
        "candidate_root": tmp_path / "candidate_root",
    }
    write_payload(paths["qlib_accepted_latest_path"], {"asof": asof, "status": "accepted", "run_id": f"run_{asof}"})
    write_payload(paths["legacy_latest_path"], {"asof": "2026-06-01"})
    write_payload(paths["dapr18_signal_latest_path"], {"asof": asof, "signal_asof": asof, "manifest": ""})
    write_payload(paths["readonly_snapshot_latest_path"], {"asof": asof, "signal_asof": asof, "manifest": ""})
    write_payload(paths["agent_prompt_latest_path"], {"signal_asof": asof, "manifest": ""})
    paths["installed_cron_path"].write_text("SHELL=/bin/bash\n", encoding="utf-8")
    return paths


def test_fpala_daily_auto_gate_disabled_returns_no_attempt(tmp_path: Path) -> None:
    module = load_daily_module()
    result = module.run_fpala_formal_accepted_latest_no_publish_preflight(
        asof="2026-08-07",
        job_id="unit",
        job_dir=tmp_path,
        enabled=False,
    )
    assert result["status"] == "disabled_by_default"
    assert result["attempted"] is False
    assert result["provider_publish_triggered"] is False
    assert result["accepted_latest_switch_triggered"] is False


def test_fpala_daily_auto_gate_enabled_writes_only_job_dir_evidence(tmp_path: Path) -> None:
    module = load_daily_module()
    paths = make_fpala_paths(tmp_path, "2026-08-07")
    result = module.run_fpala_formal_accepted_latest_no_publish_preflight(
        asof="2026-08-07",
        job_id="unit",
        job_dir=tmp_path / "job",
        job={"legacy_provider_publish_enabled": False},
        provider_candidate_gate={"enabled": True, "attempted": False, "status": "READY_UNIT", "readiness_path": str(paths["candidate_dir"] / "provider_candidate_readiness.json")},
        enabled=True,
        no_publish=True,
        allow_formal_provider_publish=False,
        allow_accepted_latest_switch=False,
        exact_authorization_id="",
        **{key: value for key, value in paths.items() if key != "candidate_dir"},
    )
    assert result["ok"] is True
    assert result["attempted"] is True
    assert result["status"] == "no_publish_decision_validated"
    assert result["decision_status"] == "already_aligned_idempotent_noop"
    assert result["job_dir_only_evidence"] is False
    assert result["fpala_evidence_dir"].endswith("fpala4_daily_auto_no_publish_20260807_unit")
    assert result["provider_publish_triggered"] is False
    assert result["accepted_latest_switch_triggered"] is False
    assert (tmp_path / "fpala_out/fpala4_daily_auto_no_publish_20260807_unit/decision.json").exists()
    assert (tmp_path / "fpala_out/fpala4_daily_auto_no_publish_20260807_unit/validation_report.json").exists()


def test_fpala_daily_auto_gate_blocks_non_no_publish_control(tmp_path: Path) -> None:
    module = load_daily_module()
    result = module.run_fpala_formal_accepted_latest_no_publish_preflight(
        asof="2026-08-07",
        job_id="unit",
        job_dir=tmp_path,
        enabled=True,
        no_publish=False,
    )
    assert result["ok"] is False
    assert result["status"] == "blocked_by_non_no_publish_control"
    assert result["provider_publish_triggered"] is False
    assert result["accepted_latest_switch_triggered"] is False


def make_qald_latest_paths(tmp_path: Path) -> dict[str, Path]:
    paths = {
        "qlib_accepted_latest_path": tmp_path / "qlib_latest.json",
        "legacy_latest_path": tmp_path / "legacy_latest.json",
        "dapr18_signal_latest_path": tmp_path / "dapr18_signal_latest.json",
        "readonly_snapshot_latest_path": tmp_path / "readonly_snapshot_latest.json",
        "agent_prompt_latest_path": tmp_path / "agent_prompt_latest.json",
    }
    for name, path in paths.items():
        write_payload(path, {"name": name, "asof": "2026-08-07"})
    return paths


def test_qald2r_flags_are_static_default_off_no_pointer() -> None:
    source = DAILY_SCRIPT.read_text(encoding="utf-8")
    assert "ENABLE_TW_QALD_ACCEPTED_LATEST_CANDIDATE_BUILDER" in source
    assert 'default=env_flag("ENABLE_TW_QALD_ACCEPTED_LATEST_CANDIDATE_BUILDER", False)' in source
    assert 'default=env_flag("TW_QALD_ACCEPTED_LATEST_CANDIDATE_NO_POINTER", True)' in source
    assert 'default=env_flag("TW_QALD_ACCEPTED_LATEST_CANDIDATE_ALLOW_POINTER_WRITE", False)' in source
    assert "qald2r_accepted_latest_candidate_preflight.json" in source
    assert '"--target-asof",' in source
    assert '"--source-candidate-root",' in source


def test_qald2r_disabled_helper_writes_skipped_evidence_without_attempt(tmp_path: Path) -> None:
    module = load_daily_module()
    result = module.run_qald_accepted_latest_candidate_builder_no_publish(
        asof="2026-08-07",
        job_id="unit",
        job_dir=tmp_path,
        enabled=False,
        **make_qald_latest_paths(tmp_path),
    )

    evidence = json.loads((tmp_path / "qald2r_accepted_latest_candidate_preflight.json").read_text(encoding="utf-8"))
    assert result["status"] == "disabled_by_default"
    assert result["attempted"] is False
    assert evidence["enabled"] is False
    assert evidence["latest_signal_updated"] is False
    assert evidence["accepted_latest_switch_authorization_required"] is True


def test_qald2r_enabled_blocks_unsafe_pointer_controls(tmp_path: Path) -> None:
    module = load_daily_module()

    def forbidden_runner(*args, **kwargs):
        raise AssertionError("builder must not be called when QALD controls are unsafe")

    result = module.run_qald_accepted_latest_candidate_builder_no_publish(
        asof="2026-08-07",
        job_id="unit",
        job_dir=tmp_path,
        enabled=True,
        no_pointer=False,
        allow_pointer_write=True,
        provider_candidate_gate={"ok": True},
        model_signal_gate={"ok": True},
        command_runner=forbidden_runner,
        **make_qald_latest_paths(tmp_path),
    )

    assert result["ok"] is False
    assert result["status"] == "blocked_by_qald2r_preflight_controls"
    assert "qald_no_pointer_false" in result["blocked_controls"]
    assert "qald_allow_pointer_write_true" in result["blocked_controls"]
    assert result["latest_signal_updated"] is False
    assert result["protected_pointer_unchanged"] is True


def test_qald2r_builder_called_with_explicit_target_and_source_root(tmp_path: Path) -> None:
    module = load_daily_module()
    source_root = tmp_path / "candidate_root"
    (source_root / "reports").mkdir(parents=True)
    (source_root / "reports/staged_prediction.csv").write_text("datetime,instrument,score\n", encoding="utf-8")
    calls = []

    def fake_runner(argv, *, cwd, stdout_path, stderr_path, timeout):
        calls.append(argv)
        stdout_path.write_text(
            json.dumps(
                {
                    "status": "pass",
                    "job_dir": str(tmp_path / "builder_job"),
                    "reader_validation": {
                        "ok": True,
                        "asof": "2026-08-07",
                        "run_id": "unit_run",
                        "top30_count": 30,
                        "top50_count": 50,
                        "status": "ok",
                    },
                }
            ),
            encoding="utf-8",
        )
        stderr_path.write_text("", encoding="utf-8")
        return {"ok": True, "returncode": 0, "argv": argv, "cwd": str(cwd), "stdout_path": str(stdout_path), "stderr_path": str(stderr_path)}

    result = module.run_qald_accepted_latest_candidate_builder_no_publish(
        asof="2026-08-07",
        job_id="unit",
        job_dir=tmp_path / "job",
        enabled=True,
        no_pointer=True,
        allow_pointer_write=False,
        source_root_override=str(source_root),
        provider_candidate_gate={"ok": True},
        model_signal_gate={"ok": True},
        builder_script=tmp_path / "builder.py",
        command_runner=fake_runner,
        **make_qald_latest_paths(tmp_path),
    )

    assert result["ok"] is True
    assert result["status"] == "candidate_built_no_pointer"
    assert calls
    argv = calls[0]
    assert "--target-asof" in argv
    assert argv[argv.index("--target-asof") + 1] == "2026-08-07"
    assert "--source-candidate-root" in argv
    assert argv[argv.index("--source-candidate-root") + 1] == str(source_root)
    assert result["reader_validation"]["top30_count"] == 30
    assert result["reader_validation"]["top50_count"] == 50


def test_daily_source_inventory_parses_finmind_stdout(tmp_path: Path) -> None:
    module = load_daily_module()
    stdout = tmp_path / "finmind_stdout.txt"
    stdout.write_text(
        json.dumps(
            {
                "archive": {"count": 4, "symbols": ["2330", "2317"], "date_min": "2026-06-24", "date_max": "2026-06-25"},
                "archived_count": 4,
                "institutional_trades": {"count": 2, "symbols": ["2330"], "date_min": "2026-06-25", "date_max": "2026-06-25"},
                "institutional_trades_archived_count": 2,
                "margin_trading": {"count": 2, "symbols": ["2330"], "date_min": "2026-06-25", "date_max": "2026-06-25"},
                "margin_trading_archived_count": 2,
            }
        ),
        encoding="utf-8",
    )
    summary = module.summarize_finmind_stdout(stdout)
    assert summary["finmind_raw_daily_price"]["row_count"] == 4
    assert summary["finmind_raw_daily_price"]["symbol_count"] == 2
    assert summary["finmind_raw_daily_price"]["source_max_date"] == "2026-06-25"
    assert summary["institutional_flow"]["row_count"] == 2
    assert summary["institutional_flow"]["archived_count"] == 2
    assert summary["margin_short"]["row_count"] == 2
    assert summary["margin_short"]["source_id"] == "finmind_margin_short"


def test_finmind_segmented_update_preserves_successful_segments_when_one_fails(tmp_path: Path, monkeypatch) -> None:
    module = load_daily_module()
    monkeypatch.setattr(module, "FINMIND_SEGMENT_CACHE_ROOT", tmp_path / "cache")
    symbols_file = tmp_path / "symbols.txt"
    symbols_file.write_text("2330\n2317\n", encoding="utf-8")

    def fake_runner(argv, *, cwd, stdout_path, stderr_path, timeout):
        segment = stdout_path.name.removeprefix("finmind_").removesuffix("_stdout.txt")
        payload = {
            "archive": {"count": 0, "symbols": [], "date_min": None, "date_max": None},
            "archived_count": 0,
            "institutional_trades": {"count": 0, "symbols": [], "date_min": None, "date_max": None},
            "institutional_trades_archived_count": 0,
            "margin_trading": {"count": 0, "symbols": [], "date_min": None, "date_max": None},
            "margin_trading_archived_count": 0,
        }
        if segment == "daily_price":
            payload["archive"] = {"count": 4, "symbols": ["2330", "2317"], "date_min": "2026-06-25", "date_max": "2026-06-26"}
            payload["archived_count"] = 4
        if segment == "margin":
            payload["margin_trading"] = {"count": 2, "symbols": ["2330"], "date_min": "2026-06-26", "date_max": "2026-06-26"}
            payload["margin_trading_archived_count"] = 2
        if segment == "institutional":
            stdout_path.write_text("", encoding="utf-8")
            stderr_path.write_text("ReadTimeout", encoding="utf-8")
            return {"ok": False, "returncode": 1, "argv": argv, "cwd": str(cwd), "stdout_path": str(stdout_path), "stderr_path": str(stderr_path), "stdout_tail": "", "stderr_tail": "ReadTimeout"}
        stdout_path.write_text(json.dumps(payload), encoding="utf-8")
        stderr_path.write_text("", encoding="utf-8")
        return {"ok": True, "returncode": 0, "argv": argv, "cwd": str(cwd), "stdout_path": str(stdout_path), "stderr_path": str(stderr_path), "stdout_tail": json.dumps(payload), "stderr_tail": ""}

    result = module.run_finmind_segmented_update(
        symbols_file=symbols_file,
        job_dir=tmp_path,
        start="2026-06-25",
        end="2026-06-26",
        timeout_seconds=10,
        skip_validate=True,
        full_scope=True,
        command_runner=fake_runner,
    )
    assert result["ok"] is False
    assert result["segmented"] is True
    handoff_artifacts = tmp_path / "same_run_handoff_artifacts"
    assert handoff_artifacts.is_dir()
    assert handoff_artifacts.stat().st_mode & 0o777 == 0o750
    summary = module.summarize_finmind_stdout(tmp_path / "finmind_stdout.txt")
    assert summary["finmind_raw_daily_price"]["row_count"] == 4
    assert summary["finmind_raw_daily_price"]["source_max_date"] == "2026-06-26"
    assert summary["institutional_flow"]["row_count"] == 0
    assert summary["margin_short"]["row_count"] == 2
    merged = json.loads((tmp_path / "finmind_stdout.txt").read_text(encoding="utf-8"))
    assert merged["segment_status"]["institutional"]["ok"] is False
    assert merged["segment_status"]["daily_price"]["ok"] is True


def test_finmind_segment_cache_reuses_success_and_cools_down_provider_402(tmp_path: Path, monkeypatch) -> None:
    module = load_daily_module()
    ops_root = tmp_path / "data_tw" / "ops" / "daily_auto_update"
    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setattr(module, "OPS_ROOT", ops_root)
    monkeypatch.setattr(module, "FINMIND_SEGMENT_CACHE_ROOT", ops_root / "finmind_segment_cache")
    symbols_file = ops_root / "symbols.txt"
    symbols_file.parent.mkdir(parents=True, exist_ok=True)
    symbols_file.write_text("2330\n", encoding="utf-8")
    calls = []

    def first_runner(argv, *, cwd, stdout_path, stderr_path, timeout):
        segment = stdout_path.name.removeprefix("finmind_").removesuffix("_stdout.txt")
        calls.append(("first", segment))
        if segment == "daily_price":
            payload = {
                "archive": {"count": 1, "symbols": ["2330"], "date_min": "2026-06-26", "date_max": "2026-06-26"},
                "archived_count": 1,
            }
            stdout_path.write_text(json.dumps(payload), encoding="utf-8")
            stderr_path.write_text("", encoding="utf-8")
            return {"ok": True, "returncode": 0, "argv": argv, "cwd": str(cwd), "stdout_path": str(stdout_path), "stderr_path": str(stderr_path), "stdout_tail": json.dumps(payload), "stderr_tail": ""}
        stdout_path.write_text("", encoding="utf-8")
        stderr_path.write_text("HTTPError: 402 Client Error: Payment Required", encoding="utf-8")
        return {"ok": False, "returncode": 1, "argv": argv, "cwd": str(cwd), "stdout_path": str(stdout_path), "stderr_path": str(stderr_path), "stdout_tail": "", "stderr_tail": "HTTPError: 402 Client Error: Payment Required"}

    module.run_finmind_segmented_update(
        symbols_file=symbols_file,
        job_dir=ops_root / "job1",
        start="2026-06-26",
        end="2026-06-26",
        timeout_seconds=10,
        skip_validate=True,
        full_scope=True,
        cooldown_hours=6,
        command_runner=first_runner,
    )

    def second_runner(argv, *, cwd, stdout_path, stderr_path, timeout):
        segment = stdout_path.name.removeprefix("finmind_").removesuffix("_stdout.txt")
        calls.append(("second", segment))
        raise AssertionError(f"segment should have been cached or cooled down: {segment}")

    result = module.run_finmind_segmented_update(
        symbols_file=symbols_file,
        job_dir=ops_root / "job2",
        start="2026-06-26",
        end="2026-06-26",
        timeout_seconds=10,
        skip_validate=True,
        full_scope=True,
        cooldown_hours=6,
        command_runner=second_runner,
    )
    merged = json.loads((ops_root / "job2" / "finmind_stdout.txt").read_text(encoding="utf-8"))
    assert result["ok"] is False
    assert merged["segment_status"]["daily_price"]["cached"] is True
    assert merged["segment_status"]["daily_price"]["ok"] is True
    assert merged["segment_status"]["institutional"]["cached"] is True
    assert merged["segment_status"]["institutional"]["provider_error"] == "provider_402_quota_or_payment_required"
    assert ("second", "daily_price") not in calls
    assert ("second", "institutional") not in calls


def test_finmind_segment_cache_disable_bypasses_provider_error_cooldown(tmp_path: Path, monkeypatch) -> None:
    module = load_daily_module()
    cache = {
        "schema_version": "finmind_segment_cache_v1",
        "segment": "daily_price",
        "asof": "2026-08-27",
        "updated_at": "2026-08-28T10:30:03+00:00",
        "ok": False,
        "covered": False,
        "provider_error": "provider_rate_limited",
        "cooldown_until": "2099-01-01T00:00:00+00:00",
    }
    assert module.should_reuse_finmind_segment_cache(cache, reuse_success=False) is False


def test_finmind_segment_cache_rejects_pytest_origin_and_refreshes(tmp_path: Path, monkeypatch) -> None:
    module = load_daily_module()
    ops_root = tmp_path / "data_tw" / "ops" / "daily_auto_update"
    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setattr(module, "OPS_ROOT", ops_root)
    monkeypatch.setattr(module, "FINMIND_SEGMENT_CACHE_ROOT", ops_root / "finmind_segment_cache")
    symbols_file = ops_root / "symbols.txt"
    symbols_file.parent.mkdir(parents=True, exist_ok=True)
    symbols_file.write_text("2330\n", encoding="utf-8")
    polluted_stdout = Path("/tmp/pytest-rcpt15-r13-r") / "test_finmind_segmented_update_0" / "finmind_daily_price_stdout.txt"
    polluted_stderr = polluted_stdout.with_name("finmind_daily_price_stderr.txt")
    polluted_stdout.parent.mkdir(parents=True, exist_ok=True)
    polluted_stdout.write_text(json.dumps({"archive": {"count": 1, "symbols": ["2330"], "date_min": "2026-06-26", "date_max": "2026-06-26"}, "archived_count": 1}), encoding="utf-8")
    polluted_stderr.write_text("", encoding="utf-8")
    module.write_json(
        module.finmind_segment_cache_path(segment="daily_price", end="2026-06-26"),
        {
            "schema_version": "finmind_segment_cache_v1",
            "segment": "daily_price",
            "asof": "2026-06-26",
            "updated_at": "2026-06-26T10:58:32+00:00",
            "ok": True,
            "covered": True,
            "provider_error": "",
            "cooldown_until": "",
            "stdout_path": str(polluted_stdout),
            "stderr_path": str(polluted_stderr),
            "returncode": 0,
        },
    )
    calls = []

    def runner(argv, *, cwd, stdout_path, stderr_path, timeout):
        segment = stdout_path.name.removeprefix("finmind_").removesuffix("_stdout.txt")
        calls.append(segment)
        payload = {
            "archive": {"count": 1, "symbols": ["2330"], "date_min": "2026-06-26", "date_max": "2026-06-26"},
            "archived_count": 1,
        }
        stdout_path.write_text(json.dumps(payload), encoding="utf-8")
        stderr_path.write_text("", encoding="utf-8")
        return {"ok": True, "returncode": 0, "argv": argv, "cwd": str(cwd), "stdout_path": str(stdout_path), "stderr_path": str(stderr_path), "stdout_tail": json.dumps(payload), "stderr_tail": ""}

    result = module.run_finmind_segmented_update(
        symbols_file=symbols_file,
        job_dir=ops_root / "job_polluted",
        start="2026-06-26",
        end="2026-06-26",
        timeout_seconds=10,
        skip_validate=True,
        full_scope=False,
        command_runner=runner,
    )
    merged = json.loads((ops_root / "job_polluted" / "finmind_stdout.txt").read_text(encoding="utf-8"))
    assert result["ok"] is True
    assert calls == ["daily_price"]
    assert merged["quota_control"]["cache_events"]["daily_price"]["action"] == "ignored_invalid_origin_then_refreshed"
    assert merged["quota_control"]["cache_events"]["daily_price"]["cache_origin_issue"] in {"stdout_path_outside_repo", "stdout_path_outside_daily_auto_ops", "stdout_path_pytest_origin"}


def test_finmind_orthogonal_batch_updates_checkpoint_and_reports_partial(tmp_path: Path, monkeypatch) -> None:
    module = load_daily_module()
    ops_root = tmp_path / "data_tw" / "ops" / "daily_auto_update"
    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setattr(module, "OPS_ROOT", ops_root)
    monkeypatch.setattr(module, "FINMIND_ORTHOGONAL_BATCH_STATE_ROOT", ops_root / "finmind_orthogonal_batch_state")
    symbols_file = ops_root / "symbols.txt"
    symbols_file.parent.mkdir(parents=True, exist_ok=True)
    symbols_file.write_text("2330\n2317\n2303\n", encoding="utf-8")
    calls = []

    def runner(argv, *, cwd, stdout_path, stderr_path, timeout):
        dataset = "institutional" if "institutional" in stdout_path.name else "margin"
        calls.append((dataset, Path(argv[argv.index("--symbols-file") + 1]).read_text(encoding="utf-8").splitlines()))
        section = "institutional_trades" if dataset == "institutional" else "margin_trading"
        archived_key = f"{section}_archived_count"
        payload = {
            section: {"count": 2, "symbols": ["2330", "2317"], "date_min": "2026-06-25", "date_max": "2026-06-26"},
            archived_key: 2,
        }
        stdout_path.write_text(json.dumps(payload), encoding="utf-8")
        stderr_path.write_text("", encoding="utf-8")
        return {"ok": True, "returncode": 0, "argv": argv, "cwd": str(cwd), "stdout_path": str(stdout_path), "stderr_path": str(stderr_path), "stdout_tail": json.dumps(payload), "stderr_tail": ""}

    result = module.run_finmind_orthogonal_batch_update(
        symbols_file=symbols_file,
        job_dir=ops_root / "job_batch",
        asof="2026-06-26",
        timeout_seconds=10,
        batch_size=2,
        lookback_days=7,
        cooldown_hours=6,
        command_runner=runner,
    )
    assert result["status"] == "success_partial"
    assert calls[0][1] == ["2330", "2317"]
    state = json.loads((ops_root / "finmind_orthogonal_batch_state" / "2026-06-26_institutional_margin.json").read_text(encoding="utf-8"))
    assert state["datasets"]["institutional"]["done_symbols"] == ["2317", "2330"]
    assert state["datasets"]["margin"]["done_symbols"] == ["2317", "2330"]
    summary = result["summary"]
    assert summary["coverage"]["institutional"]["done_symbol_count"] == 2
    assert summary["coverage"]["institutional"]["total_symbol_count"] == 3
    assert summary["next_retry_hint"] == "retry_next_scheduled_daily_auto_run"


def test_finmind_orthogonal_batch_cools_down_after_402(tmp_path: Path, monkeypatch) -> None:
    module = load_daily_module()
    ops_root = tmp_path / "data_tw" / "ops" / "daily_auto_update"
    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setattr(module, "OPS_ROOT", ops_root)
    monkeypatch.setattr(module, "FINMIND_ORTHOGONAL_BATCH_STATE_ROOT", ops_root / "finmind_orthogonal_batch_state")
    symbols_file = ops_root / "symbols.txt"
    symbols_file.parent.mkdir(parents=True, exist_ok=True)
    symbols_file.write_text("2330\n2317\n", encoding="utf-8")
    calls = []

    def first_runner(argv, *, cwd, stdout_path, stderr_path, timeout):
        calls.append(stdout_path.name)
        stdout_path.write_text("", encoding="utf-8")
        stderr_path.write_text("HTTPError: 402 Client Error: Payment Required", encoding="utf-8")
        return {"ok": False, "returncode": 1, "argv": argv, "cwd": str(cwd), "stdout_path": str(stdout_path), "stderr_path": str(stderr_path), "stdout_tail": "", "stderr_tail": "HTTPError: 402 Client Error: Payment Required"}

    first = module.run_finmind_orthogonal_batch_update(
        symbols_file=symbols_file,
        job_dir=ops_root / "job_first",
        asof="2026-06-26",
        timeout_seconds=10,
        batch_size=2,
        lookback_days=7,
        cooldown_hours=6,
        command_runner=first_runner,
    )
    assert first["status"] == "quota_exhausted_retry_next_day"
    assert calls == ["finmind_orthogonal_institutional_stdout.txt"]

    def second_runner(argv, *, cwd, stdout_path, stderr_path, timeout):
        raise AssertionError("cooldown should skip provider calls")

    second = module.run_finmind_orthogonal_batch_update(
        symbols_file=symbols_file,
        job_dir=ops_root / "job_second",
        asof="2026-06-26",
        timeout_seconds=10,
        batch_size=2,
        lookback_days=7,
        cooldown_hours=6,
        command_runner=second_runner,
    )
    assert second["status"] == "quota_exhausted_retry_next_day"
    assert second["summary"]["skipped_reason"] == "cooldown_active"


def test_finmind_orthogonal_batch_retries_symbols_until_both_datasets_done(tmp_path: Path, monkeypatch) -> None:
    module = load_daily_module()
    ops_root = tmp_path / "data_tw" / "ops" / "daily_auto_update"
    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setattr(module, "OPS_ROOT", ops_root)
    monkeypatch.setattr(module, "FINMIND_ORTHOGONAL_BATCH_STATE_ROOT", ops_root / "finmind_orthogonal_batch_state")
    symbols_file = ops_root / "symbols.txt"
    symbols_file.parent.mkdir(parents=True, exist_ok=True)
    symbols_file.write_text("1301\n1303\n1590\n1605\n", encoding="utf-8")
    state = {
        "schema_version": "finmind_orthogonal_batch_state_v1",
        "asof": "2026-06-26",
        "created_at": "2026-06-26T00:00:00+00:00",
        "updated_at": "2026-06-26T00:00:00+00:00",
        "symbols": ["1301", "1303", "1590", "1605"],
        "datasets": {
            "institutional": {"done_symbols": ["1301", "1303", "1590"], "failed_symbols": [], "cursor": 3, "last_status": "success"},
            "margin": {"done_symbols": ["1301", "1303"], "failed_symbols": ["1590"], "cursor": 2, "last_status": "provider_timeout"},
        },
        "cooldown_until": "",
        "last_provider_error": "provider_timeout",
    }
    module.write_json(module.finmind_orthogonal_state_path(asof="2026-06-26"), state)
    loaded = module.load_finmind_orthogonal_state(asof="2026-06-26", symbols=["1301", "1303", "1590", "1605"])
    assert module.select_orthogonal_batch_symbols(loaded, batch_size=2) == ["1590", "1605"]


def test_finmind_orthogonal_batch_new_asof_inherits_previous_done_and_skips_completed(tmp_path: Path, monkeypatch) -> None:
    module = load_daily_module()
    ops_root = tmp_path / "data_tw" / "ops" / "daily_auto_update"
    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setattr(module, "OPS_ROOT", ops_root)
    monkeypatch.setattr(module, "FINMIND_ORTHOGONAL_BATCH_STATE_ROOT", ops_root / "finmind_orthogonal_batch_state")
    baseline_done = [
        "1301",
        "1303",
        "1326",
        "1519",
        "1560",
        "1590",
        "1605",
        "1711",
        "1717",
        "1785",
        "1802",
        "1815",
        "2049",
        "2059",
        "2301",
    ]
    universe = [*baseline_done, "2303", "2308", "2313", "2317", "2324", "2327"]
    state = {
        "schema_version": "finmind_orthogonal_batch_state_v1",
        "asof": "2026-06-26",
        "created_at": "2026-06-26T00:00:00+00:00",
        "updated_at": "2026-06-26T00:00:00+00:00",
        "symbols": universe,
        "datasets": {
            "institutional": {"done_symbols": baseline_done, "failed_symbols": [], "cursor": 20, "last_status": "success"},
            "margin": {"done_symbols": baseline_done, "failed_symbols": [], "cursor": 15, "last_status": "success"},
        },
        "cooldown_until": "",
        "last_provider_error": "provider_timeout",
    }
    module.write_json(module.finmind_orthogonal_state_path(asof="2026-06-26"), state)

    loaded = module.load_finmind_orthogonal_state(asof="2026-06-29", symbols=universe)
    selected = module.select_orthogonal_batch_symbols(loaded, batch_size=5)

    assert set(baseline_done).issubset(set(loaded["datasets"]["institutional"]["done_symbols"]))
    assert set(baseline_done).issubset(set(loaded["datasets"]["margin"]["done_symbols"]))
    assert selected == ["2303", "2308", "2313", "2317", "2324"]
    assert set(selected).isdisjoint(baseline_done)
    assert loaded["datasets"]["institutional"]["cursor"] == 15
    assert loaded["datasets"]["margin"]["cursor"] == 15
    assert loaded["historical_last_provider_error"] == "provider_timeout"
    assert loaded["last_run_provider_error"] == ""
    assert loaded["current_provider_blocker"] == ""
    assert loaded["inherited_from_checkpoint"].endswith("2026-06-26_institutional_margin.json")


def test_finmind_orthogonal_batch_preserves_previous_done_after_next_batch_success(tmp_path: Path, monkeypatch) -> None:
    module = load_daily_module()
    ops_root = tmp_path / "data_tw" / "ops" / "daily_auto_update"
    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setattr(module, "OPS_ROOT", ops_root)
    monkeypatch.setattr(module, "FINMIND_ORTHOGONAL_BATCH_STATE_ROOT", ops_root / "finmind_orthogonal_batch_state")
    baseline_done = [
        "1301",
        "1303",
        "1326",
        "1519",
        "1560",
        "1590",
        "1605",
        "1711",
        "1717",
        "1785",
        "1802",
        "1815",
        "2049",
        "2059",
        "2301",
    ]
    universe = [*baseline_done, "2303", "2308", "2313", "2317", "2324", "2327"]
    symbols_file = ops_root / "symbols.txt"
    symbols_file.parent.mkdir(parents=True, exist_ok=True)
    symbols_file.write_text("\n".join(universe) + "\n", encoding="utf-8")
    module.write_json(
        module.finmind_orthogonal_state_path(asof="2026-06-26"),
        {
            "schema_version": "finmind_orthogonal_batch_state_v1",
            "asof": "2026-06-26",
            "created_at": "2026-06-26T00:00:00+00:00",
            "updated_at": "2026-06-26T00:00:00+00:00",
            "symbols": universe,
            "datasets": {
                "institutional": {"done_symbols": baseline_done, "failed_symbols": [], "cursor": 20, "last_status": "success"},
                "margin": {"done_symbols": baseline_done, "failed_symbols": [], "cursor": 15, "last_status": "success"},
            },
            "cooldown_until": "",
            "last_provider_error": "provider_timeout",
        },
    )
    calls = []

    def runner(argv, *, cwd, stdout_path, stderr_path, timeout):
        selected = Path(argv[argv.index("--symbols-file") + 1]).read_text(encoding="utf-8").splitlines()
        calls.append(selected)
        payload = {"archive": {"count": len(selected), "symbols": selected, "date_min": "2026-06-29", "date_max": "2026-06-29"}}
        stdout_path.write_text(json.dumps(payload), encoding="utf-8")
        stderr_path.write_text("", encoding="utf-8")
        return {"ok": True, "returncode": 0, "argv": argv, "cwd": str(cwd), "stdout_path": str(stdout_path), "stderr_path": str(stderr_path), "stdout_tail": json.dumps(payload), "stderr_tail": ""}

    result = module.run_finmind_orthogonal_batch_update(
        symbols_file=symbols_file,
        job_dir=ops_root / "job_batch",
        asof="2026-06-29",
        timeout_seconds=10,
        batch_size=5,
        lookback_days=7,
        cooldown_hours=6,
        command_runner=runner,
    )

    next_symbols = ["2303", "2308", "2313", "2317", "2324"]
    assert result["status"] == "success_partial"
    assert calls == [next_symbols, next_symbols]
    state = json.loads((ops_root / "finmind_orthogonal_batch_state" / "2026-06-29_institutional_margin.json").read_text(encoding="utf-8"))
    assert set(baseline_done).issubset(set(state["datasets"]["institutional"]["done_symbols"]))
    assert set(baseline_done).issubset(set(state["datasets"]["margin"]["done_symbols"]))
    assert set(next_symbols).issubset(set(state["datasets"]["institutional"]["done_symbols"]))
    assert set(next_symbols).issubset(set(state["datasets"]["margin"]["done_symbols"]))
    assert result["summary"]["coverage"]["institutional"]["done_symbol_count"] == 20
    assert result["summary"]["coverage"]["margin"]["done_symbol_count"] == 20
    assert result["summary"]["selected_symbols"] == next_symbols
    assert result["summary"]["historical_last_provider_error"] == "provider_timeout"
    assert result["summary"]["last_run_provider_error"] == ""
    assert result["summary"]["current_provider_blocker"] == ""


def test_finmind_orthogonal_batch_short_remaining_records_partial_without_reselecting_done(tmp_path: Path, monkeypatch) -> None:
    module = load_daily_module()
    ops_root = tmp_path / "data_tw" / "ops" / "daily_auto_update"
    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setattr(module, "OPS_ROOT", ops_root)
    monkeypatch.setattr(module, "FINMIND_ORTHOGONAL_BATCH_STATE_ROOT", ops_root / "finmind_orthogonal_batch_state")
    symbols_file = ops_root / "symbols.txt"
    symbols_file.parent.mkdir(parents=True, exist_ok=True)
    symbols_file.write_text("1301\n1303\n1590\n", encoding="utf-8")
    module.write_json(
        module.finmind_orthogonal_state_path(asof="2026-06-26"),
        {
            "schema_version": "finmind_orthogonal_batch_state_v1",
            "asof": "2026-06-26",
            "created_at": "2026-06-26T00:00:00+00:00",
            "updated_at": "2026-06-26T00:00:00+00:00",
            "symbols": ["1301", "1303", "1590"],
            "datasets": {
                "institutional": {"done_symbols": ["1301", "1303"], "failed_symbols": [], "cursor": 2, "last_status": "success"},
                "margin": {"done_symbols": ["1301", "1303"], "failed_symbols": [], "cursor": 2, "last_status": "success"},
            },
            "cooldown_until": "",
            "last_provider_error": "",
        },
    )

    def runner(argv, *, cwd, stdout_path, stderr_path, timeout):
        selected = Path(argv[argv.index("--symbols-file") + 1]).read_text(encoding="utf-8").splitlines()
        stdout_path.write_text(json.dumps({"selected": selected}), encoding="utf-8")
        stderr_path.write_text("", encoding="utf-8")
        return {"ok": True, "returncode": 0, "argv": argv, "cwd": str(cwd), "stdout_path": str(stdout_path), "stderr_path": str(stderr_path), "stdout_tail": json.dumps({"selected": selected}), "stderr_tail": ""}

    result = module.run_finmind_orthogonal_batch_update(
        symbols_file=symbols_file,
        job_dir=ops_root / "job_short",
        asof="2026-06-29",
        timeout_seconds=10,
        batch_size=5,
        lookback_days=7,
        cooldown_hours=6,
        command_runner=runner,
    )

    assert result["summary"]["selected_symbols"] == ["1590"]
    assert result["summary"]["selection_partial_reason"] == "remaining_symbols_below_batch_size"
    assert set(result["summary"]["selected_symbols"]).isdisjoint({"1301", "1303"})


def test_finmind_orthogonal_batch_provider_blocker_semantics_require_current_blocker(tmp_path: Path, monkeypatch) -> None:
    module = load_daily_module()
    ops_root = tmp_path / "data_tw" / "ops" / "daily_auto_update"
    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setattr(module, "OPS_ROOT", ops_root)
    monkeypatch.setattr(module, "FINMIND_ORTHOGONAL_BATCH_STATE_ROOT", ops_root / "finmind_orthogonal_batch_state")
    symbols_file = ops_root / "symbols.txt"
    symbols_file.parent.mkdir(parents=True, exist_ok=True)
    symbols_file.write_text("1301\n1303\n1590\n", encoding="utf-8")
    module.write_json(
        module.finmind_orthogonal_state_path(asof="2026-06-26"),
        {
            "schema_version": "finmind_orthogonal_batch_state_v1",
            "asof": "2026-06-26",
            "created_at": "2026-06-26T00:00:00+00:00",
            "updated_at": "2026-06-26T00:00:00+00:00",
            "symbols": ["1301", "1303", "1590"],
            "datasets": {
                "institutional": {"done_symbols": ["1301"], "failed_symbols": [], "cursor": 1, "last_status": "success"},
                "margin": {"done_symbols": ["1301"], "failed_symbols": [], "cursor": 1, "last_status": "success"},
            },
            "cooldown_until": "",
            "last_provider_error": "provider_timeout",
        },
    )

    def success_runner(argv, *, cwd, stdout_path, stderr_path, timeout):
        stdout_path.write_text("{}", encoding="utf-8")
        stderr_path.write_text("", encoding="utf-8")
        return {"ok": True, "returncode": 0, "argv": argv, "cwd": str(cwd), "stdout_path": str(stdout_path), "stderr_path": str(stderr_path), "stdout_tail": "{}", "stderr_tail": ""}

    success = module.run_finmind_orthogonal_batch_update(
        symbols_file=symbols_file,
        job_dir=ops_root / "job_success",
        asof="2026-06-29",
        timeout_seconds=10,
        batch_size=1,
        lookback_days=7,
        cooldown_hours=6,
        command_runner=success_runner,
    )
    assert success["summary"]["historical_last_provider_error"] == "provider_timeout"
    assert success["summary"]["last_run_provider_error"] == ""
    assert success["summary"]["current_provider_blocker"] == ""
    assert success["summary"]["status"] == "success_partial"

    def quota_runner(argv, *, cwd, stdout_path, stderr_path, timeout):
        stdout_path.write_text("", encoding="utf-8")
        stderr_path.write_text("HTTPError: 402 Client Error: Payment Required", encoding="utf-8")
        return {"ok": False, "returncode": 1, "argv": argv, "cwd": str(cwd), "stdout_path": str(stdout_path), "stderr_path": str(stderr_path), "stdout_tail": "", "stderr_tail": "HTTPError: 402 Client Error: Payment Required"}

    quota = module.run_finmind_orthogonal_batch_update(
        symbols_file=symbols_file,
        job_dir=ops_root / "job_quota",
        asof="2026-06-30",
        timeout_seconds=10,
        batch_size=1,
        lookback_days=7,
        cooldown_hours=6,
        command_runner=quota_runner,
    )
    assert quota["summary"]["last_run_provider_error"] == "provider_402_quota_or_payment_required"
    assert quota["summary"]["current_provider_blocker"] == "provider_402_quota_or_payment_required"
    assert quota["summary"]["status"] == "quota_exhausted_retry_next_day"


def test_installed_cron_daily_and_full_scopes_are_staggered() -> None:
    cron = (ROOT / "data_tw/ops/daily_auto_update/tw-daily-auto-update.installed.cron").read_text(encoding="utf-8")
    daily_lines = [line for line in cron.splitlines() if "TW_DAILY_AUTO_FINMIND_SCOPE=daily" in line and "run_daily_tw_stock_auto_update.py" in line]
    full_lines = [line for line in cron.splitlines() if "TW_DAILY_AUTO_FINMIND_SCOPE=full" in line and "run_daily_tw_stock_auto_update.py" in line]
    assert daily_lines
    assert full_lines
    daily_schedules = {" ".join(line.split()[:5]) for line in daily_lines}
    full_schedules = {" ".join(line.split()[:5]) for line in full_lines}
    assert daily_schedules.isdisjoint(full_schedules)
    assert "45 14 * * 1-5" in full_schedules


def test_full_scope_wires_all_hsa8_required_families_into_same_run() -> None:
    source = (ROOT / "scripts/run_daily_tw_stock_auto_update.py").read_text(encoding="utf-8")
    marker = "include_orthogonal_segments=bool("
    block = source[source.index(marker):source.index("reuse_success_cache=", source.index(marker))]
    assert 'args.finmind_scope == "full"' in block


def test_daily_scope_defers_hsa8_without_blocking_model_a_only() -> None:
    source = (ROOT / "scripts/run_daily_tw_stock_auto_update.py").read_text(encoding="utf-8")
    assert 'args.finmind_scope == "daily" and not args.enable_strict_e4_readonly_chain' in source
    assert '"status": "WAIT_FULL_SCOPE"' in source
    assert '"model_a_only_nonblocking": bool(independent_modela_baseline_enabled)' in source
    assert 'reason="model_signal_gate_failed"' in source


def test_pending_model_gate_retries_do_not_force_quota_heavy_full_scope() -> None:
    source = (ROOT / "scripts" / "run_daily_tw_stock_auto_update.py").read_text(encoding="utf-8")
    assert 'pending_requires_full_scope' not in source
    marker = "full_scope=bool("
    block = source[source.index(marker):source.index("include_orthogonal_segments=bool(", source.index(marker))]
    assert 'args.finmind_scope == "full"' in block
    assert "args.enable_strict_e4_readonly_chain" in block


def test_product_current_full_scope_bypasses_only_product_noop_and_stops_before_downstream() -> None:
    source = (ROOT / "scripts" / "run_daily_tw_stock_auto_update.py").read_text(encoding="utf-8")
    noop = 'if job["latest_before"] == asof and not args.force and not full_orthogonal_refresh_mode:'
    full_stop = 'if full_orthogonal_refresh_mode:'
    handoff = "handoff = build_real_same_run_handoff"
    provider = "if not args.skip_qlib and args.enable_legacy_provider_publish"
    model_gate = "model_signal_gate = run_model_signal_gate("
    assert noop in source
    assert source.index(full_stop, source.index("attach_orthogonal_batch_to_finmind_stdout")) < source.index(handoff)
    assert source.index(full_stop, source.index("attach_orthogonal_batch_to_finmind_stdout")) < source.index(provider)
    assert source.index(full_stop, source.index("attach_orthogonal_batch_to_finmind_stdout")) < source.index(model_gate)
    assert '"strict_model_b_generation_triggered": False' in source


def test_full_orthogonal_refresh_mode_is_exactly_scoped() -> None:
    module = load_daily_module()
    base = {
        "latest_before": "2026-09-03",
        "asof": "2026-09-03",
        "force": False,
        "skip_finmind": False,
        "finmind_scope": "full",
    }
    assert module.should_run_full_orthogonal_refresh(**base) is True
    assert module.should_run_full_orthogonal_refresh(**{**base, "finmind_scope": "daily"}) is False
    assert module.should_run_full_orthogonal_refresh(**{**base, "latest_before": "2026-09-02"}) is False
    assert module.should_run_full_orthogonal_refresh(**{**base, "force": True}) is False
    assert module.should_run_full_orthogonal_refresh(**{**base, "skip_finmind": True}) is False


def test_full_scope_uses_complete_segmented_capture_without_redundant_batch() -> None:
    source = (ROOT / "scripts" / "run_daily_tw_stock_auto_update.py").read_text(encoding="utf-8")
    marker = 'if args.finmind_scope == "full":\n'
    start = source.index(marker, source.index('job["finmind_update"] = run_finmind_segmented_update('))
    stop = source.index("if full_orthogonal_refresh_mode:", start)
    branch = source[start:stop]
    assert '"full_segmented_capture_supersedes_batch"' in branch
    assert branch.index("elif not args.disable_finmind_orthogonal_batch") < branch.index("run_finmind_orthogonal_batch_update(")


def test_full_orthogonal_evidence_is_research_only_and_requires_closed_target_scope(tmp_path, monkeypatch) -> None:
    module = load_daily_module()
    monkeypatch.setattr(module, "LATEST", tmp_path / "accepted.json")
    monkeypatch.setattr(module, "READONLY_SNAPSHOT_LATEST", tmp_path / "snapshot.json")
    monkeypatch.setattr(module, "AGENT_DAILY_PROMPT_LATEST", tmp_path / "agent.json")
    monkeypatch.setattr(module, "CONTROLLED_MODEL_SIGNAL_LATEST", tmp_path / "signal.json")
    for path in (
        module.LATEST,
        module.READONLY_SNAPSHOT_LATEST,
        module.AGENT_DAILY_PROMPT_LATEST,
        module.CONTROLLED_MODEL_SIGNAL_LATEST,
    ):
        write_payload(path, {"asof": "2026-09-03"})
    legacy = tmp_path / "data_tw/experiments/option_c_daily_signal/latest_signal.json"
    monkeypatch.setattr(module, "ROOT", tmp_path)
    write_payload(legacy, {"asof": "2026-06-01"})

    expected = ["2330", "2317"]
    stdout = tmp_path / "job/finmind_stdout.txt"
    write_payload(stdout, {
        "institutional_trades": {"count": 2, "symbols": expected, "date_max": "2026-09-03"},
        "institutional_trades_archived_count": 2,
        "margin_trading": {"count": 2, "symbols": expected, "date_max": "2026-09-03"},
        "margin_trading_archived_count": 2,
    })
    capture = {
        "expected_scope": expected,
        "returned_scope": expected,
        "absent_scope": [],
        "unknown_scope": [],
        "normalized_paths": [str(tmp_path / "institutional.normalized.json")],
    }
    write_payload(tmp_path / "institutional.normalized.json", {
        "records": [{"symbol": symbol, "trade_date": "2026-09-03"} for symbol in expected],
    })
    margin_capture = {**capture, "normalized_paths": [str(tmp_path / "margin.normalized.json")]}
    write_payload(tmp_path / "margin.normalized.json", {
        "records": [{"symbol": symbol, "trade_date": "2026-09-03"} for symbol in expected],
    })
    before = module.full_orthogonal_protected_fingerprints()
    evidence = module.build_full_orthogonal_refresh_evidence(
        job={"finmind_update": {
            "ok": True,
            "hsa8_capture": {"institutional": capture, "margin": margin_capture},
            "segment_results": {"institutional": {"ok": True}, "margin": {"ok": True}},
        }},
        job_dir=stdout.parent,
        asof="2026-09-03",
        expected_symbol_count=2,
        protected_before=before,
    )

    assert evidence["ok"] is True
    assert evidence["status"] == "FULL_ORTHOGONAL_REFRESH_PASSED"
    assert evidence["research_capture_only"] is True
    assert evidence["strict_pit_or_formal_oos_claimed"] is False
    assert evidence["strict_hsa8_ready"] is False
    assert evidence["research_observed_scope_is_not_authoritative"] is True
    assert evidence["strict_model_b_generation_triggered"] is False
    assert evidence["legacy_compatible_model_b_status"] == "AVAILABLE_READONLY"
    assert evidence["orthogonal_batch_triggered"] is False
    assert evidence["protected_latest_unchanged"]["all_protected_paths_unchanged"] is True
    assert all(not evidence[key] for key in (
        "provider_publish_triggered",
        "accepted_latest_switch_triggered",
        "controlled_signal_latest_write",
        "readonly_snapshot_latest_write",
        "agent_prompt_latest_write",
    ))


def test_full_orthogonal_evidence_fails_closed_on_unknown_scope(tmp_path, monkeypatch) -> None:
    module = load_daily_module()
    monkeypatch.setattr(module, "LATEST", tmp_path / "accepted.json")
    monkeypatch.setattr(module, "READONLY_SNAPSHOT_LATEST", tmp_path / "snapshot.json")
    monkeypatch.setattr(module, "AGENT_DAILY_PROMPT_LATEST", tmp_path / "agent.json")
    monkeypatch.setattr(module, "CONTROLLED_MODEL_SIGNAL_LATEST", tmp_path / "signal.json")
    for path in (
        module.LATEST,
        module.READONLY_SNAPSHOT_LATEST,
        module.AGENT_DAILY_PROMPT_LATEST,
        module.CONTROLLED_MODEL_SIGNAL_LATEST,
    ):
        write_payload(path, {"asof": "2026-09-03"})
    stdout = tmp_path / "job/finmind_stdout.txt"
    write_payload(stdout, {
        "institutional_trades": {"count": 1, "symbols": ["2330"], "date_max": "2026-09-03"},
        "margin_trading": {"count": 1, "symbols": ["2330"], "date_max": "2026-09-03"},
    })
    incomplete = {
        "expected_scope": ["2330", "2317"],
        "returned_scope": ["2330"],
        "absent_scope": [],
        "unknown_scope": ["2317"],
        "normalized_paths": [str(tmp_path / "incomplete.normalized.json")],
    }
    write_payload(tmp_path / "incomplete.normalized.json", {
        "records": [{"symbol": "2330", "trade_date": "2026-09-03"}],
    })

    evidence = module.build_full_orthogonal_refresh_evidence(
        job={"finmind_update": {
            "ok": True,
            "hsa8_capture": {"institutional": incomplete, "margin": incomplete},
            "segment_results": {"institutional": {"ok": True}, "margin": {"ok": True}},
        }},
        job_dir=stdout.parent,
        asof="2026-09-03",
        expected_symbol_count=2,
        protected_before=module.full_orthogonal_protected_fingerprints(),
    )

    assert evidence["ok"] is False
    assert evidence["status"] == "FULL_ORTHOGONAL_REFRESH_INCOMPLETE"
    assert evidence["required_source_checks"]["institutional_flow"]["authoritative_scope_closed"] is False
    assert evidence["required_source_checks"]["institutional_flow"]["research_scope_complete"] is False
    assert evidence["required_source_checks"]["margin_short"]["unknown_scope_count"] == 1


def test_full_orthogonal_evidence_fails_closed_when_any_protected_latest_changes(tmp_path, monkeypatch) -> None:
    module = load_daily_module()
    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setattr(module, "LATEST", tmp_path / "accepted.json")
    monkeypatch.setattr(module, "READONLY_SNAPSHOT_LATEST", tmp_path / "snapshot.json")
    monkeypatch.setattr(module, "AGENT_DAILY_PROMPT_LATEST", tmp_path / "agent.json")
    monkeypatch.setattr(module, "CONTROLLED_MODEL_SIGNAL_LATEST", tmp_path / "signal.json")
    legacy = tmp_path / "data_tw/experiments/option_c_daily_signal/latest_signal.json"
    for path in (
        module.LATEST,
        module.READONLY_SNAPSHOT_LATEST,
        module.AGENT_DAILY_PROMPT_LATEST,
        module.CONTROLLED_MODEL_SIGNAL_LATEST,
        legacy,
    ):
        write_payload(path, {"asof": "2026-09-03"})
    before = module.full_orthogonal_protected_fingerprints()
    write_payload(module.CONTROLLED_MODEL_SIGNAL_LATEST, {"asof": "2026-09-04"})

    stdout = tmp_path / "job/finmind_stdout.txt"
    expected = ["2330"]
    write_payload(stdout, {
        "institutional_trades": {"count": 1, "symbols": expected, "date_max": "2026-09-03"},
        "margin_trading": {"count": 1, "symbols": expected, "date_max": "2026-09-03"},
    })
    capture = {
        "expected_scope": expected,
        "returned_scope": expected,
        "absent_scope": [],
        "unknown_scope": [],
        "normalized_paths": [str(tmp_path / "complete.normalized.json")],
    }
    write_payload(tmp_path / "complete.normalized.json", {
        "records": [{"symbol": "2330", "trade_date": "2026-09-03"}],
    })
    evidence = module.build_full_orthogonal_refresh_evidence(
        job={"finmind_update": {
            "ok": True,
            "hsa8_capture": {"institutional": capture, "margin": capture},
            "segment_results": {"institutional": {"ok": True}, "margin": {"ok": True}},
        }},
        job_dir=stdout.parent,
        asof="2026-09-03",
        expected_symbol_count=1,
        protected_before=before,
    )

    assert evidence["ok"] is False
    assert evidence["status"] == "FULL_ORTHOGONAL_REFRESH_INCOMPLETE"
    assert evidence["protected_latest_unchanged"]["controlled_model_signal_latest"] is False
    assert evidence["protected_latest_unchanged"]["all_protected_paths_unchanged"] is False


def test_full_orthogonal_research_pass_does_not_promote_unknown_authoritative_scope(tmp_path, monkeypatch) -> None:
    module = load_daily_module()
    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setattr(module, "LATEST", tmp_path / "accepted.json")
    monkeypatch.setattr(module, "READONLY_SNAPSHOT_LATEST", tmp_path / "snapshot.json")
    monkeypatch.setattr(module, "AGENT_DAILY_PROMPT_LATEST", tmp_path / "agent.json")
    monkeypatch.setattr(module, "CONTROLLED_MODEL_SIGNAL_LATEST", tmp_path / "signal.json")
    for path in (module.LATEST, module.READONLY_SNAPSHOT_LATEST, module.AGENT_DAILY_PROMPT_LATEST, module.CONTROLLED_MODEL_SIGNAL_LATEST):
        write_payload(path, {"asof": "2026-09-04"})
    normalized = tmp_path / "observed.normalized.json"
    write_payload(normalized, {"records": [{"symbol": "2330", "trade_date": "2026-09-04"}]})
    stdout = tmp_path / "job/finmind_stdout.txt"
    write_payload(stdout, {
        "institutional_trades": {"count": 1, "symbols": ["2330"], "date_max": "2026-09-04"},
        "margin_trading": {"count": 1, "symbols": ["2330"], "date_max": "2026-09-04"},
    })
    capture = {
        "status": "captured",
        "validator_status": "BLOCKED_SOURCE_SCOPE_OR_VALIDATOR_UNPROVEN",
        "pit_status": "BLOCKED_PUBLICATION_AND_AVAILABILITY_UNPROVEN",
        "expected_scope": ["2330"],
        "returned_scope": [],
        "absent_scope": [],
        "unknown_scope": ["2330"],
        "normalized_paths": [str(normalized)],
    }
    evidence = module.build_full_orthogonal_refresh_evidence(
        job={"finmind_update": {
            "ok": True,
            "hsa8_capture": {"institutional": capture, "margin": capture},
            "segment_results": {"institutional": {"ok": True}, "margin": {"ok": True}},
        }},
        job_dir=stdout.parent,
        asof="2026-09-04",
        expected_symbol_count=1,
        protected_before=module.full_orthogonal_protected_fingerprints(),
    )

    assert evidence["ok"] is True
    assert evidence["status"] == "FULL_ORTHOGONAL_REFRESH_PASSED"
    assert evidence["strict_hsa8_ready"] is False
    assert evidence["strict_hsa8_blocked"] is True
    assert evidence["required_source_checks"]["institutional_flow"]["research_scope_complete"] is True
    assert evidence["required_source_checks"]["institutional_flow"]["authoritative_scope_closed"] is False


def test_successful_finmind_result_never_infers_provider_error_from_payload_text() -> None:
    module = load_daily_module()
    result = {
        "ok": True,
        "returncode": 0,
        "stderr_tail": "",
        "stdout_tail": '{"sha256":"abc402def","value":402}',
    }
    assert module.classify_finmind_provider_error(result) == ""


def test_installed_cron_daily_and_full_jobs_enable_ador_dry_run_safely() -> None:
    cron = (ROOT / "data_tw/ops/daily_auto_update/tw-daily-auto-update.installed.cron").read_text(encoding="utf-8")
    daily_lines = [line for line in cron.splitlines() if "TW_DAILY_AUTO_FINMIND_SCOPE=daily" in line and "run_daily_tw_stock_auto_update.py" in line]
    full_lines = [line for line in cron.splitlines() if "TW_DAILY_AUTO_FINMIND_SCOPE=full" in line and "run_daily_tw_stock_auto_update.py" in line]
    assert len(daily_lines) == 1
    assert len(full_lines) == 1

    required = [
        "ENABLE_TW_ADOR_NO_PUBLISH_ORCHESTRATION_DRY_RUN=true",
        "TW_ADOR_NO_PUBLISH_ORCHESTRATION_DRY_RUN=true",
        "TW_AGENT_DAILY_PROMPT_DRY_RUN=true",
        "ENABLE_TW_AGENT_DAILY_PROMPT_PUBLISH=false",
        "TW_AGENT_DAILY_PROMPT_PUBLISH_LATEST=false",
    ]
    for line in [*daily_lines, *full_lines]:
        assert "--disable-ador-no-publish-orchestration-dry-run" not in line
        assert "ENABLE_TW_AGENT_DAILY_PROMPT_PUBLISH=true" not in line
        assert "TW_AGENT_DAILY_PROMPT_PUBLISH_LATEST=true" not in line
        assert "--enable-legacy-provider-publish" not in line
    for token in required:
        assert token in cron


def test_installed_cron_enables_authorized_fpala_formal_provider_and_accepted_latest() -> None:
    cron = (ROOT / "data_tw/ops/daily_auto_update/tw-daily-auto-update.installed.cron").read_text(encoding="utf-8")
    required = [
        "ENABLE_TW_FPALA_FORMAL_ACCEPTED_LATEST_AUTOMATION=true",
        "TW_FPALA_NO_PUBLISH=true",
        "TW_FPALA_ALLOW_FORMAL_PROVIDER_PUBLISH=true",
        "TW_FPALA_ALLOW_ACCEPTED_LATEST_SWITCH=true",
        "TW_FPALA_EXACT_AUTHORIZATION_ID=FPALA_AUTO_ACCEPTED_LATEST_DAILY_20260911_USER_AUTHORIZED_STABLE_OPS",
    ]
    for token in required:
        assert token in cron
    assert "TW_FPALA_ALLOW_FORMAL_PROVIDER_PUBLISH=false" not in cron
    assert "TW_FPALA_ALLOW_ACCEPTED_LATEST_SWITCH=false" not in cron
    assert "TW_DAILY_AUTO_ENABLE_LEGACY_PROVIDER_PUBLISH=true" in cron
    assert "--enable-legacy-provider-publish" not in cron


def test_m3_script_audit_fails_when_provider_paths_are_default_reachable(tmp_path: Path) -> None:
    unsafe_script = tmp_path / "unsafe_daily.py"
    unsafe_script.write_text(
        """
provider_publish_triggered = False
cmd = 'examples/tw/run_option_c_yahoo_scrapling_refresh.py'
publish = 'examples/tw/publish_option_c_yahoo_scrapling_refresh.py'
def publish_accepted_latest(asof):
    return {'ok': True}
payload = {'confirm_accepted_latest_scheduler': True}
if not args.skip_qlib:
    provider_publish_triggered = True
""",
        encoding="utf-8",
    )
    code, result = run_validator("--audit-script", str(unsafe_script))
    assert code != 0
    assert result["ok"] is False
    error_codes = {item["code"] for item in result["errors"]}
    assert {
        "default_provider_refresh_reachable",
        "default_provider_publish_reachable",
        "default_accepted_latest_reachable",
        "legacy_provider_gate_missing",
    }.issubset(error_codes)
