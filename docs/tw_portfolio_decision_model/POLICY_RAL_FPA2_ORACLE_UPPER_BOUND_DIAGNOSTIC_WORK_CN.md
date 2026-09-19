---
created_at: 2026-06-23
status: work_order_for_ral_fpa2_oracle_upper_bound_diagnostic
phase: RAL_FPA2_ORACLE_UPPER_BOUND_DIAGNOSTIC
mainline_doc: docs/tw_portfolio_decision_model/POLICY_RAL_FPA_FULL_PATH_BASELINE_PLUS_ACTION_DIAGNOSTIC_MAINLINE_CN.md
prior_review: docs/tw_portfolio_decision_model/POLICY_RAL_FPA1_REPLAY_STATE_CONTRACT_REVIEW_CN.md
prior_work_doc: docs/tw_portfolio_decision_model/POLICY_RAL_FPA1_REPLAY_STATE_CONTRACT_WORK_CN.md
prior_execution_report: docs/tw_portfolio_decision_model/POLICY_RAL_FPA1_REPLAY_STATE_CONTRACT_EXECUTION_REPORT_CN.md
fpa1_artifact_root: data_tw/experiments/full_path_action_diagnostic/fpa1_replay_state_contract
baseline_replay_script: scripts/run_tw_policy_action_model_pa1.py
output_root: data_tw/experiments/full_path_action_diagnostic/fpa2_oracle_upper_bound
execution_report: docs/tw_portfolio_decision_model/POLICY_RAL_FPA2_ORACLE_UPPER_BOUND_DIAGNOSTIC_EXECUTION_REPORT_CN.md
fpa3_authorized: false
fpa4_authorized: false
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
oracle_diagnostic_allowed: true
not_rule_candidate: true
not_investment_advice: true
---

# RAL-FPA2 Oracle-style Upper-bound Diagnostic 工作文档

## 1. 本轮定位

本轮执行：

```text
RAL-FPA2: Oracle-style Upper-bound Diagnostic
```

本轮目标不是写规则，而是用完整 readonly portfolio path diagnostic 判断：

```text
baseline-plus 动作空间是否存在扣费税后超过 baseline 的上界空间。
```

允许 oracle diagnostic 使用事后结果做上界分析，但必须显式标记：

```text
oracle_diagnostic = true
not_rule_candidate = true
not_tradable_strategy = true
strict_test_used = false
```

本轮不是：

```text
FPA3 attribution
FPA4 rule sanity
规则选择
阈值选择
validation mining
strict_test
模型训练
生产或订单集成
```

## 2. 必须读取

执行者必须读取：

```text
docs/tw_portfolio_decision_model/POLICY_RAL_FPA_FULL_PATH_BASELINE_PLUS_ACTION_DIAGNOSTIC_MAINLINE_CN.md
docs/tw_portfolio_decision_model/POLICY_RAL_FPA1_REPLAY_STATE_CONTRACT_WORK_CN.md
docs/tw_portfolio_decision_model/POLICY_RAL_FPA1_REPLAY_STATE_CONTRACT_EXECUTION_REPORT_CN.md
docs/tw_portfolio_decision_model/POLICY_RAL_FPA1_REPLAY_STATE_CONTRACT_REVIEW_CN.md
scripts/run_tw_policy_action_model_pa1.py
```

必须读取 FPA1 artifacts：

```text
data_tw/experiments/full_path_action_diagnostic/fpa1_replay_state_contract/manifest.json
data_tw/experiments/full_path_action_diagnostic/fpa1_replay_state_contract/full_path_replay_state_contract.md
data_tw/experiments/full_path_action_diagnostic/fpa1_replay_state_contract/required_state_field_audit.csv
data_tw/experiments/full_path_action_diagnostic/fpa1_replay_state_contract/action_space_contract.csv
data_tw/experiments/full_path_action_diagnostic/fpa1_replay_state_contract/contract_gap_audit.csv
data_tw/experiments/full_path_action_diagnostic/fpa1_replay_state_contract/forbidden_output_audit.csv
data_tw/experiments/full_path_action_diagnostic/fpa1_replay_state_contract/validator_report.json
```

必须读取 baseline accounting artifacts：

```text
data_tw/experiments/explicit_rule_discovery/ral_ed2_a_baseline_replay_accounting_audit/baseline_replay_source_manifest.json
data_tw/experiments/explicit_rule_discovery/ral_ed2_a_baseline_replay_accounting_audit/baseline_summary_recomputed.json
data_tw/experiments/explicit_rule_discovery/ral_ed2_a_baseline_replay_accounting_audit/baseline_nav_recomputed.csv
data_tw/experiments/explicit_rule_discovery/ral_ed2_a_baseline_replay_accounting_audit/baseline_actions_recomputed.csv
data_tw/experiments/explicit_rule_discovery/ral_ed2_a_baseline_replay_accounting_audit/validator_report.json
```

## 3. 输入与输出

输入：

