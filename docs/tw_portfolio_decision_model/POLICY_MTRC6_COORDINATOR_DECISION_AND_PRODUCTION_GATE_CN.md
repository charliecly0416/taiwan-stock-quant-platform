---
created_at: 2026-06-28
status: coordinator_decision
phase: MTRC6_COORDINATOR_DECISION_AND_PRODUCTION_GATE
parent_phase: MTRC5_MARK_TO_MARKET_PRICE_COVERAGE_REPAIR_AND_RERUN
parent_review: docs/tw_portfolio_decision_model/POLICY_MTRC5_MARK_TO_MARKET_PRICE_COVERAGE_REPAIR_AND_RERUN_REVIEW_CN.md
readonly_only: true
simulation_only: true
diagnostic_only: true
research_only: true
production_allowed: false
---

# POLICY_MTRC6_COORDINATOR_DECISION_AND_PRODUCTION_GATE_CN

## 1. Coordinator Decision

MTRC5 通过：

```text
PASS_MARK_QUALITY_REPAIRED_READY_FOR_COORDINATOR_DECISION
```

统筹结论：

```text
MTRC research-only 路线的 mark-to-market / price coverage blocker 已清除。
MTRC5 证明：在固定 MTRC2_S OrderIntent、固定 MTRC2_T_R execution next_open、固定费用税费和固定交易规则的前提下，
补齐持仓逐日 close mark 后，研究回放仍保留很高绝对收益。

但 MTRC5 仍不得直接接入生产。
原因不是收益证据消失，而是当前产物仍属于 research-only lineage，不是 production artifact lineage。
```

本阶段 decision：

```text
KEEP_AS_HIGH_PRIORITY_PRODUCTION_CANDIDATE_REQUIRES_FORMAL_ONBOARDING
```

## 2. 已清除的问题

MTRC4 的核心 blocker 是 mark-quality 失败：

```text
MTRC3 fallback_ratio = 0.8996056241
MTRC3 final_date_fallback_ratio = 0.9
MTRC3 max_mark_lag_days = 469
```

MTRC5 已修复：

```text
same_day_mark_coverage_ratio = 1.0
final_date_same_day_mark_coverage_ratio = 1.0
fallback_ratio = 0.0
final_date_fallback_ratio = 0.0
max_mark_lag_days = 0
missing_price_count = 0
```

MTRC5 replay 结果：

```text
final_equity = 2765375861.077763
total_return = 2764.3758610778
max_drawdown = -0.3928470036
action_count = 2129
buy_count = 1069
sell_count = 1060
skipped_action_count = 249
max_holding_count = 10
negative_cash_count = 0
duplicate_position_count = 0
```

审查确认：

```text
MTRC2_S OrderIntent 固定；
MTRC2_T_R execution_date / next_open 固定；
mark_price_bridge 只使用允许的本地非 demo full OHLCV 源；
未训练模型、未重算 LTR、未修改 signal/order-intent、未调参、未写生产链路。
```

## 3. 仍不能直接生产接入的原因

### 3.1 当前策略合同仍标记 research-only

当前 MTRC 使用的策略：

```text
strategy_rule = mechanism_transfer_top50_cost_aware_v1
```

其 dependency 明确标记：

```text
diagnostic_only: true
research_only: true
production_allowed: false
not_valid_strategy_evidence: true
not_default_candidate: true
```

这意味着 MTRC5 的产物只能证明研究路线可行，不能直接成为生产默认策略。

### 3.2 当前 artifact 路径不是 production artifact lineage

MTRC5 输出路径：

```text
data_tw/experiments/policy_mtr_research_only_continuation/mtrc5_mark_to_market_price_coverage_repair_and_rerun/
```

manifest 明确：

```text
artifact_type = ResearchOnlyMTRC5MarkToMarketCoverageRepairArtifact
research_only = true
production_allowed = false
not_strategy_input = true
```

生产链路不能直接消费 `data_tw/experiments/...` 下的研究产物。

