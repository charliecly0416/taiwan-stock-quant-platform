---
created_at: 2026-06-28
status: coordinator_mainline
route: POLICY_JMD_JOINT_MODEL_DECISION_RESEARCH
research_type: joint_model_decision_end_to_end
readonly_only: true
simulation_only: true
production_allowed: false
model_training_authorized_initially: false
strict_test_authorized_initially: false
order_or_target_output_allowed: false
provider_publish_allowed: false
accepted_latest_switch_allowed: false
frontend_default_switch_allowed: false
broker_authorized: false
---

# POLICY_JMD_JOINT_MODEL_DECISION_RESEARCH_MAINLINE_CN

## 1. 统筹结论

可以开一条“模型+决策一体化”研究线，但必须与现有 qlib+LTR 生产链路隔离。

原因：

```text
许多 portfolio RL / deep portfolio / end-to-end trading 论文不是先训练 alpha/ranking 模型，再训练单独 policy；
它们通常把 market representation、组合状态、动作、交易成本和 reward 放进同一个学习闭环。
```

这与本项目当前解耦架构不同：

```text
当前生产链路:
Data / Feature -> qlib/LTR ModelSignalArtifact -> StrategyRule -> OrderIntentArtifact -> ReplayResultArtifact

JMD 研究链路:
PIT Feature / Price Tensor / Optional Score Context / Portfolio State
  -> Joint Model-Decision Policy
  -> simulation-only action / allocation diagnostic
  -> readonly replay / analysis
  -> only if accepted, adapter back to standard contracts
```

因此 JMD 可以研究，但不能绕过项目宪法。内部可模拟 weight/action，外部必须保持 readonly、simulation-only、not order、not target position、not target weight。

## 2. 为什么现有论文部分不适配旧 policy 线

旧 policy 线失败的核心不是“所有论文都错”，而是研究对象不同。

旧线多是在问：

```text
给定 qlib/LTR 已经输出 score/rank，
能否再训练一个二阶 policy 改善买卖决策？
```

很多论文实际在问：

```text
能否端到端学习：从价格/特征/持仓状态到组合动作，使长期组合 reward 最大化？
```

这意味着：

- 论文中的 model layer 和 decision layer 经常是合并的；
- reward 往往直接是 portfolio value / Sharpe / risk-adjusted return；
- state 包括 price tensor、previous portfolio、cash、holding、market context；
- action 可能是 portfolio vector、buy/sell/hold、continuous allocation 或 asset-selection set；
- training 和 evaluation 是 portfolio trajectory 级别，而不是先看 prediction IC 再看 policy。

所以 JMD 的意义是：

```text
不要继续在“强 qlib/LTR score 之后”学习弱二阶 policy；
而是重新定义一个端到端 joint model，让模型直接面对组合收益目标。
```

## 3. 与本项目的适配判断

### 3.1 适配点

JMD 与本项目适配的部分：

- 项目已有价格、特征、模型信号、回放、费用税费、portfolio state 的基础；
- 现有失败 taxonomy 已明确 cost drag、concentration、cash/no-trade、fold instability 是主要风险；
- 台湾 150 支股票 universe 规模适合先做小型端到端实验；
- 2022 downturn 可作为 risk-control diagnostic；
- qlib-only / raw feature lineage 可避免 qlib+LTR 训练集复用争议；
- 可把 qlib score/rank 作为 optional context，而不是唯一输入。

### 3.2 不适配点

JMD 与本项目冲突的部分：

- 当前生产合同禁止 `target_weight` / `target_position` / quantity instruction；
- EIIE / Deep Portfolio 类方法天然输出 allocation vector；
- FinRL 类环境可做 live trading 接口，但本项目禁止 broker/order；
- 台湾日频数据样本少于论文常见高频/多市场环境；
- 既有 PAL EIIE 尝试已出现 high cost / concentration / cash degeneration / seed instability；
- 如果只喂 qlib+LTR score，会退化为旧 policy overlay 问题。

### 3.3 适配结论

可以适配，但必须采用以下约束：

