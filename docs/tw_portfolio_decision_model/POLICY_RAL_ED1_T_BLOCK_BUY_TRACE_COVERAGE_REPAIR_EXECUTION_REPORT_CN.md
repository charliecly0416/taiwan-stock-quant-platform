---
created_at: 2026-06-23
status: executed_ral_ed1_t_block_buy_trace_coverage_repair
phase: RAL_ED1_T_BLOCK_BUY_TRACE_COVERAGE_REPAIR
work_doc: docs/tw_portfolio_decision_model/POLICY_RAL_ED1_T_BLOCK_BUY_TRACE_COVERAGE_REPAIR_WORK_CN.md
artifact_root: data_tw/experiments/explicit_rule_discovery/ral_ed1_t_block_buy_trace_coverage_repair
final_recommendation: READY_FOR_REVIEWER_TO_CONSIDER_RAL_ED1_S2_ATTRIBUTION_RERUN_WORK
ral_ed1_s2_authorized: false
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

# RAL-ED1-T Block-buy Trace Coverage Repair 执行报告

## 1. Scope

本轮只补齐 `block_buy_trace_probe_v1` 的 local counterfactual trace 覆盖。未执行 ED1-S2 attribution rerun、ED2、规则 replay、规则选择、阈值选择、strict_test、训练或生产化。

## 2. Evidence Produced

输出目录：

```text
data_tw/experiments/explicit_rule_discovery/ral_ed1_t_block_buy_trace_coverage_repair/
```

必需产物均已输出：

```text
manifest.json
source_baseline_ledger_manifest.json
block_buy_trace_coverage_repair_design.md
block_buy_trace_coverage_audit.csv
counterfactual_trace_sample_or_full.csv
baseline_vs_intervention_delta_sample_or_full.csv
trace_status_audit.csv
train_validation_window_audit.csv
determinism_audit.csv
cost_turnover_delta_audit.csv
unavailable_field_blocker_audit.csv
forbidden_consumer_audit.csv
validator_report.json
diagnostic_findings.md
```

## 3. Main Result

```text
probe_id = block_buy_trace_probe_v1
trace_status = counterfactual_replay_trace
trace_quality = counterfactual_replay_trace_local_action_delta_not_full_portfolio_path
train_rows = 447
train_date_count = 446
train_symbol_count = 118
validation_rows = 223
validation_date_count = 223
validation_symbol_count = 88
final_recommendation = READY_FOR_REVIEWER_TO_CONSIDER_RAL_ED1_S2_ATTRIBUTION_RERUN_WORK
```

Validation trace 已生成且不是单日/极少数 symbol 覆盖。

## 4. Compliance

```text
local_action_delta_only = true
full_portfolio_path_available = false
diagnostic_probe_only = true
not_rule_candidate = true
not_selected_by_validation = true
strict_test_used = false
rule_replay_run = false
rule_selection_run = false
threshold_selection_run = false
model_training_run = false
OrderIntent output = false
target_weight / target_position / quantity / broker_order = false
production_allowed = false
```

## 5. Validator

`validator_report.json`:

```text
ok = true
status = PASS_RAL_ED1_T_TRACE_COVERAGE_REPAIR_READY_FOR_ED1_S2_REVIEW
failed_count = 0
```

## 6. Recommendation For Reviewer

```text
READY_FOR_REVIEWER_TO_CONSIDER_RAL_ED1_S2_ATTRIBUTION_RERUN_WORK
```

该建议只表示可以审查是否授权 ED1-S2 attribution rerun，不表示规则有效，也不授权 ED2。
