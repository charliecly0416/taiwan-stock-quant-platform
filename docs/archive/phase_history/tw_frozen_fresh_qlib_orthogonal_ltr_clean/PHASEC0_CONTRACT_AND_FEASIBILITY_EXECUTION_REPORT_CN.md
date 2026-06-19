# Phase C0 执行报告：Frozen Fresh Qlib + Orthogonal LTR Clean Stacking 合同冻结与可行性审计

生成时间：`2026-06-15T17:31:21+00:00`

## 1. 结论

- gate：`phase_c0_clean_stacking_contract_feasible`。
- C0 只冻结并审计合同，未训练 qlib / LTR，未回放，未调参。
- LTR train 冻结为 `2025-01-01..2025-12-31`；LTR untouched test 冻结为 `2026-01-01..2026-05-07`。
- frozen fresh qlib train 截止 `2024-12-31`，2025/2026 score 均在 qlib 训练期之外。
- 不使用 qlib 2017..2024 in-sample score，不引入 walk-forward OOS 或多模型 score。

## 2. Frozen Artifact

- fresh qlib score：`data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2b_fresh_qlib_training/phase_s2b_post_filter_score_rank.csv`
- fresh qlib manifest：`data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2b_fresh_qlib_training/phase_s2b_training_manifest.json`
- O2 PIT-safe features：`data_tw/experiments/ltr_orthogonal_features_controlled/phase_o2_pit_safe_feature_builder/normalized_feature_daily.csv`
- O4 LTR manifest：`data_tw/experiments/ltr_orthogonal_features_controlled/phase_o4_controlled_treatment_ltr/phaseo4_training_manifest.json`
- O4 feature whitelist：`data_tw/experiments/ltr_orthogonal_features_controlled/phase_o4_controlled_treatment_ltr/phaseo4_training_feature_whitelist.csv`

## 3. Score / Top50 Coverage

| split | start | end | date_count | rows | daily rows min/median/max | daily top50 min/median/max | after qlib train end |
| --- | --- | --- | ---: | ---: | --- | --- | --- |
| ltr_test_2026 | 2026-01-02 | 2026-05-07 | 79 | 9792 | 115/122.0/150 | 50/50.0/50 | True |
| ltr_train_2025 | 2025-01-02 | 2025-12-31 | 242 | 22889 | 84/89.0/110 | 50/50.0/50 | True |

## 4. O2 正交特征 PIT Coverage

| split | family | rows | matched | missing_ratio | available_at violation | trade_date violation |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| ltr_test_2026 | institutional_flow | 9792 | 9792 | 0.0 | 0 | 0 |
| ltr_train_2025 | institutional_flow | 22889 | 22889 | 0.0 | 0 | 0 |
| ltr_test_2026 | margin_short | 9792 | 9686 | 0.01082516 | 0 | 0 |
| ltr_train_2025 | margin_short | 22889 | 22348 | 0.02363581 | 0 | 0 |

## 5. 10d Label 可行性

| split | rows | label rows | missing rows | available ratio | use policy |
| --- | ---: | ---: | ---: | ---: | --- |
| ltr_test_2026 | 9792 | 9792 | 0 | 1.0 | test label audit only; not used for training |
| ltr_train_2025 | 22889 | 22889 | 0 | 1.0 | train label allowed |

## 6. 冻结合同

- LTR model family / hyperparameters 沿用 O4：`LightGBM.LGBMRanker` / `lambdarank`，不调参。
- label 沿用 O4 / Phase1C：`relevance_10d_top_heavy`。
- preserve scope：`top50_only`。
- replay 合同为后续 C3 冻结：next-day execution, `fee_rate=0.001425`, `tax_rate=0.003`, `target_position_count=10`, `candidate_k=50`。
- 2026 只作为 untouched test，不用于训练、调参或选择。

## 7. 禁止事项审计

- 未训练 qlib。
- 未训练 LTR。
- 未调参。
- 未改 split / label / model。
- 未使用 qlib 训练期 in-sample score。
- 未引入 walk-forward OOS、多模型 score。
- 未改前端/API/provider/accepted latest/monitor，未触发交易链路。

## 8. 输出 Artifact

- `data_tw/experiments/frozen_fresh_qlib_orthogonal_ltr_clean/phase_c0_contract_and_feasibility/phasec0_contract_manifest.json`
- `data_tw/experiments/frozen_fresh_qlib_orthogonal_ltr_clean/phase_c0_contract_and_feasibility/phasec0_frozen_fresh_qlib_score_coverage.csv`
- `data_tw/experiments/frozen_fresh_qlib_orthogonal_ltr_clean/phase_c0_contract_and_feasibility/phasec0_top50_candidate_coverage.csv`
- `data_tw/experiments/frozen_fresh_qlib_orthogonal_ltr_clean/phase_c0_contract_and_feasibility/phasec0_o2_orthogonal_feature_coverage.csv`
- `data_tw/experiments/frozen_fresh_qlib_orthogonal_ltr_clean/phase_c0_contract_and_feasibility/phasec0_10d_label_feasibility_audit.csv`
- `data_tw/experiments/frozen_fresh_qlib_orthogonal_ltr_clean/phase_c0_contract_and_feasibility/phasec0_feature_schema_plan.csv`
- `data_tw/experiments/frozen_fresh_qlib_orthogonal_ltr_clean/phase_c0_contract_and_feasibility/phasec0_forbidden_action_audit.json`

## 9. 是否允许进入 C1

- 建议：允许进入 C1，gate 为 `phase_c0_clean_stacking_contract_feasible`。
