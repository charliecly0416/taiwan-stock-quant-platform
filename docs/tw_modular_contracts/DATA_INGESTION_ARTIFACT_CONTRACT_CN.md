# DataIngestionArtifact 合同

生成日期：2026-06-17

## 1. 目的

`DataIngestionArtifact` 记录数据从 DataSource 到标准化落盘的过程。它只负责生成可审计数据产物，不切换 provider/accepted latest，不直接喂给策略。

## 2. Artifact 结构

```text
data_tw/artifacts/data_ingestion/{source_name}/{run_id}/
manifest.json
normalized_path
schema.json
coverage_audit.csv
schema_audit.json
symbol_mapping_audit.csv
forbidden_action_audit.json
```

## 3. Required Fields

```text
artifact_type=data_ingestion
schema_version
run_id
source_name
provider
raw_path
normalized_path
symbol_mapping_version
asof_date
available_at
coverage_audit
schema_audit
no_provider_publish=true
no_accepted_latest_switch=true
```

## 4. 输出语义

`normalized_path` 只能表达标准化数据，不表达训练特征或策略信号。代码映射、缺失、停牌、退市和字段类型变化必须进入 audit。

## 5. Forbidden Fields

```text
future_return_*
forward_return_*
label_*
realized_pnl
target_position
target_weight
order_qty
execution_price
provider_publish_result
accepted_latest_result
```

## Forbidden Actions

- 不触发 provider publish / refresh。
- 不切换 provider accepted latest 或 qlib accepted latest。
- 不写 monitor config / scan / alerts。
- 不触发 broker、quick-trade 或 order。
- 不切默认模型或默认策略。

## 最小 Validator 要求

M1 validator 至少检查 required fields、manifest、schema/audit 文件、forbidden fields、forbidden actions 和只读边界。失败时必须返回明确 status，并支持 `--json`。
