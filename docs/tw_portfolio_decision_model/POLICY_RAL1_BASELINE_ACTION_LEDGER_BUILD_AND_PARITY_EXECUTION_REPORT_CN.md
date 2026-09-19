---
created_at: 2026-06-23T01:42:21+00:00
status: executed_ral1_baseline_action_ledger_parity
phase: RAL1_BASELINE_ACTION_LEDGER_BUILD_AND_PARITY
mainline_doc: docs/tw_portfolio_decision_model/POLICY_RAL_ACTION_LEDGER_RULE_ATTRIBUTION_MAINLINE_CN.md
work_doc: docs/tw_portfolio_decision_model/POLICY_RAL1_BASELINE_ACTION_LEDGER_BUILD_AND_PARITY_WORK_CN.md
artifact_root: data_tw/experiments/rule_attribution_ledger/ral1_baseline_action_ledger_parity
strict_test_used: false
training_run: false
production_allowed: false
overall_status: stop_return_to_coordinator
---

# RAL1 Baseline Action Ledger Build And Parity 执行报告

## 1. Scope

本轮只构建 baseline action ledger 和 parity artifacts。未训练模型，未新增规则，未运行 PBA2/PBA3/PBA3-R/PBA-RC attribution，未运行收益规则实验，未运行或读取 strict_test，未输出 OrderIntent / target_weight / target_position / quantity / broker order。

## 2. Documents Read

```text
docs/tw_portfolio_decision_model/POLICY_RAL_ACTION_LEDGER_RULE_ATTRIBUTION_MAINLINE_CN.md
docs/tw_portfolio_decision_model/POLICY_RAL0_LEDGER_CONTRACT_MAPPING_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_RAL0_LEDGER_CONTRACT_MAPPING_EXECUTION_REPORT_CN.md
docs/tw_portfolio_decision_model/POLICY_MODEL_RESEARCH_ROUTE_CLOSURE_WORK_CN.md
docs/tw_portfolio_decision_model/POLICY_PBA1_BASELINE_SNAPSHOT_BUILD_AND_PARITY_REPLAY_EXECUTION_REPORT_CN.md
docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md
```

## 3. Outputs

```text
data_tw/experiments/rule_attribution_ledger/ral1_baseline_action_ledger_parity/manifest.json
data_tw/experiments/rule_attribution_ledger/ral1_baseline_action_ledger_parity/baseline_action_symbol_daily_ledger.csv
data_tw/experiments/rule_attribution_ledger/ral1_baseline_action_ledger_parity/baseline_ledger_parity_metrics.csv
data_tw/experiments/rule_attribution_ledger/ral1_baseline_action_ledger_parity/daily_nav_reconciliation.csv
data_tw/experiments/rule_attribution_ledger/ral1_baseline_action_ledger_parity/symbol_pnl_reconciliation.csv
data_tw/experiments/rule_attribution_ledger/ral1_baseline_action_ledger_parity/cost_turnover_reconciliation.csv
data_tw/experiments/rule_attribution_ledger/ral1_baseline_action_ledger_parity/field_availability_audit.csv
data_tw/experiments/rule_attribution_ledger/ral1_baseline_action_ledger_parity/feature_available_at_audit.csv
data_tw/experiments/rule_attribution_ledger/ral1_baseline_action_ledger_parity/forbidden_consumer_audit.csv
data_tw/experiments/rule_attribution_ledger/ral1_baseline_action_ledger_parity/validator_report.json
data_tw/experiments/rule_attribution_ledger/ral1_baseline_action_ledger_parity/golden_samples_report.json
```

## 4. Ledger Summary

```text
snapshot_rows = 6805
replay_daily_rows = 723
ledger_rows = 7528
action_counts = {'buy': 712, 'hold': 6162, 'sell': 654}
粒度 = date x symbol x action_source x action_type
action_source = baseline only
```

`baseline_action_symbol_daily_ledger.csv` 包含两类行：

```text
1. symbol action context rows:
   来自 PBA1 baseline_action_snapshot_artifact.csv。
   rank/score/action/holding context 为 native。
   symbol-level PnL/cost/turnover 不在当前 PBA1 artifact 中，保留为空并标记 requires_future_data_contract。

2. PORTFOLIO_DIAGNOSTIC reconciliation rows:
   来自 PBA1 baseline_parity_replay_ledger.csv。
   用于 daily NAV / net PnL / fee / sell_tax / daily ledger turnover reconciliation。
   这些行不是 symbol-level 原生 PnL，不得解释为单股贡献。
```

