from __future__ import annotations

import csv
import hashlib
import json
import os
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import build_tw_model_b_hsa5_daily_auto_sealed_capture_wiring_preflight as hsa5  # noqa: E402


DAILY_SOURCE = """
def write_json(path, payload):
    pass

def main():
    parser.add_argument("--skip-finmind-validate", default=False)
    if not args.skip_finmind:
        job["finmind_update"] = run_finmind_segmented_update()
        job["orthogonal"] = run_finmind_orthogonal_batch_update()
        source_validation = validate_finmind_source_artifacts()
        if not source_validation.get("ok"):
            return 2
        write_json(job_dir / "job.json", job)
    if legacy:
        legacy_provider_path()
    provider = run_provider_candidate_refresh_gate()
    model = run_model_signal_gate()
    finalize_job()
"""

BACKEND_SOURCE = """
def run_workflow():
    archive_symbols()
    archive_corporate_action_symbols()
    archive_institutional_symbols()
    archive_margin_symbols()
    archive_monthly_revenue_symbols()
    archive_valuation_symbols()
"""


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def capture_record(tmp_path: Path, family: str) -> dict:
    raw = tmp_path / f"{family}.provider-response.json"
    normalized = tmp_path / f"{family}.normalized.jsonl"
    raw.write_text('{"data":[]}\n', encoding="utf-8")
    normalized.write_text('{"symbol":"2330"}\n', encoding="utf-8")
    return {
        "snapshot_id": f"{family}-20260824",
        "source_family": family,
        "source_id": f"fixture.{family}",
        "provider": "FinMind",
        "source_endpoint_version": f"/v4/data/{family}:v4",
        "request_parameters": {"dataset": family, "date": "2026-08-24"},
        "fetched_at": "2026-08-24T11:00:00+00:00",
        "http_status": 200,
        "transport_identity": "direct:https",
        "parser_version": "fixture-v1",
        "schema_version": "fixture-v1",
        "trade_date": "2026-08-24",
        "available_at": "2026-08-24T10:45:00+00:00",
        "source_published_at": "2026-08-24T10:30:00+00:00",
        "raw_artifact_role": "provider_raw_response",
        "normalized_artifact_role": "provider_normalized_payload",
        "source_validator_status": "PASS",
        "acquisition_run_id": "daily.acquire.20260824.fixture",
        "expected_scope": ["2330", "2317"],
        "returned_scope": ["2330"],
        "absent_scope": ["2317"],
        "unknown_scope": [],
        "raw_files": [str(raw)],
        "normalized_files": [str(normalized)],
    }


def score_lineage_record(tmp_path: Path) -> dict:
    score = tmp_path / "model_a_scores.json"
    top50 = tmp_path / "model_a_top50.json"
    score.write_text('{"scores":[]}\n', encoding="utf-8")
    top50.write_text('{"top50":[]}\n', encoding="utf-8")
    return {
        "lineage_id": "model_a.qlib.top50.fixture",
        "score_artifact_path": str(score),
        "score_artifact_sha256": sha256(score),
        "top50_artifact_path": str(top50),
        "top50_artifact_sha256": sha256(top50),
        "top50_count": 50,
        "source_validator_status": "PASS",
    }


def complete_required_inventory(tmp_path: Path) -> dict:
    inventory = {
        "schema_version": "fixture_v2",
        "target_asof": "2026-08-24",
        "sources": {
            "adjusted_price_raw_lineage": capture_record(tmp_path, "adjusted_price"),
            "twii_raw_lineage": capture_record(tmp_path, "twii"),
            "institutional_flow": capture_record(tmp_path, "institutional_flow"),
            "margin_short": capture_record(tmp_path, "margin_short"),
            "model_a_qlib_score_top50_lineage": score_lineage_record(tmp_path),
        },
    }
    write_handoff_manifest(tmp_path, inventory)
    return inventory


