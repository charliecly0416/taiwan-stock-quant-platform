---
created_at: 2026-06-22
status: review_pass_with_conditions_ready_for_pba3_work_document
phase_reviewed: PBA2_RULE_CALIBRATED_ACTIVE_OVERLAY_SANITY
mainline_doc: docs/tw_portfolio_decision_model/POLICY_PBA_BASELINE_ANCHORED_ACTIVE_POLICY_MAINLINE_CN.md
work_doc: docs/tw_portfolio_decision_model/POLICY_PBA2_RULE_CALIBRATED_ACTIVE_OVERLAY_SANITY_WORK_CN.md
execution_report: docs/tw_portfolio_decision_model/POLICY_PBA2_RULE_CALIBRATED_ACTIVE_OVERLAY_SANITY_EXECUTION_REPORT_CN.md
artifact_root: data_tw/experiments/baseline_anchored_active_policy/pba2_rule_calibrated_active_overlay_sanity
verdict: PASS_WITH_CONDITIONS_READY_FOR_PBA3_SUPERVISED_BANDIT_ACTIVE_POLICY_WORK
pba2_validation_passed: true
strict_test_authorized: false
pba5_authorized: false
training_authorized_next_phase_only: true
production_allowed: false
readonly_only: true
simulation_only: true
not_order: true
not_target_weight: true
not_target_position: true
not_quantity: true
---

# PBA2 Rule-calibrated Active Overlay Sanity 审查报告

## 1. 审查结论

结论：

```text
PASS_WITH_CONDITIONS_READY_FOR_PBA3_SUPERVISED_BANDIT_ACTIVE_POLICY_WORK
```

执行者完成了 PBA2 授权范围：

```text
1. 只运行预声明 active overlay rules。
2. 未训练模型。
3. 未运行或读取 strict_test。
4. 未进入 PBA3 / PBA5。
5. selected rule 在 validation net_return_after_fee_tax 上超过 PBA1 baseline。
6. participation / cash dominance / risk asset exposure gates 通过。
7. cost / turnover not pathological 通过。
8. not baseline clone 通过。
9. forbidden feature / forbidden consumer audit 通过。
10. 未输出 OrderIntent / target_weight / target_position / quantity / broker_order。
```

本审查允许按 PBA 主线进入：

```text
PBA3: Supervised / Bandit Active Policy
```

但仍不授权：

```text
PBA5 strict-test final replay
strict_test
production/default
OrderIntent / target_weight / target_position / quantity
provider/latest/monitor/frontend/Agent/broker
```

## 2. Validation 结果

`validation_selection_audit.csv`：

```text
selected_rule_id = score_gap_buy_filter
selection_metric = validation_net_return_after_fee_tax
validation_baseline_net_return_after_fee_tax = 0.95376753
selected_validation_net_return_after_fee_tax = 0.97910586
selected_excess_return_after_fee_tax = 0.02533833
validation_pass = True
strict_test_used = False
```

评价：

```text
PASS
```

PBA2 已证明 baseline-anchored active overlay action space 至少存在一个 rule-level validation 改善信号。

## 3. Gate 审查

selected rule `score_gap_buy_filter` 的 validation 指标：

```text
participation_rate = 0.90023202
risk_asset_exposure = 0.99173554
cash_dominance_rate = 0.00826446
turnover = 37.19929140
baseline_turnover_reference = 42.18778217
cost_drag = 0.13073442
```

各 gate：

```text
participation_gates_pass = True
cash_dominance_gates_pass = True
risk_asset_exposure_pass = True
cost_turnover_not_pathological = True
not_baseline_clone = True
```

评价：

```text
PASS
```

该规则不是通过 cash-only / no-trade 形式通过。

## 4. 规则与选择合规性

`rule_config_manifest.json` 覆盖工作文档允许的 6 个规则：

