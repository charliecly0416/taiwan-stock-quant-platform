---
created_at: 2026-06-22
status: coordinator_mainline_paper_aligned_portfolio_allocation_rl_v1
scope: after_prl1_r1_r_candidate_intent_route_failure
previous_stage_summary: docs/tw_portfolio_decision_model/POLICY_PRL1_R1_R_PARTICIPATION_CONSTRAINED_REPAIR_STAGE_SUMMARY_CN.md
base_signal_first: frozen_qlib_2018_2022
policy_train_valid_test_required: true
readonly_only: true
simulation_only: true
not_order: true
not_investment_advice: true
production_allowed: false
strict_test_authorized_initially: false
provider_publish_authorized: false
accepted_latest_switch_authorized: false
monitor_write_authorized: false
broker_authorized: false
frontend_default_switch_authorized: false
---

# PAL Paper-aligned Portfolio Allocation RL 主线

## 0. 统筹结论

当前 PRL candidate-level intent route 的结论已经足够清楚：

```text
PRL1-R0 contract/logging: PASS
PRL1-R1 candidate policy: FAIL, low participation
PRL1-R1-R participation repair: FAIL, switch concentration + seed instability
strict_test: not authorized
```

不能继续同线做：

```text
buy/sell/switch intent-level candidate policy 的无界 repair。
```

但这不等于 policy / RL 方向失败。当前失败更可能来自：

```text
我们的实现仍是离散 intent policy，
而主要 portfolio RL 论文真正优化的是 portfolio allocation / portfolio vector / previous portfolio memory / price tensor / transaction-cost-aware reward。
```

因此新路线改为：

```text
paper-aligned portfolio allocation RL adaptation
```

先按论文实现机制做适配审计和合同冻结，再决定是否训练。

## 1. 目标

本主线要回答：

```text
在不增强 qlib/LTR 信号、不接实盘、不改变 production/default 的前提下，
能否按 FinRL / EIIE / PGPortfolio 等论文的真实机制，
构造 simulation-only portfolio allocation RL，
并在 qlib-only validation 上超过 baseline？
```

第一阶段仍使用 qlib-only：

```text
input_signal_artifact =
data_tw/artifacts/signals/frozen_qlib_2018_2022/r1_legacy_signal_adapter_20260616/manifest.json

base qlib train = 2018-2022
policy train = 2023-01-01..2024-12-31
policy validation = 2025-01-01..2025-12-31
policy strict_test = 2026-01-01..2026-05-07
```

## 2. 非目标

本主线初始阶段不授权：

```text
1. strict_test。
2. qlib+orthogonal LTR。
3. provider publish / accepted latest switch。
4. monitor write / frontend default / Agent integration。
5. broker / quick-trade / real order。
6. 生产默认策略切换。
7. 直接把论文结果当作本项目收益承诺。
```

本路线也不允许：

```text
把 portfolio allocation vector 直接输出为 OrderIntent target_weight / target_position。
```

如果需要论文级 allocation action，只能先定义：

```text
simulation-only AllocationDiagnosticArtifact
```

并且该 artifact 必须被禁止进入：

```text
OrderIntentArtifact
StrategyRule production path
frontend default
Agent recommendation
broker / quick-trade
provider latest
```

是否允许该 diagnostic artifact，是 PAL0 第一阶段必须冻结和审查的合同问题。

## 3. 为什么当前 PRL 失败不等于论文方法失败

PRL1-R1-R 的失败模式：

```text
1. candidate-level policy 可以产生 validation 正收益；
2. 低参与修复后，正收益退化为 switch concentration；
3. seed stability 弱；
4. action abstraction 是 buy/sell/switch intent。
```

论文方法的常见机制：

```text
1. action 是 portfolio allocation / weight vector；
2. state 是多资产 price tensor / feature tensor；
3. policy 使用 CNN/RNN/LSTM 或 actor-critic；
4. previous portfolio vector / portfolio memory 进入 state；
5. reward 直接是 portfolio value change after transaction costs；
6. replay/backtest 评估完整 portfolio trajectory。
```

差异：

```text
当前 PRL 主要学习“做哪些 discrete intent”；
论文方法学习“组合资本如何在资产之间分配”。
```

因此后续必须做论文级适配，而不是继续扩大 intent-level hyperparameter search。

## 4. 参考研究与采用方式

执行者在 PAL0 必须逐项阅读原始论文或官方实现文档，并输出 `Paper Implementation Audit`。

