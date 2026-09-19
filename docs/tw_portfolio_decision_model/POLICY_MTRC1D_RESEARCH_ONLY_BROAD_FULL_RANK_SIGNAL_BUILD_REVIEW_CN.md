---
created_at: 2026-06-28
status: review
phase: MTRC1D_RESEARCH_ONLY_BROAD_FULL_RANK_SIGNAL_BUILD
reviewer: MTRC1D
readonly_only: true
simulation_only: true
production_allowed: false
accepted_verdict: PASS_READY_FOR_MTRC1E_RESEARCH_ONLY_BROAD_SIGNAL_REVIEW_OR_NEXT_DIAGNOSTIC_CONTRACT
next_phase_recommendation: MTRC1E_RESEARCH_ONLY_BROAD_SIGNAL_REVIEW_OR_NEXT_DIAGNOSTIC_CONTRACT
---

# POLICY_MTRC1D_RESEARCH_ONLY_BROAD_FULL_RANK_SIGNAL_BUILD_REVIEW_CN

生成日期：2026-06-28

## 1. Verdict

```text
PASS_READY_FOR_MTRC1E_RESEARCH_ONLY_BROAD_SIGNAL_REVIEW_OR_NEXT_DIAGNOSTIC_CONTRACT
```

审查接受 MTRC1D 执行结果。当前证据足以确认：MTRC1D 只构建了 research-only broad full-rank `ModelSignalArtifact`，未生成 OrderIntent、ReplayResult，未运行收益 replay，未写 production/default/latest/provider/frontend/API/Agent/daily/config registry。

本 PASS 只放行进入另行授权的 `MTRC1E_RESEARCH_ONLY_BROAD_SIGNAL_REVIEW_OR_NEXT_DIAGNOSTIC_CONTRACT`。不得自动进入收益 replay、OrderIntent、ReplayResult、MTRC2、production readiness、默认策略/模型切换、provider/latest/frontend/API/Agent/daily 接入、broker、quick-trade、order、target_weight、target_position 或 quantity 指令。

S2C 仍是新的 research lineage，不等价于 MTR2_R/E3；MTRC1D broad signal 不能解除 MTR5 的 `clean_extended_lineage_found=false` blocker。

## 2. Findings

### Critical

无。

### High

无。

### Medium

无。

### Low

1. 仓库当前存在大量既有 dirty/untracked 文件，审查未将其归因于 MTRC1D，也未回退任何他人修改。本次审查只新增本 review 文档。
2. `available_at <- date` 仍是 `S2C_LEGACY_RESEARCH_DAILY_VISIBLE` research-only policy，不构成生产 provider timing 证明。
3. MTRC1D broad artifact 只解决 S2C full-rank visibility 的 research-only signal 表达，不证明收益、集中度改善、robustness 或 production readiness。

## 3. Evidence Checked

必读文档已读取并核对：

- `docs/tw_portfolio_decision_model/POLICY_MTRC1D_RESEARCH_ONLY_BROAD_FULL_RANK_SIGNAL_BUILD_WORK_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_MTRC1D_RESEARCH_ONLY_BROAD_FULL_RANK_SIGNAL_BUILD_EXECUTION_REPORT_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_MTRC1C_RESEARCH_ONLY_BROAD_BRIDGE_CONTRACT_REVIEW_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_MTRC1B_RESEARCH_ONLY_EXTENDED_TOP50_LTR_SIGNAL_BUILD_REVIEW_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_MTRC_RESEARCH_ONLY_CONTINUATION_MAINLINE_CN.md`
- `docs/tw_modular_contracts/MODEL_SIGNAL_CONTRACT_CN.md`
- `docs/tw_modular_contracts/MODEL_SIGNAL_EXTENSION_SCHEMA_CN.md`

脚本已读取并核对：

- `scripts/build_tw_policy_mtrc1d_research_only_broad_full_rank_signal.py`

MTRC1D 输出目录下允许产物与 `negative_samples/` 已检查：

