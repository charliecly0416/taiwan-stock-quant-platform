# POLICY_JMD2_R_COST_AWARE_TURNOVER_REPAIR_EXECUTION_REPORT_CN

## 1. 范围

本次执行 JMD2-R cost-aware turnover repair。产物仅为 readonly research diagnostic artifact；未生成 OrderIntent，未输出目标仓位、数量、券商或真实订单指令，未接入 production/default/frontend/API/Agent/daily/provider/latest。

## 2. Lineage / Split

- input_source: `qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/normalized_nonempty`
- train: `2015-01-01..2020-12-31`
- validation: `2021-01-01..2021-12-31`
- read_policy: `stop_after_2021_12_31`
- repair_source: `jmd2_supervised_utility_ridge_seed11` prediction
- candidates: fixed predeclared R0-R4 only

## 3. Parity / Validator

- validator_status: `pass`
- r0_parity_status: `pass`
- no 2022 / 2023-2025 / LTR private artifacts used

## 4. Best Candidate

- best_policy_name: `jmd2_r2_max_replace_1`
- best_family: `R2_max_replacement`
- net_total_return_after_fee_tax: `0.351752`
- gross_total_return: `0.572294`
- average_turnover: `0.216116`
- max_drawdown: `-0.437932`
- original_jmd2_net: `-0.349629`
- liquidity_baseline_net: `0.418059`
- momentum_baseline_net: `0.559470`

## 5. Top Validation Results

| policy_name | family | net_total_return_after_fee_tax | gross_total_return | max_drawdown | average_turnover | average_holding_count | cash_no_selection_day_count |
| --- | --- | --- | --- | --- | --- | --- | --- |
| jmd2_r2_max_replace_1 | R2_max_replacement | 0.351752 | 0.572294 | -0.437932 | 0.216116 | 10.000000 | 0 |
| jmd2_r4_combo_D_top30_replace1_margin0020 | R4_combined | 0.336012 | 0.548572 | -0.437932 | 0.211157 | 10.000000 | 0 |
| jmd2_r4_combo_A_top30_replace1_margin0010 | R4_combined | 0.293455 | 0.499222 | -0.437932 | 0.211157 | 10.000000 | 0 |
| jmd2_r2_max_replace_3 | R2_max_replacement | 0.233163 | 0.895730 | -0.475065 | 0.611157 | 10.000000 | 0 |
| jmd2_r4_combo_B_top50_replace1_margin0010 | R4_combined | 0.231137 | 0.425205 | -0.415286 | 0.209091 | 10.000000 | 0 |
| jmd2_r1_hold_buffer_top50 | R1_hold_buffer | 0.155585 | 0.805366 | -0.416193 | 0.634711 | 10.000000 | 0 |
| jmd2_r4_combo_C_top30_replace2_margin0010 | R4_combined | 0.120876 | 0.480612 | -0.452714 | 0.396694 | 10.000000 | 0 |
| jmd2_r1_hold_buffer_top30 | R1_hold_buffer | 0.038102 | 0.852128 | -0.401437 | 0.822314 | 10.000000 | 0 |

## 6. 输出

- artifact_root: `data_tw/experiments/policy_jmd_joint_model_decision_research/jmd2_r_cost_aware_turnover_repair`
- `manifest.json`
- `repair_candidate_contract.csv`
- `repair_baseline_parity_audit.csv`
- `repair_validation_comparison.csv`
- `repair_turnover_cost_audit.csv`
- `repair_participation_audit.csv`
- `repair_holdings_overlap_audit.csv`
- `repair_rank_overlap_audit.csv`
- `repair_regime_attribution.csv`
- `repair_no_leakage_audit.csv`
- `repair_forbidden_action_audit.csv`
- `repaired_joint_decision_diagnostic_artifact.csv`
- `validator_report.json`

## 7. Verdict / Recommendation

- verdict: `PASS_REPAIR_MECHANISM_ONLY_NO_GO_TO_JMD3`
- recommendation: `DO_NOT_ENTER_JMD3_RL_OR_EXPAND_MODEL_UNTIL_FEATURE_EDGE_IS_REPAIRED`