```text
1. 先 qlib-only/raw-feature lineage，不直接使用 2023-2025 LTR 训练产物做训练输入。
2. 先做 paper implementation audit 和 data lineage，而不是直接训练。
3. 内部允许 simulation-only allocation/action diagnostic。
4. 外部不得输出 production target_weight/target_position。
5. 任何候选若要进入现有系统，必须先转换为 ModelSignalArtifact extension 或 OrderIntentArtifact。
6. 不允许把论文发表结果当作本项目必然提升证据。
7. 不允许为了复现论文而复现论文；每个机制必须先通过本项目 suitability / expected-edge gate。
```

## 3.4 Suitability / Expected-edge Gate

JMD 的第一原则不是“论文有发表就值得训练”，而是：

```text
论文机制必须能解释它在本项目中可能获得什么新增信息或优化自由度。
```

每个候选机制在进入训练前必须回答：

1. 它相对现有 qlib/LTR + baseline policy 增加了什么信息？
2. 它相对旧 PAL/PBA/PRL 失败路线改变了什么关键假设？
3. 它是否只是把 qlib/LTR score 再喂给另一个模型？
4. 它是否需要我们没有的数据频率、流动性字段、盘口、做空或真实成交？
5. 它的 action space 是否会导致高 turnover、高集中、cash/no-trade 或 target_weight 合同冲突？
6. 它的 reward 是否能在 net after fee/tax 上优化，而不是 gross-only？
7. 它的样本量是否足以支撑训练，还是更适合先做轻量 supervised baseline？
8. 它失败时能否输出有用诊断，而不是只得到一个黑盒低收益模型？

若回答不能形成明确正向先验，必须：

```text
NO_GO_DO_NOT_TRAIN
```

这不是保守，而是避免重复旧路线的主要失败模式：

- 论文机制与台湾日频股票不匹配；
- action space 过宽导致成本/集中；
- 约束过强后退化为 cash/no-trade；
- 样本不足导致 seed instability；
- 强 baseline 已吃掉大部分 ranking alpha；
- 模型只学到 baseline clone。

## 4. 参考论文与采用方式

### P1 EIIE / PVM / OSBL

论文：Jiang, Xu, Liang, “A Deep Reinforcement Learning Framework for the Financial Portfolio Management Problem,” 2017.

核心机制：

- EIIE topology；
- Portfolio-Vector Memory；
- Online Stochastic Batch Learning；
- state 是多资产价格张量；
- action 是 portfolio weight vector；
- reward 是交易成本后的组合价值变化。

本项目可采用：

- price / feature tensor；
- previous portfolio memory；
- transaction-cost-aware reward；
- CNN/RNN/LSTM 轻量对照；
- portfolio trajectory 级回放。

本项目不直接采用：

- crypto 30-minute 高频设定；
- 直接输出 target_weight 到生产；
- OSBL 在线更新进 production。

风险：

- PAL2 已证明 naive EIIE 在本项目容易高成本、高集中、seed instability；
- 因此 JMD 不能简单重跑 EIIE，必须先做 contract、cost、concentration、seed gate。

JMD0 suitability 要求：

- 证明新的 EIIE 方案与 PAL2/PAL2-R 不同；
- 明确是否引入 previous portfolio memory、cost-aware reward、concentration penalty、cash cap；
- 若只是重跑 PAL2 或扩大训练时间，必须判定为 `NO_GO_DO_NOT_TRAIN`。

### P2 FinRL

论文：Liu et al., “FinRL: A Deep Reinforcement Learning Library for Automated Stock Trading in Quantitative Finance,” 2020.

核心机制：

- data layer / environment layer / agent layer；
- 支持 DQN/DDPG/PPO/SAC/A2C/TD3；
- market environment 中包含现金、持仓、交易成本、风险偏好；
- 标准 backtesting 和 baseline 对比。

本项目可采用：

- env-agent-backtest 分层；
- gym-like readonly simulation environment；
- transaction cost、cash、holding、risk controls；
- PPO/A2C/DDPG/SAC 作为可替换 agent family；
- standardized baseline comparison。

本项目不采用：

- live trading；
- broker/order API；
- provider publish；
- 把 FinRL 默认环境直接改成生产环境。

风险：

- DRL 样本效率低；
- 多算法调参空间大；
- 容易过拟合 validation；
- 必须多 seed、walk-forward、no strict-test tuning。

JMD0 suitability 要求：

- 不得照搬 FinRL 默认环境；
- 必须先定义本项目 deterministic readonly environment；
- 必须说明为何 PPO/A2C/DDPG 比 supervised utility baseline 更适合；
- 若只是因为 FinRL 有现成库而训练，必须判定为 `NO_GO_DO_NOT_TRAIN`。

