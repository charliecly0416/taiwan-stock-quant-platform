# POLICY_MTRC1D_RESEARCH_ONLY_BROAD_FULL_RANK_SIGNAL_BUILD_EXECUTION_REPORT_CN

生成时间：2026-06-28T14:43:10+00:00

## 1. 范围

本阶段只执行 `MTRC1D_RESEARCH_ONLY_BROAD_FULL_RANK_SIGNAL_BUILD`：基于 MTRC1B top50 LTR signal 与 MTRC1C broad bridge contract，生成 research-only broad full-rank `ModelSignalArtifact`。

未训练、未调参、未模型 inference、未重新计算 LTR score、未新增策略候选、未修改 `M2_hold_rank_buffer_100`、未生成 OrderIntent/ReplayResult、未跑收益 replay、未修改 production/default/latest/provider/frontend/API/Agent/daily/config registry。

## 2. 读取文件

- `docs/tw_portfolio_decision_model/POLICY_MTRC1D_RESEARCH_ONLY_BROAD_FULL_RANK_SIGNAL_BUILD_WORK_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_MTRC_RESEARCH_ONLY_CONTINUATION_MAINLINE_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_MTRC1B_RESEARCH_ONLY_EXTENDED_TOP50_LTR_SIGNAL_BUILD_REVIEW_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_MTRC1C_RESEARCH_ONLY_BROAD_BRIDGE_CONTRACT_WORK_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_MTRC1C_RESEARCH_ONLY_BROAD_BRIDGE_CONTRACT_EXECUTION_REPORT_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_MTRC1C_RESEARCH_ONLY_BROAD_BRIDGE_CONTRACT_REVIEW_CN.md`
- `docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md`
- `docs/tw_modular_contracts/NEW_MODEL_AND_STRATEGY_DEVELOPER_GUIDE_CN.md`
- `docs/tw_modular_contracts/MODEL_SIGNAL_CONTRACT_CN.md`
- `docs/tw_modular_contracts/MODEL_SIGNAL_EXTENSION_SCHEMA_CN.md`
- `docs/tw_modular_contracts/NEW_MODEL_REVIEWER_CHECKLIST_CN.md`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc1c_research_only_broad_bridge_contract/validator_design.json`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc1c_research_only_broad_bridge_contract/mtrc1d_work_recommendation.md`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc1b_research_only_extended_top50_ltr_signal_build/signals.csv`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc1b_research_only_extended_top50_ltr_signal_build/manifest.json`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc1b_research_only_extended_top50_ltr_signal_build/schema.json`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc1b_research_only_extended_top50_ltr_signal_build/validator_report.json`
- `data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2b_fresh_qlib_training/phase_s2b_post_filter_score_rank.csv`

## 3. 产物

输出目录：

```text
data_tw/experiments/policy_mtr_research_only_continuation/mtrc1d_research_only_broad_full_rank_signal_build
```

产物：

- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc1d_research_only_broad_full_rank_signal_build/manifest.json`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc1d_research_only_broad_full_rank_signal_build/signals.csv`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc1d_research_only_broad_full_rank_signal_build/schema.json`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc1d_research_only_broad_full_rank_signal_build/coverage_audit.csv`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc1d_research_only_broad_full_rank_signal_build/top50_equivalence_audit.csv`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc1d_research_only_broad_full_rank_signal_build/non_top50_visibility_audit.csv`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc1d_research_only_broad_full_rank_signal_build/non_top50_buy_hard_fail_audit.csv`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc1d_research_only_broad_full_rank_signal_build/extension_schema_audit.csv`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc1d_research_only_broad_full_rank_signal_build/forbidden_field_audit.csv`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc1d_research_only_broad_full_rank_signal_build/lineage_boundary_audit.csv`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc1d_research_only_broad_full_rank_signal_build/available_at_policy_audit.csv`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc1d_research_only_broad_full_rank_signal_build/source_trace_audit.csv`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc1d_research_only_broad_full_rank_signal_build/negative_samples/non_top50_buy_score_present.csv`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc1d_research_only_broad_full_rank_signal_build/negative_samples/non_top50_ranked_for_buy.json`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc1d_research_only_broad_full_rank_signal_build/negative_samples/missing_mtrc1b_top50_row.csv`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc1d_research_only_broad_full_rank_signal_build/negative_samples/changed_mtrc1b_top50_score.csv`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc1d_research_only_broad_full_rank_signal_build/validator_report.json`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc1d_research_only_broad_full_rank_signal_build/diagnostic_findings.md`

## 4. 行数 / 覆盖 / 等价检查

