---
created_at: 2026-06-23T11:22:09+00:00
status: pass_ready_for_review
phase: RAL_FPA2_R_FULL_PATH_METRIC_RECONCILIATION_REPAIR
artifact_root: data_tw/experiments/full_path_action_diagnostic/fpa2_r_full_path_metric_reconciliation_repair
readonly_only: true
simulation_only: true
production_allowed: false
---

# RAL-FPA2-R Full-path Metric Reconciliation Repair 执行报告

## 1. Scope

本轮只修复 FPA2-R full-path metric reconciliation / validator 口径。FPA3 run = false；FPA4 run = false；strict_test_used = false；rule_selection_run = false；threshold_selection_run = false；model_training_run = false；OrderIntent_output = false；target_weight_output = false；target_position_output = false；quantity_or_broker_output = false；production_allowed = false。

## 2. Reconciliation Scope

主 pass gate 改为 `full_path_metric_reconciliation.csv`，以 `action_space_summary_repaired.csv` 为主表。`regime_participation` 声明为 baseline/no-op path。事件级 delta 不再作为 primary gate。

## 3. Full-path Metric Reconciliation

```json
[
  {
    "split": "train",
    "action_space": "replacement_buy",
    "baseline_source_action_space": "regime_participation",
    "baseline_noop_path_declared": true,
    "baseline_final_equity": 3418857.97,
    "action_space_final_equity": 28973382.97,
    "excess_final_equity": 25554525.0,
    "baseline_net_return_after_fee_tax": 2.41885797,
    "action_space_net_return_after_fee_tax": 27.97338297,
    "excess_net_return_after_fee_tax": 25.554525,
    "baseline_fee_and_tax": 549665.29,
    "action_space_fee_and_tax": 1783060.53,
    "fee_tax_delta": 1233395.24,
    "baseline_turnover_proxy": 87.37059302,
    "action_space_turnover_proxy": 75.14345085,
    "turnover_delta": -12.22714217,
    "baseline_action_count": 885,
    "action_space_action_count": 778,
    "action_count_delta": -107,
    "baseline_skip_count": 26,
    "action_space_skip_count": 66,
    "skip_count_delta": 40,
    "primary_gate_metric": "full_path_excess_net_return_after_fee_tax",
    "event_delta_used_as_primary_gate": false,
    "readonly_simulation_only": true
  },
  {
    "split": "validation",
    "action_space": "replacement_buy",
    "baseline_source_action_space": "regime_participation",
    "baseline_noop_path_declared": true,
    "baseline_final_equity": 1953767.53,
    "action_space_final_equity": 4762513.38,
    "excess_final_equity": 2808745.85,
    "baseline_net_return_after_fee_tax": 0.95376753,
    "action_space_net_return_after_fee_tax": 3.76251338,
    "excess_net_return_after_fee_tax": 2.80874585,
    "baseline_fee_and_tax": 146214.73,
    "action_space_fee_and_tax": 254567.22,
    "fee_tax_delta": 108352.49,
    "baseline_turnover_proxy": 42.18778217,
    "action_space_turnover_proxy": 41.4520698,
    "turnover_delta": -0.73571237,
    "baseline_action_count": 436,
    "action_space_action_count": 400,
    "action_count_delta": -36,
    "baseline_skip_count": 12,
    "action_space_skip_count": 37,
    "skip_count_delta": 25,
    "primary_gate_metric": "full_path_excess_net_return_after_fee_tax",
    "event_delta_used_as_primary_gate": false,
    "readonly_simulation_only": true
  },
  {
    "split": "train",
    "action_space": "sell_timing",
    "baseline_source_action_space": "regime_participation",
    "baseline_noop_path_declared": true,
    "baseline_final_equity": 3418857.97,
    "action_space_final_equity": 9003020.92,
    "excess_final_equity": 5584162.95,
    "baseline_net_return_after_fee_tax": 2.41885797,
    "action_space_net_return_after_fee_tax": 8.00302092,
    "excess_net_return_after_fee_tax": 5.58416295,
    "baseline_fee_and_tax": 549665.29,
    "action_space_fee_and_tax": 672938.68,
    "fee_tax_delta": 123273.39,
    "baseline_turnover_proxy": 87.37059302,
    "action_space_turnover_proxy": 63.01446831,
    "turnover_delta": -24.35612471,
    "baseline_action_count": 885,
    "action_space_action_count": 647,
    "action_count_delta": -238,
    "baseline_skip_count": 26,
    "action_space_skip_count": 275,
    "skip_count_delta": 249,
    "primary_gate_metric": "full_path_excess_net_return_after_fee_tax",
    "event_delta_used_as_primary_gate": false,
    "readonly_simulation_only": true
  },
  {
    "split": "validation",
    "action_space": "sell_timing",
    "baseline_source_action_space": "regime_participation",
    "baseline_noop_path_declared": true,
    "baseline_final_equity": 1953767.53,
    "action_space_final_equity": 2200995.61,
    "excess_final_equity": 247228.08,
    "baseline_net_return_after_fee_tax": 0.95376753,
    "action_space_net_return_after_fee_tax": 1.20099561,
    "excess_net_return_after_fee_tax": 0.24722808,
    "baseline_fee_and_tax": 146214.73,
    "action_space_fee_and_tax": 131343.58,
    "fee_tax_delta": -14871.15,
    "baseline_turnover_proxy": 42.18778217,
    "action_space_turnover_proxy": 33.23266852,
    "turnover_delta": -8.95511365,
    "baseline_action_count": 436,
    "action_space_action_count": 330,
    "action_count_delta": -106,
    "baseline_skip_count": 12,
    "action_space_skip_count": 127,
    "skip_count_delta": 115,
    "primary_gate_metric": "full_path_excess_net_return_after_fee_tax",
    "event_delta_used_as_primary_gate": false,
    "readonly_simulation_only": true
  },
  {
    "split": "train",
    "action_space": "hold_continuation",
    "baseline_source_action_space": "regime_participation",
    "baseline_noop_path_declared": true,
    "baseline_final_equity": 3418857.97,
    "action_space_final_equity": 7598148.48,
    "excess_final_equity": 4179290.51,
    "baseline_net_return_after_fee_tax": 2.41885797,
    "action_space_net_return_after_fee_tax": 6.59814848,
    "excess_net_return_after_fee_tax": 4.17929051,
    "baseline_fee_and_tax": 549665.29,
    "action_space_fee_and_tax": 422398.3,
    "fee_tax_delta": -127266.99,
    "baseline_turnover_proxy": 87.37059302,
    "action_space_turnover_proxy": 43.7119179,
    "turnover_delta": -43.65867512,
    "baseline_action_count": 885,
    "action_space_action_count": 446,
    "action_count_delta": -439,
    "baseline_skip_count": 26,
    "action_space_skip_count": 481,
    "skip_count_delta": 455,
    "primary_gate_metric": "full_path_excess_net_return_after_fee_tax",
    "event_delta_used_as_primary_gate": false,
    "readonly_simulation_only": true
  },
  {
    "split": "validation",
    "action_space": "hold_continuation",
    "baseline_source_action_space": "regime_participation",
    "baseline_noop_path_declared": true,
    "baseline_final_equity": 1953767.53,
    "action_space_final_equity": 2526314.28,
    "excess_final_equity": 572546.75,
    "baseline_net_return_after_fee_tax": 0.95376753,
    "action_space_net_return_after_fee_tax": 1.52631428,
    "excess_net_return_after_fee_tax": 0.57254675,
    "baseline_fee_and_tax": 146214.73,
    "action_space_fee_and_tax": 91880.4,
    "fee_tax_delta": -54334.33,
    "baseline_turnover_proxy": 42.18778217,
    "action_space_turnover_proxy": 22.72045491,
    "turnover_delta": -19.46732726,
    "baseline_action_count": 436,
    "action_space_action_count": 230,
    "action_count_delta": -206,
    "baseline_skip_count": 12,
    "action_space_skip_count": 216,
    "skip_count_delta": 204,
    "primary_gate_metric": "full_path_excess_net_return_after_fee_tax",
    "event_delta_used_as_primary_gate": false,
    "readonly_simulation_only": true
  },
  {
    "split": "train",
    "action_space": "regime_participation",
    "baseline_source_action_space": "regime_participation",
    "baseline_noop_path_declared": true,
    "baseline_final_equity": 3418857.97,
    "action_space_final_equity": 3418857.97,
    "excess_final_equity": 0.0,
    "baseline_net_return_after_fee_tax": 2.41885797,
    "action_space_net_return_after_fee_tax": 2.41885797,
    "excess_net_return_after_fee_tax": 0.0,
    "baseline_fee_and_tax": 549665.29,
    "action_space_fee_and_tax": 549665.29,
    "fee_tax_delta": 0.0,
    "baseline_turnover_proxy": 87.37059302,
    "action_space_turnover_proxy": 87.37059302,
    "turnover_delta": 0.0,
    "baseline_action_count": 885,
    "action_space_action_count": 885,
    "action_count_delta": 0,
    "baseline_skip_count": 26,
    "action_space_skip_count": 26,
    "skip_count_delta": 0,
    "primary_gate_metric": "full_path_excess_net_return_after_fee_tax",
    "event_delta_used_as_primary_gate": false,
    "readonly_simulation_only": true
  },
  {
    "split": "validation",
    "action_space": "regime_participation",
    "baseline_source_action_space": "regime_participation",
    "baseline_noop_path_declared": true,
    "baseline_final_equity": 1953767.53,
    "action_space_final_equity": 1953767.53,
    "excess_final_equity": 0.0,
    "baseline_net_return_after_fee_tax": 0.95376753,
    "action_space_net_return_after_fee_tax": 0.95376753,
    "excess_net_return_after_fee_tax": 0.0,
    "baseline_fee_and_tax": 146214.73,
    "action_space_fee_and_tax": 146214.73,
    "fee_tax_delta": 0.0,
    "baseline_turnover_proxy": 42.18778217,
    "action_space_turnover_proxy": 42.18778217,
    "turnover_delta": 0.0,
    "baseline_action_count": 436,
    "action_space_action_count": 436,
    "action_count_delta": 0,
    "baseline_skip_count": 12,
    "action_space_skip_count": 12,
    "skip_count_delta": 0,
    "primary_gate_metric": "full_path_excess_net_return_after_fee_tax",
    "event_delta_used_as_primary_gate": false,
    "readonly_simulation_only": true
  }
]
```

