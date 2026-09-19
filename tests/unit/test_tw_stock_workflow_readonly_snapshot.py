from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
import yaml

from tw_stock_workflow.artifacts import ArtifactError
from tw_stock_workflow.readonly_snapshot import (
    ARTIFACT_TYPE,
    OBSERVATION_STATUS,
    ReadonlyStrategySnapshotAdapter,
)
from tw_stock_workflow.service import build_default_engine, run_workflow
from tw_stock_workflow.types import ExecutionContext


MODEL_A = "e4_frozen_qlib_2018_2022"
ASOF = "2026-09-18"


def test_default_engine_registration_does_not_load_snapshot_configuration(
    tmp_path: Path,
) -> None:
    engine = build_default_engine(tmp_path)

    assert engine.modules.get("readonly_strategy_snapshot.observe").module_id == (
        "readonly_strategy_snapshot.observe"
    )


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")


@pytest.fixture()
def snapshot_repo(tmp_path: Path) -> tuple[Path, Path, Path]:
    repo = tmp_path / "repo"
    source_dir = repo / f"data_tw/artifacts/signals/{MODEL_A}/source_run"
    signals = source_dir / "signals.csv"
    signals.parent.mkdir(parents=True)
    signals.write_text("date,instrument\n2026-09-18,TW2330\n", encoding="utf-8")
    source_manifest = source_dir / "manifest.json"
    write_json(
        source_manifest,
        {
            "artifact_type": "ModelSignalArtifact",
            "model_id": MODEL_A,
            "asof": ASOF,
            "status": "READY",
            "run_id": "source_run",
            "production_allowed": False,
            "not_published_latest": True,
            "no_latest": True,
            "files": {"signals": "signals.csv"},
        },
    )
    controlled_latest = source_dir.parent / "latest.json"
    write_json(
        controlled_latest,
        {
            "artifact_type": "controlled_model_signal_latest_pointer",
            "schema_version": "clpr.controlled_signal_latest_pointer.v1",
            "model_id": MODEL_A,
            "model_name": MODEL_A,
            "asof": ASOF,
            "signal_asof": ASOF,
            "run_id": "source_run",
            "canonical_artifact_dir": str(source_dir.relative_to(repo)),
            "source_artifact_dir": str(source_dir.relative_to(repo)),
            "canonical_manifest": str(source_manifest.relative_to(repo)),
            "canonical_manifest_sha256": sha256(source_manifest),
            "source_manifest_sha256": sha256(source_manifest),
            "canonical_signals": str(signals.relative_to(repo)),
            "canonical_signals_sha256": sha256(signals),
            "source_signals_sha256": sha256(signals),
            "readonly_only": True,
            "production_trade_enabled": False,
            "provider_publish": False,
            "provider_accepted_latest_switch": False,
            "qlib_accepted_latest_switch": False,
            "frontend_default_switch": False,
        },
    )

    snapshot_dir = (
        repo / f"data_tw/artifacts/publish/readonly_strategy_snapshot/{ASOF}"
    )
    write_json(
        snapshot_dir / "strategy_snapshot.json",
        {
            "asof": ASOF,
            "data_asof": ASOF,
            "signal_asof": ASOF,
            "model_id": MODEL_A,
            "base_model_id": MODEL_A,
            "strategy_rule": "candidate_only_no_strategy_replay",
            "candidate_boundary": "qlib_top50",
            "ranking_source": "qlib_rank_controlled_signal",
            "display_role": "primary_readonly_candidate",
            "candidate_only": True,
            "readonly_only": True,
            "production_trade_enabled": False,
            "no_order_action": True,
            "not_order": True,
            "not_target_position": True,
            "not_investment_advice": True,
            "is_production_trading_default": False,
            "marker": "AAAA",
        },
    )
    write_json(
        snapshot_dir / "validation_report.json",
        {
            "status": "pass",
            "readonly_snapshot_validator_ok": True,
            "checksum_ok": True,
        },
    )
    write_json(
        snapshot_dir / "forbidden_scope_audit.json",
        {
            "status": "pass",
            "all_forbidden_false": True,
            "flags": {
                "provider_publish_triggered": False,
                "monitor_broker_order_triggered": False,
            },
        },
    )
    manifest = snapshot_dir / "manifest.json"
    write_json(
        manifest,
        {
            "artifact_type": "readonly_strategy_snapshot",
            "schema_version": "readonly_strategy_snapshot_r13_v1",
            "asof": ASOF,
            "model_id": MODEL_A,
            "base_model_id": MODEL_A,
            "readonly_only": True,
            "production_trade_enabled": False,
            "no_order_action": True,
            "not_target_position": True,
            "not_investment_advice": True,
            "is_production_trading_default": False,
            "candidate_only": True,
            "strategy_rule": "candidate_only_no_strategy_replay",
            "candidate_boundary": "qlib_top50",
            "ranking_source": "qlib_rank_controlled_signal",
            "display_role": "primary_readonly_candidate",
            "order_intent_status": "not_built_forbidden_in_rsppr",
            "replay_result_status": "not_built_forbidden_in_rsppr",
            "snapshot": "strategy_snapshot.json",
            "validation_report": "validation_report.json",
            "forbidden_scope_audit": "forbidden_scope_audit.json",
            "checksum_manifest": "checksum_manifest.json",
            "source_signal_manifest": str(source_manifest.relative_to(repo)),
            "source_signal_manifest_sha256": sha256(source_manifest),
            "source_signal_csv": str(signals.relative_to(repo)),
            "source_signal_csv_sha256": sha256(signals),
            "source_signal_latest": str(controlled_latest.relative_to(repo)),
            "source_signal_latest_sha256": sha256(controlled_latest),
        },
    )
    files = {
        name: sha256(snapshot_dir / name)
        for name in (
            "manifest.json",
            "strategy_snapshot.json",
            "validation_report.json",
            "forbidden_scope_audit.json",
        )
    }
    write_json(
        snapshot_dir / "checksum_manifest.json",
        {
            "artifact_type": "readonly_strategy_snapshot_checksum_manifest",
            "files": files,
        },
    )
    latest = snapshot_dir.parent / "latest.json"
    write_json(
        latest,
        {
            "artifact_type": "readonly_strategy_snapshot_latest_pointer",
            "asof": ASOF,
            "readonly_only": True,
            "production_trade_enabled": False,
            "not_provider_accepted_latest": True,
            "not_trade_target_latest": True,
            "snapshot_manifest": str(manifest.relative_to(repo)),
            "candidate_only": True,
            "data_asof": ASOF,
            "signal_asof": ASOF,
            "source_signal_manifest_sha256": sha256(source_manifest),
            "source_signal_csv_sha256": sha256(signals),
            "source_signal_latest": str(controlled_latest.relative_to(repo)),
            "source_signal_latest_sha256": sha256(controlled_latest),
            "planned_manifest_payload_sha256": sha256(manifest),
        },
    )
    registry = repo / "configs/tw_product_artifact_registry.yaml"
    registry.parent.mkdir(parents=True)
    registry.write_text(
        yaml.safe_dump(
            {
                "schema_version": "tw_product_artifact_registry_v1",
                "readonly_only": True,
                "artifacts": {
                    "readonly_strategy_latest": str(latest.relative_to(repo))
                },
                "safety": {
                    "no_training_in_product_context": True,
                    "no_provider_publish": True,
                    "no_accepted_latest_switch": True,
                    "no_monitor_write": True,
                    "no_broker_order": True,
                },
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    baseline = repo / "configs/active_baseline_descriptor.yaml"
    baseline.write_text(
        yaml.safe_dump(
            {
                "schema_version": "arch1.active_baseline_descriptor.v1",
                "readonly_only": True,
                "simulation_only": True,
                "active_baseline": {
                    "status": "MODEL_A_ONLY",
                    "model_a": {"model_id": MODEL_A},
                    "model_b": None,
                },
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    spec = repo / "configs/workflows/readonly_strategy_snapshot_observation.yaml"
    spec.parent.mkdir(parents=True)
    spec.write_bytes(
        (
            Path(__file__).resolve().parents[2]
            / "configs/workflows/readonly_strategy_snapshot_observation.yaml"
        ).read_bytes()
    )
    return repo, snapshot_dir, spec


def query(repo: Path):
    return ReadonlyStrategySnapshotAdapter(repo).query(
        artifact_type=ARTIFACT_TYPE,
        model_id=MODEL_A,
        asof=ASOF,
        status=OBSERVATION_STATUS,
    )


def test_snapshot_adapter_returns_complete_candidate_only_ref(snapshot_repo) -> None:
    repo, _, _ = snapshot_repo
    refs = query(repo)

    assert len(refs) == 1
    ref = refs[0]
    assert ref.run_id == "source_run"
    assert ref.metadata["candidate_only"] is True
    assert ref.metadata["full_strategy_status"] == "NOT_BUILT"
    assert ref.metadata["source_signal_latest"]["path"] == (
        f"data_tw/artifacts/signals/{MODEL_A}/latest.json"
    )
    assert set(ref.metadata["declared_files"]) == {
        "manifest.json",
        "strategy_snapshot.json",
        "validation_report.json",
        "forbidden_scope_audit.json",
    }


def test_snapshot_workflow_runs_with_artifact_read_only(snapshot_repo) -> None:
    repo, _, spec = snapshot_repo
    result = run_workflow(
        repo_root=repo,
        spec_path=spec,
        context=ExecutionContext(
            mode="readonly",
            asof=ASOF,
            decision_cutoff="2026-09-18T11:00:00+00:00",
            workspace=repo.parent / "workspace",
            permissions=frozenset({"artifact.read"}),
        ),
    )

    assert result.status == "SUCCEEDED"
    output = result.record["nodes"]["observe_model_a_readonly_snapshot"]["output"]
    assert output["count"] == 1
    assert output["full_strategy_admission"] is False


def test_snapshot_same_size_replacement_is_rejected(snapshot_repo) -> None:
    repo, snapshot_dir, _ = snapshot_repo
    path = snapshot_dir / "strategy_snapshot.json"
    original = path.read_bytes()
    path.write_bytes(original.replace(b"AAAA", b"BBBB"))
    assert path.stat().st_size == len(original)

    with pytest.raises(ArtifactError, match="checksum mismatch"):
        query(repo)


def test_snapshot_source_signal_drift_is_rejected(snapshot_repo) -> None:
    repo, snapshot_dir, _ = snapshot_repo
    manifest = json.loads((snapshot_dir / "manifest.json").read_text(encoding="utf-8"))
    source = repo / manifest["source_signal_csv"]
    source.write_text("date,instrument\n2026-09-18,TW2317\n", encoding="utf-8")

    with pytest.raises(ArtifactError, match="source signal checksum mismatch"):
        query(repo)


def test_snapshot_stale_latest_is_rejected(snapshot_repo) -> None:
    repo, snapshot_dir, _ = snapshot_repo
    latest = snapshot_dir.parent / "latest.json"
    payload = json.loads(latest.read_text(encoding="utf-8"))
    payload["asof"] = "2026-09-17"
    write_json(latest, payload)

    with pytest.raises(ArtifactError, match="latest pointer identity"):
        query(repo)


def test_snapshot_payload_semantic_drift_is_rejected_after_resigning(
    snapshot_repo,
) -> None:
    repo, snapshot_dir, _ = snapshot_repo
    snapshot = snapshot_dir / "strategy_snapshot.json"
    payload = json.loads(snapshot.read_text(encoding="utf-8"))
    payload["model_id"] = "other_model"
    write_json(snapshot, payload)
    checksums = snapshot_dir / "checksum_manifest.json"
    checksum_payload = json.loads(checksums.read_text(encoding="utf-8"))
    checksum_payload["files"]["strategy_snapshot.json"] = sha256(snapshot)
    write_json(checksums, checksum_payload)

    with pytest.raises(ArtifactError, match="payload identity/safety"):
        query(repo)


def test_snapshot_source_outside_controlled_model_root_is_rejected_after_resigning(
    snapshot_repo,
) -> None:
    repo, snapshot_dir, _ = snapshot_repo
    private = repo / "data_tw/experiments/private/source_run"
    private.mkdir(parents=True)
    private_csv = private / "signals.csv"
    private_csv.write_text("date,instrument\n2026-09-18,TW2330\n", encoding="utf-8")
    private_manifest = private / "manifest.json"
    write_json(
        private_manifest,
        {
            "artifact_type": "ModelSignalArtifact",
            "model_id": MODEL_A,
            "asof": ASOF,
            "status": "READY",
            "run_id": "../../../experiments/private/source_run",
            "production_allowed": False,
            "not_published_latest": True,
            "no_latest": True,
            "files": {"signals": "signals.csv"},
        },
    )
    manifest = snapshot_dir / "manifest.json"
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload.update(
        {
            "source_signal_manifest": str(private_manifest.relative_to(repo)),
            "source_signal_manifest_sha256": sha256(private_manifest),
            "source_signal_csv": str(private_csv.relative_to(repo)),
            "source_signal_csv_sha256": sha256(private_csv),
        }
    )
    write_json(manifest, payload)
    checksums = snapshot_dir / "checksum_manifest.json"
    checksum_payload = json.loads(checksums.read_text(encoding="utf-8"))
    checksum_payload["files"]["manifest.json"] = sha256(manifest)
    write_json(checksums, checksum_payload)
    latest = snapshot_dir.parent / "latest.json"
    latest_payload = json.loads(latest.read_text(encoding="utf-8"))
    latest_payload.update(
        {
            "source_signal_manifest_sha256": sha256(private_manifest),
            "source_signal_csv_sha256": sha256(private_csv),
            "planned_manifest_payload_sha256": sha256(manifest),
        }
    )
    write_json(latest, latest_payload)

    with pytest.raises(ArtifactError, match="source signal run identity"):
        query(repo)


def test_snapshot_latest_lineage_drift_is_rejected(snapshot_repo) -> None:
    repo, snapshot_dir, _ = snapshot_repo
    latest = snapshot_dir.parent / "latest.json"
    payload = json.loads(latest.read_text(encoding="utf-8"))
    payload["source_signal_csv_sha256"] = "f" * 64
    write_json(latest, payload)

    with pytest.raises(ArtifactError, match="latest pointer identity"):
        query(repo)


def test_snapshot_controlled_latest_drift_is_rejected(snapshot_repo) -> None:
    repo, _, _ = snapshot_repo
    controlled_latest = repo / f"data_tw/artifacts/signals/{MODEL_A}/latest.json"
    payload = json.loads(controlled_latest.read_text(encoding="utf-8"))
    payload["run_id"] = "other_run"
    write_json(controlled_latest, payload)

    with pytest.raises(ArtifactError, match="controlled signal latest checksum"):
        query(repo)


def test_snapshot_resigned_controlled_latest_identity_drift_is_rejected(
    snapshot_repo,
) -> None:
    repo, snapshot_dir, _ = snapshot_repo
    controlled_latest = repo / f"data_tw/artifacts/signals/{MODEL_A}/latest.json"
    payload = json.loads(controlled_latest.read_text(encoding="utf-8"))
    payload["run_id"] = "other_run"
    write_json(controlled_latest, payload)

    manifest = snapshot_dir / "manifest.json"
    manifest_payload = json.loads(manifest.read_text(encoding="utf-8"))
    manifest_payload["source_signal_latest_sha256"] = sha256(controlled_latest)
    write_json(manifest, manifest_payload)

    checksums = snapshot_dir / "checksum_manifest.json"
    checksum_payload = json.loads(checksums.read_text(encoding="utf-8"))
    checksum_payload["files"]["manifest.json"] = sha256(manifest)
    write_json(checksums, checksum_payload)

    latest = snapshot_dir.parent / "latest.json"
    latest_payload = json.loads(latest.read_text(encoding="utf-8"))
    latest_payload["source_signal_latest_sha256"] = sha256(controlled_latest)
    latest_payload["planned_manifest_payload_sha256"] = sha256(manifest)
    write_json(latest, latest_payload)

    with pytest.raises(ArtifactError, match="controlled signal latest identity"):
        query(repo)


def test_snapshot_manifest_symlink_is_rejected(snapshot_repo) -> None:
    repo, snapshot_dir, _ = snapshot_repo
    manifest = snapshot_dir / "manifest.json"
    target = snapshot_dir / "manifest.real.json"
    manifest.rename(target)
    manifest.symlink_to(target.name)

    with pytest.raises(ArtifactError, match="may not be a symlink"):
        query(repo)
