# Phase T1 qlib OOS Score 与 LTR 样本构建审计执行报告

生成日期：2026-06-15

## 1. 执行结论

本轮按 `docs/tw_qlib_oos_ltr_stacking/PHASET1_WORKDOC_CN.md` 执行 Phase T1，只生成或复用 qlib OOS score/rank、构建 LTR feature/label 样本，并完成 OOS、coverage、leakage 与 horizon guard 审计。

结论：`T1 通过，可提交审查；不得直接进入 T2，需等待审查通过`。

推荐 gate：

```text
phase_t1_oos_sample_audit_ready_for_review
```

核心结果：

- 采用 T0 主 split，未降级到备选保守 split；
- `2020` 使用 `WF-2020` OOS score，qlib train end 为 `2019-12-31`，OOS 通过；
- `2021-2022` 使用 `WF-VAL` OOS score，qlib train end 为 `2020-12-31`，OOS 通过；
- `2023-2025-06-16` 使用 S1B1 TEST frozen Option C pred，qlib train end 为 `2020-12-31`，OOS 通过；
- train / validation 的 primary 10d label 不跨 split；
- guard 区间未进入 `phase_t1_ltr_samples.csv`；
- input features 仍为 T0 冻结的 34 个，未包含 label-only、future、target 或 `trend_score`；
- 本轮未训练 LTR、未回放、未做策略比较、未触发 provider/accepted latest/monitor/交易链路。

## 2. 范围边界

本轮执行内容：

- 复用既有 S1B1 qlib WF score/rank；
- 复用既有 S1B2 LTR feature/label 样本；
- 按 T0 主 split 裁剪 train / validation 样本；
- 输出 T1 自己的 provenance、coverage、horizon guard、universe coverage 与 leakage audit；
- 写入本执行报告。

本轮未执行：

- 未训练 qlib；
- 未训练 LTR；
- 未跑 backtest / replay；
- 未做策略比较；
- 未做默认策略结论；
- 未调参或窗口搜索；
- 未改前端/API；
- 未触发 provider refresh / publish；
- 未切换 accepted latest；
- 未触发 monitor config save / scan / alerts write；
- 未连接 broker、orders、quick-trade 或任何交易链路；
- 未输出买卖、持有、仓位、target position、target weight、收益承诺、胜率或上涨概率语义。

## 3. 交付产物

输出目录：

```text
data_tw/experiments/tw_qlib_oos_ltr_stacking/phase_t1
```

产物：

```text
phase_t1_qlib_oos_scores.csv
phase_t1_ltr_samples.csv
phase_t1_score_provenance.csv
phase_t1_coverage_by_split.csv
phase_t1_leakage_audit.json
phase_t1_horizon_guard_audit.csv
phase_t1_universe_coverage.csv
phase_t1_summary.json
```

行数摘要：

```text
phase_t1_qlib_oos_scores.csv: 199214
phase_t1_ltr_samples.csv: 189522
```

说明：`phase_t1_ltr_samples.csv` 只包含 `t1_split in [train, validation]` 且 `sample_complete = true` 的样本；guard 区间样本只保留在 score/coverage 诊断中，不进入 LTR 样本。

## 4. 冻结 split 执行结果

采用主 split：

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

未采用备选保守 split，原因是 `WF-2020` 可与主合同可靠拼接，且 score provenance 全部通过 OOS 审计。

## 5. Score Provenance / OOS 审计

| score_window | date_range | qlib_train_start | qlib_train_end | score_source | fold_id | LTR_usage | rows | dates | OOS_pass |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2020 | 2020-01-02..2020-12-31 | 2015-05-04 | 2019-12-31 | S1B1 WF-2020 fold | WF-2020 | train | 36750 | 245 | True |
| 2021-2022 | 2021-01-04..2022-12-30 | 2015-05-04 | 2020-12-31 | S1B1 WF-VAL fold | WF-VAL | train | 73078 | 489 | True |
| 2023-2024-06-14 | 2023-01-03..2024-06-14 | 2015-05-04 | 2020-12-31 | S1B1 TEST frozen Option C pred recorder 950741cfd5f14ee5a05464fec3e12e0a | TEST | train | 51806 | 346 | True |
| 2024-07-01..2025-06-16 | 2024-07-01..2025-06-16 | 2015-05-04 | 2020-12-31 | S1B1 TEST frozen Option C pred recorder 950741cfd5f14ee5a05464fec3e12e0a | TEST | validation | 34580 | 231 | True |

判断：所有进入 LTR train / validation 的 qlib score，其 score date 均晚于对应 qlib train end，`OOS_pass=True`。

## 6. Coverage by Split

