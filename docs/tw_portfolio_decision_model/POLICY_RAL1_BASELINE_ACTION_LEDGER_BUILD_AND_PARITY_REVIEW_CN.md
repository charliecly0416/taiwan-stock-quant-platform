---
created_at: 2026-06-23
status: review_fail_stop_ral2_request_ral1_r_data_contract_repair
phase_reviewed: RAL1_BASELINE_ACTION_LEDGER_BUILD_AND_PARITY
mainline_doc: docs/tw_portfolio_decision_model/POLICY_RAL_ACTION_LEDGER_RULE_ATTRIBUTION_MAINLINE_CN.md
work_doc: docs/tw_portfolio_decision_model/POLICY_RAL1_BASELINE_ACTION_LEDGER_BUILD_AND_PARITY_WORK_CN.md
execution_report: docs/tw_portfolio_decision_model/POLICY_RAL1_BASELINE_ACTION_LEDGER_BUILD_AND_PARITY_EXECUTION_REPORT_CN.md
artifact_root: data_tw/experiments/rule_attribution_ledger/ral1_baseline_action_ledger_parity
verdict: FAIL_STOP_DO_NOT_ENTER_RAL2
next_work_doc: docs/tw_portfolio_decision_model/POLICY_RAL1_R_BASELINE_REPLAY_DATA_CONTRACT_REPAIR_WORK_CN.md
strict_test_authorized: false
training_authorized: false
pba_attribution_authorized: false
rule_experiment_authorized: false
production_allowed: false
readonly_only: true
simulation_only: true
not_order: true
not_target_weight: true
not_target_position: true
not_quantity: true
---

# RAL1 Baseline Action Ledger Build And Parity 审查报告

## 1. 审查结论

结论：

```text
FAIL_STOP_DO_NOT_ENTER_RAL2
```

RAL1 执行者诚实完成了 baseline ledger 尝试，并正确报告：

```text
overall_status = stop_return_to_coordinator
ral2_authorized_by_executor = false
```

审查认可该停止判断。当前 RAL1 没有达到 RAL 主线进入 RAL2 的门槛：

```text
1. symbol-level PnL 无法从当前 PBA1 artifact 安全还原。
2. split-level turnover metric 无法从 RAL1 ledger reconciliation。
3. baseline_action_symbol_daily_ledger.csv 主要提供 symbol action context，不提供可审计 symbol/action contribution。
```

因此：

```text
不得进入 RAL2 Action Attribution For Existing PBA Evidence。
```

下一步只能做一个窄范围修复：

```text
RAL1-R: Baseline Replay Data Contract Repair
```

## 2. 产物完整性

确认存在 RAL1 要求的产物：

```text
manifest.json
baseline_action_symbol_daily_ledger.csv
baseline_ledger_parity_metrics.csv
daily_nav_reconciliation.csv
symbol_pnl_reconciliation.csv
cost_turnover_reconciliation.csv
field_availability_audit.csv
feature_available_at_audit.csv
forbidden_consumer_audit.csv
validator_report.json
golden_samples_report.json
```

评价：

```text
PASS_FOR_ATTEMPT_COMPLETENESS
```

## 3. Reconciliation 审查

`daily_nav_reconciliation.csv` 显示：

```text
daily_nav_reconciliation_status = pass
net_pnl_reconciliation_status = pass
```

`cost_turnover_reconciliation.csv` 对 PBA1 daily replay ledger columns 的逐日 fee / sell_tax / turnover reconciliation 为 pass。

但 `baseline_ledger_parity_metrics.csv` 显示：

```text
train:
  turnover_reconciliation_status = fail_daily_replay_lacks_turnover_distribution
  symbol_pnl_reconstruction_status = fail_symbol_pnl_not_native_in_current_pba1_replay
  pba1_replay_turnover_metric = 87.37059302
  ral1_turnover_sum = 0.0
  overall_status = stop_return_to_coordinator

validation:
  turnover_reconciliation_status = fail_daily_replay_lacks_turnover_distribution
  symbol_pnl_reconstruction_status = fail_symbol_pnl_not_native_in_current_pba1_replay
  pba1_replay_turnover_metric = 42.18778217
  ral1_turnover_sum = 0.0
  overall_status = stop_return_to_coordinator
```

评价：

```text
FAIL_FOR_RAL1_PASS_GATE
```

说明：RAL 主线要求 RAL1 ledger 能支撑 action-level / symbol-level / daily attribution。当前只能通过 `PORTFOLIO_DIAGNOSTIC` rows 回放组合 NAV，不能证明 symbol/action contribution。

## 4. Symbol PnL 审查

`symbol_pnl_reconciliation.csv` 对各 symbol 标记：

```text
availability_status = requires_future_data_contract
status = not_reconstructed
```

