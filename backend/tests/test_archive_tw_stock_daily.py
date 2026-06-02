"""Offline tests for TWStock daily archive script."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "archive_tw_stock_daily.py"
SPEC = importlib.util.spec_from_file_location("archive_tw_stock_daily", SCRIPT_PATH)
archive_tw_stock_daily = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules["archive_tw_stock_daily"] = archive_tw_stock_daily
SPEC.loader.exec_module(archive_tw_stock_daily)


def _rows():
    return [
        {
            "date": "2026-05-21",
            "stock_id": "2330",
            "Trading_Volume": "26,000,000",
            "Trading_money": "58,000,000,000",
            "open": 2200,
            "max": 2250,
            "min": 2190,
            "close": 2240,
            "spread": 20,
            "Trading_turnover": "30,000",
        },
        {
            "date": "2026-05-22",
            "stock_id": "2330",
            "Trading_Volume": 26823133,
            "Trading_money": 60100000000,
            "open": 2245,
            "max": 2260,
            "min": 2225,
            "close": 2255,
            "spread": 15,
            "Trading_turnover": 31000,
        },
    ]


def test_parse_finmind_rows_to_archive_records():
    records = archive_tw_stock_daily.parse_finmind_rows(_rows(), symbol="2330.TW")

    assert len(records) == 2
    first = records[0]
    assert first.symbol == "2330"
    assert first.exchange == "TWSE"
    assert first.instrument_type == "stock"
    assert first.trade_date == "2026-05-21"
    assert first.open == 2200.0
    assert first.high == 2250.0
    assert first.low == 2190.0
    assert first.close == 2240.0
    assert first.volume == 26000000
    assert first.trading_money == 58000000000.0
    assert first.trading_turnover == 30000
    assert first.spread == 20.0
    assert first.source == "finmind"
    assert first.official_checked == 0
    assert first.official_match == 0
    assert first.quality_flags == ""
    assert '"stock_id":"2330"' in first.raw_json


def test_parse_finmind_rows_marks_quality_flags_and_dedupes_dates():
    rows = [
        {"date": "2026-05-22", "open": 10, "max": 9, "min": 8, "close": 11, "Trading_Volume": 1},
        {"date": "2026-05-22", "open": 12, "max": 12, "min": 12, "close": 12, "Trading_Volume": 1},
        {"date": "bad", "open": 1, "max": 1, "min": 1, "close": 1, "Trading_Volume": -1},
    ]

    records = archive_tw_stock_daily.parse_finmind_rows(rows, symbol="0050")

    assert len(records) == 2
    assert records[0].symbol == "0050"
    assert records[0].instrument_type == "etf"
    assert "high_below_open_close" in records[0].quality_flags
    assert records[1].trade_date == "bad"
    assert "bad_trade_date" in records[1].quality_flags
    assert "negative_volume" in records[1].quality_flags


def test_summarize_archive_records():
    records = archive_tw_stock_daily.parse_finmind_rows(_rows(), symbol="2330")

    summary = archive_tw_stock_daily.summarize(records)

    assert summary["count"] == 2
    assert summary["symbols"] == ["2330"]
    assert summary["date_min"] == "2026-05-21"
    assert summary["date_max"] == "2026-05-22"
    assert summary["flagged_count"] == 0
    assert summary["sample"][0]["symbol"] == "2330"


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

    class FakeDbModule:
        get_db_connection = staticmethod(lambda: FakeDb())

    monkeypatch.setitem(sys.modules, "app.utils.db", FakeDbModule)
    records = archive_tw_stock_daily.parse_finmind_rows(_rows()[:1], symbol="2330")

    count = archive_tw_stock_daily.upsert_records(records)

    assert count == 1
    sql, params = executed[0]
    assert "INSERT INTO qd_tw_stock_daily_bars" in sql
    assert "ON CONFLICT (symbol, trade_date, source) DO UPDATE SET" in sql
    assert "?::jsonb" in sql
    assert params[:4] == ("2330", "TWSE", "stock", "2026-05-21")
    assert params[12:15] == ("finmind", 0, 0)
    assert executed[-2:] == [("commit", None), ("close", None)]
