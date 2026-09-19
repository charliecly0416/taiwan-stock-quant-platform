import importlib.util
from pathlib import Path
import pytest


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/run_daily_tw_stock_auto_update.py"


def _module():
    spec = importlib.util.spec_from_file_location("hsa8p6_daily", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_skip_finmind_has_explicit_stop_before_qlib_gate():
    source = SCRIPT.read_text(encoding="utf-8")
    skip = source.index("    if args.skip_finmind:\n        handoff =")
    qlib = source.index("if not args.skip_qlib", skip)
    block = source[skip:qlib]
    assert "same_run_handoff_failed" in block
    assert "return 2" in block


def test_empty_or_cached_capture_cannot_build_runtime_handoff(tmp_path):
    module = _module()
    job = {"job_id": "daily.acquire.20260827.real", "asof": "2026-08-27", "finmind_update": {}}
    result = module.build_real_same_run_handoff(job=job, job_dir=tmp_path, symbols=["2330"])
    assert result["ok"] is False
    assert "error" in result
    assert not (tmp_path / "same_run_handoff" / "same_run_acquisition_handoff_manifest.json").exists()


def test_hsa8_builder_is_before_provider_and_latest_sections():
    source = SCRIPT.read_text(encoding="utf-8")
    assert source.index("handoff = build_real_same_run_handoff") < source.index("if not args.skip_qlib")
    assert source.index("handoff = build_real_same_run_handoff") < source.index("if not args.skip_qlib and args.enable_legacy_provider_publish")


def test_non_strict_hsa8_failure_blocks_strict_model_b_but_not_legacy_readonly_or_modela():
    source = SCRIPT.read_text(encoding="utf-8")
    failure = source.index('if not handoff.get("ok")')
    qlib = source.index("if not args.skip_qlib", failure)
    block = source[failure:qlib]
    assert "if args.enable_strict_e4_readonly_chain" in block
    assert "modela_observation_lane_enabled" in source
    assert "model_a_only_nonblocking" in source
    assert 'same_run_handoff_nonblocking_for_modela_baseline' in block
    assert '"blocks_strict_model_b_generation"' in source
    assert '"blocks_legacy_readonly_model_b": False' in source
    assert '"legacy_compatible_model_b_status"' in source
    assert '"blocks_model_b"' not in source
    assert "not args.skip_qlib and args.enable_legacy_provider_publish" in source
    assert 'independent_yahoo_adjusted_modela_baseline_enabled' in source
    assert 'model_b_enabled=bool(args.enable_mbcds3_daily_shadow)' in source
    assert 'model_b_hsa8_ready=bool(\n            args.enable_mbcds3_daily_shadow' in source
    assert 'and (job.get("same_run_handoff") or {}).get("ok")' in source


def test_installed_daily_and_full_cron_disable_model_b_shadow():
    cron = (ROOT / "data_tw/ops/daily_auto_update/tw-daily-auto-update.installed.cron").read_text(encoding="utf-8")
    assert "ENABLE_TW_MBCDS3_DAILY_SHADOW=false" in cron
    assert "ENABLE_TW_MBCDS3_DAILY_SHADOW=true" not in cron
    scheduled = [line for line in cron.splitlines() if "run_daily_tw_stock_auto_update.py" in line]
    assert len(scheduled) == 2
    assert any("TW_DAILY_AUTO_FINMIND_SCOPE=daily" in line for line in scheduled)
    assert any("TW_DAILY_AUTO_FINMIND_SCOPE=full" in line for line in scheduled)
    assert all("ENABLE_TW_MBCDS3_DAILY_SHADOW=true" not in line for line in scheduled)


def test_model_b_execution_is_after_explicit_hsa8_readiness_gate():
    source = SCRIPT.read_text(encoding="utf-8")
    gate = source.index("if not model_b_enabled or not model_b_hsa8_ready:")
    model_b_input = source.index("modelb_input = command_runner(", gate)
    assert gate < model_b_input


@pytest.mark.parametrize(
    ("model_b_enabled", "model_b_hsa8_ready", "expected_blocker"),
    [
        (True, False, "same_run_hsa8_adjusted_price_twii_or_orthogonal_not_ready"),
        (False, True, "model_b_disabled_for_modela_only_baseline"),
    ],
)
def test_model_b_requires_explicit_enable_and_hsa8_readiness(
    tmp_path,
    monkeypatch,
    model_b_enabled,
    model_b_hsa8_ready,
    expected_blocker,
):
    module = _module()
    monkeypatch.setattr(module, "CALENDAR", tmp_path / "day.txt")
    monkeypatch.setattr(module, "MODEL_SIGNAL_GATE_DRY_RUN_SUMMARY", tmp_path / "summary.json")
    monkeypatch.setattr(module, "DNG9_MODEL_SIGNAL_GATE_VALIDATION", tmp_path / "validation.json")
    (tmp_path / "day.txt").write_text("2026-08-27\n", encoding="utf-8")

    # The formal Model A path requires an explicit PIT cutoff.  Keep the
    # fixture isolated from repository artifacts while still allowing the
    # gate to reach the HSA8 decision branch after a successful Model A score.
    finder_calls = []
    valid_catalog = {
        "asof": "2026-08-27",
        "run_id": "fixture-modela-run",
        "pipeline_status": "SCORED_ASOF_TARGET",
        "score_status": "SCORED_ASOF_TARGET",
        "raw_scores_rows": 150,
        "signals_rows": 150,
        "artifacts": {
            "model_inference_input": "fixture/model_inference_input.json",
            "score_job": "fixture/score_job.json",
            "model_signal": "fixture/model_signal.json",
        },
    }

    def isolated_modela_finder(asof):
        finder_calls.append(asof)
        if len(finder_calls) == 1:
            return {"ok": False, "asof": asof, "errors": ["fixture_not_built_yet"]}
        return {
            "ok": True,
            "status": "READY_ISOLATED_CANDIDATE",
            "asof": asof,
            "catalog_path": "fixture/catalog.json",
            "catalog": valid_catalog,
            "artifacts": valid_catalog["artifacts"],
            "raw_scores_rows": 150,
            "signals_rows": 150,
        }

    monkeypatch.setattr(module, "find_validated_isolated_modela_artifact", isolated_modela_finder)

    calls = []

    def command_runner(command, **kwargs):
        calls.append(command)
        stdout_path = kwargs.get("stdout_path")
        if stdout_path:
            stdout_path.parent.mkdir(parents=True, exist_ok=True)
            stdout_path.write_text(
                '{"pipeline_status":"SCORED_ASOF_TARGET","artifacts":{"model_signal":"model-a.json"}}\n',
                encoding="utf-8",
            )
        return {"ok": True, "returncode": 0, "stdout_path": str(stdout_path or "")}

    result = module.run_model_signal_gate(
        asof="2026-08-27",
        job_id="compatibility-test",
        job_dir=tmp_path,
        enabled=True,
        model_b_enabled=model_b_enabled,
        model_b_hsa8_ready=model_b_hsa8_ready,
        decision_cutoff="2026-08-27T10:00:00+00:00",
        command_runner=command_runner,
    )

    assert result["ok"] is True
    assert result["model_a_score_job_triggered"] is True
    assert result["model_a_status"] == "SCORED_ASOF_TARGET"
    assert result["model_b_status"] == "BLOCKED_INPUT_NOT_READY"
    assert result["model_b_enabled"] is model_b_enabled
    assert result["model_b_hsa8_ready"] is model_b_hsa8_ready
    assert result["model_b_blockers"] == [expected_blocker]
    assert result["summary"]["strict_model_b_status"] == "BLOCKED_INPUT_NOT_READY"
    assert result["summary"]["legacy_compatible_model_b_status"] == "AVAILABLE_READONLY"
    assert result["summary"]["legacy_model_b_blocked_by_hsa8"] is False
    assert result["summary"]["legacy_compatible_model_b"] == {
        "model_id": module.MODELB_LTR_MODEL_ID,
        "status": "AVAILABLE_READONLY",
        "evidence_class": "legacy_exploratory",
        "usage": "readonly_comparison",
        "formal_oos_eligible": False,
        "production_default_eligible": False,
        "strict_retrain_or_new_scoring_eligible": False,
    }
    assert result["model_b_ltr_score_job_triggered"] is False
    modela_input_script = str(module.MODELA_INPUT_BUILD_SCRIPT.relative_to(module.ROOT))
    modela_score_script = str(module.MODELA_SCORE_JOB_SCRIPT.relative_to(module.ROOT))
    modelb_input_script = str(module.MODELB_LTR_INPUT_BUILD_SCRIPT.relative_to(module.ROOT))
    modelb_score_script = str(module.MODELB_LTR_SCORE_JOB_SCRIPT.relative_to(module.ROOT))
    assert any(modela_input_script in " ".join(map(str, command)) for command in calls)
    assert any(modela_score_script in " ".join(map(str, command)) for command in calls)
    assert not any(modelb_input_script in " ".join(map(str, command)) for command in calls)
    assert not any(modelb_score_script in " ".join(map(str, command)) for command in calls)


def test_daily_scope_hsa8_nonblocking_modela_main_path_preserves_protected_latest(tmp_path, monkeypatch, capsys):
    """Exercise the unattended daily state machine without provider/network calls."""
    module = _module()
    ops_root = tmp_path / "ops"
    monkeypatch.setattr(module, "OPS_ROOT", ops_root)
    monkeypatch.setattr(module, "PENDING_ASOF", ops_root / "pending_asof.json")
    monkeypatch.setattr(module, "LATEST", tmp_path / "provider_latest.json")
    monkeypatch.setattr(module, "READONLY_SNAPSHOT_LATEST", tmp_path / "readonly_latest.json")
    monkeypatch.setattr(module, "AGENT_DAILY_PROMPT_LATEST", tmp_path / "agent_latest.json")
    monkeypatch.setattr(module, "CONTROLLED_MODEL_SIGNAL_LATEST", tmp_path / "signal_latest.json")
    monkeypatch.setattr(module, "READONLY_DAILY_INTEGRATION_AUDIT", tmp_path / "readonly_audit.json")
    monkeypatch.setattr(module, "UNIVERSE", tmp_path / "universe.txt")
    for path in (
        module.LATEST,
        module.READONLY_SNAPSHOT_LATEST,
        module.AGENT_DAILY_PROMPT_LATEST,
        module.CONTROLLED_MODEL_SIGNAL_LATEST,
    ):
        path.write_text('{"asof":"2026-09-08"}\n', encoding="utf-8")
    module.UNIVERSE.write_text("2330\n", encoding="utf-8")
    monkeypatch.setattr(module, "latest_asof", lambda: "2026-09-08")

    def materialize(job_dir):
        symbols = job_dir / "symbols.txt"
        symbols.write_text("2330\n", encoding="utf-8")
        return symbols

    fixed_fingerprints = {
        "readonly": {"sha256": "readonly-before"},
        "agent": {"sha256": "agent-before"},
        "provider": {"sha256": "provider-before"},
        "legacy": {"sha256": "legacy-before"},
    }
    monkeypatch.setattr(module, "materialize_symbols", materialize)
    monkeypatch.setattr(module, "protected_latest_fingerprints", lambda **_: fixed_fingerprints)
    monkeypatch.setattr(module, "run_finmind_segmented_update", lambda **_: {"ok": True, "segment_results": {}})
    monkeypatch.setattr(module, "run_finmind_orthogonal_batch_update", lambda **_: {"ok": True, "status": "success"})
    monkeypatch.setattr(module, "attach_orthogonal_batch_to_finmind_stdout", lambda *_, **__: None)
    monkeypatch.setattr(module, "run_provider_candidate_refresh_gate", lambda **_: {"ok": True, "attempted": False, "status": "READY_REUSED"})
    monkeypatch.setattr(module, "attach_fpala_formal_accepted_latest_preflight", lambda *_, **__: {"ok": True, "attempted": False})
    monkeypatch.setattr(module, "run_model_signal_gate", lambda **_: {
        "ok": True,
        "attempted": True,
        "model_a_score_job_triggered": True,
        "model_b_ltr_score_job_triggered": False,
        "provider_publish_triggered": False,
        "accepted_latest_switch": False,
    })
    monkeypatch.setattr(module, "build_mbcds3_source_availability_ledger", lambda **_: {"ok": True})
    monkeypatch.setattr(module, "build_mbcds3_daily_inventory_bridge", lambda **_: {"ok": True, "inventory_path": ""})
    monkeypatch.setattr(module, "run_mbcds3_daily_shadow_accumulation", lambda **_: {"ok": True, "attempted": False, "status": "DISABLED"})
    monkeypatch.setattr(module, "run_mbcds35_prospective_shadow", lambda **_: {"ok": True, "status": "DISABLED"})
    monkeypatch.setattr(module, "attach_qald_accepted_latest_candidate_preflight", lambda *_, **__: {"ok": True, "attempted": False})
    monkeypatch.setattr(module, "run_strict_e4_readonly_chain", lambda **_: {"ok": True, "attempted": False})
    monkeypatch.setattr(module, "run_ador_no_publish_orchestration_dry_run", lambda **_: {"ok": True, "attempted": False})
    monkeypatch.setattr(module, "run_dapr18_controlled_latest_orchestration", lambda **_: {"ok": True, "attempted": False})
    monkeypatch.setattr(module, "run_readonly_strategy_snapshot_publish", lambda **_: {"ok": True, "attempted": False})
    captured = {}
    monkeypatch.setattr(module, "finalize_job", lambda job, **_: captured.update(job))

    monkeypatch.setattr("sys.argv", [
        "runner", "--asof", "2026-09-09", "--finmind-scope", "daily", "--enable-model-signal-gate",
    ])
    assert module.main() == 0
    capsys.readouterr()
    assert captured["status"] == "daily_auto_update_passed"
    assert captured["same_run_handoff"]["status"] == "WAIT_FULL_SCOPE"
    assert captured["same_run_handoff_nonblocking_for_modela_baseline"] is True
    assert captured["model_b_hsa8_gate"]["model_a_only_nonblocking"] is True
    assert captured["model_signal_gate"]["model_b_ltr_score_job_triggered"] is False
    assert captured["provider_publish_triggered"] is False
    assert captured["model_signal_gate"]["accepted_latest_switch"] is False
    assert captured["runtime_protected_before"] == captured["runtime_protected_after"]
    assert not (ops_root / "pending_asof.json").exists()


def test_skip_gate_observably_calls_no_downstream_command(tmp_path, monkeypatch):
    module = _module()
    monkeypatch.setattr(module, "OPS_ROOT", tmp_path / "ops")
    monkeypatch.setattr(module, "PENDING_ASOF", tmp_path / "pending.json")
    monkeypatch.setattr(module, "LATEST", tmp_path / "latest.json")
    calls = []
    monkeypatch.setattr(module, "run_cmd", lambda *args, **kwargs: calls.append((args, kwargs)))
    monkeypatch.setattr(module, "finalize_job", lambda *args, **kwargs: None)

    monkeypatch.setattr("sys.argv", ["runner", "--asof", "2026-08-27", "--skip-finmind", "--skip-qlib"])
    assert module.main() == 2
    assert calls == []


@pytest.mark.parametrize("failure", ["twii_blocked", "segment_skip", "cache_reuse", "empty_capture", "scope_mismatch", "pit_mismatch"])
def test_hsa8_failure_modes_are_zero_call_before_downstream(tmp_path, monkeypatch, failure):
    """Every acquisition-gate failure returns before any downstream command."""
    module = _module()
    job = {"job_id": "daily.acquire.20260827.real", "asof": "2026-08-27", "finmind_update": {}}
    captures = {}
    for family in ("daily_price", "institutional", "margin"):
        captures[family] = {
            "status": "captured", "source_id": family, "provider": "FinMind",
            "endpoint_version": "v1", "parser_version": "v1", "schema_version": "v1",
            "request_parameters": {}, "http_status": 200, "transport_identity": "https",
            "source_published_at": "2026-08-27T00:00:00+00:00", "available_at": "2026-08-27T01:00:00+00:00",
            "fetched_at": "2026-08-27T02:00:00+00:00", "trade_date": "2026-08-27", "validator_status": "PASS",
            "expected_scope": ["2330"], "returned_scope": ["2330"], "absent_scope": [], "unknown_scope": [],
            "raw_paths": [], "normalized_paths": [],
        }
    captures["twii"] = {**captures["daily_price"], "source_id": "twii", "provider": "TWSE"}
    if failure in {"twii_blocked", "empty_capture"}:
        captures["twii"]["validator_status"] = "BLOCKED"
    elif failure == "segment_skip":
        captures["institutional"] = {}
    elif failure == "cache_reuse":
        captures["margin"]["status"] = "cached"
    elif failure == "scope_mismatch":
        captures["twii"]["returned_scope"] = ["TWII"]
    elif failure == "pit_mismatch":
        captures["twii"]["available_at"] = "2026-08-27T03:00:00+00:00"
    job["finmind_update"] = {"segment_results": {}, "hsa8_capture": captures}
    result = module.build_real_same_run_handoff(job=job, job_dir=tmp_path, symbols=["2330"])
    assert result["ok"] is False
    # The builder is the gate itself; only downstream work must remain zero-call.
    source = Path(module.__file__).read_text(encoding="utf-8")
    assert source.index('if not handoff.get("ok")') < source.index("if not args.skip_qlib")
