# QALD0 Contract And Current Gate Inventory No Publish Work

## 1. Scope

- Route: `QALD_QLIB_ACCEPTED_LATEST_DAILY_PROMOTION`
- Phase: `QALD0_CONTRACT_AND_CURRENT_GATE_INVENTORY_NO_PUBLISH`

QALD0 inventories the current state before any implementation or cron changes.

## 2. Allowed Actions

Allowed:

```text
read latest pointers
read daily-auto cron installed file and saved actual-cron evidence
read daily-auto job evidence
read FPALA/DAPR18/FPALE/Qlib accepted latest docs
read candidate artifact directories
read scripts/run_daily_tw_stock_auto_update.py relevant sections
run local readonly validators or QlibOptionCSignalReader reads
write QALD0 execution report and review docs
```

## 3. Forbidden Actions

Forbidden:

```text
provider pull/refresh
provider publish
formal provider mutation
qlib refresh
qlib accepted latest pointer switch
legacy latest switch
daily-auto manual run
cron edit
DAPR18 publish config change
readonly snapshot publish
Agent prompt publish
OpenAI
DB
strategy replay
monitor/broker/order/target
frontend/API default switch
```

## 4. Required Inventory

QALD0 must identify:

```text
current formal provider max date
current qlib accepted latest asof/run_id/hash
current DAPR18 signal latest asof/run_id/hash
current readonly snapshot latest asof/hash
current Agent prompt latest asof/hash
current installed cron flags for FPALA/DAPR18/provider candidate/model signal gate
whether natural cron already builds accepted latest candidates
whether reusable accepted latest builder exists or is hard-coded
what exact inputs are needed for QALD1
what remains exact-route controlled
```

## 5. Expected Output

Write:

```text
POLICY_QALD0_CONTRACT_AND_CURRENT_GATE_INVENTORY_NO_PUBLISH_EXECUTION_REPORT_CN.md
POLICY_QALD0_CONTRACT_AND_CURRENT_GATE_INVENTORY_NO_PUBLISH_REVIEW_CN.md
POLICY_QALD1_ACCEPTED_LATEST_CANDIDATE_BUILDER_CONTRACT_NO_POINTER_WRITE_WORK_CN.md
```

## 6. Pass Criteria

QALD0 passes if:

- latest concepts are correctly separated;
- current automation boundaries are documented;
- no forbidden action occurred;
- QALD1 can be scoped without guessing.

## 7. Stop Conditions

Stop if:

- evidence is missing for current latest state;
- current daily-auto scripts are inconsistent with installed cron;
- any no-publish route would require pointer writes;
- exact authorization would be needed before QALD1 can even design a builder.
