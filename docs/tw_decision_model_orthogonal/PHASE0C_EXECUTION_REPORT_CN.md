# Phase 0C 受限 POC Raw Archive 执行报告

## 1. 执行范围

- 执行日期：`2026-06-10T17:11:25+00:00`
- 范围：仅对法人筹码与融资融券做 FinMind POC raw archive，并生成 PIT 审计产物。
- 未执行：月营收、materialize derived features、Qlib bin/provider、accepted latest switching、Phase 1 样本、单因子检验、模型训练、规则 baseline、组合回放、前端/API、broker/orders/quick-trade/target position。

## 2. 实际联网/下载命令

- `python scripts/build_tw_decision_orthogonal_phase0c_raw_archive.py --start 2025-05-01 --end 2025-09-30 --max-symbols 50 --sleep 0.15 --timeout 30.0`

## 3. 修改文件

- 新增 `scripts/build_tw_decision_orthogonal_phase0c_raw_archive.py`。

## 4. 生成文件

- `data_tw/experiments/decision_orthogonal/phase0c_raw_archive/`
- `data_tw/experiments/decision_orthogonal/phase0c_download_status.csv`
- `data_tw/experiments/decision_orthogonal/phase0c_pit_snapshot_manifest.csv`
- `data_tw/experiments/decision_orthogonal/phase0c_coverage_report.csv`
- `data_tw/experiments/decision_orthogonal/phase0c_pit_validation_samples.csv`
- `docs/tw_decision_model_orthogonal/PHASE0C_EXECUTION_REPORT_CN.md`

## 5. 数据源与 endpoint

- endpoint：`https://api.finmindtrade.com/api/v4/data`
- institutional dataset：`TaiwanStockInstitutionalInvestorsBuySell`
- margin dataset：`TaiwanStockMarginPurchaseShortSale`

## 6. 时间范围与股票范围

- start：`2025-05-01`
- end：`2025-09-30`
- max_symbols：`50`
- actual_symbols：`50`

## 7. Raw Archive 摘要

| category | request_count | success_count | failed_count | raw_rows | symbol_count | avg_coverage_rate |
|---|---|---|---|---|---|---|
| institutional_flow | 50 | 50 | 0 | 5291 | 50 | 0.9982857142857142 |
| margin_short | 50 | 50 | 0 | 5300 | 50 | 1.0 |

## 8. 下载成功/失败统计

| category | symbol | stock_id | status | row_count | error_type | error_message |
|---|---|---|---|---|---|---|
| institutional_flow | TW1216 | 1216 | success | 530 |  |  |
| institutional_flow | TW1301 | 1301 | success | 530 |  |  |
| institutional_flow | TW1303 | 1303 | success | 530 |  |  |
| institutional_flow | TW1504 | 1504 | success | 525 |  |  |
| institutional_flow | TW1513 | 1513 | success | 530 |  |  |
| institutional_flow | TW1519 | 1519 | success | 530 |  |  |
| institutional_flow | TW1560 | 1560 | success | 530 |  |  |
| institutional_flow | TW1802 | 1802 | success | 530 |  |  |
| institutional_flow | TW1815 | 1815 | success | 530 |  |  |
| institutional_flow | TW2027 | 2027 | success | 530 |  |  |
| institutional_flow | TW2049 | 2049 | success | 530 |  |  |
| institutional_flow | TW2059 | 2059 | success | 530 |  |  |
| institutional_flow | TW2301 | 2301 | success | 530 |  |  |
| institutional_flow | TW2303 | 2303 | success | 530 |  |  |
| institutional_flow | TW2308 | 2308 | success | 530 |  |  |
| institutional_flow | TW2313 | 2313 | success | 530 |  |  |
| institutional_flow | TW2316 | 2316 | success | 530 |  |  |
| institutional_flow | TW2317 | 2317 | success | 525 |  |  |
| institutional_flow | TW2327 | 2327 | success | 495 |  |  |
| institutional_flow | TW2328 | 2328 | success | 530 |  |  |

## 9. 覆盖率与缺失率

