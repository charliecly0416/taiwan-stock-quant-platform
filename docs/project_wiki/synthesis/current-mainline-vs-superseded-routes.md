---
title: Current Mainline vs Superseded Routes
category: synthesis
tags: [mainline, superseded, product-routes]
sources: ['/home/chuliyang/taiwan-stock-quant-platform/docs/tw_agent_daily_prompt_rebuild/PHASE0_TO_PHASE6_FINAL_SUMMARY_CN.md', '/home/chuliyang/taiwan-stock-quant-platform/docs/tw_agent_daily_prompt_rebuild/PHASE6_FINAL_ACCEPTANCE_REPORT_CN.md', '/home/chuliyang/taiwan-stock-quant-platform/docs/tw_agent_daily_prompt_rebuild/PHASE6_FINAL_ACCEPTANCE_REVIEW_CN.md', '/home/chuliyang/taiwan-stock-quant-platform/docs/tw_agent_daily_prompt_rebuild/POST_ACCEPTANCE_TODO_VALIDATOR_ENGLISH_ORDER_FORBIDDEN_TERMS_REVIEW_CN.md', '/home/chuliyang/taiwan-stock-quant-platform/docs/tw_modular_daily_update_productization/PHASEUI2_STRATEGY_WORKBENCH_AGENT_UX_FINAL_SUMMARY_CN.md', '/home/chuliyang/taiwan-stock-quant-platform/docs/tw_modular_daily_update_productization/PHASEUI2_STRATEGY_WORKBENCH_AGENT_UX_FINAL_ROUTE_REVIEW_CN.md', '/home/chuliyang/taiwan-stock-quant-platform/docs/tw_modular_daily_update_productization/PHASEUI2D_RESPONSIVE_PLAYWRIGHT_ACCEPTANCE_REVIEW_CN.md', '/home/chuliyang/taiwan-stock-quant-platform/docs/tw_modular_daily_update_productization/PHASEUI2C_PAPER_PORTFOLIO_AGENT_FUSION_REVIEW_CN.md', '/home/chuliyang/taiwan-stock-quant-platform/docs/tw_modular_daily_update_productization/MODULAR_DAILY_UPDATE_PRODUCTIZATION_MAINLINE_CN.md', '/home/chuliyang/taiwan-stock-quant-platform/docs/tw_modular_daily_update_productization/MODULAR_DAILY_UPDATE_FINAL_ACCEPTANCE_CN.md', '/home/chuliyang/taiwan-stock-quant-platform/docs/tw_modular_daily_update_productization/PHASEYZ_STRICT_E4_PRODUCTIZATION_FINAL_SUMMARY_CN.md', '/home/chuliyang/taiwan-stock-quant-platform/docs/tw_modular_daily_update_productization/PHASEYZ4_FINAL_CLOSURE_SUMMARY_FOR_COORDINATION_CN.md', '/home/chuliyang/taiwan-stock-quant-platform/docs/tw_new_model_strategy_pre_rnd/PRE_RND_READINESS_FINAL_SUMMARY_CN.md', '/home/chuliyang/taiwan-stock-quant-platform/docs/tw_new_model_strategy_pre_rnd/PRE_RND_READINESS_FINAL_ACCEPTANCE_REVIEW_CN.md', '/home/chuliyang/taiwan-stock-quant-platform/docs/tw_new_model_strategy_pre_rnd/PRE_RND_READINESS_COORDINATOR_HANDOFF_CN.md', '/home/chuliyang/taiwan-stock-quant-platform/docs/tw_skills_maintenance/PHASES4_FINAL_SUMMARY_CN.md', '/home/chuliyang/taiwan-stock-quant-platform/docs/tw_skills_maintenance/PHASES4_FINAL_ACCEPTANCE_REVIEW_CN.md', '/home/chuliyang/taiwan-stock-quant-platform/docs/tw_skills_maintenance/TW_SKILLS_MAINTENANCE_S_ROUTE_FINAL_SUMMARY_CN.md', '/home/chuliyang/taiwan-stock-quant-platform/docs/tw_skills_maintenance/TW_SKILLS_MAINTENANCE_S_ROUTE_FINAL_REVIEW_CN.md']
summary: Cross-route map separating current accepted product routes from superseded, intermediate, diagnostic or conditional states.
provenance:
  extracted: 0.82
  inferred: 0.18
  ambiguous: 0.0
base_confidence: 0.88
lifecycle: draft
lifecycle_changed: 2026-06-20
tier: core
created: 2026-06-20T14:00:00Z
updated: 2026-06-20T17:00:00Z
---

