---
created_at: 2026-06-22
status: reviewer_next_work_document
phase: PRL1_R1_R_PARTICIPATION_CONSTRAINED_CANDIDATE_POLICY_REPAIR
mainline_doc: docs/tw_portfolio_decision_model/POLICY_PRL_PORTFOLIO_RL_MAINLINE_CN.md
coordinator_opinion: docs/tw_portfolio_decision_model/POLICY_PRL1_R1_COORDINATOR_OPINION_FOR_REVIEWER_CN.md
previous_review: docs/tw_portfolio_decision_model/POLICY_PRL1_R1_CANDIDATE_POLICY_TRAINING_REVIEW_CN.md
previous_execution_report: docs/tw_portfolio_decision_model/POLICY_PRL1_R1_CANDIDATE_POLICY_TRAINING_EXECUTION_REPORT_CN.md
previous_artifact_root: data_tw/experiments/portfolio_rl_research/prl1_r1_candidate_policy_training
artifact_root: data_tw/experiments/portfolio_rl_research/prl1_r1_r_participation_constrained_repair
prl1_r1_repair_authorized: true
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

# PRL1-R1-R Participation-constrained Candidate Policy Repair 工作文档

## 1. 阶段定位

统筹已明确：

```text
docs/tw_portfolio_decision_model/POLICY_PRL1_R1_COORDINATOR_OPINION_FOR_REVIEWER_CN.md
recommended_next = PRL1_R1_R_PARTICIPATION_CONSTRAINED_CANDIDATE_POLICY_REPAIR
prl1_r1_repair_authorized = true
```

本阶段是 PRL1-R1 内部的一次受限 repair。

本阶段只修：

```text
1. participation/action-count gate failure。
2. switch action concentration 风险。
3. seed stability 诊断不足。
```

本阶段不授权：

```text
strict_test / PRL4
PRL2 supervised/offline route
PRL3 CQL/IQL/Decision Transformer
qlib+orthogonal LTR
oracle label / oracle reward shaping
production/default/Agent/provider/broker/monitor/frontend 扩权
```

## 2. 背景事实

PRL1-R1 已出现局部正收益信号：

```text
selected_config_id = CANDIDATE_SCORER_seed23_rank10_gap0.005
validation_policy_net_return_after_fee_tax = 1.02418720
validation_baseline_net_return_after_fee_tax = 0.96228725
validation_excess_return_after_fee_tax = 0.06189995
baseline_clone_flag = false
```

但 PRL1-R1 失败于硬门槛：

```text
participation_ratio = 0.66942149 < 0.85
action_count_ratio = 0.68936170 < 0.80
```

并存在行为集中风险：

```text
top_action_type_contribution_share = 0.9830758650
```

seed stability 也偏弱：

```text
seed_count = 4
seed_win_count = 2
seed_loss_count = 2
validation_excess_mean = -0.09184351
validation_excess_median = -0.05475969
```

因此本轮 repair 的目标不是无界调参，而是验证：

```text
candidate-level positive validation signal 是否能在满足高参与度、非 baseline clone、非 switch-only artifact 的条件下保留。
```

## 3. 必须读取

执行者开始前必须读取：

```text
docs/tw_portfolio_decision_model/POLICY_PRL_PORTFOLIO_RL_MAINLINE_CN.md
docs/tw_portfolio_decision_model/POLICY_PRL1_R1_COORDINATOR_OPINION_FOR_REVIEWER_CN.md
docs/tw_portfolio_decision_model/POLICY_PRL1_R1_R_PARTICIPATION_CONSTRAINED_REPAIR_WORK_CN.md
docs/tw_portfolio_decision_model/POLICY_PRL1_R1_CANDIDATE_POLICY_TRAINING_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_PRL1_R1_CANDIDATE_POLICY_TRAINING_EXECUTION_REPORT_CN.md
docs/tw_portfolio_decision_model/POLICY_PRL1_R1_CANDIDATE_POLICY_TRAINING_WORK_CN.md
docs/tw_portfolio_decision_model/POLICY_PRL1_R0_CANDIDATE_CONTRACT_EVENT_LOGGING_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_PRL1_R0_CANDIDATE_CONTRACT_EVENT_LOGGING_EXECUTION_REPORT_CN.md
docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md
docs/tw_modular_contracts/MODEL_SIGNAL_CONTRACT_CN.md
docs/tw_modular_contracts/STRATEGY_RULE_CONTRACT_CN.md
docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md
docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md
.agents/skills/coordinator-executor-reviewer-workflow/SKILL.md
.agents/skills/tw-stock-safety-boundary-review/SKILL.md
```

