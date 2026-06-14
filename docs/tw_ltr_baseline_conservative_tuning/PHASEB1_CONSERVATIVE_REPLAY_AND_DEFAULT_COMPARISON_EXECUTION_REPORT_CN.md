# Phase B1 LTR 保守版回放验证与默认基线比较执行报告

生成时间：2026-06-14T11:41:09+00:00

执行依据：`docs/tw_ltr_baseline_conservative_tuning/PHASEB0_REVIEW_AND_PHASEB1_CONSERVATIVE_REPLAY_WORK_CN.md`

## 1. 本轮目标和未越界声明

本轮只做固定候选的 LTR 保守版规则层回放验证，并在验证完成后给出同口径默认基线建议。

未重训 LTR，未改 Phase1C frozen score，未新增数据源，未联网，未改 provider / accepted latest，未写 monitor，未触碰 broker / quick-trade / orders / target position / target weight，未改前端/API。

## 2. 固定候选规则表

| candidate_key | description | candidate_pool_rank | buy_rank_threshold | buy_confirm_days | sell_rank_threshold | sell_confirm_days | max_actions_per_day | max_actions_per_10_trading_days | min_holding_days |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| phase1c_ltr_conservative_top30_2day_confirm_daily | 只看 Top30 且连续 2 天确认，减少单日噪声动作。 | 30 | 30 | 2 | 50 | 2 | 1 | 3 | 20 |
| phase1c_ltr_conservative_top20_entry_2day_exit_daily | 买入更严格，只接受 Top20；卖出需连续转弱。 | 50 | 20 | 1 | 50 | 2 | 1 | 3 | 20 |

既有保守基准 `phase1c_ltr_turnover_controlled_daily` 使用 Phase3A2C 既有 replay_turnover 实现作为原始参照；两个新增候选只改变规则层确认条件。

## 3. 输入 artifact 清单

- `data_tw/experiments/ltr_rerank_regime_turnover/phase3a0_frozen_phase1c_scores/phase3a0_frozen_phase1c_row_scores.csv`
- `data_tw/experiments/ltr_rerank_regime_turnover/phase3a0_frozen_phase1c_scores/phase3a0_score_schema.json`
- `scripts/evaluate_tw_ltr_phase3a2_full_daily_replay.py`
- 既有本地 normalized price archive 与 accepted historical signal artifact。

## 4. 回放口径确认

score column 固定为 `score_head10_all_l31_alpha0.7_top50_only`；执行价、费用税费、lot、max holdings、turnover proxy 均复用 Phase3A2C/product-side 口径。

## 5. 输出 artifact 清单

- `data_tw/experiments/ltr_baseline_conservative_tuning/phaseb1_conservative_replay/phaseb1_period_comparison.csv`
- `data_tw/experiments/ltr_baseline_conservative_tuning/phaseb1_conservative_replay/phaseb1_method_summary.csv`
- `data_tw/experiments/ltr_baseline_conservative_tuning/phaseb1_conservative_replay/phaseb1_conservative_candidate_delta.csv`
- `data_tw/experiments/ltr_baseline_conservative_tuning/phaseb1_conservative_replay/phaseb1_period_quality.csv`
- `data_tw/experiments/ltr_baseline_conservative_tuning/phaseb1_conservative_replay/phaseb1_gate_summary.json`

## 6. 全策略 x period 对比表

