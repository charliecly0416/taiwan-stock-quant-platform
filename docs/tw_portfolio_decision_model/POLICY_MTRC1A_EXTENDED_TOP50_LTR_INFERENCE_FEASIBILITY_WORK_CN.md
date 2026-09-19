---
created_at: 2026-06-28
status: work_doc
phase: MTRC1A_EXTENDED_TOP50_LTR_INFERENCE_FEASIBILITY
parent_mainline: docs/tw_portfolio_decision_model/POLICY_MTRC_RESEARCH_ONLY_CONTINUATION_MAINLINE_CN.md
upstream_review: docs/tw_portfolio_decision_model/POLICY_MTRC0_CLEAN_EXTENDED_LINEAGE_CONTRACT_AND_FEASIBILITY_REVIEW_CN.md
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

# POLICY_MTRC1A_EXTENDED_TOP50_LTR_INFERENCE_FEASIBILITY_WORK_CN

## 1. 目标

MTRC1A 只回答一个问题：

```text
现在是否可以在 research-only 边界内，
用既有 LTR 模型和可追溯特征，
补出 extended-window top50 LTR inference / ModelSignalArtifact 的可行路径。
```

MTRC1A 不直接生成 extended LTR score、不生成正式 ModelSignalArtifact、不做 broad bridge、不做 OrderIntent、不做 replay。

## 2. 背景

MTRC0 结论：

```text
STOP_NO_CLEAN_LINEAGE_PATH
```

原因：

```text
MTR2_R broad full-rank artifact 只覆盖 2026-01-02..2026-05-07；
标准 top50 LTR artifact 也只覆盖同一短窗口；
qlib full-rank source 虽覆盖 2023-01-03..2026-05-07，但不是 LTR buy_score 语义。
```

因此要继续研究，必须先补：

```text
extended-window standard top50 LTR score / ModelSignalArtifact
```

但补之前必须确认：

```text
是否能不训练、不调参，只用既有模型做 inference；
是否有 extended window 的 LTR 特征；
是否 PIT / available_at 可审计；
是否能与 qlib full-rank source 对齐；
是否能保持 research-only，不触碰 production/latest/default。
```

## 3. 必读输入

执行者必须读取：

```text
docs/tw_portfolio_decision_model/POLICY_MTRC_RESEARCH_ONLY_CONTINUATION_MAINLINE_CN.md
docs/tw_portfolio_decision_model/POLICY_MTRC0_CLEAN_EXTENDED_LINEAGE_CONTRACT_AND_FEASIBILITY_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_MTRC0_CLEAN_EXTENDED_LINEAGE_CONTRACT_AND_FEASIBILITY_EXECUTION_REPORT_CN.md
data_tw/experiments/policy_mtr_research_only_continuation/mtrc0_clean_extended_lineage_contract/manifest.json
data_tw/experiments/policy_mtr_research_only_continuation/mtrc0_clean_extended_lineage_contract/candidate_bridge_feasibility_matrix.csv
docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md
docs/tw_modular_contracts/NEW_MODEL_AND_STRATEGY_DEVELOPER_GUIDE_CN.md
docs/tw_modular_contracts/MODEL_SIGNAL_CONTRACT_CN.md
docs/tw_modular_contracts/MODEL_SIGNAL_EXTENSION_SCHEMA_CN.md
docs/tw_modular_contracts/NEW_MODEL_REVIEWER_CHECKLIST_CN.md
```

必须盘点两类 lineage：

