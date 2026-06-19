# Phase 1B 执行报告：扩展窗口正交数据只读验证

- 生成时间：`2026-06-11T09:49:47+00:00`
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
- 样本行数：`106440`
- 因两类 PIT feature 未同时可见而排除行数：`2869`
- Top50 子集样本量：`51599`
- Top150 子集样本量：`106440`
- qlib prediction rows：`109309`；prediction file count：`1118`
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
| 2023-01 | 1287 | 99 | 628 | 1287 | 1287 |
| 2023-02 | 1782 | 99 | 876 | 1782 | 1782 |
| 2023-03 | 2277 | 99 | 1102 | 2277 | 2277 |
| 2023-04 | 1683 | 99 | 814 | 1683 | 1683 |
| 2023-05 | 2178 | 99 | 1045 | 2178 | 2178 |
| 2023-06 | 1980 | 99 | 966 | 1980 | 1980 |
| 2023-07 | 2080 | 100 | 1017 | 2080 | 2080 |
| 2023-08 | 2200 | 100 | 1074 | 2200 | 2200 |
| 2023-09 | 2000 | 100 | 961 | 2000 | 2000 |
| 2023-10 | 2000 | 100 | 955 | 2000 | 2000 |
| 2023-11 | 2200 | 100 | 1059 | 2200 | 2200 |
| 2023-12 | 2100 | 100 | 1008 | 2100 | 2100 |
| 2024-01 | 2200 | 100 | 1050 | 2200 | 2200 |
| 2024-02 | 1300 | 100 | 615 | 1300 | 1300 |
| 2024-03 | 2100 | 100 | 999 | 2100 | 2100 |
| 2024-04 | 2000 | 100 | 971 | 2000 | 2000 |
| 2024-05 | 2200 | 100 | 1076 | 2200 | 2200 |
| 2024-06 | 1900 | 100 | 930 | 1900 | 1900 |
| 2024-07 | 2115 | 101 | 1029 | 2115 | 2115 |
| 2024-08 | 2222 | 101 | 1076 | 2222 | 2222 |
| 2024-09 | 2020 | 101 | 976 | 2020 | 2020 |
| 2024-10 | 1919 | 101 | 937 | 1919 | 1919 |
| 2024-11 | 2121 | 101 | 1029 | 2121 | 2121 |
| 2024-12 | 2222 | 101 | 1086 | 2222 | 2222 |
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
| margin_balance_20d_mean_cs_rank_pct | fwd_20d_excess_return | 103762 | 1037 | -0.041460 |
| margin_balance_20d_mean | fwd_20d_excess_return | 103762 | 1037 | -0.041460 |
| margin_balance_10d_mean | fwd_20d_excess_return | 103762 | 1037 | -0.040650 |
| margin_balance_10d_mean_cs_rank_pct | fwd_20d_excess_return | 103762 | 1037 | -0.040650 |
| margin_balance_5d_mean_cs_rank_pct | fwd_20d_excess_return | 103762 | 1037 | -0.039823 |
| margin_balance_5d_mean | fwd_20d_excess_return | 103762 | 1037 | -0.039823 |
| margin_balance_cs_rank_pct | fwd_20d_excess_return | 103762 | 1037 | -0.039272 |
| margin_balance | fwd_20d_excess_return | 103762 | 1037 | -0.039272 |
| short_balance_20d_mean_cs_rank_pct | fwd_20d_excess_return | 103762 | 1037 | -0.030411 |
| short_balance_20d_mean | fwd_20d_excess_return | 103762 | 1037 | -0.030411 |
| foreign_net_buy_20d_sum | fwd_20d_excess_return | 103762 | 1037 | 0.029804 |
| foreign_net_buy_20d_sum_cs_rank_pct | fwd_20d_excess_return | 103762 | 1037 | 0.029804 |
| foreign_net_buy_10d_sum_cs_rank_pct | fwd_10d_excess_return | 104792 | 1047 | 0.029141 |
| foreign_net_buy_10d_sum | fwd_10d_excess_return | 104792 | 1047 | 0.029141 |
| foreign_net_buy_10d_sum_cs_rank_pct | fwd_20d_excess_return | 103762 | 1037 | 0.028295 |
| foreign_net_buy_10d_sum | fwd_20d_excess_return | 103762 | 1037 | 0.028295 |
| margin_balance_20d_mean_cs_rank_pct | fwd_10d_excess_return | 104792 | 1047 | -0.028201 |
| margin_balance_20d_mean | fwd_10d_excess_return | 104792 | 1047 | -0.028201 |
| margin_balance_change_20d_sum_cs_rank_pct | fwd_20d_excess_return | 103762 | 1037 | 0.028023 |
| margin_balance_change_20d_sum | fwd_20d_excess_return | 103762 | 1037 | 0.028023 |

