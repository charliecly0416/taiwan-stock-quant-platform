---
created_at: 2026-06-22
status: review_pass_ready_for_prl1_with_conditions
phase_reviewed: PRL0_ENV_ACTION_SPACE_ORACLE_AUDIT_FREEZE
mainline_doc: docs/tw_portfolio_decision_model/POLICY_PRL_PORTFOLIO_RL_MAINLINE_CN.md
execution_report: docs/tw_portfolio_decision_model/POLICY_PRL0_ENV_ORACLE_AUDIT_EXECUTION_REPORT_CN.md
artifact_root: data_tw/experiments/portfolio_rl_research/prl0_env_oracle_audit
next_phase: PRL1_SIMULATION_RL_QLIB_ONLY
next_work_document_included: true
verdict: PASS_READY_FOR_PRL1_SIMULATION_RL_WORK_DOCUMENT_WITH_CONDITIONS
readonly_only: true
simulation_only: true
production_allowed: false
strict_test_authorized: false
rl_training_authorized_by_prl0_review: true
not_target_position: true
not_target_weight: true
not_order: true
no_provider_publish: true
no_accepted_latest_switch: true
no_monitor_write: true
no_broker: true
---

# PRL0 Env / Oracle Audit 审查报告与 PRL1 工作文档

## 1. 审查结论

结论：

```text
PASS_READY_FOR_PRL1_SIMULATION_RL_WORK_DOCUMENT_WITH_CONDITIONS
```

PRL0 满足主线进入 PRL1 的核心门槛：

```text
baseline parity: PASS
oracle upper bound train > baseline: PASS
random/heuristic executable audit: PASS
action space covers baseline and non-baseline: PASS
forbidden feature audit: PASS
validator/golden samples: PASS
strict_test_used: false
rl_training_performed: false
```

允许进入：

```text
PRL1: Simulation RL qlib-only
```

本审查不授权：

```text
strict_test / PRL4
PRL2 supervised imitation
PRL3 offline RL
PRL5 qlib + orthogonal LTR adapter
production/default/Agent/provider/broker/monitor/frontend 扩权
```

## 2. 核心证据

### 2.1 Baseline parity

`baseline_parity_metrics.csv`：

```text
train:
baseline_return = 2.41885797
prl0_replay_return = 2.41885797
absolute_diff = 0.0
action_count = 885

validation:
baseline_return = 0.95376753
prl0_replay_return = 0.95376753
absolute_diff = 0.0
action_count = 436
```

评价：通过。PRL env 的 baseline replay 与既有 qlib baseline 精确一致，后续 PRL1 评估具备可比基础。

### 2.2 Oracle upper bound

`oracle_upper_bound_train.csv`：

```text
oracle train return = 474.42807854
baseline train return = 2.41885797
excess_return = 472.00922057
oracle_diagnostic_uses_future_prices = True
oracle_used_for_training = False
strict_test_used = False
executable_action_ratio = 0.91240876
```

评价：通过，但只能解释为 action space capacity diagnostic。该 oracle 使用未来价格，不是 PIT-safe policy，也不能作为 PRL1 的 imitation label、reward shaping、checkpoint selection 或 validation 预期收益证据。

### 2.3 Random / heuristic rollout

```text
random train return = 1.78398440
random excess_return = -0.63487357
random executable_action_ratio = 0.96328029

heuristic train return = -0.02507377
heuristic excess_return = -2.44393174
heuristic executable_action_ratio = 1.0
```

评价：可执行性通过，但 random/heuristic 均未超过 baseline。这意味着 PRL1 的正当性来自“动作空间存在未来信息 oracle 上界 + env 可执行”，不是来自已有 PIT-safe heuristic 已证明收益增量。PRL1 必须按高风险探索处理。

### 2.4 Action coverage

`action_coverage_audit.csv` 显示 A0-A7 均 covered，且：

```text
baseline_action_in_space = True
non_baseline_action_in_space = True
```

`executable_action_audit.csv`：

```text
oracle executable_action_ratio = 0.91240876
random executable_action_ratio = 0.96328029
heuristic executable_action_ratio = 1.0
```

评价：通过。动作空间足够覆盖 baseline 与 non-baseline，并且 invalid action 比例不高。

## 3. Findings

### Critical

无。

### High

无。

### Medium

M1. Oracle 使用未来价格，只能作为 capacity diagnostic。

执行报告已正确标记：

```text
oracle_diagnostic_uses_future_prices = True
oracle_used_for_training = False
```

因此 PRL1 不得：

```text
用 oracle action 做 supervised imitation
用 oracle return 做训练 label
用 oracle trajectory 预训练 policy
把 oracle upper bound 当作可达到收益预期
把 oracle 作为 validation selection 依据
```

