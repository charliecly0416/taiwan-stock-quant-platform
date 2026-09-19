---
created_at: 2026-06-23
status: work_order_for_atpal3_candidate_replay_adapter_contract
phase: ATPAL3_CANDIDATE_REPLAY_ADAPTER_CONTRACT
mainline_doc: docs/tw_portfolio_decision_model/POLICY_ATPAL_ACTION_TRADE_PNL_ATTRIBUTION_LEDGER_MAINLINE_CN.md
prior_review: docs/tw_portfolio_decision_model/POLICY_ATPAL2_CONTRIBUTION_AUDIT_REVIEW_CN.md
prior_execution_report: docs/tw_portfolio_decision_model/POLICY_ATPAL2_CONTRIBUTION_AUDIT_EXECUTION_REPORT_CN.md
source_atpal0_root: data_tw/experiments/action_trade_pnl_attribution_ledger/atpal0_contract
source_atpal1_root: data_tw/experiments/action_trade_pnl_attribution_ledger/atpal1_r_action_context_ledger_repair
source_atpal2_root: data_tw/experiments/action_trade_pnl_attribution_ledger/atpal2_contribution_audit
output_root: data_tw/experiments/action_trade_pnl_attribution_ledger/atpal3_candidate_adapter_contract
execution_report: docs/tw_portfolio_decision_model/POLICY_ATPAL3_CANDIDATE_REPLAY_ADAPTER_CONTRACT_EXECUTION_REPORT_CN.md
atpal3_authorized: true
atpal4_authorized: false
candidate_replay_authorized: false
strategy_experiment_authorized: false
rule_selection_authorized: false
threshold_selection_authorized: false
strict_test_authorized: false
model_training_authorized: false
production_allowed: false
readonly_only: true
simulation_only: true
---

# ATPAL3 Candidate Replay Adapter Contract 工作文档

## 1. 本轮定位

本轮只执行：

```text
ATPAL3: Candidate Replay Adapter Contract
```

目标是定义未来 rule / policy candidate 如何接入 ATPAL ledger，使 candidate-level concentration gate 能复用 ATPAL1/2 的 ledger 与 audit 口径。

本轮只写合同，不运行 candidate replay，不产生候选策略结果，不选择规则或阈值，不进入 ATPAL4。

## 2. 必须读取

执行者必须读取：

```text
docs/tw_portfolio_decision_model/POLICY_ATPAL_ACTION_TRADE_PNL_ATTRIBUTION_LEDGER_MAINLINE_CN.md
docs/tw_portfolio_decision_model/POLICY_ATPAL2_CONTRIBUTION_AUDIT_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_ATPAL2_CONTRIBUTION_AUDIT_EXECUTION_REPORT_CN.md
data_tw/experiments/action_trade_pnl_attribution_ledger/atpal0_contract/atpal_schema_contract.md
data_tw/experiments/action_trade_pnl_attribution_ledger/atpal0_contract/ledger_table_contract.csv
data_tw/experiments/action_trade_pnl_attribution_ledger/atpal0_contract/field_dictionary.csv
data_tw/experiments/action_trade_pnl_attribution_ledger/atpal1_r_action_context_ledger_repair/manifest.json
data_tw/experiments/action_trade_pnl_attribution_ledger/atpal1_r_action_context_ledger_repair/validator_report.json
data_tw/experiments/action_trade_pnl_attribution_ledger/atpal2_contribution_audit/manifest.json
data_tw/experiments/action_trade_pnl_attribution_ledger/atpal2_contribution_audit/top_contributor_audit.csv
data_tw/experiments/action_trade_pnl_attribution_ledger/atpal2_contribution_audit/baseline_concentration_gate_design.md
data_tw/experiments/action_trade_pnl_attribution_ledger/atpal2_contribution_audit/validator_report.json
```

## 3. 输入与输出

参考输入：

```text
data_tw/experiments/action_trade_pnl_attribution_ledger/atpal0_contract/
data_tw/experiments/action_trade_pnl_attribution_ledger/atpal1_r_action_context_ledger_repair/
data_tw/experiments/action_trade_pnl_attribution_ledger/atpal2_contribution_audit/
```

输出目录：

```text
data_tw/experiments/action_trade_pnl_attribution_ledger/atpal3_candidate_adapter_contract/
```

执行报告：

```text
docs/tw_portfolio_decision_model/POLICY_ATPAL3_CANDIDATE_REPLAY_ADAPTER_CONTRACT_EXECUTION_REPORT_CN.md
```

## 4. 必须输出

必须输出主线指定的 ATPAL3 合同产物：

```text
manifest.json
candidate_replay_adapter_contract.md
candidate_id_mapping_contract.csv
candidate_vs_baseline_delta_contract.csv
candidate_concentration_gate_contract.csv
required_candidate_replay_fields.csv
forbidden_consumer_audit.csv
validator_report.json
```

不得输出 candidate replay ledger、candidate performance result、策略比较结论或任何交易指令。

## 5. Contract 要求

### 5.1 candidate_replay_adapter_contract.md

必须说明：

```text
1. ATPAL3 只定义 adapter contract，不运行 candidate；
2. candidate replay 将来必须复用 ATPAL1 四层账本结构；
3. candidate replay 将来必须产生与 baseline 可对齐的 split/date/instrument/action_trace_id/candidate_id；
4. PnL 字段只能作为 attribution label，不得作为 rule feature；
5. simulated_executed_quantity 只允许作为 diagnostic replay accounting；
6. 禁止 target_weight / target_position / quantity_instruction / broker_order / OrderIntent output；
7. candidate concentration gate 必须复用 ATPAL2 的 concentration metrics；
8. candidate 结果不得绕过 rolling OOS。
```

