---
title: Phasew4 History Lessons Review
category: references
tags: [wiki, full-ingest, w4, review]
sources: []
summary: 历史路线和弯路降权归档的审查报告，作为项目 wiki 支线过程证据。
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

# Project Wiki Full Ingest Phase W4 审查报告

生成日期：2026-06-20

## 1. 审查结论

Phase W4 审查结论：通过，允许进入 W5。

执行者按 `FULL_INGEST_PHASEW4_HISTORY_LESSONS_WORK_CN.md` 完成历史路线、旧实验、归档脚本和被替代方案的降权归档。W4 新增/更新内容没有改变 W1/W2/W3 已审定的当前主线：strict E4 当前默认模型与策略、DailyAgentPromptArtifact + backend simple-chat、`/tw-stock-monitor` readonly strategy workbench、只读安全边界。

W4 的核心价值是把旧模型/策略、旧 Agent/tool、monitor/provider/trading 相关材料收束到 `historical`、`superseded`、`boundary-only` 或 `skip` 语义，降低后续执行者把历史事实误读为当前事实的风险。

## 2. Critical Findings

无。

未发现以下阻塞项：

- 未把历史失败路线写成当前路线。
- 未把旧 Agent/tool route 写成当前 Agent 主线。
- 未把旧 monitor/ops UI 写成当前 frontend 主线。
- 未把 broker/order/quick-trade/live trading/credential 写成允许能力。
- 未把 target position / target weight 写成允许输出。
- 未把 provider publish / accepted latest switch 写成默认执行建议。
- 未把历史实验收益、旧 smoke、测试 fixture、mock 或 dynamic payload 写成当前生产证据。
- 未发现 OpenAI key、密码、token、Authorization header 或真实账户信息泄漏。

## 3. High Findings

无。

W4 已满足本阶段关键要求：

- 新增 `synthesis/historical-lessons.md`。
- 新增三类 superseded references：model/strategy、Agent/tools、monitor/provider/trading。
- 更新 `synthesis/current-mainline-vs-superseded-routes.md` 与 `synthesis/project-risk-map.md`。
- 报告第 6 节提供 source classification table，并包含 classification、extracted lesson、current replacement、wiki target、risk if misread。
- 历史收益、旧 smoke、旧截图、fixtures、dynamic payload 均被降权为 non-production evidence。

## 4. Medium Findings

无。

## 5. Low Findings

### L1. W5 需要补做全局 wiki health audit，而不是只依赖 W4 抽查

W4 页面抽查合格，但本次审查未完整跑通自动 lint。部分只读校验命令在当前 sandbox 中偶发出现 `bwrap: loopback: Failed RTM_NEWADDR`，因此 W5 应把 manifest JSON 解析、断链、frontmatter、orphan、stale/historical 标注和 index 覆盖作为正式收尾项。

该问题不影响 W4 进入 W5，因为 W4 本阶段目标是历史路线降权，而不是全库健康收尾。

### L2. `index.md` 当前未列 W3 review

`index.md` 已列 W4 work/report 和 W4 新增 historical/superseded 页面，但抽查时未看到 `FULL_INGEST_PHASEW3_CODE_MAP_REVIEW_CN.md`。这不是 W4 阻塞项，因为 W4 的新增入口完整；但 W5 final summary 前应补齐所有 phase work/report/review/follow-up 文档索引。

## 6. Wiki 结构与链接审查

抽查通过。

新增页面：

- `synthesis/historical-lessons.md`
- `references/superseded-routes-model-and-strategy.md`
- `references/superseded-routes-agent-and-tools.md`
- `references/superseded-routes-monitor-provider-and-trading.md`

结构检查结果：

- 以上新增页面均有 frontmatter、`summary`、`sources`、relationships、`lifecycle` 和正文 `## Sources`。
- 三个 superseded reference 的第一屏均明确“历史路线，不代表当前默认路径”。
- `synthesis/current-mainline-vs-superseded-routes.md` 增加 W4 Historical Route Boundary，明确 W4 不修改当前 defaults。
- `synthesis/project-risk-map.md` 增加 W4 Historical Misread Risks 和 Blocking Escalations。
- `index.md` 已列 W4 work/report、`historical-lessons` 与三类 superseded references。
- `hot.md` 已提示“历史路线已降权，不代表当前默认路径”。
- `log.md` 已追加 `INGEST phase="W4_HISTORY_LESSONS"` 记录。
- `.manifest.json` 抽查到 W4 source entries 使用绝对路径，并包含 `content_hash`、`modified_at`、`size_bytes`、`pages_created`、`pages_updated`。

## 7. 当前事实 / 历史事实边界审查

当前事实边界合格。

W4 保持以下当前事实不变：

- 模型/策略：strict E4 two-model product route + `top50_exit_one_worst_sell`。
- Agent：DailyAgentPromptArtifact -> backend simple-chat -> frontend readonly explanation。
- Frontend：`/tw-stock-monitor` readonly strategy workbench。
- Latest：provider latest、qlib accepted latest、snapshot latest、Agent latest 继续保持分离。
- Trading：paper/sim account 仍是 simulation-only gate，不是 broker/order。

历史事实降权合格：

- Entry Model v1、旧 LTR、fresh/adaptive/O4/P3/bridge/origin/original 被标为 failed/superseded/historical/diagnostic。
- 旧 dynamic Agent、legacy `/agent/chat`、complex tool route 被标为 superseded 或 boundary-only。
- monitor config/scan/alerts、provider publish、accepted latest switch、quick-trade/broker/orders、credentials/API keys 被标为 boundary-only。
- `docs/archive/phase_history/**` 和 `scripts/archive/historical_research/**` 被明确为历史证据或 skip runtime。

## 8. 安全边界审查

安全边界合格。

W4 报告和新增页面只在拒绝、边界、历史说明或误读风险语义中提到以下敏感/高风险项：

- provider publish / accepted latest switch；
- monitor write / scan / alerts；
- broker/order/quick-trade/live trading；
- credentials/API keys；
- target position / target weight；
- OpenAI key、Authorization header、token；
- 历史收益、旧 smoke、fixtures、mock、dynamic payload。

未发现实际密钥、token、密码、Authorization header 或真实账户 payload 被写入 wiki。W4 也未声称运行服务、测试、训练、数据刷新、provider publish、accepted latest switch、monitor 写入、broker/order、OpenAI smoke 或 artifact generation。

## 9. 是否允许进入下一阶段

允许进入 W5。

W5 是最终健康审查和收尾阶段，应从“内容是否正确”转向“整个项目专属 wiki 是否可交付”：manifest、frontmatter、断链、index、orphan、stale/historical 标注、hot/log 可解析，以及是否能回答当前主线、新模型、新策略、Agent、前端和禁止事项。

## 10. 下一阶段工作文档或修复要求

下一阶段执行文档已给出：

- `docs/project_wiki/FULL_INGEST_PHASEW5_FINAL_SUMMARY_WORK_CN.md`

W5 必须至少处理：

- 补齐所有 phase work/report/review/follow-up 文档索引，特别是 W3 review、W4 review、W5 work/report。
- 完成 manifest version=1、JSON 可解析、绝对 source key、hash/mtime/size/pages_created/pages_updated 抽查。
- 检查新增/核心页面 frontmatter、summary、sources、正文 `## Sources`。
- 检查 broken wikilinks 和 orphan 页面，并解释合理 orphan。
- 确认 historical/superseded 页面不会覆盖 current mainline。
- 输出 `docs/project_wiki/FULL_INGEST_PHASEW5_FINAL_SUMMARY_CN.md`。
