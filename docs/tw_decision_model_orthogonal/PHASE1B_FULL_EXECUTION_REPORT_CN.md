# Phase 1B 执行报告：扩展窗口正交数据只读验证

- 生成时间：`2026-06-10T19:59:27+00:00`
- 指标模式：`full`
- 阶段结论：`request_phase2_rules_baseline=true`
- 结论理由：扩展窗口下存在多个分段同向、与 qlib score 低到中等相关且泄露审计为 0 的候选特征；仅请求审查者授权 Phase2，不自动进入。
- 本阶段没有联网、没有使用 token、没有重拉 Phase0E、没有写入 qlib/provider、没有训练模型、没有规则 baseline、没有进入 Phase2。
- 注：脚本文件写入时 `apply_patch` 受当前沙箱 bwrap loopback 限制失败，改用受控本地 Python 写入；该问题只影响编辑方式，不影响只读数据边界。

## 1. 输入与边界

- 输入限定为 Phase0E normalized PIT archive、本地 qlib ranking/score artifact、本地价格与 TWII。
- 未使用 Phase0E excluded tail rows。
- `available_at = next_trading_day(trade_date)` 仅作为 conservative visibility proxy，不是官方发布时间证明。

| category | symbol_count | row_count | first_trade_date | last_trade_date | archive_path |
|---|---|---|---|---|---|
| institutional_flow | 150 | 158834 | 2022-01-03 | 2026-05-29 | data_tw/experiments/decision_orthogonal/phase0e_raw_archive/institutional_flow/phase0e_institutional_flow_20260610T175901Z_normalized.csv |
| margin_short | 150 | 156021 | 2022-01-03 | 2026-05-29 | data_tw/experiments/decision_orthogonal/phase0e_raw_archive/margin_short/phase0e_margin_short_20260610T180330Z_normalized.csv |

## 2. 样本构建口径

- asof 范围：`2022-01-04` 至 `2026-05-29`
- Phase0E archive symbol 数：`150`
- 样本 symbol 数：`103`
- 样本行数：`58354`
- 因两类 PIT feature 未同时可见而排除行数：`1412`
- Top50 子集样本量：`28320`
- Top150 子集样本量：`58354`
- qlib prediction rows：`59766`；prediction file count：`633`
- PIT 可见性断言：`pass`；`available_at <= asof` 违反行见泄露审计。

### 每月样本量

| month | sample_rows | symbol_count | top50_rows | top150_rows | valid_pit_rows |
|---|---|---|---|---|---|
| 2022-01 | 1648 | 97 | 819 | 1648 | 1648 |
| 2022-02 | 1455 | 97 | 710 | 1455 | 1455 |
| 2022-03 | 2231 | 97 | 1107 | 2231 | 2231 |
| 2022-04 | 1843 | 97 | 893 | 1843 | 1843 |
| 2022-05 | 2037 | 97 | 988 | 2037 | 2037 |
| 2022-06 | 2051 | 98 | 984 | 2051 | 2051 |
| 2022-07 | 2058 | 98 | 988 | 2058 | 2058 |
| 2022-08 | 2258 | 99 | 1097 | 2258 | 2258 |
| 2022-09 | 2079 | 99 | 1005 | 2079 | 2079 |
| 2022-10 | 1980 | 99 | 949 | 1980 | 1980 |
| 2022-11 | 2178 | 99 | 1067 | 2178 | 2178 |
| 2022-12 | 2178 | 99 | 1057 | 2178 | 2178 |
| 2025-01 | 1515 | 101 | 735 | 1515 | 1515 |
| 2025-02 | 1919 | 101 | 934 | 1919 | 1919 |
| 2025-03 | 2121 | 101 | 1021 | 2121 | 2121 |
| 2025-04 | 2020 | 101 | 967 | 2020 | 2020 |
| 2025-05 | 2020 | 101 | 985 | 2020 | 2020 |
| 2025-06 | 2121 | 101 | 1014 | 2121 | 2121 |
| 2025-07 | 2328 | 102 | 1124 | 2328 | 2328 |
| 2025-08 | 2040 | 102 | 993 | 2040 | 2040 |
| 2025-09 | 2142 | 102 | 1044 | 2142 | 2142 |
| 2025-10 | 2040 | 102 | 995 | 2040 | 2040 |
| 2025-11 | 2041 | 103 | 994 | 2041 | 2041 |
| 2025-12 | 2266 | 103 | 1100 | 2266 | 2266 |
| 2026-01 | 2163 | 103 | 1050 | 2163 | 2163 |
| 2026-02 | 1236 | 103 | 600 | 1236 | 1236 |
| 2026-03 | 2266 | 103 | 1100 | 2266 | 2266 |
| 2026-04 | 2060 | 103 | 1000 | 2060 | 2060 |
| 2026-05 | 2060 | 103 | 1000 | 2060 | 2060 |

