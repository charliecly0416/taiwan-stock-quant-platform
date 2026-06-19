# Phase 2B Rule Repair 执行报告

- 生成时间：`2026-06-11T10:57:02+00:00`
- 执行范围：基于 Phase1B/Phase2 本地产物的小范围可解释规则修正。
- 禁止范围：未联网、未使用 token、未重拉数据、未新增数据源、未月营收、未训练模型、未 Risk Filter Model、未写 provider、未 refresh/publish、未 accepted latest switching、未前端/API、未交易相关操作。
- Phase2B gate：`request_phase2c_manual_rule_freeze=true`
- gate 理由：修正规则仍不足以进入模型训练，但存在一条可解释风险过滤规则适合冻结为人工解释规则。

## 1. 输入与边界

- 样本：`data_tw/experiments/decision_orthogonal/phase1b_repaired_full_samples.parquet`，行数 `106440`，asof `2022-01-04` 至 `2026-05-29`。
- 本阶段只读 Phase1B repaired full 与 Phase2 rules 产物，不引入新字段。
- 阈值候选固定且少量：0.85/0.90、Top20/30/50、weak flow 0.30；没有大规模参数搜索。

## 2. 修正规则定义

| rule_id | status | rule_family | description | selected_expr | baseline_group | counts_for_gate |
|---|---|---|---|---|---|---|
| margin_crowding_top50_p85_caution | caution_watch | margin_crowding_refinement | Top50 且融资余额 20 日均值分位 >= 0.85，较 Phase2 p80 缩小拥挤定义。 | top50_flag and margin_balance_20d_mean_cs_rank_pct >= 0.85 | baseline_top50 | True |
| margin_crowding_top50_p90_caution | caution_watch | margin_crowding_refinement | Top50 且融资余额 20 日均值分位 >= 0.90，测试更极端融资拥挤。 | top50_flag and margin_balance_20d_mean_cs_rank_pct >= 0.90 | baseline_top50 | True |
| margin_crowding_top30_p85_caution | caution_watch | margin_crowding_refinement | Top30 且融资余额 20 日均值分位 >= 0.85，测试更靠前 qlib rank band。 | qlib_rank <= 30 and margin_balance_20d_mean_cs_rank_pct >= 0.85 | baseline_top50 | True |
| margin_crowding_top20_p85_caution | caution_watch | margin_crowding_refinement | Top20 且融资余额 20 日均值分位 >= 0.85，测试最前段 qlib rank band。 | qlib_rank <= 20 and margin_balance_20d_mean_cs_rank_pct >= 0.85 | baseline_top50 | True |
| flow_crowding_conflict_top50_p85_weak30_review | review_watch | flow_crowding_conflict_refinement | Top50、融资拥挤 >= 0.85，且外资/自营商 20 日流向分位均 <= 0.30。 | top50_flag and margin_balance_20d_mean_cs_rank_pct >= 0.85 and foreign_net_buy_20d_sum_cs_rank_pct <= 0.30 and dealer_net_buy_20d_sum_cs_rank_pct <= 0.30 | baseline_top50 | True |
| flow_crowding_conflict_top50_p80_weak30_review | review_watch | flow_crowding_conflict_refinement | Top50、融资拥挤 >= 0.80，且外资/自营商 20 日流向分位均 <= 0.30。 | top50_flag and margin_balance_20d_mean_cs_rank_pct >= 0.80 and foreign_net_buy_20d_sum_cs_rank_pct <= 0.30 and dealer_net_buy_20d_sum_cs_rank_pct <= 0.30 | baseline_top50 | True |
| foreign_flow_non_crowded_top150_explanation | explanation_feature | foreign_flow_downgrade | Top150 外资 10/20 日高分位且融资拥挤 < 0.80；仅保留为解释字段，不作为 confirmed watch。 | top150_flag and (foreign_net_buy_10d_sum_cs_rank_pct >= 0.80 or foreign_net_buy_20d_sum_cs_rank_pct >= 0.80) and margin_balance_20d_mean_cs_rank_pct < 0.80 | baseline_top150 | False |
| margin_change_non_crowded_top150_auxiliary | confirmation_auxiliary | margin_change_auxiliary_refinement | Top150 融资变化高分位且融资余额拥挤 < 0.80；仅作为辅助确认。 | top150_flag and margin_balance_change_20d_sum_cs_rank_pct >= 0.80 and margin_balance_20d_mean_cs_rank_pct < 0.80 | baseline_top150 | False |

