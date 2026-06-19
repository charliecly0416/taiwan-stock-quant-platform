# Phase3A2C Lookahead / Metric Repair 执行报告

生成时间：2026-06-13T19:57:58+00:00

## 1. 本轮目标

修复 Phase3A2B 的 lookahead、共同日期集合、净/毛收益字段、notional turnover proxy 与 turnover-controlled LTR 滚动预算问题，并在同一权威口径下重跑六个 required methods。Phase3B 继续暂停。

## 2. Lookahead 修复方式

`LocalKline.get_kline()` 改为返回本地 CSV 完整历史；`OfflineService._next_close_after()` 直接使用 `PriceStore.next_after(symbol, asof)`，确保成交价来自 asof 后第一个真实交易日 close，不再受 `get_kline(..., 500)` 截断影响。

## 3. Price Execution Audit 摘要

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

## 4. 共同日期集合处理

每个 period 先取 baseline accepted signal days，再与 Phase1C frozen score 日期取交集；所有六个方法只在 `common_replay_days` 上回放。缺分日期从所有方法统一排除，并写入 data quality。

| period | baseline_signal_days | ltr_score_days | common_replay_days | excluded_dates | comparison_status |
| --- | --- | --- | --- | --- | --- |
| 2022_full_available_replay_range | 246 | 241 | 241 | 2022-01-03,2022-01-04,2022-01-05,2022-01-06,2022-01-07 | completed |
| 2025_full_available_replay_range | 242 | 242 | 242 |  | completed |
| 2026_ytd_available_replay_range | 95 | 79 | 79 | 2026-05-08,2026-05-11,2026-05-12,2026-05-13,2026-05-14,2026-05-15,2026-05-18,2026-05-19,2026-05-20,2026-05-21,2026-05-22,2026-05-25,2026-05-26,2026-05-27,2026-05-28,2026-05-29 | completed |
| phase1c_validation_range | 209 | 209 | 209 |  | completed |
| phase1c_independent_test_range | 209 | 209 | 209 |  | completed |
| common_full_range_shared_by_all_compared_methods | 1048 | 1043 | 1043 | 2022-01-03,2022-01-04,2022-01-05,2022-01-06,2022-01-07 | completed |

## 5. Gross / Net 字段定义

产品侧 `_replay_variant()` 的 `totalReturn` 已基于扣除手续费和交易税后的 final equity。当前引擎没有并行维护无费用/税费 gross equity，因此 `gross_return` 明确标记为 `not_available_in_current_engine`，只使用 `fee_tax_adjusted_net_return`。

## 6. Turnover Proxy 定义

`turnover_proxy_by_notional_over_avg_equity = sum(abs(quantity * price)) / average_equity`。`action_count` 单独保留，不再用动作频率冒充换手 proxy。

## 7. Turnover-controlled LTR 滚动预算实现

Phase3A1 配置 `k30_a3_gap0.0_buf0.0_holdw2_budget0.2` 映射为：target_k=30、max_actions_per_day=3、max_actions_per_10_trading_days=3、min_holding_days=20、confidence_gap=0.0、no_trade_buffer=0.0、turnover_budget_proxy=0.2。动作预算按最近 10 个交易日滚动过期。

## 8. Parity Check

| check | status | common_replay_days | action_count | feeAndTax | finalEquity | equity_tail | basis |
| --- | --- | --- | --- | --- | --- | --- | --- |
| top50_adaptive_short_window | completed | 5 | 7 | 1580.46 | 1004303.25 | 1004303.25 | same OfflineService product _replay_variant path used by full replay |

## 9. Required Method Completion

| method | completion_status |
| --- | --- |
| rank_rotate_top30 | completed |
| rank_rotate_top50 | completed |
| rank_rotate_top50_adaptive_score | completed |
| confirmed_exit | completed |
| phase1c_ltr_simple_daily | completed |
| phase1c_ltr_turnover_controlled_daily | completed |

## 10. Common Full Range 方法结果

