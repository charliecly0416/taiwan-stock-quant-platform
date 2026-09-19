---
created_at: 2026-06-23T14:34:33+00:00
status: pass_ready_for_review
phase: ATPAL1_BASELINE_LEDGER_BUILDER
artifact_root: data_tw/experiments/action_trade_pnl_attribution_ledger/atpal1_baseline_ledger
readonly_only: true
simulation_only: true
production_allowed: false
strict_test_used: false
---

# ATPAL1 Baseline Ledger Builder 执行报告

## 1. Scope 与 Non-goals

本轮只执行 ATPAL1：基于可信 baseline replay 构建 train + validation 的 Action / Trade PnL Attribution Ledger。未进入 ATPAL2/3/4，未跑新策略，未选择规则或阈值，未使用 strict_test，未训练模型，未输出 OrderIntent/target/quantity_instruction/broker，未触碰 provider/latest/monitor/frontend/Agent/production。

## 2. 已读取文档和合同

- `docs/tw_portfolio_decision_model/POLICY_ATPAL_ACTION_TRADE_PNL_ATTRIBUTION_LEDGER_MAINLINE_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_ATPAL1_BASELINE_LEDGER_BUILDER_WORK_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_ATPAL0_SCHEMA_CONTRACT_REVIEW_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_ATPAL0_SCHEMA_CONTRACT_EXECUTION_REPORT_CN.md`
- `data_tw/experiments/action_trade_pnl_attribution_ledger/atpal0_contract/*`
- `scripts/run_tw_policy_action_model_pa1.py`
- `docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md`
- `docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md`

## 3. 输出文件

输出目录：`data_tw/experiments/action_trade_pnl_attribution_ledger/atpal1_baseline_ledger`

已输出 ATPAL1 要求的 manifest、source artifact manifest、六张 ledger、四张 audit/reconciliation、forbidden audit、validator report 与 diagnostic findings。

## 4. Ledger Row Counts

| table | rows |
|---|---:|
| trade_level_pnl_ledger | 1321 |
| position_lifecycle_ledger | 670 |
| position_day_pnl_ledger | 6093 |
| symbol_date_pnl_ledger | 6744 |
| action_context_ledger | 1366 |
| cash_fee_tax_ledger | 723 |

## 5. Reconciliation 摘要

baseline_summary_reconciliation failed rows：0

fee_tax_turnover_reconciliation_audit：

```json
[
  {
    "split": "train",
    "strategy_rule": "top50_exit_one_worst_sell",
    "candidate_id": "baseline",
    "trade_notional_sum": 187979243.85,
    "average_equity": 2151516.17,
    "ledger_turnover_proxy": 87.37059304,
    "replay_turnover_proxy": 87.37059302,
    "turnover_abs_diff": 2e-08,
    "ledger_fee_and_tax": 549665.29,
    "replay_fee_and_tax": 549665.29,
    "fee_tax_abs_diff": 0.0,
    "status": "pass"
  },
  {
    "split": "validation",
    "strategy_rule": "top50_exit_one_worst_sell",
    "candidate_id": "baseline",
    "trade_notional_sum": 50425702.49,
    "average_equity": 1195267.92,
    "ledger_turnover_proxy": 42.18778213,
    "replay_turnover_proxy": 42.18778217,
    "turnover_abs_diff": 4e-08,
    "ledger_fee_and_tax": 146214.73,
    "replay_fee_and_tax": 146214.73,
    "fee_tax_abs_diff": 0.0,
    "status": "pass"
  }
]
```

2025 validation replay summary：

```json
{
  "window": "validation",
  "model_name": "policy_supervised_utility_v1",
  "model_family": "supervised_utility_logistic_regression",
  "strategy_rule": "top50_exit_one_worst_sell",
  "start_date": "2025-01-02",
  "end_date": "2025-12-31",
  "initial_cash": 1000000.0,
  "final_equity": 1953767.53,
  "total_return": 0.95376753,
  "net_return_after_fee_tax": 0.95376753,
  "gross_return": 1.09998226,
  "max_drawdown": -0.34681374,
  "action_count": 436,
  "buy_count": 223,
  "sell_count": 213,
  "skip_count": 12,
  "skipped_action_count": 12,
  "turnover_proxy": 42.18778217,
  "fee_and_tax": 146214.73,
  "max_holding_count": 10,
  "duplicate_position_count": 0,
  "negative_cash_count": 0,
  "missing_price_count": 0,
  "diagnostic_only": true
}
```

## 6. Forbidden Field Audit 摘要

Forbidden failed rows：0

`simulated_executed_quantity` 与 `simulated_position_quantity` 仅作为 diagnostic accounting 字段输出；未输出 `quantity_instruction`、`target_weight`、`target_position`、broker/order/production 语义字段。

## 7. Validator 摘要

```json
{
  "ok": true,
  "status": "PASS_ATPAL1_BASELINE_LEDGER_READY_FOR_REVIEW",
  "phase": "ATPAL1_BASELINE_LEDGER_BUILDER",
  "failed_count": 0,
  "final_recommendation": "READY_FOR_REVIEWER_TO_CONSIDER_ATPAL2_WORK_DOC"
}
```

## 8. 下一步建议

若 reviewer 接受本轮 validator，可考虑 ATPAL2 工作文档；否则应先按 validator failed checks 修复 ATPAL1。
