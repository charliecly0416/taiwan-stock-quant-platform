---
created_at: 2026-06-22T08:30:10+00:00
status: executed_prl1_r1_r_participation_constrained_repair
phase: PRL1_R1_R_PARTICIPATION_CONSTRAINED_CANDIDATE_POLICY_REPAIR
mainline_doc: docs/tw_portfolio_decision_model/POLICY_PRL_PORTFOLIO_RL_MAINLINE_CN.md
work_document: docs/tw_portfolio_decision_model/POLICY_PRL1_R1_R_PARTICIPATION_CONSTRAINED_REPAIR_WORK_CN.md
artifact_root: data_tw/experiments/portfolio_rl_research/prl1_r1_r_participation_constrained_repair
strict_test_used: false
recommendation: FAIL_STOP_OR_COORDINATOR_DECISION
---

# PRL1-R1-R Participation-constrained Candidate Policy Repair 执行报告

## 1. Scope

Assigned phase: `PRL1_R1_R_PARTICIPATION_CONSTRAINED_CANDIDATE_POLICY_REPAIR`

本轮只修 participation/action-count gate、switch concentration 风险和 seed 稳定性，不进入 strict_test / PRL2 / PRL3 / LTR。

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
scripts/run_tw_policy_prl1_r1_r_participation_constrained_repair.py
```

修复方向：

```text
participation_target frontier = 0.65 / 0.75 / 0.85 / 0.95
hard gate = participation_ratio >= 0.85 and action_count_ratio >= 0.80
switch concentration audit / gate = enabled
seed stability audit = enabled
```

PRL1-R0 复用：

```text
candidate_action_schema.json / pair_action_schema.json
event_level_nav_log_schema.json
```

## 3. Evidence Produced

artifact root:

```text
data_tw/experiments/portfolio_rl_research/prl1_r1_r_participation_constrained_repair/
```

validator:

```text
PASS_PRL1_R1_R_VALIDATOR
```

golden samples:

```text
PASS_PRL1_R1_R_GOLDEN_SAMPLES
```

## 4. Validation Result

```text
selected_config_id = RPAIR_seed23_pt75_rank10_gap0.002
selected_algorithm = candidate_level_participation_constrained_actor_critic_lite
selected_seed = 23
selected_participation_target = 0.75
validation_policy_net_return_after_fee_tax = 1.1535769
validation_baseline_net_return_after_fee_tax = 0.96228725
validation_excess_return_after_fee_tax = 0.19128965
validation_participation_ratio = 1.0
validation_action_count_ratio = 1.02978723
baseline_clone_flag = False
low_participation_flag = False
no_action_dominance_flag = False
switch_concentration_flag = True
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
participation_ratio >= 0.85 and action_count_ratio >= 0.80 = True
```

Switch concentration gate:

```text
switch_concentration_flag = True
```

Seed stability gate:

```text
seed_stability_gate_pass = False
```

本轮已修复 participation/action-count gate，但 selected positive-return config 仍触发 switch concentration gate，且 seed stability 未通过；因此按工作文档停止，不运行 strict_test。

## 7. Files Changed

```text
scripts/run_tw_policy_prl1_r1_r_participation_constrained_repair.py
/home/chuliyang/taiwan-stock-quant-platform/data_tw/experiments/portfolio_rl_research/prl1_r1_r_participation_constrained_repair/*
/home/chuliyang/taiwan-stock-quant-platform/docs/tw_portfolio_decision_model/POLICY_PRL1_R1_R_PARTICIPATION_CONSTRAINED_REPAIR_EXECUTION_REPORT_CN.md
```

## 8. Recommendation For Reviewer

```text
FAIL_STOP_OR_COORDINATOR_DECISION
```
