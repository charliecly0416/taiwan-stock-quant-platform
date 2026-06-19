# Phase R0 审查与 R1 放行建议

生成日期：2026-06-16

## 1. 审查结论

本次 R0 不建议放行进入 R1。

理由：

- 四份最小 contract 文件已经存在，且 ModelSignal / StrategyRule / OrderIntent 的核心语义基本完整；
- 但当前工作区混入了 R0 明确禁止的前端和日更脚本改动；
- ReplayResult contract 与 R0-R2 工作文档要求的必需审计产物不完全一致；
- R0 执行报告声明“未修改前端”“未修改日更脚本”，与实际 diff 不一致。

在修复上述问题前，不能进入 R1 legacy signal adapter。

## 2. 审查对象

工作文档：

```text
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER0_R2_MODULAR_DECOUPLED_REFACTOR_WORK_CN.md
```

执行报告：

```text
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER0_MINIMAL_CONTRACT_EXECUTION_REPORT_CN.md
```

R0 contract：

```text
docs/tw_modular_contracts/MODEL_SIGNAL_CONTRACT_CN.md
docs/tw_modular_contracts/STRATEGY_RULE_CONTRACT_CN.md
docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md
docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md
```

实际工作区额外变更：

```text
frontend/src/views/tw-stock-monitor/index.vue
scripts/run_daily_tw_stock_auto_update.py
```

## 3. 通过项

### 3.1 四份 contract 存在

`docs/tw_modular_contracts/` 下已包含：

- `MODEL_SIGNAL_CONTRACT_CN.md`
- `STRATEGY_RULE_CONTRACT_CN.md`
- `ORDER_INTENT_CONTRACT_CN.md`
- `REPLAY_RESULT_CONTRACT_CN.md`

满足 R0 文件产出要求。

### 3.2 ModelSignal contract 核心语义基本完整

已定义：

- required fields；
- forbidden fields；
- forbidden actions；
- `candidate_rank`、`buy_score`、`full_qlib_rank` 的职责边界；
- 纯 qlib 与 LTR 的映射方式；
- LTR 不得替换 qlib top50 candidate boundary。

这部分可以作为 R1 adapter 的基础。

### 3.3 StrategyRule / OrderIntent 对 buggy_e8r 边界有约束

`one_sell_one_buy_buggy_e8r` 已被标记为：

```text
diagnostic only
not_valid_strategy_evidence
```

并明确不得作为默认策略、收益证据、产品展示或日更 publish 候选。

## 4. 必须修复的问题

### 4.1 R0 混入前端改动

问题级别：高。

R0 工作文档明确禁止修改前端。当前 diff 中：

```text
frontend/src/views/tw-stock-monitor/index.vue
```

新增了 `LTR 只读研究候选` 展示区块、O4 orthogonal LTR 指标、审计说明和 CSS。

这违反 R0 边界：

- R0 目标是最小 contract 冻结；
- 前端展示属于后置范围；
- R0 不应产生新的产品展示或研究候选展示入口。

修复要求：

- 从 R0 变更集中移除该前端改动；
- 如确需保留，必须拆分为 R3+ 或 Frontend readonly presentation phase 单独审查；
- R0 执行报告不得声明“未修改前端”，除非实际工作区已恢复。

### 4.2 R0 混入日更脚本改动

问题级别：高。

R0 工作文档明确禁止修改日更主链路。当前 diff 中：

```text
scripts/run_daily_tw_stock_auto_update.py
```

新增：

- `run_p3_ltr_candidate()`;
- `--run-p3-ltr`;
- `TW_DAILY_AUTO_RUN_P3_LTR`;
- 在 daily auto update 流程中可选触发 P3 LTR rerank。

即使默认关闭，这仍属于 Daily Orchestrator 接入，已超出 R0-R2 的最小研究/回放闭环范围。

修复要求：

- 从 R0 变更集中移除该日更脚本改动；
- Daily Orchestrator 接入必须等 R2 审查通过后，在后续 phase 单独设计和审查；
- R0 执行报告不得声明“未修改日更脚本”，除非实际工作区已恢复。

