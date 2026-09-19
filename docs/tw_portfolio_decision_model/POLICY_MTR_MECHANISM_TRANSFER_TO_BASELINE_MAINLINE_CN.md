---
created_at: 2026-06-28
status: coordinator_mainline
route: POLICY_MTR_MECHANISM_TRANSFER_TO_BASELINE
research_type: mechanism_transfer_to_existing_baseline
readonly_only: true
simulation_only: true
production_allowed_initially: false
strict_test_authorized_initially: false
order_intent_allowed_after_contract: true
target_weight_allowed: false
target_position_allowed: false
provider_publish_allowed: false
accepted_latest_switch_allowed: false
frontend_default_switch_allowed: false
broker_authorized: false
---

# POLICY_MTR_MECHANISM_TRANSFER_TO_BASELINE_MAINLINE_CN

## 1. 统筹结论

下一步不应继续扩大 JMD/RL 模型，也不应先放宽生产动作空间。

当前最合理路线是：

```text
把论文/JMD 中已验证可迁移的机制
迁移到现有强 baseline 的 StrategyRule / OrderIntent / Replay 合同链路
```

本路线命名为：

```text
POLICY_MTR_MECHANISM_TRANSFER_TO_BASELINE
```

MTR 的目标不是训练新模型，而是把以下机制迁移到 qlib-only 与 qlib+LTR baseline：

```text
turnover budget
max replacement
hold buffer / portfolio memory
cost-aware replacement gate
rank / score persistence
regime-aware risk control hook
```

核心判断：

```text
论文方法直接复现不适配，并不代表论文机制不可用。
JMD2-R 已证明 cost/turnover/persistence 机制能把 net 从负修到正；
但 raw supervised utility signal 仍弱于简单 baseline。
因此机制应迁移到现有 qlib+LTR 强信号，而不是继续训练更复杂 policy。
```

## 2. 背景事实

### 2.1 当前产品 baseline

项目当前产品主线来自宪法：

```text
Base Qlib:
e4_frozen_qlib_2018_2022

Orthogonal LTR:
e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025

Default strategy:
top50_exit_one_worst_sell
```

LTR 语义保持：

```text
Qlib candidate_rank / full_qlib_rank 定义 top50 candidate universe 和 sell boundary；
LTR buy_score 只在 Qlib top50 内重排买入顺序；
LTR 不改变 Qlib top50 退出边界。
```

### 2.2 JMD2 / JMD2-R 结论

JMD2 raw supervised utility：

```text
gross_total_return = 0.588862
net_after_fee_tax = -0.349629
average_turnover = 1.265702
```

JMD2-R best repair：

```text
policy = jmd2_r2_max_replace_1
net_after_fee_tax = 0.351752
average_turnover = 0.216116
```

对照 baseline：

```text
liquidity baseline net = 0.418059
momentum baseline net = 0.559470
```

结论：

- 换手/成本机制有效；
- 但 raw supervised utility signal edge 不足；
- 不进入 JMD3 RL；
- 机制应迁移到更强的 qlib / qlib+LTR score 上。

### 2.3 为什么不先扩大动作空间

不先放宽 `target_weight` / `target_position`，原因：

- 当前生产合同禁止目标权重/目标仓位；
- EIIE/FinRL 等论文的 continuous allocation 自由度不能直接进入生产；
- 现有证据显示自由动作会放大高换手；
- 若没有强净收益约束，动作空间变大只会增加成本和审查复杂度；
- 只有 research-only diagnostic 显示明显上限后，才讨论生产合同扩展。

## 3. 参考研究机制与本项目采用方式

本路线不复现完整论文，而是迁移可审计机制。

### 3.1 EIIE / PVM

来源：Jiang, Xu, Liang, 2017, EIIE / Portfolio-Vector Memory。

可迁移机制：

```text
previous portfolio memory
turnover-aware reward
portfolio transition cost
hold/rebalance persistence
```

本项目采用：

```text
PortfolioState 中记录当前持仓；
StrategyRule 不因 score/rank 小幅波动无意义换仓；
max replacement / hold buffer 等价于离散化 portfolio memory。
```

不采用：

```text
continuous target_weight
online stochastic batch learning
直接输出 allocation vector
```

### 3.2 FinRL Environment Layer

来源：Liu et al., FinRL。

可迁移机制：

```text
data / environment / agent 分层
cash / holding / transaction cost explicit state
standardized backtest baseline comparison
```

本项目采用：

```text
StrategyDependency -> OrderIntentArtifact -> ReplayResultArtifact；
费用、税、换手、持仓、cash days 全部作为 replay audit；
不让策略直接记账或读 replay result。
```

不采用：

```text
live trading adapter
broker/order integration
FinRL 默认环境直接接生产
```

### 3.3 AlphaStock Winner/Loser Selection

