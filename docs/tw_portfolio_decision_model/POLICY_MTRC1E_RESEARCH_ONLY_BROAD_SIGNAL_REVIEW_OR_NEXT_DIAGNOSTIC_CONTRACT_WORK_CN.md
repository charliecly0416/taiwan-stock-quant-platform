---
created_at: 2026-06-28
status: work_doc
phase: MTRC1E_RESEARCH_ONLY_BROAD_SIGNAL_REVIEW_OR_NEXT_DIAGNOSTIC_CONTRACT
parent_phase: MTRC1D_RESEARCH_ONLY_BROAD_FULL_RANK_SIGNAL_BUILD
parent_review: docs/tw_portfolio_decision_model/POLICY_MTRC1D_RESEARCH_ONLY_BROAD_FULL_RANK_SIGNAL_BUILD_REVIEW_CN.md
readonly_only: true
simulation_only: true
production_allowed: false
model_training_authorized: false
model_inference_authorized: false
model_signal_artifact_authorized: false
diagnostic_contract_authorized: true
strategy_replay_authorized: false
order_intent_authorized: false
replay_result_authorized: false
strategy_tuning_authorized: false
new_candidate_authorized: false
provider_publish_allowed: false
accepted_latest_switch_allowed: false
frontend_default_switch_allowed: false
broker_authorized: false
---

# POLICY_MTRC1E_RESEARCH_ONLY_BROAD_SIGNAL_REVIEW_OR_NEXT_DIAGNOSTIC_CONTRACT_WORK_CN

## 1. 目标

MTRC1E 只做一件事：

```text
审查 MTRC1D research-only broad full-rank ModelSignalArtifact 是否足以支持下一阶段 concentration/window diagnostic，
并冻结 MTRC2 diagnostic 的输入、输出、gate 与禁止项合同。
```

本阶段不得生成 OrderIntent、ReplayResult，不得跑收益 replay，不得实现 MTRC2，不得生产化。MTRC1E 的输出是“下一步 diagnostic contract / readiness decision”，不是策略效果结论。

MTRC1E 必须回答：

```text
1. MTRC1D broad signal 是否仍保持 top50 LTR 等价与 non-top50 visibility-only 边界；
2. MTRC1D broad signal 是否足以作为 MTRC2 diagnostic 的标准 ModelSignal 输入；
3. MTRC2 若后续授权，必须消费哪些 artifact；
4. MTRC2 可以输出哪些 concentration/window diagnostic artifact；
5. MTRC2 必须禁止哪些 replay、收益结论、生产接入或策略调参动作；
6. 当前是否存在必须先 repair 的 blocker。
```

## 2. 必读输入

执行者必须读取：

```text
docs/tw_portfolio_decision_model/POLICY_MTRC_RESEARCH_ONLY_CONTINUATION_MAINLINE_CN.md
docs/tw_portfolio_decision_model/POLICY_MTRC1B_RESEARCH_ONLY_EXTENDED_TOP50_LTR_SIGNAL_BUILD_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_MTRC1C_RESEARCH_ONLY_BROAD_BRIDGE_CONTRACT_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_MTRC1D_RESEARCH_ONLY_BROAD_FULL_RANK_SIGNAL_BUILD_WORK_CN.md
docs/tw_portfolio_decision_model/POLICY_MTRC1D_RESEARCH_ONLY_BROAD_FULL_RANK_SIGNAL_BUILD_EXECUTION_REPORT_CN.md
docs/tw_portfolio_decision_model/POLICY_MTRC1D_RESEARCH_ONLY_BROAD_FULL_RANK_SIGNAL_BUILD_REVIEW_CN.md
docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md
docs/tw_modular_contracts/NEW_MODEL_AND_STRATEGY_DEVELOPER_GUIDE_CN.md
docs/tw_modular_contracts/MODEL_SIGNAL_CONTRACT_CN.md
docs/tw_modular_contracts/MODEL_SIGNAL_EXTENSION_SCHEMA_CN.md
docs/tw_modular_contracts/NEW_MODEL_REVIEWER_CHECKLIST_CN.md
```

