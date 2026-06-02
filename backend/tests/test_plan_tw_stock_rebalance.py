"""Offline tests for TWStock rebalance planner."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "plan_tw_stock_rebalance.py"
SPEC = importlib.util.spec_from_file_location("plan_tw_stock_rebalance", SCRIPT_PATH)
plan_tw_stock_rebalance = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules["plan_tw_stock_rebalance"] = plan_tw_stock_rebalance
SPEC.loader.exec_module(plan_tw_stock_rebalance)


def _ranking_payload():
    return {
        "items": [
            {"symbol": "2454", "config_symbol": "TWStock:2454", "rank": 1, "composite_score": 0.8, "reasons": []},
            {"symbol": "2317", "config_symbol": "TWStock:2317", "rank": 2, "composite_score": 0.7, "reasons": []},
            {"symbol": "2330", "config_symbol": "TWStock:2330", "rank": 3, "composite_score": 0.6, "reasons": []},
            {"symbol": "9999", "config_symbol": "TWStock:9999", "rank": 4, "composite_score": 0.1, "reasons": ["below_min_bars"]},
        ]
    }


def test_parse_ranked_items_skips_rejected_items_and_sorts_by_rank():
    items = plan_tw_stock_rebalance.parse_ranked_items(_ranking_payload())

    assert [item["config_symbol"] for item in items] == ["TWStock:2454", "TWStock:2317", "TWStock:2330"]
    assert [item["score"] for item in items] == [0.8, 0.7, 0.6]


def test_parse_ranked_items_can_use_rankings_fallback():
    items = plan_tw_stock_rebalance.parse_ranked_items({"rankings": ["TWStock:2330", "2317"]})

    assert items == [
        {"config_symbol": "TWStock:2330", "symbol": "2330", "rank": 1, "score": 0.0},
        {"config_symbol": "TWStock:2317", "symbol": "2317", "rank": 2, "score": 0.0},
    ]


def test_build_rebalance_plan_equal_weights_top_n():
    ranked = plan_tw_stock_rebalance.parse_ranked_items(_ranking_payload())

    plan = plan_tw_stock_rebalance.build_rebalance_plan(ranked, top_n=2, max_weight=0.6, cash_weight=0.0, as_of="2026-05-22")

    assert plan["selected_count"] == 2
    assert plan["allocated_weight"] == 1.0
    assert plan["residual_cash_weight"] == 0.0
    assert [p["config_symbol"] for p in plan["target_positions"]] == ["TWStock:2454", "TWStock:2317"]
    assert [p["target_weight"] for p in plan["target_positions"]] == [0.5, 0.5]
    assert plan["warnings"] == []


def test_build_rebalance_plan_respects_cash_and_max_weight():
    ranked = plan_tw_stock_rebalance.parse_ranked_items(_ranking_payload())

    plan = plan_tw_stock_rebalance.build_rebalance_plan(ranked, top_n=3, max_weight=0.25, cash_weight=0.1)

    assert [p["target_weight"] for p in plan["target_positions"]] == [0.25, 0.25, 0.25]
    assert plan["allocated_weight"] == 0.75
    assert plan["residual_cash_weight"] == 0.25
    assert "max_weight_leaves_extra_cash" in plan["warnings"]


def test_build_rebalance_plan_empty_input_returns_warning():
    plan = plan_tw_stock_rebalance.build_rebalance_plan([], top_n=3)

    assert plan["selected_count"] == 0
    assert plan["target_positions"] == []
    assert plan["warnings"] == ["no_ranked_symbols"]


def test_main_writes_output_json(tmp_path):
    ranking = tmp_path / "ranking.json"
    ranking.write_text(json.dumps(_ranking_payload()), encoding="utf-8")
    out = tmp_path / "plan.json"

    exit_code = plan_tw_stock_rebalance.main([
        "--ranking-json",
        str(ranking),
        "--top-n",
        "2",
        "--as-of",
        "2026-05-22",
        "--output-json",
        str(out),
    ])

    assert exit_code == 0
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["selected_count"] == 2
    assert payload["target_positions"][0]["config_symbol"] == "TWStock:2454"
