"""Tests for guarded TWStock research Agent chat."""
from __future__ import annotations

from pathlib import Path

from app.services.tw_stock_agent_chat import SAFE_REFUSAL_WARNING, TWStockAgentChatService
from app.services.tw_stock_agent_context import TWStockAgentContextService
from app.services.tw_stock_agent_guardrails import RESEARCH_ONLY_DISCLAIMER
from app.services.tw_stock_agent_openai import MockTWStockAgentOpenAIAdapter, TWStockAgentOpenAIAdapter, TWStockAgentOpenAIConfig
from tests.test_tw_stock_agent_context import FakeCrossAnalysisService


def _context_service() -> TWStockAgentContextService:
    return TWStockAgentContextService(cross_service=FakeCrossAnalysisService())


def _valid_model_payload(preview):
    return {
        "answer": "模型和趋势均支持的项目建议关注，并保留人工复盘。",
        "citations": preview["citations"][:1],
        "warnings": ["fixture_warning"],
        "research_only_disclaimer": RESEARCH_ONLY_DISCLAIMER,
        "intent": preview["intent"],
    }


def test_chat_openai_disabled_returns_deterministic_fallback(monkeypatch):
    monkeypatch.setenv("ENABLE_TW_STOCK_AGENT_OPENAI", "false")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    service = TWStockAgentChatService(context_service=_context_service())

    payload = service.chat(question="今天 top30", max_items=2)

    assert payload["ok"] is True
    assert payload["mode"] == "disabled"
    assert payload["intent"] == "today_top30"
    assert payload["blocked"] is False
    assert "openai_disabled" in payload["warnings"]
    assert payload["research_only_disclaimer"] == RESEARCH_ONLY_DISCLAIMER
    assert payload["trading"]["orders_enabled"] is False


def test_chat_missing_openai_key_does_not_crash(monkeypatch):
    monkeypatch.setenv("ENABLE_TW_STOCK_AGENT_OPENAI", "true")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    service = TWStockAgentChatService(context_service=_context_service())

    payload = service.chat(question="列出重点观察")

    assert payload["mode"] == "disabled"
    assert "missing_openai_api_key" in payload["warnings"]
    assert payload["answer"]


def test_blocked_questions_do_not_call_openai():
    adapter = MockTWStockAgentOpenAIAdapter({"unused": True})
    service = TWStockAgentChatService(context_service=_context_service(), openai_adapter=adapter)

    order = service.chat(question="帮我下单买 2330")
    ops = service.chat(question="刷新 qlib 并 retrain 模型")

    assert adapter.calls == []
    assert order["blocked"] is True
    assert order["intent"] == "place_order"
    assert order["mode"] == "disabled"
    assert ops["blocked"] is True
    assert ops["intent"] == "qlib_retrain_or_tune"


def test_mock_openai_valid_json_response_passes_schema():
    context = _context_service()
    preview = context.preview(question="今天 top30", max_items=2)
    adapter = MockTWStockAgentOpenAIAdapter(_valid_model_payload(preview))
    service = TWStockAgentChatService(context_service=context, openai_adapter=adapter)

    payload = service.chat(question="今天 top30", max_items=2)

    assert payload["mode"] == "mock"
    assert payload["blocked"] is False
    assert payload["answer"] == "模型和趋势均支持的项目建议关注，并保留人工复盘。"
    assert payload["citations"] == preview["citations"][:1]
    assert payload["items"]
    assert "fixture_warning" in payload["warnings"]
    assert adapter.calls[0]["items"]
    assert "blocked_operations" in adapter.calls[0]
    assert "OPENAI_API_KEY" not in str(adapter.calls[0])


def test_mock_openai_invalid_json_falls_back_to_preview():
    adapter = MockTWStockAgentOpenAIAdapter("not-json")
    service = TWStockAgentChatService(context_service=_context_service(), openai_adapter=adapter)

    payload = service.chat(question="今天 top30")

    assert payload["mode"] == "mock"
    assert payload["blocked"] is False
    assert "model_output_invalid_fallback_to_preview" in payload["warnings"]
    assert payload["answer"].startswith("today_top30 预览")


