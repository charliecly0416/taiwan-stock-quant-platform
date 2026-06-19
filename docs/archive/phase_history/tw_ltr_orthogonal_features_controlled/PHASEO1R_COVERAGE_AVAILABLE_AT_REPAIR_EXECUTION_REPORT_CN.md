# Phase O1R 执行报告：覆盖与 available_at 合同修复

生成时间：`2026-06-15T10:13:06+00:00`

## 1. 执行摘要

本轮只处理 Phase1C control 150 股的法人筹码与融资融券覆盖，以及 `exact T+1` vs `PIT-safe delayed availability` 合同审计。

推荐 gate：

```text
phase_o1r_needs_user_confirmation_for_delayed_availability_contract
```

推荐 available_at 合同：`pit_safe_delayed_availability`。

## 2. 边界

- 未训练 qlib/LTR。
- 未回放，不做收益率优劣证明。
- 未构建 treatment sample。
- 未修改 Phase1C control。
- 未触发 frontend/API/provider/accepted latest/monitor/交易链路。
- 未引入月营收或其他数据源。

## 3. 联网与 token/scrapling

- 是否联网拉取：`True`。
- final_refresh_reused_existing_archive：`True`。
- token_used：`False`。
- token_source：`none`。
- scrapling_used：`false`。
- endpoint：`https://api.finmindtrade.com/api/v4/data`。

## 4. 使用数据集

- `TaiwanStockInstitutionalInvestorsBuySell`
- `TaiwanStockMarginPurchaseShortSale`

## 5. 150 个 control symbols 覆盖前后对比

| category | control_symbol_count | before_symbols_with_rows | after_symbols_with_rows | absent_before | absent_after | low_coverage_after_lt_0_95 | min_after_coverage_rate | median_after_coverage_rate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| institutional_flow | 150 | 103 | 150 | 47 | 0 | 4 | 0.77979 | 0.990689 |
| margin_short | 150 | 103 | 150 | 47 | 0 | 9 | 0.017949 | 0.990689 |

## 6. Absent symbols 补齐结果