必须检查 MTRC1D artifact：

```text
data_tw/experiments/policy_mtr_research_only_continuation/mtrc1d_research_only_broad_full_rank_signal_build/manifest.json
data_tw/experiments/policy_mtr_research_only_continuation/mtrc1d_research_only_broad_full_rank_signal_build/signals.csv
data_tw/experiments/policy_mtr_research_only_continuation/mtrc1d_research_only_broad_full_rank_signal_build/schema.json
data_tw/experiments/policy_mtr_research_only_continuation/mtrc1d_research_only_broad_full_rank_signal_build/validator_report.json
data_tw/experiments/policy_mtr_research_only_continuation/mtrc1d_research_only_broad_full_rank_signal_build/top50_equivalence_audit.csv
data_tw/experiments/policy_mtr_research_only_continuation/mtrc1d_research_only_broad_full_rank_signal_build/non_top50_visibility_audit.csv
data_tw/experiments/policy_mtr_research_only_continuation/mtrc1d_research_only_broad_full_rank_signal_build/non_top50_buy_hard_fail_audit.csv
data_tw/experiments/policy_mtr_research_only_continuation/mtrc1d_research_only_broad_full_rank_signal_build/extension_schema_audit.csv
data_tw/experiments/policy_mtr_research_only_continuation/mtrc1d_research_only_broad_full_rank_signal_build/lineage_boundary_audit.csv
data_tw/experiments/policy_mtr_research_only_continuation/mtrc1d_research_only_broad_full_rank_signal_build/negative_samples/
```

## 3. MTRC1E 允许输出

输出目录：

```text
data_tw/experiments/policy_mtr_research_only_continuation/mtrc1e_research_only_broad_signal_review_or_next_diagnostic_contract/
```

允许生成：

```text
manifest.json
broad_signal_readiness_audit.csv
top50_equivalence_recheck.csv
non_top50_boundary_recheck.csv
negative_sample_coverage_audit.csv
extension_schema_recheck.csv
downstream_diagnostic_input_contract.csv
downstream_diagnostic_output_contract.csv
mtrc2_gate_contract.csv
mtrc2_forbidden_actions_contract.csv
forbidden_scope_audit.csv
production_boundary_audit.csv
validator_report.json
diagnostic_findings.md
mtrc2_work_recommendation.md
```

执行报告：

```text
docs/tw_portfolio_decision_model/POLICY_MTRC1E_RESEARCH_ONLY_BROAD_SIGNAL_REVIEW_OR_NEXT_DIAGNOSTIC_CONTRACT_EXECUTION_REPORT_CN.md
```

审查报告：

```text
docs/tw_portfolio_decision_model/POLICY_MTRC1E_RESEARCH_ONLY_BROAD_SIGNAL_REVIEW_OR_NEXT_DIAGNOSTIC_CONTRACT_REVIEW_CN.md
```

允许新增 contract/audit builder：

```text
scripts/build_tw_policy_mtrc1e_research_only_broad_signal_review_contract.py
```

builder 只能写 MTRC1E 输出目录和 MTRC1E 执行报告，不得写 MTRC1D 产物，不得写 registry、configs、provider、latest、frontend、API、Agent、daily 或 production 目录。

## 4. Readiness recheck 要求

MTRC1E 必须基于 MTRC1D artifact 重新检查：

```text
required_core_fields_present
date_instrument_unique
signal_rows = 169366
date_range = 2017-01-10..2026-05-07
date_count = 2260
top50_rows = 113000
non_top50_rows = 56366
top50_buy_score_equal_mtrc1b
top50_raw_score_equal_mtrc1b
top50_score_rank_equal_mtrc1b
top50_candidate_rank_equal_mtrc1b_and_s2b
top50_full_qlib_rank_equal_mtrc1b_and_s2b
non_top50_rows_from_s2b_rank_gt50
non_top50_buy_score_raw_score_score_rank_null
non_top50_buy_eligible_false
extension_fields_declared_and_ranking_allowed_false
negative_samples_exist_and_fail_as_expected
lineage_s2c_research_only_non_equivalent_to_mtr2r_e3
no_order_intent_or_replay_result_or_return_replay
no_production_default_latest_provider_frontend_api_agent_daily_write
```

