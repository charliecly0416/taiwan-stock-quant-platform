from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest
import yaml

from tw_stock_workflow.run_registry import run_id_for_identity


ROOT = Path(__file__).resolve().parents[2]
HELPER_SCRIPT = ROOT / "scripts/tw_daily_workflow_readonly_shadow.py"


def load_helper_module():
    spec = importlib.util.spec_from_file_location(
        "tw_daily_workflow_readonly_shadow_test", HELPER_SCRIPT
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False) + "\n", encoding="utf-8")


@pytest.fixture()
def isolated_wf3(tmp_path: Path):
    module = load_helper_module()
    protected = {
        "formal_provider_calendar": tmp_path / "protected/calendar.txt",
        "qlib_accepted_latest": tmp_path / "protected/accepted_latest.json",
        "legacy_option_c_latest": tmp_path / "protected/legacy_latest.json",
        "controlled_model_signal_latest": tmp_path / "protected/model_a_latest.json",
        "readonly_snapshot_latest": tmp_path / "protected/snapshot_latest.json",
        "agent_prompt_latest": tmp_path / "protected/agent_latest.json",
    }
    for name, path in protected.items():
        write_json(path, {"name": name, "asof": "2026-09-18"})
    pending = tmp_path / "protected/pending_asof.json"
    cron = tmp_path / "protected/installed.cron"
    write_json(pending, {"asof": "2026-09-18"})
    cron.write_text("cron\n", encoding="utf-8")
    job_dir = tmp_path / "job"
    job_dir.mkdir()
    job = {
        "job_id": "daily_test",
        "status": "daily_auto_update_passed",
        "finished_at": "2026-09-18T11:00:00+00:00",
    }
    context = {
        "repo_root": ROOT,
        "python_executable": "python",
        "workflow_runner_path": ROOT / "scripts/run_tw_stock_workflow.py",
        "spec_path": ROOT / "configs/workflows/replay_window_observation.yaml",
        "expected_model_id": "e4_frozen_qlib_2018_2022",
        "expected_strategy_rule": "top50_exit_one_worst_sell",
        "protected_paths": protected,
        "pending_path": pending,
        "installed_cron_path": cron,
    }
    return module, job_dir, job, context


def workflow_record(status: str) -> dict:
    return {
        "schema_version": "tw.workflow.run.v1",
        "run_id": "",
        "workflow_id": "replay_window.model_a_observation",
        "workflow_version": "1",
        "status": status,
        "artifact_inputs": {
            "observe_model_a_replay_window": [
                {
                    "artifact_type": "ReadonlyReplayWindowArtifact",
                    "adapter_id": "readonly_replay_window.v1",
                    "model_id": "e4_frozen_qlib_2018_2022",
                    "asof": "2026-05-07",
                    "status": "INDEXED_READONLY",
                    "run_id": "replay_window_0123456789abcdef01234567",
                    "path": "data_tw/artifacts/readonly_replay_windows/example",
                    "manifest_path": "data_tw/artifacts/readonly_replay_windows/example/manifest.json",
                    "manifest_sha256": "a" * 64,
                    "metadata": {
                        "strategy_rule": "top50_exit_one_worst_sell",
                        "window_start": "2026-01-01",
                        "window_end": "2026-05-07",
                        "full_replay_contract_status": "HOLD",
                    },
                }
            ]
        },
        "nodes": {
            "observe_model_a_replay_window": {
                "module": "replay_window.observe",
                "status": status,
                "output": {"full_replay_contract_admission": False},
            }
        },
    }


def bind_record_context(record: dict, argv: list[str]) -> None:
    workspace = Path(argv[argv.index("--workspace") + 1]).resolve()
    context = {
        "mode": "readonly",
        "asof": argv[argv.index("--asof") + 1],
        "decision_cutoff": argv[argv.index("--decision-cutoff") + 1],
        "workspace": str(workspace),
        "permissions": [argv[argv.index("--permission") + 1]],
    }
    artifact_inputs = record["artifact_inputs"]
    workflow = {
        "schema_version": "tw.workflow.spec.v1",
        "workflow_id": "replay_window.model_a_observation",
        "version": "1",
        "nodes": [
            {
                "id": "observe_model_a_replay_window",
                "module": "replay_window.observe",
                "needs": [],
                "policy": "required",
                "config": {
                    "model_id": "e4_frozen_qlib_2018_2022",
                    "strategy_rule": "top50_exit_one_worst_sell",
                    "window_start": "2026-01-01",
                    "window_end": "2026-05-07",
                    "status": "INDEXED_READONLY",
                    "min_count": 1,
                },
            }
        ],
    }
    identity_payload = {
        "workflow": workflow,
        "context": context,
        "artifact_inputs": artifact_inputs,
        "artifact_input_errors": {},
    }
    run_id, digest = run_id_for_identity(identity_payload)
    stage = {
        "policy": "required",
        "module": "replay_window.observe",
        "status": record["status"],
    }
    if record["status"] == "SUCCEEDED":
        stage["output"] = {"full_replay_contract_admission": False}
    elif record["status"] == "BLOCKED":
        stage.update(reason="artifact_unavailable", root_cause="BLOCKED")
    else:
        stage.update(
            error_type="RuntimeError",
            error="observation failed",
            root_cause="FAILED",
        )
    record.update(
        run_id=run_id,
        identity_sha256=digest,
        identity_payload=identity_payload,
        context=context,
        artifact_input_errors={},
        started_at="2026-09-18T11:00:00+00:00",
        finished_at="2026-09-18T11:00:01+00:00",
        nodes={"observe_model_a_replay_window": stage},
    )


