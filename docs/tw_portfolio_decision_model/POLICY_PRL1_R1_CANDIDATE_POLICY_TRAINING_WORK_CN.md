---
created_at: 2026-06-22
status: reviewer_next_work_document
phase: PRL1_R1_CANDIDATE_POLICY_TRAINING
mainline_doc: docs/tw_portfolio_decision_model/POLICY_PRL_PORTFOLIO_RL_MAINLINE_CN.md
coordinator_opinion: docs/tw_portfolio_decision_model/POLICY_PRL1_R0_COORDINATOR_OPINION_FOR_REVIEWER_CN.md
previous_review: docs/tw_portfolio_decision_model/POLICY_PRL1_R0_CANDIDATE_CONTRACT_EVENT_LOGGING_REVIEW_CN.md
previous_execution_report: docs/tw_portfolio_decision_model/POLICY_PRL1_R0_CANDIDATE_CONTRACT_EVENT_LOGGING_EXECUTION_REPORT_CN.md
artifact_root: data_tw/experiments/portfolio_rl_research/prl1_r1_candidate_policy_training
prl1_r1_authorized: true
strict_test_authorized: false
prl2_authorized: false
prl3_authorized: false
ltr_authorized: false
production_allowed: false
readonly_only: true
simulation_only: true
not_order: true
not_target_position: true
not_target_weight: true
---

# PRL1-R1 Candidate-level Policy Training 工作文档

## 1. 阶段定位

统筹已明确：

```text
docs/tw_portfolio_decision_model/POLICY_PRL1_R0_COORDINATOR_OPINION_FOR_REVIEWER_CN.md
recommended_next = PRL1_R1_CANDIDATE_POLICY_TRAINING
prl1_r1_authorized = true
```

本阶段只授权执行 `PRL1-R1 Candidate-level Policy Training`。

本阶段目标是：

```text
在 qlib-only train 窗口训练 candidate-level / pair-level policy，
在 validation 窗口选择唯一 final candidate policy，
判断 candidate-level action 表达是否能在 validation 上超过 baseline。
```

本阶段不是：

```text
strict_test
PRL2 supervised/offline route
PRL3 offline RL
qlib+LTR
production/default/Agent/provider/broker/monitor/frontend 扩权
```

## 2. 必须读取

执行者开始前必须读取：

```text
docs/tw_portfolio_decision_model/POLICY_PRL_PORTFOLIO_RL_MAINLINE_CN.md
docs/tw_portfolio_decision_model/POLICY_PRL1_R0_COORDINATOR_OPINION_FOR_REVIEWER_CN.md
docs/tw_portfolio_decision_model/POLICY_PRL1_R1_CANDIDATE_POLICY_TRAINING_WORK_CN.md
docs/tw_portfolio_decision_model/POLICY_PRL1_R0_CANDIDATE_CONTRACT_EVENT_LOGGING_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_PRL1_R0_CANDIDATE_CONTRACT_EVENT_LOGGING_EXECUTION_REPORT_CN.md
docs/tw_portfolio_decision_model/POLICY_PRL1_D_LEARNABILITY_ACTION_ATTRIBUTION_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_PRL1_SIMULATION_RL_QLIB_ONLY_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_PRL0_ENV_ORACLE_AUDIT_REVIEW_CN.md
docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md
docs/tw_modular_contracts/MODEL_SIGNAL_CONTRACT_CN.md
docs/tw_modular_contracts/STRATEGY_RULE_CONTRACT_CN.md
docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md
docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md
.agents/skills/coordinator-executor-reviewer-workflow/SKILL.md
.agents/skills/tw-stock-safety-boundary-review/SKILL.md
```

## 3. 输入 Artifact

必须使用 PRL1-R0 的 contract 和 logging 产物：

