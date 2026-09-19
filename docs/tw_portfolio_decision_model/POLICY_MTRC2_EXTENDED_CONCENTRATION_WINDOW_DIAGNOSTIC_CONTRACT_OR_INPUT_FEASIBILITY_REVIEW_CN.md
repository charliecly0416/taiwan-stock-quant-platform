---
created_at: 2026-06-28
status: review
phase: MTRC2_EXTENDED_CONCENTRATION_WINDOW_DIAGNOSTIC_CONTRACT_OR_INPUT_FEASIBILITY
reviewer: MTRC2
readonly_only: true
simulation_only: true
production_allowed: false
accepted_verdict: PASS_READY_FOR_MTRC2_R_SAME_SIGNAL_ORDER_REPLAY_INPUT_BUILD_CONTRACT
next_phase_recommendation: MTRC2_R_SAME_SIGNAL_ORDER_REPLAY_INPUT_BUILD_CONTRACT
---

# POLICY_MTRC2_EXTENDED_CONCENTRATION_WINDOW_DIAGNOSTIC_CONTRACT_OR_INPUT_FEASIBILITY_REVIEW_CN

生成日期：2026-06-28

## 1. Verdict

```text
PASS_READY_FOR_MTRC2_R_SAME_SIGNAL_ORDER_REPLAY_INPUT_BUILD_CONTRACT
```

审查接受 MTRC2 执行结果。当前阶段只完成了 input feasibility / diagnostic contract：确认 MTRC1D S2C broad `ModelSignalArtifact` 可作为后续 diagnostic 的信号输入；同时确认当前不存在合法 same-candidate / same-parameter / same-signal 的 OrderIntent、ReplayResult 或 ledger 输入。

本 PASS 只放行进入另行授权的 `MTRC2_R_SAME_SIGNAL_ORDER_REPLAY_INPUT_BUILD_CONTRACT`。不得直接进入 MTRC3，不得直接运行收益 replay，不得生成 OrderIntent、ReplayResult、ledger、ModelSignal，不得实现 concentration/window diagnostic 计算，不得把旧 MTR2_R/E3 replay 作为 S2C/MTRC1D lineage input，不得写 production/default/latest/provider/frontend/API/Agent/daily/config registry。

## 2. Findings

### Critical

无。

### High

无。

### Medium

无。

### Low

1. `validator_report.json` 的 `checks.same_signal_legal_input_exists=false` 与最终 PASS 并不矛盾，因为 MTRC2 work doc 明确允许在 MTRC1D signal ready 但无合法 same-signal order/replay/ledger 时，推荐 `PASS_READY_FOR_MTRC2_R_SAME_SIGNAL_ORDER_REPLAY_INPUT_BUILD_CONTRACT`。该 PASS 是合同构建放行，不是 MTRC3 diagnostic 放行。
2. 仓库已有大量 dirty/untracked 文件，本审查未归因、未回退、未修改。此次只新增本 review 文档。

## 3. Evidence Checked

必读文档已读取并核对：

- `docs/tw_portfolio_decision_model/POLICY_MTRC2_EXTENDED_CONCENTRATION_WINDOW_DIAGNOSTIC_CONTRACT_OR_INPUT_FEASIBILITY_WORK_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_MTRC2_EXTENDED_CONCENTRATION_WINDOW_DIAGNOSTIC_CONTRACT_OR_INPUT_FEASIBILITY_EXECUTION_REPORT_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_MTRC1E_RESEARCH_ONLY_BROAD_SIGNAL_REVIEW_OR_NEXT_DIAGNOSTIC_CONTRACT_REVIEW_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_MTRC_RESEARCH_ONLY_CONTINUATION_MAINLINE_CN.md`

脚本已读取并核对：

- `scripts/build_tw_policy_mtrc2_extended_concentration_window_diagnostic_contract_or_input_feasibility.py`

MTRC2 输出目录全部产物已检查：

- `manifest.json`
- `mtrc1d_signal_input_readiness.csv`
- `same_candidate_same_parameter_input_inventory.csv`
- `order_intent_input_feasibility.csv`
- `replay_result_input_feasibility.csv`
- `ledger_input_feasibility.csv`
- `old_mtr_lineage_non_equivalence_audit.csv`
- `diagnostic_input_gap_analysis.csv`
- `mtrc2_diagnostic_contract.csv`
- `mtrc2_output_schema_contract.csv`
- `mtrc2_stop_or_repair_decision.csv`
- `forbidden_scope_audit.csv`
- `production_boundary_audit.csv`
- `validator_report.json`
- `diagnostic_findings.md`
- `mtrc2_next_step_recommendation.md`

