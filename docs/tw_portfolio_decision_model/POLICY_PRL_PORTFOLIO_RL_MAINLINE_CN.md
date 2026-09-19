---
created_at: 2026-06-22
status: coordinator_mainline_portfolio_rl_decision_policy_v1
scope: policy_after_pe1_repair_stop
previous_pe_closure: docs/tw_portfolio_decision_model/POLICY_PE1_REPAIR_QLIB_ONLY_ACTIVE_POLICY_SEARCH_REVIEW_CN.md
base_signal_first: frozen_qlib_2018_2022
policy_train_valid_test_required: true
readonly_only: true
simulation_only: true
not_order: true
not_target_position: true
not_target_weight: true
not_investment_advice: true
production_allowed: false
no_provider_publish: true
no_accepted_latest_switch: true
no_monitor_write: true
no_broker: true
no_frontend_default_switch: true
---

# PRL Portfolio RL / Deep Policy Decision 主线

## 0. 统筹结论

PE1 repair 已给出清晰负结果：

```text
docs/tw_portfolio_decision_model/POLICY_PE1_REPAIR_QLIB_ONLY_ACTIVE_POLICY_SEARCH_REVIEW_CN.md
verdict = FAIL_STOP_OR_COORDINATOR_DECISION
```

PE1 失败不是因为交易太少，而是因为手写 Family A/B/C active policy 在积极参与时破坏 baseline 收益：

```text
baseline train return = 2.41885797

baseline override active excess = -1.21053028
aggressive active excess        = -1.73060985 到 -2.45534395
switch active excess            = -1.32135007 到 -1.76286249
```

因此当前不应继续：

```text
1. PE1 手写参数网格无界调参。
2. PE2 strict_test replay。
3. 直接把 baseline clone 当作 policy 成功。
```

但这不代表 policy / RL 方向错误。它说明旧路线仍然太像“baseline 附近的规则扰动”。新主线改为真正的 portfolio decision environment：

```text
state = model rank/score + score history + price/MA/history + portfolio state
action = daily buy/sell/switch/hold slate
reward = after-fee-tax portfolio return / NAV delta
objective = maximize full episode return
```

本主线仍只做历史仿真和只读研究，不接实盘、不输出真实订单、不切换任何 production/default。

## 1. Simulation RL 与 Supervised/Offline RL 的区别

### 1.1 Simulation RL

Simulation RL 指：

```text
在历史 replay environment 中，让 agent 反复与环境交互。
agent 在 state_t 选择 action_t。
环境用历史价格和交易成本计算 reward_t 与 next_state_t。
训练目标是最大化 episode return。
```

它不需要事先构造固定 action dataset。训练过程中会自然产生 rollout buffer：

```text
(state, action, reward, next_state, done)
```

优点：

```text
1. 可以主动探索 baseline 没做过的动作。
2. 更贴近“让模型自己学如何最大化收益”。
3. 适合我们当前想扩大动作空间的目标。
4. PPO / A2C / DQN 等已有成熟算法可用。
```

主要风险：

```text
1. 容易过拟合 2023-2024 历史轨迹。
2. 动作空间过大时随机探索效率很低。
3. reward 噪声大，可能学到偶然行情。
4. 深度 policy 可解释性较弱，需要额外 attribution / replay audit。
```

### 1.2 Supervised / Offline RL

Supervised / Offline RL 指：

```text
先构造固定 dataset。
dataset 包含历史 state、candidate action、reward/return/advantage 或 trajectory。
模型只从 dataset 学习，不再主动探索环境。
```

典型形式：

```text
1. supervised imitation: 学 oracle / high-return action。
2. action-value regression/ranking: 学 Q(s,a) 或 advantage(s,a)。
3. offline RL: CQL / IQL / BCQ / Decision Transformer。
```

优点：

```text
1. 更容易审计 dataset coverage。
2. 训练稳定，便于离线复现。
3. 适合从 oracle / heuristic / simulation rollouts 中蒸馏 policy。
```

主要风险：

```text
1. dataset 覆盖不足时，policy 会在 OOD action 上过估计。
2. 如果 dataset 主要来自 baseline，就会学成 baseline clone。
3. 如果 oracle label 太依赖未来信息，容易形成不可泛化标签。
4. 固定 dataset 无法自己补探索盲区。
```

### 1.3 本项目优先级

本主线优先级如下：

