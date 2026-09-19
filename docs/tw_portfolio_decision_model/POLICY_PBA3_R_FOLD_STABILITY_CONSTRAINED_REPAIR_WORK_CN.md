---
created_at: 2026-06-22
status: reviewer_next_work_document
phase: PBA3_R_FOLD_STABILITY_CONSTRAINED_REPAIR
mainline_doc: docs/tw_portfolio_decision_model/POLICY_PBA_BASELINE_ANCHORED_ACTIVE_POLICY_MAINLINE_CN.md
coordinator_opinion: docs/tw_portfolio_decision_model/POLICY_PBA3_COORDINATOR_OPINION_FOR_REVIEWER_CN.md
previous_review: docs/tw_portfolio_decision_model/POLICY_PBA3_SUPERVISED_BANDIT_ACTIVE_POLICY_REVIEW_CN.md
previous_execution_report: docs/tw_portfolio_decision_model/POLICY_PBA3_SUPERVISED_BANDIT_ACTIVE_POLICY_EXECUTION_REPORT_CN.md
pba1_artifact_root: data_tw/experiments/baseline_anchored_active_policy/pba1_baseline_snapshot_parity_replay
pba2_artifact_root: data_tw/experiments/baseline_anchored_active_policy/pba2_rule_calibrated_active_overlay_sanity
pba3_artifact_root: data_tw/experiments/baseline_anchored_active_policy/pba3_supervised_bandit_active_policy
artifact_root: data_tw/experiments/baseline_anchored_active_policy/pba3_r_fold_stability_repair
strict_test_authorized: false
pba5_authorized: false
pba4_offline_rl_authorized: false
production_allowed: false
readonly_only: true
simulation_only: true
not_order: true
not_target_weight: true
not_target_position: true
not_quantity: true
---

# PBA3-R Fold-stability Constrained Repair 工作文档

## 1. 本轮目标

你是执行者。请继续 PBA Baseline-anchored Active Policy 主线的 PBA3 修复步骤：

```text
PBA3_R_FOLD_STABILITY_CONSTRAINED_REPAIR
```

本轮目标不是追求更高 validation return，而是修复和验证 PBA3 暴露出的稳定性问题：

```text
fold / regime / time split stability
```

允许牺牲一部分 2025 validation return，但必须证明 train folds / subfolds / validation 不再出现明显方向反转。

本轮不授权 PBA5，不授权 strict_test，不授权 PBA4 offline RL，不授权生产或订单输出。

## 2. 必须读取

执行前必须读取：

```text
docs/tw_portfolio_decision_model/POLICY_PBA_BASELINE_ANCHORED_ACTIVE_POLICY_MAINLINE_CN.md
docs/tw_portfolio_decision_model/POLICY_PBA3_SUPERVISED_BANDIT_ACTIVE_POLICY_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_PBA3_SUPERVISED_BANDIT_ACTIVE_POLICY_EXECUTION_REPORT_CN.md
docs/tw_portfolio_decision_model/POLICY_PBA3_COORDINATOR_OPINION_FOR_REVIEWER_CN.md
```

必须使用既有产物：

```text
data_tw/experiments/baseline_anchored_active_policy/pba1_baseline_snapshot_parity_replay/
data_tw/experiments/baseline_anchored_active_policy/pba2_rule_calibrated_active_overlay_sanity/
data_tw/experiments/baseline_anchored_active_policy/pba3_supervised_bandit_active_policy/
```

## 3. 授权范围

本轮只允许做稳定性约束修复：

```text
1. walk-forward / subfold stability audit。
2. outer_train 内部 rolling / half-year folds。
3. 对 PBA3 已预声明模型做稳定性约束重训。
4. 降低模型复杂度。
5. 加 regularization / early stopping，但只能用 train folds。
6. 对 active decision change rate 设置下限和上限。
7. 增加 regime stability audit。
8. 保留 participation / cash dominance / risk exposure / OOD / baseline clone / PnL concentration gates。
```