### 4.3 ReplayResult contract 必需输出与任务书不一致

问题级别：中高。

R0-R2 工作文档要求 ReplayResult 标准输出包括：

```text
summary.csv
actions.csv
daily_nav.csv
position_snapshots.csv
coverage_audit.csv
position_integrity_audit.csv
forbidden_field_audit.csv
manifest.json
```

当前 `REPLAY_RESULT_CONTRACT_CN.md` 的必需文件为：

```text
manifest.json
summary.csv
actions.csv
daily_nav.csv
position_snapshots.csv
execution_audit.csv
forbidden_action_audit.json
```

并将 `position_integrity_audit.csv` 放入可选文件，且没有把 `coverage_audit.csv`、`forbidden_field_audit.csv` 作为必需文件。

这会削弱 R2 replay matrix 验收中的审计闭环，尤其是：

- actual window 是否越过 requested window；
- active action quantity 是否 > 0；
- execution_date 是否 > signal_date；
- max holding count 是否 <= target holdings；
- duplicate position 是否为 0；
- future label / return 是否没有参与 ranking；
- final holdings 是否完成 mark-to-market。

修复要求：

- 将 `coverage_audit.csv`、`position_integrity_audit.csv`、`forbidden_field_audit.csv` 纳入 ReplayResult 必需文件；
- 保留 `execution_audit.csv` 可以，但不能替代上述任务书要求的审计产物；
- 明确每个 audit 的 required fields 和最小检查项；
- R0 执行报告更新为“ReplayResult contract 已与任务书标准输出一致”后再申请复审。

### 4.4 执行报告与实际变更不一致

问题级别：中高。

`PHASER0_MINIMAL_CONTRACT_EXECUTION_REPORT_CN.md` 声明：

```text
未修改前端
未修改日更脚本
```

但工作区实际存在：

```text
M frontend/src/views/tw-stock-monitor/index.vue
M scripts/run_daily_tw_stock_auto_update.py
```

修复要求：

- 执行者需要先恢复 R0 禁止范围内的代码改动；
- 再更新执行报告；
- 审查者复核 `git status --short` 和 `git diff --stat` 后，才可考虑放行。

## 5. R0 修复验收清单

执行者修复后，审查者至少检查：

- `docs/tw_modular_contracts/` 四份 contract 仍存在；
- `MODEL_SIGNAL_CONTRACT_CN.md` required fields 完整；
- `candidate_rank / buy_score / full_qlib_rank` 语义未弱化；
- LTR 仍只能用底座 qlib rank 作为 candidate boundary；
- `one_sell_one_buy_buggy_e8r` 仍为 diagnostic only；
- `REPLAY_RESULT_CONTRACT_CN.md` 必需输出包含 `coverage_audit.csv`、`position_integrity_audit.csv`、`forbidden_field_audit.csv`；
- 工作区不再包含 R0 禁止的前端、日更、provider、accepted latest、monitor、broker/order 变更；
- 执行报告与实际 diff 一致。

## 6. R1 放行条件

只有在 R0 复审通过后，才允许进入 R1。

R1 必须继续遵守：

- 不训练；
- 不调参；
- 不重算模型分数；
- 不改变 score；
- 不改变排序；
- 不改变 universe；
- 不产生策略收益结论；
- 不修改前端；
- 不修改日更；
- 不触发 provider publish；
- 不切 accepted latest；
- 不触发 monitor；
- 不触发 broker、quick-trade 或 order。

R1 只允许新增 legacy signal adapter，将旧 replay-ready / score 产物标准化为 `ModelSignalArtifact`。

## 7. 给执行者的返工指令

请先修复 R0，不要进入 R1：

1. 移除本次 R0 中的前端改动。
2. 移除本次 R0 中的日更脚本改动。
3. 修正 `docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md`，补齐任务书要求的必需审计产物。
4. 更新 `docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER0_MINIMAL_CONTRACT_EXECUTION_REPORT_CN.md`，确保禁止事项记录与实际 diff 一致。
5. 重新提交 R0 复审。

复审通过后，审查者再明确允许进入 R1。
