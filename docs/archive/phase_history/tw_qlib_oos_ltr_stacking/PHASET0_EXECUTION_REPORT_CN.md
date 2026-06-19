# Phase T0 数据覆盖与时序合同冻结执行报告

生成日期：2026-06-15

## 1. 执行结论

本轮按 `docs/TW_STOCK_QLIB_OOS_LTR_STACKING_MAINLINE_CN.md` 与 `docs/tw_qlib_oos_ltr_stacking/PHASET0_REVIEW_AND_REVISION_WORKDOC_CN.md` 执行 Phase T0 修订，仅做数据覆盖审计、qlib calendar horizon guard 推导与后续 stacking 时序合同冻结。

结论：`T0 通过，可提交审查；T1 只能按本文冻结合同执行`。

核心判断：

- `2020-2021` normalized price / TWII 覆盖存在，足以支持技术、流动性、市场状态特征构建；
- `2020` 不能使用 frozen Option C 对自身训练期的 in-sample score；若纳入 LTR train，必须使用独立 walk-forward fold，例如已有 `WF-2020`；
- `2021` 可作为 frozen qlib base train 截止 `2020-12-31` 后的 OOS score 区间；
- 已有 S1B1/S1B2 产物证明 `2020`、`2021` 均可构建 qlib score/rank + LTR feature/label 样本；
- 本主线冻结使用 dynamic universe 作为主口径，同时要求 T2 做 common universe 对照；
- 本轮未训练、未调参、未回放、未改前端/API、未触发 provider/accepted latest/monitor/交易链路。

推荐 gate：

```text
phaset0_contract_frozen_request_review
```

## 2. 本轮边界

本轮执行内容：

- 读取主线文档与历史 S1B1/S1B2/S2 产物；
- 只读统计本地 normalized price、S1B1 qlib WF score、S1B2 LTR samples；
- 冻结 T1/T2 使用的时间线、OOS score 政策、split 边界、label horizon guard、universe 口径和有限窗口敏感性矩阵；
- 新增本报告。

本轮未执行：

- 未训练 qlib；
- 未训练 LTR；
- 未调参或扩展搜索；
- 未跑 backtest / replay / 组合比较；
- 未改前端/API；
- 未联网抓取数据；
- 未触发 provider refresh / publish；
- 未切换 accepted latest；
- 未触发 monitor config save / scan / alerts write；
- 未连接 broker、orders、quick-trade 或任何交易链路；
- 未输出买卖、持有、仓位、target position、target weight、收益承诺、胜率或上涨概率语义。

## 3. 证据来源

主要只读证据：

```text
qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/normalized_nonempty/*.csv
qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/normalized_nonempty/TWII.csv
qlib_pipeline/configs/tw_yahoo_primary_alpha158.yaml
qlib_pipeline/configs/tw_yahoo_primary_alpha158_s2_fresh_retrain.yaml
qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin/calendars/day.txt
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b1_qlib_wf_scores/
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b2_ltr_samples/
docs/tw_ltr_qlib_split_aligned_retrain/PHASES1B1S_LOW_THREAD_RESOURCE_EXECUTION_REPORT_CN.md
docs/tw_ltr_qlib_split_aligned_retrain/PHASES1B2_LTR_SAMPLE_BUILD_EXECUTION_REPORT_CN.md
docs/tw_qlib_oos_ltr_stacking/PHASET0_REVIEW_AND_REVISION_WORKDOC_CN.md
```

## 4. 2020-2021 normalized price 覆盖

本地目录：

```text
qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/normalized_nonempty
```

只读统计结果：

| item | value |
| --- | ---: |
| `TW*.csv` 文件数，含 `TWII` | 1987 |
| 2020-2021 有数据的股票文件数，不含 `TWII` | 1785 |
| 股票日期范围 | `2020-01-02..2021-12-30` |
| 股票总行数 | 855401 |
| close positive 行数 | 855401 |
| volume non-null 行数 | 855401 |
| 单票 2020-2021 日期数 min / median / max | `3 / 488 / 488` |
| `TWII` 日期范围 | `2020-01-02..2021-12-30` |
| `TWII` 日期数 | 489 |