```text
PRL0: PortfolioDecisionEnv + oracle/random/heuristic audit
PRL1: Simulation RL first, PPO/A2C/DQN on compact discrete action templates
PRL2: Supervised imitation / action-value learning from generated rollouts as对照
PRL3: Offline RL only after rollout dataset coverage audit
PRL4: qlib+orthogonal LTR adapter only after qlib-only evidence
```

选择理由：

```text
1. 当前缺的不是静态市场数据，而是可交互的决策环境和可审计动作空间。
2. baseline 历史日志覆盖太窄，不足以直接做强 offline RL。
3. simulation RL 能在历史环境中探索 baseline 没做过的动作。
4. supervised/offline RL 更适合作为 simulation 轨迹和 oracle 轨迹的蒸馏/对照，而不是第一步。
```

## 2. 参考研究与采用方式

执行者不得 freestyle。PRL0 必须逐项阅读并写 `Research Adoption Audit`。

| id | 研究 | 链接 | 借鉴点 | 本项目采用 | 本项目暂不采用 |
|---|---|---|---|---|---|
| R1 | FinRL: A Deep Reinforcement Learning Library for Automated Stock Trading in Quantitative Finance | https://arxiv.org/abs/2011.09607 | environment / agent / backtest 分层；交易成本、流动性、风险约束；DQN/DDPG/PPO/SAC/A2C/TD3 等算法对照 | 采用分层架构、历史仿真环境、交易成本、baseline 对照、可复现 artifact | 不接 live trading；不照搬连续仓位输出；不输出真实订单 |
| R2 | A Deep Reinforcement Learning Framework for the Financial Portfolio Management Problem / EIIE | https://arxiv.org/abs/1706.10059 | portfolio state、previous portfolio memory、显式 reward、交易成本、CNN/RNN/LSTM policy | 采用 portfolio state/history/reward 设计思想；用于支持深度 policy 捕捉 score/MA/持仓交互 | 不采用连续 target_weight；不采用 crypto 高频假设；不做 online stochastic batch learning |
| R3 | Proximal Policy Optimization Algorithms | https://arxiv.org/abs/1707.06347 | 通过 clipped objective 控制 policy update；采样 trajectory 后多轮 minibatch update | PRL1 优先候选：categorical PPO over compact action templates | 不允许真实市场在线探索；不允许 strict_test 调参 |
| R4 | Human-level control through deep reinforcement learning / DQN | https://www.nature.com/articles/nature14236 | 深度 Q-learning 从高维 state 学离散动作价值；experience replay / target network 思路 | PRL1 对照候选：DQN/Double-DQN for compact discrete action templates | 不用于过大组合动作空间；不把 Q 值当作可解释收益承诺 |
| R5 | Conservative Q-Learning for Offline Reinforcement Learning | https://arxiv.org/abs/2006.04779 | offline RL 中对 OOD action 价值保守，降低分布外动作过估计 | PRL3 候选：当 rollout dataset coverage 足够后做 CQL 对照 | PRL0/PRL1 不做 CQL；不从 baseline-only dataset 直接训练 |
| R6 | Offline Reinforcement Learning with Implicit Q-Learning | https://arxiv.org/abs/2110.06169 | 避免直接评估数据外 action；advantage-weighted behavioral cloning | PRL3 候选：用于 coverage 不完整但有多策略 rollouts 的 offline policy improvement | PRL0/PRL1 不做 IQL |
| R7 | Decision Transformer | https://arxiv.org/abs/2106.01345 | 把 RL 表述为 return-conditioned sequence modeling | PRL3/diagnostic：在有足够 trajectory 后分析高收益轨迹模式 | 暂不作为第一版；returns-to-go 有泄漏/过拟合风险 |
| R8 | Portfolio Choice with Transaction Costs: a User's Guide | https://arxiv.org/abs/1207.7330 | 交易成本会改变最优再平衡，存在 no-trade/rebalance tradeoff | reward 和审计必须 after-fee-tax；做 cost sensitivity audit | 不把低换手当主目标，仍 return-first |

## 3. 核心研究问题

本主线要回答：

```text
给定 qlib 模型输出的 rank/score、历史价格/MA、当前持仓与交易成本，
能否训练一个 policy，在严格 OOS validation/test 上超过 baseline？
```

当前 baseline：

```text
top50_exit_one_worst_sell / equivalent readonly baseline
```

新路线不再限制为：

```text
每日最多一买一卖
只能买 rank 最高
只能卖 rank 最低
必须跟 baseline 动作接近
```

但仍必须限制为 intent-level readonly action：

