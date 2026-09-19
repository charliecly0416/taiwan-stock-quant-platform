# POLICY_MTRC2_S_SAME_SIGNAL_ORDER_INTENT_BUILD_REVIEW_CN

生成日期：2026-06-28

## 1. Verdict

```text
PASS_READY_FOR_MTRC2_T_SAME_SIGNAL_REPLAY_INPUT_BUILD_CONTRACT
```

审查接受 MTRC2_S 产物。`scripts/build_tw_policy_mtrc2_s_same_signal_order_intent.py` 只生成 readonly、simulation-only、diagnostic-only 的 same-signal `OrderIntentArtifact`，未发现 ReplayResult、ledger、price store selection、收益/回撤/集中度/window 诊断、production readiness、provider/latest/default/frontend/API/Agent/daily、broker/order 或 target/quantity 输出。

本 PASS 只放行到另行授权的 `MTRC2_T_SAME_SIGNAL_REPLAY_INPUT_BUILD_CONTRACT`。不得直接进入 replay、MTRC3 diagnostic 或 production readiness。

## 2. Findings

### Critical

无。

### High

无。

### Medium

无。

### Low

1. `order_intents.csv` 包含可选审计列 `source_artifact`。该列来自 MTRC1D `signals.csv` 的标准 `ModelSignalArtifact` core field，builder 只逐行透传用于 lineage audit；未读取该字段指向的文件，未读取 `source_model_artifact` / `source_feature_artifact`，也未打开私有模型文件。因此不构成私有模型读取边界违规。
2. 仓库已有大量 dirty/untracked 文件，本审查未归因、未回退、未修改。本次只新增本 review 文档。

## 3. Evidence Checked

必读文档已读取并核对：

- `docs/tw_portfolio_decision_model/POLICY_MTRC2_S_SAME_SIGNAL_ORDER_INTENT_BUILD_WORK_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_MTRC2_S_SAME_SIGNAL_ORDER_INTENT_BUILD_EXECUTION_REPORT_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_MTRC_RESEARCH_ONLY_CONTINUATION_MAINLINE_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_MTRC2_R_SAME_SIGNAL_ORDER_REPLAY_INPUT_BUILD_CONTRACT_REVIEW_CN.md`
- `docs/tw_modular_contracts/STRATEGY_RULE_CONTRACT_CN.md`
- `docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md`
- `docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md`
- `docs/tw_modular_contracts/NEW_STRATEGY_REVIEWER_CHECKLIST_CN.md`
- `docs/tw_modular_contracts/TW_NEW_STRATEGY_ONBOARDING_TEMPLATE_CN.md`
- `configs/strategy_dependencies/mechanism_transfer_top50_cost_aware_v1.yaml`

脚本已读取并核对：

- `scripts/build_tw_policy_mtrc2_s_same_signal_order_intent.py`

MTRC2_S 输出目录全部 12 个产物已检查：

- `manifest.json`
- `order_intents.csv`
- `schema.json`
- `strategy_decision_audit.csv`
- `non_top50_buy_validator_report.json`
- `candidate_parameter_audit.csv`
- `signal_lineage_audit.csv`
- `forbidden_field_audit.csv`
- `forbidden_action_audit.json`
- `old_mtr2r_reuse_audit.csv`
- `validator_report.json`
- `diagnostic_findings.md`

独立抽查输入证据：

- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc1d_research_only_broad_full_rank_signal_build/manifest.json`
- `data_tw/experiments/policy_mtr_research_only_continuation/mtrc1d_research_only_broad_full_rank_signal_build/signals.csv`
- `data_tw/experiments/policy_mtr_mechanism_transfer/mtr2_r_broad_full_rank_visibility_repair/order_intents/M2_hold_rank_buffer_100/manifest.json`

## 4. Independent Recompute/Audit 摘要

输出路径复核：

```text
OUT_DIR = data_tw/experiments/policy_mtr_research_only_continuation/mtrc2_s_same_signal_order_intent_build
REPORT_PATH = docs/tw_portfolio_decision_model/POLICY_MTRC2_S_SAME_SIGNAL_ORDER_INTENT_BUILD_EXECUTION_REPORT_CN.md
```

builder 的 `write_csv` / `write_json` / `write_text` 写入均限定在上述 `OUT_DIR` 和 `REPORT_PATH`。未发现写入 MTRC1D/MTRC2_R、registry、configs、provider、latest、frontend、API、Agent、daily 或 production 目录的代码路径。

`order_intents.csv` 独立复算结果：

```text
row_count = 2378
buy_intent_count = 1194
sell_intent_count = 1184
allowed_actions = buy, sell, hold, skip
missing_required_fields = 0
forbidden_order_columns = 0
bad_signal_artifact_rows = 0
non_top50_buy_intent_count = 0
max_daily_buy_count = 1
max_daily_sell_count = 1
buy_rank_missing_for_buy = 0
```

冻结参数复核通过：

```text
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

