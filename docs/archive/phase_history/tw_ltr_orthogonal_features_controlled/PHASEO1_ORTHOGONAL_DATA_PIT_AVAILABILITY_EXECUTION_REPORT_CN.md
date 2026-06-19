# Phase O1 执行报告：正交数据 PIT 可得性审计

生成时间：`2026-06-15T09:56:46+00:00`

## 1. 执行结论

本轮只读取既有 Phase0E/Phase0D FinMind 法人筹码与融资融券产物，审计其是否可用于后续 O2 的 PIT-safe raw archive / normalized daily table 设计。

推荐 gate：

```text
phase_o1_blocked_requires_data_coverage_decision
```

本轮未请求 FinMind 网络、未训练 qlib/LTR、未构建 treatment 样本、未做回放或收益率优劣证明、未改 frontend/API/provider/accepted latest/monitor/交易链路。

## 2. Control 与数据范围

- O0 gate：`phase_o0_anchor_and_control_contract_frozen`
- control sample rows：`159993`
- control sample complete rows：`152249`
- control symbols：`150`
- control date range：`2022-01-03` ~ `2026-06-12`
- 正交数据范围：`institutional_flow`、`margin_short`
- PIT 规则：`available_at = next_trading_day(trade_date)`

## 3. FinMind Download/API 状态摘要

| category | request_count | success_count | failed_count | symbols_requested | row_count_sum | token_used_values | start_date_min | end_date_max |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| institutional_flow | 150 | 150 | 0 | 150 | 800020 | True | 2022-01-01 | 2026-06-10 |
| margin_short | 150 | 150 | 0 | 150 | 157550 | True | 2022-01-01 | 2026-06-10 |

## 4. Field Schema 审计

| category | required_columns_present | missing_required_columns | extra_columns | column_count | raw_snapshot_ids |
| --- | --- | --- | --- | --- | --- |
| institutional_flow | yes |  |  | 13 | phase0e_institutional_flow_20260610T175901Z |
| margin_short | yes |  |  | 13 | phase0e_margin_short_20260610T180330Z |

## 5. PIT available_at 审计

| category | row_count | available_at_nonnull_rows | available_at_missing_rows | available_at_not_after_trade_date_rows | available_at_next_trading_day_mismatch_rows | pit_rule_pass |
| --- | --- | --- | --- | --- | --- | --- |
| institutional_flow | 158834 | 158834 | 0 | 0 | 398 | no |
| margin_short | 156021 | 156021 | 0 | 0 | 5 | no |

说明：未发现 `available_at <= trade_date` 的同日可见记录，但发现若干记录不满足严格 `available_at = next_trading_day(trade_date)`。这些记录多数属于保守延迟可见或交易日历/上市状态差异，不能在 O1 判为 exact T+1 通过；若继续 O2，必须明确处理为 PIT-safe delayed availability 或回到数据源修正。

PIT mismatch 样例：

| category | symbol | trade_date | available_at | expected_available_at | quality_flags |
| --- | --- | --- | --- | --- | --- |
| institutional_flow | TW6472 | 2024-01-15 | 2024-01-17 | 2024-01-16 |  |
| institutional_flow | TW6472 | 2024-08-26 | 2024-08-28 | 2024-08-27 |  |
| institutional_flow | TW6472 | 2025-07-31 | 2025-08-01 | 2025-08-04 |  |
| institutional_flow | TW6805 | 2022-01-04 | 2023-10-31 | 2022-01-05 |  |
| institutional_flow | TW6805 | 2022-01-05 | 2023-10-31 | 2022-01-06 |  |
| institutional_flow | TW6805 | 2022-01-06 | 2023-10-31 | 2022-01-07 |  |
| institutional_flow | TW6805 | 2022-01-07 | 2023-10-31 | 2022-01-10 |  |
| institutional_flow | TW6805 | 2022-01-10 | 2023-10-31 | 2022-01-11 |  |
| institutional_flow | TW6805 | 2022-01-12 | 2023-10-31 | 2022-01-13 |  |
| institutional_flow | TW6805 | 2022-01-13 | 2023-10-31 | 2022-01-14 |  |
| institutional_flow | TW6805 | 2022-01-14 | 2023-10-31 | 2022-01-17 |  |
| institutional_flow | TW6805 | 2022-01-17 | 2023-10-31 | 2022-01-18 |  |

## 6. Phase1C Control Symbol 覆盖

| category | control_symbol_count | symbols_with_phase0e_data | control_symbols_absent | normalized_rows | trade_date_min | trade_date_max | coverage_rate_min | coverage_rate_median | low_coverage_symbol_count_lt_0_95 | lowest_coverage_symbols |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| institutional_flow | 150 | 103 | 47 | 158834 | 2022-01-03 | 2026-05-29 | 0.786538 | 0.999061 | 1 | TW4749:0.7865 |
| margin_short | 150 | 103 | 47 | 156021 | 2022-01-03 | 2026-05-29 | 0.111737 | 0.999061 | 5 | TW3131:0.1117|TW4749:0.1962|TW6446:0.6441|TW6805:0.7328|TW6770:0.9033 |

## 7. 低覆盖/缺失分布样例

