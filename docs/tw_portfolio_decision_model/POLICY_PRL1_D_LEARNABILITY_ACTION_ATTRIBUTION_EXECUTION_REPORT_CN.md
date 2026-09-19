---
created_at: 2026-06-22T06:35:57+00:00
status: executed_prl1_d_learnability_action_attribution
phase: PRL1_D_LEARNABILITY_AND_ACTION_ATTRIBUTION_DIAGNOSTIC
mainline_doc: docs/tw_portfolio_decision_model/POLICY_PRL_PORTFOLIO_RL_MAINLINE_CN.md
work_document: docs/tw_portfolio_decision_model/POLICY_PRL1_D_LEARNABILITY_ACTION_ATTRIBUTION_WORK_CN.md
artifact_root: data_tw/experiments/portfolio_rl_research/prl1_d_learnability_action_attribution
recommendation: DIAGNOSTIC_COMPLETE_RECOMMEND_COORDINATOR_DECIDE_PRL1_R
readonly_only: true
simulation_only: true
strict_test_used: false
oracle_used_for_training: false
---

# PRL1-D Learnability And Action Attribution 执行报告

## 1. Scope
本轮只做诊断：baseline imitation sanity check、train-only oracle bucket analysis、action template return attribution、candidate-level redesign proposal。未运行 strict_test，未训练最终收益策略，未用 oracle action/return 做训练、模仿或 reward shaping，未进入 PRL2/PRL3。

## 2. Documents / Contracts / Skills Read
已读取 PRL 主线、PRL1 coordinator opinion、PRL1-D work document、PRL1 review、PRL1 execution report、PRL0 review/execution report、项目宪法、ModelSignal / StrategyRule / OrderIntent / ReplayResult 合同、coordinator 和 safety-boundary skills。

## 3. Baseline Imitation Sanity Check
validation_accuracy = 0.98760331
validation_macro_f1 = 0.86046512
sanity_check_only = true
model_used_as_policy = false

## 4. Oracle Bucket Analysis
bucket_count = 22
oracle_used_for_training = false
oracle_used_for_reward_shaping = false

## 5. Action Template Attribution
attribution_rows = 16
single_day_extreme_contribution = diagnostic fallback; exact NAV event-level share requires richer PRL1 env logging.

## 6. Candidate-level Redesign
Proposal/schema/risk documents written. Recommendation = `DIAGNOSTIC_COMPLETE_RECOMMEND_COORDINATOR_DECIDE_PRL1_R`.

## 7. Validator / Golden Samples
Validator: PASS_PRL1_D_VALIDATOR / failed_count=0
Golden: PASS_PRL1_D_GOLDEN_SAMPLES / failed_count=0

## 8. Forbidden Actions Audit
未触发 strict_test、最终收益策略训练、oracle imitation/reward shaping、PRL2/PRL3、LTR、provider/latest/monitor/frontend/Agent/broker、target_position/target_weight/quantity/broker order。

## 9. Recommendation
```text
DIAGNOSTIC_COMPLETE_RECOMMEND_COORDINATOR_DECIDE_PRL1_R
```
