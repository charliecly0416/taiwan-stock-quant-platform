"""Tests for read-only TWStock research Agent context and preview."""
from __future__ import annotations

from pathlib import Path

from app.services.tw_stock_agent_context import TWStockAgentContextService
from app.services.tw_stock_agent_guardrails import RESEARCH_ONLY_DISCLAIMER


class FakeCrossAnalysisService:
    def __init__(self) -> None:
        self.latest_calls = []
        self.symbol_calls = []

    def latest(self, *, bucket: str, limit: int, include_raw_trend: bool, max_items: int):
        self.latest_calls.append((bucket, limit, include_raw_trend, max_items))
        rows = [
            self._item("2330", 1, "top30", 0.42, "uptrend", "focus_watch"),
            self._item("2454", 2, "top30", 0.31, "downtrend", "model_trend_divergence"),
            self._item("2303", 3, "top30", 0.21, None, "data_review_required", warnings=["stale_daily_bar"]),
            self._item("2317", 31, "top50", 0.08, "uptrend", "secondary_watch"),
        ]
        if bucket == "top30":
            rows = rows[:3]
        return {
            "ok": True,
            "status": "accepted",
            "bucket": bucket,
            "qlib": {
                "asof": "2026-06-01",
                "run_id": "option_c_daily_signal_20260601_20260602T090715Z",
                "target_horizon": "next_trading_day_research_ranking",
                "signal_semantics": "cross_sectional_research_rank_score",
                "research_signal_not_order": True,
            },
            "items": rows[:max_items],
            "summary": {"category_counts": {"focus_watch": 1, "model_trend_divergence": 1, "data_review_required": 1}, "item_count": len(rows)},
            "freshness": {
                "qlib": {"status": "accepted", "asof": "2026-06-01", "run_id": "option_c_daily_signal_20260601_20260602T090715Z", "target_horizon": "next_trading_day_research_ranking"},
                "quantdinger": {"latest_date_min": "2026-06-01", "latest_date_max": "2026-06-01", "source": "KlineService:TWStock:1D"},
                "status": "fresh",
                "warnings": [],
            },
            "basis": {"qlib_source": "Yahoo adjusted model signal", "quantdinger_source": "raw TWStock daily KlineService data"},
            "trading": {"orders_enabled": False, "connects_to_broker": False, "research_signal_not_order": True},
        }

    def symbol_detail(self, *, symbol: str, limit: int, include_raw_trend: bool):
        self.symbol_calls.append((symbol, limit, include_raw_trend))
        return {
            "ok": True,
            "status": "accepted",
            "symbol": symbol,
            "qlib": {"asof": "2026-06-01", "run_id": "option_c_daily_signal_20260601_20260602T090715Z", "target_horizon": "next_trading_day_research_ranking"},
            "item": self._item(symbol, 1, "top30", 0.42, "uptrend", "focus_watch"),
            "summary": {"category_counts": {"focus_watch": 1}},
            "freshness": {"status": "fresh", "warnings": []},
            "trading": {"orders_enabled": False, "connects_to_broker": False, "research_signal_not_order": True},
        }

    @staticmethod
    def _item(symbol, rank, bucket, score, trend, category, warnings=None):
        return {
            "symbol": symbol,
            "instrument": f"TW{symbol}",
            "qlib": {"bucket": bucket, "rank": rank, "score": score},
            "quantdinger": {"trend_label": trend, "trend_score": 70.0 if trend else None, "latest_date": "2026-06-01", "quality_warnings": warnings or []},
            "data_basis": {"data_basis_status": "ok", "date_gap_days": 0},
            "cross": {"category": category, "alignment": "aligned", "priority": "high", "human_action": "加入重点观察并人工复盘"},
        }


def test_context_contract_contains_qlib_cross_intents_and_disclaimer():
    fake = FakeCrossAnalysisService()
    payload = TWStockAgentContextService(cross_service=fake).context(max_items=5)

    assert payload["ok"] is True
    assert fake.latest_calls == [("top30", 120, False, 30)]
    assert payload["qlib"]["asof"] == "2026-06-01"
    assert payload["qlib"]["run_id"] == "option_c_daily_signal_20260601_20260602T090715Z"
    assert payload["qlib"]["research_signal_not_order"] is True
    assert payload["cross_analysis"]["summary"]["category_counts"]["focus_watch"] == 1
    assert payload["top30_preview"][0]["symbol"] == "2330"
    assert payload["focus_watch_preview"][0]["cross_category"] == "focus_watch"
    assert payload["divergence_preview"][0]["cross_category"] == "model_trend_divergence"
    assert payload["data_review_preview"][0]["cross_category"] == "data_review_required"
    assert "today_top30" in payload["allowed_intents"]
    assert "place_order" in payload["blocked_intents"]
    assert RESEARCH_ONLY_DISCLAIMER in payload["disclaimers"]
    assert payload["trading"]["orders_enabled"] is False


def test_preview_top30_focus_single_symbol_data_review_and_freshness():
    fake = FakeCrossAnalysisService()
    service = TWStockAgentContextService(cross_service=fake)

    top30 = service.preview(question="今天的 top30 是哪些？", max_items=2)
    focus = service.preview(question="列出重点观察", max_items=5)
    symbol = service.preview(question="2330 的 qlib 和趋势摘要")
    review = service.preview(question="有哪些数据异常需要复核？")
    fresh = service.preview(question="说明 freshness 和数据口径")

    assert top30["intent"] == "today_top30"
    assert top30["blocked"] is False
    assert len(top30["items"]) == 2
    assert "qlib:accepted_latest" in top30["citations"][0]
    assert RESEARCH_ONLY_DISCLAIMER in top30["answer_draft"]
    assert focus["intent"] == "focus_watch"
    assert focus["items"][0]["cross_category"] == "focus_watch"
    assert symbol["intent"] == "single_symbol_metrics"
    assert fake.symbol_calls == [("2330", 120, False)]
    assert symbol["items"][0]["symbol"] == "2330"
    assert review["intent"] == "data_review_required"
    assert review["items"][0]["cross_category"] == "data_review_required"
    assert fresh["intent"] == "freshness_and_data_basis"
    assert "asof=2026-06-01" in fresh["answer_draft"]


