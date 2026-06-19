# Phase O0 执行报告：Anchor 与 Control 实验合同冻结

生成时间：2026-06-15T09:35:12+00:00

## 1. 执行结论

Phase O0 已完成：control 精确冻结为第一版 simple LTR / Phase1C anchor。本轮没有进入 O1，没有拉取正交数据，没有训练 qlib/LTR，没有回放新实验。

推荐 gate：

```text
phase_o0_anchor_and_control_contract_frozen
```

## 2. Control Identity

| field | expected | actual | pass |
| --- | --- | --- | --- |
| candidate_id | head10_all_l31_alpha0.7_top50_only | head10_all_l31_alpha0.7_top50_only | yes |
| model_id | head10_all_l31 | head10_all_l31 | yes |
| score_column | score_head10_all_l31_alpha0.7_top50_only | score_head10_all_l31_alpha0.7_top50_only | yes |
| blend_alpha | 0.7 | 0.7 | yes |
| preserve_scope | top50_only | top50_only | yes |
| label_col | relevance_10d_top_heavy | relevance_10d_top_heavy | yes |
| num_leaves | 31 | 31 | yes |
| learning_rate | 0.03 | 0.03 | yes |
| n_estimators | 120 | 120 | yes |
| random_state | 42 | 42 | yes |

## 3. Control Sample Audit

| metric | value |
| --- | --- |
| sample_raw_rows | 159993 |
| sample_complete_rows | 152249 |
| feature_complete_rows | 153739 |
| label_complete_10d_rows | 155387 |
| date_min | 2022-01-03 |
| date_max | 2026-06-12 |
| instrument_count | 150 |
| split_independent_test_rows | 31350 |
| split_out_of_split_or_incomplete_rows | 4630 |
| split_train_rows | 92717 |
| split_validation_rows | 31296 |

## 4. Score Reproduction

| metric_rows | max_abs_diff | mean_abs_diff | tolerance | pass |
| --- | --- | --- | --- | --- |
| 24 | 4.440892098500626e-16 | 4.192248400277284e-17 | 0.0007 | yes |

## 5. Anchor Replay Metrics 冻结

Full universe：

- fee_tax_adjusted_net_return：`0.721631`
- max_drawdown：`-0.05083`
- action_count：`405`

Common universe：

- common universe key count：`22474`
- fee_tax_adjusted_net_return：`0.641235`
- max_drawdown：`-0.076739`
- action_count：`405`

## 6. Control Artifact 清单

| path | role | exists | size_bytes |
| --- | --- | --- | --- |
| docs/tw_phase1c_anchor_reproduction/PHASEA2_REVIEW_AND_ANCHOR_CARD_CN.md | Phase A2 frozen anchor card | True | 5859 |
| docs/tw_phase1c_anchor_reproduction/PHASEA1_ANCHOR_REPRODUCTION_EXECUTION_REPORT_CN.md | Phase A1 reproduction report | True | 8484 |
| docs/tw_ltr_rerank_regime_turnover/PHASE1C_FINAL_LTR_REPAIR_EXECUTION_REPORT_CN.md | Phase1C final LTR repair report | True | 10000 |
| docs/tw_ltr_rerank_regime_turnover/PHASE3A0_FROZEN_PHASE1C_SCORE_EXECUTION_REPORT_CN.md | Phase3A0 frozen row-level score report | True | 6848 |
| docs/tw_ltr_qlib_split_aligned_retrain/PHASES2F_OLD_VS_FRESH_SAME_WINDOW_RECHECK_REPORT_CN.md | S2F same-window replay report | True | 3925 |
| data_tw/experiments/ltr_rerank_regime_turnover/phase1_ltr_baseline/phase1_ltr_samples.csv | first simple LTR control sample | True | 115730495 |
| data_tw/experiments/ltr_rerank_regime_turnover/phase1_ltr_baseline/phase1_sample_schema.json | first simple LTR sample schema | True | 1787 |
| data_tw/experiments/ltr_rerank_regime_turnover/phase1c_final_ltr_repair/phase1c_gate_summary.json | Phase1C gate summary | True | 835 |
| data_tw/experiments/ltr_rerank_regime_turnover/phase1c_final_ltr_repair/phase1c_validation_selection.csv | Phase1C validation selection | True | 28735 |
| data_tw/experiments/ltr_rerank_regime_turnover/phase1c_final_ltr_repair/phase1c_independent_test_comparison.csv | Phase1C independent test comparison | True | 2884 |
| data_tw/experiments/ltr_rerank_regime_turnover/phase3a0_frozen_phase1c_scores/phase3a0_score_schema.json | frozen Phase1C score schema | True | 2856 |
| data_tw/experiments/ltr_rerank_regime_turnover/phase3a0_frozen_phase1c_scores/phase3a0_frozen_phase1c_row_scores.csv | frozen Phase1C row-level score | True | 37234254 |
| data_tw/experiments/ltr_rerank_regime_turnover/phase3a0_frozen_phase1c_scores/phase3a0_score_reproduction_metrics.csv | score reproduction metrics | True | 2111 |
| data_tw/experiments/phase1c_anchor_reproduction/phasea1_anchor_summary.json | A1 anchor reproduction summary | True | 1693 |
| data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2f_old_vs_fresh_same_window_recheck/phase_s2f_same_window_metrics.csv | S2F full universe metrics | True | 1380 |
| data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2f_old_vs_fresh_same_window_recheck/phase_s2f_same_window_common_universe_metrics.csv | S2F common universe metrics | True | 1382 |
| data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2f_old_vs_fresh_same_window_recheck/phase_s2f_same_window_action_audit.csv | S2F action audit | True | 172409 |

