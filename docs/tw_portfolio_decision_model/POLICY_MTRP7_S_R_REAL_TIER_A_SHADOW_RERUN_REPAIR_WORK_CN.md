---
created_at: 2026-06-28
status: work_doc
phase: MTRP7_S_R_REAL_TIER_A_SHADOW_RERUN_REPAIR
parent_phase: MTRP7_S_CLEAN_DAILY_MODELB_LTR_TOP50_ACCUMULATION_BUILD
strategy_candidate: top50_hold_rank_buffer_100
readonly_only: true
simulation_only: true
production_allowed: false
production_ready: false
default_switch_allowed: false
formal_phase_yz_write_allowed: false
latest_pointer_mutation_allowed: false
provider_publish_allowed: false
accepted_latest_switch_allowed: false
broker_authorized: false
---

# POLICY_MTRP7_S_R_REAL_TIER_A_SHADOW_RERUN_REPAIR_WORK_CN

## 1. 目标

修复 MTRP7_S 审查发现的 blocker：

```text
MTRP7_R rerun 只有 manifest/validator/tier_a_rerun_dates，
没有真实生成 daily bridge / OrderIntent / readonly replay / shadow accumulation artifact。
```

本阶段目标：

```text
使用 MTRP7_S 已补齐的 isolated ModelB root；
使用 MTRP7_R 已物化的 isolated_phase_yz clean Tier A lineage；
真实生成 Tier A MTRP7 shadow dry-run artifacts；
输出 daily bridge / OrderIntent / readonly replay / accumulation / audit；
使审查可以确认进入 MTRP8 shadow review。
```

## 2. 非目标

本阶段不做：

```text
训练/调参/更换模型
新增 ModelB scoring
provider refresh / publish
accepted latest switch
latest pointer mutation
formal phase_yz 写入
formal PriceStore 写入
production/default registry 修改
frontend/API/Agent 修改
daily auto 主链路/default path 修改
broker / quick-trade / real order
target_weight / target_position / quantity instruction
收益筛选或收益调参
```

## 3. 输入

必须使用：

```text
data_tw/artifacts/shadow_readiness/top50_hold_rank_buffer_100/mtrp7_s_clean_daily_modelb_ltr_top50_accumulation_build/
data_tw/artifacts/shadow_readiness/top50_hold_rank_buffer_100/mtrp7_s_clean_daily_modelb_ltr_top50_accumulation_build/isolated_modelb_yz2/
data_tw/artifacts/shadow_readiness/top50_hold_rank_buffer_100/mtrp7_s_clean_daily_modelb_ltr_top50_accumulation_build/mtrp7_r_rerun/isolated_phase_yz/
```

可复用：

```text
scripts/build_tw_policy_mtrp7_isolated_daily_shadow_dry_run.py
scripts/build_tw_policy_mtrp7_r_clean_daily_tier_a_lineage_and_rerun.py
```

但必须避免原 MTRP7 builder 的 Tier B hard-code 污染结果。

## 4. 输出

新增或修复 builder：

```text
scripts/build_tw_policy_mtrp7_s_r_real_tier_a_shadow_rerun_repair.py
```

输出 root：

```text
data_tw/artifacts/shadow_readiness/top50_hold_rank_buffer_100/mtrp7_s_clean_daily_modelb_ltr_top50_accumulation_build/mtrp7_s_r_real_tier_a_shadow_rerun_repair/
```

必须输出：

```text
manifest.json
daily_input_discovery.csv
daily_bridge_artifact_register.csv
daily_order_intent_artifact_register.csv
daily_shadow_replay_artifact_register.csv
shadow_accumulation_register.csv
candidate_baseline_skip_delta.csv
lineage_checksum_audit.csv
price_mark_coverage_audit.csv
readonly_wording_audit.csv
forbidden_scope_audit.csv
validator_report.json
diagnostic_findings.md
```

必须生成 daily 子 artifact：