## 4. 输入 Artifact

必须使用 PRL1-R0 的 contract / logging：

```text
data_tw/experiments/portfolio_rl_research/prl1_r0_candidate_contract_event_logging/candidate_action_schema.json
data_tw/experiments/portfolio_rl_research/prl1_r0_candidate_contract_event_logging/pair_action_schema.json
data_tw/experiments/portfolio_rl_research/prl1_r0_candidate_contract_event_logging/event_level_nav_log_schema.json
```

必须读取 PRL1-R1 失败证据作为 repair baseline：

```text
data_tw/experiments/portfolio_rl_research/prl1_r1_candidate_policy_training/manifest.json
data_tw/experiments/portfolio_rl_research/prl1_r1_candidate_policy_training/training_config_grid.csv
data_tw/experiments/portfolio_rl_research/prl1_r1_candidate_policy_training/validation_episode_metrics.csv
data_tw/experiments/portfolio_rl_research/prl1_r1_candidate_policy_training/validation_selection_audit.csv
data_tw/experiments/portfolio_rl_research/prl1_r1_candidate_policy_training/seed_stability_audit.csv
data_tw/experiments/portfolio_rl_research/prl1_r1_candidate_policy_training/participation_audit.csv
data_tw/experiments/portfolio_rl_research/prl1_r1_candidate_policy_training/baseline_clone_audit.csv
data_tw/experiments/portfolio_rl_research/prl1_r1_candidate_policy_training/concentration_audit.csv
```

必须继续使用 qlib-only frozen signal：

```text
data_tw/artifacts/signals/frozen_qlib_2018_2022/r1_legacy_signal_adapter_20260616/manifest.json
```

允许读取 PRL0 / PRL1-D artifact 作为诊断背景，但不得把 oracle action / oracle return / oracle advantage 用作训练标签、imitation label、reward shaping 或 validation selection。

## 5. 数据窗口

固定窗口：

```text
train = 2023-01-01..2024-12-31
validation = 2025-01-01..2025-12-31
strict_test = 2026-01-01..2026-05-07
```

本阶段使用规则：

```text
train: 允许训练、搜索、约束调试、训练曲线记录。
validation: 只用于 repair config selection 和最终 validation replay。
strict_test: 不运行、不读取、不评估、不选择。
```

## 6. 允许修复范围

允许执行者：

```text
1. 继续使用 qlib-only frozen signal。
2. 继续使用 PRL1-R0 candidate/pair action contract。
3. 继续使用 PRL1-R0 event-level logging schema。
4. 在 train=2023-2024 上训练或搜索。
5. 在 validation=2025 上选择 final repair config。
6. 增加 participation/action-count 约束到 training 或 selection。
7. 输出 return-participation frontier。
8. 增加 switch action concentration audit / gate。
9. 增加多 seed 稳定性审计。
```

允许的最小修复方式：

```text
1. 调整 score/rank/gap threshold，使 candidate policy 不因过度筛选而降参与。
2. 在 selection 中加入 hard gate：
   participation_ratio >= 0.85
   action_count_ratio >= 0.80
3. 输出不同 participation target 下的 frontier：
   target = 0.65 / 0.75 / 0.85 / 0.95
4. 对 switch-only 倾向加入 gate 或诊断：
   top_action_type_contribution_share
   switch_count_ratio
   switch_fee_tax_share
```

