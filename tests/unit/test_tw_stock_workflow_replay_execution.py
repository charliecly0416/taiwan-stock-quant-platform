from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Callable

import pytest

from tw_stock_workflow.artifacts import ArtifactError, ArtifactRef, ArtifactResolver
from tw_stock_workflow.engine import WorkflowEngine
from tw_stock_workflow.modules import ModuleRegistry
from tw_stock_workflow.replay_execution import (
    MODEL_A,
    STRATEGY,
    WINDOW_END,
    WINDOW_START,
    ReplayCandidateExecution,
    ReplayCandidateInputAdapter,
    _execution_implementation_digest,
)
from tw_stock_workflow.spec import WorkflowSpec
from tw_stock_workflow.types import ExecutionContext, WorkflowError


ROOT = Path(__file__).resolve().parents[2]
RUN_ID = "wf2a_0123456789abcdef01234567"
IDENTITY = "a" * 64


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )


class FixtureInputAdapter:
    adapter_id = "fixture.wf2b.input"

    def __init__(self, repo: Path) -> None:
        self.repo = repo
        self.manifest = repo / "inputs/source/manifest.json"
        self.implementation_sha256 = "1" * 64
        write_json(self.manifest, {"revision": 1})

    def resolve(self) -> ArtifactRef:
        implementation_files = [
            {
                "path": "fixture/replay_execution.py",
                "sha256": self.implementation_sha256,
                "bytes": 100,
            }
        ]
        return ArtifactRef(
            adapter_id=self.adapter_id,
            artifact_type="replay_result",
            model_id=MODEL_A,
            asof=WINDOW_END,
            status="CANDIDATE_HOLD",
            run_id=RUN_ID,
            path="inputs/source",
            manifest_path="inputs/source/manifest.json",
            manifest_sha256=sha256(self.manifest),
            metadata={
                "input_identity_sha256": IDENTITY,
                "builder_inputs": {
                    "baseline_manifest": "inputs/baseline.json",
                    "replay_window_policy": "inputs/policy.yaml",
                    "model_registry": "inputs/registry.yaml",
                    "baseline_descriptor": "inputs/baseline_descriptor.yaml",
                    "canonical_price_store_manifest": "inputs/prices.json",
                },
                "execution_implementation_files": implementation_files,
                "execution_implementation_sha256": (
                    _execution_implementation_digest(implementation_files)
                ),
            },
        )

    def implementation_digest(self) -> str:
        return self.resolve().metadata["execution_implementation_sha256"]


class FixtureBuilder:
    def __init__(self, *, mutation: Callable[[], None] | None = None) -> None:
        self.calls = 0
        self.mutation = mutation

    def __call__(self, **kwargs: Any) -> dict[str, Any]:
        self.calls += 1
        manifest = (
            Path(kwargs["out_root"])
            / MODEL_A
            / STRATEGY
            / "20260101_20260507"
            / RUN_ID
            / "order_intent_replay_result/manifest.json"
        )
        write_json(
            manifest,
            {
                "artifact_type": "replay_result",
                "run_id": RUN_ID,
                "identity_sha256": IDENTITY,
                "status": "CANDIDATE_HOLD",
                "product_index_admission": False,
                "model_id": MODEL_A,
                "strategy_rule": STRATEGY,
                "window_start": WINDOW_START,
                "window_end": WINDOW_END,
            },
        )
        if self.mutation is not None:
            self.mutation()
        return {"manifest": str(manifest)}


def config(**updates: Any) -> dict[str, Any]:
    value = {
        "model_id": MODEL_A,
        "strategy_rule": STRATEGY,
        "window_start": WINDOW_START,
        "window_end": WINDOW_END,
    }
    value.update(updates)
    return value


def workflow(*, policy: str = "required", **updates: Any) -> WorkflowSpec:
    return WorkflowSpec.from_mapping(
        {
            "schema_version": "tw.workflow.spec.v1",
            "workflow_id": "test.wf2b_replay_candidate",
            "version": "1",
            "nodes": [
                {
                    "id": "candidate",
                    "module": "replay_candidate.build_validate",
                    "policy": policy,
                    "config": config(**updates),
                }
            ],
        }
    )


def context(
    workspace: Path,
    permissions: frozenset[str] = frozenset(
        {"artifact.read", "replay.candidate.write"}
    ),
    *,
    decision_cutoff: str = "2026-05-07T13:30:00+08:00",
) -> ExecutionContext:
    return ExecutionContext(
        mode="replay",
        asof=WINDOW_END,
        decision_cutoff=decision_cutoff,
        workspace=workspace,
        permissions=permissions,
    )