```text
data_tw/experiments/portfolio_rl_research/prl1_r0_candidate_contract_event_logging/manifest.json
data_tw/experiments/portfolio_rl_research/prl1_r0_candidate_contract_event_logging/candidate_action_schema.json
data_tw/experiments/portfolio_rl_research/prl1_r0_candidate_contract_event_logging/pair_action_schema.json
data_tw/experiments/portfolio_rl_research/prl1_r0_candidate_contract_event_logging/event_level_nav_log_schema.json
data_tw/experiments/portfolio_rl_research/prl1_r0_candidate_contract_event_logging/candidate_action_space_audit.csv
data_tw/experiments/portfolio_rl_research/prl1_r0_candidate_contract_event_logging/validator_report.json
data_tw/experiments/portfolio_rl_research/prl1_r0_candidate_contract_event_logging/golden_samples_report.json
```

必须继续使用 qlib-only frozen signal：

```text
data_tw/artifacts/signals/frozen_qlib_2018_2022/r1_legacy_signal_adapter_20260616/manifest.json
```

允许读取 PRL0 / PRL1-D artifact 作为诊断背景，但不得把 oracle action / oracle return / oracle advantage 用作训练标签、imitation label、reward shaping 或 validation selection。

## 4. 数据窗口

固定窗口：

```text
train = 2023-01-01..2024-12-31
validation = 2025-01-01..2025-12-31
strict_test = 2026-01-01..2026-05-07
```

本阶段使用规则：

```text
train: 允许训练、调参、训练曲线记录。
validation: 只用于 algorithm/config/checkpoint selection 和最终 validation replay。
strict_test: 不运行、不读取、不评估、不选择。
```

如果 validation 未超过 baseline：

```text
STOP_OR_COORDINATOR_DECISION
```

不得运行 strict_test。

## 5. 允许任务

### 5.1 Candidate-level / Pair-level Policy Training

执行者必须基于 PRL1-R0 contract 训练候选级策略：

```text
buy_action:
  state + candidate_stock -> buy logit/value

sell_action:
  state + holding_stock -> sell logit/value

switch_action:
  state + holding_stock + candidate_stock -> switch logit/value
```

动作边界必须保持：

```text
buy_candidates: qlib top20 by candidate_rank / buy_score
sell_candidates: current holdings only, max 10
switch_pairs: top5 weak holdings x top10 candidates, cap 20 pairs/day
max_buy_count <= 3
max_sell_count <= 3
max_switch_pair_count <= 3
```

输出仍只能是 intent-level action slate：

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

### 5.2 候选训练路线

执行者可以在本阶段内比较多个 candidate-level policy，但必须保持在 PRL1-R1 范围内。

允许路线：

```text
1. supervised candidate scorer sanity baseline
   只能使用 PIT-safe replay-generated labels 或 approved train-only labels；
   不得使用 oracle action / oracle return / oracle advantage。

2. candidate-level PPO / actor-critic
   policy over bounded buy/sell/switch candidates；
   必须使用 PRL1-R0 compact candidate set。

3. candidate-level DQN / Q scorer diagnostic comparison
   只在固定 discrete candidate/action set 内。
```

执行者不必强行实现所有算法；但至少必须实现一个完整 candidate-level policy 训练、validation selection、readonly replay、attribution 和 validator 闭环。

如果实现多算法或多 config，必须说明：

```text
algorithm
config_id
seed
episode_count
train_window
validation_window
selection_metric
validation_evaluation_count
```

### 5.3 Event-level Logging 和 Attribution

PRL1-R1 必须沿用 PRL1-R0 event-level logging schema。

训练和 validation replay 必须输出：

```text
event_level_nav_log_train.csv
event_level_nav_log_validation.csv
```

字段至少包括：

