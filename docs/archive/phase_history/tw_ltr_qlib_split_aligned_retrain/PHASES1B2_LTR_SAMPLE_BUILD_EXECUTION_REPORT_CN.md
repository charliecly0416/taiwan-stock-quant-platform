# Phase S1B2 LTR Split-Aligned 样本构建执行报告

生成日期：2026-06-14

## 1. 执行结论

本轮严格按 `docs/tw_ltr_qlib_split_aligned_retrain/PHASES1B1M_REVIEW_AND_PHASES1B2_WORK_CN.md` 执行，只完成：

```text
把 S1B1 qlib walk-forward score/rank 转成可用于后续 LTR 训练的 split-aligned 样本，并完成 feature / label / leakage 审计。
```

结论：`通过，可提交审查`。

当前 gate：

```text
s1b2_ltr_samples_pass_request_s1b3_ltr_training
```

说明：该 gate 仅表示 S1B2 样本构建与泄漏审计通过，可请求进入后续 LTR 训练阶段；本轮没有训练 LTR，也没有做任何收益或策略结论。

## 2. 范围边界

本轮执行内容：

- 使用冻结输入 `phase_s1b1_qlib_wf_scores.csv`；
- 复用本地已存在 `normalized_nonempty/*.csv` 与 `TWII.csv`；
- 复用既有 LTR input feature 白名单；
- 构建 split-aligned 样本；
- 生成 label 审计、feature coverage、forbidden feature 审计、leakage / boundary 审计。

本轮未执行：

- 未训练 LTR；
- 未做模型选择；
- 未跑组合回放；
- 未做策略比较；
- 未调 qlib/LTR 参数；
- 未新增正交数据、基本面数据、联网数据或 provider 数据；
- 未改前端/API；
- 未触发 provider refresh / publish；
- 未切换 accepted latest；
- 未触发 monitor / broker / orders / quick-trade / 交易链路；
- 未输出买卖、持有、仓位、target position、target weight、收益承诺、胜率或上涨概率语义。

## 3. 输入冻结与来源

S1B1 输入：

```text
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b1_qlib_wf_scores/phase_s1b1_qlib_wf_scores.csv
```

本地价格 / 市场数据：

```text
qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/normalized_nonempty/*.csv
qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/normalized_nonempty/TWII.csv
```

复用的 input feature 白名单：

```text
data_tw/experiments/ltr_rerank_regime_turnover/phase1_ltr_baseline/phase1_input_feature_list.json
```

说明：`WF-VAL` 的 qlib score/rank 是远端回传补齐的，因此 S1B1 gate summary 中会出现 `/lustre/...` provider 路径；本轮 S1B2 样本构建只使用当前工作区内已有的本地 score 文件和本地 normalized/TWII 文件，不涉及 provider 切换、accepted latest 切换或 refresh/publish。

## 4. 实现

新增脚本：

```text
scripts/build_tw_ltr_s1b2_samples.py
```

主要逻辑：

1. 读取 S1B1 完整 qlib walk-forward score/rank；
2. 固定 split：

```text
train_scored: 2017-01-01..2020-12-31
validation:   2021-01-01..2022-12-31
test:         2023-01-01..2025-06-30
```

3. 只在 S1B1 有 score/rank 的 `date/instrument` 上构建样本；
4. 衍生 qlib 特征：
   - `qlib_score_percentile_by_date`
   - `qlib_score_zscore_by_date`
   - `rank_change_1d/3d/5d`
   - `top10/top30/top50 flag`
   - `top30/top50 streak`
5. 从本地 OHLCV 构建技术与流动性特征；
6. 从本地 TWII 构建市场状态特征；
7. 生成 forward return / excess return / relevance label，并把这些字段标记为 `label_only`；
8. 输出 schema、feature list、label audit、feature coverage、forbidden feature audit、leakage gate。

## 5. Input Feature 冻结

本轮输入特征共 34 个，保持与既有白名单一致，并继续排除 `trend_score`：

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

`phase_s1b2_forbidden_feature_audit.csv` 显示：

```text
forbidden_feature_hits: []
label_input_overlap: []
trend_score: excluded
```

