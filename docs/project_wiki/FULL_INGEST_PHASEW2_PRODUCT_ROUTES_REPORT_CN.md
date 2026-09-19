---
title: Phasew2 Product Routes Report
category: references
tags: [wiki, full-ingest, w2, report]
sources: []
summary: 产品路线、Agent、前端和日更支线编译的执行报告，作为项目 wiki 支线过程证据。
provenance:
  extracted: 1.0
  inferred: 0.0
  ambiguous: 0.0
base_confidence: 0.5
lifecycle: draft
lifecycle_changed: 2026-06-20
tier: peripheral
created: 2026-06-20T19:00:00Z
updated: 2026-06-20T19:00:00Z
---

# Project Wiki Full Ingest Phase W2 执行报告

## 1. 本阶段结论

Phase W2 已完成。已从四个产品路线主源目录编译最终稳定知识，保留 W1 当前默认模型/策略/registry/latest 边界，并把失败过程、中间修复、历史路线和 `ACCEPTED_WITH_CONDITIONS` 明确降权。

本次只修改 `docs/project_wiki/**`。未运行服务、未刷新数据、未 provider publish/refresh、未 accepted latest switch、未写 monitor、未 broker/order/quick-trade、未读取 OpenAI key、未真实 OpenAI smoke、未训练模型、未生成策略 artifact、未发布 readonly snapshot。

## 2. 读取的 source 范围

- `docs/tw_agent_daily_prompt_rebuild/`：29 个文件。
- `docs/tw_modular_daily_update_productization/`：30 个文件。
- `docs/tw_new_model_strategy_pre_rnd/`：24 个文件。
- `docs/tw_skills_maintenance/`：21 个文件。

## 3. 明确排除的 source 范围

未读取产品源码、测试、数据 artifact、运行态输出、OpenAI key、外部网络或 W2 主源目录之外的历史文档。W2 没有把 phase 中间失败过程逐篇建 reference 页面。

## 4. 新增 / 更新的 wiki 页面

新增：

- `references/agent-daily-prompt-rebuild-final.md`
- `references/ui2-frontend-final.md`
- `references/skills-maintenance-final.md`
- `synthesis/current-mainline-vs-superseded-routes.md`
- `synthesis/project-risk-map.md`

更新：

- `concepts/agent-daily-prompt-route.md`
- `concepts/frontend-strategy-workbench.md`
- `concepts/daily-update-data-flow.md`
- `concepts/readonly-safety-boundary.md`
- `skills/readonly-e2e-acceptance-workflow.md`
- `skills/frontend-ux-review-workflow.md`
- `skills/data-freshness-diagnosis-workflow.md`
- `skills/safety-boundary-review-workflow.md`
- `skills/modular-integration-regression-workflow.md`
- `references/pre-rnd-readiness-final-handoff.md`
- `skills/pre-rnd-readiness-governance.md`
- `index.md`、`hot.md`、`log.md`、`.manifest.json`

## 5. manifest / index / hot / log 更新

- `.manifest.json` 已记录 W2 source entry，source key 使用绝对路径，包含 `content_hash`、`modified_at`、`size_bytes`、`pages_created`、`pages_updated`、`source_type`、`project`。
- `index.md` 已修复 W1 follow-up 重复条目，并加入 W2 references/synthesis/report。
- `hot.md` 已更新 W2 recent activity、active threads、key takeaways。
- `log.md` 已追加 `W2_PRODUCT_ROUTES` 记录。

## 6. 当前事实与历史事实边界

当前事实仍以 W1 为基准：`strict_e4_yz_product`、base `e4_frozen_qlib_2018_2022`、treatment `e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025`、display alias `e4_frozen_qlib_2023_2025_ltr`、default strategy `top50_exit_one_worst_sell`、candidate boundary `qlib_top50`、ranking `ltr_rerank_within_qlib_top50`、execution price mode `next_open`。

W2 新增当前事实：Agent 是 DailyAgentPromptArtifact + backend simple-chat；前端是 `/tw-stock-monitor` readonly strategy workbench；日更是 readonly daily chain；project-local tw-stock skills 是当前权威 skill 来源。

历史/中间路线写入 [[synthesis/current-mainline-vs-superseded-routes]]，不作为当前默认事实。

## 7. 安全边界确认

