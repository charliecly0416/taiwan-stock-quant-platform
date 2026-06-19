# Phase S1B1 Qlib Walk-Forward Score/Rank 生成执行报告

生成日期：2026-06-14

## 1. 执行结论

本轮严格按 `docs/tw_ltr_qlib_split_aligned_retrain/PHASES1B0R_REVIEW_AND_PHASES1B1_WORK_CN.md` 执行 S1B1，只生成 qlib walk-forward score/rank 产物与 coverage / leakage / boundary 审计。

结论：`未通过，数据产物不足`。

推荐 gate：

```text
s1b1_qlib_wf_scores_data_insufficient
```

原因：full provider 口径下，`WF-2017`、`WF-2018`、`WF-2019`、`WF-2020` 与 `TEST` 已生成 score/rank；但 `WF-VAL` 在 `2021-01-01..2022-12-31` validation score 生成阶段两次被系统以 exit code 137 杀掉，未形成 validation fold 产物。本轮未缩短窗口、未改 provider、未改参数、未做降级替代。

## 2. 范围边界

本轮执行内容：

- 复用 S1B0R 冻结的 calendar / universe 口径；
- 按冻结 fold 生成 qlib walk-forward score/rank；
- 逐 fold 落盘，支持中断后续跑；
- 生成已完成 fold 的 coverage、leakage、boundary 与 gate 证据。

本轮未执行：

- 未训练 LTR；
- 未构建 LTR 样本；
- 未跑回放 / backtest / 组合策略比较；
- 未调 qlib 或 LTR 参数；
- 未改前端/API；
- 未联网；
- 未触发 provider refresh / publish；
- 未切换 accepted latest；
- 未触发 monitor config save / scan / alerts write；
- 未连接 broker、orders、quick-trade 或任何交易链路；
- 未输出买卖、持有、仓位、target position、target weight、收益承诺、胜率或上涨概率语义。

## 3. 实现变更

新增脚本：

```text
scripts/generate_tw_ltr_s1b1_qlib_wf_scores.py
```

关键实现点：

1. 使用 full provider：

```text
/home/chuliyang/qlib/data_tw/experiments/yahoo_adjusted_primary/qlib_bin
```

2. 使用冻结配置：

```text
qlib_pipeline/configs/tw_yahoo_primary_alpha158.yaml
```

3. 使用 S1B0R 冻结 dynamic universe：

```text
qlib day.txt ∩ TWII normalized price calendar
asof active instrument range + same-day price + >=60 history + trailing 60-day value top up to 150
selected_count >= 145
```

4. 修正 fold train window 与阶段文档一致：

| fold | qlib train window | score window | 状态 |
| --- | --- | --- | --- |
| WF-2017 | 2015-05-04..2016-12-31 | 2017-01-01..2017-12-31 | 已完成 |
| WF-2018 | 2015-05-04..2017-12-31 | 2018-01-01..2018-12-31 | 已完成 |
| WF-2019 | 2015-05-04..2018-12-31 | 2019-01-01..2019-12-31 | 已完成 |
| WF-2020 | 2015-05-04..2019-12-31 | 2020-01-01..2020-12-31 | 已完成 |
| WF-VAL | 2015-05-04..2020-12-31 | 2021-01-01..2022-12-31 | 未完成，exit code 137 |
| TEST | frozen recorder 950741cfd5f14ee5a05464fec3e12e0a | 2023-01-01..2025-06-30 | 已完成 |

5. 将输出改为逐 fold 落盘：

```text
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b1_qlib_wf_scores/folds/
```

这样已完成 fold 不会因后续 OOM 丢失，重跑时可跳过已完成 fold。

## 4. 产物清单

主要输出目录：

```text
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b1_qlib_wf_scores/
```

已生成产物：

```text
folds/WF-2017.csv
folds/WF-2017.manifest.json
folds/WF-2018.csv
folds/WF-2018.manifest.json
folds/WF-2019.csv
folds/WF-2019.manifest.json
folds/WF-2020.csv
folds/WF-2020.manifest.json
folds/TEST.csv
folds/TEST.manifest.json
phase_s1b1_fold_training_manifest.csv
phase_s1b1_qlib_wf_scores.csv
phase_s1b1_qlib_wf_scores_partial.csv
phase_s1b1_score_rank_coverage_by_split.csv
phase_s1b1_score_rank_coverage_by_fold.csv
phase_s1b1_score_rank_coverage_by_date.csv
phase_s1b1_universe_selected_count_audit.csv
phase_s1b1_leakage_boundary_audit.json
phase_s1b1_gate_summary.json
```

