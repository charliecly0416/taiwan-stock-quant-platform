# POLICY_MTRC1C_RESEARCH_ONLY_BROAD_BRIDGE_CONTRACT_EXECUTION_REPORT_CN

生成时间：2026-06-28T14:27:46+00:00

## 1. 范围

本阶段只执行 `MTRC1C_RESEARCH_ONLY_BROAD_BRIDGE_CONTRACT`：为 S2C research-only top50 LTR signal 设计 broad full-rank visibility bridge 的合同、可行性检查和 validator 规则。

未训练、未 inference、未生成 broad `signals.csv`、未生成 OrderIntent/ReplayResult、未跑收益 replay、未修改 production/default/latest/provider/frontend/API/Agent/daily/config registry。

## 2. 读取文件

- `docs/tw_portfolio_decision_model/POLICY_MTRC_RESEARCH_ONLY_CONTINUATION_MAINLINE_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_MTRC1A_R_LTR_INFERENCE_LINEAGE_REPAIR_REVIEW_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_MTRC1B_RESEARCH_ONLY_EXTENDED_TOP50_LTR_SIGNAL_BUILD_WORK_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_MTRC1B_RESEARCH_ONLY_EXTENDED_TOP50_LTR_SIGNAL_BUILD_EXECUTION_REPORT_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_MTRC1B_RESEARCH_ONLY_EXTENDED_TOP50_LTR_SIGNAL_BUILD_REVIEW_CN.md`
- `docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md`
- `docs/tw_modular_contracts/NEW_MODEL_AND_STRATEGY_DEVELOPER_GUIDE_CN.md`
- `docs/tw_modular_contracts/MODEL_SIGNAL_CONTRACT_CN.md`
- `docs/tw_modular_contracts/MODEL_SIGNAL_EXTENSION_SCHEMA_CN.md`
- `docs/tw_modular_contracts/NEW_MODEL_REVIEWER_CHECKLIST_CN.md`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc1b_research_only_extended_top50_ltr_signal_build/manifest.json`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc1b_research_only_extended_top50_ltr_signal_build/signals.csv`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc1b_research_only_extended_top50_ltr_signal_build/schema.json`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc1b_research_only_extended_top50_ltr_signal_build/validator_report.json`
- `data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2b_fresh_qlib_training/phase_s2b_post_filter_score_rank.csv`

## 3. 产物

输出目录：

```text
data_tw/experiments/policy_mtr_research_only_continuation/mtrc1c_research_only_broad_bridge_contract
```

产物：

- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc1c_research_only_broad_bridge_contract/manifest.json`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc1c_research_only_broad_bridge_contract/broad_bridge_contract.csv`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc1c_research_only_broad_bridge_contract/qlib_full_rank_source_contract.csv`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc1c_research_only_broad_bridge_contract/top50_equivalence_contract.csv`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc1c_research_only_broad_bridge_contract/non_top50_visibility_contract.csv`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc1c_research_only_broad_bridge_contract/non_top50_buy_hard_fail_contract.csv`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc1c_research_only_broad_bridge_contract/model_signal_extension_contract.csv`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc1c_research_only_broad_bridge_contract/candidate_input_inventory.csv`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc1c_research_only_broad_bridge_contract/feasibility_gate.csv`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc1c_research_only_broad_bridge_contract/forbidden_scope_audit.csv`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc1c_research_only_broad_bridge_contract/production_boundary_audit.csv`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc1c_research_only_broad_bridge_contract/validator_design.json`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc1c_research_only_broad_bridge_contract/validator_report.json`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc1c_research_only_broad_bridge_contract/diagnostic_findings.md`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc1c_research_only_broad_bridge_contract/mtrc1d_work_recommendation.md`

## 4. 检查结果

- MTRC1B top50 rows: `113000`
- MTRC1B date range: `2017-01-10..2026-05-07`
- S2B qlib source rows: `169366`
- S2B qlib date range: `2017-01-10..2026-05-07`
- S2B rows/date: `51..150`
- MTRC1B top50 join missing: `0`
- candidate_rank mismatch: `0`
- full_qlib_rank mismatch: `0`
- S2B non-top50 rows available: `56366`

Gate 明细：

- `mtrc1b_artifact_present`: PASS - MTRC1B top50 ModelSignalArtifact inputs exist.
- `mtrc1b_parent_validator_passed`: PASS - Parent validator has no blocking failures.
- `lineage_is_s2c_only`: PASS - Manifest declares S2C and non-equivalence to MTR2_R/E3.
- `required_core_fields_present`: PASS - MTRC1B top50 signal has ModelSignal core fields.
- `s2b_qlib_source_columns_present`: PASS - S2B source has date,instrument,qlib_rank,qlib_score_raw.
- `date_range_covered_by_s2b_source`: PASS - S2B source covers all MTRC1B signal dates.
- `top50_date_instrument_join_complete`: PASS - All MTRC1B top50 rows join to S2B qlib source.
- `top50_candidate_rank_equal_s2c_qlib_rank`: PASS - Top50 candidate_rank equals S2B qlib_rank.
- `top50_full_qlib_rank_equal_s2c_qlib_rank`: PASS - Top50 full_qlib_rank equals S2B qlib_rank.
- `top50_buy_score_equal_mtrc1b_policy_defined`: PASS - MTRC1D must copy MTRC1B top50 buy_score exactly.
- `top50_raw_score_equal_mtrc1b_policy_defined`: PASS - MTRC1D must copy MTRC1B top50 raw_score exactly.
- `top50_score_rank_equal_mtrc1b_policy_defined`: PASS - MTRC1B score_rank is internally stable and must be copied exactly.
- `s2b_has_non_top50_visibility_rows`: PASS - S2B source contains qlib_rank > 50 rows for visibility-only bridge.
- `non_top50_visibility_only_policy_defined`: PASS - Contract defines non-top50 rows as hold/sell visibility only.
- `non_top50_buy_hard_fail_policy_defined`: PASS - Contract defines negative samples and hard-fail gates.
- `extension_schema_compliant_if_used`: PASS - Only ext_* diagnostic fields are proposed; ranking_allowed=false.
- `forbidden_fields_absent_from_inputs`: PASS - Forbidden input columns found: []
- `available_at_policy_declared`: PASS - MTRC1B declares legacy research daily-visible policy.
- `no_broad_signal_generated_by_mtrc1c`: PASS - MTRC1C must not generate broad signals.csv.
- `no_order_intent`: PASS - MTRC1C does not create OrderIntentArtifact.
- `no_replay_result`: PASS - MTRC1C does not create ReplayResultArtifact or run return replay.
- `no_production_or_default_write`: PASS - Builder writes only MTRC1C output directory and execution report.
- `mtr5_blocker_not_cleared`: PASS - S2C does not clear clean_extended_lineage_found=false.

Failed gates:

```json
[]
```

## 5. Forbidden Actions Audit

确认未执行：

- 训练模型、调参、模型 inference
- 生成 broad `signals.csv`
- 生成 OrderIntentArtifact / ReplayResultArtifact
- 收益 replay
- 新增策略候选或修改 `M2_hold_rank_buffer_100`
- provider publish / accepted latest switch
- production/default/latest/provider/frontend/API/Agent/daily/config registry 改动
- broker / quick-trade / real order
- `target_weight` / `target_position` / `quantity` 指令
- 将 S2C 写成 MTR2_R/E3 等价
- 解除 MTR5 `clean_extended_lineage_found=false` blocker

## 6. 结论

```text
PASS_READY_FOR_MTRC1D_RESEARCH_ONLY_BROAD_FULL_RANK_SIGNAL_BUILD
```

理由：S2B `phase_s2b_post_filter_score_rank.csv` 可作为 S2C broad bridge 的唯一 qlib full-rank source 候选；它覆盖 MTRC1B 日期范围，MTRC1B top50 key 全部可对齐，top50 `candidate_rank/full_qlib_rank` 与 S2B `qlib_rank` mismatch 为 0。MTRC1C 已定义 top50 等价、non-top50 visibility-only、non-top50 buy hard-fail、extension schema 和 validator design。

MTRC1D 仍需另行授权；本报告不授权 broad build、replay、production readiness 或任何下游接入。
