# Phase T2R 补充审计执行报告

生成日期：2026-06-15

## 1. 执行结论

本轮按 `docs/tw_qlib_oos_ltr_stacking/PHASET2_REVIEW_AND_FOLLOWUP_WORKDOC_CN.md` 执行 T2R，只做补充审计，不进入 T3，不切换默认策略。

结论：`T2R 完成；继续确认不得进入 T3 默认候选`。

核心判断：

- old/frozen final test full dynamic universe 34-feature 已用本地 normalized price 补齐，覆盖 `30475 / 30475` old score rows；
- full feature 重放后，simple 版本仍高收益，但最大回撤仍显著差于 fresh baseline；
- turnover-controlled 版本收益低于 fresh common baseline，且回撤更差；
- 真实 PnL contribution 显示第一贡献股票占 total net PnL 约 `16.8%`，存在贡献集中风险；
- validation 与 final 的 regime 分布差异显著：validation 近半为 risk_off，final 约四分之三为 normal，这能解释方向反转的一部分，但不能证明稳定泛化；
- 风险接受性审计结论为 `reject_default`。

推荐 gate：

```text
phase_t2r_completed_negative_default_decision
```

## 2. 安全边界

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
data_tw/experiments/tw_qlib_oos_ltr_stacking/phase_t2r
```

主要产物：

```text
phase_t2r_old_frozen_full_feature_scores.csv
phase_t2r_full_feature_coverage.csv
phase_t2r_full_feature_replay_metrics.csv
phase_t2r_full_feature_daily_nav.csv
phase_t2r_full_feature_action_audit.csv
phase_t2r_real_pnl_contribution_by_symbol.csv
phase_t2r_real_pnl_contribution_by_day.csv
phase_t2r_regime_distribution.csv
phase_t2r_score_correlation_shift.csv
phase_t2r_factor_exposure_shift.csv
phase_t2r_high_return_date_concentration.csv
phase_t2r_risk_acceptance_audit.csv
phase_t2r_summary.json
```

## 4. Full Dynamic Universe Feature 补齐

| old_score_rows | full_feature_rows_before_fill | old_score_dates | feature_dates | missing_by_feature |
| --- | --- | --- | --- | --- |
| 30475 | 30475 | 205 | 205 | {} |

判断：本轮用本地 normalized price/TWII 重新构建 final test 技术、流动性、市场状态特征，并用 old/frozen qlib score/rank 重算 qlib 派生特征。覆盖从 T2 的 `22523 / 30475` overlap-feature rows 提升到 `30475 / 30475` full old score rows。

## 5. Full Feature 只读回放结果

| method | fee_tax_adjusted_net_return | final_equity | max_drawdown | action_count | buy_count | sell_count | fee_and_tax | turnover_proxy_by_notional_over_avg_equity | turnover_notional | start_date | end_date | trading_days | initial_cash_or_equity_assumption | fee_rate | tax_rate | position_count_target | daily_nav_available_count | missing_price_days | skipped_trade_count | last_day_new_trade_without_next_price_count |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| old_frozen_t2r_ltr_simple | 1.106315 | 2106314.79 | -0.140099 | 403 | 204 | 199 | 182520.2 | 40.283436 | 62291889.05 | 2025-07-01 | 2026-05-07 | 205 | 1000000.0 | 0.001425 | 0.003 | 10 | 205 | 0 | 0 | 0 |
| old_frozen_t2r_ltr_turnover_controlled | 0.633462 | 1633462.17 | -0.147156 | 63 | 34 | 29 | 24706.26 | 6.29121 | 8534108.67 | 2025-07-01 | 2026-05-07 | 205 | 1000000.0 | 0.001425 | 0.003 | 10 | 205 | 0 | 0 | 0 |

对照 T2 common fresh baseline：

```text
fresh_qlib_top50_adaptive common return: 0.663150
fresh_qlib_top50_adaptive common max_drawdown: -0.088516
```

判断：

- `old_frozen_t2r_ltr_simple` 收益仍高，但 max_drawdown 为 `-0.140099`，显著差于 fresh baseline；
- `old_frozen_t2r_ltr_turnover_controlled` 收益 `0.633462`，低于 fresh baseline `0.663150`，且 max_drawdown `-0.147156` 更差；
- 因此 full feature 补齐没有改变“不进入默认候选”的结论。

## 6. 真实 PnL Contribution

逐票 contribution top rows：

| method | symbol | realized_pnl | unrealized_pnl | fee_tax_allocated | net_pnl | share_of_total_net_pnl |
| --- | --- | --- | --- | --- | --- | --- |
| old_frozen_t2r_ltr_simple | TW2408 | 115823.23 | 69542.82 | 6058.95 | 185366.05 | 0.167553 |
| old_frozen_t2r_ltr_simple | TW2344 | 118868.74 | -294.03 | 5549.7 | 118574.71 | 0.10718 |
| old_frozen_t2r_ltr_simple | TW3481 | 85240.87 | 0.0 | 6058.13 | 85240.87 | 0.077049 |
| old_frozen_t2r_ltr_simple | TW8299 | 82396.43 | 0.0 | 4751.85 | 82396.43 | 0.074478 |
| old_frozen_t2r_ltr_simple | TW1802 | 52291.86 | 0.0 | 5325.14 | 52291.86 | 0.047267 |
| old_frozen_t2r_ltr_simple | TW3081 | 51708.61 | 0.0 | 3691.39 | 51708.61 | 0.04674 |
| old_frozen_t2r_ltr_simple | TW4967 | 49334.32 | 0.0 | 2180.68 | 49334.32 | 0.044593 |
| old_frozen_t2r_ltr_simple | TW3563 | 44435.53 | 0.0 | 1364.47 | 44435.53 | 0.040165 |
| old_frozen_t2r_ltr_simple | TW2337 | 38778.22 | 0.0 | 2389.78 | 38778.22 | 0.035052 |
| old_frozen_t2r_ltr_simple | TW2383 | 38393.89 | 0.0 | 2566.53 | 38393.89 | 0.034704 |
| old_frozen_t2r_ltr_simple | TW2485 | 35665.6 | 0.0 | 3408.9 | 35665.6 | 0.032238 |
| old_frozen_t2r_ltr_simple | TW6442 | 33526.59 | 0.0 | 3433.41 | 33526.59 | 0.030305 |
| old_frozen_t2r_ltr_simple | TW4979 | 33398.78 | 0.0 | 1281.22 | 33398.78 | 0.030189 |
| old_frozen_t2r_ltr_simple | TW2313 | 25379.26 | 7920.14 | 1540.6 | 33299.4 | 0.030099 |
| old_frozen_t2r_ltr_simple | TW3163 | 32161.47 | 0.0 | 5188.53 | 32161.47 | 0.029071 |
| old_frozen_t2r_ltr_simple | TW6683 | 30117.34 | 0.0 | 4682.66 | 30117.34 | 0.027223 |
| old_frozen_t2r_ltr_simple | TW6443 | 28843.7 | 0.0 | 5055.8 | 28843.7 | 0.026072 |
| old_frozen_t2r_ltr_simple | TW3715 | 27274.27 | 0.0 | 693.73 | 27274.27 | 0.024653 |
| old_frozen_t2r_ltr_simple | TW8996 | 27196.21 | 0.0 | 1896.09 | 27196.21 | 0.024583 |
| old_frozen_t2r_ltr_simple | TW1590 | 25256.34 | 0.0 | 993.66 | 25256.34 | 0.022829 |

逐日 realized PnL top rows：

| method | date | realized_net_pnl |
| --- | --- | --- |
| old_frozen_t2r_ltr_simple | 2026-01-20 | 181379.45 |
| old_frozen_t2r_ltr_simple | 2025-12-24 | 82054.51000000001 |
| old_frozen_t2r_ltr_simple | 2025-11-12 | 72482.44 |
| old_frozen_t2r_ltr_simple | 2025-08-18 | 67560.84 |
| old_frozen_t2r_ltr_simple | 2026-01-29 | 60939.58 |
| old_frozen_t2r_ltr_simple | 2025-11-05 | 56512.13 |
| old_frozen_t2r_ltr_simple | 2026-01-27 | 49592.86 |
| old_frozen_t2r_ltr_simple | 2026-01-13 | 45771.07 |
| old_frozen_t2r_ltr_simple | 2026-01-16 | 44613.96 |
| old_frozen_t2r_ltr_simple | 2026-03-03 | 44435.53 |
| old_frozen_t2r_ltr_simple | 2026-03-02 | 42268.14 |
| old_frozen_t2r_ltr_simple | 2026-05-04 | 41462.83 |
| old_frozen_t2r_ltr_simple | 2026-04-01 | 38520.57 |
| old_frozen_t2r_ltr_simple | 2026-03-12 | 31919.75 |
| old_frozen_t2r_ltr_simple | 2025-08-21 | 31568.92 |
| old_frozen_t2r_ltr_simple | 2026-02-26 | 31456.26 |
| old_frozen_t2r_ltr_simple | 2026-01-19 | 30285.88 |
| old_frozen_t2r_ltr_simple | 2026-03-23 | 29195.91 |
| old_frozen_t2r_ltr_simple | 2025-08-04 | 27274.27 |
| old_frozen_t2r_ltr_simple | 2025-08-29 | 25944.86 |

判断：

- simple 版本第一贡献股票 `TW2408` 的 net PnL share 约 `0.167553`；
- 前几只股票贡献占比不低，仍需要把高收益视为集中度风险，而不是稳定默认收益来源；
- 本轮 contribution 已从 sell-notional proxy 改为基于回放 action 的 realized/unrealized PnL 重建。

## 7. Regime 反转解释

Regime 分布：

| period | regime_segment | rows | share |
| --- | --- | --- | --- |
| validation | risk_off | 16597 | 0.486858 |
| validation | caution | 9921 | 0.291024 |
| validation | normal | 7572 | 0.222118 |
| final_full_feature | normal | 22988 | 0.754323 |
| final_full_feature | caution | 6442 | 0.211386 |
| final_full_feature | risk_off | 1045 | 0.03429 |

Score / return correlation：

| period | metric | value |
| --- | --- | --- |
| validation | ltr_score_vs_future_excess_return_10d_spearman | 0.0621342869530688 |
| validation | ltr_score_vs_qlib_score_spearman | 0.2436955654086201 |
| final_full_feature | ltr_score_vs_future_return_10d_spearman | 0.0576110891394019 |
| final_full_feature | ltr_score_vs_qlib_score_spearman | 0.323085952048077 |

Factor exposure shift：

| period | feature | mean | std |
| --- | --- | --- | --- |
| validation | avg_trading_value_20d | 1932076335.4446952 | 3507929758.1440644 |
| validation | volatility20 | 0.0309821647959283 | 0.0128783764464383 |
| validation | MA60 | 362.3405339939379 | 573.9491277919934 |
| validation | volume_stability20 | 0.5496302214967124 | 0.1355103952372289 |
| validation | TWII_close_vs_MA120 | 0.0081922646883458 | 0.0661034604710867 |
| validation | market_volatility20 | 0.0155061895935704 | 0.0085955413722332 |
| validation | MACD | -0.3769603393020584 | 23.6092144049562 |
| validation | ret20 | -0.0002917236745832 | 0.1444607008328544 |
| validation | market_breadth20 | 0.448278643511425 | 0.2447055628066964 |
| validation | TWII_ret60 | -0.001106398574295 | 0.0807942060221554 |
| final_full_feature | avg_trading_value_20d | 3315885883.962714 | 5366725693.32187 |
| final_full_feature | volatility20 | 0.0335135948129143 | 0.0143217507930416 |
| final_full_feature | MA60 | 514.9307599871263 | 872.9126635701026 |
| final_full_feature | volume_stability20 | 0.5736384319052393 | 0.1219235599382593 |
| final_full_feature | TWII_close_vs_MA120 | 0.1374323141524079 | 0.056483905379311 |
| final_full_feature | market_volatility20 | 0.0128997222330175 | 0.0046935348057917 |
| final_full_feature | MACD | 18.199783109124464 | 65.47013384465968 |
| final_full_feature | ret20 | 0.1082739704283381 | 0.2022459848716176 |
| final_full_feature | market_breadth20 | 0.6459135886683629 | 0.1325171673714931 |
| final_full_feature | TWII_ret60 | 0.1610067770216657 | 0.0514888204566862 |

High-return date concentration：

| method | top10_daily_return_sum | period_return_proxy | top10_share_of_positive_return_proxy |
| --- | --- | --- | --- |
| old_frozen_t2r_ltr_simple | 0.396223 | 1.106315 | 0.220412 |
| old_frozen_t2r_ltr_turnover_controlled | 0.378557 | 0.633462 | 0.255615 |

解释：

- validation 样本中 `risk_off` 占 `48.69%`，final full feature 中 `normal` 占 `75.43%`；
- final 期间 TWII 60日收益、市场宽度、个股 ret20 明显高于 validation；
- LTR score 与 qlib score 的 Spearman 相关从 validation `0.2437` 升到 final `0.3231`，说明 final 环境下模型更贴近 qlib 排序强信号；
- high-return 日期贡献并非单日完全支配，但 top10 正收益日占正收益 proxy 约 `22%-26%`，仍有阶段集中风险。

结论：regime 反转有可解释性，但这不是默认化依据，因为 validation 未证明稳健正收益。

## 8. 风险接受性

| method | return_vs_fresh_common | drawdown_vs_fresh_common | risk_acceptance |
| --- | --- | --- | --- |
| old_frozen_t2r_ltr_simple | 0.443165 | -0.051583 | reject_default |
| old_frozen_t2r_ltr_turnover_controlled | -0.029688 | -0.05864 | reject_default |

回答：收益提升不足以自动补偿回撤恶化。

- simple 版本相对 fresh common baseline 收益更高，但回撤恶化约 `-0.051583`；
- turnover-controlled 版本收益低于 fresh baseline，回撤也更差；
- 两者 risk acceptance 均为 `reject_default`。

## 9. 低换手候选

低换手 old/frozen T2R：

```text
old_frozen_t2r_ltr_turnover_controlled return: 0.633462
old_frozen_t2r_ltr_turnover_controlled max_drawdown: -0.147156
fresh_qlib_top50_adaptive common return: 0.663150
fresh_qlib_top50_adaptive common max_drawdown: -0.088516
```

结论：低换手 old/frozen LTR 仍不能作为实用默认候选。

## 10. 最终结论

T2R 补充审计没有推翻 T2 审查结论：

```text
不得进入 T3 默认候选；不得切换默认策略。
```

建议：停止本条作为默认候选推进。若后续继续研究，应作为研究支线而不是产品默认路径，并优先解决 validation 稳健性、回撤控制和贡献集中问题。