注意：`phase_s1b1_qlib_wf_scores.csv` 与 `phase_s1b1_qlib_wf_scores_partial.csv` 当前均只包含已完成 folds 的部分产物，不得作为完整 S1B1 通过产物使用；缺少 `WF-VAL` validation score/rank。

## 5. Coverage 摘要

`phase_s1b1_score_rank_coverage_by_fold.csv`：

| fold | start_date | end_date | date_count | score_rows | selected_count_min | selected_count_median | selected_count_max | frozen pred |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| WF-2017 | 2017-01-03 | 2017-12-29 | 243 | 36379 | 147 | 150.0 | 150 | False |
| WF-2018 | 2018-01-02 | 2018-12-28 | 245 | 36664 | 149 | 150.0 | 150 | False |
| WF-2019 | 2019-01-02 | 2019-12-31 | 241 | 36128 | 149 | 150.0 | 150 | False |
| WF-2020 | 2020-01-02 | 2020-12-31 | 245 | 36750 | 150 | 150.0 | 150 | False |
| TEST | 2023-01-03 | 2025-06-30 | 597 | 89386 | 148 | 150.0 | 150 | True |

`phase_s1b1_score_rank_coverage_by_split.csv`：

| split | start_date | end_date | date_count | score_rows | selected_count_min | selected_count_median | selected_count_max | score_missing | rank_missing |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| train_scored_2017_2020 | 2017-01-03 | 2020-12-31 | 974 | 145921 | 147 | 150.0 | 150 | 0 | 0 |
| test | 2023-01-03 | 2025-06-30 | 597 | 89386 | 148 | 150.0 | 150 | 0 | 0 |

缺失 coverage：

```text
validation: 2021-01-01..2022-12-31
missing fold: WF-VAL
```

完整 universe audit：

```text
selected_count_min: 145
selected_count_median: 150.0
selected_count_max: 150
```

已完成 folds 的质量检查：

```text
score_missing_count_on_completed_folds: 0
rank_missing_count_on_completed_folds: 0
duplicate_date_instrument_count_on_completed_folds: 0
```

## 6. 阻断说明

执行命令：

```text
python scripts/generate_tw_ltr_s1b1_qlib_wf_scores.py
```

第一次完整运行：

- `WF-2017`、`WF-2018`、`WF-2019` 完成；
- 在 `WF-2020` 训练阶段被系统 `Killed`，exit code 137。

第二次续跑：

- 成功复用 `WF-2017`、`WF-2018`、`WF-2019`；
- 成功完成 `WF-2020`；
- 进入 `WF-VAL` 后在数据构造 / 训练前段被系统 `Killed`，exit code 137。

随后单独生成 `TEST` frozen-pred fold，成功完成。

判断：阻断点是 full provider 下 `WF-VAL` fold 的本地资源压力，不是 selected universe 不可行。执行者未改 fold/window/parameter/provider 来规避失败。

## 7. Leakage / Boundary 审计

`phase_s1b1_leakage_boundary_audit.json` 记录：

```text
s1_test_feedback_used_for_train_or_fold_design: false
parameter_search_performed: false
ltr_training_performed: false
ltr_sample_build_performed: false
portfolio_replay_performed: false
provider_refresh_publish_performed: false
accepted_latest_switching_performed: false
monitor_or_trading_chain_touched: false
early_train_2015_2016_scored: false
```

`2015-05-04..2016-12-31` 未生成 LTR qlib score/rank；已完成 train scored rows 从 2017 年交易日开始。

## 8. 验证命令

已执行：

```text
python -m py_compile scripts/generate_tw_ltr_s1b1_qlib_wf_scores.py
python scripts/generate_tw_ltr_s1b1_qlib_wf_scores.py
```

补充执行：

```text
# 仅生成 TEST frozen-pred fold
# 仅汇总已完成 folds 并写 data_insufficient gate
```

## 9. 待审查者决策事项

当前执行者建议审查者不要通过 S1B1，因为 validation score/rank 缺失。

可供审查者后续决策的方向包括：

1. 是否允许对 `WF-VAL` 做技术性内存修复，例如训练一次后按 score 年度或更小 score segment 分块预测，但保持训练窗口、参数、provider 不变；
2. 是否由用户在更大内存环境手动运行同一脚本续跑 `WF-VAL`；
3. 是否接受其他审查者指定的只读资源控制方案。

执行者本轮未自行采用上述方案，等待审查意见。
