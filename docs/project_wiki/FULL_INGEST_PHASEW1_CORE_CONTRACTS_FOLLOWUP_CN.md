---
title: Phasew1 Core Contracts Followup
category: references
tags: [wiki, full-ingest, w1]
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

# Phase W1 Core Contracts Follow-up 修复报告

生成日期：2026-06-20

## 1. 修复结论

已按 `docs/project_wiki/FULL_INGEST_PHASEW1_CORE_CONTRACTS_REVIEW_CN.md` 的 H1 要求完成 W1 follow-up：补齐 `docs/tw_modular_contracts/templates/*.md` 的显式分流、判断对现有 workflow 页的影响，并同步更新 `.manifest.json`、`index.md`、`hot.md`、`log.md`。

本次只修改 `docs/project_wiki/**`。未修改产品源码、配置、脚本、测试或数据 artifact；未运行服务、刷新数据、provider publish/refresh、accepted latest switch、monitor、broker/order、target position/weight、训练模型或真实 OpenAI smoke。

## 2. 已读取来源范围

- `docs/project_wiki/FULL_INGEST_PHASEW1_CORE_CONTRACTS_REVIEW_CN.md`
- `docs/tw_modular_contracts/templates/*.md`：当前枚举 9 个文件，全部显式分类。

## 3. Templates 分流表

| 文件 | 分类 | 对正式 wiki 页影响 |
| --- | --- | --- |
| `EXECUTION_REPORT_TEMPLATE_CN.md` | workflow template / supporting source | 影响新模型、新策略 workflow 的执行报告证据字段；已更新对应 skills 页。 |
| `REVIEW_REPORT_TEMPLATE_CN.md` | workflow template / supporting source | 影响 review 结论与 forbidden-action 审查字段；已更新对应 skills 页。 |
| `NEW_MODEL_WORK_TEMPLATE_CN.md` | workflow template | 直接影响 [[skills/new-model-onboarding-workflow]]；已补 Template Evidence。 |
| `NEW_STRATEGY_WORK_TEMPLATE_CN.md` | workflow template | 直接影响 [[skills/new-strategy-onboarding-workflow]]；已补 Template Evidence。 |
| `NEW_DATA_SOURCE_WORK_TEMPLATE_CN.md` | supporting source | 数据源接入模板，保留 no_provider_publish/no_accepted_latest_switch；当前无独立 data-source workflow 页，暂不新增页面。 |
| `NEW_FEATURE_WORK_TEMPLATE_CN.md` | supporting source | FeatureArtifact 接入模板，强调 PIT 和 future-field audit；当前无独立 feature workflow 页，暂不新增页面。 |
| `NEW_FRONTEND_READONLY_DISPLAY_WORK_TEMPLATE_CN.md` | supporting source | 前端只读展示模板，要求 GET-only、禁止本地 replay/ranking/signal compute；现有 [[concepts/frontend-strategy-workbench]] 已覆盖核心边界，暂不更新。 |
| `NEW_AGENT_READONLY_CONTEXT_WORK_TEMPLATE_CN.md` | supporting source | Agent readonly context 模板，M0-M6 只允许 placeholder 且不扩权；现有 [[concepts/agent-daily-prompt-route]] 已覆盖当前路线，暂不更新。 |
| `NEW_REPLAY_WINDOW_WORK_TEMPLATE_CN.md` | supporting source | Replay window 模板，禁止前端本地 replay，要求 ReplayResultArtifact output；现有 W1 页面已覆盖 readonly replay 主边界，暂不新增页面。 |

## 4. 已更新页面

- `skills/new-model-onboarding-workflow.md`：加入 `NEW_MODEL_WORK_TEMPLATE_CN.md`、执行报告模板和审查报告模板来源，并补充 Template Evidence。
- `skills/new-strategy-onboarding-workflow.md`：加入 `NEW_STRATEGY_WORK_TEMPLATE_CN.md`、执行报告模板和审查报告模板来源，并补充 Template Evidence。
- `projects/taiwan-stock-quant-platform/taiwan-stock-quant-platform.md`：加入 W1 新核心页面入口，关闭 review L2。
- `index.md`、`hot.md`、`log.md`：记录 follow-up 和 H1 closure。
- `.manifest.json`：新增 9 个 template source entry 和 W1 review source entry，并更新 stats。

## 5. 是否创建新 Reference 页面

不创建。9 个模板是执行/审查 workflow 的支撑来源，不是新的产品事实或独立知识对象。将它们作为 manifest source 和 workflow 证据字段记录，比为每个模板创建 reference 页面更符合 W1“编译，不搬运”的要求。

## 6. 安全边界确认

模板统一要求 `production_allowed=false`、`readonly_boundary`、`forbidden_actions_audit`，并明确禁止训练、收益结论、默认切换、provider publish/refresh、accepted latest switch、monitor/broker/order 写入和前端 Agent 扩权。本次 follow-up 没有改变当前默认模型、默认策略、latest 指针或任何产品行为。

## 7. 自检

- 9 个 `docs/tw_modular_contracts/templates/*.md` 已全部显式分类。
- `.manifest.json` 已包含 `/docs/tw_modular_contracts/templates/` source entry。
- 新增 follow-up 报告已加入 `index.md`。
- `hot.md` 已将 48 文件口径解释为 39 个顶层合同文件 + 9 个 templates 文件。
- 后续进入 W2 前仍应保持 W1 review 的只读边界。