| category | symbol | expected_trading_days | observed_rows | coverage_rate | missing_dates_count | duplicate_rows_count | quality_issue_count |
|---|---|---|---|---|---|---|---|
| institutional_flow | TW1216 | 105 | 106 | 1.0 | 0 | 0 | 1 |
| institutional_flow | TW1301 | 105 | 106 | 1.0 | 0 | 0 | 1 |
| institutional_flow | TW1303 | 105 | 106 | 1.0 | 0 | 0 | 1 |
| institutional_flow | TW1504 | 105 | 105 | 0.9904761904761905 | 1 | 0 | 1 |
| institutional_flow | TW1513 | 105 | 106 | 1.0 | 0 | 0 | 1 |
| institutional_flow | TW1519 | 105 | 106 | 1.0 | 0 | 0 | 1 |
| institutional_flow | TW1560 | 105 | 106 | 1.0 | 0 | 0 | 1 |
| institutional_flow | TW1802 | 105 | 106 | 1.0 | 0 | 0 | 1 |
| institutional_flow | TW1815 | 105 | 106 | 1.0 | 0 | 0 | 1 |
| institutional_flow | TW2027 | 105 | 106 | 1.0 | 0 | 0 | 1 |
| institutional_flow | TW2049 | 105 | 106 | 1.0 | 0 | 0 | 1 |
| institutional_flow | TW2059 | 105 | 106 | 1.0 | 0 | 0 | 1 |
| institutional_flow | TW2301 | 105 | 106 | 1.0 | 0 | 0 | 1 |
| institutional_flow | TW2303 | 105 | 106 | 1.0 | 0 | 0 | 1 |
| institutional_flow | TW2308 | 105 | 106 | 1.0 | 0 | 0 | 1 |
| institutional_flow | TW2313 | 105 | 106 | 1.0 | 0 | 0 | 1 |
| institutional_flow | TW2316 | 105 | 106 | 1.0 | 0 | 0 | 1 |
| institutional_flow | TW2317 | 105 | 105 | 0.9904761904761905 | 1 | 0 | 1 |
| institutional_flow | TW2327 | 105 | 99 | 0.9333333333333333 | 7 | 0 | 1 |
| institutional_flow | TW2328 | 105 | 106 | 1.0 | 0 | 0 | 1 |

## 10. available_at 规则与证据

- 规则：`available_at = next_trading_day(trade_date)`。
- 不能直接使用 `trade_date`：法人筹码与融资融券通常为盘后/日后可见数据；若在同一交易日收盘前用于 asof，会产生未来函数风险。
- FinMind/TWSE/TPEx 可见时间证据：既有仓库 POC 文档和脚本注释记录法人数据按交易日盘后发布，需要 T+1；融资融券同属日频盘后统计，本 Phase0C 采用保守 T+1，等待审查者复核。
- `fetched_at` 只表示本地抓取时间，晚于历史交易日，不能替代历史当时的官方可见时间。
- 若审查者不接受 T+1 规则，则相关字段必须 deferred，不得进入 Phase 1。

## 11. PIT validation samples 摘要

