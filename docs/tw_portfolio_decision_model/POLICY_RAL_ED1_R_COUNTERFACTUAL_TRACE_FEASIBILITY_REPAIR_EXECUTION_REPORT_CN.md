---
created_at: 2026-06-23
status: executed_ral_ed1_r_counterfactual_trace_feasibility_repair
phase: RAL_ED1_R_COUNTERFACTUAL_TRACE_FEASIBILITY_REPAIR
mainline_doc: docs/tw_portfolio_decision_model/POLICY_RAL_ED_EXPLICIT_RULE_DISCOVERY_MAINLINE_CN.md
work_doc: docs/tw_portfolio_decision_model/POLICY_RAL_ED1_R_COUNTERFACTUAL_TRACE_FEASIBILITY_REPAIR_WORK_CN.md
artifact_root: data_tw/experiments/explicit_rule_discovery/ral_ed1_r_counterfactual_trace_repair
final_recommendation: READY_FOR_REVIEWER_TO_AUDIT_TRACE_FEASIBILITY
ral_ed2_authorized: false
rule_replay_run: false
rule_selection_run: false
strict_test_used: false
model_training_run: false
production_allowed: false
readonly_only: true
simulation_only: true
---

# RAL-ED1-R Counterfactual Trace Feasibility Repair 执行报告

## 1. Scope

本轮只做 counterfactual trace feasibility repair，不执行 ED2、不做规则收益排名、不选择阈值、不使用 strict_test。

## 2. Documents / Contracts / Skills Read

```text
coordinator-executor-reviewer-workflow
docs/tw_portfolio_decision_model/POLICY_RAL_ED_EXPLICIT_RULE_DISCOVERY_MAINLINE_CN.md
docs/tw_portfolio_decision_model/POLICY_RAL_ED1_COORDINATOR_OPINION_FOR_REVIEWER_CN.md
docs/tw_portfolio_decision_model/POLICY_RAL_ED1_SCORE_RANK_REGIME_HOLDING_ATTRIBUTION_DIAGNOSTIC_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_RAL_ED1_SCORE_RANK_REGIME_HOLDING_ATTRIBUTION_DIAGNOSTIC_EXECUTION_REPORT_CN.md
docs/tw_portfolio_decision_model/POLICY_RAL_ED1_R_COUNTERFACTUAL_TRACE_FEASIBILITY_REPAIR_WORK_CN.md
data_tw/experiments/explicit_rule_discovery/ral_ed0_contract_design/*
data_tw/experiments/explicit_rule_discovery/ral_ed1_attribution_diagnostic/*
docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md
docs/tw_modular_contracts/MODEL_SIGNAL_CONTRACT_CN.md
docs/tw_modular_contracts/STRATEGY_RULE_CONTRACT_CN.md
docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md
docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md
```

## 3. Changes Made

新增只读 repair 脚本：

```text
scripts/build_tw_policy_ral_ed1_r_counterfactual_trace_repair.py
```

新增 artifact root：

```text
data_tw/experiments/explicit_rule_discovery/ral_ed1_r_counterfactual_trace_repair/
```

## 4. Evidence Produced

必需文件均已输出：

```text
manifest.json
counterfactual_trace_feasibility_design.md
intervention_probe_manifest.json
required_replay_state_field_audit.csv
counterfactual_trace_sample.csv
baseline_vs_intervention_delta_sample.csv
trace_status_upgrade_audit.csv
replay_determinism_audit.csv
cost_turnover_delta_audit.csv
multi_trade_gate_feasibility_audit.csv
unavailable_field_blocker_audit.csv
forbidden_consumer_audit.csv
validator_report.json
golden_samples_report.json
```

## 5. Trace Feasibility Result

```text
counterfactual_replay_trace_rows = 120
feasible_probe = block_buy_trace_probe_v1
construction_method = deterministic local single-action buy suppression from repaired baseline ledger
trace_quality = local action delta only, not full portfolio path
```

`delay_sell_trace_probe_v1`、`accelerated_sell_trace_probe_v1`、`threshold_multi_buy_trace_probe_v1` 均因缺少 post-intervention state path、pre-decision cash 或 multi-action allocation/gate path 被 blocker audit 阻断。

## 6. Validator

`validator_report.json`：

```text
ok = true
status = PASS_RAL_ED1_R_TRACE_FEASIBILITY_REPAIR_READY_FOR_REVIEW
strict_test_used = false
model_training_run = false
rule_replay_run = false
rule_selection_run = false
order_intent_output = false
target_weight_output = false
target_position_output = false
quantity_or_broker_output = false
```

## 7. Forbidden Actions Audit

未执行：

```text
model_training
rule_return_replay
rule_selection
strict_test
OrderIntent output
target_weight / target_position / quantity / broker_order
provider/latest/monitor/frontend/Agent/broker/production
```

## 8. Issues / Limitations

`block_buy_trace_probe_v1` 只证明当前 baseline buy row 可构造 deterministic local action-level counterfactual delta。它不是完整 portfolio path replay，不是 rule candidate，不得直接进入 ED2。

后续如要继续，应由统筹决定是否授权：

```text
RAL-ED1-S: score/rank/regime attribution rerun with counterfactual traces
```

或定义更完整的 diagnostic-only counterfactual replay state contract。

## 9. Files Changed

```text
scripts/build_tw_policy_ral_ed1_r_counterfactual_trace_repair.py
docs/tw_portfolio_decision_model/POLICY_RAL_ED1_R_COUNTERFACTUAL_TRACE_FEASIBILITY_REPAIR_EXECUTION_REPORT_CN.md
data_tw/experiments/explicit_rule_discovery/ral_ed1_r_counterfactual_trace_repair/
```

## 10. Recommendation For Reviewer

```text
READY_FOR_REVIEWER_TO_AUDIT_TRACE_FEASIBILITY
```

即使审查通过，也只表示 trace feasibility 可审计，不表示任何显式规则有效，不授权 ED2。
