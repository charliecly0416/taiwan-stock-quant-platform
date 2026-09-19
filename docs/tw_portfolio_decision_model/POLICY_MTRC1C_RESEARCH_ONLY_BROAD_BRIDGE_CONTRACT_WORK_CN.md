---
created_at: 2026-06-28
status: work_doc
phase: MTRC1C_RESEARCH_ONLY_BROAD_BRIDGE_CONTRACT
parent_phase: MTRC1B_RESEARCH_ONLY_EXTENDED_TOP50_LTR_SIGNAL_BUILD
parent_review: docs/tw_portfolio_decision_model/POLICY_MTRC1B_RESEARCH_ONLY_EXTENDED_TOP50_LTR_SIGNAL_BUILD_REVIEW_CN.md
readonly_only: true
simulation_only: true
production_allowed: false
model_training_authorized: false
model_inference_authorized: false
model_signal_artifact_authorized: false
broad_bridge_build_authorized: false
strategy_replay_authorized: false
strategy_tuning_authorized: false
new_candidate_authorized: false
provider_publish_allowed: false
accepted_latest_switch_allowed: false
frontend_default_switch_allowed: false
broker_authorized: false
---

# POLICY_MTRC1C_RESEARCH_ONLY_BROAD_BRIDGE_CONTRACT_WORK_CN

## 1. 目标

MTRC1C 只做一件事：

```text
为 S2C_SPLIT_ALIGNED_FRESH_LTR research-only top50 signal 设计 broad full-rank visibility bridge 的合同、可行性检查和 validator 规则。
```

本阶段不得直接构建 broad bridge，不得生成新的 `signals.csv` broad artifact，不得跑 OrderIntent、ReplayResult 或收益 replay。MTRC1C 的产物只能回答：

```text
如果后续另行授权 MTRC1D，应该如何合法构建 research-only broad full-rank signal；
如何保证 top50 LTR 等价；
如何保证 non-top50 rows 只能用于 hold/sell visibility；
如何 hard-fail non-top50 buy；
当前是否存在足够输入进入 MTRC1D。
```

## 2. 必读输入

执行者必须读取：

```text
docs/tw_portfolio_decision_model/POLICY_MTRC_RESEARCH_ONLY_CONTINUATION_MAINLINE_CN.md
docs/tw_portfolio_decision_model/POLICY_MTRC1A_R_LTR_INFERENCE_LINEAGE_REPAIR_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_MTRC1B_RESEARCH_ONLY_EXTENDED_TOP50_LTR_SIGNAL_BUILD_WORK_CN.md
docs/tw_portfolio_decision_model/POLICY_MTRC1B_RESEARCH_ONLY_EXTENDED_TOP50_LTR_SIGNAL_BUILD_EXECUTION_REPORT_CN.md
docs/tw_portfolio_decision_model/POLICY_MTRC1B_RESEARCH_ONLY_EXTENDED_TOP50_LTR_SIGNAL_BUILD_REVIEW_CN.md
docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md
docs/tw_modular_contracts/NEW_MODEL_AND_STRATEGY_DEVELOPER_GUIDE_CN.md
docs/tw_modular_contracts/MODEL_SIGNAL_CONTRACT_CN.md
docs/tw_modular_contracts/MODEL_SIGNAL_EXTENSION_SCHEMA_CN.md
docs/tw_modular_contracts/NEW_MODEL_REVIEWER_CHECKLIST_CN.md
```

执行者必须检查但不得修改：

```text
data_tw/experiments/policy_mtr_research_only_continuation/mtrc1b_research_only_extended_top50_ltr_signal_build/manifest.json
data_tw/experiments/policy_mtr_research_only_continuation/mtrc1b_research_only_extended_top50_ltr_signal_build/signals.csv
data_tw/experiments/policy_mtr_research_only_continuation/mtrc1b_research_only_extended_top50_ltr_signal_build/schema.json
data_tw/experiments/policy_mtr_research_only_continuation/mtrc1b_research_only_extended_top50_ltr_signal_build/validator_report.json
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2b_fresh_qlib_training/phase_s2b_post_filter_score_rank.csv
```

