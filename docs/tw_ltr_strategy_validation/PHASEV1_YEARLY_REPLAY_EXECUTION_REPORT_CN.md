# Phase V1 分年完整日频回放验证执行报告

生成时间：2026-06-14T07:02:28+00:00

## 1. 本轮目标

按 Phase V0 冻结合同，只做 2022 / 2023 / 2024 / 2025 / 2026 YTD 分年完整日频回放验证。候选策略、baseline、分数字段、产品侧回放 authority、执行价、费用税费、共同日期集合与指标均沿用 Phase3A2C 修复口径。

本轮未执行 rolling 验证、未执行市况分段、未调参、未重训 LTR、未改前端/API、未联网、未新增数据源、未触发 provider / accepted latest / monitor / 交易链路。

## 2. 冻结对象

- 候选策略：`phase1c_ltr_simple_daily`、`phase1c_ltr_turnover_controlled_daily`。
- 冻结分数：`score_head10_all_l31_alpha0.7_top50_only`。
- 主 baseline：`rank_rotate_top50_adaptive_score`。
- 其他 baseline：`rank_rotate_top50`、`rank_rotate_top30`、`confirmed_exit`。
- 权威回放路径：产品侧 `TWStockPortfolioReplayService` / `_replay_variant()`；turnover-controlled 候选沿用 Phase3A2C 已修复只读实现。
- 执行价：asof 后第一个真实交易日 close。
- gross return：`not_available_in_current_engine`。

## 3. 年度数据质量

| period | start_date | end_date | baseline_signal_days | ltr_score_days | common_replay_days | excluded_dates | comparison_status | reason |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2022 | 2022-01-01 | 2022-12-31 | 246 | 241 | 241 | 2022-01-03,2022-01-04,2022-01-05,2022-01-06,2022-01-07 | completed | excluded dates removed from all methods |
| 2023 | 2023-01-01 | 2023-12-31 | 239 | 239 | 239 |  | completed |  |
| 2024 | 2024-01-01 | 2024-12-31 | 242 | 242 | 242 |  | completed |  |
| 2025 | 2025-01-01 | 2025-12-31 | 242 | 242 | 242 |  | completed |  |
| 2026_ytd | 2026-01-01 | 2026-06-13 | 95 | 79 | 79 | 2026-05-08,2026-05-11,2026-05-12,2026-05-13,2026-05-14,2026-05-15,2026-05-18,2026-05-19,2026-05-20,2026-05-21,2026-05-22,2026-05-25,2026-05-26,2026-05-27,2026-05-28,2026-05-29 | completed | excluded dates removed from all methods |

## 4. 主候选与主基线年度结果