def resign_record(record: dict) -> None:
    run_id, digest = run_id_for_identity(record["identity_payload"])
    record["run_id"] = run_id
    record["identity_sha256"] = digest


def fake_runner_for(status: str, returncode: int, calls: list[dict]):
    def fake_runner(argv, **kwargs):
        calls.append({"argv": argv, **kwargs})
        record = workflow_record(status)
        bind_record_context(record, argv)
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

    return fake_runner


def run_shadow(module, job_dir, job, context, runner, *, enabled=True, **overrides):
    return module.run_daily_workflow_readonly_shadow(
        job=job,
        job_dir=job_dir,
        asof="2026-09-18",
        enabled=enabled,
        command_runner=runner,
        **{**context, **overrides},
    )


def test_default_disabled_does_not_invoke_runner(isolated_wf3) -> None:
    module, job_dir, job, context = isolated_wf3
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
    assert result["attempted"] is False
    assert result["mainline_blocking"] is False
    assert job["status"] == "daily_auto_update_passed"


@pytest.mark.parametrize(
    ("workflow_status", "returncode", "expected_status", "expected_ok"),
    [
        ("SUCCEEDED", 0, "SUCCEEDED_NONBLOCKING", True),
        ("BLOCKED", 2, "BLOCKED_NONBLOCKING", False),
        ("FAILED", 2, "FAILED_NONBLOCKING", False),
    ],
)
def test_terminal_workflow_results_are_nonblocking(
    isolated_wf3,
    workflow_status: str,
    returncode: int,
    expected_status: str,
    expected_ok: bool,
) -> None:
    module, job_dir, job, context = isolated_wf3
    calls: list[dict] = []
    result = run_shadow(
        module,
        job_dir,
        job,
        context,
        fake_runner_for(workflow_status, returncode, calls),
    )

    assert result["status"] == expected_status
    assert result["ok"] is expected_ok
    assert result["workflow_status"] == workflow_status
    assert result["mainline_status_before"] == "daily_auto_update_passed"
    assert result["mainline_status_after"] == "daily_auto_update_passed"
    assert job["status"] == "daily_auto_update_passed"
    assert result["daily_job_asof"] == "2026-09-18"
    assert result["observed_artifact_asof"] == "2026-05-07"
    assert result["protected_unchanged"] is True
    assert result["pending_unchanged"] is True
    assert result["installed_cron_unchanged"] is True
    assert len(result["protected_before"]) == 6


def test_runner_uses_only_replay_read_and_job_local_workspace(isolated_wf3) -> None:
    module, job_dir, job, context = isolated_wf3
    calls: list[dict] = []
    result = run_shadow(
        module, job_dir, job, context, fake_runner_for("SUCCEEDED", 0, calls)
    )

    assert result["ok"] is True
    assert len(calls) == 1
    argv = calls[0]["argv"]
    permission_indexes = [
        index for index, value in enumerate(argv) if value == "--permission"
    ]
    assert permission_indexes == [argv.index("--permission")]
    assert argv[permission_indexes[0] + 1] == "replay.read"
    assert "artifact.read" not in argv
    assert "replay.candidate.write" not in argv
    assert "replay_candidate.build_validate" not in argv
    workspace = Path(argv[argv.index("--workspace") + 1]).resolve()
    workspace.relative_to(job_dir.resolve())
    assert workspace == (job_dir / "workflow_readonly_shadow").resolve()
    assert calls[0]["timeout"] == 60
    assert calls[0]["env"] == {"PYTHONPATH": str(ROOT)}


