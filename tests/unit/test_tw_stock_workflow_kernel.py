from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from tw_stock_workflow.artifacts import (
    ArtifactError,
    ArtifactResolver,
    ResearchHistoryAdapter,
)
from tw_stock_workflow.engine import StageResult, WorkflowEngine
from tw_stock_workflow.modules import (
    ModuleBlocked,
    ModuleRegistry,
    ResearchHistoryObservation,
)
from tw_stock_workflow.run_registry import RunRegistry, RunRegistryError
from tw_stock_workflow.spec import WorkflowSpec, WorkflowSpecError
from tw_stock_workflow.types import ExecutionContext, WorkflowError


MODEL_A = "e4_frozen_qlib_2018_2022"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")


def make_history(
    repo: Path, *, asof: str = "2026-09-18", run_id: str = "run-1"
) -> Path:
    slots: dict[str, dict[str, Any]] = {}
    for slot, artifact_type in (
        ("inference_input", "ModelInferenceInput"),
        ("signal", "ModelSignalArtifact"),
    ):
        artifact_dir = repo / "artifacts" / slot / run_id
        manifest = {
            "artifact_type": artifact_type,
            "model_id": MODEL_A,
            "asof": asof,
            "status": "READY",
            "run_id": run_id,
        }
        write_json(artifact_dir / "manifest.json", manifest)
        slots[slot] = {
            "artifact_type": artifact_type,
            "path": str(artifact_dir.relative_to(repo)),
            "run_id": run_id,
            "files": {
                "manifest.json": {
                    "path": str((artifact_dir / "manifest.json").relative_to(repo)),
                    "sha256": sha256(artifact_dir / "manifest.json"),
                }
            },
        }
    index_path = repo / "history/index.json"
    write_json(
        index_path,
        {
            "schema_version": "tw.research_data_history.index.v1",
            "days": {
                asof: {
                    "asof": asof,
                    "status": "READY_MODELA_ONLY",
                    "model_a": {
                        "model_id": MODEL_A,
                        "asof": asof,
                        "status": "READY",
                        **slots,
                    },
                    "model_b": None,
                }
            },
        },
    )
    return index_path


def context(
    workspace: Path, *, permissions: frozenset[str] = frozenset({"artifact.read"})
) -> ExecutionContext:
    return ExecutionContext(
        mode="readonly",
        asof="2026-09-18",
        decision_cutoff="2026-09-18T10:30:00+00:00",
        workspace=workspace,
        permissions=permissions,
    )


def spec(nodes: list[dict[str, Any]]) -> WorkflowSpec:
    return WorkflowSpec.from_mapping(
        {
            "schema_version": "tw.workflow.spec.v1",
            "workflow_id": "test.workflow",
            "version": "1",
            "nodes": nodes,
        }
    )


@dataclass
class RecordingModule:
    module_id: str
    calls: list[str]
    required_permissions: frozenset[str] = frozenset()
    outcome: str = "success"

    def resolve_artifact_inputs(self, context, config, resolver):
        return []

    def execute(self, context, config, inputs, resolver):
        self.calls.append(str(config.get("name") or self.module_id))
        if self.outcome == "blocked":
            raise ModuleBlocked("fixture blocked")
        if self.outcome == "failed":
            raise ValueError("fixture failed")
        return {"name": config.get("name"), "inputs": sorted(inputs)}


@dataclass
class ManifestTamperingModule:
    manifest_path: Path
    module_id: str = "fixture.tamper"
    required_permissions: frozenset[str] = frozenset({"artifact.read"})

    def resolve_artifact_inputs(self, context, config, resolver):
        return resolver.query(
            artifact_type="ModelSignalArtifact",
            model_id=MODEL_A,
            asof=context.asof,
            status="READY",
        )

    def execute(self, context, config, inputs, resolver):
        self.manifest_path.write_text("{}\n", encoding="utf-8")
        return {"ordinary_result": True}


