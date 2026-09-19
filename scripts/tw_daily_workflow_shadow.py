from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping

import yaml

from tw_stock_workflow.run_registry import validate_run_record


CommandRunner = Callable[..., dict[str, Any]]
RecordValidator = Callable[[dict[str, Any], str], dict[str, Any]]
Precondition = Callable[[], dict[str, Any]]
TIMEOUT_SECONDS = 60


class WorkflowShadowBlocked(RuntimeError):
    pass


@dataclass(frozen=True)
class WorkflowShadowProfile:
    schema_version: str
    workflow_id: str
    workflow_version: str
    permission: str
    workspace_name: str
    stdout_name: str
    stderr_name: str
    spec_relative_path: str
    expected_workflow: dict[str, Any]
    disabled_observed_asof: str = ""
    pinned_sources: tuple[tuple[str, str], ...] = ()


def relative_path(path: Path, repo_root: Path) -> str:
    try:
        return str(path.resolve().relative_to(repo_root.resolve()))
    except ValueError:
        return str(path)


def fingerprint(path: Path, repo_root: Path) -> dict[str, Any]:
    if not path.exists() or not path.is_file():
        return {
            "exists": False,
            "path": relative_path(path, repo_root),
            "size": 0,
            "sha256": "",
            "mtime": "",
        }
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    stat = path.stat()
    return {
        "exists": True,
        "path": relative_path(path, repo_root),
        "size": stat.st_size,
        "sha256": digest.hexdigest(),
        "mtime": datetime.fromtimestamp(stat.st_mtime, timezone.utc)
        .replace(microsecond=0)
        .isoformat(),
    }


def _fingerprints(
    paths: Mapping[str, Path], repo_root: Path
) -> dict[str, dict[str, Any]]:
    return {name: fingerprint(path, repo_root) for name, path in paths.items()}


def _regular_pinned_file(
    path: Path, expected: Path, repo_root: Path, label: str
) -> None:
    if path.is_symlink() or not path.is_file() or path.resolve() != expected.resolve():
        noun = "workflow CLI" if label == "runner" else "file"
        raise ValueError(
            f"workflow shadow {label} must be the pinned regular repository {noun}"
        )
    path.resolve().relative_to(repo_root.resolve())


def _validate_spec(
    spec_path: Path, repo_root: Path, profile: WorkflowShadowProfile
) -> None:
    expected_spec_path = repo_root / profile.spec_relative_path
    _regular_pinned_file(spec_path, expected_spec_path, repo_root, "spec")
    payload = yaml.safe_load(spec_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("nodes"), list):
        raise ValueError("workflow shadow spec must be an object with nodes")
    nodes = [
        {**node, "needs": node.get("needs", [])}
        for node in payload["nodes"]
        if isinstance(node, dict)
    ]
    if (
        len(nodes) != len(payload["nodes"])
        or {**payload, "nodes": nodes} != profile.expected_workflow
    ):
        expected_modules = ", ".join(
            str(node["module"]) for node in profile.expected_workflow["nodes"]
        )
        raise ValueError(
            "workflow shadow fixed spec identity changed; "
            f"may only run {expected_modules}"
        )


def _workspace(job_dir: Path, name: str) -> Path:
    if not job_dir.exists() or not job_dir.is_dir() or job_dir.is_symlink():
        raise ValueError("workflow shadow job_dir must be a real directory")
    workspace = job_dir / name
    if workspace.is_symlink():
        raise ValueError("workflow shadow workspace may not be a symlink")
    workspace.resolve(strict=False).relative_to(job_dir.resolve())
    return workspace


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _persisted_record(
    *,
    stdout_record: dict[str, Any],
    workspace: Path,
    daily_asof: str,
    decision_cutoff: str,
    profile: WorkflowShadowProfile,
) -> dict[str, Any]:
    run_id = str(stdout_record.get("run_id") or "")
    run_path = workspace / "runs" / f"{run_id}.json"
    if run_path.is_symlink() or not run_path.is_file():
        raise ValueError("workflow run record is missing or is not a regular file")
    run_path.resolve().relative_to(workspace.resolve())
    record = validate_run_record(_read_json(run_path), run_id)
    for field in ("workflow_id", "workflow_version", "run_id", "status"):
        if stdout_record.get(field) != record.get(field):
            raise ValueError(f"workflow stdout/run record {field} mismatch")
    if (
        record["workflow_id"] != profile.workflow_id
        or record["workflow_version"] != profile.workflow_version
        or record["identity_payload"]["workflow"] != profile.expected_workflow
    ):
        raise ValueError("workflow run record spec identity changed")
    if record["context"] != {
        "mode": "readonly",
        "asof": daily_asof,
        "decision_cutoff": decision_cutoff,
        "workspace": str(workspace.resolve()),
        "permissions": [profile.permission],
    }:
        raise ValueError("workflow run record context does not match this daily job")
    return record


