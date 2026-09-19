---
created_at: 2026-06-28
status: review
phase: MTRC1B_RESEARCH_ONLY_EXTENDED_TOP50_LTR_SIGNAL_BUILD
reviewer: MTRC1B
readonly_only: true
simulation_only: true
production_allowed: false
accepted_verdict: PASS_READY_FOR_MTRC1C_RESEARCH_ONLY_BROAD_BRIDGE_CONTRACT
next_phase_recommendation: MTRC1C_RESEARCH_ONLY_BROAD_BRIDGE_CONTRACT
---

# POLICY_MTRC1B_RESEARCH_ONLY_EXTENDED_TOP50_LTR_SIGNAL_BUILD_REVIEW_CN

生成日期：2026-06-28

## 1. Verdict

```text
PASS_READY_FOR_MTRC1C_RESEARCH_ONLY_BROAD_BRIDGE_CONTRACT
```

审查接受 MTRC1B 执行结果。当前证据足以确认：

```text
MTRC1B 已基于 S2C_SPLIT_ALIGNED_FRESH_LTR 生成 research-only extended top50 LTR ModelSignalArtifact。
```

本 PASS 只放行进入另行授权的 MTRC1C research-only broad bridge contract 设计/审查，不授权直接 broad bridge、不授权 OrderIntent、ReplayResult、收益 replay、MTRC2 诊断、production/default/latest/provider/frontend/API/Agent/daily 改动，也不授权 broker、quick-trade、order、target_weight、target_position 或 quantity 指令。

S2C 仍是新的 research lineage，不等价于 MTR2_R/E3；本次 signal 不能解除 MTR5 的 `clean_extended_lineage_found=false` blocker。

## 2. 审查范围

已读取并复核：