| category | symbol | pit_valid_coverage_rate | expected_trading_days | raw_rows | pit_valid_rows | missing_dates_count | quality_issue_count |
| --- | --- | --- | --- | --- | --- | --- | --- |
| institutional_flow | TW1326 | 0.0 |  | 0 | 0 |  |  |
| institutional_flow | TW1711 | 0.0 |  | 0 | 0 |  |  |
| institutional_flow | TW1717 | 0.0 |  | 0 | 0 |  |  |
| institutional_flow | TW1785 | 0.0 |  | 0 | 0 |  |  |
| institutional_flow | TW1802 | 0.0 |  | 0 | 0 |  |  |
| institutional_flow | TW2337 | 0.0 |  | 0 | 0 |  |  |
| institutional_flow | TW2367 | 0.0 |  | 0 | 0 |  |  |
| institutional_flow | TW2451 | 0.0 |  | 0 | 0 |  |  |
| institutional_flow | TW2467 | 0.0 |  | 0 | 0 |  |  |
| institutional_flow | TW2481 | 0.0 |  | 0 | 0 |  |  |
| institutional_flow | TW2485 | 0.0 |  | 0 | 0 |  |  |
| institutional_flow | TW2489 | 0.0 |  | 0 | 0 |  |  |
| institutional_flow | TW2492 | 0.0 |  | 0 | 0 |  |  |
| institutional_flow | TW3030 | 0.0 |  | 0 | 0 |  |  |
| institutional_flow | TW3167 | 0.0 |  | 0 | 0 |  |  |
| institutional_flow | TW3211 | 0.0 |  | 0 | 0 |  |  |
| institutional_flow | TW3264 | 0.0 |  | 0 | 0 |  |  |
| institutional_flow | TW3563 | 0.0 |  | 0 | 0 |  |  |
| institutional_flow | TW3693 | 0.0 |  | 0 | 0 |  |  |
| institutional_flow | TW3702 | 0.0 |  | 0 | 0 |  |  |
| institutional_flow | TW3714 | 0.0 |  | 0 | 0 |  |  |
| institutional_flow | TW4967 | 0.0 |  | 0 | 0 |  |  |
| institutional_flow | TW4971 | 0.0 |  | 0 | 0 |  |  |
| institutional_flow | TW4977 | 0.0 |  | 0 | 0 |  |  |
| institutional_flow | TW4989 | 0.0 |  | 0 | 0 |  |  |
| institutional_flow | TW4991 | 0.0 |  | 0 | 0 |  |  |
| institutional_flow | TW5289 | 0.0 |  | 0 | 0 |  |  |
| institutional_flow | TW5351 | 0.0 |  | 0 | 0 |  |  |
| institutional_flow | TW5439 | 0.0 |  | 0 | 0 |  |  |
| institutional_flow | TW5536 | 0.0 |  | 0 | 0 |  |  |

## 8. Quality Flags 摘要

| category | quality_flag_reason | symbol_count | row_count_sum |
| --- | --- | --- | --- |
| institutional_flow | available_at_missing_no_next_trading_day | 150 | 1529 |
| institutional_flow | none | 150 | 158834 |
| margin_short | available_at_missing_no_next_trading_day | 150 | 1529 |
| margin_short | none | 150 | 156021 |

## 9. 停止条件复核

- 402/403/429：本轮复用本地 Phase0E 状态，未发现 failed request。
- 字段稳定性：两个 normalized table 均包含主线要求字段。
- 历史覆盖：本地 Phase0E 覆盖 `2022-01-01..2026-06-10` 请求窗口，但部分股票低覆盖，O2/O3 必须保留缺失标记与 neutral fill。
- PIT available_at：未发现同日可见，但严格 `available_at = next_trading_day(trade_date)` 未通过；尾部无下一交易日记录不得未来补齐。
- 新数据源/新账号：本轮未引入。

## 10. O2 前置要求

- O2 只能基于已审计的法人筹码与融资融券字段构建 PIT-safe feature builder。
- 后续 treatment 样本必须与 control 行数、label hash、原始特征 hash 完全一致。
- 正交数据缺失只能 neutral fill + missing flag，不能删行、不能更改 control sample rows。
- O1 不证明收益率优劣；不得用本报告作为产品化或前端切换依据。

## 11. 输出产物

- `data_tw/experiments/ltr_orthogonal_features_controlled/phase_o1_pit_availability/phaseo1_source_artifact_inventory.csv`
- `data_tw/experiments/ltr_orthogonal_features_controlled/phase_o1_pit_availability/phaseo1_dataset_status_summary.csv`
- `data_tw/experiments/ltr_orthogonal_features_controlled/phase_o1_pit_availability/phaseo1_field_schema_audit.csv`
- `data_tw/experiments/ltr_orthogonal_features_controlled/phase_o1_pit_availability/phaseo1_pit_available_at_audit.csv`
- `data_tw/experiments/ltr_orthogonal_features_controlled/phase_o1_pit_availability/phaseo1_pit_available_at_mismatch_examples.csv`
- `data_tw/experiments/ltr_orthogonal_features_controlled/phase_o1_pit_availability/phaseo1_symbol_coverage_summary.csv`
- `data_tw/experiments/ltr_orthogonal_features_controlled/phase_o1_pit_availability/phaseo1_missing_distribution.csv`
- `data_tw/experiments/ltr_orthogonal_features_controlled/phase_o1_pit_availability/phaseo1_quality_flags_summary.csv`
- `data_tw/experiments/ltr_orthogonal_features_controlled/phase_o1_pit_availability/phaseo1_summary.json`

## 12. 需要用户/审查确认的问题

- available_at has strict next-trading-day mismatches; no same-day visibility was found, but exact T+1 PIT rule is not satisfied.
- Phase0E local archive does not cover all Phase1C control symbols.
