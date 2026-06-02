"""Offline tests for TWStock monthly revenue archive script."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "archive_tw_stock_monthly_revenue.py"
SPEC = importlib.util.spec_from_file_location("archive_tw_stock_monthly_revenue", SCRIPT_PATH)
archive_tw_stock_monthly_revenue = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules["archive_tw_stock_monthly_revenue"] = archive_tw_stock_monthly_revenue
SPEC.loader.exec_module(archive_tw_stock_monthly_revenue)


def _rows():
    return [
        {"date": "2025-01-01", "stock_id": "2330", "country": "Taiwan", "revenue": 278163107000, "revenue_month": 12, "revenue_year": 2024, "create_time": ""},
        {"date": "2025-02-01", "stock_id": "2330", "country": "Taiwan", "revenue": 293288038000, "revenue_month": 1, "revenue_year": 2025, "create_time": ""},
        {"date": "2025-03-01", "stock_id": "2330", "country": "Taiwan", "revenue": 260008796000, "revenue_month": 2, "revenue_year": 2025, "create_time": ""},
        {"date": "2026-02-01", "stock_id": "2330", "country": "Taiwan", "revenue": 335771000000, "revenue_month": 1, "revenue_year": 2026, "create_time": ""},
    ]


def test_parse_finmind_rows_builds_monthly_revenue_and_growth():
    records = archive_tw_stock_monthly_revenue.parse_finmind_rows(_rows(), symbol="2330.TW")

    assert len(records) == 4
    assert records[0].symbol == "2330"
    assert records[0].report_date == "2025-01-01"
    assert records[0].revenue_period == "2024-12"
    assert records[0].monthly_revenue == 278163107000
    assert records[0].mom_growth is None
    assert records[1].revenue_period == "2025-01"
    assert records[1].mom_growth == round((293288038000 - 278163107000) / 278163107000 * 100, 8)
    assert records[3].revenue_period == "2026-01"
    assert records[3].yoy_growth == round((335771000000 - 293288038000) / 293288038000 * 100, 8)
    assert records[3].quality_flags == ""
    assert '"stock_id":"2330"' in records[0].raw_json


def test_parse_finmind_rows_marks_quality_flags_and_dedupes():
    rows = [
        {"date": "bad", "stock_id": "2330", "revenue": -1, "revenue_month": 13, "revenue_year": 2025},
        {"date": "2025-01-01", "stock_id": "2330", "revenue": 1, "revenue_month": 13, "revenue_year": 2025},
    ]

    records = archive_tw_stock_monthly_revenue.parse_finmind_rows(rows, symbol="2330")

    assert len(records) == 1
    assert "negative_revenue" in records[0].quality_flags
    assert "bad_revenue_month" in records[0].quality_flags
    assert "bad_report_date" in records[0].quality_flags


def test_summarize_monthly_revenue_records():
    records = archive_tw_stock_monthly_revenue.parse_finmind_rows(_rows(), symbol="2330")

    summary = archive_tw_stock_monthly_revenue.summarize(records)

    assert summary["count"] == 4
    assert summary["symbols"] == ["2330"]
    assert summary["period_min"] == "2024-12"
    assert summary["period_max"] == "2026-01"
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
    records = archive_tw_stock_monthly_revenue.parse_finmind_rows(_rows()[:1], symbol="2330")

    count = archive_tw_stock_monthly_revenue.upsert_records(records)

    assert count == 1
    sql, params = executed[0]
    assert "INSERT INTO qd_tw_stock_monthly_revenue" in sql
    assert "ON CONFLICT (symbol, revenue_period, source) DO UPDATE SET" in sql
    assert "?::jsonb" in sql
    assert params[:6] == ("2330", "2025-01-01", 2024, 12, "2024-12", 278163107000)
    assert executed[-2:] == [("commit", None), ("close", None)]
