from __future__ import annotations

import csv
import json
import sys
from argparse import Namespace
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import tw_research_data_history as history  # noqa: E402
import run_daily_tw_stock_auto_update as daily  # noqa: E402


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def make_model_a(repo: Path, asof: str, run_id: str) -> tuple[Path, Path]:
    input_dir = repo / "data_tw/canonical/model_inference_input" / history.MODEL_A_ID / run_id
    signal_dir = repo / "data_tw/artifacts/signals" / history.MODEL_A_ID / run_id
    for artifact_dir, artifact_type, data_file in (
        (input_dir, "ModelInferenceInput", "inference_frame.csv"),
        (signal_dir, "ModelSignalArtifact", "signals.csv"),
    ):
        write_json(artifact_dir / "manifest.json", {
            "artifact_type": artifact_type,
            "model_id": history.MODEL_A_ID,
            "run_id": run_id,
            "asof": asof,
            "status": "READY",
            "created_at": f"{asof}T10:00:00+00:00",
            "source_acquisition_run_id": f"source.{asof}",
            "decision_cutoff": f"{asof}T10:00:00+00:00",
        })
        write_json(artifact_dir / "validator_report.json", {"ok": True, "status": "PASS"})
        (artifact_dir / data_file).write_text("date,instrument,value\n" + f"{asof},TW2330,1\n", encoding="utf-8")
    return input_dir, signal_dir


def make_job(repo: Path, asof: str, run_id: str, *, job_id: str = "daily_fixture") -> tuple[dict, Path, Path]:
    input_dir, signal_dir = make_model_a(repo, asof, run_id)
    job_dir = repo / "data_tw/ops/daily_auto_update" / job_id
    job_dir.mkdir(parents=True)
    job = {
        "job_id": job_id,
        "model_signal_gate": {
            "summary": {
                "model_a_inference_input_path": str(input_dir.relative_to(repo)),
                "model_a_signal_path": str(signal_dir.relative_to(repo)),
            }
        },
    }
    return job, job_dir, signal_dir


