# DAPR3 Exact-Target Provider/Bridge Candidate Route 主线

创建时间：2026-07-18

## 1. Goal

DAPR3 是 DAPR0-DAPR2 之后的 exact-target provider/bridge candidate-or-blocker 路线。目标是针对 `target_asof=2026-07-17` 判断是否存在可被后续 Model A no-publish dry-run 使用的 exact-target 输入：

```text
local exact-target provider_candidate_readiness
or local exact-target canonical_bridge_readiness
or formal provider/calendar already covers target_asof
```

若不存在，DAPR3 必须写 blocker，不得通过旧 asof evidence、raw-only evidence 或隐式 provider pull 来补齐。

## 2. Non-Goals

DAPR3 不授权：

- provider pull / Yahoo / Scrapling / FinMind live request；
- provider publish；
- formal qlib provider/calendar/instruments/features mutation；
- accepted latest switch / qlib refresh；
- Model A scoring、ModelInferenceInput、ScoreJob、ModelSignalArtifact；
- readonly snapshot latest / Agent prompt latest publish；
- OpenAI；
- monitor、broker、order、OrderIntent、target_position、target_weight、quantity。

## 3. Baseline

从 DAPR0-DAPR2 继承：

- readiness target job: `daily_tw_stock_auto_update_20260717_20260717T144501Z`
- target_asof=`2026-07-17`
- raw_status=`READY`
- FinMind raw daily price source_max_date=`2026-07-17`，symbol_count=150，row_count=25800
- formal qlib provider calendar max=`2026-06-25`
- qlib accepted latest asof=`2026-07-08`
- PBPR2A-AC provider candidate target_asof=`2026-07-08`，不能证明 `2026-07-17`

## 4. Phase Plan

### DAPR3A - Exact-Target Local Evidence Inventory

搜索本地 durable readiness artifacts，包括：

- `provider_candidate_readiness.json`
- `provider_candidate_readiness_accepted.json`
- `canonical_bridge_readiness.json`

只接受 `candidate_asof` / `bridge_asof` / `target_asof` 等于 `2026-07-17` 的 artifact。

### DAPR3B - Contract Mapping And Candidate-Or-Blocker

把本地 evidence 对照 DAPR1/PBPR1 contract 判断：

- exact target asof；
- validator_status=pass；
- production_allowed=false；
- not_published_latest=true；
- forbidden actions false；
- raw-only 不可作为 bridge-ready。

### DAPR3C - Review And Closure

审查 DAPR3 是否正确输出 candidate 或 blocker，并确认 no-publish boundary。

## 5. Allowed Outputs

Allowed artifact root:

```text
data_tw/experiments/daily_accepted_production_readiness/dapr3_exact_target_provider_bridge_candidate_or_blocker/
```

Allowed docs:

```text
docs/tw_portfolio_decision_model/POLICY_DAPR3_EXACT_TARGET_PROVIDER_BRIDGE_CANDIDATE_OR_BLOCKER_WORK_CN.md
docs/tw_portfolio_decision_model/POLICY_DAPR3_EXACT_TARGET_PROVIDER_BRIDGE_CANDIDATE_OR_BLOCKER_EXECUTION_REPORT_CN.md
docs/tw_portfolio_decision_model/POLICY_DAPR3_EXACT_TARGET_PROVIDER_BRIDGE_CANDIDATE_OR_BLOCKER_REVIEW_CN.md
```

## 6. Closure Criteria

DAPR3 closes when one of these is true:

- exact-target provider/bridge readiness exists and is validated no-publish；或
- exact-target provider/bridge readiness is absent and blocker is machine-readable。

Current expected outcome is blocker unless a new exact-target provider/bridge artifact already exists locally.
