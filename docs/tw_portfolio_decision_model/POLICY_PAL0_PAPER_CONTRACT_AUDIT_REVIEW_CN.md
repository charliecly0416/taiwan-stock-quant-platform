---
created_at: 2026-06-22
status: review_pass_ready_for_pal1_work_document
phase_reviewed: PAL0_PAPER_IMPLEMENTATION_AUDIT_AND_CONTRACT_ADAPTATION_FREEZE
mainline_doc: docs/tw_portfolio_decision_model/POLICY_PAL_PAPER_ALIGNED_PORTFOLIO_ALLOCATION_RL_MAINLINE_CN.md
execution_report: docs/tw_portfolio_decision_model/POLICY_PAL0_PAPER_CONTRACT_AUDIT_EXECUTION_REPORT_CN.md
artifact_root: data_tw/experiments/paper_aligned_portfolio_rl/pal0_paper_contract_audit
verdict: PASS_READY_FOR_PAL1_ENV_TENSOR_MEMORY_BUILD_WORK
strict_test_authorized: false
pal1_authorized_by_mainline: true
training_authorized: false
production_allowed: false
readonly_only: true
simulation_only: true
not_order: true
not_target_position: true
not_target_weight: true
---

# PAL0 Paper Contract Audit 审查报告

## 1. 审查结论

结论：

```text
PASS_READY_FOR_PAL1_ENV_TENSOR_MEMORY_BUILD_WORK
```

执行者完成了 PAL0 的授权范围：

```text
1. R1-R8 paper implementation audit 已输出；
2. 已明确 portfolio allocation vector / previous portfolio memory / price tensor / after-cost reward 是论文机制核心；
3. 已识别 allocation vector 与本项目 OrderIntent target_weight / target_position 禁令的冲突；
4. 已冻结 simulation-only AllocationDiagnosticArtifact；
5. 已设计 forbidden consumers、research-only replay adapter、state tensor、portfolio memory、reward schema；
6. validator / golden sample 设计覆盖关键正负样本；
7. 未训练模型；
8. 未运行 validation return replay；
9. 未运行 strict_test；
10. 未修改 OrderIntent / StrategyRule production contract；
11. 未做 provider/latest/monitor/frontend/Agent/broker/production 扩权。
```

本审查允许按 PAL 主线进入下一步：

```text
PAL1: Allocation Env / Tensor / Memory Build
```

但 PAL1 仍不授权训练、不授权 validation 收益结论、不授权 strict_test。

## 2. 证据核查

### 2.1 必需产物

artifact root：

```text
data_tw/experiments/paper_aligned_portfolio_rl/pal0_paper_contract_audit/
```

审查确认产物完整：

```text
manifest.json
paper_implementation_audit.csv
contract_adaptation_decision.md
allocation_diagnostic_schema.json
research_only_allocation_replay_adapter_schema.json
state_tensor_schema.json
portfolio_memory_schema.json
reward_schema.json
forbidden_consumer_audit.csv
validator_design.md
golden_sample_design.md
```

评价：

```text
PASS
```

### 2.2 Paper Implementation Audit

`paper_implementation_audit.csv` 覆盖 R1-R8：

```text
R1 FinRL
R2 FinRL-Meta
R3 EIIE
R4 EIIE stock-market replication/adaptation
R5 PPO
R6 DDPG
R7 SAC
R8 Portfolio Choice with Transaction Costs
```

审计字段覆盖主线要求：

```text
paper_mechanism
required_state
required_action
required_reward
training_method
transaction_cost_model
baseline_used_in_paper
reported_market_frequency
what_can_be_adopted
what_conflicts_with_current_contract
required_adapter_or_contract_change
risk_if_adapted_to_tw_stock
```

评价：

```text
PASS
```

PAL0 没有把论文路线简单写成“继续 intent policy”，而是明确区分了 paper allocation vector / PVM / price tensor / after-cost reward 与此前 PRL buy/sell/switch intent 的机制差异。

### 2.3 Contract Adaptation Decision

`contract_adaptation_decision.md` 的核心决策：

```text
allow AllocationDiagnosticArtifact only as simulation-only readonly research artifact
production contracts are not changed
OrderIntentArtifact and StrategyRule production path continue to forbid target_weight / target_position / quantity
```

评价：

```text
PASS
```

该决策解决了主线要求的关键冲突：允许 PAL 后续构建论文级 allocation environment，但不把 allocation vector 暴露为真实仓位、目标权重或订单意图。

### 2.4 AllocationDiagnosticArtifact Schema

`allocation_diagnostic_schema.json` 要求字段包括：

```text
allocation_weight_diagnostic
previous_allocation_weight_diagnostic
rebalance_delta_diagnostic
cash_weight_diagnostic
simulation_only
readonly_research_only
production_allowed
forbidden_consumers
```

并明确：

