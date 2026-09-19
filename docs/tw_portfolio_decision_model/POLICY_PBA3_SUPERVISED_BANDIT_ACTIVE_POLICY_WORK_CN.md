---
created_at: 2026-06-22
status: reviewer_next_work_document
phase: PBA3_SUPERVISED_BANDIT_ACTIVE_POLICY
mainline_doc: docs/tw_portfolio_decision_model/POLICY_PBA_BASELINE_ANCHORED_ACTIVE_POLICY_MAINLINE_CN.md
previous_review: docs/tw_portfolio_decision_model/POLICY_PBA2_RULE_CALIBRATED_ACTIVE_OVERLAY_SANITY_REVIEW_CN.md
previous_execution_report: docs/tw_portfolio_decision_model/POLICY_PBA2_RULE_CALIBRATED_ACTIVE_OVERLAY_SANITY_EXECUTION_REPORT_CN.md
pba1_artifact_root: data_tw/experiments/baseline_anchored_active_policy/pba1_baseline_snapshot_parity_replay
pba2_artifact_root: data_tw/experiments/baseline_anchored_active_policy/pba2_rule_calibrated_active_overlay_sanity
artifact_root: data_tw/experiments/baseline_anchored_active_policy/pba3_supervised_bandit_active_policy
strict_test_authorized: false
production_allowed: false
readonly_only: true
simulation_only: true
not_order: true
not_target_weight: true
not_target_position: true
not_quantity: true
---

# PBA3 Supervised / Bandit Active Policy 工作文档

## 1. 本轮目标

你是执行者。请继续 PBA Baseline-anchored Active Policy 主线的第四步：

```text
PBA3: Supervised / Bandit Active Policy
```

本轮目标是在 PBA2 已证明 active overlay action space 有 validation 改善信号后，训练一个小模型学习 baseline active overlay，而不是完整组合。

本轮不允许 strict_test，不允许生产或订单输出。

## 2. 必须读取

执行前必须读取：

```text
docs/tw_portfolio_decision_model/POLICY_PBA_BASELINE_ANCHORED_ACTIVE_POLICY_MAINLINE_CN.md
docs/tw_portfolio_decision_model/POLICY_PBA2_RULE_CALIBRATED_ACTIVE_OVERLAY_SANITY_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_PBA2_RULE_CALIBRATED_ACTIVE_OVERLAY_SANITY_EXECUTION_REPORT_CN.md
docs/tw_portfolio_decision_model/POLICY_PBA1_BASELINE_SNAPSHOT_BUILD_AND_PARITY_REPLAY_REVIEW_CN.md
```

必须使用：

```text
data_tw/experiments/baseline_anchored_active_policy/pba1_baseline_snapshot_parity_replay/
data_tw/experiments/baseline_anchored_active_policy/pba2_rule_calibrated_active_overlay_sanity/
```

## 3. 授权范围

本轮允许候选：

```text
1. supervised utility model
2. contextual bandit with conservative offline evaluation
3. shallow MLP / LightGBM active policy
```

但第一轮 PBA3 必须保持小模型、baseline-anchored、小动作空间，不得扩展为 free allocation。

允许 action 仅限 PBA0/PBA2 已定义的 active overlay diagnostic actions：

```text
allow_baseline_buy
block_baseline_buy
allow_baseline_sell
delay_baseline_sell
no_extra_action
require_score_gap
require_score_zscore
market_risk_reduce_participation_diagnostic
overweight_top_ranked_diagnostic, diagnostic only
underweight_low_edge_candidate_diagnostic, diagnostic only
cap_low_score_holding_diagnostic, diagnostic only
```

## 4. 禁止事项

本轮禁止：

```text
1. 运行或读取 strict_test。
2. 进入 PBA4 / PBA5 / PBA6。
3. 输出 OrderIntent。
4. 输出 target_weight / target_position / quantity / broker_order。
5. provider publish / accepted latest switch。
6. monitor write / frontend default / Agent recommendation。
7. broker / quick-trade / real order。
8. 修改 production/default 策略。
9. free allocation vector。
10. 使用 future_return / label / realized_pnl / future price 作为 feature。
11. 使用 validation 或 strict_test 反复调参。
12. 用 cash-only / no-trade 作为成功。
13. 只复刻 PBA2 selected rule 而不做稳定性和 OOD audit。
```

## 5. 数据窗口

必须保持：

```text
train = 2023-01-01..2024-12-31
validation = 2025-01-01..2025-12-31
strict_test = 2026-01-01..2026-05-07, declared only, not used
```

训练只允许使用 train window。validation 只能做一次 final selection / comparison。

