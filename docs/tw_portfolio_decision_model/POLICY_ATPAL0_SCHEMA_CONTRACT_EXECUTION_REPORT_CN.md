---
created_at: 2026-06-23T12:28:22+00:00
status: pass_ready_for_review
phase: ATPAL0_SCHEMA_CONTRACT_FREEZE
artifact_root: data_tw/experiments/action_trade_pnl_attribution_ledger/atpal0_contract
readonly_only: true
simulation_only: true
production_allowed: false
---

# ATPAL0 Schema / Contract Freeze 执行报告

## 1. Scope and Non-goals

本轮只冻结 ATPAL schema / contract，不生成正式账本，不运行 ATPAL1/2/3/4，不跑策略实验，不选择规则或阈值，不使用 strict_test，不训练模型，不触碰生产链路。

## 2. Documents Read

- `docs/tw_portfolio_decision_model/POLICY_ATPAL_ACTION_TRADE_PNL_ATTRIBUTION_LEDGER_MAINLINE_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_RAL_FPA_FINAL_CLOSURE_REVIEW_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_RAL_FPA_FINAL_COORDINATOR_OPINION_CN.md`
- `scripts/run_tw_policy_action_model_pa1.py`
- `docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md`
- `docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md`

## 3. Outputs

输出目录：`data_tw/experiments/action_trade_pnl_attribution_ledger/atpal0_contract`

## 4. Contract Summary

已定义 11 张 ledger/audit 表、98 个字段、13 个 PnL component、8 条 reconciliation rule，以及 forbidden field audit。

## 5. Validator Summary

```json
{
  "ok": true,
  "status": "PASS_ATPAL0_SCHEMA_CONTRACT_READY_FOR_REVIEW",
  "phase": "ATPAL0_SCHEMA_CONTRACT_FREEZE",
  "failed_count": 0,
  "final_recommendation": "READY_FOR_REVIEWER_TO_CONSIDER_ATPAL1_WORK_DOC"
}
```

## 6. Forbidden Audit

OrderIntent、target_weight、target_position、quantity_instruction、broker_order、strict_test、model_training、rule/threshold selection、validation mining、future/PnL-as-rule-feature 均禁止。`simulated_executed_quantity` 仅允许作为 diagnostic replay accounting 字段。
