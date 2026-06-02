"""Tests for TWStock IBKR paper/live preflight."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "preflight_tw_stock_ibkr_live.py"
SPEC = importlib.util.spec_from_file_location("preflight_tw_stock_ibkr_live", SCRIPT_PATH)
preflight_tw_stock_ibkr_live = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules["preflight_tw_stock_ibkr_live"] = preflight_tw_stock_ibkr_live
SPEC.loader.exec_module(preflight_tw_stock_ibkr_live)


def _token_row(*, paper_only=True, scopes="R,T", markets="TWStock", status="active"):
    return {"id": 1, "user_id": 1, "name": "paper-token", "scopes": scopes, "markets": markets, "instruments": "*", "paper_only": paper_only, "rate_limit_per_min": 60, "status": status}


def test_paper_preflight_passes_with_paper_token_and_valid_symbols():
    report = preflight_tw_stock_ibkr_live.build_preflight_report(symbols=["2330", "TPEX:6488"], agent_token_row=_token_row(paper_only=True), env={"AGENT_LIVE_TRADING_ENABLED": "false", "ALLOW_LOCAL_DESKTOP_BROKERS": "true", "IBKR_ORDER_CLIENT_ID": "7"})
    assert report["status"] == "pass"
    assert report["connects_to_ibkr"] is False
    assert report["submits_orders"] is False
    assert any(item["name"] == "contract_mapping:TPEX:6488" and item["ok"] for item in report["checks"])


def test_paper_preflight_warns_when_live_switch_enabled():
    report = preflight_tw_stock_ibkr_live.build_preflight_report(symbols=["2330"], agent_token_row=_token_row(paper_only=True), env={"AGENT_LIVE_TRADING_ENABLED": "true", "ALLOW_LOCAL_DESKTOP_BROKERS": "true", "IBKR_ORDER_CLIENT_ID": "7"})
    assert report["status"] == "warning"
    assert any(item["name"] == "agent_live_kill_switch" and not item["ok"] for item in report["checks"])


def test_live_preflight_fails_when_token_is_still_paper_only():
    report = preflight_tw_stock_ibkr_live.build_preflight_report(symbols=["2330"], agent_token_row=_token_row(paper_only=True), require_live=True, env={"AGENT_LIVE_TRADING_ENABLED": "true", "ALLOW_LOCAL_DESKTOP_BROKERS": "true", "IBKR_ORDER_CLIENT_ID": "7"})
    assert report["status"] == "fail"
    assert any(item["name"] == "agent_token:paper_only_mode" and not item["ok"] for item in report["checks"])


def test_live_preflight_requires_live_kill_switch():
    report = preflight_tw_stock_ibkr_live.build_preflight_report(symbols=["2330"], agent_token_row=_token_row(paper_only=False), require_live=True, env={"AGENT_LIVE_TRADING_ENABLED": "false", "ALLOW_LOCAL_DESKTOP_BROKERS": "true", "IBKR_ORDER_CLIENT_ID": "7"})
    assert report["status"] == "fail"
    assert any(item["name"] == "agent_live_kill_switch" and not item["ok"] for item in report["checks"])


def test_preflight_rejects_invalid_tw_symbol_mapping():
    report = preflight_tw_stock_ibkr_live.build_preflight_report(symbols=["BAD"], agent_token_row=_token_row(paper_only=True), env={"AGENT_LIVE_TRADING_ENABLED": "false", "ALLOW_LOCAL_DESKTOP_BROKERS": "true", "IBKR_ORDER_CLIENT_ID": "7"})
    assert report["status"] == "fail"
    assert any(item["name"] == "contract_mapping:BAD" and not item["ok"] for item in report["checks"])


def test_render_markdown_includes_red_lines():
    report = preflight_tw_stock_ibkr_live.build_preflight_report(symbols=["2330"], agent_token_row=_token_row(paper_only=True), env={"AGENT_LIVE_TRADING_ENABLED": "false", "ALLOW_LOCAL_DESKTOP_BROKERS": "true", "IBKR_ORDER_CLIENT_ID": "7"})
    text = preflight_tw_stock_ibkr_live.render_markdown(report)
    assert "TWStock IBKR Paper/Live Preflight" in text
    assert "Do not enable live" in text


def test_main_writes_outputs(monkeypatch, tmp_path):
    monkeypatch.setattr(preflight_tw_stock_ibkr_live, "load_agent_token_row", lambda token: _token_row(paper_only=True))
    out_json = tmp_path / "preflight.json"
    out_md = tmp_path / "preflight.md"
    exit_code = preflight_tw_stock_ibkr_live.main(["--symbol", "2330,0050", "--agent-token", "qd_agent_TOKEN", "--output-json", str(out_json), "--output-md", str(out_md)])
    assert exit_code in (0, 1)
    assert json.loads(out_json.read_text(encoding="utf-8"))["broker"] == "ibkr"
    assert "TWStock IBKR Paper/Live Preflight" in out_md.read_text(encoding="utf-8")
