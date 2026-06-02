"""Offline tests for TWStock corporate-action archive script."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "archive_tw_stock_corporate_actions.py"
SPEC = importlib.util.spec_from_file_location("archive_tw_stock_corporate_actions", SCRIPT_PATH)
archive_tw_stock_corporate_actions = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules["archive_tw_stock_corporate_actions"] = archive_tw_stock_corporate_actions
SPEC.loader.exec_module(archive_tw_stock_corporate_actions)


def _rows():
    return [
        {
            "date": "2026-03-17",
            "stock_id": "2330",
            "before_price": 1845.0,
            "after_price": 1838.99,
            "stock_and_cache_dividend": 6.0,
            "stock_or_cache_dividend": "息",
            "reference_price": 1838.99,
        }
    ]


def test_parse_finmind_rows_builds_adjustment_factor():
    records = archive_tw_stock_corporate_actions.parse_finmind_rows(_rows(), symbol="2330.TW")

    assert len(records) == 1
    rec = records[0]
    assert rec.symbol == "2330"
    assert rec.action_date == "2026-03-17"
    assert rec.action_type == "息"
    assert rec.before_price == 1845.0
    assert rec.after_price == 1838.99
    assert rec.cash_or_stock_dividend == 6.0
    assert rec.adjustment_factor == round(1838.99 / 1845.0, 12)
    assert rec.source == "finmind"
    assert rec.quality_flags == ""
    assert '"stock_id":"2330"' in rec.raw_json


def test_parse_finmind_rows_marks_bad_reference_prices_and_dedupes():
    rows = [
        {"date": "2026-03-17", "stock_id": "2330", "before_price": 0, "after_price": 1},
        {"date": "2026-03-17", "stock_id": "2330", "before_price": 10, "after_price": 9},
    ]

    records = archive_tw_stock_corporate_actions.parse_finmind_rows(rows, symbol="2330")

    assert len(records) == 1
    assert "non_positive_reference_price" in records[0].quality_flags
    assert "non_positive_adjustment_factor" in records[0].quality_flags


def test_summarize_corporate_actions():
    records = archive_tw_stock_corporate_actions.parse_finmind_rows(_rows(), symbol="2330")

    summary = archive_tw_stock_corporate_actions.summarize(records)

    assert summary["count"] == 1
    assert summary["symbols"] == ["2330"]
    assert summary["date_min"] == "2026-03-17"
    assert summary["date_max"] == "2026-03-17"
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
    records = archive_tw_stock_corporate_actions.parse_finmind_rows(_rows(), symbol="2330")

    count = archive_tw_stock_corporate_actions.upsert_records(records)

    assert count == 1
    sql, params = executed[0]
    assert "INSERT INTO qd_tw_stock_corporate_actions" in sql
    assert "ON CONFLICT (symbol, action_date, source) DO UPDATE SET" in sql
    assert "?::jsonb" in sql
    assert params[:3] == ("2330", "2026-03-17", "息")
    assert params[6] == round(1838.99 / 1845.0, 12)
    assert executed[-2:] == [("commit", None), ("close", None)]
