# Phase T1 工作文档：qlib OOS Score 与 LTR 样本构建审计

生成日期：2026-06-15

前置 gate：

```text
phaset0_contract_review_passed_proceed_to_t1
```

依据文档：

```text
docs/TW_STOCK_QLIB_OOS_LTR_STACKING_MAINLINE_CN.md
docs/tw_qlib_oos_ltr_stacking/PHASET0_EXECUTION_REPORT_CN.md
```

## 1. T1 目标

Phase T1 只做三件事：

1. 按 T0 冻结合同生成或复用 qlib OOS score/rank；
2. 按 T0 冻结合同构建 LTR feature/label 样本；
3. 做 score OOS、feature leakage、label horizon、coverage 与降级语义审计。

T1 不训练 LTR，不跑回放，不做策略比较，不给默认策略结论。

## 2. 冻结 split

主 split：

```text
qlib base train:              2015-05-04..2020-12-31
qlib OOS score for LTR:       2020-01-01..2025-06-30
LTR train:                    2020-01-02..2024-06-14
train/validation guard:       2024-06-17..2024-06-28
LTR validation:               2024-07-01..2025-06-16
validation/final guard:       2025-06-17..2025-06-30
final test:                   2025-07-01..2026-05-07
primary label horizon guard:  10 trading days
```

备选保守 split：

```text
qlib base train:              2015-05-04..2020-12-31
qlib OOS score for LTR:       2021-01-01..2025-06-30
LTR train:                    2021-01-04..2024-06-14
train/validation guard:       2024-06-17..2024-06-28
LTR validation:               2024-07-01..2025-06-16
validation/final guard:       2025-06-17..2025-06-30
final test:                   2025-07-01..2026-05-07
```

默认执行主 split。只有当执行者发现 `2020` 的 `WF-2020` OOS score 与主合同无法可靠拼接时，才允许降级到备选保守 split，并必须在 T1 报告中显式说明。

## 3. qlib OOS Score 政策

T1 必须保证：

- 任何进入 LTR train / validation 的 qlib score，其 score date 不得落在对应 qlib 模型训练窗口内；
- `2020` 若进入 LTR train，只能使用 `WF-2020: train 2015-05-04..2019-12-31 -> score 2020` 或等价 OOS fold；
- `2021-2022` 可使用 qlib train 截止 `2020-12-31` 后的 OOS / WF score；
- `2023-2025-06-30` 可使用 frozen / test-score 口径，但必须写明 recorder、训练截止日与 score window；
- 禁止用 `2017-01-10..2024-12-31` fresh qlib score 训练 `2021-2024` LTR。

T1 报告必须输出 score provenance 表：

| score window | qlib train start | qlib train end | score source | LTR usage | OOS pass |
| --- | --- | --- | --- | --- | --- |
| 2020 | 待填 | 待填 | 待填 | train | yes/no |
| 2021-2022 | 待填 | 待填 | 待填 | train | yes/no |
| 2023-2024-06-14 | 待填 | 待填 | 待填 | train | yes/no |
| 2024-07-01..2025-06-16 | 待填 | 待填 | 待填 | validation | yes/no |

## 4. LTR 样本构建要求

输入特征：

- 使用 T0 冻结的 34 个 input features；
- 包含 qlib score/rank 派生特征、技术特征、流动性特征、TWII/市场状态特征；
- `trend_score` 继续排除；
- label-only 字段不得进入 input features。

label：

```text
primary label: ltr_relevance_label
primary horizon: 10 trading days
uses TWII excess return: true
label bucket policy: fixed percentile thresholds [0.2, 0.4, 0.6, 0.8]
label_bucket_fit_on_validation_or_test: false
```

过滤：

- 训练/验证样本必须满足 `sample_complete`；
- guard 区间样本不得进入训练、validation、模型选择或窗口选择；
- guard 区间最多只能作为覆盖诊断或事后数据完整性统计。

## 5. Universe 口径

主口径：

```text
dynamic universe
calendar: qlib day.txt ∩ TWII normalized price calendar
universe policy: asof active instrument range + same-day price + >=60 history + trailing 60-day value top up to 150
selected_count >= 145
```