def run_daily_workflow_shadow(
    *,
    profile: WorkflowShadowProfile,
    record_validator: RecordValidator,
    job: dict[str, Any],
    job_dir: Path,
    asof: str,
    enabled: bool,
    repo_root: Path,
    python_executable: str,
    workflow_runner_path: Path,
    spec_path: Path,
    protected_paths: Mapping[str, Path],
    pending_path: Path,
    installed_cron_path: Path,
    command_runner: CommandRunner,
    precondition: Precondition | None = None,
) -> dict[str, Any]:
    mainline_status = str(job.get("status") or "")
    workspace = job_dir / profile.workspace_name
    stdout_path = job_dir / profile.stdout_name
    stderr_path = job_dir / profile.stderr_name
    result: dict[str, Any] = {
        "schema_version": profile.schema_version,
        "enabled": bool(enabled),
        "attempted": False,
        "ok": not enabled,
        "status": "DISABLED_BY_DEFAULT" if not enabled else "NOT_ATTEMPTED",
        "mainline_blocking": False,
        "production_allowed": False,
        "no_apply": True,
        "workflow_id": profile.workflow_id,
        "workflow_version": "",
        "run_id": "",
        "workflow_status": "NOT_RUN",
        "daily_job_asof": asof,
        "observed_artifact_asof": profile.disabled_observed_asof,
        "spec_path": relative_path(spec_path, repo_root),
        "workspace": relative_path(workspace, repo_root),
        "run_record_path": "",
        "stdout_path": relative_path(stdout_path, repo_root),
        "stderr_path": relative_path(stderr_path, repo_root),
        "permissions": [profile.permission],
        "replay_candidate_execution": False,
        "automatic_recovery_triggered": False,
        "provider_refresh_triggered": False,
        "provider_publish_triggered": False,
        "accepted_latest_switch_triggered": False,
        "latest_pointer_write_performed": False,
        "pending_asof_write_performed": False,
        "model_training_triggered": False,
        "model_scoring_triggered": False,
        "trading_triggered": False,
        "mainline_status_before": mainline_status,
        "mainline_status_after": mainline_status,
        "protected_before": {},
        "protected_after": {},
        "protected_unchanged": True,
        "pending_before": {},
        "pending_after": {},
        "pending_unchanged": True,
        "installed_cron_before": {},
        "installed_cron_after": {},
        "installed_cron_unchanged": True,
        "runner_returncode": None,
        "timeout": TIMEOUT_SECONDS,
        "error_type": "",
        "error": "",
    }
    if not enabled:
        return result
    try:
        result["protected_before"] = _fingerprints(protected_paths, repo_root)
        result["pending_before"] = fingerprint(pending_path, repo_root)
        result["installed_cron_before"] = fingerprint(installed_cron_path, repo_root)
        if precondition is not None:
            result.update(precondition())
        _validate_spec(spec_path, repo_root, profile)
        result["workflow_version"] = profile.workflow_version
        _regular_pinned_file(
            workflow_runner_path,
            repo_root / "scripts/run_tw_stock_workflow.py",
            repo_root,
            "runner",
        )
        workspace = _workspace(job_dir, profile.workspace_name)
        decision_cutoff = str(job.get("finished_at") or "")
        if not decision_cutoff:
            raise ValueError("workflow shadow requires job.finished_at")
        argv = [
            python_executable,
            str(workflow_runner_path.relative_to(repo_root)),
            "--spec",
            profile.spec_relative_path,
            "--mode",
            "readonly",
            "--asof",
            asof,
            "--decision-cutoff",
            decision_cutoff,
            "--workspace",
            str(workspace),
            "--permission",
            profile.permission,
        ]
        for flag, relative_source in profile.pinned_sources:
            source = repo_root / relative_source
            _regular_pinned_file(source, source, repo_root, flag)
            argv.extend((flag, relative_source))
        for output in (stdout_path, stderr_path):
            if output.is_symlink():
                raise ValueError("workflow shadow stdout/stderr may not be a symlink")
        result["attempted"] = True
        runner_result = command_runner(
            argv,
            cwd=repo_root,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            timeout=TIMEOUT_SECONDS,
            env={"PYTHONPATH": str(repo_root)},
        )
        result["runner_returncode"] = runner_result.get("returncode")
        if (
            Path(str(runner_result.get("stdout_path") or "")).resolve()
            != stdout_path.resolve()
            or Path(str(runner_result.get("stderr_path") or "")).resolve()
            != stderr_path.resolve()
            or stdout_path.is_symlink()
            or stderr_path.is_symlink()
        ):
            raise ValueError("workflow runner stdout/stderr evidence path changed")
        stdout_record = _read_json(stdout_path)
        result["workflow_status"] = str(stdout_record.get("status") or "UNKNOWN")
        result["run_id"] = str(stdout_record.get("run_id") or "")
        if result["run_id"]:
            result["run_record_path"] = relative_path(
                workspace / "runs" / f"{result['run_id']}.json", repo_root
            )
        if int(runner_result.get("returncode", 1)) == 124:
            result.update(
                ok=False,
                status="TIMEOUT_NONBLOCKING",
                error_type="TimeoutExpired",
                error=f"workflow runner exceeded {TIMEOUT_SECONDS} seconds",
            )
        else:
            try:
                record = _persisted_record(
                    stdout_record=stdout_record,
                    workspace=workspace,
                    daily_asof=asof,
                    decision_cutoff=decision_cutoff,
                    profile=profile,
                )
                result.update(record_validator(record, asof))
                workflow_status = str(record["status"])
                result["workflow_status"] = workflow_status
            except Exception as exc:
                result.update(
                    ok=False,
                    status="FAILED_NONBLOCKING",
                    error_type="InvalidWorkflowRunnerOutput",
                    error=str(exc),
                )
            else:
                if workflow_status == "SUCCEEDED" and bool(runner_result.get("ok")):
                    result.update(ok=True, status="SUCCEEDED_NONBLOCKING")
                elif workflow_status == "BLOCKED":
                    result.update(ok=False, status="BLOCKED_NONBLOCKING")
                else:
                    result.update(ok=False, status="FAILED_NONBLOCKING")
    except WorkflowShadowBlocked as exc:
        result.update(
            ok=False,
            status="BLOCKED_NONBLOCKING",
            error_type=type(exc).__name__,
            error=str(exc),
        )
    except Exception as exc:
        result.update(
            ok=False,
            status="ERROR_NONBLOCKING",
            error_type=type(exc).__name__,
            error=str(exc),
        )
    finally:
        try:
            result["protected_after"] = _fingerprints(protected_paths, repo_root)
            result["pending_after"] = fingerprint(pending_path, repo_root)
            result["installed_cron_after"] = fingerprint(installed_cron_path, repo_root)
            result["protected_unchanged"] = (
                result["protected_before"] == result["protected_after"]
            )
            result["pending_unchanged"] = (
                result["pending_before"] == result["pending_after"]
            )
            result["installed_cron_unchanged"] = (
                result["installed_cron_before"] == result["installed_cron_after"]
            )
            if not all(
                (
                    result["protected_unchanged"],
                    result["pending_unchanged"],
                    result["installed_cron_unchanged"],
                )
            ):
                result.update(
                    ok=False,
                    status="FAILED_NONBLOCKING",
                    error_type="ReadonlyBoundaryChanged",
                    error="workflow shadow observed a protected path mutation",
                )
        except Exception as exc:
            result.update(
                ok=False,
                status="ERROR_NONBLOCKING",
                error_type=type(exc).__name__,
                error=str(exc),
            )
        result["mainline_status_after"] = str(job.get("status") or "")
    return result
