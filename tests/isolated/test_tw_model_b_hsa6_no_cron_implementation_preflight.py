from __future__ import annotations

import copy
import json
import subprocess
import sys
from types import SimpleNamespace
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import build_tw_model_b_hsa5u_synthetic_acquisition_handoff as hsa5u  # noqa: E402
import build_tw_model_b_hsa6_no_cron_implementation_preflight as hsa6  # noqa: E402


def _fixture(tmp_path: Path) -> tuple[Path, dict]:
    root = tmp_path / "hsa5u"
    hsa5u.build_fixture(root, project_root=tmp_path)
    return root, json.loads((root / "same_run_acquisition_handoff_manifest.json").read_text())


def test_builds_one_hsa4_candidate_per_required_family(tmp_path: Path) -> None:
    source_root, _ = _fixture(tmp_path)
    output = tmp_path / "hsa6"
    result = hsa6.build_preflight(source_root, output, allow_test_output_override=True)
    assert result["decision"] == "PASS_HSA6_NO_CRON_ISOLATED_CANDIDATES"
    assert len(result["candidates"]) == 4
    assert len(list((output / "sealed_candidates").iterdir())) == 4
    assert (output / "manifest.json").is_file()
    validation = hsa6.validate_evidence_manifest(output)
    assert validation == {"artifact_count": 15, "candidate_manifest_count": 4, "all_checksums_match": True}
    root_manifest = json.loads((output / "manifest.json").read_text())
    artifact_paths = {item["path"] for item in root_manifest["artifacts"]}
    assert all(
        f"sealed_candidates/{family}/manifest.json" in artifact_paths
        for family in [
            "hsa6_adjusted_price_20260825_candidate",
            "hsa6_twii_20260825_candidate",
            "hsa6_institutional_flow_20260825_candidate",
            "hsa6_margin_short_20260825_candidate",
        ]
    )
    assert root_manifest["artifact_count"] == len(root_manifest["artifacts"])
    report = json.loads((output / "validation_report.json").read_text())
    assert report["protected_paths_unchanged"] is True
    assert len(report["protected_paths_before_after"]) == 11
    assert all(item["unchanged"] for item in report["protected_paths_before_after"].values())


def test_manifest_validator_rejects_changed_nested_candidate_manifest(tmp_path: Path) -> None:
    source_root, _ = _fixture(tmp_path)
    output = tmp_path / "hsa6"
    hsa6.build_preflight(source_root, output, allow_test_output_override=True)
    candidate_manifest = next((output / "sealed_candidates").glob("*/manifest.json"))
    candidate_manifest.write_text(candidate_manifest.read_text() + " ", encoding="utf-8")
    with pytest.raises(hsa6.HSA6Error, match="evidence_manifest_incomplete_or_checksum_mismatch"):
        hsa6.validate_evidence_manifest(output)


def test_manifest_validator_rejects_artifact_count_or_missing_candidate_manifest(tmp_path: Path) -> None:
    source_root, _ = _fixture(tmp_path)
    output = tmp_path / "hsa6"
    hsa6.build_preflight(source_root, output, allow_test_output_override=True)
    manifest_path = output / "manifest.json"
    payload = json.loads(manifest_path.read_text())
    payload["artifact_count"] -= 1
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(hsa6.HSA6Error, match="evidence_artifact_count_mismatch"):
        hsa6.validate_evidence_manifest(output)


def test_actual_crontab_fingerprint_always_uses_read_only_crontab_l_even_when_spool_is_available(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = []

    def fake_run(*args, **kwargs):
        calls.append((args, kwargs))
        return SimpleNamespace(returncode=0, stdout=b"0 1 * * 1 echo ok\n", stderr=b"")

    monkeypatch.setattr(hsa6, "_fingerprint", lambda path, **kwargs: {"status": "PRESENT"})
    monkeypatch.setattr(hsa6.subprocess, "run", fake_run)
    fingerprint = hsa6._actual_crontab_fingerprint()
    assert len(calls) == 1
    assert calls[0][0][0] == ["crontab", "-l"]
    assert calls[0][1]["stdin"] is subprocess.DEVNULL
    assert fingerprint["source"] == "crontab-l"
    assert fingerprint["status"] == "PRESENT"
    assert fingerprint["size"] == len(b"0 1 * * 1 echo ok\n")
    assert fingerprint["read_only_subprocess"] is True


def test_actual_crontab_fingerprint_stops_on_command_failure_or_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(hsa6.subprocess, "run", lambda *args, **kwargs: SimpleNamespace(returncode=1, stdout=b"", stderr=b"no crontab"))
    with pytest.raises(hsa6.HSA6Error, match="actual_crontab_read_failed"):
        hsa6._actual_crontab_fingerprint()

    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd="crontab -l", timeout=5)

    monkeypatch.setattr(hsa6.subprocess, "run", timeout)
    with pytest.raises(hsa6.HSA6Error, match="actual_crontab_read_failed:TimeoutExpired"):
        hsa6._actual_crontab_fingerprint()

    def os_error(*args, **kwargs):
        raise OSError("crontab unavailable")

    monkeypatch.setattr(hsa6.subprocess, "run", os_error)
    with pytest.raises(hsa6.HSA6Error, match="actual_crontab_read_failed:OSError"):
        hsa6._actual_crontab_fingerprint()


