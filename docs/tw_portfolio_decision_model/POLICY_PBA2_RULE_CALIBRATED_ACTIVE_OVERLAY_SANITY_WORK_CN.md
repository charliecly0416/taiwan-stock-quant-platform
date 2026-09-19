---
created_at: 2026-06-22
status: reviewer_next_work_document
phase: PBA2_RULE_CALIBRATED_ACTIVE_OVERLAY_SANITY
mainline_doc: docs/tw_portfolio_decision_model/POLICY_PBA_BASELINE_ANCHORED_ACTIVE_POLICY_MAINLINE_CN.md
previous_review: docs/tw_portfolio_decision_model/POLICY_PBA1_BASELINE_SNAPSHOT_BUILD_AND_PARITY_REPLAY_REVIEW_CN.md
previous_execution_report: docs/tw_portfolio_decision_model/POLICY_PBA1_BASELINE_SNAPSHOT_BUILD_AND_PARITY_REPLAY_EXECUTION_REPORT_CN.md
pba1_artifact_root: data_tw/experiments/baseline_anchored_active_policy/pba1_baseline_snapshot_parity_replay
artifact_root: data_tw/experiments/baseline_anchored_active_policy/pba2_rule_calibrated_active_overlay_sanity
strict_test_authorized: false
training_authorized: false
production_allowed: false
readonly_only: true
simulation_only: true
not_order: true
not_target_weight: true
not_target_position: true
not_quantity: true
---

# PBA2 Rule-calibrated Active Overlay Sanity 工作文档

## 1. 本轮目标

你是执行者。请继续 PBA Baseline-anchored Active Policy 主线的第三步：

```text
PBA2: Rule-calibrated Active Overlay Sanity
```

本轮目标是先用少量可解释、预声明的 active overlay rule 验证 PBA action space 是否有提升空间。

本轮不是 PBA3，不训练模型；不是 PBA5，不运行 strict_test。

## 2. 必须读取

执行前必须读取：

```text
docs/tw_portfolio_decision_model/POLICY_PBA_BASELINE_ANCHORED_ACTIVE_POLICY_MAINLINE_CN.md
docs/tw_portfolio_decision_model/POLICY_PBA1_BASELINE_SNAPSHOT_BUILD_AND_PARITY_REPLAY_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_PBA1_BASELINE_SNAPSHOT_BUILD_AND_PARITY_REPLAY_EXECUTION_REPORT_CN.md
docs/tw_portfolio_decision_model/POLICY_PBA0_CONTRACT_BASELINE_AUDIT_REVIEW_CN.md
```

必须使用 PBA1 产物：

```text
data_tw/experiments/baseline_anchored_active_policy/pba1_baseline_snapshot_parity_replay/
```

## 3. 授权范围

本轮只允许预声明的 rule-calibrated active overlay sanity，不允许训练模型。

允许规则仅限：

```text
score_gap_buy_filter
score_zscore_buy_filter
holding_age_sell_delay
trend_confirmed_hold
market_risk_exposure_reduce
top_rank_active_tilt_diagnostic
```

每个规则必须：

```text
1. 以 baseline_action_snapshot_artifact 为锚点。
2. 只输出 ActivePolicyDecisionArtifact 风格 diagnostic decisions。
3. 使用 PBA1 baseline parity replay 口径做 readonly replay。
4. 与 PBA1 baseline 比较 net_return_after_fee_tax。
5. 检查 participation / risk exposure / cash dominance gates。
```

## 4. 禁止事项

本轮禁止：

```text
1. 训练模型。
2. 运行或读取 strict_test。
3. 进入 PBA3 / PBA4 / PBA5。
4. 根据 validation 反复调参。
5. 使用 gross return、低 turnover、低 cost、低 drawdown 替代 net_return_after_fee_tax。
6. 用 cash-only / no-trade 作为成功。
7. 输出 OrderIntent。
8. 输出 target_weight / target_position / quantity / broker_order。
9. provider publish / accepted latest switch。
10. monitor write / frontend default / Agent recommendation。
11. broker / quick-trade / real order。
12. 修改 production/default 策略。
13. free allocation vector。
```

## 5. 数据窗口与选择规则

窗口：

```text
train = 2023-01-01..2024-12-31
validation = 2025-01-01..2025-12-31
strict_test = 2026-01-01..2026-05-07, declared only, not used
```

规则：

```text
1. 所有 active overlay rules 和参数必须在 rule_config_manifest.json 中预声明。
2. train 可用于规则校准和 sanity replay。
3. validation 只能做一次 final selection / comparison。
4. primary metric = validation net_return_after_fee_tax。
5. 通过条件必须相对 PBA1 baseline validation after-fee-tax return。
6. 不得基于 strict_test 选择或调整规则。
```

## 6. 必须输出产物

artifact root：

