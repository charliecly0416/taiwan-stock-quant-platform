---
created_at: 2026-07-10T07:29:34+00:00
status: work_document
route: RSPPR_READONLY_SNAPSHOT_BUILDER_PUBLISH_ROUTE
phase: RSPPR3_SNAPSHOT_READONLY_INTEGRATION_ACCEPTANCE
target_asof: 2026-07-08
requires_rsppr2_reviewer_pass: true
readonly_snapshot_artifact_write_allowed: false
readonly_snapshot_latest_write_allowed: false
agent_prompt_build_allowed: false
agent_prompt_publish_allowed: false
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

# RSPPR3 Snapshot Readonly Integration Acceptance Work

## 1. Objective

RSPPR3 only validates the published candidate-only `ReadonlyStrategySnapshot` and its latest pointer. It must not build Agent prompt; Agent prompt latest route remains separate and can start only after RSPPR final PASS.

## 2. Required Inputs

```text
docs/tw_portfolio_decision_model/POLICY_RSPPR_READONLY_SNAPSHOT_BUILDER_PUBLISH_ROUTE_MAINLINE_CN.md
docs/tw_portfolio_decision_model/POLICY_RSPPR2_CANDIDATE_ONLY_SNAPSHOT_PUBLISH_EXECUTION_REPORT_CN.md
data_tw/experiments/readonly_snapshot_builder_publish_route/rsppr2_candidate_only_snapshot_publish/*.json
data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json
data_tw/artifacts/publish/readonly_strategy_snapshot/2026-07-08/manifest.json
data_tw/artifacts/publish/readonly_strategy_snapshot/2026-07-08/strategy_snapshot.json
data_tw/artifacts/publish/readonly_strategy_snapshot/2026-07-08/validation_report.json
data_tw/artifacts/publish/readonly_strategy_snapshot/2026-07-08/forbidden_scope_audit.json
data_tw/artifacts/publish/readonly_strategy_snapshot/2026-07-08/checksum_manifest.json
```

## 3. Required Checks

```text
RSPPR2 reviewer PASS
latest pointer points only to data_tw/artifacts/publish/readonly_strategy_snapshot/2026-07-08/manifest.json
published snapshot files match checksum_manifest and RSPPR2 evidence
candidate_only=true
top_candidates=50
exit_candidates=[]
hold_candidates=[]
exit_hold_context_status=not_built_no_strategy_replay
no provider/qlib accepted latest, legacy option_c, frontend/API/default, model, strategy, replay, order, monitor, OpenAI, or Agent prompt action
```

## 4. Allowed Writes

```text
data_tw/experiments/readonly_snapshot_builder_publish_route/rsppr3_snapshot_readonly_integration_acceptance/*.json
docs/tw_portfolio_decision_model/POLICY_RSPPR3_SNAPSHOT_READONLY_INTEGRATION_ACCEPTANCE_EXECUTION_REPORT_CN.md
docs/tw_portfolio_decision_model/POLICY_RSPPR4_FINAL_CLOSURE_AND_AGENT_ROUTE_GATE_WORK_CN.md
```

## 5. Pass Gate

RSPPR3 PASS may recommend final RSPPR closure review. It must not itself start or publish Agent prompt.
