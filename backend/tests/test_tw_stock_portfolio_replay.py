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
                    "qlib_plus_trend_position_risk": {
                        "items": [
                            {"symbol": "2330", "decision": {"code": "new_watch"}, "positionRisk": {"status": "overheated"}},
                            {"symbol": "2357", "decision": {"code": "risk_review"}, "positionRisk": {"status": "reasonable"}},
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
                    "qlib_plus_trend_position_risk": {
                        "items": [
                            {"symbol": "2330", "decision": {"code": "risk_review"}, "positionRisk": {"status": "overheated"}},
                            {"symbol": "2357", "decision": {"code": "data_insufficient"}, "positionRisk": {"status": "reasonable"}},
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
    assert set(payload["comparison"]) == {"qlib_only", "qlib_plus_trend", "qlib_plus_trend_indicators", "qlib_plus_trend_position_risk"}
    for variant in payload["comparison"].values():
        assert set(variant["metrics"]) == {"totalReturn", "maxDrawdown", "actionCount", "addActionCount", "riskActionCount", "feeAndTax", "finalEquity"}
        assert variant["equityCurve"]
        assert "positionRiskSummary" in variant
        assert all("order_id" not in action and "trade_uid" not in action for action in variant["historicalActions"])
    assert set(payload["strategyComparison"]) == {"rank_rotate_top30", "rank_rotate_top50", "rank_rotate_top50_adaptive_score", "rank_rotate_top50_adaptive_score_risk_control", "confirmed_exit"}
    for strategy in payload["strategyComparison"].values():
        assert strategy["profile"]["label"]
        assert strategy["metrics"]["actionCount"] >= 0
    assert payload["comparison"]["qlib_plus_trend_position_risk"]["positionRiskSummary"]["blocked_overheated_adds"] >= 1
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
            for name in ["qlib_only", "qlib_plus_trend", "qlib_plus_trend_indicators", "qlib_plus_trend_position_risk"]
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


def test_portfolio_replay_uses_action_plan_to_avoid_chasing_adds():
    daily = [{
        "asof": "2026-06-01",
        "variants": {
            name: {"items": [
                {"symbol": "2330", "decision": {"code": "new_watch"}, "actionPlan": {"code": "wait_pullback"}, "positionRisk": {"status": "elevated"}},
                {"symbol": "2357", "decision": {"code": "new_watch"}, "actionPlan": {"code": "simulate_watch"}, "positionRisk": {"status": "reasonable"}},
            ]}
            for name in ["qlib_plus_trend_position_risk"]
        },
    }]
    service = TWStockPortfolioReplayService(observation_service=FakeObservationService(daily=daily), kline_service=FakeKlineService())
    payload = service.replay(config={"startDate": "2026-06-01", "endDate": "2026-06-01", "variant": "qlib_plus_trend_position_risk", "initialCash": 100000, "maxHoldings": 2, "lotSize": 10})
    actions = payload["comparison"]["qlib_plus_trend_position_risk"]["historicalActions"]

    assert any(item["symbol"] == "2357" and item["action"] == "historical_add" for item in actions)
    assert not any(item["symbol"] == "2330" and item["action"] == "historical_add" for item in actions)


def test_strategy_comparison_replays_entry_and_exit_rules():
    daily = [
        {
            "asof": "2026-06-01",
            "variants": {
                "qlib_plus_trend_position_risk": {"items": [
                    {"symbol": "2330", "decision": {"code": "new_watch"}, "actionPlan": {"code": "simulate_watch"}, "technical": {"status": "technical_strong"}, "positionRisk": {"status": "elevated", "metrics": {"distance_ma20_pct": 9}}},
                    {"symbol": "2357", "decision": {"code": "new_watch"}, "actionPlan": {"code": "simulate_watch"}, "technical": {"status": "technical_strong"}, "positionRisk": {"status": "reasonable", "metrics": {"distance_ma20_pct": 2}}},
                ]}
            },
        },
        {
            "asof": "2026-06-02",
            "variants": {
                "qlib_plus_trend_position_risk": {"items": [
                    {"symbol": "2357", "decision": {"code": "risk_review"}, "actionPlan": {"code": "risk_review"}, "technical": {"status": "technical_weak"}, "positionRisk": {"status": "pullback_watch", "metrics": {}}},
                ]}
            },
        },
    ]
    service = TWStockPortfolioReplayService(observation_service=FakeObservationService(daily=daily), kline_service=FakeKlineService())
    payload = service.replay(config={"startDate": "2026-06-01", "endDate": "2026-06-02", "initialCash": 100000, "maxHoldings": 2, "lotSize": 10})

    confirmed_actions = payload["strategyComparison"]["confirmed_exit"]["historicalActions"]

    assert not any(item["action"] == "historical_risk_reduce" for item in confirmed_actions)


class CaptureObservationService(FakeObservationService):
    def __init__(self):
        super().__init__(daily=[])
        self.kwargs = None

    def compare(self, **kwargs):
        self.kwargs = kwargs
        return super().compare(**kwargs)


def test_portfolio_replay_passes_historical_signal_root_and_uses_next_close_by_default():
    daily = [{
        "asof": "2026-06-01",
        "variants": {
            "qlib_only": {"items": [
                {"symbol": "2330", "decision": {"code": "new_watch"}},
            ]}
        },
    }]
    service = TWStockPortfolioReplayService(observation_service=FakeObservationService(daily=daily), kline_service=FakeKlineService())
    payload = service.replay(config={"startDate": "2026-06-01", "endDate": "2026-06-01", "variant": "qlib_only", "initialCash": 100000, "maxHoldings": 1, "lotSize": 10})
    add = next(item for item in payload["comparison"]["qlib_only"]["historicalActions"] if item["action"] == "historical_add")

    assert payload["execution"]["mode"] == "next_trading_day_close"
    assert payload["execution"]["lookahead_guard"] is True
    assert add["price"] == 110

    capture = CaptureObservationService()
    TWStockPortfolioReplayService(observation_service=capture, kline_service=FakeKlineService()).replay(config={"startDate": "2026-06-01", "endDate": "2026-06-01", "signalRoot": "/tmp/backfill-root"})
    assert capture.kwargs["signal_root"] == "/tmp/backfill-root"



def test_rank_rotation_sells_lowest_rank_breach_and_buys_best_top10_once_per_day():
    daily = [
        {
            "asof": "2026-06-01",
            "variants": {
                "qlib_only": {"items": [
                    {"symbol": "2330", "rank": 1, "decision": {"code": "new_watch"}},
                    {"symbol": "2357", "rank": 2, "decision": {"code": "new_watch"}},
                ]}
            },
        },
        {
            "asof": "2026-06-02",
            "variants": {
                "qlib_only": {"items": [
                    {"symbol": "2357", "rank": 1, "decision": {"code": "new_watch"}},
                    {"symbol": "2330", "rank": 8, "decision": {"code": "new_watch"}},
                    {"symbol": "2409", "rank": 9, "decision": {"code": "new_watch"}},
                ]}
            },
        },
        {
            "asof": "2026-06-03",
            "variants": {
                "qlib_only": {"items": [
                    {"symbol": "2454", "rank": 1, "decision": {"code": "new_watch"}},
                    {"symbol": "2330", "rank": 8, "decision": {"code": "new_watch"}},
                    {"symbol": "2409", "rank": 35, "decision": {"code": "observe_only"}},
                    {"symbol": "2357", "rank": 60, "decision": {"code": "observe_only"}},
                ]}
            },
        },
    ]

    class RotationKlineService(FakeKlineService):
        def get_kline(self, market, symbol, timeframe, limit):
            prices = {
                "2330": [("2026-06-01", 100), ("2026-06-02", 101), ("2026-06-03", 102), ("2026-06-04", 103)],
                "2357": [("2026-06-01", 50), ("2026-06-02", 51), ("2026-06-03", 52), ("2026-06-04", 53)],
                "2409": [("2026-06-01", 20), ("2026-06-02", 21), ("2026-06-03", 22), ("2026-06-04", 23)],
                "2454": [("2026-06-01", 80), ("2026-06-02", 81), ("2026-06-03", 82), ("2026-06-04", 83)],
            }
            return [{"date": day, "close": close, "time": idx + 1} for idx, (day, close) in enumerate(prices.get(symbol, []))]

    service = TWStockPortfolioReplayService(observation_service=FakeObservationService(daily=daily), kline_service=RotationKlineService())
    payload = service.replay(config={"startDate": "2026-06-01", "endDate": "2026-06-03", "initialCash": 100000, "maxHoldings": 2, "lotSize": 10})

    top30_actions = payload["strategyComparison"]["rank_rotate_top30"]["historicalActions"]
    top50_actions = payload["strategyComparison"]["rank_rotate_top50"]["historicalActions"]

    day3_top30 = [item for item in top30_actions if item["date"] == "2026-06-03" and item["action"] in {"historical_add", "historical_risk_reduce"}]
    day3_top50 = [item for item in top50_actions if item["date"] == "2026-06-03" and item["action"] in {"historical_add", "historical_risk_reduce"}]

    assert [item["action"] for item in day3_top30] == ["historical_risk_reduce", "historical_add"]
    assert day3_top30[0]["symbol"] == "2357"
    assert day3_top30[1]["symbol"] == "2454"
    assert [item["action"] for item in day3_top50] == ["historical_risk_reduce", "historical_add"]
    assert day3_top50[0]["symbol"] == "2357"
    assert day3_top50[1]["symbol"] == "2454"


def test_rank_rotation_top30_exits_when_top50_would_hold():
    daily = [
        {"asof": "2026-06-01", "variants": {"qlib_only": {"items": [
            {"symbol": "2330", "rank": 1, "decision": {"code": "new_watch"}},
        ]}}},
        {"asof": "2026-06-02", "variants": {"qlib_only": {"items": [
            {"symbol": "2454", "rank": 1, "decision": {"code": "new_watch"}},
            {"symbol": "2330", "rank": 35, "decision": {"code": "observe_only"}},
        ]}}},
    ]

    class RotationKlineService(FakeKlineService):
        def get_kline(self, market, symbol, timeframe, limit):
            prices = {
                "2330": [("2026-06-01", 100), ("2026-06-02", 101), ("2026-06-03", 102)],
                "2454": [("2026-06-01", 80), ("2026-06-02", 81), ("2026-06-03", 82)],
            }
            return [{"date": day, "close": close, "time": idx + 1} for idx, (day, close) in enumerate(prices.get(symbol, []))]

    service = TWStockPortfolioReplayService(observation_service=FakeObservationService(daily=daily), kline_service=RotationKlineService())
    payload = service.replay(config={"startDate": "2026-06-01", "endDate": "2026-06-02", "initialCash": 100000, "maxHoldings": 1, "lotSize": 10})

    top30_actions = payload["strategyComparison"]["rank_rotate_top30"]["historicalActions"]
    top50_actions = payload["strategyComparison"]["rank_rotate_top50"]["historicalActions"]

    assert any(item["date"] == "2026-06-02" and item["symbol"] == "2330" and item["action"] == "historical_risk_reduce" for item in top30_actions)
    assert not any(item["date"] == "2026-06-02" and item["symbol"] == "2330" and item["action"] == "historical_risk_reduce" for item in top50_actions)

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


class CautionMarketKlineService(FakeKlineService):
    def get_kline(self, market, symbol, timeframe, limit):
        if symbol in {"TWII", "II"}:
            rows = []
            close = 200.0
            for idx in range(140):
                day = f"2026-01-{(idx % 28) + 1:02d}" if idx < 28 else f"2026-{(idx // 28) + 1:02d}-{(idx % 28) + 1:02d}"
                close -= 1.0
                rows.append({"date": day, "close": close, "time": idx + 1})
            return rows
        prices = {
            "2330": [("2026-06-01", 100), ("2026-06-02", 101)],
            "2357": [("2026-06-01", 50), ("2026-06-02", 51)],
        }
        return [{"date": day, "close": close, "time": idx + 1} for idx, (day, close) in enumerate(prices.get(symbol, []))]


def test_adaptive_score_rotation_inherits_top50_and_skips_uncalibrated_score_in_caution_market():
    daily = [{
        "asof": "2026-06-01",
        "variants": {
            "qlib_only": {"items": [
                {"symbol": "2330", "rank": 1, "score": 0.095, "qlib": {"score": 0.095}, "decision": {"code": "new_watch"}},
                {"symbol": "2357", "rank": 2, "score": 0.055, "qlib": {"score": 0.055}, "decision": {"code": "new_watch"}},
            ]}
        },
    }]
    payload = TWStockPortfolioReplayService(
        observation_service=FakeObservationService(daily=daily),
        kline_service=CautionMarketKlineService(),
    ).replay(config={"startDate": "2026-06-01", "endDate": "2026-06-01", "initialCash": 100000, "maxHoldings": 2, "lotSize": 10})

    strategy = payload["strategyComparison"]["rank_rotate_top50_adaptive_score"]
    actions = strategy["historicalActions"]

    assert strategy["profile"]["label"] == "Top50 自适应 score"
    assert strategy["adaptiveScoreSummary"]["enabled"] is True
    assert strategy["adaptiveScoreSummary"]["blocked_adds"] >= 1
    assert any(item["symbol"] == "2330" and item["action"] == "historical_skip" for item in actions)
    assert any(item["symbol"] == "2357" and item["action"] == "historical_add" for item in actions)
