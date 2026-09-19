---
created_at: 2026-06-23
status: review_pass_ready_for_ral2_work_document
phase_reviewed: RAL1_R_BASELINE_REPLAY_DATA_CONTRACT_REPAIR
mainline_doc: docs/tw_portfolio_decision_model/POLICY_RAL_ACTION_LEDGER_RULE_ATTRIBUTION_MAINLINE_CN.md
work_doc: docs/tw_portfolio_decision_model/POLICY_RAL1_R_BASELINE_REPLAY_DATA_CONTRACT_REPAIR_WORK_CN.md
execution_report: docs/tw_portfolio_decision_model/POLICY_RAL1_R_BASELINE_REPLAY_DATA_CONTRACT_REPAIR_EXECUTION_REPORT_CN.md
artifact_root: data_tw/experiments/rule_attribution_ledger/ral1_r_baseline_replay_data_contract_repair
verdict: PASS_READY_FOR_RAL2_WORK_DOCUMENT
strict_test_authorized: false
training_authorized: false
pba_attribution_authorized_by_this_review: false
rule_experiment_authorized: false
production_allowed: false
readonly_only: true
simulation_only: true
not_order: true
not_target_weight: true
not_target_position: true
not_quantity: true
---

# RAL1-R Baseline Replay Data Contract Repair 审查报告

## 1. 审查结论

结论：

```text
PASS_READY_FOR_RAL2_WORK_DOCUMENT
```

RAL1-R 已修复 RAL1 暴露的 baseline replay data contract 缺口：

```text
1. repaired ledger 已包含 baseline price / shares / notional / fee / tax / turnover / PnL contribution。
2. train / validation 的 daily NAV、net PnL、fee、sell tax、turnover、symbol PnL reconstruction 均通过。
3. 修复使用现有内部 replay engine 与内部 price store，没有新外部数据、provider 切换或 strict_test。
4. diagnostic shares/notional 没有映射为 OrderIntent / quantity / target_weight / target_position。
```

本审查允许审查者后续另行撰写 RAL2 工作文档，但本审查本身不直接授权执行 RAL2。

## 2. 产物完整性

确认存在：

```text
manifest.json
source_data_feasibility_audit.csv
repaired_baseline_replay_data_contract.json
repaired_baseline_action_symbol_daily_ledger.csv
repaired_daily_nav_reconciliation.csv
repaired_cost_turnover_reconciliation.csv
repaired_symbol_pnl_reconciliation.csv
repaired_baseline_ledger_parity_metrics.csv
price_source_audit.csv
position_lifecycle_audit.csv
trade_event_reconstruction_audit.csv
field_availability_audit.csv
feature_available_at_audit.csv
forbidden_consumer_audit.csv
validator_report.json
golden_samples_report.json
```

评价：

```text
PASS
```

## 3. Data Contract Repair 审查

`source_data_feasibility_audit.csv` 显示本轮使用：

```text
PBA1 baseline_action_snapshot_artifact.csv
PBA1 internal replay engine actions/snapshots/nav
Existing internal OHLCV adjusted price store
Existing fee and sell tax constants
```

关键字段可用性：

```text
can_support_symbol_pnl = true
can_support_trade_notional = true
can_support_turnover = true
can_support_fee_tax = true
external_data_used = false
strict_test_used = false
pit_safe = true
```

评价：

```text
PASS
```

## 4. Repaired Ledger 审查

`repaired_baseline_action_symbol_daily_ledger.csv` 已从 RAL1 的 context ledger 升级为 contribution ledger，包含：

```text
price_used
price_source
shares_diagnostic
notional_diagnostic
trade_notional_diagnostic
position_value_before_diagnostic
position_value_after_diagnostic
turnover_contribution
fee_contribution
sell_tax_contribution
gross_pnl_contribution
realized_pnl_contribution
unrealized_pnl_contribution
net_pnl_after_fee_tax_contribution
nav_contribution
availability_status_by_field
```

ledger 粒度保持：

```text
date x symbol x action_source x action_type
```

并且：

```text
action_source = baseline
simulation_only = true
readonly_research_only = true
production_allowed = false
```

评价：

```text
PASS
```

注意：symbol/action PnL 是 `derived_proxy_internal_replay`，不是 broker-native execution record。RAL2 必须继续沿用该语义，不得把它解释为真实成交或生产订单证据。

## 5. Reconciliation 审查

`repaired_baseline_ledger_parity_metrics.csv` 显示：