def test_timeout_is_nonblocking_and_preserves_all_boundaries(isolated_wf3) -> None:
    module, job_dir, job, context = isolated_wf3

    def timed_out(argv, **kwargs):
        kwargs["stdout_path"].write_text("", encoding="utf-8")
        kwargs["stderr_path"].write_text("timeout", encoding="utf-8")
        return {
            "ok": False,
            "returncode": 124,
            "stdout_path": str(kwargs["stdout_path"]),
            "stderr_path": str(kwargs["stderr_path"]),
        }

    result = run_shadow(module, job_dir, job, context, timed_out)

    assert result["status"] == "TIMEOUT_NONBLOCKING"
    assert result["runner_returncode"] == 124
    assert result["timeout"] == 60
    assert result["protected_unchanged"] is True
    assert result["pending_unchanged"] is True
    assert job["status"] == "daily_auto_update_passed"


def test_runner_exception_is_nonblocking(isolated_wf3) -> None:
    module, job_dir, job, context = isolated_wf3

    def raises(argv, **kwargs):
        raise RuntimeError("isolated runner failure")

    result = run_shadow(module, job_dir, job, context, raises)

    assert result["status"] == "ERROR_NONBLOCKING"
    assert result["error_type"] == "RuntimeError"
    assert result["attempted"] is True
    assert result["protected_unchanged"] is True
    assert result["pending_unchanged"] is True
    assert job["status"] == "daily_auto_update_passed"


def test_execution_spec_replacement_is_rejected_before_runner(
    isolated_wf3, tmp_path: Path
) -> None:
    module, job_dir, job, context = isolated_wf3
    fake_root = tmp_path / "repo"
    bad_spec = fake_root / "configs/workflows/replay_window_observation.yaml"
    bad_spec.parent.mkdir(parents=True)
    payload = yaml.safe_load(
        (ROOT / "configs/workflows/replay_window_observation.yaml").read_text(
            encoding="utf-8"
        )
    )
    payload["nodes"][0]["module"] = "replay_candidate.build_validate"
    bad_spec.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    calls: list[dict] = []

    result = run_shadow(
        module,
        job_dir,
        job,
        context,
        lambda *args, **kwargs: calls.append(kwargs),
        repo_root=fake_root,
        workflow_runner_path=fake_root / "scripts/run_tw_stock_workflow.py",
        spec_path=bad_spec,
    )

    assert calls == []
    assert result["status"] == "ERROR_NONBLOCKING"
    assert "may only run replay_window.observe" in result["error"]
    assert result["replay_candidate_execution"] is False
    assert job["status"] == "daily_auto_update_passed"


def test_workspace_symlink_escape_is_rejected_before_runner(
    isolated_wf3, tmp_path: Path
) -> None:
    module, job_dir, job, context = isolated_wf3
    outside = tmp_path / "outside"
    outside.mkdir()
    (job_dir / "workflow_readonly_shadow").symlink_to(outside, target_is_directory=True)
    calls: list[dict] = []

    result = run_shadow(
        module,
        job_dir,
        job,
        context,
        lambda *args, **kwargs: calls.append(kwargs),
    )

    assert calls == []
    assert result["status"] == "ERROR_NONBLOCKING"
    assert "workspace may not be a symlink" in result["error"]
    assert job["status"] == "daily_auto_update_passed"


def test_no_recovery_pointer_training_replay_or_trading_side_effects(
    isolated_wf3,
) -> None:
    module, job_dir, job, context = isolated_wf3
    protected = {
        **context["protected_paths"],
        "pending": context["pending_path"],
        "cron": context["installed_cron_path"],
    }
    before = {name: path.read_bytes() for name, path in protected.items()}
    calls: list[dict] = []

    result = run_shadow(
        module, job_dir, job, context, fake_runner_for("SUCCEEDED", 0, calls)
    )

    assert result["automatic_recovery_triggered"] is False
    assert result["provider_refresh_triggered"] is False
    assert result["provider_publish_triggered"] is False
    assert result["accepted_latest_switch_triggered"] is False
    assert result["latest_pointer_write_performed"] is False
    assert result["pending_asof_write_performed"] is False
    assert result["replay_candidate_execution"] is False
    assert result["model_training_triggered"] is False
    assert result["trading_triggered"] is False
    assert {name: path.read_bytes() for name, path in protected.items()} == before


