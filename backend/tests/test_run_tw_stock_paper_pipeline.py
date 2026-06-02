"""Offline tests for TWStock paper order end-to-end pipeline."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "run_tw_stock_paper_pipeline.py"
SPEC = importlib.util.spec_from_file_location("run_tw_stock_paper_pipeline", SCRIPT_PATH)
run_tw_stock_paper_pipeline = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules["run_tw_stock_paper_pipeline"] = run_tw_stock_paper_pipeline
SPEC.loader.exec_module(run_tw_stock_paper_pipeline)


def test_run_pipeline_builds_preview_and_submit_payloads(monkeypatch, tmp_path):
    monkeypatch.setattr(run_tw_stock_paper_pipeline, "resolve_prices", lambda symbols, price_map, as_of: {"2317": 250.0})
    plan = tmp_path / "plan.json"
    plan.write_text(json.dumps({"target_positions": [{"symbol": "2317", "target_weight": 0.3}]}), encoding="utf-8")

    report = run_tw_stock_paper_pipeline.run_pipeline(plan_json=str(plan), portfolio_value=5_000_000, as_of="2026-05-22")

    assert report["dry_run"] is True
    assert report["preview_summary"]["order_count"] == 1
    assert report["submit_summary"]["submit_candidate_count"] == 1
    assert report["submit"]["payloads"][0] == {
        "market": "TWStock",
        "symbol": "2317",
        "side": "buy",
        "qty": 6000,
        "order_type": "limit",
        "limit_price": 251.25,
        "lot_size": 1000,
        "source": "tw_stock_paper_order_preview",
    }


def test_evaluate_pipeline_guards_detects_warning_blocked_and_count():
    errors = run_tw_stock_paper_pipeline.evaluate_pipeline_guards(
        preview={"warnings": ["target_below_one_lot:2330"], "blocked_count": 1},
        payloads=[{"symbol": "2317"}, {"symbol": "2330"}],
        fail_on_warning=True,
        fail_on_blocked=True,
        max_submit_candidates=1,
    )

    assert errors == ["warnings_present", "blocked_orders_present", "max_submit_candidates_exceeded"]


def test_run_pipeline_records_guard_errors_in_dry_run(monkeypatch, tmp_path):
    monkeypatch.setattr(run_tw_stock_paper_pipeline, "resolve_prices", lambda symbols, price_map, as_of: {"2330": 2000.0})
    plan = tmp_path / "plan.json"
    plan.write_text(json.dumps({"target_positions": [{"symbol": "2330", "target_weight": 0.3}]}), encoding="utf-8")

    report = run_tw_stock_paper_pipeline.run_pipeline(
        plan_json=str(plan),
        portfolio_value=5_000_000,
        fail_on_warning=True,
    )

    assert report["guard_errors"] == ["warnings_present"]
    assert report["guards"]["fail_on_warning"] is True


def test_main_returns_three_when_guard_fails(monkeypatch, tmp_path):
    monkeypatch.setattr(run_tw_stock_paper_pipeline, "resolve_prices", lambda symbols, price_map, as_of: {"2330": 2000.0})
    plan = tmp_path / "plan.json"
    plan.write_text(json.dumps({"target_positions": [{"symbol": "2330", "target_weight": 0.3}]}), encoding="utf-8")

    exit_code = run_tw_stock_paper_pipeline.main([
        "--plan-json",
        str(plan),
        "--portfolio-value",
        "5000000",
        "--fail-on-warning",
    ])

    assert exit_code == 3


def test_submit_guard_fails_before_http_call(monkeypatch, tmp_path):
    monkeypatch.setattr(run_tw_stock_paper_pipeline, "resolve_prices", lambda symbols, price_map, as_of: {"2317": 250.0, "2412": 100.0})

    def fail_submit(**kwargs):
        raise AssertionError("submit_payloads should not be called")

    monkeypatch.setattr(run_tw_stock_paper_pipeline, "submit_payloads", fail_submit)
    plan = tmp_path / "plan.json"
    plan.write_text(
        json.dumps({"target_positions": [
            {"symbol": "2317", "target_weight": 0.3},
            {"symbol": "2412", "target_weight": 0.3},
        ]}),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="max_submit_candidates_exceeded"):
        run_tw_stock_paper_pipeline.run_pipeline(
            plan_json=str(plan),
            portfolio_value=5_000_000,
            submit=True,
            agent_token="qd_agent_TOKEN",
            max_submit_candidates=1,
            fail_on_warning=False,
            fail_on_blocked=False,
        )


def test_main_writes_pipeline_preview_and_submit_outputs(monkeypatch, tmp_path):
    monkeypatch.setattr(run_tw_stock_paper_pipeline, "resolve_prices", lambda symbols, price_map, as_of: {"2317": 250.0})
    plan = tmp_path / "plan.json"
    plan.write_text(json.dumps({"target_positions": [{"symbol": "2317", "target_weight": 0.3}]}), encoding="utf-8")
    output = tmp_path / "pipeline.json"
    preview = tmp_path / "preview.json"
    submit = tmp_path / "submit.json"

    exit_code = run_tw_stock_paper_pipeline.main([
        "--plan-json",
        str(plan),
        "--portfolio-value",
        "5000000",
        "--output-json",
        str(output),
        "--preview-output-json",
        str(preview),
        "--submit-output-json",
        str(submit),
    ])

    assert exit_code == 0
    assert json.loads(output.read_text(encoding="utf-8"))["market"] == "TWStock"
    assert json.loads(preview.read_text(encoding="utf-8"))["order_count"] == 1
    assert json.loads(submit.read_text(encoding="utf-8"))["submit_candidate_count"] == 1


def test_main_submit_requires_agent_token(monkeypatch, tmp_path):
    monkeypatch.setattr(run_tw_stock_paper_pipeline, "resolve_prices", lambda symbols, price_map, as_of: {"2317": 250.0})
    plan = tmp_path / "plan.json"
    plan.write_text(json.dumps({"target_positions": [{"symbol": "2317", "target_weight": 0.3}]}), encoding="utf-8")

    exit_code = run_tw_stock_paper_pipeline.main([
        "--plan-json",
        str(plan),
        "--portfolio-value",
        "5000000",
        "--submit",
    ])

    assert exit_code == 2


def test_run_pipeline_submit_uses_submit_payloads(monkeypatch, tmp_path):
    monkeypatch.setattr(run_tw_stock_paper_pipeline, "resolve_prices", lambda symbols, price_map, as_of: {"2317": 250.0})
    captured = {}

    def fake_submit(*, payloads, api_base_url, agent_token, timeout):
        captured.update({"payloads": payloads, "api_base_url": api_base_url, "agent_token": agent_token, "timeout": timeout})
        return [{"ok": True, "status_code": 200, "payload": payloads[0], "response": {"code": 0}}]

    monkeypatch.setattr(run_tw_stock_paper_pipeline, "submit_payloads", fake_submit)
    plan = tmp_path / "plan.json"
    plan.write_text(json.dumps({"target_positions": [{"symbol": "2317", "target_weight": 0.3}]}), encoding="utf-8")

    report = run_tw_stock_paper_pipeline.run_pipeline(
        plan_json=str(plan),
        portfolio_value=5_000_000,
        submit=True,
        api_base_url="http://localhost:5000",
        agent_token="qd_agent_TOKEN",
        timeout=7,
    )

    assert report["dry_run"] is False
    assert report["submit_summary"]["submitted_count"] == 1
    assert captured["agent_token"] == "qd_agent_TOKEN"

def test_main_writes_execution_report_when_verify_and_summary_provided(monkeypatch, tmp_path):
    monkeypatch.setattr(run_tw_stock_paper_pipeline, "resolve_prices", lambda symbols, price_map, as_of: {"2317": 250.0})
    plan = tmp_path / "plan.json"
    verify = tmp_path / "verify.json"
    summary = tmp_path / "summary.json"
    report_json = tmp_path / "execution_report.json"
    report_md = tmp_path / "execution_report.md"
    plan.write_text(json.dumps({"target_positions": [{"symbol": "2317", "target_weight": 0.3}]}), encoding="utf-8")
    verify.write_text(json.dumps({"expected_count": 0, "matched_count": 0, "missing_count": 0, "matched_order_uids": [], "missing_order_uids": []}), encoding="utf-8")
    summary.write_text(json.dumps({"data": {"initial_cash": 5000000.0, "cash": 3500000.0, "gross_buy_value": 1500000.0, "gross_sell_value": 0.0, "realized_pnl": 0.0, "open_cost_value": 1500000.0, "equity_at_cost": 5000000.0, "position_count": 1, "positions": [{"symbol": "2317", "quantity": 6000}], "warnings": []}}), encoding="utf-8")

    exit_code = run_tw_stock_paper_pipeline.main([
        "--plan-json", str(plan),
        "--portfolio-value", "5000000",
        "--verify-json", str(verify),
        "--portfolio-summary-json", str(summary),
        "--execution-report-json", str(report_json),
        "--execution-report-md", str(report_md),
    ])

    assert exit_code == 0
    payload = json.loads(report_json.read_text(encoding="utf-8"))
    assert payload["market"] == "TWStock"
    assert payload["status"] == "pass"
    assert payload["portfolio_summary"]["cash"] == 3500000.0
    assert "TWStock Paper Execution Report" in report_md.read_text(encoding="utf-8")


def test_main_execution_report_requires_verify_and_summary_together(monkeypatch, tmp_path):
    monkeypatch.setattr(run_tw_stock_paper_pipeline, "resolve_prices", lambda symbols, price_map, as_of: {"2317": 250.0})
    plan = tmp_path / "plan.json"
    verify = tmp_path / "verify.json"
    plan.write_text(json.dumps({"target_positions": [{"symbol": "2317", "target_weight": 0.3}]}), encoding="utf-8")
    verify.write_text(json.dumps({"expected_count": 0}), encoding="utf-8")

    exit_code = run_tw_stock_paper_pipeline.main([
        "--plan-json", str(plan),
        "--portfolio-value", "5000000",
        "--verify-json", str(verify),
        "--execution-report-json", str(tmp_path / "execution_report.json"),
    ])

    assert exit_code == 2

