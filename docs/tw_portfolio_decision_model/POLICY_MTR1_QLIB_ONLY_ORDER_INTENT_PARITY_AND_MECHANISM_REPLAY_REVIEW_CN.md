# POLICY_MTR1_QLIB_ONLY_ORDER_INTENT_PARITY_AND_MECHANISM_REPLAY_REVIEW_CN

生成日期：2026-06-28

## 1. Verdict

```text
PASS_MTR1_QLIB_ONLY_WITH_MECHANISM_CANDIDATE_AND_MTR2_LINEAGE_BLOCKER
```

MTR1 执行产物通过审查。结论仅限 qlib-only readonly research candidate，不构成生产策略、默认策略、真实订单或投资建议。

限制条件：

```text
MTR2 仍被 qlib+LTR 标准 ModelSignalArtifact lineage blocker 阻断。
不得使用 LTR private artifacts、替代 CSV 或缺失 manifest 的旁路路径。
不得切 production/default/frontend/API/Agent/daily/provider/latest。
```

## 2. Evidence Checked

已检查：

```text
docs/tw_portfolio_decision_model/POLICY_MTR1_QLIB_ONLY_ORDER_INTENT_PARITY_AND_MECHANISM_REPLAY_EXECUTION_REPORT_CN.md
data_tw/experiments/policy_mtr_mechanism_transfer/mtr1_qlib_only_order_intent_parity_and_mechanism_replay/manifest.json
data_tw/experiments/policy_mtr_mechanism_transfer/mtr1_qlib_only_order_intent_parity_and_mechanism_replay/input_signal_lineage_audit.csv
data_tw/experiments/policy_mtr_mechanism_transfer/mtr1_qlib_only_order_intent_parity_and_mechanism_replay/dependency_validation_report.json
data_tw/experiments/policy_mtr_mechanism_transfer/mtr1_qlib_only_order_intent_parity_and_mechanism_replay/order_intent_artifact_index.csv
data_tw/experiments/policy_mtr_mechanism_transfer/mtr1_qlib_only_order_intent_parity_and_mechanism_replay/order_intent_validator_report.json
data_tw/experiments/policy_mtr_mechanism_transfer/mtr1_qlib_only_order_intent_parity_and_mechanism_replay/baseline_order_intent_parity_audit.csv
data_tw/experiments/policy_mtr_mechanism_transfer/mtr1_qlib_only_order_intent_parity_and_mechanism_replay/replay_artifact_index.csv
data_tw/experiments/policy_mtr_mechanism_transfer/mtr1_qlib_only_order_intent_parity_and_mechanism_replay/replay_validator_report.json
data_tw/experiments/policy_mtr_mechanism_transfer/mtr1_qlib_only_order_intent_parity_and_mechanism_replay/baseline_replay_parity_audit.csv
data_tw/experiments/policy_mtr_mechanism_transfer/mtr1_qlib_only_order_intent_parity_and_mechanism_replay/mechanism_candidate_contract.csv
data_tw/experiments/policy_mtr_mechanism_transfer/mtr1_qlib_only_order_intent_parity_and_mechanism_replay/mechanism_replay_comparison.csv
data_tw/experiments/policy_mtr_mechanism_transfer/mtr1_qlib_only_order_intent_parity_and_mechanism_replay/turnover_cost_audit.csv
data_tw/experiments/policy_mtr_mechanism_transfer/mtr1_qlib_only_order_intent_parity_and_mechanism_replay/holding_overlap_audit.csv
data_tw/experiments/policy_mtr_mechanism_transfer/mtr1_qlib_only_order_intent_parity_and_mechanism_replay/rank_overlap_audit.csv
data_tw/experiments/policy_mtr_mechanism_transfer/mtr1_qlib_only_order_intent_parity_and_mechanism_replay/cash_no_trade_audit.csv
data_tw/experiments/policy_mtr_mechanism_transfer/mtr1_qlib_only_order_intent_parity_and_mechanism_replay/forbidden_field_audit.csv
data_tw/experiments/policy_mtr_mechanism_transfer/mtr1_qlib_only_order_intent_parity_and_mechanism_replay/forbidden_action_audit.csv
scripts/run_tw_policy_mtr1_qlib_only_order_intent_parity_and_mechanism_replay.py
```

并做了只读搜索：

