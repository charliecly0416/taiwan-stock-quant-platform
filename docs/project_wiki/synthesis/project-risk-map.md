---
title: Project Risk Map
category: synthesis
tags: [risk, safety, readiness, product-routes]
sources: ['/home/chuliyang/taiwan-stock-quant-platform/docs/tw_agent_daily_prompt_rebuild/PHASE0_TO_PHASE6_FINAL_SUMMARY_CN.md', '/home/chuliyang/taiwan-stock-quant-platform/docs/tw_agent_daily_prompt_rebuild/PHASE6_FINAL_ACCEPTANCE_REPORT_CN.md', '/home/chuliyang/taiwan-stock-quant-platform/docs/tw_agent_daily_prompt_rebuild/PHASE6_FINAL_ACCEPTANCE_REVIEW_CN.md', '/home/chuliyang/taiwan-stock-quant-platform/docs/tw_agent_daily_prompt_rebuild/POST_ACCEPTANCE_TODO_VALIDATOR_ENGLISH_ORDER_FORBIDDEN_TERMS_REVIEW_CN.md', '/home/chuliyang/taiwan-stock-quant-platform/docs/tw_modular_daily_update_productization/PHASEUI2_STRATEGY_WORKBENCH_AGENT_UX_FINAL_SUMMARY_CN.md', '/home/chuliyang/taiwan-stock-quant-platform/docs/tw_modular_daily_update_productization/PHASEUI2_STRATEGY_WORKBENCH_AGENT_UX_FINAL_ROUTE_REVIEW_CN.md', '/home/chuliyang/taiwan-stock-quant-platform/docs/tw_modular_daily_update_productization/PHASEUI2D_RESPONSIVE_PLAYWRIGHT_ACCEPTANCE_REVIEW_CN.md', '/home/chuliyang/taiwan-stock-quant-platform/docs/tw_modular_daily_update_productization/PHASEUI2C_PAPER_PORTFOLIO_AGENT_FUSION_REVIEW_CN.md', '/home/chuliyang/taiwan-stock-quant-platform/docs/tw_modular_daily_update_productization/MODULAR_DAILY_UPDATE_PRODUCTIZATION_MAINLINE_CN.md', '/home/chuliyang/taiwan-stock-quant-platform/docs/tw_modular_daily_update_productization/MODULAR_DAILY_UPDATE_FINAL_ACCEPTANCE_CN.md', '/home/chuliyang/taiwan-stock-quant-platform/docs/tw_modular_daily_update_productization/PHASEYZ_STRICT_E4_PRODUCTIZATION_FINAL_SUMMARY_CN.md', '/home/chuliyang/taiwan-stock-quant-platform/docs/tw_modular_daily_update_productization/PHASEYZ4_FINAL_CLOSURE_SUMMARY_FOR_COORDINATION_CN.md', '/home/chuliyang/taiwan-stock-quant-platform/docs/tw_new_model_strategy_pre_rnd/PRE_RND_READINESS_FINAL_SUMMARY_CN.md', '/home/chuliyang/taiwan-stock-quant-platform/docs/tw_new_model_strategy_pre_rnd/PRE_RND_READINESS_FINAL_ACCEPTANCE_REVIEW_CN.md', '/home/chuliyang/taiwan-stock-quant-platform/docs/tw_new_model_strategy_pre_rnd/PRE_RND_READINESS_COORDINATOR_HANDOFF_CN.md', '/home/chuliyang/taiwan-stock-quant-platform/docs/tw_skills_maintenance/PHASES4_FINAL_SUMMARY_CN.md', '/home/chuliyang/taiwan-stock-quant-platform/docs/tw_skills_maintenance/PHASES4_FINAL_ACCEPTANCE_REVIEW_CN.md', '/home/chuliyang/taiwan-stock-quant-platform/docs/tw_skills_maintenance/TW_SKILLS_MAINTENANCE_S_ROUTE_FINAL_SUMMARY_CN.md', '/home/chuliyang/taiwan-stock-quant-platform/docs/tw_skills_maintenance/TW_SKILLS_MAINTENANCE_S_ROUTE_FINAL_REVIEW_CN.md']
summary: Current non-blocking risks and safety gates after W2 product route ingest, with escalation boundaries for future work.
provenance:
  extracted: 0.78
  inferred: 0.22
  ambiguous: 0.0