M2. PRL0 没有 PIT-safe heuristic 正收益证据。

random 和 heuristic rollout 均低于 baseline。PRL0 仍可通过，因为主线只要求 train-only oracle upper bound 高于 baseline、rollout 可执行、action coverage 充分；但 PRL1 必须承认这是高风险 simulation RL 探索，不能把 PRL0 解释为已有可学习策略雏形。

M3. PRL1 必须防 baseline clone。

action space 包含 `A1_execute_baseline` 是 baseline parity 的必要条件，但后续 policy 可能退化为 baseline clone。PRL1 必须输出：

```text
baseline_action_ratio
non_baseline_action_ratio
active_action_return_contribution
action_template_distribution
```

如果 validation 只是复现 baseline 或主要依赖 `A1_execute_baseline`，不得通过进入 strict_test。

### Low

L1. schema 是 v1 级别，足以进入 PRL1，但 PRL1 需补充更细 available_at 证据。

`state_feature_schema.json` 声明 PIT-safe，但 PRL1 训练前应把每类 price/history/market feature 的 `asof / available_at / lookback_window / decision_time` 写入 manifest 或 feature audit。

## 4. 主线符合性核查

| 核查项 | 结论 | 说明 |
|---|---|---|
| 是否完整读取主线/PE closure/合同 | PASS | 执行报告列明已读取 |
| Research Adoption Audit 是否覆盖 R1-R8 | PASS | 覆盖 FinRL/EIIE/PPO/DQN/CQL/IQL/DT/交易成本 |
| Env/state/action/reward schema | PASS | 四类 schema 均产出 |
| baseline parity | PASS | train/validation absolute_diff=0 |
| oracle upper bound | PASS_WITH_CONDITION | 高于 baseline，但为未来价格 diagnostic only |
| random/heuristic rollout 可执行 | PASS | 可执行率均 > 0.91 |
| action coverage | PASS | baseline 与 non-baseline 均 in-space |
| forbidden feature audit | PASS | 未见 forbidden state/output |
| validator/golden samples | PASS | failed_count=0 |
| 是否未训练 RL | PASS | `rl_training_performed=false` |
| 是否未运行 strict_test | PASS | `strict_test_used=false` |
| 是否无生产/交易扩权 | PASS | 未见 provider/latest/monitor/frontend/Agent/broker 扩权 |

## 5. Safety Boundary

未发现：

```text
strict_test replay
PPO/DQN/A2C training in PRL0
LTR usage
provider publish / accepted latest switch
monitor write
frontend default switch
Agent / OpenAI integration
broker / quick-trade / order
target_position / target_weight / quantity
future_return / label / realized_pnl as policy state
```

允许上下文：

```text
forbidden lists / negative golden samples / oracle diagnostic future prices
```

其中 oracle future price 只允许作为 train-only upper-bound diagnostic，不允许进入 PRL1 policy state 或训练标签。

## 6. PRL1 工作文档

### 6.1 阶段名称

```text
PRL1_SIMULATION_RL_QLIB_ONLY
```

### 6.2 阶段目标

在 PRL0 通过的 `PortfolioDecisionEnv v1` 上，只使用 frozen qlib-only signal 和 train window 训练 compact discrete action-template policy，并用 validation 选择唯一 final policy/config/checkpoint。

本阶段只回答：

```text
PPO/A2C/DQN 类 simulation RL 是否能在 validation 上 after-fee-tax return 超过 baseline，
且不是 baseline clone、不是低参与/no_action、不是单股/单日偶然贡献。
```

### 6.3 必须读取

执行者必须读取：

```text
docs/tw_portfolio_decision_model/POLICY_PRL_PORTFOLIO_RL_MAINLINE_CN.md
docs/tw_portfolio_decision_model/POLICY_PRL0_ENV_ORACLE_AUDIT_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_PRL0_ENV_ORACLE_AUDIT_EXECUTION_REPORT_CN.md
docs/tw_portfolio_decision_model/POLICY_PRL_PORTFOLIO_RL_MAINLINE_FEASIBILITY_ANALYSIS_CN.md
docs/tw_portfolio_decision_model/POLICY_PE1_REPAIR_QLIB_ONLY_ACTIVE_POLICY_SEARCH_REVIEW_CN.md
docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md
docs/tw_modular_contracts/MODEL_SIGNAL_CONTRACT_CN.md
docs/tw_modular_contracts/STRATEGY_RULE_CONTRACT_CN.md
docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md
docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md
.agents/skills/coordinator-executor-reviewer-workflow/SKILL.md
.agents/skills/tw-stock-safety-boundary-review/SKILL.md
```

