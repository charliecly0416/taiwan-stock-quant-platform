---
created_at: 2026-06-28
status: review
phase: MTRC1E_RESEARCH_ONLY_BROAD_SIGNAL_REVIEW_OR_NEXT_DIAGNOSTIC_CONTRACT
reviewer: MTRC1E
readonly_only: true
simulation_only: true
production_allowed: false
accepted_verdict: PASS_READY_FOR_MTRC2_EXTENDED_CONCENTRATION_WINDOW_DIAGNOSTIC_CONTRACT_OR_INPUT_FEASIBILITY
next_phase_recommendation: MTRC2_EXTENDED_CONCENTRATION_WINDOW_DIAGNOSTIC_CONTRACT_OR_INPUT_FEASIBILITY
---

# POLICY_MTRC1E_RESEARCH_ONLY_BROAD_SIGNAL_REVIEW_OR_NEXT_DIAGNOSTIC_CONTRACT_REVIEW_CN

生成日期：2026-06-28

## 1. Verdict

```text
PASS_READY_FOR_MTRC2_EXTENDED_CONCENTRATION_WINDOW_DIAGNOSTIC_CONTRACT_OR_INPUT_FEASIBILITY
```

审查接受 MTRC1E 执行结果。当前证据足以确认：MTRC1E 只做了 MTRC1D broad `ModelSignalArtifact` readiness recheck，并冻结了 MTRC2 extended concentration/window diagnostic 的 input/output/gate/forbidden-actions contract。

本 PASS 只放行进入另行授权的 `MTRC2_EXTENDED_CONCENTRATION_WINDOW_DIAGNOSTIC_CONTRACT_OR_INPUT_FEASIBILITY`。不得自动实现 MTRC2，不得生成 OrderIntent、ReplayResult，不得运行收益 replay，不得选择 replay artifact，不得写 production/default/latest/provider/frontend/API/Agent/daily/config registry，不得把 diagnostic 结果写成 production readiness 或收益承诺。

S2C 仍是新的 research lineage，不等价于 MTR2_R/E3；MTRC1E 不解除 MTR5 的 `clean_extended_lineage_found=false` blocker。

## 2. Findings

### Critical

无。

### High

无。

### Medium

无。

### Low

1. 仓库当前存在大量既有 dirty/untracked 文件，审查未将其归因于 MTRC1E，也未回退任何他人修改。本次审查只新增本 review 文档。
2. MTRC1E 产物中的 `validator_report.json` 保留了未被本次实际使用的 `PASS_WITH_CONDITIONS_READY_FOR_MTRC1E_R_NARROW_REPAIR` allowed verdict 字符串。实际 verdict 为 PASS，且 hard gates 全部通过；该项不构成 blocker，但后续若要严格收敛 verdict vocabulary，可在单独文档维护中清理。

## 3. Evidence Checked

必读文档已读取并核对：

- `docs/tw_portfolio_decision_model/POLICY_MTRC1E_RESEARCH_ONLY_BROAD_SIGNAL_REVIEW_OR_NEXT_DIAGNOSTIC_CONTRACT_WORK_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_MTRC1E_RESEARCH_ONLY_BROAD_SIGNAL_REVIEW_OR_NEXT_DIAGNOSTIC_CONTRACT_EXECUTION_REPORT_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_MTRC1D_RESEARCH_ONLY_BROAD_FULL_RANK_SIGNAL_BUILD_REVIEW_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_MTRC_RESEARCH_ONLY_CONTINUATION_MAINLINE_CN.md`
- `docs/tw_modular_contracts/MODEL_SIGNAL_CONTRACT_CN.md`
- `docs/tw_modular_contracts/MODEL_SIGNAL_EXTENSION_SCHEMA_CN.md`

脚本已读取并核对：

- `scripts/build_tw_policy_mtrc1e_research_only_broad_signal_review_contract.py`

MTRC1E 输出目录下全部产物已检查：

- `manifest.json`
- `broad_signal_readiness_audit.csv`
- `top50_equivalence_recheck.csv`
- `non_top50_boundary_recheck.csv`
- `negative_sample_coverage_audit.csv`
- `extension_schema_recheck.csv`
- `downstream_diagnostic_input_contract.csv`
- `downstream_diagnostic_output_contract.csv`
- `mtrc2_gate_contract.csv`
- `mtrc2_forbidden_actions_contract.csv`
- `forbidden_scope_audit.csv`
- `production_boundary_audit.csv`
- `validator_report.json`
- `diagnostic_findings.md`
- `mtrc2_work_recommendation.md`

为独立复核，另读取并复算：

- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc1d_research_only_broad_full_rank_signal_build/signals.csv`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc1b_research_only_extended_top50_ltr_signal_build/signals.csv`
- `data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2b_fresh_qlib_training/phase_s2b_post_filter_score_rank.csv`

## 4. 独立复核摘要

独立读取 MTRC1D broad `signals.csv`、MTRC1B top50 `signals.csv` 与 S2B full-rank qlib rank 后复算：

