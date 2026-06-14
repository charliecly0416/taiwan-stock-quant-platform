# Phase 2B 执行报告：Regime Gating 修复

生成时间：2026-06-13T17:38:46+00:00

## 1. 本轮目标

只做 Stage 3 regime-aware gating 的一次修复：在固定 Phase1C `qlib-preserving LTR rerank` 的前提下，测试是否能得到非 no-op、可解释、且不降低核心 TopK 质量的 regime gating。

## 2. 实际完成内容

- 新增只读离线脚本：`scripts/repair_tw_ltr_phase2b_regime_gating.py`。
- 复用 Phase1 样本并复现 Phase1C score：`score_head10_all_l31_alpha0.7_top50_only`。
- 仅使用 5 个 regime 白名单字段生成多个候选 regime definition。
- 生成多个非 no-op gating rule，并保留 Phase2 no-op gate 作为对照。
- 只用 validation selection score 选择候选，independent_test 只做最终检验。
- 未进入 Stage 4 turnover layer，未生成真实动作语义。

## 3. 改动文件清单

- `scripts/repair_tw_ltr_phase2b_regime_gating.py`
- `docs/tw_ltr_rerank_regime_turnover/PHASE2B_REGIME_REPAIR_EXECUTION_REPORT_CN.md`

## 4. 新增产物清单

- `data_tw/experiments/ltr_rerank_regime_turnover/phase2b_regime_repair/phase2b_regime_definition_candidates.json`
- `data_tw/experiments/ltr_rerank_regime_turnover/phase2b_regime_repair/phase2b_regime_distribution.csv`
- `data_tw/experiments/ltr_rerank_regime_turnover/phase2b_regime_repair/phase2b_validation_selection.csv`
- `data_tw/experiments/ltr_rerank_regime_turnover/phase2b_regime_repair/phase2b_regime_metric_by_state.csv`
- `data_tw/experiments/ltr_rerank_regime_turnover/phase2b_regime_repair/phase2b_independent_test_comparison.csv`
- `data_tw/experiments/ltr_rerank_regime_turnover/phase2b_regime_repair/phase2b_gate_summary.json`

## 5. Regime 候选分布

