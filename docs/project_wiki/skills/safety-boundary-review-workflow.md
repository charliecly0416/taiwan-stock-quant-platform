---
title: Safety Boundary Review Workflow
category: skills
tags: [safety, readonly, review, forbidden-actions]
aliases: [只读安全边界审查流程]
relationships:
  - target: "[[concepts/readonly-safety-boundary]]"
    type: implements
sources: [/home/chuliyang/taiwan-stock-quant-platform/.agents/skills/tw-stock-safety-boundary-review/SKILL.md, /home/chuliyang/taiwan-stock-quant-platform/.agents/skills/tw-stock-safety-boundary-review/references/forbidden-actions.md, /home/chuliyang/taiwan-stock-quant-platform/.agents/skills/tw-stock-safety-boundary-review/references/network-audit-rules.md]
summary: 安全边界审查检查 diff、Agent、前端、artifacts 和 E2E evidence 是否越过只读、交易、OpenAI 和 latest 红线。
provenance:
  extracted: 0.9
  inferred: 0.1
  ambiguous: 0.0
base_confidence: 0.84
lifecycle: draft
lifecycle_changed: 2026-06-20
tier: supporting
created: 2026-06-20T12:00:00Z
updated: 2026-06-20T16:00:00Z
---

# Safety Boundary Review Workflow

Safety review 用于审查 diffs、Agent answers、DailyAgentPromptArtifact、prompt builder/validator、OpenAI adapter、frontend text、screenshots、network audit 和 console audit。

## Checks

- broker、quick-trade、order、place order、submit order、target_position、target_weight。
- monitor config/scan/alerts writes。
- provider publish/refresh、qlib refresh、accepted latest switch。
- frontend OpenAI key/base URL/browser-side call。
- forged citations、unsafe buy/sell semantics、qlib score 被误解为收益率/胜率/上涨概率/买入概率/仓位。

## Allowed Contexts

Forbidden keywords can appear in refusals, safety disclaimers, readonly flags, historical simulation labels, validator deny-lists and forbidden-action documentation.

## Output

Findings should lead, ordered by severity, with file/artifact references and evidence.

## W2 Product Route Evidence

W2 accepted product routes share the same forbidden set: no broker/order/quick-trade, no target position/weight, no monitor config/scan/alerts write, no provider publish/refresh, no accepted latest switch, no frontend OpenAI/key exposure, no default model/strategy switch, and no return/probability promise. Accepted-with-conditions must remain conditional.

## W3 Code Review Anchors

- Current allowed Agent route: `backend/app/routes/tw_stock.py` `/agent/simple-chat` plus `backend/app/services/tw_stock_agent_simple_chat.py`.
- Forbidden code sources: `backend/app/routes/quick_trade.py`, `backend/app/routes/credentials.py`, `backend/app/services/live_trading/**`, `backend/app/services/exchange_execution.py`, `backend/app/services/trading_executor.py`.
- Frontend forbidden network anchors: quick-trade/broker/order, target position/weight, monitor config/scan/alerts, provider publish/accepted latest and browser OpenAI.
- Allowed forbidden terms appear only in refusals, deny-lists, safety labels, audit rows and boundary documentation.

## Sources

- [[references/code-map-backend-readonly-routes|Backend Readonly Routes Code Map]]
- [[references/code-map-frontend-workbench|Frontend Workbench Code Map]]
- `.agents/skills/tw-stock-safety-boundary-review/SKILL.md`
- `.agents/skills/tw-stock-safety-boundary-review/references/forbidden-actions.md`
- `.agents/skills/tw-stock-safety-boundary-review/references/network-audit-rules.md`