## 6. 必须输出产物

artifact root：

```text
data_tw/experiments/baseline_anchored_active_policy/pba3_supervised_bandit_active_policy/
```

必须输出：

```text
manifest.json
model_candidate_manifest.json
training_dataset_schema.json
training_dataset_audit.csv
action_space_coverage_audit.csv
behavior_policy_coverage_audit.csv
ood_action_audit.csv
model_train_metrics.csv
validation_replay_metrics_by_model.csv
validation_selection_audit.csv
fold_stability_audit.csv
seed_stability_audit.csv
participation_gate_audit.csv
cash_dominance_gate_audit.csv
risk_asset_exposure_audit.csv
cost_turnover_audit.csv
baseline_clone_audit.csv
pnl_concentration_audit.csv
feature_available_at_audit.csv
forbidden_feature_and_consumer_audit.csv
validator_report.json
golden_samples_report.json
```

必须写执行报告：

```text
docs/tw_portfolio_decision_model/POLICY_PBA3_SUPERVISED_BANDIT_ACTIVE_POLICY_EXECUTION_REPORT_CN.md
```

## 7. 训练数据与防泄漏要求

`training_dataset_schema.json` 和 `training_dataset_audit.csv` 必须说明：

```text
state features
allowed action set
reward / utility construction
label_or_utility_available_window
cost model
baseline action anchor
PIT / available_at status
forbidden feature check
```

允许在 train window 内用 readonly replay 构造 action utility，但必须禁止：

```text
future_return as feature
label as feature
realized_pnl as feature
future price
same-day unavailable data
validation metric inside training loop
strict_test metrics
oracle action as direct label
```

## 8. 模型候选要求

`model_candidate_manifest.json` 必须预声明模型，不得无界搜索。

候选最多包括：

```text
supervised_utility_logistic_or_tree
contextual_bandit_conservative
shallow_mlp_or_lightgbm_active_policy
```

每个候选必须记录：

```text
model_id
model_type
feature_set
action_set
training_window
validation_window
hyperparameters
random_seeds
strict_test_used = false
production_allowed = false
```

## 9. OOD / Coverage 要求

必须输出：

```text
action_space_coverage_audit.csv
behavior_policy_coverage_audit.csv
ood_action_audit.csv
```

必须证明：

```text
1. 模型没有大量选择 train replay 中缺少支持的 actions。
2. contextual bandit / supervised policy 的 action 分布仍接近 baseline-supported active overlay。
3. OOD action 不得作为 validation pass 的主要来源。
```

## 10. Validation 通过条件

PBA3 只有以下全部满足时，才可建议审查者考虑 PBA3 validation pass：

```text
1. validation net_return_after_fee_tax > PBA1 baseline validation net_return_after_fee_tax。
2. validation net_return_after_fee_tax >= PBA2 selected rule 或清楚说明为何略低但稳定性更强。
3. fold stability pass。
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

如果 validation 不超过 baseline，必须：

```text
STOP_NO_STRICT_TEST_REQUEST
```

不得进入 PBA5。

## 11. Validator / Golden Samples

`validator_report.json` 必须检查：

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

`golden_samples_report.json` 必须包含：

```text
positive: baseline-anchored supervised utility sample accepted.
positive: conservative contextual bandit action accepted.
positive: readonly model replay accepted.
negative: target_weight field must fail.
negative: target_position field must fail.
negative: quantity / broker_order must fail.
negative: OrderIntentArtifact consumer must fail.
negative: strict_test metrics access must fail.
negative: future_return feature must fail.
negative: unpredeclared model candidate must fail.
negative: OOD unsupported action pass claim must fail.
negative: cash-only / no-trade pass claim must fail.
negative: PBA5 request without PBA3 validation pass must fail.
```

## 12. 执行报告要求

执行报告必须包括：

```text
1. Scope：说明只做 PBA3 supervised / bandit active policy。
2. Documents read。
3. Model candidates and datasets。
4. Feature/PIT/forbidden feature audit。
5. Training metrics。
6. Validation replay metrics and selection。
7. Fold / seed stability。
8. Participation / cash dominance / risk exposure gates。
9. OOD action / behavior coverage audit。
10. Cost / turnover / baseline clone / pnl concentration audit。
11. Forbidden consumer audit。
12. Issues / blockers / deviations。
13. Recommendation：只能是 PASS_READY_FOR_REVIEWER_TO_CONSIDER_PBA3_VALIDATION_PASS 或 STOP_NO_STRICT_TEST_REQUEST。
```

如果 PBA3 未通过，执行者不得请求 strict_test 或 PBA5。
