---
created_at: 2026-06-28
status: work_doc
phase: MTRC1D_RESEARCH_ONLY_BROAD_FULL_RANK_SIGNAL_BUILD
parent_phase: MTRC1C_RESEARCH_ONLY_BROAD_BRIDGE_CONTRACT
parent_review: docs/tw_portfolio_decision_model/POLICY_MTRC1C_RESEARCH_ONLY_BROAD_BRIDGE_CONTRACT_REVIEW_CN.md
readonly_only: true
simulation_only: true
production_allowed: false
model_training_authorized: false
model_inference_authorized: false
model_signal_artifact_authorized: true
broad_bridge_build_authorized: true
strategy_replay_authorized: false
strategy_tuning_authorized: false
new_candidate_authorized: false
provider_publish_allowed: false
accepted_latest_switch_allowed: false
frontend_default_switch_allowed: false
broker_authorized: false
---

# POLICY_MTRC1D_RESEARCH_ONLY_BROAD_FULL_RANK_SIGNAL_BUILD_WORK_CN

## 1. 目标

MTRC1D 只做一件事：

```text
基于 MTRC1B top50 LTR signal 与 MTRC1C 通过的 broad bridge contract，
构建 research-only broad full-rank ModelSignalArtifact。
```

本阶段允许实际生成 broad `signals.csv`，但只能作为 research-only `ModelSignalArtifact`。不得生成 OrderIntent、ReplayResult，不得运行收益 replay，不得进入 production/default/latest/provider/frontend/API/Agent/daily。

MTRC1D 输出必须证明：

```text
top50 rows 与 MTRC1B 完全等价；
non-top50 rows 只用于 hold/sell visibility 和 diagnostic；
non-top50 rows 不具备 LTR buy priority；
validator 能 hard-fail non-top50 buy；
产物仍是 S2C research-only lineage，不能解除 MTR5 blocker。
```

## 2. 必读输入

执行者必须读取：

```text
docs/tw_portfolio_decision_model/POLICY_MTRC_RESEARCH_ONLY_CONTINUATION_MAINLINE_CN.md
docs/tw_portfolio_decision_model/POLICY_MTRC1B_RESEARCH_ONLY_EXTENDED_TOP50_LTR_SIGNAL_BUILD_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_MTRC1C_RESEARCH_ONLY_BROAD_BRIDGE_CONTRACT_WORK_CN.md
docs/tw_portfolio_decision_model/POLICY_MTRC1C_RESEARCH_ONLY_BROAD_BRIDGE_CONTRACT_EXECUTION_REPORT_CN.md
docs/tw_portfolio_decision_model/POLICY_MTRC1C_RESEARCH_ONLY_BROAD_BRIDGE_CONTRACT_REVIEW_CN.md
docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md
docs/tw_modular_contracts/NEW_MODEL_AND_STRATEGY_DEVELOPER_GUIDE_CN.md
docs/tw_modular_contracts/MODEL_SIGNAL_CONTRACT_CN.md
docs/tw_modular_contracts/MODEL_SIGNAL_EXTENSION_SCHEMA_CN.md
docs/tw_modular_contracts/NEW_MODEL_REVIEWER_CHECKLIST_CN.md
data_tw/experiments/policy_mtr_research_only_continuation/mtrc1c_research_only_broad_bridge_contract/validator_design.json
data_tw/experiments/policy_mtr_research_only_continuation/mtrc1c_research_only_broad_bridge_contract/mtrc1d_work_recommendation.md
```

输入 artifact：

```text
top50 equivalence source:
data_tw/experiments/policy_mtr_research_only_continuation/mtrc1b_research_only_extended_top50_ltr_signal_build/signals.csv

top50 parent manifest/schema/validator:
data_tw/experiments/policy_mtr_research_only_continuation/mtrc1b_research_only_extended_top50_ltr_signal_build/manifest.json
data_tw/experiments/policy_mtr_research_only_continuation/mtrc1b_research_only_extended_top50_ltr_signal_build/schema.json
data_tw/experiments/policy_mtr_research_only_continuation/mtrc1b_research_only_extended_top50_ltr_signal_build/validator_report.json

S2C qlib full-rank source:
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2b_fresh_qlib_training/phase_s2b_post_filter_score_rank.csv
```

