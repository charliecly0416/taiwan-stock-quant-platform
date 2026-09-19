---
title: Phasew1 Core Contracts Report
category: references
tags: [wiki, full-ingest, w1, report]
sources: []
summary: 核心合同、配置和 skills 编译的执行报告，作为项目 wiki 支线过程证据。
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

# Phase W1 Core Contracts Ingest 执行报告

## 结论

已按 `docs/project_wiki/FULL_INGEST_PHASEW1_CORE_CONTRACTS_WORK_CN.md` 完成 W1：围绕 `docs/tw_modular_contracts/`、`configs/`、`.agents/skills/tw-stock-*` 建立核心 contract/config/skill 知识层，并补齐 W0 review 的 M1/M2 要求。

本次只修改 `docs/project_wiki/**`。未运行服务、未刷新数据、未发布 provider/accepted latest、未写 monitor、未生成策略 artifact、未训练模型、未读取 OpenAI key、未执行真实 OpenAI smoke，也未触碰 broker/order/quick-trade/target position/weight。

## 已读取来源范围

- `docs/tw_modular_contracts/*.md`：当前文件系统枚举共 39 个文件，全部分类。
- `configs/**`：当前枚举共 16 个配置文件，重点吸收 product registry、modular registry、data/price/feature registry、strategy dependencies、replay policy/matrix 和 model template。
- `.agents/skills/tw-stock-*`：读取 9 个 `SKILL.md`；对引用的 `references/` 文件做必要读取；对相关 `scripts/` 只做头部/用途检查，未执行。

## 排除来源范围

- 未扩展到 `docs/tw_new_model_strategy_pre_rnd/`、产品源码、测试、数据目录或运行态 artifact。
- 未把历史/deprecated/smoke 配置提升为 current product default。
- 未把任何写操作型脚本或服务运行结果作为 W1 来源。

## 新增 Wiki 页面

- `concepts/product-artifact-registry.md`
- `concepts/current-default-model-and-strategy.md`
- `concepts/frontend-strategy-workbench.md`
- `concepts/data-freshness-and-latest-pointers.md`
- `skills/readonly-e2e-acceptance-workflow.md`
- `skills/frontend-ux-review-workflow.md`
- `skills/data-freshness-diagnosis-workflow.md`
- `skills/safety-boundary-review-workflow.md`
- `skills/modular-integration-regression-workflow.md`

## 更新 Wiki 页面

- `concepts/modular-artifact-chain.md`
- `concepts/readonly-safety-boundary.md`
- `concepts/agent-daily-prompt-route.md`
- `skills/new-model-onboarding-workflow.md`
- `skills/new-strategy-onboarding-workflow.md`
- `index.md`
- `hot.md`
- `log.md`
- `.manifest.json`

## Manifest / Index / Hot / Log 更新

- `.manifest.json` 已更新为 W1 source manifest，source key 使用绝对路径，并记录 `content_hash`、`modified_at`、`size_bytes`、`pages_created`、`pages_updated`、`source_type`、`project`。
- `index.md` 已加入 W1 新增/更新概念页、技能页和 W1 报告入口。
- `hot.md` 已更新 W1 active threads、key takeaways 和 handoff 文件数量差异。
- `log.md` 已追加 W1 ingest 记录。

## 当前 vs 历史边界

- 当前 product profile：`strict_e4_yz_product`。
- 当前 base model：`e4_frozen_qlib_2018_2022`。
- 当前 treatment model：`e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025`。
- 当前 display alias：`e4_frozen_qlib_2023_2025_ltr`。
- 当前默认策略：`top50_exit_one_worst_sell`。
- 当前 candidate boundary：`qlib_top50`。
- 当前 ranking：`ltr_rerank_within_qlib_top50`。
- 当前 execution price mode：`next_open`。
- `one_sell_one_buy_correct` 是 research-only candidate；`one_sell_one_buy_buggy_e8r` 是 diagnostic-only；`original`、`top50_exit_all` 是历史/废弃背景；模板和 smoke 配置不得作为默认策略。

## 安全边界

W1 明确保留只读边界：不得执行 provider publish、accepted latest switch、monitor write、broker/order/quick-trade、target position/weight、训练、真实 OpenAI smoke 或前端直连 OpenAI。`POST /api/tw-stock/agent/simple-chat` 仅作为后端只读解释路径，不等价于交易、调仓或数据刷新。

## Artifact Chain 摘要

`DataSource -> DataIngestionArtifact -> PriceStore/FeatureArtifact -> ModelAdapter -> ModelSignalArtifact/FullRankArtifact -> StrategyRule -> OrderIntentArtifact -> ReplayExecution -> ReplayResultArtifact -> ReadonlyStrategySnapshot -> Backend readonly API -> Frontend/Agent/PaperPortfolio`。