| id | 研究 | 链接 | 原方案关键机制 | 本项目拟采用 | 本项目限制 / 不采用 |
|---|---|---|---|---|---|
| R1 | FinRL: A Deep Reinforcement Learning Library for Automated Stock Trading in Quantitative Finance | https://arxiv.org/abs/2011.09607 | 三层架构；market environment / agent / application；DQN/DDPG/PPO/SAC/A2C/TD3；交易成本、流动性、风险约束、backtesting | 采用 env-agent-backtest 分层、标准算法对照、交易成本、baseline 对照、reproducible artifacts | 不接 live trading；不使用任何真实 order/broker；算法输出不得直接进入 production |
| R2 | FinRL-Meta / Dynamic Datasets and Market Environments for Financial Reinforcement Learning | https://arxiv.org/abs/2304.13174 | DataOps、gym-style market environments、动态数据、survivorship bias / overfitting 风险、环境库 | 采用 data/env 分层、feature availability audit、overfit/seed stability audit | 不引入外部数据流水线改造；不 provider publish |
| R3 | A Deep Reinforcement Learning Framework for the Financial Portfolio Management Problem / EIIE | https://arxiv.org/abs/1706.10059 | EIIE 拓扑；Portfolio-Vector Memory；Online Stochastic Batch Learning；CNN/RNN/LSTM；explicit reward；action 为 portfolio weight vector | 采用 price tensor、previous allocation memory、transaction-cost-aware reward、CNN/RNN/LSTM 对照 | 不直接输出 target_weight 到 OrderIntent；crypto 高频设定不照搬 |
| R4 | EIIE stock-market replication/adaptation study | https://arxiv.org/abs/2409.08426 | 复现 EIIE；原 crypto 结果可复现；迁移到股票市场表现不如 crypto | 作为风险证据：论文机制迁移股票不保证提升，必须 OOS 审查 | 不把论文发表视为本项目必然收益证明 |
| R5 | PPO | https://arxiv.org/abs/1707.06347 | clipped policy update；trajectory rollout；actor-critic 稳定训练 | 若进入 PAL2/PAL3，用 PPO 作为 allocation/adapter policy 候选 | 不允许 strict_test 调参；不允许真实在线探索 |
| R6 | DDPG / continuous control | https://arxiv.org/abs/1509.02971 | actor 输出连续动作，critic 学 Q 值 | 若允许 simulation-only allocation vector，可作为连续 allocation baseline | 不输出真实 target_weight；不接 broker |
| R7 | Soft Actor-Critic | https://arxiv.org/abs/1801.01290 | entropy-regularized continuous control，提升探索稳定性 | PAL3+ 候选，用于 continuous allocation exploration | 初期不作为第一实现，避免复杂度过高 |
| R8 | Portfolio Choice with Transaction Costs: a User's Guide | https://arxiv.org/abs/1207.7330 | 交易成本导致再平衡 tradeoff/no-trade region | reward/backtest 必须 after-fee-tax；做 turnover/cost sensitivity | 不把低换手当主目标，仍 return-first |

PAL0 必须把每篇研究按以下字段审计：

```text
paper_mechanism
required_state
required_action
required_reward
training_method
transaction_cost_model
baseline_used_in_paper
reported_market / frequency
what_can_be_adopted
what_conflicts_with_current_contract
required_adapter_or_contract_change
risk_if_adapted_to_tw_stock
```

## 5. 合同决策：允许 simulation-only allocation diagnostic，不修改生产合同

EIIE / PGPortfolio / FinRL portfolio allocation 路线通常需要：

```text
portfolio allocation vector
previous portfolio vector
rebalance vector
```

这在语义上接近 target weight。当前项目策略/OrderIntent 边界禁止输出：

```text
target_position
target_weight
quantity
broker order
```

统筹决定：

```text
1. 生产合同暂不修改。
2. OrderIntent / StrategyRule production path 继续禁止 target_weight / target_position / quantity。
3. PAL 路线允许新增 simulation-only AllocationDiagnosticArtifact。
4. AllocationDiagnosticArtifact 只用于 readonly research replay，不得进入任何生产或交易 consumer。
```

原因：

```text
如果完全禁止 allocation vector，就无法真正适配 EIIE / FinRL / PGPortfolio 的核心机制，
只能退回旧 PRL 的 buy/sell/switch intent 近似。

但如果直接修改生产合同允许 target_weight，
又会把研究信号误解释为真实仓位或调仓指令，风险过高。
```

因此本路线采用隔离研究合同：

```text
AllocationDiagnosticArtifact
```

它可以包含：

```text
date
instrument
allocation_score
allocation_weight_diagnostic
previous_allocation_weight_diagnostic
rebalance_delta_diagnostic
cash_weight_diagnostic
source_policy
source_signal_artifact
source_state_tensor_artifact
simulation_only = true
readonly_research_only = true
production_allowed = false
forbidden_consumers
```

字段命名必须使用 `_diagnostic` 后缀，避免被误解为真实 target weight。

严格禁止 consumers：

