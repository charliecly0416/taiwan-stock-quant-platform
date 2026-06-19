# Phase 2 Rules Baseline 执行报告

- 生成时间：`2026-06-11T10:46:50+00:00`
- 执行范围：基于 repaired Phase1B Full 样本的只读规则型风险过滤 baseline。
- 禁止范围：未联网、未使用 token、未重拉数据、未新增数据源、未训练模型、未写 provider、未 refresh/publish、未 accepted latest switching、未前端/API、未交易相关操作。
- Phase2 gate：`request_phase2b_rule_repair=true`
- gate 理由：存在一条非辅助风险规则具备局部有效性，但辅助确认规则不能单独支撑 Phase3，且部分规则存在 2025 或跨年反向，需要修正规则或缩小适用范围。

## 1. 输入与 PIT

- 样本：`data_tw/experiments/decision_orthogonal/phase1b_repaired_full_samples.parquet`
- 样本行数：`106440`
- 样本 asof：`2022-01-04` 至 `2026-05-29`
- repair prediction days：`481` / `481`
- schema prediction selection：`latest duplicate by asof/symbol after sorting; repaired 2023-2024 asof-aware batch has highest priority, pred_fast has lowest priority`
- PIT 口径沿用 Phase1B：法人/融资字段只取 `available_at <= asof` 最近一笔；本阶段不引入新字段。

## 2. 规则定义

| rule_id | status | scope | description | selected_expr | excluded_expr |
|---|---|---|---|---|---|
| margin_crowding_caution_top50 | caution_watch | qlib Top50 | qlib Top50 且融资余额 20 日均值处于当日横截面高分位，识别融资拥挤风险。 | top50_flag and margin_balance_20d_mean_cs_rank_pct >= 0.80 | top50_flag and margin_balance_20d_mean_cs_rank_pct < 0.80 |
| margin_change_confirmation_top150 | confirmation_auxiliary | qlib Top150 | qlib Top150 且融资余额 20 日变化处于高分位，仅作为辅助确认，不单独形成强结论。 | top150_flag and margin_balance_change_20d_sum_cs_rank_pct >= 0.80 | top150_flag and margin_balance_change_20d_sum_cs_rank_pct < 0.80 |
| foreign_flow_confirmed_candidate_top150 | confirmed_watch_candidate | qlib Top150 | qlib Top150 且外资 10/20 日连续买超分位较高，作为多源确认候选，不是买入建议。 | top150_flag and (foreign_net_buy_10d_sum_cs_rank_pct >= 0.80 or foreign_net_buy_20d_sum_cs_rank_pct >= 0.80) | top150_flag and not (foreign_net_buy_10d_sum_cs_rank_pct >= 0.80 or foreign_net_buy_20d_sum_cs_rank_pct >= 0.80) |
| flow_crowding_conflict_top50 | review_watch | qlib Top50 | qlib Top50 但融资拥挤较高，同时外资和自营商 20 日流向偏弱，识别法人/融资冲突。 | top50_flag and margin_balance_20d_mean_cs_rank_pct >= 0.80 and foreign_net_buy_20d_sum_cs_rank_pct <= 0.40 and dealer_net_buy_20d_sum_cs_rank_pct <= 0.40 | top50_flag and not (margin_balance_20d_mean_cs_rank_pct >= 0.80 and foreign_net_buy_20d_sum_cs_rank_pct <= 0.40 and dealer_net_buy_20d_sum_cs_rank_pct <= 0.40) |

## 3. 20d 对照摘要

