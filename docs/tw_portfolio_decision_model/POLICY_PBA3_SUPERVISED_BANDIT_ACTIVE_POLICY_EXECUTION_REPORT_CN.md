---
created_at: 2026-06-22T15:59:59+00:00
status: executed_pba3_supervised_bandit_active_policy
phase: PBA3_SUPERVISED_BANDIT_ACTIVE_POLICY
mainline_doc: docs/tw_portfolio_decision_model/POLICY_PBA_BASELINE_ANCHORED_ACTIVE_POLICY_MAINLINE_CN.md
work_doc: docs/tw_portfolio_decision_model/POLICY_PBA3_SUPERVISED_BANDIT_ACTIVE_POLICY_WORK_CN.md
artifact_root: data_tw/experiments/baseline_anchored_active_policy/pba3_supervised_bandit_active_policy
strict_test_used: false
production_allowed: false
recommendation: STOP_NO_STRICT_TEST_REQUEST
---

# PBA3 Supervised / Bandit Active Policy 执行报告

## 1. Scope

本轮只执行 PBA3 supervised / bandit active policy。未运行或读取 strict_test，未进入 PBA4/PBA5/PBA6，未输出 OrderIntent 或目标仓位/数量。

## 2. Documents Read

```text
docs/tw_portfolio_decision_model/POLICY_PBA_BASELINE_ANCHORED_ACTIVE_POLICY_MAINLINE_CN.md
docs/tw_portfolio_decision_model/POLICY_PBA2_RULE_CALIBRATED_ACTIVE_OVERLAY_SANITY_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_PBA2_RULE_CALIBRATED_ACTIVE_OVERLAY_SANITY_EXECUTION_REPORT_CN.md
docs/tw_portfolio_decision_model/POLICY_PBA1_BASELINE_SNAPSHOT_BUILD_AND_PARITY_REPLAY_REVIEW_CN.md
```

## 3. Model Candidates and Datasets

候选模型已在 `model_candidate_manifest.json` 预声明。训练数据来自 PBA1 baseline snapshot 与 PBA2 selected active overlay diagnostic decisions，仅使用 train window 训练。

## 4. Validation Selection

```text
selected_model_id = shallow_mlp_active_policy_seed_23
validation_baseline_net_return_after_fee_tax = 0.95376753
pba2_selected_validation_net_return_after_fee_tax = 0.97910586
selected_validation_net_return_after_fee_tax = 1.20247421
selected_excess_return_after_fee_tax = 0.24870668
validation_pass = False
```

## 5. Gate Summary

```text
fold_stability_pass = False
seed_stability_pass = True
participation_gates_pass = True
cash_dominance_gates_pass = True
risk_asset_exposure_pass = True
cost_turnover_not_pathological = True
not_baseline_clone = True
ood_action_audit_pass = True
pnl_concentration_audit_pass = True
```

## 6. Forbidden Consumer Audit

```text
strict_test_used = false
order_intent_output = false
target_weight_output = false
target_position_output = false
quantity_or_broker_output = false
provider/latest/monitor/frontend/Agent/broker/production touched = false
```

## 7. Recommendation

```text
STOP_NO_STRICT_TEST_REQUEST
```
