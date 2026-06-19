# Phase A1 执行报告：Phase1C Anchor 精确复刻与只读审计

生成时间：2026-06-15T05:58:25+00:00

## 1. 执行边界

- 本轮只读取既有 Phase1C / Phase3A0 / S2F 产物，并使用 S2F 原 `PriceStore` 本地 normalized price 源补充持仓 PnL 审计。
- 未训练 qlib，未训练 LTR，未改窗口、feature、label、score column、费用税费、持仓数量或 next-day execution 口径。
- 未使用 Q0/L1-L4、T2/T2R 或 `tw_qlib_oos_ltr_stacking` 产物作为 A1 输入。
- 未触发 provider / accepted latest / monitor / broker / orders / quick-trade / frontend / API 链路。

固定窗口：`2025-07-01..2026-05-07`。

## 2. Anchor Identity Audit

| field | expected | actual | pass |
| --- | --- | --- | --- |
| candidate_id | head10_all_l31_alpha0.7_top50_only | head10_all_l31_alpha0.7_top50_only | yes |
| model_id | head10_all_l31 | head10_all_l31 | yes |
| score_column | score_head10_all_l31_alpha0.7_top50_only | score_head10_all_l31_alpha0.7_top50_only | yes |
| blend_alpha | 0.7 | 0.7 | yes |
| preserve_scope | top50_only | top50_only | yes |
| label_col | relevance_10d_top_heavy | relevance_10d_top_heavy | yes |
| num_leaves | 31 | 31 | yes |
| learning_rate | 0.03 | 0.03 | yes |
| n_estimators | 120 | 120 | yes |
| random_state | 42 | 42 | yes |

## 3. Score Reproduction Audit

| row_count | score_column | metric_rows | max_absolute_difference | mean_absolute_difference | tolerance | pass |
| --- | --- | --- | --- | --- | --- | --- |
| 152249 | score_head10_all_l31_alpha0.7_top50_only | 24 | 4.440892098500626e-16 | 4.192248400277284e-17 | 0.0007 | yes |

## 4. Full Universe Metrics

| method | fee_tax_adjusted_net_return | expected_fee_tax_adjusted_net_return | diff_fee_tax_adjusted_net_return | max_drawdown | expected_max_drawdown | diff_max_drawdown | action_count | expected_action_count | diff_action_count | pass |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| old_qlib_new_ltr_phase1c_simple | 0.721631 | 0.721631 | 0.0 | -0.05083 | -0.05083 | 0.0 | 405 | 405 | 0 | yes |
| fresh_qlib_top50_adaptive_baseline | 0.662457 | 0.662457 | 0.0 | -0.088396 | -0.088396 | 0.0 | 410 | 410 | 0 | yes |
| fresh_ltr_simple | 0.544381 | 0.544381 | 0.0 | -0.132896 | -0.132896 | 0.0 | 408 | 408 | 0 | yes |
| fresh_ltr_turnover_controlled | 0.615059 | 0.615059 | 0.0 | -0.11131 | -0.11131 | 0.0 | 63 | 63 | 0 | yes |

## 5. Common Universe Metrics

- common universe key 数量：`22474`。
- common universe 过滤后，old Phase1C anchor return 从 `0.721631` 变为 `0.641235`，差值 `-0.080396`；动作数仍为 `405`。

| method | fee_tax_adjusted_net_return | expected_fee_tax_adjusted_net_return | diff_fee_tax_adjusted_net_return | max_drawdown | expected_max_drawdown | diff_max_drawdown | action_count | expected_action_count | diff_action_count | pass |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| old_qlib_new_ltr_phase1c_simple | 0.641235 | 0.641235 | 0.0 | -0.076739 | -0.076739 | 0.0 | 405 | 405 | 0 | yes |
| fresh_qlib_top50_adaptive_baseline | 0.625943 | 0.625943 | 0.0 | -0.088431 | -0.088431 | 0.0 | 410 | 410 | 0 | yes |
| fresh_ltr_simple | 0.544381 | 0.544381 | 0.0 | -0.132896 | -0.132896 | 0.0 | 408 | 408 | 0 | yes |
| fresh_ltr_turnover_controlled | 0.615059 | 0.615059 | 0.0 | -0.11131 | -0.11131 | 0.0 | 63 | 63 | 0 | yes |

## 6. Next-day Accounting Audit

| method | active_action_count | execution_date_after_signal_date | execution_date_not_after_signal_violations | effective_nav_date_on_or_after_execution_date | missing_price_days | skipped_trade_count | last_day_new_trade_without_next_price_count | pass |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| old_qlib_new_ltr_phase1c_simple | 405 | True | 0 | True | 0 | 0 | 0 | yes |

## 7. Real PnL Contribution

Top contribution symbols：

| symbol | realized_pnl | unrealized_pnl | fee_tax_allocated | net_pnl | share_of_total_net_pnl |
| --- | --- | --- | --- | --- | --- |
| TW3163 | 118210.0 | 0.0 | 5952.77 | 112257.23 | 0.15556 |
| TW2344 | 87042.22 | 0.0 | 2589.96 | 84452.26 | 0.11703 |
| TW3081 | 72000.0 | 0.0 | 4203.22 | 67796.78 | 0.093949 |
| TW4971 | 59580.0 | 0.0 | 4829.7 | 54750.3 | 0.07587 |
| TW8996 | 49660.79 | 0.0 | 2377.99 | 47282.8 | 0.065522 |
| TW8358 | 48722.29 | 0.0 | 2266.0 | 46456.29 | 0.064377 |
| TW4919 | 3630.0 | 37440.0 | 1259.42 | 39810.58 | 0.055168 |
| TW3715 | 39069.0 | 0.0 | 2298.81 | 36770.19 | 0.050954 |
| TW3167 | 35597.5 | 0.0 | 3716.73 | 31880.77 | 0.044179 |
| TW6415 | 13660.17 | 13545.0 | 1104.99 | 26100.18 | 0.036168 |

