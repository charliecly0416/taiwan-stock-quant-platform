"""Service tests for read-only TWStock rank-tech cross classification."""
from __future__ import annotations

from pathlib import Path

import pytest

from app.services.tw_stock_qlib_option_c import QlibOptionCSignalError
from app.services.tw_stock_rank_tech_cross import TWStockRankTechCrossService


class FakeQlibReader:
    def latest(self, *, bucket: str, enrich_trend: bool = False):
        assert enrich_trend is False
        rows = [
            {"symbol": "2330", "instrument": "TW2330", "name": "台积电", "rank": 1, "bucket": bucket, "qlib_score": 0.9},
            {"symbol": "6290", "instrument": "TW6290", "name": "良维", "rank": 12, "bucket": bucket, "qlib_score": 0.7},
            {"symbol": "2357", "instrument": "TW2357", "name": "华硕", "rank": 23, "bucket": bucket, "qlib_score": 0.6},
            {"symbol": "2303", "instrument": "TW2303", "name": "联电", "rank": 35, "bucket": bucket, "qlib_score": 0.5},
            {"symbol": "9999", "instrument": "TW9999", "name": "测试", "rank": 45, "bucket": bucket, "qlib_score": 0.4},
        ]
        return {
            "ok": True,
            "status": "accepted",
            "asof": "2026-06-04",
            "run_id": "run-1",
            "recorder_id": "950741cfd5f14ee5a05464fec3e12e0a",
            "target_horizon": "next_trading_day_research_ranking",
            "target_date": "2026-06-05",
            "signal_semantics": "research_only_cross_sectional_ranking",
            "recommendation_semantics": "watchlist_not_trade_advice",
            "signals": rows,
            "warnings": [],
        }


class BlockedQlibReader:
    def latest(self, *, bucket: str, enrich_trend: bool = False):
        raise QlibOptionCSignalError("missing_latest_signal", "fixture missing", warnings=["missing_fixture"])


class FakeTrendService:
    LABELS = {
        "2330": "uptrend",
        "6290": "sideways",
        "2357": "downtrend",
        "2303": "rebound",
    }

    def analyze_symbol(self, *, symbol: str, limit: int = 120, as_of=None):
        if symbol == "9999":
            return {"ok": False, "error": "no_daily_bars", "quality": {"warnings": ["no_daily_bars"]}}
        label = self.LABELS.get(symbol, "unknown")
        return {
            "ok": True,
            "symbol": symbol,
            "latest": {"date": "2026-06-04"},
            "trend": {"label": label, "score": 71.5},
            "quality": {"warnings": [], "latest_date": "2026-06-04"},
        }


class FakeTechnicalService:
    STATUS = {
        "2330": "technical_strong",
        "6290": "technical_neutral",
        "2357": "technical_strong",
        "2303": "technical_strong",
        "9999": "technical_data_insufficient",
    }

    def analyze_symbol(self, *, symbol: str, limit: int = 120, strategies=None, as_of=None):
        status = self.STATUS.get(symbol, "technical_neutral")
        states = {
            "technical_strong": ["supportive", "supportive", "supportive", "supportive"],
            "technical_weak": ["caution", "caution", "neutral", "neutral"],
            "technical_neutral": ["supportive", "neutral", "neutral", "caution"],
            "technical_data_insufficient": ["data_insufficient", "data_insufficient", "data_insufficient", "data_insufficient"],
        }[status]
        ids = ["ma", "rsi", "macd", "bollinger"]
        warnings = ["ma_data_insufficient"] if status == "technical_data_insufficient" else []
        return {
            "ok": True,
            "status": status,
            "summary": {
                "supportive_count": states.count("supportive"),
                "neutral_count": states.count("neutral"),
                "caution_count": states.count("caution"),
                "data_insufficient_count": states.count("data_insufficient"),
            },
            "strategies": [{"id": item, "label": item.upper(), "state": state, "metrics": {}, "reason": "fixture"} for item, state in zip(ids, states)],
            "positionRisk": {"status": "reasonable", "label": "位置合理", "score": 35, "reason": "fixture", "metrics": {}, "warnings": []},
            "warnings": warnings,
        }




