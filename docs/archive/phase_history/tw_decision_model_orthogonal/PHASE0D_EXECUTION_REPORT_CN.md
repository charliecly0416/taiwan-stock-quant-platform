# Phase 0D PIT 修复与 Gate Confirmation 执行报告

## 1. 执行范围

- 执行日期：`2026-06-10T17:20:49+00:00`
- 阶段目标：基于既有 Phase0C raw archive 做不联网 PIT 修复与 gate confirmation。
- 本阶段未联网、未重跑 FinMind、未新增数据源、未扩大时间范围或 symbol universe。
- 未执行：月营收、materialize derived features、Qlib bin/provider、accepted latest switching、Phase1 样本、单因子检验、模型训练、规则 baseline、前端/API、broker/orders/quick-trade/target position/target weight。

## 2. 修改文件

- 新增 `scripts/confirm_tw_decision_orthogonal_phase0d_pit_gate.py`。
- 新增 `docs/tw_decision_model_orthogonal/PHASE0D_EXECUTION_REPORT_CN.md`。

## 3. 生成文件

- `data_tw/experiments/decision_orthogonal/phase0d_pit_clean/`
- `data_tw/experiments/decision_orthogonal/phase0d_pit_clean_manifest.csv`
- `data_tw/experiments/decision_orthogonal/phase0d_pit_valid_coverage_report.csv`
- `data_tw/experiments/decision_orthogonal/phase0d_quality_flags_summary.csv`
- `data_tw/experiments/decision_orthogonal/phase0d_phase1_allowed_fields.csv`
- `docs/tw_decision_model_orthogonal/PHASE0D_EXECUTION_REPORT_CN.md`

## 4. 数据来源

- Phase0C normalized raw archive：`data_tw/experiments/decision_orthogonal/phase0c_raw_archive/`。
- 本地交易日历来源：`qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/normalized_nonempty/*.csv` 的 `date` 列。
- 交易日历窗口：从 raw archive 最早交易日至最后交易日后 `10` 个自然日。

## 5. Point-in-Time 处理

- 保守可见性规则继续采用：`available_at = next_trading_day(trade_date)`。
- `available_at` 不是官方发布时间声明，只是 Phase0D 继续验证所用的保守 T+1 可见性规则。
- 对 Phase0C 尾部缺失 `available_at` 的行，首选从本地价格交易日历补下一交易日。
- 不使用 `trade_date` 回填 `available_at`，不使用 `fetched_at` 作为历史可见时间。
- cleaned view 只保留 `phase1_allowed=true` 且 `available_at` 非空的行；如无法补出下一交易日则排除。

## 6. Category 汇总

| category | raw_rows | rows_with_non_empty_available_at | rows_excluded_due_to_missing_available_at | available_at_repaired_rows | avg_pit_valid_coverage_rate | avg_raw_observed_coverage_rate | extra_dates_count | missing_dates_count | duplicate_rows_count | quality_issue_count |
|---|---|---|---|---|---|---|---|---|---|---|
| institutional_flow | 5291 | 5291 | 0 | 50 | 0.9982857142857142 | 0.9982857142857142 | 50 | 9 | 0 | 50 |
| margin_short | 5300 | 5300 | 0 | 50 | 1.0 | 1.0 | 50 | 0 | 0 | 50 |

## 7. Per-Symbol 覆盖率样例

