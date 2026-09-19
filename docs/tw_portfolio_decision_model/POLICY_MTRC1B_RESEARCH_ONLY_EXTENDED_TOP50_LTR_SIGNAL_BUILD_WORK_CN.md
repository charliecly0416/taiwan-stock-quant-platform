---
created_at: 2026-06-28
status: work_doc
phase: MTRC1B_RESEARCH_ONLY_EXTENDED_TOP50_LTR_SIGNAL_BUILD
parent_phase: MTRC1A_R_LTR_INFERENCE_LINEAGE_REPAIR
parent_review: docs/tw_portfolio_decision_model/POLICY_MTRC1A_R_LTR_INFERENCE_LINEAGE_REPAIR_REVIEW_CN.md
readonly_only: true
simulation_only: true
production_allowed: false
model_training_authorized: false
model_inference_authorized: true
model_signal_artifact_authorized: true
strategy_replay_authorized: false
strategy_tuning_authorized: false
new_candidate_authorized: false
broad_bridge_authorized: false
provider_publish_allowed: false
accepted_latest_switch_allowed: false
frontend_default_switch_allowed: false
broker_authorized: false
---

# POLICY_MTRC1B_RESEARCH_ONLY_EXTENDED_TOP50_LTR_SIGNAL_BUILD_WORK_CN

## 1. 目标

MTRC1B 只做一件事：

```text
基于 MTRC1A_R 审查通过的 S2C split-aligned fresh lineage input contract，
生成 research-only extended top50 LTR ModelSignalArtifact。
```

MTRC1B 可以加载既有 S2C LTR 模型并执行 research-only inference，生成标准
ModelSignalArtifact；但不得 broad bridge，不得生成 OrderIntent，不得生成
ReplayResult，不得跑收益 replay，不得生产化。

本阶段输出必须回答：

```text
是否已经形成一个标准、可校验、research-only 的 extended top50 LTR signal artifact，
供后续另行授权的研究阶段继续检查。
```

## 2. 必读输入

执行者必须读取：

```text
docs/tw_portfolio_decision_model/POLICY_MTRC1A_R_LTR_INFERENCE_LINEAGE_REPAIR_WORK_CN.md
docs/tw_portfolio_decision_model/POLICY_MTRC1A_R_LTR_INFERENCE_LINEAGE_REPAIR_EXECUTION_REPORT_CN.md
docs/tw_portfolio_decision_model/POLICY_MTRC1A_R_LTR_INFERENCE_LINEAGE_REPAIR_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_MTRC_RESEARCH_ONLY_CONTINUATION_MAINLINE_CN.md
docs/tw_modular_contracts/MODEL_SIGNAL_CONTRACT_CN.md
docs/tw_modular_contracts/MODEL_SIGNAL_EXTENSION_SCHEMA_CN.md
docs/tw_modular_contracts/NEW_MODEL_REVIEWER_CHECKLIST_CN.md
data_tw/experiments/policy_mtr_research_only_continuation/mtrc1a_r_ltr_inference_lineage_repair/manifest.json
data_tw/experiments/policy_mtr_research_only_continuation/mtrc1a_r_ltr_inference_lineage_repair/feature_schema_contract.json
data_tw/experiments/policy_mtr_research_only_continuation/mtrc1a_r_ltr_inference_lineage_repair/inference_input_contract.json
data_tw/experiments/policy_mtr_research_only_continuation/mtrc1a_r_ltr_inference_lineage_repair/inference_input_columns_audit.csv
data_tw/experiments/policy_mtr_research_only_continuation/mtrc1a_r_ltr_inference_lineage_repair/forbidden_column_exclusion_audit.csv
data_tw/experiments/policy_mtr_research_only_continuation/mtrc1a_r_ltr_inference_lineage_repair/pit_available_at_policy.md
data_tw/experiments/policy_mtr_research_only_continuation/mtrc1a_r_ltr_inference_lineage_repair/pit_available_at_audit.csv
data_tw/experiments/policy_mtr_research_only_continuation/mtrc1a_r_ltr_inference_lineage_repair/qlib_rank_alignment_contract.csv
data_tw/experiments/policy_mtr_research_only_continuation/mtrc1a_r_ltr_inference_lineage_repair/coverage_plan.csv
data_tw/experiments/policy_mtr_research_only_continuation/mtrc1a_r_ltr_inference_lineage_repair/mtrc1b_readiness_gate.csv
data_tw/experiments/policy_mtr_research_only_continuation/mtrc1a_r_ltr_inference_lineage_repair/validator_report.json
```