# Current Mainline vs Superseded Routes

## Current Mainline

- Agent: [[concepts/agent-daily-prompt-route|DailyAgentPromptArtifact -> backend simple-chat -> frontend readonly explanation]].
- Frontend: [[concepts/frontend-strategy-workbench|/tw-stock-monitor readonly strategy workbench]].
- Daily update: [[concepts/daily-update-data-flow|readonly daily chain]] with daily data/features/model signal/order intent/snapshot/run registry/latest pointer.
- Product defaults: [[concepts/current-default-model-and-strategy|strict E4 product profile and top50_exit_one_worst_sell]].
- Skills: project-local `.agents/skills/tw-stock-*` only.

## W3 Code-Level Boundary

W3 maps code co-location without changing route status: `backend/app/routes/tw_stock.py` includes current readonly APIs and older ops/monitor routes in the same file, while frontend `index.vue` includes current strategy workbench plus legacy monitor/ops UI. Current mainline remains the W1/W2 route; co-located legacy code is not promotion evidence.


## W4 Historical Route Boundary

W4 adds historical route distillation only. [[synthesis/historical-lessons]] and the superseded-route references record why older model/strategy, Agent/tool, monitor/provider and trading routes were archived, but they do not modify current defaults.

- Model/strategy history is archived in [[references/superseded-routes-model-and-strategy]]; strict E4 plus `top50_exit_one_worst_sell` remains current.
- Agent/tool history is archived in [[references/superseded-routes-agent-and-tools]]; DailyAgentPromptArtifact plus backend simple-chat remains current.
- Monitor/provider/trading history is archived in [[references/superseded-routes-monitor-provider-and-trading]]; these routes remain safety boundaries or historical evidence only.

## Superseded Or Intermediate

- Complex tool Agent / legacy `/agent/chat` as frontend main path: superseded by backend simple-chat.
- Frontend engineering debug panel main path: superseded by UI2 user-facing strategy workbench.
- Old model defaults such as `fresh_qlib_adaptive`, `fresh_qlib_2025_ltr`, P3/O4/bridge/frozen fresh 2025 LTR: deprecated from product default path.
- `origin/original`, `one_sell_one_buy_buggy_e8r`, smoke/template strategy dependencies: not production defaults.
- YZ4 pending replay artifacts: clean readonly display evidence, not 2026 return proof.

## Conditional Routes

Pre-RND readiness is `ACCEPTED_WITH_CONDITIONS`: it allows only narrow single-variable new model or new strategy R&D and does not allow default/latest switch, production artifact publish, or unrestricted model/strategy development.

## Related

- [[concepts/readonly-safety-boundary]]
- [[references/code-map-backend-readonly-routes]]
- [[references/code-map-frontend-workbench]]
- [[references/code-map-scripts-and-tests]]
- [[references/agent-daily-prompt-rebuild-final]]
- [[references/ui2-frontend-final]]
- [[references/skills-maintenance-final]]

## Sources

- `docs/tw_agent_daily_prompt_rebuild/PHASE0_TO_PHASE6_FINAL_SUMMARY_CN.md`
- `docs/tw_agent_daily_prompt_rebuild/PHASE6_FINAL_ACCEPTANCE_REVIEW_CN.md`
- `docs/tw_modular_daily_update_productization/PHASEUI2_STRATEGY_WORKBENCH_AGENT_UX_FINAL_SUMMARY_CN.md`
- `docs/tw_modular_daily_update_productization/PHASEUI2_STRATEGY_WORKBENCH_AGENT_UX_FINAL_ROUTE_REVIEW_CN.md`
- `docs/tw_modular_daily_update_productization/MODULAR_DAILY_UPDATE_FINAL_ACCEPTANCE_CN.md`
- `docs/tw_modular_daily_update_productization/PHASEYZ_STRICT_E4_PRODUCTIZATION_FINAL_SUMMARY_CN.md`
- `docs/tw_modular_daily_update_productization/PHASEYZ4_FINAL_CLOSURE_SUMMARY_FOR_COORDINATION_CN.md`
- `docs/tw_new_model_strategy_pre_rnd/PRE_RND_READINESS_FINAL_SUMMARY_CN.md`
- `docs/tw_new_model_strategy_pre_rnd/PRE_RND_READINESS_FINAL_ACCEPTANCE_REVIEW_CN.md`
- `docs/tw_skills_maintenance/PHASES4_FINAL_SUMMARY_CN.md`
- `docs/tw_skills_maintenance/PHASES4_FINAL_ACCEPTANCE_REVIEW_CN.md`