```text
            definition_id            split   regime  date_count  row_count  mean_TWII_ret20  mean_TWII_ret60  mean_market_drawdown60  mean_market_volatility20  mean_market_breadth20
          phase2_original            train  caution         131      18955         0.016883        -0.006166               -0.045052                  0.009603               0.589800
          phase2_original            train   normal         279      40385         0.041821         0.096826               -0.008360                  0.008897               0.680134
          phase2_original            train risk_off         215      30961        -0.040082        -0.044364               -0.092048                  0.012091               0.298239
          phase2_original       validation  caution          71      10514         0.026644        -0.009651               -0.049456                  0.012620               0.581301
          phase2_original       validation   normal          47       6997         0.022401         0.042209               -0.012165                  0.011153               0.611340
          phase2_original       validation risk_off          91      13366        -0.032798        -0.053378               -0.097928                  0.019943               0.382216
          phase2_original independent_test  caution          44       6591         0.048228         0.192817               -0.034319                  0.020007               0.651691
          phase2_original independent_test   normal         158      23435         0.062745         0.151230               -0.007334                  0.010756               0.661998
          phase2_original independent_test risk_off           7       1045        -0.043294         0.116288               -0.071054                  0.015369               0.287081
balanced_drawdown_breadth            train  caution         126      18217         0.018493         0.005415               -0.037921                  0.009892               0.613842
balanced_drawdown_breadth            train   normal         244      35368         0.045092         0.102788               -0.006420                  0.008822               0.698760
balanced_drawdown_breadth            train risk_off         255      36716        -0.031694        -0.035793               -0.085075                  0.011533               0.326412
balanced_drawdown_breadth       validation  caution          69      10245         0.024022         0.004244               -0.036831                  0.012641               0.583791
balanced_drawdown_breadth       validation   normal          27       4018         0.025310         0.056230               -0.009297                  0.010980               0.653071
balanced_drawdown_breadth       validation risk_off         113      16614        -0.021024        -0.047490               -0.090244                  0.018277               0.414895
balanced_drawdown_breadth independent_test  caution          52       7775         0.069894         0.188842               -0.023722                  0.017284               0.650597
balanced_drawdown_breadth independent_test   normal         142      21051         0.061542         0.148778               -0.006169                  0.010559               0.671409
balanced_drawdown_breadth independent_test risk_off          15       2245        -0.042718         0.149800               -0.070376                  0.019301               0.408463
        breadth_sensitive            train  caution         141      20349         0.024048         0.027562               -0.030223                  0.010127               0.632446
        breadth_sensitive            train   normal         202      29340         0.049364         0.105982               -0.005307                  0.008608               0.723780
        breadth_sensitive            train risk_off         282      40612        -0.028802        -0.030791               -0.080537                  0.011254               0.339192
        breadth_sensitive       validation  caution          69      10245         0.026465         0.008334               -0.031931                  0.012692               0.613928
        breadth_sensitive       validation   normal          14       2085         0.024246         0.069351               -0.008454                  0.011028               0.691764
        breadth_sensitive       validation risk_off         126      18547        -0.017426        -0.040414               -0.084609                  0.017483               0.418721
        breadth_sensitive independent_test  caution          71      10599         0.061499         0.173854               -0.019867                  0.016158               0.658416
        breadth_sensitive independent_test   normal         116      17185         0.068161         0.151811               -0.003991                  0.010010               0.685154
        breadth_sensitive independent_test risk_off          22       3287        -0.024373         0.147523               -0.058763                  0.017256               0.412624
severe_risk_broad_caution            train  caution         206      29756         0.011988         0.001044               -0.046034                  0.009757               0.551944
severe_risk_broad_caution            train   normal         249      36103         0.044723         0.101429               -0.006607                  0.008835               0.697853
severe_risk_broad_caution            train risk_off         170      24442        -0.049232        -0.052086               -0.099548                  0.012535               0.256215
severe_risk_broad_caution       validation  caution         107      15845         0.023671        -0.009077               -0.047834                  0.012228               0.551702
severe_risk_broad_caution       validation   normal          35       5210         0.025002         0.046930               -0.009570                  0.011170               0.643386
severe_risk_broad_caution       validation risk_off          67       9822        -0.051601        -0.063150               -0.112626                  0.022942               0.346599
severe_risk_broad_caution independent_test  caution          64       9573         0.048855         0.184012               -0.032758                  0.017956               0.613015
severe_risk_broad_caution independent_test   normal         142      21051         0.061542         0.148778               -0.006169                  0.010559               0.671409
severe_risk_broad_caution independent_test risk_off           3        447        -0.045100         0.096202               -0.064520                  0.013038               0.239374
```

## 6. validation 选择 Top12

