---
created_at: 2026-06-24T07:03:53Z
status: executed_rcpt1_pit_safe_adaptive_threshold_rule_design
phase: RCPT1_PIT_SAFE_ADAPTIVE_THRESHOLD_RULE_DESIGN
work_doc: docs/tw_portfolio_decision_model/POLICY_RCPT1_PIT_SAFE_ADAPTIVE_THRESHOLD_RULE_DESIGN_WORK_CN.md
artifact_root: data_tw/experiments/risk_control_policy_2022/rcpt1_pit_safe_adaptive_threshold_rule_design
policy_replay_performed: false
risk_control_replay_performed: false
model_training_performed: false
strict_test_performed: false
production_or_provider_change_performed: false
order_chain_touched: false
recommended_next_step: PASS_READY_FOR_RCPT2_ADAPTIVE_THRESHOLD_REPLAY_SANITY_WORK_DOC
---

# RCPT1 PIT-safe Adaptive Threshold Rule Design 执行报告

## 1. Scope

本轮只执行 RCPT1 规则设计：把 RCPT0/RCPT0-R 的阈值诊断发现转成 T2 可回放的预声明 adaptive threshold rule contract。

未执行：

```text
policy replay
risk-control replay
model training
strict_test
registry/default/provider/frontend/Agent/订单链路修改
OrderIntent/target_weight/target_position/quantity_instruction 输出
```

## 2. Documents And Inputs Read

```text
docs/tw_portfolio_decision_model/POLICY_RCPT1_PIT_SAFE_ADAPTIVE_THRESHOLD_RULE_DESIGN_WORK_CN.md
docs/tw_portfolio_decision_model/POLICY_RCPT0_R_CANDIDATE_HYPOTHESIS_CONSISTENCY_REPAIR_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_RCPT0_SCORE_RANK_REGIME_THRESHOLD_DISCOVERY_WORK_CN.md
docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md
docs/tw_modular_contracts/STRATEGY_RULE_CONTRACT_CN.md
docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md
docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md
docs/tw_modular_contracts/STRATEGY_DEPENDENCY_CONTRACT_CN.md
data_tw/experiments/risk_control_policy_2022/rcpt0_score_rank_regime_threshold_discovery/candidate_threshold_hypotheses.csv
data_tw/experiments/risk_control_policy_2022/rcpt0_score_rank_regime_threshold_discovery/pit_safe_candidate_filter.csv
data_tw/experiments/risk_control_policy_2022/rcpt0_score_rank_regime_threshold_discovery/score_04_08_vs_08plus_audit.csv
data_tw/experiments/risk_control_policy_2022/rcpt0_score_rank_regime_threshold_discovery/score_percentile_band_forward_return_by_regime.csv
data_tw/experiments/risk_control_policy_2022/rcpt0_score_rank_regime_threshold_discovery/rank_change_forward_return_surface.csv
data_tw/experiments/risk_control_policy_2022/rcpt0_score_rank_regime_threshold_discovery/score_delta_forward_return_surface.csv
data_tw/experiments/risk_control_policy_2022/rcpt0_score_rank_regime_threshold_discovery/score_rank_joint_threshold_surface.csv
data_tw/experiments/risk_control_policy_2022/rcpt0_score_rank_regime_threshold_discovery/anti_overfit_and_label_leakage_audit.csv
data_tw/experiments/risk_control_policy_2022/rcp3a_market_feature_coverage_pit_gate/market_feature_by_signal_date.csv
```

## 3. Outputs

```text
manifest.json
adaptive_threshold_rule_design_manifest.json
predeclared_adaptive_threshold_rules.csv
threshold_source_contract.csv
pit_feature_contract.csv
rule_dependency_contract.csv
candidate_from_t0_mapping.csv
small_sample_exclusion_audit.csv
anti_overfit_and_no_2022_direct_fit_audit.csv
cash_no_trade_guardrail_contract.csv
t2_replay_metric_contract.csv
diagnostic_semantics_audit.json
forbidden_action_audit.csv
validator_report.json
diagnostic_findings.md
```

输出目录：

```text
data_tw/experiments/risk_control_policy_2022/rcpt1_pit_safe_adaptive_threshold_rule_design
```

## 4. Rule Contract Summary

```text
rule_count = 5
rules = ['RCPT1_RULE_01', 'RCPT1_RULE_02', 'RCPT1_RULE_03', 'RCPT1_RULE_04', 'RCPT1_RULE_05']
H01/H08 mapped = RCPT1_RULE_01 / RCPT1_RULE_03
H09 status = REFERENCE_ONLY_INSUFFICIENT_SAMPLE_NOT_A_TRIGGER
future_return_label_as_rule_input = false
uses_2022_direct_fit = false
```

## 5. Validator Result

```text
status = PASS
pass = True
required_files_status = PASS
rule_design_status = PASS
threshold_source_status = PASS
pit_feature_status = PASS
small_sample_exclusion_status = PASS
anti_overfit_status = PASS
cash_guardrail_status = PASS
t2_metric_contract_status = PASS
diagnostic_semantics_status = PASS
forbidden_actions_status = PASS
t2_authorizable = True
recommended_next_step = PASS_READY_FOR_RCPT2_ADAPTIVE_THRESHOLD_REPLAY_SANITY_WORK_DOC
```

## 6. Recommendation

```text
PASS_READY_FOR_RCPT2_ADAPTIVE_THRESHOLD_REPLAY_SANITY_WORK_DOC
```
