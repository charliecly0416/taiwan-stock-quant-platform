---
created_at: 2026-06-28
status: coordinator_closure
phase: MTRP5_GO_NO_GO_CLOSURE
strategy_rule: top50_hold_rank_buffer_100
readonly_only: true
simulation_only: true
production_allowed: false
production_ready: false
default_switch_authorized: false
---

# POLICY_MTRP5_GO_NO_GO_CLOSURE_CN

## 1. Go / No-Go Verdict

当前结论：

```text
NO_GO_FOR_PRODUCTION_DEFAULT
CONDITIONAL_GO_FOR_READONLY_SHADOW_INTEGRATION_DESIGN
```

解释：

```text
top50_hold_rank_buffer_100 已经具备明确的生产候选价值：
在 2026-01-02..2026-05-07 同窗口、同 bridge、同 next_open、同费用税费和同 mark-to-market 口径下，
候选策略相对当前 baseline top50_exit_one_worst_sell 收益更高、回撤更低、交易次数更少。

但它还不能直接接入生产默认链路。
原因不是收益不够，而是 production lineage、daily auto、live shadow、frontend/API/Agent readonly integration 仍未完成。
```

## 2. 已通过证据

### 2.1 MTRP0-P2 合同与 readiness

正式候选策略合同已建立：

```text
configs/strategy_dependencies/top50_hold_rank_buffer_100.yaml
```

策略语义：

```text
candidate_k = 50
hold_rank_buffer = 100
target_holding_count = 10
max_buy_count = 1
max_sell_count = 1
buy = top50 内 buy_score 最高且未持有
sell = 持仓 full_qlib_rank > 100 时卖出最差一支
```

初始 production signal readiness 曾正确 STOP：

```text
当前 production model_b_yz2 只有 top50 行，不能支持 rank buffer 100 的持仓可见性。
```

随后 MTRP2_R 构建 production-candidate bridge：

```text
data_tw/artifacts/signals/top50_hold_rank_buffer_100_full_rank_visibility_bridge/mtrp2_r_20260628T181347Z/
```

bridge 结果：

```text
date_range = 2026-01-02..2026-05-07
bridge_rows = 11837
daily_min_rows = 149
top50_rows = 3950
non_top50_visibility_rows = 7887
```

候选 OrderIntent：

```text
data_tw/artifacts/strategies/top50_hold_rank_buffer_100/mtrp2_r_20260628T181347Z/
order_intent_rows = 76
buy_intents = 43
sell_intents = 33
```

审查结论：

```text
PASS_READY_FOR_P3_SAME_WINDOW_REPLAY_WITH_LINEAGE_WARNING
```

### 2.2 P3 同窗口 replay 证据

P3 输出：

```text
data_tw/artifacts/replays/top50_hold_rank_buffer_100/mtrp3_same_window_replay_comparison/
```

同口径：

```text
window = 2026-01-02..2026-05-07
execution_price = next_open
initial_equity = 1000000
fee_rate = 0.001425
sell_tax_rate = 0.003
lot_size = 10
same_day_mark_coverage_ratio = 1.0
max_mark_lag_days = 0
```

结果：

| metric | baseline top50_exit_one_worst_sell | candidate top50_hold_rank_buffer_100 |
| --- | ---: | ---: |
| final_equity | 1,889,481.157718 | 1,960,582.833712 |
| total_return | 0.8894811577 | 0.9605828337 |
| max_drawdown | -0.1369660506 | -0.1104340101 |
| actions | 137 | 66 |
| skipped | 7 | 10 |
| same_day_mark_coverage_ratio | 1.0 | 1.0 |
| max_mark_lag_days | 0 | 0 |

审查结论：

```text
PASS_CANDIDATE_OUTPERFORMS_READY_FOR_P4_SHADOW_READINESS
```

统筹判断：

```text
候选策略确实比 baseline 多约 7.11 个百分点收益，
最大回撤改善约 2.65 个百分点，
交易次数减少 71 次。
这是目前最强的 policy 改善证据。
```

### 2.3 P4 shadow readiness

P4 输出：

```text
data_tw/artifacts/shadow_readiness/top50_hold_rank_buffer_100/mtrp4_shadow_readiness/
```

通过 gate：

```text
candidate_outperforms_baseline = true
drawdown_not_worse = true
mark_quality_pass = true
execution_price_pass = true
order_intent_contract_pass = true
forbidden_scope_clean = true
lineage_warning_present = true
```

同时保留：

```text
production_ready = false
needs_multi_day_shadow = true
needs_daily_auto_integration_contract = true
needs_frontend_api_agent_readonly_contract = true
```

