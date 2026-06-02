"""Backend-only OpenAI adapter for the TWStock research agent."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


DEFAULT_MODEL = "gpt-4.1-mini"
DEFAULT_TIMEOUT_SECONDS = 20
DEFAULT_BASE_URL = "https://api.openai.com/v1"


@dataclass(frozen=True)
class TWStockAgentOpenAIConfig:
    enabled: bool
    api_key: str
    model: str = DEFAULT_MODEL
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS
    base_url: str = DEFAULT_BASE_URL

    @classmethod
    def from_env(cls) -> "TWStockAgentOpenAIConfig":
        enabled = str(os.getenv("ENABLE_TW_STOCK_AGENT_OPENAI") or "false").strip().lower() in {"1", "true", "yes", "on"}
        timeout_raw = os.getenv("TW_STOCK_AGENT_OPENAI_TIMEOUT_SECONDS") or str(DEFAULT_TIMEOUT_SECONDS)
        try:
            timeout = max(1, min(int(timeout_raw), 60))
        except Exception:
            timeout = DEFAULT_TIMEOUT_SECONDS
        return cls(
            enabled=enabled,
            api_key=(os.getenv("OPENAI_API_KEY") or "").strip(),
            model=(os.getenv("TW_STOCK_AGENT_OPENAI_MODEL") or DEFAULT_MODEL).strip() or DEFAULT_MODEL,
            timeout_seconds=timeout,
            base_url=(os.getenv("TW_STOCK_AGENT_OPENAI_BASE_URL") or os.getenv("OPENAI_BASE_URL") or DEFAULT_BASE_URL).strip().rstrip("/") or DEFAULT_BASE_URL,
        )


class TWStockAgentOpenAIAdapter:
    """Call OpenAI with a controlled JSON-only research prompt when enabled."""

    def __init__(self, *, config: Optional[TWStockAgentOpenAIConfig] = None, http_post: Optional[Any] = None) -> None:
        self.config = config or TWStockAgentOpenAIConfig.from_env()
        self._http_post = http_post

    def status(self) -> Dict[str, Any]:
        if not self.config.enabled:
            return {"enabled": False, "mode": "disabled", "reason": "openai_disabled", "model": self.config.model}
        if not self.config.api_key:
            return {"enabled": False, "mode": "disabled", "reason": "missing_openai_api_key", "model": self.config.model}
        return {"enabled": True, "mode": "openai", "reason": "enabled", "model": self.config.model}

    def complete(self, *, controlled_context: Dict[str, Any]) -> Dict[str, Any]:
        status = self.status()
        if not status["enabled"]:
            return {"ok": False, "mode": "disabled", "status": status["reason"], "message": status["reason"]}

        messages = [
            {"role": "system", "content": self._system_prompt()},
            {"role": "user", "content": json.dumps(controlled_context, ensure_ascii=False, separators=(",", ":"))},
        ]
        body = {
            "model": self.config.model,
            "messages": messages,
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
        }
        try:
            response = self._post(
                f"{self.config.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.config.api_key}",
                    "Content-Type": "application/json",
                },
                json=body,
                timeout=self.config.timeout_seconds,
            )
            if getattr(response, "status_code", 200) >= 400:
                return {"ok": False, "mode": "openai", "status": "api_error", "message": str(getattr(response, "text", ""))}
            payload = response.json()
            content = (((payload.get("choices") or [{}])[0].get("message") or {}).get("content") or "").strip()
            return {"ok": True, "mode": "openai", "content": content, "model": self.config.model}
        except Exception as exc:
            return {"ok": False, "mode": "openai", "status": "api_error", "message": str(exc)}

    def _post(self, url: str, *, headers: Dict[str, str], json: Dict[str, Any], timeout: int) -> Any:
        if self._http_post is not None:
            return self._http_post(url, headers=headers, json=json, timeout=timeout)
        import requests

        return requests.post(url, headers=headers, json=json, timeout=timeout)

    @staticmethod
    def _system_prompt() -> str:
        return (
            "你是台股 research-only 助手。只能解释给定上下文，不能使用外部工具。"
            "不能下单、不能建议仓位、不能承诺收益，不能操作 qlib refresh/publish/pipeline/retrain/tune。"
            "qlib score 是横截面排序分数，不是收益率、胜率、涨幅或买入概率。"
            "使用“建议关注/建议回避/人工复盘/数据复核”，不要输出“必须买入/必须卖出”。"
            "回答必须引用输入 citations。只输出 JSON："
            '{"answer":"string","citations":["string"],"warnings":["string"],"research_only_disclaimer":"string","intent":"string"}'
        )


class MockTWStockAgentOpenAIAdapter:
    """Test helper adapter that never performs network access."""

    def __init__(self, content: str | Dict[str, Any], *, ok: bool = True, mode: str = "mock", status: str = "ok") -> None:
        self.content = content
        self.ok = ok
        self.mode = mode
        self.status_value = status
        self.calls: List[Dict[str, Any]] = []

    def status(self) -> Dict[str, Any]:
        return {"enabled": True, "mode": self.mode, "reason": self.status_value, "model": "mock"}

    def complete(self, *, controlled_context: Dict[str, Any]) -> Dict[str, Any]:
        self.calls.append(controlled_context)
        if not self.ok:
            return {"ok": False, "mode": self.mode, "status": self.status_value, "message": self.status_value}
        content = json.dumps(self.content, ensure_ascii=False) if isinstance(self.content, dict) else str(self.content)
        return {"ok": True, "mode": self.mode, "content": content, "model": "mock"}
