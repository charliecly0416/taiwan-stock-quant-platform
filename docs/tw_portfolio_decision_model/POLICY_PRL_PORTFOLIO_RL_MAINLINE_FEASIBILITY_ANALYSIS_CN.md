---
created_at: 2026-06-22
status: reviewer_feasibility_analysis_only
mainline_doc: docs/tw_portfolio_decision_model/POLICY_PRL_PORTFOLIO_RL_MAINLINE_CN.md
previous_pe_review: docs/tw_portfolio_decision_model/POLICY_PE1_REPAIR_QLIB_ONLY_ACTIVE_POLICY_SEARCH_REVIEW_CN.md
scope: mainline_feasibility_analysis_no_executor_review
verdict: CONDITIONALLY_REASONABLE_WITH_STRICT_PRL0_GATE
readonly_only: true
simulation_only: true
production_allowed: false
pe2_authorized: false
prl1_authorized_by_this_doc: false
strict_test_authorized: false
---

# PRL Portfolio RL 主线可行性分析

## 1. 总体结论

结论：

```text
CONDITIONALLY_REASONABLE_WITH_STRICT_PRL0_GATE
```

PRL 主线作为 PE1 repair 失败后的下一条研究路线，是合理且有实验价值的，但必须保持“PRL0 先证明环境和动作空间存在学习空间，再允许 PRL1 训练 RL”的门槛。

当前主线最合理的部分是：

```text
1. 不直接从 PE1 失败跳到 PPO/DQN 训练。
2. 先做 PortfolioDecisionEnv / action space / reward / oracle upper bound / random rollout audit。
3. PRL0 只用 train/validation，不碰 strict_test。
4. PRL1 只有在 PRL0 证明 oracle upper bound 明显高于 baseline 后才允许。
5. PRL3 offline RL 被放在 rollout coverage 充分之后，而不是 baseline-only dataset 上直接训练。
```

这与本项目当前情况匹配：PE1 手写规则扰动失败，说明 baseline 附近的小规则空间没有发现增量；但它没有否定更丰富 state、可学习 policy、历史仿真 environment 的研究价值。

本轮只分析主线可行性，不审查执行者工作，不授权 PRL1、PRL2、PRL3、PRL4 或 strict_test。

## 2. 与本项目现状的适配性

### 2.1 为什么 PRL 方向不是简单“再换一种调参”

PE1 repair 的负结果是：

```text
baseline clone 排除后，没有 active policy 通过 train/validation gate。
Family A/B/C active policy 在积极参与时显著低于 baseline。
```

这说明现有手写规则空间的问题不是交易不足，而是动作选择质量差。PRL 主线把问题改成：

```text
state = rank/score + score history + price/history + portfolio state
action = compact daily action templates
reward = after-fee-tax NAV delta
objective = full episode return
```

这个转换是合理的。它把“人工写阈值规则”换成“先定义可审计环境，再让 policy 在环境中学习动作选择”。如果我们还想验证 portfolio decision model 是否有增量价值，这比继续扩 PE1 网格更有意义。

### 2.2 为什么 PRL0 是必要前置

PRL0 的 oracle/random/heuristic audit 很关键。它回答三个底层问题：

```text
1. action space 里是否存在理论上能超过 baseline 的动作序列。
2. baseline action 是否能被环境复现，baseline parity 是否成立。
3. random/heuristic rollout 是否大多可执行，还是动作空间设计导致大量 invalid。
```

如果 oracle upper bound 都不能高于 baseline，说明不是 PPO/DQN 能解决的问题，而是：

```text
action space 设计不含有效增量动作；
state 信息不足；
qlib-only signal 本身不足；
或环境/reward 有 bug。
```

因此主线写明“oracle upper bound 不高于 baseline 则不得进入 PRL1”是必要且正确的。

## 3. 研究依据判断

### 3.1 FinRL 支持分层环境思路，但不支持无审计直接训练

FinRL 论文强调交易 DRL 应有 environment / agent / backtest 的模块化分层，并显式纳入交易成本、流动性、风险约束和 baseline 对照。PRL 主线采用分层环境、历史仿真、交易成本和 baseline parity，是符合该研究范式的。

