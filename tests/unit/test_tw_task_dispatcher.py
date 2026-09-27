from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml
from jsonschema import Draft202012Validator

from tw_stock_workflow.task_dispatcher import TaskDispatcher, TaskRequestError


ROOT = Path(__file__).resolve().parents[2]


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")


def write_yaml(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def request_schema(repo: Path) -> Path:
    path = repo / "schemas/tw_task_request.schema.json"
    write_json(
        path,
        json.loads(
            (ROOT / "schemas/tw_task_request.schema.json").read_text(encoding="utf-8")
        ),
    )
    return path


def daily_repo(tmp_path: Path) -> tuple[Path, Path]:
    repo = tmp_path / "repo"
    runner = repo / "scripts/run_daily_tw_stock_auto_update.py"
    runner.parent.mkdir(parents=True)
    runner.write_text("raise SystemExit(0)\n", encoding="utf-8")
    write_yaml(
        repo / "configs/readonly_model_tracks.yaml",
        {
            "default_track_id": "model_a_only",
            "tracks": {
                "model_a_only": {"workflow_policy": "required"},
                "model_a_plus_b_b19r2r": {"workflow_policy": "nonblocking"},
            },
        },
    )
    write_yaml(
        repo / "configs/daily_model_tracks.yaml",
        {
            "schema_version": "tw.daily_model_tracks.v1",
            "tracks": {
                "model_a_only": {"runtime_adapter_id": "daily_model_a_v1"},
                "model_a_plus_b_b19r2r": {
                    "runtime_adapter_id": "daily_model_a_plus_b_b19r2r_v1"
                },
            },
        },
    )
    registry = repo / "configs/tw_task_registry.yaml"
    write_yaml(
        registry,
        {
            "schema_version": "tw.task.registry.v1",
            "run_record_schema": "tw.task.run.v1",
            "tasks": {
                "daily_update": {
                    "executor_id": "daily_update_v1",
                    "description": "fixture",
                    "defaults": {
                        "asof": "auto",
                        "model_track_ids": [
                            "model_a_only",
                            "model_a_plus_b_b19r2r",
                        ],
                        "finmind_scope": "full",
                        "force": False,
                        "skip_finmind": False,
                        "skip_qlib": False,
                        "max_workers": 4,
                        "timeout_seconds": 1200,
                    },
                    "parameter_schema": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "asof": {"type": "string"},
                            "model_track_ids": {
                                "type": "array",
                                "minItems": 1,
                                "uniqueItems": True,
                                "items": {"type": "string"},
                            },
                            "finmind_scope": {"enum": ["daily", "full"]},
                            "force": {"type": "boolean"},
                            "skip_finmind": {"type": "boolean"},
                            "skip_qlib": {"type": "boolean"},
                            "max_workers": {"type": "integer"},
                            "timeout_seconds": {"type": "integer"},
                        },
                    },
                    "bindings": {
                        "runner": "scripts/run_daily_tw_stock_auto_update.py",
                        "model_track_governance": "configs/readonly_model_tracks.yaml",
                        "model_track_runtime": "configs/daily_model_tracks.yaml",
                    },
                }
            },
        },
    )
    request_schema(repo)
    return repo, registry


def backtest_repo(tmp_path: Path) -> tuple[Path, Path]:
    repo = tmp_path / "repo"
    for relative in (
        "scripts/build_tw_readonly_replay_window_artifact.py",
        "configs/active_baseline_descriptor.yaml",
        "data/baseline_manifest.json",
        "data/price_store_manifest.json",
    ):
        path = repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{}\n", encoding="utf-8")
    write_yaml(
        repo / "configs/readonly_model_tracks.yaml",
        {
            "tracks": {
                "model_a_only": {"model_id": "model-a"},
                "model_a_plus_b": {"model_id": "model-a-plus-b"},
            }
        },
    )
    write_yaml(
        repo / "configs/tw_replay_window_policy.yaml",
        {
            "allowed_replay_start_min": "2026-01-01",
            "latest_available_signal_date": "2026-05-07",
            "models": {
                "model-a": {
                    "allowed_replay_start_min": "2026-01-01",
                    "qlib_train_start": "2018-01-01",
                    "qlib_train_end": "2022-12-31",
                    "ltr_train_start": "",
                    "ltr_train_end": "",
                    "source_manifest": "data/model.json",
                    "source_training_report": "docs/model.md",
                }
            },
            "diagnostic_rules": {},
        },
    )
    write_yaml(
        repo / "configs/tw_modular_registry.yaml",
        {
            "strategies": {
                "production_selectable": {
                    "top50_exit_one_worst_sell": {
                        "dependency_path": "configs/strategy_dependencies/top50.yaml"
                    }
                }
            }
        },
    )
    registry = repo / "configs/tw_task_registry.yaml"
    write_yaml(
        registry,
        {
            "schema_version": "tw.task.registry.v1",
            "run_record_schema": "tw.task.run.v1",
            "tasks": {
                "readonly_backtest": {
                    "executor_id": "readonly_backtest_v1",
                    "description": "fixture",
                    "defaults": {"timeout_seconds": 1200},
                    "parameter_schema": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": [
                            "model_track_id",
                            "strategy_rule",
                            "start_date",
                            "end_date",
                        ],
                        "properties": {
                            "model_track_id": {"type": "string"},
                            "strategy_rule": {"type": "string"},
                            "start_date": {"type": "string", "format": "date"},
                            "end_date": {"type": "string", "format": "date"},
                            "timeout_seconds": {"type": "integer"},
                        },
                    },
                    "bindings": {
                        "runner": "scripts/build_tw_readonly_replay_window_artifact.py",
                        "model_tracks": "configs/readonly_model_tracks.yaml",
                        "replay_policy": "configs/tw_replay_window_policy.yaml",
                        "modular_registry": "configs/tw_modular_registry.yaml",
                        "baseline_descriptor": "configs/active_baseline_descriptor.yaml",
                        "baseline_manifest": "data/baseline_manifest.json",
                        "price_store_manifest": "data/price_store_manifest.json",
                    },
                }
            },
        },
    )
    request_schema(repo)
    return repo, registry