```text
signal_rows = 169366
date_range = 2017-01-10..2026-05-07
date_count = 2260
duplicate date,instrument = 0
top50_rows = 113000
non_top50_rows = 56366
top50 outer join not both vs MTRC1B = 0
top50 buy_score mismatch vs MTRC1B = 0
top50 raw_score mismatch vs MTRC1B = 0
top50 score_rank mismatch vs MTRC1B = 0
top50 candidate_rank mismatch vs MTRC1B/S2B = 0
top50 full_qlib_rank mismatch vs MTRC1B/S2B = 0
non_top50 S2B rank>50 outer join not both = 0
non_top50 buy_score/raw_score/score_rank present = 0
non_top50 buy_eligible not false = 0
non_top50 visibility_role bad = 0
```

结论：MTRC1D recheck 覆盖了 top50 等价、non-top50 visibility-only、negative samples、extension schema 与 S2C non-equivalence。`validator_report.json` 中所有 hard checks 为 true，`blocking_reasons=[]`。

## 5. MTRC2 Contract Review

MTRC2 input contract 足够严格：

- 标准输入限定为 MTRC1D broad `ModelSignalArtifact`。
- same-candidate/same-parameter lineage evidence 为 required。
- 若需要 OrderIntent/ReplayResult/ledger，必须由 MTRC2 work doc 另行声明来源与校验。
- MTRC1E 不替 MTRC2 选择 replay artifact。
- 若不存在合法 same-candidate same-parameter same-signal lineage，MTRC2 必须 STOP 或另开 repair。

MTRC2 gate 覆盖最低要求：

- `same_candidate_m2_hold_rank_buffer_100`
- `same_parameter_rank_buffer_100`
- `same_signal_artifact_mtrc1d_broad`
- `non_top50_buy_validator_pass`
- `order_intent_input_contract_declared_if_needed`
- `replay_result_input_contract_declared_if_needed`
- `no_strategy_tuning`
- `no_new_candidate`
- `no_replay_return_conclusion_without_predeclared_replay_contract`
- `no_production_or_default_write`

MTRC2 output contract 仅允许 concentration、symbol/event attribution、monthly/rolling/risk-off/drawdown diagnostic tables，并要求 `diagnostic_only=true`、source/window/asof/input lineage。合同明确禁止 production readiness、target weights、order sizes、buy/sell instruction、broker action、target_position、target_weight、quantity。

## 6. Forbidden Actions Audit

审查未发现 MTRC1E forbidden actions：

- 未生成或修改 broad `signals.csv`；MTRC1E 输出目录没有 `signals.csv`。
- 未生成 OrderIntentArtifact、ReplayResultArtifact。
- 未运行收益 replay，未输出 return/pnl/replay result 产物。
- 未实现 MTRC2；只生成 MTRC2 diagnostic contract/recommendation。
- 未训练、调参、inference 或重新计算 LTR score。
- 未新增候选，未修改 `M2_hold_rank_buffer_100`。
- 未选择 replay artifact；合同要求 MTRC2 另行声明或 STOP。
- 未写 production/default/latest/provider/frontend/API/Agent/daily/config registry。
- 未 provider refresh/publish，未 accepted latest switch。
- 未 broker、quick-trade、real order。
- 未输出 target_weight、target_position 或 quantity instruction。
- 未将 S2C 描述为 MTR2_R/E3 等价，未解除 MTR5 blocker。

脚本写入路径集中于：

```text
data_tw/experiments/policy_mtr_research_only_continuation/mtrc1e_research_only_broad_signal_review_or_next_diagnostic_contract/
docs/tw_portfolio_decision_model/POLICY_MTRC1E_RESEARCH_ONLY_BROAD_SIGNAL_REVIEW_OR_NEXT_DIAGNOSTIC_CONTRACT_EXECUTION_REPORT_CN.md
```

`forbidden_scope_audit.csv` 与 `production_boundary_audit.csv` 均为 pass。产物目录只包含 work doc 允许的 15 个 MTRC1E 文件。

## 7. 下一步文档控制

下一步只能开：

```text
MTRC2_EXTENDED_CONCENTRATION_WINDOW_DIAGNOSTIC_CONTRACT_OR_INPUT_FEASIBILITY
```

MTRC2 下一步边界：

- 只能做 extended concentration/window diagnostic contract 或 input feasibility。
- 必须先验证 same candidate、same `M2_hold_rank_buffer_100` parameter、same MTRC1D broad signal artifact、same non-top50 buy hard-fail。
- 如需 OrderIntent、ReplayResult 或 ledger，只能读取 MTRC2 work doc 另行声明且已合同化校验的既有 research-only 输入。
- 不得自动跑收益 replay，不得生成 OrderIntent/ReplayResult，不得生成新的 replay lineage。
- 不得把 diagnostic 结果当 production readiness、收益承诺或默认策略切换依据。
- 不得替 MTRC2 选择 replay artifact；若合法 lineage 不存在，必须 STOP 或另开授权 repair。
- 不得修改 production/default/latest/provider/frontend/API/Agent/daily/config registry。

不得自动进入 MTRC2 implementation、return replay、production readiness proposal、provider publish、accepted latest switch、frontend/API/Agent/daily 接入、broker、quick-trade、order、target_weight、target_position 或 quantity instruction。