## 3. 20d 全样本对照

- `historical_positive_rate` 仅为历史样本统计，不代表未来胜率或收益承诺。
| rule_id | group | coverage_rows | coverage_days | coverage_symbols | mean | median | downside_q10 | worst_decile_mean | historical_positive_rate |
|---|---|---|---|---|---|---|---|---|---|
| baseline | baseline_top50 | 51599 | 1063 | 103 | 0.025458 | 0.003448 | -0.114664 | -0.165363 | 0.515120 |
| baseline | baseline_top150 | 106440 | 1063 | 103 | 0.020705 | 0.000495 | -0.113525 | -0.161908 | 0.502197 |
| margin_crowding_top50_p85_caution | rule_selected | 7321 | 1063 | 35 | 0.013156 | -0.010893 | -0.116822 | -0.168010 | 0.453723 |
| margin_crowding_top50_p85_caution | rule_excluded | 44278 | 1063 | 98 | 0.027508 | 0.005847 | -0.114333 | -0.164900 | 0.525351 |
| margin_crowding_top50_p90_caution | rule_selected | 5019 | 1060 | 27 | 0.013014 | -0.012162 | -0.119976 | -0.170511 | 0.448830 |
| margin_crowding_top50_p90_caution | rule_excluded | 46580 | 1063 | 101 | 0.026805 | 0.005045 | -0.114140 | -0.164760 | 0.522299 |
| margin_crowding_top30_p85_caution | rule_selected | 4301 | 1049 | 35 | 0.017125 | -0.012443 | -0.123726 | -0.177268 | 0.452821 |
| margin_crowding_top30_p85_caution | rule_excluded | 26513 | 1063 | 98 | 0.032355 | 0.008708 | -0.117199 | -0.169421 | 0.534242 |
| margin_crowding_top20_p85_caution | rule_selected | 2734 | 1002 | 35 | 0.023687 | -0.009509 | -0.129052 | -0.182539 | 0.468458 |
| margin_crowding_top20_p85_caution | rule_excluded | 17733 | 1063 | 98 | 0.035550 | 0.010167 | -0.118662 | -0.171750 | 0.537410 |
| flow_crowding_conflict_top50_p85_weak30_review | rule_selected | 1473 | 744 | 31 | 0.010271 | -0.007309 | -0.104859 | -0.152387 | 0.464286 |
| flow_crowding_conflict_top50_p85_weak30_review | rule_excluded | 50126 | 1063 | 103 | 0.025911 | 0.003800 | -0.115014 | -0.165707 | 0.516635 |
| flow_crowding_conflict_top50_p80_weak30_review | rule_selected | 1798 | 797 | 41 | 0.008129 | -0.009571 | -0.107884 | -0.153551 | 0.452435 |
| flow_crowding_conflict_top50_p80_weak30_review | rule_excluded | 49801 | 1063 | 103 | 0.026088 | 0.003976 | -0.114967 | -0.165768 | 0.517401 |
| foreign_flow_non_crowded_top150_explanation | rule_selected | 18257 | 1063 | 94 | 0.025422 | 0.007338 | -0.105842 | -0.157934 | 0.531433 |
| foreign_flow_non_crowded_top150_explanation | rule_excluded | 88183 | 1063 | 103 | 0.019722 | -0.000917 | -0.114646 | -0.162626 | 0.496104 |
| margin_change_non_crowded_top150_auxiliary | rule_selected | 13884 | 1063 | 94 | 0.033365 | 0.009357 | -0.113039 | -0.161386 | 0.535891 |
| margin_change_non_crowded_top150_auxiliary | rule_excluded | 92556 | 1063 | 103 | 0.018803 | -0.000624 | -0.113561 | -0.161987 | 0.497134 |

