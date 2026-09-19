from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import build_tw_model_b_hsa5u_synthetic_acquisition_handoff as hsa5u  # noqa: E402


def _manifest(tmp_path: Path) -> dict:
    result = hsa5u.build_fixture(tmp_path / "fixture", project_root=tmp_path)
    assert result["decision"] == "READY_FOR_HSA6_NO_CRON_IMPLEMENTATION"
    return json.loads((tmp_path / "fixture" / "same_run_acquisition_handoff_manifest.json").read_text())


def _source(manifest: dict) -> dict:
    return manifest["sources"][0]


def test_complete_fixture_makes_existing_hsa5_ready_and_writes_manifest_last(tmp_path: Path) -> None:
    output = tmp_path / "fixture"
    result = hsa5u.build_fixture(output, project_root=tmp_path)
    assert result["decision"] == "READY_FOR_HSA6_NO_CRON_IMPLEMENTATION"
    assert (output / "manifest.json").is_file()
    preflight = json.loads((output / "hsa5_preflight" / "manifest.json").read_text())
    assert preflight["decision"] == "READY_FOR_HSA6_NO_CRON_IMPLEMENTATION"
    assert json.loads((output / "same_run_acquisition_handoff_manifest.json").read_text())["acquisition_run_id"] == hsa5u.RUN_ID


@pytest.mark.parametrize("mutation", [
    lambda m: m["sources"][0].pop("artifacts"),
    lambda m: m["sources"][0].update(acquisition_run_id="other.run"),
    lambda m: m["sources"][0]["artifacts"][0].update(sha256="0" * 64),
    lambda m: m["sources"][0].update(raw_artifact_role="stdout"),
    lambda m: m["sources"][0].update(source_validator_status="SKIPPED"),
    lambda m: m["sources"][0].update(absent_scope=["2330"]),
    lambda m: m["sources"][0].update(fetched_at="${LATEST_FETCHED_AT}"),
])
def test_contract_mutations_fail_closed(tmp_path: Path, mutation) -> None:
    manifest = _manifest(tmp_path)
    mutation(manifest)
    with pytest.raises(hsa5u.HSA5UError):
        hsa5u.validate_handoff(manifest)


def test_missing_manifest_is_not_accepted_by_hsa5(tmp_path: Path) -> None:
    output = tmp_path / "fixture"
    hsa5u.build_fixture(output, project_root=tmp_path)
    inventory_path = output / "source_inventory.json"
    inventory = json.loads(inventory_path.read_text())
    inventory.pop("acquisition_handoff_manifest_path")
    negative_inventory_path = output / "negative-source-inventory.json"
    hsa5u.write_json(negative_inventory_path, inventory)
    import build_tw_model_b_hsa5_daily_auto_sealed_capture_wiring_preflight as hsa5
    result = hsa5.build_preflight(
        daily_script=output / "daily_fixture.py", backend_script=output / "backend_fixture.py",
        source_inventory=negative_inventory_path, output_dir=output / "negative-preflight",
        project_root=tmp_path, allow_test_output_override=True,
    )
    assert result["decision"] == hsa5.STOP


def test_symlink_and_renamed_stdout_fail_closed(tmp_path: Path) -> None:
    manifest = _manifest(tmp_path)
    source = _source(manifest)
    raw = Path(source["raw_files"][0])
    link = raw.with_name("provider-response-renamed.json")
    link.symlink_to(raw)
    source["raw_files"] = [str(link)]
    source["artifacts"][0]["path"] = str(link)
    with pytest.raises(hsa5u.HSA5UError, match="symlink"):
        hsa5u.validate_handoff(manifest)


def test_renamed_stdout_file_is_not_accepted_as_raw(tmp_path: Path) -> None:
    manifest = _manifest(tmp_path)
    source = _source(manifest)
    raw = Path(source["raw_files"][0])
    renamed = raw.with_name("provider_stdout_renamed.json")
    renamed.write_bytes(raw.read_bytes())
    source["raw_files"] = [str(renamed)]
    source["artifacts"][0]["path"] = str(renamed)
    source["artifacts"][0]["sha256"] = hsa5u.sha256(renamed, tmp_path)
    with pytest.raises(hsa5u.HSA5UError, match="status_stream_not_raw"):
        hsa5u.validate_handoff(manifest, trusted_root=tmp_path)


def test_path_hash_mismatch_and_scope_overlap_are_independent_stops(tmp_path: Path) -> None:
    manifest = _manifest(tmp_path)
    mutated = copy.deepcopy(manifest)
    mutated["sources"][1]["artifacts"][0]["path"] = str(Path(mutated["sources"][1]["raw_files"][0]).with_name("missing.json"))
    with pytest.raises(hsa5u.HSA5UError):
        hsa5u.validate_handoff(mutated, trusted_root=tmp_path)
    mutated = copy.deepcopy(manifest)
    mutated["sources"][2]["unknown_scope"] = ["2330"]
    with pytest.raises(hsa5u.HSA5UError, match="partition_overlap"):
        hsa5u.validate_handoff(mutated, trusted_root=tmp_path)


def test_atomic_write_refuses_existing_final_and_staging(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    target = tmp_path / "evidence.json"
    target.write_bytes(b"owned-before")
    with pytest.raises(hsa5u.HSA5UError, match="final_exists"):
        hsa5u.atomic_write(target, b"replacement")
    assert target.read_bytes() == b"owned-before"

    target.unlink()
    monkeypatch.setattr(hsa5u.uuid, "uuid4", lambda: type("UUID", (), {"hex": "blocked"})())
    staging = target.with_name(f".{target.name}.staging.{__import__('os').getpid()}.blocked")
    staging.write_bytes(b"unknown-staging")
    with pytest.raises(hsa5u.HSA5UError, match="staging_exists"):
        hsa5u.atomic_write(target, b"payload")
    assert staging.read_bytes() == b"unknown-staging"


def test_secure_reads_reject_parent_symlink_and_outside_root(tmp_path: Path) -> None:
    trusted = tmp_path / "trusted"
    trusted.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    payload = outside / "payload.json"
    payload.write_bytes(b"payload")
    (trusted / "link").symlink_to(outside, target_is_directory=True)
    with pytest.raises(hsa5u.HSA5UError):
        hsa5u._secure_path(trusted / "link" / "payload.json", trusted)


def test_atomic_write_uses_noreplace_and_leaves_unknown_files(tmp_path: Path) -> None:
    target = tmp_path / "new.json"
    hsa5u.atomic_write(target, b"first")
    assert target.read_bytes() == b"first"
    assert not list(tmp_path.glob("*.staging*"))
    with pytest.raises(hsa5u.HSA5UError, match="final_exists"):
        hsa5u.atomic_write(target, b"second")
    assert target.read_bytes() == b"first"