### 6.4 输入 artifact

必须使用：

```text
data_tw/experiments/portfolio_rl_research/prl0_env_oracle_audit/manifest.json
data_tw/experiments/portfolio_rl_research/prl0_env_oracle_audit/env_schema.json
data_tw/experiments/portfolio_rl_research/prl0_env_oracle_audit/state_feature_schema.json
data_tw/experiments/portfolio_rl_research/prl0_env_oracle_audit/action_space_schema.json
data_tw/experiments/portfolio_rl_research/prl0_env_oracle_audit/reward_schema.json
data_tw/artifacts/signals/frozen_qlib_2018_2022/r1_legacy_signal_adapter_20260616/manifest.json
```

禁止把以下 artifact 当训练标签或 imitation dataset：

```text
oracle_upper_bound_train.csv
```

该文件只能用于说明 action space capacity。

### 6.5 数据窗口

固定：

```text
train = 2023-01-01..2024-12-31
validation = 2025-01-01..2025-12-31
strict_test = 2026-01-01..2026-05-07
```

PRL1 使用规则：

```text
train: RL training, rollout buffer, reward curve, checkpoint proposal.
validation: algorithm/config/checkpoint final selection.
strict_test: 不运行、不读取、不评估、不选择。
```

### 6.6 允许算法

允许：

```text
PPO categorical policy over compact action templates
A2C lightweight actor-critic baseline
DQN / Double-DQN fixed discrete action-template comparison
```

建议首轮优先：

```text
1. PPO categorical
2. A2C lightweight comparison
3. DQN/Double-DQN as optional fixed-action baseline
```

不得执行：

```text
CQL
IQL
Decision Transformer
offline RL
supervised imitation from oracle
qlib/LTR retraining
Family D / regime route expansion
```

### 6.7 必须记录的训练控制

PRL1 必须输出：

```text
algorithm
config_id
random_seed
seed_count
episode_count
train_reward_curve
train_episode_return
validation_evaluation_count
checkpoint_selection_rule
final_selected_checkpoint
```

最低 seed 要求：

```text
至少 3 个 seed。
报告 mean / std / best / worst seed。
不得只选 best seed 作为唯一结论。
```

validation 使用限制：

```text
记录 validation 被评估次数。
不得根据 validation 结果反复扩参数空间。
若 validation 反复被用于搜索，应报告 overfit risk，不能直接进入 strict_test。
```

### 6.8 必须产出 artifact

artifact 根目录：

```text
data_tw/experiments/portfolio_rl_research/prl1_simulation_rl_qlib_only/
```

必须产出：

```text
manifest.json
rl_training_config_grid.csv
train_reward_curve.csv
train_episode_metrics.csv
validation_episode_metrics.csv
validation_selection_audit.csv
seed_stability_audit.csv
action_template_distribution.csv
baseline_clone_audit.csv
participation_audit.csv
trade_contribution_audit.csv
concentration_audit.csv
forbidden_feature_audit.csv
validator_report.json
golden_samples_report.json
```

建议产出：

```text
selected_policy_config.json
selected_policy_decisions_train.jsonl
selected_policy_decisions_validation.jsonl
selected_order_intents_train.jsonl
selected_order_intents_validation.jsonl
validation_replay_result_summary.json
```

禁止产出：

```text
strict_test replay metrics
strict_test policy decisions
strict_test order intents
production registry/default changes
```

### 6.9 必须通过的 PRL1 gate

全部满足才可建议进入后续 strict-test final replay 阶段：

```text
validation policy net_return_after_fee_tax > validation baseline
validation excess_return > 0
participation_ratio >= 0.85
action_count_ratio >= 0.80
non_baseline_action_ratio > 0
policy 不得主要退化为 A1_execute_baseline
policy 不得靠 no_action / low participation 获得改善
收益不是单一股票/单日极端贡献
seed mean 或至少多数 seed 不显著低于 baseline
validator_report pass
golden_samples_report pass
forbidden_feature_audit pass
strict_test_used=false
```

审查者不会接受以下通过理由：

```text
best seed validation 超过 baseline，但 mean/worst seed 崩坏
低换手/低回撤好于 baseline，但 return 低于 baseline
policy 几乎只执行 A1_execute_baseline
policy 使用 oracle future price action/label
validation 经过过多轮试探后才过线
```

### 6.10 PRL1 失败条件

任一情况出现，PRL1 不得进入 strict_test：

```text
validation policy return <= baseline
多数 seed 低于 baseline 且无解释
improvement 来自 no_action / low participation
improvement 来自单一股票或单日极端贡献
baseline clone
strict_test 被读取或运行
oracle_upper_bound_train 被用于训练/label/imitation
future_return / realized_pnl / label 进入 state
target_weight / target_position / quantity / broker order 输出
validator/golden samples fail
```

