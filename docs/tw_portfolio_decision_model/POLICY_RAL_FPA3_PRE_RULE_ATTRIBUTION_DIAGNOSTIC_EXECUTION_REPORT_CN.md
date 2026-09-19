---
created_at: 2026-06-23T11:34:25+00:00
status: pass_ready_for_review
phase: RAL_FPA3_PRE_RULE_ATTRIBUTION_DIAGNOSTIC
artifact_root: data_tw/experiments/full_path_action_diagnostic/fpa3_pre_rule_attribution_diagnostic
readonly_only: true
simulation_only: true
production_allowed: false
---

# RAL-FPA3 Pre-rule Attribution Diagnostic 执行报告

## 1. Scope

本轮只执行 FPA3 pre-rule attribution diagnostic。FPA4 run = false；rule_sanity_run = false；strict_test_used = false；rule_selection_run = false；threshold_selection_run = false；model_training_run = false；OrderIntent_output = false；target_weight_output = false；target_position_output = false；quantity_or_broker_output = false；production_allowed = false。

## 2. Inputs

- FPA2 metric root: `data_tw/experiments/full_path_action_diagnostic/fpa2_r_full_path_metric_reconciliation_repair`
- FPA2 lineage root: `data_tw/experiments/full_path_action_diagnostic/fpa2_r_full_path_replay_lineage_repair`
- Positive action spaces analyzed: `hold_continuation, replacement_buy, sell_timing`

## 3. Attribution Summary

Feature bucket rows: 38
Direction rows: 19
Candidate hypotheses: 18

## 4. Candidate Hypotheses