def make_model_b(repo: Path, asof: str, signal_dir: Path) -> Path:
    artifact_dir = repo / "data_tw/ops/daily_auto_update/b19_fixture"
    artifact_dir.mkdir(parents=True)
    feature_names = [f"feature_{index:02d}" for index in range(78)]
    with (artifact_dir / "features_78.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["date", "instrument", *feature_names])
        writer.writerow([asof, "TW2330", *([1] * 78)])
    (artifact_dir / "signals.csv").write_text(
        f"date,instrument,score\n{asof},TW2330,1\n", encoding="utf-8"
    )
    for name in (
        "schema.json",
        "coverage_audit.csv",
        "forbidden_field_audit.csv",
        "legacy_mapping_audit.csv",
        "provider_input_inventory.json",
    ):
        (artifact_dir / name).write_text("{}\n" if name.endswith(".json") else "ok\n1\n", encoding="utf-8")
    write_json(artifact_dir / "validator_report.json", {"ok": True, "status": "PASS"})
    files = {}
    for name in history.MODEL_B_REQUIRED_FILES:
        if name == "manifest.json":
            continue
        files[name] = {"path": name, "sha256": history.sha256_file(artifact_dir / name)}
    write_json(artifact_dir / "manifest.json", {
        "model_id": history.MODEL_B_ID,
        "asof": asof,
        "status": "READY_RESEARCH_SHADOW",
        "feature_count": 78,
        "source_acquisition_run_id": f"source.{asof}",
        "decision_cutoff": f"{asof}T11:00:00+00:00",
        "source_model_a_artifact": str(signal_dir.relative_to(repo)),
        "production_allowed": False,
        "no_apply": True,
        "no_latest_write": True,
        "no_provider_write": True,
        "tw7769_excluded": True,
        "tw7769_substitution_performed": False,
        "protected_unchanged": True,
        "files": files,
    })
    return artifact_dir


def materialize(repo: Path, asof: str, job: dict, job_dir: Path, model_b_dir: Path | None = None) -> dict:
    return history.materialize_daily_research_history(
        repo_root=repo,
        asof=asof,
        job_id=job["job_id"],
        job=job,
        job_dir=job_dir,
        catalog_root=repo / "catalog",
        canonical_history_root=repo / "canonical_history",
        model_b_dir=model_b_dir,
    )


def test_model_a_is_indexed_by_reference_and_latest_advances(tmp_path: Path) -> None:
    job, job_dir, _ = make_job(tmp_path, "2026-09-18", "modela_run")
    result = materialize(tmp_path, "2026-09-18", job, job_dir)

    assert result["ok"] is True
    assert result["status"] == "READY_MODELA_ONLY"
    assert result["model_a"]["storage_policy"] == "REFERENCE_EXISTING_CANONICAL_ARTIFACTS"
    latest = json.loads((tmp_path / "catalog/latest.json").read_text(encoding="utf-8"))
    assert latest["asof"] == "2026-09-18"
    assert latest["model_b"] is None


def test_model_a_is_discovered_from_canonical_same_day_without_gate_summary(tmp_path: Path) -> None:
    _, job_dir, signal_dir = make_job(tmp_path, "2026-09-18", "modela_run")
    job = {"job_id": "no_gate_summary"}
    result = materialize(tmp_path, "2026-09-18", job, job_dir)

    assert result["ok"] is True
    assert result["status"] == "READY_MODELA_ONLY"
    assert result["model_a"]["signal"]["path"] == str(signal_dir.relative_to(tmp_path))


def test_ready_model_b_is_copied_idempotently_with_research_guards(tmp_path: Path) -> None:
    job, job_dir, signal_dir = make_job(tmp_path, "2026-09-18", "modela_run")
    model_b_dir = make_model_b(tmp_path, "2026-09-18", signal_dir)

    first = materialize(tmp_path, "2026-09-18", job, job_dir, model_b_dir)
    second = materialize(tmp_path, "2026-09-18", job, job_dir, model_b_dir)

    assert first["status"] == "READY_MODELA_MODELB"
    assert first["model_b"]["materialization"] == "CREATED"
    assert second["model_b"]["materialization"] == "IDEMPOTENT_NOOP"
    copied = tmp_path / first["model_b"]["history_path"]
    assert (copied / "features_78.csv").is_file()
    assert (copied / "legacy_mapping_audit.csv").is_file()
    assert (copied / "provider_input_inventory.json").is_file()
    record = json.loads((copied / "history_record.json").read_text(encoding="utf-8"))
    assert record["production_allowed"] is False
    assert record["no_apply"] is True


def test_invalid_model_b_warns_without_blocking_valid_model_a(tmp_path: Path) -> None:
    job, job_dir, signal_dir = make_job(tmp_path, "2026-09-18", "modela_run")
    model_b_dir = make_model_b(tmp_path, "2026-09-18", signal_dir)
    manifest_path = model_b_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["production_allowed"] = True
    write_json(manifest_path, manifest)

    result = materialize(tmp_path, "2026-09-18", job, job_dir, model_b_dir)

    assert result["ok"] is True
    assert result["status"] == "READY_MODELA_ONLY"
    assert result["model_b"] is None
    assert result["warnings"] and "research-only safety flags" in result["warnings"][0]


def test_model_b_missing_declared_checksum_is_not_materialized(tmp_path: Path) -> None:
    job, job_dir, signal_dir = make_job(tmp_path, "2026-09-18", "modela_run")
    model_b_dir = make_model_b(tmp_path, "2026-09-18", signal_dir)
    manifest_path = model_b_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    del manifest["files"]["provider_input_inventory.json"]["sha256"]
    write_json(manifest_path, manifest)

    result = materialize(tmp_path, "2026-09-18", job, job_dir, model_b_dir)

    assert result["status"] == "READY_MODELA_ONLY"
    assert "declared checksum missing: provider_input_inventory.json" in result["warnings"][0]


def test_model_b_staging_copy_is_reverified(tmp_path: Path, monkeypatch) -> None:
    job, job_dir, signal_dir = make_job(tmp_path, "2026-09-18", "modela_run")
    model_b_dir = make_model_b(tmp_path, "2026-09-18", signal_dir)
    real_copy = history.shutil.copy2

    def corrupt_copy(source, destination):
        copied = real_copy(source, destination)
        if Path(source).name == "signals.csv":
            Path(destination).write_text("corrupted\n", encoding="utf-8")
        return copied

    monkeypatch.setattr(history.shutil, "copy2", corrupt_copy)
    result = materialize(tmp_path, "2026-09-18", job, job_dir, model_b_dir)

    assert result["status"] == "READY_MODELA_ONLY"
    assert "staged Model B checksum mismatch: signals.csv" in result["warnings"][0]


def test_later_model_a_only_observation_retains_same_day_ready_model_b(tmp_path: Path) -> None:
    first_job, first_dir, signal_dir = make_job(tmp_path, "2026-09-18", "modela_run", job_id="first")
    model_b_dir = make_model_b(tmp_path, "2026-09-18", signal_dir)
    first = materialize(tmp_path, "2026-09-18", first_job, first_dir, model_b_dir)
    assert first["status"] == "READY_MODELA_MODELB"

    later_job = json.loads(json.dumps(first_job))
    later_job["job_id"] = "later"
    later_dir = tmp_path / "data_tw/ops/daily_auto_update/later"
    later_dir.mkdir(parents=True)
    later = materialize(tmp_path, "2026-09-18", later_job, later_dir)
    day_manifest = json.loads((tmp_path / later["manifest_path"]).read_text(encoding="utf-8"))

    assert later["status"] == "READY_MODELA_MODELB"
    assert later["model_b_retained_from_previous_observation"] is True
    assert later["model_b"]["content_sha256"] == first["model_b"]["content_sha256"]
    assert day_manifest["model_b"]["content_sha256"] == first["model_b"]["content_sha256"]


def test_same_day_different_model_a_does_not_retain_old_model_b(tmp_path: Path) -> None:
    first_job, first_dir, signal_dir = make_job(tmp_path, "2026-09-18", "modela_run", job_id="first")
    model_b_dir = make_model_b(tmp_path, "2026-09-18", signal_dir)
    assert materialize(tmp_path, "2026-09-18", first_job, first_dir, model_b_dir)["model_b"]

    later_job, later_dir, _ = make_job(tmp_path, "2026-09-18", "different_modela_run", job_id="later")
    later = materialize(tmp_path, "2026-09-18", later_job, later_dir)

    assert later["status"] == "READY_MODELA_ONLY"
    assert later["model_b"] is None
    assert later["model_b_retained_from_previous_observation"] is False


def test_older_backfill_does_not_regress_latest(tmp_path: Path) -> None:
    newer_job, newer_dir, _ = make_job(tmp_path, "2026-09-18", "newer", job_id="newer_job")
    older_job, older_dir, _ = make_job(tmp_path, "2026-09-17", "older", job_id="older_job")
    assert materialize(tmp_path, "2026-09-18", newer_job, newer_dir)["ok"] is True
    assert materialize(tmp_path, "2026-09-17", older_job, older_dir)["ok"] is True

    latest = json.loads((tmp_path / "catalog/latest.json").read_text(encoding="utf-8"))
    assert latest["asof"] == "2026-09-18"


def test_no_model_a_is_a_nonblocking_skip(tmp_path: Path) -> None:
    job_dir = tmp_path / "job"
    job_dir.mkdir()
    result = materialize(tmp_path, "2026-09-18", {"job_id": "empty"}, job_dir)
    assert result["ok"] is True
    assert result["status"] == "SKIPPED_NO_ACCEPTED_ASSET"
    assert result["mainline_blocking"] is False


def test_invalid_identity_returns_nonblocking_error(tmp_path: Path) -> None:
    result = history.materialize_daily_research_history(
        repo_root=tmp_path,
        asof="not-a-date",
        job_id="../escape",
        job={},
        job_dir=tmp_path,
    )
    assert result["ok"] is False
    assert result["status"] == "ERROR_NONBLOCKING"
    assert result["mainline_blocking"] is False


def test_noncanonical_iso_date_cannot_regress_latest(tmp_path: Path) -> None:
    job, job_dir, _ = make_job(tmp_path, "2026-09-18", "newer")
    assert materialize(tmp_path, "2026-09-18", job, job_dir)["ok"] is True

    result = history.materialize_daily_research_history(
        repo_root=tmp_path,
        asof="20260917",
        job_id="older_noncanonical",
        job={},
        job_dir=tmp_path,
        catalog_root=tmp_path / "catalog",
        canonical_history_root=tmp_path / "canonical_history",
    )

    assert result["status"] == "ERROR_NONBLOCKING"
    latest = json.loads((tmp_path / "catalog/latest.json").read_text(encoding="utf-8"))
    assert latest["asof"] == "2026-09-18"


def test_daily_orchestrator_wires_default_on_nonblocking_finalize_step() -> None:
    source = (ROOT / "scripts/run_daily_tw_stock_auto_update.py").read_text(encoding="utf-8")
    assert "materialize_daily_research_history(" in source
    assert '"--disable-research-data-history"' in source
    assert 'env_flag("TW_DAILY_AUTO_DISABLE_RESEARCH_DATA_HISTORY", False)' in source
    assert '"research_data_history_enabled": not bool(args.disable_research_data_history)' in source


def test_finalize_job_contains_unexpected_history_exception(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(daily, "write_daily_source_inventory", lambda *args, **kwargs: {})
    monkeypatch.setattr(daily, "write_daily_full_capture_accounting", lambda *args, **kwargs: {})
    monkeypatch.setattr(daily, "attach_daily_readiness_dashboard", lambda *args, **kwargs: None)
    monkeypatch.setattr(daily, "write_dng13_daily_chain_artifacts", lambda *args, **kwargs: None)
    monkeypatch.setattr(daily, "write_json", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        daily,
        "materialize_daily_research_history",
        lambda **kwargs: (_ for _ in ()).throw(RuntimeError("fixture failure")),
    )
    job = {"job_id": "fixture"}

    daily.finalize_job(
        job,
        job_dir=tmp_path,
        asof="2026-09-18",
        args=Namespace(disable_research_data_history=False),
    )

    assert job["research_data_history"]["status"] == "ERROR_NONBLOCKING"
    assert job["research_data_history"]["mainline_blocking"] is False
