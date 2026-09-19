---
created_at: 2026-06-23T02:08:44+00:00
status: executed_ral1_r_baseline_replay_data_contract_repair
phase: RAL1_R_BASELINE_REPLAY_DATA_CONTRACT_REPAIR
artifact_root: data_tw/experiments/rule_attribution_ledger/ral1_r_baseline_replay_data_contract_repair
strict_test_used: false
training_run: false
production_allowed: false
overall_status: pass
---

# RAL1-R Baseline Replay Data Contract Repair 执行报告

## 1. Scope

本轮仍只处理 baseline replay data contract repair。未进入 RAL2，未做 PBA2/PBA3/PBA-RC attribution，未新增规则或调参，未训练模型，未运行或读取 strict_test，未抓取外部数据，未切换 provider，未输出 OrderIntent / target_weight / target_position / quantity / broker order。

## 2. Documents Read

```text
docs/tw_portfolio_decision_model/POLICY_RAL_ACTION_LEDGER_RULE_ATTRIBUTION_MAINLINE_CN.md
docs/tw_portfolio_decision_model/POLICY_RAL1_BASELINE_ACTION_LEDGER_BUILD_AND_PARITY_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_RAL1_BASELINE_ACTION_LEDGER_BUILD_AND_PARITY_EXECUTION_REPORT_CN.md
docs/tw_portfolio_decision_model/POLICY_RAL1_BASELINE_ACTION_LEDGER_BUILD_AND_PARITY_WORK_CN.md
docs/tw_portfolio_decision_model/POLICY_RAL0_LEDGER_CONTRACT_MAPPING_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_PBA1_BASELINE_SNAPSHOT_BUILD_AND_PARITY_REPLAY_EXECUTION_REPORT_CN.md
docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md
```

## 3. Repair Method

RAL1 的缺口来自 PBA1 产物未落盘 action-level replay state。本轮没有改 provider 或抓新数据，而是复用现有内部 baseline replay engine：

```text
scripts/run_tw_policy_action_model_pa1.py::replay_window
existing internal PriceStore = qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/normalized_nonempty
fee_rate = 0.001425
sell_tax_rate = 0.003
windows = 2023-01-01..2025-12-31 only
```

重建并落盘：

```text
repaired_baseline_action_symbol_daily_ledger.csv
price_source_audit.csv
position_lifecycle_audit.csv
trade_event_reconstruction_audit.csv
```

## 4. Outputs

```text
data_tw/experiments/rule_attribution_ledger/ral1_r_baseline_replay_data_contract_repair/manifest.json
data_tw/experiments/rule_attribution_ledger/ral1_r_baseline_replay_data_contract_repair/source_data_feasibility_audit.csv
data_tw/experiments/rule_attribution_ledger/ral1_r_baseline_replay_data_contract_repair/repaired_baseline_replay_data_contract.json
data_tw/experiments/rule_attribution_ledger/ral1_r_baseline_replay_data_contract_repair/repaired_baseline_action_symbol_daily_ledger.csv
data_tw/experiments/rule_attribution_ledger/ral1_r_baseline_replay_data_contract_repair/repaired_daily_nav_reconciliation.csv
data_tw/experiments/rule_attribution_ledger/ral1_r_baseline_replay_data_contract_repair/repaired_cost_turnover_reconciliation.csv
data_tw/experiments/rule_attribution_ledger/ral1_r_baseline_replay_data_contract_repair/repaired_symbol_pnl_reconciliation.csv
data_tw/experiments/rule_attribution_ledger/ral1_r_baseline_replay_data_contract_repair/repaired_baseline_ledger_parity_metrics.csv
data_tw/experiments/rule_attribution_ledger/ral1_r_baseline_replay_data_contract_repair/price_source_audit.csv
data_tw/experiments/rule_attribution_ledger/ral1_r_baseline_replay_data_contract_repair/position_lifecycle_audit.csv
data_tw/experiments/rule_attribution_ledger/ral1_r_baseline_replay_data_contract_repair/trade_event_reconstruction_audit.csv
data_tw/experiments/rule_attribution_ledger/ral1_r_baseline_replay_data_contract_repair/field_availability_audit.csv
data_tw/experiments/rule_attribution_ledger/ral1_r_baseline_replay_data_contract_repair/feature_available_at_audit.csv
data_tw/experiments/rule_attribution_ledger/ral1_r_baseline_replay_data_contract_repair/forbidden_consumer_audit.csv
data_tw/experiments/rule_attribution_ledger/ral1_r_baseline_replay_data_contract_repair/validator_report.json
data_tw/experiments/rule_attribution_ledger/ral1_r_baseline_replay_data_contract_repair/golden_samples_report.json
```

## 5. Reconciliation

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
    "turnover_reconciliation_status": "pass",
    "symbol_pnl_reconstruction_status": "pass",
    "overall_status": "pass"
  },
  {
    "split": "validation",
    "start_date": "2025-01-02",
    "end_date": "2025-12-31",
    "daily_nav_reconciliation_status": "pass",
    "net_pnl_reconciliation_status": "pass",
    "fee_reconciliation_status": "pass",
    "sell_tax_reconciliation_status": "pass",
    "turnover_reconciliation_status": "pass",
    "symbol_pnl_reconstruction_status": "pass",
    "overall_status": "pass"
  }
]
```

## 6. Gate Answers

```text
1. RAL1-R 是否仍只处理 baseline: yes
2. 是否找到了足以重建 symbol/action contribution 的内部数据: yes, internal replay actions/snapshots/nav + internal price store
3. 是否使用了新外部数据、strict_test 或 provider 切换: no
4. price_used 来源: trades use existing internal next_open after signal_date; holds use close_on_or_before mark
5. shares/notional/trade_notional 来源: existing internal replay action and position snapshots; diagnostic only
6. fee/sell_tax/turnover 是否能 reconcile 到 PBA1: yes
7. symbol-level PnL 状态: derived_proxy_internal_replay, reconciled to replay NAV
8. repaired ledger 是否支持 date x symbol x action attribution: yes for baseline
9. 是否没有训练、规则实验、PBA attribution: yes
10. 是否没有 OrderIntent / target_weight / target_position / quantity: yes
11. 是否允许审查者考虑 RAL2: true
```

## 7. Recommendation

```text
overall_status = pass
ral2_authorized_by_executor = false
```

执行者不自行授权 RAL2；如审查通过，应由审查者另行撰写 RAL2 工作文档。
