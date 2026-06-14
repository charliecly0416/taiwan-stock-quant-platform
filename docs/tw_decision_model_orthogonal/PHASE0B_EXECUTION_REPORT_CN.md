# Phase 0B 只读方案设计执行报告

## 1. 执行范围

- 执行日期：`2026-06-10T16:59:31+00:00`
- 范围：只读盘点现有脚本、参数、输出路径和风险语义；设计 PIT 行级 schema；编写未来补齐方案草案。
- 未执行：联网、FinMind 下载、materialize、provider refresh/publish、accepted latest switching、Phase 1 样本、单因子检验、模型训练、前端/API、broker/orders/quick-trade/target position。

## 2. 修改文件

- 新增 `scripts/audit_tw_decision_orthogonal_phase0b.py`。

## 3. 生成文件

- `data_tw/experiments/decision_orthogonal/phase0b_script_inventory.csv`
- `data_tw/experiments/decision_orthogonal/phase0b_pit_schema_proposal.md`
- `docs/tw_decision_model_orthogonal/PHASE0B_DATA_BACKFILL_PLAN_CN.md`
- `docs/tw_decision_model_orthogonal/PHASE0B_EXECUTION_REPORT_CN.md`

## 4. 脚本盘点摘要

- 指定脚本数：`9`
- 存在脚本数：`9`
- 需要联网脚本数：`4`
- 会写数据脚本数：`9`
- Phase0B 可运行脚本数：`0`

| script_path | exists | category | purpose | requires_network | writes_data | touches_provider_refresh_publish | safe_to_run_in_phase0b | reason |
|---|---|---|---|---|---|---|---|---|
| qlib_pipeline/examples/tw/run_tw_finmind_institutional_full_download.py | True | institutional_flow | full historical FinMind download and source diagnostics | True | True | True | False | requires network/FinMind request; writes local outputs or feature bins; touches provider/materialized Qlib feature path or publish semantics; Phase 0B work doc says required scripts are inventory targets only; do not run them |
| qlib_pipeline/examples/tw/run_tw_finmind_institutional_poc.py | True | institutional_flow | narrow FinMind POC download and source diagnostics | True | True | True | False | requires network/FinMind request; writes local outputs or feature bins; touches provider/materialized Qlib feature path or publish semantics; Phase 0B work doc says required scripts are inventory targets only; do not run them |
| qlib_pipeline/examples/tw/materialize_tw_institutional_factors.py | True | institutional_flow | materialize raw source rows into derived factor CSV diagnostics | False | True | True | False | writes local outputs or feature bins; touches provider/materialized Qlib feature path or publish semantics; Phase 0B work doc says required scripts are inventory targets only; do not run them |
| qlib_pipeline/examples/tw/screen_tw_institutional_factors.py | True | institutional_flow | write Qlib feature bins and run single-factor screening | False | True | True | False | writes local outputs or feature bins; touches provider/materialized Qlib feature path or publish semantics; Phase 0B work doc says required scripts are inventory targets only; do not run them |
| qlib_pipeline/examples/tw/run_tw_finmind_margin_full_download.py | True | margin_short | full historical FinMind download and source diagnostics | True | True | True | False | requires network/FinMind request; writes local outputs or feature bins; touches provider/materialized Qlib feature path or publish semantics; Phase 0B work doc says required scripts are inventory targets only; do not run them |
| qlib_pipeline/examples/tw/run_tw_finmind_margin_poc.py | True | margin_short | narrow FinMind POC download and source diagnostics | True | True | True | False | requires network/FinMind request; writes local outputs or feature bins; touches provider/materialized Qlib feature path or publish semantics; Phase 0B work doc says required scripts are inventory targets only; do not run them |
| qlib_pipeline/examples/tw/materialize_tw_margin_batch_a.py | True | margin_short | materialize raw source rows into derived factor CSV diagnostics | False | True | True | False | writes local outputs or feature bins; touches provider/materialized Qlib feature path or publish semantics; Phase 0B work doc says required scripts are inventory targets only; do not run them |
| qlib_pipeline/examples/tw/screen_tw_margin_batch_a.py | True | margin_short | write Qlib feature bins and run single-factor screening | False | True | True | False | writes local outputs or feature bins; touches provider/materialized Qlib feature path or publish semantics; Phase 0B work doc says required scripts are inventory targets only; do not run them |
| qlib_pipeline/examples/tw/run_tw_margin_util_ablation.py | True | margin_short | run fixed factor ablation/model experiment | False | True | True | False | writes local outputs or feature bins; touches provider/materialized Qlib feature path or publish semantics; Phase 0B work doc says required scripts are inventory targets only; do not run them |

