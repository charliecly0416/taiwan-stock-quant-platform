# POLICY_MTRC2_R_SAME_SIGNAL_ORDER_REPLAY_INPUT_BUILD_CONTRACT_EXECUTION_REPORT_CN

生成时间：2026-06-28T15:31:12+00:00

## 1. 范围

本阶段只执行 `MTRC2_R_SAME_SIGNAL_ORDER_REPLAY_INPUT_BUILD_CONTRACT`：为后续基于 MTRC1D broad signal、`M2_hold_rank_buffer_100`、`rank_buffer=100` 构建 same-signal readonly OrderIntent / ReplayResult / ledger input 冻结合同、validator 和下一步边界。

未生成 OrderIntentArtifact、ReplayResultArtifact、ledger 或 ModelSignal；未运行收益 replay；未实现 concentration/window diagnostic；未训练、调参、inference 或重新计算 LTR score；未修改 strategy dependency YAML、registry/default、production/default/latest/provider/frontend/API/Agent/daily；未 provider publish、accepted latest switch、broker、quick-trade、real order；未输出 target_weight、target_position 或 quantity。

## 2. 读取文件

- `docs/tw_portfolio_decision_model/POLICY_MTRC_RESEARCH_ONLY_CONTINUATION_MAINLINE_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_MTRC2_EXTENDED_CONCENTRATION_WINDOW_DIAGNOSTIC_CONTRACT_OR_INPUT_FEASIBILITY_WORK_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_MTRC2_EXTENDED_CONCENTRATION_WINDOW_DIAGNOSTIC_CONTRACT_OR_INPUT_FEASIBILITY_EXECUTION_REPORT_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_MTRC2_EXTENDED_CONCENTRATION_WINDOW_DIAGNOSTIC_CONTRACT_OR_INPUT_FEASIBILITY_REVIEW_CN.md`
- `docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md`
- `docs/tw_modular_contracts/NEW_MODEL_AND_STRATEGY_DEVELOPER_GUIDE_CN.md`
- `docs/tw_modular_contracts/MODEL_SIGNAL_CONTRACT_CN.md`
- `docs/tw_modular_contracts/MODEL_SIGNAL_EXTENSION_SCHEMA_CN.md`
- `docs/tw_modular_contracts/STRATEGY_RULE_CONTRACT_CN.md`
- `docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md`
- `docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md`
- `docs/tw_modular_contracts/NEW_STRATEGY_REVIEWER_CHECKLIST_CN.md`
- `configs/strategy_dependencies/mechanism_transfer_top50_cost_aware_v1.yaml`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc1d_research_only_broad_full_rank_signal_build/manifest.json`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc1d_research_only_broad_full_rank_signal_build/signals.csv`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc1d_research_only_broad_full_rank_signal_build/validator_report.json`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc2_extended_concentration_window_diagnostic_contract_or_input_feasibility/same_candidate_same_parameter_input_inventory.csv`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc2_extended_concentration_window_diagnostic_contract_or_input_feasibility/diagnostic_input_gap_analysis.csv`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc2_extended_concentration_window_diagnostic_contract_or_input_feasibility/validator_report.json`
- `data_tw/experiments/policy_mtr_mechanism_transfer/mtr2_r_broad_full_rank_visibility_repair/order_intents/M2_hold_rank_buffer_100/manifest.json`
- `data_tw/experiments/policy_mtr_mechanism_transfer/mtr2_r_broad_full_rank_visibility_repair/replays/M2_hold_rank_buffer_100/manifest.json`
- `data_tw/experiments/policy_mtr_mechanism_transfer/mtr2_r_broad_full_rank_visibility_repair/order_intent_artifact_index.csv`
- `data_tw/experiments/policy_mtr_mechanism_transfer/mtr2_r_broad_full_rank_visibility_repair/replay_artifact_index.csv`

## 3. 产物

输出目录：

```text
data_tw/experiments/policy_mtr_research_only_continuation/mtrc2_r_same_signal_order_replay_input_build_contract
```

产物：

- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc2_r_same_signal_order_replay_input_build_contract/manifest.json`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc2_r_same_signal_order_replay_input_build_contract/same_signal_order_intent_build_contract.csv`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc2_r_same_signal_order_replay_input_build_contract/same_signal_replay_input_build_contract.csv`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc2_r_same_signal_order_replay_input_build_contract/same_signal_ledger_input_contract.csv`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc2_r_same_signal_order_replay_input_build_contract/strategy_dependency_contract.csv`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc2_r_same_signal_order_replay_input_build_contract/m2_100_parameter_freeze_contract.csv`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc2_r_same_signal_order_replay_input_build_contract/non_top50_buy_validator_contract.csv`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc2_r_same_signal_order_replay_input_build_contract/old_mtr2r_template_non_equivalence_audit.csv`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc2_r_same_signal_order_replay_input_build_contract/mtrc2_s_order_intent_build_work_recommendation.md`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc2_r_same_signal_order_replay_input_build_contract/mtrc2_t_replay_input_build_work_recommendation.md`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc2_r_same_signal_order_replay_input_build_contract/mtrc3_diagnostic_entry_gate_contract.csv`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc2_r_same_signal_order_replay_input_build_contract/forbidden_scope_audit.csv`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc2_r_same_signal_order_replay_input_build_contract/production_boundary_audit.csv`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc2_r_same_signal_order_replay_input_build_contract/validator_report.json`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc2_r_same_signal_order_replay_input_build_contract/diagnostic_findings.md`
- `docs/tw_portfolio_decision_model/POLICY_MTRC2_R_SAME_SIGNAL_ORDER_REPLAY_INPUT_BUILD_CONTRACT_EXECUTION_REPORT_CN.md`

## 4. OrderIntent Build Contract 摘要

后续 MTRC2_S 若被授权，只能消费 `data_tw/experiments/policy_mtr_research_only_continuation/mtrc1d_research_only_broad_full_rank_signal_build/manifest.json`，使用 `mechanism_transfer_top50_cost_aware_v1`、`candidate_id=M2_hold_rank_buffer_100`、`mechanism=hold_rank_buffer`、`rank_buffer=100`、`target_holding_count=10`、`candidate_k=50`、`max_buy_count=1`、`max_sell_count=1`。买入排序仅限 top50 内 `buy_score` 降序，tie-breaker 为 `full_qlib_rank_asc, instrument_asc`；卖出边界为 `qlib_top50_by_candidate_rank_and_full_qlib_rank`。

## 5. Replay Input Contract 摘要

后续 MTRC2_T 若被授权，必须消费 MTRC2_S same-signal OrderIntentArtifact，不得消费旧 MTR2_R/E3 order/replay。价格源只能由 MTRC2_T 声明并通过 PIT/readiness 检查；执行配置冻结为 `next_open`、`initial_equity=1000000`、`target_holdings=10`、`fee_rate=0.001425`、`sell_tax_rate=0.003`、`lot_size=10`。

## 6. Non-top50 Buy Validator Contract

`non_top50_buy_intent_count_equals_0` 是 hard fail。任何 buy intent 必须满足 `candidate_rank <= 50`；MTRC1D 中 non-top50 rows 只能用于 broad visibility / hold-sell 边界，不得参与买入排序。MTRC1D 当前统计：rows=169366，top50=113000，non_top50=56366，non_top50 buy score/raw/score_rank present 均为 0。

## 7. Old MTR2_R Non-equivalence

旧 MTR2_R `M2_hold_rank_buffer_100` OrderIntent / ReplayResult 只能作为 non-equivalent 模板参考：same_candidate=true、same_parameter=true、same_signal=false、usable_as_mtrc_input=false。S2C 是新的 research lineage，不得写成 MTR2_R/E3 等价，不得解除 MTR5 `clean_extended_lineage_found=false` blocker。

## 8. Forbidden Actions Audit

forbidden scope 与 production boundary audit 均为 pass。脚本只写 MTRC2_R 输出目录和本执行报告；未写 MTRC1D/MTRC2 既有产物，未写 registry/config default/provider/latest/frontend/API/Agent/daily/production。

## 9. Verdict

```text
PASS_READY_FOR_MTRC2_S_SAME_SIGNAL_ORDER_INTENT_BUILD
```

推荐下一步：

```text
PASS_READY_FOR_MTRC2_S_SAME_SIGNAL_ORDER_INTENT_BUILD
```
