# DataSource 合同

生成日期：2026-06-17

## 1. 目的

`DataSource` 描述台股研究链路可接入的数据来源、可见性、覆盖率和安全边界。它只定义数据来源合同，不执行抓取、不 publish provider、不切 accepted latest。

## 2. 标准输入

```text
source_name
provider
source_endpoint_or_file
symbol_mapping_version
asof_date
available_at
license_or_access_note
```

## 3. 标准输出 / Manifest

```text
artifact_type=data_source
schema_version
source_name
provider
raw_path
symbol_mapping_version
asof_date
available_at
coverage_audit
schema_audit
no_provider_publish=true
no_accepted_latest_switch=true
```

## 4. Forbidden Fields

```text
future_return_*
forward_return_*
label_*
target_position
target_weight
order_qty
execution_price
broker_order_id
provider_publish_status=published
accepted_latest_status=switched
```

## Forbidden Actions

- 不触发 provider publish / refresh。
- 不切换 provider accepted latest 或 qlib accepted latest。
- 不写 monitor config / scan / alerts。
- 不触发 broker、quick-trade 或 order。
- 不切默认模型或默认策略。

## 最小 Validator 要求

M1 validator 至少检查 required fields、manifest、schema/audit 文件、forbidden fields、forbidden actions 和只读边界。失败时必须返回明确 status，并支持 `--json`。
