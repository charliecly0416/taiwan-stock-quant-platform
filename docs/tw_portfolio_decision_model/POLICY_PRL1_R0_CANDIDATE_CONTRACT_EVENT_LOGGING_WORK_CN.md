---
created_at: 2026-06-22
status: reviewer_next_work_document
phase: PRL1_R0_CANDIDATE_LEVEL_CONTRACT_AND_EVENT_LOGGING_REPAIR
mainline_doc: docs/tw_portfolio_decision_model/POLICY_PRL_PORTFOLIO_RL_MAINLINE_CN.md
coordinator_opinion: docs/tw_portfolio_decision_model/POLICY_PRL1_D_COORDINATOR_OPINION_FOR_REVIEWER_CN.md
previous_review: docs/tw_portfolio_decision_model/POLICY_PRL1_D_LEARNABILITY_ACTION_ATTRIBUTION_REVIEW_CN.md
previous_execution_report: docs/tw_portfolio_decision_model/POLICY_PRL1_D_LEARNABILITY_ACTION_ATTRIBUTION_EXECUTION_REPORT_CN.md
artifact_root: data_tw/experiments/portfolio_rl_research/prl1_r0_candidate_contract_event_logging
strict_test_authorized: false
prl1_r_training_authorized: false
prl2_authorized: false
prl3_authorized: false
production_allowed: false
readonly_only: true
simulation_only: true
not_order: true
not_target_position: true
not_target_weight: true
---

# PRL1-R0 Candidate-level Contract And Event Logging Repair 工作文档

## 1. 阶段定位

统筹已明确：

```text
docs/tw_portfolio_decision_model/POLICY_PRL1_D_COORDINATOR_OPINION_FOR_REVIEWER_CN.md
recommended_next = PRL1_R0_CANDIDATE_LEVEL_CONTRACT_AND_EVENT_LOGGING_REPAIR
```

本阶段是 PRL1-R 的前置修复阶段，不是收益训练阶段。

本阶段只授权：

```text
1. 定义 bounded candidate-level / pair-level action contract。
2. 补齐 env/replay event-level NAV contribution logging。
3. 产出 exact attribution audits。
4. 增加 no-training validator / golden samples。
```

本阶段不授权：

```text
PRL1-R candidate-level policy training
PPO / DQN / A2C / supervised policy training
PRL2 / PRL3
strict_test
qlib+LTR
production/default/Agent/provider/broker/monitor/frontend 扩权
```

## 2. 背景事实

PRL1-D 诊断给出继续研究的正信号：

```text
baseline imitation validation_accuracy = 0.98760331
baseline imitation validation_macro_f1 = 0.86046512

oracle top30 / high score / not_held / above_ma20:
positive_advantage_ratio = 0.83137830

oracle top30 / high score / not_held / below_ma20:
positive_advantage_ratio = 0.82857143
```

但 PRL1-D 也暴露关键缺口：

```text
single_day_extreme_share 无法精确重构；
top_loss_date / top_loss_symbol = aggregate_only_v1；
fee/tax contribution by action 不完整；
train template count = 0；
当前 PRL1 lite logs 不足以支撑训练后的精确 attribution。
```

因此 PRL1-R0 的目标是补合同和日志，不是训练。

## 3. 阶段目标

PRL1-R0 只解决两个问题：

```text
1. 将 action 表达从 coarse template 升级为 bounded candidate-level / pair-level contract。
2. 补齐 env/replay event-level logging，让后续训练结果可以按 action/candidate/pair 精确归因。
```

PRL1-R0 不要求收益超过 baseline，不训练最终策略，不运行 strict_test。

## 4. 必须读取

执行者开始前必须读取：

```text
docs/tw_portfolio_decision_model/POLICY_PRL_PORTFOLIO_RL_MAINLINE_CN.md
docs/tw_portfolio_decision_model/POLICY_PRL1_D_COORDINATOR_OPINION_FOR_REVIEWER_CN.md
docs/tw_portfolio_decision_model/POLICY_PRL1_R0_CANDIDATE_CONTRACT_EVENT_LOGGING_WORK_CN.md
docs/tw_portfolio_decision_model/POLICY_PRL1_D_LEARNABILITY_ACTION_ATTRIBUTION_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_PRL1_D_LEARNABILITY_ACTION_ATTRIBUTION_EXECUTION_REPORT_CN.md
docs/tw_portfolio_decision_model/POLICY_PRL1_SIMULATION_RL_QLIB_ONLY_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_PRL1_SIMULATION_RL_QLIB_ONLY_EXECUTION_REPORT_CN.md
docs/tw_portfolio_decision_model/POLICY_PRL0_ENV_ORACLE_AUDIT_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_PRL0_ENV_ORACLE_AUDIT_EXECUTION_REPORT_CN.md
docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md
docs/tw_modular_contracts/MODEL_SIGNAL_CONTRACT_CN.md
docs/tw_modular_contracts/STRATEGY_RULE_CONTRACT_CN.md
docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md
docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md
.agents/skills/coordinator-executor-reviewer-workflow/SKILL.md
.agents/skills/tw-stock-safety-boundary-review/SKILL.md
```

