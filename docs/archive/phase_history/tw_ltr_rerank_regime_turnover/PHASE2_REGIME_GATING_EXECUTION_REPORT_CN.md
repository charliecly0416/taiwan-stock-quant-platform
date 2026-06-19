# Phase 2 执行报告：Regime-aware Gating 最小离线评估

生成时间：2026-06-13T17:10:22+00:00

## 1. 本轮目标

只做 Stage 3 regime-aware gating 的最小离线实现与评估，验证 `qlib baseline + qlib-preserving LTR rerank` 在 normal / caution / risk_off 下是否需要不同保守阈值。

## 2. 实际完成内容

- 新增只读离线脚本：`scripts/evaluate_tw_ltr_phase2_regime_gating.py`。
- 复用 Phase1 样本。
- 复现 Phase1C 冻结的 `qlib-preserving LTR rerank`：`score_head10_all_l31_alpha0.7_top50_only`。
- 仅使用 5 个 regime 白名单字段生成 3 态。
- 只做阈值 / 过滤 / 候选保守程度评估；未生成真实动作指令，未做 turnover layer。

## 3. 改动文件清单

- `scripts/evaluate_tw_ltr_phase2_regime_gating.py`
- `docs/tw_ltr_rerank_regime_turnover/PHASE2_REGIME_GATING_EXECUTION_REPORT_CN.md`

## 4. 新增产物清单

- `data_tw/experiments/ltr_rerank_regime_turnover/phase2_regime_gating/phase2_regime_definition.json`
- `data_tw/experiments/ltr_rerank_regime_turnover/phase2_regime_gating/phase2_regime_distribution.csv`
- `data_tw/experiments/ltr_rerank_regime_turnover/phase2_regime_gating/phase2_regime_metric_by_state.csv`
- `data_tw/experiments/ltr_rerank_regime_turnover/phase2_regime_gating/phase2_gating_threshold_grid.csv`
- `data_tw/experiments/ltr_rerank_regime_turnover/phase2_regime_gating/phase2_baseline_vs_regime_gated_comparison.csv`
- `data_tw/experiments/ltr_rerank_regime_turnover/phase2_regime_gating/phase2_gate_summary.json`

## 5. Regime 分布

```text
           split   regime  date_count  row_count  mean_TWII_ret20  mean_TWII_ret60  mean_market_drawdown60  mean_market_volatility20  mean_market_breadth20
           train  caution         131      18955         0.016883        -0.006166               -0.045052                  0.009603               0.589800
           train   normal         279      40385         0.041821         0.096826               -0.008360                  0.008897               0.680134
           train risk_off         215      30961        -0.040082        -0.044364               -0.092048                  0.012091               0.298239
      validation  caution          71      10514         0.026644        -0.009651               -0.049456                  0.012620               0.581301
      validation   normal          47       6997         0.022401         0.042209               -0.012165                  0.011153               0.611340
      validation risk_off          91      13366        -0.032798        -0.053378               -0.097928                  0.019943               0.382216
independent_test  caution          44       6591         0.048228         0.192817               -0.034319                  0.020007               0.651691
independent_test   normal         158      23435         0.062745         0.151230               -0.007334                  0.010756               0.661998
independent_test risk_off           7       1045        -0.043294         0.116288               -0.071054                  0.015369               0.287081
```

## 6. Regime 分状态指标