### 年度/季度/月度分段

- 分段指标输出：`data_tw/experiments/decision_orthogonal/phase1b_repaired_full_segment_metrics.csv`
- hit-rate 只作为历史样本统计，不代表未来胜率或收益承诺。

## 6. 与 qlib 排名关系

- 已计算正交特征与 `qlib_score_raw`、`qlib_rank`、`qlib_score_percentile_by_date` 的 Spearman 相关。
- 已对 qlib Top50/Top150 内外分别计算特征 high-low 与历史正样本比例。

| feature | label | n | value |
|---|---|---|---|
| institutional_total_net_buy_10d_sum | qlib_score_raw | 106440 | 0.214321 |
| institutional_total_net_buy_20d_sum | qlib_score_raw | 106440 | 0.205416 |
| institutional_total_net_buy_10d_sum | qlib_score_percentile_by_date | 106440 | 0.201868 |
| institutional_total_net_buy_10d_sum | qlib_rank | 106440 | -0.201637 |
| institutional_total_net_buy_10d_sum_cs_rank_pct | qlib_score_percentile_by_date | 106440 | 0.199586 |
| institutional_total_net_buy_10d_sum_cs_rank_pct | qlib_rank | 106440 | -0.199582 |
| institutional_total_net_buy_10d_sum_cs_rank_pct | qlib_score_raw | 106440 | 0.193130 |
| institutional_total_net_buy_20d_sum | qlib_score_percentile_by_date | 106440 | 0.191713 |
| institutional_total_net_buy_20d_sum | qlib_rank | 106440 | -0.191463 |
| institutional_total_net_buy_20d_sum_cs_rank_pct | qlib_score_percentile_by_date | 106440 | 0.189032 |
| institutional_total_net_buy_20d_sum_cs_rank_pct | qlib_rank | 106440 | -0.189025 |
| institutional_total_net_buy_5d_sum | qlib_score_raw | 106440 | 0.184979 |
| institutional_total_net_buy_20d_sum_cs_rank_pct | qlib_score_raw | 106440 | 0.182986 |
| foreign_net_buy_10d_sum | qlib_score_raw | 106440 | 0.176052 |
| institutional_total_net_buy_5d_sum | qlib_score_percentile_by_date | 106440 | 0.175497 |
| institutional_total_net_buy_5d_sum | qlib_rank | 106440 | -0.175322 |
| institutional_total_net_buy_5d_sum_cs_rank_pct | qlib_rank | 106440 | -0.174695 |
| institutional_total_net_buy_5d_sum_cs_rank_pct | qlib_score_percentile_by_date | 106440 | 0.174694 |
| foreign_net_buy_20d_sum | qlib_score_raw | 106440 | 0.169489 |
| institutional_total_net_buy_5d_sum_cs_rank_pct | qlib_score_raw | 106440 | 0.169096 |

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

- 样本：`data_tw/experiments/decision_orthogonal/phase1b_repaired_full_samples.parquet`
- 样本预览：`data_tw/experiments/decision_orthogonal/phase1b_repaired_full_samples_preview.csv`
- schema：`data_tw/experiments/decision_orthogonal/phase1b_repaired_full_schema.json`
- 每月样本量：`data_tw/experiments/decision_orthogonal/phase1b_repaired_full_monthly_sample_size.csv`
- 全样本指标：`data_tw/experiments/decision_orthogonal/phase1b_repaired_full_factor_metrics.csv`
- 分段指标：`data_tw/experiments/decision_orthogonal/phase1b_repaired_full_segment_metrics.csv`
- 因子增量摘要：`data_tw/experiments/decision_orthogonal/phase1b_repaired_full_factor_increment_report.md`
- 泄露审计：`data_tw/experiments/decision_orthogonal/phase1b_repaired_full_leakage_audit_report.md`

