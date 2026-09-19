---
title: Readonly E2E Acceptance Workflow
category: skills
tags: [e2e, readonly, playwright, acceptance]
aliases: [只读 E2E 验收流程]
relationships:
  - target: "[[concepts/frontend-strategy-workbench]]"
    type: related_to
  - target: "[[concepts/readonly-safety-boundary]]"
    type: uses
sources: [/home/chuliyang/taiwan-stock-quant-platform/.agents/skills/tw-stock-readonly-e2e-acceptance/SKILL.md, /home/chuliyang/taiwan-stock-quant-platform/.agents/skills/tw-stock-readonly-e2e-acceptance/references/readonly-boundary.md, /home/chuliyang/taiwan-stock-quant-platform/.agents/skills/tw-stock-readonly-e2e-acceptance/references/acceptance-report-template.md]
summary: 只读验收审查 /tw-stock-monitor、Agent simple-chat、DailyAgentPromptArtifact gate、截图、network 和 console 证据。
provenance:
  extracted: 0.88
  inferred: 0.12
  ambiguous: 0.0
base_confidence: 0.84
lifecycle: draft
lifecycle_changed: 2026-06-20
tier: supporting
created: 2026-06-20T12:00:00Z
updated: 2026-06-20T16:00:00Z
---

# Readonly E2E Acceptance Workflow

Readonly acceptance 只验证证据，不操作数据管线或交易系统。覆盖 `/tw-stock-monitor`、strategy workbench UI、Agent simple-chat、DailyAgentPromptArtifact dry-run/validator、desktop/tablet/mobile screenshots、network audit 和 console audit。

## Required Evidence

- summary/audit JSON、network_audit.json、console_audit.json。
- desktop/tablet/mobile screenshots。
- frontend static checks、backend readonly pytest、DailyAgentPromptArtifact dry-run/validator when applicable。
- simple-chat request count and path when Agent panel is clicked。

## Pass Criteria

`forbidden_request_count`、monitor write counts、ops dry-run POST count、frontend OpenAI direct request count、broker/quick-trade/order request count、failed response count、console/page error count must be zero for acceptance evidence.

## Boundary

`POST /api/tw-stock/agent/simple-chat` is allowed only as backend readonly explanation. Old `/agent/chat` must not be the frontend main path, and browser-side OpenAI calls are forbidden.

## W2 Product Route Evidence

W2 final sources add two accepted readonly evidence families: Agent simple-chat network audit and UI2 strategy workbench desktop/tablet/mobile Playwright audit. Acceptance remains evidence-only: `forbidden_request_count=0`, monitor write counts are zero, frontend OpenAI direct requests are zero, broker/order/quick-trade requests are zero, and console/page errors are zero.

Agent accepted POST path is `/api/tw-stock/agent/simple-chat`; UI2 accepted workbench path is `/tw-stock-monitor`. These are not trading or data-refresh paths.

## W3 Test Evidence Map

- Agent panel: `frontend/tests/e2e/tw-stock-agent-simple-chat-network.mjs` and `frontend/tests/unit/tw-stock-agent-simple-chat-check.mjs` audit `/agent/simple-chat`, frontend OpenAI direct calls, broker/quick-trade/order, monitor writes and provider/latest requests.
- Readonly replay/snapshot: `frontend/tests/e2e/tw-stock-readonly-replay-window-readonly.mjs`, `frontend/tests/e2e/tw-stock-readonly-strategy-snapshot-readonly.mjs` and unit static checks verify GET-only route usage, labels and forbidden network counts.
- Backend API: `backend/tests/test_tw_stock_readonly_replay_window_api.py` and `backend/tests/test_tw_stock_readonly_strategy_snapshot_api.py` assert readonly flags and no write methods.
- These tests use mocks/fixtures and are evidence of guardrails, not production artifacts.

## Sources

- [[references/code-map-scripts-and-tests|Scripts And Tests Code Map]]
- `.agents/skills/tw-stock-readonly-e2e-acceptance/SKILL.md`
- `.agents/skills/tw-stock-readonly-e2e-acceptance/references/readonly-boundary.md`