def test_protected_fingerprints_do_not_read_spool(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(hsa6, "_fingerprint", lambda path, **kwargs: {"path": str(path), "status": "ABSENT"})
    calls = []

    def fake_run(*args, **kwargs):
        calls.append(args[0])
        return SimpleNamespace(returncode=0, stdout=b"# empty\n", stderr=b"")

    monkeypatch.setattr(hsa6.subprocess, "run", fake_run)
    result = hsa6._protected_fingerprints(tmp_path)
    assert result["actual_crontab_locator"]["source"] == "crontab-l"
    assert calls == [["crontab", "-l"]]


def test_actual_crontab_before_after_content_change_is_detected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(hsa6, "_fingerprint", lambda path: (_ for _ in ()).throw(hsa6.HSA6Error("protected_path_inaccessible:spool")))
    outputs = iter([b"first\n", b"second\n"])
    monkeypatch.setattr(hsa6.subprocess, "run", lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout=next(outputs), stderr=b""))
    before = hsa6._actual_crontab_fingerprint()
    after = hsa6._actual_crontab_fingerprint()
    assert before["source"] == after["source"] == "crontab-l"
    assert before != after


@pytest.mark.parametrize("mutation", [
    lambda m: m["sources"][0].update(source_validator_status="SKIPPED"),
    lambda m: m["sources"][0].update(acquisition_run_id="wrong.run"),
    lambda m: m["sources"][0].update(raw_files=[]),
    lambda m: m.update(sources=m["sources"] + [{**m["sources"][0], "source_family": "unknown_family"}]),
])
def test_handoff_mismatch_validator_missing_or_unknown_family_stops(tmp_path: Path, mutation) -> None:
    source_root, manifest = _fixture(tmp_path)
    mutation(manifest)
    (source_root / "same_run_acquisition_handoff_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(hsa6.HSA6Error):
        hsa6.build_preflight(source_root, tmp_path / "hsa6", allow_test_output_override=True)


def test_scope_closure_and_missing_normalized_stop(tmp_path: Path) -> None:
    source_root, manifest = _fixture(tmp_path)
    manifest["sources"][0]["unknown_scope"] = ["2330"]
    (source_root / "same_run_acquisition_handoff_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(hsa6.HSA6Error):
        hsa6.build_preflight(source_root, tmp_path / "hsa6", allow_test_output_override=True)
    source_root, manifest = _fixture(tmp_path / "second")
    manifest["sources"][0]["normalized_files"] = []
    (source_root / "same_run_acquisition_handoff_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(hsa6.HSA6Error):
        hsa6.build_preflight(source_root, tmp_path / "second-hsa6", allow_test_output_override=True)


def test_duplicate_final_and_symlink_source_stop(tmp_path: Path) -> None:
    source_root, manifest = _fixture(tmp_path)
    output = tmp_path / "hsa6"
    hsa6.build_preflight(source_root, output, allow_test_output_override=True)
    with pytest.raises(hsa6.HSA6Error, match="output_root_must_be_new_empty"):
        hsa6.build_preflight(source_root, output, allow_test_output_override=True)
    source_root, manifest = _fixture(tmp_path / "symlink")
    raw = Path(manifest["sources"][0]["raw_files"][0])
    link = raw.with_name("raw-link.json")
    link.symlink_to(raw)
    manifest["sources"][0]["raw_files"] = [str(link)]
    (source_root / "same_run_acquisition_handoff_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(hsa6.HSA6Error):
        hsa6.build_preflight(source_root, tmp_path / "symlink-hsa6", allow_test_output_override=True)


def test_hsa5_ready_is_required(tmp_path: Path) -> None:
    source_root, _ = _fixture(tmp_path)
    preflight = source_root / "hsa5_preflight" / "manifest.json"
    payload = json.loads(preflight.read_text())
    payload["decision"] = "STOP_HSA5_UPSTREAM_CAPTURE_CONTRACT_GAPS"
    preflight.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(hsa6.HSA6Error, match="hsa5_not_READY"):
        hsa6.build_preflight(source_root, tmp_path / "hsa6", allow_test_output_override=True)


def test_hsa4_failure_isolation_leaves_quarantine_without_final(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source_root, _ = _fixture(tmp_path)
    output = tmp_path / "hsa6"
    import build_tw_model_b_hsa4_isolated_daily_sealed_capture as hsa4

    original = hsa4._copy_source

    def fail_once(*args, **kwargs):
        monkeypatch.setattr(hsa4, "_copy_source", original)
        raise hsa4.CaptureError("TEST_RACE", "source changed during copy")

    monkeypatch.setattr(hsa4, "_copy_source", fail_once)
    with pytest.raises(hsa4.CaptureError, match="TEST_RACE"):
        hsa6.build_preflight(source_root, output, allow_test_output_override=True)
    candidates = output / "sealed_candidates"
    assert not (candidates / "hsa6_adjusted_price_20260825_candidate").exists()
    quarantined = list(candidates.glob(".hsa4-failed-*"))
    assert len(quarantined) == 1
    assert (quarantined[0] / "failure_marker.json").is_file()
