---
title: Superseded Routes: Agent And Tools
category: references
tags: [historical, superseded, agent, tools]
relationships:
  - target: "[[concepts/agent-daily-prompt-route]]"
    type: related_to
  - target: "[[synthesis/historical-lessons]]"
    type: related_to
sources: [/home/chuliyang/taiwan-stock-quant-platform/docs/tw_agent_daily_prompt_rebuild/PHASE0_EXECUTION_REPORT_CN.md, /home/chuliyang/taiwan-stock-quant-platform/docs/tw_agent_daily_prompt_rebuild/PHASE0_TO_PHASE6_FINAL_SUMMARY_CN.md, /home/chuliyang/taiwan-stock-quant-platform/docs/tw_agent_daily_prompt_rebuild/PHASE6_FINAL_ACCEPTANCE_REVIEW_CN.md, /home/chuliyang/taiwan-stock-quant-platform/docs/tw_modular_daily_update_productization/PHASEUI2_STRATEGY_WORKBENCH_AGENT_UX_FINAL_ROUTE_REVIEW_CN.md]
summary: Historical Agent/tool routes were replaced by DailyAgentPromptArtifact plus backend simple-chat; old dynamic preview/tool paths are not current mainline.
provenance:
  extracted: 0.86
  inferred: 0.14
  ambiguous: 0.0
base_confidence: 0.86
lifecycle: archived
lifecycle_changed: 2026-06-20
tier: supporting
created: 2026-06-20T17:00:00Z
updated: 2026-06-20T17:00:00Z
---

# Superseded Routes: Agent And Tools

历史路线，不代表当前 Agent 主线。当前 Agent 路线是 [[concepts/agent-daily-prompt-route|DailyAgentPromptArtifact -> backend simple-chat -> frontend readonly explanation]]。

## Superseded Agent Routes

| Historical route | Classification | Why replaced | Current replacement |
|---|---|---|---|
| dynamic `/agent/context` + cross-analysis preview | superseded input path | 动态 preview 不是已验证 DailyAgentPromptArtifact，source/citation/checksum 难以固定 | DailyAgentPromptArtifact loader and validator |
| legacy `/agent/chat` as frontend main path | superseded | 前端主路径已切到 `/agent/simple-chat`，只传 question/symbol/maxItems | `POST /api/tw-stock/agent/simple-chat` |
| complex Agent/tool or skill-registry expansion | boundary-only / superseded | 容易引入 action/tool/function calling 误解，不符合 readonly research route | deterministic simple-chat with blocked-before-OpenAI guardrails |
| manual review explanation | superseded historical module | LTR closure explicitly keeps manual review explanation回退，不恢复 | LTR readonly explanation minimal surface and simple-chat explanation |
| real OpenAI smoke evidence | skip as current evidence | 真实 key/smoke 不能进入 wiki；disabled/mock path is accepted safety proof | backend-only adapter with no key exposure and blocked unsafe outputs |

## Lessons

- Agent prompt source 必须 artifact-backed；动态服务 payload 只能是上游 source 或历史背景。
- `target_weight`、`target_position`、orders、monitor scan、provider publish 等英文/字段级语义必须在后端阻断，不依赖前端。
- Browser E2E fixture 只证明 network denylist 和 UI flow，不证明生产 Agent artifact 已发布。
- 真实 OpenAI key、Authorization header、token、完整 payload、截图都不得进入报告或 wiki。

## Sources

- `docs/tw_agent_daily_prompt_rebuild/PHASE0_EXECUTION_REPORT_CN.md`
- `docs/tw_agent_daily_prompt_rebuild/PHASE0_TO_PHASE6_FINAL_SUMMARY_CN.md`
- `docs/tw_agent_daily_prompt_rebuild/PHASE6_FINAL_ACCEPTANCE_REVIEW_CN.md`
- `docs/tw_modular_daily_update_productization/PHASEUI2_STRATEGY_WORKBENCH_AGENT_UX_FINAL_ROUTE_REVIEW_CN.md`
