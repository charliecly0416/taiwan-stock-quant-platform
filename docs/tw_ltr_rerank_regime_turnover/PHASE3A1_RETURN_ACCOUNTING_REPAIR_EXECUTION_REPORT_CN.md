# Phase 3A1 Return Accounting Repair 执行报告

生成时间：2026-06-13T18:43:20+00:00

## 1. 本轮目标

修复 Phase3A replay 的 return accounting：在固定 Phase1C row-level score 的前提下，用非重叠 10 交易日窗口重新评估 turnover control。

## 2. 旧 Phase3A 结果处理

旧 `PHASE3A_ROUTE_B_TURNOVER_REPLAY_EXECUTION_REPORT_CN.md` 及 `phase3a_route_b_turnover_replay/` 产物把 `future_return_10d` 当作逐交易日收益复利，当前仅保留为失败证据，不作为通过证据，也不作为用户 tradeoff 决策依据。

## 3. 固定输入与边界

- Frozen artifact：`data_tw/experiments/ltr_rerank_regime_turnover/phase3a0_frozen_phase1c_scores/phase3a0_frozen_phase1c_row_scores.csv`
- Fixed score：`score_head10_all_l31_alpha0.7_top50_only`
- Return column：`future_return_10d`
- 未发现逐日收益列；因此采用非重叠 10 交易日窗口 replay。
- 未重建、未改写、未替换 Phase1C score。
- validation-only 选参；independent_test 只做终检。
- regime 仅 diagnostic-only，未用于 gate、过滤或参数选择。

## 4. Return Accounting 修复口径

- 每个 split 按交易日排序，取索引 `0, 10, 20, ...` 作为窗口起点。
- 每个窗口只应用一次 `future_return_10d` 的横截面均值作为 `window_gross_return`。
- 换手、动作、成本、holding 全部按窗口频率计算。
- `min_holding_windows` 以窗口计；`average_holding_days` 按 `10 * target_k / mean(action_count_per_window)` 估算。

## 5. 改动文件清单

- `scripts/evaluate_tw_ltr_phase3a1_return_accounting_repair.py`
- `docs/tw_ltr_rerank_regime_turnover/PHASE3A1_RETURN_ACCOUNTING_REPAIR_EXECUTION_REPORT_CN.md`

## 6. 新增产物清单

- `data_tw/experiments/ltr_rerank_regime_turnover/phase3a1_return_accounting_repair/phase3a1_validation_selection.csv`
- `data_tw/experiments/ltr_rerank_regime_turnover/phase3a1_return_accounting_repair/phase3a1_independent_test_comparison.csv`
- `data_tw/experiments/ltr_rerank_regime_turnover/phase3a1_return_accounting_repair/phase3a1_yearly_metrics.csv`
- `data_tw/experiments/ltr_rerank_regime_turnover/phase3a1_return_accounting_repair/phase3a1_regime_diagnostic_metrics.csv`
- `data_tw/experiments/ltr_rerank_regime_turnover/phase3a1_return_accounting_repair/phase3a1_turnover_action_summary.csv`
- `data_tw/experiments/ltr_rerank_regime_turnover/phase3a1_return_accounting_repair/phase3a1_window_replay_rows.csv`
- `data_tw/experiments/ltr_rerank_regime_turnover/phase3a1_return_accounting_repair/phase3a1_gate_summary.json`

## 7. validation 参数选择

