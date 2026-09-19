---
created_at: 2026-06-28
status: review
phase: MTRC2_R_SAME_SIGNAL_ORDER_REPLAY_INPUT_BUILD_CONTRACT
reviewer: MTRC2_R
readonly_only: true
simulation_only: true
production_allowed: false
accepted_verdict: PASS_READY_FOR_MTRC2_S_SAME_SIGNAL_ORDER_INTENT_BUILD
next_phase_recommendation: MTRC2_S_SAME_SIGNAL_ORDER_INTENT_BUILD
---

# POLICY_MTRC2_R_SAME_SIGNAL_ORDER_REPLAY_INPUT_BUILD_CONTRACT_REVIEW_CN

生成日期：2026-06-28

## 1. Verdict

```text
PASS_READY_FOR_MTRC2_S_SAME_SIGNAL_ORDER_INTENT_BUILD
```

审查接受 MTRC2_R 执行结果。MTRC2_R 产物是合同和 validator 边界，不是 OrderIntent / ReplayResult / ledger / ModelSignal 结果；未发现收益 replay、concentration/window diagnostic 计算、生产接入或旧 MTR2_R/E3 复用为 MTRC/S2C input。

本 PASS 只放行进入另行授权的 `MTRC2_S_SAME_SIGNAL_ORDER_INTENT_BUILD`。MTRC2_S 只能构建 readonly、simulation-only、diagnostic-only 的 same-signal `OrderIntentArtifact`，不得 replay、不得生成 ReplayResult 或 ledger、不得给收益结论、不得 production readiness、不得写 provider/latest/default/frontend/API/Agent/daily/registry。

## 2. Findings

### Critical

无。

### High

无。

### Medium

无。

### Low

1. `same_signal_replay_input_build_contract.csv` 已冻结 MTRC2_T 的执行配置字段，但没有选择实际 price store 产物；这符合 MTRC2_R work doc，因为 price store 只能由 MTRC2_T 在另行授权后声明并做 PIT/readiness 检查。
2. 仓库已有大量 dirty/untracked 文件，本审查未归因、未回退、未修改。此次只新增本 review 文档。

## 3. Evidence Checked

必读文档已读取并核对：

- `docs/tw_portfolio_decision_model/POLICY_MTRC2_R_SAME_SIGNAL_ORDER_REPLAY_INPUT_BUILD_CONTRACT_WORK_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_MTRC2_R_SAME_SIGNAL_ORDER_REPLAY_INPUT_BUILD_CONTRACT_EXECUTION_REPORT_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_MTRC2_EXTENDED_CONCENTRATION_WINDOW_DIAGNOSTIC_CONTRACT_OR_INPUT_FEASIBILITY_REVIEW_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_MTRC_RESEARCH_ONLY_CONTINUATION_MAINLINE_CN.md`
- `docs/tw_modular_contracts/STRATEGY_RULE_CONTRACT_CN.md`
- `docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md`
- `docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md`
- `.agents/skills/tw-stock-safety-boundary-review/SKILL.md`
- `.agents/skills/tw-stock-safety-boundary-review/references/forbidden-actions.md`

脚本已读取并核对：

- `scripts/build_tw_policy_mtrc2_r_same_signal_order_replay_input_build_contract.py`

MTRC2_R 输出目录全部产物已检查：

- `manifest.json`
- `same_signal_order_intent_build_contract.csv`
- `same_signal_replay_input_build_contract.csv`
- `same_signal_ledger_input_contract.csv`
- `strategy_dependency_contract.csv`
- `m2_100_parameter_freeze_contract.csv`
- `non_top50_buy_validator_contract.csv`
- `old_mtr2r_template_non_equivalence_audit.csv`
- `mtrc2_s_order_intent_build_work_recommendation.md`
- `mtrc2_t_replay_input_build_work_recommendation.md`
- `mtrc3_diagnostic_entry_gate_contract.csv`
- `forbidden_scope_audit.csv`
- `production_boundary_audit.csv`
- `validator_report.json`
- `diagnostic_findings.md`

独立抽查输入证据：

- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc1d_research_only_broad_full_rank_signal_build/signals.csv`
- `data_tw/experiments/policy_mtr_mechanism_transfer/mtr2_r_broad_full_rank_visibility_repair/order_intents/M2_hold_rank_buffer_100/manifest.json`
- `data_tw/experiments/policy_mtr_mechanism_transfer/mtr2_r_broad_full_rank_visibility_repair/replays/M2_hold_rank_buffer_100/manifest.json`

## 4. 独立复核摘要

MTRC2_R 产物目录只包含 work doc 允许的 15 个合同、审计和报告类文件，未出现 `order_intents.csv`、`summary.csv`、`actions.csv`、`daily_nav.csv`、ledger 结果、ModelSignal 或 diagnostic 计算输出。

脚本写入路径复核：

```text
OUT_DIR = data_tw/experiments/policy_mtr_research_only_continuation/mtrc2_r_same_signal_order_replay_input_build_contract
REPORT_PATH = docs/tw_portfolio_decision_model/POLICY_MTRC2_R_SAME_SIGNAL_ORDER_REPLAY_INPUT_BUILD_CONTRACT_EXECUTION_REPORT_CN.md
```

脚本实际 `write_csv` / `write_json` / `write_text` 写入均限定在上述 `OUT_DIR` 和 `REPORT_PATH`。未发现写 registry、configs default、provider/latest、frontend、API、Agent、daily 或 production 目录的代码路径。

MTRC1D broad signal 独立复算：

```text
rows = 169366
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

这与 MTRC2_R `manifest.json` 统计一致，支持 non-top50 rows 仅作 broad visibility / hold-sell 边界，不作买入排序。

OrderIntent build contract 复核通过：

