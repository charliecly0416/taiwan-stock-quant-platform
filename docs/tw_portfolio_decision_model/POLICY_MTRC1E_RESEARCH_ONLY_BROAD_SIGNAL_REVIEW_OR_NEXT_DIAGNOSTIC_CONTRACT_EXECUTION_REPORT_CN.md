# POLICY_MTRC1E_RESEARCH_ONLY_BROAD_SIGNAL_REVIEW_OR_NEXT_DIAGNOSTIC_CONTRACT_EXECUTION_REPORT_CN

生成时间：2026-06-28T14:59:56+00:00

## 1. 范围

本阶段只执行 `MTRC1E_RESEARCH_ONLY_BROAD_SIGNAL_REVIEW_OR_NEXT_DIAGNOSTIC_CONTRACT`：审查 MTRC1D research-only broad full-rank `ModelSignalArtifact` 是否足以作为下一阶段 concentration/window diagnostic contract 的标准输入，并冻结 MTRC2 的输入、输出、gate 与禁止项合同。

未生成或修改 broad `signals.csv`；未生成 OrderIntent、ReplayResult；未运行收益 replay；未实现 MTRC2；未训练、调参、inference 或重新计算 LTR score；未修改 production/default/latest/provider/frontend/API/Agent/daily/config registry；未 provider publish、accepted latest switch、broker、quick-trade、real order；未输出 target_weight、target_position 或 quantity 指令。

## 2. 读取文件

必读文档：

- `docs/tw_portfolio_decision_model/POLICY_MTRC_RESEARCH_ONLY_CONTINUATION_MAINLINE_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_MTRC1B_RESEARCH_ONLY_EXTENDED_TOP50_LTR_SIGNAL_BUILD_REVIEW_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_MTRC1C_RESEARCH_ONLY_BROAD_BRIDGE_CONTRACT_REVIEW_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_MTRC1D_RESEARCH_ONLY_BROAD_FULL_RANK_SIGNAL_BUILD_WORK_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_MTRC1D_RESEARCH_ONLY_BROAD_FULL_RANK_SIGNAL_BUILD_EXECUTION_REPORT_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_MTRC1D_RESEARCH_ONLY_BROAD_FULL_RANK_SIGNAL_BUILD_REVIEW_CN.md`
- `docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md`
- `docs/tw_modular_contracts/NEW_MODEL_AND_STRATEGY_DEVELOPER_GUIDE_CN.md`
- `docs/tw_modular_contracts/MODEL_SIGNAL_CONTRACT_CN.md`
- `docs/tw_modular_contracts/MODEL_SIGNAL_EXTENSION_SCHEMA_CN.md`
- `docs/tw_modular_contracts/NEW_MODEL_REVIEWER_CHECKLIST_CN.md`

MTRC1D artifact：

- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc1d_research_only_broad_full_rank_signal_build/manifest.json`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc1d_research_only_broad_full_rank_signal_build/signals.csv`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc1d_research_only_broad_full_rank_signal_build/schema.json`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc1d_research_only_broad_full_rank_signal_build/validator_report.json`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc1d_research_only_broad_full_rank_signal_build/top50_equivalence_audit.csv`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc1d_research_only_broad_full_rank_signal_build/non_top50_visibility_audit.csv`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc1d_research_only_broad_full_rank_signal_build/non_top50_buy_hard_fail_audit.csv`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc1d_research_only_broad_full_rank_signal_build/extension_schema_audit.csv`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc1d_research_only_broad_full_rank_signal_build/lineage_boundary_audit.csv`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc1d_research_only_broad_full_rank_signal_build/negative_samples`

另读取：

- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc1b_research_only_extended_top50_ltr_signal_build/signals.csv`
- `data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2b_fresh_qlib_training/phase_s2b_post_filter_score_rank.csv`

## 3. 产物

输出目录：

```text
data_tw/experiments/policy_mtr_research_only_continuation/mtrc1e_research_only_broad_signal_review_or_next_diagnostic_contract
```

产物：

- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc1e_research_only_broad_signal_review_or_next_diagnostic_contract/manifest.json`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc1e_research_only_broad_signal_review_or_next_diagnostic_contract/broad_signal_readiness_audit.csv`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc1e_research_only_broad_signal_review_or_next_diagnostic_contract/top50_equivalence_recheck.csv`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc1e_research_only_broad_signal_review_or_next_diagnostic_contract/non_top50_boundary_recheck.csv`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc1e_research_only_broad_signal_review_or_next_diagnostic_contract/negative_sample_coverage_audit.csv`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc1e_research_only_broad_signal_review_or_next_diagnostic_contract/extension_schema_recheck.csv`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc1e_research_only_broad_signal_review_or_next_diagnostic_contract/downstream_diagnostic_input_contract.csv`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc1e_research_only_broad_signal_review_or_next_diagnostic_contract/downstream_diagnostic_output_contract.csv`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc1e_research_only_broad_signal_review_or_next_diagnostic_contract/mtrc2_gate_contract.csv`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc1e_research_only_broad_signal_review_or_next_diagnostic_contract/mtrc2_forbidden_actions_contract.csv`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc1e_research_only_broad_signal_review_or_next_diagnostic_contract/forbidden_scope_audit.csv`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc1e_research_only_broad_signal_review_or_next_diagnostic_contract/production_boundary_audit.csv`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc1e_research_only_broad_signal_review_or_next_diagnostic_contract/validator_report.json`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc1e_research_only_broad_signal_review_or_next_diagnostic_contract/diagnostic_findings.md`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc1e_research_only_broad_signal_review_or_next_diagnostic_contract/mtrc2_work_recommendation.md`

## 4. MTRC1D Recheck 结果

- `signal_rows = 169366`
- `date_range = 2017-01-10..2026-05-07`
- `date_count = 2260`
- `top50_rows = 113000`
- `non_top50_rows = 56366`
- `duplicate_date_instrument = 0`
- `top50_outer_join_not_both = 0`
- `s2b_gt50_non_top50_join_not_both = 0`

Hard-gate blockers：

无

结论：top50 LTR 等价边界、non-top50 visibility-only/buy hard-fail 边界、extension schema、negative samples、S2C non-equivalence 与 forbidden side-effect flags 均已在本阶段重新检查。

## 5. MTRC2 Contract 内容摘要

MTRC2 若后续另行授权，只能做 `extended concentration / window diagnostic`。标准输入为 MTRC1D broad `ModelSignalArtifact`；如果需要既有 M2_100 research-only candidate/order/replay lineage、OrderIntent、ReplayResult 或 ledger，必须在 MTRC2 work doc 中另行声明来源与校验，MTRC1E 不替 MTRC2 选择 replay artifact。

MTRC2 gate 至少包括：

- `same_candidate_m2_hold_rank_buffer_100`
- `same_parameter_rank_buffer_100`
- `same_signal_artifact_mtrc1d_broad`
- `non_top50_buy_validator_pass`
- `order_intent_input_contract_declared_if_needed`
- `replay_result_input_contract_declared_if_needed`
- `no_strategy_tuning`
- `no_new_candidate`
- `no_replay_return_conclusion_without_predeclared_replay_contract`
- `no_production_or_default_write`

允许输出仅限 concentration、symbol/event attribution、monthly/rolling/risk-off/drawdown diagnostic tables，且必须标记为 diagnostic-only，不得写成 production readiness 或收益承诺。

## 6. Forbidden Actions Audit

本阶段 forbidden scope 和 production boundary audit 均为 pass。明确禁止：

- 训练、调参、inference、重新计算 LTR score。
- 生成或修改 broad `signals.csv`。
- 生成 OrderIntentArtifact、ReplayResultArtifact 或运行收益 replay。
- 实现 MTRC2、选择/生成 replay artifact、策略调参、新增候选或修改 `M2_hold_rank_buffer_100`。
- 修改 production/default/latest/provider/frontend/API/Agent/daily/config registry。
- provider refresh/publish、accepted latest switch、monitor write、broker、quick-trade、real order。
- 输出 target_weight、target_position、quantity instruction。
- 将 S2C 写成 MTR2_R/E3 等价或解除 MTR5 blocker。

## 7. Verdict

```text
PASS_READY_FOR_MTRC2_EXTENDED_CONCENTRATION_WINDOW_DIAGNOSTIC_CONTRACT_OR_INPUT_FEASIBILITY
```

若进入下一步，只建议：

```text
MTRC2_EXTENDED_CONCENTRATION_WINDOW_DIAGNOSTIC_CONTRACT_OR_INPUT_FEASIBILITY
```

MTRC2 仍不能直接跑收益 replay。必须先确认是否存在合法 same-candidate、same-parameter、same-signal lineage 的 diagnostic 输入；若不存在，必须 STOP 或开另行授权的 repair。
