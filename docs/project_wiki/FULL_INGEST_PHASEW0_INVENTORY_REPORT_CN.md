---
title: Phasew0 Inventory Report
category: references
tags: [wiki, full-ingest, w0, report]
sources: []
summary: 范围地图和过滤规则的执行报告，作为项目 wiki 支线过程证据。
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

# Project Wiki Full Ingest Phase W0 执行报告

生成日期：2026-06-20

## 1. 本阶段结论

Phase W0 已完成范围地图和过滤规则设计。本阶段只读仓库源文件并新增本报告，未执行大规模 ingest，未创建或更新知识页，未更新 `.manifest.json`、`index.md`、`hot.md`、`log.md`，未运行服务、训练、日更、provider refresh/publish、accepted latest switch、monitor、broker/order 或任何 target position / target weight 写入。

当前 `docs/project_wiki` 是唯一允许写入的 vault。现有 seed vault 状态为：

- manifest version：`1`
- manifest sources：`16`
- manifest total_pages：`15`
- project：`taiwan-stock-quant-platform`
- 现有页面类型：project overview、4 个 concepts、3 个 skills、2 个 references、README/index/log/hot/taxonomy

本仓库不适合直接全仓 ingest。默认排除目录已观测到约 `98,793` 个文件；二进制、表格、截图、PDF 等高风险/低价值扩展名约 `55,194` 个文件。后续必须继续采用“编译，不搬运”的分阶段路线。

## 2. 读取的 source 范围

本阶段读取或扫描了以下范围：

- `docs/project_wiki/PROJECT_WIKI_FULL_INGEST_EXECUTION_AND_REVIEW_PLAN_CN.md`
- `/home/chuliyang/.codex/skills/llm-wiki/SKILL.md`
- `/home/chuliyang/.codex/skills/wiki-status/SKILL.md`
- `/home/chuliyang/.codex/skills/wiki-ingest/SKILL.md`
- `/home/chuliyang/.codex/skills/wiki-lint/SKILL.md`
- `/home/chuliyang/.codex/skills/wiki-query/SKILL.md`
- `docs/project_wiki/.manifest.json`
- `docs/project_wiki/index.md`
- `docs/project_wiki/log.md`
- 仓库目录地图：`docs/`、`configs/`、`.agents/skills/`、`backend/app/routes`、`backend/app/services`、`frontend/src/views/tw-stock-monitor`、`frontend/src/api`、`scripts/`、`tests/`、`frontend/tests/`、`crawler/scrapling_handoff/`、`qlib_pipeline/`

分层候选统计如下：

| Tier | 范围 | 预计 ingest/编译文件数 | 处理策略 |
|---|---:|---:|---|
| Tier A | `docs/tw_modular_contracts`、`configs`、`.agents/skills/tw-stock-*` | 约 85 | W1 核心合同与 skill 编译主源 |
| Tier B | 产品化路线文档、crawler handoff、qlib extension/config/example、backend/frontend tests | 约 323 | W2/W3 选择性编译 |
| Tier C | archive、LTR/decision/orthogonal 历史路线、`scripts/archive` | 约 629 | W4 只抽历史教训 |
| Tier D | 数据、缓存、构建产物、日志、node_modules、mlruns、tmp、home 镜像等 | 约 98,793 | 默认不 ingest |
| 代码映射补充 | backend routes/services、frontend workbench/API、scripts 顶层、tests | 约 285 | W3 源码到知识页关系图 |

关键分项：

- `docs/tw_modular_contracts`：48 个文件
- `configs`：16 个文件
- `.agents/skills/tw-stock-*`：21 个文件
- `docs/tw_agent_daily_prompt_rebuild`、`docs/tw_modular_daily_update_productization`、`docs/tw_new_model_strategy_pre_rnd`、`docs/tw_skills_maintenance`：104 个文件
- `backend/app/routes`、`backend/app/services`、`frontend/src/views/tw-stock-monitor`、`frontend/src/api`：185 个非 pycache 文件
- `scripts` 顶层：59 个文件

## 3. 明确排除的 source 范围

默认排除目录：

```text
.git/
node_modules/
frontend/node_modules/
frontend/dist/
__pycache__/
.pytest_cache/
logs/
backend/logs/
tmp/
mlruns/
qlib_pipeline/mlruns/
home/
tools/*/node_modules/
tools/*/.git/
```

默认排除或只做 manifest/source reference 的文件类型：

```text
*.bin
*.pkl
*.parquet
*.sqlite
*.db
*.csv
*.tsv
*.png
*.jpg
*.jpeg
*.webp
*.gif
*.pdf
*.log
*.pyc
```

默认只抽 schema、manifest 结构、代表性样本和路径语义，不编译原始数据正文：

```text
data_tw/artifacts/
data_tw/experiments/
qlib_pipeline/data_tw/
data_tw/golden_samples/
data_tw/ops/
```

