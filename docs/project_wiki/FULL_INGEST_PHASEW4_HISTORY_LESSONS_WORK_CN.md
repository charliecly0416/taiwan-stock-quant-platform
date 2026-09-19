---
title: Phasew4 History Lessons WORK
category: skills
tags: [wiki, full-ingest, w4, work]
sources: []
summary: 历史路线和弯路降权归档的工作文档，作为项目 wiki 支线过程证据。
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

# Project Wiki Full Ingest Phase W4 执行工作文档

生成日期：2026-06-20

## 1. 阶段目标

Phase W4 的目标是归档历史路线、旧实验、弯路和被替代方案，只抽取仍有价值的教训。

W4 不是重新评估当前产品默认路径，不是复活旧 agent/tool/broker/monitor/provider publish 路线，也不是把历史实验收益或 smoke 结果写成当前证据。执行者必须回答：

- 哪些历史路线已经 superseded / archived。
- 它们为什么被当前路线替代。
- 当前替代方案是什么。
- 哪些风险或误读需要写进长期项目风险地图。
- 后续执行者看到旧文档时应该如何避免把历史事实误读为当前事实。

本阶段完成后必须输出：

- `docs/project_wiki/FULL_INGEST_PHASEW4_HISTORY_LESSONS_REPORT_CN.md`

## 2. 必读前置文档

执行者开始 W4 前必须读取：

- `docs/project_wiki/PROJECT_WIKI_FULL_INGEST_EXECUTION_AND_REVIEW_PLAN_CN.md`
- `docs/project_wiki/FULL_INGEST_PHASEW1_CORE_CONTRACTS_REVIEW_CN.md`
- `docs/project_wiki/FULL_INGEST_PHASEW2_PRODUCT_ROUTES_FOLLOWUP_REVIEW_CN.md`
- `docs/project_wiki/FULL_INGEST_PHASEW3_CODE_MAP_REVIEW_CN.md`
- `docs/project_wiki/synthesis/current-mainline-vs-superseded-routes.md`
- `docs/project_wiki/synthesis/project-risk-map.md`
- `docs/project_wiki/concepts/current-default-model-and-strategy.md`
- `docs/project_wiki/concepts/agent-daily-prompt-route.md`
- `docs/project_wiki/concepts/frontend-strategy-workbench.md`
- `docs/project_wiki/concepts/readonly-safety-boundary.md`
- `/home/chuliyang/.codex/skills/llm-wiki/SKILL.md`
- `/home/chuliyang/.codex/skills/wiki-ingest/SKILL.md`
- `/home/chuliyang/.codex/skills/wiki-lint/SKILL.md`
- `/home/chuliyang/.codex/skills/wiki-status/SKILL.md`

W4 必须以 W1/W2/W3 已审定事实为基准，不得重新打开默认模型、默认策略、Agent route、frontend route 或 readonly safety boundary。

## 3. 允许写入范围

只允许写入：

- `docs/project_wiki/**`

允许更新：

- `docs/project_wiki/.manifest.json`
- `docs/project_wiki/index.md`
- `docs/project_wiki/hot.md`
- `docs/project_wiki/log.md`
- `docs/project_wiki/synthesis/historical-lessons.md`
- `docs/project_wiki/synthesis/current-mainline-vs-superseded-routes.md`
- `docs/project_wiki/synthesis/project-risk-map.md`
- 必要时更新少量 core concepts 的历史边界段落
- 必要时新增少量 `references/superseded-routes-*.md`
- `docs/project_wiki/FULL_INGEST_PHASEW4_HISTORY_LESSONS_REPORT_CN.md`

禁止修改产品源码、配置、脚本、测试、数据 artifact 和任何 `docs/project_wiki` 以外的文件。

## 4. 禁止事项

本阶段禁止：

