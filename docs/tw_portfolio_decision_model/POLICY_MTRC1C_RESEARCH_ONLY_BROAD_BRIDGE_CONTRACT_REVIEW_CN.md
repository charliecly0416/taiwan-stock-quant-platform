---
created_at: 2026-06-28
status: review
phase: MTRC1C_RESEARCH_ONLY_BROAD_BRIDGE_CONTRACT
reviewer: MTRC1C
readonly_only: true
simulation_only: true
production_allowed: false
accepted_verdict: PASS_READY_FOR_MTRC1D_RESEARCH_ONLY_BROAD_FULL_RANK_SIGNAL_BUILD
next_phase_recommendation: MTRC1D_RESEARCH_ONLY_BROAD_FULL_RANK_SIGNAL_BUILD
---

# POLICY_MTRC1C_RESEARCH_ONLY_BROAD_BRIDGE_CONTRACT_REVIEW_CN

生成日期：2026-06-28

## 1. Verdict

```text
PASS_READY_FOR_MTRC1D_RESEARCH_ONLY_BROAD_FULL_RANK_SIGNAL_BUILD
```

审查接受 MTRC1C 执行结果。当前证据足以确认：MTRC1C 只完成了 broad full-rank visibility bridge 的合同、可行性检查和 validator 设计；未生成 broad `signals.csv`，未生成 OrderIntent、ReplayResult，未运行收益 replay，未改 production/default/latest/provider/frontend/API/Agent/daily/config registry。

本 PASS 只放行进入另行授权的 MTRC1D research-only broad full-rank ModelSignalArtifact build。它不授权 MTRC1D 进入 OrderIntent、ReplayResult、收益 replay、production readiness、默认策略/模型切换、provider/latest/frontend/API/Agent/daily 接入、broker、quick-trade、order、target_weight、target_position 或 quantity 指令。

S2C 仍是新的 research lineage，不等价于 MTR2_R/E3；MTRC1C 与后续 MTRC1D 都不能解除 MTR5 的 `clean_extended_lineage_found=false` blocker。

## 2. Findings

### Critical

无。

### High

无。

### Medium

无。

### Low

1. 仓库当前存在大量既有 dirty/untracked 文件，审查未将其归因于 MTRC1C，也未回退任何他人修改。本次报告只新增本 review 文档。
2. MTRC1C 的 `available_at <- date` 仍是 `S2C_LEGACY_RESEARCH_DAILY_VISIBLE` research-only policy，不构成生产 provider timing 证明。MTRC1D 只能继承该 research-only 限制，不能把它解释为生产级可见性证明。

## 3. Mainline Compliance

MTRC1C 符合 `POLICY_MTRC_RESEARCH_ONLY_CONTINUATION_MAINLINE_CN.md` 与 MTRC1C work doc 的边界：

- 只做合同、可行性和 validator 设计。
- 不训练、不调参、不 inference。
- 不生成 broad `signals.csv`。
- 不生成 OrderIntentArtifact 或 ReplayResultArtifact。
- 不跑收益 replay。
- 不新增策略候选，不修改 `M2_hold_rank_buffer_100`。
- 不改 production/default/latest/provider/frontend/API/Agent/daily/config registry。
- 保持 S2C research-only 且 non-equivalent to MTR2_R/E3。
- 不解除 MTR5 `clean_extended_lineage_found=false` blocker。

## 4. Evidence Checked

必读文档已读取并核对：

- `docs/tw_portfolio_decision_model/POLICY_MTRC1C_RESEARCH_ONLY_BROAD_BRIDGE_CONTRACT_WORK_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_MTRC1C_RESEARCH_ONLY_BROAD_BRIDGE_CONTRACT_EXECUTION_REPORT_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_MTRC1B_RESEARCH_ONLY_EXTENDED_TOP50_LTR_SIGNAL_BUILD_REVIEW_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_MTRC_RESEARCH_ONLY_CONTINUATION_MAINLINE_CN.md`
- `docs/tw_modular_contracts/MODEL_SIGNAL_CONTRACT_CN.md`
- `docs/tw_modular_contracts/MODEL_SIGNAL_EXTENSION_SCHEMA_CN.md`
- `docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md`
- `docs/tw_modular_contracts/NEW_MODEL_AND_STRATEGY_DEVELOPER_GUIDE_CN.md`
- `docs/tw_modular_contracts/NEW_MODEL_REVIEWER_CHECKLIST_CN.md`

