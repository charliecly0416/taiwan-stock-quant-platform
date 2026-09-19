---
created_at: 2026-07-13
status: coordinator_mainline
route: TADR7_TRADINGAGENTS_AUXILIARY_OVERLAY_FOR_CURRENT_BEST_MODEL
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

# TADR7 TradingAgents Auxiliary Overlay For Current Best Model Mainline

## 1. Goal

TADR7 接受 TADR6 的结论：

```text
TradingAgents independent decision branch = NO-GO
Recommended direction = TradingAgents as auxiliary overlay for current best decision model
```

TADR7 的目标不是让 TA 独立选股、替代当前最优模型、或直接提高收益率声明，而是先验证一个更保守的问题：

```text
TA 能否对当前最优决策模型已经产生的候选/持仓/排除对象，产出可审计的辅助 overlay 标注？
```

允许研究的 overlay 形态：

```text
risk_flag
data_gap_flag
event_uncertainty_flag
analyst_disagreement_flag
human_review_priority
neutral_context_note
```

TADR7 的默认定位：

```text
current best model remains primary decision source
TA overlay is read-only auxiliary context
TA overlay cannot create buy/sell/order/sizing decisions
```

## 2. Non-Goals

TADR7 不做：

```text
不替代当前最优模型
不修改 current best strategy/model defaults
不接入生产
不更新 latest/default/provider/accepted latest
不刷新 qlib
不读 provider/latest 或 accepted latest
不读 raw/_raw_runs/_memory/latest
不读 PCOM/order/target/sizing
不生成 order/target/sizing
不连接 broker
不发布 ReadonlyStrategySnapshot
不自动跑 replay/backtest/OOS
不自动调用 OpenAI/TradingAgents real run
不声明收益提升
不声明 TA beats baseline
不声明 OOS/backtest validation
不声明 production readiness 或可交易性
```

## 3. Current Facts

TADR6 已关闭：

```text
closure_decision=INDEPENDENT_NO_GO_OVERLAY_RECOMMENDED
independent_decision_branch=closed_no_go
schema_validation.status=pass
Action Diversity Gate=fail
include=0
exclude=0
rank_only=12
```

TADR6 的可复用事实：

```text
TA/LLM 可以按 schema 产出可验证 artifact。
在独立决策任务上，严格 frozen context 下没有产生 include/exclude diversity。
因此后续不应继续独立决策，而应把 TA 限制为辅助 overlay。
```

## 4. Strict Route Control

TADR7 最多 5 个阶段：

```text
P0: Mainline And Scope Freeze
P1: Current-Best Interface And Overlay Contract Design
P2: Frozen Overlay Input Approval Or Stop
P3: Auxiliary Overlay Annotation Execution Approval Or Stop
P4: Interpretation And Route Closure
```

Hard rule:

```text
No P5.
No automatic replay/backtest/OOS.
No automatic production integration.
No automatic current-best model/default change.
No automatic prompt retry loop.
No automatic source expansion.
```

Repair rule:

```text
Each phase may have at most one repair step: Pn-R.
Pn-R may only repair evidence, schema, validator, or documentation needed for the same phase.
Pn-R must not introduce a new source family, metric family, execution engine, production path, or independent-decision route.
If Pn-R still fails, STOP or close the route.
```

Anti-sprawl / route convergence amendment:

```text
Remaining substantive work after P1 is limited to P2, P3, and P4.
P2 is approval/stop-only by default and may use only document-level or file-name-level evidence unless the user explicitly approves exact payload read execution.
No P2R/P2X/P3X split is allowed unless a hard blocker makes the approved phase impossible and the split remains same-scope.
No same-phase repair may be used to expand sources, add metrics, add replay/backtest/OOS, add production integration, or retry prompts for better labels.
P3 may perform at most one overlay annotation execution after explicit approval; no automatic prompt retry loop is allowed.
P4 must close this route and any further evaluation/productization must be a separate route.
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

No phase may be considered complete without a review document.

## 6. Source Boundary

Default allowed source classes:

```text
TADR6 closure artifacts
TADR6 P3-X validation/gate artifacts
static docs/contracts in docs/tw_portfolio_decision_model
existing current-best model/interface docs only if a phase explicitly approves them
candidate/holding/exclusion artifacts only if a phase explicitly approves exact paths and fields
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
exact frozen input artifacts=true
exact overlay schema=true
no production writes=true
no order/target/sizing=true
```

## 7. Overlay Contract Direction

TADR7 overlay output must be auxiliary-only. It may include:

```text
row_id
symbol
signal_asof
primary_model_ref
overlay_context_ref
overlay_label: risk_flag | data_gap_flag | event_uncertainty_flag | analyst_disagreement_flag | human_review_priority | neutral_context_note
overlay_severity: low | medium | high
overlay_confidence: low | medium | high
evidence_flags
reason_code
source_ref
schema_version
```

Forbidden output fields:

```text
buy
sell
hold
include
exclude
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
expected_return
probability_of_profit
Sharpe
drawdown
NAV
production_readiness
```

## 8. Hard Gates

### Auxiliary-Only Gate

Every overlay artifact must satisfy:

```text
schema_valid_rate=100%
forbidden_decision_field_count=0
forbidden_order_sizing_field_count=0
unapproved_source_ref_count=0
primary_model_decision_unchanged=true
production_publish=false
```

If this fails:

```text
STOP or Pn-R only
```

### Overlay Usefulness Gate

Overlay may continue only if it shows non-empty, auditable auxiliary coverage without becoming a decision engine:

```text
overlay_record_count equals frozen input count
reason_code_missing_rate=0
at least one non-neutral auxiliary label exists, or a documented all-neutral result closes the route
human_review_priority labels must not imply buy/sell/sizing
```

If the result is all neutral or unactionable:

```text
Close route or recommend a narrower overlay question.
Do not force labels by prompt retry.
```

### Evaluation Gate

TADR7 P0-P4 does not run performance evaluation. Any replay/backtest/OOS or return comparison requires a separate route after P4.

## 9. Phase Plan

### P0 - Mainline And Scope Freeze

Objective:

```text
Create and review this mainline. Freeze route scope, source boundary, overlay-only contract direction, forbidden actions, and closure criteria.
```

Allowed:

```text
read TADR6 closure artifacts
write this mainline
write P0 execution report
write P0 review
```

Forbidden:

```text
no current-best payload read
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

### P1 - Current-Best Interface And Overlay Contract Design

Objective:

```text
Design the exact read-only interface between current best model outputs and TA overlay annotations.
```

P1 is design-only unless explicitly approved otherwise.

Required outputs:

```text
current_best_interface_contract.json
overlay_annotation_schema.json
prompt_contract.md
validator_contract.json
auxiliary_only_gate.json
source_boundary.json
claim_boundary.json
execution_report.md
review.md
```

### P2 - Frozen Overlay Input Approval Or Stop

Objective:

```text
Decide whether to read exact current-best candidate/holding/exclusion artifacts and freeze a small overlay input set.
```

P2 must specify:

```text
exact source paths
exact allowed fields
exact forbidden fields
exact row selection rule
candidate_overlay_input_frozen.json contract
context_manifest.json contract
```

### P3 - Auxiliary Overlay Annotation Execution Approval Or Stop

Objective:

```text
Decide whether to run TA/LLM overlay annotation on frozen inputs.
```

P3 must specify:

```text
exact frozen inputs
exact prompt and overlay schema
network/OpenAI/TradingAgents permission if needed
validator and auxiliary-only gate
no production writes
no order/target/sizing
```

If explicitly approved, P3 may execute only overlay annotation and validators, not metrics or replay.

### P4 - Interpretation And Route Closure

Objective:

```text
Close TADR7. Decide whether TA overlay annotation is feasible enough to justify a separate evaluation/productization route.
```

Required closure decisions:

```text
OVERLAY_FEASIBLE_SEPARATE_EVALUATION_ROUTE_RECOMMENDED
OVERLAY_NOT_USEFUL_STOP_AND_ARCHIVE
OVERLAY_BLOCKED_BY_SOURCE_OR_SAFETY
```

P4 must not implement production overlay or run performance evaluation.

## 10. Forbidden Claims

TADR7 must not claim:

```text
TA improves returns
TA beats current best model
TA is production ready
TA is tradable
TA is OOS validated
TA has backtest validation
TA should replace current best decision model
TA overlay should change orders or sizing
```

Allowed claims:

```text
Overlay annotation is feasible / infeasible.
Auxiliary-only gate passed / failed.
Overlay labels are auditable / not auditable.
Further evaluation route is recommended / not recommended.
```

## 11. Stop Conditions

Stop immediately if:

```text
phase would need unapproved source reads
phase would need unapproved OpenAI/TradingAgents/network
phase would need prices.csv/provider/latest/qlib/raw/_memory/PCOM/order/target/sizing
phase would alter current best model decision/default behavior
phase would produce buy/sell/order/sizing fields
phase would run replay/backtest/OOS
executor wants to add a new phase beyond P4
reviewer cannot verify evidence
```

## 12. Closure Criteria

TADR7 closes when:

```text
P4 review exists
overlay feasibility decision is explicit
future work is marked separate-route-only
forbidden action audit is clean
no automatic continuation remains
```