允许比较多个 repair configs / seeds，但必须有上限并写入 `training_config_grid.csv`。本轮不得做无界 search。

## 7. Action Contract 和输出边界

动作边界必须保持 PRL1-R0 / PRL1-R1 合同：

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

## 8. 禁止事项

本阶段禁止：

```text
1. 运行 strict_test。
2. 读取 strict_test 结果或 strict_test metrics。
3. 使用 PRL2 supervised/offline route。
4. 使用 PRL3 CQL/IQL/Decision Transformer。
5. 使用 qlib+orthogonal LTR。
6. 使用 oracle action 做 imitation label。
7. 使用 oracle return / oracle advantage 做 reward shaping。
8. 使用 future_return / label / realized_pnl / future price / same-day unavailable data 作为 feature。
9. 输出 target_position / target_weight / quantity / broker order。
10. provider refresh / provider publish。
11. accepted latest switch。
12. monitor write / monitor scan / monitor alerts write。
13. frontend default switch。
14. Agent 扩权。
15. broker / quick-trade / order / place order / submit order。
16. 根据 validation 结果无限扩展 action space 或无限调参。
17. 降低 participation_ratio / action_count_ratio 通过门槛后宣称通过。
```

## 9. 必须产出

artifact root：

```text
data_tw/experiments/portfolio_rl_research/prl1_r1_r_participation_constrained_repair/
```

必须产出：

```text
manifest.json
training_config_grid.csv
candidate_policy_model_manifest.json
train_episode_metrics.csv
validation_episode_metrics.csv
validation_selection_audit.csv
return_participation_frontier.csv
seed_stability_audit.csv
candidate_action_distribution.csv
baseline_clone_audit.csv
participation_audit.csv
switch_concentration_audit.csv
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
docs/tw_portfolio_decision_model/POLICY_PRL1_R1_R_PARTICIPATION_CONSTRAINED_REPAIR_EXECUTION_REPORT_CN.md
```

## 10. Artifact 字段要求

### 10.1 manifest.json

必须包含：

```text
artifact_type
schema_version
created_at
stage = PRL1_R1_R_PARTICIPATION_CONSTRAINED_CANDIDATE_POLICY_REPAIR
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
selected_participation_target
validation_policy_net_return_after_fee_tax
validation_baseline_net_return_after_fee_tax
validation_excess_return_after_fee_tax
validation_participation_ratio
validation_action_count_ratio
baseline_clone_flag
low_participation_flag
no_action_dominance_flag
switch_concentration_flag
recommendation
output_files
```

### 10.2 training_config_grid.csv

至少包含：

```text
config_id
algorithm
seed
episode_count
participation_target
action_count_target
candidate_top_k
max_buy_count
max_sell_count
max_switch_pair_count
buy_rank_threshold
sell_rank_floor
switch_gap
participation_penalty_or_constraint
switch_concentration_penalty_or_gate
train_start
train_end
validation_start
validation_end
strict_test_used
oracle_label_used
oracle_reward_shaping_used
```

### 10.3 return_participation_frontier.csv

必须覆盖 participation target：

```text
0.65
0.75
0.85
0.95
```

至少包含：

```text
participation_target
best_config_id
best_seed
validation_policy_net_return_after_fee_tax
validation_baseline_net_return_after_fee_tax
validation_excess_return_after_fee_tax
participation_ratio
action_count_ratio
baseline_clone_flag
low_participation_flag
no_action_dominance_flag
switch_concentration_flag
selected_for_final
```

### 10.4 validation_selection_audit.csv

selection 必须先过滤硬门槛，再按 return 选择。

至少包含：

