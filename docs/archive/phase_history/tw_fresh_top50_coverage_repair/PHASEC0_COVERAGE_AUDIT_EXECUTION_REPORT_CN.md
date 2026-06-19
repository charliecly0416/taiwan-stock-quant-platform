# Phase C0 覆盖审计执行报告

生成时间：2026-06-15T07:33:41+00:00

## 结论

fresh top50 覆盖不足是事实，根因在 S2B post-score universe filter：raw fresh qlib 在测试窗口每日 150 支，但 post-filter/replay-ready 只有 88/109/150。该缺口可用本地 raw qlib score、normalized price 与既有 feature 逻辑离线修复。

## Source Audit

| artifact | role | rows_in_window | daily_min | daily_median | daily_max |
| --- | --- | --- | --- | --- | --- |
| data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2b_fresh_qlib_training/phase_s2b_raw_score_rank.csv | fresh raw qlib score | 30750 | 150 | 150.0 | 150 |
| data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2b_fresh_qlib_training/phase_s2b_post_filter_score_rank.csv | fresh S2B post-filter score | 22613 | 88 | 109.0 | 150 |
| data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2d_full_daily_replay/phase_s2d_replay_ready_scores.csv | fresh S2D replay-ready adaptive | 22613 | 88 | 109.0 | 150 |
| data_tw/experiments/ltr_rerank_regime_turnover/phase3a0_frozen_phase1c_scores/phase3a0_frozen_phase1c_row_scores.csv | old Phase1C frozen score | 30475 | 147 | 149.0 | 150 |

## Missing Reason

| reason | key_count |
| --- | --- |
| missing_fresh_raw_qlib_score | 0 |
| filtered_by_s2b_post_score_universe_policy | 7952 |
| present_post_filter_but_missing_replay_ready_adaptive | 0 |
| raw_top150_missing_local_price | 0 |
| fresh_replay_ready_not_in_old_phase1c | 90 |

## 边界

未训练 qlib/LTR，未改原 S2B/S2C/S2D/S2F/Phase1C 产物，未触发 provider/accepted latest/monitor/交易/前端/API。
