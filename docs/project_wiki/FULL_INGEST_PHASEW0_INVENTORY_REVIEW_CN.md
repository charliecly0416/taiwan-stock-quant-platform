---
title: Phasew0 Inventory Review
category: references
tags: [wiki, full-ingest, w0, review]
sources: []
summary: 范围地图和过滤规则的审查报告，作为项目 wiki 支线过程证据。
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

# Project Wiki Full Ingest Phase W0 审查报告

生成日期：2026-06-20

## 1. 审查结论

Phase W0 审查结论：有条件通过，允许进入 W1。

执行者的 W0 报告基本符合 `PROJECT_WIKI_FULL_INGEST_EXECUTION_AND_REVIEW_PLAN_CN.md` 对范围地图和过滤规则的要求：已明确 Tier A/B/C/D、预计文件数、ignore patterns、首批 ingest source list、风险和安全边界；未执行大规模 ingest；未更新 `.manifest.json`、`index.md`、`hot.md`、`log.md`；未创建或更新正式知识页；写入范围仅限 `docs/project_wiki/FULL_INGEST_PHASEW0_INVENTORY_REPORT_CN.md`。

本阶段未发现必须阻塞 W1 的 Critical 问题。但 W1 启动前必须修正首批 source 覆盖口径：W0 建议的 Tier A 首批清单对 `docs/tw_modular_contracts/` 不是完整当前合同面，漏掉若干仍应进入 W1 研判的合同、扩展、模板和 reviewer checklist 文件。该问题不否定 W0 的范围地图，但如果不修正，会导致 W1 核心合同编译先天缺页。

## 2. Critical Findings

无。

未发现以下阻塞项：

- 未把历史失败路线写成当前路线。
- 未把 readonly candidate 写成交易建议。
- 未把 `target_position` / `target_weight` 写成允许输出。
- 未把 provider publish / accepted latest switch 写成默认执行路径。
- 未把动态 payload 或 fixture 当生产 artifact。
- 未泄漏 OpenAI key、密码、token、真实账户信息。
- 未改动 manifest，因此不存在本阶段新增 manifest key/hash/mtime/size 错误。
- 未新增正式知识页，因此不存在本阶段新增断链或 frontmatter 缺失。

## 3. High Findings

无阻塞性 High Finding。

## 4. Medium Findings

### M1. W1 首批 `docs/tw_modular_contracts/` source list 不够完整

W0 报告将 `docs/tw_modular_contracts` 统计为 48 个文件，但 W1 首批 ingest source list 只列入其中约 20 个顶层合同文件。抽查确认目录中还有多个可能属于当前合同面或 W1 编译前置语义的文件未进入首批建议清单，例如：

- `ANALYSIS_ARTIFACT_CONTRACT_CN.md`
- `DATA_INGESTION_ARTIFACT_CONTRACT_CN.md`
- `DEFAULT_CANDIDATE_DECISION_CONTRACT_CN.md`
- `EXTENSIBLE_CONTRACT_CAPABILITY_DESIGN_CN.md`
- `FULL_RANK_CONTRACT_CN.md`
- `MODEL_SIGNAL_EXTENSION_SCHEMA_CN.md`
- `PRICE_STORE_CONTRACT_CN.md`
- `READONLY_REPLAY_WINDOW_PRODUCTIZATION_GUIDE_CN.md`
- `NEW_MODEL_REVIEWER_CHECKLIST_CN.md`
- `NEW_STRATEGY_REVIEWER_CHECKLIST_CN.md`
- `TW_DAILY_AUTO_UPDATE_RUNBOOK_CN.md`
- `TW_DEVELOPER_TEST_AND_EXPERIMENT_PLAYBOOK_CN.md`
- `TW_NEW_STRATEGY_ONBOARDING_TEMPLATE_CN.md`
- `docs/tw_modular_contracts/templates/*.md`

修复要求：W1 执行者不要机械照抄 W0 的首批清单。W1 开始时应先把 `docs/tw_modular_contracts/` 全量顶层文件和 `templates/` 分成三类：必须编译、只作为 workflow/source 支撑、历史/验收参考。至少上述文件必须被显式判定是否纳入 W1 source，而不是静默遗漏。

### M2. W1 对 `.agents/skills/tw-stock-*` references/scripts 的读取策略仍未定案

W0 报告正确提出了问题：编译 skill 页面时，是只读 `SKILL.md`，还是一并读取 skill references/scripts。当前仓库内 `.agents/skills/tw-stock-*` 抽查显示仅有 9 个 `SKILL.md`，未发现同级 references/scripts；但 W1 仍应按 skill 规则确认每个 `SKILL.md` 是否引用相对路径。

修复要求：W1 读取每个 tw-stock skill 时，如果 `SKILL.md` 明确引用相对路径，必须按技能规则读取必要文件；如果没有引用，则记录“无额外 references/scripts”。不要把未读取的隐含文件当作已覆盖证据。

## 5. Low Findings

### L1. Tier B/W3 代码映射统计应排除 `__pycache__` 后再报数

