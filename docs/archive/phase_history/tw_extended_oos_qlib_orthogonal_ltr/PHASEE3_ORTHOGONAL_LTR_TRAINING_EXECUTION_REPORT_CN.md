# Phase E3 执行报告：Orthogonal LTR Training

生成时间：`2026-06-15T19:03:32+00:00`

## 1. 结论

- gate：`phase_e3_extended_oos_ltr_trained`。
- 仅使用 E2 通过审计的 2023-2025 宽候选 row-aligned 样本训练一个 extended OOS qlib + orthogonal LTR treatment。
- 2026 样本只用于 score / rank metric audit，不用于训练、调参、early stopping、模型选择或阈值选择。
- 未训练 qlib，未调参，未训练多个版本，未回放。

## 2. 使用 Artifact

- E2 manifest：`data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e2_row_aligned_sample/phasee2_sample_manifest.json`
- train sample：`data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e2_row_aligned_sample/phasee2_ltr_train_sample_2023_2025.csv`
- test score sample：`data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e2_row_aligned_sample/phasee2_ltr_test_sample_2026.csv`
- feature schema：`data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e2_row_aligned_sample/phasee2_feature_schema.csv`
- O4 model config：`data_tw/experiments/ltr_orthogonal_features_controlled/phase_o4_controlled_treatment_ltr/phaseo4_training_manifest.json`

## 3. Train / Test

- train period：`2023-01-01..2025-12-31`，rows：`107408`。
- test period：`2026-01-01..2026-05-07`，rows：`11822`。
- candidate scope：`E1R broad candidate rows`。
- future replay boundary：`qlib top50 rerank only`。

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
- feature whitelist 来自 E2 / O4，未新增特征族。

## 6. Group Audit

| split | rows | dates | group min/median/max | median max rank | top50-only | non top50 rows |
| --- | ---: | ---: | --- | ---: | --- | ---: |
| train_2023_2025 | 107408 | 723 | 147/149.0/149 | 149.0 | False | 71258 |
| test_2026 | 11822 | 79 | 149/150.0/150 | 150.0 | False | 7872 |

## 7. Rank Metrics

| split | rows | dates | spearman_ic_10d | ndcg@10 | ndcg@30 | ndcg@50 | audit_only |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| train_2023_2025 | 107408 | 723 | 0.127789499801899 | 0.6926812195038778 | 0.5649080548428773 | 0.575499040515629 | False |
| test_2026 | 11822 | 79 | 0.09194015404607192 | 0.4052261228437372 | 0.41859645146304075 | 0.46153056322175834 | True |

## 8. Feature Importance Top20

| feature | family | importance_split | importance_gain |
| --- | --- | ---: | ---: |
| volatility20 | control_original | 300 | 12300.604747056961 |
| avg_trading_value_20d | control_original | 332 | 3719.322298526764 |
| MACD | control_original | 154 | 2514.3464579582214 |
| margin_balance | margin_short | 257 | 2507.591241121292 |
| ret20 | control_original | 135 | 2036.5914046764374 |
| short_balance | margin_short | 168 | 1787.9663126468658 |
| MA60 | control_original | 193 | 1293.6267404556274 |
| volume_stability20 | control_original | 186 | 1220.7343487739563 |
| dealer_net_buy_roll10 | institutional_flow | 108 | 1157.3899161815643 |
| market_volatility20 | control_original | 141 | 954.4572584629059 |
| MA5 | control_original | 112 | 857.5069425106049 |
| investment_trust_net_buy_roll10 | institutional_flow | 120 | 838.63711810112 |
| margin_balance_change_roll10 | margin_short | 93 | 725.4370310306549 |
| MA20 | control_original | 94 | 629.2573189735413 |
| TWII_close_vs_MA120 | control_original | 88 | 614.9707589149475 |
| MA10 | control_original | 76 | 614.1671953201294 |
| TWII_ret60 | control_original | 85 | 570.9953618049622 |
| RSI14 | control_original | 52 | 540.8829190731049 |
| short_balance_change_roll10 | margin_short | 54 | 510.0123870372772 |
| TWII_close_vs_MA60 | control_original | 70 | 492.9074516296387 |

## 9. 边界审计

- 只训练了一个 treatment。
- 模型家族和参数完全沿用 O4。
- train 只来自 2023-2025。
- 训练 group 是宽候选集合，不是 top50-only。
- 2026 未用于训练、调参或选择。
- 未使用 qlib 2018..2022 in-sample score。
- 未引入 walk-forward 或多模型 score。
- 未回放。
- 未触发 frontend/API/provider/accepted latest/monitor/交易链路。

## 10. 输出 Artifact

- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e3_orthogonal_ltr_training/phasee3_training_manifest.json`
- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e3_orthogonal_ltr_training/phasee3_ltr_model.pkl`
- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e3_orthogonal_ltr_training/phasee3_train_row_scores.csv`
- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e3_orthogonal_ltr_training/phasee3_test_row_scores_2026.csv`
- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e3_orthogonal_ltr_training/phasee3_feature_importance.csv`
- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e3_orthogonal_ltr_training/phasee3_rank_metrics.csv`
- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e3_orthogonal_ltr_training/phasee3_group_audit.csv`
- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e3_orthogonal_ltr_training/phasee3_training_log.txt`
- `data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e3_orthogonal_ltr_training/phasee3_forbidden_action_audit.json`

## 11. 是否建议进入 E4

- 建议：允许进入 E4，gate 为 `phase_e3_extended_oos_ltr_trained`。
