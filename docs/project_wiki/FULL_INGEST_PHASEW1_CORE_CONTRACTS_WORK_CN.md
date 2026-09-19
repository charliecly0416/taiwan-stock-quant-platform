---
title: Phasew1 Core Contracts WORK
category: skills
tags: [wiki, full-ingest, w1, work]
sources: []
summary: 核心合同、配置和 skills 编译的工作文档，作为项目 wiki 支线过程证据。
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

# Project Wiki Full Ingest Phase W1 执行工作文档

生成日期：2026-06-20

## 1. 阶段目标

Phase W1 的目标是编译核心架构与合同知识，不是逐文件摘要。

执行者必须围绕以下主线更新或创建 wiki 页面：

- 模块化 artifact 链路
- 只读安全边界
- product artifact registry
- 当前默认模型与策略
- Agent DailyAgentPromptArtifact / simple-chat 路线
- frontend strategy workbench 路线
- 数据新鲜度与 latest pointer 边界
- 新模型 onboarding workflow
- 新策略 onboarding workflow
- readonly E2E / frontend UX / freshness / safety / integration regression workflow

本阶段完成后必须输出：

- `docs/project_wiki/FULL_INGEST_PHASEW1_CORE_CONTRACTS_REPORT_CN.md`

## 2. 必读前置文档

执行者开始 W1 前必须读取：

- `docs/project_wiki/PROJECT_WIKI_FULL_INGEST_EXECUTION_AND_REVIEW_PLAN_CN.md`
- `docs/project_wiki/FULL_INGEST_PHASEW0_INVENTORY_REPORT_CN.md`
- `docs/project_wiki/FULL_INGEST_PHASEW0_INVENTORY_REVIEW_CN.md`
- `/home/chuliyang/.codex/skills/llm-wiki/SKILL.md`
- `/home/chuliyang/.codex/skills/wiki-ingest/SKILL.md`
- `/home/chuliyang/.codex/skills/wiki-lint/SKILL.md`
- `/home/chuliyang/.codex/skills/wiki-status/SKILL.md`

W1 必须显式吸收 W0 审查报告中的 M1/M2 修复要求。

## 3. 允许写入范围

只允许写入：

- `docs/project_wiki/**`

允许更新：

- `docs/project_wiki/.manifest.json`
- `docs/project_wiki/index.md`
- `docs/project_wiki/hot.md`
- `docs/project_wiki/log.md`
- `docs/project_wiki/concepts/*.md`
- `docs/project_wiki/skills/*.md`
- `docs/project_wiki/projects/taiwan-stock-quant-platform/**/*.md`
- `docs/project_wiki/references/*.md`，仅限确有必要的 supporting reference
- `docs/project_wiki/FULL_INGEST_PHASEW1_CORE_CONTRACTS_REPORT_CN.md`

禁止修改产品源码、配置、脚本、测试、数据 artifact 和任何 `docs/project_wiki` 以外的文件。

## 4. 禁止事项

本阶段禁止：

- 真实数据拉取
- provider refresh / publish
- accepted latest switch
- monitor config / scan / alerts 写入
- broker / quick-trade / order 调用
- `target_position` / `target_weight` 写入
- 读取 OpenAI key、密码、token、真实账户信息
- 真实 OpenAI smoke
- 生产 latest/default 切换
- 训练模型
- 生成策略 artifact
- 发布 readonly snapshot
- 运行服务
- 把 readonly candidate 或 Agent 回答写成交易建议

W1 是只读源文件分析 + 写 wiki，不做任何产品状态变更。

## 5. W1 Source 范围

### 5.1 主源

W1 主源限定为：

- `docs/tw_modular_contracts/`
- `configs/`
- `.agents/skills/tw-stock-*`

不要扩展到历史 phase report，不要读取大规模数据目录，不要进入 W2/W3/W4 范围。

### 5.2 `docs/tw_modular_contracts/` 开工分流要求

执行者不能直接照抄 W0 首批 source list。W1 开始时必须先读取或枚举 `docs/tw_modular_contracts/` 全量文件，并在 W1 报告中给出分流表：

- 必须编译
- 支撑读取
- 历史/验收参考
- 排除

