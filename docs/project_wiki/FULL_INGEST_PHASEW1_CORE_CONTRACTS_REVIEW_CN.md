---
title: Phasew1 Core Contracts Review
category: references
tags: [wiki, full-ingest, w1, review]
sources: []
summary: 核心合同、配置和 skills 编译的审查报告，作为项目 wiki 支线过程证据。
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

# Project Wiki Full Ingest Phase W1 审查报告

生成日期：2026-06-20

## 1. 审查结论

Phase W1 审查结论：有条件通过，允许进入 W2，但必须先完成一个 W1 follow-up 修复。

执行者围绕 `docs/tw_modular_contracts/*.md`、`configs/**`、`.agents/skills/tw-stock-*` 完成了核心 contract/config/skill 知识编译，新增/更新了核心 concepts/skills 页面，并同步更新了 `.manifest.json`、`index.md`、`hot.md`、`log.md`。抽查显示当前默认产品路径、strategy dependency 分类、Agent simple-chat 路线、四类 latest 边界和 readonly 安全边界基本准确。

主要问题是：W1 工作文档明确要求 `docs/tw_modular_contracts/templates/*.md` 必须被显式判定，但执行报告把 `docs/tw_modular_contracts/*.md` 的 39 个顶层文件当作全量范围，未覆盖 `templates/` 下 9 个模板文件。这正是 W0 review M1 中 48 个文件口径和 W1 报告 39 个文件口径的差异。该问题目前未污染正式知识页，但属于 W1 明确要求未闭环，必须在进入实质 W2 ingest 前补齐。

## 2. Critical Findings

无。

未发现以下阻塞项：

- 未把历史失败路线写成当前路线。
- 未把 readonly candidate 写成交易建议。
- 未把 `target_position` / `target_weight` 写入为允许输出。
- 未把 provider publish / accepted latest switch 写成默认执行路径。
- 未把动态 payload 或 fixture 当生产 artifact。
- 未泄漏 OpenAI key、密码、token 或真实账户信息。
- 未把 broker/order/quick-trade 写成当前能力入口。

## 3. High Findings

### H1. `docs/tw_modular_contracts/templates/*.md` 未按 W1 要求显式分流

证据：

- W1 工作文档要求至少显式判定 `docs/tw_modular_contracts/templates/*.md`。
- 当前文件系统中 `docs/tw_modular_contracts/` 共 48 个文件，其中顶层 39 个、`templates/` 下 9 个。
- W1 执行报告写明“`docs/tw_modular_contracts/*.md`：当前文件系统枚举共 39 个文件，全部分类”，并将 39 个顶层文件作为 M1 全量范围。
- `.manifest.json` 和 W1 报告中未见 `docs/tw_modular_contracts/templates/EXECUTION_REPORT_TEMPLATE_CN.md`、`NEW_*_WORK_TEMPLATE_CN.md`、`REVIEW_REPORT_TEMPLATE_CN.md` 的 source entry 或分类说明。

影响：

- W0 review M1 的“全量合同面显式判定”没有完全闭环。
- 这些模板不一定需要编译成正式知识页，但它们定义执行/审查/新模块工作模板，至少应作为 workflow 支撑或排除项被记录。

修复要求：

- 补充读取或枚举 `docs/tw_modular_contracts/templates/*.md`。
- 在 W1 follow-up 中逐项分类为“workflow template/supporting source/排除”，说明是否影响现有 skills 页面。
- 如模板对 onboarding/review workflow 有稳定规则，更新对应 skills 页面；如不影响，明确记录“不更新正式页面，仅作为 source 备案”。
- 同步更新 `.manifest.json`、`log.md`，必要时更新 `index.md`/`hot.md`。
- 输出 `docs/project_wiki/FULL_INGEST_PHASEW1_CORE_CONTRACTS_FOLLOWUP_CN.md`。

## 4. Medium Findings

### M1. W1 报告格式未完全使用总计划标准标题

总计划要求阶段报告使用固定 10 节标题。W1 报告包含核心内容，但标题与顺序不完全一致，例如使用“结论”“已读取来源范围”“排除来源范围”等。

影响较低，不阻塞 W2；后续阶段必须严格使用总计划固定格式，避免审查遗漏。

### M2. Manifest 抽查受限于沙箱，未完成完整 JSON 程序化校验

Python JSON 解析命令在当前沙箱触发 `bwrap: loopback: Failed RTM_NEWADDR`，未能完成程序化全量校验。文本抽查显示 `.manifest.json` 为 version 1，source key 为绝对路径，W1 source entry 包含 `content_hash`、`modified_at`、`size_bytes`、`pages_created`、`pages_updated`。

W1 follow-up 或 W2 前建议由执行者用可用环境运行一次 JSON parse / schema check，或在报告中给出等价的只读校验证据。

## 5. Low Findings

### L1. 部分 manifest entry 把阶段报告列入 `pages_updated`

W1 manifest 中大量 source entry 的 `pages_updated` 包含 `FULL_INGEST_PHASEW1_CORE_CONTRACTS_REPORT_CN.md`。这可解释为 source 贡献了阶段报告，但长期看会让 manifest 的 source-to-knowledge-page 映射变得偏噪。

建议：后续 manifest 中可以保留 report provenance，但正式知识页映射应优先指向 concepts/skills/references/projects 页面；阶段报告最好单独作为 ingest report source 或 operation artifact 管理。

### L2. project overview 尚未显式加入 W1 新核心页面

`projects/taiwan-stock-quant-platform/taiwan-stock-quant-platform.md` 仍主要链接 seed 页和 pre-RND skill，未明显加入 W1 新增的 `product-artifact-registry`、`current-default-model-and-strategy`、`frontend-strategy-workbench`、`data-freshness-and-latest-pointers` 等关键页面。