- `historical_positive_rate` 仅为历史样本统计，不代表未来胜率或收益承诺。
| rule_id | group | coverage_rows | coverage_days | coverage_symbols | mean | median | downside_q10 | worst_decile_mean | historical_positive_rate |
|---|---|---|---|---|---|---|---|---|---|
| baseline | baseline_top50 | 51599 | 1063 | 103 | 0.025458 | 0.003448 | -0.114664 | -0.165363 | 0.515120 |
| baseline | baseline_top150 | 106440 | 1063 | 103 | 0.020705 | 0.000495 | -0.113525 | -0.161908 | 0.502197 |
| margin_crowding_caution_top50 | rule_selected | 9652 | 1063 | 45 | 0.016215 | -0.009081 | -0.116062 | -0.167205 | 0.459228 |
| margin_crowding_caution_top50 | rule_excluded | 41947 | 1063 | 95 | 0.027597 | 0.006476 | -0.114371 | -0.164919 | 0.528058 |
| margin_change_confirmation_top150 | rule_selected | 21944 | 1063 | 102 | 0.029810 | 0.002718 | -0.116337 | -0.164655 | 0.510608 |
| margin_change_confirmation_top150 | rule_excluded | 84496 | 1063 | 103 | 0.018340 | 0.000002 | -0.112748 | -0.161169 | 0.500012 |
| foreign_flow_confirmed_candidate_top150 | rule_selected | 28512 | 1063 | 102 | 0.019940 | 0.000107 | -0.109994 | -0.159892 | 0.500431 |
| foreign_flow_confirmed_candidate_top150 | rule_excluded | 77928 | 1063 | 103 | 0.020986 | 0.000649 | -0.114503 | -0.162600 | 0.502845 |
| flow_crowding_conflict_top50 | rule_selected | 2055 | 835 | 41 | 0.009239 | -0.008439 | -0.110659 | -0.154811 | 0.459179 |
| flow_crowding_conflict_top50 | rule_excluded | 49544 | 1063 | 103 | 0.026137 | 0.003990 | -0.114835 | -0.165787 | 0.517461 |

## 4. Turnover Proxy

| group | days | mean_daily_member_count | mean_daily_symmetric_change | median_daily_symmetric_change | mean_jaccard_with_previous_day |
|---|---|---|---|---|---|
| baseline_top50 | 1063 | 48.540922 | 36.698682 | 37.000000 | 0.455652 |
| baseline_top150 | 1063 | 100.131703 | 0.006591 | 0.000000 | 0.999934 |
| margin_crowding_caution_top50__selected | 1063 | 9.079962 | 7.481168 | 7.000000 | 0.424127 |
| margin_crowding_caution_top50__excluded | 1063 | 39.460960 | 29.307910 | 29.000000 | 0.462187 |
| margin_change_confirmation_top150__selected | 1063 | 20.643462 | 5.965160 | 6.000000 | 0.753029 |
| margin_change_confirmation_top150__excluded | 1063 | 79.488241 | 5.971751 | 6.000000 | 0.928111 |
| foreign_flow_confirmed_candidate_top150__selected | 1063 | 26.822201 | 5.985876 | 6.000000 | 0.804555 |
| foreign_flow_confirmed_candidate_top150__excluded | 1063 | 73.309501 | 5.990584 | 6.000000 | 0.921676 |
| flow_crowding_conflict_top50__selected | 835 | 2.461078 | 2.679856 | 2.000000 | 0.325207 |
| flow_crowding_conflict_top50__excluded | 1063 | 46.607714 | 35.119586 | 35.000000 | 0.456769 |

## 5. 年度分段与 2025 反向年份

- 2025 年单独列出，用于审查 margin balance 方向反转风险。
| rule_id | group | coverage_rows | coverage_days | mean | downside_q10 | historical_positive_rate |
|---|---|---|---|---|---|---|
| margin_crowding_caution_top50 | rule_selected | 2217 | 242 | 0.047555 | -0.108392 | 0.527740 |
| margin_crowding_caution_top50 | rule_excluded | 9689 | 242 | 0.024137 | -0.126068 | 0.515946 |
| margin_change_confirmation_top150 | rule_selected | 5082 | 242 | 0.046995 | -0.108548 | 0.537190 |
| margin_change_confirmation_top150 | rule_excluded | 19491 | 242 | 0.019332 | -0.124227 | 0.494587 |
| foreign_flow_confirmed_candidate_top150 | rule_selected | 6569 | 242 | 0.036745 | -0.109029 | 0.536002 |
| foreign_flow_confirmed_candidate_top150 | rule_excluded | 18004 | 242 | 0.020788 | -0.124921 | 0.491502 |
| flow_crowding_conflict_top50 | rule_selected | 388 | 183 | 0.041605 | -0.095002 | 0.536082 |
| flow_crowding_conflict_top50 | rule_excluded | 11518 | 242 | 0.028056 | -0.123775 | 0.517538 |

## 6. 季度分段摘要

