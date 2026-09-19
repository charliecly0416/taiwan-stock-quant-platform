---
title: Phasew2 Product Routes Review
category: references
tags: [wiki, full-ingest, w2, review]
sources: []
summary: 产品路线、Agent、前端和日更支线编译的审查报告，作为项目 wiki 支线过程证据。
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

# Project Wiki Full Ingest Phase W2 审查报告

生成日期：2026-06-20

## 1. 审查结论

Phase W2 审查结论：有条件通过，但进入 W3 前必须完成 W2 follow-up 修复。

W2 执行报告总体满足阶段目标：四个产品路线目录均已分流，最终稳定事实已编译进 core concepts、supporting references 和 synthesis 页面；Agent 路线保持 DailyAgentPromptArtifact + backend simple-chat；前端路线保持 `/tw-stock-monitor` readonly strategy workbench；`ACCEPTED_WITH_CONDITIONS` 未被写成无条件接受；历史/中间/失败路线被降权到 synthesis。

主要缺口是新增 `references/` 与 `synthesis/` 页面没有正文 `## Sources` section。frontmatter 中有 `sources`，但 W1/W2 页面质量要求和 wiki page template 要求正式页面正文保留 `## Sources`，否则 Obsidian 阅读和人工审查时 provenance 不够直接。该问题不改变产品事实，但必须在 W3 前修复。

## 2. Critical Findings

无。

未发现以下阻塞项：

- 未把历史失败路线写成当前路线。
- 未把 accepted-with-conditions 写成 unconditional accepted。
- 未把 readonly candidate 写成交易建议。
- 未把 provider publish / accepted latest switch 写成默认执行路径。
- 未把 broker/order/quick-trade/target position/target weight 写成允许能力。
- 未泄漏 OpenAI key、密码、token、Authorization header 或真实账户信息。

## 3. High Findings

### H1. W2 新增 reference/synthesis 页面缺正文 `## Sources`

受影响页面：

- `references/agent-daily-prompt-rebuild-final.md`
- `references/ui2-frontend-final.md`
- `references/skills-maintenance-final.md`
- `synthesis/current-mainline-vs-superseded-routes.md`
- `synthesis/project-risk-map.md`

证据：这些页面 frontmatter 含 `sources`，但正文缺少 `## Sources` section。

影响：

- 不影响当前产品事实判断。
- 影响人工审查和 Obsidian 阅读时的 source 可见性。
- 不符合 W2 工作文档延续的正式页面质量要求。

修复要求：

- 为上述 5 个页面补 `## Sources` section。
- Source 列表应使用相对可读路径或现有 wikilink，不需要全文搬运。
- 不新增无必要 reference 页面。
- 同步更新 `.manifest.json`、`log.md`，必要时更新 `hot.md`。
- 输出 `docs/project_wiki/FULL_INGEST_PHASEW2_PRODUCT_ROUTES_FOLLOWUP_CN.md`。

## 4. Medium Findings

无。

## 5. Low Findings

### L1. Manifest 仍将大量 phase report 映射到新增 synthesis/reference 页面

这是 W2 “目录级编译”可解释的结果，不阻塞。但 W3/W5 健康审查时应关注 manifest 可读性：正式知识页映射应优先服务 source-to-page provenance，阶段报告本身不应成为主要知识节点。

## 6. Wiki 结构与链接审查

W2 新增页面存在并已加入 `index.md`：

- `references/agent-daily-prompt-rebuild-final.md`
- `references/ui2-frontend-final.md`
- `references/skills-maintenance-final.md`
- `synthesis/current-mainline-vs-superseded-routes.md`
- `synthesis/project-risk-map.md`

核心页面抽查通过：

- `concepts/agent-daily-prompt-route.md` 明确 Agent 当前路线、builder/validator/prompt boundary、OpenAI/key 边界和 residual conditions。
- `concepts/frontend-strategy-workbench.md` 明确 `/tw-stock-monitor` readonly strategy workbench、API boundary 和 UI2 acceptance evidence。
- `references/pre-rnd-readiness-final-handoff.md` 明确 `ACCEPTED_WITH_CONDITIONS`，没有写成无条件 readiness。
- `index.md` 已修复 W1 follow-up 重复条目。
- `log.md` 已追加 W2 ingest 记录。

未发现大量断链或缺 frontmatter。

## 7. 当前事实 / 历史事实边界审查

W2 保留 W1 当前事实：

- product profile：`strict_e4_yz_product`
- base model：`e4_frozen_qlib_2018_2022`
- treatment model：`e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025`
- display alias：`e4_frozen_qlib_2023_2025_ltr`
- default strategy：`top50_exit_one_worst_sell`
- candidate boundary：`qlib_top50`
- ranking：`ltr_rerank_within_qlib_top50`
- execution price mode：`next_open`

W2 新增当前事实处理合格：

- Agent 当前路线是 DailyAgentPromptArtifact -> backend simple-chat -> frontend readonly explanation。
- 前端当前路线是 `/tw-stock-monitor` readonly strategy workbench。
- project-local `.agents/skills/tw-stock-*` 是当前权威 skill 来源。

历史/中间路线已降权：

- legacy `/agent/chat` / complex tool Agent 主路径降权。
- 工程调试型 `/tw-stock-monitor` 主路径降权。
- old/fresh/P3/O4/bridge/frozen fresh 2025 LTR 默认模型降权。
- buggy/smoke/template strategy 依然不是生产默认。
- YZ4 pending replay return 未被写成收益证明。

## 8. 安全边界审查

W2 安全边界合格。

抽查页面明确禁止：

- provider publish/refresh
- accepted latest switch
- monitor write
- broker/order/quick-trade
- `target_position` / `target_weight`
- frontend OpenAI / OpenAI key exposure
- 真实 OpenAI smoke 默认执行
- 训练、生产 default/latest 切换
- 收益、胜率、上涨概率承诺

Agent simple-chat 仍只是只读策略解释，不是交易助手。

## 9. 是否允许进入下一阶段

不允许直接进入 W3。

必须先完成 W2 follow-up，补齐 H1 的 5 个页面 `## Sources` section。修复完成并通过审查后，才允许进入 W3。

## 10. 下一阶段工作文档或修复要求

下一步执行文档：

- `docs/project_wiki/FULL_INGEST_PHASEW2_PRODUCT_ROUTES_FOLLOWUP_WORK_CN.md`

W3 正式工作文档将在 W2 follow-up 通过后下发。W3 预计聚焦源码、脚本、测试、配置映射，不运行服务、不训练模型、不触发日更。
