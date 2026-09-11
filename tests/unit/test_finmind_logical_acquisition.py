import importlib.util
from pathlib import Path
import pytest


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("finmind_logical_acquisition", ROOT / "scripts/finmind_logical_acquisition.py")
module = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(module)


def evidence(ok=True, path="/ops/evidence.json", sha="a" * 64):
    return {"ok": ok, "evidence_path": path, "evidence_sha256": sha}


def test_segments_from_different_jobs_share_one_logical_identity():
    state = module.new_state(target_asof="2026-08-27", symbols=["2330", "2317"])
    state = module.record_segment(state, segment="daily_price", job_id="job-price", evidence=evidence())
    state = module.record_segment(state, segment="institutional", job_id="job-inst", evidence=evidence(path="/ops/i.json", sha="b" * 64))
    assert state["logical_run_id"].startswith("finmind.logical.20260827.")
    assert state["segments"]["daily_price"]["logical_run_id"] == state["logical_run_id"]
    assert state["segments"]["daily_price"]["job_id"] != state["segments"]["institutional"]["job_id"]
    assert state["status"] == "INCOMPLETE"
    assert state["handoff_allowed"] is False


def test_incomplete_or_failed_required_segment_stops_handoff():
    state = module.new_state(target_asof="2026-08-27", symbols=["2330"])
    for segment in module.REQUIRED_SEGMENTS[:-1]:
        state = module.record_segment(state, segment=segment, job_id=f"job-{segment}", evidence=evidence())
    state = module.record_segment(state, segment="twii", job_id="job-twii", evidence=evidence(ok=False))
    assert module.validate_state(state) == ("INCOMPLETE", False)


def test_complete_required_set_allows_handoff_but_optional_is_non_blocking():
    state = module.new_state(target_asof="2026-08-27", symbols=["2330"])
    for segment in module.REQUIRED_SEGMENTS:
        state = module.record_segment(state, segment=segment, job_id=f"job-{segment}", evidence=evidence())
    assert module.validate_state(state) == ("COMPLETE", True)
    state = module.record_segment(state, segment="corporate_actions", job_id="job-ca", evidence=evidence())
    assert module.validate_state(state) == ("COMPLETE", True)


def test_cross_asof_evidence_is_rejected():
    state = module.new_state(target_asof="2026-08-27", symbols=["2330"])
    bad = evidence()
    bad["target_asof"] = "2026-08-26"
    with pytest.raises(ValueError, match="target_asof"):
        module.record_segment(state, segment="daily_price", job_id="job-price", evidence=bad)


def test_state_write_is_readable_and_atomic(tmp_path):
    state = module.new_state(target_asof="2026-08-27", symbols=["2330"])
    path = tmp_path / "state.json"
    module.write_state(path, state)
    assert path.exists()
    assert not list(tmp_path.glob("*.tmp"))


def test_state_restarts_from_same_logical_run_identity(tmp_path):
    state = module.new_state(target_asof="2026-08-27", symbols=["2330"])
    path = tmp_path / "state.json"
    module.write_state(path, state)
    resumed = module.load_state(path, target_asof="2026-08-27", symbols=["2330"])
    assert resumed["logical_run_id"] == state["logical_run_id"]
    assert resumed["symbols_sha256"] == state["symbols_sha256"]


def test_changed_scope_does_not_reuse_prior_logical_state(tmp_path):
    state = module.new_state(target_asof="2026-08-27", symbols=["2330"])
    path = tmp_path / "state.json"
    module.write_state(path, state)
    resumed = module.load_state(path, target_asof="2026-08-27", symbols=["2330", "2317"])
    assert resumed["logical_run_id"] != state["logical_run_id"]
    assert resumed["segments"] == {}