@dataclass
class CacheValidatingModule:
    module_id: str
    execute_calls: list[str]
    validation_calls: list[dict[str, Any]]
    required_permissions: frozenset[str] = frozenset()
    outcome: str = "success"
    cached_output_valid: bool = True

    def resolve_artifact_inputs(self, context, config, resolver):
        return []

    def execute(self, context, config, inputs, resolver):
        self.execute_calls.append(self.module_id)
        if self.outcome == "blocked":
            raise ModuleBlocked("fixture blocked")
        if self.outcome == "failed":
            raise ValueError("fixture failed")
        return {"artifact": "fixture.json"}

    def validate_cached_output(self, context, config, output, resolver):
        self.validation_calls.append(dict(output))
        if not self.cached_output_valid:
            raise WorkflowError("fixture cached output is invalid")


def engine_for(repo: Path, *modules: RecordingModule) -> WorkflowEngine:
    registry = ModuleRegistry()
    for module in modules:
        registry.register(module)
    return WorkflowEngine(registry, ArtifactResolver(repo))


def test_dag_has_stable_topological_execution_order(tmp_path: Path) -> None:
    calls: list[str] = []
    engine = engine_for(tmp_path, RecordingModule("fixture.ok", calls))
    workflow = spec(
        [
            {
                "id": "last",
                "module": "fixture.ok",
                "needs": ["first"],
                "policy": "required",
                "config": {"name": "last"},
            },
            {
                "id": "first",
                "module": "fixture.ok",
                "policy": "required",
                "config": {"name": "first"},
            },
            {
                "id": "side",
                "module": "fixture.ok",
                "policy": "required",
                "config": {"name": "side"},
            },
        ]
    )

    result = engine.run(workflow, context(tmp_path / "workspace"))

    assert result.status == "SUCCEEDED"
    assert calls == ["first", "last", "side"]


def test_terminal_success_calls_cached_output_validator_before_reuse(
    tmp_path: Path,
) -> None:
    execute_calls: list[str] = []
    validation_calls: list[dict[str, Any]] = []
    module = CacheValidatingModule("fixture.cached", execute_calls, validation_calls)
    service = engine_for(tmp_path, module)
    workflow = spec(
        [{"id": "cached", "module": "fixture.cached", "policy": "required"}]
    )
    run_context = context(tmp_path / "workspace")

    first = service.run(workflow, run_context)
    second = service.run(workflow, run_context)

    assert first.status == "SUCCEEDED"
    assert second.idempotent_reuse is True
    assert execute_calls == ["fixture.cached"]
    assert validation_calls == [{"artifact": "fixture.json"}]


def test_terminal_success_cached_output_validator_fails_closed(
    tmp_path: Path,
) -> None:
    module = CacheValidatingModule("fixture.cached", [], [], cached_output_valid=False)
    service = engine_for(tmp_path, module)
    workflow = spec(
        [{"id": "cached", "module": "fixture.cached", "policy": "required"}]
    )
    run_context = context(tmp_path / "workspace")
    first = service.run(workflow, run_context)

    with pytest.raises(
        WorkflowError, match="cached output validation failed.*fixture cached output"
    ):
        service.run(workflow, run_context)

    assert first.status == "SUCCEEDED"
    assert len(module.validation_calls) == 1


@pytest.mark.parametrize("outcome", ["blocked", "failed"])
def test_non_success_terminal_reuse_does_not_validate_cached_output(
    tmp_path: Path, outcome: str
) -> None:
    module = CacheValidatingModule("fixture.cached", [], [], outcome=outcome)
    service = engine_for(tmp_path, module)
    workflow = spec(
        [{"id": "cached", "module": "fixture.cached", "policy": "required"}]
    )
    run_context = context(tmp_path / "workspace")

    first = service.run(workflow, run_context)
    second = service.run(workflow, run_context)

    assert first.status == ("BLOCKED" if outcome == "blocked" else "FAILED")
    assert second.idempotent_reuse is True
    assert module.validation_calls == []


