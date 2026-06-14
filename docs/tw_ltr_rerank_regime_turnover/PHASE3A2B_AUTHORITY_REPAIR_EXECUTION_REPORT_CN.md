# Phase3A2B Authority Repair 执行报告

生成时间：2026-06-13T19:37:12+00:00

## 1. 本轮目标

调和 Top50 adaptive / confirmed_exit 的权威完整日频组合回放口径，并在同一口径下重新尝试 Phase3A2 公平对照。本轮不进入 Phase3B。

## 2. Authority Matrix

| item | stress replay script | portfolio replay service |
| --- | --- | --- |
| Top30 | rank rotation threshold=30 | strategyComparison.rank_rotate_top30 |
| Top50 | rank rotation threshold=50 | strategyComparison.rank_rotate_top50 |
| Top50 adaptive score | threshold=50 + adaptive_score 0.04-0.08 in caution/severe | strategyComparison.rank_rotate_top50_adaptive_score |
| confirmed_exit | not implemented | strategyComparison.confirmed_exit via qlib_plus_trend_position_risk |
| price source | local Yahoo-adjusted normalized CSV | KlineService; Phase3A2B adapter injects same local CSV |
| execution price | next available close after asof | next_trading_day_close default |
| initial cash | 1,000,000 default | initialCash default 1,000,000 |
| lot size | 10 default | lotSize default 10 |
| fee rate | 0.001425 | 0.001425 |
| sell tax rate | 0.003 | 0.003 |
| max holdings | 10 default | maxHoldings default 10 |
| max actions per day | one reduce + one add per rank-rotation day | rank rotation one reduce + one add; confirmed_exit maxRiskActionPerDay/maxAddPerDay default 1 |
| missing price handling | skip and count missing prices | historical_skip warning missing_close |
| equity curve | curve per signal asof | equityCurve per signal asof |
| action count | buy/sell actions | historical_add/historical_risk_reduce actionCount |
| fee/tax accounting | fee on add; fee+sell tax on reduce | same in _replay_variant |
| readonly flags | research-only local-only flags | simulation_only=True, persist=False, writes_business_db=False, research_signal_not_order=True |

## 3. 权威口径选择

选择 `backend/app/services/tw_stock_portfolio_replay.py` 作为产品侧权威口径。离线 adapter 只注入本地历史 signal 与本地 Yahoo-adjusted normalized CSV K 线，复用产品侧 `_replay_variant()` 的现金、持仓、下一交易日收盘价、手续费、交易税、动作与权益曲线记账。没有修改后端服务或 API。

## 4. 实际改动文件

- `scripts/evaluate_tw_ltr_phase3a2_full_daily_replay.py`
- `data_tw/experiments/ltr_rerank_regime_turnover/phase3a2_full_daily_replay/phase3a2b_authority_matrix.csv`
- `data_tw/experiments/ltr_rerank_regime_turnover/phase3a2_full_daily_replay/phase3a2_method_comparison.csv`
- `data_tw/experiments/ltr_rerank_regime_turnover/phase3a2_full_daily_replay/phase3a2_period_comparison.csv`
- `data_tw/experiments/ltr_rerank_regime_turnover/phase3a2_full_daily_replay/phase3a2_equity_curves.csv`
- `data_tw/experiments/ltr_rerank_regime_turnover/phase3a2_full_daily_replay/phase3a2_actions_summary.csv`
- `data_tw/experiments/ltr_rerank_regime_turnover/phase3a2_full_daily_replay/phase3a2_data_quality.csv`
- `data_tw/experiments/ltr_rerank_regime_turnover/phase3a2_full_daily_replay/phase3a2_gate_summary.json`
- `docs/tw_ltr_rerank_regime_turnover/PHASE3A2B_AUTHORITY_REPAIR_EXECUTION_REPORT_CN.md`

## 5. Required Method Completion

| method | completion_status |
| --- | --- |
| rank_rotate_top30 | completed |
| rank_rotate_top50 | completed |
| rank_rotate_top50_adaptive_score | completed |
| confirmed_exit | completed |
| phase1c_ltr_simple_daily | completed |
| phase1c_ltr_turnover_controlled_daily | completed |

## 6. Common Full Range 方法结果