失败时 recommendation 只能是：

```text
STOP_OR_PRL1_REPAIR_WITH_COORDINATOR_DECISION
```

### 6.11 执行报告

执行报告路径：

```text
docs/tw_portfolio_decision_model/POLICY_PRL1_SIMULATION_RL_QLIB_ONLY_EXECUTION_REPORT_CN.md
```

报告必须包含：

```text
1. Scope 与非目标确认
2. Documents / Contracts / Skills Read
3. PRL0 artifact input summary
4. Algorithm/config/seed/episode_count
5. Train reward curve and episode metrics
6. Validation selection audit
7. Seed stability audit
8. Action distribution / baseline clone audit
9. Participation / no_action / turnover audit
10. Trade contribution and concentration audit
11. Forbidden feature/action audit
12. Validator/golden sample results
13. Files changed / artifacts produced
14. Recommendation
```

允许 recommendation：

```text
PASS_READY_FOR_PRL4_STRICT_TEST_FINAL_REPLAY_REVIEWER_DECISION
STOP_OR_PRL1_REPAIR_WITH_COORDINATOR_DECISION
```

注意：即使 PRL1 validation 通过，执行者也不能自行运行 strict_test。必须等待审查者审查 PRL1 后再决定是否授权后续 strict-test 阶段。

## 7. 给执行者的 PRL1 命令

```text
你是执行者。请严格执行 PRL Portfolio RL 主线 PRL1：
PRL1_SIMULATION_RL_QLIB_ONLY。

必须读取：
1. docs/tw_portfolio_decision_model/POLICY_PRL_PORTFOLIO_RL_MAINLINE_CN.md
2. docs/tw_portfolio_decision_model/POLICY_PRL0_ENV_ORACLE_AUDIT_REVIEW_CN.md
3. docs/tw_portfolio_decision_model/POLICY_PRL0_ENV_ORACLE_AUDIT_EXECUTION_REPORT_CN.md
4. docs/tw_portfolio_decision_model/POLICY_PRL_PORTFOLIO_RL_MAINLINE_FEASIBILITY_ANALYSIS_CN.md
5. docs/tw_portfolio_decision_model/POLICY_PE1_REPAIR_QLIB_ONLY_ACTIVE_POLICY_SEARCH_REVIEW_CN.md
6. docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md
7. docs/tw_modular_contracts/MODEL_SIGNAL_CONTRACT_CN.md
8. docs/tw_modular_contracts/STRATEGY_RULE_CONTRACT_CN.md
9. docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md
10. docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md

本轮只允许：
- qlib-only frozen signal；
- PRL0 PortfolioDecisionEnv v1；
- train=2023-01-01..2024-12-31 训练；
- validation=2025-01-01..2025-12-31 选择；
- PPO/A2C/DQN over compact discrete action templates；
- 输出 PRL1 artifacts 和 execution report。

本轮禁止：
- 运行 strict_test；
- 使用 oracle_upper_bound_train.csv 做训练 label / imitation / reward shaping；
- 执行 supervised/offline RL、CQL、IQL、Decision Transformer；
- 使用 LTR；
- 输出 target_position/target_weight/quantity/broker order；
- provider/latest/monitor/frontend default/Agent/broker 扩权；
- 用低换手/低回撤或 baseline clone 代替 validation return-first 通过。

artifact 根目录：
data_tw/experiments/portfolio_rl_research/prl1_simulation_rl_qlib_only/

执行报告：
docs/tw_portfolio_decision_model/POLICY_PRL1_SIMULATION_RL_QLIB_ONLY_EXECUTION_REPORT_CN.md

若 validation 未严格超过 baseline，或 seed 稳定性/action attribution/concentration/validator 任一核心门槛失败，必须报告 STOP_OR_PRL1_REPAIR_WITH_COORDINATOR_DECISION，不得进入 strict_test。
```

## 8. 最终意见

PRL0 可以通过。它证明了：

```text
1. env baseline parity 成立；
2. action space 容量上存在超过 baseline 的 train-only diagnostic oracle；
3. compact action templates 可执行；
4. PRL0 没有越过 readonly / no-strict-test / no-RL-training 边界。
```

但 PRL1 必须以高风险探索执行，因为：

```text
random/heuristic 均低于 baseline；
oracle 使用未来价格，只能证明上界容量；
深度 RL 在本项目窗口上容易过拟合。
```

因此审查者后续必须严格执行：

```text
validation return-first
multi-seed stability
no baseline clone
no oracle label leakage
no strict_test before reviewer approval
```
