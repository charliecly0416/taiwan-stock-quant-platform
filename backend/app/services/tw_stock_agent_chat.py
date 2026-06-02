"""Chat orchestration for the TWStock research agent."""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from app.services.tw_stock_agent_context import TWStockAgentContextService
from app.services.tw_stock_agent_guardrails import BLOCKED_ANSWER, RESEARCH_ONLY_DISCLAIMER, TWStockAgentGuardrails
from app.services.tw_stock_agent_openai import TWStockAgentOpenAIAdapter
from app.services.tw_stock_qlib_option_c import research_only_trading_flags


SAFE_REFUSAL_WARNING = "unsafe_model_output_overridden"


class TWStockAgentChatService:
    """Run guardrails, deterministic preview, optional OpenAI, then validate output."""

    _unsafe_answer_terms = (
        "必须买入",
        "必須買入",
        "必须卖出",
        "必須賣出",
        "保证上涨",
        "保證上漲",
        "保证收益",
        "保證收益",
        "目标仓位",
        "目標倉位",
        "下单",
        "下單",
        "自动交易",
        "自動交易",
        "broker",
        "IBKR",
        "qlib refresh",
        "refresh qlib",
        "publish",
        "retrain",
        "调参",
        "調參",
    )

    def __init__(
        self,
        *,
        context_service: Optional[TWStockAgentContextService] = None,
        openai_adapter: Optional[Any] = None,
        guardrails: Optional[TWStockAgentGuardrails] = None,
    ) -> None:
        self.context_service = context_service or TWStockAgentContextService()
        self.openai_adapter = openai_adapter or TWStockAgentOpenAIAdapter()
        self.guardrails = guardrails or TWStockAgentGuardrails()

    def chat(self, *, question: str, symbol: str = "", max_items: int = 10) -> Dict[str, Any]:
        preview = self.context_service.preview(question=question, symbol=symbol, max_items=max_items)
        if preview.get("blocked"):
            return self._from_preview(preview, mode="disabled")

        status = self.openai_adapter.status()
        if not status.get("enabled"):
            fallback = self._from_preview(preview, mode="disabled")
            fallback["warnings"] = self._merge_warnings(fallback.get("warnings"), [str(status.get("reason") or "openai_disabled")])
            return fallback

        controlled_context = self._controlled_context(question=question, preview=preview)
        result = self.openai_adapter.complete(controlled_context=controlled_context)
        if not result.get("ok"):
            fallback = self._from_preview(preview, mode=str(result.get("mode") or status.get("mode") or "disabled"))
            fallback["warnings"] = self._merge_warnings(fallback.get("warnings"), [str(result.get("status") or "openai_error")])
            return fallback

        validated = self._validate_model_content(
            content=str(result.get("content") or ""),
            preview=preview,
            mode=str(result.get("mode") or status.get("mode") or "openai"),
        )
        if validated is not None:
            return validated

        fallback = self._from_preview(preview, mode=str(result.get("mode") or status.get("mode") or "openai"))
        fallback["warnings"] = self._merge_warnings(fallback.get("warnings"), ["model_output_invalid_fallback_to_preview"])
        return fallback

    def _validate_model_content(self, *, content: str, preview: Dict[str, Any], mode: str) -> Optional[Dict[str, Any]]:
        try:
            parsed = json.loads(content)
        except Exception:
            return None
        if not isinstance(parsed, dict):
            return None

        answer = parsed.get("answer")
        citations = parsed.get("citations")
        warnings = parsed.get("warnings")
        disclaimer = parsed.get("research_only_disclaimer")
        intent = parsed.get("intent")
        if not isinstance(answer, str) or not answer.strip():
            return None
        if not isinstance(citations, list) or not all(isinstance(item, str) for item in citations):
            return None
        if not isinstance(warnings, list) or not all(isinstance(item, str) for item in warnings):
            return None
        if not isinstance(disclaimer, str) or "不构成交易建议" not in disclaimer:
            return None
        if not isinstance(intent, str) or intent != preview.get("intent"):
            return None

        allowed_citations = set(str(item) for item in (preview.get("citations") or []))
        if not citations or any(item not in allowed_citations for item in citations):
            return None

        if self._is_unsafe_answer(answer):
            return {
                "ok": True,
                "mode": mode,
                "intent": preview.get("intent"),
                "blocked": True,
                "answer": BLOCKED_ANSWER,
                "citations": [],
                "items": [],
                "warnings": self._merge_warnings(preview.get("warnings"), [SAFE_REFUSAL_WARNING]),
                "research_only_disclaimer": RESEARCH_ONLY_DISCLAIMER,
                "context_digest": preview.get("context_digest") or {},
                "trading": research_only_trading_flags(),
            }

        return {
            "ok": True,
            "mode": mode,
            "intent": intent,
            "blocked": False,
            "answer": answer.strip(),
            "citations": citations,
            "items": preview.get("items") or [],
            "warnings": self._merge_warnings(preview.get("warnings"), warnings),
            "research_only_disclaimer": disclaimer,
            "context_digest": preview.get("context_digest") or {},
            "trading": research_only_trading_flags(),
        }

    def _controlled_context(self, *, question: str, preview: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "intent": preview.get("intent"),
            "question": question,
            "context_digest": preview.get("context_digest") or {},
            "items": preview.get("items") or [],
            "citations": preview.get("citations") or [],
            "warnings": preview.get("warnings") or [],
            "research_only_disclaimer": preview.get("research_only_disclaimer") or RESEARCH_ONLY_DISCLAIMER,
            "allowed_answer_style": ["建议关注", "建议回避", "人工复盘", "数据复核"],
            "blocked_operations": self.guardrails.blocked_intents,
        }

    @staticmethod
    def _from_preview(preview: Dict[str, Any], *, mode: str) -> Dict[str, Any]:
        return {
            "ok": bool(preview.get("ok")),
            "mode": mode,
            "intent": preview.get("intent"),
            "blocked": bool(preview.get("blocked")),
            "answer": preview.get("answer_draft") or "",
            "citations": preview.get("citations") or [],
            "items": preview.get("items") or [],
            "warnings": preview.get("warnings") or [],
            "research_only_disclaimer": preview.get("research_only_disclaimer") or RESEARCH_ONLY_DISCLAIMER,
            "context_digest": preview.get("context_digest") or {},
            "trading": research_only_trading_flags(),
        }

    @classmethod
    def _is_unsafe_answer(cls, answer: str) -> bool:
        lowered = str(answer or "").lower()
        return any(term.lower() in lowered for term in cls._unsafe_answer_terms)

    @staticmethod
    def _merge_warnings(base: Any, extra: Any) -> List[str]:
        merged: List[str] = []
        for group in (base or [], extra or []):
            if isinstance(group, str):
                values = [group]
            else:
                values = list(group) if isinstance(group, list) else []
            for value in values:
                clean = str(value or "").strip()
                if clean and clean not in merged:
                    merged.append(clean)
        return merged
