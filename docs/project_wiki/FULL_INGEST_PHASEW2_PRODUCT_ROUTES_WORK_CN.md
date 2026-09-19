---
title: Phasew2 Product Routes WORK
category: skills
tags: [wiki, full-ingest, w2, work]
sources: []
summary: 产品路线、Agent、前端和日更支线编译的工作文档，作为项目 wiki 支线过程证据。
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

# Project Wiki Full Ingest Phase W2 执行工作文档

生成日期：2026-06-20

## 1. 阶段目标

Phase W2 的目标是编译产品化路线、Agent、前端和日更链路的最终稳定知识。

W2 不是重做 W1 的核心合同判断，也不是逐篇复制 phase report。执行者必须从产品路线文档中抽取最终结论、验收状态、当前有效入口和仍可复用的调试/维护方法，并把失败过程、历史修复过程和 accepted-with-conditions 的限制条件正确降权。

本阶段完成后必须输出：

- `docs/project_wiki/FULL_INGEST_PHASEW2_PRODUCT_ROUTES_REPORT_CN.md`

## 2. 必读前置文档

执行者开始 W2 前必须读取：

- `docs/project_wiki/PROJECT_WIKI_FULL_INGEST_EXECUTION_AND_REVIEW_PLAN_CN.md`
- `docs/project_wiki/FULL_INGEST_PHASEW1_CORE_CONTRACTS_WORK_CN.md`
- `docs/project_wiki/FULL_INGEST_PHASEW1_CORE_CONTRACTS_REPORT_CN.md`
- `docs/project_wiki/FULL_INGEST_PHASEW1_CORE_CONTRACTS_REVIEW_CN.md`
- `docs/project_wiki/FULL_INGEST_PHASEW1_CORE_CONTRACTS_FOLLOWUP_CN.md`
- `docs/project_wiki/FULL_INGEST_PHASEW1_CORE_CONTRACTS_FOLLOWUP_REVIEW_CN.md`
- `/home/chuliyang/.codex/skills/llm-wiki/SKILL.md`
- `/home/chuliyang/.codex/skills/wiki-ingest/SKILL.md`
- `/home/chuliyang/.codex/skills/wiki-lint/SKILL.md`
- `/home/chuliyang/.codex/skills/wiki-status/SKILL.md`

W2 必须以 W1 建立的当前默认模型、默认策略、registry、Agent simple-chat 路线、frontend strategy workbench 路线和 readonly safety boundary 为基准，不得重新解释或覆盖。

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
- `docs/project_wiki/references/*.md`
- `docs/project_wiki/synthesis/*.md`
- `docs/project_wiki/projects/taiwan-stock-quant-platform/**/*.md`
- `docs/project_wiki/FULL_INGEST_PHASEW2_PRODUCT_ROUTES_REPORT_CN.md`

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

W2 只读产品路线文档，并写 `docs/project_wiki`。

## 5. W2 Source 范围

### 5.1 主源目录

W2 主源限定为：

- `docs/tw_agent_daily_prompt_rebuild/`
- `docs/tw_modular_daily_update_productization/`
- `docs/tw_new_model_strategy_pre_rnd/`
- `docs/tw_skills_maintenance/`

### 5.2 读取策略

执行者必须先按目录建立文件清单，并对每个目录按以下类别分流：

- final summary / final handoff / final review
- execution report
- review report
- work plan / optimization plan
- accepted-with-conditions
- failed/intermediate/fix history
- historical/superseded
- not ingested

W2 页面只写最终稳定事实。中间失败状态、修复过程、临时 workaround、旧路线和 accepted-with-conditions 的限制必须明确标注，不得写成当前默认事实。

## 6. 必须回答的产品路线问题

W2 编译后，wiki 至少应能回答：

- Agent 当前是不是 DailyAgentPromptArtifact + backend simple-chat 路线？
- 前端当前是不是 readonly strategy workbench？
- Agent simple-chat 的允许边界和 forbidden intent 是什么？
- DailyAgentPromptArtifact 的 builder / validator / prompt context / citations / checksum 边界是什么？
- 日更链路哪些是 current route，哪些只是历史 phase 修复？
- UI2 / replay / candidates / paper portfolio / Agent fusion 的最终验收状态是什么？
- `ACCEPTED_WITH_CONDITIONS` 的条件是什么，哪些不能被写成 unconditional accepted？
- skills maintenance 最终保留哪些 tw-stock skill，各自服务哪条 workflow？

## 7. 目标 Wiki 页面

W2 应优先更新 W1 已有核心页面：

- `concepts/agent-daily-prompt-route.md`
- `concepts/frontend-strategy-workbench.md`
- `concepts/daily-update-data-flow.md`
- `concepts/data-freshness-and-latest-pointers.md`
- `concepts/readonly-safety-boundary.md`
- `concepts/product-artifact-registry.md`
- `skills/readonly-e2e-acceptance-workflow.md`
- `skills/frontend-ux-review-workflow.md`
- `skills/data-freshness-diagnosis-workflow.md`
- `skills/safety-boundary-review-workflow.md`
- `skills/modular-integration-regression-workflow.md`

