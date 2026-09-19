---
created_at: 2026-06-23
status: executed_ral_ed1_attribution_diagnostic
phase: RAL_ED1_SCORE_RANK_REGIME_HOLDING_ATTRIBUTION_DIAGNOSTIC
mainline_doc: docs/tw_portfolio_decision_model/POLICY_RAL_ED_EXPLICIT_RULE_DISCOVERY_MAINLINE_CN.md
work_doc: docs/tw_portfolio_decision_model/POLICY_RAL_ED1_SCORE_RANK_REGIME_HOLDING_ATTRIBUTION_DIAGNOSTIC_WORK_CN.md
artifact_root: data_tw/experiments/explicit_rule_discovery/ral_ed1_attribution_diagnostic
final_recommendation: STOP_NO_RAL_ED2_READY_HYPOTHESIS
training_run: false
rule_replay_run: false
strict_test_used: false
production_allowed: false
readonly_only: true
simulation_only: true
---

# RAL-ED1 Score / Rank / Regime / Holding Attribution Diagnostic 执行报告

## 1. Scope

本轮只执行 RAL-ED1 attribution diagnostic：

```text
构建 action trace 样本
生成 trace support audit
生成 counterfactual delta attribution audit
生成 score/rank/regime/holding/cost attribution tables
生成 candidate hypothesis audit
写 diagnostic findings
写 validator report
```

本轮未执行：

```text
规则收益 replay
模型训练
strict_test
OrderIntent
target_weight / target_position / quantity / broker order
provider/latest/monitor/frontend/Agent/broker/production 扩权
```

## 2. Documents / Contracts / Skills Read

使用 skill：

```text
coordinator-executor-reviewer-workflow
```

读取：

```text
docs/tw_portfolio_decision_model/POLICY_RAL_ED_EXPLICIT_RULE_DISCOVERY_MAINLINE_CN.md
docs/tw_portfolio_decision_model/POLICY_RAL_ED0_EXPLICIT_RULE_DISCOVERY_CONTRACT_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_RAL_ED0_EXPLICIT_RULE_DISCOVERY_CONTRACT_EXECUTION_REPORT_CN.md
docs/tw_portfolio_decision_model/POLICY_RAL_ED1_SCORE_RANK_REGIME_HOLDING_ATTRIBUTION_DIAGNOSTIC_WORK_CN.md
data_tw/experiments/explicit_rule_discovery/ral_ed0_contract_design/*
docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md
docs/tw_modular_contracts/MODEL_SIGNAL_CONTRACT_CN.md
docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md
docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md
```

## 3. Changes Made

新增只读生成脚本：

```text
scripts/build_tw_policy_ral_ed1_attribution_diagnostic.py
```

新增 artifact root：

```text
data_tw/experiments/explicit_rule_discovery/ral_ed1_attribution_diagnostic/
```

未修改模型、策略、回放引擎、OrderIntent、frontend、API、registry 或生产配置。

## 4. Evidence Produced

输出文件：

```text
manifest.json
action_trace_ledger_sample.csv
trace_support_audit.csv
counterfactual_delta_attribution_audit.csv
score_bucket_return_attribution.csv
score_gap_bucket_attribution.csv
score_zscore_bucket_attribution.csv
rank_delta_attribution.csv
score_delta_attribution.csv
market_regime_action_attribution.csv
volatility_regime_action_attribution.csv
holding_age_sell_attribution.csv
entry_score_hold_attribution.csv
cost_edge_attribution.csv
candidate_rule_hypothesis_audit.csv
diagnostic_findings.md
validator_report.json
```

## 5. Diagnostic Answers

1. 现有 replay 不能原生生成 `action_trace_id`；ED1 仅为 baseline trace sample 生成 deterministic id。
2. PBA active changed rows 只能是 `derived_proxy`；PBA active overlay daily replay 只能是 `summary_level_only`。
3. score / zscore 可以 PIT-safe 分桶，但当前只是 baseline observed contribution，不是 intervention delta。
4. score gap 小的 baseline buy 可以诊断，但没有 counterfactual block-buy trace。
5. rank/score 快速下降可由历史 signal 派生，但没有 accelerated sell replay。
6. rank 下降但 score 仍强的持仓只能作为 baseline observation，不能证明 sell delay。
7. baseline source 缺 market/high-vol regime；RAL2/PBA-RC 相关证据仍是 proxy/summary。
8. holding_age 存在，可诊断卖出/持有观察，但不能建立因果 sell timing rule。
9. trade cost 可从 baseline action 观测，minimum score edge 仍是 proxy。
10. threshold-driven multi-buy/multi-sell 未被 replay，不能判断收益，只能要求未来 gates。
11. 没有候选达到 `counterfactual_replay_trace`，因此没有 RAL-ED2-ready hypothesis。

## 6. Validator

`validator_report.json`：

```text
ok = true
status = PASS_RAL_ED1_DIAGNOSTIC_ARTIFACTS_COMPLETE_STOP_NO_ED2_READY_HYPOTHESIS
strict_test_used = false
model_training_run = false
rule_replay_run = false
order_intent_output = false
target_weight_output = false
target_position_output = false
quantity_or_broker_output = false
```

## 7. Compliance With Mainline

| Requirement | Status |
|---|---|
| 所有必需输出存在 | pass |
| trace_status 审计完整 | pass |
| diagnostic features PIT-safe | pass |
| no strict_test / training / rule replay | pass |
| no OrderIntent / target/order fields | pass |
| proxy/summary 未冒充 native/counterfactual | pass |
| 至少一个 ED2-ready hypothesis | fail |

因此 ED1 诊断完成，但不得进入 ED2。

## 8. Forbidden Actions Audit

```text
model_training = not_performed
rule_return_replay = not_performed
strict_test = not_used
OrderIntent_output = not_output
target_weight = not_output
target_position = not_output
quantity = not_output
broker_order = not_output
provider_publish = not_performed
accepted_latest_switch = not_performed
monitor_write = not_performed
frontend_default_switch = not_performed
Agent_recommendation = not_performed
production_default_strategy = not_performed
```

## 9. Issues / Blockers / Deviations

无执行偏离。

阻断进入 ED2 的原因：

```text
current artifacts do not contain intervention-level counterfactual replay traces;
candidate hypotheses remain baseline observation / derived proxy / summary-level only.
```

## 10. Files Changed

新增：

```text
scripts/build_tw_policy_ral_ed1_attribution_diagnostic.py
docs/tw_portfolio_decision_model/POLICY_RAL_ED1_SCORE_RANK_REGIME_HOLDING_ATTRIBUTION_DIAGNOSTIC_EXECUTION_REPORT_CN.md
data_tw/experiments/explicit_rule_discovery/ral_ed1_attribution_diagnostic/
```

## 11. Recommendation For Reviewer

```text
STOP_NO_RAL_ED2_READY_HYPOTHESIS
```

建议审查者按 STOP 口径审查：ED1 诊断产物完整，但没有达到 RAL-ED2 的 counterfactual trace hypothesis gate。