## 9. Phase 1B Gate

- `request_phase2_rules_baseline=true`
- 即使请求 Phase2 rules baseline，也必须等待审查者授权；本脚本和本报告没有自动进入 Phase2。


## 10. Repaired Full 专项补充

### Prediction Repair Provenance

- repaired batch：`qlib_pipeline/data_tw/experiments/option_c_historical_signal_backfill/option_c_historical_backfill_20230101_20241231_asof_aware_research_only`
- 2023-2024 calendar days：`481`
- repaired prediction files：`481`
- missing prediction days：`0`
- prediction columns：`['datetime,instrument,score']`
- formal validation bypass count：`0`
- refresh / publish / provider mutation / model retraining：`0` / `0` / `0` / `0`
- prediction selection rule：`latest duplicate by asof/symbol after sorting; repaired 2023-2024 asof-aware batch has highest priority, pred_fast has lowest priority`

### 2023-2024 Prediction Coverage

| year | prediction_file_count | rows | symbols_min | symbols_max | formal_fail_count | no_prediction |
|---|---|---|---|---|---|---|
| 2023 | 239 | 35611 | 149 | 149 | 0 | 0 |
| 2024 | 242 | 36101 | 149 | 150 | 0 | 0 |

### 2023-2024 每月样本量

| month | sample_rows | symbol_count | top50_rows | top150_rows | valid_pit_rows |
|---|---|---|---|---|---|
| 2023-01 | 1287 | 99 | 628 | 1287 | 1287 |
| 2023-02 | 1782 | 99 | 876 | 1782 | 1782 |
| 2023-03 | 2277 | 99 | 1102 | 2277 | 2277 |
| 2023-04 | 1683 | 99 | 814 | 1683 | 1683 |
| 2023-05 | 2178 | 99 | 1045 | 2178 | 2178 |
| 2023-06 | 1980 | 99 | 966 | 1980 | 1980 |
| 2023-07 | 2080 | 100 | 1017 | 2080 | 2080 |
| 2023-08 | 2200 | 100 | 1074 | 2200 | 2200 |
| 2023-09 | 2000 | 100 | 961 | 2000 | 2000 |
| 2023-10 | 2000 | 100 | 955 | 2000 | 2000 |
| 2023-11 | 2200 | 100 | 1059 | 2200 | 2200 |
| 2023-12 | 2100 | 100 | 1008 | 2100 | 2100 |
| 2024-01 | 2200 | 100 | 1050 | 2200 | 2200 |
| 2024-02 | 1300 | 100 | 615 | 1300 | 1300 |
| 2024-03 | 2100 | 100 | 999 | 2100 | 2100 |
| 2024-04 | 2000 | 100 | 971 | 2000 | 2000 |
| 2024-05 | 2200 | 100 | 1076 | 2200 | 2200 |
| 2024-06 | 1900 | 100 | 930 | 1900 | 1900 |
| 2024-07 | 2115 | 101 | 1029 | 2115 | 2115 |
| 2024-08 | 2222 | 101 | 1076 | 2222 | 2222 |
| 2024-09 | 2020 | 101 | 976 | 2020 | 2020 |
| 2024-10 | 1919 | 101 | 937 | 1919 | 1919 |
| 2024-11 | 2121 | 101 | 1029 | 2121 | 2121 |
| 2024-12 | 2222 | 101 | 1086 | 2222 | 2222 |

### 2022-2026 年度样本量

| year | sample_rows | symbol_min | symbol_max | top50_rows | top150_rows |
|---|---|---|---|---|---|
| 2022 | 23996 | 97 | 99 | 11664 | 23996 |
| 2023 | 23767 | 99 | 100 | 11505 | 23767 |
| 2024 | 24319 | 100 | 101 | 11774 | 24319 |
| 2025 | 24573 | 101 | 103 | 11906 | 24573 |
| 2026 | 9785 | 103 | 103 | 4750 | 9785 |

