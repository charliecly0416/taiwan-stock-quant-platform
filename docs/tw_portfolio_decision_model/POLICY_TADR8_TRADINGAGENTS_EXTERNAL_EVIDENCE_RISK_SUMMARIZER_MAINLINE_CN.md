---
created_at: 2026-07-14
status: coordinator_mainline
route: TADR8_TRADINGAGENTS_EXTERNAL_EVIDENCE_RISK_SUMMARIZER
coordinator: Codex
research_only: true
production_allowed: false
provider_pull_allowed_by_default: false
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

# TADR8 TradingAgents External Evidence Risk Summarizer Mainline

## 1. Goal

TADR8 follows the TADR7 closure:

```text
TADR7 closure_decision=OVERLAY_NOT_USEFUL_STOP_AND_ARCHIVE
Reason: schema/gate feasible, but current-best frozen rows without external evidence produced all neutral_context_note.
```

TADR8 changes the role of TradingAgents/LLM:

```text
Do not ask TA to directly annotate current-best decision rows.
Use TA/LLM only as an external evidence compressor and risk summarizer.
```

The research question:

```text
Can TA/LLM transform approved external evidence into auditable, structured risk/context summaries that may later support human review of the current-best model, without generating buy/sell/order/sizing or performance claims?
```

## 2. Non-Goals

TADR8 does not:

```text
replace the current-best model
directly overlay current-best decision rows
join risk summaries to orders, targets, sizing, or production decisions
modify current-best model/strategy defaults
publish production/default/latest
read provider/latest or accepted latest by default
refresh qlib
read raw/_raw_runs/_memory/latest
read PCOM/order/target/sizing
connect broker
run replay/backtest/OOS
compute returns, hit rate, Sharpe, drawdown, NAV, alpha, or PnL
claim return improvement
claim TA beats current-best
claim OOS/backtest/production readiness
```

## 3. Current Facts

TADR6:

```text
independent TA decision branch closed no-go
Action Diversity Gate failed: include=0, exclude=0, rank_only=12
```

TADR7:

```text
overlay annotation schema/gate feasible
P3-R final validator=PASS
record_count=4
label_distribution={"neutral_context_note": 4}
closure_decision=OVERLAY_NOT_USEFUL_STOP_AND_ARCHIVE
```

Inference for TADR8:

```text
TA/LLM should not be used as a decision engine.
TA/LLM may still be useful where it has actual text/evidence to summarize.
Therefore TADR8 isolates external evidence compression before any current-best integration.
```

## 4. Strict Route Control

TADR8 has at most 5 phases:

```text
P0: Mainline And Scope Freeze
P1: External Evidence Packet And Risk Summary Contract Design
P2: Evidence Source Approval Or Stop
P3: Evidence Compression Pilot Execution Approval Or Stop
P4: Interpretation And Route Closure
```

Hard rules:

```text
No P5.
No automatic source expansion.
No automatic OpenAI/TradingAgents real run.
No automatic replay/backtest/OOS.
No automatic production integration.
No direct decision-row overlay inside TADR8.
No current-best default change.
No prompt retry loop to force non-neutral labels.
```

Repair rule:

```text
Each phase may have at most one repair step: Pn-R.
Pn-R may only repair evidence, schema, validator, or documentation needed for the same phase.
Pn-R must not add a new source family, metric family, execution engine, production path, or decision route.
If Pn-R still fails, STOP or close the route.
```

Anti-sprawl amendment:

```text
P0-P4 only.
P1 is design-only.
P2 is approval/stop-only by default and may use only document-level or file-name-level evidence unless user explicitly approves exact payload reads.
P3 may perform at most one evidence compression pilot after explicit approval of exact source paths, allowed fields, LLM/network permission, schema, and validator.
P4 must close the route. Any current-best integration, evaluation, or productization must be a separate route after P4.
```

## 5. Required Agent Workflow

Every phase must use executor and reviewer roles.

For each phase:

```text
Coordinator writes/approves work document.
Executor performs exactly the approved phase and writes execution report.
Reviewer audits artifacts and writes review.
No phase is complete without review.
```

## 6. Source Boundary

Default allowed source classes for P0/P1:

```text
TADR6/TADR7 closure artifacts
static docs/contracts in docs/tw_portfolio_decision_model
static project wiki docs about current-best model only as background
```

Potential future external evidence source classes, not approved until P2:

```text
exchange announcements
company filings
financial report text
earnings call or investor meeting transcripts
company news releases
approved news article excerpts
analyst report metadata or sanitized snippets if licensed/approved
sector event notes
```

Default forbidden source classes:

```text
prices.csv
provider/latest
accepted latest
qlib source stores
raw/_raw_runs/_memory/latest
PCOM/order/target/sizing
broker/order routes
production/default/latest publish targets
unapproved web/network reads
unapproved OpenAI/TradingAgents real run
```

