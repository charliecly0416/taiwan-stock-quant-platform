# Phase O4 执行报告：Controlled Treatment LTR Training

生成时间：`2026-06-15T11:35:06+00:00`

## 1. 执行结论

本轮使用 Phase1C 相同模型类型、label、split 与超参数，只增加 O3 审查通过的正交训练特征白名单，训练 controlled treatment LTR。

推荐 gate：

```text
phase_o4_controlled_treatment_ltr_trained
```

## 2. 边界

- 未重训 qlib。
- 未训练新的 control 模型替代 Phase1C anchor。
- 未做收益率回放或策略优劣判断。
- 未改 Phase1C control artifact / label / split / original features / hyperparameters。
- 未自动调参。
- 未触发 frontend/API/provider/accepted latest/monitor/交易链路。

## 3. 输入 Artifact

- `data_tw/experiments/ltr_orthogonal_features_controlled/phase_o3_row_aligned_treatment_sample/phaseo3_treatment_candidate_sample.csv`
- `data_tw/experiments/ltr_orthogonal_features_controlled/phase_o3_row_aligned_treatment_sample/phaseo3_row_alignment_audit.csv`
- `data_tw/experiments/ltr_orthogonal_features_controlled/phase_o3_row_aligned_treatment_sample/phaseo3_pit_leakage_audit.csv`
- `data_tw/experiments/ltr_orthogonal_features_controlled/phase_o0_contract_freeze/phaseo0_experiment_contract.json`

## 4. 输出 Artifact

- `data_tw/experiments/ltr_orthogonal_features_controlled/phase_o4_controlled_treatment_ltr/phaseo4_training_manifest.json`
- `data_tw/experiments/ltr_orthogonal_features_controlled/phase_o4_controlled_treatment_ltr/phaseo4_training_feature_whitelist.csv`
- `data_tw/experiments/ltr_orthogonal_features_controlled/phase_o4_controlled_treatment_ltr/phaseo4_excluded_metadata_columns.csv`
- `data_tw/experiments/ltr_orthogonal_features_controlled/phase_o4_controlled_treatment_ltr/phaseo4_row_split_audit.csv`
- `data_tw/experiments/ltr_orthogonal_features_controlled/phase_o4_controlled_treatment_ltr/phaseo4_model_config_audit.csv`
- `data_tw/experiments/ltr_orthogonal_features_controlled/phase_o4_controlled_treatment_ltr/phaseo4_training_log.json`
- `data_tw/experiments/ltr_orthogonal_features_controlled/phase_o4_controlled_treatment_ltr/phaseo4_validation_metrics.csv`
- `data_tw/experiments/ltr_orthogonal_features_controlled/phase_o4_controlled_treatment_ltr/phaseo4_feature_importance.csv`
- `data_tw/experiments/ltr_orthogonal_features_controlled/phase_o4_controlled_treatment_ltr/phaseo4_treatment_model.pkl`
- `data_tw/experiments/ltr_orthogonal_features_controlled/phase_o4_controlled_treatment_ltr/phaseo4_treatment_row_scores.csv`
- `data_tw/experiments/ltr_orthogonal_features_controlled/phase_o4_controlled_treatment_ltr/phaseo4_summary.json`

## 5. Row Count / Split Count

| metric | value |
| --- | --- |
| total_rows | 159993 |
| sample_complete_rows | 152249 |
| train_rows | 92717 |
| validation_rows | 31296 |
| independent_test_rows | 31350 |
| out_of_split_or_incomplete_rows | 4630 |
| rows_used_for_training | 90301 |
| rows_used_for_validation | 30877 |
| rows_scored | 152249 |

## 6. Feature Whitelist

- original control features：`34`。
- orthogonal training features：`44`。
- total training features：`78`。
- O4 工作文档中“新增 40 个”与实际列举/总数说明不一致；本轮按列举白名单与文末 `34 + 44` 执行，没有自行增删。

## 7. Model Config Audit

