# DAPR7 Same-Lineage Yahoo-Adjusted Exact-Target Bridge Build No-Publish Work

创建时间：2026-07-18

## Scope

进入 DAPR7：

```text
target_asof=2026-07-17
required_lineage=yahoo_adjusted_primary / Yahoo-Scrapling adjusted OHLCV
goal=obtain same-lineage exact-target bridge/provider candidate without publish
```

本阶段先执行本地 same-lineage inventory 与 provider-only rerun plan。除非另行明确授权，不执行 live Yahoo/Scrapling pull。

## Required Inputs

- DAPR1 accepted input contract:
  `data_tw/experiments/daily_accepted_production_readiness/dapr1_canonical_bridge_contract/bridge_contract.json`
- DAPR6 Stop:
  `data_tw/experiments/daily_accepted_production_readiness/dapr6_lineage_model_compatibility_review_or_stop/lineage_model_compatibility_decision.json`
- Existing local Yahoo-adjusted / Yahoo-Scrapling candidates under:
  - `qlib_pipeline/data_tw/experiments/`
  - `data_tw/experiments/`

## Allowed Actions

- Read local candidate/provider/normalized files.
- Inventory local `candidate_normalized`, `option_c_150_normalized`, `normalized_nonempty`.
- Inventory local qlib provider roots with `calendars/day.txt`, `instruments/all.txt`, and `features`.
- Write DAPR7 isolated evidence.
- Write a provider-only rerun plan.

## Forbidden Actions

- live provider pull / Yahoo / Scrapling unless separately authorized；
- provider publish；
- formal provider/calendar/normalized mutation；
- qlib refresh；
- accepted latest switch；
- Model A scoring；
- ModelInferenceInput / ScoreJob / ModelSignal build；
- readonly/Agent latest publish；
- OpenAI；
- DB access；
- monitor/broker/order/target/quantity output。

## Required Artifacts

Output root:

```text
data_tw/experiments/daily_accepted_production_readiness/dapr7_same_lineage_yahoo_adjusted_exact_target_bridge_build_no_publish/
```

Required:

- `local_same_lineage_inventory.json`
- `provider_only_rerun_plan.json`
- `candidate_or_blocker_decision.json`
- `same_lineage_bridge_blocker.json`
- `forbidden_action_audit.json`
- `artifact_manifest.json`

## Decision Policy

If a local same-lineage provider root already satisfies:

- calendar includes `2026-07-17`
- instruments count = 150
- required qlib feature fields for all 150 symbols

then decision may be:

```text
LOCAL_SAME_LINEAGE_YAHOO_ADJUSTED_PROVIDER_READY_FOR_DAPR3_VALIDATION
```

If only normalized files cover `2026-07-17`, decision must require provider/bin build.

If neither exists, decision must be:

```text
BLOCKED_NO_LOCAL_SAME_LINEAGE_YAHOO_ADJUSTED_EXACT_TARGET_CANDIDATE
```

## Provider-Only Rerun Plan

The rerun plan must use:

```text
qlib_pipeline/examples/tw/run_option_c_yahoo_scrapling_refresh.py
```

Required boundaries:

- `--provider-only`
- Yahoo/Scrapling only
- no FinMind fallback
- no mixed provider
- no prior-asof fill
- output under `data_tw/experiments/provider_bridge_productionization/`
- no provider publish
- no qlib refresh
- no accepted/latest switch
- no Model A scoring

## Executor Command

```text
Run scripts/build_tw_dapr7_same_lineage_yahoo_adjusted_bridge_no_publish.py. Do local inventory and write provider-only rerun plan. Do not execute live Yahoo/Scrapling pull unless separately authorized.
```