## 4. 2025 单独分段

| rule_id | group | coverage_rows | coverage_days | mean | downside_q10 | historical_positive_rate |
|---|---|---|---|---|---|---|
| baseline | baseline_top50 | 11906 | 242 | 0.028497 | -0.122536 | 0.518142 |
| baseline | baseline_top150 | 24573 | 242 | 0.025053 | -0.121175 | 0.503398 |
| margin_crowding_top50_p85_caution | rule_selected | 1692 | 242 | 0.055433 | -0.107749 | 0.541371 |
| margin_crowding_top50_p85_caution | rule_excluded | 10214 | 242 | 0.024035 | -0.125341 | 0.514294 |
| margin_crowding_top50_p90_caution | rule_selected | 1199 | 241 | 0.068355 | -0.109042 | 0.563803 |
| margin_crowding_top50_p90_caution | rule_excluded | 10707 | 242 | 0.024034 | -0.124208 | 0.513029 |
| margin_crowding_top30_p85_caution | rule_selected | 1022 | 240 | 0.064104 | -0.112214 | 0.545010 |
| margin_crowding_top30_p85_caution | rule_excluded | 6110 | 242 | 0.029308 | -0.131177 | 0.529296 |
| margin_crowding_top20_p85_caution | rule_selected | 680 | 230 | 0.076207 | -0.116008 | 0.570588 |
| margin_crowding_top20_p85_caution | rule_excluded | 4069 | 242 | 0.033052 | -0.131894 | 0.528385 |
| flow_crowding_conflict_top50_p85_weak30_review | rule_selected | 319 | 167 | 0.042092 | -0.091377 | 0.536050 |
| flow_crowding_conflict_top50_p85_weak30_review | rule_excluded | 11587 | 242 | 0.028123 | -0.123580 | 0.517649 |
| flow_crowding_conflict_top50_p80_weak30_review | rule_selected | 346 | 173 | 0.040979 | -0.095305 | 0.540462 |
| flow_crowding_conflict_top50_p80_weak30_review | rule_excluded | 11560 | 242 | 0.028124 | -0.123710 | 0.517474 |
| foreign_flow_non_crowded_top150_explanation | rule_selected | 4123 | 242 | 0.029594 | -0.113870 | 0.538685 |
| foreign_flow_non_crowded_top150_explanation | rule_excluded | 20450 | 242 | 0.024138 | -0.122324 | 0.496284 |
| margin_change_non_crowded_top150_auxiliary | rule_selected | 3096 | 242 | 0.037624 | -0.105239 | 0.535853 |
| margin_change_non_crowded_top150_auxiliary | rule_excluded | 21477 | 242 | 0.023241 | -0.123489 | 0.498720 |

## 5. 季度分段摘要

