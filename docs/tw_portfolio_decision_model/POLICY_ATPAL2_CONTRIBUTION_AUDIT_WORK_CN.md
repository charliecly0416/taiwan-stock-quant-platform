---
created_at: 2026-06-23
status: work_order_for_atpal2_contribution_concentration_audit
phase: ATPAL2_CONTRIBUTION_CONCENTRATION_AUDIT
mainline_doc: docs/tw_portfolio_decision_model/POLICY_ATPAL_ACTION_TRADE_PNL_ATTRIBUTION_LEDGER_MAINLINE_CN.md
prior_review: docs/tw_portfolio_decision_model/POLICY_ATPAL1_R_ACTION_CONTEXT_LEDGER_REPAIR_REVIEW_CN.md
prior_execution_report: docs/tw_portfolio_decision_model/POLICY_ATPAL1_R_ACTION_CONTEXT_LEDGER_REPAIR_EXECUTION_REPORT_CN.md
source_atpal1_root: data_tw/experiments/action_trade_pnl_attribution_ledger/atpal1_r_action_context_ledger_repair
output_root: data_tw/experiments/action_trade_pnl_attribution_ledger/atpal2_contribution_audit
execution_report: docs/tw_portfolio_decision_model/POLICY_ATPAL2_CONTRIBUTION_AUDIT_EXECUTION_REPORT_CN.md
atpal2_authorized: true
atpal3_authorized: false
atpal4_authorized: false
strategy_experiment_authorized: false
rule_selection_authorized: false
threshold_selection_authorized: false
strict_test_authorized: false
model_training_authorized: false
production_allowed: false
readonly_only: true
simulation_only: true
---

# ATPAL2 Contribution / Concentration Audit 工作文档

## 1. 本轮定位

本轮只执行：

```text
ATPAL2: Concentration / Contribution Audit
```

目标是基于 ATPAL1-R baseline ledger，生成 baseline 的 symbol/date/trade/position/fee/turnover contribution audit，并设计 baseline concentration gate。

本轮仍然不找策略，不运行 candidate，不进入 ATPAL3/4，不做规则选择、阈值选择、strict_test、模型训练或生产集成。

## 2. 必须读取

执行者必须读取：

```text
docs/tw_portfolio_decision_model/POLICY_ATPAL_ACTION_TRADE_PNL_ATTRIBUTION_LEDGER_MAINLINE_CN.md
docs/tw_portfolio_decision_model/POLICY_ATPAL1_R_ACTION_CONTEXT_LEDGER_REPAIR_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_ATPAL1_R_ACTION_CONTEXT_LEDGER_REPAIR_EXECUTION_REPORT_CN.md
data_tw/experiments/action_trade_pnl_attribution_ledger/atpal1_r_action_context_ledger_repair/manifest.json
data_tw/experiments/action_trade_pnl_attribution_ledger/atpal1_r_action_context_ledger_repair/symbol_date_pnl_ledger.csv
data_tw/experiments/action_trade_pnl_attribution_ledger/atpal1_r_action_context_ledger_repair/trade_level_pnl_ledger.csv
data_tw/experiments/action_trade_pnl_attribution_ledger/atpal1_r_action_context_ledger_repair/position_lifecycle_ledger.csv
data_tw/experiments/action_trade_pnl_attribution_ledger/atpal1_r_action_context_ledger_repair/cash_fee_tax_ledger.csv
data_tw/experiments/action_trade_pnl_attribution_ledger/atpal1_r_action_context_ledger_repair/fee_tax_turnover_reconciliation_audit.csv
data_tw/experiments/action_trade_pnl_attribution_ledger/atpal1_r_action_context_ledger_repair/validator_report.json
```

## 3. 输入与输出

输入：

```text
source_atpal1_root =
data_tw/experiments/action_trade_pnl_attribution_ledger/atpal1_r_action_context_ledger_repair/
```

输出目录：

```text
data_tw/experiments/action_trade_pnl_attribution_ledger/atpal2_contribution_audit/
```

执行报告：

```text
docs/tw_portfolio_decision_model/POLICY_ATPAL2_CONTRIBUTION_AUDIT_EXECUTION_REPORT_CN.md
```

## 4. 必须输出

必须输出：

```text
manifest.json
symbol_contribution_summary.csv
date_contribution_summary.csv
symbol_date_contribution_matrix.csv
top_contributor_audit.csv
trade_pnl_distribution_audit.csv
position_lifecycle_distribution_audit.csv
fee_tax_contribution_audit.csv
turnover_contribution_audit.csv
baseline_concentration_gate_design.md
forbidden_consumer_audit.csv
validator_report.json
diagnostic_findings.md
```

## 5. Audit 口径

### 5.1 Symbol Contribution

`symbol_contribution_summary.csv` 至少包含：