def test_protected_or_pending_mutation_fails_closed_without_changing_mainline(
    isolated_wf3,
) -> None:
    module, job_dir, job, context = isolated_wf3
    calls: list[dict] = []
    base_runner = fake_runner_for("SUCCEEDED", 0, calls)

    def mutating_runner(argv, **kwargs):
        result = base_runner(argv, **kwargs)
        write_json(context["pending_path"], {"asof": "2026-09-19"})
        write_json(
            context["protected_paths"]["controlled_model_signal_latest"],
            {"asof": "2026-09-19"},
        )
        return result

    result = run_shadow(module, job_dir, job, context, mutating_runner)

    assert result["status"] == "FAILED_NONBLOCKING"
    assert result["error_type"] == "ReadonlyBoundaryChanged"
    assert result["protected_unchanged"] is False
    assert result["pending_unchanged"] is False
    assert job["status"] == "daily_auto_update_passed"


def test_malformed_stdout_is_failed_nonblocking(isolated_wf3) -> None:
    module, job_dir, job, context = isolated_wf3

    def malformed(argv, **kwargs):
        kwargs["stdout_path"].write_text("{", encoding="utf-8")
        kwargs["stderr_path"].write_text("", encoding="utf-8")
        return {
            "ok": True,
            "returncode": 0,
            "stdout_path": str(kwargs["stdout_path"]),
            "stderr_path": str(kwargs["stderr_path"]),
        }

    result = run_shadow(module, job_dir, job, context, malformed)

    assert result["status"] == "FAILED_NONBLOCKING"
    assert result["error_type"] == "InvalidWorkflowRunnerOutput"
    assert job["status"] == "daily_auto_update_passed"


def test_missing_run_record_is_failed_nonblocking(isolated_wf3) -> None:
    module, job_dir, job, context = isolated_wf3

    def stdout_only(argv, **kwargs):
        record = workflow_record("SUCCEEDED")
        bind_record_context(record, argv)
        write_json(kwargs["stdout_path"], record)
        kwargs["stderr_path"].write_text("", encoding="utf-8")
        return {
            "ok": True,
            "returncode": 0,
            "stdout_path": str(kwargs["stdout_path"]),
            "stderr_path": str(kwargs["stderr_path"]),
        }

    result = run_shadow(module, job_dir, job, context, stdout_only)

    assert result["status"] == "FAILED_NONBLOCKING"
    assert "run record is missing" in result["error"]
    assert job["status"] == "daily_auto_update_passed"


def test_wrong_full_replay_admission_is_failed_nonblocking(isolated_wf3) -> None:
    module, job_dir, job, context = isolated_wf3

    def wrong_admission(argv, **kwargs):
        record = workflow_record("SUCCEEDED")
        bind_record_context(record, argv)
        record["nodes"]["observe_model_a_replay_window"]["output"][
            "full_replay_contract_admission"
        ] = True
        write_json(kwargs["stdout_path"], record)
        workspace = Path(argv[argv.index("--workspace") + 1])
        write_json(workspace / "runs" / f"{record['run_id']}.json", record)
        kwargs["stderr_path"].write_text("", encoding="utf-8")
        return {
            "ok": True,
            "returncode": 0,
            "stdout_path": str(kwargs["stdout_path"]),
            "stderr_path": str(kwargs["stderr_path"]),
        }

    result = run_shadow(module, job_dir, job, context, wrong_admission)

    assert result["status"] == "FAILED_NONBLOCKING"
    assert "admission must remain false" in result["error"]
    assert job["status"] == "daily_auto_update_passed"


def test_runner_symlink_is_rejected_before_invocation(
    isolated_wf3, tmp_path: Path
) -> None:
    module, job_dir, job, context = isolated_wf3
    fake_root = tmp_path / "runner_repo"
    runner = fake_root / "scripts/run_tw_stock_workflow.py"
    runner.parent.mkdir(parents=True)
    target = fake_root / "other_runner.py"
    target.write_text("pass\n", encoding="utf-8")
    runner.symlink_to(target)
    spec = fake_root / "configs/workflows/replay_window_observation.yaml"
    spec.parent.mkdir(parents=True)
    spec.write_bytes(context["spec_path"].read_bytes())
    calls: list[dict] = []

    result = run_shadow(
        module,
        job_dir,
        job,
        context,
        lambda *args, **kwargs: calls.append(kwargs),
        repo_root=fake_root,
        workflow_runner_path=runner,
        spec_path=spec,
    )

    assert calls == []
    assert result["status"] == "ERROR_NONBLOCKING"
    assert "regular repository workflow CLI" in result["error"]
    assert job["status"] == "daily_auto_update_passed"