敏感或会误导当前事实的内容处理：

- broker、quick-trade、orders、live trading、credentials、OpenAI adapter 相关源码只在 W3 做边界识别，不作为允许能力写入 wiki。
- `provider publish`、`accepted latest switch`、真实 provider refresh、monitor scan/alert 只作为禁区或历史事实记录，不作为可默认执行路径。
- fixtures、动态 payload、历史 replay output 不可当生产 artifact。

## 4. 新增 / 更新的 wiki 页面

本阶段只新增：

- `docs/project_wiki/FULL_INGEST_PHASEW0_INVENTORY_REPORT_CN.md`

本阶段未新增或更新 `concepts/`、`skills/`、`references/`、`synthesis/`、`projects/` 下的知识页。

## 5. manifest / index / hot / log 更新

本阶段没有更新以下文件：

- `docs/project_wiki/.manifest.json`
- `docs/project_wiki/index.md`
- `docs/project_wiki/hot.md`
- `docs/project_wiki/log.md`

原因：W0 是范围地图和过滤规则，不是 ingest 阶段。待 W1 正式编译知识页后，再按 `wiki-ingest` 规则写入 manifest 绝对路径 source key、`content_hash`、`pages_created`、`pages_updated`，并同步 index/hot/log。

## 6. 当前事实与历史事实边界

当前事实优先进入 W1/W2/W3：

- 模块化 artifact 合同链路：DataSource、FeatureArtifact、ModelSignalArtifact、StrategyRule、OrderIntentArtifact、ReplayResultArtifact、ReadonlyStrategySnapshot、DailyAgentPromptArtifact。
- 只读安全边界：readonly candidate/context/replay/snapshot/Agent answer，不允许 broker/order/quick-trade/target_position/target_weight。
- 当前主线入口：product artifact registry、strategy dependency、replay policy、readonly API、Agent simple-chat、frontend strategy workbench。
- 新模型/新策略 onboarding workflow：registry、golden sample、validator、OOS evidence、readonly dry-run。

历史事实只进入 W4：

- `docs/tw_ltr_*`
- `docs/tw_decision_model*`
- `docs/tw_orthogonal_*`
- `docs/archive/phase_history/*`
- `scripts/archive/historical_research/*`

历史内容只抽取“为什么被替代、当前替代方案是什么、以后不要重复什么”，目标页限定为：

- `synthesis/historical-lessons.md`
- `synthesis/current-mainline-vs-superseded-routes.md`
- `synthesis/project-risk-map.md`

## 7. 安全边界确认

本阶段确认以下红线继续有效：

- 不读取 OpenAI key、密码、token、真实账户信息。
- 不运行 OpenAI smoke，不访问真实 LLM provider。
- 不触发真实数据拉取、provider refresh、provider publish。
- 不切换 accepted latest、latest/default pointer。
- 不运行 monitor scan、alerts、daily auto-update。
- 不训练模型，不生成策略 artifact，不发布 readonly snapshot。
- 不调用 broker、quick-trade、order、target_position、target_weight 写入。
- 不把 readonly candidate 或 Agent 回答写成交易建议。

## 8. 自检结果

W0 自检：

- 已读取计划文档和要求的 5 个 wiki companion skills。
- 已确认 vault 路径固定为 `docs/project_wiki`。
- 已确认 seed manifest 为官方 version=1 结构，并使用绝对路径 source key。
- 已识别 Tier A/B/C/D 范围与预计文件数。
- 已明确 ignore patterns。
- 已识别大文件/数据/缓存/构建产物风险。
- 已区分当前主线与历史/弃用路线。
- 已保持只读仓库源文件，只写本 W0 报告。

未执行：

- 未运行 wiki ingest。
- 未运行 wiki lint 写入修复。
- 未运行服务、测试、训练、数据刷新或网络调用。

## 9. 遗留问题

- W1 需要审查者先确认 Tier A 首批 source list 是否完整，尤其是合同、registry、strategy dependency、skill 之间是否还有漏项。
- W2 需要对 product route 文档做“最终结论优先”的筛选，避免把中间失败状态写入当前事实。
- W3 需要更细地拆分 backend route/service：只读路线、Agent simple-chat、daily prompt、artifact registry、paper portfolio、sim account、legacy/live trading 边界。
- W4 需要专门处理历史路线，避免历史 LTR/decision/orthogonal 结论污染当前默认路径。
- 需要在 W1 后做一次 wiki health audit，检查 frontmatter、summary、sources、broken wikilinks 和 manifest hash/mtime/size。

## 10. 请求审查者审查的问题

请审查者重点确认：

