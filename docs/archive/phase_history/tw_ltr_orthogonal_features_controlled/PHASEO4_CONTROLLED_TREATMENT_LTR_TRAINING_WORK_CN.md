# Phase O4 工作文档：Controlled Treatment LTR Training

生成日期：2026-06-15

依据：

```text
docs/tw_ltr_orthogonal_features_controlled/ORTHOGONAL_LTR_CONTROLLED_MAINLINE_CN.md
docs/tw_ltr_orthogonal_features_controlled/PHASEO3_REVIEW_CN.md
data_tw/experiments/ltr_orthogonal_features_controlled/phase_o0_contract_freeze/phaseo0_experiment_contract.json
data_tw/experiments/ltr_orthogonal_features_controlled/phase_o3_row_aligned_treatment_sample/phaseo3_summary.json
```

## 1. O4 启动条件

O3 已通过：

```text
gate: phase_o3_treatment_sample_row_aligned_passed
control_rows == treatment_rows == 159993
label hash 一致
original feature hash 一致
identity hash 一致
PIT leakage rows == 0
rolling_window_available_at_monotonic_groups == 0
```

O4 允许启动。

O4 的目标 gate：

```text
phase_o4_controlled_treatment_ltr_trained
```

## 2. O4 目标

O4 只做一件事：

```text
用 Phase1C 完全相同的 LTR 训练配置，
训练“原始 simple LTR 特征 + O3 正交数值特征”的 treatment 模型。
```

O4 不做收益率回放，不做策略优劣判断，不改前端默认。

## 3. 冻结 Control 合同

Control identity 不得改变：

```text
candidate_id: head10_all_l31_alpha0.7_top50_only
model_id: head10_all_l31
score_column: score_head10_all_l31_alpha0.7_top50_only
blend_alpha: 0.7
preserve_scope: top50_only
label_col: relevance_10d_top_heavy
num_leaves: 31
learning_rate: 0.03
n_estimators: 120
random_state: 42
```

Control sample 合同：

```text
control_rows: 159993
control_complete_rows: 152249
train_rows: 92717
validation_rows: 31296
independent_test_rows: 31350
out_of_split_or_incomplete_rows: 4630
```

O4 不得改变：

```text
split
label
sample_complete / feature_complete / label_complete 口径
original features
model type
hyperparameters
random_state
```

## 4. 输入产物

只允许使用：

```text
data_tw/experiments/ltr_orthogonal_features_controlled/phase_o3_row_aligned_treatment_sample/phaseo3_treatment_candidate_sample.csv
data_tw/experiments/ltr_orthogonal_features_controlled/phase_o3_row_aligned_treatment_sample/phaseo3_row_alignment_audit.csv
data_tw/experiments/ltr_orthogonal_features_controlled/phase_o3_row_aligned_treatment_sample/phaseo3_pit_leakage_audit.csv
data_tw/experiments/ltr_orthogonal_features_controlled/phase_o0_contract_freeze/phaseo0_experiment_contract.json
```

允许读取第一版 simple LTR 训练脚本作为模板：

```text
scripts/train_tw_ltr_phase1_lambdamart.py
```

不得读取或混入 fresh qlib / fresh LTR / OOS stacking / frontend default 产物作为训练输入。

## 5. 训练样本规则

训练样本必须沿用 Phase1C / first simple LTR 的可训练行口径。

O4 必须报告：

```text
total_rows
sample_complete_rows
train_rows
validation_rows
independent_test_rows
out_of_split_or_incomplete_rows
rows_used_for_training
rows_used_for_validation
rows_scored
```

如果执行者发现必须删除任何 row，必须停止，不得继续。

缺失处理：

```text
O3 已完成 neutral fill + missing flag；
O4 不得因正交特征缺失删除样本；
O4 不得重新填充导致 O3 hash / row identity 失效。
```

## 6. 原始 Control 特征白名单

O4 必须保留以下 34 个原始特征：

```text
qlib_score_raw
qlib_rank
qlib_score_percentile_by_date
qlib_score_zscore_by_date
rank_change_1d
rank_change_3d
rank_change_5d
top10_flag
top30_flag
top50_flag
top30_streak
top50_streak
MA5
MA10
MA20
MA60
RSI14
MACD
Bollinger_position
ret20
volatility20
volume_ratio20
avg_trading_value_20d
volume_stability20
missing_rate20
suspension_proxy
slippage_proxy
TWII_ret20
TWII_ret60
TWII_close_vs_MA60
TWII_close_vs_MA120
market_volatility20
market_drawdown60
market_breadth20
```

## 7. 正交训练特征白名单

O4 只允许新增以下 40 个正交训练特征。

### 7.1 法人筹码训练特征

```text
foreign_net_buy
investment_trust_net_buy
dealer_net_buy
institutional_total_net_buy
foreign_net_buy_roll1
foreign_net_buy_roll3
foreign_net_buy_roll5
foreign_net_buy_roll10
investment_trust_net_buy_roll1
investment_trust_net_buy_roll3
investment_trust_net_buy_roll5
investment_trust_net_buy_roll10
dealer_net_buy_roll1
dealer_net_buy_roll3
dealer_net_buy_roll5
dealer_net_buy_roll10
institutional_total_net_buy_roll1
institutional_total_net_buy_roll3
institutional_total_net_buy_roll5
institutional_total_net_buy_roll10
institutional_total_net_buy_streak
institutional_missing_flag
institutional_delay_flag
institutional_flow_delay_days
institutional_flow_asof_missing_flag
```

