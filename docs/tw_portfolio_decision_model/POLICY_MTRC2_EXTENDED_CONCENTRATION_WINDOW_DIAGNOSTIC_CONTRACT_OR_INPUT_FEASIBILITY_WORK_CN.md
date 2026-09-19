---
created_at: 2026-06-28
status: work_doc
phase: MTRC2_EXTENDED_CONCENTRATION_WINDOW_DIAGNOSTIC_CONTRACT_OR_INPUT_FEASIBILITY
parent_phase: MTRC1E_RESEARCH_ONLY_BROAD_SIGNAL_REVIEW_OR_NEXT_DIAGNOSTIC_CONTRACT
parent_review: docs/tw_portfolio_decision_model/POLICY_MTRC1E_RESEARCH_ONLY_BROAD_SIGNAL_REVIEW_OR_NEXT_DIAGNOSTIC_CONTRACT_REVIEW_CN.md
readonly_only: true
simulation_only: true
production_allowed: false
model_training_authorized: false
model_inference_authorized: false
model_signal_artifact_authorized: false
diagnostic_contract_authorized: true
input_feasibility_authorized: true
order_intent_authorized: false
replay_result_authorized: false
return_replay_authorized: false
strategy_tuning_authorized: false
new_candidate_authorized: false
provider_publish_allowed: false
accepted_latest_switch_allowed: false
frontend_default_switch_allowed: false
broker_authorized: false
---

# POLICY_MTRC2_EXTENDED_CONCENTRATION_WINDOW_DIAGNOSTIC_CONTRACT_OR_INPUT_FEASIBILITY_WORK_CN

## 1. 目标

MTRC2 只做一件事：

```text
基于 MTRC1D/MTRC1E 已通过的 S2C research-only broad ModelSignalArtifact，
盘点是否存在合法的 same-candidate / same-parameter / same-signal diagnostic 输入，
并冻结 extended concentration/window diagnostic 的输入可行性与下一步边界。
```

本阶段不得直接运行收益 replay，不得生成 OrderIntent、ReplayResult，不得实现 concentration/window diagnostic 计算，不得进入 production readiness。

MTRC2 必须回答：

```text
1. MTRC1D broad signal 是否是合法 diagnostic signal input；
2. 是否存在同候选 M2_hold_rank_buffer_100、同参数 rank_buffer=100、同 signal lineage=S2C/MTRC1D broad 的既有 OrderIntent / ReplayResult / ledger 输入；
3. 若不存在，缺口是什么，下一步应 STOP 还是开 repair/build contract；
4. 若存在，下一步 diagnostic 可以消费哪些 artifact，必须输出哪些表；
5. 无论是否存在，不得把旧 MTR2_R/E3 replay 伪装成 S2C/MTRC1D lineage；
6. 不得把本阶段输出写成收益结论或 production readiness。
```

## 2. 必读输入

执行者必须读取：

```text
docs/tw_portfolio_decision_model/POLICY_MTRC_RESEARCH_ONLY_CONTINUATION_MAINLINE_CN.md
docs/tw_portfolio_decision_model/POLICY_MTRC1D_RESEARCH_ONLY_BROAD_FULL_RANK_SIGNAL_BUILD_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_MTRC1E_RESEARCH_ONLY_BROAD_SIGNAL_REVIEW_OR_NEXT_DIAGNOSTIC_CONTRACT_WORK_CN.md
docs/tw_portfolio_decision_model/POLICY_MTRC1E_RESEARCH_ONLY_BROAD_SIGNAL_REVIEW_OR_NEXT_DIAGNOSTIC_CONTRACT_EXECUTION_REPORT_CN.md
docs/tw_portfolio_decision_model/POLICY_MTRC1E_RESEARCH_ONLY_BROAD_SIGNAL_REVIEW_OR_NEXT_DIAGNOSTIC_CONTRACT_REVIEW_CN.md
docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md
docs/tw_modular_contracts/NEW_MODEL_AND_STRATEGY_DEVELOPER_GUIDE_CN.md
docs/tw_modular_contracts/MODEL_SIGNAL_CONTRACT_CN.md
docs/tw_modular_contracts/MODEL_SIGNAL_EXTENSION_SCHEMA_CN.md
docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md
docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md
docs/tw_modular_contracts/STRATEGY_RULE_CONTRACT_CN.md
```

必须检查 MTRC1E contract：

