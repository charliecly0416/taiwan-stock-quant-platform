---
created_at: 2026-06-23
status: work_order_for_atpal1_baseline_ledger_builder
phase: ATPAL1_BASELINE_LEDGER_BUILDER
mainline_doc: docs/tw_portfolio_decision_model/POLICY_ATPAL_ACTION_TRADE_PNL_ATTRIBUTION_LEDGER_MAINLINE_CN.md
prior_review: docs/tw_portfolio_decision_model/POLICY_ATPAL0_SCHEMA_CONTRACT_REVIEW_CN.md
prior_execution_report: docs/tw_portfolio_decision_model/POLICY_ATPAL0_SCHEMA_CONTRACT_EXECUTION_REPORT_CN.md
source_contract_root: data_tw/experiments/action_trade_pnl_attribution_ledger/atpal0_contract
output_root: data_tw/experiments/action_trade_pnl_attribution_ledger/atpal1_baseline_ledger
execution_report: docs/tw_portfolio_decision_model/POLICY_ATPAL1_BASELINE_LEDGER_BUILDER_EXECUTION_REPORT_CN.md
atpal1_authorized: true
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
not_order: true
not_target_weight: true
not_target_position: true
not_quantity_instruction: true
---

# ATPAL1 Baseline Ledger Builder 工作文档

## 1. 本轮定位

本轮只执行：

```text
ATPAL1: Baseline Ledger Builder
```

目标是基于可信 baseline replay 生成 train + validation 的四层 Action / Trade PnL Attribution Ledger，并通过 ATPAL0 定义的 reconciliation gate。

本轮不是策略实验，不是规则搜索，不是阈值选择，不是 ATPAL2 concentration audit，不是 ATPAL3 candidate adapter，不是 ATPAL4 FPA4 backfill。

## 2. 必须读取

执行者必须读取：

```text
docs/tw_portfolio_decision_model/POLICY_ATPAL_ACTION_TRADE_PNL_ATTRIBUTION_LEDGER_MAINLINE_CN.md
docs/tw_portfolio_decision_model/POLICY_ATPAL0_SCHEMA_CONTRACT_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_ATPAL0_SCHEMA_CONTRACT_EXECUTION_REPORT_CN.md
data_tw/experiments/action_trade_pnl_attribution_ledger/atpal0_contract/atpal_schema_contract.md
data_tw/experiments/action_trade_pnl_attribution_ledger/atpal0_contract/ledger_table_contract.csv
data_tw/experiments/action_trade_pnl_attribution_ledger/atpal0_contract/field_dictionary.csv
data_tw/experiments/action_trade_pnl_attribution_ledger/atpal0_contract/reconciliation_rule_contract.csv
data_tw/experiments/action_trade_pnl_attribution_ledger/atpal0_contract/pnl_component_definition.csv
data_tw/experiments/action_trade_pnl_attribution_ledger/atpal0_contract/forbidden_field_audit.csv
scripts/run_tw_policy_action_model_pa1.py
docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md
docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md
```

## 3. 输入与输出

输入：

```text
baseline_signal_artifact =
data_tw/artifacts/signals/frozen_qlib_2018_2022/r1_legacy_signal_adapter_20260616/manifest.json

baseline_replay_engine =
scripts/run_tw_policy_action_model_pa1.py

baseline_rule =
top50_exit_one_worst_sell

atpal0_contract_root =
data_tw/experiments/action_trade_pnl_attribution_ledger/atpal0_contract/
```

输出目录：

```text
data_tw/experiments/action_trade_pnl_attribution_ledger/atpal1_baseline_ledger/
```

执行报告：

```text
docs/tw_portfolio_decision_model/POLICY_ATPAL1_BASELINE_LEDGER_BUILDER_EXECUTION_REPORT_CN.md
```

