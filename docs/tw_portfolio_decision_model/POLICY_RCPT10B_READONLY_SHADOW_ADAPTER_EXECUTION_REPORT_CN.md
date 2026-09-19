---
created_at: 2026-06-25
status: execution_report
phase: RCPT10B_READONLY_SHADOW_ADAPTER
verdict: PASS_READY_FOR_RCPT10C_SHADOW_REPLAY_DIAGNOSTIC
production_allowed: false
order_or_target_output_allowed: false
replay_performed: false
model_training_performed: false
threshold_tuning_performed: false
production_chain_modified: false
---

# RCPT10B Readonly Shadow Adapter 执行报告

## 1. 执行范围

本轮只实现 M1-only readonly shadow artifact adapter，并复用 RCPT10A frozen contract 与 RCPT9C/RCPT9D 已有证据生成说明性 shadow artifact。

本轮未做：

- replay；
- training；
- threshold tuning；
- mapping 扩展；
- production/default/provider/latest/frontend/Agent/monitor/order 改动；
- OrderIntent / target_weight / target_position / quantity_instruction / broker_order_id / quick_trade_flag 输出。

## 2. 已读取输入

- `docs/tw_portfolio_decision_model/POLICY_RCPT10_M1_PRODUCTION_READINESS_SAFETY_INTEGRATION_MAINLINE_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_RCPT10B_READONLY_SHADOW_ADAPTER_WORK_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_RCPT10A_M1_SAFETY_CONTRACT_REVIEW_CN.md`
- `data_tw/experiments/risk_control_policy_2022/rcpt10a_m1_safety_contract`
- `data_tw/experiments/risk_control_policy_2022/rcpt9c_predeclared_longer_oos_replay`
- `data_tw/experiments/risk_control_policy_2022/rcpt9d_longer_oos_closure`

## 3. Adapter 实现结果

已新增脚本：

- `scripts/build_tw_policy_rcpt10b_readonly_shadow_adapter.py`

已生成最小 shadow artifact：

- `data_tw/experiments/risk_control_policy_2022/rcpt10b_readonly_shadow_adapter/manifest.json`
- `data_tw/experiments/risk_control_policy_2022/rcpt10b_readonly_shadow_adapter/candidate_signal_snapshot.json`
- `data_tw/experiments/risk_control_policy_2022/rcpt10b_readonly_shadow_adapter/candidate_decision_trace.csv`
- `data_tw/experiments/risk_control_policy_2022/rcpt10b_readonly_shadow_adapter/candidate_daily_summary.csv`
- `data_tw/experiments/risk_control_policy_2022/rcpt10b_readonly_shadow_adapter/forbidden_scope_audit.csv`
- `data_tw/experiments/risk_control_policy_2022/rcpt10b_readonly_shadow_adapter/validator_report.json`
- `data_tw/experiments/risk_control_policy_2022/rcpt10b_readonly_shadow_adapter/diagnostic_findings.md`

## 4. M1-only 说明

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

RCPT10B 对 M1 的语义保持与 RCPT10A 一致：

```text
M1 仅可解释为：在 2025-07-01..2026-05-07 的 RCPT9C longer holdout 上收益更高且 drawdown 未恶化。
不得表述为显著降低回撤。
不得表述为买卖建议、仓位建议、目标权重建议或可执行交易指令。
```

## 5. Shadow artifact 摘要

`candidate_signal_snapshot.json` 提供最新 signal date 的 top symbol snapshot 与 market state summary。

`candidate_decision_trace.csv` 提供按 signal date 对齐的 symbol / score / rank / risk_gate_state / reason_code / market_features_used 解释 trace。

`candidate_daily_summary.csv` 提供按日的 signal_count、market_regime_summary 与 explanation trace 完整性摘要。

## 6. Runtime validator 结果

- `lineage_traceability_gate` = PASS
- `m1_only_gate` = PASS
- `readonly_shadow_gate` = PASS
- `forbidden_scope_gate` = PASS
- `artifact_completeness_gate` = PASS
- `explanation_trace_gate` = PASS
- `rollback_contract_gate` = PASS
- `output_path_isolation_gate` = PASS
- `shadow_schema_runtime_gate` = PASS
- `forbidden_field_runtime_gate` = PASS

## 7. Fail-close 边界结果

- 所有输出均隔离在 `data_tw/experiments/risk_control_policy_2022/rcpt10b_readonly_shadow_adapter`；
- 未发现禁字段落入业务 shadow artifact；
- 未发现非 M1 mapping 渗入 RCPT10B 输出；
- validator 可独立支撑进入 RCPT10C 的 runtime 结论。

## 8. Verdict

```text
PASS_READY_FOR_RCPT10C_SHADOW_REPLAY_DIAGNOSTIC
```
