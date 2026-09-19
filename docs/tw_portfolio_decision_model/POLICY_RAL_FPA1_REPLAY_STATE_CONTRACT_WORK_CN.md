---
created_at: 2026-06-23
status: work_order_for_ral_fpa1_replay_state_contract_freeze
phase: RAL_FPA1_REPLAY_STATE_CONTRACT_FREEZE
mainline_doc: docs/tw_portfolio_decision_model/POLICY_RAL_FPA_FULL_PATH_BASELINE_PLUS_ACTION_DIAGNOSTIC_MAINLINE_CN.md
previous_review: docs/tw_portfolio_decision_model/POLICY_RAL_ED2_A_BASELINE_REPLAY_ACCOUNTING_AUDIT_REVIEW_CN.md
previous_opinion: docs/tw_portfolio_decision_model/POLICY_RAL_ED2_A_COORDINATOR_POST_AUDIT_OPINION_CN.md
baseline_replay_script: scripts/run_tw_policy_action_model_pa1.py
output_root: data_tw/experiments/full_path_action_diagnostic/fpa1_replay_state_contract
execution_report: docs/tw_portfolio_decision_model/POLICY_RAL_FPA1_REPLAY_STATE_CONTRACT_EXECUTION_REPORT_CN.md
fpa2_oracle_authorized: false
fpa3_attribution_authorized: false
fpa4_rule_sanity_authorized: false
strict_test_authorized: false
rule_selection_authorized: false
threshold_selection_authorized: false
model_training_authorized: false
provider_publish_authorized: false
accepted_latest_switch_authorized: false
monitor_write_authorized: false
frontend_default_switch_authorized: false
agent_authorized: false
broker_authorized: false
order_intent_authorized: false
target_weight_authorized: false
target_position_authorized: false
quantity_authorized: false
production_allowed: false
readonly_only: true
simulation_only: true
not_investment_advice: true
---

# RAL-FPA1 Replay State Contract Freeze 工作文档

## 1. 本轮定位

本轮执行新主线：

```text
RAL-FPA1: Replay State Contract Freeze
```

本轮目标是冻结 full-path readonly replay state contract，确保后续 FPA2 可以在完整组合路径中模拟：

```text
replacement buy
sell timing
hold continuation
regime participation
transaction-cost marginal
```

本轮只做 contract / schema / field availability / forbidden output audit。

本轮不是：

```text
FPA2 oracle upper-bound diagnostic
FPA3 attribution diagnostic
FPA4 rule sanity
strict_test
规则选择
阈值选择
模型训练
生产或订单集成
```

执行者不得被之前 RAL-ED block-buy 路线带偏。本轮不继续删 baseline buy，不调 ED2 阈值，不扩展 block-buy grid。

## 2. 必须读取

执行者必须读取：

```text
docs/tw_portfolio_decision_model/POLICY_RAL_FPA_FULL_PATH_BASELINE_PLUS_ACTION_DIAGNOSTIC_MAINLINE_CN.md
docs/tw_portfolio_decision_model/POLICY_RAL_ED_EXPLICIT_RULE_DISCOVERY_MAINLINE_CN.md
docs/tw_portfolio_decision_model/POLICY_RAL_ED2_A_BASELINE_REPLAY_ACCOUNTING_AUDIT_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_RAL_ED2_A_COORDINATOR_POST_AUDIT_OPINION_CN.md
scripts/run_tw_policy_action_model_pa1.py
```

必须参考项目边界合同：

```text
docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md
docs/tw_modular_contracts/STRATEGY_RULE_CONTRACT_CN.md
docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md
docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md
```

必须读取或引用 baseline accounting 产物：

```text
data_tw/experiments/explicit_rule_discovery/ral_ed2_a_baseline_replay_accounting_audit/manifest.json
data_tw/experiments/explicit_rule_discovery/ral_ed2_a_baseline_replay_accounting_audit/baseline_replay_source_manifest.json
data_tw/experiments/explicit_rule_discovery/ral_ed2_a_baseline_replay_accounting_audit/baseline_summary_recomputed.json
data_tw/experiments/explicit_rule_discovery/ral_ed2_a_baseline_replay_accounting_audit/baseline_nav_recomputed.csv
data_tw/experiments/explicit_rule_discovery/ral_ed2_a_baseline_replay_accounting_audit/baseline_actions_recomputed.csv
data_tw/experiments/explicit_rule_discovery/ral_ed2_a_baseline_replay_accounting_audit/validator_report.json
```

## 3. 输入与输出

输入：

```text
baseline_replay_script =
scripts/run_tw_policy_action_model_pa1.py

baseline_signal =
data_tw/artifacts/signals/frozen_qlib_2018_2022/r1_legacy_signal_adapter_20260616/manifest.json

baseline_accounting_audit_root =
data_tw/experiments/explicit_rule_discovery/ral_ed2_a_baseline_replay_accounting_audit/
```