| method | config_id | fee_tax_adjusted_net_return | max_drawdown | action_count | turnover_proxy | average_holding_days | selection_score | window_count |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| confirmed_exit | baseline |  |  |  |  |  |  |  |
| phase1c_simple_topk_no_turnover | baseline | 0.23498352942022582 | -0.21646929893177957 | 814 | 1.292063492063492 | 7.73955773955774 |  | 21 |
| phase1c_turnover_controlled | k30_a3_gap0.0_buf0.0_holdw2_budget0.2 | 0.36060129675125707 | -0.24929218130128938 | 146 | 0.2317460317460318 | 41.09589041095891 | 0.22344379277039983 | 21 |
| phase1c_turnover_controlled | k30_a3_gap0.01_buf0.0_holdw2_budget0.2 | 0.36060129675125707 | -0.24929218130128938 | 146 | 0.2317460317460318 | 41.09589041095891 | 0.22344379277039983 | 21 |
| phase1c_turnover_controlled | k30_a3_gap0.02_buf0.0_holdw2_budget0.2 | 0.36060129675125707 | -0.24929218130128938 | 146 | 0.2317460317460318 | 41.09589041095891 | 0.22344379277039983 | 21 |
| phase1c_turnover_controlled | k30_a1_gap0.0_buf0.0_holdw2_budget0.2 | 0.31293038271047235 | -0.2587230327207294 | 70 | 0.11111111111111116 | 85.71428571428571 | 0.18547865793824717 | 21 |
| phase1c_turnover_controlled | k30_a1_gap0.01_buf0.0_holdw2_budget0.2 | 0.31293038271047235 | -0.2587230327207294 | 70 | 0.11111111111111116 | 85.71428571428571 | 0.18547865793824717 | 21 |
| phase1c_turnover_controlled | k30_a1_gap0.02_buf0.0_holdw2_budget0.2 | 0.31293038271047235 | -0.2587230327207294 | 70 | 0.11111111111111116 | 85.71428571428571 | 0.18547865793824717 | 21 |
| phase1c_turnover_controlled | k30_a2_gap0.0_buf0.0_holdw2_budget0.2 | 0.29663005433404566 | -0.26827637711661523 | 110 | 0.1746031746031746 | 54.54545454545455 | 0.16044078711364265 | 21 |
| phase1c_turnover_controlled | k30_a2_gap0.01_buf0.0_holdw2_budget0.2 | 0.29663005433404566 | -0.26827637711661523 | 110 | 0.1746031746031746 | 54.54545454545455 | 0.16044078711364265 | 21 |
| phase1c_turnover_controlled | k30_a2_gap0.02_buf0.0_holdw2_budget0.2 | 0.29663005433404566 | -0.26827637711661523 | 110 | 0.1746031746031746 | 54.54545454545455 | 0.16044078711364265 | 21 |
| phase1c_turnover_controlled | k30_a5_gap0.0_buf0.0_holdw2_budget0.2 | 0.3054072250225104 | -0.2550398381387934 | 222 | 0.3523809523809523 | 27.027027027027028 | 0.1547493147687851 | 21 |
| phase1c_turnover_controlled | k30_a5_gap0.01_buf0.0_holdw2_budget0.2 | 0.3054072250225104 | -0.2550398381387934 | 222 | 0.3523809523809523 | 27.027027027027028 | 0.1547493147687851 | 21 |
| phase1c_turnover_controlled | k30_a5_gap0.02_buf0.0_holdw2_budget0.2 | 0.3054072250225104 | -0.2550398381387934 | 222 | 0.3523809523809523 | 27.027027027027028 | 0.1547493147687851 | 21 |

## 8. independent_test 最终结果

| method | config_id | status | return_accounting | fee_tax_adjusted_net_return | final_equity | max_drawdown | action_count | turnover_proxy | average_holding_days | cost_drag | window_count | reason |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| rank_rotate_top30 | baseline | ok | non_overlapping_10d_windows | 2.4084159323453935 | 3.4084159323453935 | -0.05260466340556613 | 820 | 1.3015873015873016 | 7.682926829268292 | 0.12095000000000002 | 21 |  |
| rank_rotate_top50 | baseline | ok | non_overlapping_10d_windows | 2.206141895669419 | 3.206141895669419 | -0.03471346316834045 | 1158 | 1.102857142857143 | 9.067357512953368 | 0.102483 | 21 |  |
| phase1c_simple_topk_no_turnover | baseline | ok | non_overlapping_10d_windows | 2.4509187220889648 | 3.4509187220889648 | -0.051929830809715805 | 750 | 1.1904761904761902 | 8.4 | 0.110625 | 21 |  |
| rank_rotate_top50_adaptive_score | baseline | blocked | non_overlapping_10d_windows |  |  |  |  |  |  |  |  | Frozen Phase3A0 artifact does not include the technical columns required to reconstruct this baseline without leaving the fixed-input boundary. |
| confirmed_exit | baseline | blocked | non_overlapping_10d_windows |  |  |  |  |  |  |  |  | Frozen Phase3A0 artifact does not include the technical columns required to reconstruct this baseline without leaving the fixed-input boundary. |
| phase1c_turnover_controlled | k30_a3_gap0.0_buf0.0_holdw2_budget0.2 | ok | non_overlapping_10d_windows | 2.329407958934038 | 3.329407958934038 | -0.05747603476257801 | 144 | 0.2285714285714286 | 41.666666666666664 | 0.021240000000000002 | 21 |  |

## 9. baseline 覆盖说明