| category | symbol | status | raw_row_count | normalized_row_count | error_type | token_used | scrapling_used |
| --- | --- | --- | --- | --- | --- | --- | --- |
| institutional_flow | TW1326 | success | 5365 | 1073 |  | False | False |
| institutional_flow | TW1711 | success | 5365 | 1073 |  | False | False |
| institutional_flow | TW1717 | success | 5330 | 1066 |  | False | False |
| institutional_flow | TW1785 | success | 5360 | 1072 |  | False | False |
| institutional_flow | TW1802 | success | 5365 | 1073 |  | False | False |
| institutional_flow | TW2337 | success | 5365 | 1073 |  | False | False |
| institutional_flow | TW2367 | success | 5365 | 1073 |  | False | False |
| institutional_flow | TW2451 | success | 5365 | 1073 |  | False | False |
| institutional_flow | TW2467 | success | 5365 | 1073 |  | False | False |
| institutional_flow | TW2481 | success | 5365 | 1073 |  | False | False |
| institutional_flow | TW2485 | success | 5365 | 1073 |  | False | False |
| institutional_flow | TW2489 | success | 5265 | 1053 |  | False | False |
| institutional_flow | TW2492 | success | 5365 | 1073 |  | False | False |
| institutional_flow | TW3030 | success | 5365 | 1073 |  | False | False |
| institutional_flow | TW3167 | success | 5355 | 1071 |  | False | False |
| institutional_flow | TW3211 | success | 5360 | 1072 |  | False | False |
| institutional_flow | TW3264 | success | 5360 | 1072 |  | False | False |
| institutional_flow | TW3563 | success | 5365 | 1073 |  | False | False |
| institutional_flow | TW3693 | success | 5360 | 1072 |  | False | False |
| institutional_flow | TW3702 | success | 5365 | 1073 |  | False | False |
| institutional_flow | TW3714 | success | 5365 | 1073 |  | False | False |
| institutional_flow | TW4967 | success | 5330 | 1066 |  | False | False |
| institutional_flow | TW4971 | success | 5345 | 1069 |  | False | False |
| institutional_flow | TW4977 | success | 5360 | 1072 |  | False | False |
| institutional_flow | TW4989 | success | 5365 | 1073 |  | False | False |
| institutional_flow | TW4991 | success | 5095 | 1019 |  | False | False |
| institutional_flow | TW5289 | success | 5365 | 1073 |  | False | False |
| institutional_flow | TW5351 | success | 5360 | 1072 |  | False | False |
| institutional_flow | TW5439 | success | 5360 | 1072 |  | False | False |
| institutional_flow | TW5536 | success | 5325 | 1065 |  | False | False |
| institutional_flow | TW6147 | success | 5360 | 1072 |  | False | False |
| institutional_flow | TW6257 | success | 5365 | 1073 |  | False | False |
| institutional_flow | TW6271 | success | 5330 | 1066 |  | False | False |
| institutional_flow | TW6290 | success | 5360 | 1072 |  | False | False |
| institutional_flow | TW6505 | success | 5365 | 1073 |  | False | False |
| institutional_flow | TW6510 | success | 5360 | 1072 |  | False | False |
| institutional_flow | TW6683 | success | 5360 | 1072 |  | False | False |
| institutional_flow | TW6789 | success | 5049 | 1045 |  | False | False |
| institutional_flow | TW6919 | success | 2901 | 699 |  | False | False |
| institutional_flow | TW7769 | success | 1421 | 389 |  | False | False |
| institutional_flow | TW8021 | success | 5365 | 1073 |  | False | False |
| institutional_flow | TW8039 | success | 5365 | 1073 |  | False | False |
| institutional_flow | TW8096 | success | 5365 | 1073 |  | False | False |
| institutional_flow | TW8110 | success | 5365 | 1073 |  | False | False |
| institutional_flow | TW8112 | success | 5365 | 1073 |  | False | False |
| institutional_flow | TW8150 | success | 5365 | 1073 |  | False | False |
| institutional_flow | TW8358 | success | 5365 | 1073 |  | False | False |
| margin_short | TW1326 | success | 1073 | 1073 |  | False | False |
| margin_short | TW1711 | success | 1073 | 1073 |  | False | False |
| margin_short | TW1717 | success | 1073 | 1073 |  | False | False |
| margin_short | TW1785 | success | 1073 | 1073 |  | False | False |
| margin_short | TW1802 | success | 1073 | 1073 |  | False | False |
| margin_short | TW2337 | success | 1073 | 1073 |  | False | False |
| margin_short | TW2367 | success | 1073 | 1073 |  | False | False |
| margin_short | TW2451 | success | 1073 | 1073 |  | False | False |
| margin_short | TW2467 | success | 1073 | 1073 |  | False | False |
| margin_short | TW2481 | success | 1073 | 1073 |  | False | False |
| margin_short | TW2485 | success | 1073 | 1073 |  | False | False |
| margin_short | TW2489 | success | 1073 | 1073 |  | False | False |
| margin_short | TW2492 | success | 1073 | 1073 |  | False | False |
| margin_short | TW3030 | success | 1073 | 1073 |  | False | False |
| margin_short | TW3167 | success | 1073 | 1073 |  | False | False |
| margin_short | TW3211 | success | 1073 | 1073 |  | False | False |
| margin_short | TW3264 | success | 1073 | 1073 |  | False | False |
| margin_short | TW3563 | success | 1073 | 1073 |  | False | False |
| margin_short | TW3693 | success | 1073 | 1073 |  | False | False |
| margin_short | TW3702 | success | 1073 | 1073 |  | False | False |
| margin_short | TW3714 | success | 1073 | 1073 |  | False | False |
| margin_short | TW4967 | success | 1073 | 1073 |  | False | False |
| margin_short | TW4971 | success | 1073 | 1073 |  | False | False |
| margin_short | TW4977 | success | 1073 | 1073 |  | False | False |
| margin_short | TW4989 | success | 1073 | 1073 |  | False | False |
| margin_short | TW4991 | success | 1073 | 1073 |  | False | False |
| margin_short | TW5289 | success | 1073 | 1073 |  | False | False |
| margin_short | TW5351 | success | 1073 | 1073 |  | False | False |
| margin_short | TW5439 | success | 1073 | 1073 |  | False | False |
| margin_short | TW5536 | success | 1073 | 1073 |  | False | False |
| margin_short | TW6147 | success | 1073 | 1073 |  | False | False |
| margin_short | TW6257 | success | 1073 | 1073 |  | False | False |
| margin_short | TW6271 | success | 1073 | 1073 |  | False | False |
| margin_short | TW6290 | success | 1073 | 1073 |  | False | False |
| margin_short | TW6505 | success | 1073 | 1073 |  | False | False |
| margin_short | TW6510 | success | 1073 | 1073 |  | False | False |
| margin_short | TW6683 | success | 127 | 127 |  | False | False |
| margin_short | TW6789 | success | 797 | 797 |  | False | False |
| margin_short | TW6919 | success | 32 | 32 |  | False | False |
| margin_short | TW7769 | success | 7 | 7 |  | False | False |
| margin_short | TW8021 | success | 1073 | 1073 |  | False | False |
| margin_short | TW8039 | success | 1073 | 1073 |  | False | False |
| margin_short | TW8096 | success | 1073 | 1073 |  | False | False |
| margin_short | TW8110 | success | 1073 | 1073 |  | False | False |
| margin_short | TW8112 | success | 1073 | 1073 |  | False | False |
| margin_short | TW8150 | success | 1073 | 1073 |  | False | False |
| margin_short | TW8358 | success | 1073 | 1073 |  | False | False |