- `manifest.json`
- `signals.csv`
- `schema.json`
- `coverage_audit.csv`
- `top50_equivalence_audit.csv`
- `non_top50_visibility_audit.csv`
- `non_top50_buy_hard_fail_audit.csv`
- `extension_schema_audit.csv`
- `forbidden_field_audit.csv`
- `lineage_boundary_audit.csv`
- `available_at_policy_audit.csv`
- `source_trace_audit.csv`
- `validator_report.json`
- `diagnostic_findings.md`
- `negative_samples/non_top50_buy_score_present.csv`
- `negative_samples/non_top50_ranked_for_buy.json`
- `negative_samples/missing_mtrc1b_top50_row.csv`
- `negative_samples/changed_mtrc1b_top50_score.csv`

## 4. 独立复算结果

独立读取 MTRC1B `signals.csv`、MTRC1D broad `signals.csv` 与 S2B `phase_s2b_post_filter_score_rank.csv` 后复算：

```text
MTRC1B top50 rows = 113000
MTRC1D broad rows = 169366
S2B qlib rows = 169366
MTRC1D top50 keys = 113000
MTRC1D non-top50 visibility-only rows = 56366
date_range = 2017-01-10..2026-05-07
date_count = 2260
rows_per_date = 51..150
duplicate date,instrument = 0
```

Top50 等价复算：

```text
top50 outer join not both = 0
top50 buy_score mismatch vs MTRC1B = 0
top50 raw_score mismatch vs MTRC1B = 0
top50 score_rank mismatch vs MTRC1B = 0
top50 signal_asof mismatch vs MTRC1B = 0
top50 available_at mismatch vs MTRC1B = 0
top50 candidate_rank mismatch vs MTRC1B = 0
top50 full_qlib_rank mismatch vs MTRC1B = 0
top50 candidate_rank mismatch vs S2B qlib_rank = 0
top50 full_qlib_rank mismatch vs S2B qlib_rank = 0
top50 visibility role bad = 0
```

Non-top50 复算：

```text
non_top50_not_from_s2b_rank_gt50 = 0
s2b_rank_gt50_missing_from_output = 0
non_top50_candidate_rank_le50 = 0
non_top50_buy_score_present = 0
non_top50_raw_score_present = 0
non_top50_score_rank_present = 0
non_top50_buy_eligible_not_false = 0
```

结论：broad `signals.csv` 完整包含 MTRC1B top50；top50 的 `buy_score/raw_score/score_rank/signal_asof/available_at` 与 MTRC1B 逐值等价；top50 的 `candidate_rank/full_qlib_rank` 同时等于 MTRC1B 与 S2B `qlib_rank`；non-top50 全部来自 S2B `qlib_rank > 50`，且只具备 visibility-only 语义。

## 5. Negative Samples

四类 negative samples 均存在，且 `validator_report.json` 声明 `failed_as_expected=true`：

- `non_top50_buy_score_present.csv`：构造 `candidate_rank=51` 且 `buy_score/raw_score/score_rank` 非空，预期 fail。
- `non_top50_ranked_for_buy.json`：构造 non-top50 被 buy ranking consumer 使用，预期 fail。
- `missing_mtrc1b_top50_row.csv`：构造缺失 MTRC1B top50 key，预期 fail。
- `changed_mtrc1b_top50_score.csv`：构造 top50 `buy_score` 被改写，预期 fail。

审查接受 `negative_samples_fail_as_expected=true`。这些负例覆盖了 non-top50 buy hard-fail、top50 row completeness 与 top50 score immutability。

## 6. Manifest / Schema / Extension Review

`manifest.json` 与 `validator_report.json` 明确声明：

```text
readonly_only = true
simulation_only = true
research_only = true
production_allowed = false
provider_publish_allowed = false
accepted_latest_switch_allowed = false
frontend_default_switch_allowed = false
broker_authorized = false
model_training_performed = false
model_tuning_performed = false
model_inference_performed = false
ltr_score_recomputed = false
order_intent_generated = false
replay_result_generated = false
replay_performed = false
```

