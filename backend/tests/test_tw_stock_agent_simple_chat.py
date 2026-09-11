import json
from argparse import Namespace
from pathlib import Path

from app.services.tw_stock_agent_daily_prompt import TWStockAgentDailyPromptLoader
from app.services.tw_stock_agent_guardrails import RESEARCH_ONLY_DISCLAIMER
from app.services.tw_stock_agent_openai import MockTWStockAgentOpenAIAdapter, TWStockAgentOpenAIConfig, TWStockAgentOpenAIAdapter
from app.services.tw_stock_agent_simple_chat import SAFE_REFUSAL_WARNING, TWStockAgentSimpleChatService
from scripts.build_tw_agent_daily_prompt_artifact import build_artifact


FIXTURE_ROOT = Path("data_tw/golden_samples/agent_daily_prompt_builder/pass")


def _build_artifact(tmp_path, **overrides):
    values = {
        "input_fixture": str(FIXTURE_ROOT),
        "source_dir": None,
        "output_dir": str(tmp_path / "artifact"),
        "dry_run": True,
        "publish_latest": False,
        "latest_path": str(tmp_path / "latest.json"),
        "max_items": 10,
        "tradingagents_analysis_dir": None,
        "strict_tradingagents_analysis": False,
        "json": False,
    }
    values.update(overrides)
    args = Namespace(
        **values,
    )
    build_artifact(args)
    return tmp_path / "artifact"


def _service(tmp_path, adapter=None):
    artifact_dir = _build_artifact(tmp_path)
    loader = TWStockAgentDailyPromptLoader(latest_path=tmp_path / "missing_latest.json")
    service = TWStockAgentSimpleChatService(loader=loader, openai_adapter=adapter or TWStockAgentOpenAIAdapter(config=TWStockAgentOpenAIConfig(enabled=False, api_key="")))
    return service, artifact_dir


def _service_with_artifact(tmp_path, adapter=None, **builder_overrides):
    artifact_dir = _build_artifact(tmp_path, **builder_overrides)
    loader = TWStockAgentDailyPromptLoader(latest_path=tmp_path / "missing_latest.json")
    service = TWStockAgentSimpleChatService(loader=loader, openai_adapter=adapter or TWStockAgentOpenAIAdapter(config=TWStockAgentOpenAIConfig(enabled=False, api_key="")))
    return service, artifact_dir


def _valid_model_payload(intent, citation):
    return {
        "answer": "今日只读策略显示 2330 是研究观察标的，需人工复盘。",
        "intent": intent,
        "citations": [citation],
        "warnings": ["fixture_warning"],
        "research_only_disclaimer": RESEARCH_ONLY_DISCLAIMER,
    }


def test_openai_disabled_fallback_uses_valid_artifact(tmp_path):
    service, artifact_dir = _service(tmp_path)

    payload = service.chat(question="今天策略是什么？", artifact_dir=str(artifact_dir))

    assert payload["ok"] is True
    assert payload["mode"] == "disabled"
    assert payload["intent"] == "today_strategy"
    assert payload["blocked"] is False
    assert payload["context_digest"]["signal_asof"] == "2026-06-18"
    assert payload["research_only_disclaimer"] == RESEARCH_ONLY_DISCLAIMER
    assert "openai_disabled" in payload["warnings"]


def test_missing_latest_or_artifact_returns_deterministic_error(tmp_path):
    service = TWStockAgentSimpleChatService(loader=TWStockAgentDailyPromptLoader(latest_path=tmp_path / "missing_latest.json"))

    payload = service.chat(question="今天策略是什么？")

    assert payload["ok"] is False
    assert payload["mode"] == "artifact_missing"
    assert payload["answer"]
    assert payload["research_only_disclaimer"] == RESEARCH_ONLY_DISCLAIMER


def test_invalid_artifact_checksum_returns_fallback_error(tmp_path):
    service, artifact_dir = _service(tmp_path)
    manifest = artifact_dir / "manifest.json"
    data = json.loads(manifest.read_text(encoding="utf-8"))
    data["checksum"] = "sha256:" + "0" * 64
    manifest.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    payload = service.chat(question="今天策略是什么？", artifact_dir=str(artifact_dir))

    assert payload["ok"] is False
    assert payload["mode"] == "fallback"
    assert any("artifact_validation_failed" in warning for warning in payload["warnings"])