```text
data_tw/experiments/baseline_anchored_active_policy/pba2_rule_calibrated_active_overlay_sanity/
```

必须输出：

```text
manifest.json
rule_config_manifest.json
active_policy_decision_artifact.csv
active_overlay_replay_ledger.csv
rule_replay_metrics_by_split.csv
validation_selection_audit.csv
participation_gate_audit.csv
cash_dominance_gate_audit.csv
risk_asset_exposure_audit.csv
baseline_clone_audit.csv
cost_turnover_audit.csv
feature_available_at_audit.csv
forbidden_feature_and_consumer_audit.csv
validator_report.json
golden_samples_report.json
```

必须写执行报告：

```text
docs/tw_portfolio_decision_model/POLICY_PBA2_RULE_CALIBRATED_ACTIVE_OVERLAY_SANITY_EXECUTION_REPORT_CN.md
```

## 7. Rule Config 要求

`rule_config_manifest.json` 必须为每个规则记录：

```text
rule_id
rule_name
layer
allowed_active_decision_types
parameters
parameter_source
train_calibration_allowed
validation_selection_allowed_once
uses_strict_test
simulation_only
readonly_research_only
production_allowed
```

`uses_strict_test` 必须为 false。

## 8. ActivePolicyDecisionArtifact 要求

`active_policy_decision_artifact.csv` 必须遵守 PBA0 schema，至少包含：

```text
date
instrument
split
rule_id
baseline_action_type
active_decision_type
active_decision_score
active_decision_reason_code
active_overlay_delta_diagnostic
participation_flag_diagnostic
risk_asset_exposure_flag_diagnostic
source_policy_id
source_baseline_snapshot_artifact
simulation_only
readonly_research_only
production_allowed
```

禁止字段：

```text
target_weight
target_position
quantity
order_size
broker_order
```

## 9. Replay / Metrics 要求

`rule_replay_metrics_by_split.csv` 必须至少包含：

```text
rule_id
split
baseline_net_return_after_fee_tax
active_overlay_net_return_after_fee_tax
baseline_excess_return_after_fee_tax
gross_return
turnover
fee
sell_tax
cost_drag
drawdown
participation_rate
risk_asset_exposure
cash_dominance_rate
action_concentration
pnl_concentration
status
```

`validation_selection_audit.csv` 必须记录：

```text
selected_rule_id
selection_metric
validation_baseline_net_return_after_fee_tax
selected_validation_net_return_after_fee_tax
selected_excess_return_after_fee_tax
participation_gates_pass
cash_dominance_gates_pass
risk_asset_exposure_pass
cost_turnover_not_pathological
not_baseline_clone
strict_test_used
validation_pass
recommendation
```

## 10. PBA2 通过条件

PBA2 只有以下全部满足时，才可建议审查者考虑 PBA2 validation pass：

```text
1. validation net_return_after_fee_tax > PBA1 baseline validation net_return_after_fee_tax。
2. participation gates pass。
3. cash dominance gates pass。
4. risk asset exposure gates pass。
5. cost / turnover not pathological。
6. not baseline clone。
7. strict_test_used = false。
8. forbidden consumer / OrderIntent / target_weight / target_position / quantity audit pass。
```

如果 validation 不超过 baseline，必须：

```text
STOP_NO_STRICT_TEST_REQUEST
```

不得进入 PBA3 / PBA5。

## 11. Validator / Golden Samples

`validator_report.json` 必须检查：

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

`golden_samples_report.json` 必须包含：

```text
positive: score_gap_buy_filter diagnostic decision accepted.
positive: holding_age_sell_delay diagnostic decision accepted.
positive: readonly active overlay replay accepted.
negative: unpredeclared rule must fail.
negative: target_weight field must fail.
negative: target_position field must fail.
negative: quantity / broker_order must fail.
negative: OrderIntentArtifact consumer must fail.
negative: strict_test metrics access must fail.
negative: cash-only / no-trade pass claim must fail.
negative: validation pass based on gross return must fail.
negative: PBA3 request without PBA2 validation pass must fail.
```

## 12. 执行报告要求

执行报告必须包括：

```text
1. Scope：说明只做 PBA2 rule-calibrated active overlay sanity。
2. Documents read。
3. Rules run：列出所有预声明规则和参数。
4. Replay metrics：train / validation 与 baseline 对照。
5. Validation selection：说明是否超过 PBA1 baseline。
6. Participation / cash dominance / risk exposure gate summary。
7. Cost / turnover / baseline clone summary。
8. PIT / forbidden feature / forbidden consumer audit。
9. Issues / blockers / deviations。
10. Recommendation：只能是 PASS_READY_FOR_REVIEWER_TO_CONSIDER_PBA2_VALIDATION_PASS 或 STOP_NO_STRICT_TEST_REQUEST。
```

如果 PBA2 未通过，执行者不得请求 strict_test 或 PBA3。
