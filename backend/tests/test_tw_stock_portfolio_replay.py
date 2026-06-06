"""Tests for in-memory TWStock portfolio rule replay."""
from __future__ import annotations

from pathlib import Path

from app.services.tw_stock_portfolio_replay import TWStockPortfolioReplayService


class FakeObservationService:
    def __init__(self, daily=None, warnings=None):
        self.daily = daily if daily is not None else [
            {
                "asof": "2026-06-01",
                "variants": {
                    "qlib_only": {
                        "items": [
                            {"symbol": "2330", "decision": {"code": "new_watch"}},
                            {"symbol": "2357", "decision": {"code": "manual_review"}},
                        ]
                    },
                    "qlib_plus_trend": {
                        "items": [
                            {"symbol": "2330", "decision": {"code": "new_watch"}},
                            {"symbol": "2357", "decision": {"code": "data_insufficient"}},
                        ]
                    },
                    "qlib_plus_trend_indicators": {
                        "items": [
                            {"symbol": "2330", "decision": {"code": "new_watch"}},
                            {"symbol": "2357", "decision": {"code": "risk_review"}},
                        ]
                    },
                },
            },
            {
                "asof": "2026-06-02",
                "variants": {
                    "qlib_only": {
                        "items": [
                            {"symbol": "2330", "decision": {"code": "continue_watch"}},
                            {"symbol": "2357", "decision": {"code": "new_watch"}},
                        ]
                    },
                    "qlib_plus_trend": {
                        "items": [
                            {"symbol": "2330", "decision": {"code": "risk_review"}},
                            {"symbol": "2357", "decision": {"code": "manual_review"}},
                        ]
                    },
                    "qlib_plus_trend_indicators": {
                        "items": [
                            {"symbol": "2330", "decision": {"code": "risk_review"}},
                            {"symbol": "2357", "decision": {"code": "data_insufficient"}},
                        ]
                    },
                },
            },
        ]
        self.warnings = warnings or []

    def compare(self, **kwargs):
        return {"ok": True, "daily": self.daily, "dataQuality": {"point_in_time": True, "warnings": self.warnings}}


class FakeKlineService:
    def get_kline(self, market, symbol, timeframe, limit):
        prices = {
            "2330": [("2026-06-01", 100), ("2026-06-02", 110)],
            "2357": [("2026-06-01", 50), ("2026-06-02", 48)],
        }
        return [{"date": day, "close": close, "time": idx + 1} for idx, (day, close) in enumerate(prices.get(symbol, []))]


class MissingPriceKlineService(FakeKlineService):
    def get_kline(self, market, symbol, timeframe, limit):
        if symbol == "2357":
            return []
        return super().get_kline(market, symbol, timeframe, limit)


def test_portfolio_replay_returns_metrics_for_three_variants_and_forces_no_persist():
    service = TWStockPortfolioReplayService(observation_service=FakeObservationService(), kline_service=FakeKlineService())
    payload = service.replay(config={"startDate": "2026-06-01", "endDate": "2026-06-02", "persist": True, "initialCash": 100000, "maxHoldings": 2, "lotSize": 10})

    assert payload["ok"] is True
    assert payload["simulation_only"] is True
    assert payload["persist"] is False
    assert payload["writes_business_db"] is False
    assert set(payload["comparison"]) == {"qlib_only", "qlib_plus_trend", "qlib_plus_trend_indicators"}
    for variant in payload["comparison"].values():
        assert set(variant["metrics"]) == {"totalReturn", "maxDrawdown", "actionCount", "addActionCount", "riskActionCount", "feeAndTax", "finalEquity"}
        assert variant["equityCurve"]
        assert all("order_id" not in action and "trade_uid" not in action for action in variant["historicalActions"])
    assert payload["trading"]["orders_enabled"] is False
    assert payload["trading"]["writes_orders"] is False
    assert payload["trading"]["writes_positions"] is False


def test_manual_review_and_data_insufficient_do_not_add_or_reduce():
    daily = [{
        "asof": "2026-06-01",
        "variants": {
            name: {"items": [
                {"symbol": "2330", "decision": {"code": "manual_review"}},
                {"symbol": "2357", "decision": {"code": "data_insufficient"}},
            ]}
            for name in ["qlib_only", "qlib_plus_trend", "qlib_plus_trend_indicators"]
        },
    }]
    service = TWStockPortfolioReplayService(observation_service=FakeObservationService(daily=daily), kline_service=FakeKlineService())
    payload = service.replay(config={"startDate": "2026-06-01", "endDate": "2026-06-01"})

    for variant in payload["comparison"].values():
        assert variant["metrics"]["actionCount"] == 0
        assert {item["action"] for item in variant["historicalActions"]} == {"historical_skip"}


def test_no_accepted_runs_and_missing_price_are_clear_warnings():
    empty = TWStockPortfolioReplayService(
        observation_service=FakeObservationService(daily=[], warnings=["no_accepted_runs_in_range"]),
        kline_service=FakeKlineService(),
    ).replay(config={"startDate": "2026-06-01", "endDate": "2026-06-02"})
    assert "no_accepted_runs_in_range" in empty["dataQuality"]["warnings"]

    missing = TWStockPortfolioReplayService(
        observation_service=FakeObservationService(),
        kline_service=MissingPriceKlineService(),
    ).replay(config={"startDate": "2026-06-01", "endDate": "2026-06-02"})
    assert any(str(item).startswith("missing_close") for item in missing["dataQuality"]["warnings"])


def test_portfolio_replay_source_has_no_business_writes_or_dangerous_paths():
    source = Path("backend/app/services/tw_stock_portfolio_replay.py").read_text()
    forbidden = [
        "INSERT INTO",
        "UPDATE",
        "DELETE",
        "qd_tw_sim_orders",
        "qd_tw_sim_trades",
        "qd_tw_sim_positions",
        "broker",
        "quick_trade",
        "target_position",
        "target_weight",
        "accepted_latest",
        "provider_publish",
        "立即买入",
        "立即卖出",
        "自动买入",
        "自动卖出",
        "下单",
        "提交订单",
        "目标仓位",
        "上涨概率",
        "收益承诺",
        "order instruction",
    ]
    assert not any(term in source for term in forbidden)