| rule_id | segment | coverage_rows | coverage_days | mean | downside_q10 | historical_positive_rate |
|---|---|---|---|---|---|---|
| flow_crowding_conflict_top50_p80_weak30_review | 2025Q4 | 79 | 41 | 0.140928 | -0.075732 | 0.645570 |
| flow_crowding_conflict_top50_p80_weak30_review | 2026Q1 | 130 | 45 | 0.055937 | -0.204386 | 0.569231 |
| flow_crowding_conflict_top50_p80_weak30_review | 2024Q1 | 51 | 35 | -0.049903 | -0.122220 | 0.196078 |
| flow_crowding_conflict_top50_p85_weak30_review | 2025Q4 | 75 | 40 | 0.142519 | -0.075897 | 0.626667 |
| flow_crowding_conflict_top50_p85_weak30_review | 2024Q1 | 41 | 30 | -0.066987 | -0.135634 | 0.170732 |
| flow_crowding_conflict_top50_p85_weak30_review | 2024Q4 | 90 | 48 | -0.030038 | -0.109606 | 0.333333 |
| foreign_flow_non_crowded_top150_explanation | 2026Q2 | 629 | 40 | 0.090995 | -0.180856 | 0.632959 |
| foreign_flow_non_crowded_top150_explanation | 2023Q2 | 933 | 59 | 0.063600 | -0.056785 | 0.642015 |
| foreign_flow_non_crowded_top150_explanation | 2023Q3 | 1274 | 63 | 0.056720 | -0.075377 | 0.643642 |
| margin_change_non_crowded_top150_auxiliary | 2026Q2 | 543 | 40 | 0.125602 | -0.136821 | 0.598131 |
| margin_change_non_crowded_top150_auxiliary | 2023Q2 | 791 | 59 | 0.096571 | -0.095907 | 0.666245 |
| margin_change_non_crowded_top150_auxiliary | 2026Q1 | 629 | 55 | 0.091170 | -0.154390 | 0.553259 |
| margin_crowding_top20_p85_caution | 2023Q2 | 117 | 54 | 0.162568 | -0.078527 | 0.606838 |
| margin_crowding_top20_p85_caution | 2025Q4 | 217 | 61 | 0.135159 | -0.082199 | 0.635945 |
| margin_crowding_top20_p85_caution | 2025Q3 | 159 | 62 | 0.119097 | -0.139332 | 0.616352 |
| margin_crowding_top30_p85_caution | 2025Q4 | 299 | 62 | 0.126475 | -0.087796 | 0.608696 |
| margin_crowding_top30_p85_caution | 2023Q2 | 192 | 59 | 0.120594 | -0.077114 | 0.541667 |
| margin_crowding_top30_p85_caution | 2025Q3 | 245 | 64 | 0.081598 | -0.144734 | 0.551020 |
| margin_crowding_top50_p85_caution | 2025Q4 | 473 | 62 | 0.108400 | -0.086601 | 0.583510 |
| margin_crowding_top50_p85_caution | 2023Q2 | 368 | 59 | 0.077599 | -0.077557 | 0.508152 |
| margin_crowding_top50_p85_caution | 2025Q3 | 425 | 64 | 0.066389 | -0.125913 | 0.550588 |
| margin_crowding_top50_p90_caution | 2025Q4 | 364 | 62 | 0.124378 | -0.087275 | 0.612637 |
| margin_crowding_top50_p90_caution | 2025Q3 | 285 | 63 | 0.104441 | -0.119597 | 0.603509 |
| margin_crowding_top50_p90_caution | 2023Q2 | 243 | 59 | 0.096543 | -0.081799 | 0.534979 |

## 6. Turnover Proxy

| group | days | mean_daily_member_count | mean_daily_symmetric_change | median_daily_symmetric_change | mean_jaccard_with_previous_day |
|---|---|---|---|---|---|
| baseline_top50 | 1063 | 48.540922 | 36.698682 | 37.000000 | 0.455652 |
| baseline_top150 | 1063 | 100.131703 | 0.006591 | 0.000000 | 0.999934 |
| margin_crowding_top50_p85_caution__selected | 1063 | 6.887112 | 5.647834 | 6.000000 | 0.425606 |
| margin_crowding_top50_p90_caution__selected | 1060 | 4.734906 | 3.860246 | 4.000000 | 0.429178 |
| margin_crowding_top30_p85_caution__selected | 1049 | 4.100095 | 4.278626 | 4.000000 | 0.328379 |
| margin_crowding_top20_p85_caution__selected | 1002 | 2.728543 | 3.075924 | 3.000000 | 0.303444 |
| flow_crowding_conflict_top50_p85_weak30_review__selected | 744 | 1.979839 | 2.087483 | 2.000000 | 0.365283 |
| flow_crowding_conflict_top50_p80_weak30_review__selected | 797 | 2.255960 | 2.430905 | 2.000000 | 0.338714 |
| foreign_flow_non_crowded_top150_explanation__selected | 1063 | 17.174976 | 4.347458 | 4.000000 | 0.782638 |
| margin_change_non_crowded_top150_auxiliary__selected | 1063 | 13.061148 | 4.193032 | 4.000000 | 0.730736 |

