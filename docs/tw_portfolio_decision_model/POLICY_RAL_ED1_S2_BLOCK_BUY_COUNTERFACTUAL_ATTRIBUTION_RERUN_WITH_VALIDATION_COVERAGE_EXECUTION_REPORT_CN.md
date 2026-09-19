---
created_at: 2026-06-23
status: executed_ral_ed1_s2_block_buy_counterfactual_attribution_rerun_with_validation_coverage
phase: RAL_ED1_S2_BLOCK_BUY_COUNTERFACTUAL_ATTRIBUTION_RERUN_WITH_VALIDATION_COVERAGE
work_doc: docs/tw_portfolio_decision_model/POLICY_RAL_ED1_S2_BLOCK_BUY_COUNTERFACTUAL_ATTRIBUTION_RERUN_WITH_VALIDATION_COVERAGE_WORK_CN.md
artifact_root: data_tw/experiments/explicit_rule_discovery/ral_ed1_s2_block_buy_counterfactual_attribution_with_validation_coverage
final_recommendation: READY_FOR_REVIEWER_TO_CONSIDER_RAL_ED2_WORK_DOCUMENT
ral_ed2_authorized: false
rule_replay_run: false
rule_selection_run: false
threshold_selection_run: false
strict_test_used: false
model_training_run: false
production_allowed: false
readonly_only: true
simulation_only: true
---

# RAL-ED1-S2 Block-buy Counterfactual Attribution Rerun With Validation Coverage 执行报告

## 1. Scope

本轮只使用 ED1-T 补齐后的 `block_buy_trace_probe_v1` local counterfactual traces 重跑 block-buy attribution。未执行 ED2、规则 replay、rule selection、threshold selection、strict_test、训练或生产化。

## 2. Evidence Produced

```text
manifest.json
source_trace_manifest.json
bucket_policy.md
block_buy_trace_coverage_audit.csv
block_buy_feature_attribution_by_bucket.csv
block_buy_train_validation_direction_audit.csv
block_buy_candidate_hypothesis_audit.csv
trace_status_audit.csv
forbidden_consumer_audit.csv
unavailable_field_blocker_audit.csv
diagnostic_findings.md
validator_report.json
```

## 3. Main Result

```text
train_rows = 447
validation_rows = 223
validation_date_count = 223
validation_symbol_count = 88
eligible_candidate_hypothesis_count = 14
final_recommendation = READY_FOR_REVIEWER_TO_CONSIDER_RAL_ED2_WORK_DOCUMENT
```

## 4. Compliance

```text
trace_status = counterfactual_replay_trace
trace_quality = counterfactual_replay_trace_local_action_delta_not_full_portfolio_path
local_action_delta_only = true
full_portfolio_path_available = false
rule_replay_run = false
rule_selection_run = false
threshold_selection_run = false
strict_test_used = false
model_training_run = false
OrderIntent output = false
target_weight / target_position / quantity / broker_order = false
production_allowed = false
```

## 5. Validator

```text
ok = true
status = PASS_RAL_ED1_S2_ATTRIBUTION_WITH_VALIDATION_READY_FOR_REVIEW
failed_count = 0
```

## 6. Recommendation For Reviewer

```text
READY_FOR_REVIEWER_TO_CONSIDER_RAL_ED2_WORK_DOCUMENT
```

该建议不授权 ED2。若审查者接受候选，也只能由审查者/统筹另行决定是否撰写 ED2 工作文档。
