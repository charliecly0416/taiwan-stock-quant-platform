from __future__ import annotations

from pathlib import Path

from .artifacts import ArtifactResolver, ResearchHistoryAdapter
from .engine import WorkflowEngine, WorkflowRunResult
from .modules import ModuleRegistry, ResearchHistoryObservation
from .replay import ReadonlyReplayWindowAdapter, ReadonlyReplayWindowObservation
from .replay_execution import ReplayCandidateExecution
from .readonly_snapshot import ReadonlyStrategySnapshotObservation
from .dual_track import ReadonlyModelTrackComparison, ReadonlyModelTrackExecution, _load_track_registry
from .spec import WorkflowSpec
from .types import ExecutionContext


def build_default_engine(
    repo_root: Path, history_index: Path | None = None
) -> WorkflowEngine:
    resolver = ArtifactResolver(repo_root)
    resolver.register(ResearchHistoryAdapter(repo_root, history_index))
    modules = ModuleRegistry()
    modules.register(ResearchHistoryObservation())
    modules.register(
        ReadonlyReplayWindowObservation(ReadonlyReplayWindowAdapter(repo_root))
    )
    modules.register(
        ReadonlyStrategySnapshotObservation(repo_root)
    )
    modules.register(ReplayCandidateExecution(repo_root))
    track_registry = _load_track_registry(repo_root)
    for track_id in track_registry["tracks"]:
        modules.register(ReadonlyModelTrackExecution(repo_root, track_id))
    modules.register(ReadonlyModelTrackComparison(repo_root, module_id="readonly_model_track.catalog"))
    modules.register(ReadonlyModelTrackComparison(repo_root))
    return WorkflowEngine(modules, resolver)


def run_workflow(
    *,
    repo_root: Path,
    spec_path: Path,
    context: ExecutionContext,
    history_index: Path | None = None,
) -> WorkflowRunResult:
    spec = WorkflowSpec.load(spec_path)
    engine = build_default_engine(repo_root, history_index)
    return engine.run(spec, context)
