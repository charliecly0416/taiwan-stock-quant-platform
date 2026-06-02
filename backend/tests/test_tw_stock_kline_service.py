"""KlineService integration tests for TWStock without real network calls."""
from __future__ import annotations

import importlib.util
from pathlib import Path
from unittest.mock import patch

from app.data_sources.factory import DataSourceFactory


def _load_kline_service_class():
    path = Path(__file__).resolve().parents[1] / "app" / "services" / "kline.py"
    spec = importlib.util.spec_from_file_location("_qd_kline_service_for_test", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module.KlineService


KlineService = _load_kline_service_class()


_ROWS = [
    {"date": "2025-01-02", "stock_id": "2330", "Trading_Volume": 10000, "open": 100, "max": 105, "min": 99, "close": 104},
    {"date": "2025-01-03", "stock_id": "2330", "Trading_Volume": 12000, "open": 104, "max": 108, "min": 103, "close": 107},
]


def test_kline_service_routes_twstock_to_data_source(monkeypatch):
    DataSourceFactory._sources.pop("TWStock", None)
    service = KlineService()
    service.cache_ttl = {"1D": 60}

    calls = []

    def fake_http_get(params):
        calls.append(params)
        return {"status": 200, "data": _ROWS}

    monkeypatch.setenv("FINMIND_TOKEN", "service_test_token")
    with patch("app.data_sources.tw_stock.TWStockDataSource._http_get", side_effect=fake_http_get):
        bars = service.get_kline("TWStock", "2330.TW", "1D", limit=10)

    assert [b["close"] for b in bars] == [104.0, 107.0]
    assert calls[0]["dataset"] == "TaiwanStockPrice"
    assert calls[0]["data_id"] == "2330"
    assert calls[0]["token"] == "service_test_token"


def test_kline_service_cache_key_separates_twstock_from_usstock():
    service = KlineService()
    seen_keys = []

    class FakeCache:
        def get(self, key):
            seen_keys.append(("get", key))
            return None

        def set(self, key, value, ttl):
            seen_keys.append(("set", key, ttl))

    service.cache = FakeCache()
    service.cache_ttl = {"1D": 60}

    with patch("app.data_sources.factory.DataSourceFactory.get_kline", return_value=[{"time": 1, "open": 1, "high": 1, "low": 1, "close": 1, "volume": 1}]):
        service.get_kline("TWStock", "2330", "1D", limit=5)
        service.get_kline("USStock", "2330", "1D", limit=5)

    get_keys = [key for op, key, *_ in seen_keys if op == "get"]
    assert "kline:TWStock:::2330:1D:5" in get_keys
    assert "kline:USStock:::2330:1D:5" in get_keys
    assert len(set(get_keys)) == 2


def test_kline_service_returns_empty_for_twstock_unsupported_timeframe():
    DataSourceFactory._sources.pop("TWStock", None)
    service = KlineService()

    with patch("app.data_sources.tw_stock.TWStockDataSource._http_get") as http_get:
        bars = service.get_kline("TWStock", "2330", "5m", limit=10)

    assert bars == []
    http_get.assert_not_called()
