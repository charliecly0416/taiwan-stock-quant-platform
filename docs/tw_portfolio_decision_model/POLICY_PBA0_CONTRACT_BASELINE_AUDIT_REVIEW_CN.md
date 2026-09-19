---
created_at: 2026-06-22
status: review_pass_ready_for_pba1_work_document
phase_reviewed: PBA0_CONTRACT_BASELINE_AUDIT
mainline_doc: docs/tw_portfolio_decision_model/POLICY_PBA_BASELINE_ANCHORED_ACTIVE_POLICY_MAINLINE_CN.md
work_doc: docs/tw_portfolio_decision_model/POLICY_PBA0_CONTRACT_BASELINE_AUDIT_WORK_CN.md
execution_report: docs/tw_portfolio_decision_model/POLICY_PBA0_CONTRACT_BASELINE_AUDIT_EXECUTION_REPORT_CN.md
artifact_root: data_tw/experiments/baseline_anchored_active_policy/pba0_contract_baseline_audit
verdict: PASS_READY_FOR_PBA1_BASELINE_SNAPSHOT_BUILD_AND_PARITY_REPLAY_WORK
strict_test_authorized: false
training_authorized: false
pba1_authorized_by_mainline: true
production_allowed: false
readonly_only: true
simulation_only: true
not_order: true
not_target_weight: true
not_target_position: true
not_quantity: true
---

# PBA0 Contract / Baseline Snapshot / Research Audit 审查报告

## 1. 审查结论

结论：

```text
PASS_READY_FOR_PBA1_BASELINE_SNAPSHOT_BUILD_AND_PARITY_REPLAY_WORK
```

执行者完成了 PBA0 授权范围：

```text
1. R1-R8 Research Adoption Audit 已逐项输出。
2. BaselineActionSnapshotArtifact schema 已定义。
3. ActivePolicyDecisionArtifact schema 已定义。
4. PBAReplayResultArtifact schema 已定义。
5. Layer A/B/C baseline-anchored active action space 已定义。
6. cash/no-trade 防退化 gate 已设计。
7. forbidden consumer audit 已覆盖。
8. validator / golden samples 已设计。
9. 未训练模型。
10. 未运行收益 replay。
11. 未运行或读取 strict_test。
12. 未输出 OrderIntent / target_weight / target_position / quantity / broker_order。
13. 未做 provider/latest/monitor/frontend/Agent/broker/production 扩权。
```

本审查允许按 PBA 主线进入：

```text
PBA1: Baseline Snapshot Build And Parity Replay
```

但 PBA1 仍不授权训练，不授权 active policy 选择，不授权 strict_test。

## 2. 证据核查

artifact root：

```text
data_tw/experiments/baseline_anchored_active_policy/pba0_contract_baseline_audit/
```

确认存在：

```text
manifest.json
research_adoption_audit.csv
baseline_action_snapshot_schema.json
active_policy_decision_schema.json
pba_replay_result_schema.json
action_space_design.md
cash_no_trade_degeneracy_gate_design.md
forbidden_consumer_audit.csv
validator_design.md
golden_sample_design.md
```

评价：

```text
PASS
```

## 3. Research Adoption Audit

`research_adoption_audit.csv` 覆盖 PBA 主线 R1-R8：

```text
R1 Active Portfolio Management / active return
R2 Residual Policy Learning
R3 FinRL
R4 EIIE / PGPortfolio
R5 Transaction cost / no-trade region literature
R6 Contextual bandit / LinUCB
R7 Offline RL: CQL / IQL / BCQ
R8 Alpha / signal combination and meta-labeling
```

字段覆盖工作文档要求：

```text
paper_or_method
original_problem_setting
baseline_or_benchmark
state_definition
action_definition
reward_or_label
cost_model
why_it_may_work_here
why_it_may_fail_here
adopted_component
rejected_component
required_contract_or_artifact_change
PBA_phase_mapping
```

评价：

```text
PASS
```

审计明确区分了 PBA 与 PAL free allocation：PBA 采用 baseline-anchored active overlay / residual policy 思想，拒绝 free allocation vector 与 target_weight 生产语义。

## 4. Artifact 合同审查

### 4.1 BaselineActionSnapshotArtifact

`baseline_action_snapshot_schema.json` 包含主线必需字段：

```text
date
instrument
baseline_rank
baseline_score
baseline_action_type
baseline_position_before_diagnostic
baseline_position_after_diagnostic
baseline_holding_age
baseline_candidate_reason
source_signal_artifact
simulation_only
readonly_research_only
production_allowed
```

并禁止：

```text
target_weight
target_position
quantity
order_size
broker_order
future_return / label / realized_pnl
```

评价：

```text
PASS
```

该 schema 能支持 PBA1 构建 baseline action snapshot 与 parity replay 所需的上下文。

