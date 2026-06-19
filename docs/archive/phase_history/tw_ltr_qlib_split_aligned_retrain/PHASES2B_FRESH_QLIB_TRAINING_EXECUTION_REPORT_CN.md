# Phase S2B 执行报告：Fresh Qlib Training

生成日期：2026-06-14T18:53:09.874927+00:00

## 1. 执行范围

本轮严格按 `docs/tw_ltr_qlib_split_aligned_retrain/PHASES2ARR_REVIEW_AND_PHASES2B_FRESH_QLIB_TRAINING_WORK_CN.md` 执行，只训练 fresh qlib baseline 并生成 raw / post-filter score rank 与覆盖审计。

未执行：LTR 训练、组合回放、调参、split/feature/label 变更、provider/accepted latest/前端/API/monitor/交易链路。

## 2. 合同核对

- provider_uri: `/home/chuliyang/taiwan-stock-quant-platform/qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin`
- handler instruments: `all`
- train: `2017-01-10..2024-12-31`
- validation: `2025-01-01..2025-06-30`
- test: `2025-07-01..2026-05-07`
- handler end_time: `2026-05-07`
- fit_end_time: `2024-12-31`
- runtime thread count used: `4`

## 3. 训练与 score 产物

- recorder id: `s2b_manual_20260614T185309Z`
- model path: `data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2b_fresh_qlib_training/run/s2b_model.pkl`
- raw score file: `data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2b_fresh_qlib_training/phase_s2b_raw_score_rank.csv`
- post-filter score file: `data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2b_fresh_qlib_training/phase_s2b_post_filter_score_rank.csv`

## 4. 关键审计

- generated_yaml_matches_s2arr_contract = `True`
- provider_uri_matches_contract = `True`
- handler_instruments = `all`
- thread_policy_respected = `True`
- validation_score_coverage_complete_or_explained = `True`
- test_score_coverage_complete_or_explained = `True`
- no_post_test_data_used = `True`

## 5. Gate 建议

```text
s2b_fresh_qlib_training_pass_request_s2c_fresh_ltr_sample_and_training
```
