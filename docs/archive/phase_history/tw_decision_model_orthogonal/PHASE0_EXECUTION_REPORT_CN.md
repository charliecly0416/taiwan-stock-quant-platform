# 正交数据 Decision Model Phase 0 执行报告

## 1. 执行范围

- 执行日期：`2026-06-10T16:44:24+00:00`
- 范围：只读审计法人筹码、融资融券、月营收三类正交数据的本地可用性与 point-in-time 证据。
- 禁止项执行情况：未训练模型，未构建 Phase 1 样本，未做单因子检验，未做组合回放，未接前端/API，未触发 provider refresh/publish，未切换 accepted latest，未触碰 broker/orders/quick-trade/target position/monitor config/alerts。

## 2. 修改文件

- 新增 `scripts/audit_tw_decision_orthogonal_phase0.py`。

## 3. 生成文件

- `data_tw/experiments/decision_orthogonal/phase0_data_sources.json`
- `data_tw/experiments/decision_orthogonal/phase0_feature_availability.csv`
- `data_tw/experiments/decision_orthogonal/phase0_point_in_time_rules.md`
- `docs/tw_decision_model_orthogonal/PHASE0_EXECUTION_REPORT_CN.md`

## 4. 数据源清单

| category | source_name | file_or_table_exists | row_count | symbol_count | first_date | last_date | has_announcement_date | has_available_at | has_source_period | pit_status |
|---|---|---|---|---|---|---|---|---|---|---|
| institutional_flow | finmind_institutional_trades | True | 0 | 0 | None | None | False | False | False | fail |
| margin_short | finmind_margin_trading | True | 0 | 0 | None | None | False | False | False | fail |
| monthly_revenue | finmind_monthly_revenue | True | 0 | 0 | None | None | False | False | False | fail |

## 5. PIT 规则摘要

- 法人筹码：需要 trade_date + row-level `available_at` 或可审计 T+1 可见规则；当前本地 row_count=0，不能进入 Phase 1。
- 融资融券：需要 trade_date + row-level `available_at` 或可审计 T+1 可见规则，并能计算 `days_since_last_report`；当前本地 row_count=0，不能进入 Phase 1。
- 月营收：必须同时保留 `source_period` 与 `announcement_date`/`available_at`；禁止按所属月份直接 join；当前本地 row_count=0 且无公告日期证据，不能进入 Phase 1。

## 6. 覆盖率 / 缺失率摘要

| category | feature_count | phase1_allowed_count | failed_or_deferred_count | source_row_count | pit_status |
|---|---|---|---|---|---|
| institutional_flow | 7 | 0 | 7 | 0 | fail |
| margin_short | 6 | 0 | 6 | 0 | fail |
| monthly_revenue | 6 | 0 | 6 | 0 | fail |

## 7. 可进入 Phase 1 的字段清单

_no rows_

## 8. Deferred / Fail 字段清单

| category | feature_name | pit_status | deferred_or_fail_reason |
|---|---|---|---|
| institutional_flow | foreign_net_buy | fail | No local archived rows were found for this category; cannot compute feature or prove PIT availability. |
| institutional_flow | investment_trust_net_buy | fail | No local archived rows were found for this category; cannot compute feature or prove PIT availability. |
| institutional_flow | dealer_net_buy | fail | No local archived rows were found for this category; cannot compute feature or prove PIT availability. |
| institutional_flow | institutional_total_net_buy | fail | No local archived rows were found for this category; cannot compute feature or prove PIT availability. |
| institutional_flow | institutional_consecutive_net_buy_days | fail | No local archived rows were found for this category; cannot compute feature or prove PIT availability. |
| institutional_flow | institutional_net_buy_volume_ratio | fail | No local archived rows were found for this category; cannot compute feature or prove PIT availability. |
| institutional_flow | foreign_trust_direction_sync | fail | No local archived rows were found for this category; cannot compute feature or prove PIT availability. |
| margin_short | margin_balance_change | fail | No local archived rows were found for this category; cannot compute feature or prove PIT availability. |
| margin_short | short_balance_change | fail | No local archived rows were found for this category; cannot compute feature or prove PIT availability. |
| margin_short | margin_usage_proxy | fail | No local archived rows were found for this category; cannot compute feature or prove PIT availability. |
| margin_short | short_covering_proxy | fail | No local archived rows were found for this category; cannot compute feature or prove PIT availability. |
| margin_short | margin_fast_increase_high_price | fail | No local archived rows were found for this category; cannot compute feature or prove PIT availability. |
| margin_short | margin_decline_price_resilience | fail | No local archived rows were found for this category; cannot compute feature or prove PIT availability. |
| monthly_revenue | monthly_revenue_yoy | fail | No local archived rows were found for this category; cannot compute feature or prove PIT availability. |
| monthly_revenue | monthly_revenue_mom | fail | No local archived rows were found for this category; cannot compute feature or prove PIT availability. |
| monthly_revenue | monthly_revenue_yoy_improvement_streak | fail | No local archived rows were found for this category; cannot compute feature or prove PIT availability. |
| monthly_revenue | monthly_revenue_yoy_3m_mean | fail | No local archived rows were found for this category; cannot compute feature or prove PIT availability. |
| monthly_revenue | monthly_revenue_yoy_3m_slope | fail | No local archived rows were found for this category; cannot compute feature or prove PIT availability. |
| monthly_revenue | monthly_revenue_days_since_last_report | fail | No local archived rows were found for this category; cannot compute feature or prove PIT availability. |

## 9. Phase 0 Gate

- 是否满足 Phase 0 Gate：`False`。
- 结论：三类正交数据当前均未发现本地可用 PIT 行级数据，且没有任何字段 `phase1_allowed=true`。按审查文档，本主线不应进入 Phase 1，除非用户后续确认新数据源或安全的数据补齐/PIT 归档工作。

## 10. 安全边界

- broker/orders/quick-trade/target position：未触碰。
- provider refresh/publish：未触碰。
- accepted latest switching：未触碰。
- monitor config/alerts：未触碰。
- 真实交易建议语义：未生成。

## 11. 需要审查者或用户确认的问题

- 若要继续该正交数据主线，需要用户确认是否允许新增或补齐法人筹码、融资融券、月营收数据源，并要求每行具备 `available_at` / `announcement_date` / `source_period` 等 PIT 字段。
- 在确认前，不建议进入 Phase 1。

## 12. 只读扫描证据

- FinMind summary paths：`['qlib_pipeline/data_tw/experiments/option_c_historical_signal_backfill/option_c_historical_backfill_20260101_20260531/finmind_archive_apply_summary.json']`
- daily finmind stdout count：`12`
- daily auto job summary：`{'job_count_with_finmind_context': 86, 'disabled_flag_counts': {'--no-institutional': 12, '--no-margin': 12, '--no-monthly-revenue': 12}, 'sample_job_paths': ['data_tw/ops/daily_auto_update/daily_tw_stock_auto_update_20260602_20260603T035233Z/job.json', 'data_tw/ops/daily_auto_update/daily_tw_stock_auto_update_20260602_20260603T035247Z/job.json', 'data_tw/ops/daily_auto_update/daily_tw_stock_auto_update_20260602_20260603T040342Z/job.json', 'data_tw/ops/daily_auto_update/daily_tw_stock_auto_update_20260602_20260603T040354Z/job.json', 'data_tw/ops/daily_auto_update/daily_tw_stock_auto_update_20260603_20260603T171533Z/job.json']}`
