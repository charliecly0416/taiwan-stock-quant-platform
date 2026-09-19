---
created_at: 2026-07-10
status: work_document
route: RSPPR_READONLY_SNAPSHOT_BUILDER_PUBLISH_ROUTE
phase: RSPPR0_CONTRACT_EXTENSION_AND_PUBLISH_PLAN
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

# RSPPR0 Contract Extension And Publish Plan Work

## 1. Objective

RSPPR0 只做 candidate-only readonly snapshot 的合同扩展、source inventory、publish plan、rollback plan 和 validator plan。RSPPR0 不写 snapshot artifact，也不写 latest pointer。

## 2. Required Inputs

必须读取：

```text
docs/tw_portfolio_decision_model/POLICY_RSPPR_READONLY_SNAPSHOT_BUILDER_PUBLISH_ROUTE_MAINLINE_CN.md
docs/tw_portfolio_decision_model/POLICY_CLPR4_FINAL_SAFETY_AND_INTEGRATION_ACCEPTANCE_REVIEW_CN.md
docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md
docs/tw_modular_contracts/MODEL_SIGNAL_CONTRACT_CN.md
docs/tw_modular_contracts/READONLY_STRATEGY_SNAPSHOT_CONTRACT_CN.md
data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/latest.json
data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/pbpr3x_modela_20260708_contained/manifest.json
data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/pbpr3x_modela_20260708_contained/signals.csv
```

## 3. Allowed Writes

```text
scripts/build_tw_rsppr0_contract_extension_and_publish_plan.py
data_tw/experiments/readonly_snapshot_builder_publish_route/rsppr0_contract_extension_and_publish_plan/*.json
docs/tw_portfolio_decision_model/POLICY_RSPPR0_CONTRACT_EXTENSION_AND_PUBLISH_PLAN_EXECUTION_REPORT_CN.md
docs/tw_portfolio_decision_model/POLICY_RSPPR1_CANDIDATE_ONLY_SNAPSHOT_DRY_RUN_WORK_CN.md
```

## 4. Required Evidence

必须生成：

```text
source_inventory.json
candidate_only_contract_extension.json
publish_plan.json
validator_plan.json
rollback_plan.json
forbidden_action_audit.json
artifact_manifest.json
```

## 5. Required Checks

```text
CLPR final review PASS
controlled signal latest exists and asof=2026-07-08
canonical manifest/signals checksum match latest pointer
signals.csv rows=150
date/signal_asof only 2026-07-08
duplicate keys=0
forbidden_columns=[]
existing readonly snapshot latest fingerprinted only
target snapshot dir data_tw/artifacts/publish/readonly_strategy_snapshot/2026-07-08 does not exist or collision is explicit
candidate-only contract marks exit/hold as not built
existing LTR-primary validator mismatch is documented and not ignored
```

## 6. Forbidden Actions

RSPPR0 禁止：

```text
creating data_tw/artifacts/publish/readonly_strategy_snapshot/2026-07-08/
writing data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json
building or publishing Agent prompt
modifying controlled signal latest
modifying legacy option_c latest_signal
provider/network/model/strategy/replay/order/default actions
```

## 7. Pass Gate

RSPPR0 PASS 条件：

```text
source_inventory.status=pass
candidate_only_contract_extension.status=pass
publish_plan.status=pass
validator_plan.status=pass
rollback_plan.status=pass
forbidden_action_audit.all_false=true
artifact_manifest.status=pass
RSPPR1 work doc remains dry-run only
```
