---
created_at: 2026-06-23
status: work_order_for_atpal4_fpa4_backfill_diagnostic
phase: ATPAL4_FPA4_BACKFILL_DIAGNOSTIC
mainline_doc: docs/tw_portfolio_decision_model/POLICY_ATPAL_ACTION_TRADE_PNL_ATTRIBUTION_LEDGER_MAINLINE_CN.md
prior_review: docs/tw_portfolio_decision_model/POLICY_ATPAL3_CANDIDATE_REPLAY_ADAPTER_CONTRACT_REVIEW_CN.md
prior_execution_report: docs/tw_portfolio_decision_model/POLICY_ATPAL3_CANDIDATE_REPLAY_ADAPTER_CONTRACT_EXECUTION_REPORT_CN.md
source_atpal1_root: data_tw/experiments/action_trade_pnl_attribution_ledger/atpal1_r_action_context_ledger_repair
source_atpal2_root: data_tw/experiments/action_trade_pnl_attribution_ledger/atpal2_contribution_audit
source_atpal3_root: data_tw/experiments/action_trade_pnl_attribution_ledger/atpal3_candidate_adapter_contract
source_fpa4_root: data_tw/experiments/full_path_action_diagnostic/fpa4_predeclared_full_path_rule_sanity
output_root: data_tw/experiments/action_trade_pnl_attribution_ledger/atpal4_fpa4_backfill_diagnostic
execution_report: docs/tw_portfolio_decision_model/POLICY_ATPAL4_FPA4_BACKFILL_DIAGNOSTIC_EXECUTION_REPORT_CN.md
atpal4_authorized: true
fpa4_repair_authorized: false
candidate_replay_authorized: false
new_strategy_replay_authorized: false
rule_selection_authorized: false
threshold_selection_authorized: false
strict_test_authorized: false
model_training_authorized: false
production_allowed: false
readonly_only: true
simulation_only: true
---

# ATPAL4 FPA4 Backfill Diagnostic 工作文档

## 1. 本轮定位

本轮只执行：

```text
ATPAL4: FPA4 Backfill Diagnostic
```

目标是对既有 FPA4 失败候选做 PnL attribution backfill，解释其收益/亏损来自哪些 symbol/date/trade，并补齐当时 FPA4 缺少的 concentration attribution 诊断。

本轮不是 FPA4 repair，不允许改变 FPA4 结论：

```text
STOP_NO_PREDECLARED_RULE_SANITY_PASS
```

本轮不得新增候选、不得调阈值、不得运行新的策略搜索、不得使用 strict_test、不得训练模型、不得触碰生产链路。

## 2. 必须读取

执行者必须读取：

```text
docs/tw_portfolio_decision_model/POLICY_ATPAL_ACTION_TRADE_PNL_ATTRIBUTION_LEDGER_MAINLINE_CN.md
docs/tw_portfolio_decision_model/POLICY_ATPAL3_CANDIDATE_REPLAY_ADAPTER_CONTRACT_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_ATPAL3_CANDIDATE_REPLAY_ADAPTER_CONTRACT_EXECUTION_REPORT_CN.md
docs/tw_portfolio_decision_model/POLICY_RAL_FPA4_PREDECLARED_FULL_PATH_RULE_SANITY_EXECUTION_REPORT_CN.md
docs/tw_portfolio_decision_model/POLICY_RAL_FPA4_PREDECLARED_FULL_PATH_RULE_SANITY_REVIEW_CN.md
data_tw/experiments/action_trade_pnl_attribution_ledger/atpal1_r_action_context_ledger_repair/manifest.json
data_tw/experiments/action_trade_pnl_attribution_ledger/atpal1_r_action_context_ledger_repair/trade_level_pnl_ledger.csv
data_tw/experiments/action_trade_pnl_attribution_ledger/atpal1_r_action_context_ledger_repair/symbol_date_pnl_ledger.csv
data_tw/experiments/action_trade_pnl_attribution_ledger/atpal1_r_action_context_ledger_repair/position_lifecycle_ledger.csv
data_tw/experiments/action_trade_pnl_attribution_ledger/atpal2_contribution_audit/top_contributor_audit.csv
data_tw/experiments/action_trade_pnl_attribution_ledger/atpal2_contribution_audit/baseline_concentration_gate_design.md
data_tw/experiments/action_trade_pnl_attribution_ledger/atpal3_candidate_adapter_contract/candidate_concentration_gate_contract.csv
data_tw/experiments/action_trade_pnl_attribution_ledger/atpal3_candidate_adapter_contract/candidate_vs_baseline_delta_contract.csv
data_tw/experiments/full_path_action_diagnostic/fpa4_predeclared_full_path_rule_sanity/manifest.json
data_tw/experiments/full_path_action_diagnostic/fpa4_predeclared_full_path_rule_sanity/predeclared_candidate_manifest.csv
data_tw/experiments/full_path_action_diagnostic/fpa4_predeclared_full_path_rule_sanity/full_path_rule_sanity_replay_summary.csv
data_tw/experiments/full_path_action_diagnostic/fpa4_predeclared_full_path_rule_sanity/candidate_pass_audit.csv
data_tw/experiments/full_path_action_diagnostic/fpa4_predeclared_full_path_rule_sanity/rolling_oos_excess_audit.csv
data_tw/experiments/full_path_action_diagnostic/fpa4_predeclared_full_path_rule_sanity/symbol_date_concentration_audit.csv
data_tw/experiments/full_path_action_diagnostic/fpa4_predeclared_full_path_rule_sanity/forbidden_consumer_audit.csv
data_tw/experiments/full_path_action_diagnostic/fpa4_predeclared_full_path_rule_sanity/validator_report.json
```

