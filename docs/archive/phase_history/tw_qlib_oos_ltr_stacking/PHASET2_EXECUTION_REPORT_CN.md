# Phase T2 LTR Stacking 训练与同窗口只读回放执行报告

生成日期：2026-06-15

## 1. 执行结论

本轮按 `docs/tw_qlib_oos_ltr_stacking/PHASET2_WORKDOC_CN.md` 执行 Phase T2：先冻结 final test 推理期 score/feature 合同，再基于 T1 样本训练 Q0/L1-L4 LTR stacking 模型，并在 `2025-07-01..2026-05-07` 做只读历史回放。

结论：`T2 可提交审查，但不建议进入 T3 默认候选`。

原因：

- final test 上 `old_frozen_t2_ltr_simple` 收益显著高于 fresh qlib/top50 adaptive，但最大回撤显著恶化；
- validation 窗口中 Q0/L1-L4 全部为负收益，最终选择的 Q0/L4 只是 validation 中亏损最小，final test 方向反转为大幅正收益，稳定性不足；
- turnover-controlled old/frozen stacked LTR 在 full/common universe 下均低于 fresh qlib/top50 adaptive；
- final test old/frozen 特征是 `phase3a0` old qlib score 与 S2C 同日历史技术/市场特征的 overlap 拼接，覆盖 `22523 / 30475` old score rows，不能包装成完整 old dynamic universe；
- 因此，本轮只能说明“方向值得继续审查”，不能作为默认化依据。

推荐 gate：

```text
phase_t2_review_required_do_not_promote_default
```

## 2. 边界与禁止事项

本轮执行内容：

- 训练本地 LightGBM ranker LTR stacking 模型；
- 只读历史回放 validation / final test；
- 输出 full overlap universe、common universe、年度/regime、费用税费、换手、回撤、贡献、异常日、过拟合与 feature importance 审计。

本轮未执行：

- 未改前端/API；
- 未切换默认策略；
- 未触发 provider refresh / publish；
- 未切换 accepted latest；
- 未触发 monitor config save / scan / alerts write；
- 未连接 broker、orders、quick-trade 或任何交易链路；
- 未输出真实交易指令、仓位建议、收益承诺、胜率或上涨概率语义。

## 3. 产物

输出目录：

```text
data_tw/experiments/tw_qlib_oos_ltr_stacking/phase_t2
```

主要产物：

```text
phase_t2_final_test_score_provenance.csv
phase_t2_ltr_model_registry.csv
phase_t2_window_matrix_results.csv
phase_t2_strategy_comparison_full_universe.csv
phase_t2_strategy_comparison_common_universe.csv
phase_t2_yearly_results.csv
phase_t2_regime_results.csv
phase_t2_turnover_fee_audit.csv
phase_t2_next_day_accounting_audit.csv
phase_t2_contribution_audit.csv
phase_t2_single_stock_outlier_audit.csv
phase_t2_overfit_audit.csv
phase_t2_feature_importance.csv
phase_t2_summary.json
```

## 4. Final Test Score / Feature Provenance

| score_window | qlib_train_start | qlib_train_end | score_source | usage | OOS_pass | old_score_rows | feature_overlap_rows | dates |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2025-07-01..2026-05-07 | 2015-05-04 | 2020-12-31 | phase3a0_frozen_phase1c_row_scores.csv qlib_score_raw/rank + S2C same-date historical features | inference_only | True | 30475 | 22523 | 205 |

判断：

- final test qlib score 使用 old/frozen `phase3a0_frozen_phase1c_row_scores.csv` 中的 `qlib_score_raw / qlib_rank`；
- qlib train end 为 `2020-12-31`，对 `2025-07-01..2026-05-07` 推理期 OOS 语义通过；
- 技术/流动性/TWII 特征来自 S2C 同日同票历史特征，final test label/收益未参与训练或模型选择；
- 覆盖限制：old score 原始行数 `30475`，可拼接完整 34-feature 的行数 `22523`。本报告中的 old/frozen T2 LTR 结果应解读为 overlap-feature universe，不得宣称完整 old universe。

## 5. LTR 窗口矩阵与选择

模型注册：

