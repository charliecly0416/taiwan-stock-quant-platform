from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .artifacts import ArtifactResolver
from .modules import CachedOutputValidator, Module, ModuleBlocked, ModuleRegistry
from .run_registry import (
    TERMINAL_STATUSES,
    RunRegistry,
    RunRegistryError,
    run_id_for_identity,
)
from .spec import WorkflowSpec
from .types import ExecutionContext, WorkflowError


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass(frozen=True)
class StageResult:
    status: str
    policy: str
    module: str
    output: dict[str, Any] | None = None
    reason: str | None = None
    dependencies: dict[str, str] = field(default_factory=dict)
    dependency_causes: dict[str, str] = field(default_factory=dict)
    root_cause: str | None = None
    missing_permissions: tuple[str, ...] = ()
    error_type: str | None = None
    error: str | None = None

    def __post_init__(self) -> None:
        if self.status not in {"SUCCEEDED", "BLOCKED", "FAILED", "SKIPPED"}:
            raise WorkflowError(f"invalid stage status: {self.status}")
        if self.policy not in {"required", "optional", "nonblocking"}:
            raise WorkflowError(f"invalid stage policy: {self.policy}")
        if not self.module:
            raise WorkflowError("stage module is required")

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "status": self.status,
            "policy": self.policy,
            "module": self.module,
        }
        optional = {
            "output": self.output,
            "reason": self.reason,
            "root_cause": self.root_cause,
            "error_type": self.error_type,
            "error": self.error,
        }
        result.update(
            {key: value for key, value in optional.items() if value is not None}
        )
        if self.dependencies:
            result["dependencies"] = self.dependencies
        if self.dependency_causes:
            result["dependency_causes"] = self.dependency_causes
        if self.missing_permissions:
            result["missing_permissions"] = list(self.missing_permissions)
        return result


@dataclass(frozen=True)
class WorkflowRunResult:
    record: dict[str, Any]
    idempotent_reuse: bool = False

    @property
    def run_id(self) -> str:
        return str(self.record["run_id"])

    @property
    def status(self) -> str:
        return str(self.record["status"])