## 5. 输入 artifact

允许读取：

```text
data_tw/experiments/portfolio_rl_research/prl0_env_oracle_audit/manifest.json
data_tw/experiments/portfolio_rl_research/prl0_env_oracle_audit/env_schema.json
data_tw/experiments/portfolio_rl_research/prl0_env_oracle_audit/state_feature_schema.json
data_tw/experiments/portfolio_rl_research/prl0_env_oracle_audit/action_space_schema.json
data_tw/experiments/portfolio_rl_research/prl0_env_oracle_audit/reward_schema.json
data_tw/experiments/portfolio_rl_research/prl1_d_learnability_action_attribution/candidate_level_redesign_proposal.md
data_tw/experiments/portfolio_rl_research/prl1_d_learnability_action_attribution/candidate_level_state_action_schema_draft.json
data_tw/experiments/portfolio_rl_research/prl1_d_learnability_action_attribution/candidate_level_risk_and_gate.md
data_tw/artifacts/signals/frozen_qlib_2018_2022/r1_legacy_signal_adapter_20260616/manifest.json
```

`oracle_upper_bound_train.csv` 如需参考，只能用于诊断背景，不得进入训练、label、reward shaping 或 selection。

## 6. 数据窗口

固定窗口：

```text
train = 2023-01-01..2024-12-31
validation = 2025-01-01..2025-12-31
strict_test = 2026-01-01..2026-05-07
```

PRL1-R0 使用规则：

```text
train: contract/schema/event logging sample and attribution audit。
validation: contract/schema/event logging sample and attribution audit。
strict_test: 不运行、不读取、不评估、不选择。
```

## 7. 必做任务

### 7.1 Candidate-level Action Contract

定义候选级 action schema：

```text
buy_action:
  state + candidate_stock -> buy logit/value

sell_action:
  state + holding_stock -> sell logit/value

switch_action:
  state + holding_stock + candidate_stock -> switch logit/value
```

动作边界必须写入 schema：

```text
buy_candidates: qlib top20 by candidate_rank / buy_score
sell_candidates: current holdings only, max 10
switch_pairs: top5 weak holdings x top10 candidates, cap 20 pairs/day
max_buy_count <= 3
max_sell_count <= 3
max_switch_pair_count <= 3
```

输出只能是 intent-level action slate：

```text
date
action_type
candidate_instrument
holding_instrument, optional
reason_code
source_policy
```

禁止输出：

```text
target_position
target_weight
quantity
execution_price
execution_date
broker_order_id
cash amount
quick_trade
```

最低产出：

```text
candidate_action_schema.json
pair_action_schema.json
candidate_action_space_audit.csv
```

`candidate_action_space_audit.csv` 至少包含：

```text
split
date_count
avg_buy_candidates_per_day
avg_sell_candidates_per_day
avg_switch_pairs_per_day
max_switch_pairs_per_day
candidate_cap_pass
baseline_action_representable
non_baseline_action_representable
invalid_candidate_reason_count
```

### 7.2 Event-level NAV Contribution Logging

必须补齐 env/replay 事件级日志 schema，并产出样例。

事件日志至少包括：

```text
date
config_id
episode_id
action_id
action_type
template_id, optional
candidate_instrument
holding_instrument, optional
pre_nav
post_nav
nav_delta
reward
fee_tax
invalid_action_flag
invalid_action_reason
baseline_reference_action_id, optional
```

注意：

```text
ReplayResult 可以有历史模拟成交结果；
但 ActionDecision / OrderIntent 仍不得输出 quantity / execution_price / target_position / target_weight。
```

最低产出：

```text
event_level_nav_log_schema.json
event_level_nav_log_sample.csv
```

`event_level_nav_log_sample.csv` 必须同时覆盖：

```text
train split
validation split
buy action
sell action
switch action
hold/skip action
invalid action example, if available
fee_tax non-null examples
```

### 7.3 Exact Attribution Audits

PRL1-R0 必须能精确输出：

