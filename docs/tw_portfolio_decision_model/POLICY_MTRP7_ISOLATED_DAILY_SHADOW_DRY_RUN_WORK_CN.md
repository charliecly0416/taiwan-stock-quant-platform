---
created_at: 2026-06-28
status: work_doc
phase: MTRP7_ISOLATED_DAILY_SHADOW_DRY_RUN
parent_phase: MTRP6_DAILY_FULL_RANK_BRIDGE_AND_CANDIDATE_SHADOW_INTEGRATION_CONTRACT
strategy_candidate: top50_hold_rank_buffer_100
baseline_strategy: top50_exit_one_worst_sell
readonly_only: true
simulation_only: true
production_allowed: false
production_ready: false
default_switch_allowed: false
daily_auto_default_path_mutation_allowed: false
frontend_api_agent_mutation_allowed: false
provider_publish_allowed: false
accepted_latest_switch_allowed: false
broker_authorized: false
---

# POLICY_MTRP7_ISOLATED_DAILY_SHADOW_DRY_RUN_WORK_CN

## 1. 目标

MTRP7 进入实际 isolated daily shadow dry-run。

目标不是重新证明收益，也不是切生产，而是验证 MTRP6 定义的合同能否在隔离路径中每天实际产出：

```text
daily full-rank bridge artifact
daily candidate OrderIntentArtifact
daily readonly replay/shadow artifact
multi-day shadow accumulation register
lineage/checksum audit
skip reason delta audit
price/mark coverage audit
forbidden scope audit
```

MTRP7 最低要求覆盖不少于 5 个交易日。若无法取得 5 个可用交易日，必须给出 `STOP_INSUFFICIENT_DAILY_INPUTS` 或 `FAIL_NEEDS_MTRP7_REPAIR`，不得伪造日期或用非交易日补数。

## 2. 非目标

本阶段不做：

```text
production default switch
production registry selectable/default 修改
frontend/API/Agent 代码改动
daily auto 主链路/default path 改动
latest pointer 改动
provider refresh / publish
accepted latest switch
formal PriceStore write
broker / quick-trade / real order
target_weight / target_position / quantity instruction
模型训练 / 新 inference / LTR 重算
新收益筛选或调参
```

## 3. 前置事实

MTRP6 已通过：

```text
docs/tw_portfolio_decision_model/POLICY_MTRP6_DAILY_FULL_RANK_BRIDGE_AND_CANDIDATE_SHADOW_INTEGRATION_CONTRACT_REVIEW_CN.md
verdict = PASS_READY_FOR_MTRP7_DAILY_SHADOW_DRY_RUN
```

MTRP6 只授权本阶段做 isolated daily shadow dry-run，不授权生产接入。

当前候选策略：

```text
strategy_rule = top50_hold_rank_buffer_100
candidate_k = 50
hold_rank_buffer = 100
target_holding_count = 10
max_buy_count = 1
max_sell_count = 1
buy = top50 内 buy_score 最高且未持有
sell = 持仓 full_qlib_rank > 100 时卖出最差一支
```

P3 同窗口收益证据只作为背景，不作为 MTRP7 的优化输入：

```text
candidate total_return = 0.9605828337
baseline total_return = 0.8894811577
candidate max_drawdown = -0.1104340101
baseline max_drawdown = -0.1369660506
```

## 4. 输入优先级

执行者必须先发现可用 daily 输入，并在 manifest 中标记 input tier。

### Tier A: clean daily lineage

优先使用：

```text
daily model_a 150-row qlib ModelSignalArtifact
daily model_b top50 LTR ModelSignalArtifact
daily readonly PriceStore / next_open / mark close source
```

要求：

```text
model_a 每日 rows >= 100，最好 150
model_b 每日 top50 rows = 50
top50 buy_score 来自 model_b LTR
non-top50 行只提供 qlib full_qlib_rank visibility，不允许买入 ranking
available_at <= signal_asof
source lineage / checksum 可追踪
```

若 Tier A 可用且 5 个交易日全部通过，可给：

```text
PASS_READY_FOR_MTRP8_SHADOW_REVIEW
```

### Tier B: isolated mechanics fallback

若 Tier A 不可用，但已有 MTRP2_R/P2_R audited broad bridge 可按日拆分生成 isolated artifacts，可用于验证 builder/replay mechanics。

Tier B 必须显式标记：

```text
input_tier = tier_b_repackaged_research_lineage_mechanics_only
source_lineage_warning = existing_audited_broad_reference_repackaged_for_production_candidate_readiness
production_lineage_blocker = true
```

Tier B 最多给：

```text
PASS_MECHANICS_READY_LINEAGE_BLOCKED
```

不得把 Tier B 说成 production-ready，也不得进入 production default switch。

### 无可用输入

若 Tier A 和 Tier B 都不可用，必须 STOP：

```text
STOP_INSUFFICIENT_DAILY_INPUTS
```

## 5. 执行者任务

执行者应新增 builder：

```text
scripts/build_tw_policy_mtrp7_isolated_daily_shadow_dry_run.py
```

输出 root：

```text
data_tw/artifacts/shadow_readiness/top50_hold_rank_buffer_100/mtrp7_isolated_daily_shadow_dry_run/
```

建议 artifact 子目录：