| category | symbol | expected_trading_days | raw_rows | pit_valid_rows | pit_valid_coverage_rate | raw_observed_coverage_rate | extra_dates_count | missing_dates_count | duplicate_rows_count | quality_issue_count |
|---|---|---|---|---|---|---|---|---|---|---|
| institutional_flow | TW1216 | 105 | 106 | 106 | 1.0 | 1.0 | 1 | 0 | 0 | 1 |
| institutional_flow | TW1301 | 105 | 106 | 106 | 1.0 | 1.0 | 1 | 0 | 0 | 1 |
| institutional_flow | TW1303 | 105 | 106 | 106 | 1.0 | 1.0 | 1 | 0 | 0 | 1 |
| institutional_flow | TW1504 | 105 | 105 | 105 | 0.9904761904761905 | 0.9904761904761905 | 1 | 1 | 0 | 1 |
| institutional_flow | TW1513 | 105 | 106 | 106 | 1.0 | 1.0 | 1 | 0 | 0 | 1 |
| institutional_flow | TW1519 | 105 | 106 | 106 | 1.0 | 1.0 | 1 | 0 | 0 | 1 |
| institutional_flow | TW1560 | 105 | 106 | 106 | 1.0 | 1.0 | 1 | 0 | 0 | 1 |
| institutional_flow | TW1802 | 105 | 106 | 106 | 1.0 | 1.0 | 1 | 0 | 0 | 1 |
| institutional_flow | TW1815 | 105 | 106 | 106 | 1.0 | 1.0 | 1 | 0 | 0 | 1 |
| institutional_flow | TW2027 | 105 | 106 | 106 | 1.0 | 1.0 | 1 | 0 | 0 | 1 |
| institutional_flow | TW2049 | 105 | 106 | 106 | 1.0 | 1.0 | 1 | 0 | 0 | 1 |
| institutional_flow | TW2059 | 105 | 106 | 106 | 1.0 | 1.0 | 1 | 0 | 0 | 1 |
| institutional_flow | TW2301 | 105 | 106 | 106 | 1.0 | 1.0 | 1 | 0 | 0 | 1 |
| institutional_flow | TW2303 | 105 | 106 | 106 | 1.0 | 1.0 | 1 | 0 | 0 | 1 |
| institutional_flow | TW2308 | 105 | 106 | 106 | 1.0 | 1.0 | 1 | 0 | 0 | 1 |
| institutional_flow | TW2313 | 105 | 106 | 106 | 1.0 | 1.0 | 1 | 0 | 0 | 1 |
| institutional_flow | TW2316 | 105 | 106 | 106 | 1.0 | 1.0 | 1 | 0 | 0 | 1 |
| institutional_flow | TW2317 | 105 | 105 | 105 | 0.9904761904761905 | 0.9904761904761905 | 1 | 1 | 0 | 1 |
| institutional_flow | TW2327 | 105 | 99 | 99 | 0.9333333333333333 | 0.9333333333333333 | 1 | 7 | 0 | 1 |
| institutional_flow | TW2328 | 105 | 106 | 106 | 1.0 | 1.0 | 1 | 0 | 0 | 1 |
| institutional_flow | TW2330 | 105 | 106 | 106 | 1.0 | 1.0 | 1 | 0 | 0 | 1 |
| institutional_flow | TW2344 | 105 | 106 | 106 | 1.0 | 1.0 | 1 | 0 | 0 | 1 |
| institutional_flow | TW2345 | 105 | 106 | 106 | 1.0 | 1.0 | 1 | 0 | 0 | 1 |
| institutional_flow | TW2354 | 105 | 106 | 106 | 1.0 | 1.0 | 1 | 0 | 0 | 1 |
| institutional_flow | TW2357 | 105 | 106 | 106 | 1.0 | 1.0 | 1 | 0 | 0 | 1 |
| institutional_flow | TW2359 | 105 | 106 | 106 | 1.0 | 1.0 | 1 | 0 | 0 | 1 |
| institutional_flow | TW2360 | 105 | 106 | 106 | 1.0 | 1.0 | 1 | 0 | 0 | 1 |
| institutional_flow | TW2368 | 105 | 106 | 106 | 1.0 | 1.0 | 1 | 0 | 0 | 1 |
| institutional_flow | TW2374 | 105 | 106 | 106 | 1.0 | 1.0 | 1 | 0 | 0 | 1 |
| institutional_flow | TW2376 | 105 | 106 | 106 | 1.0 | 1.0 | 1 | 0 | 0 | 1 |

## 8. Quality Flags 汇总样例