| method | comparison_status | fee_tax_adjusted_net_return | final_equity | max_drawdown | action_count | fee_and_tax | missing_price_count | delta_vs_rank_rotate_top50_adaptive_score | delta_vs_phase1c_ltr_simple_daily |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| rank_rotate_top30 | completed | 1.607147 | 2607147.05 | -0.446514 | 2062 | 566995.95 | 0 | -0.533856 | -4.465328 |
| rank_rotate_top50 | completed | 2.134495 | 3134494.62 | -0.409458 | 1994 | 576302.14 | 0 | -0.006508 | -3.93798 |
| rank_rotate_top50_adaptive_score | completed | 2.141003 | 3141003.25 | -0.408884 | 1942 | 567930.58 | 0 | 0.0 | -3.931472 |
| confirmed_exit | completed | 1.29917 | 2299169.89 | -0.091115 | 47 | 12247.62 | 0 | -0.841833 | -4.773305 |
| phase1c_ltr_simple_daily | completed | 6.072475 | 7072475.05 | -0.421769 | 1976 | 821105.19 | 0 | 3.931472 | 0.0 |
| phase1c_ltr_turnover_controlled_daily | completed | 0.869193 | 1869192.51 | -0.147199 | 3 | 424.46 | 0 | -1.27181 | -5.203282 |

## 7. 区间结果

| period | method | fee_tax_adjusted_net_return | final_equity | max_drawdown | action_count | missing_price_count | trading_days_used |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2022_full_available_replay_range | rank_rotate_top30 | -0.128888 | 871112.5 | -0.128887 | 483 | 0 | 246 |
| 2022_full_available_replay_range | rank_rotate_top50 | -0.129866 | 870133.86 | -0.129866 | 476 | 0 | 246 |
| 2022_full_available_replay_range | rank_rotate_top50_adaptive_score | -0.115792 | 884207.77 | -0.115792 | 428 | 0 | 246 |
| 2022_full_available_replay_range | confirmed_exit | 0.0 | 1000000.0 | 0.0 | 0 | 0 | 246 |
| 2022_full_available_replay_range | phase1c_ltr_simple_daily | -0.123197 | 876802.58 | -0.123197 | 464 | 0 | 246 |
| 2022_full_available_replay_range | phase1c_ltr_turnover_controlled_daily | -0.000424 | 999575.54 | -0.000424 | 3 | 0 | 246 |
| 2025_full_available_replay_range | rank_rotate_top30 | 0.931097 | 1931097.29 | -0.382047 | 472 | 0 | 242 |
| 2025_full_available_replay_range | rank_rotate_top50 | 0.896396 | 1896395.67 | -0.415914 | 452 | 0 | 242 |
| 2025_full_available_replay_range | rank_rotate_top50_adaptive_score | 0.833162 | 1833161.93 | -0.38705 | 446 | 0 | 242 |
| 2025_full_available_replay_range | confirmed_exit | 0.416364 | 1416363.64 | -0.081386 | 42 | 0 | 242 |
| 2025_full_available_replay_range | phase1c_ltr_simple_daily | 2.01937 | 3019369.51 | -0.337204 | 450 | 0 | 242 |
| 2025_full_available_replay_range | phase1c_ltr_turnover_controlled_daily | 0.118576 | 1118575.75 | -0.153091 | 3 | 0 | 242 |
| 2026_ytd_available_replay_range | rank_rotate_top30 | 0.856925 | 1856925.28 | -0.174852 | 181 | 0 | 95 |
| 2026_ytd_available_replay_range | rank_rotate_top50 | 1.225078 | 2225078.25 | -0.161748 | 178 | 0 | 95 |
| 2026_ytd_available_replay_range | rank_rotate_top50_adaptive_score | 1.225078 | 2225078.25 | -0.161748 | 178 | 0 | 95 |
| 2026_ytd_available_replay_range | confirmed_exit | 0.327098 | 1327098.05 | -0.059278 | 12 | 0 | 95 |
| 2026_ytd_available_replay_range | phase1c_ltr_simple_daily | 0.876689 | 1876688.97 | -0.168388 | 156 | 0 | 95 |
| 2026_ytd_available_replay_range | phase1c_ltr_turnover_controlled_daily | 0.310133 | 1310133.45 | -0.068195 | 3 | 0 | 95 |
| phase1c_validation_range | rank_rotate_top30 | 0.133542 | 1133542.24 | -0.420899 | 404 | 0 | 209 |
| phase1c_validation_range | rank_rotate_top50 | 0.141073 | 1141073.08 | -0.406586 | 396 | 0 | 209 |
| phase1c_validation_range | rank_rotate_top50_adaptive_score | 0.323224 | 1323224.27 | -0.370298 | 399 | 0 | 209 |
| phase1c_validation_range | confirmed_exit | 0.060414 | 1060414.1 | -0.081386 | 20 | 0 | 209 |
| phase1c_validation_range | phase1c_ltr_simple_daily | 0.485349 | 1485349.08 | -0.38555 | 404 | 0 | 209 |
| phase1c_validation_range | phase1c_ltr_turnover_controlled_daily | 0.039284 | 1039283.9 | -0.211728 | 3 | 0 | 209 |
| phase1c_independent_test_range | rank_rotate_top30 | 2.537688 | 3537688.28 | -0.167481 | 406 | 0 | 209 |
| phase1c_independent_test_range | rank_rotate_top50 | 2.450848 | 3450848.17 | -0.167457 | 386 | 0 | 209 |
| phase1c_independent_test_range | rank_rotate_top50_adaptive_score | 2.450848 | 3450848.17 | -0.167457 | 386 | 0 | 209 |
| phase1c_independent_test_range | confirmed_exit | 1.970208 | 2970207.6 | -0.101134 | 37 | 0 | 209 |
| phase1c_independent_test_range | phase1c_ltr_simple_daily | 3.550601 | 4550601.26 | -0.160298 | 384 | 0 | 209 |
| phase1c_independent_test_range | phase1c_ltr_turnover_controlled_daily | 0.547921 | 1547921.5 | -0.09725 | 3 | 0 | 209 |
| common_full_range_shared_by_all_compared_methods | rank_rotate_top30 | 1.607147 | 2607147.05 | -0.446514 | 2062 | 0 | 1048 |
| common_full_range_shared_by_all_compared_methods | rank_rotate_top50 | 2.134495 | 3134494.62 | -0.409458 | 1994 | 0 | 1048 |
| common_full_range_shared_by_all_compared_methods | rank_rotate_top50_adaptive_score | 2.141003 | 3141003.25 | -0.408884 | 1942 | 0 | 1048 |
| common_full_range_shared_by_all_compared_methods | confirmed_exit | 1.29917 | 2299169.89 | -0.091115 | 47 | 0 | 1048 |
| common_full_range_shared_by_all_compared_methods | phase1c_ltr_simple_daily | 6.072475 | 7072475.05 | -0.421769 | 1976 | 0 | 1048 |
| common_full_range_shared_by_all_compared_methods | phase1c_ltr_turnover_controlled_daily | 0.869193 | 1869192.51 | -0.147199 | 3 | 0 | 1048 |