## 3. 输入与输出

参考输入：

```text
source_atpal1_root =
data_tw/experiments/action_trade_pnl_attribution_ledger/atpal1_r_action_context_ledger_repair/

source_atpal2_root =
data_tw/experiments/action_trade_pnl_attribution_ledger/atpal2_contribution_audit/

source_atpal3_root =
data_tw/experiments/action_trade_pnl_attribution_ledger/atpal3_candidate_adapter_contract/

source_fpa4_root =
data_tw/experiments/full_path_action_diagnostic/fpa4_predeclared_full_path_rule_sanity/
```

输出目录：

```text
data_tw/experiments/action_trade_pnl_attribution_ledger/atpal4_fpa4_backfill_diagnostic/
```

执行报告：

```text
docs/tw_portfolio_decision_model/POLICY_ATPAL4_FPA4_BACKFILL_DIAGNOSTIC_EXECUTION_REPORT_CN.md
```

## 4. 必须输出

必须输出主线指定的 ATPAL4 产物，并补充 validator / manifest / forbidden audit：

```text
manifest.json
fpa4_candidate_trade_pnl_attribution.csv
fpa4_candidate_symbol_date_concentration.csv
fpa4_candidate_delta_component_breakdown.csv
fpa4_failure_attribution_report.md
forbidden_consumer_audit.csv
validator_report.json
```

不得输出新的 candidate replay ledger、candidate pass result、策略通过结论或交易指令。

## 5. Backfill 口径

### 5.1 FPA4 candidate 范围

只允许覆盖既有 FPA4 candidate / threshold_version：

```text
FPA4_C01 / rank_lte_25
FPA4_C01 / rank_lte_50
FPA4_C02 / unrealized_gain_large
FPA4_C03 / unrealized_loss_large
FPA4_C04 / unrealized_gain_large
FPA4_C05 / holding_days_005_019
FPA4_C05 / holding_days_020_059
```

必须从 FPA4 `candidate_pass_audit.csv` 或 `predeclared_candidate_manifest.csv` 读取，不得手工新增。

### 5.2 fpa4_candidate_trade_pnl_attribution.csv

至少包含：

```text
candidate_id
threshold_version
split
action_space
trade_count
buy_count
sell_count
fee_and_tax
turnover_proxy
net_return_after_fee_tax
excess_net_return_after_fee_tax_vs_baseline
baseline_trade_count
baseline_fee_and_tax
baseline_turnover_proxy
baseline_net_return_after_fee_tax
delta_trade_count
delta_fee_and_tax
delta_turnover_proxy
delta_net_return_after_fee_tax
top_abs_trade_share_baseline_reference
diagnostic_only
not_rule_feature
fpa4_candidate_pass_original
fpa4_conclusion_unchanged
```

说明：如果当前没有 FPA4 candidate trade-level ledger，不得伪造 per-trade 明细。可以输出 summary-level trade attribution backfill，并在报告中说明 limitation。

### 5.3 fpa4_candidate_symbol_date_concentration.csv

至少包含：