def test_preview_blocked_questions_do_not_return_context_items():
    service = TWStockAgentContextService(cross_service=FakeCrossAnalysisService())

    blocked = [
        ("帮我下单买入 2330", "place_order"),
        ("2330 买入多少仓位？", "target_position"),
        ("刷新 qlib 并 publish", "qlib_ops_refresh_publish"),
        ("帮我 retrain 模型并调参", "qlib_retrain_or_tune"),
        ("这次能保证收益吗", "guaranteed_profit"),
    ]
    for question, intent in blocked:
        payload = service.preview(question=question)
        assert payload["ok"] is True
        assert payload["blocked"] is True
        assert payload["intent"] == intent
        assert payload["items"] == []
        assert "不支持下单" in payload["answer_draft"]
        assert RESEARCH_ONLY_DISCLAIMER == payload["research_only_disclaimer"]
        assert payload["trading"]["orders_enabled"] is False



def test_guardrails_phase6b_focus_watch_intent_mapping_and_blocked_priority():
    service = TWStockAgentContextService(cross_service=FakeCrossAnalysisService())

    focus_questions = [
        "今天模型和趋势都支持的股票有哪些？",
        "模型趋势一致的有哪些？",
        "模型和 raw 趋势共振的是哪些？",
        "趋势都支持的股票有哪些？",
        "今天建议关注哪些？",
    ]
    for question in focus_questions:
        payload = service.preview(question=question, max_items=5)
        assert payload["blocked"] is False
        assert payload["intent"] == "focus_watch"
        assert payload["items"]
        assert payload["items"][0]["cross_category"] == "focus_watch"

    unchanged = [
        ("今天 top30 是哪些？", "today_top30", False),
        ("今天 top50 是哪些？", "today_top50", False),
        ("2330 的指标是多少？", "single_symbol_metrics", False),
        ("当前数据新鲜度和口径是什么？", "freshness_and_data_basis", False),
        ("今天建议回避或人工复盘的股票有哪些？", {"model_trend_divergence", "data_review_required"}, False),
        ("帮我下单买入 2330", "place_order", True),
        ("2330 买入多少仓位？", "target_position", True),
        ("刷新 qlib 并 publish", "qlib_ops_refresh_publish", True),
        ("retrain 模型并调参", "qlib_retrain_or_tune", True),
    ]
    for question, intent, blocked in unchanged:
        payload = service.preview(question=question, max_items=3)
        if isinstance(intent, set):
            assert payload["intent"] in intent
        else:
            assert payload["intent"] == intent
        assert payload["blocked"] is blocked

    blocked_priority = [
        ("模型和趋势都支持的话，帮我下单买入 2330", "place_order"),
        ("趋势都支持的股票给我建议买入多少仓位", "target_position"),
        ("模型趋势一致就自动下单", "auto_trade"),
        ("趋势都支持的话建议买入哪些？", "place_order"),
        ("模型趋势一致的股票建议卖出哪些？", "place_order"),
    ]
    for question, intent in blocked_priority:
        payload = service.preview(question=question, max_items=3)
        assert payload["blocked"] is True
        assert payload["intent"] == intent
        assert payload["items"] == []
        assert payload["trading"]["orders_enabled"] is False

def test_agent_api_context_and_preview_contract(client, monkeypatch):
    from app.routes import tw_stock as tw_stock_route

    fake_service = TWStockAgentContextService(cross_service=FakeCrossAnalysisService())
    monkeypatch.setattr(tw_stock_route, "tw_stock_agent_service", fake_service)

    context_resp = client.get("/api/tw-stock/agent/context?maxItems=3")
    preview_resp = client.post("/api/tw-stock/agent/preview", json={"question": "今天 top30", "maxItems": 2})
    blocked_resp = client.post("/api/tw-stock/agent/preview", json={"question": "帮我下单买 2330"})

    context_payload = context_resp.get_json()
    preview_payload = preview_resp.get_json()
    blocked_payload = blocked_resp.get_json()

    assert context_resp.status_code == 200
    assert context_payload["code"] == 1
    assert context_payload["data"]["qlib"]["research_signal_not_order"] is True
    assert preview_payload["code"] == 1
    assert preview_payload["data"]["intent"] == "today_top30"
    assert preview_payload["data"]["blocked"] is False
    assert blocked_payload["code"] == 1
    assert blocked_payload["data"]["blocked"] is True
    assert blocked_payload["data"]["intent"] == "place_order"


def test_agent_step1_sources_do_not_use_openai_key_or_forbidden_imports(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "should-not-be-read")
    root = Path(__file__).resolve().parents[1] / "app" / "services"
    sources = [
        (root / "tw_stock_agent_context.py").read_text(),
        (root / "tw_stock_agent_guardrails.py").read_text(),
    ]
    joined = "\n".join(sources)

    assert "OPENAI_API_KEY" not in joined
    assert "openai" not in joined.lower()
    assert "option_c_ops" not in joined
    assert "normal_publish" not in joined
    assert "eod_pipeline" not in joined
    assert "backtest" not in joined
    assert "import app.services.broker" not in joined.lower()
    assert "from app.services.broker" not in joined.lower()
    assert "trading_executor" not in joined