```text
config_id
algorithm
seed
participation_target
validation_policy_net_return_after_fee_tax
validation_baseline_net_return_after_fee_tax
validation_excess_return_after_fee_tax
participation_ratio
action_count_ratio
baseline_clone_flag
low_participation_flag
no_action_dominance_flag
switch_concentration_flag
hard_gate_pass
selected
selection_rank
selection_reason
validation_evaluation_count
strict_test_used
```

### 10.5 participation_audit.csv

至少包含：

```text
config_id
algorithm
seed
participation_target
participation_ratio
action_count_ratio
hold_ratio
buy_count
sell_count
switch_count
low_participation_flag
no_action_dominance_flag
participation_gate_pass
action_count_gate_pass
```

### 10.6 switch_concentration_audit.csv

至少包含：

```text
config_id
algorithm
seed
switch_count
switch_count_ratio
switch_nav_delta
switch_abs_nav_delta_share
switch_fee_tax
switch_fee_tax_share
top_action_type_contribution_share
switch_concentration_flag
switch_concentration_reason
```

建议默认 flag 规则：

```text
switch_count_ratio > 0.80 或
switch_abs_nav_delta_share > 0.90 或
top_action_type_contribution_share > 0.90
```

如果执行者使用不同规则，必须在执行报告解释。

### 10.7 seed_stability_audit.csv

至少包含：

```text
algorithm
config_family
participation_target
seed_count
validation_excess_mean
validation_excess_median
validation_excess_min
validation_excess_max
seed_win_count
seed_loss_count
hard_gate_pass_seed_count
selected_seed
selected_seed_reason
```

### 10.8 forbidden_feature_audit.csv

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

## 11. Validator / Golden Samples 要求

`validator_report.json` 必须确认：

```text
stage = PRL1_R1_R_PARTICIPATION_CONSTRAINED_CANDIDATE_POLICY_REPAIR
strict_test_used = false
prl2_used = false
prl3_used = false
ltr_used = false
oracle_used_for_training = false
oracle_used_for_reward_shaping = false
candidate_action_contract_reused_from_prl1_r0 = true
event_level_nav_logging_reused_from_prl1_r0 = true
return_participation_frontier_exists = true
validation_selection_uses_hard_gate = true
selected_validation_return_gate_pass = true
selected_participation_gate_pass = true
selected_action_count_gate_pass = true
selected_baseline_clone_gate_pass = true
selected_no_action_dominance_gate_pass = true
selected_switch_concentration_gate_pass = true
seed_stability_audit_exists = true
forbidden_feature_audit_pass = true
no_target_position = true
no_target_weight = true
no_quantity = true
no_broker_order = true
```

`golden_samples_report.json` 必须包含：

```text
positive_participation_constrained_selection
positive_return_participation_frontier
positive_switch_concentration_audit
positive_event_level_nav_log_train
positive_event_level_nav_log_validation
negative_low_participation_selected
negative_action_count_low_selected
negative_switch_only_artifact_selected
negative_strict_test_usage
negative_oracle_training_label
negative_oracle_reward_shaping
negative_target_weight_output
negative_quantity_output
negative_broker_order_output
negative_prl2_or_prl3_entry
```

## 12. 通过条件

全部满足才可在执行报告中建议审查者提交统筹考虑后续阶段：

```text
1. selected validation excess_return_after_fee_tax > 0。
2. selected participation_ratio >= 0.85。
3. selected action_count_ratio >= 0.80。
4. selected baseline_clone_flag = false。
5. selected no_action_dominance_flag = false。
6. selected low_participation_flag = false。
7. seed stability 不得只有单一 seed 正收益且整体均值严重为负。
8. single_day_extreme_flag = false。
9. single_symbol_dominance_flag = false。
10. switch_concentration_audit 不得显示不可解释的 switch-only artifact。
11. validator_report.json pass。
12. golden_samples_report.json pass。
13. strict_test_used = false。
14. oracle_used_for_training = false。
15. oracle_used_for_reward_shaping = false。
16. 输出保持 intent-only，无 target/quantity/broker 字段。
```