```text
     split regime                                          method                                         score_column  date_count  row_count  rank_ic_10d  ndcg_at_10  ndcg_at_30  ndcg_at_50  top10_future_excess_rank_10d  top10_mean_relevance_10d  top10_median_qlib_rank  top30_future_excess_rank_10d  top30_mean_relevance_10d  top30_median_qlib_rank  top50_future_excess_rank_10d  top50_mean_relevance_10d  top50_median_qlib_rank             definition_id              gate_id                    regime_column  caution_scope  risk_scope  non_noop  conservative_effect_passed  selection_score
validation    all balanced_drawdown_breadth__caution_only_c40_r50 score_balanced_drawdown_breadth_caution_only_c40_r50         209      30877     0.057787    0.552061    0.541770    0.574750                      0.532687                  2.155502                     8.0                      0.528169                  2.134928                    17.0                      0.520453                  2.098756                    26.0 balanced_drawdown_breadth caution_only_c40_r50 regime_balanced_drawdown_breadth             40          50      True                        True         0.572484
validation    all         breadth_sensitive__caution_only_c40_r50         score_breadth_sensitive_caution_only_c40_r50         209      30877     0.057915    0.552061    0.541482    0.574771                      0.532687                  2.155502                     8.0                      0.527887                  2.133014                    17.0                      0.520453                  2.098756                    26.0         breadth_sensitive caution_only_c40_r50         regime_breadth_sensitive             40          50      True                        True         0.571824
validation    all severe_risk_broad_caution__caution_only_c40_r50 score_severe_risk_broad_caution_caution_only_c40_r50         209      30877     0.057649    0.551978    0.541657    0.574721                      0.532536                  2.155024                     8.0                      0.528007                  2.134290                    17.0                      0.520453                  2.098756                    26.0 severe_risk_broad_caution caution_only_c40_r50 regime_severe_risk_broad_caution             40          50      True                        True         0.571770
validation    all           phase2_original__caution_only_c40_r50           score_phase2_original_caution_only_c40_r50         209      30877     0.057513    0.551826    0.540888    0.574648                      0.532375                  2.154067                     8.0                      0.527332                  2.129984                    17.0                      0.520453                  2.098756                    26.0           phase2_original caution_only_c40_r50           regime_phase2_original             40          50      True                        True         0.566222
validation    all                 breadth_sensitive__mild_c45_r40                 score_breadth_sensitive_mild_c45_r40         209      30877     0.057071    0.551978    0.540648    0.574517                      0.532536                  2.155024                     8.0                      0.527071                  2.128708                    16.0                      0.520453                  2.098756                    26.0         breadth_sensitive         mild_c45_r40         regime_breadth_sensitive             45          40      True                        True         0.565129
validation    all         balanced_drawdown_breadth__mild_c45_r40         score_balanced_drawdown_breadth_mild_c45_r40         209      30877     0.057087    0.551978    0.540481    0.574517                      0.532536                  2.155024                     8.0                      0.526920                  2.127911                    17.0                      0.520453                  2.098756                    26.0 balanced_drawdown_breadth         mild_c45_r40 regime_balanced_drawdown_breadth             45          40      True                        True         0.563897
validation    all                   phase2_original__mild_c45_r40                   score_phase2_original_mild_c45_r40         209      30877     0.056965    0.552213    0.540421    0.574495                      0.532847                  2.156459                     8.0                      0.526862                  2.127432                    17.0                      0.520453                  2.098756                    26.0           phase2_original         mild_c45_r40           regime_phase2_original             45          40      True                        True         0.563852
validation    all         severe_risk_broad_caution__mild_c45_r40         score_severe_risk_broad_caution_mild_c45_r40         209      30877     0.057136    0.552213    0.540138    0.574525                      0.532847                  2.156459                     8.0                      0.526601                  2.125837                    17.0                      0.520453                  2.098756                    26.0 severe_risk_broad_caution         mild_c45_r40 regime_severe_risk_broad_caution             45          40      True                        True         0.561756
validation    all            phase2_original__phase2_noop_c50_r50            score_phase2_original_phase2_noop_c50_r50         209      30877     0.057987    0.552061    0.541481    0.574777                      0.532687                  2.155502                     8.0                      0.528127                  2.133174                    17.0                      0.520453                  2.098756                    26.0           phase2_original  phase2_noop_c50_r50           regime_phase2_original             50          50     False                       False         0.559627
validation    all  severe_risk_broad_caution__phase2_noop_c50_r50  score_severe_risk_broad_caution_phase2_noop_c50_r50         209      30877     0.057987    0.552061    0.541481    0.574777                      0.532687                  2.155502                     8.0                      0.528127                  2.133174                    17.0                      0.520453                  2.098756                    26.0 severe_risk_broad_caution  phase2_noop_c50_r50 regime_severe_risk_broad_caution             50          50     False                       False         0.559627
validation    all          breadth_sensitive__phase2_noop_c50_r50          score_breadth_sensitive_phase2_noop_c50_r50         209      30877     0.057987    0.552061    0.541481    0.574777                      0.532687                  2.155502                     8.0                      0.528127                  2.133174                    17.0                      0.520453                  2.098756                    26.0         breadth_sensitive  phase2_noop_c50_r50         regime_breadth_sensitive             50          50     False                       False         0.559627
validation    all  balanced_drawdown_breadth__phase2_noop_c50_r50  score_balanced_drawdown_breadth_phase2_noop_c50_r50         209      30877     0.057987    0.552061    0.541481    0.574777                      0.532687                  2.155502                     8.0                      0.528127                  2.133174                    17.0                      0.520453                  2.098756                    26.0 balanced_drawdown_breadth  phase2_noop_c50_r50 regime_balanced_drawdown_breadth             50          50     False                       False         0.559627
```