| window_id | ltr_train_start | ltr_train_end | train_rows | train_dates | validation_rows | validation_dates | model_path | feature_importance_qlib_related | feature_importance_total | qlib_importance_share |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Q0_L1_1y | 2023-06-15 | 2024-06-14 | 35006 | 243 | 34090 | 231 | data_tw/experiments/tw_qlib_oos_ltr_stacking/phase_t2/Q0_L1_1y_lgbm_ranker.pkl | 113 | 2400 | 0.047083 |
| Q0_L2_2y | 2022-06-15 | 2024-06-14 | 71095 | 487 | 34090 | 231 | data_tw/experiments/tw_qlib_oos_ltr_stacking/phase_t2/Q0_L2_2y_lgbm_ranker.pkl | 106 | 2400 | 0.044167 |
| Q0_L3_3y | 2021-06-15 | 2024-06-14 | 104953 | 732 | 34090 | 231 | data_tw/experiments/tw_qlib_oos_ltr_stacking/phase_t2/Q0_L3_3y_lgbm_ranker.pkl | 70 | 2400 | 0.029167 |
| Q0_L4_4y | 2020-06-15 | 2024-06-14 | 140638 | 974 | 34090 | 231 | data_tw/experiments/tw_qlib_oos_ltr_stacking/phase_t2/Q0_L4_4y_lgbm_ranker.pkl | 84 | 2400 | 0.035 |

Validation 窗口矩阵：

| window_id | fee_tax_adjusted_net_return | final_equity | max_drawdown | action_count | buy_count | sell_count | fee_and_tax | turnover_proxy_by_notional_over_avg_equity | turnover_notional | start_date | end_date | trading_days | initial_cash_or_equity_assumption | fee_rate | tax_rate | position_count_target | daily_nav_available_count | missing_price_days | skipped_trade_count | last_day_new_trade_without_next_price_count |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Q0_L4_4y | -0.130647 | 869352.81 | -0.344117 | 448 | 228 | 220 | 111003.25 | 44.345103 | 38306624.49 | 2024-07-01 | 2025-06-16 | 231 | 1000000.0 | 0.001425 | 0.003 | 10 | 231 | 0 | 0 | 0 |
| Q0_L1_1y | -0.170079 | 829921.15 | -0.351885 | 430 | 219 | 211 | 110881.51 | 42.927578 | 38265664.19 | 2024-07-01 | 2025-06-16 | 231 | 1000000.0 | 0.001425 | 0.003 | 10 | 231 | 0 | 0 | 0 |
| Q0_L2_2y | -0.233877 | 766122.62 | -0.350923 | 450 | 227 | 223 | 117267.71 | 44.085469 | 40304272.91 | 2024-07-01 | 2025-06-16 | 231 | 1000000.0 | 0.001425 | 0.003 | 10 | 231 | 0 | 0 | 0 |
| Q0_L3_3y | -0.299983 | 700016.85 | -0.414266 | 449 | 229 | 220 | 107945.5 | 44.596444 | 37320658.09 | 2024-07-01 | 2025-06-16 | 231 | 1000000.0 | 0.001425 | 0.003 | 10 | 231 | 0 | 0 | 0 |

选择规则：先看 validation 费用税费后收益，再看回撤；未使用 final test 选择窗口。

选择结果：`Q0_L4_4y`。

关键风险：validation 中所有 Q0/L1-L4 均为负收益，说明 LTR stacking 在 validation 上没有形成稳定正增益；final test 的高收益方向反转不能直接解释为稳定泛化。

## 6. Final Test Full Universe / Overlap Universe

