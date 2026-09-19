---
created_at: 2026-06-24T06:32:57+00:00
status: executed_rcpt0_r_candidate_hypothesis_consistency_repair
phase: RCPT0_R_CANDIDATE_HYPOTHESIS_CONSISTENCY_REPAIR
parent_phase: RCPT0_SCORE_RANK_REGIME_THRESHOLD_DISCOVERY
artifact_root: data_tw/experiments/risk_control_policy_2022/rcpt0_score_rank_regime_threshold_discovery
policy_replay_performed: false
risk_control_replay_performed: false
model_training_performed: false
strict_test_performed: false
production_chain_touched: false
order_chain_touched: false
---

# RCPT0-R Candidate Hypothesis Consistency Repair Execution Report

## 1. Scope
- Narrow repair only: candidate hypothesis / forbidden audit / validator / findings consistency.
- No policy replay, no risk-control replay, no training, no strict_test.
- No production/default/provider/frontend/Agent/order chain changes.

## 2. Files Repaired
- candidate_threshold_hypotheses.csv
- pit_safe_candidate_filter.csv
- diagnostic_findings.md
- validator_report.json
- forbidden_action_audit.csv

## 3. H01 Repair
- Before repair: H01 used condition `risk_off AND 0.4 <= raw_score < 0.8` but carried whole-risk_off statistics `sample_count=26028`, `mean_future_return_20d=-0.01810150`.
- After repair: H01 now matches `score_04_08_vs_08plus_audit.csv` with `sample_count=206`, `mean_future_return_5d=0.01473884`, `mean_future_return_20d=0.02341612`, `median_future_return_20d=0.01420901`, `win_rate_20d=0.51941748`.

## 4. Small-sample Candidate Downgrade
- H09 now carries `sample_count=9`, `min_sample_gate_status=insufficient`, `reference_only_due_to_n_lt_100=True`, `pit_safe_t1_possible=False`.
- `pit_safe_candidate_filter.csv` marks n<100 candidates as `reference_only_insufficient_sample`, `t1_authorizable_after_recheck=false`, and `threshold_can_be_written_as_predeclared_rule=false`.

## 5. Forbidden Audit Repair
- `entry_date_* / entry_open_* / exit_date_* / exit_close_*` are now classified as `label_construction_only`.
- These label-construction fields are marked `used_for_ranking=false`, `used_for_strategy_input=false`, `status=pass`.
- `future_return_*` and `future_return_label_available_*` remain diagnostic-only and are also excluded from ranking and strategy input.

## 6. Validator Repair
- `candidate_hypothesis_consistency_status=PASS`.
- Added explicit `candidate_hypothesis_source_surface_crosscheck` records for all hypotheses.
- `small_sample_hypothesis_status=PASS`.
- `forbidden_audit_consistency_status=PASS`.
- `recommended_next_step=PASS_READY_FOR_RCPT1_PIT_SAFE_ADAPTIVE_THRESHOLD_RULE_DESIGN_WORK_DOC`.

## 7. Scope Compliance
- No replay executed.
- No risk-control replay executed.
- No training executed.
- No strict_test executed.
- No production/default/provider/frontend/Agent/order chain files modified.

## 8. Implementation Note
- Repaired the RCPT0 artifact generator so regenerated outputs stay source-surface consistent instead of patching CSVs by hand.

## 9. Files Changed
- scripts/run_tw_policy_rcpt0_score_rank_regime_threshold_discovery.py
- docs/tw_portfolio_decision_model/POLICY_RCPT0_R_CANDIDATE_HYPOTHESIS_CONSISTENCY_REPAIR_EXECUTION_REPORT_CN.md
