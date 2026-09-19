import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
P14 = ROOT / "tests/isolated/test_hsa8p14_real_scenario_spy_repair.py"
RUNNER = ROOT / "scripts/run_daily_tw_stock_auto_update.py"


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("scenario", (
    "twii_blocked", "segment_skip", "cache_reuse", "empty_capture",
    "scope_mismatch", "pit_mismatch", "missing_adapter_output", "missing_required_family",
))
def test_scenario_target_mutation_and_actual_error_are_bound(scenario, tmp_path):
    p14 = _load(P14, "hsa8p14_helpers")
    runner = _load(RUNNER, "hsa8p15_runner")
    hsa8, run_id, target, sources = p14._fixture(tmp_path)
    before = p14._digest(sources)
    mutated = p14._mutate(sources, scenario)
    after = p14._digest(mutated)
    config = runner.HSA8_FAILURE_SCENARIOS[scenario]
    result = runner.run_hsa8_validated_downstream_orchestration(
        validator=lambda: hsa8.validate_and_build(run_id, target, mutated, tmp_path),
        downstream={kind: (lambda: (_ for _ in ()).throw(AssertionError(kind))) for kind in runner.DOWNSTREAM_KINDS},
        recorder=runner.DownstreamCallRecorder(),
    )
    assert before != after
    assert result["validator_error"] == config["expected_validator_error"]
    assert result["decision"] == "STOP_HANDOFF_VALIDATION_FAILED"
    assert result["calls"] == {kind: 0 for kind in runner.DOWNSTREAM_KINDS}


def test_success_control_is_one_call_each_and_committed_evidence_is_bound():
    evidence = json.loads((ROOT / "docs/tw_portfolio_decision_model/HSA8P15_DOWNSTREAM_ZERO_CALL_MATRIX_EVIDENCE.json").read_text())
    kinds = evidence["downstream_kinds"]
    assert len(evidence["scenarios"]) == 8
    assert all(row["input_digest_before"] != row["input_digest_after"] for row in evidence["scenarios"])
    assert all(row["validator_error"] == row["expected_validator_error"] for row in evidence["scenarios"])
    assert all(row["downstream_calls"] == {kind: 0 for kind in kinds} for row in evidence["scenarios"])
    assert evidence["success_control"]["downstream_calls"] == {kind: 1 for kind in kinds}