def write_handoff_manifest(tmp_path: Path, inventory: dict) -> Path:
    run_id = "daily.acquire.20260824.fixture"
    sources = []
    for record in inventory["sources"].values():
        if not isinstance(record, dict) or "raw_files" not in record:
            continue
        artifacts = []
        for role, field in (
            ("provider_raw_response", "raw_files"),
            ("provider_normalized_payload", "normalized_files"),
        ):
            for raw_path in record[field]:
                path = Path(raw_path)
                artifacts.append({"role": role, "path": str(path), "sha256": sha256(path)})
        sources.append({
            "source_family": record["source_family"],
            "source_id": record["source_id"],
            "acquisition_run_id": run_id,
            "source_validator_status": record["source_validator_status"],
            "artifacts": artifacts,
        })
    path = tmp_path / "same_run_acquisition_handoff_manifest.json"
    path.write_text(json.dumps({
        "schema_version": hsa5.HANDOFF_SCHEMA_VERSION,
        "acquisition_run_id": run_id,
        "target_asof": inventory["target_asof"],
        "sources": sources,
    }), encoding="utf-8")
    inventory["acquisition_handoff_manifest_path"] = str(path)
    return path


def write_inputs(tmp_path: Path, inventory: dict, daily_source: str = DAILY_SOURCE, backend_source: str = BACKEND_SOURCE):
    daily = tmp_path / "daily.py"
    backend = tmp_path / "backend.py"
    inventory_path = tmp_path / "inventory.json"
    daily.write_text(daily_source, encoding="utf-8")
    backend.write_text(backend_source, encoding="utf-8")
    inventory_path.write_text(json.dumps(inventory), encoding="utf-8")
    return daily, backend, inventory_path


def run_fixture(tmp_path: Path, inventory: dict, daily_source: str = DAILY_SOURCE, backend_source: str = BACKEND_SOURCE):
    daily, backend, inventory_path = write_inputs(tmp_path, inventory, daily_source, backend_source)
    output = tmp_path / "isolated-output"
    before = {daily: sha256(daily), backend: sha256(backend), inventory_path: sha256(inventory_path)}
    result = hsa5.build_preflight(
        daily_script=daily,
        backend_script=backend,
        source_inventory=inventory_path,
        output_dir=output,
        project_root=tmp_path,
        allow_test_output_override=True,
    )
    assert before == {path: sha256(path) for path in before}
    return result, output


def test_required_dependencies_ready_while_optional_sources_do_not_block(tmp_path: Path) -> None:
    result, output = run_fixture(tmp_path, complete_required_inventory(tmp_path))

    assert result["decision"] == hsa5.READY
    assert result["ready"] is True
    optional = [row for row in result["rows"] if row["requirement_class"] == "optional_future_research"]
    assert optional and all(not row["ready"] and not row["blocking_for_model_b"] for row in optional)
    dependencies = {row["dependency"]: row for row in result["dependency_rows"]}
    assert all(dependencies[name]["ready"] for name in (
        "adjusted_price_raw_lineage", "twii_raw_lineage", "model_a_qlib_score_top50_lineage",
        "institutional_flow", "margin_short",
    ))
    assert dependencies["corporate_actions"]["blocking_for_model_b"] is False
    assert dependencies["corporate_actions"]["ready"] is True
    assert (output / "model_b_dependency_matrix.csv").is_file()
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["decision"] == "READY_FOR_HSA6_NO_CRON_IMPLEMENTATION"


def test_corporate_actions_only_blocks_when_adjusted_lineage_declares_dependency(tmp_path: Path) -> None:
    inventory = complete_required_inventory(tmp_path)
    inventory["sources"]["adjusted_price_raw_lineage"]["depends_on_corporate_actions"] = True

    result, _ = run_fixture(tmp_path, inventory)

    assert result["decision"] == hsa5.STOP
    corporate = next(row for row in result["dependency_rows"] if row["dependency"] == "corporate_actions")
    assert corporate["blocking_for_model_b"] is True
    assert corporate["ready"] is False