T1 只需要构建主口径样本并记录 coverage。T2 才必须输出 common universe 对照。

若 T1 发现某日 `selected_count < 145`，必须列出日期、原因和影响范围，不得静默过滤。

## 6. 必做审计

T1 报告必须包含以下审计表。

### 6.1 Coverage by split

| split | date range | dates | rows | instruments | feature complete | label complete | sample complete | missing score/rank |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| train | 待填 | 待填 | 待填 | 待填 | 待填 | 待填 | 待填 | 待填 |
| validation | 待填 | 待填 | 待填 | 待填 | 待填 | 待填 | 待填 | 待填 |

### 6.2 Horizon guard

| boundary | sample end | horizon | label end | next split start | pass |
| --- | --- | ---: | --- | --- | --- |
| train -> validation | 2024-06-14 | 10d | 2024-06-28 | 2024-07-01 | yes/no |
| validation -> final test | 2025-06-16 | 10d | 2025-06-30 | 2025-07-01 | yes/no |

### 6.3 Leakage audit

必须检查并报告：

- input features 中没有未来 return、future label、后验 bucket、target return；
- qlib rank / percentile / zscore 仅按同日横截面计算；
- rolling 技术特征只使用 sample date 当日及过去数据；
- TWII / market regime 特征只使用 sample date 当日及过去数据；
- feature scaling 不使用 validation 或 final test 拟合参数；
- label bucket 不在 validation 或 final test 上拟合。

### 6.4 Final test 推理期说明

T1 必须补充说明：

```text
T2 final test = 2025-07-01..2026-05-07
```

T1 不需要训练 LTR 或回放，但必须说明 T2 推理期所需 qlib score / feature 的生成计划：

- final test 期间的 qlib score 只能用于 T2 推理和回放；
- final test label、收益、回放表现不得参与 T1 样本构建、模型选择或窗口选择；
- 若 final test score 需要额外生成，必须满足 qlib train end < score start，且不能触发 provider refresh / publish / accepted latest switching。

## 7. 禁止事项

T1 禁止：

- 训练 LTR；
- 策略回放；
- 组合比较；
- 默认策略结论；
- 调参或窗口搜索；
- 前端/API 改动；
- provider refresh / publish；
- accepted latest switching；
- monitor config save / scan / alerts write；
- broker / orders / quick-trade；
- 输出买卖、持有、仓位、target position、target weight、收益承诺、胜率或上涨概率语义。

## 8. T1 交付物

执行者应提交：

```text
docs/tw_qlib_oos_ltr_stacking/PHASET1_EXECUTION_REPORT_CN.md
```

建议数据产物目录：

```text
data_tw/experiments/tw_qlib_oos_ltr_stacking/phase_t1/
```

建议产物：

```text
phase_t1_qlib_oos_scores.csv
phase_t1_ltr_samples.csv
phase_t1_score_provenance.csv
phase_t1_coverage_by_split.csv
phase_t1_leakage_audit.json
phase_t1_horizon_guard_audit.csv
```

若复用既有 S1B1/S1B2 产物，也必须输出 T1 自己的 provenance / coverage / guard / leakage 审计文件，不得只引用旧报告。

## 9. T1 通过标准

T1 可提交审查的最低标准：

- train / validation 的 qlib score 全部通过 OOS 语义；
- 10d primary label 不跨 split；
- guard 区间未进入训练、validation、模型选择或窗口选择；
- input features 无 label-only 或未来信息；
- dynamic universe coverage 可解释；
- final test 推理期生成计划清楚；
- 没有执行任何 T1 禁止事项。

若任一项不满足，T1 不得进入 T2。

## 10. 给执行者的一句话

请按本工作文档执行 Phase T1：只生成或复用 qlib OOS score/rank、构建 LTR feature/label 样本，并完成 OOS、coverage、leakage 与 horizon guard 审计；不得训练 LTR、不得回放、不得做策略比较或默认结论，完成后提交 `PHASET1_EXECUTION_REPORT_CN.md` 等待审查。
