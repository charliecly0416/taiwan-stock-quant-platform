# Phase 0E 扩展 Raw Archive Backfill 执行报告

## 1. 执行范围

- 执行日期：`2026-06-10T18:06:34+00:00`
- 阶段目标：对法人筹码与融资融券做扩展 raw archive backfill，并生成 PIT 审计产物。
- 未执行：月营收、全市场补齐、materialize derived features、Qlib bin/provider 写入、provider refresh/publish、accepted latest switching、Phase 1 样本、单因子检验、模型训练、规则 baseline、Phase 2、前端/API、broker/orders/quick-trade/target position/target weight。

## 2. 实际联网/下载命令

- 脱敏命令：`python scripts/build_tw_decision_orthogonal_phase0e_raw_archive.py --token-stdin --start 2022-01-01 --end 2026-06-10 --max-symbols 150 --sleep 0.08 --timeout 45.0`
- 命令记录不包含 token 原文。

## 3. 是否使用 Scrapling

- `scrapling_used=false`。
- 本次使用 FinMind API endpoint；未使用 Scrapling。

## 4. 是否使用 API Token

- `token_used=true`。
- token 来源：`用户提供 token，运行时临时注入`。
- 未在脚本、CSV、JSON、Markdown、日志或错误信息中写入 token 原文。

## 5. 修改文件

- 新增 `scripts/build_tw_decision_orthogonal_phase0e_raw_archive.py`。
- 更新 `docs/tw_decision_model_orthogonal/PHASE0E_EXECUTION_REPORT_CN.md`。

## 6. 生成文件

- `data_tw/experiments/decision_orthogonal/phase0e_raw_archive/`
- `data_tw/experiments/decision_orthogonal/phase0e_download_status.csv`
- `data_tw/experiments/decision_orthogonal/phase0e_pit_snapshot_manifest.csv`
- `data_tw/experiments/decision_orthogonal/phase0e_coverage_report.csv`
- `data_tw/experiments/decision_orthogonal/phase0e_pit_validation_samples.csv`
- `data_tw/experiments/decision_orthogonal/phase0e_quality_flags_summary.csv`
- `docs/tw_decision_model_orthogonal/PHASE0E_EXECUTION_REPORT_CN.md`

## 7. 数据源、endpoint、source_url

- endpoint/source_url：`https://api.finmindtrade.com/api/v4/data`
- institutional dataset：`TaiwanStockInstitutionalInvestorsBuySell`
- margin dataset：`TaiwanStockMarginPurchaseShortSale`

## 8. 时间范围与股票范围

- start：`2022-01-01`
- end：`2026-06-10`
- max_symbols：`150`
- actual_symbols：`150`
- universe 选择：`tw_liquid_dyn` 与时间窗口重叠的 symbol，按窗口内 active days 排序取 Top150；不是全市场。

## 9. Raw Archive 摘要

| category | request_count | success_count | failed_count | pit_normalized_rows | excluded_missing_available_at_rows | symbol_count | avg_pit_valid_coverage_rate |
|---|---|---|---|---|---|---|---|
| institutional_flow | 150 | 150 | 0 | 158834 | 1529 | 150 | 0.996827947049235 |
| margin_short | 150 | 150 | 0 | 156021 | 1529 | 150 | 0.980837088123374 |

## 10. 下载成功/失败统计

