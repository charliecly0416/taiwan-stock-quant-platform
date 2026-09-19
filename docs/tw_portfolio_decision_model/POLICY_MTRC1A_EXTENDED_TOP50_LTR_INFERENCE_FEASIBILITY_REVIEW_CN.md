---
created_at: 2026-06-28
status: review
phase: MTRC1A_EXTENDED_TOP50_LTR_INFERENCE_FEASIBILITY
reviewer: MTRC1A
readonly_only: true
simulation_only: true
production_allowed: false
accepted_verdict: STOP_NEEDS_LTR_INFERENCE_LINEAGE_REPAIR
next_work_doc: docs/tw_portfolio_decision_model/POLICY_MTRC1A_R_LTR_INFERENCE_LINEAGE_REPAIR_WORK_CN.md
---

# POLICY_MTRC1A_EXTENDED_TOP50_LTR_INFERENCE_FEASIBILITY_REVIEW_CN

生成日期：2026-06-28

## 1. Verdict

```text
STOP_NEEDS_LTR_INFERENCE_LINEAGE_REPAIR
```

审查接受执行者 MTRC1A verdict。当前证据不支持直接进入
`PASS_READY_FOR_MTRC1B_RESEARCH_ONLY_EXTENDED_TOP50_LTR_SIGNAL_BUILD`，
因为 E3 与 S2C 都还缺可审计的 PIT-clean inference input contract、
`available_at` policy、标准 ModelSignal mapping 的输入侧证据，以及 qlib
full-rank alignment 的完整证明。

审查也不支持升级为
`STOP_NEEDS_MODEL_RETRAIN_OR_FEATURE_REBUILD`。理由是两条 lineage 均有既有
LightGBM LTR 模型文件；S2C 已有完整 34-feature schema 和大范围样本表；
E3 虽缺完整 78-feature list/PIT-clean feature input，但 manifest 至少保存
`feature_count=78` 和 feature hash，且现有阻断更像 inference lineage / 输入合同
缺口，而不是已经证明必须重训模型。

## 2. 审查范围

已读取并复核：

- `docs/tw_portfolio_decision_model/POLICY_MTRC1A_EXTENDED_TOP50_LTR_INFERENCE_FEASIBILITY_WORK_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_MTRC1A_EXTENDED_TOP50_LTR_INFERENCE_FEASIBILITY_EXECUTION_REPORT_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_MTRC_RESEARCH_ONLY_CONTINUATION_MAINLINE_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_MTRC0_CLEAN_EXTENDED_LINEAGE_CONTRACT_AND_FEASIBILITY_REVIEW_CN.md`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc1a_extended_top50_ltr_inference_feasibility/` 下全部 13 个 artifacts
- E3 / S2C 源头 manifest、CSV 表头、S2C sample schema、S2C label/split audit
- `MODEL_SIGNAL_CONTRACT_CN.md`、`MODEL_SIGNAL_EXTENSION_SCHEMA_CN.md`、`NEW_MODEL_REVIEWER_CHECKLIST_CN.md`

本审查只新增本报告和下一步 `MTRC1A_R` repair 工作文档；未修改执行者产物。

## 3. 关键证据

### 3.1 E3 模型与输入缺口

E3 模型文件存在：

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e3_orthogonal_ltr_training/phasee3_ltr_model.pkl
```

`model_file_audit.csv` 记录模型大小、sha256、manifest 存在，且
`needs_retraining_for_model_file=False`、`usable_without_retraining_for_future_inference=True`。
源头 `phasee3_training_manifest.json` 声明：

```text
model_type=LightGBM.LGBMRanker
train_period=2023-01-01..2025-12-31
test_period=2026-01-01..2026-05-07
feature_count=78
feature_hash=ab0c0faf2e26bca0cf4edce1f48b57dc8dd6c2b25831719dc6f9b4d497d463bf
```

但 E3 manifest 没有暴露完整 78-feature list。`feature_availability_audit.csv`
也将 `feature_list_available=False`、`has_all_model_features_for_inference=False`
标为阻断。E3 可见 CSV 表头为：

```text
control_row_id,date,date_str,instrument,e2_sample_split,qlib_score_raw,qlib_rank,top50_flag,
future_excess_return_rank_10d,relevance_10d_top_heavy,phasee3_extended_oos_ltr_score,
phasee3_extended_oos_ltr_rank
```

这证明现有 E3 CSV 是 score/label 行，不是 feature-only inference input。
因此 E3 不可直接 PASS；但也不能据此断言必须重训，因为模型文件和 feature hash 仍在。

### 3.2 S2C 模型与输入缺口

S2C 模型文件存在：

```text
data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2c_fresh_ltr_sample_training/phase_s2c_ltr_model.pkl
```

`phase_s2c_ltr_model_manifest.json` 明确列出 34 个 feature columns；
`phase_s2c_training_manifest.json` 声明 `parameter_search_performed=false`
和 `no_test_feedback_for_tuning=true`。这足以支持“不必立刻重训”的判断。