```text
baseline_signal =
data_tw/artifacts/signals/frozen_qlib_2018_2022/r1_legacy_signal_adapter_20260616/manifest.json

baseline_replay_script =
scripts/run_tw_policy_action_model_pa1.py

fpa1_contract_root =
data_tw/experiments/full_path_action_diagnostic/fpa1_replay_state_contract/
```

输出目录：

```text
data_tw/experiments/full_path_action_diagnostic/fpa2_oracle_upper_bound/
```

执行报告：

```text
docs/tw_portfolio_decision_model/POLICY_RAL_FPA2_ORACLE_UPPER_BOUND_DIAGNOSTIC_EXECUTION_REPORT_CN.md
```

## 4. 必须输出

输出目录必须包含：

```text
manifest.json
source_baseline_manifest.json
replacement_buy_upper_bound.csv
sell_timing_upper_bound.csv
hold_continuation_upper_bound.csv
regime_participation_upper_bound.csv
transaction_cost_marginal_audit.csv
symbol_date_concentration_audit.csv
train_validation_direction_audit.csv
oracle_leakage_boundary_audit.csv
forbidden_consumer_audit.csv
validator_report.json
diagnostic_findings.md
```

还必须输出 FPA1 审查要求的 lineage 产物：

```text
full_path_pre_post_state_lineage.csv
replacement_candidate_lineage.csv
pending_order_state_lineage.csv
```

这些 lineage 产物是 readonly simulation diagnostics，不得被消费为订单、target、broker 或生产字段。

## 5. 必须执行的四类 Diagnostic

### 5.1 replacement_buy_oracle

目标：

```text
当 baseline buy 被 oracle 识别为弱买入时，评估同日候选中替换买入是否存在上界收益。
```

要求：

```text
1. 只能使用同日 PIT candidate slate 作为替换候选集合；
2. 必须保持完整组合路径 replay，不能只算单笔 local delta；
3. 必须记录 baseline candidate、replacement candidate、candidate rank、selected reason namespace；
4. oracle 可用事后结果选择上界，但必须在 oracle_leakage_boundary_audit.csv 标记 not_rule_candidate；
5. 不得把 replacement choice 写成规则或阈值。
```

### 5.2 sell_timing_oracle

目标：

```text
对 baseline sell 评估提前卖、延后卖、继续持有到下一 rebalance 的上界。
```

要求：

```text
1. 使用 full-path replay，不得只比较单笔卖出价；
2. 必须持久化被改动 sell 的 pre_action_state / post_action_state；
3. 必须记录 cash、holding_count、pending order、NAV 的路径变化；
4. 不得输出 sell timing rule 或阈值。
```

### 5.3 hold_continuation_oracle

目标：

```text
对 baseline 准备卖出的持仓，比较继续持有 5/10/20 个交易日的上界空间。
```

要求：

```text
1. 必须记录 entry_date、exact holding_days、cost_basis、mark_price、unrealized_pnl；
2. 必须计算 continuation 对未来买入 slot、现金、持仓数量、费用税和 NAV path 的影响；
3. 不得把 continuation 结果当成持仓建议。
```

### 5.4 regime_participation_oracle

目标：

```text
按 market trend / volatility / drawdown / score dispersion 分桶，评估哪些 regime 下调整参与有正上界。
```

要求：

```text
1. regime 特征只能来自 as-of 历史，不得使用未来收益定义 regime；
2. 输出必须区分 train 与 validation；
3. 必须做 symbol/date concentration audit；
4. 不得选择规则阈值。
```

## 6. Transaction Cost 和 Concentration Gate

`transaction_cost_marginal_audit.csv` 必须检查：

```text
gross_delta
fee_tax_delta
turnover_delta
net_delta_after_fee_tax
cost_covered
```

`symbol_date_concentration_audit.csv` 必须检查：

```text
top_symbol_contribution_share
top_date_contribution_share
top_5_symbol_contribution_share
top_5_date_contribution_share
concentration_gate_status
```

不得用单日/单股集中收益通过 FPA2。

## 7. Train / Validation Direction Audit

`train_validation_direction_audit.csv` 必须按 action_space 输出：

```text
action_space
train_net_delta_after_fee_tax
validation_net_delta_after_fee_tax
train_positive
validation_positive
direction_consistency_status
sample_count_train
sample_count_validation
not_cash_no_trade
not_baseline_clone
eligible_for_reviewer_to_consider_fpa3_work_doc
```

FPA2 通过的最低要求：

```text
至少一个 action_space 在 train 与 validation 都有正 upper-bound；
正收益扣费税后仍为正；
不是 cash/no-trade；
不是 baseline clone；
不是单日/单股集中；
能初步归因到低维可观测特征。
```

## 8. Oracle Leakage Boundary Audit

`oracle_leakage_boundary_audit.csv` 必须逐 action_space 标记：

```text
action_space
uses_future_outcome_for_oracle_selection
oracle_diagnostic_only
not_rule_candidate
not_tradable_strategy
requires_fpa3_attribution_before_rule
strict_test_used
status
notes
```

允许：

```text
uses_future_outcome_for_oracle_selection = true
oracle_diagnostic_only = true
not_rule_candidate = true
```

