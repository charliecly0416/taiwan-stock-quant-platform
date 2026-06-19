# PriceStore 合同

生成日期：2026-06-17

## 1. 目的

`PriceStore` 是回放执行、特征计算和只读展示可引用的标准价格数据层。它不代表 provider latest，也不负责发布或切换 accepted latest。

## 2. Artifact 结构

```text
data_tw/artifacts/price_store/{price_source}/{run_id}/
manifest.json
prices.parquet 或 prices.csv
schema.json
coverage_audit.csv
adjustment_audit.json
execution_availability_audit.csv
```

## 3. Required Fields

```text
price_date
instrument
open
close
adj_factor
tradable_flag
halt_flag
next_day_execution_availability
price_source
adjustment_policy
coverage_audit
```

Manifest 必须声明 `artifact_type=price_store`、`source_data_artifact`、日期范围、标的数量、复权政策、execution availability audit、`no_provider_publish=true` 和 `no_accepted_latest_switch=true`。

## 4. Forbidden Fields

```text
future_return_*
forward_return_*
label_*
strategy_action
target_position
target_weight
order_qty
broker_order_id
portfolio_equity
```

## Forbidden Actions

- 不触发 provider publish / refresh。
- 不切换 provider accepted latest 或 qlib accepted latest。
- 不写 monitor config / scan / alerts。
- 不触发 broker、quick-trade 或 order。
- 不切默认模型或默认策略。

## 最小 Validator 要求

M1 validator 至少检查 required fields、manifest、schema/audit 文件、forbidden fields、forbidden actions 和只读边界。失败时必须返回明确 status，并支持 `--json`。
