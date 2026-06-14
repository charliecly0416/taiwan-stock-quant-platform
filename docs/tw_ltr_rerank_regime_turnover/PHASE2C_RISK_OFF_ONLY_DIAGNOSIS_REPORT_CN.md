# Phase 2C 执行报告：Risk-off-only 最终诊断

生成时间：2026-06-13T17:58:43+00:00

## 1. 本轮目标

只回答：为什么 Phase2B selected gate 在 `risk_off` 下没有形成有效保守过滤。本轮不是 Phase3，不进入 turnover-controlled portfolio layer。

## 2. 实际完成内容

- 新增只读诊断脚本：`scripts/diagnose_tw_ltr_phase2c_risk_off_only.py`。
- 复用 Phase2B aggregate 产物与 Phase1 样本的 regime 白名单字段。
- 未重新训练 LTR，未重建 Phase1C 行级 score。
- 对 Phase2B selected definition 的 `risk_off` 分布、已有 risk_scope 诊断、年度样本分布做汇总。

## 3. 改动文件清单

- `scripts/diagnose_tw_ltr_phase2c_risk_off_only.py`
- `docs/tw_ltr_rerank_regime_turnover/PHASE2C_RISK_OFF_ONLY_DIAGNOSIS_REPORT_CN.md`

## 4. 新增产物清单

- `data_tw/experiments/ltr_rerank_regime_turnover/phase2c_risk_off_diagnosis/phase2c_risk_off_distribution.csv`
- `data_tw/experiments/ltr_rerank_regime_turnover/phase2c_risk_off_diagnosis/phase2c_risk_off_scope_sensitivity.csv`
- `data_tw/experiments/ltr_rerank_regime_turnover/phase2c_risk_off_diagnosis/phase2c_risk_off_by_year.csv`
- `data_tw/experiments/ltr_rerank_regime_turnover/phase2c_risk_off_diagnosis/phase2c_risk_off_gate_diagnosis.json`

## 5. risk_off 样本分布

```text
            definition_id            split   regime  date_count  row_count  mean_TWII_ret20  mean_TWII_ret60  mean_market_drawdown60  mean_market_volatility20  mean_market_breadth20
balanced_drawdown_breadth independent_test risk_off          15       2245        -0.042718         0.149800               -0.070376                  0.019301               0.408463
balanced_drawdown_breadth            train risk_off         255      36716        -0.031694        -0.035793               -0.085075                  0.011533               0.326412
balanced_drawdown_breadth       validation risk_off         113      16614        -0.021024        -0.047490               -0.090244                  0.018277               0.414895
        breadth_sensitive independent_test risk_off          22       3287        -0.024373         0.147523               -0.058763                  0.017256               0.412624
        breadth_sensitive            train risk_off         282      40612        -0.028802        -0.030791               -0.080537                  0.011254               0.339192
        breadth_sensitive       validation risk_off         126      18547        -0.017426        -0.040414               -0.084609                  0.017483               0.418721
          phase2_original independent_test risk_off           7       1045        -0.043294         0.116288               -0.071054                  0.015369               0.287081
          phase2_original            train risk_off         215      30961        -0.040082        -0.044364               -0.092048                  0.012091               0.298239
          phase2_original       validation risk_off          91      13366        -0.032798        -0.053378               -0.097928                  0.019943               0.382216
severe_risk_broad_caution independent_test risk_off           3        447        -0.045100         0.096202               -0.064520                  0.013038               0.239374
severe_risk_broad_caution            train risk_off         170      24442        -0.049232        -0.052086               -0.099548                  0.012535               0.256215
severe_risk_broad_caution       validation risk_off          67       9822        -0.051601        -0.063150               -0.112626                  0.022942               0.346599
```

## 6. Phase2B selected definition 下 risk_off 指标

