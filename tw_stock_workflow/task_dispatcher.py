from __future__ import annotations

import hashlib
import json
import os
import signal
import subprocess
import sys
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Callable, Mapping
from zoneinfo import ZoneInfo

import yaml
from jsonschema import Draft202012Validator, FormatChecker

from .service import run_workflow
from .types import ExecutionContext


DEFAULT_REGISTRY = Path("configs/tw_task_registry.yaml")
DEFAULT_REQUEST_SCHEMA = Path("schemas/tw_task_request.schema.json")
DEFAULT_RUN_ROOT = Path("data_tw/ops/unified_tasks")
TASK_RUN_SCHEMA = "tw.task.run.v1"
SUPPORTED_EXECUTORS = {
    "daily_update_v1",
    "readonly_backtest_v1",
    "workflow_spec_v1",
}

CommandRunner = Callable[..., Mapping[str, Any]]
WorkflowRunner = Callable[..., Any]


class TaskRequestError(RuntimeError):
    """Raised when a task request or registry entry violates its contract."""


def _canonical_sha256(payload: Any) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _load_document(path: Path) -> dict[str, Any]:
    try:
        if path.suffix.lower() == ".json":
            payload = json.loads(path.read_text(encoding="utf-8"))
        else:
            payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, yaml.YAMLError) as exc:
        raise TaskRequestError(f"invalid task document: {path}") from exc
    if not isinstance(payload, dict):
        raise TaskRequestError(f"task document must be an object: {path}")
    return payload


def _validation_error(
    payload: Mapping[str, Any], schema: Mapping[str, Any], *, label: str
) -> None:
    try:
        Draft202012Validator.check_schema(schema)
        errors = sorted(
            Draft202012Validator(
                schema, format_checker=FormatChecker()
            ).iter_errors(payload),
            key=lambda error: list(error.absolute_path),
        )
    except Exception as exc:
        raise TaskRequestError(f"invalid {label} schema") from exc
    if errors:
        error = errors[0]
        location = ".".join(str(item) for item in error.absolute_path) or "$"
        raise TaskRequestError(f"invalid {label} at {location}: {error.message}")


def _default_command_runner(
    command: list[str],
    *,
    cwd: Path,
    stdout_path: Path,
    stderr_path: Path,
    timeout: int,
    env: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    stdout_path.parent.mkdir(parents=True, exist_ok=True)
    stderr_path.parent.mkdir(parents=True, exist_ok=True)
    process_env = os.environ.copy()
    process_env.update(dict(env or {}))
    process = subprocess.Popen(
        command,
        cwd=cwd,
        env=process_env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )
    try:
        stdout, stderr = process.communicate(timeout=timeout)
        stdout_path.write_text(stdout, encoding="utf-8")
        stderr_path.write_text(stderr, encoding="utf-8")
        return {
            "ok": process.returncode == 0,
            "returncode": process.returncode,
            "stdout_path": str(stdout_path),
            "stderr_path": str(stderr_path),
            "stdout": stdout,
            "stderr_tail": stderr[-4000:],
        }
    except subprocess.TimeoutExpired:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            stdout, stderr = process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            stdout, stderr = process.communicate()
        stdout_path.write_text(stdout, encoding="utf-8")
        stderr_path.write_text(stderr, encoding="utf-8")
        return {
            "ok": False,
            "returncode": process.returncode,
            "timed_out": True,
            "stdout_path": str(stdout_path),
            "stderr_path": str(stderr_path),
            "stdout": stdout,
            "stderr_tail": stderr[-4000:],
        }


@contextmanager
def _exclusive_lock(path: Path):
    import fcntl

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _parse_json_stdout(result: Mapping[str, Any]) -> dict[str, Any]:
    raw = str(result.get("stdout") or "").strip()
    if not raw and result.get("stdout_path"):
        path = Path(str(result["stdout_path"]))
        if path.is_file():
            raw = path.read_text(encoding="utf-8").strip()
    if not raw:
        return {}
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


@dataclass(frozen=True)
class TaskPlan:
    run_id: str
    task_type: str
    executor_id: str
    normalized_request: dict[str, Any]
    registry_entry_sha256: str
    run_dir: Path
    details: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "tw.task.plan.v1",
            "run_id": self.run_id,
            "task_type": self.task_type,
            "executor_id": self.executor_id,
            "normalized_request": self.normalized_request,
            "registry_entry_sha256": self.registry_entry_sha256,
            "run_dir": str(self.run_dir),
            "details": self.details,
        }