## Four Latest 摘要

- provider raw/latest：provider 原始抓取或缓存侧 latest。
- qlib accepted latest：Qlib 接受数据的 latest。
- readonly strategy snapshot latest：产品只读策略快照 latest。
- Agent DailyAgentPromptArtifact latest：Agent prompt artifact latest。

四者不得合并，也不得用其中一个 latest 证明另一个 latest 已同步。

## docs/tw_modular_contracts 全量分类表

| 文件 | W1 分类 | 处理方式 |
| --- | --- | --- |
| `AGENT_READONLY_CONTEXT_CONTRACT_CN.md` | W1 core contract | 已纳入 W1 分类；核心合同被蒸馏到概念/技能页，其他作为治理、runbook 或验收背景。 |
| `ANALYSIS_ARTIFACT_CONTRACT_CN.md` | W1 core contract | 已纳入 W1 分类；核心合同被蒸馏到概念/技能页，其他作为治理、runbook 或验收背景。 |
| `AUTO_UPDATE_ORCHESTRATOR_CONTRACT_CN.md` | W1 core contract | 已纳入 W1 分类；核心合同被蒸馏到概念/技能页，其他作为治理、runbook 或验收背景。 |
| `DAILY_ORCHESTRATOR_CONTRACT_CN.md` | W1 core contract | 已纳入 W1 分类；核心合同被蒸馏到概念/技能页，其他作为治理、runbook 或验收背景。 |
| `DATA_INGESTION_ARTIFACT_CONTRACT_CN.md` | W1 core contract | 已纳入 W1 分类；核心合同被蒸馏到概念/技能页，其他作为治理、runbook 或验收背景。 |
| `DATA_SOURCE_CONTRACT_CN.md` | W1 core contract | 已纳入 W1 分类；核心合同被蒸馏到概念/技能页，其他作为治理、runbook 或验收背景。 |
| `DEFAULT_CANDIDATE_DECISION_CONTRACT_CN.md` | W1 core contract | 已纳入 W1 分类；核心合同被蒸馏到概念/技能页，其他作为治理、runbook 或验收背景。 |
| `EXTENSIBLE_CONTRACT_CAPABILITY_DESIGN_CN.md` | supporting reference | 已纳入 W1 分类；核心合同被蒸馏到概念/技能页，其他作为治理、runbook 或验收背景。 |
| `FEATURE_ARTIFACT_CONTRACT_CN.md` | W1 core contract | 已纳入 W1 分类；核心合同被蒸馏到概念/技能页，其他作为治理、runbook 或验收背景。 |
| `FRONTEND_AGENT_PANEL_CONTRACT_CN.md` | W1 core contract | 已纳入 W1 分类；核心合同被蒸馏到概念/技能页，其他作为治理、runbook 或验收背景。 |
| `FRONTEND_READONLY_DISPLAY_CONTRACT_CN.md` | W1 core contract | 已纳入 W1 分类；核心合同被蒸馏到概念/技能页，其他作为治理、runbook 或验收背景。 |
| `FULL_RANK_CONTRACT_CN.md` | W1 core contract | 已纳入 W1 分类；核心合同被蒸馏到概念/技能页，其他作为治理、runbook 或验收背景。 |
| `MODEL_SIGNAL_CONTRACT_CN.md` | W1 core contract | 已纳入 W1 分类；核心合同被蒸馏到概念/技能页，其他作为治理、runbook 或验收背景。 |
| `MODEL_SIGNAL_EXTENSION_SCHEMA_CN.md` | W1 core contract | 已纳入 W1 分类；核心合同被蒸馏到概念/技能页，其他作为治理、runbook 或验收背景。 |
| `MODULAR_FOUNDATION_FINAL_ACCEPTANCE_CN.md` | review/acceptance reference | 已纳入 W1 分类；核心合同被蒸馏到概念/技能页，其他作为治理、runbook 或验收背景。 |
| `NEW_MODEL_AND_STRATEGY_DEVELOPER_GUIDE_CN.md` | developer/runbook reference | 已纳入 W1 分类；核心合同被蒸馏到概念/技能页，其他作为治理、runbook 或验收背景。 |
| `NEW_MODEL_REVIEWER_CHECKLIST_CN.md` | review/acceptance reference | 已纳入 W1 分类；核心合同被蒸馏到概念/技能页，其他作为治理、runbook 或验收背景。 |
| `NEW_STRATEGY_REVIEWER_CHECKLIST_CN.md` | review/acceptance reference | 已纳入 W1 分类；核心合同被蒸馏到概念/技能页，其他作为治理、runbook 或验收背景。 |
| `ORDER_INTENT_CONTRACT_CN.md` | W1 core contract | 已纳入 W1 分类；核心合同被蒸馏到概念/技能页，其他作为治理、runbook 或验收背景。 |
| `PHASED8_FINAL_ACCEPTANCE_REVIEW_SUGGESTION_CN.md` | review/acceptance reference | 已纳入 W1 分类；核心合同被蒸馏到概念/技能页，其他作为治理、runbook 或验收背景。 |
| `PHASEM3R_REVIEW_SUPPLEMENT_PHASEM4_FRONTEND_ACCEPTANCE_SUGGESTION_CN.md` | review/acceptance reference | 已纳入 W1 分类；核心合同被蒸馏到概念/技能页，其他作为治理、runbook 或验收背景。 |
| `PRICE_STORE_CONTRACT_CN.md` | W1 core contract | 已纳入 W1 分类；核心合同被蒸馏到概念/技能页，其他作为治理、runbook 或验收背景。 |
| `READONLY_REPLAY_WINDOW_PRODUCTIZATION_GUIDE_CN.md` | developer/runbook reference | 已纳入 W1 分类；核心合同被蒸馏到概念/技能页，其他作为治理、runbook 或验收背景。 |
| `READONLY_STRATEGY_SNAPSHOT_CONTRACT_CN.md` | W1 core contract | 已纳入 W1 分类；核心合同被蒸馏到概念/技能页，其他作为治理、runbook 或验收背景。 |
| `REPLAY_RESULT_CONTRACT_CN.md` | W1 core contract | 已纳入 W1 分类；核心合同被蒸馏到概念/技能页，其他作为治理、runbook 或验收背景。 |
| `RUN_REGISTRY_CONTRACT_CN.md` | W1 core contract | 已纳入 W1 分类；核心合同被蒸馏到概念/技能页，其他作为治理、runbook 或验收背景。 |
| `STRATEGY_DEPENDENCY_CONTRACT_CN.md` | W1 core contract | 已纳入 W1 分类；核心合同被蒸馏到概念/技能页，其他作为治理、runbook 或验收背景。 |
| `STRATEGY_RULE_CONTRACT_CN.md` | W1 core contract | 已纳入 W1 分类；核心合同被蒸馏到概念/技能页，其他作为治理、runbook 或验收背景。 |
| `TW_AGENT_DAILY_PROMPT_ARTIFACT_CONTRACT_CN.md` | W1 core contract | 已纳入 W1 分类；核心合同被蒸馏到概念/技能页，其他作为治理、runbook 或验收背景。 |
| `TW_AGENT_DAILY_PROMPT_OPENAI_REBUILD_DESIGN_CN.md` | supporting reference | 已纳入 W1 分类；核心合同被蒸馏到概念/技能页，其他作为治理、runbook 或验收背景。 |
| `TW_AGENT_DAILY_PROMPT_OPENAI_REBUILD_EXECUTION_AND_REVIEW_PLAN_CN.md` | review/acceptance reference | 已纳入 W1 分类；核心合同被蒸馏到概念/技能页，其他作为治理、runbook 或验收背景。 |
| `TW_CURRENT_PROJECT_DOC_ENTRY_AND_ARCHIVE_POLICY_CN.md` | governance/map reference | 已纳入 W1 分类；核心合同被蒸馏到概念/技能页，其他作为治理、runbook 或验收背景。 |
| `TW_CURRENT_STRATEGY_CONTEXT_API_FIELD_DICTIONARY_CN.md` | W1 core contract | 已纳入 W1 分类；核心合同被蒸馏到概念/技能页，其他作为治理、runbook 或验收背景。 |
| `TW_DAILY_AUTO_UPDATE_RUNBOOK_CN.md` | developer/runbook reference | 已纳入 W1 分类；核心合同被蒸馏到概念/技能页，其他作为治理、runbook 或验收背景。 |
| `TW_DEVELOPER_TEST_AND_EXPERIMENT_PLAYBOOK_CN.md` | developer/runbook reference | 已纳入 W1 分类；核心合同被蒸馏到概念/技能页，其他作为治理、runbook 或验收背景。 |
| `TW_MODULAR_PIPELINE_FUTURE_DEVELOPMENT_GUIDE_CN.md` | developer/runbook reference | 已纳入 W1 分类；核心合同被蒸馏到概念/技能页，其他作为治理、runbook 或验收背景。 |
| `TW_NEW_STRATEGY_ONBOARDING_TEMPLATE_CN.md` | developer/runbook reference | 已纳入 W1 分类；核心合同被蒸馏到概念/技能页，其他作为治理、runbook 或验收背景。 |
| `TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md` | governance/map reference | 已纳入 W1 分类；核心合同被蒸馏到概念/技能页，其他作为治理、runbook 或验收背景。 |
| `TW_PROJECT_MODULE_MAP_AND_FLOW_CN.md` | governance/map reference | 已纳入 W1 分类；核心合同被蒸馏到概念/技能页，其他作为治理、runbook 或验收背景。 |

