---
created_at: 2026-07-13
status: coordinator_mainline
route: TADR6_TRADINGAGENTS_INDEPENDENT_DECISION_PILOT_AND_OVERLAY_GATE
coordinator: Codex
research_only: true
production_allowed: false
provider_pull_allowed: false
provider_publish_allowed: false
accepted_latest_switch_allowed: false
qlib_refresh_allowed: false
readonly_latest_publish_allowed: false
openai_or_tradingagents_real_run_allowed_by_default: false
replay_backtest_oos_allowed_by_default: false
broker_order_allowed: false
target_output_allowed: false
max_phase_count: 5
route_must_close_after_p4: true
---

# TADR6 TradingAgents Independent Decision Pilot And Overlay Gate Mainline

## 1. Goal

TADR6 是一条短支线，用最小成本回答一个问题：

```text
TradingAgents 能不能作为独立决策模型产生可审计、非零、可评估的 include/exclude/rank 决策？
```

如果浅试结果不好，TADR6 必须关闭独立决策方向，并把后续重心转回：

```text
TradingAgents as auxiliary overlay for current best decision model
```

TADR6 不追求一次性做出更高收益策略。它只判断独立成模是否值得继续。

## 2. Non-Goals

TADR6 不做：

```text
不接入生产
不更新 latest/default/provider/accepted latest
不刷新 qlib
不读 provider/latest 或 accepted latest
不读 raw/_raw_runs/_memory/latest
不读 PCOM/order/target/sizing
不生成 order/target/sizing
不连接 broker
不发布 ReadonlyStrategySnapshot
不修改 current best strategy/model defaults
不自动跑 replay/backtest/OOS
不自动调用 OpenAI/TradingAgents real run
不声明收益提升
不声明 TA beats baseline
不声明 OOS/backtest validation
不声明 production readiness 或可交易性
```

## 3. Current Facts

TADRE3 已关闭：

```text
TADRE3-E26 verdict=PASS
closure_decision=CLOSE_TADRE3_METRIC_PRODUCING_FEASIBILITY_BRANCH
default_future_route=STOP_AND_ARCHIVE_THIS_BRANCH
```

TADRE3-E25 的关键事实：

```text
E25 metric chain passed.
leakage_fail_stop=pass
sample_gate=pass
paired_row_count=36
TA variant actions were all rank_only.
baseline and TA used identical paired row ids and identical E13 outcomes.
paired TA-minus-baseline h1 difference=0.0
paired TA-minus-baseline h5 difference=0.0
```

由此得到 TADR6 的起点：

```text
Current TA integration can be evaluated, but it does not create differentiated decisions.
The next useful experiment is not more evaluation of the same rank_only ledger.
The next useful experiment is a constrained independent-decision pilot that forces an auditable action contract.
```

## 4. Strict Route Control

TADR6 最多 5 个阶段：

```text
P0: Mainline And Scope Freeze
P1: Independent Decision Contract Design
P2: Independent Pilot Action Generation Approval Or Stop
P3: Independent Pilot Evaluation
P4: Interpretation And Overlay Gate Closure
```

Hard rule:

```text
No P5.
No automatic replay/backtest/OOS.
No automatic overlay implementation.
No automatic data expansion.
No automatic prompt redesign loop.
```

Repair rule:

```text
Each phase may have at most one repair step: Pn-R.
Pn-R may only repair evidence, schema, validator, or documentation needed for the same phase.
Pn-R must not introduce a new research question, new source family, new metric family, new execution engine, or new production path.
If Pn-R still fails, STOP or close the route with no-go.
```

## 5. Required Agent Workflow

Every phase must use executor and reviewer roles.

For each phase:

```text
Coordinator writes/approves work document.
Executor performs exactly the approved phase and writes execution report.
Reviewer audits artifacts and writes review.
Reviewer may write the next work document only if it stays inside this mainline.
```

Reviewer verdicts:

```text
PASS
PASS_WITH_LIMITATIONS
FAIL_NEEDS_REPAIR
STOP
```

No phase may be considered complete without a review document.

## 6. Source Boundary

Default allowed source classes:

```text
TADRE3-E26 closure artifacts
TADRE3-E25 summary artifacts
E21/E13/E16 artifacts only if a phase explicitly approves them
static docs/contracts in docs/tw_portfolio_decision_model
```

Default forbidden source classes:

```text
prices.csv
provider/latest
accepted latest
qlib source stores
raw/_raw_runs/_memory/latest
PCOM/order/target/sizing
production/default/latest publish targets
network/OpenAI/TradingAgents real run
broker/order routes
```

OpenAI/TradingAgents real run is allowed only if a later work document explicitly requests it and the user explicitly approves:

```text
network=true
OpenAI/LLM=true
TradingAgents real run=true
exact rows=true
exact prompt/action schema=true
no production writes=true
```

## 7. Decision Contract

The independent pilot must produce an action ledger with this minimal schema:

```text
row_id
symbol
signal_asof
candidate_context_ref
ta_decision_action: include | exclude | rank_only
ta_confidence: low | medium | high
reason_code
evidence_flags
source_ref
schema_version
```

Disallowed action fields:

```text
target_weight
target_position
quantity
shares
lots
price_target
stop_loss
take_profit
portfolio_weight
order_type
broker_instruction
```

## 8. Hard Go / No-Go Gates

### Action Diversity Gate

Independent pilot must show non-trivial differentiated actions:

```text
minimum include_or_exclude_rate >= 20% of rows
rank_only_rate <= 80% of rows
at least 2 action classes present
reason_code missing rate = 0
schema_valid_rate = 100%
```

If this fails:

```text
TADR6 independent decision direction = NO-GO
Skip P3 performance-like evaluation
Proceed directly to P4 closure and recommend overlay route.
```