```text
hold
buy one/multiple from allowed topK candidates
sell one/multiple from current holdings
switch one/multiple sell_i -> buy_j
```

不得输出：

```text
quantity
target_position
target_weight
execution_price
broker order
quick-trade
```

## 4. 数据窗口与 OOS 规则

第一阶段仍使用 qlib-only，避免 LTR 训练窗口争议：

```text
input_signal_artifact =
data_tw/artifacts/signals/frozen_qlib_2018_2022/r1_legacy_signal_adapter_20260616/manifest.json

base qlib train = 2018-2022
policy train = 2023-01-01..2024-12-31
policy validation = 2025-01-01..2025-12-31
policy strict_test = 2026-01-01..2026-05-07
```

规则：

```text
1. train 可用于 env debug、RL training、oracle/random audit、hyperparameter proposal。
2. validation 只用于 model/config/final policy selection。
3. strict_test 只 final-only，不得用于任何调参。
4. 如果 validation 不超过 baseline，不得运行 strict_test。
5. 如果 strict_test 失败，不得回头改同一 policy 再试。
```

## 5. PortfolioDecisionEnv v1

### 5.1 State

每个 decision date 的 state 包含：

```text
per-stock signal:
  candidate_rank
  buy_score
  raw_score
  score_rank
  full_qlib_rank
  score_delta_1/5/20d if PIT-safe
  rank_delta_1/5/20d if PIT-safe

price/history:
  close/open history available before decision
  MA5/MA10/MA20/MA60
  return_1/5/20d past-only
  volatility_20d past-only
  volume/value features only if available_at is safe

portfolio:
  current_holding_flag
  holding_age
  unrealized_return based on available current/past price only
  cost_basis if replay state provides it
  number_of_holdings
  cash/full-slot status

market:
  market index past return/MA/volatility if PIT-safe
  breadth features if PIT-safe
```

禁止 feature：

```text
future_return
forward_return
label
realized_pnl from future replay
future price
same-day unavailable data
strict_test metrics
```

### 5.2 Action Space

第一版必须压缩动作空间，不能让 agent 在全市场任意组合爆炸。

推荐 compact discrete action templates：

```text
A0: hold / no trade
A1: execute baseline action
A2: buy_top_i where i in topK buckets and free slot exists
A3: sell_holding_j where j is one of current holdings ordered by learned/heuristic weakness
A4: switch_holding_j_to_candidate_i
A5: multi_switch_template with max 2 pairs
A6: sell_k_weak_holdings
A7: buy_k_strong_candidates
```

候选边界：

```text
candidate_k in {50, 100, 150}
max_buy_count <= 3
max_sell_count <= 3
max_switch_pair_count <= 3
```

PRL0 必须审计：

```text
action_count_per_day
executable_action_ratio
invalid_action_reasons
baseline_action_in_space
oracle_action_in_space
```

### 5.3 Reward

第一版 reward 必须 after-fee-tax：

```text
reward_t = NAV_{t+1}/NAV_t - 1 - fee_tax_impact
```

可做 ablation：

```text
R0: next-open to next-open one-step NAV delta
R1: multi-day shaped reward with transaction cost
R2: episode terminal return with small step reward
```

不得把低换手/低回撤作为主 reward。它们只作为约束和审计。

## 6. Action Dataset 是否必须构造

结论：

```text
不是 simulation RL 的前置条件。
```

如果走 PPO/DQN simulation RL，dataset 会在训练中由 rollout buffer 产生：

```text
state, action, reward, next_state, done, action_logprob/value
```

但 PRL0 仍必须做 oracle/random/heuristic rollout audit，原因是：

```text
1. 证明 action space 存在超过 baseline 的 oracle upper bound。
2. 证明随机探索不是完全无效。
3. 证明可执行动作覆盖足够。
4. 证明环境 reward 没有明显 bug。
```

如果 oracle upper bound 都不超过 baseline，则说明：

```text
action space 设计错了，或 qlib-only signal 本身不足以支持 policy 增量。
```

此时不应进入 PPO/DQN。

## 7. 阶段计划

## PRL0: Env / Action Space / Oracle Audit Freeze

目标：

```text
实现或设计 PortfolioDecisionEnv v1，并证明动作空间、reward、baseline replay、oracle/random audit 可审查。
```

PRL0 允许：

```text
1. 构造 env schema。
2. 生成 state/action/reward schema。
3. 跑 train/validation 的 baseline parity replay。
4. 跑 train-only oracle upper bound。
5. 跑 train-only random/heuristic rollout。
6. 输出 env validator / golden samples。
```