| method | comparison_status | gross_return | fee_tax_adjusted_net_return | final_equity | max_drawdown | action_count | turnover_proxy_by_notional_over_avg_equity | fee_and_tax | missing_price_count | delta_vs_rank_rotate_top50_adaptive_score | delta_vs_phase1c_ltr_simple_daily |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| rank_rotate_top30 | completed | not_available_in_current_engine | 9.785117 | 10785116.82 | -0.426219 | 2054 | 193.662284 | 1422495.32 | 0 | -6.17856 | -30.233103 |
| rank_rotate_top50 | completed | not_available_in_current_engine | 11.061246 | 12061245.63 | -0.408928 | 1982 | 198.730437 | 1761893.31 | 0 | -4.902431 | -28.956974 |
| rank_rotate_top50_adaptive_score | completed | not_available_in_current_engine | 15.963677 | 16963676.69 | -0.402422 | 1932 | 184.497379 | 2088395.51 | 0 | 0.0 | -24.054543 |
| confirmed_exit | completed | not_available_in_current_engine | 3.011848 | 4011847.68 | -0.337436 | 265 | 21.361639 | 89767.52 | 0 | -12.951829 | -37.006372 |
| phase1c_ltr_simple_daily | completed | not_available_in_current_engine | 40.01822 | 41018219.55 | -0.387816 | 1978 | 199.489876 | 4183658.34 | 0 | 24.054543 | 0.0 |
| phase1c_ltr_turnover_controlled_daily | completed | not_available_in_current_engine | 4.652725 | 5652725.27 | -0.199269 | 315 | 31.849293 | 217564.89 | 0 | -11.310952 | -35.365495 |

## 11. 区间结果

| period | method | fee_tax_adjusted_net_return | final_equity | max_drawdown | action_count | turnover_proxy_by_notional_over_avg_equity | missing_price_count | trading_days_used |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2022_full_available_replay_range | rank_rotate_top30 | -0.202398 | 797602.07 | -0.282892 | 473 | 46.347099 | 0 | 241 |
| 2022_full_available_replay_range | rank_rotate_top50 | -0.213877 | 786123.42 | -0.307894 | 466 | 44.918136 | 0 | 241 |
| 2022_full_available_replay_range | rank_rotate_top50_adaptive_score | -0.12456 | 875440.11 | -0.241499 | 418 | 41.332549 | 0 | 241 |
| 2022_full_available_replay_range | confirmed_exit | -0.190221 | 809778.69 | -0.283779 | 78 | 7.354547 | 0 | 241 |
| 2022_full_available_replay_range | phase1c_ltr_simple_daily | -0.00163 | 998370.15 | -0.256739 | 464 | 45.501766 | 0 | 241 |
| 2022_full_available_replay_range | phase1c_ltr_turnover_controlled_daily | 0.11929 | 1119289.89 | -0.160512 | 73 | 7.167496 | 0 | 241 |
| 2025_full_available_replay_range | rank_rotate_top30 | 0.931097 | 1931097.29 | -0.382047 | 472 | 43.351398 | 0 | 242 |
| 2025_full_available_replay_range | rank_rotate_top50 | 0.896396 | 1896395.67 | -0.415914 | 452 | 41.836936 | 0 | 242 |
| 2025_full_available_replay_range | rank_rotate_top50_adaptive_score | 0.833162 | 1833161.93 | -0.38705 | 446 | 41.516749 | 0 | 242 |
| 2025_full_available_replay_range | confirmed_exit | 0.571193 | 1571193.31 | -0.292607 | 58 | 4.935787 | 0 | 242 |
| 2025_full_available_replay_range | phase1c_ltr_simple_daily | 2.01937 | 3019369.51 | -0.337204 | 450 | 40.303273 | 0 | 242 |
| 2025_full_available_replay_range | phase1c_ltr_turnover_controlled_daily | 0.218875 | 1218874.77 | -0.173828 | 74 | 7.299281 | 0 | 242 |
| 2026_ytd_available_replay_range | rank_rotate_top30 | 0.501287 | 1501286.78 | -0.174852 | 149 | 14.193097 | 0 | 79 |
| 2026_ytd_available_replay_range | rank_rotate_top50 | 0.896163 | 1896163.26 | -0.161748 | 148 | 13.376837 | 0 | 79 |
| 2026_ytd_available_replay_range | rank_rotate_top50_adaptive_score | 0.896163 | 1896163.26 | -0.161748 | 148 | 13.376837 | 0 | 79 |
| 2026_ytd_available_replay_range | confirmed_exit | 0.168845 | 1168844.8 | -0.059278 | 9 | 0.814404 | 0 | 79 |
| 2026_ytd_available_replay_range | phase1c_ltr_simple_daily | 0.973726 | 1973726.13 | -0.168388 | 146 | 14.239895 | 0 | 79 |
| 2026_ytd_available_replay_range | phase1c_ltr_turnover_controlled_daily | 0.113415 | 1113414.57 | -0.085224 | 24 | 2.353677 | 0 | 79 |
| phase1c_validation_range | rank_rotate_top30 | 0.133542 | 1133542.24 | -0.420899 | 404 | 40.132511 | 0 | 209 |
| phase1c_validation_range | rank_rotate_top50 | 0.141073 | 1141073.08 | -0.406586 | 396 | 40.024263 | 0 | 209 |
| phase1c_validation_range | rank_rotate_top50_adaptive_score | 0.323224 | 1323224.27 | -0.370298 | 399 | 40.629269 | 0 | 209 |
| phase1c_validation_range | confirmed_exit | 0.037412 | 1037411.75 | -0.254308 | 78 | 7.093931 | 0 | 209 |
| phase1c_validation_range | phase1c_ltr_simple_daily | 0.485349 | 1485349.08 | -0.38555 | 404 | 41.487823 | 0 | 209 |
| phase1c_validation_range | phase1c_ltr_turnover_controlled_daily | 0.112269 | 1112268.57 | -0.152926 | 63 | 6.212238 | 0 | 209 |
| phase1c_independent_test_range | rank_rotate_top30 | 2.537688 | 3537688.28 | -0.167481 | 406 | 36.86702 | 0 | 209 |
| phase1c_independent_test_range | rank_rotate_top50 | 2.450848 | 3450848.17 | -0.167457 | 386 | 37.15186 | 0 | 209 |
| phase1c_independent_test_range | rank_rotate_top50_adaptive_score | 2.450848 | 3450848.17 | -0.167457 | 386 | 37.15186 | 0 | 209 |
| phase1c_independent_test_range | confirmed_exit | 1.970208 | 2970207.6 | -0.101134 | 37 | 2.493577 | 0 | 209 |
| phase1c_independent_test_range | phase1c_ltr_simple_daily | 3.550601 | 4550601.26 | -0.160298 | 384 | 36.664086 | 0 | 209 |
| phase1c_independent_test_range | phase1c_ltr_turnover_controlled_daily | 0.315243 | 1315242.54 | -0.084103 | 63 | 6.248977 | 0 | 209 |
| common_full_range_shared_by_all_compared_methods | rank_rotate_top30 | 9.785117 | 10785116.82 | -0.426219 | 2054 | 193.662284 | 0 | 1043 |
| common_full_range_shared_by_all_compared_methods | rank_rotate_top50 | 11.061246 | 12061245.63 | -0.408928 | 1982 | 198.730437 | 0 | 1043 |
| common_full_range_shared_by_all_compared_methods | rank_rotate_top50_adaptive_score | 15.963677 | 16963676.69 | -0.402422 | 1932 | 184.497379 | 0 | 1043 |
| common_full_range_shared_by_all_compared_methods | confirmed_exit | 3.011848 | 4011847.68 | -0.337436 | 265 | 21.361639 | 0 | 1043 |
| common_full_range_shared_by_all_compared_methods | phase1c_ltr_simple_daily | 40.01822 | 41018219.55 | -0.387816 | 1978 | 199.489876 | 0 | 1043 |
| common_full_range_shared_by_all_compared_methods | phase1c_ltr_turnover_controlled_daily | 4.652725 | 5652725.27 | -0.199269 | 315 | 31.849293 | 0 | 1043 |

