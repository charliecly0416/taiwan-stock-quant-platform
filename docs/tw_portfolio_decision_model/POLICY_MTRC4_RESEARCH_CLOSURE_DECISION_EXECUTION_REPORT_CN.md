# MTRC4 Research Closure Decision Execution Report

## 1. Scope

- Assigned phase: `MTRC4_RESEARCH_CLOSURE_DECISION`
- Mainline document: `docs/tw_portfolio_decision_model/POLICY_MTRC_RESEARCH_ONLY_CONTINUATION_MAINLINE_CN.md`
- Work document: `docs/tw_portfolio_decision_model/POLICY_MTRC4_RESEARCH_CLOSURE_DECISION_WORK_CN.md`
- Decision: `KEEP_RESEARCH_ONLY_WITH_DATA_QUALITY_FOLLOWUP`
- Verdict: `PASS_MTRC_RESEARCH_ROUTE_CLOSED_WITH_OPTIONAL_DATA_QUALITY_FOLLOWUP`
- Non-goals confirmed: no new signal/order/replay/ledger, no training/inference, no strategy tuning, no production/default/latest/frontend/API/Agent/daily write.

## 2. Documents / Contracts / Skills Read

- `docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_MTRC_RESEARCH_ONLY_CONTINUATION_MAINLINE_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_MTRC4_RESEARCH_CLOSURE_DECISION_WORK_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_MTRC2_U_SAME_SIGNAL_READONLY_REPLAY_BUILD_REVIEW_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_MTRC3_EXTENDED_CONCENTRATION_WINDOW_DIAGNOSTIC_EXECUTION_REPORT_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_MTRC3_EXTENDED_CONCENTRATION_WINDOW_DIAGNOSTIC_REVIEW_CN.md`
- MTRC3 manifest/summary/mark-quality/concentration/validator artifacts
- Skills used: `coordinator-executor-reviewer-workflow`, `tw-stock-new-strategy-onboarding`

## 3. Changes Made

- Added builder: `scripts/build_tw_policy_mtrc4_research_closure_decision.py`
- Wrote research-only closure artifact directory: `data_tw/experiments/policy_mtr_research_only_continuation/mtrc4_research_closure_decision`
- Wrote this execution report: `docs/tw_portfolio_decision_model/POLICY_MTRC4_RESEARCH_CLOSURE_DECISION_EXECUTION_REPORT_CN.md`

No production registry, config, provider latest, frontend, API, Agent, daily-auto, broker, order, model, strategy, signal, replay, or ledger artifact was written.

## 4. Evidence Produced

Required output files:

```text
manifest.json
closure_decision.csv
evidence_summary.csv
production_blocker_register.csv
research_archive_register.csv
optional_followup_register.csv
forbidden_scope_audit.csv
validator_report.json
closure_findings.md
```

Core evidence:

```text
total_return = 2011.1302182622
max_drawdown = -0.1990237415
positive_month_ratio = 0.8288288288
rolling_20d_positive_ratio = 0.9055319149
rolling_40d_positive_ratio = 0.9238095238
top1_symbol_share = 0.0732851362
top3_symbol_share = 0.1641435559
top1_event_share = 0.0342442911
fallback_ratio = 0.8996056241
final_date_fallback_ratio = 0.9
max_mark_lag_days = 469
baseline_delta_allowed = False
```

## 5. Compliance With Mainline

MTRC4 only performs research-only closure. The route is not advanced to production readiness because mark quality fails and no legal same-signal baseline delta exists.

The concentration blocker is mitigated for research interpretation, but the mark-quality blocker remains production-critical.

## 6. Forbidden Actions Audit

`forbidden_scope_audit.csv` marks all forbidden scope items as pass/absent. The validator checks:

```json
{
  "mtrc3_review_passed": true,
  "decision_is_allowed": true,
  "required_output_files_present": true,
  "evidence_summary_contains_required_metrics": true,
  "production_blockers_include_mark_quality": true,
  "research_archive_register_complete": true,
  "optional_followups_are_not_authorized": true,
  "no_new_signal_order_replay_ledger": true,
  "no_model_training_or_inference": true,
  "no_strategy_tuning_or_candidate_selection": true,
  "no_provider_latest_default_frontend_api_agent_daily_write": true,
  "no_broker_order_target_weight_target_position": true,
  "production_allowed_false": true,
  "research_only_true": true,
  "forbidden_scope_audit_passed": true
}
```

## 7. Issues / Blockers / Deviations

Production blockers are intentionally retained:

- `mark_quality_fallback_ratio_fail`
- `final_date_mark_quality_fail`
- `max_mark_lag_days_fail`
- `no_legal_same_signal_baseline_delta`
- `absolute_return_not_production_evidence`
- `research_only_lineage_not_default_artifact`
- `no_frontend_api_agent_daily_default_authorization`

No deviations from the MTRC4 work document were made.

## 8. Files Changed

- `scripts/build_tw_policy_mtrc4_research_closure_decision.py`
- `docs/tw_portfolio_decision_model/POLICY_MTRC4_RESEARCH_CLOSURE_DECISION_EXECUTION_REPORT_CN.md`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc4_research_closure_decision/`

## 9. Validation

Ran:

```text
python -m py_compile scripts/build_tw_policy_mtrc4_research_closure_decision.py
python scripts/build_tw_policy_mtrc4_research_closure_decision.py
```

Validator verdict:

```text
PASS
blocking_reasons = []
```

## 10. Recommendation For Reviewer

Review should decide whether this can be accepted as:

```text
PASS_MTRC_RESEARCH_ROUTE_CLOSED_WITH_OPTIONAL_DATA_QUALITY_FOLLOWUP
```

Next work, if any, must be a separately authorized data-quality follow-up, not production readiness.
