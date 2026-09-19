---
created_at: 2026-06-23
status: executed_ral_ed2_a_baseline_replay_accounting_audit
phase: RAL_ED2_A_BASELINE_REPLAY_ACCOUNTING_AUDIT
work_doc: docs/tw_portfolio_decision_model/POLICY_RAL_ED2_A_BASELINE_REPLAY_ACCOUNTING_AUDIT_WORK_CN.md
artifact_root: data_tw/experiments/explicit_rule_discovery/ral_ed2_a_baseline_replay_accounting_audit
final_recommendation: READY_FOR_REVIEWER_TO_CLOSE_BLOCK_BUY_ROUTE_AS_NEGATIVE_EVIDENCE
strict_test_used: false
model_training_run: false
production_allowed: false
readonly_only: true
simulation_only: true
---

# RAL-ED2-A Baseline Replay Accounting Audit 执行报告

## 1. Scope

本轮只审计 ED2 baseline/replay accounting，不执行 ED3、strict_test、规则调参、新规则、训练、订单或生产集成。

## 2. Main Result

```text
ed2_reported_baseline_net_return_after_fee_tax = 0.95376753
ed2_a_recomputed_net_return_after_fee_tax = 0.95376753
core_metric_diff_pass = true
nav_accounting_pass = true
fee_tax_turnover_pass = true
pending_order_window_pass = true
price_signal_alignment_pass = true
liquidation_sensitivity_conclusion_unchanged = true
validator_ok = true
failed_count = 0
final_recommendation = READY_FOR_REVIEWER_TO_CLOSE_BLOCK_BUY_ROUTE_AS_NEGATIVE_EVIDENCE
```

## 3. Recommendation

```text
READY_FOR_REVIEWER_TO_CLOSE_BLOCK_BUY_ROUTE_AS_NEGATIVE_EVIDENCE
```
