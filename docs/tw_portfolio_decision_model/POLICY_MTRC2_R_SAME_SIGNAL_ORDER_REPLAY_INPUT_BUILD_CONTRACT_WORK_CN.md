---
created_at: 2026-06-28
status: work_doc
phase: MTRC2_R_SAME_SIGNAL_ORDER_REPLAY_INPUT_BUILD_CONTRACT
parent_phase: MTRC2_EXTENDED_CONCENTRATION_WINDOW_DIAGNOSTIC_CONTRACT_OR_INPUT_FEASIBILITY
parent_review: docs/tw_portfolio_decision_model/POLICY_MTRC2_EXTENDED_CONCENTRATION_WINDOW_DIAGNOSTIC_CONTRACT_OR_INPUT_FEASIBILITY_REVIEW_CN.md
readonly_only: true
simulation_only: true
production_allowed: false
model_training_authorized: false
model_inference_authorized: false
model_signal_artifact_authorized: false
strategy_contract_authorized: true
order_intent_build_authorized: false
replay_result_build_authorized: false
return_replay_authorized: false
strategy_tuning_authorized: false
new_candidate_authorized: false
provider_publish_allowed: false
accepted_latest_switch_allowed: false
frontend_default_switch_allowed: false
broker_authorized: false
---

# POLICY_MTRC2_R_SAME_SIGNAL_ORDER_REPLAY_INPUT_BUILD_CONTRACT_WORK_CN

## 1. 目标

MTRC2_R 只做一件事：

```text
为后续基于 MTRC1D broad signal、M2_hold_rank_buffer_100、rank_buffer=100
构建 same-signal readonly OrderIntent / ReplayResult / ledger input 冻结合同、validator 和下一步工作边界。
```

本阶段不得生成 OrderIntent、ReplayResult、ledger，不得运行收益 replay，不得实现 concentration/window diagnostic。MTRC2_R 的输出是 build contract，不是 build result。

MTRC2_R 必须回答：

```text
1. 后续 MTRC2_S 若被授权，如何基于 MTRC1D broad signal 构建 same-signal OrderIntent；
2. 后续 ReplayResult 若被授权，必须消费哪个 OrderIntent、哪个 price store、哪个 execution config；
3. 如何保证 candidate_id=M2_hold_rank_buffer_100、rank_buffer=100、strategy_rule 不变；
4. 如何保证 non-top50 buy hard fail；
5. 如何禁止旧 MTR2_R/E3 replay 进入 S2C/MTRC diagnostic；
6. MTRC2_S/MTRC2_T/MTRC3 的阶段边界是什么。
```

## 2. 必读输入

执行者必须读取：

```text
docs/tw_portfolio_decision_model/POLICY_MTRC_RESEARCH_ONLY_CONTINUATION_MAINLINE_CN.md
docs/tw_portfolio_decision_model/POLICY_MTRC2_EXTENDED_CONCENTRATION_WINDOW_DIAGNOSTIC_CONTRACT_OR_INPUT_FEASIBILITY_WORK_CN.md
docs/tw_portfolio_decision_model/POLICY_MTRC2_EXTENDED_CONCENTRATION_WINDOW_DIAGNOSTIC_CONTRACT_OR_INPUT_FEASIBILITY_EXECUTION_REPORT_CN.md
docs/tw_portfolio_decision_model/POLICY_MTRC2_EXTENDED_CONCENTRATION_WINDOW_DIAGNOSTIC_CONTRACT_OR_INPUT_FEASIBILITY_REVIEW_CN.md
docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md
docs/tw_modular_contracts/NEW_MODEL_AND_STRATEGY_DEVELOPER_GUIDE_CN.md
docs/tw_modular_contracts/MODEL_SIGNAL_CONTRACT_CN.md
docs/tw_modular_contracts/MODEL_SIGNAL_EXTENSION_SCHEMA_CN.md
docs/tw_modular_contracts/STRATEGY_RULE_CONTRACT_CN.md
docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md
docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md
docs/tw_modular_contracts/NEW_STRATEGY_REVIEWER_CHECKLIST_CN.md
configs/strategy_dependencies/mechanism_transfer_top50_cost_aware_v1.yaml
```

必须检查 MTRC 输入：