```text
           split   regime                      method                             score_column  date_count  row_count  rank_ic_10d  ndcg_at_10  ndcg_at_30  ndcg_at_50  top10_future_excess_rank_10d  top10_mean_relevance_10d  top10_median_qlib_rank  top30_future_excess_rank_10d  top30_mean_relevance_10d  top30_median_qlib_rank  top50_future_excess_rank_10d  top50_mean_relevance_10d  top50_median_qlib_rank
independent_test   normal      qlib_rank_rotate_top50                           qlib_score_raw         158      23435     0.022045    0.554318    0.541395    0.565974                      0.541264                  2.215190                     6.0                      0.526825                  2.141561                    16.0                      0.510877                  2.063924                    26.0
independent_test   normal phase1c_qlib_preserving_ltr score_head10_all_l31_alpha0.7_top50_only         158      23435     0.021856    0.557412    0.539960    0.565151                      0.548702                  2.253165                     7.0                      0.525629                  2.139451                    16.0                      0.510877                  2.063924                    26.0
independent_test   normal    regime_gate_c50_r50_p0.0                         gate_c50_r50_p00         158      23435     0.021856    0.557412    0.539960    0.565151                      0.548702                  2.253165                     7.0                      0.525629                  2.139451                    16.0                      0.510877                  2.063924                    26.0
independent_test  caution      qlib_rank_rotate_top50                           qlib_score_raw          44       6591     0.064108    0.528537    0.537322    0.574311                      0.528378                  2.145455                     5.5                      0.533712                  2.172727                    16.0                      0.527375                  2.147273                    26.0
independent_test  caution phase1c_qlib_preserving_ltr score_head10_all_l31_alpha0.7_top50_only          44       6591     0.067334    0.586304    0.557033    0.584871                      0.575719                  2.370455                    10.0                      0.540668                  2.207576                    17.0                      0.527375                  2.147273                    26.0
independent_test  caution    regime_gate_c50_r50_p0.0                         gate_c50_r50_p00          44       6591     0.067334    0.586304    0.557033    0.584871                      0.575719                  2.370455                    10.0                      0.540668                  2.207576                    17.0                      0.527375                  2.147273                    26.0
independent_test risk_off      qlib_rank_rotate_top50                           qlib_score_raw           7       1045    -0.105109    0.394686    0.446912    0.497248                      0.455381                  1.771429                     6.0                      0.477222                  1.909524                    16.0                      0.482686                  1.945714                    26.0
independent_test risk_off phase1c_qlib_preserving_ltr score_head10_all_l31_alpha0.7_top50_only           7       1045    -0.099686    0.424262    0.485475    0.514080                      0.422857                  1.685714                    11.5                      0.498603                  2.019048                    18.0                      0.482686                  1.945714                    26.0
independent_test risk_off    regime_gate_c50_r50_p0.0                         gate_c50_r50_p00           7       1045    -0.099686    0.424262    0.485475    0.514080                      0.422857                  1.685714                    11.5                      0.498603                  2.019048                    18.0                      0.482686                  1.945714                    26.0
```

## 7. validation 阈值网格 Top10

```text
     split regime                    method      score_column  date_count  row_count  rank_ic_10d  ndcg_at_10  ndcg_at_30  ndcg_at_50  top10_future_excess_rank_10d  top10_mean_relevance_10d  top10_median_qlib_rank  top30_future_excess_rank_10d  top30_mean_relevance_10d  top30_median_qlib_rank  top50_future_excess_rank_10d  top50_mean_relevance_10d  top50_median_qlib_rank  caution_scope  risk_scope  risk_penalty  selection_score
validation    all  regime_gate_c50_r50_p0.0  gate_c50_r50_p00         209      30877     0.057987    0.552061    0.541481    0.574777                      0.532687                  2.155502                     8.0                      0.528127                  2.133174                    17.0                      0.520453                  2.098756                    26.0             50          50          0.00         0.569627
validation    all regime_gate_c50_r50_p0.02 gate_c50_r50_p002         209      30877     0.057987    0.552061    0.541481    0.574777                      0.532687                  2.155502                     8.0                      0.528127                  2.133174                    17.0                      0.520453                  2.098756                    26.0             50          50          0.02         0.569627
validation    all regime_gate_c50_r50_p0.05 gate_c50_r50_p005         209      30877     0.057987    0.552061    0.541481    0.574777                      0.532687                  2.155502                     8.0                      0.528127                  2.133174                    17.0                      0.520453                  2.098756                    26.0             50          50          0.05         0.569627
validation    all regime_gate_c40_r50_p0.02 gate_c40_r50_p002         209      30877     0.057513    0.551826    0.540888    0.574648                      0.532375                  2.154067                     8.0                      0.527332                  2.129984                    17.0                      0.520453                  2.098756                    26.0             40          50          0.02         0.568980
validation    all  regime_gate_c40_r50_p0.0  gate_c40_r50_p00         209      30877     0.057513    0.551826    0.540888    0.574648                      0.532375                  2.154067                     8.0                      0.527332                  2.129984                    17.0                      0.520453                  2.098756                    26.0             40          50          0.00         0.568980
validation    all regime_gate_c40_r50_p0.05 gate_c40_r50_p005         209      30877     0.057513    0.551826    0.540888    0.574648                      0.532375                  2.154067                     8.0                      0.527332                  2.129984                    17.0                      0.520453                  2.098756                    26.0             40          50          0.05         0.568980
validation    all  regime_gate_c50_r40_p0.0  gate_c50_r40_p00         209      30877     0.057311    0.552213    0.540823    0.574579                      0.532847                  2.156459                     8.0                      0.527348                  2.129665                    17.0                      0.520453                  2.098756                    26.0             50          40          0.00         0.568910
validation    all regime_gate_c50_r40_p0.02 gate_c50_r40_p002         209      30877     0.057311    0.552213    0.540823    0.574579                      0.532847                  2.156459                     8.0                      0.527348                  2.129665                    17.0                      0.520453                  2.098756                    26.0             50          40          0.02         0.568910
validation    all regime_gate_c50_r40_p0.05 gate_c50_r40_p005         209      30877     0.057311    0.552213    0.540823    0.574579                      0.532847                  2.156459                     8.0                      0.527348                  2.129665                    17.0                      0.520453                  2.098756                    26.0             50          40          0.05         0.568910
validation    all  regime_gate_c40_r40_p0.0  gate_c40_r40_p00         209      30877     0.056837    0.551978    0.540230    0.574450                      0.532536                  2.155024                     8.0                      0.526553                  2.126475                    16.0                      0.520453                  2.098756                    26.0             40          40          0.00         0.568262
```

