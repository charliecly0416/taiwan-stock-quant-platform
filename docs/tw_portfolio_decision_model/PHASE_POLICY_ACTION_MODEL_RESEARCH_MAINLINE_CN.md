---
created_at: 2026-06-21
status: coordinator_mainline_policy_action_model_research_v1
scope: policy_action_model_research_after_phase_p_closure
previous_route_closure: docs/tw_portfolio_decision_model/PHASEP_BRANCH_B_CLOSURE_REVIEW_CN.md
base_signal_first: frozen_qlib_2018_2022
base_signal_first_reason: qlib_train_2018_2022_and_2023_2026_signal_is_oos
policy_train_valid_test_required: true
readonly_only: true
simulation_only: true
not_order: true
not_target_position: true
not_investment_advice: true
production_allowed: false
---

# Policy / Action Model Research 主线：从 qlib-only 动作价值模型到后续 RL

## 1. 统筹结论

`portfolio_decision_optimizer_v1` 规则型 P 分支已经关闭：

```text
closure_review = docs/tw_portfolio_decision_model/PHASEP_BRANCH_B_CLOSURE_REVIEW_CN.md
closure_decision = PASS_BRANCH_B_CLOSED_AS_READONLY_RESEARCH
```

旧 P 分支的结论是：规则型 action layer 可以降低换手、费用和回撤，但收益捕获能力显著弱于 baseline。它只能保留为：

```text
readonly research artifact
人工复盘辅助层
组合动作审计层
解释层
失败机制样本
```

不得把旧 candidate 用作：

```text
默认策略
自动交易策略
监督训练标签
P5 入口
B-R LTR coverage repair 入口
qlib-only 机制修复入口
```

新的研究方向应另开主线：

```text
Policy / Action Model Research
```

核心目标不是继续修旧规则，而是学习“在已有 ranking signal 与组合状态下，某个动作是否值得执行”。第一阶段先不重训 qlib/LTR，只使用已有 `frozen_qlib_2018_2022` 标准 `ModelSignalArtifact`，因为：

```text
qlib train window = 2018-2022
policy research signal window = 2023-2026H1
因此 2023-2026H1 对 qlib signal 层是 OOS
```

但必须注意：

```text
可以不重新训练 qlib/LTR；
但 policy/action model 自身必须做 train / validation / test 或 walk-forward OOS。
```

## 2. 研究问题

本主线要回答的问题是：

```text
在 frozen qlib signal、当前持仓状态、市场状态和成本约束下，
一个动作 buy / sell / hold / skip 是否能提高扣费税后的组合净收益率，并在可接受约束内控制成本和风险？
```

### 2.1 Return-first 原则

本主线的目标函数必须明确为 return-first：

```text
primary objective = maximize net_return_after_fee_tax
secondary constraints = turnover / fee / drawdown / concentration / action stability
```

也就是说，风险控制、换手控制和费用控制是约束与惩罚项，不是替代目标。新 policy 不能重走旧 P 分支路线：

```text
低换手但低收益，不算成功。
低回撤但几乎不参与市场，不算成功。
费用很低但错失主要上涨，不算成功。
只提高 risk-adjusted utility 但净收益显著低于 baseline，默认不推进。
```

PA1/PA2/PA3 的继续推进条件必须优先看：

```text
1. test net_return_after_fee_tax 是否接近或超过 baseline。
2. validation 上的收益优势是否不是单窗口偶然。
3. 若净收益略低于 baseline，是否有非常明确且统筹接受的风险/回撤改善 tradeoff。
4. 不能只凭 turnover、fee、drawdown 改善推进。
```

第一阶段不做连续仓位分配，不输出目标权重，不输出数量，不接 broker/order。

更具体地说，第一阶段只研究：

```text
1. 是否执行 baseline 候选动作。
2. 是否过滤某个 buy。
3. 是否过滤或延后某个 sell。
4. 是否在可控约束下生成 buy/sell/hold/skip intent。
```

这比直接做完整 portfolio allocation 或在线 RL 更稳健，也更贴合现有合同链路。

## 3. 参考研究、采用矩阵与落地方式

本主线必须参考已有研究，但不能把论文结果当作本项目收益承诺。执行者在 PA0 必须把下列研究逐项核查，并在报告中说明采用/不采用的原因。

