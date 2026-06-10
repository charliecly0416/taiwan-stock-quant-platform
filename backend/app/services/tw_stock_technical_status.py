"""Lightweight read-only TWStock daily technical status.

The service reads daily bars and computes current indicator states only. It
does not run portfolio replay, create historical action lists, or call the
backtest engine.
"""
from __future__ import annotations

import math
from datetime import date, datetime, timedelta, timezone
from statistics import pstdev
from typing import Any, Dict, List, Optional, Sequence

from app.services.kline import KlineService

TAIPEI_TZ = timezone(timedelta(hours=8))


DEFAULT_STRATEGIES = ["ma", "rsi", "macd", "bollinger"]
VALID_STRATEGIES = set(DEFAULT_STRATEGIES)
STATE_ORDER = {"supportive", "neutral", "caution", "data_insufficient"}


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        out = float(value)
        if math.isnan(out) or math.isinf(out):
            return default
        return out
    except Exception:
        return default


def _round_optional(value: Optional[float], digits: int = 4) -> Optional[float]:
    if value is None:
        return None
    return round(float(value), digits)


def _mean(values: Sequence[float]) -> Optional[float]:
    clean = [float(item) for item in values if item is not None]
    if not clean:
        return None
    return sum(clean) / len(clean)


def _percent(value: Optional[float]) -> Optional[float]:
    if value is None:
        return None
    return round(float(value) * 100.0, 2)


def _percentile_rank(values: Sequence[float], value: float) -> Optional[float]:
    clean = [float(item) for item in values if item is not None]
    if len(clean) < 2:
        return None
    below = len([item for item in clean if item < value])
    equal = len([item for item in clean if item == value])
    return ((below + equal * 0.5) / len(clean)) * 100.0


def _ratio_pct(numerator: float, denominator: Optional[float]) -> Optional[float]:
    if denominator is None or denominator == 0:
        return None
    return (float(numerator) / float(denominator) - 1.0) * 100.0


def _ema(values: Sequence[float], period: int) -> List[float]:
    if not values:
        return []
    alpha = 2.0 / (period + 1.0)
    out = [float(values[0])]
    for value in values[1:]:
        out.append(float(value) * alpha + out[-1] * (1.0 - alpha))
    return out


