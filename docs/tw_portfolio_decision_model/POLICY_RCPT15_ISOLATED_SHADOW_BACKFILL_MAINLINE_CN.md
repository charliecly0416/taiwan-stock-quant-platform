---
created_at: 2026-06-25
status: mainline
phase: RCPT15_ISOLATED_SHADOW_BACKFILL
parent_review: docs/tw_portfolio_decision_model/POLICY_RCPT14B_QUARANTINE_ACCEPTANCE_GO_NO_GO_CONTRACT_REVIEW_CN.md
production_allowed: false
provider_publish_default_allowed: false
accepted_latest_switch_allowed: false
order_or_target_output_allowed: false
---

# RCPT15 Isolated Shadow Backfill 主线文档

## 1. 目标

RCPT15 目标是为 RCPT risk-control production-readiness route 补齐更多 readonly shadow days，优先覆盖：

```text
2026-06-18 至 2026-06-25
```

但必须隔离在 research/shadow 路径中，不得把补生成动作误变成 production/default/latest/provider/frontend/Agent/monitor/order 链路改动。

## 2. 当前事实

已确认：

```text
daily_auto_update cron installed = true
latest_signal_after_daily_auto_update = 2026-06-17
daily_ltr_rerank available source days = 2026-06-15, 2026-06-17
default daily_auto_update mode = M3 readonly orchestrator
legacy qlib/provider path default = skipped
```

日更脚本最近仍在运行，但默认只做 FinMind daily update，不会推进 qlib accepted latest / daily LTR rerank：

```text
yahoo_refresh_triggered = false
provider_publish_triggered = false
latest_signal_updated = false
qlib_legacy_provider_skip_reason = m3_readonly_orchestrator_default_requires_explicit_enable_legacy_provider_publish
```

## 3. 非目标

RCPT15 不授权：

```text
真实交易
OrderIntent
target_weight
target_position
quantity_instruction
broker / quick-trade / real order
production/default/latest/provider/frontend/Agent/monitor/order 改动
默认打开 TW_DAILY_AUTO_ENABLE_LEGACY_PROVIDER_PUBLISH
修改 cron 默认参数
修改 production latest pointer
修改 qlib accepted latest pointer
发布 provider accepted latest
```

任何需要联网拉取 Yahoo/Scrapling 或切 accepted latest 的动作，必须先在 R0 feasibility 中明确列为“需要 coordinator/user 显式授权”，不能由执行者自行做。

## 4. 阶段计划

### RCPT15_R0_FEASIBILITY_AND_BACKFILL_CONTRACT

只读可行性审计，不拉数据、不写生产。

目标：

1. 找到生成 `daily_ltr_rerank_YYYY-MM-DD_score_snapshot.csv` 的本地脚本和依赖；
2. 判断是否存在本地已可用的 qlib latest signal / top50 / feature table，可直接生成 6/18-6/25 shadow artifacts；
3. 判断缺口是否必须走 legacy Yahoo/Scrapling refresh / provider publish / accepted latest；
4. 产出 isolated backfill contract，明确允许/禁止路径；
5. 给出是否可进入 R1。

### RCPT15_R1_ISOLATED_BACKFILL_EXECUTION

只有 R0 通过并且不需要 production latest/provider publish 时才能进入。

若 R0 判断必须联网或切 accepted latest，则 R1 不得执行，必须回到 coordinator/user 明确授权。

### RCPT15_R2_REVIEW_AND_RCPT14A_RERUN

审查 R1 产物；若产生新 source days，则重跑 RCPT14A。

## 5. R0 必需输出

输出目录：

```text
data_tw/experiments/risk_control_policy_2022/rcpt15_r0_isolated_shadow_backfill_feasibility/
```

必须输出：

```text
manifest.json
available_daily_rerank_days.csv
daily_auto_update_status_audit.csv
backfill_script_inventory.csv
candidate_backfill_dates.csv
dependency_gap_audit.csv
isolated_backfill_contract.csv
forbidden_scope_audit.csv
validator_report.json
diagnostic_findings.md
```

执行报告：

```text
docs/tw_portfolio_decision_model/POLICY_RCPT15_R0_ISOLATED_SHADOW_BACKFILL_FEASIBILITY_EXECUTION_REPORT_CN.md
```

审查报告：

```text
docs/tw_portfolio_decision_model/POLICY_RCPT15_R0_ISOLATED_SHADOW_BACKFILL_FEASIBILITY_REVIEW_CN.md
```

建议脚本：

```text
scripts/build_tw_policy_rcpt15_r0_shadow_backfill_feasibility.py
```

## 6. R0 允许结论

```text
PASS_READY_FOR_R1_LOCAL_ISOLATED_BACKFILL
STOP_REQUIRES_EXPLICIT_LEGACY_REFRESH_OR_ACCEPTED_LATEST_AUTHORIZATION
FAIL_NEEDS_REPAIR_FEASIBILITY_INCOMPLETE
STOP_SCOPE_OR_SAFETY_VIOLATION
```

## 7. 审查者重点

审查者必须确认：

1. R0 没有拉取外部数据；
2. R0 没有运行 daily auto update；
3. R0 没有打开 legacy provider gate；
4. R0 没有修改 cron；
5. R0 没有切 qlib accepted latest；
6. R0 没有输出 order/target/broker；
7. R0 的 R1 建议是否真的可在本地隔离完成。
