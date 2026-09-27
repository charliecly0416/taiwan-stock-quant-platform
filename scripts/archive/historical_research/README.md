# Historical Research Scripts

This directory contains older TW-stock research and audit scripts that are no longer part of the active product chain. They were kept for traceability and method review, but should not be used as default production entrypoints.

Active production-facing scripts remain in `scripts/` root. Before restoring anything from this archive, re-check current data contracts, strict E4/YZ model scope, readonly boundaries, and frontend/API references.

Archived in this cleanup pass:

- `audit_extended_oos_qlib_orthogonal_ltr_phase_e1r.py`
- `audit_extended_oos_qlib_orthogonal_ltr_phase_e5_fairness.py`
- `audit_finmind_orthogonal_data_availability.py`
- `audit_fresh_top50_phasec3_asof_replay_ready.py`
- `audit_frozen_fresh_qlib_orthogonal_ltr_clean_phase_c0.py`
- `audit_orthogonal_ltr_phase_o1_pit_availability.py`
- `audit_phasea1_anchor_reproduction.py`
- `audit_phasep1_o4_vs_repaired_fresh_same_window.py`
- `build_frozen_fresh_qlib_orthogonal_ltr_clean_phase_c1_sample.py`
- `build_orthogonal_fresh_qlib_phase_q1_feature_join.py`
- `compare_e4_treatment_vs_fresh_qlib_2026_window.py`
- `compare_o4_ltr_vs_fresh_qlib_2026_window.py`
- `evaluate_frozen_fresh_qlib_orthogonal_ltr_clean_phase_c3_replay.py`
- `evaluate_orthogonal_fresh_qlib_phase_q3.py`
- `evaluate_tw_ltr_baseline_phaseb1_conservative_replay.py`
- `evaluate_tw_ltr_s1b6_full_daily_replay.py`
- `evaluate_tw_ltr_s1b6r_accounting_repair.py`
- `evaluate_tw_ltr_strategy_validation_phasev1_yearly_replay.py`
- `freeze_orthogonal_ltr_phase_o0_contract.py`
- `repair_fresh_top50_phasec4_replay_ready.py`
- `repair_orthogonal_ltr_phase_o1r_coverage_available_at.py`
- `repair_tw_ltr_s1b5r_baseline_readiness.py`
- `run_extended_oos_qlib_orthogonal_ltr_phase_e8_daily_readonly.py`
- `run_fresh_top50_coverage_repair_c0_c1.py`
- `train_frozen_fresh_qlib_orthogonal_ltr_clean_phase_c2.py`
- `train_orthogonal_fresh_qlib_phase_q2.py`
- `train_tw_ltr_s2b_fresh_qlib.py`
- `write_tw_ltr_s2e_fresh_retrain_conclusion.py`

Archived in second cleanup pass:

- `analyze_tw_decision_orthogonal_phase1b.py`
- `audit_extended_oos_qlib_orthogonal_ltr_phase_e0.py`
- `audit_extended_oos_qlib_orthogonal_ltr_phase_e8r_replay_rule_attribution.py`
- `audit_extended_oos_qlib_orthogonal_ltr_phase_e8s_one_sell_one_buy_repair.py`
- `audit_phasep3r_daily_chain_repair.py`
- `audit_phasep3rr_orthogonal_refresh.py`
- `audit_phasep3s_preopen_datetime_availability.py`
- `audit_tw_decision_fundamental_phasef0.py`
- `audit_tw_decision_orthogonal_phase0.py`
- `audit_tw_decision_orthogonal_phase0b.py`
- `audit_tw_decision_orthogonal_phase1b_asof_aware_repair.py`
- `audit_tw_decision_phase0.py`
- `audit_tw_ltr_phase0_contract.py`
- `backfill_tw_option_c_historical_signals.py`
- `build_p3rr_latest_orthogonal_features.py`
- `build_tw_decision_fundamental_phasef0b_monthly_revenue_poc.py`
- `build_tw_decision_orthogonal_phase0c_raw_archive.py`
- `build_tw_decision_orthogonal_phase0e_raw_archive.py`
- `build_tw_decision_orthogonal_phase1a_poc_samples.py`
- `build_tw_decision_phase1_samples.py`
- `build_tw_ltr_phase1_samples.py`
- `build_tw_ltr_s1b2_samples.py`
- `build_tw_ltr_s2c_fresh_samples.py`
- `confirm_tw_decision_entry_model_phase2c.py`
- `confirm_tw_decision_orthogonal_phase0d_pit_gate.py`
- `diagnose_tw_decision_entry_model_phase2b.py`
- `diagnose_tw_decision_fundamental_phasef0e_twse_coverage.py`
- `diagnose_tw_decision_orthogonal_phase1b_coverage.py`
- `diagnose_tw_decision_orthogonal_phase1b_formal_source.py`
- `diagnose_tw_ltr_phase1b_repair.py`
- `diagnose_tw_ltr_phase1c_final_repair.py`
- `diagnose_tw_ltr_phase2c_risk_off_only.py`
- `diagnose_tw_ltr_s1b5_score_diagnostics.py`
- `evaluate_orthogonal_ltr_phase_o5_controlled_replay.py`
- `evaluate_tw_ltr_phase2_regime_gating.py`
- `evaluate_tw_ltr_phase3a1_return_accounting_repair.py`
- `evaluate_tw_ltr_phase3a2_full_daily_replay.py`
- `evaluate_tw_ltr_phase3a_route_b_turnover_replay.py`
- `evaluate_tw_ltr_s2d_full_daily_replay.py`
- `freeze_tw_decision_orthogonal_phase2c_manual_rules.py`
- `generate_tw_ltr_s1b1_qlib_wf_scores.py`
- `materialize_tw_ltr_phase3a0_frozen_phase1c_scores.py`
- `probe_tw_decision_fundamental_phasef0c_official_disclosure.py`
- `probe_tw_decision_fundamental_phasef0d_official_access_repair.py`
- `recheck_tw_ltr_old_vs_fresh_same_window.py`
- `repair_orthogonal_ltr_phase_o5r_common_universe_audit.py`
- `repair_p3rrr_orthogonal_source_freshness.py`
- `repair_tw_ltr_phase2b_regime_gating.py`
- `repair_tw_ltr_strategy_phasev1_split_aware_audit.py`
- `run_extended_oos_qlib_orthogonal_ltr_phase_e6_bridge.py`
- `run_tw_decision_orthogonal_phase2_rules_baseline.py`
- `run_tw_decision_orthogonal_phase2b_rule_repair.py`
- `run_tw_ltr_p3_daily_rerank_readonly.py`
- `run_tw_rank_rotation_stress_replay.py`
- `scan_tw_ltr_phasev4_optional_sim_static_safety.py`
- `summarize_tw_decision_orthogonal_phase2d_closure.py`
- `train_orthogonal_ltr_phase_o4_controlled_treatment.py`
- `train_tw_decision_entry_model_v1.py`
- `train_tw_ltr_phase1_lambdamart.py`
- `train_tw_ltr_s1b4_common_model.py`
- `train_tw_ltr_s2c_fresh_model.py`
- `validate_tw_ltr_strategy_phasev2_comprehensive_stability.py`

## 2026-09-27 root cleanup

A third cleanup pass moved 172 unreferenced phase, dated, and one-off research scripts from
the `scripts/` root into
`root_recovered_20260927/`. The files were selected only after searching current configs,
runtime modules, tests, CI, and workflow code. They are not part of the daily update, unified
task entrypoint, readonly replay API, or frontend runtime.

The exact source list, SHA256 manifest, credential scan, and isolated restore verification are
kept outside the repository at:

`/home/chuliyang/taiwan-stock-quant-platform-backups/slimming-20260927-r1/`

The scan found only code that reads `FINMIND_TOKEN` from the environment; no literal credential
value was present. Do not run these scripts against current production assets without a new
contract and review.