W2 全部路线保持 readonly：禁止 provider publish/refresh、accepted latest switch、monitor write、broker/order/quick-trade、target_position/target_weight、frontend OpenAI/key、真实 OpenAI smoke、训练、生产 default/latest 切换、收益/胜率/上涨概率承诺。

## 8. 自检结果

- 已修复 `index.md` 中 W1 follow-up 重复条目。
- manifest JSON 可解析。
- W2 四个主源目录 source files 共 104 个，已全部分类。
- 新增/更新页面均保留 Obsidian wikilinks。
- 未执行运行态命令或产品状态变更。

## 9. 遗留问题

- W2 是产品路线文档编译，不验证源代码和运行态 artifact 的现时一致性。
- `.agents/skills/` 与 `docs/tw_skills_maintenance/` 的版本化状态仍由统筹/后续提交处理。
- Archive skill metadata 可能仍被运行时展示，需后续运行时配置专项处理。
- 生产启用 Agent prompt publish latest 前仍需单独 dry-run 和 source artifact 检查。

## 10. 请求审查者审查的问题

- 是否接受 W2 将 final summaries/reviews 编译为 3 个 references + 2 个 synthesis，而不是逐篇 phase report 建页？
- 是否接受 `ACCEPTED_WITH_CONDITIONS` 只写成条件接受，不作为无条件 readiness？
- 是否接受 superseded/intermediate 路线表对历史失败和修复过程的降权？

## 四个 W2 主源目录文件分流表

### docs/tw_agent_daily_prompt_rebuild

| 文件 | 分流 | 处理 |
| --- | --- | --- |
| `docs/tw_agent_daily_prompt_rebuild/PHASE0_EXECUTION_REPORT_CN.md` | execution report | 作为分流/source provenance，不单独建页 |
| `docs/tw_agent_daily_prompt_rebuild/PHASE0_REVIEW_CN.md` | review report | 作为分流/source provenance，不单独建页 |
| `docs/tw_agent_daily_prompt_rebuild/PHASE0_TO_PHASE6_FINAL_SUMMARY_CN.md` | final summary / final review | 用于最终稳定事实 |
| `docs/tw_agent_daily_prompt_rebuild/PHASE1_EXECUTION_REPORT_CN.md` | execution report | 作为分流/source provenance，不单独建页 |
| `docs/tw_agent_daily_prompt_rebuild/PHASE1_FIX_EXECUTION_REPORT_CN.md` | failed/intermediate/fix history | 作为分流/source provenance，不单独建页 |
| `docs/tw_agent_daily_prompt_rebuild/PHASE1_FIX_REVIEW_CN.md` | failed/intermediate/fix history | 作为分流/source provenance，不单独建页 |
| `docs/tw_agent_daily_prompt_rebuild/PHASE1_REVIEW_CN.md` | review report | 作为分流/source provenance，不单独建页 |
| `docs/tw_agent_daily_prompt_rebuild/PHASE1_WORK_CN.md` | work plan / optimization plan | 作为分流/source provenance，不单独建页 |
| `docs/tw_agent_daily_prompt_rebuild/PHASE2_EXECUTION_REPORT_CN.md` | execution report | 作为分流/source provenance，不单独建页 |
| `docs/tw_agent_daily_prompt_rebuild/PHASE2_REVIEW_CN.md` | review report | 作为分流/source provenance，不单独建页 |
| `docs/tw_agent_daily_prompt_rebuild/PHASE2_WORK_CN.md` | work plan / optimization plan | 作为分流/source provenance，不单独建页 |
| `docs/tw_agent_daily_prompt_rebuild/PHASE3_EXECUTION_REPORT_CN.md` | execution report | 作为分流/source provenance，不单独建页 |
| `docs/tw_agent_daily_prompt_rebuild/PHASE3_FIX_EXECUTION_REPORT_CN.md` | failed/intermediate/fix history | 作为分流/source provenance，不单独建页 |
| `docs/tw_agent_daily_prompt_rebuild/PHASE3_FIX_REVIEW_CN.md` | failed/intermediate/fix history | 作为分流/source provenance，不单独建页 |
| `docs/tw_agent_daily_prompt_rebuild/PHASE3_REVIEW_CN.md` | review report | 作为分流/source provenance，不单独建页 |
| `docs/tw_agent_daily_prompt_rebuild/PHASE3_WORK_CN.md` | work plan / optimization plan | 作为分流/source provenance，不单独建页 |
| `docs/tw_agent_daily_prompt_rebuild/PHASE4_EXECUTION_REPORT_CN.md` | execution report | 作为分流/source provenance，不单独建页 |
| `docs/tw_agent_daily_prompt_rebuild/PHASE4_REVIEW_CN.md` | review report | 作为分流/source provenance，不单独建页 |
| `docs/tw_agent_daily_prompt_rebuild/PHASE4_WORK_CN.md` | work plan / optimization plan | 作为分流/source provenance，不单独建页 |
| `docs/tw_agent_daily_prompt_rebuild/PHASE5_EXECUTION_REPORT_CN.md` | execution report | 作为分流/source provenance，不单独建页 |
| `docs/tw_agent_daily_prompt_rebuild/PHASE5_REVIEW_CN.md` | review report | 作为分流/source provenance，不单独建页 |
| `docs/tw_agent_daily_prompt_rebuild/PHASE5_WORK_CN.md` | work plan / optimization plan | 作为分流/source provenance，不单独建页 |
| `docs/tw_agent_daily_prompt_rebuild/PHASE6_FINAL_ACCEPTANCE_REPORT_CN.md` | final summary / final review | 用于最终稳定事实 |
| `docs/tw_agent_daily_prompt_rebuild/PHASE6_FINAL_ACCEPTANCE_REVIEW_CN.md` | final summary / final review | 用于最终稳定事实 |
| `docs/tw_agent_daily_prompt_rebuild/PHASE6_WORK_CN.md` | work plan / optimization plan | 作为分流/source provenance，不单独建页 |
| `docs/tw_agent_daily_prompt_rebuild/POST_ACCEPTANCE_TODO_VALIDATOR_ENGLISH_ORDER_FORBIDDEN_TERMS_EXECUTION_REPORT_CN.md` | execution report | 作为分流/source provenance，不单独建页 |
| `docs/tw_agent_daily_prompt_rebuild/POST_ACCEPTANCE_TODO_VALIDATOR_ENGLISH_ORDER_FORBIDDEN_TERMS_EXECUTOR_WORK_CN.md` | work plan / optimization plan | 作为分流/source provenance，不单独建页 |
| `docs/tw_agent_daily_prompt_rebuild/POST_ACCEPTANCE_TODO_VALIDATOR_ENGLISH_ORDER_FORBIDDEN_TERMS_REVIEW_CN.md` | review report | 作为分流/source provenance，不单独建页 |
| `docs/tw_agent_daily_prompt_rebuild/POST_ACCEPTANCE_TODO_VALIDATOR_ENGLISH_ORDER_FORBIDDEN_TERMS_WORK_CN.md` | work plan / optimization plan | 作为分流/source provenance，不单独建页 |