来源：Wang et al., AlphaStock。

可迁移机制：

```text
winner selection
loser selling
attention/attribution style explanation
```

本项目采用：

```text
只替换最弱持仓；
只买入高优先级候选；
记录 holding overlap / rank overlap / replacement attribution。
```

不采用：

```text
attention score 直接作为 production buy list
未经合同的 action 输出
```

### 3.4 Risk-aware / Cost-aware Portfolio RL

可迁移机制：

```text
turnover penalty
drawdown / regime penalty
concentration penalty
cost-aware action gate
```

本项目采用：

```text
max_replace_per_day
score/rank advantage gate
risk-off market regime hook
concentration / turnover / fee-tax audit
```

## 4. 目标

MTR 目标：

```text
在不训练新模型、不放宽生产 target 合同的前提下，
把 cost-aware / persistence / max replacement 机制
接入 qlib-only 与 qlib+LTR 标准信号链路，
验证它是否能改善 net after fee/tax、回撤、换手和下跌期表现。
```

通过条件优先级：

1. 不破坏现有 baseline 核心收益；
2. 显著降低 turnover / fee / tax；
3. 2022 downturn 或其他 risk-off 窗口回撤改善；
4. qlib+LTR 上能保持 LTR 排名优势；
5. 全流程遵守 StrategyDependency / OrderIntent / ReplayResult 合同。

## 5. 非目标

本路线不做：

```text
新模型训练
RL / PPO / EIIE / FinRL 训练
continuous allocation
target_weight / target_position
读取模型私有文件
读取 future return / label / realized pnl 作为策略输入
2023-2025 LTR private artifacts 训练 policy
provider publish / accepted latest switch
frontend default switch
broker / quick-trade / real order
```

本路线初始也不改变生产默认策略。即使某个候选通过，也只能进入 readonly research candidate；是否生产化另开 Go/No-Go。

## 6. 机制候选

MTR 初始候选必须预声明，不允许后验无限搜索。

### M0 Baseline Parity

复现现有 baseline：

```text
top50_exit_one_worst_sell
```

必须做到 OrderIntent / Replay parity，作为后续所有机制的对照。

### M1 Max Replacement

机制：

```text
每日最多替换 N 支。
```

参数：

```text
max_replace_per_day in [1, 2]
```

注意：

```text
当前 baseline 本身每日最多一卖一买；
M1 重点是确认 qlib-only / qlib+LTR 不同窗口下的一致 parity 和可审计写法。
```

### M2 Hold Buffer

机制：

```text
已有持仓若仍在保留边界内，则不因轻微排序下降而卖出；
只卖出跌破 exit boundary 或明显劣化者。
```

参数：

```text
hold_rank_buffer in [60, 75, 100]
```

对 qlib+LTR：

```text
sell boundary 仍使用 qlib full_qlib_rank；
buy priority 使用 LTR buy_score；
不得让 LTR 改 qlib top50 / full rank exit boundary。
```

### M3 Score / Rank Advantage Gate

机制：

```text
只有当新候选相对最弱持仓具备足够优势时才替换。
```

允许使用：

```text
buy_score rank gap
buy_score standardized gap within same date
candidate_rank / full_qlib_rank deterioration
```

禁止：

```text
future return
next_open / next_close
execution price
realized pnl
replay return
```

参数：

```text
score_gap_min in [0.0, 0.25 daily z-score, 0.50 daily z-score]
rank_gap_min in [0, 5, 10]
```

### M4 Cost Gate

机制：

```text
若替换带来的 score/rank advantage 不足以覆盖预估 fee/tax，则跳过。
```

注意：

```text
cost gate 不能使用未来收益；
只能用固定 fee/tax 参数和当日可见 score/rank advantage。
```

### M5 Regime Risk Hook

机制：

```text
risk-off market regime 下提高替换门槛或降低 buy count；
risk-on 正常使用 baseline。
```

允许输入：

```text
TWII ret/MA/drawdown/volatility, computed from history <= signal_date
```

第一轮只允许 diagnostic：

```text
market_regime_code in {risk_on, neutral, risk_off}
```

不得用 validation return 后验定义 regime。

### M6 Combined Candidate

只允许以下预声明组合：

```text
C1: M1 max_replace=1 + M2 hold_rank_buffer=75
C2: M1 max_replace=1 + M3 score_z_gap_min=0.25
C3: M1 max_replace=1 + M2 hold_rank_buffer=75 + M3 score_z_gap_min=0.25
C4: C3 + M5 risk_off_buy_block_for_weak_score
```

## 7. 数据与评估窗口

### 7.1 初始 qlib-only 控制线

先用 qlib-only 是为了控制变量：

```text
source_signal = frozen_qlib_2018_2022 standard ModelSignalArtifact
candidate window = existing qlib-only replay windows where lineage is clean
```