### Asof-aware Universe Exclusion

- `TW7769` 在 `2024-11-01` 前因 `missing_source_asof` 与 `outside_instrument_date_range` 排除，共 438 个交易日。
- `2024-11-01` smoke validation 中 active universe 为 150、excluded 为 0，说明 source/provider 均具备后可进入 universe。
- 完整月度排除明细见 `data_tw/experiments/decision_orthogonal/phase1b_asof_aware_prediction_repair_excluded_summary.csv`。

### 年度 RankIC 摘要

| segment | feature | label | n | valid_periods | value |
|---|---|---|---|---|---|
| 2022 | short_balance_5d_mean | fwd_20d_excess_return | 23996 | 245 | -0.070794 |
| 2022 | short_balance_5d_mean_cs_rank_pct | fwd_20d_excess_return | 23996 | 245 | -0.070794 |
| 2022 | short_balance_10d_mean | fwd_20d_excess_return | 23996 | 245 | -0.069754 |
| 2023 | margin_balance_20d_mean | fwd_20d_excess_return | 23767 | 239 | -0.059085 |
| 2023 | margin_balance_20d_mean_cs_rank_pct | fwd_20d_excess_return | 23767 | 239 | -0.059085 |
| 2023 | margin_balance_10d_mean | fwd_20d_excess_return | 23767 | 239 | -0.057291 |
| 2024 | margin_balance_10d_mean | fwd_20d_excess_return | 24319 | 242 | -0.084954 |
| 2024 | margin_balance_10d_mean_cs_rank_pct | fwd_20d_excess_return | 24319 | 242 | -0.084954 |
| 2024 | margin_balance_20d_mean | fwd_20d_excess_return | 24319 | 242 | -0.084804 |
| 2025 | dealer_net_buy_10d_sum | fwd_20d_excess_return | 24573 | 242 | 0.063191 |
| 2025 | dealer_net_buy_10d_sum_cs_rank_pct | fwd_20d_excess_return | 24573 | 242 | 0.063191 |
| 2025 | dealer_net_buy_20d_sum | fwd_20d_excess_return | 24573 | 242 | 0.061212 |
| 2026 | margin_balance | fwd_20d_excess_return | 7107 | 69 | -0.119303 |
| 2026 | margin_balance_cs_rank_pct | fwd_20d_excess_return | 7107 | 69 | -0.119303 |
| 2026 | margin_balance_5d_mean | fwd_20d_excess_return | 7107 | 69 | -0.118387 |

### 季度 RankIC 摘要

