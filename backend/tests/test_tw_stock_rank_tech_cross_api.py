"""API tests for read-only TWStock rank-tech cross classification."""
from __future__ import annotations

from pathlib import Path


class FakeRankTechCrossService:
    def __init__(self) -> None:
        self.calls = []

    def latest(self, *, bucket: str, limit: int, max_items: int, include_technical_strategies: bool = True, technical_strategies=None):
        self.calls.append((bucket, limit, max_items, include_technical_strategies, technical_strategies))
        return {
            "ok": True,
            "status": "accepted",
            "simulation_only": True,
            "research_signal_not_order": True,
            "bucket": bucket,
            "limit": limit,
            "maxItems": max_items,
            "qlib": {
                "asof": "2026-06-04",
                "run_id": "run-1",
                "target_horizon": "next_trading_day_research_ranking",
                "research_signal_not_order": True,
            },
            "items": [
                {
                    "symbol": "2330",
                    "rank": 1,
                    "rankTier": "top10",
                    "trend": {"label": "uptrend", "score": 72.4, "latest_date": "2026-06-04"},
                    "technical": {"status": "technical_strong", "basis": "quantdinger_trend_plus_daily_indicators", "summary": {"supportive_count": 4, "neutral_count": 0, "caution_count": 0, "data_insufficient_count": 0}, "strategies": [{"id": "ma", "state": "supportive"}, {"id": "rsi", "state": "supportive"}, {"id": "macd", "state": "supportive"}, {"id": "bollinger", "state": "supportive"}], "warnings": []},
                    "decision": {
                        "code": "new_watch",
                        "label": "新增观察",
                        "priority": "high",
                        "reason": "qlib top10 且 QuantDinger 趋势偏强，进入优先复盘队列。",
                    },
                }
            ],
            "summary": {
                "new_watch": 1,
                "continue_watch": 0,
                "risk_review": 0,
                "manual_review": 0,
                "observe_only": 0,
                "data_insufficient": 0,
            },
            "trading": {
                "orders_enabled": False,
                "connects_to_broker": False,
                "paper_orders_enabled": False,
                "live_trading_enabled": False,
                "quick_trade_enabled": False,
                "writes_orders": False,
                "writes_positions": False,
                "research_signal_not_order": True,
            },
        }


def test_rank_tech_cross_latest_api_contract_and_params(client, monkeypatch):
    fake = FakeRankTechCrossService()
    from app.routes import tw_stock as tw_stock_route

    monkeypatch.setattr(tw_stock_route, "rank_tech_cross_service", fake)
    resp = client.get("/api/tw-stock/rank-tech-cross/latest?bucket=top50&limit=9&maxItems=4&includeTechnicalStrategies=true&technicalStrategies=ma,rsi")
    payload = resp.get_json()

    assert resp.status_code == 200
    assert payload["code"] == 1
    assert fake.calls == [("top50", 20, 4, True, ["ma", "rsi"])]
    data = payload["data"]
    assert data["simulation_only"] is True
    assert data["research_signal_not_order"] is True
    assert data["summary"]["new_watch"] == 1
    assert data["items"][0]["decision"]["code"] == "new_watch"
    assert data["items"][0]["decision"]["label"] == "新增观察"
    assert data["items"][0]["technical"]["basis"] == "quantdinger_trend_plus_daily_indicators"
    assert {item["id"] for item in data["items"][0]["technical"]["strategies"]} == {"ma", "rsi", "macd", "bollinger"}
    assert data["trading"]["orders_enabled"] is False
    assert data["trading"]["connects_to_broker"] is False
    assert data["trading"]["quick_trade_enabled"] is False
    assert data["trading"]["writes_orders"] is False
    assert data["trading"]["writes_positions"] is False


def test_rank_tech_cross_latest_api_blocked_response(client, monkeypatch):
    class BlockedService(FakeRankTechCrossService):
        def latest(self, **kwargs):
            return {
                "ok": False,
                "status": "missing_latest_signal",
                "message": "fixture blocked",
                "simulation_only": True,
                "research_signal_not_order": True,
                "items": [],
                "summary": {
                    "new_watch": 0,
                    "continue_watch": 0,
                    "risk_review": 0,
                    "manual_review": 0,
                    "observe_only": 0,
                    "data_insufficient": 0,
                },
                "trading": {"orders_enabled": False, "connects_to_broker": False, "writes_orders": False, "writes_positions": False, "research_signal_not_order": True},
            }

    from app.routes import tw_stock as tw_stock_route

    monkeypatch.setattr(tw_stock_route, "rank_tech_cross_service", BlockedService())
    resp = client.get("/api/tw-stock/rank-tech-cross/latest")
    payload = resp.get_json()

    assert resp.status_code == 200
    assert payload["code"] == 0
    assert payload["data"]["status"] == "missing_latest_signal"
    assert payload["data"]["simulation_only"] is True
    assert payload["data"]["research_signal_not_order"] is True
    assert payload["data"]["items"] == []
    assert payload["data"]["trading"]["orders_enabled"] is False
    assert payload["data"]["trading"]["writes_orders"] is False


def test_rank_tech_cross_api_source_uses_get_and_no_dangerous_write_route():
    source = Path("backend/app/routes/tw_stock.py").read_text()
    assert '@tw_stock_bp.route("/rank-tech-cross/latest", methods=["GET"])' in source
    route_slice = source.split('@tw_stock_bp.route("/rank-tech-cross/latest"', 1)[1].split('@tw_stock_bp.route("/rank-tech-cross/observation-replay"', 1)[0]
    forbidden = ["methods=[\"POST\"]", "confirm(", "draft(", "BacktestService", "portfolio-replay", "trigger_dry_run", "save_review", "import_latest", "monitor scan", "alerts", "publish", "refresh"]
    assert not any(term in route_slice for term in forbidden)
