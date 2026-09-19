---
created_at: 2026-06-22T14:03:07+00:00
status: executed_pba0_contract_baseline_audit
phase: PBA0_CONTRACT_BASELINE_AUDIT
mainline_doc: docs/tw_portfolio_decision_model/POLICY_PBA_BASELINE_ANCHORED_ACTIVE_POLICY_MAINLINE_CN.md
work_doc: docs/tw_portfolio_decision_model/POLICY_PBA0_CONTRACT_BASELINE_AUDIT_WORK_CN.md
artifact_root: data_tw/experiments/baseline_anchored_active_policy/pba0_contract_baseline_audit
strict_test_used: false
training_run: false
replay_return_run: false
production_allowed: false
recommendation: PASS_READY_FOR_REVIEWER_TO_AUDIT_PBA0
---

# PBA0 Contract / Baseline Snapshot / Research Audit 执行报告

## 1. Scope

本轮只执行 PBA0：合同冻结、baseline snapshot schema、active overlay action space、research adoption audit、validator / golden samples 设计。

未训练模型，未运行收益 replay，未运行或读取 strict_test，未进入 PBA1。

## 2. Documents Read

```text
docs/tw_portfolio_decision_model/POLICY_PBA_BASELINE_ANCHORED_ACTIVE_POLICY_MAINLINE_CN.md
docs/tw_portfolio_decision_model/POLICY_PAL2_R_COST_AWARE_CONCENTRATION_CONSTRAINED_EIIE_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_PAL2_R_COST_AWARE_CONCENTRATION_CONSTRAINED_EIIE_EXECUTION_REPORT_CN.md
docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md
docs/tw_modular_contracts/NEW_MODEL_AND_STRATEGY_DEVELOPER_GUIDE_CN.md
docs/tw_modular_contracts/MODEL_SIGNAL_CONTRACT_CN.md
docs/tw_modular_contracts/STRATEGY_RULE_CONTRACT_CN.md
docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md
docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md
```

## 3. Research Audit Summary

`research_adoption_audit.csv` 已逐项覆盖 PBA 主线 R1-R8：

```text
R1 Active Portfolio Management / active return
R2 Residual Policy Learning
R3 FinRL
R4 EIIE / PGPortfolio
R5 Transaction cost / no-trade region literature
R6 Contextual bandit / LinUCB
R7 Offline RL: CQL / IQL / BCQ
R8 Alpha / signal combination and meta-labeling
```

## 4. Contract Artifacts

已输出：

```text
baseline_action_snapshot_schema.json
active_policy_decision_schema.json
pba_replay_result_schema.json
action_space_design.md
cash_no_trade_degeneracy_gate_design.md
```

核心边界：

```text
baseline anchored active overlay only
free allocation vector forbidden
Layer C diagnostic only
target_weight / target_position / quantity / broker_order forbidden
```

## 5. Forbidden Actions Audit

```text
training_run = false
replay_return_run = false
strict_test_used = false
order_intent_output = false
target_weight_output = false
target_position_output = false
quantity_or_broker_output = false
provider/latest/monitor/frontend/Agent/broker/production touched = false
```

## 6. Evidence Produced

```text
manifest.json
research_adoption_audit.csv
baseline_action_snapshot_schema.json
active_policy_decision_schema.json
pba_replay_result_schema.json
action_space_design.md
cash_no_trade_degeneracy_gate_design.md
forbidden_consumer_audit.csv
validator_design.md
golden_sample_design.md
```

## 7. Issues / Blockers / Deviations

未发现 active overlay diagnostic 与 OrderIntent / target_weight / target_position / quantity 无法区分的合同冲突。

## 8. Recommendation

```text
PASS_READY_FOR_REVIEWER_TO_AUDIT_PBA0
```
