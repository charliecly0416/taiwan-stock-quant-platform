# Phase 2B Entry Model v1 诊断报告

## 1. 结论

- 原 Phase 2 失败结论保留：不得进入 Phase 3。
- Phase 2B 修复了 ensemble 评估口径：新增 `train+validation fitted minmax` 与 `same-asof minmax`，均不使用 test/forward 全区间分布。
- Phase 2B 是否建议进入 Phase 3：`False`。本次未提出进入 Phase 3 建议，等待审查者复核。

## 2. Gate Delta vs qlib rank

| split_name | split_part | model | top5_delta | top10_delta | rankic_delta | ndcg10_delta | precision5_delta |
|---|---|---|---|---|---|---|---|
| main | forward | binary | -0.089455 | -0.061237 | -0.165976 | -0.092261 | -0.257971 |
| main | forward | ensemble_fixed_same_asof | -0.061150 | -0.036793 | -0.087727 | -0.056862 | -0.162319 |
| main | forward | ensemble_fixed_trainval | -0.093653 | -0.064237 | -0.096839 | -0.086507 | -0.243478 |
| main | forward | ensemble_original | -0.037481 | -0.031008 | -0.083984 | -0.043444 | -0.121739 |
| main | forward | regression | 0.003147 | 0.016428 | 0.020866 | 0.015187 | -0.023188 |
| main | test | binary | -0.043229 | -0.030323 | -0.012061 | -0.040376 | -0.105785 |
| main | test | ensemble_fixed_same_asof | -0.017493 | -0.017215 | 0.007034 | -0.015281 | -0.056198 |
| main | test | ensemble_fixed_trainval | -0.030637 | -0.027667 | 0.003479 | -0.029221 | -0.076860 |
| main | test | ensemble_original | -0.029209 | -0.026805 | 0.004576 | -0.025619 | -0.071074 |
| main | test | regression | 0.002495 | 0.005862 | 0.011534 | 0.007005 | -0.037190 |
| sensitivity | forward | binary | 0.019948 | 0.012835 | 0.070190 | 0.014544 | 0.043478 |
| sensitivity | forward | ensemble_fixed_same_asof | 0.043405 | 0.012912 | 0.065523 | 0.022285 | 0.057971 |
| sensitivity | forward | ensemble_fixed_trainval | 0.040632 | 0.014407 | 0.067649 | 0.021097 | 0.052174 |
| sensitivity | forward | ensemble_original | 0.043737 | 0.013443 | 0.071215 | 0.022090 | 0.060870 |
| sensitivity | forward | regression | 0.041712 | 0.013921 | 0.070658 | 0.022316 | 0.055072 |
| sensitivity | test | binary | -0.007291 | 0.000388 | 0.016301 | -0.007740 | -0.009524 |
| sensitivity | test | ensemble_fixed_same_asof | -0.014667 | -0.011887 | 0.051476 | -0.018386 | -0.025397 |
| sensitivity | test | ensemble_fixed_trainval | -0.015520 | -0.008970 | 0.049716 | -0.019420 | -0.036508 |
| sensitivity | test | ensemble_original | -0.017021 | -0.015915 | 0.051234 | -0.023162 | -0.033333 |
| sensitivity | test | regression | -0.019605 | -0.018637 | 0.060158 | -0.027667 | -0.014286 |

## 3. Ensemble Calibration Compare

| split_name | calibration_method | fit_parts | binary_min | binary_max | regression_min | regression_max | uses_test_forward_whole_period_distribution |
|---|---|---|---|---|---|---|---|
| main | trainval_fitted_minmax | train+validation | 0.391255 | 0.411184 | -0.958568 | 4.508479 | False |
| sensitivity | trainval_fitted_minmax | train+validation | 0.410729 | 0.431898 | -0.140076 | 4.980499 | False |
| main | same_asof_minmax | same asof candidates only |  |  |  |  | False |
| sensitivity | same_asof_minmax | same asof candidates only |  |  |  |  | False |

## 4. Feature Group Ablation

