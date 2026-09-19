---
created_at: 2026-07-13
status: reviewed
route: TADR7_TRADINGAGENTS_AUXILIARY_OVERLAY_FOR_CURRENT_BEST_MODEL
phase: TADR7-P1 Current-Best Interface And Overlay Contract Design
verdict: PASS_WITH_LIMITATIONS
research_only: true
design_only: true
---

# TADR7-P1 Current-Best Interface And Overlay Contract Design Review

## 1. Review Scope

- Mainline: `docs/tw_portfolio_decision_model/POLICY_TADR7_TRADINGAGENTS_AUXILIARY_OVERLAY_FOR_CURRENT_BEST_MODEL_MAINLINE_CN.md`
- Work order: `docs/tw_portfolio_decision_model/POLICY_TADR7_P1_CURRENT_BEST_INTERFACE_AND_OVERLAY_CONTRACT_DESIGN_WORK_CN.md`
- Execution report: `docs/tw_portfolio_decision_model/POLICY_TADR7_P1_CURRENT_BEST_INTERFACE_AND_OVERLAY_CONTRACT_DESIGN_EXECUTION_REPORT_CN.md`
- Artifact root: `data_tw/experiments/tradingagents_auxiliary_overlay/tadr7_p1_current_best_interface_and_overlay_contract_design/`

This review covers only P1 design artifacts. It does not review current-best payloads, source payloads, OpenAI/TradingAgents runs, overlay annotations, metrics, replay/backtest/OOS, production integration, or current-best default changes.

## 2. Verdict

`PASS_WITH_LIMITATIONS`

P1 is acceptable as a design-only contract package. The independent reviewer found one high-priority contract ambiguity before P2/P3 execution: generic forbidden aliases and unknown/additional fields were not explicit enough. That finding was repaired in the same phase.

## 3. Evidence Checked

Artifacts checked:

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
build_p1_contracts.py
```

Assertion evidence:

```text
tadr7_p1_assertions=pass
p1_repair_assertions=pass
design_only=true
current_best_payload_read=false
source_payload_read=false
auxiliary_only_schema=true
p2_exact_source_approval_required=true
generic_forbidden_aliases_included=true
unknown_fields_rejected=true
```

## 4. Reviewer Finding And Repair

Independent reviewer finding:

```text
High / Must-fix before P2/P3 execution:
The contract should explicitly reject unknown/additional fields and include generic forbidden aliases such as order, sizing, position_size, performance, production, plus snake/camel variants.
```

Repair completed:

```text
current_best_interface_contract.additional_fields_policy=reject_unknown_fields
overlay_annotation_schema.additional_fields_policy=reject_unknown_fields
auxiliary_only_gate.minimum_requirements.unknown_field_count=0
validator_contract requires rejection of unknown/additional fields
generic aliases added: order, sizing, position_size, performance, production, orderIntent, targetWeight, productionReady, expectedReturn, futureReturn, and related snake/camel variants
```

Repair validation:

```text
p1_repair_assertions=pass
generic_forbidden_aliases_included=true
unknown_fields_rejected=true
validator.status=pass
```

## 5. Compliance Findings

### PASS: P1 Stayed Design-Only

P1 did not:

```text
read current-best payloads
read source payloads
call OpenAI/TradingAgents/network
generate overlay annotations
compute metrics
run replay/backtest/OOS
modify current-best defaults
generate order/target/sizing
publish production/default/latest
make return-improvement, OOS, production, or trading claims
```

### PASS: Current-Best Interface Requires P2 Approval

`current_best_interface_contract.json` records:

```text
future_input_artifact_status=requires_p2_exact_source_approval_before_read
primary_model_decision_must_remain_unchanged=true
```

P2 must approve exact source path, exact field allowlist, forbidden field list, row selection rule, source family audit, and frozen input validator before any payload read.

### PASS: Overlay Schema Is Auxiliary-Only

Allowed overlay labels:

```text
risk_flag
data_gap_flag
event_uncertainty_flag
analyst_disagreement_flag
human_review_priority
neutral_context_note
```

Forbidden fields now include decision, order/sizing, generic alias, performance, and production terms.

### PASS: Gates And Validator Are Strict Enough For P2/P3

The gate requires:

```text
schema_valid_rate=1.0
forbidden_decision_field_count=0
forbidden_order_sizing_field_count=0
unknown_field_count=0
unapproved_source_ref_count=0
primary_model_decision_unchanged=true
production_publish=false
reason_code_missing_rate=0.0
```

## 6. Limitations

- P1 did not discover or read actual current-best artifacts.
- P1 did not freeze exact overlay input rows.
- P1 did not approve OpenAI/TradingAgents/network.
- P1 did not generate overlay annotations.
- Future P2 must still be an approval/stop package before any current-best/source payload read.

## 7. Next Work Document

Recommended next phase:

```text
TADR7-P2 Frozen Overlay Input Approval Or Stop
```

P2 must remain approval/stop-only unless explicitly authorized otherwise. It should define:

```text
exact current-best source path candidates
exact allowed fields
exact forbidden fields and alias scan
exact row selection rule
candidate_overlay_input_frozen.json contract
context_manifest.json contract
source-family forbidden list
payload-read execution approval checklist
```

P2 must not:

```text
read current-best/source payload unless explicitly approved in P2
call OpenAI/TradingAgents/network
generate overlay annotations
compute metrics
run replay/backtest/OOS
modify current-best defaults
generate order/target/sizing
publish production/default/latest
make return-improvement, OOS, production, or trading claims
```

## 8. Recommended Approval Wording

```text
批准进入 TADR7-P2 Frozen Overlay Input Approval Or Stop，只做冻结 overlay 输入的执行审批/停止包，明确 exact current-best source path candidates、allowed fields、forbidden fields/aliases、row selection rule、candidate_overlay_input_frozen.json 和 context_manifest.json contract、source boundary、validator 和 claim boundary；默认不读取 current-best payload 或 source payload，不调用 OpenAI/TradingAgents/network，不生成 overlay annotations，不计算 metrics，不运行 replay/backtest/OOS，不修改 current-best defaults，不生成 order/target/sizing，不发布 production/default/latest，不做收益提升、OOS、生产或交易结论。
```
