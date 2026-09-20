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
    track_calls = []
    monkeypatch.setattr(module, "build_real_same_run_handoff", lambda **kw: {"ok": True})
    monkeypatch.setattr(
        module,
        "run_daily_model_track_batch",
        lambda **kw: track_calls.append(kw) or {
            "ok": True,
            "tracks": {
                "model_a_only": {"ok": True, "status": "READY"},
                "model_a_plus_b_b19r2r": {
                    "ok": shadow_ok,
                    "attempted": True,
                    "status": "READY" if shadow_ok else "BLOCKED_MARGIN",
                },
            },
        },
    )
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
        assert track_calls == []
        assert pending_calls[0][1]["reason"] == "full_orthogonal_refresh_incomplete"
        return
    assert pending_calls == []
    assert len(track_calls) == 1
    assert track_calls[0]["include_prior_jobs"] is True
    assert final_jobs[0]["full_orthogonal_refresh"]["ok"] is False
    assert final_jobs[0]["accepted_day_shadow_only"] is True
    assert final_jobs[0]["daily_model_tracks"]["tracks"]["model_a_only"]["ok"] is True
    assert final_jobs[0]["latest_after"] == "2026-09-18"
    assert "pending_asof_set" not in final_jobs[0]


def test_daily_model_tracks_resolve_provider_and_normalized_from_same_origin(tmp_path, monkeypatch):
    module = load_daily()
    ops = tmp_path / "ops"
    qlib = tmp_path / "qlib"
    refresh_id = "option_c_yahoo_scrapling_refresh_today"
    publish_id = "option_c_yahoo_scrapling_publish_today"
    normalized = qlib / "data_tw/experiments/option_c_ops" / refresh_id / "candidate_normalized"
    provider = qlib / "data_tw/experiments/option_c_ops" / publish_id / "tmp/formal_provider_rebuild"
    normalized.mkdir(parents=True)
    provider.mkdir(parents=True)
    origin = ops / "origin" / "job.json"
    origin.parent.mkdir(parents=True)
    origin.write_text(json.dumps({
        "job_id": "origin",
        "asof": "2026-09-18",
        "latest_after": "2026-09-18",
        "acquisition_logical_run_id": "source-1",
        "refresh_job_id": refresh_id,
        "publish_job_id": publish_id,
    }))
    monkeypatch.setattr(module, "OPS_ROOT", ops)
    monkeypatch.setattr(module, "QLIB", qlib)

    result = module.discover_daily_model_track_sources(
        job={"job_id": "full", "acquisition_logical_run_id": "source-1"},
        asof="2026-09-18",
        include_prior_jobs=True,
    )

    assert result["ok"] is True
    assert result["origin_job_id"] == "origin"
    assert Path(result["qlib_provider"]) == provider
    assert Path(result["qlib_normalized"]) == normalized


def test_daily_model_track_batch_keeps_twii_failure_nonblocking(tmp_path, monkeypatch):
    module = load_daily()
    provider = tmp_path / "provider"
    normalized = tmp_path / "normalized"
    provider.mkdir()
    normalized.mkdir()
    job_dir = tmp_path / "job"
    job_dir.mkdir()
    (job_dir / "same_run_handoff_validation.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(module, "discover_daily_model_track_sources", lambda **kw: {
        "ok": True,
        "status": "READY",
        "qlib_provider": str(provider),
        "qlib_normalized": str(normalized),
    })
    monkeypatch.setattr(module, "capture_b19_twii_snapshot", lambda **kw: {
        "ok": False,
        "status": "BLOCKED_TWII_CAPTURE",
        "twii_csv": "",
        "twii_manifest": "",
    })
    calls = []

    def score_model_a(request):
        calls.append(request["track_id"])
        return {
            "ok": True,
            "status": "SCORED_ASOF_TARGET",
            "model_signal_artifact": str(tmp_path / request["track_id"]),
        }

    monkeypatch.setattr(module, "build_model_track_services", lambda **kw: {
        "model_a_scorer": score_model_a,
        "b19r2r_reranker": lambda request: pytest.fail("B must not run without TWII"),
    })
    result = module.run_daily_model_track_batch(
        job={"job_id": "full", "acquisition_logical_run_id": "source-1"},
        job_dir=job_dir,
        asof="2026-09-18",
        include_prior_jobs=False,
        timeout_seconds=30,
    )

    assert result["ok"] is True
    assert result["status"] == "READY_WITH_NONBLOCKING_FAILURES"
    assert calls == ["model_a_only"]
    assert result["tracks"]["model_a_only"]["ok"] is True
    assert result["tracks"]["model_a_plus_b_b19r2r"]["missing_dependencies"] == [
        "twii_snapshot"
    ]