@pytest.mark.parametrize(
    "nodes,match",
    [
        (
            [
                {"id": "same", "module": "fixture.ok", "policy": "required"},
                {"id": "same", "module": "fixture.ok", "policy": "required"},
            ],
            "duplicate workflow node",
        ),
        (
            [
                {
                    "id": "one",
                    "module": "fixture.ok",
                    "needs": ["missing"],
                    "policy": "required",
                }
            ],
            "unknown dependencies",
        ),
        (
            [
                {
                    "id": "one",
                    "module": "fixture.ok",
                    "needs": ["two"],
                    "policy": "required",
                },
                {
                    "id": "two",
                    "module": "fixture.ok",
                    "needs": ["one"],
                    "policy": "required",
                },
            ],
            "cycle",
        ),
    ],
)
def test_invalid_dag_is_rejected(nodes: list[dict[str, Any]], match: str) -> None:
    with pytest.raises(WorkflowSpecError, match=match):
        spec(nodes)


@pytest.mark.parametrize(
    "mutation,match",
    [
        ({"version": 1}, "invalid workflow_id or version"),
        ({"unexpected": True}, "unknown workflow fields"),
    ],
)
def test_spec_runtime_rejects_schema_type_and_unknown_field(
    mutation: dict[str, Any], match: str
) -> None:
    payload: dict[str, Any] = {
        "schema_version": "tw.workflow.spec.v1",
        "workflow_id": "test.workflow",
        "version": "1",
        "nodes": [{"id": "one", "module": "fixture.ok", "policy": "required"}],
    }
    payload.update(mutation)
    with pytest.raises(WorkflowSpecError, match=match):
        WorkflowSpec.from_mapping(payload)

    payload = {
        "schema_version": "tw.workflow.spec.v1",
        "workflow_id": "test.workflow",
        "version": "1",
        "nodes": [
            {
                "id": "one",
                "module": "fixture.ok",
                "policy": "required",
                "import_target": "os.system",
            }
        ],
    }
    with pytest.raises(WorkflowSpecError, match="unknown node fields"):
        WorkflowSpec.from_mapping(payload)


def test_unknown_module_is_rejected_without_dynamic_import(tmp_path: Path) -> None:
    workflow = spec([{"id": "one", "module": "os.system", "policy": "required"}])
    with pytest.raises(WorkflowError, match="unknown workflow module"):
        engine_for(tmp_path).run(workflow, context(tmp_path / "workspace"))


def test_permission_denial_blocks_required_node(tmp_path: Path) -> None:
    module = RecordingModule("fixture.read", [], frozenset({"artifact.read"}))
    workflow = spec([{"id": "read", "module": "fixture.read", "policy": "required"}])

    result = engine_for(tmp_path, module).run(
        workflow,
        context(tmp_path / "workspace", permissions=frozenset()),
    )

    assert result.status == "BLOCKED"
    assert result.record["nodes"]["read"]["reason"] == "permission_denied"
    assert module.calls == []


def test_optional_failure_isolated_and_dependency_is_skipped(tmp_path: Path) -> None:
    calls: list[str] = []
    workflow = spec(
        [
            {"id": "optional", "module": "fixture.fail", "policy": "optional"},
            {
                "id": "child",
                "module": "fixture.ok",
                "needs": ["optional"],
                "policy": "optional",
            },
            {"id": "required", "module": "fixture.ok", "policy": "required"},
        ]
    )
    engine = engine_for(
        tmp_path,
        RecordingModule("fixture.fail", calls, outcome="failed"),
        RecordingModule("fixture.ok", calls),
    )

    result = engine.run(workflow, context(tmp_path / "workspace"))

    assert result.status == "SUCCEEDED"
    assert result.record["nodes"]["optional"]["status"] == "FAILED"
    assert result.record["nodes"]["child"]["status"] == "SKIPPED"
    assert result.record["nodes"]["required"]["status"] == "SUCCEEDED"