W2 可按需要新增 supporting reference 页面，建议优先考虑：

- `references/agent-daily-prompt-rebuild-final.md`
- `references/ui2-frontend-final.md`
- `references/skills-maintenance-final.md`
- `references/pre-rnd-readiness-final-handoff.md`，如已有则更新

W2 可按需要新增或更新 synthesis 页面：

- `synthesis/current-mainline-vs-superseded-routes.md`
- `synthesis/project-risk-map.md`

不要为每个 phase report 创建 reference 页面。

## 8. 当前事实边界

W2 必须保留以下 W1 事实：

- product profile：`strict_e4_yz_product`
- base model：`e4_frozen_qlib_2018_2022`
- treatment model：`e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025`
- display alias：`e4_frozen_qlib_2023_2025_ltr`
- default strategy：`top50_exit_one_worst_sell`
- candidate boundary：`qlib_top50`
- ranking：`ltr_rerank_within_qlib_top50`
- execution price mode：`next_open`
- Agent route：DailyAgentPromptArtifact -> backend simple-chat -> frontend readonly explanation
- Frontend route：`/tw-stock-monitor` readonly strategy workbench

如果 W2 source 中出现不同说法，必须作为 historical/superseded/intermediate 或 ambiguous 处理，不能直接覆盖 W1 当前事实。

## 9. Manifest / Index / Hot / Log 要求

W2 只要新增或更新正式 wiki 页面，就必须同步更新：

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

W2 开工时必须顺手修复 W1 follow-up review 发现的 Low issue：`index.md` 中 `FULL_INGEST_PHASEW1_CORE_CONTRACTS_FOLLOWUP_CN` 重复条目应合并为一条。

## 10. W2 报告格式

执行者最终必须输出：

```markdown
# Project Wiki Full Ingest Phase W2 执行报告

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

- 四个 W2 主源目录的文件分流表。
- W1 follow-up review Low issue 的修复说明。
- Agent route 最终结论表。
- Frontend/UI2 route 最终结论表。
- accepted-with-conditions 条件表。
- superseded/intermediate 路线表。

## 11. W2 通过门槛

审查者将在 W2 后检查：

- 是否把 phase 中失败过的中间状态误写成当前状态。
- 是否把 accepted-with-conditions 写成 unconditional accepted。
- Agent 是否仍保持 DailyAgentPromptArtifact + backend simple-chat 路线。
- 前端是否仍是 readonly strategy workbench，不含 broker/quick-trade/order。
- 是否把产品路线 supporting docs 合并进 core concepts，而不是逐篇搬运。
- 是否更新 manifest/index/hot/log。
- 是否保留 W1 当前默认模型、策略和 latest 边界。

若出现总计划列出的阻塞项，W2 不得通过。

## 12. 给执行者的启动命令

```text
你是执行者。请启动 Project Wiki Full Ingest 支线 Phase W2，只读编译产品化路线、Agent、前端和日更链路。必须读取 docs/project_wiki/PROJECT_WIKI_FULL_INGEST_EXECUTION_AND_REVIEW_PLAN_CN.md、docs/project_wiki/FULL_INGEST_PHASEW1_CORE_CONTRACTS_REPORT_CN.md、docs/project_wiki/FULL_INGEST_PHASEW1_CORE_CONTRACTS_REVIEW_CN.md、docs/project_wiki/FULL_INGEST_PHASEW1_CORE_CONTRACTS_FOLLOWUP_CN.md、docs/project_wiki/FULL_INGEST_PHASEW1_CORE_CONTRACTS_FOLLOWUP_REVIEW_CN.md、docs/project_wiki/FULL_INGEST_PHASEW2_PRODUCT_ROUTES_WORK_CN.md、/home/chuliyang/.codex/skills/llm-wiki/SKILL.md、/home/chuliyang/.codex/skills/wiki-ingest/SKILL.md、/home/chuliyang/.codex/skills/wiki-lint/SKILL.md、/home/chuliyang/.codex/skills/wiki-status/SKILL.md。主源限定为 docs/tw_agent_daily_prompt_rebuild/、docs/tw_modular_daily_update_productization/、docs/tw_new_model_strategy_pre_rnd/、docs/tw_skills_maintenance/。必须先做四个目录的文件分流，最终结论优先，失败/中间态/accepted-with-conditions 必须降权。只允许写 docs/project_wiki。必须修复 index.md 中 W1 follow-up 重复条目，更新 .manifest.json、index.md、hot.md、log.md，并输出 docs/project_wiki/FULL_INGEST_PHASEW2_PRODUCT_ROUTES_REPORT_CN.md。严禁读取 OpenAI key、触发真实数据、provider publish、accepted latest、monitor、broker/order、target_position/target_weight、训练模型、生成策略 artifact、运行服务或改产品代码。
```
