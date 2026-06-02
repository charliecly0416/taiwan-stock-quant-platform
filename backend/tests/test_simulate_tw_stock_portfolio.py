"""Offline tests for TWStock portfolio simulator."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

from scripts.archive_tw_stock_daily import parse_finmind_rows


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "simulate_tw_stock_portfolio.py"
SPEC = importlib.util.spec_from_file_location("simulate_tw_stock_portfolio", SCRIPT_PATH)
simulate_tw_stock_portfolio = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules["simulate_tw_stock_portfolio"] = simulate_tw_stock_portfolio
SPEC.loader.exec_module(simulate_tw_stock_portfolio)


def _rows(symbol="2330", closes=None, money=1_000_000_000):
    closes = closes or [100, 102, 104, 106, 108, 110]
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
    return parse_finmind_rows(rows, symbol=symbol)


def test_load_symbols_reads_universe_json_and_cli_symbols(tmp_path):
    path = tmp_path / "universe.json"
    path.write_text(json.dumps({"symbol_list": ["TWStock:2330", "TWStock:2317"]}), encoding="utf-8")

    symbols = simulate_tw_stock_portfolio.load_symbols(str(path), ["2454"])

    assert symbols == ["2454", "2330", "2317"]


def test_rank_records_for_date_uses_existing_daily_records():
    records = {
        "2330": _rows("2330", closes=[100, 102, 104, 110], money=2_000_000_000),
        "2317": _rows("2317", closes=[100, 99, 98, 97], money=1_000_000_000),
    }

    ranking = simulate_tw_stock_portfolio.rank_records_for_date(
        records,
        as_of="2026-05-04",
        lookback_days=10,
        momentum_window=2,
        volatility_window=2,
        min_bars=4,
        weights={"momentum": 0.8, "low_volatility": 0.0, "liquidity": 0.2},
    )

    assert ranking["eligible_count"] == 2
    assert ranking["rankings"][0] == "TWStock:2330"
    assert ranking["items"][0]["rank"] == 1




def test_price_limit_flags_detect_limit_up_and_down():
    closes = {
        "2330": {"2026-05-01": 100.0, "2026-05-02": 110.0},
        "2317": {"2026-05-01": 100.0, "2026-05-02": 90.0},
        "2454": {"2026-05-01": 100.0, "2026-05-02": 105.0},
    }

    flags = simulate_tw_stock_portfolio._price_limit_flags(
        symbols=["2330", "2317", "2454"],
        closes=closes,
        previous_date="2026-05-01",
        current_date="2026-05-02",
        limit_pct=0.10,
    )

    assert flags == {"2330": "limit_up", "2317": "limit_down"}


def test_apply_price_limit_to_weights_blocks_impossible_trades():
    adjusted, blocked_buys, blocked_sells = simulate_tw_stock_portfolio._apply_price_limit_to_weights(
        current_weights={"2330": 0.2, "2317": 0.3},
        target_weights={"2330": 0.5, "2317": 0.0, "2454": 0.2},
        limit_flags={"2330": "limit_up", "2317": "limit_down"},
    )

    assert adjusted == {"2330": 0.2, "2317": 0.3, "2454": 0.2}
    assert blocked_buys == ["2330"]
    assert blocked_sells == ["2317"]

def test_rebalance_whole_lots_rounds_to_lot_size_and_splits_costs():
    result = simulate_tw_stock_portfolio._rebalance_whole_lots(
        current_shares={"2330": 1000},
        target_weights={"2330": 0.3, "2317": 0.3},
        prices={"2330": 100.0, "2317": 50.0},
        equity_value=1_000_000.0,
        lot_size=1000,
        commission_rate=0.001425,
        sell_tax_rate=0.003,
    )

    assert result.shares == {"2317": 6000, "2330": 3000}
    assert result.weights == {"2330": 0.3, "2317": 0.3}
    assert result.buy_value == 500_000.0
    assert result.sell_value == 0.0
    assert result.buy_commission == 712.5
    assert result.sell_commission == 0.0
    assert result.sell_tax == 0.0
    assert result.cost_weight == 0.0007125
    assert result.cash_weight == 0.3992875


def test_rebalance_whole_lots_records_sell_tax_when_position_is_reduced():
    result = simulate_tw_stock_portfolio._rebalance_whole_lots(
        current_shares={"2330": 3000},
        target_weights={"2330": 0.1},
        prices={"2330": 100.0},
        equity_value=1_000_000.0,
        lot_size=1000,
        commission_rate=0.001425,
        sell_tax_rate=0.003,
    )

    assert result.shares == {"2330": 1000}
    assert result.sell_value == 200_000.0
    assert result.sell_commission == 285.0
    assert result.sell_tax == 600.0
    assert result.cost_weight == 0.000885


def test_rebalance_whole_lots_respects_price_limit_blocks():
    result = simulate_tw_stock_portfolio._rebalance_whole_lots(
        current_shares={"2330": 1000, "2317": 3000},
        target_weights={"2330": 0.5, "2317": 0.0, "2454": 0.2},
        prices={"2330": 100.0, "2317": 50.0, "2454": 200.0},
        equity_value=1_000_000.0,
        lot_size=1000,
        commission_rate=0.0,
        sell_tax_rate=0.0,
        limit_flags={"2330": "limit_up", "2317": "limit_down"},
    )

    assert result.shares == {"2317": 3000, "2330": 1000, "2454": 1000}
    assert result.blocked_buys == ["2330"]
    assert result.blocked_sells == ["2317"]
    assert result.buy_value == 200_000.0
    assert result.sell_value == 0.0

def test_simulate_portfolio_generates_equity_curve_and_rebalance_events(monkeypatch):
    def fake_fetch(symbol, start, end):
        if symbol == "2330":
            return _rows(symbol, closes=[100, 102, 104, 106, 108, 110], money=2_000_000_000)
        return _rows(symbol, closes=[100, 99, 98, 97, 96, 95], money=1_000_000_000)

    monkeypatch.setattr(simulate_tw_stock_portfolio, "fetch_symbol_records", fake_fetch)

    report = simulate_tw_stock_portfolio.simulate_portfolio(
        symbols=["2330", "2317"],
        start="2026-05-01",
        end="2026-05-06",
        rebalance_frequency="monthly",
        lookback_days=10,
        momentum_window=2,
        volatility_window=2,
        min_bars=3,
        top_n=1,
        transaction_cost=0.0,
    )

    assert report["metrics"]["rebalance_count"] == 1
    assert report["rebalance_events"][0]["selected"] == ["2330"]
    assert len(report["equity_curve"]) == 6
    assert report["metrics"]["final_equity"] > 1.0


def test_simulate_portfolio_reports_insufficient_dates(monkeypatch):
    monkeypatch.setattr(simulate_tw_stock_portfolio, "fetch_symbol_records", lambda symbol, start, end: _rows(symbol, closes=[100]))

    report = simulate_tw_stock_portfolio.simulate_portfolio(symbols=["2330"], start="2026-05-01", end="2026-05-01")

    assert report["error"] == "insufficient_trading_dates"


def test_simulate_portfolio_enforces_lot_size_when_requested(monkeypatch):
    def fake_fetch(symbol, start, end):
        if symbol == "2330":
            return _rows(symbol, closes=[100, 102, 104, 106, 108, 110], money=2_000_000_000)
        return _rows(symbol, closes=[50, 51, 52, 53, 54, 55], money=1_000_000_000)

    monkeypatch.setattr(simulate_tw_stock_portfolio, "fetch_symbol_records", fake_fetch)

    report = simulate_tw_stock_portfolio.simulate_portfolio(
        symbols=["2330", "2317"],
        start="2026-05-01",
        end="2026-05-06",
        rebalance_frequency="monthly",
        lookback_days=10,
        momentum_window=2,
        volatility_window=2,
        min_bars=3,
        top_n=2,
        cash_weight=0.1,
        max_weight=0.5,
        enforce_lot_size=True,
        initial_capital=1_000_000,
        lot_size=1000,
        commission_rate=0.001425,
        sell_tax_rate=0.003,
    )

    event = report["rebalance_events"][0]
    assert report["assumptions"]["lot_size_enforced"] is True
    assert event["shares"]
    assert all(qty % 1000 == 0 for qty in event["shares"].values())
    assert event["buy_commission"] > 0
    assert event["cash_weight"] >= 0



def test_simulate_portfolio_records_price_limit_blocks(monkeypatch):
    def fake_fetch(symbol, start, end):
        if symbol == "2330":
            return _rows(symbol, closes=[100, 110, 121, 133.1, 146.41, 161.051], money=2_000_000_000)
        return _rows(symbol, closes=[100, 100, 100, 100, 100, 100], money=1_000_000_000)

    monkeypatch.setattr(simulate_tw_stock_portfolio, "fetch_symbol_records", fake_fetch)

    report = simulate_tw_stock_portfolio.simulate_portfolio(
        symbols=["2330", "2317"],
        start="2026-05-01",
        end="2026-05-06",
        rebalance_frequency="daily",
        lookback_days=10,
        momentum_window=1,
        volatility_window=2,
        min_bars=3,
        top_n=1,
        cash_weight=0.0,
        max_weight=0.5,
        transaction_cost=0.0,
        enforce_price_limit=True,
        price_limit_pct=0.10,
    )

    assert report["assumptions"]["price_limit_enforced"] is True
    events = report["rebalance_events"]
    assert any("2330" in event["blocked_buys"] for event in events)

def test_main_writes_output_json(monkeypatch, tmp_path):
    captured = {}

    def fake_simulate(**kwargs):
        captured.update(kwargs)
        return {"metrics": {"final_equity": 1.0}, "equity_curve": [{"date": "2026-05-01", "equity": 1.0}]}

    monkeypatch.setattr(simulate_tw_stock_portfolio, "simulate_portfolio", fake_simulate)
    out = tmp_path / "simulation.json"

    exit_code = simulate_tw_stock_portfolio.main([
        "--symbol",
        "2330",
        "--start",
        "2026-05-01",
        "--end",
        "2026-05-02",
        "--enforce-lot-size",
        "--initial-capital",
        "2000000",
        "--lot-size",
        "1000",
        "--commission-rate",
        "0.001",
        "--sell-tax-rate",
        "0.002",
        "--enforce-price-limit",
        "--price-limit-pct",
        "0.09",
        "--output-json",
        str(out),
    ])

    assert exit_code == 0
    assert captured["enforce_lot_size"] is True
    assert captured["initial_capital"] == 2_000_000
    assert captured["lot_size"] == 1000
    assert captured["commission_rate"] == 0.001
    assert captured["sell_tax_rate"] == 0.002
    assert captured["enforce_price_limit"] is True
    assert captured["price_limit_pct"] == 0.09
    assert json.loads(out.read_text(encoding="utf-8"))["metrics"]["final_equity"] == 1.0
