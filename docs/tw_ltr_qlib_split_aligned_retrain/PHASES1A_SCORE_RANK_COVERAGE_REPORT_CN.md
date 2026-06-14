# Phase S1A qlib Score/Rank 覆盖与生成口径诊断报告

生成日期：2026-06-14

## 1. 执行范围

本轮严格执行 `docs/tw_ltr_qlib_split_aligned_retrain/PHASES0_REVIEW_AND_PHASES1_WORK_CN.md` 中的 S1A，只做旧窗口 `2015-05-04..2025-06-30` qlib score/rank 覆盖与生成口径诊断。

已执行：

- 只读检查 frozen qlib `pred.pkl` 覆盖；
- 只读检查本地 normalized price 覆盖；
- 只读检查现有 LTR 样本中的 qlib score/rank、label、feature 覆盖；
- 输出 split 级和 date 级 coverage 表；
- 输出 qlib score/rank 生成口径选项。

未执行：

- 未训练 qlib；
- 未训练 LTR；
- 未调参；
- 未构建 S1 训练样本；
- 未跑新回放；
- 未改前端/API；
- 未联网；
- 未触发 provider refresh/publish；
- 未切换 accepted latest；
- 未触发 monitor、broker、orders、quick-trade 或任何交易链路。

## 2. 输入证据

| 证据 | 路径 |
| --- | --- |
| qlib frozen pred | `qlib_pipeline/mlruns/607910013167647574/950741cfd5f14ee5a05464fec3e12e0a/artifacts/pred.pkl` |
| qlib universe | `qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/universe/tw_liquid_dyn.txt` |
| normalized price | `qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/normalized_nonempty` |
| 当前 LTR 样本 | `data_tw/experiments/ltr_rerank_regime_turnover/phase1_ltr_baseline/phase1_ltr_samples.csv` |
| S1A coverage summary | `data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1/phase_s1a_qlib_score_rank_coverage.csv` |
| S1A daily coverage | `data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1/phase_s1a_qlib_score_rank_coverage_daily.csv` |
| S1A generation policy options | `data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s1/phase_s1a_generation_policy_options.json` |

## 3. Frozen qlib pred 覆盖结论

只读读取 `pred.pkl` 后确认：

| 项目 | 值 |
| --- | ---: |
| row count | `89550` |
| date min | `2023-01-03` |
| date max | `2025-06-30` |
| date count | `597` |
| instrument count | `412` |
| score missing | `0` |

结论：frozen qlib `pred.pkl` 只覆盖 S1 test 区间，不覆盖 S1 train / validation。

## 4. Split 覆盖统计

S1 固定 split：

| split | 日期区间 |
| --- | --- |
| `s1_train` | `2015-05-04..2020-12-31` |
| `s1_validation` | `2021-01-01..2022-12-31` |
| `s1_test` | `2023-01-01..2025-06-30` |

覆盖摘要：

| split | trading dates | target symbol-date | price present | missing price | frozen pred score | missing frozen score/rank | existing LTR sample rows | existing LTR feature complete |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `s1_train` | `1451` | `217650` | `208296` | `9354` | `0` | `217650` | `0` | `0` |
| `s1_validation` | `490` | `73500` | `73350` | `150` | `0` | `73500` | `16606` | `16078` |
| `s1_test` | `597` | `89550` | `89548` | `2` | `89550` | `0` | `49133` | `48296` |

解释：

- `s1_train`：没有 frozen qlib score/rank，也没有现有 LTR 样本覆盖；
- `s1_validation`：没有 frozen qlib score/rank；现有 LTR 样本仅覆盖 2022 年部分日期，不覆盖完整 2021..2022；
- `s1_test`：frozen qlib score/rank 覆盖完整；现有 LTR 样本覆盖其中一部分，但这不是 S1 split-aligned 新样本。

## 5. Price / label / feature 诊断

### 5.1 Price

本地 normalized price 覆盖：

- 文件数：`1987`
- 日期范围：`2015-01-02..2026-06-01`
- 总 date rows：`4850582`

S1 active universe 口径下，price 缺口较小：

- `s1_train`: `9354 / 217650`
- `s1_validation`: `150 / 73500`
- `s1_test`: `2 / 89550`

因此，S1A 的主要阻断不是 price，而是旧窗口 qlib score/rank 来源。

### 5.2 Label / feature

现有 LTR 样本不是按 S1 旧窗口构建：

- 当前 LTR 样本日期范围：`2022-01-03..2026-06-12`；
- 当前 LTR split 与 S1 split 不一致；
- `s1_train` 旧窗口 `2015-05-04..2020-12-31` 没有现成 LTR sample / label / feature；
- `s1_validation` 只在 2022 年存在部分现成样本，不覆盖 2021 年；
- S1B 若继续，必须重新构建 split-aligned 样本并重新做 leakage scan。

## 6. qlib score/rank 来源判断

| 来源 | 覆盖情况 | 是否可直接进入 S1B |
| --- | --- | --- |
| frozen `pred.pkl` | 仅 `2023-01-03..2025-06-30` | 否，缺 train/validation |
| 当前 LTR 样本字段 `qlib_score_raw` / `qlib_rank` | 现有 2022+ LTR 样本内存在 | 否，不覆盖 S1 train，且不是已证明的旧窗口生成口径 |
| historical backfill / daily signal | 仅发现 2026 附近日频预测产物 | 否，不能覆盖 2015..2022 |
| 重新生成 qlib score/rank | 技术上可能，但 S1A 未授权执行 | 需审查者明确生成政策 |

## 7. 生成口径选项

已写入 `phase_s1a_generation_policy_options.json`，摘要如下：

| option | 状态 | 风险 |
| --- | --- | --- |
| `use_frozen_pred_only` | `insufficient` | train/validation 无 qlib score/rank，不能训练 LTR |
| `generate_in_sample_scores_from_frozen_qlib_model_for_train_valid` | `requires_reviewer_decision` | LTR train 会使用 qlib 训练期 in-sample score，语义需审查确认 |
| `cross_fit_or_walk_forward_qlib_scores_for_train_valid` | `requires_new_training_design_and_reviewer_work_doc` | 更严谨，但需要冻结 qlib fold/训练计划，S1A 未授权 |
| `remove_qlib_score_rank_features_from_s1_ltr` | `out_of_scope_without_reviewer_decision` | 改变当前 LTR rerank 方法，不再是同方法验证 |

## 8. S1A 判断

S1A 发现：

1. frozen qlib `pred.pkl` 完整覆盖 S1 test；
2. frozen qlib `pred.pkl` 对 S1 train / validation 覆盖为 0；
3. 当前 LTR 方法依赖 `qlib_score_raw`、`qlib_rank` 等 qlib score/rank 特征；
4. 直接进入 S1B 构建样本和训练会缺少 train/validation qlib score/rank；
5. 若要生成 train/validation score/rank，必须先由审查者决定 in-sample、cross-fit/walk-forward 或其他生成政策。

因此，本轮停止在 S1A，不进入样本构建、训练或回放。

## 9. Gate 建议

建议 gate：

```text
split_aligned_data_insufficient_pending_generation_policy_decision
```

若审查者要求只能使用主线三选一 gate，则建议：

```text
split_aligned_data_insufficient
```

原因：在未冻结 qlib train/validation score/rank 生成口径前，无法公平构建 S1 split-aligned LTR 训练样本。