class TWStockTechnicalStatusService:
    """Compute current daily indicator states without producing actions."""

    def __init__(self, kline_service: Optional[Any] = None) -> None:
        self.kline_service = kline_service or KlineService()

    def analyze_symbol(self, *, symbol: str, limit: int = 120, strategies: Optional[List[str]] = None, as_of: Optional[date] = None) -> Dict[str, Any]:
        normalized_limit = self._normalize_limit(limit)
        requested = self._normalize_strategies(strategies)
        bars = self._daily_bars(symbol=symbol, limit=normalized_limit, as_of=as_of)
        closes = [_safe_float(bar.get("close"), 0.0) for bar in bars]
        closes = [value for value in closes if value > 0]
        if not closes:
            items = [self._insufficient_item(strategy_id, "日线样本不足，暂不判断该指标状态。") for strategy_id in requested]
        else:
            items = []
            for strategy_id in requested:
                if strategy_id == "ma":
                    items.append(self._ma_status(closes))
                elif strategy_id == "rsi":
                    items.append(self._rsi_status(closes))
                elif strategy_id == "macd":
                    items.append(self._macd_status(closes))
                elif strategy_id == "bollinger":
                    items.append(self._bollinger_status(closes))
        summary = self._summary(items)
        return {
            "ok": bool(closes),
            "symbol": str(symbol or "").strip(),
            "limit": normalized_limit,
            "basis": "daily_indicators",
            "as_of": as_of.isoformat() if as_of else None,
            "strategies": items,
            "summary": summary,
            "status": self._overall_status(summary),
            "positionRisk": self._position_risk(closes),
            "warnings": self._warnings(items),
        }

    @staticmethod
    def _normalize_limit(limit: int) -> int:
        try:
            value = int(limit or 120)
        except Exception:
            value = 120
        return max(20, min(value, 500))

    @staticmethod
    def _normalize_strategies(strategies: Optional[List[str]]) -> List[str]:
        if not strategies:
            return list(DEFAULT_STRATEGIES)
        out = []
        for raw in strategies:
            item = str(raw or "").strip().lower()
            if item in VALID_STRATEGIES and item not in out:
                out.append(item)
        return out or list(DEFAULT_STRATEGIES)

    def _daily_bars(self, *, symbol: str, limit: int, as_of: Optional[date] = None) -> List[Dict[str, Any]]:
        fetch_limit = limit if as_of is None else min(max(limit * 3, limit), 500)
        rows = self.kline_service.get_kline("TWStock", str(symbol or "").strip(), "1D", fetch_limit) or []
        bars = [row for row in rows if isinstance(row, dict) and _safe_float(row.get("close"), 0.0) > 0]
        if as_of is not None:
            bars = [row for row in bars if self._bar_date(row) and self._bar_date(row) <= as_of]
        bars.sort(key=lambda row: int(_safe_float(row.get("time"), 0.0)))
        return bars[-limit:]

    @staticmethod
    def _bar_date(bar: Dict[str, Any]) -> Optional[date]:
        raw = bar.get("date") or bar.get("trade_date") or bar.get("latest_date")
        if raw:
            try:
                return date.fromisoformat(str(raw)[:10])
            except ValueError:
                return None
        ts = int(_safe_float(bar.get("time"), 0.0))
        if ts <= 0:
            return None
        return datetime.fromtimestamp(ts, TAIPEI_TZ).date()

    @staticmethod
    def _ma_status(closes: Sequence[float]) -> Dict[str, Any]:
        if len(closes) < 20:
            return TWStockTechnicalStatusService._insufficient_item("ma", "MA 需要至少 20 根日线样本。")
        close = closes[-1]
        ma5 = _mean(closes[-5:])
        ma20 = _mean(closes[-20:])
        if close > ma5 > ma20:
            state = "supportive"
            reason = "收盘价位于短中期均线上方，技术状态偏支持。"
        elif close < ma5 < ma20:
            state = "caution"
            reason = "收盘价位于短中期均线下方，技术状态偏谨慎。"
        else:
            state = "neutral"
            reason = "短中期均线关系不够一致，技术状态偏中性。"
        return {
            "id": "ma",
            "label": "MA",
            "state": state,
            "metrics": {"close": _round_optional(close), "ma5": _round_optional(ma5), "ma20": _round_optional(ma20)},
            "reason": reason,
            "warnings": [],
        }

    @staticmethod
    def _rsi_status(closes: Sequence[float]) -> Dict[str, Any]:
        period = 14
        if len(closes) <= period:
            return TWStockTechnicalStatusService._insufficient_item("rsi", "RSI 需要至少 15 根日线样本。")
        changes = [closes[i] - closes[i - 1] for i in range(len(closes) - period, len(closes))]
        gains = [max(change, 0.0) for change in changes]
        losses = [abs(min(change, 0.0)) for change in changes]
        avg_gain = _mean(gains) or 0.0
        avg_loss = _mean(losses) or 0.0
        if avg_loss == 0:
            rsi = 100.0 if avg_gain > 0 else 50.0
        else:
            rs = avg_gain / avg_loss
            rsi = 100.0 - (100.0 / (1.0 + rs))
        if 40.0 <= rsi <= 65.0:
            state = "supportive"
            reason = "RSI 位于可观察区间，技术状态偏支持。"
        elif rsi > 75.0 or rsi < 25.0:
            state = "caution"
            reason = "RSI 偏热或偏冷，技术状态偏谨慎。"
        else:
            state = "neutral"
            reason = "RSI 未形成明显支持或谨慎状态。"
        return {"id": "rsi", "label": "RSI", "state": state, "metrics": {"rsi14": _round_optional(rsi, 2)}, "reason": reason, "warnings": []}

    @staticmethod
    def _macd_status(closes: Sequence[float]) -> Dict[str, Any]:
        if len(closes) < 35:
            return TWStockTechnicalStatusService._insufficient_item("macd", "MACD 需要至少 35 根日线样本。")
        ema12 = _ema(closes, 12)
        ema26 = _ema(closes, 26)
        dif_values = [fast - slow for fast, slow in zip(ema12, ema26)]
        dea_values = _ema(dif_values, 9)
        dif = dif_values[-1]
        dea = dea_values[-1]
        histogram = dif - dea
        if dif > dea and histogram >= 0:
            state = "supportive"
            reason = "MACD 动能线位于信号线上方，技术状态偏支持。"
        elif dif < dea and histogram < 0:
            state = "caution"
            reason = "MACD 动能线位于信号线下方，技术状态偏谨慎。"
        else:
            state = "neutral"
            reason = "MACD 动能状态不够明确，技术状态偏中性。"
        return {
            "id": "macd",
            "label": "MACD",
            "state": state,
            "metrics": {"dif": _round_optional(dif, 4), "dea": _round_optional(dea, 4), "histogram": _round_optional(histogram, 4)},
            "reason": reason,
            "warnings": [],
        }

    @staticmethod
    def _bollinger_status(closes: Sequence[float]) -> Dict[str, Any]:
        period = 20
        if len(closes) < period:
            return TWStockTechnicalStatusService._insufficient_item("bollinger", "Bollinger 需要至少 20 根日线样本。")
        window = list(closes[-period:])
        middle = _mean(window) or 0.0
        width = pstdev(window) * 2.0 if len(window) >= 2 else 0.0
        upper = middle + width
        lower = middle - width
        close = closes[-1]
        if middle <= close <= upper:
            state = "supportive"
            reason = "收盘价位于布林中轨与上轨之间，技术状态偏支持。"
        elif close < lower or close > upper * 1.01:
            state = "caution"
            reason = "收盘价偏离布林区间，技术状态偏谨慎。"
        else:
            state = "neutral"
            reason = "布林区间位置未形成明显支持或谨慎状态。"
        return {
            "id": "bollinger",
            "label": "Bollinger",
            "state": state,
            "metrics": {
                "close": _round_optional(close),
                "middle": _round_optional(middle),
                "upper": _round_optional(upper),
                "lower": _round_optional(lower),
            },
            "reason": reason,
            "warnings": [],
        }

    @staticmethod
    def _rsi_value(closes: Sequence[float], period: int = 14) -> Optional[float]:
        if len(closes) <= period:
            return None
        changes = [closes[i] - closes[i - 1] for i in range(len(closes) - period, len(closes))]
        gains = [max(change, 0.0) for change in changes]
        losses = [abs(min(change, 0.0)) for change in changes]
        avg_gain = _mean(gains) or 0.0
        avg_loss = _mean(losses) or 0.0
        if avg_loss == 0:
            return 100.0 if avg_gain > 0 else 50.0
        rs = avg_gain / avg_loss
        return 100.0 - (100.0 / (1.0 + rs))

    @staticmethod
    def _position_risk(closes: Sequence[float]) -> Dict[str, Any]:
        if len(closes) < 60:
            return {
                "status": "data_insufficient",
                "label": "数据不足",
                "score": None,
                "reason": "日线样本少于 60 根，暂不判断当前位置。",
                "metrics": {},
                "warnings": ["position_risk_data_insufficient"],
            }

        close = float(closes[-1])
        ma20 = _mean(closes[-20:])
        ma60 = _mean(closes[-60:])
        window120 = list(closes[-120:]) if len(closes) >= 120 else list(closes)
        price_percentile = _percentile_rank(window120, close)
        rsi14 = TWStockTechnicalStatusService._rsi_value(closes)
        distance_ma20 = _ratio_pct(close, ma20)
        distance_ma60 = _ratio_pct(close, ma60)
        return_5d = _ratio_pct(close, closes[-6]) if len(closes) >= 6 else None
        return_20d = _ratio_pct(close, closes[-21]) if len(closes) >= 21 else None

        bollinger_position = None
        if len(closes) >= 20:
            boll_window = list(closes[-20:])
            middle = _mean(boll_window) or 0.0
            width = pstdev(boll_window) * 2.0 if len(boll_window) >= 2 else 0.0
            lower = middle - width
            upper = middle + width
            if upper > lower:
                bollinger_position = (close - lower) / (upper - lower)

        risk_points = 0
        reasons: List[str] = []
        if price_percentile is not None:
            if price_percentile >= 92:
                risk_points += 32
                reasons.append("接近近 120 日高位")
            elif price_percentile >= 85:
                risk_points += 22
                reasons.append("处于近 120 日偏高区间")
            elif price_percentile <= 35:
                risk_points -= 8
                reasons.append("不在区间高位")
        if rsi14 is not None:
            if rsi14 >= 72:
                risk_points += 28
                reasons.append("RSI 偏热")
            elif rsi14 >= 68:
                risk_points += 18
                reasons.append("RSI 略偏热")
        if distance_ma20 is not None:
            if distance_ma20 >= 12:
                risk_points += 32
                reasons.append("距离 20 日均线较远")
            elif distance_ma20 >= 8:
                risk_points += 20
                reasons.append("距离 20 日均线偏远")
            elif -4 <= distance_ma20 <= 6:
                risk_points -= 8
                reasons.append("接近 20 日均线")
        if bollinger_position is not None:
            if bollinger_position >= 1.02:
                risk_points += 22
                reasons.append("越过布林上沿")
            elif bollinger_position >= 0.88:
                risk_points += 12
                reasons.append("靠近布林上沿")
        if return_5d is not None and return_5d >= 8:
            risk_points += 10
            reasons.append("近 5 日涨幅较快")
        if return_20d is not None and return_20d >= 18:
            risk_points += 10
            reasons.append("近 20 日涨幅较大")

        score = max(0, min(100, 35 + risk_points))
        overheated = (price_percentile is not None and price_percentile >= 92 and rsi14 is not None and rsi14 >= 72) or (distance_ma20 is not None and distance_ma20 >= 12)
        elevated = (price_percentile is not None and price_percentile >= 85) or (rsi14 is not None and rsi14 >= 68) or (distance_ma20 is not None and distance_ma20 >= 8)
        pullback_watch = (distance_ma20 is not None and -4 <= distance_ma20 <= 3 and price_percentile is not None and 45 <= price_percentile <= 82)
        if overheated:
            status = "overheated"
            label = "过热谨慎"
        elif elevated:
            status = "elevated"
            label = "强势但偏高"
        elif pullback_watch:
            status = "pullback_watch"
            label = "回调观察"
        else:
            status = "reasonable"
            label = "位置合理"

        reason = "，".join(dict.fromkeys(reasons[:3])) if reasons else "价格位置未显示明显偏高信号。"
        if status == "reasonable" and reasons:
            reason = "位置相对可观察；" + reason
        return {
            "status": status,
            "label": label,
            "score": int(round(score)),
            "reason": reason,
            "metrics": {
                "close": _round_optional(close, 4),
                "ma20": _round_optional(ma20, 4),
                "ma60": _round_optional(ma60, 4),
                "distance_ma20_pct": _round_optional(distance_ma20, 2),
                "distance_ma60_pct": _round_optional(distance_ma60, 2),
                "rsi14": _round_optional(rsi14, 2),
                "price_percentile_120d": _round_optional(price_percentile, 2),
                "bollinger_position": _round_optional(bollinger_position, 4),
                "return_5d_pct": _round_optional(return_5d, 2),
                "return_20d_pct": _round_optional(return_20d, 2),
            },
            "warnings": [],
        }

    @staticmethod
    def _insufficient_item(strategy_id: str, reason: str) -> Dict[str, Any]:
        labels = {"ma": "MA", "rsi": "RSI", "macd": "MACD", "bollinger": "Bollinger"}
        return {
            "id": strategy_id,
            "label": labels.get(strategy_id, strategy_id.upper()),
            "state": "data_insufficient",
            "metrics": {},
            "reason": reason,
            "warnings": [f"{strategy_id}_data_insufficient"],
        }

    @staticmethod
    def _summary(items: Sequence[Dict[str, Any]]) -> Dict[str, int]:
        summary = {"supportive_count": 0, "neutral_count": 0, "caution_count": 0, "data_insufficient_count": 0}
        for item in items:
            state = str(item.get("state") or "data_insufficient")
            if state == "supportive":
                summary["supportive_count"] += 1
            elif state == "caution":
                summary["caution_count"] += 1
            elif state == "neutral":
                summary["neutral_count"] += 1
            else:
                summary["data_insufficient_count"] += 1
        return summary

    @staticmethod
    def _overall_status(summary: Dict[str, int]) -> str:
        if int(summary.get("data_insufficient_count") or 0) >= 3:
            return "technical_data_insufficient"
        if int(summary.get("caution_count") or 0) >= 2:
            return "technical_weak"
        if int(summary.get("supportive_count") or 0) >= 2 and int(summary.get("caution_count") or 0) == 0:
            return "technical_strong"
        return "technical_neutral"

    @staticmethod
    def _warnings(items: Sequence[Dict[str, Any]]) -> List[str]:
        warnings: List[str] = []
        for item in items:
            for warning in item.get("warnings") or []:
                text = str(warning)
                if text and text not in warnings:
                    warnings.append(text)
        return warnings
