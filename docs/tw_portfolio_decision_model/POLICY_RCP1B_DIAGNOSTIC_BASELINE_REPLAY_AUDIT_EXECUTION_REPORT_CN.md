---
created_at: 2026-06-24T04:22:47+00:00
status: rcp1b_execution_report
phase: RCP1B_DIAGNOSTIC_BASELINE_REPLAY_AUDIT
work_doc: docs/tw_portfolio_decision_model/POLICY_RCP1B_DIAGNOSTIC_BASELINE_REPLAY_AUDIT_WORK_CN.md
artifact_root: data_tw/experiments/risk_control_policy_2022/rcp1b_diagnostic_baseline_replay_audit
recommended_next_step: PASS_READY_FOR_RCP2_RISK_CONTROL_RULE_DESIGN_CONTRACT_WORK_DOC
risk_control_replay_performed: false
model_training_performed: false
strict_test_performed: false
production_or_provider_change_performed: false
---

# RCP1B 2022 Diagnostic Baseline Replay Audit 执行报告

## 1. Scope

本轮只执行 RCP1B diagnostic baseline replay audit。目标是基于 RCP1A adapter 在 2022 下跌年诊断窗口建立 baseline 对照。

已确认非目标：

```text
不做 risk-control policy
不做规则设计或阈值选择
不做 2022 threshold mining
不训练模型
不做 strict_test
不修改 registry/default/provider/frontend/Agent/订单链路
不输出 OrderIntent / target_weight / target_position / quantity_instruction
```

## 2. Documents / Contracts Read

```text
docs/tw_portfolio_decision_model/POLICY_RCP_RISK_CONTROL_POLICY_2022_DOWNTURN_MAINLINE_CN.md
docs/tw_portfolio_decision_model/POLICY_RCP1A_DIAGNOSTIC_SIGNAL_ADAPTER_CONTRACT_WORK_CN.md
docs/tw_portfolio_decision_model/POLICY_RCP1A_DIAGNOSTIC_SIGNAL_ADAPTER_CONTRACT_EXECUTION_REPORT_CN.md
docs/tw_portfolio_decision_model/POLICY_RCP1A_DIAGNOSTIC_SIGNAL_ADAPTER_CONTRACT_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_RCP1B_DIAGNOSTIC_BASELINE_REPLAY_AUDIT_WORK_CN.md
docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md
docs/tw_modular_contracts/STRATEGY_RULE_CONTRACT_CN.md
docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md
docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md
```

## 3. Replay Implementation

本轮复用既有 readonly replay accounting engine：

```text
scripts/run_tw_policy_action_model_pa1.py::replay_window
```

输入不是 PA1 默认信号，而是 RCP1A adapter：

```text
data_tw/experiments/risk_control_policy_2022/rcp1a_diagnostic_signal_adapter_contract/diagnostic_model_signal.csv
```

字段映射：

```text
candidate_rank = rank
buy_score = score
raw_score = raw_score
score_rank = rank
full_qlib_rank = rank
signal_asof = signal_date
available_at = signal_date
```

执行价口径：`next_open`；缺失 next_open 时 skip/audit，不 fallback。

## 4. Evidence Produced

输出目录：

```text
data_tw/experiments/risk_control_policy_2022/rcp1b_diagnostic_baseline_replay_audit
```

已生成：

```text
manifest.json
baseline_replay_source_manifest.json
baseline_summary.csv
baseline_nav.csv
baseline_actions.csv
baseline_position_snapshots.csv
coverage_audit.csv
price_alignment_audit.csv
execution_audit.csv
fee_tax_turnover_audit.csv
risk_metric_summary.csv
cash_no_trade_audit.csv
diagnostic_semantics_audit.json
forbidden_consumer_audit.csv
validator_report.json
diagnostic_findings.md
```

## 5. Baseline Summary