| period | method | fee_tax_adjusted_net_return | max_drawdown | action_count | buy_count | sell_count | fee_and_tax | turnover_proxy_by_notional_over_avg_equity | trading_days_used | relative_return_vs_top50_adaptive | relative_drawdown_vs_top50_adaptive | relative_actions_vs_top50_adaptive |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2022 | rank_rotate_top30 | -0.202398 | -0.282892 | 473 | 241 | 232 | 116198.5 | 46.347099 | 241 | -0.077838 | -0.041393 | 55 |
| 2022 | rank_rotate_top50 | -0.213877 | -0.307894 | 466 | 238 | 228 | 112692.63 | 44.918136 | 241 | -0.089317 | -0.066395 | 48 |
| 2022 | rank_rotate_top50_adaptive_score | -0.12456 | -0.241499 | 418 | 213 | 205 | 107271.73 | 41.332549 | 241 | 0.0 | 0.0 | 0 |
| 2022 | confirmed_exit | -0.190221 | -0.283779 | 78 | 43 | 35 | 17578.96 | 7.354547 | 241 | -0.065661 | -0.04228 | -340 |
| 2022 | phase1c_ltr_simple_daily | -0.00163 | -0.256739 | 464 | 237 | 227 | 125312.27 | 45.501766 | 241 | 0.12293 | -0.01524 | 46 |
| 2022 | phase1c_ltr_turnover_controlled_daily | 0.11929 | -0.160512 | 73 | 38 | 35 | 20280.24 | 7.167496 | 241 | 0.24385 | 0.080987 | -345 |
| 2022 | phase1c_ltr_conservative_top30_2day_confirm_daily | 0.03392 | -0.193244 | 72 | 38 | 34 | 19338.96 | 6.924679 | 241 | 0.15848 | 0.048255 | -346 |
| 2022 | phase1c_ltr_conservative_top20_entry_2day_exit_daily | 0.021816 | -0.207133 | 73 | 40 | 33 | 18723.81 | 7.024241 | 241 | 0.146376 | 0.034366 | -345 |
| 2023 | rank_rotate_top30 | 1.38198 | -0.141015 | 458 | 234 | 224 | 234797.98 | 43.624869 | 239 | 0.010187 | -0.000989 | 18 |
| 2023 | rank_rotate_top50 | 1.371793 | -0.140026 | 440 | 225 | 215 | 215056.65 | 40.293872 | 239 | 0.0 | 0.0 | 0 |
| 2023 | rank_rotate_top50_adaptive_score | 1.371793 | -0.140026 | 440 | 225 | 215 | 215056.65 | 40.293872 | 239 | 0.0 | 0.0 | 0 |
| 2023 | confirmed_exit | 0.450275 | -0.153786 | 56 | 33 | 23 | 15856.78 | 4.685345 | 239 | -0.921518 | -0.01376 | -384 |
| 2023 | phase1c_ltr_simple_daily | 1.965554 | -0.145731 | 432 | 221 | 211 | 273192.97 | 44.466555 | 239 | 0.593761 | -0.005705 | -8 |
| 2023 | phase1c_ltr_turnover_controlled_daily | 0.630687 | -0.130101 | 72 | 37 | 35 | 28782.22 | 7.040341 | 239 | -0.741106 | 0.009925 | -368 |
| 2023 | phase1c_ltr_conservative_top30_2day_confirm_daily | 0.931025 | -0.224266 | 72 | 39 | 33 | 29657.97 | 6.77576 | 239 | -0.440768 | -0.08424 | -368 |
| 2023 | phase1c_ltr_conservative_top20_entry_2day_exit_daily | 0.99857 | -0.163802 | 72 | 38 | 34 | 30253.73 | 6.817337 | 239 | -0.373223 | -0.023776 | -368 |
| 2024 | rank_rotate_top30 | 0.424891 | -0.283675 | 468 | 239 | 229 | 170896.28 | 44.672021 | 242 | -0.369466 | -0.001386 | 14 |
| 2024 | rank_rotate_top50 | 0.615173 | -0.285426 | 452 | 231 | 221 | 177899.14 | 41.800808 | 242 | -0.179184 | -0.003137 | -2 |
| 2024 | rank_rotate_top50_adaptive_score | 0.794357 | -0.282289 | 454 | 232 | 222 | 193573.35 | 43.720155 | 242 | 0.0 | 0.0 | 0 |
| 2024 | confirmed_exit | 0.390174 | -0.214431 | 72 | 41 | 31 | 20866.35 | 6.40561 | 242 | -0.404183 | 0.067858 | -382 |
| 2024 | phase1c_ltr_simple_daily | 1.87572 | -0.234454 | 450 | 230 | 220 | 268517.43 | 48.133736 | 242 | 1.081363 | 0.047835 | -4 |
| 2024 | phase1c_ltr_turnover_controlled_daily | 0.784358 | -0.118144 | 74 | 39 | 35 | 30534.61 | 7.42291 | 242 | -0.009999 | 0.164145 | -380 |
| 2024 | phase1c_ltr_conservative_top30_2day_confirm_daily | 0.702011 | -0.127658 | 73 | 40 | 33 | 27367.68 | 6.94712 | 242 | -0.092346 | 0.154631 | -381 |
| 2024 | phase1c_ltr_conservative_top20_entry_2day_exit_daily | 0.976266 | -0.122147 | 74 | 39 | 35 | 32811.75 | 7.299823 | 242 | 0.181909 | 0.160142 | -380 |
| 2025 | rank_rotate_top30 | 0.931097 | -0.382047 | 472 | 241 | 231 | 148603.96 | 43.351398 | 242 | 0.097935 | 0.005003 | 26 |
| 2025 | rank_rotate_top50 | 0.896396 | -0.415914 | 452 | 231 | 221 | 142526.45 | 41.836936 | 242 | 0.063234 | -0.028864 | 6 |
| 2025 | rank_rotate_top50_adaptive_score | 0.833162 | -0.38705 | 446 | 228 | 218 | 139051.12 | 41.516749 | 242 | 0.0 | 0.0 | 0 |
| 2025 | confirmed_exit | 0.571193 | -0.292607 | 58 | 34 | 24 | 14267.12 | 4.935787 | 242 | -0.261969 | 0.094443 | -388 |
| 2025 | phase1c_ltr_simple_daily | 2.01937 | -0.337204 | 450 | 230 | 220 | 179907.78 | 40.303273 | 242 | 1.186208 | 0.049846 | 4 |
| 2025 | phase1c_ltr_turnover_controlled_daily | 0.218875 | -0.173828 | 74 | 39 | 35 | 23245.07 | 7.299281 | 242 | -0.614287 | 0.213222 | -372 |
| 2025 | phase1c_ltr_conservative_top30_2day_confirm_daily | 0.626518 | -0.154205 | 73 | 40 | 33 | 24716.52 | 7.146973 | 242 | -0.206644 | 0.232845 | -373 |
| 2025 | phase1c_ltr_conservative_top20_entry_2day_exit_daily | 0.513323 | -0.196784 | 74 | 40 | 34 | 24813.04 | 7.266425 | 242 | -0.319839 | 0.190266 | -372 |
| 2026_ytd | rank_rotate_top30 | 0.501287 | -0.174852 | 149 | 79 | 70 | 47258.73 | 14.193097 | 79 | -0.394876 | -0.013104 | 1 |
| 2026_ytd | rank_rotate_top50 | 0.896163 | -0.161748 | 148 | 79 | 69 | 49122.77 | 13.376837 | 79 | 0.0 | 0.0 | 0 |
| 2026_ytd | rank_rotate_top50_adaptive_score | 0.896163 | -0.161748 | 148 | 79 | 69 | 49122.77 | 13.376837 | 79 | 0.0 | 0.0 | 0 |
| 2026_ytd | confirmed_exit | 0.168845 | -0.059278 | 9 | 6 | 3 | 1896.49 | 0.814404 | 79 | -0.727318 | 0.10247 | -139 |
| 2026_ytd | phase1c_ltr_simple_daily | 0.973726 | -0.168388 | 146 | 78 | 68 | 58019.05 | 14.239895 | 79 | 0.077563 | -0.00664 | -2 |
| 2026_ytd | phase1c_ltr_turnover_controlled_daily | 0.113415 | -0.085224 | 24 | 13 | 11 | 7100.91 | 2.353677 | 79 | -0.782748 | 0.076524 | -124 |
| 2026_ytd | phase1c_ltr_conservative_top30_2day_confirm_daily | 0.683008 | -0.104778 | 24 | 14 | 10 | 8521.83 | 2.290227 | 79 | -0.213155 | 0.05697 | -124 |
| 2026_ytd | phase1c_ltr_conservative_top20_entry_2day_exit_daily | 0.22191 | -0.08566 | 24 | 13 | 11 | 7542.27 | 2.312022 | 79 | -0.674253 | 0.076088 | -124 |
| common_full_range_shared_by_all_compared_methods | rank_rotate_top30 | 9.785117 | -0.426219 | 2054 | 1032 | 1022 | 1422495.32 | 193.662284 | 1043 | -6.17856 | -0.023797 | 122 |
| common_full_range_shared_by_all_compared_methods | rank_rotate_top50 | 11.061246 | -0.408928 | 1982 | 996 | 986 | 1761893.31 | 198.730437 | 1043 | -4.902431 | -0.006506 | 50 |
| common_full_range_shared_by_all_compared_methods | rank_rotate_top50_adaptive_score | 15.963677 | -0.402422 | 1932 | 971 | 961 | 2088395.51 | 184.497379 | 1043 | 0.0 | 0.0 | 0 |
| common_full_range_shared_by_all_compared_methods | confirmed_exit | 3.011848 | -0.337436 | 265 | 137 | 128 | 89767.52 | 21.361639 | 1043 | -12.951829 | 0.064986 | -1667 |
| common_full_range_shared_by_all_compared_methods | phase1c_ltr_simple_daily | 40.01822 | -0.387816 | 1978 | 994 | 984 | 4183658.34 | 199.489876 | 1043 | 24.054543 | 0.014606 | 46 |
| common_full_range_shared_by_all_compared_methods | phase1c_ltr_turnover_controlled_daily | 4.652725 | -0.199269 | 315 | 159 | 156 | 217564.89 | 31.849293 | 1043 | -11.310952 | 0.203153 | -1617 |
| common_full_range_shared_by_all_compared_methods | phase1c_ltr_conservative_top30_2day_confirm_daily | 7.42078 | -0.225025 | 312 | 157 | 155 | 306643.78 | 30.456281 | 1043 | -8.542897 | 0.177397 | -1620 |
| common_full_range_shared_by_all_compared_methods | phase1c_ltr_conservative_top20_entry_2day_exit_daily | 8.060574 | -0.207133 | 314 | 160 | 154 | 293416.48 | 29.893958 | 1043 | -7.903103 | 0.195289 | -1618 |
| phase1c_validation_range | rank_rotate_top30 | 0.133542 | -0.420899 | 404 | 207 | 197 | 127078.14 | 40.132511 | 209 | -0.189682 | -0.050601 | 5 |
| phase1c_validation_range | rank_rotate_top50 | 0.141073 | -0.406586 | 396 | 203 | 193 | 127175.73 | 40.024263 | 209 | -0.182151 | -0.036288 | -3 |
| phase1c_validation_range | rank_rotate_top50_adaptive_score | 0.323224 | -0.370298 | 399 | 204 | 195 | 141094.03 | 40.629269 | 209 | 0.0 | 0.0 | 0 |
| phase1c_validation_range | confirmed_exit | 0.037412 | -0.254308 | 78 | 44 | 34 | 19224.42 | 7.093931 | 209 | -0.285812 | 0.11599 | -321 |
| phase1c_validation_range | phase1c_ltr_simple_daily | 0.485349 | -0.38555 | 404 | 207 | 197 | 145256.29 | 41.487823 | 209 | 0.162125 | -0.015252 | 5 |
| phase1c_validation_range | phase1c_ltr_turnover_controlled_daily | 0.112269 | -0.152926 | 63 | 33 | 30 | 18851.27 | 6.212238 | 209 | -0.210955 | 0.217372 | -336 |
| phase1c_validation_range | phase1c_ltr_conservative_top30_2day_confirm_daily | 0.17605 | -0.128686 | 63 | 32 | 31 | 19661.95 | 6.212691 | 209 | -0.147174 | 0.241612 | -336 |
| phase1c_validation_range | phase1c_ltr_conservative_top20_entry_2day_exit_daily | 0.02884 | -0.206277 | 63 | 33 | 30 | 18001.46 | 6.226156 | 209 | -0.294384 | 0.164021 | -336 |
| phase1c_independent_test_range | rank_rotate_top30 | 2.537688 | -0.167481 | 406 | 208 | 198 | 193471.53 | 36.86702 | 209 | 0.08684 | -2.4e-05 | 20 |
| phase1c_independent_test_range | rank_rotate_top50 | 2.450848 | -0.167457 | 386 | 198 | 188 | 197566.14 | 37.15186 | 209 | 0.0 | 0.0 | 0 |
| phase1c_independent_test_range | rank_rotate_top50_adaptive_score | 2.450848 | -0.167457 | 386 | 198 | 188 | 197566.14 | 37.15186 | 209 | 0.0 | 0.0 | 0 |
| phase1c_independent_test_range | confirmed_exit | 1.970208 | -0.101134 | 37 | 22 | 15 | 9852.53 | 2.493577 | 209 | -0.48064 | 0.066323 | -349 |
| phase1c_independent_test_range | phase1c_ltr_simple_daily | 3.550601 | -0.160298 | 384 | 197 | 187 | 236164.09 | 36.664086 | 209 | 1.099753 | 0.007159 | -2 |
| phase1c_independent_test_range | phase1c_ltr_turnover_controlled_daily | 0.315243 | -0.084103 | 63 | 32 | 31 | 22537.86 | 6.248977 | 209 | -2.135605 | 0.083354 | -323 |
| phase1c_independent_test_range | phase1c_ltr_conservative_top30_2day_confirm_daily | 1.257516 | -0.098271 | 63 | 33 | 30 | 26477.33 | 6.17243 | 209 | -1.193332 | 0.069186 | -323 |
| phase1c_independent_test_range | phase1c_ltr_conservative_top20_entry_2day_exit_daily | 0.65007 | -0.143129 | 63 | 33 | 30 | 23023.09 | 6.207663 | 209 | -1.800778 | 0.024328 | -323 |