判断：

- 2020-2021 的底层 normalized price 和 TWII 市场指数存在；
- 少数新上市股票只有短历史，不能直接说明不可用，后续仍按 dynamic universe 的 `>=60 history + trailing value` 规则过滤；
- 技术特征中的 MA/RSI/MACD/波动率/成交额代理与 TWII 市场状态特征具备本地构建基础。

## 5. qlib OOS score/rank 覆盖

S1B1 score/rank 文件：

```text
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b1_qlib_wf_scores/phase_s1b1_qlib_wf_scores.csv
```

coverage by split：

| split | start | end | dates | score rows | selected min / median / max | missing score/rank |
| --- | --- | --- | ---: | ---: | --- | ---: |
| train_scored_2017_2020 | 2017-01-03 | 2020-12-31 | 974 | 145921 | `147 / 150 / 150` | 0 / 0 |
| validation | 2021-01-04 | 2022-12-30 | 489 | 73078 | `148 / 150 / 150` | 0 / 0 |
| test | 2023-01-03 | 2025-06-30 | 597 | 89386 | `148 / 150 / 150` | 0 / 0 |

fold 语义：

| fold | qlib train | score window | LTR usage | OOS 判断 |
| --- | --- | --- | --- | --- |
| WF-2020 | 2015-05-04..2019-12-31 | 2020-01-01..2020-12-31 | train_score | 可作为 2020 LTR train 的 OOS score |
| WF-VAL | 2015-05-04..2020-12-31 | 2021-01-01..2022-12-31 | validation_score | 可作为 2021-2022 LTR train/validation 的 OOS score |
| TEST | frozen recorder | 2023-01-01..2025-06-30 | test_score_baseline | 对 2023+ 为 frozen qlib OOS/test score |

边界判断：

- `2020` 若使用 `WF-2020`，OOS 语义成立；若使用 frozen Option C 模型在 2020 的 score，则不成立；
- `2021` 在 qlib base train 截止 `2020-12-31` 的合同下，OOS 语义成立；
- 后续 T1 不得把 qlib 对自身训练窗口的 in-sample score 混入 LTR 主训练特征。

## 6. LTR feature/label 可构建性

S1B2 样本文件：

```text
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b2_ltr_samples/phase_s1b2_ltr_samples.csv
```

已有样本 split 摘要：

| split | date range | dates | rows | instruments | feature complete | 10d label available | sample complete |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| train_scored | 2017-01-03..2020-12-31 | 974 | 145921 | 431 | 141087 | 145911 | 141085 |
| validation | 2021-01-04..2022-12-30 | 489 | 73078 | 379 | 69812 | 73078 | 69812 |
| test | 2023-01-03..2025-06-30 | 597 | 89386 | 411 | 87345 | 89386 | 87345 |

2020 与 2021 分年检查：

| year | date range | dates | rows | instruments | split | feature complete | sample complete | 10d label complete | score/rank missing |
| --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: |
| 2020 | 2020-01-02..2020-12-31 | 245 | 36750 | 272 | train_scored | 35337 | 35337 | 36750 | 0 / 0 |
| 2021 | 2021-01-04..2021-12-30 | 243 | 36274 | 292 | validation | 33492 | 33492 | 36274 | 0 / 0 |

冻结的 input features 共 34 个，包含 qlib score/rank 派生特征、技术特征、流动性特征、TWII/市场状态特征；`trend_score` 继续排除。label-only 字段未进入 input features。

主 label：

```text
primary label: ltr_relevance_label
primary horizon: 10 trading days
uses TWII excess return: true
label bucket policy: fixed percentile thresholds [0.2, 0.4, 0.6, 0.8]
label_bucket_fit_on_validation_or_test: false
```

判断：

- 2020-2021 可构建 LTR feature/label；
- 少量 feature incomplete 行应在训练样本构建时按 `sample_complete` 过滤；
- 10d label 在 2020 和 2021 分年检查中均完整；历史 S1B2 全 split 中少量 2018 label 缺失来自局部未来价格段不足，不影响 2020-2021 合同冻结。

## 7. Label horizon 与 split 边界

冻结 label horizon：

