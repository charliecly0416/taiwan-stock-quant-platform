---
created_at: 2026-06-28
status: review
phase: MTRC1A_R_LTR_INFERENCE_LINEAGE_REPAIR
reviewer: MTRC1A_R
readonly_only: true
simulation_only: true
production_allowed: false
accepted_verdict: PASS_READY_FOR_MTRC1B_RESEARCH_ONLY_EXTENDED_TOP50_LTR_SIGNAL_BUILD
next_work_doc: docs/tw_portfolio_decision_model/POLICY_MTRC1B_RESEARCH_ONLY_EXTENDED_TOP50_LTR_SIGNAL_BUILD_WORK_CN.md
---

# POLICY_MTRC1A_R_LTR_INFERENCE_LINEAGE_REPAIR_REVIEW_CN

生成日期：2026-06-28

## 1. Verdict

```text
PASS_READY_FOR_MTRC1B_RESEARCH_ONLY_EXTENDED_TOP50_LTR_SIGNAL_BUILD
```

审查接受 MTRC1A_R 执行者 verdict。当前证据足以进入 MTRC1B 的
`research-only extended top50 LTR signal build`，但只限基于本次声明的
`S2C_SPLIT_ALIGNED_FRESH_LTR` 合同生成 research-only signal。

本 PASS 不代表 S2C 等价于 MTR2_R/E3 lineage，不授权 broad bridge、
OrderIntent、ReplayResult、收益 replay、production/default/latest/provider/frontend/API/Agent/daily
改动，也不授权任何 broker、quick-trade、order、target_weight、target_position
或 quantity 指令。

## 2. 审查范围

已读取并复核：