## 3. 标签

- 标签来自本地 `qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/normalized_nonempty/*.csv` 价格文件。
- 已生成 `fwd_5d_excess_return`、`fwd_10d_excess_return`、`fwd_20d_excess_return`，以个股 forward return 减 TWII forward return。
- forward label date 必须大于 asof，审计见 `phase1b_leakage_audit_report.md`。

## 4. 特征

- 法人字段：外资、投信、自营商与合计净买超；对各字段生成 5/10/20 日 rolling sum、rolling zscore 与横截面 rank pct。
- 融资融券字段：融资余额、融资变化、融券余额、融券变化；对余额生成 rolling mean/zscore，对变化生成 rolling sum/zscore，并生成横截面 rank pct。
- 每个样本点只取 `available_at <= asof` 的最近一笔 PIT row。

## 5. 单因子与分段稳定性

### 全样本 RankIC 摘要

| feature | label | n | valid_periods | value |
|---|---|---|---|---|
| dealer_net_buy_5d_sum_cs_rank_pct | fwd_5d_excess_return | 57221 | 571 | 0.034026 |
| dealer_net_buy_5d_sum | fwd_5d_excess_return | 57221 | 571 | 0.034026 |
| margin_balance_change_20d_sum | fwd_10d_excess_return | 56706 | 566 | 0.031844 |
| margin_balance_change_20d_sum_cs_rank_pct | fwd_10d_excess_return | 56706 | 566 | 0.031844 |
| margin_balance_change_10d_sum | fwd_20d_excess_return | 55676 | 556 | 0.031775 |
| margin_balance_change_10d_sum_cs_rank_pct | fwd_20d_excess_return | 55676 | 556 | 0.031775 |
| margin_balance_change_20d_sum_cs_rank_pct | fwd_20d_excess_return | 55676 | 556 | 0.030112 |
| margin_balance_change_20d_sum | fwd_20d_excess_return | 55676 | 556 | 0.030112 |
| dealer_net_buy_5d_sum | fwd_10d_excess_return | 56706 | 566 | 0.028334 |
| dealer_net_buy_5d_sum_cs_rank_pct | fwd_10d_excess_return | 56706 | 566 | 0.028334 |
| dealer_net_buy_10d_sum_cs_rank_pct | fwd_5d_excess_return | 57221 | 571 | 0.026336 |
| dealer_net_buy_10d_sum | fwd_5d_excess_return | 57221 | 571 | 0.026336 |
| dealer_net_buy_10d_sum_cs_rank_pct | fwd_10d_excess_return | 56706 | 566 | 0.024794 |
| dealer_net_buy_10d_sum | fwd_10d_excess_return | 56706 | 566 | 0.024794 |
| dealer_net_buy_5d_sum | fwd_20d_excess_return | 55676 | 556 | 0.023427 |
| dealer_net_buy_5d_sum_cs_rank_pct | fwd_20d_excess_return | 55676 | 556 | 0.023427 |
| dealer_net_buy_20d_sum | fwd_5d_excess_return | 57221 | 571 | 0.023051 |
| dealer_net_buy_20d_sum_cs_rank_pct | fwd_5d_excess_return | 57221 | 571 | 0.023051 |
| margin_balance_change_5d_sum_cs_rank_pct | fwd_20d_excess_return | 55676 | 556 | 0.022082 |
| margin_balance_change_5d_sum | fwd_20d_excess_return | 55676 | 556 | 0.022082 |

### 年度/季度/月度分段

- 分段指标输出：`data_tw/experiments/decision_orthogonal/phase1b_full_segment_metrics.csv`
- hit-rate 只作为历史样本统计，不代表未来胜率或收益承诺。

## 6. 与 qlib 排名关系

