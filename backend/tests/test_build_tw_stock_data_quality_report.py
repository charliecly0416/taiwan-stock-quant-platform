"""Tests for read-only TWStock data quality report builder."""
from __future__ import annotations

import json

from scripts import build_tw_stock_data_quality_report as report_builder


def _preflight_report():
    return {
        "config": {"name": "sample"},
        "symbol_count": 2,
        "ok_count": 1,
        "failed_count": 1,
        "warning_count": 1,
        "orders_enabled": False,
        "scanned": False,
        "alerts_created": 0,
        "db_written": False,
        "quality_gate": {
            "ready_for_manual_review": False,
            "status": "fail",
            "failure_count": 1,
            "warning_count": 0,
            "failures": [{"symbol": "0050", "reason": "stale_daily_bar", "stale_days": 8}],
            "warnings": [],
            "orders_enabled": False,
            "db_written": False,
        },
        "items": [
            {
                "symbol": "2330",
                "ok": True,
                "latest": {"date": "2026-05-22"},
                "trend": {"label": "uptrend", "score": 72.5},
                "quality": {"bar_count": 120, "stale_days": 1, "warnings": []},
            },
            {
                "symbol": "0050",
                "ok": True,
                "latest": {"date": "2026-05-15"},
                "trend": {"label": "sideways", "score": 50.0},
                "quality": {"bar_count": 120, "stale_days": 8, "warnings": ["stale_daily_bar"]},
            },
        ],
    }


def test_build_quality_report_summarizes_preflight_without_side_effects():
    report = report_builder.build_quality_report(input_json="sample.json", preflight=_preflight_report())

    assert report["input_json"] == "sample.json"
    assert report["config_name"] == "sample"
    assert report["symbol_count"] == 2
    assert report["quality_gate"]["status"] == "fail"
    assert report["symbols"][0]["symbol"] == "2330"
    assert report["symbols"][1]["failures"] == [{"symbol": "0050", "reason": "stale_daily_bar", "stale_days": 8}]
    assert report["orders_enabled"] is False
    assert report["writes_production_data"] is False
    assert report["connects_to_broker"] is False
    assert report["scanned"] is False
    assert report["alerts_created"] == 0


def test_render_markdown_includes_quality_gate_and_symbol_table():
    report = report_builder.build_quality_report(input_json="sample.json", preflight=_preflight_report())

    markdown = report_builder.render_markdown(report)

    assert "# TWStock Data Quality Report" in markdown
    assert "quality_gate_status: `fail`" in markdown
    assert "orders_enabled: `False`" in markdown
    assert "| 0050 | True | 2026-05-15 | 120 | 8 | sideways | 50.0 | stale_daily_bar | stale_daily_bar |" in markdown


def test_main_writes_reports_and_returns_quality_gate_code(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(
        report_builder,
        "preflight_monitor_config",
        lambda **kwargs: _preflight_report(),
    )
    json_path = tmp_path / "quality.json"
    md_path = tmp_path / "quality.md"

    rc = report_builder.main([
        "--input-json",
        "sample.json",
        "--output-json",
        str(json_path),
        "--output-md",
        str(md_path),
        "--fail-on-quality-gate",
    ])

    assert rc == 3
    stdout = json.loads(capsys.readouterr().out)
    assert stdout["orders_enabled"] is False
    assert json.loads(json_path.read_text(encoding="utf-8"))["connects_to_broker"] is False
    assert "TWStock Data Quality Report" in md_path.read_text(encoding="utf-8")