```text
allocation_weight_diagnostic forbidden to rename or map to target_weight
production_allowed = false
not_order = true
not_investment_advice = true
```

禁止字段：

```text
target_weight
target_position
quantity
execution_price
broker_order
order_id
quick_trade
```

评价：

```text
PASS_WITH_CONDITION
```

PAL1 必须继续使用 `_diagnostic` 后缀，不得在实现中引入无后缀的 `weight`、`target_weight`、`position`、`target_position` 字段。

### 2.5 Forbidden Consumer Audit

`forbidden_consumer_audit.csv` 明确禁止：

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
PAL readonly research env
PAL readonly allocation replay
PAL validator / audit / review report
```

评价：

```text
PASS
```

### 2.6 State / Memory / Reward Schema

`state_tensor_schema.json` 允许：

```text
qlib rank/score/raw_score/score_rank/full_qlib_rank
past-only OHLCV tensor
past returns
MA5/MA10/MA20/MA60
past volatility
portfolio diagnostic memory
transaction cost state
PIT-safe market state
```

禁止：

```text
future_return
forward_return
label
realized_pnl as feature
future_price
same_day_unavailable_data
strict_test_metrics
oracle_action
oracle_return
```

`portfolio_memory_schema.json` 将 previous allocation memory 限定为 diagnostic memory。

`reward_schema.json` 采用：

```text
portfolio value relative change after transaction costs
```

并要求：

```text
turnover_cost_audit
transaction_cost_sensitivity
concentration_audit
baseline_parity_before_training
```

评价：

```text
PASS
```

### 2.7 Validator / Golden Sample Design

validator design 覆盖：

```text
R1-R8 exactly once
_diagnostic suffix
simulation_only / readonly_research_only / production_allowed=false
forbidden consumers
no OrderIntent / target_weight / target_position / quantity / broker output
state feature leakage checks
after-fee-tax reward
no training / no validation return / no strict_test in PAL0
```

golden sample design 覆盖正样本与负样本，包括：

```text
OrderIntentArtifact attempting to consume allocation_weight_diagnostic
Agent prompt / frontend default / provider publish / monitor consuming allocation diagnostic
state tensor containing future_return / label / future_price / realized_pnl / strict_test metric / oracle_return
PAL0 artifact claiming validation return / strict_test result / trained policy
```

评价：

```text
PASS
```

## 3. Findings

### Critical

无。

### High

无。

### Medium

M1. PAL1 必须把 PAL0 的 validator/golden sample 从设计升级为可执行 artifact。

PAL0 只需设计 validator/golden sample，因此本轮通过。但 PAL1 若构建 env/tensor/memory，必须输出实际 validator_report 和 golden_samples_report，而不能只继续停留在设计文档。

M2. AllocationDiagnosticArtifact 的字段安全依赖命名隔离。

后续实现必须严格禁止：

```text
target_weight
target_position
quantity
execution_price
broker_order
```

同时避免用无后缀字段如：

```text
weight
position
rebalance_delta
allocation_weight
```

这些字段容易被误接入生产或 Agent 语义。

### Low

L1. `paper_implementation_audit.csv` 的 source verification 是摘要/官方页面级别，不是全文逐段复核。

这对 PAL0 合同冻结足够；PAL2 若进入具体算法实现，应要求执行者读取对应论文关键实现段落或官方代码，并说明实现差异。

## 4. 主线合规性

对照 PAL 主线：

```text
PAL0 paper audit：PASS
contract adaptation freeze：PASS
AllocationDiagnosticArtifact design：PASS
forbidden consumer audit：PASS
state tensor / memory / reward schema：PASS
validator/golden sample design：PASS
未训练：PASS
未 validation return replay：PASS
未 strict_test：PASS
未 OrderIntent target/quantity/broker：PASS
未 production/default/Agent/provider/frontend/monitor 扩权：PASS
```

## 5. 只读安全边界审查

关键词扫描命中：

```text
target_weight
target_position
quantity
broker_order
quick_trade
provider publish
accepted latest
monitor
Agent
frontend
OrderIntent
strict_test
```

审查判断：命中位于允许上下文：

```text
1. 禁止字段列表；
2. forbidden consumers；
3. negative golden samples；
4. manifest false flags；
5. execution report 的 non-goals confirmed。
```

未发现真实训练、收益 replay、strict_test、OrderIntent 输出、target/quantity/broker 输出或生产扩权。

## 6. 下一步控制

本审查允许进入主线下一阶段：

```text
PAL1_ALLOCATION_ENV_TENSOR_MEMORY_BUILD
```

PAL1 只能构建 paper-aligned environment / tensor / memory / baseline parity / cost audit，不允许训练策略，不允许 strict_test。

## 7. 给执行者的下一步

下一步工作文档：

```text
docs/tw_portfolio_decision_model/POLICY_PAL1_ALLOCATION_ENV_TENSOR_MEMORY_BUILD_WORK_CN.md
```