PRL0 不允许：

```text
1. 训练 PPO/DQN。
2. 使用 strict_test。
3. 使用 LTR。
4. 输出 target_weight / target_position / quantity / broker order。
5. provider/latest/monitor/frontend/Agent 扩权。
```

PRL0 输出：

```text
data_tw/experiments/portfolio_rl_research/prl0_env_oracle_audit/
  manifest.json
  env_schema.json
  state_feature_schema.json
  action_space_schema.json
  reward_schema.json
  baseline_parity_metrics.csv
  oracle_upper_bound_train.csv
  random_rollout_train.csv
  heuristic_rollout_train.csv
  action_coverage_audit.csv
  executable_action_audit.csv
  forbidden_feature_audit.csv
  validator_report.json
  golden_samples_report.json

docs/tw_portfolio_decision_model/POLICY_PRL0_ENV_ORACLE_AUDIT_EXECUTION_REPORT_CN.md
```

PRL0 通过条件：

```text
1. baseline parity 与现有 qlib baseline 一致或差异可解释。
2. oracle upper bound train 明显高于 baseline。
3. random/heuristic rollout 可执行率足够，不大量 invalid。
4. action space 覆盖 baseline action 和 non-baseline action。
5. validator/golden samples pass。
6. forbidden feature audit pass。
```

若 oracle upper bound 不高于 baseline：

```text
STOP_REDESIGN_ACTION_SPACE_OR_SIGNAL_INPUT
```

不得进入 PRL1。

## PRL1: Simulation RL qlib-only

只有 PRL0 通过后才允许。

优先算法：

```text
1. PPO categorical policy over compact action templates
2. A2C as lightweight actor-critic baseline
3. DQN / Double-DQN for fixed discrete action template comparison
```

为什么 PPO 优先：

```text
1. 它直接优化 trajectory return。
2. clipped update 比普通 policy gradient 稳定。
3. 适合 stochastic policy 在历史 env 中探索。
4. FinRL 等交易 RL 工作广泛采用 PPO/A2C/DQN 类方法。
```

PRL1 必须：

```text
1. 只在 train 训练。
2. 用 validation 选择 algorithm/config/checkpoint。
3. strict_test 不运行。
4. 记录 seeds、episode_count、reward curve、validation evaluation count。
5. 输出 policy decision artifact、readonly replay、action attribution audit。
```

PRL1 通过条件：

```text
validation policy net_return_after_fee_tax > validation baseline
participation_ratio >= 0.85
action_count_ratio >= 0.80
收益不是靠 no_action / 极低参与产生
收益不是单一股票/单日极端贡献
validator/golden samples pass
```

若 validation 未超过 baseline：

```text
STOP_OR_PRL1_REPAIR_WITH_COORDINATOR_DECISION
```

不得进入 strict_test。

## PRL2: Supervised / Imitation / Action-value Contrast

只有 PRL0 通过后可作为 PRL1 对照，或 PRL1 有初步正证据后启动。

训练数据来源：

```text
1. PRL0 oracle actions
2. PRL0 heuristic rollouts
3. PRL1 high-return rollouts
4. random rollouts after filtering invalid actions
```

可训练：

```text
1. supervised policy classifier
2. action-value regressor / ranker
3. advantage-weighted behavior cloning
```

PRL2 的 dataset 好坏不看 dataset 自身收益率，而看：

```text
1. oracle upper bound 是否高于 baseline。
2. action coverage 是否足够。
3. executable action ratio 是否足够。
4. learned policy validation 是否超过 baseline。
5. label/feature 是否无泄漏。
```

## PRL3: Offline RL

只有 PRL1/PRL2 至少一个在 validation 有正证据，且 rollout dataset coverage 充分，才允许。

候选：

```text
CQL
IQL
BCQ-style behavior-constrained Q learning
Decision Transformer diagnostic
```

PRL3 必须特别审计：

```text
OOD action ratio
behavior policy mixture
coverage by action type
coverage by market regime
coverage by score/rank bucket
```

## PRL4: Strict-test Final Replay

只有 validation 选出唯一 final policy 后才允许。

规则：

```text
1. strict_test 只跑一次。
2. 不得根据 strict_test 改任何参数。
3. strict_test policy return 必须 > strict_test baseline。
4. 若失败，写 closure，不得同线反复试。
```