def test_nonblocking_failure_isolated_and_cannot_feed_required_node(
    tmp_path: Path,
) -> None:
    workflow = spec(
        [
            {"id": "shadow", "module": "fixture.fail", "policy": "nonblocking"},
            {"id": "main", "module": "fixture.ok", "policy": "required"},
        ]
    )
    engine = engine_for(
        tmp_path,
        RecordingModule("fixture.fail", [], outcome="failed"),
        RecordingModule("fixture.ok", []),
    )
    result = engine.run(workflow, context(tmp_path / "workspace"))
    assert result.status == "SUCCEEDED"
    assert result.record["nodes"]["shadow"]["status"] == "FAILED"

    with pytest.raises(WorkflowSpecError, match="required node cannot depend"):
        spec(
            [
                {"id": "shadow", "module": "fixture.fail", "policy": "nonblocking"},
                {
                    "id": "main",
                    "module": "fixture.ok",
                    "needs": ["shadow"],
                    "policy": "required",
                },
            ]
        )


def test_required_exception_fails_closed(tmp_path: Path) -> None:
    workflow = spec(
        [{"id": "required", "module": "fixture.fail", "policy": "required"}]
    )
    result = engine_for(
        tmp_path,
        RecordingModule("fixture.fail", [], outcome="failed"),
    ).run(workflow, context(tmp_path / "workspace"))

    assert result.status == "FAILED"
    assert result.record["nodes"]["required"]["error_type"] == "ValueError"
    stored = json.loads(
        (tmp_path / "workspace/runs" / f"{result.run_id}.json").read_text()
    )
    assert stored["status"] == "FAILED"


def test_engine_detects_input_drift_without_module_artifact_echo(
    tmp_path: Path,
) -> None:
    index_path = make_history(tmp_path)
    payload = json.loads(index_path.read_text(encoding="utf-8"))
    signal = payload["days"]["2026-09-18"]["model_a"]["signal"]
    manifest_path = tmp_path / signal["files"]["manifest.json"]["path"]
    resolver = ArtifactResolver(tmp_path)
    resolver.register(ResearchHistoryAdapter(tmp_path, index_path))
    registry = ModuleRegistry()
    registry.register(ManifestTamperingModule(manifest_path))
    workflow = spec(
        [{"id": "tamper", "module": "fixture.tamper", "policy": "required"}]
    )

    result = WorkflowEngine(registry, resolver).run(
        workflow, context(tmp_path / "workspace")
    )

    assert result.status == "FAILED"
    assert result.record["nodes"]["tamper"]["error_type"] == "ArtifactError"
    assert "checksum mismatch" in result.record["nodes"]["tamper"]["error"]
    stored = RunRegistry(tmp_path / "workspace").load(result.run_id)
    assert stored is not None
    assert stored["status"] == "FAILED"


def test_required_failure_propagates_through_multiple_skipped_nodes(
    tmp_path: Path,
) -> None:
    calls: list[str] = []
    workflow = spec(
        [
            {"id": "root", "module": "fixture.fail", "policy": "optional"},
            {
                "id": "middle",
                "module": "fixture.ok",
                "needs": ["root"],
                "policy": "optional",
            },
            {
                "id": "required_leaf",
                "module": "fixture.ok",
                "needs": ["middle"],
                "policy": "required",
            },
        ]
    )
    engine = engine_for(
        tmp_path,
        RecordingModule("fixture.fail", calls, outcome="failed"),
        RecordingModule("fixture.ok", calls),
    )

    result = engine.run(workflow, context(tmp_path / "workspace"))

    assert result.status == "FAILED"
    assert result.record["nodes"]["required_leaf"]["root_cause"] == "FAILED"