`field_availability_audit.csv` 明确：

```text
price_used = requires_future_data_contract
shares_diagnostic = requires_future_data_contract
notional_diagnostic = requires_future_data_contract
realized_pnl_contribution = requires_future_data_contract
unrealized_pnl_contribution = requires_future_data_contract
```

执行者没有将 portfolio-level net_return 平均分摊到 symbol，也没有把缺失 PnL/cost/turnover 默认填 0 后冒充 native。

评价：

```text
PASS_FOR_HONEST_MISSING_FIELD_DISCLOSURE
FAIL_FOR_RAL1_SYMBOL_ATTRIBUTION_REQUIREMENT
```

## 5. Ledger 粒度与字段审查

`baseline_action_symbol_daily_ledger.csv` 包含：

```text
action_source = baseline only
action_type = buy / hold / sell
simulation_only = true
readonly_research_only = true
production_allowed = false
```

但 symbol action context rows 的 contribution 字段为空，且标记：

```text
missing_field_status = requires_future_data_contract
contribution_availability_status = symbol_action_context_native_contribution_not_available
```

评价：

```text
PASS_FOR_CONTEXT_LEDGER
FAIL_FOR_CONTRIBUTION_LEDGER
```

## 6. Validator / Golden Samples 审查

`validator_report.json` 显示：

```text
required_fields_exist = true
primary_key_no_duplicates = true
enum_fields_valid = true
forbidden_fields_absent = true
missing_numeric_contribution_fields_not_silently_filled_with_zero = true
daily_nav_reconciliation_pass = true
split_turnover_metric_reconciliation_pass = false
overall_status = stop_return_to_coordinator
```

`golden_samples_report.json` 显示正负样本覆盖并通过。

评价：

```text
PASS_FOR_VALIDATOR_DISCLOSURE
FAIL_FOR_RAL1_OVERALL_PASS
```

## 7. 安全边界审查

依据 RAL 主线与只读安全边界，抽查 `manifest.json`、`forbidden_consumer_audit.csv`、执行报告与 ledger 样例，未发现以下越权：

```text
training_run
strict_test_used
pba_attribution_run
rule_experiment_run
OrderIntent
target_weight
target_position
quantity
broker_order
provider publish
accepted latest switch
monitor write
frontend default
Agent recommendation
production
```

评价：

```text
PASS_SAFETY_BOUNDARY
```

## 8. Findings

### High

```text
RAL1 未满足进入 RAL2 的核心条件：symbol-level/action-level PnL attribution 不可用。
```

证据：

```text
symbol_pnl_reconstruction_status = fail_symbol_pnl_not_native_in_current_pba1_replay
availability_status = requires_future_data_contract
```

### High

```text
split-level turnover metric reconciliation 失败。
```

证据：

```text
train pba1_replay_turnover_metric = 87.37059302, ral1_turnover_sum = 0.0
validation pba1_replay_turnover_metric = 42.18778217, ral1_turnover_sum = 0.0
```

### Medium

```text
当前 baseline ledger 是 action context ledger + PORTFOLIO_DIAGNOSTIC reconciliation rows，不是完整 ActionSymbolDailyLedgerArtifact contribution ledger。
```

该设计对暴露缺口有价值，但不足以做 RAL2 attribution。

## 9. 审查意见

RAL1 执行报告是可信的失败报告：

```text
1. 没有伪造 symbol PnL。
2. 没有用 portfolio-level return 冒充 symbol/action contribution。
3. 没有用缺失字段填 0 冒充真实 ledger。
4. 没有越过 readonly / simulation / non-production 边界。
5. 正确拒绝自行进入 RAL2。
```

但 RAL 主线的停止条件已经触发：

```text
action attribution 需要的关键字段无法从现有 replay 还原，且不能靠伪造或外部数据补。
```

因此必须暂停 RAL2。

## 10. 下一步

本审查写出 RAL1-R 修复工作文档：

```text
docs/tw_portfolio_decision_model/POLICY_RAL1_R_BASELINE_REPLAY_DATA_CONTRACT_REPAIR_WORK_CN.md
```

RAL1-R 只允许：

```text
1. 修复 / 扩展 baseline replay data contract。
2. 尝试用现有内部价格、持仓、trade events、cost model 重建可审计 symbol/action contribution。
3. 证明 repaired baseline ledger 能 reconcile 到 PBA1 NAV、fee、sell tax、turnover。
```

RAL1-R 不允许：

```text
PBA attribution
新规则
训练
strict_test
provider/latest/monitor/frontend/Agent/broker/production
OrderIntent / target_weight / target_position / quantity
```

若 RAL1-R 仍无法还原 symbol/action-level ledger，应停止 RAL 主线并回到统筹。
