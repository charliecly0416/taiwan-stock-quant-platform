
# POLICY_MTR5_EXTENDED_OOS_SHADOW_AND_PRODUCTION_READINESS_DIAGNOSTIC_EXECUTION_REPORT_CN

生成日期：2026-06-28

## 1. Verdict

```text
KEEP_RESEARCH_ONLY
```

原因：

- top3_symbol_share remains fail_or_research_only and no clean extended lineage exists

## 2. Scope

- readonly_only: `true`
- simulation_only: `true`
- production_allowed: `false`
- replay_performed: `false`
- model_training_performed: `false`
- strategy_tuning_performed: `false`
- new_candidate_added: `false`
- fixed_candidate: `M2_hold_rank_buffer_100`
- baseline: `baseline_top50_exit_one_worst_sell`
- input_mtr2_r_dir: `data_tw/experiments/policy_mtr_mechanism_transfer/mtr2_r_broad_full_rank_visibility_repair`
- input_mtr3_dir: `data_tw/experiments/policy_mtr_mechanism_transfer/mtr3_robustness_window_regime_and_mechanism_attribution`
- input_mtr4_dir: `data_tw/experiments/policy_mtr_mechanism_transfer/mtr4_readiness_design_and_extended_evidence_contract`

## 3. Diagnostics Summary

| gate | value |
| --- | --- |
| same_window_status | `pass` |
| rolling_20d_positive_ratio | `0.966667` |
| rolling_40d_positive_ratio | `1.0` |
| monthly_positive_ratio | `0.6` |
| negative_months | `['2026-02', '2026-05']` |
| risk_off_net_delta | `0.01063245` |
| drawdown_segment_delta | `0.03056198` |
| turnover_fee_tax_pass | `True` |
| top1_symbol_share | `0.63176` |
| top3_symbol_share | `0.972755` |
| top1_event_share | `0.300709` |
| non_top50_validator_ok | `True` |
| clean_extended_lineage_found | `False` |

## 4. Safety Boundary

本次 MTR5 未训练、未调参、未新增候选、未修改 M2、未重跑 MTR2_R replay、未修改 MTR2_R/MTR3/MTR4 输入 artifacts。未修改 production/default/frontend/API/Agent/daily/provider/latest，未 provider publish，未 accepted latest switch，未 broker/quick-trade/real order，未输出 target_weight/target_position/quantity instruction。

## 5. Generated Artifacts

- `data_tw/experiments/policy_mtr_mechanism_transfer/mtr5_extended_oos_shadow_and_production_readiness_diagnostic/manifest.json`
- `data_tw/experiments/policy_mtr_mechanism_transfer/mtr5_extended_oos_shadow_and_production_readiness_diagnostic/same_window_replay_confirmation.csv`
- `data_tw/experiments/policy_mtr_mechanism_transfer/mtr5_extended_oos_shadow_and_production_readiness_diagnostic/daily_rolling_window_attribution.csv`
- `data_tw/experiments/policy_mtr_mechanism_transfer/mtr5_extended_oos_shadow_and_production_readiness_diagnostic/monthly_negative_inventory.csv`
- `data_tw/experiments/policy_mtr_mechanism_transfer/mtr5_extended_oos_shadow_and_production_readiness_diagnostic/regime_attribution_summary.csv`
- `data_tw/experiments/policy_mtr_mechanism_transfer/mtr5_extended_oos_shadow_and_production_readiness_diagnostic/drawdown_segment_attribution.csv`
- `data_tw/experiments/policy_mtr_mechanism_transfer/mtr5_extended_oos_shadow_and_production_readiness_diagnostic/turnover_fee_tax_decomposition.csv`
- `data_tw/experiments/policy_mtr_mechanism_transfer/mtr5_extended_oos_shadow_and_production_readiness_diagnostic/symbol_concentration_gate.csv`
- `data_tw/experiments/policy_mtr_mechanism_transfer/mtr5_extended_oos_shadow_and_production_readiness_diagnostic/event_concentration_gate.csv`
- `data_tw/experiments/policy_mtr_mechanism_transfer/mtr5_extended_oos_shadow_and_production_readiness_diagnostic/non_top50_buy_validator_report.json`
- `data_tw/experiments/policy_mtr_mechanism_transfer/mtr5_extended_oos_shadow_and_production_readiness_diagnostic/extended_lineage_inventory.csv`
- `data_tw/experiments/policy_mtr_mechanism_transfer/mtr5_extended_oos_shadow_and_production_readiness_diagnostic/data_lineage_blocker.md`
- `data_tw/experiments/policy_mtr_mechanism_transfer/mtr5_extended_oos_shadow_and_production_readiness_diagnostic/forbidden_scope_audit.csv`
- `data_tw/experiments/policy_mtr_mechanism_transfer/mtr5_extended_oos_shadow_and_production_readiness_diagnostic/validator_report.json`
- `data_tw/experiments/policy_mtr_mechanism_transfer/mtr5_extended_oos_shadow_and_production_readiness_diagnostic/diagnostic_findings.md`

## 6. Verification Commands

```bash
python -m py_compile scripts/build_tw_policy_mtr5_extended_oos_shadow_diagnostic.py
python scripts/build_tw_policy_mtr5_extended_oos_shadow_diagnostic.py
```
