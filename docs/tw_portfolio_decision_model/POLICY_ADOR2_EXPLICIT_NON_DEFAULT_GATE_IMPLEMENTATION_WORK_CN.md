---
created_at: 2026-07-10T09:47:54+00:00
status: work_document
route: ADOR_AUTOMATIC_DAILY_ORCHESTRATION_ROUTE
phase: ADOR2_EXPLICIT_NON_DEFAULT_GATE_IMPLEMENTATION
target_reference_asof: 2026-07-08
implementation_allowed: true
orchestrator_code_write_allowed: true
default_enabled_allowed: false
dry_run_default_required: true
readonly_snapshot_latest_write_default_allowed: false
agent_prompt_latest_write_default_allowed: false
provider_pull_allowed: false
provider_publish_allowed: false
accepted_latest_switch_allowed: false
model_scoring_allowed: false
strategy_replay_allowed: false
openai_call_allowed: false
daily_automation_default_switch_allowed: false
cron_switch_allowed: false
---

# ADOR2 Explicit Non-Default Gate Implementation Work

## 1. Scope

ADOR2 may implement a daily orchestrator gate only after ADOR1 reviewer PASS. The gate must be explicit, non-default, and dry-run by default.

Allowed implementation surface:

```text
scripts/run_daily_tw_stock_auto_update.py
targeted tests for default-disabled and dry-run behavior
daily job-dir evidence writers
```

## 2. Required Defaults

```text
ENABLE_TW_ADOR_NO_PUBLISH_ORCHESTRATION_DRY_RUN=false
TW_AGENT_DAILY_PROMPT_DRY_RUN=true
ENABLE_TW_AGENT_DAILY_PROMPT_PUBLISH=false
TW_AGENT_DAILY_PROMPT_PUBLISH_LATEST=false
```

Equivalent CLI flags may be added, but they must default to disabled. Cron, backend, frontend, config defaults, and daily automation defaults must not be changed.

## 3. Required Behavior

- Read daily job source readiness from job-dir JSON evidence.
- Build or record readonly snapshot and Agent prompt no-write plans only when the explicit gate is enabled.
- Attach evidence under the daily job dir and summarize it in `job.json`.
- Keep latest pointer writes disabled by default.
- Validate any staged local artifact before any future pointer write path.
- Record protected path fingerprints before and after the gate.
- Fail closed into warning/evidence, not provider publish or accepted latest switching.

## 4. Forbidden Behavior

ADOR2 must not perform provider/network pull, provider publish, accepted latest switching, legacy Option C latest switching, model scoring/training, strategy replay, OpenAI calls, frontend/backend/config/default changes, monitor/broker/order paths, or trade sizing/allocation output.

## 5. Acceptance Evidence

ADOR2 implementation must produce:

```text
default-disabled test
dry-run true test
no latest pointer write test
protected path fingerprint before/after test
job evidence attachment test
forbidden action audit test
py_compile
```

If any default would become enabled or any latest pointer would be written by default, stop and repair before review.
