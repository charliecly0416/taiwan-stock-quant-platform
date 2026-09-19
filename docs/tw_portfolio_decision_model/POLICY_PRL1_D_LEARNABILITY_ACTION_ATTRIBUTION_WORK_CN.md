---
created_at: 2026-06-22
status: reviewer_next_work_document
phase: PRL1_D_LEARNABILITY_AND_ACTION_ATTRIBUTION_DIAGNOSTIC
mainline_doc: docs/tw_portfolio_decision_model/POLICY_PRL_PORTFOLIO_RL_MAINLINE_CN.md
coordinator_opinion: docs/tw_portfolio_decision_model/POLICY_PRL1_COORDINATOR_OPINION_FOR_REVIEWER_CN.md
previous_review: docs/tw_portfolio_decision_model/POLICY_PRL1_SIMULATION_RL_QLIB_ONLY_REVIEW_CN.md
previous_execution_report: docs/tw_portfolio_decision_model/POLICY_PRL1_SIMULATION_RL_QLIB_ONLY_EXECUTION_REPORT_CN.md
artifact_root: data_tw/experiments/portfolio_rl_research/prl1_d_learnability_action_attribution
strict_test_authorized: false
prl2_authorized: false
prl3_authorized: false
production_allowed: false
readonly_only: true
simulation_only: true
not_order: true
not_target_position: true
not_target_weight: true
---

# PRL1-D Learnability And Action Attribution 执行工作文档

## 1. 阶段结论与定位

PRL1 已审查失败：

```text
docs/tw_portfolio_decision_model/POLICY_PRL1_SIMULATION_RL_QLIB_ONLY_REVIEW_CN.md
verdict = FAIL_STOP_OR_COORDINATOR_DECISION
```

统筹意见明确：

```text
docs/tw_portfolio_decision_model/POLICY_PRL1_COORDINATOR_OPINION_FOR_REVIEWER_CN.md
recommended_next = PRL1_D_LEARNABILITY_AND_ACTION_ATTRIBUTION_DIAGNOSTIC
```

本轮不是 PRL1 训练 repair，不是 PRL2，不是 PRL3，不是 strict_test。它是 PRL1 后的诊断分支，只回答：

```text
当前 state/action/reward 设计是否具备可学习性。
```

## 2. 阶段目标

PRL1-D 只回答四个问题：

```text
1. 现有 state/action encoding 能不能学会 baseline？
2. PRL0 oracle upper bound 的优势是否存在 PIT-safe 可学习模式？
3. 哪些 action templates 在 train/validation 持续破坏收益？
4. 是否应从 template-level action 改成 candidate-level / pair-level action policy？
```

PRL1-D 不以超过 baseline 为目标，不训练最终收益策略，不选择可交易 policy，不运行 strict_test。

## 3. 必须读取

执行者开始前必须读取：

