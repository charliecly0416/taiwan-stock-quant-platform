"""Offline tests for TWStock universe ranking script."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

from scripts.archive_tw_stock_daily import parse_finmind_rows


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "rank_tw_stock_universe.py"
SPEC = importlib.util.spec_from_file_location("rank_tw_stock_universe", SCRIPT_PATH)
rank_tw_stock_universe = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules["rank_tw_stock_universe"] = rank_tw_stock_universe
SPEC.loader.exec_module(rank_tw_stock_universe)


def _rows(symbol="2330", closes=None, money=1_000_000_000):
    closes = closes or [100, 101, 102, 104, 108]
    rows = []
    for idx, close in enumerate(closes, start=1):
        rows.append({
            "date": f"2026-05-{idx:02d}",
            "stock_id": symbol,
            "Trading_Volume": 1_000_000,
            "Trading_money": money,
            "open": close - 1,
            "max": close + 1,
            "min": close - 2,
            "close": close,
            "Trading_turnover": 1,
            "spread": 1,
        })
    return rows


def test_parse_config_symbols_accepts_twstock_prefixes():
    symbols = rank_tw_stock_universe.parse_config_symbols(["TWStock:2330,2317", "2454.TW"])

    assert symbols == ["2330", "2317", "2454"]


def test_load_symbols_from_universe_json_reads_symbol_list(tmp_path):
    path = tmp_path / "universe.json"
    path.write_text(json.dumps({"symbol_list": ["TWStock:2330", "TWStock:2317"]}), encoding="utf-8")

    assert rank_tw_stock_universe.load_symbols_from_universe_json(str(path)) == ["2330", "2317"]


def test_compute_raw_metrics_calculates_momentum_volatility_and_liquidity():
    records = parse_finmind_rows(_rows(closes=[100, 105, 110, 120]), symbol="2330")

    metrics = rank_tw_stock_universe.compute_raw_metrics(records, momentum_window=2, volatility_window=2)

    assert metrics["bars"] == 4
    assert metrics["last_trade_date"] == "2026-05-04"
    assert metrics["last_close"] == 120.0
    assert metrics["momentum"] == round(120 / 105 - 1, 8)
    assert metrics["volatility"] is not None
    assert metrics["avg_trading_money"] == 1_000_000_000
    assert metrics["reasons"] == []


def test_percentile_scores_ordering():
    scores = rank_tw_stock_universe._percentile_scores({"a": 10, "b": 20, "c": 30})
    reverse_scores = rank_tw_stock_universe._percentile_scores({"a": 10, "b": 20, "c": 30}, reverse=True)

    assert scores == {"a": 1.0, "b": 0.5, "c": 0.0}
    assert reverse_scores == {"c": 1.0, "b": 0.5, "a": 0.0}


def test_rank_symbols_outputs_ranked_config_symbols(monkeypatch):
    def fake_fetch(symbol, start, end):
        if symbol == "2330":
            return parse_finmind_rows(_rows(symbol, closes=[100, 101, 102, 110], money=2_000_000_000), symbol=symbol)
        return parse_finmind_rows(_rows(symbol, closes=[100, 99, 98, 97], money=1_000_000_000), symbol=symbol)

    monkeypatch.setattr(rank_tw_stock_universe, "fetch_symbol_records", fake_fetch)

    report = rank_tw_stock_universe.rank_symbols(
        symbols=["TWStock:2330", "TWStock:2317"],
        start="2026-05-01",
        end="2026-05-04",
        momentum_window=2,
        volatility_window=2,
        min_bars=4,
        weights={"momentum": 0.8, "low_volatility": 0.0, "liquidity": 0.2},
    )

    assert report["count"] == 2
    assert report["eligible_count"] == 2
    assert report["rankings"][0] == "TWStock:2330"
    assert report["items"][0]["rank"] == 1
    assert report["items"][0]["symbol"] == "2330"
    assert report["items"][0]["composite_score"] > report["items"][1]["composite_score"]


def test_rank_symbols_marks_insufficient_data(monkeypatch):
    monkeypatch.setattr(
        rank_tw_stock_universe,
        "fetch_symbol_records",
        lambda symbol, start, end: parse_finmind_rows(_rows(symbol, closes=[100, 101]), symbol=symbol),
    )

    report = rank_tw_stock_universe.rank_symbols(
        symbols=["2330"],
        start="2026-05-01",
        end="2026-05-02",
        momentum_window=2,
        volatility_window=2,
        min_bars=4,
    )

    assert report["eligible_count"] == 0
    assert "below_min_bars" in report["items"][0]["reasons"]


def test_main_writes_output_json(monkeypatch, tmp_path):
    monkeypatch.setattr(
        rank_tw_stock_universe,
        "rank_symbols",
        lambda **kwargs: {"eligible_count": 1, "rankings": ["TWStock:2330"], "items": []},
    )
    out = tmp_path / "ranking.json"

    exit_code = rank_tw_stock_universe.main([
        "--symbol",
        "2330",
        "--start",
        "2026-05-01",
        "--end",
        "2026-05-22",
        "--output-json",
        str(out),
    ])

    assert exit_code == 0
    assert json.loads(out.read_text(encoding="utf-8"))["rankings"] == ["TWStock:2330"]