def test_declared_corporate_dependency_is_ready_with_complete_handoff(tmp_path: Path) -> None:
    inventory = complete_required_inventory(tmp_path)
    inventory["sources"]["adjusted_price_raw_lineage"]["declared_dependencies"] = ["corporate_actions"]
    inventory["sources"]["corporate_actions"] = capture_record(tmp_path, "corporate_actions")
    write_handoff_manifest(tmp_path, inventory)

    result, _ = run_fixture(tmp_path, inventory)

    assert result["decision"] == hsa5.READY


@pytest.mark.parametrize("required_key", [
    "adjusted_price_raw_lineage", "twii_raw_lineage", "model_a_qlib_score_top50_lineage",
    "institutional_flow", "margin_short",
])
def test_each_model_b_required_dependency_fails_closed_when_missing(tmp_path: Path, required_key: str) -> None:
    inventory = complete_required_inventory(tmp_path)
    del inventory["sources"][required_key]

    result, _ = run_fixture(tmp_path, inventory)

    assert result["decision"] == hsa5.STOP
    dependency = next(row for row in result["dependency_rows"] if row["dependency"] == required_key)
    assert dependency["ready"] is False


def test_model_score_and_top50_checksum_count_and_validator_are_required(tmp_path: Path) -> None:
    inventory = complete_required_inventory(tmp_path)
    lineage = inventory["sources"]["model_a_qlib_score_top50_lineage"]
    lineage["score_artifact_sha256"] = "0" * 64
    lineage["top50_count"] = 49
    lineage["source_validator_status"] = "SKIPPED"

    result, _ = run_fixture(tmp_path, inventory)

    row = next(item for item in result["dependency_rows"] if item["dependency"] == "model_a_qlib_score_top50_lineage")
    assert result["decision"] == hsa5.STOP
    assert "score_artifact_sha256_mismatch_or_missing" in row["gaps"]
    assert "top50_count_not_50" in row["gaps"]
    assert "source_validator_status_not_PASS" in row["gaps"]


def test_stdout_cannot_be_disguised_as_provider_raw_response(tmp_path: Path) -> None:
    inventory = complete_required_inventory(tmp_path)
    stdout = tmp_path / "provider-response.json"
    stdout.write_text('{"summary":true}\n', encoding="utf-8")
    inventory["sources"]["institutional_flow"]["raw_files"] = [str(stdout)]

    result, _ = run_fixture(tmp_path, inventory)

    row = next(item for item in result["rows"] if item["source_family"] == "institutional_flow")
    assert result["decision"] == hsa5.STOP
    assert any("same_run_handoff_provider_raw_response_path_or_sha256_mismatch" in gap for gap in row["gaps"])


def test_inventory_roles_and_paths_cannot_replace_missing_authoritative_handoff(tmp_path: Path) -> None:
    inventory = complete_required_inventory(tmp_path)
    del inventory["acquisition_handoff_manifest_path"]

    result, _ = run_fixture(tmp_path, inventory)

    assert result["decision"] == hsa5.STOP
    row = next(item for item in result["rows"] if item["source_family"] == "institutional_flow")
    assert "same_run_acquisition_handoff_manifest_path_missing" in row["gaps"]


@pytest.mark.parametrize("field,value", [
    ("raw_artifact_role", "daily_summary"),
    ("normalized_artifact_role", "database_rows"),
    ("source_validator_status", "SKIPPED"),
    ("source_id", "FinMind Invalid"),
])
def test_handoff_roles_validator_and_stable_identity_are_mandatory(tmp_path: Path, field: str, value: str) -> None:
    inventory = complete_required_inventory(tmp_path)
    inventory["sources"]["margin_short"][field] = value

    result, _ = run_fixture(tmp_path, inventory)

    assert result["decision"] == hsa5.STOP
    row = next(item for item in result["rows"] if item["source_family"] == "margin_short")
    assert row["ready_for_hsa4_handoff"] is False


