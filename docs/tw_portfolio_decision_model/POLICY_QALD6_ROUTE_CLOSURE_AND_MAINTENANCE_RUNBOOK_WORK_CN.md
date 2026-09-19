# POLICY QALD6 Route Closure And Maintenance Runbook Work

## 1. Scope

- Route: `QALD_QLIB_ACCEPTED_LATEST_DAILY_PROMOTION`
- Phase: `QALD6_ROUTE_CLOSURE_AND_MAINTENANCE_RUNBOOK`
- Prior phase: `QALD5_ACTUAL_CONTROLLED_ACCEPTED_LATEST_AUTO_SWITCH_OR_DEFER`
- Required prior verdict: `PASS`
- QALD5 review: `docs/tw_portfolio_decision_model/POLICY_QALD5_ACTUAL_CONTROLLED_ACCEPTED_LATEST_AUTO_SWITCH_OR_DEFER_REVIEW_CN.md`

QALD6 closes the controlled accepted-latest promotion route and writes a maintenance runbook. It must not perform another accepted latest switch.

## 2. Current Accepted State

The qlib accepted latest pointer is now expected to remain:

```text
path=qlib_pipeline/data_tw/experiments/option_c_daily_signal/latest_signal.json
asof=2026-08-12
status=accepted
run_id=option_c_daily_signal_20260812_qald2r_candidate_20260812T123001Z
```

The rollback copy for the pre-QALD5 state remains:

```text
data_tw/experiments/qald_controlled_auto_switch_preflight/qald5_actual_switch_20260812T000000Z/latest_signal.json.rollback
```

That rollback copy restores the prior `2026-08-07` accepted latest pointer if a separately authorized rollback is ever required.

## 3. Allowed Actions

Allowed local reads:

```text
docs/tw_portfolio_decision_model/POLICY_QALD*_CN.md
data_tw/experiments/qald_controlled_auto_switch_preflight/qald4_preflight_20260812T123001Z.json
data_tw/experiments/qald_controlled_auto_switch_preflight/qald5_actual_switch_20260812T000000Z/latest_signal.json.rollback
qlib_pipeline/data_tw/experiments/option_c_daily_signal/latest_signal.json
qlib_pipeline/data_tw/experiments/option_c_daily_signal/option_c_daily_signal_20260812_qald2r_candidate_20260812T123001Z/*
data_tw/ops/daily_auto_update/tw-daily-auto-update.installed.cron
actual crontab via read-only `crontab -l`
```

Allowed validation:

```text
QlibOptionCSignalReader.latest(bucket=all/top30/top50, enrich_trend=False)
QlibOptionCSignalReader.run_detail(run_id=option_c_daily_signal_20260812_qald2r_candidate_20260812T123001Z, bucket=all, enrich_trend=False)
sha256sum on target/protected pointers, formal provider files, installed cron
line counts for top30/top50
readonly grep/rg checks for installed cron and actual crontab
```

Allowed writes:

- QALD6 closure/runbook execution report;
- QALD6 review document;
- optional route closure summary under `docs/tw_portfolio_decision_model/`.

## 4. Forbidden Actions

QALD6 must not run or trigger:

```text
daily-auto manual run
provider pull/refresh/publish
formal provider mutation
qlib refresh
qlib accepted latest pointer switch
legacy latest switch
DAPR18 signal latest write
readonly snapshot publish
Agent prompt publish
installed cron edit
actual crontab edit
DB/OpenAI
strategy replay
monitor/broker/order/target
target_position
target_weight
frontend/API default switch
```

QALD6 must not install an automatic QALD5 switch cron. The installed and actual cron state must keep:

```text
TW_QALD_ACCEPTED_LATEST_CANDIDATE_NO_POINTER=true
TW_QALD_ACCEPTED_LATEST_CANDIDATE_ALLOW_POINTER_WRITE=false
TW_QALD_ACCEPTED_LATEST_CANDIDATE_EXACT_AUTHORIZATION_ID=""
```

## 5. Closure Checks

QALD6 execution should verify:

1. QALD5 review verdict is `PASS`.
2. Target pointer still parses as `asof=2026-08-12`, `status=accepted`, and `run_id=option_c_daily_signal_20260812_qald2r_candidate_20260812T123001Z`.
3. `QlibOptionCSignalReader.latest(bucket=all)` returns `ok=true`, `top30_count=30`, `top50_count=50`, and readonly trading flags.
4. `QlibOptionCSignalReader.run_detail(target_run_id, bucket=all)` returns the same accepted run.
5. Rollback copy exists and parses as `asof=2026-08-07`, `status=accepted`.
6. Candidate `formal_validation.json` remains `status=PASS`.
7. Protected pointers remain unchanged:
   - `data_tw/experiments/option_c_daily_signal/latest_signal.json`
   - `data_tw/artifacts/signals/e4_frozen_qlib_2018_2022/latest.json`
   - `data_tw/artifacts/publish/readonly_strategy_snapshot/latest.json`
   - `data_tw/artifacts/agent_daily_prompt/latest.json`
8. Formal provider files remain unchanged:
   - `qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin/calendars/day.txt`
   - `qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin/instruments/all.txt`
9. Installed cron and actual crontab do not contain a QALD5 switch task or an exact authorization id.
10. Forbidden scope audit has all forbidden actions false; only the already-completed QALD5 target pointer write is historical evidence, not a QALD6 action.

## 6. Maintenance Runbook

Daily steady state after QALD5:

- Natural daily-auto may continue to build QALD accepted-latest candidates in no-pointer mode.
- Candidate builder output is evidence only while `TW_QALD_ACCEPTED_LATEST_CANDIDATE_ALLOW_POINTER_WRITE=false`.
- A future accepted latest switch requires a fresh QALD preflight, exact target asof/run id, rollback path, before/after fingerprints, reader validation, and explicit authorization.
- QALD5 authorization id `QALD_CONTROLLED_ACCEPTED_LATEST_AUTO_SWITCH_20260812` must not be reused for a future date.
- Stale or independent downstream latest concepts must not be collapsed into qlib accepted latest:
  - legacy Option C latest;
  - DAPR18 signal latest;
  - readonly strategy snapshot latest;
  - Agent DailyAgentPromptArtifact latest;
  - formal provider latest.
- If downstream readonly snapshot or Agent prompt needs to advance to the new qlib accepted latest, that must use a separate route with its own preflight/review and no trading or provider side effects.

Rollback guidance:

- Do not rollback during QALD6.
- If rollback is requested later, require a separate exact authorization naming the rollback source and target path.
- The rollback operation must write only `qlib_pipeline/data_tw/experiments/option_c_daily_signal/latest_signal.json`.
- After rollback, rerun `QlibOptionCSignalReader.latest(bucket=all)` and verify it returns the restored `2026-08-07` accepted state.

## 7. Stop Conditions

Stop QALD6 and write a blocker report if:

- QALD5 review is missing or not `PASS`;
- current accepted latest no longer points to `2026-08-12` / target run id;
- reader latest/run_detail fails;
- rollback copy is missing or does not parse as the 2026-08-07 prior accepted state;
- any protected pointer or formal provider fingerprint changed unexpectedly;
- installed cron or actual crontab contains a QALD5 pointer-write task;
- closure would require provider refresh/publish, qlib refresh, another pointer switch, downstream publish, DB/OpenAI, strategy replay, trading, or frontend/API default switch.

## 8. Required Execution Report

Write:

```text
docs/tw_portfolio_decision_model/POLICY_QALD6_ROUTE_CLOSURE_AND_MAINTENANCE_RUNBOOK_EXECUTION_REPORT_CN.md
```

The report must include:

- QALD5 review verdict reference;
- current accepted latest pointer payload and sha256;
- reader latest/run_detail validation summary;
- rollback copy path and sha256;
- protected pointer/formal provider/cron unchanged evidence;
- maintenance runbook summary;
- forbidden action audit;
- final decision: `PASS_ROUTE_CLOSED`, `PASS_ROUTE_CLOSED_WITH_DOWNSTREAM_DEFERRED`, or `STOP`.

## 9. Reviewer Brief

The QALD6 reviewer must confirm this phase was closure-only. A passing review should explicitly state that no provider/qlib refresh, no cron edit, no additional pointer switch, no downstream latest publish, and no trading/DB/OpenAI/frontend default action occurred.