## 7. 新保守候选相对原保守版对比

| period | candidate | delta_return_vs_original_conservative | delta_drawdown_vs_original_conservative | delta_actions_vs_original_conservative | delta_turnover_vs_original_conservative | actions_vs_ltr_simple |
| --- | --- | --- | --- | --- | --- | --- |
| 2022 | phase1c_ltr_conservative_top30_2day_confirm_daily | -0.08537 | -0.032732 | -1 | -0.242817 | -392 |
| 2022 | phase1c_ltr_conservative_top20_entry_2day_exit_daily | -0.097474 | -0.046621 | 0 | -0.143255 | -391 |
| 2023 | phase1c_ltr_conservative_top30_2day_confirm_daily | 0.300338 | -0.094165 | 0 | -0.264581 | -360 |
| 2023 | phase1c_ltr_conservative_top20_entry_2day_exit_daily | 0.367883 | -0.033701 | 0 | -0.223004 | -360 |
| 2024 | phase1c_ltr_conservative_top30_2day_confirm_daily | -0.082347 | -0.009514 | -1 | -0.47579 | -377 |
| 2024 | phase1c_ltr_conservative_top20_entry_2day_exit_daily | 0.191908 | -0.004003 | 0 | -0.123087 | -376 |
| 2025 | phase1c_ltr_conservative_top30_2day_confirm_daily | 0.407643 | 0.019623 | -1 | -0.152308 | -377 |
| 2025 | phase1c_ltr_conservative_top20_entry_2day_exit_daily | 0.294448 | -0.022956 | 0 | -0.032856 | -376 |
| 2026_ytd | phase1c_ltr_conservative_top30_2day_confirm_daily | 0.569593 | -0.019554 | 0 | -0.06345 | -122 |
| 2026_ytd | phase1c_ltr_conservative_top20_entry_2day_exit_daily | 0.108495 | -0.000436 | 0 | -0.041655 | -122 |
| common_full_range_shared_by_all_compared_methods | phase1c_ltr_conservative_top30_2day_confirm_daily | 2.768055 | -0.025756 | -3 | -1.393012 | -1666 |
| common_full_range_shared_by_all_compared_methods | phase1c_ltr_conservative_top20_entry_2day_exit_daily | 3.407849 | -0.007864 | -1 | -1.955335 | -1664 |
| phase1c_validation_range | phase1c_ltr_conservative_top30_2day_confirm_daily | 0.063781 | 0.02424 | 0 | 0.000453 | -341 |
| phase1c_validation_range | phase1c_ltr_conservative_top20_entry_2day_exit_daily | -0.083429 | -0.053351 | 0 | 0.013918 | -341 |
| phase1c_independent_test_range | phase1c_ltr_conservative_top30_2day_confirm_daily | 0.942273 | -0.014168 | 0 | -0.076547 | -321 |
| phase1c_independent_test_range | phase1c_ltr_conservative_top20_entry_2day_exit_daily | 0.334827 | -0.059026 | 0 | -0.041314 | -321 |