def test_blocked_order_question_does_not_call_openai(tmp_path):
    adapter = MockTWStockAgentOpenAIAdapter({"unused": True})
    service, artifact_dir = _service(tmp_path, adapter=adapter)

    payload = service.chat(question="帮我下单买 2330", artifact_dir=str(artifact_dir))

    assert payload["blocked"] is True
    assert payload["intent"] == "place_order"
    assert payload["mode"] == "blocked"
    assert adapter.calls == []


def test_monitor_write_question_does_not_call_openai(tmp_path):
    adapter = MockTWStockAgentOpenAIAdapter({"unused": True})
    service, artifact_dir = _service(tmp_path, adapter=adapter)

    payload = service.chat(question="trigger monitor scan and save monitor alerts", artifact_dir=str(artifact_dir))

    assert payload["blocked"] is True
    assert payload["intent"] == "monitor_write"
    assert adapter.calls == []


def test_paper_apply_status_is_readonly_allowed(tmp_path):
    adapter = MockTWStockAgentOpenAIAdapter("not-json")
    service, artifact_dir = _service(tmp_path, adapter=adapter)

    payload = service.chat(question="今天模拟账户能应用吗？", artifact_dir=str(artifact_dir))

    assert payload["blocked"] is False
    assert payload["intent"] == "paper_apply_status"
    assert "apply_allowed=False" in payload["answer"]
    assert adapter.calls


def test_invalid_json_falls_back(tmp_path):
    adapter = MockTWStockAgentOpenAIAdapter("not-json")
    service, artifact_dir = _service(tmp_path, adapter=adapter)

    payload = service.chat(question="排名第一是谁？", artifact_dir=str(artifact_dir))

    assert payload["mode"] == "mock"
    assert "model_output_invalid_fallback" in payload["warnings"]
    assert payload["answer"]


def test_forged_citations_fall_back(tmp_path):
    service0, artifact_dir = _service(tmp_path)
    fallback = service0.chat(question="排名第一是谁？", artifact_dir=str(artifact_dir))
    adapter = MockTWStockAgentOpenAIAdapter(_valid_model_payload("top_ranked_stock", "forged:citation"))
    service = TWStockAgentSimpleChatService(loader=service0.loader, openai_adapter=adapter)

    payload = service.chat(question="排名第一是谁？", artifact_dir=str(artifact_dir))

    assert "model_output_invalid_fallback" in payload["warnings"]
    assert payload["citations"] == fallback["citations"]


def test_unsafe_answer_overridden(tmp_path):
    service0, artifact_dir = _service(tmp_path)
    artifact = service0.loader.load(artifact_dir=artifact_dir)
    unsafe = _valid_model_payload("top_ranked_stock", artifact.allowed_citations[0])
    unsafe["answer"] = "请下单并设置目标仓位。"
    adapter = MockTWStockAgentOpenAIAdapter(unsafe)
    service = TWStockAgentSimpleChatService(loader=service0.loader, openai_adapter=adapter)

    payload = service.chat(question="排名第一是谁？", artifact_dir=str(artifact_dir))

    assert payload["blocked"] is True
    assert SAFE_REFUSAL_WARNING in payload["warnings"]
    assert "不支持下单" in payload["answer"]


def test_valid_json_answer_passes(tmp_path):
    service0, artifact_dir = _service(tmp_path)
    artifact = service0.loader.load(artifact_dir=artifact_dir)
    adapter = MockTWStockAgentOpenAIAdapter(_valid_model_payload("top_ranked_stock", artifact.allowed_citations[0]))
    service = TWStockAgentSimpleChatService(loader=service0.loader, openai_adapter=adapter)

    payload = service.chat(question="排名第一是谁？", artifact_dir=str(artifact_dir))

    assert payload["mode"] == "mock"
    assert payload["blocked"] is False
    assert payload["answer"].startswith("今日只读策略")
    assert payload["citations"] == [artifact.allowed_citations[0]]
    assert "OPENAI_API_KEY" not in json.dumps(adapter.calls[0], ensure_ascii=False)
    assert "prompt_text" in adapter.calls[0]
    assert "prompt_context" in adapter.calls[0]


