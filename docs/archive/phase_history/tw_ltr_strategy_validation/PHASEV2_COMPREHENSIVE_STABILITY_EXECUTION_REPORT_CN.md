# Phase V2 综合稳定性验证执行报告

生成时间：2026-06-14T10:00:08+00:00

## 1. 本轮目标

按 Phase V2 工作文档，在 Phase V1/V1B 年度与 split-aware 审计基础上，完成 LTR 候选策略综合稳定性验证。本轮覆盖 rolling 6M/12M、市况分段、walk-forward OOS、label-shuffle sanity check 与 feature leakage scan。

本轮未重训 LTR、未调参、未改候选策略、未改 Phase1C score、未改 replay 口径、未新增数据源、未联网、未改前端/API、未触发 provider / accepted latest / monitor / 交易链路。所有结果均为只读历史模拟和审计诊断，不是买卖、仓位或收益承诺。

## 2. Rolling 6M / 12M 摘要

| method | rows | avg_net_return | min_net_return | avg_max_drawdown | avg_action_count | positive_window_count |
| --- | --- | --- | --- | --- | --- | --- |
| rank_rotate_top30 | 18 | 0.559488 | -0.202398 | -0.213887 | 337.33 | 13 |
| rank_rotate_top50 | 18 | 0.590678 | -0.213877 | -0.226924 | 326.56 | 13 |
| rank_rotate_top50_adaptive_score | 18 | 0.617194 | -0.156989 | -0.210433 | 318.44 | 14 |
| confirmed_exit | 18 | 0.261993 | -0.263328 | -0.186888 | 49.06 | 12 |
| phase1c_ltr_simple_daily | 18 | 1.043586 | -0.149026 | -0.2072 | 324.89 | 15 |
| phase1c_ltr_turnover_controlled_daily | 18 | 0.327495 | -0.109791 | -0.115315 | 53.56 | 14 |

解释：LTR simple 的 rolling 收益更高，但仍需结合 OOS split 与 label/leakage 审查；turnover-controlled LTR 的平均动作数和回撤压力较低，但收益牺牲明显。Top50 adaptive 仍作为主比较基线保留。

## 3. 市况分段摘要

