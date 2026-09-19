---
created_at: 2026-07-10T08:19:43+00:00
status: work_document
route: APLR_AGENT_PROMPT_LATEST_ROUTE
phase: APLR2_AGENT_PROMPT_ARTIFACT_PUBLISH
target_asof: 2026-07-08
requires_aplr1_reviewer_pass: true
agent_prompt_artifact_write_allowed: true
agent_prompt_latest_write_allowed: true
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

# APLR2 Agent Prompt Artifact Publish Work

## 1. Entry Gate

APLR2 只能在 APLR1 reviewer PASS 后启动。若 APLR1 reviewer 未 PASS，必须 STOP/repair。

## 2. Scope

APLR2 只允许发布 2026-07-08 candidate-only DailyAgentPromptArtifact 与 Agent prompt
latest pointer。不得修改 readonly strategy snapshot latest、controlled signal latest、
provider/qlib accepted latest、legacy option_c latest，且不得调用 OpenAI。

## 3. Allowed Writes

```text
data_tw/artifacts/agent_daily_prompt/2026-07-08/manifest.json
data_tw/artifacts/agent_daily_prompt/2026-07-08/prompt_context.json
data_tw/artifacts/agent_daily_prompt/2026-07-08/prompt_text.md
data_tw/artifacts/agent_daily_prompt/latest.json
data_tw/experiments/agent_prompt_latest_route/aplr2_agent_prompt_artifact_publish/*.json
docs/tw_portfolio_decision_model/POLICY_APLR2_AGENT_PROMPT_ARTIFACT_PUBLISH_EXECUTION_REPORT_CN.md
```

## 4. Required Gates

```text
readonly_strategy_snapshot/latest still points to 2026-07-08 manifest
candidate_only=true
top_candidates=50
exit_candidates=[]
hold_candidates=[]
exit_hold_context_status=not_built_no_strategy_replay
source lineage points to controlled ModelSignalArtifact latest
strategy_rule=candidate_only_no_strategy_replay
treatment model null/not_applicable
ranking_source=qlib_rank_controlled_signal
candidate_boundary=qlib_top50
candidate-only validator passes
checksum recomputes as sha256:b65c3478e53c25194a0ebd7da5a50d6c23ce72c42edcda55e4ac2208e962bddc
rollback state captured before latest pointer write
```

## 5. Validator Requirement

APLR2 must implement or wrap a candidate-only validator. It must not silently reuse the
old full-strategy/LTR validator constants. Validator output must explicitly state that
candidate-only no-strategy-replay semantics are accepted for this artifact.

## 6. Stop Conditions

Stop if any publish step requires provider/network pull, model scoring/training, strategy
replay, OrderIntent, ReplayResult/NAV, OpenAI call, frontend/API/default switch, monitor,
broker, order path, readonly snapshot latest modification, or any trade execution/sizing
output.