脚本已读取并核对：

- `scripts/build_tw_policy_mtrc1c_research_only_broad_bridge_contract.py`

MTRC1C 输出目录下 15 个产物已全部读取或抽查内容：

- `manifest.json`
- `broad_bridge_contract.csv`
- `qlib_full_rank_source_contract.csv`
- `top50_equivalence_contract.csv`
- `non_top50_visibility_contract.csv`
- `non_top50_buy_hard_fail_contract.csv`
- `model_signal_extension_contract.csv`
- `candidate_input_inventory.csv`
- `feasibility_gate.csv`
- `forbidden_scope_audit.csv`
- `production_boundary_audit.csv`
- `validator_design.json`
- `validator_report.json`
- `diagnostic_findings.md`
- `mtrc1d_work_recommendation.md`

独立复算结果与执行报告一致：

```text
MTRC1B rows = 113000
MTRC1B date_count = 2260
MTRC1B date_range = 2017-01-10..2026-05-07
MTRC1B rows_per_date = 50..50
MTRC1B duplicate date,instrument = 0

S2B qlib source rows = 169366
S2B qlib date_count = 2260
S2B qlib date_range = 2017-01-10..2026-05-07
S2B qlib rows_per_date = 51..150
S2B duplicate date,instrument = 0
S2B non-top50 rows = 56366

MTRC1B top50 join missing = 0
candidate_rank vs S2B qlib_rank mismatch = 0
full_qlib_rank vs S2B qlib_rank mismatch = 0
score_rank mismatch = 0
buy_score/raw_score mismatch = 0
candidate_rank_gt50 in MTRC1B = 0
full_qlib_rank_gt50 in MTRC1B = 0
```

## 5. S2B Full-Rank Source Review

接受 `data_tw/experiments/ltr_qlib_split_aligned_retrain/phase_s2b_fresh_qlib_training/phase_s2b_post_filter_score_rank.csv` 作为 S2C broad bridge 的唯一 qlib full-rank source 候选。

理由：

- 覆盖 MTRC1B 全部日期范围：`2017-01-10..2026-05-07`。
- 与 MTRC1B top50 `date,instrument` join missing 为 0。
- MTRC1B top50 `candidate_rank` 与 S2B `qlib_rank` mismatch 为 0。
- MTRC1B top50 `full_qlib_rank` 与 S2B `qlib_rank` mismatch 为 0。
- S2B 存在 56366 行 `qlib_rank > 50`，足以作为后续 MTRC1D visibility-only broad rows 候选。

限制：

- S2B `qlib_score_raw` 只能作为 diagnostic audit 或 qlib base source trace，不得变成 non-top50 LTR buy priority。
- 该 source 不能证明 MTR2_R/E3 等价，不能解除 MTR5 blocker。

## 6. Top50 Equivalence Review

MTRC1C 的 top50 等价规则足够严格：

- MTRC1D broad output 必须包含每个 MTRC1B top50 `date,instrument`，且唯一。
- top50 `candidate_rank` 必须等于 MTRC1B `candidate_rank` 且等于 S2B `qlib_rank`。
- top50 `full_qlib_rank` 必须等于 MTRC1B `full_qlib_rank` 且等于 S2B `qlib_rank`。
- top50 `buy_score`、`raw_score`、`score_rank` 必须逐值复制 MTRC1B，不允许重新打分、重新 inference 或重排。
- validator design 已列出 `top50_rows_equal_mtrc1b_by_date_instrument`、`top50_buy_score_equal_mtrc1b`、`top50_raw_score_equal_mtrc1b`、`top50_score_rank_equal_mtrc1b` 等 hard gates。

## 7. Non-Top50 Boundary Review

non-top50 被严格限定为 visibility-only：

- `candidate_rank` 必须 `>50` 或后续 schema 明确标记为 non-candidate。
- `full_qlib_rank` 必须来自同一个 S2B `qlib_rank` source。
- 允许 consumer 仅限 hold/sell visibility、exit boundary、diagnostic。
- `ranking_allowed=false`，`buy_eligible=false`。
- 采用 option A：non-top50 `buy_score`、`raw_score`、`score_rank` 必须为空，并禁止 ranking consumer 读取。

buy hard-fail 设计足够明确：

