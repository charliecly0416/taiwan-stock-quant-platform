---
created_at: 2026-06-25
status: coordinator_mainline
route: RCPT10_M1_PRODUCTION_READINESS_SAFETY_INTEGRATION
parent_closure: docs/tw_portfolio_decision_model/POLICY_RCPT9D_LONGER_OOS_CLOSURE_EXECUTION_REPORT_CN.md
production_allowed: false
order_or_target_output_allowed: false
model_training_authorized: false
threshold_tuning_authorized: false
---

# RCPT10 M1 Production Readiness Safety Integration 主线

## 1. 统筹结论

RCPT9D 已关闭，结论为：

```text
PASS_READY_FOR_PRODUCTION_READINESS_ROUTE
```

但该结论不是生产授权。它只表示：

```text
M1_QLIB_SCORE_COMPONENT_PRIMARY
```

在 RCPT9C 的 longer strict OOS holdout `2025-07-01..2026-05-07` 上通过 gate，可进入 production readiness / safety integration 路线。

RCPT10 的目标是验证 M1 能否满足生产前安全、可解释、回滚、shadow/paper 运行、前端只读展示和 Agent 解释边界。

## 2. 非目标

RCPT10 当前不授权：

```text
直接生产化
切换默认策略
修改 production/default/provider/latest/frontend/Agent/monitor/order 链路
输出 OrderIntent
输出 target_weight
输出 target_position
输出 quantity_instruction
broker / quick-trade / real order
复活 M2 或 M3
新增 mapping
调阈值
重训 qlib/LTR
用 RCPT9C 结果继续优化规则
```

如果后续确实需要接入前端、Agent 或 daily orchestrator，必须另开明确阶段，并且仍从 readonly/shadow 开始。

## 3. 当前事实

RCPT9C longer strict OOS holdout：

```text
window: 2025-07-01..2026-05-07
trading_days: 205
lineage: RCPT9B_S2B_S2C_fresh_retrain_holdout_lineage
readonly_accounting_only: true
```

Mapping disposition：

| mapping | RCPT9D disposition | next route |
| --- | --- | --- |
| M1_QLIB_SCORE_COMPONENT_PRIMARY | ACCEPT_FOR_PRODUCTION_READINESS_ROUTE | allowed |
| M2_LTR_SCORE_COMPONENT_SECONDARY | REJECT_FOR_PRODUCTION_READINESS_ROUTE | forbidden |
| M3_BLEND_Q70_L30_TERTIARY | REJECTED_PRIOR_MAPPING_NOT_REPLAYED | forbidden |

M1 RCPT9C evidence：

```text
baseline_return = 2.27529371
candidate_return = 2.56128630
return_capture = 1.12569480
drawdown_improvement = 0.00000000
average_cash_rate = 0.06759263
average_position_count = 9.37560976
```

解释：

```text
M1 的优势主要来自收益改善且 drawdown 不恶化；不是来自显著降低 max drawdown。
```

因此 RCPT10 必须特别关注：

```text
1. 不把 M1 夸大成 drawdown 显著改善策略；
2. 不把研究 replay 直接转换成订单或目标仓位；
3. 不让 shadow/dry-run 产物污染 production/latest/default；
4. 明确失败回滚条件。
```

## 4. 架构边界

RCPT10 只允许生成研究/只读/影子产物：

```text
data_tw/experiments/risk_control_policy_2022/rcpt10_*/
docs/tw_portfolio_decision_model/POLICY_RCPT10*_*.md
scripts/build_tw_policy_rcpt10_*.py
scripts/run_tw_policy_rcpt10_*.py
```

不得写入或修改：

```text
production default strategy
provider latest pointer
qlib accepted latest pointer
frontend/API live route
Agent live prompt/tool/action
monitor scan/write
broker/order/quick-trade path
real portfolio state
```

## 5. 阶段计划

### RCPT10A: M1-Only Candidate And Safety Contract

目标：

```text
冻结 M1-only production-readiness candidate contract；
冻结 shadow/dry-run 安全边界；
冻结 forbidden scope；
冻结 go/no-go gate；
不实现 adapter，不 replay，不接生产链。
```

输出目录：

```text
data_tw/experiments/risk_control_policy_2022/rcpt10a_m1_safety_contract/
```

必须输出：

```text
manifest.json
m1_candidate_contract.json
safety_boundary_contract.csv
shadow_artifact_contract.csv
go_no_go_gate_contract.csv
failure_rollback_contract.csv
forbidden_scope_audit.csv
validator_report.json
diagnostic_findings.md
```

允许结论：

```text
PASS_READY_FOR_RCPT10B_READONLY_SHADOW_ADAPTER
FAIL_NEEDS_RCPT10A_REPAIR
STOP_SCOPE_OR_PRODUCTION_BOUNDARY_VIOLATION
```

### RCPT10B: Readonly Shadow Adapter Builder

前提：

```text
RCPT10A PASS
```

目标：

```text
构建 M1-only readonly shadow artifact adapter。
```

该 adapter 只能输出 shadow/paper artifact，不得输出订单或 target。

### RCPT10C: Shadow Replay / Paper Accumulation Diagnostic

前提：

```text
RCPT10B PASS
```

目标：

```text
用 frozen M1 adapter 生成 shadow/paper daily evidence；
验证 artifact 完整性、市场状态解释、baseline attribution、failure rollback trigger。
```

### RCPT10D: Production Readiness Go/No-Go Closure

目标：

```text
判断 M1 是否可以进入下一条真正 production integration proposal。
```

允许结论：

```text
PASS_READY_FOR_SEPARATE_PRODUCTION_INTEGRATION_PROPOSAL
PASS_SHADOW_ONLY_CONTINUE_ACCUMULATION
FAIL_NOT_PRODUCTION_READY
STOP_SCOPE_OR_SAFETY_VIOLATION
```

## 6. RCPT10 Gate 原则

RCPT10 不再追求回测收益提升，而是验证生产前安全性。

必须满足：

```text
1. M1-only；
2. no M2/M3；
3. no threshold tuning；
4. no training；
5. no order/target/quantity/broker output；
6. shadow artifacts isolated under rcpt10 output root；
7. no latest/default/provider switch；
8. replay/shadow artifact 可追溯到 RCPT9B lineage；
9. 每个 trigger 都能解释 score/rank/market feature；
10. 有明确 rollback/fail-close 条件。
```

## 7. Stop Conditions

必须 STOP：

```text
1. 任何阶段试图输出 OrderIntent / target_weight / target_position / quantity_instruction；
2. 任何阶段试图接 broker / quick-trade / real order；
3. 任何阶段复活 M2/M3；
4. 任何阶段调阈值或新增 mapping；
5. shadow artifact 写出到非隔离目录；
6. 需要修改 production/default/latest/provider 才能继续；
7. 无法证明 M1 artifact 可追溯到 RCPT9 lineage；
8. 无法定义 fail-close rollback 条件。
```

## 8. 第一阶段执行命令

执行者执行 RCPT10A：

```text
读取本主线、RCPT9D closure、RCPT9C replay/review；
只生成 M1-only candidate 与 safety contracts；
不得实现 adapter；
不得 replay；
不得修改生产链。
```

## 9. 第一阶段审查重点

审查者必须判断：

```text
1. 是否 M1-only；
2. 是否正确排除 M2/M3；
3. 是否冻结 safety / shadow / rollback / go-no-go 合同；
4. 是否没有 adapter/replay/生产越权；
5. 是否可以进入 RCPT10B readonly shadow adapter。
```
