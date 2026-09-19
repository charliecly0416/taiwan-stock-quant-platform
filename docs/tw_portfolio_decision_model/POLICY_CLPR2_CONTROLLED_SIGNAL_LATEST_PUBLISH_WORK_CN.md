---
created_at: 2026-07-10
status: work_document
route: CLPR_CONTROLLED_LATEST_PUBLISH_ROUTE
phase: CLPR2_CONTROLLED_SIGNAL_LATEST_PUBLISH
target_asof: 2026-07-08
provider_pull_allowed: false
network_command_allowed: false
provider_publish_allowed: false
provider_accepted_latest_switch_allowed: false
qlib_accepted_latest_switch_allowed: false
legacy_option_c_latest_signal_switch_allowed: false
canonical_artifact_write_allowed: true
controlled_signal_latest_pointer_write_allowed: true
readonly_snapshot_publish_allowed: false
agent_prompt_build_allowed: false
agent_prompt_publish_allowed: false
model_scoring_allowed: false
strategy_replay_allowed: false
openai_call_allowed: false
monitor_write_allowed: false
order_or_target_output_allowed: false
production_default_switch_allowed: false
requires_clpr1_reviewer_pass: true
---

# CLPR2 Controlled Signal Latest Publish Work

## 1. Objective

CLPR2 的目标是在 CLPR1 reviewer PASS 后，执行唯一受控 publish 动作：

```text
PBPR3_X verified ModelSignalArtifact
  -> canonical ModelSignalArtifact copy
  -> controlled ModelSignalArtifact latest pointer
```

允许写入范围仅限：

```text
data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/pbpr3x_modela_20260708_contained/*
data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/latest.json
```

CLPR2 不允许写 readonly snapshot latest，不允许写 Agent prompt latest，不允许写 provider/qlib accepted latest，不允许写 legacy option_c latest_signal。

## 2. Required Inputs

Executor 必须读取：

```text
docs/tw_portfolio_decision_model/POLICY_CLPR_CONTROLLED_LATEST_PUBLISH_ROUTE_MAINLINE_CN.md
docs/tw_portfolio_decision_model/POLICY_CLPR2_CONTROLLED_SIGNAL_LATEST_PUBLISH_WORK_CN.md
docs/tw_portfolio_decision_model/POLICY_CLPR1_CANONICAL_SIGNAL_PROMOTION_DRY_RUN_EXECUTION_REPORT_CN.md
docs/tw_portfolio_decision_model/POLICY_CLPR1_CANONICAL_SIGNAL_PROMOTION_DRY_RUN_REVIEW_CN.md
docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md
docs/tw_modular_contracts/MODEL_SIGNAL_CONTRACT_CN.md
data_tw/experiments/controlled_latest_publish_route/clpr1_canonical_signal_promotion_dry_run/source_to_target_file_map.json
data_tw/experiments/controlled_latest_publish_route/clpr1_canonical_signal_promotion_dry_run/target_collision_audit.json
data_tw/experiments/controlled_latest_publish_route/clpr1_canonical_signal_promotion_dry_run/dry_run_copy_plan.json
data_tw/experiments/controlled_latest_publish_route/clpr1_canonical_signal_promotion_dry_run/latest_pointer_payload_plan.json
data_tw/experiments/controlled_latest_publish_route/clpr1_canonical_signal_promotion_dry_run/validator_plan.json
data_tw/experiments/controlled_latest_publish_route/clpr1_canonical_signal_promotion_dry_run/rollback_preflight.json
data_tw/experiments/controlled_latest_publish_route/clpr1_canonical_signal_promotion_dry_run/forbidden_action_audit.json
data_tw/experiments/controlled_latest_publish_route/clpr1_canonical_signal_promotion_dry_run/artifact_manifest.json
```

## 3. Allowed Writes

CLPR2 只允许写：