class HotTechnicalService(FakeTechnicalService):
    def analyze_symbol(self, *, symbol: str, limit: int = 120, strategies=None, as_of=None):
        payload = super().analyze_symbol(symbol=symbol, limit=limit, strategies=strategies, as_of=as_of)
        if symbol == "2330":
            payload["positionRisk"] = {"status": "overheated", "label": "过热谨慎", "score": 88, "reason": "fixture", "metrics": {}, "warnings": []}
        return payload

class WeakTechnicalService(FakeTechnicalService):
    STATUS = {
        "2330": "technical_weak",
        "6290": "technical_neutral",
        "2357": "technical_strong",
        "2303": "technical_strong",
        "9999": "technical_data_insufficient",
    }


def test_rank_tech_cross_latest_classification_matrix():
    service = TWStockRankTechCrossService(qlib_reader=FakeQlibReader(), trend_service=FakeTrendService())
    payload = service.latest(bucket="top50", limit=9, max_items=5, include_technical_strategies=False)
    by_symbol = {item["symbol"]: item for item in payload["items"]}

    assert payload["ok"] is True
    assert payload["simulation_only"] is True
    assert payload["research_signal_not_order"] is True
    assert payload["limit"] == 20
    assert by_symbol["2330"]["rankTier"] == "top10"
    assert by_symbol["2330"]["technical"]["status"] == "technical_strong"
    assert by_symbol["2330"]["decision"]["code"] == "new_watch"
    assert by_symbol["2330"]["actionPlan"]["code"] == "continue_observe"
    assert by_symbol["6290"]["decision"]["code"] == "continue_watch"
    assert by_symbol["2357"]["decision"]["code"] == "manual_review"
    assert by_symbol["2303"]["rankTier"] == "top50"
    assert by_symbol["2303"]["decision"]["code"] == "observe_only"
    assert by_symbol["9999"]["decision"]["code"] == "data_insufficient"
    assert payload["summary"] == {
        "new_watch": 1,
        "continue_watch": 1,
        "risk_review": 0,
        "manual_review": 1,
        "observe_only": 1,
        "data_insufficient": 1,
    }
    assert payload["trading"]["orders_enabled"] is False
    assert payload["trading"]["connects_to_broker"] is False
    assert payload["trading"]["quick_trade_enabled"] is False
    assert payload["trading"]["writes_orders"] is False
    assert payload["trading"]["writes_positions"] is False


def test_rank_tech_cross_includes_daily_indicator_technical_status_by_default():
    service = TWStockRankTechCrossService(
        qlib_reader=FakeQlibReader(),
        trend_service=FakeTrendService(),
        technical_service=FakeTechnicalService(),
    )
    payload = service.latest(bucket="top50", max_items=5)
    by_symbol = {item["symbol"]: item for item in payload["items"]}

    assert payload["includeTechnicalStrategies"] is True
    assert payload["basis"]["technical_basis"] == "quantdinger_trend_plus_daily_indicators"
    assert by_symbol["2330"]["technical"]["basis"] == "quantdinger_trend_plus_daily_indicators"
    assert {item["id"] for item in by_symbol["2330"]["technical"]["strategies"]} == {"ma", "rsi", "macd", "bollinger"}
    assert by_symbol["2357"]["technical"]["status"] == "technical_neutral"
    assert by_symbol["2357"]["decision"]["code"] != "new_watch"
    assert by_symbol["9999"]["technical"]["warnings"] == ["no_daily_bars", "ma_data_insufficient"]


def test_rank_tech_cross_strong_trend_with_weak_indicators_is_not_new_watch():
    service = TWStockRankTechCrossService(
        qlib_reader=FakeQlibReader(),
        trend_service=FakeTrendService(),
        technical_service=WeakTechnicalService(),
    )
    payload = service.latest(bucket="top50", max_items=1)
    item = payload["items"][0]

    assert item["symbol"] == "2330"
    assert item["trend"]["label"] == "uptrend"
    assert item["technical"]["status"] == "technical_neutral"
    assert item["decision"]["code"] != "new_watch"