若任一 hard gate 失败，MTRC1E 必须给出：

```text
FAIL_NEEDS_MTRC1D_R_ARTIFACT_REPAIR
```

或若 broad signal 本身不可合法用于后续 diagnostic：

```text
STOP_NO_VALID_DIAGNOSTIC_INPUT
```

## 5. MTRC2 diagnostic 合同要求

MTRC1E 若建议进入 MTRC2，必须冻结 MTRC2 仅可做的事情：

```text
MTRC2 只能做 extended concentration / window diagnostic。
MTRC2 可以消费 MTRC1D broad ModelSignalArtifact、已存在且另行声明的 M2_100 research-only candidate/order/replay lineage artifact 或合同化输入。
MTRC2 必须先检查 same candidate、same M2 parameter、same signal artifact、same non_top50 buy hard fail。
MTRC2 可以输出 concentration、symbol/event attribution、monthly/rolling/risk-off/drawdown diagnostic tables。
MTRC2 不得把 diagnostic 结果写成 production readiness 或收益承诺。
```

MTRC2 gate 至少包括：

```text
same_candidate_m2_hold_rank_buffer_100
same_parameter_rank_buffer_100
same_signal_artifact_mtrc1d_broad
non_top50_buy_validator_pass
order_intent_input_contract_declared_if_needed
replay_result_input_contract_declared_if_needed
no_strategy_tuning
no_new_candidate
no_replay_return_conclusion_without_predeclared_replay_contract
no_production_or_default_write
```

重要限制：

```text
MTRC1E 不得直接替 MTRC2 选择 replay artifact。
如果 MTRC2 需要 OrderIntent / ReplayResult / ledger，必须在 MTRC2 work doc 中另行声明来源与校验。
如果不存在合法的 same-candidate same-parameter replay lineage，MTRC2 必须 STOP 或先开 repair，不得临时生成收益 replay。
```

## 6. 禁止动作

MTRC1E 明确禁止：

```text
训练模型
调参
模型 inference
重新计算 LTR score
生成或修改 broad signals.csv
生成 OrderIntentArtifact
生成 ReplayResultArtifact
运行收益 replay
新增策略候选
修改 M2_hold_rank_buffer_100 参数
选择或调参策略
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

## 7. PASS / FAIL 标准

PASS 需要同时满足：

```text
MTRC1D broad signal recheck 全部通过；
MTRC2 diagnostic input/output/gate/forbidden-actions contract 完整；
明确 MTRC2 不得自动做 replay 或 production readiness；
明确 S2C 仍不等价于 MTR2_R/E3；
forbidden scope 和 production boundary audit 干净。
```

允许 verdict：

```text
PASS_READY_FOR_MTRC2_EXTENDED_CONCENTRATION_WINDOW_DIAGNOSTIC_CONTRACT_OR_INPUT_FEASIBILITY
PASS_WITH_CONDITIONS_READY_FOR_MTRC1E_R_NARROW_REPAIR
FAIL_NEEDS_MTRC1D_R_ARTIFACT_REPAIR
STOP_NO_VALID_DIAGNOSTIC_INPUT
```

## 8. 下一阶段边界

若 MTRC1E PASS，下一步只能建议：

```text
MTRC2_EXTENDED_CONCENTRATION_WINDOW_DIAGNOSTIC_CONTRACT_OR_INPUT_FEASIBILITY
```

MTRC2 仍然不能直接跑收益 replay。它必须先确认是否存在合法的 same-candidate、same-parameter、same-signal lineage 的 diagnostic 输入；如果不存在，必须 STOP 或开 repair。
