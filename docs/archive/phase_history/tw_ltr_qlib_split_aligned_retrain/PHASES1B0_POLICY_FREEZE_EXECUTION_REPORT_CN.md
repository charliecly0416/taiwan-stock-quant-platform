# Phase S1B0 Qlib Score/Rank 政策与 Universe 口径冻结执行报告

生成日期：2026-06-14

## 1. 执行范围

本轮严格执行 `docs/tw_ltr_qlib_split_aligned_retrain/PHASES1B0_QILB_SCORE_POLICY_AND_UNIVERSE_WORK_CN.md`，只冻结 qlib score/rank 生成政策、walk-forward fold/window、qlib 参数、PIT/as-of dynamic universe 可行性和 static universe 降级方案。

已执行：

- 只读解析 qlib frozen config 与 recorder artifact；
- 冻结 walk-forward qlib score/rank fold 计划；
- 只读检查 normalized price 字段是否支持 trailing liquidity Top150；
- 只读计算 dynamic PIT/as-of universe 的 split/year feasibility；
- 输出 static accepted 150 降级方案；
- 输出 gate summary。

未执行：

- 未训练 qlib；
- 未训练 LTR；
- 未实际生成 qlib score/rank；
- 未构建 S1 LTR 样本；
- 未跑组合回放；
- 未调参；
- 未改前端/API；
- 未联网；
- 未触发 provider refresh/publish；
- 未切换 accepted latest；
- 未触发 monitor、broker、orders、quick-trade 或任何交易链路。

## 2. 产物

| 产物 | 路径 |
| --- | --- |
| qlib score/rank 生成政策 | `data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b0_policy_freeze/phase_s1b0_qlib_score_generation_policy.json` |
| walk-forward fold 计划 | `data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b0_policy_freeze/phase_s1b0_walk_forward_fold_plan.csv` |
| qlib config 冻结 | `data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b0_policy_freeze/phase_s1b0_qlib_config_freeze.json` |
| dynamic universe feasibility | `data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b0_policy_freeze/phase_s1b0_dynamic_universe_feasibility.csv` |
| dynamic universe daily 明细 | `data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b0_policy_freeze/phase_s1b0_dynamic_universe_feasibility_daily.csv` |
| static universe 降级方案 | `data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b0_policy_freeze/phase_s1b0_static_universe_degrade_plan.json` |
| gate summary | `data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1b0_policy_freeze/phase_s1b0_gate_summary.json` |

## 3. Qlib 参数冻结与一致性

冻结来源：

- config：`qlib_pipeline/configs/tw_yahoo_primary_alpha158.yaml`
- recorder：`qlib_pipeline/mlruns/607910013167647574/950741cfd5f14ee5a05464fec3e12e0a`
- model：`qlib_pipeline/mlruns/607910013167647574/950741cfd5f14ee5a05464fec3e12e0a/artifacts/params.pkl`
- pred：`qlib_pipeline/mlruns/607910013167647574/950741cfd5f14ee5a05464fec3e12e0a/artifacts/pred.pkl`

冻结参数：

| 项目 | 值 |
| --- | --- |
| model | `qlib.contrib.model.gbdt.LGBModel` |
| handler | `qlib.contrib.data.handler.Alpha158` |
| dataset | `qlib.data.dataset.DatasetH` |
| loss | `mse` |
| learning_rate | `0.05` |
| colsample_bytree | `0.8879` |
| subsample | `0.8789` |
| lambda_l1 | `205.6999` |
| lambda_l2 | `580.9768` |
| max_depth | `8` |
| num_leaves | `210` |
| num_threads | `8` |

一致性审计结果：

- model class/module 一致；
- model kwargs 一致；
- dataset class/module 一致；
- handler class/module/kwargs 一致；
- train/valid/test segments 一致；
- `config_recorder_consistency_ok = true`。

本轮未改 qlib 参数，未做搜索。

## 4. Walk-Forward Score/Rank 生成计划

默认政策：`strict_walk_forward_qlib_scores_with_pit_asof_dynamic_universe`。

原则：

- 每个 score target 日期只能使用该日期之前的数据训练 qlib；
- qlib 参数沿用 frozen Option C config；
- 不使用 S1 test 结果决定 fold/window/参数；
- 生成 score/rank 只作为 LTR input feature，不解释为交易信号；
- S1B0 不执行实际训练或 score 生成。

冻结 fold 草案：

| fold | qlib train window | score window | LTR 用途 | 结论 |
| --- | --- | --- | --- | --- |
| `WF-2017` | `2015-05-04..2016-12-31` | `2017-01-01..2017-12-31` | train score | 可作为严格 WF 首个打分年 |
| `WF-2018` | `2015-05-04..2017-12-31` | `2018-01-01..2018-12-31` | train score | 可行 |
| `WF-2019` | `2015-05-04..2018-12-31` | `2019-01-01..2019-12-31` | train score | 可行 |
| `WF-2020` | `2015-05-04..2019-12-31` | `2020-01-01..2020-12-31` | train score | 可行 |
| `WF-VAL` | `2015-05-04..2020-12-31` | `2021-01-01..2022-12-31` | validation score | 设计可行 |
| `TEST` | frozen recorder | `2023-01-01..2025-06-30` | test score / baseline comparison | 已有 frozen pred 覆盖 |

## 5. 2015-2016 处理建议