```text
date
split
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

必须基于 event log 输出：

```text
per_action_contribution.csv
per_candidate_contribution.csv
per_pair_contribution.csv
single_day_extreme_contribution.csv
top_gain_loss_events.csv
fee_tax_by_action.csv
concentration_audit.csv
```

## 6. 禁止事项

本阶段禁止：

```text
1. 运行 strict_test。
2. 读取 strict_test 结果或 strict_test metrics。
3. 使用 oracle action 做 imitation label。
4. 使用 oracle return / oracle advantage 做 reward shaping。
5. 使用 future_return / label / realized_pnl / future price / same-day unavailable data 作为 feature。
6. 进入 PRL2 supervised/offline route。
7. 进入 PRL3 CQL/IQL/Decision Transformer。
8. 使用 qlib+orthogonal LTR。
9. 输出 target_position / target_weight / quantity / broker order。
10. provider refresh / provider publish。
11. accepted latest switch。
12. monitor write / monitor scan / monitor alerts write。
13. frontend default switch。
14. Agent 扩权。
15. broker / quick-trade / order / place order / submit order。
16. 根据 validation 反复无界改 action space。
```

说明：

```text
PRL1-R1 可以训练 candidate-level policy；
但不得把本阶段扩展成 offline RL、strict_test、LTR 或生产路线。
```

## 7. 必须产出

artifact root：

```text
data_tw/experiments/portfolio_rl_research/prl1_r1_candidate_policy_training/
```

必须产出：

```text
manifest.json
training_config_grid.csv
candidate_policy_model_manifest.json
train_episode_metrics.csv
validation_episode_metrics.csv
validation_selection_audit.csv
seed_stability_audit.csv
candidate_action_distribution.csv
baseline_clone_audit.csv
participation_audit.csv
event_level_nav_log_train.csv
event_level_nav_log_validation.csv
per_action_contribution.csv
per_candidate_contribution.csv
per_pair_contribution.csv
single_day_extreme_contribution.csv
top_gain_loss_events.csv
fee_tax_by_action.csv
concentration_audit.csv
forbidden_feature_audit.csv
validator_report.json
golden_samples_report.json
```

执行报告：

```text
docs/tw_portfolio_decision_model/POLICY_PRL1_R1_CANDIDATE_POLICY_TRAINING_EXECUTION_REPORT_CN.md
```

## 8. Artifact 字段要求

### 8.1 manifest.json

必须包含：

```text
artifact_type
schema_version
created_at
stage = PRL1_R1_CANDIDATE_POLICY_TRAINING
readonly_only = true
simulation_only = true
production_allowed = false
strict_test_used = false
prl2_used = false
prl3_used = false
ltr_used = false
oracle_used_for_training = false
oracle_used_for_reward_shaping = false
not_order = true
not_target_position = true
not_target_weight = true
selected_config_id
selected_algorithm
selected_seed
validation_policy_net_return_after_fee_tax
validation_baseline_net_return_after_fee_tax
validation_excess_return_after_fee_tax
recommendation
output_files
```

### 8.2 training_config_grid.csv

至少包含：

```text
config_id
algorithm
seed
episode_count
candidate_top_k
max_buy_count
max_sell_count
max_switch_pair_count
learning_rate, if applicable
policy_params_summary
train_start
train_end
validation_start
validation_end
strict_test_used
oracle_label_used
oracle_reward_shaping_used
```

### 8.3 train_episode_metrics.csv / validation_episode_metrics.csv

至少包含：

```text
split
config_id
algorithm
seed
episode_id
net_return_after_fee_tax
baseline_net_return_after_fee_tax
excess_return_after_fee_tax
gross_return
fee_tax_total
action_count
baseline_action_count
participation_ratio
action_count_ratio
invalid_action_count
invalid_action_ratio
max_single_day_gain_share
max_single_day_loss_share
top_symbol_contribution_share
```

### 8.4 validation_selection_audit.csv

至少包含：

```text
config_id
algorithm
seed
validation_policy_net_return_after_fee_tax
validation_baseline_net_return_after_fee_tax
validation_excess_return_after_fee_tax
selected
selection_rank
selection_reason
validation_evaluation_count
strict_test_used
```

### 8.5 seed_stability_audit.csv

至少包含：

```text
algorithm
config_family
seed_count
validation_excess_mean
validation_excess_median
validation_excess_min
validation_excess_max
seed_win_count
seed_loss_count
selected_seed
selected_seed_reason
```

### 8.6 baseline_clone_audit.csv

至少包含：

```text
config_id
algorithm
seed
baseline_action_match_ratio
hold_match_ratio
buy_match_ratio
sell_match_ratio
switch_match_ratio
baseline_clone_flag
baseline_clone_reason
```

### 8.7 participation_audit.csv

至少包含：

```text
config_id
algorithm
seed
participation_ratio
action_count_ratio
hold_ratio
buy_count
sell_count
switch_count
low_participation_flag
no_action_dominance_flag
```

### 8.8 concentration_audit.csv

至少包含：

```text
config_id
algorithm
seed
max_single_day_gain_share
max_single_day_loss_share
top_symbol_contribution_share
top_action_type_contribution_share
single_day_extreme_flag
single_symbol_dominance_flag
concentration_reason
```

### 8.9 forbidden_feature_audit.csv

至少包含：

```text
field_name
present_in_state_feature
present_in_action_contract_output
present_in_order_intent
used_for_training
used_for_selection
status
```

必须覆盖：

```text
future_return
forward_return
label
realized_pnl
future_price
same_day_unavailable_data
strict_test_metrics
target_position
target_weight
quantity
execution_price
execution_date
broker_order
broker_order_id
quick_trade
provider_publish
accepted_latest
monitor_write
oracle_action
oracle_return
oracle_advantage
```

## 9. Validator / Golden Samples 要求

`validator_report.json` 必须确认：

```text
stage = PRL1_R1_CANDIDATE_POLICY_TRAINING
strict_test_used = false
prl2_used = false
prl3_used = false
ltr_used = false
oracle_used_for_training = false
oracle_used_for_reward_shaping = false
candidate_action_contract_reused_from_prl1_r0 = true
event_level_nav_logging_reused_from_prl1_r0 = true
train_episode_metrics_non_empty = true
validation_episode_metrics_non_empty = true
validation_selection_audit_exists = true
seed_stability_audit_exists = true
baseline_clone_audit_exists = true
participation_audit_exists = true
concentration_audit_exists = true
forbidden_feature_audit_pass = true
no_target_position = true
no_target_weight = true
no_quantity = true
no_broker_order = true
```

`golden_samples_report.json` 必须包含正负样本：

```text
positive_candidate_policy_training_artifact
positive_validation_selection
positive_event_level_nav_log_train
positive_event_level_nav_log_validation
positive_attribution_outputs
negative_strict_test_usage
negative_oracle_training_label
negative_oracle_reward_shaping
negative_target_weight_output
negative_quantity_output
negative_broker_order_output
negative_provider_publish
negative_accepted_latest_switch
negative_monitor_write
negative_prl2_or_prl3_entry
```

## 10. 通过条件

全部满足才可在执行报告中建议审查者提交统筹考虑后续阶段：

```text
1. validation policy net_return_after_fee_tax > validation baseline。
2. validation excess_return_after_fee_tax > 0。
3. train 不得明显低于 baseline 后只靠 validation 偶然胜出；如出现必须解释并标记风险。
4. participation_ratio >= 0.85。
5. action_count_ratio >= 0.80。
6. policy 不得退化为 baseline clone。
7. policy 不得靠 no_action / low participation 获得收益。
8. multi-seed 中至少多数 seed 不显著低于 baseline，且 selected seed/config 有稳定理由。
9. single_day_extreme_share 不得显示收益主要来自单日偶然。
10. top_gain_loss_events / concentration_audit 不得显示单一股票支配收益。
11. event-level attribution 完整且 train / validation 均非空。
12. validator_report.json pass。
13. golden_samples_report.json pass。
14. strict_test_used = false。
15. oracle_used_for_training = false。
16. oracle_used_for_reward_shaping = false。
17. 输出保持 intent-only，无 target/quantity/broker 字段。
```

如果未满足第 1 或第 2 条：

```text
STOP_OR_COORDINATOR_DECISION
```

不得运行 strict_test。

## 11. 失败与停止条件

任一情况出现，必须停止并写入执行报告：

```text
1. 发现必须使用 strict_test 才能选择 policy。
2. validation 未超过 baseline。
3. 收益来自 no_action / 极低参与。
4. 收益由单日或单一股票主导且无法解释。
5. 多 seed 大多数失败且 selected seed 是孤立成功。
6. candidate-level action contract 无法复用 PRL1-R0 contract。
7. event-level logging 无法复用 PRL1-R0 schema。
8. 需要 oracle action / oracle return / oracle advantage 才能训练。
9. 需要 future_return / realized_pnl / future price 作为 feature。
10. 需要输出 target_position / target_weight / quantity / broker order。
11. 需要 provider/latest/monitor/frontend/Agent/broker 扩权。
12. 执行者认为必须进入 PRL2/PRL3/LTR 才能完成。
```

停止时不得自行改路线；必须提交执行报告给审查者和统筹。

## 12. 执行报告要求

执行者必须写：

```text
docs/tw_portfolio_decision_model/POLICY_PRL1_R1_CANDIDATE_POLICY_TRAINING_EXECUTION_REPORT_CN.md
```

报告至少包含：

```text
1. Scope
   - assigned phase
   - mainline document
   - work document
   - non-goals confirmed

