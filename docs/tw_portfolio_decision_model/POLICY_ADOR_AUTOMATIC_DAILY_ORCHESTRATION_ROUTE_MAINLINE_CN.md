---
created_at: 2026-07-10
status: mainline
route: ADOR_AUTOMATIC_DAILY_ORCHESTRATION_ROUTE
coordinator: Codex
prerequisite_routes: RSPPR_READONLY_SNAPSHOT_BUILDER_PUBLISH_ROUTE, APLR_AGENT_PROMPT_LATEST_ROUTE
prerequisite_verdicts: PASS_CLOSE_RSPPR_AND_OPEN_SEPARATE_AGENT_PROMPT_LATEST_ROUTE, PASS_CLOSE_APLR_AGENT_PROMPT_LATEST_ROUTE
target_reference_asof: 2026-07-08
provider_pull_allowed: false
network_command_allowed: false
provider_publish_allowed: false
provider_accepted_latest_switch_allowed: false
qlib_accepted_latest_switch_allowed: false
legacy_option_c_latest_signal_switch_allowed: false
model_scoring_allowed_by_default: false
strategy_replay_allowed: false
order_intent_allowed: false
replay_result_allowed: false
readonly_snapshot_publish_gate_allowed: true
agent_prompt_publish_gate_allowed: true
agent_prompt_publish_gate_default_enabled: false
openai_call_allowed: false
monitor_write_allowed: false
order_or_trade_target_output_allowed: false
production_default_switch_allowed: false
daily_automation_default_switch_allowed: false
---

# ADOR Automatic Daily Orchestration Route Mainline

## 1. Goal

ADOR 的目标是把已通过 RSPPR/APLR 手工路线验证的链路，设计成日更脚本里的
**显式、非默认、可审计自动编排 gate**：

```text
daily controlled ModelSignalArtifact latest/source
  -> candidate-only ReadonlyStrategySnapshot latest
  -> candidate-only DailyAgentPromptArtifact latest
```

该路线回答的是：日更数据更新后，是否可以自动更新 readonly snapshot 和 Agent
prompt latest，而不是每次使用前临时构建。

核心原则：

```text
default disabled
explicit env/CLI gate required
dry-run default true
no provider publish or accepted latest switching
no OpenAI
artifact-backed only
validator-gated before latest pointer write
```

## 2. Non-goals

ADOR 不做：

```text
provider/network pull
provider publish
provider or qlib accepted latest switch
legacy option_c latest_signal switch
model scoring/training by default
strategy replay
OrderIntentArtifact generation
ReplayResult/NAV generation
OpenAI call
frontend/API/default switch
daily automation default enablement
monitor config/scan/alerts
broker, quick-trade, real order
target_position, target_weight, quantity, shares, lots output
```

ADOR 也不改变 cron schedule。若后续要在 cron 中开启 gate，必须另有运维确认。

## 3. Current Baseline

RSPPR final closure 已确认：

```text
readonly_strategy_snapshot/latest.json -> 2026-07-08 candidate-only snapshot
candidate_only=true
top_candidates_count=50
exit_candidates=[]
hold_candidates=[]
```

APLR final closure 已确认：

```text
agent_daily_prompt/latest.json -> data_tw/artifacts/agent_daily_prompt/2026-07-08/manifest.json
checksum=sha256:b65c3478e53c25194a0ebd7da5a50d6c23ce72c42edcda55e4ac2208e962bddc
validator ok=true
backend loader local load pass
no OpenAI
daily automation/default/frontend/backend/config not modified
```

Existing daily orchestrator has a non-default readonly snapshot publish gate:

```text
ENABLE_TW_READONLY_STRATEGY_SNAPSHOT_PUBLISH=false by default
TW_READONLY_STRATEGY_SNAPSHOT_DRY_RUN=true by default
run_readonly_strategy_snapshot_publish(...)
```

It does not yet have an equivalent productionized Agent prompt latest publish gate.

## 4. Required Documents And Contracts

Every phase must read:

```text
docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md
docs/tw_modular_contracts/TW_DAILY_AUTO_UPDATE_RUNBOOK_CN.md
docs/tw_modular_contracts/TW_AGENT_DAILY_PROMPT_ARTIFACT_CONTRACT_CN.md
docs/tw_portfolio_decision_model/POLICY_RSPPR_FINAL_CLOSURE_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_APLR_FINAL_CLOSURE_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_ADOR_AUTOMATIC_DAILY_ORCHESTRATION_ROUTE_MAINLINE_CN.md
scripts/run_daily_tw_stock_auto_update.py
```

## 5. Architecture Boundary

ADOR can write:

```text
scripts/build_tw_ador*.py
scripts/run_daily_tw_stock_auto_update.py only in explicitly approved implementation phases
backend/tests/test_tw_stock_agent_daily_prompt_validator.py only for validator regression when needed
tests/unit/test_tw_daily_readonly_snapshot_integration.py or targeted orchestrator tests when needed
data_tw/experiments/automatic_daily_orchestration_route/
docs/tw_portfolio_decision_model/POLICY_ADOR*.md
```

ADOR cannot write:

```text
data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/latest.json
data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json except in explicit gated dry-run/publish validation phases
data_tw/artifacts/agent_daily_prompt/latest.json except in explicit gated dry-run/publish validation phases
qlib_pipeline/data_tw/experiments/option_c_daily_signal/latest_signal.json
data_tw/experiments/option_c_daily_signal/latest_signal.json
frontend/
backend/
configs/
cron files
```

## 6. Phase Plan

### ADOR0: Contract Inventory And Automation Readiness

Inventory existing daily orchestrator gates, current RSPPR/APLR builder scripts,
validator contracts, latest concepts, default env flags, and safe integration points.
No orchestrator code change.

### ADOR1: No-publish Orchestration Dry-run Design

Design a no-publish dry-run evidence path that proves the daily orchestrator can
detect source readiness and plan readonly snapshot + Agent prompt updates without
writing latest pointers.

### ADOR2: Explicit Non-default Gate Implementation

If ADOR1 reviewer PASS, implement explicit env/CLI gate(s) in daily orchestrator.
Default remains disabled and dry-run. No cron/default switch.

### ADOR3: Orchestrator Dry-run Acceptance

Run targeted dry-run/static tests proving the gate is default-disabled, no-OpenAI,
no-provider-publish, no-accepted-latest, and artifact-backed.

### ADOR4: Final Closure / Ops Recommendation

Close ADOR and state whether a separate operations decision may enable the gate
in cron. ADOR itself must not enable cron/default.

## 7. Required Gate Semantics

New Agent prompt daily gate, if implemented, must be explicit:

```text
ENABLE_TW_AGENT_DAILY_PROMPT_PUBLISH=false by default
TW_AGENT_DAILY_PROMPT_DRY_RUN=true by default
TW_AGENT_DAILY_PROMPT_PUBLISH_LATEST=false by default unless explicit gate says publish
```

The gate must:

```text
validate source readonly snapshot latest for asof
validate candidate-only Agent prompt artifact before latest pointer write
record before/after fingerprints
write job evidence into daily job dir
report warning without blocking provider archive unless explicit strict mode is added later
never call OpenAI
never switch provider/qlib accepted latest
```

## 8. Forbidden Actions

All phases forbid:

```text
provider/network pull
provider publish
provider or qlib accepted latest switch
legacy option_c latest_signal switch
model scoring/training unless explicitly inside existing non-default model signal gate and not part of ADOR
strategy replay
OrderIntentArtifact generation
ReplayResult/NAV generation
OpenAI call
frontend/API/default switch
daily automation default enablement
monitor write/scan/alerts
broker, quick-trade, real order
target_position, target_weight, quantity, shares, lots output
```

## 9. Stop Conditions

Stop if:

```text
RSPPR/APLR closure evidence missing or not PASS
daily orchestrator cannot distinguish provider accepted latest, readonly snapshot latest, and Agent prompt latest
Agent prompt publish would require OpenAI or dynamic service payloads
builder/validator cannot run from artifact-backed sources
implementation would enable daily automation defaults or cron without explicit user decision
any provider/qlib accepted latest, legacy option_c latest, default switch, order, target, monitor, or OpenAI action is required
```

## 10. Evidence Requirements

Each phase must produce:

```text
artifact_manifest.json
forbidden_action_audit.json
default_gate_audit.json
latest_concept_separation evidence
validator or blocker evidence
execution report
review report
next work document
```