- `candidate_rank > 50` 且存在 `buy_score/raw_score/score_rank` 或被标记 buy eligible 时必须 fail。
- strategy dependency 或 bridge consumer 将 non-top50 row 用于 buy ranking 时必须 fail。
- broad output 缺失 MTRC1B top50 key 时必须 fail。
- top50 LTR score 被改写时必须 fail。

## 8. Extension Schema Review

extension schema 合规。

MTRC1C 只提出两个 optional `ext_*` diagnostic fields：

- `ext_mtrc1c_visibility_role`
- `ext_mtrc1c_non_top50_buy_eligible`

二者均声明了 dtype、semantic_role、availability_policy、producer、allowed_consumers、ranking_allowed、required_for_core_replay、description；`ranking_allowed=false`，`required_for_core_replay=false`，且未使用 forbidden extension fields 或 legacy 私有字段名作为策略输入。

## 9. Forbidden Actions Audit

审查未发现 MTRC1C 执行了 forbidden actions。

产物目录没有 `signals.csv`，只有合同、audit、validator design/report、manifest、diagnostic 和 MTRC1D recommendation。`forbidden_scope_audit.csv` 与 `production_boundary_audit.csv` 均显示：

- `model_training=False`
- `model_inference=False`
- `broad_signals_csv_generated=False`
- `order_intent_generated=False`
- `replay_result_generated=False`
- `return_replay_run=False`
- `provider_publish_or_refresh=False`
- `accepted_latest_switch=False`
- `monitor_scan_config_alert_write=False`
- `broker_quick_trade_real_order=False`
- `target_weight_position_quantity_instruction=False`
- `production_default_latest_provider_modified=False`
- `frontend_api_agent_daily_modified=False`

builder 写路径集中在 MTRC1C 输出目录和 MTRC1C 执行报告；未发现 registry、configs、provider、latest、frontend、API、Agent、daily 或 production 目录写入逻辑。

## 10. Missing Evidence Or Open Questions

无阻断性缺证。

后续 MTRC1D 仍需在实际 broad artifact build 时补齐真实 artifact validator 输出和 negative samples。MTRC1C 当前只审查合同与可行性，不能替代 MTRC1D artifact-level review。

## 11. 下一步文档控制

建议下一步开：

```text
MTRC1D_RESEARCH_ONLY_BROAD_FULL_RANK_SIGNAL_BUILD
```

MTRC1D 工作边界：

- 只能构建 research-only broad full-rank `ModelSignalArtifact`。
- top50 equivalence source 必须是 MTRC1B `signals.csv`。
- qlib full-rank source 必须是 S2B `phase_s2b_post_filter_score_rank.csv`。
- top50 rows 必须完全继承 MTRC1B 的 `buy_score/raw_score/score_rank`。
- top50 `candidate_rank/full_qlib_rank` 必须与 S2B `qlib_rank` 等价。
- non-top50 rows 只能 visibility-only，`buy_score/raw_score/score_rank` 必须为空。
- 必须先实现并运行 non-top50 buy hard-fail validator 和 top50 equivalence validator。
- 必须生成 MTRC1D execution report，再由独立 reviewer 审查。

MTRC1D 禁止事项：

- 不得训练、调参、重新 inference。
- 不得新增候选或修改 `M2_hold_rank_buffer_100`。
- 不得生成 OrderIntent、ReplayResult 或运行收益 replay。
- 不得接入 production/default/latest/provider/frontend/API/Agent/daily/config registry。
- 不得 provider publish、accepted latest switch、monitor write。
- 不得 broker、quick-trade、real order。
- 不得输出 target_weight、target_position 或 quantity instruction。
- 不得声称 S2C 等价于 MTR2_R/E3。
- 不得解除 MTR5 `clean_extended_lineage_found=false` blocker。

## 12. Command For Next Executor

```text
请执行 MTRC1D_RESEARCH_ONLY_BROAD_FULL_RANK_SIGNAL_BUILD。
只构建 research-only broad full-rank ModelSignalArtifact；top50 必须与 MTRC1B 等价，non-top50 必须 visibility-only 且 buy hard-fail。
不得生成 OrderIntent、ReplayResult、收益 replay，不得修改 production/default/latest/provider/frontend/API/Agent/daily/config registry。
完成后写 MTRC1D execution report，等待独立审查。
```
