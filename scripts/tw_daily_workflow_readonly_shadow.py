from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping

import yaml

from tw_stock_workflow.run_registry import validate_run_record


WORKFLOW_ID = "replay_window.model_a_observation"
WORKFLOW_MODULE = "replay_window.observe"
WORKFLOW_PERMISSION = "replay.read"
WORKFLOW_TIMEOUT_SECONDS = 60
OBSERVED_ARTIFACT_ASOF = "2026-05-07"


CommandRunner = Callable[..., dict[str, Any]]


def _expected_workflow_identity(
    *, expected_model_id: str, expected_strategy_rule: str
) -> dict[str, Any]:
    return {
        "schema_version": "tw.workflow.spec.v1",
        "workflow_id": WORKFLOW_ID,
        "version": "1",
        "nodes": [
            {
                "id": "observe_model_a_replay_window",
                "module": WORKFLOW_MODULE,
                "needs": [],
                "policy": "required",
                "config": {
                    "model_id": expected_model_id,
                    "strategy_rule": expected_strategy_rule,
                    "window_start": "2026-01-01",
                    "window_end": OBSERVED_ARTIFACT_ASOF,
                    "status": "INDEXED_READONLY",
                    "min_count": 1,
                },
            }
        ],
    }


def _rel_path(path: Path, repo_root: Path) -> str:
    try:
        return str(path.resolve().relative_to(repo_root.resolve()))
    except ValueError:
        return str(path)


def _fingerprint(path: Path, repo_root: Path) -> dict[str, Any]:
    if not path.exists() or not path.is_file():
        return {
            "exists": False,
            "path": _rel_path(path, repo_root),
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
        "path": _rel_path(path, repo_root),
        "size": stat.st_size,
        "sha256": digest.hexdigest(),
        "mtime": datetime.fromtimestamp(stat.st_mtime, timezone.utc)
        .replace(microsecond=0)
        .isoformat(),
    }


def _fingerprints(
    paths: Mapping[str, Path], repo_root: Path
) -> dict[str, dict[str, Any]]:
    return {name: _fingerprint(path, repo_root) for name, path in paths.items()}