def engine(
    repo: Path,
    adapter: FixtureInputAdapter,
    builder: FixtureBuilder,
    *,
    validator_ok: bool = True,
) -> WorkflowEngine:
    registry = ModuleRegistry()
    registry.register(
        ReplayCandidateExecution(
            repo,
            input_adapter=adapter,
            builder=builder,
            validator=lambda _path: {"ok": validator_ok},
        )
    )
    return WorkflowEngine(registry, ArtifactResolver(repo))


def test_required_module_builds_validated_hold_candidate(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    adapter = FixtureInputAdapter(repo)
    builder = FixtureBuilder()
    result = engine(repo, adapter, builder).run(
        workflow(), context(tmp_path / "workspace")
    )

    assert result.status == "SUCCEEDED"
    output = result.record["nodes"]["candidate"]["output"]
    assert output["status"] == "CANDIDATE_HOLD"
    assert output["product_index_admission"] is False
    assert output["model_id"] == MODEL_A
    assert output["reused_candidate"] is False
    assert (tmp_path / "workspace" / output["manifest"]).is_file()
    assert builder.calls == 1


def test_missing_permissions_blocks_without_resolving_or_building(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    adapter = FixtureInputAdapter(repo)
    builder = FixtureBuilder()
    result = engine(repo, adapter, builder).run(
        workflow(), context(tmp_path / "workspace", frozenset())
    )

    assert result.status == "BLOCKED"
    node = result.record["nodes"]["candidate"]
    assert node["missing_permissions"] == [
        "artifact.read",
        "replay.candidate.write",
    ]
    assert builder.calls == 0


@pytest.mark.parametrize(
    "override",
    [
        {"model_id": "modelb_b19r2r_lambdarank_exact50_78f_v2"},
        {"strategy_rule": "top50_exit_all"},
        {"window_start": "2026-01-02"},
        {"window_end": "2026-05-06"},
        {"output_root": "/tmp/escape"},
    ],
)
def test_identity_or_output_override_fails_closed(
    tmp_path: Path, override: dict[str, str]
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    adapter = FixtureInputAdapter(repo)
    builder = FixtureBuilder()
    result = engine(repo, adapter, builder).run(
        workflow(**override), context(tmp_path / "workspace")
    )

    assert result.status == "FAILED"
    assert result.record["nodes"]["candidate"]["reason"] == (
        "artifact_input_resolution_failed"
    )
    assert builder.calls == 0


def test_workspace_symlink_escape_to_protected_product_path_is_rejected(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    protected = repo / "data_tw/artifacts/readonly_replay_windows/d6"
    protected.mkdir(parents=True)
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "artifacts").symlink_to(protected, target_is_directory=True)
    adapter = FixtureInputAdapter(repo)
    builder = FixtureBuilder()
    result = engine(repo, adapter, builder).run(workflow(), context(workspace))

    assert result.status == "FAILED"
    assert "escapes workspace" in result.record["nodes"]["candidate"]["error"]
    assert builder.calls == 0


def test_nested_output_symlink_escape_is_rejected_before_builder(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    protected = repo / "data_tw/artifacts/readonly_replay_windows/d6"
    protected.mkdir(parents=True)
    workspace = tmp_path / "workspace"
    nested = workspace / "artifacts/wf2b_model_a_replay_candidate"
    nested.mkdir(parents=True)
    adapter = FixtureInputAdapter(repo)
    implementation_root = nested / f"implementation_{adapter.implementation_digest()}"
    implementation_root.mkdir()
    (implementation_root / MODEL_A).symlink_to(protected, target_is_directory=True)
    builder = FixtureBuilder()

    result = engine(repo, adapter, builder).run(workflow(), context(workspace))

    assert result.status == "FAILED"
    assert "escapes workspace" in result.record["nodes"]["candidate"]["error"]
    assert builder.calls == 0


def test_workspace_inside_repository_is_rejected(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    adapter = FixtureInputAdapter(repo)
    builder = FixtureBuilder()
    result = engine(repo, adapter, builder).run(
        workflow(), context(repo / "data_tw/artifacts/readonly_replay_windows/d6")
    )

    assert result.status == "FAILED"
    assert "outside repository" in result.record["nodes"]["candidate"]["error"]
    assert builder.calls == 0


def test_complete_validator_failure_is_required_failure_and_nonblocking_isolated(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    adapter = FixtureInputAdapter(repo)
    required = engine(repo, adapter, FixtureBuilder(), validator_ok=False).run(
        workflow(), context(tmp_path / "required-workspace")
    )
    shadow = engine(repo, adapter, FixtureBuilder(), validator_ok=False).run(
        workflow(policy="nonblocking"), context(tmp_path / "shadow-workspace")
    )

    assert required.status == "FAILED"
    assert required.record["nodes"]["candidate"]["status"] == "FAILED"
    assert shadow.status == "SUCCEEDED"
    assert shadow.record["nodes"]["candidate"]["status"] == "FAILED"


def test_input_mutation_during_build_is_detected_by_kernel_toctou(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    adapter = FixtureInputAdapter(repo)

    def mutate() -> None:
        write_json(adapter.manifest, {"revision": 2})

    builder = FixtureBuilder(mutation=mutate)
    result = engine(repo, adapter, builder).run(
        workflow(), context(tmp_path / "workspace")
    )

    assert result.status == "FAILED"
    node = result.record["nodes"]["candidate"]
    assert node["error_type"] == "WorkflowError"
    assert "changed during module execution" in node["error"]


def test_same_identity_reuses_run_and_does_not_rebuild(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    adapter = FixtureInputAdapter(repo)
    builder = FixtureBuilder()
    service = engine(repo, adapter, builder)
    run_context = context(tmp_path / "workspace")

    first = service.run(workflow(), run_context)
    second = service.run(workflow(), run_context)

    assert first.status == "SUCCEEDED"
    assert second.idempotent_reuse is True
    assert first.run_id == second.run_id
    assert builder.calls == 1


def test_terminal_success_with_deleted_manifest_fails_cached_revalidation(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    adapter = FixtureInputAdapter(repo)
    builder = FixtureBuilder()
    service = engine(repo, adapter, builder)
    run_context = context(tmp_path / "workspace")
    first = service.run(workflow(), run_context)
    output = first.record["nodes"]["candidate"]["output"]
    manifest = run_context.workspace / output["manifest"]
    manifest.unlink()

    with pytest.raises(WorkflowError, match="cached output validation failed.*missing"):
        service.run(workflow(), run_context)

    assert builder.calls == 1
    assert not manifest.exists()


def test_terminal_success_with_tampered_manifest_fails_cached_revalidation(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    adapter = FixtureInputAdapter(repo)
    builder = FixtureBuilder()
    service = engine(repo, adapter, builder)
    run_context = context(tmp_path / "workspace")
    first = service.run(workflow(), run_context)
    output = first.record["nodes"]["candidate"]["output"]
    manifest = run_context.workspace / output["manifest"]
    write_json(manifest, {"tampered": True})

    with pytest.raises(
        WorkflowError, match="cached output validation failed.*identity"
    ):
        service.run(workflow(), run_context)

    assert builder.calls == 1
    assert json.loads(manifest.read_text(encoding="utf-8")) == {"tampered": True}


def test_same_implementation_reuses_valid_candidate_for_new_run(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    adapter = FixtureInputAdapter(repo)
    builder = FixtureBuilder()
    service = engine(repo, adapter, builder)
    workspace = tmp_path / "workspace"

    first = service.run(workflow(), context(workspace))
    second = service.run(
        workflow(),
        context(
            workspace,
            decision_cutoff="2026-05-07T13:31:00+08:00",
        ),
    )

    first_output = first.record["nodes"]["candidate"]["output"]
    second_output = second.record["nodes"]["candidate"]["output"]
    assert first.status == "SUCCEEDED"
    assert second.status == "SUCCEEDED"
    assert first.run_id != second.run_id
    assert second.idempotent_reuse is False
    assert first_output["manifest"] == second_output["manifest"]
    assert second_output["reused_candidate"] is True
    assert builder.calls == 1


def test_changed_implementation_hash_builds_isolated_candidate(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    adapter = FixtureInputAdapter(repo)
    builder = FixtureBuilder()
    service = engine(repo, adapter, builder)
    workspace = tmp_path / "workspace"

    first = service.run(workflow(), context(workspace))
    first_output = first.record["nodes"]["candidate"]["output"]
    adapter.implementation_sha256 = "2" * 64
    second = service.run(workflow(), context(workspace))
    second_output = second.record["nodes"]["candidate"]["output"]

    assert first.status == "SUCCEEDED"
    assert second.status == "SUCCEEDED"
    assert first.run_id != second.run_id
    assert second.idempotent_reuse is False
    assert (
        first_output["execution_implementation_sha256"]
        != (second_output["execution_implementation_sha256"])
    )
    assert first_output["manifest"] != second_output["manifest"]
    assert second_output["reused_candidate"] is False
    assert (workspace / first_output["manifest"]).is_file()
    assert (workspace / second_output["manifest"]).is_file()
    assert builder.calls == 2


def test_existing_invalid_candidate_is_not_reused(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    adapter = FixtureInputAdapter(repo)
    builder = FixtureBuilder()
    workspace = tmp_path / "workspace"
    expected = (
        workspace
        / "artifacts/wf2b_model_a_replay_candidate"
        / f"implementation_{adapter.implementation_digest()}"
        / MODEL_A
        / STRATEGY
        / "20260101_20260507"
        / RUN_ID
        / "order_intent_replay_result/manifest.json"
    )
    write_json(expected, {"tampered": True})

    result = engine(repo, adapter, builder, validator_ok=False).run(
        workflow(), context(workspace)
    )

    assert result.status == "FAILED"
    assert "complete validator" in result.record["nodes"]["candidate"]["error"]
    assert builder.calls == 0


def test_execution_does_not_change_product_pointers(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    pointers = [
        repo / "data_tw/artifacts/readonly_replay_windows/d7/latest.json",
        repo / "data_tw/artifacts/readonly_replay_windows/d6/manifest.json",
        repo / "data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/latest.json",
    ]
    for index, pointer in enumerate(pointers):
        write_json(pointer, {"sentinel": index})
    before = {path: sha256(path) for path in pointers}
    adapter = FixtureInputAdapter(repo)

    result = engine(repo, adapter, FixtureBuilder()).run(
        workflow(), context(tmp_path / "workspace")
    )

    assert result.status == "SUCCEEDED"
    assert {path: sha256(path) for path in pointers} == before


def test_committed_wf2b_spec_is_required_and_model_a_only() -> None:
    spec = WorkflowSpec.load(
        ROOT / "configs/workflows/model_a_replay_candidate_execution.yaml"
    )
    assert len(spec.nodes) == 1
    node = spec.nodes[0]
    assert node.module == "replay_candidate.build_validate"
    assert node.policy == "required"
    assert node.config == config()


def test_real_wf2a_candidate_binds_complete_wf2b_input_closure() -> None:
    source = ROOT / (
        "data_tw/artifacts/readonly_replay_windows/wf2_candidate_model_a_v4/"
        "e4_frozen_qlib_2018_2022/top50_exit_one_worst_sell/"
        "20260101_20260507/wf2a_a1dd7d213f1913c9e53e90de/"
        "order_intent_replay_result/manifest.json"
    )
    if not source.is_file():
        pytest.skip("local WF-2A candidate is not present in a fresh checkout")

    try:
        ref = ReplayCandidateInputAdapter(ROOT).resolve()
    except ArtifactError as exc:
        pytest.skip(f"local optional WF-2A candidate is stale or invalid: {exc}")
    bound = {row["path"] for row in ref.metadata["bound_files"]}

    assert ref.model_id == MODEL_A
    assert ref.status == "CANDIDATE_HOLD"
    assert len(bound) == 39
    assert ref.metadata["binding_kind"] == "WF2A_COMPLETE_REPLAY_INPUT_CLOSURE"
    implementations = {
        (row["path"], row["sha256"])
        for row in ref.metadata["execution_implementation_files"]
    }
    assert implementations == {
        (
            "tw_stock_workflow/replay_execution.py",
            sha256(ROOT / "tw_stock_workflow/replay_execution.py"),
        ),
        (
            "scripts/build_tw_readonly_replay_window_artifact.py",
            sha256(ROOT / "scripts/build_tw_readonly_replay_window_artifact.py"),
        ),
        (
            "scripts/validate_tw_readonly_replay_window_artifact.py",
            sha256(ROOT / "scripts/validate_tw_readonly_replay_window_artifact.py"),
        ),
        (
            "scripts/run_tw_modular_order_intent_replay_parity.py",
            sha256(ROOT / "scripts/run_tw_modular_order_intent_replay_parity.py"),
        ),
    }
    assert ref.metadata["execution_implementation_sha256"] == (
        _execution_implementation_digest(ref.metadata["execution_implementation_files"])
    )
    assert {
        "configs/active_baseline_descriptor.yaml",
        "configs/tw_modular_registry.yaml",
        "configs/tw_replay_window_policy.yaml",
        "data_tw/canonical/price_store/tw_equity_daily/"
        "dng2_r_price_market_calendar_20260625/manifest.json",
        "data_tw/canonical/price_store/tw_equity_daily/"
        "dng2_r_price_market_calendar_20260625/prices.csv",
        "data_tw/experiments/extended_oos_qlib_orthogonal_ltr/"
        "phase_e1_frozen_qlib_training_and_oos_score/phasee1_training_manifest.json",
    }.issubset(bound)
    assert all("modelb_b19r2r" not in path for path in bound)
