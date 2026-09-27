"""Async bridge from the readonly API to the registered replay task.

The task dispatcher remains the single workflow entrypoint.  This service only
validates the request, runs that registered task off the Flask request thread,
and exposes a small filesystem-backed status snapshot for polling.
"""
from __future__ import annotations

import json
import re
import threading
import csv
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path
from typing import Any

from tw_stock_workflow.task_dispatcher import TaskDispatcher, TaskRequestError


ROOT = Path(__file__).resolve().parents[3]
RUN_ROOT = ROOT / "data_tw/ops/unified_tasks"
TASK_TYPE = "readonly_backtest"
JOB_ID_RE = re.compile(r"^task_readonly_backtest_[a-f0-9]{20}$")
TERMINAL = {"SUCCEEDED", "FAILED", "REJECTED"}
_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="tw-readonly-replay")
_lock = threading.RLock()
_active: set[str] = set()


class DynamicReplayError(ValueError):
    def __init__(self, status: str, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.status = status
        self.message = message
        self.details = details or {}


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{threading.get_native_id()}.tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    temporary.replace(path)


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _parse_date(value: Any, field: str) -> str:
    raw = str(value or "")
    try:
        parsed = date.fromisoformat(raw)
    except ValueError as exc:
        raise DynamicReplayError("invalid_request", f"{field} must be an ISO date", {field: raw}) from exc
    return parsed.isoformat()


def _request_payload(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise DynamicReplayError("invalid_request", "request body must be an object")
    allowed = {"model_track_id", "strategy_rule", "start_date", "end_date", "timeout_seconds"}
    unknown = sorted(set(payload) - allowed)
    if unknown:
        raise DynamicReplayError("invalid_request", "unknown replay parameters", {"unknown": unknown})
    track = str(payload.get("model_track_id") or "").strip()
    strategy = str(payload.get("strategy_rule") or "").strip()
    if not track or not re.fullmatch(r"[a-z][a-z0-9_.-]*", track):
        raise DynamicReplayError("invalid_request", "model_track_id is required and must be canonical")
    if not strategy or not re.fullmatch(r"[a-z][a-z0-9_.-]*", strategy):
        raise DynamicReplayError("invalid_request", "strategy_rule is required and must be canonical")
    start = _parse_date(payload.get("start_date"), "start_date")
    end = _parse_date(payload.get("end_date"), "end_date")
    if start > end:
        raise DynamicReplayError("invalid_window", "start_date must be <= end_date")
    timeout = int(payload.get("timeout_seconds") or 1200)
    if timeout < 60 or timeout > 7200:
        raise DynamicReplayError("invalid_request", "timeout_seconds must be between 60 and 7200")
    return {
        "model_track_id": track,
        "strategy_rule": strategy,
        "start_date": start,
        "end_date": end,
        "timeout_seconds": timeout,
    }


def _dispatcher() -> TaskDispatcher:
    return TaskDispatcher(ROOT, run_root=RUN_ROOT)


def _status_path(run_id: str) -> Path:
    return RUN_ROOT / TASK_TYPE / run_id / "api_status.json"


def _base_status(run_id: str, request: dict[str, Any], *, status: str) -> dict[str, Any]:
    return {
        "schema_version": "tw.readonly_dynamic_replay.v1",
        "task_type": TASK_TYPE,
        "run_id": run_id,
        "status": status,
        "readonly_only": True,
        "no_apply": True,
        "production_trade_enabled": False,
        "request": request,
    }


def _enrich_execution(execution: dict[str, Any]) -> dict[str, Any]:
    """Attach audited metrics without making the API handler run replay code."""
    artifact = execution.get("artifact")
    if not isinstance(artifact, dict):
        return execution
    manifest_ref = str(artifact.get("manifest") or "")
    manifest_path = (ROOT / manifest_ref).resolve() if manifest_ref else None
    if not manifest_path or not manifest_path.is_file() or not manifest_path.is_relative_to(ROOT.resolve()):
        return execution
    manifest = _read_json(manifest_path)
    if not manifest:
        return execution
    metrics: dict[str, Any] = {}
    metrics_ref = str((manifest.get("artifacts") or {}).get("metrics") or "")
    metrics_path = (ROOT / metrics_ref).resolve() if metrics_ref else None
    if metrics_path and metrics_path.is_file() and metrics_path.is_relative_to(ROOT.resolve()):
        metrics = _read_json(metrics_path) or {}
    if not metrics:
        summary_ref = str((manifest.get("artifacts") or {}).get("summary") or "")
        summary_path = (ROOT / summary_ref).resolve() if summary_ref else None
        if summary_path and summary_path.is_file() and summary_path.is_relative_to(ROOT.resolve()):
            try:
                with summary_path.open("r", encoding="utf-8", newline="") as handle:
                    rows = list(csv.DictReader(handle))
                if rows:
                    metrics = rows[0]
            except (OSError, csv.Error):
                metrics = {}
    if metrics:
        enriched = dict(execution)
        enriched["replay_metrics"] = metrics
        enriched["replay_manifest"] = manifest_ref
        return enriched
    return execution


def create_replay(payload: dict[str, Any]) -> dict[str, Any]:
    request_parameters = _request_payload(payload)
    dispatcher = _dispatcher()
    request = {
        "schema_version": "tw.task.request.v1",
        "task_type": TASK_TYPE,
        "parameters": request_parameters,
    }
    try:
        plan = dispatcher.plan(request)
    except TaskRequestError as exc:
        raise DynamicReplayError("rejected", str(exc)) from exc
    run_id = plan.run_id
    path = _status_path(run_id)
    result_path = plan.run_dir / "result.json"
    with _lock:
        existing = _read_json(result_path)
        if existing:
            # A deterministic task id may already have a completed result.
            # Reuse must expose the same audited metrics as the async runner;
            # otherwise the UI sees SUCCEEDED but renders empty indicators.
            reusable = dict(existing)
            execution = reusable.get("execution")
            if isinstance(execution, dict):
                reusable["execution"] = _enrich_execution(execution)
            return {**_base_status(run_id, request_parameters, status=str(reusable.get("status") or "FAILED")), "result": reusable, "idempotent_reuse": True}
        status = _read_json(path)
        if status:
            return status
        queued = {**_base_status(run_id, request_parameters, status="QUEUED"), "queued_at": date.today().isoformat()}
        _write_json(path, queued)
        if run_id not in _active:
            _active.add(run_id)
            _executor.submit(_run, dispatcher, request, run_id, request_parameters)
        return queued


def _run(dispatcher: TaskDispatcher, request: dict[str, Any], run_id: str, parameters: dict[str, Any]) -> None:
    path = _status_path(run_id)
    _write_json(path, {**_base_status(run_id, parameters, status="RUNNING")})
    try:
        result = dispatcher.dispatch(request)
        execution = result.get("execution") if isinstance(result.get("execution"), dict) else None
        if execution is not None:
            result = dict(result)
            result["execution"] = _enrich_execution(execution)
        status = str(result.get("status") or ("SUCCEEDED" if result.get("ok") else "FAILED"))
        _write_json(path, {**_base_status(run_id, parameters, status=status), "result": result})
    except Exception as exc:  # keep polling contract intact on unexpected runner errors
        _write_json(path, {**_base_status(run_id, parameters, status="FAILED"), "error": str(exc), "error_type": type(exc).__name__})
    finally:
        with _lock:
            _active.discard(run_id)


def get_replay(run_id: str) -> dict[str, Any]:
    if not JOB_ID_RE.fullmatch(str(run_id or "")):
        raise DynamicReplayError("invalid_job_id", "invalid readonly replay task id")
    path = _status_path(run_id)
    payload = _read_json(path)
    if payload:
        return payload
    result = _read_json(RUN_ROOT / TASK_TYPE / run_id / "result.json")
    if result:
        return {**_base_status(run_id, result.get("normalized_request", {}).get("parameters", {}), status=str(result.get("status") or "FAILED")), "result": result}
    raise DynamicReplayError("not_found", "readonly replay task was not found")


def replay_options() -> dict[str, Any]:
    """Return selectable production model tracks and strategies without running anything."""
    dispatcher = _dispatcher()
    entry = dispatcher.registry["tasks"][TASK_TYPE]
    tracks_path = ROOT / str(entry["bindings"]["model_tracks"])
    policy_path = ROOT / str(entry["bindings"]["replay_policy"])
    registry_path = ROOT / str(entry["bindings"]["modular_registry"])
    import yaml

    tracks = yaml.safe_load(tracks_path.read_text(encoding="utf-8")).get("tracks") or {}
    policy = yaml.safe_load(policy_path.read_text(encoding="utf-8")) or {}
    registry = yaml.safe_load(registry_path.read_text(encoding="utf-8")) or {}
    models = policy.get("models") or {}
    strategies = (registry.get("strategies") or {}).get("production_selectable") or {}
    return {
        "schema_version": "tw.readonly_dynamic_replay_options.v1",
        "readonly_only": True,
        "models": [
            {"track_id": track_id, "model_id": cfg.get("model_id"), "display_name": track_id}
            for track_id, cfg in tracks.items()
            if cfg.get("model_id") in models and models[cfg.get("model_id")].get("production_selectable") is True
        ],
        "strategies": [
            {"strategy_rule": rule, "display_name": (cfg or {}).get("display_name", rule)}
            for rule, cfg in strategies.items()
        ],
        "policy": {
            "allowed_replay_start_min": policy.get("allowed_replay_start_min"),
            "latest_available_signal_date": policy.get("latest_available_signal_date"),
        },
    }
