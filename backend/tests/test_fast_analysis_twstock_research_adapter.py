"""Tests for TWStock read-only adaptation in fast analysis."""

from app.services.fast_analysis import FastAnalysisService


def _asus_context():
    return {
        "ok": True,
        "status": "accepted",
        "symbol": "2357",
        "instrument": "TW2357",
        "name": "華碩",
        "qlib": {
            "asof": "2026-06-04",
            "run_id": "option_c_daily_signal_20260604_20260605T054532Z",
            "target_horizon": "next_trading_day_research_ranking",
            "rank": 1,
            "bucket": "top50",
            "score": 0.11491631975255866,
            "signal_semantics": "research_only_cross_sectional_ranking",
            "recommendation_semantics": "watchlist_not_trade_advice",
        },
        "quantdinger": {
            "trend_label": "uptrend",
            "trend_score": 93.64,
            "latest_date": "2026-06-04",
            "quality_warnings": [],
        },
        "cross": {
            "category": "secondary_watch",
            "priority": "medium",
            "alignment": "aligned",
            "reason": "top50 aligned with positive trend",
        },
        "trading": {"orders_enabled": False, "research_signal_not_order": True},
        "disclaimer": "qlib_score 是横截面研究排序分数，不是收益率、胜率、上涨概率或买入概率。输出仅供人工研究复盘，不构成交易建议。",
    }


def test_twstock_adapter_converts_sell_to_research_watch_context():
    service = FastAnalysisService()
    analysis = {
        "decision": "SELL",
        "confidence": 88,
        "summary": "generic short signal",
        "key_reasons": ["generic bearish"],
        "risks": [],
        "analysis": {"technical": "downtrend"},
        "position_size_pct": 20,
        "entry_price": 500,
        "stop_loss": 525,
        "take_profit": 475,
    }

    adapted = service._apply_tw_stock_research_adapter(
        analysis,
        context=_asus_context(),
        language="zh-CN",
        current_price=500,
    )

    assert adapted["decision"] == "HOLD"
    assert adapted["position_size_pct"] == 0
    assert adapted["stop_loss"] is None
    assert adapted["take_profit"] is None
    assert adapted["tw_stock_research_context"]["display_decision"] == "高优先观察"
    assert adapted["tw_stock_research_context"]["research_only"] is True
    assert "SELL" not in adapted["summary"]
    assert "下降" not in adapted["summary"]
    assert "qlib accepted latest 为 2026-06-04" in adapted["summary"]
    assert "趋势 uptrend" in adapted["summary"]
    assert "不构成交易建议" in "".join(adapted["key_reasons"])


def test_twstock_research_label_uses_high_priority_for_top30_aligned_uptrend():
    context = _asus_context()
    context["qlib"]["rank"] = 1
    context["qlib"]["bucket"] = "top30"
    context["cross"]["category"] = "focus_watch"

    assert FastAnalysisService._tw_stock_research_label(context) == ("高优先观察", "high_priority_watch")