## 7. Evidence Compression Contract Direction

Future TADR8 risk summary output must be evidence-first and auxiliary-only. It may include:

```text
evidence_context_id
symbol
evidence_asof
source_type
source_ref
source_published_at
evidence_window
summary_bullets
risk_context_label:
  data_gap
  event_uncertainty
  regulatory_or_legal_risk
  earnings_quality_risk
  guidance_or_outlook_change
  supply_chain_or_demand_risk
  capital_structure_or_liquidity_risk
  analyst_or_market_disagreement
  no_material_external_risk_found
risk_severity: low | medium | high
risk_confidence: low | medium | high
evidence_coverage_flags
reason_code
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
portfolio_weight
order_type
broker_instruction
entry_price
price_target
stop_loss
take_profit
expected_return
probability_of_profit
Sharpe
drawdown
NAV
production_readiness
tradable
outperform_baseline
```

## 8. Hard Gates

### Evidence-Only Gate

Every future evidence summary artifact must satisfy:

```text
schema_valid_rate=100%
approved_source_ref_count equals total_source_ref_count
forbidden_decision_field_count=0
forbidden_order_sizing_field_count=0
forbidden_performance_field_count=0
current_best_decision_row_join=false
primary_model_decision_unchanged=true
production_publish=false
```

### Usefulness Gate

Evidence summaries may continue only if:

```text
record_count > 0
reason_code_missing_rate=0
source_ref_coverage_rate=100%
at least one record has concrete evidence-supported risk_context_label other than no_material_external_risk_found, or all-neutral result closes the route
```

If all summaries are neutral/no-material-risk:

```text
Close or redesign source selection in a separate route.
Do not prompt-retry to force risk labels.
```

### Evaluation Gate

TADR8 does not evaluate performance. Any later test of whether external evidence summaries improve current-best decision workflow requires a separate reviewed route after P4.

## 9. Phase Plan

### P0 - Mainline And Scope Freeze

Objective:

```text
Create/review this mainline and freeze route boundaries.
```

Allowed:

```text
read TADR6/TADR7 closure artifacts
write mainline, P0 artifacts, execution report, review
```

Forbidden:

```text
no external source payload read
no current-best payload read
no OpenAI/TradingAgents/network
no evidence summaries
no metrics/replay/backtest/OOS
```

### P1 - External Evidence Packet And Risk Summary Contract Design

Objective:

```text
Design external evidence packet schema, risk summary schema, prompt contract, source boundary, validator, evidence-only gate, and claim boundary.
```

P1 is design-only.

### P2 - Evidence Source Approval Or Stop

Objective:

```text
Decide whether any exact external evidence sources may be read for a small pilot.
```

P2 must specify:

```text
exact source paths or URLs
source ownership/licensing boundary
exact allowed fields/snippets
forbidden fields/aliases
symbol/date sample rule
payload read audit plan
validator and stop conditions
```

### P3 - Evidence Compression Pilot Execution Approval Or Stop

Objective:

```text
If explicitly approved, read exact approved evidence payloads and run at most one TA/LLM compression pilot into structured risk summaries.
```

P3 must not join output to current-best decision rows or run performance evaluation.

### P4 - Interpretation And Route Closure

Objective:

```text
Close TADR8. Decide whether external evidence compression is useful enough to justify a separate current-best human-review integration route.
```

Allowed closure decisions:

```text
EVIDENCE_SUMMARIZER_FEASIBLE_SEPARATE_INTEGRATION_ROUTE_RECOMMENDED
EVIDENCE_SUMMARIZER_NOT_USEFUL_STOP_AND_ARCHIVE
EVIDENCE_SUMMARIZER_BLOCKED_BY_SOURCE_OR_SAFETY
```

## 10. Forbidden Claims

TADR8 must not claim:

```text
TA improves returns
TA beats current-best model
TA is production ready
TA is tradable
TA is OOS/backtest validated
TA should change orders, sizing, or model defaults
```

Allowed claims:

```text
External evidence summarization is feasible/infeasible.
Evidence-only gate passed/failed.
Risk summaries are auditable/not auditable.
Separate integration route is recommended/not recommended.
```

## 11. Stop Conditions

Stop immediately if:

```text
phase would need unapproved source reads
phase would need unapproved network/OpenAI/TradingAgents
phase would need prices.csv/provider/latest/accepted latest/qlib/raw/_memory/PCOM/order/target/sizing
phase would alter current-best defaults or decisions
phase would produce buy/sell/order/sizing/performance fields
phase would run replay/backtest/OOS
executor or reviewer tries to add P5
reviewer cannot verify evidence
```

## 12. Closure Criteria

TADR8 closes when:

```text
P4 review exists
closure decision is explicit
future work is marked separate-route-only
forbidden action audit is clean
no automatic continuation remains
```
