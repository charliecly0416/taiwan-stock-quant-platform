---
created_at: 2026-06-22
status: review_pass_ready_for_pba2_work_document
phase_reviewed: PBA1_BASELINE_SNAPSHOT_BUILD_AND_PARITY_REPLAY
mainline_doc: docs/tw_portfolio_decision_model/POLICY_PBA_BASELINE_ANCHORED_ACTIVE_POLICY_MAINLINE_CN.md
work_doc: docs/tw_portfolio_decision_model/POLICY_PBA1_BASELINE_SNAPSHOT_BUILD_AND_PARITY_REPLAY_WORK_CN.md
execution_report: docs/tw_portfolio_decision_model/POLICY_PBA1_BASELINE_SNAPSHOT_BUILD_AND_PARITY_REPLAY_EXECUTION_REPORT_CN.md
artifact_root: data_tw/experiments/baseline_anchored_active_policy/pba1_baseline_snapshot_parity_replay
verdict: PASS_READY_FOR_PBA2_RULE_CALIBRATED_ACTIVE_OVERLAY_SANITY_WORK
strict_test_authorized: false
training_authorized: false
pba2_authorized_by_mainline: true
production_allowed: false
readonly_only: true
simulation_only: true
not_order: true
not_target_weight: true
not_target_position: true
not_quantity: true
---

# PBA1 Baseline Snapshot Build And Parity Replay 审查报告

## 1. 审查结论

结论：

```text
PASS_READY_FOR_PBA2_RULE_CALIBRATED_ACTIVE_OVERLAY_SANITY_WORK
```

执行者完成了 PBA1 授权范围：

```text
1. BaselineActionSnapshotArtifact 已构建。
2. baseline parity replay ledger 已构建。
3. train / validation baseline parity metrics 均 pass。
4. feature available_at / PIT audit pass。
5. baseline action coverage audit pass。
6. cash/no-trade gate dry-run audit 已落成可计算字段。
7. validator / golden samples pass。
8. 未训练 active policy。
9. 未做 validation 选择。
10. 未运行或读取 strict_test。
11. 未输出 OrderIntent / target_weight / target_position / quantity / broker_order。
12. 未做 provider/latest/monitor/frontend/Agent/broker/production 扩权。
```

本审查允许按 PBA 主线进入：

```text
PBA2: Rule-calibrated Active Overlay Sanity
```

但 PBA2 仍不授权训练模型、不授权 strict_test、不授权生产或订单输出。

## 2. 证据核查

artifact root：

```text
data_tw/experiments/baseline_anchored_active_policy/pba1_baseline_snapshot_parity_replay/
```

确认存在：

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

评价：

```text
PASS
```

## 3. Baseline Parity

`baseline_parity_metrics.csv`：

```text
train:
  baseline_reference_net_return_after_fee_tax = 2.41885797
  pba1_replay_net_return_after_fee_tax = 2.41885797
  absolute_diff = 0.0
  baseline_reference_turnover = 87.37059302
  pba1_replay_turnover = 87.37059302
  turnover_diff = 0.0
  status = pass

validation:
  baseline_reference_net_return_after_fee_tax = 0.95376753
  pba1_replay_net_return_after_fee_tax = 0.95376753
  absolute_diff = 0.0
  baseline_reference_turnover = 42.18778217
  pba1_replay_turnover = 42.18778217
  turnover_diff = 0.0
  status = pass
```

评价：

```text
PASS
```

PBA1 已证明 readonly replay 能复现 baseline return / turnover 口径，可以作为 PBA2 active overlay sanity 的比较锚点。

## 4. Baseline Snapshot / Action Coverage

执行报告给出：

```text
snapshot_rows = 6805
ledger_rows = 723
train_date_count = 481
validation_date_count = 242
```

`baseline_action_coverage_audit.csv`：

```text
train:
  rebalance_date_count = 481
  instrument_count = 120
  buy_candidate_count = 477
  sell_candidate_count = 439
  hold_count = 3541
  status = pass

validation:
  rebalance_date_count = 242
  instrument_count = 88
  buy_candidate_count = 235
  sell_candidate_count = 215
  hold_count = 1898
  status = pass
```

评价：

```text
PASS
```

PBA2 可以基于 buy/sell/hold contexts 做 rule-calibrated active overlay sanity。

## 5. Feature Available-at / PIT

`feature_available_at_audit.csv` 覆盖：

```text
baseline_rank
baseline_score
baseline_action_type
baseline_position_before_diagnostic
baseline_holding_age
price / cost / turnover inputs
market state inputs
```

train / validation 均显示：

```text
future_return_used = False
label_used = False
future_price_used = False
realized_pnl_as_feature_used = False
same_day_unavailable_data_used = False
strict_test_metrics_used = False
validation_metric_used_inside_training_loop = False
status = pass
```

评价：

```text
PASS
```

## 6. Cash / No-trade Gate Dry-run

`cash_no_trade_gate_dry_run_audit.csv` 已把 PBA0 gate 落成可计算字段：

```text
train:
  actual_baseline_participation_rate = 0.99168399
  actual_baseline_risk_asset_exposure = 0.997921
  actual_baseline_cash_dominance_rate = 0.002079
  actual_baseline_action_coverage = 3
  status = pass

validation:
  actual_baseline_participation_rate = 0.97107438
  actual_baseline_risk_asset_exposure = 0.99586777
  actual_baseline_cash_dominance_rate = 0.00413223
  actual_baseline_action_coverage = 3
  status = pass
```

评价：

```text
PASS
```

PBA2 必须继续使用这些字段，防止 active overlay 通过 cash-only / no-trade 获得形式 pass。

## 7. Forbidden Actions Audit

`forbidden_feature_and_consumer_audit.csv` 确认：

```text
future_return / label / realized_pnl / future_price 未使用
strict_test_metrics 未使用
target_weight / target_position / quantity / broker_order 未使用
OrderIntentArtifact 未触达
provider / monitor / frontend / Agent / broker / production 未触达
```

`validator_report.json` 确认：

```text
strict_test_not_used = true
no_training_run = true
no_active_policy_run = true
no_order_intent_output = true
no_target_weight = true
no_target_position = true
no_quantity = true
no_broker_order = true
no_provider_monitor_frontend_agent_production = true
```

评价：

```text
PASS
```

## 8. Findings

### Critical

无。

### High

无。

### Medium

PBA1 replay 使用既有 baseline accounting 口径作为 reference 与 PBA1 replay 同源复核。该处理符合 PBA1 parity 目标，但 PBA2 必须避免把同源 parity 当作 active overlay 有效性证明。

处理：

```text
PBA2 工作文档要求所有规则与 baseline 做 after-fee-tax 对照，并检查 participation / risk exposure / cash dominance / not baseline clone。
```

### Low

无。

## 9. 下一步控制

允许进入：

```text
PBA2: Rule-calibrated Active Overlay Sanity
```

对应工作文档：

```text
docs/tw_portfolio_decision_model/POLICY_PBA2_RULE_CALIBRATED_ACTIVE_OVERLAY_SANITY_WORK_CN.md
```

仍禁止：

```text
训练模型
strict_test
OrderIntent
target_weight / target_position / quantity / broker_order
provider/latest/monitor/frontend/Agent/broker/production
free allocation vector
validation 反复调参
用 cash-only / no-trade 作为成功
```
