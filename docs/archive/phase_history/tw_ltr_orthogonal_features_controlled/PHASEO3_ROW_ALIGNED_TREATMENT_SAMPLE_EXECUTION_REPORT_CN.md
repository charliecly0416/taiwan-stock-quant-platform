# Phase O3 执行报告：受控样本拼接

生成时间：`2026-06-15T11:22:54+00:00`

## 1. 执行结论

本轮只读取 Phase1C control LTR sample 与 O2 PIT-safe daily features，按 `available_at <= sample_date` 做 row-aligned treatment candidate 拼接。

推荐 gate：

```text
phase_o3_treatment_sample_row_aligned_passed
```

## 2. 边界

- 未训练 qlib/LTR。
- 未做收益率回放。
- 未修改 Phase1C control。
- 未改 label / 原始特征 / 训练窗口 / 回放窗口。
- 未新增过滤器、阈值、market gate、turnover rule。
- 未触发 frontend/API/provider/accepted latest/monitor/交易链路。

## 3. Row Alignment

| metric | value |
| --- | --- |
| control_rows | 159993 |
| treatment_rows | 159993 |
| control_label_hash | 1c0068a392ea2a990a77e50a3998d4990c19015bcfd9eb68415308405fd91277 |
| treatment_label_hash | 1c0068a392ea2a990a77e50a3998d4990c19015bcfd9eb68415308405fd91277 |
| control_original_feature_hash | c8e69af04c392a8b7f803bff784f10a0fdd61cc8790517776f62d028b7a750a3 |
| treatment_original_feature_hash | c8e69af04c392a8b7f803bff784f10a0fdd61cc8790517776f62d028b7a750a3 |
| control_identity_hash | 0a666a52524047a381c7b820a235ac77b45d6a8e28700baf15989799507d07ea |
| treatment_identity_hash | 0a666a52524047a381c7b820a235ac77b45d6a8e28700baf15989799507d07ea |
| row_identity_mismatch_count | 0 |
| row_label_mismatch_count | 0 |
| row_original_feature_mismatch_count | 0 |
| added_column_count | 62 |

## 4. PIT Leakage Audit

| feature_family | used_available_at_gt_sample_date_rows | used_trade_date_gt_sample_date_rows | missing_rows | missing_ratio |
| --- | --- | --- | --- | --- |
| institutional_flow | 0 | 0 | 595 | 0.003718912702430731 |
| margin_short | 0 | 0 | 5417 | 0.03385773127574331 |

## 5. Rolling Window available_at 单调审计

- rolling_window_available_at_monotonic_groups：`0`

## 6. 新增列范围

- added_column_count：`62`
- 新增列只来自 O2 feature dictionary 的 institutional_flow / margin_short 特征与 PIT lineage metadata。

## 7. 输出产物

- `data_tw/experiments/ltr_orthogonal_features_controlled/phase_o3_row_aligned_treatment_sample/phaseo3_treatment_candidate_sample.csv`
- `data_tw/experiments/ltr_orthogonal_features_controlled/phase_o3_row_aligned_treatment_sample/phaseo3_row_alignment_audit.csv`
- `data_tw/experiments/ltr_orthogonal_features_controlled/phase_o3_row_aligned_treatment_sample/phaseo3_row_hash_audit.csv`
- `data_tw/experiments/ltr_orthogonal_features_controlled/phase_o3_row_aligned_treatment_sample/phaseo3_feature_schema_diff.csv`
- `data_tw/experiments/ltr_orthogonal_features_controlled/phase_o3_row_aligned_treatment_sample/phaseo3_pit_leakage_audit.csv`
- `data_tw/experiments/ltr_orthogonal_features_controlled/phase_o3_row_aligned_treatment_sample/phaseo3_missing_by_symbol.csv`
- `data_tw/experiments/ltr_orthogonal_features_controlled/phase_o3_row_aligned_treatment_sample/phaseo3_rolling_available_at_monotonic_audit.csv`
- `data_tw/experiments/ltr_orthogonal_features_controlled/phase_o3_row_aligned_treatment_sample/phaseo3_summary.json`

## 8. 后续边界

O3 通过只说明样本行级拼接合同通过；仍不得视为已训练或已证明收益率优劣。进入 O4 前仍需审查。