### Evaluation Gate

P3 may run only if P2 passes the Action Diversity Gate.

P3 may evaluate only:

```text
row-level exploratory outcome diagnostics
baseline comparison on identical approved row universe
coverage and action distribution
```

P3 must not evaluate:

```text
Sharpe
drawdown
portfolio NAV
turnover-adjusted net return
full replay/backtest/OOS
production readiness
tradability
```

### Independent Model Continuation Gate

Independent decision route may continue beyond TADR6 only if all are true:

```text
Action Diversity Gate passes.
Leakage/source gate passes.
Evaluation gate produces interpretable non-zero action outcome differences.
No forbidden source or metric is used.
Reviewer says PASS or PASS_WITH_LIMITATIONS.
User explicitly approves a new route.
```

Otherwise:

```text
Close independent route.
Recommend TA overlay for current best model.
```

## 9. Phase Plan

### P0 - Mainline And Scope Freeze

Objective:

```text
Create and review this mainline. Freeze strict route scope, phase cap, repair cap, source boundary, action schema, and go/no-go gates.
```

Allowed:

```text
read prior docs and E26 closure
write this mainline
write P0 execution report
write P0 review
```

Forbidden:

```text
no source payload read
no TA/OpenAI run
no metric computation
no replay/backtest/OOS
```

Exit:

```text
PASS -> P1
FAIL_NEEDS_REPAIR -> P0-R only
STOP -> ask user
```

### P1 - Independent Decision Contract Design

Objective:

```text
Design independent TA action schema, prompt constraints, validator, exact candidate sample selection rule, and artifact names.
```

P1 is design-only.

Required outputs:

```text
independent_action_schema.json
prompt_contract.md
candidate_sample_plan.json
validator_contract.json
action_diversity_gate.json
claim_boundary.json
execution_report.md
review.md
```

Exit:

```text
PASS -> P2 approval/stop
FAIL_NEEDS_REPAIR -> P1-R only
STOP -> close or ask user
```

### P2 - Independent Pilot Action Generation Approval Or Stop

Objective:

```text
Decide whether to generate independent TA action ledger on a fixed small sample.
```

P2 must specify:

```text
exact rows
exact input fields
exact TA/OpenAI/network permission if needed
exact output schema
exact validator
no production writes
```

If user approves actual action generation, P2 may produce:

```text
ta_independent_action_ledger.jsonl
action_schema_validation.json
action_diversity_gate_result.json
safety_boundary_audit.json
execution_report.md
review.md
```

Mandatory stop:

```text
If Action Diversity Gate fails, skip P3 and go directly to P4 closure.
```

### P3 - Independent Pilot Evaluation

Objective:

```text
Evaluate P2 action ledger only if P2 produced meaningful include/exclude/rank_only diversity.
```

Allowed metrics:

```text
action_count_by_class
coverage_count
row-level h1/h5 outcome summary by action class
baseline-vs-TA row-level exploratory comparison on approved identical universe
```

Forbidden:

```text
Sharpe
drawdown
NAV
turnover-adjusted net return
replay/backtest/OOS
production/trading claim
```

Exit:

```text
PASS/PASS_WITH_LIMITATIONS -> P4
FAIL_NEEDS_REPAIR -> P3-R only
STOP -> P4 closure with limitations
```

### P4 - Interpretation And Overlay Gate Closure

Objective:

```text
Close TADR6. Decide independent go/no-go and whether future work should focus on overlay.
```

Required closure decisions:

```text
INDEPENDENT_NO_GO_OVERLAY_RECOMMENDED
INDEPENDENT_PROMISING_NEW_ROUTE_REQUIRED
STOP_AND_ARCHIVE
```

Default if evidence is weak:

```text
INDEPENDENT_NO_GO_OVERLAY_RECOMMENDED
```

P4 must not start overlay implementation. It may only recommend a separate overlay mainline.

## 10. Forbidden Claims

TADR6 must not claim:

```text
TA improves returns
TA beats current best model
TA is production ready
TA is tradable
TA is OOS validated
TA has backtest validation
TA should replace current best decision model
```

Allowed claims:

```text
Independent action generation is feasible / infeasible.
Action diversity gate passed / failed.
Row-level exploratory diagnostics suggest / do not suggest further study.
Overlay route is recommended / not recommended.
```

## 11. Stop Conditions

Stop immediately if:

```text
phase would need unapproved source reads
phase would need unapproved OpenAI/TradingAgents/network
phase would need prices.csv/provider/latest/qlib/raw/_memory/PCOM/order/target/sizing
phase would need replay/backtest/OOS before P3 approval
Action Diversity Gate fails
schema validity is below 100%
executor wants to add a new phase beyond P4
reviewer cannot verify evidence
```

## 12. Closure Criteria

TADR6 closes when:

```text
P4 review exists
independent go/no-go is explicit
overlay recommendation is explicit
all future work is marked separate-route-only
forbidden action audit is clean
no automatic continuation remains
```

## 13. First Executor Command

```text
Read this TADR6 mainline and prior E26 closure review. P0 review must already exist or be completed before P1 starts. Execute P1 only: design the Independent Decision Contract package. Do not read source payloads, do not call OpenAI/TradingAgents/network, do not compute metrics, do not run replay/backtest/OOS, and do not make performance or production claims. Write P1 execution report and artifacts for reviewer audit.
```

## 14. First Reviewer Audit Brief

```text
Audit P1 against TADR6 mainline. Confirm action schema, prompt contract, sample plan, validator, action diversity gate, source boundary, and claim boundary are strict enough to prevent route drift. If P1 passes, write P2 approval/stop work document. If it fails, write P1-R repair work only. Do not approve any OpenAI/TradingAgents/network/source payload read unless explicitly scoped for P2 and user approval.
```