### 3.1 核心参考文献与项目

| 编号 | 研究 / 项目 | 链接 | 核心方案 | 本项目采用 | 本项目不采用 |
|---|---|---|---|---|---|
| R1 | FinRL: A Deep Reinforcement Learning Library for Automated Stock Trading in Quantitative Finance | https://arxiv.org/abs/2011.09607 | 分层金融 DRL 工程框架，包含 market environment、agent、transaction cost、risk-aversion、backtesting 与 baseline 比较 | 采用其“数据层 / 环境层 / agent 层 / 回测分析层分离”的工程思想；PA0 设计 artifact 与 validator 时参考其模块化边界 | 不采用其直接训练 DRL agent 并进入交易环境的生产假设；不接 broker，不做 online trading |
| R2 | A Deep Reinforcement Learning Framework for the Financial Portfolio Management Problem / EIIE | https://arxiv.org/abs/1706.10059 | EIIE topology、Portfolio-Vector Memory、Online Stochastic Batch Learning、显式 reward，用于 portfolio allocation | 采用其 state 包含 portfolio context、reward 显式扣交易成本、历史组合状态可进入模型的思想 | 第一阶段不采用连续 portfolio weight，不采用 target_weight，不采用 OSBL 在线更新，不做 crypto 30min 高频假设 |
| R3 | Moody & Saffell, Recurrent Reinforcement Learning for Trading | 经典 RRL trading work | 直接优化带交易成本的交易目标，强调 transaction cost 对交易策略的影响 | 采用“reward/utility 必须 cost-aware”的原则，PA1 reward ablation 必须包含 turnover/cost penalty | 不采用黑箱直接优化最终收益后回写策略规则；不允许同窗收益倒调 |
| R4 | LinUCB / contextual bandit: A Contextual-Bandit Approach to Personalized News Article Recommendation | https://arxiv.org/abs/1003.0146 | 给定 context 选择 action，并用离线日志评估 bandit policy | 采用“先做小 action space 的 contextual decision”思想；PA2 用 allow/block 或 buy/sell/hold/skip 的离散 action | 不采用在线探索真实市场反馈；不把未随机化的 replay 日志直接当无偏 bandit 反馈 |
| R5 | Conservative Q-Learning for Offline Reinforcement Learning, CQL | https://arxiv.org/abs/2006.04779 | offline RL 中对 OOD action 估值保守，降低分布外动作过估计 | PA3 若启动，优先参考 CQL 的 conservative value 约束和 OOD action audit | PA0-PA2 不启动 CQL；不允许 policy 输出历史数据中覆盖不足的激进行动 |
| R6 | Offline Reinforcement Learning with Implicit Q-Learning, IQL | https://arxiv.org/abs/2110.06169 | 避免显式评估数据集外 action，通过 expectile value 与 advantage-weighted BC 做 offline policy improvement | PA3 可参考 IQL 的“尽量不查询 OOD action”的思想，适合历史日志覆盖不足场景 | PA1/PA2 不使用；不把 IQL 结果作为生产策略，必须 readonly replay |
| R7 | Batch-Constrained / Behavior-Constrained offline RL, BCQ family | https://arxiv.org/abs/1812.02900 | 约束 policy 接近 behavior data，降低 offline RL 的 extrapolation error | PA3 可作为 CQL/IQL 的对照 baseline，用于 OOD action 风险控制 | 不在 PA0/PA1 直接采用；不允许扩展到未覆盖动作空间 |
| R8 | Decision Transformer: Reinforcement Learning via Sequence Modeling | https://arxiv.org/abs/2106.01345 | 把 offline RL 表述为条件序列建模，用 past states/actions/returns-to-go 生成 action | 仅作为 PA3+ 的 diagnostic 方向，用于数据量足够后的序列模型对照 | 第一阶段不采用；returns-to-go 容易造成误用，必须有严格 leakage audit |
| R9 | DeepPocket: Deep Graph Convolutional Reinforcement Learning for Financial Portfolio Management | https://arxiv.org/abs/2105.08664 | 用图结构表达资产相关性，actor-critic 学习 portfolio policy | PA4/后续可参考“标的相关性/产业链/图关系”作为 state extension | 第一阶段不采用图网络或 actor-critic；不输出 portfolio reallocation weight |
| R10 | Risk-sensitive / drawdown-aware / cost-aware trading literature | 多篇风险敏感 RL 与 cost-aware trading 工作 | 把交易成本、波动、回撤、CVaR 等放进 reward 或 evaluation | PA1 起必须做 reward ablation：return only、return-cost、return-cost-drawdown | 不允许只报告低回撤而忽略收益捕获；不把 risk penalty 权重按 test 倒调 |