## 6. Label 口径

本轮冻结 label 体系：

- `future_return_5d`
- `future_return_10d`
- `future_return_20d`
- `future_excess_return_5d`
- `future_excess_return_10d`
- `future_excess_return_20d`
- `future_excess_return_rank_5d`
- `future_excess_return_rank_10d`
- `future_excess_return_rank_20d`
- `topk_forward_bucket`
- `ltr_relevance_label`

关键说明：

```text
primary label: ltr_relevance_label
primary horizon: 10 trading days
uses TWII excess return: true
label_only: true
```

这些 label 字段未进入 input feature。

## 7. Split 摘要

`phase_s1b2_split_summary.json`：

| split | date range | date_count | row_count | instrument_count | feature_complete | label_available_10d | sample_complete |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| train_scored | 2017-01-03..2020-12-31 | 974 | 145921 | 431 | 141087 | 145911 | 141085 |
| validation | 2021-01-04..2022-12-30 | 489 | 73078 | 379 | 69812 | 73078 | 69812 |
| test | 2023-01-03..2025-06-30 | 597 | 89386 | 411 | 87345 | 89386 | 87345 |

总体：

```text
row_count: 308385
sample_complete_row_count: 298242
duplicate_date_instrument_count: 0
qlib_score_missing_count: 0
qlib_rank_missing_count: 0
```

注意：`2015-05-04..2016-12-31` 没有纳入样本，因为 S1B1 没有该阶段 qlib walk-forward score/rank。

## 8. Label 审计摘要

`phase_s1b2_label_audit_summary.json`：

- `train_scored`：
  - `future_excess_return_10d` 非空 `145911`
  - `ltr_relevance_label` 非空 `145911`
  - 10d label 不可得尾段：`2018-04-16..2018-04-27`
- `validation`：
  - `future_excess_return_10d` 非空 `73078`
  - `ltr_relevance_label` 非空 `73078`
  - 10d label 不可得尾段：`null`
- `test`：
  - `future_excess_return_10d` 非空 `89386`
  - `ltr_relevance_label` 非空 `89386`
  - 10d label 不可得尾段：`null`

补充判断：train_scored 中少量 10d/20d label 缺失来自局部价格未来段不足，不是 test 反馈或 split 泄漏问题。

## 9. 产物清单

输出目录：

```text
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b2_ltr_samples/
```

已生成：

```text
phase_s1b2_ltr_samples.csv
phase_s1b2_sample_schema.json
phase_s1b2_feature_list.json
phase_s1b2_split_summary.json
phase_s1b2_label_audit_summary.json
phase_s1b2_feature_coverage.csv
phase_s1b2_forbidden_feature_audit.csv
phase_s1b2_leakage_boundary_audit.json
phase_s1b2_gate_summary.json
```

## 10. Leakage / Boundary 审计

`phase_s1b2_leakage_boundary_audit.json`：

```text
train_scored_start: 2017-01-01
early_train_2015_2016_scored: false
forbidden_feature_hits: []
label_input_overlap: []
s1_test_feedback_used_for_feature_label_or_filtering: false
ltr_training_performed: false
ltr_sample_build_performed: true
portfolio_replay_performed: false
strategy_comparison_performed: false
provider_refresh_publish_performed: false
accepted_latest_switching_performed: false
monitor_or_trading_chain_touched: false
```

结论：本轮只完成样本构建与审计，没有越过主线边界。

## 11. 验证命令

已执行：

```text
python -m py_compile scripts/build_tw_ltr_s1b2_samples.py
python scripts/build_tw_ltr_s1b2_samples.py
```

运行完成，无需远端迁移。

## 12. 待审查者关注点

建议审查者重点核查：

1. `phase_s1b2_ltr_samples.csv` 是否严格只包含 S1B1 score/rank 可用的 `date/instrument`；
2. `phase_s1b2_forbidden_feature_audit.csv` 是否继续排除 `trend_score` 和 forbidden features；
3. `phase_s1b2_label_audit_summary.json` 中 label-only 字段是否未误入 input feature；
4. `train_scored` 只应表述为 `2017-2020`，不能表述为完整 `2015-2020`。