```text
candidate_id
threshold_version
split
action_space
source_concentration_status
source_symbol_date_concentration_status
baseline_top1_symbol_contribution_share
baseline_top3_symbol_contribution_share
baseline_top1_date_contribution_share
baseline_top5_date_contribution_share
baseline_top1_symbol_date_contribution_share
baseline_top10_symbol_date_contribution_share
baseline_contribution_hhi
candidate_symbol_date_available
candidate_symbol_date_backfill_status
concentration_gap_reason
diagnostic_only
not_rule_feature
fpa4_conclusion_unchanged
```

若 FPA4 candidate 缺少 symbol-date ledger，必须显式标记：

```text
candidate_symbol_date_available = false
candidate_symbol_date_backfill_status = unavailable_requires_candidate_atpal_replay
```

不得把 baseline concentration 指标冒充为 candidate concentration 指标。

### 5.4 fpa4_candidate_delta_component_breakdown.csv

至少包含：

```text
candidate_id
threshold_version
split
action_space
component
candidate_value
baseline_value
delta_value
direction
diagnostic_interpretation
diagnostic_only
not_rule_feature
fpa4_candidate_pass_original
fpa4_conclusion_unchanged
```

component 至少覆盖：

```text
net_return_after_fee_tax
net_return_if_liquidated_at_period_end
fee_and_tax
turnover_proxy
action_count
buy_count
sell_count
skip_count
max_drawdown
average_cash_rate
missing_price_count
negative_cash_count
rolling_oos_mean_excess
rolling_oos_median_excess
```

## 6. fpa4_failure_attribution_report.md 要求

必须说明：

```text
1. ATPAL4 是 backfill diagnostic，不是 FPA4 repair；
2. FPA4 原始结论 STOP_NO_PREDECLARED_RULE_SANITY_PASS 不变；
3. 哪些 candidate 2025 validation excess 为正但仍未通过 rolling/concentration gate；
4. 哪些 candidate validation excess 为负；
5. FPA4 当时 symbol-date concentration 缺失的原因；
6. 当前 backfill 是否只能做到 summary-level attribution；
7. 若要得到真正 candidate symbol-date/trade attribution，需要未来另行授权 candidate ATPAL replay，但本轮不得执行；
8. 不得据此选择规则、调阈值、strict_test 或生产切换。
```

## 7. Validator 要求

`validator_report.json` 至少检查：

```text
all_required_files_exist
mainline_read
atpal3_review_read
source_atpal1_validator_ok
source_atpal2_validator_ok
source_atpal3_validator_ok
source_fpa4_validator_ok
source_fpa4_conclusion_is_stop_no_pass
all_fpa4_candidates_covered
no_new_candidate_added
candidate_pass_original_all_false
fpa4_conclusion_unchanged_true
trade_pnl_attribution_completed
symbol_date_concentration_completed
delta_component_breakdown_completed
failure_attribution_report_completed
candidate_symbol_date_not_fabricated
no_candidate_replay_run
no_new_strategy_replay_run
rule_selection_run_false
threshold_selection_run_false
strict_test_used_false
model_training_run_false
production_allowed_false
no_order_target_quantity_broker_output
```

允许的 final recommendation：

```text
READY_FOR_REVIEWER_TO_CLOSE_ATPAL_MAINLINE
FAIL_NEEDS_ATPAL4_REPAIR
STOP_SOURCE_FPA4_INVALID
STOP_BACKFILL_WOULD_REQUIRE_CANDIDATE_REPLAY
STOP_FORBIDDEN_CONSUMER_USED
```

## 8. 禁止事项

本轮禁止：

```text
改变 FPA4 失败结论
把 ATPAL4 写成 FPA4 repair
新增 candidate
调整 threshold
运行 candidate replay
运行新策略 replay
生成 candidate pass/fail 新结论
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
请只执行 ATPAL4 FPA4 Backfill Diagnostic。

基于既有 FPA4 失败候选结果、ATPAL1-R baseline ledger、ATPAL2 concentration audit 和 ATPAL3 adapter contract，
输出 FPA4 candidate 的 summary-level trade PnL attribution、symbol-date concentration gap diagnosis、
delta component breakdown 和 failure attribution report。

不得新增候选，不得调阈值，不得运行 candidate replay 或新策略 replay，不得改变 FPA4 的
STOP_NO_PREDECLARED_RULE_SANITY_PASS 结论，不得 strict_test，不得训练模型，不得输出 OrderIntent/target/quantity_instruction/broker，
不得触碰生产链路。
```