- 运行 backend/frontend 服务
- 运行 pytest、Playwright、smoke 或 contract regression
- 训练模型或重新计算实验收益
- 真实数据拉取
- provider refresh / publish
- accepted latest switch
- monitor config / scan / alerts 写入
- broker / quick-trade / order 调用
- `target_position` / `target_weight` 写入
- 读取 OpenAI key、密码、token、真实账户信息
- 真实 OpenAI smoke
- 生产 latest/default 切换
- 生成策略 artifact
- 发布 readonly snapshot
- 把历史收益、旧 smoke、旧截图、测试 fixture 或动态 payload 当当前生产证据

W4 只读历史文档和少量历史脚本路径，并写 `docs/project_wiki`。

## 5. W4 Source 范围

### 5.1 历史实验和旧路线文档

选择性读取：

- `docs/tw_ltr_*`
- `docs/tw_decision_model*`
- `docs/tw_orthogonal_*`
- `docs/archive/`
- 旧 phase acceptance / execution / review 文档
- 早期 Agent、frontend、product adaptation 报告
- `scripts/archive/**`

读取目标不是逐篇摘要，而是抽取稳定教训。

### 5.2 必须降权的历史主题

以下主题只能作为 historical / superseded / boundary 进入 wiki：

- 旧 Agent tool / complex Agent route。
- 旧 monitor / ops UI 作为当前前端主线的替代。
- quick-trade / broker / live trading / credential route。
- provider publish / accepted latest scheduler / normal publish 作为默认路径。
- old/fresh/adaptive/diagnostic strategies 作为 product default。
- 旧实验中的单次收益、smoke 通过、截图、动态 payload。
- 未被 W1/W2/W3 接受的模型、策略、候选集和 latest 指针。

### 5.3 不进入 wiki 的内容

默认不读取或不编译：

- 原始行情 CSV / parquet / sqlite / db。
- 模型二进制、pickle、bin。
- mlruns、cache、logs、build output。
- 大量截图、测试输出 artifact。
- credential、token、password、OpenAI key 或真实账户 payload。

## 6. 目标 Wiki 页面

W4 应优先更新：

- `synthesis/historical-lessons.md`
- `synthesis/current-mainline-vs-superseded-routes.md`
- `synthesis/project-risk-map.md`

必要时可新增：

- `references/superseded-routes-agent-and-tools.md`
- `references/superseded-routes-model-and-strategy.md`
- `references/superseded-routes-monitor-provider-and-trading.md`

新增 reference 必须满足：

- frontmatter `lifecycle: archived` 或 `lifecycle: draft`。
- `summary` 明确写出 superseded / historical。
- 正文第一屏明确“历史路线，不代表当前默认路径”。
- 正文必须有 `## Sources`。
- 不为每个历史报告单独建 reference。

## 7. 必须产出的分类表

W4 报告必须包含 source classification table，至少使用以下分类：

| Classification | Meaning |
|---|---|
| historical | 历史事实，可用于背景，不代表当前路线 |
| superseded | 已被当前主线替代，必须说明替代方案 |
| intermediate | 中间尝试/修复过程，不可写成最终结论 |
| current-risk | 仍会影响当前维护的风险或误读点 |
| boundary-only | 只作为安全边界/禁区证据 |
| skip | 不进入 wiki，或只记录为 manifest/source reference |

每个被读取的历史 source group 必须给出：

- source group / path pattern；
- classification；
- extracted lesson；
- current replacement；
- wiki page target；
- risk if misread。

## 8. 必须回答的问题

W4 报告和 wiki 更新后必须能回答：

- 哪些旧模型/策略路线已经被 strict E4 + current default strategy 替代。
- 哪些旧 Agent 路线已经被 DailyAgentPromptArtifact + backend simple-chat 替代。
- 哪些旧 frontend/monitor/ops 路线不再代表 `/tw-stock-monitor` 当前产品主线。
- 哪些 provider publish / accepted latest / scheduler 逻辑是 ops boundary，不是默认执行建议。
- 哪些 broker/quick-trade/live trading/credential 路线必须保持 forbidden boundary。
- 哪些历史实验收益不能作为当前产品证据。
- 当前项目最容易被后来执行者误读的历史文档有哪些。

## 9. Manifest / Index / Hot / Log 要求

