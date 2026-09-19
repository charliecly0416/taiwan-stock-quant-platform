from __future__ import annotations

from pathlib import Path

from scripts.tw_daily_runtime_stages import (
    RuntimeDescriptorError,
    build_stage_facade,
    descriptor_summary,
    load_runtime_descriptor,
    no_publish_fingerprint_audit,
    run_no_publish_terminal_orchestrator,
)
from scripts.tw_daily_stage_adapters import (
    build_model_a_signal_callback,
    build_model_b_shadow_callback,
    build_named_stage_adapters,
    build_staged_artifact_publish_callback,
    inspect_model_a_signal_artifact,
    project_legacy_model_a_signal_contract,
    validate_model_a_top50,
    stage_contract_summary,
)


def test_descriptor_summary_matches_frozen_runtime_truth() -> None:
    summary = descriptor_summary()
    assert summary["active_model_id"] == "e4_frozen_qlib_2018_2022"
    assert summary["active_status"] == "MODEL_A_ONLY"
    assert summary["strategy_rule"] == "top50_exit_one_worst_sell"
    assert summary["execution_price_mode"] == "next_open"
    assert summary["shadow_model_id"] == "e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025"
    assert summary["shadow_production_default"] is False


def test_schema_is_enforced_for_runtime_loader(tmp_path: Path) -> None:
    descriptor = tmp_path / "descriptor.yaml"
    descriptor.write_text("{}\n", encoding="utf-8")
    try:
        load_runtime_descriptor(descriptor_path=descriptor)
    except RuntimeDescriptorError as exc:
        assert "invalid active baseline descriptor" in str(exc)
    else:
        raise AssertionError("invalid descriptor unexpectedly loaded")


def test_stage_facade_is_injectable_and_preserves_callback_result() -> None:
    stages = build_stage_facade(signal=lambda asof: {"asof": asof, "ok": True})
    assert stages["signal"].run("2026-09-04")["ok"] is True
    assert stages["acquisition"].run()["status"] == "NOT_IMPLEMENTED_LEGACY_PATH"


def test_no_publish_audit_compares_actual_before_after() -> None:
    before = {"latest": {"exists": True, "size": 1, "sha256": "a"}}
    after = {"latest": {"exists": True, "size": 2, "sha256": "b"}}
    audit = no_publish_fingerprint_audit(before, after)
    assert audit["ok"] is False
    assert audit["comparison"]["latest"] is False
    assert audit["publish_allowed"] is False


def test_named_stage_adapters_expose_model_a_and_model_b_boundaries() -> None:
    adapters = build_named_stage_adapters(
        acquisition=lambda context: {"ok": True},
        model_a_signal=lambda context: {"ok": True, "model": "a"},
        model_b_shadow=lambda context: {"ok": True, "model": "b", "shadow": True},
    )
    assert adapters["signal"].run({})["stage_contract"] == "model_a_signal.v1"
    assert adapters["model_b_shadow"].run({})["shadow"] is True
    summary = stage_contract_summary(adapters)
    assert summary["model_b_active_selection"] is False
    assert summary["stages"]["acquisition"]["callback_bound"] is True


def test_missing_model_a_callback_fails_closed_without_model_b_fallback() -> None:
    adapters = build_named_stage_adapters(model_b_shadow=lambda context: {"ok": True, "model": "b"})
    result = adapters["signal"].run({})
    assert result["ok"] is False
    assert result["status"] == "model_a_signal_callback_missing"
    assert result["model_b_active_selection"] is False


def test_model_a_signal_callback_reads_existing_artifact_without_writes() -> None:
    signal_dir = Path("data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/dng9_daily_auto_modela_20260911_20260911T103001Z")
    result = inspect_model_a_signal_artifact(signal_dir)
    assert result["ok"] is True
    assert result["status"] == "READY"
    assert result["row_count"] == 150
    assert len(result["signal_checksum"]) == 64


def test_model_b_shadow_isolated_to_model_a_top50_and_job_dir(tmp_path: Path) -> None:
    signal_dir = Path("data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/dng9_daily_auto_modela_20260911_20260911T103001Z")
    model_a = build_model_a_signal_callback(signal_dir)({})
    shadow = build_model_b_shadow_callback()({"model_a_signal": model_a, "job_dir": tmp_path})
    assert shadow["ok"] is True
    assert shadow["candidate_universe"] == "model_a_top50_only"
    assert shadow["candidate_universe_count"] == 50
    assert shadow["published"] is False
    assert shadow["shadow_score_generated"] is False
    assert (tmp_path / "model_b_shadow/shadow_observation.json").is_file()