def daily_request(**parameters) -> dict:
    return {
        "schema_version": "tw.task.request.v1",
        "task_type": "daily_update",
        "parameters": parameters,
    }


def backtest_request(model_track_id: str = "model_a_only") -> dict:
    return {
        "schema_version": "tw.task.request.v1",
        "task_type": "readonly_backtest",
        "parameters": {
            "model_track_id": model_track_id,
            "strategy_rule": "top50_exit_one_worst_sell",
            "start_date": "2026-01-01",
            "end_date": "2026-05-07",
        },
    }


def test_repository_task_request_schema_and_registry_are_valid() -> None:
    schema = json.loads(
        (ROOT / "schemas/tw_task_request.schema.json").read_text(encoding="utf-8")
    )
    Draft202012Validator.check_schema(schema)
    registry = yaml.safe_load(
        (ROOT / "configs/tw_task_registry.yaml").read_text(encoding="utf-8")
    )
    assert registry["schema_version"] == "tw.task.registry.v1"
    assert set(registry["tasks"]) == {
        "daily_update",
        "readonly_backtest",
        "readonly_model_comparison",
    }


def test_daily_plan_resolves_auto_date_and_registered_model_tracks(
    tmp_path: Path,
) -> None:
    repo, registry = daily_repo(tmp_path)
    dispatcher = TaskDispatcher(
        repo,
        registry_path=registry,
        run_root=tmp_path / "runs",
        now_taipei=lambda: datetime(2026, 9, 21, 8, 0, 0),
    )

    plan = dispatcher.plan(daily_request())

    assert plan.normalized_request["parameters"]["asof"] == "2026-09-21"
    assert plan.details["selected_model_track_ids"] == [
        "model_a_only",
        "model_a_plus_b_b19r2r",
    ]
    assert plan.details["required_model_track_ids"] == ["model_a_only"]
    assert "--enable-model-signal-gate" in plan.details["command"]
    assert "--enable-b19r2r-shadow" in plan.details["command"]
    assert plan.details["environment_overrides"][
        "TW_DAILY_AUTO_ENABLE_B19R2R_SHADOW"
    ] == "true"


def test_daily_plan_rejects_omitting_required_model_a(tmp_path: Path) -> None:
    repo, registry = daily_repo(tmp_path)
    dispatcher = TaskDispatcher(repo, registry_path=registry, run_root=tmp_path / "runs")

    with pytest.raises(TaskRequestError, match="cannot omit required model tracks"):
        dispatcher.plan(
            daily_request(model_track_ids=["model_a_plus_b_b19r2r"])
        )


def test_request_cannot_inject_runner_or_unknown_parameter(tmp_path: Path) -> None:
    repo, registry = daily_repo(tmp_path)
    dispatcher = TaskDispatcher(repo, registry_path=registry, run_root=tmp_path / "runs")

    with pytest.raises(TaskRequestError, match="Additional properties"):
        dispatcher.plan(daily_request(runner="/tmp/arbitrary.py"))


def test_backtest_plan_maps_track_and_enforces_replay_policy(tmp_path: Path) -> None:
    repo, registry = backtest_repo(tmp_path)
    dispatcher = TaskDispatcher(repo, registry_path=registry, run_root=tmp_path / "runs")

    plan = dispatcher.plan(backtest_request())

    assert plan.details["model_track_id"] == "model_a_only"
    assert plan.details["model_id"] == "model-a"
    assert plan.details["readonly_only"] is True
    assert plan.details["product_index_admission"] is False

    with pytest.raises(TaskRequestError, match="not replay-enabled"):
        dispatcher.plan(backtest_request("model_a_plus_b"))


