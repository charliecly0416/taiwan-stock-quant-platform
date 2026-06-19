# Phase R0-R2 工作文档：模块化解耦最小闭环重构

生成日期：2026-06-16

## 1. 背景与目标

本阶段承接：

- `docs/tw_extended_oos_qlib_orthogonal_ltr/MODULAR_DECOUPLED_RESEARCH_AND_PRODUCTION_PIPELINE_DESIGN_CN.md`
- `docs/tw_extended_oos_qlib_orthogonal_ltr/MODULAR_DECOUPLED_REFACTOR_REVIEW_AND_EXECUTION_SUGGESTION_CN.md`
- 当前 formal replay matrix：`scripts/run_extended_oos_formal_replay_matrix.py`

审查意见认为总体模块化方向合理，但不能一次性重构全链路。第一轮必须收敛到研究/回放链路的最小闭环：

```text
旧 qlib/LTR replay-ready CSV
  -> legacy adapter
  -> 标准 ModelSignalArtifact
  -> YAML config
  -> config-driven formal replay matrix
  -> 与当前 formal replay matrix 完全复现对齐
```

本阶段目标不是提出新策略结论，也不是改日更生产链路，而是让后续新增模型、新策略可以按 contract 接入。

## 2. 总原则

必须坚持：

1. 先 contract，后重构。
2. 先 adapter，后替换旧脚本。
3. 只读研究链路优先，日更生产链路后置。
4. 新旧结果必须可复现对齐。
5. 默认策略切换必须单独决策，不由重构自动发生。
6. 不因为模块化而新增策略结论。
7. 不触发 provider publish / accepted latest / frontend / monitor / broker / order。

## 3. 本阶段范围

只执行 R0-R2：

| Phase | 名称 | 目标 |
| --- | --- | --- |
| R0 | 最小合同冻结 | 冻结 ModelSignal / StrategyRule / OrderIntent / ReplayResult contract |
| R1 | Legacy Signal Adapter | 将现有核心 replay-ready 产物转换为标准 ModelSignalArtifact |
| R2 | Config-driven Formal Replay Matrix | formal replay matrix 改为读取标准 signal artifact + YAML config |

明确后置，不在本阶段执行：

- Provider / Normalizer 重构；
- Feature Builder 重构；
- Daily Orchestrator 接入；
- Frontend / API 展示接入；
- 默认策略切换；
- 模型训练或调参；
- 新策略收益筛选。

## 4. Phase R0：最小 Contract 冻结

### 4.1 目标

冻结研究/回放链路最小 contract，不改业务逻辑，不重跑模型。

### 4.2 必须产出

目录：

```text
docs/tw_modular_contracts/
```

文件：

```text
MODEL_SIGNAL_CONTRACT_CN.md
STRATEGY_RULE_CONTRACT_CN.md
ORDER_INTENT_CONTRACT_CN.md
REPLAY_RESULT_CONTRACT_CN.md
```

### 4.3 MODEL_SIGNAL_CONTRACT 必须定义

标准字段：

```text
date
instrument
model_name
model_family
candidate_rank
buy_score
raw_score
score_rank
full_qlib_rank
signal_asof
available_at
source_artifact
source_model_artifact
source_feature_artifact
```

语义必须明确：

- `candidate_rank`：用于 qlib top50 universe / exit boundary；
- `buy_score`：用于 top50 内买入排序；
- `full_qlib_rank`：用于持仓跌出 top50 后判断最差排名；
- 纯 qlib：`candidate_rank` 与 `buy_score` 都来自 qlib；
- LTR：`candidate_rank` 仍来自底座 qlib，`buy_score` 来自 LTR。

禁止字段：

```text
future_return_*
future_excess_return_*
relevance_10d_top_heavy
ltr_relevance_label
realized_pnl
action
holding
target_position
```

### 4.4 STRATEGY_RULE_CONTRACT 必须定义

策略模块输入：

```text
ModelSignalArtifact
PortfolioState
StrategyRuleConfig
```

