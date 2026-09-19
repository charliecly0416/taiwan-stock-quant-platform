---
created_at: 2026-07-10T06:18:37+00:00
status: execution_report
route: CLPR_CONTROLLED_LATEST_PUBLISH_ROUTE
phase: CLPR2_CONTROLLED_SIGNAL_LATEST_PUBLISH
executor: CLPR2_EXECUTOR
target_asof: 2026-07-08
verdict: PASS_RECOMMEND_CLPR3_READONLY_SNAPSHOT_CANDIDATE_OR_BLOCKER
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
---

# CLPR2 Controlled Signal Latest Publish Execution Report

## 1. Verdict

```text
PASS_RECOMMEND_CLPR3_READONLY_SNAPSHOT_CANDIDATE_OR_BLOCKER
```

CLPR2 已执行唯一受控 publish：复制 CLPR1 批准的六个 `ModelSignalArtifact`
文件到 canonical readonly signal 路径，并写入 controlled signal `latest.json`。

## 2. Scope

Allowed writes used:

```text
data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/pbpr3x_modela_20260708_contained/{manifest.json,signals.csv,schema.json,coverage_audit.csv,forbidden_field_audit.csv,validator_report.json}
data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/latest.json
data_tw/experiments/controlled_latest_publish_route/clpr2_controlled_signal_latest_publish/*.json
docs/tw_portfolio_decision_model/POLICY_CLPR2_CONTROLLED_SIGNAL_LATEST_PUBLISH_EXECUTION_REPORT_CN.md
docs/tw_portfolio_decision_model/POLICY_CLPR3_READONLY_SNAPSHOT_CANDIDATE_OR_BLOCKER_WORK_CN.md
```

Non-goals confirmed:

```text
no readonly snapshot latest
no Agent prompt latest
no provider/network pull
no provider publish
no provider or qlib accepted latest switch
no legacy option_c latest_signal switch
no model scoring
no strategy replay
no ReplayResult/NAV
no OrderIntent
no OpenAI call
no frontend/API/default switch
no monitor/broker/order
no target output
```

## 3. Documents / Contracts / Skills Read

```text
docs/tw_portfolio_decision_model/POLICY_CLPR_CONTROLLED_LATEST_PUBLISH_ROUTE_MAINLINE_CN.md
docs/tw_portfolio_decision_model/POLICY_CLPR2_CONTROLLED_SIGNAL_LATEST_PUBLISH_WORK_CN.md
docs/tw_portfolio_decision_model/POLICY_CLPR1_CANONICAL_SIGNAL_PROMOTION_DRY_RUN_EXECUTION_REPORT_CN.md
docs/tw_portfolio_decision_model/POLICY_CLPR1_CANONICAL_SIGNAL_PROMOTION_DRY_RUN_REVIEW_CN.md
docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md
docs/tw_modular_contracts/MODEL_SIGNAL_CONTRACT_CN.md
docs/tw_modular_contracts/NEW_MODEL_AND_STRATEGY_DEVELOPER_GUIDE_CN.md
docs/tw_modular_contracts/MODEL_SIGNAL_EXTENSION_SCHEMA_CN.md
docs/tw_modular_contracts/NEW_MODEL_REVIEWER_CHECKLIST_CN.md
```

Skills applied:

```text
coordinator-executor-reviewer-workflow
tw-stock-new-model-onboarding
```

## 4. Changes Made

Copied canonical files:

```text
data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/pbpr3x_modela_20260708_contained/manifest.json
data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/pbpr3x_modela_20260708_contained/signals.csv
data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/pbpr3x_modela_20260708_contained/schema.json
data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/pbpr3x_modela_20260708_contained/coverage_audit.csv
data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/pbpr3x_modela_20260708_contained/forbidden_field_audit.csv
data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/pbpr3x_modela_20260708_contained/validator_report.json
```

Wrote controlled latest pointer:

```text
data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/latest.json
```

Added CLPR2 helper and next work document:

