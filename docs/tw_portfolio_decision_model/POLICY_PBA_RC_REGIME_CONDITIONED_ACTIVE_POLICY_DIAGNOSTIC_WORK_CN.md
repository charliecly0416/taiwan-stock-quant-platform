---
created_at: 2026-06-22
status: reviewer_next_work_document
phase: PBA_RC_REGIME_CONDITIONED_ACTIVE_POLICY_DIAGNOSTIC
mainline_doc: docs/tw_portfolio_decision_model/POLICY_PBA_BASELINE_ANCHORED_ACTIVE_POLICY_MAINLINE_CN.md
coordinator_opinion: docs/tw_portfolio_decision_model/POLICY_PBA3_R_COORDINATOR_OPINION_FOR_REVIEWER_CN.md
previous_pba3_review: docs/tw_portfolio_decision_model/POLICY_PBA3_SUPERVISED_BANDIT_ACTIVE_POLICY_REVIEW_CN.md
previous_pba3_r_review: docs/tw_portfolio_decision_model/POLICY_PBA3_R_FOLD_STABILITY_CONSTRAINED_REPAIR_REVIEW_CN.md
pba2_artifact_root: data_tw/experiments/baseline_anchored_active_policy/pba2_rule_calibrated_active_overlay_sanity
pba3_artifact_root: data_tw/experiments/baseline_anchored_active_policy/pba3_supervised_bandit_active_policy
pba3_r_artifact_root: data_tw/experiments/baseline_anchored_active_policy/pba3_r_fold_stability_repair
artifact_root: data_tw/experiments/baseline_anchored_active_policy/pba_rc_regime_conditioned_diagnostic
strict_test_authorized: false
pba5_authorized: false
pba4_offline_rl_authorized: false
qlib_ltr_authorized: false
training_authorized: false
production_allowed: false
readonly_only: true
simulation_only: true
not_order: true
not_target_weight: true
not_target_position: true
not_quantity: true
---

# PBA-RC Regime-conditioned Active Policy Diagnostic 工作文档

## 1. 本轮目标

你是执行者。请继续 PBA Baseline-anchored Active Policy 主线，但本轮不是继续 PBA3/PBA3-R 模型修复。

本轮只执行：

```text
PBA_RC_REGIME_CONDITIONED_ACTIVE_POLICY_DIAGNOSTIC
```

目标是诊断 PBA2 / PBA3 / PBA3-R 的 active overlay 收益是否只存在于特定：

```text
market regime
volatility regime
score dispersion regime
baseline state
action context
```

本轮只做诊断和合同设计，不训练新模型，不运行 strict_test，不进入 PBA4/PBA5，不接生产。

## 2. 必须读取

执行前必须读取：

```text
docs/tw_portfolio_decision_model/POLICY_PBA_BASELINE_ANCHORED_ACTIVE_POLICY_MAINLINE_CN.md
docs/tw_portfolio_decision_model/POLICY_PBA3_SUPERVISED_BANDIT_ACTIVE_POLICY_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_PBA3_R_FOLD_STABILITY_CONSTRAINED_REPAIR_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_PBA3_R_COORDINATOR_OPINION_FOR_REVIEWER_CN.md
```

必须使用既有产物：

```text
data_tw/experiments/baseline_anchored_active_policy/pba1_baseline_snapshot_parity_replay/
data_tw/experiments/baseline_anchored_active_policy/pba2_rule_calibrated_active_overlay_sanity/
data_tw/experiments/baseline_anchored_active_policy/pba3_supervised_bandit_active_policy/
data_tw/experiments/baseline_anchored_active_policy/pba3_r_fold_stability_repair/
```

## 3. 本轮必须回答的问题

执行者必须至少回答：

