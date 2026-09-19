---
created_at: 2026-07-10
status: mainline
route: CLPR_CONTROLLED_LATEST_PUBLISH_ROUTE
coordinator: Codex
pbpr_prerequisite_verdict: PASS_CLOSE_PBPR_ROUTE_AND_RECOMMEND_SEPARATE_PUBLISH_ROUTE_CONFIRMATION
target_asof: 2026-07-08
production_trade_enabled: false
provider_pull_allowed: false
network_command_allowed: false
provider_publish_allowed: false
provider_accepted_latest_switch_allowed: false
qlib_accepted_latest_switch_allowed: false
legacy_option_c_latest_signal_switch_allowed: false
model_scoring_allowed: false
strategy_replay_allowed: false
agent_prompt_build_allowed: false
agent_prompt_publish_allowed: false
openai_call_allowed: false
monitor_write_allowed: false
order_or_target_output_allowed: false
production_default_switch_allowed: false
controlled_readonly_latest_publish_route_allowed: true
---

# CLPR Controlled Latest Publish Route Mainline

## 1. Goal

CLPR 的目标是把 PBPR 已验证的 `target_asof=2026-07-08` Model A `ModelSignalArtifact`，以最小、可审查、可回滚的方式推进到受控 readonly latest 路径。

本路线只解决：

```text
verified PBPR3_X ModelSignalArtifact
  -> canonical readonly ModelSignalArtifact copy
  -> explicit controlled latest pointer
  -> optional readonly snapshot pointer after validation
```

CLPR 不解决 provider refresh、formal qlib provider publish、accepted/latest switch、策略重放、Agent prompt 生成或任何交易执行问题。

## 2. Non-goals

CLPR 明确不做：

```text
real provider/network pull
Yahoo/Scrapling/FinMind refresh
provider publish
provider accepted latest switch
qlib accepted latest switch
legacy option_c_daily_signal/latest_signal.json switch
model scoring rerun
model training or tuning
strategy replay
ReplayResult/NAV generation
OrderIntentArtifact generation
Agent DailyAgentPromptArtifact build or publish
OpenAI call
frontend/API/default behavior switch
monitor config/scan/alerts write
broker, quick-trade, real order
target_position, target_weight, quantity, shares, lots output
```

## 3. Current Baseline

PBPR5 review 已确认：

```text
PBPR route closed
target_asof=2026-07-08
PBPR2A-AC provider candidate accepted under controlled AC root
PBPR3_X validator=PASS
PBPR3_X signals.csv rows=150
PBPR3_X forbidden_columns=[]
PBPR3_X duplicate_keys=0
PBPR4 source-context status=pass
PBPR3_X/PBPR4/PBPR5 manifests checksum recompute=pass
PBPR5 forbidden_action_audit.all_false=true
PBPR5 did_publish=false
PBPR5 authorizes_publish=false
```

当前已知 latest 状态：

```text
readonly_strategy_snapshot/latest.json currently points to 2026-06-18
legacy qlib_pipeline/data_tw/experiments/option_c_daily_signal/latest_signal.json currently points to 2026-06-17
PBPR3_X artifact is isolated under planned_future_outputs and is not published latest
FinMind raw may be newer than qlib/readonly latest; this route does not reconcile raw/provider freshness
```

## 4. Required Documents And Contracts

Executor / reviewer 必须读取：

```text
docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md
docs/tw_modular_contracts/MODEL_SIGNAL_CONTRACT_CN.md
docs/tw_modular_contracts/READONLY_STRATEGY_SNAPSHOT_CONTRACT_CN.md
docs/tw_modular_contracts/TW_AGENT_DAILY_PROMPT_ARTIFACT_CONTRACT_CN.md
docs/tw_portfolio_decision_model/POLICY_PBPR5_PRODUCTIONIZATION_CLOSURE_OR_PUBLISH_ROUTE_GATE_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_CLPR_CONTROLLED_LATEST_PUBLISH_ROUTE_MAINLINE_CN.md
```

CLPR0 起还必须读取本阶段 work document。

## 5. Allowed Publish Surface

CLPR 只允许在明确阶段中写以下受控 readonly artifact/pointer：

```text
data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/pbpr3x_modela_20260708_contained/
data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/latest.json
data_tw/artifacts/publish/readonly_strategy_snapshot/2026-07-08/
data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json
```

其中：

```text
data_tw/artifacts/signals/.../latest.json is a controlled ModelSignalArtifact latest pointer.
data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json is a readonly snapshot pointer.
Neither pointer is provider accepted latest or qlib accepted latest.
```

CLPR 不允许写：

```text
qlib_pipeline/data_tw/experiments/option_c_daily_signal/latest_signal.json
data_tw/experiments/option_c_daily_signal/latest_signal.json
provider accepted latest
qlib accepted latest
data_tw/artifacts/agent_daily_prompt/latest.json
configs/tw_product_artifact_registry.yaml
configs/tw_modular_registry.yaml
frontend/default/API behavior
```

## 6. Phase Plan

### CLPR0: Contract, Inventory, Promotion Plan

只读盘点 PBPR3_X / PBPR4 / PBPR5 输入、当前 latest 指针、目标 canonical 路径、checksum、rollback plan、validator plan。输出 work evidence 和执行报告。

Allowed writes:

```text
docs/tw_portfolio_decision_model/POLICY_CLPR0_CONTRACT_INVENTORY_AND_PROMOTION_PLAN_EXECUTION_REPORT_CN.md
docs/tw_portfolio_decision_model/POLICY_CLPR1_CANONICAL_SIGNAL_PROMOTION_DRY_RUN_WORK_CN.md
data_tw/experiments/controlled_latest_publish_route/clpr0_contract_inventory_and_promotion_plan/
scripts/build_tw_clpr0_promotion_plan.py
```

Forbidden in CLPR0:

```text
any latest pointer write
any canonical artifact copy
any provider/network/model/strategy/Agent/prompt/default/order action
```

### CLPR1: Canonical Signal Promotion Dry-run

从 PBPR3_X verified source 生成 dry-run promotion package，验证 canonical target shape、checksums、forbidden columns、duplicate keys、lineage。默认不写 canonical artifact，不写 latest pointer。

CLPR1 reviewer 通过后，若 dry-run 证明输入与目标无歧义，CLPR2 可执行 canonical signal copy 与 controlled signal latest pointer write。

### CLPR2: Controlled Signal Latest Publish

允许写：

```text
data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/pbpr3x_modela_20260708_contained/*
data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/latest.json
```

必须先备份任何 existing latest pointer 到 CLPR evidence root，写后必须复算 checksum 并证明 rollback 可恢复。CLPR2 不允许写 legacy `option_c_daily_signal/latest_signal.json`。

### CLPR3: Readonly Snapshot Candidate Or Blocker

检查 canonical signal latest 是否足以构建 readonly snapshot。若可构建，只允许生成 `data_tw/artifacts/publish/readonly_strategy_snapshot/2026-07-08/` 和 readonly snapshot latest pointer；若缺少策略/snapshot 合同输入，则输出 blocker，不得伪造动态 payload。

### CLPR4: Final Safety And Integration Acceptance

只读复核 latest pointer、artifact manifest、forbidden-action audit、可回滚性、后端 loader 兼容性。CLPR4 可关闭路线或建议另开 Agent prompt latest route。

## 7. Per-phase Executor Duties

Executor 必须：

```text
read mainline and phase work document
execute exactly one phase
avoid unrelated refactors
record before/after pointer fingerprints when writing is allowed
write durable evidence and execution report
stop on missing artifact, checksum mismatch, source ambiguity, or forbidden action need
```

## 8. Per-phase Reviewer Duties

Reviewer 必须：

```text
read mainline, phase work document, execution report
independently inspect evidence and checksums
verify no forbidden pointer/action changed
classify findings
write review report and next work document or blocker
```

## 9. Forbidden Actions

全路线禁止：

```text
provider/network pull
provider publish
provider accepted latest switch
qlib accepted latest switch
legacy option_c latest_signal switch
model scoring rerun
model training or tuning
strategy replay
ReplayResult/NAV generation
OrderIntentArtifact generation
Agent prompt build or publish
OpenAI call
frontend/API/default switch
monitor write/scan/alerts
broker, quick-trade, real order
target_position, target_weight, quantity, shares, lots output
```

## 10. Stop Conditions

必须停止并交回 coordinator/user：

```text
PBPR3_X source checksum cannot be verified
PBPR3_X source has forbidden columns or duplicate keys
canonical publish target would overwrite unrelated artifact
latest pointer target is ambiguous
rollback cannot be described or verified
readonly snapshot requires strategy replay or OrderIntentArtifact generation
Agent prompt latest is requested before separate route
any provider/qlib accepted latest switch is required
any external network or credential is required
```

## 11. Evidence Requirements

每阶段至少产出：

```text
artifact_manifest.json with sha256 checksums
forbidden_action_audit.json
pointer_fingerprint_before_after.json when writing pointers
rollback_plan.json when writing pointers
validator_report.json or blocker_report.json
execution report
review report
next work document
```

## 12. Closure Criteria

CLPR 可关闭的条件：

```text
CLPR0-CLPR4 all PASS or accepted PASS_WITH_CONDITIONS
canonical signal artifact validates
controlled signal latest pointer, if written, points only to canonical ModelSignalArtifact
readonly snapshot latest pointer, if written, points only to readonly snapshot
all rollback plans are verifiable
forbidden-action audit clean
no provider/qlib accepted latest, Agent prompt latest, default switch, monitor/broker/order/target output occurred
```

## 13. First Executor Command

```text
执行 CLPR0。读取 CLPR mainline、CLPR0 work doc、PBPR5 review、PBPR3_X/PBPR4/PBPR5 evidence 与相关合同。只做 contract/inventory/promotion plan，不写任何 latest pointer，不复制 canonical artifact，不触发 provider/network/model/strategy/Agent/prompt/default/order 行为。产出 CLPR0 evidence、execution report，并写 CLPR1 work doc。
```

## 14. First Reviewer Brief

```text
审查 CLPR0。独立复核 CLPR0 execution report、promotion plan、rollback plan、source/target pointer inventory、PBPR3_X/PBPR4/PBPR5 evidence、checksums 与 forbidden-action audit。若通过，写 CLPR0 review，并确认 CLPR1 是否仍为 dry-run only。不得批准任何 latest write，除非 CLPR1 dry-run 后进入 CLPR2。
```
