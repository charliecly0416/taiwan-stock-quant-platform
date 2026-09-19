---
created_at: 2026-06-22T14:15:06+00:00
status: executed_pba1_baseline_snapshot_parity_replay
phase: PBA1_BASELINE_SNAPSHOT_BUILD_AND_PARITY_REPLAY
mainline_doc: docs/tw_portfolio_decision_model/POLICY_PBA_BASELINE_ANCHORED_ACTIVE_POLICY_MAINLINE_CN.md
work_doc: docs/tw_portfolio_decision_model/POLICY_PBA1_BASELINE_SNAPSHOT_BUILD_AND_PARITY_REPLAY_WORK_CN.md
artifact_root: data_tw/experiments/baseline_anchored_active_policy/pba1_baseline_snapshot_parity_replay
strict_test_used: false
training_run: false
active_policy_run: false
production_allowed: false
recommendation: PASS_READY_FOR_REVIEWER_TO_AUDIT_PBA1
---

# PBA1 Baseline Snapshot Build And Parity Replay 执行报告

## 1. Scope

本轮只执行 PBA1 baseline snapshot / parity replay。未训练 active policy，未做 validation 选择，未运行或读取 strict_test，未进入 PBA2。

## 2. Documents Read

```text
docs/tw_portfolio_decision_model/POLICY_PBA_BASELINE_ANCHORED_ACTIVE_POLICY_MAINLINE_CN.md
docs/tw_portfolio_decision_model/POLICY_PBA0_CONTRACT_BASELINE_AUDIT_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_PBA0_CONTRACT_BASELINE_AUDIT_EXECUTION_REPORT_CN.md
docs/tw_portfolio_decision_model/POLICY_PBA0_CONTRACT_BASELINE_AUDIT_WORK_CN.md
```

## 3. Changes / Artifacts

```text
manifest.json
baseline_action_snapshot_artifact.csv
baseline_parity_replay_ledger.csv
baseline_parity_metrics.csv
baseline_action_coverage_audit.csv
feature_available_at_audit.csv
cash_no_trade_gate_dry_run_audit.csv
forbidden_feature_and_consumer_audit.csv
validator_report.json
golden_samples_report.json
```

## 4. Baseline Snapshot Summary

```text
snapshot_rows = 6805
ledger_rows = 723
train_date_count = 481
validation_date_count = 242
```

## 5. Parity Metrics

```text
[
  {
    "split": "train",
    "start_date": "2023-01-03",
    "end_date": "2024-12-31",
    "baseline_reference_net_return_after_fee_tax": 2.41885797,
    "pba1_replay_net_return_after_fee_tax": 2.41885797,
    "absolute_diff": 0.0,
    "relative_diff": 0.0,
    "baseline_reference_turnover": 87.37059302,
    "pba1_replay_turnover": 87.37059302,
    "turnover_diff": 0.0,
    "status": "pass"
  },
  {
    "split": "validation",
    "start_date": "2025-01-02",
    "end_date": "2025-12-31",
    "baseline_reference_net_return_after_fee_tax": 0.95376753,
    "pba1_replay_net_return_after_fee_tax": 0.95376753,
    "absolute_diff": 0.0,
    "relative_diff": 0.0,
    "baseline_reference_turnover": 42.18778217,
    "pba1_replay_turnover": 42.18778217,
    "turnover_diff": 0.0,
    "status": "pass"
  }
]
```

## 6. PIT / Available-at Audit Summary

```text
feature_available_at_audit_pass = True
baseline_action_coverage_pass = True
cash_no_trade_gate_dry_run_audit_exists = True
```

## 7. Forbidden Actions Audit

```text
training_run = false
active_policy_run = false
strict_test_used = false
order_intent_output = false
target_weight_output = false
target_position_output = false
quantity_or_broker_output = false
provider/latest/monitor/frontend/Agent/broker/production touched = false
```

## 8. Issues / Blockers / Deviations

PBA1 replay 使用既有 baseline accounting 口径作为 reference 与 PBA1 replay 同源复核，未输出 OrderIntentArtifact；内部 baseline intents 仅用于构建 readonly diagnostic snapshot。

## 9. Recommendation

```text
PASS_READY_FOR_REVIEWER_TO_AUDIT_PBA1
```
