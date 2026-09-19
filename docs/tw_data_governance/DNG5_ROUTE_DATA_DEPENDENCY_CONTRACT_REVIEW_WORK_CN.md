# DNG5 RouteDataDependencyContract 审查工作文档

生成日期：2026-06-29

## 1. 审查输入

```text
docs/tw_data_governance/TW_DATA_NORMALIZATION_AND_LINEAGE_MAINLINE_CN.md
docs/tw_data_governance/DNG5_ROUTE_DATA_DEPENDENCY_CONTRACT_WORK_CN.md
docs/tw_data_governance/DNG5_ROUTE_DATA_DEPENDENCY_CONTRACT_EXECUTION_REPORT_CN.md
docs/tw_data_governance/ROUTE_DATA_DEPENDENCY_CONTRACT_TEMPLATE_CN.md
scripts/validate_tw_route_data_dependency.py
data_tw/catalog/route_dependency_contract_examples/*.yaml
data_tw/catalog/dng5_route_dependency_validation.json
```

## 2. 审查目标

判断 DNG5 是否建立了可执行的路线数据依赖合同和 validator，是否可以进入 DNG6 daily auto catalog integration。

## 3. 必查项

1. 模板字段是否覆盖数据层、日期、字段、latest、fallback、forbidden paths/actions。
2. validator 是否能结合 DataCatalog/latest_status 判断 required dependency。
3. qlib-only 示例是否语义合理。
4. qlib+LTR 示例是否因 Model B blocker 不误通过。
5. strategy input bundle 示例是否明确 partial，不能进入 replay/performance。
6. 是否未触发 forbidden action。

## 4. 建议命令

```text
python -m py_compile scripts/validate_tw_route_data_dependency.py
python scripts/validate_tw_route_data_dependency.py --contract data_tw/catalog/route_dependency_contract_examples/qlib_only_model_score_20260625.yaml --catalog data_tw/catalog/data_catalog.json --latest-status data_tw/catalog/latest_status.json --json
python scripts/validate_tw_route_data_dependency.py --contract data_tw/catalog/route_dependency_contract_examples/qlib_ltr_model_b_20260625.yaml --catalog data_tw/catalog/data_catalog.json --latest-status data_tw/catalog/latest_status.json --json
python scripts/validate_tw_route_data_dependency.py --contract data_tw/catalog/route_dependency_contract_examples/strategy_input_bundle_20260625.yaml --catalog data_tw/catalog/data_catalog.json --latest-status data_tw/catalog/latest_status.json --json
```

## 5. Verdict

审查结论只能是：

```text
PASS_GO_DNG6
PASS_WITH_CONDITIONS_GO_DNG6
FAIL_NEEDS_DNG5_REPAIR
STOP_COORDINATOR_DECISION_REQUIRED
```

## 6. 输出

审查者必须写：

```text
docs/tw_data_governance/DNG5_ROUTE_DATA_DEPENDENCY_CONTRACT_REVIEW_CN.md
```