| segment | feature | label | n | valid_periods | value |
|---|---|---|---|---|---|
| 2022Q1 | margin_balance_change_20d_sum | fwd_20d_excess_return | 5334 | 55 | -0.099657 |
| 2022Q1 | margin_balance_change_20d_sum_cs_rank_pct | fwd_20d_excess_return | 5334 | 55 | -0.099657 |
| 2022Q2 | short_balance_10d_mean | fwd_20d_excess_return | 5931 | 61 | -0.135708 |
| 2022Q2 | short_balance_10d_mean_cs_rank_pct | fwd_20d_excess_return | 5931 | 61 | -0.135708 |
| 2022Q3 | short_balance_10d_mean | fwd_20d_excess_return | 6395 | 65 | -0.109644 |
| 2022Q3 | short_balance_10d_mean_cs_rank_pct | fwd_20d_excess_return | 6395 | 65 | -0.109644 |
| 2022Q4 | investment_trust_net_buy_20d_sum | fwd_20d_excess_return | 6336 | 64 | -0.141667 |
| 2022Q4 | investment_trust_net_buy_20d_sum_cs_rank_pct | fwd_20d_excess_return | 6336 | 64 | -0.141667 |
| 2023Q1 | investment_trust_net_buy_5d_sum | fwd_10d_excess_return | 5346 | 54 | -0.066141 |
| 2023Q1 | investment_trust_net_buy_5d_sum_cs_rank_pct | fwd_10d_excess_return | 5346 | 54 | -0.066141 |
| 2023Q2 | investment_trust_net_buy_20d_sum | fwd_20d_excess_return | 5841 | 59 | 0.179737 |
| 2023Q2 | investment_trust_net_buy_20d_sum_cs_rank_pct | fwd_20d_excess_return | 5841 | 59 | 0.179737 |
| 2023Q3 | dealer_net_buy_20d_sum | fwd_20d_excess_return | 6280 | 63 | 0.123409 |
| 2023Q3 | dealer_net_buy_20d_sum_cs_rank_pct | fwd_20d_excess_return | 6280 | 63 | 0.123409 |
| 2023Q4 | margin_balance_5d_mean | fwd_20d_excess_return | 6300 | 63 | -0.102322 |
| 2023Q4 | margin_balance_5d_mean_cs_rank_pct | fwd_20d_excess_return | 6300 | 63 | -0.102322 |
| 2024Q1 | short_balance_20d_zscore | fwd_10d_excess_return | 5595 | 56 | 0.131299 |
| 2024Q1 | short_balance_20d_zscore_cs_rank_pct | fwd_10d_excess_return | 5595 | 56 | 0.131299 |
| 2024Q2 | foreign_net_buy_20d_sum | fwd_10d_excess_return | 6100 | 61 | 0.092911 |
| 2024Q2 | foreign_net_buy_20d_sum_cs_rank_pct | fwd_10d_excess_return | 6100 | 61 | 0.092911 |
| 2024Q3 | margin_balance_20d_zscore | fwd_10d_excess_return | 6355 | 63 | 0.104164 |
| 2024Q3 | margin_balance_20d_zscore_cs_rank_pct | fwd_10d_excess_return | 6355 | 63 | 0.104164 |
| 2024Q4 | margin_balance_10d_mean | fwd_20d_excess_return | 6262 | 62 | -0.168489 |
| 2024Q4 | margin_balance_10d_mean_cs_rank_pct | fwd_20d_excess_return | 6262 | 62 | -0.168489 |

### 全样本 RankIC / IC 摘要

RankIC top absolute：

| feature | label | n | valid_periods | value |
|---|---|---|---|---|
| margin_balance_20d_mean_cs_rank_pct | fwd_20d_excess_return | 103762 | 1037 | -0.041460 |
| margin_balance_20d_mean | fwd_20d_excess_return | 103762 | 1037 | -0.041460 |
| margin_balance_10d_mean | fwd_20d_excess_return | 103762 | 1037 | -0.040650 |
| margin_balance_10d_mean_cs_rank_pct | fwd_20d_excess_return | 103762 | 1037 | -0.040650 |
| margin_balance_5d_mean_cs_rank_pct | fwd_20d_excess_return | 103762 | 1037 | -0.039823 |
| margin_balance_5d_mean | fwd_20d_excess_return | 103762 | 1037 | -0.039823 |
| margin_balance_cs_rank_pct | fwd_20d_excess_return | 103762 | 1037 | -0.039272 |
| margin_balance | fwd_20d_excess_return | 103762 | 1037 | -0.039272 |
| short_balance_20d_mean_cs_rank_pct | fwd_20d_excess_return | 103762 | 1037 | -0.030411 |
| short_balance_20d_mean | fwd_20d_excess_return | 103762 | 1037 | -0.030411 |

IC top absolute：

| feature | label | n | valid_periods | value |
|---|---|---|---|---|
| margin_balance_20d_mean | fwd_20d_excess_return | 103762 | 1037 | -0.039557 |
| margin_balance_10d_mean | fwd_20d_excess_return | 103762 | 1037 | -0.037900 |
| margin_balance_5d_mean | fwd_20d_excess_return | 103762 | 1037 | -0.036956 |
| margin_balance | fwd_20d_excess_return | 103762 | 1037 | -0.036110 |
| foreign_net_buy_20d_sum_cs_rank_pct | fwd_20d_excess_return | 103762 | 1037 | 0.034184 |
| margin_balance_change_20d_sum_cs_rank_pct | fwd_10d_excess_return | 104792 | 1047 | 0.032490 |
| margin_balance_20d_mean_cs_rank_pct | fwd_20d_excess_return | 103762 | 1037 | -0.031943 |
| margin_balance_10d_mean_cs_rank_pct | fwd_20d_excess_return | 103762 | 1037 | -0.031435 |
| foreign_net_buy_20d_sum_cs_rank_pct | fwd_10d_excess_return | 104792 | 1047 | 0.030713 |
| margin_balance_5d_mean_cs_rank_pct | fwd_20d_excess_return | 103762 | 1037 | -0.030586 |