```text
data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/pbpr3x_modela_20260708_contained/manifest.json
data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/pbpr3x_modela_20260708_contained/signals.csv
data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/pbpr3x_modela_20260708_contained/schema.json
data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/pbpr3x_modela_20260708_contained/coverage_audit.csv
data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/pbpr3x_modela_20260708_contained/forbidden_field_audit.csv
data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/pbpr3x_modela_20260708_contained/validator_report.json
data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/latest.json
data_tw/experiments/controlled_latest_publish_route/clpr2_controlled_signal_latest_publish/*.json
docs/tw_portfolio_decision_model/POLICY_CLPR2_CONTROLLED_SIGNAL_LATEST_PUBLISH_EXECUTION_REPORT_CN.md
docs/tw_portfolio_decision_model/POLICY_CLPR3_READONLY_SNAPSHOT_CANDIDATE_OR_BLOCKER_WORK_CN.md
```

## 4. Required Checks

CLPR2 helper / executor 必须证明：

```text
CLPR1 reviewer verdict allows CLPR2
CLPR1 source_to_target_file_map.status=pass
CLPR1 target_collision_audit.status=pass
CLPR1 dry_run_copy_plan.status=pass
CLPR1 latest_pointer_payload_plan.status=pass
CLPR1 validator_plan.status=pass
CLPR1 rollback_preflight.status=pass
CLPR1 forbidden_action_audit.all_false=true
CLPR1 artifact_manifest.status=pass
canonical directory did not pre-exist before CLPR2 copy
controlled signal latest pointer pre-state is backed up or recorded
copied canonical files match CLPR1 source checksums
latest.json payload matches CLPR1 latest_pointer_payload_plan payload
latest.json points only to canonical manifest/signals
canonical manifest status=READY
signals.csv rows=150
date/signal_asof only 2026-07-08
duplicate date+instrument keys=0
forbidden columns=[]
legacy option_c latest_signal pointers unchanged
readonly snapshot latest unchanged
forbidden_action_audit.all_false=true except the explicitly allowed CLPR2 signal publish flags
artifact_manifest.status=pass
```

## 5. Forbidden Actions

CLPR2 禁止：

```text
writing data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json
writing data_tw/artifacts/agent_daily_prompt/latest.json
writing qlib_pipeline/data_tw/experiments/option_c_daily_signal/latest_signal.json
writing data_tw/experiments/option_c_daily_signal/latest_signal.json
provider/network pull
provider publish
provider accepted latest switch
qlib accepted latest switch
model scoring
strategy replay
ReplayResult/NAV generation
OrderIntentArtifact generation
Agent prompt build/publish
OpenAI call
frontend/API/default switch
monitor/broker/order/target output
```

## 6. Stop Conditions

必须 STOP：

```text
CLPR1 reviewer report missing or not PASS
canonical directory already exists before CLPR2
controlled signal latest pointer has changed since CLPR1 preflight and cannot be backed up
any required source checksum differs from CLPR1 file map
latest payload differs from CLPR1 plan
post-copy validator fails
legacy option_c latest_signal pointer would need to change
readonly snapshot latest would need to change
provider/qlib accepted latest switch is requested
strategy replay, Agent prompt build, OpenAI call, monitor/broker/order, or target output is required
```

## 7. Pass Gate

CLPR2 PASS 条件：

```text
canonical signal artifact exists under allowed path
all six canonical files match CLPR1 planned checksums
controlled signal latest pointer exists and matches planned payload
latest pointer references only canonical manifest/signals
post-publish validator evidence pass
rollback evidence explicit
legacy option_c latest_signal pointers unchanged
readonly snapshot latest unchanged
no provider/qlib accepted latest, Agent prompt latest, default switch, monitor/broker/order/target occurred
```

## 8. Reviewer Brief

Reviewer 必须独立复核 CLPR2 execution report、canonical files、latest pointer payload、checksum、rollback backup、legacy pointer fingerprints 与 forbidden-action audit。

若通过，reviewer 可以建议进入 CLPR3 readonly snapshot candidate/blocker；CLPR3 不得触发 strategy replay 或 OrderIntentArtifact，除非另开受控路线并由用户明确确认。
