# Phase 2 Entry Model v1 执行报告

## 1. 执行摘要

- 执行日期：`2026-06-10T15:24:47+00:00`
- 修改文件：新增 `scripts/train_tw_decision_entry_model_v1.py`。
- 生成文件：Phase 2 model、prediction、metrics、split、importance、calibration、group metrics 与报告。
- 是否只训练 Entry Model：是。
- 是否触碰只读边界：否。未触发 broker/orders/quick-trade/target position/provider refresh/provider publish/accepted latest/monitor config/alerts。

## 2. 输入与 Schema

- samples path：`data_tw/experiments/decision_model/phase1_samples.parquet`
- schema path：`data_tw/experiments/decision_model/phase1_schema.json`
- input_features count：`48`
- label target：`entry_label_dynamic` / `entry_target_regression` / `entry_rank_target`
- market_regime 是否输入：`False`
- candidate_reason_flags 是否输入：`False`
- FinMind 暂缓字段是否输入：`False`

## 3. 时间切分

| split_name | train | validation | test | forward | notes |
|---|---|---|---|---|---|
| main | 2022 | 2023 | 2025 | 2026 labeled | 2024 unavailable |
| sensitivity | 2022+2023 | 2025H1 | 2025H2 | 2026 labeled | no test/forward tuning |

## 4. Split Coverage

| split_name | split_part | rows | candidate_rows | positive_rate | target_mean | target_std | unique_dates | unique_symbols |
|---|---|---|---|---|---|---|---|---|
| main | train | 21541 | 21541 | 0.398914 | 0.794768 | 2.803249 | 246 | 146 |
| main | validation | 13273 | 13273 | 0.452648 | 1.360400 | 4.139505 | 239 | 107 |
| main | test | 22662 | 22662 | 0.450181 | 1.805027 | 5.135992 | 242 | 149 |
| main | forward | 6721 | 6721 | 0.508704 | 2.384024 | 6.418824 | 69 | 150 |
| sensitivity | train | 34814 | 34814 | 0.419400 | 1.010418 | 3.386783 | 485 | 146 |
| sensitivity | validation | 10844 | 10844 | 0.438122 | 1.459172 | 3.953520 | 116 | 145 |
| sensitivity | test | 11818 | 11818 | 0.461246 | 2.122379 | 6.002696 | 126 | 149 |
| sensitivity | forward | 6721 | 6721 | 0.508704 | 2.384024 | 6.418824 | 69 | 150 |

## 5. 模型与参数

- binary model：LightGBM objective=binary, fixed params, validation early stopping only。
- regression model：LightGBM objective=regression, fixed params, validation early stopping only。
- ensemble rule：minmax(binary)*0.5 + minmax(regression)*0.5 within split part。
- fixed random seed：`20260610`
- 是否在 test/forward 调参：否。

## 6. Metrics

