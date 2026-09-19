---
title: Pre-RND Readiness Governance
category: skills
tags: [pre-rnd, governance, acceptance, handoff]
aliases: [Pre-RND 支线治理]
relationships:
  - target: "[[references/pre-rnd-readiness-final-handoff]]"
    type: derived_from
sources: [/home/chuliyang/taiwan-stock-quant-platform/docs/tw_new_model_strategy_pre_rnd/PRE_RND_READINESS_COORDINATOR_HANDOFF_CN.md]
summary: Pre-RND 支线已经有条件收尾，后续研发只能按单变量、窄范围、先工作文档后执行的方式启动。
provenance:
  extracted: 0.88
  inferred: 0.12
  ambiguous: 0.0
base_confidence: 0.67
lifecycle: draft
lifecycle_changed: 2026-06-20
tier: supporting
created: 2026-06-20T00:00:00Z
updated: 2026-06-20T14:00:00Z
---

# Pre-RND Readiness Governance

Pre-RND readiness 的结论是 `ACCEPTED_WITH_CONDITIONS`。它允许开启研发节点，但不允许无条件开放研发，也不建议第一轮同时开新模型和新策略。

## Startup Constraints

- 第一轮研发必须限制为单变量：单模型或单策略。
- 第一轮推荐路线是单新模型节点。
- 执行者必须先提交独立 work doc，再允许训练或 artifact 生成。
- 后续节点以 project-local `.agents/skills/tw-stock-*` 为准。
- 如运行时触发 archive 旧 skill 描述，必须停止并报告。
- 正式研发前建议做版本冻结提交或 baseline tag。

## W2 Readiness Boundary

Final acceptance is `ACCEPTED_WITH_CONDITIONS`: only narrow single-variable new model or new strategy R&D is allowed. First recommended route is a single new model node ending at ModelSignalArtifact + registry + golden sample + OOS evidence + validator + review report. It does not authorize default/latest switch, production artifact publish, strategy/frontend/Agent changes, or simultaneous model+strategy development.

## Sources

- [[references/pre-rnd-readiness-final-handoff|Pre-RND Readiness Final Handoff]]