| period | method | comparison_status | gross_return | fee_tax_adjusted_net_return | final_equity | max_drawdown | action_count | buy_count | sell_count | turnover_proxy_by_notional_over_avg_equity | fee_and_tax | missing_price_count | trading_days_used | relative_return_vs_top50_adaptive | relative_drawdown_vs_top50_adaptive | relative_actions_vs_top50_adaptive |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2022 | rank_rotate_top50_adaptive_score | completed | not_available_in_current_engine | -0.12456 | 875440.11 | -0.241499 | 418 | 213 | 205 | 41.332549 | 107271.73 | 0 | 241 | 0.0 | 0.0 | 0 |
| 2022 | phase1c_ltr_simple_daily | completed | not_available_in_current_engine | -0.00163 | 998370.15 | -0.256739 | 464 | 237 | 227 | 45.501766 | 125312.27 | 0 | 241 | 0.12293 | -0.01524 | 46 |
| 2022 | phase1c_ltr_turnover_controlled_daily | completed | not_available_in_current_engine | 0.11929 | 1119289.89 | -0.160512 | 73 | 38 | 35 | 7.167496 | 20280.24 | 0 | 241 | 0.24385 | 0.080987 | -345 |
| 2023 | rank_rotate_top50_adaptive_score | completed | not_available_in_current_engine | 1.371793 | 2371793.3 | -0.140026 | 440 | 225 | 215 | 40.293872 | 215056.65 | 0 | 239 | 0.0 | 0.0 | 0 |
| 2023 | phase1c_ltr_simple_daily | completed | not_available_in_current_engine | 1.965554 | 2965553.91 | -0.145731 | 432 | 221 | 211 | 44.466555 | 273192.97 | 0 | 239 | 0.593761 | -0.005705 | -8 |
| 2023 | phase1c_ltr_turnover_controlled_daily | completed | not_available_in_current_engine | 0.630687 | 1630686.71 | -0.130101 | 72 | 37 | 35 | 7.040341 | 28782.22 | 0 | 239 | -0.741106 | 0.009925 | -368 |
| 2024 | rank_rotate_top50_adaptive_score | completed | not_available_in_current_engine | 0.794357 | 1794357.11 | -0.282289 | 454 | 232 | 222 | 43.720155 | 193573.35 | 0 | 242 | 0.0 | 0.0 | 0 |
| 2024 | phase1c_ltr_simple_daily | completed | not_available_in_current_engine | 1.87572 | 2875720.34 | -0.234454 | 450 | 230 | 220 | 48.133736 | 268517.43 | 0 | 242 | 1.081363 | 0.047835 | -4 |
| 2024 | phase1c_ltr_turnover_controlled_daily | completed | not_available_in_current_engine | 0.784358 | 1784357.99 | -0.118144 | 74 | 39 | 35 | 7.42291 | 30534.61 | 0 | 242 | -0.009999 | 0.164145 | -380 |
| 2025 | rank_rotate_top50_adaptive_score | completed | not_available_in_current_engine | 0.833162 | 1833161.93 | -0.38705 | 446 | 228 | 218 | 41.516749 | 139051.12 | 0 | 242 | 0.0 | 0.0 | 0 |
| 2025 | phase1c_ltr_simple_daily | completed | not_available_in_current_engine | 2.01937 | 3019369.51 | -0.337204 | 450 | 230 | 220 | 40.303273 | 179907.78 | 0 | 242 | 1.186208 | 0.049846 | 4 |
| 2025 | phase1c_ltr_turnover_controlled_daily | completed | not_available_in_current_engine | 0.218875 | 1218874.77 | -0.173828 | 74 | 39 | 35 | 7.299281 | 23245.07 | 0 | 242 | -0.614287 | 0.213222 | -372 |
| 2026_ytd | rank_rotate_top50_adaptive_score | completed | not_available_in_current_engine | 0.896163 | 1896163.26 | -0.161748 | 148 | 79 | 69 | 13.376837 | 49122.77 | 0 | 79 | 0.0 | 0.0 | 0 |
| 2026_ytd | phase1c_ltr_simple_daily | completed | not_available_in_current_engine | 0.973726 | 1973726.13 | -0.168388 | 146 | 78 | 68 | 14.239895 | 58019.05 | 0 | 79 | 0.077563 | -0.00664 | -2 |
| 2026_ytd | phase1c_ltr_turnover_controlled_daily | completed | not_available_in_current_engine | 0.113415 | 1113414.57 | -0.085224 | 24 | 13 | 11 | 2.353677 | 7100.91 | 0 | 79 | -0.782748 | 0.076524 | -124 |

## 5. 全部 baseline 与候选年度结果

