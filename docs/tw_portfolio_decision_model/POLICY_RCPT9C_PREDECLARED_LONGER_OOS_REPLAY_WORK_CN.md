---
created_at: 2026-06-25
status: work_doc
phase: RCPT9C_PREDECLARED_LONGER_OOS_REPLAY
parent_mainline: docs/tw_portfolio_decision_model/POLICY_RCPT9_LONGER_STRICT_OOS_RETRAIN_HOLDOUT_MAINLINE_CN.md
parent_lineage_package: data_tw/experiments/risk_control_policy_2022/rcpt9b_lineage_build/
production_allowed: false
order_or_target_output_allowed: false
model_training_authorized: false
threshold_tuning_authorized: false
---

# RCPT9C Predeclared Longer OOS Replay 工作文档

## 1. 目标

只在 RCPT9A/RCPT9B 冻结的 holdout 上 replay 已接受的 M1/M2 research candidates。

冻结窗口：

```text
holdout: 2025-07-01..2026-05-07
```

允许 mappings：

```text
M1_QLIB_SCORE_COMPONENT_PRIMARY
M2_LTR_SCORE_COMPONENT_SECONDARY
```

禁止：

```text
M3
新 mapping
阈值调参
根据 replay 结果改规则
新训练 qlib/LTR
生产化
订单/target/quantity/broker 输出
```

## 2. 输入

必须读取：

```text
docs/tw_portfolio_decision_model/POLICY_RCPT9_LONGER_STRICT_OOS_RETRAIN_HOLDOUT_MAINLINE_CN.md
docs/tw_portfolio_decision_model/POLICY_RCPT9B_LINEAGE_BUILD_EXECUTION_REPORT_CN.md
docs/tw_portfolio_decision_model/POLICY_RCPT9B_REPAIR_COVERAGE_GATE_EXECUTION_REPORT_CN.md
data_tw/experiments/risk_control_policy_2022/rcpt9b_lineage_build/
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2c_fresh_ltr_sample_training/phase_s2c_ltr_score_rank.csv
```

## 3. 输出目录

```text
data_tw/experiments/risk_control_policy_2022/rcpt9c_predeclared_longer_oos_replay/
```

必须生成：

```text
manifest.json
window_metric_summary.csv
candidate_vs_qlib_ltr_adaptive_baseline.csv
gate_decision_by_window.csv
gate_decision_by_mapping.csv
daily_nav.csv
actions.csv
trigger_attribution.csv
cash_exposure_audit.csv
fee_turnover_audit.csv
concentration_audit.csv
lineage_replay_audit.json
forbidden_action_audit.csv
validator_report.json
diagnostic_findings.md
```

执行报告：

```text
docs/tw_portfolio_decision_model/POLICY_RCPT9C_PREDECLARED_LONGER_OOS_REPLAY_EXECUTION_REPORT_CN.md
```

## 4. Gate

RCPT9C 继承 RCPT9 主线 gate：

```text
return_capture >= 0.85
max_drawdown severity 改善 >= 5pp，或候选 drawdown 不恶化且 downside concentration 改善
average_cash_rate <= 0.65
cash_gt_90pct_equity_day_share <= 0.25
average_position_count >= 5
fee/turnover 不得无补偿恶化
no production/order/target fields
```

## 5. 允许结论

```text
PASS_READY_FOR_RCPT9D_CLOSURE
FAIL_NO_MAPPING_PASSES_LONGER_OOS_GATE
FAIL_NEEDS_RCPT9C_REPAIR
STOP_SCOPE_OR_LINEAGE_VIOLATION
```