`rank_rotate_top30`、`rank_rotate_top50`、`phase1c_simple_topk_no_turnover`、`phase1c_turnover_controlled` 已保留。`rank_rotate_top50_adaptive_score` 与 `confirmed_exit` 因 Phase3A0 frozen artifact 不含技术列而 blocked；这意味着 baseline 覆盖不完整，不能包装成完整 baseline 胜出。

## 10. 年度结果

| split | year | method | fee_tax_adjusted_net_return | final_equity | max_drawdown | action_count | turnover_proxy | window_count |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| validation | 2024 | rank_rotate_top30 | 0.18824069360371154 | 1.1882406936037115 | -0.056999340226068895 | 418 | 1.3933333333333333 | 10 |
| validation | 2025 | rank_rotate_top30 | -0.02037007847580785 | 0.9796299215241921 | -0.21936986612028642 | 506 | 1.533333333333333 | 11 |
| validation | 2024 | rank_rotate_top50 | 0.1544471345169942 | 1.1544471345169942 | -0.05327522185785838 | 602 | 1.204 | 10 |
| validation | 2025 | rank_rotate_top50 | 0.008339224984461824 | 1.0083392249844618 | -0.19902107498785837 | 682 | 1.24 | 11 |
| validation | 2024 | phase1c_simple_topk_no_turnover | 0.2415081513611339 | 1.241508151361134 | -0.06169881103583441 | 364 | 1.2133333333333334 | 10 |
| validation | 2025 | phase1c_simple_topk_no_turnover | -0.00525540000180813 | 0.9947445999981919 | -0.21646929893177957 | 450 | 1.3636363636363635 | 11 |
| independent_test | 2025 | rank_rotate_top30 | 0.6237824759242792 | 1.6237824759242792 | -0.05260466340556613 | 492 | 1.2615384615384615 | 13 |
| independent_test | 2026 | rank_rotate_top30 | 1.099059438614323 | 2.099059438614323 | 0.0 | 328 | 1.3666666666666667 | 8 |
| independent_test | 2025 | rank_rotate_top50 | 0.5582885416359225 | 1.5582885416359225 | -0.03471346316834045 | 714 | 1.0984615384615386 | 13 |
| independent_test | 2026 | rank_rotate_top50 | 1.0574763979869526 | 2.0574763979869526 | 0.0 | 444 | 1.1099999999999999 | 8 |
| independent_test | 2025 | phase1c_simple_topk_no_turnover | 0.6466386163481461 | 1.6466386163481461 | -0.051929830809715805 | 450 | 1.1538461538461537 | 13 |
| independent_test | 2026 | phase1c_simple_topk_no_turnover | 1.0957353288253877 | 2.0957353288253877 | 0.0 | 300 | 1.25 | 8 |
| validation | 2024 | phase1c_turnover_controlled | 0.36734932741048953 | 1.3673493274104895 | -0.026452415859771983 | 78 | 0.26000000000000006 | 10 |
| validation | 2025 | phase1c_turnover_controlled | -0.00493511827881743 | 0.9950648817211826 | -0.24929218130128927 | 68 | 0.20606060606060608 | 11 |
| independent_test | 2025 | phase1c_turnover_controlled | 0.5974626924634843 | 1.5974626924634843 | -0.05747603476257801 | 96 | 0.24615384615384622 | 13 |
| independent_test | 2026 | phase1c_turnover_controlled | 1.0841851109522196 | 2.0841851109522196 | 0.0 | 48 | 0.2 | 8 |

## 11. turnover / action / cost 结果

