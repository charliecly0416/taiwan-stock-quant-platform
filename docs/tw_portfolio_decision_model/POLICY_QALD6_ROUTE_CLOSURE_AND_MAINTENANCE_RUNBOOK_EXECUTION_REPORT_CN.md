# POLICY QALD6 Route Closure And Maintenance Runbook Execution Report

## 1. Scope

- Route: `QALD_QLIB_ACCEPTED_LATEST_DAILY_PROMOTION`
- Phase: `QALD6_ROUTE_CLOSURE_AND_MAINTENANCE_RUNBOOK`
- Final decision: `PASS_ROUTE_CLOSED_WITH_DOWNSTREAM_DEFERRED`
- Closure mode: readonly verification and runbook write only

QALD6 did not perform another accepted latest switch. It did not run daily-auto, provider pull/refresh/publish, qlib refresh, cron edit, downstream latest publish, DB/OpenAI, strategy replay, monitor/broker/order/target, target position/weight, or frontend/API default switch.

## 2. Prior Verdict

QALD5 review:

```text
docs/tw_portfolio_decision_model/POLICY_QALD5_ACTUAL_CONTROLLED_ACCEPTED_LATEST_AUTO_SWITCH_OR_DEFER_REVIEW_CN.md
verdict=PASS
```

The review confirmed the controlled QALD5 write was limited to:

```text
qlib_pipeline/data_tw/experiments/option_c_daily_signal/latest_signal.json
```

## 3. Current Qlib Accepted Latest

Current pointer:

```text
path=qlib_pipeline/data_tw/experiments/option_c_daily_signal/latest_signal.json
sha256=b9f663b276e70ce33fd847a528149603ecf62aca63424ef8f70da4b074515fad
```

Payload:

```text
asof=2026-08-12
status=accepted
run_id=option_c_daily_signal_20260812_qald2r_candidate_20260812T123001Z
run_dir=data_tw/experiments/option_c_daily_signal/option_c_daily_signal_20260812_qald2r_candidate_20260812T123001Z
created_at=2026-08-12T13:45:00Z
diagnostic_only=true
research_signal_not_order=true
```

## 4. Reader Validation

`QlibOptionCSignalReader.latest(bucket=all, enrich_trend=False)`:

```text
ok=true
status=accepted
asof=2026-08-12
run_id=option_c_daily_signal_20260812_qald2r_candidate_20260812T123001Z
top30_count=30
top50_count=50
warnings=[]
orders_enabled=false
connects_to_broker=false
writes_orders=false
writes_positions=false
research_signal_not_order=true
```

`QlibOptionCSignalReader.run_detail(target_run_id, bucket=all, enrich_trend=False)` was already independently verified in QALD5 review with the same accepted run and counts.

Candidate row counts:

```text
top30_signals.csv lines=31, data_rows=30
top50_signals.csv lines=51, data_rows=50
```

Candidate `formal_validation.json`:

```text
path=qlib_pipeline/data_tw/experiments/option_c_daily_signal/option_c_daily_signal_20260812_qald2r_candidate_20260812T123001Z/formal_validation.json
sha256=70c14beaf9e636e1046c99e5785b0a352d1b6d2abc90a816803b59eba95e0c82
status=PASS
target_asof=2026-08-12
run_id=option_c_daily_signal_20260812_qald2r_candidate_20260812T123001Z
```

## 5. Rollback Reference

Rollback copy remains available:

```text
data_tw/experiments/qald_controlled_auto_switch_preflight/qald5_actual_switch_20260812T000000Z/latest_signal.json.rollback
sha256=e9c9e5cf5fca8fb2e2da9a1c51624e3e9bbf6b155962b4d4adac11bc5e0a229b
```

It restores the prior accepted latest pointer:

```text
asof=2026-08-07
status=accepted
run_dir=data_tw/experiments/option_c_daily_signal/option_c_daily_signal_20260807_fpale2_candidate_20260808T035113Z
```

Rollback was not executed in QALD6. Any future rollback requires a separate exact authorization.

## 6. Protected Boundary State

QALD5 review already verified these non-target pointers remained unchanged after the controlled switch:

- legacy latest:
  `data_tw/experiments/option_c_daily_signal/latest_signal.json`
- DAPR18 signal latest:
  `data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/latest.json`
- readonly strategy snapshot latest:
  `data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json`
- Agent DailyAgentPromptArtifact latest:
  `data_tw/artifacts/agent_daily_prompt/latest.json`

Formal provider remained unchanged:

- `qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin/calendars/day.txt`
- `qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin/instruments/all.txt`

