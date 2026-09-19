---
title: Project Wiki Full Ingest Execution And Review Plan
category: skills
tags: [wiki, full-ingest, review]
sources: []
summary: 项目专属 wiki 全仓知识编译总路线的工作文档，作为项目 wiki 支线过程证据。
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

# 项目专属 Wiki 全仓知识编译支线执行与审查文档

生成日期：2026-06-20

## 1. 结论与路线选择

这是一个大工程，不建议由单个节点在一个回合里直接完成。

原因：本仓库不是一个小型源码仓库，而是包含源码、合同、执行/审查文档、实验报告、历史弯路、数据 artifact、前端构建产物、模型实验目录、缓存、日志、测试、skills 和多阶段路线总结的复合型项目。如果直接让 `wiki-ingest` 全仓扫描，会把大量低价值或过时内容编译进知识库，导致 wiki 变成“搜索垃圾场”，而不是“项目大脑”。

推荐方式：开一个独立支线，由执行者和审查者分阶段完成。

目标不是“把每个文件都塞进 wiki”，而是：

```text
把整个项目吃透，但只把仍然有架构价值、产品价值、合同价值、研发复用价值、调试价值、历史教训价值的知识编译进 docs/project_wiki。
```

## 2. 当前基础

已完成：

```text
obsidian-wiki 2026.6.6 已安装。
全局 config 已指向 docs/project_wiki。
35 个 wiki companion skills 已安装到 ~/.codex/skills 等 agent 目录。
docs/project_wiki 已有 seed vault。
manifest 已升级为官方 version=1 结构。
当前 seed vault 自检：sources=16，total_pages=15，missing_frontmatter=[]，broken_links=0。
```

当前 vault：

```text
docs/project_wiki
```

后续所有写入必须只写这个 vault，除非统筹另行批准。

## 3. 总原则

### 3.1 编译，不是搬运

Wiki 页面不是原文摘要堆叠，而是编译后的知识单元。执行者必须把多个来源合并为稳定页面，例如：

```text
模块化 artifact 链路
只读安全边界
日更数据链路
Agent simple-chat 路线
前端策略工作台路线
新模型接入流程
新策略接入流程
数据新鲜度诊断流程
回放与模拟账户边界
历史弯路与弃用路线
```

不要为每个 phase report 建一个页面。phase report 是 source，不是天然 wiki page。

### 3.2 当前事实优先，历史事实降权

当前仍有效的事实写入 core/supporting 页面。

历史弯路只进入：

```text
synthesis/historical-lessons.md
references/superseded-routes-*.md
```

并且必须标记：

```text
lifecycle: archived 或 draft
summary 中说明 superseded / historical
正文明确“历史路线，不代表当前默认路径”
```

### 3.3 不吃无意义内容

默认不 ingest：

```text
.git/
node_modules/
frontend/node_modules/
frontend/dist/
__pycache__/
.pytest_cache/
logs/
backend/logs/
tmp/
mlruns/
qlib_pipeline/mlruns/
home/
*.bin
*.pkl
*.parquet
*.sqlite
*.db
大体量 CSV 原始数据
图片截图产物，除非是前端验收关键证据
PDF 论文全文，除非进入研究参考专项
```

默认只做 manifest/source reference，不把大数据原文编译进 wiki：

```text
data_tw/artifacts
data_tw/experiments
qlib_pipeline/data_tw
```

这些目录只抽取 artifact schema、manifest 结构、代表性真实样本和路径语义。

### 3.4 不改产品状态

本支线禁止：

```text
真实数据拉取
provider refresh / publish
accepted latest switch
monitor config / scan / alerts 写入
broker / quick-trade / order
target_position / target_weight 写入
OpenAI key 读取
真实 OpenAI smoke
生产 latest/default 切换
训练模型或生成策略 artifact
```

本支线只读仓库源文件，并写 `docs/project_wiki`。

## 4. 信息分层：哪些内容应该进入 Wiki

### Tier A：必须编译为核心页面

