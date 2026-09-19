---
title: Phasew2 Product Routes Followup WORK
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

# Project Wiki Full Ingest Phase W2 Follow-up 执行工作文档

生成日期：2026-06-20

## 1. 修复目标

本 follow-up 只修复 W2 审查 H1：W2 新增 reference/synthesis 页面缺正文 `## Sources` section。

本次不是 W3，不读取源码，不运行服务，不扩展产品事实。

## 2. 必读文档

执行者必须读取：

- `docs/project_wiki/FULL_INGEST_PHASEW2_PRODUCT_ROUTES_REPORT_CN.md`
- `docs/project_wiki/FULL_INGEST_PHASEW2_PRODUCT_ROUTES_REVIEW_CN.md`
- `/home/chuliyang/.codex/skills/llm-wiki/SKILL.md`

## 3. 允许写入范围

只允许写入：

- `docs/project_wiki/**`

允许更新：

- `references/agent-daily-prompt-rebuild-final.md`
- `references/ui2-frontend-final.md`
- `references/skills-maintenance-final.md`
- `synthesis/current-mainline-vs-superseded-routes.md`
- `synthesis/project-risk-map.md`
- `.manifest.json`
- `log.md`
- `hot.md`，如有必要
- `docs/project_wiki/FULL_INGEST_PHASEW2_PRODUCT_ROUTES_FOLLOWUP_CN.md`

禁止修改产品源码、配置、脚本、测试和数据 artifact。

## 4. 修复要求

为以下 5 个页面补正文 `## Sources` section：

- `references/agent-daily-prompt-rebuild-final.md`
- `references/ui2-frontend-final.md`
- `references/skills-maintenance-final.md`
- `synthesis/current-mainline-vs-superseded-routes.md`
- `synthesis/project-risk-map.md`

要求：

- Source list 使用相对可读路径即可。
- 不复制源文档正文。
- 不新增无必要 reference 页面。
- 不改变 W2 当前事实结论。
- 同步更新 `.manifest.json` 和 `log.md`。

## 5. 禁止事项

禁止：

- 真实数据拉取
- provider refresh / publish
- accepted latest switch
- monitor config / scan / alerts 写入
- broker / quick-trade / order
- `target_position` / `target_weight`
- 读取 OpenAI key、密码、token、真实账户信息
- 真实 OpenAI smoke
- 生产 latest/default 切换
- 训练模型
- 生成策略 artifact
- 发布 readonly snapshot
- 运行服务

## 6. 输出报告

输出：

- `docs/project_wiki/FULL_INGEST_PHASEW2_PRODUCT_ROUTES_FOLLOWUP_CN.md`

报告必须包含：

- 修复结论
- 更新页面列表
- manifest/log 更新说明
- 安全边界确认
- 自检结果

## 7. 给执行者的启动命令

```text
你是执行者。请完成 Project Wiki Full Ingest Phase W2 follow-up，只修复 W2 审查 H1：为 references/agent-daily-prompt-rebuild-final.md、references/ui2-frontend-final.md、references/skills-maintenance-final.md、synthesis/current-mainline-vs-superseded-routes.md、synthesis/project-risk-map.md 补正文 ## Sources section。只允许写 docs/project_wiki。同步更新 .manifest.json 和 log.md，必要时更新 hot.md。输出 docs/project_wiki/FULL_INGEST_PHASEW2_PRODUCT_ROUTES_FOLLOWUP_CN.md。不得读取 OpenAI key、运行服务、刷新数据、provider publish、accepted latest、monitor、broker/order、target_position/target_weight、训练模型、生成策略 artifact 或改产品代码。
```
