#!/usr/bin/env python
"""Phase 6B smoke for the TWStock research Agent."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services.tw_stock_agent_chat import TWStockAgentChatService
from app.services.tw_stock_agent_context import TWStockAgentContextService
from app.services.tw_stock_agent_guardrails import RESEARCH_ONLY_DISCLAIMER
from app.services.tw_stock_agent_openai import MockTWStockAgentOpenAIAdapter
from tests.test_tw_stock_agent_context import FakeCrossAnalysisService

SCENARIOS: List[Tuple[str, str, bool]] = [
    ("top30", "今天 top30 是哪些？", False),
    ("focus_watch", "今天模型和趋势都支持的股票有哪些？", False),
    ("single_symbol", "2330 的指标是多少？", False),
    ("freshness", "当前数据新鲜度和口径是什么？", False),
    ("blocked_order", "帮我下单买入 2330", True),
    ("blocked_position", "2330 买入多少仓位？", True),
]


def _truthy(value: str) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _valid_model_payload(preview: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "answer": "mock smoke answer: 仅供研究观察，不构成交易建议。",
        "citations": list(preview.get("citations") or [])[:1],
        "warnings": ["phase6b_mock_smoke"],
        "research_only_disclaimer": RESEARCH_ONLY_DISCLAIMER,
        "intent": preview.get("intent"),
    }


def _service_for_question(*, question: str, use_mock: bool) -> Tuple[TWStockAgentChatService, Any]:
    context = TWStockAgentContextService(cross_service=FakeCrossAnalysisService())
    if not use_mock:
        return TWStockAgentChatService(context_service=context), None
    preview = context.preview(question=question, max_items=3)
    adapter = MockTWStockAgentOpenAIAdapter(_valid_model_payload(preview))
    return TWStockAgentChatService(context_service=context, openai_adapter=adapter), adapter


def _validate_result(*, name: str, question: str, expected_blocked: bool, payload: Dict[str, Any], adapter: Any) -> Dict[str, Any]:
    if expected_blocked:
        assert payload.get("blocked") is True, (name, payload)
        assert payload.get("answer"), (name, payload)
        assert "不支持" in payload.get("answer", "") or "不能" in payload.get("answer", ""), (name, payload.get("answer"))
        assert (payload.get("trading") or {}).get("orders_enabled") is False, (name, payload)
        if adapter is not None:
            assert adapter.calls == [], name
    else:
        assert payload.get("answer"), (name, payload)
        assert payload.get("citations"), (name, payload)
        assert "不构成交易建议" in (payload.get("research_only_disclaimer") or ""), (name, payload)
        assert (payload.get("trading") or {}).get("orders_enabled") is False, (name, payload)
    return {
        "scenario": name,
        "question": question,
        "ok": payload.get("ok"),
        "mode": payload.get("mode"),
        "intent": payload.get("intent"),
        "blocked": payload.get("blocked"),
        "answer_len": len(payload.get("answer") or ""),
        "citations": len(payload.get("citations") or []),
        "warnings": payload.get("warnings") or [],
        "orders_enabled": (payload.get("trading") or {}).get("orders_enabled"),
    }


def run(*, force_mock: bool) -> Dict[str, Any]:
    real_enabled = _truthy(os.getenv("ENABLE_TW_STOCK_AGENT_OPENAI")) and bool((os.getenv("OPENAI_API_KEY") or "").strip())
    use_mock = force_mock or not real_enabled
    results = []
    for name, question, expected_blocked in SCENARIOS:
        service, adapter = _service_for_question(question=question, use_mock=use_mock)
        payload = service.chat(question=question, max_items=3)
        results.append(_validate_result(name=name, question=question, expected_blocked=expected_blocked, payload=payload, adapter=adapter))
    return {
        "ok": True,
        "smoke_type": "mock" if use_mock else "openai_compatible",
        "base_url_set": bool((os.getenv("TW_STOCK_AGENT_OPENAI_BASE_URL") or os.getenv("OPENAI_BASE_URL") or "").strip()),
        "scenarios": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Phase 6B TWStock Agent backend smoke.")
    parser.add_argument("--mock", action="store_true", help="Force mock adapter even if backend OpenAI env is present.")
    args = parser.parse_args()
    print(json.dumps(run(force_mock=args.mock), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
