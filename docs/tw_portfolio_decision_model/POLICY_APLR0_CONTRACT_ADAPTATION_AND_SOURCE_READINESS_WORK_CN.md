---
created_at: 2026-07-10
status: work_document
route: APLR_AGENT_PROMPT_LATEST_ROUTE
phase: APLR0_CONTRACT_ADAPTATION_AND_SOURCE_READINESS
target_asof: 2026-07-08
agent_prompt_artifact_write_allowed: false
agent_prompt_latest_write_allowed: false
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

# APLR0 Contract Adaptation And Source Readiness Work

## 1. Objective

APLR0 只确认 candidate-only readonly snapshot 是否能安全映射为
DailyAgentPromptArtifact，并形成 source inventory、contract adaptation plan、
builder/validator compatibility plan、publish plan、rollback plan。APLR0 不创建
Agent prompt artifact 目录，不写 `data_tw/artifacts/agent_daily_prompt/latest.json`。

## 2. Required Inputs

必须读取：

```text
docs/tw_portfolio_decision_model/POLICY_APLR_AGENT_PROMPT_LATEST_ROUTE_MAINLINE_CN.md
docs/tw_portfolio_decision_model/POLICY_RSPPR_FINAL_CLOSURE_REVIEW_CN.md
docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md
docs/tw_modular_contracts/TW_AGENT_DAILY_PROMPT_ARTIFACT_CONTRACT_CN.md
docs/tw_modular_contracts/TW_AGENT_DAILY_PROMPT_OPENAI_REBUILD_DESIGN_CN.md
docs/tw_agent_daily_prompt_rebuild/PHASE0_TO_PHASE6_FINAL_SUMMARY_CN.md
scripts/build_tw_agent_daily_prompt_artifact.py
scripts/validate_tw_agent_daily_prompt_artifact.py
data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json
data_tw/artifacts/publish/readonly_strategy_snapshot/2026-07-08/manifest.json
data_tw/artifacts/publish/readonly_strategy_snapshot/2026-07-08/strategy_snapshot.json
data_tw/artifacts/publish/readonly_strategy_snapshot/2026-07-08/validation_report.json
data_tw/artifacts/publish/readonly_strategy_snapshot/2026-07-08/checksum_manifest.json
```

## 3. Allowed Writes

```text
scripts/build_tw_aplr0_contract_adaptation_and_source_readiness.py
data_tw/experiments/agent_prompt_latest_route/aplr0_contract_adaptation_and_source_readiness/*.json
docs/tw_portfolio_decision_model/POLICY_APLR0_CONTRACT_ADAPTATION_AND_SOURCE_READINESS_EXECUTION_REPORT_CN.md
docs/tw_portfolio_decision_model/POLICY_APLR1_CANDIDATE_ONLY_AGENT_PROMPT_DRY_RUN_WORK_CN.md
```

## 4. Required Evidence

必须生成：

```text
rsppr_gate_check.json
source_inventory.json
candidate_only_prompt_contract_extension.json
builder_validator_compatibility.json
publish_plan.json
rollback_plan.json
forbidden_action_audit.json
artifact_manifest.json
```

## 5. Required Checks

```text
RSPPR final closure verdict PASS_CLOSE_RSPPR_AND_OPEN_SEPARATE_AGENT_PROMPT_LATEST_ROUTE
readonly_strategy_snapshot/latest.json points to 2026-07-08 manifest
snapshot candidate_only=true
top_candidates count=50
exit_candidates=[]
hold_candidates=[]
exit_hold_context_status=not_built_no_strategy_replay
source lineage points to controlled ModelSignalArtifact latest
existing Agent prompt latest absent or fingerprinted only
existing builder/validator LTR/full-strategy assumptions documented
candidate-only adaptation does not output target_position/target_weight/quantity/shares/lots
```

## 6. Forbidden Actions

APLR0 禁止：

```text
creating data_tw/artifacts/agent_daily_prompt/2026-07-08/
writing data_tw/artifacts/agent_daily_prompt/latest.json
modifying readonly_strategy_snapshot/latest.json
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

APLR0 PASS 条件：

```text
rsppr_gate_check.status=pass
source_inventory.status=pass
candidate_only_prompt_contract_extension.status=pass
builder_validator_compatibility.status=pass
publish_plan.status=pass
rollback_plan.status=pass
forbidden_action_audit.all_false=true
artifact_manifest.status=pass
APLR1 work doc limits writes to dry-run evidence only
```