```text
train:
  daily_nav_reconciliation_status = pass
  net_pnl_reconciliation_status = pass
  fee_reconciliation_status = pass
  sell_tax_reconciliation_status = pass
  turnover_reconciliation_status = pass
  symbol_pnl_reconstruction_status = pass
  overall_status = pass

validation:
  daily_nav_reconciliation_status = pass
  net_pnl_reconciliation_status = pass
  fee_reconciliation_status = pass
  sell_tax_reconciliation_status = pass
  turnover_reconciliation_status = pass
  symbol_pnl_reconstruction_status = pass
  overall_status = pass
```

`repaired_cost_turnover_reconciliation.csv` 修复了 RAL1 的 blocker：

```text
train:
  pba1_turnover = 87.37059302
  repaired_turnover_sum = 87.37059302
  turnover_diff = -0.0

validation:
  pba1_turnover = 42.18778217
  repaired_turnover_sum = 42.18778217
  turnover_diff = 0.0
```

`repaired_daily_nav_reconciliation.csv` 覆盖到：

```text
2023-01-03..2025-12-31
```

尾部 validation 日期仍为 2025-12-31，没有发现 2026 strict-test 日期混入。

评价：

```text
PASS
```

## 6. Field Availability 审查

`field_availability_audit.csv` 明确：

```text
price_used = derived_proxy_internal_replay
shares_diagnostic = derived_proxy_internal_replay
notional_diagnostic = derived_proxy_internal_replay
trade_notional_diagnostic = derived_proxy_internal_replay
fee_contribution = native_internal_replay
sell_tax_contribution = native_internal_replay
turnover_contribution = derived_proxy_internal_replay
net_pnl_after_fee_tax_contribution = derived_proxy_internal_replay
```

未发现缺失 numeric contribution 字段被静默填 0 并标为 native。

评价：

```text
PASS
```

## 7. Validator / Golden Samples 审查

`validator_report.json` 显示：

```text
required_fields_exist = true
primary_key_no_duplicates = true
enum_fields_valid = true
safety_constants_pass = true
forbidden_fields_absent = true
strict_test_used = false
training_run = false
no_pba_attribution = true
no_rule_experiment = true
field_level_availability_exists = true
price_source_pit_safe = true
shares_notional_diagnostic_only = true
daily_nav_reconciliation_pass = true
fee_sell_tax_turnover_reconciliation_pass = true
symbol_pnl_reconstruction_pass = true
overall_status = pass
```

`golden_samples_report.json` 覆盖：

```text
positive_repaired_baseline_buy_with_trade_notional
positive_repaired_baseline_sell_with_fee_tax
positive_repaired_baseline_hold_with_unrealized_pnl
negative_forbidden_quantity_field
negative_target_weight_field
negative_future_price_source
negative_missing_pnl_filled_zero_as_native
negative_portfolio_return_allocated_to_symbol_as_native
negative_strict_test_source
negative_pba_attribution_row
```

评价：

```text
PASS
```

## 8. Safety Boundary 审查

依据 `tw-stock-safety-boundary-review`，抽查 manifest、forbidden audit、执行报告、data contract、ledger 样例，未发现可消费越权字段或链路：

```text
OrderIntent
target_weight
target_position
quantity
order_size
broker_order
quick_trade
provider publish
accepted latest switch
monitor write
frontend default switch
Agent recommendation
production order
```

`forbidden_consumer_audit.csv` 中相关词只作为禁止项标签出现，不是 ledger 字段或可执行 consumer。

评价：

```text
PASS_SAFETY_BOUNDARY
```

## 9. Findings

### Critical

```text
None
```

### High

```text
None
```

### Medium

```text
symbol/action contribution 仍是 derived_proxy_internal_replay，不是 native broker execution evidence。
```

影响：

```text
这不阻止 RAL2 attribution，但 RAL2 必须继续把所有 attribution 结论限定为 readonly research replay，不得写成真实交易、生产订单或投资建议。
```

### Low

```text
RAL2 前应复用 RAL1-R repaired ledger 作为 baseline contribution anchor，而不是回退到 RAL1 context ledger。
```

## 10. 审查意见

RAL1-R 通过。它解决了 RAL1 的两个核心 blocker：

```text
1. split-level turnover metric reconciliation 失败。
2. symbol-level PnL 不可还原。
```

可以进入下一步工作文档设计：

```text
RAL2: Action Attribution For Existing PBA Evidence
```

但 RAL2 仍不得：

```text
1. 新增规则或调参。
2. 训练模型。
3. 运行 strict_test。
4. 做 provider/latest/monitor/frontend/Agent/broker/production 扩权。
5. 输出 OrderIntent / target_weight / target_position / quantity。
6. 把 no_extra_action / baseline clone 解释成 active edge。
```