def test_missing_replay_artifact_identity_is_failed_nonblocking(isolated_wf3) -> None:
    module, job_dir, job, context = isolated_wf3

    def missing_artifact(argv, **kwargs):
        record = workflow_record("SUCCEEDED")
        bind_record_context(record, argv)
        record["artifact_inputs"]["observe_model_a_replay_window"] = []
        record["identity_payload"]["artifact_inputs"] = record["artifact_inputs"]
        resign_record(record)
        write_json(kwargs["stdout_path"], record)
        workspace = Path(argv[argv.index("--workspace") + 1])
        write_json(workspace / "runs" / f"{record['run_id']}.json", record)
        kwargs["stderr_path"].write_text("", encoding="utf-8")
        return {
            "ok": True,
            "returncode": 0,
            "stdout_path": str(kwargs["stdout_path"]),
            "stderr_path": str(kwargs["stderr_path"]),
        }

    result = run_shadow(module, job_dir, job, context, missing_artifact)

    assert result["status"] == "FAILED_NONBLOCKING"
    assert "exactly one replay artifact" in result["error"]


def test_run_record_context_mismatch_is_failed_nonblocking(isolated_wf3) -> None:
    module, job_dir, job, context = isolated_wf3

    def wrong_context(argv, **kwargs):
        record = workflow_record("SUCCEEDED")
        bind_record_context(record, argv)
        record["context"]["permissions"] = ["artifact.read"]
        resign_record(record)
        write_json(kwargs["stdout_path"], record)
        workspace = Path(argv[argv.index("--workspace") + 1])
        write_json(workspace / "runs" / f"{record['run_id']}.json", record)
        kwargs["stderr_path"].write_text("", encoding="utf-8")
        return {
            "ok": True,
            "returncode": 0,
            "stdout_path": str(kwargs["stdout_path"]),
            "stderr_path": str(kwargs["stderr_path"]),
        }

    result = run_shadow(module, job_dir, job, context, wrong_context)

    assert result["status"] == "FAILED_NONBLOCKING"
    assert "context does not match" in result["error"]


def test_preexisting_stdout_symlink_is_rejected_before_runner(
    isolated_wf3, tmp_path: Path
) -> None:
    module, job_dir, job, context = isolated_wf3
    outside = tmp_path / "outside_stdout.json"
    outside.write_text("untouched\n", encoding="utf-8")
    (job_dir / "workflow_readonly_shadow_stdout.json").symlink_to(outside)
    calls: list[dict] = []

    result = run_shadow(
        module,
        job_dir,
        job,
        context,
        lambda *args, **kwargs: calls.append(kwargs),
    )

    assert calls == []
    assert result["status"] == "ERROR_NONBLOCKING"
    assert "stdout/stderr may not be a symlink" in result["error"]
    assert outside.read_text(encoding="utf-8") == "untouched\n"


def test_runner_returned_evidence_path_mismatch_is_rejected(
    isolated_wf3, tmp_path: Path
) -> None:
    module, job_dir, job, context = isolated_wf3
    calls: list[dict] = []
    base_runner = fake_runner_for("SUCCEEDED", 0, calls)

    def redirected(argv, **kwargs):
        result = base_runner(argv, **kwargs)
        outside = tmp_path / "outside_stdout.json"
        outside.write_text(
            kwargs["stdout_path"].read_text(encoding="utf-8"), encoding="utf-8"
        )
        result["stdout_path"] = str(outside)
        return result

    result = run_shadow(module, job_dir, job, context, redirected)

    assert result["status"] == "ERROR_NONBLOCKING"
    assert "evidence path changed" in result["error"]
    assert job["status"] == "daily_auto_update_passed"


def test_signed_run_record_with_changed_workflow_spec_is_rejected(isolated_wf3) -> None:
    module, job_dir, job, context = isolated_wf3

    def changed_spec(argv, **kwargs):
        record = workflow_record("SUCCEEDED")
        bind_record_context(record, argv)
        workflow = record["identity_payload"]["workflow"]
        workflow["nodes"][0]["config"]["min_count"] = 0
        resign_record(record)
        write_json(kwargs["stdout_path"], record)
        workspace = Path(argv[argv.index("--workspace") + 1])
        write_json(workspace / "runs" / f"{record['run_id']}.json", record)
        kwargs["stderr_path"].write_text("", encoding="utf-8")
        return {
            "ok": True,
            "returncode": 0,
            "stdout_path": str(kwargs["stdout_path"]),
            "stderr_path": str(kwargs["stderr_path"]),
        }

    result = run_shadow(module, job_dir, job, context, changed_spec)

    assert result["status"] == "FAILED_NONBLOCKING"
    assert "spec identity changed" in result["error"]
    assert job["status"] == "daily_auto_update_passed"
