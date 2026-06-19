# Phase E2 执行报告：宽候选 Row-aligned LTR 样本构建

生成时间：`2026-06-15T18:56:15+00:00`

## 1. 结论

- gate：`phase_e2_extended_oos_ltr_sample_passed`。
- 已基于 E1 raw OOS score 与 E1R 宽候选合同构建 2023-2025 LTR train 和 2026 untouched test 样本。
- 训练样本为旧 O4-style 宽候选集合，不是 top50-only；top50 仅作为特征和后续回放 rerank 边界。
- 未训练 qlib，未训练 LTR，未调参，未回放。

## 2. 输入 Artifact

- E1 raw score：`data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e1_frozen_qlib_training_and_oos_score/phasee1_raw_oos_score_rank_2023_2026.csv`
- E1R contract：`data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e1r_candidate_coverage_scope_repair/phasee1r_recommended_e2_candidate_contract.json`
- O3 row-aligned source：`data_tw/experiments/ltr_orthogonal_features_controlled/phase_o3_row_aligned_treatment_sample/phaseo3_treatment_candidate_sample.csv`
- O4 feature whitelist：`data_tw/experiments/ltr_orthogonal_features_controlled/phase_o4_controlled_treatment_ltr/phaseo4_training_feature_whitelist.csv`

## 3. Train / Test Row Alignment

| split | start | end | rows | dates | daily rows min/median/max | top50 rows | top50-only | max rank | median daily max rank |
| --- | --- | --- | ---: | ---: | --- | ---: | --- | ---: | ---: |
| ltr_test_2026 | 2026-01-02 | 2026-05-07 | 11822 | 79 | 149/150.0/150 | 3950 | False | 150 | 150.0 |
| ltr_train_2023_2025 | 2023-01-03 | 2025-12-31 | 107408 | 723 | 147/149.0/149 | 36150 | False | 149 | 149.0 |

## 4. Feature Schema

- feature count：`78`。
- control original features：`34`。
- orthogonal features：`44`。
- feature schema 完全来自 O4 whitelist，未新增 O2/O4 之外特征。

## 5. Label Audit

| split | rows | label non-null | label complete 10d | label used for training | test audit only | distribution |
| --- | ---: | ---: | ---: | --- | --- | --- |
| ltr_test_2026 | 11822 | 11822 | 11822 | False | True | `{"0": 5844, "1": 2354, "2": 1180, "3": 1180, "4": 1264}` |
| ltr_train_2023_2025 | 107408 | 107408 | 107408 | True | False | `{"0": 53258, "1": 21674, "2": 10827, "3": 10832, "4": 10817}` |

## 6. PIT Leakage Audit

| split | family | rows | missing_ratio | available_at violation | trade_date violation |
| --- | --- | ---: | ---: | ---: | ---: |
| ltr_test_2026 | institutional_flow | 11822 | 0.0 | 0 | 0 |
| ltr_train_2023_2025 | institutional_flow | 107408 | 0.0 | 0 | 0 |
| ltr_test_2026 | margin_short | 11822 | 0.01040433 | 0 | 0 |
| ltr_train_2023_2025 | margin_short | 107408 | 0.02741881 | 0 | 0 |

## 7. Score Provenance

- train/test score 均来自同一个 E1 frozen qlib raw OOS score artifact。
- train rows only from 2023-2025。
- test rows only from 2026。
- 2026 label 仅用于 audit / rank metric，不用于训练、调参或选择。
- qlib in-sample rows used for LTR train：`0`。
- walk-forward / multi-model score：`False`。

## 8. Candidate Scope

- 详见 `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e2_row_aligned_sample/phasee2_candidate_scope_audit.csv`。
- 未使用 top50/top30/full_market_trailing_value_top150_intersection 作为训练候选过滤。

## 9. Missing Report

- 详见 `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e2_row_aligned_sample/phasee2_missing_report.csv`。
- 正交特征缺失通过 O2 missing/asof flag 暴露；未因 O2 缺失删除候选。

## 10. 禁止事项审计

- 未训练 qlib / LTR。
- 未调参、未回放。
- 未改 split / label。
- 未新增 O4/O2 之外特征或数据源。
- 未触发 frontend/API/provider/accepted latest/monitor/交易链路。

## 11. 输出 Artifact

- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e2_row_aligned_sample/phasee2_sample_manifest.json`
- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e2_row_aligned_sample/phasee2_ltr_train_sample_2023_2025.csv`
- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e2_row_aligned_sample/phasee2_ltr_test_sample_2026.csv`
- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e2_row_aligned_sample/phasee2_feature_schema.csv`
- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e2_row_aligned_sample/phasee2_row_alignment_audit.csv`
- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e2_row_aligned_sample/phasee2_candidate_scope_audit.csv`
- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e2_row_aligned_sample/phasee2_score_provenance_audit.csv`
- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e2_row_aligned_sample/phasee2_pit_leakage_audit.csv`
- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e2_row_aligned_sample/phasee2_missing_report.csv`
- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e2_row_aligned_sample/phasee2_label_audit.csv`
- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e2_row_aligned_sample/phasee2_forbidden_action_audit.json`

## 12. 是否建议进入 E3

- 建议：允许进入 E3，gate 为 `phase_e2_extended_oos_ltr_sample_passed`。
