---
created_at: 2026-06-23T11:06:26+00:00
status: pass_ready_for_review
phase: RAL_FPA2_R_FULL_PATH_REPLAY_LINEAGE_REPAIR
artifact_root: data_tw/experiments/full_path_action_diagnostic/fpa2_r_full_path_replay_lineage_repair
readonly_only: true
simulation_only: true
production_allowed: false
---

# RAL-FPA2-R Full-path Replay Lineage Repair 执行报告

## 1. Scope

本轮只修复 FPA2 sell_timing / hold_continuation full-path replay 与 lineage 缺口。FPA3 run = false；FPA4 run = false；strict_test_used = false；rule_selection_run = false；threshold_selection_run = false；model_training_run = false；OrderIntent_output = false；target_weight_output = false；target_position_output = false；quantity_or_broker_output = false；production_allowed = false。

## 2. Outputs Produced

输出目录：`data_tw/experiments/full_path_action_diagnostic/fpa2_r_full_path_replay_lineage_repair`

已输出 repaired upper-bound、pre/post lineage、pending lineage、replacement lineage、cost/concentration/direction/leakage/full-path replay audit、forbidden consumer audit、validator 和 findings。

## 3. Full-path Replay Audit

```json
[
  {
    "action_space": "replacement_buy",
    "full_path_replay_used": true,
    "positive_upper_bound": true,
    "pre_post_lineage_present": true,
    "pending_order_lineage_present": true,
    "status": "pass"
  },
  {
    "action_space": "sell_timing",
    "full_path_replay_used": true,
    "positive_upper_bound": true,
    "pre_post_lineage_present": true,
    "pending_order_lineage_present": true,
    "status": "pass"
  },
  {
    "action_space": "hold_continuation",
    "full_path_replay_used": true,
    "positive_upper_bound": true,
    "pre_post_lineage_present": true,
    "pending_order_lineage_present": true,
    "status": "pass"
  },
  {
    "action_space": "regime_participation",
    "full_path_replay_used": true,
    "positive_upper_bound": false,
    "pre_post_lineage_present": true,
    "pending_order_lineage_present": true,
    "status": "pass"
  }
]
```

## 4. Train / Validation Direction

```json
[
  {
    "action_space": "replacement_buy",
    "train_net_delta_after_fee_tax": 1760417.1248,
    "validation_net_delta_after_fee_tax": 1050488.4497,
    "train_positive": true,
    "validation_positive": true,
    "direction_consistency_status": "pass",
    "sample_count_train": 481,
    "sample_count_validation": 242,
    "not_cash_no_trade": true,
    "not_baseline_clone": true,
    "eligible_for_reviewer_to_consider_fpa3_work_doc": true
  },
  {
    "action_space": "sell_timing",
    "train_net_delta_after_fee_tax": 6584655.961,
    "validation_net_delta_after_fee_tax": 1198978.7334,
    "train_positive": true,
    "validation_positive": true,
    "direction_consistency_status": "pass",
    "sample_count_train": 248,
    "sample_count_validation": 123,
    "not_cash_no_trade": true,
    "not_baseline_clone": true,
    "eligible_for_reviewer_to_consider_fpa3_work_doc": true
  },
  {
    "action_space": "hold_continuation",
    "train_net_delta_after_fee_tax": 15949990.5866,
    "validation_net_delta_after_fee_tax": 4482012.9968,
    "train_positive": true,
    "validation_positive": true,
    "direction_consistency_status": "pass",
    "sample_count_train": 310,
    "sample_count_validation": 150,
    "not_cash_no_trade": true,
    "not_baseline_clone": true,
    "eligible_for_reviewer_to_consider_fpa3_work_doc": true
  },
  {
    "action_space": "regime_participation",
    "train_net_delta_after_fee_tax": 0.0,
    "validation_net_delta_after_fee_tax": 0.0,
    "train_positive": false,
    "validation_positive": false,
    "direction_consistency_status": "fail_no_stable_positive_upper_bound",
    "sample_count_train": 481,
    "sample_count_validation": 242,
    "not_cash_no_trade": true,
    "not_baseline_clone": false,
    "eligible_for_reviewer_to_consider_fpa3_work_doc": false
  }
]
```

