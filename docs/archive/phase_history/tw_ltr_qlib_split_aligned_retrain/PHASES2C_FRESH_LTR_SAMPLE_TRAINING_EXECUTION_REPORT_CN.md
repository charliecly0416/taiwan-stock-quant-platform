# Phase S2C 执行报告：Fresh LTR Sample And Training

生成日期：2026-06-14T19:17:07+00:00

## 1. 本轮目标

只基于 S2B post-filter qlib score/rank 构建 fresh LTR 样本，完成 label horizon / split purity 审计，训练一个 common fresh LTR ranker，并输出 train / validation / test 的 LTR score/rank 覆盖产物。

## 2. 执行范围

- 复用 S2B post-filter `qlib_score_raw` 与 `qlib_rank`。
- 复用 S1B3 冻结 34 个 feature、固定 label 和 LightGBM.LGBMRanker 参数。
- 训练前按 `training_row_eligible == true` 过滤，即 `sample_complete == true` 且 `label_end_date_10d` 不越过各 split 终点。
- `fresh_ltr_simple` 与 `fresh_ltr_turnover_controlled` 共用同一训练分数；后者只复用已冻结 usage config，不在本轮重选。

## 3. Label Horizon / Split Purity

| split | split_start | split_end | row_count | sample_complete | purged_from_sample_complete | training_row_eligible | overflow_date_min | overflow_date_max |
| --- | --- | --- | ---: | ---: | ---: | ---: | --- | --- |
| train | 2017-01-10 | 2024-12-31 | 136685 | 132875 | 840 | 135845 | 2024-12-18 | 2024-12-31 |
| validation | 2025-01-01 | 2025-06-30 | 10068 | 9958 | 840 | 9228 | 2025-06-17 | 2025-06-30 |
| test | 2025-07-01 | 2026-05-07 | 22613 | 22474 | 1394 | 21215 | 2026-04-23 | 2026-05-07 |

purge 规则：`drop sample_complete rows whose label_end_date_10d exceeds their split end date before training eligibility`。

## 4. Score Coverage By Split

| split | date_start | date_end | date_count | row_count | selected_min | selected_median | selected_max | ltr_score_missing | ltr_rank_missing |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| test | 2025-07-01 | 2026-05-07 | 205 | 22474 | 87 | 109.0 | 149 | 0 | 0 |
| train | 2017-01-17 | 2024-12-31 | 1934 | 132875 | 12 | 68.0 | 89 | 0 | 0 |
| validation | 2025-01-02 | 2025-06-30 | 116 | 9958 | 82 | 86.0 | 89 | 0 | 0 |

## 5. 主要产物

- `data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2c_fresh_ltr_sample_training/phase_s2c_ltr_samples.csv`
- `data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2c_fresh_ltr_sample_training/phase_s2c_ltr_sample_schema.json`
- `data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2c_fresh_ltr_sample_training/phase_s2c_label_horizon_split_purity_audit.json`
- `data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2c_fresh_ltr_sample_training/phase_s2c_training_manifest.json`
- `data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2c_fresh_ltr_sample_training/phase_s2c_ltr_model_manifest.json`
- `data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2c_fresh_ltr_sample_training/phase_s2c_ltr_score_rank.csv`
- `data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2c_fresh_ltr_sample_training/phase_s2c_ltr_score_coverage_by_date.csv`
- `data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2c_fresh_ltr_sample_training/phase_s2c_ltr_score_coverage_by_split.csv`
- `data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2c_fresh_ltr_sample_training/phase_s2c_forbidden_action_audit.json`
- `data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2c_fresh_ltr_sample_training/phase_s2c_gate_summary.json`

## 6. 边界审计

- 未跑 replay。
- 未比较收益、回撤、换手、费用或默认策略。
- 未调参，未做 parameter search。
- 未新增 feature、label、数据源。
- 未改前端/API。
- 未触发 provider refresh/publish、accepted latest switching、monitor 或交易链路。

## 7. 结论

本轮已完成 S2C 授权范围内的 fresh sample 构建、purity 审计、common fresh LTR 训练和 score/rank 物化。

推荐 gate：

```text
s2c_fresh_ltr_training_pass_request_s2d_full_daily_replay
```
