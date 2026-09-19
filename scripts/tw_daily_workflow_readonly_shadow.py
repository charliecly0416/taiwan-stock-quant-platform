from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from scripts.tw_daily_workflow_shadow import (
    CommandRunner,
    WorkflowShadowProfile,
    run_daily_workflow_shadow,
)


WORKFLOW_ID = "replay_window.model_a_observation"
WORKFLOW_MODULE = "replay_window.observe"
WORKFLOW_PERMISSION = "replay.read"
OBSERVED_ARTIFACT_ASOF = "2026-05-07"
WORKFLOW_TIMEOUT_SECONDS = 60


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


def _validate_replay_record(
    record: dict[str, Any], *, expected_model_id: str, expected_strategy_rule: str
) -> dict[str, Any]:
    nodes = record.get("nodes")
    if not isinstance(nodes, dict) or set(nodes) != {"observe_model_a_replay_window"}:
        raise ValueError("workflow run record must contain the one observation node")
    node = nodes["observe_model_a_replay_window"]
    if not isinstance(node, dict) or node.get("module") != WORKFLOW_MODULE:
        raise ValueError("workflow run record contains a non-observation module")
    observed_asof = OBSERVED_ARTIFACT_ASOF
    if record.get("status") == "SUCCEEDED":
        output = node.get("output")
        if (
            not isinstance(output, dict)
            or output.get("full_replay_contract_admission") is not False
        ):
            raise ValueError("workflow observation admission must remain false")
        refs = record.get("artifact_inputs", {}).get("observe_model_a_replay_window")
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
    return {"observed_artifact_asof": observed_asof}


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
    profile = WorkflowShadowProfile(
        schema_version="daily.workflow_readonly_shadow.v1",
        workflow_id=WORKFLOW_ID,
        workflow_version="1",
        permission=WORKFLOW_PERMISSION,
        workspace_name="workflow_readonly_shadow",
        stdout_name="workflow_readonly_shadow_stdout.json",
        stderr_name="workflow_readonly_shadow_stderr.txt",
        spec_relative_path="configs/workflows/replay_window_observation.yaml",
        expected_workflow=_expected_workflow_identity(
            expected_model_id=expected_model_id,
            expected_strategy_rule=expected_strategy_rule,
        ),
        disabled_observed_asof=OBSERVED_ARTIFACT_ASOF,
    )
    return run_daily_workflow_shadow(
        profile=profile,
        record_validator=lambda record, _asof: _validate_replay_record(
            record,
            expected_model_id=expected_model_id,
            expected_strategy_rule=expected_strategy_rule,
        ),
        job=job,
        job_dir=job_dir,
        asof=asof,
        enabled=enabled,
        repo_root=repo_root,
        python_executable=python_executable,
        workflow_runner_path=workflow_runner_path,
        spec_path=spec_path,
        protected_paths=protected_paths,
        pending_path=pending_path,
        installed_cron_path=installed_cron_path,
        command_runner=command_runner,
    )
