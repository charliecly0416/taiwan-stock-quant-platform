---
created_at: 2026-06-22
status: review_fail_stop_no_strict_test_no_pba5
phase_reviewed: PBA3_SUPERVISED_BANDIT_ACTIVE_POLICY
mainline_doc: docs/tw_portfolio_decision_model/POLICY_PBA_BASELINE_ANCHORED_ACTIVE_POLICY_MAINLINE_CN.md
work_doc: docs/tw_portfolio_decision_model/POLICY_PBA3_SUPERVISED_BANDIT_ACTIVE_POLICY_WORK_CN.md
execution_report: docs/tw_portfolio_decision_model/POLICY_PBA3_SUPERVISED_BANDIT_ACTIVE_POLICY_EXECUTION_REPORT_CN.md
artifact_root: data_tw/experiments/baseline_anchored_active_policy/pba3_supervised_bandit_active_policy
verdict: FAIL_STOP_NO_STRICT_TEST_NO_PBA5
pba3_validation_passed: false
pba5_authorized: false
strict_test_authorized: false
production_allowed: false
readonly_only: true
simulation_only: true
not_order: true
not_target_weight: true
not_target_position: true
not_quantity: true
---

# PBA3 Supervised / Bandit Active Policy 审查报告

## 1. 审查结论

结论：

```text
FAIL_STOP_NO_STRICT_TEST_NO_PBA5
```

执行者完成了 PBA3 授权范围，并且在失败情况下正确 STOP：

```text
strict_test_used = false
production_allowed = false
order_intent_output = false
target_weight_output = false
target_position_output = false
quantity_or_broker_output = false
recommendation = STOP_NO_STRICT_TEST_REQUEST
```

虽然 selected model 的 validation after-fee-tax return 明显超过 baseline 和 PBA2 selected rule：

```text
selected_model_id = shallow_mlp_active_policy_seed_23
validation_baseline_net_return_after_fee_tax = 0.95376753
pba2_selected_validation_net_return_after_fee_tax = 0.97910586
selected_validation_net_return_after_fee_tax = 1.20247421
selected_excess_return_after_fee_tax = 0.24870668
```

但 PBA3 工作文档和主线把 `fold stability pass` 列为通过条件。本轮：

```text
fold_stability_pass = False
validation_pass = False
```

因此不得进入：

```text
PBA5 strict-test final replay
strict_test
production/default
OrderIntent / target_weight / target_position / quantity
provider/latest/monitor/frontend/Agent/broker
```

## 2. 主线 Gate 对照

PBA3 通过条件包括：

```text
validation return > baseline
seed stability / fold stability pass
participation gates pass
cash dominance gates pass
OOD action audit pass
strict_test_used=false
```

本轮结果：

```text
validation return > baseline: PASS
validation return >= PBA2 selected rule: PASS
fold stability pass: FAIL
seed stability pass: PASS
participation gates pass: PASS
cash dominance gates pass: PASS
risk asset exposure gates pass: PASS
cost / turnover not pathological: PASS
not baseline clone: selected model PASS
OOD action audit pass: PASS
pnl concentration audit pass: PASS
strict_test_used=false: PASS
forbidden consumer audit: PASS
```

总体评价：

```text
FAIL
```

原因是硬 gate `fold_stability_pass=False`。

## 3. 关键证据

### 3.1 Validation Return

`validation_replay_metrics_by_model.csv` 显示 selected model：

```text
model_id = shallow_mlp_active_policy_seed_23
validation_net_return_after_fee_tax = 1.20247421
baseline_net_return_after_fee_tax = 0.95376753
baseline_excess_return_after_fee_tax = 0.24870668
turnover = 41.39514683
cost_drag = 0.15511059
participation_rate = 0.98013245
risk_asset_exposure = 0.99173554
cash_dominance_rate = 0.00826446
```

评价：

```text
PASS_AS_RETURN_SIGNAL
```

该结果说明 supervised/bandit active policy 有明显 validation 收益信号，但不能覆盖稳定性失败。

### 3.2 Fold Stability

`fold_stability_audit.csv` 显示所有模型方向均不稳定：

```text
contextual_bandit_conservative:
  train_excess_return = -0.80615849
  validation_excess_return = 0.02533833
  direction_stable = False

shallow_mlp_active_policy_seed_23:
  train_excess_return = -0.92621018
  validation_excess_return = 0.24870668
  direction_stable = False
  status = fail
```

评价：

```text
FAIL
```

selected model 在 train 上显著落后 baseline，却在 validation 上显著领先。这与 PBA2 selected rule 的风险类似，不能直接进入 strict_test。

### 3.3 Seed Stability

`seed_stability_audit.csv`：

```text
shallow_mlp_active_policy:
  above_baseline_seed_count = 3
  seed_count = 3
  seed_stability_pass = True
```

