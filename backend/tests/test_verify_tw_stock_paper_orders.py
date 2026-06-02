"""Offline tests for TWStock paper order read-back verification."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "verify_tw_stock_paper_orders.py"
SPEC = importlib.util.spec_from_file_location("verify_tw_stock_paper_orders", SCRIPT_PATH)
verify_tw_stock_paper_orders = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules["verify_tw_stock_paper_orders"] = verify_tw_stock_paper_orders
SPEC.loader.exec_module(verify_tw_stock_paper_orders)


def _submit_report():
    return {
        "submit_results": [
            {"ok": True, "response": {"code": 0, "data": {"order_uid": "paper-1"}}},
            {"ok": False, "response": {"code": 400, "data": {"order_uid": "paper-bad"}}},
            {"ok": True, "response": {"code": 0, "data": {"order_uid": "paper-2"}}},
        ]
    }


def test_extract_order_uids_from_submit_report():
    assert verify_tw_stock_paper_orders.extract_order_uids(_submit_report()) == ["paper-1", "paper-2"]


def test_extract_order_uids_from_pipeline_report():
    report = {"submit": _submit_report()}

    assert verify_tw_stock_paper_orders.extract_order_uids(report) == ["paper-1", "paper-2"]


def test_build_report_marks_missing_orders():
    fetched = {
        "ok": True,
        "status_code": 200,
        "orders": [
            {"order_uid": "paper-1", "market": "TWStock", "symbol": "2317"},
            {"order_uid": "other", "market": "TWStock", "symbol": "2330"},
        ],
    }

    report = verify_tw_stock_paper_orders.build_report(expected_order_uids=["paper-1", "paper-2"], fetched=fetched)

    assert report["matched_order_uids"] == ["paper-1"]
    assert report["missing_order_uids"] == ["paper-2"]
    assert report["missing_count"] == 1
    assert report["matched_orders"] == [{"order_uid": "paper-1", "market": "TWStock", "symbol": "2317"}]


def test_fetch_paper_orders_calls_agent_portfolio_endpoint(monkeypatch):
    calls = []

    class FakeResponse:
        status_code = 200
        text = "ok"

        def json(self):
            return {"code": 0, "data": [{"order_uid": "paper-1"}]}

    def fake_get(url, headers, timeout):
        calls.append({"url": url, "headers": headers, "timeout": timeout})
        return FakeResponse()

    monkeypatch.setattr(verify_tw_stock_paper_orders.requests, "get", fake_get)

    fetched = verify_tw_stock_paper_orders.fetch_paper_orders(
        api_base_url="http://localhost:5000/",
        agent_token="qd_agent_TOKEN",
        timeout=3,
    )

    assert calls[0]["url"] == "http://localhost:5000/api/agent/v1/portfolio/paper-orders"
    assert calls[0]["headers"]["Authorization"] == "Bearer qd_agent_TOKEN"
    assert fetched["orders"] == [{"order_uid": "paper-1"}]


def test_main_writes_success_report(monkeypatch, tmp_path):
    submit_report = tmp_path / "submit.json"
    submit_report.write_text(json.dumps(_submit_report()), encoding="utf-8")
    output = tmp_path / "verify.json"
    monkeypatch.setattr(
        verify_tw_stock_paper_orders,
        "fetch_paper_orders",
        lambda **kwargs: {"ok": True, "status_code": 200, "orders": [{"order_uid": "paper-1"}, {"order_uid": "paper-2"}]},
    )

    exit_code = verify_tw_stock_paper_orders.main([
        "--submit-report-json",
        str(submit_report),
        "--agent-token",
        "qd_agent_TOKEN",
        "--output-json",
        str(output),
    ])

    assert exit_code == 0
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["matched_count"] == 2
    assert report["missing_count"] == 0


def test_main_returns_two_when_no_successful_order_uid(tmp_path):
    submit_report = tmp_path / "submit.json"
    submit_report.write_text(json.dumps({"submit_results": [{"ok": False, "response": {}}]}), encoding="utf-8")

    exit_code = verify_tw_stock_paper_orders.main([
        "--submit-report-json",
        str(submit_report),
        "--agent-token",
        "qd_agent_TOKEN",
    ])

    assert exit_code == 2