class TaskDispatcher:
    """Validate and dispatch registered tasks without accepting executable paths."""

    def __init__(
        self,
        repo_root: Path,
        *,
        registry_path: Path | None = None,
        request_schema_path: Path | None = None,
        run_root: Path | None = None,
        command_runner: CommandRunner | None = None,
        workflow_runner: WorkflowRunner | None = None,
        now_taipei: Callable[[], datetime] | None = None,
    ) -> None:
        self.repo_root = Path(repo_root).resolve()
        self.registry_path = self._repo_file(
            registry_path or DEFAULT_REGISTRY, label="task registry"
        )
        self.request_schema_path = self._repo_file(
            request_schema_path or DEFAULT_REQUEST_SCHEMA,
            label="task request schema",
        )
        self.run_root = (
            Path(run_root).resolve()
            if run_root is not None
            else (self.repo_root / DEFAULT_RUN_ROOT).resolve()
        )
        self.command_runner = command_runner or _default_command_runner
        self.workflow_runner = workflow_runner or run_workflow
        self.now_taipei = now_taipei or (
            lambda: datetime.now(ZoneInfo("Asia/Taipei"))
        )
        self.registry = _load_document(self.registry_path)
        self.request_schema = _load_document(self.request_schema_path)
        self._validate_registry()

    def _repo_path(self, raw: str | Path, *, label: str) -> Path:
        path = Path(raw)
        resolved = path.resolve() if path.is_absolute() else (self.repo_root / path).resolve()
        try:
            resolved.relative_to(self.repo_root)
        except ValueError as exc:
            raise TaskRequestError(f"{label} must stay inside the repository") from exc
        return resolved

    def _repo_file(self, raw: str | Path, *, label: str) -> Path:
        resolved = self._repo_path(raw, label=label)
        if not resolved.is_file():
            raise TaskRequestError(f"{label} is missing: {resolved}")
        return resolved

    def _validate_registry(self) -> None:
        if self.registry.get("schema_version") != "tw.task.registry.v1":
            raise TaskRequestError("unsupported task registry schema_version")
        tasks = self.registry.get("tasks")
        if not isinstance(tasks, dict) or not tasks:
            raise TaskRequestError("task registry must contain tasks")
        for task_type, entry in tasks.items():
            if not isinstance(task_type, str) or not isinstance(entry, dict):
                raise TaskRequestError("task registry entry is invalid")
            expected = {
                "executor_id",
                "description",
                "defaults",
                "parameter_schema",
                "bindings",
            }
            unknown = sorted(set(entry) - expected)
            if unknown:
                raise TaskRequestError(
                    f"unknown task registry fields for {task_type}: {', '.join(unknown)}"
                )
            if entry.get("executor_id") not in SUPPORTED_EXECUTORS:
                raise TaskRequestError(f"unsupported task executor: {task_type}")
            if not isinstance(entry.get("defaults"), dict):
                raise TaskRequestError(f"task defaults must be an object: {task_type}")
            if not isinstance(entry.get("parameter_schema"), dict):
                raise TaskRequestError(f"task parameter schema is missing: {task_type}")
            if not isinstance(entry.get("bindings"), dict):
                raise TaskRequestError(f"task bindings must be an object: {task_type}")
            defaults_schema = dict(entry["parameter_schema"])
            defaults_schema.pop("required", None)
            _validation_error(
                entry["defaults"], defaults_schema, label=f"{task_type} defaults"
            )

    def _entry(self, task_type: str) -> dict[str, Any]:
        entry = (self.registry.get("tasks") or {}).get(task_type)
        if not isinstance(entry, dict):
            raise TaskRequestError(f"unregistered task_type: {task_type}")
        return entry

    def _normalize_request(
        self, request: Mapping[str, Any]
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        _validation_error(request, self.request_schema, label="task request")
        task_type = str(request["task_type"])
        entry = self._entry(task_type)
        parameters = {**entry["defaults"], **dict(request["parameters"])}
        _validation_error(
            parameters, entry["parameter_schema"], label=f"{task_type} parameters"
        )
        if task_type == "daily_update" and parameters.get("asof") == "auto":
            parameters["asof"] = self.now_taipei().date().isoformat()
        normalized = {
            "schema_version": "tw.task.request.v1",
            "task_type": task_type,
            "parameters": parameters,
        }
        if request.get("request_id"):
            normalized["request_id"] = str(request["request_id"])
        return normalized, entry

    def _daily_plan(
        self, parameters: Mapping[str, Any], bindings: Mapping[str, Any]
    ) -> dict[str, Any]:
        runner = self._repo_file(str(bindings.get("runner") or ""), label="daily runner")
        governance_path = self._repo_file(
            str(bindings.get("model_track_governance") or ""),
            label="model-track governance",
        )
        runtime_path = self._repo_file(
            str(bindings.get("model_track_runtime") or ""),
            label="model-track runtime",
        )
        governance = _load_document(governance_path)
        runtime = _load_document(runtime_path)
        tracks = governance.get("tracks") or {}
        runtime_tracks = runtime.get("tracks") or {}
        selected = list(parameters["model_track_ids"])
        unknown = sorted(set(selected) - set(tracks))
        if unknown:
            raise TaskRequestError(f"unknown daily model tracks: {', '.join(unknown)}")
        if set(runtime_tracks) != set(tracks):
            raise TaskRequestError("daily model-track governance/runtime mismatch")
        required = sorted(
            track_id
            for track_id, config in tracks.items()
            if isinstance(config, dict) and config.get("workflow_policy") == "required"
        )
        missing = sorted(set(required) - set(selected))
        if missing:
            raise TaskRequestError(
                f"daily task cannot omit required model tracks: {', '.join(missing)}"
            )
        stage_timeout = int(
            parameters.get("stage_timeout_seconds", parameters.get("timeout_seconds", 1800))
        )
        overall_timeout = int(
            parameters.get("overall_timeout_seconds", max(stage_timeout * 4, 7200))
        )
        if overall_timeout <= stage_timeout:
            raise TaskRequestError(
                "daily overall_timeout_seconds must exceed stage_timeout_seconds"
            )
        command = [
            sys.executable,
            str(runner.relative_to(self.repo_root)),
            "--asof",
            str(parameters["asof"]),
            "--finmind-scope",
            str(parameters["finmind_scope"]),
            "--max-workers",
            str(parameters["max_workers"]),
            "--timeout-seconds",
            str(stage_timeout),
            "--enable-model-signal-gate",
        ]
        for field, flag in (
            ("force", "--force"),
            ("skip_finmind", "--skip-finmind"),
            ("skip_qlib", "--skip-qlib"),
        ):
            if parameters[field] is True:
                command.append(flag)
        challenger_enabled = "model_a_plus_b_b19r2r" in selected
        if challenger_enabled:
            command.append("--enable-b19r2r-shadow")
        return {
            "command": command,
            "stage_timeout_seconds": stage_timeout,
            "overall_timeout_seconds": overall_timeout,
            "environment_overrides": {
                "TW_DAILY_AUTO_ENABLE_MODEL_SIGNAL_GATE": "true",
                "TW_DAILY_AUTO_ENABLE_B19R2R_SHADOW": (
                    "true" if challenger_enabled else "false"
                ),
            },
            "selected_model_track_ids": selected,
            "required_model_track_ids": required,
            "orchestration_config": str(runtime_path.relative_to(self.repo_root)),
            "delegates_side_effect_authority": True,
        }

    def _backtest_plan(
        self, parameters: Mapping[str, Any], bindings: Mapping[str, Any]
    ) -> dict[str, Any]:
        required_bindings = {
            name: self._repo_file(str(bindings.get(name) or ""), label=name)
            for name in (
                "runner",
                "model_tracks",
                "replay_policy",
                "modular_registry",
                "baseline_descriptor",
                "baseline_manifest",
                "price_store_manifest",
            )
        }
        tracks = (_load_document(required_bindings["model_tracks"]).get("tracks") or {})
        track_id = str(parameters["model_track_id"])
        track = tracks.get(track_id)
        if not isinstance(track, dict):
            raise TaskRequestError(f"unknown readonly model track: {track_id}")
        model_id = str(track.get("model_id") or "")
        replay_policy = _load_document(required_bindings["replay_policy"])
        if model_id not in (replay_policy.get("models") or {}):
            raise TaskRequestError(
                f"model track is not replay-enabled by policy: {track_id}"
            )
        modular_registry = _load_document(required_bindings["modular_registry"])
        selectable = (
            (modular_registry.get("strategies") or {}).get("production_selectable")
            or {}
        )
        strategy_rule = str(parameters["strategy_rule"])
        if strategy_rule not in selectable:
            raise TaskRequestError(
                f"strategy is not registered for readonly product replay: {strategy_rule}"
            )
        try:
            from scripts.build_tw_readonly_replay_window_artifact import validate_window

            validate_window(
                replay_policy,
                model_id,
                strategy_rule,
                str(parameters["start_date"]),
                str(parameters["end_date"]),
            )
        except Exception as exc:
            raise TaskRequestError(f"readonly backtest policy rejected request: {exc}") from exc
        return {
            "runner": str(required_bindings["runner"].relative_to(self.repo_root)),
            "model_track_id": track_id,
            "model_id": model_id,
            "strategy_rule": strategy_rule,
            "window_start": str(parameters["start_date"]),
            "window_end": str(parameters["end_date"]),
            "timeout_seconds": int(parameters["timeout_seconds"]),
            "bindings": {
                key: str(path.relative_to(self.repo_root))
                for key, path in required_bindings.items()
                if key != "runner"
            },
            "readonly_only": True,
            "product_index_admission": False,
            "no_apply": True,
        }

    def _workflow_plan(
        self, parameters: Mapping[str, Any], bindings: Mapping[str, Any]
    ) -> dict[str, Any]:
        spec = self._repo_file(
            str(bindings.get("workflow_spec") or ""), label="workflow spec"
        )
        mode = str(bindings.get("mode") or "")
        permissions = bindings.get("permissions")
        if not mode or not isinstance(permissions, list) or any(
            not isinstance(item, str) for item in permissions
        ):
            raise TaskRequestError("workflow task context binding is invalid")
        return {
            "workflow_spec": str(spec.relative_to(self.repo_root)),
            "mode": mode,
            "permissions": sorted(permissions),
            "asof": str(parameters["asof"]),
            "decision_cutoff": str(parameters["decision_cutoff"]),
        }

    def plan(self, request: Mapping[str, Any]) -> TaskPlan:
        normalized, entry = self._normalize_request(request)
        task_type = str(normalized["task_type"])
        executor_id = str(entry["executor_id"])
        parameters = normalized["parameters"]
        bindings = entry["bindings"]
        if executor_id == "daily_update_v1":
            details = self._daily_plan(parameters, bindings)
        elif executor_id == "readonly_backtest_v1":
            details = self._backtest_plan(parameters, bindings)
        elif executor_id == "workflow_spec_v1":
            details = self._workflow_plan(parameters, bindings)
        else:  # Registry validation keeps this branch unreachable.
            raise TaskRequestError(f"unsupported task executor: {executor_id}")
        entry_sha = _canonical_sha256(entry)
        identity_sha = _canonical_sha256(
            {"request": normalized, "registry_entry_sha256": entry_sha}
        )
        run_id = f"task_{task_type}_{identity_sha[:20]}"
        return TaskPlan(
            run_id=run_id,
            task_type=task_type,
            executor_id=executor_id,
            normalized_request=normalized,
            registry_entry_sha256=entry_sha,
            run_dir=self.run_root / task_type / run_id,
            details=details,
        )

    @staticmethod
    def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        temporary.replace(path)

    def _run_command(
        self,
        plan: TaskPlan,
        command: list[str],
        *,
        timeout: int,
        env: Mapping[str, str] | None = None,
        require_payload_ok: bool,
    ) -> tuple[bool, dict[str, Any], dict[str, Any]]:
        command_result = dict(
            self.command_runner(
                command,
                cwd=self.repo_root,
                stdout_path=plan.run_dir / "stdout.txt",
                stderr_path=plan.run_dir / "stderr.txt",
                timeout=timeout,
                env=env,
            )
        )
        payload = _parse_json_stdout(command_result)
        ok = command_result.get("ok") is True
        if require_payload_ok:
            ok = ok and payload.get("ok") is True
        summary = {
            key: value
            for key, value in command_result.items()
            if key not in {"stdout", "stderr"}
        }
        return ok, payload, summary

    def _execute_daily(self, plan: TaskPlan) -> dict[str, Any]:
        details = plan.details
        ok, payload, command = self._run_command(
            plan,
            list(details["command"]),
            timeout=int(details["overall_timeout_seconds"]),
            env=details["environment_overrides"],
            require_payload_ok=False,
        )
        return {
            "ok": ok,
            "status": "SUCCEEDED" if ok else "FAILED",
            "command": command,
            "daily_result": payload,
        }

    def _execute_backtest(self, plan: TaskPlan) -> dict[str, Any]:
        details = plan.details
        bindings = details["bindings"]
        output_root = plan.run_dir / "artifacts"
        command = [
            sys.executable,
            details["runner"],
            "--model-id",
            details["model_id"],
            "--strategy-rule",
            details["strategy_rule"],
            "--start",
            details["window_start"],
            "--end",
            details["window_end"],
            "--out-root",
            str(output_root),
            "--baseline-manifest",
            bindings["baseline_manifest"],
            "--policy",
            bindings["replay_policy"],
            "--registry",
            bindings["modular_registry"],
            "--baseline-descriptor",
            bindings["baseline_descriptor"],
            "--price-store",
            bindings["price_store_manifest"],
            "--json",
        ]
        ok, payload, command_result = self._run_command(
            plan,
            command,
            timeout=int(details["timeout_seconds"]),
            require_payload_ok=True,
        )
        return {
            "ok": ok,
            "status": "SUCCEEDED" if ok else "FAILED",
            "command": command_result,
            "artifact": payload,
        }

    def _execute_workflow(self, plan: TaskPlan) -> dict[str, Any]:
        details = plan.details
        context = ExecutionContext(
            mode=details["mode"],
            asof=details["asof"],
            decision_cutoff=details["decision_cutoff"],
            workspace=plan.run_dir / "workspace",
            permissions=frozenset(details["permissions"]),
        )
        result = self.workflow_runner(
            repo_root=self.repo_root,
            spec_path=self.repo_root / details["workflow_spec"],
            context=context,
        )
        record = dict(result.record)
        ok = result.status == "SUCCEEDED"
        return {
            "ok": ok,
            "status": result.status,
            "idempotent_workflow_reuse": bool(result.idempotent_reuse),
            "workflow_result": record,
        }

    def dispatch(self, request: Mapping[str, Any]) -> dict[str, Any]:
        plan = self.plan(request)
        plan.run_dir.mkdir(parents=True, exist_ok=True)
        with _exclusive_lock(plan.run_dir / ".task.lock"):
            result_path = plan.run_dir / "result.json"
            if plan.executor_id != "daily_update_v1" and result_path.is_file():
                existing = _load_document(result_path)
                if (
                    existing.get("schema_version") == TASK_RUN_SCHEMA
                    and existing.get("run_id") == plan.run_id
                    and existing.get("status") == "SUCCEEDED"
                    and existing.get("registry_entry_sha256")
                    == plan.registry_entry_sha256
                ):
                    return {**existing, "idempotent_reuse": True}
            self._write_json(
                plan.run_dir / "normalized_request.json", plan.normalized_request
            )
            self._write_json(plan.run_dir / "plan.json", plan.to_dict())
            started_at = (
                datetime.now(ZoneInfo("UTC")).replace(microsecond=0).isoformat()
            )
            try:
                if plan.executor_id == "daily_update_v1":
                    execution = self._execute_daily(plan)
                elif plan.executor_id == "readonly_backtest_v1":
                    execution = self._execute_backtest(plan)
                else:
                    execution = self._execute_workflow(plan)
            except Exception as exc:
                execution = {
                    "ok": False,
                    "status": "FAILED",
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                }
            record = {
                "schema_version": TASK_RUN_SCHEMA,
                "run_id": plan.run_id,
                "task_type": plan.task_type,
                "executor_id": plan.executor_id,
                "registry_entry_sha256": plan.registry_entry_sha256,
                "normalized_request": plan.normalized_request,
                "status": str(execution.get("status") or "FAILED"),
                "ok": execution.get("ok") is True,
                "started_at": started_at,
                "finished_at": datetime.now(ZoneInfo("UTC"))
                .replace(microsecond=0)
                .isoformat(),
                "run_dir": str(plan.run_dir),
                "execution": execution,
                "idempotent_reuse": False,
            }
            self._write_json(result_path, record)
            return record

    def recent_status(
        self, task_type: str | None = None, *, limit: int = 10
    ) -> dict[str, Any]:
        """Return recent task records without executing or mutating a task.

        Result files are atomically replaced by ``dispatch``. Reading them directly
        keeps this status path independent from task executors and safe to use from
        a health check or an operator shell.
        """
        if limit < 1 or limit > 100:
            raise TaskRequestError("status limit must be between 1 and 100")
        if task_type is not None:
            self._entry(task_type)
            task_types = [task_type]
        else:
            task_types = sorted(
                str(value) for value in (self.registry.get("tasks") or {})
            )

        records: list[dict[str, Any]] = []
        for current_type in task_types:
            task_root = self.run_root / current_type
            if not task_root.is_dir():
                continue
            for result_path in task_root.glob("*/result.json"):
                try:
                    record = _load_document(result_path)
                except TaskRequestError:
                    records.append(
                        {
                            "task_type": current_type,
                            "run_id": result_path.parent.name,
                            "status": "INVALID_RECORD",
                            "result_path": str(result_path),
                        }
                    )
                    continue
                if record.get("schema_version") != TASK_RUN_SCHEMA:
                    records.append(
                        {
                            "task_type": current_type,
                            "run_id": result_path.parent.name,
                            "status": "INVALID_RECORD",
                            "result_path": str(result_path),
                        }
                    )
                    continue
                records.append(
                    {
                        "task_type": record.get("task_type", current_type),
                        "run_id": record.get("run_id", result_path.parent.name),
                        "executor_id": record.get("executor_id"),
                        "status": record.get("status", "UNKNOWN"),
                        "ok": record.get("ok") is True,
                        "started_at": record.get("started_at"),
                        "finished_at": record.get("finished_at"),
                        "run_dir": record.get("run_dir", str(result_path.parent)),
                        "result_path": str(result_path),
                    }
                )

        records.sort(
            key=lambda item: (
                str(item.get("finished_at") or item.get("started_at") or ""),
                str(item.get("run_id") or ""),
            ),
            reverse=True,
        )
        return {
            "schema_version": "tw.task.status.v1",
            "task_type": task_type or "all",
            "run_root": str(self.run_root),
            "count": min(len(records), limit),
            "runs": records[:limit],
        }


def load_task_request(path: Path) -> dict[str, Any]:
    return _load_document(path)