`signals.csv` 包含 ModelSignal core fields，并只新增两个受控 extension fields：

```text
ext_mtrc1d_visibility_role
ext_mtrc1d_non_top50_buy_eligible
```

`schema.json` 与 `manifest.json` 均按 `MODEL_SIGNAL_EXTENSION_SCHEMA_CN.md` 声明 extension metadata：

```text
schema_version = model_signal_extension_v1
semantic_role = diagnostic
availability_policy = S2C_LEGACY_RESEARCH_DAILY_VISIBLE
allowed_consumers = audit, validator, mtrc_research_only_diagnostic
ranking_allowed = false
required_for_core_replay = false
```

`extension_schema_audit.csv` 两个字段均 pass。未发现 extension 改变 core field 语义或赋予 non-top50 buy priority。

## 7. Forbidden Actions Audit

审查未发现 MTRC1D 执行 forbidden actions：

- 未训练模型、未调参、未模型 inference、未重新计算 LTR score。
- 未新增策略候选，未修改 `M2_hold_rank_buffer_100`。
- 未生成 OrderIntentArtifact 或 ReplayResultArtifact。
- 未运行收益 replay。
- 未 provider publish / refresh，未 accepted latest switch。
- 未写 production/default/latest/provider/frontend/API/Agent/daily/config registry。
- 未写 monitor config / scan / alerts。
- 未 broker、quick-trade、real order。
- 未输出 target_weight、target_position 或 quantity instruction。
- 未将 S2C 描述为 MTR2_R/E3 等价。
- 未解除 MTR5 `clean_extended_lineage_found=false` blocker。

脚本写入路径集中于：

```text
data_tw/experiments/policy_mtr_research_only_continuation/mtrc1d_research_only_broad_full_rank_signal_build/
docs/tw_portfolio_decision_model/POLICY_MTRC1D_RESEARCH_ONLY_BROAD_FULL_RANK_SIGNAL_BUILD_EXECUTION_REPORT_CN.md
```

输出目录未发现额外命名为 order/intent/replay/return/pnl/provider/latest/frontend/agent/daily/registry/config 的产物。

## 8. Limitations

MTRC1D 不提供以下证明：

- 不证明 MTR2_R/E3 等价。
- 不证明 MTR5 production blocker 已解除。
- 不证明收益、集中度、monthly stability、risk-off 或 drawdown 表现。
- 不授权任何 replay、OrderIntent、ReplayResult 或 production/default/latest/provider/frontend/API/Agent/daily 接入。

## 9. 下一步文档控制

建议下一步只能开：

```text
MTRC1E_RESEARCH_ONLY_BROAD_SIGNAL_REVIEW_OR_NEXT_DIAGNOSTIC_CONTRACT
```

MTRC1E 边界：

- 只能审查 MTRC1D broad signal 是否足以支持后续 concentration/window diagnostic 的合同。
- 可以继续检查 broad signal row semantics、visibility-only non-top50 边界、negative validator 覆盖和 downstream diagnostic contract 需求。
- 不得自动进入收益 replay、OrderIntent、ReplayResult 或 MTRC2。
- 若后续要进入 replay、MTRC2 或任何 downstream artifact build，必须另写工作文档并再次授权。
- 仍不得修改 production/default/latest/provider/frontend/API/Agent/daily/config registry。
- 仍不得 provider publish、accepted latest switch、monitor write、broker、quick-trade、order、target_weight、target_position 或 quantity instruction。

## 10. Command For Next Executor

```text
请执行 MTRC1E_RESEARCH_ONLY_BROAD_SIGNAL_REVIEW_OR_NEXT_DIAGNOSTIC_CONTRACT。
只审查 MTRC1D research-only broad ModelSignalArtifact 是否足以支持下一步 diagnostic contract；不得实现 replay、OrderIntent、ReplayResult、MTRC2、production/default/latest/provider/frontend/API/Agent/daily/config registry 接入。
```