| category | symbol | stock_id | status | row_count | error_type | error_message | token_used |
|---|---|---|---|---|---|---|---|
| institutional_flow | TW2303 | 2303 | success | 5365 |  |  | True |
| institutional_flow | TW2308 | 2308 | success | 5361 |  |  | True |
| institutional_flow | TW2317 | 2317 | success | 5360 |  |  | True |
| institutional_flow | TW2327 | 2327 | success | 5295 |  |  | True |
| institutional_flow | TW2330 | 2330 | success | 5365 |  |  | True |
| institutional_flow | TW2345 | 2345 | success | 5365 |  |  | True |
| institutional_flow | TW2357 | 2357 | success | 5365 |  |  | True |
| institutional_flow | TW2368 | 2368 | success | 5330 |  |  | True |
| institutional_flow | TW2379 | 2379 | success | 5365 |  |  | True |
| institutional_flow | TW2454 | 2454 | success | 5365 |  |  | True |
| institutional_flow | TW2603 | 2603 | success | 5330 |  |  | True |
| institutional_flow | TW2881 | 2881 | success | 5365 |  |  | True |
| institutional_flow | TW2882 | 2882 | success | 5365 |  |  | True |
| institutional_flow | TW2891 | 2891 | success | 5365 |  |  | True |
| institutional_flow | TW3008 | 3008 | success | 5365 |  |  | True |
| institutional_flow | TW3017 | 3017 | success | 5365 |  |  | True |
| institutional_flow | TW3034 | 3034 | success | 5365 |  |  | True |
| institutional_flow | TW3037 | 3037 | success | 5360 |  |  | True |
| institutional_flow | TW3443 | 3443 | success | 5365 |  |  | True |
| institutional_flow | TW3529 | 3529 | success | 5365 |  |  | True |
| institutional_flow | TW3661 | 3661 | success | 5365 |  |  | True |
| institutional_flow | TW3711 | 3711 | success | 5365 |  |  | True |
| institutional_flow | TW5274 | 5274 | success | 5365 |  |  | True |
| institutional_flow | TW6669 | 6669 | success | 5365 |  |  | True |
| institutional_flow | TW8299 | 8299 | success | 5365 |  |  | True |
| institutional_flow | TW2382 | 2382 | success | 5365 |  |  | True |
| institutional_flow | TW5269 | 5269 | success | 5360 |  |  | True |
| institutional_flow | TW2376 | 2376 | success | 5365 |  |  | True |
| institutional_flow | TW2609 | 2609 | success | 5365 |  |  | True |
| institutional_flow | TW6488 | 6488 | success | 5360 |  |  | True |

## 11. 覆盖率、缺失率、重复行、Quality Flags