### 3.2 为什么不是直接 RL

现有研究说明 RL / DRL 可以用于金融交易和组合管理，但本项目不能直接跳到 RL，原因是：

```text
1. 旧 P 分支失败模式是过度保守和参与度过低，直接 RL 可能复现“少交易低回撤但低收益”。
2. Offline RL 对 behavior policy 覆盖很敏感；我们的历史动作主要来自 baseline/replay，不是真实随机探索日志。
3. 直接 portfolio allocation 类方法通常输出连续权重，和本项目 OrderIntent 合同冲突。
4. qlib+LTR 存在训练窗口和 OOS 边界问题，先 qlib-only 更干净。
5. PA0 还没有定义 PolicyTrainingDatasetArtifact、PolicyDecisionArtifact、validator 和 golden samples。
```

因此本主线采用的落地顺序是：

```text
supervised utility model -> contextual bandit -> offline RL -> qlib+LTR adapter
```

### 3.3 研究方案到 PA 阶段的映射

| PA 阶段 | 主要参考 | 采用内容 | 关键实验 | 审查重点 |
|---|---|---|---|---|
| PA0 | FinRL、ModelSignal/OrderIntent 合同、LinUCB offline evaluation 思路 | 先定义 dataset / decision / evaluation artifact；固定 split；设计 leakage audit | 不训练，只产出 artifact schema、split、state/action/reward、validator/golden sample 设计 | 是否防止 future/replay leakage；是否只用 frozen qlib；是否没有直接 RL |
| PA1 | Moody & Saffell cost-aware objective、risk-sensitive utility、监督学习 baseline | 用 supervised model 预测 action utility 或 allow/block；做 reward ablation | Logistic Regression / LightGBM / small MLP；R0/R1/R2 reward ablation；validation 选阈值，test 一次评估 | 是否比旧 P 分支更高参与度；是否避免收益大幅劣化；是否没有 test 倒调 |
| PA2 | LinUCB / Thompson Sampling contextual bandit | 把每个候选动作作为 contextual decision；学习 allow/block 或 buy/sell/hold/skip | LinUCB、Thompson、IPS/DR evaluation only if behavior policy 可定义 | offline bandit 评估是否合理；是否承认非随机日志偏差 |
| PA3 | CQL、IQL、BCQ、Decision Transformer | 仅在 PA1/PA2 有价值后研究 offline RL；重点控制 OOD action | CQL/IQL/BCQ 对照；OOD action audit；behavior policy coverage audit | 是否 action coverage 足够；是否没有在线 RL；是否不输出仓位/订单 |
| PA4 | EIIE、DeepPocket、LTR rerank research | 适配 qlib+LTR 或加入图/相关性 state extension | 只在 qlib-only 证明有效后做 LTR adapter；必要时重新规划 qlib/LTR/action OOS | 是否把 2023-2025 LTR training window 误写为 strict OOS |
| PA5 | FinRL backtesting separation、本项目 ReplayResultContract | 合同化 readonly integration | PolicyDecision -> StrategyRule -> OrderIntent -> ReplayResult | 是否 production_allowed=false；是否 no default/no publish/no order |

### 3.4 本项目明确采用的设计决策

从上述研究中，本项目明确采用：

```text
1. 模块分层：dataset / policy / decision artifact / strategy adapter / replay 分离。
2. Cost-aware utility：reward/label 必须扣交易成本或显式做 cost ablation。
3. Risk-aware evaluation：不只看 return，也看 drawdown、turnover、PnL concentration、regime stability。
4. 小动作空间：先 allow/block baseline action，再扩展 buy/sell/hold/skip。
5. Offline-first：所有训练与评估只用历史数据，先 readonly replay，不接真实交易。
6. OOD action 审计：PA3 若做 offline RL，必须衡量 action coverage 和 policy 是否偏离 behavior data。
7. qlib-only first：先用 frozen_qlib_2018_2022，避免 LTR 训练窗口争议。
```

