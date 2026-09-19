---
created_at: 2026-06-28
status: work_doc
phase: MTRC1A_R_LTR_INFERENCE_LINEAGE_REPAIR
parent_phase: MTRC1A_EXTENDED_TOP50_LTR_INFERENCE_FEASIBILITY
parent_review: docs/tw_portfolio_decision_model/POLICY_MTRC1A_EXTENDED_TOP50_LTR_INFERENCE_FEASIBILITY_REVIEW_CN.md
readonly_only: true
simulation_only: true
production_allowed: false
model_training_authorized: false
model_inference_authorized: false
model_signal_artifact_authorized: false
strategy_replay_authorized: false
strategy_tuning_authorized: false
new_candidate_authorized: false
provider_publish_allowed: false
accepted_latest_switch_allowed: false
frontend_default_switch_allowed: false
broker_authorized: false
---

# POLICY_MTRC1A_R_LTR_INFERENCE_LINEAGE_REPAIR_WORK_CN

## 1. 目标

MTRC1A_R 只做一件事：

```text
构建并审计 extended top50 LTR 的 PIT-clean inference input contract。
```

它不是训练阶段，不是 inference 阶段，不生成 LTR score，不生成
ModelSignalArtifact，不生成 broad bridge，不生成 OrderIntent，不跑 replay。

MTRC1A_R 的输出必须回答：

```text
后续 MTRC1B 是否可以在 research-only 边界内，
基于一个已审计的 PIT-clean inference input contract，
执行标准 extended top50 LTR signal build。
```

## 2. 背景

MTRC1A verdict 已接受为：

```text
STOP_NEEDS_LTR_INFERENCE_LINEAGE_REPAIR
```

阻断原因：

```text
E3 模型存在，但缺完整 78-feature list 和 PIT-clean feature input；
S2C 模型与 34-feature schema 存在，但 samples/score 表含 label/future/audit 列且缺 available_at；
S2C 与 MTR2_R/E3 不是同一 lineage，不能混用；
两条 lineage 均未形成标准 ModelSignalArtifact 的输入侧 lineage contract。
```

因此 MTRC1A_R 的修复目标必须停在 input contract 层。

## 3. 必读输入

执行者必须读取：

```text
docs/tw_portfolio_decision_model/POLICY_MTRC1A_EXTENDED_TOP50_LTR_INFERENCE_FEASIBILITY_WORK_CN.md
docs/tw_portfolio_decision_model/POLICY_MTRC1A_EXTENDED_TOP50_LTR_INFERENCE_FEASIBILITY_EXECUTION_REPORT_CN.md
docs/tw_portfolio_decision_model/POLICY_MTRC1A_EXTENDED_TOP50_LTR_INFERENCE_FEASIBILITY_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_MTRC_RESEARCH_ONLY_CONTINUATION_MAINLINE_CN.md
docs/tw_modular_contracts/MODEL_SIGNAL_CONTRACT_CN.md
docs/tw_modular_contracts/MODEL_SIGNAL_EXTENSION_SCHEMA_CN.md
docs/tw_modular_contracts/NEW_MODEL_REVIEWER_CHECKLIST_CN.md
data_tw/experiments/policy_mtr_research_only_continuation/mtrc1a_extended_top50_ltr_inference_feasibility/manifest.json
data_tw/experiments/policy_mtr_research_only_continuation/mtrc1a_extended_top50_ltr_inference_feasibility/ltr_lineage_inventory.csv
data_tw/experiments/policy_mtr_research_only_continuation/mtrc1a_extended_top50_ltr_inference_feasibility/model_file_audit.csv
data_tw/experiments/policy_mtr_research_only_continuation/mtrc1a_extended_top50_ltr_inference_feasibility/feature_availability_audit.csv
data_tw/experiments/policy_mtr_research_only_continuation/mtrc1a_extended_top50_ltr_inference_feasibility/inference_input_coverage_audit.csv
data_tw/experiments/policy_mtr_research_only_continuation/mtrc1a_extended_top50_ltr_inference_feasibility/pit_available_at_feasibility_audit.csv
data_tw/experiments/policy_mtr_research_only_continuation/mtrc1a_extended_top50_ltr_inference_feasibility/top50_alignment_feasibility.csv
data_tw/experiments/policy_mtr_research_only_continuation/mtrc1a_extended_top50_ltr_inference_feasibility/model_signal_mapping_plan.csv
data_tw/experiments/policy_mtr_research_only_continuation/mtrc1a_extended_top50_ltr_inference_feasibility/validator_report.json
```