```text
data_tw/experiments/policy_mtr_research_only_continuation/mtrc1d_research_only_broad_full_rank_signal_build/manifest.json
data_tw/experiments/policy_mtr_research_only_continuation/mtrc1d_research_only_broad_full_rank_signal_build/signals.csv
data_tw/experiments/policy_mtr_research_only_continuation/mtrc1d_research_only_broad_full_rank_signal_build/validator_report.json
data_tw/experiments/policy_mtr_research_only_continuation/mtrc2_extended_concentration_window_diagnostic_contract_or_input_feasibility/same_candidate_same_parameter_input_inventory.csv
data_tw/experiments/policy_mtr_research_only_continuation/mtrc2_extended_concentration_window_diagnostic_contract_or_input_feasibility/diagnostic_input_gap_analysis.csv
data_tw/experiments/policy_mtr_research_only_continuation/mtrc2_extended_concentration_window_diagnostic_contract_or_input_feasibility/validator_report.json
```

允许参考旧 MTR2_R 模板，但必须标记 non-equivalent：

```text
data_tw/experiments/policy_mtr_mechanism_transfer/mtr2_r_broad_full_rank_visibility_repair/order_intents/M2_hold_rank_buffer_100/manifest.json
data_tw/experiments/policy_mtr_mechanism_transfer/mtr2_r_broad_full_rank_visibility_repair/replays/M2_hold_rank_buffer_100/manifest.json
data_tw/experiments/policy_mtr_mechanism_transfer/mtr2_r_broad_full_rank_visibility_repair/order_intent_artifact_index.csv
data_tw/experiments/policy_mtr_mechanism_transfer/mtr2_r_broad_full_rank_visibility_repair/replay_artifact_index.csv
```

## 3. 允许输出

输出目录：

```text
data_tw/experiments/policy_mtr_research_only_continuation/mtrc2_r_same_signal_order_replay_input_build_contract/
```

允许生成：

```text
manifest.json
same_signal_order_intent_build_contract.csv
same_signal_replay_input_build_contract.csv
same_signal_ledger_input_contract.csv
strategy_dependency_contract.csv
m2_100_parameter_freeze_contract.csv
non_top50_buy_validator_contract.csv
old_mtr2r_template_non_equivalence_audit.csv
mtrc2_s_order_intent_build_work_recommendation.md
mtrc2_t_replay_input_build_work_recommendation.md
mtrc3_diagnostic_entry_gate_contract.csv
forbidden_scope_audit.csv
production_boundary_audit.csv
validator_report.json
diagnostic_findings.md
```

执行报告：

```text
docs/tw_portfolio_decision_model/POLICY_MTRC2_R_SAME_SIGNAL_ORDER_REPLAY_INPUT_BUILD_CONTRACT_EXECUTION_REPORT_CN.md
```

审查报告：

```text
docs/tw_portfolio_decision_model/POLICY_MTRC2_R_SAME_SIGNAL_ORDER_REPLAY_INPUT_BUILD_CONTRACT_REVIEW_CN.md
```

允许新增 contract/audit builder：

```text
scripts/build_tw_policy_mtrc2_r_same_signal_order_replay_input_build_contract.py
```

builder 只能写 MTRC2_R 输出目录和 MTRC2_R 执行报告，不得写 MTRC1D/MTRC2 产物，不得写 registry、configs、provider、latest、frontend、API、Agent、daily 或 production 目录。

## 4. 后续 OrderIntent build 合同

MTRC2_R 必须冻结 MTRC2_S 若后续授权时的 OrderIntent build 规则：

```text
input_model_signal = data_tw/experiments/policy_mtr_research_only_continuation/mtrc1d_research_only_broad_full_rank_signal_build/manifest.json
strategy_rule = mechanism_transfer_top50_cost_aware_v1
candidate_id = M2_hold_rank_buffer_100
mechanism = hold_rank_buffer
rank_buffer = 100
target_holding_count = 10
candidate_k = 50
max_buy_count = 1
max_sell_count = 1
sell_boundary = qlib_top50_by_candidate_rank_and_full_qlib_rank
buy_order = buy_score_desc_only_within_top50
tie_breaker = full_qlib_rank_asc, instrument_asc
readonly_only = true
simulation_only = true
diagnostic_only = true
production_allowed = false
```

OrderIntent validator hard gates：