- `docs/tw_portfolio_decision_model/POLICY_MTRC1B_RESEARCH_ONLY_EXTENDED_TOP50_LTR_SIGNAL_BUILD_WORK_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_MTRC1B_RESEARCH_ONLY_EXTENDED_TOP50_LTR_SIGNAL_BUILD_EXECUTION_REPORT_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_MTRC1A_R_LTR_INFERENCE_LINEAGE_REPAIR_REVIEW_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_MTRC_RESEARCH_ONLY_CONTINUATION_MAINLINE_CN.md`
- `docs/tw_modular_contracts/MODEL_SIGNAL_CONTRACT_CN.md`
- `docs/tw_modular_contracts/MODEL_SIGNAL_EXTENSION_SCHEMA_CN.md`
- `docs/tw_modular_contracts/NEW_MODEL_REVIEWER_CHECKLIST_CN.md`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc1b_research_only_extended_top50_ltr_signal_build/` 下全部 12 个 artifacts
- S2C model manifest、sample schema、sample CSV 表头、S2B qlib rank source 表头
- MTRC1B builder 的读写边界和关键 mapping 逻辑

本审查只新增本报告；未修改执行者产物。

## 3. ModelSignalArtifact 复核

`signals.csv` 独立复算结果：

```text
rows = 113000
columns = 14
date_range = 2017-01-10..2026-05-07
date_count = 2260
rows_per_date_min = 50
rows_per_date_max = 50
instrument_count = 150
missing_required_fields = []
date_instrument_duplicate = 0
```

必需字段完整：

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

`schema.json` 将 primary key 声明为 `date,instrument`，`manifest.json` 与 `validator_report.json` 均声明 artifact 为 research-only、production_allowed=false。

## 4. Lineage 与非等价声明

产物明确且一致声明：

```text
lineage_id = S2C_SPLIT_ALIGNED_FRESH_LTR
S2C is a new research lineage and is not equivalent to MTR2_R/E3.
This artifact must not be used to clear MTR5 clean_extended_lineage_found=false.
```

`lineage_boundary_audit.csv` 显示：

```text
e3_model_artifact_used = False
mtr2r_broad_signal_used = False
mtr2r_e3_full_rank_source_used = False
broad_bridge_generated = False
mtr5_blocker_cleared_by_s2c = False
```

审查未发现 E3、MTR2_R broad signal 或 MTR2_R/E3 full-rank source 被混入本产物。

## 5. Top50 Universe 与 Rank Mapping

独立 join S2C source samples 后复算：

```text
candidate_rank_min_max = 1.0..50.0
full_qlib_rank_min_max = 1.0..50.0
candidate_rank_gt50 = 0
full_qlib_rank_gt50 = 0
merge_missing_source_top50 = 0
candidate_rank_source_mismatch = 0
full_qlib_rank_source_mismatch = 0
```

因此本产物只保留 `top50_flag == 1 and qlib_rank <= 50` rows，未扩大 buy universe。

`candidate_rank` 与 `full_qlib_rank` 均等于 S2C `qlib_rank`。这只在 S2C lineage 内成立，不表示 MTR2_R/E3 full-rank visibility 已修复。

## 6. Score 可复核性

`buy_score` 与 `raw_score` 独立检查：

```text
raw_score_equals_buy_score_mismatch = 0
score_rank_mismatch = 0
```

`score_rank` 为每日 `buy_score` 降序、`instrument` 升序 tie-break 的 rank。`legacy_mapping_audit.csv` 与 `qlib_rank_alignment_audit.csv` 的 mismatch 均为 0。

## 7. Forbidden Fields 与 Source Trace

`signals.csv` 只包含 14 个 core fields；按 forbidden term 扫描未发现：

```text
future
label
relevance
realized
order
position
execution
broker
target
holding
action
quantity
pnl
return
```

`forbidden_field_audit.csv` 确认源 S2C samples 中的 future/label/audit/training 字段未进入 signals，包括：

```text
future_return_*
future_excess_return_*
topk_forward_bucket
ltr_relevance_label
label_start_date
label_end_date_*
label_complete_*
feature_complete
sample_complete
split_purity_keep
training_row_eligible
```

`source_artifact`、`source_model_artifact`、`source_feature_artifact` 均无空值，且各自唯一来源为：

```text
source_artifact = phase_s2c_ltr_samples.csv
source_model_artifact = phase_s2c_ltr_model.pkl
source_feature_artifact = MTRC1A_R inference_input_contract.json
```

## 8. 只读与越界审查

`manifest.json`、`validator_report.json`、`diagnostic_findings.md` 与 builder 逻辑一致显示：

- 已执行 research-only inference；
- 未训练模型；
- 未调参；
- 未根据收益或 replay 表现筛选模型；
- 未新增候选；
- 未生成 broad bridge；
- 未生成 OrderIntent；
- 未生成 ReplayResult；
- 未跑收益 replay；
- 未修改 production/default/latest/provider/frontend/API/Agent/daily；
- 未 provider publish；
- 未 accepted latest switch；
- 未写 monitor config / scan / alerts；
- 未 broker / quick-trade / real order；
- 未输出 target_weight / target_position / quantity instruction。

builder 的写路径集中在 MTRC1B 输出目录与 MTRC1B 执行报告；本审查未发现写入 production/default/frontend/API/Agent/daily/provider/latest 的路径。

当前工作树存在大量既有 dirty/untracked 文件；本审查不将这些归因于 MTRC1B，且未回退任何他人改动。

## 9. Matplotlib Cache Warning

在 MTRC1B 执行报告、产物目录和 builder 中未检索到 `matplotlib`、`MPLCONFIGDIR`、cache warning 或相关依赖。builder 未导入 matplotlib。

即使执行环境曾出现 matplotlib cache warning，也不会改变 `signals.csv`、schema、manifest、rank mapping 或 forbidden-field audit；本审查判定其对 MTRC1B signal artifact 无实质影响。

## 10. 风险与限制

1. `available_at <- date` 只是在 `S2C_LEGACY_RESEARCH_DAILY_VISIBLE` 下的 research-only policy，不是生产级 provider timing 证明。
2. 本产物是 top50-only LTR signal，不包含 broad full-rank visibility。
3. S2C lineage 与 MTR2_R/E3 non-equivalent；不能用本 PASS 解除 MTR5 clean lineage blocker。
4. 当前产物未证明收益、集中度、robustness 或 production readiness；这些都不是 MTRC1B 的审查目标。

## 11. 下一步建议

建议下一步开：

```text
MTRC1C_RESEARCH_ONLY_BROAD_BRIDGE_CONTRACT
```

MTRC1C 只能先写 contract / feasibility / validator 设计，必须另行授权后才能构建 broad bridge。MTRC1C 至少要明确：

- broad rows 只能用于既有持仓 hold/sell visibility，不得扩大 top50 buy universe；
- top50 内 `buy_score/raw_score/score_rank` 必须与本 MTRC1B signal 等价；
- non-top50 rows 不得生成 LTR buy priority；
- candidate_rank/full_qlib_rank 的来源、字段语义、available_at policy 和 PIT 限制必须单独声明；
- 输出不得直接进入 OrderIntent、ReplayResult、收益 replay、production/default/latest/provider/frontend/API/Agent/daily；
- S2C lineage 仍不能解除 MTR2_R/E3 clean lineage blocker。

不建议直接进入 MTRC2。MTRC2 的 extended concentration / window diagnostic 至少需要先有经过审查的 broad bridge contract，并在另行授权后生成合法的 research-only downstream artifacts。

最终结论：

```text
PASS_READY_FOR_MTRC1C_RESEARCH_ONLY_BROAD_BRIDGE_CONTRACT
```
