# FeatureArtifact 合同

生成日期：2026-06-17

## 1. 目的

`FeatureArtifact` 是模型训练、推理或 analysis 使用的标准特征产物。它必须保留 PIT 可见性，禁止未来收益、训练标签、真实成交或未来持仓污染。

## 2. Artifact 结构

```text
data_tw/artifacts/features/{feature_set_name}/{run_id}/
manifest.json
features.parquet 或 features.csv
schema.json
source_data_audit.json
pit_audit.csv
forbidden_future_field_audit.json
coverage_audit.csv
```

## 3. Required Fields

```text
feature_date
instrument
feature_name
feature_value
source_data_artifact
lookback_window
signal_asof
available_at
pit_policy
forbidden_future_field_audit
```

Manifest 必须声明 `artifact_type=feature_artifact`、`schema_version`、`feature_set_name`、`run_id`、`input_artifacts`、`output_path`、`feature_date_range`、`pit_policy` 和 coverage audit。

## 4. Forbidden Fields

```text
future_return_*
future_excess_return_*
forward_return_*
label_*
relevance_*
realized_pnl
execution_price
execution_date
target_position
target_weight
broker_order_id
```

## 5. 特殊边界

策略不得直接读取 FeatureArtifact。若策略需要消费新特征，必须经 ModelSignal extension 和 strategy dependency 显式声明。

## Forbidden Actions

- 不触发 provider publish / refresh。
- 不切换 provider accepted latest 或 qlib accepted latest。
- 不写 monitor config / scan / alerts。
- 不触发 broker、quick-trade 或 order。
- 不切默认模型或默认策略。

## 最小 Validator 要求

M1 validator 至少检查 required fields、manifest、schema/audit 文件、forbidden fields、forbidden actions 和只读边界。失败时必须返回明确 status，并支持 `--json`。
