---
created_at: 2026-06-21T18:21:39+00:00
status: executed_action_value_ranker_repair
phase: PAV2_ACTION_VALUE_RANKER_REPAIR
mainline_doc: docs/tw_portfolio_decision_model/POLICY_PA3_COUNTERFACTUAL_ACTION_SPACE_MAINLINE_CN.md
work_document: docs/tw_portfolio_decision_model/POLICY_PAV2_ACTION_VALUE_RANKER_REVIEW_CN.md
artifact_root: data_tw/experiments/policy_action_model_research/pav2_action_value_ranker_repair
recommendation: STOP_DO_NOT_CONTINUE
readonly_only: true
simulation_only: true
not_order: true
not_target_position: true
not_investment_advice: true
production_allowed: false
no_pav3: true
no_offline_rl: true
---

# PAV2 Action Value Ranker Repair 执行报告

## 1. Scope

本轮严格执行 `PAV2_ACTION_VALUE_RANKER_REPAIR`，这是 PAV2 内部修复，不是 PAV3。输入仍只使用 PAV1 manifest，未新增 PAV1 topK/cap config，未进入 offline RL / constrained slate policy，未触发 provider/latest/monitor/broker/frontend default/Agent/OpenAI。

## 2. Documents / Contracts / Skills Read

已读取 PA3 counterfactual action space 主线、PAV1 review、PAV2 execution report、PAV2 review/repair work doc、项目宪法、开发手册、ModelSignal / StrategyRule / OrderIntent / ReplayResult 合同，以及 coordinator / new-model / new-strategy / safety-boundary skills 和 forbidden-actions reference。

## 3. Failure Root Cause From Initial PAV2

首轮 PAV2 的模型合同和只读产物通过，但 strict_test return-first 失败：policy=0.46828264，baseline=1.14173800，excess=-0.67345536。失败机制是 selected action 与 rolling portfolio execution feasibility 脱节，导致低参与和高 skip。

## 4. Repair Controls Implemented

本轮实现了：

```text
1. execution-feasibility filter：按 rolling policy portfolio 判断 buy_one / sell_one / switch_pair / keep_baseline_action 是否可执行。
2. keep_baseline fallback / margin gate：不可执行或模型分数相对 keep_baseline margin 不足时回退 baseline；无 baseline 时 no_action。
3. participation guardrail：validation 上审计 action_count、turnover、skip_ratio。
4. validation replay-aware selection：用 validation readonly replay return-first 选择最终 model/config/margin。
5. strict_test final-only：strict_test 不参与任何模型、阈值、margin、topK/cap 或 fallback policy 选择。
```

## 5. Validation-only Selection And Guardrails

最终 validation-only 选择：

```text
candidate_topk=50
action_cap=200
model_family=ridge
target_label=label_relative_return_vs_baseline
margin_threshold=999.0
selected_by=validation_replay_aware_guardrail
```

选择证据：

```text
data_tw/experiments/policy_action_model_research/pav2_action_value_ranker_repair/validation_selection_audit.csv
data_tw/experiments/policy_action_model_research/pav2_action_value_ranker_repair/evaluation/validation_replay_selection_audit.csv
```

## 6. ActionValueModelArtifact

已输出 `manifest.json`、`model_config.json`、`feature_schema.json`、`training_metrics.csv`、`validation_selection_audit.csv`、`forbidden_feature_audit.csv`、`action_value_predictions.csv`。模型输入仍仅限 PAV1 schema 允许的 `state_feature_*`、`action_feature_*`、`action_type` one-hot。

## 7. ActionSlateDecisionArtifact

已输出 `action_slate_decisions.csv` 和 `action_slate_decision_schema.json`。ActionSlateDecision 不包含 quantity、target_weight、target_position、execution_price、execution_date、broker/order/quick_trade 字段。

## 8. Execution-feasibility / Participation / Keep-baseline Audits

已输出：

```text
evaluation/execution_feasibility_audit.csv
evaluation/participation_guardrail_audit.csv
evaluation/keep_baseline_fallback_audit.csv
```

## 9. OrderIntentArtifact

已输出 baseline 与 policy 的 readonly OrderIntentArtifact。adapter 只输出 buy/sell/skip intent，不计算数量、成交价、现金、仓位、broker/order 字段。

## 10. Readonly ReplayResultArtifact

已输出 baseline 与 policy replay：

```text
data_tw/experiments/policy_action_model_research/pav2_action_value_ranker_repair/replay_result/
```

ReplayResult 中的 quantity、execution_price、cash、NAV 属于历史模拟输出，不进入 ActionSlateDecision 或 OrderIntent。

## 11. Return-first Evaluation

validation：

```text
baseline=0.95376753
policy=0.84549802
excess=-0.10826951
```

strict_test final-only：

```text
baseline=1.141738
policy=0.90317488
excess=-0.23856312
```

完整文件：

```text
evaluation/baseline_comparison.csv
evaluation/return_first_metrics.csv
```

## 12. Strict Test Final-only Audit

`validation_selection_audit.csv` 和 `policy_input_audit.csv` 均记录 `strict_test_used_for_selection=false`。strict_test 只在最终 selected policy 上评估一次。

## 13. Validator And Golden Samples

Validator：

```text
status=PASS_PAV2_ACTION_VALUE_RANKER_VALIDATION
failed_count=0
```

Golden samples：

```text
status=PASS_PAV2_GOLDEN_SAMPLES
failed_count=0
```

## 14. Forbidden Actions Audit

本轮未触发 provider publish、accepted latest switch、monitor write/scan/alerts、broker、quick-trade、real order、frontend default 或 Agent/OpenAI。ActionSlateDecision 和 OrderIntent 均不包含 target_position / target_weight / quantity / execution_price / broker order 字段。

## 15. Issues / Stop Conditions

若 strict_test excess 仍显著为负，按 repair work doc 必须 `STOP_DO_NOT_CONTINUE`，不得进入 PAV3，也不得继续无界调参。本轮结论见 recommendation。

## 16. Files Changed

```text
scripts/run_tw_policy_pav2_action_value_ranker.py
docs/tw_portfolio_decision_model/POLICY_PAV2_ACTION_VALUE_RANKER_REPAIR_EXECUTION_REPORT_CN.md
data_tw/experiments/policy_action_model_research/pav2_action_value_ranker_repair/
```

## 17. Recommendation For Reviewer

```text
STOP_DO_NOT_CONTINUE
```
