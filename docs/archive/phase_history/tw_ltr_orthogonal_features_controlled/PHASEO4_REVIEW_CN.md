# Phase O4 审查结论：Controlled Treatment LTR Training

生成日期：2026-06-15

审查对象：

```text
docs/tw_ltr_orthogonal_features_controlled/PHASEO4_CONTROLLED_TREATMENT_LTR_TRAINING_WORK_CN.md
docs/tw_ltr_orthogonal_features_controlled/PHASEO4_CONTROLLED_TREATMENT_LTR_TRAINING_EXECUTION_REPORT_CN.md
scripts/train_orthogonal_ltr_phase_o4_controlled_treatment.py
data_tw/experiments/ltr_orthogonal_features_controlled/phase_o4_controlled_treatment_ltr/
```

## 1. 审查结论

结论：

```text
通过
```

推荐 gate：

```text
phase_o4_controlled_treatment_ltr_trained
```

O4 没有发现需要停下来沟通的阻塞问题。执行者没有重训 qlib，没有替换 Phase1C control，没有做收益率回放，没有自动调参，也没有触发 frontend/API/provider/accepted latest/monitor/交易链路。

## 2. 训练合同核对

模型配置与 Phase1C 合同一致：

```text
model_type: LightGBM.LGBMRanker
objective: lambdarank
metric: ndcg
num_leaves: 31
learning_rate: 0.03
n_estimators: 120
min_child_samples: 40
random_state: 42
label_col: relevance_10d_top_heavy
```

训练脚本复用 Phase1C 的 `relevance_10d_top_heavy` 构造方式，没有改 label 语义。

## 3. Row / Split 审查

Row split 审计：

```text
total_rows: 159993
sample_complete_rows: 152249
train_rows: 92717
validation_rows: 31296
independent_test_rows: 31350
out_of_split_or_incomplete_rows: 4630
rows_used_for_training: 90301
rows_used_for_validation: 30877
rows_scored: 152249
```

`rows_used_for_training / validation` 小于 split 总行数，是因为训练沿用 `sample_complete == True` 的 complete-row 口径；这与 Phase1C 训练口径一致，不是因正交特征缺失删行。

## 4. Feature Whitelist 审查

训练特征数量：

```text
original control features: 34
orthogonal training features: 44
total training features: 78
```

审查者说明：

```text
O4 工作文档中“新增 40 个正交训练特征”是文字笔误；
实际列举清单与文末说明均为 44 个。
```

执行者按列举白名单与 `34 + 44 = 78` 执行，没有自行增删。该处理可以接受。

## 5. Metadata 排除审查

训练白名单和 feature importance 中未发现以下禁止 metadata：

```text
raw_snapshot_id
raw_snapshot_path
available_at_contract
lineage_source
available_at
trade_date
used_available_at_gt_sample_date
used_trade_date_gt_sample_date
delay_reason
```

`phaseo4_excluded_metadata_columns.csv` 已记录禁止列，训练脚本也显式检查 forbidden columns 不得进入 feature list。

## 6. 输出产物审查

O4 输出齐全：

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

`phaseo4_treatment_row_scores.csv` 覆盖 `sample_complete` 行：

```text
rows_scored: 152249
```

这与 Phase1C frozen row-score 口径兼容。

## 7. 训练指标说明

O4 报告了 rank / NDCG 指标：

```text
validation mean_daily_spearman_rank_ic_10d: 0.062851
independent_test mean_daily_spearman_rank_ic_10d: 0.078585
```

这些指标只能说明模型训练产物已生成，并提供 ranking quality 参考。

不能据此判断策略收益优劣，也不能据此默认化。

## 8. 是否允许进入 O5

允许进入 O5。

O5 只允许做同窗口、同口径评测：

```text
Treatment orthogonal LTR vs 第一版 simple LTR / Phase1C anchor
```

O5 必须报告：

```text
same-window full universe
same-window common universe
fee/tax adjusted return
max drawdown
action_count
turnover
next-day accounting
真实 PnL contribution
分段/月度/年份表现
低覆盖股票与 missing flag 对结果的影响
feature importance 稳定性
```

O5 禁止：

```text
改训练结果
重训 qlib/LTR
改回放规则
新增 filter / threshold / market gate / turnover rule
改 Phase1C anchor
改 frontend/API/provider/accepted latest/monitor/交易链路
把训练窗口 rank 指标当作策略优劣证据
```

## 9. 最终判断

```text
O4 执行合规；
训练特征白名单合规；
metadata 未进入模型；
模型配置与 Phase1C 合同一致；
允许进入 O5 同口径评测。
```