| period | method | comparison_status | fee_tax_adjusted_net_return | final_equity | max_drawdown | action_count | buy_count | sell_count | turnover_proxy_by_notional_over_avg_equity | fee_and_tax | missing_price_count | trading_days_used | relative_return_vs_top50_adaptive | relative_drawdown_vs_top50_adaptive | relative_actions_vs_top50_adaptive |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2022 | rank_rotate_top30 | completed | -0.202398 | 797602.07 | -0.282892 | 473 | 241 | 232 | 46.347099 | 116198.5 | 0 | 241 | -0.077838 | -0.041393 | 55 |
| 2022 | rank_rotate_top50 | completed | -0.213877 | 786123.42 | -0.307894 | 466 | 238 | 228 | 44.918136 | 112692.63 | 0 | 241 | -0.089317 | -0.066395 | 48 |
| 2022 | rank_rotate_top50_adaptive_score | completed | -0.12456 | 875440.11 | -0.241499 | 418 | 213 | 205 | 41.332549 | 107271.73 | 0 | 241 | 0.0 | 0.0 | 0 |
| 2022 | confirmed_exit | completed | -0.190221 | 809778.69 | -0.283779 | 78 | 43 | 35 | 7.354547 | 17578.96 | 0 | 241 | -0.065661 | -0.04228 | -340 |
| 2022 | phase1c_ltr_simple_daily | completed | -0.00163 | 998370.15 | -0.256739 | 464 | 237 | 227 | 45.501766 | 125312.27 | 0 | 241 | 0.12293 | -0.01524 | 46 |
| 2022 | phase1c_ltr_turnover_controlled_daily | completed | 0.11929 | 1119289.89 | -0.160512 | 73 | 38 | 35 | 7.167496 | 20280.24 | 0 | 241 | 0.24385 | 0.080987 | -345 |
| 2023 | rank_rotate_top30 | completed | 1.38198 | 2381980.2 | -0.141015 | 458 | 234 | 224 | 43.624869 | 234797.98 | 0 | 239 | 0.010187 | -0.000989 | 18 |
| 2023 | rank_rotate_top50 | completed | 1.371793 | 2371793.3 | -0.140026 | 440 | 225 | 215 | 40.293872 | 215056.65 | 0 | 239 | 0.0 | 0.0 | 0 |
| 2023 | rank_rotate_top50_adaptive_score | completed | 1.371793 | 2371793.3 | -0.140026 | 440 | 225 | 215 | 40.293872 | 215056.65 | 0 | 239 | 0.0 | 0.0 | 0 |
| 2023 | confirmed_exit | completed | 0.450275 | 1450275.26 | -0.153786 | 56 | 33 | 23 | 4.685345 | 15856.78 | 0 | 239 | -0.921518 | -0.01376 | -384 |
| 2023 | phase1c_ltr_simple_daily | completed | 1.965554 | 2965553.91 | -0.145731 | 432 | 221 | 211 | 44.466555 | 273192.97 | 0 | 239 | 0.593761 | -0.005705 | -8 |
| 2023 | phase1c_ltr_turnover_controlled_daily | completed | 0.630687 | 1630686.71 | -0.130101 | 72 | 37 | 35 | 7.040341 | 28782.22 | 0 | 239 | -0.741106 | 0.009925 | -368 |
| 2024 | rank_rotate_top30 | completed | 0.424891 | 1424891.0 | -0.283675 | 468 | 239 | 229 | 44.672021 | 170896.28 | 0 | 242 | -0.369466 | -0.001386 | 14 |
| 2024 | rank_rotate_top50 | completed | 0.615173 | 1615172.97 | -0.285426 | 452 | 231 | 221 | 41.800808 | 177899.14 | 0 | 242 | -0.179184 | -0.003137 | -2 |
| 2024 | rank_rotate_top50_adaptive_score | completed | 0.794357 | 1794357.11 | -0.282289 | 454 | 232 | 222 | 43.720155 | 193573.35 | 0 | 242 | 0.0 | 0.0 | 0 |
| 2024 | confirmed_exit | completed | 0.390174 | 1390173.54 | -0.214431 | 72 | 41 | 31 | 6.40561 | 20866.35 | 0 | 242 | -0.404183 | 0.067858 | -382 |
| 2024 | phase1c_ltr_simple_daily | completed | 1.87572 | 2875720.34 | -0.234454 | 450 | 230 | 220 | 48.133736 | 268517.43 | 0 | 242 | 1.081363 | 0.047835 | -4 |
| 2024 | phase1c_ltr_turnover_controlled_daily | completed | 0.784358 | 1784357.99 | -0.118144 | 74 | 39 | 35 | 7.42291 | 30534.61 | 0 | 242 | -0.009999 | 0.164145 | -380 |
| 2025 | rank_rotate_top30 | completed | 0.931097 | 1931097.29 | -0.382047 | 472 | 241 | 231 | 43.351398 | 148603.96 | 0 | 242 | 0.097935 | 0.005003 | 26 |
| 2025 | rank_rotate_top50 | completed | 0.896396 | 1896395.67 | -0.415914 | 452 | 231 | 221 | 41.836936 | 142526.45 | 0 | 242 | 0.063234 | -0.028864 | 6 |
| 2025 | rank_rotate_top50_adaptive_score | completed | 0.833162 | 1833161.93 | -0.38705 | 446 | 228 | 218 | 41.516749 | 139051.12 | 0 | 242 | 0.0 | 0.0 | 0 |
| 2025 | confirmed_exit | completed | 0.571193 | 1571193.31 | -0.292607 | 58 | 34 | 24 | 4.935787 | 14267.12 | 0 | 242 | -0.261969 | 0.094443 | -388 |
| 2025 | phase1c_ltr_simple_daily | completed | 2.01937 | 3019369.51 | -0.337204 | 450 | 230 | 220 | 40.303273 | 179907.78 | 0 | 242 | 1.186208 | 0.049846 | 4 |
| 2025 | phase1c_ltr_turnover_controlled_daily | completed | 0.218875 | 1218874.77 | -0.173828 | 74 | 39 | 35 | 7.299281 | 23245.07 | 0 | 242 | -0.614287 | 0.213222 | -372 |
| 2026_ytd | rank_rotate_top30 | completed | 0.501287 | 1501286.78 | -0.174852 | 149 | 79 | 70 | 14.193097 | 47258.73 | 0 | 79 | -0.394876 | -0.013104 | 1 |
| 2026_ytd | rank_rotate_top50 | completed | 0.896163 | 1896163.26 | -0.161748 | 148 | 79 | 69 | 13.376837 | 49122.77 | 0 | 79 | 0.0 | 0.0 | 0 |
| 2026_ytd | rank_rotate_top50_adaptive_score | completed | 0.896163 | 1896163.26 | -0.161748 | 148 | 79 | 69 | 13.376837 | 49122.77 | 0 | 79 | 0.0 | 0.0 | 0 |
| 2026_ytd | confirmed_exit | completed | 0.168845 | 1168844.8 | -0.059278 | 9 | 6 | 3 | 0.814404 | 1896.49 | 0 | 79 | -0.727318 | 0.10247 | -139 |
| 2026_ytd | phase1c_ltr_simple_daily | completed | 0.973726 | 1973726.13 | -0.168388 | 146 | 78 | 68 | 14.239895 | 58019.05 | 0 | 79 | 0.077563 | -0.00664 | -2 |
| 2026_ytd | phase1c_ltr_turnover_controlled_daily | completed | 0.113415 | 1113414.57 | -0.085224 | 24 | 13 | 11 | 2.353677 | 7100.91 | 0 | 79 | -0.782748 | 0.076524 | -124 |