### P3 AlphaStock

论文：Wang et al., “AlphaStock: A Buying-Winners-and-Selling-Losers Investment Strategy using Interpretable Deep Reinforcement Attention Networks,” 2019.

核心机制：

- attention 学习资产间关系；
- RL objective 偏向 Sharpe / risk-return；
- 关注 winner selection 与 loser selling；
- 强调可解释性。

本项目可采用：

- cross-asset attention；
- winner/loser selection 与 sell-side deterioration；
- attention attribution 作为审查 artifact；
- risk-return balanced reward。

本项目不采用：

- 直接把 attention score 当 production buy list；
- 未经 OrderIntent 合同的买卖动作；
- 未经 OOS 的解释性叙事。

风险：

- attention 不等于因果解释；
- 小样本下 relation learning 容易不稳定；
- 必须有 attribution stability audit。

JMD0 suitability 要求：

- 必须证明 cross-asset relation 在 150 支台湾股票 universe 有可用输入；
- 必须定义 attention attribution audit；
- 若无法解释 attention 如何转化为稳定 action edge，不能进入训练。

### P4 Deep Portfolio Theory

论文：Heaton, Polson, Witte, “Deep Portfolio Theory,” 2016.

核心机制：

- encode / calibrate / validate / verify；
- 用深度组合结构做 portfolio selection；
- 强调 cross-validation 和 efficient frontier。

本项目可采用：

- 把 JMD 切成 encode/calibrate/validate/verify；
- 用 cross-validation / walk-forward 约束；
- 用 efficient frontier / risk-return tradeoff 做最终呈现。

本项目不采用：

- 只做静态 portfolio selection 后直接 production；
- 不考虑交易成本的 frontier。

JMD0 suitability 要求：

- 只能采用 encode/calibrate/validate/verify 的实验组织方式；
- 不得把 deep portfolio theory 当作某个必须复现的模型；
- 如果不能落成具体可审计 artifact，则仅作为方法论参考。

### P5 DeepTrader / Risk-aware DRL / Relation-aware RL

相关研究方向包括 risk-return balanced portfolio management、relation-aware DRL、adversarial / robust portfolio RL。

本项目可采用：

- risk-aware reward；
- drawdown penalty；
- turnover penalty；
- concentration penalty；
- market regime conditioning；
- adversarial/noisy validation diagnostic。

本项目不初期采用：

- 复杂多 agent；
- online adversarial training；
- 过大模型；
- GPU-heavy transformer-first 路线。

JMD0 suitability 要求：

- risk-aware 机制必须对应本项目已观测失败模式，例如 2022 drawdown、turnover、concentration；
- 如果只是增加 reward penalty 但没有可解释的机制假设，不能进入训练。

## 5. 数据切分与 lineage

JMD 必须重新冻结数据切分，不能直接沿用 qlib+LTR 的训练/测试叙事。

建议初始路线：

```text
JMD train: 2015-01-01..2020-12-31
JMD validation: 2021-01-01..2021-12-31
JMD downturn diagnostic: 2022-01-01..2022-12-31
JMD candidate test: 2023-01-01..2025-06-30
JMD strict test: 初始不授权，需 JMD closure 后另开
```

解释：

- train/valid/test 必须以 JMD 自己的模型训练为准；
- 2022 可用于 downturn diagnostic，不当 strict OOS；
- 2023-2025 若使用 LTR 训练产物则会污染，因此第一轮应 qlib-only/raw-feature；
- 若后续要使用 qlib+LTR context，必须另开 lineage audit。

## 6. 输入设计

### 6.1 最小输入

第一版 JMD 不直接使用 LTR，建议输入：

```text
price features:
  open/high/low/close/volume/return/MA/volatility

market features:
  TWII return/MA/drawdown/volatility/regime

cross-sectional features:
  rank/percentile/relative momentum/relative volatility

portfolio state:
  holding flag/cash flag/previous action/holding age

optional qlib context:
  frozen qlib score/rank only if lineage permits
```

### 6.2 不允许输入

禁止：

```text
future_return_*
forward_return_*
label_*
realized_pnl
replay_return
execution_price as state
next_open / next_close as decision input
broker/order fields
target_position from previous experiments
2023-2025 LTR training labels or private scores
```