| regime | method | fee_tax_adjusted_net_return | max_drawdown | action_count | turnover_proxy_by_notional_over_avg_equity | relative_return_vs_top50_adaptive | relative_drawdown_vs_top50_adaptive | relative_actions_vs_top50_adaptive | sample_status | oos_interpretation_allowed |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| normal | rank_rotate_top30 | 14.802259 | -0.177301 | 1652 | 136.482704 | 2.827782 | 0.019681 | 66 | mixed_or_insufficient_data | false |
| normal | rank_rotate_top50 | 11.974477 | -0.196982 | 1586 | 140.666961 | 0.0 | 0.0 | 0 | mixed_or_insufficient_data | false |
| normal | rank_rotate_top50_adaptive_score | 11.974477 | -0.196982 | 1586 | 140.666961 | 0.0 | 0.0 | 0 | mixed_or_insufficient_data | false |
| normal | confirmed_exit | 2.92659 | -0.299382 | 202 | 16.347272 | -9.047887 | -0.1024 | -1384 | mixed_or_insufficient_data | false |
| normal | phase1c_ltr_simple_daily | 26.639084 | -0.197785 | 1588 | 160.476719 | 14.664607 | -0.000803 | 2 | mixed_or_insufficient_data | false |
| normal | phase1c_ltr_turnover_controlled_daily | 3.003386 | -0.13033 | 254 | 25.267843 | -8.971091 | 0.066652 | -1332 | mixed_or_insufficient_data | false |
| caution | rank_rotate_top30 | 0.609778 | -0.174962 | 216 | 21.293158 | 0.304884 | 0.025803 | 35 | train_validation_mixed | false |
| caution | rank_rotate_top50 | 0.850231 | -0.188264 | 214 | 22.10366 | 0.545337 | 0.012501 | 33 | train_validation_mixed | false |
| caution | rank_rotate_top50_adaptive_score | 0.304894 | -0.200765 | 181 | 17.882359 | 0.0 | 0.0 | 0 | train_validation_mixed | false |
| caution | confirmed_exit | 1.727083 | -0.229752 | 44 | 5.281637 | 1.422189 | -0.028987 | -137 | train_validation_mixed | false |
| caution | phase1c_ltr_simple_daily | 2.188211 | -0.18519 | 213 | 23.082457 | 1.883317 | 0.015575 | 32 | train_validation_mixed | false |
| caution | phase1c_ltr_turnover_controlled_daily | 1.063962 | -0.166987 | 34 | 3.547135 | 0.759068 | 0.033778 | -147 | train_validation_mixed | false |
| risk_off | rank_rotate_top30 | 1.608411 | -0.290345 | 171 | 16.169831 | -0.852611 | -0.054517 | 23 | train_validation_mixed | false |
| risk_off | rank_rotate_top50 | 2.060724 | -0.320451 | 164 | 16.047384 | -0.400298 | -0.084623 | 16 | train_validation_mixed | false |
| risk_off | rank_rotate_top50_adaptive_score | 2.461022 | -0.235828 | 148 | 15.189752 | 0.0 | 0.0 | 0 | train_validation_mixed | false |
| risk_off | confirmed_exit | 0.076338 | -0.141372 | 39 | 3.922875 | -2.384684 | 0.094456 | -109 | train_validation_mixed | false |
| risk_off | phase1c_ltr_simple_daily | 0.923282 | -0.310138 | 168 | 17.046333 | -1.53774 | -0.07431 | 20 | train_validation_mixed | false |
| risk_off | phase1c_ltr_turnover_controlled_daily | 0.407006 | -0.239088 | 27 | 2.401473 | -2.054016 | -0.00326 | -121 | train_validation_mixed | false |

市况定义：沿用 Phase3A2C 本地 proxy regime，`normal` 保持为 normal，`caution` 保持为 caution，`severe` 映射为 `risk_off`。该分段仅用于研究诊断，不打开 regime gating。

## 4. Walk-forward OOS

| fold_id | walk_forward_mode | test_period | method | fee_tax_adjusted_net_return | max_drawdown | action_count | relative_return_vs_top50_adaptive | relative_drawdown_vs_top50_adaptive | relative_actions_vs_top50_adaptive | sample_status | oos_interpretation_allowed |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| wf_independent_2025h2 | frozen_score_oos_replay_only | 2025-06-25..2025-12-31 | rank_rotate_top30 | 0.911744 | -0.139319 | 248 | -0.038782 | -0.007842 | 18 | independent_test_only | true |
| wf_independent_2025h2 | frozen_score_oos_replay_only | 2025-06-25..2025-12-31 | rank_rotate_top50 | 0.950526 | -0.131477 | 230 | 0.0 | 0.0 | 0 | independent_test_only | true |
| wf_independent_2025h2 | frozen_score_oos_replay_only | 2025-06-25..2025-12-31 | rank_rotate_top50_adaptive_score | 0.950526 | -0.131477 | 230 | 0.0 | 0.0 | 0 | independent_test_only | true |
| wf_independent_2025h2 | frozen_score_oos_replay_only | 2025-06-25..2025-12-31 | confirmed_exit | 0.348112 | -0.094442 | 30 | -0.602414 | 0.037035 | -200 | independent_test_only | true |
| wf_independent_2025h2 | frozen_score_oos_replay_only | 2025-06-25..2025-12-31 | phase1c_ltr_simple_daily | 1.165049 | -0.137301 | 228 | 0.214523 | -0.005824 | -2 | independent_test_only | true |
| wf_independent_2025h2 | frozen_score_oos_replay_only | 2025-06-25..2025-12-31 | phase1c_ltr_turnover_controlled_daily | 0.197409 | -0.084103 | 39 | -0.753117 | 0.047374 | -191 | independent_test_only | true |
| wf_independent_2026ytd | frozen_score_oos_replay_only | 2026-01-01..2026-05-07 | rank_rotate_top30 | 0.501287 | -0.174852 | 149 | -0.394876 | -0.013104 | 1 | independent_test_only | true |
| wf_independent_2026ytd | frozen_score_oos_replay_only | 2026-01-01..2026-05-07 | rank_rotate_top50 | 0.896163 | -0.161748 | 148 | 0.0 | 0.0 | 0 | independent_test_only | true |
| wf_independent_2026ytd | frozen_score_oos_replay_only | 2026-01-01..2026-05-07 | rank_rotate_top50_adaptive_score | 0.896163 | -0.161748 | 148 | 0.0 | 0.0 | 0 | independent_test_only | true |
| wf_independent_2026ytd | frozen_score_oos_replay_only | 2026-01-01..2026-05-07 | confirmed_exit | 0.168845 | -0.059278 | 9 | -0.727318 | 0.10247 | -139 | independent_test_only | true |
| wf_independent_2026ytd | frozen_score_oos_replay_only | 2026-01-01..2026-05-07 | phase1c_ltr_simple_daily | 0.973726 | -0.168388 | 146 | 0.077563 | -0.00664 | -2 | independent_test_only | true |
| wf_independent_2026ytd | frozen_score_oos_replay_only | 2026-01-01..2026-05-07 | phase1c_ltr_turnover_controlled_daily | 0.113415 | -0.085224 | 24 | -0.782748 | 0.076524 | -124 | independent_test_only | true |