base_confidence: 0.86
lifecycle: draft
lifecycle_changed: 2026-06-20
tier: core
created: 2026-06-20T14:00:00Z
updated: 2026-06-20T17:00:00Z
---

# Project Risk Map

## Non-Blocking Risks

- Production source artifacts for Agent prompt/latest publish still need dry-run checks before enabling publish latest.
- Legacy provider publish and accepted latest code paths still exist but are gate-protected and default unreachable.
- Runtime metadata may still expose archived old skills; project-local skills remain authoritative.
- `.agents/skills/` and `docs/tw_skills_maintenance/` must be versioned before final handoff.
- YZ pending execution price state prevents paper apply; it is correct pending behavior, not a product failure.


## W4 Historical Misread Risks

- Historical phase reports can describe defaults that were valid only inside an old route; current defaults must be checked against [[concepts/current-default-model-and-strategy]].
- Historical returns, one-off smoke passes, screenshots, fixtures and dynamic payloads are not current production evidence unless backed by current artifact manifests, latest pointers and validators.
- `scripts/archive/historical_research/**` is not the active product chain; restoring an archived script requires a new review against current contracts, strict E4 scope and readonly safety boundaries.
- Old Agent/tool routes, monitor/ops panels, provider publish paths and accepted latest switches are likely to be misread because related code/docs still exist; treat them as [[references/superseded-routes-agent-and-tools|superseded]] or [[references/superseded-routes-monitor-provider-and-trading|boundary-only]] unless a newer reviewed source says otherwise.

## Blocking Escalations

Stop and report if future work requests provider publish, accepted latest switch, monitor writes, broker/order/quick-trade, target position/weight, frontend OpenAI, key exposure, production default switch, production artifact/latest publish, or return/probability promises.

## Review Entry Points

- [[skills/safety-boundary-review-workflow]] for forbidden action or text risk.
- [[skills/readonly-e2e-acceptance-workflow]] for Playwright/network/console acceptance.
- [[skills/data-freshness-diagnosis-workflow]] for latest/asof confusion.
- [[skills/modular-integration-regression-workflow]] for cross-artifact route checks.

## W3 Code-Level Risks

- Forbidden live trading/quick-trade/credential code exists in the repo and must remain boundary-only documentation.
- `tw_stock.py` still contains ops/monitor/provider/latest endpoints near current readonly routes; future reviews must not infer product authorization from co-location.
- Frontend E2E fixtures can make a UI path appear complete; W3 demotes fixture/mock/dynamic payloads to non-production evidence unless backed by artifact manifests/latest pointers.
- Publisher scripts such as `publish_tw_modular_readonly_snapshot.py` are not provider publish, but still must not be run during code-map or read-only review phases.

## Related

- [[concepts/readonly-safety-boundary]]
- [[synthesis/current-mainline-vs-superseded-routes]]

## Sources

- `docs/tw_agent_daily_prompt_rebuild/PHASE6_FINAL_ACCEPTANCE_REVIEW_CN.md`
- `docs/tw_modular_daily_update_productization/PHASEYZ4_FINAL_CLOSURE_SUMMARY_FOR_COORDINATION_CN.md`
- `docs/tw_new_model_strategy_pre_rnd/PRE_RND_READINESS_FINAL_SUMMARY_CN.md`
- `docs/tw_new_model_strategy_pre_rnd/PRE_RND_READINESS_FINAL_ACCEPTANCE_REVIEW_CN.md`
- `docs/tw_skills_maintenance/PHASES4_FINAL_SUMMARY_CN.md`
- `docs/tw_skills_maintenance/PHASES4_FINAL_ACCEPTANCE_REVIEW_CN.md`
- `docs/tw_skills_maintenance/TW_SKILLS_MAINTENANCE_S_ROUTE_FINAL_REVIEW_CN.md`
