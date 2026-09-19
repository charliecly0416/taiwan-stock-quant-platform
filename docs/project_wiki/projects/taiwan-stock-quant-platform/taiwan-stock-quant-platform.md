---
title: Taiwan Stock Quant Platform
category: project
tags: [tw-stock, quant, readonly, agent, frontend]
source_path: /home/chuliyang/taiwan-stock-quant-platform
sources: [/home/chuliyang/taiwan-stock-quant-platform/docs/tw_new_model_strategy_pre_rnd/PRE_RND_READINESS_COORDINATOR_HANDOFF_CN.md, /home/chuliyang/taiwan-stock-quant-platform/docs/tw_new_model_strategy_pre_rnd/TW_DAILY_UPDATE_DATA_FLOW_REAL_SAMPLE_20260618_CN.md, /home/chuliyang/taiwan-stock-quant-platform/docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md]
created: 2026-06-20T00:00:00Z
updated: 2026-06-20T18:00:00Z
summary: 台股量化平台的项目级知识入口，聚合架构、合同、安全边界、Agent、前端和 pre-RND 研发约束。
provenance:
  extracted: 0.82
  inferred: 0.18
  ambiguous: 0.0
base_confidence: 0.78
lifecycle: draft
lifecycle_changed: 2026-06-20
tier: core
---

# Taiwan Stock Quant Platform

本项目当前主线是“只读研究 + 产品化候选展示 + 模拟账户”，不是实盘交易系统、自动下单系统或收益承诺系统。平台目标是让数据、模型、策略、回放、API、前端和模拟账户以可审查、可复现、可回滚的方式协同工作。

## Key Concepts

- [[concepts/modular-artifact-chain|Modular Artifact Chain]] — 标准模块边界和 artifact 流转。
- [[concepts/product-artifact-registry|Product Artifact Registry]] — 当前产品 registry、artifact root 和只读 flags。
- [[concepts/current-default-model-and-strategy|Current Default Model And Strategy]] — 当前默认模型、策略、candidate boundary 和 execution price mode。
- [[concepts/frontend-strategy-workbench|Frontend Strategy Workbench]] — 前端策略工作台的只读展示入口。
- [[concepts/data-freshness-and-latest-pointers|Data Freshness And Latest Pointers]] — provider、qlib、snapshot、Agent 四类 latest 边界。
- [[concepts/readonly-safety-boundary|Readonly Safety Boundary]] — 所有研发节点必须继承的安全红线。
- [[concepts/daily-update-data-flow|Daily Update Data Flow]] — 日更数据链路与真实样本。
- [[concepts/agent-daily-prompt-route|Agent Daily Prompt Route]] — Agent 的当前产品化路线。

## Workflows

- [[skills/new-model-onboarding-workflow|New Model Onboarding Workflow]] — 第一轮推荐路线。
- [[skills/new-strategy-onboarding-workflow|New Strategy Onboarding Workflow]] — 第二类允许研发路线。
- [[skills/readonly-e2e-acceptance-workflow|Readonly E2E Acceptance Workflow]] — 前端/Agent 只读验收路线。
- [[skills/safety-boundary-review-workflow|Safety Boundary Review Workflow]] — forbidden action 和网络安全边界审查路线。
- [[skills/modular-integration-regression-workflow|Modular Integration Regression Workflow]] — 模型到策略到 Agent 的集成回归路线。
- [[skills/pre-rnd-readiness-governance|Pre-RND Readiness Governance]] — readiness 支线和统筹交接约束。

## Current Closure State

Pre-RND readiness 支线结论是 `ACCEPTED_WITH_CONDITIONS`：可以收尾，但只允许进入列明的窄范围新模型/新策略研发。第一轮建议单新模型节点，且不改默认模型、默认策略、前端默认、Agent prompt 来源或任何 latest/default 路径。

## Sources

- [[references/pre-rnd-readiness-final-handoff|Pre-RND Readiness Final Handoff]]
- [[references/real-sample-20260618|Real Sample 2026-06-18]]
