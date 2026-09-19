from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

from scripts.tw_daily_workflow_shadow import (
    TIMEOUT_SECONDS,
    CommandRunner,
    WorkflowShadowProfile,
    WorkflowShadowBlocked,
    run_daily_workflow_shadow,
)


WORKFLOW_ID = "research_history.model_a_observation"
WORKFLOW_MODULE = "research_history.observe"
WORKFLOW_PERMISSION = "artifact.read"
WORKFLOW_TIMEOUT_SECONDS = TIMEOUT_SECONDS
WORKFLOW_SPEC_RELATIVE_PATH = "configs/workflows/research_history_observation.yaml"
HISTORY_INDEX_RELATIVE_PATH = "data_tw/catalog/research_data_history/index.json"
SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
JOB_ID_PATTERN = re.compile(r"[A-Za-z0-9._-]+")


def _is_canonical_repo_relative_path(value: Any) -> bool:
    if not isinstance(value, str) or not value:
        return False
    path = PurePosixPath(value)
    return not path.is_absolute() and ".." not in path.parts and str(path) == value


def _expected_workflow_identity(expected_model_id: str) -> dict[str, Any]:
    return {
        "schema_version": "tw.workflow.spec.v1",
        "workflow_id": WORKFLOW_ID,
        "version": "1",
        "nodes": [
            {
                "id": "observe_model_a_input",
                "module": WORKFLOW_MODULE,
                "needs": [],
                "policy": "required",
                "config": {
                    "artifact_type": "ModelInferenceInput",
                    "model_id": expected_model_id,
                    "status": "READY",
                    "min_count": 1,
                },
            },
            {
                "id": "observe_model_a_signal",
                "module": WORKFLOW_MODULE,
                "needs": ["observe_model_a_input"],
                "policy": "required",
                "config": {
                    "artifact_type": "ModelSignalArtifact",
                    "model_id": expected_model_id,
                    "status": "READY",
                    "min_count": 1,
                    "require_same_run_id": True,
                },
            },
        ],
    }


def _validate_file_records(
    metadata: dict[str, Any], *, slot: str, data_filename: str, artifact_path: str
) -> dict[str, dict[str, Any]]:
    day_manifest = metadata.get("history_day_manifest")
    if (
        not isinstance(day_manifest, dict)
        or set(day_manifest) != {"path", "size_bytes", "sha256"}
        or not _is_canonical_repo_relative_path(day_manifest.get("path"))
        or not isinstance(day_manifest.get("size_bytes"), int)
        or isinstance(day_manifest.get("size_bytes"), bool)
        or day_manifest["size_bytes"] < 0
        or SHA256_PATTERN.fullmatch(str(day_manifest.get("sha256") or "")) is None
    ):
        raise ValueError("workflow Model A history day manifest identity is incomplete")
    files = metadata.get("declared_files")
    required = {"manifest.json", "validator_report.json", data_filename}
    if not isinstance(files, dict) or not required.issubset(files):
        raise ValueError(f"workflow Model A {slot} declared files are incomplete")
    for name, record in files.items():
        if (
            not isinstance(name, str)
            or not isinstance(record, dict)
            or set(record) != {"path", "size_bytes", "sha256"}
            or not _is_canonical_repo_relative_path(record.get("path"))
            or not isinstance(record.get("size_bytes"), int)
            or isinstance(record.get("size_bytes"), bool)
            or record["size_bytes"] < 0
            or SHA256_PATTERN.fullmatch(str(record.get("sha256") or "")) is None
        ):
            raise ValueError(
                f"workflow Model A {slot} declared file identity is invalid"
            )
        expected_path = str(PurePosixPath(artifact_path) / name)
        if record["path"] != expected_path:
            raise ValueError(
                f"workflow Model A {slot} declared file path/name mismatch"
            )
    return files


def _validate_ref(
    ref: Any,
    *,
    artifact_type: str,
    slot: str,
    data_filename: str,
    expected_model_id: str,
    daily_asof: str,
) -> str:
    if not isinstance(ref, dict):
        raise ValueError(f"workflow Model A {slot} reference must be an object")
    metadata = ref.get("metadata")
    if (
        ref.get("adapter_id") != "research_data_history.v1"
        or ref.get("artifact_type") != artifact_type
        or ref.get("model_id") != expected_model_id
        or ref.get("asof") != daily_asof
        or ref.get("status") != "READY"
        or not isinstance(ref.get("run_id"), str)
        or not ref["run_id"]
        or not _is_canonical_repo_relative_path(ref.get("path"))
        or not isinstance(metadata, dict)
        or metadata.get("history_slot") != slot
        or metadata.get("history_day_status")
        not in {"READY_MODELA_ONLY", "READY_MODELA_MODELB"}
        or metadata.get("production_allowed") is not False
        or metadata.get("no_apply") is not True
        or metadata.get("mainline_blocking") is not False
    ):
        raise ValueError(f"workflow Model A {slot} identity/safety boundary changed")
    files = _validate_file_records(
        metadata,
        slot=slot,
        data_filename=data_filename,
        artifact_path=str(ref["path"]),
    )
    manifest = files["manifest.json"]
    if (
        ref.get("manifest_path") != manifest["path"]
        or ref.get("manifest_sha256") != manifest["sha256"]
    ):
        raise ValueError(f"workflow Model A {slot} manifest identity is inconsistent")
    return str(ref["run_id"])