`walk_forward_mode = frozen_score_oos_replay_only`。本轮没有重新训练模型，也没有用新窗口反向调参；只验证冻结 score 在不同 OOS 测试切片下的 replay 稳定性。

## 5. Label-shuffle Sanity Check

| label_shuffle_status | shuffle_object | shuffle_granularity | date_constraint | actual_top10_label_mean | shuffled_top10_label_mean | actual_minus_shuffled | sanity_conclusion | reason |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| completed | future_excess_return_10d | within_asof_date_label_rotation | independent_test_only; labels shuffled only within same asof date | 0.05107369 | 0.01869732 | 0.03237637 | pass | Frozen-score rank top10 labels compared with deterministic within-date shuffled labels; no model was trained. |

## 6. Feature Leakage Scan

| leakage_scan_status | blocked_fields | date_alignment_status | available_at_status | conclusion |
| --- | --- | --- | --- | --- |
| pass |  | pass | pass | Input feature list does not include future/label fields; frozen artifact contains label fields for audit only. Split guardrail remains required. |

## 7. 结论边界

Phase V2 可以支持审查者继续判断 LTR 是否进入用户第一性产品化设计，但不能直接触发前端/API 或策略入口实现。train / validation 结果不得作为产品化背书；2025 年度聚合和 2026 YTD 聚合也不能整体视为 independent_test。

基于本轮只读验证，建议 gate 为：

`request_phase_v3_user_first_product_design`

## 8. 产物

- rolling：`data_tw/experiments/ltr_strategy_validation/phasev2_comprehensive_stability/phasev2_rolling_6m_12m.csv`
- regime：`data_tw/experiments/ltr_strategy_validation/phasev2_comprehensive_stability/phasev2_regime_segments.csv`
- walk-forward：`data_tw/experiments/ltr_strategy_validation/phasev2_comprehensive_stability/phasev2_walk_forward_oos.csv`
- label-shuffle：`data_tw/experiments/ltr_strategy_validation/phasev2_comprehensive_stability/phasev2_label_shuffle_sanity.csv`
- feature leakage scan：`data_tw/experiments/ltr_strategy_validation/phasev2_comprehensive_stability/phasev2_feature_leakage_scan.csv`
- gate summary：`data_tw/experiments/ltr_strategy_validation/phasev2_comprehensive_stability/phasev2_gate_summary.json`
