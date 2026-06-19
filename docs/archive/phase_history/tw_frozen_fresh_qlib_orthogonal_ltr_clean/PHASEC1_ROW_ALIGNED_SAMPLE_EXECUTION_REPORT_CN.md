# Phase C1 执行报告：Row-aligned LTR 样本构建

生成时间：`2026-06-15T17:43:14+00:00`

## 1. 结论

- gate：`phase_c1_clean_stacking_sample_passed`。
- 已基于同一个 frozen fresh qlib S2B OOS score 构建 2025 train 与 2026 untouched test 的 top50 row-aligned 样本。
- 未训练 qlib，未训练 LTR，未调参，未回放。
- 未使用 qlib 2017..2024 in-sample score，未引入 walk-forward OOS 或多模型 score。

## 2. 输入 Artifact

- C0 manifest：`data_tw/experiments/frozen_fresh_qlib_orthogonal_ltr_clean/phase_c0_contract_and_feasibility/phasec0_contract_manifest.json`
- frozen fresh qlib score：`data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2b_fresh_qlib_training/phase_s2b_post_filter_score_rank.csv`
- O3 row-aligned source：`data_tw/experiments/ltr_orthogonal_features_controlled/phase_o3_row_aligned_treatment_sample/phaseo3_treatment_candidate_sample.csv`
- O4 feature whitelist：`data_tw/experiments/ltr_orthogonal_features_controlled/phase_o4_controlled_treatment_ltr/phaseo4_training_feature_whitelist.csv`
- O4 model config source：`data_tw/experiments/ltr_orthogonal_features_controlled/phase_o4_controlled_treatment_ltr/phaseo4_training_manifest.json`

## 3. Train / Test Row Alignment

| split | start | end | rows | dates | daily rows min/median/max | duplicate keys | top50 rows | after qlib train end |
| --- | --- | --- | ---: | ---: | --- | ---: | ---: | --- |
| ltr_test_2026 | 2026-01-02 | 2026-05-07 | 3950 | 79 | 50/50.0/50 | 0 | 3950 | True |
| ltr_train_2025 | 2025-01-02 | 2025-12-31 | 12100 | 242 | 50/50.0/50 | 0 | 12100 | True |

## 4. Feature Schema

- feature count：`78`。
- control original features：`34`。
- orthogonal features：`44`。
- feature schema 完全来自 O4 whitelist，未新增 O4/O2 之外特征族。

## 5. Label Audit

| split | rows | label non-null | label complete 10d | label used for training | test audit only | distribution |
| --- | ---: | ---: | ---: | --- | --- | --- |
| ltr_test_2026 | 3950 | 3950 | 3950 | False | True | `{"0": 1905, "1": 711, "2": 410, "3": 454, "4": 470}` |
| ltr_train_2025 | 12100 | 12100 | 12100 | True | False | `{"0": 5908, "1": 2120, "2": 1246, "3": 1403, "4": 1423}` |

## 6. PIT Leakage Audit

| split | family | rows | missing_ratio | available_at violation | trade_date violation |
| --- | --- | ---: | ---: | ---: | ---: |
| ltr_test_2026 | institutional_flow | 3950 | 0.0 | 0 | 0 |
| ltr_train_2025 | institutional_flow | 12100 | 0.0 | 0 | 0 |
| ltr_test_2026 | margin_short | 3950 | 0.00835443 | 0 | 0 |
| ltr_train_2025 | margin_short | 12100 | 0.03371901 | 0 | 0 |

## 7. Score Provenance

- train/test score 均来自同一个 frozen fresh qlib S2B post-filter score artifact。
- train rows only from 2025。
- test rows only from 2026。
- 2026 label 仅用于 audit / rank metric，不用于训练、调参或选择。
- qlib in-sample rows used for LTR train：`0`。
- walk-forward / multi-model score：`False`。

## 8. Missing Report

- 详见 `data_tw/experiments/frozen_fresh_qlib_orthogonal_ltr_clean/phase_c1_row_aligned_sample/phasec1_missing_report.csv`。
- 正交特征缺失通过 O2 missing/asof flag 暴露；未新增补数规则。

## 9. 禁止事项审计

- 未训练 qlib / LTR。
- 未调参、未回放。
- 未改 split / label。
- 未新增 O4/O2 之外特征或数据源。
- 未触发 frontend/API/provider/accepted latest/monitor/交易链路。

## 10. 输出 Artifact

- `data_tw/experiments/frozen_fresh_qlib_orthogonal_ltr_clean/phase_c1_row_aligned_sample/phasec1_sample_manifest.json`
- `data_tw/experiments/frozen_fresh_qlib_orthogonal_ltr_clean/phase_c1_row_aligned_sample/phasec1_ltr_train_sample_2025.csv`
- `data_tw/experiments/frozen_fresh_qlib_orthogonal_ltr_clean/phase_c1_row_aligned_sample/phasec1_ltr_test_sample_2026.csv`
- `data_tw/experiments/frozen_fresh_qlib_orthogonal_ltr_clean/phase_c1_row_aligned_sample/phasec1_feature_schema.csv`
- `data_tw/experiments/frozen_fresh_qlib_orthogonal_ltr_clean/phase_c1_row_aligned_sample/phasec1_row_alignment_audit.csv`
- `data_tw/experiments/frozen_fresh_qlib_orthogonal_ltr_clean/phase_c1_row_aligned_sample/phasec1_score_provenance_audit.csv`
- `data_tw/experiments/frozen_fresh_qlib_orthogonal_ltr_clean/phase_c1_row_aligned_sample/phasec1_pit_leakage_audit.csv`
- `data_tw/experiments/frozen_fresh_qlib_orthogonal_ltr_clean/phase_c1_row_aligned_sample/phasec1_missing_report.csv`
- `data_tw/experiments/frozen_fresh_qlib_orthogonal_ltr_clean/phase_c1_row_aligned_sample/phasec1_label_audit.csv`
- `data_tw/experiments/frozen_fresh_qlib_orthogonal_ltr_clean/phase_c1_row_aligned_sample/phasec1_forbidden_action_audit.json`

## 11. 是否建议进入 C2

- 建议：允许进入 C2，gate 为 `phase_c1_clean_stacking_sample_passed`。
