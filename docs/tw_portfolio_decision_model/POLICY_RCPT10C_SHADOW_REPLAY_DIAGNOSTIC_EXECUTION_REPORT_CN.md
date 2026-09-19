---
created_at: 2026-06-25
status: execution_report
phase: RCPT10C_SHADOW_REPLAY_DIAGNOSTIC
verdict: PASS_SHADOW_ONLY_CONTINUE_ACCUMULATION
production_allowed: false
order_or_target_output_allowed: false
replay_performed: false
model_training_performed: false
threshold_tuning_performed: false
production_chain_modified: false
---

# RCPT10C Shadow Replay Diagnostic 执行报告

## 1. 执行范围

本轮只做 readonly/shadow diagnostic evidence 组织。

本轮未做：

- 真实 replay；
- training；
- threshold tuning；
- production/default/provider/latest/frontend/Agent/monitor/order 改动；
- OrderIntent / target_weight / target_position / quantity_instruction / broker_order_id / quick_trade_flag 输出；
- M2 / M3 恢复。

## 2. 已读取输入

- `docs/tw_portfolio_decision_model/POLICY_RCPT10_M1_PRODUCTION_READINESS_SAFETY_INTEGRATION_MAINLINE_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_RCPT10C_SHADOW_REPLAY_DIAGNOSTIC_WORK_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_RCPT10B_R_CONDITION_FIX_COORDINATOR_CONFIRMATION_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_RCPT10B_R_READONLY_SHADOW_ADAPTER_REPAIR_REVIEW_CN.md`
- `data_tw/experiments/risk_control_policy_2022/rcpt10b_readonly_shadow_adapter/`
- `data_tw/experiments/risk_control_policy_2022/rcpt9c_predeclared_longer_oos_replay/`
- `data_tw/experiments/risk_control_policy_2022/rcpt9d_longer_oos_closure/`

## 3. 产物

- `data_tw/experiments/risk_control_policy_2022/rcpt10c_shadow_replay_diagnostic/manifest.json`
- `data_tw/experiments/risk_control_policy_2022/rcpt10c_shadow_replay_diagnostic/shadow_replay_daily_evidence.csv`
- `data_tw/experiments/risk_control_policy_2022/rcpt10c_shadow_replay_diagnostic/shadow_market_state_explanation.csv`
- `data_tw/experiments/risk_control_policy_2022/rcpt10c_shadow_replay_diagnostic/baseline_attribution_summary.json`
- `data_tw/experiments/risk_control_policy_2022/rcpt10c_shadow_replay_diagnostic/failure_rollback_trigger_audit.csv`
- `data_tw/experiments/risk_control_policy_2022/rcpt10c_shadow_replay_diagnostic/completeness_diagnostic.csv`
- `data_tw/experiments/risk_control_policy_2022/rcpt10c_shadow_replay_diagnostic/forbidden_scope_audit.csv`
- `data_tw/experiments/risk_control_policy_2022/rcpt10c_shadow_replay_diagnostic/validator_report.json`
- `data_tw/experiments/risk_control_policy_2022/rcpt10c_shadow_replay_diagnostic/diagnostic_findings.md`

## 4. 核心证据

唯一候选保持为：

```text
M1_QLIB_SCORE_COMPONENT_PRIMARY
```

lineage 固定为：

```text
source_lineage = RCPT9B_S2B_S2C_fresh_retrain_holdout_lineage
source_replay = RCPT9C_PREDECLARED_LONGER_OOS_REPLAY
source_closure = RCPT9D_LONGER_OOS_CLOSURE
```

baseline attribution 只解释：

```text
baseline_return = 2.27529371
candidate_return = 2.56128630
return_capture = 1.12569480
drawdown_improvement = 0.00000000
```

RCPT10C 未把 M1 表述为显著降低回撤策略。

## 5. Completeness 观察项

已显式报告 RCPT10B `candidate_decision_trace.csv` 空指标行：
- `2025-07-14 TW6919`
- `2026-03-02 TW4989`

这两行没有被忽略，而是进入 `completeness_diagnostic.csv` 与 `validator_report.json` 的 `null_metric_visibility`。

## 6. Validator 结果

- `lineage_traceability_gate` = PASS
- `m1_only_gate` = PASS
- `readonly_shadow_gate` = PASS
- `forbidden_scope_gate` = PASS
- `artifact_completeness_gate` = PASS
- `baseline_attribution_gate` = PASS
- `failure_rollback_diagnostic_gate` = PASS
- `output_path_isolation_gate` = PASS
- `null_metric_visibility_gate` = PASS

## 7. Verdict

```text
PASS_SHADOW_ONLY_CONTINUE_ACCUMULATION
```