```text
primary horizon: 10 trading days
secondary audit horizons: 5 / 20 trading days
```

T1/T2 边界规则：

- LTR train 样本必须保证 primary 10d label 完整；
- 5d / 10d label 可用于训练或模型选择时，必须按各自 horizon guard 截断 split 末端；
- 20d 只允许作为事后稳定性审计指标，不得参与模型选择、窗口选择或默认结论；若后续希望让 20d 参与选择，必须重新冻结 20 trading days guard；
- validation 不得用 final test 的 label、收益或回放表现拟合阈值；
- final test 不得参与 feature scaling、label bucket fitting、模型选择或窗口选择；
- `label_only_columns` 不得进入 input feature。

qlib calendar 推导采用：

```text
qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin/calendars/day.txt
label_end = sample_date 在 qlib day calendar 中向后第 N 个可交易日
```

关键日历行号：

| date | day.txt line |
| --- | ---: |
| 2024-06-14 | 2299 |
| 2024-06-28 | 2309 |
| 2024-07-01 | 2310 |
| 2025-06-02 | 2530 |
| 2025-06-16 | 2540 |
| 2025-06-30 | 2550 |
| 2025-07-01 | 2551 |
| 2025-07-14 | 2560 |

split guard 审计表：

| boundary | sample end | horizon | label end | next split start | pass |
| --- | --- | ---: | --- | --- | --- |
| train -> validation | 2024-06-14 | 10d | 2024-06-28 | 2024-07-01 | yes |
| validation -> final test | 2025-06-16 | 10d | 2025-06-30 | 2025-07-01 | yes |
| validation -> final test audit | 2025-06-16 | 20d | 2025-07-14 | 2025-07-01 | not used for selection |

补充约束：

- 若 20d audit 被要求参与模型/窗口选择，则 validation sample end 必须改为 `2025-06-02`，其 20d label end 为 `2025-06-30`；
- 本 T0 合同不允许 20d audit 参与模型/窗口选择，因此主 validation sample end 保持 `2025-06-16`。

冻结的主 split：

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

说明：

- 主 split 明确把 final test 放到 `2025-07-01..2026-05-07`，与 S2F 同窗口复核保持一致；
- LTR train 允许包含 2020，但只允许使用 `WF-2020` 这类 OOS qlib score；
- `2024-06-17..2024-06-28` 是 train 与 validation 之间的 10d label guard，不进入训练、validation、模型选择或窗口选择；
- `2025-06-17..2025-06-30` 是 validation 与 final test 之间的 10d label guard，不进入训练、validation、模型选择或窗口选择；
- 被 guard 截掉的末端样本可只作为覆盖诊断或事后数据完整性统计，不得进入任何训练、模型选择或窗口选择；
- 若 T1 无法为 `2024-07-01..2025-06-16` 完整生成 OOS score/rank 和 label，则必须降级为 `LTR validation: 2023-01-03..2025-06-16` 的既有 frozen qlib OOS/test-score 口径，并在 T1 报告中标明降级语义，不得静默替换。

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

使用条件：

- 若审查者认为 2020 的额外 WF fold 与 frozen Option C 主合同混用风险过高，则采用备选保守 split；
- 采用备选 split 时，2020 只作为 qlib 训练/覆盖审计资料，不进入 LTR 主训练样本。

## 8. Universe 口径冻结

主口径：

```text
dynamic universe
calendar: qlib day.txt ∩ TWII normalized price calendar
universe policy: asof active instrument range + same-day price + >=60 history + trailing 60-day value top up to 150
selected_count >= 145
```

原因：

- S1B1/S1B2 已按该口径生成覆盖和泄漏审计；
- dynamic universe 更贴近历史可交易可观测集合，避免静态 accepted 150 把后验可得股票池带入早期样本；
- T2 必须同时输出 common universe 对照，隔离 universe 差异带来的收益放大。

T0 不冻结 static accepted 150 为主训练口径。static accepted 150 只能作为产品对齐或 common universe 对照，不得替代主 OOS stacking 研究口径。

## 9. qlib OOS score 生成政策冻结

T1 允许的 score 政策：