### docs/tw_modular_daily_update_productization

| 文件 | 分流 | 处理 |
| --- | --- | --- |
| `docs/tw_modular_daily_update_productization/MODULAR_DAILY_UPDATE_FINAL_ACCEPTANCE_CN.md` | final summary / final review | 用于最终稳定事实 |
| `docs/tw_modular_daily_update_productization/MODULAR_DAILY_UPDATE_PRODUCTIZATION_MAINLINE_CN.md` | work plan / optimization plan | 作为分流/source provenance，不单独建页 |
| `docs/tw_modular_daily_update_productization/MODULAR_DAILY_UPDATE_REVIEWER_CHECKLIST_CN.md` | review report | 作为分流/source provenance，不单独建页 |
| `docs/tw_modular_daily_update_productization/MODULAR_DAILY_UPDATE_RUNBOOK_CN.md` | work plan / optimization plan | 作为分流/source provenance，不单独建页 |
| `docs/tw_modular_daily_update_productization/PHASEU3_REVIEW_AND_FINAL_CLOSURE_CN.md` | final summary / final review | 用于最终稳定事实 |
| `docs/tw_modular_daily_update_productization/PHASEUI2B_CANDIDATES_AND_REPLAY_FIX_EXECUTION_REPORT_CN.md` | failed/intermediate/fix history | 作为分流/source provenance，不单独建页 |
| `docs/tw_modular_daily_update_productization/PHASEUI2B_CANDIDATES_AND_REPLAY_FIX_REVIEW_CN.md` | failed/intermediate/fix history | 作为分流/source provenance，不单独建页 |
| `docs/tw_modular_daily_update_productization/PHASEUI2B_CANDIDATES_AND_REPLAY_REVIEW_CN.md` | review report | 作为分流/source provenance，不单独建页 |
| `docs/tw_modular_daily_update_productization/PHASEUI2B_CANDIDATES_AND_REPLAY_WORK_CN.md` | work plan / optimization plan | 作为分流/source provenance，不单独建页 |
| `docs/tw_modular_daily_update_productization/PHASEUI2C_PAPER_PORTFOLIO_AGENT_FUSION_EXECUTION_REPORT_CN.md` | execution report | 作为分流/source provenance，不单独建页 |
| `docs/tw_modular_daily_update_productization/PHASEUI2C_PAPER_PORTFOLIO_AGENT_FUSION_REVIEW_CN.md` | review report | 作为分流/source provenance，不单独建页 |
| `docs/tw_modular_daily_update_productization/PHASEUI2C_PAPER_PORTFOLIO_AGENT_FUSION_WORK_CN.md` | work plan / optimization plan | 作为分流/source provenance，不单独建页 |
| `docs/tw_modular_daily_update_productization/PHASEUI2D_RESPONSIVE_PLAYWRIGHT_ACCEPTANCE_EXECUTION_REPORT_CN.md` | execution report | 作为分流/source provenance，不单独建页 |
| `docs/tw_modular_daily_update_productization/PHASEUI2D_RESPONSIVE_PLAYWRIGHT_ACCEPTANCE_REVIEW_CN.md` | review report | 作为分流/source provenance，不单独建页 |
| `docs/tw_modular_daily_update_productization/PHASEUI2D_RESPONSIVE_PLAYWRIGHT_ACCEPTANCE_WORK_CN.md` | work plan / optimization plan | 作为分流/source provenance，不单独建页 |
| `docs/tw_modular_daily_update_productization/PHASEUI2_STRATEGY_WORKBENCH_AGENT_UX_EXECUTION_REPORT_CN.md` | execution report | 作为分流/source provenance，不单独建页 |
| `docs/tw_modular_daily_update_productization/PHASEUI2_STRATEGY_WORKBENCH_AGENT_UX_FINAL_ROUTE_REVIEW_CN.md` | final summary / final review | 用于最终稳定事实 |
| `docs/tw_modular_daily_update_productization/PHASEUI2_STRATEGY_WORKBENCH_AGENT_UX_FINAL_SUMMARY_CN.md` | final summary / final review | 用于最终稳定事实 |
| `docs/tw_modular_daily_update_productization/PHASEUI2_STRATEGY_WORKBENCH_AGENT_UX_OPTIMIZATION_PLAN_CN.md` | work plan / optimization plan | 作为分流/source provenance，不单独建页 |
| `docs/tw_modular_daily_update_productization/PHASEUI2_STRATEGY_WORKBENCH_AGENT_UX_REVIEW_CN.md` | review report | 作为分流/source provenance，不单独建页 |
| `docs/tw_modular_daily_update_productization/PHASEUI_STRATEGY_WORKBENCH_FRONTEND_UX_REPAIR_WORK_CN.md` | work plan / optimization plan | 作为分流/source provenance，不单独建页 |
| `docs/tw_modular_daily_update_productization/PHASEV_ROUTE_SUMMARY_FOR_COORDINATION_REVIEW_CN.md` | review report | 作为分流/source provenance，不单独建页 |
| `docs/tw_modular_daily_update_productization/PHASEW0_REVIEW_AND_CLOSURE_CN.md` | final summary / final review | 用于最终稳定事实 |
| `docs/tw_modular_daily_update_productization/PHASEX_PAPER_PORTFOLIO_STRATEGY_AND_SIMULATION_APP_FINAL_SUMMARY_CN.md` | final summary / final review | 用于最终稳定事实 |
| `docs/tw_modular_daily_update_productization/PHASEYZ4_FINAL_CLOSURE_SUMMARY_FOR_COORDINATION_CN.md` | final summary / final review | 用于最终稳定事实 |
| `docs/tw_modular_daily_update_productization/PHASEYZ_FINAL_SUMMARY_REVIEW_AND_REPAIR_SUGGESTION_CN.md` | final summary / final review | 用于最终稳定事实 |
| `docs/tw_modular_daily_update_productization/PHASEYZ_FOLLOWUP_EXECUTION_PRICE_CONTRACT_SUGGESTION_CN.md` | supporting source | 作为分流/source provenance，不单独建页 |
| `docs/tw_modular_daily_update_productization/PHASEYZ_STRICT_E4_PRODUCTIZATION_FINAL_SUMMARY_CN.md` | final summary / final review | 用于最终稳定事实 |
| `docs/tw_modular_daily_update_productization/REAL_PROVIDER_DAILY_UPDATE_REVIEWER_CHECKLIST_CN.md` | review report | 作为分流/source provenance，不单独建页 |
| `docs/tw_modular_daily_update_productization/REAL_PROVIDER_DAILY_UPDATE_RUNBOOK_CN.md` | work plan / optimization plan | 作为分流/source provenance，不单独建页 |

