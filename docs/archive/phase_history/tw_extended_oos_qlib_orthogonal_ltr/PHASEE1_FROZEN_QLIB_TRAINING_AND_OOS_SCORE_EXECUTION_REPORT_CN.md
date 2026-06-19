# Phase E1 执行报告：2018-2022 Frozen Qlib 训练与 OOS 打分

生成时间：`2026-06-15T18:30:52+00:00`

## 1. 结论

- gate：`phase_e1_frozen_qlib_oos_score_completed`。
- 已训练一个只使用 `2018-01-01..2022-12-31` 的 frozen qlib。
- `2023-01-01..2026-05-07` 仅作为同一模型 OOS predict 区间。
- 未调 qlib 参数，未训练 LTR，未回放，未触发 provider / accepted latest / frontend / API / monitor / 交易链路。

## 2. 合同核对

- provider：`qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin`
- S2B 参数来源：`data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2b_fresh_qlib_training/phase_s2b_generated_qlib_config.yaml`
- train：`2018-01-01..2022-12-31`
- valid：`2022-07-01..2022-12-31`，仍在 qlib train 窗口内。
- oos score：`2023-01-01..2026-05-07`
- handler fit：`2018-01-01..2022-12-31`
- runtime thread count used：`4`

## 3. OOS Score 覆盖

| split | start | end | dates | score rows | selected min/median/max | top50 min/median/max |
| --- | --- | --- | ---: | ---: | --- | --- |
| oos_ltr_train_window | 2023-01-03 | 2025-12-31 | 723 | 61905 | 71/85.0/110 | 50/50.0/50 |
| oos_untouched_test_window | 2026-01-02 | 2026-05-07 | 79 | 9792 | 115/122.0/150 | 50/50.0/50 |

## 4. 输出 Artifact

- manifest：`data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e1_frozen_qlib_training_and_oos_score/phasee1_training_manifest.json`
- model：`data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e1_frozen_qlib_training_and_oos_score/run/phasee1_frozen_qlib_model.pkl`
- generated config：`data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e1_frozen_qlib_training_and_oos_score/phasee1_generated_qlib_config.yaml`
- raw OOS score：`data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e1_frozen_qlib_training_and_oos_score/phasee1_raw_oos_score_rank_2023_2026.csv`
- post-filter score：`data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e1_frozen_qlib_training_and_oos_score/phasee1_post_filter_oos_score_rank_2023_2026.csv`
- top50 score：`data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e1_frozen_qlib_training_and_oos_score/phasee1_top50_oos_score_rank_2023_2026.csv`
- coverage by date：`data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e1_frozen_qlib_training_and_oos_score/phasee1_oos_score_coverage_by_date.csv`
- coverage by split：`data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e1_frozen_qlib_training_and_oos_score/phasee1_oos_score_coverage_by_split.csv`

## 5. Leakage / Resource / 禁止事项审计

- qlib_train_uses_only_2018_2022：`True`
- oos_not_in_fit_or_valid_sets：`True`
- no_parameter_search：`True`
- thread_policy_respected：`True`
- same_model_for_all_oos_scores：`True`
- provider_refresh_publish_performed：`False`
- frontend_api_touched：`False`
- monitor_or_trading_chain_touched：`False`

## 6. 是否建议进入 E2

- 建议：允许进入 E2，gate 为 `phase_e1_frozen_qlib_oos_score_completed`。
