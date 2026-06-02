"""Offline tests for TWStock paper order submission bridge."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "submit_tw_stock_paper_orders.py"
SPEC = importlib.util.spec_from_file_location("submit_tw_stock_paper_orders", SCRIPT_PATH)
submit_tw_stock_paper_orders = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules["submit_tw_stock_paper_orders"] = submit_tw_stock_paper_orders
SPEC.loader.exec_module(submit_tw_stock_paper_orders)


def _preview_payload():
    return {
        "market": "TWStock",
        "paper_only": True,
        "warnings": ["target_below_one_lot:2330"],
        "assumptions": {"lot_size": 1000},
        "orders": [
            {"symbol": "2317", "side": "buy", "qty": 6000, "order_type": "limit", "limit_price": 251.25, "status": "preview"},
            {"symbol": "2454", "side": "buy", "qty": 1000, "order_type": "limit", "limit_price": 1500, "status": "blocked"},
        ],
    }


def test_build_quick_trade_payloads_filters_preview_orders_only():
    payloads = submit_tw_stock_paper_orders.build_quick_trade_payloads(_preview_payload())

    assert payloads == [{
        "market": "TWStock",
        "symbol": "2317",
        "side": "buy",
        "qty": 6000,
        "order_type": "limit",
        "limit_price": 251.25,
        "lot_size": 1000,
        "source": "tw_stock_paper_order_preview",
    }]


def test_build_quick_trade_payloads_adds_current_qty_for_sells():
    preview = {"assumptions": {"lot_size": 1000}, "orders": [{"symbol": "2317", "side": "sell", "qty": 2000, "current_qty": 6000, "limit_price": 249, "status": "preview"}]}

    payload = submit_tw_stock_paper_orders.build_quick_trade_payloads(preview)[0]

    assert payload["current_qty"] == 6000


def test_build_quick_trade_payloads_falls_back_to_qty_for_legacy_sell_previews():
    preview = {"assumptions": {"lot_size": 1000}, "orders": [{"symbol": "2317", "side": "sell", "qty": 2000, "limit_price": 249, "status": "preview"}]}

    payload = submit_tw_stock_paper_orders.build_quick_trade_payloads(preview)[0]

    assert payload["current_qty"] == 2000


def test_build_report_is_dry_run_without_submit_results():
    payloads = submit_tw_stock_paper_orders.build_quick_trade_payloads(_preview_payload())
    report = submit_tw_stock_paper_orders.build_report(preview=_preview_payload(), payloads=payloads)

    assert report["dry_run"] is True
    assert report["submit_candidate_count"] == 1
    assert report["skipped_count"] == 1
    assert report["warnings"] == ["target_below_one_lot:2330"]


def test_submit_payloads_posts_to_agent_quick_trade(monkeypatch):
    calls = []

    class FakeResponse:
        status_code = 200
        text = "ok"

        def json(self):
            return {"code": 0, "data": {"paper": True}}

    def fake_post(url, headers, json, timeout):
        calls.append({"url": url, "headers": headers, "json": json, "timeout": timeout})
        return FakeResponse()

    monkeypatch.setattr(submit_tw_stock_paper_orders.requests, "post", fake_post)

    results = submit_tw_stock_paper_orders.submit_payloads(
        payloads=[{"market": "TWStock", "symbol": "2317"}],
        api_base_url="http://localhost:5000/",
        agent_token="qd_agent_TOKEN",
        timeout=3,
    )

    assert calls[0]["url"] == "http://localhost:5000/api/agent/v1/quick-trade/orders"
    assert calls[0]["headers"]["Authorization"] == "Bearer qd_agent_TOKEN"
    assert results[0]["ok"] is True


def test_main_dry_run_writes_output_json(tmp_path):
    preview = tmp_path / "preview.json"
    preview.write_text(json.dumps(_preview_payload()), encoding="utf-8")
    out = tmp_path / "submit.json"

    exit_code = submit_tw_stock_paper_orders.main(["--preview-json", str(preview), "--output-json", str(out)])

    assert exit_code == 0
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["dry_run"] is True
    assert payload["payloads"][0]["symbol"] == "2317"


def test_main_submit_requires_agent_token(tmp_path):
    preview = tmp_path / "preview.json"
    preview.write_text(json.dumps(_preview_payload()), encoding="utf-8")

    exit_code = submit_tw_stock_paper_orders.main(["--preview-json", str(preview), "--submit"])

    assert exit_code == 2
