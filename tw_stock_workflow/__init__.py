"""Small, read-only-first workflow kernel for Taiwan stock research artifacts."""

from .artifacts import ArtifactRef, ArtifactResolver, ResearchHistoryAdapter
from .engine import StageResult, WorkflowEngine, WorkflowRunResult
from .modules import (
    CachedOutputValidator,
    Module,
    ModuleBlocked,
    ModuleRegistry,
    ResearchHistoryObservation,
)
from .run_registry import RunRegistry
from .replay import ReadonlyReplayWindowAdapter, ReadonlyReplayWindowObservation
from .replay_execution import ReplayCandidateExecution, ReplayCandidateInputAdapter
from .spec import WorkflowNode, WorkflowSpec
from .types import ExecutionContext

__all__ = [
    "ArtifactRef",
    "ArtifactResolver",
    "CachedOutputValidator",
    "ExecutionContext",
    "Module",
    "ModuleBlocked",
    "ModuleRegistry",
    "ResearchHistoryAdapter",
    "ResearchHistoryObservation",
    "ReadonlyReplayWindowAdapter",
    "ReadonlyReplayWindowObservation",
    "ReplayCandidateExecution",
    "ReplayCandidateInputAdapter",
    "RunRegistry",
    "StageResult",
    "WorkflowEngine",
    "WorkflowNode",
    "WorkflowRunResult",
    "WorkflowSpec",
]
