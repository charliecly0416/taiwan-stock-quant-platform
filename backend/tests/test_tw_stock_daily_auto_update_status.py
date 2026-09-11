"""Tests for read-only TWStock daily auto-update status API/service."""
from __future__ import annotations

import json
from pathlib import Path

from app.services.tw_stock_daily_auto_update_status import TWStockDailyAutoUpdateStatusService


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _make_service(tmp_path: Path) -> TWStockDailyAutoUpdateStatusService:
    signal_root = tmp_path / "qlib_pipeline/data_tw/experiments/option_c_daily_signal"
    ops_root = tmp_path / "data_tw/ops/daily_auto_update"
    signal_root.mkdir(parents=True, exist_ok=True)
    ops_root.mkdir(parents=True, exist_ok=True)
    return TWStockDailyAutoUpdateStatusService(signal_root=signal_root, ops_root=ops_root)


def test_status_without_jobs_returns_readonly_empty_state(tmp_path):
    service = _make_service(tmp_path)

    payload = service.status()

    assert payload["ok"] is True
    assert payload["latest_asof"] is None
    assert payload["pending_asof"] is None
    assert payload["last_job_id"] is None
    assert payload["fresh_data_wait"] is False
    assert payload["trading"]["orders_enabled"] is False
    assert payload["trading"]["connects_to_broker"] is False
    assert payload["trading"]["research_signal_not_order"] is True


def test_status_reads_successful_latest_and_last_job(tmp_path):
    service = _make_service(tmp_path)
    _write_json(
        service.signal_root / "latest_signal.json",
        {
            "status": "accepted",
            "asof": "2026-06-03",
            "created_at": "2026-06-03T11:20:00+00:00",
            "run_dir": "data_tw/experiments/option_c_daily_signal/option_c_daily_signal_20260603_20260603T111900Z",
        },
    )
    _write_json(
        service.ops_root / "daily_tw_stock_auto_update_20260603_20260603T111000Z/job.json",
        {
            "job_id": "daily_tw_stock_auto_update_20260603_20260603T111000Z",
            "status": "daily_auto_update_passed",
            "asof": "2026-06-03",
            "started_at": "2026-06-03T11:10:00+00:00",
            "finished_at": "2026-06-03T11:22:00+00:00",
            "finmind_update": {"ok": True},
            "archived_count": 1200,
            "yahoo_refresh": {"ok": True},
            "refresh_summary": {
                "status": "pass",
                "asof": "2026-06-03",
                "normalized_validation": {
                    "status": "pass",
                    "date_max_max": "2026-06-03",
                    "missing_asof_count": 0,
                },
            },
            "provider_publish_triggered": True,
            "latest_signal_updated": True,
        },
    )

    payload = service.status()

    assert payload["latest_asof"] == "2026-06-03"
    assert payload["latest_status"] == "accepted"
    assert payload["latest_run_id"] == "option_c_daily_signal_20260603_20260603T111900Z"
    assert payload["last_job_status"] == "daily_auto_update_passed"
    assert payload["finmind_update_status"] == "success"
    assert payload["finmind_archived_count"] == 1200
    assert payload["yahoo_date_max"] == "2026-06-03"
    assert payload["yahoo_missing_asof_count"] == 0
    assert payload["fresh_data_wait"] is False


