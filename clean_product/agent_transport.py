"""One backend JSON request; no tools, credentials in responses, or retries."""
from __future__ import annotations

import json
from urllib.parse import urlsplit

import requests


class OpenAIAdapter:
    def __init__(self, *, api_key: str, model: str, base_url: str = "https://api.openai.com/v1", timeout: int = 20, post=None):
        parsed = urlsplit(base_url)
        if (parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password
                or parsed.query or parsed.fragment or not api_key or not model or not 1 <= timeout <= 60):
            raise ValueError("AGENT_REMOTE_CONFIGURATION_INVALID")
        self.key, self.model, self.url = api_key, model, base_url.rstrip('/') + '/chat/completions'
        self.timeout, self.post = timeout, post or requests.post

    @classmethod
    def from_config(cls, settings):
        # Called only by an explicitly enabled backend; tests inject a transport.
        import os
        return cls(api_key=os.getenv('OPENAI_API_KEY', ''), model=settings.get('model', ''),
                   base_url=settings.get('base_url', 'https://api.openai.com/v1'),
                   timeout=settings.get('timeout_seconds', 20))

    def complete(self, *, question: str, context: dict, citation: str) -> dict:
        body = {'model': self.model, 'store': False, 'response_format': {'type': 'json_object'},
                'messages': [
                    {'role': 'system', 'content': '只解释给定的只读台股研究证据。不提供交易行动、仓位、收益承诺，不调用工具。分数仅为相对排序。证据不足必须明确说明。只输出 JSON，字段为 answer 字符串、citations 字符串数组、warnings 字符串数组；引用必须来自给定 citation。'},
                    {'role': 'user', 'content': json.dumps({'question': question, 'context': context, 'citation': citation}, ensure_ascii=False)}]}
        try:
            response = self.post(self.url, headers={'Authorization': 'Bearer ' + self.key},
                                 json=body, timeout=self.timeout, allow_redirects=False)
            if response.status_code != 200:
                raise ValueError('remote response rejected')
            result = response.json()['choices'][0]
            if result.get('finish_reason') != 'stop' or result['message'].get('tool_calls'):
                raise ValueError('incomplete or tool-bearing response')
            content = result['message']['content']
            if not isinstance(content, str) or len(content) > 20000:
                raise ValueError('response too large')
            return json.loads(content)
        except Exception:
            # Neither HTTP bodies nor exception strings are safe to return.
            raise ValueError('AGENT_REMOTE_UNAVAILABLE') from None
