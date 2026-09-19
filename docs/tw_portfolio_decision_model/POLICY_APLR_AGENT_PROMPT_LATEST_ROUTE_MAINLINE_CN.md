---
created_at: 2026-07-10
status: mainline
route: APLR_AGENT_PROMPT_LATEST_ROUTE
coordinator: Codex
prerequisite_route: RSPPR_READONLY_SNAPSHOT_BUILDER_PUBLISH_ROUTE
prerequisite_verdict: PASS_CLOSE_RSPPR_AND_OPEN_SEPARATE_AGENT_PROMPT_LATEST_ROUTE
target_asof: 2026-07-08
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
readonly_snapshot_publish_allowed: false
agent_prompt_build_allowed: true
agent_prompt_latest_publish_allowed: true
openai_call_allowed: false
monitor_write_allowed: false
order_or_trade_target_output_allowed: false
production_default_switch_allowed: false
---

# APLR Agent Prompt Latest Route Mainline

## 1. Goal

APLR 的目标是在 RSPPR 已发布的 candidate-only `ReadonlyStrategySnapshot`
latest 基础上，生成并受控发布 `DailyAgentPromptArtifact` latest，让后端
simple-chat 能读取稳定、可验证、只读的每日上下文。

目标链路：

```text
CLPR controlled ModelSignalArtifact latest
  -> RSPPR candidate-only ReadonlyStrategySnapshot latest
  -> DailyAgentPromptArtifact artifact
  -> data_tw/artifacts/agent_daily_prompt/latest.json
```

APLR 只负责 artifact 构建、校验、latest pointer 和只读安全验收；不调用
OpenAI，不改前端，不改后端默认，不触发 provider/model/strategy/replay/order。

## 2. Non-goals

APLR 不做：

```text
provider/network pull
provider publish
provider or qlib accepted latest switch
legacy option_c latest_signal switch
model scoring or training
strategy replay
OrderIntentArtifact generation
ReplayResult/NAV generation
OpenAI call
frontend/API/default switch
monitor config/scan/alerts
broker, quick-trade, real order
target_position, target_weight, quantity, shares, lots output
```

## 3. Current Baseline

RSPPR final closure 已确认：

```text
readonly_strategy_snapshot/latest.json -> data_tw/artifacts/publish/readonly_strategy_snapshot/2026-07-08/manifest.json
snapshot asof=2026-07-08
candidate_only=true
top_candidates_count=50
exit_candidates=[]
hold_candidates=[]
exit_hold_context_status=not_built_no_strategy_replay
source controlled signal latest sha256=c58d3e4d88e729eda32b65a9b0a854b827947ba68aec4e8c7bdc76014a152752
data_tw/artifacts/agent_daily_prompt/latest.json absent
data_tw/artifacts/agent_daily_prompt/ directory absent
```

Existing Agent prompt builder/validator were originally written for the prior
full strategy/LTR-style source artifact chain. APLR must therefore prove
candidate-only compatibility explicitly before publishing Agent prompt latest.

## 4. Required Documents And Contracts

Every phase must read:

```text
docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md
docs/tw_modular_contracts/TW_AGENT_DAILY_PROMPT_ARTIFACT_CONTRACT_CN.md
docs/tw_modular_contracts/TW_AGENT_DAILY_PROMPT_OPENAI_REBUILD_DESIGN_CN.md
docs/tw_agent_daily_prompt_rebuild/PHASE0_TO_PHASE6_FINAL_SUMMARY_CN.md
docs/tw_portfolio_decision_model/POLICY_RSPPR_FINAL_CLOSURE_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_APLR_AGENT_PROMPT_LATEST_ROUTE_MAINLINE_CN.md
```

## 5. Architecture Boundary

APLR can write only:

```text
data_tw/artifacts/agent_daily_prompt/2026-07-08/
data_tw/artifacts/agent_daily_prompt/latest.json
data_tw/experiments/agent_prompt_latest_route/
scripts/build_tw_aplr*.py
docs/tw_portfolio_decision_model/POLICY_APLR*.md
```