```json
{
  "window": "2022_downturn_validation_diagnostic",
  "model_name": "policy_supervised_utility_v1",
  "model_family": "qlib_lightgbm_alpha158",
  "strategy_rule": "top50_exit_one_worst_sell",
  "start_date": "2022-01-03",
  "end_date": "2022-12-30",
  "initial_cash": 1000000.0,
  "final_equity": 663907.8,
  "total_return": -0.3360922,
  "net_return_after_fee_tax": -0.3360922,
  "gross_return": -0.22316603,
  "max_drawdown": -0.42634734,
  "action_count": 478,
  "buy_count": 244,
  "sell_count": 234,
  "skip_count": 1,
  "skipped_action_count": 1,
  "turnover_proxy": 48.45575343,
  "fee_and_tax": 112926.17,
  "max_holding_count": 10,
  "duplicate_position_count": 0,
  "negative_cash_count": 0,
  "missing_price_count": 0,
  "diagnostic_only": true,
  "model_id": "rcp_qllib_20150504_20201231_wf_val_2021_2022_diagnostic",
  "strict_oos": false,
  "semantic_label": "downturn_validation_diagnostic_only"
}
```

## 6. Risk Metrics

```json
{
  "net_return_after_fee_tax": -0.3360922,
  "gross_return": -0.22316603,
  "max_drawdown": -0.42634734,
  "drawdown_duration": 223,
  "worst_month_return": -0.170488,
  "monthly_win_rate": 0.25,
  "downside_volatility": 0.01432064,
  "calmar_like_ratio": -0.78830608,
  "average_cash_rate": 0.14025927,
  "max_cash_rate": 1.0,
  "participation_rate": 0.99593496,
  "average_holding_count": 8.43089431,
  "max_holding_count": 10,
  "action_count": 478,
  "buy_count": 244,
  "sell_count": 234,
  "turnover_proxy": 48.45575343,
  "fee_and_tax": 112926.17
}
```

## 7. Validator Result

```json
{
  "phase": "RCP1B_DIAGNOSTIC_BASELINE_REPLAY_AUDIT",
  "status": "PASS",
  "pass": true,
  "rcp1a_validator_pass": true,
  "input_signal_exists": true,
  "baseline_replay_completed": true,
  "summary_status": "PASS",
  "coverage_status": "PASS",
  "price_alignment_status": "PASS",
  "execution_status": "PASS",
  "fee_tax_turnover_status": "PASS",
  "cash_no_trade_status": "PASS",
  "diagnostic_semantics_status": "PASS",
  "forbidden_actions_status": "PASS",
  "risk_control_replay_performed": false,
  "strict_test_performed": false,
  "model_training_performed": false,
  "rcp2_authorizable": true,
  "recommended_next_step": "PASS_READY_FOR_RCP2_RISK_CONTROL_RULE_DESIGN_CONTRACT_WORK_DOC",
  "baseline_net_return_after_fee_tax": -0.3360922,
  "baseline_max_drawdown": -0.42634734,
  "baseline_action_count": 478,
  "baseline_fee_and_tax": 112926.17
}
```

## 8. Forbidden Actions Audit

本轮未执行：

```text
risk-control replay
model training
strict_test
registry/default 修改
provider publish
accepted latest switch
monitor/frontend/Agent integration
broker/order/quick-trade
OrderIntent 输出
target_weight / target_position / quantity_instruction 输出
```

## 9. Issues / Blockers / Deviations

无阻塞。

说明：`baseline_actions.csv` 是 replay 事实账本，包含 execution_date、execution_price、quantity、fee/tax 等回放结果字段；它不是 OrderIntentArtifact，也不是下单指令。

## 10. Recommendation For Reviewer

```text
PASS_READY_FOR_RCP2_RISK_CONTROL_RULE_DESIGN_CONTRACT_WORK_DOC
```

若审查通过，只授权进入 RCP2 risk-control rule design contract，不授权直接运行 risk-control replay。
