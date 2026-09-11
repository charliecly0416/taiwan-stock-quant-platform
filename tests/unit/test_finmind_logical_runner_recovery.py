import importlib.util
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("daily_runner_recovery", ROOT / "scripts/run_daily_tw_stock_auto_update.py")
runner = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(runner)


def _terminal_pending_fixture(tmp_path: Path, *, error: str = "HSA8Error:adjusted_price:validator_not_PASS") -> tuple[Path, Path]:
    job_id = "daily_tw_stock_auto_update_20260828_20260831T144501Z"
    job_dir = tmp_path / job_id
    state = tmp_path / "logical.json"
    state.write_text(json.dumps({"status": "COMPLETE", "handoff_allowed": True}), encoding="utf-8")
    job_dir.mkdir(parents=True)
    (job_dir / "job.json").write_text(json.dumps({
        "job_id": job_id,
        "status": "same_run_handoff_failed",
        "logical_acquisition_state_path": str(state),
        "same_run_handoff": {"error": error},
    }), encoding="utf-8")
    pending = tmp_path / "pending_asof.json"
    pending.write_text(json.dumps({"asof": "2026-08-28", "reason": "same_run_handoff_failed", "job_id": job_id}), encoding="utf-8")
    return pending, state


def test_terminal_evidence_pending_is_quarantined_and_next_weekday_is_caught_up(tmp_path, monkeypatch):
    pending, _state = _terminal_pending_fixture(tmp_path)
    monkeypatch.setattr(runner, "ROOT", tmp_path)
    monkeypatch.setattr(runner, "OPS_ROOT", tmp_path)
    monkeypatch.setattr(runner, "PENDING_ASOF", pending)
    monkeypatch.setattr(runner, "TERMINAL_PENDING_QUARANTINE_ROOT", tmp_path / "quarantine")
    now = datetime(2026, 9, 1, 0, 5, tzinfo=ZoneInfo("Asia/Taipei"))

    asof, source, evidence = runner.resolve_asof_with_terminal_quarantine("", now_taipei=now)

    assert (asof, source) == ("2026-08-31", "terminal_pending_catchup")
    current = json.loads(pending.read_text(encoding="utf-8"))
    assert current["reason"] == "terminal_pending_catchup"
    assert current["quarantined_asof"] == "2026-08-28"
    assert len(list((tmp_path / "quarantine").glob("*.pending.json"))) == 1
    assert evidence["terminal_pending_quarantine"]["protected_latest_changed"] is False


def test_retryable_handoff_error_remains_pending(tmp_path, monkeypatch):
    pending, _state = _terminal_pending_fixture(tmp_path, error="HSA8Error:adapter_output:required_field_missing")
    monkeypatch.setattr(runner, "ROOT", tmp_path)
    monkeypatch.setattr(runner, "OPS_ROOT", tmp_path)
    monkeypatch.setattr(runner, "PENDING_ASOF", pending)
    monkeypatch.setattr(runner, "TERMINAL_PENDING_QUARANTINE_ROOT", tmp_path / "quarantine")
    now = datetime(2026, 9, 1, 0, 5, tzinfo=ZoneInfo("Asia/Taipei"))

    asof, source, evidence = runner.resolve_asof_with_terminal_quarantine("", now_taipei=now)

    assert (asof, source) == ("2026-08-28", "pending")
    assert pending.exists()
    assert not (tmp_path / "quarantine").exists()
    assert evidence["pending_decision"]["reason"] == "handoff_error_retryable"


def _payload(segment: str, output: Path, *, include_segment: bool = True) -> dict:
    captures = {}
    for name in ([segment] if include_segment else []) + (["twii"] if segment == "daily_price" else []):
        artifact = output / f"{name}.adapter_output.json"
        artifact.write_text(json.dumps({"source_family": name}), encoding="utf-8")
        captures[name] = {
            "status": "captured",
            "target_asof": "2026-08-27",
            "validator_status": "PASS",
            "pit_status": "PASS",
            "adapter_output_path": str(artifact),
            "raw_paths": [str(artifact)],
            "normalized_paths": [str(artifact)],
        }
    return {"hsa8_capture": captures}


def test_two_jobs_resume_one_logical_run_and_request_only_missing_segment(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, "ROOT", tmp_path)
    monkeypatch.setattr(runner, "FINMIND_SEGMENT_CACHE_ROOT", tmp_path / "cache")
    symbols_file = tmp_path / "symbols.txt"
    symbols_file.write_text("2330\n2317\n", encoding="utf-8")
    state_path = tmp_path / "logical.json"
    calls = []
    margin_failed_once = [False]

    def fake_runner(argv, *, cwd, stdout_path, stderr_path, timeout):
        segment = stdout_path.name.removeprefix("finmind_").removesuffix("_stdout.txt")
        calls.append(segment)
        stdout_path.parent.mkdir(parents=True, exist_ok=True)
        if segment == "margin" and not margin_failed_once[0]:
            margin_failed_once[0] = True
            stdout_path.write_text("", encoding="utf-8")
            stderr_path.write_text("HTTP 402", encoding="utf-8")
            return {"ok": False, "returncode": 1, "stdout_path": str(stdout_path), "stderr_path": str(stderr_path), "stderr_tail": "HTTP 402"}
        payload = _payload(segment, stdout_path.parent)
        stdout_path.write_text(json.dumps(payload), encoding="utf-8")
        stderr_path.write_text("", encoding="utf-8")
        return {"ok": True, "returncode": 0, "stdout_path": str(stdout_path), "stderr_path": str(stderr_path), "stdout_tail": json.dumps(payload), "stderr_tail": ""}

    first = runner.run_finmind_segmented_update(
        symbols_file=symbols_file, job_dir=tmp_path / "job1", start="2026-08-26", end="2026-08-27",
        timeout_seconds=10, skip_validate=True, full_scope=True, include_optional_segments=False,
        reuse_success_cache=False, command_runner=fake_runner, acquisition_run_id="logical-1", logical_state_path=state_path,
    )
    assert first["ok"] is False
    assert calls == ["daily_price", "institutional", "margin"]
    calls.clear()
    second = runner.run_finmind_segmented_update(
        symbols_file=symbols_file, job_dir=tmp_path / "job2", start="2026-08-26", end="2026-08-27",
        timeout_seconds=10, skip_validate=True, full_scope=True, include_optional_segments=False,
        reuse_success_cache=False, command_runner=fake_runner, acquisition_run_id="logical-1", logical_state_path=state_path,
    )
    assert second["ok"] is True
    assert calls == ["margin"]
    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert state["status"] == "COMPLETE"
    assert state["handoff_allowed"] is True
    assert len({item["logical_run_id"] for item in state["segments"].values()}) == 1
    assert all(len(item["evidence_sha256"]) == 64 for item in state["segments"].values())
