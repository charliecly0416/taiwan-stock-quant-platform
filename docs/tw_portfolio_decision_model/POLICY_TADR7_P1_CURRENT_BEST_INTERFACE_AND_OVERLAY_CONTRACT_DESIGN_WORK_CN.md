---
created_at: 2026-07-13
status: approved
route: TADR7_TRADINGAGENTS_AUXILIARY_OVERLAY_FOR_CURRENT_BEST_MODEL
phase: TADR7-P1 Current-Best Interface And Overlay Contract Design
research_only: true
design_only: true
---

# TADR7-P1 Current-Best Interface And Overlay Contract Design Work Order

## Objective

Design the read-only interface between the current best model outputs and TradingAgents auxiliary overlay annotations.

P1 is design-only. It must not read current-best payloads or source payloads.

## Required Outputs

```text
current_best_interface_contract.json
overlay_annotation_schema.json
prompt_contract.md
validator_contract.json
auxiliary_only_gate.json
source_boundary.json
claim_boundary.json
safety_boundary_audit.json
validator_result.json
execution_report.md
review.md
```

## Required Design Decisions

```text
future current-best input field allowlist
future current-best input field forbidden list
overlay annotation schema
prompt constraints
validator stages
Auxiliary-Only Gate
Overlay Usefulness Gate
P2 exact-source approval requirements
claim boundary
```

## Forbidden Actions

```text
Do not read current-best payload.
Do not read source payload.
Do not call OpenAI/TradingAgents/network.
Do not generate overlay annotations.
Do not compute metrics.
Do not run replay/backtest/OOS.
Do not modify current-best defaults.
Do not generate order/target/sizing.
Do not publish production/default/latest.
Do not make return-improvement, OOS, production, or trading claims.
```
