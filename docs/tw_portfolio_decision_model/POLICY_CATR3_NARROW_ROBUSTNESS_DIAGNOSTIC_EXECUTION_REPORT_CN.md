---
created_at: 2026-06-23T17:43:28+00:00
status: execution_complete
phase: CATR3_NARROW_ROBUSTNESS_DIAGNOSTIC
artifact_root: data_tw/experiments/candidate_atpal_replay_feasibility/catr3_narrow_robustness_diagnostic
candidate_pass_fail_authorized: false
strict_test_authorized: false
model_training_authorized: false
production_allowed: false
---

# CATR3 Narrow Robustness Diagnostic 执行报告

## 1. Scope

本轮严格执行 CATR3 窄范围 robustness diagnostic，只覆盖：

```text
FPA4_C01 / rank_lte_25
FPA4_C01 / rank_lte_50
FPA4_C05 / holding_days_020_059
```

未执行 candidate pass/fail judgement、FPA4 repair、新增候选、调阈值、validation mining、strict_test、模型训练或生产/default/order/provider/frontend/Agent 集成。

## 2. Documents / Artifacts Read

```text
docs/tw_portfolio_decision_model/POLICY_CATR_FINAL_ROUTE_DECISION_CN.md
docs/tw_portfolio_decision_model/POLICY_CATR3_NARROW_ROBUSTNESS_DIAGNOSTIC_WORK_CN.md
docs/tw_portfolio_decision_model/POLICY_CATR2_CANDIDATE_ATPAL_LEDGER_ANALYSIS_REVIEW_CN.md
data_tw/experiments/candidate_atpal_replay_feasibility/catr1_candidate_atpal_replay_builder/
data_tw/experiments/candidate_atpal_replay_feasibility/catr2_candidate_atpal_ledger_analysis/
data_tw/experiments/action_trade_pnl_attribution_ledger/atpal2_contribution_audit/
```

## 3. Changes Made

新增脚本：

```text
scripts/build_tw_policy_catr3_narrow_robustness_diagnostic.py
```

新增产物目录：

```text
data_tw/experiments/candidate_atpal_replay_feasibility/catr3_narrow_robustness_diagnostic/
```

## 4. Evidence Produced

```text
manifest.json
source_artifact_manifest.json
narrow_candidate_inventory.csv
narrow_candidate_symbol_date_stress.csv
narrow_candidate_top_contributor_removal_sensitivity.csv
narrow_candidate_year_split_stability.csv
narrow_candidate_trade_lifecycle_stress.csv
narrow_candidate_cost_turnover_stress.csv
narrow_candidate_route_recommendation.csv
forbidden_consumer_audit.csv
validator_report.json
diagnostic_findings.md
```

## 5. Route Recommendation Summary

- `FPA4_C01 / rank_lte_25`: `close_candidate_negative_evidence` - `validation_delta_positive_but_train_delta_negative_and_validation_positive_delta_requires_higher_cost_turnover`
- `FPA4_C01 / rank_lte_50`: `close_candidate_negative_evidence` - `validation_delta_positive_but_train_delta_negative_and_validation_positive_delta_requires_higher_cost_turnover`
- `FPA4_C05 / holding_days_020_059`: `eligible_for_new_mainline_discussion_only` - `both_train_validation_positive_and_top10_removal_preserves_validation_positive_direction_but_edge_is_thin`

这些 recommendation 均为路线讨论建议，不是 candidate pass/fail。

## 6. Validator

```json
{
  "ok": true,
  "status": "CATR3_ROBUSTNESS_READY_FOR_REVIEW",
  "final_recommendation": "READY_FOR_REVIEWER_TO_AUDIT_CATR3_ROBUSTNESS",
  "narrow_scope_only": true,
  "candidate_scope_matches_route_decision": true,
  "analysis_only": true,
  "candidate_pass_fail_judgement": false,
  "new_candidate_added": false,
  "threshold_adjustment": false,
  "strict_test_used": false,
  "model_training_run": false,
  "production_allowed": false,
  "order_intent_output": false,
  "target_weight_output": false,
  "target_position_output": false,
  "quantity_instruction_output": false,
  "broker_order_output": false,
  "failed_count": 0,
  "checks": [
    {
      "name": "narrow_scope_only",
      "passed": true
    },
    {
      "name": "route_recommendations_allowed",
      "passed": true
    },
    {
      "name": "no_forbidden_fields_in_csv_outputs",
      "passed": true
    },
    {
      "name": "all_required_analysis_outputs_non_empty",
      "passed": true
    }
  ]
}
```

## 7. Final Recommendation

```text
READY_FOR_REVIEWER_TO_AUDIT_CATR3_ROBUSTNESS
```