## 7. Control Script 清单

| path | role | exists | size_bytes |
| --- | --- | --- | --- |
| scripts/build_tw_ltr_phase1_samples.py | control sample construction script | True | 19990 |
| scripts/train_tw_ltr_phase1_lambdamart.py | first LTR training script | True | 19398 |
| scripts/diagnose_tw_ltr_phase1c_final_repair.py | Phase1C candidate/model selection diagnosis script | True | 19521 |
| scripts/materialize_tw_ltr_phase3a0_frozen_phase1c_scores.py | frozen row-level score materialization script | True | 22415 |
| scripts/recheck_tw_ltr_old_vs_fresh_same_window.py | same-window replay/check script | True | 14489 |
| scripts/evaluate_tw_ltr_s2d_full_daily_replay.py | next-day replay engine reused by S2F | True | 38687 |

## 8. 本轮禁止变化清单

| item | status |
| --- | --- |
| do_not_retrain_qlib_in_o0 | frozen_forbidden |
| do_not_train_ltr_in_o0 | frozen_forbidden |
| do_not_enter_o1 | frozen_forbidden |
| do_not_fetch_finmind_in_o0 | frozen_forbidden |
| do_not_change_control_sample_rows | frozen_forbidden |
| do_not_change_label_col | frozen_forbidden |
| do_not_change_original_features | frozen_forbidden |
| do_not_change_ltr_model_type_or_hyperparameters | frozen_forbidden |
| do_not_change_top50_preserve_scope | frozen_forbidden |
| do_not_change_replay_fee_tax_next_day_position_count | frozen_forbidden |
| do_not_add_filters_thresholds_market_gates_turnover_rules | frozen_forbidden |
| do_not_delete_rows_for_missing_orthogonal_features | frozen_forbidden |
| do_not_modify_frontend_api_provider_accepted_latest_monitor_trading | frozen_forbidden |
| do_not_use_return_metrics_to_select_o0_contract | frozen_forbidden |

## 9. O1 前置合同

O1 只可在审查通过后执行 FinMind/PIT 可得性审计。Treatment 唯一允许变化是新增 PIT-safe 法人筹码与融资融券正交特征；不得改变 control 样本行、标签、原有特征、模型类型、超参数、top50 preserve_scope、回放规则或费用税费。

## 10. 安全边界

- 未进入 O1。
- 未训练 qlib/LTR。
- 未联网或拉取 FinMind。
- 未改前端/API。
- 未触发 provider / accepted latest / monitor / broker / orders / quick-trade。
- 未使用收益率选择或改变合同。

## 11. 输出产物

- `data_tw/experiments/ltr_orthogonal_features_controlled/phase_o0_contract_freeze/phaseo0_control_identity_audit.csv`
- `data_tw/experiments/ltr_orthogonal_features_controlled/phase_o0_contract_freeze/phaseo0_control_sample_audit.csv`
- `data_tw/experiments/ltr_orthogonal_features_controlled/phase_o0_contract_freeze/phaseo0_control_artifact_inventory.csv`
- `data_tw/experiments/ltr_orthogonal_features_controlled/phase_o0_contract_freeze/phaseo0_control_script_inventory.csv`
- `data_tw/experiments/ltr_orthogonal_features_controlled/phase_o0_contract_freeze/phaseo0_forbidden_change_checklist.csv`
- `data_tw/experiments/ltr_orthogonal_features_controlled/phase_o0_contract_freeze/phaseo0_experiment_contract.json`
