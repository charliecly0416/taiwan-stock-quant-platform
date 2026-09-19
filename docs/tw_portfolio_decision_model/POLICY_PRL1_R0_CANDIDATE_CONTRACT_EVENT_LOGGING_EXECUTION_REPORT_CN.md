---
created_at: 2026-06-22T07:05:31+00:00
status: executed_prl1_r0_candidate_contract_event_logging
phase: PRL1_R0_CANDIDATE_LEVEL_CONTRACT_AND_EVENT_LOGGING_REPAIR
mainline_doc: docs/tw_portfolio_decision_model/POLICY_PRL_PORTFOLIO_RL_MAINLINE_CN.md
work_document: docs/tw_portfolio_decision_model/POLICY_PRL1_R0_CANDIDATE_CONTRACT_EVENT_LOGGING_WORK_CN.md
artifact_root: data_tw/experiments/portfolio_rl_research/prl1_r0_candidate_contract_event_logging
strict_test_used: false
no_rl_training: true
production_allowed: false
recommendation: PASS_READY_FOR_COORDINATOR_DECIDE_PRL1_R1_CANDIDATE_POLICY_TRAINING
---

# PRL1-R0 Candidate-level Contract And Event Logging 执行报告

## 1. Scope

本轮只执行 PRL1-R0：candidate-level / pair-level action contract、event-level NAV contribution logging、exact attribution audits、validator 和 golden samples。

明确未执行：

```text
PPO / DQN / A2C / supervised policy training
strict_test
oracle action/return training label
oracle reward shaping
PRL2 / PRL3
qlib+LTR
production/default/Agent/provider/broker/monitor/frontend 扩权
```

## 2. Artifacts

artifact root:

```text
data_tw/experiments/portfolio_rl_research/prl1_r0_candidate_contract_event_logging/
```

核心产物：

```text
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
manifest.json
```

## 3. Evidence

event_level_nav_log_sample 覆盖：

```text
splits = ['train', 'validation']
action_types = ['baseline_reference', 'buy', 'hold', 'invalid', 'sell', 'switch']
fee_tax_non_null_examples = 433
invalid_action_examples = 144
```

candidate action bounds:

```text
buy_candidates = top20
sell_candidates = current holdings only, max10
switch_pairs = top5 weak holdings x top10 candidates, cap20/day
max_buy_count <= 3
max_sell_count <= 3
max_switch_pair_count <= 3
```

validator:

```text
status = PASS_PRL1_R0_VALIDATOR
ok = True
strict_test_used = false
no_rl_training = true
oracle_used_for_training = false
oracle_used_for_reward_shaping = false
```

golden samples:

```text
status = PASS_PRL1_R0_GOLDEN_SAMPLES
```

## 4. Safety Boundary

Action contract 和 intent-level slate 禁止输出：

```text
target_position
target_weight
quantity
execution_price
execution_date
broker_order
cash amount
quick_trade
```

event-level replay 日志包含 NAV / fee_tax / reward 仅用于历史 simulation attribution，不反写到 ActionDecision / OrderIntent。

## 5. Recommendation

```text
PASS_READY_FOR_COORDINATOR_DECIDE_PRL1_R1_CANDIDATE_POLICY_TRAINING
```