但 `phase_s2c_ltr_samples.csv` 表头同时包含：

```text
future_return_5d, future_return_10d, future_return_20d,
future_excess_return_5d, future_excess_return_10d, future_excess_return_20d,
future_excess_return_rank_5d, future_excess_return_rank_10d, future_excess_return_rank_20d,
topk_forward_bucket, ltr_relevance_label,
label_start_date, label_end_date_5d, label_end_date_10d, label_end_date_20d
```

`phase_s2c_ltr_score_rank.csv` 也包含 `label_start_date`、
`label_end_date_10d`、`ltr_relevance_label`。两者均缺 `available_at`。
按照 `MODEL_SIGNAL_CONTRACT_CN.md` 和 `NEW_MODEL_REVIEWER_CHECKLIST_CN.md`，
这些字段不得进入策略可消费输入或标准信号链路。

因此 S2C 可作为 repair 起点，但不是可直接用于 MTRC1B 的标准 PIT-clean
inference input。

### 3.3 qlib full-rank / top50 alignment

E3 有 qlib full-rank source：

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/phase_e1_frozen_qlib_training_and_oos_score/phasee1_raw_oos_score_rank_2023_2026.csv
```

它覆盖 `2023-01-03..2026-05-07`，但语义仍是 qlib rank/score，不是 LTR
`buy_score`。S2C 则使用 split-aligned fresh qlib source，`top50_alignment_feasibility.csv`
明确标注它尚未证明与 MTRC/MTR2_R qlib full-rank source 等价。

所以 MTRC1A 正确阻断了“把 S2C 新 lineage 静默替代 MTR2_R/E3 lineage”的风险。

## 4. 为什么不是 PASS

PASS 需要同时证明：

```text
existing model usable without retraining
feature/input rows available for extended top50 inference
PIT/available_at feasible
ModelSignal mapping feasible
research-only output path defined
production boundary clean
```

当前只满足模型文件存在、mapping 可设计、research-only 边界清晰。关键缺口仍是：

1. E3 缺完整 78-feature list 和 PIT-clean feature input。
2. S2C 虽有 feature schema，但样本/score 表带 label/future/audit 列且缺 `available_at`。
3. 两条 lineage 都没有标准 extended top50 LTR ModelSignalArtifact 输入合同。
4. S2C 与 MTR2_R/E3 qlib full-rank alignment 尚未证明等价。

因此不能进入 `PASS_READY_FOR_MTRC1B_RESEARCH_ONLY_EXTENDED_TOP50_LTR_SIGNAL_BUILD`。

## 5. 为什么不是 STOP_NEEDS_MODEL_RETRAIN_OR_FEATURE_REBUILD

不升级为重训/大规模重建的原因：

1. E3 与 S2C 的 LTR model `.pkl` 均存在，且模型 manifest 可读。
2. S2C feature schema 完整，样本表覆盖 `2017-01-10..2026-05-07`，可作为
   构建 feature-only inference input contract 的来源。
3. S2C split / label audit 声明 purge 和 split purity pass；当前问题是不能把训练样本
   或带 label 的 score 表直接喂给 ModelSignal 链路。
4. E3 的 78-feature schema 缺失是 lineage repair blocker；只有在 `MTRC1A_R`
   无法恢复 exact feature schema 或无法证明 PIT input 后，才应考虑升级到
   retrain / feature rebuild。

## 6. 越界审查

未发现 MTRC1A 执行者越界证据。

`manifest.json`、`validator_report.json`、`forbidden_scope_audit.csv`、
`production_boundary_audit.csv` 与 builder 脚本一致显示：

- 未训练模型；
- 未执行模型 inference 或生成新 score；
- 未生成 ModelSignalArtifact；
- 未生成 broad bridge；
- 未生成 OrderIntent / ReplayResult；
- 未跑 replay；
- 未调参、未新增策略候选、未修改 M2 参数；
- 未 provider publish；
- 未 accepted latest switch；
- 未修改 production/default/latest/provider/frontend/API/Agent/daily；
- 未发出 target weight / target position / quantity / broker 指令。

工作树本身已有大量 dirty/untracked 文件，本审查不将这些归因给 MTRC1A。

## 7. 下一步

接受 `STOP_NEEDS_LTR_INFERENCE_LINEAGE_REPAIR` 后，下一步应开：

```text
MTRC1A_R_LTR_INFERENCE_LINEAGE_REPAIR
```

目标不是训练、不是 inference、不是 replay，也不是生成 ModelSignalArtifact；
目标是构建并审计 PIT-clean inference input contract，使后续 MTRC1B 是否可生成
research-only extended top50 LTR signal 有明确、可验证的输入侧证据。

工作文档已写入：

```text
docs/tw_portfolio_decision_model/POLICY_MTRC1A_R_LTR_INFERENCE_LINEAGE_REPAIR_WORK_CN.md
```

最终结论：

```text
STOP_NEEDS_LTR_INFERENCE_LINEAGE_REPAIR
```