```text
daily_bridge_artifacts/{signal_date}/
daily_order_intent_artifacts/{signal_date}/
daily_shadow_replay_artifacts/{signal_date}/
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

执行报告：

```text
docs/tw_portfolio_decision_model/POLICY_MTRP7_ISOLATED_DAILY_SHADOW_DRY_RUN_EXECUTION_REPORT_CN.md
```

## 6. Daily bridge artifact 要求

每日 bridge artifact 至少包含：

```text
manifest.json
signals.csv
schema.json
lineage_audit.csv
forbidden_field_audit.json
```

`signals.csv` 必须满足：

```text
rows >= 100
top50 rows = 50
non_top50_visibility_rows >= 50
full_qlib_rank populated for all rows
top50 buy_score populated from LTR or declared top50 source
non-top50 buy_score blank / buy ranking disabled
available_at <= signal_asof
production_candidate = true
production_allowed = false
not_published_latest = true
```

禁止：

```text
future_return / label / forward_return
replay_return as input
new training / inference / LTR recompute
accepted latest switch
provider publish
formal PriceStore write
```

## 7. Daily candidate OrderIntent 要求

每日 OrderIntent artifact 至少包含：

```text
manifest.json
order_intents.csv
schema.json
strategy_decision_audit.csv
forbidden_action_audit.json
```

要求：

```text
strategy_rule = top50_hold_rank_buffer_100
input_signal = 当日 bridge manifest
input_portfolio_state = readonly prior shadow state
max_buy_count = 1
max_sell_count = 1
candidate_k = 50
hold_rank_buffer = 100
non_top50_buy_count = 0
missing_holding_visibility_policy = stop_or_skip_with_audit
```

`order_intents.csv` 禁止字段：

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
broker_order_id
```

## 8. Daily readonly replay/shadow 要求

每日 replay/shadow artifact 至少包含：

```text
manifest.json
summary.json
actions.csv
positions.csv
skip_reason_audit.csv
mark_coverage_audit.csv
```

要求：

```text
execution_price = next_open
execution_date_policy = next_tradeable_day_after_signal_date
fee_rate = 0.001425
sell_tax_rate = 0.003
lot_size = 10
same_day_mark_coverage_ratio >= 0.99
max_mark_lag_days = 0
negative_cash_count = 0
duplicate_position_count = 0
candidate-baseline same-day comparison required
```

Replay 可以计算 cash/NAV/equity/PnL，但这些字段只允许出现在 replay/shadow artifact 中，不允许回流到 bridge 或 OrderIntent。

## 9. Shadow accumulation gate

最低 gate：

```text
minimum_shadow_days >= 5 trading days
all daily bridge validators pass
all daily OrderIntent validators pass
all daily replay/shadow validators pass
lineage/checksum consistent
skip reason delta tracked
price mark coverage pass
readonly wording pass
forbidden scope clean
no production default/latest/provider mutation
```

## 10. Forbidden scope audit

必须审计且全部为 `performed=false`：

```text
production_default_registry_change
production_registry_selectable_change
frontend_code_change
api_code_change
agent_code_change
daily_auto_default_path_change
latest_pointer_change
provider_refresh_or_publish
accepted_latest_switch
formal_pricestore_write
broker_connection
quick_trade
real_order
target_weight_instruction
target_position_instruction
quantity_instruction
model_training
model_inference
ltr_recompute
new_return_experiment_or_tuning
```

## 11. 允许 verdict

执行者 verdict：

```text
PASS_READY_FOR_MTRP8_SHADOW_REVIEW
PASS_MECHANICS_READY_LINEAGE_BLOCKED
FAIL_NEEDS_MTRP7_REPAIR
STOP_INSUFFICIENT_DAILY_INPUTS
STOP_COORDINATOR_DECISION_REQUIRED
```

审查者 verdict：

```text
PASS_READY_FOR_MTRP8_SHADOW_REVIEW
PASS_MECHANICS_READY_LINEAGE_BLOCKED
FAIL_NEEDS_MTRP7_REPAIR
STOP_INSUFFICIENT_DAILY_INPUTS
STOP_COORDINATOR_DECISION_REQUIRED
```

## 12. 审查重点

审查者必须确认：

```text
是否真实生成每日 bridge / OrderIntent / replay-shadow artifacts
是否覆盖至少 5 个真实交易日
是否明确标记 Tier A 或 Tier B input lineage
是否没有把 Tier B research lineage 误说成 production-ready
是否没有越界修改 daily auto / frontend / API / Agent / latest / provider / PriceStore
是否没有 OrderIntent target/quantity/broker 字段
是否 replay cash/NAV/PnL 没有回流到 signal/order input
是否 skip delta、lineage checksum、price mark coverage 都有证据
```

## 13. 下一步边界

若 `PASS_READY_FOR_MTRP8_SHADOW_REVIEW`：

```text
MTRP8 可以做 shadow review / readonly exposure design review。
仍不授权 production default switch。
```

若 `PASS_MECHANICS_READY_LINEAGE_BLOCKED`：

```text
说明 mechanics 可行，但 production lineage blocker 仍存在。
下一步应修 clean daily ModelA/ModelB lineage 或接入只读 shadow builder 的正式 daily source。
```

若 `FAIL` 或 `STOP`：

```text
不得进入 MTRP8，必须 repair 或回到 coordinator 决策。
```
