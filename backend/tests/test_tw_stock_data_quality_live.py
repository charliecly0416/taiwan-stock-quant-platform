"""Optional live data-quality checks for TWStock.

Skipped by default. Run with:
    TW_STOCK_LIVE_TEST=1 python -m pytest backend/tests/test_tw_stock_data_quality_live.py -q -s

Checks:
- FinMind daily bars are non-empty, sorted and OHLC-valid.
- Latest bar is timely relative to TWSE official STOCK_DAY_ALL date.
- Latest close/volume match TWSE official STOCK_DAY_ALL.
"""
from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Dict

import pytest
import requests

from app.data_sources.tw_stock import TAIPEI_TZ, TWStockDataSource


pytestmark = pytest.mark.skipif(
    os.getenv("TW_STOCK_LIVE_TEST", "").strip().lower() not in ("1", "true", "yes"),
    reason="Set TW_STOCK_LIVE_TEST=1 to run live TWStock data-quality checks.",
)

TWSE_STOCK_DAY_ALL_URL = "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL"
TWSE_QUALITY_SYMBOLS = ("2330", "2317", "2454", "0050", "0056", "00878")


def _roc_yyyymmdd_to_date(value: str) -> datetime:
    s = str(value or "").strip()
    if len(s) != 7 or not s.isdigit():
        raise ValueError(f"Unexpected ROC date: {value!r}")
    year = int(s[:3]) + 1911
    month = int(s[3:5])
    day = int(s[5:7])
    return datetime(year, month, day, tzinfo=TAIPEI_TZ)


def _num(value: Any) -> float:
    return float(str(value).replace(",", "").strip())


@pytest.fixture(scope="module")
def twse_rows_by_code() -> Dict[str, Dict[str, Any]]:
    resp = requests.get(TWSE_STOCK_DAY_ALL_URL, timeout=20)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list) and data
    rows = {str(row.get("Code") or "").strip(): row for row in data if row.get("Code")}
    for code in TWSE_QUALITY_SYMBOLS:
        assert code in rows, f"TWSE STOCK_DAY_ALL did not include {code}"
    return rows


@pytest.mark.parametrize("symbol", TWSE_QUALITY_SYMBOLS)
def test_live_finmind_matches_twse_latest_close_and_volume(symbol: str, twse_rows_by_code: Dict[str, Dict[str, Any]]):
    twse = twse_rows_by_code[symbol]
    twse_date = _roc_yyyymmdd_to_date(twse["Date"])
    twse_close = _num(twse["ClosingPrice"])
    twse_volume = _num(twse["TradeVolume"])

    src = TWStockDataSource()
    bars = src.get_kline(symbol, "1D", limit=10)

    assert bars, f"FinMind returned no {symbol} bars"
    assert bars == sorted(bars, key=lambda x: x["time"])
    for bar in bars:
        assert bar["open"] > 0
        assert bar["high"] >= max(bar["open"], bar["close"])
        assert bar["low"] <= min(bar["open"], bar["close"])
        assert bar["volume"] >= 0

    latest = bars[-1]
    latest_dt = datetime.fromtimestamp(int(latest["time"]), tz=TAIPEI_TZ)
    now_tw = datetime.now(TAIPEI_TZ)

    assert latest_dt.date() == twse_date.date(), (
        f"{symbol}: FinMind latest date {latest_dt.date()} != TWSE latest date {twse_date.date()}"
    )
    assert abs(float(latest["close"]) - twse_close) < 1e-9
    assert abs(float(latest["volume"]) - twse_volume) < 1e-9
    assert 0 <= (now_tw.date() - latest_dt.date()).days <= 5

    print(
        "TWStock quality "
        f"symbol={symbol} name={twse.get('Name')} twse_date={twse_date.date()} "
        f"close={twse_close} volume={twse_volume} latest={latest}"
    )
