"""Offline tests for TWStock margin trading archive script."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "archive_tw_stock_margin_trading.py"
SPEC = importlib.util.spec_from_file_location("archive_tw_stock_margin_trading", SCRIPT_PATH)
archive_tw_stock_margin_trading = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules["archive_tw_stock_margin_trading"] = archive_tw_stock_margin_trading
SPEC.loader.exec_module(archive_tw_stock_margin_trading)


def _rows():
    return [
        {
            "date": "2026-05-22",
            "stock_id": "2330",
            "MarginPurchaseBuy": 699,
            "MarginPurchaseCashRepayment": 13,
            "MarginPurchaseLimit": 6483131,
            "MarginPurchaseSell": 692,
            "MarginPurchaseTodayBalance": 26946,
            "MarginPurchaseYesterdayBalance": 26952,
            "Note": " ",
            "OffsetLoanAndShort": 2,
            "ShortSaleBuy": 5,
            "ShortSaleCashRepayment": 0,
            "ShortSaleLimit": 6483131,
            "ShortSaleSell": 2,
            "ShortSaleTodayBalance": 97,
            "ShortSaleYesterdayBalance": 100,
        }
    ]


def test_parse_finmind_rows_builds_margin_record():
    records = archive_tw_stock_margin_trading.parse_finmind_rows(_rows(), symbol="2330.TW")

    assert len(records) == 1
    rec = records[0]
    assert rec.symbol == "2330"
    assert rec.trade_date == "2026-05-22"
    assert rec.margin_purchase_buy == 699
    assert rec.margin_purchase_sell == 692
    assert rec.margin_purchase_cash_repayment == 13
    assert rec.margin_purchase_yesterday_balance == 26952
    assert rec.margin_purchase_today_balance == 26946
    assert rec.margin_purchase_limit == 6483131
    assert rec.short_sale_buy == 5
    assert rec.short_sale_sell == 2
    assert rec.short_sale_cash_repayment == 0
    assert rec.short_sale_yesterday_balance == 100
    assert rec.short_sale_today_balance == 97
    assert rec.short_sale_limit == 6483131
    assert rec.offset_loan_and_short == 2
    assert rec.note == ""
    assert rec.quality_flags == ""
    assert '"stock_id":"2330"' in rec.raw_json


def test_parse_finmind_rows_marks_quality_flags_and_dedupes():
    rows = [
        {"date": "bad", "stock_id": "2330", "MarginPurchaseBuy": -1, "ShortSaleSell": 1},
        {"date": "bad", "stock_id": "2330", "MarginPurchaseBuy": 1, "ShortSaleSell": 1},
    ]

    records = archive_tw_stock_margin_trading.parse_finmind_rows(rows, symbol="2330")

    assert len(records) == 1
    assert "negative_margin_purchase_buy" in records[0].quality_flags
    assert "bad_trade_date" in records[0].quality_flags


def test_summarize_margin_records():
    records = archive_tw_stock_margin_trading.parse_finmind_rows(_rows(), symbol="2330")

    summary = archive_tw_stock_margin_trading.summarize(records)

    assert summary["count"] == 1
    assert summary["symbols"] == ["2330"]
    assert summary["date_min"] == "2026-05-22"
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
    records = archive_tw_stock_margin_trading.parse_finmind_rows(_rows(), symbol="2330")

    count = archive_tw_stock_margin_trading.upsert_records(records)

    assert count == 1
    sql, params = executed[0]
    assert "INSERT INTO qd_tw_stock_margin_trading" in sql
    assert "ON CONFLICT (symbol, trade_date, source) DO UPDATE SET" in sql
    assert "?::jsonb" in sql
    assert params[:2] == ("2330", "2026-05-22")
    assert params[2:8] == (699, 692, 13, 26952, 26946, 6483131)
    assert params[8:14] == (5, 2, 0, 100, 97, 6483131)
    assert executed[-2:] == [("commit", None), ("close", None)]