至少以下文件必须被显式判定，不得静默遗漏：

- `ANALYSIS_ARTIFACT_CONTRACT_CN.md`
- `DATA_INGESTION_ARTIFACT_CONTRACT_CN.md`
- `DEFAULT_CANDIDATE_DECISION_CONTRACT_CN.md`
- `EXTENSIBLE_CONTRACT_CAPABILITY_DESIGN_CN.md`
- `FULL_RANK_CONTRACT_CN.md`
- `MODEL_SIGNAL_EXTENSION_SCHEMA_CN.md`
- `PRICE_STORE_CONTRACT_CN.md`
- `READONLY_REPLAY_WINDOW_PRODUCTIZATION_GUIDE_CN.md`
- `NEW_MODEL_REVIEWER_CHECKLIST_CN.md`
- `NEW_STRATEGY_REVIEWER_CHECKLIST_CN.md`
- `TW_DAILY_AUTO_UPDATE_RUNBOOK_CN.md`
- `TW_DEVELOPER_TEST_AND_EXPERIMENT_PLAYBOOK_CN.md`
- `TW_NEW_STRATEGY_ONBOARDING_TEMPLATE_CN.md`
- `docs/tw_modular_contracts/templates/*.md`

### 5.3 `configs/` 必读项

以下配置必须进入 W1：

- `configs/tw_product_artifact_registry.yaml`
- `configs/tw_modular_registry.yaml`
- `configs/data_source_registry.yaml`
- `configs/price_store_registry.yaml`
- `configs/tw_replay_window_policy.yaml`
- `configs/tw_modular_replay_matrix.yaml`
- `configs/feature_registry.yaml`
- `configs/model_onboarding_templates/model_signal_m2_template.yaml`
- `configs/strategy_dependencies/m2_strategy_dependency_template.yaml`
- `configs/strategy_dependencies/one_sell_one_buy_correct.yaml`
- `configs/strategy_dependencies/top50_exit_one_worst_sell.yaml`

以下 strategy dependency 文件必须显式分类为当前默认、模板/示例、smoke、buggy、历史或不纳入：

- `configs/strategy_dependencies/dummy_new_strategy_dependency_smoke.yaml`
- `configs/strategy_dependencies/one_sell_one_buy_buggy_e8r.yaml`
- `configs/strategy_dependencies/original.yaml`
- `configs/strategy_dependencies/sector_extension_analysis_smoke.yaml`
- `configs/strategy_dependencies/top50_exit_all.yaml`

### 5.4 `.agents/skills/tw-stock-*` 必读项

必须读取每个：

- `.agents/skills/tw-stock-*/SKILL.md`

如果 `SKILL.md` 明确引用相对 references/scripts，必须按引用读取必要文件，并在 W1 报告中记录。若没有引用，记录“无额外 references/scripts”。

## 6. 目标 Wiki 页面

W1 应优先更新已有页面，并按需创建缺失页面。

优先页面：

- `concepts/modular-artifact-chain.md`
- `concepts/readonly-safety-boundary.md`
- `concepts/product-artifact-registry.md`
- `concepts/current-default-model-and-strategy.md`
- `concepts/agent-daily-prompt-route.md`
- `concepts/frontend-strategy-workbench.md`
- `concepts/data-freshness-and-latest-pointers.md`
- `skills/new-model-onboarding-workflow.md`
- `skills/new-strategy-onboarding-workflow.md`
- `skills/readonly-e2e-acceptance-workflow.md`
- `skills/frontend-ux-review-workflow.md`
- `skills/data-freshness-diagnosis-workflow.md`
- `skills/safety-boundary-review-workflow.md`
- `skills/modular-integration-regression-workflow.md`

可按需要更新：

- `projects/taiwan-stock-quant-platform/taiwan-stock-quant-platform.md`

不要为每份合同单独创建 reference 页面。只有当某个源文件本身需要作为稳定支持材料被长期引用时，才创建 `references/` 页面。

## 7. 页面质量要求

每个新增或更新的正式 wiki 页面必须包含：