```text
signal_artifact_equals_mtrc1d_broad
candidate_id_equals_M2_hold_rank_buffer_100
rank_buffer_equals_100
strategy_rule_equals_mechanism_transfer_top50_cost_aware_v1
required_order_intent_fields_present
no_execution_price_cash_nav_fee_tax_quantity_target_fields
daily_buy_count_lte_1
daily_sell_count_lte_1
buy_candidate_rank_lte_50
buy_score_present_only_for_top50_buy_candidates
non_top50_buy_intent_count_equals_0
full_qlib_rank_used_for_sell_boundary
old_mtr2r_order_intent_not_reused
```

## 5. 后续 Replay input 合同

MTRC2_R 必须冻结 MTRC2_T 若后续授权时的 ReplayResult input build 规则：

```text
decision_source = MTRC2_S same-signal OrderIntentArtifact
price_store = 只能使用合同声明且 PIT/readiness 通过的历史价格源
execution_price = next_open
initial_equity = 1000000
target_holdings = 10
fee_rate = 0.001425
sell_tax_rate = 0.003
lot_size = 10
readonly_only = true
simulation_only = true
diagnostic_only = true
production_allowed = false
```

Replay validator hard gates：

```text
order_intent_artifact_equals_mtrc2_s_same_signal
order_intent_signal_artifact_equals_mtrc1d_broad
candidate_id_equals_M2_hold_rank_buffer_100
rank_buffer_equals_100
execution_date_gt_signal_date
missing_price_skip_or_audit
no_negative_cash_unless_explicitly_allowed
max_holding_count_lte_10
forbidden_fields_absent
old_mtr2r_replay_not_reused
```

MTRC2_R 不得选择实际 price store 产物为最终输入；只能声明后续 MTRC2_T 必须检查价格源 readiness。

## 6. Ledger contract

如果后续 MTRC3 需要 action-level 或 daily ledger，必须从 MTRC2_T ReplayResult 派生，不得从旧 MTR2_R/E3 ledger 派生。

ledger contract 必须声明：

```text
source_replay_result = MTRC2_T same-signal ReplayResult
source_order_intent = MTRC2_S same-signal OrderIntent
source_signal = MTRC1D broad signal
diagnostic_only = true
not_strategy_input = true
not_production_readiness = true
```

## 7. 禁止动作

MTRC2_R 当前阶段明确禁止：

```text
训练模型
调参
模型 inference
重新计算 LTR score
生成或修改 ModelSignalArtifact
生成 OrderIntentArtifact
生成 ReplayResultArtifact
生成 ledger
运行收益 replay
实现 concentration/window diagnostic 计算
新增策略候选
修改 M2_hold_rank_buffer_100 参数
选择或调参策略
复用旧 MTR2_R/E3 order/replay/ledger 作为 S2C/MTRC input
修改 strategy dependency YAML 或 registry/default
修改 production/default/latest/provider/frontend/API/Agent/daily
provider refresh / publish
accepted latest switch
monitor config / scan / alerts write
broker / quick-trade / real order
target_weight / target_position / quantity instruction
将 S2C 描述为 MTR2_R/E3 等价
解除 MTR5 clean_extended_lineage_found=false blocker
```

## 8. PASS / FAIL 标准

PASS 需要同时满足：

```text
MTRC2_S OrderIntent build contract 完整；
MTRC2_T Replay input build contract 完整；
MTRC3 diagnostic entry gate 完整；
M2_100 参数冻结；
non_top50 buy hard fail 合同明确；
旧 MTR2_R/E3 只作为模板参考并明确 non-equivalent；
forbidden scope 和 production boundary audit 干净；
未生成 OrderIntent/ReplayResult/ledger，未跑收益 replay。
```

允许 verdict：

```text
PASS_READY_FOR_MTRC2_S_SAME_SIGNAL_ORDER_INTENT_BUILD
PASS_WITH_CONDITIONS_READY_FOR_MTRC2_R_R_NARROW_REPAIR
FAIL_NEEDS_MTRC2_R_CONTRACT_REPAIR
STOP_NO_LEGAL_SAME_SIGNAL_INPUT_BUILD_PATH
```

## 9. 下一阶段边界

若 PASS，下一步只能开：

```text
MTRC2_S_SAME_SIGNAL_ORDER_INTENT_BUILD
```

MTRC2_S 只能构建 readonly OrderIntentArtifact，不得 replay，不得收益结论，不得 production readiness。Replay input build 必须等 MTRC2_S 审查通过后再开 MTRC2_T。