```text
           split   regime                       method                                         score_column  date_count  row_count  rank_ic_10d  ndcg_at_10  ndcg_at_30  ndcg_at_50  top10_future_excess_rank_10d  top10_mean_relevance_10d  top10_median_qlib_rank  top30_future_excess_rank_10d  top30_mean_relevance_10d  top30_median_qlib_rank  top50_future_excess_rank_10d  top50_mean_relevance_10d  top50_median_qlib_rank             definition_id
independent_test risk_off       qlib_rank_rotate_top50                                       qlib_score_raw          15       2245     0.014679    0.480616    0.511355    0.550097                      0.529356                  2.106667                     6.0                      0.529059                  2.148889                    16.0                      0.518329                  2.109333                    26.0 balanced_drawdown_breadth
independent_test risk_off  phase1c_qlib_preserving_ltr             score_head10_all_l31_alpha0.7_top50_only          15       2245     0.024086    0.551137    0.558694    0.572503                      0.544978                  2.246667                    12.0                      0.553244                  2.264444                    17.0                      0.518329                  2.109333                    26.0 balanced_drawdown_breadth
independent_test risk_off             phase2_noop_gate                               phase2_noop_gate_score          15       2245     0.024086    0.551137    0.558694    0.572503                      0.544978                  2.246667                    12.0                      0.553244                  2.264444                    17.0                      0.518329                  2.109333                    26.0 balanced_drawdown_breadth
independent_test risk_off phase2b_repaired_regime_gate score_balanced_drawdown_breadth_caution_only_c40_r50          15       2245     0.024086    0.551137    0.558694    0.572503                      0.544978                  2.246667                    12.0                      0.553244                  2.264444                    17.0                      0.518329                  2.109333                    26.0 balanced_drawdown_breadth
```

## 7. risk_scope sensitivity

```text
            definition_id            split  risk_scope  available                                          method ndcg_at_30 top30_future_excess_rank_10d risk_off_top30_median_qlib_rank risk_off_changed_ratio risk_off_top30_future_excess_delta                                                                                                   diagnosis_note
balanced_drawdown_breadth       validation          50       True balanced_drawdown_breadth__caution_only_c40_r50    0.54177                     0.528169                            17.0                    0.0                                0.0                                    existing Phase2B aggregate diagnostic reused; no Phase2C parameter selection.
balanced_drawdown_breadth independent_test          50       True  balanced_drawdown_breadth__phase2_noop_c50_r50   0.541729                      0.52789                            17.0                    0.0                                0.0                                    existing Phase2B aggregate diagnostic reused; no Phase2C parameter selection.
balanced_drawdown_breadth       validation          45      False   not_available_without_row_level_phase1c_score       <NA>                         <NA>                            <NA>                   <NA>                               <NA> Phase2B did not materialize this exact scope; Phase2C forbids retraining/reconstructing row-level Phase1C score.
balanced_drawdown_breadth independent_test          45      False   not_available_without_row_level_phase1c_score       <NA>                         <NA>                            <NA>                   <NA>                               <NA> Phase2B did not materialize this exact scope; Phase2C forbids retraining/reconstructing row-level Phase1C score.
balanced_drawdown_breadth       validation          40       True         balanced_drawdown_breadth__mild_c45_r40   0.540481                      0.52692                            17.0               0.082301                          -0.002202                                    existing Phase2B aggregate diagnostic reused; no Phase2C parameter selection.
balanced_drawdown_breadth independent_test          40       True         balanced_drawdown_breadth__mild_c45_r40   0.541328                     0.527309                            16.0               0.106667                          -0.005785                                    existing Phase2B aggregate diagnostic reused; no Phase2C parameter selection.
balanced_drawdown_breadth       validation          35      False   not_available_without_row_level_phase1c_score       <NA>                         <NA>                            <NA>                   <NA>                               <NA> Phase2B did not materialize this exact scope; Phase2C forbids retraining/reconstructing row-level Phase1C score.
balanced_drawdown_breadth independent_test          35      False   not_available_without_row_level_phase1c_score       <NA>                         <NA>                            <NA>                   <NA>                               <NA> Phase2B did not materialize this exact scope; Phase2C forbids retraining/reconstructing row-level Phase1C score.
balanced_drawdown_breadth       validation          30       True    balanced_drawdown_breadth__risk_only_c50_r30   0.536592                     0.522074                            16.0                0.20236                          -0.011196                                    existing Phase2B aggregate diagnostic reused; no Phase2C parameter selection.
balanced_drawdown_breadth independent_test          30       True    balanced_drawdown_breadth__risk_only_c50_r30   0.540226                     0.526154                            16.0               0.224444                          -0.024185                                    existing Phase2B aggregate diagnostic reused; no Phase2C parameter selection.
balanced_drawdown_breadth       validation          20       True       balanced_drawdown_breadth__strict_c35_r20   0.536481                     0.522108                            16.0                0.20236                          -0.011196                                    existing Phase2B aggregate diagnostic reused; no Phase2C parameter selection.
balanced_drawdown_breadth independent_test          20       True       balanced_drawdown_breadth__strict_c35_r20   0.540894                     0.527209                            16.0               0.224444                          -0.024185                                    existing Phase2B aggregate diagnostic reused; no Phase2C parameter selection.
```

