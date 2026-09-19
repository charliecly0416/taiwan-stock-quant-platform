---
created_at: 2026-07-19
status: mainline
route: DAPR18_DAILY_AUTO_CONTROLLED_LATEST_PRODUCTIONIZATION
coordinator: Codex
production_allowed: false
provider_pull_allowed: false
provider_publish_allowed: false
provider_accepted_latest_switch_allowed: false
qlib_accepted_latest_switch_allowed: false
legacy_option_c_latest_signal_switch_allowed: false
controlled_signal_latest_publish_allowed_by_default: false
readonly_snapshot_latest_publish_allowed_by_default: false
agent_prompt_latest_publish_allowed_by_default: false
openai_call_allowed: false
daily_auto_run_allowed: false
crontab_change_allowed: false
monitor_write_allowed: false
broker_order_allowed: false
target_output_allowed: false
---

# DAPR18 Daily Auto Controlled Latest Productionization Mainline

## 1. Goal

DAPR18 的目标是把已经人工受控走通的 DAPR10/DAPR13/DAPR17 链路，产品化为 daily auto 中的显式、可审计、默认关闭的 controlled latest gate：

```text
raw/provider-or-bridge readiness
  -> Model A no-publish score / ModelSignalArtifact readiness
  -> controlled signal latest candidate or publish gate
  -> readonly strategy snapshot candidate or publish gate
  -> Agent DailyAgentPromptArtifact candidate or publish gate
  -> post-write validation / freshness evidence / rollback evidence
```

这条路线回答的问题是：每天数据抓取后，系统能否自动判断并推进所有关键 latest/artifact 新鲜度，而不是等前端或 Agent 使用时临时构建。

## 2. Non-Goals

DAPR18 不直接授权：

```text
provider pull
provider publish
formal qlib refresh
provider accepted latest switch
qlib accepted latest switch
legacy option_c latest_signal switch
cron/system crontab change
OpenAI call
strategy replay
monitor config/scan/alert write
broker, quick-trade, real order
OrderIntentArtifact
target_position, target_weight, quantity, shares, lots output
frontend/API production default switch
```

DAPR18 可以设计和实现 daily auto 内的受控 gate，但所有真实 latest pointer write 必须默认关闭，并在进入 actual publish/default enablement 前经过独立 exact authorization。

## 3. Current Baseline

截至 2026-07-19，只读诊断显示：

```text
installed cron: running
weekday daily scope: every 2 hours
weekday full/orthogonal scope: Asia/Taipei 22:45
2026-07-17 FinMind raw daily price: source_max_date=2026-07-17, symbol_count=150, row_count=25800
formal qlib provider calendar max: 2026-06-25
qlib accepted/latest signal asof: 2026-07-08
2026-07-17 daily_chain_status: RAW_READY_PROVIDER_STALE
blocker: qlib_provider_view_or_formal_calendar
orthogonal institutional/margin coverage: 75/150 for 2026-07-17
```

Current latest pointers are fresh to 2026-07-17 only because of explicit controlled DAPR publish phases:

```text
data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/latest.json
  created_by_planned_phase=DAPR10_ACTUAL_CONTROLLED_SIGNAL_LATEST_PUBLISH

data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json
  created_by_planned_phase=DAPR13_ACTUAL_READONLY_SNAPSHOT_PUBLISH_AFTER_EXACT_AUTHORIZATION

data_tw/artifacts/agent_daily_prompt/latest.json
  created by DAPR17 actual controlled Agent prompt latest publish
```

Cron still runs downstream in no-publish/dry-run mode:

```text
ENABLE_TW_ADOR_NO_PUBLISH_ORCHESTRATION_DRY_RUN=true
TW_ADOR_NO_PUBLISH_ORCHESTRATION_DRY_RUN=true
TW_AGENT_DAILY_PROMPT_DRY_RUN=true
ENABLE_TW_AGENT_DAILY_PROMPT_PUBLISH=false
TW_AGENT_DAILY_PROMPT_PUBLISH_LATEST=false
```

## 4. Required Prior Documents

Every DAPR18 phase must read the relevant subset:

```text
docs/tw_portfolio_decision_model/POLICY_PCOM3_DAILY_AUTO_PRODUCTION_READINESS_LATEST_PUBLISH_CONTRACT_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_ADOR_AUTOMATIC_DAILY_ORCHESTRATION_ROUTE_MAINLINE_CN.md
docs/tw_portfolio_decision_model/POLICY_ADOR_FINAL_CLOSURE_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_AOGE_AUTOMATIC_ORCHESTRATION_GATE_ENABLEMENT_MAINLINE_CN.md
docs/tw_portfolio_decision_model/POLICY_AOGE_FINAL_CLOSURE_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_DAPR8_CONTROLLED_MODELA_NO_PUBLISH_DRY_RUN_GATE_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_DAPR9_CONTROLLED_LATEST_PUBLISH_PREFLIGHT_OR_STOP_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_DAPR10_ACTUAL_CONTROLLED_SIGNAL_LATEST_PUBLISH_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_DAPR13_ACTUAL_READONLY_SNAPSHOT_PUBLISH_REVIEW_CN.md
docs/tw_portfolio_decision_model/POLICY_DAPR16_CONTROLLED_AGENT_PROMPT_PUBLISH_PREFLIGHT_OR_STOP_REVIEW_CN.md
data_tw/experiments/daily_accepted_production_readiness/dapr17_actual_controlled_agent_prompt_latest_publish/execution_report.json
docs/tw_modular_contracts/TW_PROJECT_DEVELOPMENT_CONSTITUTION_CN.md
docs/tw_modular_contracts/TW_DAILY_AUTO_UPDATE_RUNBOOK_CN.md
docs/tw_modular_contracts/TW_AGENT_DAILY_PROMPT_ARTIFACT_CONTRACT_CN.md
scripts/run_daily_tw_stock_auto_update.py
```

## 5. Readiness Concepts

DAPR18 must keep these states separate:

```text
raw-ready != provider/bridge-ready
provider/bridge-ready != model-score-ready
model-score-ready != controlled signal latest publish-ready
controlled signal latest != qlib accepted latest
readonly snapshot candidate != readonly snapshot latest publish
Agent prompt candidate != Agent prompt latest publish
Agent prompt latest != OpenAI answer generation
TradingAgents readonly context != order/target/trading signal
```

## 6. Protected Paths

Protected latest pointers:

```text
data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/latest.json
data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json
data_tw/artifacts/agent_daily_prompt/latest.json
qlib_pipeline/data_tw/experiments/option_c_daily_signal/latest_signal.json
data_tw/experiments/option_c_daily_signal/latest_signal.json
```

Provider and cron protected paths:

```text
qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/
qlib_pipeline/data_tw/experiments/option_c_daily_signal/
data_tw/ops/daily_auto_update/tw-daily-auto-update.installed.cron
system crontab
```

Any phase that writes a protected latest pointer must have:

```text
exact target_asof
exact source artifact directory
exact allowed write paths
before fingerprint
rollback copy
after fingerprint
diff
checksum validation
artifact validator
latest pointer payload validator
post-write review
explicit user authorization
```

## 7. Phase Plan

### DAPR18A - Contract Inventory And Gate Matrix

Inventory existing daily auto gates, DAPR publish scripts, validators, current cron flags, latest pointers, and future experiment data accounting. Produce a gate matrix that says which steps can be automatic dry-run now, which can become controlled publish later, and which must remain explicit authorization.

No code change, no cron change, no latest write.

### DAPR18B - Controlled Publish Orchestrator Design

Design the daily auto controlled latest sub-orchestrator:

```text
input readiness detector
provider/bridge selection contract
ModelSignalArtifact source adapter
controlled signal publish candidate planner
readonly snapshot candidate planner
Agent prompt candidate planner
validator chain
rollback/fingerprint plan
forbidden action audit
failure ledger / skipped_asof ledger
future experiment dataset coverage ledger
```

Design only unless DAPR18A review explicitly allows implementation.

### DAPR18C - Default-Off Implementation

Implement explicit env/CLI gates in `scripts/run_daily_tw_stock_auto_update.py` or helper scripts. Defaults must remain disabled or dry-run. The implementation may write job-dir evidence only unless a later exact publish phase authorizes protected latest writes.