| feature_group | split_name | split_part | model | RankIC | NDCG@10 | precision@5 | top5_excess_return | top10_excess_return |
|---|---|---|---|---|---|---|---|---|
| qlib only | main | forward | regression | 0.081785 | 0.475519 | 0.582609 | 0.095430 | 0.090782 |
| qlib only | main | forward | ensemble_fixed_trainval | 0.071771 | 0.467206 | 0.628986 | 0.104851 | 0.081472 |
| qlib only | main | test | regression | 0.018635 | 0.438774 | 0.484298 | 0.030445 | 0.033390 |
| qlib only | main | test | ensemble_fixed_trainval | 0.017299 | 0.436325 | 0.467769 | 0.029486 | 0.034085 |
| qlib + technical | main | forward | regression | 0.117483 | 0.435702 | 0.536232 | 0.071209 | 0.067469 |
| qlib + technical | main | forward | ensemble_fixed_trainval | 0.075615 | 0.460829 | 0.527536 | 0.072351 | 0.091981 |
| qlib + technical | main | test | regression | 0.044535 | 0.447155 | 0.485124 | 0.034517 | 0.039423 |
| qlib + technical | main | test | ensemble_fixed_trainval | 0.051393 | 0.464710 | 0.507438 | 0.053189 | 0.049502 |
| qlib + liquidity | main | forward | regression | 0.007888 | 0.474057 | 0.573913 | 0.087628 | 0.105476 |
| qlib + liquidity | main | forward | ensemble_fixed_trainval | -0.019842 | 0.478666 | 0.582609 | 0.116746 | 0.097299 |
| qlib + liquidity | main | test | regression | 0.016968 | 0.451571 | 0.459504 | 0.038987 | 0.035838 |
| qlib + liquidity | main | test | ensemble_fixed_trainval | 0.010959 | 0.450533 | 0.494215 | 0.044933 | 0.036249 |
| qlib + market continuous | main | forward | regression | 0.072486 | 0.468027 | 0.565217 | 0.078387 | 0.086197 |
| qlib + market continuous | main | forward | ensemble_fixed_trainval | 0.041751 | 0.462164 | 0.553623 | 0.073923 | 0.079285 |
| qlib + market continuous | main | test | regression | -0.021051 | 0.447731 | 0.485950 | 0.039865 | 0.038932 |
| qlib + market continuous | main | test | ensemble_fixed_trainval | -0.006263 | 0.451794 | 0.473554 | 0.038131 | 0.040259 |
| qlib + technical + liquidity | main | forward | regression | 0.126936 | 0.458958 | 0.510145 | 0.067429 | 0.078502 |
| qlib + technical + liquidity | main | forward | ensemble_fixed_trainval | 0.074303 | 0.457778 | 0.527536 | 0.078879 | 0.077564 |
| qlib + technical + liquidity | main | test | regression | 0.026336 | 0.460945 | 0.481818 | 0.048279 | 0.048210 |
| qlib + technical + liquidity | main | test | ensemble_fixed_trainval | 0.013709 | 0.463394 | 0.489256 | 0.047552 | 0.048517 |
| all input features | main | forward | regression | 0.101562 | 0.483214 | 0.542029 | 0.081534 | 0.102625 |
| all input features | main | forward | ensemble_fixed_trainval | -0.016142 | 0.381520 | 0.321739 | -0.015266 | 0.021961 |
| all input features | main | test | regression | 0.034912 | 0.460928 | 0.459504 | 0.046758 | 0.047104 |
| all input features | main | test | ensemble_fixed_trainval | 0.026858 | 0.424703 | 0.419835 | 0.013625 | 0.013575 |
| qlib only | sensitivity | forward | regression | 0.085886 | 0.480226 | 0.617391 | 0.110689 | 0.103231 |
| qlib only | sensitivity | forward | ensemble_fixed_trainval | 0.081607 | 0.483183 | 0.634783 | 0.115337 | 0.103408 |
| qlib only | sensitivity | test | regression | 0.026081 | 0.423682 | 0.511111 | 0.060037 | 0.061440 |
| qlib only | sensitivity | test | ensemble_fixed_trainval | 0.019538 | 0.421952 | 0.498413 | 0.060625 | 0.062705 |
| qlib + technical | sensitivity | forward | regression | 0.117135 | 0.461252 | 0.559420 | 0.085814 | 0.082464 |
| qlib + technical | sensitivity | forward | ensemble_fixed_trainval | 0.132805 | 0.459096 | 0.536232 | 0.078953 | 0.085584 |
| qlib + technical | sensitivity | test | regression | 0.053414 | 0.454685 | 0.542857 | 0.086919 | 0.072512 |
| qlib + technical | sensitivity | test | ensemble_fixed_trainval | 0.044353 | 0.447808 | 0.526984 | 0.085215 | 0.074648 |
| qlib + liquidity | sensitivity | forward | regression | 0.058373 | 0.450536 | 0.553623 | 0.070113 | 0.067728 |
| qlib + liquidity | sensitivity | forward | ensemble_fixed_trainval | 0.027622 | 0.434607 | 0.559420 | 0.051385 | 0.057441 |
| qlib + liquidity | sensitivity | test | regression | 0.024934 | 0.406590 | 0.484127 | 0.053133 | 0.043177 |
| qlib + liquidity | sensitivity | test | ensemble_fixed_trainval | -0.010435 | 0.399797 | 0.465079 | 0.046634 | 0.037913 |
| qlib + market continuous | sensitivity | forward | regression | -0.039552 | 0.468027 | 0.565217 | 0.078387 | 0.086197 |
| qlib + market continuous | sensitivity | forward | ensemble_fixed_trainval | 0.063551 | 0.470080 | 0.559420 | 0.079213 | 0.089599 |
| qlib + market continuous | sensitivity | test | regression | -0.050203 | 0.425329 | 0.512698 | 0.059290 | 0.056082 |
| qlib + market continuous | sensitivity | test | ensemble_fixed_trainval | 0.015814 | 0.432220 | 0.523810 | 0.061447 | 0.057086 |
| qlib + technical + liquidity | sensitivity | forward | regression | 0.099826 | 0.431035 | 0.507246 | 0.036593 | 0.063912 |
| qlib + technical + liquidity | sensitivity | forward | ensemble_fixed_trainval | 0.142545 | 0.438007 | 0.536232 | 0.050576 | 0.073304 |
| qlib + technical + liquidity | sensitivity | test | regression | 0.078895 | 0.434450 | 0.500000 | 0.072718 | 0.064370 |
| qlib + technical + liquidity | sensitivity | test | ensemble_fixed_trainval | 0.051699 | 0.434170 | 0.503175 | 0.070523 | 0.068961 |
| all input features | sensitivity | forward | regression | 0.151354 | 0.490343 | 0.620290 | 0.120099 | 0.100118 |
| all input features | sensitivity | forward | ensemble_fixed_trainval | 0.148346 | 0.489124 | 0.617391 | 0.119019 | 0.100604 |
| all input features | sensitivity | test | regression | 0.082370 | 0.416908 | 0.526984 | 0.056850 | 0.052195 |
| all input features | sensitivity | test | ensemble_fixed_trainval | 0.071928 | 0.425154 | 0.504762 | 0.060935 | 0.061862 |