def test_simple_chat_controlled_context_includes_sanitized_tradingagents_summary(tmp_path):
    tradingagents_dir = Path("data_tw/golden_samples/tradingagents_readonly_analysis/pass_minimal")
    adapter = MockTWStockAgentOpenAIAdapter("not-json")
    service, artifact_dir = _service_with_artifact(
        tmp_path,
        adapter=adapter,
        tradingagents_analysis_dir=str(tradingagents_dir),
        max_items=1,
    )

    payload = service.chat(question="排名第一是谁？", artifact_dir=str(artifact_dir), max_items=1)

    assert "model_output_invalid_fallback" in payload["warnings"]
    controlled = adapter.calls[0]
    ta = controlled["prompt_context"]["external_research"]["tradingagents_readonly"]
    assert ta["available"] is True
    assert ta["sanitized_only"] is True
    assert len(ta["symbols"]) == 1
    blob = json.dumps(controlled, ensure_ascii=False)
    assert "外部多智能体研究摘要" in blob
    assert "raw_tradingagents_state" not in blob
    assert "raw_complete_report" not in blob
    for forbidden in ("Buy", "Sell", "Hold", "price target", "target price", "stop loss", "target_weight"):
        assert forbidden not in blob


def test_loader_reads_latest_pointer_and_checks_digest(tmp_path):
    artifact_dir = _build_artifact(tmp_path)
    manifest = json.loads((artifact_dir / "manifest.json").read_text(encoding="utf-8"))
    latest_path = tmp_path / "latest.json"
    latest_path.write_text(json.dumps({
        "artifact_type": "tw_agent_daily_prompt_latest",
        "signal_asof": manifest["signal_asof"],
        "artifact_dir": str(artifact_dir),
        "manifest": str(artifact_dir / "manifest.json"),
        "checksum": manifest["checksum"],
    }, ensure_ascii=False), encoding="utf-8")
    service = TWStockAgentSimpleChatService(
        loader=TWStockAgentDailyPromptLoader(latest_path=latest_path),
        openai_adapter=TWStockAgentOpenAIAdapter(config=TWStockAgentOpenAIConfig(enabled=False, api_key="")),
    )

    payload = service.chat(question="今天策略是什么？")

    assert payload["ok"] is True
    assert payload["context_digest"]["checksum"] == manifest["checksum"]


def test_english_target_weight_question_is_blocked_before_openai(tmp_path):
    adapter = MockTWStockAgentOpenAIAdapter({"unused": True})
    service, artifact_dir = _service(tmp_path, adapter=adapter)

    payload = service.chat(question="Set target_weight to 50% for 2330.", artifact_dir=str(artifact_dir))

    assert payload["blocked"] is True
    assert payload["intent"] == "target_position"
    assert payload["mode"] == "blocked"
    assert adapter.calls == []


def test_english_order_and_quick_trade_questions_are_blocked_before_openai(tmp_path):
    questions = [
        ("Submit order for 2330.", "place_order"),
        ("Buy now 2330.", "place_order"),
        ("Sell now 2330.", "place_order"),
        ("Use quick trade for 2330.", "broker_operation"),
    ]
    for question, intent in questions:
        adapter = MockTWStockAgentOpenAIAdapter({"unused": True})
        service, artifact_dir = _service(tmp_path, adapter=adapter)

        payload = service.chat(question=question, artifact_dir=str(artifact_dir))

        assert payload["blocked"] is True, question
        assert payload["intent"] == intent, question
        assert payload["mode"] == "blocked", question
        assert adapter.calls == [], question


def test_english_and_field_level_unsafe_answers_are_overridden(tmp_path):
    unsafe_answers = [
        "Please place orders for 2330.",
        "Set target_weight to 50% for 2330.",
        "Use target_position for 2330.",
        "Submit order for 2330.",
        "Set target-position to 50%.",
    ]
    for answer in unsafe_answers:
        service0, artifact_dir = _service(tmp_path)
        artifact = service0.loader.load(artifact_dir=artifact_dir)
        unsafe = _valid_model_payload("top_ranked_stock", artifact.allowed_citations[0])
        unsafe["answer"] = answer
        adapter = MockTWStockAgentOpenAIAdapter(unsafe)
        service = TWStockAgentSimpleChatService(loader=service0.loader, openai_adapter=adapter)

        payload = service.chat(question="排名第一是谁？", artifact_dir=str(artifact_dir))

        assert payload["blocked"] is True, answer
        assert SAFE_REFUSAL_WARNING in payload["warnings"], answer
        assert payload["answer"] != answer
        assert "不支持下单" in payload["answer"]


