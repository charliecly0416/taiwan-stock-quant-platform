"""Optional live smoke tests for TWStock FinMind data.

These tests are skipped by default. Run explicitly with:
    TW_STOCK_LIVE_TEST=1 python -m pytest backend/tests/test_tw_stock_live_smoke.py -q -s
"""
from __future__ import annotations

import os

import pytest

from app.data_sources.tw_stock import TWStockDataSource


pytestmark = pytest.mark.skipif(
    os.getenv("TW_STOCK_LIVE_TEST", "").strip().lower() not in ("1", "true", "yes"),
    reason="Set TW_STOCK_LIVE_TEST=1 to run live FinMind Taiwan stock smoke tests.",
)


def test_live_finmind_fetches_2330_daily_bars():
    src = TWStockDataSource()
    bars = src.get_kline("2330", "1D", limit=10)

    assert bars, "FinMind returned no 2330 daily bars"
    assert len(bars) <= 10
    assert bars == sorted(bars, key=lambda x: x["time"])

    latest = bars[-1]
    assert {"time", "open", "high", "low", "close", "volume"} <= set(latest)
    assert latest["open"] > 0
    assert latest["high"] >= max(latest["open"], latest["close"])
    assert latest["low"] <= min(latest["open"], latest["close"])
    assert latest["volume"] >= 0

    print(f"TWStock 2330 live bars={len(bars)} latest={latest}")