def test_model_b_shadow_blocks_missing_or_invalid_model_a() -> None:
    callback = build_model_b_shadow_callback()
    result = callback({"model_a_signal": {"ok": False, "status": "BLOCKED_SIGNAL_SCHEMA_MISMATCH"}})
    assert result["ok"] is False
    assert result["status"] == "BLOCKED_MODEL_A_SIGNAL"
    assert result["model_b_active_selection"] is False


def test_legacy_projection_is_independent_and_matches_model_a_callback() -> None:
    signal_dir = Path("data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/dng9_daily_auto_modela_20260911_20260911T103001Z")
    legacy = project_legacy_model_a_signal_contract(signal_dir)
    new = build_model_a_signal_callback(signal_dir)({})
    for key in ("ok", "status", "model_id", "row_count", "signal_checksum", "schema_fields"):
        assert legacy[key] == new[key]


def test_top50_validator_positive_and_negative_fixtures() -> None:
    positive = [{"instrument": f"TW{i:04d}", "full_qlib_rank": str(i)} for i in range(1, 51)]
    assert validate_model_a_top50(positive)["ok"] is True
    duplicate_rank = [dict(row) for row in positive]
    duplicate_rank[-1]["full_qlib_rank"] = "1"
    assert validate_model_a_top50(duplicate_rank)["ok"] is False
    missing_candidate = [dict(row) for row in positive]
    missing_candidate[-1]["instrument"] = ""
    assert validate_model_a_top50(missing_candidate)["ok"] is False


def test_staged_publish_authorization_and_rollback_guards(tmp_path: Path) -> None:
    candidate = tmp_path / "candidate.json"
    candidate.write_text("candidate\n", encoding="utf-8")
    rollback = tmp_path / "rollback.json"
    rollback.write_text("rollback\n", encoding="utf-8")
    callback = build_staged_artifact_publish_callback(rollback_source=rollback)
    denied = callback({"job_dir": str(tmp_path), "candidate_path": str(candidate), "authorization": {}})
    assert denied["status"] == "BLOCKED_UNAUTHORIZED_CANDIDATE_PUBLISH"
    allowed = callback({"job_dir": str(tmp_path), "candidate_path": str(candidate), "authorization": {"allow_candidate_publish": True, "authorization_id": "arch2c-test", "publish_mode": "candidate_only"}})
    assert allowed["ok"] is True
    assert allowed["protected_pointer_write"] is False
    assert (tmp_path / "candidate_publish/rollback_manifest.json").is_file()
    mismatch = callback({"job_dir": str(tmp_path), "candidate_path": str(candidate), "authorization": {"allow_candidate_publish": True, "authorization_id": "arch2c-test", "publish_mode": "candidate_only"}, "rollback_checksum": "bad"})
    assert mismatch["status"] == "BLOCKED_ROLLBACK_CHECKSUM_MISMATCH"


def test_no_publish_terminal_orchestrator_preserves_legacy_terminal(tmp_path: Path) -> None:
    protected = tmp_path / "latest.json"
    protected.write_text("latest\n", encoding="utf-8")
    callbacks = {name: (lambda context, stage=name: {"ok": True, "status": "READY", "stage": stage}) for name in ("acquisition", "readiness", "signal", "strategy", "artifact_publish", "ops_status")}
    result = run_no_publish_terminal_orchestrator(
        build_stage_facade(**callbacks), asof="2026-09-12", job_id="arch2d", protected_paths={"latest": protected}, root=tmp_path,
    )
    assert result["ok"] is True
    assert result["status"] == "publish_precondition_blocked"
    assert result["parity"]["stage_order_equal"] is True
    assert result["parity"]["latest_parity"] is True
    assert result["publish_allowed"] is False


def test_staged_publish_path_and_rollback_source_guards(tmp_path: Path) -> None:
    job = tmp_path / "job"
    job.mkdir()
    outside = tmp_path / "outside.json"
    outside.write_text("outside\n", encoding="utf-8")
    callback = build_staged_artifact_publish_callback(rollback_source=tmp_path / "missing.json")
    auth = {"allow_candidate_publish": True, "authorization_id": "arch2d", "publish_mode": "candidate_only"}
    result = callback({"job_dir": str(job), "candidate_path": str(outside), "authorization": auth})
    assert result["status"] == "BLOCKED_ROLLBACK_SOURCE_MISSING"
    rollback = tmp_path / "rollback.json"
    rollback.write_text("rollback\n", encoding="utf-8")
    candidate = tmp_path / "candidate.json"
    candidate.write_text("candidate\n", encoding="utf-8")
    callback = build_staged_artifact_publish_callback(rollback_source=rollback)
    result = callback({"job_dir": str(job), "candidate_path": str(outside), "authorization": auth})
    assert result["status"] == "BLOCKED_CANDIDATE_PATH_OUTSIDE_JOB_DIR"
