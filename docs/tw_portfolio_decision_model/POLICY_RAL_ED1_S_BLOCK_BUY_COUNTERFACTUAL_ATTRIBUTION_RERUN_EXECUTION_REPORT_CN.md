---
created_at: 2026-06-23
status: executed_ral_ed1_s_block_buy_counterfactual_attribution_rerun
phase: RAL_ED1_S_BLOCK_BUY_COUNTERFACTUAL_ATTRIBUTION_RERUN
work_doc: docs/tw_portfolio_decision_model/POLICY_RAL_ED1_S_BLOCK_BUY_COUNTERFACTUAL_ATTRIBUTION_RERUN_WORK_CN.md
artifact_root: data_tw/experiments/explicit_rule_discovery/ral_ed1_s_block_buy_counterfactual_attribution
final_recommendation: STOP_BLOCK_BUY_TRACE_COVERAGE_INSUFFICIENT
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

# RAL-ED1-S Block-buy Counterfactual Attribution Rerun 执行报告

## 1. Scope

本轮只使用 ED1-R 的 `block_buy_trace_probe_v1` local counterfactual traces 重新做 attribution。未执行 ED2、规则 replay、规则选择、阈值选择、strict_test、训练或生产化。

## 2. Evidence Produced

输出：

```text
manifest.json
source_trace_manifest.json
block_buy_trace_coverage_audit.csv
score_bucket_block_buy_delta_attribution.csv
score_gap_block_buy_delta_attribution.csv
score_zscore_block_buy_delta_attribution.csv
rank_delta_block_buy_delta_attribution.csv
score_delta_block_buy_delta_attribution.csv
regime_block_buy_delta_attribution.csv
cost_edge_block_buy_delta_attribution.csv
train_validation_direction_audit.csv
candidate_block_buy_rule_hypothesis_audit.csv
trace_status_audit.csv
forbidden_consumer_audit.csv
validator_report.json
diagnostic_findings.md
```

## 3. Main Result

```text
source_trace_rows = 120
train_rows = 120
validation_rows = 0
trace_status = counterfactual_replay_trace
trace_quality = counterfactual_replay_trace_local_action_delta_not_full_portfolio_path
final_recommendation = STOP_BLOCK_BUY_TRACE_COVERAGE_INSUFFICIENT
```

`validation_rows = 0`，因此不能做 train/validation 方向一致性判断，不能形成 ED2-ready block-buy hypothesis。

## 4. Compliance

```text
only block_buy_trace_probe_v1 used = true
all evidence trace_status = counterfactual_replay_trace
local_action_delta_only disclosed = true
full_portfolio_path_available = false
rule_replay_run = false
rule_selection_run = false
threshold_selection_run = false
strict_test_used = false
model_training_run = false
OrderIntent output = false
target_weight / target_position / quantity / broker_order = false
```

## 5. Validator

`validator_report.json`:

```text
ok = true
status = PASS_RAL_ED1_S_ARTIFACTS_COMPLETE_STOP_COVERAGE_INSUFFICIENT
failed_count = 0
```

## 6. Recommendation For Reviewer

```text
STOP_BLOCK_BUY_TRACE_COVERAGE_INSUFFICIENT
```

建议按 STOP 审查：产物完整，但 block-buy trace 覆盖不足，没有 validation rows，不能写 ED2 工作文档。
