---
created_at: 2026-06-23T15:48:45+00:00
status: pass_ready_for_review
phase: ATPAL2_CONTRIBUTION_CONCENTRATION_AUDIT
artifact_root: data_tw/experiments/action_trade_pnl_attribution_ledger/atpal2_contribution_audit
readonly_only: true
simulation_only: true
production_allowed: false
strict_test_used: false
---

# ATPAL2 Contribution / Concentration Audit 执行报告

## 1. Scope 与 Non-goals

本轮只执行 ATPAL2：基于 ATPAL1-R baseline ledger 生成 symbol/date/symbol-date、trade、position、fee、turnover contribution audit，并设计 future candidate concentration gate。未进入 ATPAL3/4，未跑新策略或 candidate replay，未选择规则或阈值，未使用 strict_test，未训练模型，未触碰生产链路。

## 2. 已读取文档和输入

- `docs/tw_portfolio_decision_model/POLICY_ATPAL_ACTION_TRADE_PNL_ATTRIBUTION_LEDGER_MAINLINE_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_ATPAL2_CONTRIBUTION_AUDIT_WORK_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_ATPAL1_R_ACTION_CONTEXT_LEDGER_REPAIR_REVIEW_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_ATPAL1_R_ACTION_CONTEXT_LEDGER_REPAIR_EXECUTION_REPORT_CN.md`
- `data_tw/experiments/action_trade_pnl_attribution_ledger/atpal1_r_action_context_ledger_repair/manifest.json`
- ATPAL1-R symbol_date/trade/position/cash/turnover/validator artifacts

## 3. 输出文件

输出目录：`data_tw/experiments/action_trade_pnl_attribution_ledger/atpal2_contribution_audit`

已输出工作文档要求的 12 个文件：manifest、8 张 audit/summary CSV、gate design、forbidden consumer audit、validator 与 diagnostic findings。

## 4. Top Contributor 摘要

```json
[
  {
    "split": "train",
    "top1_symbol_contribution_share": 0.0554565801,
    "top3_symbol_contribution_share": 0.1513068307,
    "top1_date_contribution_share": 0.0081998489,
    "top5_date_contribution_share": 0.0363180522,
    "top1_symbol_date_contribution_share": 0.0064477264,
    "top10_symbol_date_contribution_share": 0.0367614345,
    "positive_contribution_symbol_count": 68,
    "negative_contribution_symbol_count": 50,
    "contribution_hhi": 0.022049535
  },
  {
    "split": "validation",
    "top1_symbol_contribution_share": 0.0607301284,
    "top3_symbol_contribution_share": 0.1629622214,
    "top1_date_contribution_share": 0.01567772,
    "top5_date_contribution_share": 0.0738089117,
    "top1_symbol_date_contribution_share": 0.0108893715,
    "top10_symbol_date_contribution_share": 0.0723960962,
    "positive_contribution_symbol_count": 49,
    "negative_contribution_symbol_count": 39,
    "contribution_hhi": 0.0264257497
  },
  {
    "split": "all",
    "top1_symbol_contribution_share": 0.0487401147,
    "top3_symbol_contribution_share": 0.1318833533,
    "top1_date_contribution_share": 0.0062482844,
    "top5_date_contribution_share": 0.0276743536,
    "top1_symbol_date_contribution_share": 0.0049131671,
    "top10_symbol_date_contribution_share": 0.0293220093,
    "positive_contribution_symbol_count": 75,
    "negative_contribution_symbol_count": 53,
    "contribution_hhi": 0.018121517
  }
]
```

## 5. Distribution 摘要

Trade distribution：

```json
[
  {
    "split": "train",
    "trade_count": 885,
    "mean_realized_pnl_after_fee_tax": 2615.37,
    "median_realized_pnl_after_fee_tax": -281.22,
    "p10_realized_pnl_after_fee_tax": -8681.38,
    "p90_realized_pnl_after_fee_tax": 15485.57,
    "positive_trade_count": 247,
    "negative_trade_count": 638,
    "top_abs_trade_share": 0.0330275247
  },
  {
    "split": "validation",
    "trade_count": 436,
    "mean_realized_pnl_after_fee_tax": 1553.95,
    "median_realized_pnl_after_fee_tax": -143.24,
    "p10_realized_pnl_after_fee_tax": -5655.43,
    "p90_realized_pnl_after_fee_tax": 9929.17,
    "positive_trade_count": 119,
    "negative_trade_count": 317,
    "top_abs_trade_share": 0.0517860543
  },
  {
    "split": "all",
    "trade_count": 1321,
    "mean_realized_pnl_after_fee_tax": 2265.04,
    "median_realized_pnl_after_fee_tax": -190.67,
    "p10_realized_pnl_after_fee_tax": -7996.93,
    "p90_realized_pnl_after_fee_tax": 13330.97,
    "positive_trade_count": 366,
    "negative_trade_count": 955,
    "top_abs_trade_share": 0.0251583447
  }
]
```

