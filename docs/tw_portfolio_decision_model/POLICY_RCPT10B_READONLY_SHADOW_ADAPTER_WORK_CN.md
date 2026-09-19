---
created_at: 2026-06-25
status: work_doc
phase: RCPT10B_READONLY_SHADOW_ADAPTER
parent_mainline: docs/tw_portfolio_decision_model/POLICY_RCPT10_M1_PRODUCTION_READINESS_SAFETY_INTEGRATION_MAINLINE_CN.md
parent_review: docs/tw_portfolio_decision_model/POLICY_RCPT10A_M1_SAFETY_CONTRACT_REVIEW_CN.md
production_allowed: false
order_or_target_output_allowed: false
model_training_authorized: false
replay_authorized: false
threshold_tuning_authorized: false
---

# RCPT10B Readonly Shadow Adapter 工作文档

## 1. 前提

RCPT10A 独立审查结论为：

```text
PASS_READY_FOR_RCPT10B_READONLY_SHADOW_ADAPTER
```

RCPT10B 只在该前提下启动。

## 2. 目标

构建：

```text
M1-only readonly shadow artifact adapter
```

该 adapter 的职责仅限于把已冻结的 M1 候选解释与只读证据整理为 shadow/paper artifact。

RCPT10B 不授权：

```text
生产接入
default strategy 切换
latest / accepted pointer 切换
provider publish / refresh
frontend live trading action
Agent tool/action trading expansion
OrderIntent
target_weight
target_position
quantity_instruction
broker / quick-trade / real order
replay
training
threshold tuning
mapping 扩展
```

## 3. 必读输入

必须读取：

```text
docs/tw_portfolio_decision_model/POLICY_RCPT10_M1_PRODUCTION_READINESS_SAFETY_INTEGRATION_MAINLINE_CN.md
docs/tw_portfolio_decision_model/POLICY_RCPT10A_M1_SAFETY_CONTRACT_WORK_CN.md
docs/tw_portfolio_decision_model/POLICY_RCPT10A_M1_SAFETY_CONTRACT_EXECUTION_REPORT_CN.md
docs/tw_portfolio_decision_model/POLICY_RCPT10A_M1_SAFETY_CONTRACT_REVIEW_CN.md
data_tw/experiments/risk_control_policy_2022/rcpt10a_m1_safety_contract/
docs/tw_portfolio_decision_model/POLICY_RCPT9D_LONGER_OOS_CLOSURE_EXECUTION_REPORT_CN.md
data_tw/experiments/risk_control_policy_2022/rcpt9d_longer_oos_closure/
```

其中 `data_tw/experiments/risk_control_policy_2022/rcpt10a_m1_safety_contract/` 为 RCPT10B 的上游控制合同。

## 4. 实现边界

RCPT10B 只允许：

1. 读取 RCPT10A frozen contract；
2. 构建只读 adapter；
3. 输出最小 shadow artifact；
4. 构建与执行 adapter 级 validator；
5. 生成 execution report 与 artifact manifest。

RCPT10B 不得：

1. 修改任何生产链路；
2. 写入 `rcpt10*` 目录以外的“最新指针 / 默认配置 / 生产状态”；
3. 生成订单、目标仓位、权重、数量、broker 相关字段；
4. 借由 adapter 名义做 replay、训练、调阈值或 mapping 搜索。

## 5. 候选范围

唯一允许候选：

```text
M1_QLIB_SCORE_COMPONENT_PRIMARY
```

必须固化：

```text
source_lineage = RCPT9B_S2B_S2C_fresh_retrain_holdout_lineage
source_replay = RCPT9C_PREDECLARED_LONGER_OOS_REPLAY
source_closure = RCPT9D_LONGER_OOS_CLOSURE
```

明确禁止：

```text
M2_LTR_SCORE_COMPONENT_SECONDARY
M3_BLEND_Q70_L30_TERTIARY
```

任何 M2/M3 痕迹一旦出现在 adapter 产物、日志、validator 或 manifest 中，均视为 fail-close。

## 6. 输出目录

建议输出根目录：

```text
data_tw/experiments/risk_control_policy_2022/rcpt10b_readonly_shadow_adapter/
```

执行报告：

```text
docs/tw_portfolio_decision_model/POLICY_RCPT10B_READONLY_SHADOW_ADAPTER_EXECUTION_REPORT_CN.md
```

