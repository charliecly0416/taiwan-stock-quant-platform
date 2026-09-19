---
title: Phasew5 Final Summary WORK
category: skills
tags: [wiki, full-ingest, w5, work]
sources: []
summary: 最终 wiki health audit 和收尾判断的工作文档，作为项目 wiki 支线过程证据。
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

# Project Wiki Full Ingest Phase W5 执行工作文档

生成日期：2026-06-20

## 1. 阶段目标

Phase W5 是 Project Wiki Full Ingest 支线的最终健康审查和收尾阶段。

W5 不再扩展新主题，不做产品功能开发，不运行服务、训练、数据刷新或交易相关操作。执行者要验证 `docs/project_wiki` 是否已经可以作为项目专属知识库交付，并输出最终总结。

本阶段完成后必须输出：

- `docs/project_wiki/FULL_INGEST_PHASEW5_FINAL_SUMMARY_CN.md`

## 2. 必读前置文档

执行者开始 W5 前必须读取：

- `docs/project_wiki/PROJECT_WIKI_FULL_INGEST_EXECUTION_AND_REVIEW_PLAN_CN.md`
- `docs/project_wiki/FULL_INGEST_PHASEW0_INVENTORY_REVIEW_CN.md`
- `docs/project_wiki/FULL_INGEST_PHASEW1_CORE_CONTRACTS_REVIEW_CN.md`
- `docs/project_wiki/FULL_INGEST_PHASEW1_CORE_CONTRACTS_FOLLOWUP_REVIEW_CN.md`
- `docs/project_wiki/FULL_INGEST_PHASEW2_PRODUCT_ROUTES_REVIEW_CN.md`
- `docs/project_wiki/FULL_INGEST_PHASEW2_PRODUCT_ROUTES_FOLLOWUP_REVIEW_CN.md`
- `docs/project_wiki/FULL_INGEST_PHASEW3_CODE_MAP_REVIEW_CN.md`
- `docs/project_wiki/FULL_INGEST_PHASEW4_HISTORY_LESSONS_REVIEW_CN.md`
- `docs/project_wiki/index.md`
- `docs/project_wiki/hot.md`
- `docs/project_wiki/log.md`
- `docs/project_wiki/.manifest.json`
- `/home/chuliyang/.codex/skills/llm-wiki/SKILL.md`
- `/home/chuliyang/.codex/skills/wiki-lint/SKILL.md`
- `/home/chuliyang/.codex/skills/wiki-status/SKILL.md`
- `/home/chuliyang/.codex/skills/wiki-query/SKILL.md`

## 3. 允许写入范围

只允许写入：

- `docs/project_wiki/**`

允许更新：

- `docs/project_wiki/.manifest.json`
- `docs/project_wiki/index.md`
- `docs/project_wiki/hot.md`
- `docs/project_wiki/log.md`
- `docs/project_wiki/FULL_INGEST_PHASEW5_FINAL_SUMMARY_CN.md`
- 必要时修复 `docs/project_wiki/**` 内的断链、缺 frontmatter、缺 `## Sources`、明显索引遗漏。

禁止修改产品源码、配置、脚本、测试、数据 artifact 和任何 `docs/project_wiki` 以外的文件。

## 4. 禁止事项

本阶段禁止：

- 运行 backend/frontend 服务。
- 运行 pytest、Playwright、smoke、训练、日更或数据刷新。
- provider refresh / publish。
- accepted latest switch。
- monitor config / scan / alerts 写入。
- broker / quick-trade / order 调用。
- `target_position` / `target_weight` 写入。
- 读取 OpenAI key、密码、token、Authorization header、真实账户信息。
- 真实 OpenAI smoke。
- 生产 latest/default 切换。
- 生成策略 artifact。
- 发布 readonly snapshot。

W5 只做 wiki 健康审查、轻量修复和最终总结。

## 5. 必做 Health Audit

W5 必须执行或手动等价完成以下检查，并在最终总结中给出结果：

| Check | Required result |
|---|---|
| Manifest version | `.manifest.json` 为 `version: 1` |
| Manifest parse | JSON 可解析 |
| Manifest source keys | 关键 entries 使用绝对路径 |
| Manifest provenance | 抽查 entries 有 `content_hash`、`modified_at`、`size_bytes`、`pages_created`、`pages_updated` |
| Frontmatter | 核心页面和新增 W1-W4 页面有 frontmatter |
| Summary | 核心页面和新增 W1-W4 页面有 `summary` |
| Sources | 核心页面和新增 W1-W4 页面有 frontmatter `sources` 与正文 `## Sources` |
| Wikilinks | 无明显 broken wikilinks；如存在必须列出和修复/解释 |
| Index coverage | `index.md` 覆盖核心 concepts、skills、references、synthesis、phase work/report/review |
| Hot cache | `hot.md` 反映 W4/W5 当前状态 |
| Log parseability | `log.md` 记录 W0-W5 关键操作，格式可解析 |
| Historical labels | historical/superseded/archived 页面明确不代表当前默认路径 |
| Orphans | orphan 页面可解释，或补入 index/related links |

