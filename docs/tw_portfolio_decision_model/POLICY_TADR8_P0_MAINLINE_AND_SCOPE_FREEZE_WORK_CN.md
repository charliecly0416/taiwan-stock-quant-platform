---
created_at: 2026-07-14
status: work_order
route: TADR8_TRADINGAGENTS_EXTERNAL_EVIDENCE_RISK_SUMMARIZER
phase: TADR8-P0 Mainline And Scope Freeze
research_only: true
---

# TADR8-P0 Mainline And Scope Freeze Work

## 1. Objective

Freeze the TADR8 route as an external evidence compressor/risk summarizer line.

P0 must confirm that TADR8 is not:

```text
a decision model
a current-best row overlay execution
a replay/backtest/OOS route
a production integration route
an order/target/sizing route
```

## 2. Required Reads

Executor may read:

```text
docs/tw_portfolio_decision_model/POLICY_TADR8_TRADINGAGENTS_EXTERNAL_EVIDENCE_RISK_SUMMARIZER_MAINLINE_CN.md
docs/tw_portfolio_decision_model/POLICY_TADR7_P4_INTERPRETATION_AND_ROUTE_CLOSURE_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_TADR7_P4_INTERPRETATION_AND_ROUTE_CLOSURE_EXECUTION_REPORT_CN.md
docs/tw_portfolio_decision_model/POLICY_TADR6_P4_INTERPRETATION_AND_OVERLAY_GATE_CLOSURE_REVIEW_CN.md
```

If a listed TADR6/TADR7 document is missing, executor may note it as a limitation but must not expand source discovery broadly.

## 3. Required Outputs

Write artifact root:

```text
data_tw/experiments/tradingagents_external_evidence_risk_summarizer/tadr8_p0_mainline_scope_freeze/
```

Required artifacts:

```text
scope_freeze_decision.json
route_boundary.json
phase_plan_freeze.json
source_boundary.json
forbidden_action_audit.json
claim_boundary.json
validator_result.json
execution_report.md
```

Write execution report:

```text
docs/tw_portfolio_decision_model/POLICY_TADR8_P0_MAINLINE_AND_SCOPE_FREEZE_EXECUTION_REPORT_CN.md
```

## 4. Forbidden Actions

P0 must not:

```text
read external evidence payloads
read current-best payloads
read prices.csv/provider/latest/accepted latest/qlib/raw/_memory/PCOM/order/target/sizing
call OpenAI/network/TradingAgents
generate risk summaries
generate overlay annotations
compute metrics
run replay/backtest/OOS
modify current-best defaults
generate order/target/sizing
publish production/default/latest
create P5
```

## 5. Expected Decision

Expected P0 decision:

```text
TADR8_SCOPE_FROZEN_PROCEED_TO_P1_DESIGN_ONLY
```

P1, if approved later, must be design-only.