def test_mock_openai_missing_or_forged_citations_falls_back():
    context = _context_service()
    preview = context.preview(question="今天 top30")
    bad = _valid_model_payload(preview)
    bad["citations"] = ["qlib:accepted_latest:forged:2099-01-01"]
    service = TWStockAgentChatService(context_service=context, openai_adapter=MockTWStockAgentOpenAIAdapter(bad))

    payload = service.chat(question="今天 top30")

    assert "model_output_invalid_fallback_to_preview" in payload["warnings"]
    assert payload["citations"] == preview["citations"]


def test_mock_openai_unsafe_trading_answer_is_overridden():
    context = _context_service()
    preview = context.preview(question="今天 top30")
    unsafe = _valid_model_payload(preview)
    unsafe["answer"] = "必须买入 2330，并设置目标仓位。"
    service = TWStockAgentChatService(context_service=context, openai_adapter=MockTWStockAgentOpenAIAdapter(unsafe))

    payload = service.chat(question="今天 top30")

    assert payload["blocked"] is True
    assert payload["items"] == []
    assert SAFE_REFUSAL_WARNING in payload["warnings"]
    assert "不支持下单" in payload["answer"]
    assert payload["trading"]["orders_enabled"] is False


def test_openai_adapter_disabled_and_missing_key_status(monkeypatch):
    monkeypatch.setenv("ENABLE_TW_STOCK_AGENT_OPENAI", "false")
    monkeypatch.setenv("OPENAI_API_KEY", "backend-only")
    assert TWStockAgentOpenAIAdapter().status()["reason"] == "openai_disabled"

    monkeypatch.setenv("ENABLE_TW_STOCK_AGENT_OPENAI", "true")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert TWStockAgentOpenAIAdapter().status()["reason"] == "missing_openai_api_key"


def test_openai_adapter_mock_http_validates_backend_only_key(monkeypatch):
    calls = []

    class Response:
        status_code = 200

        @staticmethod
        def json():
            return {"choices": [{"message": {"content": "{\"answer\":\"ok\",\"citations\":[],\"warnings\":[],\"research_only_disclaimer\":\"仅供研究观察，不构成交易建议\",\"intent\":\"today_top30\"}"}}]}

    def fake_post(url, *, headers, json, timeout):
        calls.append({"url": url, "headers": headers, "json": json, "timeout": timeout})
        return Response()

    adapter = TWStockAgentOpenAIAdapter(
        config=TWStockAgentOpenAIConfig(enabled=True, api_key="secret-key", model="fixture-model", timeout_seconds=3, base_url="https://chat.pku.edu.cn/v1"),
        http_post=fake_post,
    )
    result = adapter.complete(controlled_context={"intent": "today_top30", "citations": [], "items": []})

    assert result["ok"] is True
    assert calls[0]["url"] == "https://chat.pku.edu.cn/v1/chat/completions"
    assert calls[0]["headers"]["Authorization"] == "Bearer secret-key"
    assert "secret-key" not in str(calls[0]["json"])
    assert calls[0]["timeout"] == 3


def test_agent_chat_api_contract(client, monkeypatch):
    from app.routes import tw_stock as tw_stock_route

    context = _context_service()
    preview = context.preview(question="今天 top30")
    service = TWStockAgentChatService(
        context_service=context,
        openai_adapter=MockTWStockAgentOpenAIAdapter(_valid_model_payload(preview)),
    )
    monkeypatch.setattr(tw_stock_route, "tw_stock_agent_chat_service", service)

    resp = client.post("/api/tw-stock/agent/chat", json={"question": "今天 top30", "maxItems": 2})
    payload = resp.get_json()

    assert resp.status_code == 200
    assert payload["code"] == 1
    data = payload["data"]
    assert data["mode"] == "mock"
    assert data["intent"] == "today_top30"
    assert data["research_only_disclaimer"] == RESEARCH_ONLY_DISCLAIMER
    assert data["trading"]["orders_enabled"] is False


def test_agent_step2_sources_do_not_import_forbidden_tooling():
    root = Path(__file__).resolve().parents[1] / "app" / "services"
    joined = "\n".join([
        (root / "tw_stock_agent_openai.py").read_text(),
        (root / "tw_stock_agent_chat.py").read_text(),
    ])

    forbidden = [
        "tw_stock_qlib_option_c_ops",
        "tw_stock_qlib_option_c_normal_publish",
        "tw_stock_qlib_option_c_eod_pipeline",
        "trading_executor",
        "quick_trade",
        "backtest",
        "ibkr_trading",
        "live_trading",
    ]
    for token in forbidden:
        assert token not in joined
