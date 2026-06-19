# Phase V1B Split-aware / Lookahead 修复执行报告

生成时间：2026-06-14T07:21:40+00:00

## 1. 本轮目标

按审查文档要求，只修复 Phase V1 年度结果的 split-aware / lookahead 审计缺口。 本轮读取既有 Phase V1 年度产物并重建 accepted/common replay 日期覆盖，补充 split 覆盖、样本状态和样本外解释限制。

本轮未执行新回放、未执行 rolling、未执行市况分段、未做 walk-forward、未做 label-shuffle、未做 feature leakage scan、未调参、未重训 LTR、未改策略、未改 Phase1C score、未改 replay 口径、未改前端/API、未联网、未新增数据源、未触发 provider / accepted latest / monitor / 交易链路。

## 2. Split 定义

| split | 起始日期 | 结束日期 | 解释限制 |
| --- | --- | --- | --- |
| train | 2022-01-10 | 2024-08-09 | 样本内训练覆盖区间，不得解释为样本外效果 |
| validation | 2024-08-12 | 2025-06-24 | 验证期，不得解释为独立样本外效果 |
| independent_test | 2025-06-25 | 2026-05-07 | 可作为样本外审查核心，但仍需后续 walk-forward 等审查 |
| post_independent_test_or_out_of_split | split 外日期 | split 外日期 | 不得混入 independent_test 结论 |

## 3. 年度 Split 覆盖修复结果

| period | split_coverage | train_days | validation_days | independent_test_days | out_of_split_days | sample_status | oos_interpretation_allowed | oos_interpretation_note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2022 | train:241;validation:0;independent_test:0;out_of_split:0 | 241 | 0 | 0 | 0 | train_only | false | 样本内训练覆盖区间，只能用于复盘，不能作为样本外证据。 |
| 2023 | train:239;validation:0;independent_test:0;out_of_split:0 | 239 | 0 | 0 | 0 | train_only | false | 样本内训练覆盖区间，只能用于复盘，不能作为样本外证据。 |
| 2024 | train:145;validation:97;independent_test:0;out_of_split:0 | 145 | 97 | 0 | 0 | train_validation_mixed | false | 年度结果混合 train 与 validation，不能作为独立样本外证据。 |
| 2025 | train:0;validation:112;independent_test:130;out_of_split:0 | 0 | 112 | 130 | 0 | validation_independent_test_mixed | false | 年度结果混合 validation 与 independent_test，必须拆分后才能解释样本外效果。 |
| 2026_ytd | train:0;validation:0;independent_test:79;out_of_split:16 | 0 | 0 | 79 | 16 | independent_test_out_of_split_mixed | false | 年度 YTD 覆盖 post-independent / out-of-split 日期，不能作为完整年度样本外证据；只能拆出 independent_test 截止日内部分审查。 |

说明：2026 YTD 的 out_of_split_days=16 来自 2026-05-08 之后的 accepted signal days；这些日期已从共同回放结果中排除，但必须显式标注为 post-independent / out-of-split，不能混入 independent_test 结论。

## 4. 主候选与主基线 Split-aware 年度结果

