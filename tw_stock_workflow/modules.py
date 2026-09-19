from __future__ import annotations

from typing import Any, Protocol

from .artifacts import ArtifactRef, ArtifactResolver
from .types import ExecutionContext, WorkflowError


class ModuleBlocked(WorkflowError):
    pass


class Module(Protocol):
    module_id: str
    required_permissions: frozenset[str]

    def resolve_artifact_inputs(
        self,
        context: ExecutionContext,
        config: dict[str, Any],
        resolver: ArtifactResolver,
    ) -> list[ArtifactRef]: ...

    def execute(
        self,
        context: ExecutionContext,
        config: dict[str, Any],
        inputs: dict[str, dict[str, Any]],
        resolver: ArtifactResolver,
    ) -> dict[str, Any]: ...


class ModuleRegistry:
    def __init__(self) -> None:
        self._modules: dict[str, Module] = {}

    def register(self, module: Module) -> None:
        if module.module_id in self._modules:
            raise WorkflowError(f"duplicate module registration: {module.module_id}")
        self._modules[module.module_id] = module

    def get(self, module_id: str) -> Module:
        try:
            return self._modules[module_id]
        except KeyError as exc:
            raise WorkflowError(f"unknown workflow module: {module_id}") from exc

    def contains(self, module_id: str) -> bool:
        return module_id in self._modules


class ResearchHistoryObservation:
    module_id = "research_history.observe"
    required_permissions = frozenset({"artifact.read"})

    @staticmethod
    def _query(
        context: ExecutionContext,
        config: dict[str, Any],
        resolver: ArtifactResolver,
    ) -> list[ArtifactRef]:
        artifact_type = str(config.get("artifact_type") or "")
        model_id = str(config.get("model_id") or "")
        status = str(config.get("status") or "")
        if not artifact_type or not model_id or not status:
            raise WorkflowError("artifact_type, model_id, and status are required")
        return resolver.query(
            artifact_type=artifact_type,
            model_id=model_id,
            asof=str(config.get("asof") or context.asof),
            status=status,
        )

    def resolve_artifact_inputs(
        self,
        context: ExecutionContext,
        config: dict[str, Any],
        resolver: ArtifactResolver,
    ) -> list[ArtifactRef]:
        return self._query(context, config, resolver)

    def execute(
        self,
        context: ExecutionContext,
        config: dict[str, Any],
        inputs: dict[str, dict[str, Any]],
        resolver: ArtifactResolver,
    ) -> dict[str, Any]:
        allowed = {
            "artifact_type",
            "model_id",
            "asof",
            "status",
            "min_count",
            "require_same_run_id",
        }
        unknown = sorted(set(config) - allowed)
        if unknown:
            raise WorkflowError(
                f"unknown observation config fields: {', '.join(unknown)}"
            )
        artifact_type = str(config.get("artifact_type") or "")
        model_id = str(config.get("model_id") or "")
        status = str(config.get("status") or "")
        query_asof = str(config.get("asof") or context.asof)
        min_count = config.get("min_count", 1)
        if (
            not isinstance(min_count, int)
            or isinstance(min_count, bool)
            or min_count < 0
        ):
            raise WorkflowError("min_count must be a non-negative integer")
        refs = self._query(context, config, resolver)
        if len(refs) < min_count:
            raise ModuleBlocked(
                f"only {len(refs)} matching artifacts found; at least {min_count} required"
            )
        if config.get("require_same_run_id") is True:
            upstream_ids = {
                str(artifact.get("run_id"))
                for output in inputs.values()
                for artifact in output.get("artifacts", [])
                if artifact.get("run_id")
            }
            current_ids = {ref.run_id for ref in refs if ref.run_id}
            if not upstream_ids or not current_ids.intersection(upstream_ids):
                raise ModuleBlocked(
                    "no artifact shares a run_id with an upstream dependency"
                )
        return {
            "count": len(refs),
            "query": {
                "artifact_type": artifact_type,
                "model_id": model_id,
                "asof": query_asof,
                "status": status,
            },
            "artifacts": [ref.to_dict() for ref in refs],
        }
