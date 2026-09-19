from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from scripts.tw_daily_workflow_shadow import (
    TIMEOUT_SECONDS,
    CommandRunner,
    WorkflowShadowBlocked,
    WorkflowShadowProfile,
    run_daily_workflow_shadow,
)
from tw_stock_workflow.readonly_snapshot import (
    ARTIFACT_TYPE,
    OBSERVATION_STATUS,
    ReadonlyStrategySnapshotAdapter,
)


WORKFLOW_ID = "readonly_strategy_snapshot.model_a_observation"
WORKFLOW_MODULE = "readonly_strategy_snapshot.observe"
WORKFLOW_PERMISSION = "artifact.read"
WORKFLOW_TIMEOUT_SECONDS = TIMEOUT_SECONDS
WORKFLOW_SPEC_RELATIVE_PATH = (
    "configs/workflows/readonly_strategy_snapshot_observation.yaml"
)
DAPR18_PRODUCT_STATE_FIELDS = frozenset(
    {
        "schema_version",
        "created_at",
        "target_asof",
        "controlled_signal_latest_asof",
        "readonly_snapshot_latest_asof",
        "agent_prompt_latest_asof",
        "controlled_signal_run_id",
        "readonly_snapshot_manifest",
        "agent_prompt_manifest",
        "all_product_latest_match_target",
    }
)
DAPR18_PRODUCT_STABLE_FIELDS = DAPR18_PRODUCT_STATE_FIELDS - {"created_at"}


def _expected_workflow_identity(expected_model_id: str) -> dict[str, Any]:
    return {
        "schema_version": "tw.workflow.spec.v1",
        "workflow_id": WORKFLOW_ID,
        "version": "1",
        "nodes": [
            {
                "id": "observe_model_a_readonly_snapshot",
                "module": WORKFLOW_MODULE,
                "needs": [],
                "policy": "required",
                "config": {
                    "artifact_type": ARTIFACT_TYPE,
                    "model_id": expected_model_id,
                    "status": OBSERVATION_STATUS,
                    "min_count": 1,
                    "require_candidate_only": True,
                },
            }
        ],
    }


def _dapr18_stable_state(state: dict[str, Any]) -> dict[str, Any]:
    string_fields = DAPR18_PRODUCT_STABLE_FIELDS - {
        "all_product_latest_match_target"
    }
    if (
        set(state) != DAPR18_PRODUCT_STATE_FIELDS
        or state.get("schema_version") != "dapr18p1.product_latest_state.v1"
        or not isinstance(state.get("created_at"), str)
        or not state["created_at"]
        or any(
            not isinstance(state.get(field), str) or not state[field]
            for field in string_fields
        )
        or type(state.get("all_product_latest_match_target")) is not bool
    ):
        raise WorkflowShadowBlocked(
            "current daily DAPR18 product state schema is invalid"
        )
    return {field: state[field] for field in sorted(DAPR18_PRODUCT_STABLE_FIELDS)}


