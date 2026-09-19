---
created_at: 2026-07-10T07:16:21+00:00
status: work_document
route: RSPPR_READONLY_SNAPSHOT_BUILDER_PUBLISH_ROUTE
phase: RSPPR2_CANDIDATE_ONLY_SNAPSHOT_PUBLISH
target_asof: 2026-07-08
requires_rsppr1_reviewer_pass: true
readonly_snapshot_artifact_write_allowed: true
readonly_snapshot_latest_write_allowed: true
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

# RSPPR2 Candidate-only Snapshot Publish Work

## 1. Objective

RSPPR2 仅在 RSPPR1 reviewer PASS 后，把 RSPPR1 已验证的 candidate-only payload plan 写成 readonly snapshot artifact，并更新 `readonly_strategy_snapshot/latest.json` 指向该 readonly snapshot。RSPPR2 不构建或发布 Agent prompt。

## 2. Required Inputs

必须读取：

```text
docs/tw_portfolio_decision_model/POLICY_RSPPR_READONLY_SNAPSHOT_BUILDER_PUBLISH_ROUTE_MAINLINE_CN.md
docs/tw_portfolio_decision_model/POLICY_RSPPR1_CANDIDATE_ONLY_SNAPSHOT_DRY_RUN_EXECUTION_REPORT_CN.md
docs/tw_portfolio_decision_model/POLICY_RSPPR1_CANDIDATE_ONLY_SNAPSHOT_DRY_RUN_REVIEW_CN.md
data_tw/experiments/readonly_snapshot_builder_publish_route/rsppr1_candidate_only_snapshot_dry_run/source_preflight.json
data_tw/experiments/readonly_snapshot_builder_publish_route/rsppr1_candidate_only_snapshot_dry_run/candidate_snapshot_payload_plan.json
data_tw/experiments/readonly_snapshot_builder_publish_route/rsppr1_candidate_only_snapshot_dry_run/latest_pointer_payload_plan.json
data_tw/experiments/readonly_snapshot_builder_publish_route/rsppr1_candidate_only_snapshot_dry_run/validator_dry_run.json
data_tw/experiments/readonly_snapshot_builder_publish_route/rsppr1_candidate_only_snapshot_dry_run/checksum_plan.json
data_tw/experiments/readonly_snapshot_builder_publish_route/rsppr1_candidate_only_snapshot_dry_run/rollback_preflight.json
data_tw/experiments/readonly_snapshot_builder_publish_route/rsppr1_candidate_only_snapshot_dry_run/forbidden_action_audit.json
```

## 3. Allowed Writes

```text
data_tw/artifacts/publish/readonly_strategy_snapshot/2026-07-08/manifest.json
data_tw/artifacts/publish/readonly_strategy_snapshot/2026-07-08/strategy_snapshot.json
data_tw/artifacts/publish/readonly_strategy_snapshot/2026-07-08/validation_report.json
data_tw/artifacts/publish/readonly_strategy_snapshot/2026-07-08/forbidden_scope_audit.json
data_tw/artifacts/publish/readonly_strategy_snapshot/2026-07-08/checksum_manifest.json
data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json
data_tw/experiments/readonly_snapshot_builder_publish_route/rsppr2_candidate_only_snapshot_publish/*.json
docs/tw_portfolio_decision_model/POLICY_RSPPR2_CANDIDATE_ONLY_SNAPSHOT_PUBLISH_EXECUTION_REPORT_CN.md
docs/tw_portfolio_decision_model/POLICY_RSPPR3_SNAPSHOT_READONLY_INTEGRATION_ACCEPTANCE_WORK_CN.md
```

## 4. Required Evidence

必须生成：

```text
pre_publish_fingerprint.json
written_snapshot_artifact.json
latest_pointer_write.json
validator_publish.json
checksum_manifest_verify.json
rollback_package.json
forbidden_action_audit.json
artifact_manifest.json
```

## 5. Required Checks

```text
RSPPR1 reviewer PASS
RSPPR1 source_preflight.status=pass
RSPPR1 candidate_snapshot_payload_plan.status=pass
RSPPR1 latest_pointer_payload_plan.status=pass
RSPPR1 validator_dry_run.status=pass
RSPPR1 checksum_plan.status=pass
RSPPR1 rollback_preflight.status=pass
target snapshot dir collision clear before write
previous readonly_strategy_snapshot/latest.json bytes backed up and sha256 recorded
written snapshot files match RSPPR1 payload plan checksums
checksum_manifest excludes itself and matches written snapshot files
latest pointer points only to readonly_strategy_snapshot/2026-07-08/manifest.json
candidate_only=true
exit_candidates=[]
hold_candidates=[]
exit_hold_context_status=not_built_no_strategy_replay
no Agent prompt build/publish
no provider/qlib accepted latest, legacy option_c, frontend/API/default, model, strategy, replay, order, monitor, OpenAI action
```

## 6. Forbidden Actions

RSPPR2 禁止：

```text
provider/network pull
provider publish
provider or qlib accepted latest switch
legacy option_c latest signal switch
model scoring or training
strategy replay
OrderIntentArtifact generation
ReplayResult/NAV generation
Agent prompt build/publish
OpenAI call
frontend/API/default switch
monitor/broker/order
trade target or size output
```

## 7. Pass Gate

RSPPR2 PASS 条件：

```text
pre_publish_fingerprint.status=pass
written_snapshot_artifact.status=pass
latest_pointer_write.status=pass
validator_publish.status=pass
checksum_manifest_verify.status=pass
rollback_package.status=pass
forbidden_action_audit.all_false=true
artifact_manifest.status=pass
```
