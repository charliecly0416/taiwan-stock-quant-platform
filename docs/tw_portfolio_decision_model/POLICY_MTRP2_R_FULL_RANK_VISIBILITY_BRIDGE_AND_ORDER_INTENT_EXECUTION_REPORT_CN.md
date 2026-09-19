---
created_at: 2026-06-28T18:13:47+00:00
phase: MTRP2_R_FULL_RANK_VISIBILITY_BRIDGE_AND_ORDER_INTENT
strategy_rule: top50_hold_rank_buffer_100
readonly_only: true
simulation_only: true
production_candidate: true
production_allowed: false
not_default_candidate: true
not_published_latest: true
verdict: PASS_FULL_RANK_VISIBILITY_BRIDGE_AND_ORDER_INTENT_READY_FOR_P3_REPLAY
---

# POLICY_MTRP2_R_FULL_RANK_VISIBILITY_BRIDGE_AND_ORDER_INTENT_EXECUTION_REPORT_CN

## 1. Verdict

```text
PASS_FULL_RANK_VISIBILITY_BRIDGE_AND_ORDER_INTENT_READY_FOR_P3_REPLAY
```

Can enter P3 same-window readonly replay: `true`

## 2. Bridge Artifact

- path: `data_tw/artifacts/signals/top50_hold_rank_buffer_100_full_rank_visibility_bridge/mtrp2_r_20260628T181347Z`
- manifest: `data_tw/artifacts/signals/top50_hold_rank_buffer_100_full_rank_visibility_bridge/mtrp2_r_20260628T181347Z/manifest.json`
- source_lineage: `existing_audited_broad_reference_repackaged_for_production_candidate_readiness`
- source: `data_tw/artifacts/signals/e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025_broad_full_rank_mtr2_r/r1_broad_full_rank_visibility_repair_20260628/manifest.json`
- row_count: `11837`
- date_range: `2026-01-02..2026-05-07`
- daily_min_row_count: `149`
- top50_row_count: `3950`
- non_top50_row_count: `7887`

Bridge 是 readonly production-candidate readiness 产物，不声明 production-ready，不发布 latest，不改默认链路。non-top50 行只保留 `full_qlib_rank` 可见性，`buy_score/raw_score/score_rank` 置空且 `ext_buy_ranking_allowed=false`。

## 3. OrderIntent Artifact

- path: `data_tw/artifacts/strategies/top50_hold_rank_buffer_100/mtrp2_r_20260628T181347Z`
- manifest: `data_tw/artifacts/strategies/top50_hold_rank_buffer_100/mtrp2_r_20260628T181347Z/manifest.json`
- order_intent_count: `76`
- buy_intent_count: `43`
- sell_intent_count: `33`
- max_holding_count: `10`
- date_range: `2026-01-02..2026-05-07`

规则固定：`max_sell_count=1`、`max_buy_count=1`、`target_holding_count=10`、`candidate_k=50`、`hold_rank_buffer=100`。卖出只针对当前持仓中 `full_qlib_rank > 100` 的最差标的；买入只允许 top50，排序为 `buy_score desc + full_qlib_rank asc + instrument asc`。

## 4. Boundary Statement

本阶段没有训练、推理或重算 LTR；没有读取 replay return、future label、future price 或 broker/order 数据作为输入；没有修改 production default、frontend/API/Agent/daily/latest/provider/PriceStore；没有输出 broker/order/quantity/target_weight/target_position。

## 5. P3 Readiness

```text
can_enter_p3 = true
```