## 3. 构建规则

### 3.1 Top50 rows

MTRC1D 必须从 MTRC1B `signals.csv` 复制全部 top50 rows。对每个 `date,instrument`：

```text
buy_score 逐值等于 MTRC1B buy_score
raw_score 逐值等于 MTRC1B raw_score
score_rank 逐值等于 MTRC1B score_rank
signal_asof 逐值等于 MTRC1B signal_asof
available_at 逐值等于 MTRC1B available_at
source_artifact / source_model_artifact / source_feature_artifact 可追加 bridge trace，但不得丢失 MTRC1B 来源
```

`candidate_rank` 与 `full_qlib_rank` 必须同时满足：

```text
等于 MTRC1B 对应字段；
等于 S2B phase_s2b_post_filter_score_rank.csv 的 qlib_rank。
```

不得重新训练、重新 inference、重新排序或用 qlib score 替换 top50 LTR score。

### 3.2 Non-top50 rows

MTRC1D 可从 S2B qlib source 加入 `qlib_rank > 50` rows，但必须满足：

```text
candidate_rank <- qlib_rank
full_qlib_rank <- qlib_rank
buy_score <- null
raw_score <- null
score_rank <- null
model_name <- 与 MTRC1D research-only artifact 一致
model_family <- ltr_broad_visibility_research_only 或受控等价命名
signal_asof <- date
available_at <- date under S2C_LEGACY_RESEARCH_DAILY_VISIBLE
```

non-top50 rows 只能用于：

```text
已有持仓 hold/sell visibility
exit boundary
diagnostic
validator negative sample
```

non-top50 rows 禁止用于：

```text
buy universe
buy ranking
LTR priority
收益筛选
策略调参
生产展示
```

## 4. Extension 字段

MTRC1D 应添加以下 diagnostic-only extension fields：

```text
ext_mtrc1d_visibility_role
ext_mtrc1d_non_top50_buy_eligible
```

字段语义：

```text
ext_mtrc1d_visibility_role:
  top50_buy_candidate | non_top50_visibility_only

ext_mtrc1d_non_top50_buy_eligible:
  false for all non-top50 rows
  false or null for top50 rows unless schema 明确说明 top50 buy eligibility 仍由 candidate_rank<=50 决定
```

Manifest 必须按 `MODEL_SIGNAL_EXTENSION_SCHEMA_CN.md` 声明 metadata：

```text
dtype
semantic_role = diagnostic
availability_policy = available_at_lte_signal_asof 或 S2C_LEGACY_RESEARCH_DAILY_VISIBLE
producer
allowed_consumers = [audit, validator, mtrc_research_only_diagnostic]
ranking_allowed = false
required_for_core_replay = false
description
```

extension 不得改变 core fields 语义，不得让 non-top50 rows 获得 buy priority。

## 5. 允许输出

输出目录：

```text
data_tw/experiments/policy_mtr_research_only_continuation/mtrc1d_research_only_broad_full_rank_signal_build/
```

允许生成：

```text
manifest.json
signals.csv
schema.json
coverage_audit.csv
top50_equivalence_audit.csv
non_top50_visibility_audit.csv
non_top50_buy_hard_fail_audit.csv
extension_schema_audit.csv
forbidden_field_audit.csv
lineage_boundary_audit.csv
available_at_policy_audit.csv
source_trace_audit.csv
negative_samples/
negative_samples/non_top50_buy_score_present.csv
negative_samples/non_top50_ranked_for_buy.json
negative_samples/missing_mtrc1b_top50_row.csv
negative_samples/changed_mtrc1b_top50_score.csv
validator_report.json
diagnostic_findings.md
```

