---
created_at: 2026-06-25
status: work_doc
phase: RCPT14B_QUARANTINE_ACCEPTANCE_GO_NO_GO_CONTRACT
parent_review: docs/tw_portfolio_decision_model/POLICY_RCPT14A_SHADOW_CONTINUATION_LONGER_ACCUMULATION_REVIEW_CN.md
production_allowed: false
order_or_target_output_allowed: false
model_training_authorized: false
replay_authorized: false
threshold_tuning_authorized: false
---

# RCPT14B Quarantine Acceptance Go/No-Go Contract 工作文档

## 1. 目标

RCPT14B 只做合同化 go/no-go 判定：评估 RCPT13 的两个 historical quarantine 是否可被后续 production-readiness route 作为显式例外接受。

本阶段不做生产接入，不输出交易意图。

## 2. 输入事实

来自 RCPT13：

```text
blocker_count = 2
repaired_count = 0
quarantined_count = 2
production_gate_status = BLOCKED_BY_HISTORICAL_QUARANTINE
```

来自 RCPT14A：

```text
discovered_source_day_count = 2
new_source_day_count = 0
continued_daily_rows = 207
production_gate_status = BLOCKED_BY_HISTORICAL_QUARANTINE_AND_INSUFFICIENT_ACCUMULATION
```

## 3. 非目标

RCPT14B 不授权：

```text
真实 replay
training
threshold tuning
mapping expansion
production/default/latest/provider/frontend/Agent/monitor/order 改动
OrderIntent
target_weight
target_position
quantity_instruction
broker / quick-trade / real order
修改 RCPT10C/RCPT11/RCPT12/RCPT13/RCPT14A frozen evidence 原文件
下载新数据
把 quarantine 直接转换成 production pass
```

## 4. 必读输入

```text
docs/tw_portfolio_decision_model/POLICY_RCPT13_HISTORICAL_BLOCKER_DISPOSITION_AND_SHADOW_CONTINUATION_CONTRACT_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_RCPT14A_SHADOW_CONTINUATION_LONGER_ACCUMULATION_REVIEW_CN.md
data_tw/experiments/risk_control_policy_2022/rcpt13_historical_blocker_disposition_and_shadow_continuation_contract/validator_report.json
data_tw/experiments/risk_control_policy_2022/rcpt13_historical_blocker_disposition_and_shadow_continuation_contract/historical_blocker_disposition.csv
data_tw/experiments/risk_control_policy_2022/rcpt14a_shadow_continuation_longer_accumulation/validator_report.json
data_tw/experiments/risk_control_policy_2022/rcpt14a_shadow_continuation_longer_accumulation/source_day_discovery.csv
data_tw/experiments/risk_control_policy_2022/rcpt14a_shadow_continuation_longer_accumulation/historical_quarantine_gate_audit.csv
```

## 5. 必需输出

输出目录：

```text
data_tw/experiments/risk_control_policy_2022/rcpt14b_quarantine_acceptance_go_no_go_contract/
```

必须输出：

```text
manifest.json
historical_quarantine_scope.csv
quarantine_acceptance_contract.csv
go_no_go_gate_matrix.csv
production_readiness_decision.csv
forbidden_scope_audit.csv
validator_report.json
diagnostic_findings.md
```

执行报告：

```text
docs/tw_portfolio_decision_model/POLICY_RCPT14B_QUARANTINE_ACCEPTANCE_GO_NO_GO_CONTRACT_EXECUTION_REPORT_CN.md
```

建议脚本：

```text
scripts/build_tw_policy_rcpt14b_quarantine_acceptance_contract.py
```

## 6. Go/No-Go 规则

Quarantine 可被“后续 production-readiness route 讨论”的最低条件：

1. quarantine scope 固定为两个 historical rows；
2. no new input null metric blocker；
3. quarantine 原因显式；
4. historical evidence immutability pass；
5. forbidden scope pass。

Production readiness 当前 Go 条件：

1. quarantine acceptance contract pass；
2. 有足够多新增 shadow days 或 coordinator 明确接受短窗口；
3. production integration route 单独授权；
4. no order/target/broker output；
5. no production/default/latest/provider switch in RCPT14B。

若第 2 或第 3 条不满足，必须判定：

```text
NO_GO_PRODUCTION_READINESS
```

## 7. 允许结论

```text
PASS_CONTRACT_COMPLETE_BUT_PRODUCTION_NO_GO
PASS_CONTRACT_COMPLETE_READY_FOR_SEPARATE_PRODUCTION_READINESS_PROPOSAL
FAIL_NEEDS_REPAIR_CONTRACT_INCOMPLETE
STOP_SCOPE_OR_SAFETY_VIOLATION
```

当前在无新增 shadow days 的情况下，预期结论应为：

```text
PASS_CONTRACT_COMPLETE_BUT_PRODUCTION_NO_GO
```
