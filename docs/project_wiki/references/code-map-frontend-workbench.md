---
title: Frontend Workbench Code Map
category: references
tags: [frontend, workbench, readonly, code-map]
relationships:
  - target: "[[concepts/frontend-strategy-workbench]]"
    type: related_to
  - target: "[[concepts/agent-daily-prompt-route]]"
    type: related_to
  - target: "[[concepts/readonly-safety-boundary]]"
    type: uses
sources: [/home/chuliyang/taiwan-stock-quant-platform/frontend/src/api/tw-stock.js, /home/chuliyang/taiwan-stock-quant-platform/frontend/src/views/tw-stock-monitor/index.vue, /home/chuliyang/taiwan-stock-quant-platform/frontend/src/views/tw-stock-monitor/components/ReadonlyStrategySnapshotPanel.vue, /home/chuliyang/taiwan-stock-quant-platform/frontend/src/views/tw-stock-monitor/components/ReadonlyReplayWindowPanel.vue, /home/chuliyang/taiwan-stock-quant-platform/frontend/src/views/tw-stock-monitor/components/PaperPortfolioPanel.vue, /home/chuliyang/taiwan-stock-quant-platform/frontend/src/views/tw-stock-monitor/components/ReplayAuditDetail.vue]
summary: `/tw-stock-monitor` 前端 API 与组件映射，确认 Agent panel 走 backend simple-chat，候选/回放/模拟账户保持只读语义。
provenance:
  extracted: 0.9
  inferred: 0.1
  ambiguous: 0.0
base_confidence: 0.86
lifecycle: draft
lifecycle_changed: 2026-06-20
tier: supporting
created: 2026-06-20T16:00:00Z
updated: 2026-06-20T16:00:00Z
---

# Frontend Workbench Code Map

`/tw-stock-monitor` 的当前产品解释应以 W1/W2 的 readonly strategy workbench 为准。W3 静态读取确认该页面仍含旧 monitor/ops 区块，但当前主线 API 和组件是 current-strategy-context、readonly snapshot/replay、paper/sim account 和 Agent simple-chat。

## API Map

| API helper | HTTP path | Current role |
|---|---|---|
| `getTwStockCurrentStrategyContext` | `GET /api/tw-stock/current-strategy-context` | 今日策略口径、模型/策略、ranking、asof consistency、paper portfolio context |
| `getTwStockReadonlyStrategySnapshot` | `GET /api/tw-stock/readonly-strategy-snapshot` | 候选名单和调出复核的只读 snapshot |
| `getTwStockReadonlyReplayWindowIndex` | `GET /api/tw-stock/readonly-replay-window-index` | 可选 replay window index |
| `getTwStockReadonlyReplayWindow` | `GET /api/tw-stock/readonly-replay-window` | 已登记只读历史模拟窗口详情 |
| `simpleChatTwStockAgent` | `POST /api/tw-stock/agent/simple-chat` | Agent panel 唯一当前解释入口 |
| `getTwStockPaperPortfolioLatestDecision` / `getTwStockPaperPortfolioState` | `GET /api/tw-stock/paper-portfolio/*` | 模拟账户状态和 clean decision |
| `applyTwStockPaperPortfolioDecision` | `POST /api/tw-stock/paper-portfolio/apply-decision` | 模拟账户 apply gate；不是 broker/order |
| `draftTwStockSimOrder` / `confirmTwStockSimOrder` / `cancelTwStockSimOrder` | `POST /api/tw-stock/sim/orders/*` | simulation-only ledger；不得写成真实交易能力 |

## Component Map

| Component | Responsibility | Safety notes |
|---|---|---|
| `frontend/src/views/tw-stock-monitor/index.vue` | 组合今日策略、候选、历史模拟、模拟账户、Agent panel、旧 monitor/ops 区块 | Agent submit 调用 `simpleChatTwStockAgent`；readonly panels 从 GET endpoints 读取 |
| `ReadonlyStrategySnapshotPanel.vue` | 展示候选调入、调出复核、freshness、checksum/audit | gate 需要 `readonly_only=true`、`production_trade_enabled=false`、`not_order=true`、`no_order_action=true`、`not_target_position=true` |
| `ReadonlyReplayWindowPanel.vue` | 展示 replay window、费用/税费、收益指标、覆盖和审计 | 明确“只用于研究复盘”，不在前端本地 replay |
| `PaperPortfolioPanel.vue` | 展示模拟账户、clean decision、apply/reset controls | apply 前检查 simulation flags；后端仍是权威 gate |
| `ReplayAuditDetail.vue` | 折叠显示技术审计字段 | 技术细节默认不改变产品主语义 |

## Direct OpenAI / Broker Boundary

前端 simple-chat helper 只拼 `/agent/simple-chat`，不携带 OpenAI key、OpenAI endpoint、model 或 tool/action 权限。`index.vue` 可显示 OpenAI backend mode，但不得浏览器直连 `api.openai.com`。旧 quick-trade、broker、target position/weight 和 monitor write 请求若出现在测试中，应作为 forbidden network audit 项而不是当前能力。

## Fixture Demotion

前端 E2E 会 route/fulfill mock payload 并写 network/console audit JSON。这些 payload 只能证明 UI 与 forbidden request 审计规则，不是生产 artifact、真实 snapshot 或真实 replay 结果。

## Sources

- `frontend/src/api/tw-stock.js`
- `frontend/src/views/tw-stock-monitor/index.vue`
- `frontend/src/views/tw-stock-monitor/components/ReadonlyStrategySnapshotPanel.vue`
- `frontend/src/views/tw-stock-monitor/components/ReadonlyReplayWindowPanel.vue`
- `frontend/src/views/tw-stock-monitor/components/PaperPortfolioPanel.vue`
- `frontend/src/views/tw-stock-monitor/components/ReplayAuditDetail.vue`