- 已计算正交特征与 `qlib_score_raw`、`qlib_rank`、`qlib_score_percentile_by_date` 的 Spearman 相关。
- 已对 qlib Top50/Top150 内外分别计算特征 high-low 与历史正样本比例。

| feature | label | n | value |
|---|---|---|---|
| institutional_total_net_buy_10d_sum | qlib_score_raw | 58354 | 0.205815 |
| institutional_total_net_buy_20d_sum | qlib_score_raw | 58354 | 0.198063 |
| institutional_total_net_buy_10d_sum | qlib_score_percentile_by_date | 58354 | 0.195065 |
| institutional_total_net_buy_10d_sum | qlib_rank | 58354 | -0.194652 |
| institutional_total_net_buy_10d_sum_cs_rank_pct | qlib_score_percentile_by_date | 58354 | 0.189907 |
| institutional_total_net_buy_10d_sum_cs_rank_pct | qlib_rank | 58354 | -0.189897 |
| institutional_total_net_buy_20d_sum | qlib_score_percentile_by_date | 58354 | 0.184967 |
| institutional_total_net_buy_20d_sum | qlib_rank | 58354 | -0.184497 |
| institutional_total_net_buy_10d_sum_cs_rank_pct | qlib_score_raw | 58354 | 0.183410 |
| institutional_total_net_buy_20d_sum_cs_rank_pct | qlib_score_percentile_by_date | 58354 | 0.179019 |
| institutional_total_net_buy_20d_sum_cs_rank_pct | qlib_rank | 58354 | -0.179000 |
| institutional_total_net_buy_5d_sum | qlib_score_raw | 58354 | 0.175088 |
| institutional_total_net_buy_20d_sum_cs_rank_pct | qlib_score_raw | 58354 | 0.173231 |
| foreign_net_buy_10d_sum | qlib_score_raw | 58354 | 0.171570 |
| institutional_total_net_buy_5d_sum | qlib_score_percentile_by_date | 58354 | 0.167517 |
| institutional_total_net_buy_5d_sum | qlib_rank | 58354 | -0.167205 |
| foreign_net_buy_20d_sum | qlib_score_raw | 58354 | 0.166829 |
| institutional_total_net_buy_5d_sum_cs_rank_pct | qlib_score_percentile_by_date | 58354 | 0.164205 |
| institutional_total_net_buy_5d_sum_cs_rank_pct | qlib_rank | 58354 | -0.164204 |
| institutional_total_net_buy_5d_sum_cs_rank_pct | qlib_score_raw | 58354 | 0.158143 |

## 7. 泄露审计

| check | bad_rows | pass |
|---|---|---|
| institutional_available_at_lte_asof | 0 | 1 |
| margin_available_at_lte_asof | 0 | 1 |
| all_feature_rows_have_pit_join | 0 | 1 |
| same_day_institutional_trade_date_not_visible_same_day | 0 | 1 |
| same_day_margin_trade_date_not_visible_same_day | 0 | 1 |
| qlib_predictions_present | 0 | 1 |
| fwd_5d_label_date_gt_asof | 0 | 1 |
| fwd_10d_label_date_gt_asof | 0 | 1 |
| fwd_20d_label_date_gt_asof | 0 | 1 |

## 8. 产物

- 样本：`data_tw/experiments/decision_orthogonal/phase1b_full_samples.parquet`
- 样本预览：`data_tw/experiments/decision_orthogonal/phase1b_full_samples_preview.csv`
- schema：`data_tw/experiments/decision_orthogonal/phase1b_full_schema.json`
- 每月样本量：`data_tw/experiments/decision_orthogonal/phase1b_full_monthly_sample_size.csv`
- 全样本指标：`data_tw/experiments/decision_orthogonal/phase1b_full_factor_metrics.csv`
- 分段指标：`data_tw/experiments/decision_orthogonal/phase1b_full_segment_metrics.csv`
- 因子增量摘要：`data_tw/experiments/decision_orthogonal/phase1b_full_factor_increment_report.md`
- 泄露审计：`data_tw/experiments/decision_orthogonal/phase1b_full_leakage_audit_report.md`

## 9. Phase 1B Gate

- `request_phase2_rules_baseline=true`
- 即使请求 Phase2 rules baseline，也必须等待审查者授权；本脚本和本报告没有自动进入 Phase2。
