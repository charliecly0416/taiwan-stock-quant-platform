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
