# Phase S1B6R 执行报告：Accounting Repair

生成日期：2026-06-14T18:12:13+00:00

## 1. 本轮目标

修复 S1B6 中“用 signal_date 后下一交易日成交，却把成交后持仓/现金计入 signal_date 当日 NAV”的 accounting/lookahead 问题，并按同一冻结策略重跑。

## 2. 修复口径

- `signal_date/asof`：只生成待执行订单。
- `execution_date`：下一交易日 close 成交。
- `effective_nav_date`：与 `execution_date` 相同。
- 当日 NAV 只反映当日之前已经生效的持仓与现金。

## 3. Full Test 指标

| method | fee_tax_adjusted_net_return | max_drawdown | action_count | buy_count | sell_count | fee_and_tax | turnover_proxy | relative_return_vs_top50_adaptive |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| qlib_top50_adaptive_baseline | -0.112917 | -0.207861 | 1189 | 596 | 593 | 331343.27 | 116.52068 | 0.0 |
| rank_rotate_top50 | -0.115908 | -0.190013 | 1189 | 596 | 593 | 327415.64 | 116.492576 | -0.002991 |
| rank_rotate_top30 | -0.115908 | -0.190013 | 1189 | 596 | 593 | 327415.64 | 116.492576 | -0.002991 |
| confirmed_exit | -0.097833 | -0.184988 | 1189 | 596 | 593 | 329639.78 | 116.486312 | 0.015084 |
| split_aligned_ltr_simple | -0.080041 | -0.276558 | 1185 | 596 | 589 | 331188.28 | 117.850532 | 0.032876 |
| split_aligned_ltr_turnover_controlled | 0.130541 | -0.186466 | 180 | 92 | 88 | 57118.18 | 17.852216 | 0.243458 |

## 4. Accounting Timeline Audit

- `signal_date_affects_same_day_nav = False`
- `execution_date_before_or_equal_effective_nav_date = True`
- `next_day_execution_not_counted_in_prior_day_nav = True`
- `last_day_new_trade_without_next_price_count = 0`
- `fee_tax_deducted_on_execution_date = True`

## 5. Strategy Identity Audit

- `rank_rotate_top50_vs_top30_identical_metrics = True`
- reason: `position_count_target=10 and both strategies sort by the same qlib score, so candidate pool top30/top50 degenerates to the same top10 holdings path under the frozen implementation`

## 6. Split / Lookahead 边界

- 最终比较仍只使用 `split == test`、`2023-01-03..2025-06-30`。
- 未使用 future label 字段参与任何策略输入。
- 未用 test 结果调参、改 feature、改 label、改 split、改 turnover 阈值。

## 7. 产物

- `data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b6r_accounting_repair/phase_s1b6r_strategy_metrics_full_test.csv`
- `data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b6r_accounting_repair/phase_s1b6r_strategy_metrics_yearly.csv`
- `data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b6r_accounting_repair/phase_s1b6r_strategy_metrics_rolling_6m.csv`
- `data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b6r_accounting_repair/phase_s1b6r_strategy_metrics_rolling_12m.csv`
- `data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b6r_accounting_repair/phase_s1b6r_strategy_metrics_by_regime.csv`
- `data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b6r_accounting_repair/phase_s1b6r_daily_nav_by_strategy.csv`
- `data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b6r_accounting_repair/phase_s1b6r_action_audit_by_strategy.csv`
- `data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b6r_accounting_repair/phase_s1b6r_accounting_timeline_audit.json`
- `data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b6r_accounting_repair/phase_s1b6r_split_purity_and_lookahead_audit.json`
- `data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b6r_accounting_repair/phase_s1b6r_strategy_identity_audit.json`
- `data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b6r_accounting_repair/phase_s1b6r_forbidden_action_audit.json`
- `data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b6r_accounting_repair/phase_s1b6r_gate_summary.json`

## 8. 禁止事项执行结果

- 未训练 LTR / qlib。
- 未调参，未改 feature / label / split / universe。
- 未新增数据源，未联网。
- 未改前端/API，未触发 provider / accepted latest / monitor / trading chain。
- 未输出买卖、持有、仓位、收益承诺、胜率或上涨概率语义。

## 9. 结论

本轮只提交 accounting 修复后的完整日频回放事实结果，等待审查者决定 S1 结论。

推荐 gate：

```text
s1b6r_accounting_repair_complete_request_reviewer_decision
```
