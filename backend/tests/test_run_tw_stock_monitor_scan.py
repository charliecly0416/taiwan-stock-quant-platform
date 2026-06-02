"""Tests for independent TWStock monitor scan script."""
from __future__ import annotations

import json

from scripts import run_tw_stock_monitor_scan as scan_script


def test_clamp_interval_bounds():
    assert scan_script.clamp_interval(1) == 30
    assert scan_script.clamp_interval(900) == 900
    assert scan_script.clamp_interval(999999) == 86400


def test_run_once_prints_research_only_summary(monkeypatch, capsys):
    calls = []

    def fake_run_scan_once(*, force, trigger_source, write_log):
        calls.append({"force": force, "trigger_source": trigger_source, "write_log": write_log})
        return {
            "count": 2,
            "total_scanned_count": 5,
            "total_alert_count": 1,
            "trading": {"orders_enabled": False},
        }

    monkeypatch.setattr(scan_script, "run_scan_once", fake_run_scan_once)

    rc = scan_script.main(["--once", "--force", "--trigger-source", "cron-test"])

    assert rc == 0
    assert calls == [{"force": True, "trigger_source": "cron-test", "write_log": True}]
    line = capsys.readouterr().out.strip()
    payload = json.loads(line)
    assert payload["status"] == "success"
    assert payload["count"] == 2
    assert payload["total_scanned_count"] == 5
    assert payload["total_alert_count"] == 1
    assert payload["orders_enabled"] is False


def test_loop_respects_max_runs_without_sleep(monkeypatch, capsys):
    calls = []

    def fake_run_scan_once(*, force, trigger_source, write_log):
        calls.append(trigger_source)
        return {"count": 1, "total_scanned_count": 1, "total_alert_count": 0, "trading": {"orders_enabled": False}}

    monkeypatch.setattr(scan_script, "run_scan_once", fake_run_scan_once)
    monkeypatch.setattr(scan_script.time, "sleep", lambda _seconds: None)

    rc = scan_script.main(["--loop", "--max-runs", "2", "--interval-sec", "30", "--trigger-source", "worker-test", "--no-log"])

    assert rc == 0
    assert calls == ["worker-test", "worker-test"]
    lines = capsys.readouterr().out.strip().splitlines()
    assert len(lines) == 2
    assert json.loads(lines[-1])["run_count"] == 2