- YAML frontmatter
- `title`
- `category`
- `tags`
- `sources`
- `summary`
- `base_confidence`
- `lifecycle`
- `lifecycle_changed`
- `tier`
- 正文中的 Obsidian wikilinks
- `## Sources` section

原则：

- 当前事实优先。
- 历史事实不得污染当前默认路径。
- inferred claim 必须标记 `^[inferred]`。
- ambiguous claim 必须标记 `^[ambiguous]`。
- readonly 安全边界必须显式保留。
- 不写交易建议。

## 8. Manifest / Index / Hot / Log 要求

W1 只要新增或更新正式 wiki 页面，就必须同步更新：

- `.manifest.json`
- `index.md`
- `hot.md`
- `log.md`

manifest 要求：

- `version` 保持 `1`
- source key 必须是绝对路径
- 每个 source entry 必须包含 `content_hash`
- 必须包含 `modified_at`
- 必须包含 `size_bytes`
- 必须包含 `pages_created`
- 必须包含 `pages_updated`
- `pages_created` / `pages_updated` 使用 vault-relative 路径

`log.md` 必须追加可解析记录，说明 W1 ingest/compile 操作。

## 9. W1 报告格式

执行者最终必须输出：

```markdown
# Project Wiki Full Ingest Phase W1 执行报告

## 1. 本阶段结论
## 2. 读取的 source 范围
## 3. 明确排除的 source 范围
## 4. 新增 / 更新的 wiki 页面
## 5. manifest / index / hot / log 更新
## 6. 当前事实与历史事实边界
## 7. 安全边界确认
## 8. 自检结果
## 9. 遗留问题
## 10. 请求审查者审查的问题
```

报告还必须额外包含：

- `docs/tw_modular_contracts/` 全量分流表
- `configs/strategy_dependencies/*.yaml` 分类表
- `.agents/skills/tw-stock-*` references/scripts 读取判定表
- W0 审查 M1/M2 的修复说明

## 10. W1 通过门槛

审查者将在 W1 后检查：

- 当前产品默认路径是否准确。
- registry、contract、skill 是否自洽。
- 是否有断链。
- 是否缺 frontmatter。
- 是否缺 summary。
- 是否缺 sources。
- manifest 是否为 version=1 且 source key 为绝对路径。
- manifest 是否包含 hash/mtime/size/pages_created/pages_updated。
- readonly 安全边界是否保留。
- 是否把 broker/order/quick-trade/target 写入误写为允许能力。
- 是否把历史或 smoke/buggy strategy dependency 写成当前默认。

若出现计划文档列出的阻塞项，W1 不得通过。

## 11. 给执行者的启动命令

```text
你是执行者。请启动 Project Wiki Full Ingest 支线 Phase W1，只做核心架构与合同编译。必须读取 docs/project_wiki/PROJECT_WIKI_FULL_INGEST_EXECUTION_AND_REVIEW_PLAN_CN.md、docs/project_wiki/FULL_INGEST_PHASEW0_INVENTORY_REPORT_CN.md、docs/project_wiki/FULL_INGEST_PHASEW0_INVENTORY_REVIEW_CN.md、docs/project_wiki/FULL_INGEST_PHASEW1_CORE_CONTRACTS_WORK_CN.md、/home/chuliyang/.codex/skills/llm-wiki/SKILL.md、/home/chuliyang/.codex/skills/wiki-ingest/SKILL.md、/home/chuliyang/.codex/skills/wiki-lint/SKILL.md、/home/chuliyang/.codex/skills/wiki-status/SKILL.md。主源限定为 docs/tw_modular_contracts/、configs/、.agents/skills/tw-stock-*。必须先完成 docs/tw_modular_contracts/ 全量分流、strategy dependency 分类、tw-stock skill references/scripts 判定，再编译 wiki 页面。只允许写 docs/project_wiki。必须更新 .manifest.json、index.md、hot.md、log.md，并输出 docs/project_wiki/FULL_INGEST_PHASEW1_CORE_CONTRACTS_REPORT_CN.md。严禁读取 OpenAI key、触发真实数据、provider publish、accepted latest、monitor、broker/order、target_position/target_weight、训练模型、生成策略 artifact、运行服务或改产品代码。
```