## 8. 默认基线综合比较

| method | period_count | avg_fee_tax_adjusted_net_return | min_fee_tax_adjusted_net_return | avg_max_drawdown | worst_max_drawdown | avg_action_count | avg_turnover_proxy | positive_period_count |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| rank_rotate_top30 | 8 | 1.936651 | -0.202398 | -0.284885 | -0.426219 | 610.5 | 57.856287 | 7 |
| rank_rotate_top50 | 8 | 2.152352 | -0.213877 | -0.286747 | -0.415914 | 590.25 | 57.266644 | 7 |
| rank_rotate_top50_adaptive_score | 8 | 2.813583 | -0.12456 | -0.269099 | -0.402422 | 577.88 | 55.314834 | 7 |
| confirmed_exit | 8 | 0.801217 | -0.190221 | -0.212095 | -0.337436 | 81.62 | 6.893105 | 7 |
| phase1c_ltr_simple_daily | 8 | 6.360864 | -0.00163 | -0.259522 | -0.387816 | 588.5 | 58.785876 | 7 |
| phase1c_ltr_turnover_controlled_daily | 8 | 0.868358 | 0.112269 | -0.138013 | -0.199269 | 94.75 | 9.449277 | 8 |
| phase1c_ltr_conservative_top30_2day_confirm_daily | 8 | 1.478854 | 0.03392 | -0.157017 | -0.225025 | 94.0 | 9.11577 | 8 |
| phase1c_ltr_conservative_top20_entry_2day_exit_daily | 8 | 1.433921 | 0.021816 | -0.166508 | -0.207133 | 94.62 | 9.130953 | 8 |