必须抽查源头：

```text
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2c_fresh_ltr_sample_training/phase_s2c_ltr_model_manifest.json
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2c_fresh_ltr_sample_training/phase_s2c_ltr_sample_schema.json
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2c_fresh_ltr_sample_training/phase_s2c_ltr_samples.csv
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2c_fresh_ltr_sample_training/phase_s2c_ltr_model.pkl
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2b_fresh_qlib_training/phase_s2b_post_filter_score_rank.csv
```

## 3. Lineage 边界

MTRC1B 必须只使用：

```text
S2C_SPLIT_ALIGNED_FRESH_LTR
```

禁止混用：

```text
E3 model artifact
E3 78-feature lineage
MTR2_R broad signal artifact
MTR2_R/E3 full-rank source
任何未在 MTRC1A_R contract 中声明的 feature
```

MTRC1B 的报告和 manifest 必须显式写明：

```text
S2C is a new research lineage and is not equivalent to MTR2_R/E3.
```

不得把 S2C signal 用于解除 MTR5 的 MTR2_R/E3 clean extended lineage blocker。

## 4. 允许输出

输出目录建议：

```text
data_tw/experiments/policy_mtr_research_only_continuation/mtrc1b_research_only_extended_top50_ltr_signal_build/
```

允许生成：

```text
manifest.json
signals.csv
schema.json
coverage_audit.csv
forbidden_field_audit.csv
legacy_mapping_audit.csv
input_contract_audit.csv
lineage_boundary_audit.csv
available_at_policy_audit.csv
qlib_rank_alignment_audit.csv
validator_report.json
diagnostic_findings.md
```

执行报告：

```text
docs/tw_portfolio_decision_model/POLICY_MTRC1B_RESEARCH_ONLY_EXTENDED_TOP50_LTR_SIGNAL_BUILD_EXECUTION_REPORT_CN.md
```

审查报告：

```text
docs/tw_portfolio_decision_model/POLICY_MTRC1B_RESEARCH_ONLY_EXTENDED_TOP50_LTR_SIGNAL_BUILD_REVIEW_CN.md
```

允许新增 builder：

```text
scripts/build_tw_policy_mtrc1b_research_only_extended_top50_ltr_signal.py
```

builder 只能写 MTRC1B 输出目录和执行报告。

## 5. Signal 字段要求

`signals.csv` 必须遵守 `MODEL_SIGNAL_CONTRACT_CN.md`，至少包含：

```text
date
instrument
model_name
model_family
candidate_rank
buy_score
raw_score
score_rank
full_qlib_rank
signal_asof
available_at
source_artifact
source_model_artifact
source_feature_artifact
```

S2C LTR mapping 固定为：

```text
candidate_rank <- qlib_rank
buy_score <- S2C LTR predict score
raw_score <- S2C LTR predict score
score_rank <- buy_score daily descending rank within authorized top50 rows
full_qlib_rank <- qlib_rank
signal_asof <- date
available_at <- date under S2C_LEGACY_RESEARCH_DAILY_VISIBLE
```

candidate universe 边界：

```text
top50_flag == 1
qlib_rank <= 50
```

LTR 只能在 S2C qlib top50 内重排买入优先级；不得扩大 buy universe。

## 6. Feature Input 要求

MTRC1B 必须从 MTRC1A_R contract 构建 feature-only input：

```text
date
instrument
signal_asof
available_at
34 declared S2C feature columns in exact order
```

必须在 audit 中证明：

```text
feature_count = 34
feature order equals phase_s2c_ltr_model_manifest.json
feature order equals phase_s2c_ltr_sample_schema.json input_columns
date,instrument duplicate = 0
forbidden retained columns = 0
```

MTRC1B 不得把源 sample CSV 中的以下字段带入 inference matrix 或 signals.csv：

```text
future_return_*
future_excess_return_*
forward_return_*
label_*
relevance_10d_top_heavy
ltr_relevance_label
topk_forward_bucket
label_start_date
label_end_date_*
label_complete_*
feature_complete
sample_complete
split_purity_keep
training_row_eligible
realized_pnl
realized_return
action
holding
position
target_position
target_weight
quantity
order_qty
execution_*
broker_order_id
```

## 7. Validator 要求

validator 至少检查：