def test_artifact_query_filters_and_checks_manifest_sha(tmp_path: Path) -> None:
    index_path = make_history(tmp_path)
    resolver = ArtifactResolver(tmp_path)
    resolver.register(ResearchHistoryAdapter(tmp_path, index_path))

    refs = resolver.query(
        artifact_type="ModelSignalArtifact",
        model_id=MODEL_A,
        asof="2026-09-18",
        status="READY",
    )

    assert len(refs) == 1
    assert refs[0].run_id == "run-1"
    assert resolver.query(model_id="other") == []

    manifest = tmp_path / refs[0].manifest_path
    manifest.write_text("{}\n", encoding="utf-8")
    with pytest.raises(ArtifactError, match="checksum mismatch"):
        resolver.query(model_id=MODEL_A)


def test_manifest_identity_fields_are_required(tmp_path: Path) -> None:
    index_path = make_history(tmp_path)
    payload = json.loads(index_path.read_text(encoding="utf-8"))
    signal = payload["days"]["2026-09-18"]["model_a"]["signal"]
    manifest_path = tmp_path / signal["files"]["manifest.json"]["path"]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    del manifest["run_id"]
    write_json(manifest_path, manifest)
    signal["files"]["manifest.json"]["sha256"] = sha256(manifest_path)
    write_json(index_path, payload)
    resolver = ArtifactResolver(tmp_path)
    resolver.register(ResearchHistoryAdapter(tmp_path, index_path))

    with pytest.raises(ArtifactError, match="identity field missing for run_id"):
        resolver.query(artifact_type="ModelSignalArtifact")


def test_artifact_path_and_symlink_escape_are_rejected(tmp_path: Path) -> None:
    index_path = make_history(tmp_path)
    payload = json.loads(index_path.read_text(encoding="utf-8"))
    signal = payload["days"]["2026-09-18"]["model_a"]["signal"]
    signal["path"] = "../outside"
    write_json(index_path, payload)
    resolver = ArtifactResolver(tmp_path)
    resolver.register(ResearchHistoryAdapter(tmp_path, index_path))
    with pytest.raises(ArtifactError, match="escapes repository"):
        resolver.query(artifact_type="ModelSignalArtifact")

    outside = tmp_path.parent / f"{tmp_path.name}-outside"
    outside.mkdir()
    write_json(outside / "manifest.json", {"model_id": MODEL_A})
    link = tmp_path / "artifacts/symlink"
    link.parent.mkdir(parents=True, exist_ok=True)
    link.symlink_to(outside, target_is_directory=True)
    payload = json.loads(index_path.read_text(encoding="utf-8"))
    signal = payload["days"]["2026-09-18"]["model_a"]["signal"]
    signal["path"] = str(link.relative_to(tmp_path))
    signal["files"]["manifest.json"] = {
        "path": str((link / "manifest.json").relative_to(tmp_path)),
        "sha256": sha256(outside / "manifest.json"),
    }
    write_json(index_path, payload)
    with pytest.raises(ArtifactError, match="escapes repository"):
        resolver.query(artifact_type="ModelSignalArtifact")


def test_history_index_escape_and_symlink_escape_are_rejected(tmp_path: Path) -> None:
    outside = tmp_path.parent / f"{tmp_path.name}-private-index.json"
    write_json(
        outside, {"schema_version": "tw.research_data_history.index.v1", "days": {}}
    )
    with pytest.raises(ArtifactError, match="index escapes repository"):
        ResearchHistoryAdapter(tmp_path, outside)

    link = tmp_path / "history-link.json"
    link.symlink_to(outside)
    with pytest.raises(ArtifactError, match="index escapes repository"):
        ResearchHistoryAdapter(tmp_path, link)


def test_identical_run_is_reused_without_executing_module(tmp_path: Path) -> None:
    calls: list[str] = []
    engine = engine_for(tmp_path, RecordingModule("fixture.ok", calls))
    workflow = spec([{"id": "one", "module": "fixture.ok", "policy": "required"}])
    run_context = context(tmp_path / "workspace")

    first = engine.run(workflow, run_context)
    second = engine.run(workflow, run_context)

    assert first.run_id == second.run_id
    assert second.idempotent_reuse is True
    assert calls == ["fixture.ok"]
    assert first.record == second.record