输出目录：

```text
data_tw/experiments/full_path_action_diagnostic/fpa1_replay_state_contract/
```

执行报告：

```text
docs/tw_portfolio_decision_model/POLICY_RAL_FPA1_REPLAY_STATE_CONTRACT_EXECUTION_REPORT_CN.md
```

## 4. 必须输出

输出目录必须包含：

```text
manifest.json
full_path_replay_state_contract.md
required_state_field_audit.csv
action_space_contract.csv
forbidden_output_audit.csv
validator_report.json
```

建议同时输出：

```text
source_artifact_manifest.json
pa1_replay_field_inventory.csv
contract_gap_audit.csv
diagnostic_findings.md
```

如果执行者认为某个建议文件没有必要，必须在执行报告中说明原因；但 6 个必须文件不可缺失。

## 5. Contract 必须覆盖的 State

`full_path_replay_state_contract.md` 必须定义后续 full-path simulation 需要的 state，至少覆盖：

```text
date / signal_date / execution_date
split
instrument
candidate universe
candidate_rank
buy_score
raw_score
score_rank
full_qlib_rank
score_gap_to_daily_best
rank_gap_to_top50_boundary
current holdings
holding quantity for internal replay accounting only
entry_date
cost_basis
mark_price
unrealized_pnl
holding_days
cash
market_value
equity / nav
daily_return
holding_count
pending orders by execution_date
execution price policy
fee_rate
sell_tax_rate
turnover
market regime
volatility bucket
liquidity bucket
missing price status
```

注意：

```text
quantity / cash / nav / execution_price 等字段只能是 replay 内部 simulation accounting 字段；
不得作为策略输出、订单输出或生产消费字段。
```

## 6. Action Space Contract

`action_space_contract.csv` 必须逐行定义每类 simulation-only action：

```text
replacement_buy
sell_timing_advance
sell_timing_delay
hold_continuation
regime_participation_adjustment
transaction_cost_marginal_filter
```

每一行至少包含：

```text
action_space
simulation_action_type
baseline_action_context
allowed_internal_state_fields
required_price_policy
required_fee_tax_policy
path_dependency
can_change_cash
can_change_holdings
can_change_pending_orders
production_output_allowed
order_output_allowed
target_output_allowed
oracle_allowed_in_fpa1
rule_replay_allowed_in_fpa1
notes
```

FPA1 中：

```text
production_output_allowed = false
order_output_allowed = false
target_output_allowed = false
oracle_allowed_in_fpa1 = false
rule_replay_allowed_in_fpa1 = false
```

## 7. Required Field Audit

`required_state_field_audit.csv` 必须逐字段审计：

```text
field_name
field_category
required_for_action_spaces
source_location
available_now
source_artifact_or_code
pit_safe
simulation_only
production_output_allowed
missing_status
repair_required_before_fpa2
notes
```

字段状态只能使用：

```text
available
available_with_transform
missing_repair_required
missing_blocker
forbidden_as_output
not_required_for_fpa2
```

如果 replacement buy、sell timing、hold continuation 或 regime participation 所需关键字段缺失，必须诚实标记，不得用虚构字段通过 validator。

## 8. PA1 Replay Field Inventory

执行者必须从 `scripts/run_tw_policy_action_model_pa1.py` 梳理现有 replay 能提供的字段来源，例如：

```text
PriceStore.close_on_or_before
PriceStore.open_after
baseline_trade_intents
make_order_row
execute_pending
replay_window summary / nav / actions / snapshots / order_rows
sample_from_intent state_feature_*
market_regime
volatility_bucket
liquidity_bucket
```

但不得把 PA1 旧的 `write_order_intent_artifact` 当作 FPA1 输出合同。FPA1 的目标是 full-path simulation state contract，不是生成 OrderIntentArtifact。

## 9. Forbidden Output Audit

`forbidden_output_audit.csv` 必须逐项审计：

```text
OrderIntent
target_weight
target_position
quantity
broker_order
quick_trade
provider_publish
accepted_latest_switch
monitor_write
frontend_default_switch
Agent_recommendation
production_default_strategy
strict_test
model_training
rule_selection
threshold_selection
oracle_replay
rule_replay
```

每一行至少包含：

```text
consumer_or_action
status
allowed_in_fpa1
present_in_outputs
notes
```

所有上述项在 FPA1 中必须：

```text
allowed_in_fpa1 = false
present_in_outputs = false
```

例外说明：

```text
quantity / cash / nav / execution_price 可以作为 internal replay accounting 字段被 contract 描述，
但不得作为 OrderIntent、target、broker 或生产输出字段。
```

## 10. Validator 要求

`validator_report.json` 至少检查：