- `docs/tw_portfolio_decision_model/POLICY_MTRC1A_R_LTR_INFERENCE_LINEAGE_REPAIR_WORK_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_MTRC1A_R_LTR_INFERENCE_LINEAGE_REPAIR_EXECUTION_REPORT_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_MTRC1A_EXTENDED_TOP50_LTR_INFERENCE_FEASIBILITY_REVIEW_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_MTRC_RESEARCH_ONLY_CONTINUATION_MAINLINE_CN.md`
- `docs/tw_modular_contracts/MODEL_SIGNAL_CONTRACT_CN.md`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc1a_r_ltr_inference_lineage_repair/` 下全部 15 个 artifacts
- S2C model manifest、sample schema、sample 表头、score/rank 表头、training manifest、missing/label purity audits
- MTRC1A_R builder 脚本的输出边界和关键读写逻辑

本审查只新增本报告和下一步 MTRC1B 工作文档；未修改执行者产物。

## 3. Lineage 选择复核

执行者明确选择且只选择：

```text
S2C_SPLIT_ALIGNED_FRESH_LTR
```

`lineage_selection_decision.csv` 将 `E3/MTR2_R-compatible` 标为未选择，理由是
E3 仍缺 exact 78-feature order 和 PIT-clean feature-only input。`manifest.json`、
`feature_schema_contract.json`、`inference_input_contract.json` 与
`diagnostic_findings.md` 均声明 S2C 是 split-aligned fresh lineage，不是 MTR2_R/E3
lineage，且不得混用。

审查未发现 E3 模型、MTR2_R broad signal、E3 qlib full-rank artifact 或 S2C
features 被混合成同一 lineage。`qlib_rank_alignment_contract.csv` 也明确写明
alignment 只在 S2C split-aligned fresh lineage 内可接受，不等价于 MTR2_R/E3。

## 4. Feature / Input Contract 复核

S2C 源 `phase_s2c_ltr_model_manifest.json` 声明：

```text
feature_count = 34
model_family = LightGBM.LGBMRanker
label_column = ltr_relevance_label
```

审查独立复算结果：

```text
feature_count_contract = 34
feature_count_manifest = 34
contract_equals_manifest = True
contract_equals_schema = True
required_input_count = 38
forbidden_retained = []
```

`required_input_count=38` 对应：

```text
date, instrument, signal_asof, available_at + 34 S2C feature columns
```

这符合 MTRC1A_R 要求。合同只保留 key、asof/available_at 映射字段和 34 个
模型 feature columns；未把 label、future、audit、training eligibility 字段纳入
inference-ready boundary。

`Bollinger_position` 被保留是合理的：它出现在 S2C 34-feature manifest/schema 中，
语义为技术指标，不是交易持仓字段 `position`。

## 5. Forbidden 字段剔除复核

源 `phase_s2c_ltr_samples.csv` 表头确实包含不应进入 inference input 的字段，包括：

```text
future_return_5d
future_return_10d
future_return_20d
future_excess_return_5d
future_excess_return_10d
future_excess_return_20d
future_excess_return_rank_5d
future_excess_return_rank_10d
future_excess_return_rank_20d
topk_forward_bucket
ltr_relevance_label
label_start_date
label_end_date_5d
label_end_date_10d
label_end_date_20d
regime_segment
label_complete_5d
label_complete_10d
label_complete_20d
feature_complete
sample_complete
split_purity_keep
training_row_eligible
```

`forbidden_column_exclusion_audit.csv` 与 `inference_input_columns_audit.csv`
将上述 future/label/training 字段明确标记为不可策略消费、不可作为 MTRC1B
inference input。审查未发现 realized_pnl、action、holding、position、
target_position、target_weight、order_qty、execution_*、broker_order_id 等字段被保留。

## 6. PIT / available_at 复核

MTRC1A_R 采用：

```text
signal_asof <- date
feature_asof <- date
available_at <- date
policy_id = S2C_LEGACY_RESEARCH_DAILY_VISIBLE
```

该政策足以进入 MTRC1B 的 research-only signal build，因为 MTRC1A_R 的目标是
建立 input contract，而不是证明生产级数据发布时间。`pit_available_at_policy.md`
已明确 production use forbidden，且 `inference_input_contract.json` 声明
`inference_input_is_contract_only=true`。

限制也必须保留：`available_at <- date` 是 legacy daily-visible research policy，
不是已生成信号，也不是生产 timing 证明。若后续要进入 production readiness，必须另做
生产级 available_at / provider timing 审查。

## 7. qlib rank / full_qlib_rank alignment 复核

执行者声明：

```text
sample_rows_checked = 169366
missing_key_rows = 0
qlib_rank_mismatch_rows = 0
qlib_score_mismatch_rows = 0
```

审查独立复算结果一致：

```text
sample_rows = 169366
sample_keys = 169366
duplicate_keys = 0
sample_dates = 2017-01-10..2026-05-07
qlib_source_rows = 169366
matched = 169366
missing = 0
rank_mismatch = 0
score_mismatch = 0
```

因此 MTRC1B 可以在 S2C lineage 内使用：

```text
candidate_rank <- qlib_rank
full_qlib_rank <- qlib_rank
```

但该 alignment 只证明 S2C samples 与 S2B fresh qlib rank source 在
`date,instrument,qlib_rank,qlib_score_raw` 上一致；它不证明 S2C 的 qlib base 与
MTR2_R/E3 full-rank source 等价。

## 8. MTRC1B Gate 复核

`mtrc1b_readiness_gate.csv` 全部为 True：

```text
exact_feature_schema_declared
feature_column_order_declared
feature_only_input_contract_exists
date_instrument_unique_key_declared
coverage_window_declared
available_at_policy_declared_and_audited
forbidden_columns_excluded
qlib_rank_full_qlib_rank_mapping_declared
lineage_not_mixed
research_only_output_path_clean
production_boundary_clean
```

审查认为这些 gate 支撑 PASS。PASS 的对象是可供 MTRC1B 使用的
PIT-clean inference input contract，不是已有 score rows。

## 9. 越界审查

`manifest.json`、`forbidden_scope_audit.csv`、`production_boundary_audit.csv`、
`validator_report.json` 和 builder 逻辑一致显示：

- 未训练模型；
- 未执行 predict / inference 生成新 LTR score；
- 未生成 ModelSignalArtifact 或 `signals.csv`；
- 未生成 broad bridge；
- 未生成 OrderIntent / ReplayResult；
- 未跑收益 replay；
- 未调参、未新增候选、未修改 M2 参数；
- 未 provider publish；
- 未 accepted latest switch；
- 未修改 production/default/latest/provider/frontend/API/Agent/daily；
- 未发出 broker、quick-trade、order、target_weight、target_position、quantity 指令。

本仓库当前工作树存在大量既有 dirty/untracked 文件；本审查不将这些归因给
MTRC1A_R，且未回退任何他人改动。

## 10. 下一步

接受 PASS 后，下一步可开：

```text
MTRC1B_RESEARCH_ONLY_EXTENDED_TOP50_LTR_SIGNAL_BUILD
```

MTRC1B 只允许在 research-only 目录中，基于本次 S2C contract 生成标准
extended top50 LTR ModelSignalArtifact。MTRC1B 不得 broad bridge，不得 replay，
不得修改 production/default/latest/provider/frontend/API/Agent/daily，也不得把
S2C 静默说成 MTR2_R/E3 lineage。

工作文档已写入：

```text
docs/tw_portfolio_decision_model/POLICY_MTRC1B_RESEARCH_ONLY_EXTENDED_TOP50_LTR_SIGNAL_BUILD_WORK_CN.md
```

最终结论：

```text
PASS_READY_FOR_MTRC1B_RESEARCH_ONLY_EXTENDED_TOP50_LTR_SIGNAL_BUILD
```