### 5.2 candidate_id_mapping_contract.csv

至少包含：

```text
field_name
required
description
allowed_values_or_pattern
example
forbidden_semantics
```

必须覆盖：

```text
candidate_id
baseline_candidate_id
candidate_family
candidate_version
candidate_config_hash
replay_engine_version
source_signal_artifact
split
train_window
validation_window
strict_test_declared_only
```

`candidate_id` 是诊断标识，不得表示 production strategy id。

### 5.3 candidate_vs_baseline_delta_contract.csv

至少包含：

```text
delta_field
grain
required
baseline_field
candidate_field
calculation
diagnostic_only
not_rule_feature
notes
```

必须覆盖：

```text
delta_net_return_after_fee_tax
delta_net_return_if_liquidated_at_period_end
delta_fee_tax_total
delta_turnover_proxy
delta_action_count
delta_trade_notional
delta_realized_pnl_after_fee_tax
delta_unrealized_pnl_change
delta_symbol_date_contribution
delta_top1_symbol_contribution_share
delta_top3_symbol_contribution_share
delta_top1_date_contribution_share
delta_top5_date_contribution_share
delta_top1_symbol_date_contribution_share
delta_top10_symbol_date_contribution_share
delta_contribution_hhi
```

### 5.4 candidate_concentration_gate_contract.csv

至少包含：

```text
gate_metric
source_atpal2_metric
grain
required_for_candidate
direction
pass_fail_allowed_in_atpal3
threshold_selection_allowed
notes
```

必须覆盖：

```text
top1_symbol_contribution_share
top3_symbol_contribution_share
top1_date_contribution_share
top5_date_contribution_share
top1_symbol_date_contribution_share
top10_symbol_date_contribution_share
contribution_hhi
positive_contribution_symbol_count
negative_contribution_symbol_count
top_abs_trade_share
top_abs_lifecycle_share
fee_tax_share_of_total_abs_contribution
fee_tax_share_of_trade_notional
turnover_proxy
top_symbol_turnover_share
top_date_turnover_share
```

`pass_fail_allowed_in_atpal3` 必须为 false。ATPAL3 只能定义 future gate，不得设阈值，不得判断候选策略通过。

### 5.5 required_candidate_replay_fields.csv

至少包含：

```text
table_name
field_name
required
data_type
grain
available_before_action
attribution_label_only
diagnostic_only
not_order_instruction
not_rule_feature
source_or_derivation
notes
```

必须覆盖未来 candidate replay 接入 ATPAL 所需字段：

```text
split
strategy_rule
candidate_id
action_trace_id
baseline_action_type
candidate_action_type
signal_date
execution_date
date
instrument
execution_price
simulated_executed_quantity
trade_notional
fee_tax_total
realized_pnl_after_fee_tax
unrealized_pnl_change
net_symbol_date_contribution
position_lifecycle_id
holding_days
market_value
cash_before
cash_after
diagnostic_only
readonly_research_only
not_order_instruction
attribution_label_only
not_rule_feature
```

若字段属于 action/context 且会被未来规则使用，`available_before_action` 必须为 true；若字段是 PnL attribution，`attribution_label_only` 与 `not_rule_feature` 必须为 true。

## 6. Validator 要求

`validator_report.json` 至少检查：

```text
all_required_files_exist
mainline_read
atpal2_review_read
source_atpal0_contract_read
source_atpal1_validator_ok
source_atpal2_validator_ok
candidate_replay_adapter_contract_completed
candidate_id_mapping_contract_completed
candidate_vs_baseline_delta_contract_completed
candidate_concentration_gate_contract_completed
required_candidate_replay_fields_completed
forbidden_consumer_audit_completed
no_candidate_replay_run
no_strategy_experiment_run
rule_selection_run_false
threshold_selection_run_false
strict_test_used_false
model_training_run_false
production_allowed_false
no_order_target_quantity_broker_output
pass_fail_allowed_in_atpal3_false
threshold_selection_allowed_false
```

允许的 final recommendation：

```text
READY_FOR_REVIEWER_TO_CONSIDER_ATPAL4_WORK_DOC
FAIL_NEEDS_ATPAL3_REPAIR
STOP_SOURCE_ATPAL2_INVALID
STOP_CONTRACT_INSUFFICIENT
STOP_FORBIDDEN_CONSUMER_USED
```

## 7. 禁止事项

本轮禁止：

```text
ATPAL4 FPA4 backfill
candidate replay
new strategy replay
candidate performance comparison
candidate pass/fail judgement
候选规则选择
阈值选择
validation mining
strict_test
模型训练
使用 PnL 作为 rule feature
生产默认策略切换
OrderIntent 输出
target_weight / target_position / quantity_instruction
broker_order / quick_trade
provider/latest/monitor/frontend/Agent 集成
```

## 8. 给执行者的命令

```text
请只执行 ATPAL3 Candidate Replay Adapter Contract。

基于 ATPAL0 合同、ATPAL1-R repaired baseline ledger 与 ATPAL2 contribution/concentration audit，
定义未来 candidate replay 如何接入 ATPAL ledger 的 adapter contract、candidate_id mapping、candidate-vs-baseline delta、
candidate concentration gate contract 和 required candidate replay fields。

不得运行 candidate replay，不得跑新策略，不得输出 candidate 结果，不得选择规则或阈值，不得 strict_test，不得训练模型，
不得输出 OrderIntent/target/quantity_instruction/broker，不得触碰生产链路。
```
