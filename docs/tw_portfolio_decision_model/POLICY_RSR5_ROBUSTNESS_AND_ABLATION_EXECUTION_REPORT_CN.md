# Execution Report

## 1. Scope
- Assigned phase: POLICY_RSR5_ROBUSTNESS_AND_ABLATION
- Mainline document: docs/tw_portfolio_decision_model/POLICY_RSR_SCORE_RANK_REGIME_RULE_RESEARCH_MAINLINE_CN.md
- Work document: docs/tw_portfolio_decision_model/POLICY_RSR5_ROBUSTNESS_AND_ABLATION_WORK_CN.md
- Non-goals confirmed: no training/retraining, no qlib refresh, no LTR adaptation, no threshold tuning, no rejected-rule repair, no provider/latest/default/frontend/daily/publish, no broker/quick-trade/real order, no target_position/target_weight/allocation_weight/quantity instruction.

RSR5 only evaluated `rsr2_rank_deterioration_sell_gate_v1`. The four RSR4 rejected rules were boundary-audited as excluded and were not used in robustness, ablation, candidate statistics, or candidate promotion.

## 2. Documents / Contracts / Skills Read
```text
/home/chuliyang/.agents/skills/coordinator-executor-reviewer-workflow/SKILL.md
/home/chuliyang/taiwan-stock-quant-platform/.agents/skills/tw-stock-new-strategy-onboarding/SKILL.md
docs/tw_portfolio_decision_model/POLICY_RSR_SCORE_RANK_REGIME_RULE_RESEARCH_MAINLINE_CN.md
docs/tw_portfolio_decision_model/POLICY_RSR5_ROBUSTNESS_AND_ABLATION_WORK_CN.md
docs/tw_portfolio_decision_model/POLICY_RSR4_PREDECLARED_READONLY_REPLAY_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_RSR2_PREDECLARED_RULE_CONTRACT_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_RSR3_ORDER_INTENT_BUILDER_AND_PARITY_SMOKE_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_RSR4_PREDECLARED_READONLY_REPLAY_WORK_CN.md
docs/tw_portfolio_decision_model/POLICY_RSR4_PREDECLARED_READONLY_REPLAY_EXECUTION_REPORT_CN.md
docs/tw_modular_contracts/STRATEGY_RULE_CONTRACT_CN.md
docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md
docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md
docs/tw_modular_contracts/TW_NEW_STRATEGY_ONBOARDING_TEMPLATE_CN.md
docs/tw_modular_contracts/NEW_STRATEGY_REVIEWER_CHECKLIST_CN.md
```

## 3. Changes Made
- Added RSR5 builder: `scripts/build_tw_policy_rsr5_robustness_and_ablation.py`.
- Generated artifact root: `data_tw/experiments/policy_rsr_score_rank_regime_rule_research/rsr5_robustness_and_ablation`.
- Wrote this execution report: `docs/tw_portfolio_decision_model/POLICY_RSR5_ROBUSTNESS_AND_ABLATION_EXECUTION_REPORT_CN.md`.

## 4. Evidence Produced
- Artifacts:
```text
manifest.json
input_manifest_links.json
candidate_boundary_audit.csv
window_robustness_summary.csv
ablation_matrix.csv
parameter_neighborhood_stability.csv
action_level_attribution.csv
market_regime_ablation.csv
transaction_cost_sensitivity.csv
cash_no_trade_recheck.csv
baseline_clone_recheck.csv
missing_price_audit.csv
pit_leakage_audit.csv
forbidden_field_audit.csv
forbidden_action_audit.csv
```
- Logs / validator output:
```text
python -m py_compile scripts/build_tw_policy_rsr5_robustness_and_ablation.py
python scripts/build_tw_policy_rsr5_robustness_and_ablation.py --json
```
- Screenshots: not applicable; no UI work.

## 5. Compliance With Mainline
- 2021 sanity: `unavailable_lineage_start_after_window`; blocked because qlib-only signal and comparable baseline lineage start at `2023-01-03` / `2023-01-03`.
- 2022 downturn diagnostic: `unavailable_lineage_start_after_window` and explicitly `downturn_diagnostic_not_strict_oos`; no strict-OOS claim made.
- 2023-2025 qlib-only strict candidate re-check: net return `1.98685891`, max drawdown `-0.37160781`, action count `1053` from the RSR4 OrderIntent -> ReplayResult chain.
- Action attribution sell subtype counts: `{'top50_exit_sell': 522}`; refill buys `531`; fee/tax drag `659712.96`.
- Mechanism support status: `weak_or_not_supported_by_action_attribution`. Distinct `rank_3d_5d_deteriorated_without_score_support` sells = `0`; observed sell executions are attributable to top50 exit in this RSR5 join.
- Parameter neighborhood rows are diagnostic-only, all perturbations have `not_candidate=true`, no replay rerun, and no best-threshold selection.

## 6. Forbidden Actions Audit
- Clean: no real trading, no broker/quick-trade, no default strategy change, no provider publish, no accepted latest switch, no frontend/daily change, no model training or qlib refresh.
- Clean: no target_position, target_weight, allocation_weight, quantity instruction emitted by OrderIntent or RSR5 artifacts.
- Clean: no threshold/rule change and no post-hoc threshold selection.

## 7. Issues / Blockers / Deviations
- 2021 sanity and 2022 downturn diagnostics are unavailable under current qlib-only-compatible lineage. RSR5 records this as a lineage blocker instead of pulling data, refreshing qlib, or relabeling the windows.
- RSR5 therefore cannot claim full multi-window pass. It can only say the existing 2023-2025 qlib-only strict re-check remains credible under the produced diagnostics.
- Action attribution does not support a distinct rank-deterioration-without-score-support sell mechanism in the executed actions: all 522 sell executions classify as top50 exit under the PIT feature join. This weakens the RSR5 mechanism case and should be treated as a reviewer finding, not hidden behind the positive net return.
- Transaction cost stress remains net-positive versus the comparable baseline in the diagnostic stress rows, but turnover is still materially high and should remain a reviewer focus.

## 8. Files Changed
- `scripts/build_tw_policy_rsr5_robustness_and_ablation.py`
- `data_tw/experiments/policy_rsr_score_rank_regime_rule_research/rsr5_robustness_and_ablation/`
- `docs/tw_portfolio_decision_model/POLICY_RSR5_ROBUSTNESS_AND_ABLATION_EXECUTION_REPORT_CN.md`

## 9. Recommendation For Reviewer
Recommend `PASS_WITH_CONDITIONS` only if the reviewer accepts both the 2021/2022 lineage unavailability and the weak distinct rank-deterioration mechanism attribution. A stricter reviewer can reasonably close or fail the candidate despite the 2023-2025 net result. Do not promote to production/default/latest/publish. The candidate remains historical readonly research only and should proceed, if at all, to RSR6 closure with these limitations explicit.
