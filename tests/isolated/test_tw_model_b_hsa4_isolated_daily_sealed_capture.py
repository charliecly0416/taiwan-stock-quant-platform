from __future__ import annotations

import importlib.util
import json
import os
import sys
from dataclasses import replace
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts/build_tw_model_b_hsa4_isolated_daily_sealed_capture.py"
SPEC = importlib.util.spec_from_file_location("hsa4_capture", MODULE_PATH)
hsa4 = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = hsa4
SPEC.loader.exec_module(hsa4)


def assert_code(code, function, *args, **kwargs):
    with pytest.raises(hsa4.CaptureError) as caught:
        function(*args, **kwargs)
    assert caught.value.code == code


@pytest.fixture
def case(tmp_path):
    source = tmp_path / "source"
    output = tmp_path / "output"
    source.mkdir()
    output.mkdir()
    raw = source / "raw.jsonl"
    normalized = source / "normalized.csv"
    raw.write_bytes(b'{"data":[]}\n')
    normalized.write_bytes(b"date,instrument,value\n2026-08-25,TW0001,1\n")
    request = hsa4.CaptureRequest(
        snapshot_id="HSA4_20260825_TEST",
        source_family="institutional_flow",
        source_id="finmind.taiwan_stock_institutional_investors_buy_sell",
        provider="SYNTHETIC_LOCAL",
        source_endpoint_version="endpoint-v1",
        parser_version="parser-v1",
        schema_version="normalized-v1",
        trade_date="2026-08-25",
        source_published_at="2026-08-25T09:00:00+00:00",
        available_at="2026-08-25T09:01:00+00:00",
        fetched_at="2026-08-25T09:02:00+00:00",
        http_status=200,
        transport_identity="local_test",
        request_parameters={"dataset": "test"},
        raw_files=[raw],
        normalized_files=[normalized],
        expected_scope=["TW0001", "TW0002", "TW0003"],
        returned_scope=["TW0001"],
        absent_scope=["TW0002"],
        unknown_scope=["TW0003"],
    )
    return request, output, raw, normalized


def test_nominal_capture_is_append_only_and_manifest_last(case):
    request, output, raw, normalized = case
    target = hsa4.build_capture(request, output_root=output)
    manifest = json.loads((target / "manifest.json").read_text())
    assert manifest["scope"]["closure"] is True
    assert manifest["scope"]["unknown_scope"] == ["TW0003"]
    assert manifest["file_count"] == 2
    assert manifest["manifest_written_last"] is True
    assert manifest["source_family"] == request.source_family
    assert manifest["source_id"] == request.source_id
    assert len(manifest["lineage_digest"]) == 64
    assert (target / "raw/0000_raw.jsonl").read_bytes() == raw.read_bytes()
    assert (target / "normalized/0000_normalized.csv").read_bytes() == normalized.read_bytes()
    assert not any(".stage." in child.name for child in output.iterdir())
    assert_code("HSA4_E_APPEND_ONLY", hsa4.build_capture, request, output_root=output)
    assert (target / "manifest.json").read_text()


def test_source_identity_and_checksums_are_sealed(case):
    request, output, raw, _ = case
    target = hsa4.build_capture(request, output_root=output)
    manifest = json.loads((target / "manifest.json").read_text())
    entry = next(row for row in manifest["files"] if row["family"] == "raw")
    assert entry["source_inode"] == raw.stat().st_ino
    assert entry["source_device"] == raw.stat().st_dev
    assert entry["source_size_bytes"] == len(raw.read_bytes())
    assert entry["sha256"] == hsa4.sha256_bytes(raw.read_bytes())


@pytest.mark.parametrize("field,value", [
    ("source_family", "Institutional Flow"),
    ("source_family", "_institutional"),
    ("source_id", "FinMind.Dataset"),
    ("source_id", "finmind..dataset"),
])
def test_stable_source_identity_is_required(case, field, value):
    request, output, *_ = case
    assert_code("HSA4_E_SOURCE_IDENTITY", hsa4.build_capture, replace(request, **{field: value}), output_root=output)
    assert list(output.iterdir()) == []