| split | date_range | dates | rows | instruments | feature_complete | label_complete | sample_complete | missing_score | missing_rank |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| train | 2020-01-02..2024-06-14 | 1080 | 161634 | 537 | 155432 | 161634 | 155432 | 0 | 0 |
| validation | 2024-07-01..2025-06-16 | 231 | 34580 | 278 | 34090 | 34580 | 34090 | 0 | 0 |

判断：

- train / validation 均无 qlib score 或 rank 缺失；
- `sample_complete` 行数为后续 LTR 可用样本数；
- feature incomplete 行没有进入 `phase_t1_ltr_samples.csv`。

## 7. Horizon Guard 审计

| boundary | sample_end | horizon | label_end | next_split_start | pass |
| --- | --- | --- | --- | --- | --- |
| train -> validation | 2024-06-14 | 10 | 2024-06-28 | 2024-07-01 | True |
| validation -> final test | 2025-06-16 | 10 | 2025-06-30 | 2025-07-01 | True |
| validation -> final test audit | 2025-06-16 | 20 | 2025-07-14 | 2025-07-01 | not_used_for_selection |

判断：

- train 最后样本日 `2024-06-14` 的 10d label end 为 `2024-06-28`，早于 validation start `2024-07-01`；
- validation 最后样本日 `2025-06-16` 的 10d label end 为 `2025-06-30`，早于 final test start `2025-07-01`；
- 20d 只作为事后审计，不参与模型选择、窗口选择或默认结论。

## 8. Universe Coverage

| role | date_range | dates | selected_count_min | selected_count_median | selected_count_max | below_145_dates |
| --- | --- | --- | --- | --- | --- | --- |
| train | 2020-01-02..2024-06-14 | 1080 | 148 | 150.0 | 150 | 0 |
| train_validation_guard | 2024-06-17..2024-06-28 | 10 | 150 | 150.0 | 150 | 0 |
| validation | 2024-07-01..2025-06-16 | 231 | 149 | 150.0 | 150 | 0 |
| validation_final_guard | 2025-06-17..2025-06-30 | 10 | 150 | 150.0 | 150 | 0 |

判断：主口径 dynamic universe 的 selected_count 在 train、validation 及 guard 区间均不低于 145，没有静默过滤低覆盖日期。

## 9. Leakage Audit

关键检查结果：

| item | result |
| --- | --- |
| input feature count | 34 |
| label input overlap | [] |
| future / target like input features | [] |
| forbidden feature hits | [] |
| trend_score in input features | False |
| feature scaling fit on validation/final test | False |
| label bucket fit on validation/test | False |
| guard rows excluded from LTR samples | 3000 |

同日横截面 rank / percentile 审计：

```json
{
  "train": {
    "checked": true,
    "rank_min_is_1": true,
    "rank_max_equals_rows": true,
    "percentile_min_ge_0": true,
    "percentile_max_le_1": true
  },
  "validation": {
    "checked": true,
    "rank_min_is_1": true,
    "rank_max_equals_rows": true,
    "percentile_min_ge_0": true,
    "percentile_max_le_1": true
  }
}
```

判断：

- input features 中没有 future return、future label、后验 bucket 或 target return；
- `qlib_rank`、percentile、zscore 保持同日横截面语义；
- rolling 技术特征与 TWII/market 特征沿用 S1B2 规则，只使用 sample date 当日及过去数据；
- label bucket 使用固定分位阈值 `[0.2, 0.4, 0.6, 0.8]`，不在 validation 或 final test 上拟合。

## 10. Final Test 推理期说明

T2 final test 固定为：

```text
2025-07-01..2026-05-07
```

T1 不训练 LTR，也不做 final test 回放。T2 推理期规则冻结如下：

- final test 期间的 qlib score 只能用于 T2 推理和回放；
- final test label、收益、回放表现不得参与 T1 样本构建、模型选择或窗口选择；
- 若 final test score 需要额外生成，必须满足 `qlib train end < score start`；
- 生成 final test score 不得触发 provider refresh / publish / accepted latest switching；
- 若 T2 需要 `2025-07-01..2026-05-07` 的特征或 score，必须在 T2 工作文档中单独冻结生成合同与 readonly 边界。

## 11. 待审查点

请审查：

1. `WF-2020`、`WF-VAL`、`TEST frozen Option C pred` 拼接后的 OOS 语义是否满足 T0/T1 合同；
2. train / validation coverage 是否足以进入 T2 训练前准备；
3. 10d horizon guard 是否确实阻断 split 边界污染；
4. 20d 只作事后审计、不参与选择的限制是否清楚；
5. final test 推理期是否应在 T2 单独补 score/feature 生成合同。