| method | fee_tax_adjusted_net_return | final_equity | max_drawdown | action_count | buy_count | sell_count | fee_and_tax | turnover_proxy_by_notional_over_avg_equity | turnover_notional | start_date | end_date | trading_days | initial_cash_or_equity_assumption | fee_rate | tax_rate | position_count_target | daily_nav_available_count | missing_price_days | skipped_trade_count | last_day_new_trade_without_next_price_count | relative_return_vs_fresh_top50_adaptive | relative_drawdown_vs_fresh_top50_adaptive | relative_actions_vs_fresh_top50_adaptive |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| fresh_qlib_top50_adaptive | 0.662457 | 1662456.78 | -0.088396 | 410 | 204 | 206 | 155259.42 | 40.692897 | 52838152.18 | 2025-07-01 | 2026-05-07 | 205 | 1000000.0 | 0.001425 | 0.003 | 10 | 205 | 0 | 0 | 0 | 0.0 | 0.0 | 0 |
| old_frozen_t2_ltr_simple | 1.221918 | 2221918.15 | -0.148581 | 403 | 204 | 199 | 186087.4 | 40.124243 | 63478967.85 | 2025-07-01 | 2026-05-07 | 205 | 1000000.0 | 0.001425 | 0.003 | 10 | 205 | 0 | 0 | 0 | 0.559461 | -0.060185 | -7 |
| old_frozen_t2_ltr_turnover_controlled | 0.579378 | 1579377.95 | -0.083835 | 63 | 35 | 28 | 22611.68 | 6.169866 | 7988880.13 | 2025-07-01 | 2026-05-07 | 205 | 1000000.0 | 0.001425 | 0.003 | 10 | 205 | 0 | 0 | 0 | -0.083079 | 0.004561 | -347 |
| fresh_ltr_simple | 0.544381 | 1544381.13 | -0.132896 | 408 | 204 | 204 | 145915.05 | 40.342791 | 49837559.21 | 2025-07-01 | 2026-05-07 | 205 | 1000000.0 | 0.001425 | 0.003 | 10 | 205 | 0 | 0 | 0 | -0.118076 | -0.0445 | -2 |
| fresh_ltr_turnover_controlled | 0.615059 | 1615059.14 | -0.11131 | 63 | 34 | 29 | 22944.59 | 6.207343 | 7935934.37 | 2025-07-01 | 2026-05-07 | 205 | 1000000.0 | 0.001425 | 0.003 | 10 | 205 | 0 | 0 | 0 | -0.047398 | -0.022914 | -347 |

说明：表名保留 `full_universe`，但对 old/frozen T2 LTR 而言实际是 final feature overlap universe；fresh baseline 使用既有 S2D replay-ready universe。

## 7. Common Universe 对照

| method | fee_tax_adjusted_net_return | final_equity | max_drawdown | action_count | buy_count | sell_count | fee_and_tax | turnover_proxy_by_notional_over_avg_equity | turnover_notional | start_date | end_date | trading_days | initial_cash_or_equity_assumption | fee_rate | tax_rate | position_count_target | daily_nav_available_count | missing_price_days | skipped_trade_count | last_day_new_trade_without_next_price_count | relative_return_vs_fresh_top50_adaptive | relative_drawdown_vs_fresh_top50_adaptive | relative_actions_vs_fresh_top50_adaptive |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| fresh_qlib_top50_adaptive | 0.66315 | 1663149.94 | -0.088516 | 410 | 204 | 206 | 155311.67 | 40.685358 | 52855633.18 | 2025-07-01 | 2026-05-07 | 205 | 1000000.0 | 0.001425 | 0.003 | 10 | 205 | 0 | 0 | 0 | 0.0 | 0.0 | 0 |
| old_frozen_t2_ltr_simple | 1.221918 | 2221918.15 | -0.148581 | 403 | 204 | 199 | 186087.4 | 40.124243 | 63478967.85 | 2025-07-01 | 2026-05-07 | 205 | 1000000.0 | 0.001425 | 0.003 | 10 | 205 | 0 | 0 | 0 | 0.558768 | -0.060065 | -7 |
| old_frozen_t2_ltr_turnover_controlled | 0.579378 | 1579377.95 | -0.083835 | 63 | 35 | 28 | 22611.68 | 6.169866 | 7988880.13 | 2025-07-01 | 2026-05-07 | 205 | 1000000.0 | 0.001425 | 0.003 | 10 | 205 | 0 | 0 | 0 | -0.083772 | 0.004681 | -347 |
| fresh_ltr_simple | 0.544381 | 1544381.13 | -0.132896 | 408 | 204 | 204 | 145915.05 | 40.342791 | 49837559.21 | 2025-07-01 | 2026-05-07 | 205 | 1000000.0 | 0.001425 | 0.003 | 10 | 205 | 0 | 0 | 0 | -0.118769 | -0.04438 | -2 |
| fresh_ltr_turnover_controlled | 0.615059 | 1615059.14 | -0.11131 | 63 | 34 | 29 | 22944.59 | 6.207343 | 7935934.37 | 2025-07-01 | 2026-05-07 | 205 | 1000000.0 | 0.001425 | 0.003 | 10 | 205 | 0 | 0 | 0 | -0.048091 | -0.022794 | -347 |

判断：