策略模块输出：

```text
OrderIntentArtifact
```

策略规则不得：

- 读取模型私有文件；
- 训练模型；
- 改 universe；
- 读 future return / label；
- 读未来价格；
- 负责成交记账。

必须冻结当前规则语义：

| rule | status |
| --- | --- |
| original | valid |
| top50_exit_all | valid |
| top50_exit_one_worst_sell | valid |
| one_sell_one_buy_correct | valid |
| one_sell_one_buy_buggy_e8r | diagnostic only，不得作为策略收益证据 |

### 4.5 ORDER_INTENT_CONTRACT 必须定义

标准字段：

```text
signal_date
instrument
intent_action
intent_reason
strategy_rule
candidate_rank
buy_rank
full_qlib_rank
max_buy_count
max_sell_count
model_name
signal_artifact
```

注意：

- OrderIntent 只是意图，不包含实际成交价；
- 成交价格只能由 ReplayExecution 模块处理；
- 若 signal_date 是最后一天且无下一交易日价格，ReplayExecution 决定 skip。

### 4.6 REPLAY_RESULT_CONTRACT 必须定义

标准输出：

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

必须审计：

- active action quantity > 0；
- execution_date > signal_date；
- max holding count <= target holdings；
- duplicate position = 0；
- future label / return 不参与 ranking；
- actual window 不越过 requested window；
- final holdings mark-to-market。

### 4.7 R0 禁止事项

禁止：

- 训练 qlib / LTR；
- 重跑收益筛选；
- 修改前端；
- 修改日更；
- 修改默认策略；
- 触发 provider / accepted latest / monitor / broker / order。

### 4.8 R0 验收

审查者必须确认：

- 四份 contract 都存在；
- required fields / forbidden fields / forbidden actions 完整；
- `candidate_rank / buy_score / full_qlib_rank` 语义清晰；
- qlib 与 LTR 映射清晰；
- buggy rule 只作为 diagnostic。

## 5. Phase R1：Legacy Signal Adapter

### 5.1 目标

把现有旧 replay-ready / score 文件转换为标准 `ModelSignalArtifact`，不重训、不重算模型分数、不改变排序。

### 5.2 输入

至少支持以下旧产物：

```text
data_tw/experiments/fresh_top50_coverage_repair/phasec4_repaired_replay_ready_scores.csv
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e4_2026_replay/phasee4_replay_ready_scores_2026.csv
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e6_bridge_ltr_2025_two_qlib_bases/phasee6_replay_ready_scores_2026.csv
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e1_frozen_qlib_training_and_oos_score/phasee1_raw_oos_score_rank_2023_2026.csv
```

还需要 full rank source：

```text
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2b_fresh_qlib_training/phase_s2b_post_filter_score_rank.csv
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e1_frozen_qlib_training_and_oos_score/phasee1_raw_oos_score_rank_2023_2026.csv
```

### 5.3 输出目录

建议：

```text
data_tw/artifacts/signals/{model_name}/{run_id}/
```

每个 model 至少输出：

```text
manifest.json
signals.csv
schema.json
coverage_audit.csv
forbidden_field_audit.csv
legacy_mapping_audit.csv
```

### 5.4 必须支持的标准模型名

```text
fresh_qlib_adaptive
fresh_qlib_2025_ltr
frozen_qlib_2025_ltr
e4_frozen_qlib_2023_2025_ltr
frozen_qlib_2018_2022
```

### 5.5 Legacy Mapping 要求

`fresh_qlib_adaptive`：

```text
candidate_rank <- qlib_rank
buy_score <- adaptive_score_baseline
raw_score <- qlib_score_raw
full_qlib_rank <- phase_s2b_post_filter_score_rank.qlib_rank
```

`fresh_qlib_2025_ltr`：

```text
candidate_rank <- qlib_rank
buy_score <- phasee6_branch_a_fresh_ltr_score
raw_score <- phasee6_branch_a_fresh_ltr_score
full_qlib_rank <- phase_s2b_post_filter_score_rank.qlib_rank
method_group <- branch_a_treatment
```

