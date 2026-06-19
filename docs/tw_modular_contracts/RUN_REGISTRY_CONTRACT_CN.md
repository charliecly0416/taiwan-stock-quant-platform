# RunRegistry 合同

生成日期：2026-06-17

## 1. 目的

`RunRegistry` 是模块化日更、dry-run、analysis 和只读发布的运行账本。它记录输入输出、validator 状态和 latest pointer 决策，不承载业务逻辑。

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
keep_previous_latest_on_failure
previous_latest
proposed_latest
committed_latest
checksum
```

## 3. Pointer 语义

`latest_readonly_pointer.json` 只表示 API/frontend 可读的 readonly latest。no_new_data 不得刷新 latest pointer；failed run 的 committed latest 必须等于 previous latest。

## 4. Forbidden Fields

```text
provider_accepted_latest_switched=true
qlib_accepted_latest_switched=true
broker_order_id
quick_trade_id
target_position
target_weight
monitor_write_id
```

## Forbidden Actions

- 不触发 provider publish / refresh。
- 不切换 provider accepted latest 或 qlib accepted latest。
- 不写 monitor config / scan / alerts。
- 不触发 broker、quick-trade 或 order。
- 不切默认模型或默认策略。

## 最小 Validator 要求

M1 validator 至少检查 required fields、manifest、schema/audit 文件、forbidden fields、forbidden actions 和只读边界。失败时必须返回明确 status，并支持 `--json`。