### 3.5 本项目明确不采用的设计决策

从上述研究中，本项目明确不采用：

```text
1. 不直接输出 portfolio target_weight / target_position。
2. 不做 online RL 或真实市场探索。
3. 不使用 test replay 结果调 reward、阈值或 action space。
4. 不把旧 portfolio_decision_optimizer_v1 的动作当监督标签。
5. 不把低回撤本身当策略成功，必须同时检查收益捕获和参与度。
6. 不把 2023-2025 LTR training-window replay 当 strict OOS。
7. 不把论文或开源框架结果当成本项目收益承诺。
```

### 3.6 PA0 执行者必须补充的研究阅读清单

PA0 执行报告必须新增一节：

```text
Research Adoption Audit
```

逐项回答：

```text
1. FinRL 的 environment/agent/backtest 分层，映射到本项目哪些 artifact？
2. EIIE/PVM 中哪些 portfolio-state 概念可作为 state feature，哪些因 target_weight 禁止不用？
3. LinUCB/contextual bandit 的 offline evaluation 需要什么日志假设，本项目是否满足？
4. CQL/IQL/BCQ 各自解决什么 offline RL 风险，为什么 PA3 才允许？
5. Decision Transformer 为什么只作为 PA3+ diagnostic，不作为第一版？
6. DeepPocket 的图关系是否可作为 PA4 state extension，而不是 PA1 必需项？
7. cost-aware / risk-aware reward 如何落到 R0/R1/R2 ablation？
```

PA0 审查者必须确认执行者不是只列论文名，而是完成：

```text
adopted / rejected / deferred / risk / PA_mapping
```

五列判断。

## 4. 总体路线

本主线按从小到大推进：

```text
PA0: Contract / dataset / evaluation design freeze
PA1: qlib-only supervised utility model
PA2: qlib-only contextual bandit policy
PA3: qlib-only offline RL research
PA4: qlib+orthogonal LTR adapter research, only after PA1/PA2/PA3 evidence
PA5: readonly integration review, not production default
```

推荐先做 PA0-PA1，不直接进入 RL。

原因：

```text
1. supervised utility model 最容易审查标签、PIT、OOS 和 baseline 对比。
2. contextual bandit 比 offline RL 更容易控制 action space 和 OOD 风险。
3. offline RL 对数据量、行为策略覆盖和 reward 设计更敏感，必须后置。
4. qlib+LTR 适配要等 qlib-only 证明动作模型有价值后再做。
```

## 5. 数据与切分原则

### 5.1 第一阶段固定输入

第一阶段只使用：

```text
signal_artifact = data_tw/artifacts/signals/frozen_qlib_2018_2022/r1_legacy_signal_adapter_20260616/manifest.json
model_family = qlib
qlib_train_window = 2018-2022
policy_research_window = 2023-01-03 到 2026-05-07
```

不得在 PA0-PA2 中做：

```text
重训 qlib
重训 LTR
修 2023-2025 LTR artifact
把 2023-2025 LTR training window 当 OOS
读取 qlib/LTR 私有 CSV 作为策略输入
```

### 5.2 policy 自身必须切分

推荐第一版切分：

```text
policy_train = 2023-01-03 到 2024-12-31
policy_validation = 2025-01-01 到 2025-12-31
policy_test = 2026-01-01 到 2026-05-07
```

如果数据量不足，可做 walk-forward：

```text
WF1 train=2023H1..2023H2, valid=2024H1, test=2024H2
WF2 train=2023..2024H1, valid=2024H2, test=2025H1
WF3 train=2023..2024H2, valid=2025H1, test=2025H2
WF4 train=2023..2025, valid=none_or_rolling, test=2026H1 diagnostic
```

但任何报告必须明确区分：

```text
strict_test
validation
engineering_diagnostic
training_window_result
```

### 5.3 禁止的数据用法

禁止把以下字段作为策略运行时输入：

```text
future_return_*
forward_return_*
label_*
realized_pnl
realized_return
replay_return
future price
next_open / next_close, unless used only by replay execution after signal_date
execution_price
cash_after
nav_after
target_position
target_weight
broker_order_id
```

