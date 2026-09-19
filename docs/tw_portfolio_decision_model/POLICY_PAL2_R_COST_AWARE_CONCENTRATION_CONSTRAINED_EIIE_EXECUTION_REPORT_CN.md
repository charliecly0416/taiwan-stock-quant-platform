---
created_at: 2026-06-22T13:26:16+00:00
status: executed_pal2_r_cost_aware_concentration_constrained_eiie
phase: PAL2_R_COST_AWARE_CONCENTRATION_CONSTRAINED_EIIE
mainline_doc: docs/tw_portfolio_decision_model/POLICY_PAL_PAPER_ALIGNED_PORTFOLIO_ALLOCATION_RL_MAINLINE_CN.md
work_doc: docs/tw_portfolio_decision_model/POLICY_PAL2_R_COST_AWARE_CONCENTRATION_CONSTRAINED_EIIE_WORK_CN.md
artifact_root: data_tw/experiments/paper_aligned_portfolio_rl/pal2_r_cost_concentration_repair
strict_test_used: false
production_allowed: false
readonly_only: true
simulation_only: true
recommendation: STOP_NO_STRICT_TEST_REQUEST
---

# PAL2-R Cost-aware Concentration-constrained EIIE 执行报告

## 1. Scope

本轮只执行 PAL2-R EIIE repair：base_config、repair_a、repair_b、repair_c。未进入 PAL3，未运行或读取 strict_test。

## 2. Documents Read

```text
docs/tw_portfolio_decision_model/POLICY_PAL_PAPER_ALIGNED_PORTFOLIO_ALLOCATION_RL_MAINLINE_CN.md
docs/tw_portfolio_decision_model/POLICY_PAL2_MINIMAL_EIIE_CNN_TRAINING_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_PAL2_MINIMAL_EIIE_CNN_TRAINING_EXECUTION_REPORT_CN.md
docs/tw_portfolio_decision_model/POLICY_PAL2_COORDINATOR_OPINION_FOR_REVIEWER_CN.md
docs/tw_portfolio_decision_model/POLICY_PAL2_R_COST_AWARE_CONCENTRATION_CONSTRAINED_EIIE_WORK_CN.md
```

## 3. Repair Implementation

```text
transaction-cost-aware reward: gross return - fee/tax cost
turnover penalty: repair_a/b/c use predeclared turnover_penalty_weight
no-trade threshold: repair_b/c use rebalance_threshold
allocation smoothing: repair_b/c use smoothing_alpha
concentration control: repair_c uses HHI penalty, entropy regularizer, and diagnostic cap
```

## 4. Configs Run

```text
configs = ['base_config', 'repair_a', 'repair_b', 'repair_c']
seeds = [11, 23, 37]
train = 2023-01-01..2024-12-31
validation = 2025-01-01..2025-12-31
```

## 5. Validation Result

```text
PAL1 validation baseline = 0.95376753
selected_config_id = repair_c
selected_mean_validation_net_return_after_fee_tax = 0.02833287
excess_vs_PAL1_baseline_after_fee_tax = -0.92543466
hard_gates_pass = False
```

## 6. Evidence Produced

```text
manifest.json
repair_config_manifest.json
reward_design_audit.md
train_curve_by_config_seed.csv
validation_replay_metrics_by_config_seed.csv
validation_selection_audit.csv
turnover_cost_audit.csv
cost_sensitivity_audit.csv
concentration_audit.csv
allocation_smoothing_audit.csv
no_trade_threshold_audit.csv
baseline_clone_audit.csv
forbidden_feature_and_consumer_audit.csv
validator_report.json
golden_samples_report.json
```

## 7. Forbidden Actions Audit

```text
strict_test_used = false
order_intent_output = false
target_weight_output = false
target_position_output = false
quantity_or_broker_output = false
provider/latest/monitor/frontend/Agent/broker/production touched = false
```

## 8. Recommendation

```text
STOP_NO_STRICT_TEST_REQUEST
```

若 PAL2-R 未通过，本报告不请求 strict_test、不请求 PAL3。