## 4. Direction / Cost / Concentration

```json
{
  "direction": [
    {
      "action_space": "hold_continuation",
      "train_excess_net_return_after_fee_tax": 4.17929051,
      "validation_excess_net_return_after_fee_tax": 0.57254675,
      "train_excess_final_equity": 4179290.51,
      "validation_excess_final_equity": 572546.75,
      "train_positive": true,
      "validation_positive": true,
      "direction_consistency_status": "pass",
      "sample_count_train": "",
      "sample_count_validation": "",
      "not_cash_no_trade": true,
      "not_baseline_clone": true,
      "eligible_for_reviewer_to_consider_fpa3_work_doc": true,
      "primary_gate_source": "full_path_metric_reconciliation.csv",
      "event_delta_used_as_primary_gate": false
    },
    {
      "action_space": "regime_participation",
      "train_excess_net_return_after_fee_tax": 0.0,
      "validation_excess_net_return_after_fee_tax": 0.0,
      "train_excess_final_equity": 0.0,
      "validation_excess_final_equity": 0.0,
      "train_positive": false,
      "validation_positive": false,
      "direction_consistency_status": "fail_no_stable_full_path_positive_excess",
      "sample_count_train": "",
      "sample_count_validation": "",
      "not_cash_no_trade": true,
      "not_baseline_clone": false,
      "eligible_for_reviewer_to_consider_fpa3_work_doc": false,
      "primary_gate_source": "full_path_metric_reconciliation.csv",
      "event_delta_used_as_primary_gate": false
    },
    {
      "action_space": "replacement_buy",
      "train_excess_net_return_after_fee_tax": 25.554525,
      "validation_excess_net_return_after_fee_tax": 2.80874585,
      "train_excess_final_equity": 25554525.0,
      "validation_excess_final_equity": 2808745.85,
      "train_positive": true,
      "validation_positive": true,
      "direction_consistency_status": "pass",
      "sample_count_train": "",
      "sample_count_validation": "",
      "not_cash_no_trade": true,
      "not_baseline_clone": true,
      "eligible_for_reviewer_to_consider_fpa3_work_doc": true,
      "primary_gate_source": "full_path_metric_reconciliation.csv",
      "event_delta_used_as_primary_gate": false
    },
    {
      "action_space": "sell_timing",
      "train_excess_net_return_after_fee_tax": 5.58416295,
      "validation_excess_net_return_after_fee_tax": 0.24722808,
      "train_excess_final_equity": 5584162.95,
      "validation_excess_final_equity": 247228.08,
      "train_positive": true,
      "validation_positive": true,
      "direction_consistency_status": "pass",
      "sample_count_train": "",
      "sample_count_validation": "",
      "not_cash_no_trade": true,
      "not_baseline_clone": true,
      "eligible_for_reviewer_to_consider_fpa3_work_doc": true,
      "primary_gate_source": "full_path_metric_reconciliation.csv",
      "event_delta_used_as_primary_gate": false
    }
  ],
  "cost": [
    {
      "action_space": "hold_continuation",
      "train_fee_tax_delta": -127266.99,
      "validation_fee_tax_delta": -54334.33,
      "train_turnover_delta": -43.65867512,
      "validation_turnover_delta": -19.46732726,
      "train_net_excess_after_fee_tax": 4.17929051,
      "validation_net_excess_after_fee_tax": 0.57254675,
      "cost_covered_train": true,
      "cost_covered_validation": true,
      "cost_covered": true,
      "cost_audit_source": "full_path_metric_reconciliation.csv",
      "event_delta_used_as_primary_gate": false
    },
    {
      "action_space": "regime_participation",
      "train_fee_tax_delta": 0.0,
      "validation_fee_tax_delta": 0.0,
      "train_turnover_delta": 0.0,
      "validation_turnover_delta": 0.0,
      "train_net_excess_after_fee_tax": 0.0,
      "validation_net_excess_after_fee_tax": 0.0,
      "cost_covered_train": false,
      "cost_covered_validation": false,
      "cost_covered": false,
      "cost_audit_source": "full_path_metric_reconciliation.csv",
      "event_delta_used_as_primary_gate": false
    },
    {
      "action_space": "replacement_buy",
      "train_fee_tax_delta": 1233395.24,
      "validation_fee_tax_delta": 108352.49,
      "train_turnover_delta": -12.22714217,
      "validation_turnover_delta": -0.73571237,
      "train_net_excess_after_fee_tax": 25.554525,
      "validation_net_excess_after_fee_tax": 2.80874585,
      "cost_covered_train": true,
      "cost_covered_validation": true,
      "cost_covered": true,
      "cost_audit_source": "full_path_metric_reconciliation.csv",
      "event_delta_used_as_primary_gate": false
    },
    {
      "action_space": "sell_timing",
      "train_fee_tax_delta": 123273.39,
      "validation_fee_tax_delta": -14871.15,
      "train_turnover_delta": -24.35612471,
      "validation_turnover_delta": -8.95511365,
      "train_net_excess_after_fee_tax": 5.58416295,
      "validation_net_excess_after_fee_tax": 0.24722808,
      "cost_covered_train": true,
      "cost_covered_validation": true,
      "cost_covered": true,
      "cost_audit_source": "full_path_metric_reconciliation.csv",
      "event_delta_used_as_primary_gate": false
    }
  ],
  "concentration": [
    {
      "action_space": "hold_continuation",
      "concentration_scope": "event_attribution_auxiliary",
      "not_primary_full_path_gate": true,
      "primary_gate_source": "full_path_metric_reconciliation.csv",
      "full_path_positive_excess_train_validation": true,
      "event_top_symbol_contribution_share": "0.10849625",
      "event_top_date_contribution_share": "0.02898812",
      "event_top_5_symbol_contribution_share": "0.34543199",
      "event_top_5_date_contribution_share": "0.121685",
      "event_concentration_gate_status": "pass",
      "concentration_gate_status": "auxiliary_pass_not_primary_gate"
    },
    {
      "action_space": "regime_participation",
      "concentration_scope": "event_attribution_auxiliary",
      "not_primary_full_path_gate": true,
      "primary_gate_source": "full_path_metric_reconciliation.csv",
      "full_path_positive_excess_train_validation": false,
      "event_top_symbol_contribution_share": "0.0",
      "event_top_date_contribution_share": "0.0",
      "event_top_5_symbol_contribution_share": "0.0",
      "event_top_5_date_contribution_share": "0.0",
      "event_concentration_gate_status": "review_required_or_no_positive_delta",
      "concentration_gate_status": "auxiliary_review_required_or_no_positive_delta"
    },
    {
      "action_space": "replacement_buy",
      "concentration_scope": "event_attribution_auxiliary",
      "not_primary_full_path_gate": true,
      "primary_gate_source": "full_path_metric_reconciliation.csv",
      "full_path_positive_excess_train_validation": true,
      "event_top_symbol_contribution_share": "0.04370199",
      "event_top_date_contribution_share": "0.00480992",
      "event_top_5_symbol_contribution_share": "0.18549883",
      "event_top_5_date_contribution_share": "0.02145602",
      "event_concentration_gate_status": "pass",
      "concentration_gate_status": "auxiliary_pass_not_primary_gate"
    },
    {
      "action_space": "sell_timing",
      "concentration_scope": "event_attribution_auxiliary",
      "not_primary_full_path_gate": true,
      "primary_gate_source": "full_path_metric_reconciliation.csv",
      "full_path_positive_excess_train_validation": true,
      "event_top_symbol_contribution_share": "0.0914329",
      "event_top_date_contribution_share": "0.03247066",
      "event_top_5_symbol_contribution_share": "0.31401296",
      "event_top_5_date_contribution_share": "0.14770813",
      "event_concentration_gate_status": "pass",
      "concentration_gate_status": "auxiliary_pass_not_primary_gate"
    }
  ]
}
```

## 5. Validator Summary

```json
{
  "ok": true,
  "status": "PASS_FPA2_R_FULL_PATH_METRIC_RECONCILIATION_REPAIR_READY_FOR_REVIEW",
  "phase": "RAL_FPA2_R_FULL_PATH_METRIC_RECONCILIATION_REPAIR",
  "failed_count": 0,
  "final_recommendation": "READY_FOR_REVIEWER_TO_CONSIDER_FPA3_WORK_DOC"
}
```

## 6. Final Recommendation

```text
READY_FOR_REVIEWER_TO_CONSIDER_FPA3_WORK_DOC
```