1. `frozen Option C / expanding WF`：
   - 2020 使用 `WF-2020: train 2015-05-04..2019-12-31 -> score 2020`；
   - 2021-2025 使用 qlib train 截止早于 score window 的 frozen / walk-forward score；
   - 不允许 score date 落在同一模型训练窗口内。

2. `recent 5y qlib`：
   - 每个 score window 的 qlib train end 必须早于 score start；
   - 示例：`train 2017-01-10..2022-12-31 -> score 2023-2025`；
   - 若用于 LTR train 2021-2022，则必须额外生成对应早截止 fold，不得借用 2022 后训练过的模型。

3. `longer / expanding qlib`：
   - 扩张窗口只允许向过去扩张；
   - 对每个 score window 仍必须满足 `qlib train end < score start`。

禁止：

- 禁止用 `2015-05-04..2020-12-31` 训练出的 qlib score 直接给 2020 LTR train；
- 禁止用 `2017-01-10..2024-12-31` fresh qlib score 训练 2021-2024 LTR；
- 禁止把 final test 表现用于决定 score 生成窗口。

## 10. 有限窗口敏感性矩阵冻结

T2 只能在以下有限矩阵内做窗口敏感性验证，不得扩展为无边界搜索。

qlib train window candidates：

| id | train window | score policy | 覆盖意图 |
| --- | --- | --- | --- |
| Q0 | expanding frozen/WF: 2015-05-04 起，score window 前一年底截止 | walk-forward OOS | 长历史基线，复核旧 qlib + LTR 的 OOS 语义 |
| Q1 | recent 5y rolling，例如 2017-01-10..2022-12-31 -> 2023 score | rolling OOS | 较近期窗口，检验 fresh qlib 是否更适配新市场 |
| Q2 | recent 7-8y / expanding long，例如 2015-05-04..2022-12-31 -> 2023 score | rolling OOS | 较长窗口对照，检验样本更多是否更稳 |

LTR train window candidates：

| id | train sample length | end policy | 覆盖意图 |
| --- | --- | --- | --- |
| L1 | 1y OOS score sample | validation 前滚动截断 | 太短纠错窗口 |
| L2 | 2y OOS score sample | validation 前滚动截断 | 推荐最小稳健候选 |
| L3 | 3y OOS score sample | validation 前滚动截断 | 与旧 Phase1C 经验接近 |
| L4 | 4y OOS score sample | validation 前滚动截断 | 较长 LTR 样本候选 |

算力或数据不足时的优先保留矩阵：

```text
qlib: Q0 vs Q1
LTR:  L2 vs L3
```

选择原则：

- 不能只选 final test 收益最高的窗口；
- 必须同时看 train / validation / final test；
- 若 train 明显优于 validation/final test，标记过拟合风险；
- 若 common universe 下优势小于 2-3 个百分点，不建议切默认。

## 11. 后续 T1 输入合同

T1 只能执行：

- 按本文冻结的 qlib OOS score/rank 政策生成或复用 score；
- 按本文冻结的 feature/label 口径构建 LTR 样本；
- 做 feature leakage / label horizon / score OOS 审计；
- 报告覆盖不足或降级语义。

T1 不得执行：

- LTR 训练；
- 策略回放；
- 组合比较；
- 默认策略结论；
- 调参或窗口搜索；
- 前端/API 改动；
- provider refresh / publish；
- accepted latest switching；
- monitor / broker / orders / quick-trade。

## 12. 审查者重点

请审查：

1. 是否接受主 split 纳入 2020，但强制使用 `WF-2020` OOS score；
2. 是否改用备选保守 split，从 2021 开始训练 LTR；
3. `2024-06-17..2024-06-28` 与 `2025-06-17..2025-06-30` guard 是否足够满足 10d primary label 和回放边界；
4. dynamic universe 主口径 + common universe 对照是否符合本主线目标；
5. Q0/Q1/Q2 与 L1/L2/L3/L4 是否足够覆盖“太短/适中/太长”，且没有形成无边界调参；
6. T1 是否必须先补齐 `2024-07-01..2025-06-16` 的 OOS score/rank，若补不齐是否接受降级 validation 口径。