def test_status_reads_pending_fresh_data_wait_and_retry_hint(tmp_path):
    service = _make_service(tmp_path)
    _write_json(
        service.signal_root / "latest_signal.json",
        {
            "status": "accepted",
            "asof": "2026-06-02",
            "run_dir": "data_tw/experiments/option_c_daily_signal/option_c_daily_signal_20260602_20260603T031450Z",
        },
    )
    _write_json(
        service.ops_root / "pending_asof.json",
        {
            "asof": "2026-06-03",
            "reason": "fresh_data_wait",
            "job_id": "daily_tw_stock_auto_update_20260603_20260603T171533Z",
            "updated_at": "2026-06-03T17:22:57+00:00",
        },
    )
    _write_json(
        service.ops_root / "daily_tw_stock_auto_update_20260603_20260603T171533Z/job.json",
        {
            "job_id": "daily_tw_stock_auto_update_20260603_20260603T171533Z",
            "status": "fresh_data_wait",
            "asof": "2026-06-03",
            "started_at": "2026-06-03T17:15:33+00:00",
            "finished_at": "2026-06-03T17:22:57+00:00",
            "finmind_update": {"ok": True, "stdout_tail": '\n  "archived_count": 1200,\n'},
            "yahoo_refresh": {"ok": False},
            "refresh_summary": {
                "status": "candidate_validation_failed",
                "asof": "2026-06-03",
                "normalized_validation": {
                    "status": "fail",
                    "date_max_max": "2026-06-02",
                    "missing_asof_count": 150,
                },
            },
            "message": "Yahoo/Scrapling did not produce complete asof data yet",
        },
    )
    (service.ops_root / "tw-daily-auto-update.installed.cron").write_text(
        "30 8,10,12,14,16,18,20 * * 1-5 cd /repo && python scripts/run_daily_tw_stock_auto_update.py\n",
        encoding="utf-8",
    )

    payload = service.status()

    assert payload["latest_asof"] == "2026-06-02"
    assert payload["pending_asof"] == "2026-06-03"
    assert payload["pending_reason"] == "fresh_data_wait"
    assert payload["last_job_status"] == "fresh_data_wait"
    assert payload["finmind_update_status"] == "success"
    assert payload["yahoo_update_status"] == "failed"
    assert payload["yahoo_target_asof"] == "2026-06-03"
    assert payload["yahoo_date_max"] == "2026-06-02"
    assert payload["yahoo_missing_asof_count"] == 150
    assert payload["fresh_data_wait"] is True
    assert payload["cron_installed_hint"] is True
    assert "pending asof 2026-06-03 will be retried" in payload["next_retry_hint"]


def test_status_reports_non_fresh_pending_instead_of_claiming_no_pending(tmp_path):
    service = _make_service(tmp_path)
    _write_json(service.ops_root / "pending_asof.json", {
        "asof": "2026-08-31",
        "reason": "terminal_pending_catchup",
        "job_id": "prior_terminal_job",
        "updated_at": "2026-08-31T16:00:00+00:00",
    })
    (service.ops_root / "tw-daily-auto-update.installed.cron").write_text(
        "30 */2 * * * python scripts/run_daily_tw_stock_auto_update.py\n", encoding="utf-8"
    )

    payload = service.status()

    assert payload["pending_asof"] == "2026-08-31"
    assert payload["fresh_data_wait"] is False
    assert "will be processed by the installed schedule" in payload["next_retry_hint"]
    assert "no pending asof" not in payload["next_retry_hint"]