```text
docs/tw_portfolio_decision_model/POLICY_PRL_PORTFOLIO_RL_MAINLINE_CN.md
docs/tw_portfolio_decision_model/POLICY_PRL1_COORDINATOR_OPINION_FOR_REVIEWER_CN.md
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

## 4. 输入 artifact

允许读取：

```text
data_tw/experiments/portfolio_rl_research/prl0_env_oracle_audit/manifest.json
data_tw/experiments/portfolio_rl_research/prl0_env_oracle_audit/env_schema.json
data_tw/experiments/portfolio_rl_research/prl0_env_oracle_audit/state_feature_schema.json
data_tw/experiments/portfolio_rl_research/prl0_env_oracle_audit/action_space_schema.json
data_tw/experiments/portfolio_rl_research/prl0_env_oracle_audit/reward_schema.json
data_tw/experiments/portfolio_rl_research/prl0_env_oracle_audit/oracle_upper_bound_train.csv
data_tw/experiments/portfolio_rl_research/prl1_simulation_rl_qlib_only/manifest.json
data_tw/experiments/portfolio_rl_research/prl1_simulation_rl_qlib_only/train_episode_metrics.csv
data_tw/experiments/portfolio_rl_research/prl1_simulation_rl_qlib_only/validation_episode_metrics.csv
data_tw/experiments/portfolio_rl_research/prl1_simulation_rl_qlib_only/action_template_distribution.csv
data_tw/experiments/portfolio_rl_research/prl1_simulation_rl_qlib_only/selected_policy_decisions_train.jsonl
data_tw/experiments/portfolio_rl_research/prl1_simulation_rl_qlib_only/selected_policy_decisions_validation.jsonl
data_tw/artifacts/signals/frozen_qlib_2018_2022/r1_legacy_signal_adapter_20260616/manifest.json
```

`oracle_upper_bound_train.csv` 只能用于 train-only 诊断分析，禁止用于训练策略、imitation policy、reward shaping、validation selection 或 strict_test。

## 5. 数据窗口

固定：

```text
train = 2023-01-01..2024-12-31
validation = 2025-01-01..2025-12-31
strict_test = 2026-01-01..2026-05-07
```

PRL1-D 使用规则：

```text
train: baseline imitation sanity check、oracle bucket analysis、action attribution。
validation: baseline imitation validation metrics、action attribution 对照。
strict_test: 不运行、不读取、不评估、不选择。
```

## 6. 必做任务

### 6.1 Baseline Imitation Sanity Check

目的：

```text
确认当前 state/action encoding 是否足以表达 baseline 决策。
```

要求：

```text
1. 用 train 数据构造 baseline action template labels。
2. 训练轻量 supervised classifier 预测 baseline action template。
3. 在 validation 上评估 imitation accuracy / macro F1 / action confusion matrix。
4. 只允许作为 sanity check，不得作为收益策略、交易 policy 或 strict_test 前置 policy。
```

最低输出：

```text
baseline_imitation_metrics.csv
baseline_imitation_confusion_matrix.csv
baseline_imitation_feature_audit.csv
```

必须包含：

```text
train_accuracy
train_macro_f1
validation_accuracy
validation_macro_f1
per_action_precision
per_action_recall
class_support
most_confused_action_pairs
```

判断规则：

```text
如果 baseline imitation 在 validation 上显著失败，说明当前 state/action encoding 可能不能表达 baseline，不应继续 RL 训练 repair。
```

### 6.2 Oracle Bucket Analysis

目的：

```text
只做 train-only 诊断，分析 PRL0 oracle 高收益动作是否存在 PIT-safe 可学习模式。
```

要求：

```text
1. 不得用 oracle action 训练 policy。
2. 不得用 oracle action 做 imitation label。
3. 不得用 oracle return 做 reward shaping。
4. 只在 train 窗口分析 oracle action 与 PIT-safe score/rank/MA/holding state 的关系。
```

必须输出 bucket 表：

```text
score_bucket
rank_bucket
score_delta_bucket
rank_delta_bucket
MA_trend_bucket
holding_age_bucket
unrealized_return_bucket
oracle_action_type
oracle_advantage_vs_baseline_action
count
mean_advantage
median_advantage
positive_advantage_ratio
```

最低输出：

```text
oracle_bucket_analysis.csv
oracle_advantage_concentration.csv
oracle_bucket_pattern_summary.md
```

判断规则：

```text
如果 oracle advantage 只来自少数 hindsight 个股/日期，
且没有稳定 PIT-safe bucket pattern，
则 supervised/offline/RL 都很难泛化。
```

### 6.3 Action Template Return Attribution

目的：

```text
解释 PRL1 active policy 为什么破坏收益。
```

要求：

```text
1. 对 A0-A7 每个 action template 输出 train/validation 贡献。
2. 统计每类 template 的 count、average next reward、median next reward、cumulative NAV contribution。
3. 统计 invalid action count、fee/tax contribution、top loss dates/symbols。
4. 补齐 PRL1 review 中缺失的 single_day_extreme_share。
```

最低输出：

```text
action_template_return_attribution.csv
single_day_extreme_contribution.csv
action_template_top_loss_events.csv
```

必须覆盖：

```text
split = train / validation
template_id = A0..A7
count
avg_next_reward
median_next_reward
cumulative_nav_contribution
fee_tax_contribution
invalid_action_count
top_loss_date
top_loss_symbol
single_day_extreme_share
```

判断规则：

```text
如果某些 template 在 train/validation 都稳定负贡献，应在后续 action space 中移除、拆细或降权。
```

### 6.4 Candidate-level Action Redesign Proposal

目的：

```text
判断是否应从 template-level policy 改为 candidate-level / pair-level policy。
```

当前 PRL1 动作过粗：

```text
A2_buy_top_1
A4_switch_h1_c1
A6_sell_k_weak_holdings
```

这些模板不能直接学习：

```text
某个股票 score 多高才买；
某个持仓是否该卖；
某个 sell_i -> buy_j pair 是否值得换。
```

必须提出下一步设计建议：

```text
state + candidate_stock -> buy logit/value
state + holding_stock -> sell logit/value
state + holding_stock + candidate_stock -> switch logit/value
```

最低输出：

```text
candidate_level_redesign_proposal.md
candidate_level_state_action_schema_draft.json
candidate_level_risk_and_gate.md
```

建议必须回答：

```text
1. 是否建议另开 PRL1-R Candidate-level Policy Repair。
2. 如果建议，新的 action space 如何限制可探索规模。
3. 如何避免 target_weight / target_position / quantity。
4. 如何避免 oracle future label 泄漏。
5. 如何做 validation-only selection。
6. 哪些 PRL1 template 应删除、拆细或降权。
```

## 7. 必须产出 artifact

artifact 根目录：

```text
data_tw/experiments/portfolio_rl_research/prl1_d_learnability_action_attribution/
```

必须产出：

```text
manifest.json
baseline_imitation_metrics.csv
baseline_imitation_confusion_matrix.csv
baseline_imitation_feature_audit.csv
oracle_bucket_analysis.csv
oracle_advantage_concentration.csv
oracle_bucket_pattern_summary.md
action_template_return_attribution.csv
single_day_extreme_contribution.csv
action_template_top_loss_events.csv
candidate_level_redesign_proposal.md
candidate_level_state_action_schema_draft.json
candidate_level_risk_and_gate.md
forbidden_feature_audit.csv
validator_report.json
golden_samples_report.json
```

执行报告：

```text
docs/tw_portfolio_decision_model/POLICY_PRL1_D_LEARNABILITY_ACTION_ATTRIBUTION_EXECUTION_REPORT_CN.md
```

## 8. Validator / Golden Sample 要求

validator 至少检查：

```text
1. 所有必需 artifact 存在。
2. strict_test 未读取、未运行、未用于选择。
3. oracle action / oracle return 未用于训练 policy、imitation policy 或 reward shaping。
4. baseline imitation 输出被标记为 sanity_check_only。
5. baseline imitation model 未输出收益策略或 OrderIntent。
6. forbidden feature audit 通过。
7. candidate-level proposal 不含 target_weight / target_position / quantity / broker order。
8. 没有 PRL2 / PRL3 / offline RL 训练产物。
```

golden samples 至少覆盖：

```text
positive_baseline_imitation_metrics
positive_oracle_bucket_analysis_diagnostic_only
positive_action_template_attribution
positive_candidate_level_schema_intent_only
negative_oracle_action_used_as_training_label
negative_future_return_as_feature
negative_strict_test_usage
negative_target_weight_output
negative_quantity_order_output
negative_offline_rl_started
```

## 9. 禁止事项

本轮禁止：

```text
1. 运行 strict_test。
2. 训练最终收益策略。
3. 用 baseline imitation classifier 作为交易 policy。
4. 用 oracle action 做 imitation policy。
5. 用 oracle return 做 reward shaping。
6. 进入 PRL2 supervised/action-value training。
7. 进入 PRL3 CQL/IQL/Decision Transformer/offline RL。
8. 使用 qlib+LTR。
9. 扩大 PRL1 seeds / episode_count / hidden size / learning rate 网格。
10. provider/latest/monitor/frontend/Agent/broker 扩权。
11. 输出 target_position / target_weight / quantity / broker order。
12. 将任何结果写成收益承诺或投资建议。
```

## 10. 通过 / 停止判断

PRL1-D 不是收益通过阶段，因此不得给出：

```text
PASS_READY_FOR_STRICT_TEST
PASS_READY_FOR_PRL2
PASS_READY_FOR_PRL3
```

允许的 recommendation 只有：

```text
DIAGNOSTIC_COMPLETE_RECOMMEND_CLOSE_PRL_Q_ONLY_BRANCH
DIAGNOSTIC_COMPLETE_RECOMMEND_COORDINATOR_DECIDE_PRL1_R
FAIL_NEEDS_PRL1_D_REPAIR
STOP_FOR_CONTRACT_OR_LEAKAGE_VIOLATION
```

如果出现以下情况，应建议关闭当前 PRL qlib-only 分支：

```text
baseline imitation validation 表现很差；
oracle advantage 无稳定 PIT-safe bucket pattern；
action templates 在 train/validation 均稳定负贡献且无法拆细解释；
candidate-level redesign 无法避免泄漏或动作空间爆炸。
```

只有在以下条件都较清晰时，才可建议统筹考虑另开 PRL1-R：

```text
baseline imitation 能证明 state/action encoding 可表达 baseline；
oracle bucket analysis 显示存在 PIT-safe 可学习 pattern；
action attribution 找到明确应移除/拆细的负贡献 template；
candidate-level / pair-level policy proposal 有受限 action space 和清晰无泄漏 gate。
```

即使建议 PRL1-R，也必须由统筹另行授权；执行者不得自行进入 PRL1-R。

## 11. 给执行者的命令

```text
你是执行者。请执行 PRL1-D Learnability And Action Attribution Diagnostic。