### docs/tw_new_model_strategy_pre_rnd

| 文件 | 分流 | 处理 |
| --- | --- | --- |
| `docs/tw_new_model_strategy_pre_rnd/PHASER0_VERSION_FREEZE_INVENTORY_EXECUTION_REPORT_CN.md` | execution report | 作为分流/source provenance，不单独建页 |
| `docs/tw_new_model_strategy_pre_rnd/PHASER0_VERSION_FREEZE_INVENTORY_REVIEW_CN.md` | review report | 作为分流/source provenance，不单独建页 |
| `docs/tw_new_model_strategy_pre_rnd/PHASER1R2_REMAINING_REGRESSION_REPAIR_EXECUTION_REPORT_CN.md` | failed/intermediate/fix history | 作为分流/source provenance，不单独建页 |
| `docs/tw_new_model_strategy_pre_rnd/PHASER1R2_REMAINING_REGRESSION_REPAIR_REVIEW_CN.md` | failed/intermediate/fix history | 作为分流/source provenance，不单独建页 |
| `docs/tw_new_model_strategy_pre_rnd/PHASER1R2_REMAINING_REGRESSION_REPAIR_WORK_CN.md` | work plan / optimization plan | 作为分流/source provenance，不单独建页 |
| `docs/tw_new_model_strategy_pre_rnd/PHASER1_READONLY_INTEGRATION_REGRESSION_EXECUTION_REPORT_CN.md` | execution report | 作为分流/source provenance，不单独建页 |
| `docs/tw_new_model_strategy_pre_rnd/PHASER1_READONLY_INTEGRATION_REGRESSION_REVIEW_CN.md` | review report | 作为分流/source provenance，不单独建页 |
| `docs/tw_new_model_strategy_pre_rnd/PHASER1_READONLY_INTEGRATION_REGRESSION_WORK_CN.md` | work plan / optimization plan | 作为分流/source provenance，不单独建页 |
| `docs/tw_new_model_strategy_pre_rnd/PHASER1_REPAIR_EXECUTION_REPORT_CN.md` | failed/intermediate/fix history | 作为分流/source provenance，不单独建页 |
| `docs/tw_new_model_strategy_pre_rnd/PHASER1_REPAIR_REVIEW_CN.md` | failed/intermediate/fix history | 作为分流/source provenance，不单独建页 |
| `docs/tw_new_model_strategy_pre_rnd/PHASER1_REPAIR_WORK_CN.md` | work plan / optimization plan | 作为分流/source provenance，不单独建页 |
| `docs/tw_new_model_strategy_pre_rnd/PHASER2_SKILL_RUNTIME_ENTRY_EXECUTION_REPORT_CN.md` | failed/intermediate/fix history | 作为分流/source provenance，不单独建页 |
| `docs/tw_new_model_strategy_pre_rnd/PHASER2_SKILL_RUNTIME_ENTRY_REVIEW_CN.md` | failed/intermediate/fix history | 作为分流/source provenance，不单独建页 |
| `docs/tw_new_model_strategy_pre_rnd/PHASER2_SKILL_RUNTIME_ENTRY_WORK_CN.md` | work plan / optimization plan | 作为分流/source provenance，不单独建页 |
| `docs/tw_new_model_strategy_pre_rnd/PHASER3_ARTIFACT_CHAIN_ENTRY_EXECUTION_REPORT_CN.md` | execution report | 作为分流/source provenance，不单独建页 |
| `docs/tw_new_model_strategy_pre_rnd/PHASER3_ARTIFACT_CHAIN_ENTRY_REVIEW_CN.md` | review report | 作为分流/source provenance，不单独建页 |
| `docs/tw_new_model_strategy_pre_rnd/PHASER3_ARTIFACT_CHAIN_ENTRY_WORK_CN.md` | work plan / optimization plan | 作为分流/source provenance，不单独建页 |
| `docs/tw_new_model_strategy_pre_rnd/PRE_RND_READINESS_COORDINATOR_HANDOFF_CN.md` | accepted-with-conditions | 作为分流/source provenance，不单独建页 |
| `docs/tw_new_model_strategy_pre_rnd/PRE_RND_READINESS_EXECUTION_AND_REVIEW_PLAN_CN.md` | review report | 作为分流/source provenance，不单独建页 |
| `docs/tw_new_model_strategy_pre_rnd/PRE_RND_READINESS_FINAL_ACCEPTANCE_REVIEW_CN.md` | final summary / final review | 用于最终稳定事实 |
| `docs/tw_new_model_strategy_pre_rnd/PRE_RND_READINESS_FINAL_SUMMARY_CN.md` | final summary / final review | 用于最终稳定事实 |
| `docs/tw_new_model_strategy_pre_rnd/PRE_RND_READINESS_FINAL_SUMMARY_WORK_CN.md` | final summary / final review | 用于最终稳定事实 |
| `docs/tw_new_model_strategy_pre_rnd/TW_DAILY_UPDATE_DATA_FLOW_EXPLAINED_FOR_BEGINNERS_CN.md` | supporting source | 作为分流/source provenance，不单独建页 |
| `docs/tw_new_model_strategy_pre_rnd/TW_DAILY_UPDATE_DATA_FLOW_REAL_SAMPLE_20260618_CN.md` | supporting source | 作为分流/source provenance，不单独建页 |