2. Documents / Contracts / Skills Read

3. Implementation / Training Changes
   - scripts/files changed
   - algorithm/configs implemented
   - how PRL1-R0 contract/logging was reused

4. Evidence Produced
   - artifact root
   - required files
   - key metric tables
   - validator/golden sample output

5. Validation Result
   - selected_config_id
   - selected_algorithm
   - selected_seed
   - validation policy return
   - validation baseline return
   - validation excess return
   - participation/action-count
   - baseline clone audit
   - concentration audit

6. Compliance With Mainline

7. Forbidden Actions Audit
   - strict_test_used
   - oracle label/reward shaping
   - PRL2/PRL3/LTR
   - target/quantity/broker/order
   - provider/latest/monitor/frontend/Agent

8. Issues / Blockers / Deviations

9. Files Changed

10. Recommendation For Reviewer
```

允许的推荐值只有：

```text
PASS_READY_FOR_REVIEWER_TO_RECOMMEND_COORDINATOR_DECIDE_NEXT_STAGE
FAIL_STOP_OR_COORDINATOR_DECISION
FAIL_NEEDS_PRL1_R1_REPAIR
STOP_FOR_CONTRACT_OR_LEAKAGE_OR_SAFETY_VIOLATION
```

执行者不得在报告中自行宣布进入 strict_test、PRL2、PRL3 或 LTR。

## 13. 给执行者的命令

```text
你是执行者。请执行 PRL1-R1 Candidate-level Policy Training。

