"""Optional live quality checks for TPEx-listed Taiwan stocks.

Skipped by default. Run with:
    TW_STOCK_LIVE_TEST=1 python -m pytest backend/tests/test_tw_stock_tpex_quality_live.py -q -s

TPEx official endpoints are currently Cloudflare-protected from some server
networks. The test always validates FinMind freshness/OHLC for TPEx samples; it
attempts official TPEx cross-check and xfails with a clear reason if TPEx blocks
access with HTTP 403.
"""
from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Dict, Iterable, Optional

import pytest
import requests

from app.data_sources.tw_stock import TAIPEI_TZ, TWStockDataSource


pytestmark = pytest.mark.skipif(
    os.getenv("TW_STOCK_LIVE_TEST", "").strip().lower() not in ("1", "true", "yes"),
    reason="Set TW_STOCK_LIVE_TEST=1 to run live TPEx TWStock data-quality checks.",
)

TPEX_QUALITY_SYMBOLS = ("6488", "3105", "8069")
TPEX_OFFICIAL_URL = "https://www.tpex.org.tw/openapi/v1/tpex_mainboard_daily_close_quotes"


def _num(value: Any) -> float:
    return float(str(value).replace(",", "").strip())


def _candidate_code(row: Dict[str, Any]) -> str:
    for key in ("SecuritiesCompanyCode", "Code", "代號", "公司代號", "股票代號"):
        value = row.get(key)
        if value:
            return str(value).strip()
    return ""


def _candidate_close(row: Dict[str, Any]) -> Optional[float]:
    for key in ("Close", "ClosingPrice", "收盤", "收盤價"):
        value = row.get(key)
        if value not in (None, "", "--"):
            return _num(value)
    return None


def _candidate_volume(row: Dict[str, Any]) -> Optional[float]:
    for key in ("TradeVolume", "Trading_Volume", "成交股數", "成交量"):
        value = row.get(key)
        if value not in (None, "", "--"):
            return _num(value)
    return None


def _fetch_tpex_rows() -> Iterable[Dict[str, Any]]:
    headers = {
        "User-Agent": "Mozilla/5.0 QuantDinger TPEx data-quality smoke",
        "Accept": "application/json,text/plain,*/*",
        "Referer": "https://www.tpex.org.tw/openapi/",
    }
    try:
        resp = requests.get(TPEX_OFFICIAL_URL, headers=headers, timeout=20)
    except requests.RequestException as exc:
        pytest.xfail(f"TPEx official OpenAPI is not reachable from this environment: {exc}")
    if resp.status_code == 403:
        pytest.xfail("TPEx official OpenAPI returned HTTP 403 (Cloudflare blocked this environment)")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list) and data
    return data


@pytest.mark.parametrize("symbol", TPEX_QUALITY_SYMBOLS)
def test_live_finmind_tpex_sample_is_fresh_and_ohlc_valid(symbol: str):
    src = TWStockDataSource()
    bars = src.get_kline(symbol, "1D", limit=10)

    assert bars, f"FinMind returned no TPEx sample bars for {symbol}"
    assert bars == sorted(bars, key=lambda x: x["time"])
    for bar in bars:
        assert bar["open"] > 0
        assert bar["high"] >= max(bar["open"], bar["close"])
        assert bar["low"] <= min(bar["open"], bar["close"])
        assert bar["volume"] >= 0

    latest = bars[-1]
    latest_dt = datetime.fromtimestamp(int(latest["time"]), tz=TAIPEI_TZ)
    now_tw = datetime.now(TAIPEI_TZ)
    assert 0 <= (now_tw.date() - latest_dt.date()).days <= 5
    print(f"TPEx FinMind quality symbol={symbol} latest_date={latest_dt.date()} latest={latest}")


@pytest.mark.parametrize("symbol", TPEX_QUALITY_SYMBOLS)
def test_live_finmind_tpex_sample_matches_official_when_accessible(symbol: str):
    rows = list(_fetch_tpex_rows())
    official = next((row for row in rows if _candidate_code(row) == symbol), None)
    assert official is not None, f"TPEx official data did not include {symbol}"

    close = _candidate_close(official)
    volume = _candidate_volume(official)
    assert close is not None, f"Could not parse official close for {symbol}: {official}"
    assert volume is not None, f"Could not parse official volume for {symbol}: {official}"

    latest = TWStockDataSource().get_kline(symbol, "1D", limit=10)[-1]
    assert abs(float(latest["close"]) - close) < 1e-9
    assert abs(float(latest["volume"]) - volume) < 1e-9
    print(f"TPEx official match symbol={symbol} close={close} volume={volume} latest={latest}")
