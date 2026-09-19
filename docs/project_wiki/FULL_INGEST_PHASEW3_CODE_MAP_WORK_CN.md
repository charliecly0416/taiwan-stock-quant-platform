---
title: Phasew3 Code Map WORK
category: skills
tags: [wiki, full-ingest, w3, work]
sources: []
summary: 源码、脚本、测试和配置静态映射的工作文档，作为项目 wiki 支线过程证据。
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

# Project Wiki Full Ingest Phase W3 执行工作文档

生成日期：2026-06-20

## 1. 阶段目标

Phase W3 的目标是把源码、脚本、测试和配置映射到 W1/W2 已建立的 wiki 知识页。

W3 不是运行验收，不是训练模型，不是触发日更，不是刷新数据，也不是逐文件创建 reference。执行者必须只读分析当前代码形态，回答：

- backend route/service 分别对应哪些 wiki concepts。
- frontend workbench 组件和 API 的职责。
- scripts 中哪些是当前 product path、diagnostic、validator、builder、legacy 或 archive。
- tests 如何守住合同和只读安全边界。
- 代码中 live trading、broker、quick-trade、credentials、OpenAI adapter 等风险点如何作为 forbidden boundary，而不是当前台股能力入口。

本阶段完成后必须输出：

- `docs/project_wiki/FULL_INGEST_PHASEW3_CODE_MAP_REPORT_CN.md`

## 2. 必读前置文档

执行者开始 W3 前必须读取：

- `docs/project_wiki/PROJECT_WIKI_FULL_INGEST_EXECUTION_AND_REVIEW_PLAN_CN.md`
- `docs/project_wiki/FULL_INGEST_PHASEW1_CORE_CONTRACTS_REPORT_CN.md`
- `docs/project_wiki/FULL_INGEST_PHASEW1_CORE_CONTRACTS_REVIEW_CN.md`
- `docs/project_wiki/FULL_INGEST_PHASEW2_PRODUCT_ROUTES_REPORT_CN.md`
- `docs/project_wiki/FULL_INGEST_PHASEW2_PRODUCT_ROUTES_REVIEW_CN.md`
- `docs/project_wiki/FULL_INGEST_PHASEW2_PRODUCT_ROUTES_FOLLOWUP_REVIEW_CN.md`
- `docs/project_wiki/FULL_INGEST_PHASEW3_CODE_MAP_WORK_CN.md`
- `/home/chuliyang/.codex/skills/llm-wiki/SKILL.md`
- `/home/chuliyang/.codex/skills/wiki-ingest/SKILL.md`
- `/home/chuliyang/.codex/skills/wiki-lint/SKILL.md`
- `/home/chuliyang/.codex/skills/wiki-status/SKILL.md`

W3 必须以 W1/W2 事实为基准，不得重新打开默认模型、默认策略、Agent route 或 frontend route。

## 3. 允许写入范围

只允许写入：

- `docs/project_wiki/**`

允许更新：

- `docs/project_wiki/.manifest.json`
- `docs/project_wiki/index.md`
- `docs/project_wiki/hot.md`
- `docs/project_wiki/log.md`
- `docs/project_wiki/concepts/*.md`
- `docs/project_wiki/skills/*.md`
- `docs/project_wiki/references/*.md`
- `docs/project_wiki/synthesis/*.md`
- `docs/project_wiki/projects/taiwan-stock-quant-platform/**/*.md`
- `docs/project_wiki/FULL_INGEST_PHASEW3_CODE_MAP_REPORT_CN.md`

禁止修改产品源码、配置、脚本、测试、数据 artifact 和任何 `docs/project_wiki` 以外的文件。

## 4. 禁止事项

本阶段禁止：

- 运行 backend/frontend 服务
- 运行 Playwright 或 pytest 作为验收
- 真实数据拉取
- provider refresh / publish
- accepted latest switch
- monitor config / scan / alerts 写入
- broker / quick-trade / order 调用
- `target_position` / `target_weight` 写入
- 读取 OpenAI key、密码、token、真实账户信息
- 真实 OpenAI smoke
- 生产 latest/default 切换
- 训练模型
- 生成策略 artifact
- 发布 readonly snapshot
- 把测试 fixture 或动态 payload 当生产 artifact