可用 scope 说明：

```text
            definition_id            split  risk_scope  available                                          method ndcg_at_30 top30_future_excess_rank_10d risk_off_top30_median_qlib_rank risk_off_changed_ratio risk_off_top30_future_excess_delta                                                                diagnosis_note
balanced_drawdown_breadth       validation          50       True balanced_drawdown_breadth__caution_only_c40_r50    0.54177                     0.528169                            17.0                    0.0                                0.0 existing Phase2B aggregate diagnostic reused; no Phase2C parameter selection.
balanced_drawdown_breadth independent_test          50       True  balanced_drawdown_breadth__phase2_noop_c50_r50   0.541729                      0.52789                            17.0                    0.0                                0.0 existing Phase2B aggregate diagnostic reused; no Phase2C parameter selection.
balanced_drawdown_breadth       validation          40       True         balanced_drawdown_breadth__mild_c45_r40   0.540481                      0.52692                            17.0               0.082301                          -0.002202 existing Phase2B aggregate diagnostic reused; no Phase2C parameter selection.
balanced_drawdown_breadth independent_test          40       True         balanced_drawdown_breadth__mild_c45_r40   0.541328                     0.527309                            16.0               0.106667                          -0.005785 existing Phase2B aggregate diagnostic reused; no Phase2C parameter selection.
balanced_drawdown_breadth       validation          30       True    balanced_drawdown_breadth__risk_only_c50_r30   0.536592                     0.522074                            16.0                0.20236                          -0.011196 existing Phase2B aggregate diagnostic reused; no Phase2C parameter selection.
balanced_drawdown_breadth independent_test          30       True    balanced_drawdown_breadth__risk_only_c50_r30   0.540226                     0.526154                            16.0               0.224444                          -0.024185 existing Phase2B aggregate diagnostic reused; no Phase2C parameter selection.
balanced_drawdown_breadth       validation          20       True       balanced_drawdown_breadth__strict_c35_r20   0.536481                     0.522108                            16.0                0.20236                          -0.011196 existing Phase2B aggregate diagnostic reused; no Phase2C parameter selection.
balanced_drawdown_breadth independent_test          20       True       balanced_drawdown_breadth__strict_c35_r20   0.540894                     0.527209                            16.0               0.224444                          -0.024185 existing Phase2B aggregate diagnostic reused; no Phase2C parameter selection.
```

不可用 scope 说明：

```text
            definition_id            split  risk_scope  available                                        method ndcg_at_30 top30_future_excess_rank_10d risk_off_top30_median_qlib_rank risk_off_changed_ratio risk_off_top30_future_excess_delta                                                                                                   diagnosis_note
balanced_drawdown_breadth       validation          45      False not_available_without_row_level_phase1c_score       <NA>                         <NA>                            <NA>                   <NA>                               <NA> Phase2B did not materialize this exact scope; Phase2C forbids retraining/reconstructing row-level Phase1C score.
balanced_drawdown_breadth independent_test          45      False not_available_without_row_level_phase1c_score       <NA>                         <NA>                            <NA>                   <NA>                               <NA> Phase2B did not materialize this exact scope; Phase2C forbids retraining/reconstructing row-level Phase1C score.
balanced_drawdown_breadth       validation          35      False not_available_without_row_level_phase1c_score       <NA>                         <NA>                            <NA>                   <NA>                               <NA> Phase2B did not materialize this exact scope; Phase2C forbids retraining/reconstructing row-level Phase1C score.
balanced_drawdown_breadth independent_test          35      False not_available_without_row_level_phase1c_score       <NA>                         <NA>                            <NA>                   <NA>                               <NA> Phase2B did not materialize this exact scope; Phase2C forbids retraining/reconstructing row-level Phase1C score.
```