```text
input_model_signal = data_tw/experiments/policy_mtr_research_only_continuation/mtrc1d_research_only_broad_full_rank_signal_build/manifest.json
strategy_rule = mechanism_transfer_top50_cost_aware_v1
candidate_id = M2_hold_rank_buffer_100
mechanism = hold_rank_buffer
rank_buffer = 100
target_holding_count = 10
candidate_k = 50
max_buy_count = 1
max_sell_count = 1
sell_boundary = qlib_top50_by_candidate_rank_and_full_qlib_rank
buy_order = buy_score_desc_only_within_top50
tie_breaker = full_qlib_rank_asc, instrument_asc
```

`m2_100_parameter_freeze_contract.csv` 进一步声明 candidate、mechanism、rank_buffer、strategy_rule、target_holding_count、candidate_k、max buy/sell 和 signal_lineage 在 MTRC2_S/MTRC2_T 中均不可改。

Non-top50 buy hard fail 复核通过：

```text
buy_candidate_rank_lte_50 = hard_fail
buy_score_present_only_for_top50_buy_candidates = hard_fail
non_top50_buy_intent_count_equals_0 = hard_fail
non_top50_rows_visibility_only = hard_fail
negative_sample_non_top50_buy_fails = hard_fail
```

Replay input contract 复核通过：

```text
decision_source = MTRC2_S same-signal OrderIntentArtifact
order_intent_artifact_equals_mtrc2_s_same_signal = hard gate
order_intent_signal_artifact_equals_mtrc1d_broad = hard gate
old_mtr2r_replay_not_reused = hard gate
price_store = declared historical PriceStore with PIT/readiness pass
```

该合同没有提前选择 replay artifact，也没有运行 replay；MTRC2_T 必须等 MTRC2_S 输出和审查通过后才能另行启动。

旧 MTR2_R/E3 non-equivalence 复核通过。旧 `M2_hold_rank_buffer_100` OrderIntent manifest 的 signal_artifact 为：

```text
data_tw/artifacts/signals/e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025_broad_full_rank_mtr2_r/r1_broad_full_rank_visibility_repair_20260628/manifest.json
```

该路径不是 MTRC1D broad signal manifest。旧 replay manifest 又消费旧 MTR2_R OrderIntent：

```text
data_tw/experiments/policy_mtr_mechanism_transfer/mtr2_r_broad_full_rank_visibility_repair/order_intents/M2_hold_rank_buffer_100/manifest.json
```

因此旧 order/replay 只能作为 same-candidate、same-parameter、same_signal=false 的 non-equivalent template reference，不可作为 MTRC/S2C input，也不能解除 MTR5 `clean_extended_lineage_found=false` blocker。

## 5. Forbidden Actions Audit

未发现 MTRC2_R 越权动作：

- 未生成 `OrderIntentArtifact`。
- 未生成 `ReplayResultArtifact`。
- 未生成 ledger。
- 未生成或修改 `ModelSignalArtifact`。
- 未运行收益 replay。
- 未实现 concentration/window diagnostic 计算。
- 未训练模型、未调参、未 inference、未重新计算 LTR score。
- 未新增候选，未修改 `M2_hold_rank_buffer_100` 或 `rank_buffer=100`。
- 未修改 `mechanism_transfer_top50_cost_aware_v1.yaml`、strategy dependency YAML、registry/default。
- 未写 production/default/latest/provider/frontend/API/Agent/daily。
- 未 provider refresh / publish，未 accepted latest switch。
- 未 monitor config / scan / alerts write。
- 未 broker、quick-trade、real order。
- 未输出 target_weight、target_position 或 quantity instruction。
- 未把 S2C 描述为 MTR2_R/E3 等价。
- 未解除 MTR5 `clean_extended_lineage_found=false` blocker。

关键字静态搜索中出现的 `OrderIntentArtifact`、`ReplayResultArtifact`、`ledger`、`replay`、`provider/latest/frontend/API/Agent/daily`、`broker`、`target_weight`、`target_position`、`quantity` 等命中均位于合同、禁止项、审计字段或 recommendation 的 hard stop 语境；未发现真实执行调用或边界外写入。

## 6. 下一步文档控制

下一步只能开：

```text
MTRC2_S_SAME_SIGNAL_ORDER_INTENT_BUILD
```

MTRC2_S 边界：

- 只能消费 MTRC1D broad signal manifest。
- 必须保持 `M2_hold_rank_buffer_100`、`mechanism=hold_rank_buffer`、`rank_buffer=100`、`mechanism_transfer_top50_cost_aware_v1`。
- 只能构建 readonly、simulation-only、diagnostic-only 的 `OrderIntentArtifact`。
- 必须执行 non-top50 buy hard fail，任何 buy intent 必须 `candidate_rank <= 50`，`non_top50_buy_intent_count` 必须为 0。
- 必须禁止成交价、成交日、现金、NAV、fee/tax、target_weight、target_position、quantity、broker/order 字段进入 OrderIntent。
- 必须禁止旧 MTR2_R/E3 OrderIntent 复用；旧产物最多作为模板形状参考并保留 non-equivalent 标记。

MTRC2_S 不得做：

```text
ReplayResult build
ledger build
收益 replay
concentration/window diagnostic
price store selection
production readiness
provider publish / refresh
accepted latest switch
frontend/API/Agent/daily 接入
broker / quick-trade / real order
target_weight / target_position / quantity instruction
```

MTRC2_T 只能在 MTRC2_S 输出和审查均 PASS 后另行授权。MTRC3 diagnostic 只能在 reviewed MTRC2_S same-signal OrderIntent、reviewed MTRC2_T same-signal ReplayResult，以及必要时从 MTRC2_T 派生的 ledger 均合法后再进入。
