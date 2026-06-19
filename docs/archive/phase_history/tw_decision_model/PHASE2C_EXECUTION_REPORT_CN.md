# Phase 2C Entry Model v1 归档失败执行报告

## 1. 执行摘要

- 执行日期：`2026-06-10T16:00:52+00:00`
- 执行范围：Phase 2C 最后一次 gate confirmation / closeout。
- 评估候选：`qlib + technical / ensemble_fixed_trainval`、`qlib + technical / regression`。
- 唯一准入基线：`baseline_qlib_rank`。
- 是否新增 feature：否。
- 是否新增数据源、FinMind、2024 回填或数据补齐：否。
- 是否训练新模型、Exit Model、LambdaRank：否。
- 是否做组合回放、前端/API/产品化：否。
- 是否触碰 provider refresh/publish/accepted latest switching：否。
- 是否触碰 broker/orders/quick-trade/target position/monitor config/alerts：否。

## 2. 固定判断口径

- 覆盖区间：`main/test`、`main/forward`、`sensitivity/test`、`sensitivity/forward`。
- 通过条件：同一个候选四个区间的 top5/top10 delta 均非负，且 RankIC、NDCG@10、precision@5 不出现负 delta。
- 容忍区间：未使用。
- 不以单一区间或 overall 均值替代逐区间判断。

## 3. Gate Confirmation

| feature_group | candidate_model | split_name | split_part | top5_delta | top10_delta | rankic_delta | ndcg10_delta | precision5_delta | interval_pass | candidate_pass_phase3_gate |
|---|---|---|---|---|---|---|---|---|---|---|
| qlib + technical | ensemble_fixed_trainval | main | test | 0.008927 | 0.008261 | 0.028015 | 0.010787 | 0.010744 | True | False |
| qlib + technical | ensemble_fixed_trainval | main | forward | -0.006036 | 0.005784 | -0.005081 | -0.007198 | -0.037681 | False | False |
| qlib + technical | ensemble_fixed_trainval | sensitivity | test | 0.008761 | 0.003815 | 0.022141 | 0.003233 | -0.014286 | False | False |
| qlib + technical | ensemble_fixed_trainval | sensitivity | forward | 0.000566 | -0.000613 | 0.052109 | -0.008931 | -0.028986 | False | False |
| qlib + technical | regression | main | test | -0.009746 | -0.001818 | 0.021156 | -0.006768 | -0.011570 | False | False |
| qlib + technical | regression | main | forward | -0.007178 | -0.018728 | 0.036787 | -0.032325 | -0.028986 | False | False |
| qlib + technical | regression | sensitivity | test | 0.010464 | 0.001680 | 0.031202 | 0.010110 | 0.001587 | True | False |
| qlib + technical | regression | sensitivity | forward | 0.007427 | -0.003733 | 0.036439 | -0.006775 | -0.005797 | False | False |

## 4. Candidate Comparison

| feature_group | candidate_model | split_name | split_part | candidate_top5_excess_return | baseline_top5_excess_return | top5_delta | candidate_top10_excess_return | baseline_top10_excess_return | top10_delta |
|---|---|---|---|---|---|---|---|---|---|
| qlib + technical | ensemble_fixed_trainval | main | test | 0.053189 | 0.044263 | 0.008927 | 0.049502 | 0.041242 | 0.008261 |
| qlib + technical | regression | main | test | 0.034517 | 0.044263 | -0.009746 | 0.039423 | 0.041242 | -0.001818 |
| qlib + technical | ensemble_fixed_trainval | main | forward | 0.072351 | 0.078387 | -0.006036 | 0.091981 | 0.086197 | 0.005784 |
| qlib + technical | regression | main | forward | 0.071209 | 0.078387 | -0.007178 | 0.067469 | 0.086197 | -0.018728 |
| qlib + technical | ensemble_fixed_trainval | sensitivity | test | 0.085215 | 0.076455 | 0.008761 | 0.074648 | 0.070832 | 0.003815 |
| qlib + technical | regression | sensitivity | test | 0.086919 | 0.076455 | 0.010464 | 0.072512 | 0.070832 | 0.001680 |
| qlib + technical | ensemble_fixed_trainval | sensitivity | forward | 0.078953 | 0.078387 | 0.000566 | 0.085584 | 0.086197 | -0.000613 |
| qlib + technical | regression | sensitivity | forward | 0.085814 | 0.078387 | 0.007427 | 0.082464 | 0.086197 | -0.003733 |

## 5. Failure Attribution

| feature_group | candidate_model | split_name | split_part | failed_checks | top5_delta | top10_delta | rankic_delta | ndcg10_delta | precision5_delta |
|---|---|---|---|---|---|---|---|---|---|
| qlib + technical | ensemble_fixed_trainval | main | forward | top5_delta_negative,rankic_delta_negative,ndcg10_delta_negative,precision5_delta_negative | -0.006036 | 0.005784 | -0.005081 | -0.007198 | -0.037681 |
| qlib + technical | ensemble_fixed_trainval | sensitivity | test | precision5_delta_negative | 0.008761 | 0.003815 | 0.022141 | 0.003233 | -0.014286 |
| qlib + technical | ensemble_fixed_trainval | sensitivity | forward | top10_delta_negative,ndcg10_delta_negative,precision5_delta_negative | 0.000566 | -0.000613 | 0.052109 | -0.008931 | -0.028986 |
| qlib + technical | regression | main | test | top5_delta_negative,top10_delta_negative,ndcg10_delta_negative,precision5_delta_negative | -0.009746 | -0.001818 | 0.021156 | -0.006768 | -0.011570 |
| qlib + technical | regression | main | forward | top5_delta_negative,top10_delta_negative,ndcg10_delta_negative,precision5_delta_negative | -0.007178 | -0.018728 | 0.036787 | -0.032325 | -0.028986 |
| qlib + technical | regression | sensitivity | forward | top10_delta_negative,ndcg10_delta_negative,precision5_delta_negative | 0.007427 | -0.003733 | 0.036439 | -0.006775 | -0.005797 |

## 6. 最终二选一结论

- `pass_phase3_gate=false`
- `archive_entry_model_v1_failed=true`
- Phase 3 准入：否。
- Phase 2D：不继续。
- 后续若要重启 Entry 方向，只能由用户另行确认新研究方向。

## 7. 生成文件

- `data_tw/experiments/decision_model/phase2_entry_model_v1/phase2c_gate_confirmation.csv`
- `data_tw/experiments/decision_model/phase2_entry_model_v1/phase2c_candidate_comparison.csv`
- `data_tw/experiments/decision_model/phase2_entry_model_v1/phase2c_failure_attribution.csv`
- `docs/tw_decision_model/PHASE2C_EXECUTION_REPORT_CN.md`