```text
OrderIntentArtifact
StrategyRule production path
production replay / product default
frontend default
Agent prompt / Agent recommendation
broker / quick-trade / real order
provider publish / accepted latest switch
monitor scan / config / alerts
```

允许 consumers 仅限：

```text
PAL readonly research env
PAL readonly allocation replay
PAL validator / audit / review report
```

PAL0 必须设计：

```text
1. AllocationDiagnosticArtifact schema。
2. forbidden consumer audit。
3. negative golden samples，证明该 artifact 被 OrderIntent / Agent / broker consumer 读取时必须失败。
4. research-only adapter schema，用于 readonly replay 内部把 diagnostic allocation 转换成 simulated rebalance accounting。
```

PAL0 只能设计和审查合同，不得直接训练 allocation policy，不得运行收益 replay。

## 6. 数据与窗口

第一轮 qlib-only：

```text
train = 2023-01-01..2024-12-31
validation = 2025-01-01..2025-12-31
strict_test = 2026-01-01..2026-05-07, declared only
```

允许 state：

```text
1. qlib rank / score / raw_score / score_rank / full_qlib_rank。
2. price tensor: OHLCV / return / MA / volatility, past-only。
3. portfolio memory: previous diagnostic allocation or previous holdings, simulation-only。
4. transaction cost state, past-only。
5. market state, PIT-safe。
```

禁止：

```text
future_return
label
realized_pnl as feature
future price
same-day unavailable data
strict_test metrics
oracle action / oracle return as training label
```

## 7. 阶段计划

## PAL0: Paper Implementation Audit And Contract Adaptation Freeze

目标：

```text
把 FinRL / EIIE / PGPortfolio / PPO/DDPG/SAC 的关键机制转成项目可执行合同。
```

执行者必须：

```text
1. 阅读 R1-R8 原始论文或官方实现说明。
2. 输出 Paper Implementation Audit。
3. 按统筹决策设计 simulation-only AllocationDiagnosticArtifact。
4. 设计 forbidden consumers 与 research-only adapter 合同。
5. 设计 env/state/action/reward schema。
6. 设计 validator/golden samples。
7. 写 PAL0 execution report。
```

PAL0 不允许：

```text
训练模型
运行 validation收益结论
运行 strict_test
输出 OrderIntent
输出真实 target_weight / target_position / quantity / broker order
provider/latest/monitor/frontend/Agent/broker 扩权
```

PAL0 输出：

```text
data_tw/experiments/paper_aligned_portfolio_rl/pal0_paper_contract_audit/
  manifest.json
  paper_implementation_audit.csv
  contract_adaptation_decision.md
  allocation_diagnostic_schema.json
  research_only_allocation_replay_adapter_schema.json
  state_tensor_schema.json
  portfolio_memory_schema.json
  reward_schema.json
  forbidden_consumer_audit.csv
  validator_design.md
  golden_sample_design.md

docs/tw_portfolio_decision_model/POLICY_PAL0_PAPER_CONTRACT_AUDIT_EXECUTION_REPORT_CN.md
```

PAL0 通过条件：

```text
1. R1-R8 逐项审计完整。
2. 明确论文机制与本项目合同冲突。
3. AllocationDiagnosticArtifact schema 完整且字段使用 diagnostic 语义。
4. forbidden consumers 完整，且 negative golden samples 覆盖误用场景。
5. reviewer 能据此写 PAL1 work doc。
```

## PAL1: Allocation Env / Tensor / Memory Build

只有 PAL0 通过后允许。

目标：

```text
构建 paper-aligned environment，不训练策略。
```

必须输出：

```text
price_tensor_artifact
portfolio_memory_artifact
allocation_action_space_audit
baseline_parity
transaction_cost_audit
feature_available_at_audit
```

PAL1 不允许训练，不允许 strict_test。

PAL1 通过条件：

```text
baseline parity pass
feature PIT / available_at pass
allocation/rebalance cost calculation pass
validator/golden samples pass
```

## PAL2: Paper-aligned Full Training Feasibility

只有 PAL1 通过后允许。

目标：

```text
在 train 上运行完整或接近完整的 paper-aligned training，
用 validation 选择唯一 final policy/config。
```

候选实现顺序：

```text
1. EIIE-CNN with PVM, small universe topK。
2. EIIE-LSTM/RNN 对照。
3. PPO allocation policy。
4. DDPG/SAC continuous allocation diagnostic, if方案B被审查通过。
```

计算约束：

```text
如果 CPU 环境无法完整训练，执行者必须输出 training feasibility report：
estimated_runtime
episode_count
batch_count
checkpoint frequency
whether GPU is required
minimum viable training setting
```

PAL2 通过条件：

```text
validation return > baseline
seed stability pass
turnover/cost audit pass
concentration audit pass
not baseline clone
strict_test_used=false
```