## configs/strategy_dependencies 分类表

| 文件 | 分类 | W1 处理 |
| --- | --- | --- |
| `top50_exit_one_worst_sell.yaml` | current product default | 默认产品策略。 |
| `one_sell_one_buy_correct.yaml` | research-only candidate | 研究候选，不是当前默认。 |
| `one_sell_one_buy_buggy_e8r.yaml` | diagnostic-only | `not_valid_strategy_evidence=true`，不能作为有效策略证据。 |
| `original.yaml` | deprecated/historical | 历史规则。 |
| `top50_exit_all.yaml` | deprecated/historical research | 历史研究规则。 |
| `m2_strategy_dependency_template.yaml` | template only | M2 模板。 |
| `dummy_new_strategy_dependency_smoke.yaml` | smoke/template | smoke/template，不是默认候选。 |
| `sector_extension_analysis_smoke.yaml` | smoke/analysis | 分析 smoke，不是产品策略。 |

## .agents/skills/tw-stock-* references/scripts 读取决策表

| Skill | references/scripts 决策 | W1 用途 |
| --- | --- | --- |
| `tw-stock-agent-daily-prompt-maintenance/SKILL.md` | 无额外 reference/script 需要读取 | 用于 Agent route 与 DailyAgentPromptArtifact 维护边界。 |
| `tw-stock-data-freshness-diagnosis/SKILL.md` | 读取 `references/data-source-boundary.md`、`references/freshness-status-fields.md`；检查 `scripts/fetch_tw_stock_readonly_status.mjs` 头部，未执行 | 用于四类 latest 与只读状态诊断。 |
| `tw-stock-frontend-workbench-ux-review/SKILL.md` | 无额外 reference/script 需要读取 | 用于前端策略工作台 UX 页面。 |
| `tw-stock-modular-integration-regression/SKILL.md` | 无额外 reference/script 需要读取 | 用于集成回归 workflow。 |
| `tw-stock-new-model-onboarding/SKILL.md` | 无额外 reference/script 需要读取 | 用于新模型 onboarding workflow。 |
| `tw-stock-new-strategy-onboarding/SKILL.md` | 无额外 reference/script 需要读取 | 用于新策略 onboarding workflow。 |
| `tw-stock-readonly-e2e-acceptance/SKILL.md` | 读取 `references/readonly-boundary.md`、`references/acceptance-report-template.md`；检查 `scripts/summarize_e2e_artifacts.mjs` 头部，未执行 | 用于只读 E2E 验收 workflow。 |
| `tw-stock-research-context-analyst/SKILL.md` | 读取 `references/qlib-cross-analysis-semantics.md`、`references/research-report-template.md`；检查 `scripts/summarize_research_context.mjs` 头部，未执行 | 用于 current default 与研究语义边界。 |
| `tw-stock-safety-boundary-review/SKILL.md` | 读取 `references/forbidden-actions.md`、`references/network-audit-rules.md`；检查 `scripts/audit_tw_stock_diff.mjs` 头部，未执行 | 用于安全边界 review workflow。 |

