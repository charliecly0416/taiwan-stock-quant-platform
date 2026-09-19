---
created_at: 2026-06-23T10:49:46+00:00
status: pass_ready_for_review
phase: RAL_FPA2_ORACLE_UPPER_BOUND_DIAGNOSTIC
artifact_root: data_tw/experiments/full_path_action_diagnostic/fpa2_oracle_upper_bound
readonly_only: true
simulation_only: true
production_allowed: false
---

# RAL-FPA2 Oracle-style Upper-bound Diagnostic 执行报告

## 1. Scope

本轮只执行 FPA2 oracle-style upper-bound diagnostic。FPA3 attribution run = false；FPA4 rule sanity run = false；strict_test_used = false；rule_selection_run = false；threshold_selection_run = false；model_training_run = false；production_allowed = false；OrderIntent_output = false；target_weight_output = false；target_position_output = false；quantity_or_broker_output = false。

## 2. Documents / Contracts Read

- `docs/tw_portfolio_decision_model/POLICY_RAL_FPA_FULL_PATH_BASELINE_PLUS_ACTION_DIAGNOSTIC_MAINLINE_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_RAL_FPA1_REPLAY_STATE_CONTRACT_REVIEW_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_RAL_FPA2_ORACLE_UPPER_BOUND_DIAGNOSTIC_WORK_CN.md`
- `data_tw/experiments/full_path_action_diagnostic/fpa1_replay_state_contract/full_path_replay_state_contract.md`
- `scripts/run_tw_policy_action_model_pa1.py`

## 3. Source Code and Artifacts Inspected

- FPA1 contract artifacts under `data_tw/experiments/full_path_action_diagnostic/fpa1_replay_state_contract`
- ED2-A baseline audit artifacts under `data_tw/experiments/explicit_rule_discovery/ral_ed2_a_baseline_replay_accounting_audit`
- Signal manifest `data_tw/artifacts/signals/frozen_qlib_2018_2022/r1_legacy_signal_adapter_20260616/manifest.json`

## 4. Outputs Produced

输出目录：`data_tw/experiments/full_path_action_diagnostic/fpa2_oracle_upper_bound`

关键文件包括 work doc 要求的 upper-bound、lineage、cost、concentration、direction、leakage、forbidden consumer、validator 和 findings artifacts。

## 5. Four Action-space Diagnostic Summary

```json
[
  {
    "action_space": "replacement_buy",
    "event_count": 723,
    "gross_delta": 2810905.5745,
    "fee_tax_delta": 0.0,
    "turnover_delta": 706.0,
    "net_delta_after_fee_tax": 2810905.5745,
    "cost_covered": true,
    "train_baseline_return": 2.41885797,
    "validation_baseline_return": 0.95376753
  },
  {
    "action_space": "sell_timing",
    "event_count": 654,
    "gross_delta": 1545447.7511,
    "fee_tax_delta": 0.0,
    "turnover_delta": 0.0,
    "net_delta_after_fee_tax": 1545447.7511,
    "cost_covered": true
  },
  {
    "action_space": "hold_continuation",
    "event_count": 654,
    "gross_delta": 6187074.7401,
    "fee_tax_delta": 0.0,
    "turnover_delta": 0.0,
    "net_delta_after_fee_tax": 6187074.7401,
    "cost_covered": true
  },
  {
    "action_space": "regime_participation",
    "event_count": 723,
    "gross_delta": 0.0,
    "fee_tax_delta": 0.0,
    "turnover_delta": 0.0,
    "net_delta_after_fee_tax": 0.0,
    "cost_covered": false
  }
]
```

## 6. Transaction Cost and Concentration Summary

```json
{
  "transaction_cost": [
    {
      "action_space": "replacement_buy",
      "gross_delta": 2810905.5745,
      "fee_tax_delta": 0.0,
      "turnover_delta": 706.0,
      "net_delta_after_fee_tax": 2810905.5745,
      "cost_covered": true
    },
    {
      "action_space": "sell_timing",
      "gross_delta": 1545447.7511,
      "fee_tax_delta": 0.0,
      "turnover_delta": 0.0,
      "net_delta_after_fee_tax": 1545447.7511,
      "cost_covered": true
    },
    {
      "action_space": "hold_continuation",
      "gross_delta": 6187074.7401,
      "fee_tax_delta": 0.0,
      "turnover_delta": 0.0,
      "net_delta_after_fee_tax": 6187074.7401,
      "cost_covered": true
    },
    {
      "action_space": "regime_participation",
      "gross_delta": 0.0,
      "fee_tax_delta": 0.0,
      "turnover_delta": 0.0,
      "net_delta_after_fee_tax": 0.0,
      "cost_covered": false
    }
  ],
  "concentration": [
    {
      "action_space": "hold_continuation",
      "positive_net_delta": 10975855.7585,
      "top_symbol_contribution_share": 0.04829843,
      "top_date_contribution_share": 0.03133249,
      "top_5_symbol_contribution_share": 0.21625098,
      "top_5_date_contribution_share": 0.0893107,
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
      "positive_net_delta": 4849722.4739,
      "top_symbol_contribution_share": 0.05533686,
      "top_date_contribution_share": 0.03292318,
      "top_5_symbol_contribution_share": 0.22172425,
      "top_5_date_contribution_share": 0.12580159,
      "concentration_gate_status": "pass"
    }
  ]
}
```

## 7. Oracle Leakage Boundary Summary

所有 action_space 均标记 `oracle_diagnostic_only=true`、`not_rule_candidate=true`、`not_tradable_strategy=true`、`strict_test_used=false`。

## 8. Forbidden Consumer Audit Summary

全部禁用 consumer/action 均为 `allowed_in_fpa2=false` 且 `present_in_outputs=false`。`quantity/cash/nav/execution_price` 只作为 readonly internal replay accounting lineage 字段出现，不作为策略、OrderIntent、target、broker 或 production output。

## 9. Validator Summary

```json
{
  "ok": true,
  "status": "PASS_FPA2_ORACLE_UPPER_BOUND_READY_FOR_REVIEW",
  "phase": "RAL_FPA2_ORACLE_UPPER_BOUND_DIAGNOSTIC",
  "failed_count": 0,
  "final_recommendation": "READY_FOR_REVIEWER_TO_CONSIDER_FPA3_WORK_DOC"
}
```

## 10. Final Recommendation

```text
READY_FOR_REVIEWER_TO_CONSIDER_FPA3_WORK_DOC
```