评价：

```text
PASS
```

但 seed stability 不能替代 fold stability。

### 3.4 OOD / Behavior Coverage

`ood_action_audit.csv`：

```text
ood_action_rate = 0.0
unsupported_action_count = 0
status = pass
```

`behavior_policy_coverage_audit.csv` 显示 action 都来自 train 支持：

```text
block_baseline_buy
allow_baseline_buy
no_extra_action
allow_baseline_sell
```

评价：

```text
PASS
```

### 3.5 Participation / Cash / Risk Gates

selected model validation：

```text
participation_rate = 0.98013245
cash_dominance_rate = 0.00826446
risk_asset_exposure = 0.99173554
```

对应 audit 均 pass。

评价：

```text
PASS
```

该模型没有通过 cash-only / no-trade 形式获得通过。

## 4. 数据与合同审查

`model_candidate_manifest.json` 预声明候选：

```text
supervised_utility_logistic_or_tree
contextual_bandit_conservative
shallow_mlp_active_policy
```

`training_dataset_audit.csv` 和 `feature_available_at_audit.csv` 显示：

```text
future_return_as_feature = False
label_as_feature = False
realized_pnl_as_feature = False
future_price_as_feature = False
same_day_unavailable_data = False
strict_test_metrics = False
validation_metric_inside_training_loop = False
```

`forbidden_feature_and_consumer_audit.csv` 确认未触达：

```text
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

## 5. Validator / Golden Samples

`validator_report.json` 通过：

```text
pba1_artifact_loaded
pba2_artifact_loaded
model_candidates_predeclared
train_validation_separated
strict_test_not_used
no_order_intent_output
no_target_weight
no_target_position
no_quantity
no_broker_order
no_provider_monitor_frontend_agent_production
training_dataset_audit_pass
feature_available_at_audit_pass
forbidden_feature_and_consumer_audit_pass
fold_stability_audit_exists
seed_stability_audit_exists
participation_gate_audit_exists
cash_dominance_gate_audit_exists
risk_asset_exposure_audit_exists
ood_action_audit_exists
pnl_concentration_audit_exists
```

`golden_samples_report.json` 覆盖：

```text
positive baseline-anchored supervised / bandit / readonly replay
negative target_weight / target_position / quantity / broker_order
negative OrderIntent consumer
negative strict_test metrics access
negative future_return feature
negative unpredeclared model candidate
negative OOD unsupported action pass claim
negative cash-only / no-trade pass claim
negative PBA5 request without PBA3 validation pass
```

评价：

```text
PASS
```

## 6. Findings

### High: Fold stability 未通过

selected model 在 train 上显著低于 baseline，在 validation 上显著高于 baseline：

```text
train_excess_return = -0.92621018
validation_excess_return = 0.24870668
```

影响：

```text
不得进入 PBA5。
不得运行 strict_test。
不得声称 PBA3 validation pass。
```

### Medium: Validation 信号强，但可能存在窗口依赖

selected model validation return 高于 baseline 和 PBA2 selected rule，但所有候选都存在 train/validation 方向不一致。

影响：

```text
需要统筹判断是否授权 PBA3-R 稳定性修复或回到 PBA2/PBA3 重新约束模型。
```

### Low: shallow_mlp seed_37 baseline clone audit fail，但不是 selected model

`baseline_clone_audit.csv` 中：

```text
shallow_mlp_active_policy_seed_37 status = fail
```

selected `seed_23` 为 pass，因此不构成本轮 selected model 的失败原因。

## 7. 下一步控制

本审查不写 PBA5 strict-test 工作文档。

本审查也不直接写 repair 工作文档。原因：

```text
1. PBA3 出现强 validation 信号，但 fold stability hard gate 失败。
2. 主线规定 strict_test 只能在 validation 通过后由统筹单独授权。
3. 当前失败不是合同/安全问题，而是稳定性问题，下一步应由统筹决定是否授权 PBA3-R stability repair。
```

在统筹给出新意见前，执行者不得继续：

```text
运行 strict_test
进入 PBA5
继续同线调参
扩展 PBA4 offline RL
接入 production / OrderIntent / Agent / frontend / broker / provider
```

## 8. 给统筹的建议

建议统筹记录为：

```text
PBA3 supervised/bandit active policy: executed, boundary compliant, strong validation return signal, fold stability failed, STOP before strict_test.
```

当前证据支持：

```text
PBA active policy 路线有实验价值，且比 PAL free allocation 更接近项目结构。
```

当前证据不支持：

```text
直接进入 PBA5 strict_test。
直接作为稳定策略结论。
```

如继续，建议统筹优先考虑：

```text
PBA3-R fold-stability constrained repair；
要求 train/fold 方向一致、窗口稳定性提升，同时保持 validation after-fee-tax 高于 baseline。
```
