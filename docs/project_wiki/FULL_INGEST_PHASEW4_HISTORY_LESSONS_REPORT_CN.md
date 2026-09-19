---
title: Phasew4 History Lessons Report
category: references
tags: [wiki, full-ingest, w4, report]
sources: []
summary: 历史路线和弯路降权归档的执行报告，作为项目 wiki 支线过程证据。
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

# Project Wiki Full Ingest Phase W4 执行报告

## 1. 本阶段结论

W4 已完成历史路线、旧实验、弯路和被替代方案的知识库降权归档。当前主线未改变：`strict_e4_yz_product`、`e4_frozen_qlib_2018_2022`、`e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025`、display alias `e4_frozen_qlib_2023_2025_ltr`、默认策略 `top50_exit_one_worst_sell`、候选边界 `qlib_top50`、`ltr_rerank_within_qlib_top50`、执行价 `next_open`、DailyAgentPromptArtifact -> backend simple-chat -> frontend readonly explanation、`/tw-stock-monitor` readonly strategy workbench。

W4 的新增知识只回答历史路线为什么被替代、当前替代方案是什么、后续执行者如何避免误读；没有复活旧 Agent/tool、monitor/provider、broker/order、quick-trade、accepted latest switch 或旧模型/策略默认路径。

## 2. 读取的 source 范围

- W4 工作文档：`docs/project_wiki/FULL_INGEST_PHASEW4_HISTORY_LESSONS_WORK_CN.md`。
- W1/W2/W3 审查基线与既有 wiki 页面：core contracts review、product routes follow-up review、code map review、current mainline、risk map、默认模型策略、Agent、frontend、readonly boundary 页面。
- 历史模型/策略路线：`docs/tw_decision_model/**`、`docs/tw_ltr_*`、`docs/tw_orthogonal_*` 中的 final/review/closure 文档。
- 历史 Agent/frontend/productization 路线：Agent Daily Prompt rebuild final/review、UI2 final route review、strict E4/YZ cleanup/final summary、real provider daily update runbook。
- 归档目录说明：`docs/archive/phase_history/README_CN.md`、`scripts/archive/historical_research/README.md`。

## 3. 明确排除的 source 范围

- 原始行情 CSV/parquet/sqlite/db、模型二进制、pickle、bin、mlruns、cache、build output、日志、截图和测试 artifact。
- credential、token、password、OpenAI key、Authorization header、真实账户 payload。
- 历史脚本正文的大规模逐行 ingest；W4 只读取 `scripts/archive/historical_research/README.md` 作为归档边界说明。
- 产品源码、配置、测试和数据 artifact 的写入或运行。

## 4. 新增 / 更新的 wiki 页面

新增页面：

- `synthesis/historical-lessons.md`
- `references/superseded-routes-model-and-strategy.md`
- `references/superseded-routes-agent-and-tools.md`
- `references/superseded-routes-monitor-provider-and-trading.md`
- `FULL_INGEST_PHASEW4_HISTORY_LESSONS_REPORT_CN.md`

更新页面：

- `synthesis/current-mainline-vs-superseded-routes.md`
- `synthesis/project-risk-map.md`
- `concepts/current-default-model-and-strategy.md`
- `concepts/agent-daily-prompt-route.md`
- `concepts/frontend-strategy-workbench.md`
- `concepts/readonly-safety-boundary.md`
- `.manifest.json`
- `index.md`
- `hot.md`
- `log.md`

## 5. manifest / index / hot / log 更新

- `.manifest.json` 已追加 W4 work doc 与 W4 历史 source entries，source key 使用绝对路径，并记录 `content_hash`、`modified_at`、`size_bytes`、`pages_created`、`pages_updated`。
- `index.md` 已加入 W4 work/report、`historical-lessons` 与三类 superseded routes references。
- `hot.md` 已加入 W4 recent activity 与“历史路线已降权，不代表当前默认路径”的活跃提醒。
- `log.md` 已追加 `INGEST phase="W4_HISTORY_LESSONS"` 可解析记录。

## 6. 当前事实与历史事实边界

