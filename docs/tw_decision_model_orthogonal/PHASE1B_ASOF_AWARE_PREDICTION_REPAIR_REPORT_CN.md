# Phase 1B Asof-aware Prediction Repair 工作报告

- 生成时间：`2026-06-11T07:57:09+00:00`
- 执行范围：2023-2024 qlib prediction artifact 的 asof-aware universe repair 与覆盖审计。
- 禁止范围：未联网、未使用 token、未重拉数据、未训练模型、未写入或重建 provider、未 provider refresh/publish、未 accepted latest switching、未进入 Phase2、未触碰交易路径。

## 1. 修复口径

- 候选池从 static accepted universe 开始。
- 每个 asof 只保留 `option_c_150_normalized/{symbol}.csv` 存在该日期记录的 symbol。
- 同时要求 provider instrument 日期区间覆盖该 asof，且 `open/high/low/close/volume/vwap/factor` feature inventory 完整。
- formal validation 在过滤后的 asof-aware universe 上执行；full repair 未使用 `--research-only-skip-formal-validation`。
- prediction.csv 保持标准列 `datetime,instrument,score`。

## 2. Smoke Validation

| asof | status | candidate_count | active_count | excluded_count | prediction_rows | prediction_columns | formal_validation_bypassed_for_research_only |
|---|---|---|---|---|---|---|---|
| 2023-01-03 | pass | 150 | 149 | 1 | 149 | datetime,instrument,score | False |
| 2024-01-02 | pass | 150 | 149 | 1 | 149 | datetime,instrument,score | False |
| 2024-11-01 | pass | 150 | 150 | 0 | 150 | datetime,instrument,score | False |

## 3. Full Coverage

- 2023-2024 provider calendar days：`481`
- repaired prediction files：`481`
- missing prediction days：`0`
- all calendar days have prediction：`True`
- prediction column sets：`['datetime,instrument,score']`

| month | prediction_file_count | rows | symbols_min | symbols_max | days | formal_pass_count | formal_fail_count | no_prediction |
|---|---|---|---|---|---|---|---|---|
| 2023-01 | 13 | 1937 | 149 | 149 | 13 | 13 | 0 | 0 |
| 2023-02 | 18 | 2682 | 149 | 149 | 18 | 18 | 0 | 0 |
| 2023-03 | 23 | 3427 | 149 | 149 | 23 | 23 | 0 | 0 |
| 2023-04 | 17 | 2533 | 149 | 149 | 17 | 17 | 0 | 0 |
| 2023-05 | 22 | 3278 | 149 | 149 | 22 | 22 | 0 | 0 |
| 2023-06 | 20 | 2980 | 149 | 149 | 20 | 20 | 0 | 0 |
| 2023-07 | 21 | 3129 | 149 | 149 | 21 | 21 | 0 | 0 |
| 2023-08 | 22 | 3278 | 149 | 149 | 22 | 22 | 0 | 0 |
| 2023-09 | 20 | 2980 | 149 | 149 | 20 | 20 | 0 | 0 |
| 2023-10 | 20 | 2980 | 149 | 149 | 20 | 20 | 0 | 0 |
| 2023-11 | 22 | 3278 | 149 | 149 | 22 | 22 | 0 | 0 |
| 2023-12 | 21 | 3129 | 149 | 149 | 21 | 21 | 0 | 0 |
| 2024-01 | 22 | 3278 | 149 | 149 | 22 | 22 | 0 | 0 |
| 2024-02 | 13 | 1937 | 149 | 149 | 13 | 13 | 0 | 0 |
| 2024-03 | 21 | 3129 | 149 | 149 | 21 | 21 | 0 | 0 |
| 2024-04 | 20 | 2980 | 149 | 149 | 20 | 20 | 0 | 0 |
| 2024-05 | 22 | 3278 | 149 | 149 | 22 | 22 | 0 | 0 |
| 2024-06 | 19 | 2831 | 149 | 149 | 19 | 19 | 0 | 0 |
| 2024-07 | 21 | 3129 | 149 | 149 | 21 | 21 | 0 | 0 |
| 2024-08 | 22 | 3278 | 149 | 149 | 22 | 22 | 0 | 0 |
| 2024-09 | 20 | 2980 | 149 | 149 | 20 | 20 | 0 | 0 |
| 2024-10 | 19 | 2831 | 149 | 149 | 19 | 19 | 0 | 0 |
| 2024-11 | 21 | 3150 | 150 | 150 | 21 | 21 | 0 | 0 |
| 2024-12 | 22 | 3300 | 150 | 150 | 22 | 22 | 0 | 0 |

## 4. Exclusion Summary

| symbol | reason | excluded_days |
|---|---|---|
| TW7769 | missing_source_asof | 438 |
| TW7769 | outside_instrument_date_range | 438 |

TW7769 说明：`2024-11-01` 前因 `missing_source_asof` 与 `outside_instrument_date_range` 被排除；`2024-11-01` 起 smoke validation 显示 active universe 为 150、excluded 为 0，可进入 universe。

## 5. Provenance 与安全边界

- frozen recorder/model provenance：见每个 run 的 `run_metadata.json`，batch root：`qlib_pipeline/data_tw/experiments/option_c_historical_signal_backfill/option_c_historical_backfill_20230101_20241231_asof_aware_research_only`。
- formal validation bypass count：`0`
- refresh triggered count：`0`
- publish triggered count：`0`
- provider mutation triggered count：`0`
- model retraining count：`0`

## 6. 产物

- 月度覆盖：`data_tw/experiments/decision_orthogonal/phase1b_asof_aware_prediction_repair_monthly_coverage.csv`
- 排除汇总：`data_tw/experiments/decision_orthogonal/phase1b_asof_aware_prediction_repair_excluded_summary.csv`
- smoke validation：`data_tw/experiments/decision_orthogonal/phase1b_asof_aware_prediction_repair_smoke_validation.csv`
- summary：`data_tw/experiments/decision_orthogonal/phase1b_asof_aware_prediction_repair_summary.json`