### 4.2 ActivePolicyDecisionArtifact

`active_policy_decision_schema.json` 包含：

```text
baseline_action_type
active_decision_type
active_overlay_delta_diagnostic
participation_flag_diagnostic
risk_asset_exposure_flag_diagnostic
source_policy_id
source_baseline_snapshot_artifact
forbidden_consumers
```

并明确禁止：

```text
target_weight
target_position
quantity
order_size
broker_order
```

评价：

```text
PASS
```

PBA0 没有把 active overlay diagnostic 映射成 OrderIntent 或目标仓位。

### 4.3 PBAReplayResultArtifact

`pba_replay_result_schema.json` 包含：

```text
net_return_after_fee_tax
gross_return
turnover
fee
sell_tax
cost_drag
drawdown
participation_rate
risk_asset_exposure
cash_dominance_rate
baseline_excess_return_after_fee_tax
action_concentration
pnl_concentration
seed_stability
strict_test_used
```

评价：

```text
PASS
```

该 schema 把 primary metric 固定为 after-fee-tax，并保留了防 cash/no-trade 退化所需指标。

## 5. Action Space 与防退化 Gate

`action_space_design.md` 定义了：

```text
Layer A: participation / gating
Layer B: threshold / breadth
Layer C: active tilt, diagnostic only
```

并明确：

```text
No free allocation vector.
No target_weight or target_position.
No cash-only/no-trade success claim.
Layer C never enters OrderIntent / broker / frontend / Agent / provider / monitor.
```

评价：

```text
PASS
```

`cash_no_trade_degeneracy_gate_design.md` 定义了：

```text
minimum_participation_rate
minimum_risk_asset_exposure
maximum_cash_dominance_rate
minimum_baseline_action_coverage
minimum_buy_candidate_coverage
minimum_sell_review_coverage
```

评价：

```text
PASS_WITH_PBA1_ENFORCEMENT
```

PBA0 只需设计 gate；PBA1 必须把这些 gate dry-run 成可计算 audit 字段，并报告 baseline 本身的 participation / risk exposure / cash dominance / action coverage。

## 6. Forbidden Actions Audit

`forbidden_consumer_audit.csv` 覆盖并禁止：

```text
OrderIntentArtifact
StrategyRule production path
production replay / product default
frontend default
Agent prompt / Agent recommendation
broker / quick-trade / real order
provider publish / accepted latest switch
monitor scan / config / alerts
```

允许消费者仅限：

```text
PBA readonly research env
PBA readonly replay
PBA validator / audit / review report
```

`manifest.json` 与执行报告确认：

```text
training_run = false
replay_return_run = false
strict_test_used = false
order_intent_output = false
target_weight_output = false
target_position_output = false
quantity_or_broker_output = false
free_allocation_vector_allowed = false
```

评价：

```text
PASS
```

## 7. Validator / Golden Samples

`validator_design.md` 覆盖：

```text
research_adoption_audit_complete
baseline_action_snapshot_schema_complete
active_policy_decision_schema_complete
pba_replay_result_schema_complete
layer_a_b_c_action_space_complete
cash_no_trade_degeneracy_gates_defined
forbidden_consumers_complete
no_training_run
no_return_replay_run
strict_test_not_used
no_order_intent_output
no_target_weight
no_target_position
no_quantity
no_broker_order
no_provider_monitor_frontend_agent_production
```

`golden_sample_design.md` 覆盖：

```text
positive baseline snapshot / active decision / replay result cases
negative target_weight / target_position / quantity / broker_order
negative OrderIntentArtifact consumer
negative strict_test metrics access
negative cash-only / no-trade pass claim
negative free allocation vector action
negative gross-return-only pass claim
```

评价：

```text
PASS
```

## 8. Findings

### Critical

无。

### High

无。

### Medium

PBA1 必须把 PBA0 的防退化 gate 设计落成 dry-run audit，不能只沿用文字说明。

影响：

```text
如果 PBA1 无法计算 baseline action coverage、participation、risk exposure、cash dominance，
后续 PBA2 active overlay 会再次面临 cash/no-trade 形式通过风险。
```

处理：

```text
已在 PBA1 工作文档中列为必须产物和通过条件。
```

### Low

无。

## 9. 下一步控制

允许进入：

```text
PBA1: Baseline Snapshot Build And Parity Replay
```

对应工作文档：

```text
docs/tw_portfolio_decision_model/POLICY_PBA1_BASELINE_SNAPSHOT_BUILD_AND_PARITY_REPLAY_WORK_CN.md
```

仍禁止：

```text
训练模型
active policy validation selection
strict_test
OrderIntent
target_weight / target_position / quantity / broker_order
provider/latest/monitor/frontend/Agent/broker/production
free allocation vector
```
