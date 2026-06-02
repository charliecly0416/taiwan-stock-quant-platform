"""Offline tests for TWStock valuation archive script."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "archive_tw_stock_valuation.py"
SPEC = importlib.util.spec_from_file_location("archive_tw_stock_valuation", SCRIPT_PATH)
archive_tw_stock_valuation = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules["archive_tw_stock_valuation"] = archive_tw_stock_valuation
SPEC.loader.exec_module(archive_tw_stock_valuation)


def _rows():
    return [
        {"date": "2026-05-20", "stock_id": "2330", "dividend_yield": 1.01, "PER": 29.38, "PBR": 9.62},
        {"date": "2026-05-22", "stock_id": "2330", "dividend_yield": 0.98, "PER": 30.32, "PBR": 9.93},
    ]


def test_parse_finmind_rows_builds_valuation_records():
    records = archive_tw_stock_valuation.parse_finmind_rows(_rows(), symbol="2330.TW")

    assert len(records) == 2
    first = records[0]
    assert first.symbol == "2330"
    assert first.trade_date == "2026-05-20"
    assert first.pe == 29.38
    assert first.pb == 9.62
    assert first.dividend_yield == 1.01
    assert first.source == "finmind"
    assert first.quality_flags == ""
    assert '"stock_id":"2330"' in first.raw_json


def test_parse_finmind_rows_marks_quality_flags_and_dedupes():
    rows = [
        {"date": "bad", "stock_id": "2330", "dividend_yield": -1, "PER": "--", "PBR": "--"},
        {"date": "bad", "stock_id": "2330", "dividend_yield": 1, "PER": 1, "PBR": 1},
    ]

    records = archive_tw_stock_valuation.parse_finmind_rows(rows, symbol="2330")

    assert len(records) == 1
    assert "bad_trade_date" in records[0].quality_flags
    assert "negative_dividend_yield" in records[0].quality_flags


def test_summarize_valuation_records():
    records = archive_tw_stock_valuation.parse_finmind_rows(_rows(), symbol="2330")

    summary = archive_tw_stock_valuation.summarize(records)

    assert summary["count"] == 2
    assert summary["symbols"] == ["2330"]
    assert summary["date_min"] == "2026-05-20"
    assert summary["date_max"] == "2026-05-22"
    assert summary["flagged_count"] == 0


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
    records = archive_tw_stock_valuation.parse_finmind_rows(_rows()[:1], symbol="2330")

    count = archive_tw_stock_valuation.upsert_records(records)

    assert count == 1
    sql, params = executed[0]
    assert "INSERT INTO qd_tw_stock_valuation" in sql
    assert "ON CONFLICT (symbol, trade_date, source) DO UPDATE SET" in sql
    assert "?::jsonb" in sql
    assert params[:5] == ("2330", "2026-05-20", 29.38, 9.62, 1.01)
    assert executed[-2:] == [("commit", None), ("close", None)]
