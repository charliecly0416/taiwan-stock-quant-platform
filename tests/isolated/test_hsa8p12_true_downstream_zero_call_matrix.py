import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/run_daily_tw_stock_auto_update.py"


def _module():
    spec = importlib.util.spec_from_file_location("hsa8p12_daily", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


FAILURES = (
    "twii_blocked", "segment_skip", "cache_reuse", "empty_capture",
    "scope_mismatch", "pit_mismatch", "missing_adapter_output", "missing_required_family",
)


@pytest.mark.parametrize("failure", FAILURES)
def test_each_mutated_failure_fixture_uses_common_harness_and_records_zero(failure, tmp_path):
    module = _module()
    calls = []

    def callback():
        calls.append("called")

    recorder = module.DownstreamCallRecorder()
    result = module.run_hsa8_failure_scenario(
        scenario=failure,
        downstream={kind: callback for kind in module.DOWNSTREAM_KINDS},
        recorder=recorder,
    )
    assert result["status"] == "STOP_HANDOFF_FAILED"
    assert result["scenario"] == failure
    assert result["input_mutation"] == module.HSA8_FAILURE_SCENARIOS[failure]["input_mutation"]
    assert result["expected_validator_error"] == module.HSA8_FAILURE_SCENARIOS[failure]["expected_validator_error"]
    assert result["decision"] == "STOP_HANDOFF_FAILED"
    assert result["calls"] == {kind: 0 for kind in module.DOWNSTREAM_KINDS}
    assert calls == []


def test_failure_matrix_is_machine_readable_and_all_zero(tmp_path):
    module = _module()
    matrix = []
    for failure in FAILURES:
        recorder = module.DownstreamCallRecorder()
        result = module.run_hsa8_failure_scenario(
            scenario=failure,
            downstream={kind: lambda: None for kind in module.DOWNSTREAM_KINDS},
            recorder=recorder,
        )
        matrix.append({
            "scenario": result["scenario"],
            "input_mutation": result["input_mutation"],
            "expected_validator_error": result["expected_validator_error"],
            "decision": result["decision"],
            "handoff_status": result["status"],
            "downstream_calls": result["calls"],
        })
    evidence = {"schema_version": "hsa8p12.downstream_zero_call_matrix.v1", "scenarios": matrix}
    output = tmp_path / "hsa8p12_downstream_zero_call_matrix.json"
    output.write_text(json.dumps(evidence, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    loaded = json.loads(output.read_text(encoding="utf-8"))
    assert all(all(count == 0 for count in row["downstream_calls"].values()) for row in loaded["scenarios"])
    assert all(row["input_mutation"] and row["expected_validator_error"] and row["decision"] == "STOP_HANDOFF_FAILED" for row in loaded["scenarios"])
    assert len(loaded["scenarios"]) == 8


def test_committed_matrix_contains_scenario_trigger_and_decision_fields():
    evidence = json.loads((ROOT / "docs/tw_portfolio_decision_model/HSA8P13_DOWNSTREAM_ZERO_CALL_MATRIX_EVIDENCE.json").read_text(encoding="utf-8"))
    assert evidence["schema_version"] == "hsa8p13.downstream_zero_call_matrix.v1"
    assert [row["scenario"] for row in evidence["scenarios"]] == list(FAILURES)
    assert all(row["input_mutation"] and row["trigger_error"] for row in evidence["scenarios"])
    assert all(row["decision"] == "STOP_HANDOFF_FAILED" for row in evidence["scenarios"])
    assert all(row["downstream_calls"] == {kind: 0 for kind in evidence["downstream_kinds"]} for row in evidence["scenarios"])


def test_recorder_observes_callable_downstream_once_after_successful_handoff():
    module = _module()
    calls = []
    result = module.run_hsa8_downstream_orchestration(
        handoff_ok=True,
        downstream={kind: (lambda kind=kind: calls.append(kind)) for kind in module.DOWNSTREAM_KINDS},
    )
    assert result["ok"] is True
    assert result["calls"] == {kind: 1 for kind in module.DOWNSTREAM_KINDS}
    assert calls == list(module.DOWNSTREAM_KINDS)