若发现还需要其他 qlib full-rank source，必须只记录为候选输入和 blocker，不得在本阶段生成 bridge。

## 3. 当前已知事实

MTRC1B 已通过审查：

```text
artifact = data_tw/experiments/policy_mtr_research_only_continuation/mtrc1b_research_only_extended_top50_ltr_signal_build/
signal lineage = S2C_SPLIT_ALIGNED_FRESH_LTR
rows = 113000
date_range = 2017-01-10..2026-05-07
rows_per_date = 50
duplicate date,instrument = 0
forbidden fields absent
```

必须保留的限制：

```text
S2C 是新的 research lineage，不等价于 MTR2_R/E3。
S2C 不得用于解除 MTR5 clean_extended_lineage_found=false blocker。
MTRC1B 是 top50-only LTR signal，不含 broad full-rank visibility。
```

## 4. Broad Bridge 合同原则

后续若进入 MTRC1D，broad bridge 必须遵守：

```text
top50 rows:
  candidate_rank 必须等于 S2C qlib base rank
  full_qlib_rank 必须等于 S2C qlib base full-rank source
  buy_score/raw_score/score_rank 必须与 MTRC1B top50 signal 等价
  LTR 只允许在 qlib top50 内决定买入优先级

non-top50 rows:
  candidate_rank 必须大于 50 或明确标记为非候选
  full_qlib_rank 必须来自同一 S2C qlib full-rank source
  不得拥有 LTR buy priority
  不得参与 buy universe
  只能用于既有持仓的 hold/sell visibility、exit boundary 或 diagnostic
```

`buy_score` 对 non-top50 rows 的处理必须在 MTRC1C 明确二选一：

```text
方案 A: non-top50 buy_score/raw_score/score_rank 为空，并由 validator 证明任何策略不得读取其买入分数。
方案 B: non-top50 buy_score/raw_score 填 qlib base score 或 sentinel extension，但必须不允许 ranking/buy consumer 使用。
```

除非 MTRC1C 给出更强理由，默认推荐方案 A，避免把 qlib broad score 误解为 LTR buy priority。

## 5. 允许输出

输出目录：

```text
data_tw/experiments/policy_mtr_research_only_continuation/mtrc1c_research_only_broad_bridge_contract/
```

允许生成：

```text
manifest.json
broad_bridge_contract.csv
qlib_full_rank_source_contract.csv
top50_equivalence_contract.csv
non_top50_visibility_contract.csv
non_top50_buy_hard_fail_contract.csv
model_signal_extension_contract.csv
candidate_input_inventory.csv
feasibility_gate.csv
forbidden_scope_audit.csv
production_boundary_audit.csv
validator_design.json
validator_report.json
diagnostic_findings.md
mtrc1d_work_recommendation.md
```

执行报告：

```text
docs/tw_portfolio_decision_model/POLICY_MTRC1C_RESEARCH_ONLY_BROAD_BRIDGE_CONTRACT_EXECUTION_REPORT_CN.md
```

审查报告：

```text
docs/tw_portfolio_decision_model/POLICY_MTRC1C_RESEARCH_ONLY_BROAD_BRIDGE_CONTRACT_REVIEW_CN.md
```

允许新增 contract/audit builder：

```text
scripts/build_tw_policy_mtrc1c_research_only_broad_bridge_contract.py
```

builder 只能写 MTRC1C 输出目录和执行报告，不得写 MTRC1B 产物，不得写 registry、configs、provider、latest、frontend、API、Agent、daily 或 production 目录。

## 6. 必须回答的问题

MTRC1C 必须逐项回答：

