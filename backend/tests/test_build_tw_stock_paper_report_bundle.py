"""Tests for TWStock post-submit paper report bundle assembly."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "build_tw_stock_paper_report_bundle.py"
SPEC = importlib.util.spec_from_file_location("build_tw_stock_paper_report_bundle", SCRIPT_PATH)
build_tw_stock_paper_report_bundle = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules["build_tw_stock_paper_report_bundle"] = build_tw_stock_paper_report_bundle
SPEC.loader.exec_module(build_tw_stock_paper_report_bundle)


def _pipeline():
    return {
        "dry_run": False,
        "preview_summary": {"order_count": 1, "blocked_count": 0},
        "submit_summary": {"submit_candidate_count": 1, "submitted_count": 1, "failed_submit_count": 0},
        "guard_errors": [],
        "preview": {
            "orders": [
                {
                    "symbol": "2317",
                    "side": "buy",
                    "qty": 6000,
                    "order_type": "limit",
                    "limit_price": 251.25,
                    "reference_price": 250.0,
                    "status": "preview",
                    "estimated_notional": 1500000.0,
                }
            ]
        },
        "submit": {
            "payloads": [{"market": "TWStock", "symbol": "2317", "side": "buy", "qty": 6000}],
            "submit_results": [{"ok": True, "response": {"code": 0, "data": {"order_uid": "paper-1"}}}],
        },
    }


def _summary_response():
    return {
        "code": 0,
        "data": {
            "initial_cash": 5000000.0,
            "cash": 3500000.0,
            "gross_buy_value": 1500000.0,
            "gross_sell_value": 0.0,
            "realized_pnl": 0.0,
            "open_cost_value": 1500000.0,
            "equity_at_cost": 5000000.0,
            "position_count": 1,
            "positions": [{"market": "TWStock", "symbol": "2317", "quantity": 6000}],
            "warnings": [],
        },
    }


def test_fetch_paper_summary_calls_agent_endpoint(monkeypatch):
    calls = []

    class FakeResponse:
        status_code = 200
        text = "ok"

        def json(self):
            return _summary_response()

    def fake_get(url, headers, params, timeout):
        calls.append({"url": url, "headers": headers, "params": params, "timeout": timeout})
        return FakeResponse()

    monkeypatch.setattr(build_tw_stock_paper_report_bundle.requests, "get", fake_get)

    fetched = build_tw_stock_paper_report_bundle.fetch_paper_summary(
        api_base_url="http://localhost:5000/",
        agent_token="qd_agent_TOKEN",
        initial_cash=5000000,
        timeout=3,
    )

    assert calls[0]["url"] == "http://localhost:5000/api/agent/v1/portfolio/paper-summary"
    assert calls[0]["headers"]["Authorization"] == "Bearer qd_agent_TOKEN"
    assert calls[0]["params"] == {"initial_cash": 5000000}
    assert fetched["data"]["cash"] == 3500000.0


def test_build_bundle_passes_for_verified_submit_and_summary():
    bundle = build_tw_stock_paper_report_bundle.build_bundle(
        pipeline_report=_pipeline(),
        fetched_orders={"ok": True, "status_code": 200, "orders": [{"order_uid": "paper-1", "symbol": "2317"}]},
        fetched_summary={"ok": True, "status_code": 200, "response": _summary_response()},
    )

    assert bundle["status"] == "pass"
    assert bundle["verification"]["matched_count"] == 1
    assert bundle["execution_report"]["portfolio_summary"]["cash"] == 3500000.0
    assert bundle["execution_report"]["safety"]["live_order_submitted"] is False


def test_build_bundle_fails_when_summary_fetch_fails():
    bundle = build_tw_stock_paper_report_bundle.build_bundle(
        pipeline_report=_pipeline(),
        fetched_orders={"ok": True, "status_code": 200, "orders": [{"order_uid": "paper-1"}]},
        fetched_summary={"ok": False, "status_code": 500, "response": {"code": 500}},
    )

    assert bundle["status"] == "fail"
    assert "paper_summary_fetch_failed" in bundle["status_reasons"]


def test_main_writes_bundle_artifacts(monkeypatch, tmp_path):
    pipeline = tmp_path / "pipeline.json"
    pipeline.write_text(json.dumps(_pipeline()), encoding="utf-8")
    out = tmp_path / "bundle.json"
    verify = tmp_path / "verify.json"
    summary = tmp_path / "summary.json"
    report_json = tmp_path / "report.json"
    report_md = tmp_path / "report.md"
    monkeypatch.setattr(
        build_tw_stock_paper_report_bundle,
        "fetch_paper_orders",
        lambda **kwargs: {"ok": True, "status_code": 200, "orders": [{"order_uid": "paper-1"}]},
    )
    monkeypatch.setattr(
        build_tw_stock_paper_report_bundle,
        "fetch_paper_summary",
        lambda **kwargs: {"ok": True, "status_code": 200, "response": _summary_response()},
    )

    exit_code = build_tw_stock_paper_report_bundle.main([
        "--pipeline-json",
        str(pipeline),
        "--agent-token",
        "qd_agent_TOKEN",
        "--initial-cash",
        "5000000",
        "--output-json",
        str(out),
        "--verify-output-json",
        str(verify),
        "--summary-output-json",
        str(summary),
        "--execution-report-json",
        str(report_json),
        "--execution-report-md",
        str(report_md),
    ])

    assert exit_code == 0
    assert json.loads(out.read_text(encoding="utf-8"))["status"] == "pass"
    assert json.loads(verify.read_text(encoding="utf-8"))["matched_count"] == 1
    assert json.loads(summary.read_text(encoding="utf-8"))["data"]["cash"] == 3500000.0
    assert json.loads(report_json.read_text(encoding="utf-8"))["status"] == "pass"
    assert "TWStock Paper Execution Report" in report_md.read_text(encoding="utf-8")
