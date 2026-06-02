"""Offline tests for the Taiwan stock data-source adapter."""
from __future__ import annotations

from unittest.mock import patch

from app.data_sources.factory import DataSourceFactory
from app.data_sources.tw_stock import TAIPEI_TZ, TWStockCorporateAction, TWStockDataSource


def _payload(rows, status=200):
    return {"status": status, "data": rows}


def _rows():
    return [
        {"date": "2025-01-02", "stock_id": "2330", "Trading_Volume": "10,000", "open": 100, "max": 105, "min": 99, "close": 104},
        {"date": "2025-01-03", "stock_id": "2330", "Trading_Volume": 12000, "open": 104, "max": 108, "min": 103, "close": 107},
        {"date": "2025-01-06", "stock_id": "2330", "Trading_Volume": 15000, "open": 108, "max": 110, "min": 106, "close": 109},
    ]


def test_factory_recognizes_twstock_aliases():
    assert DataSourceFactory.normalize_market("TWStock") == "TWStock"
    assert DataSourceFactory.normalize_market("twstock") == "TWStock"
    assert DataSourceFactory.normalize_market("tw_stock") == "TWStock"
    assert DataSourceFactory.normalize_market("taiwanstock") == "TWStock"

    src = DataSourceFactory.get_source("TWStock")
    assert isinstance(src, TWStockDataSource)


def test_get_data_source_recognizes_twstock_legacy_aliases():
    src = DataSourceFactory.get_data_source("taiwan_stock")
    assert isinstance(src, TWStockDataSource)


def test_normalize_symbol_accepts_common_formats():
    assert TWStockDataSource.normalize_symbol("2330").symbol == "2330"
    assert TWStockDataSource.normalize_symbol("2330.TW").symbol == "2330"
    assert TWStockDataSource.normalize_symbol("2330.TW").exchange == "TWSE"
    assert TWStockDataSource.normalize_symbol("TWSE:2330").symbol == "2330"
    assert TWStockDataSource.normalize_symbol("TWSE:2330").exchange == "TWSE"
    assert TWStockDataSource.normalize_symbol("TPEX:6488").symbol == "6488"
    assert TWStockDataSource.normalize_symbol("TPEX:6488").exchange == "TPEX"
    assert TWStockDataSource.normalize_symbol("6488.TPEX").exchange == "TPEX"


def test_normalize_symbol_rejects_invalid_input():
    assert TWStockDataSource.normalize_symbol("").symbol == ""
    assert TWStockDataSource.normalize_symbol("../2330").symbol == ""
    assert TWStockDataSource.normalize_symbol("2330/2317").symbol == ""
    assert TWStockDataSource.normalize_symbol("A" * 40).symbol == ""


def test_bars_from_finmind_rows_parses_and_sorts_daily_bars():
    rows = [
        _rows()[1],
        _rows()[0],
        {"date": "2025-01-04", "open": "--", "max": 1, "min": 1, "close": 1, "Trading_Volume": 1},
        "bad-row",
    ]

    bars = TWStockDataSource._bars_from_finmind_rows(rows)

    assert len(bars) == 2
    assert bars[0]["time"] < bars[1]["time"]
    assert bars[0]["open"] == 100.0
    assert bars[0]["high"] == 105.0
    assert bars[0]["low"] == 99.0
    assert bars[0]["close"] == 104.0
    assert bars[0]["volume"] == 10000.0


def test_get_kline_fetches_finmind_daily_with_token_and_filters(monkeypatch):
    src = TWStockDataSource()
    calls = []

    def fake_http_get(params):
        calls.append(params)
        return _payload(_rows())

    monkeypatch.setenv("FINMIND_TOKEN", "finmind_test_token")
    with patch.object(src, "_http_get", side_effect=fake_http_get):
        bars = src.get_kline("2330.TW", "1D", limit=2)

    assert len(bars) == 2
    assert bars[0]["close"] == 107.0
    assert bars[1]["close"] == 109.0
    assert calls[0]["dataset"] == "TaiwanStockPrice"
    assert calls[0]["data_id"] == "2330"
    assert calls[0]["token"] == "finmind_test_token"


def test_get_kline_honors_after_time_without_truncating_left_edge():
    src = TWStockDataSource()
    all_bars = TWStockDataSource._bars_from_finmind_rows(_rows())
    after_time = all_bars[1]["time"]

    with patch.object(src, "_http_get", return_value=_payload(_rows())):
        bars = src.get_kline("2330", "1D", limit=1, after_time=after_time)

    assert [b["close"] for b in bars] == [107.0, 109.0]