```text
per_action_contribution.csv
per_candidate_contribution.csv
per_pair_contribution.csv
single_day_extreme_contribution.csv
top_gain_loss_events.csv
fee_tax_by_action.csv
invalid_action_audit.csv
```

这些文件必须支持：

```text
exact single_day_extreme_share
top_loss_date
top_loss_symbol
top_gain_date
top_gain_symbol
fee/tax contribution by action type
train/validation attribution, both non-empty
```

最低字段要求：

`per_action_contribution.csv`：

```text
split
action_type
action_id
candidate_instrument
holding_instrument
nav_delta
reward
fee_tax
valid_action
```

`per_candidate_contribution.csv`：

```text
split
candidate_instrument
action_type
action_count
cumulative_nav_delta
mean_reward
fee_tax
top_gain_date
top_loss_date
```

`per_pair_contribution.csv`：

```text
split
holding_instrument
candidate_instrument
pair_count
cumulative_nav_delta
mean_reward
fee_tax
top_gain_date
top_loss_date
```

`single_day_extreme_contribution.csv`：

```text
split
date
daily_nav_delta
total_abs_nav_delta
single_day_extreme_share
top_action_id
top_instrument
```

`top_gain_loss_events.csv`：

```text
split
rank_type
date
action_id
action_type
candidate_instrument
holding_instrument
nav_delta
reward
fee_tax
```

`fee_tax_by_action.csv`：

```text
split
action_type
action_count
total_fee_tax
avg_fee_tax
fee_tax_share
```

`invalid_action_audit.csv`：

```text
split
action_type
invalid_action_count
invalid_action_reason
invalid_action_ratio
```

### 7.4 No-training Validator

PRL1-R0 validator 必须确认：

```text
no_rl_training = true
no_supervised_policy_training = true
strict_test_used = false
oracle_used_for_training = false
oracle_used_for_reward_shaping = false
candidate_action_contract_exists = true
event_level_nav_logging_exists = true
exact_single_day_extreme_share_available = true
train_attribution_non_empty = true
validation_attribution_non_empty = true
no_target_position = true
no_target_weight = true
no_quantity = true
no_broker_order = true
```

## 8. 必须产出 artifact

artifact 根目录：

```text
data_tw/experiments/portfolio_rl_research/prl1_r0_candidate_contract_event_logging/
```

必须产出：

```text
manifest.json
candidate_action_schema.json
pair_action_schema.json
event_level_nav_log_schema.json
candidate_action_space_audit.csv
event_level_nav_log_sample.csv
per_action_contribution.csv
per_candidate_contribution.csv
per_pair_contribution.csv
single_day_extreme_contribution.csv
top_gain_loss_events.csv
fee_tax_by_action.csv
invalid_action_audit.csv
forbidden_feature_audit.csv
validator_report.json
golden_samples_report.json
```

执行报告：

```text
docs/tw_portfolio_decision_model/POLICY_PRL1_R0_CANDIDATE_CONTRACT_EVENT_LOGGING_EXECUTION_REPORT_CN.md
```

## 9. Validator / Golden Sample 要求

validator 至少检查：

```text
1. candidate-level / pair-level action schema 完整。
2. event-level NAV log schema 完整。
3. event-level sample 覆盖 train 和 validation。
4. per_action / per_candidate / per_pair contribution 非空。
5. exact single_day_extreme_share 可计算。
6. top_gain_loss_events 有 date / symbol / action。
7. fee_tax_by_action 非空。
8. invalid_action_audit 非空或显式说明无 invalid action。
9. no_rl_training=true。
10. no_supervised_policy_training=true。
11. strict_test_used=false。
12. oracle_used_for_training=false。
13. oracle_used_for_reward_shaping=false。
14. no target_position / target_weight / quantity / broker_order。
```

golden samples 至少覆盖：

```text
positive_candidate_action_schema
positive_pair_action_schema
positive_event_level_nav_log
positive_exact_single_day_extreme_share
positive_top_gain_loss_event
positive_fee_tax_by_action
negative_target_weight_output
negative_quantity_output
negative_broker_order_output
negative_strict_test_usage
negative_oracle_training_label
negative_rl_training_started
```

## 10. 禁止事项

本阶段禁止：

```text
1. 训练 PPO / DQN / A2C / supervised policy。
2. 运行 strict_test。
3. 使用 oracle action/return 做训练、模仿、reward shaping。
4. 进入 PRL2 / PRL3。
5. 使用 qlib+orthogonal LTR。
6. provider/latest/monitor/frontend/Agent/broker 扩权。
7. 输出 target_position / target_weight / quantity / broker order。
8. 将 event-level historical simulation 字段反向写入 ActionDecision / OrderIntent。
9. 将本阶段 attribution 结果写成收益承诺或投资建议。
```

