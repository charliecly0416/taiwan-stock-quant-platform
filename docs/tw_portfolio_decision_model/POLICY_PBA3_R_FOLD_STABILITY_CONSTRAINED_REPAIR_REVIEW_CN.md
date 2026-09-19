---
created_at: 2026-06-22
status: review_fail_stop_no_strict_test_no_pba5
phase_reviewed: PBA3_R_FOLD_STABILITY_CONSTRAINED_REPAIR
mainline_doc: docs/tw_portfolio_decision_model/POLICY_PBA_BASELINE_ANCHORED_ACTIVE_POLICY_MAINLINE_CN.md
work_doc: docs/tw_portfolio_decision_model/POLICY_PBA3_R_FOLD_STABILITY_CONSTRAINED_REPAIR_WORK_CN.md
execution_report: docs/tw_portfolio_decision_model/POLICY_PBA3_R_FOLD_STABILITY_CONSTRAINED_REPAIR_EXECUTION_REPORT_CN.md
artifact_root: data_tw/experiments/baseline_anchored_active_policy/pba3_r_fold_stability_repair
verdict: FAIL_STOP_NO_STRICT_TEST_NO_PBA5
pba3_r_validation_passed: false
pba5_authorized: false
pba4_offline_rl_authorized: false
strict_test_authorized: false
production_allowed: false
readonly_only: true
simulation_only: true
not_order: true
not_target_weight: true
not_target_position: true
not_quantity: true
---

# PBA3-R Fold-stability Constrained Repair 审查报告

## 1. 审查结论

结论：

```text
FAIL_STOP_NO_STRICT_TEST_NO_PBA5
```

执行者按统筹意见完成了 PBA3-R 稳定性修复实验，并且在失败情况下正确 STOP：

```text
strict_test_used = false
pba5_authorized = false
pba4_offline_rl_authorized = false
production_allowed = false
order_intent_output = false
target_weight_output = false
target_position_output = false
quantity_or_broker_output = false
recommendation = STOP_NO_STRICT_TEST_REQUEST
```

本轮没有候选同时满足：

```text
fold stability
validation return > baseline
not baseline clone
active decision change rate pass
```

因此不得进入：

```text
PBA5 strict-test final replay
strict_test
PBA4 offline RL
qlib+LTR
production/default
OrderIntent / target_weight / target_position / quantity
provider/latest/monitor/frontend/Agent/broker
```

## 2. 主线 Gate 对照

PBA3-R 通过条件要求：

```text
validation net_return_after_fee_tax > PBA1 baseline
validation net_return_after_fee_tax >= PBA2 selected rule，或略低但有清楚稳定性收益
fold stability pass
seed stability pass
participation / cash dominance / risk asset exposure gates pass
cost / turnover not pathological
not baseline clone
OOD action audit pass
pnl concentration audit pass
strict_test_used=false
forbidden consumer audit pass
```

本轮结果：

```text
validation > baseline: FAIL for selected fold-stable model
validation >= PBA2 selected rule: FAIL
fold stability pass: PASS for baseline-clone candidates only
seed stability pass: FAIL for shallow_mlp stability-constrained family
participation gates pass: PASS
cash dominance gates pass: PASS
risk asset exposure gates pass: PASS
cost / turnover not pathological: PASS
not baseline clone: FAIL for all candidates
active decision change rate pass: FAIL for all candidates
OOD action audit pass: PASS
pnl concentration audit pass: PASS
strict_test_used=false: PASS
forbidden consumer audit: PASS
```

总体评价：

```text
FAIL
```

## 3. 关键证据

### 3.1 Validation Selection

`validation_selection_audit.csv`：

```text
selected_model_id = supervised_utility_logistic_or_tree_stability_constrained
validation_baseline_net_return_after_fee_tax = 0.95376753
pba2_selected_validation_net_return_after_fee_tax = 0.97910586
selected_validation_net_return_after_fee_tax = 0.95376753
selected_excess_return_after_fee_tax = 0.0
validation_pass = False
recommendation = STOP_NO_STRICT_TEST_REQUEST
```

评价：

```text
FAIL
```

selected model 只是复现 baseline，不是有效 active policy。

### 3.2 Fold Stability

`fold_stability_audit.csv`：

```text
contextual_bandit_conservative_stability_constrained:
  positive_excess_fold_count = 2
  negative_excess_fold_count = 2
  fold_stability_pass = False
  validation_excess_return = 0.07789642

supervised_utility_logistic_or_tree_stability_constrained:
  positive_excess_fold_count = 4
  negative_excess_fold_count = 0
  fold_stability_pass = True
  validation_excess_return = 0.0
```

