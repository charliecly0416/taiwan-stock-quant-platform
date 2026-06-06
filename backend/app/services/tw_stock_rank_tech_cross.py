"""Read-only rank, trend and technical-status cross classification for TWStock.

This service reads accepted qlib ranking artifacts and QuantDinger daily trend
snapshots only. It never writes simulation accounts, orders, positions, monitor
config, alerts, qlib provider state, or accepted-latest state.
"""
from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional

from app.services.tw_stock_qlib_option_c import (
    QlibOptionCSignalError,
    QlibOptionCSignalReader,
    research_only_trading_flags,
)
from app.services.tw_stock_trend import TWStockTrendService
from app.services.tw_stock_technical_status import TWStockTechnicalStatusService


DECISION_LABELS = {
    "new_watch": "新增观察",
    "continue_watch": "继续观察",
    "risk_review": "风险复盘",
    "manual_review": "人工复核",
    "observe_only": "仅观察",
    "data_insufficient": "数据不足",
}

SUMMARY_TEMPLATE = {
    "new_watch": 0,
    "continue_watch": 0,
    "risk_review": 0,
    "manual_review": 0,
    "observe_only": 0,
    "data_insufficient": 0,
}

SERIOUS_QUALITY_WARNINGS = {
    "no_daily_bars",
    "data_source_unavailable",
    "stale_daily_bar",
    "latest_bar_in_future",
    "invalid_twstock_symbol",
    "short_history_below_60_bars",
}
STRONG_TRENDS = {"uptrend", "rebound"}
WEAK_TRENDS = {"downtrend", "pullback"}
NEUTRAL_TRENDS = {"sideways", "unknown"}


def blocked_rank_tech_cross_payload(status: str, message: str, *, warnings: Optional[List[str]] = None) -> Dict[str, Any]:
    flags = research_only_trading_flags()
    return {
        "ok": False,
        "status": status,
        "message": message,
        "simulation_only": True,
        "research_signal_not_order": True,
        "bucket": None,
        "limit": None,
        "maxItems": None,
        "qlib": None,
        "items": [],
        "summary": dict(SUMMARY_TEMPLATE),
        "warnings": warnings or [],
        "trading": flags,
    }


