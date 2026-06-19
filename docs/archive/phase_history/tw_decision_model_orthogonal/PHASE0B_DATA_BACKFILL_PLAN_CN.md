# Phase 0B 正交数据未来补齐方案草案

## 1. 性质声明

本文件不是执行日志，也不是补齐结果。Phase 0B 未联网、未下载、未 materialize、未写生产数据、未进入 Phase 1。

## 2. 最小范围建议

- 起止日期：优先 2022-01-01 至最新已审查 qlib asof；若 API 限额不足，可先做 2025-01-01 至 2026 当前日期的试点。
- symbol universe：优先当前 qlib Option C / tw_liquid_dyn 150 档历史 universe；不得全市场扩展，除非用户另行授权。
- 数据类别：第一优先法人筹码与融资融券，第二优先月营收。月营收若拿不到公告日期，直接 deferred。

## 3. 每类数据的 PIT 风险

- 法人筹码：FinMind/TWSE 盘后发布时间需要确认；若只有 trade_date，无 row-level `available_at`，必须采用保守 T+1 并在报告列明证据。
- 融资融券：可能存在停券、暂停交易、限额字段缺失；必须保留缺失原因，不得盲目 forward-fill。
- 月营收：最大风险是用 source period 直接 join 到当月交易日。必须有 announcement_date/available_at 和 as-reported snapshot。

## 4. 最小字段

- 法人筹码：`symbol`, `stock_id`, `trade_date`, `available_at`, `foreign_net_buy`, `investment_trust_net_buy`, `dealer_net_buy`, `institutional_total_net_buy`, `data_source`, `raw_snapshot_id`。
- 融资融券：`symbol`, `stock_id`, `trade_date`, `available_at`, `margin_balance`, `margin_balance_change`, `short_balance`, `short_balance_change`, `data_source`, `raw_snapshot_id`。
- 月营收：`symbol`, `stock_id`, `source_period`, `announcement_date`, `available_at`, `revenue`, `revenue_yoy`, `revenue_mom`, `days_since_last_report`, `data_source`, `raw_snapshot_id`。

## 5. 需要联网的步骤

- 运行 FinMind POC/full download 脚本会调用外部 API，需要用户另行授权。
- 月营收脚本当前未在 `qlib_pipeline/examples/tw` 中发现；若新增脚本或数据源，需要用户另行授权。

## 6. 会写入本地归档的步骤

- POC/full download 脚本会写 raw CSV、status、coverage、diagnostics 和报告。
- materialize 脚本会写 feature CSV 和诊断文件。
- screening 脚本会写 Qlib feature bin、IC screening CSV 和报告。
- ablation 脚本会运行模型/实验并写 recorder/log/summary，Phase 0B 和真实补齐阶段都不应运行，除非未来进入相应模型阶段并获授权。

## 7. 必须再次征得用户确认的动作

- 任何联网或 FinMind API 请求。
- 任何真实数据下载或本地 raw archive 写入。
- 任何 materialize 特征、Qlib bin 写入或 provider 相关写入。
- 任何 Phase 1 样本构建、单因子检验、模型训练、前端/API 或交易相关动作。

## 8. 如果无法获得 PIT 字段

- 法人/融资融券无法证明盘后可见时间时：deferred，不进入 Phase 1。
- 月营收没有 announcement_date/available_at 时：fail/deferred，不得用 source_period join。
- 只拿到最终修正值且没有 as-reported snapshot 时：deferred。

## 9. 脚本盘点摘要

| script_path | exists | category | purpose | requires_network | writes_data | safe_to_run_in_phase0b |
|---|---|---|---|---|---|---|
| qlib_pipeline/examples/tw/run_tw_finmind_institutional_full_download.py | True | institutional_flow | full historical FinMind download and source diagnostics | True | True | False |
| qlib_pipeline/examples/tw/run_tw_finmind_institutional_poc.py | True | institutional_flow | narrow FinMind POC download and source diagnostics | True | True | False |
| qlib_pipeline/examples/tw/materialize_tw_institutional_factors.py | True | institutional_flow | materialize raw source rows into derived factor CSV diagnostics | False | True | False |
| qlib_pipeline/examples/tw/screen_tw_institutional_factors.py | True | institutional_flow | write Qlib feature bins and run single-factor screening | False | True | False |
| qlib_pipeline/examples/tw/run_tw_finmind_margin_full_download.py | True | margin_short | full historical FinMind download and source diagnostics | True | True | False |
| qlib_pipeline/examples/tw/run_tw_finmind_margin_poc.py | True | margin_short | narrow FinMind POC download and source diagnostics | True | True | False |
| qlib_pipeline/examples/tw/materialize_tw_margin_batch_a.py | True | margin_short | materialize raw source rows into derived factor CSV diagnostics | False | True | False |
| qlib_pipeline/examples/tw/screen_tw_margin_batch_a.py | True | margin_short | write Qlib feature bins and run single-factor screening | False | True | False |
| qlib_pipeline/examples/tw/run_tw_margin_util_ablation.py | True | margin_short | run fixed factor ablation/model experiment | False | True | False |

## 10. 月营收脚本发现

_no rows_