## 7. independent_test 最终对照

```text
           split regime                       method                                         score_column  date_count  row_count  rank_ic_10d  ndcg_at_10  ndcg_at_30  ndcg_at_50  top10_future_excess_rank_10d  top10_mean_relevance_10d  top10_median_qlib_rank  top30_future_excess_rank_10d  top30_mean_relevance_10d  top30_median_qlib_rank  top50_future_excess_rank_10d  top50_mean_relevance_10d  top50_median_qlib_rank
independent_test    all       qlib_rank_rotate_top50                                       qlib_score_raw         209      31071     0.026642    0.543544    0.537373    0.565427                      0.535675                  2.185646                     6.0                      0.526614                  2.140351                    16.0                      0.513406                  2.077512                    26.0
independent_test    all  phase1c_qlib_preserving_ltr             score_head10_all_l31_alpha0.7_top50_only         209      31071     0.027360    0.559035    0.541729    0.567592                      0.550175                  2.258852                     8.0                      0.527890                  2.149761                    16.0                      0.513406                  2.077512                    26.0
independent_test    all             phase2_noop_gate                               phase2_noop_gate_score         209      31071     0.027360    0.559035    0.541729    0.567592                      0.550175                  2.258852                     8.0                      0.527890                  2.149761                    16.0                      0.513406                  2.077512                    26.0
independent_test    all phase2b_repaired_regime_gate score_balanced_drawdown_breadth_caution_only_c40_r50         209      31071     0.027755    0.559035    0.542685    0.567752                      0.550175                  2.258852                     8.0                      0.528888                  2.154705                    16.0                      0.513406                  2.077512                    26.0
```

## 8. selected gate 分状态指标

```text
           split   regime                       method                                         score_column  date_count  row_count  rank_ic_10d  ndcg_at_10  ndcg_at_30  ndcg_at_50  top10_future_excess_rank_10d  top10_mean_relevance_10d  top10_median_qlib_rank  top30_future_excess_rank_10d  top30_mean_relevance_10d  top30_median_qlib_rank  top50_future_excess_rank_10d  top50_mean_relevance_10d  top50_median_qlib_rank             definition_id
independent_test   normal       qlib_rank_rotate_top50                                       qlib_score_raw         142      21051     0.037072    0.565069    0.549891    0.574821                      0.549773                  2.254225                     6.0                      0.533346                  2.170423                    16.0                      0.517125                  2.093239                    26.0 balanced_drawdown_breadth
independent_test   normal  phase1c_qlib_preserving_ltr             score_head10_all_l31_alpha0.7_top50_only         142      21051     0.037801    0.570488    0.550423    0.574571                      0.559850                  2.304225                     7.0                      0.533655                  2.176291                    16.0                      0.517125                  2.093239                    26.0 balanced_drawdown_breadth
independent_test   normal             phase2_noop_gate                               phase2_noop_gate_score         142      21051     0.037801    0.570488    0.550423    0.574571                      0.559850                  2.304225                     7.0                      0.533655                  2.176291                    16.0                      0.517125                  2.093239                    26.0 balanced_drawdown_breadth
independent_test   normal phase2b_repaired_regime_gate score_balanced_drawdown_breadth_caution_only_c40_r50         142      21051     0.037801    0.570488    0.550423    0.574571                      0.559850                  2.304225                     7.0                      0.533655                  2.176291                    16.0                      0.517125                  2.093239                    26.0 balanced_drawdown_breadth
independent_test  caution       qlib_rank_rotate_top50                                       qlib_score_raw          52       7775     0.001611    0.502914    0.510695    0.544198                      0.498998                  2.021154                     6.0                      0.507525                  2.055769                    16.0                      0.501831                  2.025385                    26.0 balanced_drawdown_breadth
independent_test  caution  phase1c_qlib_preserving_ltr             score_head10_all_l31_alpha0.7_top50_only          52       7775    -0.000209    0.530038    0.513096    0.547120                      0.525254                  2.138462                     9.0                      0.504832                  2.044231                    17.0                      0.501831                  2.025385                    26.0 balanced_drawdown_breadth
independent_test  caution             phase2_noop_gate                               phase2_noop_gate_score          52       7775    -0.000209    0.530038    0.513096    0.547120                      0.525254                  2.138462                     9.0                      0.504832                  2.044231                    17.0                      0.501831                  2.025385                    26.0 balanced_drawdown_breadth
independent_test  caution phase2b_repaired_regime_gate score_balanced_drawdown_breadth_caution_only_c40_r50          52       7775     0.001379    0.530038    0.516937    0.547759                      0.525254                  2.138462                     9.0                      0.508845                  2.064103                    16.0                      0.501831                  2.025385                    26.0 balanced_drawdown_breadth
independent_test risk_off       qlib_rank_rotate_top50                                       qlib_score_raw          15       2245     0.014679    0.480616    0.511355    0.550097                      0.529356                  2.106667                     6.0                      0.529059                  2.148889                    16.0                      0.518329                  2.109333                    26.0 balanced_drawdown_breadth
independent_test risk_off  phase1c_qlib_preserving_ltr             score_head10_all_l31_alpha0.7_top50_only          15       2245     0.024086    0.551137    0.558694    0.572503                      0.544978                  2.246667                    12.0                      0.553244                  2.264444                    17.0                      0.518329                  2.109333                    26.0 balanced_drawdown_breadth
independent_test risk_off             phase2_noop_gate                               phase2_noop_gate_score          15       2245     0.024086    0.551137    0.558694    0.572503                      0.544978                  2.246667                    12.0                      0.553244                  2.264444                    17.0                      0.518329                  2.109333                    26.0 balanced_drawdown_breadth
independent_test risk_off phase2b_repaired_regime_gate score_balanced_drawdown_breadth_caution_only_c40_r50          15       2245     0.024086    0.551137    0.558694    0.572503                      0.544978                  2.246667                    12.0                      0.553244                  2.264444                    17.0                      0.518329                  2.109333                    26.0 balanced_drawdown_breadth
```

