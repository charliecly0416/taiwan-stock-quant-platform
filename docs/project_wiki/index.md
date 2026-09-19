---
title: Wiki Index
category: index
tags: [wiki, index]
sources: []
summary: 项目知识库的内容索引，按 project、concept、skill、reference 和 synthesis 分类。
provenance:
  extracted: 1.0
  inferred: 0.0
  ambiguous: 0.0
base_confidence: 0.5
lifecycle: draft
lifecycle_changed: 2026-06-20
tier: supporting
created: 2026-06-20T00:00:00Z
updated: 2026-06-20T18:00:00Z
---

# Wiki Index

## Project Wiki
- [[README|Project Wiki Vault]] - 本项目本地 Obsidian-compatible wiki vault 的使用说明。 ( #wiki #setup )
- [[FULL_INGEST_PHASEW1_CORE_CONTRACTS_REPORT_CN|Phase W1 Core Contracts Report]] - W1 contract/config/skill ingest 执行报告。 ( #wiki #ingest #w1 )
- [[FULL_INGEST_PHASEW1_CORE_CONTRACTS_REVIEW_CN|Phase W1 Core Contracts Review]] - W1 审查报告。 ( #wiki #review #w1 )
- [[FULL_INGEST_PHASEW1_CORE_CONTRACTS_FOLLOWUP_CN|Phase W1 Core Contracts Follow-up]] - W1 review H1 templates 分流修复报告。 ( #wiki #ingest #w1 )
- [[FULL_INGEST_PHASEW2_PRODUCT_ROUTES_REPORT_CN|Phase W2 Product Routes Report]] - W2 产品路线 ingest 执行报告。 ( #wiki #ingest #w2 )
- [[FULL_INGEST_PHASEW2_PRODUCT_ROUTES_REVIEW_CN|Phase W2 Product Routes Review]] - W2 产品路线审查报告。 ( #wiki #review #w2 )
- [[FULL_INGEST_PHASEW2_PRODUCT_ROUTES_FOLLOWUP_CN|Phase W2 Product Routes Follow-up]] - W2 Sources section follow-up 修复报告。 ( #wiki #ingest #w2 )
- [[FULL_INGEST_PHASEW2_PRODUCT_ROUTES_FOLLOWUP_REVIEW_CN|Phase W2 Product Routes Follow-up Review]] - W2 follow-up 审查报告。 ( #wiki #review #w2 )
- [[FULL_INGEST_PHASEW3_CODE_MAP_WORK_CN|Phase W3 Code Map Work]] - W3 源码/脚本/测试映射工作文档。 ( #wiki #work #w3 )
- [[FULL_INGEST_PHASEW3_CODE_MAP_REPORT_CN|Phase W3 Code Map Report]] - W3 code-map 执行报告。 ( #wiki #ingest #w3 )
- [[FULL_INGEST_PHASEW4_HISTORY_LESSONS_WORK_CN|Phase W4 History Lessons Work]] - W4 历史路线/弯路归档工作文档。 ( #wiki #work #w4 )
- [[FULL_INGEST_PHASEW4_HISTORY_LESSONS_REPORT_CN|Phase W4 History Lessons Report]] - W4 历史路线降权与教训蒸馏执行报告。 ( #wiki #ingest #w4 )

- [[PROJECT_WIKI_FULL_INGEST_EXECUTION_AND_REVIEW_PLAN_CN|Project Wiki Full Ingest Plan]] - 项目专属 wiki 全仓知识编译总计划。 ( #wiki #plan )
- [[FULL_INGEST_PHASEW1_CORE_CONTRACTS_WORK_CN|Phase W1 Core Contracts Work]] - W1 核心合同/配置/skill 工作文档。 ( #wiki #work #w1 )
- [[FULL_INGEST_PHASEW2_PRODUCT_ROUTES_WORK_CN|Phase W2 Product Routes Work]] - W2 产品路线 ingest 工作文档。 ( #wiki #work #w2 )
- [[FULL_INGEST_PHASEW2_PRODUCT_ROUTES_FOLLOWUP_WORK_CN|Phase W2 Product Routes Follow-up Work]] - W2 follow-up provenance 修复工作文档。 ( #wiki #work #w2 )
- [[FULL_INGEST_PHASEW3_CODE_MAP_REVIEW_CN|Phase W3 Code Map Review]] - W3 code-map 审查报告。 ( #wiki #review #w3 )
- [[FULL_INGEST_PHASEW4_HISTORY_LESSONS_REVIEW_CN|Phase W4 History Lessons Review]] - W4 历史路线降权审查报告。 ( #wiki #review #w4 )
- [[FULL_INGEST_PHASEW5_FINAL_SUMMARY_WORK_CN|Phase W5 Final Summary Work]] - W5 最终健康审查工作文档。 ( #wiki #work #w5 )
- [[FULL_INGEST_PHASEW5_FINAL_SUMMARY_CN|Phase W5 Final Summary]]
- [[FULL_INGEST_PHASEW5R_FRONTMATTER_REPAIR_REPORT_CN|Phase W5R Frontmatter Repair Report]] - W5 项目知识库最终总结。 ( #wiki #summary #w5 )
## Projects
- [[projects/taiwan-stock-quant-platform/taiwan-stock-quant-platform|Taiwan Stock Quant Platform]] - 台股只读研究、模型/策略 artifact、Agent 与前端策略工作台项目总览。 ( #project #tw-stock #readonly )

## Concepts
- [[concepts/modular-artifact-chain|Modular Artifact Chain]] - DataSource 到 Frontend/Agent 的 artifact 合约链路。 ( #concept #tw-stock )
- [[concepts/product-artifact-registry|Product Artifact Registry]] - 产品 registry、默认 artifact root、只读 flags 与前端路径边界。 ( #concept #tw-stock )
- [[concepts/current-default-model-and-strategy|Current Default Model And Strategy]] - 当前默认 profile、模型、策略、candidate boundary 与执行价假设。 ( #concept #tw-stock )
- [[concepts/data-freshness-and-latest-pointers|Data Freshness And Latest Pointers]] - provider raw/latest、qlib accepted latest、snapshot latest、Agent latest 四类 latest。 ( #concept #tw-stock )
- [[concepts/readonly-safety-boundary|Readonly Safety Boundary]] - 只读、数据刷新、monitor write、broker/order、OpenAI key 等红线。 ( #concept #tw-stock )
- [[concepts/agent-daily-prompt-route|Agent Daily Prompt Route]] - DailyAgentPromptArtifact、backend simple-chat 与前端 Agent panel 路线。 ( #concept #tw-stock )
- [[concepts/frontend-strategy-workbench|Frontend Strategy Workbench]] - 策略工作台只读展示、current-strategy-context 与 Agent panel 边界。 ( #concept #tw-stock )
- [[concepts/daily-update-data-flow|Daily Update Data Flow]] - 日更数据从价格、模型、LTR、策略快照到前端的流动方式。 ( #concept #tw-stock )

## Skills
- [[skills/new-model-onboarding-workflow|New Model Onboarding Workflow]] - 新模型进入 ModelSignalArtifact、registry、golden sample、OOS evidence 和 validator。 ( #skill #workflow )
- [[skills/new-strategy-onboarding-workflow|New Strategy Onboarding Workflow]] - 新策略通过 StrategyRule、OrderIntentArtifact、ReplayResultArtifact 和 readonly snapshot 接入。 ( #skill #workflow )
- [[skills/readonly-e2e-acceptance-workflow|Readonly E2E Acceptance Workflow]] - 只读 E2E、network、console、截图和 Agent simple-chat 验收。 ( #skill #workflow )
- [[skills/frontend-ux-review-workflow|Frontend UX Review Workflow]] - 策略工作台 UI/Agent panel 的响应式和展示质量审查。 ( #skill #workflow )
- [[skills/data-freshness-diagnosis-workflow|Data Freshness Diagnosis Workflow]] - 四类 latest、数据源边界和只读状态字段诊断。 ( #skill #workflow )
- [[skills/safety-boundary-review-workflow|Safety Boundary Review Workflow]] - diff、Agent、前端和 E2E 证据中的 forbidden actions 审查。 ( #skill #workflow )
- [[skills/modular-integration-regression-workflow|Modular Integration Regression Workflow]] - 模型到策略到 Agent 的只读集成回归审查。 ( #skill #workflow )
- [[skills/pre-rnd-readiness-governance|Pre-RND Readiness Governance]] - pre-RND 支线验收、统筹交接和后续启动约束。 ( #skill #workflow )

## References
- [[references/agent-daily-prompt-rebuild-final|Agent Daily Prompt Rebuild Final]] - Agent DailyPromptArtifact + simple-chat 最终接受路线。 ( #reference #agent )
- [[references/ui2-frontend-final|UI2 Frontend Final]] - `/tw-stock-monitor` 只读策略工作台最终接受状态。 ( #reference #frontend )
- [[references/skills-maintenance-final|Skills Maintenance Final]] - 九个 project-local tw-stock skills 的最终职责边界。 ( #reference #skills )
- [[references/pre-rnd-readiness-final-handoff|Pre-RND Readiness Final Handoff]] - `ACCEPTED_WITH_CONDITIONS` 的统筹交接摘要。 ( #handoff #acceptance )
- [[references/real-sample-20260618|Real Sample 2026-06-18]] - `TW2330` 与 `TW3481` 的真实样本数据链路摘录。 ( #sample #data )
- [[references/code-map-backend-readonly-routes|Backend Readonly Routes Code Map]] - backend readonly routes/services 与 forbidden boundary source 映射。 ( #reference #backend #w3 )
- [[references/code-map-frontend-workbench|Frontend Workbench Code Map]] - `/tw-stock-monitor` API/helper/component 只读路线映射。 ( #reference #frontend #w3 )
- [[references/code-map-scripts-and-tests|Scripts And Tests Code Map]] - scripts/tests 分类与 fixture/mock 降权说明。 ( #reference #tests #w3 )
- [[references/superseded-routes-model-and-strategy|Superseded Routes Model And Strategy]] - historical/superseded 模型与策略路线边界。 ( #reference #historical #w4 )
- [[references/superseded-routes-agent-and-tools|Superseded Routes Agent And Tools]] - 旧 Agent/tool 路线被 DailyAgentPromptArtifact + simple-chat 替代。 ( #reference #agent #w4 )
- [[references/superseded-routes-monitor-provider-and-trading|Superseded Routes Monitor Provider And Trading]] - monitor/provider/trading 历史路线和禁区边界。 ( #reference #boundary #w4 )

## Synthesis
- [[synthesis/current-mainline-vs-superseded-routes|Current Mainline vs Superseded Routes]] - 当前主线、历史/中间路线和条件接受边界。 ( #synthesis #routes )
- [[synthesis/project-risk-map|Project Risk Map]] - W2 后非阻塞风险、阻塞升级条件和 review entry points。 ( #synthesis #risk )
- [[synthesis/historical-lessons|Historical Lessons]] - W4 历史路线、旧实验、弯路和误读风险蒸馏。 ( #synthesis #historical #w4 )

## Phase Reports
- [[PROJECT_WIKI_FULL_INGEST_EXECUTION_AND_REVIEW_PLAN_CN|Project Wiki Full Ingest Plan]]
- [[FULL_INGEST_PHASEW0_INVENTORY_REPORT_CN|Phase W0 Inventory Report]]
- [[FULL_INGEST_PHASEW0_INVENTORY_REVIEW_CN|Phase W0 Inventory Review]]
- [[FULL_INGEST_PHASEW1_CORE_CONTRACTS_WORK_CN|Phase W1 Core Contracts Work]]
- [[FULL_INGEST_PHASEW1_CORE_CONTRACTS_REPORT_CN|Phase W1 Core Contracts Report]]
- [[FULL_INGEST_PHASEW1_CORE_CONTRACTS_REVIEW_CN|Phase W1 Core Contracts Review]]
- [[FULL_INGEST_PHASEW1_CORE_CONTRACTS_FOLLOWUP_CN|Phase W1 Core Contracts Follow-up]]
- [[FULL_INGEST_PHASEW1_CORE_CONTRACTS_FOLLOWUP_REVIEW_CN|Phase W1 Core Contracts Follow-up Review]]
- [[FULL_INGEST_PHASEW2_PRODUCT_ROUTES_WORK_CN|Phase W2 Product Routes Work]]
- [[FULL_INGEST_PHASEW2_PRODUCT_ROUTES_REPORT_CN|Phase W2 Product Routes Report]]
- [[FULL_INGEST_PHASEW2_PRODUCT_ROUTES_REVIEW_CN|Phase W2 Product Routes Review]]
- [[FULL_INGEST_PHASEW2_PRODUCT_ROUTES_FOLLOWUP_WORK_CN|Phase W2 Product Routes Follow-up Work]]
- [[FULL_INGEST_PHASEW2_PRODUCT_ROUTES_FOLLOWUP_CN|Phase W2 Product Routes Follow-up]]
- [[FULL_INGEST_PHASEW2_PRODUCT_ROUTES_FOLLOWUP_REVIEW_CN|Phase W2 Product Routes Follow-up Review]]
- [[FULL_INGEST_PHASEW3_CODE_MAP_WORK_CN|Phase W3 Code Map Work]]
- [[FULL_INGEST_PHASEW3_CODE_MAP_REPORT_CN|Phase W3 Code Map Report]]
- [[FULL_INGEST_PHASEW3_CODE_MAP_REVIEW_CN|Phase W3 Code Map Review]]
- [[FULL_INGEST_PHASEW4_HISTORY_LESSONS_WORK_CN|Phase W4 History Lessons Work]]
- [[FULL_INGEST_PHASEW4_HISTORY_LESSONS_REPORT_CN|Phase W4 History Lessons Report]]
- [[FULL_INGEST_PHASEW4_HISTORY_LESSONS_REVIEW_CN|Phase W4 History Lessons Review]]
- [[FULL_INGEST_PHASEW5_FINAL_SUMMARY_WORK_CN|Phase W5 Final Summary Work]]
- [[FULL_INGEST_PHASEW5_FINAL_SUMMARY_CN|Phase W5 Final Summary]]