候选模型不得无界扩展，只允许：

```text
supervised_utility_logistic_or_tree_stability_constrained
contextual_bandit_conservative_stability_constrained
shallow_mlp_active_policy_stability_constrained
```

## 4. 禁止事项

本轮禁止：

```text
1. 运行或读取 strict_test。
2. 进入 PBA5。
3. 启动 PBA4 offline RL。
4. 扩展到 qlib+LTR。
5. 新增 free allocation vector。
6. 新增 target_weight / target_position / quantity。
7. 输出 OrderIntent。
8. provider/latest/monitor/frontend/Agent/broker/production 扩权。
9. 根据 validation 反复调参。
10. 只为了保留 2025 validation 最优结果而放宽 stability gate。
11. 使用 gross return、单 seed 最好结果、train return 或人工挑选 checkpoint 作为通过条件。
```

## 5. 窗口与 Fold 设计

必须保持外层窗口隔离：

```text
outer_train = 2023-01-01..2024-12-31
outer_validation = 2025-01-01..2025-12-31
strict_test = 2026-01-01..2026-05-07, declared only, not used
```

必须在 `outer_train` 内部定义 stability folds，例如：

```text
fold_1 = 2023H1
fold_2 = 2023H2
fold_3 = 2024H1
fold_4 = 2024H2
```

或使用 rolling / expanding split，但必须写入：

```text
train_fold_split_manifest.json
```

## 6. 选择规则

选择规则必须预先固定：

```text
1. 先过 hard gates。
2. 再看 fold stability。
3. 再看 validation net_return_after_fee_tax。
```

不得用以下方式选择：

```text
单一 2025 validation 最好结果
单 seed 最好结果
gross return
train return
strict_test
人工挑选 checkpoint
```

## 7. 必须输出产物

artifact root：

```text
data_tw/experiments/baseline_anchored_active_policy/pba3_r_fold_stability_repair/
```

必须输出：

```text
manifest.json
model_candidate_manifest.json
train_fold_split_manifest.json
stability_constraint_design.md
train_fold_replay_metrics_by_model.csv
fold_stability_audit.csv
regime_stability_audit.csv
validation_replay_metrics_by_model.csv
validation_selection_audit.csv
seed_stability_audit.csv
participation_gate_audit.csv
cash_dominance_gate_audit.csv
risk_asset_exposure_audit.csv
cost_turnover_audit.csv
baseline_clone_audit.csv
active_decision_change_rate_audit.csv
ood_action_audit.csv
behavior_policy_coverage_audit.csv
pnl_concentration_audit.csv
feature_available_at_audit.csv
forbidden_feature_and_consumer_audit.csv
validator_report.json
golden_samples_report.json
```

必须写执行报告：

```text
docs/tw_portfolio_decision_model/POLICY_PBA3_R_FOLD_STABILITY_CONSTRAINED_REPAIR_EXECUTION_REPORT_CN.md
```

## 8. Stability Constraint Design 要求

`stability_constraint_design.md` 必须说明：

```text
1. 为什么 PBA3 原模型 fold stability 失败。
2. 本轮采用哪些稳定性约束。
3. 如何避免只追求 2025 validation 最优。
4. active decision change rate 下限和上限。
5. regularization / early stopping 如何只用 train folds。
6. regime stability 如何定义。
7. 如何保证仍是 baseline-anchored active overlay，而不是 free allocation。
```

## 9. Fold / Regime Audit 要求

`train_fold_replay_metrics_by_model.csv` 必须至少包含：

```text
model_id
fold_id
fold_start_date
fold_end_date
baseline_net_return_after_fee_tax
model_net_return_after_fee_tax
excess_return_after_fee_tax
turnover
cost_drag
participation_rate
risk_asset_exposure
cash_dominance_rate
status
```