1. Tier A 是否应作为 W1 唯一首批 ingest 主源。
2. `configs/tw_product_artifact_registry.yaml`、`configs/tw_modular_registry.yaml`、`configs/data_source_registry.yaml`、`configs/tw_replay_window_policy.yaml`、`configs/strategy_dependencies/*.yaml` 是否均应进入 W1。
3. `.agents/skills/tw-stock-*` 下的 references/scripts 是否在 W1 编译 skill 页面时一并读取，还是先只读 `SKILL.md`。
4. `backend/app/services/*live_trading*`、`quick_trade`、`credentials`、`broker` 相关文件在 W3 是否仅作为禁区/边界 source，不进入能力说明。
5. `data_tw/golden_samples` 是否在 W1/W3 只抽代表性 schema，不纳入大规模 ingest。

## 11. 首批 ingest source list 建议

建议 W1 首批 source 限定为以下当前主线文件，不扩展到历史 phase report：

```text
docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md
docs/tw_modular_contracts/TW_MODULAR_PIPELINE_FUTURE_DEVELOPMENT_GUIDE_CN.md
docs/tw_modular_contracts/TW_PROJECT_MODULE_MAP_AND_FLOW_CN.md
docs/tw_modular_contracts/DATA_SOURCE_CONTRACT_CN.md
docs/tw_modular_contracts/FEATURE_ARTIFACT_CONTRACT_CN.md
docs/tw_modular_contracts/MODEL_SIGNAL_CONTRACT_CN.md
docs/tw_modular_contracts/STRATEGY_RULE_CONTRACT_CN.md
docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md
docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md
docs/tw_modular_contracts/READONLY_STRATEGY_SNAPSHOT_CONTRACT_CN.md
docs/tw_modular_contracts/TW_AGENT_DAILY_PROMPT_ARTIFACT_CONTRACT_CN.md
docs/tw_modular_contracts/AGENT_READONLY_CONTEXT_CONTRACT_CN.md
docs/tw_modular_contracts/FRONTEND_READONLY_DISPLAY_CONTRACT_CN.md
docs/tw_modular_contracts/FRONTEND_AGENT_PANEL_CONTRACT_CN.md
docs/tw_modular_contracts/DAILY_ORCHESTRATOR_CONTRACT_CN.md
docs/tw_modular_contracts/AUTO_UPDATE_ORCHESTRATOR_CONTRACT_CN.md
docs/tw_modular_contracts/STRATEGY_DEPENDENCY_CONTRACT_CN.md
docs/tw_modular_contracts/RUN_REGISTRY_CONTRACT_CN.md
docs/tw_modular_contracts/TW_CURRENT_STRATEGY_CONTEXT_API_FIELD_DICTIONARY_CN.md
docs/tw_modular_contracts/NEW_MODEL_AND_STRATEGY_DEVELOPER_GUIDE_CN.md
configs/tw_product_artifact_registry.yaml
configs/tw_modular_registry.yaml
configs/data_source_registry.yaml
configs/price_store_registry.yaml
configs/tw_replay_window_policy.yaml
configs/tw_modular_replay_matrix.yaml
configs/feature_registry.yaml
configs/model_onboarding_templates/model_signal_m2_template.yaml
configs/strategy_dependencies/m2_strategy_dependency_template.yaml
configs/strategy_dependencies/one_sell_one_buy_correct.yaml
configs/strategy_dependencies/top50_exit_one_worst_sell.yaml
.agents/skills/tw-stock-new-model-onboarding/SKILL.md
.agents/skills/tw-stock-new-strategy-onboarding/SKILL.md
.agents/skills/tw-stock-readonly-e2e-acceptance/SKILL.md
.agents/skills/tw-stock-frontend-workbench-ux-review/SKILL.md
.agents/skills/tw-stock-data-freshness-diagnosis/SKILL.md
.agents/skills/tw-stock-research-context-analyst/SKILL.md
.agents/skills/tw-stock-agent-daily-prompt-maintenance/SKILL.md
.agents/skills/tw-stock-modular-integration-regression/SKILL.md
.agents/skills/tw-stock-safety-boundary-review/SKILL.md
```

W1 目标不是逐文件建 reference，而是合并更新或创建：

- `concepts/modular-artifact-chain.md`
- `concepts/readonly-safety-boundary.md`
- `concepts/product-artifact-registry.md`
- `concepts/current-default-model-and-strategy.md`
- `concepts/agent-daily-prompt-route.md`
- `concepts/frontend-strategy-workbench.md`
- `concepts/data-freshness-and-latest-pointers.md`
- `skills/new-model-onboarding-workflow.md`
- `skills/new-strategy-onboarding-workflow.md`
- `skills/readonly-e2e-acceptance-workflow.md`
- `skills/frontend-ux-review-workflow.md`
- `skills/data-freshness-diagnosis-workflow.md`
- `skills/safety-boundary-review-workflow.md`
- `skills/modular-integration-regression-workflow.md`