def test_scope_overlap_fails_closed(tmp_path: Path) -> None:
    inventory = complete_required_inventory(tmp_path)
    record = inventory["sources"]["institutional_flow"]
    record["absent_scope"] = ["2330", "2317"]

    result, _ = run_fixture(tmp_path, inventory)

    row = next(item for item in result["rows"] if item["source_family"] == "institutional_flow")
    assert "scope_closure:partition_overlap" in row["gaps"]


def test_ast_is_limited_to_same_main_guard_and_cannot_combine_other_functions() -> None:
    misleading = """
def helper():
    validation = validate_finmind_source_artifacts()
    if not validation.get("ok"):
        return 2
    write_json(job_dir / "job.json", job)
    run_provider_candidate_refresh_gate()

def main():
    if not args.skip_finmind:
        run_finmind_segmented_update()
    run_model_signal_gate()
"""
    audit = hsa5.analyze_static_insertion_point(misleading, BACKEND_SOURCE)

    assert audit["ok"] is False
    assert audit["analysis_scope_limited_to_entry_functions"] is True
    assert audit["source_validator"]["validator_pass_proven"] is False
    assert audit["exact_insertion_point"]["after_line"] is None


def test_explicit_same_guard_validator_must_fail_closed() -> None:
    warning_only = DAILY_SOURCE.replace('        if not source_validation.get("ok"):\n            return 2\n', '')
    audit = hsa5.analyze_static_insertion_point(warning_only, BACKEND_SOURCE)

    assert audit["ok"] is False
    assert audit["source_validator"]["explicit_validator_call"] == "validate_finmind_source_artifacts"
    assert audit["source_validator"]["fail_closed_return_or_raise_before_anchor"] is False


def test_validator_success_branch_return_cannot_masquerade_as_fail_closed() -> None:
    wrong_polarity = DAILY_SOURCE.replace(
        'if not source_validation.get("ok"):',
        'if source_validation.get("ok"):',
    )
    audit = hsa5.analyze_static_insertion_point(wrong_polarity, BACKEND_SOURCE)

    assert audit["ok"] is False
    assert audit["source_validator"]["fail_closed_return_or_raise_before_anchor"] is False


def test_fail_close_after_anchor_is_rejected() -> None:
    source = DAILY_SOURCE.replace(
        '        if not source_validation.get("ok"):\n            return 2\n        write_json(job_dir / "job.json", job)\n',
        '        write_json(job_dir / "job.json", job)\n        if not source_validation.get("ok"):\n            return 2\n',
    )
    audit = hsa5.analyze_static_insertion_point(source, BACKEND_SOURCE)

    assert audit["ok"] is False
    assert audit["source_validator"]["fail_closed_return_or_raise_before_anchor"] is False


def test_nested_divergent_fetch_is_rejected() -> None:
    source = DAILY_SOURCE.replace(
        '        job["finmind_update"] = run_finmind_segmented_update()\n',
        '        if enabled:\n            job["finmind_update"] = run_finmind_segmented_update()\n',
    )
    audit = hsa5.analyze_static_insertion_point(source, BACKEND_SOURCE)

    assert audit["ok"] is False
    assert audit["nested_or_divergent_relevant_calls"]
    assert audit["linear_guard_control_flow_proven"] is False


def test_default_skip_true_stops_even_with_complete_validator_shape() -> None:
    source = DAILY_SOURCE.replace(
        'default=False',
        'default=True',
    )
    audit = hsa5.analyze_static_insertion_point(source, BACKEND_SOURCE)

    assert audit["source_validator"]["explicit_validator_shape_proven"] is True
    assert audit["source_validator"]["default_validation_enabled_proven"] is False
    assert audit["source_validator"]["default_skip_validation_detected"] is True
    assert audit["source_validator"]["validator_pass_proven"] is False
    assert audit["source_validator"]["status"] == "STOP_VALIDATOR_PASS_NOT_PROVEN"
    assert audit["ok"] is False


