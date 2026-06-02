"""Offline tests for TWStock paper order preview."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "preview_tw_stock_paper_orders.py"
SPEC = importlib.util.spec_from_file_location("preview_tw_stock_paper_orders", SCRIPT_PATH)
preview_tw_stock_paper_orders = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules["preview_tw_stock_paper_orders"] = preview_tw_stock_paper_orders
SPEC.loader.exec_module(preview_tw_stock_paper_orders)


def test_ibkr_tw_contract_uses_twse_twd():
    contract = preview_tw_stock_paper_orders.ibkr_tw_contract("TWStock:2330")

    assert contract == {
        "secType": "STK",
        "symbol": "2330",
        "exchange": "TWSE",
        "currency": "TWD",
        "market": "TWStock",
    }


def test_parse_target_weights_reads_rebalance_plan():
    payload = {
        "target_positions": [
            {"symbol": "2330", "target_weight": 0.3},
            {"config_symbol": "TWStock:2317", "target_weight": 0.2},
        ]
    }

    assert preview_tw_stock_paper_orders.parse_target_weights(payload) == {"2330": 0.3, "2317": 0.2}


def test_parse_positions_accepts_mapping_and_list():
    assert preview_tw_stock_paper_orders.parse_positions({"positions": {"TWStock:2330": 2000}}) == {"2330": 2000}
    assert preview_tw_stock_paper_orders.parse_positions({"positions": [{"symbol": "2317", "shares": 3000}]}) == {"2317": 3000}


def test_build_order_previews_generates_limit_orders_and_lot_quantities():
    report = preview_tw_stock_paper_orders.build_order_previews(
        target_weights={"2330": 0.3, "2317": 0.2},
        current_positions={"2330": 1000},
        prices={"2330": 100.0, "2317": 50.0},
        portfolio_value=1_000_000,
        lot_size=1000,
        limit_buffer=0.01,
    )

    assert report["paper_only"] is True
    assert report["order_count"] == 2
    orders = {item["symbol"]: item for item in report["orders"]}
    assert orders["2330"]["side"] == "buy"
    assert orders["2330"]["qty"] == 2000
    assert orders["2330"]["limit_price"] == 101.0
    assert orders["2330"]["contract"]["currency"] == "TWD"
    assert orders["2317"]["qty"] == 4000



def test_build_order_previews_warns_when_target_is_below_one_lot():
    report = preview_tw_stock_paper_orders.build_order_previews(
        target_weights={"2330": 0.3},
        current_positions={},
        prices={"2330": 2_000.0},
        portfolio_value=5_000_000,
        lot_size=1000,
    )

    assert report["order_count"] == 0
    assert report["warnings"] == ["target_below_one_lot:2330"]

def test_build_order_previews_blocks_oversized_orders():
    report = preview_tw_stock_paper_orders.build_order_previews(
        target_weights={"2330": 0.8},
        current_positions={},
        prices={"2330": 100.0},
        portfolio_value=1_000_000,
        max_order_value=100_000,
    )

    assert report["blocked_count"] == 1
    assert report["orders"][0]["status"] == "blocked"
    assert "max_order_value_exceeded" in report["orders"][0]["reasons"]


def test_build_order_previews_blocks_total_buy_cap():
    report = preview_tw_stock_paper_orders.build_order_previews(
        target_weights={"2330": 0.3, "2317": 0.3},
        current_positions={},
        prices={"2330": 100.0, "2317": 50.0},
        portfolio_value=1_000_000,
        max_total_buy_value=400_000,
    )

    assert "max_total_buy_value_exceeded" in report["warnings"]
    assert report["blocked_count"] == 2


def test_main_writes_output_json_without_fetch(monkeypatch, tmp_path):
    monkeypatch.setattr(
        preview_tw_stock_paper_orders,
        "resolve_prices",
        lambda symbols, price_map, as_of: {"2330": 100.0},
    )
    plan = tmp_path / "plan.json"
    plan.write_text(json.dumps({"target_positions": [{"symbol": "2330", "target_weight": 0.3}]}), encoding="utf-8")
    out = tmp_path / "orders.json"

    exit_code = preview_tw_stock_paper_orders.main([
        "--plan-json",
        str(plan),
        "--portfolio-value",
        "1000000",
        "--output-json",
        str(out),
    ])

    assert exit_code == 0
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["orders"][0]["symbol"] == "2330"
    assert payload["orders"][0]["order_type"] == "limit"

def test_build_order_previews_generates_sell_when_target_below_current_position():
    report = preview_tw_stock_paper_orders.build_order_previews(
        target_weights={"2317": 0.2},
        current_positions={"2317": 6000},
        prices={"2317": 250.0},
        portfolio_value=5_000_000,
        lot_size=1000,
        limit_buffer=0.005,
    )

    assert report["order_count"] == 1
    order = report["orders"][0]
    assert order["side"] == "sell"
    assert order["qty"] == 2000
    assert order["limit_price"] == 248.75
    assert order["estimated_notional"] == 500000.0
    assert order["current_qty"] == 6000