W3 只读源码和文档，并写 `docs/project_wiki`。

## 5. W3 Source 范围

### 5.1 Backend route/service

重点只读分析：

- `backend/app/routes/tw_stock.py`
- `backend/app/routes/readonly_replay_window.py`
- `backend/app/routes/readonly_replay_window_index.py`
- `backend/app/routes/readonly_strategy_snapshot.py`
- `backend/app/services/tw_stock_agent_daily_prompt.py`
- `backend/app/services/tw_stock_agent_simple_chat.py`
- `backend/app/services/tw_stock_agent_guardrails.py`
- `backend/app/services/tw_stock_agent_openai.py`
- `backend/app/services/tw_stock_artifact_registry.py`
- `backend/app/services/tw_stock_current_strategy_context.py`
- `backend/app/services/tw_stock_daily_auto_update_status.py`
- `backend/app/services/readonly_replay_window.py`
- `backend/app/services/readonly_replay_window_index.py`
- `backend/app/services/readonly_strategy_snapshot.py`
- `backend/app/services/tw_stock_paper_portfolio.py`
- `backend/app/services/tw_stock_sim_account.py`

必须单独标记为 forbidden/boundary source，而不是能力入口：

- `backend/app/routes/quick_trade.py`
- `backend/app/routes/credentials.py`
- `backend/app/services/live_trading/**`
- `backend/app/services/*trading*`
- `backend/app/services/exchange_execution.py`
- `backend/app/services/trading_executor.py`

### 5.2 Frontend workbench/API

重点只读分析：

- `frontend/src/api/tw-stock.js`
- `frontend/src/views/tw-stock-monitor/index.vue`
- `frontend/src/views/tw-stock-monitor/components/*.vue`

必须确认：

- `/tw-stock-monitor` 仍是 readonly strategy workbench。
- Agent panel 只走 backend simple-chat。
- 前端不得直连 OpenAI。
- 前端不得引入 broker/order/quick-trade/target position/target weight。

### 5.3 Scripts

重点只读分类：

- `scripts/build_tw_agent_daily_prompt_artifact.py`
- `scripts/validate_tw_agent_daily_prompt_artifact.py`
- `scripts/validate_tw_modular_artifact_contract.py`
- `scripts/run_tw_modular_contract_regression.py`
- `scripts/run_daily_tw_stock_auto_update.py`
- `scripts/export_tw_qlib_normalized.py`
- `scripts/export_tw_current_market_symbols.py`
- `scripts/archive/**`
- 与 readonly snapshot、current strategy context、paper portfolio、sim account、agent prompt、validator、readiness 相关的 scripts。

分类必须包括：

- current product path
- validator
- builder
- diagnostic
- readonly dry-run
- legacy
- archive/historical
- forbidden runtime action

### 5.4 Tests

重点只读分析：

- `backend/tests/*tw_stock*`
- `backend/tests/test_tw_stock_agent_*`
- `tests/unit/*tw*`
- `frontend/tests/e2e/*tw-stock*`
- `frontend/tests/unit/*tw-stock*`

必须区分：

- contract/validator tests
- readonly E2E/static checks
- Agent simple-chat tests
- frontend network/console tests
- fixture / mock / synthetic data
- non-production evidence

测试 fixture、mock payload、dynamic payload 不得写成生产 artifact。

## 6. 目标 Wiki 页面

W3 应优先更新：

- `concepts/agent-daily-prompt-route.md`
- `concepts/frontend-strategy-workbench.md`
- `concepts/daily-update-data-flow.md`
- `concepts/data-freshness-and-latest-pointers.md`
- `concepts/modular-artifact-chain.md`
- `concepts/readonly-safety-boundary.md`
- `concepts/product-artifact-registry.md`
- `skills/readonly-e2e-acceptance-workflow.md`
- `skills/safety-boundary-review-workflow.md`
- `skills/modular-integration-regression-workflow.md`
- `skills/data-freshness-diagnosis-workflow.md`

W3 可新增：

- `references/code-map-backend-readonly-routes.md`
- `references/code-map-frontend-workbench.md`
- `references/code-map-scripts-and-tests.md`

W3 可更新：