## 7. 必需产物

RCPT10B 至少必须生成：

```text
manifest.json
candidate_signal_snapshot.json
candidate_decision_trace.csv
candidate_daily_summary.csv
forbidden_scope_audit.csv
validator_report.json
diagnostic_findings.md
```

可选补充产物仅限只读说明性文件，但不得改变最小合同。

## 8. Shadow Artifact 要求

### 8.1 `manifest.json`

必须至少包含：

```text
phase
status
candidate_id
source_lineage
source_replay
source_closure
production_allowed=false
order_or_target_output_allowed=false
artifact_paths
validator_summary
```

### 8.2 `candidate_signal_snapshot.json`

必须至少包含：

```text
asof
candidate_id
lineage
score_source
top_symbols_snapshot
market_state_summary
interpretation_constraints
```

### 8.3 `candidate_decision_trace.csv`

必须至少包含列：

```text
date
symbol
score
rank
risk_gate_state
reason_code
market_features_used
```

### 8.4 `candidate_daily_summary.csv`

必须至少包含列：

```text
date
candidate_id
signal_count
market_regime_summary
explanation_trace_status
```

### 8.5 `forbidden_scope_audit.csv`

必须覆盖：

```text
m1_only_scope
no_order_output
no_target_output
no_quantity_output
no_broker_or_quick_trade
no_production_chain_write
shadow_output_isolated
no_replay_execution
no_training
no_threshold_tuning
```

### 8.6 `validator_report.json`

必须至少给出：

```text
required_files_status
lineage_traceability_status
m1_only_status
readonly_boundary_status
forbidden_field_scan_status
output_path_isolation_status
schema_completeness_status
recommended_verdict
```

## 9. 明确禁止字段

RCPT10B 所有产物中都不得出现：

```text
OrderIntent
target_weight
target_position
quantity_instruction
broker_order_id
quick_trade_flag
```

如果需要表达“禁止”，只能出现在 contract / audit / validator 的禁字段说明中，不能作为业务输出字段出现。

## 10. 必须通过的 Gate

RCPT10B 必须至少验证：

1. `lineage_traceability_gate`
2. `m1_only_gate`
3. `readonly_shadow_gate`
4. `forbidden_scope_gate`
5. `artifact_completeness_gate`
6. `explanation_trace_gate`
7. `rollback_contract_gate`

此外，RCPT10B 还必须新增实现层 gate：

8. `output_path_isolation_gate`
9. `shadow_schema_runtime_gate`
10. `forbidden_field_runtime_gate`

## 11. Fail-Close / Rollback 要求

RCPT10B 遇到以下任一情形必须停止并判失败，不得“带问题进入 RCPT10C”：

1. lineage 无法追溯到 RCPT9B / RCPT9C / RCPT9D；
2. 出现 M2/M3；
3. 输出路径不在 `rcpt10b_*` 隔离根目录下；
4. 任何产物含有 order/target/quantity/broker/quick-trade 字段；
5. 解释 trace 缺失；
6. 必需产物缺失；
7. validator 无法给出 PASS；
8. 任何生产链路被写入或修改。

## 12. 解释语义约束

RCPT10B 对 M1 的描述必须保持与 RCPT10A 一致：

```text
M1 仅可解释为：在 2025-07-01..2026-05-07 的 RCPT9C longer holdout 上收益更高且 drawdown 未恶化。
不得表述为“显著降低回撤”。
不得表述为买卖建议、仓位建议、目标权重建议或可执行交易指令。
```

## 13. 允许结论

```text
PASS_READY_FOR_RCPT10C_SHADOW_REPLAY_DIAGNOSTIC
PASS_WITH_CONDITIONS_FOR_RCPT10C
FAIL_NEEDS_RCPT10B_REPAIR
STOP_SCOPE_OR_PRODUCTION_BOUNDARY_VIOLATION
```

## 14. RCPT10B 完成标准

只有同时满足以下条件，RCPT10B 才算完成：

1. adapter 已实现；
2. adapter 只输出 RCPT10A 规定的最小 shadow artifact；
3. 所有输出路径隔离；
4. 所有禁字段扫描通过；
5. M1-only 范围保持；
6. execution report 说明未触发 replay / training / threshold tuning / production modification；
7. validator_report.json 可独立支撑进入 RCPT10C 的结论。
