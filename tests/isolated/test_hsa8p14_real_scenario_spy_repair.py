import copy
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
RUNNER = ROOT / "scripts/run_daily_tw_stock_auto_update.py"
BUILDER = ROOT / "scripts/build_tw_model_b_hsa8_isolated_handoff_wiring.py"
FAMILIES = ("adjusted_price", "twii", "institutional_flow", "margin_short")
SCENARIOS = (
    "twii_blocked", "segment_skip", "cache_reuse", "empty_capture",
    "scope_mismatch", "pit_mismatch", "missing_adapter_output", "missing_required_family",
)


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def _fixture(tmp_path):
    hsa8 = _load(BUILDER, "hsa8p14_builder")
    run_id = "daily.acquire.20260827.real"
    target = "2026-08-27"
    sources = []
    for family in FAMILIES:
        raw_path = tmp_path / f"{family}.raw.bin"
        norm_path = tmp_path / f"{family}.normalized.json"
        raw_path.write_bytes(f"raw:{family}".encode())
        norm_path.write_text(json.dumps({"family": family, "trade_date": "2026-08-26"}), encoding="utf-8")
        raw = [{"role": "provider_raw_response", "path": str(raw_path), "sha256": hsa8._digest(tmp_path, raw_path)}]
        normalized = [{"role": "provider_normalized_payload", "path": str(norm_path), "sha256": hsa8._digest(tmp_path, norm_path)}]
        source = {
            "source_family": family, "provider": "fixture-provider", "source_id": f"fixture.{family}.v1",
            "trade_date": "2026-08-26", "http_status": 200, "validator_status": "PASS", "pit_status": "PASS",
            "expected_scope": [f"{family}:scope"], "returned_scope": [f"{family}:scope"], "absent_scope": [], "unknown_scope": [],
            "endpoint": f"fixture://{family}", "endpoint_version": "fixture-v1", "parser_version": "fixture-parser-v1",
            "schema_version": "fixture-schema-v1", "transport_identity": "fixture-transport-v1", "request_parameters": {"family": family},
            "acquisition_run_id": run_id, "target_asof": target,
            "source_published_at": "2026-08-26T00:00:00+00:00", "available_at": "2026-08-26T01:00:00+00:00", "fetched_at": "2026-08-26T02:00:00+00:00",
            "raw_files": raw, "normalized_files": normalized,
        }
        digest_source = {
            **source,
            "source_validator_status": source["validator_status"],
            "source_endpoint_version": source["endpoint_version"],
        }
        source["canonical_metadata_digest"] = hsa8._canonical_digest(hsa8._canonical_metadata(digest_source, raw, normalized))
        adapter = tmp_path / f"{family}.adapter.json"
        adapter.write_text(json.dumps(source, sort_keys=True), encoding="utf-8")
        sources.append({"source_family": family, "adapter_output_path": str(adapter), "adapter_output_files": [str(adapter)]})
    return hsa8, run_id, target, sources