## 8. independent_test 最终对照

```text
           split regime                           method                             score_column  date_count  row_count  rank_ic_10d  ndcg_at_10  ndcg_at_30  ndcg_at_50  top10_future_excess_rank_10d  top10_mean_relevance_10d  top10_median_qlib_rank  top30_future_excess_rank_10d  top30_mean_relevance_10d  top30_median_qlib_rank  top50_future_excess_rank_10d  top50_mean_relevance_10d  top50_median_qlib_rank
independent_test    all           qlib_rank_rotate_top50                           qlib_score_raw         209      31071     0.026642    0.543544    0.537373    0.565427                      0.535675                  2.185646                     6.0                      0.526614                  2.140351                    16.0                      0.513406                  2.077512                    26.0
independent_test    all      phase1c_qlib_preserving_ltr score_head10_all_l31_alpha0.7_top50_only         209      31071     0.027360    0.559035    0.541729    0.567592                      0.550175                  2.258852                     8.0                      0.527890                  2.149761                    16.0                      0.513406                  2.077512                    26.0
independent_test    all rank_rotate_top50_adaptive_score                  adaptive_score_baseline         209      31071     0.027657    0.545739    0.537928    0.565340                      0.538533                  2.198086                     6.0                      0.527020                  2.142265                    16.0                      0.513162                  2.075885                    26.0
independent_test    all                   confirmed_exit                  confirmed_exit_baseline         209      31071     0.026509    0.543636    0.537459    0.565503                      0.535675                  2.185646                     6.0                      0.526716                  2.140670                    16.0                      0.513478                  2.077799                    26.0
independent_test    all         regime_gate_c50_r50_p0.0                         gate_c50_r50_p00         209      31071     0.027360    0.559035    0.541729    0.567592                      0.550175                  2.258852                     8.0                      0.527890                  2.149761                    16.0                      0.513406                  2.077512                    26.0
```

## 9. independent_test 分年度结果