相关 MTR2_R / MTR3 / MTR5 / MTRC1D / MTRC1E 证据已检查：

- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc1d_research_only_broad_full_rank_signal_build/manifest.json`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc1d_research_only_broad_full_rank_signal_build/signals.csv`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc1d_research_only_broad_full_rank_signal_build/validator_report.json`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc1e_research_only_broad_signal_review_or_next_diagnostic_contract/mtrc2_gate_contract.csv`
- `data_tw/experiments/policy_mtr_mechanism_transfer/mtr2_r_broad_full_rank_visibility_repair/order_intent_artifact_index.csv`
- `data_tw/experiments/policy_mtr_mechanism_transfer/mtr2_r_broad_full_rank_visibility_repair/replay_artifact_index.csv`
- `data_tw/experiments/policy_mtr_mechanism_transfer/mtr2_r_broad_full_rank_visibility_repair/order_intents/M2_hold_rank_buffer_100/manifest.json`
- `data_tw/experiments/policy_mtr_mechanism_transfer/mtr2_r_broad_full_rank_visibility_repair/replays/M2_hold_rank_buffer_100/manifest.json`
- `data_tw/experiments/policy_mtr_mechanism_transfer/mtr2_r_broad_full_rank_visibility_repair/manifest.json`
- `data_tw/experiments/policy_mtr_mechanism_transfer/mtr3_robustness_window_regime_and_mechanism_attribution/manifest.json`
- `data_tw/experiments/policy_mtr_mechanism_transfer/mtr5_extended_oos_shadow_and_production_readiness_diagnostic/manifest.json`
- `data_tw/experiments/policy_mtr_mechanism_transfer/mtr5_extended_oos_shadow_and_production_readiness_diagnostic/extended_lineage_inventory.csv`
- `data_tw/experiments/policy_mtr_mechanism_transfer/mtr5_extended_oos_shadow_and_production_readiness_diagnostic/data_lineage_blocker.md`

## 4. 独立复核摘要

MTRC1D signal readiness 充分。独立读取 `signals.csv` 复算：

```text
signal_rows = 169366
top50_rows = 113000
non_top50_rows = 56366
date_range = 2017-01-10..2026-05-07
date_count = 2260
duplicate_date_instrument = 0
non_top50_buy_score_present = 0
non_top50_raw_score_present = 0
non_top50_score_rank_present = 0
non_top50_buy_eligible_not_false = 0
```

MTRC1D manifest / validator 进一步确认：

```text
artifact_type = policy_mtrc1d_research_only_broad_full_rank_signal_build
lineage_id = S2C_SPLIT_ALIGNED_FRESH_LTR
model_name = s2c_split_aligned_fresh_ltr_research_only_broad_full_rank_mtrc1d
verdict = PASS_READY_FOR_MTRC1E_RESEARCH_ONLY_BROAD_SIGNAL_REVIEW_OR_NEXT_DIAGNOSTIC_CONTRACT
S2C non-equivalent to MTR2_R/E3 = true
MTR5 blocker cleared by S2C = false
order_intent_generated = false
replay_result_generated = false
return_replay_performed = false
production/default/latest/provider/frontend/API/Agent/daily modified = false
```

MTRC2 inventory 独立复核结果：

```text
legal_same_signal_inputs = 0
M2_hold_rank_buffer_100 order_intent: same_candidate=true, same_parameter=true, same_signal=false, usable=false
M2_hold_rank_buffer_100 replay_result: same_candidate=true, same_parameter=true, same_signal=false, usable=false
M2_hold_rank_buffer_100 ledger: same_candidate=true, same_parameter=true, same_signal=false, usable=false
```

旧 MTR2_R `M2_hold_rank_buffer_100` order/replay manifest 的 `signal_artifact` 均指向：

```text
data_tw/artifacts/signals/e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025_broad_full_rank_mtr2_r/r1_broad_full_rank_visibility_repair_20260628/manifest.json
```

该 lineage 不是 MTRC1D 的：

```text
data_tw/experiments/policy_mtr_research_only_continuation/mtrc1d_research_only_broad_full_rank_signal_build/manifest.json
```

因此旧 MTR2_R 的 `M2_hold_rank_buffer_100` 必须维持 `same_signal=false`、`usable_for_mtrc2_diagnostic=false`。MTR3 manifest 也显示其为 MTR2_R 同窗口后验 robustness/attribution；MTR5 manifest / blocker 显示 `clean_extended_lineage_found=false`，不能替代 S2C/MTRC1D same-signal input。

