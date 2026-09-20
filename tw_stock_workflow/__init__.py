"""Small, read-only-first workflow kernel for Taiwan stock research artifacts."""

from .artifacts import ArtifactRef, ArtifactResolver, ResearchHistoryAdapter
from .engine import StageResult, WorkflowEngine, WorkflowRunResult
from .dual_track import (
    ReadonlyModelTrackComparison,
    ReadonlyModelTrackExecution,
    build_comparison_bundle,
    build_track_bundle,
    validate_track_bundle,
)
from .modules import (
    CachedOutputValidator,
    Module,
    ModuleBlocked,
    ModuleRegistry,
    ResearchHistoryObservation,
)
from .run_registry import RunRegistry
from .task_dispatcher import TaskDispatcher, TaskPlan, TaskRequestError
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
    "ReadonlyModelTrackComparison",
    "ReadonlyModelTrackExecution",
    "ReplayCandidateExecution",
    "ReplayCandidateInputAdapter",
    "RunRegistry",
    "TaskDispatcher",
    "TaskPlan",
    "TaskRequestError",
    "StageResult",
    "WorkflowEngine",
    "WorkflowNode",
    "WorkflowRunResult",
    "WorkflowSpec",
    "build_comparison_bundle",
    "build_track_bundle",
    "validate_track_bundle",
]
