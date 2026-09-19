---
created_at: 2026-07-10T00:00:00+00:00
status: work_document
route: APLR_AGENT_PROMPT_LATEST_ROUTE
phase: APLR1_CANDIDATE_ONLY_AGENT_PROMPT_DRY_RUN
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
order_or_trade_sizing_output_allowed: false
production_default_switch_allowed: false
---

# APLR1 Candidate-only Agent Prompt Dry-run Work

## 1. Objective

APLR1 只基于 APLR0 PASS evidence 与 RSPPR candidate-only readonly snapshot
latest 构建 Agent prompt dry-run evidence。APLR1 不写生产 Agent prompt artifact
目录，不写 Agent prompt latest pointer。

## 2. Required Inputs

必须读取：

```text
docs/tw_portfolio_decision_model/POLICY_APLR_AGENT_PROMPT_LATEST_ROUTE_MAINLINE_CN.md
docs/tw_portfolio_decision_model/POLICY_APLR0_CONTRACT_ADAPTATION_AND_SOURCE_READINESS_EXECUTION_REPORT_CN.md
data_tw/experiments/agent_prompt_latest_route/aplr0_contract_adaptation_and_source_readiness/*.json
docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md
docs/tw_modular_contracts/TW_AGENT_DAILY_PROMPT_ARTIFACT_CONTRACT_CN.md
docs/tw_modular_contracts/TW_AGENT_DAILY_PROMPT_OPENAI_REBUILD_DESIGN_CN.md
scripts/build_tw_agent_daily_prompt_artifact.py
scripts/validate_tw_agent_daily_prompt_artifact.py
data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json
data_tw/artifacts/publish/readonly_strategy_snapshot/2026-07-08/manifest.json
data_tw/artifacts/publish/readonly_strategy_snapshot/2026-07-08/strategy_snapshot.json
data_tw/artifacts/publish/readonly_strategy_snapshot/2026-07-08/validation_report.json
data_tw/artifacts/publish/readonly_strategy_snapshot/2026-07-08/checksum_manifest.json
```

## 3. Allowed Writes

APLR1 只能写 dry-run evidence：

```text
scripts/build_tw_aplr1_candidate_only_agent_prompt_dry_run.py
data_tw/experiments/agent_prompt_latest_route/aplr1_candidate_only_agent_prompt_dry_run/*.json
data_tw/experiments/agent_prompt_latest_route/aplr1_candidate_only_agent_prompt_dry_run/*.md
docs/tw_portfolio_decision_model/POLICY_APLR1_CANDIDATE_ONLY_AGENT_PROMPT_DRY_RUN_EXECUTION_REPORT_CN.md
```

## 4. Forbidden Writes

APLR1 禁止写：

```text
data_tw/artifacts/agent_daily_prompt/2026-07-08/
data_tw/artifacts/agent_daily_prompt/latest.json
data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json
data_tw/artifacts/publish/readonly_strategy_snapshot/2026-07-08/
data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/latest.json
qlib_pipeline/data_tw/experiments/option_c_daily_signal/latest_signal.json
data_tw/experiments/option_c_daily_signal/latest_signal.json
frontend/
backend/
configs/
```

## 5. Required Dry-run Evidence

必须生成：

```text
source_gate_check.json
candidate_only_prompt_context_dry_run.json
candidate_only_prompt_text_dry_run.md
dry_run_manifest_plan.json
validator_adaptation_plan.json
checksum_plan.json
forbidden_action_audit.json
artifact_manifest.json
```

## 6. Required Checks

APLR1 必须证明：

```text
APLR0 evidence status=pass
readonly_strategy_snapshot/latest.json still points to 2026-07-08 manifest
candidate_only=true
top_candidates=50
exit_candidates=[]
hold_candidates=[]
exit_hold_context_status=not_built_no_strategy_replay
source lineage points to controlled ModelSignalArtifact latest
dry-run context uses candidate_only_no_strategy_replay, not full strategy replay
treatment model is null/not applicable for candidate-only context
prompt text preserves readonly/research-only boundaries
checksum is computed over dry-run context bytes plus dry-run prompt bytes
validator adaptation needs are explicit
Agent prompt latest remains absent or fingerprinted only
```

## 7. Hard Boundary

APLR1 禁止 provider/network pull、provider publish、accepted latest switch、
legacy option_c switch、model scoring/training、strategy replay、OrderIntent、
ReplayResult/NAV、OpenAI call、frontend/API/default switch、monitor/broker/order/
quick-trade，以及交易执行或交易规模输出。

## 8. Pass Gate

APLR1 PASS 条件：

```text
source_gate_check.status=pass
candidate_only_prompt_context_dry_run.status=pass
dry_run_manifest_plan.status=pass
validator_adaptation_plan.status=pass
checksum_plan.status=pass
forbidden_action_audit.all_false=true
artifact_manifest.status=pass
no production Agent prompt artifact/latest write
```

APLR1 reviewer PASS 后，才允许 coordinator 开启独立 APLR2 publish 工作文档。
