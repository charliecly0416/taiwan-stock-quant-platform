"""BacktestService integration tests for TWStock using mocked K-lines."""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from app.services.backtest import BacktestService, _kline_cache


@pytest.fixture(autouse=True)
def clear_backtest_kline_cache():
    with _kline_cache._lock:
        _kline_cache._store.clear()
    yield
    with _kline_cache._lock:
        _kline_cache._store.clear()


def _ts(date_s: str) -> int:
    return int(datetime.strptime(date_s, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp())


_KLINES = [
    {"time": _ts("2025-01-02"), "open": 100, "high": 102, "low": 99, "close": 101, "volume": 10000},
    {"time": _ts("2025-01-03"), "open": 101, "high": 104, "low": 100, "close": 103, "volume": 12000},
    {"time": _ts("2025-01-06"), "open": 104, "high": 107, "low": 103, "close": 106, "volume": 15000},
    {"time": _ts("2025-01-07"), "open": 106, "high": 108, "low": 105, "close": 107, "volume": 13000},
    {"time": _ts("2025-01-08"), "open": 107, "high": 109, "low": 104, "close": 105, "volume": 14000},
]


_INDICATOR = """
df = df.copy()
df['buy'] = False
df['sell'] = False
df.loc[df.index[0], 'buy'] = True
df.loc[df.index[-1], 'sell'] = True
output = {'name': 'TWStock smoke backtest', 'plots': [], 'signals': []}
"""


def test_backtest_service_runs_twstock_daily_backtest_without_real_data_request():
    svc = BacktestService()
    calls = []

    def fake_get_kline(**kwargs):
        calls.append(kwargs)
        return list(_KLINES)

    with patch("app.services.backtest.DataSourceFactory.get_kline", side_effect=fake_get_kline):
        result = svc.run(
            indicator_code=_INDICATOR,
            market="TWStock",
            symbol="2330",
            timeframe="1D",
            start_date=datetime(2025, 1, 2),
            end_date=datetime(2025, 1, 8),
            initial_capital=100000,
            commission=0.002925,
            slippage=0.001,
            leverage=1,
            trade_direction="long",
            strategy_config={"position": {"entryPct": 1.0}},
        )

    assert calls
    assert calls[0]["market"] == "TWStock"
    assert calls[0]["symbol"] == "2330"
    assert calls[0]["timeframe"] == "1D"
    assert calls[0]["after_time"] is not None
    assert calls[0]["before_time"] is not None

    assumptions = result["executionAssumptions"]
    assert assumptions["simulationMode"] == "standard"
    assert assumptions["strategyTimeframe"] == "1D"
    assert assumptions["market"] == "TWStock"
    assert assumptions["currency"] == "TWD"
    assert assumptions["timezone"] == "Asia/Taipei"
    assert assumptions["lotSize"] == 1000
    assert assumptions["lotSizeEnforced"] is False
    assert assumptions["sellTaxMode"] == "folded_into_commission"
    assert assumptions["commission"] == 0.002925
    assert assumptions["slippage"] == 0.001
    assert isinstance(result["equityCurve"], list)
    assert len(result["equityCurve"]) > 0
    assert "totalReturn" in result
    assert "totalTrades" in result

    metrics = result["metrics"]
    assert metrics["totalReturn"] == result["totalReturn"]
    assert "maxDrawdown" in metrics
    assert "winRate" in metrics
    assert "totalTrades" in metrics
    assert "benchmarkReturn" in metrics
    assert "exposure" in metrics

    quality = result["dataQuality"]
    assert quality["market"] == "TWStock"
    assert quality["symbol"] == "2330"
    assert quality["timeframe"] == "1D"
    assert quality["barCount"] == len(_KLINES)
    assert quality["preferredSource"] == "qd_tw_stock_daily_bars"
    assert quality["adjustmentMode"] == "raw"
    assert "short_history_below_60_bars" in quality["warnings"]

    trading = result["trading"]
    assert trading["orders_enabled"] is False
    assert trading["connects_to_broker"] is False
    assert trading["paper_orders_enabled"] is False
    assert trading["live_trading_enabled"] is False
    assert trading["quick_trade_enabled"] is False
    assert trading["writes_positions"] is False
    assert trading["writes_orders"] is False


def test_backtest_service_raises_clear_error_when_twstock_has_no_data():
    svc = BacktestService()

    with patch("app.services.backtest.DataSourceFactory.get_kline", return_value=[]):
        try:
            svc.run(
                indicator_code=_INDICATOR,
                market="TWStock",
                symbol="2317",
                timeframe="1D",
                start_date=datetime(2025, 1, 2),
                end_date=datetime(2025, 1, 8),
                initial_capital=100000,
            )
        except ValueError as exc:
            assert "No TWStock daily bars available" in str(exc)
            assert "qd_tw_stock_daily_bars" in str(exc)
        else:
            raise AssertionError("BacktestService.run should fail when TWStock data is empty")



def test_backtest_route_applies_twstock_default_costs(client, monkeypatch):
    from app.routes import backtest as backtest_routes
    from app.utils import auth as auth_utils

    captured = {}

    def fake_verify_token(_raw):
        return {"sub": "tester", "user_id": 1, "role": "user"}

    def fake_run(**kwargs):
        captured.update(kwargs)
        return {
            "totalReturn": 0,
            "totalTrades": 0,
            "equityCurve": [],
            "trades": [],
            "executionAssumptions": {},
        }

    monkeypatch.setattr(auth_utils, "verify_token", fake_verify_token)
    monkeypatch.setattr(backtest_routes.backtest_service, "run", fake_run)

    resp = client.post(
        "/api/indicator/backtest",
        headers={"Authorization": "Bearer test", "Content-Type": "application/json"},
        json={
            "indicatorCode": _INDICATOR,
            "market": "TWStock",
            "symbol": "2330",
            "timeframe": "1D",
            "startDate": "2025-01-02",
            "endDate": "2025-01-08",
            "initialCapital": 100000,
            "enableMtf": False,
            "persist": False,
        },
    )

    assert resp.status_code == 200
    assert resp.get_json()["code"] == 1
    assert captured["market"] == "TWStock"
    assert captured["commission"] == 0.002925
    assert captured["slippage"] == 0.001
    assert captured["trade_direction"] == "long"


def test_backtest_service_rejects_twstock_non_daily_timeframe():
    svc = BacktestService()

    with pytest.raises(ValueError, match="timeframe=1D"):
        svc.run(
            indicator_code=_INDICATOR,
            market="TWStock",
            symbol="2330",
            timeframe="1W",
            start_date=datetime(2025, 1, 2),
            end_date=datetime(2025, 1, 8),
            initial_capital=100000,
        )


def test_backtest_route_defaults_twstock_persist_false(client, monkeypatch):
    from app.routes import backtest as backtest_routes
    from app.utils import auth as auth_utils

    persisted = []

    def fake_verify_token(_raw):
        return {"sub": "tester", "user_id": 1, "role": "user"}

    def fake_run(**_kwargs):
        return {
            "totalReturn": 0,
            "totalTrades": 0,
            "equityCurve": [],
            "trades": [],
            "executionAssumptions": {},
            "metrics": {"totalReturn": 0, "maxDrawdown": 0, "winRate": 0, "totalTrades": 0},
            "dataQuality": {"barCount": 0},
            "trading": {"orders_enabled": False, "connects_to_broker": False},
        }

    def fake_persist(**kwargs):
        persisted.append(kwargs)
        return 999

    monkeypatch.setattr(auth_utils, "verify_token", fake_verify_token)
    monkeypatch.setattr(backtest_routes.backtest_service, "run", fake_run)
    monkeypatch.setattr(backtest_routes.backtest_service, "persist_run", fake_persist)

    resp = client.post(
        "/api/indicator/backtest",
        headers={"Authorization": "Bearer test", "Content-Type": "application/json"},
        json={
            "indicatorCode": _INDICATOR,
            "market": "TWStock",
            "symbol": "2330",
            "timeframe": "1D",
            "startDate": "2025-01-02",
            "endDate": "2025-01-08",
            "initialCapital": 100000,
            "enableMtf": False,
        },
    )

    payload = resp.get_json()
    assert resp.status_code == 200
    assert payload["code"] == 1
    assert payload["data"]["runId"] is None
    assert persisted == []


def test_backtest_route_rejects_twstock_non_daily_timeframe(client, monkeypatch):
    from app.utils import auth as auth_utils

    def fake_verify_token(_raw):
        return {"sub": "tester", "user_id": 1, "role": "user"}

    monkeypatch.setattr(auth_utils, "verify_token", fake_verify_token)

    resp = client.post(
        "/api/indicator/backtest",
        headers={"Authorization": "Bearer test", "Content-Type": "application/json"},
        json={
            "indicatorCode": _INDICATOR,
            "market": "TWStock",
            "symbol": "2330",
            "timeframe": "1W",
            "startDate": "2025-01-02",
            "endDate": "2025-01-08",
            "initialCapital": 100000,
            "enableMtf": False,
        },
    )

    assert resp.status_code == 400
    assert resp.get_json()["code"] == 0
    assert "timeframe=1D" in resp.get_json()["msg"]



def test_twstock_builtin_templates_are_available_and_research_only(client):
    resp = client.get("/api/indicator/backtest/tw-stock/templates")

    payload = resp.get_json()
    assert resp.status_code == 200
    assert payload["code"] == 1
    ids = {item["id"] for item in payload["data"]["items"]}
    assert {"ma_cross_builtin", "rsi_builtin", "macd_builtin", "bollinger_builtin"}.issubset(ids)
    trading = payload["data"]["trading"]
    assert trading["orders_enabled"] is False
    assert trading["connects_to_broker"] is False
    assert trading["paper_orders_enabled"] is False
    assert trading["live_trading_enabled"] is False


def test_twstock_builtin_template_code_is_safe_for_all_templates():
    from app.services.tw_stock_backtest_templates import build_tw_stock_builtin_indicator_code
    from app.utils.safe_exec import validate_code_safety

    for strategy_id in ["ma_cross_builtin", "rsi_builtin", "macd_builtin", "bollinger_builtin"]:
        code = build_tw_stock_builtin_indicator_code(strategy_id)
        is_safe, reason = validate_code_safety(code)
        assert is_safe, f"{strategy_id} unsafe: {reason}"
        assert "df['buy']" in code
        assert "df['sell']" in code
        assert "tradeDirection long" in code


def test_backtest_route_runs_twstock_builtin_strategy_without_indicator_code(client, monkeypatch):
    from app.routes import backtest as backtest_routes
    from app.utils import auth as auth_utils

    captured = {}

    def fake_verify_token(_raw):
        return {"sub": "tester", "user_id": 1, "role": "user"}

    def fake_run(**kwargs):
        captured.update(kwargs)
        return {
            "totalReturn": 0,
            "totalTrades": 0,
            "equityCurve": [],
            "trades": [],
            "executionAssumptions": {},
            "metrics": {"totalReturn": 0, "maxDrawdown": 0, "winRate": 0, "totalTrades": 0},
            "dataQuality": {"barCount": 0},
            "trading": {"orders_enabled": False, "connects_to_broker": False},
        }

    monkeypatch.setattr(auth_utils, "verify_token", fake_verify_token)
    monkeypatch.setattr(backtest_routes.backtest_service, "run", fake_run)

    resp = client.post(
        "/api/indicator/backtest",
        headers={"Authorization": "Bearer test", "Content-Type": "application/json"},
        json={
            "market": "TWStock",
            "symbol": "2330",
            "timeframe": "1D",
            "startDate": "2025-01-02",
            "endDate": "2025-01-08",
            "initialCapital": 100000,
            "strategyId": "ma_cross_builtin",
            "strategyConfig": {"template": {"fastWindow": 2, "slowWindow": 3}},
            "enableMtf": False,
        },
    )

    payload = resp.get_json()
    assert resp.status_code == 200
    assert payload["code"] == 1
    assert payload["data"]["runId"] is None
    assert captured["market"] == "TWStock"
    assert captured["timeframe"] == "1D"
    assert "TWStock MA Cross Built-in" in captured["indicator_code"]
    assert captured["strategy_config"]["strategyId"] == "ma_cross_builtin"
    assert captured["strategy_config"]["strategySource"] == "tw_stock_builtin"


def test_backtest_route_rejects_unknown_twstock_builtin_strategy(client, monkeypatch):
    from app.routes import backtest as backtest_routes
    from app.utils import auth as auth_utils

    called = {"run": False}

    def fake_verify_token(_raw):
        return {"sub": "tester", "user_id": 1, "role": "user"}

    def fake_run(**_kwargs):
        called["run"] = True
        return {}

    monkeypatch.setattr(auth_utils, "verify_token", fake_verify_token)
    monkeypatch.setattr(backtest_routes.backtest_service, "run", fake_run)

    resp = client.post(
        "/api/indicator/backtest",
        headers={"Authorization": "Bearer test", "Content-Type": "application/json"},
        json={
            "market": "TWStock",
            "symbol": "2330",
            "timeframe": "1D",
            "startDate": "2025-01-02",
            "endDate": "2025-01-08",
            "strategyId": "unknown_builtin",
            "enableMtf": False,
        },
    )

    assert resp.status_code == 400
    assert resp.get_json()["code"] == 0
    assert "Unsupported TWStock built-in strategyId" in resp.get_json()["msg"]
    assert called["run"] is False


def test_twstock_backtest_service_does_not_touch_broker_order_or_position_paths():
    svc = BacktestService()
    forbidden = [
        "app.services.backtest.get_db_connection",
        "app.services.backtest.DataSourceFactory.get_ticker",
    ]

    with patch("app.services.backtest.DataSourceFactory.get_kline", return_value=list(_KLINES)) as get_kline:
        with patch(forbidden[0]) as get_db_connection:
            with patch(forbidden[1]) as get_ticker:
                result = svc.run(
                    indicator_code=_INDICATOR,
                    market="TWStock",
                    symbol="2330",
                    timeframe="1D",
                    start_date=datetime(2025, 1, 2),
                    end_date=datetime(2025, 1, 8),
                    initial_capital=100000,
                    commission=0.002925,
                    slippage=0.001,
                    leverage=1,
                    trade_direction="long",
                )

    assert get_kline.called
    assert not get_db_connection.called
    assert not get_ticker.called
    assert result["trading"]["orders_enabled"] is False
    assert result["trading"]["writes_orders"] is False
    assert result["trading"]["writes_positions"] is False
