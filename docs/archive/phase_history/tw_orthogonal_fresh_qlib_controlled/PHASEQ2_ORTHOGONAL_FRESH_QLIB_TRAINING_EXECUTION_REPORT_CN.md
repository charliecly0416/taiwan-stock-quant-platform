# Phase Q2 执行报告：Orthogonal Fresh Qlib Training

生成时间：`2026-06-15T16:43:06.767296+00:00`

## 1. 结论

- gate：`phase_q2_orthogonal_fresh_qlib_training_completed`。
- 已按原 S2B fresh qlib 合同训练 Orthogonal Fresh Qlib。
- 唯一变化：在原 Alpha158 特征之外追加 Q1 通过的正交数值特征与 missing/delay flag。
- 未回放，未比较收益，未改默认策略。
- 未引入 LTR，未触发 frontend / API / provider / accepted latest / monitor / broker / orders / quick-trade。

## 2. 训练合同

- provider：`qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin`
- model family：`qlib.contrib.model.gbdt.LGBModel`
- successful thread count：`4`
- train：`2017-01-10..2024-12-31`
- validation：`2025-01-01..2025-06-30`
- test：`2025-07-01..2026-05-07`
- handler：`2015-05-04..2026-05-07`
- fit：`2015-05-04..2024-12-31`

## 3. Row / Feature Summary

- raw score rows：`326915`
- post-filter rows：`169366`
- symbol count：`150`
- Alpha158 feature count：`158`
- orthogonal training feature count：`42`
- final training feature count：`200`
- excluded non-training audit fields：`['institutional_flow_delay_reason', 'institutional_flow_lineage_source', 'institutional_flow_matched_available_at', 'institutional_flow_matched_trade_date', 'institutional_flow_raw_snapshot_id', 'institutional_flow_raw_snapshot_path', 'institutional_flow_used_available_at_gt_signal_asof', 'institutional_flow_used_trade_date_gt_signal_asof', 'margin_short_delay_reason', 'margin_short_lineage_source', 'margin_short_matched_available_at', 'margin_short_matched_trade_date', 'margin_short_raw_snapshot_id', 'margin_short_raw_snapshot_path', 'margin_short_used_available_at_gt_signal_asof', 'margin_short_used_trade_date_gt_signal_asof']`

## 4. Missing / PIT Audit

| feature_family | control_rows | missing_rows | missing_ratio | matched_rows |
| --- | --- | --- | --- | --- |
| institutional_flow | 326915 | 171417 | 0.52434731 | 155498 |
| margin_short | 326915 | 176221 | 0.53904226 | 150694 |

| feature_family | rows_checked | used_available_at_gt_signal_asof_rows | used_trade_date_gt_signal_asof_rows | pit_pass |
| --- | --- | --- | --- | --- |
| institutional_flow | 326915 | 0 | 0 | True |
| margin_short | 326915 | 0 | 0 | True |

## 5. 必须证明的等式

- `control_model_family == treatment_model_family`：`True`
- `control_model_params == treatment_model_params`：`True`
- `control_label == treatment_label`：`True`
- `control_split == treatment_split`：`True`
- `control_universe_policy == treatment_universe_policy`：`True`
- `control_post_score_filter == treatment_post_score_filter`：`True`
- `only_added_training_features == q1_approved_numeric_orthogonal_features_and_flags`：`True`

## 6. Feature Importance Top

| feature | importance_gain | importance_split | is_orthogonal_feature |
| --- | --- | --- | --- |
| STD30 | 519.5358071923256 | 26 | False |
| STD60 | 504.43012664606795 | 32 | False |
| STD20 | 427.0059007406235 | 30 | False |
| QTLU60 | 216.03812116384506 | 18 | False |
| CORD30 | 174.23556983470917 | 31 | False |
| QTLU5 | 169.8384189605713 | 11 | False |
| SUMD60 | 168.1920988559723 | 13 | False |
| RESI10 | 161.06431823130697 | 23 | False |
| STD5 | 139.51992720365524 | 20 | False |
| MAX5 | 138.72037835419178 | 11 | False |
| CORD5 | 138.38557934761047 | 25 | False |
| MAX30 | 124.63038758613402 | 23 | False |
| KSFT | 119.07221031188965 | 13 | False |
| STD10 | 116.67190181650221 | 18 | False |
| RSQR5 | 108.70481356978416 | 22 | False |
| margin_balance | 101.42623090744019 | 13 | True |
| VSTD10 | 97.01303297281265 | 21 | False |
| MIN30 | 96.79151546955109 | 14 | False |
| CORD10 | 95.79478430747986 | 16 | False |
| VSTD20 | 94.49333888851106 | 20 | False |

## 7. 输出 Artifact

| artifact | path |
| --- | --- |
| training_manifest | data_tw/experiments/orthogonal_fresh_qlib_controlled/phase_q2_orthogonal_fresh_qlib_training/phase_q2_training_manifest.json |
| generated_config | data_tw/experiments/orthogonal_fresh_qlib_controlled/phase_q2_orthogonal_fresh_qlib_training/phase_q2_generated_qlib_config.yaml |
| model_artifact | data_tw/experiments/orthogonal_fresh_qlib_controlled/phase_q2_orthogonal_fresh_qlib_training/phase_q2_model_artifact/phase_q2_orthogonal_fresh_qlib_model.pkl |
| raw_score_rank | data_tw/experiments/orthogonal_fresh_qlib_controlled/phase_q2_orthogonal_fresh_qlib_training/phase_q2_raw_score_rank.csv |
| post_filter_score_rank | data_tw/experiments/orthogonal_fresh_qlib_controlled/phase_q2_orthogonal_fresh_qlib_training/phase_q2_post_filter_score_rank.csv |
| feature_importance | data_tw/experiments/orthogonal_fresh_qlib_controlled/phase_q2_orthogonal_fresh_qlib_training/phase_q2_feature_importance.csv |
| resource_audit | data_tw/experiments/orthogonal_fresh_qlib_controlled/phase_q2_orthogonal_fresh_qlib_training/phase_q2_resource_audit.json |
| leakage_audit | data_tw/experiments/orthogonal_fresh_qlib_controlled/phase_q2_orthogonal_fresh_qlib_training/phase_q2_leakage_audit.json |
| forbidden_action_audit | data_tw/experiments/orthogonal_fresh_qlib_controlled/phase_q2_orthogonal_fresh_qlib_training/phase_q2_forbidden_action_audit.json |
| training_log | data_tw/experiments/orthogonal_fresh_qlib_controlled/phase_q2_orthogonal_fresh_qlib_training/phase_q2_training_log.txt |

## 8. 是否建议进入 Q3

- 建议允许进入 Q3：`是`，用于同口径 replay/evaluation。
- Q3 不得改 Q0/Q2 冻结合同，不得新增规则或切换默认策略。
