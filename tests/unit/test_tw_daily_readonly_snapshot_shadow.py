from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from tw_stock_workflow.artifacts import ArtifactRef
from tw_stock_workflow.run_registry import run_id_for_identity


ROOT = Path(__file__).resolve().parents[2]
HELPER = ROOT / "scripts/tw_daily_readonly_snapshot_shadow.py"
MODEL_A = "e4_frozen_qlib_2018_2022"
ASOF = "2026-09-18"


def load_helper():
    spec = importlib.util.spec_from_file_location("wf4b_helper_test", HELPER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")


def dapr18(*, status: str = "auto_publish_chain_completed") -> dict:
    manifest = (
        "data_tw/artifacts/publish/readonly_strategy_snapshot/"
        f"{ASOF}/manifest.json"
    )
    current_state = {
        "schema_version": "dapr18p1.product_latest_state.v1",
        "target_asof": ASOF,
        "controlled_signal_latest_asof": ASOF,
        "readonly_snapshot_latest_asof": ASOF,
        "agent_prompt_latest_asof": ASOF,
        "readonly_snapshot_manifest": manifest,
        "agent_prompt_manifest": (
            f"data_tw/artifacts/publish/daily_agent_prompt/{ASOF}/manifest.json"
        ),
        "controlled_signal_run_id": "source_run",
        "all_product_latest_match_target": True,
    }
    if status == "auto_publish_chain_completed":
        state_before = {
            "created_at": "2026-09-18T10:59:58+00:00",
            **current_state,
            "controlled_signal_latest_asof": "2026-09-17",
            "readonly_snapshot_latest_asof": "2026-09-17",
            "agent_prompt_latest_asof": "2026-09-17",
            "controlled_signal_run_id": "previous_source_run",
            "readonly_snapshot_manifest": (
                "data_tw/artifacts/publish/readonly_strategy_snapshot/"
                "2026-09-17/manifest.json"
            ),
            "agent_prompt_manifest": (
                "data_tw/artifacts/publish/daily_agent_prompt/"
                "2026-09-17/manifest.json"
            ),
            "all_product_latest_match_target": False,
        }
        state_after = {
            "created_at": "2026-09-18T11:00:02+00:00",
            **current_state,
        }
        chain = {
            "target_asof": ASOF,
            "ok": True,
            "status": "pass",
            "steps": [
                {
                    "name": "dapr13_actual_readonly_snapshot_publish",
                    "ok": True,
                    "stdout_payload": {
                        "status": "pass",
                        "target_asof": ASOF,
                        "snapshot_manifest": manifest,
                    },
                }
            ],
        }
        wrote = True
    else:
        state_before = {
            "created_at": "2026-09-18T10:59:58+00:00",
            **current_state,
        }
        state_after = {
            "created_at": "2026-09-18T11:00:02+00:00",
            **current_state,
        }
        chain = {
            "target_asof": ASOF,
            "ok": True,
            "status": "idempotent_noop",
            "reason": "all_product_latest_already_match_target_asof",
            "steps": [],
        }
        wrote = False
    return {
        "enabled": True,
        "attempted": True,
        "ok": True,
        "status": status,
        "publish_readonly_snapshot_latest": True,
        "forbidden_actions_all_false": True,
        "forbidden_protected_paths_unchanged": True,
        "authorization_gate": {"allowed": True},
        "product_latest_state_before": state_before,
        "product_latest_state_after": state_after,
        "auto_publish_chain": chain,
        "readonly_snapshot_latest_write_performed": wrote,
    }


@pytest.fixture()
def isolated_wf4b(tmp_path: Path, monkeypatch):
    module = load_helper()
    repo = tmp_path / "repo"
    spec_path = repo / "configs/workflows/readonly_strategy_snapshot_observation.yaml"
    spec_path.parent.mkdir(parents=True)
    spec_path.write_bytes(
        (ROOT / "configs/workflows/readonly_strategy_snapshot_observation.yaml").read_bytes()
    )
    runner = repo / "scripts/run_tw_stock_workflow.py"
    runner.parent.mkdir(parents=True)
    runner.write_text("# fixture\n", encoding="utf-8")
    file_paths = {
        "manifest_path": (
            f"data_tw/artifacts/publish/readonly_strategy_snapshot/{ASOF}/manifest.json"
        ),
        "latest": "data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json",
        "checksum": (
            f"data_tw/artifacts/publish/readonly_strategy_snapshot/{ASOF}/checksum_manifest.json"
        ),
        "registry": "configs/tw_product_artifact_registry.yaml",
        "baseline": "configs/active_baseline_descriptor.yaml",
        "snapshot": (
            f"data_tw/artifacts/publish/readonly_strategy_snapshot/{ASOF}/strategy_snapshot.json"
        ),
        "source_manifest": f"data_tw/artifacts/signals/{MODEL_A}/source_run/manifest.json",
        "source_csv": f"data_tw/artifacts/signals/{MODEL_A}/source_run/signals.csv",
        "source_latest": f"data_tw/artifacts/signals/{MODEL_A}/latest.json",
    }
    for name, relative in file_paths.items():
        path = repo / relative
        if name == "source_csv":
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("signals\n", encoding="utf-8")
        else:
            write_json(path, {"name": name})
    record = lambda path: {  # noqa: E731
        "path": path,
        "size_bytes": (repo / path).stat().st_size,
        "sha256": "a" * 64,
    }
    ref = ArtifactRef(
        adapter_id="readonly_strategy_snapshot.v1",
        artifact_type="ReadonlyStrategySnapshot",
        model_id=MODEL_A,
        asof=ASOF,
        status="VALIDATED_READONLY",
        run_id="source_run",
        path=str(Path(file_paths["manifest_path"]).parent),
        manifest_path=file_paths["manifest_path"],
        manifest_sha256="a" * 64,
        metadata={
            "candidate_only": True,
            "full_strategy_status": "NOT_BUILT",
            "strategy_rule": "candidate_only_no_strategy_replay",
            "production_allowed": False,
            "no_apply": True,
            "mainline_blocking": False,
            "latest_pointer": record(file_paths["latest"]),
            "checksum_manifest": record(file_paths["checksum"]),
            "product_registry": record(file_paths["registry"]),
            "baseline_descriptor": record(file_paths["baseline"]),
            "source_signal_latest": record(file_paths["source_latest"]),
            "declared_files": {
                "manifest.json": record(file_paths["manifest_path"]),
                "strategy_snapshot.json": record(file_paths["snapshot"]),
            },
            "source_signal_files": {
                "manifest.json": record(file_paths["source_manifest"]),
                "signals.csv": record(file_paths["source_csv"]),
            },
        },
    ).to_dict()

    class FakeAdapter:
        def __init__(self, repo_root):
            assert repo_root == repo

        def query(self, **kwargs):
            return [ArtifactRef(**ref)]

    monkeypatch.setattr(module, "ReadonlyStrategySnapshotAdapter", FakeAdapter)
    protected = {"provider": repo / "protected/provider.json"}
    write_json(protected["provider"], {"asof": ASOF})
    pending = repo / "protected/pending.json"
    cron = repo / "protected/cron.txt"
    write_json(pending, {"asof": ASOF})
    cron.write_text("cron\n", encoding="utf-8")
    job_dir = repo / "jobs/daily_test"
    job_dir.mkdir(parents=True)
    job = {
        "job_id": "daily_test",
        "status": "daily_auto_update_passed",
        "finished_at": "2026-09-18T11:00:00+00:00",
        "dapr18_controlled_latest_orchestration": dapr18(),
    }
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
    return module, repo, job_dir, job, context, ref


def run_shadow(module, job_dir, job, context, runner, *, enabled=True):
    return module.run_daily_readonly_snapshot_shadow(
        job=job,
        job_dir=job_dir,
        asof=ASOF,
        enabled=enabled,
        command_runner=runner,
        **context,
    )


def fake_runner(module, expected_ref, calls):
    def run(argv, **kwargs):
        calls.append({"argv": argv, **kwargs})
        workspace = Path(argv[argv.index("--workspace") + 1]).resolve()
        workflow = module._expected_workflow_identity(MODEL_A)
        context = {
            "mode": "readonly",
            "asof": ASOF,
            "decision_cutoff": "2026-09-18T11:00:00+00:00",
            "workspace": str(workspace),
            "permissions": ["artifact.read"],
        }
        artifact_inputs = {"observe_model_a_readonly_snapshot": [expected_ref]}
        identity = {
            "workflow": workflow,
            "context": context,
            "artifact_inputs": artifact_inputs,
            "artifact_input_errors": {},
        }
        run_id, digest = run_id_for_identity(identity)
        output = {
            "count": 1,
            "query": {
                "artifact_type": "ReadonlyStrategySnapshot",
                "model_id": MODEL_A,
                "asof": ASOF,
                "status": "VALIDATED_READONLY",
                "require_candidate_only": True,
            },
            "artifacts": [expected_ref],
            "full_strategy_admission": False,
        }
        record = {
            "schema_version": "tw.workflow.run.v1",
            "run_id": run_id,
            "identity_sha256": digest,
            "identity_payload": identity,
            "workflow_id": "readonly_strategy_snapshot.model_a_observation",
            "workflow_version": "1",
            "context": context,
            "artifact_inputs": artifact_inputs,
            "artifact_input_errors": {},
            "status": "SUCCEEDED",
            "started_at": "2026-09-18T11:00:00+00:00",
            "finished_at": "2026-09-18T11:00:01+00:00",
            "nodes": {
                "observe_model_a_readonly_snapshot": {
                    "status": "SUCCEEDED",
                    "policy": "required",
                    "module": "readonly_strategy_snapshot.observe",
                    "output": output,
                }
            },
        }
        write_json(kwargs["stdout_path"], record)
        write_json(workspace / "runs" / f"{run_id}.json", record)
        kwargs["stderr_path"].write_text("", encoding="utf-8")
        return {
            "ok": True,
            "returncode": 0,
            "stdout_path": str(kwargs["stdout_path"]),
            "stderr_path": str(kwargs["stderr_path"]),
        }

    return run


def test_default_off_does_not_construct_adapter_or_read_configs(tmp_path: Path) -> None:
    module = load_helper()
    repo = tmp_path / "empty_repo"
    repo.mkdir()
    job_dir = repo / "job"
    job_dir.mkdir()
    result = module.run_daily_readonly_snapshot_shadow(
        job={"status": "daily_auto_update_passed"},
        job_dir=job_dir,
        asof=ASOF,
        enabled=False,
        repo_root=repo,
        python_executable="python",
        workflow_runner_path=repo / "missing_runner.py",
        spec_path=repo / "missing_spec.yaml",
        expected_model_id=MODEL_A,
        protected_paths={},
        pending_path=repo / "missing_pending.json",
        installed_cron_path=repo / "missing_cron",
        command_runner=lambda *args, **kwargs: pytest.fail("runner called"),
    )

    assert result["status"] == "DISABLED_BY_DEFAULT"
    assert result["attempted"] is False


def test_enabled_missing_adapter_config_is_nonblocking(tmp_path: Path) -> None:
    module = load_helper()
    repo = tmp_path / "empty_repo"
    repo.mkdir()
    job_dir = repo / "job"
    job_dir.mkdir()
    job = {
        "status": "daily_auto_update_passed",
        "finished_at": "2026-09-18T11:00:00+00:00",
        "dapr18_controlled_latest_orchestration": dapr18(),
    }
    result = module.run_daily_readonly_snapshot_shadow(
        job=job,
        job_dir=job_dir,
        asof=ASOF,
        enabled=True,
        repo_root=repo,
        python_executable="python",
        workflow_runner_path=repo / "missing_runner.py",
        spec_path=repo / "missing_spec.yaml",
        expected_model_id=MODEL_A,
        protected_paths={},
        pending_path=repo / "missing_pending.json",
        installed_cron_path=repo / "missing_cron",
        command_runner=lambda *args, **kwargs: pytest.fail("runner called"),
    )

    assert result["status"] == "ERROR_NONBLOCKING"
    assert result["attempted"] is False
    assert result["mainline_status_after"] == "daily_auto_update_passed"


def test_current_dapr18_publish_runs_readonly_snapshot_observation(
    isolated_wf4b,
) -> None:
    module, _, job_dir, job, context, ref = isolated_wf4b
    calls = []
    result = run_shadow(
        module, job_dir, job, context, fake_runner(module, ref, calls)
    )

    assert result["status"] == "SUCCEEDED_NONBLOCKING"
    assert result["observed_artifact_asof"] == ASOF
    assert result["snapshot_source_run_id"] == "source_run"
    assert result["full_strategy_admission"] is False
    evidence = job["dapr18_controlled_latest_orchestration"]
    assert (
        evidence["product_latest_state_before"]["controlled_signal_run_id"]
        == "previous_source_run"
    )
    assert (
        evidence["product_latest_state_before"]["all_product_latest_match_target"]
        is False
    )
    assert calls[0]["argv"][calls[0]["argv"].index("--permission") + 1] == (
        "artifact.read"
    )
    assert Path(calls[0]["argv"][calls[0]["argv"].index("--workspace") + 1]) == (
        job_dir / "workflow_readonly_snapshot_shadow"
    )
    assert "snapshot_source_signal_latest" in result["protected_before"]


def test_snapshot_ref_change_during_runner_fails_nonblocking(
    isolated_wf4b, monkeypatch
) -> None:
    module, repo, job_dir, job, context, ref = isolated_wf4b
    drifted_ref = {**ref, "manifest_sha256": "b" * 64}

    class DriftingAdapter:
        query_count = 0

        def __init__(self, repo_root):
            assert repo_root == repo

        def query(self, **kwargs):
            type(self).query_count += 1
            current = ref if type(self).query_count <= 2 else drifted_ref
            return [ArtifactRef(**current)]

    monkeypatch.setattr(module, "ReadonlyStrategySnapshotAdapter", DriftingAdapter)
    result = run_shadow(module, job_dir, job, context, fake_runner(module, ref, []))

    assert result["status"] == "FAILED_NONBLOCKING"
    assert result["error_type"] == "InvalidWorkflowRunnerOutput"
    assert "changed during observation" in result["error"]
    assert result["mainline_status_after"] == "daily_auto_update_passed"
    assert result["protected_unchanged"] is True
    assert result["pending_unchanged"] is True


def test_failed_dapr18_cannot_observe_old_latest(isolated_wf4b) -> None:
    module, _, job_dir, job, context, _ = isolated_wf4b
    job["dapr18_controlled_latest_orchestration"]["ok"] = False
    calls = []
    result = run_shadow(
        module,
        job_dir,
        job,
        context,
        lambda *args, **kwargs: calls.append(kwargs),
    )

    assert result["status"] == "BLOCKED_NONBLOCKING"
    assert result["attempted"] is False
    assert calls == []


def test_exact_same_day_idempotent_evidence_is_accepted(isolated_wf4b) -> None:
    module, _, job_dir, job, context, ref = isolated_wf4b
    job["dapr18_controlled_latest_orchestration"] = dapr18(
        status="auto_publish_idempotent_noop_already_current"
    )
    result = run_shadow(module, job_dir, job, context, fake_runner(module, ref, []))
    assert result["status"] == "SUCCEEDED_NONBLOCKING"
    evidence = job["dapr18_controlled_latest_orchestration"]
    assert (
        evidence["product_latest_state_before"]["created_at"]
        != evidence["product_latest_state_after"]["created_at"]
    )


def test_dapr18_controlled_run_mismatch_blocks_before_runner(isolated_wf4b) -> None:
    module, _, job_dir, job, context, _ = isolated_wf4b
    evidence = dapr18()
    evidence["product_latest_state_after"]["controlled_signal_run_id"] = "run_b"
    job["dapr18_controlled_latest_orchestration"] = evidence

    result = run_shadow(
        module,
        job_dir,
        job,
        context,
        lambda *args, **kwargs: pytest.fail("runner called"),
    )

    assert result["status"] == "BLOCKED_NONBLOCKING"
    assert result["attempted"] is False
    assert result["mainline_status_after"] == "daily_auto_update_passed"


def test_completed_dapr18_allows_current_controlled_run_when_other_latest_is_stale(
    isolated_wf4b,
) -> None:
    module, _, job_dir, job, context, ref = isolated_wf4b
    evidence = dapr18()
    before = evidence["product_latest_state_before"]
    before["controlled_signal_latest_asof"] = ASOF
    before["controlled_signal_run_id"] = "source_run"
    job["dapr18_controlled_latest_orchestration"] = evidence

    result = run_shadow(module, job_dir, job, context, fake_runner(module, ref, []))

    assert result["status"] == "SUCCEEDED_NONBLOCKING"


def test_idempotent_state_drift_is_blocked(isolated_wf4b) -> None:
    module, _, job_dir, job, context, _ = isolated_wf4b
    evidence = dapr18(status="auto_publish_idempotent_noop_already_current")
    evidence["product_latest_state_before"]["readonly_snapshot_manifest"] = "old.json"
    job["dapr18_controlled_latest_orchestration"] = evidence
    result = run_shadow(
        module,
        job_dir,
        job,
        context,
        lambda *args, **kwargs: pytest.fail("runner called"),
    )
    assert result["status"] == "BLOCKED_NONBLOCKING"


def test_idempotent_product_state_unknown_field_is_blocked(isolated_wf4b) -> None:
    module, _, job_dir, job, context, _ = isolated_wf4b
    evidence = dapr18(status="auto_publish_idempotent_noop_already_current")
    evidence["product_latest_state_before"]["unexpected"] = True
    evidence["product_latest_state_after"]["unexpected"] = True
    job["dapr18_controlled_latest_orchestration"] = evidence

    result = run_shadow(
        module,
        job_dir,
        job,
        context,
        lambda *args, **kwargs: pytest.fail("runner called"),
    )

    assert result["status"] == "BLOCKED_NONBLOCKING"
    assert result["attempted"] is False
    assert "product state schema is invalid" in result["error"]


def test_idempotent_product_state_non_boolean_status_is_blocked(
    isolated_wf4b,
) -> None:
    module, _, job_dir, job, context, _ = isolated_wf4b
    evidence = dapr18(status="auto_publish_idempotent_noop_already_current")
    evidence["product_latest_state_before"][
        "all_product_latest_match_target"
    ] = 1
    evidence["product_latest_state_after"]["all_product_latest_match_target"] = 1
    job["dapr18_controlled_latest_orchestration"] = evidence

    result = run_shadow(
        module,
        job_dir,
        job,
        context,
        lambda *args, **kwargs: pytest.fail("runner called"),
    )

    assert result["status"] == "BLOCKED_NONBLOCKING"
    assert result["attempted"] is False
    assert "product state schema is invalid" in result["error"]