def _digest(sources):
    logical = []
    for source in sources:
        item = copy.deepcopy(source)
        for key in ("adapter_output_path", "adapter_output_files"):
            if key in item:
                item[key] = [Path(x).name for x in item[key]] if isinstance(item[key], list) else Path(item[key]).name
        logical.append(item)
    adapter_bytes = []
    for source in sources:
        path = source.get("adapter_output_path")
        if path:
            adapter = json.loads(Path(path).read_text())
            for field in ("raw_files", "normalized_files"):
                for item in adapter.get(field, []):
                    if isinstance(item, dict) and item.get("path"):
                        item["path"] = Path(item["path"]).name
            # The builder's production digest intentionally binds absolute job-local
            # locators; this evidence digest is a portable fixture mutation digest.
            adapter["canonical_metadata_digest"] = "fixture-bound"
            adapter_bytes.append({"path": Path(path).name, "payload": adapter})
    return hashlib.sha256(json.dumps({"sources": logical, "adapter_bytes": adapter_bytes}, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _mutate(sources, scenario):
    mutated = copy.deepcopy(sources)
    target_family = {
        "twii_blocked": "twii", "segment_skip": "institutional_flow", "cache_reuse": "adjusted_price",
        "empty_capture": "adjusted_price", "scope_mismatch": "margin_short", "pit_mismatch": "institutional_flow",
        "missing_adapter_output": "adjusted_price",
    }.get(scenario)
    target_index = next((i for i, item in enumerate(mutated) if item.get("source_family") == target_family), 0)
    adapter = Path(mutated[target_index]["adapter_output_path"]) if target_family else None
    payload = json.loads(adapter.read_text()) if adapter else None
    if scenario == "twii_blocked":
        payload["validator_status"] = "BLOCK"; payload["pit_status"] = "BLOCK"
        adapter.write_text(json.dumps(payload, sort_keys=True))
    elif scenario == "segment_skip":
        payload["segment_status"] = "skipped"; payload["validator_status"] = "BLOCK"
        adapter.write_text(json.dumps(payload, sort_keys=True))
    elif scenario == "cache_reuse":
        payload["acquisition_run_id"] = "previous-run"
        adapter.write_text(json.dumps(payload, sort_keys=True))
    elif scenario == "empty_capture":
        payload["raw_files"] = []
        adapter.write_text(json.dumps(payload, sort_keys=True))
    elif scenario == "scope_mismatch":
        payload["returned_scope"] = ["wrong:scope"]; payload["unknown_scope"] = ["wrong:scope"]
        adapter.write_text(json.dumps(payload, sort_keys=True))
    elif scenario == "pit_mismatch":
        payload["source_published_at"] = "2026-08-26T02:00:00+00:00"; payload["available_at"] = "2026-08-26T01:00:00+00:00"
        adapter.write_text(json.dumps(payload, sort_keys=True))
    elif scenario == "missing_adapter_output":
        mutated[target_index].pop("adapter_output_path"); mutated[target_index].pop("adapter_output_files")
    elif scenario == "missing_required_family":
        mutated.pop()
    return mutated


@pytest.mark.parametrize("scenario", SCENARIOS)
def test_real_mutation_builder_error_stops_all_downstreams(scenario, tmp_path):
    runner = _load(RUNNER, "hsa8p14_runner")
    hsa8, run_id, target, sources = _fixture(tmp_path)
    mutated = _mutate(sources, scenario)
    recorder = runner.DownstreamCallRecorder()
    spies = {kind: (lambda kind=kind: (_ for _ in ()).throw(AssertionError(kind))) for kind in runner.DOWNSTREAM_KINDS}
    result = runner.run_hsa8_validated_downstream_orchestration(
        validator=lambda: hsa8.validate_and_build(run_id, target, mutated, tmp_path),
        downstream=spies,
        recorder=recorder,
    )
    assert result["ok"] is False
    assert result["decision"] == "STOP_HANDOFF_VALIDATION_FAILED"
    assert result["validator_error"]
    assert result["calls"] == {kind: 0 for kind in runner.DOWNSTREAM_KINDS}


def test_valid_fixture_success_control_calls_each_downstream_once(tmp_path):
    runner = _load(RUNNER, "hsa8p14_runner_success")
    hsa8, run_id, target, sources = _fixture(tmp_path)
    result = runner.run_hsa8_validated_downstream_orchestration(
        validator=lambda: hsa8.validate_and_build(run_id, target, sources, tmp_path),
        downstream={kind: (lambda: None) for kind in runner.DOWNSTREAM_KINDS},
    )
    assert result["ok"] is True, result.get("validator_error", result)
    assert result["calls"] == {kind: 1 for kind in runner.DOWNSTREAM_KINDS}


def test_committed_p14_evidence_has_real_error_and_digest_fields():
    evidence = json.loads((ROOT / "docs/tw_portfolio_decision_model/HSA8P14_DOWNSTREAM_ZERO_CALL_MATRIX_EVIDENCE.json").read_text())
    assert evidence["schema_version"] == "hsa8p14.downstream_zero_call_matrix.v1"
    assert [row["scenario"] for row in evidence["scenarios"]] == list(SCENARIOS)
    assert all(row["input_digest_before"] != row["input_digest_after"] for row in evidence["scenarios"])
    assert all(row["validator_error"] and row["decision"] == "STOP_HANDOFF_VALIDATION_FAILED" for row in evidence["scenarios"])
    assert all(row["downstream_calls"] == {kind: 0 for kind in evidence["downstream_kinds"]} for row in evidence["scenarios"])
    assert evidence["success_control"]["downstream_calls"] == {kind: 1 for kind in evidence["downstream_kinds"]}
