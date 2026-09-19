"""API tests for in-memory TWStock portfolio replay."""
from __future__ import annotations

from pathlib import Path


class FakePortfolioReplayService:
    def __init__(self) -> None:
        self.calls = []

    def replay(self, *, config):
        self.calls.append(config)
        return {
            "ok": True,
            "status": "accepted",
            "simulation_only": True,
            "research_signal_not_order": True,
            "replay_type": "portfolio_rule_historical_simulation",
            "persist": False,
            "writes_business_db": False,
            "comparison": {
                "qlib_only": {
                    "metrics": {
                        "totalReturn": 0.01,
                        "maxDrawdown": -0.02,
                        "actionCount": 1,
                        "addActionCount": 1,
                        "riskActionCount": 0,
                        "feeAndTax": 12.3,
                        "finalEquity": 101000,
                    },
                    "equityCurve": [{"date": "2026-06-01", "equity": 101000}],
                    "historicalActions": [{"date": "2026-06-01", "action": "historical_add", "simulation_only": True}],
                    "dataQuality": {"warnings": []},
                }
            },
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


def test_portfolio_replay_api_contract(client, monkeypatch):
    fake = FakePortfolioReplayService()
    from app.routes import tw_stock as tw_stock_route

    monkeypatch.setattr(tw_stock_route, "portfolio_replay_service", fake)
    resp = client.post(
        "/api/tw-stock/rank-tech-cross/portfolio-replay",
        json={"startDate": "2026-06-01", "endDate": "2026-06-02", "persist": True, "initialCash": 100000},
    )
    payload = resp.get_json()

    assert resp.status_code == 200
    assert payload["code"] == 1
    assert fake.calls[0]["persist"] is True
    data = payload["data"]
    assert data["simulation_only"] is True
    assert data["research_signal_not_order"] is True
    assert data["persist"] is False
    assert data["writes_business_db"] is False
    assert data["trading"]["orders_enabled"] is False
    assert data["trading"]["connects_to_broker"] is False
    assert data["trading"]["quick_trade_enabled"] is False
    assert data["trading"]["writes_orders"] is False
    assert data["trading"]["writes_positions"] is False


def test_portfolio_replay_route_slice_avoids_write_services():
    source = Path("backend/app/routes/tw_stock_replay_routes.py").read_text()
    assert '@tw_stock_replay_bp.route("/rank-tech-cross/portfolio-replay", methods=["POST"])' in source
    route_slice = source.split('@tw_stock_replay_bp.route("/rank-tech-cross/portfolio-replay"', 1)[1]
    forbidden = ["tw_stock_sim_account_service", "draft(", "confirm(", "BacktestService", "monitor scan", "alerts", "publish", "refresh"]
    assert not any(term in route_slice for term in forbidden)
