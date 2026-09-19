---
created_at: 2026-06-28
status: work_doc
phase: MTRC0_CLEAN_EXTENDED_LINEAGE_CONTRACT_AND_FEASIBILITY
parent_mainline: docs/tw_portfolio_decision_model/POLICY_MTRC_RESEARCH_ONLY_CONTINUATION_MAINLINE_CN.md
readonly_only: true
simulation_only: true
production_allowed: false
model_training_authorized: false
strategy_tuning_authorized: false
new_candidate_authorized: false
replay_authorized: false
provider_publish_allowed: false
accepted_latest_switch_allowed: false
frontend_default_switch_allowed: false
broker_authorized: false
---

# POLICY_MTRC0_CLEAN_EXTENDED_LINEAGE_CONTRACT_AND_FEASIBILITY_WORK_CN

## 1. 目标

MTRC0 是 MTR5 后的 research-only continuation 第一阶段。

目标：

```text
合同化 clean extended lineage 的定义；
盘点现有 extended_oos / shadow / signal artifacts；
判断是否可以合法进入 MTRC1 extended lineage build / replay；
或者明确 STOP_NO_CLEAN_LINEAGE_PATH。
```

MTRC0 不跑收益 replay，不生成 OrderIntent，不生成 ReplayResult，不修改策略。

## 2. 必读输入

执行者必须读取：

```text
docs/tw_portfolio_decision_model/POLICY_MTRC_RESEARCH_ONLY_CONTINUATION_MAINLINE_CN.md
docs/tw_portfolio_decision_model/POLICY_MTR5_EXTENDED_OOS_SHADOW_AND_PRODUCTION_READINESS_DIAGNOSTIC_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_MTR5_EXTENDED_OOS_SHADOW_AND_PRODUCTION_READINESS_DIAGNOSTIC_EXECUTION_REPORT_CN.md
data_tw/experiments/policy_mtr_mechanism_transfer/mtr5_extended_oos_shadow_and_production_readiness_diagnostic/manifest.json
data_tw/experiments/policy_mtr_mechanism_transfer/mtr5_extended_oos_shadow_and_production_readiness_diagnostic/extended_lineage_inventory.csv
data_tw/experiments/policy_mtr_mechanism_transfer/mtr5_extended_oos_shadow_and_production_readiness_diagnostic/data_lineage_blocker.md
docs/tw_portfolio_decision_model/POLICY_MTR4_READINESS_DESIGN_AND_EXTENDED_EVIDENCE_CONTRACT_REVIEW_CN.md
data_tw/experiments/policy_mtr_mechanism_transfer/mtr4_readiness_design_and_extended_evidence_contract/*.csv
docs/tw_portfolio_decision_model/POLICY_MTR2_R_BROAD_FULL_RANK_VISIBILITY_REPAIR_REVIEW_CN.md
data_tw/experiments/policy_mtr_mechanism_transfer/mtr2_r_broad_full_rank_visibility_repair/manifest.json
data_tw/artifacts/signals/e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025_broad_full_rank_mtr2_r/r1_broad_full_rank_visibility_repair_20260628/manifest.json
docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md
docs/tw_modular_contracts/STRATEGY_RULE_CONTRACT_CN.md
docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md
docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md
docs/tw_modular_contracts/NEW_STRATEGY_REVIEWER_CHECKLIST_CN.md
```

