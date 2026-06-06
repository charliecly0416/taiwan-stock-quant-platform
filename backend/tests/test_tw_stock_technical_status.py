"""Unit tests for lightweight read-only TWStock technical status."""
from __future__ import annotations

from pathlib import Path

from app.services.tw_stock_technical_status import TWStockTechnicalStatusService


class FakeKlineService:
    def __init__(self, closes):
        self.closes = closes
        self.calls = []

    def get_kline(self, market, symbol, timeframe, limit):
        self.calls.append((market, symbol, timeframe, limit))
        return [{"time": index + 1, "close": close} for index, close in enumerate(self.closes[-limit:])]


def _service(closes):
    return TWStockTechnicalStatusService(kline_service=FakeKlineService(closes))


def _mild_uptrend_closes():
    value = 100.0
    closes = []
    for index in range(80):
        step = 0.4 if index % 4 in (1, 2) else -0.15
        value += step
        closes.append(round(value, 2))
    return closes


def test_ma_supportive_neutral_caution_and_insufficient():
    supportive = _service(list(range(80, 121))).analyze_symbol(symbol="2330", strategies=["ma"])["strategies"][0]
    caution = _service(list(range(120, 79, -1))).analyze_symbol(symbol="2330", strategies=["ma"])["strategies"][0]
    neutral = _service([100] * 40).analyze_symbol(symbol="2330", strategies=["ma"])["strategies"][0]
    insufficient = _service([100] * 10).analyze_symbol(symbol="2330", strategies=["ma"])["strategies"][0]

    assert supportive["state"] == "supportive"
    assert caution["state"] == "caution"
    assert neutral["state"] == "neutral"
    assert insufficient["state"] == "data_insufficient"


def test_rsi_supportive_caution_and_insufficient():
    supportive_closes = [100] * 26 + [101, 100, 101, 100, 101, 100, 101, 100, 101, 100, 101, 100, 101, 100]
    high_caution = list(range(80, 121))
    low_caution = list(range(120, 79, -1))

    supportive = _service(supportive_closes).analyze_symbol(symbol="2330", strategies=["rsi"])["strategies"][0]
    caution_high = _service(high_caution).analyze_symbol(symbol="2330", strategies=["rsi"])["strategies"][0]
    caution_low = _service(low_caution).analyze_symbol(symbol="2330", strategies=["rsi"])["strategies"][0]
    insufficient = _service([100] * 10).analyze_symbol(symbol="2330", strategies=["rsi"])["strategies"][0]

    assert supportive["state"] == "supportive"
    assert caution_high["state"] == "caution"
    assert caution_low["state"] == "caution"
    assert insufficient["state"] == "data_insufficient"


def test_macd_supportive_caution_and_insufficient():
    supportive = _service(list(range(80, 141))).analyze_symbol(symbol="2330", strategies=["macd"])["strategies"][0]
    caution = _service(list(range(140, 79, -1))).analyze_symbol(symbol="2330", strategies=["macd"])["strategies"][0]
    insufficient = _service([100] * 20).analyze_symbol(symbol="2330", strategies=["macd"])["strategies"][0]

    assert supportive["state"] == "supportive"
    assert caution["state"] == "caution"
    assert insufficient["state"] == "data_insufficient"


def test_bollinger_supportive_caution_and_insufficient():
    supportive = _service(_mild_uptrend_closes()).analyze_symbol(symbol="2330", strategies=["bollinger"])["strategies"][0]
    caution = _service([100] * 39 + [140]).analyze_symbol(symbol="2330", strategies=["bollinger"])["strategies"][0]
    insufficient = _service([100] * 10).analyze_symbol(symbol="2330", strategies=["bollinger"])["strategies"][0]

    assert supportive["state"] == "supportive"
    assert caution["state"] == "caution"
    assert insufficient["state"] == "data_insufficient"


def test_technical_summary_rules():
    strong = _service(_mild_uptrend_closes()).analyze_symbol(symbol="2330")
    weak = _service(list(range(140, 79, -1))).analyze_symbol(symbol="2330")
    insufficient = _service([100] * 10).analyze_symbol(symbol="2330")

    assert strong["summary"]["supportive_count"] >= 2
    assert strong["status"] == "technical_strong"
    assert weak["summary"]["caution_count"] >= 2
    assert weak["status"] == "technical_weak"
    assert insufficient["summary"]["data_insufficient_count"] >= 3
    assert insufficient["status"] == "technical_data_insufficient"


def test_technical_status_source_has_no_backtest_or_action_terms():
    source = Path("backend/app/services/tw_stock_technical_status.py").read_text()
    forbidden = [
        "BacktestService",
        "portfolio-replay",
        "equity_curve",
        "trade_list",
        "立即买入",
        "立即卖出",
        "自动买入",
        "自动卖出",
        "下单",
        "提交订单",
        "目标仓位",
        "上涨概率",
        "收益承诺",
        "buy signal",
        "sell signal",
        "target weight",
        "target position",
    ]

    assert not any(term in source for term in forbidden)