## 6. Price Execution Audit 摘要

| sample_asof | symbol | expected_next_trade_date | actual_execution_date | actual_execution_price | days_to_execution | status |
| --- | --- | --- | --- | --- | --- | --- |
| 2022-01-10 | TW3714 | 2022-01-11 | 2022-01-11 | 85.3814 | 1 | ok |
| 2022-01-10 | TW3583 | 2022-01-11 | 2022-01-11 | 95.1739 | 1 | ok |
| 2022-01-10 | TW2360 | 2022-01-11 | 2022-01-11 | 205.6188 | 1 | ok |
| 2022-01-10 | TW6446 | 2022-01-11 | 2022-01-11 | 230.4224 | 1 | ok |
| 2022-01-10 | TW3533 | 2022-01-11 | 2022-01-11 | 644.7098 | 1 | ok |
| 2022-01-10 | TW2603 | 2022-01-11 | 2022-01-11 | 126.4012 | 1 | ok |
| 2022-01-10 | TW3037 | 2022-01-11 | 2022-01-11 | 188.8382 | 1 | ok |
| 2022-01-10 | TW2382 | 2022-01-11 | 2022-01-11 | 73.2111 | 1 | ok |
| 2022-01-10 | TW3491 | 2022-01-11 | 2022-01-11 | 167.6365 | 1 | ok |
| 2022-01-10 | TW6274 | 2022-01-11 | 2022-01-11 | 76.9108 | 1 | ok |
| 2022-01-10 | TW3189 | 2022-01-11 | 2022-01-11 | 179.4955 | 1 | ok |
| 2022-01-10 | TW6669 | 2022-01-11 | 2022-01-11 | 992.6249 | 1 | ok |
| 2022-01-10 | TW3324 | 2022-01-11 | 2022-01-11 | 199.8402 | 1 | ok |
| 2022-01-10 | TW3231 | 2022-01-11 | 2022-01-11 | 24.759 | 1 | ok |
| 2022-01-10 | TW2059 | 2022-01-11 | 2022-01-11 | 427.5514 | 1 | ok |
| 2022-01-10 | TW6805 | 2022-01-11 | 2022-01-11 | 266.5791 | 1 | ok |
| 2022-01-10 | TW2449 | 2022-01-11 | 2022-01-11 | 36.4522 | 1 | ok |
| 2022-01-10 | TW1717 | 2022-01-11 | 2022-01-11 | 33.9631 | 1 | ok |
| 2022-01-10 | TW5351 | 2022-01-11 | 2022-01-11 | 71.4657 | 1 | ok |
| 2022-01-10 | TW4958 | 2022-01-11 | 2022-01-11 | 84.3074 | 1 | ok |

## 7. 产物

- 年度结果：`data_tw/experiments/ltr_strategy_validation/phasev1_yearly_replay/phasev1_yearly_comparison.csv`
- 数据质量：`data_tw/experiments/ltr_strategy_validation/phasev1_yearly_replay/phasev1_yearly_data_quality.csv`
- 执行价审计：`data_tw/experiments/ltr_strategy_validation/phasev1_yearly_replay/phasev1_price_execution_audit.csv`
- gate summary：`data_tw/experiments/ltr_strategy_validation/phasev1_yearly_replay/phasev1_gate_summary.json`

## 8. Safety Boundary

本轮仅运行本地只读历史验证脚本。所有 add / reduce / action count 均为历史模拟统计，不是交易指令；报告不包含买入、卖出、持有、仓位建议，不包含收益承诺、胜率承诺或上涨概率语义。

## 9. Gate

`phasev1_yearly_replay_completed_hold_for_review`

等待审查者确认后，才可进入下一阶段；本轮不自动启动 rolling 或市况验证。
