"""Static checks for the TWStock read-only backtest implementation plan."""
from __future__ import annotations

from pathlib import Path

DOC = Path(__file__).resolve().parents[2] / "docs" / "TW_STOCK_BACKTEST_IMPLEMENTATION_PLAN_CN.md"


def _text() -> str:
    return DOC.read_text(encoding="utf-8")


def test_tw_stock_backtest_plan_exists_and_defines_scope():
    text = _text()

    required = [
        "只读回测",
        "TWStock",
        "本地日线归档",
        "qd_tw_stock_daily_bars",
        "timeframe=1D",
        "经典指标",
    ]
    for phrase in required:
        assert phrase in text


def test_tw_stock_backtest_plan_preserves_research_only_boundary():
    text = _text().lower()

    required = [
        "不连接 broker",
        "不启用 live",
        "不提交订单",
        "不提交 paper order",
        "不调用 quick-trade",
        "orders_enabled=false",
        "connects_to_broker=false",
    ]
    for phrase in required:
        assert phrase in text


def test_tw_stock_backtest_plan_lists_minimum_result_contract():
    text = _text()

    required = [
        "metrics.totalReturn",
        "metrics.maxDrawdown",
        "metrics.winRate",
        "metrics.totalTrades",
        "equityCurve[]",
        "trades[]",
        "executionAssumptions",
        "dataQuality",
    ]
    for phrase in required:
        assert phrase in text