- `old_frozen_t2_ltr_simple` 在 common universe 下仍显著高于 fresh qlib/top50 adaptive；
- 但 `old_frozen_t2_ltr_turnover_controlled` 低于 fresh qlib/top50 adaptive；
- simple 版本回撤显著更差，不能只按收益率推进默认。

## 8. 年度 / Regime 结果

年度结果：

| method | year | trading_days | fee_tax_adjusted_net_return | max_drawdown | win_days | loss_days |
| --- | --- | --- | --- | --- | --- | --- |
| fresh_ltr_simple | 2025 | 126 | 0.19746 | -0.132896 | 65 | 60 |
| fresh_ltr_simple | 2026 | 79 | 0.289715 | -0.061187 | 48 | 31 |
| fresh_ltr_turnover_controlled | 2025 | 126 | 0.362943 | -0.080297 | 74 | 51 |
| fresh_ltr_turnover_controlled | 2026 | 79 | 0.184979 | -0.11131 | 48 | 31 |
| fresh_qlib_top50_adaptive_baseline | 2025 | 126 | 0.336427 | -0.088396 | 71 | 54 |
| fresh_qlib_top50_adaptive_baseline | 2026 | 79 | 0.243956 | -0.056785 | 48 | 31 |
| old_frozen_t2_ltr_simple | 2025 | 126 | 0.606586 | -0.057218 | 78 | 47 |
| old_frozen_t2_ltr_simple | 2026 | 79 | 0.383006 | -0.148581 | 46 | 33 |
| old_frozen_t2_ltr_turnover_controlled | 2025 | 126 | 0.373287 | -0.067751 | 71 | 54 |
| old_frozen_t2_ltr_turnover_controlled | 2026 | 79 | 0.150071 | -0.083835 | 46 | 33 |

Regime 结果：

| method | regime_segment | trading_days | fee_tax_adjusted_net_return | max_drawdown | win_days | loss_days |
| --- | --- | --- | --- | --- | --- | --- |
| fresh_ltr_simple | caution | 43 | -0.008163 | -0.044863 | 21 | 22 |
| fresh_ltr_simple | normal | 155 | 0.720522 | -0.105782 | 90 | 64 |
| fresh_ltr_simple | risk_off | 7 | -0.094989 | -0.053504 | 2 | 5 |
| fresh_ltr_turnover_controlled | caution | 43 | -0.009328 | -0.057053 | 23 | 20 |
| fresh_ltr_turnover_controlled | normal | 155 | 0.8342 | -0.081472 | 97 | 57 |
| fresh_ltr_turnover_controlled | risk_off | 7 | -0.111184 | -0.046616 | 2 | 5 |
| fresh_qlib_top50_adaptive_baseline | caution | 43 | 0.028685 | -0.056785 | 24 | 19 |
| fresh_qlib_top50_adaptive_baseline | normal | 155 | 0.709145 | -0.057996 | 93 | 61 |
| fresh_qlib_top50_adaptive_baseline | risk_off | 7 | -0.05444 | -0.040036 | 2 | 5 |
| old_frozen_t2_ltr_simple | caution | 43 | -0.059126 | -0.110653 | 20 | 23 |
| old_frozen_t2_ltr_simple | normal | 155 | 1.648272 | -0.102106 | 101 | 53 |
| old_frozen_t2_ltr_simple | risk_off | 7 | -0.108269 | -0.065564 | 3 | 4 |
| old_frozen_t2_ltr_turnover_controlled | caution | 43 | -0.006445 | -0.059949 | 22 | 21 |
| old_frozen_t2_ltr_turnover_controlled | normal | 155 | 0.662066 | -0.067751 | 92 | 62 |
| old_frozen_t2_ltr_turnover_controlled | risk_off | 7 | -0.043586 | -0.040195 | 3 | 4 |

## 9. 费用、换手、Next-Day Accounting

费用与换手：