def test_get_kline_weekly_resamples_daily_bars():
    src = TWStockDataSource()
    with patch.object(src, "_http_get", return_value=_payload(_rows())):
        bars = src.get_kline("2330", "1W", limit=10)

    assert len(bars) == 2
    assert bars[0]["open"] == 100.0
    assert bars[0]["high"] == 108.0
    assert bars[0]["low"] == 99.0
    assert bars[0]["close"] == 107.0
    assert bars[0]["volume"] == 22000.0
    assert bars[1]["open"] == 108.0
    assert bars[1]["close"] == 109.0


def test_get_kline_returns_empty_for_unsupported_timeframe_and_bad_symbol():
    src = TWStockDataSource()
    assert src.get_kline("2330", "5m", 10) == []
    assert src.get_kline("../2330", "1D", 10) == []


def test_get_kline_returns_empty_on_finmind_failure():
    src = TWStockDataSource()
    with patch.object(src, "_http_get", return_value={"status": 500, "data": _rows()}):
        assert src.get_kline("2330", "1D", 10) == []
    with patch.object(src, "_http_get", return_value=None):
        assert src.get_kline("2330", "1D", 10) == []


def test_get_ticker_uses_latest_daily_bar():
    src = TWStockDataSource()
    with patch.object(src, "_http_get", return_value=_payload(_rows())):
        ticker = src.get_ticker("2330.TW")

    assert ticker["last"] == 109.0
    assert ticker["previousClose"] == 107.0
    assert ticker["change"] == 2.0
    assert abs(ticker["changePercent"] - 1.87) < 0.01
    assert ticker["symbol"] == "2330"
    assert ticker["exchange"] == "TWSE"
    assert ticker["currency"] == "TWD"


def test_daily_timestamp_uses_taipei_midnight():
    bars = TWStockDataSource._bars_from_finmind_rows([_rows()[0]])
    from datetime import datetime

    dt = datetime.fromtimestamp(bars[0]["time"], tz=TAIPEI_TZ)
    assert dt.strftime("%Y-%m-%d %H:%M:%S") == "2025-01-02 00:00:00"



class _FakeCursor:
    def __init__(self, rows):
        self.rows = rows
        self.executed = []

    def execute(self, sql, params=None):
        self.executed.append((sql, params))

    def fetchall(self):
        return self.rows

    def close(self):
        pass


class _FakeDb:
    def __init__(self, rows):
        self.rows = rows
        self.cursor_obj = _FakeCursor(rows)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def cursor(self):
        return self.cursor_obj


def _install_fake_archive_db(monkeypatch, rows):
    import sys

    fake_db = _FakeDb(rows)

    class FakeDbModule:
        get_db_connection = staticmethod(lambda: fake_db)

    monkeypatch.setitem(sys.modules, "app.utils.db", FakeDbModule)
    return fake_db


def test_get_kline_prefers_local_archive_when_available(monkeypatch):
    src = TWStockDataSource()
    archive_rows = [
        {"trade_date": "2025-01-02", "open": 100, "high": 105, "low": 99, "close": 104, "volume": 10000},
        {"trade_date": "2025-01-03", "open": 104, "high": 108, "low": 103, "close": 107, "volume": 12000},
    ]
    fake_db = _install_fake_archive_db(monkeypatch, archive_rows)

    with patch.object(src, "_fetch_finmind_daily", side_effect=AssertionError("FinMind should not be called")):
        bars = src.get_kline("2330", "1D", limit=2)

    assert [bar["close"] for bar in bars] == [104.0, 107.0]
    sql, params = fake_db.cursor_obj.executed[0]
    assert "FROM qd_tw_stock_daily_bars" in sql
    assert params[0] == "2330"


def test_get_kline_falls_back_to_finmind_when_archive_is_insufficient(monkeypatch):
    src = TWStockDataSource()
    _install_fake_archive_db(monkeypatch, [
        {"trade_date": "2025-01-02", "open": 100, "high": 105, "low": 99, "close": 104, "volume": 10000},
    ])

    with patch.object(src, "_fetch_finmind_daily", return_value=TWStockDataSource._bars_from_finmind_rows(_rows())) as finmind:
        bars = src.get_kline("2330", "1D", limit=3)

    assert finmind.called
    assert [bar["close"] for bar in bars] == [104.0, 107.0, 109.0]