训练标签或 reward 可以由未来窗口收益计算，但必须满足：

```text
1. 只在 training dataset construction 中使用。
2. 不进入 policy inference feature。
3. train / validation / test 严格按时间切开。
4. 标签计算脚本输出 label_leakage_audit。
```

## 6. State / Action / Reward 初始设计

### 6.1 State features

第一版允许特征：

```text
qlib candidate_rank
qlib buy_score
qlib raw_score
qlib score_rank
qlib full_qlib_rank
score gap / rank gap
是否当前持仓
持仓天数
当前未实现收益分桶，仅限 as-of 可得 mark-to-market
持仓在 top50 内外状态
组合当前持仓数
当日可买候选数
当日可卖候选数
过去 N 日波动率，仅用 as-of 历史价格
过去 N 日成交量 / 流动性分桶，仅用 as-of 历史数据
市场 regime，如 normal / caution / risk_off，仅用 as-of 可得规则
估计交易成本参数
```

禁止特征：

```text
未来收益
未来价格
未来标签
replay realized pnl
未来是否涨停/跌停
从 test window 统计得到的全局归一化参数
任何不能在 signal_asof / available_at 前获得的字段
```

### 6.2 Action space

第一版动作空间必须离散、小而可审查：

```text
0 = skip / no_action
1 = allow_baseline_buy
2 = allow_baseline_sell
3 = hold_existing_position
```

更推荐从 binary action 开始：

```text
buy_candidate_action: allow_buy / block_buy
sell_candidate_action: allow_sell / block_sell
```

禁止第一版直接输出：

```text
target_weight
target_position
shares
lots
execution_quantity
cash allocation
broker order
```

### 6.3 Reward / utility

第一版 reward 只用于训练/评估，不得作为 inference 输入。

候选 utility 必须 return-first：

```text
primary_label = future_after_fee_tax_return
utility = future_after_fee_tax_return
          - turnover_penalty
          - drawdown_or_volatility_penalty
          - concentration_penalty
```

`missed_opportunity_penalty` 可以作为诊断项，但第一版不能把它设计成迫使模型事后追涨的未来泄漏机制。

必须至少做三种 return-first reward ablation：

```text
R0 = after_fee_tax_return_only
R1 = after_fee_tax_return - turnover_penalty
R2 = after_fee_tax_return - turnover_penalty - drawdown_penalty
```

R0 是主基准。R1/R2 只有在不显著牺牲 test net_return_after_fee_tax 的情况下才可优先。

审查者必须确认：

```text
reward 使用未来窗口只发生在 label construction；
policy inference 不读取 reward / realized pnl / replay return；
validation/test 上不按结果倒调 reward 权重。
```

## 7. Artifact 与合同设计

PA0 必须先设计实验 artifact，不得先训练。

建议新增诊断 artifact：

```text
PolicyTrainingDatasetArtifact
PolicyDecisionArtifact
PolicyEvaluationArtifact
```

### 7.1 PolicyTrainingDatasetArtifact

推荐路径：

```text
data_tw/experiments/policy_action_model_research/pa0_dataset_design/
```

必需文件：

```text
manifest.json
samples.csv
schema.json
feature_audit.csv
label_audit.csv
split_audit.csv
forbidden_field_audit.csv
```

`samples.csv` 必须包含：

```text
sample_id
signal_date
instrument
split
source_signal_artifact
source_price_artifact
baseline_strategy_rule
candidate_action_context
state_feature_*
label_utility_*
label_horizon
available_at
```

注意：`label_utility_*` 只能存在于 training dataset，不能进入 policy inference artifact。

### 7.2 PolicyDecisionArtifact

推荐路径：

```text
data_tw/experiments/policy_action_model_research/{phase}/policy_decisions/
```

必需文件：

```text
manifest.json
policy_decisions.csv
schema.json
policy_input_audit.csv
forbidden_output_audit.csv
```

`policy_decisions.csv` 可以包含：

```text
signal_date
instrument
policy_name
policy_family
policy_version
source_signal_artifact
policy_action
policy_score
policy_confidence
policy_reason_code
allowed_strategy_consumer
readonly_only
simulation_only
```

禁止包含：

```text
execution_price
execution_quantity
shares
lots
target_position
target_weight
cash
nav
broker_order_id
quick_trade
```