### 7.2 融资融券训练特征

```text
margin_balance
margin_balance_change
short_balance
short_balance_change
margin_balance_change_roll1
margin_balance_change_roll3
margin_balance_change_roll5
margin_balance_change_roll10
short_balance_change_roll1
short_balance_change_roll3
short_balance_change_roll5
short_balance_change_roll10
margin_direction_proxy
short_direction_proxy
margin_short_divergence_proxy
margin_short_missing_flag
margin_short_delay_flag
margin_short_delay_days
margin_short_asof_missing_flag
```

说明：

```text
原始 control 特征 34 个 + 正交训练特征 44 个。
```

如果执行者实际统计发现数量与本文列举不一致，必须停止并提交差异，不得自行增删。

## 8. 禁止进入模型的列

以下列只能用于审计，严禁作为训练特征：

```text
control_row_id
date
instrument
year
split
regime_segment
future_return_5d
future_return_10d
future_return_20d
future_excess_return_5d
future_excess_return_10d
future_excess_return_20d
future_excess_return_rank_5d
future_excess_return_rank_10d
future_excess_return_rank_20d
topk_forward_bucket
ltr_relevance_label
label_complete_5d
label_complete_10d
label_complete_20d
feature_complete
sample_complete
```

以下 O3 metadata 严禁作为训练特征：

```text
institutional_flow_trade_date
institutional_flow_available_at
institutional_flow_raw_snapshot_id
institutional_flow_delay_reason
institutional_flow_available_at_contract
institutional_flow_raw_snapshot_path
institutional_flow_lineage_source
institutional_flow_used_available_at_gt_sample_date
institutional_flow_used_trade_date_gt_sample_date
margin_short_trade_date
margin_short_available_at
margin_short_raw_snapshot_id
margin_short_delay_reason
margin_short_available_at_contract
margin_short_raw_snapshot_path
margin_short_lineage_source
margin_short_used_available_at_gt_sample_date
margin_short_used_trade_date_gt_sample_date
```

如训练脚本检测到任一禁止列进入 model feature list，必须 fail。

## 9. 训练配置

必须沿用 Phase1C：

```text
model type: LightGBM LambdaMART / LGBMRanker
label_col: relevance_10d_top_heavy
num_leaves: 31
learning_rate: 0.03
n_estimators: 120
random_state: 42
```

禁止：

```text
自动调参
增加/减少树数
改变 num_leaves
改变 learning_rate
改变 label
改变 group/query 构造
改变 train/validation/test split
改变 sample_complete 过滤
```

## 10. 必须输出的审计

O4 报告必须包含：

```text
使用脚本
输入 artifact
输出 artifact
训练 feature whitelist
被排除 metadata 列清单
row count / split count
label hash
original feature hash
orthogonal feature hash
model config diff vs Phase1C
training log
validation ranking metrics
feature importance
missing/delay feature importance
是否触发停止条件
```

推荐输出产物：

```text
phaseo4_training_manifest.json
phaseo4_training_feature_whitelist.csv
phaseo4_excluded_metadata_columns.csv
phaseo4_row_split_audit.csv
phaseo4_model_config_audit.csv
phaseo4_training_log.json
phaseo4_validation_metrics.csv
phaseo4_feature_importance.csv
phaseo4_treatment_model.pkl
phaseo4_treatment_row_scores.csv
phaseo4_summary.json
```

## 11. O4 禁止事项

严格禁止：

```text
重训 qlib
训练新的 control 模型替代 Phase1C anchor
改 Phase1C control artifact
改 label / split / original features / hyperparameters
自动调参
收益率回放
策略默认化判断
新增过滤器、阈值、market gate、turnover rule
新增数据源
改 frontend/API/provider/accepted latest/monitor/交易链路
```

## 12. O4 停止条件

如出现以下任一情况，执行者必须停止：

```text
control_rows != treatment_rows
label hash 不一致
original feature hash 不一致
训练特征不等于白名单
禁止 metadata 列进入训练
模型配置与 Phase1C 不一致
split count 与 O0 不一致
训练需要删除样本
训练需要改 label 或 group 构造
训练脚本需要新增未审查数据源
```

## 13. O4 后续说明

O4 通过只表示 treatment LTR 按合同训练完成。

O4 不得声称策略优劣。

策略优劣只能在 O5 同窗口、同回放口径评测后判断。

## 14. 给执行者的一句话

```text
请按本 O4 工作文档训练 controlled treatment LTR：完全沿用 Phase1C 模型类型、label、split 和超参数，只在 34 个原始 control 特征之外加入本文冻结的正交训练特征白名单；严禁把 O3 lineage/audit metadata 喂给模型，严禁调参、回放、改 control、改前端或触发 provider/accepted latest/monitor/交易链路。
```
