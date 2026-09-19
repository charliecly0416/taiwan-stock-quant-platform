from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from tw_stock_workflow.artifacts import ArtifactError
from tw_stock_workflow.replay import ReadonlyReplayWindowAdapter
from tw_stock_workflow.run_registry import RunRegistry
from tw_stock_workflow.service import build_default_engine
from tw_stock_workflow.spec import WorkflowSpec
from tw_stock_workflow.types import ExecutionContext


ROOT = Path(__file__).resolve().parents[2]
FIXTURE_SOURCE = ROOT / "tests/fixtures/tw_stock_workflow_replay/repo"
MODEL_A = "e4_frozen_qlib_2018_2022"
STRATEGY = "top50_exit_one_worst_sell"
D7_MANIFEST = Path("data_tw/artifacts/readonly_replay_windows/d7/manifest.json")
D7_CHECKSUM = Path(
    "data_tw/artifacts/readonly_replay_windows/d7/checksum_manifest.json"
)
D6_MANIFEST = Path(
    "data_tw/artifacts/readonly_replay_windows/d6/e4_frozen_qlib_2018_2022/"
    "top50_exit_one_worst_sell/20260101_20260507/order_intent_replay_result/manifest.json"
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )


def fixture_repo(tmp_path: Path) -> Path:
    target = tmp_path / "repo"
    shutil.copytree(FIXTURE_SOURCE, target)
    return target


def refresh_declared_checksum(
    repo: Path, checksum_relative: Path, target_relative: Path
) -> None:
    checksum_path = repo / checksum_relative
    payload = json.loads(checksum_path.read_text(encoding="utf-8"))
    for item in payload["files"]:
        if item["path"] == str(target_relative):
            target = repo / target_relative
            item["sha256"] = sha256(target)
            item["bytes"] = target.stat().st_size
            write_json(checksum_path, payload)
            return
    raise AssertionError(f"checksum record not found: {target_relative}")


def replay_spec() -> WorkflowSpec:
    return WorkflowSpec.from_mapping(
        {
            "schema_version": "tw.workflow.spec.v1",
            "workflow_id": "test.replay_window_observation",
            "version": "1",
            "nodes": [
                {
                    "id": "observe",
                    "module": "replay_window.observe",
                    "policy": "required",
                    "config": {
                        "model_id": MODEL_A,
                        "strategy_rule": STRATEGY,
                        "window_start": "2026-01-01",
                        "window_end": "2026-05-07",
                        "status": "INDEXED_READONLY",
                    },
                }
            ],
        }
    )


def context(workspace: Path, permissions: frozenset[str]) -> ExecutionContext:
    return ExecutionContext(
        mode="readonly",
        asof="2026-05-07",
        decision_cutoff="2026-05-07T13:30:00+08:00",
        workspace=workspace,
        permissions=permissions,
    )


def test_adapter_reads_committed_formal_shape_without_claiming_replay_admission() -> (
    None
):
    refs = ReadonlyReplayWindowAdapter(FIXTURE_SOURCE).query(
        artifact_type="ReadonlyReplayWindowArtifact",
        model_id=MODEL_A,
        asof="2026-05-07",
        status="INDEXED_READONLY",
        strategy_rule=STRATEGY,
        window_start="2026-01-01",
        window_end="2026-05-07",
    )

    assert len(refs) == 1
    ref = refs[0]
    assert ref.manifest_path == str(D6_MANIFEST)
    assert ref.metadata["index_manifest_path"] == str(D7_MANIFEST)
    assert ref.metadata["full_replay_contract_status"] == "HOLD"
    assert ref.metadata["full_replay_contract_gaps"] == [
        "not_copied_from_legacy_replay",
        "model_training_windows_traceable",
        "source_order_intents_exist",
    ]
    assert ref.metadata["no_recompute"] is True
    assert ref.metadata["no_switch"] is True
    assert ref.artifact_type != "ReplayResultArtifact"


def test_workflow_binds_d7_and_d6_hashes_and_is_idempotent(tmp_path: Path) -> None:
    repo = fixture_repo(tmp_path)
    engine = build_default_engine(repo)
    run_context = context(tmp_path / "workspace", frozenset({"replay.read"}))

    first = engine.run(replay_spec(), run_context)
    second = engine.run(replay_spec(), run_context)

    assert first.status == "SUCCEEDED"
    assert second.idempotent_reuse is True
    artifact = first.record["artifact_inputs"]["observe"][0]
    assert artifact["manifest_sha256"] == sha256(repo / D6_MANIFEST)
    assert artifact["metadata"]["index_manifest_sha256"] == sha256(repo / D7_MANIFEST)
    assert artifact["metadata"]["full_replay_contract_status"] == "HOLD"