```text
docs/tw_modular_contracts/
configs/*.yaml 中的产品 registry / replay policy / strategy dependency / data source registry
.agents/skills/tw-stock-*/SKILL.md
backend/app/services 与 backend/app/routes 中的 Agent、daily prompt、readonly API 路线
frontend/src/views/tw-stock-monitor 与相关 API 封装
scripts 中当前产品化 validator、builder、daily orchestrator、readiness、snapshot、agent prompt 脚本
tests/unit 与 frontend/tests 中体现合同和边界的测试
```

目标页面类型：

```text
concepts/
skills/
projects/taiwan-stock-quant-platform/concepts/
projects/taiwan-stock-quant-platform/skills/
```

### Tier B：选择性编译为 supporting 页面

```text
docs/tw_new_model_strategy_pre_rnd/
docs/tw_agent_daily_prompt_rebuild/
docs/tw_modular_daily_update_productization/
docs/tw_skills_maintenance/
backend/tests/
frontend/tests/
configs/strategy_dependencies/
configs/model_onboarding_templates/
crawler/scrapling_handoff/README/CODEX_GUIDE/DATA_CONTRACT/SOURCE_PLAYBOOK
qlib_pipeline/qlib_extensions
qlib_pipeline/configs
qlib_pipeline/examples/tw 中仍可复用的研究/诊断脚本
```

目标：抽取当前稳定路线、验收结论、后续入口和可复用调试方法。

### Tier C：历史和弯路，只抽教训

```text
docs/tw_ltr_* 历史实验路线
docs/tw_decision_model* 历史决策模型路线
docs/tw_orthogonal_* 历史实验路线
docs/archive/
旧 phase acceptance / execution / review 文档
早期 agent / frontend / product adaptation 报告
```

处理方式：

```text
不逐篇建 reference。
只做 synthesis/historical-lessons.md。
只记录“为什么被替代”“当前替代方案是什么”“以后不要重复什么”。
```

### Tier D：默认不进入 wiki

```text
原始行情文件
模型二进制
缓存
日志
构建产物
node_modules
临时截图目录
测试运行输出
大规模 mlruns
```

## 5. 目标 Wiki 结构

执行完成后，建议至少形成以下结构：

```text
docs/project_wiki/
  index.md
  hot.md
  log.md
  .manifest.json
  _meta/taxonomy.md
  projects/taiwan-stock-quant-platform/taiwan-stock-quant-platform.md
  concepts/
    modular-artifact-chain.md
    readonly-safety-boundary.md
    daily-update-data-flow.md
    product-artifact-registry.md
    current-default-model-and-strategy.md
    agent-daily-prompt-route.md
    frontend-strategy-workbench.md
    paper-portfolio-simulation.md
    data-freshness-and-latest-pointers.md
    qlib-ltr-model-stack.md
    execution-price-readiness.md
  skills/
    new-model-onboarding-workflow.md
    new-strategy-onboarding-workflow.md
    readonly-e2e-acceptance-workflow.md
    frontend-ux-review-workflow.md
    data-freshness-diagnosis-workflow.md
    safety-boundary-review-workflow.md
    modular-integration-regression-workflow.md
  references/
    real-sample-20260618.md
    pre-rnd-readiness-final-handoff.md
    agent-daily-prompt-rebuild-final.md
    ui2-frontend-final.md
    skills-maintenance-final.md
  synthesis/
    historical-lessons.md
    current-mainline-vs-superseded-routes.md
    project-risk-map.md
```

页面不必一次全部完成，但每个阶段必须推进一组稳定页面。

## 6. 阶段拆分

### Phase W0：范围地图和过滤规则

执行者要做：

1. 读取本工作文档、`llm-wiki`、`wiki-status`、`wiki-ingest`、`wiki-lint`、`wiki-query` skill。
2. 用只读命令生成仓库目录地图、候选 source 清单、排除清单。
3. 输出 `docs/project_wiki/FULL_INGEST_PHASEW0_INVENTORY_REPORT_CN.md`。
4. 报告必须包含：
   - Tier A/B/C/D 清单；
   - 每类预计 ingest 文件数；
   - 明确 ignore patterns；
   - 首批 ingest source list；
   - 风险：大文件、重复报告、历史路线、敏感配置、二进制/数据 artifact。