必须读取：
1. docs/tw_portfolio_decision_model/POLICY_PRL_PORTFOLIO_RL_MAINLINE_CN.md
2. docs/tw_portfolio_decision_model/POLICY_PRL1_COORDINATOR_OPINION_FOR_REVIEWER_CN.md
3. docs/tw_portfolio_decision_model/POLICY_PRL1_D_LEARNABILITY_ACTION_ATTRIBUTION_WORK_CN.md
4. docs/tw_portfolio_decision_model/POLICY_PRL1_SIMULATION_RL_QLIB_ONLY_REVIEW_CN.md
5. docs/tw_portfolio_decision_model/POLICY_PRL1_SIMULATION_RL_QLIB_ONLY_EXECUTION_REPORT_CN.md
6. docs/tw_portfolio_decision_model/POLICY_PRL0_ENV_ORACLE_AUDIT_REVIEW_CN.md
7. docs/tw_portfolio_decision_model/POLICY_PRL0_ENV_ORACLE_AUDIT_EXECUTION_REPORT_CN.md
8. docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md
9. docs/tw_modular_contracts/MODEL_SIGNAL_CONTRACT_CN.md
10. docs/tw_modular_contracts/STRATEGY_RULE_CONTRACT_CN.md
11. docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md
12. docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md