- `synthesis/project-risk-map.md`
- `synthesis/current-mainline-vs-superseded-routes.md`

不要为每个源码文件单独建 reference。

## 7. 必须回答的问题

W3 报告和 wiki 更新后必须能回答：

- 当前 Agent simple-chat 后端入口和服务层是哪几个文件。
- DailyAgentPromptArtifact builder/validator 对应哪些脚本。
- `/tw-stock-monitor` 当前用哪些前端组件和 API。
- readonly replay/snapshot/current-strategy-context 对应哪些 route/service。
- paper portfolio / sim account 在代码中如何保持 simulated/readonly。
- 哪些脚本是 validator/builder/current product path，哪些是 diagnostic/legacy/archive。
- 哪些 tests 守住 forbidden request、Agent simple-chat、frontend readonly、contract validator。
- 哪些 live trading / quick-trade / credentials 文件只作为 forbidden boundary source。

## 8. Manifest / Index / Hot / Log 要求

W3 只要新增或更新正式 wiki 页面，就必须同步更新：

- `.manifest.json`
- `index.md`
- `hot.md`
- `log.md`

manifest 要求：

- `version` 保持 `1`
- source key 必须是绝对路径
- 每个 source entry 必须包含 `content_hash`
- 必须包含 `modified_at`
- 必须包含 `size_bytes`
- 必须包含 `pages_created`
- 必须包含 `pages_updated`
- `pages_created` / `pages_updated` 使用 vault-relative 路径

W3 开工时必须顺手补齐 `index.md` Phase Reports：

- `FULL_INGEST_PHASEW2_PRODUCT_ROUTES_REVIEW_CN.md`
- `FULL_INGEST_PHASEW2_PRODUCT_ROUTES_FOLLOWUP_CN.md`
- `FULL_INGEST_PHASEW2_PRODUCT_ROUTES_FOLLOWUP_REVIEW_CN.md`
- `FULL_INGEST_PHASEW3_CODE_MAP_WORK_CN.md`

## 9. W3 报告格式

执行者最终必须输出：

```markdown
# Project Wiki Full Ingest Phase W3 执行报告

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

报告还必须额外包含：

- backend route/service 映射表。
- frontend component/API 映射表。
- scripts 分类表。
- tests 分类表。
- forbidden boundary source 表。
- fixture/mock/dynamic payload 降权说明。

## 10. W3 通过门槛

审查者将在 W3 后检查：

- 是否误读 legacy 脚本为当前入口。
- 是否把测试 fixture 当真实生产数据。
- 是否遗漏 validator、golden sample、readonly E2E。
- 是否有敏感配置泄漏到 wiki。
- 是否把 live trading、broker、quick-trade、credentials 写成台股当前能力入口。
- 是否保留 Agent simple-chat 和 frontend readonly workbench 路线。
- 是否更新 manifest/index/hot/log。

若出现总计划列出的阻塞项，W3 不得通过。

## 11. 给执行者的启动命令

```text
你是执行者。请启动 Project Wiki Full Ingest 支线 Phase W3，只读分析源码、脚本、测试和配置，建立代码到 wiki 知识页的关系。必须读取 docs/project_wiki/PROJECT_WIKI_FULL_INGEST_EXECUTION_AND_REVIEW_PLAN_CN.md、W1/W2 执行与审查报告、docs/project_wiki/FULL_INGEST_PHASEW3_CODE_MAP_WORK_CN.md、/home/chuliyang/.codex/skills/llm-wiki/SKILL.md、/home/chuliyang/.codex/skills/wiki-ingest/SKILL.md、/home/chuliyang/.codex/skills/wiki-lint/SKILL.md、/home/chuliyang/.codex/skills/wiki-status/SKILL.md。只允许写 docs/project_wiki。不得运行服务、测试、训练、数据刷新、provider publish、accepted latest、monitor、broker/order、target_position/target_weight、OpenAI smoke 或生成策略 artifact。必须输出 backend route/service 映射表、frontend component/API 映射表、scripts 分类表、tests 分类表、forbidden boundary source 表，并输出 docs/project_wiki/FULL_INGEST_PHASEW3_CODE_MAP_REPORT_CN.md。
```