### 3.3 还缺合法的 production baseline delta

MTRC5 是 same-signal research-only replay，证明的是候选机制在研究链路中有效。

生产接入还必须回答：

```text
在同一 production ModelSignalArtifact、同一 production PriceStore、同一 replay window、同一费用税费口径下，
候选策略是否稳定优于当前 production default top50_exit_one_worst_sell？
```

这个比较目前还没有被 production artifact 化。

### 3.4 还缺日更和 shadow 证据

生产策略不能只靠历史回放通过。

还需要证明：

```text
daily auto 可以自动生成候选策略 OrderIntentArtifact；
readonly replay / snapshot 可以稳定构建；
Agent / frontend 只读展示不会产生真实下单或 target position/weight 误读；
连续多个交易日 shadow accumulation 无 blocker。
```

## 4. 生产接入路线

生产接入应拆成 5 个 gate。

### Gate P0: Formal Strategy Contract

目标：

```text
把 mechanism_transfer_top50_cost_aware_v1 从 research-only 机制，收敛成一个正式 production-candidate StrategyRule。
```

建议新策略名：

```text
top50_hold_rank_buffer_100
```

或者如果希望保留机制来源：

```text
top50_exit_hold_rank_buffer_100
```

必须新增或修改：

```text
configs/strategy_dependencies/top50_hold_rank_buffer_100.yaml
```

要求：

```text
diagnostic_only: false
research_only: false
production_allowed: false
production_candidate: true
frontend_selectable: false
production_default: false
max_buy_count: 1
max_sell_count: 1
target_holding_count: 10
candidate_k: 50
hold_rank_buffer: 100
```

注意：

```text
production_allowed 仍先保持 false。
只有完成后续 gates 后，才允许进入 registry selectable/default 决策。
```

### Gate P1: Production ModelSignalArtifact Adapter

目标：

```text
候选策略不得读取 MTRC 私有 signal CSV。
必须消费当前生产链路的 ModelSignalArtifact。
```

固定输入应来自：

```text
configs/tw_product_artifact_registry.yaml
configs/tw_modular_registry.yaml
configs/tw_replay_window_policy.yaml
```

当前产品模型：

```text
Base Qlib: e4_frozen_qlib_2018_2022
Orthogonal LTR: e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025
```

策略输入字段：

```text
candidate_rank
buy_score
raw_score
score_rank
full_qlib_rank
signal_asof
available_at
source_artifact
```

禁止：

```text
读取 phase_s2b / phase_s2c / MTRC1D 私有 CSV；
重训或重算 LTR；
用 replay return 调参；
用 future return / label / realized pnl。
```

### Gate P2: Formal OrderIntentArtifact Build

目标：

```text
用正式 StrategyRule + production ModelSignalArtifact + PortfolioState，
生成标准 OrderIntentArtifact。
```

输出路径应使用 production-candidate artifact 路径，不再使用 research experiments 路径，例如：

```text
data_tw/artifacts/strategies/top50_hold_rank_buffer_100/{run_id}/
```

必须输出：

```text
manifest.json
order_intents.csv
schema.json
strategy_decision_audit.csv
forbidden_action_audit.json
validator_report.json
```

OrderIntent 禁止包含：

```text
execution_date
execution_price
execution_quantity
commission
tax
cash
equity
daily_return
realized_pnl
target_weight
target_position
broker_order_id
```

### Gate P3: Same-Window Production Baseline Replay

目标：

```text
在同一 production signal、同一 production PriceStore、同一 replay window 下，
同时回放：
1. 当前默认策略 top50_exit_one_worst_sell
2. 新候选策略 top50_hold_rank_buffer_100
```

必须固定：

```text
execution_price = next_open
initial_equity = 1000000
target_holdings = 10
fee_rate = 0.001425
sell_tax_rate = 0.003
lot_size = 10
cash_policy = no_negative_cash_unless_explicitly_allowed_and_audited
```

硬性 gate：

