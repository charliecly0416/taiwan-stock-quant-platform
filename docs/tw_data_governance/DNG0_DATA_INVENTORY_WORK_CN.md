# DNG0 数据现状盘点与数据地图工作文档

生成日期：2026-06-29

主线文档：

```text
docs/tw_data_governance/TW_DATA_NORMALIZATION_AND_LINEAGE_MAINLINE_CN.md
```

## 1. 目标

DNG0 只做只读盘点，建立当前数据层、latest pointer、temporary bridge、route dependency 的现状地图，为 DNG1 DataCatalog scanner 提供输入。

## 2. 范围

必须盘点：

```text
data_tw/artifacts/**
data_tw/experiments/**
data_tw/ops/daily_auto_update/**
qlib_pipeline/data_tw/**
configs/tw_product_artifact_registry.yaml
configs/tw_modular_registry.yaml
docs/tw_modular_contracts/**
```

重点识别：

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

## 3. 输出产物

执行者必须生成：

```text
data_tw/catalog/dng0_current_data_inventory.csv
data_tw/catalog/dng0_latest_pointer_inventory.csv
data_tw/catalog/dng0_route_dependency_sample.csv
docs/tw_data_governance/DNG0_DATA_INVENTORY_EXECUTION_REPORT_CN.md
```

CSV 至少包含：

`dng0_current_data_inventory.csv`

```text
layer,dataset_or_artifact,path,exists,file_count,dir_count,date_min,date_max,latest_pointer_type,status,status_reason,canonicality,recommended_next_action
```

`dng0_latest_pointer_inventory.csv`

```text
latest_concept,path,exists,asof,run_id,target_path,status,status_reason,downstream_surface
```

`dng0_route_dependency_sample.csv`

```text
route_id,dependency_name,current_source_path,required_layer,latest_concept,canonicality,known_blocker,recommended_contract
```

## 4. 禁止动作

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

## 5. 执行建议

允许使用只读 shell 扫描本地目录和 manifest/latest/job 文件。允许创建 DNG0 盘点产物和执行报告。

不得因为某个目录缺失就修复它；只记录状态和下一步建议。

## 6. 审查关注点

审查者必须判断：

1. 是否明确区分多种 latest。
2. 是否覆盖 artifacts、experiments、ops、qlib_pipeline、configs。
3. 是否指出哪些是 canonical，哪些是 experiment，哪些是 temporary bridge。
4. 是否解释 6/17、6/25、6/29 这类不一致可能来自哪一层。
5. 是否没有触发任何 forbidden action。