## 5. Forbidden Actions Audit

未发现 MTRC2 越权动作：

- 未训练模型、未调参、未 inference、未重新计算 LTR score。
- 未生成或修改 `ModelSignalArtifact`。
- 未生成 `OrderIntentArtifact`。
- 未生成 `ReplayResultArtifact`。
- 未生成 ledger。
- 未运行收益 replay。
- 未选择 replay artifact 给 MTRC2 diagnostic 使用。
- 未实现 symbol/event/monthly/rolling/risk-off/drawdown/turnover diagnostic 计算。
- 未新增候选，未修改 `M2_hold_rank_buffer_100` 或 `rank_buffer=100`。
- 未把旧 MTR2_R/E3 replay 标为 S2C/MTRC1D 等价。
- 未解除 MTR5 `clean_extended_lineage_found=false` blocker。
- 未写 production/default/latest/provider/frontend/API/Agent/daily/config registry。
- 未 provider refresh / publish，未 accepted latest switch。
- 未 broker、quick-trade、real order。
- 未输出 target_weight、target_position 或 quantity instruction。

脚本写入路径审查：

```text
OUT_DIR = data_tw/experiments/policy_mtr_research_only_continuation/mtrc2_extended_concentration_window_diagnostic_contract_or_input_feasibility/
REPORT_PATH = docs/tw_portfolio_decision_model/POLICY_MTRC2_EXTENDED_CONCENTRATION_WINDOW_DIAGNOSTIC_CONTRACT_OR_INPUT_FEASIBILITY_EXECUTION_REPORT_CN.md
```

未发现脚本写入 registry、configs、provider、latest、frontend、API、Agent、daily 或 production 目录。

## 6. PASS 合理性

`PASS_READY_FOR_MTRC2_R_SAME_SIGNAL_ORDER_REPLAY_INPUT_BUILD_CONTRACT` 合理，理由是：

- MTRC1D broad signal 本身 readiness 通过，可作为后续 diagnostic signal input。
- 当前没有合法 same-candidate / same-parameter / same-signal 的 OrderIntent、ReplayResult 或 ledger。
- Work doc 明确规定：若只有 MTRC1D broad signal 而没有同 signal order/replay/ledger，推荐 verdict 可以是 `PASS_READY_FOR_MTRC2_R_SAME_SIGNAL_ORDER_REPLAY_INPUT_BUILD_CONTRACT` 或 `STOP_NO_LEGAL_SAME_SIGNAL_DIAGNOSTIC_INPUT`。
- 当前存在明确、狭窄、只读的下一步：先写 MTRC2_R same-signal order/replay input build contract，而不是直接运行 replay 或 diagnostic。

不应改为 `PASS_READY_FOR_MTRC3_EXTENDED_CONCENTRATION_WINDOW_DIAGNOSTIC_IF_LEGAL_INPUT_EXISTS`，因为 `legal_same_signal_inputs=0`。也不必 STOP，因为 MTRC1D signal 已 ready，且下一步合同化 repair/build 路线明确。

## 7. 下一步文档控制

下一步只能开：

```text
MTRC2_R_SAME_SIGNAL_ORDER_REPLAY_INPUT_BUILD_CONTRACT
```

MTRC2_R 边界：

- 只能先写合同，不得直接跑收益 replay。
- 合同必须声明如何基于 MTRC1D broad signal、`M2_hold_rank_buffer_100`、`rank_buffer=100` 构建或定位 readonly OrderIntent / ReplayResult / ledger input。
- 必须保留 `S2C_SPLIT_ALIGNED_FRESH_LTR` same-signal gate。
- 必须保留 non-top50 buy hard fail。
- 必须明确旧 MTR2_R/E3 只能作为 non-equivalence / feasibility 参考，不得作为 S2C/MTRC1D diagnostic input。
- 必须继续禁止 production/default/latest/provider/frontend/API/Agent/daily/config registry 写入。
- 必须继续禁止 broker、quick-trade、real order、target_weight、target_position、quantity instruction。
- 必须继续禁止 production readiness、收益承诺、默认策略切换。

不得自动进入：

```text
MTRC3_EXTENDED_CONCENTRATION_WINDOW_DIAGNOSTIC
MTR6 production readiness proposal
provider publish
accepted latest switch
frontend/API/Agent/daily 接入
broker / quick-trade / order
```