必须抽查源头：

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e3_orthogonal_ltr_training/phasee3_training_manifest.json
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e3_orthogonal_ltr_training/phasee3_ltr_model.pkl
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e1_frozen_qlib_training_and_oos_score/phasee1_raw_oos_score_rank_2023_2026.csv
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2c_fresh_ltr_sample_training/phase_s2c_ltr_model_manifest.json
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2c_fresh_ltr_sample_training/phase_s2c_ltr_sample_schema.json
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2c_fresh_ltr_sample_training/phase_s2c_ltr_samples.csv
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2c_fresh_ltr_sample_training/phase_s2c_ltr_score_rank.csv
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2c_fresh_ltr_sample_training/phase_s2c_missing_feature_label_audit.json
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2c_fresh_ltr_sample_training/phase_s2c_label_horizon_split_purity_audit.json
```

## 4. Lineage 选择原则

MTRC1A_R 必须先选择且只选择一条 lineage：

```text
E3/MTR2_R-compatible lineage
```

或

```text
S2C split-aligned fresh lineage
```

不得把 E3 模型、S2C features、MTR2_R broad signal、S2C qlib rank 混合成一个
未审查的新 lineage。

如果选择 E3：

```text
必须恢复 exact 78-feature list；
必须证明 feature order 与 E3 model artifact 一致；
必须产出或定位 PIT-clean feature-only input contract；
必须证明 qlib full-rank source 与 E3 LTR candidate rows 可按 date/instrument 对齐。
```

如果选择 S2C：

```text
必须声明这是 split-aligned fresh lineage，不是 MTR2_R/E3 lineage；
必须只使用 phase_s2c_ltr_model_manifest.json 中声明的 34 feature columns；
必须从 samples/schema 中定义 feature-only input contract；
必须明确剔除 future/label/audit/training eligibility 字段；
必须证明 qlib_rank/full_qlib_rank 来源和 MTRC 后续合同的可接受关系。
```

## 5. 允许输出

输出目录：

```text
data_tw/experiments/policy_mtr_research_only_continuation/mtrc1a_r_ltr_inference_lineage_repair/
```

允许生成：

```text
manifest.json
lineage_selection_decision.csv
feature_schema_contract.json
inference_input_contract.json
inference_input_columns_audit.csv
forbidden_column_exclusion_audit.csv
pit_available_at_policy.md
pit_available_at_audit.csv
qlib_rank_alignment_contract.csv
coverage_plan.csv
mtrc1b_readiness_gate.csv
forbidden_scope_audit.csv
production_boundary_audit.csv
validator_report.json
diagnostic_findings.md
```

执行报告：

```text
docs/tw_portfolio_decision_model/POLICY_MTRC1A_R_LTR_INFERENCE_LINEAGE_REPAIR_EXECUTION_REPORT_CN.md
```

审查报告：

```text
docs/tw_portfolio_decision_model/POLICY_MTRC1A_R_LTR_INFERENCE_LINEAGE_REPAIR_REVIEW_CN.md
```

允许新增 builder：

```text
scripts/build_tw_policy_mtrc1a_r_ltr_inference_lineage_repair.py
```

builder 只能写 MTRC1A_R 输出目录和执行报告。

## 6. Inference Input Contract 要求

`inference_input_contract.json` 至少必须声明：

```text
lineage_id
model_artifact
model_manifest
feature_schema_source
feature_columns
feature_column_order
required_key_columns
signal_asof_mapping
available_at_policy
qlib_rank_source
full_qlib_rank_mapping
top50_candidate_boundary
forbidden_columns
source_artifacts
checksum_or_hash_evidence
```

要求：

```text
required_key_columns = date, instrument
signal_asof <- date
available_at 必须有明确 PIT policy
feature_asof <= signal_asof 必须可审计
feature input 不得包含 future_return_*, future_excess_return_*, forward_return_*
feature input 不得包含 label_*, relevance_10d_top_heavy, ltr_relevance_label
feature input 不得包含 realized_pnl, action, holding, position, target_position, order_qty, execution_*, broker_order_id
```

MTRC1A_R 可以写合同、schema、审计表；不得写真实 LTR inference score。

## 7. PIT / available_at 要求

必须定义并审计：

```text
signal_asof=date
available_at 的生成规则
available_at <= signal_asof 或合同允许的 legacy visible policy
feature_asof <= signal_asof
label/future columns excluded before any inference-ready boundary
```

如果只能从现有训练样本中导出 feature-only rows，必须在 audit 中列出：

```text
原始列
保留列
剔除列
剔除原因
是否策略可消费
是否可作为后续 MTRC1B inference input
```

## 8. MTRC1B Gate

只有全部满足时，MTRC1A_R 才能给出进入 MTRC1B 的建议：

```text
exact feature schema declared
feature column order declared
feature-only input contract exists
date/instrument unique key declared
coverage window declared
available_at policy declared and audited
forbidden columns excluded
qlib rank/full_qlib_rank mapping declared
lineage not mixed
research-only output path clean
production boundary clean
```

MTRC1A_R 不得因为已有 score rows 就判定 ready；ready 的对象只能是
PIT-clean inference input contract。

## 9. Verdict

允许 verdict：

```text
PASS_READY_FOR_MTRC1B_RESEARCH_ONLY_EXTENDED_TOP50_LTR_SIGNAL_BUILD
STOP_NEEDS_MORE_LTR_INFERENCE_LINEAGE_REPAIR
STOP_NEEDS_MODEL_RETRAIN_OR_FEATURE_REBUILD
FAIL_NEEDS_MTRC1A_R_REPAIR
```

### 9.1 PASS 条件

必须同时满足：

```text
不需要训练；
不需要大规模重建 feature；
已选择单一 lineage；
已有模型 artifact 可溯源；
feature-only inference input contract 完整；
PIT/available_at 可审计；
qlib rank/full_qlib_rank mapping 可审计；
无 forbidden fields；
未生成 score/signal/replay；
production boundary clean。
```

### 9.2 STOP_NEEDS_MORE_LTR_INFERENCE_LINEAGE_REPAIR

用于：

```text
模型仍可用，但 feature schema、available_at、coverage 或 qlib alignment 仍缺证据；
需要继续 repair input lineage，但尚未证明必须重训。
```

### 9.3 STOP_NEEDS_MODEL_RETRAIN_OR_FEATURE_REBUILD

用于：

```text
E3 exact feature schema 无法恢复；
S2C feature-only input 无法建立；
feature_asof / available_at 无法 PIT 证明；
模型 artifact 与 feature schema 不匹配；
必须重训或大规模重建 feature 才能继续。
```

### 9.4 FAIL_NEEDS_MTRC1A_R_REPAIR

用于：

```text
MTRC1A_R 产物缺失、合同字段缺失、validator 不一致、混用 lineage、
或发生任何禁止动作。
```

## 10. 禁止事项

MTRC1A_R 禁止：

```text
训练模型
加载模型执行 predict/inference 生成新 score
生成 LTR score/rank
生成 ModelSignalArtifact/signals.csv
生成 broad bridge
生成 OrderIntent / ReplayResult
跑收益 replay
调参
新增策略候选
修改 M2 参数
修改 MTR 输入产物
修改 production/default/frontend/API/Agent/daily/provider/latest
provider publish / accepted latest switch
broker / quick-trade / real order
target_weight / target_position / quantity instruction
```

## 11. 给执行者命令

```text
请执行 MTRC1A_R_LTR_INFERENCE_LINEAGE_REPAIR。
只选择一条 LTR lineage，构建并审计 PIT-clean inference input contract。
不得训练、不得 inference、不得生成 score、不得生成 ModelSignalArtifact、不得 replay、不得生产化。
最终给出 PASS_READY_FOR_MTRC1B_RESEARCH_ONLY_EXTENDED_TOP50_LTR_SIGNAL_BUILD /
STOP_NEEDS_MORE_LTR_INFERENCE_LINEAGE_REPAIR /
STOP_NEEDS_MODEL_RETRAIN_OR_FEATURE_REBUILD /
FAIL_NEEDS_MTRC1A_R_REPAIR。
```

## 12. 给审查者 brief

```text
审查重点不是收益，也不是模型效果；
重点是 MTRC1A_R 是否真的形成了 feature-only、PIT-clean、available_at 可审计、
单一 lineage、可供后续 MTRC1B inference 的输入合同。
若发现训练、predict、score/signal/replay 生成或生产路径改动，直接 FAIL。
```
