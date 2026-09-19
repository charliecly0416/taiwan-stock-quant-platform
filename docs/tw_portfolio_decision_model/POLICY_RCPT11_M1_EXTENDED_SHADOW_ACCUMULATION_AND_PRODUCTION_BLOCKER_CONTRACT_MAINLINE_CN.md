---
created_at: 2026-06-25
status: coordinator_mainline
route: RCPT11_M1_EXTENDED_SHADOW_ACCUMULATION_AND_PRODUCTION_BLOCKER_CONTRACT
parent_closure: docs/tw_portfolio_decision_model/POLICY_RCPT10D_PRODUCTION_READINESS_GO_NO_GO_CLOSURE_REPORT_CN.md
production_allowed: false
order_or_target_output_allowed: false
model_training_authorized: false
replay_authorized: false
threshold_tuning_authorized: false
---

# RCPT11 M1 Extended Shadow Accumulation And Production Blocker Contract 主线

## 1. 统筹结论

RCPT10D 结论为：

```text
PASS_SHADOW_ONLY_CONTINUE_ACCUMULATION
```

含义：

1. M1 没有失败；
2. M1 已通过 RCPT10 的 safety / readonly shadow / diagnostic evidence gate；
3. 当前仍不授权生产接入；
4. 当前也不直接授权另开 production integration proposal；
5. 下一步应先补齐 extended shadow accumulation 与 production blocker/fail-close 合同。

RCPT11 的任务是把后续 shadow/paper evidence accumulation 变成可执行、可审查、不会误触生产的合同包。

## 2. 非目标

RCPT11 不授权：

```text
真实生产接入
切换默认策略
切换 latest / accepted / provider pointer
frontend live trading action
Agent tool/action trading expansion
OrderIntent
target_weight
target_position
quantity_instruction
broker / quick-trade / real order
真实 replay 执行
training
threshold tuning
mapping expansion
M2 / M3 恢复
```

RCPT11 也不做收益优化，不重新选择阈值，不根据 RCPT9C/RCPT10C 结果调规则。

## 3. 当前事实

M1 frozen evidence：

```text
candidate = M1_QLIB_SCORE_COMPONENT_PRIMARY
source_lineage = RCPT9B_S2B_S2C_fresh_retrain_holdout_lineage
source_replay = RCPT9C_PREDECLARED_LONGER_OOS_REPLAY
source_closure = RCPT9D_LONGER_OOS_CLOSURE
window = 2025-07-01..2026-05-07
baseline_return = 2.27529371
candidate_return = 2.56128630
return_capture = 1.12569480
drawdown_improvement = 0.00000000
```

RCPT10C known issue：

```text
2025-07-14 TW6919 missing score|rank|score_component|qlib_score_raw|ltr_score
2026-03-02 TW4989 missing score|rank|score_component|qlib_score_raw|ltr_score
```

这些空指标行已经显式暴露，因此不是 RCPT10C 的 STOP；但它们必须成为 RCPT11 的 production blocker / fail-close 合同项。

## 4. RCPT11 阶段计划

### RCPT11A: Contract Package Freeze

目标：

```text
冻结 extended shadow accumulation contract；
冻结 production blocker / fail-close contract；
冻结 no-order/no-target artifact contract；
冻结 go/no-go gate；
生成静态 validator evidence。
```

不执行 replay，不接生产，不训练，不调阈值。

### RCPT11B: Future Shadow Accumulation Execution

仅作为后续阶段，不在本轮执行。

目标：

```text
按 RCPT11A 合同积累新的 shadow/paper evidence；
遇到 blocker 必须 fail-close；
不得输出订单、目标仓位或 broker 指令。
```

### RCPT11C: Accumulation Review And Production Proposal Decision

仅作为后续阶段，不在本轮执行。

目标：

```text
根据 RCPT11B 的新证据判断是否继续 shadow、fail-close，或另开独立 production integration proposal。
```

## 5. RCPT11A 必需产物

输出目录：

```text
data_tw/experiments/risk_control_policy_2022/rcpt11_m1_extended_shadow_accumulation_and_production_blocker_contract/
```

必须包含：

```text
manifest.json
shadow_accumulation_contract.csv
production_blocker_contract.csv
no_order_no_target_artifact_contract.csv
go_no_go_gate_contract.csv
forbidden_scope_audit.csv
validator_report.json
diagnostic_findings.md
```

## 6. Production Blocker 原则

以下情况必须在后续执行中 fail-close，不能进入 production proposal：

```text
missing score
missing rank
missing score_component
missing qlib_score_raw
missing ltr_score
stale signal date
lineage mismatch
M2/M3 mapping present
order/target/quantity/broker field present
production/default/latest/provider write
threshold drift
mapping expansion
training/replay outside authorized phase
unexplained market-state trigger
```

## 7. Closure Criteria

RCPT11A 允许结论：

```text
PASS_READY_FOR_RCPT11B_SHADOW_ACCUMULATION
FAIL_NEEDS_RCPT11A_REPAIR
STOP_SCOPE_OR_SAFETY_VIOLATION
```

RCPT11A 通过只表示合同包完整，仍不表示生产 ready。

## 8. Executor Brief

执行者只允许：

1. 新增 RCPT11A 合同 artifact；
2. 写执行报告；
3. 不执行 replay/training/tuning；
4. 不改 production/default/latest/provider/frontend/Agent/monitor/order。

## 9. Reviewer Brief

审查者必须核对：

1. M1-only；
2. M2/M3 forbidden；
3. blocker contract 是否覆盖 RCPT10C 的 2 行 null metric；
4. 是否严格 no-order/no-target/no-broker；
5. 是否没有 replay/training/tuning/production 改动；
6. validator 是否能支撑进入 RCPT11B shadow accumulation。