## 9. independent_test 分年度结果

```text
           split regime                       method                                         score_column  date_count  row_count  rank_ic_10d  ndcg_at_10  ndcg_at_30  ndcg_at_50  top10_future_excess_rank_10d  top10_mean_relevance_10d  top10_median_qlib_rank  top30_future_excess_rank_10d  top30_mean_relevance_10d  top30_median_qlib_rank  top50_future_excess_rank_10d  top50_mean_relevance_10d  top50_median_qlib_rank  year
independent_test    all       qlib_rank_rotate_top50                                       qlib_score_raw         130      19249     0.020326    0.550532    0.536989    0.563409                      0.542003                  2.220000                     6.0                      0.524523                  2.127179                    16.0                      0.510394                  2.057692                    26.0  2025
independent_test    all  phase1c_qlib_preserving_ltr             score_head10_all_l31_alpha0.7_top50_only         130      19249     0.021492    0.554963    0.537513    0.563090                      0.551271                  2.263077                     7.0                      0.525292                  2.134615                    16.0                      0.510394                  2.057692                    26.0  2025
independent_test    all             phase2_noop_gate                               phase2_noop_gate_score         130      19249     0.021492    0.554963    0.537513    0.563090                      0.551271                  2.263077                     7.0                      0.525292                  2.134615                    16.0                      0.510394                  2.057692                    26.0  2025
independent_test    all phase2b_repaired_regime_gate score_balanced_drawdown_breadth_caution_only_c40_r50         130      19249     0.021974    0.554963    0.538603    0.563258                      0.551271                  2.263077                     7.0                      0.526429                  2.140513                    16.0                      0.510394                  2.057692                    26.0  2025
independent_test    all       qlib_rank_rotate_top50                                       qlib_score_raw          79      11822     0.037035    0.532044    0.538006    0.568750                      0.525262                  2.129114                     5.5                      0.530055                  2.162025                    15.5                      0.518364                  2.110127                    26.0  2026
independent_test    all  phase1c_qlib_preserving_ltr             score_head10_all_l31_alpha0.7_top50_only          79      11822     0.037016    0.565736    0.548667    0.575001                      0.548371                  2.251899                     9.0                      0.532165                  2.174684                    17.0                      0.518364                  2.110127                    26.0  2026
independent_test    all             phase2_noop_gate                               phase2_noop_gate_score          79      11822     0.037016    0.565736    0.548667    0.575001                      0.548371                  2.251899                     9.0                      0.532165                  2.174684                    17.0                      0.518364                  2.110127                    26.0  2026
independent_test    all phase2b_repaired_regime_gate score_balanced_drawdown_breadth_caution_only_c40_r50          79      11822     0.037269    0.565736    0.549403    0.575146                      0.548371                  2.251899                     9.0                      0.532935                  2.178059                    16.0                      0.518364                  2.110127                    26.0  2026
```