def test_replay_observation_permission_is_default_deny(tmp_path: Path) -> None:
    repo = fixture_repo(tmp_path)
    result = build_default_engine(repo).run(
        replay_spec(), context(tmp_path / "workspace", frozenset())
    )

    assert result.status == "BLOCKED"
    assert result.record["nodes"]["observe"]["reason"] == "permission_denied"
    assert result.record["nodes"]["observe"]["missing_permissions"] == ["replay.read"]


def test_checksum_failure_writes_atomic_failed_run_evidence(tmp_path: Path) -> None:
    repo = fixture_repo(tmp_path)
    summary = repo / D6_MANIFEST.parent / "summary.csv"
    summary.write_text("corrupted\n", encoding="utf-8")
    run_context = context(tmp_path / "workspace", frozenset({"replay.read"}))

    result = build_default_engine(repo).run(replay_spec(), run_context)

    assert result.status == "FAILED"
    assert (
        result.record["nodes"]["observe"]["reason"]
        == "artifact_input_resolution_failed"
    )
    assert "checksum mismatch" in result.record["nodes"]["observe"]["error"]
    stored = RunRegistry(run_context.workspace).load(result.run_id)
    assert stored is not None and stored["status"] == "FAILED"


def test_registry_cannot_route_adapter_to_private_experiment_path(
    tmp_path: Path,
) -> None:
    repo = fixture_repo(tmp_path)
    registry_path = repo / "configs/tw_product_artifact_registry.yaml"
    registry = registry_path.read_text(encoding="utf-8").replace(
        str(D7_MANIFEST), "data_tw/experiments/private/replay/manifest.json"
    )
    registry_path.write_text(registry, encoding="utf-8")

    with pytest.raises(ArtifactError, match="outside the readonly product root"):
        ReadonlyReplayWindowAdapter(repo).query(model_id=MODEL_A)


def test_registry_safety_false_is_rejected(tmp_path: Path) -> None:
    repo = fixture_repo(tmp_path)
    registry_path = repo / "configs/tw_product_artifact_registry.yaml"
    registry = registry_path.read_text(encoding="utf-8").replace(
        "no_provider_publish: true", "no_provider_publish: false"
    )
    registry_path.write_text(registry, encoding="utf-8")

    with pytest.raises(ArtifactError, match="registry safety contract"):
        ReadonlyReplayWindowAdapter(repo).query(model_id=MODEL_A)


@pytest.mark.parametrize(
    ("field", "integer_value"),
    [("readonly_only", 1), ("production_trade_enabled", 0)],
)
def test_manifest_safety_rejects_integer_boolean_aliases(
    tmp_path: Path, field: str, integer_value: int
) -> None:
    repo = fixture_repo(tmp_path)
    manifest_path = repo / D6_MANIFEST
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest[field] = integer_value
    write_json(manifest_path, manifest)
    refresh_declared_checksum(
        repo, D6_MANIFEST.parent / "checksum_manifest.json", D6_MANIFEST
    )
    refresh_declared_checksum(repo, D7_CHECKSUM, D6_MANIFEST)

    with pytest.raises(ArtifactError, match=f"safety mismatch: {field}"):
        ReadonlyReplayWindowAdapter(repo).query(model_id=MODEL_A)


def test_narrow_observation_cannot_self_admit_full_replay_contract(
    tmp_path: Path,
) -> None:
    repo = fixture_repo(tmp_path)
    manifest_path = repo / D6_MANIFEST
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["not_copied_from_legacy_replay"] = True
    manifest["replay_window_policy_validation"]["model_training_windows_traceable"] = (
        True
    )
    manifest["order_intent_artifacts"] = [
        "data_tw/artifacts/readonly_replay_windows/nonexistent-order-intent.json"
    ]
    manifest["generated_by"] = "untrusted_full_contract_claim"
    write_json(manifest_path, manifest)
    refresh_declared_checksum(
        repo, D6_MANIFEST.parent / "checksum_manifest.json", D6_MANIFEST
    )
    refresh_declared_checksum(repo, D7_CHECKSUM, D6_MANIFEST)

    refs = ReadonlyReplayWindowAdapter(repo).query(model_id=MODEL_A)

    assert len(refs) == 1
    assert refs[0].metadata["full_replay_contract_status"] == "HOLD"
    assert refs[0].metadata["full_replay_contract_gaps"] == []

    result = build_default_engine(repo).run(
        replay_spec(), context(tmp_path / "workspace", frozenset({"replay.read"}))
    )
    output = result.record["nodes"]["observe"]["output"]
    assert output["full_replay_contract_admission"] is False