### DAPR18D - No-Publish Natural Cron Acceptance

Observe natural cron jobs with DAPR18 evidence enabled but all publish writes disabled. Required evidence:

```text
3 valid trading days minimum
weekend/non-trading skip classification correct
raw-ready/provider-stale blocker explicit when applicable
future experiment dataset coverage ledger updated
protected latest fingerprints unchanged
forbidden actions all false
```

### DAPR18E - Controlled Publish Preflight Or Stop

For a concrete target_asof, run preflight for signal latest, readonly snapshot latest, and Agent prompt latest. This phase stops before protected latest writes and produces exact authorization text if and only if all validators pass.

### DAPR18F - Actual Controlled Publish After Exact Authorization

Only after user supplies exact authorization, write the allowed latest pointers for that one target_asof. This does not authorize cron/default automation.

### DAPR18G - Cron Default Enablement Preflight Or Stop

Decide whether daily cron may enable controlled publish gates by default. Requires successful DAPR18D natural evidence and at least one DAPR18F controlled publish with clean post-write review.

### DAPR18H - Operations Closure

Close the route as one of:

```text
MAINTENANCE_DRY_RUN_ONLY
CONTROLLED_PUBLISH_READY_BUT_CRON_DEFAULT_BLOCKED
CRON_DEFAULT_READY_AFTER_EXACT_OPS_AUTHORIZATION
STOP_WITH_BLOCKER
```

## 8. Future Experiment Data Scope

DAPR18 must preserve and improve daily accounting for data useful beyond the current frontend path:

```text
stock_ohlcv_adjusted_price
twii_market_index
finmind_raw_daily_price
corporate_actions
institutional_flow
margin_short
orthogonal_raw_archive
daily_ltr_source_freshness
readonly_price_twii_calendar_bridge
execution_price_readiness
schema_coverage_holiday_pending_evidence
```

The goal is not to force all categories to publish every day. The goal is to ensure each category has one of:

```text
captured
pending_with_retry_hint
skipped_by_calendar_or_contract
blocked_with_next_required_action
```

No dataset may silently remain at an old asof without ledger evidence.

## 9. Forbidden Actions

Forbidden until a later exact authorization explicitly narrows scope:

```text
provider pull
provider publish
formal qlib refresh
accepted/latest switch
legacy option_c latest_signal switch
controlled signal latest write
readonly snapshot latest write
Agent prompt latest write
OpenAI call
system crontab change
daily auto manual run
DB write
strategy replay
monitor write
broker/order/quick-trade
OrderIntentArtifact generation
target_position / target_weight / quantity / shares / lots output
frontend/API production default switch
```

## 10. Stop Conditions

Stop if:

```text
provider/bridge readiness cannot be determined from artifact-backed evidence
formal provider refresh is required but not authorized
ModelSignalArtifact cannot be produced without provider publish or qlib accepted latest switch
readonly snapshot or Agent prompt build requires OpenAI or dynamic service payload
any protected latest pointer would be written without exact authorization
cron/default would be changed before no-publish natural cron acceptance
future experiment data categories cannot be classified into captured/pending/skipped/blocked
```

## 11. Evidence Requirements

Each phase must produce:

```text
execution report
review report
artifact_manifest.json
forbidden_action_audit.json
gate_matrix or gate_status when relevant
protected pointer fingerprint audit when relevant
validator report or blocker report
next work document or closure decision
```

## 12. First Executor Command

```text
Read POLICY_DAPR18_DAILY_AUTO_CONTROLLED_LATEST_PRODUCTIONIZATION_MAINLINE_CN.md and execute DAPR18A_CONTRACT_INVENTORY_AND_GATE_MATRIX only. Do not edit scripts, cron, latest pointers, provider data, DB, frontend, backend, or configs. Produce the required inventory artifacts, execution report, and DAPR18B work draft.
```

## 13. First Reviewer Brief

```text
Review DAPR18A against this mainline. Confirm no forbidden actions occurred, all readiness states remain separated, protected paths are listed, and the gate matrix does not imply default publish enablement. Verdict must be PASS, PASS_WITH_CONDITIONS, FAIL_NEEDS_REPAIR, or STOP.
```