Position lifecycle distribution：

```json
[
  {
    "split": "train",
    "position_lifecycle_count": 447,
    "closed_count": 438,
    "open_at_period_end_count": 9,
    "mean_net_pnl_after_fee_tax": 5411.31,
    "median_net_pnl_after_fee_tax": 1601.21,
    "p10_net_pnl_after_fee_tax": -18139.16,
    "p90_net_pnl_after_fee_tax": 31292.59,
    "top_abs_lifecycle_share": 0.0325961961
  },
  {
    "split": "validation",
    "position_lifecycle_count": 223,
    "closed_count": 213,
    "open_at_period_end_count": 10,
    "mean_net_pnl_after_fee_tax": 4276.98,
    "median_net_pnl_after_fee_tax": 1559.55,
    "p10_net_pnl_after_fee_tax": -10709.24,
    "p90_net_pnl_after_fee_tax": 18036.98,
    "top_abs_lifecycle_share": 0.0740920999
  },
  {
    "split": "all",
    "position_lifecycle_count": 670,
    "closed_count": 651,
    "open_at_period_end_count": 19,
    "mean_net_pnl_after_fee_tax": 5033.76,
    "median_net_pnl_after_fee_tax": 1568.46,
    "p10_net_pnl_after_fee_tax": -14836.7,
    "p90_net_pnl_after_fee_tax": 27386.37,
    "top_abs_lifecycle_share": 0.02427053
  }
]
```

## 6. Fee / Turnover 摘要

```json
[
  {
    "split": "train",
    "fee_tax_total": 549665.29,
    "gross_positive_contribution": 19234152.91,
    "gross_negative_contribution": -17023700.66,
    "fee_tax_share_of_total_abs_contribution": 0.015159896,
    "fee_tax_share_of_trade_notional": 0.0029240744
  },
  {
    "split": "validation",
    "fee_tax_total": 146214.73,
    "gross_positive_contribution": 6114402.21,
    "gross_negative_contribution": -5210233.0,
    "fee_tax_share_of_total_abs_contribution": 0.0129112085,
    "fee_tax_share_of_trade_notional": 0.0028996071
  },
  {
    "split": "all",
    "fee_tax_total": 695880.01,
    "gross_positive_contribution": 25348555.12,
    "gross_negative_contribution": -22233933.66,
    "fee_tax_share_of_total_abs_contribution": 0.0146247082,
    "fee_tax_share_of_trade_notional": 0.0029188992
  }
]
```

```json
[
  {
    "split": "train",
    "trade_notional_sum": 187979243.85,
    "average_equity": 2151516.17,
    "turnover_proxy": 87.37059304,
    "trade_count": 885,
    "buy_count": 447,
    "sell_count": 438,
    "top_symbol_turnover_share": 0.0348288403,
    "top_date_turnover_share": 0.0050173213
  },
  {
    "split": "validation",
    "trade_notional_sum": 50425702.49,
    "average_equity": 1195267.92,
    "turnover_proxy": 42.18778213,
    "trade_count": 436,
    "buy_count": 223,
    "sell_count": 213,
    "top_symbol_turnover_share": 0.032618764,
    "top_date_turnover_share": 0.011983695
  },
  {
    "split": "all",
    "trade_notional_sum": 238404946.34,
    "average_equity": "",
    "turnover_proxy": "",
    "trade_count": 1321,
    "buy_count": 670,
    "sell_count": 651,
    "top_symbol_turnover_share": 0.0291316012,
    "top_date_turnover_share": 0.0039560935
  }
]
```

## 7. Forbidden Consumer Audit

Forbidden consumer failed rows：0

## 8. Validator 摘要

```json
{
  "ok": true,
  "status": "PASS_ATPAL2_CONTRIBUTION_AUDIT_READY_FOR_REVIEW",
  "phase": "ATPAL2_CONTRIBUTION_CONCENTRATION_AUDIT",
  "failed_count": 0,
  "final_recommendation": "READY_FOR_REVIEWER_TO_CONSIDER_ATPAL3_WORK_DOC"
}
```
