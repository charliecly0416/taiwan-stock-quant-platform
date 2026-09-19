---
title: Agent Daily Prompt Route
category: concepts
tags: [agent, prompt, simple-chat, readonly]
aliases: [DailyAgentPromptArtifact 路线]
relationships:
  - target: "[[concepts/readonly-safety-boundary]]"
    type: uses
  - target: "[[concepts/current-default-model-and-strategy]]"
    type: related_to
  - target: "[[skills/safety-boundary-review-workflow]]"
    type: related_to
sources: ['/home/chuliyang/taiwan-stock-quant-platform/docs/tw_modular_contracts/TW_AGENT_DAILY_PROMPT_ARTIFACT_CONTRACT_CN.md', '/home/chuliyang/taiwan-stock-quant-platform/.agents/skills/tw-stock-agent-daily-prompt-maintenance/SKILL.md', '/home/chuliyang/taiwan-stock-quant-platform/docs/tw_agent_daily_prompt_rebuild/PHASE0_TO_PHASE6_FINAL_SUMMARY_CN.md', '/home/chuliyang/taiwan-stock-quant-platform/docs/tw_agent_daily_prompt_rebuild/PHASE6_FINAL_ACCEPTANCE_REPORT_CN.md', '/home/chuliyang/taiwan-stock-quant-platform/docs/tw_agent_daily_prompt_rebuild/PHASE6_FINAL_ACCEPTANCE_REVIEW_CN.md', '/home/chuliyang/taiwan-stock-quant-platform/docs/tw_agent_daily_prompt_rebuild/POST_ACCEPTANCE_TODO_VALIDATOR_ENGLISH_ORDER_FORBIDDEN_TERMS_REVIEW_CN.md']
summary: Agent 当前路线是 DailyAgentPromptArtifact -> backend simple-chat -> readonly explanation，真实 OpenAI 与 publish latest 仍需单独 gate。
provenance:
  extracted: 0.9
  inferred: 0.1
  ambiguous: 0.0
base_confidence: 0.9
lifecycle: draft
lifecycle_changed: 2026-06-20
tier: core
created: 2026-06-20T00:00:00Z
updated: 2026-06-20T17:00:00Z
---

# Agent Daily Prompt Route

Agent 产品路线固定为：DailyAgentPromptArtifact -> backend simple-chat -> `/api/tw-stock/agent/simple-chat` -> frontend readonly explanation。W2 final sources 确认 Phase 0-6 已接受该路线，Playwright 网络审计补验通过，无阻塞验收缺口。

## Current Accepted Route

```text
DailyAgentPromptArtifact
  -> TWStockAgentSimpleChatService
  -> /api/tw-stock/agent/simple-chat
  -> 前端策略解释助手只读展示
  -> disabled/mock OpenAI 安全路径
  -> 日更默认关闭/dry-run 的 Agent prompt build gate
```

`POST /api/tw-stock/agent/simple-chat` 是唯一允许的前端 Agent 解释路径。前端只发送 `question`、`symbol`、`maxItems`，不得发送 OpenAI key、endpoint、model 或 tool/action 权限。

## Artifact Contract

DailyAgentPromptArtifact 的生产结构包括：

```text
data_tw/artifacts/agent_daily_prompt/{signal_asof}/manifest.json
data_tw/artifacts/agent_daily_prompt/{signal_asof}/prompt_context.json
data_tw/artifacts/agent_daily_prompt/{signal_asof}/prompt_text.md
data_tw/artifacts/agent_daily_prompt/latest.json
```

`latest.json` 只是 Agent prompt latest pointer，不是 provider accepted latest，也不是 qlib accepted latest。

## Builder / Validator / Prompt Boundary

Builder 默认 dry-run；日更接入 gate 默认关闭，启用后也默认 dry-run、默认不 publish Agent prompt latest。Validator 必须拦截 broker/order/quick-trade、monitor config/scan/alerts、provider publish、accepted latest、target position/target weight，以及英文 actionable order 单数/短语。

Prompt context 必须包含 readonly safety flags、date context、model context、answer policy，并可包含 rankings、strategy、paper portfolio、replay summary 和 freshness 的只读摘要。checksum/citation 必须可验证；forged citations、invalid JSON、unsafe answer 要 fallback 或 blocked。

## Forbidden Route Changes

- 不绕过 DailyAgentPromptArtifact 向 OpenAI 发送动态服务 payload。
- 不重引入 complex tool Agent action path。
- 不从前端调用 OpenAI，不暴露 key/base URL。
- 不回答买卖动作、目标仓位、目标权重、收益承诺或胜率承诺。
- 不触发 monitor/provider/latest/broker/order。

## Residual Conditions

真实 OpenAI-compatible smoke 如执行，只能通过后端环境变量注入 key，报告不得记录 key、Authorization header、Bearer token、完整敏感 payload 或截图。生产启用 Agent prompt publish latest 前，必须先 dry-run 检查 source artifacts、asof、checksum 和 warnings。

## W3 Code Evidence

- Backend entry: `backend/app/routes/tw_stock.py` 中的 `POST /agent/simple-chat` 调用 `simple_chat_tw_stock_agent_answer`。
- Service layer: `backend/app/services/tw_stock_agent_simple_chat.py` 读取经过 `TWStockAgentDailyPromptLoader` 校验的 DailyAgentPromptArtifact，并在 OpenAI 前阻断 forbidden intent。
- Loader: `backend/app/services/tw_stock_agent_daily_prompt.py` 使用 `data_tw/artifacts/agent_daily_prompt/latest.json`，校验 latest pointer、checksum、signal_asof、readonly flags 和 allowed citations。
- OpenAI: `backend/app/services/tw_stock_agent_openai.py` 是 backend-only adapter；缺 key 时返回 disabled/mock 状态，前端不得直连。
- Frontend: `frontend/src/api/tw-stock.js` 的 `simpleChatTwStockAgent` 只调用 `/agent/simple-chat`；`frontend/src/views/tw-stock-monitor/index.vue` 的 Agent panel 只提交 question/symbol/maxItems。
- Builder/validator: `scripts/build_tw_agent_daily_prompt_artifact.py` 和 `scripts/validate_tw_agent_daily_prompt_artifact.py` 是 DailyAgentPromptArtifact 的构建/校验入口，W3 只读映射，未运行。


## W4 Historical Boundary

Dynamic `/agent/context`, legacy `/agent/chat`, complex tool Agent routes, manual review explanation modules and real OpenAI smoke records are historical or boundary-only. [[references/superseded-routes-agent-and-tools]] records the lesson; it does not expand the current Agent route beyond DailyAgentPromptArtifact -> backend simple-chat.

## Sources

- [[references/agent-daily-prompt-rebuild-final|Agent Daily Prompt Rebuild Final]]
- [[references/code-map-backend-readonly-routes|Backend Readonly Routes Code Map]]
- [[references/code-map-frontend-workbench|Frontend Workbench Code Map]]
- [[references/code-map-scripts-and-tests|Scripts And Tests Code Map]]
- `docs/tw_modular_contracts/TW_AGENT_DAILY_PROMPT_ARTIFACT_CONTRACT_CN.md`
- `.agents/skills/tw-stock-agent-daily-prompt-maintenance/SKILL.md`
