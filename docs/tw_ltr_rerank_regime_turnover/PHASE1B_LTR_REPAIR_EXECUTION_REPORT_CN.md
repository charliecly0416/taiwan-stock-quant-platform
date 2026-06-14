# Phase 1B 执行报告：LTR Baseline 诊断与修复

生成时间：2026-06-13T16:12:52+00:00

## 1. 本轮目标

只诊断并尝试修复 Phase1 LTR baseline 在 independent_test 上 rank IC 改善但 TopK / NDCG 输给 qlib baseline 的问题；不进入 Phase2。

## 2. 实际完成内容

- 新增脚本：`scripts/diagnose_tw_ltr_phase1b_repair.py`。
- 复用 Phase1 样本：`phase1_ltr_baseline/phase1_ltr_samples.csv`。
- 对 5d / 10d / 20d label window 做小范围对照。
- 对 qlib-only、qlib+technical、qlib+liquidity、qlib+market、all whitelist 做 feature group ablation。
- 只用 train / validation 做轻量参数与模型选择。
- 最后对选中模型做 independent_test 对照。
- 检查 LTR 与 qlib TopK overlap 和日间名单稳定性。

## 3. 改动文件清单

- `scripts/diagnose_tw_ltr_phase1b_repair.py`
- `docs/tw_ltr_rerank_regime_turnover/PHASE1B_LTR_REPAIR_EXECUTION_REPORT_CN.md`

## 4. 新增产物清单

- `data_tw/experiments/ltr_rerank_regime_turnover/phase1b_ltr_repair/phase1b_diagnosis_summary.json`
- `data_tw/experiments/ltr_rerank_regime_turnover/phase1b_ltr_repair/phase1b_feature_ablation_metrics.csv`
- `data_tw/experiments/ltr_rerank_regime_turnover/phase1b_ltr_repair/phase1b_label_window_metrics.csv`
- `data_tw/experiments/ltr_rerank_regime_turnover/phase1b_ltr_repair/phase1b_validation_model_selection.csv`
- `data_tw/experiments/ltr_rerank_regime_turnover/phase1b_ltr_repair/phase1b_independent_test_comparison.csv`
- `data_tw/experiments/ltr_rerank_regime_turnover/phase1b_ltr_repair/phase1b_topk_overlap_and_stability.csv`
- `data_tw/experiments/ltr_rerank_regime_turnover/phase1b_ltr_repair/phase1b_gate_summary.json`

## 5. 诊断结论

- Phase1 的主要问题不是整体排序完全失效，而是 TopK 头部集中度不足。
- validation 上可选模型仍能提升 NDCG，但 independent_test 上 qlib 头部排序更稳。
- repaired LTR 与 qlib 的 TopK overlap / day-to-day stability 见下表，说明 LTR 对头部名单有明显重排，但未转化为更好的 independent_test TopK 质量。

```text
           split                                          metric    value  date_count
independent_test          top10_repaired_vs_qlib_jaccard_overlap 0.120824         209
independent_test top10_repaired_ltr_day_to_day_jaccard_stability 0.629558         208
independent_test         top10_qlib_day_to_day_jaccard_stability 0.319623         208
independent_test     top10_adaptive_day_to_day_jaccard_stability 0.326271         208
independent_test          top30_repaired_vs_qlib_jaccard_overlap 0.244095         209
independent_test top30_repaired_ltr_day_to_day_jaccard_stability 0.708284         208
independent_test         top30_qlib_day_to_day_jaccard_stability 0.398962         208
independent_test     top30_adaptive_day_to_day_jaccard_stability 0.407761         208
independent_test          top50_repaired_vs_qlib_jaccard_overlap 0.330728         209
independent_test top50_repaired_ltr_day_to_day_jaccard_stability 0.768046         208
independent_test         top50_qlib_day_to_day_jaccard_stability 0.440619         208
independent_test     top50_adaptive_day_to_day_jaccard_stability 0.450809         208
```

## 6. validation 模型选择

只基于 validation 的 selection_score = NDCG@30 + 0.10 * rank_ic_10d 选择模型，未用 independent_test 调参。