W0 报告声明 backend/frontend route/service 统计为非 pycache 文件，这个方向正确。后续 W3 报告应继续用显式排除 `__pycache__`、`.pyc` 的命令或清单作为证据，避免把缓存文件混入代码映射计数。

### L2. 历史路线目录命名需要在 W4 前再次核对

W0 对历史路线的处理原则正确，但 W4 前需要用实际目录清单确认 `docs/tw_ltr_*`、`docs/tw_decision_model*`、`docs/tw_orthogonal_*`、`docs/archive/` 和 `scripts/archive/` 是否覆盖全部 superseded 路线。W0 阶段可不阻塞。

## 6. Wiki 结构与链接审查

本阶段只新增 W0 执行报告：

- `docs/project_wiki/FULL_INGEST_PHASEW0_INVENTORY_REPORT_CN.md`

抽查 `docs/project_wiki` 当前结构仍保持 seed vault 形态，包含：

- `.manifest.json`
- `index.md`
- `hot.md`
- `log.md`
- `_meta/taxonomy.md`
- `projects/taiwan-stock-quant-platform/taiwan-stock-quant-platform.md`
- 既有 `concepts/`、`skills/`、`references/`

W0 未新增正式 knowledge page，因此本阶段不要求更新 index/hot/log/manifest。该处理符合计划文档对 W0 的定义。

## 7. 当前事实 / 历史事实边界审查

W0 报告正确区分：

- 当前主线：模块化 artifact 合同链路、只读安全边界、product artifact registry、strategy dependency、replay policy、readonly API、Agent simple-chat、frontend strategy workbench、新模型/新策略 onboarding。
- 历史路线：`docs/tw_ltr_*`、`docs/tw_decision_model*`、`docs/tw_orthogonal_*`、`docs/archive/phase_history/*`、`scripts/archive/historical_research/*`。

审查判断：当前事实与历史事实未混写。W1/W2 必须继续执行“最终结论优先”，不得把 phase 中间失败状态或 accepted-with-conditions 写成 unconditional accepted。

## 8. 安全边界审查

W0 报告明确保留以下红线，符合总计划：

- 不读取 OpenAI key、密码、token、真实账户信息。
- 不运行 OpenAI smoke，不访问真实 LLM provider。
- 不触发真实数据拉取、provider refresh、provider publish。
- 不切换 accepted latest、latest/default pointer。
- 不运行 monitor scan、alerts、daily auto-update。
- 不训练模型，不生成策略 artifact，不发布 readonly snapshot。
- 不调用 broker、quick-trade、order、`target_position`、`target_weight` 写入。
- 不把 readonly candidate 或 Agent 回答写成交易建议。

对 W3 的安全要求：`backend/app/services/*live_trading*`、`quick_trade`、`credentials`、`broker`、OpenAI adapter 相关文件只能作为禁区/边界 source，不得编译为“项目能力入口”或默认 workflow。

## 9. 是否允许进入下一阶段

允许进入 W1。

进入 W1 的条件是：执行者必须把本审查报告的 M1/M2 作为 W1 开工前修正要求，而不是等 W1 结束后补救。

## 10. 下一阶段工作文档或修复要求

W1 执行者必须按以下要求推进：

1. W1 主源仍以 `docs/tw_modular_contracts/`、`configs/`、`.agents/skills/tw-stock-*` 为核心，不扩展到历史 phase report。
2. 在读取合同前，先输出或在 W1 报告中记录 `docs/tw_modular_contracts/` 全量文件分流结果：必须编译、支撑读取、历史/验收参考、排除。
3. `configs/` 中以下文件必须进入 W1：`tw_product_artifact_registry.yaml`、`tw_modular_registry.yaml`、`data_source_registry.yaml`、`price_store_registry.yaml`、`tw_replay_window_policy.yaml`、`tw_modular_replay_matrix.yaml`、`feature_registry.yaml`、`model_onboarding_templates/model_signal_m2_template.yaml`、`strategy_dependencies/m2_strategy_dependency_template.yaml`、`strategy_dependencies/one_sell_one_buy_correct.yaml`、`strategy_dependencies/top50_exit_one_worst_sell.yaml`。
4. 对 `strategy_dependencies/dummy_new_strategy_dependency_smoke.yaml`、`one_sell_one_buy_buggy_e8r.yaml`、`original.yaml`、`sector_extension_analysis_smoke.yaml`、`top50_exit_all.yaml` 做显式分类：当前默认、模板/示例、smoke、buggy、历史或不纳入。
5. 每个 `.agents/skills/tw-stock-* / SKILL.md` 必须读取；若它引用相对 references/scripts，按需读取并记录；若没有引用，明确记录无额外文件。
6. W1 生成或更新知识页时必须同步 `.manifest.json`、`index.md`、`hot.md`、`log.md`，manifest source key 必须为绝对路径，并包含 `content_hash`、`modified_at`、`size_bytes`、`pages_created`、`pages_updated`。
7. W1 知识页必须保留 readonly 安全边界，尤其是 Agent/simple-chat、OrderIntentArtifact、paper portfolio、sim account、replay 与 broker/order/quick-trade/target 写入之间的边界。