```text
1. PBA2 selected rule 在哪些 regime 赢 baseline，哪些 regime 输 baseline？
2. PBA3 selected model 在哪些 regime 赢 baseline，哪些 regime 输 baseline？
3. PBA3-R contextual bandit 在 risk_off 为什么失败？
4. active overlay 的收益是否主要来自 normal regime？
5. score dispersion 高/低时，active overlay 是否效果不同？
6. baseline 自身强/弱时，active overlay 是否效果不同？
7. 当前持仓年龄、趋势、波动状态是否影响 delay_sell / block_buy 的收益？
8. 是否存在一个简单的 regime gate：
   normal/caution 启用 active overlay；
   risk_off 退回 baseline 或只允许保守规则。
```

## 4. Regime 切分要求

PBA-RC 诊断至少覆盖：

```text
market_regime:
  normal
  caution
  risk_off

volatility_regime:
  low_vol
  mid_vol
  high_vol

score_dispersion_regime:
  low_dispersion
  mid_dispersion
  high_dispersion

baseline_state:
  baseline_recent_strong
  baseline_recent_weak
  baseline_drawdown

action_context:
  buy_filter
  sell_delay
  no_extra_action
  top_rank_tilt_diagnostic
```

所有 regime 定义必须 PIT-safe，不得用 future return、strict_test、validation 结果倒推阈值。

## 5. 禁止事项

本轮禁止：

```text
1. 训练新模型。
2. 运行或读取 strict_test。
3. 进入 PBA5。
4. 启动 PBA4 offline RL。
5. 扩展到 qlib+LTR。
6. 无界调参。
7. 新增 free allocation vector。
8. 新增 target_weight / target_position / quantity。
9. 输出 OrderIntent。
10. broker / quick-trade / real order。
11. provider publish / accepted latest switch。
12. monitor write。
13. frontend default。
14. Agent recommendation。
15. production/default 策略切换。
```

## 6. 输出产物

artifact root：

```text
data_tw/experiments/baseline_anchored_active_policy/pba_rc_regime_conditioned_diagnostic/
```

必须输出：

```text
manifest.json
regime_definition_manifest.json
pba2_regime_replay_metrics.csv
pba3_regime_replay_metrics.csv
pba3_r_regime_replay_metrics.csv
regime_excess_return_summary.csv
regime_failure_attribution.csv
regime_gate_candidate_audit.csv
active_decision_change_rate_by_regime.csv
participation_gate_by_regime.csv
cash_dominance_gate_by_regime.csv
risk_asset_exposure_by_regime.csv
cost_turnover_by_regime.csv
baseline_clone_by_regime.csv
feature_available_at_audit.csv
forbidden_feature_and_consumer_audit.csv
validator_report.json
golden_samples_report.json
```

必须写执行报告：

```text
docs/tw_portfolio_decision_model/POLICY_PBA_RC_REGIME_CONDITIONED_ACTIVE_POLICY_DIAGNOSTIC_EXECUTION_REPORT_CN.md
```

## 7. Regime Definition 要求

`regime_definition_manifest.json` 必须说明：

```text
regime_name
regime_family
definition
input_fields
available_at_rule
threshold_source
uses_future_return
uses_validation_metric
uses_strict_test
pit_safe
```

其中：

```text
uses_future_return = false
uses_validation_metric = false
uses_strict_test = false
pit_safe = true
```

## 8. Metrics 要求

`pba2_regime_replay_metrics.csv`、`pba3_regime_replay_metrics.csv`、`pba3_r_regime_replay_metrics.csv` 必须至少包含：

```text
source_stage
policy_or_rule_id
regime_family
regime_name
action_context
date_count
baseline_net_return_after_fee_tax
active_overlay_net_return_after_fee_tax
excess_return_after_fee_tax
turnover
cost_drag
participation_rate
risk_asset_exposure
cash_dominance_rate
active_decision_change_rate
baseline_clone_flag
status
```

`regime_excess_return_summary.csv` 必须回答：

```text
哪些 regime 正 excess
哪些 regime 负 excess
正 excess 是否跨 PBA2/PBA3/PBA3-R 一致
负 excess 是否集中在 risk_off / high_vol / low_dispersion 等状态
```

