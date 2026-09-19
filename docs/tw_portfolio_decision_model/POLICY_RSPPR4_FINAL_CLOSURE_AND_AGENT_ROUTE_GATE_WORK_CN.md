---
created_at: 2026-07-10T07:41:04+00:00
status: work_document
route: RSPPR_READONLY_SNAPSHOT_BUILDER_PUBLISH_ROUTE
phase: RSPPR4_FINAL_CLOSURE_AND_AGENT_ROUTE_GATE
target_asof: 2026-07-08
requires_rsppr3_reviewer_pass: true
final_closure_allowed: true
agent_route_gate_allowed: true
agent_prompt_build_allowed_in_rsppr4: false
agent_prompt_publish_allowed_in_rsppr4: false
readonly_snapshot_artifact_write_allowed: false
readonly_snapshot_latest_write_allowed: false
provider_pull_allowed: false
network_command_allowed: false
provider_publish_allowed: false
provider_accepted_latest_switch_allowed: false
qlib_accepted_latest_switch_allowed: false
legacy_option_c_latest_signal_switch_allowed: false
model_scoring_allowed: false
strategy_replay_allowed: false
order_intent_allowed: false
replay_result_allowed: false
openai_call_allowed: false
monitor_write_allowed: false
order_or_trade_target_output_allowed: false
production_default_switch_allowed: false
---

# RSPPR4 Final Closure And Agent Route Gate Work

## 1. Objective

RSPPR4 may close the RSPPR route only if RSPPR3 reviewer passes. It may then
record a gate decision that the separate Agent prompt latest route can be opened.

RSPPR4 must not build, publish, or validate Agent prompt artifacts itself.

## 2. Required Inputs

```text
docs/tw_portfolio_decision_model/POLICY_RSPPR_READONLY_SNAPSHOT_BUILDER_PUBLISH_ROUTE_MAINLINE_CN.md
docs/tw_portfolio_decision_model/POLICY_RSPPR3_SNAPSHOT_READONLY_INTEGRATION_ACCEPTANCE_EXECUTION_REPORT_CN.md
data_tw/experiments/readonly_snapshot_builder_publish_route/rsppr3_snapshot_readonly_integration_acceptance/*.json
data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json
data_tw/artifacts/publish/readonly_strategy_snapshot/2026-07-08/manifest.json
```

## 3. Required Checks

```text
RSPPR3 reviewer PASS
latest pointer still points to data_tw/artifacts/publish/readonly_strategy_snapshot/2026-07-08/manifest.json
RSPPR3 evidence all pass
controlled signal latest lineage unchanged
candidate-only safety semantics still present
no provider/model/strategy/replay/order/monitor/OpenAI/default action
no Agent prompt artifact build or publish inside RSPPR
```

## 4. Allowed Writes

```text
data_tw/experiments/readonly_snapshot_builder_publish_route/rsppr4_final_closure_and_agent_route_gate/*.json
docs/tw_portfolio_decision_model/POLICY_RSPPR4_FINAL_CLOSURE_AND_AGENT_ROUTE_GATE_EXECUTION_REPORT_CN.md
docs/tw_portfolio_decision_model/POLICY_RSPPR_FINAL_CLOSURE_REVIEW_CN.md
```

## 5. Pass Gate

If RSPPR4 passes and final reviewer accepts closure, the coordinator may open a
separate Agent prompt latest route with its own work document, contract checks,
validator evidence, and safety review. That later route must not inherit write
permission from RSPPR.