```json
[
  {
    "hypothesis_id": "FPA3_H01",
    "action_space": "hold_continuation",
    "feature_names": "holding_days",
    "human_readable_hypothesis": "hold_continuation upper-bound appears associated with observable bucket holding_days=holding_days_000_004; this is diagnostic only and not an executable rule.",
    "train_support_summary": "n=28, mean_delta=44043.40659643, positive_rate=1.0",
    "validation_support_summary": "n=13, mean_delta=12585.46834615, positive_rate=1.0",
    "observable_before_action": true,
    "low_dimensional": true,
    "not_oracle_only": true,
    "not_baseline_clone": true,
    "not_cash_only": true,
    "validation_threshold_mining_used": false,
    "eligible_for_reviewer_to_consider_fpa4_work_doc": true
  },
  {
    "hypothesis_id": "FPA3_H02",
    "action_space": "hold_continuation",
    "feature_names": "holding_days",
    "human_readable_hypothesis": "hold_continuation upper-bound appears associated with observable bucket holding_days=holding_days_005_019; this is diagnostic only and not an executable rule.",
    "train_support_summary": "n=127, mean_delta=55072.4330378, positive_rate=1.0",
    "validation_support_summary": "n=50, mean_delta=26991.464422, positive_rate=1.0",
    "observable_before_action": true,
    "low_dimensional": true,
    "not_oracle_only": true,
    "not_baseline_clone": true,
    "not_cash_only": true,
    "validation_threshold_mining_used": false,
    "eligible_for_reviewer_to_consider_fpa4_work_doc": true
  },
  {
    "hypothesis_id": "FPA3_H03",
    "action_space": "hold_continuation",
    "feature_names": "holding_days",
    "human_readable_hypothesis": "hold_continuation upper-bound appears associated with observable bucket holding_days=holding_days_020_059; this is diagnostic only and not an executable rule.",
    "train_support_summary": "n=134, mean_delta=46739.28634104, positive_rate=1.0",
    "validation_support_summary": "n=77, mean_delta=22083.7185039, positive_rate=1.0",
    "observable_before_action": true,
    "low_dimensional": true,
    "not_oracle_only": true,
    "not_baseline_clone": true,
    "not_cash_only": true,
    "validation_threshold_mining_used": false,
    "eligible_for_reviewer_to_consider_fpa4_work_doc": true
  },
  {
    "hypothesis_id": "FPA3_H04",
    "action_space": "hold_continuation",
    "feature_names": "holding_days",
    "human_readable_hypothesis": "hold_continuation upper-bound appears associated with observable bucket holding_days=holding_days_060_plus; this is diagnostic only and not an executable rule.",
    "train_support_summary": "n=21, mean_delta=69500.5636381, positive_rate=1.0",
    "validation_support_summary": "n=10, mean_delta=126838.23624, positive_rate=1.0",
    "observable_before_action": true,
    "low_dimensional": true,
    "not_oracle_only": true,
    "not_baseline_clone": true,
    "not_cash_only": true,
    "validation_threshold_mining_used": false,
    "eligible_for_reviewer_to_consider_fpa4_work_doc": true
  },
  {
    "hypothesis_id": "FPA3_H05",
    "action_space": "hold_continuation",
    "feature_names": "holding_unrealized_return_bucket",
    "human_readable_hypothesis": "hold_continuation upper-bound appears associated with observable bucket holding_unrealized_return_bucket=unrealized_gain_large; this is diagnostic only and not an executable rule.",
    "train_support_summary": "n=132, mean_delta=68294.14095303, positive_rate=1.0",
    "validation_support_summary": "n=66, mean_delta=43803.41086515, positive_rate=1.0",
    "observable_before_action": true,
    "low_dimensional": true,
    "not_oracle_only": true,
    "not_baseline_clone": true,
    "not_cash_only": true,
    "validation_threshold_mining_used": false,
    "eligible_for_reviewer_to_consider_fpa4_work_doc": true
  },
  {
    "hypothesis_id": "FPA3_H06",
    "action_space": "hold_continuation",
    "feature_names": "holding_unrealized_return_bucket",
    "human_readable_hypothesis": "hold_continuation upper-bound appears associated with observable bucket holding_unrealized_return_bucket=unrealized_gain_small; this is diagnostic only and not an executable rule.",
    "train_support_summary": "n=25, mean_delta=24288.115812, positive_rate=1.0",
    "validation_support_summary": "n=25, mean_delta=19467.773932, positive_rate=1.0",
    "observable_before_action": true,
    "low_dimensional": true,
    "not_oracle_only": true,
    "not_baseline_clone": true,
    "not_cash_only": true,
    "validation_threshold_mining_used": false,
    "eligible_for_reviewer_to_consider_fpa4_work_doc": true
  },
  {
    "hypothesis_id": "FPA3_H07",
    "action_space": "hold_continuation",
    "feature_names": "holding_unrealized_return_bucket",
    "human_readable_hypothesis": "hold_continuation upper-bound appears associated with observable bucket holding_unrealized_return_bucket=unrealized_loss_large; this is diagnostic only and not an executable rule.",
    "train_support_summary": "n=129, mean_delta=42426.52346589, positive_rate=1.0",
    "validation_support_summary": "n=38, mean_delta=17698.2563, positive_rate=1.0",
    "observable_before_action": true,
    "low_dimensional": true,
    "not_oracle_only": true,
    "not_baseline_clone": true,
    "not_cash_only": true,
    "validation_threshold_mining_used": false,
    "eligible_for_reviewer_to_consider_fpa4_work_doc": true
  },
  {
    "hypothesis_id": "FPA3_H08",
    "action_space": "hold_continuation",
    "feature_names": "holding_unrealized_return_bucket",
    "human_readable_hypothesis": "hold_continuation upper-bound appears associated with observable bucket holding_unrealized_return_bucket=unrealized_loss_small; this is diagnostic only and not an executable rule.",
    "train_support_summary": "n=24, mean_delta=35622.4816, positive_rate=1.0",
    "validation_support_summary": "n=21, mean_delta=20559.99009524, positive_rate=1.0",
    "observable_before_action": true,
    "low_dimensional": true,
    "not_oracle_only": true,
    "not_baseline_clone": true,
    "not_cash_only": true,
    "validation_threshold_mining_used": false,
    "eligible_for_reviewer_to_consider_fpa4_work_doc": true
  },
  {
    "hypothesis_id": "FPA3_H09",
    "action_space": "replacement_buy",
    "feature_names": "candidate_replacement_rank",
    "human_readable_hypothesis": "replacement_buy upper-bound appears associated with observable bucket candidate_replacement_rank=rank_001_010; this is diagnostic only and not an executable rule.",
    "train_support_summary": "n=127, mean_delta=3343.5509189, positive_rate=0.88976378",
    "validation_support_summary": "n=44, mean_delta=3689.22088182, positive_rate=0.93181818",
    "observable_before_action": true,
    "low_dimensional": true,
    "not_oracle_only": true,
    "not_baseline_clone": true,
    "not_cash_only": true,
    "validation_threshold_mining_used": false,
    "eligible_for_reviewer_to_consider_fpa4_work_doc": true
  },
  {
    "hypothesis_id": "FPA3_H10",
    "action_space": "replacement_buy",
    "feature_names": "candidate_replacement_rank",
    "human_readable_hypothesis": "replacement_buy upper-bound appears associated with observable bucket candidate_replacement_rank=rank_011_025; this is diagnostic only and not an executable rule.",
    "train_support_summary": "n=144, mean_delta=3952.13880972, positive_rate=1.0",
    "validation_support_summary": "n=67, mean_delta=4666.70062537, positive_rate=1.0",
    "observable_before_action": true,
    "low_dimensional": true,
    "not_oracle_only": true,
    "not_baseline_clone": true,
    "not_cash_only": true,
    "validation_threshold_mining_used": false,
    "eligible_for_reviewer_to_consider_fpa4_work_doc": true
  },
  {
    "hypothesis_id": "FPA3_H11",
    "action_space": "replacement_buy",
    "feature_names": "candidate_replacement_rank",
    "human_readable_hypothesis": "replacement_buy upper-bound appears associated with observable bucket candidate_replacement_rank=rank_026_050; this is diagnostic only and not an executable rule.",
    "train_support_summary": "n=210, mean_delta=3650.84842619, positive_rate=1.0",
    "validation_support_summary": "n=131, mean_delta=4393.08235878, positive_rate=1.0",
    "observable_before_action": true,
    "low_dimensional": true,
    "not_oracle_only": true,
    "not_baseline_clone": true,
    "not_cash_only": true,
    "validation_threshold_mining_used": false,
    "eligible_for_reviewer_to_consider_fpa4_work_doc": true
  },
  {
    "hypothesis_id": "FPA3_H12",
    "action_space": "sell_timing",
    "feature_names": "holding_days",
    "human_readable_hypothesis": "sell_timing upper-bound appears associated with observable bucket holding_days=holding_days_000_004; this is diagnostic only and not an executable rule.",
    "train_support_summary": "n=45, mean_delta=15182.90653778, positive_rate=1.0",
    "validation_support_summary": "n=24, mean_delta=7937.712475, positive_rate=1.0",
    "observable_before_action": true,
    "low_dimensional": true,
    "not_oracle_only": true,
    "not_baseline_clone": true,
    "not_cash_only": true,
    "validation_threshold_mining_used": false,
    "eligible_for_reviewer_to_consider_fpa4_work_doc": true
  },
  {
    "hypothesis_id": "FPA3_H13",
    "action_space": "sell_timing",
    "feature_names": "holding_days",
    "human_readable_hypothesis": "sell_timing upper-bound appears associated with observable bucket holding_days=holding_days_005_019; this is diagnostic only and not an executable rule.",
    "train_support_summary": "n=130, mean_delta=24523.59338615, positive_rate=1.0",
    "validation_support_summary": "n=53, mean_delta=10361.52067547, positive_rate=1.0",
    "observable_before_action": true,
    "low_dimensional": true,
    "not_oracle_only": true,
    "not_baseline_clone": true,
    "not_cash_only": true,
    "validation_threshold_mining_used": false,
    "eligible_for_reviewer_to_consider_fpa4_work_doc": true
  },
  {
    "hypothesis_id": "FPA3_H14",
    "action_space": "sell_timing",
    "feature_names": "holding_days",
    "human_readable_hypothesis": "sell_timing upper-bound appears associated with observable bucket holding_days=holding_days_020_059; this is diagnostic only and not an executable rule.",
    "train_support_summary": "n=69, mean_delta=34209.75665362, positive_rate=1.0",
    "validation_support_summary": "n=45, mean_delta=9971.28973778, positive_rate=1.0",
    "observable_before_action": true,
    "low_dimensional": true,
    "not_oracle_only": true,
    "not_baseline_clone": true,
    "not_cash_only": true,
    "validation_threshold_mining_used": false,
    "eligible_for_reviewer_to_consider_fpa4_work_doc": true
  },
  {
    "hypothesis_id": "FPA3_H15",
    "action_space": "sell_timing",
    "feature_names": "holding_unrealized_return_bucket",
    "human_readable_hypothesis": "sell_timing upper-bound appears associated with observable bucket holding_unrealized_return_bucket=unrealized_gain_large; this is diagnostic only and not an executable rule.",
    "train_support_summary": "n=122, mean_delta=35791.48842295, positive_rate=1.0",
    "validation_support_summary": "n=44, mean_delta=13509.57509773, positive_rate=1.0",
    "observable_before_action": true,
    "low_dimensional": true,
    "not_oracle_only": true,
    "not_baseline_clone": true,
    "not_cash_only": true,
    "validation_threshold_mining_used": false,
    "eligible_for_reviewer_to_consider_fpa4_work_doc": true
  },
  {
    "hypothesis_id": "FPA3_H16",
    "action_space": "sell_timing",
    "feature_names": "holding_unrealized_return_bucket",
    "human_readable_hypothesis": "sell_timing upper-bound appears associated with observable bucket holding_unrealized_return_bucket=unrealized_gain_small; this is diagnostic only and not an executable rule.",
    "train_support_summary": "n=19, mean_delta=11707.73163684, positive_rate=1.0",
    "validation_support_summary": "n=19, mean_delta=6152.48348947, positive_rate=1.0",
    "observable_before_action": true,
    "low_dimensional": true,
    "not_oracle_only": true,
    "not_baseline_clone": true,
    "not_cash_only": true,
    "validation_threshold_mining_used": false,
    "eligible_for_reviewer_to_consider_fpa4_work_doc": true
  },
  {
    "hypothesis_id": "FPA3_H17",
    "action_space": "sell_timing",
    "feature_names": "holding_unrealized_return_bucket",
    "human_readable_hypothesis": "sell_timing upper-bound appears associated with observable bucket holding_unrealized_return_bucket=unrealized_loss_large; this is diagnostic only and not an executable rule.",
    "train_support_summary": "n=82, mean_delta=21446.55817073, positive_rate=1.0",
    "validation_support_summary": "n=48, mean_delta=9025.61995625, positive_rate=1.0",
    "observable_before_action": true,
    "low_dimensional": true,
    "not_oracle_only": true,
    "not_baseline_clone": true,
    "not_cash_only": true,
    "validation_threshold_mining_used": false,
    "eligible_for_reviewer_to_consider_fpa4_work_doc": true
  },
  {
    "hypothesis_id": "FPA3_H18",
    "action_space": "sell_timing",
    "feature_names": "holding_unrealized_return_bucket",
    "human_readable_hypothesis": "sell_timing upper-bound appears associated with observable bucket holding_unrealized_return_bucket=unrealized_loss_small; this is diagnostic only and not an executable rule.",
    "train_support_summary": "n=25, mean_delta=9481.188092, positive_rate=1.0",
    "validation_support_summary": "n=12, mean_delta=4535.87374167, positive_rate=1.0",
    "observable_before_action": true,
    "low_dimensional": true,
    "not_oracle_only": true,
    "not_baseline_clone": true,
    "not_cash_only": true,
    "validation_threshold_mining_used": false,
    "eligible_for_reviewer_to_consider_fpa4_work_doc": true
  }
]
```

## 5. Oracle Leakage / Forbidden Consumer

Oracle labels are used only for diagnostic attribution. No executable rules, thresholds, strict_test, model training, OrderIntent, target, broker, or production outputs were produced.

## 6. Validator Summary

```json
{
  "ok": true,
  "status": "PASS_FPA3_PRE_RULE_ATTRIBUTION_DIAGNOSTIC_READY_FOR_REVIEW",
  "phase": "RAL_FPA3_PRE_RULE_ATTRIBUTION_DIAGNOSTIC",
  "failed_count": 0,
  "final_recommendation": "READY_FOR_REVIEWER_TO_CONSIDER_FPA4_WORK_DOC"
}
```

## 7. Final Recommendation

```text
READY_FOR_REVIEWER_TO_CONSIDER_FPA4_WORK_DOC
```