```text
configs/
backend/
frontend/
scripts/
docs/tw_modular_contracts/
docs/tw_portfolio_decision_model/
```

未发现 `mechanism_transfer_top50_cost_aware_v1` 被接入 production registry、backend/API、frontend、daily/provider、accepted latest 或默认策略路径。

## 3. Gate Review

### 3.1 qlib-only ModelSignalArtifact

结论：

```text
PASS
```

执行产物只使用：

```text
data_tw/artifacts/signals/frozen_qlib_2018_2022/r1_legacy_signal_adapter_20260616/manifest.json
```

`input_signal_lineage_audit.csv` 通过：

```text
artifact_type = model_signal
model_family = qlib
quality_status = pass
core_signal_v1 = true
candidate_boundary = qlib_top50
buy_ordering = buy_score_desc
full_rank_exit = full_qlib_rank
row_count = 119862
date_range = 2023-01-03..2026-05-07
```

未发现 qlib+LTR、LTR private artifact 或替代 lineage 路径被使用。

### 3.2 M0 OrderIntent Parity

结论：

```text
PASS
```

`baseline_order_intent_parity_audit.csv` 显示：

```text
same_signal_date_instrument_action_parity: pass, baseline_not_m0=0, m0_not_baseline=0
daily_buy_count_parity: pass
daily_sell_count_parity: pass
intent_reason_parity: pass, canonical mapping accepted
```

baseline 与 M0 均为：

```text
buy_intents = 744
sell_intents = 716
row_count = 1460
```

### 3.3 M0 ReplayResult Parity

结论：

```text
PASS
```

`baseline_replay_parity_audit.csv` 对核心 replay metrics 全部零差异：

```text
final_equity delta = 0
gross_total_return delta = 0
net_total_return_after_fee_tax delta = 0
max_drawdown delta = 0
average_turnover delta = 0
total_fee delta = 0
total_tax delta = 0
buy_count delta = 0
sell_count delta = 0
skipped_action_count delta = 0
average_holding_count delta = 0
```

`replay_validator_report.json` 显示 `decision_source_order_intent = pass`，`M2_hold_rank_buffer_100/replays/manifest.json` 声明：

```text
decision_source = order_intent_artifact
order_intent_artifact = .../order_intents/M2_hold_rank_buffer_100/manifest.json
price_store = qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/normalized_nonempty
execution_price = next_open
```

未发现 replay 为通过 M0 parity 而读取策略私有字段或模型私有字段。

### 3.4 Candidate Boundary

结论：

```text
PASS
```

实际运行候选严格来自 MTR0/mainline：

```text
M0 baseline parity
M1 max_replace_per_day in [1, 2]
M2 hold_rank_buffer in [60, 75, 100]
M3 score_z_gap_min in [0.0, 0.25, 0.50] and rank_gap_min in [0, 5, 10]
M4 fixed fee/tax cost gate
C1 M1=1 + M2=75
C2 M1=1 + M3 score_z=0.25
C3 M1=1 + M2=75 + M3 score_z=0.25
```

`M5_and_C4` 被记录为：

```text
deferred_not_run
requires ext_market_regime_code schema and PIT TWII lineage
```

未发现后验候选扩展。

### 3.5 Forbidden Inputs / Actions

结论：

```text
PASS
```

`forbidden_action_audit.csv` 全部为 `not_performed`，覆盖：

```text
trained_model
tuned_model
used_ltr_or_private_signal
read_future_or_label
read_replay_return_as_strategy_input
modified_replay_engine_private_field
modified_registry_default
modified_frontend_or_api
modified_daily_or_provider
provider_publish
accepted_latest_switch
broker_or_quick_trade
target_weight_or_position_output
posthoc_candidate_expansion
```

`forbidden_field_audit.csv` 未发现 future/label/realized pnl/replay return 作为策略输入；未发现 target_weight、target_position、broker、order、quick_trade 输出。

说明：ReplayResult 合同本身要求 `actions.csv` 包含 `quantity`、`execution_price`、`commission`、`tax`、`cash_after` 等回放结果字段；审查中将这些字段限定为 replay 输出侧字段，未将其视为 OrderIntent 或策略输入。OrderIntentArtifact 未包含 `quantity_to_buy`、`quantity_to_sell`、`target_weight`、`target_position`、broker/order/quick_trade 等禁用字段。