## 5. Binary Failure Diagnosis

| split_name | split_part | best_iteration | score_mean | label_positive_rate | calibration_error_mean_minus_label | auc | rankic | ndcg10 | precision5 |
|---|---|---|---|---|---|---|---|---|---|
| main | forward | 1 | 0.394748 | 0.508704 | -0.113956 | 0.464138 | -0.085280 | 0.375766 | 0.307246 |
| main | test | 1 | 0.397046 | 0.450181 | -0.053135 | 0.512983 | 0.011317 | 0.413547 | 0.390909 |
| main | train | 1 | 0.398908 | 0.398914 | -0.000006 | 0.679053 | 0.231054 | 0.599328 | 0.650407 |
| main | validation | 1 | 0.397132 | 0.452648 | -0.055516 | 0.468941 | -0.055211 | 0.450534 | 0.364017 |
| sensitivity | forward | 1 | 0.424931 | 0.508704 | -0.083773 | 0.573596 | 0.150887 | 0.482571 | 0.608696 |
| sensitivity | test | 1 | 0.421294 | 0.461246 | -0.039952 | 0.517872 | 0.038513 | 0.436835 | 0.531746 |
| sensitivity | train | 1 | 0.419399 | 0.419400 | -0.000002 | 0.631778 | 0.150250 | 0.593560 | 0.597526 |
| sensitivity | validation | 1 | 0.420109 | 0.438122 | -0.018014 | 0.450490 | 0.017842 | 0.482865 | 0.522414 |

