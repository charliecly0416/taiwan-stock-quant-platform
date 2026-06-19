# Phase O2 执行报告：PIT-safe Feature Builder

生成时间：`2026-06-15T11:13:38+00:00`

## 1. 执行结论

本轮只基于 O1R 已确认的法人筹码与融资融券数据构建 PIT-safe daily feature builder，并输出 lineage、missing、delay 与 PIT leakage 审计。

推荐 gate：

```text
phase_o2_pit_safe_feature_builder_passed
```

## 2. 边界

- 未训练 qlib/LTR。
- 未回放收益率。
- 未构建最终 treatment LTR sample。
- 未修改 Phase1C control。
- 未新增月营收或 O1R 未审查数据源。
- 未触发 frontend/API/provider/accepted latest/monitor/交易链路。

## 3. 输入 Artifact

- `data_tw/experiments/ltr_rerank_regime_turnover/phase1_ltr_baseline/phase1_ltr_samples.csv` read-only，用于 symbol/sample_date/control row universe。
- `data_tw/experiments/ltr_orthogonal_features_controlled/phase_o1r_coverage_available_at_repair/`。
- `data_tw/experiments/decision_orthogonal/phase0e_pit_snapshot_manifest.csv`。

## 4. 输出 Artifact

- `data_tw/experiments/ltr_orthogonal_features_controlled/phase_o2_pit_safe_feature_builder/feature_dictionary.csv`
- `data_tw/experiments/ltr_orthogonal_features_controlled/phase_o2_pit_safe_feature_builder/normalized_feature_daily.csv`
- `data_tw/experiments/ltr_orthogonal_features_controlled/phase_o2_pit_safe_feature_builder/pit_normalized_daily_with_lineage.csv`
- `data_tw/experiments/ltr_orthogonal_features_controlled/phase_o2_pit_safe_feature_builder/feature_builder_manifest.json`
- `data_tw/experiments/ltr_orthogonal_features_controlled/phase_o2_pit_safe_feature_builder/pit_lineage_audit.csv`
- `data_tw/experiments/ltr_orthogonal_features_controlled/phase_o2_pit_safe_feature_builder/pit_leakage_audit.csv`
- `data_tw/experiments/ltr_orthogonal_features_controlled/phase_o2_pit_safe_feature_builder/missing_by_feature_family.csv`
- `data_tw/experiments/ltr_orthogonal_features_controlled/phase_o2_pit_safe_feature_builder/missing_by_symbol.csv`
- `data_tw/experiments/ltr_orthogonal_features_controlled/phase_o2_pit_safe_feature_builder/missing_by_date.csv`
- `data_tw/experiments/ltr_orthogonal_features_controlled/phase_o2_pit_safe_feature_builder/delay_distribution.csv`
- `data_tw/experiments/ltr_orthogonal_features_controlled/phase_o2_pit_safe_feature_builder/phaseo2_summary.json`

## 5. Row Count / Symbol / Date Range

| feature_family | input_rows | output_rows | symbol_count | trade_date_min | trade_date_max | available_at_min | available_at_max | lineage_sources | missing_raw_snapshot_path_rows |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| institutional_flow | 158317 | 158317 | 150 | 2022-01-03 | 2026-06-10 | 2022-01-04 | 2026-06-11 | phase0e|phaseo1r | 0 |
| margin_short | 153705 | 153705 | 150 | 2022-01-03 | 2026-06-10 | 2022-01-04 | 2026-06-11 | phase0e|phaseo1r | 0 |

## 6. available_at 合同统计

| feature_family | rows | available_at_le_trade_date_rows | available_at_gt_trade_date_rows | available_at_lt_next_trading_day_rows | available_at_gt_next_trading_day_rows | missing_next_trading_day_rows |
| --- | --- | --- | --- | --- | --- | --- |
| institutional_flow | 158317 | 0 | 158317 | 1 | 386 | 103 |
| margin_short | 153705 | 0 | 153705 | 1 | 1 | 102 |

## 7. Delay 分布

| feature_family | delay_reason | row_count | min_delay_days | max_delay_days |
| --- | --- | --- | --- | --- |
| institutional_flow | calendar_gap | 1 | -3 | -3 |
| institutional_flow | exact_t1 | 157827 | 0 | 0 |
| institutional_flow | listing_status_gap | 386 | 1 | 664 |
| institutional_flow | missing_calendar | 103 |  |  |
| margin_short | calendar_gap | 2 | -3 | 1 |
| margin_short | exact_t1 | 153601 | 0 | 0 |
| margin_short | missing_calendar | 102 |  |  |

## 8. Missing Ratio by Feature Family

| feature_family | control_rows | missing_rows | missing_ratio |
| --- | --- | --- | --- |
| institutional_flow | 159993 | 595 | 0.003718912702430731 |
| margin_short | 159993 | 5417 | 0.03385773127574331 |

## 9. 低覆盖 Symbols

| category | symbol | after_coverage_rate | after_raw_rows | after_missing_control_dates |
| --- | --- | --- | --- | --- |
| institutional_flow | TW4749 | 0.77979 | 819 | 231 |
| institutional_flow | TW6919 | 0.837935 | 699 | 135 |
| institutional_flow | TW6805 | 0.94041 | 1011 | 64 |
| institutional_flow | TW4991 | 0.947858 | 1019 | 56 |
| margin_short | TW7769 | 0.017949 | 7 | 383 |
| margin_short | TW6919 | 0.038415 | 32 | 801 |
| margin_short | TW3131 | 0.110801 | 119 | 955 |
| margin_short | TW6683 | 0.11825 | 127 | 947 |
| margin_short | TW4749 | 0.194471 | 205 | 845 |
| margin_short | TW6805 | 0.425512 | 458 | 617 |
| margin_short | TW6446 | 0.638734 | 687 | 388 |
| margin_short | TW6789 | 0.741155 | 797 | 278 |
| margin_short | TW6770 | 0.895717 | 963 | 112 |

## 10. PIT Leakage Audit

| feature_family | control_rows_checked | audit_rows | missing_rows | missing_ratio | used_available_at_gt_sample_date_rows | used_trade_date_gt_sample_date_rows |
| --- | --- | --- | --- | --- | --- | --- |
| institutional_flow | 159993 | 159993 | 595 | 0.003718912702430731 | 0 | 0 |
| margin_short | 159993 | 159993 | 5417 | 0.03385773127574331 | 0 | 0 |

## 11. Control 不变性

- control rows read-only checked：`159993`。
- control symbols：`150`。
- 未写回 control sample。
- 未输出最终 treatment LTR sample；`pit_lineage_audit.csv` 仅含 lineage/可用性/泄漏审计列。

## 12. 停止条件复核

- as-of join 使用 `available_at > sample_date` 行：`0`。
- `available_at <= trade_date` 禁止性提前可见行：`0`。
- 缺 raw lineage path 行：`0`。
- stop_triggered：`False`。