### 7.3 与 OrderIntentArtifact 的关系

policy model 不得直接输出订单，也不得直接写 replay result。

标准链路必须是：

```text
ModelSignalArtifact
  -> PolicyDecisionArtifact, diagnostic / readonly
  -> StrategyRule adapter
  -> OrderIntentArtifact
  -> ReplayResultArtifact
```

在 PA1/PA2 阶段，`PolicyDecisionArtifact` 只能作为 strategy rule 的附加过滤信号，并必须声明：

```text
production_allowed=false
readonly_only=true
simulation_only=true
not_order=true
not_target_position=true
```

## 8. 阶段计划

## PA0：合同、数据集与评估设计冻结

目标：

```text
1. 定义 PolicyTrainingDatasetArtifact / PolicyDecisionArtifact / PolicyEvaluationArtifact 草案。
2. 定义 qlib-only train/valid/test split。
3. 定义 state/action/reward 初始版本。
4. 定义 validator、golden samples、forbidden field audit。
5. 不训练模型。
```

执行者输出：

```text
docs/tw_portfolio_decision_model/POLICY_PA0_CONTRACT_DATASET_EVAL_DESIGN_EXECUTION_REPORT_CN.md
```

审查者输出：

```text
docs/tw_portfolio_decision_model/POLICY_PA0_CONTRACT_DATASET_EVAL_DESIGN_REVIEW_CN.md
```

PA0 通过条件：

```text
PASS_READY_FOR_PA1_SUPERVISED_UTILITY_DATASET
```

阻断条件：

```text
数据切分不清楚
future/replay/realized pnl 进入 inference feature
没有 forbidden field audit
没有 validator/golden sample 设计
试图直接进入 RL
```

## PA1：qlib-only supervised utility model

目标：

```text
1. 用 frozen_qlib_2018_2022 的 2023-2026H1 标准 signal 构造 policy dataset。
2. 训练简单 supervised utility model，优先 Logistic Regression / LightGBM / small MLP。
3. 预测每个候选动作的 utility 或 allow/block 概率。
4. 只在 validation 上选择阈值；test 只做一次最终评估。
5. 输出 PolicyDecisionArtifact 与 readonly replay。
```

第一版模型建议：

```text
baseline_model = logistic_regression 或 lightgbm_binary
objective = classify_positive_utility_action 或 rank_action_utility
```

比较对象：

```text
default = top50_exit_one_worst_sell
closed_rule_candidate = portfolio_decision_optimizer_v1, diagnostic only
policy_candidate = policy_supervised_utility_v1
```

PA1 必须报告：

```text
train_metrics
validation_metrics
test_metrics
calibration
feature_importance / SHAP, if available
threshold_selection_audit
readonly_replay_summary
turnover / fee / drawdown / return
missed_opportunity_analysis
forbidden_input_output_audit
```

执行者输出：

```text
docs/tw_portfolio_decision_model/POLICY_PA1_QLIB_ONLY_SUPERVISED_UTILITY_EXECUTION_REPORT_CN.md
```

审查者输出：

```text
docs/tw_portfolio_decision_model/POLICY_PA1_QLIB_ONLY_SUPERVISED_UTILITY_REVIEW_CN.md
```

PA1 通过条件：

```text
PASS_READY_FOR_PA2_CONTEXTUAL_BANDIT
```

最低要求采用 return-first：

```text
1. test net_return_after_fee_tax 原则上应超过 baseline；至少不能显著低于 baseline。
2. validation 与 test 的收益方向不能互相矛盾，不能只靠单窗口偶然收益推进。
3. 若收益略低于 baseline，必须有统筹明确接受的回撤/成本 tradeoff；否则不通过。
4. 换手/费用/回撤改善不能只来自极低参与度。
5. buy_count / sell_count / skip_count 不能复现旧 P 分支的过度保守失败模式。
6. validator 和 modular regression 通过。
```

默认阻断：

```text
只降低 turnover / fee / drawdown，但 test net_return_after_fee_tax 明显低于 baseline。
```

## PA2：qlib-only contextual bandit

目标：

```text
1. 在 PA1 数据集和 artifact 合同通过后，研究 contextual bandit。
2. 每个候选动作作为 bandit arm 或 binary allow/block decision。
3. 比较 supervised utility 与 bandit policy。
4. 仍只做 readonly replay，不接生产。
```

