# RouteDataDependencyContract 模板

生成日期：2026-06-29

## 1. 目的

`RouteDataDependencyContract` 是模型、策略、回放、日更路线开跑前的前置数据合同。它回答：

```text
路线要用哪些数据层
每层来自哪个 DataCatalog / latest_status / bundle
缺失时是否阻断
允许怎样 fallback
fallback 后还能声称什么，不能声称什么
```

没有通过本合同 validator 的路线，不得进入训练、推理、score 生成、策略收益回放、ReplayResult/NAV、readonly/Agent publish、accepted latest switch、broker/order/quick-trade 或 target_position/target_weight。

## 2. 顶层字段

```yaml
contract_version: v1.dng5.route_data_dependency_contract
route_id: example_route_20260625
route_type: model_score | model_ltr | strategy_input_bundle | replay_input_bundle | daily_auto | readonly_publish
asof: "2026-06-25"
owner: "route owner or reviewer"

required_data_layers:
  - canonical_price_store
  - provider_calendar_evidence
required_date_range:
  date_min: "2015-01-05"
  date_max: "2026-06-25"
required_universe: option_c_150
required_fields:
  - date
  - instrument
required_latest_concepts:
  - provider_raw_latest
  - qlib_accepted_latest

dependencies:
  - dependency_name: price_coverage
    required: true
    layer: canonical_price_store
    dataset_id: tw_equity_daily
    artifact_path: data_tw/canonical/price_store/tw_equity_daily/dng2_r_price_market_calendar_20260625/prices.csv
    latest_concept: price_store_latest
    required_fields:
      - price_date
      - instrument
      - close
    date_min: "2015-01-05"
    date_max: "2026-06-25"
    coverage_requirement:
      min_symbol_count: 150
      min_coverage_status: READY
    pit_required: true
    available_at_required: false
    fallback_allowed: false
    fallback_policy: "none"
    blocker_if_missing: true

optional_dependencies:
  - dependency_name: optional_explanation_feature
    reason_optional: "Only used for UI explanation, not for score generation."

allowed_fallbacks:
  - fallback_id: qlib_only_if_ltr_not_ready
    allowed_when:
      - orthogonal_feature_store can_continue_to_model_b_ltr is false
    impact_on_claim: "Route may claim qlib-only readiness only; it must not claim full LTR readiness."
    reviewer_approval_required: true

forbidden_private_paths:
  - data_tw/experiments/**
  - /tmp/**

forbidden_actions:
  - real_data_fetch
  - provider_refresh
  - provider_publish
  - qlib_accepted_latest_switch
  - readonly_latest_publish
  - agent_prompt_publish
  - model_training
  - model_inference
  - model_score_generation
  - strategy_replay
  - replay_result_nav_generation
  - broker_order_quick_trade
  - target_position_or_target_weight

expected_outputs:
  - validator_report_only

readiness_gate:
  mode: BLOCK_ON_REQUIRED_FAILURE
  allow_partial: false
  pass_claim: "Exact claim allowed when gate passes."
  partial_claim: "Exact claim allowed when gate is partial."
  blocked_claim: "Exact reason route must stop."
  required_gate_checks:
    - check_name: dng3_model_b_ltr_ready
      path: data_tw/catalog/readiness_matrix/2026-06-25/orthogonal_feature_store.json
      json_pointer: /can_continue_to_model_b_ltr
      expected: true
      blocker_if_mismatch: true
```

## 3. Dependency 字段要求

每个 `dependencies[]` 至少必须包含：

```text
dependency_name
required
layer
dataset_id
artifact_path
latest_concept
required_fields
date_min
date_max
coverage_requirement
pit_required
available_at_required
fallback_allowed
fallback_policy
blocker_if_missing
```

`required=true` 且 `artifact_path` 缺失时，只有两种合法结果：

```text
gate_result=BLOCK
gate_result=PARTIAL, 但必须 allow_partial=true 且 fallback_allowed=true，并明确 impact_on_claim
```

无论哪一种，都不得输出 `gate_pass=true`。

## 4. Latest 概念约束

`required_latest_concepts` 和每个 dependency 的 `latest_concept` 必须存在于：

```text
data_tw/catalog/latest_status.json#/latest_by_concept
```

validator 只确认 latest 概念存在和状态，不允许跨层推断。例如：

```text
provider_raw_latest 到 2026-06-25
!= qlib_accepted_latest 到 2026-06-25
!= model_signal_latest 到 2026-06-25
```

## 5. Fallback 声明

任何 fallback 都必须写清：

```text
fallback_id
allowed_when
impact_on_claim
reviewer_approval_required
```

示例：

```text
orthogonal_feature_store 缺失时，可 fallback qlib-only；
但只能声称 qlib-only model score route partial/pass，不得声称 full qlib+LTR ready。
```

## 6. Forbidden Action Audit

DNG5 合同和 validator 只允许读取本地合同、catalog、latest_status、readiness matrix 与既有 artifact 路径。禁止：

```text
真实抓数
provider refresh / publish
qlib accepted latest switch
readonly latest publish
Agent prompt latest publish
模型训练
模型推理
模型 score 生成
策略收益回放
ReplayResult/NAV 生成
broker/order/quick-trade
target_position / target_weight
```

合同若包含以上动作作为 `expected_outputs`，validator 必须阻断。

## 7. 推荐执行命令

```bash
python scripts/validate_tw_route_data_dependency.py \
  --contract data_tw/catalog/route_dependency_contract_examples/qlib_only_model_score_20260625.yaml \
  --catalog data_tw/catalog/data_catalog.json \
  --latest-status data_tw/catalog/latest_status.json \
  --json
```