def _dapr18_current_snapshot(
    job: dict[str, Any],
    *,
    daily_asof: str,
    expected_manifest: str,
    expected_source_run_id: str,
) -> dict[str, Any]:
    orchestration = job.get("dapr18_controlled_latest_orchestration")
    if not isinstance(orchestration, dict):
        raise WorkflowShadowBlocked("current daily DAPR18 result is missing")
    status = orchestration.get("status")
    allowed_statuses = {
        "auto_publish_chain_completed",
        "auto_publish_idempotent_noop_already_current",
    }
    state_before = orchestration.get("product_latest_state_before")
    state_after = orchestration.get("product_latest_state_after")
    chain = orchestration.get("auto_publish_chain")
    authorization = orchestration.get("authorization_gate")
    if not isinstance(state_before, dict) or not isinstance(state_after, dict):
        raise WorkflowShadowBlocked("current daily DAPR18 product state is missing")
    stable_state_before = _dapr18_stable_state(state_before)
    stable_state_after = _dapr18_stable_state(state_after)
    if (
        orchestration.get("enabled") is not True
        or orchestration.get("attempted") is not True
        or orchestration.get("ok") is not True
        or status not in allowed_statuses
        or orchestration.get("publish_readonly_snapshot_latest") is not True
        or orchestration.get("forbidden_actions_all_false") is not True
        or orchestration.get("forbidden_protected_paths_unchanged") is not True
        or not isinstance(chain, dict)
        or not isinstance(authorization, dict)
        or authorization.get("allowed") is not True
        or chain.get("target_asof") != daily_asof
        or chain.get("ok") is not True
        or state_after.get("target_asof") != daily_asof
        or state_after.get("controlled_signal_latest_asof") != daily_asof
        or state_after.get("readonly_snapshot_latest_asof") != daily_asof
        or state_after.get("agent_prompt_latest_asof") != daily_asof
        or state_after.get("readonly_snapshot_manifest") != expected_manifest
        or state_after.get("controlled_signal_run_id") != expected_source_run_id
        or state_after.get("all_product_latest_match_target") is not True
    ):
        raise WorkflowShadowBlocked(
            "current daily DAPR18 result did not validate this asof snapshot"
        )

    if status == "auto_publish_chain_completed":
        steps = chain.get("steps")
        dapr13 = [
            step
            for step in steps or []
            if isinstance(step, dict)
            and step.get("name") == "dapr13_actual_readonly_snapshot_publish"
        ]
        output = dapr13[0].get("stdout_payload") if len(dapr13) == 1 else None
        if (
            chain.get("status") != "pass"
            or orchestration.get("readonly_snapshot_latest_write_performed") is not True
            or len(dapr13) != 1
            or dapr13[0].get("ok") is not True
            or not isinstance(output, dict)
            or output.get("status") != "pass"
            or output.get("target_asof") != daily_asof
            or output.get("snapshot_manifest") != expected_manifest
            or state_before.get("all_product_latest_match_target") is not False
            or stable_state_before == stable_state_after
        ):
            raise WorkflowShadowBlocked(
                "current daily DAPR13 publish evidence does not bind this snapshot"
            )
    else:
        if (
            chain.get("status") != "idempotent_noop"
            or chain.get("reason")
            != "all_product_latest_already_match_target_asof"
            or chain.get("steps") != []
            or orchestration.get("readonly_snapshot_latest_write_performed") is not False
            or state_before.get("target_asof") != daily_asof
            or state_before.get("readonly_snapshot_latest_asof") != daily_asof
            or state_before.get("readonly_snapshot_manifest") != expected_manifest
            or state_before.get("controlled_signal_run_id")
            != expected_source_run_id
            or state_before.get("all_product_latest_match_target") is not True
            or stable_state_before != stable_state_after
        ):
            raise WorkflowShadowBlocked(
                "current daily DAPR18 idempotent evidence is not exact"
            )
    return {
        "dapr18_status": status,
        "dapr18_snapshot_manifest": expected_manifest,
    }


def _validate_snapshot_record(
    record: dict[str, Any],
    daily_asof: str,
    *,
    expected_model_id: str,
    expected_ref: dict[str, Any],
    verify_current_ref: Any,
) -> dict[str, Any]:
    if verify_current_ref() != expected_ref:
        raise ValueError("workflow current readonly snapshot changed during observation")
    node_id = "observe_model_a_readonly_snapshot"
    nodes = record.get("nodes")
    artifact_inputs = record.get("artifact_inputs")
    if (
        not isinstance(nodes, dict)
        or set(nodes) != {node_id}
        or not isinstance(artifact_inputs, dict)
        or set(artifact_inputs) != {node_id}
        or not isinstance(nodes[node_id], dict)
        or nodes[node_id].get("module") != WORKFLOW_MODULE
    ):
        raise ValueError("workflow run record must contain exactly one snapshot node")
    if record.get("status") != "SUCCEEDED":
        return {"observed_artifact_asof": ""}
    refs = artifact_inputs[node_id]
    output = nodes[node_id].get("output")
    expected_query = {
        "artifact_type": ARTIFACT_TYPE,
        "model_id": expected_model_id,
        "asof": daily_asof,
        "status": OBSERVATION_STATUS,
        "require_candidate_only": True,
    }
    if (
        refs != [expected_ref]
        or nodes[node_id].get("status") != "SUCCEEDED"
        or not isinstance(output, dict)
        or output.get("count") != 1
        or output.get("query") != expected_query
        or output.get("artifacts") != refs
        or output.get("full_strategy_admission") is not False
        or expected_ref.get("adapter_id") != "readonly_strategy_snapshot.v1"
        or expected_ref.get("artifact_type") != ARTIFACT_TYPE
        or expected_ref.get("model_id") != expected_model_id
        or expected_ref.get("asof") != daily_asof
        or expected_ref.get("status") != OBSERVATION_STATUS
    ):
        raise ValueError("workflow readonly snapshot record identity changed")
    metadata = expected_ref.get("metadata")
    if (
        not isinstance(metadata, dict)
        or metadata.get("candidate_only") is not True
        or metadata.get("full_strategy_status") != "NOT_BUILT"
        or metadata.get("production_allowed") is not False
        or metadata.get("no_apply") is not True
        or metadata.get("mainline_blocking") is not False
    ):
        raise ValueError("workflow readonly snapshot safety boundary changed")
    return {
        "observed_artifact_asof": daily_asof,
        "snapshot_source_run_id": expected_ref["run_id"],
        "full_strategy_admission": False,
    }