执行报告：

```text
docs/tw_portfolio_decision_model/POLICY_MTRC1D_RESEARCH_ONLY_BROAD_FULL_RANK_SIGNAL_BUILD_EXECUTION_REPORT_CN.md
```

审查报告：

```text
docs/tw_portfolio_decision_model/POLICY_MTRC1D_RESEARCH_ONLY_BROAD_FULL_RANK_SIGNAL_BUILD_REVIEW_CN.md
```

允许新增 builder/validator：

```text
scripts/build_tw_policy_mtrc1d_research_only_broad_full_rank_signal.py
```

builder 只能写 MTRC1D 输出目录和 MTRC1D 执行报告，不得写 registry、configs、provider、latest、frontend、API、Agent、daily 或 production 目录。

## 6. Validator hard gates

MTRC1D validator 必须至少检查：

```text
required_core_fields_present
date_instrument_unique
mtrc1b_top50_all_rows_present
top50_buy_score_equal_mtrc1b
top50_raw_score_equal_mtrc1b
top50_score_rank_equal_mtrc1b
top50_candidate_rank_equal_mtrc1b
top50_full_qlib_rank_equal_mtrc1b
top50_candidate_rank_equal_s2b_qlib_rank
top50_full_qlib_rank_equal_s2b_qlib_rank
non_top50_rows_from_s2b_qlib_rank_gt50
non_top50_buy_score_null
non_top50_raw_score_null
non_top50_score_rank_null
non_top50_buy_eligible_false
non_top50_not_ranked_for_buy
extension_fields_declared
extension_fields_ranking_allowed_false
forbidden_fields_absent
available_at_policy_declared
lineage_s2c_research_only_non_equivalent_to_mtr2r_e3
no_order_intent
no_replay_result
no_return_replay
no_production_or_default_write
```

Negative sample 必须覆盖：

```text
non_top50_buy_score_present -> fail
non_top50_ranked_for_buy -> fail
missing_mtrc1b_top50_row -> fail
changed_mtrc1b_top50_score -> fail
```

## 7. 禁止动作

MTRC1D 明确禁止：

```text
训练模型
调参
模型 inference
重新计算 LTR score
新增策略候选
修改 M2_hold_rank_buffer_100 参数
生成 OrderIntentArtifact
生成 ReplayResultArtifact
跑收益 replay
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

## 8. PASS / FAIL 标准

PASS 需要同时满足：

```text
MTRC1D broad signals.csv 生成且 schema/manifest 完整；
top50 rows 与 MTRC1B 完全等价；
non-top50 rows 来自 S2B qlib_rank > 50；
non-top50 buy_score/raw_score/score_rank 全为空；
non-top50 buy hard-fail negative samples 通过；
extension schema 合规且 ranking_allowed=false；
forbidden scope 和 production boundary audit 干净；
没有 OrderIntent、ReplayResult、收益 replay、default/latest/provider/frontend/API/Agent/daily 改动。
```

允许 verdict：

```text
PASS_READY_FOR_MTRC1E_RESEARCH_ONLY_BROAD_SIGNAL_REVIEW_OR_NEXT_DIAGNOSTIC_CONTRACT
PASS_WITH_CONDITIONS_READY_FOR_MTRC1D_R_NARROW_REPAIR
FAIL_NEEDS_MTRC1D_R_ARTIFACT_REPAIR
STOP_NO_VALID_BROAD_SIGNAL_ARTIFACT
```

## 9. 下一阶段边界

若 MTRC1D PASS，只能建议进入：

```text
MTRC1E_RESEARCH_ONLY_BROAD_SIGNAL_REVIEW_OR_NEXT_DIAGNOSTIC_CONTRACT
```

MTRC1E 可以审查 broad signal 是否足以支持后续 concentration/window diagnostic 的合同，但不得自动进入收益 replay。若要进入 replay 或 MTRC2，必须另写工作文档并再次授权。
