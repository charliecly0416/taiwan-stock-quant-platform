# DNG0 数据现状盘点审查工作文档

生成日期：2026-06-29

## 1. 审查输入

主线：

```text
docs/tw_data_governance/TW_DATA_NORMALIZATION_AND_LINEAGE_MAINLINE_CN.md
```

工作文档：

```text
docs/tw_data_governance/DNG0_DATA_INVENTORY_WORK_CN.md
```

执行报告：

```text
docs/tw_data_governance/DNG0_DATA_INVENTORY_EXECUTION_REPORT_CN.md
```

执行产物：

```text
data_tw/catalog/dng0_current_data_inventory.csv
data_tw/catalog/dng0_latest_pointer_inventory.csv
data_tw/catalog/dng0_route_dependency_sample.csv
```

## 2. 审查目标

判断 DNG0 是否足够支撑进入 DNG1 DataCatalog scanner。审查者不得执行抓数、修复、推理、回放或 publish。

## 3. 必查项

1. DNG0 是否覆盖 `data_tw/artifacts/**`、`data_tw/experiments/**`、`data_tw/ops/daily_auto_update/**`、`qlib_pipeline/data_tw/**`、configs。
2. 是否明确区分：

```text
provider_raw_latest
normalized_latest
price_store_latest
feature_store_latest
qlib_accepted_latest
model_signal_latest
readonly_bridge_latest
readonly_snapshot_latest
agent_prompt_latest
temporary_research_bridge
```

3. 是否把 canonical / experiment / temporary bridge 区分清楚。
4. 是否有足够字段让 DNG1 设计 scanner schema。
5. 是否记录已知 blocker 和 recommended_next_action。
6. 是否没有触发 forbidden action。

## 4. Verdict

审查结论只能是：

```text
PASS_GO_DNG1
PASS_WITH_CONDITIONS_GO_DNG1
FAIL_NEEDS_DNG0_REPAIR
STOP_COORDINATOR_DECISION_REQUIRED
```

## 5. 输出

审查者必须写：

```text
docs/tw_data_governance/DNG0_DATA_INVENTORY_REVIEW_CN.md
```

并在末尾给出下一步建议：

- 如果 PASS 或 PASS_WITH_CONDITIONS：给出 DNG1 DataCatalog scanner 的重点要求。
- 如果 FAIL：给出 DNG0 repair 的具体缺口。
- 如果 STOP：说明需要统筹/用户决策的问题。
