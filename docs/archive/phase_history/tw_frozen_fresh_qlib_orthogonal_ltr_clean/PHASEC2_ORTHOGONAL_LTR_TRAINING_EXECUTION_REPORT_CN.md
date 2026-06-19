# Phase C2 执行报告：Orthogonal LTR Training

生成时间：`2026-06-15T17:48:19+00:00`

## 1. 结论

- gate：`phase_c2_clean_stacking_ltr_trained`。
- 仅使用 C1 通过审计的 2025 top50 row-aligned 样本训练一个 frozen fresh qlib + orthogonal LTR treatment。
- 2026 样本只用于 score / rank metric audit，不用于训练、调参、early stopping、模型选择或阈值选择。
- 未训练 qlib，未调参，未训练多个版本，未回放。

## 2. 使用 Artifact

- C1 manifest：`data_tw/experiments/frozen_fresh_qlib_orthogonal_ltr_clean/phase_c1_row_aligned_sample/phasec1_sample_manifest.json`
- train sample：`data_tw/experiments/frozen_fresh_qlib_orthogonal_ltr_clean/phase_c1_row_aligned_sample/phasec1_ltr_train_sample_2025.csv`
- test score sample：`data_tw/experiments/frozen_fresh_qlib_orthogonal_ltr_clean/phase_c1_row_aligned_sample/phasec1_ltr_test_sample_2026.csv`
- feature schema：`data_tw/experiments/frozen_fresh_qlib_orthogonal_ltr_clean/phase_c1_row_aligned_sample/phasec1_feature_schema.csv`
- O4 model config：`data_tw/experiments/ltr_orthogonal_features_controlled/phase_o4_controlled_treatment_ltr/phaseo4_training_manifest.json`

## 3. Train / Test

- train period：`2025-01-01..2025-12-31`，rows：`12100`。
- test period：`2026-01-01..2026-05-07`，rows：`3950`。
- preserve_scope：`top50_only`。

## 4. Model Config Audit

| field | value |
| --- | --- |
| model_type | LightGBM.LGBMRanker |
| objective | lambdarank |
| metric | ndcg |
| boosting_type | gbdt |
| num_leaves | 31 |
| learning_rate | 0.03 |
| n_estimators | 120 |
| min_child_samples | 40 |
| random_state | 42 |
| n_jobs | 2 |
| verbose | -1 |

## 5. Feature / Label

- label：`relevance_10d_top_heavy`，沿用 O4 / Phase1C。
- feature count：`78`。
- feature hash：`ab0c0faf2e26bca0cf4edce1f48b57dc8dd6c2b25831719dc6f9b4d497d463bf`。
- feature whitelist 来自 C1 / O4，未新增特征族。

## 6. Group Audit

| split | rows | dates | group min/median/max | empty group | non top50 rows |
| --- | ---: | ---: | --- | ---: | ---: |
| train_2025 | 12100 | 242 | 50/50.0/50 | 0 | 0 |
| test_2026 | 3950 | 79 | 50/50.0/50 | 0 | 0 |

## 7. Rank Metrics

| split | rows | dates | spearman_ic_10d | ndcg@10 | ndcg@30 | ndcg@50 | audit_only |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| train_2025 | 12100 | 242 | 0.4679584476263814 | 0.8609432216717514 | 0.8461794765910859 | 0.9319337139434651 | False |
| test_2026 | 3950 | 79 | 0.05358339472626231 | 0.3350657352922095 | 0.5105342110381005 | 0.686091755484401 | True |

## 8. Feature Importance Top20

| feature | family | importance_split | importance_gain |
| --- | --- | ---: | ---: |
| short_balance | margin_short | 196 | 1977.0869454741478 |
| top50_streak | control_original | 290 | 1563.804326891899 |
| avg_trading_value_20d | control_original | 243 | 1223.1477929353714 |
| MA60 | control_original | 167 | 1017.6955018043518 |
| dealer_net_buy_roll10 | institutional_flow | 113 | 948.743784070015 |
| volatility20 | control_original | 147 | 911.1420737504959 |
| volume_stability20 | control_original | 189 | 741.2984843254089 |
| margin_balance | margin_short | 140 | 649.0330404043198 |
| MACD | control_original | 136 | 592.4008095264435 |
| TWII_close_vs_MA60 | control_original | 69 | 589.1563677787781 |
| ret20 | control_original | 101 | 567.0375719070435 |
| investment_trust_net_buy_roll10 | institutional_flow | 109 | 541.632289648056 |
| TWII_ret20 | control_original | 81 | 432.7651387453079 |
| MA5 | control_original | 85 | 391.5419070124626 |
| MA20 | control_original | 100 | 387.2480503320694 |
| foreign_net_buy_roll10 | institutional_flow | 83 | 367.31884956359863 |
| RSI14 | control_original | 68 | 345.5029385089874 |
| MA10 | control_original | 83 | 324.3524217605591 |
| margin_balance_change_roll10 | margin_short | 81 | 316.6827253103256 |
| short_balance_change_roll10 | margin_short | 72 | 316.41673469543457 |

## 9. 边界审计

- 只训练了一个 treatment。
- 模型家族和参数完全沿用 O4。
- train 只来自 2025。
- 2026 未用于训练、调参或选择。
- 未使用 qlib 2017..2024 in-sample score。
- 未引入 walk-forward 或多模型 score。
- 未回放。
- 未触发 frontend/API/provider/accepted latest/monitor/交易链路。

## 10. 输出 Artifact

- `data_tw/experiments/frozen_fresh_qlib_orthogonal_ltr_clean/phase_c2_orthogonal_ltr_training/phasec2_training_manifest.json`
- `data_tw/experiments/frozen_fresh_qlib_orthogonal_ltr_clean/phase_c2_orthogonal_ltr_training/phasec2_ltr_model.pkl`
- `data_tw/experiments/frozen_fresh_qlib_orthogonal_ltr_clean/phase_c2_orthogonal_ltr_training/phasec2_train_row_scores.csv`
- `data_tw/experiments/frozen_fresh_qlib_orthogonal_ltr_clean/phase_c2_orthogonal_ltr_training/phasec2_test_row_scores_2026.csv`
- `data_tw/experiments/frozen_fresh_qlib_orthogonal_ltr_clean/phase_c2_orthogonal_ltr_training/phasec2_feature_importance.csv`
- `data_tw/experiments/frozen_fresh_qlib_orthogonal_ltr_clean/phase_c2_orthogonal_ltr_training/phasec2_rank_metrics.csv`
- `data_tw/experiments/frozen_fresh_qlib_orthogonal_ltr_clean/phase_c2_orthogonal_ltr_training/phasec2_group_audit.csv`
- `data_tw/experiments/frozen_fresh_qlib_orthogonal_ltr_clean/phase_c2_orthogonal_ltr_training/phasec2_training_log.txt`
- `data_tw/experiments/frozen_fresh_qlib_orthogonal_ltr_clean/phase_c2_orthogonal_ltr_training/phasec2_forbidden_action_audit.json`

## 11. 是否建议进入 C3

- 建议：允许进入 C3，gate 为 `phase_c2_clean_stacking_ltr_trained`。