def test_rank_tech_cross_top_rank_strong_but_overheated_is_manual_review():
    service = TWStockRankTechCrossService(
        qlib_reader=FakeQlibReader(),
        trend_service=FakeTrendService(),
        technical_service=HotTechnicalService(),
    )
    payload = service.latest(bucket="top50", max_items=1)
    item = payload["items"][0]

    assert item["symbol"] == "2330"
    assert item["technical"]["status"] == "technical_strong"
    assert item["positionRisk"]["status"] == "overheated"
    assert item["decision"]["code"] == "manual_review"
    assert item["actionPlan"]["code"] == "chasing_review"
    assert "过热谨慎" in item["decision"]["reason"]


def test_rank_tech_cross_action_plan_separates_selection_from_timing():
    reasonable = TWStockRankTechCrossService.action_plan_for(
        rank_tier="top10",
        technical_status="technical_strong",
        trend_label="uptrend",
        position_risk={"status": "reasonable", "label": "位置合理"},
        decision={"code": "new_watch"},
    )
    elevated = TWStockRankTechCrossService.action_plan_for(
        rank_tier="top10",
        technical_status="technical_strong",
        trend_label="uptrend",
        position_risk={"status": "elevated", "label": "强势但偏高"},
        decision={"code": "continue_watch"},
    )
    overheated = TWStockRankTechCrossService.action_plan_for(
        rank_tier="top10",
        technical_status="technical_strong",
        trend_label="uptrend",
        position_risk={"status": "overheated", "label": "过热谨慎"},
        decision={"code": "manual_review"},
    )
    weak = TWStockRankTechCrossService.action_plan_for(
        rank_tier="outside_top50",
        technical_status="technical_weak",
        trend_label="downtrend",
        position_risk={"status": "pullback_watch", "label": "回调观察"},
        decision={"code": "risk_review"},
    )

    assert reasonable["code"] == "simulate_watch"
    assert elevated["code"] == "wait_pullback"
    assert overheated["code"] == "chasing_review"
    assert weak["code"] == "risk_review"
    assert all(item["research_only"] and item["simulation_only"] for item in [reasonable, elevated, overheated, weak])


def test_rank_tech_cross_outside_top50_contract_decisions():
    weak = TWStockRankTechCrossService.decision_for(rank_tier="outside_top50", technical_status="technical_weak")
    strong = TWStockRankTechCrossService.decision_for(rank_tier="outside_top50", technical_status="technical_strong")

    assert weak["code"] == "risk_review"
    assert strong["code"] == "manual_review"


def test_rank_tech_cross_blocked_payload_does_not_raise():
    service = TWStockRankTechCrossService(qlib_reader=BlockedQlibReader(), trend_service=FakeTrendService())
    payload = service.latest(bucket="top30")

    assert payload["ok"] is False
    assert payload["status"] == "missing_latest_signal"
    assert payload["items"] == []
    assert payload["summary"]["new_watch"] == 0
    assert payload["simulation_only"] is True
    assert payload["research_signal_not_order"] is True
    assert payload["trading"]["orders_enabled"] is False
    assert payload["trading"]["writes_orders"] is False


def test_rank_tech_cross_user_visible_decision_text_avoids_actionable_terms():
    service = TWStockRankTechCrossService(qlib_reader=FakeQlibReader(), trend_service=FakeTrendService())
    payload = service.latest(bucket="top50", max_items=5)
    text = "\n".join(f"{item['decision']['label']} {item['decision']['reason']}" for item in payload["items"])
    forbidden = ["立即买入", "立即卖出", "自动买入", "自动卖出", "提交订单", "连接券商", "目标仓位", "上涨概率", "收益承诺"]

    assert not any(term in text for term in forbidden)


def test_rank_tech_cross_service_source_has_no_write_paths():
    source = Path("backend/app/services/tw_stock_rank_tech_cross.py").read_text()
    forbidden = [
        "connect_broker(",
        "broker_client",
        "quick_trade",
        "qd_tw_sim_orders",
        "qd_tw_sim_trades",
        "qd_tw_sim_positions",
        "target_position",
        "target_weight",
        "accepted_latest_scheduler.tick",
        "option_c_ops_runner.trigger",
        "option_c_eod_pipeline",
        "monitor_scan",
        "alerts write",
    ]

    assert not any(term in source for term in forbidden)