禁止：

```text
strict_test_used = true
rule_candidate = true
tradable_strategy = true
```

## 9. Forbidden Consumer Audit

`forbidden_consumer_audit.csv` 必须逐项审计：

```text
FPA3
FPA4
strict_test
rule_selection
threshold_selection
model_training
OrderIntent_output
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
```

全部必须：

```text
allowed_in_fpa2 = false
present_in_outputs = false
```

例外：

```text
quantity / cash / nav / execution_price 只能作为 full-path replay internal accounting 字段出现在 lineage diagnostics 中；
不得作为策略、OrderIntent、target、broker 或 production output。
```

## 10. Validator 要求

`validator_report.json` 至少检查：

```text
all_required_files_exist
fpa1_contract_read
baseline_accounting_audit_read
full_path_replay_used
pre_post_state_lineage_persisted
replacement_candidate_lineage_persisted
pending_order_state_lineage_persisted
replacement_buy_upper_bound_completed
sell_timing_upper_bound_completed
hold_continuation_upper_bound_completed
regime_participation_upper_bound_completed
transaction_cost_marginal_audit_completed
symbol_date_concentration_audit_completed
train_validation_direction_audit_completed
oracle_leakage_boundary_audit_completed
strict_test_used_false
fpa3_run_false
fpa4_run_false
rule_selection_run_false
threshold_selection_run_false
model_training_run_false
no_order_target_quantity_broker_output
provider_frontend_agent_production_not_performed
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
READY_FOR_REVIEWER_TO_CONSIDER_FPA3_WORK_DOC
STOP_NO_STABLE_FULL_PATH_UPPER_BOUND
FAIL_NEEDS_FPA2_REPAIR
STOP_ORACLE_LEAKAGE_BOUNDARY_VIOLATION
STOP_FORBIDDEN_CONSUMER_USED
```

## 11. 通过条件

FPA2 通过只代表：

```text
存在值得进入 FPA3 归因诊断的 full-path upper-bound 空间。
```

通过条件：

```text
1. 至少一个动作空间在 train 与 validation 都有正 upper-bound；
2. 正收益扣费税后仍为正；
3. 正收益不是来自单日/单股集中；
4. 不靠 cash/no-trade；
5. 不靠 baseline clone；
6. oracle 泄漏边界被清楚标注为 diagnostic-only；
7. 能初步归因到低维可观测特征；
8. validator ok=true。
```

即使 FPA2 通过，也只允许审查者考虑撰写 FPA3 工作文档，不自动执行 FPA3。

## 12. 失败或停止条件

必须 FAIL 或 STOP 的情况：

```text
1. 所有动作空间 upper-bound 都不稳定或为负；
2. 正收益只存在于 validation 或少数日期；
3. 收益被费用税或换手吃掉；
4. 需要 strict_test 才能判断；
5. 使用未来收益形成了 rule candidate；
6. 结果主要来自 cash/no-trade 或 baseline clone；
7. 输出 OrderIntent、target_weight、target_position、quantity、broker_order 或生产字段；
8. 执行者跑了 FPA3/FPA4、规则选择、阈值选择或模型训练；
9. 未持久化 FPA1 审查要求的 pre/post state lineage。
```

## 13. 执行报告要求

执行报告必须写入：

```text
docs/tw_portfolio_decision_model/POLICY_RAL_FPA2_ORACLE_UPPER_BOUND_DIAGNOSTIC_EXECUTION_REPORT_CN.md
```

执行报告至少包含：

```text
1. Scope
2. Documents / contracts read
3. Source code and artifacts inspected
4. Outputs produced
5. Four action-space diagnostic summary
6. Transaction cost and concentration summary
7. Oracle leakage boundary summary
8. Forbidden consumer audit summary
9. Validator summary
10. Final recommendation
```

执行报告必须明确写：

```text
FPA3 attribution run = false
FPA4 rule sanity run = false
strict_test_used = false
rule_selection_run = false
threshold_selection_run = false
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
2. docs/tw_portfolio_decision_model/POLICY_RAL_FPA1_REPLAY_STATE_CONTRACT_REVIEW_CN.md
3. docs/tw_portfolio_decision_model/POLICY_RAL_FPA2_ORACLE_UPPER_BOUND_DIAGNOSTIC_WORK_CN.md
4. data_tw/experiments/full_path_action_diagnostic/fpa1_replay_state_contract/full_path_replay_state_contract.md
5. scripts/run_tw_policy_action_model_pa1.py

然后只执行 FPA2 Oracle-style Upper-bound Diagnostic。

输出：
data_tw/experiments/full_path_action_diagnostic/fpa2_oracle_upper_bound/

并写执行报告：
docs/tw_portfolio_decision_model/POLICY_RAL_FPA2_ORACLE_UPPER_BOUND_DIAGNOSTIC_EXECUTION_REPORT_CN.md

不得写规则、不得选择阈值、不得 strict_test、不得训练、不得输出订单/target/quantity/broker、不得触碰 provider/latest/monitor/frontend/Agent/production。
```