def test_lineage_digest_binds_source_identity(case):
    request, output, *_ = case
    first = hsa4.build_capture(request, output_root=output)
    first_digest = json.loads((first / "manifest.json").read_text())["lineage_digest"]
    second_request = replace(
        request,
        snapshot_id="HSA4_20260825_TEST_SECOND",
        source_id="finmind.taiwan_stock_institutional_investors_buy_sell.v2",
    )
    second = hsa4.build_capture(second_request, output_root=output)
    second_digest = json.loads((second / "manifest.json").read_text())["lineage_digest"]
    assert first_digest != second_digest


@pytest.mark.parametrize("field", ["expected_scope", "returned_scope", "absent_scope", "unknown_scope"])
def test_duplicate_scope_values_rejected(case, field):
    request, output, *_ = case
    values = list(getattr(request, field))
    broken = replace(request, **{field: values + [values[0]]})
    assert_code("HSA4_E_SCOPE_DUPLICATE", hsa4.build_capture, broken, output_root=output)


def test_scope_overlap_and_nonclosure_rejected(case):
    request, output, *_ = case
    assert_code("HSA4_E_SCOPE_OVERLAP", hsa4.build_capture, replace(request, absent_scope=["TW0001", "TW0002"]), output_root=output)
    assert_code("HSA4_E_SCOPE_CLOSURE", hsa4.build_capture, replace(request, unknown_scope=[]), output_root=output)
    assert list(output.iterdir()) == []


@pytest.mark.parametrize("parameters", [
    {"value": float("nan")},
    {"nested": [1, {"value": float("inf")}]},
    {"nested": [1, {"value": float("-inf")}]},
    {1: "non-string-key"},
])
def test_request_parameters_reject_noncanonical_json(case, parameters):
    request, output, *_ = case
    assert_code("HSA4_E_REQUEST_PARAMETERS", hsa4.build_capture, replace(request, request_parameters=parameters), output_root=output)
    assert list(output.iterdir()) == []


def test_canonical_json_disallows_nan():
    assert_code("HSA4_E_REQUEST_PARAMETERS", hsa4.canonical_json, {"value": float("nan")})


def test_canonical_json_directly_rejects_non_string_key():
    assert_code("HSA4_E_REQUEST_PARAMETERS", hsa4.canonical_json, {1: "value"})


@pytest.mark.parametrize("field,value", [
    ("source_published_at", "2026-08-25T09:03:00+00:00"),
    ("available_at", "2026-08-25T09:03:00+00:00"),
    ("fetched_at", "2026-08-25T09:02:00"),
])
def test_time_contract_rejected(case, field, value):
    request, output, *_ = case
    assert_code("HSA4_E_TIME_ORDER" if field != "fetched_at" else "HSA4_E_TIMESTAMP", hsa4.build_capture, replace(request, **{field: value}), output_root=output)


def test_input_file_and_parent_symlinks_rejected(case, tmp_path):
    request, output, raw, _ = case
    file_link = tmp_path / "raw-link"
    file_link.symlink_to(raw)
    assert_code("HSA4_E_SOURCE_NOFOLLOW", hsa4.build_capture, replace(request, raw_files=[file_link]), output_root=output)
    parent_link = tmp_path / "source-link"
    parent_link.symlink_to(raw.parent, target_is_directory=True)
    assert_code("HSA4_E_SOURCE_NOFOLLOW", hsa4.build_capture, replace(request, raw_files=[parent_link / raw.name]), output_root=output)
    assert len([path for path in output.iterdir() if path.name.startswith(".hsa4-failed-")]) == 2


def test_output_root_symlink_rejected(case, tmp_path):
    request, _, *_ = case
    outside = tmp_path / "outside"
    outside.mkdir()
    link = tmp_path / "output-link"
    link.symlink_to(outside, target_is_directory=True)
    assert_code("HSA4_E_OUTPUT_NOFOLLOW", hsa4.build_capture, request, output_root=link)
    assert list(outside.iterdir()) == []