但 FinRL 也说明实际交易 agent 的开发和调试容易出错。因此本项目不能直接把 FinRL 式 PPO/A2C/DQN 训练当成第一步；PRL0 先做环境 parity 和 oracle audit 是更适配本项目的工程化约束。

参考：FinRL, arXiv:2011.09607, https://arxiv.org/abs/2011.09607

### 3.2 EIIE 支持 portfolio state/history/reward，但其连续权重不适合本项目合同

EIIE/Portfolio-Vector Memory 的价值在于强调 previous portfolio、显式 reward 和交易成本，对 PRL 的 state/reward 设计有启发。但原论文面向组合权重再分配和高频 crypto 场景，本项目合同明确禁止 `target_weight / target_position / quantity`。

因此 PRL 主线“不采用连续 target_weight，只采用 intent-level compact action templates”是正确的取舍。

参考：A Deep Reinforcement Learning Framework for the Financial Portfolio Management Problem, arXiv:1706.10059, https://arxiv.org/abs/1706.10059

### 3.3 PPO/DQN 可作为 PRL1 候选，但样本量与过拟合风险很高

PPO 的 clipped objective 有助于限制过大 policy update，适合离散模板动作上的 stochastic policy；DQN/Double-DQN 可作为固定离散动作模板的对照。这些算法放在 PRL1 是合理的。

但本项目 policy train 只有 2023-2024，validation 只有 2025，strict_test 到 2026-05-07；对深度 RL 来说样本很少、市场状态非平稳、reward 噪声大。PRL1 必须强制：

```text
multi-seed
训练曲线和 early stopping 记录
validation evaluation count 限制
action distribution audit
trade contribution / concentration audit
```

否则很容易把 2023-2024 的偶然行情学成 policy。

参考：PPO, arXiv:1707.06347, https://arxiv.org/abs/1707.06347；DQN, Nature 2015, https://www.nature.com/articles/nature14236

### 3.4 Offline RL 延后是正确的

CQL/IQL/Decision Transformer 都依赖离线数据覆盖质量。当前项目如果只用 baseline 历史动作，容易复现 PE1 的 baseline clone 问题；如果 action coverage 不足，offline RL 会在 OOD action 上过估计或难以可靠改进。

PRL 主线把 CQL/IQL/Decision Transformer 放到 PRL3，并要求 rollout dataset coverage audit 后才能启动，是合理的。

参考：

```text
CQL: https://arxiv.org/abs/2006.04779
IQL: https://arxiv.org/abs/2110.06169
Decision Transformer: https://arxiv.org/abs/2106.01345
```

### 3.5 交易成本必须进入 reward，而不能只做事后指标

交易成本文献强调再平衡和 no-trade region 会改变最优策略。PRL 主线把 reward 定义为 after-fee-tax NAV delta，并把低换手/低回撤降为约束与审计，不作为主 reward，是符合 return-first 目标的。

参考：Portfolio Choice with Transaction Costs: a User's Guide, arXiv:1207.7330, https://arxiv.org/abs/1207.7330

## 4. 主要合理点

PRL 主线合理点：

```text
1. 正确吸收 PE1 失败：不继续手写规则网格，不把 baseline clone 当成功。
2. PRL0 不训练 RL，只验证 env/action/reward/oracle，是必要安全门。
3. qlib-only first，避免 LTR 2023-2025 训练窗口污染 OOS 解释。
4. action space 采用 compact discrete templates，避免全市场组合爆炸。
5. reward after-fee-tax，仍 return-first。
6. strict_test final-only，validation 不过 baseline 不跑 strict_test。
7. offline RL 延后，避免 baseline-only dataset 直接训练造成 OOD/action coverage 风险。
8. 明确 readonly/simulation-only，不触碰 target_weight/target_position/broker/production。
```

## 5. 主要风险

### R1. RL 样本量不足与过拟合

2023-2024 的训练 episode 数量有限。若按日决策，样本规模对深度 RL 偏小，而且市场 regime 非平稳。PRL1 即使 validation 通过，也可能是 seed 或单一行情窗口偶然胜利。

约束建议：