def _ref_paths(ref: dict[str, Any], repo_root: Path) -> dict[str, Path]:
    metadata = ref.get("metadata")
    if not isinstance(metadata, dict):
        return {}
    records: list[tuple[str, Any]] = [
        ("snapshot_manifest", {"path": ref.get("manifest_path")}),
        ("snapshot_latest", metadata.get("latest_pointer")),
        ("snapshot_checksum_manifest", metadata.get("checksum_manifest")),
        ("snapshot_product_registry", metadata.get("product_registry")),
        ("snapshot_baseline_descriptor", metadata.get("baseline_descriptor")),
        ("snapshot_source_signal_latest", metadata.get("source_signal_latest")),
    ]
    for group in ("declared_files", "source_signal_files"):
        values = metadata.get(group)
        if isinstance(values, dict):
            records.extend((f"snapshot_{group}_{name}", value) for name, value in values.items())
    paths: dict[str, Path] = {}
    for name, record in records:
        if isinstance(record, dict) and isinstance(record.get("path"), str):
            paths[name] = repo_root / record["path"]
    return paths


def run_daily_readonly_snapshot_shadow(
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
    adapter: ReadonlyStrategySnapshotAdapter | None = None
    expected_ref: dict[str, Any] = {}
    initial_error: Exception | None = None
    if enabled:
        try:
            adapter = ReadonlyStrategySnapshotAdapter(repo_root)
            refs = adapter.query(
                artifact_type=ARTIFACT_TYPE,
                model_id=expected_model_id,
                asof=asof,
                status=OBSERVATION_STATUS,
            )
            if len(refs) != 1:
                raise ValueError("current readonly snapshot query did not return one ref")
            expected_ref = refs[0].to_dict()
        except Exception as exc:  # Re-raised inside the shared nonblocking boundary.
            initial_error = exc

    def current_ref() -> dict[str, Any]:
        if adapter is None:
            raise ValueError("readonly snapshot adapter is unavailable")
        refs = adapter.query(
            artifact_type=ARTIFACT_TYPE,
            model_id=expected_model_id,
            asof=asof,
            status=OBSERVATION_STATUS,
        )
        if len(refs) != 1:
            raise ValueError("current readonly snapshot query did not return one ref")
        return refs[0].to_dict()

    def precondition() -> dict[str, Any]:
        if initial_error is not None:
            raise initial_error
        expected_manifest = (
            f"data_tw/artifacts/publish/readonly_strategy_snapshot/{asof}/manifest.json"
        )
        dapr18 = _dapr18_current_snapshot(
            job,
            daily_asof=asof,
            expected_manifest=expected_manifest,
            expected_source_run_id=str(expected_ref.get("run_id") or ""),
        )
        if current_ref() != expected_ref:
            raise ValueError("current readonly snapshot changed before observation")
        return {**dapr18, "readonly_snapshot_ref": expected_ref}

    profile = WorkflowShadowProfile(
        schema_version="daily.workflow_readonly_snapshot_shadow.v1",
        workflow_id=WORKFLOW_ID,
        workflow_version="1",
        permission=WORKFLOW_PERMISSION,
        workspace_name="workflow_readonly_snapshot_shadow",
        stdout_name="workflow_readonly_snapshot_shadow_stdout.json",
        stderr_name="workflow_readonly_snapshot_shadow_stderr.txt",
        spec_relative_path=WORKFLOW_SPEC_RELATIVE_PATH,
        expected_workflow=_expected_workflow_identity(expected_model_id),
    )
    return run_daily_workflow_shadow(
        profile=profile,
        record_validator=lambda record, daily_asof: _validate_snapshot_record(
            record,
            daily_asof,
            expected_model_id=expected_model_id,
            expected_ref=expected_ref,
            verify_current_ref=current_ref,
        ),
        job=job,
        job_dir=job_dir,
        asof=asof,
        enabled=enabled,
        repo_root=repo_root,
        python_executable=python_executable,
        workflow_runner_path=workflow_runner_path,
        spec_path=spec_path,
        protected_paths={**protected_paths, **_ref_paths(expected_ref, repo_root)},
        pending_path=pending_path,
        installed_cron_path=installed_cron_path,
        command_runner=command_runner,
        precondition=precondition,
    )
