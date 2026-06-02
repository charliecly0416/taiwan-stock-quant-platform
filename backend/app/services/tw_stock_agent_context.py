"""Read-only context and deterministic preview for the TWStock research agent."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.services.tw_stock_agent_guardrails import (
    BLOCKED_ANSWER,
    RESEARCH_ONLY_DISCLAIMER,
    TWStockAgentGuardrails,
)
from app.services.tw_stock_cross_analysis import TWStockCrossAnalysisService
from app.services.tw_stock_qlib_option_c import research_only_trading_flags


class TWStockAgentContextService:
    """Build read-only Agent context from accepted qlib signals and cross analysis."""

    def __init__(self, *, cross_service: Optional[Any] = None, guardrails: Optional[TWStockAgentGuardrails] = None) -> None:
        self.cross_service = cross_service or TWStockCrossAnalysisService()
        self.guardrails = guardrails or TWStockAgentGuardrails()

    def context(self, *, max_items: int = 10) -> Dict[str, Any]:
        normalized_max = self._normalize_max_items(max_items)
        payload = self.cross_service.latest(bucket="top30", limit=120, include_raw_trend=False, max_items=30)
        if not payload.get("ok"):
            return self._blocked_context(payload)

        items = list(payload.get("items") or [])
        qlib = payload.get("qlib") or {}
        return {
            "ok": True,
            "status": payload.get("status") or "accepted",
            "qlib": self._qlib_context(qlib),
            "cross_analysis": {
                "summary": payload.get("summary") or {},
                "basis": payload.get("basis") or {},
            },
            "top30_preview": self._compact_items(items, limit=normalized_max),
            "focus_watch_preview": self._compact_items(self._filter_by_category(items, "focus_watch"), limit=normalized_max),
            "divergence_preview": self._compact_items(self._filter_by_category(items, "model_trend_divergence"), limit=normalized_max),
            "data_review_preview": self._compact_items(self._filter_by_category(items, "data_review_required"), limit=normalized_max),
            "freshness": payload.get("freshness") or {},
            "allowed_intents": self.guardrails.allowed_intents,
            "blocked_intents": self.guardrails.blocked_intents,
            "disclaimers": self.guardrails.disclaimers,
            "trading": research_only_trading_flags(),
        }

    def preview(self, *, question: str, symbol: str = "", max_items: int = 10) -> Dict[str, Any]:
        normalized_max = self._normalize_max_items(max_items)
        intent = self.guardrails.classify(question, symbol=symbol)
        if intent.blocked:
            return {
                "ok": True,
                "intent": intent.intent,
                "blocked": True,
                "answer_draft": BLOCKED_ANSWER,
                "citations": [],
                "items": [],
                "warnings": [intent.reason],
                "research_only_disclaimer": RESEARCH_ONLY_DISCLAIMER,
                "context_digest": {"status": "blocked", "intent": intent.intent},
                "trading": research_only_trading_flags(),
            }

        if intent.intent == "single_symbol_metrics" and intent.symbol:
            return self._single_symbol_preview(symbol=intent.symbol, intent=intent.intent)

        bucket = "top50" if intent.intent == "today_top50" else "top30"
        payload = self.cross_service.latest(bucket=bucket, limit=120, include_raw_trend=False, max_items=50 if bucket == "top50" else 30)
        if not payload.get("ok"):
            return self._unavailable_preview(intent=intent.intent, payload=payload)

        items = list(payload.get("items") or [])
        selected = self._items_for_intent(items, intent.intent)
        compact = self._compact_items(selected, limit=normalized_max)
        answer = self._answer_for_intent(intent.intent, compact, payload)
        return {
            "ok": True,
            "intent": intent.intent,
            "blocked": False,
            "answer_draft": answer,
            "citations": self._citations(payload=payload, bucket=bucket),
            "items": compact,
            "warnings": list((payload.get("freshness") or {}).get("warnings") or []),
            "research_only_disclaimer": RESEARCH_ONLY_DISCLAIMER,
            "context_digest": self._context_digest(payload=payload, item_count=len(compact)),
            "trading": research_only_trading_flags(),
        }

    def _single_symbol_preview(self, *, symbol: str, intent: str) -> Dict[str, Any]:
        payload = self.cross_service.symbol_detail(symbol=symbol, limit=120, include_raw_trend=False)
        item = payload.get("item") or {}
        compact_items = self._compact_items([item], limit=1) if item else []
        if compact_items:
            answer = f"{symbol} 当前 qlib/cross-analysis 摘要：{self._item_phrase(compact_items[0])}。{RESEARCH_ONLY_DISCLAIMER}"
        else:
            answer = f"{symbol} 未出现在 latest qlib top50 研究排序中，可参考趋势摘要并先做人工复盘。{RESEARCH_ONLY_DISCLAIMER}"
        return {
            "ok": True,
            "intent": intent,
            "blocked": False,
            "answer_draft": answer,
            "citations": self._citations(payload=payload, bucket="all", symbol=symbol),
            "items": compact_items,
            "warnings": list((payload.get("freshness") or {}).get("warnings") or []),
            "research_only_disclaimer": RESEARCH_ONLY_DISCLAIMER,
            "context_digest": self._context_digest(payload=payload, item_count=len(compact_items)),
            "trading": research_only_trading_flags(),
        }

    def _blocked_context(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "ok": False,
            "status": payload.get("status") or "context_unavailable",
            "message": payload.get("message"),
            "qlib": payload.get("qlib"),
            "cross_analysis": {"summary": payload.get("summary") or {}, "basis": payload.get("basis") or {}},
            "top30_preview": [],
            "focus_watch_preview": [],
            "divergence_preview": [],
            "data_review_preview": [],
            "freshness": payload.get("freshness") or {},
            "allowed_intents": self.guardrails.allowed_intents,
            "blocked_intents": self.guardrails.blocked_intents,
            "disclaimers": self.guardrails.disclaimers,
            "trading": research_only_trading_flags(),
        }

    def _unavailable_preview(self, *, intent: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        message = payload.get("message") or payload.get("status") or "context_unavailable"
        return {
            "ok": False,
            "intent": intent,
            "blocked": False,
            "answer_draft": f"当前台股研究上下文不可用：{message}。{RESEARCH_ONLY_DISCLAIMER}",
            "citations": [],
            "items": [],
            "warnings": list(payload.get("warnings") or [message]),
            "research_only_disclaimer": RESEARCH_ONLY_DISCLAIMER,
            "context_digest": {"status": payload.get("status") or "context_unavailable"},
            "trading": research_only_trading_flags(),
        }

    @staticmethod
    def _normalize_max_items(max_items: int) -> int:
        try:
            value = int(max_items or 10)
        except Exception:
            value = 10
        return max(1, min(value, 20))

    @staticmethod
    def _qlib_context(qlib: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "asof": qlib.get("asof"),
            "run_id": qlib.get("run_id"),
            "target_horizon": qlib.get("target_horizon"),
            "research_signal_not_order": True,
            "signal_semantics": qlib.get("signal_semantics"),
            "recommendation_semantics": qlib.get("recommendation_semantics"),
        }

    @classmethod
    def _compact_items(cls, items: List[Dict[str, Any]], *, limit: int) -> List[Dict[str, Any]]:
        compact: List[Dict[str, Any]] = []
        for item in items[:limit]:
            qlib = item.get("qlib") or {}
            quant = item.get("quantdinger") or item.get("trend") or {}
            cross = item.get("cross") or {}
            basis = item.get("data_basis") or {}
            compact.append({
                "symbol": item.get("symbol"),
                "instrument": item.get("instrument"),
                "qlib_rank": qlib.get("rank"),
                "qlib_bucket": qlib.get("bucket"),
                "qlib_score": qlib.get("score"),
                "trend_label": quant.get("trend_label"),
                "trend_score": quant.get("trend_score"),
                "latest_date": quant.get("latest_date"),
                "quality_warnings": quant.get("quality_warnings") or [],
                "cross_category": cross.get("category"),
                "alignment": cross.get("alignment"),
                "priority": cross.get("priority"),
                "human_action": cross.get("human_action"),
                "data_basis_status": basis.get("data_basis_status"),
                "date_gap_days": basis.get("date_gap_days"),
            })
        return compact

    @staticmethod
    def _filter_by_category(items: List[Dict[str, Any]], category: str) -> List[Dict[str, Any]]:
        return [item for item in items if (item.get("cross") or {}).get("category") == category]

    @classmethod
    def _items_for_intent(cls, items: List[Dict[str, Any]], intent: str) -> List[Dict[str, Any]]:
        mapping = {
            "focus_watch": "focus_watch",
            "secondary_watch": "secondary_watch",
            "model_trend_divergence": "model_trend_divergence",
            "data_review_required": "data_review_required",
        }
        category = mapping.get(intent)
        return cls._filter_by_category(items, category) if category else items

    @classmethod
    def _answer_for_intent(cls, intent: str, items: List[Dict[str, Any]], payload: Dict[str, Any]) -> str:
        if intent == "freshness_and_data_basis":
            freshness = payload.get("freshness") or {}
            qlib = freshness.get("qlib") or payload.get("qlib") or {}
            return (
                f"当前 qlib asof={qlib.get('asof')}，run_id={qlib.get('run_id')}；"
                f"freshness={freshness.get('status')}，raw 日期范围="
                f"{(freshness.get('quantdinger') or {}).get('latest_date_min')} 到 {(freshness.get('quantdinger') or {}).get('latest_date_max')}。"
                f"{RESEARCH_ONLY_DISCLAIMER}"
            )
        if not items:
            return f"当前上下文没有匹配 {intent} 的项目，建议先检查 freshness 和数据质量。{RESEARCH_ONLY_DISCLAIMER}"
        joined = "；".join(cls._item_phrase(item) for item in items[:10])
        return f"{intent} 预览：{joined}。{RESEARCH_ONLY_DISCLAIMER}"

    @staticmethod
    def _item_phrase(item: Dict[str, Any]) -> str:
        return (
            f"{item.get('symbol')} rank={item.get('qlib_rank')} score={item.get('qlib_score')} "
            f"trend={item.get('trend_label')} category={item.get('cross_category')} action={item.get('human_action')}"
        )

    @staticmethod
    def _citations(*, payload: Dict[str, Any], bucket: str, symbol: str = "") -> List[str]:
        qlib = payload.get("qlib") or {}
        citations = [
            f"qlib:accepted_latest:{qlib.get('run_id')}:{qlib.get('asof')}",
            f"cross-analysis:latest:{bucket}",
        ]
        if symbol:
            citations.append(f"tw-stock:cross-analysis:symbol:{symbol}")
        return citations

    @staticmethod
    def _context_digest(*, payload: Dict[str, Any], item_count: int) -> Dict[str, Any]:
        qlib = payload.get("qlib") or {}
        freshness = payload.get("freshness") or {}
        summary = payload.get("summary") or {}
        return {
            "status": payload.get("status"),
            "qlib_asof": qlib.get("asof"),
            "qlib_run_id": qlib.get("run_id"),
            "target_horizon": qlib.get("target_horizon"),
            "freshness_status": freshness.get("status"),
            "category_counts": summary.get("category_counts") or {},
            "item_count": item_count,
        }
