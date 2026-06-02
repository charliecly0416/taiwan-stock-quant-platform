"""Tests for TWStock paper execution report assembly."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "build_tw_stock_paper_execution_report.py"
SPEC = importlib.util.spec_from_file_location("build_tw_stock_paper_execution_report", SCRIPT_PATH)
build_tw_stock_paper_execution_report = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules["build_tw_stock_paper_execution_report"] = build_tw_stock_paper_execution_report
SPEC.loader.exec_module(build_tw_stock_paper_execution_report)


def _pipeline():
    return {
        "dry_run": False,
        "preview_summary": {"order_count": 1, "blocked_count": 0, "warnings": []},
        "submit_summary": {"submit_candidate_count": 1, "submitted_count": 1, "failed_submit_count": 0},
        "guard_errors": [],
        "preview": {"orders": [{"symbol": "2317", "side": "buy", "qty": 6000, "order_type": "limit", "limit_price": 251.25, "reference_price": 250.0, "status": "preview", "estimated_notional": 1500000.0}]},
        "submit": {"payloads": [{"market": "TWStock", "symbol": "2317", "side": "buy", "qty": 6000}], "submit_results": [{"ok": True}]},
    }


def _verification():
    return {"expected_count": 1, "matched_count": 1, "missing_count": 0, "matched_order_uids": ["paper-1"], "missing_order_uids": []}


def _summary():
    return {"data": {"initial_cash": 5000000.0, "cash": 3500000.0, "gross_buy_value": 1500000.0, "gross_sell_value": 0.0, "realized_pnl": 0.0, "open_cost_value": 1500000.0, "equity_at_cost": 5000000.0, "position_count": 1, "positions": [{"symbol": "2317", "quantity": 6000}], "warnings": []}}


def test_build_report_passes_for_clean_pipeline():
    report = build_tw_stock_paper_execution_report.build_report(pipeline=_pipeline(), verification=_verification(), portfolio_summary=_summary())

    assert report["status"] == "pass"
    assert report["pipeline"]["submitted_count"] == 1
    assert report["verification"]["matched_count"] == 1
    assert report["portfolio_summary"]["cash"] == 3500000.0
    assert report["safety"] == {"paper_only": True, "broker_connected": False, "live_order_submitted": False}


def test_build_report_fails_when_verified_order_missing():
    verification = _verification()
    verification["missing_count"] = 1
    verification["missing_order_uids"] = ["paper-missing"]

    report = build_tw_stock_paper_execution_report.build_report(pipeline=_pipeline(), verification=verification, portfolio_summary=_summary())

    assert report["status"] == "fail"
    assert "missing_verified_orders" in report["status_reasons"]


def test_render_markdown_includes_orders_and_safety():
    report = build_tw_stock_paper_execution_report.build_report(pipeline=_pipeline(), verification=_verification(), portfolio_summary=_summary())

    text = build_tw_stock_paper_execution_report.render_markdown(report)

    assert "TWStock Paper Execution Report" in text
    assert "Broker connected: False" in text
    assert "2317 buy 6000" in text


def test_main_writes_json_and_markdown(tmp_path):
    pipeline = tmp_path / "pipeline.json"
    verify = tmp_path / "verify.json"
    summary = tmp_path / "summary.json"
    out_json = tmp_path / "report.json"
    out_md = tmp_path / "report.md"
    pipeline.write_text(json.dumps(_pipeline()), encoding="utf-8")
    verify.write_text(json.dumps(_verification()), encoding="utf-8")
    summary.write_text(json.dumps(_summary()), encoding="utf-8")

    exit_code = build_tw_stock_paper_execution_report.main([
        "--pipeline-json", str(pipeline),
        "--verify-json", str(verify),
        "--portfolio-summary-json", str(summary),
        "--output-json", str(out_json),
        "--output-md", str(out_md),
    ])

    assert exit_code == 0
    assert json.loads(out_json.read_text(encoding="utf-8"))["status"] == "pass"
    assert "TWStock Paper Execution Report" in out_md.read_text(encoding="utf-8")


def test_build_report_warns_when_submit_result_is_rejected():
    pipeline = _pipeline()
    pipeline["submit"]["submit_results"] = [
        {"ok": True, "response": {"code": 0, "data": {"order_uid": "paper-1", "status": "rejected", "note": "paper limit not marketable"}}}
    ]

    report = build_tw_stock_paper_execution_report.build_report(pipeline=pipeline, verification=_verification(), portfolio_summary=_summary())

    assert report["status"] == "warning"
    assert "rejected_paper_orders" in report["status_reasons"]
    assert report["pipeline"]["rejected_submit_count"] == 1
    assert report["rejected_submit_results"][0]["response"]["data"]["status"] == "rejected"

