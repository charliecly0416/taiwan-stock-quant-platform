"""Offline tests for TWSE official daily validation script."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "validate_tw_stock_daily.py"
SPEC = importlib.util.spec_from_file_location("validate_tw_stock_daily", SCRIPT_PATH)
validate_tw_stock_daily = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules["validate_tw_stock_daily"] = validate_tw_stock_daily
SPEC.loader.exec_module(validate_tw_stock_daily)

from scripts.archive_tw_stock_daily import DailyBarRecord  # noqa: E402


def _record(**overrides):
    data = {
        "symbol": "2330",
        "exchange": "TWSE",
        "instrument_type": "stock",
        "trade_date": "2026-05-22",
        "open": 2245.0,
        "high": 2260.0,
        "low": 2225.0,
        "close": 2255.0,
        "volume": 26823133,
        "trading_money": 60188140377.0,
        "trading_turnover": 95365,
        "spread": 25.0,
        "source": "finmind",
        "official_checked": 0,
        "official_match": 0,
        "quality_flags": "",
        "raw_json": "{}",
    }
    data.update(overrides)
    return DailyBarRecord(**data)


def test_roc_yyyymmdd_to_iso():
    assert validate_tw_stock_daily.roc_yyyymmdd_to_iso("1150522") == "2026-05-22"


def test_parse_twse_rows_extracts_official_close_and_volume():
    rows = [
        {
            "Code": "2330",
            "Name": "台積電",
            "Date": "1150522",
            "ClosingPrice": "2,255.00",
            "TradeVolume": "26,823,133",
        }
    ]

    parsed = validate_tw_stock_daily.parse_twse_rows(rows)

    official = parsed["2330"]
    assert official.symbol == "2330"
    assert official.name == "台積電"
    assert official.trade_date == "2026-05-22"
    assert official.close == 2255.0
    assert official.volume == 26823133
    assert '"Code":"2330"' in official.raw_json


def test_compare_record_to_official_matches_exact_close_and_volume():
    official = validate_tw_stock_daily.OfficialTwseRow(
        symbol="2330",
        name="台積電",
        trade_date="2026-05-22",
        close=2255.0,
        volume=26823133,
        raw_json="{}",
    )

    result = validate_tw_stock_daily.compare_record_to_official(_record(), official)

    assert result.official_checked == 1
    assert result.official_match == 1
    assert result.quality_flags == ""
    assert result.local_close == 2255.0
    assert result.official_volume == 26823133


def test_compare_record_to_official_reports_mismatch_flags():
    official = validate_tw_stock_daily.OfficialTwseRow(
        symbol="2330",
        name="台積電",
        trade_date="2026-05-21",
        close=2250.0,
        volume=1,
        raw_json="{}",
    )

    result = validate_tw_stock_daily.compare_record_to_official(_record(), official)

    assert result.official_checked == 1
    assert result.official_match == 0
    assert result.quality_flags.split(",") == ["date_mismatch", "close_mismatch", "volume_mismatch"]


def test_latest_records_by_symbol_keeps_max_trade_date():
    older = _record(trade_date="2026-05-21", close=2230.0)
    newer = _record(trade_date="2026-05-22", close=2255.0)

    latest = validate_tw_stock_daily.latest_records_by_symbol([newer, older])

    assert latest["2330"].trade_date == "2026-05-22"


def test_update_archive_validation_uses_targeted_update(monkeypatch):
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
    result = validate_tw_stock_daily.ValidationResult(
        symbol="2330",
        trade_date="2026-05-22",
        source="finmind",
        official_checked=1,
        official_match=1,
        quality_flags="",
        local_close=2255.0,
        official_close=2255.0,
        local_volume=26823133,
        official_volume=26823133,
    )

    count = validate_tw_stock_daily.update_archive_validation([result])

    assert count == 1
    sql, params = executed[0]
    assert "UPDATE qd_tw_stock_daily_bars" in sql
    assert "official_checked = ?" in sql
    assert params == (1, 1, "", "2330", "2026-05-22", "finmind")
    assert executed[-2:] == [("commit", None), ("close", None)]