### 3.1 E3 historical LTR line

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e3_orthogonal_ltr_training/phasee3_training_manifest.json
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e3_orthogonal_ltr_training/phasee3_ltr_model.pkl
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e3_orthogonal_ltr_training/phasee3_train_row_scores.csv
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e3_orthogonal_ltr_training/phasee3_test_row_scores_2026.csv
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e4_2026_replay/phasee4_replay_ready_scores_2026.csv
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e1_frozen_qlib_training_and_oos_score/phasee1_raw_oos_score_rank_2023_2026.csv
```

### 3.2 S2C / split-aligned LTR line

```text
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2c_fresh_ltr_sample_training/phase_s2c_training_manifest.json
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2c_fresh_ltr_sample_training/phase_s2c_ltr_model_manifest.json
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2c_fresh_ltr_sample_training/phase_s2c_ltr_model.pkl
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2c_fresh_ltr_sample_training/phase_s2c_ltr_samples.csv
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2c_fresh_ltr_sample_training/phase_s2c_ltr_score_rank.csv
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2c_fresh_ltr_sample_training/phase_s2c_ltr_score_coverage_by_split.csv
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2c_fresh_ltr_sample_training/phase_s2c_ltr_score_coverage_by_date.csv
```

如果某些文件缺失，必须记录，不得用非同源文件替代。

## 4. 输出目录与文件

输出目录：

```text
data_tw/experiments/policy_mtr_research_only_continuation/mtrc1a_extended_top50_ltr_inference_feasibility/
```

必须生成：

```text
manifest.json
ltr_lineage_inventory.csv
model_file_audit.csv
feature_availability_audit.csv
inference_input_coverage_audit.csv
pit_available_at_feasibility_audit.csv
top50_alignment_feasibility.csv
model_signal_mapping_plan.csv
forbidden_scope_audit.csv
production_boundary_audit.csv
validator_report.json
diagnostic_findings.md
mtrc1b_work_recommendation.md
```

执行报告：

```text
docs/tw_portfolio_decision_model/POLICY_MTRC1A_EXTENDED_TOP50_LTR_INFERENCE_FEASIBILITY_EXECUTION_REPORT_CN.md
```

审查报告：

```text
docs/tw_portfolio_decision_model/POLICY_MTRC1A_EXTENDED_TOP50_LTR_INFERENCE_FEASIBILITY_REVIEW_CN.md
```

允许新增 builder：

```text
scripts/build_tw_policy_mtrc1a_extended_top50_ltr_inference_feasibility.py
```

脚本只能写 MTRC1A 输出目录和执行报告。

## 5. 必须回答的问题

### 5.1 是否有可用既有模型

必须判断：

```text
E3 phasee3_ltr_model.pkl 是否存在、manifest 是否说明训练/测试窗口和 feature list/hash；
S2C phase_s2c_ltr_model.pkl 是否存在、manifest 是否说明 split、feature list、PIT；
是否需要重新训练；
是否只需 inference。
```

若需要重新训练才能补 extended top50 LTR，MTRC1A 结论不能直接进入 MTRC1B。

### 5.2 是否有 extended inference 输入

必须判断：

```text
是否有 2023-2026 或更长窗口的 top50 rows；
是否有 LTR 所需 78 个或对应 feature set；
是否覆盖 MTRC 所需日期；
是否能按 date/instrument 与 qlib full-rank source 对齐；
是否缺 institutional_flow / margin_short / TWII / price-derived features；
```

### 5.3 是否 PIT 合规

必须判断：

```text
feature asof <= signal date；
available_at policy 是否可写入 ModelSignalArtifact；
是否含 future_return / label / realized pnl / execution / position / order 字段；
训练标签是否会泄漏到 inference input；
```

### 5.4 是否能生成标准 top50 LTR ModelSignalArtifact

必须给出 mapping plan：

```text
candidate_rank <- qlib rank
buy_score <- LTR inference score
raw_score <- LTR inference score
score_rank <- buy_score daily descending rank
full_qlib_rank <- qlib full rank
signal_asof <- date
available_at <- PIT-safe available date
source_artifact / source_model_artifact / source_feature_artifact 完整溯源
```

### 5.5 是否能进入 MTRC1B

允许 MTRC1B 的前提：

```text
不需要训练；
模型文件和 feature schema 完整；
inference input 覆盖足够；
PIT/available_at 可审计；
能输出 research-only ModelSignalArtifact；
不触碰 accepted latest/default/provider/frontend/API/Agent/daily；
```

## 6. Verdict

允许 verdict：

```text
PASS_READY_FOR_MTRC1B_RESEARCH_ONLY_EXTENDED_TOP50_LTR_SIGNAL_BUILD
STOP_NEEDS_LTR_INFERENCE_LINEAGE_REPAIR
STOP_NEEDS_MODEL_RETRAIN_OR_FEATURE_REBUILD
FAIL_NEEDS_MTRC1A_REPAIR
```

### 6.1 PASS 条件

必须同时满足：

```text
existing model usable without retraining；
feature/input rows available for extended top50 inference；
PIT/available_at feasible；
ModelSignal mapping feasible；
research-only output path defined；
production boundary clean。
```

### 6.2 STOP_NEEDS_LTR_INFERENCE_LINEAGE_REPAIR

用于：

```text
模型存在、部分特征/score 存在，但缺标准 artifact / mapping / PIT audit；
可以 repair，但 MTRC1B 前必须先补 inference lineage。
```

### 6.3 STOP_NEEDS_MODEL_RETRAIN_OR_FEATURE_REBUILD

用于：

```text
没有可用模型；
没有可用 feature input；
需要重训模型；
需要大规模重建特征；
PIT 无法证明。
```

## 7. 禁止事项

MTRC1A 禁止：

```text
训练模型
执行模型 inference 生成新 score
生成 ModelSignalArtifact
生成 broad bridge
生成 OrderIntent / ReplayResult
跑收益 replay
调参
新增策略候选
修改 M2 参数
修改已有 MTR 输入产物
修改 production/default/frontend/API/Agent/daily/provider/latest
provider publish / accepted latest switch
broker / quick-trade / real order
target_weight / target_position / quantity instruction
```

## 8. 给执行者命令

```text
请执行 MTRC1A_EXTENDED_TOP50_LTR_INFERENCE_FEASIBILITY。
只做 E3 与 S2C 两条 LTR lineage 的模型、特征、PIT、coverage、ModelSignal mapping 可行性审计。
不得训练、不得 inference、不得生成 signal、不得 replay、不得生产化。
最终给出 PASS_READY_FOR_MTRC1B_RESEARCH_ONLY_EXTENDED_TOP50_LTR_SIGNAL_BUILD / STOP_NEEDS_LTR_INFERENCE_LINEAGE_REPAIR / STOP_NEEDS_MODEL_RETRAIN_OR_FEATURE_REBUILD / FAIL_NEEDS_MTRC1A_REPAIR。
```

## 9. 给审查者 brief

```text
请审查 MTRC1A 是否真的证明可以补 extended top50 LTR signal。
重点看是否把 S2C 新 lineage 与 MTR2_R 旧 lineage混同；
是否需要重训；
是否有 feature/PIT 缺口；
是否保持 research-only；
是否没有偷偷生成 score/signal/replay。
```
