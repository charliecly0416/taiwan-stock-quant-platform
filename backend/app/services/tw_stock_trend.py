"""Read-only TWStock trend analysis service.

This service is intentionally research/visibility only. It fetches daily bars
through the existing KlineService and returns explainable trend metrics. It
does not create orders, touch broker clients, or mutate portfolio state.
"""
from __future__ import annotations

import math
from datetime import date, datetime, timedelta, timezone
from statistics import pstdev
from typing import Any, Dict, List, Optional, Sequence

from app.data_sources.tw_stock import TWStockDataSource
from app.services.kline import KlineService


TAIPEI_TZ = timezone(timedelta(hours=8))

def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        out = float(value)
        if math.isnan(out) or math.isinf(out):
            return default
        return out
    except Exception:
        return default


def _bar_date(bar: Dict[str, Any]) -> str:
    raw = bar.get("date") or bar.get("trade_date") or bar.get("latest_date")
    if raw:
        try:
            return date.fromisoformat(str(raw)[:10]).isoformat()
        except ValueError:
            return ""
    ts = int(_safe_float(bar.get("time"), 0.0))
    if ts <= 0:
        return ""
    return datetime.fromtimestamp(ts, TAIPEI_TZ).date().isoformat()


def _mean(values: Sequence[float]) -> Optional[float]:
    clean = [float(v) for v in values if v is not None]
    return sum(clean) / len(clean) if clean else None


def _pct_return(closes: Sequence[float], window: int) -> Optional[float]:
    if len(closes) <= window:
        return None
    base = closes[-window - 1]
    if base <= 0:
        return None
    return closes[-1] / base - 1.0


def _round_optional(value: Optional[float], digits: int = 6) -> Optional[float]:
    if value is None:
        return None
    return round(float(value), digits)


