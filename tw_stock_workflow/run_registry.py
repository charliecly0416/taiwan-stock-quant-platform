from __future__ import annotations

import fcntl
import hashlib
import json
import os
import re
import tempfile
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator

from .types import WorkflowError, validate_asof


RUN_ID_PATTERN = re.compile(r"wf_[0-9a-f]{24}")
SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
RUN_STATUSES = {"RUNNING", "SUCCEEDED", "BLOCKED", "FAILED"}
TERMINAL_STATUSES = RUN_STATUSES - {"RUNNING"}
STAGE_STATUSES = {"SUCCEEDED", "BLOCKED", "FAILED", "SKIPPED"}
STAGE_POLICIES = {"required", "optional", "nonblocking"}
BASE_RECORD_FIELDS = {
    "schema_version",
    "run_id",
    "identity_sha256",
    "identity_payload",
    "workflow_id",
    "workflow_version",
    "context",
    "artifact_inputs",
    "artifact_input_errors",
    "status",
    "started_at",
    "nodes",
}
STAGE_FIELDS = {
    "status",
    "policy",
    "module",
    "output",
    "reason",
    "dependencies",
    "dependency_causes",
    "root_cause",
    "missing_permissions",
    "error_type",
    "error",
}


class RunRegistryError(WorkflowError):
    pass


def canonical_json(payload: Any) -> bytes:
    try:
        return json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise RunRegistryError("run identity must be JSON serializable") from exc


def identity_sha256(identity_payload: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json(identity_payload)).hexdigest()


def run_id_for_identity(identity_payload: dict[str, Any]) -> tuple[str, str]:
    digest = identity_sha256(identity_payload)
    return f"wf_{digest[:24]}", digest


def validate_run_id(run_id: str) -> str:
    if not isinstance(run_id, str) or RUN_ID_PATTERN.fullmatch(run_id) is None:
        raise RunRegistryError(f"invalid canonical run_id: {run_id!r}")
    return run_id


def _validate_timestamp(value: Any, field: str) -> None:
    if not isinstance(value, str) or not value:
        raise RunRegistryError(f"run record {field} must be a non-empty timestamp")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise RunRegistryError(f"run record {field} is not an ISO timestamp") from exc
    if parsed.tzinfo is None:
        raise RunRegistryError(f"run record {field} must include a timezone")


def _validate_context(context: Any) -> None:
    required = {"mode", "asof", "decision_cutoff", "workspace", "permissions"}
    if not isinstance(context, dict) or set(context) != required:
        raise RunRegistryError("run record context has an invalid structure")
    if not isinstance(context["mode"], str) or not context["mode"]:
        raise RunRegistryError("run record context.mode must be a non-empty string")
    if not isinstance(context["workspace"], str) or not context["workspace"]:
        raise RunRegistryError(
            "run record context.workspace must be a non-empty string"
        )
    try:
        validate_asof(context["asof"])
    except WorkflowError as exc:
        raise RunRegistryError("run record context.asof is invalid") from exc
    _validate_timestamp(context["decision_cutoff"], "context.decision_cutoff")
    permissions = context["permissions"]
    if (
        not isinstance(permissions, list)
        or any(not isinstance(item, str) or not item for item in permissions)
        or permissions != sorted(set(permissions))
    ):
        raise RunRegistryError(
            "run record context.permissions must be a sorted unique string list"
        )


def _validate_artifact_inputs(value: Any) -> None:
    required = {
        "adapter_id",
        "artifact_type",
        "model_id",
        "asof",
        "status",
        "run_id",
        "path",
        "manifest_path",
        "manifest_sha256",
        "metadata",
    }
    if not isinstance(value, dict):
        raise RunRegistryError("run record artifact_inputs must be an object")
    for node_id, refs in value.items():
        if not isinstance(node_id, str) or not isinstance(refs, list):
            raise RunRegistryError(
                "run record artifact_inputs has an invalid node entry"
            )
        for ref in refs:
            if not isinstance(ref, dict) or set(ref) != required:
                raise RunRegistryError(
                    "run record artifact reference has an invalid structure"
                )
            if any(
                not isinstance(ref[key], str) or not ref[key]
                for key in required - {"metadata"}
            ):
                raise RunRegistryError(
                    "run record artifact reference has an empty identity field"
                )
            if not isinstance(ref["metadata"], dict):
                raise RunRegistryError("run record artifact metadata must be an object")
            if SHA256_PATTERN.fullmatch(ref["manifest_sha256"]) is None:
                raise RunRegistryError("run record artifact manifest_sha256 is invalid")
            try:
                validate_asof(ref["asof"])
            except WorkflowError as exc:
                raise RunRegistryError("run record artifact asof is invalid") from exc