```text
score_gap_buy_filter
score_zscore_buy_filter
holding_age_sell_delay
trend_confirmed_hold
market_risk_exposure_reduce
top_rank_active_tilt_diagnostic
```

所有规则：

```text
uses_strict_test = false
simulation_only = true
readonly_research_only = true
production_allowed = false
```

`validator_report.json` 确认：

```text
rules_predeclared = true
only_allowed_rules_used = true
train_validation_separated = true
validation_selection_once = true
strict_test_not_used = true
no_training_run = true
```

评价：

```text
PASS
```

## 5. 风险与限制

### Medium: selected rule 的 train 表现与 validation 表现方向不一致

`rule_replay_metrics_by_split.csv` 显示 selected `score_gap_buy_filter`：

```text
train:
  baseline_net_return_after_fee_tax = 2.41885797
  active_overlay_net_return_after_fee_tax = 1.61269948
  baseline_excess_return_after_fee_tax = -0.80615849
  status = fail

validation:
  baseline_net_return_after_fee_tax = 0.95376753
  active_overlay_net_return_after_fee_tax = 0.97910586
  baseline_excess_return_after_fee_tax = 0.02533833
  status = pass
```

影响：

```text
PBA2 可通过为 action-space sanity，但不能把该规则直接视为稳定策略。
PBA3 必须检查 fold stability / seed stability / OOD action audit。
```

### Low: pnl_concentration 未在 PBA2 计算

`rule_replay_metrics_by_split.csv` 的 `pnl_concentration` 为：

```text
not_computed_no_pnl_by_symbol_in_pba2
```

影响：

```text
PBA2 不因此失败，但 PBA3 若训练模型，必须补充分 symbol 或分 action 的收益贡献集中度审计。
```

## 6. Forbidden Actions Audit

`forbidden_feature_and_consumer_audit.csv` 确认以下均未使用 / 未触达：

```text
future_return
forward_return
label
realized_pnl
future_price
same_day_unavailable_data
strict_test_metrics
oracle_action
oracle_return
target_weight
target_position
quantity
broker_order
OrderIntentArtifact
provider publish / accepted latest switch
monitor / frontend / Agent / broker / production
```

评价：

```text
PASS
```

## 7. Validator / Golden Samples

`validator_report.json` 通过：

```text
pba1_artifact_loaded
rules_predeclared
only_allowed_rules_used
train_validation_separated
validation_selection_once
strict_test_not_used
no_training_run
no_order_intent_output
no_target_weight
no_target_position
no_quantity
no_broker_order
no_provider_monitor_frontend_agent_production
participation_gate_audit_exists
cash_dominance_gate_audit_exists
risk_asset_exposure_audit_exists
baseline_clone_audit_exists
feature_available_at_audit_pass
forbidden_feature_and_consumer_audit_pass
```

`golden_samples_report.json` 覆盖：

```text
positive score_gap / holding_age / readonly replay cases
negative unpredeclared rule
negative target_weight / target_position / quantity / broker_order
negative OrderIntent consumer
negative strict_test metrics access
negative cash-only / no-trade pass claim
negative gross-return-only pass claim
negative PBA3 request without PBA2 validation pass
```

评价：

```text
PASS
```

## 8. 下一步控制

允许进入：

```text
PBA3: Supervised / Bandit Active Policy
```

对应工作文档：

```text
docs/tw_portfolio_decision_model/POLICY_PBA3_SUPERVISED_BANDIT_ACTIVE_POLICY_WORK_CN.md
```

仍禁止：

```text
PBA5 strict-test final replay
strict_test
production/default
OrderIntent
target_weight / target_position / quantity / broker_order
provider/latest/monitor/frontend/Agent/broker
free allocation vector
```

PBA3 必须特别处理：

```text
1. selected rule train/validation 不一致风险。
2. fold stability / seed stability。
3. OOD action audit。
4. participation / cash dominance / risk exposure gates。
5. 不得把 PBA2 selected rule 当作直接生产策略。
```