## 8. Data Quality

| period | accepted_signal_days | missing_price_count | missing_ltr_score_dates | comparison_status | reason |
| --- | --- | --- | --- | --- | --- |
| 2022_full_available_replay_range | 246 | 0 | 5 | completed_with_data_quality_warnings | LTR score dates missing |
| 2025_full_available_replay_range | 242 | 0 | 0 | completed |  |
| 2026_ytd_available_replay_range | 95 | 0 | 16 | completed_with_data_quality_warnings | LTR score dates missing |
| phase1c_validation_range | 209 | 0 | 0 | completed |  |
| phase1c_independent_test_range | 209 | 0 | 0 | completed |  |
| common_full_range_shared_by_all_compared_methods | 1048 | 0 | 5 | completed_with_data_quality_warnings | LTR score dates missing |

## 9. Safety Boundary

本轮未执行 Phase3B，未改 frontend / API / monitor / database，未新增数据源，未联网，未 provider refresh / publish，未 accepted latest switching，未重新训练 LTR，未重建 Phase1C score，未重新打开 regime gate，未接 broker / quick-trade / orders / target position / target weight。报告中的 add / reduce / action count 均为只读历史模拟统计，不是交易指令。

## 10. 验证命令与结果

- `python -m py_compile scripts/evaluate_tw_ltr_phase3a2_full_daily_replay.py`：通过。
- `python scripts/evaluate_tw_ltr_phase3a2_full_daily_replay.py`：通过。
- `python -m pytest backend/tests/test_tw_stock_portfolio_replay.py -q`：10 passed。
- safety scan：通过；命中仅出现在 readonly flags、authority matrix 或 Safety Boundary 说明中，未发现实际 broker / quick_trade / order / target position / provider / accepted latest 执行路径。

## 11. 是否建议恢复 Phase3B

暂不建议自动恢复 Phase3B。本轮已完成六个 required methods 的同口径日频回放，但仍应等待审查者确认 authority adapter 与数据质量后再决定后续阶段。
