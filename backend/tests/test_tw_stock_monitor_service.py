"""Tests for service-layer TWStock monitor scanning helpers."""
from __future__ import annotations

from app.services import tw_stock_monitor as monitor


def test_monitor_config_from_row_normalizes_symbols_and_defaults():
    default = monitor.monitor_config_from_row(None, user_id=7, name="default")
    assert default["symbols"] == ["2330", "0050", "00878"]
    assert default["enabled"] is False

    row = {
        "id": 3,
        "user_id": 7,
        "name": "phase7d",
        "symbols_json": '["2330", "2330.tw", "0050"]',
        "limit_bars": 80,
        "refresh_interval_sec": 60,
        "score_change_threshold": 5,
        "enabled": True,
        "notes": "research",
    }
    cfg = monitor.monitor_config_from_row(row, user_id=1, name="fallback")
    assert cfg["user_id"] == 7
    assert cfg["name"] == "phase7d"
    assert cfg["symbols"] == ["2330", "2330.TW", "0050"]
    assert cfg["enabled"] is True


def test_build_scan_alerts_detects_label_score_and_new_warnings():
    report = {
        "trend": {"label": "uptrend", "score": 82.5},
        "quality": {"warnings": ["stale_daily_bar", "short_history_below_60_bars"]},
    }
    previous = {
        "last_label": "range",
        "last_score": 70.0,
        "last_warnings_json": ["short_history_below_60_bars"],
    }

    alerts = monitor.build_scan_alerts("2330", report, previous, threshold=8.0)

    assert [item["type"] for item in alerts] == ["label_change", "score_change", "quality_warning"]
    assert all(item["severity"] in {"info", "warning"} for item in alerts)
    assert [item["category"] for item in alerts] == ["trend_change", "trend_change", "data_quality"]
    assert [item["reason"] for item in alerts] == ["trend_label_changed", "trend_score_threshold_crossed", "new_quality_warning"]
    assert all("不自动交易" in item["human_action"] for item in alerts)
    assert all(item["orders_enabled"] is False for item in alerts)
    assert "请人工" in alerts[0]["message"]


def test_build_scan_alerts_initial_quality_warning_is_review_only():
    report = {
        "trend": {"label": "unknown", "score": 0},
        "quality": {"warnings": ["stale_daily_bar"]},
    }

    alerts = monitor.build_scan_alerts("0050", report, previous=None, threshold=8.0)

    assert alerts == [{
        "type": "quality_warning",
        "severity": "warning",
        "message": "0050 数据质量提示：stale_daily_bar。请先复核数据后再做人工判断。",
        "category": "data_quality",
        "reason": "initial_quality_warning",
        "human_action": "先复核日线数据质量；不自动交易。",
        "orders_enabled": False,
    }]


def test_snapshot_with_alert_context_keeps_orders_disabled():
    report = {"symbol": "2330", "trend": {"label": "uptrend"}}
    alert = monitor.build_alert_payload(
        alert_type="score_change",
        severity="info",
        symbol="2330",
        message="msg",
        reason="trend_score_threshold_crossed",
        category="trend_change",
        human_action="人工确认趋势分数变化；不自动交易。",
    )

    snapshot = monitor.snapshot_with_alert_context(report, alert)

    assert snapshot["symbol"] == "2330"
    assert snapshot["alert_context"] == {
        "category": "trend_change",
        "reason": "trend_score_threshold_crossed",
        "human_action": "人工确认趋势分数变化；不自动交易。",
        "orders_enabled": False,
    }



def test_twstock_trend_uses_taipei_trade_date_for_daily_bar(monkeypatch):
    from app.services.tw_stock_trend import TWStockTrendService

    class FakeKlineService:
        def get_kline(self, market, symbol, timeframe, limit):
            return [
                {"time": 1779638400, "open": 2300, "high": 2320, "low": 2290, "close": 2310, "volume": 1000},
            ] * 60

    service = TWStockTrendService(kline_service=FakeKlineService())
    report = service.analyze_symbol(symbol="2330", limit=60)

    assert report["latest"]["date"] == "2026-05-25"
    assert report["quality"]["latest_date"] == "2026-05-25"


def test_monitor_config_route_degrades_to_default_when_database_unavailable(client, monkeypatch):
    from app.routes import tw_stock as tw_stock_routes

    def broken_db():
        raise RuntimeError("db offline")

    monkeypatch.setattr(tw_stock_routes, "get_db_connection", broken_db)

    resp = client.get("/api/tw-stock/monitor/config?name=default")
    payload = resp.get_json()

    assert resp.status_code == 200
    assert payload["code"] == 1
    assert payload["msg"] == "database_unavailable_default_config"
    assert payload["data"]["symbols"] == ["2330", "0050", "00878"]
    assert payload["data"]["persistence_enabled"] is False
    assert payload["data"]["degraded"] is True



def test_monitor_scan_route_degrades_to_ephemeral_when_database_unavailable(client, monkeypatch):
    from app.routes import tw_stock as tw_stock_routes

    def broken_db():
        raise RuntimeError("db offline")

    def fake_analyze_symbol(*, symbol, limit=120, as_of=None):
        return {
            "market": "TWStock",
            "symbol": symbol,
            "ok": True,
            "trend": {"label": "uptrend", "score": 70},
            "quality": {"warnings": [], "bar_count": limit},
            "trading": {"orders_enabled": False},
        }

    monkeypatch.setattr(tw_stock_routes, "get_db_connection", broken_db)
    monkeypatch.setattr(tw_stock_routes.trend_service, "analyze_symbol", fake_analyze_symbol)

    resp = client.post("/api/tw-stock/monitor/scan", json={"name": "default", "force": True})
    payload = resp.get_json()

    assert resp.status_code == 200
    assert payload["code"] == 1
    assert payload["msg"] == "database_unavailable_ephemeral_scan"
    assert payload["data"]["status"] == "scanned_ephemeral"
    assert payload["data"]["scanned_count"] == 3
    assert payload["data"]["alert_count"] == 0
    assert payload["data"]["persistence_enabled"] is False
    assert payload["data"]["trading"]["orders_enabled"] is False