```text
1. 哪个 qlib full-rank source 可以作为 S2C broad bridge 的唯一 rank source？
2. 该 source 是否覆盖 MTRC1B 的 date range？
3. 该 source 是否能按 date,instrument 与 MTRC1B top50 rows 对齐？
4. top50 内 candidate_rank/full_qlib_rank 是否能与 MTRC1B 保持等价？
5. top50 内 buy_score/raw_score/score_rank 如何保持 MTRC1B 等价？
6. non-top50 rows 后续若生成，应如何标记为 visibility-only？
7. validator 如何 hard-fail non-top50 buy？
8. 是否需要 ext_* 字段？若需要，每个字段的 semantic_role、allowed_consumers、ranking_allowed 如何声明？
9. MTRC1D 若执行，应构建什么，不应构建什么？
10. 当前是否存在必须先 repair 的 blocker？
```

## 7. Validator 设计要求

`validator_design.json` 至少定义以下 hard gates：

```text
required_core_fields_present
top50_rows_equal_mtrc1b_by_date_instrument
top50_buy_score_equal_mtrc1b
top50_raw_score_equal_mtrc1b
top50_score_rank_equal_mtrc1b
top50_candidate_rank_equal_s2c_qlib_rank
top50_full_qlib_rank_equal_s2c_qlib_rank
non_top50_candidate_rank_gt_50_or_non_candidate
non_top50_not_buy_eligible
non_top50_ltr_score_absent_or_forbidden_for_ranking
non_top50_buy_hard_fail_negative_sample
date_instrument_unique
forbidden_fields_absent
available_at_policy_declared
no_order_intent
no_replay_result
no_production_or_default_write
```

若执行者能在本阶段实现 validator dry-run，只能针对合同样本或现有 MTRC1B top50 事实做静态验证，不得生成 broad signal。

## 8. 禁止动作

MTRC1C 明确禁止：

```text
训练模型
调参
模型 inference
生成新的 broad signals.csv
生成 OrderIntentArtifact
生成 ReplayResultArtifact
跑收益 replay
新增策略候选
修改 M2_hold_rank_buffer_100 参数
修改 production/default/latest/provider/frontend/API/Agent/daily
provider refresh / publish
accepted latest switch
monitor config / scan / alerts write
broker / quick-trade / real order
target_weight / target_position / quantity instruction
将 S2C 描述为 MTR2_R/E3 等价
解除 MTR5 clean_extended_lineage_found=false blocker
```

## 9. PASS / FAIL 标准

PASS 需要同时满足：

```text
合同产物齐全；
MTRC1B top50 等价规则明确且可验证；
S2C qlib full-rank source 候选明确；
non-top50 visibility-only 语义明确；
non-top50 buy hard-fail validator 规则明确；
extension schema 若使用则符合 MODEL_SIGNAL_EXTENSION_SCHEMA_CN.md；
forbidden scope 和 production boundary audit 干净；
没有直接 broad build、replay、default/latest/provider/frontend/API/Agent/daily 改动。
```

允许 verdict：

```text
PASS_READY_FOR_MTRC1D_RESEARCH_ONLY_BROAD_FULL_RANK_SIGNAL_BUILD
PASS_WITH_CONDITIONS_READY_FOR_MTRC1D_AFTER_NARROW_REPAIR
FAIL_NEEDS_MTRC1C_R_CONTRACT_REPAIR
STOP_NO_LEGAL_BROAD_BRIDGE_PATH
```

## 10. 下一阶段建议格式

若 PASS，`mtrc1d_work_recommendation.md` 必须给出 MTRC1D 的边界：

```text
MTRC1D 只能构建 research-only broad full-rank ModelSignalArtifact；
top50 rows 必须完全继承 MTRC1B LTR score/rank；
non-top50 rows 必须 visibility-only；
必须先跑 non_top50_buy_hard_fail validator；
不得进入 OrderIntent、ReplayResult、收益 replay 或 production/default/latest/provider/frontend/API/Agent/daily。
```

若 FAIL 或 STOP，必须写明最小 repair 或停止原因，不得建议跳过合同直接 replay。
