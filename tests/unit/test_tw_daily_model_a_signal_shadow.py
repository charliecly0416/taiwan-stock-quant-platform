from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

from tw_stock_workflow.run_registry import run_id_for_identity


ROOT = Path(__file__).resolve().parents[2]
HELPER_SCRIPT = ROOT / "scripts/tw_daily_model_a_signal_shadow.py"
MODEL_A = "e4_frozen_qlib_2018_2022"


def load_helper_module():
    spec = importlib.util.spec_from_file_location(
        "tw_daily_model_a_signal_shadow_test", HELPER_SCRIPT
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")


@pytest.fixture()
def isolated_wf4a(tmp_path: Path):
    module = load_helper_module()
    repo = tmp_path / "repo"
    spec_path = repo / "configs/workflows/research_history_observation.yaml"
    spec_path.parent.mkdir(parents=True)
    spec_path.write_bytes(
        (ROOT / "configs/workflows/research_history_observation.yaml").read_bytes()
    )
    runner = repo / "scripts/run_tw_stock_workflow.py"
    runner.parent.mkdir(parents=True)
    runner.write_text("# fixture\n", encoding="utf-8")
    history = repo / "data_tw/catalog/research_data_history/index.json"
    write_json(
        history,
        {"schema_version": "tw.research_data_history.index.v1", "days": {}},
    )
    protected = {
        name: repo / f"protected/{name}.json"
        for name in (
            "formal_provider_calendar",
            "qlib_accepted_latest",
            "legacy_option_c_latest",
            "controlled_model_signal_latest",
            "readonly_snapshot_latest",
            "agent_prompt_latest",
        )
    }
    for name, path in protected.items():
        write_json(path, {"name": name, "asof": "2026-09-18"})
    pending = repo / "protected/pending.json"
    cron = repo / "protected/cron.txt"
    write_json(pending, {"asof": "2026-09-18"})
    cron.write_text("cron\n", encoding="utf-8")
    job_dir = repo / "jobs/daily_test"
    job_dir.mkdir(parents=True)
    job = {
        "job_id": "daily_test",
        "status": "daily_auto_update_passed",
        "finished_at": "2026-09-18T11:00:00+00:00",
        "research_data_history": {
            "enabled": True,
            "attempted": True,
            "ok": True,
            "status": "READY_MODELA_ONLY",
            "asof": "2026-09-18",
            "job_id": "daily_test",
            "manifest_path": (
                "data_tw/catalog/research_data_history/2026-09-18/daily_test.json"
            ),
            "model_a": {"model_id": MODEL_A},
        },
    }
    write_json(
        repo / job["research_data_history"]["manifest_path"],
        {
            "schema_version": "tw.research_data_history.day.v1",
            "asof": "2026-09-18",
            "job_id": "daily_test",
            "status": "READY_MODELA_ONLY",
            "model_a": job["research_data_history"]["model_a"],
            "model_b": None,
            "production_allowed": False,
            "no_apply": True,
            "mainline_blocking": False,
            "replacement_marker": "AAAA",
        },
    )
    context = {
        "repo_root": repo,
        "python_executable": "python",
        "workflow_runner_path": runner,
        "spec_path": spec_path,
        "expected_model_id": MODEL_A,
        "protected_paths": protected,
        "pending_path": pending,
        "installed_cron_path": cron,
    }
    return module, repo, job_dir, job, context


def artifact_ref(
    artifact_type: str,
    slot: str,
    data_filename: str,
    day_manifest: dict[str, object],
) -> dict:
    base = f"artifacts/{slot}/model_a_run"
    declared_files = {
        filename: {
            "path": f"{base}/{filename}",
            "size_bytes": 10,
            "sha256": "a" * 64,
        }
        for filename in ("manifest.json", "validator_report.json", data_filename)
    }
    return {
        "artifact_type": artifact_type,
        "adapter_id": "research_data_history.v1",
        "model_id": MODEL_A,
        "asof": "2026-09-18",
        "status": "READY",
        "run_id": "model_a_run",
        "path": base,
        "manifest_path": f"{base}/manifest.json",
        "manifest_sha256": "a" * 64,
        "metadata": {
            "history_day_status": "READY_MODELA_ONLY",
            "history_slot": slot,
            "history_day_manifest": day_manifest,
            "declared_files": declared_files,
            "production_allowed": False,
            "no_apply": True,
            "mainline_blocking": False,
        },
    }


def workflow_record(
    module, argv: list[str], repo_root: Path, status: str = "SUCCEEDED"
) -> dict:
    workflow = module._expected_workflow_identity(MODEL_A)
    workspace = Path(argv[argv.index("--workspace") + 1]).resolve()
    context = {
        "mode": "readonly",
        "asof": "2026-09-18",
        "decision_cutoff": "2026-09-18T11:00:00+00:00",
        "workspace": str(workspace),
        "permissions": ["artifact.read"],
    }
    artifact_inputs = {
        "observe_model_a_input": [],
        "observe_model_a_signal": [],
    }
    if status == "SUCCEEDED":
        day_path = (
            repo_root
            / "data_tw/catalog/research_data_history/2026-09-18/daily_test.json"
        )
        day_content = day_path.read_bytes()
        day_manifest = {
            "path": str(day_path.relative_to(repo_root)),
            "size_bytes": len(day_content),
            "sha256": hashlib.sha256(day_content).hexdigest(),
        }
        artifact_inputs = {
            "observe_model_a_input": [
                artifact_ref(
                    "ModelInferenceInput",
                    "inference_input",
                    "inference_frame.csv",
                    day_manifest,
                )
            ],
            "observe_model_a_signal": [
                artifact_ref(
                    "ModelSignalArtifact", "signal", "signals.csv", day_manifest
                )
            ],
        }
    identity_payload = {
        "workflow": workflow,
        "context": context,
        "artifact_inputs": artifact_inputs,
        "artifact_input_errors": {},
    }
    run_id, digest = run_id_for_identity(identity_payload)
    if status == "SUCCEEDED":
        queries = {
            "observe_model_a_input": {
                "artifact_type": "ModelInferenceInput",
                "model_id": MODEL_A,
                "asof": "2026-09-18",
                "status": "READY",
            },
            "observe_model_a_signal": {
                "artifact_type": "ModelSignalArtifact",
                "model_id": MODEL_A,
                "asof": "2026-09-18",
                "status": "READY",
            },
        }
        nodes = {
            node_id: {
                "policy": "required",
                "module": "research_history.observe",
                "status": "SUCCEEDED",
                "output": {
                    "count": 1,
                    "query": queries[node_id],
                    "artifacts": artifact_inputs[node_id],
                },
            }
            for node_id in artifact_inputs
        }
    else:
        first = (
            {
                "policy": "required",
                "module": "research_history.observe",
                "status": "BLOCKED",
                "reason": "artifact_unavailable",
                "root_cause": "BLOCKED",
            }
            if status == "BLOCKED"
            else {
                "policy": "required",
                "module": "research_history.observe",
                "status": "FAILED",
                "error_type": "RuntimeError",
                "error": "fixture failure",
                "root_cause": "FAILED",
            }
        )
        nodes = {
            "observe_model_a_input": first,
            "observe_model_a_signal": {
                "policy": "required",
                "module": "research_history.observe",
                "status": "SKIPPED",
                "reason": "dependency_not_succeeded",
                "dependencies": {"observe_model_a_input": first["status"]},
                "dependency_causes": {"observe_model_a_input": first["root_cause"]},
                "root_cause": first["root_cause"],
            },
        }
    return {
        "schema_version": "tw.workflow.run.v1",
        "run_id": run_id,
        "identity_sha256": digest,
        "identity_payload": identity_payload,
        "workflow_id": "research_history.model_a_observation",
        "workflow_version": "1",
        "context": context,
        "artifact_inputs": artifact_inputs,
        "artifact_input_errors": {},
        "status": status,
        "started_at": "2026-09-18T11:00:00+00:00",
        "finished_at": "2026-09-18T11:00:01+00:00",
        "nodes": nodes,
    }


def fake_runner(
    module, calls: list[dict], status: str = "SUCCEEDED", returncode: int = 0
):
    def run(argv, **kwargs):
        calls.append({"argv": argv, **kwargs})
        record = workflow_record(module, argv, kwargs["cwd"], status)
        write_json(kwargs["stdout_path"], record)
        workspace = Path(argv[argv.index("--workspace") + 1])
        write_json(workspace / "runs" / f"{record['run_id']}.json", record)
        kwargs["stderr_path"].write_text("", encoding="utf-8")
        return {
            "ok": returncode == 0,
            "returncode": returncode,
            "stdout_path": str(kwargs["stdout_path"]),
            "stderr_path": str(kwargs["stderr_path"]),
        }

    return run


def run_shadow(module, job_dir, job, context, runner, *, enabled=True, **overrides):
    return module.run_daily_model_a_signal_shadow(
        job=job,
        job_dir=job_dir,
        asof="2026-09-18",
        enabled=enabled,
        command_runner=runner,
        **{**context, **overrides},
    )


def test_default_disabled_does_not_invoke_runner(isolated_wf4a) -> None:
    module, _, job_dir, job, context = isolated_wf4a
    calls: list[dict] = []

    result = run_shadow(
        module,
        job_dir,
        job,
        context,
        lambda *args, **kwargs: calls.append(kwargs),
        enabled=False,
    )

    assert calls == []
    assert result["status"] == "DISABLED_BY_DEFAULT"
    assert result["permissions"] == ["artifact.read"]
    assert result["mainline_blocking"] is False


def test_missing_current_materialization_blocks_without_runner(isolated_wf4a) -> None:
    module, _, job_dir, job, context = isolated_wf4a
    job["research_data_history"]["status"] = "SKIPPED_NO_ACCEPTED_ASSET"
    calls: list[dict] = []

    result = run_shadow(
        module, job_dir, job, context, lambda *args, **kwargs: calls.append(kwargs)
    )

    assert calls == []
    assert result["status"] == "BLOCKED_NONBLOCKING"
    assert result["attempted"] is False
    assert "not READY" in result["error"]


def test_current_manifest_model_a_drift_rejects_before_runner(isolated_wf4a) -> None:
    module, repo, job_dir, job, context = isolated_wf4a
    manifest_path = repo / job["research_data_history"]["manifest_path"]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["model_a"] = {"model_id": "different"}
    write_json(manifest_path, manifest)
    calls: list[dict] = []

    result = run_shadow(
        module, job_dir, job, context, lambda *args, **kwargs: calls.append(kwargs)
    )

    assert calls == []
    assert result["status"] == "ERROR_NONBLOCKING"
    assert "manifest identity changed" in result["error"]


def test_invalid_job_id_cannot_escape_protected_manifest_path(isolated_wf4a) -> None:
    module, repo, job_dir, job, context = isolated_wf4a
    outside = repo.parent / "outside.json"
    write_json(outside, {"private": True})
    job["job_id"] = "../../outside"
    job["research_data_history"]["job_id"] = "../../outside"
    calls: list[dict] = []

    result = run_shadow(
        module, job_dir, job, context, lambda *args, **kwargs: calls.append(kwargs)
    )

    assert calls == []
    assert result["status"] == "BLOCKED_NONBLOCKING"
    assert result["protected_before"]["research_history_day_manifest"]["path"].endswith(
        "/2026-09-18/__invalid_job_id__.json"
    )
    assert (
        result["protected_before"]["research_history_day_manifest"]["exists"] is False
    )


@pytest.mark.parametrize(
    ("workflow_status", "returncode", "expected"),
    [
        ("SUCCEEDED", 0, "SUCCEEDED_NONBLOCKING"),
        ("BLOCKED", 2, "BLOCKED_NONBLOCKING"),
        ("FAILED", 2, "FAILED_NONBLOCKING"),
    ],
)
def test_terminal_results_are_nonblocking(
    isolated_wf4a, workflow_status: str, returncode: int, expected: str
) -> None:
    module, _, job_dir, job, context = isolated_wf4a
    result = run_shadow(
        module,
        job_dir,
        job,
        context,
        fake_runner(module, [], workflow_status, returncode),
    )

    assert result["status"] == expected
    assert result["mainline_status_before"] == "daily_auto_update_passed"
    assert result["mainline_status_after"] == "daily_auto_update_passed"
    assert job["status"] == "daily_auto_update_passed"


def test_success_uses_pinned_index_permission_and_workspace(isolated_wf4a) -> None:
    module, _, job_dir, job, context = isolated_wf4a
    calls: list[dict] = []

    result = run_shadow(module, job_dir, job, context, fake_runner(module, calls))

    argv = calls[0]["argv"]
    assert result["ok"] is True
    assert result["workflow_version"] == "1"
    assert result["observed_artifact_asof"] == "2026-09-18"
    assert result["model_a_run_id"] == "model_a_run"
    assert argv.count("--permission") == 1
    assert argv[argv.index("--permission") + 1] == "artifact.read"
    assert "replay.read" not in argv
    assert argv[argv.index("--history-index") + 1] == (
        "data_tw/catalog/research_data_history/index.json"
    )
    assert Path(argv[argv.index("--workspace") + 1]) == (
        job_dir / "workflow_model_a_signal_shadow"
    )
    assert calls[0]["timeout"] == 60


def test_history_index_symlink_is_rejected_before_runner(isolated_wf4a) -> None:
    module, repo, job_dir, job, context = isolated_wf4a
    history = repo / "data_tw/catalog/research_data_history/index.json"
    target = repo / "data_tw/catalog/research_data_history/other.json"
    history.rename(target)
    history.symlink_to(target.name)
    calls: list[dict] = []

    result = run_shadow(
        module, job_dir, job, context, lambda *args, **kwargs: calls.append(kwargs)
    )

    assert calls == []
    assert result["status"] == "ERROR_NONBLOCKING"
    assert "pinned regular repository file" in result["error"]


def test_alternate_spec_path_is_rejected_before_runner(isolated_wf4a) -> None:
    module, repo, job_dir, job, context = isolated_wf4a
    alternate = repo / "configs/workflows/copy.yaml"
    alternate.write_bytes(context["spec_path"].read_bytes())
    calls: list[dict] = []

    result = run_shadow(
        module,
        job_dir,
        job,
        context,
        lambda *args, **kwargs: calls.append(kwargs),
        spec_path=alternate,
    )

    assert calls == []
    assert result["status"] == "ERROR_NONBLOCKING"
    assert "pinned regular repository file" in result["error"]


def test_malformed_success_record_is_failed_nonblocking(isolated_wf4a) -> None:
    module, _, job_dir, job, context = isolated_wf4a

    def malformed(argv, **kwargs):
        record = workflow_record(module, argv, kwargs["cwd"])
        record["artifact_inputs"]["observe_model_a_signal"][0]["metadata"].pop(
            "declared_files"
        )
        record["identity_payload"]["artifact_inputs"] = record["artifact_inputs"]
        run_id, digest = run_id_for_identity(record["identity_payload"])
        record["run_id"] = run_id
        record["identity_sha256"] = digest
        write_json(kwargs["stdout_path"], record)
        workspace = Path(argv[argv.index("--workspace") + 1])
        write_json(workspace / "runs" / f"{run_id}.json", record)
        kwargs["stderr_path"].write_text("", encoding="utf-8")
        return {
            "ok": True,
            "returncode": 0,
            "stdout_path": str(kwargs["stdout_path"]),
            "stderr_path": str(kwargs["stderr_path"]),
        }

    result = run_shadow(module, job_dir, job, context, malformed)

    assert result["status"] == "FAILED_NONBLOCKING"
    assert "declared files are incomplete" in result["error"]


@pytest.mark.parametrize(
    ("mutation", "expected_error"),
    [
        ("adapter", "identity/safety boundary changed"),
        ("manifest", "manifest identity is inconsistent"),
        ("day_manifest", "do not bind the current day manifest"),
        ("day_size", "do not bind the current day manifest"),
        ("day_sha", "do not bind the current day manifest"),
    ],
)
def test_internally_signed_ref_inconsistency_is_failed_nonblocking(
    isolated_wf4a, mutation: str, expected_error: str
) -> None:
    module, _, job_dir, job, context = isolated_wf4a

    def inconsistent(argv, **kwargs):
        record = workflow_record(module, argv, kwargs["cwd"])
        ref = record["artifact_inputs"]["observe_model_a_signal"][0]
        if mutation == "adapter":
            ref["adapter_id"] = "other.v1"
        elif mutation == "manifest":
            ref["manifest_sha256"] = "c" * 64
        elif mutation == "day_manifest":
            ref["metadata"]["history_day_manifest"]["path"] = (
                "data_tw/catalog/research_data_history/2026-09-18/other.json"
            )
        elif mutation == "day_size":
            ref["metadata"]["history_day_manifest"]["size_bytes"] += 1
        else:
            ref["metadata"]["history_day_manifest"]["sha256"] = "c" * 64
        run_id, digest = run_id_for_identity(record["identity_payload"])
        record["run_id"] = run_id
        record["identity_sha256"] = digest
        write_json(kwargs["stdout_path"], record)
        workspace = Path(argv[argv.index("--workspace") + 1])
        write_json(workspace / "runs" / f"{run_id}.json", record)
        kwargs["stderr_path"].write_text("", encoding="utf-8")
        return {
            "ok": True,
            "returncode": 0,
            "stdout_path": str(kwargs["stdout_path"]),
            "stderr_path": str(kwargs["stderr_path"]),
        }

    result = run_shadow(module, job_dir, job, context, inconsistent)

    assert result["status"] == "FAILED_NONBLOCKING"
    assert expected_error in result["error"]


def test_same_path_valid_manifest_replacement_during_runner_fails_closed(
    isolated_wf4a,
) -> None:
    module, repo, job_dir, job, context = isolated_wf4a
    manifest_path = repo / job["research_data_history"]["manifest_path"]
    original = manifest_path.read_bytes()

    def replace_after_record(argv, **kwargs):
        result = fake_runner(module, [])(argv, **kwargs)
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["replacement_marker"] = "BBBB"
        write_json(manifest_path, manifest)
        return result

    result = run_shadow(module, job_dir, job, context, replace_after_record)

    assert result["status"] == "FAILED_NONBLOCKING"
    assert result["protected_unchanged"] is False
    assert result["error_type"] == "ReadonlyBoundaryChanged"
    replacement = manifest_path.read_bytes()
    assert len(replacement) == len(original)
    assert (
        hashlib.sha256(replacement).hexdigest() != hashlib.sha256(original).hexdigest()
    )


def test_timeout_and_exception_are_nonblocking(isolated_wf4a) -> None:
    module, _, job_dir, job, context = isolated_wf4a

    def timeout(argv, **kwargs):
        kwargs["stdout_path"].write_text("", encoding="utf-8")
        kwargs["stderr_path"].write_text("timeout", encoding="utf-8")
        return {
            "ok": False,
            "returncode": 124,
            "stdout_path": str(kwargs["stdout_path"]),
            "stderr_path": str(kwargs["stderr_path"]),
        }

    timed_out = run_shadow(module, job_dir, job, context, timeout)
    assert timed_out["status"] == "TIMEOUT_NONBLOCKING"

    second_job_dir = context["repo_root"] / "jobs/second"
    second_job_dir.mkdir()

    def raises(argv, **kwargs):
        raise RuntimeError("fixture exception")

    errored = run_shadow(module, second_job_dir, job, context, raises)
    assert errored["status"] == "ERROR_NONBLOCKING"
    assert errored["error_type"] == "RuntimeError"


def test_protected_mutation_fails_closed_without_mainline_change(isolated_wf4a) -> None:
    module, _, job_dir, job, context = isolated_wf4a
    protected_path = next(iter(context["protected_paths"].values()))

    def mutate(argv, **kwargs):
        result = fake_runner(module, [])(argv, **kwargs)
        protected_path.write_text("changed\n", encoding="utf-8")
        return result

    result = run_shadow(module, job_dir, job, context, mutate)

    assert result["status"] == "FAILED_NONBLOCKING"
    assert result["error_type"] == "ReadonlyBoundaryChanged"
    assert result["protected_unchanged"] is False
    assert job["status"] == "daily_auto_update_passed"
    assert result["model_training_triggered"] is False
    assert result["model_scoring_triggered"] is False
    assert result["latest_pointer_write_performed"] is False
    assert result["trading_triggered"] is False
