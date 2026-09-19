---
created_at: 2026-06-22T07:33:53+00:00
status: executed_prl1_r1_candidate_policy_training
phase: PRL1_R1_CANDIDATE_POLICY_TRAINING
mainline_doc: docs/tw_portfolio_decision_model/POLICY_PRL_PORTFOLIO_RL_MAINLINE_CN.md
work_document: docs/tw_portfolio_decision_model/POLICY_PRL1_R1_CANDIDATE_POLICY_TRAINING_WORK_CN.md
artifact_root: data_tw/experiments/portfolio_rl_research/prl1_r1_candidate_policy_training
strict_test_used: false
recommendation: FAIL_STOP_OR_COORDINATOR_DECISION
---

# PRL1-R1 Candidate-level Policy Training 执行报告

## 1. Scope

Assigned phase: `PRL1_R1_CANDIDATE_POLICY_TRAINING`

本轮只在 qlib-only train=2023-2024 上执行 candidate-level 参数化策略训练/搜索，并在 validation=2025 上选择唯一 final config。

Non-goals confirmed:

```text
strict_test
PRL2 / PRL3 / LTR
oracle action/return/advantage label or reward shaping
target_position / target_weight / quantity / broker order output
provider/latest/monitor/frontend/Agent/broker/production expansion
```

## 2. Implementation / Training Changes

新增脚本：

```text
scripts/run_tw_policy_prl1_r1_candidate_policy_training.py
```

训练路线：

```text
algorithm = candidate_level_parametric_actor_critic_lite
configs = 4
selection_metric = validation_excess_return_after_fee_tax
validation_evaluation_count = 4
```

PRL1-R0 复用：

```text
candidate_action_schema.json / pair_action_schema.json
event_level_nav_log_schema.json
```

## 3. Evidence Produced

artifact root:

```text
data_tw/experiments/portfolio_rl_research/prl1_r1_candidate_policy_training/
```

validator:

```text
PASS_PRL1_R1_VALIDATOR
```

golden samples:

```text
PASS_PRL1_R1_GOLDEN_SAMPLES
```

## 4. Validation Result

```text
selected_config_id = CANDIDATE_SCORER_seed23_rank10_gap0.005
selected_algorithm = candidate_level_parametric_actor_critic_lite
selected_seed = 23
validation_policy_net_return_after_fee_tax = 1.0241872
validation_baseline_net_return_after_fee_tax = 0.96228725
validation_excess_return_after_fee_tax = 0.06189995
participation_ratio = 0.66942149
action_count_ratio = 0.6893617
baseline_clone_flag = False
max_single_day_gain_share = 0.1341401107
max_single_day_loss_share = 0.1377755239
top_symbol_contribution_share = 0.2189674301
```

Train selected:

```text
train_policy_net_return_after_fee_tax = 3.11377764
train_baseline_net_return_after_fee_tax = 1.94413967
train_excess_return_after_fee_tax = 1.16963797
```

## 5. Compliance With Mainline

```text
strict_test_used = false
prl2_used = false
prl3_used = false
ltr_used = false
oracle_used_for_training = false
oracle_used_for_reward_shaping = false
production_allowed = false
```

## 6. Issues / Blockers / Deviations

Return gate:

```text
validation_excess_return_after_fee_tax > 0 = True
```

Participation / action-count gate:

```text
participation_ratio >= 0.85 and action_count_ratio >= 0.80 = False
selected participation_ratio = 0.66942149
selected action_count_ratio = 0.6893617
```

Baseline clone gate:

```text
baseline_clone_flag = False
```

Concentration gate:

```text
single_day_extreme_flag = False
single_symbol_dominance_flag = False
```

本阶段虽通过 validation return gate，但 selected policy 未通过 participation/action-count gate，因此按工作文档停止，不运行 strict_test。

## 7. Files Changed

```text
scripts/run_tw_policy_prl1_r1_candidate_policy_training.py
data_tw/experiments/portfolio_rl_research/prl1_r1_candidate_policy_training/*
docs/tw_portfolio_decision_model/POLICY_PRL1_R1_CANDIDATE_POLICY_TRAINING_EXECUTION_REPORT_CN.md
```

## 8. Recommendation For Reviewer

```text
FAIL_STOP_OR_COORDINATOR_DECISION
```
