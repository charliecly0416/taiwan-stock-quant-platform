# DNG1 DataCatalog Schema 与只读 Scanner 工作文档

生成日期：2026-06-29

## 1. 背景

DNG0 已通过审查，结论为：

```text
PASS_WITH_CONDITIONS_GO_DNG1
```

DNG1 必须承接 DNG0 条件：scanner 必须保守，不能把 bridge、experiment、缺 manifest/schema/coverage/lineage 的历史路径伪装成 canonical READY。

主线文档：

```text
docs/tw_data_governance/TW_DATA_NORMALIZATION_AND_LINEAGE_MAINLINE_CN.md
```

输入：

```text
data_tw/catalog/dng0_current_data_inventory.csv
data_tw/catalog/dng0_latest_pointer_inventory.csv
data_tw/catalog/dng0_route_dependency_sample.csv
docs/tw_data_governance/DNG0_DATA_INVENTORY_EXECUTION_REPORT_CN.md
docs/tw_data_governance/DNG0_DATA_INVENTORY_REVIEW_CN.md
```

## 2. 目标

实现只读 DataCatalog scanner 和 validator，将当前数据现状整理为机器可读 catalog。

## 3. 输出产物

必须生成：

```text
scripts/build_tw_data_catalog.py
scripts/validate_tw_data_catalog.py
data_tw/catalog/data_catalog.json
data_tw/catalog/latest_status.json
data_tw/catalog/data_catalog_summary.csv
data_tw/catalog/data_catalog_validation.json
docs/tw_data_governance/DNG1_DATA_CATALOG_EXECUTION_REPORT_CN.md
```

## 4. DataCatalog 最小 schema

`data_catalog.json` 必须包含：

```text
catalog_version
generated_at
source_inventory
entries[]
summary
forbidden_action_audit
```

每个 entry 至少包含：

```text
dataset_id
layer
asof
date_min
date_max
symbol_count
row_count
path
manifest_path
schema_path
coverage_audit_path
lineage_path
validator_report_path
status
status_reason
source_provider
source_run_id
checksum
pit_policy
available_at_policy
canonicality
latest_concept
forbidden_action_flags
```

status 枚举必须只使用：

```text
READY
PARTIAL_READY
MISSING
STALE
BLOCKED_PROVIDER
BLOCKED_SCHEMA
BLOCKED_PIT
BLOCKED_COVERAGE
BLOCKED_VALIDATOR
RESEARCH_ONLY
LEGACY_UNCATALOGED
TEMPORARY_BRIDGE
```

`READY` 只能用于：

- 路径存在；
- manifest/schema/coverage/lineage 或等价 evidence 足够；
- canonicality 不是 temporary bridge；
- forbidden flags 全部安全；
- 不需要通过推断伪造 asof/date range。

否则必须降级为 `PARTIAL_READY`、`RESEARCH_ONLY`、`LEGACY_UNCATALOGED` 或 `TEMPORARY_BRIDGE`。

## 5. latest_status 最小 schema

`latest_status.json` 必须包含：

```text
schema_version
generated_at
latest_by_concept
known_mismatch
recommended_next_actions
forbidden_action_audit
```

必须覆盖：

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
temporary_research_bridge_latest
```

如果某概念缺失，必须写 `status=MISSING`，不得省略。

## 6. Validator 要求

`scripts/validate_tw_data_catalog.py` 必须支持：

```text
python scripts/validate_tw_data_catalog.py --catalog data_tw/catalog/data_catalog.json --latest-status data_tw/catalog/latest_status.json --json
```

检查：

- required top-level fields；
- entry required fields；
- status 枚举合法；
- 路径存在性；
- latest concepts 覆盖完整；
- forbidden action flags 未越权；
- `READY` 不得用于 `TEMPORARY_BRIDGE` 或 `LEGACY_UNCATALOGED`；
- 输出 JSON validator report。

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
策略回放
broker/order/quick-trade
target_position / target_weight
```

## 8. 执行报告

执行报告必须包含：

1. 读取了哪些输入。
2. scanner 设计。
3. catalog entries 数量和 status 分布。
4. latest_status 关键不一致。
5. validator 输出。
6. DNG0 条件如何满足。
7. forbidden action audit。
8. 是否建议进入 DNG2。