审查者要审查：

1. 是否误把数据/缓存/构建产物列入 ingest。
2. 是否漏掉当前主线关键目录。
3. 是否把历史弯路和当前事实混在一起。
4. 是否严格只写 wiki，不改产品代码。

Phase W0 通过后，才能进入 W1。

### Phase W1：核心架构与合同编译

执行者要做：

1. 以 `docs/tw_modular_contracts/`、`configs/`、`.agents/skills/tw-stock-*` 为主。
2. 更新或创建核心 concepts/skills 页面。
3. 更新 `index.md`、`hot.md`、`.manifest.json`、`log.md`。
4. 不要逐篇复制合同，而是合并成可导航知识页。
5. 输出 `docs/project_wiki/FULL_INGEST_PHASEW1_CORE_CONTRACTS_REPORT_CN.md`。

审查者要审查：

1. 当前产品默认路径是否准确。
2. registry、contract、skill 之间是否自洽。
3. 是否有断链、缺 frontmatter、缺 summary、缺 sources。
4. 是否保留 readonly 安全边界。

### Phase W2：产品化路线、Agent、前端、日更链路编译

执行者要做：

1. 编译以下支线：
   - `docs/tw_agent_daily_prompt_rebuild/`
   - `docs/tw_modular_daily_update_productization/`
   - `docs/tw_new_model_strategy_pre_rnd/`
   - `docs/tw_skills_maintenance/`
2. 把最终结论写进 references/supporting 页面。
3. 把仍有效路线合并进 core concepts。
4. 把失败/修复过程抽成 historical lessons，不作为当前事实。
5. 输出 `docs/project_wiki/FULL_INGEST_PHASEW2_PRODUCT_ROUTES_REPORT_CN.md`。

审查者要审查：

1. 是否把 phase 中失败过的中间状态误写成当前状态。
2. 是否把 accepted-with-conditions 写成 unconditional accepted。
3. Agent 是否仍保持 DailyAgentPromptArtifact + backend simple-chat 路线。
4. 前端是否仍是 readonly strategy workbench，不含 broker/quick-trade/order。

### Phase W3：源码、脚本、测试、配置编译

执行者要做：

1. 只读分析源码，不运行服务、不训练模型、不触发日更。
2. 重点抽取：
   - backend route/service 对应哪些 wiki concepts；
   - frontend workbench 组件和 API 的职责；
   - scripts 中哪些是当前 product path，哪些是 diagnostic/legacy；
   - tests 如何守住合同和安全边界。
3. 建立源码到知识页的关系，而不是逐文件建 reference。
4. 输出 `docs/project_wiki/FULL_INGEST_PHASEW3_CODE_MAP_REPORT_CN.md`。

审查者要审查：

1. 是否误读 legacy 脚本为当前入口。
2. 是否把测试 fixture 当真实生产数据。
3. 是否遗漏 validator、golden sample、readonly E2E。
4. 是否有敏感配置泄漏到 wiki。

### Phase W4：历史路线和弯路归档

执行者要做：

1. 选择性读取历史实验目录和 archive。
2. 只抽“教训”和“为什么当前路线替代它”。
3. 写入：
   - `synthesis/historical-lessons.md`
   - `synthesis/current-mainline-vs-superseded-routes.md`
   - `synthesis/project-risk-map.md`
4. 输出 `docs/project_wiki/FULL_INGEST_PHASEW4_HISTORY_LESSONS_REPORT_CN.md`。

审查者要审查：

1. 历史路线是否明确标注 historical/superseded。
2. 是否把旧的 agent/tool/broker/monitor/provider publish 思路带回当前主线。
3. 是否把旧实验收益或 smoke 误写为当前证据。

### Phase W5：Wiki 健康审查和收尾

执行者要做：

1. 执行或手动等价完成 wiki health audit：
   - manifest version=1；
   - no broken wikilinks；
   - no missing frontmatter；
   - index 覆盖核心页面；
   - orphan 页面可解释；
   - stale/historical 页面标注清楚；
   - hot.md 更新；
   - log.md 可解析。