审查结论：

```text
PASS_READY_FOR_MTRP5_GO_NO_GO_CLOSURE
```

## 3. 当前 open blockers

仍阻断 production default 的 blockers：

1. `source_lineage_still_repackaged_from_research_only_broad_reference`

   P2_R bridge 来自 existing audited broad reference repackaging。它适合作为 production-candidate readiness 证据，但不是干净的 daily production signal lineage。

2. `window_only_2026_01_02_to_2026_05_07`

   当前 replay 只覆盖一个固定窗口。还没有更长窗口、未来日、或多日 live shadow accumulation。

3. `no_daily_auto_generation_for_candidate`

   daily auto 还不会每天自动生成 `top50_hold_rank_buffer_100` 所需 full-rank visibility bridge、OrderIntent、replay/shadow artifact。

4. `no_live_latest_shadow_accumulation`

   还没有连续交易日 shadow 结果，无法证明最新链路每天稳定。

5. `no_frontend_api_agent_readonly_integration`

   尚未把候选策略以只读候选方式接入 frontend/API/Agent。不能直接展示为默认策略或生产结论。

6. `candidate_skipped_count_higher_than_baseline`

   candidate skipped = 10，baseline skipped = 7。虽然收益和回撤更好，但 P4/P5 后续 shadow 必须追踪 skip reason 是否稳定可解释。

7. `no_production_default_switch_authorized`

   本阶段没有授权切换 default strategy。

## 4. 怎样才能接入生产

接入生产应继续按以下顺序做。

### Step 1: Formal daily full-rank bridge

目标：

```text
把 P2_R 的 bridge 从 repackaged research reference，升级为 daily auto 可重复构建的正式 production-candidate bridge。
```

要求：

```text
每日 model_a 150 行 qlib rank 可用；
每日 model_b top50 LTR score 可用；
top50 行保留 LTR buy_score；
non-top50 行只提供 qlib full_qlib_rank visibility，不允许买入 ranking；
manifest 标记 production_candidate=true, production_allowed=false。
```

### Step 2: Daily candidate OrderIntent builder

目标：

```text
daily auto 能为 top50_hold_rank_buffer_100 生成 OrderIntentArtifact。
```

要求：

```text
只输出 buy/sell/hold/skip 意图；
不输出 execution_price / quantity / cash / NAV / target_weight / target_position；
validator 检查 non-top50 buy = 0，max buy/sell <= 1，holding visibility missing = 0。
```

### Step 3: Readonly replay + shadow artifact

目标：

```text
每日生成候选策略 readonly replay/shadow artifact，与当前 baseline 同日对照。
```

要求：

```text
next_open execution；
same-day close mark；
mark coverage = 1.0；
max_mark_lag_days = 0；
negative cash = 0；
duplicate position = 0；
skip reason audited。
```

### Step 4: Frontend / API / Agent readonly candidate integration

目标：

```text
允许用户在只读界面看到 top50_hold_rank_buffer_100 的 shadow/replay 结果。
```

限制：

```text
不得标记为 default；
不得输出 target_weight / target_position；
不得给 broker/order/quick-trade 入口；
Agent 只能引用 artifact 解释，不得给交易指令。
```

### Step 5: Multi-day shadow accumulation

最低要求：

```text
至少 5 个交易日连续 shadow 成功；
每日 validator pass；
每日 signal/order/replay/checksum/source lineage 一致；
candidate skip reason 可解释；
无 forbidden field/action；
无 frontend/API/Agent 误导性生产或实盘措辞。
```

### Step 6: Production default switch Go/No-Go

只有 Step 1-5 通过后，才允许新开 default switch 审查。

Go 时才考虑修改：

```text
configs/tw_modular_registry.yaml
configs/tw_product_artifact_registry.yaml
configs/tw_replay_window_policy.yaml
readonly strategy snapshot index/latest
frontend selectable/default display
daily auto update candidate build chain
```

即使 Go，也仍然只允许：

```text
readonly / simulation / paper portfolio
```

不授权真实交易。

## 5. 当前最终判断

```text
策略开发角度：成功。
生产默认角度：暂时 No-Go。
只读 shadow 接入设计角度：Conditional Go。
```

当前最合理的下一步：

```text
MTRP6_DAILY_FULL_RANK_BRIDGE_AND_CANDIDATE_SHADOW_INTEGRATION_CONTRACT
```

目标不是再证明收益，而是把 P2_R/P3 的有效机制纳入可每日重复、可审查、可前端/API/Agent 只读展示的候选链路。