```text
all_required_files_exist
mainline_read
pa1_replay_script_read
baseline_accounting_audit_read
contract_defines_replacement_buy_state
contract_defines_sell_timing_state
contract_defines_hold_continuation_state
contract_defines_regime_participation_state
contract_defines_transaction_cost_marginal_state
required_state_field_audit_complete
action_space_contract_complete
forbidden_output_audit_complete
no_oracle_run
no_rule_replay_run
no_rule_selection_run
no_threshold_selection_run
strict_test_used_false
model_training_run_false
no_order_intent_output
no_target_weight_output
no_target_position_output
no_quantity_output_as_strategy_or_order
no_broker_order_output
provider_frontend_agent_production_not_performed
missing_fields_marked_explicitly
```

validator 必须包含：

```text
ok
status
phase
failed_count
final_recommendation
checks
```

允许的 `final_recommendation` 只有：

```text
READY_FOR_REVIEWER_TO_CONSIDER_FPA2_WORK_DOC
FAIL_NEEDS_CONTRACT_REPAIR
STOP_FIELD_BLOCKER
```

## 11. 通过条件

FPA1 通过只代表：

```text
full-path readonly replay state contract 足以支持审查者撰写 FPA2 oracle upper-bound diagnostic 工作文档。
```

通过条件：

```text
1. contract 覆盖 replacement buy / sell timing / hold continuation / regime participation / transaction-cost marginal；
2. 每类动作的必要 state 字段都有来源或明确 transform；
3. PIT-safe 和 future/oracle 边界被清楚标注；
4. simulation-only 字段与生产/订单/target 字段边界清楚；
5. forbidden output audit 全部通过；
6. validator ok=true；
7. 执行报告没有提前请求 FPA2 执行、FPA3、FPA4、strict_test、训练或生产集成。
```

## 12. 失败或停止条件

必须 FAIL 或 STOP 的情况：

```text
1. contract 不能支持完整路径 replay；
2. replacement buy / sell timing / hold continuation / regime participation 中任一核心动作空间缺字段且未标明；
3. 需要 target_weight / target_position / quantity 作为策略输出才能继续；
4. 需要 OrderIntent / broker / quick_trade / production consumer 才能继续；
5. 执行者跑了 oracle、规则回测、阈值选择、strict_test 或模型训练；
6. validator 缺失或 failed_count > 0；
7. 用旧 ED2 block-buy route 替代 FPA full-path contract。
```

如果只是字段缺口但可在 FPA1-R 修复，应返回：

```text
FAIL_NEEDS_CONTRACT_REPAIR
```

如果缺口显示 full-path replay 根本缺少不可替代的输入，应返回：

```text
STOP_FIELD_BLOCKER
```

## 13. 执行报告要求

执行报告必须写入：

```text
docs/tw_portfolio_decision_model/POLICY_RAL_FPA1_REPLAY_STATE_CONTRACT_EXECUTION_REPORT_CN.md
```

执行报告至少包含：

```text
1. Scope
2. Documents / contracts read
3. Source code and artifacts inspected
4. Outputs produced
5. State fields covered
6. Missing fields or blockers
7. Forbidden action audit summary
8. Validator summary
9. Final recommendation
```

执行报告必须明确写：

```text
FPA2 oracle run = false
FPA3 attribution run = false
FPA4 rule sanity run = false
strict_test_used = false
model_training_run = false
production_allowed = false
OrderIntent_output = false
target_weight_output = false
target_position_output = false
quantity_or_broker_output = false
```

## 14. 给执行者的命令

```text
请严格阅读：
1. docs/tw_portfolio_decision_model/POLICY_RAL_FPA_FULL_PATH_BASELINE_PLUS_ACTION_DIAGNOSTIC_MAINLINE_CN.md
2. docs/tw_portfolio_decision_model/POLICY_RAL_ED_EXPLICIT_RULE_DISCOVERY_MAINLINE_CN.md
3. docs/tw_portfolio_decision_model/POLICY_RAL_ED2_A_BASELINE_REPLAY_ACCOUNTING_AUDIT_REVIEW_CN.md
4. docs/tw_portfolio_decision_model/POLICY_RAL_ED2_A_COORDINATOR_POST_AUDIT_OPINION_CN.md
5. scripts/run_tw_policy_action_model_pa1.py

然后只执行 FPA1 Replay State Contract Freeze。

输出：
data_tw/experiments/full_path_action_diagnostic/fpa1_replay_state_contract/

并写执行报告：
docs/tw_portfolio_decision_model/POLICY_RAL_FPA1_REPLAY_STATE_CONTRACT_EXECUTION_REPORT_CN.md

不得跑 FPA2 oracle、不得跑规则、不得选择阈值、不得 strict_test、不得训练、不得输出订单/target/quantity/broker、不得触碰 provider/latest/monitor/frontend/Agent/production。
```
