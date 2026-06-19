# Phase O3 审查结论：Row-aligned Treatment Sample

生成日期：2026-06-15

审查对象：

```text
docs/tw_ltr_orthogonal_features_controlled/PHASEO2_REVIEW_CN.md
docs/tw_ltr_orthogonal_features_controlled/PHASEO3_ROW_ALIGNED_TREATMENT_SAMPLE_EXECUTION_REPORT_CN.md
scripts/build_orthogonal_ltr_phase_o3_row_aligned_sample.py
data_tw/experiments/ltr_orthogonal_features_controlled/phase_o3_row_aligned_treatment_sample/
```

## 1. 审查结论

结论：

```text
通过
```

推荐 gate：

```text
phase_o3_treatment_sample_row_aligned_passed
```

本轮没有发现需要停下来沟通的阻塞问题。O3 只完成 row-aligned treatment candidate sample 拼接，没有训练 qlib/LTR，没有做收益率回放，没有修改 Phase1C control，也没有触发 frontend/API/provider/accepted latest/monitor/交易链路。

## 2. Row Alignment

O3 满足核心硬门槛：

| metric | value |
| --- | --- |
| control_rows | 159993 |
| treatment_rows | 159993 |
| row_identity_mismatch_count | 0 |
| row_label_mismatch_count | 0 |
| row_original_feature_mismatch_count | 0 |
| added_column_count | 62 |

Hash 对齐通过：

```text
control_label_hash == treatment_label_hash
control_original_feature_hash == treatment_original_feature_hash
control_identity_hash == treatment_identity_hash
```

这说明 O3 没有改 control 行、label、原始特征、split 或 sample_complete 身份。

## 3. PIT 审查

O3 按 `available_at <= sample_date` 做 as-of join。

PIT leakage audit：

| feature_family | available_at > sample_date | trade_date > sample_date | missing_rows | missing_ratio |
| --- | ---: | ---: | ---: | ---: |
| institutional_flow | 0 | 0 | 595 | 0.003719 |
| margin_short | 0 | 0 | 5417 | 0.033858 |

Rolling 可见性审计：

```text
rolling_window_available_at_monotonic_groups: 0
```

未发现 PIT 泄漏或 rolling window 可见性倒退。

## 4. 新增列范围

新增列共 62 个，来源为：

```text
institutional_flow 正交特征
margin_short 正交特征
PIT lineage / delay / missing / audit metadata
```

未发现月营收 YoY、其他数据源、过滤器、阈值、market gate 或 turnover rule 混入。

需要注意：

```text
phaseo3_treatment_candidate_sample.csv 中同时包含可训练数值特征和审计 metadata。
```

例如以下列只能用于审计，不能直接作为 O4 训练特征：

```text
*_trade_date
*_available_at
*_raw_snapshot_id
*_available_at_contract
*_raw_snapshot_path
*_lineage_source
*_used_available_at_gt_sample_date
*_used_trade_date_gt_sample_date
```

这些列保留在 candidate sample 中是合理的，但 O4 必须先冻结训练特征白名单。

## 5. 低覆盖/缺失风险

缺失仍集中在低覆盖融资融券股票：

```text
TW7769
TW6919
TW3131
TW6683
TW4749
TW6805
TW6446
TW6789
TW6770
```

O3 没有因缺失删行，这是正确的。O4/O5/O6 必须继续保留 missing flag，并在最终解释中区分：

```text
正交数据无增益
vs
低覆盖导致信号不足
```

## 6. 是否允许进入 O4

允许进入 O4，但必须先冻结 O4 训练合同。

O4 允许：

```text
使用 Phase1C 同模型类型；
使用 Phase1C 同超参数；
使用 Phase1C 同训练/验证/测试 split；
使用 Phase1C 同 label；
在原始特征之外只增加 O3 审查通过的正交数值特征、missing flag、delay flag/days；
输出训练日志、feature list、feature importance、模型 artifact。
```

O4 必须排除：

```text
所有 raw path / snapshot id / contract text / date string / lineage source / audit boolean metadata；
所有 O2/O3 未审查字段；
所有收益率回放逻辑。
```

O4 硬门槛：

```text
model_type unchanged
hyperparameters unchanged
label unchanged
split unchanged
control original features unchanged
training_feature_whitelist recorded
non_numeric_or_audit_metadata_excluded
no auto tuning
no replay
no frontend/API/provider/accepted latest/monitor/trading
```

## 7. 最终判断

```text
O3 执行合规；
row/hash/schema/PIT 审计通过；
允许进入 O4；
O4 前必须冻结训练特征白名单，避免把审计 metadata 喂给模型。
```