## 10. Gate 结论

- 推荐 gate：`stop_regime_gating_insufficient_evidence`。
- 原因：Phase2B non-noop regime gate did not stably preserve Phase1C core TopK quality or did not provide enough robust conservative-filtering evidence.
- 条件：`{'selected_gate_non_noop': True, 'validation_did_not_use_independent_test': True, 'independent_test_core_topk_not_lower_than_phase1c': True, 'caution_or_risk_off_clear_conservative_effect': True, 'not_single_year_only': True, 'not_single_regime_only': False, 'selected_validation_candidate': {'definition_id': 'balanced_drawdown_breadth', 'gate_id': 'caution_only_c40_r50', 'score_column': 'score_balanced_drawdown_breadth_caution_only_c40_r50', 'selection_score': 0.5724836012215719, 'validation_core_floor_passed': True}, 'independent_conservative_effect': {'passed': True, 'details': [{'regime': 'caution', 'has_rows': True, 'date_count': 52, 'base_top30_median_qlib_rank': 17.0, 'gated_top30_median_qlib_rank': 16.0, 'base_top50_median_qlib_rank': 26.0, 'gated_top50_median_qlib_rank': 26.0, 'top30_changed_ratio': 0.08910256410256406, 'strictly_more_conservative_top30': True, 'top30_future_excess_delta': 0.00401283485343884}, {'regime': 'risk_off', 'has_rows': True, 'date_count': 15, 'base_top30_median_qlib_rank': 17.0, 'gated_top30_median_qlib_rank': 17.0, 'base_top50_median_qlib_rank': 26.0, 'gated_top50_median_qlib_rank': 26.0, 'top30_changed_ratio': 0.0, 'strictly_more_conservative_top30': False, 'top30_future_excess_delta': 0.0}]}}`。

## 11. 验证内容与结果

- `python -m py_compile scripts/repair_tw_ltr_phase2b_regime_gating.py`：通过。
- `python scripts/repair_tw_ltr_phase2b_regime_gating.py`：通过。
- validation selection 没有使用 independent_test 反选参数。
- 输出产物齐全。

## 12. 风险 / 异常 / 未解决问题

- risk_off 在 independent_test 中仍可能是小样本状态，审查者需要重点看分状态 date_count。
- 若推荐 gate 不是 `request_phase3_turnover_layer_work`，不得进入 Phase3。
- 本轮只证明或否定 Stage 3 gating，不报告组合净值、换手、动作次数或成本。

## 13. 需要审查者重点检查的点

- regime definition 是否只使用 5 个白名单字段。
- selected gate 是否非 no-op。
- validation selection score 是否没有读取 independent_test。
- independent_test 上是否真的不低于 Phase1C 核心 TopK 质量。
- caution / risk_off 下的保守过滤是否足够清晰且不是单一偶然窗口。

## 14. 禁止事项遵守情况

本轮未新增数据源，未新增白名单外特征，未引入 `trend_score` 或 forbidden features，未联网，未 provider refresh/publish，未 accepted latest switching，未改 frontend / API / monitor / database，未做 turnover portfolio layer，未接 broker / quick-trade / orders / target position / target weight，未输出买入、卖出、持有、仓位、收益承诺、上涨概率或胜率语义。