若 2021/2022 qlib-only 标准信号缺失，不得临时拼 archive 私有文件冒充标准信号；应记录 lineage blocker。

### 7.2 qlib+LTR 迁移线

在 qlib-only 合同与 replay 通过后，迁移到：

```text
source_signal = e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025 standard ModelSignalArtifact
```

必须保持：

```text
candidate_rank / full_qlib_rank = qlib base
buy_score = LTR rerank score
sell boundary = qlib full_qlib_rank
```

### 7.3 评估窗口

优先使用已存在、lineage clean 的 readonly windows：

```text
2023-2025 historical replay candidate windows
2026 shadow / recent readonly windows if already available
2022 downturn only if comparable qlib/LTR signal lineage exists
```

如果某窗口信号不完整，必须写 coverage blocker，不得强行补私有模型输出。

## 8. 合同与 artifact 路径

### 8.1 StrategyDependency

每个候选或候选族必须先写 dependency：

```text
configs/strategy_dependencies/{strategy_rule}.yaml
```

建议命名：

```text
mechanism_transfer_top50_cost_aware_v1
```

dependency 必须声明：

```text
required_core_fields:
  - date
  - instrument
  - candidate_rank
  - buy_score
  - raw_score
  - score_rank
  - full_qlib_rank
  - signal_asof
  - available_at

ranking_usage:
  - candidate_rank: qlib_top50_candidate_boundary
  - full_qlib_rank: qlib_exit_boundary
  - buy_score: buy_priority_and_score_gap

max_buy_count: <= 1 initially
max_sell_count: <= 1 initially
diagnostic_only: true initially
production_allowed: false
```

### 8.2 OrderIntentArtifact

输出目录：

```text
data_tw/artifacts/strategies/mechanism_transfer_top50_cost_aware_v1/{run_id}/
```

必须符合 `ORDER_INTENT_CONTRACT_CN.md`。

禁止字段：

```text
execution_price
execution_quantity
cash
nav
daily_return
realized_pnl
target_position
target_weight
broker
order_id
```

### 8.3 ReplayResultArtifact

Replay 必须消费：

```text
OrderIntentArtifact
PriceStore
ExecutionConfig
InitialPortfolioState
```

不得让 replay 读取 strategy 私有状态或模型私有 CSV。

## 9. Phase Plan

### MTR0 Contract And Baseline Parity Feasibility

目标：

- 冻结机制候选；
- 写 StrategyDependency；
- 识别 qlib-only / qlib+LTR 可用 ModelSignalArtifact；
- 确认 baseline replay parity 可实现；
- 不跑收益筛选。

输出：

```text
docs/tw_portfolio_decision_model/POLICY_MTR0_CONTRACT_AND_BASELINE_PARITY_FEASIBILITY_EXECUTION_REPORT_CN.md
docs/tw_portfolio_decision_model/POLICY_MTR0_CONTRACT_AND_BASELINE_PARITY_FEASIBILITY_REVIEW_CN.md
data_tw/experiments/policy_mtr_mechanism_transfer/mtr0_contract_and_feasibility/
```

通过条件：

- dependency 合同存在；
- qlib-only 与 qlib+LTR 信号 lineage 清楚；
- baseline parity plan 可审查；
- forbidden action audit clean。

### MTR1 Qlib-only OrderIntent Parity And Mechanism Replay

目标：

- 在 qlib-only 标准信号上生成 OrderIntentArtifact；
- 复现 baseline parity；
- 运行 M1-M6 预声明机制 readonly replay；
- 输出 net after fee/tax、turnover、fee/tax、drawdown、holding overlap。

通过条件：

- M0 baseline parity pass；
- 至少一个机制在 qlib-only 上满足：

```text
net_after_fee_tax >= baseline_net - small_tolerance
turnover materially lower
drawdown not materially worse
cash/no-trade not degenerate
```

若所有机制显著低于 baseline，则关闭 MTR 或仅保留机制诊断。

### MTR2 Qlib+LTR Transfer Replay

目标：

- 迁移 MTR1 通过的机制到 qlib+LTR 标准信号；
- 保持 LTR 语义：LTR 只重排 buy_score，不改 qlib exit boundary；
- readonly replay 对比原 qlib+LTR baseline。

通过条件：

```text
net_after_fee_tax 不显著低于 qlib+LTR baseline
turnover / fee / tax 下降
2022/downturn or risk-off window 若可用则 drawdown 改善
```

### MTR3 Robustness / Window / Regime Attribution

目标：

- 多窗口 robustness；
- regime attribution；
- holdings overlap；
- symbol concentration；
- cost sensitivity；
- no-trade/cash degeneration audit。

通过条件：

- 不是单窗口偶然；
- 不是牺牲收益换低换手；
- 有明确机制解释。

### MTR4 Adapter / Production Readiness Decision