def test_status_redacts_cron_secrets_without_hiding_schedule_or_normal_flags(tmp_path):
    service = _make_service(tmp_path)
    cron_path = service.ops_root / "tw-daily-auto-update.installed.cron"
    cron_path.write_text(
        "\n".join(
            [
                "DATABASE_URL=postgresql://quantdinger:db-secret@127.0.0.1:5433/quantdinger",
                "OPENAI_API_TOKEN=token-secret",
                "CLIENTSECRET=client-secret",
                "DBPASS=db-pass",
                "SERVICE_PASSWORD='password secret'",
                "PGPASSWORD=pg-secret",
                "SAFE_FLAG=true",
                "PUBLIC_URL=https://public.example/status",
                "HTTP_PROXY=http://proxy-user:proxy-secret@proxy.example:7890",
                "30 */2 * * * SAFE_FLAG=true ACCESS_TOKEN=inline-secret python scripts/run_daily_tw_stock_auto_update.py",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (service.ops_root / "cron.log").write_text(
        "SAFE_FLAG=true status=ok\n"
        "DATABASE_URL=postgresql://log-user:log-secret@db.example/db ACCESS_TOKEN=log-token\n"
        "callback=https://callback-user:callback-secret@public.example/hook\n",
        encoding="utf-8",
    )

    cron = service.status()["cron"]
    schedule = "\n".join(cron["installed_schedule"])
    log_tail = "\n".join(cron["cron_log_tail"])

    for secret in (
        "quantdinger:db-secret",
        "token-secret",
        "client-secret",
        "db-pass",
        "password secret",
        "pg-secret",
        "proxy-user:proxy-secret",
        "inline-secret",
        "log-user:log-secret",
        "log-token",
        "callback-user:callback-secret",
    ):
        assert secret not in schedule
        assert secret not in log_tail
    assert "DATABASE_URL=[REDACTED]" in schedule
    assert "OPENAI_API_TOKEN=[REDACTED]" in schedule
    assert "CLIENTSECRET=[REDACTED]" in schedule
    assert "DBPASS=[REDACTED]" in schedule
    assert "SERVICE_PASSWORD=[REDACTED]" in schedule
    assert "PGPASSWORD=[REDACTED]" in schedule
    assert "HTTP_PROXY=http://[REDACTED]@proxy.example:7890" in schedule
    assert "ACCESS_TOKEN=[REDACTED]" in schedule
    assert "DATABASE_URL=[REDACTED]" in log_tail
    assert "callback=https://[REDACTED]@public.example/hook" in log_tail
    assert "SAFE_FLAG=true" in schedule
    assert "SAFE_FLAG=true status=ok" in log_tail
    assert "PUBLIC_URL=https://public.example/status" in schedule
    assert "30 */2 * * *" in schedule


def test_status_redacts_adversarial_shell_assignments_and_url_boundaries(tmp_path):
    service = _make_service(tmp_path)
    cron_path = service.ops_root / "tw-daily-auto-update.installed.cron"
    cron_path.write_text(
        "\n".join(
            [
                "DBPASSWD=compact-db-secret",
                "mysql_pwd=mixed-mysql-secret",
                "ReDiScLi_AuTh=mixed-redis-secret",
                "AUTH=auth-secret",
                "PROXY_AUTH=proxy-auth-secret",
                "AUTHORIZATION=BearerValue",
                "HTTP_AUTHORIZATION='Bearer OtherValue'",
                "SSH_PRIVATE_KEY=PrivateMaterial",
                "PRIVATEKEY=CompactPrivateMaterial",
                'PASSWORD="alpha\\" beta"',
                "ALT_PASSWORD='single quoted secret'",
                "COMBINED_PASSWORD='first-secret'\"second-secret\"tail-secret",
                'BROKEN_PASSWORD="unterminated secret trailing schedule text',
                "SAFE_FLAG=true",
                "PWD=/srv/app",
                "OLDPWD=/srv/old",
                "AUTH_MODE=oauth2",
                "AUTH_METHOD=oidc",
                "AUTH_ENABLED=true",
                "PUBLIC_URL=https://public.example/status?contact=user@example.com#ok",
                "callback=https://url-user:url-secret@relay@public.example/hook",
                "query_url=https://query-user:query-secret@query.example?keep=value",
                "fragment_url=https://fragment-user:fragment-secret@fragment.example#keep",
                "space_url=https://space-user:space-secret@relay@space.example next=true",
                "30 */2 * * * DBPASSWD=inline-compact-secret python scripts/run_daily_tw_stock_auto_update.py",
                "45 14 * * 1-5 SAFE_FLAG=true python scripts/run_daily_tw_stock_auto_update.py --scope full",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (service.ops_root / "cron.log").write_text(
        'PASSWORD="log-alpha\\" log-beta" status=failed\n'
        'BROKEN_PASSWORD="unterminated-log-secret details follow\n',
        encoding="utf-8",
    )

    cron = service.status()["cron"]
    schedule_lines = cron["installed_schedule"]
    schedule = "\n".join(schedule_lines)
    log_tail = "\n".join(cron["cron_log_tail"])

    secrets = (
        "compact-db-secret",
        "mixed-mysql-secret",
        "mixed-redis-secret",
        "auth-secret",
        "proxy-auth-secret",
        "BearerValue",
        "Bearer OtherValue",
        "PrivateMaterial",
        "CompactPrivateMaterial",
        "alpha",
        "beta",
        "single quoted secret",
        "first-secret",
        "second-secret",
        "tail-secret",
        "unterminated secret trailing schedule text",
        "url-user",
        "url-secret",
        "relay",
        "query-user",
        "query-secret",
        "fragment-user",
        "fragment-secret",
        "space-user",
        "space-secret",
        "inline-compact-secret",
        "log-alpha",
        "log-beta",
        "unterminated-log-secret",
    )
    serialized = schedule + "\n" + log_tail
    assert all(secret not in serialized for secret in secrets)
    assert "DBPASSWD=[REDACTED]" in schedule_lines
    assert "mysql_pwd=[REDACTED]" in schedule_lines
    assert "ReDiScLi_AuTh=[REDACTED]" in schedule_lines
    assert "AUTH=[REDACTED]" in schedule_lines
    assert "PROXY_AUTH=[REDACTED]" in schedule_lines
    assert "AUTHORIZATION=[REDACTED]" in schedule_lines
    assert "HTTP_AUTHORIZATION=[REDACTED]" in schedule_lines
    assert "SSH_PRIVATE_KEY=[REDACTED]" in schedule_lines
    assert "PRIVATEKEY=[REDACTED]" in schedule_lines
    assert "PASSWORD=[REDACTED]" in schedule_lines
    assert "BROKEN_PASSWORD=[REDACTED]" in schedule_lines
    assert "callback=https://[REDACTED]@public.example/hook" in schedule_lines
    assert "query_url=https://[REDACTED]@query.example?keep=value" in schedule_lines
    assert "fragment_url=https://[REDACTED]@fragment.example#keep" in schedule_lines
    assert "space_url=https://[REDACTED]@space.example next=true" in schedule_lines
    assert "SAFE_FLAG=true" in schedule_lines
    assert "PWD=/srv/app" in schedule_lines
    assert "OLDPWD=/srv/old" in schedule_lines
    assert "AUTH_MODE=oauth2" in schedule_lines
    assert "AUTH_METHOD=oidc" in schedule_lines
    assert "AUTH_ENABLED=true" in schedule_lines
    assert "PUBLIC_URL=https://public.example/status?contact=user@example.com#ok" in schedule_lines
    assert "30 */2 * * * DBPASSWD=[REDACTED] python scripts/run_daily_tw_stock_auto_update.py" in schedule_lines
    assert "45 14 * * 1-5 SAFE_FLAG=true python scripts/run_daily_tw_stock_auto_update.py --scope full" in schedule_lines
    assert "PASSWORD=[REDACTED] status=failed" in cron["cron_log_tail"]
    assert "BROKEN_PASSWORD=[REDACTED]" in cron["cron_log_tail"]


def test_status_degrades_with_corrupt_job_json_warning(tmp_path):
    service = _make_service(tmp_path)
    _write_json(
        service.signal_root / "latest_signal.json",
        {"status": "accepted", "asof": "2026-06-02", "run_dir": "x/option_c_daily_signal_fixture"},
    )
    bad_job = service.ops_root / "daily_tw_stock_auto_update_bad/job.json"
    bad_job.parent.mkdir(parents=True, exist_ok=True)
    bad_job.write_text("{bad json", encoding="utf-8")

    payload = service.status()

    assert payload["ok"] is True
    assert payload["latest_asof"] == "2026-06-02"
    assert payload["last_job_id"] == "daily_tw_stock_auto_update_bad"
    assert any("job.json:json_read_failed" in warning for warning in payload["warnings"])
    assert payload["trading"]["orders_enabled"] is False


def test_status_exposes_qald2r_candidate_lifecycle_from_latest_job(tmp_path):
    service = _make_service(tmp_path)
    job_dir = service.ops_root / "daily_tw_stock_auto_update_20260807_20260807T103000Z"
    _write_json(
        job_dir / "job.json",
        {
            "job_id": job_dir.name,
            "status": "daily_auto_update_passed",
            "asof": "2026-08-07",
            "started_at": "2026-08-07T10:30:00+00:00",
            "finished_at": "2026-08-07T10:40:00+00:00",
        },
    )
    _write_json(
        job_dir / "qald2r_accepted_latest_candidate_preflight.json",
        {
            "status": "candidate_built_no_pointer",
            "enabled": True,
            "attempted": True,
            "ok": True,
            "target_asof": "2026-08-07",
            "run_id": "option_c_daily_signal_20260807_qald2r_candidate_unit",
            "source_candidate_root": "qlib_pipeline/data_tw/experiments/daily_auto_provider_candidates/unit",
            "latest_signal_updated": False,
            "protected_pointer_unchanged": True,
            "reader_validation": {"ok": True, "top30_count": 30, "top50_count": 50},
        },
    )

    payload = service.status()

    assert payload["qald_accepted_latest_candidate_status"] == "candidate_built_no_pointer"
    assert payload["qald_accepted_latest_candidate_enabled"] is True
    assert payload["qald_accepted_latest_candidate_attempted"] is True
    assert payload["qald_accepted_latest_candidate_ok"] is True
    assert payload["qald_accepted_latest_candidate_asof"] == "2026-08-07"
    assert payload["qald_accepted_latest_candidate_run_id"] == "option_c_daily_signal_20260807_qald2r_candidate_unit"
    assert payload["qald_accepted_latest_candidate_latest_signal_updated"] is False
    assert payload["qald_accepted_latest_candidate_protected_unchanged"] is True


def test_daily_auto_update_status_api_returns_200(client, monkeypatch, tmp_path):
    service = _make_service(tmp_path)
    _write_json(
        service.signal_root / "latest_signal.json",
        {
            "status": "accepted",
            "asof": "2026-06-02",
            "run_dir": "data_tw/experiments/option_c_daily_signal/option_c_daily_signal_20260602_20260603T031450Z",
        },
    )
    from app.routes import tw_stock as tw_stock_route

    monkeypatch.setattr(tw_stock_route, "daily_auto_update_status_service", service)

    resp = client.get("/api/tw-stock/quant/ops/daily-auto-update/status")
    payload = resp.get_json()

    assert resp.status_code == 200
    assert payload["code"] == 1
    assert payload["data"]["latest_asof"] == "2026-06-02"
    assert payload["data"]["trading"]["research_signal_not_order"] is True


def test_daily_auto_update_status_api_never_serializes_cron_secrets(client, monkeypatch, tmp_path):
    service = _make_service(tmp_path)
    (service.ops_root / "tw-daily-auto-update.installed.cron").write_text(
        "DATABASE_URL=postgresql://api-user:api-db-secret@db.example/quant\n"
        "DBPASSWD=api-compact-secret\n"
        "MYSQL_PWD=api-mysql-secret\n"
        "REDISCLI_AUTH=api-redis-secret\n"
        "AUTHORIZATION=api-bearer-secret\n"
        "HTTP_AUTHORIZATION='Bearer api-http-auth-secret'\n"
        "SSH_PRIVATE_KEY=api-private-material\n"
        "PRIVATEKEY=api-compact-private-material\n"
        'PASSWORD="api-alpha\\" api-beta"\n'
        "SAFE_FLAG=true\n"
        "PWD=/srv/app\n"
        "OLDPWD=/srv/old\n"
        "AUTH_MODE=oauth2\n"
        "AUTH_METHOD=oidc\n"
        "AUTH_ENABLED=true\n"
        "30 */2 * * * ACCESS_TOKEN=api-token-secret python scripts/run_daily_tw_stock_auto_update.py\n",
        encoding="utf-8",
    )
    (service.ops_root / "cron.log").write_text(
        "SERVICE_PASSWORD=api-log-secret callback=https://log-user:log-pass@relay@status.example/hook\n",
        encoding="utf-8",
    )
    from app.routes import tw_stock as tw_stock_route

    monkeypatch.setattr(tw_stock_route, "daily_auto_update_status_service", service)

    resp = client.get("/api/tw-stock/quant/ops/daily-auto-update/status")
    body = resp.get_data(as_text=True)
    payload = resp.get_json()["data"]

    assert resp.status_code == 200
    for secret in (
        "api-user",
        "api-db-secret",
        "api-compact-secret",
        "api-mysql-secret",
        "api-redis-secret",
        "api-bearer-secret",
        "api-http-auth-secret",
        "api-private-material",
        "api-compact-private-material",
        "api-alpha",
        "api-beta",
        "api-token-secret",
        "api-log-secret",
        "log-user",
        "log-pass",
        "relay",
    ):
        assert secret not in body
    assert "DATABASE_URL=[REDACTED]" in payload["cron"]["installed_schedule"]
    assert "SAFE_FLAG=true" in payload["cron"]["installed_schedule"]
    assert "PWD=/srv/app" in payload["cron"]["installed_schedule"]
    assert "OLDPWD=/srv/old" in payload["cron"]["installed_schedule"]
    assert "AUTH_MODE=oauth2" in payload["cron"]["installed_schedule"]
    assert "AUTH_METHOD=oidc" in payload["cron"]["installed_schedule"]
    assert "AUTH_ENABLED=true" in payload["cron"]["installed_schedule"]
    assert any("SERVICE_PASSWORD=[REDACTED]" in line for line in payload["cron"]["cron_log_tail"])
    assert any("callback=https://[REDACTED]@status.example/hook" in line for line in payload["cron"]["cron_log_tail"])
