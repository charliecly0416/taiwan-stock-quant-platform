"""Tests for TWStock monitor config preflight script."""
from __future__ import annotations

import json

from scripts import preflight_tw_stock_monitor_config as preflight


class FakeTrendService:
    def __init__(self, reports):
        self.reports = reports
        self.calls = []

    def analyze_symbol(self, *, symbol, limit):
        self.calls.append((symbol, limit))
        return dict(self.reports[symbol])


def test_preflight_reports_ok_warning_and_failed_symbols(tmp_path):
    path = tmp_path / "monitor.json"
    path.write_text(json.dumps({"name": "phase7c", "symbols": ["2330", "0050", "9999"], "limit_bars": 80}), encoding="utf-8")
    service = FakeTrendService({
        "2330": {"symbol": "2330", "ok": True, "quality": {"warnings": []}, "trading": {"orders_enabled": False}},
        "0050": {"symbol": "0050", "ok": True, "quality": {"warnings": ["short_history_below_60_bars"]}, "trading": {"orders_enabled": False}},
        "9999": {"symbol": "9999", "ok": False, "error": "no_daily_bars", "quality": {"warnings": ["no_daily_bars"]}},
    })

    report = preflight.preflight_monitor_config(path=str(path), trend_service=service)

    assert service.calls == [("2330", 80), ("0050", 80), ("9999", 80)]
    assert report["symbol_count"] == 3
    assert report["ok_count"] == 2
    assert report["warning_count"] == 1
    assert report["failed_count"] == 1
    assert report["warning_symbols"] == ["0050"]
    assert report["failed_symbols"] == ["9999"]
    assert report["orders_enabled"] is False
    assert report["scanned"] is False
    assert report["alerts_created"] == 0
    assert report["db_written"] is False
    assert report["quality_gate"]["status"] == "fail"
    assert report["quality_gate"]["ready_for_manual_review"] is False
    assert report["quality_gate"]["orders_enabled"] is False
    assert report["quality_gate"]["db_written"] is False


def test_quality_gate_passes_when_history_and_freshness_are_acceptable(tmp_path):
    path = tmp_path / "monitor.json"
    path.write_text(json.dumps({"symbols": ["2330"], "limit_bars": 120}), encoding="utf-8")
    service = FakeTrendService({
        "2330": {
            "symbol": "2330",
            "ok": True,
            "quality": {"bar_count": 120, "stale_days": 1, "warnings": []},
            "trading": {"orders_enabled": False},
        },
    })

    report = preflight.preflight_monitor_config(path=str(path), trend_service=service)

    assert report["quality_gate"] == {
        "ready_for_manual_review": True,
        "status": "pass",
        "min_bars_required": 60,
        "max_stale_days_allowed": 5,
        "min_seen_bar_count": 120,
        "max_seen_stale_days": 1,
        "failure_count": 0,
        "warning_count": 0,
        "failures": [],
        "warnings": [],
        "orders_enabled": False,
        "db_written": False,
    }


def test_quality_gate_flags_stale_or_short_history(tmp_path):
    path = tmp_path / "monitor.json"
    path.write_text(json.dumps({"symbols": ["2330", "0050"]}), encoding="utf-8")
    service = FakeTrendService({
        "2330": {
            "symbol": "2330",
            "ok": True,
            "quality": {"bar_count": 59, "stale_days": 0, "warnings": ["short_history_below_60_bars"]},
        },
        "0050": {
            "symbol": "0050",
            "ok": True,
            "quality": {"bar_count": 120, "stale_days": 8, "warnings": ["stale_daily_bar"]},
        },
    })

    report = preflight.preflight_monitor_config(path=str(path), trend_service=service)

    gate = report["quality_gate"]
    assert gate["status"] == "fail"
    assert gate["ready_for_manual_review"] is False
    assert gate["failure_count"] == 2
    assert gate["failures"] == [
        {"symbol": "2330", "reason": "insufficient_history", "bar_count": 59},
        {"symbol": "0050", "reason": "stale_daily_bar", "stale_days": 8},
    ]


def test_cli_exit_codes(monkeypatch, tmp_path, capsys):
    path = tmp_path / "monitor.json"
    path.write_text(json.dumps({"symbols": ["2330"]}), encoding="utf-8")
    monkeypatch.setattr(preflight, "preflight_monitor_config", lambda **kwargs: {"failed_count": 0, "warning_count": 1, "orders_enabled": False})

    rc = preflight.main(["--input-json", str(path), "--fail-on-warning"])

    assert rc == 1
    assert json.loads(capsys.readouterr().out)["orders_enabled"] is False

    monkeypatch.setattr(preflight, "preflight_monitor_config", lambda **kwargs: {"failed_count": 1, "warning_count": 0, "orders_enabled": False})
    assert preflight.main(["--input-json", str(path)]) == 2

    monkeypatch.setattr(
        preflight,
        "preflight_monitor_config",
        lambda **kwargs: {
            "failed_count": 0,
            "warning_count": 0,
            "orders_enabled": False,
            "quality_gate": {"ready_for_manual_review": False},
        },
    )
    assert preflight.main(["--input-json", str(path), "--fail-on-quality-gate"]) == 3
