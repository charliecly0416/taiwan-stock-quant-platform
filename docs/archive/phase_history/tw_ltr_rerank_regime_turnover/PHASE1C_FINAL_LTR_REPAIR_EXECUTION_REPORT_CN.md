# Phase 1C 执行报告：最后一轮保守 LTR 修复

生成时间：2026-06-13T16:39:22+00:00

## 1. 本轮目标

根据用户选择的最后一轮 Phase1C，只在 Stage 2 内尝试更贴近头部排序的 label 和 qlib-preserving rerank；若仍不过 gate，则停止 LTR reranker 主线。

## 2. 实际完成内容

- 新增脚本：`scripts/diagnose_tw_ltr_phase1c_final_repair.py`。
- 复用 Phase1 样本，不新增数据源。
- 继续排除 `trend_score`，不新增白名单外特征。
- 尝试 top-heavy label、qlib-only/all-whitelist 模型，以及 top50 内重排 / qlib blend / top30 保护策略。
- 只用 validation 选择候选；independent_test 只做最终检验。

## 3. 新增产物

- `data_tw/experiments/ltr_rerank_regime_turnover/phase1c_final_ltr_repair/phase1c_validation_selection.csv`
- `data_tw/experiments/ltr_rerank_regime_turnover/phase1c_final_ltr_repair/phase1c_independent_test_comparison.csv`
- `data_tw/experiments/ltr_rerank_regime_turnover/phase1c_final_ltr_repair/phase1c_topk_preservation_diagnostics.csv`
- `data_tw/experiments/ltr_rerank_regime_turnover/phase1c_final_ltr_repair/phase1c_gate_summary.json`
- `data_tw/experiments/ltr_rerank_regime_turnover/phase1c_final_ltr_repair/phase1c_diagnosis_summary.json`
- `docs/tw_ltr_rerank_regime_turnover/PHASE1C_FINAL_LTR_REPAIR_EXECUTION_REPORT_CN.md`

## 4. validation 选择

```text
     split                                       method                                       score_column  date_count  row_count  rank_ic_10d  ndcg_at_10  ndcg_at_30  ndcg_at_50  top10_future_excess_rank_10d  top10_mean_relevance_10d  top30_future_excess_rank_10d  top30_mean_relevance_10d  top50_future_excess_rank_10d  top50_mean_relevance_10d                                 candidate_id       model_id  blend_alpha      preserve_scope  selection_score
validation           head10_all_l31_alpha0.7_top50_only           score_head10_all_l31_alpha0.7_top50_only         209      30877     0.057973    0.552003    0.541477    0.574794                      0.533149                  2.157416                      0.528095                  2.133014                      0.520453                  2.098756           head10_all_l31_alpha0.7_top50_only head10_all_l31         0.70          top50_only         0.570781
validation  head10_all_l31_alpha0.7_full_universe_blend  score_head10_all_l31_alpha0.7_full_universe_blend         209      30877     0.062755    0.552003    0.541001    0.577642                      0.533149                  2.157416                      0.527689                  2.129506                      0.524063                  2.113493  head10_all_l31_alpha0.7_full_universe_blend head10_all_l31         0.70 full_universe_blend         0.570523
validation  head20_all_l31_alpha0.7_full_universe_blend  score_head20_all_l31_alpha0.7_full_universe_blend         209      30877     0.066540    0.552516    0.540295    0.574940                      0.545458                  2.212440                      0.531080                  2.144338                      0.523646                  2.112057  head20_all_l31_alpha0.7_full_universe_blend head20_all_l31         0.70 full_universe_blend         0.570176
validation     head10_all_l31_alpha0.7_top30_plus_top50     score_head10_all_l31_alpha0.7_top30_plus_top50         209      30877     0.057420    0.552318    0.540935    0.574641                      0.533509                  2.159330                      0.527304                  2.129665                      0.520453                  2.098756     head10_all_l31_alpha0.7_top30_plus_top50 head10_all_l31         0.70    top30_plus_top50         0.570171
validation  head10_all_l15_alpha0.7_full_universe_blend  score_head10_all_l15_alpha0.7_full_universe_blend         209      30877     0.066990    0.549420    0.540310    0.575378                      0.537390                  2.180383                      0.529717                  2.140829                      0.523429                  2.112344  head10_all_l15_alpha0.7_full_universe_blend head10_all_l15         0.70 full_universe_blend         0.570145
validation           head10_all_l15_alpha0.7_top50_only           score_head10_all_l15_alpha0.7_top50_only         209      30877     0.058628    0.549420    0.540122    0.572876                      0.537390                  2.180383                      0.529734                  2.140032                      0.520453                  2.098756           head10_all_l15_alpha0.7_top50_only head10_all_l15         0.70          top50_only         0.569540
validation  head20_all_l15_alpha0.7_full_universe_blend  score_head20_all_l15_alpha0.7_full_universe_blend         209      30877     0.064907    0.540469    0.539496    0.574164                      0.530429                  2.146411                      0.531896                  2.149282                      0.523790                  2.114258  head20_all_l15_alpha0.7_full_universe_blend head20_all_l15         0.70 full_universe_blend         0.569336
validation     head10_all_l15_alpha0.7_top30_plus_top50     score_head10_all_l15_alpha0.7_top30_plus_top50         209      30877     0.057973    0.548651    0.539715    0.572657                      0.536246                  2.175598                      0.529374                  2.138756                      0.520453                  2.098756     head10_all_l15_alpha0.7_top30_plus_top50 head10_all_l15         0.70    top30_plus_top50         0.569083
validation           head20_all_l31_alpha0.7_top50_only           score_head20_all_l31_alpha0.7_top50_only         209      30877     0.058601    0.552516    0.539424    0.572339                      0.545458                  2.212440                      0.529931                  2.138915                      0.520453                  2.098756           head20_all_l31_alpha0.7_top50_only head20_all_l31         0.70          top50_only         0.568851
validation head20_all_l31_alpha0.85_full_universe_blend score_head20_all_l31_alpha0.85_full_universe_blend         209      30877     0.061733    0.552302    0.538852    0.574491                      0.538803                  2.188038                      0.526990                  2.128389                      0.522185                  2.106603 head20_all_l31_alpha0.85_full_universe_blend head20_all_l31         0.85 full_universe_blend         0.568289
```

