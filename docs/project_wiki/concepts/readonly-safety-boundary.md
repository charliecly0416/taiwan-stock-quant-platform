---
title: Readonly Safety Boundary
category: concepts
tags: [readonly, safety, broker, accepted-latest, agent]
aliases: [只读边界, 交易安全红线]
relationships:
  - target: "[[concepts/modular-artifact-chain]]"
    type: related_to
  - target: "[[concepts/data-freshness-and-latest-pointers]]"
    type: related_to
  - target: "[[skills/safety-boundary-review-workflow]]"
    type: related_to
sources: ['/home/chuliyang/taiwan-stock-quant-platform/docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md', '/home/chuliyang/taiwan-stock-quant-platform/docs/tw_modular_contracts/READONLY_STRATEGY_SNAPSHOT_CONTRACT_CN.md', '/home/chuliyang/taiwan-stock-quant-platform/docs/tw_modular_contracts/TW_AGENT_DAILY_PROMPT_ARTIFACT_CONTRACT_CN.md', '/home/chuliyang/taiwan-stock-quant-platform/docs/tw_modular_contracts/FRONTEND_READONLY_DISPLAY_CONTRACT_CN.md', '/home/chuliyang/taiwan-stock-quant-platform/.agents/skills/tw-stock-safety-boundary-review/SKILL.md', '/home/chuliyang/taiwan-stock-quant-platform/.agents/skills/tw-stock-safety-boundary-review/references/forbidden-actions.md', '/home/chuliyang/taiwan-stock-quant-platform/docs/tw_agent_daily_prompt_rebuild/PHASE0_TO_PHASE6_FINAL_SUMMARY_CN.md', '/home/chuliyang/taiwan-stock-quant-platform/docs/tw_agent_daily_prompt_rebuild/PHASE6_FINAL_ACCEPTANCE_REPORT_CN.md', '/home/chuliyang/taiwan-stock-quant-platform/docs/tw_agent_daily_prompt_rebuild/PHASE6_FINAL_ACCEPTANCE_REVIEW_CN.md', '/home/chuliyang/taiwan-stock-quant-platform/docs/tw_agent_daily_prompt_rebuild/POST_ACCEPTANCE_TODO_VALIDATOR_ENGLISH_ORDER_FORBIDDEN_TERMS_REVIEW_CN.md', '/home/chuliyang/taiwan-stock-quant-platform/docs/tw_modular_daily_update_productization/PHASEUI2_STRATEGY_WORKBENCH_AGENT_UX_FINAL_SUMMARY_CN.md', '/home/chuliyang/taiwan-stock-quant-platform/docs/tw_modular_daily_update_productization/PHASEUI2_STRATEGY_WORKBENCH_AGENT_UX_FINAL_ROUTE_REVIEW_CN.md', '/home/chuliyang/taiwan-stock-quant-platform/docs/tw_modular_daily_update_productization/PHASEUI2D_RESPONSIVE_PLAYWRIGHT_ACCEPTANCE_REVIEW_CN.md', '/home/chuliyang/taiwan-stock-quant-platform/docs/tw_modular_daily_update_productization/PHASEUI2C_PAPER_PORTFOLIO_AGENT_FUSION_REVIEW_CN.md', '/home/chuliyang/taiwan-stock-quant-platform/docs/tw_modular_daily_update_productization/MODULAR_DAILY_UPDATE_PRODUCTIZATION_MAINLINE_CN.md', '/home/chuliyang/taiwan-stock-quant-platform/docs/tw_modular_daily_update_productization/MODULAR_DAILY_UPDATE_FINAL_ACCEPTANCE_CN.md', '/home/chuliyang/taiwan-stock-quant-platform/docs/tw_modular_daily_update_productization/PHASEYZ_STRICT_E4_PRODUCTIZATION_FINAL_SUMMARY_CN.md', '/home/chuliyang/taiwan-stock-quant-platform/docs/tw_modular_daily_update_productization/PHASEYZ4_FINAL_CLOSURE_SUMMARY_FOR_COORDINATION_CN.md', '/home/chuliyang/taiwan-stock-quant-platform/docs/tw_new_model_strategy_pre_rnd/PRE_RND_READINESS_FINAL_SUMMARY_CN.md', '/home/chuliyang/taiwan-stock-quant-platform/docs/tw_new_model_strategy_pre_rnd/PRE_RND_READINESS_FINAL_ACCEPTANCE_REVIEW_CN.md', '/home/chuliyang/taiwan-stock-quant-platform/docs/tw_new_model_strategy_pre_rnd/PRE_RND_READINESS_COORDINATOR_HANDOFF_CN.md', '/home/chuliyang/taiwan-stock-quant-platform/docs/tw_skills_maintenance/PHASES4_FINAL_SUMMARY_CN.md', '/home/chuliyang/taiwan-stock-quant-platform/docs/tw_skills_maintenance/PHASES4_FINAL_ACCEPTANCE_REVIEW_CN.md', '/home/chuliyang/taiwan-stock-quant-platform/docs/tw_skills_maintenance/TW_SKILLS_MAINTENANCE_S_ROUTE_FINAL_SUMMARY_CN.md', '/home/chuliyang/taiwan-stock-quant-platform/docs/tw_skills_maintenance/TW_SKILLS_MAINTENANCE_S_ROUTE_FINAL_REVIEW_CN.md']
summary: 台股主线默认是只读研究系统，禁止 provider publish、accepted latest switch、monitor 写入、broker/order 和目标仓位语义。
provenance:
  extracted: 0.9
  inferred: 0.1
  ambiguous: 0.0