解释：默认基线建议必须综合跨 period 稳定性、回撤、动作数、用户可理解性和前端说明复杂度，不按单一收益排序。

## 9. B1 必须回答的问题

1. 两个新增保守版候选相对原保守版的改善并不自动成立，需看多 period 稳定性：
- `phase1c_ltr_conservative_top30_2day_confirm_daily`：收益改善 period 数=6/8，动作不高于原保守版 period 数=8/8，换手不高于原保守版 period 数=7/8，回撤未明显恶化 period 数=7/8；可进入 B2 参考列表候选。
- `phase1c_ltr_conservative_top20_entry_2day_exit_daily`：收益改善 period 数=6/8，动作不高于原保守版 period 数=8/8，换手不高于原保守版 period 数=7/8，回撤未明显恶化 period 数=6/8；可进入 B2 参考列表候选。
2. 改进归因按收益、回撤、动作和换手同时判断；不以单一收益率决定。
3. 若某候选只在少数 period 改善，则视为不稳定，不进入 B2。
4. 所有保守候选 action_count 均需与 `phase1c_ltr_simple_daily` 对照，确认仍保守。
5. max_drawdown 未明显恶化是保留候选的必要条件之一。
6. turnover proxy 必须保持低换手特征，否则不算保守。
7. 保守候选保留名单：`phase1c_ltr_conservative_top30_2day_confirm_daily`, `phase1c_ltr_conservative_top20_entry_2day_exit_daily`
8. 保守候选淘汰名单：无
9. 建议当前默认基线仍保持 `rank_rotate_top50_adaptive_score`。理由：LTR simple 虽收益更高，但动作与换手高、产品解释复杂；原保守版和新增保守候选更低动作/低换手，但收益牺牲明显，不适合作为默认主基线。Top50 adaptive 在既有默认锚点、用户可理解性、产品延续性和同口径综合表现之间更均衡。
10. 默认建议不是基于单一收益，而是综合稳定性、回撤、动作数、用户可理解性与前端说明复杂度。

## 10. split-aware / OOS 防反向调参说明

两个新增候选在 B0 已冻结；B1 只执行一次固定候选回放。`phase1c_independent_test_range` 和 `2026_ytd` 只用于冻结候选后的样本外检查，没有用于新增候选或改阈值。

## 11. 是否建议进入 B2

建议进入 B2：保留默认基线整理，并将通过的保守候选作为下拉参考策略候选；不得默认化 LTR。

## 12. Gate 建议

```text
phaseb1_validated_request_phaseb2_user_first_product_closure
```