| split | method | config_id | action_count | turnover_proxy | average_holding_days | cost_drag | window_count |
| --- | --- | --- | --- | --- | --- | --- | --- |
| validation | rank_rotate_top30 | baseline | 924 | 1.4666666666666668 | 6.818181818181818 | 0.13629000000000002 | 21 |
| validation | rank_rotate_top50 | baseline | 1284 | 1.2228571428571429 | 8.177570093457943 | 0.113634 | 21 |
| validation | phase1c_simple_topk_no_turnover | baseline | 814 | 1.292063492063492 | 7.73955773955774 | 0.12006500000000002 | 21 |
| validation | rank_rotate_top50_adaptive_score | baseline |  |  |  |  |  |
| validation | confirmed_exit | baseline |  |  |  |  |  |
| validation | phase1c_turnover_controlled | k30_a1_gap0.0_buf0.0_holdw0_budget0.2 | 72 | 0.11428571428571432 | 87.5 | 0.010620000000000001 | 21 |
| validation | phase1c_turnover_controlled | k30_a1_gap0.0_buf0.0_holdw1_budget0.2 | 72 | 0.11428571428571432 | 87.5 | 0.010620000000000001 | 21 |
| validation | phase1c_turnover_controlled | k30_a1_gap0.0_buf0.0_holdw2_budget0.2 | 70 | 0.11111111111111116 | 85.71428571428571 | 0.010325 | 21 |
| validation | phase1c_turnover_controlled | k30_a1_gap0.01_buf0.0_holdw0_budget0.2 | 72 | 0.11428571428571432 | 87.5 | 0.010620000000000001 | 21 |
| validation | phase1c_turnover_controlled | k30_a1_gap0.01_buf0.0_holdw1_budget0.2 | 72 | 0.11428571428571432 | 87.5 | 0.010620000000000001 | 21 |
| validation | phase1c_turnover_controlled | k30_a1_gap0.01_buf0.0_holdw2_budget0.2 | 70 | 0.11111111111111116 | 85.71428571428571 | 0.010325 | 21 |
| validation | phase1c_turnover_controlled | k30_a1_gap0.02_buf0.0_holdw0_budget0.2 | 72 | 0.11428571428571432 | 87.5 | 0.010620000000000001 | 21 |
| validation | phase1c_turnover_controlled | k30_a1_gap0.02_buf0.0_holdw1_budget0.2 | 72 | 0.11428571428571432 | 87.5 | 0.010620000000000001 | 21 |
| validation | phase1c_turnover_controlled | k30_a1_gap0.02_buf0.0_holdw2_budget0.2 | 70 | 0.11111111111111116 | 85.71428571428571 | 0.010325 | 21 |
| validation | phase1c_turnover_controlled | k30_a2_gap0.0_buf0.0_holdw0_budget0.2 | 114 | 0.18095238095238095 | 55.26315789473684 | 0.016815 | 21 |
| validation | phase1c_turnover_controlled | k30_a2_gap0.0_buf0.0_holdw1_budget0.2 | 114 | 0.18095238095238095 | 55.26315789473684 | 0.016815 | 21 |
| validation | phase1c_turnover_controlled | k30_a2_gap0.0_buf0.0_holdw2_budget0.2 | 110 | 0.1746031746031746 | 54.54545454545455 | 0.016225 | 21 |
| validation | phase1c_turnover_controlled | k30_a2_gap0.01_buf0.0_holdw0_budget0.2 | 114 | 0.18095238095238095 | 55.26315789473684 | 0.016815 | 21 |
| validation | phase1c_turnover_controlled | k30_a2_gap0.01_buf0.0_holdw1_budget0.2 | 114 | 0.18095238095238095 | 55.26315789473684 | 0.016815 | 21 |
| validation | phase1c_turnover_controlled | k30_a2_gap0.01_buf0.0_holdw2_budget0.2 | 110 | 0.1746031746031746 | 54.54545454545455 | 0.016225 | 21 |

## 12. regime diagnostic-only 分组结果