def _validate_model_a_record(
    record: dict[str, Any],
    daily_asof: str,
    *,
    expected_model_id: str,
    expected_day_manifest: dict[str, Any],
    verify_current_manifest: Any,
) -> dict[str, Any]:
    if verify_current_manifest() != expected_day_manifest:
        raise ValueError("workflow current day manifest changed during observation")
    expected_nodes = {"observe_model_a_input", "observe_model_a_signal"}
    nodes = record.get("nodes")
    artifact_inputs = record.get("artifact_inputs")
    if not isinstance(nodes, dict) or set(nodes) != expected_nodes:
        raise ValueError("workflow run record must contain exactly two Model A nodes")
    if not isinstance(artifact_inputs, dict) or set(artifact_inputs) != expected_nodes:
        raise ValueError(
            "workflow run record must contain exactly two Model A input sets"
        )
    if any(
        not isinstance(nodes[node_id], dict)
        or nodes[node_id].get("module") != WORKFLOW_MODULE
        for node_id in expected_nodes
    ):
        raise ValueError("workflow run record contains a non-observation module")
    if record.get("status") != "SUCCEEDED":
        return {"observed_artifact_asof": ""}

    input_refs = artifact_inputs["observe_model_a_input"]
    signal_refs = artifact_inputs["observe_model_a_signal"]
    if not isinstance(input_refs, list) or len(input_refs) != 1:
        raise ValueError(
            "workflow success requires exactly one Model A input reference"
        )
    if not isinstance(signal_refs, list) or len(signal_refs) != 1:
        raise ValueError(
            "workflow success requires exactly one Model A signal reference"
        )
    input_run_id = _validate_ref(
        input_refs[0],
        artifact_type="ModelInferenceInput",
        slot="inference_input",
        data_filename="inference_frame.csv",
        expected_model_id=expected_model_id,
        daily_asof=daily_asof,
    )
    signal_run_id = _validate_ref(
        signal_refs[0],
        artifact_type="ModelSignalArtifact",
        slot="signal",
        data_filename="signals.csv",
        expected_model_id=expected_model_id,
        daily_asof=daily_asof,
    )
    if input_run_id != signal_run_id:
        raise ValueError("workflow Model A input and signal run_id differ")
    input_ref = input_refs[0]
    signal_ref = signal_refs[0]
    input_day_manifest = input_ref["metadata"]["history_day_manifest"]
    signal_day_manifest = signal_ref["metadata"]["history_day_manifest"]
    if (
        input_day_manifest != signal_day_manifest
        or input_day_manifest != expected_day_manifest
    ):
        raise ValueError("workflow Model A refs do not bind the current day manifest")
    expected_queries = {
        "observe_model_a_input": {
            "artifact_type": "ModelInferenceInput",
            "model_id": expected_model_id,
            "asof": daily_asof,
            "status": "READY",
        },
        "observe_model_a_signal": {
            "artifact_type": "ModelSignalArtifact",
            "model_id": expected_model_id,
            "asof": daily_asof,
            "status": "READY",
        },
    }
    expected_refs = {
        "observe_model_a_input": input_refs,
        "observe_model_a_signal": signal_refs,
    }
    for node_id in expected_nodes:
        output = nodes[node_id].get("output")
        if (
            nodes[node_id].get("status") != "SUCCEEDED"
            or not isinstance(output, dict)
            or output.get("count") != 1
            or output.get("query") != expected_queries[node_id]
            or output.get("artifacts") != expected_refs[node_id]
        ):
            raise ValueError(f"workflow Model A node output changed: {node_id}")
    return {"observed_artifact_asof": daily_asof, "model_a_run_id": input_run_id}


