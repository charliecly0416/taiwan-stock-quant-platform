"""Tests for the TWStock monitor page Playwright smoke script."""
from __future__ import annotations

from scripts import check_tw_stock_monitor_page_e2e as e2e


def test_mock_app_serves_monitor_page_and_research_only_apis():
    app = e2e.create_mock_app()
    client = app.test_client()

    page = client.get("/api/tw-stock/monitor")
    assert page.status_code == 200
    html = page.get_data(as_text=True)
    assert "台股趨勢監控" in html
    assert "只讀：不下單" in html

    trends = client.get("/api/tw-stock/trends?symbols=2330,0050,00878&limit=120").get_json()["data"]
    assert trends["count"] == 3
    assert trends["trading"]["orders_enabled"] is False

    history = client.get("/api/tw-stock/monitor/history?symbol=2330&limit=120").get_json()["data"]
    assert history["count"] == 3
    assert history["trading"]["orders_enabled"] is False
