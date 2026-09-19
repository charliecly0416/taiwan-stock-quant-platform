# POLICY_MTR4_READINESS_DESIGN_AND_EXTENDED_EVIDENCE_CONTRACT_EXECUTION_REPORT_CN

生成日期：2026-06-28

## 1. Verdict

```text
PASS_READY_FOR_MTR5_EXTENDED_EVIDENCE
```

MTR4 已生成 readiness / extended evidence contract package。该结论只允许进入 `MTR5_EXTENDED_OOS_SHADOW_AND_PRODUCTION_READINESS_DIAGNOSTIC`，不允许生产化、不允许切默认、不允许 provider/latest/frontend/API/Agent/daily 改动。

## 2. Scope

- readonly_only: `true`
- simulation_only: `true`
- production_allowed: `false`
- model_training_performed: `false`
- strategy_tuning_performed: `false`
- replay_performed: `false`
- source_verdict: `PASS_MTR3_WITH_CONCENTRATION_OR_WINDOW_RISK`
- fixed_candidate: `M2_hold_rank_buffer_100`
- baseline: `baseline_top50_exit_one_worst_sell`
- input_mtr3_manifest: `data_tw/experiments/policy_mtr_mechanism_transfer/mtr3_robustness_window_regime_and_mechanism_attribution/manifest.json`

## 3. Inputs Read

- `docs/tw_portfolio_decision_model/POLICY_MTR4_READINESS_DESIGN_AND_EXTENDED_EVIDENCE_CONTRACT_WORK_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_MTR_MECHANISM_TRANSFER_TO_BASELINE_MAINLINE_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_MTR2_R_BROAD_FULL_RANK_VISIBILITY_REPAIR_REVIEW_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_MTR3_ROBUSTNESS_WINDOW_REGIME_AND_MECHANISM_ATTRIBUTION_REVIEW_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_MTR3_ROBUSTNESS_WINDOW_REGIME_AND_MECHANISM_ATTRIBUTION_EXECUTION_REPORT_CN.md`
- `data_tw/experiments/policy_mtr_mechanism_transfer/mtr3_robustness_window_regime_and_mechanism_attribution/manifest.json`
- `docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md`
- `docs/tw_modular_contracts/STRATEGY_RULE_CONTRACT_CN.md`
- `docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md`
- `docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md`
- `docs/tw_modular_contracts/NEW_STRATEGY_REVIEWER_CHECKLIST_CN.md`

## 4. Generated Artifacts

- `data_tw/experiments/policy_mtr_mechanism_transfer/mtr4_readiness_design_and_extended_evidence_contract/manifest.json`
- `data_tw/experiments/policy_mtr_mechanism_transfer/mtr4_readiness_design_and_extended_evidence_contract/readiness_gate_contract.csv`
- `data_tw/experiments/policy_mtr_mechanism_transfer/mtr4_readiness_design_and_extended_evidence_contract/extended_evidence_contract.csv`
- `data_tw/experiments/policy_mtr_mechanism_transfer/mtr4_readiness_design_and_extended_evidence_contract/broad_full_rank_visibility_contract.csv`
- `data_tw/experiments/policy_mtr_mechanism_transfer/mtr4_readiness_design_and_extended_evidence_contract/non_top50_buy_validator_contract.csv`
- `data_tw/experiments/policy_mtr_mechanism_transfer/mtr4_readiness_design_and_extended_evidence_contract/window_regime_gate_contract.csv`
- `data_tw/experiments/policy_mtr_mechanism_transfer/mtr4_readiness_design_and_extended_evidence_contract/concentration_risk_contract.csv`
- `data_tw/experiments/policy_mtr_mechanism_transfer/mtr4_readiness_design_and_extended_evidence_contract/production_boundary_contract.csv`
- `data_tw/experiments/policy_mtr_mechanism_transfer/mtr4_readiness_design_and_extended_evidence_contract/mtr5_work_recommendation.md`
- `data_tw/experiments/policy_mtr_mechanism_transfer/mtr4_readiness_design_and_extended_evidence_contract/forbidden_scope_audit.csv`
- `data_tw/experiments/policy_mtr_mechanism_transfer/mtr4_readiness_design_and_extended_evidence_contract/validator_report.json`
- `data_tw/experiments/policy_mtr_mechanism_transfer/mtr4_readiness_design_and_extended_evidence_contract/diagnostic_findings.md`

## 5. Contract Decisions

- broad full-rank visibility remains research-only / diagnostic-only.
- `candidate_rank` / `full_qlib_rank` are qlib base ranks.
- `buy_score` is LTR rerank score only inside qlib top50.
- non-top50 rows are allowed only for hold/sell visibility.
- any buy intent with missing, nonnumeric, or `candidate_rank > 50` is hard fail.
- MTR5 must include same-window, rolling, monthly, regime, drawdown, turnover/fee/tax, concentration, and lineage/shadow evidence.

## 6. MTR3 Risks Mapped

- monthly_positive_delta: `3/5`; negative months `2026-02`, `2026-05`.
- rolling_20d_negative_slice_count: `1`.
- risk_off_delta: `+0.01063245`; still requires MTR5 recheck because the advantage is small.
- top1_symbol_share: `0.631760` -> warn.
- top3_symbol_share: `0.972756` -> fail_or_research_only_pending_extended_evidence.
- top1_event_share: `0.300709` -> warn.

## 7. Validator Summary

```json
{
  "artifact_complete": true,
  "all_required_contracts_present": true,
  "readiness_gate_complete": true,
  "mtr3_risks_mapped_to_gates": true,
  "non_top50_buy_hard_fail_defined": true,
  "production_no_go_explicit": true,
  "forbidden_scope_clean": true,
  "mtr5_next_step_defined": true,
  "extended_evidence_contract_complete": true,
  "broad_full_rank_visibility_contract_complete": true
}
```

## 8. Safety Boundary

MTR4 did not run new收益 replay, did not modify strategy/model/default/production/provider/latest/frontend/API/Agent/daily, did not train/tune, did not add candidates, and did not rewrite MTR2_R or MTR3 artifacts.

## 9. Verification Commands

```bash
python -m py_compile scripts/build_tw_policy_mtr4_readiness_design_and_extended_evidence_contract.py
python scripts/build_tw_policy_mtr4_readiness_design_and_extended_evidence_contract.py
```
