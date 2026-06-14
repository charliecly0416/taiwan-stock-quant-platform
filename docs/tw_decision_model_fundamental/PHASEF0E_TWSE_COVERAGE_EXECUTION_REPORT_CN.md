# Phase F0E TWSE-only Coverage Diagnosis 执行报告

- 生成时间：`2026-06-11T17:06:39+00:00`
- 阶段目标：只评估 TWSE-only 官方月营收覆盖和历史可得性，不构建样本、不训练模型、不写 provider。
- 执行范围：TWSE listed monthly revenue OpenAPI / official download candidate；本地 qlib Top50/Top150 历史 symbol 覆盖率统计。
- 禁止范围执行情况：未追 TPEx/OTC、未接受 FinMind `date/create_time` 为公告日、未 period-only join、未构建 F1 样本、未做单因子检验、未做规则 baseline、未训练模型、未写 provider、未 refresh/publish、未 accepted latest switching、未 materialize 到 qlib、未前端/API、未 monitor、未交易路径。

## 1. 修改文件

- 新增 `scripts/diagnose_tw_decision_fundamental_phasef0e_twse_coverage.py`

## 2. 生成文件

- `data_tw/experiments/decision_fundamental/phasef0e_twse_official_coverage_inventory.csv`
- `data_tw/experiments/decision_fundamental/phasef0e_twse_symbol_coverage.csv`
- `data_tw/experiments/decision_fundamental/phasef0e_gate_summary.json`
- `docs/tw_decision_model_fundamental/PHASEF0E_TWSE_COVERAGE_EXECUTION_REPORT_CN.md`

## 3. TWSE 官方源历史可得性

- current_source_periods：`['2026-04']`
- current_announcement_dates：`['2026-05-17']`
- current_twse_symbol_count：`1078`
- historical_access_proven：`False`
- official_row_level_announcement_date：`True`

| probe_name | http_status | json_ok | row_count | source_periods | announcement_dates | same_payload_as_base | proves_historical_access | notes |
|---|---:|---|---:|---|---|---|---|---|
| base_current | 200 | true | 1078 | 2026-04 | 2026-05-17 | false | false | current official file |
| param_date_current_ad | 200 | true | 1078 | 2026-04 | 2026-05-17 | true | false | parameter ignored or same current payload |
| param_date_prev_ad | 200 | true | 1078 | 2026-04 | 2026-05-17 | true | false | parameter ignored or same current payload |
| param_yyyymm_prev_ad | 200 | true | 1078 | 2026-04 | 2026-05-17 | true | false | parameter ignored or same current payload |
| param_roc_year_month_prev | 200 | true | 1078 | 2026-04 | 2026-05-17 | true | false | parameter ignored or same current payload |

## 4. TWSE-only Symbol 覆盖率

| universe_name | unique_symbols | twse_covered_symbols | unique_symbol_coverage_ratio | row_count | twse_covered_rows | row_weighted_coverage_ratio | first_asof | last_asof |
|---|---:|---:|---:|---:|---:|---:|---|---|
| phase1b_repaired_full_top150 | 103 | 81 | 0.7864 | 106440 | 84859 | 0.7972 | 2022-01-04 00:00:00 | 2026-05-29 00:00:00 |
| phase1b_repaired_full_top50 | 103 | 81 | 0.7864 | 51599 | 40968 | 0.7940 | 2022-01-04 00:00:00 | 2026-05-29 00:00:00 |
| pred_fast_2023_top150 | 283 | 203 | 0.7173 | 35850 | 27534 | 0.7680 | 2023-01-03 | 2023-12-29 |
| pred_fast_2023_top50 | 282 | 203 | 0.7199 | 11950 | 9044 | 0.7568 | 2023-01-03 | 2023-12-29 |

## 5. available_at 处理建议

- F0E 不构建样本，因此没有实际写入样本级 `available_at`。
- 若后续进入 F1，建议采用保守规则：`available_at = next_trading_day(announcement_date)`，避免无法证明公告时点在当日交易前可见时产生泄漏。
- 当前 TWSE 文件示例：announcement_date=`2026-05-17`，next_trading_day=`2026-05-18`。

## 6. F0E Gate

- recommended_gate：`stop_fundamental_mainline_insufficient_coverage=true`
- gate_reason：TWSE OpenAPI exposes only the current source_period in this smoke; parameterized historical access was not proven, so a PIT archive cannot be formed.

## 7. 安全边界

- f1_sample=false
- model_training=false
- provider_write=false
- accepted_latest_switching=false
- frontend_api=false
- trading_or_order=false
- monitor_writes=false
- target_position_or_weight=false
- 未输出买入/卖出建议、收益承诺或上涨概率承诺。

## 8. 风险与待审查问题

- TWSE 当前 OpenAPI 只证明当前公开 source_period 可得；参数化 smoke 未证明历史月份可得。
- Top50/Top150 覆盖率对 TWSE-only 子集并非为 100%，排除非上市 symbol 会减少历史 ranking 样本面。
- 在没有连续多个 official source_period 前，不满足进入 F1 的最低条件。