def test_uppercase_true_default_is_unsafe() -> None:
    source = DAILY_SOURCE.replace('default=False', 'default="TRUE"')
    audit = hsa5.analyze_static_insertion_point(source, BACKEND_SOURCE)

    assert audit["source_validator"]["default_validation_enabled_proven"] is False
    assert audit["source_validator"]["default_validation_safety_status"] == "PROVEN_UNSAFE_TRUE"
    assert audit["source_validator"]["default_validation_safety_reason"] == "literal_true"
    assert audit["ok"] is False


def test_dynamic_unknown_default_fails_closed() -> None:
    source = DAILY_SOURCE.replace('default=False', 'default=runtime_default()')
    audit = hsa5.analyze_static_insertion_point(source, BACKEND_SOURCE)

    assert audit["source_validator"]["default_validation_enabled_proven"] is False
    assert audit["source_validator"]["default_validation_safety_status"] == "UNKNOWN"
    assert audit["source_validator"]["default_validation_safety_reason"] == "dynamic_or_unrecognized_default"
    assert audit["ok"] is False


def test_literal_false_default_proves_validation_enabled() -> None:
    audit = hsa5.analyze_static_insertion_point(DAILY_SOURCE, BACKEND_SOURCE)

    assert audit["source_validator"]["default_validation_enabled_proven"] is True
    assert audit["source_validator"]["default_validation_safety_status"] == "PROVEN_SAFE_FALSE"
    assert audit["source_validator"]["validator_pass_proven"] is True
    assert audit["ok"] is True


def test_literal_false_string_default_is_truthy_and_stops() -> None:
    source = DAILY_SOURCE.replace('default=False', 'default="FaLsE"')
    audit = hsa5.analyze_static_insertion_point(source, BACKEND_SOURCE)

    assert audit["source_validator"]["default_validation_enabled_proven"] is False
    assert audit["source_validator"]["default_validation_safety_status"] == "UNKNOWN"
    assert audit["source_validator"]["default_validation_safety_reason"] == "dynamic_or_unrecognized_default"
    assert audit["source_validator"]["validator_pass_proven"] is False
    assert audit["ok"] is False


@pytest.mark.parametrize("default_expression", [
    'os.getenv("TW_SKIP", "FALSE").lower() in {"true", "1"}',
    'env_flag("TW_SKIP", default=False)',
])
def test_known_env_false_fallback_still_stops(default_expression: str) -> None:
    source = DAILY_SOURCE.replace('default=False', f'default={default_expression}')
    audit = hsa5.analyze_static_insertion_point(source, BACKEND_SOURCE)

    assert audit["source_validator"]["default_validation_enabled_proven"] is False
    assert audit["source_validator"]["default_validation_safety_status"] == "UNKNOWN"
    assert audit["source_validator"]["default_validation_safety_reason"] == "runtime_environment_can_override_false_fallback"
    assert audit["source_validator"]["validator_pass_proven"] is False
    assert audit["ok"] is False


def test_unrelated_write_json_cannot_be_anchor() -> None:
    source = DAILY_SOURCE.replace(
        'write_json(job_dir / "job.json", job)',
        'write_json(job_dir / "unrelated.json", job)',
    )
    audit = hsa5.analyze_static_insertion_point(source, BACKEND_SOURCE)

    assert audit["ok"] is False
    assert audit["exact_insertion_point"]["after_line"] is None
    assert audit["exact_insertion_point"]["after_statement"] == ""
    assert audit["source_validator"]["validator_pass_proven"] is False


def test_attribute_write_json_method_cannot_be_anchor() -> None:
    source = DAILY_SOURCE.replace(
        'write_json(job_dir / "job.json", job)',
        'writer.write_json(job_dir / "job.json", job)',
    )
    audit = hsa5.analyze_static_insertion_point(source, BACKEND_SOURCE)

    assert audit["ok"] is False
    assert audit["exact_insertion_point"]["after_line"] is None
    assert audit["source_validator"]["validator_pass_proven"] is False


