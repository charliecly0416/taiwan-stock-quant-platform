---
created_at: 2026-06-23T11:51:46+00:00
status: pass_ready_for_review
phase: RAL_FPA4_PREDECLARED_FULL_PATH_RULE_SANITY
artifact_root: data_tw/experiments/full_path_action_diagnostic/fpa4_predeclared_full_path_rule_sanity
readonly_only: true
simulation_only: true
production_allowed: false
---

# RAL-FPA4 Predeclared Full-path Rule Sanity 执行报告

## 1. Scope

本轮只测试工作文档预声明的 5 个 candidate / 7 个固定 threshold versions。strict_test_used = false；model_training_run = false；production_allowed = false；OrderIntent_output = false；target_weight_output = false；target_position_output = false；quantity_or_broker_output = false。

## 2. Outputs

输出目录：`data_tw/experiments/full_path_action_diagnostic/fpa4_predeclared_full_path_rule_sanity`

## 3. Candidate Pass Summary

```json
[
  {
    "split": "validation",
    "candidate_id": "FPA4_C01",
    "threshold_version": "rank_lte_25",
    "action_space": "replacement_buy",
    "final_equity": 2206129.54,
    "net_return_after_fee_tax": 1.20612954,
    "net_return_if_liquidated_at_period_end": 1.19731755,
    "max_drawdown": -0.34171353,
    "turnover_proxy": 42.37199884,
    "fee_and_tax": 156541.69,
    "action_count": 437,
    "buy_count": 223,
    "sell_count": 214,
    "skip_count": 15,
    "average_cash_rate": 0.16150809,
    "max_holding_count": 10,
    "missing_price_count": 0,
    "negative_cash_count": 0,
    "excess_net_return_after_fee_tax_vs_baseline": 0.25236201,
    "not_baseline_clone": true,
    "not_cash_no_trade": true,
    "rolling_oos_mean_excess": 0.00804079,
    "rolling_oos_median_excess": 0.03890537,
    "window_count": 3,
    "all_windows": "2023:-0.26714501|2024:0.03890537|2025:0.25236201",
    "candidate_pass": false
  },
  {
    "split": "validation",
    "candidate_id": "FPA4_C01",
    "threshold_version": "rank_lte_50",
    "action_space": "replacement_buy",
    "final_equity": 2206129.54,
    "net_return_after_fee_tax": 1.20612954,
    "net_return_if_liquidated_at_period_end": 1.19731755,
    "max_drawdown": -0.34171353,
    "turnover_proxy": 42.37199884,
    "fee_and_tax": 156541.69,
    "action_count": 437,
    "buy_count": 223,
    "sell_count": 214,
    "skip_count": 15,
    "average_cash_rate": 0.16150809,
    "max_holding_count": 10,
    "missing_price_count": 0,
    "negative_cash_count": 0,
    "excess_net_return_after_fee_tax_vs_baseline": 0.25236201,
    "not_baseline_clone": true,
    "not_cash_no_trade": true,
    "rolling_oos_mean_excess": 0.00804079,
    "rolling_oos_median_excess": 0.03890537,
    "window_count": 3,
    "all_windows": "2023:-0.26714501|2024:0.03890537|2025:0.25236201",
    "candidate_pass": false
  },
  {
    "split": "validation",
    "candidate_id": "FPA4_C02",
    "threshold_version": "unrealized_gain_large",
    "action_space": "hold_continuation",
    "final_equity": 1951325.45,
    "net_return_after_fee_tax": 0.95132545,
    "net_return_if_liquidated_at_period_end": 0.94270603,
    "max_drawdown": -0.37662134,
    "turnover_proxy": 23.39671549,
    "fee_and_tax": 79508.29,
    "action_count": 252,
    "buy_count": 131,
    "sell_count": 121,
    "skip_count": 184,
    "average_cash_rate": 0.07000009,
    "max_holding_count": 10,
    "missing_price_count": 0,
    "negative_cash_count": 0,
    "excess_net_return_after_fee_tax_vs_baseline": -0.00244208,
    "not_baseline_clone": true,
    "not_cash_no_trade": true,
    "rolling_oos_mean_excess": 0.19604424,
    "rolling_oos_median_excess": 0.13600263,
    "window_count": 3,
    "all_windows": "2023:0.13600263|2024:0.45457217|2025:-0.00244208",
    "candidate_pass": false
  },
  {
    "split": "validation",
    "candidate_id": "FPA4_C03",
    "threshold_version": "unrealized_loss_large",
    "action_space": "hold_continuation",
    "final_equity": 1643074.89,
    "net_return_after_fee_tax": 0.64307489,
    "net_return_if_liquidated_at_period_end": 0.6358109,
    "max_drawdown": -0.37291349,
    "turnover_proxy": 29.41804276,
    "fee_and_tax": 92368.9,
    "action_count": 302,
    "buy_count": 156,
    "sell_count": 146,
    "skip_count": 137,
    "average_cash_rate": 0.0746872,
    "max_holding_count": 10,
    "missing_price_count": 0,
    "negative_cash_count": 0,
    "excess_net_return_after_fee_tax_vs_baseline": -0.31069264,
    "not_baseline_clone": true,
    "not_cash_no_trade": true,
    "rolling_oos_mean_excess": 0.11331458,
    "rolling_oos_median_excess": 0.30680016,
    "window_count": 3,
    "all_windows": "2023:0.30680016|2024:0.34383622|2025:-0.31069264",
    "candidate_pass": false
  },
  {
    "split": "validation",
    "candidate_id": "FPA4_C04",
    "threshold_version": "unrealized_gain_large",
    "action_space": "sell_timing",
    "final_equity": 1940186.33,
    "net_return_after_fee_tax": 0.94018633,
    "net_return_if_liquidated_at_period_end": 0.93237564,
    "max_drawdown": -0.38613364,
    "turnover_proxy": 33.10765181,
    "fee_and_tax": 113260.15,
    "action_count": 341,
    "buy_count": 175,
    "sell_count": 166,
    "skip_count": 113,
    "average_cash_rate": 0.0901156,
    "max_holding_count": 10,
    "missing_price_count": 0,
    "negative_cash_count": 0,
    "excess_net_return_after_fee_tax_vs_baseline": -0.0135812,
    "not_baseline_clone": true,
    "not_cash_no_trade": true,
    "rolling_oos_mean_excess": 0.11798511,
    "rolling_oos_median_excess": 0.09104063,
    "window_count": 3,
    "all_windows": "2023:0.09104063|2024:0.27649591|2025:-0.0135812",
    "candidate_pass": false
  },
  {
    "split": "validation",
    "candidate_id": "FPA4_C05",
    "threshold_version": "holding_days_005_019",
    "action_space": "sell_timing",
    "final_equity": 1665428.23,
    "net_return_after_fee_tax": 0.66542823,
    "net_return_if_liquidated_at_period_end": 0.65807379,
    "max_drawdown": -0.36712005,
    "turnover_proxy": 30.87020827,
    "fee_and_tax": 95215.77,
    "action_count": 328,
    "buy_count": 169,
    "sell_count": 159,
    "skip_count": 135,
    "average_cash_rate": 0.07325798,
    "max_holding_count": 10,
    "missing_price_count": 0,
    "negative_cash_count": 0,
    "excess_net_return_after_fee_tax_vs_baseline": -0.2883393,
    "not_baseline_clone": true,
    "not_cash_no_trade": true,
    "rolling_oos_mean_excess": 0.04960762,
    "rolling_oos_median_excess": -0.18939192,
    "window_count": 3,
    "all_windows": "2023:-0.18939192|2024:0.62655408|2025:-0.2883393",
    "candidate_pass": false
  },
  {
    "split": "validation",
    "candidate_id": "FPA4_C05",
    "threshold_version": "holding_days_020_059",
    "action_space": "sell_timing",
    "final_equity": 1977113.26,
    "net_return_after_fee_tax": 0.97711326,
    "net_return_if_liquidated_at_period_end": 0.96838041,
    "max_drawdown": -0.40521322,
    "turnover_proxy": 33.14860442,
    "fee_and_tax": 113700.32,
    "action_count": 344,
    "buy_count": 177,
    "sell_count": 167,
    "skip_count": 104,
    "average_cash_rate": 0.09951067,
    "max_holding_count": 10,
    "missing_price_count": 0,
    "negative_cash_count": 0,
    "excess_net_return_after_fee_tax_vs_baseline": 0.02334573,
    "not_baseline_clone": true,
    "not_cash_no_trade": true,
    "rolling_oos_mean_excess": -0.00552364,
    "rolling_oos_median_excess": 0.02334573,
    "window_count": 3,
    "all_windows": "2023:-0.10797663|2024:0.06805999|2025:0.02334573",
    "candidate_pass": false
  }
]
```

## 4. Validator Summary

```json
{
  "ok": true,
  "status": "PASS_FPA4_PREDECLARED_FULL_PATH_RULE_SANITY_READY_FOR_REVIEW",
  "phase": "RAL_FPA4_PREDECLARED_FULL_PATH_RULE_SANITY",
  "failed_count": 0,
  "final_recommendation": "STOP_NO_PREDECLARED_RULE_SANITY_PASS"
}
```

## 5. Final Recommendation

```text
STOP_NO_PREDECLARED_RULE_SANITY_PASS
```