```text
data_tw/experiments/policy_mtr_research_only_continuation/mtrc1e_research_only_broad_signal_review_or_next_diagnostic_contract/mtrc2_gate_contract.csv
data_tw/experiments/policy_mtr_research_only_continuation/mtrc1e_research_only_broad_signal_review_or_next_diagnostic_contract/downstream_diagnostic_input_contract.csv
data_tw/experiments/policy_mtr_research_only_continuation/mtrc1e_research_only_broad_signal_review_or_next_diagnostic_contract/downstream_diagnostic_output_contract.csv
data_tw/experiments/policy_mtr_research_only_continuation/mtrc1e_research_only_broad_signal_review_or_next_diagnostic_contract/mtrc2_forbidden_actions_contract.csv
data_tw/experiments/policy_mtr_research_only_continuation/mtrc1e_research_only_broad_signal_review_or_next_diagnostic_contract/validator_report.json
data_tw/experiments/policy_mtr_research_only_continuation/mtrc1e_research_only_broad_signal_review_or_next_diagnostic_contract/mtrc2_work_recommendation.md
```

必须检查 MTRC1D broad signal：

```text
data_tw/experiments/policy_mtr_research_only_continuation/mtrc1d_research_only_broad_full_rank_signal_build/manifest.json
data_tw/experiments/policy_mtr_research_only_continuation/mtrc1d_research_only_broad_full_rank_signal_build/signals.csv
data_tw/experiments/policy_mtr_research_only_continuation/mtrc1d_research_only_broad_full_rank_signal_build/validator_report.json
```

允许盘点旧 MTR 产物，但只能用于 lineage feasibility，不得直接作为 S2C 等价输入：

```text
data_tw/experiments/policy_mtr_mechanism_transfer/mtr2_r_broad_full_rank_visibility_repair/order_intent_artifact_index.csv
data_tw/experiments/policy_mtr_mechanism_transfer/mtr2_r_broad_full_rank_visibility_repair/replay_artifact_index.csv
data_tw/experiments/policy_mtr_mechanism_transfer/mtr2_r_broad_full_rank_visibility_repair/manifest.json
data_tw/experiments/policy_mtr_mechanism_transfer/mtr3_robustness_window_regime_and_mechanism_attribution/manifest.json
data_tw/experiments/policy_mtr_mechanism_transfer/mtr5_extended_oos_shadow_and_production_readiness_diagnostic/extended_lineage_inventory.csv
data_tw/experiments/policy_mtr_mechanism_transfer/mtr5_extended_oos_shadow_and_production_readiness_diagnostic/data_lineage_blocker.md
```

## 3. 允许输出

输出目录：

```text
data_tw/experiments/policy_mtr_research_only_continuation/mtrc2_extended_concentration_window_diagnostic_contract_or_input_feasibility/
```

允许生成：

```text
manifest.json
mtrc1d_signal_input_readiness.csv
same_candidate_same_parameter_input_inventory.csv
order_intent_input_feasibility.csv
replay_result_input_feasibility.csv
ledger_input_feasibility.csv
old_mtr_lineage_non_equivalence_audit.csv
diagnostic_input_gap_analysis.csv
mtrc2_diagnostic_contract.csv
mtrc2_output_schema_contract.csv
mtrc2_stop_or_repair_decision.csv
forbidden_scope_audit.csv
production_boundary_audit.csv
validator_report.json
diagnostic_findings.md
mtrc2_next_step_recommendation.md
```

执行报告：

```text
docs/tw_portfolio_decision_model/POLICY_MTRC2_EXTENDED_CONCENTRATION_WINDOW_DIAGNOSTIC_CONTRACT_OR_INPUT_FEASIBILITY_EXECUTION_REPORT_CN.md
```

审查报告：

```text
docs/tw_portfolio_decision_model/POLICY_MTRC2_EXTENDED_CONCENTRATION_WINDOW_DIAGNOSTIC_CONTRACT_OR_INPUT_FEASIBILITY_REVIEW_CN.md
```

允许新增 contract/audit builder：

```text
scripts/build_tw_policy_mtrc2_extended_concentration_window_diagnostic_contract_or_input_feasibility.py
```

builder 只能写 MTRC2 输出目录和 MTRC2 执行报告，不得写 MTRC1D/MTRC1E 产物，不得写 registry、configs、provider、latest、frontend、API、Agent、daily 或 production 目录。

## 4. 必做检查

### 4.1 MTRC1D signal readiness

必须确认：

```text
artifact_type = policy_mtrc1d_research_only_broad_full_rank_signal_build 或等价声明；
lineage_id = S2C_SPLIT_ALIGNED_FRESH_LTR；
model_name = s2c_split_aligned_fresh_ltr_research_only_broad_full_rank_mtrc1d；
validator verdict = PASS_READY_FOR_MTRC1E...；
signal rows = 169366；
top50 rows = 113000；
non_top50 rows = 56366；
non_top50 buy hard fail = pass；
S2C non-equivalent to MTR2_R/E3；
MTR5 blocker not cleared。
```