def test_current_default_skip_validation_warning_is_stop() -> None:
    daily = (ROOT / "scripts/run_daily_tw_stock_auto_update.py").read_text(encoding="utf-8")
    backend = (ROOT / "backend/scripts/update_tw_stock_daily.py").read_text(encoding="utf-8")
    audit = hsa5.analyze_static_insertion_point(daily, backend)

    assert audit["ok"] is False
    assert audit["source_validator"]["default_skip_validation_detected"] is True
    assert audit["source_validator"]["warning_only_continuation_detected"] is True
    assert audit["source_validator"]["validator_pass_proven"] is False
    assert audit["source_validator"]["status"] == "STOP_VALIDATOR_PASS_NOT_PROVEN"


def test_secure_read_rejects_file_and_ancestor_symlink(tmp_path: Path) -> None:
    directory = tmp_path / "trusted"
    directory.mkdir()
    source = directory / "payload.json"
    source.write_text("{}", encoding="utf-8")
    file_link = tmp_path / "file-link.json"
    file_link.symlink_to(source)
    ancestor_link = tmp_path / "ancestor-link"
    ancestor_link.symlink_to(directory, target_is_directory=True)

    with pytest.raises(hsa5.PreflightError):
        hsa5._secure_read(file_link)
    with pytest.raises(hsa5.PreflightError):
        hsa5._secure_read(ancestor_link / source.name)


def test_secure_read_detects_locator_swap_and_preserves_unknown(monkeypatch, tmp_path: Path) -> None:
    source = tmp_path / "payload.json"
    moved = tmp_path / "payload-owned.json"
    source.write_text('{"owned":true}', encoding="utf-8")
    replacement_inode = {}

    def swap(path: Path, file_fd: int) -> None:
        if path == source:
            source.rename(moved)
            source.write_text('{"unknown":true}', encoding="utf-8")
            replacement_inode["value"] = source.stat().st_ino

    monkeypatch.setattr(hsa5, "_after_fd_read", swap)
    with pytest.raises(hsa5.PreflightError, match="locator identity changed"):
        hsa5._secure_read(source)
    assert json.loads(source.read_text())["unknown"] is True
    assert source.stat().st_ino == replacement_inode["value"]
    assert json.loads(moved.read_text())["owned"] is True


def test_output_matrices_and_manifest_are_consistent(tmp_path: Path) -> None:
    result, output = run_fixture(tmp_path, complete_required_inventory(tmp_path))

    with (output / "source_family_gap_matrix.csv").open(encoding="utf-8", newline="") as handle:
        assert len(list(csv.DictReader(handle))) == 8
    with (output / "model_b_dependency_matrix.csv").open(encoding="utf-8", newline="") as handle:
        assert len(list(csv.DictReader(handle))) == 6
    forbidden = json.loads((output / "forbidden_scope_audit.json").read_text())
    assert forbidden["input_reads_use_openat_nofollow_fd_identity_checksum"] is True
    assert forbidden["protected_paths_before_after_fingerprinted"] is True
    assert forbidden["pass"] is True
    manifest = json.loads((output / "manifest.json").read_text())
    for artifact in manifest["artifacts"]:
        assert sha256(output / artifact["path"]) == artifact["sha256"]
    assert result["decision"] == hsa5.READY


def test_production_output_scope_rejects_arbitrary_cli_path(tmp_path: Path) -> None:
    inventory = complete_required_inventory(tmp_path)
    daily, backend, inventory_path = write_inputs(tmp_path, inventory)

    with pytest.raises(hsa5.PreflightError, match="production output must equal isolated HSA5 root"):
        hsa5.build_preflight(
            daily_script=daily,
            backend_script=backend,
            source_inventory=inventory_path,
            output_dir=tmp_path / "arbitrary",
            project_root=tmp_path,
        )