| rule_id | segment | coverage_rows | coverage_days | mean | downside_q10 | historical_positive_rate |
|---|---|---|---|---|---|---|
| flow_crowding_conflict_top50 | 2025Q4 | 83 | 44 | 0.142556 | -0.074526 | 0.650602 |
| flow_crowding_conflict_top50 | 2026Q1 | 142 | 46 | 0.069187 | -0.195703 | 0.591549 |
| flow_crowding_conflict_top50 | 2024Q4 | 137 | 55 | -0.049714 | -0.146773 | 0.255474 |
| flow_crowding_conflict_top50 | 2024Q1 | 62 | 38 | -0.045497 | -0.135489 | 0.258065 |
| foreign_flow_confirmed_candidate_top150 | 2025Q4 | 1618 | 62 | 0.062404 | -0.109861 | 0.558096 |
| foreign_flow_confirmed_candidate_top150 | 2023Q2 | 1484 | 59 | 0.060219 | -0.064181 | 0.590970 |
| foreign_flow_confirmed_candidate_top150 | 2026Q2 | 1068 | 40 | 0.056391 | -0.210131 | 0.522959 |
| foreign_flow_confirmed_candidate_top150 | 2025Q3 | 1710 | 64 | 0.055658 | -0.109985 | 0.504094 |
| margin_change_confirmation_top150 | 2023Q2 | 1181 | 59 | 0.105036 | -0.090970 | 0.624047 |
| margin_change_confirmation_top150 | 2026Q2 | 840 | 40 | 0.084473 | -0.179226 | 0.510204 |
| margin_change_confirmation_top150 | 2025Q4 | 1302 | 62 | 0.081012 | -0.088391 | 0.572197 |
| margin_change_confirmation_top150 | 2025Q3 | 1344 | 64 | 0.077264 | -0.119174 | 0.590774 |
| margin_crowding_caution_top50 | 2025Q4 | 603 | 62 | 0.097481 | -0.086844 | 0.588723 |
| margin_crowding_caution_top50 | 2023Q2 | 527 | 59 | 0.089770 | -0.074315 | 0.510436 |
| margin_crowding_caution_top50 | 2025Q3 | 579 | 64 | 0.062188 | -0.124643 | 0.533679 |
| margin_crowding_caution_top50 | 2024Q4 | 563 | 62 | -0.025546 | -0.123299 | 0.323268 |

## 7. Rule Gate 明细

| rule_id | status | selected_20d_mean | excluded_20d_mean | baseline_20d_mean | selected_20d_downside_q10 | excluded_20d_downside_q10 | baseline_20d_downside_q10 | coverage_days | year_direction_share | reverse_years | passes_rule_baseline_check | counts_for_phase3_gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| margin_crowding_caution_top50 | caution_watch | 0.016215 | 0.027597 | 0.025458 | -0.116062 | -0.114371 | -0.114664 | 1063.000000 | 0.800000 | ['2025'] | True | True |
| margin_change_confirmation_top150 | confirmation_auxiliary | 0.029810 | 0.018340 | 0.020705 | -0.116337 | -0.112748 | -0.113525 | 1063.000000 | 0.800000 | ['2022'] | True | False |
| foreign_flow_confirmed_candidate_top150 | confirmed_watch_candidate | 0.019940 | 0.020986 | 0.020705 | -0.109994 | -0.114503 | -0.113525 | 1063.000000 | 0.400000 | ['2022', '2023', '2026'] | False | False |
| flow_crowding_conflict_top50 | review_watch | 0.009239 | 0.026137 | 0.025458 | -0.110659 | -0.114835 | -0.114664 | 835.000000 | 0.800000 | ['2025'] | False | False |

## 8. 产物

- 规则定义：`data_tw/experiments/decision_orthogonal/phase2_rules_definitions.json`
- 全样本组指标：`data_tw/experiments/decision_orthogonal/phase2_rules_group_metrics.csv`
- 年度/季度分段指标：`data_tw/experiments/decision_orthogonal/phase2_rules_segment_metrics.csv`
- 每日 membership：`data_tw/experiments/decision_orthogonal/phase2_rules_daily_membership.csv`
- turnover proxy：`data_tw/experiments/decision_orthogonal/phase2_rules_turnover_summary.csv`
- gate summary：`data_tw/experiments/decision_orthogonal/phase2_rules_gate_summary.json`

## 9. 是否请求下一阶段

- `request_phase2b_rule_repair=true`
- 即使 gate 请求 Phase3，也必须等待审查者授权；本阶段没有训练 Risk Filter Model。

## 10. 风险与待审查问题

- 规则阈值使用简单横截面分位数，未做参数搜索；若审查者认为稳定性不足，应进入 Phase2B 修正规则，而不是直接训练模型。
- `available_at = next_trading_day(trade_date)` 仍是 conservative visibility proxy，不是官方发布时间证明。
- 外资/融资确认类规则只作为研究状态，不构成买入/卖出建议。