### 4.2 same-candidate / same-parameter / same-signal inventory

必须盘点候选输入是否同时满足：

```text
candidate_id = M2_hold_rank_buffer_100
strategy_rule = mechanism_transfer_top50_cost_aware_v1 或合同声明的同一候选规则
rank_buffer = 100
signal_artifact = MTRC1D broad ModelSignalArtifact
lineage_id = S2C_SPLIT_ALIGNED_FRESH_LTR
non_top50_buy_validator_pass = true
readonly_only = true
simulation_only = true
production_allowed = false
```

旧 MTR2_R/E3 输入若满足 M2 参数但 signal lineage 不同，必须标记：

```text
same_candidate = true/false
same_parameter = true/false
same_signal = false
usable_for_mtrc2_diagnostic = false
reason = old MTR2_R/E3 lineage is not S2C/MTRC1D lineage
```

### 4.3 若缺合法输入

若没有同时满足 same candidate、same parameter、same signal 的 OrderIntent / ReplayResult / ledger 输入，MTRC2 不得自行生成或选择 replay artifact，必须输出：

```text
STOP_NO_LEGAL_SAME_SIGNAL_DIAGNOSTIC_INPUT
```

或如果存在明确、狭窄、只读的下一步可修复路线：

```text
PASS_READY_FOR_MTRC2_R_SAME_SIGNAL_ORDER_REPLAY_INPUT_BUILD_CONTRACT
```

repair/build contract 必须仍然不允许直接收益结论或 production readiness。

## 5. MTRC2 diagnostic contract 内容

若后续进入真实 diagnostic，必须至少输出：

```text
symbol_concentration_diagnostic.csv
event_concentration_diagnostic.csv
monthly_negative_inventory.csv
daily_rolling_window_attribution.csv
risk_off_regime_attribution.csv
drawdown_segment_attribution.csv
turnover_fee_tax_decomposition.csv
non_top50_buy_validator_report.json
diagnostic_summary.md
```

但 MTRC2 当前阶段只能冻结上述 output schema，不得实际计算这些表。

## 6. 禁止动作

MTRC2 当前阶段明确禁止：

```text
训练模型
调参
模型 inference
重新计算 LTR score
生成或修改 ModelSignalArtifact
生成 OrderIntentArtifact
生成 ReplayResultArtifact
运行收益 replay
实现 concentration/window diagnostic 计算
新增策略候选
修改 M2_hold_rank_buffer_100 参数
选择或调参策略
把旧 MTR2_R/E3 replay 当成 S2C/MTRC1D replay
把 diagnostic 结果写成收益结论、收益承诺或 production readiness
修改 production/default/latest/provider/frontend/API/Agent/daily
修改 registry/config default
provider refresh / publish
accepted latest switch
monitor config / scan / alerts write
broker / quick-trade / real order
target_weight / target_position / quantity instruction
将 S2C 描述为 MTR2_R/E3 等价
解除 MTR5 clean_extended_lineage_found=false blocker
```

## 7. PASS / STOP 标准

允许 verdict：

```text
PASS_READY_FOR_MTRC2_R_SAME_SIGNAL_ORDER_REPLAY_INPUT_BUILD_CONTRACT
PASS_READY_FOR_MTRC3_EXTENDED_CONCENTRATION_WINDOW_DIAGNOSTIC_IF_LEGAL_INPUT_EXISTS
STOP_NO_LEGAL_SAME_SIGNAL_DIAGNOSTIC_INPUT
FAIL_NEEDS_MTRC2_R_INPUT_FEASIBILITY_REPAIR
```

`PASS_READY_FOR_MTRC3...` 只有在已经存在合法 same-candidate / same-parameter / same-signal 的 OrderIntent / ReplayResult / ledger 输入时才允许。

如果只有 MTRC1D broad signal，而没有同 signal 的 order/replay/ledger，推荐 verdict 是：

```text
PASS_READY_FOR_MTRC2_R_SAME_SIGNAL_ORDER_REPLAY_INPUT_BUILD_CONTRACT
```

或若无法合法构建：

```text
STOP_NO_LEGAL_SAME_SIGNAL_DIAGNOSTIC_INPUT
```

## 8. 下一阶段边界

若 MTRC2 建议 repair/build contract，下一步只能是：

```text
MTRC2_R_SAME_SIGNAL_ORDER_REPLAY_INPUT_BUILD_CONTRACT
```

该阶段也必须先写合同，不得直接跑收益 replay；必须声明如何基于 MTRC1D broad signal、M2_hold_rank_buffer_100、rank_buffer=100 生成或定位 readonly input，并保留 non_top50 buy hard fail。