## 7. 动作空间设计

JMD 可分三种动作空间，由低到高。

### A. Asset Selection Action

输出：

```text
daily top-k buy candidates / sell candidates / no-trade
```

优点：

- 容易转换成 OrderIntentArtifact；
- 与现有回放合同兼容；
- 风险低。

缺点：

- 不完全复现 EIIE/portfolio allocation 论文；
- 可能仍接近旧 policy overlay。

建议：

```text
JMD 初期用作 supervised utility baseline。
```

### B. Discrete Portfolio Action

输出：

```text
hold / buy_one / sell_one / buy_k / sell_k / rebalance_light
```

优点：

- 更接近实际策略动作；
- 可控成本；
- 可转换 OrderIntent。

缺点：

- action abstraction 仍可能丢失 allocation 论文核心。

建议：

```text
JMD1/JMD2 可采用。
```

### C. Continuous Allocation Diagnostic

输出：

```text
allocation_weight_diagnostic
rebalance_delta_diagnostic
cash_weight_diagnostic
```

优点：

- 真正适配 EIIE / FinRL portfolio allocation；
- 可直接优化 portfolio reward。

缺点：

- 与 production contract 冲突；
- 容易被误读为 target_weight；
- 旧 PAL 已证明风险高。

建议：

```text
只允许 simulation-only AllocationDiagnosticArtifact；
不得进入 OrderIntent / production / frontend default / broker。
```

## 8. Reward 设计

JMD reward 必须是 cost-aware，不接受 gross-only。

候选 reward：

```text
R0: daily net portfolio return after fee/tax
R1: log portfolio value change after fee/tax
R2: net return - lambda_turnover * turnover - lambda_concentration * concentration
R3: Sharpe-like rolling risk-adjusted reward
R4: drawdown-penalized reward
```

初始建议：

```text
JMD1 使用 supervised utility / imitation-style objective；
JMD2 使用 R1 + turnover/concentration penalty；
JMD3 才比较 risk-adjusted reward。
```

禁止：

- 用 validation/test PnL 调 reward；
- gross reward 通过但 net reward 失败仍宣称通过；
- all-cash/no-trade 因低回撤通过。

## 9. 模型架构优先级

### Tier 1: 可控 baseline

优先实现：

- linear / shallow MLP utility model；
- temporal CNN over price/feature window；
- EIIE-style compact CNN；
- supervised action-value / utility ranking。

原因：

- CPU 可跑；
- 容易解释；
- 可做 ablation；
- 能判断 joint input 是否有增量。

### Tier 2: Paper-aligned RL

之后实现：

- PPO discrete / allocation-lite；
- A2C；
- DDPG/SAC continuous allocation diagnostic；
- EIIE CNN/RNN/LSTM with PVM。

### Tier 3: 暂缓

暂缓：

- transformer-first；
- multi-agent；
- adversarial RL；
- online learning；
- full FinRL production pipeline。

## 10. 合同适配

JMD 需要新增研究 artifact，但不得修改生产合同默认语义。

### 10.1 JointPolicyArtifact

记录训练产物：

```text
data_tw/artifacts/joint_model_decision/{model_name}/{run_id}/
```

必需：

- `manifest.json`
- `training_config.json`
- `feature_lineage.json`
- `split_lineage.json`
- `model_card.md`
- `forbidden_field_audit.csv`
- `seed_stability_report.csv`

### 10.2 JointDecisionDiagnosticArtifact

记录模型输出动作诊断：

- asset selection action；
- discrete action；
- allocation diagnostic。

必须包含：

```text
simulation_only=true
readonly_research_only=true
not_order=true
not_target_position=true
not_target_weight=true
production_allowed=false
```

### 10.3 外部适配

若候选通过，才允许另开 adapter：

```text
JointDecisionDiagnosticArtifact -> OrderIntentArtifact
```

这个 adapter 必须：

- 丢弃 continuous weight，只保留 buy/sell/hold intent；
- 不输出 quantity；
- 不输出 target position；
- 不输出 target weight；
- 通过 OrderIntent validator。

## 11. Phase Plan

### JMD0 Paper Adaptation And Feasibility Contract

目标：

