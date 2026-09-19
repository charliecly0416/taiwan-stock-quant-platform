---
created_at: 2026-06-23
status: work_order_for_atpal1_action_context_ledger_repair
phase: ATPAL1_R_ACTION_CONTEXT_LEDGER_REPAIR
mainline_doc: docs/tw_portfolio_decision_model/POLICY_ATPAL_ACTION_TRADE_PNL_ATTRIBUTION_LEDGER_MAINLINE_CN.md
prior_review: docs/tw_portfolio_decision_model/POLICY_ATPAL1_BASELINE_LEDGER_BUILDER_REVIEW_CN.md
prior_execution_report: docs/tw_portfolio_decision_model/POLICY_ATPAL1_BASELINE_LEDGER_BUILDER_EXECUTION_REPORT_CN.md
source_artifact_root: data_tw/experiments/action_trade_pnl_attribution_ledger/atpal1_baseline_ledger
output_root: data_tw/experiments/action_trade_pnl_attribution_ledger/atpal1_r_action_context_ledger_repair
execution_report: docs/tw_portfolio_decision_model/POLICY_ATPAL1_R_ACTION_CONTEXT_LEDGER_REPAIR_EXECUTION_REPORT_CN.md
atpal1_repair_authorized: true
atpal2_authorized: false
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

# ATPAL1-R Action Context Ledger Repair 工作文档

## 1. 本轮定位

本轮仍属于 ATPAL1 repair：

```text
ATPAL1-R: Action Context Ledger Repair
```

目标是修复 ATPAL1 中 `action_context_ledger.csv` 未正确记录 action 前持仓状态、且无法直接连接 trade ledger 的问题。

本轮不是 ATPAL2，不做 concentration audit；不是 ATPAL3/4；不得跑新策略、规则选择、阈值选择、strict_test、模型训练或生产链路。

## 2. 必须读取

执行者必须读取：

```text
docs/tw_portfolio_decision_model/POLICY_ATPAL_ACTION_TRADE_PNL_ATTRIBUTION_LEDGER_MAINLINE_CN.md
docs/tw_portfolio_decision_model/POLICY_ATPAL1_BASELINE_LEDGER_BUILDER_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_ATPAL1_BASELINE_LEDGER_BUILDER_EXECUTION_REPORT_CN.md
docs/tw_portfolio_decision_model/POLICY_ATPAL1_BASELINE_LEDGER_BUILDER_WORK_CN.md
data_tw/experiments/action_trade_pnl_attribution_ledger/atpal0_contract/field_dictionary.csv
data_tw/experiments/action_trade_pnl_attribution_ledger/atpal0_contract/reconciliation_rule_contract.csv
scripts/build_tw_policy_atpal1_baseline_ledger.py
scripts/run_tw_policy_action_model_pa1.py
```

## 3. 输入与输出

输入：

```text
source_artifact_root =
data_tw/experiments/action_trade_pnl_attribution_ledger/atpal1_baseline_ledger/
```

输出目录：

```text
data_tw/experiments/action_trade_pnl_attribution_ledger/atpal1_r_action_context_ledger_repair/
```

执行报告：

```text
docs/tw_portfolio_decision_model/POLICY_ATPAL1_R_ACTION_CONTEXT_LEDGER_REPAIR_EXECUTION_REPORT_CN.md
```

## 4. 必须修复

必须重新生成 ATPAL1 全套产物或至少完整重写与 action context / validator 相关的产物，并输出到新 repair 目录。

必须输出：

```text
manifest.json
source_artifact_manifest.json
trade_level_pnl_ledger.csv
position_lifecycle_ledger.csv
position_day_pnl_ledger.csv
symbol_date_pnl_ledger.csv
action_context_ledger.csv
cash_fee_tax_ledger.csv
baseline_summary_reconciliation.csv
nav_reconciliation_audit.csv
fee_tax_turnover_reconciliation_audit.csv
missing_price_audit.csv
forbidden_field_audit.csv
action_context_linkage_audit.csv
action_context_pre_state_audit.csv
validator_report.json
diagnostic_findings.md
```

## 5. Action Context 构建要求

`action_context_ledger.csv` 必须从每个 signal_date 的 pre-action portfolio state 构建。

对 sell action，必须计算：

```text
holding_days_before > 0 for normal held positions
unrealized_return_before = mark_price_before_action / cost_basis - 1
```

要求：