还必须盘点：

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/**/manifest.json
data_tw/artifacts/signals/**/manifest.json
data_tw/experiments/policy_mtr_mechanism_transfer/**/manifest.json
```

## 3. 输出目录与文件

输出目录：

```text
data_tw/experiments/policy_mtr_research_only_continuation/mtrc0_clean_extended_lineage_contract/
```

必须生成：

```text
manifest.json
clean_lineage_definition_contract.csv
source_artifact_inventory.csv
candidate_bridge_feasibility_matrix.csv
required_inputs_for_mtrc1.csv
non_equivalence_reason_catalog.csv
production_boundary_audit.csv
forbidden_scope_audit.csv
validator_report.json
diagnostic_findings.md
mtrc1_work_recommendation.md
```

执行报告：

```text
docs/tw_portfolio_decision_model/POLICY_MTRC0_CLEAN_EXTENDED_LINEAGE_CONTRACT_AND_FEASIBILITY_EXECUTION_REPORT_CN.md
```

审查报告：

```text
docs/tw_portfolio_decision_model/POLICY_MTRC0_CLEAN_EXTENDED_LINEAGE_CONTRACT_AND_FEASIBILITY_REVIEW_CN.md
```

允许新增 builder：

```text
scripts/build_tw_policy_mtrc0_clean_extended_lineage_contract.py
```

脚本只能写 MTRC0 输出目录和执行报告。

## 4. Clean Lineage 定义

`clean_lineage_definition_contract.csv` 必须包含以下 hard requirements：

```text
same_candidate = M2_hold_rank_buffer_100
same_m2_parameter = hold_rank_buffer_100, max buy/sell semantics unchanged
same_baseline = baseline_top50_exit_one_worst_sell
same_signal_semantics = qlib candidate_rank/full_qlib_rank + top50 LTR buy_score
same_broad_full_rank_visibility = non-top50 rows only for hold/sell visibility
top50_ltr_equivalence = top50 buy_score must match source top50 LTR artifact
non_top50_buy_hard_fail = candidate_rank missing/nonnumeric/>50 buy fails
same_order_intent_contract = no target/order/broker/cash/nav fields
same_replay_contract = readonly simulated replay only
pit_safe = signal_asof / available_at no future leakage
research_only = no production/default/latest/provider switch
```

每条都必须指定：

```text
requirement_id
requirement
hard_fail_if_missing
evidence_needed_for_mtrc1
```

## 5. Artifact 盘点要求

`source_artifact_inventory.csv` 必须至少包含：

```text
artifact_path
artifact_type
date_start
date_end
model_family
model_name
strategy_rule
candidate_id
has_order_intent
has_replay
has_broad_full_rank
has_top50_ltr
mentions_m2_hold_rank_buffer_100
mentions_broad_full_rank_mtr2_r
readonly_or_shadow
eligible_for_mtrc1
non_equivalence_reason
```

执行者必须重点检查：

```text
extended_oos_qlib_orthogonal_ltr
existing e4/fresh/frozen signal artifacts
MTR2_R broad signal artifact
MTR5 extended_lineage_inventory
```

## 6. Bridge Feasibility Matrix

`candidate_bridge_feasibility_matrix.csv` 必须回答：

```text
是否能从现有标准 top50 LTR signal + qlib full-rank source 构建 research-only extended broad full-rank signal；
需要哪些 source artifact；
是否能证明 PIT；
是否能证明 top50 LTR equivalence；
是否能证明 non-top50 rows 不进入 buy universe；
是否需要新增策略代码；
是否需要新增 replay；
是否可能违反生产边界。
```

允许的 bridge verdict：

```text
ready_for_mtrc1_research_only_build
possible_but_requires_missing_input
not_equivalent_do_not_use
stop_no_clean_path
```

## 7. MTRC1 推荐

若 MTRC0 结论为 ready_for_mtrc1：

`mtrc1_work_recommendation.md` 必须给出下一步：

```text
MTRC1_EXTENDED_BROAD_FULL_RANK_LINEAGE_BUILD_AND_READONLY_REPLAY
```

但仍必须是 research-only。

MTRC1 可以被建议执行的前提：

```text
存在标准可追溯 qlib full-rank source；
存在标准 top50 LTR signal；
两者日期窗口可对齐；
能复刻 MTR2_R 的 top50 equivalence / non-top50 hold-sell-only 语义；
不会修改 accepted latest 或 production defaults。
```

若不满足，必须输出：

```text
STOP_NO_CLEAN_LINEAGE_PATH
```

## 8. Verdict

允许 verdict：

```text
PASS_READY_FOR_MTRC1_EXTENDED_LINEAGE_BUILD_OR_REPLAY
STOP_NO_CLEAN_LINEAGE_PATH
FAIL_NEEDS_MTRC0_REPAIR
```

## 9. 禁止事项

MTRC0 禁止：

```text
跑收益 replay
生成 OrderIntent / ReplayResult
训练模型
调参
新增候选
修改 M2 参数
修改 MTR2_R/MTR3/MTR4/MTR5 输入产物
修改 production/default/frontend/API/Agent/daily/provider/latest
provider publish / accepted latest switch
broker / quick-trade / real order
target_weight / target_position / quantity instruction
```

## 10. 给执行者命令

```text
请执行 MTRC0_CLEAN_EXTENDED_LINEAGE_CONTRACT_AND_FEASIBILITY。
只做 research-only 合同和 lineage 可行性盘点。
不得跑收益 replay，不得生成 OrderIntent/ReplayResult，不得修改生产或已有输入产物。
最终给出 PASS_READY_FOR_MTRC1_EXTENDED_LINEAGE_BUILD_OR_REPLAY / STOP_NO_CLEAN_LINEAGE_PATH / FAIL_NEEDS_MTRC0_REPAIR。
```

## 11. 给审查者 brief

```text
请审查 MTRC0 是否真的证明了 clean extended lineage path。
重点看是否把非等价 extended_oos/shadow 产物误判为可用；
是否要求 same candidate / same M2 parameter / same signal semantics / same contracts；
是否保持 research-only 和 production no-go。
```