`frozen_qlib_2025_ltr`：

```text
candidate_rank <- qlib_rank
buy_score <- phasee6_branch_b_frozen_ltr_score
raw_score <- phasee6_branch_b_frozen_ltr_score
full_qlib_rank <- phasee1_raw_oos_score_rank_2023_2026.qlib_rank_raw
method_group <- branch_b_control_treatment
```

`e4_frozen_qlib_2023_2025_ltr`：

```text
candidate_rank <- qlib_rank
buy_score <- phasee3_extended_oos_ltr_score
raw_score <- phasee3_extended_oos_ltr_score
full_qlib_rank <- phasee1_raw_oos_score_rank_2023_2026.qlib_rank_raw
```

`frozen_qlib_2018_2022`：

```text
candidate_rank <- qlib_rank_raw
buy_score <- qlib_score_raw
raw_score <- qlib_score_raw
full_qlib_rank <- qlib_rank_raw
```

### 5.6 R1 验收

必须证明：

- signal row count 与旧输入中对应 rows 一致；
- date/instrument duplicate key 为 0；
- 2026_ytd 每日 top50 覆盖与旧 replay-ready 一致；
- `buy_score` 数值不改变；
- `candidate_rank` 数值不改变；
- `full_qlib_rank` 来源可追溯；
- forbidden fields 不出现在 `signals.csv`；
- 不产生策略动作；
- 不产生 replay 收益结论。

### 5.7 R1 禁止事项

禁止：

- 重训模型；
- 重算 LTR 分数；
- 改 qlib rank；
- 改 score；
- 扩充或缩小 universe；
- 触发日更或前端。

## 6. Phase R2：Config-driven Formal Replay Matrix

### 6.1 目标

将 formal replay matrix 从 hardcoded `StrategySpec` 改为读取：

```text
ModelSignalArtifact manifest + YAML config
```

新脚本可以是：

```text
scripts/run_modular_formal_replay_matrix.py
```

也可以在保留旧脚本的基础上新增 config mode，但必须保证旧脚本仍可用于 diff。

### 6.2 配置文件

建议：

```text
configs/tw_modular_replay_matrix.yaml
```

示例：

```yaml
signals:
  - method: fresh_qlib_adaptive
    artifact: data_tw/artifacts/signals/fresh_qlib_adaptive/latest/manifest.json

  - method: fresh_qlib_2025_ltr
    artifact: data_tw/artifacts/signals/fresh_qlib_2025_ltr/latest/manifest.json

  - method: frozen_qlib_2025_ltr
    artifact: data_tw/artifacts/signals/frozen_qlib_2025_ltr/latest/manifest.json

  - method: e4_frozen_qlib_2023_2025_ltr
    artifact: data_tw/artifacts/signals/e4_frozen_qlib_2023_2025_ltr/latest/manifest.json

  - method: frozen_qlib_2018_2022
    artifact: data_tw/artifacts/signals/frozen_qlib_2018_2022/latest/manifest.json

rules:
  - original
  - top50_exit_all
  - top50_exit_one_worst_sell
  - one_sell_one_buy_correct
  - one_sell_one_buy_buggy_e8r

windows:
  - name: 2026_ytd
    start: 2026-01-01
    end: 2026-05-07
```

### 6.3 Replay Engine 输入

R2 replay engine 只能读取标准字段：

```text
date
instrument
model_name
model_family
candidate_rank
buy_score
raw_score
score_rank
full_qlib_rank
signal_asof
available_at
source_artifact
```

不得读取：

- `phasee6_branch_a_fresh_ltr_score`
- `phasee3_extended_oos_ltr_score`
- `adaptive_score_baseline`
- `qlib_rank_raw`
- 任何 legacy 私有列名。

这些只允许出现在 R1 adapter 内部。

### 6.4 与旧 formal replay 对齐

