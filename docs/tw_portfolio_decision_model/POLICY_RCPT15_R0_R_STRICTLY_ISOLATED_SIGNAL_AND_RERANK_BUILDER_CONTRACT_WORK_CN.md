---
created_at: 2026-06-25
status: work
phase: RCPT15_R0_R_STRICTLY_ISOLATED_SIGNAL_AND_RERANK_BUILDER_CONTRACT
parent_mainline: docs/tw_portfolio_decision_model/POLICY_RCPT15_ISOLATED_SHADOW_BACKFILL_MAINLINE_CN.md
parent_review: docs/tw_portfolio_decision_model/POLICY_RCPT15_R0_ISOLATED_SHADOW_BACKFILL_FEASIBILITY_REVIEW_CN.md
production_allowed: false
provider_publish_allowed: false
accepted_latest_switch_allowed: false
external_data_pull_allowed: false
order_or_target_output_allowed: false
---

# RCPT15_R0_R Strictly Isolated Signal And Rerank Builder Contract 工作文档

## 1. 背景

RCPT15_R0 已确认 `2026-06-18` 至 `2026-06-25` 缺少本地 `option_c_daily_signal/top50_signals.csv`，因此不能直接进入 isolated shadow backfill R1。

本阶段只做更窄的 repair/contract：判断是否可以在完全隔离路径中，从本地已有 normalized/full-market/model/feature artifacts 构造 shadow-only signal 与 rerank builder。不得实际补数据、不得运行 legacy refresh、不得写 latest pointer。

## 2. 本阶段目标

1. 盘点 `2026-06-18..2026-06-25` 目标日期所需的本地 artifact 覆盖。
2. 判断是否存在可复用的本地 option_c signal/provider dry-run/prediction/top50。
3. 判断本地 normalized price 是否覆盖目标日期。
4. 判断 O2 orthogonal feature 与 O4 LTR model/whitelist 是否足够支撑 LTR rerank。
5. 审计现有生成脚本是否会写 `latest` 指针。
6. 冻结一个严格隔离 builder 合同，明确下一步是否允许进入 R1 重新定义。

## 3. 非目标

本阶段不允许：

- 下载外部数据或调用 Yahoo/Scrapling/FinMind API。
- 运行 `scripts/run_daily_tw_stock_auto_update.py`。
- 打开 `TW_DAILY_AUTO_ENABLE_LEGACY_PROVIDER_PUBLISH`。
- 切换或写入 qlib accepted latest。
- 写入 `daily_ltr_rerank_latest.json`。
- 写入 `qlib_pipeline/data_tw/experiments/option_c_daily_signal/latest_signal.json`。
- 发布 provider accepted latest。
- 修改 production/default/latest/provider/frontend/Agent/monitor/order。
- 输出 `OrderIntent`、`target_weight`、`target_position`、`quantity_instruction`、broker/quick-trade/real order。

## 4. 执行者任务

执行者必须新增或运行一个只读审计脚本：

```text
scripts/build_tw_policy_rcpt15_r0_r_strictly_isolated_builder_contract.py
```

输出目录：

```text
data_tw/experiments/risk_control_policy_2022/rcpt15_r0_r_strictly_isolated_signal_and_rerank_builder_contract/
```

必须输出：

```text
manifest.json
local_artifact_inventory.csv
target_date_local_data_coverage.csv
strict_builder_contract.csv
no_latest_pointer_write_contract.csv
dependency_gap_audit.csv
r1_redefinition_decision.csv
forbidden_scope_audit.csv
validator_report.json
diagnostic_findings.md
```

执行报告：

```text
docs/tw_portfolio_decision_model/POLICY_RCPT15_R0_R_STRICTLY_ISOLATED_SIGNAL_AND_RERANK_BUILDER_CONTRACT_EXECUTION_REPORT_CN.md
```

## 5. 判定规则

允许结论只能是以下之一：

```text
PASS_READY_FOR_R1_STRICT_LOCAL_BUILDER_IMPLEMENTATION
STOP_REQUIRES_NEW_ISOLATED_QLIB_INFERENCE_BUILDER_CONTRACT
STOP_REQUIRES_EXPLICIT_LEGACY_REFRESH_OR_ACCEPTED_LATEST_AUTHORIZATION
FAIL_NEEDS_REPAIR_CONTRACT_INCOMPLETE
STOP_SCOPE_OR_SAFETY_VIOLATION
```

判定含义：

- 若目标日期已有本地 option_c signal/top50、O2 feature 与 O4 model/whitelist 均可用，且可证明 builder 不写 latest，则 PASS。
- 若缺少 option_c signal/top50，但 normalized price 与模型文件足够，且下一步可以单独设计一个严格隔离 qlib inference builder，则 STOP 到新的 isolated qlib inference builder 合同，不得直接 backfill。
- 若缺少本地价格/模型/必要特征，必须授权外部刷新或 accepted latest/provider 路径，则 STOP 到 coordinator/user 授权。
- 若输出证据不完整或字段缺失，则 FAIL repair。

## 6. 审查者重点

审查者必须确认：

1. 审计脚本没有导入或调用网络/刷新/发布路径。
2. 没有写任何 latest pointer。
3. 没有修改 production/default/latest/provider/frontend/Agent/monitor/order。
4. artifacts 足以支持 verdict。
5. 如果建议进入下一步，下一步的边界必须仍是 research/shadow-only。

## 7. 给执行者的命令

```text
请执行 RCPT15_R0_R_STRICTLY_ISOLATED_SIGNAL_AND_RERANK_BUILDER_CONTRACT。只做合同和可行性审计，不拉数据、不运行 daily auto update、不打开 legacy provider gate、不切 accepted latest、不发布 provider、不写任何 latest pointer、不输出 order/target/broker。请生成规定 artifacts 与执行报告，并给出是否允许进入下一步的明确 verdict。
```

## 8. 给审查者的命令

```text
请审查 RCPT15_R0_R 执行报告与 artifacts。重点验证只读/隔离边界、no-latest-pointer 合同、目标日期本地数据覆盖、依赖缺口和 R1 重新定义建议。若证据不足则 FAIL；若需要新 isolated qlib inference builder 合同则 STOP，不得直接批准 backfill。
```