候选算法：

```text
LinUCB
Thompson Sampling
Doubly robust / IPS evaluation, if behavior policy can be defined
small neural contextual bandit, diagnostic only
```

执行者输出：

```text
docs/tw_portfolio_decision_model/POLICY_PA2_QLIB_ONLY_CONTEXTUAL_BANDIT_EXECUTION_REPORT_CN.md
```

审查者输出：

```text
docs/tw_portfolio_decision_model/POLICY_PA2_QLIB_ONLY_CONTEXTUAL_BANDIT_REVIEW_CN.md
```

PA2 通过后，才允许讨论 PA3。

## PA3：qlib-only offline RL research

PA3 不是当前优先任务，只能在 PA1/PA2 证明动作模型有价值后启动。

目标：

```text
1. 定义 MDP / POMDP 近似：state、action、transition、reward、episode。
2. 明确 behavior policy：baseline replay / historical simulated policy。
3. 使用 offline RL，禁止在线 RL。
4. 做 OOD action 风险审计。
```

候选算法：

```text
Conservative Q-Learning, CQL
Implicit Q-Learning, IQL
Batch-Constrained Q-learning / BCQ
Decision Transformer, diagnostic only if data量足够
```

PA3 阻断条件：

```text
没有足够 action coverage
behavior policy 不可定义
reward leakage
validation/test 不独立
RL policy 输出目标仓位或订单
```

## PA4：qlib+orthogonal LTR 适配研究

只有 qlib-only PA1/PA2/PA3 至少一个阶段显示稳定价值，才允许 PA4。

PA4 目标：

```text
1. 将 policy 输入从 qlib-only 扩展到 qlib+orthogonal LTR 标准 ModelSignalArtifact。
2. 不把 2023-2025 LTR training window 伪装为 strict OOS。
3. 优先使用 2026H1 strict forward 或重新规划 LTR/action 分层 OOS。
```

PA4 需要另行统筹判断是否：

```text
重新训练 qlib / LTR 以释放更长 action-model OOS 窗口；
或只把 LTR 适配作为 engineering diagnostic。
```

## PA5：readonly integration review

PA5 不是生产默认化。PA5 只审查：

```text
PolicyDecisionArtifact -> StrategyRule adapter -> OrderIntentArtifact -> ReplayResultArtifact
```

是否合同完整、readonly、可解释、可复现。

不得做：

```text
default switch
frontend default recommendation
provider publish
accepted latest switch
monitor write
broker/order
```

## 9. 评估指标

每个阶段至少报告，并且把收益指标置于报告最前：

```text
net_return_after_fee_tax
excess_net_return_vs_baseline
gross_return
max_drawdown
annualized_return, if supported
volatility, if supported
sharpe / sortino, if supported
action_count
buy_count
sell_count
skip_count
turnover_proxy
fee_and_tax
average_holding_days
median_holding_days
yearly_metrics
rolling_3m_metrics
rolling_6m_metrics
regime_segment_metrics
PnL concentration
symbol turnover concentration
missed_opportunity_count
false_block_buy_count
bad_allow_buy_count
bad_allow_sell_count
coverage_audit
forbidden_input_output_audit
```

必须同时报告旧 P 分支失败模式是否复现：

```text
过度 skip
参与度过低
收益捕获不足
低回撤主要来自不参与
交易集中且样本少
```

## 10. 审查总原则

审查者必须优先找以下问题：

```text
1. policy 是否用了 future/replay/realized pnl 作为 inference feature。
2. train/valid/test 是否混用。
3. threshold/reward/action 是否按 test replay 结果倒调。
4. 是否把 qlib-only 结果写成 qlib+LTR 结果。
5. 是否把 old portfolio_decision_optimizer_v1 当训练标签。
6. 是否输出 target_position / target_weight / quantity / broker order。
7. 是否默认化或 publish。
8. 是否把 engineering diagnostic 写成 strict OOS。
9. 是否没有跟 baseline 做同口径比较。
10. 是否只降低换手/回撤但收益捕获严重不足。
11. 是否违反 return-first 原则，把低回撤/低换手当成主要成功标准。
```

## 11. 给 PA0 执行者的 Prompt