2. 输出 `docs/project_wiki/FULL_INGEST_PHASEW5_FINAL_SUMMARY_CN.md`。

审查者要审查：

1. 是否可作为项目专属知识库收尾。
2. 是否能回答：当前主线是什么、怎么新增模型、怎么新增策略、Agent 怎么回答、前端展示什么、哪些不能做。
3. 是否需要继续二轮 ingest。
4. 输出 `docs/project_wiki/FULL_INGEST_PHASEW5_FINAL_REVIEW_CN.md`。

## 7. 执行者每阶段工作报告要求

每阶段结束必须提交报告，格式：

```markdown
# Project Wiki Full Ingest Phase Wx 执行报告

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

## 8. 审查者每阶段审查报告要求

每阶段审查必须提交报告，格式：

```markdown
# Project Wiki Full Ingest Phase Wx 审查报告

## 1. 审查结论
## 2. Critical Findings
## 3. High Findings
## 4. Medium Findings
## 5. Low Findings
## 6. Wiki 结构与链接审查
## 7. 当前事实 / 历史事实边界审查
## 8. 安全边界审查
## 9. 是否允许进入下一阶段
## 10. 下一阶段工作文档或修复要求
```

如果出现以下情况，审查者必须阻塞：

```text
把历史失败路线写成当前路线。
把 readonly candidate 写成交易建议。
把 target_position / target_weight 写入 wiki 作为允许输出。
把 provider publish / accepted latest switch 写成可默认执行。
把动态 payload 或 fixture 当生产 artifact。
把 OpenAI key、密码、token、真实账户信息写入 wiki。
manifest 缺 hash/mtime/size 或 source key 不是绝对路径。
大量断链或缺 frontmatter。
```

## 9. 建议第一条给执行者的命令

```text
你是执行者。请启动 Project Wiki Full Ingest 支线 Phase W0，只做范围地图和过滤规则，不执行大规模 ingest，不改产品代码，不运行服务，不触发日更，不训练模型。必须读取 docs/project_wiki/PROJECT_WIKI_FULL_INGEST_EXECUTION_AND_REVIEW_PLAN_CN.md、/home/chuliyang/.codex/skills/llm-wiki/SKILL.md、/home/chuliyang/.codex/skills/wiki-status/SKILL.md、/home/chuliyang/.codex/skills/wiki-ingest/SKILL.md、/home/chuliyang/.codex/skills/wiki-lint/SKILL.md。输出 docs/project_wiki/FULL_INGEST_PHASEW0_INVENTORY_REPORT_CN.md，列出 Tier A/B/C/D source 范围、ignore patterns、首批 ingest source list、风险和下一阶段建议。严禁读取 OpenAI key、触发真实数据、provider publish、accepted latest、monitor、broker/order、target_position/target_weight 或 default switch。
```

## 10. 建议第一条给审查者的命令

```text
你是审查者。请审查执行者的 docs/project_wiki/FULL_INGEST_PHASEW0_INVENTORY_REPORT_CN.md，并严格对照 docs/project_wiki/PROJECT_WIKI_FULL_INGEST_EXECUTION_AND_REVIEW_PLAN_CN.md。重点判断 source 范围是否覆盖整个项目的关键知识、ignore patterns 是否排除了无意义/高风险内容、历史弯路是否被降权、当前主线是否没有遗漏。输出 docs/project_wiki/FULL_INGEST_PHASEW0_INVENTORY_REVIEW_CN.md，并明确是否允许进入 W1；如不允许，给出修复清单。
```

## 11. 统筹决策建议

建议开执行者和审查者节点。

不建议当前由单节点直接完成全仓 ingest，因为：

```text
全仓源太多，且历史路线复杂。
需要先判定 current vs superseded。
需要人工审查避免 wiki 污染。
需要阶段性 lint 和 manifest 校验。
需要长期维护，而不是一次性生成。
```

当前我已经完成 seed vault 和官方工具配置；下一步应由执行者先做 W0 范围地图。
