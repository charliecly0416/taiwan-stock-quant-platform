---
created_at: 2026-07-10T08:41:47+00:00
status: execution_report
route: APLR_AGENT_PROMPT_LATEST_ROUTE
phase: APLR3_AGENT_PROMPT_READONLY_ACCEPTANCE
target_asof: 2026-07-08
verdict: STOP_REPAIR_BEFORE_APLR3_REVIEWER
provider_pull_allowed: false
network_command_allowed: false
provider_publish_allowed: false
openai_call_allowed: false
production_default_switch_allowed: false
---

# APLR3 Agent Prompt Readonly Acceptance Execution Report

## 1. Verdict

STOP_REPAIR_BEFORE_APLR3_REVIEWER

APLR3 已完成 published 2026-07-08 candidate-only DailyAgentPromptArtifact 与 Agent prompt latest pointer 的只读/no-OpenAI 验收。

结论：STOP/repair：先修复 backend loader 对 candidate-only DailyAgentPromptArtifact 的本地加载兼容，再重新执行 APLR3。

## 2. Evidence

```text
data_tw/experiments/agent_prompt_latest_route/aplr3_agent_prompt_readonly_acceptance/latest_pointer_acceptance.json
data_tw/experiments/agent_prompt_latest_route/aplr3_agent_prompt_readonly_acceptance/artifact_checksum_acceptance.json
data_tw/experiments/agent_prompt_latest_route/aplr3_agent_prompt_readonly_acceptance/candidate_only_context_acceptance.json
data_tw/experiments/agent_prompt_latest_route/aplr3_agent_prompt_readonly_acceptance/validator_acceptance.json
data_tw/experiments/agent_prompt_latest_route/aplr3_agent_prompt_readonly_acceptance/backend_loader_readonly_acceptance.json
data_tw/experiments/agent_prompt_latest_route/aplr3_agent_prompt_readonly_acceptance/source_citation_acceptance.json
data_tw/experiments/agent_prompt_latest_route/aplr3_agent_prompt_readonly_acceptance/forbidden_action_audit.json
data_tw/experiments/agent_prompt_latest_route/aplr3_agent_prompt_readonly_acceptance/artifact_manifest.json
```

## 3. Required Check Summary

```json
{
  "artifact_checksum_acceptance_pass": true,
  "backend_loader_readonly_acceptance_pass": false,
  "candidate_only_context_acceptance_pass": true,
  "forbidden_action_audit_pass": true,
  "latest_pointer_acceptance_pass": true,
  "source_citation_acceptance_pass": true,
  "validator_acceptance_pass": true
}
```

## 4. Backend Loader Readonly Compatibility

```text
status=fail
no_openai_call=True
load_error=artifact_validation_failed:manifest.model_ids.treatment: expected 'e4_frozen_qlib_2018_2022_orthogonal_ltr_2023_2025', got None;manifest.strategy_rule: expected 'top50_exit_one_worst_sell', got 'candidate_only_no_strategy_replay';manifest.execution_price_mode: expected 'next_open', got 'not_applicable_candidate_only_no_strategy_replay';manifest.source_artifacts.readonly_strategy_snapshot_latest: source path does not exist: data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json;manifest.source_artifacts.readonly_strategy_snapshot_manifest: source path does not exist: data_tw/artifacts/publish/readonly_strategy_snapshot/2026-07-08/manifest.json;manifest.source_artifacts.readonly_strategy_snapshot_payload: source path does not exist: data_tw/artifacts/publish/readonly_strategy_snapshot/2026-07-08/strategy_snapshot.json;prompt_context.date_context.execution_price_mode: expected 'next_open', got 'not_applicable_candidate_only_no_strategy_replay';prompt_context.model_context.ranking_source: expected 'ltr_rerank_within_qlib_top50', got 'qlib_rank_controlled_signal';prompt_text.md: missing qlib score non-return/non-probability explanation;prompt_context:answer_policy.score_semantics_required: forbidden action term 'up_probability_cn';prompt_text.md:7: forbidden action term 'up_probability_cn'
```

## 5. Boundary

No provider/network pull, provider publish, accepted latest switch, model scoring/training, strategy replay, OrderIntent, ReplayResult/NAV, OpenAI call, frontend/backend/config/default switch, monitor, broker, order path, or trade sizing output was invoked.

## 6. Next Step

STOP/repair：先修复 backend loader 对 candidate-only DailyAgentPromptArtifact 的本地加载兼容，再重新执行 APLR3。
