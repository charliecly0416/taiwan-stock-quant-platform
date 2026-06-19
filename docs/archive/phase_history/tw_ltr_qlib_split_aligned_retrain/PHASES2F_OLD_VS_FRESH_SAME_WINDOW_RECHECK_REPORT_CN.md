# Phase S2F 复核报告：旧 qlib + 新 LTR vs fresh qlib 同窗口比较

生成时间：2026-06-15T13:37:43+00:00

## 1. 复核问题

用户质疑 `旧 qlib + 新 LTR simple` 的历史收益异常高，要求在同一测试区间、同一回放引擎、同一费用税费和 next-day execution 口径下，与 fresh qlib / fresh LTR 重新比较。

固定测试区间：`2025-07-01..2026-05-07`。

## 2. 同窗口结果

| method | fee_tax_adjusted_net_return | max_drawdown | action_count | fee_and_tax | relative_return_vs_fresh_top50 | relative_drawdown_vs_fresh_top50 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| old_qlib_new_ltr_phase1c_simple | 0.721631 | -0.05083 | 405 | 157661.34 | 0.059174 | 0.037566 |
| fresh_qlib_top50_adaptive_baseline | 0.662457 | -0.088396 | 410 | 155259.42 | 0.0 | 0.0 |
| fresh_ltr_simple | 0.544381 | -0.132896 | 408 | 145915.05 | -0.118076 | -0.0445 |
| fresh_ltr_turnover_controlled | 0.615059 | -0.11131 | 63 | 22944.59 | -0.047398 | -0.022914 |

## 3. 直接判断

- `old_qlib_new_ltr_phase1c_simple` 同窗口收益为 `0.721631`。
- `fresh_qlib_top50_adaptive_baseline` 同窗口收益为 `0.662457`。
- 旧 LTR 相对 fresh top50 差值为 `0.059174`。

若旧 LTR 没有显著领先，则此前 `+355%` 级别结果不能作为同窗口优势证据；若仍显著领先，则需要继续做持仓贡献和异常价格审计。

## 4. Coverage 审计

- 日期数：`205`
- old LTR daily rows min/median/max：`147 / 149.0 / 150`
- fresh top50 daily rows min/median/max：`88 / 109.0 / 150`
- fresh LTR daily rows min/median/max：`87 / 109.0 / 149`

## 5. 边界

- 本轮不训练 qlib / LTR。
- 不调参、不新增策略、不改 split / feature / label。
- 不改前端/API，不触发 provider/accepted latest/monitor/交易链路。

## 6. 产物

- `data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2f_old_vs_fresh_same_window_recheck/phase_s2f_same_window_metrics.csv`
- `data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2f_old_vs_fresh_same_window_recheck/phase_s2f_same_window_daily_nav.csv`
- `data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2f_old_vs_fresh_same_window_recheck/phase_s2f_same_window_action_audit.csv`
- `data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2f_old_vs_fresh_same_window_recheck/phase_s2f_same_window_coverage_audit.json`
- `data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2f_old_vs_fresh_same_window_recheck/phase_s2f_same_window_gate_summary.json`
