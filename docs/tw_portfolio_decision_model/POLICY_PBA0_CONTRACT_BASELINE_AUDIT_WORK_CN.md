---
created_at: 2026-06-22
status: reviewer_first_work_document
phase: PBA0_CONTRACT_BASELINE_AUDIT
mainline_doc: docs/tw_portfolio_decision_model/POLICY_PBA_BASELINE_ANCHORED_ACTIVE_POLICY_MAINLINE_CN.md
previous_pal_review: docs/tw_portfolio_decision_model/POLICY_PAL2_R_COST_AWARE_CONCENTRATION_CONSTRAINED_EIIE_REVIEW_CN.md
artifact_root: data_tw/experiments/baseline_anchored_active_policy/pba0_contract_baseline_audit
strict_test_authorized: false
training_authorized: false
replay_return_authorized: false
production_allowed: false
readonly_only: true
simulation_only: true
not_order: true
not_target_weight: true
not_target_position: true
not_quantity: true
---

# PBA0 Contract / Baseline Snapshot / Research Audit 工作文档

## 1. 本轮目标

你是执行者。请启动 PBA Baseline-anchored Active Policy 主线的第一步：

```text
PBA0: Contract / Baseline Snapshot / Research Audit
```

本轮只做合同冻结、baseline snapshot 设计、active overlay action space 设计、研究采用审计和 validator / golden samples 设计。

本轮不训练、不运行收益 replay、不运行 strict_test。

PBA 是新主线，必须以 baseline 为锚点学习 active overlay，不得沿用 PAL free allocation 路线。

## 2. 必须读取

执行前必须读取：

```text
docs/tw_portfolio_decision_model/POLICY_PBA_BASELINE_ANCHORED_ACTIVE_POLICY_MAINLINE_CN.md
docs/tw_portfolio_decision_model/POLICY_PAL2_R_COST_AWARE_CONCENTRATION_CONSTRAINED_EIIE_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_PAL2_R_COST_AWARE_CONCENTRATION_CONSTRAINED_EIIE_EXECUTION_REPORT_CN.md
docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md
docs/tw_modular_contracts/NEW_MODEL_AND_STRATEGY_DEVELOPER_GUIDE_CN.md
docs/tw_modular_contracts/MODEL_SIGNAL_CONTRACT_CN.md
docs/tw_modular_contracts/STRATEGY_RULE_CONTRACT_CN.md
docs/tw_modular_contracts/ORDER_INTENT_CONTRACT_CN.md
docs/tw_modular_contracts/REPLAY_RESULT_CONTRACT_CN.md
```

## 3. 本轮必须完成

必须完成以下内容：

```text
1. 审计 PBA 主线 R1-R8 研究/方案，并输出 Research Adoption Audit。
2. 定义 BaselineActionSnapshotArtifact schema。
3. 定义 ActivePolicyDecisionArtifact schema。
4. 定义 PBAReplayResultArtifact schema。
5. 定义 Layer A/B/C active action space。
6. 定义 participation / risk exposure / cash dominance 防退化 gates。
7. 设计 forbidden consumer audit。
8. 设计 validator。
9. 设计 golden samples。
10. 写 PBA0 execution report。
```

## 4. Research Adoption Audit 要求

`research_adoption_audit.csv` 必须逐项覆盖 PBA 主线 R1-R8：

```text
R1 Active Portfolio Management / active return
R2 Residual Policy Learning
R3 FinRL
R4 EIIE / PGPortfolio
R5 Transaction cost / no-trade region literature
R6 Contextual bandit / LinUCB
R7 Offline RL: CQL / IQL / BCQ
R8 Alpha / signal combination 与 meta-labeling
```

每一项必须包含字段：

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

不能只列论文名，必须说明 PBA 采用和拒绝的机制。

## 5. Artifact Schema 要求

### 5.1 BaselineActionSnapshotArtifact

必须定义可支持 PBA1 baseline parity 的 schema，至少包含：

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

该 artifact 用于记录 baseline 在每个 rebalance date 的候选动作和组合状态。字段含 `_diagnostic` 时，不得映射为 OrderIntent。

### 5.2 ActivePolicyDecisionArtifact

必须定义 active overlay 决策 schema，至少包含：

```text
date
instrument
baseline_action_type
active_decision_type
active_decision_score
active_decision_reason_code
active_overlay_delta_diagnostic
participation_flag_diagnostic
risk_asset_exposure_flag_diagnostic
source_policy_id
source_baseline_snapshot_artifact
simulation_only
readonly_research_only
production_allowed
forbidden_consumers
```

必须明确禁止字段：

```text
target_weight
target_position
quantity
order_size
broker_order
```