| split | regime | regime_usage | method | fee_tax_adjusted_net_return | max_drawdown | action_count | turnover_proxy | window_count |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| validation | caution | diagnostic_only | rank_rotate_top30 | 0.004951539132715288 | -0.056999340226068784 | 190 | 1.5833333333333335 | 4 |
| validation | normal | diagnostic_only | rank_rotate_top30 | 0.07867961803891044 | -0.060850677866397196 | 474 | 1.4363636363636363 | 11 |
| validation | risk_off | diagnostic_only | rank_rotate_top30 | 0.07381352765625016 | -0.16879018545608737 | 260 | 1.4444444444444446 | 6 |
| validation | caution | diagnostic_only | rank_rotate_top50 | 0.022765660344543193 | -0.05327522185785838 | 242 | 1.21 | 4 |
| validation | normal | diagnostic_only | rank_rotate_top50 | 0.06526180523090974 | -0.04715594627983544 | 674 | 1.2254545454545456 | 11 |
| validation | risk_off | diagnostic_only | rank_rotate_top50 | 0.06843527519538162 | -0.15938088516699012 | 368 | 1.2266666666666668 | 6 |
| validation | caution | diagnostic_only | phase1c_simple_topk_no_turnover | 0.019143165944999208 | -0.06169881103583441 | 176 | 1.4666666666666668 | 4 |
| validation | normal | diagnostic_only | phase1c_simple_topk_no_turnover | 0.12373265506916797 | -0.05579377205566971 | 394 | 1.1939393939393939 | 11 |
| validation | risk_off | diagnostic_only | phase1c_simple_topk_no_turnover | 0.07835800750283428 | -0.17016995029351045 | 244 | 1.3555555555555554 | 6 |
| independent_test | caution | diagnostic_only | rank_rotate_top30 | 0.5352929702698126 | 0.0 | 158 | 1.3166666666666664 | 4 |
| independent_test | normal | diagnostic_only | rank_rotate_top30 | 1.1209530406518322 | -0.05260466340556613 | 618 | 1.2875 | 16 |
| independent_test | risk_off | diagnostic_only | rank_rotate_top30 | 0.046719397031748766 | 0.0 | 44 | 1.4666666666666666 | 1 |
| independent_test | caution | diagnostic_only | rank_rotate_top50 | 0.5579544310311026 | 0.0 | 198 | 0.99 | 4 |
| independent_test | normal | diagnostic_only | rank_rotate_top50 | 0.9619546641751937 | -0.03471346316834045 | 904 | 1.1300000000000001 | 16 |
| independent_test | risk_off | diagnostic_only | rank_rotate_top50 | 0.04891191982561094 | 0.0 | 56 | 1.12 | 1 |
| independent_test | caution | diagnostic_only | phase1c_simple_topk_no_turnover | 0.5248924873000942 | 0.0 | 148 | 1.2333333333333334 | 4 |
| independent_test | normal | diagnostic_only | phase1c_simple_topk_no_turnover | 1.1691713041713094 | -0.051929830809715805 | 568 | 1.1833333333333333 | 16 |
| independent_test | risk_off | diagnostic_only | phase1c_simple_topk_no_turnover | 0.043281857983932026 | 0.0 | 34 | 1.1333333333333333 | 1 |
| validation | caution | diagnostic_only | phase1c_turnover_controlled | 0.12142294986016977 | -0.026452415859771983 | 18 | 0.15000000000000002 | 4 |
| validation | normal | diagnostic_only | phase1c_turnover_controlled | 0.1046991462208331 | -0.09770251092666782 | 66 | 0.2 | 11 |
| validation | risk_off | diagnostic_only | phase1c_turnover_controlled | 0.09829099429682353 | -0.16800409200994848 | 62 | 0.3444444444444444 | 6 |
| independent_test | caution | diagnostic_only | phase1c_turnover_controlled | 0.5516615101211393 | 0.0 | 24 | 0.2 | 4 |
| independent_test | normal | diagnostic_only | phase1c_turnover_controlled | 0.985462443363732 | -0.05747603476257801 | 114 | 0.23750000000000002 | 16 |
| independent_test | risk_off | diagnostic_only | phase1c_turnover_controlled | 0.08070795827022437 | 0.0 | 6 | 0.2 | 1 |

## 13. Gate 结论

`request_user_decision_route_b_tradeoff`

原因：Non-overlapping 10d replay produced a Route B tradeoff that requires user decision.

条件：`{'return_accounting_realistic_aligned': True, 'validation_net_improved': True, 'validation_turnover_reduced': True, 'validation_actions_reduced': True, 'validation_drawdown_not_worse': False, 'independent_no_net_reversal': False, 'independent_turnover_reduced': True, 'independent_actions_reduced': True, 'independent_drawdown_not_much_worse': True}`

## 14. 验证命令与结果

- `python -m py_compile scripts/evaluate_tw_ltr_phase3a1_return_accounting_repair.py`：通过。
- `python scripts/evaluate_tw_ltr_phase3a1_return_accounting_repair.py`：通过。

## 15. 禁止事项遵守情况

本轮未重新训练 LTR，未重建 Phase1C score，未调整 Phase1C score，未重新选择 Phase1C candidate，未重新打开 Phase2 regime gate，未使用 regime 控制组合，未新增数据源，未联网，未 provider refresh / publish，未 accepted latest switching，未改 frontend / API / monitor / database，未接 broker / quick-trade / orders / target position / target weight，未输出买入、卖出、持有、仓位建议、收益承诺、胜率或上涨概率语义，未做真实交易动作。

## 16. 需审查者检查

- 非重叠 10 日窗口是否满足 Phase3A1 return accounting 修复要求。
- 窗口级 cost / turnover / holding 口径是否可接受。
- blocked baseline 是否仍符合 fixed frozen artifact 边界。
- gate 是否可进入下一步，或需要用户对 Route B tradeoff 做决策。
