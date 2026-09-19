---
created_at: 2026-06-22T06:00:19+00:00
status: executed_prl0_env_oracle_audit
phase: PRL0_ENV_ACTION_SPACE_ORACLE_AUDIT_FREEZE
mainline_doc: docs/tw_portfolio_decision_model/POLICY_PRL_PORTFOLIO_RL_MAINLINE_CN.md
artifact_root: data_tw/experiments/portfolio_rl_research/prl0_env_oracle_audit
recommendation: PASS_READY_FOR_PRL1_SIMULATION_RL_WORK_DOCUMENT
readonly_only: true
simulation_only: true
production_allowed: false
not_order: true
not_target_position: true
not_target_weight: true
strict_test_used: false
rl_training_performed: false
---

# PRL0 Env / Action Space / Oracle Audit 执行报告

## 1. Scope

本轮严格执行 PRL0：设计并产出 PortfolioDecisionEnv v1、state/action/reward schema，运行 qlib-only train/validation baseline parity，以及 train-only oracle/random/heuristic rollout audit。未训练 PPO/DQN/A2C，未运行 strict_test，未使用 LTR，未接 provider/latest/monitor/frontend/Agent/broker。

## 2. Documents / Contracts / Skills Read

已读取 PRL 主线、PE1 repair closure、项目宪法、新模型/策略开发手册、ModelSignal / StrategyRule / OrderIntent / ReplayResult 合同，以及 coordinator / new-model / safety-boundary skills。

## 3. Research Adoption Audit

| id | adopted | not adopted |
|---|---|---|
| R1 FinRL | adopt environment/agent/backtest layering, explicit costs, reproducible artifacts | no live trading or continuous target weights |
| R2 EIIE | adopt portfolio state/history/reward design | no continuous target_weight or crypto/high-frequency assumptions |
| R3 PPO | defer to PRL1 as categorical compact-template candidate | no PPO training in PRL0 |
| R4 DQN | defer to PRL1 as fixed discrete-template baseline | no DQN training in PRL0 |
| R5 CQL | coverage risk awareness for later offline RL | no CQL in PRL0/PRL1 |
| R6 IQL | later offline policy improvement candidate after rollout coverage | no IQL in PRL0/PRL1 |
| R7 Decision Transformer | later trajectory diagnostic | not first-version training |
| R8 Transaction Costs | after-fee-tax reward and cost-aware replay | do not optimize low turnover as primary objective |


## 4. Env / State / Action / Reward Schema

Schema 已输出：

```text
data_tw/experiments/portfolio_rl_research/prl0_env_oracle_audit/env_schema.json
data_tw/experiments/portfolio_rl_research/prl0_env_oracle_audit/state_feature_schema.json
data_tw/experiments/portfolio_rl_research/prl0_env_oracle_audit/action_space_schema.json
data_tw/experiments/portfolio_rl_research/prl0_env_oracle_audit/reward_schema.json
```

动作空间包含 A0-A7 compact discrete templates，baseline action 与 non-baseline action 均在 action space 内。

## 5. Baseline Parity

train baseline return = 2.41885797
validation baseline return = 0.95376753

baseline parity status = PASS

## 6. Oracle / Random / Heuristic Train-only Audit

oracle train return = 474.42807854
oracle train excess vs baseline = 472.00922057
random train return = 1.7839844
heuristic train return = -0.02507377

Oracle 是 train-only diagnostic upper bound，使用未来价格只用于 upper-bound 审计，不作为 state feature、训练标签或 validation/strict_test 选择依据。

## 7. Action Coverage / Executability

action coverage status = PASS
executable audit status = PASS

输出：

```text
data_tw/experiments/portfolio_rl_research/prl0_env_oracle_audit/action_coverage_audit.csv
data_tw/experiments/portfolio_rl_research/prl0_env_oracle_audit/executable_action_audit.csv
```

## 8. Validator / Golden Samples

Validator: PASS_PRL0_ENV_ORACLE_AUDIT / failed_count=0
Golden: PASS_PRL0_GOLDEN_SAMPLES / failed_count=0

## 9. Forbidden Actions Audit

未触发 strict_test、PPO/DQN/A2C 训练、LTR、provider publish、accepted latest switch、monitor write、frontend default switch、Agent/OpenAI、broker、quick-trade、真实订单、target_position、target_weight、quantity 输出。

## 10. Recommendation For Reviewer

```text
PASS_READY_FOR_PRL1_SIMULATION_RL_WORK_DOCUMENT
```