| method | fee_and_tax | turnover_proxy_by_notional_over_avg_equity | turnover_notional | action_count | buy_count | sell_count | max_drawdown |
| --- | --- | --- | --- | --- | --- | --- | --- |
| fresh_qlib_top50_adaptive | 155259.42 | 40.692897 | 52838152.18 | 410 | 204 | 206 | -0.088396 |
| old_frozen_t2_ltr_simple | 186087.4 | 40.124243 | 63478967.85 | 403 | 204 | 199 | -0.148581 |
| old_frozen_t2_ltr_turnover_controlled | 22611.68 | 6.169866 | 7988880.13 | 63 | 35 | 28 | -0.083835 |
| fresh_ltr_simple | 145915.05 | 40.342791 | 49837559.21 | 408 | 204 | 204 | -0.132896 |
| fresh_ltr_turnover_controlled | 22944.59 | 6.207343 | 7935934.37 | 63 | 34 | 29 | -0.11131 |

Next-day accounting audit：

| audit | pass | execution_dates_after_signal_dates | missing_price_days_total | skipped_trade_count_total |
| --- | --- | --- | --- | --- |
| next_day_execution | True | True | 0 | 0 |

判断：所有回放使用既有 next-day execution 口径；`missing_price_days_total=0`。

## 10. 贡献与异常审计

贡献 proxy 审计使用历史卖出 notional proxy，不等价于真实归因 PnL，仅用于集中度风险提示：

| method | symbol | contribution_proxy_sell_notional | share_of_sell_notional |
| --- | --- | --- | --- |
| fresh_ltr_simple | TW4991 | 1274770.0 | 0.051061 |
| fresh_ltr_simple | TW3481 | 1026478.0 | 0.041116 |
| fresh_ltr_simple | TW2408 | 970030.0 | 0.038855 |
| fresh_ltr_simple | TW2344 | 961413.8 | 0.03851 |
| fresh_ltr_simple | TW6770 | 829353.0 | 0.03322 |
| fresh_ltr_simple | TW6919 | 808249.0 | 0.032375 |
| fresh_ltr_simple | TW3167 | 804230.99 | 0.032214 |
| fresh_ltr_simple | TW8996 | 687523.65 | 0.027539 |
| fresh_ltr_simple | TW3105 | 664585.0 | 0.02662 |
| fresh_ltr_simple | TW3163 | 641950.0 | 0.025713 |
| fresh_ltr_turnover_controlled | TW3363 | 237120.0 | 0.061135 |
| fresh_ltr_turnover_controlled | TW2344 | 235780.46 | 0.06079 |
| fresh_ltr_turnover_controlled | TW4991 | 231195.0 | 0.059607 |
| fresh_ltr_turnover_controlled | TW3163 | 221480.0 | 0.057103 |
| fresh_ltr_turnover_controlled | TW8299 | 209600.0 | 0.05404 |
| fresh_ltr_turnover_controlled | TW6770 | 208380.0 | 0.053725 |
| fresh_ltr_turnover_controlled | TW3481 | 201217.5 | 0.051879 |
| fresh_ltr_turnover_controlled | TW4967 | 190960.0 | 0.049234 |
| fresh_ltr_turnover_controlled | TW6515 | 157800.0 | 0.040685 |
| fresh_ltr_turnover_controlled | TW6919 | 150120.0 | 0.038704 |

异常日审计：

| method | date | daily_return | equity |
| --- | --- | --- | --- |
| fresh_ltr_simple | 2025-11-21 | -0.048098 | 1063133.02 |
| fresh_ltr_simple | 2026-02-24 | 0.042424 | 1484849.23 |
| fresh_ltr_simple | 2025-11-14 | -0.040321 | 1138356.5 |
| fresh_ltr_simple | 2026-01-19 | 0.035385 | 1372946.33 |
| fresh_ltr_simple | 2026-01-12 | 0.033343 | 1260739.68 |
| fresh_ltr_turnover_controlled | 2026-01-19 | 0.049309 | 1624065.51 |
| fresh_ltr_turnover_controlled | 2025-12-22 | 0.046429 | 1257225.48 |
| fresh_ltr_turnover_controlled | 2026-02-02 | -0.045417 | 1576970.73 |
| fresh_ltr_turnover_controlled | 2025-12-16 | -0.042485 | 1180741.55 |
| fresh_ltr_turnover_controlled | 2025-10-14 | -0.041449 | 1032581.29 |
| fresh_qlib_top50_adaptive_baseline | 2025-09-30 | 0.040406 | 1145674.55 |
| fresh_qlib_top50_adaptive_baseline | 2025-08-18 | 0.037652 | 1119843.61 |
| fresh_qlib_top50_adaptive_baseline | 2025-10-07 | 0.033232 | 1222198.02 |
| fresh_qlib_top50_adaptive_baseline | 2025-11-21 | -0.030713 | 1182755.83 |
| fresh_qlib_top50_adaptive_baseline | 2025-08-19 | -0.030332 | 1085876.95 |
| old_frozen_t2_ltr_simple | 2026-01-19 | 0.050934 | 1982697.63 |
| old_frozen_t2_ltr_simple | 2026-01-16 | 0.048983 | 1886604.52 |
| old_frozen_t2_ltr_simple | 2026-04-01 | 0.048214 | 2095295.13 |
| old_frozen_t2_ltr_simple | 2026-03-09 | -0.045742 | 2139171.5 |
| old_frozen_t2_ltr_simple | 2026-01-21 | -0.044702 | 1873346.16 |