## 4. 必须输出

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
validator_report.json
diagnostic_findings.md
```

## 5. Scope

只允许生成 baseline ledger：

```text
strategy_rule = top50_exit_one_worst_sell
candidate_id = baseline
splits = train, validation
```

窗口：

```text
train = 2023-01-01..2024-12-31
validation = 2025-01-01..2025-12-31
```

不得使用：

```text
strict_test = 2026-01-01..2026-05-07
```

## 6. Ledger Builder 要求

账本必须从 replay state/actions/NAV/position snapshots 生成，不得从 summary 反推。

必须保留或可追溯：

```text
signal_date
execution_date
mark_date
instrument
action_type
price_source
strategy_rule
split
action_trace_id
position_lifecycle_id
```

### 6.1 trade_level_pnl_ledger

每笔 simulated executed buy/sell 一行。

必须使用 ATPAL0 字段词典中的：

```text
simulated_executed_quantity
```

不得输出：

```text
quantity_instruction
target_weight
target_position
broker_order
OrderIntent output
```

### 6.2 position_lifecycle_ledger

每段 position lifecycle 一行。

必须覆盖：

```text
closed
open_at_period_end
forced_liquidation_diagnostic
```

若 period end 仍持仓，不得伪造成真实卖出；只能记录未实现 PnL 或 diagnostic liquidation label。

### 6.3 position_day_pnl_ledger

每日持仓 mark-to-market 一行。

正式 ATPAL 字段必须使用：

```text
simulated_position_quantity
```

若读取源 replay snapshot 的 `quantity`，必须只作为 source accounting input，并在输出中避免 instruction 语义。

### 6.4 symbol_date_pnl_ledger

必须聚合每个 symbol-date 的：

```text
realized_pnl_after_fee_tax
unrealized_pnl_change
fee_tax_total
net_symbol_date_contribution
abs_contribution
contribution_share_of_total_abs
```

该表是 ATPAL2 concentration audit 的基础，必须完整覆盖 train + validation。

### 6.5 action_context_ledger

必须只使用 action 前可用字段作为 context：

```text
candidate_rank
score
score_rank
full_qlib_rank
holding_days_before
unrealized_return_before
market_regime
available_before_action
```

PnL 字段不得进入 action feature/context。

## 7. Reconciliation Gate

必须按 ATPAL0 `reconciliation_rule_contract.csv` 输出 audit，并满足：

```text
net_return_after_fee_tax absolute diff <= 1e-6
fee_and_tax absolute diff <= 0.01
turnover_proxy absolute diff <= 1e-6
action_count diff = 0
missing_price_count diff = 0
negative_cash_count diff = 0
```

必须复现 2025 validation baseline：

```text
net_return_after_fee_tax = 0.95376753
net_return_if_liquidated_at_period_end = 0.94512277
fee_and_tax = 146214.73
turnover_proxy = 42.18778217
missing_price_count = 0
negative_cash_count = 0
```

还必须输出：

```text
realized + unrealized + cash movement reconciliation
```

若无法 reconciliation，必须 STOP，不得进入 ATPAL2。

## 8. Forbidden Field Audit

`forbidden_field_audit.csv` 必须检查：

```text
target_weight
target_position
quantity_instruction
quantity_to_buy
quantity_to_sell
broker_order
broker_order_id
quick_trade
OrderIntent output
provider_publish
accepted_latest_switch
monitor_write
frontend_default_switch
Agent_recommendation
production_strategy_switch
strict_test
model_training
rule_selection
threshold_selection
validation_mining
future_return_as_action_feature
future_price_as_action_feature
pnl_used_as_rule_feature
```

允许出现的数量字段仅限：

```text
simulated_executed_quantity
simulated_position_quantity
```

且都必须标记为 diagnostic accounting，不得是 instruction。

## 9. Validator 要求

`validator_report.json` 至少检查：

```text
all_required_files_exist
mainline_read
atpal0_review_read
atpal0_contract_loaded
baseline_only
train_validation_only
strict_test_not_used
trade_level_ledger_built
position_lifecycle_ledger_built
position_day_ledger_built
symbol_date_ledger_built
action_context_ledger_built
cash_fee_tax_ledger_built
final_equity_reconciliation_pass
net_return_after_fee_tax_reconciliation_pass
fee_and_tax_reconciliation_pass
turnover_proxy_reconciliation_pass
action_count_reconciliation_pass
realized_unrealized_cash_nav_reconciliation_pass
missing_price_reconciliation_pass
negative_cash_reconciliation_pass
baseline_2025_metrics_reproduced
forbidden_field_audit_completed
simulated_quantities_diagnostic_only
quantity_instruction_forbidden
target_weight_forbidden
target_position_forbidden
broker_order_forbidden
pnl_not_used_as_rule_feature
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
STOP_FORBIDDEN_FIELD_OR_PRODUCTION_SEMANTICS
STOP_LEDGER_INSUFFICIENT_FOR_SYMBOL_DATE_CONCENTRATION
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

## 11. 执行报告要求

执行报告必须写入：

```text
docs/tw_portfolio_decision_model/POLICY_ATPAL1_BASELINE_LEDGER_BUILDER_EXECUTION_REPORT_CN.md
```

报告至少包含：

```text
1. 本轮 scope 与 non-goals；
2. 已读取文档和合同清单；
3. 输出文件清单；
4. train / validation ledger row counts；
5. reconciliation audit 摘要；
6. forbidden field audit 摘要；
7. validator_report.json 摘要；
8. 是否建议 reviewer 考虑 ATPAL2 工作文档。
```

## 12. 给执行者的命令

```text
请只执行 ATPAL1 Baseline Ledger Builder。

基于可信 baseline replay 和 ATPAL0 合同，生成 train + validation 的 trade、position lifecycle、position-day、symbol-date、
action context、cash/fee/tax 账本，并输出 summary/nav/fee/turnover/action_count/missing_price/negative_cash reconciliation audit。

必须复现 2025 validation baseline 指标。
不得进入 ATPAL2/3/4，不得跑新策略，不得选择规则或阈值，不得使用 strict_test，不得训练模型，
不得输出 OrderIntent/target/quantity_instruction/broker，不得触碰 provider/latest/monitor/frontend/Agent/production。

完成后写：
docs/tw_portfolio_decision_model/POLICY_ATPAL1_BASELINE_LEDGER_BUILDER_EXECUTION_REPORT_CN.md
```