def test_get_kline_can_disable_archive_lookup_with_env(monkeypatch):
    src = TWStockDataSource()
    monkeypatch.setenv("TW_STOCK_ARCHIVE_LOOKUP", "false")

    with patch.object(src, "_fetch_archive_daily", side_effect=AssertionError("Archive should not be called")):
        with patch.object(src, "_fetch_finmind_daily", return_value=TWStockDataSource._bars_from_finmind_rows(_rows())) as finmind:
            bars = src.get_kline("2330", "1D", limit=2)

    assert finmind.called
    assert [bar["close"] for bar in bars] == [107.0, 109.0]


def test_corporate_actions_from_finmind_rows_builds_factors():
    rows = [
        {
            "date": "2026-03-17",
            "stock_id": "2330",
            "before_price": 1845.0,
            "after_price": 1838.99,
            "stock_and_cache_dividend": 6.0,
            "stock_or_cache_dividend": "息",
        }
    ]

    actions = TWStockDataSource._corporate_actions_from_finmind_rows(rows, symbol="2330")

    assert len(actions) == 1
    assert actions[0].symbol == "2330"
    assert actions[0].date == "2026-03-17"
    assert actions[0].action_type == "息"
    assert actions[0].adjustment_factor == round(1838.99 / 1845.0, 12)


def test_apply_corporate_action_adjustment_forward_adjusts_prior_bars_only():
    bars = TWStockDataSource._bars_from_finmind_rows([
        {"date": "2026-03-16", "open": 1840, "max": 1850, "min": 1830, "close": 1845, "Trading_Volume": 1},
        {"date": "2026-03-17", "open": 1840, "max": 1860, "min": 1830, "close": 1855, "Trading_Volume": 1},
    ])
    action = TWStockCorporateAction("2330", "2026-03-17", "息", 1845.0, 1838.99, 6.0, round(1838.99 / 1845.0, 12))

    adjusted = TWStockDataSource.apply_corporate_action_adjustment(bars, [action], "forward_adjusted")

    assert adjusted[0]["close"] == round(1845.0 * action.adjustment_factor, 4)
    assert adjusted[0]["corporateActionMode"] == "forward_adjusted"
    assert adjusted[1]["close"] == 1855.0
    assert adjusted[1]["adjustmentFactor"] == 1.0


def test_apply_corporate_action_adjustment_backward_adjusts_action_and_later_bars():
    bars = TWStockDataSource._bars_from_finmind_rows([
        {"date": "2026-03-16", "open": 1840, "max": 1850, "min": 1830, "close": 1845, "Trading_Volume": 1},
        {"date": "2026-03-17", "open": 1840, "max": 1860, "min": 1830, "close": 1855, "Trading_Volume": 1},
    ])
    action = TWStockCorporateAction("2330", "2026-03-17", "息", 1845.0, 1838.99, 6.0, round(1838.99 / 1845.0, 12))

    adjusted = TWStockDataSource.apply_corporate_action_adjustment(bars, [action], "backward_adjusted")

    assert adjusted[0]["close"] == 1845.0
    assert adjusted[1]["close"] == round(1855.0 / action.adjustment_factor, 4)
    assert adjusted[1]["corporateActionMode"] == "backward_adjusted"


def test_get_kline_applies_adjustment_only_when_env_requests_it(monkeypatch):
    src = TWStockDataSource()
    rows = [
        {"date": "2026-03-16", "stock_id": "2330", "Trading_Volume": 1, "open": 1840, "max": 1850, "min": 1830, "close": 1845},
        {"date": "2026-03-17", "stock_id": "2330", "Trading_Volume": 1, "open": 1840, "max": 1860, "min": 1830, "close": 1855},
    ]
    action = TWStockCorporateAction("2330", "2026-03-17", "息", 1845.0, 1838.99, 6.0, round(1838.99 / 1845.0, 12))
    monkeypatch.setenv("TW_STOCK_ARCHIVE_LOOKUP", "false")
    monkeypatch.setenv("TW_STOCK_CORPORATE_ACTION_MODE", "forward_adjusted")

    with patch.object(src, "_http_get", return_value=_payload(rows)):
        with patch.object(src, "_fetch_finmind_corporate_actions", return_value=[action]) as ca_fetch:
            bars = src.get_kline("2330", "1D", limit=2)

    assert ca_fetch.called
    assert bars[0]["close"] == round(1845.0 * action.adjustment_factor, 4)
    assert bars[0]["corporateActionMode"] == "forward_adjusted"
    assert bars[1]["close"] == 1855.0