class TWStockTrendService:
    def __init__(self, kline_service: Optional[KlineService] = None) -> None:
        self.kline_service = kline_service or KlineService()

    def analyze_symbol(self, *, symbol: str, limit: int = 120, as_of: Optional[date] = None) -> Dict[str, Any]:
        normalized = TWStockDataSource.normalize_symbol(symbol)
        clean_symbol = normalized.symbol
        exchange = normalized.exchange or "TWSE"
        if not clean_symbol:
            return {
                "market": "TWStock",
                "symbol": str(symbol or "").strip(),
                "ok": False,
                "error": "invalid_twstock_symbol",
                "quality": {"warnings": ["invalid_twstock_symbol"]},
            }

        bar_limit = max(20, min(int(limit or 120), 500))
        fetch_limit = bar_limit if as_of is None else min(max(bar_limit * 3, bar_limit), 500)
        bars = self.kline_service.get_kline("TWStock", clean_symbol, "1D", fetch_limit) or []
        bars = [bar for bar in bars if isinstance(bar, dict) and _safe_float(bar.get("close"), 0.0) > 0]
        if as_of is not None:
            bars = [bar for bar in bars if self._bar_date_value(bar) and self._bar_date_value(bar) <= as_of]
        bars.sort(key=lambda item: int(_safe_float(item.get("time"), 0.0)))
        bars = bars[-bar_limit:]
        if not bars:
            return {
                "market": "TWStock",
                "symbol": clean_symbol,
                "exchange": exchange,
                "ok": False,
                "error": "no_daily_bars",
                "quality": {
                    "bar_count": 0,
                    "warnings": ["no_daily_bars", "data_source_unavailable"],
                    "source": "KlineService:TWStock:1D",
                },
                "trading": {
                    "signal": "none",
                    "orders_enabled": False,
                    "note": "Read-only trend analysis; data source returned no daily bars.",
                },
            }

        closes = [_safe_float(bar.get("close"), 0.0) for bar in bars]
        volumes = [_safe_float(bar.get("volume"), 0.0) for bar in bars]
        latest = bars[-1]
        latest_close = closes[-1]
        latest_date = _bar_date(latest)
        today = as_of or datetime.now(TAIPEI_TZ).date()
        stale_days = None
        warnings: List[str] = []
        if latest_date:
            stale_days = (today - date.fromisoformat(latest_date)).days
            if stale_days > 5:
                warnings.append("stale_daily_bar")
            elif stale_days < -1:
                warnings.append("latest_bar_in_future")
        if len(bars) < 60:
            warnings.append("short_history_below_60_bars")
        elif len(bars) < 120:
            warnings.append("history_below_120_bars")

        ma5 = _mean(closes[-5:]) if len(closes) >= 5 else None
        ma20 = _mean(closes[-20:]) if len(closes) >= 20 else None
        ma60 = _mean(closes[-60:]) if len(closes) >= 60 else None
        ret5 = _pct_return(closes, 5)
        ret20 = _pct_return(closes, 20)
        ret60 = _pct_return(closes, 60)
        daily_returns = []
        for prev, cur in zip(closes[-21:-1], closes[-20:]):
            if prev > 0:
                daily_returns.append(cur / prev - 1.0)
        volatility20 = pstdev(daily_returns) * math.sqrt(252) if len(daily_returns) >= 2 else None
        avg_volume20 = _mean(volumes[-20:]) if len(volumes) >= 20 else None
        avg_volume60 = _mean(volumes[-60:]) if len(volumes) >= 60 else None
        volume_ratio20 = volumes[-1] / avg_volume20 if avg_volume20 and avg_volume20 > 0 else None

        score = 50.0
        if ret20 is not None:
            score += max(min(ret20 * 55.0, 16.0), -16.0)
        if ret60 is not None:
            score += max(min(ret60 * 32.0, 12.0), -12.0)
        if ret5 is not None:
            score += max(min(ret5 * 35.0, 5.0), -5.0)
        if ma20 and latest_close > ma20:
            score += min((latest_close / ma20 - 1.0) * 120.0, 7.0)
        elif ma20 and latest_close < ma20:
            score -= min((ma20 / latest_close - 1.0) * 120.0, 7.0)
        if ma60 and latest_close > ma60:
            score += min((latest_close / ma60 - 1.0) * 80.0, 6.0)
        elif ma60 and latest_close < ma60:
            score -= min((ma60 / latest_close - 1.0) * 80.0, 6.0)
        if volume_ratio20 is not None:
            if volume_ratio20 > 1.2 and ret20 is not None and ret20 > 0:
                score += min((volume_ratio20 - 1.2) * 2.0, 3.0)
            elif volume_ratio20 > 1.2 and ret20 is not None and ret20 < 0:
                score -= min((volume_ratio20 - 1.2) * 2.0, 3.0)
        if volatility20 is not None and volatility20 > 0.45:
            score -= min((volatility20 - 0.45) * 10.0, 4.0)
        score = max(0.0, min(100.0, score))

        if ma20 and ma60 and latest_close > ma20 > ma60 and (ret20 or 0) > 0:
            label = "uptrend"
        elif ma20 and ma60 and latest_close < ma20 < ma60 and (ret20 or 0) < 0:
            label = "downtrend"
        elif ma20 and abs(latest_close / ma20 - 1.0) <= 0.02:
            label = "sideways"
        elif ret20 is not None and ret20 > 0:
            label = "rebound"
        elif ret20 is not None and ret20 < 0:
            label = "pullback"
        else:
            label = "unknown"

        return {
            "market": "TWStock",
            "symbol": clean_symbol,
            "exchange": exchange,
            "ok": True,
            "latest": {"date": latest_date, "close": round(latest_close, 4), "volume": volumes[-1]},
            "trend": {"label": label, "score": round(score, 2), "summary": self._summary(label, score, warnings)},
            "returns": {"ret_5d": _round_optional(ret5), "ret_20d": _round_optional(ret20), "ret_60d": _round_optional(ret60)},
            "moving_averages": {
                "ma5": _round_optional(ma5, 4),
                "ma20": _round_optional(ma20, 4),
                "ma60": _round_optional(ma60, 4),
                "close_above_ma20": bool(ma20 and latest_close > ma20),
                "close_above_ma60": bool(ma60 and latest_close > ma60),
            },
            "volume": {
                "latest": volumes[-1],
                "avg20": _round_optional(avg_volume20, 2),
                "avg60": _round_optional(avg_volume60, 2),
                "ratio_to_avg20": _round_optional(volume_ratio20, 4),
            },
            "risk": {"volatility_20d_annualized": _round_optional(volatility20, 6)},
            "quality": {
                "bar_count": len(bars),
                "latest_date": latest_date,
                "stale_days": stale_days,
                "warnings": warnings,
                "source": "KlineService:TWStock:1D",
            },
            "trading": {
                "signal": "none",
                "orders_enabled": False,
                "note": "Read-only trend analysis; not investment advice and not executable.",
            },
        }


    @staticmethod
    def _bar_date_value(bar: Dict[str, Any]) -> Optional[date]:
        raw = bar.get("date") or bar.get("trade_date") or bar.get("latest_date")
        if raw:
            try:
                return date.fromisoformat(str(raw)[:10])
            except ValueError:
                return None
        text = _bar_date(bar)
        if not text:
            return None
        try:
            return date.fromisoformat(text)
        except ValueError:
            return None

    @staticmethod
    def _summary(label: str, score: float, warnings: Sequence[str]) -> str:
        prefix = {
            "uptrend": "趋势偏强",
            "downtrend": "趋势偏弱",
            "sideways": "横盘震荡",
            "rebound": "短期反弹",
            "pullback": "短期回落",
        }.get(label, "趋势不明确")
        suffix = "，数据存在时效或长度提示" if warnings else ""
        return f"{prefix}，趋势分数 {score:.1f}/100{suffix}。"