signal lineage 复核通过：

```text
signal_artifact = data_tw/experiments/policy_mtr_research_only_continuation/mtrc1d_research_only_broad_full_rank_signal_build/manifest.json
MTRC1D signal_rows = 169366
top50_rows = 113000
non_top50_rows = 56366
date_range = 2017-01-10..2026-05-07
date_count = 2260
```

`source_artifact` 专项复核：

```text
checked_intents = 2378
source_artifact_mismatch_vs_mtrc1d_signal_row = 0
order_intents_has_source_model_artifact_column = false
order_intents_has_source_feature_artifact_column = false
```

结论：`source_artifact` 是 MTRC1D 标准 signal 行的来源审计字段透传，不是 builder 对私有模型文件的读取或依赖。

旧 MTR2_R/E3 复用复核通过。旧 MTR2_R OrderIntent manifest 的 `signal_artifact` 是：

```text
data_tw/artifacts/signals/e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025_broad_full_rank_mtr2_r/r1_broad_full_rank_visibility_repair_20260628/manifest.json
```

该路径不等于 MTRC1D manifest。MTRC2_S `old_mtr2r_reuse_audit.csv` 标记旧 manifest `same_signal=false`、`reused_as_output=false`，且 MTRC2_S `manifest.json` 标记 `old_mtr2r_reused=false`。

## 5. Forbidden Actions Audit

`forbidden_action_audit.json` status 为 `pass`，所有禁止动作均 `performed=false`。独立静态检查未发现以下越权输出或动作：

- 未训练模型、未调参、未模型 inference、未重新计算 LTR score。
- 未生成或修改 ModelSignalArtifact。
- 未选择 price store。
- 未生成 ReplayResultArtifact、ledger、summary/actions/daily_nav/position snapshots。
- 未运行收益 replay，未计算收益、回撤、集中度、rolling window 或 risk-off 诊断。
- 未新增候选，未修改 `M2_hold_rank_buffer_100`、`rank_buffer=100` 或 strategy dependency YAML。
- 未写 production/default/latest/provider/frontend/API/Agent/daily。
- 未 provider refresh/publish，未 accepted latest switch。
- 未 monitor config/scan/alerts write。
- 未 broker、quick-trade、real order。
- 未输出 execution_price/date、quantity、target_position、target_weight、cash、NAV、fee、tax、PnL、broker/order 字段。
- 未输出 future_return/forward_return/future_excess_return、label、LTR relevance label 字段。
- 未宣称 production readiness，未解除 MTR5 `clean_extended_lineage_found=false` blocker。

`forbidden_field_audit.csv` 对 intent artifact、schema、decision audit、parameter audit、lineage audit、manifest keys 的 `present_count` 均为 0 且 `status=pass`。

## 6. Next Work Document

下一步只能开：

```text
MTRC2_T_SAME_SIGNAL_REPLAY_INPUT_BUILD_CONTRACT
```

MTRC2_T 边界必须保持：

- 只能消费 reviewed MTRC2_S same-signal OrderIntentArtifact。
- 必须验证 OrderIntent 的 `signal_artifact` 仍严格等于 MTRC1D broad signal manifest。
- 必须继续冻结 `candidate_id=M2_hold_rank_buffer_100`、`mechanism=hold_rank_buffer`、`rank_buffer=100`、`target_holding_count=10`、`candidate_k=50`、`max_buy_count/max_sell_count=1/1`。
- 只能做 replay input/build contract；不得在未另行授权前直接运行 replay。
- 不得进入 MTRC3 diagnostic 或 production readiness。
- 不得写 provider/latest/default/frontend/API/Agent/daily，不得 broker/quick-trade/real order。