## PRL5: Optional qlib + Orthogonal LTR Adapter

只有 qlib-only PRL4 通过后才允许另开。

注意：

```text
LTR 2023-2025 是训练窗口，不能把 2023-2025 LTR replay 当严格 OOS 策略证明。
```

## 8. 审查重点

审查者每轮必须检查：

```text
1. 是否仍在当前 PRL 阶段。
2. 是否 qlib-only first。
3. 是否 strict train/validation/test 分离。
4. strict_test 是否未被提前使用。
5. 是否没有 target_weight / target_position / quantity / broker order。
6. 是否没有 future_return / label / realized_pnl 作为 feature。
7. 是否 return-first，而不是低换手/低回撤优先。
8. 是否 action space 足够大但仍可探索。
9. 是否 baseline action 在 action space 内。
10. 是否 oracle upper bound 证明有学习空间。
11. 是否 validation 真的超过 baseline，而不是 baseline clone。
12. 是否给出 attribution / trade contribution / concentration audit。
```

## 9. 停止条件

任一情况出现，必须停止：

```text
1. PRL0 oracle upper bound 不高于 baseline。
2. baseline parity replay 不一致且无法解释。
3. invalid action 比例过高。
4. validation 未超过 baseline，却要求跑 strict_test。
5. strict_test 被用于调参。
6. 输出 target_weight / target_position / quantity / broker order。
7. 使用 future label / realized pnl / future price 做 feature。
8. provider/latest/monitor/frontend/Agent/broker 扩权。
9. validation improvement 来自低参与/no_action。
10. 多 seed 结果极不稳定且无解释。
```

## 10. PRL0 执行者命令

```text
你是执行者。请启动 PRL Portfolio RL / Deep Policy Decision 主线 PRL0。

必须读取：
1. docs/tw_portfolio_decision_model/POLICY_PRL_PORTFOLIO_RL_MAINLINE_CN.md
2. docs/tw_portfolio_decision_model/POLICY_PE1_REPAIR_QLIB_ONLY_ACTIVE_POLICY_SEARCH_REVIEW_CN.md
3. docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md
4. docs/tw_modular_contracts/NEW_MODEL_AND_STRATEGY_DEVELOPER_GUIDE_CN.md
5. docs/tw_modular_contracts/MODEL_SIGNAL_CONTRACT_CN.md
6. docs/tw_modular_contracts/STRATEGY_RULE_CONTRACT_CN.md
7. docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md
8. docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md

本轮只做 PRL0：
- 设计/实现 PortfolioDecisionEnv v1 schema；
- 设计 state/action/reward schema；
- 跑 qlib-only baseline parity；
- 跑 train-only oracle upper bound；
- 跑 train-only random/heuristic rollout；
- 输出 action coverage / executable action / forbidden feature audit；
- 输出 validator/golden samples；
- 写 PRL0 execution report。

本轮禁止：
- 训练 PPO/DQN/A2C；
- 运行 strict_test；
- 使用 LTR；
- 输出 target_position/target_weight/quantity/order；
- provider/latest/monitor/frontend default/Agent/broker 扩权。

artifact 根目录：
data_tw/experiments/portfolio_rl_research/prl0_env_oracle_audit/

执行报告：
docs/tw_portfolio_decision_model/POLICY_PRL0_ENV_ORACLE_AUDIT_EXECUTION_REPORT_CN.md
```

## 11. PRL0 审查者命令

```text
你是审查者。请审查 PRL0 执行报告是否符合 PRL 主线。

必须检查：
1. 是否完整读取 PRL 主线、PE1 repair closure 和项目合同；
2. Research Adoption Audit 是否覆盖 R1-R8；
3. PortfolioDecisionEnv / state / action / reward schema 是否完整；
4. baseline parity 是否通过；
5. oracle upper bound 是否明显高于 baseline；
6. random/heuristic rollout 是否可执行；
7. action coverage 是否覆盖 baseline 与 non-baseline；
8. forbidden feature audit 是否通过；
9. validator/golden samples 是否通过；
10. 是否未训练 PPO/DQN/A2C，未运行 strict_test，未有任何生产/交易扩权。

审查输出：
docs/tw_portfolio_decision_model/POLICY_PRL0_ENV_ORACLE_AUDIT_REVIEW_CN.md

如果 PRL0 通过，请写 PRL1 simulation RL work document。
如果 oracle upper bound 不高于 baseline，请建议停止或重设 action space，不得进入 PRL1。
```