```text
scripts/build_tw_clpr2_controlled_signal_latest_publish.py
docs/tw_portfolio_decision_model/POLICY_CLPR3_READONLY_SNAPSHOT_CANDIDATE_OR_BLOCKER_WORK_CN.md
```

## 5. Evidence Produced

Evidence root:

```text
data_tw/experiments/controlled_latest_publish_route/clpr2_controlled_signal_latest_publish
```

Required evidence:

```text
pre_publish_state.json
copy_result.json
latest_pointer_write_result.json
post_publish_validation.json
rollback_evidence.json
legacy_pointer_unchanged_audit.json
forbidden_action_audit.json
artifact_manifest.json
```

Artifact manifest:

```text
status=pass
entries=17
missing=[]
checksum_mismatches=[]
```

## 6. Key Validation

```text
copy_result.status=pass
latest_pointer_write_result.status=pass
post_publish_validation.status=pass
legacy_pointer_unchanged_audit.status=pass
forbidden_action_audit.status=pass

all_six_canonical_files_match=True
latest_payload_matches_clpr1_plan=True
manifest.status=READY
validator.status=PASS
signals.rows=150
signals.date_values=['2026-07-08']
signals.signal_asof_values=['2026-07-08']
signals.duplicate_key_count=0
signals.forbidden_columns=[]
```

## 7. Forbidden Actions Audit

```text
all_forbidden_false=True
canonical_artifact_copied=true
controlled_signal_latest_written=true
readonly_snapshot_latest_written=false
agent_daily_prompt_latest_written=false
legacy_option_c_latest_signal_written=false
provider_or_qlib_accepted_latest_switched=false
model_scoring_triggered=false
strategy_replay_triggered=false
openai_call_triggered=false
monitor_broker_order_triggered=false
target_output_generated=false
```

## 8. Files Changed

```text
scripts/build_tw_clpr2_controlled_signal_latest_publish.py
docs/tw_portfolio_decision_model/POLICY_CLPR2_CONTROLLED_SIGNAL_LATEST_PUBLISH_EXECUTION_REPORT_CN.md
docs/tw_portfolio_decision_model/POLICY_CLPR3_READONLY_SNAPSHOT_CANDIDATE_OR_BLOCKER_WORK_CN.md
data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/pbpr3x_modela_20260708_contained/manifest.json
data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/pbpr3x_modela_20260708_contained/signals.csv
data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/pbpr3x_modela_20260708_contained/schema.json
data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/pbpr3x_modela_20260708_contained/coverage_audit.csv
data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/pbpr3x_modela_20260708_contained/forbidden_field_audit.csv
data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/pbpr3x_modela_20260708_contained/validator_report.json
data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/latest.json
data_tw/experiments/controlled_latest_publish_route/clpr2_controlled_signal_latest_publish/pre_publish_state.json
data_tw/experiments/controlled_latest_publish_route/clpr2_controlled_signal_latest_publish/copy_result.json
data_tw/experiments/controlled_latest_publish_route/clpr2_controlled_signal_latest_publish/latest_pointer_write_result.json
data_tw/experiments/controlled_latest_publish_route/clpr2_controlled_signal_latest_publish/post_publish_validation.json
data_tw/experiments/controlled_latest_publish_route/clpr2_controlled_signal_latest_publish/rollback_evidence.json
data_tw/experiments/controlled_latest_publish_route/clpr2_controlled_signal_latest_publish/legacy_pointer_unchanged_audit.json
data_tw/experiments/controlled_latest_publish_route/clpr2_controlled_signal_latest_publish/forbidden_action_audit.json
data_tw/experiments/controlled_latest_publish_route/clpr2_controlled_signal_latest_publish/artifact_manifest.json
```

## 9. Recommendation For Reviewer

建议 reviewer 审查 CLPR2。若通过，可进入
`CLPR3_READONLY_SNAPSHOT_CANDIDATE_OR_BLOCKER`。CLPR3 只能判断 readonly snapshot
候选或 blocker，不得触发 strategy replay、OrderIntent、Agent prompt、provider/qlib
accepted latest、frontend/default、monitor/broker/order 或 target 输出。
