"""API tests for read-only TWStock qlib cross analysis."""
from __future__ import annotations


class FakeCrossAnalysisService:
    def __init__(self) -> None:
        self.latest_calls = []
        self.symbol_calls = []

    def latest(self, *, bucket: str, limit: int, include_raw_trend: bool, max_items: int):
        self.latest_calls.append((bucket, limit, include_raw_trend, max_items))
        return {
            "ok": True,
            "status": "accepted",
            "bucket": bucket,
            "qlib": {
                "asof": "2026-06-01",
                "run_id": "option_c_daily_signal_20260601_20260602T090715Z",
                "recorder_id": "950741cfd5f14ee5a05464fec3e12e0a",
                "target_horizon": "next_trading_day_research_ranking",
                "research_signal_not_order": True,
            },
            "items": [{
                "symbol": "2330",
                "instrument": "TW2330",
                "qlib": {"bucket": "top30", "rank": 1, "score": 0.2},
                "quantdinger": {"trend_label": "uptrend", "trend_score": 72.5, "latest_date": "2026-06-01", "quality_warnings": []},
                "data_basis": {"qlib_source": "Yahoo adjusted model signal", "quantdinger_source": "KlineService:TWStock:1D", "date_gap_days": 0},
                "cross": {"category": "focus_watch", "alignment": "aligned", "priority": "high", "human_action": "加入重点观察并人工复盘"},
                **({"rawTrend": {"ok": True}} if include_raw_trend else {}),
            }],
            "summary": {"category_counts": {"focus_watch": 1}},
            "freshness": {
                "qlib": {"status": "accepted", "asof": "2026-06-01", "run_id": "option_c_daily_signal_20260601_20260602T090715Z", "target_horizon": "next_trading_day_research_ranking"},
                "quantdinger": {"latest_date_min": "2026-06-01", "latest_date_max": "2026-06-01", "source": "KlineService:TWStock:1D"},
                "date_gap_days_min": 0,
                "date_gap_days_max": 0,
                "status": "fresh",
                "warnings": [],
            },
            "basis": {"qlib_source": "Yahoo adjusted model signal", "quantdinger_source": "raw TWStock daily KlineService data", "note": "fixture basis note"},
            "trading": {"orders_enabled": False, "connects_to_broker": False, "research_signal_not_order": True},
        }

    def symbol_detail(self, *, symbol: str, limit: int, include_raw_trend: bool):
        self.symbol_calls.append((symbol, limit, include_raw_trend))
        if symbol == "9999":
            return {
                "ok": False,
                "status": "not_in_latest_qlib_top50",
                "symbol": symbol,
                "item": None,
                "trend": {"ok": True, "trend_label": "sideways"},
                "trading": {"orders_enabled": False, "research_signal_not_order": True},
            }
        return {
            "ok": True,
            "status": "accepted",
            "symbol": symbol,
            "item": {
                "symbol": symbol,
                "cross": {"category": "focus_watch", "human_action": "加入重点观察并人工复盘"},
                **({"rawTrend": {"ok": True}} if include_raw_trend else {}),
            },
            "trading": {"orders_enabled": False, "research_signal_not_order": True},
        }


def test_cross_analysis_latest_api_contract_and_params(client, monkeypatch):
    fake = FakeCrossAnalysisService()
    from app.routes import tw_stock as tw_stock_route

    monkeypatch.setattr(tw_stock_route, "cross_analysis_service", fake)
    resp = client.get("/api/tw-stock/cross-analysis/latest?bucket=top50&limit=9&maxItems=4&includeRawTrend=true")
    payload = resp.get_json()

    assert resp.status_code == 200
    assert payload["code"] == 1
    data = payload["data"]
    assert fake.latest_calls == [("top50", 20, True, 4)]
    assert data["qlib"]["target_horizon"] == "next_trading_day_research_ranking"
    assert data["qlib"]["research_signal_not_order"] is True
    assert data["items"][0]["data_basis"]["qlib_source"] == "Yahoo adjusted model signal"
    assert data["freshness"]["status"] == "fresh"
    assert data["basis"]["quantdinger_source"] == "raw TWStock daily KlineService data"
    assert data["items"][0]["cross"]["category"] == "focus_watch"
    assert "rawTrend" in data["items"][0]
    assert data["trading"]["orders_enabled"] is False


def test_cross_analysis_latest_api_blocked_response(client, monkeypatch):
    class BlockedService(FakeCrossAnalysisService):
        def latest(self, **kwargs):
            return {
                "ok": False,
                "status": "blocked_validation_failed",
                "message": "fixture blocked",
                "items": [],
                "freshness": {"status": "blocked"},
                "basis": {"qlib_source": "Yahoo adjusted model signal"},
                "trading": {"orders_enabled": False, "research_signal_not_order": True},
            }

    from app.routes import tw_stock as tw_stock_route

    monkeypatch.setattr(tw_stock_route, "cross_analysis_service", BlockedService())
    resp = client.get("/api/tw-stock/cross-analysis/latest")
    payload = resp.get_json()

    assert resp.status_code == 200
    assert payload["code"] == 0
    assert payload["data"]["status"] == "blocked_validation_failed"
    assert payload["data"]["items"] == []
    assert payload["data"]["freshness"]["status"] == "blocked"
    assert payload["data"]["trading"]["orders_enabled"] is False


def test_cross_analysis_symbol_api_in_and_not_in_top50(client, monkeypatch):
    fake = FakeCrossAnalysisService()
    from app.routes import tw_stock as tw_stock_route

    monkeypatch.setattr(tw_stock_route, "cross_analysis_service", fake)
    found = client.get("/api/tw-stock/cross-analysis/symbol/2330?limit=77&includeRawTrend=false").get_json()
    missing = client.get("/api/tw-stock/cross-analysis/symbol/9999").get_json()

    assert fake.symbol_calls[0] == ("2330", 77, False)
    assert fake.symbol_calls[1] == ("9999", 120, True)
    assert found["code"] == 1
    assert found["data"]["item"]["cross"]["category"] == "focus_watch"
    assert "rawTrend" not in found["data"]["item"]
    assert missing["code"] == 0
    assert missing["data"]["status"] == "not_in_latest_qlib_top50"
    assert missing["data"]["trading"]["orders_enabled"] is False
