# DailyOrchestrator 合同

生成日期：2026-06-17

## 1. 目的

`DailyOrchestrator` 定义台股日更模块化编排边界。它只串接标准模块、收集 validator 结果、写 RunRegistry，并在全部校验通过后才允许更新 readonly latest pointer。

## 2. Required Fields

```text
run_id
run_asof
schedule_interval
trigger_reason
data_freshness_check_result
input_artifacts
output_artifacts
validation_results
latest_pointer_policy
failure_mode
rollback_policy
keep_previous_latest_on_failure=true
```

## 3. 模块调用顺序

```text
FreshnessCheck
  -> DataIngestion
  -> FeatureArtifact
  -> ModelSignalArtifact
  -> StrategyDecision / OrderIntentArtifact
  -> ReadonlySnapshot
  -> optional ReplayWindowArtifact registration
  -> validators
  -> RunRegistry
  -> readonly latest pointer decision
```

## 4. Pointer 政策

readonly latest pointer 不等于 provider accepted latest，也不等于 qlib accepted latest。no_new_data 不得刷新 latest pointer；validator_failed 必须保留 previous latest。

## 5. Forbidden Fields

```text
accepted_latest_status=switched
provider_publish_status=published
broker_order_id
order_qty
target_position
target_weight
monitor_scan_id
```

## Forbidden Actions

- 不触发 provider publish / refresh。
- 不切换 provider accepted latest 或 qlib accepted latest。
- 不写 monitor config / scan / alerts。
- 不触发 broker、quick-trade 或 order。
- 不切默认模型或默认策略。

## 最小 Validator 要求

M1 validator 至少检查 required fields、manifest、schema/audit 文件、forbidden fields、forbidden actions 和只读边界。失败时必须返回明确 status，并支持 `--json`。
