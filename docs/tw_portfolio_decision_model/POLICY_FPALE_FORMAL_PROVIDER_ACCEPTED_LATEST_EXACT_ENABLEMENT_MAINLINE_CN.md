# POLICY FPALE: Formal Provider / Accepted Latest Exact Enablement Mainline

## 1. Goal

FPALE is the exact-authorization route for actual formal provider publish and qlib accepted latest switch.

It starts after FPALA has closed as a no-publish observation route. FPALE is separate from FPALA and cannot reuse FPALA no-publish evidence as production write authorization.

Goals:

- Publish a validated provider candidate into the formal Option C qlib provider only after exact authorization.
- Build or validate a qlib accepted latest candidate only after the formal provider covers the target asof.
- Switch qlib accepted latest only after a separate exact authorization and reader validation.
- Keep formal provider publish and accepted latest switch as separate gates.

## 2. Non-Goals

FPALE does not authorize by default:

```text
provider pull/refresh
formal provider publish
qlib accepted latest switch
legacy latest switch
qlib refresh
DAPR18 product latest publish
readonly snapshot latest publish
Agent prompt latest publish
daily-auto manual run
cron edit
OpenAI
DB
strategy replay
monitor/broker/order/target
frontend/API default switch
```

Each actual write requires exact user authorization for that phase.

## 3. Current Baseline

Current candidate:

```text
target_asof=2026-08-07
candidate_root=qlib_pipeline/data_tw/experiments/daily_auto_provider_candidates/daily_auto_provider_candidate_20260807_20260807T103148Z/
staged_provider=qlib_pipeline/data_tw/experiments/daily_auto_provider_candidates/daily_auto_provider_candidate_20260807_20260807T103148Z/staged_qlib_bin/
source=Yahoo via Scrapling direct chart API with proxy
symbols_success=150
symbols_with_asof=150
staged_provider_calendar_max=2026-08-07
staged_provider_validation=pass
model_smoke=pass
staged_provider_file_count=1052
```

Current protected state:

```text
formal_provider_path=qlib_pipeline/data_tw/experiments/yahoo_adjusted_primary/option_c_150_qlib_bin/
formal_provider_calendar_max=2026-08-06
formal_provider_calendar_hash=e96bdad133fec265553d944f29ac3546eeeb03005c56d6862d591abe92e94422
qlib_accepted_latest_path=qlib_pipeline/data_tw/experiments/option_c_daily_signal/latest_signal.json
qlib_accepted_latest_asof=2026-08-06
qlib_accepted_latest_run_id=option_c_daily_signal_20260806_fpal4a_adapter_20260807T022328Z
qlib_accepted_latest_hash=09e17a2b30248b173d29520c0ae58b616efa11c5d57fe1ae68a3bae5c07a41dd
legacy_latest_asof=2026-06-01
DAPR18_product_latest_asof=2026-08-07
```

## 4. Gate Order

FPALE must follow this order:

```text
FPALE0_EXACT_ENABLEMENT_PREFLIGHT_OR_STOP
FPALE1_ACTUAL_FORMAL_PROVIDER_PUBLISH_OR_STOP
FPALE2_ACCEPTED_LATEST_CANDIDATE_BUILD_OR_STOP
FPALE3_ACCEPTED_LATEST_SWITCH_PREFLIGHT_OR_STOP
FPALE4_ACTUAL_ACCEPTED_LATEST_SWITCH_OR_STOP
FPALE5_ROUTE_CLOSURE_AND_DAILY_AUTO_ALIGNMENT_DECISION
```

Accepted latest switch must not run before formal provider publish passes validation and covers target_asof.

## 5. Exact Authorization Rule

The phrase "enter FPALE" authorizes only route/preflight work. It does not authorize actual writes.

Actual formal provider publish requires authorization that names:

```text
target_asof
candidate source root
formal provider destination root
allowed write set
rollback copy
before fingerprints
after fingerprints
diff
provider/calendar validators
post-write review
forbidden actions
```

Actual qlib accepted latest switch requires a separate authorization that names:

```text
target_asof
target_run_id
accepted latest pointer path
allowed write set
rollback copy
before fingerprints
after fingerprints
diff
QlibOptionCSignalReader validation
post-write review
forbidden actions
```

## 6. Stop Conditions

Stop if:

- exact authorization is missing for a write phase;
- provider candidate is missing, invalid, or not 150/150;
- staged provider calendar does not cover target_asof;
- formal provider does not cover target_asof before accepted latest switch;
- accepted latest candidate target_run_id is missing;
- rollback/fingerprint/diff plan is incomplete;
- any DAPR18 authorization is used to unlock FPALE writes;
- any broker/order/target/OpenAI/DB/frontend default switch is requested.

## 7. Closure Criteria

FPALE closes only when:

- formal provider publish is either completed with evidence or explicitly deferred;
- accepted latest switch is either completed with evidence or explicitly deferred;
- daily-auto alignment decision is documented;
- no boundary confusion remains between provider candidate, formal provider, qlib accepted latest, legacy latest, and DAPR18 product latest.