@pytest.mark.parametrize(
    "run_id",
    [
        "../escape",
        "wf_0123456789abcdef0123456/",
        "wf_short",
        "other_0123456789abcdef01234567",
    ],
)
def test_run_registry_rejects_noncanonical_run_id_everywhere(
    tmp_path: Path, run_id: str
) -> None:
    registry = RunRegistry(tmp_path / "workspace")
    with pytest.raises(RunRegistryError, match="invalid canonical run_id"):
        registry.path_for(run_id)
    with pytest.raises(RunRegistryError, match="invalid canonical run_id"):
        registry.load(run_id)
    with pytest.raises(RunRegistryError, match="invalid canonical run_id"):
        with registry.lock(run_id):
            pass
    with pytest.raises(RunRegistryError, match="invalid canonical run_id"):
        registry.save({"run_id": run_id})


def test_run_registry_rejects_truncated_and_identity_tampered_records(
    tmp_path: Path,
) -> None:
    calls: list[str] = []
    engine = engine_for(tmp_path, RecordingModule("fixture.ok", calls))
    workflow = spec([{"id": "one", "module": "fixture.ok", "policy": "required"}])
    run_context = context(tmp_path / "workspace")
    result = engine.run(workflow, run_context)
    registry = RunRegistry(run_context.workspace)
    record_path = registry.path_for(result.run_id)

    write_json(
        record_path,
        {
            "run_id": result.run_id,
            "identity_sha256": result.record["identity_sha256"],
            "status": "SUCCEEDED",
        },
    )
    with pytest.raises(RunRegistryError, match="required schema"):
        registry.load(result.run_id)

    write_json(record_path, result.record)
    tampered = json.loads(record_path.read_text(encoding="utf-8"))
    tampered["context"]["mode"] = "replay"
    write_json(record_path, tampered)
    with pytest.raises(RunRegistryError, match="context does not match"):
        registry.load(result.run_id)


def test_stage_result_is_the_serialized_node_contract() -> None:
    stage = StageResult(
        status="BLOCKED",
        policy="optional",
        module="fixture.blocked",
        reason="fixture",
        root_cause="BLOCKED",
    )
    assert stage.to_dict() == {
        "status": "BLOCKED",
        "policy": "optional",
        "module": "fixture.blocked",
        "reason": "fixture",
        "root_cause": "BLOCKED",
    }


def test_run_identity_changes_when_declared_manifest_sha_changes(
    tmp_path: Path,
) -> None:
    index_path = make_history(tmp_path)
    resolver = ArtifactResolver(tmp_path)
    resolver.register(ResearchHistoryAdapter(tmp_path, index_path))
    registry = ModuleRegistry()
    registry.register(ResearchHistoryObservation())
    workflow = spec(
        [
            {
                "id": "signal",
                "module": "research_history.observe",
                "policy": "required",
                "config": {
                    "artifact_type": "ModelSignalArtifact",
                    "model_id": MODEL_A,
                    "status": "READY",
                },
            }
        ]
    )
    run_context = context(tmp_path / "workspace")
    engine = WorkflowEngine(registry, resolver)
    first = engine.run(workflow, run_context)

    payload = json.loads(index_path.read_text(encoding="utf-8"))
    signal = payload["days"]["2026-09-18"]["model_a"]["signal"]
    manifest_path = tmp_path / signal["files"]["manifest.json"]["path"]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["decision_cutoff"] = "2026-09-18T10:31:00+00:00"
    write_json(manifest_path, manifest)
    signal["files"]["manifest.json"]["sha256"] = sha256(manifest_path)
    write_json(index_path, payload)

    second = engine.run(workflow, run_context)
    assert second.run_id != first.run_id