判断：本轮尚未完成严格逐 lot PnL 归因。由于 simple 版本 final test 收益高且回撤更差，审查者应要求后续补逐笔/逐票真实 PnL contribution 才能讨论产品化。

## 11. Feature Importance / qlib 依赖度

Top feature importance：

| window_id | feature | importance | is_qlib_related |
| --- | --- | --- | --- |
| Q0_L4_4y | avg_trading_value_20d | 259 | False |
| Q0_L4_4y | volatility20 | 250 | False |
| Q0_L4_4y | MA60 | 246 | False |
| Q0_L4_4y | volume_stability20 | 191 | False |
| Q0_L4_4y | TWII_close_vs_MA120 | 162 | False |
| Q0_L4_4y | market_volatility20 | 155 | False |
| Q0_L4_4y | MACD | 130 | False |
| Q0_L4_4y | ret20 | 126 | False |
| Q0_L4_4y | market_breadth20 | 103 | False |
| Q0_L4_4y | TWII_ret60 | 102 | False |
| Q0_L4_4y | MA20 | 99 | False |
| Q0_L4_4y | MA10 | 85 | False |
| Q0_L4_4y | MA5 | 74 | False |
| Q0_L4_4y | TWII_close_vs_MA60 | 70 | False |
| Q0_L4_4y | market_drawdown60 | 64 | False |

模型注册中 `Q0_L4_4y` 的 qlib-related importance share 见 `phase_t2_ltr_model_registry.csv`。本次 top 特征以流动性、波动率、均线和市场状态为主，qlib score/rank 不是唯一驱动。

## 12. 过拟合与稳定性审计

| selected_window_id | selection_basis | validation_return | final_return | final_vs_validation_gap | final_test_used_for_selection |
| --- | --- | --- | --- | --- | --- |
| Q0_L4_4y | validation_fee_tax_adjusted_net_return_then_drawdown | -0.130647 | 1.221918 | 1.352565 | False |

判断：

- final test 未用于窗口选择；
- selected window validation return 为负，而 final return 大幅为正，存在 regime 依赖或不稳定泛化风险；
- train/validation/final test 差异不支持直接默认化。

## 13. 对待比较策略的状态

| strategy | status | note |
| --- | --- | --- |
| fresh qlib/top50 adaptive | completed | 复用 S2D replay-ready baseline |
| old/frozen qlib + stacked LTR simple | completed_with_overlap_feature_limit | T1 训练，old qlib final score + S2C historical features 推理 |
| old/frozen qlib + stacked LTR turnover-controlled | completed_with_overlap_feature_limit | 同上，低动作版本 |
| fresh qlib + fresh LTR simple | completed | 复用 S2D fresh LTR result |
| fresh qlib + fresh LTR turnover-controlled | completed | 复用 S2D fresh LTR result |

Q1/Q2 qlib rolling 窗口未新增训练；本轮只在 Q0 old/frozen OOS stacking 下跑 L1-L4，Q1 fresh 结果作为既有 fresh qlib/fresh LTR 策略对照纳入。未根据 final test 追加窗口。

## 14. T2 结论

不建议进入 T3 默认候选。

审查者若考虑继续推进，应先要求：

1. 补齐 old/frozen final test 34-feature full dynamic universe，减少 overlap 拼接偏差；
2. 做逐票真实 PnL contribution，而不是 sell-notional proxy；
3. 解释 validation 全负、final 大正的 regime 反转；
4. 检查 simple 版本最大回撤恶化是否可接受；
5. 若要低换手产品候选，本轮 old/frozen turnover-controlled 没有超过 fresh qlib/top50 adaptive。

