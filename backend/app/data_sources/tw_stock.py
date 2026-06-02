"""
Taiwan stock data source.

Phase 1 supports daily/weekly Taiwan stock K-lines from FinMind. TWSE/TPEx
official patching and local archival storage are intentionally added in later
steps.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import requests

from app.data_sources.base import BaseDataSource
from app.utils.logger import get_logger

logger = get_logger(__name__)

FINMIND_BASE_URL = "https://api.finmindtrade.com/api/v4/data"
HTTP_TIMEOUT = 20
TAIPEI_TZ = timezone(timedelta(hours=8))
ARCHIVE_LOOKUP_ENV = "TW_STOCK_ARCHIVE_LOOKUP"
CORPORATE_ACTION_MODE_ENV = "TW_STOCK_CORPORATE_ACTION_MODE"
_TW_STOCK_RE = re.compile(r"^[0-9A-Z]{2,12}$")


@dataclass(frozen=True)
class TWStockSymbol:
    symbol: str
    exchange: str = ""
    currency: str = "TWD"


@dataclass(frozen=True)
class TWStockCorporateAction:
    symbol: str
    date: str
    action_type: str
    before_price: float
    after_price: float
    cash_or_stock_dividend: float
    adjustment_factor: float


class TWStockDataSource(BaseDataSource):
    """Taiwan equities data source for research and backtesting."""

    name = "TWStock/finmind"

    def __init__(self, base_url: str = FINMIND_BASE_URL):
        self.base_url = str(base_url or FINMIND_BASE_URL).strip()
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": "QuantDinger/TWStock-DataSource"})

    @staticmethod
    def normalize_symbol(symbol: str) -> TWStockSymbol:
        """Normalize common Taiwan stock symbol formats.

        Accepted examples:
            2330, 2330.TW, TWSE:2330, 6488.TPEX, TPEX:6488
        """
        raw = str(symbol or "").strip().upper()
        if not raw:
            return TWStockSymbol(symbol="")

        exchange = ""
        s = raw
        if ":" in s:
            prefix, rest = s.split(":", 1)
            if prefix in ("TWSE", "TPEX"):
                exchange = "TPEX" if prefix == "TPEX" else "TWSE"
                s = rest

        for suffix, exch in (
            (".TWSE", "TWSE"),
            (".TPEX", "TPEX"),
            (".TWO", "TPEX"),
            (".TW", "TWSE"),
        ):
            if s.endswith(suffix):
                exchange = exch
                s = s[: -len(suffix)]
                break

        s = s.strip()
        if not _TW_STOCK_RE.match(s):
            return TWStockSymbol(symbol="", exchange=exchange)
        return TWStockSymbol(symbol=s, exchange=exchange)

    @staticmethod
    def _finmind_token() -> str:
        return (os.getenv("FINMIND_TOKEN") or os.getenv("FINMIND_API_TOKEN") or "").strip()

    @staticmethod
    def _date_range(timeframe: str, limit: int, before_time: Optional[int], after_time: Optional[int]) -> tuple[str, str]:
        end_dt = datetime.fromtimestamp(before_time, tz=TAIPEI_TZ) if before_time else datetime.now(tz=TAIPEI_TZ)
        if after_time is not None:
            start_dt = datetime.fromtimestamp(after_time, tz=TAIPEI_TZ)
        else:
            effective_limit = max(int(limit or 1), 1)
            if timeframe == "1W":
                days = effective_limit * 10 + 30
            else:
                days = int(effective_limit * 1.8) + 14
            start_dt = end_dt - timedelta(days=max(days, 30))
        return start_dt.strftime("%Y-%m-%d"), end_dt.strftime("%Y-%m-%d")

    def _http_get(self, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        try:
            resp = self._session.get(self.base_url, params=params, timeout=HTTP_TIMEOUT)
            if resp.status_code != 200:
                logger.warning("FinMind HTTP %s for Taiwan stock data", resp.status_code)
                return {"status": resp.status_code, "msg": resp.text[:500], "data": []}
            return resp.json()
        except Exception as e:
            logger.warning("FinMind request failed for Taiwan stock data: %s", e)
            return None


    @staticmethod
    def _archive_lookup_enabled() -> bool:
        return (os.getenv(ARCHIVE_LOOKUP_ENV, "true").strip().lower() not in ("0", "false", "no", "off"))

    @staticmethod
    def corporate_action_mode() -> str:
        raw = (os.getenv(CORPORATE_ACTION_MODE_ENV) or "raw_unadjusted").strip().lower()
        aliases = {
            "raw": "raw_unadjusted",
            "none": "raw_unadjusted",
            "unadjusted": "raw_unadjusted",
            "qfq": "forward_adjusted",
            "forward": "forward_adjusted",
            "forward_adjusted": "forward_adjusted",
            "hfq": "backward_adjusted",
            "backward": "backward_adjusted",
            "backward_adjusted": "backward_adjusted",
        }
        return aliases.get(raw, "raw_unadjusted")

    @classmethod
    def _corporate_actions_from_finmind_rows(cls, rows: List[Dict[str, Any]], symbol: str = "") -> List[TWStockCorporateAction]:
        out: List[TWStockCorporateAction] = []
        norm_symbol = cls.normalize_symbol(symbol).symbol if symbol else ""
        seen = set()
        for row in rows or []:
            if not isinstance(row, dict):
                continue
            date_s = str(row.get("date") or "").strip()
            row_symbol = cls.normalize_symbol(row.get("stock_id") or norm_symbol).symbol or norm_symbol
            key = (row_symbol, date_s)
            if not row_symbol or not date_s or key in seen:
                continue
            seen.add(key)
            before_price = cls._to_float(row.get("before_price"))
            after_price = cls._to_float(row.get("after_price"))
            if before_price <= 0 or after_price <= 0:
                continue
            out.append(TWStockCorporateAction(
                symbol=row_symbol,
                date=date_s,
                action_type=str(row.get("stock_or_cache_dividend") or "").strip(),
                before_price=round(before_price, 6),
                after_price=round(after_price, 6),
                cash_or_stock_dividend=round(cls._to_float(row.get("stock_and_cache_dividend")), 6),
                adjustment_factor=round(after_price / before_price, 12),
            ))
        out.sort(key=lambda item: item.date)
        return out

    def _fetch_finmind_corporate_actions(self, symbol: str, start_date: str, end_date: str) -> List[TWStockCorporateAction]:
        params: Dict[str, Any] = {
            "dataset": "TaiwanStockDividendResult",
            "data_id": symbol,
            "start_date": start_date,
            "end_date": end_date,
        }
        token = self._finmind_token()
        if token:
            params["token"] = token
        payload = self._http_get(params)
        if not payload or payload.get("status") not in (None, 200, "200", True):
            return []
        rows = payload.get("data") or []
        return self._corporate_actions_from_finmind_rows(rows if isinstance(rows, list) else [], symbol=symbol)

    @staticmethod
    def _bar_date(bar: Dict[str, Any]) -> str:
        return datetime.fromtimestamp(int(bar["time"]), tz=TAIPEI_TZ).strftime("%Y-%m-%d")

    @classmethod
    def apply_corporate_action_adjustment(
        cls,
        bars: List[Dict[str, Any]],
        actions: List[TWStockCorporateAction],
        mode: str,
    ) -> List[Dict[str, Any]]:
        mode = (mode or "raw_unadjusted").strip().lower()
        if mode not in ("forward_adjusted", "backward_adjusted") or not bars or not actions:
            return bars
        usable = [a for a in actions if a.adjustment_factor > 0]
        if not usable:
            return bars
        adjusted: List[Dict[str, Any]] = []
        for bar in bars:
            bar_date = cls._bar_date(bar)
            factor = 1.0
            if mode == "forward_adjusted":
                for action in usable:
                    if bar_date < action.date:
                        factor *= action.adjustment_factor
            else:
                for action in usable:
                    if bar_date >= action.date:
                        factor *= 1.0 / action.adjustment_factor
            item = dict(bar)
            if abs(factor - 1.0) > 1e-12:
                for key in ("open", "high", "low", "close"):
                    item[key] = round(float(item.get(key) or 0) * factor, 4)
            item["corporateActionMode"] = mode
            item["adjustmentFactor"] = round(factor, 12)
            adjusted.append(item)
        return adjusted

    @staticmethod
    def _archive_rows_to_bars(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        for row in rows or []:
            try:
                trade_date = str(row.get("trade_date") or "").strip()
                if not trade_date:
                    continue
                dt = datetime.strptime(trade_date[:10], "%Y-%m-%d").replace(tzinfo=TAIPEI_TZ)
                o = TWStockDataSource._to_float(row.get("open"))
                h = TWStockDataSource._to_float(row.get("high"))
                low = TWStockDataSource._to_float(row.get("low"))
                c = TWStockDataSource._to_float(row.get("close"))
                v = TWStockDataSource._to_float(row.get("volume"))
                if o <= 0 or h <= 0 or low <= 0 or c <= 0:
                    continue
                out.append({
                    "time": int(dt.timestamp()),
                    "open": round(o, 4),
                    "high": round(h, 4),
                    "low": round(low, 4),
                    "close": round(c, 4),
                    "volume": round(v, 2),
                })
            except Exception as e:
                logger.debug("Failed to parse archived TWStock row %s: %s", row, e)
        out.sort(key=lambda x: x["time"])
        deduped: Dict[int, Dict[str, Any]] = {int(k["time"]): k for k in out}
        return [deduped[k] for k in sorted(deduped)]

    def _fetch_archive_daily(self, symbol: str, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        if not self._archive_lookup_enabled():
            return []
        try:
            from app.utils.db import get_db_connection  # noqa: WPS433
            with get_db_connection() as db:
                cur = db.cursor()
                cur.execute(
                    """
                    SELECT trade_date::text AS trade_date, open, high, low, close, volume
                    FROM qd_tw_stock_daily_bars
                    WHERE symbol = ?
                      AND source = 'finmind'
                      AND trade_date >= ?
                      AND trade_date <= ?
                      AND (quality_flags IS NULL OR quality_flags = '')
                    ORDER BY trade_date ASC
                    """,
                    (symbol, start_date, end_date),
                )
                rows = cur.fetchall() or []
                cur.close()
            bars = self._archive_rows_to_bars(rows)
            if bars:
                logger.debug("TWStock archive hit for %s: %d bars", symbol, len(bars))
            return bars
        except Exception as e:
            logger.debug("TWStock archive lookup failed for %s: %s", symbol, e)
            return []

    def _fetch_finmind_daily(self, symbol: str, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {
            "dataset": "TaiwanStockPrice",
            "data_id": symbol,
            "start_date": start_date,
            "end_date": end_date,
        }
        token = self._finmind_token()
        if token:
            params["token"] = token

        payload = self._http_get(params)
        if not payload:
            return []
        if payload.get("status") not in (None, 200, "200", True):
            logger.warning("FinMind returned non-ok status for %s: %s", symbol, payload.get("status"))
            return []
        rows = payload.get("data") or []
        if not isinstance(rows, list):
            return []
        return self._bars_from_finmind_rows(rows)

    @classmethod
    def _bars_from_finmind_rows(cls, rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            try:
                date_s = str(row.get("date") or "").strip()
                if not date_s:
                    continue
                dt = datetime.strptime(date_s, "%Y-%m-%d").replace(tzinfo=TAIPEI_TZ)
                o = cls._to_float(row.get("open"))
                h = cls._to_float(row.get("max"))
                low = cls._to_float(row.get("min"))
                c = cls._to_float(row.get("close"))
                v = cls._to_float(row.get("Trading_Volume"))
                if o <= 0 or h <= 0 or low <= 0 or c <= 0:
                    continue
                out.append({
                    "time": int(dt.timestamp()),
                    "open": round(o, 4),
                    "high": round(h, 4),
                    "low": round(low, 4),
                    "close": round(c, 4),
                    "volume": round(v, 2),
                })
            except Exception as e:
                logger.debug("Failed to parse FinMind Taiwan stock row %s: %s", row, e)
                continue
        out.sort(key=lambda x: x["time"])
        deduped: Dict[int, Dict[str, Any]] = {int(k["time"]): k for k in out}
        return [deduped[k] for k in sorted(deduped)]

    @staticmethod
    def _to_float(value: Any) -> float:
        if value is None:
            return 0.0
        if isinstance(value, str):
            value = value.replace(",", "").strip()
            if value in ("", "--", "-"):
                return 0.0
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _resample_daily_to_weekly(klines: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not klines:
            return []
        out: List[Dict[str, Any]] = []
        current: Optional[Dict[str, Any]] = None
        current_key = None
        for k in sorted(klines, key=lambda x: x["time"]):
            dt = datetime.fromtimestamp(int(k["time"]), tz=TAIPEI_TZ)
            iso = dt.isocalendar()
            key = (iso.year, iso.week)
            if current is None or key != current_key:
                if current is not None:
                    out.append(current)
                current = {
                    "time": k["time"],
                    "open": k["open"],
                    "high": k["high"],
                    "low": k["low"],
                    "close": k["close"],
                    "volume": k["volume"],
                }
                current_key = key
            else:
                current["high"] = max(current["high"], k["high"])
                current["low"] = min(current["low"], k["low"])
                current["close"] = k["close"]
                current["volume"] = round(current["volume"] + k["volume"], 2)
        if current is not None:
            out.append(current)
        return out

    def get_kline(
        self,
        symbol: str,
        timeframe: str,
        limit: int,
        before_time: Optional[int] = None,
        after_time: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        norm = self.normalize_symbol(symbol)
        if not norm.symbol:
            return []
        if timeframe not in ("1D", "1W"):
            logger.info("TWStock: unsupported timeframe %s for %s", timeframe, norm.symbol)
            return []

        start_date, end_date = self._date_range(timeframe, limit, before_time, after_time)
        archive_daily = self._fetch_archive_daily(norm.symbol, start_date, end_date) if self._archive_lookup_enabled() else []
        expected_min = max(1, min(int(limit or 1), 5)) if after_time is None else 1
        if len(archive_daily) >= expected_min:
            klines = archive_daily
        else:
            klines = self._fetch_finmind_daily(norm.symbol, start_date, end_date)
        mode = self.corporate_action_mode()
        if mode != "raw_unadjusted" and klines:
            actions = self._fetch_finmind_corporate_actions(norm.symbol, start_date, end_date)
            klines = self.apply_corporate_action_adjustment(klines, actions, mode)

        if timeframe == "1W":
            klines = self._resample_daily_to_weekly(klines)

        klines = self.filter_and_limit(
            klines,
            limit,
            before_time,
            after_time,
            truncate=(after_time is None),
        )
        self.log_result(norm.symbol, klines, timeframe)
        return klines

    def get_ticker(self, symbol: str) -> Dict[str, Any]:
        norm = self.normalize_symbol(symbol)
        if not norm.symbol:
            return {"last": 0, "symbol": symbol}
        bars = self.get_kline(symbol, "1D", 2)
        if not bars:
            return {"last": 0, "symbol": norm.symbol, "exchange": norm.exchange, "currency": norm.currency}
        latest = bars[-1]
        prev_close = bars[-2]["close"] if len(bars) > 1 else latest.get("open", 0)
        last = float(latest.get("close") or 0)
        change = round(last - float(prev_close or 0), 4) if prev_close else 0.0
        change_pct = round(change / float(prev_close) * 100, 2) if prev_close else 0.0
        return {
            "last": last,
            "change": change,
            "changePercent": change_pct,
            "high": latest.get("high", 0),
            "low": latest.get("low", 0),
            "open": latest.get("open", 0),
            "previousClose": prev_close,
            "symbol": norm.symbol,
            "exchange": norm.exchange,
            "currency": norm.currency,
        }