`regime_failure_attribution.csv` 必须说明：

```text
failure_regime
failure_source_stage
failure_policy_or_rule
likely_failure_reason
evidence_metric
recommended_handling
```

## 9. Regime Gate Candidate 要求

`regime_gate_candidate_audit.csv` 必须评估简单 gate，例如：

```text
normal/caution 启用 active overlay
risk_off 退回 baseline
high_vol 只允许 conservative overlay
low_score_dispersion 退回 baseline
baseline_drawdown 时限制 block_buy 或 sell_delay
```

必须报告：

```text
gate_id
gate_rule
covered_regimes
baseline_net_return_after_fee_tax
gated_overlay_net_return_after_fee_tax
excess_return_after_fee_tax
participation_rate
risk_asset_exposure
cash_dominance_rate
active_decision_change_rate
baseline_clone_flag
status
```

注意：本轮只是 gate candidate audit，不得训练新模型，不得声称进入 PBA5。

## 10. 可进入下一步的条件

PBA-RC 诊断不以“策略通过”为目标，而以“是否值得开 PBA-RC 模型子线”为目标。

可建议统筹考虑 PBA-RC 模型工作文档的条件：

```text
1. 至少一个预定义 regime 中，PBA2/PBA3/PBA3-R active overlay 对 baseline 有一致正 excess。
2. risk_off 或失败 regime 的损害来源可解释。
3. 简单 regime gate 能降低负 regime 伤害，同时不把策略退化成 baseline clone。
4. participation / risk exposure / cash dominance 仍不过度退化。
5. active decision change rate 高于最低阈值。
6. 所有分析不使用 strict_test，不使用 future feature，不用 validation 反复调参。
```

如果诊断结果显示：

```text
没有任何 regime 存在稳定 active edge；
或启用 regime gate 后只是 baseline clone；
```

必须回到统筹。

## 11. Validator / Golden Samples

`validator_report.json` 必须检查：

```text
pba1_artifact_loaded
pba2_artifact_loaded
pba3_artifact_loaded
pba3_r_artifact_loaded
regime_definition_manifest_exists
regime_metrics_exist
strict_test_not_used
no_training_run
no_pba5_request
no_pba4_offline_rl
no_qlib_ltr
no_order_intent_output
no_target_weight
no_target_position
no_quantity
no_broker_order
no_provider_monitor_frontend_agent_production
feature_available_at_audit_pass
forbidden_feature_and_consumer_audit_pass
```

`golden_samples_report.json` 必须包含：

```text
positive: PIT-safe regime definition accepted.
positive: regime replay metrics accepted.
positive: regime gate candidate audit accepted.
negative: strict_test metrics access must fail.
negative: training new model must fail.
negative: PBA5 request must fail.
negative: PBA4 offline RL request must fail.
negative: qlib+LTR adapter request must fail.
negative: target_weight field must fail.
negative: target_position field must fail.
negative: quantity / broker_order must fail.
negative: OrderIntentArtifact consumer must fail.
negative: future_return regime definition must fail.
negative: validation-derived threshold must fail.
negative: baseline-clone regime gate pass claim must fail.
```

## 12. 执行报告要求

执行报告必须包括：

```text
1. Scope：说明只做 PBA-RC regime diagnostic，不训练新模型。
2. Documents read。
3. Regime definitions。
4. PBA2/PBA3/PBA3-R regime metrics。
5. Regime excess return summary。
6. Failure attribution。
7. Regime gate candidate audit。
8. Participation / cash dominance / risk exposure by regime。
9. Active decision change rate / baseline clone by regime。
10. PIT / forbidden feature / forbidden consumer audit。
11. Issues / blockers / deviations。
12. Recommendation：只能是 PASS_READY_FOR_REVIEWER_TO_CONSIDER_PBA_RC_MODEL_WORK 或 STOP_RETURN_TO_COORDINATOR。
```

不得请求 PBA5、strict_test、PBA4、qlib+LTR 或 production integration。