| period | method | fee_tax_adjusted_net_return | max_drawdown | action_count | split_coverage | sample_status | oos_interpretation_allowed | oos_interpretation_note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2022 | rank_rotate_top50_adaptive_score | -0.12456 | -0.241499 | 418 | train:241;validation:0;independent_test:0;out_of_split:0 | train_only | false | 样本内训练覆盖区间，只能用于复盘，不能作为样本外证据。 |
| 2022 | phase1c_ltr_simple_daily | -0.00163 | -0.256739 | 464 | train:241;validation:0;independent_test:0;out_of_split:0 | train_only | false | 样本内训练覆盖区间，只能用于复盘，不能作为样本外证据。 |
| 2022 | phase1c_ltr_turnover_controlled_daily | 0.11929 | -0.160512 | 73 | train:241;validation:0;independent_test:0;out_of_split:0 | train_only | false | 样本内训练覆盖区间，只能用于复盘，不能作为样本外证据。 |
| 2023 | rank_rotate_top50_adaptive_score | 1.371793 | -0.140026 | 440 | train:239;validation:0;independent_test:0;out_of_split:0 | train_only | false | 样本内训练覆盖区间，只能用于复盘，不能作为样本外证据。 |
| 2023 | phase1c_ltr_simple_daily | 1.965554 | -0.145731 | 432 | train:239;validation:0;independent_test:0;out_of_split:0 | train_only | false | 样本内训练覆盖区间，只能用于复盘，不能作为样本外证据。 |
| 2023 | phase1c_ltr_turnover_controlled_daily | 0.630687 | -0.130101 | 72 | train:239;validation:0;independent_test:0;out_of_split:0 | train_only | false | 样本内训练覆盖区间，只能用于复盘，不能作为样本外证据。 |
| 2024 | rank_rotate_top50_adaptive_score | 0.794357 | -0.282289 | 454 | train:145;validation:97;independent_test:0;out_of_split:0 | train_validation_mixed | false | 年度结果混合 train 与 validation，不能作为独立样本外证据。 |
| 2024 | phase1c_ltr_simple_daily | 1.87572 | -0.234454 | 450 | train:145;validation:97;independent_test:0;out_of_split:0 | train_validation_mixed | false | 年度结果混合 train 与 validation，不能作为独立样本外证据。 |
| 2024 | phase1c_ltr_turnover_controlled_daily | 0.784358 | -0.118144 | 74 | train:145;validation:97;independent_test:0;out_of_split:0 | train_validation_mixed | false | 年度结果混合 train 与 validation，不能作为独立样本外证据。 |
| 2025 | rank_rotate_top50_adaptive_score | 0.833162 | -0.38705 | 446 | train:0;validation:112;independent_test:130;out_of_split:0 | validation_independent_test_mixed | false | 年度结果混合 validation 与 independent_test，必须拆分后才能解释样本外效果。 |
| 2025 | phase1c_ltr_simple_daily | 2.01937 | -0.337204 | 450 | train:0;validation:112;independent_test:130;out_of_split:0 | validation_independent_test_mixed | false | 年度结果混合 validation 与 independent_test，必须拆分后才能解释样本外效果。 |
| 2025 | phase1c_ltr_turnover_controlled_daily | 0.218875 | -0.173828 | 74 | train:0;validation:112;independent_test:130;out_of_split:0 | validation_independent_test_mixed | false | 年度结果混合 validation 与 independent_test，必须拆分后才能解释样本外效果。 |
| 2026_ytd | rank_rotate_top50_adaptive_score | 0.896163 | -0.161748 | 148 | train:0;validation:0;independent_test:79;out_of_split:16 | independent_test_out_of_split_mixed | false | 年度 YTD 覆盖 post-independent / out-of-split 日期，不能作为完整年度样本外证据；只能拆出 independent_test 截止日内部分审查。 |
| 2026_ytd | phase1c_ltr_simple_daily | 0.973726 | -0.168388 | 146 | train:0;validation:0;independent_test:79;out_of_split:16 | independent_test_out_of_split_mixed | false | 年度 YTD 覆盖 post-independent / out-of-split 日期，不能作为完整年度样本外证据；只能拆出 independent_test 截止日内部分审查。 |
| 2026_ytd | phase1c_ltr_turnover_controlled_daily | 0.113415 | -0.085224 | 24 | train:0;validation:0;independent_test:79;out_of_split:16 | independent_test_out_of_split_mixed | false | 年度 YTD 覆盖 post-independent / out-of-split 日期，不能作为完整年度样本外证据；只能拆出 independent_test 截止日内部分审查。 |

## 5. 必须修正的解释

1. 2022 和 2023 是 `train_only`，只能用于样本内复盘，不能作为样本外证据。
2. 2024 是 `train_validation_mixed`，年度聚合结果不能作为独立样本外证据。
3. 2025 是 `validation_independent_test_mixed`，年度聚合结果混合验证期和独立测试期，不能直接解释为独立样本外效果。
4. 2026 YTD 的共同回放结果覆盖 independent_test 至 2026-05-07；2026-05-08 之后标注为 `post_independent_test_or_out_of_split`，不得混入 independent_test 结论。
5. 后续进入 V2 或产品化设计前，必须以 independent_test、walk-forward out-of-sample validation、label-shuffle sanity check、feature leakage scan 为核心审查依据。
6. 不得用 2022/2023/2024 的强收益为产品化背书。

## 6. 产物

- split 覆盖表：`data_tw/experiments/ltr_strategy_validation/phasev1_yearly_replay/phasev1b_yearly_split_coverage.csv`
- split-aware 年度方法表：`data_tw/experiments/ltr_strategy_validation/phasev1_yearly_replay/phasev1b_yearly_split_method_comparison.csv`
- gate summary：`data_tw/experiments/ltr_strategy_validation/phasev1_yearly_replay/phasev1b_split_gate_summary.json`

## 7. Gate

- `split_aware_audit_passed`: `True`
- `oos_interpretation_guardrail_passed`: `True`
- `ready_for_phase_v2_comprehensive_stability_validation`: `True`
- recommended gate: `phasev1b_split_aware_repair_completed_hold_for_review`

等待审查者确认后，才可进入 Phase V2；本轮不自动启动 rolling、市况、walk-forward、label-shuffle 或 leakage scan。