`fold_stability_audit.csv` 必须至少包含：

```text
model_id
fold_count
positive_excess_fold_count
negative_excess_fold_count
median_fold_excess_return
worst_fold_excess_return
direction_stable
train_validation_direction_reversal
fold_stability_pass
status
```

`regime_stability_audit.csv` 必须至少覆盖：

```text
market_regime
volatility_regime
score_dispersion_regime
baseline_net_return_after_fee_tax
model_net_return_after_fee_tax
excess_return_after_fee_tax
status
```

## 10. Validation 通过条件

PBA3-R 只有在以下全部满足时，才可建议审查者考虑 PBA3-R validation pass：

```text
1. validation net_return_after_fee_tax > PBA1 baseline。
2. validation net_return_after_fee_tax >= PBA2 selected rule，或略低但有清楚稳定性收益。
3. fold stability pass：
   - train folds 中多数 fold excess_return >= 0；
   - 不得再出现整体 train 大幅输 baseline、validation 大幅赢 baseline 的方向反转。
4. seed stability pass。
5. participation gates pass。
6. cash dominance gates pass。
7. risk asset exposure gates pass。
8. cost / turnover not pathological。
9. not baseline clone。
10. OOD action audit pass。
11. pnl concentration audit pass。
12. strict_test_used = false。
13. forbidden consumer / OrderIntent / target_weight / target_position / quantity audit pass。
```

如果 PBA3-R 仍然出现：

```text
train/fold 方向显著为负，但 validation 显著为正
```

必须：

```text
STOP_NO_STRICT_TEST_REQUEST
```

不得进入 PBA5。

## 11. Validator / Golden Samples

`validator_report.json` 必须检查：

```text
pba1_artifact_loaded
pba2_artifact_loaded
pba3_artifact_loaded
model_candidates_predeclared
train_fold_split_manifest_exists
strict_test_not_used
no_pba5_request
no_pba4_offline_rl
no_qlib_ltr
no_order_intent_output
no_target_weight
no_target_position
no_quantity
no_broker_order
no_provider_monitor_frontend_agent_production
fold_stability_audit_exists
regime_stability_audit_exists
active_decision_change_rate_audit_exists
feature_available_at_audit_pass
forbidden_feature_and_consumer_audit_pass
```

`golden_samples_report.json` 必须包含：

```text
positive: stability-constrained baseline-anchored model accepted.
positive: fold-stable validation selection accepted.
positive: readonly replay accepted.
negative: strict_test metrics access must fail.
negative: PBA5 request must fail.
negative: PBA4 offline RL request must fail.
negative: qlib+LTR adapter request must fail.
negative: target_weight field must fail.
negative: target_position field must fail.
negative: quantity / broker_order must fail.
negative: OrderIntentArtifact consumer must fail.
negative: train-negative validation-positive direction reversal pass claim must fail.
negative: cash-only / no-trade pass claim must fail.
negative: unpredeclared model candidate must fail.
```

## 12. 执行报告要求

执行报告必须包括：

```text
1. Scope：说明只做 PBA3-R fold-stability constrained repair。
2. Documents read。
3. Fold split design。
4. Stability constraints applied。
5. Model candidates and parameters。
6. Fold / regime replay metrics。
7. Validation replay metrics and selection。
8. Fold / seed stability result。
9. Participation / cash dominance / risk exposure gates。
10. OOD / behavior coverage audit。
11. Cost / turnover / baseline clone / PnL concentration audit。
12. Forbidden feature / forbidden consumer audit。
13. Issues / blockers / deviations。
14. Recommendation：只能是 PASS_READY_FOR_REVIEWER_TO_CONSIDER_PBA3_R_VALIDATION_PASS 或 STOP_NO_STRICT_TEST_REQUEST。
```

如果 PBA3-R 未通过，执行者不得请求 strict_test、PBA5、PBA4 或 qlib+LTR。
