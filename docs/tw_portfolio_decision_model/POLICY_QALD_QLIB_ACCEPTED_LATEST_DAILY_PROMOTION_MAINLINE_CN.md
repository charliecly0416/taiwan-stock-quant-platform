# POLICY QALD: Qlib Accepted Latest Daily Promotion Mainline

## 1. Goal

QALD is the route for making qlib accepted latest promotion daily-operable without losing the explicit safety boundary.

The immediate goal is not to auto-switch `latest_signal.json`. The immediate goal is:

- daily cron builds or validates a qlib accepted latest candidate when provider/model inputs are ready;
- the candidate is validated by `QlibOptionCSignalReader`;
- rollback/fingerprint/diff plans are generated every day;
- no protected pointer changes during no-publish phases;
- after multiple natural cron passes, a separate exact authorization may enable controlled auto-switch.

## 2. Non-Goals

QALD does not authorize by default:

```text
provider pull/refresh
formal provider publish
qlib accepted latest switch
legacy latest switch
qlib refresh
DAPR18 product latest publish changes
readonly snapshot publish changes
Agent prompt publish changes
daily-auto manual run
cron edit
OpenAI
DB
strategy replay
monitor/broker/order/target
frontend/API default switch
```

Any actual pointer write still requires a later exact authorization phase.

## 3. Current Baseline

As of `2026-08-11`:

```text
formal provider calendar max=2026-08-07
qlib accepted latest asof=2026-08-07
qlib accepted latest run_id=option_c_daily_signal_20260807_fpale2_candidate_20260808T035113Z
DAPR18 controlled signal latest asof=2026-08-10
readonly strategy snapshot latest asof=2026-08-10
Agent DailyAgentPromptArtifact latest asof=2026-08-10
```

This means product latest is advancing, while qlib accepted latest remains exact-route controlled.

## 4. Design Principle

QALD must separate three concepts:

```text
provider candidate readiness
accepted latest candidate readiness
actual accepted latest pointer switch
```

The first two can become daily no-publish automation. The third must remain exact-gated until enough natural cron evidence proves the no-publish path is stable.

## 5. Phase Plan

```text
QALD0_CONTRACT_AND_CURRENT_GATE_INVENTORY_NO_PUBLISH
QALD1_ACCEPTED_LATEST_CANDIDATE_BUILDER_CONTRACT_NO_POINTER_WRITE
QALD2_DAILY_AUTO_NO_PUBLISH_WIRING_PREFLIGHT_OR_STOP
QALD3_NATURAL_CRON_OBSERVATION_NO_PUBLISH
QALD4_CONTROLLED_AUTO_SWITCH_ENABLEMENT_PREFLIGHT_OR_STOP
QALD5_ACTUAL_CONTROLLED_AUTO_SWITCH_ENABLEMENT_OR_DEFER
QALD6_ROUTE_CLOSURE_AND_MAINTENANCE_RUNBOOK
```

## 6. Phase Duties

### QALD0

Inventory current scripts, cron flags, latest pointers, accepted latest candidate artifacts, and DAPR18/FPALA boundaries.

No writes except docs/evidence.

### QALD1

Design or build a reusable accepted latest candidate builder that can target the latest ready asof, not hard-code one date.

No pointer writes.

### QALD2

Wire daily-auto no-publish evidence generation if the builder and validators are ready.

Cron edit requires exact authorization. If not authorized, write preflight and stop.

### QALD3

Observe multiple natural cron runs. Required pass evidence:

```text
candidate built for target trading day
QlibOptionCSignalReader.run_detail ok=true
top30_count=30
top50_count=50
protected latest unchanged
rollback plan exists
forbidden actions all false
```

### QALD4

Prepare controlled auto-switch preflight. It must define exact auth id, allowed write path, rollback, validator, and stop conditions.

### QALD5

Only with exact authorization, enable actual controlled auto-switch. This phase must still keep provider publish, qlib refresh, legacy latest, DAPR18 config changes, DB, OpenAI, strategy replay, and trading actions out of scope.

### QALD6

Close the route and write maintenance runbook.

## 7. Forbidden Actions

Forbidden unless a later exact phase explicitly authorizes the narrow action:

```text
provider pull/refresh
provider publish
formal provider mutation
qlib refresh
qlib accepted latest pointer write
legacy latest write
daily-auto manual run
cron edit
DAPR18 publish config change
readonly snapshot publish config change
Agent prompt publish config change
OpenAI
DB
strategy replay
monitor/broker/order/target
frontend/API default switch
```

Always forbidden in QALD:

```text
broker/order/quick-trade
target_position
target_weight
investment action recommendations
```

## 8. Stop Conditions

Stop if:

- formal provider does not cover target asof;
- provider candidate has fewer than 150 symbols;
- accepted latest candidate cannot pass `QlibOptionCSignalReader.run_detail`;
- top30/top50 counts are not exactly 30/50;
- any pointer write is required in a no-publish phase;
- actual cron edit is needed but not exactly authorized;
- DAPR18 authorization is being reused to unlock QALD actual accepted latest switch;
- any trading, DB, OpenAI, or frontend default switch is needed.

## 9. Evidence Requirements

Every phase must produce:

```text
execution report
review opinion
forbidden scope audit
latest pointer fingerprints when relevant
validator outputs
next work document or closure decision
```

## 10. Closure Criteria

QALD can close when either:

- daily no-publish candidate generation is installed and observed, while auto-switch remains deferred; or
- controlled auto-switch is enabled with exact authorization and observed through natural cron.

In both cases, the final runbook must clearly state which latest concepts auto-advance and which remain exact-route controlled.

## 11. First Executor Command

Execute `QALD0_CONTRACT_AND_CURRENT_GATE_INVENTORY_NO_PUBLISH`.

Read the mainline and QALD0 work doc. Inspect only local files and existing evidence. Do not run provider refresh, provider publish, accepted latest switch, qlib refresh, daily auto manual run, cron edit, DB, OpenAI, strategy replay, or trading actions.

## 12. First Reviewer Brief

Review QALD0 for:

- accurate separation of DAPR18 product latest, FPALA formal/accepted no-publish, and qlib accepted latest;
- no hidden pointer writes;
- sufficient evidence to decide QALD1;
- clear forbidden-action compliance.