## 5. Reconciliation Result

`daily_nav_reconciliation.csv`：

```text
daily_nav_reconciliation_status = pass
net_pnl_reconciliation_status = pass
```

`cost_turnover_reconciliation.csv` 对 PBA1 daily replay ledger 中的 fee / sell_tax / turnover 列逐日 reconciliation：

```text
daily_fee_sell_tax_turnover_status = pass
```

但 `baseline_parity_metrics.csv` 中 split-level turnover 为非零：

```text
[
  {
    "split": "train",
    "start_date": "2023-01-03",
    "end_date": "2024-12-31",
    "daily_nav_reconciliation_status": "pass",
    "net_pnl_reconciliation_status": "pass",
    "fee_reconciliation_status": "pass",
    "sell_tax_reconciliation_status": "pass",
    "turnover_reconciliation_status": "fail_daily_replay_lacks_turnover_distribution",
    "symbol_pnl_reconstruction_status": "fail_symbol_pnl_not_native_in_current_pba1_replay",
    "pba1_replay_turnover_metric": 87.37059302,
    "ral1_turnover_sum": 0.0,
    "turnover_metric_diff": -87.37059302,
    "overall_status": "stop_return_to_coordinator"
  },
  {
    "split": "validation",
    "start_date": "2025-01-02",
    "end_date": "2025-12-31",
    "daily_nav_reconciliation_status": "pass",
    "net_pnl_reconciliation_status": "pass",
    "fee_reconciliation_status": "pass",
    "sell_tax_reconciliation_status": "pass",
    "turnover_reconciliation_status": "fail_daily_replay_lacks_turnover_distribution",
    "symbol_pnl_reconstruction_status": "fail_symbol_pnl_not_native_in_current_pba1_replay",
    "pba1_replay_turnover_metric": 42.18778217,
    "ral1_turnover_sum": 0.0,
    "turnover_metric_diff": -42.18778217,
    "overall_status": "stop_return_to_coordinator"
  }
]
```

当前 PBA1 daily replay ledger 没有足够字段把该 split-level turnover 安全分解到 date x symbol x action rows。因此 split turnover metric reconciliation 未通过。

## 6. Symbol PnL Status

symbol-level PnL 结论：

```text
availability_status = requires_future_data_contract
status = not_reconstructed
```

原因：

```text
PBA1 snapshot 提供 symbol action/holding context；
PBA1 replay ledger 提供 portfolio-level daily return/cash/cost；
但当前 artifacts 不提供 price_used、shares、notional、position market value、realized/unrealized PnL。
```

本轮没有把 portfolio-level net_return 平均、按行数、按持仓数或按 action rows 分配成 symbol PnL，也没有把缺失贡献字段默认填 0 后标为 native。

## 7. Safety Boundary

```text
training_run = false
strict_test_used = false
rule_experiment_run = false
pba_attribution_run = false
order_intent_output = false
target_weight_output = false
target_position_output = false
quantity_or_broker_output = false
provider/latest/monitor/frontend/Agent/broker/production touched = false
```

## 8. Gate Answer

逐项回答：

```text
1. RAL1 是否只构建 baseline ledger: yes
2. ledger 粒度是否为 date x symbol x action_source x action_type: yes
3. baseline ledger 是否能 reconcile 到 PBA1 replay daily NAV path: yes, via PORTFOLIO_DIAGNOSTIC rows
4. fee / sell tax / daily replay turnover 是否能 reconcile: yes against daily replay ledger columns
5. split-level turnover metric 是否能 reconcile: no
6. symbol-level PnL 是 native、derived_proxy，还是无法安全还原: requires_future_data_contract / not_reconstructed
7. 是否存在缺失字段被默认填 0: no
8. 是否没有训练、strict_test、新规则、PBA attribution: yes
9. 是否没有 OrderIntent / target_weight / target_position / quantity: yes
10. 是否允许进入 RAL2: false
```

## 9. Recommendation

```text
overall_status = stop_return_to_coordinator
```

由于当前 PBA1 artifacts 无法安全还原 symbol-level PnL，且 split-level turnover metric 无法从 daily replay ledger 分解 reconciliation，本执行者不授权进入 RAL2。应由审查者/统筹决定是否补 RAL1-R replay data contract，或回到统筹。