```text
1. 对 executed sell，若 action 前有持仓，holding_days_before 不得系统性为 0；
2. unrealized_return_before 必须来自 signal_date 或 action 前可用 close/mark；
3. 不得使用 execution_date 之后价格；
4. 不得使用 realized PnL 或未来收益作为 action feature；
5. 所有 context 字段必须标记 available_before_action=true；
6. PnL 字段仍只能作为 attribution label，不得进入 action context。
```

## 6. Linkage 要求

必须使 `action_context_ledger` 与 `trade_level_pnl_ledger` 可直接追溯。

允许两种方式之一：

```text
1. action_context_ledger.action_trace_id 与 trade_level_pnl_ledger.action_trace_id 对 executed actions 直接一致；
2. 若保留 context 自身 id，必须新增 executed_trade_action_trace_id，并保证 executed actions 100% 可连接到 trade_level_pnl_ledger.action_trace_id。
```

必须输出：

```text
action_context_linkage_audit.csv
```

字段至少包含：

```text
audit_name
split
trade_action_count
context_executed_action_count
direct_linked_count
missing_context_count
orphan_context_count
linkage_rate
status
```

通过要求：

```text
missing_context_count = 0
linkage_rate = 1.0
```

允许存在 skip / non-executed context，但必须清楚标记：

```text
executed_trade_linked = false
non_executed_or_skipped_intent = true
```

## 7. Pre-state Audit 要求

必须输出：

```text
action_context_pre_state_audit.csv
```

字段至少包含：

```text
audit_name
split
sell_context_count
sell_context_with_holding_days_before_positive
sell_context_with_unrealized_return_before_available
sell_holding_days_positive_rate
sell_unrealized_return_available_rate
status
```

通过要求：

```text
executed sell context 的 holding_days_before / unrealized_return_before 覆盖率必须合理；
不得出现当前版本这种 sell context 几乎全部为 0 的情况。
```

如果存在 same-day entry/exit 或无法计算的边界情况，必须单独解释并计数。

## 8. Reconciliation 要求

修复 action context 不得破坏原 ATPAL1 reconciliation：

```text
net_return_after_fee_tax absolute diff <= 1e-6
fee_and_tax absolute diff <= 0.01
turnover_proxy absolute diff <= 1e-6
action_count diff = 0
missing_price_count diff = 0
negative_cash_count diff = 0
```

必须继续复现 2025 validation baseline：

```text
net_return_after_fee_tax = 0.95376753
net_return_if_liquidated_at_period_end = 0.94512277
fee_and_tax = 146214.73
turnover_proxy = 42.18778217
missing_price_count = 0
negative_cash_count = 0
```

## 9. Validator 要求

`validator_report.json` 至少新增并检查：

```text
action_context_pre_state_audit_exists
action_context_linkage_audit_exists
sell_context_holding_days_before_coverage_pass
sell_context_unrealized_return_before_coverage_pass
action_context_trade_linkage_rate_1
missing_context_count_zero
orphan_executed_context_count_zero
action_context_built_from_pre_action_state
pnl_not_used_as_action_feature
future_price_not_used_as_action_feature
```

同时保留 ATPAL1 原有检查：

```text
baseline_only
train_validation_only
strict_test_not_used
all_ledgers_built
all_reconciliation_pass
forbidden_field_audit_completed
atpal2_not_run
atpal3_not_run
atpal4_not_run
strategy_experiment_not_run
rule_selection_run_false
threshold_selection_run_false
model_training_run_false
production_allowed_false
```

允许的 final recommendation：

```text
READY_FOR_REVIEWER_TO_CONSIDER_ATPAL2_WORK_DOC
FAIL_NEEDS_ATPAL1_REPAIR
STOP_BASELINE_RECONCILIATION_FAILED
STOP_ACTION_CONTEXT_PRE_STATE_INVALID
STOP_ACTION_TRADE_LINKAGE_INVALID
STOP_FORBIDDEN_FIELD_OR_PRODUCTION_SEMANTICS
```

## 10. 禁止事项

本轮禁止：

```text
ATPAL2 contribution audit
ATPAL3 candidate adapter
ATPAL4 FPA4 backfill
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

## 11. 给执行者的命令

```text
请只执行 ATPAL1-R Action Context Ledger Repair。

修复 action_context_ledger，使 sell action 的 holding_days_before / unrealized_return_before 来自 signal_date 的 pre-action portfolio state，
并让 action_context 与 trade_level_pnl_ledger 可直接 100% 追溯。新增 action_context_linkage_audit 和 action_context_pre_state_audit。

不得进入 ATPAL2/3/4，不得跑新策略，不得选择规则或阈值，不得 strict_test，不得训练模型，
不得输出 OrderIntent/target/quantity_instruction/broker，不得触碰生产链路。
```