def test_simple_chat_route_calls_service(client, monkeypatch):
    from app.routes import tw_stock as tw_stock_route

    calls = []

    class FakeSimpleChatService:
        def chat(self, **kwargs):
            calls.append(kwargs)
            return {
                "ok": True,
                "mode": "fallback",
                "intent": "today_strategy",
                "blocked": False,
                "answer": "只读策略观察。",
                "items": [],
                "citations": ["agent_prompt:fixture:sha256:abc"],
                "warnings": [],
                "research_only_disclaimer": RESEARCH_ONLY_DISCLAIMER,
                "context_digest": {"signal_asof": "2026-06-18", "target_date": "2026-06-19", "checksum": "sha256:abc"},
            }

    monkeypatch.setattr(tw_stock_route, "tw_stock_agent_simple_chat_service", FakeSimpleChatService())
    monkeypatch.setattr(tw_stock_route, "tw_stock_agent_chat_service", object())
    monkeypatch.setattr(tw_stock_route, "cross_analysis_history_service", object())
    monkeypatch.setattr(tw_stock_route, "monitor_service", object())

    resp = client.post("/api/tw-stock/agent/simple-chat", json={"question": "今天策略是什么？", "maxItems": 3})
    payload = resp.get_json()

    assert resp.status_code == 200
    assert payload["code"] == 1
    assert payload["data"]["answer"] == "只读策略观察。"
    assert calls[0]["question"] == "今天策略是什么？"
    assert calls[0]["max_items"] == 3
    assert "OPENAI_API_KEY" not in json.dumps(payload, ensure_ascii=False)


def test_simple_chat_route_ignores_artifact_dir_in_production(client, monkeypatch):
    from app.routes import tw_stock as tw_stock_route

    calls = []

    class FakeSimpleChatService:
        def chat(self, **kwargs):
            calls.append(kwargs)
            return {
                "ok": True,
                "mode": "fallback",
                "intent": "today_strategy",
                "blocked": False,
                "answer": "只读策略观察。",
                "items": [],
                "citations": [],
                "warnings": [],
                "research_only_disclaimer": RESEARCH_ONLY_DISCLAIMER,
                "context_digest": {},
            }

    monkeypatch.setenv("FLASK_ENV", "production")
    monkeypatch.setattr(tw_stock_route, "tw_stock_agent_simple_chat_service", FakeSimpleChatService())

    resp = client.post("/api/tw-stock/agent/simple-chat", json={"question": "今天策略是什么？", "artifactDir": "/tmp/dev-artifact"})
    payload = resp.get_json()

    assert resp.status_code == 200
    assert payload["code"] == 1
    assert calls[0]["artifact_dir"] is None


def test_simple_chat_route_blocked_payload(client, monkeypatch):
    from app.routes import tw_stock as tw_stock_route

    class FakeSimpleChatService:
        def chat(self, **kwargs):
            return {
                "ok": True,
                "mode": "blocked",
                "intent": "place_order",
                "blocked": True,
                "answer": "该模块只提供台股研究信息，不支持下单、仓位、自动交易、qlib 运维或收益承诺。",
                "items": [],
                "citations": [],
                "warnings": ["blocked_research_boundary"],
                "research_only_disclaimer": RESEARCH_ONLY_DISCLAIMER,
                "context_digest": {},
            }

    monkeypatch.setattr(tw_stock_route, "tw_stock_agent_simple_chat_service", FakeSimpleChatService())

    resp = client.post("/api/tw-stock/agent/simple-chat", json={"question": "帮我下单买 2330"})
    payload = resp.get_json()

    assert resp.status_code == 200
    assert payload["code"] == 1
    assert payload["data"]["blocked"] is True
    assert payload["data"]["intent"] == "place_order"