## 7. 相对 Phase2 原规则改善与 Gate

| rule_id | status | selected_20d_mean | excluded_20d_mean | baseline_20d_mean | selected_20d_downside_q10 | baseline_20d_downside_q10 | coverage_days | year_direction_share | reverse_years | y2025_aligned | phase2_original_selected_20d_mean | phase2_original_selected_20d_downside_q10 | passes_phase2b_gate_check | eligible_manual_freeze |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| margin_crowding_top50_p85_caution | caution_watch | 0.013156 | 0.027508 | 0.025458 | -0.116822 | -0.114664 | 1063.000000 | 0.800000 | ['2025'] | False | 0.016215 | -0.116062 | False | True |
| margin_crowding_top50_p90_caution | caution_watch | 0.013014 | 0.026805 | 0.025458 | -0.119976 | -0.114664 | 1060.000000 | 0.800000 | ['2025'] | False | 0.016215 | -0.116062 | False | True |
| margin_crowding_top30_p85_caution | caution_watch | 0.017125 | 0.032355 | 0.025458 | -0.123726 | -0.114664 | 1049.000000 | 0.800000 | ['2025'] | False | 0.016215 | -0.116062 | False | True |
| margin_crowding_top20_p85_caution | caution_watch | 0.023687 | 0.035550 | 0.025458 | -0.129052 | -0.114664 | 1002.000000 | 0.800000 | ['2025'] | False | 0.016215 | -0.116062 | False | True |
| flow_crowding_conflict_top50_p85_weak30_review | review_watch | 0.010271 | 0.025911 | 0.025458 | -0.104859 | -0.114664 | 744.000000 | 0.800000 | ['2025'] | False | 0.009239 | -0.110659 | False | True |
| flow_crowding_conflict_top50_p80_weak30_review | review_watch | 0.008129 | 0.026088 | 0.025458 | -0.107884 | -0.114664 | 797.000000 | 0.800000 | ['2025'] | False | 0.009239 | -0.110659 | False | True |
| foreign_flow_non_crowded_top150_explanation | explanation_feature | 0.025422 | 0.019722 | 0.020705 | -0.105842 | -0.113525 | 1063.000000 | 1.000000 | [] | True | nan | nan | False | False |
| margin_change_non_crowded_top150_auxiliary | confirmation_auxiliary | 0.033365 | 0.018803 | 0.020705 | -0.113039 | -0.113525 | 1063.000000 | 1.000000 | [] | True | nan | nan | False | False |

## 8. 结论

- `request_phase2c_manual_rule_freeze=true`
- 即使 gate 请求 Phase3，也必须等待审查者授权；本阶段没有训练模型。
- 若审查者接受 manual freeze，建议只把可解释风险规则冻结为人工解释标签，而不是进入自动模型训练。

## 9. 产物

- 规则定义：`data_tw/experiments/decision_orthogonal/phase2b_rules_definitions.json`
- 全样本指标：`data_tw/experiments/decision_orthogonal/phase2b_rules_group_metrics.csv`
- 年度/季度指标：`data_tw/experiments/decision_orthogonal/phase2b_rules_segment_metrics.csv`
- turnover：`data_tw/experiments/decision_orthogonal/phase2b_rules_turnover_summary.csv`
- 候选对照：`data_tw/experiments/decision_orthogonal/phase2b_rules_candidate_comparison.csv`
- gate summary：`data_tw/experiments/decision_orthogonal/phase2b_rules_gate_summary.json`

## 10. 风险与待审查问题

- 多数修正规则仍存在 2025 反向或 coverage 偏窄问题。
- foreign flow 已降级为 explanation feature，不再作为 confirmed watch 规则。
- margin change 仍只作为 auxiliary，不支撑 Phase3。
- `available_at = next_trading_day(trade_date)` 仍是 conservative visibility proxy，不是官方发布时间证明。