- 阅读并审计论文机制；
- 审计旧 PAL/PBA 失败；
- 冻结数据切分；
- 冻结允许/禁止的 action/reward/artifact；
- 对每个论文机制执行 suitability / expected-edge gate；
- 判断是否可进入 JMD1。

输出：

- `POLICY_JMD0_PAPER_ADAPTATION_AND_FEASIBILITY_CONTRACT_EXECUTION_REPORT_CN.md`
- `POLICY_JMD0_PAPER_ADAPTATION_AND_FEASIBILITY_CONTRACT_REVIEW_CN.md`
- paper adaptation matrix；
- data lineage feasibility；
- contract gap list。

通过条件：

- 至少明确 2 个可实现模型方案；
- 每个方案必须有 expected-edge hypothesis；
- 每个方案必须说明为什么不会重复旧 PAL/PBA/PRL 的失败模式；
- 明确为什么不是重跑旧 PAL；
- 明确数据切分和 leakage policy；
- 明确 simulation-only artifact 边界。

### JMD1 Joint Dataset And Environment Contract

目标：

- 构造 JMD dataset schema；
- 构造 gym-like readonly environment contract；
- 冻结 observation/action/reward；
- 不训练。

输出：

- state tensor schema；
- action space schema；
- reward spec；
- fee/tax/concentration/cash audit；
- environment deterministic replay smoke；
- JMD1 execution/review。

通过条件：

- 可以 deterministically replay baseline；
- no future leakage；
- no production fields；
- CPU smoke 可运行。

### JMD2 Supervised Joint Utility Baseline

目标：

先训练一个轻量 supervised / imitation / utility baseline，判断 joint raw feature 是否有增量。

允许：

- linear / MLP / temporal CNN；
- qlib-only/raw features；
- train/valid split；
- no strict test。

禁止：

- RL；
- LTR 训练产物；
- strict test；
- production adapter。

通过条件：

- validation after fee/tax 超过 baseline 或明确显示机制；
- fold stability 不崩；
- participation 不过低；
- 不是 baseline clone。

### JMD3 Paper-aligned EIIE / FinRL Simulation Prototype

目标：

实现小型 paper-aligned prototype：

- EIIE compact CNN + PVM；
- 或 FinRL-style PPO/A2C env；
- transaction-cost-aware reward；
- multi-seed。

通过条件：

- net after fee/tax；
- turnover/concentration/cash gates；
- seed stability；
- no strict test tuning。

### JMD4 Robustness / Walk-forward / Stress Diagnostic

目标：

对 JMD2/JMD3 候选做：

- 2021 sanity；
- 2022 downturn diagnostic；
- 2023-2025 candidate OOS if lineage clean；
- cost sensitivity；
- market regime attribution；
- action attribution；
- no-trade/cash degeneration audit。

通过条件：

- 不是单一窗口；
- 不是 all-cash；
- 不是 high-turnover gross-only；
- 不是 concentration artifact；
- 与 baseline 比较 after fee/tax。

### JMD5 Adapter Feasibility

目标：

若 JMD 候选通过，研究如何落到现有系统：

```text
JointDecisionDiagnosticArtifact -> OrderIntentArtifact
```

不允许直接 production。

通过条件：

- 可转换为 buy/sell/hold intent；
- 不含 target weight/position；
- replay engine strategy-agnostic；
- validators pass。

### JMD6 Closure

目标：

- 无候选：关闭 JMD；
- 有 research candidate：保留为 readonly research；
- 足够强：另开 qlib+LTR / production adaptation design；
- 不直接上线。

## 12. Gate

### 12.1 Return Gate

必须以 net after fee/tax 为主。

建议：

```text
收益增强候选：
validation net_return_after_fee_tax > baseline + material margin
且 drawdown 不显著恶化

防守候选：
收益不低太多
drawdown 显著改善
cash/no-trade 不是主因
```

具体 material margin 在 JMD0/JMD1 冻结，执行者不得后验更改。

### 12.2 Stability Gate

必须报告：

- seed mean/std；
- train/valid direction；
- rolling fold；
- action change rate；
- baseline clone audit。

### 12.3 Cost / Turnover Gate

必须报告：

- gross vs net；
- fee；
- tax；
- turnover；
- concentration；
- cash rate；
- no-trade days。

### 12.4 Leakage Gate

必须审计：

- future return / label；
- execution price；
- next_open/next_close；
- realized PnL；
- LTR training labels；
- same-day unavailable fields。