class TWStockRankTechCrossService:
    """Create a stable research-only classification from qlib rank and trend."""

    def __init__(self, *, qlib_reader: Optional[Any] = None, trend_service: Optional[Any] = None, technical_service: Optional[Any] = None) -> None:
        self.qlib_reader = qlib_reader or QlibOptionCSignalReader()
        self.trend_service = trend_service or TWStockTrendService()
        self.technical_service = technical_service or TWStockTechnicalStatusService()

    def latest(
        self,
        *,
        bucket: str = "top30",
        limit: int = 120,
        max_items: Optional[int] = None,
        include_technical_strategies: bool = True,
        technical_strategies: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        normalized_bucket = self._normalize_bucket(bucket)
        normalized_limit = self._normalize_limit(limit)
        normalized_max = self._normalize_max_items(max_items, normalized_bucket)
        try:
            qlib_payload = self.qlib_reader.latest(bucket=normalized_bucket, enrich_trend=False)
        except QlibOptionCSignalError as exc:
            return blocked_rank_tech_cross_payload(exc.status, exc.message, warnings=exc.warnings)

        rows = self._rows_for_bucket(qlib_payload, normalized_bucket)[:normalized_max]
        items = [
            self._item_from_signal(
                row,
                qlib_payload=qlib_payload,
                trend_limit=normalized_limit,
                include_technical_strategies=include_technical_strategies,
                technical_strategies=technical_strategies,
            )
            for row in rows
        ]
        return {
            "ok": True,
            "status": "accepted",
            "simulation_only": True,
            "research_signal_not_order": True,
            "bucket": normalized_bucket,
            "limit": normalized_limit,
            "maxItems": normalized_max,
            "qlib": self._qlib_summary(qlib_payload),
            "items": items,
            "summary": self._summary_counts(items),
            "includeTechnicalStrategies": bool(include_technical_strategies),
            "technicalStrategies": self._normalize_technical_strategies(technical_strategies),
            "basis": self.basis_contract(include_technical_strategies=include_technical_strategies),
            "warnings": list(qlib_payload.get("warnings") or []),
            "trading": research_only_trading_flags(),
        }

    def _item_from_signal(
        self,
        row: Dict[str, Any],
        *,
        qlib_payload: Dict[str, Any],
        trend_limit: int,
        include_technical_strategies: bool,
        technical_strategies: Optional[List[str]],
    ) -> Dict[str, Any]:
        symbol = str(row.get("symbol") or "").strip()
        rank_tier = self.rank_tier(row.get("rank"))
        trend = self._safe_trend_snapshot(symbol, trend_limit=trend_limit)
        technical = self.technical_status_from_trend(trend)
        if include_technical_strategies:
            technical = self.technical_status_from_trend_and_indicators(
                symbol=symbol,
                trend=trend,
                limit=trend_limit,
                strategies=technical_strategies,
            )
        decision = self.decision_for(rank_tier=rank_tier, technical_status=technical["status"])
        return {
            "symbol": symbol,
            "instrument": row.get("instrument"),
            "name": row.get("name") or row.get("symbol_name") or "",
            "rank": row.get("rank"),
            "rankTier": rank_tier,
            "qlib": {
                "bucket": row.get("bucket"),
                "rank": row.get("rank"),
                "score": row.get("qlib_score", row.get("score")),
                "asof": qlib_payload.get("asof"),
            },
            "trend": {
                "label": trend.get("trend_label"),
                "score": trend.get("trend_score"),
                "latest_date": trend.get("latest_date"),
                "ok": bool(trend.get("ok")),
                "warnings": trend.get("quality_warnings") or [],
            },
            "technical": technical,
            "decision": decision,
        }

    @staticmethod
    def rank_tier(rank: Any) -> str:
        try:
            value = int(rank)
        except Exception:
            return "outside_top50"
        if value <= 10:
            return "top10"
        if value <= 30:
            return "top30"
        if value <= 50:
            return "top50"
        return "outside_top50"

    @staticmethod
    def technical_status_from_trend(trend: Dict[str, Any]) -> Dict[str, Any]:
        warnings = [str(item) for item in (trend.get("quality_warnings") or [])]
        warning_set = set(warnings)
        label = str(trend.get("trend_label") or "").strip().lower()
        if warning_set & SERIOUS_QUALITY_WARNINGS or not trend.get("ok") or not label:
            status = "technical_data_insufficient"
        elif label in STRONG_TRENDS:
            status = "technical_strong"
        elif label in WEAK_TRENDS:
            status = "technical_weak"
        elif label in NEUTRAL_TRENDS:
            status = "technical_neutral"
        else:
            status = "technical_neutral"
        return {
            "status": status,
            "basis": "quantdinger_trend_only",
            "strategies": [],
            "warnings": warnings,
        }


    def technical_status_from_trend_and_indicators(
        self,
        *,
        symbol: str,
        trend: Dict[str, Any],
        limit: int,
        strategies: Optional[List[str]],
        as_of: Optional[date] = None,
    ) -> Dict[str, Any]:
        trend_technical = self.technical_status_from_trend(trend)
        try:
            indicators = self.technical_service.analyze_symbol(symbol=symbol, limit=limit, strategies=strategies, as_of=as_of)
        except Exception as exc:
            indicators = {
                "status": "technical_data_insufficient",
                "summary": {"supportive_count": 0, "neutral_count": 0, "caution_count": 0, "data_insufficient_count": 4},
                "strategies": [],
                "warnings": ["technical_status_service_error"],
                "error": str(exc),
            }
        indicator_status = str(indicators.get("status") or "technical_data_insufficient")
        trend_status = str(trend_technical.get("status") or "technical_data_insufficient")
        if trend_status == "technical_data_insufficient":
            status = indicator_status
            reason = "趋势数据不足，优先参考轻量日线指标摘要。"
        elif trend_status == "technical_strong" and indicator_status == "technical_weak":
            status = "technical_neutral"
            reason = "趋势与指标分歧，人工复核优先。"
        elif trend_status == "technical_weak" and indicator_status == "technical_strong":
            status = "technical_neutral"
            reason = "指标修复但趋势仍需确认。"
        elif indicator_status == "technical_data_insufficient":
            status = trend_status
            reason = "指标样本不足，暂以趋势状态为主。"
        elif trend_status == "technical_weak" or indicator_status == "technical_weak":
            status = "technical_weak"
            reason = "趋势或指标出现谨慎状态，降低技术确认强度。"
        elif trend_status == "technical_strong" and indicator_status == "technical_strong":
            status = "technical_strong"
            reason = "趋势和轻量指标状态一致偏支持。"
        else:
            status = "technical_neutral"
            reason = "趋势和轻量指标未形成一致强确认。"
        warnings = list(dict.fromkeys(list(trend_technical.get("warnings") or []) + list(indicators.get("warnings") or [])))
        return {
            "status": status,
            "basis": "quantdinger_trend_plus_daily_indicators",
            "summary": indicators.get("summary") or {},
            "strategies": list(indicators.get("strategies") or []),
            "warnings": warnings,
            "reason": reason,
        }

    @staticmethod
    def decision_for(*, rank_tier: str, technical_status: str) -> Dict[str, Any]:
        if technical_status == "technical_data_insufficient":
            code, priority = "data_insufficient", "blocked"
        elif rank_tier in {"top10", "top30"} and technical_status == "technical_strong":
            code, priority = "new_watch", "high"
        elif rank_tier in {"top10", "top30"} and technical_status == "technical_neutral":
            code, priority = "continue_watch", "medium"
        elif rank_tier in {"top10", "top30"} and technical_status == "technical_weak":
            code, priority = "manual_review", "medium"
        elif rank_tier == "top50":
            code, priority = "observe_only", "low"
        elif rank_tier == "outside_top50" and technical_status == "technical_weak":
            code, priority = "risk_review", "medium"
        elif rank_tier == "outside_top50" and technical_status == "technical_strong":
            code, priority = "manual_review", "medium"
        else:
            code, priority = "observe_only", "low"
        return {
            "code": code,
            "label": DECISION_LABELS[code],
            "priority": priority,
            "reason": TWStockRankTechCrossService._decision_reason(
                code=code,
                rank_tier=rank_tier,
                technical_status=technical_status,
            ),
        }

    @staticmethod
    def _decision_reason(*, code: str, rank_tier: str, technical_status: str) -> str:
        if code == "new_watch":
            return f"qlib {rank_tier} 且 QuantDinger 趋势偏强，进入优先复盘队列。"
        if code == "continue_watch":
            return f"qlib {rank_tier} 但技术状态偏中性，继续保留在观察队列。"
        if code == "manual_review":
            return f"qlib {rank_tier} 与技术状态存在分歧，交由人工复核。"
        if code == "risk_review":
            return "不在 qlib Top50 且技术状态偏弱，进入风险复盘队列。"
        if code == "data_insufficient":
            return "趋势数据不足或质量提示较重，暂不做强弱判断。"
        return "位于扩展观察范围，当前只做低优先级观察。"

    def _safe_trend_snapshot(self, symbol: str, *, trend_limit: int, as_of: Optional[date] = None) -> Dict[str, Any]:
        try:
            raw = self.trend_service.analyze_symbol(symbol=symbol, limit=trend_limit, as_of=as_of)
        except Exception as exc:
            return {
                "ok": False,
                "trend_label": None,
                "trend_score": None,
                "latest_date": None,
                "quality_warnings": ["trend_service_error"],
                "error": str(exc),
            }
        if not isinstance(raw, dict) or not raw.get("ok"):
            quality = raw.get("quality") if isinstance(raw, dict) else {}
            warnings = quality.get("warnings") if isinstance(quality, dict) else []
            return {
                "ok": False,
                "trend_label": None,
                "trend_score": None,
                "latest_date": quality.get("latest_date") if isinstance(quality, dict) else None,
                "quality_warnings": warnings if isinstance(warnings, list) else [],
                "error": (raw.get("error") if isinstance(raw, dict) else None) or "trend_unavailable",
            }
        trend = raw.get("trend") or {}
        latest = raw.get("latest") or {}
        quality = raw.get("quality") or {}
        warnings = quality.get("warnings") or []
        return {
            "ok": True,
            "trend_label": trend.get("label") or "unknown",
            "trend_score": trend.get("score"),
            "latest_date": latest.get("date") or quality.get("latest_date"),
            "quality_warnings": warnings if isinstance(warnings, list) else [],
            "error": None,
        }

    @staticmethod
    def _normalize_bucket(bucket: str) -> str:
        normalized = str(bucket or "top30").strip().lower()
        return normalized if normalized in {"top30", "top50", "all"} else "top30"

    @staticmethod
    def _normalize_limit(limit: int) -> int:
        try:
            value = int(limit or 120)
        except Exception:
            value = 120
        return max(20, min(value, 500))

    @staticmethod
    def _normalize_max_items(max_items: Optional[int], bucket: str) -> int:
        default = 30 if bucket == "top30" else 50
        if max_items is None:
            return default
        try:
            value = int(max_items)
        except Exception:
            value = default
        return max(1, min(value, 50))

    @staticmethod
    def _rows_for_bucket(payload: Dict[str, Any], bucket: str) -> List[Dict[str, Any]]:
        if bucket in {"top30", "top50"}:
            return list(payload.get("signals") or [])
        rows: List[Dict[str, Any]] = []
        seen = set()
        for row in list(payload.get("top30") or []) + list(payload.get("top50") or []):
            symbol = str(row.get("symbol") or "")
            if symbol and symbol not in seen:
                seen.add(symbol)
                rows.append(row)
        rows.sort(key=lambda item: int(item.get("rank") or 999999))
        return rows

    @staticmethod
    def _qlib_summary(payload: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "asof": payload.get("asof"),
            "run_id": payload.get("run_id"),
            "recorder_id": payload.get("recorder_id"),
            "target_horizon": payload.get("target_horizon"),
            "target_date": payload.get("target_date"),
            "signal_semantics": payload.get("signal_semantics"),
            "recommendation_semantics": payload.get("recommendation_semantics"),
            "research_signal_not_order": True,
            "summary": payload.get("summary") or {},
        }

    @staticmethod
    def _summary_counts(items: List[Dict[str, Any]]) -> Dict[str, int]:
        counts = dict(SUMMARY_TEMPLATE)
        for item in items:
            code = str((item.get("decision") or {}).get("code") or "")
            if code in counts:
                counts[code] += 1
        return counts

    @staticmethod
    def _normalize_technical_strategies(strategies: Optional[List[str]]) -> List[str]:
        valid = {"ma", "rsi", "macd", "bollinger"}
        if not strategies:
            return ["ma", "rsi", "macd", "bollinger"]
        out = []
        for raw in strategies:
            item = str(raw or "").strip().lower()
            if item in valid and item not in out:
                out.append(item)
        return out or ["ma", "rsi", "macd", "bollinger"]

    @staticmethod
    def basis_contract(*, include_technical_strategies: bool = True) -> Dict[str, Any]:
        technical_basis = "quantdinger_trend_plus_daily_indicators" if include_technical_strategies else "quantdinger_trend_only"
        note = "Step2 uses qlib ranking, QuantDinger daily trend, and lightweight MA/RSI/MACD/Bollinger indicator states." if include_technical_strategies else "Technical strategies disabled for this request; Step1 trend-only basis is used."
        return {
            "qlib_source": "Yahoo adjusted model signal",
            "quantdinger_source": "raw TWStock daily KlineService data",
            "technical_basis": technical_basis,
            "note": note,
        }
