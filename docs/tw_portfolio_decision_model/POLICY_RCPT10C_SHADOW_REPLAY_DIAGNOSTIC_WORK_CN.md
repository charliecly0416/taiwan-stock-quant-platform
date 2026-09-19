---
created_at: 2026-06-25
status: work_doc
phase: RCPT10C_SHADOW_REPLAY_DIAGNOSTIC
parent_mainline: docs/tw_portfolio_decision_model/POLICY_RCPT10_M1_PRODUCTION_READINESS_SAFETY_INTEGRATION_MAINLINE_CN.md
parent_review: docs/tw_portfolio_decision_model/POLICY_RCPT10B_R_READONLY_SHADOW_ADAPTER_REPAIR_REVIEW_CN.md
production_allowed: false
order_or_target_output_allowed: false
model_training_authorized: false
replay_authorized: false
threshold_tuning_authorized: false
---

# RCPT10C Shadow Replay Diagnostic 工作文档

## 1. 前提

RCPT10B repair 复审结论为：

```text
PASS_WITH_CONDITIONS_FOR_RCPT10C
```

RCPT10C 仅可在以下条件先满足后启动：

1. `data_tw/experiments/risk_control_policy_2022/rcpt10b_readonly_shadow_adapter/diagnostic_findings.md`
   必须与最终 `validator_report.json` / `manifest.json` 结论一致；
2. RCPT10C 必须把 RCPT10B `candidate_decision_trace.csv` 中空指标行纳入 completeness diagnostic。

## 2. 目标

RCPT10C 目标是：

```text
用 frozen M1 readonly shadow adapter 继续组织 shadow replay / paper accumulation 诊断证据，
验证 artifact 完整性、市场状态解释、baseline attribution、failure rollback trigger。
```

RCPT10C 的产物仍然只能是 readonly / shadow / diagnostic evidence。

## 3. 非目标

RCPT10C 不授权：

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
真实 replay 执行
training
threshold tuning
mapping 扩展
M2 / M3 恢复
```

这里的 “shadow replay diagnostic” 指对既有 frozen evidence 的只读诊断组织，不是新执行一轮可写 replay。

## 4. 必读输入

必须读取：

```text
docs/tw_portfolio_decision_model/POLICY_RCPT10_M1_PRODUCTION_READINESS_SAFETY_INTEGRATION_MAINLINE_CN.md
docs/tw_portfolio_decision_model/POLICY_RCPT10B_READONLY_SHADOW_ADAPTER_WORK_CN.md
docs/tw_portfolio_decision_model/POLICY_RCPT10B_R_READONLY_SHADOW_ADAPTER_REPAIR_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_RCPT10B_READONLY_SHADOW_ADAPTER_EXECUTION_REPORT_CN.md
docs/tw_portfolio_decision_model/POLICY_RCPT9D_LONGER_OOS_CLOSURE_EXECUTION_REPORT_CN.md
data_tw/experiments/risk_control_policy_2022/rcpt10b_readonly_shadow_adapter/
data_tw/experiments/risk_control_policy_2022/rcpt9c_predeclared_longer_oos_replay/
data_tw/experiments/risk_control_policy_2022/rcpt9d_longer_oos_closure/
```

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

## 6. 输出目录

建议输出根目录：

```text
data_tw/experiments/risk_control_policy_2022/rcpt10c_shadow_replay_diagnostic/
```

执行报告：

```text
docs/tw_portfolio_decision_model/POLICY_RCPT10C_SHADOW_REPLAY_DIAGNOSTIC_EXECUTION_REPORT_CN.md
```

## 7. 必需产物

RCPT10C 至少必须生成：

```text
manifest.json
shadow_replay_daily_evidence.csv
shadow_market_state_explanation.csv
baseline_attribution_summary.json
failure_rollback_trigger_audit.csv
completeness_diagnostic.csv
forbidden_scope_audit.csv
validator_report.json
diagnostic_findings.md
```

## 8. 诊断要求

### 8.1 完整性诊断

必须覆盖：

```text
RCPT10B shadow artifacts required files completeness
decision trace null / empty metric rows
daily summary date continuity
snapshot / trace / daily summary / baseline attribution cross-link integrity
```

### 8.2 市场状态解释

必须限定为 readonly explanation：

```text
risk_gate_state
avg_adaptive_score
avg_score_component
rule05_trigger_count
overlay_trigger_count
blocked_sell_count
market_regime_summary
```

不得把这些字段改写成买卖建议、仓位建议或执行指令。

### 8.3 baseline attribution

必须回到 RCPT9C / RCPT9D 已冻结证据，只允许解释：

```text
baseline_return
candidate_return
return_capture
drawdown_improvement
```

不得把 M1 改写成“显著降低回撤”策略。

### 8.4 rollback trigger

必须只做 diagnostic audit，不得触发真实回滚。

## 9. Validator 要求

RCPT10C validator 至少必须验证：

1. `lineage_traceability_gate`
2. `m1_only_gate`
3. `readonly_shadow_gate`
4. `forbidden_scope_gate`
5. `artifact_completeness_gate`
6. `baseline_attribution_gate`
7. `failure_rollback_diagnostic_gate`
8. `output_path_isolation_gate`
9. `null_metric_visibility_gate`

其中 `null_metric_visibility_gate` 不能只检查列是否存在，必须显式报告空指标行数量与位置。

## 10. 允许结论

RCPT10C 允许结论：

```text
PASS_READY_FOR_RCPT10D_PRODUCTION_READINESS_CLOSURE
PASS_SHADOW_ONLY_CONTINUE_ACCUMULATION
FAIL_NEEDS_RCPT10C_REPAIR
STOP_SCOPE_OR_SAFETY_VIOLATION
```

如果 RCPT10C 期间重新出现 order/target/broker/quick-trade/production/default/provider/latest/frontend/Agent/monitor 越权，必须直接 fail-close。