| field | expected | actual | pass |
| --- | --- | --- | --- |
| model_type | LightGBM.LGBMRanker | LightGBM.LGBMRanker | yes |
| objective | lambdarank | lambdarank | yes |
| metric | ndcg | ndcg | yes |
| boosting_type | gbdt | gbdt | yes |
| num_leaves | 31 | 31 | yes |
| learning_rate | 0.03 | 0.03 | yes |
| n_estimators | 120 | 120 | yes |
| min_child_samples | 40 | 40 | yes |
| random_state | 42 | 42 | yes |
| n_jobs | 2 | 2 | yes |
| verbose | -1 | -1 | yes |
| label_col | relevance_10d_top_heavy | relevance_10d_top_heavy | yes |
| original_feature_count | 34 | 34 | yes |
| orthogonal_feature_count | 44 | 44 | yes |
| total_feature_count | 78 | 78 | yes |

## 8. Validation / Ranking Metrics

| split | row_count | date_count | mean_daily_spearman_rank_ic_10d | ndcg_at_10 | ndcg_at_30 | ndcg_at_50 |
| --- | --- | --- | --- | --- | --- | --- |
| train | 90301 | 625 | 0.0927074749555931 | 0.7095400028636636 | 0.5613702791717691 | 0.5673623371939518 |
| validation | 30877 | 209 | 0.0628506093338241 | 0.4040311075919749 | 0.4080160133384677 | 0.45610894116862805 |
| independent_test | 31071 | 209 | 0.0785846369782293 | 0.3879020152555324 | 0.3949295162242758 | 0.44754081541217006 |

## 9. Hash Audit

- label_hash：`782bceb1f165937f7b56c8e9e2aca3f14469d26a5b9ee87d05f940318c58706e`
- original_feature_hash：`981197980fcf963a717ef9c335ac30a2a1cb304346c3e4de92e738679ac0d022`
- orthogonal_feature_hash：`5cb33d87287ae7e96c596064aa61c0a1ece268f3571f032846594fd0ca8c3b4c`

## 10. Feature Importance

| feature | family | importance_split | importance_gain |
| --- | --- | --- | --- |
| volatility20 | control_original | 295 | 10849.094673156738 |
| margin_balance | margin_short | 296 | 2231.699876189232 |
| avg_trading_value_20d | control_original | 264 | 1965.5776116847992 |
| MA60 | control_original | 209 | 1764.470131278038 |
| MACD | control_original | 187 | 1535.4373788833618 |
| volume_stability20 | control_original | 214 | 1419.1961299180984 |
| market_volatility20 | control_original | 159 | 1230.6980743408203 |
| TWII_close_vs_MA120 | control_original | 123 | 936.6078000068665 |
| MA20 | control_original | 123 | 894.8816879987717 |
| short_balance | margin_short | 147 | 885.9270193576813 |
| margin_balance_change_roll10 | margin_short | 96 | 766.3882389068604 |
| dealer_net_buy_roll10 | institutional_flow | 99 | 724.7778698205948 |
| short_balance_change_roll10 | margin_short | 90 | 695.9234585762024 |
| institutional_total_net_buy_roll10 | institutional_flow | 84 | 683.6084322929382 |
| MA5 | control_original | 78 | 630.7453122138977 |
| market_breadth20 | control_original | 83 | 590.7568879127502 |
| investment_trust_net_buy_roll10 | institutional_flow | 92 | 575.7960785627365 |
| ret20 | control_original | 87 | 563.6459307670593 |
| TWII_ret60 | control_original | 81 | 479.94011902809143 |
| market_drawdown60 | control_original | 70 | 397.25027871131897 |

## 11. 停止条件复核

- control_rows == treatment_rows：O3 已通过，O4 复用 O3 sample。
- label / split / original features / hyperparameters：未改变。
- 训练特征等于白名单：通过。
- 禁止 metadata 列进入训练：0。
- 自动调参：未执行。
- 收益率回放：未执行。