## W0 Review M1/M2 修复说明

- M1：不再只依赖 W0 shortlist；本次枚举并分类当前 `docs/tw_modular_contracts/*.md` 全部 39 个文件。交接摘要中提到 48 个文件，但当前目录实际为 39 个，报告以本次文件系统结果为准。
- M2：逐一读取 9 个 `.agents/skills/tw-stock-*/SKILL.md`；对被引用的 `references/` 文件做必要读取；对 `scripts/` 做只读用途检查并记录未执行。

## 自检

- 已确认 W1 新增/更新 concept 与 skill 页面具备 frontmatter 中的 `title`、`sources`、`summary`、`lifecycle`、`tier` 字段。
- 已确认本次写入范围限制在 `docs/project_wiki/**`。
- 已确认 manifest 可由 JSON 解析，并包含 W1 source entry。
- 未执行会改变项目状态的测试、服务或数据/策略生成命令。

## 剩余问题

- W1 是人工蒸馏式 ingest，不是全文镜像；后续 W2 如果需要逐段证据，可继续扩充每个概念页的 provenance 和段落级引用。
- 由于 W1 work doc 限定来源，本报告没有吸收产品源码和运行态 artifact 的最新实际输出。

## 给 Reviewer 的问题

- 是否接受以当前文件系统枚举的 39 个 `docs/tw_modular_contracts/*.md` 作为 M1 全量范围，而不是交接摘要中的 48 个估计数？
- W2 是否优先进入源码/测试/运行态 artifact ingest，还是先对 W1 页进行 cross-link/dedup/lint 强化？
