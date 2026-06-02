"""Tests for read-only TWStock monitor health reporting."""
from __future__ import annotations

import json

from app.services import tw_stock_monitor as monitor
from scripts import report_tw_stock_monitor_health as health_script


def _logs():
    return [
        {"id": 3, "trigger_source": "cron", "status": "success", "scanned_count": 5, "alert_count": 1, "duration_ms": 100, "created_at": "2026-05-25T10:00:00Z"},
        {"id": 2, "trigger_source": "cron", "status": "failed", "scanned_count": 0, "alert_count": 0, "error": "db timeout", "duration_ms": 50, "created_at": "2026-05-25T09:45:00Z"},
        {"id": 1, "trigger_source": "cron", "status": "success", "scanned_count": 4, "alert_count": 0, "duration_ms": 150, "created_at": "2026-05-25T09:30:00Z"},
    ]


def test_summarize_scan_health_reports_degraded_without_side_effect_flags():
    health = monitor.summarize_scan_health(_logs())

    assert health["status"] == "degraded"
    assert health["log_count"] == 3
    assert health["success_count"] == 2
    assert health["failed_count"] == 1
    assert health["success_rate"] == 0.6667
    assert health["total_scanned_count"] == 9
    assert health["total_alert_count"] == 1
    assert health["avg_duration_ms"] == 100.0
    assert health["recent_failures"][0]["error"] == "db timeout"
    assert health["orders_enabled"] is False
    assert health["writes_production_data"] is False
    assert health["connects_to_broker"] is False


def test_build_health_report_is_read_only_summary():
    report = health_script.build_health_report(limit=3, logs=_logs())

    assert report["limit"] == 3
    assert report["health"]["status"] == "degraded"
    assert report["scanned"] is False
    assert report["alerts_created"] == 0
    assert report["orders_enabled"] is False
    assert report["writes_production_data"] is False
    assert report["connects_to_broker"] is False


def test_load_scan_logs_normalizes_result_summary():
    rows = [
        {
            "id": 1,
            "trigger_source": "cron",
            "status": "success",
            "monitor_count": 2,
            "scanned_count": 5,
            "alert_count": 1,
            "error": "",
            "result_summary": '{"count":2}',
            "duration_ms": 10,
            "created_at": "2026-05-25T10:00:00Z",
        }
    ]

    class Cursor:
        def execute(self, sql, params):
            self.params = params

        def fetchall(self):
            return rows

        def close(self):
            pass

    class Db:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def cursor(self):
            return Cursor()

    items = health_script.load_scan_logs(limit=1, db_factory=lambda: Db())

    assert items[0]["result_summary"] == {"count": 2}
    assert items[0]["monitor_count"] == 2


def test_main_prints_health_report(monkeypatch, capsys):
    monkeypatch.setattr(health_script, "load_scan_logs", lambda **kwargs: _logs())

    rc = health_script.main(["--limit", "3"])

    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["health"]["status"] == "degraded"
    assert payload["orders_enabled"] is False