Installed cron fingerprint:

```text
data_tw/ops/daily_auto_update/tw-daily-auto-update.installed.cron
sha256=19315007426df76b6e424972db48da40fed5fd8dda23522ba6854d88ac5e7d7a
```

Installed cron QALD flags remain no-pointer:

```text
ENABLE_TW_QALD_ACCEPTED_LATEST_CANDIDATE_BUILDER=true
TW_QALD_ACCEPTED_LATEST_CANDIDATE_NO_POINTER=true
TW_QALD_ACCEPTED_LATEST_CANDIDATE_ALLOW_POINTER_WRITE=false
TW_QALD_ACCEPTED_LATEST_CANDIDATE_EXACT_AUTHORIZATION_ID=""
TW_QALD_ACCEPTED_LATEST_CANDIDATE_TARGET_ASOF=""
TW_QALD_ACCEPTED_LATEST_CANDIDATE_SOURCE_ROOT=""
```

Therefore QALD daily automation remains candidate/evidence generation only. QALD5 did not install an automatic pointer switch.

## 7. Maintenance Runbook

### Daily State

- Natural cron may continue building QALD accepted-latest candidates.
- As long as `TW_QALD_ACCEPTED_LATEST_CANDIDATE_ALLOW_POINTER_WRITE=false`, those candidates are evidence only and do not switch `latest_signal.json`.
- `qlib accepted latest` is now fresh to `2026-08-12`.
- DAPR18 signal latest, readonly snapshot latest, and Agent prompt latest are separate downstream/product latest concepts. They must not be treated as proof that qlib accepted latest switched, and qlib accepted latest must not be used as implicit authorization to publish them.

### Future Accepted Latest Switch

For any future date, require a fresh route:

1. Natural cron candidate evidence for the target date.
2. Reader validation `ok=true`, `top30_count=30`, `top50_count=50`.
3. Fresh QALD preflight naming exact target asof/run id.
4. New authorization id; do not reuse `QALD_CONTROLLED_ACCEPTED_LATEST_AUTO_SWITCH_20260812`.
5. Rollback copy and before/after fingerprints.
6. Only one allowed write path:
   `qlib_pipeline/data_tw/experiments/option_c_daily_signal/latest_signal.json`.
7. No provider publish, qlib refresh, legacy latest switch, downstream latest publish, DB/OpenAI, strategy replay, trading, or frontend/API default switch unless separately authorized by a different route.

### Future Auto-Switch Enablement

QALD is not yet in fully automatic accepted-latest switch mode. To enable automatic switching, a separate route must:

- design cron flags for pointer-write mode;
- require a non-reused exact authorization id;
- define stop/rollback behavior for each day;
- prove multiple natural cron cycles can switch safely;
- keep provider publish, qlib refresh, DB/OpenAI, replay, and trading outside the switch scope.

Until that route exists, the stable state is:

```text
daily no-pointer candidate generation: enabled
actual qlib accepted latest switch: exact-route controlled
automatic qlib accepted latest switch: not enabled
```

### Rollback

Do not rollback unless explicitly authorized. If authorized later:

- write only `qlib_pipeline/data_tw/experiments/option_c_daily_signal/latest_signal.json`;
- use the rollback copy path above;
- rerun `QlibOptionCSignalReader.latest(bucket=all)`;
- verify restored `asof=2026-08-07`;
- verify protected non-target pointers and formal provider unchanged.

## 8. Forbidden Action Audit

QALD6 action audit:

```text
daily_auto_manual_run=false
provider_pull_or_refresh=false
provider_publish=false
formal_provider_mutation=false
qlib_refresh=false
qlib_accepted_latest_pointer_switch=false
legacy_latest_switch=false
dapr18_signal_latest_write=false
readonly_snapshot_latest_write=false
agent_prompt_latest_write=false
installed_cron_edit=false
actual_crontab_edit=false
db_access_or_write=false
openai_call=false
strategy_replay=false
monitor_broker_order_target=false
target_position_or_weight_generated=false
frontend_api_default_switch=false
```

Historical QALD5 controlled target pointer write remains accepted and reviewed as `PASS`; it is not a QALD6 action.

## 9. Final Decision

`PASS_ROUTE_CLOSED_WITH_DOWNSTREAM_DEFERRED`

QALD closes with qlib accepted latest promoted to `2026-08-12` by a reviewed, exact-authorized, single-path pointer switch. The daily cron remains in no-pointer candidate generation mode. Downstream publish routes and any future automatic accepted-latest pointer-write mode remain deferred to separate exact routes.
