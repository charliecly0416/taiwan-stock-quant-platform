# 正交数据 Decision Model Phase 0C 受限 POC Raw Archive 工作文档

授权日期：2026-06-10

用户确认：

- 接受审查者建议，允许执行 Phase 0C。

前置审查文件：

- `docs/tw_decision_model_orthogonal/PHASE0B_REVIEW_AND_PHASE0C_USER_CONFIRMATION_CN.md`

## 1. 当前授权范围

允许执行者进入 Phase 0C，但只允许做受限 POC raw archive。

Phase 0C 的目标是建立最小可审计 raw archive，用来验证法人筹码与融资融券是否能形成 row-level point-in-time 数据。

Phase 0C 不是 Phase 1，不允许做样本、因子检验、模型训练、规则 baseline、回放或前端。

## 2. 数据范围

允许：

- 法人筹码 POC。
- 融资融券 POC。

暂缓：

- 月营收。

月营收暂缓原因：

- Phase 0B 未发现现成月营收脚本。
- 月营收必须有 `source_period`、`announcement_date`、`available_at`。
- 新增月营收脚本或改用其他数据源需要用户另行授权。

## 3. 时间与股票范围

推荐范围：

- 时间：优先 `2025-01-01` 至 `2026-06-10`。
- 若 API 限额、执行时间或稳定性不足，可缩小为最近 3 到 6 个月。
- 股票：仅限当前 qlib / tw_liquid_dyn 研究 universe 的小样本。
- 推荐股票数量：50 到 150 档。

禁止：

- 禁止全市场补齐。
- 禁止无限期历史回填。
- 禁止扩大到计划外数据源。

## 4. 允许动作

Phase 0C 允许以下动作：

- 联网调用 FinMind，仅限法人筹码与融资融券 POC。
- 写入 Phase 0C 专用 raw archive。
- 写下载状态、覆盖率、失败原因、PIT snapshot manifest。
- 生成 PIT validation samples。
- 写中文执行报告。

所有输出必须在 Phase 0C 专用目录下，不得写入生产 provider 或 accepted latest。

## 5. 禁止动作

Phase 0C 禁止：

- 禁止 materialize derived features。
- 禁止写 Qlib bin。
- 禁止 provider refresh/publish。
- 禁止 accepted latest switching。
- 禁止 Phase 1 样本构建。
- 禁止单因子/分组检验。
- 禁止模型训练。
- 禁止规则型风险过滤 baseline。
- 禁止组合回放。
- 禁止前端/API。
- 禁止 broker、orders、quick-trade、target position/target weight。
- 禁止月营收新增脚本或新增数据源。
- 禁止全市场补齐。

## 6. 建议新增文件

建议新增：

- `scripts/build_tw_decision_orthogonal_phase0c_raw_archive.py`
- `data_tw/experiments/decision_orthogonal/phase0c_raw_archive/`
- `data_tw/experiments/decision_orthogonal/phase0c_download_status.csv`
- `data_tw/experiments/decision_orthogonal/phase0c_pit_snapshot_manifest.csv`
- `data_tw/experiments/decision_orthogonal/phase0c_coverage_report.csv`
- `data_tw/experiments/decision_orthogonal/phase0c_pit_validation_samples.csv`
- `docs/tw_decision_model_orthogonal/PHASE0C_EXECUTION_REPORT_CN.md`

如执行者复用已有 FinMind POC/full download 脚本，必须通过包装脚本限制范围，并在报告中说明实际调用命令、参数、输出路径和网络行为。

## 7. Raw Archive 必备字段

法人筹码 raw archive 每行至少包含：

- `symbol`
- `stock_id`
- `trade_date`
- `available_at`
- `foreign_net_buy`
- `investment_trust_net_buy`
- `dealer_net_buy`
- `institutional_total_net_buy`
- `data_source`
- `raw_snapshot_id`
- `fetched_at`
- `quality_flags`

融资融券 raw archive 每行至少包含：

- `symbol`
- `stock_id`
- `trade_date`
- `available_at`
- `margin_balance`
- `margin_balance_change`
- `short_balance`
- `short_balance_change`
- `data_source`
- `raw_snapshot_id`
- `fetched_at`
- `quality_flags`

若某些原始字段不可得，必须在 `quality_flags` 与执行报告中说明，不得静默补值。

## 8. `available_at` 规则

默认使用保守 T+1：