必须以当前产物为 baseline：

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/formal_replay_matrix/formal_replay_summary.csv
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/formal_replay_matrix/formal_replay_actions.csv
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/formal_replay_matrix/formal_replay_daily_nav.csv
```

R2 输出：

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_replay_matrix/
  manifest.json
  replay_summary.csv
  replay_actions.csv
  replay_daily_nav.csv
  replay_position_snapshots.csv
  coverage_audit.csv
  position_integrity_audit.csv
  replay_diff_vs_formal_baseline.csv
```

### 6.5 R2 验收

必须证明：

- `2026_ytd` 所有 method/rule 的 net return 与旧 formal replay 完全一致；
- action_count / buy_count / sell_count 完全一致；
- daily_nav 最终 equity 完全一致；
- active action key 对齐，允许字段顺序不同，不允许交易逻辑差异；
- no training / no tuning；
- replay engine 不读 legacy 私有列；
- no provider / accepted latest / frontend / monitor / trading。

如出现差异：

- 必须输出 diff；
- 不得自行解释后继续推进；
- 必须停下来让审查者判断是否是 bug、口径变化，还是需要用户确认的 contract 变化。

## 7. 审查者交替审查流程

本阶段必须按以下节奏：

```text
执行者完成 R0 执行报告
  -> 审查者审查 R0，决定是否允许 R1
执行者完成 R1 执行报告
  -> 审查者审查 R1，决定是否允许 R2
执行者完成 R2 执行报告
  -> 审查者审查 R2，决定是否允许进入 R3
```

不得 R0-R2 一次性执行完再统一报告。

## 8. 执行报告命名

执行者报告：

```text
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER0_MINIMAL_CONTRACT_EXECUTION_REPORT_CN.md
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER1_LEGACY_SIGNAL_ADAPTER_EXECUTION_REPORT_CN.md
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER2_CONFIG_DRIVEN_REPLAY_MATRIX_EXECUTION_REPORT_CN.md
```

审查者如需写审查文档：

```text
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER0_REVIEW_AND_R1_WORK_CN.md
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER1_REVIEW_AND_R2_WORK_CN.md
docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER2_REVIEW_AND_R3_WORK_CN.md
```

## 9. 给执行者的 Prompt

### R0 执行者 Prompt

请按 `docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER0_R2_MODULAR_DECOUPLED_REFACTOR_WORK_CN.md` 执行 Phase R0：冻结最小模块化 contract。只创建 `docs/tw_modular_contracts/MODEL_SIGNAL_CONTRACT_CN.md`、`STRATEGY_RULE_CONTRACT_CN.md`、`ORDER_INTENT_CONTRACT_CN.md`、`REPLAY_RESULT_CONTRACT_CN.md` 和执行报告 `docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER0_MINIMAL_CONTRACT_EXECUTION_REPORT_CN.md`。必须明确 required fields、forbidden fields/actions、`candidate_rank/buy_score/full_qlib_rank` 语义、qlib 与 LTR 映射、`buggy_e8r` 只能 diagnostic。不得训练模型、不得重跑收益筛选、不得修改前端/日更/默认策略、不得触发 provider/accepted latest/monitor/broker/order。

### R1 执行者 Prompt

请在 R0 审查通过后，按 `docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER0_R2_MODULAR_DECOUPLED_REFACTOR_WORK_CN.md` 执行 Phase R1：新增 legacy signal adapter，把现有 fresh qlib、fresh+2025 LTR、frozen+2025 LTR、E4 LTR、frozen qlib 2018-2022 的旧 replay-ready/score 产物转换为标准 `ModelSignalArtifact`。输出到 `data_tw/artifacts/signals/{model_name}/{run_id}/`，每个模型必须有 `manifest.json`、`signals.csv`、`schema.json`、`coverage_audit.csv`、`forbidden_field_audit.csv`、`legacy_mapping_audit.csv`。必须证明 row count、date/instrument key、candidate_rank、buy_score、full_qlib_rank 与旧产物对齐，且不改变 score、不改变排序、不训练、不重算、不产生策略收益结论。执行报告写到 `docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER1_LEGACY_SIGNAL_ADAPTER_EXECUTION_REPORT_CN.md`。

