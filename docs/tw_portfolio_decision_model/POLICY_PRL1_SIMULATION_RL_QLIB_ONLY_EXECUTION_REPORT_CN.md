---
created_at: 2026-06-22T06:16:53+00:00
status: executed_prl1_simulation_rl_qlib_only
phase: PRL1_SIMULATION_RL_QLIB_ONLY
mainline_doc: docs/tw_portfolio_decision_model/POLICY_PRL_PORTFOLIO_RL_MAINLINE_CN.md
work_document: docs/tw_portfolio_decision_model/POLICY_PRL0_ENV_ORACLE_AUDIT_REVIEW_CN.md
artifact_root: data_tw/experiments/portfolio_rl_research/prl1_simulation_rl_qlib_only
recommendation: STOP_OR_PRL1_REPAIR_WITH_COORDINATOR_DECISION
readonly_only: true
simulation_only: true
strict_test_used: false
oracle_upper_bound_used_for_training: false
---

# PRL1 Simulation RL Qlib-only 执行报告

## 1. Scope
本轮执行 PRL1：qlib-only、PRL0 Env v1、train-only simulation RL 训练，validation final selection。未运行 strict_test，未使用 oracle_upper_bound_train.csv 作为训练 label/imitation/reward shaping，未使用 LTR/offline RL。

## 2. Documents / Contracts / Skills Read
已读取 PRL 主线、PRL0 review/work document、PRL0 execution report、PRL feasibility analysis、PE1 repair closure、项目宪法、ModelSignal / StrategyRule / OrderIntent / ReplayResult 合同、coordinator 与 safety-boundary skills。

## 3. Algorithm / Config / Seed
algorithms=['PPO_CATEGORICAL_LITE', 'A2C_CATEGORICAL_LITE', 'DQN_EPS_GREEDY_LITE']; seeds=[11, 23, 37]; episode_count=6; validation_evaluation_count=9。

## 4. Validation Selection
baseline validation return = 0.95376753
selected config = PPO_CATEGORICAL_LITE_seed11
selected validation return = 0.5531104
selected excess return = -0.40065713
selected non_baseline_action_ratio = 0.86363636
selected baseline_action_ratio = 0.13636364

## 5. Seed Stability
mean validation return = 0.30443287
std = 0.23282573
best = 0.5531104
worst = 0.0
majority_above_baseline = False

## 6. Audits
输出 action_template_distribution / baseline_clone / participation / trade_contribution / concentration / forbidden_feature audits。收益不得由 baseline clone 或 no_action 解释；若 gate 未全部满足，则 recommendation 为 STOP。

## 7. Validator / Golden Samples
Validator: PASS_PRL1_VALIDATOR / failed_count=0
Golden: PASS_PRL1_GOLDEN_SAMPLES / failed_count=0

## 8. Forbidden Actions Audit
未触发 strict_test、oracle imitation、supervised/offline RL、CQL/IQL/Decision Transformer、LTR、provider/latest/monitor/frontend/Agent/broker、target_position/target_weight/quantity/broker order。

## 9. Recommendation
```text
STOP_OR_PRL1_REPAIR_WITH_COORDINATOR_DECISION
```