### docs/tw_skills_maintenance

| 文件 | 分流 | 处理 |
| --- | --- | --- |
| `docs/tw_skills_maintenance/PHASES0_INVENTORY_EXECUTION_REPORT_CN.md` | execution report | 作为分流/source provenance，不单独建页 |
| `docs/tw_skills_maintenance/PHASES0_INVENTORY_REVIEW_CN.md` | review report | 作为分流/source provenance，不单独建页 |
| `docs/tw_skills_maintenance/PHASES1R_PROJECT_SKILLS_MIGRATION_EXECUTION_REPORT_CN.md` | execution report | 作为分流/source provenance，不单独建页 |
| `docs/tw_skills_maintenance/PHASES1R_PROJECT_SKILLS_MIGRATION_REVIEW_CN.md` | review report | 作为分流/source provenance，不单独建页 |
| `docs/tw_skills_maintenance/PHASES1R_PROJECT_SKILLS_MIGRATION_WORK_CN.md` | work plan / optimization plan | 作为分流/source provenance，不单独建页 |
| `docs/tw_skills_maintenance/PHASES1_EXISTING_SKILLS_UPDATE_EXECUTION_REPORT_CN.md` | execution report | 作为分流/source provenance，不单独建页 |
| `docs/tw_skills_maintenance/PHASES1_EXISTING_SKILLS_UPDATE_REVIEW_CN.md` | review report | 作为分流/source provenance，不单独建页 |
| `docs/tw_skills_maintenance/PHASES1_EXISTING_SKILLS_UPDATE_WORK_CN.md` | work plan / optimization plan | 作为分流/source provenance，不单独建页 |
| `docs/tw_skills_maintenance/PHASES1_EXISTING_SKILLS_UPDATE_WORK_V2_CN.md` | work plan / optimization plan | 作为分流/source provenance，不单独建页 |
| `docs/tw_skills_maintenance/PHASES2_NEW_SKILLS_EXECUTION_REPORT_CN.md` | execution report | 作为分流/source provenance，不单独建页 |
| `docs/tw_skills_maintenance/PHASES2_NEW_SKILLS_REVIEW_CN.md` | review report | 作为分流/source provenance，不单独建页 |
| `docs/tw_skills_maintenance/PHASES2_NEW_SKILLS_WORK_CN.md` | work plan / optimization plan | 作为分流/source provenance，不单独建页 |
| `docs/tw_skills_maintenance/PHASES3_SKILLS_TRIGGER_AND_BOUNDARY_VALIDATION_EXECUTION_REPORT_CN.md` | execution report | 作为分流/source provenance，不单独建页 |
| `docs/tw_skills_maintenance/PHASES3_SKILLS_TRIGGER_AND_BOUNDARY_VALIDATION_REVIEW_CN.md` | review report | 作为分流/source provenance，不单独建页 |
| `docs/tw_skills_maintenance/PHASES3_SKILLS_TRIGGER_AND_BOUNDARY_VALIDATION_WORK_CN.md` | work plan / optimization plan | 作为分流/source provenance，不单独建页 |
| `docs/tw_skills_maintenance/PHASES4_FINAL_ACCEPTANCE_REVIEW_CN.md` | final summary / final review | 用于最终稳定事实 |
| `docs/tw_skills_maintenance/PHASES4_FINAL_SUMMARY_AND_ACCEPTANCE_WORK_CN.md` | final summary / final review | 用于最终稳定事实 |
| `docs/tw_skills_maintenance/PHASES4_FINAL_SUMMARY_CN.md` | final summary / final review | 用于最终稳定事实 |
| `docs/tw_skills_maintenance/TW_SKILLS_MAINTENANCE_BRANCH_WORK_CN.md` | work plan / optimization plan | 作为分流/source provenance，不单独建页 |
| `docs/tw_skills_maintenance/TW_SKILLS_MAINTENANCE_S_ROUTE_FINAL_REVIEW_CN.md` | final summary / final review | 用于最终稳定事实 |
| `docs/tw_skills_maintenance/TW_SKILLS_MAINTENANCE_S_ROUTE_FINAL_SUMMARY_CN.md` | final summary / final review | 用于最终稳定事实 |