### 5.3 PBAReplayResultArtifact

必须定义 readonly research replay 内部使用的结果 schema，至少包含：

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

## 6. Action Space 设计要求

`action_space_design.md` 必须按三层定义 PBA active overlay action space：

```text
Layer A: participation / gating
  allow_baseline_buy
  block_baseline_buy
  allow_baseline_sell
  delay_baseline_sell
  no_extra_action

Layer B: threshold / breadth
  require_score_gap
  require_score_zscore
  dynamic_topk_expand_or_shrink_diagnostic
  market_risk_reduce_participation_diagnostic

Layer C: active tilt, diagnostic only
  overweight_top_ranked_diagnostic
  underweight_low_edge_candidate_diagnostic
  cap_low_score_holding_diagnostic
```

必须明确：

```text
1. action 以 baseline action / baseline portfolio 为锚点。
2. 不允许 free allocation vector。
3. Layer C 只能 simulation-only diagnostic，不得进入 OrderIntent target_weight。
4. 不允许 all-cash policy without explicit risk-off justification。
```

## 7. Cash / No-trade 防退化 Gate

`cash_no_trade_degeneracy_gate_design.md` 必须定义 hard gates：

```text
minimum_participation_rate
minimum_risk_asset_exposure
maximum_cash_dominance_rate
minimum_baseline_action_coverage
minimum_buy_candidate_coverage
minimum_sell_review_coverage
```

必须明确失败场景：

```text
长期现金
长期不交易
长期 block baseline buy
只交易极少日期
通过低成本/低换手/低回撤替代收益目标
```

通过条件不能只看：

```text
cost 低
turnover 低
drawdown 低
concentration pass
```

primary metric 必须是：

```text
net_return_after_fee_tax
```

## 8. Forbidden Consumer Audit

`forbidden_consumer_audit.csv` 必须覆盖并禁止：

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

## 9. Validator / Golden Samples 设计

`validator_design.md` 必须至少设计检查：

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

`golden_sample_design.md` 必须包含正负样本：

```text
positive: BaselineActionSnapshotArtifact can represent baseline buy/sell/hold context.
positive: ActivePolicyDecisionArtifact can represent allow/block/delay/threshold diagnostic decisions.
positive: PBAReplayResultArtifact can represent after-fee-tax replay metrics with participation/cash gates.
negative: target_weight field must fail.
negative: target_position field must fail.
negative: quantity / broker_order must fail.
negative: OrderIntentArtifact consumer must fail.
negative: strict_test metrics access must fail.
negative: cash-only / no-trade policy pass claim must fail.
negative: free allocation vector action must fail.
negative: validation pass based on gross return must fail.
```

## 10. 输出产物

artifact root：

```text
data_tw/experiments/baseline_anchored_active_policy/pba0_contract_baseline_audit/
```

必须输出：

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

必须写执行报告：

```text
docs/tw_portfolio_decision_model/POLICY_PBA0_CONTRACT_BASELINE_AUDIT_EXECUTION_REPORT_CN.md
```

## 11. 本轮禁止事项

本轮禁止：

```text
1. 训练模型。
2. 运行收益 replay。
3. 运行或读取 strict_test。
4. 输出 OrderIntent。
5. 输出 target_weight / target_position / quantity / broker_order。
6. provider publish / accepted latest switch。
7. monitor write / frontend default / Agent integration。
8. broker / quick-trade / real order。
9. 生产默认策略切换。
10. 从零自由 portfolio allocation。
11. 用 cash-only / no-trade 作为成功。
12. 用 gross return 替代 after-fee-tax return。
13. 用 validation 或 strict_test 反复调参。
```

## 12. 执行报告要求

执行报告必须包括：

```text
1. Scope：说明只做 PBA0。
2. Documents read：列出本工作文档要求读取的文档。
3. Research audit summary：说明 R1-R8 是否逐项审计。
4. Contract artifacts：列出三个 schema 和 action/gate 设计。
5. Forbidden actions audit：明确未训练、未 replay、未 strict_test、未输出 OrderIntent/target_weight/target_position/quantity/broker。
6. Evidence produced：列出 artifact root 下全部产物。
7. Issues / blockers / deviations：如合同冲突无法解决必须 STOP。
8. Recommendation：只能是 PASS_READY_FOR_REVIEWER_TO_AUDIT_PBA0 或 STOP_FOR_CONTRACT_CLARIFICATION。
```

如果发现合同无法安全区分 active overlay diagnostic 与 OrderIntent / target_weight / target_position / quantity，必须：

```text
STOP_FOR_CONTRACT_CLARIFICATION
```

不得继续到 PBA1。