def _current_materialization_manifest(
    job: dict[str, Any], *, job_dir: Path, daily_asof: str, repo_root: Path
) -> dict[str, Any]:
    history = job.get("research_data_history")
    expected_job_id = str(job.get("job_id") or job_dir.name)
    if (
        not isinstance(history, dict)
        or history.get("enabled") is not True
        or history.get("attempted") is not True
        or history.get("ok") is not True
        or history.get("status") not in {"READY_MODELA_ONLY", "READY_MODELA_MODELB"}
        or history.get("asof") != daily_asof
        or history.get("job_id") != expected_job_id
        or not isinstance(history.get("model_a"), dict)
        or JOB_ID_PATTERN.fullmatch(expected_job_id) is None
    ):
        raise WorkflowShadowBlocked(
            "current daily research history materialization is not READY"
        )
    manifest_path = history.get("manifest_path")
    expected_path = (
        f"data_tw/catalog/research_data_history/{daily_asof}/{expected_job_id}.json"
    )
    if manifest_path != expected_path or not _is_canonical_repo_relative_path(
        manifest_path
    ):
        raise WorkflowShadowBlocked(
            "current daily research history manifest path is not the expected job binding"
        )
    candidate = repo_root / expected_path
    try:
        if candidate.is_symlink() or not candidate.is_file():
            raise ValueError("day manifest is missing or is not a regular file")
        path = candidate.resolve(strict=True)
        if path.relative_to(repo_root.resolve()) != PurePosixPath(expected_path):
            raise ValueError("day manifest escapes repository or is not canonical")
        content = path.read_bytes()
        manifest = json.loads(content)
    except (OSError, ValueError, TypeError) as exc:
        raise ValueError(
            f"invalid current daily research history manifest: {exc}"
        ) from exc
    if (
        not isinstance(manifest, dict)
        or manifest.get("schema_version") != "tw.research_data_history.day.v1"
        or manifest.get("asof") != daily_asof
        or manifest.get("job_id") != expected_job_id
        or manifest.get("status") != history["status"]
        or manifest.get("model_a") != history["model_a"]
        or manifest.get("production_allowed") is not False
        or manifest.get("no_apply") is not True
        or manifest.get("mainline_blocking") is not False
    ):
        raise ValueError("current daily research history manifest identity changed")
    return {
        "path": expected_path,
        "size_bytes": len(content),
        "sha256": hashlib.sha256(content).hexdigest(),
    }


def run_daily_model_a_signal_shadow(
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
    protected_paths: Mapping[str, Path],
    pending_path: Path,
    installed_cron_path: Path,
    command_runner: CommandRunner,
) -> dict[str, Any]:
    binding: dict[str, dict[str, Any]] = {}
    raw_job_id = str(job.get("job_id") or job_dir.name)
    protected_job_id = (
        raw_job_id
        if JOB_ID_PATTERN.fullmatch(raw_job_id) is not None
        else "__invalid_job_id__"
    )

    def current_manifest() -> dict[str, Any]:
        return _current_materialization_manifest(
            job, job_dir=job_dir, daily_asof=asof, repo_root=repo_root
        )

    def precondition() -> dict[str, Any]:
        identity = current_manifest()
        binding["manifest"] = identity
        return {"materialized_history_manifest": identity}

    profile = WorkflowShadowProfile(
        schema_version="daily.workflow_model_a_signal_shadow.v1",
        workflow_id=WORKFLOW_ID,
        workflow_version="1",
        permission=WORKFLOW_PERMISSION,
        workspace_name="workflow_model_a_signal_shadow",
        stdout_name="workflow_model_a_signal_shadow_stdout.json",
        stderr_name="workflow_model_a_signal_shadow_stderr.txt",
        spec_relative_path=WORKFLOW_SPEC_RELATIVE_PATH,
        expected_workflow=_expected_workflow_identity(expected_model_id),
        pinned_sources=(("--history-index", HISTORY_INDEX_RELATIVE_PATH),),
    )
    return run_daily_workflow_shadow(
        profile=profile,
        record_validator=lambda record, daily_asof: _validate_model_a_record(
            record,
            daily_asof,
            expected_model_id=expected_model_id,
            expected_day_manifest=binding["manifest"],
            verify_current_manifest=current_manifest,
        ),
        job=job,
        job_dir=job_dir,
        asof=asof,
        enabled=enabled,
        repo_root=repo_root,
        python_executable=python_executable,
        workflow_runner_path=workflow_runner_path,
        spec_path=spec_path,
        protected_paths={
            **protected_paths,
            "research_history_index": repo_root / HISTORY_INDEX_RELATIVE_PATH,
            "research_history_day_manifest": repo_root
            / "data_tw/catalog/research_data_history"
            / asof
            / f"{protected_job_id}.json",
        },
        pending_path=pending_path,
        installed_cron_path=installed_cron_path,
        command_runner=command_runner,
        precondition=precondition,
    )
