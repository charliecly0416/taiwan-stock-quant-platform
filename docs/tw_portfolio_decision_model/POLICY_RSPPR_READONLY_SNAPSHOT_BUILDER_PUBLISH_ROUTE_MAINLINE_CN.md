---
created_at: 2026-07-10
status: mainline
route: RSPPR_READONLY_SNAPSHOT_BUILDER_PUBLISH_ROUTE
coordinator: Codex
prerequisite_route: CLPR_CONTROLLED_LATEST_PUBLISH_ROUTE
prerequisite_verdict: PASS_CLOSE_CLPR_CONTROLLED_SIGNAL_LATEST_ONLY_WITH_SNAPSHOT_BLOCKER
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
readonly_snapshot_publish_route_allowed: true
agent_prompt_build_allowed_in_rsppr: false
agent_prompt_publish_allowed_in_rsppr: false
openai_call_allowed: false
monitor_write_allowed: false
order_or_trade_target_output_allowed: false
production_default_switch_allowed: false
auto_enter_agent_prompt_latest_route_after_rsppr_pass: true
---

# RSPPR Readonly Snapshot Builder Publish Route Mainline

## 1. Goal

RSPPR 的目标是在 CLPR 已发布的 controlled `ModelSignalArtifact` latest 基础上，生成并发布一个 **candidate-only ReadonlyStrategySnapshot**，让下游 readonly context / Agent prompt 能读取稳定 artifact。

目标链路：

```text
CLPR controlled ModelSignalArtifact latest
  -> candidate-only ReadonlyStrategySnapshot artifact
  -> readonly_strategy_snapshot/latest.json
  -> if RSPPR final PASS, auto-open Agent prompt latest route
```

Candidate-only 含义：

```text
top_candidates derived from controlled signal ranks
exit_candidates=[]
hold_candidates=[]
no strategy replay
no OrderIntent
no ReplayResult/NAV
not production trading default
not portfolio target
```

## 2. Non-goals

RSPPR 不做：

```text
provider/network pull
provider publish
provider or qlib accepted latest switch
legacy option_c latest_signal switch
model scoring or training
strategy replay
OrderIntentArtifact generation
ReplayResult/NAV generation
Agent prompt build/publish
OpenAI call
frontend/API/default switch
monitor config/scan/alerts
broker, quick-trade, real order
target_position, target_weight, quantity, shares, lots output
```

Agent prompt latest 会在 RSPPR final PASS 后另开独立 route，不能混入 RSPPR。

## 3. Current Baseline

CLPR final review 已确认：

```text
controlled signal latest path=data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/latest.json
asof=2026-07-08
signal_asof=2026-07-08
run_id=pbpr3x_modela_20260708_contained
signals.csv rows=150
duplicate_key_count=0
forbidden_columns=[]
validator.status=PASS
readonly_strategy_snapshot/latest.json unchanged at 2026-06-18
data_tw/artifacts/publish/readonly_strategy_snapshot/2026-07-08/ not created
Agent latest absent / unchanged
provider/qlib accepted latest not switched
legacy option_c latest_signal not switched
```

Existing `scripts/validate_tw_modular_readonly_snapshot.py` is LTR-primary hardcoded and cannot validate this Model A candidate-only snapshot. RSPPR must therefore generate its own candidate-only validator evidence without changing that existing validator or product defaults.

## 4. Required Documents And Contracts

Every phase must read:

```text
docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md
docs/tw_modular_contracts/MODEL_SIGNAL_CONTRACT_CN.md
docs/tw_modular_contracts/READONLY_STRATEGY_SNAPSHOT_CONTRACT_CN.md
docs/tw_portfolio_decision_model/POLICY_CLPR4_FINAL_SAFETY_AND_INTEGRATION_ACCEPTANCE_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_RSPPR_READONLY_SNAPSHOT_BUILDER_PUBLISH_ROUTE_MAINLINE_CN.md
```

Agent route phases must additionally read:

```text
docs/tw_modular_contracts/TW_AGENT_DAILY_PROMPT_ARTIFACT_CONTRACT_CN.md
docs/tw_modular_contracts/TW_AGENT_DAILY_PROMPT_OPENAI_REBUILD_DESIGN_CN.md
```

## 5. Architecture Boundary

RSPPR can write only:

```text
data_tw/artifacts/publish/readonly_strategy_snapshot/2026-07-08/
data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json
data_tw/experiments/readonly_snapshot_builder_publish_route/
scripts/build_tw_rsppr*.py
docs/tw_portfolio_decision_model/POLICY_RSPPR*.md
```

RSPPR cannot write:

```text
data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/latest.json
data_tw/artifacts/agent_daily_prompt/latest.json
qlib_pipeline/data_tw/experiments/option_c_daily_signal/latest_signal.json
data_tw/experiments/option_c_daily_signal/latest_signal.json
configs/tw_product_artifact_registry.yaml
configs/tw_modular_registry.yaml
frontend/
backend/
```

## 6. Phase Plan

### RSPPR0: Contract Extension And Publish Plan

Define candidate-only snapshot contract, source inventory, target paths, validator plan, rollback plan. No snapshot artifact or latest write.

### RSPPR1: Candidate-only Snapshot Dry-run

Build dry-run payload plan from controlled signal latest. Verify top candidates, required fields, safety flags, checksum plan, latest pointer payload plan. No snapshot artifact or latest write.

### RSPPR2: Candidate-only Snapshot Publish

If RSPPR1 reviewer PASS, write:

```text
data_tw/artifacts/publish/readonly_strategy_snapshot/2026-07-08/manifest.json
data_tw/artifacts/publish/readonly_strategy_snapshot/2026-07-08/strategy_snapshot.json
data_tw/artifacts/publish/readonly_strategy_snapshot/2026-07-08/validation_report.json
data_tw/artifacts/publish/readonly_strategy_snapshot/2026-07-08/forbidden_scope_audit.json
data_tw/artifacts/publish/readonly_strategy_snapshot/2026-07-08/checksum_manifest.json
data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json
```

Must backup previous latest pointer and prove rollback.

### RSPPR3: Snapshot Readonly Integration Acceptance

Readonly validation of published snapshot latest, backend loader compatibility, pointer boundaries, and no unsafe actions.

### RSPPR4: Final Closure And Agent Route Gate

Close RSPPR if all phases PASS. If no blocker remains, automatically open Agent prompt latest route with its own mainline/work doc.

## 7. Candidate-only Snapshot Contract

RSPPR snapshot must keep the existing artifact type:

```text
artifact_type=readonly_strategy_snapshot
schema_version=readonly_strategy_snapshot_r13_v1
display_role=primary_readonly_candidate
readonly_only=true
production_trade_enabled=false
no_order_action=true
not_target_position=true
not_investment_advice=true
is_production_trading_default=false
```

RSPPR-specific metadata must disclose:

```text
candidate_only=true
source_lineage=clpr_controlled_model_signal_latest
model_id=e4_frozen_qlib_2018_2022
base_model_id=e4_frozen_qlib_2018_2022
ranking_source=qlib_rank_controlled_signal
candidate_boundary=qlib_top50
exit_candidates=[]
hold_candidates=[]
exit_hold_context_status=not_built_no_strategy_replay
```

`strategy_snapshot.json` may include `rankings` and `strategy` sections for Agent prompt source compatibility, but those sections must be readonly and candidate-only.

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
Agent prompt build/publish inside RSPPR
OpenAI call
frontend/API/default switch
monitor write/scan/alerts
broker, quick-trade, real order
target_position, target_weight, quantity, shares, lots output
```

## 9. Stop Conditions

Stop if:

```text
controlled signal latest missing or checksum mismatch
signals.csv fails row/asof/duplicate/forbidden checks
candidate-only snapshot would be mistaken for full strategy snapshot
exit/hold context is required for pass but absent
existing readonly snapshot latest changed unexpectedly
rollback cannot be proven
Agent prompt route would need to bypass DailyAgentPromptArtifact
any provider/qlib accepted latest, legacy option_c latest, default switch, order, target, or OpenAI action is required
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

Publish phases must also produce:

```text
pre_publish_state.json
publish_result.json
post_publish_validation.json
rollback_evidence.json
unchanged_pointer_audit.json
```

## 11. Closure Criteria

RSPPR closes only if:

```text
candidate-only readonly snapshot latest points to 2026-07-08
snapshot validator evidence passes
controlled signal latest remains unchanged
legacy option_c latest_signal unchanged
Agent latest unchanged during RSPPR
provider/qlib accepted latest unchanged
no default switch, monitor/broker/order/target
rollback evidence is explicit
all artifact manifests recompute pass
```

Then coordinator may auto-open Agent prompt latest route.

## 12. First Executor Command

```text
执行 RSPPR0。只做 candidate-only snapshot contract extension、source inventory、publish plan、rollback plan、validator plan。不得写 readonly snapshot artifact/latest，不得构建 Agent prompt，不得触发 provider/model/strategy/replay/order/default 行为。
```

## 13. First Reviewer Brief

```text
审查 RSPPR0。确认 candidate-only contract 不冒充 full strategy snapshot；确认 RSPPR1 仍是 dry-run；确认没有写 snapshot latest、Agent latest、provider/qlib accepted latest 或 legacy option_c latest_signal。
```