W4 只要新增或更新正式 wiki 页面，就必须同步更新：

- `.manifest.json`
- `index.md`
- `hot.md`
- `log.md`

要求：

- manifest source key 使用绝对路径。
- manifest entry 包含 `content_hash`、`modified_at`、`size_bytes`、`pages_created`、`pages_updated`。
- `index.md` 必须加入 W4 work/report 和新增/更新的重要 historical/superseded 页面。
- `hot.md` 必须提示 W4 后“历史路线已降权，不代表当前默认路径”。
- `log.md` 必须追加可解析记录，例如 `INGEST phase="W4_HISTORY_LESSONS"`。

## 10. W4 执行报告格式

输出文件：

- `docs/project_wiki/FULL_INGEST_PHASEW4_HISTORY_LESSONS_REPORT_CN.md`

报告必须使用以下格式：

```markdown
# Project Wiki Full Ingest Phase W4 执行报告

## 1. 本阶段结论
## 2. 读取的 source 范围
## 3. 明确排除的 source 范围
## 4. 新增 / 更新的 wiki 页面
## 5. manifest / index / hot / log 更新
## 6. 当前事实与历史事实边界
## 7. 安全边界确认
## 8. 自检结果
## 9. 遗留问题
## 10. 请求审查者审查的问题
```

其中第 6 节必须包含分类表，第 8 节必须说明：

- 是否所有新增/更新页面都有 frontmatter、summary、sources 和正文 `## Sources`。
- 是否没有把 historical/superseded 写成 current。
- 是否没有把历史收益、旧 smoke、fixture/mock/dynamic payload 写成当前生产证据。
- 是否没有读取或复制任何 key、password、token、真实账户 payload。
- 是否只写入 `docs/project_wiki/**`。如果工作区已有产品代码脏变更，只描述本阶段计划写入范围和实际 wiki 页面变更，不要声称全局 git status 只包含 `docs/project_wiki`。

## 11. 审查阻塞条件

如果出现以下任一情况，审查者应阻塞 W4：

- 把历史失败路线写成当前路线。
- 把旧 Agent/tool route 写成当前 Agent 主线。
- 把旧 monitor/ops UI 写成当前 frontend 主线。
- 把 broker/order/quick-trade/live trading/credential 写成允许能力。
- 把 target position / target weight 写成允许输出。
- 把 provider publish / accepted latest switch 写成默认执行建议。
- 把历史实验收益、旧 smoke、测试 fixture、mock 或 dynamic payload 写成当前生产证据。
- 泄漏 OpenAI key、密码、token、Authorization header 或真实账户信息。
- manifest 缺 hash/mtime/size，或 source key 不是绝对路径。
- 新增页面大量缺 frontmatter、summary、sources 或正文 `## Sources`。

## 12. 给执行者的启动指令

```text
你是执行者。请启动 Project Wiki Full Ingest 支线 Phase W4，只做历史路线和弯路归档。必须严格对照 docs/project_wiki/FULL_INGEST_PHASEW4_HISTORY_LESSONS_WORK_CN.md 和 docs/project_wiki/PROJECT_WIKI_FULL_INGEST_EXECUTION_AND_REVIEW_PLAN_CN.md。选择性读取 docs/tw_ltr_*、docs/tw_decision_model*、docs/tw_orthogonal_*、docs/archive/、旧 phase 文档和 scripts/archive/**，只抽“为什么被替代”“当前替代方案是什么”“以后不要重复什么”。更新 synthesis/historical-lessons.md、synthesis/current-mainline-vs-superseded-routes.md、synthesis/project-risk-map.md，必要时新增少量 references/superseded-routes-*.md。输出 docs/project_wiki/FULL_INGEST_PHASEW4_HISTORY_LESSONS_REPORT_CN.md。严禁运行服务、测试、训练、日更、数据刷新、provider publish、accepted latest switch、monitor 写入、broker/order/quick-trade、target_position/target_weight、OpenAI smoke 或读取任何 key/password/token/真实账户信息。
```
