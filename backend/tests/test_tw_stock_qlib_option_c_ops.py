"""Tests for controlled qlib Option C dry-run ops runner."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from app.services.tw_stock_qlib_option_c_ops import OptionCFileLock, OptionCOpsConfig, QlibOptionCOpsRunner, WRAPPER_SCRIPT
from app.services.tw_stock_qlib_option_c_scheduler import OptionCSchedulerConfig, QlibOptionCDryRunScheduler
from app.services.tw_stock_qlib_option_c_normal_publish import OptionCNormalPublishConfig, QlibOptionCNormalPublishGate
from app.services.tw_stock_qlib_option_c_accepted_latest_scheduler import OptionCAcceptedLatestSchedulerConfig, QlibOptionCAcceptedLatestScheduler
from app.services.tw_stock_qlib_option_c_eod_pipeline import OptionCEodPipelineConfig, QlibOptionCEodPipeline
from app.services.tw_stock_qlib_option_c_eod_automation import OptionCEodAutomationConfig, QlibOptionCEodAutomationScheduler


def make_runner(tmp_path: Path, **overrides) -> QlibOptionCOpsRunner:
    qlib = tmp_path / "qlib"
    qlib.mkdir(exist_ok=True)
    latest = tmp_path / "latest_signal.json"
    latest.write_text('{"status":"unchanged"}', encoding="utf-8")
    config = {
        "qlib_cwd": qlib,
        "ops_root": tmp_path / "ops",
        "latest_signal": latest,
        "timeout_seconds": 3,
    }
    config.update(overrides)
    return QlibOptionCOpsRunner(OptionCOpsConfig(**config))


def admin_headers():
    return {"Authorization": "Bearer admin-token"}


def user_headers():
    return {"Authorization": "Bearer user-token"}


def patch_auth(monkeypatch, role: str = "admin"):
    from app import utils as app_utils
    monkeypatch.setattr(
        app_utils.auth,
        "verify_token",
        lambda _raw: {"sub": "tester", "user_id": 42, "role": role},
    )


def fake_completed(stdout: str, stderr: str = "", returncode: int = 0) -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr=stderr)


def test_runner_rejects_invalid_asof_and_extra_parameters(tmp_path):
    runner = make_runner(tmp_path)

    invalid = runner.trigger_dry_run({"asof": "20260601"})
    extra = runner.trigger_dry_run({"asof": "2026-06-01", "provider_uri": "/tmp/bad"})

    assert invalid["ok"] is False
    assert invalid["status"] == "blocked"
    assert extra["ok"] is False
    assert extra["status"] == "blocked"
    assert extra["trading"]["orders_enabled"] is False


def test_runner_uses_fixed_allowlisted_argv(tmp_path, monkeypatch):
    runner = make_runner(tmp_path)
    seen = {}

    def fake_execute(argv, *, timeout):
        seen["argv"] = argv
        seen["timeout"] = timeout
        return fake_completed(json.dumps({"status": "dry_run_preflight_pass"}))

    monkeypatch.setattr(runner, "_execute_subprocess", fake_execute)
    result = runner.trigger_dry_run({"asof": "2026-06-01"})

    assert result["status"] == "dry_run_passed"
    assert seen["argv"] == ["python", WRAPPER_SCRIPT, "--asof", "2026-06-01", "--dry-run"]
    assert "--provider-uri" not in seen["argv"]
    assert "--max-workers" not in seen["argv"]
    assert seen["timeout"] == 3
    assert result["normal_signal_run"] is False


def test_file_lock_acquire_and_release(tmp_path):
    lock = OptionCFileLock(tmp_path / "ops" / "option_c_ops.lock", stale_seconds=60)

    acquired = lock.acquire(job_id="job-a")
    blocked = lock.acquire(job_id="job-b")
    released = lock.release(job_id="job-a")

    assert acquired["ok"] is True
    assert acquired["owner"]["owner_pid"]
    assert acquired["owner"]["job_id"] == "job-a"
    assert blocked["ok"] is False
    assert blocked["status"] == "conflict"
    assert released is True
    assert not lock.path.exists()


def test_runner_rejects_concurrent_job_with_file_lock(tmp_path):
    runner = make_runner(tmp_path)
    lock = OptionCFileLock(runner.config.ops_root / "option_c_ops.lock", stale_seconds=60)
    assert lock.acquire(job_id="external-job")["ok"] is True
    try:
        result = runner.trigger_dry_run({"asof": "2026-06-01"})
    finally:
        lock.release(job_id="external-job")

    assert result["ok"] is False
    assert result["status"] == "conflict"


def test_runner_recovers_stale_file_lock(tmp_path, monkeypatch):
    runner = make_runner(tmp_path, lock_stale_seconds=1)
    lock_path = runner.config.ops_root / "option_c_ops.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path.write_text(
        json.dumps({"owner_pid": 999999, "job_id": "old-job", "started_at": "2000-01-01T00:00:00+00:00"}),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        runner,
        "_execute_subprocess",
        lambda argv, *, timeout: fake_completed(json.dumps({"status": "dry_run_preflight_pass"})),
    )

    result = runner.trigger_dry_run({"asof": "2026-06-01"})

    assert result["status"] == "dry_run_passed"
    assert not lock_path.exists()


def test_runner_releases_file_lock_on_failure_path(tmp_path, monkeypatch):
    runner = make_runner(tmp_path)
    lock_path = runner.config.ops_root / "option_c_ops.lock"
    monkeypatch.setattr(
        runner,
        "_execute_subprocess",
        lambda argv, *, timeout: fake_completed(json.dumps({"status": "blocked_formal_validation_failed"}), returncode=1),
    )

    result = runner.trigger_dry_run({"asof": "2026-06-01"})

    assert result["status"] == "dry_run_failed"
    assert not lock_path.exists()


def test_runner_parses_failure_status(tmp_path, monkeypatch):
    runner = make_runner(tmp_path)

    monkeypatch.setattr(
        runner,
        "_execute_subprocess",
        lambda argv, *, timeout: fake_completed(json.dumps({"status": "blocked_formal_validation_failed"}), returncode=1),
    )

    result = runner.trigger_dry_run({"asof": "2026-06-01"})

    assert result["ok"] is False
    assert result["status"] == "dry_run_failed"
    assert result["parsed_dry_run_status"] == "blocked_formal_validation_failed"
    assert result["latest_signal_updated"] is False


def test_runner_blocks_if_latest_signal_changes(tmp_path, monkeypatch):
    runner = make_runner(tmp_path)

    def fake_execute(argv, *, timeout):
        runner.config.latest_signal.write_text('{"status":"changed"}', encoding="utf-8")
        return fake_completed(json.dumps({"status": "dry_run_preflight_pass"}))

    monkeypatch.setattr(runner, "_execute_subprocess", fake_execute)
    result = runner.trigger_dry_run({"asof": "2026-06-01"})

    assert result["ok"] is False
    assert result["status"] == "blocked_latest_signal_changed"
    assert result["latest_signal_updated"] is True


def test_ops_api_success_status_latest_and_log_tail(client, monkeypatch, tmp_path):
    patch_auth(monkeypatch, "admin")
    runner = make_runner(tmp_path)

    monkeypatch.setattr(
        runner,
        "_execute_subprocess",
        lambda argv, *, timeout: fake_completed(json.dumps({"status": "dry_run_preflight_pass"}) + "\n"),
    )
    from app.routes import tw_stock as tw_stock_route

    monkeypatch.setattr(tw_stock_route, "option_c_ops_runner", runner)
    resp = client.post("/api/tw-stock/quant/ops/option-c/dry-run", json={"asof": "2026-06-01"}, headers=admin_headers())
    payload = resp.get_json()

    assert resp.status_code == 200
    assert payload["code"] == 1
    data = payload["data"]
    assert data["status"] == "dry_run_passed"
    assert data["trading"]["orders_enabled"] is False
    assert data["trading"]["connects_to_broker"] is False
    assert data["trading"]["research_signal_not_order"] is True
    assert data["latest_signal_updated"] is False
    assert data["argv"] == ["python", WRAPPER_SCRIPT, "--asof", "2026-06-01", "--dry-run"]

    job_id = data["job_id"]
    status_resp = client.get(f"/api/tw-stock/quant/ops/option-c/jobs/{job_id}")
    assert status_resp.status_code == 200
    assert status_resp.get_json()["data"]["job_id"] == job_id

    latest_resp = client.get("/api/tw-stock/quant/ops/option-c/latest")
    assert latest_resp.status_code == 200
    assert latest_resp.get_json()["data"]["job"]["job_id"] == job_id

    log_resp = client.get(f"/api/tw-stock/quant/ops/option-c/jobs/{job_id}/logs?stream=stdout", headers=admin_headers())
    assert log_resp.status_code == 200
    log_data = log_resp.get_json()["data"]
    assert "dry_run_preflight_pass" in log_data["tail"]
    assert "latest_signal.json" not in log_data["tail"]


def test_ops_api_rejects_extra_parameter(client, monkeypatch, tmp_path):
    patch_auth(monkeypatch, "admin")
    runner = make_runner(tmp_path)
    from app.routes import tw_stock as tw_stock_route

    monkeypatch.setattr(tw_stock_route, "option_c_ops_runner", runner)
    resp = client.post("/api/tw-stock/quant/ops/option-c/dry-run", json={"asof": "2026-06-01", "cwd": "/tmp"}, headers=admin_headers())

    assert resp.status_code == 400
    payload = resp.get_json()
    assert payload["code"] == 0
    assert payload["data"]["status"] == "blocked"
    assert payload["data"]["trading"]["orders_enabled"] is False


def test_ops_api_rejects_anonymous_dry_run(client, monkeypatch, tmp_path):
    from app.routes import tw_stock as tw_stock_route

    monkeypatch.setattr(tw_stock_route, "option_c_ops_runner", make_runner(tmp_path))
    resp = client.post("/api/tw-stock/quant/ops/option-c/dry-run", json={"asof": "2026-06-01"})

    assert resp.status_code == 401
    assert resp.get_json()["code"] == 401


def test_ops_api_rejects_normal_user_dry_run(client, monkeypatch, tmp_path):
    patch_auth(monkeypatch, "user")
    from app.routes import tw_stock as tw_stock_route

    monkeypatch.setattr(tw_stock_route, "option_c_ops_runner", make_runner(tmp_path))
    resp = client.post("/api/tw-stock/quant/ops/option-c/dry-run", json={"asof": "2026-06-01"}, headers=user_headers())

    assert resp.status_code == 403
    assert "Option C ops" in resp.get_json()["msg"]


def test_ops_api_log_tail_requires_auth_and_rejects_arbitrary_path(client, monkeypatch, tmp_path):
    runner = make_runner(tmp_path)
    from app.routes import tw_stock as tw_stock_route

    monkeypatch.setattr(tw_stock_route, "option_c_ops_runner", runner)
    bad_job_id = "not_a_valid_job_id"
    anonymous = client.get(f"/api/tw-stock/quant/ops/option-c/jobs/{bad_job_id}/logs?stream=stdout")
    assert anonymous.status_code == 401

    patch_auth(monkeypatch, "admin")
    authed = client.get(f"/api/tw-stock/quant/ops/option-c/jobs/{bad_job_id}/logs?stream=stdout", headers=admin_headers())
    assert authed.status_code == 400
    assert authed.get_json()["data"]["status"] == "invalid_job_id"


def test_cleanup_jobs_removes_only_ops_job_dirs(tmp_path):
    runner = make_runner(
        tmp_path,
        retention_max_jobs=1,
        retention_max_age_days=1,
        retention_keep_failed_jobs=False,
        retention_keep_latest_success=True,
    )
    runner.config.ops_root.mkdir(parents=True, exist_ok=True)
    (runner.config.ops_root / "option_c_ops.lock").write_text("lock", encoding="utf-8")
    (runner.config.ops_root / "not_a_job").mkdir()

    old_job = runner.config.ops_root / "option_c_dry_run_20260501_20260501T000000Z_aaaaaaaa"
    new_job = runner.config.ops_root / "option_c_dry_run_20260601_20260601T000000Z_bbbbbbbb"
    for job_dir, status in [(old_job, "dry_run_failed"), (new_job, "dry_run_passed")]:
        job_dir.mkdir()
        (job_dir / "stdout.txt").write_text("x", encoding="utf-8")
        (job_dir / "stderr.txt").write_text("", encoding="utf-8")
        (job_dir / "job.json").write_text(json.dumps({"status": status}), encoding="utf-8")
    old_time = 1000000000
    for child in [old_job / "job.json", old_job / "stdout.txt", old_job / "stderr.txt"]:
        child.touch()
        import os
        os.utime(child, (old_time, old_time))

    result = runner.cleanup_jobs()

    assert old_job.name in result["removed"]
    assert not old_job.exists()
    assert new_job.exists()
    assert (runner.config.ops_root / "option_c_ops.lock").exists()
    assert (runner.config.ops_root / "not_a_job").exists()


class FakeSchedulerRunner:
    def __init__(self, result=None):
        self.calls = []
        self.result = result or {
            "ok": True,
            "status": "dry_run_passed",
            "job_id": "option_c_dry_run_20260601_20260602T000000Z_12345678",
            "latest_signal_updated": False,
            "normal_signal_run": False,
            "accepted_artifact_generated": False,
            "trading": {"orders_enabled": False, "connects_to_broker": False, "research_signal_not_order": True},
        }

    def trigger_dry_run(self, payload):
        self.calls.append(payload)
        return dict(self.result)


def test_scheduler_defaults_disabled_and_no_auto_trigger(monkeypatch, tmp_path):
    for name in [
        "ENABLE_TW_QLIB_OPTION_C_SCHEDULER",
        "TW_QLIB_OPTION_C_SCHEDULER_TIME",
        "TW_QLIB_OPTION_C_SCHEDULER_TZ",
        "TW_QLIB_OPTION_C_SCHEDULER_MODE",
    ]:
        monkeypatch.delenv(name, raising=False)
    runner = FakeSchedulerRunner()
    calendar = tmp_path / "day.txt"
    calendar.write_text("2026-05-29\n2026-06-01\n", encoding="utf-8")
    scheduler = QlibOptionCDryRunScheduler(OptionCSchedulerConfig(provider_calendar=calendar), runner=runner)

    status = scheduler.status()

    assert status["ok"] is True
    assert status["enabled"] is False
    assert status["configured_enabled"] is False
    assert status["mode"] == "dry-run-only"
    assert status["next_run_at"] is None
    assert status["auto_loop_started"] is False
    assert status["trading"]["orders_enabled"] is False
    assert runner.calls == []


def test_scheduler_rejects_non_dry_run_only_mode():
    runner = FakeSchedulerRunner()
    scheduler = QlibOptionCDryRunScheduler(OptionCSchedulerConfig(enabled=True, mode="normal"), runner=runner)

    status = scheduler.status()
    tick = scheduler.tick({"asof": "2026-06-01", "dry_run_only": True})

    assert status["ok"] is False
    assert status["enabled"] is False
    assert tick["ok"] is False
    assert tick["status"] == "blocked"
    assert "dry-run-only" in tick["message"]
    assert runner.calls == []


def test_scheduler_tick_requires_explicit_dry_run_only_true():
    runner = FakeSchedulerRunner()
    scheduler = QlibOptionCDryRunScheduler(OptionCSchedulerConfig(), runner=runner)

    missing = scheduler.tick({"asof": "2026-06-01"})
    false_value = scheduler.tick({"asof": "2026-06-01", "dry_run_only": False})
    extra = scheduler.tick({"asof": "2026-06-01", "dry_run_only": True, "publish": True})

    assert missing["ok"] is False
    assert false_value["ok"] is False
    assert extra["ok"] is False
    assert runner.calls == []


def test_scheduler_tick_calls_existing_dry_run_runner_only():
    runner = FakeSchedulerRunner()
    scheduler = QlibOptionCDryRunScheduler(OptionCSchedulerConfig(enabled=False), runner=runner)

    result = scheduler.tick({"asof": "2026-06-01", "dry_run_only": True})

    assert result["ok"] is True
    assert result["status"] == "dry_run_passed"
    assert result["dry_run_only"] is True
    assert result["latest_signal_updated"] is False
    assert result["normal_signal_run"] is False
    assert result["accepted_artifact_generated"] is False
    assert result["scheduler"]["auto_loop_started"] is False
    assert result["scheduler"]["last_job_id"] == "option_c_dry_run_20260601_20260602T000000Z_12345678"
    assert runner.calls == [{"asof": "2026-06-01"}]


def test_scheduler_tick_inherits_runner_conflict():
    runner = FakeSchedulerRunner({
        "ok": False,
        "status": "conflict",
        "message": "another Option C ops job is already running",
        "latest_signal_updated": False,
        "normal_signal_run": False,
        "trading": {"orders_enabled": False},
    })
    scheduler = QlibOptionCDryRunScheduler(OptionCSchedulerConfig(), runner=runner)

    result = scheduler.tick({"asof": "2026-06-01", "dry_run_only": True})

    assert result["ok"] is False
    assert result["status"] == "conflict"
    assert result["latest_signal_updated"] is False
    assert result["normal_signal_run"] is False
    assert runner.calls == [{"asof": "2026-06-01"}]


def test_scheduler_api_status_and_tick_auth(client, monkeypatch):
    fake_runner = FakeSchedulerRunner()
    scheduler = QlibOptionCDryRunScheduler(OptionCSchedulerConfig(enabled=False), runner=fake_runner)
    from app.routes import tw_stock as tw_stock_route

    monkeypatch.setattr(tw_stock_route, "option_c_dry_run_scheduler", scheduler)

    status_resp = client.get("/api/tw-stock/quant/ops/option-c/scheduler")
    assert status_resp.status_code == 200
    status = status_resp.get_json()["data"]
    assert status["enabled"] is False
    assert status["dry_run_only"] is True
    assert status["trading"]["orders_enabled"] is False

    anonymous = client.post("/api/tw-stock/quant/ops/option-c/scheduler/tick", json={"asof": "2026-06-01", "dry_run_only": True})
    assert anonymous.status_code == 401

    patch_auth(monkeypatch, "user")
    normal_user = client.post("/api/tw-stock/quant/ops/option-c/scheduler/tick", json={"asof": "2026-06-01", "dry_run_only": True}, headers=user_headers())
    assert normal_user.status_code == 403

    patch_auth(monkeypatch, "admin")
    admin = client.post("/api/tw-stock/quant/ops/option-c/scheduler/tick", json={"asof": "2026-06-01", "dry_run_only": True}, headers=admin_headers())
    assert admin.status_code == 200
    payload = admin.get_json()["data"]
    assert payload["status"] == "dry_run_passed"
    assert payload["scheduler"]["last_job_id"]
    assert fake_runner.calls == [{"asof": "2026-06-01"}]


def test_scheduler_api_rejects_tick_without_dry_run_only(client, monkeypatch):
    fake_runner = FakeSchedulerRunner()
    scheduler = QlibOptionCDryRunScheduler(OptionCSchedulerConfig(enabled=False), runner=fake_runner)
    from app.routes import tw_stock as tw_stock_route

    monkeypatch.setattr(tw_stock_route, "option_c_dry_run_scheduler", scheduler)
    patch_auth(monkeypatch, "admin")
    resp = client.post("/api/tw-stock/quant/ops/option-c/scheduler/tick", json={"asof": "2026-06-01"}, headers=admin_headers())

    assert resp.status_code == 400
    assert resp.get_json()["data"]["status"] == "blocked"
    assert fake_runner.calls == []


def test_scheduler_enabled_status_computes_next_run_and_calendar_asof(tmp_path):
    calendar = tmp_path / "day.txt"
    calendar.write_text("2026-05-29\n2026-06-01\n2099-01-01\n", encoding="utf-8")
    scheduler = QlibOptionCDryRunScheduler(
        OptionCSchedulerConfig(enabled=True, schedule_time="18:30", timezone="Asia/Taipei", provider_calendar=calendar),
        runner=FakeSchedulerRunner(),
    )

    status = scheduler.status()
    asof_plan = scheduler.select_asof(None)

    assert status["enabled"] is True
    assert status["configured_enabled"] is True
    assert status["next_run_at"]
    assert status["auto_loop_started"] is False
    assert status["asof_status"] == "ok"
    assert status["asof_source"] == "provider_calendar"
    assert asof_plan["asof"] == "2026-06-01"


def test_scheduler_calendar_missing_blocks_default_asof(tmp_path):
    runner = FakeSchedulerRunner()
    scheduler = QlibOptionCDryRunScheduler(
        OptionCSchedulerConfig(enabled=True, provider_calendar=tmp_path / "missing_day.txt"),
        runner=runner,
    )

    result = scheduler.tick({"dry_run_only": True})

    assert result["ok"] is False
    assert result["status"] == "blocked"
    assert "provider calendar not found" in result["message"]
    assert runner.calls == []


def test_scheduler_tick_uses_calendar_asof_when_not_explicit(tmp_path):
    calendar = tmp_path / "day.txt"
    calendar.write_text("2026-05-29\n2026-06-01\n2099-01-01\n", encoding="utf-8")
    runner = FakeSchedulerRunner()
    scheduler = QlibOptionCDryRunScheduler(OptionCSchedulerConfig(enabled=True, provider_calendar=calendar), runner=runner)

    result = scheduler.tick({"dry_run_only": True})

    assert result["ok"] is True
    assert result["asof_source"] == "provider_calendar"
    assert runner.calls == [{"asof": "2026-06-01"}]


class FakeAcceptedDryRunScheduler:
    def __init__(self, result=None):
        self.result = result or {
            "ok": True,
            "status": "dry_run_passed",
            "job_id": "option_c_dry_run_20260601_20260602T000000Z_12345678",
            "asof": "2026-06-01",
            "latest_signal_updated": False,
            "normal_signal_run": False,
            "accepted_artifact_generated": False,
            "refresh_triggered": False,
            "publish_triggered": False,
            "provider_mutation_triggered": False,
            "trading": {"orders_enabled": False, "research_signal_not_order": True},
        }
        self.calls = []

    def status(self):
        return {"ok": True, "enabled": False, "dry_run_only": True, "auto_loop_started": False, "trading": {"orders_enabled": False}}

    def tick(self, payload):
        self.calls.append(payload)
        return dict(self.result)


class FakeAcceptedNormalPublish:
    def __init__(self, result=None):
        self.result = result or {
            "ok": True,
            "status": "normal_publish_passed",
            "normal_publish_job_id": "option_c_normal_publish_20260601_20260602T000000Z_12345678",
            "asof": "2026-06-01",
            "normal_signal_run": True,
            "latest_signal_updated": True,
            "accepted_artifact_generated": True,
            "refresh_triggered": False,
            "publish_triggered": False,
            "provider_mutation_triggered": False,
            "trading": {"orders_enabled": False, "research_signal_not_order": True},
        }
        self.calls = []

    def status(self):
        return {"ok": True, "enabled": True, "normal_runner_enabled": True, "auto_scheduler_enabled": False, "trading": {"orders_enabled": False}}

    def publish(self, payload):
        self.calls.append(payload)
        return dict(self.result)


def make_accepted_scheduler(tmp_path: Path, *, enabled=False, dry=None, normal=None):
    return QlibOptionCAcceptedLatestScheduler(
        OptionCAcceptedLatestSchedulerConfig(enabled=enabled, ops_root=tmp_path / "ops", lock_stale_seconds=3),
        dry_run_scheduler=dry or FakeAcceptedDryRunScheduler(),
        normal_publish_gate=normal or FakeAcceptedNormalPublish(),
    )


def test_accepted_latest_scheduler_default_disabled_no_run(tmp_path):
    dry = FakeAcceptedDryRunScheduler()
    normal = FakeAcceptedNormalPublish()
    scheduler = make_accepted_scheduler(tmp_path, enabled=False, dry=dry, normal=normal)

    status = scheduler.status()
    result = scheduler.tick({"asof": "2026-06-01", "confirm_accepted_latest_scheduler": True})

    assert status["enabled"] is False
    assert status["auto_loop_started"] is False
    assert result["ok"] is False
    assert "ENABLE_TW_QLIB_OPTION_C_ACCEPTED_LATEST_SCHEDULER" in result["message"]
    assert result["normal_signal_run"] is False
    assert result["latest_signal_updated"] is False
    assert dry.calls == []
    assert normal.calls == []


def test_accepted_latest_scheduler_requires_confirm(tmp_path):
    scheduler = make_accepted_scheduler(tmp_path, enabled=True)

    missing = scheduler.tick({"asof": "2026-06-01"})
    false_value = scheduler.tick({"asof": "2026-06-01", "confirm_accepted_latest_scheduler": False})
    extra = scheduler.tick({"asof": "2026-06-01", "confirm_accepted_latest_scheduler": True, "dry_run_only": True})

    assert missing["ok"] is False
    assert false_value["ok"] is False
    assert extra["ok"] is False
    assert "confirm" in false_value["message"]


def test_accepted_latest_scheduler_dry_run_failed_does_not_normal(tmp_path):
    dry = FakeAcceptedDryRunScheduler({
        "ok": False,
        "status": "dry_run_failed",
        "job_id": "option_c_dry_run_20260601_20260602T000000Z_12345678",
        "asof": "2026-06-01",
        "latest_signal_updated": False,
        "normal_signal_run": False,
        "accepted_artifact_generated": False,
        "refresh_triggered": False,
        "publish_triggered": False,
        "provider_mutation_triggered": False,
    })
    normal = FakeAcceptedNormalPublish()
    scheduler = make_accepted_scheduler(tmp_path, enabled=True, dry=dry, normal=normal)

    result = scheduler.tick({"asof": "2026-06-01", "confirm_accepted_latest_scheduler": True})

    assert result["ok"] is False
    assert result["status"] == "blocked_dry_run_failed"
    assert result["latest_signal_updated"] is False
    assert dry.calls == [{"dry_run_only": True, "asof": "2026-06-01"}]
    assert normal.calls == []


def test_accepted_latest_scheduler_passed_dry_run_calls_normal_publish(tmp_path):
    dry = FakeAcceptedDryRunScheduler()
    normal = FakeAcceptedNormalPublish()
    scheduler = make_accepted_scheduler(tmp_path, enabled=True, dry=dry, normal=normal)

    result = scheduler.tick({"asof": "2026-06-01", "confirm_accepted_latest_scheduler": True})

    assert result["ok"] is True
    assert result["status"] == "accepted_latest_scheduler_passed"
    assert result["latest_signal_updated"] is True
    assert result["normal_signal_run"] is True
    assert result["accepted_artifact_generated"] is True
    assert result["refresh_triggered"] is False
    assert result["publish_triggered"] is False
    assert result["provider_mutation_triggered"] is False
    assert normal.calls == [{"asof": "2026-06-01", "confirm_normal_publish": True, "dry_run_job_id": "option_c_dry_run_20260601_20260602T000000Z_12345678"}]
    assert result["trading"]["orders_enabled"] is False


def test_accepted_latest_scheduler_normal_publish_disabled_blocks(tmp_path):
    normal = FakeAcceptedNormalPublish({
        "ok": False,
        "status": "blocked",
        "message": "ENABLE_TW_QLIB_OPTION_C_NORMAL_PUBLISH is false",
        "normal_signal_run": False,
        "latest_signal_updated": False,
        "accepted_artifact_generated": False,
        "refresh_triggered": False,
        "publish_triggered": False,
        "provider_mutation_triggered": False,
    })
    scheduler = make_accepted_scheduler(tmp_path, enabled=True, normal=normal)

    result = scheduler.tick({"asof": "2026-06-01", "confirm_accepted_latest_scheduler": True})

    assert result["ok"] is False
    assert result["status"] == "blocked_normal_publish_failed"
    assert result["latest_signal_updated"] is False
    assert normal.calls


def test_accepted_latest_scheduler_lock_conflict(tmp_path):
    scheduler = make_accepted_scheduler(tmp_path, enabled=True)
    lock = tmp_path / "ops" / "option_c_accepted_latest_scheduler.lock"
    lock.parent.mkdir(parents=True, exist_ok=True)
    lock.write_text('{"job_id":"existing","started_at":"2099-01-01T00:00:00+00:00"}', encoding="utf-8")

    result = scheduler.tick({"asof": "2026-06-01", "confirm_accepted_latest_scheduler": True})

    assert result["ok"] is False
    assert result["status"] == "conflict"
    assert result["latest_signal_updated"] is False


def test_accepted_latest_scheduler_api_status_and_tick(client, monkeypatch, tmp_path):
    scheduler = make_accepted_scheduler(tmp_path, enabled=True)
    from app.routes import tw_stock as tw_stock_route
    monkeypatch.setattr(tw_stock_route, "option_c_accepted_latest_scheduler", scheduler)

    status_resp = client.get("/api/tw-stock/quant/ops/option-c/accepted-latest-scheduler")
    assert status_resp.status_code == 200
    assert status_resp.get_json()["data"]["enabled"] is True

    anonymous = client.post("/api/tw-stock/quant/ops/option-c/accepted-latest-scheduler/tick", json={"asof": "2026-06-01", "confirm_accepted_latest_scheduler": True})
    assert anonymous.status_code == 401

    patch_auth(monkeypatch, "user")
    user = client.post("/api/tw-stock/quant/ops/option-c/accepted-latest-scheduler/tick", json={"asof": "2026-06-01", "confirm_accepted_latest_scheduler": True}, headers=user_headers())
    assert user.status_code == 403

    patch_auth(monkeypatch, "admin")
    admin = client.post("/api/tw-stock/quant/ops/option-c/accepted-latest-scheduler/tick", json={"asof": "2026-06-01", "confirm_accepted_latest_scheduler": True}, headers=admin_headers())
    assert admin.status_code == 200
    payload = admin.get_json()["data"]
    assert payload["status"] == "accepted_latest_scheduler_passed"
    assert payload["latest_signal_updated"] is True


def make_normal_gate(tmp_path: Path, **overrides) -> QlibOptionCNormalPublishGate:
    calendar = tmp_path / "day.txt"
    calendar.write_text("2026-06-01\n", encoding="utf-8")
    universe = tmp_path / "universe.txt"
    universe.write_text("\n".join(f"TW{i:04d}" for i in range(150)) + "\n", encoding="utf-8")
    signal_root = tmp_path / "signals"
    signal_root.mkdir(parents=True, exist_ok=True)
    latest_signal = signal_root / "latest_signal.json"
    latest_signal.write_text('{"run_dir":"old"}', encoding="utf-8")
    qlib_cwd = tmp_path / "qlib"
    qlib_cwd.mkdir(parents=True, exist_ok=True)
    config = {
        "enabled": False,
        "ops_root": tmp_path / "ops",
        "signal_root": signal_root,
        "provider_calendar": calendar,
        "expected_universe": universe,
        "qlib_cwd": qlib_cwd,
        "latest_signal": latest_signal,
        "timeout_seconds": 3,
    }
    config.update(overrides)
    return QlibOptionCNormalPublishGate(OptionCNormalPublishConfig(**config))


def write_dry_run_job(gate: QlibOptionCNormalPublishGate, job_id: str, *, asof: str = "2026-06-01", status: str = "dry_run_passed", latest_changed: bool = False):
    job_dir = gate.config.ops_root / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    latest = {"exists": True, "sha256": "abc", "size_bytes": 1}
    after = {"exists": True, "sha256": "changed", "size_bytes": 2} if latest_changed else dict(latest)
    job = {
        "job_id": job_id,
        "asof": asof,
        "status": status,
        "latest_before": latest,
        "latest_after": after,
        "latest_signal_updated": latest_changed,
        "trading": {"orders_enabled": False},
    }
    (job_dir / "job.json").write_text(json.dumps(job), encoding="utf-8")
    return job


def accepted_artifact_dir(tmp_path: Path, *, asof: str = "2026-06-01", rows: int = 150, run_id: str = "option_c_daily_signal_20260601_20260602T000000Z") -> Path:
    run_dir = tmp_path / run_id
    run_dir.mkdir(parents=True)
    (run_dir / "run_metadata.json").write_text(json.dumps({
        "run_id": run_id,
        "created_at": "2026-06-02T00:00:00+00:00",
        "status": "accepted",
        "asof": asof,
        "paper_trading_started": False,
        "live_trading_started": False,
        "target_trades_generated": False,
        "executable_orders_generated": False,
    }), encoding="utf-8")
    (run_dir / "signal_summary.json").write_text(json.dumps({
        "status": "accepted",
        "asof": asof,
        "prediction_rows": rows,
        "top30_rows": 30,
        "top50_rows": 50,
        "finite_prediction_share": 1.0,
        "diagnostic_only": True,
        "research_signal_not_order": True,
        "paper_trading_started": False,
        "live_trading_started": False,
        "target_trades_generated": False,
        "executable_orders_generated": False,
    }), encoding="utf-8")
    (run_dir / "top30_signals.csv").write_text("asof,instrument,score,rank\n", encoding="utf-8")
    (run_dir / "top50_signals.csv").write_text("asof,instrument,score,rank\n", encoding="utf-8")
    return run_dir


def test_normal_publish_default_disabled_blocks_before_gate(tmp_path):
    gate = make_normal_gate(tmp_path, enabled=False)
    result = gate.publish({
        "asof": "2026-06-01",
        "confirm_normal_publish": True,
        "dry_run_job_id": "option_c_dry_run_20260601_20260602T000000Z_12345678",
    })
    assert result["ok"] is False
    assert result["status"] == "blocked"
    assert "ENABLE_TW_QLIB_OPTION_C_NORMAL_PUBLISH" in result["message"]
    assert result["normal_signal_run"] is False
    assert result["latest_signal_updated"] is False
    assert result["trading"]["orders_enabled"] is False


def test_normal_publish_rejects_missing_confirm_and_extra_params(tmp_path):
    gate = make_normal_gate(tmp_path, enabled=True)
    missing_confirm = gate.publish({
        "asof": "2026-06-01",
        "confirm_normal_publish": False,
        "dry_run_job_id": "option_c_dry_run_20260601_20260602T000000Z_12345678",
    })
    extra = gate.publish({
        "asof": "2026-06-01",
        "confirm_normal_publish": True,
        "dry_run_job_id": "option_c_dry_run_20260601_20260602T000000Z_12345678",
        "publish": True,
    })
    assert missing_confirm["ok"] is False
    assert "confirm_normal_publish" in missing_confirm["message"]
    assert extra["ok"] is False
    assert "only asof" in extra["message"]


def test_normal_publish_rejects_missing_or_non_passed_dry_run(tmp_path):
    gate = make_normal_gate(tmp_path, enabled=True)
    missing = gate.publish({
        "asof": "2026-06-01",
        "confirm_normal_publish": True,
        "dry_run_job_id": "option_c_dry_run_20260601_20260602T000000Z_12345678",
    })
    failed_id = "option_c_dry_run_20260601_20260602T000001Z_12345678"
    write_dry_run_job(gate, failed_id, status="dry_run_failed")
    failed = gate.publish({"asof": "2026-06-01", "confirm_normal_publish": True, "dry_run_job_id": failed_id})
    assert missing["gate"]["status"] == "dry_run_job_not_found"
    assert failed["gate"]["status"] == "dry_run_not_passed"


def test_normal_publish_rejects_asof_mismatch_latest_change_and_lock(tmp_path):
    gate = make_normal_gate(tmp_path, enabled=True)
    mismatch_id = "option_c_dry_run_20260601_20260602T000002Z_12345678"
    changed_id = "option_c_dry_run_20260601_20260602T000003Z_12345678"
    write_dry_run_job(gate, mismatch_id, asof="2026-05-29")
    write_dry_run_job(gate, changed_id, latest_changed=True)
    mismatch = gate.publish({"asof": "2026-06-01", "confirm_normal_publish": True, "dry_run_job_id": mismatch_id})
    changed = gate.publish({"asof": "2026-06-01", "confirm_normal_publish": True, "dry_run_job_id": changed_id})
    (gate.config.ops_root / "option_c_ops.lock").write_text("lock", encoding="utf-8")
    locked = gate.publish({"asof": "2026-06-01", "confirm_normal_publish": True, "dry_run_job_id": changed_id})
    assert mismatch["gate"]["status"] == "asof_mismatch"
    assert changed["gate"]["status"] == "dry_run_mutated_latest"
    assert locked["gate"]["status"] == "ops_lock_running"


def test_normal_publish_enabled_pass_calls_fixed_runner_and_updates_latest(tmp_path, monkeypatch):
    gate = make_normal_gate(tmp_path, enabled=True)
    job_id = "option_c_dry_run_20260601_20260602T000004Z_12345678"
    write_dry_run_job(gate, job_id)
    run_dir = accepted_artifact_dir(gate.config.signal_root)
    seen = {}

    def fake_execute(argv, *, timeout):
        seen["argv"] = argv
        seen["timeout"] = timeout
        return fake_completed(json.dumps({"status": "accepted", "run_dir": f"data_tw/experiments/option_c_daily_signal/{run_dir.name}"}))

    monkeypatch.setattr(gate, "_execute_subprocess", fake_execute)
    result = gate.publish({"asof": "2026-06-01", "confirm_normal_publish": True, "dry_run_job_id": job_id})

    assert result["ok"] is True
    assert result["status"] == "normal_publish_passed"
    assert result["gate"]["status"] == "preflight_passed"
    assert seen["argv"] == ["python", "examples/tw/run_option_c_daily_signal_option_c_provider.py", "--asof", "2026-06-01", "--normal"]
    assert "--provider-uri" not in seen["argv"]
    assert "--allow-refresh" not in seen["argv"]
    assert seen["timeout"] == 3
    assert result["normal_signal_run"] is True
    assert result["accepted_artifact_generated"] is True
    assert result["latest_signal_updated"] is True
    assert result["refresh_triggered"] is False
    assert result["publish_triggered"] is False
    assert result["provider_mutation_triggered"] is False
    latest = json.loads(gate.config.latest_signal.read_text(encoding="utf-8"))
    assert latest["status"] == "accepted"
    assert latest["run_dir"].endswith(run_dir.name)
    assert latest["diagnostic_only"] is True
    assert latest["research_signal_not_order"] is True
    assert Path(result["latest_update"]["prepared"]["backup_path"]).exists()
    assert result["trading"]["orders_enabled"] is False


def test_normal_publish_runner_failure_does_not_update_latest(tmp_path, monkeypatch):
    gate = make_normal_gate(tmp_path, enabled=True)
    job_id = "option_c_dry_run_20260601_20260602T000005Z_12345678"
    write_dry_run_job(gate, job_id)
    before = gate.config.latest_signal.read_text(encoding="utf-8")

    def fake_execute(argv, *, timeout):
        return fake_completed('{"status":"failed"}', stderr="failed", returncode=2)

    monkeypatch.setattr(gate, "_execute_subprocess", fake_execute)
    result = gate.publish({"asof": "2026-06-01", "confirm_normal_publish": True, "dry_run_job_id": job_id})

    assert result["ok"] is False
    assert result["normal_job_status"] == "normal_runner_failed"
    assert result["normal_signal_run"] is True
    assert result["latest_signal_updated"] is False
    assert gate.config.latest_signal.read_text(encoding="utf-8") == before


def test_normal_publish_artifact_validation_failure_does_not_update_latest(tmp_path, monkeypatch):
    gate = make_normal_gate(tmp_path, enabled=True)
    job_id = "option_c_dry_run_20260601_20260602T000006Z_12345678"
    write_dry_run_job(gate, job_id)
    run_dir = accepted_artifact_dir(gate.config.signal_root, rows=149)
    before = gate.config.latest_signal.read_text(encoding="utf-8")

    def fake_execute(argv, *, timeout):
        return fake_completed(json.dumps({"status": "accepted", "run_dir": f"data_tw/experiments/option_c_daily_signal/{run_dir.name}"}))

    monkeypatch.setattr(gate, "_execute_subprocess", fake_execute)
    result = gate.publish({"asof": "2026-06-01", "confirm_normal_publish": True, "dry_run_job_id": job_id})

    assert result["ok"] is False
    assert result["normal_job_status"] == "artifact_validation_failed"
    assert result["accepted_artifact_generated"] is True
    assert result["artifact_validation"]["status"] == "artifact_validation_failed"
    assert result["latest_signal_updated"] is False
    assert gate.config.latest_signal.read_text(encoding="utf-8") == before


def test_artifact_validation_failure_and_success_no_trading(tmp_path):
    gate = make_normal_gate(tmp_path, enabled=True)
    bad = accepted_artifact_dir(tmp_path, rows=149)
    failed = gate.validate_accepted_artifacts(bad, asof="2026-06-01")
    good = accepted_artifact_dir(tmp_path / "good", rows=150)
    passed = gate.validate_accepted_artifacts(good, asof="2026-06-01")
    assert failed["ok"] is False
    assert "prediction_rows_invalid" in failed["errors"]
    assert passed["ok"] is True
    assert passed["trading"]["orders_enabled"] is False
    assert passed["trading"]["connects_to_broker"] is False


def test_latest_prepare_and_rollback_restore_previous_latest(tmp_path):
    gate = make_normal_gate(tmp_path, enabled=True)
    latest = tmp_path / "latest_signal.json"
    latest.write_text('{"run_dir":"old"}', encoding="utf-8")
    prepared = gate.prepare_latest_update(latest, {"run_dir": "new"}, backup_dir=tmp_path / "backups")
    latest.write_text('{"run_dir":"new"}', encoding="utf-8")
    rolled = gate.rollback_latest(latest_path=latest, backup_path=Path(prepared["backup_path"]))
    assert prepared["ok"] is True
    assert Path(prepared["backup_path"]).exists()
    assert rolled["ok"] is True
    assert json.loads(latest.read_text(encoding="utf-8"))["run_dir"] == "old"


def test_normal_publish_api_auth_and_default_disabled(client, monkeypatch, tmp_path):
    gate = make_normal_gate(tmp_path, enabled=False)
    from app.routes import tw_stock as tw_stock_route
    monkeypatch.setattr(tw_stock_route, "option_c_normal_publish_gate", gate)
    body = {"asof": "2026-06-01", "confirm_normal_publish": True, "dry_run_job_id": "option_c_dry_run_20260601_20260602T000000Z_12345678"}
    anonymous = client.post("/api/tw-stock/quant/ops/option-c/normal-publish", json=body)
    assert anonymous.status_code == 401
    patch_auth(monkeypatch, "user")
    user = client.post("/api/tw-stock/quant/ops/option-c/normal-publish", json=body, headers=user_headers())
    assert user.status_code == 403
    patch_auth(monkeypatch, "admin")
    admin = client.post("/api/tw-stock/quant/ops/option-c/normal-publish", json=body, headers=admin_headers())
    assert admin.status_code == 400
    payload = admin.get_json()["data"]
    assert payload["status"] == "blocked"
    assert payload["latest_signal_updated"] is False


class FakeEodAcceptedScheduler:
    def __init__(self, result=None):
        self.calls = []
        self.result = result or {
            "ok": True,
            "status": "accepted_latest_scheduler_passed",
            "scheduler_job_id": "option_c_accepted_latest_scheduler_20260601_20260602T000000Z",
            "asof": "2026-06-01",
            "latest_signal_updated": True,
            "refresh_triggered": False,
            "publish_triggered": False,
            "provider_mutation_triggered": False,
            "trading": {"orders_enabled": False, "research_signal_not_order": True},
        }

    def tick(self, payload):
        self.calls.append(payload)
        return dict(self.result)

    def status(self):
        return {"ok": True, "enabled": True, "auto_loop_started": False, "loop_enabled": False, "trading": {"orders_enabled": False}}


class FakeEodSignalReader:
    def latest(self, bucket="top30", enrich_trend=False):
        return {
            "status": "accepted",
            "asof": "2026-06-01",
            "run_id": "option_c_daily_signal_20260601_20260602T000000Z",
            "signals": [{"instrument": f"TW{i:04d}", "rank": i} for i in range(30)],
            "trading": {"orders_enabled": False, "research_signal_not_order": True},
        }


def make_eod_pipeline(tmp_path: Path, *, enabled=False, accepted=None, reader=None) -> QlibOptionCEodPipeline:
    qlib = tmp_path / "qlib"
    qlib.mkdir(parents=True, exist_ok=True)
    calendar = tmp_path / "day.txt"
    calendar.write_text("2026-05-29\n2026-06-01\n", encoding="utf-8")
    return QlibOptionCEodPipeline(
        OptionCEodPipelineConfig(
            enabled=enabled,
            ops_root=tmp_path / "ops",
            qlib_cwd=qlib,
            provider_calendar=calendar,
            timeout_seconds=3,
            refresh_proxy="",
            refresh_sleep_seconds=0.0,
        ),
        accepted_latest_scheduler=accepted or FakeEodAcceptedScheduler(),
        signal_reader=reader or FakeEodSignalReader(),
    )


def write_eod_refresh_summary(pipeline: QlibOptionCEodPipeline, refresh_job_id: str, *, status="staged_refresh_complete_waiting_for_review"):
    reports = pipeline.config.qlib_cwd / "data_tw/experiments/option_c_ops" / refresh_job_id / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    (reports / "execution_summary.json").write_text(json.dumps({
        "status": status,
        "asof": "2026-06-01",
        "fetch": {"status": "pass", "symbols_expected": 150, "symbols_success": 150, "symbols_failed": {}},
        "normalized_validation": {"status": "pass", "missing_asof_count": 0},
        "provider_validation": {"status": "pass"},
        "model_smoke": {"status": "pass", "prediction_rows": 150, "finite_prediction_share": 1.0},
        "formal_provider_mutated": False,
        "latest_signal_updated": False,
        "trading": {"orders_enabled": False, "research_signal_not_order": True},
    }), encoding="utf-8")


def write_eod_publish_summary(pipeline: QlibOptionCEodPipeline, publish_job_id: str, *, status="publish_complete_waiting_for_review"):
    reports = pipeline.config.qlib_cwd / "data_tw/experiments/option_c_ops" / publish_job_id / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    (reports / "publish_execution_summary.json").write_text(json.dumps({
        "status": status,
        "asof": "2026-06-01",
        "mode": "publish",
        "provider_scope": "option_c_150",
        "staged_gate": {"status": "pass"},
        "publish_result": {"status": "published", "provider_validation": {"status": "pass"}, "backup": {"status": "completed"}},
        "latest_signal_updated": False,
        "trading": {"orders_enabled": False, "research_signal_not_order": True},
    }), encoding="utf-8")


def test_eod_pipeline_default_disabled_blocks_before_external_commands(tmp_path, monkeypatch):
    pipeline = make_eod_pipeline(tmp_path, enabled=False)
    calls = []
    monkeypatch.setattr(pipeline, "_execute_subprocess", lambda argv, *, timeout: calls.append(argv))

    result = pipeline.tick({"asof": "2026-06-01", "confirm_eod_pipeline": True, "mode": "controlled_smoke"})

    assert result["ok"] is False
    assert result["status"] == "blocked"
    assert "ENABLE_TW_QLIB_OPTION_C_EOD_PIPELINE" in result["message"]
    assert result["refresh_triggered"] is False
    assert result["provider_mutation_triggered"] is False
    assert result["trading"]["orders_enabled"] is False
    assert calls == []


def test_eod_pipeline_requires_confirm_and_exact_payload(tmp_path):
    pipeline = make_eod_pipeline(tmp_path, enabled=True)

    missing_confirm = pipeline.tick({"asof": "2026-06-01", "mode": "controlled_smoke"})
    false_confirm = pipeline.tick({"asof": "2026-06-01", "confirm_eod_pipeline": False, "mode": "controlled_smoke"})
    extra = pipeline.tick({"asof": "2026-06-01", "confirm_eod_pipeline": True, "mode": "controlled_smoke", "provider_uri": "/tmp/bad"})

    assert missing_confirm["ok"] is False
    assert false_confirm["ok"] is False
    assert extra["ok"] is False
    assert "only asof" in extra["message"]


def test_eod_pipeline_validation_failure_does_not_publish_or_latest(tmp_path, monkeypatch):
    accepted = FakeEodAcceptedScheduler()
    pipeline = make_eod_pipeline(tmp_path, enabled=True, accepted=accepted)
    seen = []

    def fake_execute(argv, *, timeout):
        seen.append(argv)
        refresh_job_id = argv[argv.index("--job-id") + 1]
        write_eod_refresh_summary(pipeline, refresh_job_id, status="candidate_validation_failed")
        return fake_completed(json.dumps({"status": "candidate_validation_failed"}), returncode=1)

    monkeypatch.setattr(pipeline, "_execute_subprocess", fake_execute)
    result = pipeline.tick({"asof": "2026-06-01", "confirm_eod_pipeline": True, "mode": "controlled_smoke"})

    assert result["ok"] is False
    assert result["status"] == "fresh_data_wait"
    assert result["refresh_triggered"] is True
    assert result["provider_mutation_triggered"] is False
    assert result["latest_signal_updated"] is False
    assert accepted.calls == []
    assert len(seen) == 1
    assert "run_option_c_yahoo_scrapling_refresh.py" in seen[0][1]


def test_eod_pipeline_success_calls_fixed_refresh_publish_and_accepted_latest(tmp_path, monkeypatch):
    accepted = FakeEodAcceptedScheduler()
    pipeline = make_eod_pipeline(tmp_path, enabled=True, accepted=accepted)
    seen = []

    def fake_execute(argv, *, timeout):
        seen.append(argv)
        if "run_option_c_yahoo_scrapling_refresh.py" in argv[1]:
            refresh_job_id = argv[argv.index("--job-id") + 1]
            write_eod_refresh_summary(pipeline, refresh_job_id)
            return fake_completed(json.dumps({"status": "staged_refresh_complete_waiting_for_review", "job_id": refresh_job_id}))
        publish_job_id = argv[argv.index("--publish-job-id") + 1]
        write_eod_publish_summary(pipeline, publish_job_id)
        return fake_completed(json.dumps({"status": "publish_complete_waiting_for_review", "publish_job_id": publish_job_id}))

    monkeypatch.setattr(pipeline, "_execute_subprocess", fake_execute)
    result = pipeline.tick({"asof": "2026-06-01", "confirm_eod_pipeline": True, "mode": "controlled_smoke"})

    assert result["ok"] is True
    assert result["status"] == "eod_pipeline_passed"
    assert result["candidate_refresh_job_id"].startswith("option_c_yahoo_scrapling_refresh_20260601_")
    assert result["formal_publish_job_id"].startswith("option_c_yahoo_scrapling_publish_20260601_")
    assert result["accepted_latest_scheduler_job_id"] == "option_c_accepted_latest_scheduler_20260601_20260602T000000Z"
    assert result["latest_run_id"] == "option_c_daily_signal_20260601_20260602T000000Z"
    assert result["signals_count"] == 30
    assert result["refresh_triggered"] is True
    assert result["provider_mutation_triggered"] is True
    assert result["latest_signal_updated"] is True
    assert accepted.calls == [{"asof": "2026-06-01", "confirm_accepted_latest_scheduler": True}]
    assert len(seen) == 2
    assert "--provider-uri" not in seen[0]
    assert "--provider-uri" not in seen[1]
    assert seen[0][seen[0].index("--universe") + 1] == "option_c_accepted_150"
    assert seen[1][seen[1].index("--provider-scope") + 1] == "option_c_150"
    assert seen[1][seen[1].index("--mode") + 1] == "publish"
    assert result["trading"]["orders_enabled"] is False


def test_eod_pipeline_api_status_and_tick_auth(client, monkeypatch, tmp_path):
    pipeline = make_eod_pipeline(tmp_path, enabled=False)
    from app.routes import tw_stock as tw_stock_route
    monkeypatch.setattr(tw_stock_route, "option_c_eod_pipeline", pipeline)
    body = {"asof": "2026-06-01", "confirm_eod_pipeline": True, "mode": "controlled_smoke"}

    status_resp = client.get("/api/tw-stock/quant/ops/option-c/eod-pipeline")
    assert status_resp.status_code == 200
    assert status_resp.get_json()["data"]["enabled"] is False
    assert status_resp.get_json()["data"]["auto_loop_started"] is False

    anonymous = client.post("/api/tw-stock/quant/ops/option-c/eod-pipeline/tick", json=body)
    assert anonymous.status_code == 401

    patch_auth(monkeypatch, "user")
    user = client.post("/api/tw-stock/quant/ops/option-c/eod-pipeline/tick", json=body, headers=user_headers())
    assert user.status_code == 403

    patch_auth(monkeypatch, "admin")
    admin = client.post("/api/tw-stock/quant/ops/option-c/eod-pipeline/tick", json=body, headers=admin_headers())
    assert admin.status_code == 400
    payload = admin.get_json()["data"]
    assert payload["status"] == "blocked"
    assert payload["refresh_triggered"] is False


class FakeAutomationPipeline:
    def __init__(self, result=None):
        self.calls = []
        self.result = result or {
            "ok": True,
            "status": "eod_pipeline_passed",
            "pipeline_job_id": "option_c_eod_pipeline_20260601_20260602T000000Z",
            "asof": "2026-06-01",
            "latest_run_id": "option_c_daily_signal_20260601_20260602T000000Z",
            "signals_count": 30,
            "refresh_triggered": True,
            "provider_mutation_triggered": True,
            "latest_signal_updated": True,
            "trading": {"orders_enabled": False, "research_signal_not_order": True},
        }

    def tick(self, payload):
        self.calls.append(payload)
        return dict(self.result)


class FakeAutomationReader:
    def __init__(self, *, asof=None, run_id="option_c_daily_signal_20260601_20260602T000000Z", count=30, raises=False):
        self.asof = asof
        self.run_id = run_id
        self.count = count
        self.raises = raises

    def latest(self, bucket="top30", enrich_trend=False):
        if self.raises:
            from app.services.tw_stock_qlib_option_c import QlibOptionCSignalError
            raise QlibOptionCSignalError("missing_latest_signal", "missing")
        return {
            "status": "accepted",
            "asof": self.asof,
            "run_id": self.run_id,
            "signals": [{"instrument": f"TW{i:04d}"} for i in range(self.count)],
            "trading": {"orders_enabled": False, "research_signal_not_order": True},
        }


def make_automation(tmp_path: Path, *, enabled=False, calendar_rows=None, pipeline=None, reader=None) -> QlibOptionCEodAutomationScheduler:
    calendar = tmp_path / "day.txt"
    calendar.write_text("\n".join(calendar_rows or ["2026-06-01", "2026-06-02", "2026-06-03"]) + "\n", encoding="utf-8")
    return QlibOptionCEodAutomationScheduler(
        OptionCEodAutomationConfig(
            enabled=enabled,
            ops_root=tmp_path / "ops",
            provider_calendar=calendar,
            eod_window_start="15:30",
            eod_window_end="23:59",
        ),
        pipeline=pipeline or FakeAutomationPipeline(),
        signal_reader=reader or FakeAutomationReader(raises=True),
    )


def test_eod_pipeline_proxy_none_off_disabled_omits_proxy(tmp_path):
    for value in ["none", "off", "disabled", ""]:
        pipeline = make_eod_pipeline(tmp_path / value.replace("", "x"), enabled=True)
        pipeline = QlibOptionCEodPipeline(OptionCEodPipelineConfig(enabled=True, ops_root=tmp_path / "ops" / (value or "empty"), qlib_cwd=tmp_path, refresh_proxy=value if value else ""))
        argv = pipeline.fixed_refresh_argv("2026-06-01", refresh_job_id="job", report_path=tmp_path / "report.md")
        assert "--proxy" not in argv
    default_cfg = OptionCEodPipelineConfig.from_env()
    assert default_cfg.refresh_proxy


def test_eod_automation_default_disabled_does_not_run_pipeline(tmp_path):
    pipeline = FakeAutomationPipeline()
    scheduler = make_automation(tmp_path, enabled=False, pipeline=pipeline)

    result = scheduler.tick({"confirm_eod_automation": True, "mode": "controlled_scheduler_smoke", "now": "2026-06-02T16:10:00+08:00"})

    assert result["ok"] is False
    assert result["status"] == "blocked"
    assert "ENABLE_TW_QLIB_OPTION_C_EOD_AUTOMATION" in result["message"]
    assert result["refresh_triggered"] is False
    assert pipeline.calls == []


def test_eod_automation_rejects_missing_confirm_and_extra_fields(tmp_path):
    scheduler = make_automation(tmp_path, enabled=True)

    missing = scheduler.tick({"mode": "controlled_scheduler_smoke", "now": "2026-06-02T16:10:00+08:00"})
    extra = scheduler.tick({"confirm_eod_automation": True, "mode": "controlled_scheduler_smoke", "now": "2026-06-02T16:10:00+08:00", "asof": "2026-06-02"})

    assert missing["ok"] is False
    assert extra["ok"] is False
    assert "only confirm" in extra["message"]


def test_eod_automation_blocks_outside_window_and_non_trading_day(tmp_path):
    pipeline = FakeAutomationPipeline()
    scheduler = make_automation(tmp_path, enabled=True, pipeline=pipeline, calendar_rows=["2026-06-02"])

    early = scheduler.tick({"confirm_eod_automation": True, "mode": "controlled_scheduler_smoke", "now": "2026-06-02T14:10:00+08:00"})
    holiday = scheduler.tick({"confirm_eod_automation": True, "mode": "controlled_scheduler_smoke", "now": "2026-06-03T16:10:00+08:00"})

    assert early["status"] == "outside_eod_window"
    assert holiday["status"] == "market_closed_or_no_new_asof"
    assert pipeline.calls == []


def test_eod_automation_idempotent_already_accepted_latest_skips_pipeline(tmp_path):
    pipeline = FakeAutomationPipeline()
    scheduler = make_automation(tmp_path, enabled=True, pipeline=pipeline, reader=FakeAutomationReader(asof="2026-06-02"))

    result = scheduler.tick({"confirm_eod_automation": True, "mode": "controlled_scheduler_smoke", "now": "2026-06-02T16:10:00+08:00"})

    assert result["ok"] is False
    assert result["status"] == "already_accepted_latest"
    assert result["latest_run_id"] == "option_c_daily_signal_20260601_20260602T000000Z"
    assert result["signals_count"] == 30
    assert result["refresh_triggered"] is False
    assert pipeline.calls == []


def test_eod_automation_ready_window_calls_pipeline_and_returns_latest(tmp_path):
    pipeline = FakeAutomationPipeline()
    scheduler = make_automation(tmp_path, enabled=True, pipeline=pipeline, reader=FakeAutomationReader(asof="2026-06-01"))

    result = scheduler.tick({"confirm_eod_automation": True, "mode": "controlled_scheduler_smoke", "now": "2026-06-02T16:10:00+08:00"})

    assert result["ok"] is True
    assert result["status"] == "eod_automation_pipeline_passed"
    assert result["asof"] == "2026-06-02"
    assert result["target_date"] == "2026-06-03"
    assert result["target_horizon"] == "next_trading_day_research_ranking"
    assert result["latest_run_id"] == "option_c_daily_signal_20260601_20260602T000000Z"
    assert result["signals_count"] == 30
    assert result["trading"]["orders_enabled"] is False
    assert pipeline.calls == [{"asof": "2026-06-02", "confirm_eod_pipeline": True, "mode": "controlled_smoke"}]


def test_eod_automation_pipeline_fresh_data_wait_propagates_no_publish(tmp_path):
    pipeline = FakeAutomationPipeline({
        "ok": False,
        "status": "fresh_data_wait",
        "message": "candidate refresh did not produce reviewed staged data",
        "refresh_triggered": True,
        "provider_mutation_triggered": False,
        "latest_signal_updated": False,
    })
    scheduler = make_automation(tmp_path, enabled=True, pipeline=pipeline, reader=FakeAutomationReader(asof="2026-06-01"))

    result = scheduler.tick({"confirm_eod_automation": True, "mode": "controlled_scheduler_smoke", "now": "2026-06-02T16:10:00+08:00"})

    assert result["ok"] is False
    assert result["status"] == "fresh_data_wait"
    assert result["refresh_triggered"] is True
    assert result["provider_mutation_triggered"] is False
    assert result["latest_signal_updated"] is False


def test_eod_automation_api_status_and_tick_auth(client, monkeypatch, tmp_path):
    scheduler = make_automation(tmp_path, enabled=False)
    from app.routes import tw_stock as tw_stock_route
    monkeypatch.setattr(tw_stock_route, "option_c_eod_automation_scheduler", scheduler)
    body = {"confirm_eod_automation": True, "mode": "controlled_scheduler_smoke", "now": "2026-06-02T16:10:00+08:00"}

    status_resp = client.get("/api/tw-stock/quant/ops/option-c/eod-automation?now=2026-06-02T16:10:00%2B08:00")
    assert status_resp.status_code == 200
    assert status_resp.get_json()["data"]["enabled"] is False
    assert status_resp.get_json()["data"]["auto_loop_started"] is False

    anonymous = client.post("/api/tw-stock/quant/ops/option-c/eod-automation/tick", json=body)
    assert anonymous.status_code == 401
    patch_auth(monkeypatch, "user")
    user = client.post("/api/tw-stock/quant/ops/option-c/eod-automation/tick", json=body, headers=user_headers())
    assert user.status_code == 403
    patch_auth(monkeypatch, "admin")
    admin = client.post("/api/tw-stock/quant/ops/option-c/eod-automation/tick", json=body, headers=admin_headers())
    assert admin.status_code == 400
    assert admin.get_json()["data"]["status"] == "blocked"
