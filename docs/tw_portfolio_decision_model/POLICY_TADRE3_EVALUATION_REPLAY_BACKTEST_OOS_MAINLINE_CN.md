---
created_at: 2026-07-12
status: coordinator_mainline
route: TADRE3_EVALUATION_REPLAY_BACKTEST_OOS
depends_on:
  - POLICY_TADRE2B11_NESTED_SCHEMA_DATASET_BUILD_REVIEW_CN.md
coordinator: Codex
research_only: true
design_route_started: true
actual_evaluation_allowed: false
replay_allowed: false
backtest_allowed: false
oos_allowed: false
latest_publish_allowed: false
qlib_refresh_allowed: false
pcom_mutation_allowed: false
target_output_allowed: false
---

# TADRE3 Evaluation Replay Backtest OOS Mainline

## 1. Goal

TADRE3 研究 B11 产出的 63 行 research-only nested TradingAgents label dataset，是否能在严格 PIT、readonly、安全边界下，设计出可复核的 evaluation / replay / backtest / OOS 比较路线。

用户目标：

```text
走真实评估路线
摸索更好的决策方式
与现有决策方式比较
研究是否有方法能提高收益率
```

TADRE3 的第一阶段目标不是直接证明收益更高，而是先冻结评估协议，使后续任何收益、回测、OOS 或增量价值结论都有可审计依据。

## 2. Current Baseline

Accepted upstream evidence:

```text
B11 nested research dataset build: PASS_WITH_CONDITIONS
dataset_path=data_tw/experiments/tradingagents_decision_evaluation/tadre2b11_nested_schema_dataset_build/nested_research_labels_dataset.jsonl
candidate_rows=63
included_rows=63
excluded_rows=0
validator_status=pass
dataset_written=true
research_only=true
```

B11 constraints carried forward:

```text
B11 outputs may not be used for evaluation/replay/backtest/OOS without a separate approved route.
B11 outputs may not be used for production/latest/provider/qlib/PCOM/order/target/sizing without a separate approved route.
```

This mainline opens that separate approved route only for design and approval packaging first.

## 3. Non-Goals

TADRE3 does not automatically:

```text
run evaluation
run replay
run backtest
run OOS
compute returns
compute Sharpe/drawdown/PnL
claim incremental value
claim higher return
claim ranking improvement
claim probability or production readiness
change production/default model or strategy
publish provider/latest/accepted latest/readonly latest/Agent prompt latest
refresh qlib
mutate PCOM
write OrderIntentArtifact / ReplayResultArtifact / ReadonlyStrategySnapshot
write target_position / target_weight / quantity / shares / lots / sizing
run TradingAgents/network/OpenAI/LLM
read _raw_runs / _memory / raw side-effect content
```

## 4. Route Boundary

Allowed evidence roots:

```text
data_tw/experiments/tradingagents_decision_evaluation/tadre3_e0_evaluation_protocol_design/
data_tw/experiments/tradingagents_decision_evaluation/tadre3_e1_* only after separate approval
```

Allowed document pattern:

```text
docs/tw_portfolio_decision_model/POLICY_TADRE3*_CN.md
```

Forbidden write roots:

```text
data_tw/artifacts/
data_tw/experiments/project_convergence_operations/
production/
latest/
provider/
qlib/
PCOM/
order/
target/
sizing/
```

## 5. Research Questions

TADRE3 may design tests for:

```text
Q1: Does adding nested TradingAgents labels improve review/risk triage quality versus existing qlib/policy context?
Q2: Can label-conditioned overlays identify candidate subsets with different future realized return/risk characteristics under PIT-safe OOS rules?
Q3: Are any observed deltas robust to date split, symbol clustering, placebo labels, and capacity-matched baselines?
Q4: Is the label dataset large and diverse enough for any statistically meaningful evaluation?
```

TADRE3 must distinguish:

```text
triage diagnostics
candidate subset diagnostics
portfolio/backtest performance diagnostics
production/trading suitability
```

Only the first three may be designed under this research route. Production/trading suitability remains forbidden.

## 6. Phase Plan

### E0 - Evaluation Protocol Design And Approval Package

Design-only. No evaluation run.

Outputs:

```text
evaluation_protocol.json
baseline_candidate_contract.json
overlay_definition_contract.json
pit_join_and_oos_split_contract.json
metrics_and_statistics_plan.json
replay_backtest_boundary_contract.json
data_adequacy_and_power_check_plan.json
leakage_and_safety_validator_contract.json
future_execution_approval_checklist.json
safety_boundary_audit.json
E0 execution report
E1 approval-required document
E0 review document
```

### E1 - Preflight Data Availability And Join Feasibility

Only after separate approval. May inspect local existing qlib/candidate context availability but must not run backtest/OOS.

### E2 - Dry-Run Evaluation Join Manifest

Only after separate approval. Build a manifest showing which B11 rows can join to baseline candidate context and market outcomes under PIT rules. No returns computed unless explicitly approved.

### E3 - Research Evaluation Execution

Only after separate approval. May compute predeclared diagnostics and backtest/OOS metrics if E0/E1/E2 pass and contracts name exact inputs/outputs.

### E4 - Independent Review And Decision

Review whether any observed results are meaningful, stable, or insufficient. No production switch.

## 7. E0 Required Decisions

E0 must define:

```text
baseline conditions
candidate overlay conditions
PIT join rule
OOS split rule
market outcome source contract
existing decision method comparison boundary
evaluation metrics definitions
statistical controls
negative controls/placebo checks
minimum data adequacy threshold
forbidden outputs
future approval values required for E1/E2/E3
```

E0 must explicitly decide whether B11's 63 rows are:

```text
sufficient for protocol design
sufficient for join feasibility preflight
insufficient for reliable OOS/backtest claims without more rows
```

## 8. Forbidden Actions

All TADRE3 phases forbid unless later explicitly approved in a narrower work order:

```text
provider pull/publish
accepted latest switch
qlib refresh
daily auto run
crontab change
readonly latest publish
Agent prompt latest publish
OpenAI/LLM call
TradingAgents run
network access
raw side-effect content read
monitor write
broker/quick-trade/order
OrderIntentArtifact generation
ReplayResultArtifact generation unless explicitly scoped as research replay evidence and not production
ReadonlyStrategySnapshot generation
target_position / target_weight / quantity / shares / lots / sizing
production/default switch
production/latest/provider/qlib/PCOM/order/target/sizing mutation
```

## 9. Stop Conditions

Stop and request user/coordinator approval if any next step needs:

```text
actual evaluation/replay/backtest/OOS execution
market outcome label generation
qlib data read beyond static local contract inspection
provider/latest/accepted latest/qlib refresh
network/OpenAI/TradingAgents
raw side-effect content
production/default/latest/PCOM/order/target/sizing touch
claims about returns, higher收益率, OOS value, rank improvement, probability, or production readiness
```

## 10. Closure Criteria

TADRE3 can continue beyond E0 only if:

```text
E0 execution report exists
E0 review PASS or PASS_WITH_CONDITIONS
E1/E2/E3 approval-required document names exact scope
no forbidden action occurred
user/coordinator explicitly approves next phase
```

Actual performance claims require E3 execution and E4 review at minimum.
