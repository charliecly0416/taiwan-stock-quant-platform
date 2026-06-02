"""Offline tests for TWStock universe builder."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

from scripts.archive_tw_stock_daily import parse_finmind_rows


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "build_tw_stock_universe.py"
SPEC = importlib.util.spec_from_file_location("build_tw_stock_universe", SCRIPT_PATH)
build_tw_stock_universe = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules["build_tw_stock_universe"] = build_tw_stock_universe
SPEC.loader.exec_module(build_tw_stock_universe)


def _rows(symbol="2330", trading_money=1_000_000_000, volume=10_000_000):
    return [
        {
            "date": "2026-05-20",
            "stock_id": symbol,
            "Trading_Volume": volume,
            "Trading_money": trading_money,
            "open": 100,
            "max": 105,
            "min": 99,
            "close": 104,
            "Trading_turnover": 1,
            "spread": 1,
        },
        {
            "date": "2026-05-21",
            "stock_id": symbol,
            "Trading_Volume": volume,
            "Trading_money": trading_money,
            "open": 104,
            "max": 108,
            "min": 103,
            "close": 107,
            "Trading_turnover": 1,
            "spread": 3,
        },
    ]


def test_parse_symbols_accepts_twstock_formats():
    symbols = build_tw_stock_universe.parse_symbols(["2330,TWSE:2317", "0050.TW"])

    assert symbols == ["2330", "2317", "0050"]


def test_normalize_symbol_metadata_infers_instrument_type_and_dedupes():
    rows = [
        {"symbol": "2330", "name": "台積電", "exchange": "TWSE", "instrument_type": "stock"},
        {"symbol": "2330", "name": "dup"},
        {"symbol": "0050", "name": "元大台灣50"},
    ]

    normalized = build_tw_stock_universe.normalize_symbol_metadata(rows)

    assert normalized == [
        {"symbol": "0050", "name": "元大台灣50", "exchange": "TWSE", "instrument_type": "etf"},
        {"symbol": "2330", "name": "台積電", "exchange": "TWSE", "instrument_type": "stock"},
    ]


def test_load_candidate_symbols_filters_etf(monkeypatch):
    monkeypatch.setattr(
        build_tw_stock_universe,
        "get_all_symbols",
        lambda market: [
            {"symbol": "2330", "name": "台積電", "instrument_type": "stock"},
            {"symbol": "0050", "name": "元大台灣50", "instrument_type": "etf"},
        ],
    )

    assert [item["symbol"] for item in build_tw_stock_universe.load_candidate_symbols([], include_etf=False)] == ["2330"]
    assert [item["symbol"] for item in build_tw_stock_universe.load_candidate_symbols([], include_etf=True)] == ["0050", "2330"]


def test_evaluate_candidate_passes_liquidity_filters(monkeypatch):
    monkeypatch.setattr(build_tw_stock_universe, "fetch_finmind_rows", lambda symbol, start, end: _rows(symbol))

    candidate = build_tw_stock_universe.evaluate_candidate(
        {"symbol": "2330", "name": "台積電", "exchange": "TWSE", "instrument_type": "stock"},
        start="2026-05-20",
        end="2026-05-21",
        min_bars=2,
        min_avg_volume=1_000_000,
        min_avg_trading_money=100_000_000,
    )

    assert candidate.passes is True
    assert candidate.config_symbol == "TWStock:2330"
    assert candidate.avg_volume == 10_000_000
    assert candidate.avg_trading_money == 1_000_000_000
    assert candidate.last_trade_date == "2026-05-21"
    assert candidate.rank_score == 1_000_000_000


def test_evaluate_candidate_rejects_low_liquidity(monkeypatch):
    monkeypatch.setattr(build_tw_stock_universe, "fetch_finmind_rows", lambda symbol, start, end: _rows(symbol, trading_money=1, volume=1))

    candidate = build_tw_stock_universe.evaluate_candidate(
        {"symbol": "2330", "name": "台積電", "exchange": "TWSE", "instrument_type": "stock"},
        start="2026-05-20",
        end="2026-05-21",
        min_bars=2,
        min_avg_volume=1_000_000,
        min_avg_trading_money=100_000_000,
    )

    assert candidate.passes is False
    assert candidate.reasons == ["low_avg_volume", "low_avg_trading_money"]


def test_build_universe_ranks_by_average_trading_money(monkeypatch):
    monkeypatch.setattr(
        build_tw_stock_universe,
        "load_candidate_symbols",
        lambda symbols, include_etf=False, limit_candidates=0: [
            {"symbol": "2330", "name": "台積電", "exchange": "TWSE", "instrument_type": "stock"},
            {"symbol": "2317", "name": "鴻海", "exchange": "TWSE", "instrument_type": "stock"},
        ],
    )

    def fake_fetch(symbol, start, end):
        money = 2_000_000_000 if symbol == "2317" else 1_000_000_000
        return _rows(symbol, trading_money=money, volume=10_000_000)

    monkeypatch.setattr(build_tw_stock_universe, "fetch_finmind_rows", fake_fetch)

    report = build_tw_stock_universe.build_universe(
        symbols=[],
        start="2026-05-20",
        end="2026-05-21",
        min_bars=2,
        min_avg_volume=1,
        min_avg_trading_money=1,
        max_universe=1,
    )

    assert report["candidate_count"] == 2
    assert report["passed_count"] == 2
    assert report["selected_count"] == 1
    assert report["symbol_list"] == ["TWStock:2317"]


def test_main_writes_output_json(monkeypatch, tmp_path):
    monkeypatch.setattr(
        build_tw_stock_universe,
        "build_universe",
        lambda **kwargs: {"selected_count": 1, "symbol_list": ["TWStock:2330"], "selected": [], "rejected": []},
    )
    out = tmp_path / "universe.json"

    exit_code = build_tw_stock_universe.main(["--symbol", "2330", "--output-json", str(out)])

    assert exit_code == 0
    assert json.loads(out.read_text(encoding="utf-8"))["symbol_list"] == ["TWStock:2330"]

def test_build_monitor_config_payload_is_disabled_and_limited():
    symbols = [str(2300 + idx) for idx in range(60)]

    payload = build_tw_stock_universe.build_monitor_config_payload(
        symbols,
        name="phase7c",
        limit_bars=999,
        refresh_interval_sec=-1,
        score_change_threshold=999,
        enabled=False,
    )

    assert payload["name"] == "phase7c"
    assert len(payload["symbols"]) == 50
    assert payload["limit_bars"] == 500
    assert payload["refresh_interval_sec"] == 0
    assert payload["score_change_threshold"] == 100.0
    assert payload["enabled"] is False
    assert "no automatic trading" in payload["notes"]


def test_build_universe_includes_research_only_monitor_config(monkeypatch):
    monkeypatch.setattr(
        build_tw_stock_universe,
        "load_candidate_symbols",
        lambda symbols, include_etf=False, limit_candidates=0: [
            {"symbol": "2330", "name": "台積電", "exchange": "TWSE", "instrument_type": "stock"},
        ],
    )
    monkeypatch.setattr(build_tw_stock_universe, "fetch_finmind_rows", lambda symbol, start, end: _rows(symbol))

    report = build_tw_stock_universe.build_universe(
        symbols=[],
        start="2026-05-20",
        end="2026-05-21",
        min_bars=2,
        min_avg_volume=1,
        min_avg_trading_money=1,
        max_universe=10,
    )

    assert report["monitor_config"]["symbols"] == ["2330"]
    assert report["monitor_config"]["enabled"] is False
    assert report["manual_review"]["required"] is True
    assert "preflight_tw_stock_monitor_config.py" in report["manual_review"]["quality_gate_command"]
    assert "import_tw_stock_monitor_config.py" in report["manual_review"]["dry_run_import_command"]
    assert report["manual_review"]["orders_enabled"] is False
    assert report["manual_review"]["connects_to_broker"] is False
    assert report["manual_review"]["db_written_by_universe_builder"] is False
    assert report["trading"]["orders_enabled"] is False


def test_build_manual_review_payload_uses_monitor_config_path():
    payload = build_tw_stock_universe.build_manual_review_payload(monitor_config_path="/tmp/review.json")

    assert payload["steps"] == [
        "review_universe_selection",
        "run_quality_gate_preflight",
        "run_import_dry_run",
        "apply_only_after_manual_approval",
    ]
    assert "--input-json /tmp/review.json" in payload["quality_gate_command"]
    assert "--fail-on-quality-gate" in payload["quality_gate_command"]
    assert "--dry-run" in payload["dry_run_import_command"]
    assert "--apply" in payload["apply_command_template"]
    assert payload["orders_enabled"] is False


def test_main_writes_monitor_config_json(monkeypatch, tmp_path):
    monkeypatch.setattr(
        build_tw_stock_universe,
        "build_universe",
        lambda **kwargs: {"selected_count": 1, "symbols": ["2330", "0050"], "symbol_list": ["TWStock:2330", "TWStock:0050"], "selected": [], "rejected": []},
    )
    out = tmp_path / "monitor.json"

    exit_code = build_tw_stock_universe.main(["--symbol", "2330", "--monitor-name", "phase7c", "--monitor-config-json", str(out)])

    assert exit_code == 0
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["name"] == "phase7c"
    assert payload["symbols"] == ["2330", "0050"]
    assert payload["enabled"] is False
