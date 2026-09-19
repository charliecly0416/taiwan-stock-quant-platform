---
created_at: 2026-06-23T16:21:04+00:00
status: pass_ready_for_review
phase: ATPAL4_FPA4_BACKFILL_DIAGNOSTIC
artifact_root: data_tw/experiments/action_trade_pnl_attribution_ledger/atpal4_fpa4_backfill_diagnostic
readonly_only: true
simulation_only: true
production_allowed: false
candidate_replay_run: false
strict_test_used: false
fpa4_conclusion_unchanged: true
---

# ATPAL4 FPA4 Backfill Diagnostic 执行报告

## 1. Scope 与 Non-goals

本轮只执行 ATPAL4 backfill diagnostic：基于既有 FPA4 失败候选、ATPAL1-R baseline ledger、ATPAL2 concentration audit 和 ATPAL3 adapter contract，输出 summary-level trade PnL attribution、symbol-date concentration gap diagnosis、delta component breakdown 和 failure attribution report。

未运行 candidate replay，未运行新策略 replay，未新增 candidate，未调阈值，未改变 FPA4 的 `STOP_NO_PREDECLARED_RULE_SANITY_PASS` 结论，未使用 strict_test，未训练模型，未触碰生产链路。

## 2. 已读取文档和输入

- `docs/tw_portfolio_decision_model/POLICY_ATPAL_ACTION_TRADE_PNL_ATTRIBUTION_LEDGER_MAINLINE_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_ATPAL4_FPA4_BACKFILL_DIAGNOSTIC_WORK_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_ATPAL3_CANDIDATE_REPLAY_ADAPTER_CONTRACT_REVIEW_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_RAL_FPA4_PREDECLARED_FULL_PATH_RULE_SANITY_EXECUTION_REPORT_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_RAL_FPA4_PREDECLARED_FULL_PATH_RULE_SANITY_REVIEW_CN.md`
- ATPAL1-R / ATPAL2 / ATPAL3 指定源产物
- FPA4 manifest、candidate manifest、summary、pass audit、rolling OOS、concentration audit、forbidden audit、validator

## 3. 输出文件

输出目录：`data_tw/experiments/action_trade_pnl_attribution_ledger/atpal4_fpa4_backfill_diagnostic`

- `manifest.json`
- `fpa4_candidate_trade_pnl_attribution.csv`
- `fpa4_candidate_symbol_date_concentration.csv`
- `fpa4_candidate_delta_component_breakdown.csv`
- `fpa4_failure_attribution_report.md`
- `forbidden_consumer_audit.csv`
- `validator_report.json`

## 4. Backfill 结果摘要

- FPA4 candidate/threshold 覆盖数：7
- trade PnL attribution rows：14
- symbol-date concentration gap rows：14
- delta component rows：196
- validation excess positive candidate rows：3
- validation excess non-positive candidate rows：4

当前 FPA4 没有 candidate trade-level ledger 或 candidate symbol-date ledger，因此本轮只做 summary-level attribution，并明确：

```text
candidate_symbol_date_available = false
candidate_symbol_date_backfill_status = unavailable_requires_candidate_atpal_replay
```

## 5. FPA4 结论

原始 FPA4 结论保持不变：

```text
STOP_NO_PREDECLARED_RULE_SANITY_PASS
```

## 6. Validator 摘要

```json
{
  "ok": true,
  "status": "PASS_ATPAL4_FPA4_BACKFILL_DIAGNOSTIC_READY_FOR_REVIEW",
  "phase": "ATPAL4_FPA4_BACKFILL_DIAGNOSTIC",
  "failed_count": 0,
  "final_recommendation": "READY_FOR_REVIEWER_TO_CLOSE_ATPAL_MAINLINE"
}
```

## 7. Forbidden Audit

Forbidden consumer failed rows：0