base_confidence: 0.88
lifecycle: draft
lifecycle_changed: 2026-06-20
tier: core
created: 2026-06-20T00:00:00Z
updated: 2026-06-20T17:00:00Z
---

# Readonly Safety Boundary

台股平台当前主线是 artifact-backed readonly research，不是实盘交易系统。候选、排名、模拟账户、Agent 回答和前端展示都必须保留“研究观察、人工复盘、历史模拟”的语义。

## Forbidden By Default

- 真实 Yahoo/FinMind 数据拉取、provider refresh、provider publish。
- provider accepted latest 或 qlib accepted latest switch。
- monitor config save、monitor scan、scan-all、alerts write。
- broker、quick-trade、order、place order、submit order。
- `target_position`、`target_weight`、目标仓位、目标权重。
- frontend OpenAI direct call、OpenAI key/base URL/bearer token 暴露。
- 根据单次 replay 收益自动切默认模型或默认策略。
- 用动态服务 payload 假装 artifact 链路存在。

## Allowed Readonly Contexts

- GET readonly API、静态 artifact manifest/latest pointer、validator 输出、fixture-routed Playwright。
- `POST /api/tw-stock/agent/simple-chat` 仅作为 backend readonly explanation endpoint。
- ReadonlyStrategySnapshot、ReadonlyReplayWindow、DailyAgentPromptArtifact、current-strategy-context、paper portfolio gate 和 research context digest。

## Required Semantics

- `candidate_rank`、`score_rank`、`buy_score`、`full_qlib_rank` 和 qlib score 是横截面研究排序信号，不是收益率、胜率、上涨概率、买入概率、仓位或订单大小。
- `ReadonlyStrategySnapshot.latest.json` 只指向 readonly snapshot，不是 provider/qlib accepted latest。
- Agent prompt latest、readonly snapshot latest、qlib accepted latest 和 provider raw/latest 是不同概念。
- Frontend 可展示候选调入、调出复核、历史模拟、模拟账户状态和策略解释助手；不得展示买入建议、卖出建议、目标仓位、保证收益或自动下单。

## W2 Product Route Closures

W2 final sources confirm the same boundary across Agent, UI2, daily update, pre-RND and skills maintenance: accepted routes are readonly explanation, readonly strategy workbench, readonly daily artifacts, simulated paper-account gates and project-local skills. Accepted-with-conditions does not mean unrestricted product acceptance; it only allows narrow new model/new strategy R&D with default/latest paths unchanged.

Specific closures:

- Agent route accepted only as DailyAgentPromptArtifact -> backend simple-chat -> frontend readonly explanation.
- UI2 accepted only as `/tw-stock-monitor` readonly workbench, with Agent as strategy explanation assistant.
- Daily update accepted only as readonly daily chain with GET-only API and readonly latest pointer.
- Pre-RND readiness accepted with conditions, allowing only narrow single-variable R&D first.
- Skills maintenance accepted project-local `.agents/skills/tw-stock-*` as authority; archive skills are not active source.

## Review Entry

涉及 Agent、前端文案、network audit、DailyAgentPromptArtifact、OpenAI adapter 或 diff 审查时，进入 [[skills/safety-boundary-review-workflow]]。

## W3 Forbidden Boundary Code Sources

- `backend/app/routes/quick_trade.py`、`backend/app/services/live_trading/**`、`backend/app/services/trading_executor.py` 和 `backend/app/services/exchange_execution.py` 只作为 broker/order/live trading 禁区证据。
- `backend/app/routes/credentials.py` 只作为 credential/API key/broker policy 边界证据；wiki 不记录 secret、token 或完整 credential payload。
- `backend/app/routes/tw_stock.py` 中的 monitor config/alerts/scan、accepted latest scheduler、normal publish、ops dry-run endpoints 不能写成 W1/W2 当前产品主线。
- `backend/app/services/tw_stock_sim_account.py` 和 paper portfolio apply 是 simulation-only ledger/gate；它们不能升级成 broker/order 能力。


## W4 Historical Boundary

Historical docs may mention provider publish, accepted latest switches, monitor writes, quick-trade, broker/order, credentials or target position/weight while describing old work. W4 classifies those appearances as boundary-only evidence in [[references/superseded-routes-monitor-provider-and-trading]], not as allowed current capabilities.

## Sources

- [[references/code-map-backend-readonly-routes|Backend Readonly Routes Code Map]]
- [[references/code-map-frontend-workbench|Frontend Workbench Code Map]]
- `docs/tw_modular_contracts/READONLY_STRATEGY_SNAPSHOT_CONTRACT_CN.md`
- `docs/tw_modular_contracts/TW_AGENT_DAILY_PROMPT_ARTIFACT_CONTRACT_CN.md`
- `.agents/skills/tw-stock-safety-boundary-review/SKILL.md`
