---
created_at: 2026-07-10
status: work_document
route: CLPR_CONTROLLED_LATEST_PUBLISH_ROUTE
phase: CLPR1_CANONICAL_SIGNAL_PROMOTION_DRY_RUN
target_asof: 2026-07-08
provider_pull_allowed: false
network_command_allowed: false
provider_publish_allowed: false
provider_accepted_latest_switch_allowed: false
qlib_accepted_latest_switch_allowed: false
legacy_option_c_latest_signal_switch_allowed: false
canonical_artifact_write_allowed: false
latest_pointer_write_allowed: false
readonly_snapshot_publish_allowed: false
agent_prompt_build_allowed: false
agent_prompt_publish_allowed: false
model_scoring_allowed: false
strategy_replay_allowed: false
openai_call_allowed: false
monitor_write_allowed: false
order_or_target_output_allowed: false
production_default_switch_allowed: false
dry_run_only: true
---

# CLPR1 Canonical Signal Promotion Dry-run Work

## 1. Objective

CLPR1 只做 canonical signal promotion dry-run。目标是把 PBPR3_X verified `ModelSignalArtifact` 到 canonical target 的复制与 latest pointer payload 做成可审查计划，但不执行复制、不写 latest pointer。

Source:

```text
data_tw/experiments/provider_bridge_productionization/pbpr3_target_asof_model_a_no_publish_dry_run/rerun_after_pbpr3w/planned_future_outputs/model_signal_artifact/e4_frozen_qlib_2018_2022/pbpr3x_modela_20260708_contained/
```

Planned canonical target:

```text
data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/pbpr3x_modela_20260708_contained/
```

Planned controlled signal latest pointer:

```text
data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/latest.json
```

## 2. Required Inputs

Executor 必须读取：

```text
docs/tw_portfolio_decision_model/POLICY_CLPR_CONTROLLED_LATEST_PUBLISH_ROUTE_MAINLINE_CN.md
docs/tw_portfolio_decision_model/POLICY_CLPR0_CONTRACT_INVENTORY_AND_PROMOTION_PLAN_EXECUTION_REPORT_CN.md
docs/tw_portfolio_decision_model/POLICY_CLPR0_CONTRACT_INVENTORY_AND_PROMOTION_PLAN_WORK_CN.md
docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md
docs/tw_modular_contracts/MODEL_SIGNAL_CONTRACT_CN.md
data_tw/experiments/controlled_latest_publish_route/clpr0_contract_inventory_and_promotion_plan/source_inventory.json
data_tw/experiments/controlled_latest_publish_route/clpr0_contract_inventory_and_promotion_plan/promotion_plan.json
data_tw/experiments/controlled_latest_publish_route/clpr0_contract_inventory_and_promotion_plan/rollback_plan.json
data_tw/experiments/controlled_latest_publish_route/clpr0_contract_inventory_and_promotion_plan/forbidden_action_audit.json
data_tw/experiments/controlled_latest_publish_route/clpr0_contract_inventory_and_promotion_plan/artifact_manifest.json
```

## 3. Allowed Writes

CLPR1 只允许写 dry-run evidence 和执行报告：

```text
scripts/build_tw_clpr1_canonical_signal_promotion_dry_run.py
data_tw/experiments/controlled_latest_publish_route/clpr1_canonical_signal_promotion_dry_run/source_to_target_file_map.json
data_tw/experiments/controlled_latest_publish_route/clpr1_canonical_signal_promotion_dry_run/target_collision_audit.json
data_tw/experiments/controlled_latest_publish_route/clpr1_canonical_signal_promotion_dry_run/dry_run_copy_plan.json
data_tw/experiments/controlled_latest_publish_route/clpr1_canonical_signal_promotion_dry_run/latest_pointer_payload_plan.json
data_tw/experiments/controlled_latest_publish_route/clpr1_canonical_signal_promotion_dry_run/validator_plan.json
data_tw/experiments/controlled_latest_publish_route/clpr1_canonical_signal_promotion_dry_run/rollback_preflight.json
data_tw/experiments/controlled_latest_publish_route/clpr1_canonical_signal_promotion_dry_run/forbidden_action_audit.json
data_tw/experiments/controlled_latest_publish_route/clpr1_canonical_signal_promotion_dry_run/artifact_manifest.json
docs/tw_portfolio_decision_model/POLICY_CLPR1_CANONICAL_SIGNAL_PROMOTION_DRY_RUN_EXECUTION_REPORT_CN.md
docs/tw_portfolio_decision_model/POLICY_CLPR2_CONTROLLED_SIGNAL_LATEST_PUBLISH_WORK_CN.md
```

## 4. Required Checks

CLPR1 helper / executor 必须证明：

```text
CLPR0 source_inventory.status=pass
CLPR0 promotion_plan.status=pass
CLPR0 rollback_plan.status=pass
CLPR0 forbidden_action_audit.all_false=true
CLPR0 artifact_manifest.status=pass
PBPR3_X source files exist and match CLPR0 recorded checksums
source_to_target_file_map covers manifest.json, signals.csv, schema.json, coverage_audit.csv, forbidden_field_audit.csv, validator_report.json
target canonical directory collision state is explicit
controlled signal latest pointer pre-existing state is explicit
latest pointer payload is planned but not written
planned payload points only to canonical ModelSignalArtifact manifest/signals for target_asof=2026-07-08
legacy option_c latest_signal pointers are out of scope
rollback_preflight can restore or remove pointer according to CLPR0 rollback plan
forbidden_action_audit.all_false=true
artifact_manifest checksum status=pass
```

## 5. Forbidden Actions

CLPR1 禁止：

```text
copying PBPR3_X files into canonical artifact directory
creating data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/pbpr3x_modela_20260708_contained/
writing data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/latest.json
writing readonly_strategy_snapshot latest
writing agent_daily_prompt latest
writing qlib_pipeline/data_tw/experiments/option_c_daily_signal/latest_signal.json
writing data_tw/experiments/option_c_daily_signal/latest_signal.json
provider/network pull
provider publish
accepted/latest switch
model scoring
strategy replay
Agent prompt build/publish
OpenAI call
frontend/API/default switch
monitor/broker/order/target output
```

## 6. Pass Gate

CLPR1 PASS 条件：

```text
dry-run evidence is complete
source checksums match CLPR0/PBPR3_X
target collision audit is explicit and non-overwriting
latest pointer payload plan is unambiguous
rollback preflight is explicit
forbidden_action_audit.all_false=true
artifact_manifest.status=pass
no canonical artifact copy occurred
no latest pointer write occurred
```

## 7. Reviewer Brief

Reviewer 必须独立复核：

```text
CLPR1 execution report
CLPR1 source_to_target_file_map
CLPR1 target_collision_audit
CLPR1 dry_run_copy_plan
CLPR1 latest_pointer_payload_plan
CLPR1 validator_plan
CLPR1 rollback_preflight
CLPR1 forbidden_action_audit
CLPR1 artifact_manifest checksums
CLPR0 source inventory and rollback plan
PBPR3_X source checksums
```

若发现 CLPR1 写入 canonical artifact 或任何 latest pointer，必须 FAIL。

若通过，reviewer 可以建议进入 CLPR2，但 CLPR2 必须另有明确 work document，且只允许写 canonical signal artifact 与 controlled signal latest pointer，不得扩大到 readonly snapshot、Agent prompt、provider/qlib accepted latest、legacy option_c latest_signal、frontend/default、monitor/broker/order/target。