必须读取：
docs/tw_portfolio_decision_model/POLICY_PRL_PORTFOLIO_RL_MAINLINE_CN.md
docs/tw_portfolio_decision_model/POLICY_PRL1_R0_COORDINATOR_OPINION_FOR_REVIEWER_CN.md
docs/tw_portfolio_decision_model/POLICY_PRL1_R1_CANDIDATE_POLICY_TRAINING_WORK_CN.md
docs/tw_portfolio_decision_model/POLICY_PRL1_R0_CANDIDATE_CONTRACT_EVENT_LOGGING_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_PRL1_R0_CANDIDATE_CONTRACT_EVENT_LOGGING_EXECUTION_REPORT_CN.md

只允许在 qlib-only train=2023-2024 训练 candidate-level / pair-level policy，
用 validation=2025 选择唯一 final candidate policy。

必须复用 PRL1-R0 candidate/pair contract 和 event-level logging schema。

不得运行 strict_test，不得进入 PRL2/PRL3/LTR，不得使用 oracle label/reward shaping，
不得输出 target_position/target_weight/quantity/broker order，
不得做 provider/latest/monitor/frontend/Agent/broker/production 扩权。

完成后输出 artifact 到：
data_tw/experiments/portfolio_rl_research/prl1_r1_candidate_policy_training/

并写执行报告：
docs/tw_portfolio_decision_model/POLICY_PRL1_R1_CANDIDATE_POLICY_TRAINING_EXECUTION_REPORT_CN.md
```