| category | symbol | trade_date | available_at | asof_example | visible_at_asof | validation_result | validation_note |
|---|---|---|---|---|---|---|---|
| institutional_flow | TW1216 | 2025-05-02 | 2025-05-05 | 2025-05-02 | False | pass | Boundary sample: trade_date asof is before conservative T+1 available_at. |
| institutional_flow | TW1216 | 2025-05-02 | 2025-05-05 | 2025-05-05 | True | pass | Positive sample: asof is available_at, row is visible. |
| institutional_flow | TW1216 | 2025-05-05 | 2025-05-06 | 2025-05-05 | False | pass | Boundary sample: trade_date asof is before conservative T+1 available_at. |
| institutional_flow | TW1216 | 2025-05-05 | 2025-05-06 | 2025-05-06 | True | pass | Positive sample: asof is available_at, row is visible. |
| institutional_flow | TW1216 | 2025-05-06 | 2025-05-07 | 2025-05-06 | False | pass | Boundary sample: trade_date asof is before conservative T+1 available_at. |
| institutional_flow | TW1216 | 2025-05-06 | 2025-05-07 | 2025-05-07 | True | pass | Positive sample: asof is available_at, row is visible. |
| institutional_flow | TW1216 | 2025-05-07 | 2025-05-08 | 2025-05-07 | False | pass | Boundary sample: trade_date asof is before conservative T+1 available_at. |
| institutional_flow | TW1216 | 2025-05-07 | 2025-05-08 | 2025-05-08 | True | pass | Positive sample: asof is available_at, row is visible. |
| institutional_flow | TW1216 | 2025-05-08 | 2025-05-09 | 2025-05-08 | False | pass | Boundary sample: trade_date asof is before conservative T+1 available_at. |
| institutional_flow | TW1216 | 2025-05-08 | 2025-05-09 | 2025-05-09 | True | pass | Positive sample: asof is available_at, row is visible. |
| institutional_flow | TW1216 | 2025-05-09 | 2025-05-12 | 2025-05-09 | False | pass | Boundary sample: trade_date asof is before conservative T+1 available_at. |
| institutional_flow | TW1216 | 2025-05-09 | 2025-05-12 | 2025-05-12 | True | pass | Positive sample: asof is available_at, row is visible. |
| institutional_flow | TW1216 | 2025-05-12 | 2025-05-13 | 2025-05-12 | False | pass | Boundary sample: trade_date asof is before conservative T+1 available_at. |
| institutional_flow | TW1216 | 2025-05-12 | 2025-05-13 | 2025-05-13 | True | pass | Positive sample: asof is available_at, row is visible. |
| institutional_flow | TW1216 | 2025-05-13 | 2025-05-14 | 2025-05-13 | False | pass | Boundary sample: trade_date asof is before conservative T+1 available_at. |
| institutional_flow | TW1216 | 2025-05-13 | 2025-05-14 | 2025-05-14 | True | pass | Positive sample: asof is available_at, row is visible. |
| margin_short | TW1216 | 2025-05-02 | 2025-05-05 | 2025-05-02 | False | pass | Boundary sample: trade_date asof is before conservative T+1 available_at. |
| margin_short | TW1216 | 2025-05-02 | 2025-05-05 | 2025-05-05 | True | pass | Positive sample: asof is available_at, row is visible. |
| margin_short | TW1216 | 2025-05-05 | 2025-05-06 | 2025-05-05 | False | pass | Boundary sample: trade_date asof is before conservative T+1 available_at. |
| margin_short | TW1216 | 2025-05-05 | 2025-05-06 | 2025-05-06 | True | pass | Positive sample: asof is available_at, row is visible. |

## 12. 可进入后续审查的字段

| category | field | status |
|---|---|---|
| institutional_flow | foreign_net_buy / investment_trust_net_buy / dealer_net_buy / institutional_total_net_buy | review_required |
| margin_short | margin_balance / margin_balance_change / short_balance / short_balance_change | review_required |
| monthly_revenue | all monthly revenue fields | deferred_phase0c_not_authorized |

## 13. Deferred / Fail 字段与原因

- 月营收：Phase0C 未授权，全部 deferred。
- 若任一类别 raw_rows=0，则该类别 fail，等待审查者判断是否重试或停止。
- 若 T+1 `available_at` 证据不被接受，则法人/融资融券字段 deferred。

## 14. Phase 0C Gate

- 是否满足 Phase 0C Gate：`True`。
- 即使 Gate 为 true，也不能进入 Phase 1，必须等待审查者审查 PIT、覆盖率和未来函数风险。

## 15. 安全边界

- provider refresh/publish：未触碰。
- accepted latest switching：未触碰。
- materialize/screen/ablation：未执行。
- broker/orders/quick-trade/target position/target weight：未触碰。
- 前端/API：未触碰。
- 真实交易建议语义：未生成。

## 16. 需要审查者或用户确认的问题

- 是否接受法人筹码与融资融券的保守 T+1 `available_at` 规则。
- 当前 POC 覆盖率是否足以进入更大范围补齐审查。
- 是否允许后续补齐更长时间范围或更多 symbol。
- 月营收是否继续暂缓，或另行授权新增具备公告日期的数据源。