def test_research_history_fixture_workflow_binds_input_to_signal(
    tmp_path: Path,
) -> None:
    index_path = make_history(tmp_path)
    resolver = ArtifactResolver(tmp_path)
    resolver.register(ResearchHistoryAdapter(tmp_path, index_path))
    registry = ModuleRegistry()
    registry.register(ResearchHistoryObservation())
    workflow = spec(
        [
            {
                "id": "input",
                "module": "research_history.observe",
                "policy": "required",
                "config": {
                    "artifact_type": "ModelInferenceInput",
                    "model_id": MODEL_A,
                    "status": "READY",
                },
            },
            {
                "id": "signal",
                "module": "research_history.observe",
                "needs": ["input"],
                "policy": "required",
                "config": {
                    "artifact_type": "ModelSignalArtifact",
                    "model_id": MODEL_A,
                    "status": "READY",
                    "require_same_run_id": True,
                },
            },
        ]
    )

    result = WorkflowEngine(registry, resolver).run(
        workflow, context(tmp_path / "workspace")
    )

    assert result.status == "SUCCEEDED"
    assert result.record["nodes"]["signal"]["output"]["count"] == 1


def test_current_repository_research_history_is_readable(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[2]
    index_path = root / "data_tw/catalog/research_data_history/index.json"
    if not index_path.is_file():
        pytest.skip("local research history is not present in a fresh checkout")
    resolver = ArtifactResolver(root)
    resolver.register(ResearchHistoryAdapter(root, index_path))
    refs = resolver.query(
        artifact_type="ModelSignalArtifact",
        model_id=MODEL_A,
        asof="2026-09-18",
        status="READY",
    )
    assert refs


def test_model_a_query_ignores_unstandardized_model_b_history_entry(
    tmp_path: Path,
) -> None:
    index_path = make_history(tmp_path)
    payload = json.loads(index_path.read_text(encoding="utf-8"))
    day = payload["days"]["2026-09-18"]
    day["status"] = "READY_MODELA_MODELB"
    day["model_b"] = {
        "model_id": "modelb_b19r2r_lambdarank_exact50_78f_v2",
        "asof": "2026-09-18",
        "status": "READY_RESEARCH_SHADOW",
        "content_sha256": "a" * 64,
        "history_path": "canonical_history/model_b/2026-09-18/aaaaaaaaaaaaaaaa",
        "files": {},
        "production_allowed": False,
        "no_apply": True,
    }
    write_json(index_path, payload)
    resolver = ArtifactResolver(tmp_path)
    resolver.register(ResearchHistoryAdapter(tmp_path, index_path))

    refs = resolver.query(
        artifact_type="ModelSignalArtifact",
        model_id=MODEL_A,
        asof="2026-09-18",
        status="READY",
    )

    assert len(refs) == 1
    assert refs[0].model_id == MODEL_A
    assert resolver.query(model_id=day["model_b"]["model_id"]) == []


def test_cli_runs_committed_readonly_fixture_end_to_end(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[2]
    fixture_repo = root / "tests/fixtures/tw_stock_workflow/repo"
    command = [
        sys.executable,
        str(root / "scripts/run_tw_stock_workflow.py"),
        "--repo-root",
        str(fixture_repo),
        "--history-index",
        str(fixture_repo / "history/index.json"),
        "--spec",
        str(root / "configs/workflows/research_history_observation.yaml"),
        "--mode",
        "readonly",
        "--asof",
        "2026-09-18",
        "--decision-cutoff",
        "2026-09-18T10:30:00+00:00",
        "--permission",
        "artifact.read",
        "--workspace",
        str(tmp_path / "workspace"),
    ]
    environment = {**os.environ, "PYTHONPATH": str(root)}

    completed = subprocess.run(
        command,
        cwd=root,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["status"] == "SUCCEEDED"
    assert payload["nodes"]["observe_model_a_signal"]["output"]["count"] == 1