def test_daily_task_records_result_but_keeps_same_day_retries(tmp_path: Path) -> None:
    repo, registry = daily_repo(tmp_path)
    calls: list[list[str]] = []

    def fake_runner(command, **kwargs):
        calls.append(list(command))
        kwargs["stdout_path"].parent.mkdir(parents=True, exist_ok=True)
        kwargs["stdout_path"].write_text(
            json.dumps({"status": "daily_ready"}), encoding="utf-8"
        )
        kwargs["stderr_path"].write_text("", encoding="utf-8")
        return {
            "ok": True,
            "returncode": 0,
            "stdout_path": str(kwargs["stdout_path"]),
            "stderr_path": str(kwargs["stderr_path"]),
            "stdout": json.dumps({"status": "daily_ready"}),
            "stderr_tail": "",
        }

    dispatcher = TaskDispatcher(
        repo,
        registry_path=registry,
        run_root=tmp_path / "runs",
        command_runner=fake_runner,
        now_taipei=lambda: datetime(2026, 9, 21, 8, 0, 0),
    )

    first = dispatcher.dispatch(daily_request())
    second = dispatcher.dispatch(daily_request())

    assert first["status"] == "SUCCEEDED"
    assert second["idempotent_reuse"] is False
    assert len(calls) == 2
    assert Path(first["run_dir"], "normalized_request.json").is_file()
    assert Path(first["run_dir"], "plan.json").is_file()
    assert Path(first["run_dir"], "result.json").is_file()


def test_daily_task_rejects_zero_exit_without_structured_result(tmp_path: Path) -> None:
    repo, registry = daily_repo(tmp_path)

    def fake_runner(command, **kwargs):
        kwargs["stdout_path"].parent.mkdir(parents=True, exist_ok=True)
        kwargs["stdout_path"].write_text("", encoding="utf-8")
        kwargs["stderr_path"].write_text("runner emitted no JSON", encoding="utf-8")
        return {
            "ok": True,
            "returncode": 0,
            "stdout_path": str(kwargs["stdout_path"]),
            "stderr_path": str(kwargs["stderr_path"]),
            "stdout": "",
            "stderr_tail": "runner emitted no JSON",
        }

    dispatcher = TaskDispatcher(
        repo,
        registry_path=registry,
        run_root=tmp_path / "runs",
        command_runner=fake_runner,
        now_taipei=lambda: datetime(2026, 9, 21, 8, 0, 0),
    )

    result = dispatcher.dispatch(daily_request())

    assert result["status"] == "FAILED"
    assert result["ok"] is False
    assert result["execution"]["daily_result"] == {}


def test_daily_task_reads_structured_result_after_runner_logs(tmp_path: Path) -> None:
    repo, registry = daily_repo(tmp_path)

    def fake_runner(command, **kwargs):
        stdout = 'INFO optional dependency unavailable\n{"status": "daily_ready"}\n'
        kwargs["stdout_path"].parent.mkdir(parents=True, exist_ok=True)
        kwargs["stdout_path"].write_text(stdout, encoding="utf-8")
        kwargs["stderr_path"].write_text("", encoding="utf-8")
        return {
            "ok": True,
            "returncode": 0,
            "stdout_path": str(kwargs["stdout_path"]),
            "stderr_path": str(kwargs["stderr_path"]),
            "stdout": stdout,
            "stderr_tail": "",
        }

    dispatcher = TaskDispatcher(
        repo,
        registry_path=registry,
        run_root=tmp_path / "runs",
        command_runner=fake_runner,
        now_taipei=lambda: datetime(2026, 9, 21, 8, 0, 0),
    )

    result = dispatcher.dispatch(daily_request())

    assert result["status"] == "SUCCEEDED"
    assert result["execution"]["daily_result"]["status"] == "daily_ready"