## 12. Safety Boundary

本轮未执行 Phase3B，未改 frontend / API / backend 产品服务 / monitor / database，未新增数据源，未联网，未 provider refresh / publish，未 accepted latest switching，未重新训练 LTR，未重建 Phase1C score，未重新打开 regime gate，未接 broker / quick-trade / orders / target position / target weight。add / reduce / action count 均为只读历史模拟统计，不是交易指令。

## 13. 验证命令与结果

- `python -m py_compile scripts/evaluate_tw_ltr_phase3a2_full_daily_replay.py`：通过。
- `python scripts/evaluate_tw_ltr_phase3a2_full_daily_replay.py`：通过；普通沙箱遇到 `bwrap: loopback: Failed RTM_NEWADDR` 环境限制后，用相同完整命令在授权环境完成，未降级。
- `python -m pytest backend/tests/test_tw_stock_portfolio_replay.py -q`：通过，10 passed。
- price audit：通过，sample_count=240，bad_count=0，max_days_to_execution=3。
- safety scan：通过；命中仅为 Safety Boundary / readonly 标记 / 报告说明文本，未发现真实交易执行路径。

## 14. 是否建议恢复 Phase3B

不建议自动恢复 Phase3B。本轮修复并重跑后仍应等待审查者确认 price audit、共同日期集合和 turnover 口径。