def test_duplicate_source_inode_failure_is_preserved(case):
    request, output, raw, _ = case
    assert_code("HSA4_E_SOURCE_DUPLICATE", hsa4.build_capture, replace(request, raw_files=[raw, raw]), output_root=output)
    failed = [path for path in output.iterdir() if path.name.startswith(".hsa4-failed-")]
    assert len(failed) == 1
    assert json.loads((failed[0] / "failure_marker.json").read_text())["destructive_cleanup_performed"] is False


def test_preexisting_stage_is_not_owned_or_modified(monkeypatch, case):
    request, output, *_ = case
    transaction_id = "a" * 32
    monkeypatch.setattr(hsa4.secrets, "token_hex", lambda size: transaction_id)
    stale = output / f".{request.snapshot_id}.stage.{transaction_id}"
    stale.mkdir()
    (stale / "owner.txt").write_text("other transaction")
    assert_code("HSA4_E_STAGE_EXISTS", hsa4.build_capture, request, output_root=output)
    assert (stale / "owner.txt").read_text() == "other transaction"


def test_final_created_after_precheck_is_never_replaced(monkeypatch, case):
    request, output, *_ = case
    original = hsa4._rename_noreplace
    observed = {}

    def create_final_then_install(parent_fd, source, destination):
        if destination == request.snapshot_id and "inode" not in observed:
            final = output / destination
            final.mkdir()
            os.setxattr(final, b"user.hsa4_owner", b"other transaction")
            observed["inode"] = final.stat().st_ino
        return original(parent_fd, source, destination)

    monkeypatch.setattr(hsa4, "_rename_noreplace", create_final_then_install)
    assert_code("HSA4_E_APPEND_ONLY", hsa4.build_capture, request, output_root=output)
    final = output / request.snapshot_id
    assert final.stat().st_ino == observed["inode"]
    assert list(final.iterdir()) == []
    assert os.getxattr(final, b"user.hsa4_owner") == b"other transaction"
    assert not any(".stage." in child.name for child in output.iterdir())
    failed = [path for path in output.iterdir() if path.name.startswith(".hsa4-failed-")]
    assert len(failed) == 1 and (failed[0] / "failure_marker.json").is_file()


def test_write_failure_preserves_failed_candidate(monkeypatch, case):
    request, output, *_ = case
    original = hsa4._write_file
    calls = 0

    def fail_second(parent_fd, name, chunks):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("injected")
        return original(parent_fd, name, chunks)

    monkeypatch.setattr(hsa4, "_write_file", fail_second)
    with pytest.raises(OSError):
        hsa4.build_capture(request, output_root=output)
    failed = [path for path in output.iterdir() if path.name.startswith(".hsa4-failed-")]
    assert len(failed) == 1
    assert (failed[0] / "failure_marker.json").is_file()
    assert not any(".stage." in path.name for path in output.iterdir())


def test_manifest_failure_preserves_failed_candidate(monkeypatch, case):
    request, output, *_ = case
    original = hsa4._write_file

    def fail_manifest(parent_fd, name, chunks):
        if name == "manifest.json":
            raise OSError("manifest failure")
        return original(parent_fd, name, chunks)

    monkeypatch.setattr(hsa4, "_write_file", fail_manifest)
    with pytest.raises(OSError):
        hsa4.build_capture(request, output_root=output)
    failed = [path for path in output.iterdir() if path.name.startswith(".hsa4-failed-")]
    assert len(failed) == 1
    marker = json.loads((failed[0] / "failure_marker.json").read_text())
    assert marker["status"] == "HSA4_FAILED_CANDIDATE_PRESERVED"


def test_root_swap_after_install_preserves_failed_candidate(monkeypatch, case, tmp_path):
    request, output, *_ = case
    moved = tmp_path / "moved-output"
    original = hsa4._assert_root_chain
    calls = 0

    def swap_on_second_check(path, identity):
        nonlocal calls
        calls += 1
        if calls == 2:
            os.rename(output, moved)
            output.mkdir()
        return original(path, identity)

    monkeypatch.setattr(hsa4, "_assert_root_chain", swap_on_second_check)
    assert_code("HSA4_E_OUTPUT_ROOT_REPLACED", hsa4.build_capture, request, output_root=output)
    assert not (output / request.snapshot_id).exists()
    assert not (moved / request.snapshot_id).exists()
    assert len([path for path in moved.iterdir() if path.name.startswith(".hsa4-failed-")]) == 1


