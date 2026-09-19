# POLICY_MTRC2_EXTENDED_CONCENTRATION_WINDOW_DIAGNOSTIC_CONTRACT_OR_INPUT_FEASIBILITY_EXECUTION_REPORT_CN

生成时间：2026-06-28T15:14:04+00:00

## 1. 范围

本阶段只执行 `MTRC2_EXTENDED_CONCENTRATION_WINDOW_DIAGNOSTIC_CONTRACT_OR_INPUT_FEASIBILITY`：盘点 MTRC1D/MTRC1E 已通过的 S2C research-only broad `ModelSignalArtifact` 是否可作为 diagnostic signal input，并检查是否存在同候选、同参数、同信号 lineage 的既有 OrderIntent / ReplayResult / ledger 输入。

未运行收益 replay；未生成 OrderIntent、ReplayResult、ledger 或 ModelSignal；未实现 concentration/window diagnostic 计算；未替 MTRC2 选择 replay artifact；未训练、调参、inference 或重新计算 LTR score；未修改 production/default/latest/provider/frontend/API/Agent/daily/config registry；未 provider publish、accepted latest switch、broker、quick-trade、real order；未输出 target_weight、target_position 或 quantity。

## 2. 读取文件

- `docs/tw_portfolio_decision_model/POLICY_MTRC_RESEARCH_ONLY_CONTINUATION_MAINLINE_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_MTRC1D_RESEARCH_ONLY_BROAD_FULL_RANK_SIGNAL_BUILD_REVIEW_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_MTRC1E_RESEARCH_ONLY_BROAD_SIGNAL_REVIEW_OR_NEXT_DIAGNOSTIC_CONTRACT_WORK_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_MTRC1E_RESEARCH_ONLY_BROAD_SIGNAL_REVIEW_OR_NEXT_DIAGNOSTIC_CONTRACT_EXECUTION_REPORT_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_MTRC1E_RESEARCH_ONLY_BROAD_SIGNAL_REVIEW_OR_NEXT_DIAGNOSTIC_CONTRACT_REVIEW_CN.md`
- `docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md`
- `docs/tw_modular_contracts/NEW_MODEL_AND_STRATEGY_DEVELOPER_GUIDE_CN.md`
- `docs/tw_modular_contracts/MODEL_SIGNAL_CONTRACT_CN.md`
- `docs/tw_modular_contracts/MODEL_SIGNAL_EXTENSION_SCHEMA_CN.md`
- `docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md`
- `docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md`
- `docs/tw_modular_contracts/STRATEGY_RULE_CONTRACT_CN.md`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc1e_research_only_broad_signal_review_or_next_diagnostic_contract/mtrc2_gate_contract.csv`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc1e_research_only_broad_signal_review_or_next_diagnostic_contract/downstream_diagnostic_input_contract.csv`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc1e_research_only_broad_signal_review_or_next_diagnostic_contract/downstream_diagnostic_output_contract.csv`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc1e_research_only_broad_signal_review_or_next_diagnostic_contract/mtrc2_forbidden_actions_contract.csv`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc1e_research_only_broad_signal_review_or_next_diagnostic_contract/validator_report.json`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc1e_research_only_broad_signal_review_or_next_diagnostic_contract/mtrc2_work_recommendation.md`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc1d_research_only_broad_full_rank_signal_build/manifest.json`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc1d_research_only_broad_full_rank_signal_build/signals.csv`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc1d_research_only_broad_full_rank_signal_build/validator_report.json`
- `data_tw/experiments/policy_mtr_mechanism_transfer/mtr2_r_broad_full_rank_visibility_repair/order_intent_artifact_index.csv`
- `data_tw/experiments/policy_mtr_mechanism_transfer/mtr2_r_broad_full_rank_visibility_repair/replay_artifact_index.csv`
- `data_tw/experiments/policy_mtr_mechanism_transfer/mtr2_r_broad_full_rank_visibility_repair/manifest.json`
- `data_tw/experiments/policy_mtr_mechanism_transfer/mtr3_robustness_window_regime_and_mechanism_attribution/manifest.json`
- `data_tw/experiments/policy_mtr_mechanism_transfer/mtr5_extended_oos_shadow_and_production_readiness_diagnostic/manifest.json`
- `data_tw/experiments/policy_mtr_mechanism_transfer/mtr5_extended_oos_shadow_and_production_readiness_diagnostic/extended_lineage_inventory.csv`
- `data_tw/experiments/policy_mtr_mechanism_transfer/mtr5_extended_oos_shadow_and_production_readiness_diagnostic/data_lineage_blocker.md`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc1d_research_only_broad_full_rank_signal_build/manifest.json`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc1d_research_only_broad_full_rank_signal_build/signals.csv`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc1d_research_only_broad_full_rank_signal_build/validator_report.json`

## 3. 产物

输出目录：

```text
data_tw/experiments/policy_mtr_research_only_continuation/mtrc2_extended_concentration_window_diagnostic_contract_or_input_feasibility
```

产物：

- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc2_extended_concentration_window_diagnostic_contract_or_input_feasibility/manifest.json`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc2_extended_concentration_window_diagnostic_contract_or_input_feasibility/mtrc1d_signal_input_readiness.csv`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc2_extended_concentration_window_diagnostic_contract_or_input_feasibility/same_candidate_same_parameter_input_inventory.csv`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc2_extended_concentration_window_diagnostic_contract_or_input_feasibility/order_intent_input_feasibility.csv`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc2_extended_concentration_window_diagnostic_contract_or_input_feasibility/replay_result_input_feasibility.csv`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc2_extended_concentration_window_diagnostic_contract_or_input_feasibility/ledger_input_feasibility.csv`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc2_extended_concentration_window_diagnostic_contract_or_input_feasibility/old_mtr_lineage_non_equivalence_audit.csv`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc2_extended_concentration_window_diagnostic_contract_or_input_feasibility/diagnostic_input_gap_analysis.csv`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc2_extended_concentration_window_diagnostic_contract_or_input_feasibility/mtrc2_diagnostic_contract.csv`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc2_extended_concentration_window_diagnostic_contract_or_input_feasibility/mtrc2_output_schema_contract.csv`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc2_extended_concentration_window_diagnostic_contract_or_input_feasibility/mtrc2_stop_or_repair_decision.csv`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc2_extended_concentration_window_diagnostic_contract_or_input_feasibility/forbidden_scope_audit.csv`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc2_extended_concentration_window_diagnostic_contract_or_input_feasibility/production_boundary_audit.csv`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc2_extended_concentration_window_diagnostic_contract_or_input_feasibility/validator_report.json`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc2_extended_concentration_window_diagnostic_contract_or_input_feasibility/diagnostic_findings.md`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc2_extended_concentration_window_diagnostic_contract_or_input_feasibility/mtrc2_next_step_recommendation.md`
- `docs/tw_portfolio_decision_model/POLICY_MTRC2_EXTENDED_CONCENTRATION_WINDOW_DIAGNOSTIC_CONTRACT_OR_INPUT_FEASIBILITY_EXECUTION_REPORT_CN.md`

## 4. MTRC1D Signal Readiness

- artifact_type = `policy_mtrc1d_research_only_broad_full_rank_signal_build`
- lineage_id = `S2C_SPLIT_ALIGNED_FRESH_LTR`
- model_name = `s2c_split_aligned_fresh_ltr_research_only_broad_full_rank_mtrc1d`
- signal_rows = `169366`
- top50_rows = `113000`
- non_top50_rows = `56366`
- date_range = `2017-01-10..2026-05-07`
- duplicate_date_instrument = `0`
- non_top50 buy hard fail = pass
- S2C remains non-equivalent to MTR2_R/E3
- MTR5 `clean_extended_lineage_found=false` blocker remains uncleared

## 5. Same Candidate / Parameter / Signal Input Inventory

旧 MTR2_R 中存在 `M2_hold_rank_buffer_100` 的 OrderIntent 和 ReplayResult，但均为 MTR2_R broad signal lineage，不是 S2C/MTRC1D signal：

- `order_intent` `data_tw/experiments/policy_mtr_mechanism_transfer/mtr2_r_broad_full_rank_visibility_repair/order_intents/M2_hold_rank_buffer_100/manifest.json`: same_candidate=true, same_parameter=true, same_signal=false, usable=false
- `replay_result` `data_tw/experiments/policy_mtr_mechanism_transfer/mtr2_r_broad_full_rank_visibility_repair/replays/M2_hold_rank_buffer_100/manifest.json`: same_candidate=true, same_parameter=true, same_signal=false, usable=false
- `ledger` ``: same_candidate=true, same_parameter=true, same_signal=false, usable=false

合法 same-candidate / same-parameter / same-signal input 数量：`0`。

## 6. 是否存在合法 Diagnostic Input

结论：不存在合法 same-signal OrderIntent / ReplayResult / ledger 输入。MTRC2 当前不能进入 MTRC3 diagnostic，也不能临时生成或选择 replay artifact。

## 7. Old MTR2_R/E3 Non-equivalence

旧 MTR2_R/E3 replay 只能作为 lineage feasibility / non-equivalence audit 参考。即使 candidate_id 与 rank_buffer=100 相同，signal lineage 仍不是 `S2C_SPLIT_ALIGNED_FRESH_LTR`，因此 `same_signal=false`、`usable_for_mtrc2_diagnostic=false`。

## 8. Forbidden Actions Audit

本阶段 forbidden scope / production boundary audit 均为 pass。未执行收益 replay、OrderIntent/ReplayResult/ledger/ModelSignal 生成、diagnostic 计算、策略调参、生产链路写入、provider/latest 切换、broker/order 或 target/quantity 输出。

## 9. Verdict

```text
PASS_READY_FOR_MTRC2_R_SAME_SIGNAL_ORDER_REPLAY_INPUT_BUILD_CONTRACT
```

建议下一步只开：

```text
MTRC2_R_SAME_SIGNAL_ORDER_REPLAY_INPUT_BUILD_CONTRACT
```

该下一步仍必须先写合同，不得直接跑收益 replay；必须声明如何基于 MTRC1D broad signal、`M2_hold_rank_buffer_100`、`rank_buffer=100` 生成或定位 readonly input，并保留 non-top50 buy hard fail。