| split_name | split_part | model | rows | AUC | logloss | brier | regression_ic | RankIC | NDCG@5 | NDCG@10 | precision@5 | top5_excess_return | top10_excess_return |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| main | train | binary | 21541 | 0.679053 | 0.669624 | 0.238368 | 0.246912 | 0.231054 | 0.559725 | 0.599328 | 0.650407 | 0.039456 | 0.033910 |
| main | train | regression | 21541 | 0.663011 |  |  | 0.496937 | 0.256166 | 0.642006 | 0.677376 | 0.571545 | 0.073532 | 0.060367 |
| main | train | ensemble | 21541 | 0.703231 | 0.614912 | 0.213474 | 0.359143 | 0.300767 | 0.653628 | 0.681064 | 0.703252 | 0.079928 | 0.061198 |
| main | validation | binary | 13273 | 0.468941 | 0.695663 | 0.251154 | -0.106269 | -0.055211 | 0.392178 | 0.450534 | 0.364017 | -0.004375 | 0.003591 |
| main | validation | regression | 13273 | 0.508145 |  |  | 0.092733 | -0.006460 | 0.479056 | 0.515970 | 0.487029 | 0.040073 | 0.025653 |
| main | validation | ensemble | 13273 | 0.474110 | 0.979665 | 0.328103 | -0.061848 | -0.041680 | 0.415001 | 0.472092 | 0.402510 | 0.008791 | 0.012616 |
| main | test | binary | 22662 | 0.512983 | 0.693798 | 0.250246 | -0.020433 | 0.011317 | 0.365996 | 0.413547 | 0.390909 | 0.001034 | 0.010919 |
| main | test | regression | 22662 | 0.512759 |  |  | 0.040532 | 0.034912 | 0.413019 | 0.460928 | 0.459504 | 0.046758 | 0.047104 |
| main | test | ensemble | 22662 | 0.515064 | 0.756653 | 0.274773 | -0.002984 | 0.027954 | 0.391498 | 0.428305 | 0.425620 | 0.015054 | 0.014437 |
| main | forward | binary | 6721 | 0.464138 | 0.720096 | 0.263180 | -0.063388 | -0.085280 | 0.313857 | 0.375766 | 0.307246 | -0.011068 | 0.024960 |
| main | forward | regression | 6721 | 0.558352 |  |  | 0.066832 | 0.101562 | 0.431065 | 0.483214 | 0.542029 | 0.081534 | 0.102625 |
| main | forward | ensemble | 6721 | 0.495397 | 1.111162 | 0.367741 | -0.003932 | -0.003287 | 0.378608 | 0.424583 | 0.443478 | 0.040906 | 0.055189 |
| sensitivity | train | binary | 34814 | 0.631778 | 0.678328 | 0.242642 | 0.231587 | 0.150250 | 0.552690 | 0.593560 | 0.597526 | 0.060990 | 0.049065 |
| sensitivity | train | regression | 34814 | 0.600333 |  |  | 0.435018 | 0.144261 | 0.626106 | 0.645635 | 0.602062 | 0.089490 | 0.062855 |
| sensitivity | train | ensemble | 34814 | 0.647522 | 0.666758 | 0.237061 | 0.339287 | 0.181870 | 0.626288 | 0.652107 | 0.635464 | 0.088900 | 0.065880 |
| sensitivity | validation | binary | 10844 | 0.450490 | 0.686671 | 0.246757 | -0.017668 | 0.017842 | 0.439451 | 0.482865 | 0.522414 | 0.024963 | 0.019844 |
| sensitivity | validation | regression | 10844 | 0.520193 |  |  | 0.060548 | -0.023601 | 0.427842 | 0.476086 | 0.415517 | 0.015963 | 0.018739 |
| sensitivity | validation | ensemble | 10844 | 0.455553 | 0.773517 | 0.282283 | 0.003350 | -0.007210 | 0.450082 | 0.483781 | 0.489655 | 0.029091 | 0.018740 |
| sensitivity | test | binary | 11818 | 0.517872 | 0.693201 | 0.250002 | 0.007945 | 0.038513 | 0.389483 | 0.436835 | 0.531746 | 0.069164 | 0.071220 |
| sensitivity | test | regression | 11818 | 0.560397 |  |  | 0.065197 | 0.082370 | 0.378386 | 0.416908 | 0.526984 | 0.056850 | 0.052195 |
| sensitivity | test | ensemble | 11818 | 0.542876 | 0.840514 | 0.299787 | 0.037245 | 0.073446 | 0.381402 | 0.421412 | 0.507937 | 0.059434 | 0.054917 |
| sensitivity | forward | binary | 6721 | 0.573596 | 0.705900 | 0.256316 | 0.122176 | 0.150887 | 0.443923 | 0.482571 | 0.608696 | 0.098335 | 0.099032 |
| sensitivity | forward | regression | 6721 | 0.599976 |  |  | 0.148812 | 0.151354 | 0.467792 | 0.490343 | 0.620290 | 0.120099 | 0.100118 |
| sensitivity | forward | ensemble | 6721 | 0.597773 | 0.718193 | 0.257548 | 0.145908 | 0.151911 | 0.469389 | 0.490117 | 0.626087 | 0.122124 | 0.099640 |

