---
title: Frontend UX Review Workflow
category: skills
tags: [frontend, ux, workbench, readonly]
aliases: [前端策略工作台 UX 审查]
relationships:
  - target: "[[concepts/frontend-strategy-workbench]]"
    type: implements
  - target: "[[concepts/readonly-safety-boundary]]"
    type: uses
sources: [/home/chuliyang/taiwan-stock-quant-platform/.agents/skills/tw-stock-frontend-workbench-ux-review/SKILL.md, /home/chuliyang/taiwan-stock-quant-platform/.agents/skills/frontend-design/SKILL.md]
summary: 前端 UX 审查保持 /tw-stock-monitor 为安静、精确、只读的研究工作台，避免交易入口和营销式界面。
provenance:
  extracted: 0.84
  inferred: 0.16
  ambiguous: 0.0
base_confidence: 0.8
lifecycle: draft
lifecycle_changed: 2026-06-20
tier: supporting
created: 2026-06-20T12:00:00Z
updated: 2026-06-20T14:00:00Z
---

# Frontend UX Review Workflow

`/tw-stock-monitor` 应是 quiet, precise, research workbench。UX 审查关注信息层级、响应式、可读性、network/console audit 和 readonly 语义。

## Review Focus

- 首屏展示今日策略总览、候选名单、历史模拟、模拟账户状态、Agent simple-chat、data state 和 risk hints。
- desktop/tablet/mobile 截图必须无明显重叠、按钮不溢出、主要面板非空、technical details 默认折叠。
- 文案使用“观察优先级、人工复盘、研究排序、候选调入、调出复核、历史模拟、模拟账户、策略解释助手”。
- 不做 marketing hero、装饰背景、交易助手或实盘入口。

## Forbidden UX

不得新增 broker、quick-trade、real order、target position/weight、monitor write、provider publish/refresh、accepted latest switch、daily real fetch、frontend OpenAI key 或 browser-side OpenAI call。

## W2 Product Route Evidence

UI2 final review defines the frontend target state: 今日策略总览 -> 候选名单 -> 历史模拟 -> 模拟账户状态 -> 策略解释助手。 Technical fields remain available but default collapsed. Agent is a strategy explanation assistant, not a trading assistant.

Future UX work should preserve the quiet research-workbench layout, avoid putting engineering artifact names back on the primary path, and rerun responsive + network/console readonly acceptance.

## Sources

- `.agents/skills/tw-stock-frontend-workbench-ux-review/SKILL.md`
- `.agents/skills/frontend-design/SKILL.md`