Worst contribution symbols：

| symbol | realized_pnl | unrealized_pnl | fee_tax_allocated | net_pnl | share_of_total_net_pnl |
| --- | --- | --- | --- | --- | --- |
| TW3693 | -24890.0 | 0.0 | 1517.51 | -26407.51 | -0.036594 |
| TW2467 | -21245.0 | 0.0 | 3367.8 | -24612.8 | -0.034107 |
| TW8039 | -15485.0 | 0.0 | 3180.67 | -18665.67 | -0.025866 |
| TW6147 | -16324.0 | 0.0 | 819.47 | -17143.47 | -0.023757 |
| TW2451 | -12845.0 | 0.0 | 3025.72 | -15870.72 | -0.021993 |
| TW3260 | -12308.11 | 0.0 | 755.22 | -13063.33 | -0.018103 |
| TW2481 | -11069.1 | 0.0 | 1376.5 | -12445.6 | -0.017246 |
| TW6187 | -11050.0 | 0.0 | 875.11 | -11925.11 | -0.016525 |
| TW2368 | -8660.0 | 0.0 | 1445.34 | -10105.34 | -0.014003 |
| TW6488 | -9195.26 | 0.0 | 664.89 | -9860.15 | -0.013664 |

Top contribution days：

| date | realized_pnl | unrealized_pnl | fee_tax_allocated | net_pnl | share_of_total_net_pnl |
| --- | --- | --- | --- | --- | --- |
| 2026-02-25 | 81760.0 | 33740.0 | 1177.8 | 114322.2 | 0.158422 |
| 2025-07-28 | 75356.96 | 36550.65 | 2300.75 | 109606.86 | 0.151888 |
| 2026-04-16 | 41390.0 | 35890.0 | 1743.36 | 75536.64 | 0.104675 |
| 2026-04-14 | 78250.0 | -1415.0 | 2532.38 | 74302.62 | 0.102965 |
| 2026-04-17 | 34410.0 | 29980.0 | 1122.21 | 63267.79 | 0.087673 |
| 2026-01-19 | 36120.0 | 26039.99 | 1553.7 | 60606.29 | 0.083985 |
| 2025-12-10 | 40635.0 | 19056.0 | 913.09 | 58777.91 | 0.081451 |
| 2025-10-15 | 21870.0 | 37108.87 | 1350.34 | 57628.53 | 0.079859 |
| 2026-04-01 | 17953.0 | 35314.01 | 1627.82 | 51639.19 | 0.071559 |
| 2025-11-05 | 50901.08 | 461.86 | 1459.87 | 49903.08 | 0.069153 |

## 8. 异常审计

| audit_item | value | threshold | status | note |
| --- | --- | --- | --- | --- |
| top_symbol_abs_share_of_total_net_pnl | 0.15556 | 0.35 | ok | absolute share by single symbol |
| top_day_abs_share_of_total_net_pnl | 0.158422 | 0.35 | ok | absolute share by single day |
| max_abs_daily_nav_return | 0.031448 | 0.12 | ok | largest absolute daily equity return from S2F daily NAV |
| pnl_contribution_total_vs_nav_gain | -0.03 | 1.0 | ok | symbol-level net PnL sum minus S2F final equity gain |
| large_daily_nav_return_sample | 0.031448 |  | info | 2025-07-28 |
| large_daily_nav_return_sample | 0.029572 |  | info | 2025-10-15 |
| large_daily_nav_return_sample | -0.028682 |  | info | 2025-11-21 |
| large_daily_nav_return_sample | -0.026633 |  | info | 2026-03-31 |
| large_daily_nav_return_sample | -0.026385 |  | info | 2025-11-14 |
| large_daily_nav_return_sample | 0.025968 |  | info | 2025-08-07 |
| large_daily_nav_return_sample | 0.024945 |  | info | 2026-04-10 |
| large_daily_nav_return_sample | 0.022785 |  | info | 2026-04-01 |
| large_daily_nav_return_sample | 0.022757 |  | info | 2025-08-21 |
| large_daily_nav_return_sample | -0.021823 |  | info | 2025-12-16 |

结论：Phase1C anchor identity 与 row-level score reproduction 均通过；S2F full/common universe 指标与冻结表逐项一致；next-day accounting 无违反项。PnL contribution 与 outlier 审计已补齐，仅作为历史只读 anchor 解释，不构成任何交易建议。

## 9. 输出产物

- `data_tw/experiments/phase1c_anchor_reproduction/phasea1_anchor_identity_audit.csv`
- `data_tw/experiments/phase1c_anchor_reproduction/phasea1_score_reproduction_audit.csv`
- `data_tw/experiments/phase1c_anchor_reproduction/phasea1_anchor_metrics.csv`
- `data_tw/experiments/phase1c_anchor_reproduction/phasea1_common_universe_metrics.csv`
- `data_tw/experiments/phase1c_anchor_reproduction/phasea1_next_day_accounting_audit.csv`
- `data_tw/experiments/phase1c_anchor_reproduction/phasea1_real_pnl_contribution_by_symbol.csv`
- `data_tw/experiments/phase1c_anchor_reproduction/phasea1_real_pnl_contribution_by_day.csv`
- `data_tw/experiments/phase1c_anchor_reproduction/phasea1_outlier_audit.csv`
- `data_tw/experiments/phase1c_anchor_reproduction/phasea1_anchor_summary.json`
