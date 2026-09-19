---
created_at: 2026-06-23T15:31:53+00:00
status: pass_ready_for_review
phase: ATPAL1_R_ACTION_CONTEXT_LEDGER_REPAIR
artifact_root: data_tw/experiments/action_trade_pnl_attribution_ledger/atpal1_r_action_context_ledger_repair
readonly_only: true
simulation_only: true
production_allowed: false
strict_test_used: false
---

# ATPAL1-R Action Context Ledger Repair 执行报告

## 1. Scope 与 Non-goals

本轮只执行 ATPAL1-R：修复 `action_context_ledger.csv` 的 pre-action portfolio state 与 trade ledger linkage。未进入 ATPAL2/3/4，未跑新策略，未选择规则或阈值，未使用 strict_test，未训练模型，未输出 OrderIntent/target/quantity_instruction/broker，未触碰 provider/latest/monitor/frontend/Agent/production。

## 2. 已读取文档和合同

- `docs/tw_portfolio_decision_model/POLICY_ATPAL_ACTION_TRADE_PNL_ATTRIBUTION_LEDGER_MAINLINE_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_ATPAL1_R_ACTION_CONTEXT_LEDGER_REPAIR_WORK_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_ATPAL1_BASELINE_LEDGER_BUILDER_REVIEW_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_ATPAL1_BASELINE_LEDGER_BUILDER_EXECUTION_REPORT_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_ATPAL1_BASELINE_LEDGER_BUILDER_WORK_CN.md`
- `data_tw/experiments/action_trade_pnl_attribution_ledger/atpal0_contract/field_dictionary.csv`
- `data_tw/experiments/action_trade_pnl_attribution_ledger/atpal0_contract/reconciliation_rule_contract.csv`
- `scripts/build_tw_policy_atpal1_baseline_ledger.py`
- `scripts/run_tw_policy_action_model_pa1.py`

## 3. 输出文件

输出目录：`data_tw/experiments/action_trade_pnl_attribution_ledger/atpal1_r_action_context_ledger_repair`

已输出 ATPAL1-R 要求的全套 ledger、reconciliation/audit、`action_context_linkage_audit.csv`、`action_context_pre_state_audit.csv`、validator 与 diagnostic findings。

## 4. Row Counts

| table | rows |
|---|---:|
| trade_level_pnl_ledger | 1321 |
| position_lifecycle_ledger | 670 |
| position_day_pnl_ledger | 6093 |
| symbol_date_pnl_ledger | 6744 |
| action_context_ledger | 1366 |
| cash_fee_tax_ledger | 723 |

## 5. Action Context Linkage Audit

```json
[
  {
    "audit_name": "action_context_trade_direct_linkage",
    "split": "train",
    "trade_action_count": 885,
    "context_executed_action_count": 885,
    "direct_linked_count": 885,
    "missing_context_count": 0,
    "orphan_context_count": 0,
    "orphan_non_executed_context_count": 31,
    "linkage_rate": 1.0,
    "status": "pass"
  },
  {
    "audit_name": "action_context_trade_direct_linkage",
    "split": "validation",
    "trade_action_count": 436,
    "context_executed_action_count": 436,
    "direct_linked_count": 436,
    "missing_context_count": 0,
    "orphan_context_count": 0,
    "orphan_non_executed_context_count": 14,
    "linkage_rate": 1.0,
    "status": "pass"
  }
]
```

## 6. Pre-state Audit

```json
[
  {
    "audit_name": "executed_sell_pre_action_state_coverage",
    "split": "train",
    "sell_context_count": 438,
    "sell_context_with_holding_days_before_positive": 397,
    "sell_context_with_unrealized_return_before_available": 438,
    "sell_holding_days_positive_rate": 0.9063926941,
    "sell_unrealized_return_available_rate": 1.0,
    "same_day_entry_exit_or_zero_day_count": 41,
    "status": "pass"
  },
  {
    "audit_name": "executed_sell_pre_action_state_coverage",
    "split": "validation",
    "sell_context_count": 213,
    "sell_context_with_holding_days_before_positive": 197,
    "sell_context_with_unrealized_return_before_available": 213,
    "sell_holding_days_positive_rate": 0.9248826291,
    "sell_unrealized_return_available_rate": 1.0,
    "same_day_entry_exit_or_zero_day_count": 16,
    "status": "pass"
  }
]
```

## 7. Reconciliation 摘要

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

## 8. Forbidden Field Audit 摘要

Forbidden failed rows：0

## 9. Validator 摘要

```json
{
  "ok": true,
  "status": "PASS_ATPAL1_R_ACTION_CONTEXT_LEDGER_REPAIR_READY_FOR_REVIEW",
  "phase": "ATPAL1_R_ACTION_CONTEXT_LEDGER_REPAIR",
  "failed_count": 0,
  "final_recommendation": "READY_FOR_REVIEWER_TO_CONSIDER_ATPAL2_WORK_DOC"
}
```
