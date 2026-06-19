# Phase S1B4 执行报告：Split-Aligned LTR Training

生成日期：2026-06-14T17:24:39+00:00

## 1. 本轮目标

按 `PHASES1B3_REVIEW_AND_PHASES1B4_TRAINING_WORK_CN.md` 要求，严格复用 S1B3 冻结政策训练一个 common split-aligned LTR model，并输出一次性 score/rank 与训练诊断。

## 2. 执行范围

- 使用唯一 S1B2R 样本、schema、feature list 和 S1B3 policy。
- 训练前过滤 `sample_complete == true`。
- 只训练一个 common `LightGBM.LGBMRanker objective=lambdarank` 模型。
- 输出 train_scored / validation / test 的一次性 LTR score/rank、metric、feature importance、边界审计。

## 3. 固定输入与参数

- sample: `data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b2_ltr_samples/phase_s1b2_ltr_samples.csv`
- schema: `data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b2_ltr_samples/phase_s1b2_sample_schema.json`
- feature list: `data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b2_ltr_samples/phase_s1b2_feature_list.json`
- policy: `data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b3_training_policy/phase_s1b3_training_policy.json`
- 过滤：`sample_complete == true`
- 参数：`n_estimators=120, learning_rate=0.05, num_leaves=31, min_child_samples=20, random_state=42, n_jobs=2`
- `early_stopping_enabled = false`
- `parameter_search = false`

## 4. Split 训练边界

- `train_scored`：拟合。
- `validation`：固定训练诊断。
- `test`：一次性 holdout score/evaluation only，不回馈训练。
- `split_aligned_ltr_simple` 与 `split_aligned_ltr_turnover_controlled` 共用同一训练分数；本轮未实现 turnover-control 使用层规则。

## 5. Metric By Split

| split | row_count | date_count | ndcg@10 | ndcg@30 | ndcg@50 | rank_ic_audit | top10_label_mean | top30_label_mean | top50_label_mean |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| train_scored | 141085 | 969 | 0.818906 | 0.667408 | 0.653471 | 0.107457 | 3.086791 | 2.377881 | 2.153849 |
| validation | 69812 | 489 | 0.508662 | 0.511378 | 0.550673 | -0.015908 | 2.003681 | 1.988753 | 1.984123 |
| test | 87345 | 597 | 0.511329 | 0.519084 | 0.558275 | 0.034576 | 2.038358 | 2.070743 | 2.062915 |

## 6. Top Feature Importance

| feature | importance_gain | importance_split |
| --- | ---: | ---: |
| volatility20 | 2500.878821 | 385 |
| avg_trading_value_20d | 2191.700347 | 323 |
| volume_stability20 | 2049.247739 | 390 |
| MA5 | 1515.163520 | 172 |
| MA60 | 1457.160036 | 255 |
| market_volatility20 | 1252.120328 | 261 |
| ret20 | 1239.862118 | 161 |
| MACD | 1185.095849 | 249 |
| TWII_close_vs_MA120 | 923.568358 | 179 |
| RSI14 | 762.765552 | 128 |

## 7. 产物

- `data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b4_ltr_training/phase_s1b4_ltr_model.pkl`
- `data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b4_ltr_training/phase_s1b4_ltr_scores.csv`
- `data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b4_ltr_training/phase_s1b4_ltr_score_schema.json`
- `data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b4_ltr_training/phase_s1b4_training_diagnostics.json`
- `data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b4_ltr_training/phase_s1b4_metric_by_split.csv`
- `data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b4_ltr_training/phase_s1b4_feature_importance.csv`
- `data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b4_ltr_training/phase_s1b4_leakage_boundary_audit.json`
- `data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b4_ltr_training/phase_s1b4_gate_summary.json`

## 8. 只读边界与禁止事项

- 未训练 qlib。
- 未跑组合回放。
- 未比较策略收益、回撤、换手、动作次数。
- 未调参，未改 feature / label / split / universe。
- 未实现 turnover-controlled 使用层约束。
- 未联网，未新增数据源。
- 未改前端/API。
- 未触发 provider refresh / publish、accepted latest switching、monitor 或交易链路。
- 未输出买卖、持有、仓位、target position、target weight、收益承诺、胜率或上涨概率语义。

## 9. 结论

本轮完成 S1B4 授权范围内的一次性 LTR 训练与分 split score/rank 物化。

推荐 gate：

```text
s1b4_ltr_training_pass_request_s1b5_score_diagnostics_and_replay_policy
```