如果 repair 后只有低参与配置能获得正收益：

```text
STOP_AND_RETURN_TO_COORDINATOR
```

不得擅自降低参与度门槛后进入 strict_test。

## 13. 失败与停止条件

任一情况出现，必须停止并写入执行报告：

```text
1. 没有任何 config 同时满足 return gate 和 participation/action-count gate。
2. 只有 selected config 为正，且 seed stability 明显弱于 PRL1-R1。
3. 正收益来自 no_action / low participation。
4. 正收益来自不可解释的 switch-only artifact。
5. 需要 strict_test 才能选择 policy。
6. 需要 oracle action / oracle return / oracle advantage 才能训练。
7. 需要 future_return / realized_pnl / future price 作为 feature。
8. 需要进入 PRL2/PRL3/LTR 才能完成。
9. 需要输出 target_position / target_weight / quantity / broker order。
10. 需要 provider/latest/monitor/frontend/Agent/broker 扩权。
```

停止时不得自行改路线；必须提交执行报告给审查者和统筹。

## 14. 执行报告要求

执行者必须写：

```text
docs/tw_portfolio_decision_model/POLICY_PRL1_R1_R_PARTICIPATION_CONSTRAINED_REPAIR_EXECUTION_REPORT_CN.md
```

报告至少包含：

```text
1. Scope
   - assigned phase
   - mainline document
   - work document
   - non-goals confirmed

2. Documents / Contracts / Skills Read

3. Repair Changes
   - scripts/files changed
   - participation/action-count constraint implementation
   - switch concentration gate implementation
   - how PRL1-R0 contract/logging was reused

4. Evidence Produced
   - artifact root
   - required files
   - return_participation_frontier
   - validator/golden sample output

5. Validation Result
   - selected_config_id
   - selected_algorithm
   - selected_seed
   - selected_participation_target
   - validation policy return
   - validation baseline return
   - validation excess return
   - participation/action-count
   - baseline clone audit
   - switch concentration audit
   - seed stability

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
FAIL_NEEDS_PRL1_R1_R_REPAIR
STOP_FOR_CONTRACT_OR_LEAKAGE_OR_SAFETY_VIOLATION
```

执行者不得在报告中自行宣布进入 strict_test、PRL2、PRL3 或 LTR。

## 15. 给执行者的命令

```text
你是执行者。请执行 PRL1-R1-R Participation-constrained Candidate Policy Repair。

必须读取：
docs/tw_portfolio_decision_model/POLICY_PRL_PORTFOLIO_RL_MAINLINE_CN.md
docs/tw_portfolio_decision_model/POLICY_PRL1_R1_COORDINATOR_OPINION_FOR_REVIEWER_CN.md
docs/tw_portfolio_decision_model/POLICY_PRL1_R1_R_PARTICIPATION_CONSTRAINED_REPAIR_WORK_CN.md
docs/tw_portfolio_decision_model/POLICY_PRL1_R1_CANDIDATE_POLICY_TRAINING_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_PRL1_R1_CANDIDATE_POLICY_TRAINING_EXECUTION_REPORT_CN.md

本轮只修 participation/action-count 与 switch concentration。
必须复用 PRL1-R0 candidate/pair contract 和 event-level logging schema。
必须输出 return_participation_frontier.csv 和 switch_concentration_audit.csv。

不得运行 strict_test，不得进入 PRL2/PRL3/LTR，不得使用 oracle label/reward shaping，
不得输出 target_position/target_weight/quantity/broker order，
不得做 provider/latest/monitor/frontend/Agent/broker/production 扩权。

完成后输出 artifact 到：
data_tw/experiments/portfolio_rl_research/prl1_r1_r_participation_constrained_repair/

并写执行报告：
docs/tw_portfolio_decision_model/POLICY_PRL1_R1_R_PARTICIPATION_CONSTRAINED_REPAIR_EXECUTION_REPORT_CN.md
```
