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

ACTION_PLAN_LABELS = {
    "simulate_watch": "可模拟观察",
    "wait_pullback": "等回调",
    "chasing_review": "追高复核",
    "continue_observe": "继续观察",
    "risk_review": "风险复盘",
    "data_review": "资料复核",
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
        position_risk = self._position_risk_from_technical(technical)
        decision = self.decision_for(rank_tier=rank_tier, technical_status=technical["status"], position_risk=position_risk)
        action_plan = self.action_plan_for(
            rank_tier=rank_tier,
            technical_status=technical["status"],
            trend_label=trend.get("trend_label"),
            position_risk=position_risk,
            decision=decision,
        )
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
            "positionRisk": position_risk,
            "decision": decision,
            "actionPlan": action_plan,
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
            "positionRisk": indicators.get("positionRisk") or {},
            "warnings": warnings,
            "reason": reason,
        }

    @staticmethod
    def _position_risk_from_technical(technical: Dict[str, Any]) -> Dict[str, Any]:
        risk = technical.get("positionRisk") if isinstance(technical, dict) else None
        if isinstance(risk, dict) and risk.get("status"):
            return risk
        return {"status": "data_insufficient", "label": "数据不足", "score": None, "reason": "暂未计算价格位置。", "metrics": {}, "warnings": ["position_risk_missing"]}

    @staticmethod
    def decision_for(*, rank_tier: str, technical_status: str, position_risk: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        risk_status = str((position_risk or {}).get("status") or "")
        if technical_status == "technical_data_insufficient":
            code, priority = "data_insufficient", "blocked"
        elif rank_tier in {"top10", "top30"} and technical_status == "technical_strong" and risk_status == "overheated":
            code, priority = "manual_review", "medium"
        elif rank_tier in {"top10", "top30"} and technical_status == "technical_strong" and risk_status == "elevated":
            code, priority = "continue_watch", "medium"
        elif rank_tier in {"top10", "top30"} and technical_status == "technical_strong":
            code, priority = "new_watch", "high"
        elif rank_tier in {"top10", "top30"} and technical_status == "technical_neutral":
            code, priority = "continue_watch", "medium"
        elif rank_tier in {"top10", "top30"} and technical_status == "technical_weak":
            code, priority = "manual_review", "medium"
        elif rank_tier == "top50" and risk_status == "overheated":
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
                position_risk=position_risk,
            ),
        }

    @staticmethod
    def _decision_reason(*, code: str, rank_tier: str, technical_status: str, position_risk: Optional[Dict[str, Any]] = None) -> str:
        risk_status = str((position_risk or {}).get("status") or "")
        risk_label = str((position_risk or {}).get("label") or "")
        if risk_status == "overheated":
            return f"qlib {rank_tier} 且趋势偏强，但位置为{risk_label or '过热谨慎'}，先交由人工复核。"
        if risk_status == "elevated" and code == "continue_watch":
            return f"qlib {rank_tier} 且趋势偏强，但位置为{risk_label or '强势但偏高'}，先继续观察追高风险。"
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


    @staticmethod
    def action_plan_for(
        *,
        rank_tier: str,
        technical_status: str,
        trend_label: Optional[str] = None,
        position_risk: Optional[Dict[str, Any]] = None,
        decision: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Translate model signals into user-facing research steps.

        This is deliberately not an order instruction. It separates selection
        quality from current price position so a high rank does not become a
        blind chase and a short-term rank drop does not become an automatic exit.
        """
        risk_status = str((position_risk or {}).get("status") or "")
        risk_label = str((position_risk or {}).get("label") or "")
        trend = str(trend_label or "").strip().lower()
        top_pool = rank_tier in {"top10", "top30"}
        strong_or_rebound = trend in STRONG_TRENDS or technical_status == "technical_strong"
        weak_confirmed = trend in WEAK_TRENDS and technical_status == "technical_weak"
        if technical_status == "technical_data_insufficient":
            code, priority = "data_review", "blocked"
            reason = "资料还不完整，先不要提高优先级。"
            next_check = "补齐日线和指标后再复盘。"
        elif top_pool and strong_or_rebound and risk_status == "reasonable":
            code, priority = "simulate_watch", "high"
            reason = "排名和趋势有支持，价格位置未显示明显偏高。"
            next_check = "只适合放入模拟观察，继续看后续回放表现。"
        elif top_pool and strong_or_rebound and risk_status == "elevated":
            code, priority = "wait_pullback", "medium"
            reason = "标的值得看，但当前位置偏高，直接追容易买在短线高点。"
            next_check = "等价格靠近关键均线或热度降温后再复盘。"
        elif top_pool and strong_or_rebound and risk_status == "overheated":
            code, priority = "chasing_review", "medium"
            reason = "趋势强不等于适合现在介入，当前位置已经偏热。"
            next_check = "先做人工复核或等待回调，不把它放入高优先模拟新增。"
        elif top_pool and risk_status == "pullback_watch":
            code, priority = "continue_observe", "medium"
            reason = "正在回调，关键是确认趋势有没有被破坏。"
            next_check = "观察是否守住均线、MACD/RSI 是否继续恶化。"
        elif weak_confirmed or (rank_tier == "outside_top50" and technical_status == "technical_weak"):
            code, priority = "risk_review", "medium"
            reason = "排名或趋势转弱已经有技术确认，适合做风险复盘。"
            next_check = "优先检查是否连续转弱，而不是只看单日排名波动。"
        elif (decision or {}).get("code") == "manual_review":
            code, priority = "chasing_review" if risk_status == "overheated" else "continue_observe", "medium"
            reason = "模型、趋势、指标或位置没有形成一致结论。"
            next_check = "只做复核，不直接扩大模拟暴露。"
        else:
            code, priority = "continue_observe", "low"
            reason = "当前更像观察信号，还缺少明确入场或退出确认。"
            next_check = "继续观察排名持续性、趋势和位置变化。"
        return {
            "code": code,
            "label": ACTION_PLAN_LABELS[code],
            "priority": priority,
            "reason": reason,
            "nextCheck": next_check,
            "positionLabel": risk_label,
            "research_only": True,
            "simulation_only": True,
        }

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
            "position_risk_basis": "daily_price_position" if include_technical_strategies else "not_used",
            "action_plan_basis": "rank_trend_indicator_position_research_step",
            "note": note,
        }
