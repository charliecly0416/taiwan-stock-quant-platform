# Phase Q1 执行报告：Orthogonal Qlib Feature Join 与样本对齐

生成时间：`2026-06-15T16:30:05+00:00`

## 1. 结论

- gate：`phase_q1_orthogonal_qlib_feature_join_passed`。
- 本阶段只做 S2B fresh qlib control row universe 与 O2 PIT-safe 正交特征的 as-of join 审计。
- 未训练 Orthogonal Fresh Qlib，未回放，未比较收益。
- 未改 Alpha158、label、split、universe、model params、post-score filter 或 replay 合同。
- 未引入 LTR，未新增 filter / market gate / turnover rule。

## 2. 输入 Artifact

- Q0 report：`docs/tw_orthogonal_fresh_qlib_controlled/PHASEQ0_CONTROL_AND_FEATURE_CONTRACT_EXECUTION_REPORT_CN.md`
- S2B raw score row universe：`data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2b_fresh_qlib_training/phase_s2b_raw_score_rank.csv`
- S2B generated config：`data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2b_fresh_qlib_training/phase_s2b_generated_qlib_config.yaml`
- S2D gate：`data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2d_full_daily_replay/phase_s2d_gate_summary.json`
- O2 normalized features：`data_tw/experiments/ltr_orthogonal_features_controlled/phase_o2_pit_safe_feature_builder/normalized_feature_daily.csv`
- O2 feature dictionary：`data_tw/experiments/ltr_orthogonal_features_controlled/phase_o2_pit_safe_feature_builder/feature_dictionary.csv`
- O2 PIT audit：`data_tw/experiments/ltr_orthogonal_features_controlled/phase_o2_pit_safe_feature_builder/pit_leakage_audit.csv`
- O2 lineage audit：`data_tw/experiments/ltr_orthogonal_features_controlled/phase_o2_pit_safe_feature_builder/pit_lineage_audit.csv`

## 3. Row Alignment

- control rows：`326915`。
- treatment rows：`326915`。
- symbol count：`150`。
- date range：`2017-01-10`..`2026-05-07`。
- split counts：`{'test': 30750, 'train': 278765, 'validation': 17400}`。

| check | control | treatment | pass |
| --- | --- | --- | --- |
| row_count | 326915 | 326915 | True |
| control_row_id_exact_match | ordered | ordered | True |
| date_instrument_split_exact_match | date|instrument|split | date|instrument|split | True |
| symbol_count | 150 | 150 | True |

## 4. Schema Diff

- added columns：`58`。
- removed control columns：`[]`。
- disallowed added columns：`[]`。
- added columns 仅来自 Q0 白名单正交特征、missing/delay/lineage/PIT audit 字段。

## 5. Missing Report

| feature_family | control_rows | missing_rows | missing_ratio | matched_rows | symbol_count | date_min | date_max |
| --- | --- | --- | --- | --- | --- | --- | --- |
| institutional_flow | 326915 | 171417 | 0.52434731 | 155498 | 150 | 2017-01-10 | 2026-05-07 |
| margin_short | 326915 | 176221 | 0.53904226 | 150694 | 150 | 2017-01-10 | 2026-05-07 |

## 6. PIT / available_at Join

- join 口径：按 `instrument + signal_asof(date)`，对每个 family 使用 `available_at <= signal_asof` 的最近一条正交记录。
- 未人工提前 `available_at`，未用未来 trade_date，未因正交缺失删行。

| feature_family | rows_checked | used_available_at_gt_signal_asof_rows | used_trade_date_gt_signal_asof_rows | matched_available_at_min | matched_available_at_max | matched_trade_date_min | matched_trade_date_max | pit_pass |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| institutional_flow | 326915 | 0 | 0 | 2022-01-04 | 2026-05-07 | 2022-01-03 | 2026-05-06 | True |
| margin_short | 326915 | 0 | 0 | 2022-01-04 | 2026-05-07 | 2022-01-03 | 2026-05-06 | True |

## 7. 必须满足的等式

- `control_label == treatment_label`：`True`。Q1 未改 Alpha158 handler/label config。
- `control_split == treatment_split`：`True`。
- `control_universe_policy == treatment_universe_policy`：`True`。
- `only_added_columns == approved_orthogonal_features_and_missing_flags`：`True`。

## 8. Forbidden Action Audit

- 未训练模型。
- 未调用或引入 LTR。
- 未调参。
- 未改 label / split / universe / Alpha158 / post-score filter / replay。
- 未触发 frontend / API / provider / accepted latest / monitor / broker / orders / quick-trade。

## 9. 输出 Artifact

| artifact | path |
| --- | --- |
| treatment_joined_sample | data_tw/experiments/orthogonal_fresh_qlib_controlled/phase_q1_orthogonal_qlib_feature_join/treatment_joined_sample.csv |
| schema_diff | data_tw/experiments/orthogonal_fresh_qlib_controlled/phase_q1_orthogonal_qlib_feature_join/schema_diff.csv |
| row_alignment_audit | data_tw/experiments/orthogonal_fresh_qlib_controlled/phase_q1_orthogonal_qlib_feature_join/row_alignment_audit.csv |
| missing_report | data_tw/experiments/orthogonal_fresh_qlib_controlled/phase_q1_orthogonal_qlib_feature_join/missing_report.csv |
| pit_leakage_audit | data_tw/experiments/orthogonal_fresh_qlib_controlled/phase_q1_orthogonal_qlib_feature_join/pit_leakage_audit.csv |
| available_at_join_audit | data_tw/experiments/orthogonal_fresh_qlib_controlled/phase_q1_orthogonal_qlib_feature_join/available_at_join_audit.csv |
| forbidden_action_audit | data_tw/experiments/orthogonal_fresh_qlib_controlled/phase_q1_orthogonal_qlib_feature_join/forbidden_action_audit.json |
| dataset_config_draft | data_tw/experiments/orthogonal_fresh_qlib_controlled/phase_q1_orthogonal_qlib_feature_join/orthogonal_fresh_qlib_dataset_config_draft.yaml |

## 10. 是否建议进入 Q2

- 建议允许进入 Q2：`是`，前提是审查者接受 Q1 的 as-of join 方案与 schema diff。
- Q2 仍不得改 Q0 冻结合同；若训练实现需要改 label/split/universe/model/replay，应停止并请求确认。
