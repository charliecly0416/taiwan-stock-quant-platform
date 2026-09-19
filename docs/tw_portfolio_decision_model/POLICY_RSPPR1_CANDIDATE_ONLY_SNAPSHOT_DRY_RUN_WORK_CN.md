---
created_at: 2026-07-10T07:02:46+00:00
status: work_document
route: RSPPR_READONLY_SNAPSHOT_BUILDER_PUBLISH_ROUTE
phase: RSPPR1_CANDIDATE_ONLY_SNAPSHOT_DRY_RUN
target_asof: 2026-07-08
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

# RSPPR1 Candidate-only Snapshot Dry-run Work

## 1. Objective

RSPPR1 只从 CLPR controlled `ModelSignalArtifact` latest 生成 candidate-only `ReadonlyStrategySnapshot` 的 payload dry-run、checksum plan、latest pointer payload plan、validator evidence plan 和 rollback preflight。RSPPR1 不创建 snapshot artifact 目录，不写 `readonly_strategy_snapshot/latest.json`。

## 2. Required Inputs

必须读取：

```text
docs/tw_portfolio_decision_model/POLICY_RSPPR_READONLY_SNAPSHOT_BUILDER_PUBLISH_ROUTE_MAINLINE_CN.md
docs/tw_portfolio_decision_model/POLICY_RSPPR0_CONTRACT_EXTENSION_AND_PUBLISH_PLAN_WORK_CN.md
docs/tw_portfolio_decision_model/POLICY_RSPPR0_CONTRACT_EXTENSION_AND_PUBLISH_PLAN_EXECUTION_REPORT_CN.md
docs/tw_portfolio_decision_model/POLICY_RSPPR0_CONTRACT_EXTENSION_AND_PUBLISH_PLAN_REVIEW_CN.md
docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md
docs/tw_modular_contracts/MODEL_SIGNAL_CONTRACT_CN.md
docs/tw_modular_contracts/READONLY_STRATEGY_SNAPSHOT_CONTRACT_CN.md
data_tw/experiments/readonly_snapshot_builder_publish_route/rsppr0_contract_extension_and_publish_plan/source_inventory.json
data_tw/experiments/readonly_snapshot_builder_publish_route/rsppr0_contract_extension_and_publish_plan/candidate_only_contract_extension.json
data_tw/experiments/readonly_snapshot_builder_publish_route/rsppr0_contract_extension_and_publish_plan/publish_plan.json
data_tw/experiments/readonly_snapshot_builder_publish_route/rsppr0_contract_extension_and_publish_plan/validator_plan.json
data_tw/experiments/readonly_snapshot_builder_publish_route/rsppr0_contract_extension_and_publish_plan/rollback_plan.json
data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/latest.json
data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/pbpr3x_modela_20260708_contained/manifest.json
data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/pbpr3x_modela_20260708_contained/signals.csv
```

## 3. Allowed Writes

```text
scripts/build_tw_rsppr1_candidate_only_snapshot_dry_run.py
data_tw/experiments/readonly_snapshot_builder_publish_route/rsppr1_candidate_only_snapshot_dry_run/*.json
docs/tw_portfolio_decision_model/POLICY_RSPPR1_CANDIDATE_ONLY_SNAPSHOT_DRY_RUN_EXECUTION_REPORT_CN.md
docs/tw_portfolio_decision_model/POLICY_RSPPR2_CANDIDATE_ONLY_SNAPSHOT_PUBLISH_WORK_CN.md
```

## 4. Required Evidence

必须生成：

```text
source_preflight.json
candidate_snapshot_payload_plan.json
latest_pointer_payload_plan.json
validator_dry_run.json
checksum_plan.json
rollback_preflight.json
forbidden_action_audit.json
artifact_manifest.json
```

## 5. Required Checks

```text
RSPPR0 reviewer PASS
controlled signal latest asof=2026-07-08
canonical manifest/signals checksum match latest pointer
signals.csv rows=150
date/signal_asof only 2026-07-08
duplicate keys=0
forbidden_columns=[]
top_candidates derived from candidate_rank<=50
top_candidates count=50
exit_candidates=[]
hold_candidates=[]
exit_hold_context_status=not_built_no_strategy_replay
candidate-only payload cannot be mistaken for full strategy replay snapshot
existing readonly snapshot latest fingerprint unchanged
target snapshot dir collision explicit and not written
existing LTR-primary validator mismatch remains documented
```

## 6. Forbidden Actions

RSPPR1 禁止：

```text
creating data_tw/artifacts/publish/readonly_strategy_snapshot/2026-07-08/
writing data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json
building or publishing Agent prompt
modifying controlled signal latest
modifying legacy option_c latest_signal
provider/network pull
model scoring
strategy replay
OrderIntentArtifact generation
ReplayResult/NAV generation
OpenAI call
frontend/API/default switch
monitor/broker/order
target_position/target_weight/quantity/shares/lots output
```

## 7. Pass Gate

RSPPR1 PASS 条件：

```text
source_preflight.status=pass
candidate_snapshot_payload_plan.status=pass
latest_pointer_payload_plan.status=pass
validator_dry_run.status=pass
checksum_plan.status=pass
rollback_preflight.status=pass
forbidden_action_audit.all_false=true
artifact_manifest.status=pass
RSPPR2 work doc limits writes to candidate-only readonly snapshot artifact and latest pointer only
```