评价：

```text
MIXED_BUT_FAIL_FOR_SELECTION
```

唯一仍有 validation excess 的 contextual bandit 没有通过 fold stability；fold-stable 候选则退化为 baseline clone。

### 3.3 Baseline Clone / Active Decision Change Rate

`baseline_clone_audit.csv`：

```text
not_baseline_clone = False for all candidates
status = fail for all candidates
```

`active_decision_change_rate_audit.csv`：

```text
contextual_bandit_conservative_stability_constrained: active_decision_change_rate = 0.00367377, minimum = 0.005, status = fail
supervised_utility_logistic_or_tree_stability_constrained: active_decision_change_rate = 0.0, status = fail
all shallow_mlp stability-constrained seeds: active_decision_change_rate = 0.0, status = fail
```

评价：

```text
FAIL
```

稳定性约束把多数候选推回 baseline clone / no active overlay，未形成有效 active policy。

### 3.4 Regime Stability

`regime_stability_audit.csv` 显示 contextual bandit：

```text
caution: excess = 0.04332361, pass
normal: excess = 0.03041202, pass
risk_off: excess = -0.01542057, fail
```

评价：

```text
FAIL_FOR_FULL_REGIME_STABILITY
```

当前仍存在 regime 依赖，尤其 risk_off 段未通过。

## 4. 合同与安全边界

`validator_report.json` 确认：

```text
strict_test_not_used = true
no_pba5_request = true
no_pba4_offline_rl = true
no_qlib_ltr = true
no_order_intent_output = true
no_target_weight = true
no_target_position = true
no_quantity = true
no_broker_order = true
no_provider_monitor_frontend_agent_production = true
feature_available_at_audit_pass = true
forbidden_feature_and_consumer_audit_pass = true
```

`forbidden_feature_and_consumer_audit.csv` 确认未触达：

```text
strict_test_metrics
PBA5 request
PBA4 offline RL
qlib+LTR adapter
target_weight
target_position
quantity
broker_order
OrderIntentArtifact
provider/latest/monitor/frontend/Agent/broker/production
free_allocation_vector
```

评价：

```text
PASS
```

## 5. Findings

### High: PBA3-R 没有形成非 baseline-clone 的稳定模型

所有候选 `not_baseline_clone = False` 或 active decision change rate 低于下限。

影响：

```text
不得进入 PBA5。
不得运行 strict_test。
不得声称 PBA3-R validation pass。
```

### High: 有 validation excess 的候选仍未通过 fold / regime stability

`contextual_bandit_conservative_stability_constrained` validation excess 为 `0.07789642`，但 fold stability fail，risk_off regime fail，active decision change rate fail。

影响：

```text
仍不能作为稳定 active policy。
```

### Medium: Stability repair 把模型推向 baseline clone

fold-stable 候选的 validation excess 为 0，active decision change rate 为 0。

影响：

```text
当前稳定性约束过强或 action policy 仍缺乏可迁移 edge。
```

## 6. 下一步控制

本审查不写 PBA5 strict-test 工作文档。

本审查也不直接写 PBA4 / qlib+LTR / production 工作文档。原因：

```text
1. PBA3-R 未通过 validation gate。
2. strict_test 未授权。
3. 统筹明确 PBA4 offline RL、qlib+LTR、production/default/order 均未授权。
4. 当前失败是策略稳定性与非 clone active edge 未同时成立，需要回到统筹判断。
```

在统筹给出新意见前，执行者不得继续：

```text
运行 strict_test
进入 PBA5
进入 PBA4 offline RL
扩展 qlib+LTR
继续同线无界调参
接入 production / OrderIntent / Agent / frontend / broker / provider
```

## 7. 给统筹的建议

建议统筹记录为：

```text
PBA3-R fold-stability constrained repair: executed, boundary compliant, no stable non-clone active policy found, STOP before strict_test.
```

当前证据支持：

```text
PBA 路线比 PAL 更接近项目结构，且曾出现 validation edge；
但 PBA3/PBA3-R 还没有证明稳定、非 baseline clone、可迁移的 active policy。
```

当前证据不支持：

```text
进入 PBA5 strict_test。
启动 PBA4 offline RL。
扩展 qlib+LTR。
生产或订单集成。
```

后续应由统筹决定是否：

```text
1. 暂停 PBA3 模型子线，回到 PBA2 rule-based overlay；
2. 重新定义 regime-conditioned active policy；
3. 调整 policy train/validation 切分；
4. 关闭当前 qlib-only PBA policy 主线。
```
