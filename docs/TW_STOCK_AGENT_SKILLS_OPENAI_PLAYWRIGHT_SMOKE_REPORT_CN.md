# 台股 Agent Skills / OpenAI / Playwright 真实接口补充验证报告

生成时间：2026-06-04

## 1. 结论

已完成真实 OpenAI-compatible 配置与全流程验证。

- 本地后端配置已写入 `backend/.env`，该文件被 `.gitignore` 忽略，不会提交到 GitHub。
- 后端真实 OpenAI-compatible smoke 通过，非阻断问题返回 `mode=openai`。
- 后端 Agent 返回中包含 `invoked_skills`，可以证明 Web Agent 的后端 skill registry 已选择并传递对应 skills 上下文。
- Playwright 网络级全流程通过：浏览器进入真实前端页面，触发 `/api/tw-stock/agent/chat`，请求转发到启用真实 OpenAI 的临时后端，后端返回 `mode=openai` 与 skills 信息。
- 浏览器没有直连 OpenAI-compatible endpoint，没有泄露 API key，没有触发 broker、quick-trade、order、monitor 写入、qlib ops 等危险请求。

## 2. 本地配置

配置位置：

```text
backend/.env
```

配置内容类型：

```text
ENABLE_TW_STOCK_AGENT_OPENAI=true
OPENAI_BASE_URL=https://chat.pku.edu.cn/v1
TW_STOCK_AGENT_OPENAI_BASE_URL=https://chat.pku.edu.cn/v1
OPENAI_API_KEY=<backend-only secret>
TW_STOCK_AGENT_OPENAI_MODEL=gpt-4.1-mini
TW_STOCK_AGENT_OPENAI_TIMEOUT_SECONDS=20
```

安全确认：

```text
backend/.env 被 backend/.gitignore 忽略
backend/.env 权限为 600
```

## 3. 后端真实 OpenAI Smoke

验证场景：

```text
research: 解释今天 top30 的主要观察点。
freshness: 为什么 latest_asof 还是昨天，Yahoo 和 FinMind 后面会自动重试吗？
blocked_order: 帮我下单买入 2330
e2e_handoff: 用 Playwright 跑一个全流程验收测试
```

结果摘要：

```json
{
  "research": {
    "mode": "openai",
    "skills": [
      ["tw-stock-safety-boundary-review", "applied", "guardrail_policy"],
      ["tw-stock-research-context-analyst", "invoked", "readonly_context"]
    ]
  },
  "freshness": {
    "mode": "openai",
    "skills": [
      ["tw-stock-safety-boundary-review", "applied", "guardrail_policy"],
      ["tw-stock-data-freshness-diagnosis", "invoked", "readonly_context"]
    ]
  },
  "blocked_order": {
    "mode": "disabled",
    "blocked": true,
    "skills": [
      ["tw-stock-safety-boundary-review", "applied", "guardrail_policy"]
    ]
  },
  "e2e_handoff": {
    "mode": "openai",
    "skills": [
      ["tw-stock-safety-boundary-review", "applied", "guardrail_policy"],
      ["tw-stock-research-context-analyst", "invoked", "readonly_context"],
      ["tw-stock-readonly-e2e-acceptance", "not_invoked_from_web_agent", "operator_handoff"]
    ]
  }
}
```

结论：后端 Agent 会选择并传递对应 skills 上下文；阻断类交易问题在 OpenAI 调用前被 guardrail 拦截。

## 4. Playwright 网络级全流程

临时后端：

```text
http://127.0.0.1:5094
```

前端：

```text
http://127.0.0.1:8000/#/tw-stock-monitor
```

结果摘要：

```json
{
  "ok": true,
  "forwarded": [
    "GET http://127.0.0.1:5094/api/tw-stock/agent/context?... 200",
    "GET http://127.0.0.1:5094/api/tw-stock/agent/context?... 200",
    "POST http://127.0.0.1:5094/api/tw-stock/agent/chat 200"
  ],
  "chat_mode": "openai",
  "blocked": false,
  "skills": [
    ["tw-stock-safety-boundary-review", "applied", "guardrail_policy"],
    ["tw-stock-research-context-analyst", "invoked", "readonly_context"]
  ],
  "directOpenAIRequests": [],
  "dangerousWrites": [],
  "pageErrors": [],
  "keyLeaked": false
}
```

说明：浏览器只调用后端 `/api/tw-stock/agent/*`，真实 OpenAI-compatible 调用只发生在后端。

## 5. 边界说明

- Web 后端不会执行 `~/.agents/skills/*` 中的本地脚本。
- Web 后端通过 `TWStockAgentSkillRegistry` 读取 skill description，并把 selected skills、skill context 与 invocation policy 放入受控 OpenAI prompt。
- `tw-stock-readonly-e2e-acceptance` 在 Web Agent 中是 operator handoff，不会从前端聊天里运行 Playwright。
- Codex/Agent 本地 skills 的自动触发仍取决于 Codex 会话是否重新加载 skills 元数据。

## 6. 收尾建议

可以收尾。

如果后续要提交代码，只提交后端 skill registry、Agent chat 集成、前端 skills 展示、测试与不含密钥的文档。不要提交 `backend/.env`。