若 validation 不过，不得 strict_test。

## PAL3: Strict-test Final Replay

只有 PAL2 validation 通过后才允许。

规则：

```text
1. strict_test 只 final-only。
2. 不得根据 strict_test 改参数。
3. strict_test return > baseline 才可写阶段通过。
4. 失败则 closure，不得同线反复试。
```

## PAL4: Optional qlib+orthogonal LTR Adapter

只有 qlib-only PAL3 通过后才允许另开。

注意：

```text
LTR 2023-2025 是训练窗口，不能把 2023-2025 LTR replay 当严格 OOS 策略证明。
```

## 8. 审查重点

审查者每轮必须检查：

```text
1. 是否真正按论文机制适配，而不是只换名继续 intent-level PRL。
2. 是否清楚处理 allocation vector 与 target_weight 禁令的冲突。
3. AllocationDiagnosticArtifact 是否 simulation-only 且 forbidden consumers 完整。
4. 是否没有 OrderIntent target_weight / target_position / quantity。
5. 是否 train/validation/strict_test 分离。
6. 是否没有 oracle label / future return / realized pnl feature。
7. 是否 return-first，但同时审计 turnover/cost/concentration。
8. 是否 seed stability 足够。
9. 是否 CPU 训练不足时诚实报告 feasibility，而不是用 lite run 代表论文方法失败。
```

## 9. 停止条件

必须停止并回到统筹：

```text
1. PAL0 无法给出安全的 allocation contract。
2. AllocationDiagnosticArtifact 被误接入 OrderIntent / Agent / frontend / broker。
3. feature available_at 或 PIT audit 失败。
4. validation 不超过 baseline，却要求 strict_test。
5. strict_test 被用于调参。
6. 训练只是 lite sanity，却声称完整论文方法失败或成功。
7. 输出 target_position / target_weight / quantity / broker order 到策略/OrderIntent。
```

## 10. PAL0 执行者命令

```text
你是执行者。请启动 PAL Paper-aligned Portfolio Allocation RL 主线 PAL0。

必须读取：
1. docs/tw_portfolio_decision_model/POLICY_PAL_PAPER_ALIGNED_PORTFOLIO_ALLOCATION_RL_MAINLINE_CN.md
2. docs/tw_portfolio_decision_model/POLICY_PRL1_R1_R_PARTICIPATION_CONSTRAINED_REPAIR_STAGE_SUMMARY_CN.md
3. docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md
4. docs/tw_modular_contracts/NEW_MODEL_AND_STRATEGY_DEVELOPER_GUIDE_CN.md
5. docs/tw_modular_contracts/MODEL_SIGNAL_CONTRACT_CN.md
6. docs/tw_modular_contracts/STRATEGY_RULE_CONTRACT_CN.md
7. docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md
8. docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md

本轮只做 PAL0：
- 阅读并审计 R1-R8 论文/实现机制；
- 输出 paper_implementation_audit.csv；
- 按统筹决策设计 simulation-only AllocationDiagnosticArtifact；
- 设计 state tensor / portfolio memory / reward / research-only adapter schema；
- 设计 forbidden consumer audit、validator、golden samples；
- 写 PAL0 execution report。

本轮禁止：
- 训练模型；
- 运行 validation收益结论；
- 运行 strict_test；
- 输出 OrderIntent；
- 输出真实 target_position / target_weight / quantity / broker order；
- provider/latest/monitor/frontend/Agent/broker 扩权。

artifact root:
data_tw/experiments/paper_aligned_portfolio_rl/pal0_paper_contract_audit/

执行报告：
docs/tw_portfolio_decision_model/POLICY_PAL0_PAPER_CONTRACT_AUDIT_EXECUTION_REPORT_CN.md
```

## 11. PAL0 审查者命令

```text
你是审查者。请审查 PAL0 执行报告是否符合 PAL 主线。

必须检查：
1. R1-R8 是否逐项审计；
2. 是否真正分析论文实现机制，而不是只写方向；
3. 是否明确 allocation vector 与项目 target_weight 禁令的冲突；
4. 是否按统筹决策给出 simulation-only AllocationDiagnosticArtifact；
5. forbidden consumers 与 negative golden samples 是否完整；
6. 是否未训练、未 replay收益、未 strict_test；
7. 是否没有 OrderIntent / target_position / target_weight / quantity / broker 输出；
8. 是否能据此写 PAL1 env/tensor/memory build 工作文档。

审查输出：
docs/tw_portfolio_decision_model/POLICY_PAL0_PAPER_CONTRACT_AUDIT_REVIEW_CN.md

如果 PAL0 通过，请写 PAL1 工作文档。
如果合同冲突无法安全解决，请 STOP 回到统筹。
```