| category | symbol | quality_flag_reason | row_count |
|---|---|---|---|
| institutional_flow | TW1216 | none | 105 |
| institutional_flow | TW1216 | phase0c_missing_available_at_before_phase0d_repair | 1 |
| institutional_flow | TW1216 | phase0d_available_at_repaired_from_local_calendar | 1 |
| institutional_flow | TW1301 | none | 105 |
| institutional_flow | TW1301 | phase0c_missing_available_at_before_phase0d_repair | 1 |
| institutional_flow | TW1301 | phase0d_available_at_repaired_from_local_calendar | 1 |
| institutional_flow | TW1303 | none | 105 |
| institutional_flow | TW1303 | phase0c_missing_available_at_before_phase0d_repair | 1 |
| institutional_flow | TW1303 | phase0d_available_at_repaired_from_local_calendar | 1 |
| institutional_flow | TW1504 | none | 104 |
| institutional_flow | TW1504 | phase0c_missing_available_at_before_phase0d_repair | 1 |
| institutional_flow | TW1504 | phase0d_available_at_repaired_from_local_calendar | 1 |
| institutional_flow | TW1513 | none | 105 |
| institutional_flow | TW1513 | phase0c_missing_available_at_before_phase0d_repair | 1 |
| institutional_flow | TW1513 | phase0d_available_at_repaired_from_local_calendar | 1 |
| institutional_flow | TW1519 | none | 105 |
| institutional_flow | TW1519 | phase0c_missing_available_at_before_phase0d_repair | 1 |
| institutional_flow | TW1519 | phase0d_available_at_repaired_from_local_calendar | 1 |
| institutional_flow | TW1560 | none | 105 |
| institutional_flow | TW1560 | phase0c_missing_available_at_before_phase0d_repair | 1 |
| institutional_flow | TW1560 | phase0d_available_at_repaired_from_local_calendar | 1 |
| institutional_flow | TW1802 | none | 105 |
| institutional_flow | TW1802 | phase0c_missing_available_at_before_phase0d_repair | 1 |
| institutional_flow | TW1802 | phase0d_available_at_repaired_from_local_calendar | 1 |
| institutional_flow | TW1815 | none | 105 |
| institutional_flow | TW1815 | phase0c_missing_available_at_before_phase0d_repair | 1 |
| institutional_flow | TW1815 | phase0d_available_at_repaired_from_local_calendar | 1 |
| institutional_flow | TW2027 | none | 105 |
| institutional_flow | TW2027 | phase0c_missing_available_at_before_phase0d_repair | 1 |
| institutional_flow | TW2027 | phase0d_available_at_repaired_from_local_calendar | 1 |
| institutional_flow | TW2049 | none | 105 |
| institutional_flow | TW2049 | phase0c_missing_available_at_before_phase0d_repair | 1 |
| institutional_flow | TW2049 | phase0d_available_at_repaired_from_local_calendar | 1 |
| institutional_flow | TW2059 | none | 105 |
| institutional_flow | TW2059 | phase0c_missing_available_at_before_phase0d_repair | 1 |
| institutional_flow | TW2059 | phase0d_available_at_repaired_from_local_calendar | 1 |
| institutional_flow | TW2301 | none | 105 |
| institutional_flow | TW2301 | phase0c_missing_available_at_before_phase0d_repair | 1 |
| institutional_flow | TW2301 | phase0d_available_at_repaired_from_local_calendar | 1 |
| institutional_flow | TW2303 | none | 105 |

## 9. 可进入后续审查字段

| category | field | phase1_allowed | status | notes |
|---|---|---|---|---|
| institutional_flow | foreign_net_buy / investment_trust_net_buy / dealer_net_buy / institutional_total_net_buy | true | review_required_phase0d_pass | T+1 is conservative visibility, not official publication timestamp. |
| margin_short | margin_balance / margin_balance_change / short_balance / short_balance_change | true | review_required_phase0d_pass | T+1 is conservative visibility, not official publication timestamp. |
| monthly_revenue | all monthly revenue fields | false | deferred_not_authorized | Phase0C/Phase0D did not authorize monthly revenue data. |

## 10. Phase 0D Gate

- 是否满足 Phase0D PIT gate：`True`。
- 即使 Phase0D gate 为 true，也不代表已进入 Phase1；必须等待审查者给出下一步授权。

## 11. 安全边界

- 禁止联网：未触碰。
- provider refresh/publish：未触碰。
- accepted latest switching：未触碰。
- materialize/screen/ablation：未执行。
- Phase1 样本：未构建。
- 单因子检验/模型训练：未执行。
- broker/orders/quick-trade/target position/target weight：未触碰。
- 前端/API：未触碰。
- 真实交易建议语义：未生成。

## 12. 风险与待审查问题

- T+1 规则仍是保守可见性 proxy，不是官方发布时间证据；是否接受进入 Phase1 仍需审查者确认。
- 月营收仍未授权且 deferred。
- Phase0D 只确认 POC archive 的 PIT-clean 可用性，不代表允许扩大 universe、补齐历史或构建 Phase1 样本。