## 5. Cost and Concentration

```json
{
  "transaction_cost": [
    {
      "action_space": "replacement_buy",
      "gross_delta": 2810905.5745,
      "fee_tax_delta": 0.0,
      "turnover_delta": 706.0,
      "cash_opportunity_delta": 0.0,
      "nav_path_delta": 2810905.5745,
      "net_delta_after_fee_tax": 2810905.5745,
      "cost_covered": true
    },
    {
      "action_space": "sell_timing",
      "gross_delta": 7783634.6944,
      "fee_tax_delta": 0.0,
      "turnover_delta": 0.0,
      "cash_opportunity_delta": 0.0,
      "nav_path_delta": 7783634.6944,
      "net_delta_after_fee_tax": 7783634.6944,
      "cost_covered": true
    },
    {
      "action_space": "hold_continuation",
      "gross_delta": 20432003.5834,
      "fee_tax_delta": 0.0,
      "turnover_delta": 0.0,
      "cash_opportunity_delta": 0.0,
      "nav_path_delta": 20432003.5834,
      "net_delta_after_fee_tax": 20432003.5834,
      "cost_covered": true
    },
    {
      "action_space": "regime_participation",
      "gross_delta": 0.0,
      "fee_tax_delta": 0.0,
      "turnover_delta": 0.0,
      "cash_opportunity_delta": 0.0,
      "nav_path_delta": 0.0,
      "net_delta_after_fee_tax": 0.0,
      "cost_covered": false
    }
  ],
  "concentration": [
    {
      "action_space": "hold_continuation",
      "positive_net_delta": 20432003.5834,
      "top_symbol_contribution_share": 0.10849625,
      "top_date_contribution_share": 0.02898812,
      "top_5_symbol_contribution_share": 0.34543199,
      "top_5_date_contribution_share": 0.121685,
      "concentration_gate_status": "pass"
    },
    {
      "action_space": "regime_participation",
      "positive_net_delta": 0.0,
      "top_symbol_contribution_share": 0.0,
      "top_date_contribution_share": 0.0,
      "top_5_symbol_contribution_share": 0.0,
      "top_5_date_contribution_share": 0.0,
      "concentration_gate_status": "review_required_or_no_positive_delta"
    },
    {
      "action_space": "replacement_buy",
      "positive_net_delta": 2810905.5745,
      "top_symbol_contribution_share": 0.04370199,
      "top_date_contribution_share": 0.00480992,
      "top_5_symbol_contribution_share": 0.18549883,
      "top_5_date_contribution_share": 0.02145602,
      "concentration_gate_status": "pass"
    },
    {
      "action_space": "sell_timing",
      "positive_net_delta": 7783634.6944,
      "top_symbol_contribution_share": 0.0914329,
      "top_date_contribution_share": 0.03247066,
      "top_5_symbol_contribution_share": 0.31401296,
      "top_5_date_contribution_share": 0.14770813,
      "concentration_gate_status": "pass"
    }
  ]
}
```

## 6. Validator Summary

```json
{
  "ok": true,
  "status": "PASS_FPA2_R_FULL_PATH_REPLAY_LINEAGE_REPAIR_READY_FOR_REVIEW",
  "phase": "RAL_FPA2_R_FULL_PATH_REPLAY_LINEAGE_REPAIR",
  "failed_count": 0,
  "final_recommendation": "READY_FOR_REVIEWER_TO_CONSIDER_FPA3_WORK_DOC"
}
```

## 7. Final Recommendation

```text
READY_FOR_REVIEWER_TO_CONSIDER_FPA3_WORK_DOC
```