目标：

- 仅当 MTR2/MTR3 明确通过时，讨论是否进入 production readiness；
- 不直接切默认；
- 写 Go/No-Go。

通过条件：

- OrderIntent validator pass；
- ReplayResult validator pass；
- modular regression pass；
- safety boundary clean；
- 用户另行授权。

### MTR5 Closure

目标：

- 若无机制超过 baseline：关闭机制迁移线；
- 若机制有效但未够生产：保留 readonly research candidate；
- 若机制强且稳定：另开 production integration。

## 10. Gate

### 10.1 Return Gate

主指标：

```text
net_total_return_after_fee_tax
```

不得以 gross return 通过。

### 10.2 Cost / Turnover Gate

必须报告：

```text
average_turnover
total_fee
total_tax
buy_count / sell_count
holding_days
replacement count
```

### 10.3 Baseline Preservation Gate

机制不能只靠减少交易让收益大幅下降。

最低要求：

```text
net_after_fee_tax >= baseline_net - tolerance
```

tolerance 必须在 MTR0 冻结，不能后验调整。

### 10.4 Risk Gate

必须报告：

```text
max_drawdown
monthly returns
risk-off regime returns
concentration
cash/no-trade days
```

### 10.5 Leakage Gate

禁止策略输入：

```text
future_return
forward_return
label
next_open
next_close
execution_price
execution_date
realized_pnl
replay_return
target_position
target_weight
```

## 11. Forbidden Actions

全路线禁止：

```text
broker / quick-trade / real order
target_weight / target_position
provider publish
accepted latest switch
frontend default switch
Agent recommendation expansion
monitor scan / config save / alerts write
读取模型私有文件
读取 future/replay returns 作为策略输入
修改生产默认策略
```

## 12. Stop Conditions

必须停止并回报：

- 找不到标准 ModelSignalArtifact；
- baseline parity 无法复现；
- 必须读取模型私有文件才能实现；
- 策略需要 future/replay return 才能判断；
- OrderIntent 合同无法表达机制；
- replay engine 需要被改成读策略私有字段；
- 任何步骤想输出 target_weight/target_position。

## 13. Evidence Requirements

每阶段至少输出：

```text
manifest.json
contract/dependency files
coverage/lineage audit
forbidden action audit
OrderIntent validator report where applicable
ReplayResult validator report where applicable
baseline comparison
turnover/cost audit
holding overlap / rank overlap
execution report
review report
next work doc
```

## 14. First Executor Command

```text
请执行 POLICY_MTR0_CONTRACT_AND_BASELINE_PARITY_FEASIBILITY。

必须读取：
- docs/tw_portfolio_decision_model/POLICY_MTR_MECHANISM_TRANSFER_TO_BASELINE_MAINLINE_CN.md
- docs/tw_portfolio_decision_model/POLICY_JMD2_R_COST_AWARE_TURNOVER_REPAIR_REVIEW_CN.md
- docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md
- docs/tw_modular_contracts/NEW_MODEL_AND_STRATEGY_DEVELOPER_GUIDE_CN.md
- docs/tw_modular_contracts/STRATEGY_RULE_CONTRACT_CN.md
- docs/tw_modular_contracts/STRATEGY_DEPENDENCY_CONTRACT_CN.md
- docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md
- docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md
- docs/tw_modular_contracts/TW_NEW_STRATEGY_ONBOARDING_TEMPLATE_CN.md

只做合同、dependency、lineage、baseline parity feasibility。
不得跑收益筛选，不得接 production/default/frontend/API/Agent/daily/provider/latest。
```

## 15. First Reviewer Brief

```text
请审查 POLICY_MTR0_CONTRACT_AND_BASELINE_PARITY_FEASIBILITY。

重点：
1. 是否机制候选严格来自本 mainline；
2. 是否 StrategyDependency 合同完整；
3. 是否只消费标准 ModelSignalArtifact；
4. 是否 qlib-only / qlib+LTR lineage 清楚；
5. 是否 baseline parity plan 可实现；
6. 是否 forbidden action clean；
7. 是否可进入 MTR1 qlib-only OrderIntent parity/replay。
```

## 16. 参考来源

- Jiang, Xu, Liang, “A Deep Reinforcement Learning Framework for the Financial Portfolio Management Problem,” arXiv:1706.10059
- Liu et al., “FinRL: A Deep Reinforcement Learning Library for Automated Stock Trading in Quantitative Finance,” arXiv:2011.09607
- Wang et al., “AlphaStock: A Buying-Winners-and-Selling-Losers Investment Strategy using Interpretable Deep Reinforcement Attention Networks,” arXiv:1908.02646
- Heaton, Polson, Witte, “Deep Portfolio Theory,” arXiv:1605.07230
- 本项目 JMD2 / JMD2-R 执行与审查报告