严格 walk-forward 下，`2015-05-04..2016-12-31` 无法打分，因为没有足够更早的 qlib 训练窗口。

S1B0 默认建议：

```text
严格 PIT/as-of 默认政策下，将 2015-05-04..2016-12-31 从 LTR train 中排除；
S1 LTR train 使用 2017-01-01..2020-12-31 的 walk-forward scored rows。
```

这会缩短 LTR train，但保持 score/rank 的严格 PIT/as-of 语义。执行者未自动采用该方案进入训练，等待审查确认。

可讨论但未选择的降级：

- `blocked_cross_fit_within_train_only`
- `static_in_sample_frozen_train_scores`

## 6. Dynamic PIT/as-of Universe 可行性

### 6.1 字段支持

normalized price 文件包含：

- `symbol`
- `date`
- `open`
- `high`
- `low`
- `close`
- `volume`
- `vwap`
- `factor`

因此本地字段支持 as-of trailing liquidity Top150：

```text
asof active instrument range
+ same-day price
+ >=60 historical rows
+ trailing 60-day value = mean(vwap_or_close * volume)
+ Top150
```

未使用 future accepted list、future top list 或全窗口 active days 排序。

### 6.2 Feasibility 摘要

| split | year | dates | selected min | selected median | selected max | dates selected < 50 | dates selected < 150 | dynamic feasible |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| train | 2015 | 174 | 2 | 149 | 150 | 3 | 96 | false |
| train | 2016 | 263 | 0 | 150 | 150 | 19 | 92 | false |
| train | 2017 | 261 | 0 | 150 | 150 | 18 | 61 | false |
| train | 2018 | 261 | 0 | 150 | 150 | 16 | 102 | false |
| train | 2019 | 247 | 0 | 150 | 150 | 6 | 28 | false |
| train | 2020 | 245 | 150 | 150 | 150 | 0 | 0 | true |
| validation | 2021 | 244 | 0 | 150 | 150 | 1 | 116 | false |
| validation | 2022 | 246 | 148 | 150 | 150 | 0 | 50 | true |
| test | 2023 | 239 | 148 | 150 | 150 | 0 | 56 | true |
| test | 2024 | 242 | 148 | 150 | 150 | 0 | 80 | true |
| test | 2025 | 116 | 149 | 150 | 150 | 0 | 5 | true |

判断：

- dynamic universe 字段层面可计算；
- 但在早期 train 年份和 2021 年，按严格规则存在 selected count 低于 50 的日期；
- 因此 `dynamic_universe_feasible = false`，不能直接进入 S1B1。

## 7. Static Accepted 150 降级方案

已输出 `phase_s1b0_static_universe_degrade_plan.json`，但本轮未采用。

降级方案边界：

- 可能来源：当前 accepted/top150 signal universe 或 frozen option_c_150_normalized symbol list；
- 必须用户确认；
- 结论必须降级为 `static_accepted_150_research_replay`；
- 不得称为严格 PIT/as-of active universe；
- 不得用于证明全市场 PIT 公平验证。

由于 dynamic universe 严格规则下不可完全通过，若审查者认为仍要推进，下一步需要选择：

1. 接受 strict walk-forward + dynamic universe 但排除 selected count 不足日期；
2. 降级为 static accepted 150 research replay；
3. 停止 S1。

执行者本轮不做选择。

## 8. S1B0 回答工作文档问题

1. walk-forward qlib score 生成计划是否覆盖足够的 LTR train / validation / test？
   - score 计划层面：2017..2020 train、2021..2022 validation、2023..2025H1 test 可覆盖；
   - 2015..2016 无法严格 walk-forward 打分，建议排除或降级；
   - 但 dynamic universe 早期 selected count 不足，不能直接进入 S1B1。

2. 2015-2016 无法严格 walk-forward 打分时，建议如何处理？
   - 默认建议排除 `2015-05-04..2016-12-31`，从 `2017-01-01` 开始使用严格 WF scored rows；
   - 未自动执行，等待审查确认。

3. qlib 参数是否完全沿用 frozen config？是否发现 config / recorder 不一致？
   - 完全沿用 frozen config；
   - 未发现 config / recorder 不一致。

4. dynamic PIT/as-of active universe 是否可行？
   - 字段可行；
   - 严格 selected count 规则下整体不可行，因为早期 train 年份和 2021 年存在 selected count < 50 的日期。

5. 如果 dynamic universe 不可行，static accepted 150 降级方案是什么，结论如何降级？
   - 见第 7 节；
   - 需用户确认；
   - 结论降级为 `static_accepted_150_research_replay`。

6. 是否需要执行者下一轮实际训练 qlib folds / 生成 score/rank？
   - 当前不建议直接进入 S1B1，需先由审查者/用户决定 universe 降级或日期排除政策。

7. 是否存在任何 provider、accepted latest、monitor、前端/API、交易链路越权？
   - 未发现；本轮未触发这些链路。

## 9. Gate 建议

建议 gate：

```text
s1b0_dynamic_universe_infeasible_static_degrade_requires_user_confirmation
```

理由：qlib 参数和 walk-forward score 计划可冻结，但严格 PIT/as-of dynamic universe 在早期年份不可完全满足 selected count 要求；若继续，需要审查者/用户确认日期排除或 static universe 降级方案。S1B0 未训练、未生成 score、未构建样本、未回放。