建议在 W1 follow-up 或 W2 开始时更新 project overview，让它成为当前主线入口。

## 6. Wiki 结构与链接审查

W1 新增页面抽查存在，且 index 已覆盖：

- `concepts/product-artifact-registry.md`
- `concepts/current-default-model-and-strategy.md`
- `concepts/frontend-strategy-workbench.md`
- `concepts/data-freshness-and-latest-pointers.md`
- `skills/readonly-e2e-acceptance-workflow.md`
- `skills/frontend-ux-review-workflow.md`
- `skills/data-freshness-diagnosis-workflow.md`
- `skills/safety-boundary-review-workflow.md`
- `skills/modular-integration-regression-workflow.md`

已更新页面抽查存在：

- `concepts/modular-artifact-chain.md`
- `concepts/readonly-safety-boundary.md`
- `concepts/agent-daily-prompt-route.md`
- `skills/new-model-onboarding-workflow.md`
- `skills/new-strategy-onboarding-workflow.md`

页面质量抽查：

- 抽查 `concepts/product-artifact-registry.md`、`concepts/current-default-model-and-strategy.md`，frontmatter 包含 `title`、`category`、`tags`、`sources`、`summary`、`base_confidence`、`lifecycle`、`lifecycle_changed`、`tier`。
- 页面包含 `## Sources`。
- 页面之间使用 Obsidian wikilinks，核心链接目标在当前 vault 中存在。
- `index.md` 和 `hot.md` 已更新 W1 主线。
- `log.md` 已追加 W1 ingest 记录。

未发现大量断链或缺 frontmatter 的证据。

## 7. 当前事实 / 历史事实边界审查

W1 当前事实边界基本合格：

- 当前 product profile：`strict_e4_yz_product`。
- 当前 base model：`e4_frozen_qlib_2018_2022`。
- 当前 treatment model：`e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025`。
- 当前 display alias：`e4_frozen_qlib_2023_2025_ltr`。
- 当前默认策略：`top50_exit_one_worst_sell`。
- 当前 candidate boundary：`qlib_top50`。
- 当前 ranking：`ltr_rerank_within_qlib_top50`。
- 当前 execution price mode：`next_open`。

strategy dependency 分类清楚：

- `top50_exit_one_worst_sell.yaml` 是 current product default。
- `one_sell_one_buy_correct.yaml` 是 research-only candidate。
- `one_sell_one_buy_buggy_e8r.yaml` 是 diagnostic-only。
- `original.yaml`、`top50_exit_all.yaml` 是 deprecated/historical。
- `m2_strategy_dependency_template.yaml`、`dummy_new_strategy_dependency_smoke.yaml`、`sector_extension_analysis_smoke.yaml` 未被写成默认策略。

未发现历史/smoke/buggy 配置污染当前默认路径。

## 8. 安全边界审查

W1 安全边界合格。

抽查页面明确禁止：

- provider refresh / publish。
- accepted latest switch。
- monitor write。
- broker、quick-trade、order、place order、submit order。
- `target_position`、`target_weight`、目标仓位、目标权重。
- frontend OpenAI direct call、OpenAI key/base URL/bearer token 暴露。
- 训练、真实 OpenAI smoke、生产 default/latest 切换。

Agent 路线保持为：

```text
DailyAgentPromptArtifact -> backend simple-chat -> /api/tw-stock/agent/simple-chat -> frontend readonly explanation
```

并明确 `POST /api/tw-stock/agent/simple-chat` 只是后端只读解释路径，不等价于交易、调仓、数据刷新或前端直连 OpenAI。

四类 latest 被明确拆分：

- provider raw/latest
- qlib accepted latest
- readonly strategy snapshot latest
- Agent DailyAgentPromptArtifact latest

未发现把任一 latest 混同为另一个 latest 的问题。

## 9. 是否允许进入下一阶段

有条件允许进入 W2。

条件：执行者必须先完成 W1 follow-up，补齐 `docs/tw_modular_contracts/templates/*.md` 的显式分流与 manifest/log 记录。该 follow-up 不需要重做 W1，只需关闭 H1。

W2 可以在 follow-up 完成后启动。

## 10. 下一阶段工作文档或修复要求

### W1 Follow-up 修复要求

执行者下一步先执行：

```text
你是执行者。请先完成 Phase W1 follow-up 修复，不进入 W2 正式 ingest。只处理 docs/tw_modular_contracts/templates/*.md 未显式分流的问题：读取或枚举 templates 下 9 个模板文件，逐项分类为 workflow template/supporting source/排除，判断是否影响现有 onboarding/review workflow 页面；如影响则只更新 docs/project_wiki 下对应 skills 页面，如不影响则记录不更新正式页面。必须同步 .manifest.json 和 log.md，必要时更新 index.md/hot.md。输出 docs/project_wiki/FULL_INGEST_PHASEW1_CORE_CONTRACTS_FOLLOWUP_CN.md。严禁改产品代码、运行服务、刷新数据、provider publish、accepted latest、monitor、broker/order、target_position/target_weight、训练模型或真实 OpenAI smoke。
```

### W2 执行文档要求

W2 正式工作文档应在 follow-up 通过后下发，主线应覆盖：

- `docs/tw_agent_daily_prompt_rebuild/`
- `docs/tw_modular_daily_update_productization/`
- `docs/tw_new_model_strategy_pre_rnd/`
- `docs/tw_skills_maintenance/`

W2 必须坚持“最终结论优先”，不得把失败中间态、accepted-with-conditions 或历史修复过程写成当前默认事实。Agent 必须保持 DailyAgentPromptArtifact + backend simple-chat，前端必须保持 readonly strategy workbench，不得引入 broker/quick-trade/order。
