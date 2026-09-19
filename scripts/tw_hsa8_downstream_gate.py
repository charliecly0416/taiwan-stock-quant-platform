"""Isolated HSA8 downstream callback gate."""
from __future__ import annotations

from typing import Any

DOWNSTREAM_KINDS = ("provider_refresh", "model_score", "latest", "readonly_snapshot", "agent")

HSA8_FAILURE_SCENARIOS = {
    "twii_blocked": {"target_source_family": "twii", "mutation_path": "sources[twii].pit_status+validator_status", "input_mutation": {"pit_status": "BLOCK", "validator_status": "BLOCK"}, "expected_validator_error": "twii:validator_not_PASS"},
    "segment_skip": {"target_source_family": "institutional_flow", "mutation_path": "sources[institutional_flow].segment_status+validator_status", "input_mutation": {"segment_status": "skipped", "validator_status": "BLOCK"}, "expected_validator_error": "institutional_flow:validator_not_PASS"},
    "cache_reuse": {"target_source_family": "adjusted_price", "mutation_path": "sources[adjusted_price].acquisition_run_id", "input_mutation": {"acquisition_run_id": "previous-run"}, "expected_validator_error": "adjusted_price:run_or_asof_mismatch"},
    "empty_capture": {"target_source_family": "adjusted_price", "mutation_path": "sources[adjusted_price].raw_files", "input_mutation": {"raw_files": []}, "expected_validator_error": "adjusted_price:raw_files:required"},
    "scope_mismatch": {"target_source_family": "margin_short", "mutation_path": "sources[margin_short].returned_scope+unknown_scope", "input_mutation": {"returned_scope": ["wrong:scope"], "unknown_scope": ["wrong:scope"]}, "expected_validator_error": "scope:partition_overlap"},
    "pit_mismatch": {"target_source_family": "institutional_flow", "mutation_path": "sources[institutional_flow].source_published_at+available_at", "input_mutation": {"source_published_at": "2026-08-26T02:00:00+00:00", "available_at": "2026-08-26T01:00:00+00:00"}, "expected_validator_error": "institutional_flow:pit_order"},
    "missing_adapter_output": {"target_source_family": "adjusted_price", "mutation_path": "sources[adjusted_price].adapter_output_path+adapter_output_files", "input_mutation": {"adapter_output_path": None, "adapter_output_files": None}, "expected_validator_error": "adapter_output:required_unique_source_mapping"},
    "missing_required_family": {"target_source_family": "required_manifest", "mutation_path": "sources.remove(margin_short)", "input_mutation": {"removed_source_family": "margin_short"}, "expected_validator_error": "source_family:required_or_duplicate"},
}

class DownstreamCallRecorder:
    """Observable callback recorder for the acquisition-to-downstream gate."""
    def __init__(self) -> None:
        self.counts = {kind: 0 for kind in DOWNSTREAM_KINDS}
    def record(self, kind: str, callback, *args, **kwargs):
        if kind not in self.counts:
            raise ValueError(f"unknown downstream kind: {kind}")
        self.counts[kind] += 1
        return callback(*args, **kwargs)
    def snapshot(self) -> dict[str, int]:
        return dict(self.counts)

def run_hsa8_downstream_orchestration(*, handoff_ok: bool, downstream: dict[str, Any], recorder: DownstreamCallRecorder | None = None) -> dict[str, Any]:
    """Invoke downstream callbacks only after a successful HSA8 handoff."""
    recorder = recorder or DownstreamCallRecorder()
    if not handoff_ok:
        return {"ok": False, "status": "STOP_HANDOFF_FAILED", "calls": recorder.snapshot()}
    for kind in DOWNSTREAM_KINDS:
        callback = downstream.get(kind)
        if not callable(callback):
            return {"ok": False, "status": f"STOP_DOWNSTREAM_CALLBACK_MISSING:{kind}", "calls": recorder.snapshot()}
        recorder.record(kind, callback)
    return {"ok": True, "status": "DOWNSTREAM_CALLED", "calls": recorder.snapshot()}

def run_hsa8_validated_downstream_orchestration(*, validator, downstream: dict[str, Any], recorder: DownstreamCallRecorder | None = None) -> dict[str, Any]:
    """Run a validator callable, then pass its result through the common gate."""
    try:
        validation = validator()
    except Exception as exc:
        recorder = recorder or DownstreamCallRecorder()
        return {"ok": False, "status": "STOP_HANDOFF_VALIDATION_FAILED", "validator_error": str(exc), "decision": "STOP_HANDOFF_VALIDATION_FAILED", "calls": recorder.snapshot()}
    if validation is None:
        recorder = recorder or DownstreamCallRecorder()
        return {"ok": False, "status": "STOP_HANDOFF_VALIDATION_EMPTY", "validator_error": "validator_returned_none", "decision": "STOP_HANDOFF_VALIDATION_EMPTY", "calls": recorder.snapshot()}
    result = run_hsa8_downstream_orchestration(handoff_ok=True, downstream=downstream, recorder=recorder)
    return {**result, "validation": validation, "decision": result["status"]}

def run_hsa8_failure_scenario(*, scenario: str, downstream: dict[str, Any], recorder: DownstreamCallRecorder | None = None) -> dict[str, Any]:
    """Run one concrete offline failure fixture through the common gate."""
    fixture = HSA8_FAILURE_SCENARIOS.get(scenario)
    if fixture is None:
        raise ValueError(f"unknown HSA8 failure scenario: {scenario}")
    result = run_hsa8_downstream_orchestration(handoff_ok=False, downstream=downstream, recorder=recorder)
    return {**result, "scenario": scenario, "input_mutation": fixture["input_mutation"], "target_source_family": fixture["target_source_family"], "mutation_path": fixture["mutation_path"], "expected_validator_error": fixture["expected_validator_error"], "decision": "STOP_HANDOFF_FAILED"}
