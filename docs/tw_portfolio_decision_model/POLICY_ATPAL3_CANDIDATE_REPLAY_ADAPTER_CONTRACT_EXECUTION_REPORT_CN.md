---
created_at: 2026-06-23T16:09:50+00:00
status: pass_ready_for_review
phase: ATPAL3_CANDIDATE_REPLAY_ADAPTER_CONTRACT
artifact_root: data_tw/experiments/action_trade_pnl_attribution_ledger/atpal3_candidate_adapter_contract
readonly_only: true
simulation_only: true
production_allowed: false
candidate_replay_run: false
strict_test_used: false
---

# ATPAL3 Candidate Replay Adapter Contract 执行报告

## 1. Scope 与 Non-goals

本轮只执行 ATPAL3 contract：定义未来 candidate replay 如何接入 ATPAL ledger，以及 candidate_id mapping、candidate-vs-baseline delta、candidate concentration gate 和 required candidate replay fields。未运行 candidate replay，未产出 candidate performance result，未判断候选策略通过，未选择规则或阈值，未使用 strict_test，未训练模型，未触碰生产链路。

## 2. 已读取文档和输入

- `docs/tw_portfolio_decision_model/POLICY_ATPAL_ACTION_TRADE_PNL_ATTRIBUTION_LEDGER_MAINLINE_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_ATPAL3_CANDIDATE_REPLAY_ADAPTER_CONTRACT_WORK_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_ATPAL2_CONTRIBUTION_AUDIT_REVIEW_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_ATPAL2_CONTRIBUTION_AUDIT_EXECUTION_REPORT_CN.md`
- ATPAL0 schema/table/field contract
- ATPAL1-R manifest and validator
- ATPAL2 manifest, top contributor audit, gate design and validator

## 3. 输出文件

输出目录：`data_tw/experiments/action_trade_pnl_attribution_ledger/atpal3_candidate_adapter_contract`

已输出：

- `manifest.json`
- `candidate_replay_adapter_contract.md`
- `candidate_id_mapping_contract.csv`
- `candidate_vs_baseline_delta_contract.csv`
- `candidate_concentration_gate_contract.csv`
- `required_candidate_replay_fields.csv`
- `forbidden_consumer_audit.csv`
- `validator_report.json`

## 4. Contract 摘要

- candidate replay 将来必须复用 ATPAL1 四层账本结构。
- candidate ledger 必须可用 split/date/instrument/action_trace_id/candidate_id 与 baseline 对齐。
- PnL 字段只允许作为 attribution label，不得作为 rule feature。
- `simulated_executed_quantity` 只允许作为 diagnostic replay accounting，不得作为 instruction。
- candidate concentration gate 只能复用 ATPAL2 metrics；ATPAL3 不允许 pass/fail 或 threshold selection。
- candidate 结果不得绕过 rolling OOS。

## 5. Validator 摘要

```json
{
  "ok": true,
  "status": "PASS_ATPAL3_CANDIDATE_REPLAY_ADAPTER_CONTRACT_READY_FOR_REVIEW",
  "phase": "ATPAL3_CANDIDATE_REPLAY_ADAPTER_CONTRACT",
  "failed_count": 0,
  "final_recommendation": "READY_FOR_REVIEWER_TO_CONSIDER_ATPAL4_WORK_DOC"
}
```

## 6. Forbidden Audit

Forbidden consumer failed rows：0