## 5. PIT Schema 设计摘要

- 法人筹码：必须有 `symbol`, `trade_date`, `available_at`, 三大法人买卖超字段、`data_source`, `raw_snapshot_id`。
- 融资融券：必须有 `symbol`, `trade_date`, `available_at`, 融资/融券余额与变化、`data_source`, `raw_snapshot_id`。
- 月营收：必须有 `symbol`, `source_period`, `announcement_date`, `available_at`, revenue/YoY/MoM、`days_since_last_report`, `data_source`, `raw_snapshot_id`。
- 日频数据默认使用保守 T+1；月营收只能从 announcement_date/available_at 向后对齐，不能按 source_period 直接 join。

## 6. 未来补齐需要用户授权的动作清单

- 运行任何 FinMind POC/full download。
- 新增或接入月营收数据源。
- 写 raw archive、status、coverage、diagnostics。
- materialize 特征或写 Qlib bin/provider。
- 构建 Phase 1 样本、单因子检验、训练模型、前端/API。

## 7. Phase0B 禁止运行的脚本

| script_path | reason |
|---|---|
| qlib_pipeline/examples/tw/run_tw_finmind_institutional_full_download.py | requires network/FinMind request; writes local outputs or feature bins; touches provider/materialized Qlib feature path or publish semantics; Phase 0B work doc says required scripts are inventory targets only; do not run them |
| qlib_pipeline/examples/tw/run_tw_finmind_institutional_poc.py | requires network/FinMind request; writes local outputs or feature bins; touches provider/materialized Qlib feature path or publish semantics; Phase 0B work doc says required scripts are inventory targets only; do not run them |
| qlib_pipeline/examples/tw/materialize_tw_institutional_factors.py | writes local outputs or feature bins; touches provider/materialized Qlib feature path or publish semantics; Phase 0B work doc says required scripts are inventory targets only; do not run them |
| qlib_pipeline/examples/tw/screen_tw_institutional_factors.py | writes local outputs or feature bins; touches provider/materialized Qlib feature path or publish semantics; Phase 0B work doc says required scripts are inventory targets only; do not run them |
| qlib_pipeline/examples/tw/run_tw_finmind_margin_full_download.py | requires network/FinMind request; writes local outputs or feature bins; touches provider/materialized Qlib feature path or publish semantics; Phase 0B work doc says required scripts are inventory targets only; do not run them |
| qlib_pipeline/examples/tw/run_tw_finmind_margin_poc.py | requires network/FinMind request; writes local outputs or feature bins; touches provider/materialized Qlib feature path or publish semantics; Phase 0B work doc says required scripts are inventory targets only; do not run them |
| qlib_pipeline/examples/tw/materialize_tw_margin_batch_a.py | writes local outputs or feature bins; touches provider/materialized Qlib feature path or publish semantics; Phase 0B work doc says required scripts are inventory targets only; do not run them |
| qlib_pipeline/examples/tw/screen_tw_margin_batch_a.py | writes local outputs or feature bins; touches provider/materialized Qlib feature path or publish semantics; Phase 0B work doc says required scripts are inventory targets only; do not run them |
| qlib_pipeline/examples/tw/run_tw_margin_util_ablation.py | writes local outputs or feature bins; touches provider/materialized Qlib feature path or publish semantics; Phase 0B work doc says required scripts are inventory targets only; do not run them |

## 8. 安全边界

- broker/orders/quick-trade/target position/target weight：未触碰。
- provider refresh/publish：未触碰。
- accepted latest switching：未触碰。
- monitor config/alerts：未触碰。
- 真实交易建议语义：未生成。

## 9. 是否建议进入真实数据补齐阶段

- Phase0B gate 结论：`request_user_approval_for_data_backfill=true`。
- 说明：现有脚本显示法人/融资融券补齐技术路径存在，但都需要联网和写本地归档；月营收脚本未发现。执行者不能自行补齐，需等待审查者和用户下一步授权。
- Phase 1：不允许进入。

## 10. 需要用户确认的问题

- 是否允许联网调用 FinMind 或其他数据源。
- 是否允许写入新的正交 raw archive 与 PIT snapshot。
- 是否接受日频法人/融资融券使用保守 T+1 `available_at` 规则。
- 月营收若仓库没有现成脚本，是否允许新增脚本或改用其他具备公告日的数据源。

## 11. 月营收脚本发现

_no rows_