| Source group / path pattern | Classification | Extracted lesson | Current replacement | Wiki page target | Risk if misread |
|---|---|---|---|---|---|
| `docs/tw_decision_model/**` | superseded | Entry Model v1 没有稳定超过 qlib rank，失败归因和 gate 方法可复用，模型本身不保留 | strict E4 artifact chain + qlib top50/LTR top50 内重排 | `references/superseded-routes-model-and-strategy.md` | 把失败 rerank 写成当前 AI 选股能力 |
| `docs/tw_ltr_strategy_validation/**` | historical | optional simulation 可作为 readonly 复盘，不是默认策略或交易策略 | `top50_exit_one_worst_sell` + readonly replay/paper gate | `synthesis/historical-lessons.md` | 把 optional sim 当产品默认或收益证明 |
| `docs/tw_ltr_baseline_conservative_tuning/**` | intermediate | split purity、mixed period、full range 只说明旧路线修复过程 | 当前 validator、fixed OOS、same-window baseline | `references/superseded-routes-model-and-strategy.md` | 用中间修复结果替代最终证据 |
| `docs/tw_ltr_rerank_regime_turnover/**` | superseded | LTR rerank/regime/turnover 主线已归档，只保留最小 readonly explanation 教训 | DailyAgentPromptArtifact/simple-chat 与 current workbench explanation | `references/superseded-routes-model-and-strategy.md` | 复活 manual review explanation 或交易化 LTR |
| `docs/tw_orthogonal_*` | historical | 控制变量与 PIT/coverage 是可复用教训，Orthogonal Fresh Qlib 不进入产品候选 | strict E4 Model A/Model B scoped orthogonal LTR | `synthesis/historical-lessons.md` | 把未支持 treatment 写成当前模型 |
| `docs/tw_modular_daily_update_productization/PHASEYZ*` | current-risk | strict E4/YZ 清理确立当前替代方案，并移除 fresh/P3/O4/bridge/origin/original | two production E4 models + `top50_exit_one_worst_sell` | `concepts/current-default-model-and-strategy.md` | 把清理前旧模型重新加入 selectable |
| `docs/tw_agent_daily_prompt_rebuild/**` | superseded | 旧 dynamic context、legacy chat 和 complex tool route 被 artifact-backed simple-chat 替代 | DailyAgentPromptArtifact -> backend simple-chat -> readonly explanation | `references/superseded-routes-agent-and-tools.md` | 把旧 `/agent/chat` 或 tool Agent 当当前主线 |
| `docs/tw_modular_daily_update_productization/PHASEUI2*` | current-risk | `/tw-stock-monitor` 已从工程/debug/ops 面板收敛为 readonly strategy workbench | current strategy context + simple-chat + readonly panels | `concepts/frontend-strategy-workbench.md` | 把旧 monitor/ops UI 当当前 frontend 主线 |
| `docs/tw_modular_daily_update_productization/REAL_PROVIDER_DAILY_UPDATE_RUNBOOK_CN.md` | boundary-only | provider daily update 是受控 runbook，不是默认 publish/accepted latest 建议 | readonly latest/status gates and diagnostics | `references/superseded-routes-monitor-provider-and-trading.md` | 在 freshness 诊断中建议 publish 或 accepted latest switch |
| `docs/archive/phase_history/**` | historical | 大量 phase 文件是过程证据，不是当前入口 | docs summaries/contracts/runbooks + project wiki current pages | `synthesis/historical-lessons.md` | 用旧 phase 文件覆盖 W1/W2/W3 已审定事实 |
| `scripts/archive/historical_research/**` | skip | 历史脚本不再是 active product chain；恢复前需新审查 | root `scripts/` validators/builders and current contracts | `references/superseded-routes-monitor-provider-and-trading.md` | 直接运行归档脚本刷新/训练/回放 |
| broker/order/quick-trade/credential docs or routes | boundary-only | 只作为禁区证据，不是允许能力 | simulation-only paper/sim gate, no broker/order | `concepts/readonly-safety-boundary.md` | 泄漏密钥或把交易能力写成允许 |

## 7. 安全边界确认

W4 未运行 backend/frontend 服务、pytest、Playwright、smoke、训练、数据刷新、provider refresh/publish、accepted latest switch、monitor 写入、broker/order/quick-trade、target_position/target_weight、OpenAI smoke、artifact generation 或 readonly snapshot publish。

W4 未读取或复制任何 key、password、token、Authorization header、真实账户 payload。涉及这些词的内容只以 forbidden/boundary 语义进入 wiki。

## 8. 自检结果

- 新增/更新的正式 wiki 页面均保留 frontmatter、`summary`、`sources` 和正文 `## Sources`，W4 报告按要求 10 节输出。
- 没有把 historical/superseded 写成 current；当前主线仍由 W1/W2/W3 审定页面定义。
- 没有把历史收益、旧 smoke、fixture/mock、截图或 dynamic payload 写成当前生产证据。
- 没有读取或复制任何 key、password、token 或真实账户信息。
- 实际写入范围限制在 `docs/project_wiki/**`；若工作区存在产品代码脏变更，不属于 W4 写入范围。

## 9. 遗留问题

- W4 只做历史路线蒸馏，没有逐篇 ingest `docs/archive/phase_history/**` 的 479 个历史阶段文件。
- 若未来要重启任一旧模型、旧 Agent/tool、provider publish、accepted latest、monitor 或 broker/trading 路线，必须新开合同和审查，不能复用 W4 历史页面作为授权。

## 10. 请求审查者审查的问题

- 是否仍有任何句子可能把 old/fresh/adaptive/O4/P3/bridge/origin/original、Entry Model v1 或 optional LTR sim 误读为当前默认路径。
- 是否所有 provider publish、accepted latest、monitor write、broker/order/quick-trade、credential 和 target position/weight 表述都保持 boundary-only。
- manifest entries 是否满足绝对路径、hash、mtime、size 和 pages_created/pages_updated 要求。
- W4 是否充分连接到 `current-mainline-vs-superseded-routes` 与 `project-risk-map`，让后续执行者不会被历史文档误导。