## W1 follow-up review Low issue 修复说明

已修复 `index.md` 中 `FULL_INGEST_PHASEW1_CORE_CONTRACTS_FOLLOWUP_CN` 重复条目，保留单条“W1 review H1 templates 分流修复报告”描述。

## Agent route 最终结论表

| 问题 | 最终结论 |
| --- | --- |
| Agent 当前路线 | DailyAgentPromptArtifact -> TWStockAgentSimpleChatService -> `/api/tw-stock/agent/simple-chat` -> 前端只读展示 |
| Simple-chat 允许边界 | 只读策略解释；payload 限 `question`、`symbol`、`maxItems` |
| Forbidden intent | order/place/submit order、target_position/target_weight、monitor write、provider publish、accepted latest、broker/quick-trade、收益/胜率/上涨概率承诺 |
| OpenAI 边界 | 前端不得直连；真实 key 只能后端 env 注入且报告不得泄漏 |
| Daily prompt publish | 默认关闭、dry-run、默认不 publish latest |

## Frontend/UI2 route 最终结论表

| 问题 | 最终结论 |
| --- | --- |
| 当前前端主路径 | `/tw-stock-monitor` readonly strategy workbench |
| 主页面顺序 | 今日策略总览 -> 候选名单 -> 历史模拟 -> 模拟账户状态 -> 策略解释助手 |
| Agent 角色 | 策略解释助手，不是交易助手 |
| UI2 验收 | desktop/tablet/mobile Playwright DOM audit、network audit、console/page audit 通过 |
| 模拟账户 | 只影响模拟账户；不连接券商；pending execution price 时后端阻断 apply |

