---
created_at: 2026-07-10T08:30:31+00:00
status: work_document
route: APLR_AGENT_PROMPT_LATEST_ROUTE
phase: APLR3_AGENT_PROMPT_READONLY_ACCEPTANCE
target_asof: 2026-07-08
requires_aplr2_reviewer_pass: true
provider_pull_allowed: false
network_command_allowed: false
provider_publish_allowed: false
openai_call_allowed: false
production_default_switch_allowed: false
---

# APLR3 Agent Prompt Readonly Acceptance Work

## 1. Entry Gate

APLR3 may start only after APLR2 reviewer PASS.

## 2. Scope

Validate the published 2026-07-08 candidate-only DailyAgentPromptArtifact and Agent prompt latest pointer in readonly/no-OpenAI mode.

## 3. Required Checks

```text
latest pointer manifest == data_tw/artifacts/agent_daily_prompt/2026-07-08/manifest.json
manifest/context/text checksum == sha256:b65c3478e53c25194a0ebd7da5a50d6c23ce72c42edcda55e4ac2208e962bddc
candidate-only validator publish evidence == pass
readonly_strategy_snapshot/latest remains pointed at 2026-07-08 manifest
source citations exist and remain readonly
backend loader compatibility may be checked only without OpenAI calls
forbidden action audit remains pass
```

## 4. Stop Conditions

Stop if acceptance requires provider/network pull, provider publish, accepted latest switch, model scoring/training, strategy replay, OrderIntent, ReplayResult/NAV, OpenAI call, frontend/API/default switch, monitor, broker, order path, or production default switch.
