---
created_at: 2026-06-22T16:41:08+00:00
status: executed_pba3_r_fold_stability_constrained_repair
phase: PBA3_R_FOLD_STABILITY_CONSTRAINED_REPAIR
mainline_doc: docs/tw_portfolio_decision_model/POLICY_PBA_BASELINE_ANCHORED_ACTIVE_POLICY_MAINLINE_CN.md
work_doc: docs/tw_portfolio_decision_model/POLICY_PBA3_R_FOLD_STABILITY_CONSTRAINED_REPAIR_WORK_CN.md
artifact_root: data_tw/experiments/baseline_anchored_active_policy/pba3_r_fold_stability_repair
strict_test_used: false
production_allowed: false
recommendation: STOP_NO_STRICT_TEST_REQUEST
---

# PBA3-R Fold-stability Constrained Repair 执行报告

## 1. Scope

本轮只执行 PBA3-R fold-stability constrained repair。未运行或读取 strict_test，未进入 PBA5，未启动 PBA4 offline RL，未输出 OrderIntent / target_weight / target_position / quantity。

## 2. Documents Read

```text
docs/tw_portfolio_decision_model/POLICY_PBA_BASELINE_ANCHORED_ACTIVE_POLICY_MAINLINE_CN.md
docs/tw_portfolio_decision_model/POLICY_PBA3_SUPERVISED_BANDIT_ACTIVE_POLICY_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_PBA3_SUPERVISED_BANDIT_ACTIVE_POLICY_EXECUTION_REPORT_CN.md
docs/tw_portfolio_decision_model/POLICY_PBA3_COORDINATOR_OPINION_FOR_REVIEWER_CN.md
```

## 3. Fold Split Design

```text
2023H1 = 2023-01-01..2023-06-30
2023H2 = 2023-07-01..2023-12-31
2024H1 = 2024-01-01..2024-06-30
2024H2 = 2024-07-01..2024-12-31
outer_validation = 2025-01-01..2025-12-31
strict_test declared only, not used
```

## 4. Stability Constraints Applied

候选被限制为 PBA3 已授权模型族的 stability-constrained 版本：depth-1 tree、score-gap conservative bandit threshold 0.0025、regularized tiny MLP。选择顺序固定为 hard gates -> fold stability -> validation net return。

## 5. Validation Selection

```text
selected_model_id = supervised_utility_logistic_or_tree_stability_constrained
validation_baseline_net_return_after_fee_tax = 0.95376753
pba2_selected_validation_net_return_after_fee_tax = 0.97910586
selected_validation_net_return_after_fee_tax = 0.95376753
selected_excess_return_after_fee_tax = 0.0
fold_stability_pass = True
seed_stability_pass = True
validation_pass = False
```

## 6. Gate Summary

```text
participation_gates_pass = True
cash_dominance_gates_pass = True
risk_asset_exposure_pass = True
cost_turnover_not_pathological = True
not_baseline_clone = False
active_decision_change_rate_pass = False
ood_action_audit_pass = True
pnl_concentration_audit_pass = True
```

## 7. Issues / Blockers / Deviations

本轮没有候选同时通过 hard gates 与 fold stability；fold-stable 候选退化为 baseline clone / active decision change rate 不达标，因此按工作文档 STOP，不请求 strict_test/PBA5/PBA4。

## 8. Recommendation

```text
STOP_NO_STRICT_TEST_REQUEST
```
