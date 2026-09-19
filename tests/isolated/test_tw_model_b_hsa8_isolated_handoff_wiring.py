import hashlib
import json
import os
import sys
from types import SimpleNamespace
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import build_tw_model_b_hsa8_isolated_handoff_wiring as hsa8


FAMILIES = ("adjusted_price", "twii", "institutional_flow", "margin_short")


def make_sources(job: Path, run="daily.acquire.20260826.real", asof="2026-08-26"):
    sources = []
    for family in FAMILIES:
        raw = job / f"{family}.raw.json"
        norm = job / f"{family}.normalized.json"
        raw.write_text(json.dumps({"family": family, "raw": True}), encoding="utf-8")
        norm.write_text(json.dumps({"family": family, "normalized": True}), encoding="utf-8")
        sources.append({
            "snapshot_id": f"{family}.{run}", "source_family": family,
            "source_id": f"finmind.{family}.v1", "target_asof": asof,
            "endpoint": "https://provider.invalid/v1",
            "trade_date": asof,
            "acquisition_run_id": run, "provider": "FinMind",
            "source_endpoint_version": "dataset.v1", "parser_version": "parser.v1",
            "schema_version": "normalized.v1", "request_parameters": {"dataset": family},
            "http_status": 200, "transport_identity": "https", "source_validator_status": "PASS",
            "pit_status": "PASS",
            "source_published_at": f"{asof}T00:00:00+00:00",
            "available_at": f"{asof}T01:00:00+00:00", "fetched_at": f"{asof}T02:00:00+00:00",
            "expected_scope": ["2330", "2317"], "returned_scope": ["2330"],
            "absent_scope": ["2317"], "unknown_scope": [],
            "raw_files": [str(raw)], "normalized_files": [str(norm)],
        })
    for source in sources:
        family = source["source_family"]
        raw = [{"path": source["raw_files"][0], "role": "provider_raw_response", "sha256": hashlib.sha256(Path(source["raw_files"][0]).read_bytes()).hexdigest()}]
        normalized = [{"path": source["normalized_files"][0], "role": "provider_normalized_payload", "sha256": hashlib.sha256(Path(source["normalized_files"][0]).read_bytes()).hexdigest()}]
        adapter = job / f"{family}.adapter_output.json"
        payload = {"source_family": family, "provider": source["provider"], "source_id": source["source_id"], "trade_date": source["trade_date"], "http_status": source["http_status"], "validator_status": source["source_validator_status"], "pit_status": source["pit_status"], "expected_scope": source["expected_scope"], "returned_scope": source["returned_scope"], "absent_scope": source["absent_scope"], "unknown_scope": source["unknown_scope"], "endpoint": source["endpoint"], "endpoint_version": source["source_endpoint_version"], "parser_version": source["parser_version"], "schema_version": source["schema_version"], "transport_identity": source["transport_identity"], "request_parameters": source["request_parameters"], "acquisition_run_id": source["acquisition_run_id"], "target_asof": source["target_asof"], "source_published_at": source["source_published_at"], "available_at": source["available_at"], "fetched_at": source["fetched_at"], "raw_files": raw, "normalized_files": normalized}
        payload["canonical_metadata_digest"] = hashlib.sha256(json.dumps({k: payload[k] for k in ("provider", "source_id", "trade_date", "http_status", "validator_status", "pit_status", "expected_scope", "returned_scope", "absent_scope", "unknown_scope", "endpoint", "endpoint_version", "request_parameters", "acquisition_run_id", "target_asof", "raw_files", "normalized_files")}, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        adapter.write_text(json.dumps(payload), encoding="utf-8")
        source["adapter_output_path"] = str(adapter)
        source["adapter_output_files"] = [str(adapter)]
    return sources


def test_valid_contract_writes_manifest_last_and_rebinds_hashes(tmp_path):
    job = tmp_path / "job"; job.mkdir(); output = tmp_path / "evidence"
    hsa8.ISOLATED_ROOT = tmp_path
    path = hsa8.build_handoff(job, "daily.acquire.20260826.real", "2026-08-26", make_sources(job), output)
    payload = json.loads(path.read_text())
    assert payload["schema_version"] == hsa8.SCHEMA
    assert {x["source_family"] for x in payload["sources"]} == set(FAMILIES)
    for source in payload["sources"]:
        for item in source["artifacts"]:
            assert item["sha256"] == hashlib.sha256(Path(item["path"]).read_bytes()).hexdigest()
    assert path.stat().st_mode & 0o777 == 0o640


def test_first_successful_capture_availability_mode_is_backward_compatible(tmp_path):
    job = tmp_path / "job"; job.mkdir()
    sources = make_sources(job)
    for source in sources:
        adapter = Path(source["adapter_output_path"])
        payload = json.loads(adapter.read_text(encoding="utf-8"))
        payload["source_published_at"] = None
        payload["available_at"] = "2026-08-26T01:30:00+00:00"
        payload["availability_evidence"] = {
            "method": "first_successful_capture",
            "observed_at": "2026-08-26T01:30:00+00:00",
            "observation_scope": "segment_capture",
        }
        source["source_published_at"] = None
        source["available_at"] = payload["available_at"]
        source["fetched_at"] = payload["fetched_at"]
        source["availability_evidence"] = payload["availability_evidence"]
        canonical = hsa8._canonical_metadata(source, payload["raw_files"], payload["normalized_files"])
        payload["canonical_metadata_digest"] = hsa8._canonical_digest(canonical)
        adapter.write_text(json.dumps(payload), encoding="utf-8")
    hsa8.ISOLATED_ROOT = tmp_path
    built = hsa8.validate_and_build("daily.acquire.20260826.real", "2026-08-26", sources, job)
    assert built["sources"][0]["availability_evidence"]["method"] == "first_successful_capture"


@pytest.mark.parametrize("run_id", [
    "daily_tw_stock_auto_update_20260827_20260827T144501Z",
    "daily_tw_stock_auto_update_20260228_20260228T000000Z",
])
def test_real_daily_job_id_format_is_accepted_and_exactly_bound(tmp_path, run_id):
    job = tmp_path / "job"; job.mkdir()
    sources = make_sources(job, run=run_id, asof="2026-08-27")
    payload = hsa8.validate_and_build(run_id, "2026-08-27", sources, job)
    assert payload["acquisition_run_id"] == run_id
    assert all(source["acquisition_run_id"] == run_id for source in payload["sources"])


@pytest.mark.parametrize("run_id", [
    "daily_tw_stock_auto_update_2026082_20260827T144501Z",
    "daily_tw_stock_auto_update_20260827_20260827t144501Z",
    "daily_tw_stock_auto_update_20260827_20260827T14450Z",
    "daily_tw_stock_auto_update_20261301_20260827T144501Z",
    "daily_tw_stock_auto_update_20260827_20260827T256061Z",
    "daily_tw_stock_auto_update_20260827_20260827T144501z",
    "daily_tw_stock_auto_update_20260827_20260827T144501Z" + "x" * 129,
])
def test_real_daily_job_id_invalid_shape_or_timestamp_fails_closed(tmp_path, run_id):
    job = tmp_path / "job"; job.mkdir()
    sources = make_sources(job)
    with pytest.raises(hsa8.HSA8Error, match="acquisition_run_id:invalid"):
        hsa8.validate_and_build(run_id, "2026-08-26", sources, job)


def test_real_daily_job_id_source_binding_remains_exact(tmp_path):
    run_id = "daily_tw_stock_auto_update_20260827_20260827T144501Z"
    job = tmp_path / "job"; job.mkdir()
    sources = make_sources(job, run=run_id, asof="2026-08-27")
    sources[0]["acquisition_run_id"] = "daily_tw_stock_auto_update_20260827_20260827T144502Z"
    with pytest.raises(hsa8.HSA8Error, match="run_or_asof_mismatch|override_mismatch"):
        hsa8.validate_and_build(run_id, "2026-08-27", sources, job)


@pytest.mark.parametrize("mutation", [
    lambda s: s.pop(),
    lambda s: s[0].update(available_at="2026-08-26T03:00:00+00:00"),
    lambda s: s[0].update(absent_scope=["2330"]),
    lambda s: s[0].update(acquisition_run_id="other.run"),
    lambda s: s[0].update(source_validator_status="WARN"),
])
def test_contract_fail_closed(tmp_path, mutation):
    job = tmp_path / "job"; job.mkdir()
    sources = make_sources(job)
    mutation(sources)
    with pytest.raises(hsa8.HSA8Error):
        hsa8.validate_and_build("daily.acquire.20260826.real", "2026-08-26", sources, job)


@pytest.mark.parametrize("mutation", [
    lambda s: s[0].update(provider="Other"),
    lambda s: s[0].update(source_validator_status="WARN"),
    lambda s: s[0].update(trade_date="2026-08-25"),
    lambda s: s[0].update(expected_scope=["other"]),
    lambda s: s[0].update(returned_scope=["other"]),
    lambda s: s[0].update(returned_scope=["2330"], absent_scope=[], unknown_scope=[]),
])
def test_authoritative_adapter_metadata_and_scope_missing_or_invalid_stops(tmp_path, mutation):
    job = tmp_path / "job"; job.mkdir()
    sources = make_sources(job)
    mutation(sources)
    with pytest.raises(hsa8.HSA8Error):
        hsa8.validate_and_build("daily.acquire.20260826.real", "2026-08-26", sources, job)


def test_adapter_output_is_required_to_be_job_local_and_bound_when_declared(tmp_path):
    job = tmp_path / "job"; job.mkdir()
    sources = make_sources(job)
    adapter = job / "adjusted_price.adapter_output.json"
    source = sources[0]
    raw_binding = [{"path": str(job / "adjusted_price.raw.json"), "role": "provider_raw_response", "sha256": hashlib.sha256((job / "adjusted_price.raw.json").read_bytes()).hexdigest()}]
    normalized_binding = [{"path": str(job / "adjusted_price.normalized.json"), "role": "provider_normalized_payload", "sha256": hashlib.sha256((job / "adjusted_price.normalized.json").read_bytes()).hexdigest()}]
    adapter.write_text(json.dumps({"source_family": source["source_family"], "provider": source["provider"], "source_id": source["source_id"], "trade_date": source["trade_date"], "http_status": source["http_status"], "validator_status": source["source_validator_status"], "pit_status": source["pit_status"], "expected_scope": source["expected_scope"], "returned_scope": source["returned_scope"], "absent_scope": source["absent_scope"], "unknown_scope": source["unknown_scope"], "endpoint": source["endpoint"], "endpoint_version": source["source_endpoint_version"], "parser_version": source["parser_version"], "schema_version": source["schema_version"], "transport_identity": source["transport_identity"], "request_parameters": source["request_parameters"], "acquisition_run_id": source["acquisition_run_id"], "target_asof": source["target_asof"], "source_published_at": source["source_published_at"], "available_at": source["available_at"], "fetched_at": source["fetched_at"], "raw_files": raw_binding, "normalized_files": normalized_binding}), encoding="utf-8")
    adapter_payload = json.loads(adapter.read_text(encoding="utf-8"))
    digest_fields = ("provider", "source_id", "trade_date", "http_status", "validator_status", "pit_status", "expected_scope", "returned_scope", "absent_scope", "unknown_scope", "endpoint", "endpoint_version", "request_parameters", "acquisition_run_id", "target_asof", "raw_files", "normalized_files")
    adapter_payload["canonical_metadata_digest"] = hashlib.sha256(json.dumps({k: adapter_payload[k] for k in digest_fields}, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    adapter.write_text(json.dumps(adapter_payload), encoding="utf-8")
    sources[0]["adapter_output_path"] = str(adapter)
    sources[0]["adapter_output_files"] = [str(adapter)]
    payload = hsa8.validate_and_build("daily.acquire.20260826.real", "2026-08-26", sources, job)
    bound = payload["sources"][0]["adapter_output_files"][0]
    assert bound["role"] == "adapter_output_metadata"
    assert bound["sha256"] == hashlib.sha256(adapter.read_bytes()).hexdigest()
    outside = tmp_path / "outside-adapter.json"; outside.write_text("{}", encoding="utf-8")
    sources[0]["adapter_output_path"] = str(outside)
    sources[0]["adapter_output_files"] = [str(outside)]
    with pytest.raises(hsa8.HSA8Error, match="outside_job_root"):
        hsa8.validate_and_build("daily.acquire.20260826.real", "2026-08-26", sources, job)
    sources = make_sources(job)
    adapter = job / "adjusted_price.adapter_output.json"
    adapter.write_text(json.dumps({"acquisition_run_id": "other.run", "target_asof": "2026-08-26", "source_id": sources[0]["source_id"]}), encoding="utf-8")
    sources[0]["adapter_output_path"] = str(adapter)
    sources[0]["adapter_output_files"] = [str(adapter)]
    with pytest.raises(hsa8.HSA8Error, match="required_field_missing"):
        hsa8.validate_and_build("daily.acquire.20260826.real", "2026-08-26", sources, job)


def test_adapter_canonical_digest_tamper_stops(tmp_path):
    job = tmp_path / "job"; job.mkdir()
    sources = make_sources(job)
    source = sources[0]
    adapter = job / "adjusted_price.adapter_output.json"
    raw = [{"path": str(job / "adjusted_price.raw.json"), "role": "provider_raw_response", "sha256": hashlib.sha256((job / "adjusted_price.raw.json").read_bytes()).hexdigest()}]
    normalized = [{"path": str(job / "adjusted_price.normalized.json"), "role": "provider_normalized_payload", "sha256": hashlib.sha256((job / "adjusted_price.normalized.json").read_bytes()).hexdigest()}]
    payload = {"source_family": source["source_family"], "provider": source["provider"], "source_id": source["source_id"], "trade_date": source["trade_date"], "http_status": source["http_status"], "validator_status": "PASS", "pit_status": "PASS", "expected_scope": source["expected_scope"], "returned_scope": source["returned_scope"], "absent_scope": source["absent_scope"], "unknown_scope": source["unknown_scope"], "endpoint": source["endpoint"], "endpoint_version": source["source_endpoint_version"], "parser_version": source["parser_version"], "schema_version": source["schema_version"], "transport_identity": source["transport_identity"], "request_parameters": source["request_parameters"], "acquisition_run_id": source["acquisition_run_id"], "target_asof": source["target_asof"], "source_published_at": source["source_published_at"], "available_at": source["available_at"], "fetched_at": source["fetched_at"], "raw_files": raw, "normalized_files": normalized, "canonical_metadata_digest": "0" * 64}
    adapter.write_text(json.dumps(payload), encoding="utf-8")
    source["adapter_output_path"] = str(adapter); source["adapter_output_files"] = [str(adapter)]
    with pytest.raises(hsa8.HSA8Error, match="canonical_digest_mismatch"):
        hsa8.validate_and_build("daily.acquire.20260826.real", "2026-08-26", sources, job)


def test_pit_mismatch_and_nonclosed_adapter_scope_stop(tmp_path):
    job = tmp_path / "job"; job.mkdir()
    sources = make_sources(job)
    sources[0]["available_at"] = "2026-08-26T03:00:00+00:00"
    with pytest.raises(hsa8.HSA8Error, match="override_mismatch"):
        hsa8.validate_and_build("daily.acquire.20260826.real", "2026-08-26", sources, job)
    sources = make_sources(job)
    sources[0]["unknown_scope"] = ["not-in-expected"]
    with pytest.raises(hsa8.HSA8Error, match="override_mismatch"):
        hsa8.validate_and_build("daily.acquire.20260826.real", "2026-08-26", sources, job)


def test_path_escape_symlink_and_hash_drift_fail_closed(tmp_path):
    job = tmp_path / "job"; job.mkdir(); sources = make_sources(job)
    outside = tmp_path / "outside.json"; outside.write_text("outside")
    sources[0]["raw_files"] = [str(outside)]
    with pytest.raises(hsa8.HSA8Error, match="override_mismatch"):
        hsa8.validate_and_build("daily.acquire.20260826.real", "2026-08-26", sources, job)
    link = job / "link.json"; link.symlink_to(outside)
    sources = make_sources(job); sources[0]["raw_files"] = [str(link)]
    with pytest.raises(hsa8.HSA8Error):
        hsa8.validate_and_build("daily.acquire.20260826.real", "2026-08-26", sources, job)
    sources = make_sources(job); sources[0]["raw_files"] = [str(job / "missing.json")]
    with pytest.raises(hsa8.HSA8Error):
        hsa8.validate_and_build("daily.acquire.20260826.real", "2026-08-26", sources, job)


def test_existing_final_is_append_only(tmp_path):
    job = tmp_path / "job"; job.mkdir(); output = tmp_path / "evidence"
    hsa8.ISOLATED_ROOT = tmp_path
    hsa8.build_handoff(job, "daily.acquire.20260826.real", "2026-08-26", make_sources(job), output)
    with pytest.raises(hsa8.HSA8Error, match="final_exists"):
        hsa8.build_handoff(job, "daily.acquire.20260826.real", "2026-08-26", make_sources(job), output)


def test_output_must_be_isolated_and_not_symlink(tmp_path):
    job = tmp_path / "job"; job.mkdir(); hsa8.ISOLATED_ROOT = tmp_path / "allowed"; hsa8.ISOLATED_ROOT.mkdir()
    with pytest.raises(hsa8.HSA8Error, match="outside_isolated_root"):
        hsa8.build_handoff(job, "daily.acquire.20260826.real", "2026-08-26", make_sources(job), tmp_path / "production")
    linked = hsa8.ISOLATED_ROOT / "linked"; linked.symlink_to(tmp_path / "elsewhere", target_is_directory=True)
    with pytest.raises(hsa8.HSA8Error, match="symlink_component"):
        hsa8.build_handoff(job, "daily.acquire.20260826.real", "2026-08-26", make_sources(job), linked / "evidence")


def test_atomic_rename_failure_cleans_only_staging(tmp_path, monkeypatch):
    output = tmp_path / "evidence"; output.mkdir(); final = output / "same_run_acquisition_handoff_manifest.json"
    hsa8.ISOLATED_ROOT = tmp_path
    monkeypatch.setattr(hsa8, "_rename_noreplace", lambda *args: (_ for _ in ()).throw(hsa8.HSA8Error("forced_rename_failure")))
    with pytest.raises(hsa8.HSA8Error, match="forced_rename_failure"):
        hsa8._atomic_json(final, {"ok": True})
    assert not final.exists()
    assert not list(output.glob("*.staging.*"))


def test_atomic_rename_conflict_cleans_staging_and_keeps_final(tmp_path):
    output = tmp_path / "evidence"; output.mkdir(); final = output / "same_run_acquisition_handoff_manifest.json"
    hsa8.ISOLATED_ROOT = tmp_path
    final.write_text("first", encoding="utf-8")
    with pytest.raises(hsa8.HSA8Error, match="final_exists"):
        hsa8._atomic_json(final, {"ok": True})
    assert final.read_text(encoding="utf-8") == "first"
    assert not list(output.glob("*.staging.*"))


def test_atomic_write_and_fsync_failure_clean_staging(tmp_path, monkeypatch):
    output = tmp_path / "evidence"; output.mkdir(); final = output / "same_run_acquisition_handoff_manifest.json"
    hsa8.ISOLATED_ROOT = tmp_path
    monkeypatch.setattr(hsa8.os, "fsync", lambda fd: (_ for _ in ()).throw(OSError("fsync failure")))
    with pytest.raises(OSError, match="fsync failure"):
        hsa8._atomic_json(final, {"ok": True})
    assert not final.exists()
    assert not list(output.glob("*.staging.*"))


def test_renameat2_unavailable_cleans_staging(tmp_path, monkeypatch):
    output = tmp_path / "evidence"; output.mkdir(); final = output / "same_run_acquisition_handoff_manifest.json"
    hsa8.ISOLATED_ROOT = tmp_path
    monkeypatch.setattr(hsa8, "_rename_noreplace", lambda *args: (_ for _ in ()).throw(hsa8.HSA8Error("renameat2_unavailable")))
    with pytest.raises(hsa8.HSA8Error, match="renameat2_unavailable"):
        hsa8._atomic_json(final, {"ok": True})
    assert not final.exists()
    assert not list(output.glob("*.staging.*"))


def test_stage_inode_replacement_is_rejected_and_replacement_final_is_preserved(tmp_path, monkeypatch):
    output = tmp_path / "evidence"; output.mkdir(); final = output / "same_run_acquisition_handoff_manifest.json"
    hsa8.ISOLATED_ROOT = tmp_path
    real_rename = hsa8._rename_noreplace
    def replace_stage(directory, source, destination):
        decoy = ".decoy"
        decoy_fd = os.open(decoy, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o640, dir_fd=directory)
        os.write(decoy_fd, b"decoy\n"); os.close(decoy_fd)
        os.unlink(source, dir_fd=directory)
        fd = os.open(source, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o640, dir_fd=directory)
        os.write(fd, b"replacement\n"); os.fsync(fd); os.close(fd)
        os.unlink(decoy, dir_fd=directory)
        real_rename(directory, source, destination)
        real_stat = hsa8.os.stat
        def mismatched_stat(path, *args, **kwargs):
            info = real_stat(path, *args, **kwargs)
            if path == destination:
                return SimpleNamespace(st_dev=info.st_dev + 1, st_ino=info.st_ino, st_size=info.st_size, st_mtime_ns=info.st_mtime_ns)
            return info
        monkeypatch.setattr(hsa8.os, "stat", mismatched_stat)
    monkeypatch.setattr(hsa8, "_rename_noreplace", replace_stage)
    with pytest.raises(hsa8.HSA8Error, match="final_inode_mismatch"):
        hsa8._atomic_json(final, {"ok": True})
    assert final.exists()
    assert final.read_text(encoding="utf-8") == "replacement\n"
    assert not list(output.glob("*.staging.*"))


def test_parent_locator_replacement_is_rejected_and_original_parent_final_is_preserved(tmp_path, monkeypatch):
    output = tmp_path / "evidence"; output.mkdir(); final = output / "same_run_acquisition_handoff_manifest.json"
    hsa8.ISOLATED_ROOT = tmp_path
    real_rename = hsa8._rename_noreplace
    def replace_parent(directory, source, destination):
        real_rename(directory, source, destination)
        backup = output.with_name("evidence.parent-replaced")
        os.rename(output, backup)
        output.mkdir()
    monkeypatch.setattr(hsa8, "_rename_noreplace", replace_parent)
    with pytest.raises(hsa8.HSA8Error, match="parent_locator_changed"):
        hsa8._atomic_json(final, {"ok": True})
    assert (output / final.name).exists() is False
    assert (output.with_name("evidence.parent-replaced") / final.name).exists()
    assert not list(output.glob("*.staging.*"))


def test_runtime_handoff_is_allowed_only_under_job_root(tmp_path):
    job = tmp_path / "job"
    job.mkdir()
    outside = tmp_path / "outside"
    with pytest.raises(hsa8.HSA8Error, match="outside_job_root"):
        hsa8.build_runtime_handoff(job, "daily.acquire.20260825.real", "2026-08-25", [], outside)


def test_runtime_handoff_stays_fail_closed_for_missing_pit_and_required_family(tmp_path):
    job = tmp_path / "job"
    job.mkdir()
    with pytest.raises(hsa8.HSA8Error):
        hsa8.build_runtime_handoff(job, "daily.acquire.20260825.real", "2026-08-25", [], job / "handoff")
    assert not (job / "handoff" / "same_run_acquisition_handoff_manifest.json").exists()
