# DNG5 RouteDataDependencyContract 执行报告

生成日期：2026-06-29T07:19:31+00:00

## 1. 本轮产物

- `docs/tw_data_governance/ROUTE_DATA_DEPENDENCY_CONTRACT_TEMPLATE_CN.md`
- `scripts/validate_tw_route_data_dependency.py`
- `data_tw/catalog/route_dependency_contract_examples/qlib_only_model_score_20260625.yaml`
- `data_tw/catalog/route_dependency_contract_examples/qlib_ltr_model_b_20260625.yaml`
- `data_tw/catalog/route_dependency_contract_examples/strategy_input_bundle_20260625.yaml`
- `data_tw/catalog/dng5_route_dependency_validation.json`

## 2. 模板字段

模板要求顶层字段：`contract_version`、`route_id`、`route_type`、`asof`、`owner`、`required_data_layers`、`required_date_range`、`required_universe`、`required_fields`、`required_latest_concepts`、`dependencies`、`optional_dependencies`、`allowed_fallbacks`、`forbidden_private_paths`、`forbidden_actions`、`expected_outputs`、`readiness_gate`。

每个 dependency 要求：`dependency_name`、`required`、`layer`、`dataset_id`、`artifact_path`、`latest_concept`、`required_fields`、`date_min`、`date_max`、`coverage_requirement`、`pit_required`、`available_at_required`、`fallback_allowed`、`fallback_policy`、`blocker_if_missing`。

## 3. Validator 检查逻辑

Validator 只读本地 YAML、DataCatalog、latest_status、readiness matrix 和既有 artifact 路径。检查内容包括：

- 必填顶层字段与 dependency 字段。
- `required_latest_concepts` 与 dependency `latest_concept` 是否存在于 `latest_status.latest_by_concept`。
- `artifact_path` 是否存在；required 且缺失时不得 `gate_pass=true`。
- dependency 路径是否命中 `forbidden_private_paths`。
- `forbidden_actions` 是否覆盖 DNG5 全部禁止动作，`expected_outputs` 是否包含 forbidden action。
- `readiness_gate.required_gate_checks` 的 JSON pointer 是否满足期望值。
- 输出区分 `validation_ok`、`gate_result` 和 `gate_pass`，防止 partial 被误解成 full ready。

## 4. 三个示例验证结果

| route_id | gate_result | gate_pass | 主要原因 |
| --- | --- | --- | --- |
| `qlib_ltr_model_b_20260625` | `BLOCK` | `False` | qlib_base_signal latest_concept model_signal_latest asof 2026-06-17 older than contract asof 2026-06-25; gate check dng3_model_b_ltr_ready expected True at /can_continue_to_model_b_ltr, actual False |
| `qlib_only_model_score_20260625` | `PARTIAL` | `False` | accepted_qlib_model_a_signal latest_concept qlib_accepted_latest asof 2026-06-17 older than contract asof 2026-06-25; price_coverage latest_concept price_store_latest asof 2026-06-17 older than contract asof 2026-06-25 |
| `strategy_input_bundle_20260625` | `PARTIAL` | `False` | dng4_strategy_input_bundle latest_concept model_signal_latest asof 2026-06-17 older than contract asof 2026-06-25; gate check dng4_strategy_bundle_status_partial_ready matched partial condition /strategy_input_bundle/status=PARTIAL_READY; no_replay_input_bundle_required latest_concept price_store_latest asof 2026-06-17 older than contract asof 2026-06-25 |

## 5. 防绕过规则

新路线必须在合同中声明 DataCatalog / latest_status / bundle 路径和 latest 概念。策略路线只能引用 StrategyInputBundle / ReplayInputBundle；模型路线必须声明 qlib provider view、ModelSignalArtifact、FeatureStore 或明确 qlib-only fallback。直接消费未声明的 `data_tw/experiments/**` 私有路径会被 `forbidden_private_paths` 阻断。

## 6. Forbidden Action Audit

本轮只生成合同、validator、示例和报告。未执行真实抓数、provider refresh/publish、qlib accepted latest switch、readonly/Agent publish、模型训练、模型推理、模型 score 生成、策略收益回放、ReplayResult/NAV、broker/order/quick-trade、target_position 或 target_weight。

## 7. DNG6 建议

建议进入 DNG6 daily auto catalog integration，但范围应限定为 catalog/readiness/dashboard 集成。不得把 DNG5 的合同 gate 通过解释成 publish_latest_gate、Model B LTR、replay execution 或生产就绪。