- broad `signals.csv` rows: `169366`
- MTRC1B top50 rows copied: `113000` / `113000`
- S2B qlib rows: `169366`
- non-top50 visibility-only rows: `56366` / S2B rank>50 `56366`
- date range: `2017-01-10..2026-05-07`
- date_count: `2260`
- rows_per_date: `51..150`
- duplicate `date,instrument`: `0`
- missing MTRC1B top50 rows: `0`
- top50 `buy_score` mismatch vs MTRC1B: `0`
- top50 `raw_score` mismatch vs MTRC1B: `0`
- top50 `score_rank` mismatch vs MTRC1B: `0`
- top50 `candidate_rank` mismatch vs S2B `qlib_rank`: `0`
- top50 `full_qlib_rank` mismatch vs S2B `qlib_rank`: `0`
- non-top50 rows not from S2B `qlib_rank > 50`: `0`
- S2B `qlib_rank > 50` rows missing from output: `0`
- non-top50 `buy_score/raw_score/score_rank` present counts: `0` / `0` / `0`
- non-top50 buy eligible not false: `0`

Validator checks:

- `required_core_fields_present`: True
- `date_instrument_unique`: True
- `mtrc1b_top50_all_rows_present`: True
- `top50_buy_score_equal_mtrc1b`: True
- `top50_raw_score_equal_mtrc1b`: True
- `top50_score_rank_equal_mtrc1b`: True
- `top50_candidate_rank_equal_mtrc1b`: True
- `top50_full_qlib_rank_equal_mtrc1b`: True
- `top50_candidate_rank_equal_s2b_qlib_rank`: True
- `top50_full_qlib_rank_equal_s2b_qlib_rank`: True
- `non_top50_rows_from_s2b_qlib_rank_gt50`: True
- `non_top50_buy_score_null`: True
- `non_top50_raw_score_null`: True
- `non_top50_score_rank_null`: True
- `non_top50_buy_eligible_false`: True
- `non_top50_not_ranked_for_buy`: True
- `extension_fields_declared`: True
- `extension_fields_ranking_allowed_false`: True
- `forbidden_fields_absent`: True
- `available_at_policy_declared`: True
- `lineage_s2c_research_only_non_equivalent_to_mtr2r_e3`: True
- `no_order_intent`: True
- `no_replay_result`: True
- `no_return_replay`: True
- `no_production_or_default_write`: True
- `negative_samples_fail_as_expected`: True

Failed gates:

```json
[]
```

## 5. Negative Sample 验证

- `non_top50_buy_score_present`: expected `fail`, failed_as_expected=`True`, sample=`data_tw/experiments/policy_mtr_research_only_continuation/mtrc1d_research_only_broad_full_rank_signal_build/negative_samples/non_top50_buy_score_present.csv`
- `non_top50_ranked_for_buy`: expected `fail`, failed_as_expected=`True`, sample=`data_tw/experiments/policy_mtr_research_only_continuation/mtrc1d_research_only_broad_full_rank_signal_build/negative_samples/non_top50_ranked_for_buy.json`
- `missing_mtrc1b_top50_row`: expected `fail`, failed_as_expected=`True`, sample=`data_tw/experiments/policy_mtr_research_only_continuation/mtrc1d_research_only_broad_full_rank_signal_build/negative_samples/missing_mtrc1b_top50_row.csv`
- `changed_mtrc1b_top50_score`: expected `fail`, failed_as_expected=`True`, sample=`data_tw/experiments/policy_mtr_research_only_continuation/mtrc1d_research_only_broad_full_rank_signal_build/negative_samples/changed_mtrc1b_top50_score.csv`

四类负例均已生成并由 validator 证明会 fail：

- `non_top50_buy_score_present`
- `non_top50_ranked_for_buy`
- `missing_mtrc1b_top50_row`
- `changed_mtrc1b_top50_score`

## 6. Forbidden Actions Audit

确认未执行：

- 训练模型、调参、模型 inference、重新计算 LTR score
- 新增策略候选或修改 `M2_hold_rank_buffer_100`
- 生成 OrderIntentArtifact / ReplayResultArtifact
- 收益 replay
- provider publish / accepted latest switch
- production/default/latest/provider/frontend/API/Agent/daily/config registry 改动
- monitor config / scan / alerts write
- broker / quick-trade / real order
- `target_weight` / `target_position` / `quantity` 指令
- 将 S2C 写成 MTR2_R/E3 等价
- 解除 MTR5 `clean_extended_lineage_found=false` blocker

## 7. 结论

```text
PASS_READY_FOR_MTRC1E_RESEARCH_ONLY_BROAD_SIGNAL_REVIEW_OR_NEXT_DIAGNOSTIC_CONTRACT
```

建议：`PASS，可进入 MTRC1E_RESEARCH_ONLY_BROAD_SIGNAL_REVIEW_OR_NEXT_DIAGNOSTIC_CONTRACT；不得自动进入 replay 或 production。`
