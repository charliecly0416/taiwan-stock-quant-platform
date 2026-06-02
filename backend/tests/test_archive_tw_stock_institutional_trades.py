"""Offline tests for TWStock institutional trade archive script."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "archive_tw_stock_institutional_trades.py"
SPEC = importlib.util.spec_from_file_location("archive_tw_stock_institutional_trades", SCRIPT_PATH)
archive_tw_stock_institutional_trades = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules["archive_tw_stock_institutional_trades"] = archive_tw_stock_institutional_trades
SPEC.loader.exec_module(archive_tw_stock_institutional_trades)


def _rows():
    return [
        {"date": "2026-05-22", "stock_id": "2330", "buy": 0, "name": "Foreign_Dealer_Self", "sell": 0},
        {"date": "2026-05-22", "stock_id": "2330", "buy": 22000, "name": "Investment_Trust", "sell": 486848},
        {"date": "2026-05-22", "stock_id": "2330", "buy": 448400, "name": "Dealer_self", "sell": 416000},
        {"date": "2026-05-22", "stock_id": "2330", "buy": 287566, "name": "Dealer_Hedging", "sell": 132302},
        {"date": "2026-05-22", "stock_id": "2330", "buy": 16780717, "name": "Foreign_Investor", "sell": 16047743},
    ]


def test_parse_finmind_rows_aggregates_institutional_categories():
    records = archive_tw_stock_institutional_trades.parse_finmind_rows(_rows(), symbol="2330.TW")

    assert len(records) == 1
    rec = records[0]
    assert rec.symbol == "2330"
    assert rec.trade_date == "2026-05-22"
    assert rec.foreign_buy == 16780717
    assert rec.foreign_sell == 16047743
    assert rec.foreign_net_buy == 732974
    assert rec.investment_trust_net_buy == -464848
    assert rec.dealer_self_net_buy == 32400
    assert rec.dealer_hedging_net_buy == 155264
    assert rec.dealer_net_buy == 187664
    assert rec.total_institutional_net_buy == 455790
    assert rec.quality_flags == ""
    assert '"Foreign_Investor"' in rec.raw_json


def test_parse_finmind_rows_marks_unknown_category():
    rows = _rows() + [{"date": "2026-05-22", "stock_id": "2330", "buy": 1, "name": "Unknown", "sell": 0}]

    records = archive_tw_stock_institutional_trades.parse_finmind_rows(rows, symbol="2330")

    assert records[0].quality_flags == "unknown_category"


def test_summarize_institutional_records():
    records = archive_tw_stock_institutional_trades.parse_finmind_rows(_rows(), symbol="2330")

    summary = archive_tw_stock_institutional_trades.summarize(records)

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
    records = archive_tw_stock_institutional_trades.parse_finmind_rows(_rows(), symbol="2330")

    count = archive_tw_stock_institutional_trades.upsert_records(records)

    assert count == 1
    sql, params = executed[0]
    assert "INSERT INTO qd_tw_stock_institutional_trades" in sql
    assert "ON CONFLICT (symbol, trade_date, source) DO UPDATE SET" in sql
    assert "?::jsonb" in sql
    assert params[:2] == ("2330", "2026-05-22")
    assert params[2:5] == (16780717, 16047743, 732974)
    assert params[15] == 455790
    assert executed[-2:] == [("commit", None), ("close", None)]