## 13. Executor Rules

执行者必须：

- 每阶段只执行指定 work doc；
- 先写/读合同再实现；
- 保留 artifact manifest；
- 报告 data split；
- 报告 no production boundary；
- 报告 seeds；
- 报告失败模式。

执行者不得：

- 直接重跑 PAL2 当作 JMD；
- 直接接 FinRL live trading；
- 输出 target_weight / target_position；
- 用 strict test 调参；
- 使用 2023-2025 LTR training artifact 训练 JMD；
- 修改 production default。

## 14. Reviewer Rules

审查者必须：

- 审论文机制是否真的被采用；
- 审是否与旧失败路线不同；
- 审数据切分；
- 审 cost/cash/concentration；
- 审 seed stability；
- 审 forbidden actions；
- 写下一阶段 work doc。

审查者不得：

- 因为论文发表就默认会提升；
- 接受 gross-only；
- 接受 all-cash/no-trade；
- 接受 target_weight 进入生产合同；
- 接受 strict test 反复调参。

## 15. First Executor Command

```text
请执行 POLICY_JMD0_PAPER_ADAPTATION_AND_FEASIBILITY_CONTRACT。

必须读取：
- docs/tw_portfolio_decision_model/POLICY_JMD_JOINT_MODEL_DECISION_RESEARCH_MAINLINE_CN.md
- docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md
- docs/tw_modular_contracts/NEW_MODEL_AND_STRATEGY_DEVELOPER_GUIDE_CN.md
- docs/tw_modular_contracts/MODEL_SIGNAL_CONTRACT_CN.md
- docs/tw_modular_contracts/MODEL_SIGNAL_EXTENSION_SCHEMA_CN.md
- docs/tw_modular_contracts/STRATEGY_RULE_CONTRACT_CN.md
- docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md
- docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md
- docs/tw_portfolio_decision_model/POLICY_PAL_PAPER_ALIGNED_PORTFOLIO_ALLOCATION_RL_MAINLINE_CN.md
- docs/tw_portfolio_decision_model/POLICY_MODEL_RESEARCH_ROUTE_CLOSURE_EXECUTION_REPORT_CN.md
- docs/tw_portfolio_decision_model/POLICY_RAL_POLICY_RESEARCH_EXTERNAL_CLOSURE_EXECUTION_REPORT_CN.md

只做论文适配、数据 lineage 和合同可行性；不得训练，不得 replay 收益，不得生产接入。
```

## 16. First Reviewer Brief

```text
请审查 POLICY_JMD0_PAPER_ADAPTATION_AND_FEASIBILITY_CONTRACT。

重点：
1. 是否真实阅读并映射 EIIE / FinRL / AlphaStock / Deep Portfolio 等论文机制；
2. 是否解释为什么旧 PAL/PBA 失败不等于 JMD 不可做；
3. 是否冻结 train/valid/diagnostic/test lineage；
4. 是否明确 simulation-only artifact；
5. 是否禁止 target_weight/target_position/order 进入生产；
6. 是否可以进入 JMD1 dataset/env contract。
```

## 17. 参考来源

- Jiang, Xu, Liang, “A Deep Reinforcement Learning Framework for the Financial Portfolio Management Problem,” arXiv:1706.10059, https://arxiv.org/abs/1706.10059
- Liu et al., “FinRL: A Deep Reinforcement Learning Library for Automated Stock Trading in Quantitative Finance,” arXiv:2011.09607, https://arxiv.org/abs/2011.09607
- Wang et al., “AlphaStock: A Buying-Winners-and-Selling-Losers Investment Strategy using Interpretable Deep Reinforcement Attention Networks,” arXiv:1908.02646, https://arxiv.org/abs/1908.02646
- Heaton, Polson, Witte, “Deep Portfolio Theory,” arXiv:1605.07230, https://arxiv.org/abs/1605.07230
- Sutton and Barto, “Reinforcement Learning: An Introduction,” second edition, http://incompleteideas.net/book/the-book-2nd.html
- Schulman et al., “Proximal Policy Optimization Algorithms,” arXiv:1707.06347, https://arxiv.org/abs/1707.06347
- Lillicrap et al., “Continuous Control with Deep Reinforcement Learning,” arXiv:1509.02971, https://arxiv.org/abs/1509.02971