```text
PRL1 必须 multi-seed。
必须报告 seed mean/std，而不是只报 best seed。
必须限制 validation evaluation count。
必须记录每次 validation 被查看的次数。
```

### R2. Oracle upper bound 容易泄漏

PRL0 oracle 是最重要的 gate，也是最容易出问题的部分。oracle 如果用到了 future return、未来价格路径、当前日不可得成交信息或 replay outcome，就会虚高。

约束建议：

```text
oracle 必须声明是 diagnostic upper bound 还是 PIT-safe oracle。
若 oracle 用未来信息，只能作为 action space capacity diagnostic，不能作为可学习性证明。
PRL0 应至少有一个 PIT-safe heuristic/oracle-like rollout 用于学习空间判断。
```

### R3. Action template 可能仍然包含 baseline shortcut

PRL action space 包含：

```text
A1: execute baseline action
```

这是必要的 baseline parity 设计，但也会让 RL 学成 baseline clone。PRL1 需要审计：

```text
baseline_action_ratio
non_baseline_action_ratio
active improvement contribution
```

若最终 policy 主要靠 `execute baseline action` 达到 baseline，不能算 PRL 成功。

### R4. Action space 过大或 invalid 过多会让探索失败

买/卖/switch/multi-switch 如果模板展开过多，PPO/DQN 会面对稀疏有效动作和高噪声 reward。主线已限制 candidate_k、max_buy/sell/switch，这是正确的，但 PRL0 还必须给出 invalid action reasons 和 executable ratio。

### R5. State feature 的 available_at 需要严格定义

price/history、MA、volume/value、breadth、market index 特征都可能有可得性问题。主线写了 PIT-safe，但 PRL0 必须落到字段级：

```text
feature_name
source
lookback_window
asof
available_at
decision_time
forbidden_future_dependency
```

### R6. reward 口径要和既有 replay 一致

PRL0 baseline parity 是硬门槛。若 Env 的 NAV、税费、pending、next_open 执行、缺价处理和现有 replay 不一致，后续 RL 结果没有可比性。

## 6. 对主线的必要约束建议

不需要改变主线阶段，但建议在 PRL0 审查时强制以下门槛：

```text
1. baseline parity tolerance 必须明确，例如 return/turnover/action_count 差异阈值。
2. oracle 分成 diagnostic oracle 与 PIT-safe heuristic，不得混用结论。
3. action space 必须证明 baseline action in-space，non-baseline action in-space，invalid action ratio 可控。
4. active policy 成功必须排除 baseline clone：最终 policy 需报告 non_baseline_action_ratio。
5. PRL1 若启动，必须 multi-seed，并报告 mean/std/worst seed。
6. PRL1 validation improvement 必须扣除交易成本，且不是单日/单股贡献。
7. strict_test 只在 PRL4，由 reviewer 在 validation final policy 后授权。
```

## 7. 是否值得做

值得做，但预期成功概率应保守。

理由：

```text
1. PE1 已证明手写规则空间不够，继续 PE1 网格价值低。
2. PRL0 能低成本暴露最关键问题：env 是否正确、action space 是否有 oracle 上界。
3. 如果 PRL0 oracle upper bound 都失败，可以快速停止，不消耗 PRL1/strict_test。
4. 如果 PRL0 通过，PRL1 才有正当实验价值。
```

不应期待：

```text
PPO/DQN 一上来稳定超过 baseline。
一次 validation 通过就能证明可上线。
RL 自动解决 qlib-only signal 信息不足。
```

## 8. 审查结论

PRL 主线在路线设计上合理，适配当前项目的失败事实和模块边界。它不是直接把失败的 PE 规则换成更复杂模型，而是先补齐 portfolio decision environment，并用 oracle/action coverage/baseline parity 判断是否有学习空间。

通过性结论：

```text
可以允许进入 PRL0。
不应直接允许 PRL1。
PRL0 不通过时必须停止或重设 action space / signal input。
PRL1 只有在 PRL0 oracle upper bound、baseline parity、action coverage、validator/golden 全部通过后才有实验价值。
```

最终判断：

```text
PRL is feasible as a controlled research mainline.
Its value depends almost entirely on PRL0 gate quality.
The reviewer should be strict: no oracle upper bound, no PRL1.
```