| category | symbol | expected_trading_days | raw_rows | pit_valid_rows | pit_valid_coverage_rate | missing_dates_count | extra_dates_count | duplicate_rows_count | quality_issue_count |
|---|---|---|---|---|---|---|---|---|---|
| institutional_flow | TW2303 | 1065 | 1073 | 1065 | 0.9990610328638497 | 1 | 8 | 0 | 8 |
| institutional_flow | TW2308 | 1065 | 1073 | 1065 | 0.9990610328638497 | 1 | 8 | 0 | 8 |
| institutional_flow | TW2317 | 1065 | 1072 | 1064 | 0.9981220657276996 | 2 | 8 | 0 | 8 |
| institutional_flow | TW2327 | 1065 | 1059 | 1051 | 0.9859154929577465 | 15 | 8 | 0 | 8 |
| institutional_flow | TW2330 | 1065 | 1073 | 1065 | 0.9990610328638497 | 1 | 8 | 0 | 8 |
| institutional_flow | TW2345 | 1065 | 1073 | 1065 | 0.9990610328638497 | 1 | 8 | 0 | 8 |
| institutional_flow | TW2357 | 1065 | 1073 | 1065 | 0.9990610328638497 | 1 | 8 | 0 | 8 |
| institutional_flow | TW2368 | 1065 | 1066 | 1058 | 0.9924882629107982 | 8 | 8 | 0 | 8 |
| institutional_flow | TW2379 | 1065 | 1073 | 1065 | 0.9990610328638497 | 1 | 8 | 0 | 8 |
| institutional_flow | TW2454 | 1065 | 1073 | 1065 | 0.9990610328638497 | 1 | 8 | 0 | 8 |
| institutional_flow | TW2603 | 1065 | 1066 | 1058 | 0.9924882629107982 | 8 | 8 | 0 | 8 |
| institutional_flow | TW2881 | 1065 | 1073 | 1065 | 0.9990610328638497 | 1 | 8 | 0 | 8 |
| institutional_flow | TW2882 | 1065 | 1073 | 1065 | 0.9990610328638497 | 1 | 8 | 0 | 8 |
| institutional_flow | TW2891 | 1065 | 1073 | 1065 | 0.9990610328638497 | 1 | 8 | 0 | 8 |
| institutional_flow | TW3008 | 1065 | 1073 | 1065 | 0.9990610328638497 | 1 | 8 | 0 | 8 |
| institutional_flow | TW3017 | 1065 | 1073 | 1065 | 0.9990610328638497 | 1 | 8 | 0 | 8 |
| institutional_flow | TW3034 | 1065 | 1073 | 1065 | 0.9990610328638497 | 1 | 8 | 0 | 8 |
| institutional_flow | TW3037 | 1065 | 1072 | 1064 | 0.9981220657276996 | 2 | 8 | 0 | 8 |
| institutional_flow | TW3443 | 1065 | 1073 | 1065 | 0.9990610328638497 | 1 | 8 | 0 | 8 |
| institutional_flow | TW3529 | 1065 | 1073 | 1065 | 0.9990610328638497 | 1 | 8 | 0 | 8 |
| institutional_flow | TW3661 | 1065 | 1073 | 1065 | 0.9990610328638497 | 1 | 8 | 0 | 8 |
| institutional_flow | TW3711 | 1065 | 1073 | 1065 | 0.9990610328638497 | 1 | 8 | 0 | 8 |
| institutional_flow | TW5274 | 1065 | 1073 | 1065 | 0.9990610328638497 | 1 | 8 | 0 | 8 |
| institutional_flow | TW6669 | 1065 | 1073 | 1065 | 0.9990610328638497 | 1 | 8 | 0 | 8 |
| institutional_flow | TW8299 | 1065 | 1073 | 1065 | 0.9990610328638497 | 1 | 8 | 0 | 8 |
| institutional_flow | TW2382 | 1065 | 1073 | 1065 | 0.9990610328638497 | 1 | 8 | 0 | 8 |
| institutional_flow | TW5269 | 1065 | 1072 | 1064 | 0.9981220657276996 | 2 | 8 | 0 | 8 |
| institutional_flow | TW2376 | 1065 | 1073 | 1065 | 0.9990610328638497 | 1 | 8 | 0 | 8 |
| institutional_flow | TW2609 | 1065 | 1073 | 1065 | 0.9990610328638497 | 1 | 8 | 0 | 8 |
| institutional_flow | TW6488 | 1065 | 1072 | 1064 | 0.9981220657276996 | 2 | 8 | 0 | 8 |

## 12. available_at 规则与 PIT Validation

- 规则：`available_at = next_trading_day(trade_date)`。
- T+1 是 conservative visibility proxy，不是官方发布时间声明。
- 不使用 `trade_date`，避免盘后/日后可见统计在同日 asof 中产生未来函数。
- 不使用 `fetched_at`，因为它是本次抓取时间，不代表历史当时可见时间。
- 本次本地交易日历加载至本地价格最大覆盖日；对仍无法生成下一交易日的 tail rows，保留 raw response 证据，但从 normalized PIT archive 中排除，并在 manifest 记录 `excluded_missing_available_at_rows`。