## 7. 低覆盖 symbols 列表

| category | symbol | before_coverage_rate | after_coverage_rate | after_raw_rows | after_missing_control_dates | fetch_attempted | fetch_success |
| --- | --- | --- | --- | --- | --- | --- | --- |
| institutional_flow | TW4749 | 0.77979 | 0.77979 | 819 | 231 | False | False |
| institutional_flow | TW6919 | 0.0 | 0.837935 | 699 | 135 | True | True |
| institutional_flow | TW6805 | 0.94041 | 0.94041 | 1011 | 64 | False | False |
| institutional_flow | TW4991 | 0.0 | 0.947858 | 1019 | 56 | True | True |
| margin_short | TW7769 | 0.0 | 0.017949 | 7 | 383 | True | True |
| margin_short | TW6919 | 0.0 | 0.038415 | 32 | 801 | True | True |
| margin_short | TW3131 | 0.110801 | 0.110801 | 119 | 955 | False | False |
| margin_short | TW6683 | 0.0 | 0.11825 | 127 | 947 | True | True |
| margin_short | TW4749 | 0.194471 | 0.194471 | 205 | 845 | False | False |
| margin_short | TW6805 | 0.425512 | 0.425512 | 458 | 617 | False | False |
| margin_short | TW6446 | 0.638734 | 0.638734 | 687 | 388 | False | False |
| margin_short | TW6789 | 0.0 | 0.741155 | 797 | 278 | True | True |
| margin_short | TW6770 | 0.895717 | 0.895717 | 963 | 112 | False | False |

## 8. available_at mismatch 分类

| category | rows | available_at_lt_next_trading_day_rows | prohibited_early_visible_rows | same_or_before_trade_date_rows | exact_t1_rows | delayed_rows | missing_calendar_rows | max_delay_days | reason_counts | pit_safe_delayed_pass |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| institutional_flow | 208059 | 2 | 0 | 0 | 207464 | 396 | 197 | 664 | calendar_gap:12|exact_t1:207464|listing_status_gap:386|missing_calendar:197 | yes |
| margin_short | 203123 | 2 | 0 | 0 | 202925 | 3 | 193 | 1 | calendar_gap:5|exact_t1:202925|missing_calendar:193 | yes |

## 9. 是否存在提前可见行

- `available_at <= trade_date` prohibited early-visible rows：`0`。
- `available_at <= trade_date` rows 见 `available_at_contract_audit.csv`；若非零则不得进入 O2。

## 10. 合同建议

O1R 不建议继续使用 strict exact T+1 作为唯一合同，因为 combined archive 中存在 delayed availability / listing_status_gap / calendar_gap 行。

建议采用：

```text
available_at >= next_trading_day(trade_date)
```

后续 O2 必须保留 `delay_days` 与 `delay_reason`，并按真实 `available_at` 做 as-of join；不得把 delayed availability 静默当作 exact T+1，也不得人工提前 `available_at`。

## 11. 是否允许进入 O2

- 当前执行建议：`phase_o1r_needs_user_confirmation_for_delayed_availability_contract`。
- 如审查者接受 PIT-safe delayed availability 合同，且确认低覆盖行只能 neutral fill + missing flag，不删行，则可进入 O2。
- 如必须坚持 exact T+1，则本轮不通过，需要继续修复日历/上市状态或剔除不满足合同的数据族。

## 12. 是否触发用户确认

- 是。available_at 合同从 `exact T+1` 调整为 `PIT-safe delayed availability` 属于主线合同选择，必须用户/审查确认。

## 13. 输出产物

- `data_tw/experiments/ltr_orthogonal_features_controlled/phase_o1r_coverage_available_at_repair/absent_symbol_fetch_attempts.csv`
- `data_tw/experiments/ltr_orthogonal_features_controlled/phase_o1r_coverage_available_at_repair/coverage_before_after.csv`
- `data_tw/experiments/ltr_orthogonal_features_controlled/phase_o1r_coverage_available_at_repair/fetch_error_summary.csv`
- `data_tw/experiments/ltr_orthogonal_features_controlled/phase_o1r_coverage_available_at_repair/raw_archive_manifest.csv`
- `data_tw/experiments/ltr_orthogonal_features_controlled/phase_o1r_coverage_available_at_repair/available_at_contract_audit.csv`
- `data_tw/experiments/ltr_orthogonal_features_controlled/phase_o1r_coverage_available_at_repair/available_at_mismatch_classification.csv`
- `data_tw/experiments/ltr_orthogonal_features_controlled/phase_o1r_coverage_available_at_repair/coverage_after_summary.csv`
- `data_tw/experiments/ltr_orthogonal_features_controlled/phase_o1r_coverage_available_at_repair/phaseo1r_summary.json`