## 7. Baseline 对比

| split_name | split_part | model | rows | AUC | logloss | brier | regression_ic | RankIC | NDCG@5 | NDCG@10 | precision@5 | top5_excess_return | top10_excess_return |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| main | train | baseline_qlib_raw | 21541 | 0.516873 |  |  | 0.054473 | 0.015830 | 0.494055 | 0.526650 | 0.424390 | 0.011841 | 0.005010 |
| main | train | baseline_qlib_percentile | 21541 | 0.515017 | 1.108241 | 0.353741 | 0.036635 | 0.015830 | 0.494055 | 0.526650 | 0.424390 | 0.011841 | 0.005010 |
| main | train | baseline_qlib_rank | 21541 | 0.515113 |  |  | 0.036807 | 0.015828 | 0.494055 | 0.526650 | 0.424390 | 0.011841 | 0.005010 |
| main | train | baseline_candidate_sort | 21541 | 0.497818 |  |  | 0.000860 | -0.012461 | 0.464787 | 0.507969 | 0.399187 | -0.003723 | -0.002111 |
| main | train | baseline_random | 21541 | 0.494624 | 1.006692 | 0.335735 | -0.006505 | -0.006774 | 0.471718 | 0.516300 | 0.403252 | 0.004316 | 0.003557 |
| main | validation | baseline_qlib_raw | 13273 | 0.533523 |  |  | 0.103984 | 0.064807 | 0.474338 | 0.527811 | 0.526360 | 0.047143 | 0.041564 |
| main | validation | baseline_qlib_percentile | 13273 | 0.533598 | 1.025679 | 0.321898 | 0.083400 | 0.064807 | 0.474338 | 0.527811 | 0.526360 | 0.047143 | 0.041564 |
| main | validation | baseline_qlib_rank | 13273 | 0.535323 |  |  | 0.089545 | 0.064811 | 0.474338 | 0.527811 | 0.526360 | 0.047143 | 0.041564 |
| main | validation | baseline_candidate_sort | 13273 | 0.509792 |  |  | 0.040824 | 0.017941 | 0.437994 | 0.494900 | 0.462762 | 0.024840 | 0.027558 |
| main | validation | baseline_random | 13273 | 0.497351 | 1.007150 | 0.335485 | 0.001821 | -0.002766 | 0.430873 | 0.477131 | 0.471967 | 0.021578 | 0.015681 |
| main | test | baseline_qlib_raw | 22662 | 0.522902 |  |  | 0.044448 | 0.023365 | 0.412562 | 0.453923 | 0.496694 | 0.044263 | 0.041242 |
| main | test | baseline_qlib_percentile | 22662 | 0.511693 | 1.067257 | 0.342935 | 0.011555 | 0.023365 | 0.412562 | 0.453923 | 0.496694 | 0.044263 | 0.041242 |
| main | test | baseline_qlib_rank | 22662 | 0.511697 |  |  | 0.011558 | 0.023378 | 0.412562 | 0.453923 | 0.496694 | 0.044263 | 0.041242 |
| main | test | baseline_candidate_sort | 22662 | 0.523586 |  |  | 0.040344 | 0.025467 | 0.390132 | 0.442817 | 0.442975 | 0.025595 | 0.035340 |
| main | test | baseline_random | 22662 | 0.500608 | 1.002858 | 0.333360 | 0.008351 | 0.010031 | 0.394238 | 0.438454 | 0.457851 | 0.028434 | 0.030407 |
| main | forward | baseline_qlib_raw | 6721 | 0.534782 |  |  | 0.030502 | 0.080698 | 0.426694 | 0.468027 | 0.565217 | 0.078387 | 0.086197 |
| main | forward | baseline_qlib_percentile | 6721 | 0.548041 | 0.970885 | 0.311715 | 0.054956 | 0.080698 | 0.426694 | 0.468027 | 0.565217 | 0.078387 | 0.086197 |
| main | forward | baseline_qlib_rank | 6721 | 0.548052 |  |  | 0.054960 | 0.080696 | 0.426694 | 0.468027 | 0.565217 | 0.078387 | 0.086197 |
| main | forward | baseline_candidate_sort | 6721 | 0.542789 |  |  | 0.059598 | 0.063598 | 0.430640 | 0.461609 | 0.594203 | 0.081229 | 0.076417 |
| main | forward | baseline_random | 6721 | 0.495929 | 1.010296 | 0.336402 | -0.006811 | -0.007300 | 0.396648 | 0.426527 | 0.501449 | 0.059953 | 0.049681 |
| sensitivity | train | baseline_qlib_raw | 34814 | 0.524864 |  |  | 0.085135 | 0.039965 | 0.484339 | 0.527222 | 0.474639 | 0.029237 | 0.023023 |
| sensitivity | train | baseline_qlib_percentile | 34814 | 0.521077 | 1.076764 | 0.341600 | 0.053782 | 0.039965 | 0.484339 | 0.527222 | 0.474639 | 0.029237 | 0.023023 |
| sensitivity | train | baseline_qlib_rank | 34814 | 0.528820 |  |  | 0.071951 | 0.039966 | 0.484339 | 0.527222 | 0.474639 | 0.029237 | 0.023023 |
| sensitivity | train | baseline_candidate_sort | 34814 | 0.504867 |  |  | 0.024332 | 0.002521 | 0.451584 | 0.501529 | 0.430515 | 0.010352 | 0.012509 |
| sensitivity | train | baseline_random | 34814 | 0.496337 | 1.004414 | 0.335480 | -0.010376 | -0.003308 | 0.450822 | 0.500324 | 0.431753 | 0.011446 | 0.011345 |
| sensitivity | validation | baseline_qlib_raw | 10844 | 0.520300 |  |  | 0.022968 | 0.024619 | 0.421808 | 0.464078 | 0.448276 | 0.009295 | 0.009101 |
| sensitivity | validation | baseline_qlib_percentile | 10844 | 0.495309 | 1.099021 | 0.352392 | -0.008369 | 0.024619 | 0.421808 | 0.464078 | 0.448276 | 0.009295 | 0.009101 |
| sensitivity | validation | baseline_qlib_rank | 10844 | 0.495319 |  |  | -0.008358 | 0.024645 | 0.421808 | 0.464078 | 0.448276 | 0.009295 | 0.009101 |
| sensitivity | validation | baseline_candidate_sort | 10844 | 0.519826 |  |  | 0.020752 | 0.026871 | 0.418755 | 0.471687 | 0.417241 | 0.009666 | 0.015803 |
| sensitivity | validation | baseline_random | 10844 | 0.492777 | 1.015387 | 0.337894 | -0.015698 | -0.007028 | 0.432606 | 0.476740 | 0.441379 | 0.015415 | 0.015175 |
| sensitivity | test | baseline_qlib_raw | 11818 | 0.522967 |  |  | 0.041866 | 0.022210 | 0.404049 | 0.444575 | 0.541270 | 0.076455 | 0.070832 |
| sensitivity | test | baseline_qlib_percentile | 11818 | 0.526505 | 1.038112 | 0.334257 | 0.022896 | 0.022210 | 0.404049 | 0.444575 | 0.541270 | 0.076455 | 0.070832 |
| sensitivity | test | baseline_qlib_rank | 11818 | 0.526505 |  |  | 0.022895 | 0.022212 | 0.404049 | 0.444575 | 0.541270 | 0.076455 | 0.070832 |
| sensitivity | test | baseline_candidate_sort | 11818 | 0.525439 |  |  | 0.045839 | 0.024174 | 0.363781 | 0.416238 | 0.466667 | 0.040260 | 0.053327 |
| sensitivity | test | baseline_random | 11818 | 0.500522 | 1.001004 | 0.333748 | 0.007007 | 0.007782 | 0.377531 | 0.404255 | 0.485714 | 0.055272 | 0.037862 |
| sensitivity | forward | baseline_qlib_raw | 6721 | 0.534782 |  |  | 0.030502 | 0.080698 | 0.426694 | 0.468027 | 0.565217 | 0.078387 | 0.086197 |
| sensitivity | forward | baseline_qlib_percentile | 6721 | 0.548041 | 0.970885 | 0.311715 | 0.054956 | 0.080698 | 0.426694 | 0.468027 | 0.565217 | 0.078387 | 0.086197 |
| sensitivity | forward | baseline_qlib_rank | 6721 | 0.548052 |  |  | 0.054960 | 0.080696 | 0.426694 | 0.468027 | 0.565217 | 0.078387 | 0.086197 |
| sensitivity | forward | baseline_candidate_sort | 6721 | 0.542789 |  |  | 0.059598 | 0.063598 | 0.430640 | 0.461609 | 0.594203 | 0.081229 | 0.076417 |
| sensitivity | forward | baseline_random | 6721 | 0.495929 | 1.010296 | 0.336402 | -0.006811 | -0.007300 | 0.396648 | 0.426527 | 0.501449 | 0.059953 | 0.049681 |