def test_validation_report_symlink_escape_is_rejected_before_read(
    tmp_path: Path,
) -> None:
    repo = fixture_repo(tmp_path)
    validation = repo / D6_MANIFEST.parent / "validation_report.json"
    outside = tmp_path / "outside-validation.json"
    outside.write_text(validation.read_text(encoding="utf-8"), encoding="utf-8")
    validation.unlink()
    validation.symlink_to(outside)

    with pytest.raises(ArtifactError, match="outside the readonly product root"):
        ReadonlyReplayWindowAdapter(repo).query(model_id=MODEL_A)


@pytest.mark.parametrize("location", ["index", "entry"])
def test_next_open_is_required_at_index_and_entry(
    tmp_path: Path, location: str
) -> None:
    repo = fixture_repo(tmp_path)
    manifest_path = repo / D7_MANIFEST
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if location == "index":
        manifest["execution_price_mode"] = "next_close"
    else:
        manifest["windows"][0]["execution_price_mode"] = "next_close"
    write_json(manifest_path, manifest)
    refresh_declared_checksum(repo, D7_CHECKSUM, D7_MANIFEST)

    with pytest.raises(ArtifactError, match="execution mode"):
        ReadonlyReplayWindowAdapter(repo).query(model_id=MODEL_A)


def test_duplicate_window_identity_is_rejected(tmp_path: Path) -> None:
    repo = fixture_repo(tmp_path)
    manifest_path = repo / D7_MANIFEST
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["windows"].append(dict(manifest["windows"][0]))
    write_json(manifest_path, manifest)
    refresh_declared_checksum(repo, D7_CHECKSUM, D7_MANIFEST)

    with pytest.raises(
        ArtifactError, match="duplicate readonly replay window identity"
    ):
        ReadonlyReplayWindowAdapter(repo).query(model_id=MODEL_A)


def test_adapter_projection_matches_existing_readonly_index_loader(monkeypatch) -> None:
    module_path = ROOT / "backend/app/services/readonly_replay_window_index.py"
    module_spec = importlib.util.spec_from_file_location(
        "wf1_fixture_readonly_replay_window_index", module_path
    )
    assert module_spec is not None and module_spec.loader is not None
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    monkeypatch.setattr(module, "ROOT", FIXTURE_SOURCE)
    monkeypatch.setattr(
        module,
        "INDEX_ROOT",
        FIXTURE_SOURCE / "data_tw/artifacts/readonly_replay_windows/d7",
    )
    monkeypatch.setattr(
        module,
        "LATEST_PATH",
        FIXTURE_SOURCE / "data_tw/artifacts/readonly_replay_windows/d7/latest.json",
    )
    monkeypatch.setattr(
        module, "POLICY", FIXTURE_SOURCE / "configs/tw_replay_window_policy.yaml"
    )

    existing = module.load_readonly_replay_window_index()
    refs = ReadonlyReplayWindowAdapter(FIXTURE_SOURCE).query(model_id=MODEL_A)

    assert len(existing["windows"]) == len(refs) == 1
    window = existing["windows"][0]
    ref = refs[0]
    assert (
        window["model_id"],
        window["strategy_rule"],
        window["start"],
        window["end"],
        window["artifact_manifest"],
    ) == (
        ref.model_id,
        ref.metadata["strategy_rule"],
        ref.metadata["window_start"],
        ref.metadata["window_end"],
        ref.manifest_path,
    )
    assert window["checksum"]["ok"] is True
    assert existing["sources"]["manifest"] == ref.metadata["index_manifest_path"]


def test_current_repository_readonly_index_is_observable_without_recompute() -> None:
    refs = ReadonlyReplayWindowAdapter(ROOT).query(
        model_id=MODEL_A,
        strategy_rule=STRATEGY,
        window_start="2026-01-01",
        window_end="2026-05-07",
    )
    assert len(refs) == 1
    assert refs[0].metadata["full_replay_contract_status"] == "HOLD"


def test_existing_cli_runs_replay_observation_without_business_script(
    tmp_path: Path,
) -> None:
    command = [
        sys.executable,
        str(ROOT / "scripts/run_tw_stock_workflow.py"),
        "--repo-root",
        str(FIXTURE_SOURCE),
        "--spec",
        str(ROOT / "configs/workflows/replay_window_observation.yaml"),
        "--mode",
        "readonly",
        "--asof",
        "2026-05-07",
        "--decision-cutoff",
        "2026-05-07T13:30:00+08:00",
        "--permission",
        "replay.read",
        "--workspace",
        str(tmp_path / "workspace"),
    ]
    completed = subprocess.run(
        command,
        cwd=ROOT,
        env={**os.environ, "PYTHONPATH": str(ROOT)},
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["status"] == "SUCCEEDED"
    output = payload["nodes"]["observe_model_a_replay_window"]["output"]
    assert output["observation_kind"] == "READONLY_REPLAY_WINDOW_INDEX"
    assert output["full_replay_contract_admission"] is False
