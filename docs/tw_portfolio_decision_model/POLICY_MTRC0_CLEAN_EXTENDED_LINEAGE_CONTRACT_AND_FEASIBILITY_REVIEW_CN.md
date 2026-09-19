# POLICY_MTRC0_CLEAN_EXTENDED_LINEAGE_CONTRACT_AND_FEASIBILITY_REVIEW_CN

生成日期：2026-06-28

## 1. Verdict

```text
STOP_NO_CLEAN_LINEAGE_PATH
```

审查接受执行者 MTRC0 verdict。现有证据不足以进入 `MTRC1_EXTENDED_BROAD_FULL_RANK_LINEAGE_BUILD_AND_READONLY_REPLAY`：可验证的 MTR2_R broad full-rank 语义只覆盖 `2026-01-02` 至 `2026-05-07`，标准 top50 LTR ModelSignalArtifact 也只覆盖同一短窗口；虽然 qlib full-rank source 覆盖 `2023-01-03` 至 `2026-05-07`，但它不是 top50 LTR buy_score 语义，不能单独替代 MTR2_R 的 qlib+LTR clean lineage。

未发现执行者漏判可桥接的 clean extended lineage。MTRC0 盘点的 `224` 个 manifest 中，`eligible_for_mtrc1=0`；`extended_oos_qlib_orthogonal_ltr` 下未发现 `M2_hold_rank_buffer_100`、`hold_rank_buffer_100`、`broad_full_rank`、`MTR2_R` 或等价的 top50 LTR equivalence / non-top50 hold-sell-only 证据。

## 2. 审查范围

已读取：

- `POLICY_MTRC0_CLEAN_EXTENDED_LINEAGE_CONTRACT_AND_FEASIBILITY_WORK_CN.md`
- `POLICY_MTRC0_CLEAN_EXTENDED_LINEAGE_CONTRACT_AND_FEASIBILITY_EXECUTION_REPORT_CN.md`
- `POLICY_MTRC_RESEARCH_ONLY_CONTINUATION_MAINLINE_CN.md`
- `POLICY_MTR5_EXTENDED_OOS_SHADOW_AND_PRODUCTION_READINESS_DIAGNOSTIC_REVIEW_CN.md`
- MTRC0 输出目录全部 11 个 artifacts
- MTR5 `manifest.json`、`extended_lineage_inventory.csv`、`data_lineage_blocker.md`
- MTR2_R manifest、MTR2_R broad signal manifest
- 标准 top50 LTR signal manifest 与 qlib full-rank source manifest
- `extended_oos_qlib_orthogonal_ltr/**/manifest.json` 关键语义抽查

## 3. Clean Lineage 合同复核

MTRC0 的 `clean_lineage_definition_contract.csv` 正确固化 11 条 hard requirements：

- same candidate: `M2_hold_rank_buffer_100`
- same M2 parameter: `hold_rank_buffer_100` 与 max buy/sell 语义不变
- same baseline: `baseline_top50_exit_one_worst_sell`
- same signal semantics: qlib `candidate_rank/full_qlib_rank` + top50 LTR `buy_score`
- same broad full-rank visibility: non-top50 rows 仅用于 hold/sell visibility
- top50 LTR equivalence: top50 `buy_score` 必须匹配 source top50 LTR artifact
- non-top50 buy hard fail: buy 的 `candidate_rank` 缺失、非数值、>50 均 hard fail
- same OrderIntent / Replay contracts
- PIT safe: `signal_asof` / `available_at` 不得未来泄漏
- research-only: 不改 production/default/latest/provider/frontend/API/Agent/daily

该定义符合 MTRC mainline 与 MTR5 blocker 的要求。

## 4. Source Inventory 与 Bridge Matrix 复核

MTRC0 source inventory 足以支撑 STOP：

- 标准 top50 LTR artifact：`data_tw/artifacts/signals/e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025/r1_legacy_signal_adapter_20260616/manifest.json`，窗口仅 `2026-01-02..2026-05-07`，无 broad full-rank visibility。
- MTR2_R broad signal：`data_tw/artifacts/signals/e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025_broad_full_rank_mtr2_r/r1_broad_full_rank_visibility_repair_20260628/manifest.json`，具备 broad/top50/non-top50 语义，但同样只覆盖 `2026-01-02..2026-05-07`。
- qlib full-rank source：`data_tw/artifacts/signals/frozen_qlib_2018_2022/r1_legacy_signal_adapter_20260616/manifest.json`，窗口较长，但 `model_family=qlib` 且不支持 LTR rerank，不能证明 top50 LTR buy_score equivalence。
- existing extended_oos / shadow / replay artifacts 多数是 downstream replay/order_intent 或非同源 shadow，未证明 same M2 parameter、MTR2_R broad semantics、same contracts 与 top50 LTR equivalence。

`candidate_bridge_feasibility_matrix.csv` 的分类合理：

- `reuse_existing_mtr2_r_broad_signal` 标记为 `not_equivalent_do_not_use`，原因是 same-window only。
- `build_extended_broad_from_standard_top50_ltr_plus_qlib_full_rank` 标记为 `possible_but_requires_missing_input`，决定性缺口是 extended standard top50 LTR artifact 与 equivalence audit。
- `reuse_existing_extended_oos_order_intent_or_replay_artifacts` 标记为 `not_equivalent_do_not_use`。
- overall verdict 标记为 `stop_no_clean_path`。

## 5. 安全边界复核

未发现 MTRC0 越界证据。MTRC0 manifest、validator、forbidden_scope_audit、执行报告一致声明：

- 未跑收益 replay；
- 未生成 OrderIntent / ReplayResult；
- 未训练、未调参、未新增候选；
- 未修改 M2 参数；
- 未修改 MTR2_R/MTR3/MTR4/MTR5 输入产物；
- 未修改 production/default/latest/provider/frontend/API/Agent/daily；
- 未 provider publish、accepted latest switch、broker/quick-trade/real order；
- 未输出 target_weight、target_position、quantity instruction。

本审查过程中工作树已有大量 dirty/untracked 文件，不能归因给 MTRC0；本审查只新增本报告。

## 6. Research-only Closure

MTRC0 应作为 research-only closure 接受：

1. 当前不得启动 MTRC1 extended build/replay。
2. `M2_hold_rank_buffer_100` 仍只能保留在 research-only / diagnostic-only 状态。
3. MTR5 的 `clean_extended_lineage_found=false` blocker 未被解除。
4. 不得用 existing extended_oos/shadow/replay 产物拼接替代 clean extended lineage。
5. 不得进入 MTR6 production readiness proposal，也不得修改 production/default/latest/provider/frontend/API/Agent/daily。

## 7. Possible Future Unblocker

未来若要重新打开 MTRC1，至少需要先提供：

1. 覆盖 extended window 的标准 top50 LTR ModelSignalArtifact。
2. 与 qlib full-rank source 按每个 `signal_asof` 对齐的 PIT audit。
3. MTR2_R-compatible bridge：top50 `buy_score` 完全等价，non-top50 rows 仅用于 hold/sell visibility。
4. non-top50 buy hard-fail validator、top50 equivalence audit、forbidden field audit、research-only boundary audit。
5. 全部输出隔离在 research-only continuation 目录，不触碰 latest/default/provider/frontend/API/Agent/daily/broker 路径。

最终结论：

```text
STOP_NO_CLEAN_LINEAGE_PATH
```
