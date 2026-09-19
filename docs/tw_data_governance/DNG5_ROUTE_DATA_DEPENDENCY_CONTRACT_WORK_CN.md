# DNG5 RouteDataDependencyContract 工作文档

生成日期：2026-06-29

## 1. 背景

DNG4 审查结论：

```text
PASS_WITH_CONDITIONS_GO_DNG5
```

条件：

- 只能进入 RouteDataDependencyContract / gate 设计；
- 不得进入 LTR、OrderIntent、ReplayResult、shadow 或 publish。

## 2. 目标

建立后续所有模型/策略/回放/日更路线的前置数据依赖合同模板和 validator。任何新路线开跑前必须声明需要哪些数据层、日期、字段、latest 概念、fallback，以及缺失时是否阻断。

## 3. 必须生成

```text
docs/tw_data_governance/ROUTE_DATA_DEPENDENCY_CONTRACT_TEMPLATE_CN.md
scripts/validate_tw_route_data_dependency.py
data_tw/catalog/route_dependency_contract_examples/
data_tw/catalog/route_dependency_contract_examples/qlib_only_model_score_20260625.yaml
data_tw/catalog/route_dependency_contract_examples/qlib_ltr_model_b_20260625.yaml
data_tw/catalog/route_dependency_contract_examples/strategy_input_bundle_20260625.yaml
data_tw/catalog/dng5_route_dependency_validation.json
docs/tw_data_governance/DNG5_ROUTE_DATA_DEPENDENCY_CONTRACT_EXECUTION_REPORT_CN.md
```

## 4. 模板最小字段

模板必须要求：

```text
contract_version
route_id
route_type
asof
owner
required_data_layers
required_date_range
required_universe
required_fields
required_latest_concepts
dependencies[]
optional_dependencies
allowed_fallbacks
forbidden_private_paths
forbidden_actions
expected_outputs
readiness_gate
```

每个 dependency 至少包含：

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

## 5. Validator 要求

`scripts/validate_tw_route_data_dependency.py` 必须支持：

```text
python scripts/validate_tw_route_data_dependency.py --contract <path> --catalog data_tw/catalog/data_catalog.json --latest-status data_tw/catalog/latest_status.json --json
```

检查：

- required fields；
- dependency fields；
- latest concepts 是否存在于 latest_status；
- artifact_path 是否存在，或缺失时是否有 blocker/fallback；
- forbidden_private_paths；
- forbidden_actions；
- 如果 dependency required 且 missing，不得 gate pass；
- 输出 JSON。

## 6. 示例合同

必须提供三个示例：

1. `qlib_only_model_score_20260625.yaml`
   - 允许 qlib-only；
   - 不要求 LTR Model B；
   - 应因 Model A signal stale 或 qlib provider view 状态明确给出 pass/partial/blocker。

2. `qlib_ltr_model_b_20260625.yaml`
   - 要求 orthogonal store；
   - 应因为 DNG3 `can_continue_to_model_b_ltr=false` 而 gate fail 或 partial fail；
   - 不得 fallback 为 full LTR ready。

3. `strategy_input_bundle_20260625.yaml`
   - 要求 StrategyInputBundle；
   - 允许 partial；
   - 明确不能进入 replay/performance。

## 7. 禁止动作

不得执行：

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

## 8. 执行报告

报告必须说明：

1. 模板字段。
2. validator 检查逻辑。
3. 三个示例合同的验证结果。
4. 如何防止新路线绕过 DataCatalog/Bundle。
5. forbidden action audit。
6. 是否建议进入 DNG6 daily auto catalog integration。