| category | symbol | trade_date | available_at | asof_example | visible_at_asof | validation_result |
|---|---|---|---|---|---|---|
| institutional_flow | TW2303 | 2022-01-03 | 2022-01-04 | 2022-01-03 | False | pass |
| institutional_flow | TW2303 | 2022-01-03 | 2022-01-04 | 2022-01-04 | True | pass |
| institutional_flow | TW2303 | 2022-01-04 | 2022-01-05 | 2022-01-04 | False | pass |
| institutional_flow | TW2303 | 2022-01-04 | 2022-01-05 | 2022-01-05 | True | pass |
| institutional_flow | TW2303 | 2022-01-05 | 2022-01-06 | 2022-01-05 | False | pass |
| institutional_flow | TW2303 | 2022-01-05 | 2022-01-06 | 2022-01-06 | True | pass |
| institutional_flow | TW2303 | 2022-01-06 | 2022-01-07 | 2022-01-06 | False | pass |
| institutional_flow | TW2303 | 2022-01-06 | 2022-01-07 | 2022-01-07 | True | pass |
| institutional_flow | TW2303 | 2022-01-07 | 2022-01-10 | 2022-01-07 | False | pass |
| institutional_flow | TW2303 | 2022-01-07 | 2022-01-10 | 2022-01-10 | True | pass |
| institutional_flow | TW2303 | 2022-01-10 | 2022-01-11 | 2022-01-10 | False | pass |
| institutional_flow | TW2303 | 2022-01-10 | 2022-01-11 | 2022-01-11 | True | pass |
| institutional_flow | TW2303 | 2022-01-11 | 2022-01-12 | 2022-01-11 | False | pass |
| institutional_flow | TW2303 | 2022-01-11 | 2022-01-12 | 2022-01-12 | True | pass |
| institutional_flow | TW2303 | 2022-01-12 | 2022-01-13 | 2022-01-12 | False | pass |
| institutional_flow | TW2303 | 2022-01-12 | 2022-01-13 | 2022-01-13 | True | pass |
| institutional_flow | TW2303 | 2022-01-13 | 2022-01-14 | 2022-01-13 | False | pass |
| institutional_flow | TW2303 | 2022-01-13 | 2022-01-14 | 2022-01-14 | True | pass |
| institutional_flow | TW2303 | 2022-01-14 | 2022-01-17 | 2022-01-14 | False | pass |
| institutional_flow | TW2303 | 2022-01-14 | 2022-01-17 | 2022-01-17 | True | pass |

## 13. 可进入后续 Phase 1B 审查字段

| category | field | status |
|---|---|---|
| institutional_flow | foreign_net_buy / investment_trust_net_buy / dealer_net_buy / institutional_total_net_buy | review_required |
| margin_short | margin_balance / margin_balance_change / short_balance / short_balance_change | review_required |
| monthly_revenue | all monthly revenue fields | deferred_not_authorized |

## 14. Deferred / Fail 字段与原因

- 月营收：`deferred_not_authorized`，Phase 0E 未授权。
- 若单一 symbol 请求失败，已保留在 download status，等待审查者判断是否重试。

## 15. Phase 0E Gate

- 是否满足 Phase 0E Gate：`True`。
- Gate 口径：normalized archive 仅保留 `available_at` 非空的 PIT-valid rows；两类数据各排除 `1529` 行本地日历无法生成下一交易日的 tail rows，raw response JSONL 仍保留下载证据。
- 即使 Gate 为 true，也不能自动进入 Phase 1B，必须等待审查者审查。

## 16. 安全边界

- 月营收：未触碰。
- 全市场补齐：未执行。
- materialize derived features：未执行。
- Qlib bin/provider 写入：未触碰。
- provider refresh/publish：未触碰。
- accepted latest switching：未触碰。
- Phase 1 样本/单因子检验：未执行。
- 模型训练/规则 baseline/Phase 2：未执行。
- 前端/API：未触碰。
- broker/orders/quick-trade/target position/target weight：未触碰。
- 真实交易建议语义：未生成。

## 17. 需要审查者或用户确认的问题

- 是否接受本次 Top150 historical universe 的定义：按 `tw_liquid_dyn` 在窗口内 active days 排序取前 150。
- 是否接受继续使用 T+1 conservative visibility proxy 进入后续 Phase 1B 审查。
- 若存在失败 symbol，是否需要重试或降级时间范围。
- 月营收仍需另行授权。