def _validate_spec(
    *,
    spec_path: Path,
    repo_root: Path,
    expected_model_id: str,
    expected_strategy_rule: str,
) -> dict[str, str]:
    if spec_path.is_symlink():
        raise ValueError("workflow readonly shadow spec may not be a symlink")
    try:
        spec_path.resolve().relative_to(repo_root.resolve())
    except ValueError as exc:
        raise ValueError(
            "workflow readonly shadow spec must remain inside the repository"
        ) from exc
    payload = yaml.safe_load(spec_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("workflow readonly shadow spec must be an object")
    nodes = payload.get("nodes")
    if not isinstance(nodes, list) or len(nodes) != 1 or not isinstance(nodes[0], dict):
        raise ValueError("workflow readonly shadow must contain exactly one node")
    node = nodes[0]
    if node.get("module") != WORKFLOW_MODULE:
        raise ValueError("workflow readonly shadow may only run replay_window.observe")
    if (
        node.get("id") != "observe_model_a_replay_window"
        or node.get("needs", []) != []
        or node.get("policy") != "required"
    ):
        raise ValueError("workflow readonly shadow node contract changed")
    normalized = {**payload, "nodes": [{**node, "needs": node.get("needs", [])}]}
    if normalized != _expected_workflow_identity(
        expected_model_id=expected_model_id,
        expected_strategy_rule=expected_strategy_rule,
    ):
        raise ValueError("workflow readonly shadow fixed observation config changed")
    return {
        "workflow_id": WORKFLOW_ID,
        "workflow_version": "1",
        "observed_artifact_asof": OBSERVED_ARTIFACT_ASOF,
    }


def _workspace(job_dir: Path) -> Path:
    if not job_dir.exists() or not job_dir.is_dir() or job_dir.is_symlink():
        raise ValueError("workflow readonly shadow job_dir must be a real directory")
    job_root = job_dir.resolve()
    workspace = job_dir / "workflow_readonly_shadow"
    if workspace.is_symlink():
        raise ValueError("workflow readonly shadow workspace may not be a symlink")
    try:
        workspace.resolve(strict=False).relative_to(job_root)
    except ValueError as exc:
        raise ValueError("workflow readonly shadow workspace escapes job_dir") from exc
    return workspace


def _read_runner_record(stdout_path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(stdout_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _observed_asof(record: dict[str, Any]) -> str:
    artifact_inputs = record.get("artifact_inputs")
    if isinstance(artifact_inputs, dict):
        for refs in artifact_inputs.values():
            if not isinstance(refs, list):
                continue
            for ref in refs:
                if (
                    isinstance(ref, dict)
                    and ref.get("artifact_type") == "ReadonlyReplayWindowArtifact"
                    and ref.get("asof")
                ):
                    return str(ref["asof"])
    return ""


def _validate_runner_path(workflow_runner_path: Path, repo_root: Path) -> None:
    expected = repo_root / "scripts/run_tw_stock_workflow.py"
    if (
        workflow_runner_path.is_symlink()
        or not workflow_runner_path.is_file()
        or workflow_runner_path.resolve() != expected.resolve()
    ):
        raise ValueError(
            "workflow readonly shadow runner must be the regular repository workflow CLI"
        )


def _load_and_validate_run_record(
    *,
    stdout_record: dict[str, Any],
    workspace: Path,
    daily_asof: str,
    decision_cutoff: str,
    expected_model_id: str,
    expected_strategy_rule: str,
    expected_workflow: dict[str, Any],
) -> tuple[dict[str, Any], str]:
    run_id = str(stdout_record.get("run_id") or "")
    if re.fullmatch(r"wf_[0-9a-f]{24}", run_id) is None:
        raise ValueError("workflow runner stdout has an invalid run_id")
    run_record_path = workspace / "runs" / f"{run_id}.json"
    if run_record_path.is_symlink() or not run_record_path.is_file():
        raise ValueError("workflow run record is missing or is not a regular file")
    try:
        run_record_path.resolve().relative_to(workspace.resolve())
    except ValueError as exc:
        raise ValueError("workflow run record escapes the job workspace") from exc
    try:
        record = json.loads(run_record_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("workflow run record is unreadable") from exc
    if not isinstance(record, dict):
        raise ValueError("workflow run record must be an object")
    record = validate_run_record(record, run_id)
    for field in ("workflow_id", "workflow_version", "run_id", "status"):
        if stdout_record.get(field) != record.get(field):
            raise ValueError(f"workflow stdout/run record {field} mismatch")
    if (
        record.get("workflow_id") != WORKFLOW_ID
        or record.get("workflow_version") != "1"
    ):
        raise ValueError("workflow run record identity is not allowed")
    identity_payload = record.get("identity_payload")
    if (
        not isinstance(identity_payload, dict)
        or identity_payload.get("workflow") != expected_workflow
    ):
        raise ValueError("workflow run record spec identity changed")
    if record.get("context") != {
        "mode": "readonly",
        "asof": daily_asof,
        "decision_cutoff": decision_cutoff,
        "workspace": str(workspace.resolve()),
        "permissions": [WORKFLOW_PERMISSION],
    }:
        raise ValueError("workflow run record context does not match this daily job")
    nodes = record.get("nodes")
    if not isinstance(nodes, dict) or set(nodes) != {"observe_model_a_replay_window"}:
        raise ValueError("workflow run record must contain the one observation node")
    node = nodes["observe_model_a_replay_window"]
    if not isinstance(node, dict) or node.get("module") != WORKFLOW_MODULE:
        raise ValueError("workflow run record contains a non-observation module")
    observed_asof = _observed_asof(record)
    if record.get("status") == "SUCCEEDED":
        output = node.get("output")
        if (
            not isinstance(output, dict)
            or output.get("full_replay_contract_admission") is not False
        ):
            raise ValueError("workflow observation admission must remain false")
        artifact_inputs = record.get("artifact_inputs")
        refs = (
            artifact_inputs.get("observe_model_a_replay_window")
            if isinstance(artifact_inputs, dict)
            else None
        )
        if (
            not isinstance(refs, list)
            or len(refs) != 1
            or not isinstance(refs[0], dict)
        ):
            raise ValueError(
                "workflow success requires exactly one replay artifact input"
            )
        ref = refs[0]
        metadata = ref.get("metadata")
        if (
            ref.get("artifact_type") != "ReadonlyReplayWindowArtifact"
            or ref.get("model_id") != expected_model_id
            or ref.get("asof") != OBSERVED_ARTIFACT_ASOF
            or ref.get("status") != "INDEXED_READONLY"
            or not isinstance(metadata, dict)
            or metadata.get("strategy_rule") != expected_strategy_rule
            or metadata.get("window_start") != "2026-01-01"
            or metadata.get("window_end") != OBSERVED_ARTIFACT_ASOF
            or metadata.get("full_replay_contract_status") != "HOLD"
        ):
            raise ValueError(
                "workflow observation artifact identity/HOLD contract changed"
            )
        observed_asof = str(ref["asof"])
    return record, observed_asof


def run_daily_workflow_readonly_shadow(
    *,
    job: dict[str, Any],
    job_dir: Path,
    asof: str,
    enabled: bool,
    repo_root: Path,
    python_executable: str,
    workflow_runner_path: Path,
    spec_path: Path,
    expected_model_id: str,
    expected_strategy_rule: str,
    protected_paths: Mapping[str, Path],
    pending_path: Path,
    installed_cron_path: Path,
    command_runner: CommandRunner,
) -> dict[str, Any]:
    mainline_status = str(job.get("status") or "")
    stdout_path = job_dir / "workflow_readonly_shadow_stdout.json"
    stderr_path = job_dir / "workflow_readonly_shadow_stderr.txt"
    result: dict[str, Any] = {
        "schema_version": "daily.workflow_readonly_shadow.v1",
        "enabled": bool(enabled),
        "attempted": False,
        "ok": not enabled,
        "status": "DISABLED_BY_DEFAULT" if not enabled else "NOT_ATTEMPTED",
        "mainline_blocking": False,
        "production_allowed": False,
        "no_apply": True,
        "workflow_id": WORKFLOW_ID,
        "workflow_version": "",
        "run_id": "",
        "workflow_status": "NOT_RUN",
        "daily_job_asof": asof,
        "observed_artifact_asof": OBSERVED_ARTIFACT_ASOF,
        "spec_path": _rel_path(spec_path, repo_root),
        "workspace": _rel_path(job_dir / "workflow_readonly_shadow", repo_root),
        "run_record_path": "",
        "stdout_path": _rel_path(stdout_path, repo_root),
        "stderr_path": _rel_path(stderr_path, repo_root),
        "permissions": [WORKFLOW_PERMISSION],
        "replay_candidate_execution": False,
        "automatic_recovery_triggered": False,
        "provider_refresh_triggered": False,
        "provider_publish_triggered": False,
        "accepted_latest_switch_triggered": False,
        "latest_pointer_write_performed": False,
        "pending_asof_write_performed": False,
        "model_training_triggered": False,
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
        "timeout": WORKFLOW_TIMEOUT_SECONDS,
        "error_type": "",
        "error": "",
    }
    if not enabled:
        return result

    try:
        result["protected_before"] = _fingerprints(protected_paths, repo_root)
        result["pending_before"] = _fingerprint(pending_path, repo_root)
        result["installed_cron_before"] = _fingerprint(installed_cron_path, repo_root)
        result.update(
            _validate_spec(
                spec_path=spec_path,
                repo_root=repo_root,
                expected_model_id=expected_model_id,
                expected_strategy_rule=expected_strategy_rule,
            )
        )
        _validate_runner_path(workflow_runner_path, repo_root)
        workspace = _workspace(job_dir)
        result["workspace"] = _rel_path(workspace, repo_root)
        decision_cutoff = str(job.get("finished_at") or "")
        if not decision_cutoff:
            raise ValueError("workflow readonly shadow requires job.finished_at")
        for output_path in (stdout_path, stderr_path):
            if output_path.is_symlink():
                raise ValueError(
                    "workflow readonly shadow stdout/stderr may not be a symlink"
                )
        argv = [
            python_executable,
            str(workflow_runner_path.relative_to(repo_root)),
            "--spec",
            str(spec_path.relative_to(repo_root)),
            "--mode",
            "readonly",
            "--asof",
            asof,
            "--decision-cutoff",
            decision_cutoff,
            "--workspace",
            str(workspace),
            "--permission",
            WORKFLOW_PERMISSION,
        ]
        result["attempted"] = True
        runner_result = command_runner(
            argv,
            cwd=repo_root,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            timeout=WORKFLOW_TIMEOUT_SECONDS,
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
            raise ValueError(
                "workflow runner stdout/stderr evidence path changed or became a symlink"
            )
        stdout_record = _read_runner_record(stdout_path)
        workflow_status = str(stdout_record.get("status") or "UNKNOWN")
        result["workflow_status"] = workflow_status
        result["run_id"] = str(stdout_record.get("run_id") or "")
        if result["run_id"]:
            result["run_record_path"] = _rel_path(
                workspace / "runs" / f"{result['run_id']}.json", repo_root
            )
        if int(runner_result.get("returncode", 1)) == 124:
            result.update(
                ok=False,
                status="TIMEOUT_NONBLOCKING",
                error_type="TimeoutExpired",
                error=f"workflow runner exceeded {WORKFLOW_TIMEOUT_SECONDS} seconds",
            )
        else:
            try:
                record, observed_asof = _load_and_validate_run_record(
                    stdout_record=stdout_record,
                    workspace=workspace,
                    daily_asof=asof,
                    decision_cutoff=decision_cutoff,
                    expected_model_id=expected_model_id,
                    expected_strategy_rule=expected_strategy_rule,
                    expected_workflow=_expected_workflow_identity(
                        expected_model_id=expected_model_id,
                        expected_strategy_rule=expected_strategy_rule,
                    ),
                )
                result["observed_artifact_asof"] = observed_asof
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
            result["pending_after"] = _fingerprint(pending_path, repo_root)
            result["installed_cron_after"] = _fingerprint(
                installed_cron_path, repo_root
            )
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
                    error="workflow readonly shadow observed a protected path mutation",
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
