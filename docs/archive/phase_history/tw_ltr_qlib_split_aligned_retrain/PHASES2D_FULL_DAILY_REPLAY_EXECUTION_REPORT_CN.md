# Phase S2D 执行报告：Full Daily Replay

生成日期：2026-06-14T19:30:35+00:00

## 1. 本轮目标

只用 S2B fresh qlib score 与 S2C fresh LTR score，在 S1B6R next-day accounting 下对 fresh qlib / confirmed_exit / LTR simple / turnover-controlled 做 validation 与 untouched test 的完整日频回放。

## 2. Full Validation / Test 指标

| split | method | fee_tax_adjusted_net_return | max_drawdown | action_count | buy_count | sell_count | fee_and_tax | turnover_proxy | relative_return_vs_fresh_top50_adaptive |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| validation | fresh_qlib_top50_adaptive_baseline | 0.03827 | -0.151349 | 226 | 115 | 111 | 64493.47 | 22.391193 | 0.0 |
| validation | fresh_rank_rotate_top50 | -0.010622 | -0.167158 | 226 | 115 | 111 | 62702.51 | 22.32834 | -0.048892 |
| validation | fresh_confirmed_exit | -0.00101 | -0.167158 | 226 | 115 | 111 | 62926.64 | 22.358029 | -0.03928 |
| validation | fresh_ltr_simple | -0.057453 | -0.310589 | 226 | 115 | 111 | 60732.3 | 22.405397 | -0.095723 |
| validation | fresh_ltr_turnover_controlled | -0.023366 | -0.28577 | 36 | 19 | 17 | 9612.42 | 3.563704 | -0.061636 |
| test | fresh_qlib_top50_adaptive_baseline | 0.662457 | -0.088396 | 410 | 204 | 206 | 155259.42 | 40.692897 | 0.0 |
| test | fresh_rank_rotate_top50 | 0.637989 | -0.080952 | 409 | 204 | 205 | 154759.28 | 40.547617 | -0.024468 |
| test | fresh_confirmed_exit | 0.668523 | -0.08134 | 409 | 204 | 205 | 157103.46 | 40.583861 | 0.006066 |
| test | fresh_ltr_simple | 0.544381 | -0.132896 | 408 | 204 | 204 | 145915.05 | 40.342791 | -0.118076 |
| test | fresh_ltr_turnover_controlled | 0.615059 | -0.11131 | 63 | 34 | 29 | 22944.59 | 6.207343 | -0.047398 |

## 3. Coverage 差异

- validation qlib daily rows min/median/max: `84 / 87.0 / 89`
- validation LTR daily rows min/median/max: `82 / 86.0 / 89`
- test qlib daily rows min/median/max: `88 / 109.0 / 150`
- test LTR daily rows min/median/max: `87 / 109.0 / 149`

## 4. Segment / Rolling

- segment rows: `40`
- rolling 6m rows: `20`
- 12m rolling 未输出，原因是 frozen fresh test 仅 205 个交易日，不足以在 test 内独立形成可解释窗口。

## 5. 边界审计

- 未训练 qlib / LTR。
- 未调参，未重选 turnover-controlled config。
- 未新增策略变体。
- 未改 feature / label / split / 数据源。
- 未改前端/API，未触发 provider refresh/publish、accepted latest、monitor 或交易链路。

## 6. 主要产物

- `data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2d_full_daily_replay/phase_s2d_strategy_input_coverage_audit.json`
- `data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2d_full_daily_replay/phase_s2d_replay_metrics_by_strategy.csv`
- `data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2d_full_daily_replay/phase_s2d_replay_metrics_by_segment.csv`
- `data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2d_full_daily_replay/phase_s2d_rolling_6m_metrics.csv`
- `data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2d_full_daily_replay/phase_s2d_action_summary_by_strategy.csv`
- `data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2d_full_daily_replay/phase_s2d_accounting_audit.json`
- `data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2d_full_daily_replay/phase_s2d_split_tuning_audit.json`
- `data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2d_full_daily_replay/phase_s2d_forbidden_action_audit.json`
- `data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2d_full_daily_replay/phase_s2d_gate_summary.json`

## 7. 结论

本轮完成 S2D 授权范围内的 full daily replay 与 coverage / accounting / tuning / safety 审计。

推荐 gate：

```text
s2d_full_daily_replay_pass_request_s2e_fresh_retrain_conclusion_review
```
