# AutoUpdateOrchestrator 合同

生成日期：2026-06-17

## 1. 目的

`AutoUpdateOrchestrator` 约束既有“两小时自动更新”能力。自动脚本保留调度、状态、重试和失败关闭职责，但业务步骤必须模块化，不得继续扩张为大脚本。

## 2. Required Fields

```text
poll_interval_hours
fresh_data_detected
no_new_data_noop
module_call_sequence
module_result_status
retry_policy
failure_closes_without_publish
previous_latest_preserved
readonly_latest_update_only_after_all_validators_pass=true
does_not_switch_provider_accepted_latest=true
does_not_place_orders=true
```

## 3. 标准状态

```text
no_new_data_noop
fresh_data_success_validators_passed
fresh_data_validator_failed_previous_latest_preserved
module_failed_previous_latest_preserved
```

## 4. Forbidden Fields

```text
provider_publish_status=published
accepted_latest_status=switched
monitor_scan_id
broker_order_id
target_position
target_weight
order_qty
```

## Forbidden Actions

- 不触发 provider publish / refresh。
- 不切换 provider accepted latest 或 qlib accepted latest。
- 不写 monitor config / scan / alerts。
- 不触发 broker、quick-trade 或 order。
- 不切默认模型或默认策略。

## 最小 Validator 要求

M1 validator 至少检查 required fields、manifest、schema/audit 文件、forbidden fields、forbidden actions 和只读边界。失败时必须返回明确 status，并支持 `--json`。