## 11. 通过 / 停止判断

PRL1-R0 通过不等于可以进入 strict_test，也不等于可以训练收益策略。它只说明后续训练具备可审查的日志和合同基础。

允许的 recommendation：

```text
PASS_READY_FOR_COORDINATOR_DECIDE_PRL1_R1_CANDIDATE_POLICY_TRAINING
FAIL_NEEDS_PRL1_R0_REPAIR
STOP_CLOSE_PRL_Q_ONLY_BRANCH
STOP_FOR_CONTRACT_OR_LEAKAGE_VIOLATION
```

PRL1-R0 通过条件：

```text
1. candidate-level / pair-level action schema 完整。
2. event-level NAV logging 可重构每个 action 的 reward / nav_delta / fee_tax。
3. exact single_day_extreme_share 可计算。
4. top_gain_loss_events 可定位 date / symbol / action。
5. train 和 validation attribution 均非空。
6. validator / golden samples pass。
7. strict_test 未使用。
8. oracle 未用于训练、模仿或 reward shaping。
9. 所有输出保持 intent-only，不含 target/quantity/broker 字段。
```

若无法补齐 event-level attribution，应推荐：

```text
STOP_CLOSE_PRL_Q_ONLY_BRANCH
```

避免继续训练不可解释、不可审计的策略模型。

## 12. 给执行者的命令

```text
你是执行者。请执行 PRL1-R0 Candidate-level Contract And Event Logging Repair。

必须读取：
1. docs/tw_portfolio_decision_model/POLICY_PRL_PORTFOLIO_RL_MAINLINE_CN.md
2. docs/tw_portfolio_decision_model/POLICY_PRL1_D_COORDINATOR_OPINION_FOR_REVIEWER_CN.md
3. docs/tw_portfolio_decision_model/POLICY_PRL1_R0_CANDIDATE_CONTRACT_EVENT_LOGGING_WORK_CN.md
4. docs/tw_portfolio_decision_model/POLICY_PRL1_D_LEARNABILITY_ACTION_ATTRIBUTION_REVIEW_CN.md
5. docs/tw_portfolio_decision_model/POLICY_PRL1_D_LEARNABILITY_ACTION_ATTRIBUTION_EXECUTION_REPORT_CN.md
6. docs/tw_portfolio_decision_model/POLICY_PRL1_SIMULATION_RL_QLIB_ONLY_REVIEW_CN.md
7. docs/tw_portfolio_decision_model/POLICY_PRL1_SIMULATION_RL_QLIB_ONLY_EXECUTION_REPORT_CN.md
8. docs/tw_portfolio_decision_model/POLICY_PRL0_ENV_ORACLE_AUDIT_REVIEW_CN.md
9. docs/tw_portfolio_decision_model/POLICY_PRL0_ENV_ORACLE_AUDIT_EXECUTION_REPORT_CN.md
10. docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md
11. docs/tw_modular_contracts/MODEL_SIGNAL_CONTRACT_CN.md
12. docs/tw_modular_contracts/STRATEGY_RULE_CONTRACT_CN.md
13. docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md
14. docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md

本轮只允许：
- candidate-level / pair-level action contract；
- event-level NAV contribution logging；
- exact attribution audits；
- forbidden feature audit、validator、golden samples；
- 写执行报告。

本轮禁止：
- 训练 PPO/DQN/A2C/supervised policy；
- 运行 strict_test；
- 使用 oracle action/return 做训练、模仿或 reward shaping；
- 进入 PRL2/PRL3；
- 使用 LTR；
- 输出 target_position/target_weight/quantity/broker order；
- provider/latest/monitor/frontend/Agent/broker 扩权。

artifact 根目录：
data_tw/experiments/portfolio_rl_research/prl1_r0_candidate_contract_event_logging/

执行报告：
docs/tw_portfolio_decision_model/POLICY_PRL1_R0_CANDIDATE_CONTRACT_EVENT_LOGGING_EXECUTION_REPORT_CN.md

recommendation 只能从以下选择：
- PASS_READY_FOR_COORDINATOR_DECIDE_PRL1_R1_CANDIDATE_POLICY_TRAINING
- FAIL_NEEDS_PRL1_R0_REPAIR
- STOP_CLOSE_PRL_Q_ONLY_BRANCH
- STOP_FOR_CONTRACT_OR_LEAKAGE_VIOLATION
```