## 5. independent_test 最终对照

```text
           split                                                  method                             score_column  date_count  row_count  rank_ic_10d  ndcg_at_10  ndcg_at_30  ndcg_at_50  top10_future_excess_rank_10d  top10_mean_relevance_10d  top30_future_excess_rank_10d  top30_mean_relevance_10d  top50_future_excess_rank_10d  top50_mean_relevance_10d
independent_test phase1c_conservative_head10_all_l31_alpha0.7_top50_only score_head10_all_l31_alpha0.7_top50_only         209      31071     0.027360    0.559268    0.541698    0.567569                      0.550175                  2.258852                      0.527896                  2.149761                      0.513406                  2.077512
independent_test                                       rank_rotate_top30                           qlib_score_raw         209      31071     0.026642    0.543544    0.537373    0.565427                      0.535675                  2.185646                      0.526614                  2.140351                      0.513406                  2.077512
independent_test                                       rank_rotate_top50                           qlib_score_raw         209      31071     0.026642    0.543544    0.537373    0.565427                      0.535675                  2.185646                      0.526614                  2.140351                      0.513406                  2.077512
independent_test                        rank_rotate_top50_adaptive_score                  adaptive_score_baseline         209      31071     0.027657    0.545739    0.537928    0.565340                      0.538533                  2.198086                      0.527020                  2.142265                      0.513162                  2.075885
independent_test                                          confirmed_exit                  confirmed_exit_baseline         209      31071     0.026509    0.543636    0.537459    0.565503                      0.535675                  2.185646                      0.526716                  2.140670                      0.513478                  2.077799
```

## 6. TopK 保守性诊断

```text
                         metric    value  date_count
top10_candidate_vs_qlib_jaccard 0.503351         209
top30_candidate_vs_qlib_jaccard 0.691217         209
top50_candidate_vs_qlib_jaccard 1.000000         209
```

## 7. Gate 结论

- 推荐 gate：`request_phase2_regime_gating_work`。
- 原因：Phase1C conservative rerank cleared all user-approved final gate conditions.
- 条件：`{'rank_ic_higher_than_qlib': True, 'ndcg_at_30_not_lower_than_qlib': True, 'top30_future_excess_rank_not_lower_than_qlib': True, 'not_single_year_only': True}`。

## 8. 风险 / 异常 / 未解决问题

- 这是用户授权的最后一轮 LTR 修复。
- 若 gate 为 `stop_ltr_mainline_insufficient_evidence`，执行者不再继续扩大 LTR 搜索，不进入 Phase2。
- 本轮没有真实组合 replay，不能解释为组合净值、换手、动作次数、成本或可执行动作。

## 9. 禁止事项遵守情况

本轮未新增白名单外特征，未引入 `trend_score`，未引入 forbidden features，未联网，未 provider refresh/publish，未 accepted latest switching，未改 frontend / API / monitor / database，未做 regime gating 动作实现，未做 turnover portfolio layer，未接 broker / quick-trade / orders / target position / target weight，未输出买入、卖出、持有、仓位、收益承诺、上涨概率或胜率语义。
