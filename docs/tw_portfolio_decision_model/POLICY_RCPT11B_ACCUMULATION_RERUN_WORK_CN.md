---
created_at: 2026-06-25
status: work_doc
phase: RCPT11B_ACCUMULATION_RERUN
parent_review: docs/tw_portfolio_decision_model/POLICY_RCPT11B_S2_M1_READONLY_SHADOW_BUILDER_REVIEW_CN.md
production_allowed: false
order_or_target_output_allowed: false
model_training_authorized: false
replay_authorized: false
threshold_tuning_authorized: false
---

# RCPT11B Accumulation Rerun 工作文档

## 1. 目标

重新执行 RCPT11B extended shadow accumulation，但只使用已通过 S2 的 M1-only readonly shadow input。

本轮目标：

```text
把 RCPT10C frozen shadow evidence 与 S2 2026-06-17 M1-only shadow input 合并为 accumulation evidence；
重新运行 production blocker / fail-close gate；
判断是否可以进入 RCPT11C accumulation review。
```

## 2. 非目标

不授权：

```text
真实 replay
training
threshold tuning
mapping expansion
production/default/provider/latest/frontend/Agent/monitor/order 改动
OrderIntent
target_weight
target_position
quantity_instruction
broker / quick-trade / real order
production proposal
```

## 3. 必读输入

必须读取：

```text
docs/tw_portfolio_decision_model/POLICY_RCPT11B_S2_M1_READONLY_SHADOW_BUILDER_REVIEW_CN.md
data_tw/experiments/risk_control_policy_2022/rcpt11b_s2_m1_readonly_shadow_builder/m1_readonly_shadow_input.csv
data_tw/experiments/risk_control_policy_2022/rcpt11b_s2_m1_readonly_shadow_builder/validator_report.json
data_tw/experiments/risk_control_policy_2022/rcpt10c_shadow_replay_diagnostic/shadow_replay_daily_evidence.csv
data_tw/experiments/risk_control_policy_2022/rcpt10c_shadow_replay_diagnostic/validator_report.json
data_tw/experiments/risk_control_policy_2022/rcpt11_m1_extended_shadow_accumulation_and_production_blocker_contract/production_blocker_contract.csv
```

## 4. 必需输出

输出目录：

```text
data_tw/experiments/risk_control_policy_2022/rcpt11b_accumulation_rerun/
```

必须生成：

```text
manifest.json
accumulated_shadow_evidence.csv
new_shadow_input_acceptance.csv
production_blocker_audit.csv
accumulation_summary.json
forbidden_scope_audit.csv
validator_report.json
diagnostic_findings.md
```

执行报告：

```text
docs/tw_portfolio_decision_model/POLICY_RCPT11B_ACCUMULATION_RERUN_EXECUTION_REPORT_CN.md
```

## 5. 合并规则

1. RCPT10C historical evidence 只作为 frozen historical diagnostic evidence；
2. S2 input 是唯一新增 accepted shadow input；
3. 不允许直接使用 LTR source artifact；
4. 不允许生成交易 action/order/target/quantity/broker 字段；
5. `accumulated_shadow_evidence.csv` 可以按日汇总，不需要逐 symbol 交易指令；
6. 必须显式保留 RCPT10C 2 行 null metric 的 historical blocker；
7. S2 新输入如果无 null metric / stale / forbidden field，则记为 accepted new input。

## 6. Fail-close Gate

必须检查：

1. S2 validator 是否 PASS；
2. S2 input 是否 50 行；
3. S2 input 是否只有允许字段；
4. S2 input 是否没有 null score/rank/qlib_score_raw；
5. S2 input 是否 `diagnostic_only=True`、`research_signal_not_order=True`、`pit_pass=True`；
6. S2 input 是否无 action/order/target/quantity/broker 字段；
7. accumulated output 是否隔离在 rcpt11b_accumulation_rerun 目录；
8. no replay/training/tuning/production write。

## 7. 允许结论

```text
PASS_READY_FOR_RCPT11C_ACCUMULATION_REVIEW
FAIL_CLOSE_NEEDS_RCPT11B_REPAIR
STOP_SCOPE_OR_SAFETY_VIOLATION
```

`PASS_READY_FOR_RCPT11C_ACCUMULATION_REVIEW` 只授权进入 RCPT11C 审查，不授权 production proposal 或生产接入。