```text
           split regime                      method                             score_column  date_count  row_count  rank_ic_10d  ndcg_at_10  ndcg_at_30  ndcg_at_50  top10_future_excess_rank_10d  top10_mean_relevance_10d  top10_median_qlib_rank  top30_future_excess_rank_10d  top30_mean_relevance_10d  top30_median_qlib_rank  top50_future_excess_rank_10d  top50_mean_relevance_10d  top50_median_qlib_rank  year
independent_test    all      qlib_rank_rotate_top50                           qlib_score_raw         130      19249     0.020326    0.550532    0.536989    0.563409                      0.542003                  2.220000                     6.0                      0.524523                  2.127179                    16.0                      0.510394                  2.057692                    26.0  2025
independent_test    all      qlib_rank_rotate_top50                           qlib_score_raw          79      11822     0.037035    0.532044    0.538006    0.568750                      0.525262                  2.129114                     5.5                      0.530055                  2.162025                    15.5                      0.518364                  2.110127                    26.0  2026
independent_test    all phase1c_qlib_preserving_ltr score_head10_all_l31_alpha0.7_top50_only         130      19249     0.021492    0.554963    0.537513    0.563090                      0.551271                  2.263077                     7.0                      0.525292                  2.134615                    16.0                      0.510394                  2.057692                    26.0  2025
independent_test    all phase1c_qlib_preserving_ltr score_head10_all_l31_alpha0.7_top50_only          79      11822     0.037016    0.565736    0.548667    0.575001                      0.548371                  2.251899                     9.0                      0.532165                  2.174684                    17.0                      0.518364                  2.110127                    26.0  2026
independent_test    all    regime_gate_c50_r50_p0.0                         gate_c50_r50_p00         130      19249     0.021492    0.554963    0.537513    0.563090                      0.551271                  2.263077                     7.0                      0.525292                  2.134615                    16.0                      0.510394                  2.057692                    26.0  2025
independent_test    all    regime_gate_c50_r50_p0.0                         gate_c50_r50_p00          79      11822     0.037016    0.565736    0.548667    0.575001                      0.548371                  2.251899                     9.0                      0.532165                  2.174684                    17.0                      0.518364                  2.110127                    26.0  2026
```

## 10. Gate 结论

- 推荐 gate：`stop_regime_gating_insufficient_evidence`。
- 原因：Regime gating did not provide incremental explanation or stability over Phase1C.
- 条件：`{'core_topk_not_lower_than_phase1c': True, 'caution_or_risk_off_conservative_effect': False, 'not_single_year_only': True, 'conservative_effect': {'passed': False, 'has_non_noop_gate': False, 'details': [{'regime': 'caution', 'has_rows': True, 'date_count': 44, 'base_top30_median_qlib_rank': 17.0, 'gated_top30_median_qlib_rank': 17.0, 'base_top30_future_excess_rank_10d': 0.5406682089349876, 'gated_top30_future_excess_rank_10d': 0.5406682089349876, 'strictly_more_conservative_top30': False}, {'regime': 'risk_off', 'has_rows': True, 'date_count': 7, 'base_top30_median_qlib_rank': 18.0, 'gated_top30_median_qlib_rank': 18.0, 'base_top30_future_excess_rank_10d': 0.4986031746031746, 'gated_top30_future_excess_rank_10d': 0.4986031746031746, 'strictly_more_conservative_top30': False}]}}`。

## 11. 风险 / 异常 / 未解决问题

- 本轮不是 turnover layer，不报告组合净值、换手、动作次数或成本。
- Regime 不是买卖信号、收益预测或概率预测，只是离线研究排序的保守过滤状态。
- 若 gate 未通过，不得强行进入 Phase3。
- validation 选择出的最优配置为 `regime_gate_c50_r50_p0.0`，这是 Phase1C 等价的 no-op gating；因此不能把它解释为已经证明需要不同 regime 阈值。

## 12. 需要审查者重点检查的点

- Regime 定义是否只使用主文档 5 个白名单字段。
- Phase1C score 是否保持 `qlib-preserving LTR rerank` 语义。
- 阈值选择是否只基于 validation。
- 是否存在真实动作、前端/API/provider/monitor/trading 越界。

## 13. 禁止事项遵守情况

本轮未新增数据源，未新增白名单外特征，未引入 `trend_score` 或 forbidden features，未联网，未 provider refresh/publish，未 accepted latest switching，未改 frontend / API / monitor / database，未做 turnover portfolio layer，未接 broker / quick-trade / orders / target position / target weight，未输出买入、卖出、持有、仓位、收益承诺、上涨概率或胜率语义。