- `available_at = next_trading_day(trade_date)`

但执行者必须在报告中说明：

- 为什么不能直接使用 `trade_date`。
- FinMind/TWSE/TPEx 数据的可见时间证据是什么。
- 若使用实际抓取时间 `fetched_at`，为什么不替代官方/保守可见时间。
- 若无法证明 T+1 规则，该字段必须 deferred，不得进入后续 Phase 1。

所有滚动或派生字段未来都必须使用 `available_at <= asof` 的记录。

## 9. `phase0c_download_status.csv` 要求

每次请求或每个 symbol/date batch 至少记录：

- `category`
- `symbol`
- `stock_id`
- `start_date`
- `end_date`
- `request_started_at`
- `request_finished_at`
- `status`
- `row_count`
- `error_type`
- `error_message`
- `source_endpoint`
- `output_path`

失败必须保留，不得只报告成功样本。

## 10. `phase0c_pit_snapshot_manifest.csv` 要求

每个 raw snapshot 至少记录：

- `raw_snapshot_id`
- `category`
- `data_source`
- `fetched_at`
- `source_endpoint`
- `symbol_count`
- `row_count`
- `first_trade_date`
- `last_trade_date`
- `available_at_rule`
- `archive_path`
- `checksum_or_size`

## 11. `phase0c_coverage_report.csv` 要求

至少包含：

- `category`
- `symbol`
- `expected_trading_days`
- `observed_rows`
- `coverage_rate`
- `first_trade_date`
- `last_trade_date`
- `missing_dates_count`
- `duplicate_rows_count`
- `quality_issue_count`

## 12. `phase0c_pit_validation_samples.csv` 要求

抽样验证 PIT 对齐，至少包含：

- `category`
- `symbol`
- `trade_date`
- `available_at`
- `asof_example`
- `visible_at_asof`
- `raw_snapshot_id`
- `validation_result`
- `validation_note`

必须包含正例和边界样例，例如：

- `asof < available_at` 时不可见。
- `asof >= available_at` 时可见。

## 13. 执行报告要求

`PHASE0C_EXECUTION_REPORT_CN.md` 必须包含：

1. 执行范围。
2. 实际联网/下载命令。
3. 修改文件。
4. 生成文件。
5. 数据源与 endpoint。
6. 时间范围与股票范围。
7. raw archive 行数、symbol 数、日期范围。
8. 下载成功/失败统计。
9. 覆盖率与缺失率。
10. `available_at` 规则与证据。
11. PIT validation samples 摘要。
12. 可进入后续审查的字段。
13. deferred/fail 字段与原因。
14. 是否满足 Phase 0C Gate。
15. 安全边界说明。
16. 需要审查者或用户确认的问题。

## 14. Phase 0C Gate

Phase 0C 通过的最低条件：

- 至少一类数据有非零 raw archive。
- 每行有 `symbol`、`trade_date`、`available_at`、`data_source`、`raw_snapshot_id`。
- 有下载状态、覆盖率、失败原因。
- 有 PIT validation samples 证明 `available_at <= asof` 规则可执行。
- 没有 materialize、screen、训练、Phase 1 样本或前端/API 越界。

Phase 0C 失败条件：

- 两类数据都无法下载或都是 0 行。
- 无法生成 `available_at`。
- 只能拿到最终修正值且无法保留 raw snapshot。
- 执行者运行了 materialize/screen/ablation。
- 执行者进入 Phase 1 样本或单因子检验。
- 执行者触发 provider refresh/publish 或 accepted latest switching。

## 15. Phase 0C 后续限制

即使 Phase 0C 成功，也不能自动进入 Phase 1。

执行者完成 Phase 0C 后必须等待审查者审查：

- PIT 是否可信。
- 覆盖率是否足够。
- 是否存在未来函数。
- 是否只适合继续补齐，还是可以构建 Phase 1 样本。

## 16. 审查者裁决

- 是否允许执行 Phase 0C：是。
- 是否允许联网：是，仅限法人筹码与融资融券 POC。
- 是否允许写 raw archive：是，仅限 Phase 0C 专用目录。
- 是否允许 materialize：否。
- 是否允许 Qlib bin/provider 写入：否。
- 是否允许 accepted latest switching：否。
- 是否允许 Phase 1：否。
- 是否允许训练模型：否。
- 当前给执行者的任务：受限 POC raw archive + PIT validation。