class WorkflowEngine:
    def __init__(self, modules: ModuleRegistry, resolver: ArtifactResolver) -> None:
        self.modules = modules
        self.resolver = resolver

    def _resolve_artifact_inputs(
        self,
        module: Module,
        context: ExecutionContext,
        config: dict[str, Any],
    ) -> list[dict[str, Any]]:
        return [
            ref.to_dict()
            for ref in module.resolve_artifact_inputs(context, config, self.resolver)
        ]

    @staticmethod
    def _terminal_status(stages: dict[str, StageResult]) -> str:
        required = [stage for stage in stages.values() if stage.policy == "required"]
        if any(
            stage.status == "FAILED"
            or (stage.status == "SKIPPED" and stage.root_cause == "FAILED")
            for stage in required
        ):
            return "FAILED"
        if any(stage.status in {"BLOCKED", "SKIPPED"} for stage in required):
            return "BLOCKED"
        return "SUCCEEDED"

    def run(self, spec: WorkflowSpec, context: ExecutionContext) -> WorkflowRunResult:
        ordered_nodes = spec.topological_nodes()
        for node in spec.nodes:
            if not self.modules.contains(node.module):
                raise WorkflowError(f"unknown workflow module: {node.module}")
        artifact_inputs: dict[str, list[dict[str, Any]]] = {}
        artifact_input_errors: dict[str, dict[str, str]] = {}
        for node in ordered_nodes:
            module = self.modules.get(node.module)
            if module.required_permissions - context.permissions:
                artifact_inputs[node.node_id] = []
                continue
            try:
                artifact_inputs[node.node_id] = self._resolve_artifact_inputs(
                    module, context, node.config
                )
            except Exception as exc:
                artifact_inputs[node.node_id] = []
                artifact_input_errors[node.node_id] = {
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                }
        identity_payload = {
            "workflow": spec.to_dict(),
            "context": context.identity_payload(),
            "artifact_inputs": artifact_inputs,
            "artifact_input_errors": artifact_input_errors,
        }
        run_id, identity_digest = run_id_for_identity(identity_payload)
        registry = RunRegistry(context.workspace)
        with registry.lock(run_id):
            existing = registry.load(run_id)
            if existing is not None:
                if existing["identity_sha256"] != identity_digest:
                    raise RunRegistryError(f"run identity conflict: {run_id}")
                if existing["status"] not in TERMINAL_STATUSES:
                    raise RunRegistryError(f"non-terminal run already exists: {run_id}")
                if existing["status"] == "SUCCEEDED":
                    for node in ordered_nodes:
                        stage = existing["nodes"][node.node_id]
                        module = self.modules.get(node.module)
                        if stage["status"] != "SUCCEEDED" or not isinstance(
                            module, CachedOutputValidator
                        ):
                            continue
                        try:
                            module.validate_cached_output(
                                context,
                                node.config,
                                stage["output"],
                                self.resolver,
                            )
                            after = self._resolve_artifact_inputs(
                                module, context, node.config
                            )
                            if after != artifact_inputs[node.node_id]:
                                raise WorkflowError(
                                    "artifact inputs changed during cached output validation"
                                )
                        except Exception as exc:
                            raise WorkflowError(
                                f"cached output validation failed for node {node.node_id}: {exc}"
                            ) from exc
                return WorkflowRunResult(existing, idempotent_reuse=True)

            started_at = _utc_now()
            common_record = {
                "schema_version": "tw.workflow.run.v1",
                "run_id": run_id,
                "identity_sha256": identity_digest,
                "identity_payload": identity_payload,
                "workflow_id": spec.workflow_id,
                "workflow_version": spec.version,
                "context": context.identity_payload(),
                "artifact_inputs": artifact_inputs,
                "artifact_input_errors": artifact_input_errors,
                "started_at": started_at,
            }
            registry.save({**common_record, "status": "RUNNING", "nodes": {}})
            stages: dict[str, StageResult] = {}
            for node in ordered_nodes:
                dependency_states = {item: stages[item].status for item in node.needs}
                if any(state != "SUCCEEDED" for state in dependency_states.values()):
                    dependency_causes = {
                        item: stages[item].root_cause or stages[item].status
                        for item in node.needs
                    }
                    stages[node.node_id] = StageResult(
                        status="SKIPPED",
                        policy=node.policy,
                        module=node.module,
                        reason="dependency_not_succeeded",
                        dependencies=dependency_states,
                        dependency_causes=dependency_causes,
                        root_cause=(
                            "FAILED"
                            if "FAILED" in dependency_causes.values()
                            else "BLOCKED"
                        ),
                    )
                    continue
                module = self.modules.get(node.module)
                missing_permissions = tuple(
                    sorted(module.required_permissions - context.permissions)
                )
                if missing_permissions:
                    stages[node.node_id] = StageResult(
                        status="BLOCKED",
                        policy=node.policy,
                        module=node.module,
                        reason="permission_denied",
                        missing_permissions=missing_permissions,
                        root_cause="BLOCKED",
                    )
                    continue
                if node.node_id in artifact_input_errors:
                    error = artifact_input_errors[node.node_id]
                    stages[node.node_id] = StageResult(
                        status="FAILED",
                        policy=node.policy,
                        module=node.module,
                        reason="artifact_input_resolution_failed",
                        error_type=error["error_type"],
                        error=error["error"],
                        root_cause="FAILED",
                    )
                    continue
                inputs = {item: stages[item].output or {} for item in node.needs}
                try:
                    before = self._resolve_artifact_inputs(module, context, node.config)
                    if before != artifact_inputs[node.node_id]:
                        raise WorkflowError(
                            "artifact inputs changed before module execution"
                        )
                    execution_error: Exception | None = None
                    output: dict[str, Any] | None = None
                    try:
                        output = module.execute(
                            context,
                            node.config,
                            inputs,
                            self.resolver,
                        )
                        if not isinstance(output, dict):
                            raise WorkflowError("module output must be an object")
                    except Exception as exc:
                        execution_error = exc
                    after = self._resolve_artifact_inputs(module, context, node.config)
                    if after != artifact_inputs[node.node_id]:
                        raise WorkflowError(
                            "artifact inputs changed during module execution"
                        )
                    if execution_error is not None:
                        raise execution_error
                    if output is None:
                        raise WorkflowError("module output is missing")
                    stages[node.node_id] = StageResult(
                        status="SUCCEEDED",
                        policy=node.policy,
                        module=node.module,
                        output=output,
                    )
                except ModuleBlocked as exc:
                    stages[node.node_id] = StageResult(
                        status="BLOCKED",
                        policy=node.policy,
                        module=node.module,
                        reason=str(exc),
                        root_cause="BLOCKED",
                    )
                except Exception as exc:
                    stages[node.node_id] = StageResult(
                        status="FAILED",
                        policy=node.policy,
                        module=node.module,
                        error_type=type(exc).__name__,
                        error=str(exc),
                        root_cause="FAILED",
                    )
            status = self._terminal_status(stages)
            record = {
                **common_record,
                "status": status,
                "finished_at": _utc_now(),
                "nodes": {
                    node_id: stage.to_dict() for node_id, stage in stages.items()
                },
            }
            registry.save(record)
            return WorkflowRunResult(record)
