# 正交数据 Decision Model Phase 0B 只读方案设计工作文档

授权日期：2026-06-10

用户确认：

- 允许进入 Phase 0B。

前置审查文件：

- `docs/tw_decision_model_orthogonal/PHASE0_REVIEW_AND_USER_CONFIRMATION_CN.md`

## 1. 当前结论

Phase 0 Gate 已失败，当前不得进入 Phase 1。

用户已允许进入 Phase 0B，但本次授权只覆盖只读方案设计，不覆盖真实数据补齐。

Phase 0B 的目标是判断：如果未来要补齐法人筹码、融资融券、月营收数据，现有仓库脚本、字段、输出路径和 PIT schema 应如何设计，哪些步骤需要另行授权。

## 2. Phase 0B 边界

允许：

- 只读盘点现有脚本。
- 只读查看脚本参数、输入输出路径、字段语义。
- 只读查看已有日志、summary、配置文件。
- 设计 PIT 行级归档 schema。
- 设计最小可行补齐方案。
- 标记哪些操作未来需要用户授权。

禁止：

- 禁止联网。
- 禁止真实下载数据。
- 禁止运行 FinMind full download / POC download。
- 禁止 materialize 新特征。
- 禁止写入生产数据。
- 禁止 provider refresh/publish。
- 禁止 accepted latest switching。
- 禁止构建 Phase 1 样本。
- 禁止单因子检验。
- 禁止训练模型。
- 禁止前端/API。
- 禁止 broker、orders、quick-trade、target position/target weight。

## 3. 执行者必须审计的脚本

至少盘点以下脚本，若文件不存在需记录：

- `qlib_pipeline/examples/tw/run_tw_finmind_institutional_full_download.py`
- `qlib_pipeline/examples/tw/run_tw_finmind_institutional_poc.py`
- `qlib_pipeline/examples/tw/materialize_tw_institutional_factors.py`
- `qlib_pipeline/examples/tw/screen_tw_institutional_factors.py`
- `qlib_pipeline/examples/tw/run_tw_finmind_margin_full_download.py`
- `qlib_pipeline/examples/tw/run_tw_finmind_margin_poc.py`
- `qlib_pipeline/examples/tw/materialize_tw_margin_batch_a.py`
- `qlib_pipeline/examples/tw/screen_tw_margin_batch_a.py`
- `qlib_pipeline/examples/tw/run_tw_margin_util_ablation.py`

如发现月营收相关脚本，也必须纳入盘点。

## 4. Phase 0B 产物要求

执行者应新增：

- `data_tw/experiments/decision_orthogonal/phase0b_script_inventory.csv`
- `data_tw/experiments/decision_orthogonal/phase0b_pit_schema_proposal.md`
- `docs/tw_decision_model_orthogonal/PHASE0B_DATA_BACKFILL_PLAN_CN.md`
- `docs/tw_decision_model_orthogonal/PHASE0B_EXECUTION_REPORT_CN.md`

如需新增只读辅助脚本，建议命名：

- `scripts/audit_tw_decision_orthogonal_phase0b.py`

该脚本只能读取文件、解析参数和输出文档，不得执行任何下载/materialize 逻辑。

## 5. `phase0b_script_inventory.csv` 要求

每个脚本至少包含：

- `script_path`
- `exists`
- `category`: `institutional_flow` / `margin_short` / `monthly_revenue` / `unknown`
- `purpose`
- `requires_network`
- `writes_data`
- `possible_output_paths`
- `input_args`
- `uses_finmind`
- `touches_provider_refresh_publish`
- `touches_accepted_latest`
- `safe_to_run_in_phase0b`
- `reason`

Phase 0B 中 `safe_to_run_in_phase0b` 默认应为 `false`，除非脚本明确只读且不会下载或写数据。

## 6. `phase0b_pit_schema_proposal.md` 要求

必须给出三类数据的建议 schema。

法人筹码至少包含：

- `symbol`
- `trade_date`
- `available_at`
- `foreign_net_buy`
- `investment_trust_net_buy`
- `dealer_net_buy`
- `institutional_total_net_buy`
- `data_source`
- `raw_snapshot_id`

融资融券至少包含：

- `symbol`
- `trade_date`
- `available_at`
- `margin_balance`
- `margin_balance_change`
- `short_balance`
- `short_balance_change`
- `data_source`
- `raw_snapshot_id`

月营收至少包含：

- `symbol`
- `source_period`
- `announcement_date`
- `available_at`
- `revenue`
- `revenue_yoy`
- `revenue_mom`
- `days_since_last_report`
- `data_source`
- `raw_snapshot_id`

必须说明：

- `available_at` 如何生成。
- 是否使用 T+1 保守规则。
- 月营收如何从公告日向后对齐交易日。
- 如何避免用 `source_period` 直接 join。
- 如何保留 as-reported snapshot。
- 如何处理事后修正。

## 7. `PHASE0B_DATA_BACKFILL_PLAN_CN.md` 要求

这不是执行计划，而是未来若用户继续授权时的方案草案。

必须包含：

- 数据补齐最小范围建议。
- 建议起止日期。
- 建议 symbol universe。
- 每类数据的 PIT 风险。
- 每类数据的最小字段。
- 哪些步骤需要联网。
- 哪些步骤会写入本地归档。
- 哪些步骤必须再次征得用户确认。
- 若无法获得公告日期/available_at，应如何放弃或 deferred。

不得包含：

- 实际补齐结果。
- 下载日志。
- 新数据行数。
- 模型训练结果。
- 进入 Phase 1 的建议，除非未来真实补齐后再审查。

## 8. `PHASE0B_EXECUTION_REPORT_CN.md` 要求

执行报告必须包含：

1. 执行范围。
2. 修改文件。
3. 生成文件。
4. 脚本盘点摘要。
5. PIT schema 设计摘要。
6. 未来补齐需要用户授权的动作清单。
7. 哪些脚本禁止在 Phase 0B 运行。
8. 是否触碰安全边界。
9. 是否建议进入真实数据补齐阶段。
10. 需要用户确认的问题。

## 9. Phase 0B Gate

Phase 0B 不允许直接进入 Phase 1。

Phase 0B 完成后，只能有三种结论：

- `stop_orthogonal_data_line=true`：现有脚本或数据源不足，或 PIT 风险不可控。
- `request_user_approval_for_data_backfill=true`：方案可行，但需要用户授权联网/下载/归档。
- `phase0b_incomplete=true`：脚本盘点或 schema 证据不足，需要补文档，不得继续。

即使 Phase 0B 认为方案可行，也不能自行补数据。

## 10. 审查者裁决

- 是否允许执行 Phase 0B：是。
- 是否允许联网：否。
- 是否允许下载数据：否。
- 是否允许 materialize 特征：否。
- 是否允许进入 Phase 1：否。
- 是否允许训练模型：否。
- 当前给执行者的任务：只读脚本盘点 + PIT schema/补齐方案设计。