def _validate_artifact_errors(value: Any) -> None:
    if not isinstance(value, dict):
        raise RunRegistryError("run record artifact_input_errors must be an object")
    for node_id, error in value.items():
        if (
            not isinstance(node_id, str)
            or not isinstance(error, dict)
            or set(error) != {"error_type", "error"}
            or any(not isinstance(error[key], str) or not error[key] for key in error)
        ):
            raise RunRegistryError(
                "run record artifact input error has an invalid structure"
            )


def _workflow_nodes(identity_payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    workflow = identity_payload.get("workflow")
    if not isinstance(workflow, dict) or set(workflow) != {
        "schema_version",
        "workflow_id",
        "version",
        "nodes",
    }:
        raise RunRegistryError("run identity workflow has an invalid structure")
    if workflow["schema_version"] != "tw.workflow.spec.v1":
        raise RunRegistryError("run identity workflow schema_version is invalid")
    if not isinstance(workflow["workflow_id"], str) or not workflow["workflow_id"]:
        raise RunRegistryError("run identity workflow_id is invalid")
    if not isinstance(workflow["version"], str) or not workflow["version"]:
        raise RunRegistryError("run identity workflow version is invalid")
    if not isinstance(workflow["nodes"], list) or not workflow["nodes"]:
        raise RunRegistryError("run identity workflow nodes are invalid")
    result: dict[str, dict[str, Any]] = {}
    for node in workflow["nodes"]:
        if not isinstance(node, dict):
            raise RunRegistryError("run identity workflow node is invalid")
        node_id = node.get("id")
        if not isinstance(node_id, str) or not node_id or node_id in result:
            raise RunRegistryError("run identity workflow node id is invalid")
        if node.get("policy") not in STAGE_POLICIES:
            raise RunRegistryError("run identity workflow node policy is invalid")
        if not isinstance(node.get("module"), str) or not node["module"]:
            raise RunRegistryError("run identity workflow node module is invalid")
        result[node_id] = node
    return result


def _validate_stage(stage: Any, declared: dict[str, Any]) -> None:
    if not isinstance(stage, dict) or not {
        "status",
        "policy",
        "module",
    }.issubset(stage):
        raise RunRegistryError("run record stage result is incomplete")
    if set(stage) - STAGE_FIELDS:
        raise RunRegistryError("run record stage result has unknown fields")
    if stage["status"] not in STAGE_STATUSES:
        raise RunRegistryError("run record stage status is invalid")
    if stage["policy"] != declared["policy"] or stage["module"] != declared["module"]:
        raise RunRegistryError(
            "run record stage contract does not match workflow identity"
        )
    status = stage["status"]
    if status == "SUCCEEDED" and not isinstance(stage.get("output"), dict):
        raise RunRegistryError("successful stage must contain an output object")
    if status == "FAILED" and (
        not isinstance(stage.get("error_type"), str)
        or not isinstance(stage.get("error"), str)
        or stage.get("root_cause") != "FAILED"
    ):
        raise RunRegistryError("failed stage evidence is incomplete")
    if status == "BLOCKED" and (
        not isinstance(stage.get("reason"), str) or stage.get("root_cause") != "BLOCKED"
    ):
        raise RunRegistryError("blocked stage evidence is incomplete")
    if status == "SKIPPED" and (
        stage.get("reason") != "dependency_not_succeeded"
        or not isinstance(stage.get("dependencies"), dict)
        or not isinstance(stage.get("dependency_causes"), dict)
        or stage.get("root_cause") not in {"FAILED", "BLOCKED"}
    ):
        raise RunRegistryError("skipped stage evidence is incomplete")


def _expected_terminal_status(nodes: dict[str, dict[str, Any]]) -> str:
    required = [stage for stage in nodes.values() if stage["policy"] == "required"]
    if any(
        stage["status"] == "FAILED"
        or (stage["status"] == "SKIPPED" and stage.get("root_cause") == "FAILED")
        for stage in required
    ):
        return "FAILED"
    if any(stage["status"] in {"BLOCKED", "SKIPPED"} for stage in required):
        return "BLOCKED"
    return "SUCCEEDED"


def validate_run_record(
    record: Any, expected_run_id: str | None = None
) -> dict[str, Any]:
    if not isinstance(record, dict):
        raise RunRegistryError("run registry entry must be an object")
    status = record.get("status")
    if status not in RUN_STATUSES:
        raise RunRegistryError("run record status is invalid")
    expected_fields = BASE_RECORD_FIELDS | (
        {"finished_at"} if status in TERMINAL_STATUSES else set()
    )
    if set(record) != expected_fields:
        raise RunRegistryError("run record fields do not match the required schema")
    if record["schema_version"] != "tw.workflow.run.v1":
        raise RunRegistryError("run record schema_version is invalid")
    run_id = validate_run_id(record["run_id"])
    if expected_run_id is not None and run_id != validate_run_id(expected_run_id):
        raise RunRegistryError("run registry identity mismatch")
    identity_payload = record["identity_payload"]
    if not isinstance(identity_payload, dict) or set(identity_payload) != {
        "workflow",
        "context",
        "artifact_inputs",
        "artifact_input_errors",
    }:
        raise RunRegistryError("run identity payload has an invalid structure")
    digest = identity_sha256(identity_payload)
    if record["identity_sha256"] != digest or run_id != f"wf_{digest[:24]}":
        raise RunRegistryError("run record identity digest does not match its payload")
    declared_nodes = _workflow_nodes(identity_payload)
    if record["workflow_id"] != identity_payload["workflow"]["workflow_id"]:
        raise RunRegistryError("run record workflow_id does not match its identity")
    if record["workflow_version"] != identity_payload["workflow"]["version"]:
        raise RunRegistryError(
            "run record workflow_version does not match its identity"
        )
    if record["context"] != identity_payload["context"]:
        raise RunRegistryError("run record context does not match its identity")
    if record["artifact_inputs"] != identity_payload["artifact_inputs"]:
        raise RunRegistryError("run record artifact_inputs do not match its identity")
    if record["artifact_input_errors"] != identity_payload["artifact_input_errors"]:
        raise RunRegistryError(
            "run record artifact_input_errors do not match its identity"
        )
    _validate_context(record["context"])
    _validate_artifact_inputs(record["artifact_inputs"])
    _validate_artifact_errors(record["artifact_input_errors"])
    if set(record["artifact_inputs"]) != set(declared_nodes):
        raise RunRegistryError("run record artifact_inputs do not cover workflow nodes")
    if set(record["artifact_input_errors"]) - set(declared_nodes):
        raise RunRegistryError(
            "run record artifact input error references an unknown node"
        )
    _validate_timestamp(record["started_at"], "started_at")
    if status == "RUNNING":
        if record["nodes"] != {}:
            raise RunRegistryError("RUNNING record nodes must be empty")
    else:
        _validate_timestamp(record["finished_at"], "finished_at")
        if not isinstance(record["nodes"], dict) or set(record["nodes"]) != set(
            declared_nodes
        ):
            raise RunRegistryError("terminal run nodes do not match workflow identity")
        for node_id, stage in record["nodes"].items():
            _validate_stage(stage, declared_nodes[node_id])
        if status != _expected_terminal_status(record["nodes"]):
            raise RunRegistryError("terminal run status does not match stage results")
    return record


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, sort_keys=True, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        directory_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        temporary.unlink(missing_ok=True)


class RunRegistry:
    def __init__(self, workspace: Path) -> None:
        self.workspace = Path(workspace).resolve()
        self.runs_dir = self.workspace / "runs"

    def path_for(self, run_id: str) -> Path:
        return self.runs_dir / f"{validate_run_id(run_id)}.json"

    @contextmanager
    def lock(self, run_id: str) -> Iterator[None]:
        canonical_run_id = validate_run_id(run_id)
        self.runs_dir.mkdir(parents=True, exist_ok=True)
        lock_path = self.runs_dir / f".{canonical_run_id}.lock"
        with lock_path.open("a+b") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            yield

    def load(self, run_id: str) -> dict[str, Any] | None:
        canonical_run_id = validate_run_id(run_id)
        path = self.path_for(canonical_run_id)
        if not path.exists():
            return None
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RunRegistryError(f"invalid run registry entry: {path}") from exc
        return validate_run_record(value, canonical_run_id)

    def save(self, record: dict[str, Any]) -> None:
        if not isinstance(record, dict):
            raise RunRegistryError("run registry entry must be an object")
        validate_run_id(record.get("run_id"))
        validated = validate_run_record(record)
        atomic_write_json(self.path_for(validated["run_id"]), validated)