### R2 执行者 Prompt

请在 R1 审查通过后，按 `docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER0_R2_MODULAR_DECOUPLED_REFACTOR_WORK_CN.md` 执行 Phase R2：把 formal replay matrix 改为 config-driven，从标准 `ModelSignalArtifact manifest` + `configs/tw_modular_replay_matrix.yaml` 读取，不得再读取 legacy 私有列名。输出到 `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_replay_matrix/`。必须与当前 baseline `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/formal_replay_matrix/` 在 `2026_ytd` 的 summary/action/nav 关键结果完全一致；若不一致，必须输出 diff 并停止，不得自行推进。不得训练、调参、改默认策略、改前端/日更、触发 provider/accepted latest/monitor/broker/order。执行报告写到 `docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER2_CONFIG_DRIVEN_REPLAY_MATRIX_EXECUTION_REPORT_CN.md`。

## 10. 给审查者的 Prompt

### R0 审查者 Prompt

请审查 `docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER0_MINIMAL_CONTRACT_EXECUTION_REPORT_CN.md` 以及 `docs/tw_modular_contracts/` 下四份 contract。重点确认 required fields、forbidden fields/actions 是否完整，`candidate_rank/buy_score/full_qlib_rank` 语义是否清晰，qlib 与 LTR 映射是否真正解耦，`buggy_e8r` 是否只允许 diagnostic，以及执行者是否没有训练、重跑收益筛选、修改前端/日更/默认策略或触发 provider/accepted latest/monitor/broker/order。若 contract 不完整或语义会导致模型/策略耦合，必须要求修复；通过后给出 R1 工作文档或明确允许进入 R1。

### R1 审查者 Prompt

请审查 `docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER1_LEGACY_SIGNAL_ADAPTER_EXECUTION_REPORT_CN.md` 及 `data_tw/artifacts/signals/` 下产物。重点确认 legacy adapter 是否只是字段映射和 artifact 标准化，没有重训、重算、改分数、改 rank、改 universe；检查每个 `signals.csv` 的 row count、duplicate key、candidate_rank、buy_score、full_qlib_rank、forbidden fields、coverage audit、legacy_mapping_audit；确认 qlib/LTR 都输出统一 ModelSignalArtifact，且 LTR 没有改变 qlib top50 boundary。若任何标准信号与旧产物不一致，必须停下来要求修复；通过后给出 R2 工作文档或明确允许进入 R2。

### R2 审查者 Prompt

请审查 `docs/tw_extended_oos_qlib_orthogonal_ltr/PHASER2_CONFIG_DRIVEN_REPLAY_MATRIX_EXECUTION_REPORT_CN.md`、`configs/tw_modular_replay_matrix.yaml` 和 `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_replay_matrix/`。重点确认 replay engine 是否只读取标准 ModelSignalArtifact 字段，不再读取 legacy 私有列名；确认 config-driven replay 与旧 formal replay 在 `2026_ytd` 的 net return、action_count、buy_count、sell_count、final equity、active action key 是否完全一致；确认 no training/no tuning/no provider/no accepted latest/no frontend/no monitor/no broker/order。若有差异，必须判断是 bug 还是 contract 变化；contract 变化必须要求用户确认，不能自行放行。

## 11. R2 之后的建议

R2 审查通过后，才允许讨论 R3：

```text
R3：StrategyDecision / OrderIntent 拆分
```

R3 目标是把当前 replay 内部的策略决策拆成独立 `OrderIntentArtifact`：

```text
ModelSignalArtifact + PortfolioState + StrategyRule
  -> OrderIntentArtifact
OrderIntentArtifact + PriceStore + ExecutionConfig
  -> ReplayResultArtifact
```

Daily Orchestrator、Provider/Normalizer、Frontend 展示全部继续后置，不得提前混入 R0-R2。