```text
same_day_mark_coverage_ratio >= 0.99
max_mark_lag_days = 0
negative_cash_count = 0
duplicate_position_count = 0
missing_price_count = 0
execution_next_open_preserved = true
```

收益 gate 建议：

```text
候选 total_return > baseline total_return
候选 max_drawdown 不得显著劣于 baseline
候选 skipped/action 变化必须可解释
至少输出 monthly / rolling / drawdown / concentration diagnostics
```

如果候选收益更高但回撤明显更大，应进入 coordinator decision，不得自动生产。

### Gate P4: Readonly Snapshot / Frontend / Agent Shadow

目标：

```text
把候选策略作为 readonly selectable shadow，不作为默认策略。
```

允许先接入：

```text
readonly replay window
readonly strategy snapshot
frontend strategy workbench selectable candidate
Agent context citation-only explanation
paper portfolio simulation-only diagnostic
```

仍禁止：

```text
production default switch
broker
quick-trade
target_weight / target_position
real order
收益承诺
```

必须连续 shadow accumulation：

```text
至少 5 个交易日无 blocker；
每日自动构建成功；
validator 全通过；
latest/snapshot/checksum/source lineage 一致；
frontend/API/Agent 无 forbidden action 文案。
```

### Gate P5: Production Go/No-Go

只有 P0-P4 全部通过后，才能开 production Go/No-Go closure。

Go 时才允许考虑修改：

```text
configs/tw_modular_registry.yaml
configs/tw_product_artifact_registry.yaml
configs/tw_replay_window_policy.yaml
readonly_strategy_snapshot latest pointer
frontend selectable/default display
daily auto update strategy build chain
```

默认策略切换必须单独审查：

```text
top50_exit_one_worst_sell -> top50_hold_rank_buffer_100
```

即使 Go，也仍然只允许：

```text
readonly / simulation / paper portfolio
```

不授权真实交易。

## 5. 当前推荐下一步工作文档

建议下一阶段名称：

```text
POLICY_MTRP0_FORMAL_PRODUCTION_CANDIDATE_STRATEGY_CONTRACT_WORK_CN
```

目标：

```text
把 MTRC5 已验证的 M2_hold_rank_buffer_100 机制，转成正式 production-candidate StrategyRule 合同。
不跑新收益实验，不接生产默认，不改 frontend/API/Agent。
```

执行者应完成：

```text
1. 新增 production-candidate dependency YAML；
2. 明确它与 research-only mechanism_transfer_top50_cost_aware_v1 的差异；
3. 定义正式 StrategyRule 输入、输出、forbidden fields/actions；
4. 定义 P1/P2/P3 所需 artifact 路径；
5. 写 validator checklist；
6. 写 execution report。
```

审查者应检查：

```text
1. 是否仍有 research_only / diagnostic_only / not_valid_strategy_evidence 残留；
2. 是否误把 production_allowed 或 production_default 打开；
3. 是否遵守 ModelSignal -> StrategyRule -> OrderIntent -> ReplayResult 边界；
4. 是否禁止 target_weight / target_position / broker/order；
5. 是否没有读取 MTRC 私有 CSV 或 replay return；
6. 是否可以进入 P1 adapter / OrderIntent build。
```

## 6. 本阶段禁止动作

本 coordinator decision 不授权：

```text
修改生产默认策略
修改 frontend 默认展示
修改 API 默认策略
修改 Agent 默认策略上下文
修改 daily auto 默认链路
provider refresh / publish
accepted latest switch
正式 PriceStore 写入
broker / quick-trade / real order
target_weight / target_position
```

## 7. 对用户的直接结论

```text
MTRC5 结果值得继续推进生产候选化。
但不能跳过合同化、production artifact lineage、同窗口 baseline replay、readonly shadow 和 Go/No-Go。
最快路径不是直接接入生产，而是先把 MTRC5 的 hold_rank_buffer_100 机制转成正式 production-candidate 策略，
然后用当前生产 qlib+LTR 信号和生产价格源跑同口径 baseline-vs-candidate replay。
```
