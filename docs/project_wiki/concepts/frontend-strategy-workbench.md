---
title: Frontend Strategy Workbench
category: concepts
tags: [frontend, workbench, readonly, agent]
aliases: [/tw-stock-monitor, 策略工作台]
relationships:
  - target: "[[concepts/readonly-safety-boundary]]"
    type: uses
  - target: "[[concepts/current-default-model-and-strategy]]"
    type: related_to
  - target: "[[skills/frontend-ux-review-workflow]]"
    type: related_to
sources: ['/home/chuliyang/taiwan-stock-quant-platform/docs/tw_modular_contracts/FRONTEND_READONLY_DISPLAY_CONTRACT_CN.md', '/home/chuliyang/taiwan-stock-quant-platform/docs/tw_modular_contracts/FRONTEND_AGENT_PANEL_CONTRACT_CN.md', '/home/chuliyang/taiwan-stock-quant-platform/docs/tw_modular_contracts/TW_CURRENT_STRATEGY_CONTEXT_API_FIELD_DICTIONARY_CN.md', '/home/chuliyang/taiwan-stock-quant-platform/.agents/skills/tw-stock-frontend-workbench-ux-review/SKILL.md', '/home/chuliyang/taiwan-stock-quant-platform/docs/tw_modular_daily_update_productization/PHASEUI2_STRATEGY_WORKBENCH_AGENT_UX_FINAL_SUMMARY_CN.md', '/home/chuliyang/taiwan-stock-quant-platform/docs/tw_modular_daily_update_productization/PHASEUI2_STRATEGY_WORKBENCH_AGENT_UX_FINAL_ROUTE_REVIEW_CN.md', '/home/chuliyang/taiwan-stock-quant-platform/docs/tw_modular_daily_update_productization/PHASEUI2D_RESPONSIVE_PLAYWRIGHT_ACCEPTANCE_REVIEW_CN.md', '/home/chuliyang/taiwan-stock-quant-platform/docs/tw_modular_daily_update_productization/PHASEUI2C_PAPER_PORTFOLIO_AGENT_FUSION_REVIEW_CN.md']
summary: /tw-stock-monitor 当前是只读策略工作台：今日策略总览、候选名单、历史模拟、模拟账户状态和策略解释助手。
provenance:
  extracted: 0.9
  inferred: 0.1
  ambiguous: 0.0
base_confidence: 0.9
lifecycle: draft
lifecycle_changed: 2026-06-20
tier: core
created: 2026-06-20T12:00:00Z
updated: 2026-06-20T17:00:00Z
---

# Frontend Strategy Workbench

`/tw-stock-monitor` 的当前产品角色是 Taiwan stock readonly strategy workbench。UI2 final review 确认它已从工程调试面板收敛为：今日策略总览 -> 候选名单 -> 历史模拟 -> 模拟账户状态 -> 策略解释助手。

## Current Main Path

- 今日策略总览：信号日期、目标交易日、模型/策略、候选覆盖、榜首标的、模拟账户状态和 execution price pending 状态。
- 候选名单：候选调入、调出复核、排名、股票代码/名称、LTR/Qlib/全市场排名摘要。
- 历史模拟：测试窗口、净收益、最大回撤、交易次数、费用/税费、覆盖状态，但不得承诺未来收益。
- 模拟账户状态：现金、持仓数、当前决策日期、可否应用、阻断原因、预计模拟调入/调出；只影响模拟账户，不连接券商，不提交真实订单。
- 策略解释助手：只调用 backend simple-chat，回答策略、候选、调出复核、模拟账户阻断原因和数据新鲜度。

## API Boundary

统一只读入口是：

```text
GET /api/tw-stock/current-strategy-context
POST /api/tw-stock/agent/simple-chat
```

UI2-C review 修正文档口径：没有新增后端 API；前端 helper/调用切换到既有 `/agent/simple-chat`，用于只读策略解释。

## Display Semantics

工程字段如 manifest、checksum、schema、execution_price_mode、raw model id、artifact path、ReplayWindowPolicy、final equity、turnover proxy 等仍可查，但默认折叠，不抢占主路径。`ltr_top10`、`top_candidates` 与 `exit_candidates` 都是只读研究对象，不是成交或订单。

## Acceptance Evidence

UI2-D / final route review 通过 desktop/tablet/mobile Playwright audit、network audit、console/page audit 和 PNG structural audit：无横向溢出，技术详情默认折叠，`forbidden_request_count=0`，console/page error 为 0。

## W3 Code Evidence

- API helpers: `frontend/src/api/tw-stock.js` 定义 `getTwStockCurrentStrategyContext`、`getTwStockReadonlyStrategySnapshot`、`getTwStockReadonlyReplayWindowIndex`、`getTwStockReadonlyReplayWindow` 和 `simpleChatTwStockAgent`。
- Main view: `frontend/src/views/tw-stock-monitor/index.vue` 组合 current strategy context、readonly snapshot、readonly replay window、paper portfolio 和 Agent panel。
- Snapshot panel: `ReadonlyStrategySnapshotPanel.vue` 明确检查 `readonly_only`、`production_trade_enabled=false`、`not_order`、`no_order_action`、`not_target_position` 和 validation/checksum。
- Replay panel: `ReadonlyReplayWindowPanel.vue` 展示已登记窗口、费用/税费、收益指标和审计详情；文案限定为研究复盘。
- Paper panel: `PaperPortfolioPanel.vue` 面向 simulation-only account；后端仍执行 checksum/idempotency/confirmation gate。
- `index.vue` 仍含旧 monitor/ops 区块，W3 将其降级为历史/边界代码，不把它们写成当前主线。


## W4 Historical Boundary

Old monitor/ops/debug panels and UI routes documented in historical phase files do not replace the current `/tw-stock-monitor` readonly strategy workbench. Provider publish, accepted latest, monitor writes and trading controls remain historical or boundary-only surfaces, tracked in [[references/superseded-routes-monitor-provider-and-trading]].

## Sources

- [[references/ui2-frontend-final|UI2 Frontend Final]]
- [[references/code-map-frontend-workbench|Frontend Workbench Code Map]]
- `docs/tw_modular_contracts/FRONTEND_READONLY_DISPLAY_CONTRACT_CN.md`
- `.agents/skills/tw-stock-frontend-workbench-ux-review/SKILL.md`