```text
split
instrument
net_contribution
abs_contribution
positive_contribution
negative_contribution
contribution_share_of_total_abs
trade_count
active_day_count
rank_by_abs_contribution
```

### 5.2 Date Contribution

`date_contribution_summary.csv` 至少包含：

```text
split
date
net_contribution
abs_contribution
positive_contribution
negative_contribution
contribution_share_of_total_abs
symbol_count
trade_count
rank_by_abs_contribution
```

### 5.3 Symbol-date Matrix

`symbol_date_contribution_matrix.csv` 必须来自 ATPAL1-R 的 `symbol_date_pnl_ledger.csv`，至少包含：

```text
split
date
instrument
net_symbol_date_contribution
abs_contribution
contribution_share_of_total_abs
rank_by_abs_contribution
```

### 5.4 Top Contributor Audit

`top_contributor_audit.csv` 必须计算主线要求的 concentration metrics：

```text
top1_symbol_contribution_share
top3_symbol_contribution_share
top1_date_contribution_share
top5_date_contribution_share
top1_symbol_date_contribution_share
top10_symbol_date_contribution_share
positive_contribution_symbol_count
negative_contribution_symbol_count
contribution_hhi
```

必须按：

```text
split = train, validation, all
```

分别输出。

### 5.5 Trade / Position Distribution

`trade_pnl_distribution_audit.csv` 至少包含：

```text
split
trade_count
mean_realized_pnl_after_fee_tax
median_realized_pnl_after_fee_tax
p10_realized_pnl_after_fee_tax
p90_realized_pnl_after_fee_tax
positive_trade_count
negative_trade_count
top_abs_trade_share
```

`position_lifecycle_distribution_audit.csv` 至少包含：

```text
split
position_lifecycle_count
closed_count
open_at_period_end_count
mean_net_pnl_after_fee_tax
median_net_pnl_after_fee_tax
p10_net_pnl_after_fee_tax
p90_net_pnl_after_fee_tax
top_abs_lifecycle_share
```

### 5.6 Fee / Turnover Contribution

`fee_tax_contribution_audit.csv` 至少包含：

```text
split
fee_tax_total
gross_positive_contribution
gross_negative_contribution
fee_tax_share_of_total_abs_contribution
fee_tax_share_of_trade_notional
```

`turnover_contribution_audit.csv` 至少包含：

```text
split
trade_notional_sum
average_equity
turnover_proxy
trade_count
buy_count
sell_count
top_symbol_turnover_share
top_date_turnover_share
```

## 6. Baseline Concentration Gate Design

`baseline_concentration_gate_design.md` 只能设计 future candidate gate，不得评价新策略。

必须说明：

```text
1. ATPAL2 是 baseline diagnostic，不是 strategy pass；
2. future candidate 需要证明收益不是来自单一 symbol/date/symbol-date；
3. 推荐 candidate-level gate 应复用 top contributor、HHI、trade distribution、fee/turnover metrics；
4. 不得用 ATPAL2 结果直接选择规则或阈值；
5. 不得绕过 rolling OOS。
```

## 7. Validator 要求

`validator_report.json` 至少检查：

```text
all_required_files_exist
mainline_read
atpal1_repair_review_read
source_atpal1_validator_ok
source_is_repaired_atpal1
symbol_contribution_summary_completed
date_contribution_summary_completed
symbol_date_matrix_completed
top_contributor_audit_completed
trade_pnl_distribution_completed
position_lifecycle_distribution_completed
fee_tax_contribution_completed
turnover_contribution_completed
baseline_concentration_gate_design_completed
train_validation_all_splits_present
no_candidate_replay_run
no_strategy_experiment_run
rule_selection_run_false
threshold_selection_run_false
strict_test_used_false
model_training_run_false
production_allowed_false
no_order_target_quantity_broker_output
```

允许的 final recommendation：

```text
READY_FOR_REVIEWER_TO_CONSIDER_ATPAL3_WORK_DOC
FAIL_NEEDS_ATPAL2_REPAIR
STOP_SOURCE_ATPAL1_INVALID
STOP_CONTRIBUTION_AUDIT_INSUFFICIENT
STOP_FORBIDDEN_CONSUMER_USED
```

## 8. 禁止事项

本轮禁止：

```text
ATPAL3 candidate adapter
ATPAL4 FPA4 backfill
candidate replay
新策略 replay
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

## 9. 给执行者的命令

```text
请只执行 ATPAL2 Contribution / Concentration Audit。

基于 ATPAL1-R repaired baseline ledger，生成 baseline 的 symbol/date/symbol-date/trade/position/fee/turnover contribution audit，
并设计 baseline_concentration_gate_design.md。

不得进入 ATPAL3/4，不得运行 candidate replay 或新策略，不得选择规则或阈值，不得 strict_test，不得训练模型，
不得输出 OrderIntent/target/quantity_instruction/broker，不得触碰生产链路。
```
