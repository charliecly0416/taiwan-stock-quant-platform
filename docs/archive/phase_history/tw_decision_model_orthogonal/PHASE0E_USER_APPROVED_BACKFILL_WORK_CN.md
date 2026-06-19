# 正交数据 Decision Model Phase 0E 扩展 Raw Archive Backfill 工作文档

授权日期：2026-06-10

用户确认：

- 允许进入 Phase 0E 扩展 raw archive backfill。
- 拉取数据时使用 Scrapling 和 API token。

前置审查文件：

- `docs/tw_decision_model_orthogonal/PHASE1A_REVIEW_AND_BACKFILL_CONFIRMATION_CN.md`

## 1. 当前授权范围

允许执行者对法人筹码与融资融券做扩展 raw archive backfill，为后续完整 Phase 1 验证准备更长历史和更多 symbols 的 PIT 数据。

Phase 0E 仍是数据补齐与 PIT 审计阶段，不是完整 Phase 1，不允许做单因子检验、模型训练、规则 baseline、Phase 2、前端/API 或交易相关动作。

## 2. 数据范围

允许：

- 法人筹码。
- 融资融券。

暂缓：

- 月营收。

月营收仍需另行授权，因为当前没有现成脚本，且必须具备 `source_period`、`announcement_date`、`available_at`。

## 3. 时间与股票范围

推荐范围：

- 首选：`2022-01-01` 至 `2026-06-10`。
- 若 API 限额、token 权限或执行时间不足，最低范围：`2024-01-01` 至 `2026-06-10`。

股票范围：

- qlib / tw_liquid_dyn Top150 historical universe。
- 不允许全市场。

若实际下载范围小于推荐范围，执行者必须在报告中说明原因、失败类别和可恢复方案。

## 4. 拉取方式要求

允许使用：

- Scrapling。
- FinMind API token 或等价 API token。

Token 要求：

- token 可以由用户在聊天框中直接提供给执行者。
- 执行者可以在当前运行时将用户提供的 token 临时注入为 `FINMIND_TOKEN` 或 `FINMIND_API_TOKEN`。
- 禁止把 token 持久化写入仓库文件、脚本、CSV、JSON、Markdown、日志或错误信息。
- 禁止在执行报告、download status、source manifest、命令记录中显示 token 原文。
- 实际联网/下载命令不得包含 token 原文；如需记录命令，只记录脱敏命令和 `token_used=true/false`。
- 若 token 缺失或无效，必须停止并报告，不能改用未授权数据源绕过。
- 报告中只能写 `token_used=true/false`，不得写 token 内容。

Scrapling 要求：

- 只允许用于授权数据源访问、endpoint probing、source availability verification 或必要的网页/接口拉取。
- 不得绕过登录、付费墙、验证码或访问控制。
- 不得触发 broker、交易、monitor、provider publish/refresh、accepted latest switching。
- 必须记录 `source_url`、dataset、status、row_count、error_type、error_message。

## 5. 允许动作

Phase 0E 允许：

- 联网拉取法人筹码和融资融券数据。
- 使用 API token。
- 使用 Scrapling。
- 写 Phase 0E 专用 raw archive。
- 写 download status、PIT snapshot manifest、coverage report、PIT validation samples、quality flags。
- 生成中文执行报告。

所有输出必须位于：

- `data_tw/experiments/decision_orthogonal/phase0e_*`
- `docs/tw_decision_model_orthogonal/PHASE0E_EXECUTION_REPORT_CN.md`

## 6. 禁止动作

Phase 0E 禁止：

- 禁止月营收。
- 禁止全市场补齐。
- 禁止 materialize derived features。
- 禁止 Qlib bin/provider 写入。
- 禁止 provider refresh/publish。
- 禁止 accepted latest switching。
- 禁止 Phase 1 样本构建。
- 禁止单因子检验。
- 禁止模型训练。
- 禁止规则型风险过滤 baseline。
- 禁止 Phase 2。
- 禁止前端/API。
- 禁止 broker、orders、quick-trade、target position/target weight。
- 禁止输出买入/卖出建议、收益承诺、上涨概率承诺。

## 7. 建议新增文件

建议新增：

- `scripts/build_tw_decision_orthogonal_phase0e_raw_archive.py`
- `data_tw/experiments/decision_orthogonal/phase0e_raw_archive/`
- `data_tw/experiments/decision_orthogonal/phase0e_download_status.csv`
- `data_tw/experiments/decision_orthogonal/phase0e_pit_snapshot_manifest.csv`
- `data_tw/experiments/decision_orthogonal/phase0e_coverage_report.csv`
- `data_tw/experiments/decision_orthogonal/phase0e_pit_validation_samples.csv`
- `data_tw/experiments/decision_orthogonal/phase0e_quality_flags_summary.csv`
- `docs/tw_decision_model_orthogonal/PHASE0E_EXECUTION_REPORT_CN.md`

如复用 Phase 0C 脚本，必须新增 Phase 0E 包装脚本限制输出路径、universe、日期范围和 token redaction。

## 8. Raw Archive 必备字段

