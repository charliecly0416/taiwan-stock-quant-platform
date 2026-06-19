# Phase E0 执行报告：Extended OOS 合同与可行性审计

生成时间：`2026-06-15T18:21:05+00:00`

## 1. 结论

- gate：`phase_e0_extended_oos_contract_feasible`。
- E0 只做合同与可行性审计，未训练 qlib / LTR，未调参，未回放。
- qlib train 冻结为 `2018-01-01..2022-12-31`。
- 同一个 frozen qlib 计划为 `2023-01-01..2026-05-07` 生成 OOS score。
- LTR train 冻结为 `2023-01-01..2025-12-31`；2026 为 untouched test。

## 2. 使用 Artifact

- provider：`qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin`
- S2B manifest：`data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2b_fresh_qlib_training/phase_s2b_training_manifest.json`
- S2B config：`data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2b_fresh_qlib_training/phase_s2b_generated_qlib_config.yaml`
- O2 features：`data_tw/experiments/ltr_orthogonal_features_controlled/phase_o2_pit_safe_feature_builder/normalized_feature_daily.csv`
- O4 manifest：`data_tw/experiments/ltr_orthogonal_features_controlled/phase_o4_controlled_treatment_ltr/phaseo4_training_manifest.json`
- O4 whitelist：`data_tw/experiments/ltr_orthogonal_features_controlled/phase_o4_controlled_treatment_ltr/phaseo4_training_feature_whitelist.csv`

## 3. Qlib 数据覆盖

| window | start | end | days | active min/median/max | top50 feasible |
| --- | --- | --- | ---: | --- | --- |
| qlib_train_2018_2022 | 2018-01-01 | 2022-12-31 | 1220 | 139/141.0/148 | True |
| qlib_oos_score_2023_2026 | 2023-01-01 | 2026-05-07 | 802 | 148/149.0/150 | True |
| ltr_train_2023_2025 | 2023-01-01 | 2025-12-31 | 723 | 148/149.0/150 | True |
| ltr_test_2026 | 2026-01-01 | 2026-05-07 | 79 | 150/150.0/150 | True |

## 4. Top50 / OOS Score 可行性

| window | date_count | candidate min/median/max | top50 feasible |
| --- | ---: | --- | --- |
| ltr_train_2023_2025 | 723 | 148/149.0/150 | True |
| ltr_test_2026 | 79 | 150/150.0/150 | True |

## 5. O2 正交特征 PIT Coverage

| window | family | rows | matched | missing_ratio | available_at violation | trade_date violation |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| ltr_test_2026 | institutional_flow | 11850 | 11850 | 0.0 | 0 | 0 |
| ltr_train_2023_2025 | institutional_flow | 108450 | 107815 | 0.00585523 | 0 | 0 |
| ltr_test_2026 | margin_short | 11850 | 11699 | 0.01274262 | 0 | 0 |
| ltr_train_2023_2025 | margin_short | 108450 | 104463 | 0.03676349 | 0 | 0 |

## 6. Label 可行性

| window | rows | label rows | missing rows | ratio | train allowed | audit only |
| --- | ---: | ---: | ---: | ---: | --- | --- |
| ltr_train_2023_2025 | 107552 | 107552 | 0 | 1.0 | True | False |
| ltr_test_2026 | 11850 | 11850 | 0 | 1.0 | False | True |

## 7. 参数与特征计划

- qlib model family：`qlib.contrib.model.gbdt.LGBModel`。
- qlib 参数沿用 S2B，仅允许改变日期 split。
- LTR model family / params 沿用 O4：`LightGBM.LGBMRanker / lambdarank`。
- label：`relevance_10d_top_heavy`。
- feature schema：`78` 个 O4 whitelist 特征，未新增 O2/O4 之外特征。

## 8. 禁止事项审计

- 未训练 qlib / LTR。
- 未调参，未回放。
- 未改变 provider。
- 未引入多个 qlib 模型拼接 score。
- 未使用 2026 做训练、调参或选择。
- 未触发 provider refresh / publish / accepted latest、frontend/API、monitor 或交易链路。

## 9. 输出 Artifact

- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e0_contract_and_feasibility/phasee0_contract_manifest.json`
- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e0_contract_and_feasibility/phasee0_qlib_data_coverage.csv`
- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e0_contract_and_feasibility/phasee0_oos_score_feasibility_plan.csv`
- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e0_contract_and_feasibility/phasee0_top50_candidate_feasibility.csv`
- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e0_contract_and_feasibility/phasee0_o2_orthogonal_feature_coverage.csv`
- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e0_contract_and_feasibility/phasee0_label_feasibility_audit.csv`
- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e0_contract_and_feasibility/phasee0_feature_schema_plan.csv`
- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e0_contract_and_feasibility/phasee0_forbidden_action_audit.json`

## 10. 是否建议进入 E1

- 建议：允许进入 E1，gate 为 `phase_e0_extended_oos_contract_feasible`。
