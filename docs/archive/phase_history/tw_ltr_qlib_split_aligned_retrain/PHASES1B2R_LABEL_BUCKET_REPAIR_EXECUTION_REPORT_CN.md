# Phase S1B2R Label Bucket Split-Purity 修复执行报告

生成日期：2026-06-14

## 1. 执行结论

本轮严格按 `docs/tw_ltr_qlib_split_aligned_retrain/PHASES1B2_REVIEW_AND_PHASES1B2R_LABEL_REPAIR_WORK_CN.md` 执行，只修复 S1B2 的 label bucket split-purity 问题。

结论：`通过，可请求进入 Phase S1B3 training policy freeze`。

当前 gate：

```text
s1b2r_label_bucket_repair_pass_request_s1b3_training_policy_freeze
```

本轮没有训练 LTR，没有回放，没有策略比较，没有新增数据源，没有改 feature 白名单，没有触发 provider/accepted latest/monitor/交易链路。

## 2. 修复目标

审查指出上一轮 S1B2 使用了全样本 `pd.qcut` 生成：

```text
topk_forward_bucket
ltr_relevance_label
```

这会让 validation/test 的未来标签分布参与 label bucket 边界确定，违反 split purity。

本轮已修复为：

```text
fixed_percentile_thresholds = [0.20, 0.40, 0.60, 0.80]
```

也就是说，bucket 仅由同日横截面 percentile rank 的固定阈值映射得到，不再使用全样本、validation 或 test 去拟合 bucket 边界。

## 3. 范围边界

本轮执行内容：

- 复用 S1B1 完整 qlib score/rank；
- 复用本地 normalized/TWII 数据；
- 保持 S1B2 input features 不变；
- 保持 split contract 不变；
- 把 `topk_forward_bucket` / `ltr_relevance_label` 改为固定阈值规则；
- 修正 label 审计中的不可得范围表述与缺失计数；
- 更新 label audit、leakage audit、gate summary 与执行报告。

本轮未执行：

- 未训练 LTR；
- 未跑组合回放；
- 未做策略比较；
- 未调参；
- 未新增 feature；
- 未新增数据源；
- 未联网；
- 未改前端/API；
- 未触发 provider refresh / publish；
- 未切换 accepted latest；
- 未触发 monitor config save / scan / alerts write；
- 未接 broker、orders、quick-trade；
- 未输出买卖、持有、仓位、target position、target weight、收益承诺、胜率或上涨概率语义。

## 4. 实现

修改脚本：

```text
scripts/build_tw_ltr_s1b2_samples.py
```

主要变更：

1. 新增固定 bucket 规则：

```text
rank_pct <= 0.20 -> 0
0.20 < rank_pct <= 0.40 -> 1
0.40 < rank_pct <= 0.60 -> 2
0.60 < rank_pct <= 0.80 -> 3
rank_pct > 0.80 -> 4
NaN -> NaN
```

2. 在审计中明确：

```text
label_bucket_policy = fixed_percentile_thresholds
label_bucket_thresholds = [0.20, 0.40, 0.60, 0.80]
label_bucket_fit_on_all_splits = false
label_bucket_fit_on_validation_or_test = false
s1_test_feedback_used_for_label_bucket = false
```

3. 把原先“不准确的尾段缺失”改为更准确的缺失范围与缺失原因判断：

- 不再把中间缺失日期称为尾段；
- 输出每个 split / horizon 的缺失行数；
- 给出简短原因判断，例如 `feature_history_or_price_gap`、`future_price_segment_unavailable_for_some_rows`。

## 5. 执行结果

执行命令：

```text
python scripts/build_tw_ltr_s1b2_samples.py
```

结果：成功。

关键结果：

```text
row_count: 308385
sample_complete_row_count: 298242
duplicate_date_instrument_count: 0
qlib_score_missing_count: 0
qlib_rank_missing_count: 0
forbidden_feature_hits: []
label_input_overlap: []
```

`topk_forward_bucket` 值域为：

```text
[0, 1, 2, 3, 4]
```

`topk_forward_bucket` 不再依赖全样本 `qcut`。

## 6. Split / Label 摘要

### 6.1 Split 摘要

| split | date range | rows | sample complete |
| --- | --- | ---: | ---: |
| train_scored | `2017-01-03..2020-12-31` | 145921 | 141085 |
| validation | `2021-01-04..2022-12-30` | 73078 | 69812 |
| test | `2023-01-03..2025-06-30` | 89386 | 87345 |

### 6.2 Label 审计摘要

- `label_horizon = 10 trading days primary relevance label`
- `uses_twii_excess_return = true`
- `primary_label = ltr_relevance_label`
- `label_only_columns` 保持不变
- `label_bucket_policy = fixed_percentile_thresholds`

修复后，validation/test 不再参与 bucket 边界拟合。

## 7. 产物清单

更新 / 生成：

```text
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b2_ltr_samples/phase_s1b2_ltr_samples.csv
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b2_ltr_samples/phase_s1b2_sample_schema.json
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b2_ltr_samples/phase_s1b2_feature_list.json
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b2_ltr_samples/phase_s1b2_split_summary.json
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b2_ltr_samples/phase_s1b2_label_audit_summary.json
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b2_ltr_samples/phase_s1b2_feature_coverage.csv
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b2_ltr_samples/phase_s1b2_forbidden_feature_audit.csv
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b2_ltr_samples/phase_s1b2_leakage_boundary_audit.json
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b2_ltr_samples/phase_s1b2_gate_summary.json
```

## 8. Leakage / Boundary 审计

更新后审计记录：

```text
label_bucket_policy: fixed_percentile_thresholds
label_bucket_thresholds: [0.2, 0.4, 0.6, 0.8]
label_bucket_fit_on_all_splits: false
label_bucket_fit_on_validation_or_test: false
s1_test_feedback_used_for_label_bucket: false
ltr_training_performed: false
ltr_sample_build_performed: true
portfolio_replay_performed: false
strategy_comparison_performed: false
provider_refresh_publish_performed: false
accepted_latest_switching_performed: false
monitor_or_trading_chain_touched: false
```

结论：S1B2R 只修复 label bucket purity，不扩主线。

## 9. 验证命令

已执行：

```text
python -m py_compile scripts/build_tw_ltr_s1b2_samples.py
python scripts/build_tw_ltr_s1b2_samples.py
```

结果：语法检查通过，脚本成功重建样本与审计。

## 10. 给审查者的下一步

当前产物现在满足：

- sample key 与 S1B1 score/rank 一致；
- forbidden feature hits 为空；
- label/input 无重叠；
- label bucket 不再依赖 validation/test 分布。

可按审查文档进入下一步 `S1B3 training policy freeze`。