法人筹码每行至少包含：

- `symbol`
- `stock_id`
- `trade_date`
- `available_at`
- `foreign_net_buy`
- `investment_trust_net_buy`
- `dealer_net_buy`
- `institutional_total_net_buy`
- `data_source`
- `source_url_or_endpoint`
- `raw_snapshot_id`
- `fetched_at`
- `quality_flags`

融资融券每行至少包含：

- `symbol`
- `stock_id`
- `trade_date`
- `available_at`
- `margin_balance`
- `margin_balance_change`
- `short_balance`
- `short_balance_change`
- `data_source`
- `source_url_or_endpoint`
- `raw_snapshot_id`
- `fetched_at`
- `quality_flags`

若某字段缺失，必须显式记录原因。不得静默填 0。

## 9. PIT 与 available_at 规则

默认继续使用保守 T+1：

- `available_at = next_trading_day(trade_date)`

执行者必须说明：

- T+1 是 conservative visibility proxy，不是官方发布时间声明。
- 为什么不能用 `trade_date`。
- 为什么不能用 `fetched_at` 替代历史可见时间。
- 如何使用本地交易日历修复区间尾部 `available_at`。
- 无法生成 `available_at` 的行如何排除或标记。

所有未来 Phase 1 样本只允许使用 `available_at <= asof` 的记录。

## 10. Download Status 要求

`phase0e_download_status.csv` 每个请求或 batch 至少包含：

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
- `source_url`
- `token_used`
- `output_path`

注意：

- `token_used` 只能是 true/false。
- `error_message` 必须脱敏。
- 失败请求必须保留。

## 11. Manifest / Coverage / PIT Validation 要求

`phase0e_pit_snapshot_manifest.csv` 至少包含：

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

`phase0e_coverage_report.csv` 至少包含：

- `category`
- `symbol`
- `expected_trading_days`
- `raw_rows`
- `pit_valid_rows`
- `pit_valid_coverage_rate`
- `missing_dates_count`
- `extra_dates_count`
- `duplicate_rows_count`
- `quality_issue_count`

`phase0e_pit_validation_samples.csv` 至少包含：

- `category`
- `symbol`
- `trade_date`
- `available_at`
- `asof_example`
- `visible_at_asof`
- `raw_snapshot_id`
- `validation_result`
- `validation_note`

必须包含边界样例：

- `asof < available_at` 时不可见。
- `asof >= available_at` 时可见。

## 12. 执行报告要求

`PHASE0E_EXECUTION_REPORT_CN.md` 必须包含：

1. 执行范围。
2. 实际联网/下载命令，不能包含 token。
3. 是否使用 Scrapling。
4. 是否使用 API token，不能显示 token；若 token 由聊天框提供，只能写“用户提供 token，运行时临时注入”。
5. 修改文件。
6. 生成文件。
7. 数据源、endpoint、source_url。
8. 时间范围与股票范围。
9. raw archive 行数、symbol 数、日期范围。
10. 下载成功/失败统计。
11. 覆盖率、缺失率、重复行、quality flags。
12. `available_at` 规则与 PIT validation。
13. 哪些字段可进入后续 Phase 1B 审查。
14. deferred/fail 字段与原因。
15. 是否满足 Phase 0E Gate。
16. 安全边界说明。
17. 需要审查者或用户确认的问题。

## 13. Phase 0E Gate

Phase 0E 通过的最低条件：

- 法人筹码与融资融券至少一类有足够非零 PIT-valid rows。
- 每行有 `symbol`、`trade_date`、`available_at`、`data_source`、`raw_snapshot_id`。
- `available_at` 非空。
- 有 download status、manifest、coverage、quality flags、PIT validation samples。
- token 未泄露。
- 没有 materialize、Qlib bin/provider、accepted latest、Phase 1、Phase 2、模型或前端/API 越界。

Phase 0E 失败条件：

- 两类数据均无法下载或全为 0 行。
- 无法生成 `available_at`。
- token 泄露到任何产物。
- 执行者使用计划外数据源。
- 执行者进入 Phase 1/Phase 2 或训练模型。

## 14. Phase 0E 后续限制

即使 Phase 0E 通过，也不能自动进入 Phase 1B。

执行者完成 Phase 0E 后必须等待审查者审查：

- PIT 是否可信。
- 覆盖率是否足够。
- token 是否脱敏。
- 是否有未来函数风险。
- 是否具备完整 Phase 1B 样本与单因子检验前提。

## 15. 审查者裁决

- 是否允许执行 Phase 0E：是。
- 是否允许联网：是，仅限法人筹码与融资融券。
- 是否允许使用 Scrapling：是，仅限授权数据源访问与 source verification。
- 是否允许使用 API token：是，必须从环境变量读取且不得泄露。
- 是否允许月营收：否。
- 是否允许 materialize/Qlib bin/provider：否。
- 是否允许 accepted latest switching：否。
- 是否允许 Phase 1B：否，需 Phase 0E 审查后再决定。
- 是否允许 Phase 2：否。
- 是否允许模型训练：否。