## accepted-with-conditions 条件表

| 来源 | 条件 |
| --- | --- |
| Pre-RND readiness | `ACCEPTED_WITH_CONDITIONS`，仅允许窄范围单变量新模型/新策略研发 |
| 新模型第一轮 | 建议单新模型，止于 ModelSignalArtifact + registry + golden sample + OOS evidence + validator + review |
| 新策略 | 可开但不建议第一轮；止于 StrategyDependency/Rule、OrderIntentArtifact、readonly ReplayResultArtifact |
| Agent publish latest | 生产启用前必须 dry-run 检查 source artifacts、asof、checksum、warnings |
| Skills maintenance | project-local skills 为准；archive skills 不得作为 active 来源 |

## superseded/intermediate 路线表

| 路线 | 降权原因 |
| --- | --- |
| legacy `/agent/chat` / complex tool Agent 主路径 | 被 backend simple-chat 只读解释路线替代 |
| 工程调试型 `/tw-stock-monitor` 主路径 | 被 UI2 用户可理解的策略工作台替代 |
| old/fresh/P3/O4/bridge/frozen fresh 2025 LTR 默认模型 | 被 clean strict E4 registry/default path 替代 |
| `origin/original`、buggy/smoke/template strategy | historical/diagnostic/template，不是生产默认 |
| YZ4 pending replay return | 只是 pending execution price 下的 readonly display，不是收益证明 |