### Qlib Score 相关性

| feature | label | n | value |
|---|---|---|---|
| institutional_total_net_buy_10d_sum | qlib_score_raw | 106440 | 0.214321 |
| institutional_total_net_buy_20d_sum | qlib_score_raw | 106440 | 0.205416 |
| institutional_total_net_buy_10d_sum_cs_rank_pct | qlib_score_raw | 106440 | 0.193130 |
| institutional_total_net_buy_5d_sum | qlib_score_raw | 106440 | 0.184979 |
| institutional_total_net_buy_20d_sum_cs_rank_pct | qlib_score_raw | 106440 | 0.182986 |
| foreign_net_buy_10d_sum | qlib_score_raw | 106440 | 0.176052 |
| foreign_net_buy_20d_sum | qlib_score_raw | 106440 | 0.169489 |
| institutional_total_net_buy_5d_sum_cs_rank_pct | qlib_score_raw | 106440 | 0.169096 |
| foreign_net_buy_10d_sum_cs_rank_pct | qlib_score_raw | 106440 | 0.155179 |
| foreign_net_buy_5d_sum | qlib_score_raw | 106440 | 0.151353 |

### Top50 / Top150 内外表现

| feature | label | segment_type | segment | n | valid_periods | value |
|---|---|---|---|---|---|---|
| foreign_net_buy_20d_sum | fwd_20d_excess_return | top50_flag | top50_flag=outside | 35642 | 1063 | 0.018825 |
| margin_balance_change_20d_sum_cs_rank_pct | fwd_20d_excess_return | top50_flag | top50_flag=inside | 33532 | 1063 | 0.017649 |
| margin_balance_change_10d_sum_cs_rank_pct | fwd_20d_excess_return | top50_flag | top50_flag=inside | 33515 | 1063 | 0.016287 |
| foreign_net_buy_20d_sum | fwd_20d_excess_return | top150_flag | top150_flag=inside | 69174 | 1063 | 0.015602 |
| foreign_net_buy_10d_sum | fwd_20d_excess_return | top50_flag | top50_flag=outside | 35642 | 1063 | 0.015387 |
| margin_balance_20d_zscore_cs_rank_pct | fwd_20d_excess_return | top50_flag | top50_flag=inside | 33392 | 1063 | 0.014390 |
| foreign_net_buy_20d_sum_cs_rank_pct | fwd_20d_excess_return | top50_flag | top50_flag=outside | 35667 | 1063 | 0.013822 |
| foreign_net_buy_5d_sum | fwd_20d_excess_return | top50_flag | top50_flag=outside | 35642 | 1063 | 0.013316 |
| foreign_net_buy_10d_sum_cs_rank_pct | fwd_20d_excess_return | top50_flag | top50_flag=outside | 35601 | 1063 | 0.013261 |
| foreign_net_buy_10d_sum | fwd_20d_excess_return | top150_flag | top150_flag=inside | 69175 | 1063 | 0.012850 |
| margin_balance_change_20d_sum | fwd_20d_excess_return | top50_flag | top50_flag=inside | 33539 | 1063 | 0.012227 |
| institutional_total_net_buy_20d_sum | fwd_20d_excess_return | top50_flag | top50_flag=outside | 35642 | 1063 | 0.012216 |

### Gate

- `request_phase2_rules_baseline=true`
- 这只是向审查者请求 Phase2 rules baseline 授权；本阶段没有进入 Phase2，没有规则 baseline，没有模型训练。