```text
required signal fields present
date,instrument duplicate = 0
feature order matches MTRC1A_R contract
feature_count = 34
model artifact hash matches MTRC1A_R source hash
candidate_rank numeric
buy_score numeric
raw_score numeric
score_rank numeric
full_qlib_rank numeric
candidate_rank == qlib_rank
full_qlib_rank == qlib_rank
score_rank is daily descending rank of buy_score
available_at <= signal_asof under declared legacy policy
forbidden fields absent from signals.csv
source_artifact/source_model_artifact/source_feature_artifact populated
lineage is S2C only
no broad bridge / replay / production side effects
```

如果使用已有 `phase_s2c_ltr_score_rank.csv` 作为 reference-only 对照，必须只用于审计；
不得把其中 label/audit/training 字段复制进标准 signal。

## 8. 禁止事项

MTRC1B 禁止：

```text
训练模型
调参
根据收益或 replay 表现筛选模型
新增候选
修改 M2 参数
生成 broad bridge
生成 OrderIntent
生成 ReplayResult
跑收益 replay
修改 production/default/latest/provider/frontend/API/Agent/daily
provider publish
accepted latest switch
monitor config save / scan / alerts write
broker / quick-trade / real order
target_weight / target_position / quantity instruction
把 S2C 静默宣称为 MTR2_R/E3 lineage
用 S2C signal 解除 MTR5 clean_extended_lineage_found=false
```

## 9. Verdict

允许 verdict：

```text
PASS_READY_FOR_MTRC1B_R_RESEARCH_ONLY_SIGNAL_REVIEW
STOP_NEEDS_MORE_SIGNAL_BUILD_REPAIR
STOP_NEEDS_MODEL_RETRAIN_OR_FEATURE_REBUILD
FAIL_NEEDS_MTRC1B_REPAIR
```

### 9.1 PASS 条件

必须同时满足：

```text
标准 ModelSignalArtifact 已生成
只使用 S2C split-aligned fresh lineage
34-feature input order 正确
forbidden fields absent
date,instrument unique
candidate_rank/full_qlib_rank mapping 正确
score_rank 可复核
available_at policy 声明并审计
source hashes / artifacts 可溯源
validator 全 PASS
未 broad bridge
未 replay
未 production/default/latest/provider/frontend/API/Agent/daily 改动
未 broker/order/target position/target weight/quantity
```

### 9.2 STOP_NEEDS_MORE_SIGNAL_BUILD_REPAIR

用于：

```text
模型与 feature contract 仍可用，但 signal schema、rank mapping、validator、
coverage、forbidden audit 或 source trace 仍缺证据。
```

### 9.3 STOP_NEEDS_MODEL_RETRAIN_OR_FEATURE_REBUILD

用于：

```text
S2C model artifact 无法加载；
34-feature matrix 无法按合同建立；
feature schema 与模型不匹配；
available_at / feature_asof 无法满足 research-only PIT contract；
必须重训或大规模重建 feature 才能继续。
```

### 9.4 FAIL_NEEDS_MTRC1B_REPAIR

用于：

```text
产物缺失、validator 不一致、混用 lineage、forbidden 字段进入 signal、
或发生任何 broad bridge/replay/production/order 越界。
```

## 10. 给执行者命令

```text
请执行 MTRC1B_RESEARCH_ONLY_EXTENDED_TOP50_LTR_SIGNAL_BUILD。
只能基于 MTRC1A_R 审查通过的 S2C split-aligned fresh lineage contract，
生成 research-only standard ModelSignalArtifact。
允许 research-only inference 生成 signal；不得训练、不得调参、不得 broad bridge、
不得 OrderIntent、不得 ReplayResult、不得 replay、不得 production/default/latest/provider/frontend/API/Agent/daily 改动。
最终给出 PASS_READY_FOR_MTRC1B_R_RESEARCH_ONLY_SIGNAL_REVIEW /
STOP_NEEDS_MORE_SIGNAL_BUILD_REPAIR /
STOP_NEEDS_MODEL_RETRAIN_OR_FEATURE_REBUILD /
FAIL_NEEDS_MTRC1B_REPAIR。
```

## 11. 给审查者 brief

```text
审查重点不是收益，也不是 replay。
重点是 MTRC1B 是否只基于 S2C contract 生成标准 research-only ModelSignalArtifact，
是否保留 34-feature input order、正确映射 candidate_rank/full_qlib_rank/buy_score/score_rank，
是否剔除 forbidden fields，是否未 broad bridge、未 replay、未生产化。
```