## 8. risk_off by year

```text
           split  year   regime  date_count  row_count  metrics_available                                                                                              diagnosis_note
independent_test  2025 risk_off           5        745              False Only distribution is available without saved row-level Phase1C score; no LTR retraining allowed in Phase2C.
independent_test  2026 risk_off          10       1500              False Only distribution is available without saved row-level Phase1C score; no LTR retraining allowed in Phase2C.
           train  2022 risk_off         173      24906              False Only distribution is available without saved row-level Phase1C score; no LTR retraining allowed in Phase2C.
           train  2023 risk_off          47       6916              False Only distribution is available without saved row-level Phase1C score; no LTR retraining allowed in Phase2C.
           train  2024 risk_off          35       4894              False Only distribution is available without saved row-level Phase1C score; no LTR retraining allowed in Phase2C.
      validation  2024 risk_off          41       6075              False Only distribution is available without saved row-level Phase1C score; no LTR retraining allowed in Phase2C.
      validation  2025 risk_off          72      10539              False Only distribution is available without saved row-level Phase1C score; no LTR retraining allowed in Phase2C.
```

## 9. validation vs independent_test 是否一致

Phase2B 已有 aggregate 显示：对 selected definition，风险收缩类 gate 在 validation 上会形成 risk_off 过滤，但通常伴随整体 TopK 指标下降；在 independent_test 上也能形成 risk_off 过滤，但 Top30 future excess delta 为负。Phase2B 最终选择的 `caution_only_c40_r50` 在 validation 和 independent_test 都没有 risk_off 过滤变化。

## 10. 最终诊断结论

最终 gate：`risk_off_gating_not_supported_final`。

诊断结论：Risk-off gating is not supported as a final Stage 3 gate: the selected Phase2B gate has no risk_off effect, stricter existing risk scopes hurt risk_off Top30 future excess rank, risk_off samples are limited, and exact 45/35 checks require row-level Phase1C score that was not saved while Phase2C forbids retraining.

逐项回答：

1. 每个 regime definition 的 risk_off 分布已输出在 `phase2c_risk_off_distribution.csv`。
2. Phase2B selected definition 下 independent_test risk_off 为 15 dates / 2245 rows，样本偏少，但不是唯一原因。
3. Phase2B selected definition 的 risk_off 中，Phase1C 相比 qlib 的 NDCG@30、Top30 future excess rank、TopK relevance 已经更高，说明 Phase1C 在该子样本内已有较强过滤。
4. 已有 scope 诊断显示：risk_scope=40/30/20 会改变 risk_off Top30，但 risk_off Top30 future excess delta 为负；risk_scope=50 无变化。
5. 未发现 validation 与 independent_test 同时支持“不伤害 Phase1C 且形成 risk_off 过滤”的 scope。45/35 需要行级 score 才能精确补算，当前无行级 score 且 Phase2C 禁止重训。
6. 失败原因是组合性的：risk_off 样本偏少、Phase1C 已较强、进一步收缩会牺牲 TopK，且现有产物无法支持更细 scope 的只读验证。

## 11. 验证命令与结果

- `python -m py_compile scripts/diagnose_tw_ltr_phase2c_risk_off_only.py`：通过。
- `python scripts/diagnose_tw_ltr_phase2c_risk_off_only.py`：通过。

## 12. 禁止事项遵守情况

本轮未进入 Phase3，未做 turnover portfolio layer，未做组合净值、动作次数、换手、成本回放，未新增数据源，未联网，未 provider refresh/publish，未 accepted latest switching，未改 frontend/API/monitor/database，未重新训练 LTR，未引入 `trend_score` 或 forbidden features，未新增白名单外 regime 特征，未输出买入、卖出、持有、仓位、target position/target weight、收益承诺、胜率或上涨概率语义。

## 13. 需要审查者重点检查的点

- 本轮是否严格停留在只读诊断。
- 45/35 scope 缺失是否应接受为 Phase2C 禁止重训条件下的合理限制。
- risk_off failure 是否可正式作为 Stage 3 证据不足收尾。
