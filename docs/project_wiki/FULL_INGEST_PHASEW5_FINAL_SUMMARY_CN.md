---
title: Phasew5 Final Summary
category: references
tags: [wiki, full-ingest, w5, summary]
sources: []
summary: 最终 wiki health audit 和收尾判断的最终总结，作为项目 wiki 支线过程证据。
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

# Project Wiki Full Ingest Phase W5 最终总结

## 1. 总体结论

`docs/project_wiki` 已达到项目专属知识库交付状态。W0-W4 已完成范围盘点、核心合同/配置/skill 编译、产品路线编译、源码/脚本/测试静态映射、历史路线降权；W5 完成最终健康审查和轻量修复。

当前 wiki 能作为后续执行者的项目入口，但它不是生产运行授权。所有后续产品动作仍必须遵守只读边界、合同、validator、review workflow 和明确批准。

## 2. Health Audit 结果

| Check | Result |
|---|---|
| Manifest version | 通过：`.manifest.json` 为 `version: 1` |
| Manifest parse | 通过：JSON 可解析 |
| Manifest source keys | 通过：272 个 source key 抽查/统计均为绝对路径 |
| Manifest provenance | 通过：source entries 均包含 `content_hash`、`modified_at`、`size_bytes`、`pages_created`、`pages_updated` |
| Frontmatter | 通过：核心页面和 W1-W4 新增正式知识页有 frontmatter；W5 补齐 project overview frontmatter `sources` |
| Summary | 通过：核心页面和 W1-W4 新增正式知识页有 `summary` |
| Sources | 通过：核心页面和 W1-W4 新增正式知识页有 frontmatter `sources` 与正文 `## Sources` |
| Wikilinks | 通过：自动检查 `broken_wikilinks=0` |
| Index coverage | 通过：`index.md` 已覆盖核心 concepts、skills、references、synthesis、phase work/report/review/follow-up |
| Hot cache | 通过：`hot.md` 反映 W4 历史降权和 W5 最终健康状态 |
| Log parseability | 通过：`log.md` 记录 W0-W5 关键操作，格式保持 parseable |
| Historical labels | 通过：historical/superseded/archived 页面第一屏和 summary 均明确不代表当前默认路径 |
| Orphans | 修复后复查通过：无明显 broken orphan；index/log 类 operational 入口可解释 |

## 3. Wiki 覆盖范围

核心覆盖包括：项目总览、模块化 artifact 链、产品 artifact registry、当前默认模型与策略、四类 latest、新模型 onboarding、新策略 onboarding、Agent DailyPromptArtifact + simple-chat、`/tw-stock-monitor` readonly workbench、日更数据链路、只读安全边界、E2E/UX/freshness/safety/integration workflow、代码映射、历史路线降权和风险地图。

W5 未扩展新业务主题，未 ingest 原始行情、模型二进制、缓存、日志、构建产物、截图 artifact 或大规模历史 phase 文件正文。

## 4. 当前主线答案

当前主线是 artifact-backed readonly research：strict E4 模型/策略链路生成只读候选、回放、snapshot、Agent prompt 和前端解释，不是实盘交易系统。

当前默认值：

- product profile：`strict_e4_yz_product`
- base model：`e4_frozen_qlib_2018_2022`
- treatment model：`e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025`
- display alias：`e4_frozen_qlib_2023_2025_ltr`
- default strategy：`top50_exit_one_worst_sell`
- candidate boundary：`qlib_top50`
- ranking：`ltr_rerank_within_qlib_top50`
- execution price mode：`next_open`

## 5. 新模型 / 新策略 / Agent / 前端入口答案

新模型入口：走 `skills/new-model-onboarding-workflow.md`，必须提供 ModelSignalArtifact、registry entry、golden sample、OOS evidence、coverage、validator 和 review 结论；不能直接切默认/latest。

新策略入口：走 `skills/new-strategy-onboarding-workflow.md`，必须通过 StrategyRule、OrderIntentArtifact、ReplayResultArtifact、readonly snapshot、candidate boundary 和安全审查；不能输出真实订单或目标仓位。

Agent 入口：DailyAgentPromptArtifact -> `TWStockAgentSimpleChatService` -> `POST /api/tw-stock/agent/simple-chat` -> frontend readonly explanation。前端只发送 question/symbol/maxItems；OpenAI adapter 仅后端可用，且 unsafe intent 必须在 OpenAI 前阻断。

前端入口：`/tw-stock-monitor` readonly strategy workbench，展示今日策略总览、候选名单、历史模拟、模拟账户状态和策略解释助手。当前主线 API 是 current-strategy-context、readonly snapshot/replay window、paper portfolio gate 和 simple-chat。

## 6. Historical / Superseded 边界

历史路线已降权：Entry Model v1、旧 LTR rerank/regime/turnover、fresh/adaptive/O4/P3/bridge/frozen-fresh、origin/original、diagnostic E8R、dynamic `/agent/context`、legacy `/agent/chat`、complex tool Agent、旧 monitor/ops/debug panel、provider publish、accepted latest scheduler/switch、archive scripts。

这些内容只能作为 historical、superseded、intermediate、current-risk、boundary-only 或 skip 证据。历史收益、旧 smoke、fixture/mock、截图和 dynamic payload 不能作为当前生产证据。

## 7. 安全边界

默认禁止：provider refresh/publish、accepted latest switch、monitor config/scan/alerts 写入、broker/order/quick-trade、`target_position`、`target_weight`、frontend OpenAI direct call、OpenAI key/base URL/token 暴露、真实 OpenAI smoke、训练、日更、数据刷新、策略 artifact 生成、readonly snapshot publish、生产 latest/default 切换。

允许的上下文是只读 GET/API、artifact manifest/latest pointer、validator 输出、fixture-routed Playwright 证据、simulation-only paper/sim account gate 和 backend simple-chat readonly explanation。

## 8. manifest / index / hot / log 状态

- `.manifest.json`：version 1，JSON 可解析，`last_updated=2026-06-20T18:00:00Z`，`total_sources_ingested=272`，`total_pages=58`，source keys 为绝对路径，provenance 字段完整。
- `index.md`：已补齐 W1/W2 work、W2 follow-up work、W3 review、W4 review、W5 work/final summary 和总计划入口。
- `hot.md`：已加入 W5 final health audit 状态，并保留 W4 历史路线降权提醒。
- `log.md`：已追加 `SUMMARY phase="W5_FINAL_SUMMARY"` 操作记录。

## 9. 遗留问题与二轮 ingest 建议

- 二轮 ingest 可选择更细地处理 crawler/scrapling handoff、qlib extension、research diagnostics，但必须另开范围文档。
- 不建议逐篇 ingest `docs/archive/phase_history/**`；如未来需要，只抽稳定教训，不恢复旧路线。
- manifest 中部分 source-to-report 映射偏噪声，但不影响当前交付；后续可在维护周期中做 provenance 精简。
- 工作区可能存在 `docs/project_wiki` 以外的既有脏变更；W5 未归因、未修改、未清理这些变更。

## 10. 请求审查者最终审查的问题

- 是否认可 `docs/project_wiki` 作为当前项目知识库交付入口。
- 是否认可 W5 对 manifest/index/hot/log、断链、frontmatter、Sources、orphan 的健康审查结论。
- 是否仍有历史路线可能被误读为当前默认路径。
- 是否需要开启二轮专项 ingest；若需要，应先定义范围和禁止事项。
