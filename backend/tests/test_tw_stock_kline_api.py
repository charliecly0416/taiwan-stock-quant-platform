"""API route tests for TWStock K-lines without real network calls."""
from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path
from unittest.mock import patch

import pytest
from flask import Flask

from app.data_sources.factory import DataSourceFactory
from app.utils.cache import CacheManager


_ROWS = [
    {"date": "2025-01-02", "stock_id": "2330", "Trading_Volume": 10000, "open": 100, "max": 105, "min": 99, "close": 104},
    {"date": "2025-01-03", "stock_id": "2330", "Trading_Volume": 12000, "open": 104, "max": 108, "min": 103, "close": 107},
]


def _load_kline_blueprint():
    """Load kline.py in isolation so app.services.__init__ does not import pandas-heavy services."""
    backend_root = Path(__file__).resolve().parents[1]
    service_path = backend_root / "app" / "services" / "kline.py"
    route_path = backend_root / "app" / "routes" / "kline.py"

    service_spec = importlib.util.spec_from_file_location("_qd_kline_service_for_api_test", service_path)
    service_module = importlib.util.module_from_spec(service_spec)
    assert service_spec and service_spec.loader
    service_spec.loader.exec_module(service_module)

    fake_services_pkg = types.ModuleType("app.services")
    fake_kline_module = types.ModuleType("app.services.kline")
    fake_kline_module.KlineService = service_module.KlineService

    old_services = sys.modules.get("app.services")
    old_kline = sys.modules.get("app.services.kline")
    sys.modules["app.services"] = fake_services_pkg
    sys.modules["app.services.kline"] = fake_kline_module
    try:
        route_spec = importlib.util.spec_from_file_location("_qd_kline_route_for_api_test", route_path)
        route_module = importlib.util.module_from_spec(route_spec)
        assert route_spec and route_spec.loader
        route_spec.loader.exec_module(route_module)
        return route_module.kline_bp
    finally:
        if old_services is not None:
            sys.modules["app.services"] = old_services
        else:
            sys.modules.pop("app.services", None)
        if old_kline is not None:
            sys.modules["app.services.kline"] = old_kline
        else:
            sys.modules.pop("app.services.kline", None)


@pytest.fixture
def kline_client():
    cache = CacheManager()
    if hasattr(cache, "_client") and hasattr(cache._client, "clear"):
        cache._client.clear()
    DataSourceFactory._sources.pop("TWStock", None)
    app = Flask(__name__)
    app.register_blueprint(_load_kline_blueprint(), url_prefix="/api/indicator")
    client = app.test_client()
    yield client
    if hasattr(cache, "_client") and hasattr(cache._client, "clear"):
        cache._client.clear()
    DataSourceFactory._sources.pop("TWStock", None)


def test_indicator_kline_api_returns_twstock_daily_data(kline_client):
    DataSourceFactory._sources.pop("TWStock", None)

    with patch("app.data_sources.tw_stock.TWStockDataSource._http_get", return_value={"status": 200, "data": _ROWS}) as http_get:
        resp = kline_client.get("/api/indicator/kline?market=TWStock&symbol=2330.TW&timeframe=1D&limit=10")

    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] == 1
    assert body["msg"] == "success"
    assert [bar["close"] for bar in body["data"]] == [104.0, 107.0]
    http_get.assert_called_once()


def test_indicator_kline_api_requires_symbol(kline_client):
    resp = kline_client.get("/api/indicator/kline?market=TWStock&timeframe=1D&limit=10")

    assert resp.status_code == 400
    body = resp.get_json()
    assert body["code"] == 0
    assert body["msg"] == "Missing symbol parameter"


def test_indicator_kline_api_returns_empty_success_shape_when_no_twstock_data(kline_client):
    DataSourceFactory._sources.pop("TWStock", None)

    with patch("app.data_sources.tw_stock.TWStockDataSource._http_get", return_value={"status": 200, "data": []}) as http_get:
        resp = kline_client.get("/api/indicator/kline?market=TWStock&symbol=2330&timeframe=1D&limit=10")

    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] == 0
    assert body["msg"] == "No data found"
    assert body["data"] == []
    http_get.assert_called_once()


def test_indicator_kline_api_does_not_call_provider_for_unsupported_twstock_timeframe(kline_client):
    DataSourceFactory._sources.pop("TWStock", None)

    with patch("app.data_sources.tw_stock.TWStockDataSource._http_get") as http_get:
        resp = kline_client.get("/api/indicator/kline?market=TWStock&symbol=2330&timeframe=5m&limit=10")

    assert resp.status_code == 200
    body = resp.get_json()
    assert body["code"] == 0
    assert body["data"] == []
    http_get.assert_not_called()
