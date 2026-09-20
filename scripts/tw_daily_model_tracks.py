#!/usr/bin/env python3
"""Run independent daily model tracks behind one small orchestration contract.

The caller owns data preparation and injects the actual scorers.  This module
only checks readiness, applies required/nonblocking policy, and makes each
track produce one ModelSignalArtifact without consuming another track's run.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping

import yaml


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TRACK_CONFIG = ROOT / "configs/readonly_model_tracks.yaml"
DEFAULT_RUNTIME_CONFIG = ROOT / "configs/daily_model_tracks.yaml"
RESULT_SCHEMA = "tw.daily_model_track_run.v1"

RUNTIME_ADAPTER_CONTRACTS = {
    "daily_model_a_v1": {
        "governance_adapter_id": "model_a_passthrough_v1",
        "required_dependencies": (
            "qlib_provider",
            "qlib_normalized",
            "source_acquisition",
            "decision_cutoff",
        ),
        "internal_stages": ("model_a_score",),
    },
    "daily_model_a_plus_b_b19r2r_v1": {
        "governance_adapter_id": "b19r2r_lambdarank_78f_v1",
        "required_dependencies": (
            "qlib_provider",
            "qlib_normalized",
            "source_acquisition",
            "decision_cutoff",
            "orthogonal_handoff",
            "provider_snapshot",
            "next_session_open",
            "twii_snapshot",
        ),
        "internal_stages": ("model_a_score", "b19r2r_rerank"),
    },
}

TrackAdapter = Callable[["TrackInvocation"], Mapping[str, Any]]
TrackService = Callable[[Mapping[str, Any]], Mapping[str, Any]]


class DailyModelTrackError(RuntimeError):
    """Raised when track configuration or an injected service is invalid."""


@dataclass(frozen=True)
class Dependency:
    name: str
    ready: bool
    value: Any = None
    detail: str = ""


@dataclass(frozen=True)
class TrackInvocation:
    asof: str
    batch_run_id: str
    output_root: Path
    track_id: str
    track_config: Mapping[str, Any]
    runtime_config: Mapping[str, Any]
    model_a_model_id: str
    dependencies: Mapping[str, Dependency]
    services: Mapping[str, TrackService]

    @property
    def track_output_root(self) -> Path:
        return self.output_root / self.track_id


def _load_config(config_path: Path, runtime_config_path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    runtime = yaml.safe_load(runtime_config_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise DailyModelTrackError("readonly model-track config must be an object")
    if not isinstance(runtime, dict):
        raise DailyModelTrackError("daily model-track runtime config must be an object")
    tracks = payload.get("tracks")
    runtime_tracks = runtime.get("tracks")
    if (
        not isinstance(tracks, dict)
        or not isinstance(runtime_tracks, dict)
        or runtime.get("schema_version") != "tw.daily_model_tracks.v1"
        or runtime.get("dependency_mode") != "independent"
    ):
        raise DailyModelTrackError("daily model-track runtime config is invalid")
    if set(runtime_tracks) != set(tracks):
        raise DailyModelTrackError("daily runtime tracks must match readonly model tracks")
    default_track_id = payload.get("default_track_id")
    defaults = [
        track_id
        for track_id, config in tracks.items()
        if config.get("production_default") is True
    ]
    if defaults != [default_track_id]:
        raise DailyModelTrackError("daily model tracks must keep exactly one configured default")
    model_a_model_id = str((runtime.get("model_a_scorer") or {}).get("model_id") or "")
    if model_a_model_id != tracks[default_track_id].get("model_id"):
        raise DailyModelTrackError("daily Model A scorer identity must match the default track")
    allowed = list((payload.get("virtual_account_policy") or {}).get("allowed_track_ids") or [])
    if allowed != [default_track_id]:
        raise DailyModelTrackError("daily runner cannot widen the virtual-account allowlist")
    for track_id, runtime_config in runtime_tracks.items():
        if not isinstance(runtime_config, dict):
            raise DailyModelTrackError(f"daily runtime config is invalid: {track_id}")
        if runtime_config.get("consumes_track_outputs") != []:
            raise DailyModelTrackError(f"daily track must not consume another track output: {track_id}")
        if tracks[track_id].get("workflow_policy") not in {"required", "nonblocking"}:
            raise DailyModelTrackError(f"daily track workflow policy is invalid: {track_id}")
        adapter_id = str(runtime_config.get("runtime_adapter_id") or "")
        contract = RUNTIME_ADAPTER_CONTRACTS.get(adapter_id)
        if contract is None:
            raise DailyModelTrackError(
                f"unknown daily model-track adapter: {adapter_id or track_id}"
            )
        governance = tracks[track_id]
        if runtime_config.get("model_id") != governance.get("model_id"):
            raise DailyModelTrackError(
                f"daily track model identity mismatch: {track_id}"
            )
        if governance.get("adapter_id") != contract["governance_adapter_id"]:
            raise DailyModelTrackError(
                f"daily track adapter identity mismatch: {track_id}"
            )
        if tuple(runtime_config.get("required_dependencies") or ()) != contract[
            "required_dependencies"
        ]:
            raise DailyModelTrackError(
                f"daily track dependency contract mismatch: {track_id}"
            )
        if tuple(runtime_config.get("internal_stages") or ()) != contract[
            "internal_stages"
        ]:
            raise DailyModelTrackError(
                f"daily track stage contract mismatch: {track_id}"
            )
    return {"governance": payload, "runtime": runtime}


def _dependency(name: str, raw: Any) -> Dependency:
    if isinstance(raw, bool):
        return Dependency(name=name, ready=raw)
    if isinstance(raw, Mapping):
        if "ready" not in raw:
            raise DailyModelTrackError(f"dependency readiness is missing: {name}")
        value = raw.get("value")
        if value is None:
            value = raw.get("path", raw.get("ref"))
        return Dependency(
            name=name,
            ready=raw.get("ready") is True,
            value=value,
            detail=str(raw.get("detail") or ""),
        )
    if raw is None:
        return Dependency(name=name, ready=False, detail="dependency was not supplied")
    raise DailyModelTrackError(f"dependency state is invalid: {name}")


def _service(invocation: TrackInvocation, name: str) -> TrackService:
    value = invocation.services.get(name)
    if not callable(value):
        raise DailyModelTrackError(f"daily model-track service is missing: {name}")
    return value


def _value(invocation: TrackInvocation, name: str) -> Any:
    return invocation.dependencies[name].value


def _artifact_path(result: Mapping[str, Any], *, service_name: str) -> str:
    value = str(result.get("model_signal_artifact") or "").strip()
    if not value:
        raise DailyModelTrackError(f"{service_name} did not return model_signal_artifact")
    return value


def _model_a_request(invocation: TrackInvocation, *, stage_root: Path) -> dict[str, Any]:
    return {
        "track_id": invocation.track_id,
        "stage_id": "model_a_score",
        "model_id": invocation.model_a_model_id,
        "asof": invocation.asof,
        "run_id": f"{invocation.batch_run_id}__{invocation.track_id}__model_a",
        "output_root": str(stage_root),
        "qlib_provider": _value(invocation, "qlib_provider"),
        "qlib_normalized": _value(invocation, "qlib_normalized"),
        "source_acquisition_run_id": _value(invocation, "source_acquisition"),
        "decision_cutoff": _value(invocation, "decision_cutoff"),
        "no_publish": True,
        "no_catalog": True,
        "no_latest": True,
        "no_target_output": True,
    }


def run_model_a_track(invocation: TrackInvocation) -> Mapping[str, Any]:
    request = _model_a_request(
        invocation,
        stage_root=invocation.track_output_root / "model_a_stage",
    )
    score = dict(_service(invocation, "model_a_scorer")(request))
    ok = score.get("ok") is True
    artifact = _artifact_path(score, service_name="model_a_scorer") if ok else ""
    return {
        "ok": ok,
        "status": str(score.get("status") or ("READY" if ok else "BLOCKED_MODELA_SCORE")),
        "model_signal_artifact": artifact,
        "stages": {"model_a_score": score},
    }


def run_model_a_plus_b_track(invocation: TrackInvocation) -> Mapping[str, Any]:
    """Run an isolated Model A score, then rerank that exact internal output."""
    model_a_request = _model_a_request(
        invocation,
        stage_root=invocation.track_output_root / "model_a_stage",
    )
    model_a = dict(_service(invocation, "model_a_scorer")(model_a_request))
    if model_a.get("ok") is not True:
        return {
            "ok": False,
            "status": str(model_a.get("status") or "BLOCKED_INTERNAL_MODELA_SCORE"),
            "model_signal_artifact": "",
            "stages": {"model_a_score": model_a},
        }
    internal_model_a_artifact = _artifact_path(model_a, service_name="model_a_scorer")
    rerank_request = {
        "track_id": invocation.track_id,
        "stage_id": "b19r2r_rerank",
        "model_id": invocation.track_config.get("model_id"),
        "asof": invocation.asof,
        "run_id": f"{invocation.batch_run_id}__{invocation.track_id}__b19r2r",
        "output_root": str(invocation.track_output_root / "b19r2r_stage"),
        "model_a_signal_artifact": internal_model_a_artifact,
        "model_a_source": "internal_same_track_score",
        "orthogonal_handoff": _value(invocation, "orthogonal_handoff"),
        "provider_snapshot": _value(invocation, "provider_snapshot"),
        "source_acquisition_run_id": _value(invocation, "source_acquisition"),
        "decision_cutoff": _value(invocation, "decision_cutoff"),
        "next_session_open": _value(invocation, "next_session_open"),
        "twii_snapshot": _value(invocation, "twii_snapshot"),
        "production_allowed": False,
        "no_apply": True,
        "no_latest": True,
    }
    rerank = dict(_service(invocation, "b19r2r_reranker")(rerank_request))
    ok = rerank.get("ok") is True
    artifact = _artifact_path(rerank, service_name="b19r2r_reranker") if ok else ""
    return {
        "ok": ok,
        "status": str(rerank.get("status") or ("READY_RESEARCH_SHADOW" if ok else "BLOCKED_B19R2R")),
        "model_signal_artifact": artifact,
        "internal_model_a_signal_artifact": internal_model_a_artifact,
        "stages": {"model_a_score": model_a, "b19r2r_rerank": rerank},
    }


DEFAULT_ADAPTERS: dict[str, TrackAdapter] = {
    "daily_model_a_v1": run_model_a_track,
    "daily_model_a_plus_b_b19r2r_v1": run_model_a_plus_b_track,
}


def run_daily_model_tracks(
    *,
    asof: str,
    batch_run_id: str,
    output_root: Path | str,
    dependency_states: Mapping[str, Any],
    services: Mapping[str, TrackService],
    config_path: Path | str = DEFAULT_TRACK_CONFIG,
    runtime_config_path: Path | str = DEFAULT_RUNTIME_CONFIG,
    selected_track_ids: list[str] | tuple[str, ...] | None = None,
    adapter_registry: Mapping[str, TrackAdapter] | None = None,
    max_workers: int | None = None,
) -> dict[str, Any]:
    """Run same-level model tracks and apply their configured failure policy."""
    loaded = _load_config(Path(config_path), Path(runtime_config_path))
    config = loaded["governance"]
    runtime = loaded["runtime"]
    tracks = config["tracks"]
    runtime_tracks = runtime["tracks"]
    selected = list(selected_track_ids) if selected_track_ids is not None else list(tracks)
    unknown = sorted(set(selected) - set(tracks))
    if unknown:
        raise DailyModelTrackError(f"unknown daily model tracks: {','.join(unknown)}")
    adapters = dict(DEFAULT_ADAPTERS)
    if adapter_registry:
        adapters.update(adapter_registry)
    configured_workers = runtime.get("default_max_workers") or 2
    workers = int(configured_workers if max_workers is None else max_workers)
    if workers < 1:
        raise DailyModelTrackError("max_workers must be at least 1")

    pending_results: dict[str, Any] = {}
    runnable: dict[str, tuple[dict[str, Any], TrackInvocation, TrackAdapter]] = {}
    for track_id in selected:
        track_config = tracks[track_id]
        runtime_config = runtime_tracks[track_id]
        policy = str(track_config["workflow_policy"])
        required_names = list(runtime_config.get("required_dependencies") or [])
        dependencies = {
            name: _dependency(name, dependency_states.get(name)) for name in required_names
        }
        missing = [name for name, state in dependencies.items() if not state.ready]
        base = {
            "track_id": track_id,
            "runtime_adapter_id": runtime_config.get("runtime_adapter_id"),
            "artifact_type": "ModelSignalArtifact",
            "workflow_policy": policy,
            "governance_status": track_config.get("governance_status"),
            "production_default": track_config.get("production_default") is True,
            "virtual_account_eligible": track_config.get("virtual_account_eligible") is True,
            "production_allowed": False,
            "no_apply": True,
            "source_snapshot_id": str(
                dependencies.get("source_acquisition").value
                if dependencies.get("source_acquisition") is not None
                else ""
            ),
            "blocking": policy == "required",
            "output_root": str(Path(output_root) / track_id),
            "dependencies": {
                name: {"ready": state.ready, "detail": state.detail}
                for name, state in dependencies.items()
            },
        }
        if missing:
            track_result = {
                **base,
                "attempted": False,
                "ok": False,
                "status": "BLOCKED_DEPENDENCY_NOT_READY",
                "missing_dependencies": missing,
                "model_signal_artifact": "",
                "artifact_dir": "",
                "stages": {},
            }
            pending_results[track_id] = track_result
        else:
            adapter_id = str(runtime_config.get("runtime_adapter_id") or "")
            adapter = adapters.get(adapter_id)
            if adapter is None:
                raise DailyModelTrackError(f"unknown daily model-track adapter: {adapter_id}")
            invocation = TrackInvocation(
                asof=asof,
                batch_run_id=batch_run_id,
                output_root=Path(output_root),
                track_id=track_id,
                track_config=track_config,
                runtime_config=runtime_config,
                model_a_model_id=str(runtime["model_a_scorer"]["model_id"]),
                dependencies=dependencies,
                services=services,
            )
            runnable[track_id] = (base, invocation, adapter)

    def execute_track(
        base: dict[str, Any], invocation: TrackInvocation, adapter: TrackAdapter
    ) -> dict[str, Any]:
        try:
            adapter_result = dict(adapter(invocation))
            normalized = {
                **adapter_result,
                **base,
                "attempted": True,
                "ok": adapter_result.get("ok") is True,
                "status": str(adapter_result.get("status") or "INVALID_ADAPTER_RESULT"),
                "model_signal_artifact": str(
                    adapter_result.get("model_signal_artifact") or ""
                ),
                "artifact_dir": str(
                    adapter_result.get("model_signal_artifact") or ""
                ),
                "stages": dict(adapter_result.get("stages") or {}),
            }
            return normalized
        except Exception as exc:
            return {
                **base,
                "attempted": True,
                "ok": False,
                "status": "FAILED_ADAPTER_EXCEPTION",
                "error": f"{type(exc).__name__}:{exc}",
                "model_signal_artifact": "",
                "artifact_dir": "",
                "stages": {},
            }

    if runnable:
        with ThreadPoolExecutor(max_workers=min(workers, len(runnable))) as executor:
            futures = {
                executor.submit(execute_track, base, invocation, adapter): track_id
                for track_id, (base, invocation, adapter) in runnable.items()
            }
            for future in as_completed(futures):
                pending_results[futures[future]] = future.result()

    results = {track_id: pending_results[track_id] for track_id in selected}
    required_failed = False
    nonblocking_failed = False
    for track_id, track_result in results.items():
        policy = str(tracks[track_id]["workflow_policy"])
        if track_result.get("ok") is not True:
            if policy == "required":
                required_failed = True
            else:
                nonblocking_failed = True

    status = (
        "BLOCKED_REQUIRED_TRACK"
        if required_failed
        else "READY_WITH_NONBLOCKING_FAILURES"
        if nonblocking_failed
        else "READY"
    )
    return {
        "schema_version": RESULT_SCHEMA,
        "asof": asof,
        "batch_run_id": batch_run_id,
        "dependency_mode": "independent",
        "execution_mode": (
            "concurrent_fan_out" if len(runnable) > 1 and workers > 1 else "sequential"
        ),
        "max_workers": workers,
        "status": status,
        "ok": not required_failed,
        "default_track_id": config["default_track_id"],
        "virtual_account_allowed_track_ids": list(
            config["virtual_account_policy"]["allowed_track_ids"]
        ),
        "tracks": results,
    }