APLR cannot write:

```text
data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json
data_tw/artifacts/publish/readonly_strategy_snapshot/2026-07-08/
data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/latest.json
qlib_pipeline/data_tw/experiments/option_c_daily_signal/latest_signal.json
data_tw/experiments/option_c_daily_signal/latest_signal.json
configs/
frontend/
backend/
```

## 6. Phase Plan

### APLR0: Contract Adaptation And Source Readiness

Confirm how a candidate-only readonly snapshot maps into DailyAgentPromptArtifact.
Inventory source artifacts, builder/validator compatibility, target paths,
publish plan, rollback plan, and validator adaptation needs. No Agent prompt
artifact/latest write.

### APLR1: Candidate-only Agent Prompt Dry-run

Build dry-run prompt payload plan from readonly snapshot latest. Verify context,
prompt text, checksum, safety terms, source citations, latest pointer payload
plan, and validator evidence. No artifact/latest write.

### APLR2: Agent Prompt Artifact Publish

If APLR1 reviewer PASS, write:

```text
data_tw/artifacts/agent_daily_prompt/2026-07-08/manifest.json
data_tw/artifacts/agent_daily_prompt/2026-07-08/prompt_context.json
data_tw/artifacts/agent_daily_prompt/2026-07-08/prompt_text.md
data_tw/artifacts/agent_daily_prompt/latest.json
```

Must backup previous latest pointer state, validate checksum, and prove rollback.

### APLR3: Agent Prompt Readonly Acceptance

Validate latest pointer, artifact checksum, validator result, backend loader
compatibility in readonly/no-OpenAI mode, citation/source availability, and safety
boundaries. No OpenAI call.

### APLR4: Final Closure

Close APLR if all phases PASS. State whether daily automation can later enable
Agent prompt build/publish under its own daily-update gate; do not change that
gate in APLR.

## 7. Candidate-only Agent Prompt Contract Extension

APLR artifact must keep the existing artifact type:

```text
artifact_type=tw_agent_daily_prompt
schema_version=tw_agent_daily_prompt_v1
readonly_only=true
not_order=true
not_target_position=true
not_investment_advice=true
production_trade_enabled=false
```

APLR-specific context must disclose:

```text
source_lineage=rsppr_candidate_only_readonly_snapshot_latest
snapshot_candidate_only=true
base_model_id=e4_frozen_qlib_2018_2022
treatment_model_id=null_or_not_applicable
ranking_source=qlib_rank_controlled_signal
candidate_boundary=qlib_top50
strategy_rule=candidate_only_no_strategy_replay
top_candidates derived from readonly snapshot latest
exit_candidates=[]
hold_candidates=[]
exit_hold_context_status=not_built_no_strategy_replay
```

Any validator adaptation must be explicit. It must not silently force the old
LTR/treatment strategy constants when the source artifact is candidate-only.

## 8. Forbidden Actions

All phases forbid:

```text
provider/network pull
provider publish
provider or qlib accepted latest switch
legacy option_c latest_signal switch
model scoring or training
strategy replay
OrderIntentArtifact generation
ReplayResult/NAV generation
OpenAI call
frontend/API/default switch
monitor write/scan/alerts
broker, quick-trade, real order
target_position, target_weight, quantity, shares, lots output
```

## 9. Stop Conditions

Stop if:

```text
RSPPR final closure is missing or not PASS
readonly snapshot latest missing or no longer points to 2026-07-08
candidate-only snapshot cannot be mapped without pretending it is a full replay snapshot
Agent prompt validator requires LTR/treatment/full-strategy semantics and cannot be adapted safely
prompt artifact would need dynamic service payloads instead of source artifacts
OpenAI call is required
any provider/qlib accepted latest, legacy option_c latest, default switch, order, target, or monitor action is required
```

## 10. Evidence Requirements

Each phase must produce:

```text
artifact_manifest.json
forbidden_action_audit.json
source/latest fingerprint evidence
validator or blocker evidence
execution report
review report
next work document
```