## 6. Regression Robustness Diagnosis

### Overall

| split_name | split_part | top5_delta_vs_qlib_rank | top10_delta_vs_qlib_rank | rankic_regression | rankic_qlib_rank |
|---|---|---|---|---|---|
| main | test | 0.002495 | 0.005862 | 0.034912 | 0.023378 |
| main | forward | 0.003147 | 0.016428 | 0.101562 | 0.080696 |
| sensitivity | test | -0.019605 | -0.018637 | 0.082370 | 0.022212 |
| sensitivity | forward | 0.041712 | 0.013921 | 0.151354 | 0.080696 |

### Worst Concentrated Groups

| split_name | split_part | group_col | group_value | rows | top5_delta_vs_qlib_rank | top10_delta_vs_qlib_rank |
|---|---|---|---|---|---|---|
| sensitivity | test | month | 2025-09 | 2001 | -0.050451 | -0.090604 |
| sensitivity | forward | month | 2026-02 | 1089 | -0.041881 | -0.078917 |
| main | test | month | 2025-09 | 2001 | -0.054302 | -0.073405 |
| sensitivity | test | month | 2025-10 | 1873 | -0.052454 | -0.061327 |
| sensitivity | test | month | 2025-07 | 2133 | -0.097015 | -0.053914 |
| main | test | month | 2025-07 | 2133 | -0.077144 | -0.031952 |
| main | forward | month | 2026-04 | 1444 | -0.046749 | -0.029525 |
| main | forward | liquidity_bucket | high | 1653 | -0.067387 | -0.028946 |
| main | test | month | 2025-10 | 1873 | 0.036167 | -0.023140 |
| sensitivity | forward | liquidity_bucket | high | 1653 | -0.032397 | -0.022498 |
| sensitivity | test | market_regime | bull | 11818 | -0.019605 | -0.018637 |
| sensitivity | test | year | 2025 | 11818 | -0.019605 | -0.018637 |

### Feature Stability

| group_value | rankic_regression | rankic_qlib_rank | summary |
|---|---|---|---|
| avg_trading_value_20d | 7.000000 | 9.000000 | rankic_regression stores main importance rank; rankic_qlib_rank stores sensitivity rank. |
| bollinger_position | 18.000000 | 20.000000 | rankic_regression stores main importance rank; rankic_qlib_rank stores sensitivity rank. |
| distance_to_ma20_pct | 19.000000 | 23.000000 | rankic_regression stores main importance rank; rankic_qlib_rank stores sensitivity rank. |
| liquidity_percentile_by_date | 2.000000 | 5.000000 | rankic_regression stores main importance rank; rankic_qlib_rank stores sensitivity rank. |
| ma20_slope | 11.000000 | 19.000000 | rankic_regression stores main importance rank; rankic_qlib_rank stores sensitivity rank. |
| ma60_slope | 3.000000 | 1.000000 | rankic_regression stores main importance rank; rankic_qlib_rank stores sensitivity rank. |
| macd_hist | 8.000000 | 7.000000 | rankic_regression stores main importance rank; rankic_qlib_rank stores sensitivity rank. |
| market_breadth_ma20 | 4.000000 | 8.000000 | rankic_regression stores main importance rank; rankic_qlib_rank stores sensitivity rank. |
| market_breadth_ret20_positive | 9.000000 | 14.000000 | rankic_regression stores main importance rank; rankic_qlib_rank stores sensitivity rank. |
| market_drawdown60 | 5.000000 | 10.000000 | rankic_regression stores main importance rank; rankic_qlib_rank stores sensitivity rank. |
| market_volatility20 | 15.000000 | 4.000000 | rankic_regression stores main importance rank; rankic_qlib_rank stores sensitivity rank. |
| ret20 | 14.000000 | 13.000000 | rankic_regression stores main importance rank; rankic_qlib_rank stores sensitivity rank. |

## 7. Safety Boundary

- Exit Risk Model：未训练。
- LambdaRank：未训练。
- 组合回放与前端：未执行。
- broker/orders/quick-trade/target position：未触碰。
- provider refresh/publish/accepted latest switching：未触碰。
- monitor config/alerts：未触碰。
- 真实交易建议语义：未生成。