```text
daily_bridge_artifacts/{signal_date}/manifest.json
daily_bridge_artifacts/{signal_date}/signals.csv
daily_bridge_artifacts/{signal_date}/schema.json
daily_bridge_artifacts/{signal_date}/lineage_audit.csv
daily_bridge_artifacts/{signal_date}/forbidden_field_audit.json

daily_order_intent_artifacts/{signal_date}/manifest.json
daily_order_intent_artifacts/{signal_date}/order_intents.csv
daily_order_intent_artifacts/{signal_date}/schema.json
daily_order_intent_artifacts/{signal_date}/strategy_decision_audit.csv
daily_order_intent_artifacts/{signal_date}/forbidden_action_audit.json

daily_shadow_replay_artifacts/{signal_date}/manifest.json
daily_shadow_replay_artifacts/{signal_date}/summary.json
daily_shadow_replay_artifacts/{signal_date}/actions.csv
daily_shadow_replay_artifacts/{signal_date}/positions.csv
daily_shadow_replay_artifacts/{signal_date}/skip_reason_audit.csv
daily_shadow_replay_artifacts/{signal_date}/mark_coverage_audit.csv
```

执行报告：

```text
docs/tw_portfolio_decision_model/POLICY_MTRP7_S_R_REAL_TIER_A_SHADOW_RERUN_REPAIR_EXECUTION_REPORT_CN.md
```

## 5. 实现要求

真实 Tier A rerun 至少满足：

```text
input_tier = tier_a_clean_daily_lineage
tier_b_fallback_used = false
covered_shadow_signal_days >= 5
daily_bridge_artifact_count >= 5
daily_order_intent_artifact_count >= 5
daily_shadow_replay_artifact_count >= 5
all daily bridge validators pass
all daily OrderIntent validators pass
all daily replay/shadow validators pass
same_day_mark_coverage_ratio >= 0.99
max_mark_lag_days = 0
negative_cash_count = 0
duplicate_position_count = 0
skip delta tracked
forbidden scope clean
```

若无法真实生成 daily bridge/order/replay artifact，不得 PASS。

## 6. OrderIntent 边界

`order_intents.csv` 禁止：

```text
execution_date
execution_price
execution_quantity
quantity
shares
lots
cash
nav
equity
target_weight
target_position
broker
broker_order_id
order_id
quick_trade
daily_return
realized_pnl
unrealized_pnl
replay_return
```

Replay artifact 可以包含 cash/equity/PnL 账务字段，但不得回流到 bridge/order。

## 7. 允许 verdict

执行者 verdict：

```text
PASS_REAL_TIER_A_SHADOW_RERUN_READY_FOR_MTRP8
FAIL_NEEDS_MTRP7_S_R_REPAIR
STOP_COORDINATOR_DECISION_REQUIRED
```

审查者 verdict：

```text
PASS_REAL_TIER_A_SHADOW_RERUN_READY_FOR_MTRP8
FAIL_NEEDS_MTRP7_S_R_REPAIR
STOP_COORDINATOR_DECISION_REQUIRED
```

## 8. 审查重点

审查者必须确认：

```text
daily bridge / OrderIntent / replay-shadow artifacts 真实存在
不是只有 manifest/validator/tier_a_rerun_dates
input_tier 为 Tier A，且 tier_b_fallback_used=false
使用 MTRP7_S isolated ModelB 与 MTRP7_R isolated_phase_yz
OrderIntent 无 target/quantity/broker/execution/cash/nav/equity
replay cash/equity/PnL 未回流到 signal/order input
forbidden scope clean
不触碰 production/default/latest/provider/frontend/API/Agent/PriceStore/broker/order
```

## 9. 下一步

若通过：

```text
进入 MTRP8 shadow review / readonly exposure design review。
仍不授权 production default switch。
```

若失败：

```text
继续 repair Tier A shadow rerun，不得回退 Tier B。
```