本轮只做诊断：
- baseline imitation sanity check；
- train-only oracle bucket analysis；
- action template return attribution；
- candidate-level / pair-level redesign proposal；
- forbidden feature audit、validator、golden samples；
- 写执行报告。

本轮禁止：
- 运行 strict_test；
- 训练最终收益策略；
- 用 oracle action/return 训练或塑形；
- 进入 PRL2/PRL3；
- 使用 LTR；
- 扩大 PRL1 训练网格；
- 输出 target_position/target_weight/quantity/broker order；
- provider/latest/monitor/frontend/Agent/broker 扩权。

artifact 根目录：
data_tw/experiments/portfolio_rl_research/prl1_d_learnability_action_attribution/

执行报告：
docs/tw_portfolio_decision_model/POLICY_PRL1_D_LEARNABILITY_ACTION_ATTRIBUTION_EXECUTION_REPORT_CN.md

recommendation 只能从以下选择：
- DIAGNOSTIC_COMPLETE_RECOMMEND_CLOSE_PRL_Q_ONLY_BRANCH
- DIAGNOSTIC_COMPLETE_RECOMMEND_COORDINATOR_DECIDE_PRL1_R
- FAIL_NEEDS_PRL1_D_REPAIR
- STOP_FOR_CONTRACT_OR_LEAKAGE_VIOLATION
```