def test_final_failure_isolation_identity_drift_preserves_unknown(monkeypatch, case):
    request, output, *_ = case
    original = hsa4._assert_root_chain
    calls = 0
    unknown = {}

    def swap_final_before_post_install_check(path, identities):
        nonlocal calls
        calls += 1
        if calls == 2:
            final = output / request.snapshot_id
            final.rename(output / "owned-moved")
            final.mkdir()
            (final / "owner.txt").write_text("unknown entry")
            unknown["inode"] = final.stat().st_ino
        return original(path, identities)

    monkeypatch.setattr(hsa4, "_assert_root_chain", swap_final_before_post_install_check)
    assert_code("HSA4_E_FAILURE_ISOLATION_TAINT", hsa4.build_capture, request, output_root=output)
    failed = [path for path in output.iterdir() if path.name.startswith(".hsa4-failed-")]
    assert failed == []
    assert (output / request.snapshot_id).stat().st_ino == unknown["inode"]
    assert (output / request.snapshot_id / "owner.txt").read_text() == "unknown entry"
    assert (output / "owned-moved").is_dir()


def test_stage_failure_isolation_identity_drift_preserves_unknown(monkeypatch, case):
    request, output, *_ = case
    original_write = hsa4._write_file
    unknown = {}

    def fail_manifest(parent_fd, name, chunks):
        if name == "manifest.json":
            raise OSError("build failure")
        return original_write(parent_fd, name, chunks)

    def swap_stage_before_isolation(parent_fd, source_name, failed_name, identity):
        stage = output / source_name
        stage.rename(output / "owned-stage-moved")
        stage.mkdir()
        (stage / "owner.txt").write_text("unknown stage")
        unknown["inode"] = stage.stat().st_ino

    monkeypatch.setattr(hsa4, "_write_file", fail_manifest)
    monkeypatch.setattr(hsa4, "_before_failure_isolation", swap_stage_before_isolation)
    assert_code("HSA4_E_FAILURE_ISOLATION_TAINT", hsa4.build_capture, request, output_root=output)
    failed = [path for path in output.iterdir() if path.name.startswith(".hsa4-failed-")]
    assert failed == []
    stage = [path for path in output.iterdir() if ".stage." in path.name]
    assert len(stage) == 1 and stage[0].stat().st_ino == unknown["inode"]
    assert (stage[0] / "owner.txt").read_text() == "unknown stage"
    assert (output / "owned-stage-moved").is_dir()


def test_output_ancestor_swap_preserves_bound_failed_candidate(monkeypatch, case, tmp_path):
    request, _, *_ = case
    trusted = tmp_path / "trusted"
    output = trusted / "output"
    output.mkdir(parents=True)
    moved = tmp_path / "trusted-moved"
    original = hsa4._assert_root_chain
    swapped = False

    def swap_ancestor_then_assert(path, identities):
        nonlocal swapped
        if not swapped:
            swapped = True
            trusted.rename(moved)
            output.mkdir(parents=True)
            (output / "owner.txt").write_text("replacement chain")
        return original(path, identities)

    monkeypatch.setattr(hsa4, "_assert_root_chain", swap_ancestor_then_assert)
    assert_code("HSA4_E_OUTPUT_ROOT_REPLACED", hsa4.build_capture, request, output_root=output)
    assert (output / "owner.txt").read_text() == "replacement chain"
    assert not any(".stage." in child.name for child in (moved / "output").iterdir())
    assert len([path for path in (moved / "output").iterdir() if path.name.startswith(".hsa4-failed-")]) == 1


