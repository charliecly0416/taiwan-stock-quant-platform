"""API tests for observation-only TWStock replay."""
from __future__ import annotations

from pathlib import Path


class FakeObservationReplayService:
    def __init__(self) -> None:
        self.calls = []

    def compare(self, *, start_date: str, end_date: str, bucket: str, max_items: int, technical_strategies=None):
        self.calls.append((start_date, end_date, bucket, max_items, technical_strategies))
        return {
            "ok": True,
            "status": "accepted",
            "simulation_only": True,
            "research_signal_not_order": True,
            "replay_type": "observation_only",
            "performance_metrics_included": False,
            "range": {"startDate": start_date, "endDate": end_date, "runCount": 1},
            "comparison": {
                "qlib_only": {"new_watch_count": 1, "manual_review_count": 0, "data_insufficient_count": 0, "item_count": 2},
                "qlib_plus_trend": {"new_watch_count": 1, "manual_review_count": 1, "data_insufficient_count": 0, "item_count": 2},
                "qlib_plus_trend_indicators": {"new_watch_count": 1, "manual_review_count": 0, "data_insufficient_count": 1, "item_count": 2},
                "qlib_plus_trend_position_risk": {"new_watch_count": 0, "manual_review_count": 1, "data_insufficient_count": 1, "item_count": 2},
            },
            "daily": [
                {
                    "asof": "2026-06-01",
                    "run_id": "run-20260601",
                    "variants": {
                        "qlib_only": {"summary": {"new_watch": 1, "item_count": 2}, "items": []},
                        "qlib_plus_trend": {"summary": {"manual_review": 1, "item_count": 2}, "items": []},
                        "qlib_plus_trend_indicators": {"summary": {"data_insufficient": 1, "item_count": 2}, "items": []},
                        "qlib_plus_trend_position_risk": {"summary": {"manual_review": 1, "item_count": 2}, "items": []},
                    },
                }
            ],
            "dataQuality": {"point_in_time": True, "warnings": []},
            "trading": {
                "orders_enabled": False,
                "connects_to_broker": False,
                "quick_trade_enabled": False,
                "writes_orders": False,
                "writes_positions": False,
                "research_signal_not_order": True,
            },
        }


def test_observation_replay_api_contract_and_params(client, monkeypatch):
    fake = FakeObservationReplayService()
    from app.routes import tw_stock as tw_stock_route

    monkeypatch.setattr(tw_stock_route, "observation_replay_service", fake)
    resp = client.get(
        "/api/tw-stock/rank-tech-cross/observation-replay"
        "?startDate=2026-06-01&endDate=2026-06-05&bucket=top50&maxItems=4&technicalStrategies=ma,macd"
    )
    payload = resp.get_json()

    assert resp.status_code == 200
    assert payload["code"] == 1
    assert fake.calls == [("2026-06-01", "2026-06-05", "top50", 4, ["ma", "macd"])]
    data = payload["data"]
    assert data["simulation_only"] is True
    assert data["research_signal_not_order"] is True
    assert data["performance_metrics_included"] is False
    assert set(data["comparison"]) == {"qlib_only", "qlib_plus_trend", "qlib_plus_trend_indicators", "qlib_plus_trend_position_risk"}
    assert data["dataQuality"]["point_in_time"] is True
    assert data["trading"]["orders_enabled"] is False
    assert data["trading"]["connects_to_broker"] is False
    assert data["trading"]["quick_trade_enabled"] is False
    assert data["trading"]["writes_orders"] is False
    assert data["trading"]["writes_positions"] is False


def test_observation_replay_api_source_get_only_and_no_dangerous_route_terms():
    source = Path("backend/app/routes/tw_stock_replay_routes.py").read_text()
    assert '@tw_stock_replay_bp.route("/rank-tech-cross/observation-replay", methods=["GET"])' in source
    route_slice = source.split('@tw_stock_replay_bp.route("/rank-tech-cross/observation-replay"', 1)[1].split('@tw_stock_replay_bp.route("/rank-tech-cross/portfolio-replay"', 1)[0]
    forbidden = ["methods=[\"POST\"]", "BacktestService", "sim/orders", "portfolio-replay", "monitor scan", "alerts", "publish", "refresh"]
    assert not any(term in route_slice for term in forbidden)
