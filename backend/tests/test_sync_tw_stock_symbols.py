"""Tests for TWSE symbol sync script parsing and DB upsert behavior."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "sync_tw_stock_symbols.py"
SPEC = importlib.util.spec_from_file_location("sync_tw_stock_symbols", SCRIPT_PATH)
sync_tw_stock_symbols = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules["sync_tw_stock_symbols"] = sync_tw_stock_symbols
SPEC.loader.exec_module(sync_tw_stock_symbols)


def test_parse_twse_stock_day_all_keeps_stocks_and_etfs_only_by_default():
    rows = [
        {"Code": "2330", "Name": "台積電", "TradeVolume": "26,823,133"},
        {"Code": "0050", "Name": "元大台灣50", "TradeVolume": "64,288,280"},
        {"Code": "020001", "Name": "富邦特選高股息30ETN", "TradeVolume": "100"},
        {"Code": "030001", "Name": "測試權證", "TradeVolume": "200"},
        {"Code": "BAD", "Name": "bad", "TradeVolume": "300"},
        {"Code": "", "Name": "empty", "TradeVolume": "400"},
    ]

    records = sync_tw_stock_symbols.parse_twse_stock_day_all(rows)

    assert [(item.symbol, item.name, item.instrument_type) for item in records] == [
        ("2330", "台積電", "stock"),
        ("0050", "元大台灣50", "etf"),
    ]
    assert records[0].market == "TWStock"
    assert records[0].exchange == "TWSE"
    assert records[0].currency == "TWD"
    assert records[0].lot_size == 1000
    assert records[0].sort_order == 26823133
    assert '"source":"twse_default"' in records[0].price_tick_json


def test_parse_twse_stock_day_all_can_include_non_stock_etf_when_requested():
    rows = [
        {"Code": "030001", "Name": "測試權證", "TradeVolume": "200"},
        {"Code": "020001", "Name": "富邦特選高股息30ETN", "TradeVolume": "100"},
        {"Code": "999999", "Name": "未知", "TradeVolume": "--"},
    ]

    records = sync_tw_stock_symbols.parse_twse_stock_day_all(rows, include_non_stock_etf=True)

    assert [(item.symbol, item.instrument_type, item.sort_order) for item in records] == [
        ("020001", "etn", 100),
        ("030001", "warrant", 200),
        ("999999", "unknown", 0),
    ]


def test_classify_tw_instrument_detects_common_twse_stock_and_etf_codes():
    assert sync_tw_stock_symbols.classify_tw_instrument("2330", "台積電") == "stock"
    assert sync_tw_stock_symbols.classify_tw_instrument("0050", "元大台灣50") == "etf"
    assert sync_tw_stock_symbols.classify_tw_instrument("00878", "國泰永續高股息") == "etf"
    assert sync_tw_stock_symbols.classify_tw_instrument("020001", "富邦特選高股息30ETN") == "etn"
    assert sync_tw_stock_symbols.classify_tw_instrument("030001", "測試權證") == "warrant"


def test_summarize_returns_counts_and_small_sample():
    records = sync_tw_stock_symbols.parse_twse_stock_day_all(
        [
            {"Code": "2330", "Name": "台積電", "TradeVolume": "10"},
            {"Code": "0050", "Name": "元大台灣50", "TradeVolume": "20"},
        ]
    )

    summary = sync_tw_stock_symbols.summarize(records)

    assert summary["count"] == 2
    assert summary["by_type"] == {"stock": 1, "etf": 1}
    assert summary["first_symbols"] == ["2330", "0050"]
    assert summary["sample"][0] == {
        "symbol": "2330",
        "name": "台積電",
        "exchange": "TWSE",
        "instrument_type": "stock",
        "lot_size": 1000,
    }


def test_upsert_records_uses_idempotent_conflict_update(monkeypatch):
    executed = []

    class FakeCursor:
        def execute(self, sql, params):
            executed.append((sql, params))

        def close(self):
            executed.append(("close", None))

    class FakeDb:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def cursor(self):
            return FakeCursor()

        def commit(self):
            executed.append(("commit", None))

    def fake_get_db_connection():
        return FakeDb()

    class FakeDbModule:
        get_db_connection = staticmethod(fake_get_db_connection)

    monkeypatch.setitem(__import__("sys").modules, "app.utils.db", FakeDbModule)

    records = sync_tw_stock_symbols.parse_twse_stock_day_all(
        [{"Code": "2330", "Name": "台積電", "TradeVolume": "26,823,133"}]
    )
    count = sync_tw_stock_symbols.upsert_records(records)

    assert count == 1
    sql, params = executed[0]
    assert "INSERT INTO qd_market_symbols" in sql
    assert "ON CONFLICT (market, symbol) DO UPDATE SET" in sql
    assert "price_tick_json = CASE" in sql
    assert params[:5] == ("TWStock", "2330", "台積電", "TWSE", "TWD")
    assert params[8:10] == ("stock", 1000)
    assert executed[-2:] == [("commit", None), ("close", None)]