def test_ancestor_swap_at_final_locator_revalidation_cannot_return_success(monkeypatch, case, tmp_path):
    request, _, *_ = case
    trusted = tmp_path / "trusted-final"
    output = trusted / "output"
    output.mkdir(parents=True)
    moved = tmp_path / "trusted-final-moved"
    original = hsa4._assert_root_chain
    calls = 0

    def swap_at_third_check(path, identities):
        nonlocal calls
        calls += 1
        if calls == 3:
            trusted.rename(moved)
            output.mkdir(parents=True)
            (output / "owner.txt").write_text("replacement locator")
        return original(path, identities)

    monkeypatch.setattr(hsa4, "_assert_root_chain", swap_at_third_check)
    assert_code("HSA4_E_OUTPUT_ROOT_REPLACED", hsa4.build_capture, request, output_root=output)
    assert (output / "owner.txt").read_text() == "replacement locator"
    assert not (output / request.snapshot_id).exists()
    assert not (moved / "output" / request.snapshot_id).exists()
    assert len([path for path in (moved / "output").iterdir() if path.name.startswith(".hsa4-failed-")]) == 1


def test_failed_quarantine_name_collision_preserves_unknown_and_stage(monkeypatch, case):
    request, output, *_ = case
    original_write = hsa4._write_file
    unknown = {}

    def fail_manifest(parent_fd, name, chunks):
        if name == "manifest.json":
            raise OSError("force stage cleanup")
        return original_write(parent_fd, name, chunks)

    def occupy_failed_name(parent_fd, source_name, failed_name, expected_identity):
        failed = output / failed_name
        failed.mkdir()
        (failed / "owner.txt").write_text("unknown failed name")
        unknown["inode"] = failed.stat().st_ino

    monkeypatch.setattr(hsa4, "_write_file", fail_manifest)
    monkeypatch.setattr(hsa4, "_before_failure_isolation", occupy_failed_name)
    assert_code("HSA4_E_FAILURE_ISOLATION_TAINT", hsa4.build_capture, request, output_root=output)
    failed = [path for path in output.iterdir() if path.name.startswith(".hsa4-failed-")]
    stage = [path for path in output.iterdir() if ".stage." in path.name]
    assert len(failed) == len(stage) == 1
    assert failed[0].stat().st_ino == unknown["inode"]
    assert (failed[0] / "owner.txt").read_text() == "unknown failed name"


def test_failure_marker_write_failure_still_preserves_quarantine(monkeypatch, case):
    request, output, *_ = case
    original_write = hsa4._write_file

    def fail_manifest(parent_fd, name, chunks):
        if name == "manifest.json":
            raise OSError("build failure")
        return original_write(parent_fd, name, chunks)

    def fail_marker(*args, **kwargs):
        raise OSError("marker failure")

    monkeypatch.setattr(hsa4, "_write_file", fail_manifest)
    monkeypatch.setattr(hsa4, "_write_failure_marker", fail_marker)
    with pytest.raises(OSError):
        hsa4.build_capture(request, output_root=output)
    failed = [path for path in output.iterdir() if path.name.startswith(".hsa4-failed-")]
    assert len(failed) == 1
    assert not (failed[0] / "failure_marker.json").exists()


def test_builder_contains_no_destructive_cleanup_calls():
    source = MODULE_PATH.read_text()
    assert "os.unlink" not in source
    assert "os.rmdir" not in source


def test_cli_rejects_non_isolated_output_root(case, tmp_path):
    request, _, raw, normalized = case
    argv = [
        "--snapshot-id", request.snapshot_id,
        "--source-family", request.source_family, "--source-id", request.source_id,
        "--provider", request.provider,
        "--source-endpoint-version", request.source_endpoint_version,
        "--parser-version", request.parser_version, "--schema-version", request.schema_version,
        "--trade-date", request.trade_date, "--source-published-at", request.source_published_at,
        "--available-at", request.available_at, "--fetched-at", request.fetched_at,
        "--http-status", "200", "--raw-file", str(raw), "--normalized-file", str(normalized),
        "--expected-instrument", "TW0001", "--returned-instrument", "TW0001",
        "--output-root", str(tmp_path / "not-canonical"),
    ]
    assert_code("HSA4_E_OUTPUT_ROOT", hsa4.main, argv)