## 8. 分组评估

- by year / market_regime / qlib rank bucket / liquidity bucket / position_risk_status：详见 `phase2_group_metrics.csv`。

## 9. Feature Importance

| split_name | model | feature | importance_gain | importance_split |
|---|---|---|---|---|
| sensitivity | regression | ma60_slope | 114290.056946 | 34 |
| main | regression | volatility20 | 68922.824219 | 93 |
| sensitivity | regression | volatility20 | 62713.653534 | 36 |
| sensitivity | regression | twii_close_vs_ma120 | 60452.423096 | 26 |
| sensitivity | regression | market_volatility20 | 60267.203583 | 28 |
| main | regression | liquidity_percentile_by_date | 50723.141800 | 75 |
| main | regression | ma60_slope | 36486.391052 | 89 |
| main | regression | market_breadth_ma20 | 29880.792175 | 40 |
| sensitivity | regression | liquidity_percentile_by_date | 29265.825043 | 29 |
| main | regression | market_drawdown60 | 26950.519012 | 55 |
| sensitivity | regression | twii_ret60 | 26092.791931 | 32 |
| sensitivity | regression | macd_hist | 25518.239258 | 24 |
| sensitivity | regression | market_breadth_ma20 | 23010.700958 | 21 |
| sensitivity | regression | avg_trading_value_20d | 22762.919861 | 28 |
| main | regression | slippage_proxy | 22035.022919 | 34 |
- 是否有 forbidden/future/deferred 字段：`[]`
- 是否过度依赖单一特征：待审查者结合 importance 分布判断。

## 10. Calibration

- binary calibration：详见 `phase2_calibration.csv`。
- regression score distribution：详见 `phase2_predictions.parquet`。
- score drift by split：详见 predictions 与 calibration。

## 11. 安全边界

- broker/orders/quick-trade：未触碰。
- provider publish/refresh：未触碰。
- accepted latest switching：未触碰。
- monitor config/alerts：未触碰。
- 真实交易建议语义：未生成。

## 12. 风险与待审查问题

- 必须修复：暂无执行者自行认定的必须修复项，待审查者复核。
- 需要用户确认：暂无。
- 可暂缓：Exit Risk Model、LambdaRank、组合回放、前端产品化、FinMind 暂缓字段。

## 13. Phase 3 准入建议

- 是否建议进入 Phase 3：不建议直接进入。主切分 test/forward 未优于 qlib rank/percentile baseline；敏感性切分 forward 改善但 test 仍劣化，未满足第 12 条稳健准入要求。
- 若审查者仍考虑放行，限制条件：需先解释 main split 劣化原因，并保持 research-only；不得接组合回放或前端。