## 6. 必须回答的项目知识问题

W5 最终总结必须证明当前 wiki 能回答：

- 当前主线是什么。
- 当前默认模型、策略、候选边界、ranking 和 execution price mode 是什么。
- 怎么新增模型。
- 怎么新增策略。
- Agent 如何回答、依赖哪个 artifact、走哪个 backend route。
- 前端 `/tw-stock-monitor` 展示什么，哪些组件/API 是当前主线。
- 日更、latest pointer、readonly snapshot、Agent latest 的边界是什么。
- 哪些事情不能做：provider publish、accepted latest switch、monitor write、broker/order/quick-trade、target position/weight、OpenAI key 暴露。
- 哪些旧路线已经 historical/superseded，不能被当成当前证据。

## 7. 必须检查的核心页面

至少检查：

- `projects/taiwan-stock-quant-platform/taiwan-stock-quant-platform.md`
- `concepts/modular-artifact-chain.md`
- `concepts/product-artifact-registry.md`
- `concepts/current-default-model-and-strategy.md`
- `concepts/data-freshness-and-latest-pointers.md`
- `concepts/readonly-safety-boundary.md`
- `concepts/agent-daily-prompt-route.md`
- `concepts/frontend-strategy-workbench.md`
- `concepts/daily-update-data-flow.md`
- `skills/new-model-onboarding-workflow.md`
- `skills/new-strategy-onboarding-workflow.md`
- `skills/readonly-e2e-acceptance-workflow.md`
- `skills/frontend-ux-review-workflow.md`
- `skills/data-freshness-diagnosis-workflow.md`
- `skills/safety-boundary-review-workflow.md`
- `skills/modular-integration-regression-workflow.md`
- `synthesis/current-mainline-vs-superseded-routes.md`
- `synthesis/project-risk-map.md`
- `synthesis/historical-lessons.md`
- `references/superseded-routes-model-and-strategy.md`
- `references/superseded-routes-agent-and-tools.md`
- `references/superseded-routes-monitor-provider-and-trading.md`

## 8. Phase 文档索引要求

W5 必须确保 `index.md` 至少列出：

- W0 inventory report/review。
- W1 work/report/review/follow-up/follow-up review。
- W2 work/report/review/follow-up work/follow-up/follow-up review。
- W3 work/report/review。
- W4 work/report/review。
- W5 work/final summary。

如果某些早期 work doc 没有单独创建，最终总结应说明“不存在独立 work doc”或只列实际存在文件。

## 9. W5 最终总结格式

输出文件：

- `docs/project_wiki/FULL_INGEST_PHASEW5_FINAL_SUMMARY_CN.md`

报告必须使用以下格式：

```markdown
# Project Wiki Full Ingest Phase W5 最终总结

## 1. 总体结论
## 2. Health Audit 结果
## 3. Wiki 覆盖范围
## 4. 当前主线答案
## 5. 新模型 / 新策略 / Agent / 前端入口答案
## 6. Historical / Superseded 边界
## 7. 安全边界
## 8. manifest / index / hot / log 状态
## 9. 遗留问题与二轮 ingest 建议
## 10. 请求审查者最终审查的问题
```

## 10. 审查阻塞条件

如果出现以下任一情况，W5 不能请求最终通过：

- manifest 不是 version=1 或 JSON 不可解析。
- 大量 source key 不是绝对路径。
- 核心页面缺 frontmatter、summary、sources 或正文 `## Sources`。
- 大量 broken wikilinks 未解释。
- `index.md` 漏掉核心 concepts/skills/references/synthesis 或关键 phase 文档。
- 历史路线被写成当前路线。
- readonly candidate 被写成交易建议。
- provider publish / accepted latest switch 被写成默认建议。
- broker/order/quick-trade/target position/target weight 被写成允许能力。
- OpenAI key、密码、token、Authorization header 或真实账户信息泄漏。

## 11. 给执行者的启动指令

```text
你是执行者。请启动 Project Wiki Full Ingest 支线 Phase W5，只做 wiki health audit 和最终总结。必须严格对照 docs/project_wiki/FULL_INGEST_PHASEW5_FINAL_SUMMARY_WORK_CN.md 和 docs/project_wiki/PROJECT_WIKI_FULL_INGEST_EXECUTION_AND_REVIEW_PLAN_CN.md。检查 manifest version/JSON/绝对 source key/hash/mtime/size/pages_created/pages_updated、frontmatter、summary、sources、正文 ## Sources、broken wikilinks、orphan、index 覆盖、hot.md、log.md、historical/superseded 标注，并修复 docs/project_wiki 内的轻量问题。输出 docs/project_wiki/FULL_INGEST_PHASEW5_FINAL_SUMMARY_CN.md。严禁运行服务、测试、训练、日更、数据刷新、provider publish、accepted latest switch、monitor 写入、broker/order/quick-trade、target_position/target_weight、OpenAI smoke 或读取任何 key/password/token/真实账户信息。
```
