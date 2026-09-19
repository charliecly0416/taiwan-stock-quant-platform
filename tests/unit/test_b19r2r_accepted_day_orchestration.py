from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

ROOT = Path(__file__).resolve().parents[2]


def load_daily():
    spec = importlib.util.spec_from_file_location("daily_b19_accepted_test", ROOT / "scripts/run_daily_tw_stock_auto_update.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("shadow_enabled,shadow_ok", [(True, True), (True, False), (False, False)])
def test_accepted_full_incomplete_reaches_shadow_without_publishing_or_pending(tmp_path, monkeypatch, shadow_enabled, shadow_ok):
    module = load_daily()
    monkeypatch.setattr(module, "OPS_ROOT", tmp_path / "ops")
    monkeypatch.setattr(module, "FINMIND_LOGICAL_ACQUISITION_ROOT", tmp_path / "logical")
    universe = tmp_path / "symbols.txt"
    universe.write_text("2330\n7769\n")
    monkeypatch.setattr(module, "UNIVERSE", universe)
    monkeypatch.setattr(module, "taipei_now", lambda: datetime(2026, 9, 18, 22, 45, tzinfo=ZoneInfo("Asia/Taipei")))
    monkeypatch.setattr(module, "resolve_asof_with_terminal_quarantine", lambda *a, **kw: ("2026-09-18", "today", {}))
    monkeypatch.setattr(module, "latest_asof", lambda: "2026-09-18")
    monkeypatch.setattr(module, "protected_latest_fingerprints", lambda **kw: {})
    monkeypatch.setattr(module, "full_orthogonal_protected_fingerprints", lambda: {})
    monkeypatch.setattr(module.logical_acquisition, "load_state", lambda *a, **kw: {"logical_run_id": "capture_today"})
    monkeypatch.setattr(module, "run_finmind_segmented_update", lambda **kw: {"ok": False})
    monkeypatch.setattr(module, "run_o4_prospective_shadow_nonblocking", lambda **kw: {"attempted": False})
    # Full-universe margin coverage can fail for TW7769. The dedicated B
    # runner remains responsible for its reduced candidate scope and PIT gate.
    evidence = {"ok": False, "status": "FULL_ORTHOGONAL_REFRESH_INCOMPLETE", "protected_latest_unchanged": {"all_protected_paths_unchanged": True}}
    monkeypatch.setattr(module, "build_full_orthogonal_refresh_evidence", lambda **kw: evidence)
    shadow_calls = []
    monkeypatch.setattr(module, "run_b19r2r_for_accepted_day_nonblocking", lambda **kw: shadow_calls.append(kw) or {"shadow_ok": shadow_ok, "status": "READY" if shadow_ok else "BLOCKED_MARGIN"})
    final_jobs = []
    monkeypatch.setattr(module, "finalize_job", lambda job, **kw: final_jobs.append(dict(job)))

    def forbidden(*a, **kw):
        pytest.fail("accepted-day shadow attempted a mainline write")

    pending_calls = []
    monkeypatch.setattr(module, "set_pending_asof", lambda *a, **kw: pending_calls.append((a, kw)))
    monkeypatch.setattr(module, "clear_pending_asof", forbidden)
    monkeypatch.setattr(module, "run_cmd", forbidden)
    monkeypatch.setattr(module, "publish_accepted_latest", forbidden)
    monkeypatch.setenv("TW_DAILY_AUTO_ENABLE_B19R2R_SHADOW", "false")
    argv = ["daily", "--finmind-scope", "full", "--enable-model-signal-gate"]
    if shadow_enabled:
        argv.append("--enable-b19r2r-shadow")
    monkeypatch.setattr(sys, "argv", argv)
    assert module.main() == (0 if shadow_enabled else 2)
    if not shadow_enabled:
        assert shadow_calls == []
        assert pending_calls[0][1]["reason"] == "full_orthogonal_refresh_incomplete"
        return
    assert pending_calls == []
    assert len(shadow_calls) == 1
    assert shadow_calls[0]["symbols"] == ["2330", "7769"]
    assert final_jobs[0]["full_orthogonal_refresh"]["ok"] is False
    assert final_jobs[0]["accepted_day_shadow_only"] is True
    assert final_jobs[0]["latest_after"] == "2026-09-18"
    assert "pending_asof_set" not in final_jobs[0]


def test_accepted_day_missing_snapshot_is_a_shadow_blocker(tmp_path, monkeypatch):
    module = load_daily()
    artifact = tmp_path / "a"
    artifact.mkdir()
    artifact.joinpath("manifest.json").write_text(json.dumps({"source_acquisition_run_id": "same_logical_capture"}))
    pointer = tmp_path / "latest.json"
    pointer.write_text(json.dumps({"asof": "2026-09-18", "canonical_artifact_dir": str(artifact)}))
    monkeypatch.setattr(module, "CONTROLLED_MODEL_SIGNAL_LATEST", pointer)
    monkeypatch.setattr(module, "OPS_ROOT", tmp_path / "ops")
    result = module.run_b19r2r_for_accepted_day_nonblocking(job={"job_id": "full_today", "acquisition_logical_run_id": "same_logical_capture"}, job_dir=tmp_path, asof="2026-09-18", symbols=["2330"])
    assert result["status"] == "BLOCKED_ACCEPTED_DAY_INPUT"
    assert result["warning"] == "PUBLISHED_MODEL_A_PROVIDER_SNAPSHOT_MISSING"
    assert result["mainline_blocking"] is False
    assert result["pending_asof_set"] is False


def test_accepted_day_reuses_exact_model_a_origin_snapshot(tmp_path, monkeypatch):
    module = load_daily()
    artifact = tmp_path / "a"
    artifact.mkdir()
    artifact.joinpath("manifest.json").write_text(json.dumps({"source_acquisition_run_id": "same_logical_capture"}))
    pointer = tmp_path / "latest.json"
    pointer.write_text(json.dumps({"asof": "2026-09-18", "canonical_artifact_dir": str(artifact)}))
    ops = tmp_path / "ops"
    previous = ops / "a_today"
    previous.mkdir(parents=True)
    publish_id = "option_c_yahoo_scrapling_publish_today"
    previous.joinpath("job.json").write_text(json.dumps({"job_id": "a_today", "asof": "2026-09-18", "latest_after": "2026-09-18", "acquisition_logical_run_id": "same_logical_capture", "publish_job_id": publish_id, "model_signal_gate": {"ok": True, "summary": {"model_a_signal_path": str(artifact)}}}))
    snapshot = tmp_path / "qlib/data_tw/experiments/option_c_ops" / publish_id / "tmp/formal_provider_rebuild"
    snapshot.mkdir(parents=True)
    monkeypatch.setattr(module, "CONTROLLED_MODEL_SIGNAL_LATEST", pointer)
    monkeypatch.setattr(module, "OPS_ROOT", ops)
    monkeypatch.setattr(module, "QLIB", tmp_path / "qlib")
    monkeypatch.setattr(module, "build_real_same_run_handoff", lambda **kw: {"ok": False})
    calls = []
    monkeypatch.setattr(module, "run_b19r2r_daily_shadow_nonblocking", lambda **kw: calls.append(kw) or {"shadow_ok": True})
    job = {"job_id": "full_today", "acquisition_logical_run_id": "same_logical_capture"}
    result = module.run_b19r2r_for_accepted_day_nonblocking(job=job, job_dir=tmp_path, asof="2026-09-18", symbols=["2330"])
    assert result["reused_model_a_job_id"] == "a_today"
    assert calls[0]["provider_snapshot"] == snapshot
    assert calls[0]["source_acquisition_run_id"] == "same_logical_capture"
    assert calls[0]["model_signal_gate"]["summary"]["model_a_signal_path"] == str(artifact)
    calls.clear()
    job["acquisition_logical_run_id"] = "different_capture"
    blocked = module.run_b19r2r_for_accepted_day_nonblocking(job=job, job_dir=tmp_path, asof="2026-09-18", symbols=["2330"])
    assert blocked["warning"] == "PUBLISHED_MODEL_A_ACQUISITION_RUN_MISMATCH"
    assert blocked["mainline_blocking"] is False
    assert calls == []