```text
     split                                             method       score_column  date_count  row_count  rank_ic_10d  ndcg_at_10  ndcg_at_30  ndcg_at_50  top10_rows  top10_future_excess_rank_10d  top10_mean_relevance_10d  top30_rows  top30_future_excess_rank_10d  top30_mean_relevance_10d  top50_rows  top50_future_excess_rank_10d  top50_mean_relevance_10d                                       candidate_id label_window                     feature_group  feature_count  num_leaves  learning_rate  n_estimators  selection_score
validation candidate_30_20d_all_whitelist_without_trend_score repaired_ltr_score         209      30877     0.079899    0.561579    0.551745    0.584878        2090                      0.554905                  2.243062        6270                      0.540890                  2.185965       10450                      0.531656                  2.144019 candidate_30_20d_all_whitelist_without_trend_score          20d all_whitelist_without_trend_score             34          31           0.03           120         0.559735
validation candidate_29_20d_all_whitelist_without_trend_score repaired_ltr_score         209      30877     0.060072    0.567053    0.548580    0.580473        2090                      0.550356                  2.228230        6270                      0.534576                  2.152632       10450                      0.524920                  2.112919 candidate_29_20d_all_whitelist_without_trend_score          20d all_whitelist_without_trend_score             34          15           0.05            80         0.554587
validation               candidate_14_10d_qlib_plus_technical repaired_ltr_score         209      30877     0.067828    0.552055    0.544923    0.577427        2090                      0.544714                  2.207177        6270                      0.535599                  2.165391       10450                      0.525987                  2.119809               candidate_14_10d_qlib_plus_technical          10d               qlib_plus_technical             22          31           0.03           120         0.551706
validation               candidate_13_10d_qlib_plus_technical repaired_ltr_score         209      30877     0.066388    0.549369    0.540891    0.572125        2090                      0.542789                  2.203828        6270                      0.531588                  2.148963       10450                      0.521034                  2.097990               candidate_13_10d_qlib_plus_technical          10d               qlib_plus_technical             22          15           0.05            80         0.547529
validation candidate_20_10d_all_whitelist_without_trend_score repaired_ltr_score         209      30877     0.071847    0.552588    0.539220    0.576191        2090                      0.541728                  2.197129        6270                      0.529154                  2.131579       10450                      0.524626                  2.114737 candidate_20_10d_all_whitelist_without_trend_score          10d all_whitelist_without_trend_score             34          31           0.03           120         0.546405
validation                candidate_04_5d_qlib_plus_technical repaired_ltr_score         209      30877     0.062636    0.557192    0.539918    0.576610        2090                      0.539098                  2.181818        6270                      0.524903                  2.119936       10450                      0.522149                  2.107177                candidate_04_5d_qlib_plus_technical           5d               qlib_plus_technical             22          31           0.03           120         0.546181
validation               candidate_16_10d_qlib_plus_liquidity repaired_ltr_score         209      30877     0.056122    0.556815    0.537585    0.573992        2090                      0.543334                  2.207177        6270                      0.523477                  2.116427       10450                      0.521529                  2.101627               candidate_16_10d_qlib_plus_liquidity          10d               qlib_plus_liquidity             17          31           0.03           120         0.543197
validation  candidate_10_5d_all_whitelist_without_trend_score repaired_ltr_score         209      30877     0.080782    0.548807    0.533959    0.576402        2090                      0.537163                  2.172249        6270                      0.521867                  2.103349       10450                      0.524832                  2.119330  candidate_10_5d_all_whitelist_without_trend_score           5d all_whitelist_without_trend_score             34          31           0.03           120         0.542037
```

## 7. independent_test 对照

```text
           split                                                          method            score_column  date_count  row_count  rank_ic_10d  ndcg_at_10  ndcg_at_30  ndcg_at_50  top10_rows  top10_future_excess_rank_10d  top10_mean_relevance_10d  top30_rows  top30_future_excess_rank_10d  top30_mean_relevance_10d  top50_rows  top50_future_excess_rank_10d  top50_mean_relevance_10d
independent_test repaired_ltr_candidate_30_20d_all_whitelist_without_trend_score      repaired_ltr_score         209      31071     0.059551    0.520816    0.525077    0.566626        2090                      0.524711                  2.120574        6270                      0.523047                  2.116906       10450                      0.522693                  2.118278
independent_test                                               rank_rotate_top30          qlib_score_raw         209      31071     0.026642    0.543544    0.537373    0.565427        2090                      0.535675                  2.185646        6270                      0.526614                  2.140351       10450                      0.513406                  2.077512
independent_test                                               rank_rotate_top50          qlib_score_raw         209      31071     0.026642    0.543544    0.537373    0.565427        2090                      0.535675                  2.185646        6270                      0.526614                  2.140351       10450                      0.513406                  2.077512
independent_test                                rank_rotate_top50_adaptive_score adaptive_score_baseline         209      31071     0.027657    0.545739    0.537928    0.565340        2090                      0.538533                  2.198086        6270                      0.527020                  2.142265       10450                      0.513162                  2.075885
independent_test                                                  confirmed_exit confirmed_exit_baseline         209      31071     0.026509    0.543636    0.537459    0.565503        2090                      0.535675                  2.185646        6270                      0.526716                  2.140670       10450                      0.513478                  2.077799
```

## 8. Gate 结论

- 推荐 gate：`phase1b_ltr_needs_repair`。
- gate 原因：some repaired LTR signals improved, but Phase1B gate was not fully cleared。
- rank IC 条件：`True`。
- NDCG@30 条件：`False`。
- Top30 future excess rank 条件：`False`。
- 非单一 segment 条件：`True`。

## 9. 风险 / 异常 / 未解决问题

- 本轮没有新增数据、没有新增白名单外特征，`trend_score` 仍排除。
- 本轮没有真实组合 replay，因此不解释为组合净值、换手、动作次数、成本或可执行动作结论。
- 如果审查者认为 rank IC 改善但 TopK 不改善仍可推进，需要用户明确放宽 gate；执行者本轮未自行放宽。

## 10. 需要审查者重点检查的点

- 是否认可 validation-only 模型选择流程。
- 是否认可 repaired LTR 的 gate 判定。
- `phase1b_independent_test_comparison.csv` 是否显示仍无法满足 Phase2 前置证据。
- 是否存在越界特征、越权数据源或真实交易语义。

## 11. 禁止事项遵守情况

本轮未新增白名单外特征，未引入 `trend_score`，未引入 forbidden features，未联网，未 provider refresh/publish，未 accepted latest switching，未改 frontend / API / monitor / database，未做 regime gating 动作实现，未做 turnover portfolio layer，未接 broker / quick-trade / orders / target position / target weight，未输出买入、卖出、持有、仓位、收益承诺、上涨概率或胜率语义。