def test_backtest_executor_uses_only_registered_bindings(tmp_path: Path) -> None:
    repo, registry = backtest_repo(tmp_path)
    calls: list[list[str]] = []

    def fake_runner(command, **kwargs):
        calls.append(list(command))
        payload = {
            "ok": True,
            "status": "CANDIDATE_HOLD",
            "manifest": "fixture/manifest.json",
        }
        kwargs["stdout_path"].parent.mkdir(parents=True, exist_ok=True)
        kwargs["stdout_path"].write_text(json.dumps(payload), encoding="utf-8")
        kwargs["stderr_path"].write_text("", encoding="utf-8")
        return {
            "ok": True,
            "returncode": 0,
            "stdout_path": str(kwargs["stdout_path"]),
            "stderr_path": str(kwargs["stderr_path"]),
            "stdout": json.dumps(payload),
            "stderr_tail": "",
        }

    dispatcher = TaskDispatcher(
        repo,
        registry_path=registry,
        run_root=tmp_path / "runs",
        command_runner=fake_runner,
    )
    result = dispatcher.dispatch(backtest_request())
    reused = dispatcher.dispatch(backtest_request())

    assert result["status"] == "SUCCEEDED"
    assert reused["idempotent_reuse"] is True
    assert len(calls) == 1
    command = calls[0]
    assert command[command.index("--model-id") + 1] == "model-a"
    assert command[command.index("--strategy-rule") + 1] == (
        "top50_exit_one_worst_sell"
    )
    assert command[command.index("--out-root") + 1].startswith(str(tmp_path / "runs"))


def test_workflow_executor_delegates_to_existing_engine(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    spec = repo / "configs/workflows/comparison.yaml"
    write_yaml(
        spec,
        {
            "schema_version": "tw.workflow.spec.v1",
            "workflow_id": "fixture.comparison",
            "version": "1",
            "nodes": [
                {"id": "observe", "module": "fixture.observe", "policy": "required"}
            ],
        },
    )
    registry = repo / "configs/tw_task_registry.yaml"
    write_yaml(
        registry,
        {
            "schema_version": "tw.task.registry.v1",
            "run_record_schema": "tw.task.run.v1",
            "tasks": {
                "comparison": {
                    "executor_id": "workflow_spec_v1",
                    "description": "fixture",
                    "defaults": {},
                    "parameter_schema": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["asof", "decision_cutoff"],
                        "properties": {
                            "asof": {"type": "string", "format": "date"},
                            "decision_cutoff": {
                                "type": "string",
                                "format": "date-time",
                            },
                        },
                    },
                    "bindings": {
                        "workflow_spec": "configs/workflows/comparison.yaml",
                        "mode": "readonly",
                        "permissions": ["artifact.read"],
                    },
                }
            },
        },
    )
    request_schema(repo)
    calls = []

    def fake_workflow(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(
            status="SUCCEEDED",
            idempotent_reuse=False,
            record={"status": "SUCCEEDED", "run_id": "workflow-fixture"},
        )

    dispatcher = TaskDispatcher(
        repo,
        registry_path=registry,
        run_root=tmp_path / "runs",
        workflow_runner=fake_workflow,
    )
    result = dispatcher.dispatch(
        {
            "schema_version": "tw.task.request.v1",
            "task_type": "comparison",
            "parameters": {
                "asof": "2026-09-01",
                "decision_cutoff": "2026-09-01T10:00:00+00:00",
            },
        }
    )

    assert result["status"] == "SUCCEEDED"
    assert calls[0]["spec_path"] == spec
    assert calls[0]["context"].mode == "readonly"
    assert calls[0]["context"].permissions == frozenset({"artifact.read"})


def test_recent_status_reads_atomic_run_records_without_reexecuting(
    tmp_path: Path,
) -> None:
    repo, registry = daily_repo(tmp_path)

    def fake_runner(command, **kwargs):
        payload = {"status": "daily_ready"}
        kwargs["stdout_path"].parent.mkdir(parents=True, exist_ok=True)
        kwargs["stdout_path"].write_text(json.dumps(payload), encoding="utf-8")
        kwargs["stderr_path"].write_text("", encoding="utf-8")
        return {
            "ok": True,
            "returncode": 0,
            "stdout_path": str(kwargs["stdout_path"]),
            "stderr_path": str(kwargs["stderr_path"]),
            "stdout": json.dumps(payload),
            "stderr_tail": "",
        }

    dispatcher = TaskDispatcher(
        repo,
        registry_path=registry,
        run_root=tmp_path / "runs",
        command_runner=fake_runner,
        now_taipei=lambda: datetime(2026, 9, 21, 8, 0, 0),
    )
    completed = dispatcher.dispatch(daily_request())

    status = dispatcher.recent_status("daily_update")

    assert status["schema_version"] == "tw.task.status.v1"
    assert status["count"] == 1
    assert status["runs"][0]["run_id"] == completed["run_id"]
    assert status["runs"][0]["status"] == "SUCCEEDED"
    assert dispatcher.recent_status("daily_update", limit=1)["count"] == 1


def test_recent_status_rejects_unknown_task_or_invalid_limit(tmp_path: Path) -> None:
    repo, registry = daily_repo(tmp_path)
    dispatcher = TaskDispatcher(repo, registry_path=registry, run_root=tmp_path / "runs")

    with pytest.raises(TaskRequestError, match="unregistered task_type"):
        dispatcher.recent_status("missing")
    with pytest.raises(TaskRequestError, match="between 1 and 100"):
        dispatcher.recent_status(limit=0)