### 3.6 Turnover / Cost / Degeneration

结论：

```text
PASS
```

唯一通过 candidate gate 的机制为：

```text
M2_hold_rank_buffer_100
```

关键指标：

```text
baseline net_total_return_after_fee_tax = 11.82112201
M2_hold_rank_buffer_100 net_total_return_after_fee_tax = 13.71864776
baseline average_turnover = 0.17115347
M2_hold_rank_buffer_100 average_turnover = 0.10241990
turnover_reduction_vs_baseline = 0.40159028
baseline total_fee_plus_tax = 1244140.76
M2_hold_rank_buffer_100 total_fee_plus_tax = 784348.68
fee_tax_reduction_vs_baseline = 0.36956596
baseline max_drawdown = -0.32496728
M2_hold_rank_buffer_100 max_drawdown = -0.35223608
cash_no_trade_day_count = 0
average_holding_count = 8.706983
```

M2_hold_rank_buffer_100 满足：

```text
net >= baseline_net - 0.02
turnover reduction >= 20%
fee+tax reduction >= 20%
drawdown worse within 0.05 absolute tolerance
cash/no-trade ratio = 0.0 <= 0.1
```

因此 turnover/cost 降低不是 all-cash/no-trade degeneration。

## 4. Findings

### Low

1. Replay independence 仍建议在下一阶段补一轮独立复核。

   MTR1 runner 同时生成 OrderIntentArtifact 与 ReplayResultArtifact；产物 manifest、execution audit 与 validator 均声明 replay 决策源为 `OrderIntentArtifact`，且未发现私有字段读取或收益反向改写。但若后续进入 qlib+LTR 或 production readiness，应增加一个独立 readonly replay 复核步骤：从已落盘 OrderIntentArtifact 重新读取并生成 replay checksum，避免同一 runner 内部状态成为隐含耦合。

2. 部分机制未产生有效差异，不影响 MTR1 gate。

   M3 与 M4 多数组合 replay 与 baseline 完全相同，C1/C3 未通过 candidate gate。MTR1 的通过依据仅应绑定 `M2_hold_rank_buffer_100`，不得把未通过候选写成有效机制。

## 5. Gate Decision

```text
qlib_only_standard_signal_gate: PASS
M0_order_intent_parity_gate: PASS
M0_replay_parity_gate: PASS
replay_no_private_field_gate: PASS
M1_M4_C1_C3_predeclared_candidate_gate: PASS
M5_C4_deferred_gate: PASS
no_qlib_ltr_private_artifact_gate: PASS
no_future_label_realized_pnl_replay_return_input_gate: PASS
order_intent_forbidden_output_gate: PASS
replay_forbidden_output_gate: PASS_WITH_CONTRACT_SCOPE_NOTE
turnover_cost_not_degenerate_gate: PASS
production_default_boundary_gate: PASS
MTR1_readiness_gate: PASS_QLIB_ONLY
MTR2_readiness_gate: BLOCKED_LINEAGE_REPAIR_REQUIRED
```

## 6. Recommendation

建议下一步二选一：

1. `qlib-only closure`：把 `M2_hold_rank_buffer_100` 作为 readonly research candidate 封存，写 MTR1 qlib-only closure/route decision，不进入生产、不切默认、不接前端/API/daily/provider/latest。
2. `MTR2 repair work doc`：先修复 qlib+LTR 标准 ModelSignalArtifact lineage，再单独审查。建议 work doc 命名：

```text
docs/tw_portfolio_decision_model/POLICY_MTR2_QLIB_LTR_LINEAGE_REPAIR_AND_TRANSFER_REPLAY_WORK_CN.md
```

MTR2 启动前必须满足：

```text
指定 qlib+LTR 标准 ModelSignalArtifact manifest 存在
artifact_type = model_signal
quality_status = pass
candidate_rank/full_qlib_rank 仍来自 qlib base
buy_score 来自 LTR rerank
LTR 不改变 qlib top50 candidate boundary / sell boundary
无 LTR private artifacts 或替代路径
复用 MTR1 已通过的 M2_hold_rank_buffer_100
先跑 qlib+LTR baseline M0 parity，再跑 transfer replay
```

在上述 lineage repair 完成前，本路线只能停在 qlib-only closure。