```text
你是执行者。请启动 Policy / Action Model Research 主线 PA0：合同、数据集与评估设计冻结。

必须读取：
- docs/tw_portfolio_decision_model/PHASE_POLICY_ACTION_MODEL_RESEARCH_MAINLINE_CN.md
- docs/tw_portfolio_decision_model/PHASEP_BRANCH_B_CLOSURE_REVIEW_CN.md
- docs/tw_portfolio_decision_model/PHASEP_BRANCH_B_CLOSURE_EXECUTION_REPORT_CN.md
- docs/tw_modular_contracts/NEW_MODEL_AND_STRATEGY_DEVELOPER_GUIDE_CN.md
- docs/tw_modular_contracts/MODEL_SIGNAL_CONTRACT_CN.md
- docs/tw_modular_contracts/STRATEGY_RULE_CONTRACT_CN.md
- docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md
- docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md
- .agents/skills/tw-stock-new-model-onboarding/SKILL.md
- .agents/skills/tw-stock-new-strategy-onboarding/SKILL.md

本轮只做 PA0 设计，不训练、不 replay、不调参、不默认化。

目标：
1. 设计 PolicyTrainingDatasetArtifact / PolicyDecisionArtifact / PolicyEvaluationArtifact。
2. 固定第一阶段 signal 为 frozen_qlib_2018_2022 标准 ModelSignalArtifact。
3. 固定 policy train/validation/test 或 walk-forward 切分。
4. 定义 state/action/reward v0，并明确 return-first objective 与收益优先通过门槛。
5. 设计 validator、positive/negative golden samples、forbidden field audit。
6. 完成 Research Adoption Audit，逐项说明 FinRL / EIIE / LinUCB / CQL / IQL / BCQ / Decision Transformer / DeepPocket 的 adopted、rejected、deferred、risk、PA_mapping。
7. 明确 PA1 supervised utility model 的进入条件。

禁止：
不训练模型、不重训 qlib/LTR、不修 LTR artifact、不读取模型私有 CSV、不用旧 portfolio_decision_optimizer_v1 动作当训练标签、不输出 target_position/target_weight/quantity/order、不 provider publish、不 accepted latest switch、不 monitor write、不 broker/order、不启动 RL。

输出：
docs/tw_portfolio_decision_model/POLICY_PA0_CONTRACT_DATASET_EVAL_DESIGN_EXECUTION_REPORT_CN.md
```

## 12. 给 PA0 审查者的 Prompt

```text
你是审查者。请审查 PA0 执行报告：

- 是否只做合同、数据集、评估设计，没有训练或 replay；
- 是否固定第一阶段使用 frozen_qlib_2018_2022 标准 ModelSignalArtifact；
- 是否定义 policy train/validation/test 或 walk-forward；
- 是否没有把旧 portfolio_decision_optimizer_v1 动作当训练标签；
- 是否没有 future/replay/realized pnl 进入 inference feature；
- 是否定义 state/action/reward 且 action 不含目标仓位、数量、订单；
- 是否明确 return-first objective，且没有把低回撤/低换手作为主要成功标准；
- 是否设计 PolicyTrainingDatasetArtifact / PolicyDecisionArtifact / PolicyEvaluationArtifact；
- 是否设计 validator、golden samples、forbidden field audit；
- 是否完成 Research Adoption Audit，而不是只列论文名；
- 是否明确 PA1 才能训练 supervised utility model；
- 是否没有默认化、publish、monitor write、broker/order。

审查结论值：
PASS_READY_FOR_PA1_SUPERVISED_UTILITY_DATASET
FAIL_NEEDS_PA0_REPAIR
STOP_DO_NOT_CONTINUE

输出：
docs/tw_portfolio_decision_model/POLICY_PA0_CONTRACT_DATASET_EVAL_DESIGN_REVIEW_CN.md
```

## 13. 当前不授权事项

本主线文档不授权：

```text
生产默认策略切换
frontend 默认推荐
provider publish / refresh
accepted latest switch
monitor write / scan / alerts write
broker / quick-trade / real order
target_position / target_weight / execution_quantity 输出
直接 online RL
直接使用 qlib+LTR 训练窗口作为 strict OOS
把旧 P candidate 当监督标签
把 validation/test replay 结果用于倒调规则或 reward
```
