---
created_at: 2026-06-23T17:09:52+00:00
status: pass_ready_for_review
phase: CATR1_CANDIDATE_ATPAL_REPLAY_BUILDER
artifact_root: data_tw/experiments/candidate_atpal_replay_feasibility/catr1_candidate_atpal_replay_builder
candidate_replay_run: true
candidate_pass_fail_judgement: false
strict_test_used: false
model_training_run: false
production_allowed: false
---

# CATR1 Candidate ATPAL Replay Builder 执行报告

## 1. Scope

本轮严格执行 CATR1：为既有 FPA4 candidates 生成 ATPAL-compatible candidate ledgers。

确认未执行：

```text
candidate pass/fail judgement
FPA4 repair
新增候选
调阈值
validation mining
strict_test
模型训练
生产/default/order/provider/frontend/Agent 集成
```

## 2. Documents / Contracts Read

已读取并遵守：

```text
docs/tw_portfolio_decision_model/POLICY_CATR_CANDIDATE_ATPAL_REPLAY_FEASIBILITY_MAINLINE_CN.md
docs/tw_portfolio_decision_model/POLICY_CATR0_CANDIDATE_REPLAY_FEASIBILITY_CONTRACT_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_CATR0_CANDIDATE_REPLAY_FEASIBILITY_CONTRACT_EXECUTION_REPORT_CN.md
docs/tw_portfolio_decision_model/POLICY_CATR1_CANDIDATE_ATPAL_REPLAY_BUILDER_WORK_CN.md
docs/tw_portfolio_decision_model/POLICY_ATPAL_ACTION_TRADE_PNL_ATTRIBUTION_LEDGER_MAINLINE_CN.md
docs/tw_portfolio_decision_model/POLICY_RAL_FPA4_PREDECLARED_FULL_PATH_RULE_SANITY_REVIEW_CN.md
data_tw/experiments/candidate_atpal_replay_feasibility/catr0_feasibility_contract/
data_tw/experiments/action_trade_pnl_attribution_ledger/atpal1_r_action_context_ledger_repair/
data_tw/experiments/action_trade_pnl_attribution_ledger/atpal2_contribution_audit/
data_tw/experiments/action_trade_pnl_attribution_ledger/atpal3_candidate_adapter_contract/
data_tw/experiments/full_path_action_diagnostic/fpa4_predeclared_full_path_rule_sanity/
scripts/build_tw_policy_ral_fpa4_predeclared_full_path_rule_sanity.py
scripts/run_tw_policy_action_model_pa1.py
```

## 3. Outputs

输出目录：

```text
data_tw/experiments/candidate_atpal_replay_feasibility/catr1_candidate_atpal_replay_builder
```

主要产物：

```text
manifest.json
source_artifact_manifest.json
candidate_replay_summary.csv
candidate_trade_level_pnl_ledger.csv
candidate_position_lifecycle_ledger.csv
candidate_position_day_pnl_ledger.csv
candidate_symbol_date_pnl_ledger.csv
candidate_action_context_ledger.csv
candidate_vs_baseline_delta_summary.csv
candidate_concentration_audit.csv
candidate_reconciliation_audit.csv
candidate_lineage_audit.csv
forbidden_consumer_audit.csv
validator_report.json
diagnostic_findings.md
```

## 4. Row Counts

```json
{
  "candidate_replay_summary": 14,
  "candidate_trade_level_pnl_ledger": 7249,
  "candidate_position_lifecycle_ledger": 3689,
  "candidate_position_day_pnl_ledger": 45438,
  "candidate_symbol_date_pnl_ledger": 48998,
  "candidate_action_context_ledger": 9691
}
```

## 5. Validator Summary

```json
{
  "ok": true,
  "status": "PASS_CATR1_CANDIDATE_ATPAL_LEDGERS_READY_FOR_REVIEW",
  "failed_count": 0,
  "final_recommendation": "READY_FOR_REVIEWER_TO_AUDIT_CANDIDATE_ATPAL_LEDGERS",
  "reconciliation_pass": true,
  "candidate_symbol_date_available": true
}
```

## 6. Final Recommendation

```text
READY_FOR_REVIEWER_TO_AUDIT_CANDIDATE_ATPAL_LEDGERS
```
