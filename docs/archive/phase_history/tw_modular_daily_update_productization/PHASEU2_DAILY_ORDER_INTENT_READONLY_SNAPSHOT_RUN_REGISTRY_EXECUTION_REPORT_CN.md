# Phase U2 Daily OrderIntent / ReadonlySnapshot / RunRegistry 执行报告

生成日期：2026-06-17

## 1. 执行范围

本阶段按 `PHASEU1_REVIEW_AND_PHASEU2_WORK_CN.md` 执行 U2：从 U1 daily ModelSignalArtifact 生成 daily OrderIntentArtifact，再生成 daily ReadonlyStrategySnapshot、daily RunRegistry 和 U2 专用 readonly latest pointer。

本轮没有训练新模型，没有调参，没有替换冻结模型权重，没有触发 provider refresh / publish，没有切 provider accepted latest 或 qlib accepted latest，没有写 monitor config / scan / alerts，没有连接 broker / quick-trade / orders，没有修改 Agent prompt / tool / action，没有把 U1/U2 staging 产物接入前端默认展示。

## 2. 新增脚本

| 脚本 | 作用 |
| --- | --- |
| `scripts/build_tw_daily_order_intent_artifact.py` | 从 U1 ModelSignalArtifact 生成 daily readonly OrderIntentArtifact |
| `scripts/validate_tw_daily_order_intent_artifact.py` | 校验 daily OrderIntentArtifact 的 readonly 标志、禁止字段、source signal、no broker/order 边界 |
| `scripts/publish_tw_daily_readonly_snapshot.py` | 从 daily OrderIntentArtifact 生成 daily readonly snapshot，并在 validator-gated success 时更新 U2 专用 latest pointer |
| `scripts/validate_tw_daily_readonly_snapshot.py` | 校验 snapshot 的 readonly flags、source order intent、checksum 与安全语义 |
| `scripts/validate_tw_daily_run_registry.py` | 校验 RunRegistry / latest pointer 的 success、noop、validator_failed、module_failed 四类行为 |

## 3. 产物路径

### 3.1 Success chain

```text
data_tw/artifacts/daily_order_intents/e4_frozen_qlib_2023_2025_ltr/top50_exit_one_worst_sell/u2_success_order_intent_demo/manifest.json
data_tw/artifacts/daily_readonly_snapshots/u2_success_readonly_snapshot_demo/manifest.json
data_tw/artifacts/daily_run_registry/u2_success_run_registry_demo/manifest.json
data_tw/artifacts/daily_readonly_latest/latest.json
```

关键结果：

| Artifact | row_count | 状态 |
| --- | ---: | --- |
| OrderIntentArtifact | 5 | pass |
| ReadonlySnapshot | 5 intents | pass |
| RunRegistry | success | pass |
| U2 latest pointer | 更新到 U2 success snapshot | pass |

### 3.2 No-new-data chain

```text
data_tw/artifacts/daily_order_intents/e4_frozen_qlib_2023_2025_ltr/top50_exit_one_worst_sell/u2_no_new_data_order_intent_demo/manifest.json
data_tw/artifacts/daily_readonly_snapshots/u2_no_new_data_readonly_snapshot_demo/manifest.json
data_tw/artifacts/daily_run_registry/u2_no_new_data_run_registry_demo/manifest.json
```

关键结果：

| Artifact | row_count | 状态 |
| --- | ---: | --- |
| OrderIntentArtifact | 0 | noop |
| ReadonlySnapshot | 0 intents | noop |
| RunRegistry | no_new_data | 保留 previous latest |

### 3.3 Validator failed / module failed registry chain

```text
data_tw/artifacts/daily_run_registry/u2_validator_failed_run_registry_demo/manifest.json
data_tw/artifacts/daily_run_registry/u2_module_failed_run_registry_demo/manifest.json
```

两者都保持 `committed_latest == previous_latest` 语义，不得提前提交 proposed latest。

## 4. Golden samples

Golden root：

```text
data_tw/golden_samples/modular_daily_update/u2/
```

覆盖样本：

| 类型 | 样本 |
| --- | --- |
| pass | `order_intent/pass_success_updates_readonly_latest` |
| fail | `order_intent/fail_order_intent_contains_broker_order` |
| fail | `order_intent/fail_order_intent_contains_target_position` |
| pass | `readonly_snapshot/pass_success_updates_readonly_latest` |
| fail | `readonly_snapshot/fail_snapshot_missing_readonly_flags` |
| pass | `run_registry/pass_success_updates_readonly_latest` |
| pass | `run_registry/pass_no_new_data_preserves_previous_latest` |
| pass | `run_registry/pass_validator_failed_preserves_previous_latest` |
| pass | `run_registry/pass_module_failed_preserves_previous_latest` |
| fail | `run_registry/fail_latest_pointer_updates_before_validators_pass` |
| fail | `run_registry/fail_latest_pointer_is_provider_accepted_latest` |

## 5. 验证结果

语法检查：

```text
python -m py_compile scripts/build_tw_daily_order_intent_artifact.py scripts/validate_tw_daily_order_intent_artifact.py scripts/publish_tw_daily_readonly_snapshot.py scripts/validate_tw_daily_readonly_snapshot.py scripts/validate_tw_daily_run_registry.py
```

结果：通过。

Golden validator：

```text
python scripts/validate_tw_daily_order_intent_artifact.py --run-golden --json
python scripts/validate_tw_daily_readonly_snapshot.py --run-golden --json
python scripts/validate_tw_daily_run_registry.py --run-golden --json
```

结果：全部 `ok=true`，`status=passed`。

Direct artifact validation：

```text
python scripts/validate_tw_daily_order_intent_artifact.py --artifact-path data_tw/artifacts/daily_order_intents/e4_frozen_qlib_2023_2025_ltr/top50_exit_one_worst_sell/u2_success_order_intent_demo --json
python scripts/validate_tw_daily_readonly_snapshot.py --artifact-path data_tw/artifacts/daily_readonly_snapshots/u2_success_readonly_snapshot_demo --json
python scripts/validate_tw_daily_run_registry.py --artifact-path data_tw/artifacts/daily_run_registry/u2_success_run_registry_demo --json
```

结果：全部 `ok=true`，`status=passed`。

汇总文件：

```text
data_tw/experiments/modular_daily_update/u2_validation_summary.json
```

汇总结果：

```text
ok=true
status=passed
```

## 6. U2 合同行为

### 6.1 OrderIntent

保持：

```text
readonly_only=true
not_order=true
not_target_position=true
not_investment_advice=true
production_trade_enabled=false
no_broker_order=true
strategy_rule=top50_exit_one_worst_sell
model_id=e4_frozen_qlib_2023_2025_ltr
```

禁止字段与语义：

```text
execution_price
cash
equity
broker_order_id
target_position
target_weight
order_qty
order_id
quick_trade
```

### 6.2 ReadonlySnapshot

保持：

```text
readonly_only=true
not_order=true
not_target_position=true
not_investment_advice=true
production_trade_enabled=false
source_order_intent_artifact
source_model_signal_artifact
source_strategy_rule
audit_status
checksum
```

Snapshot 仅用于研究展示，不含交易建议、自动买卖或收益承诺。

### 6.3 RunRegistry / latest pointer

覆盖四类状态：

```text
success_validators_passed_updates_readonly_latest
no_new_data_noop_preserves_previous_latest
validator_failed_preserves_previous_latest
module_failed_preserves_previous_latest
```

U2 latest pointer 保持：

```text
previous_latest
proposed_latest
committed_latest
checksum
run_id
status
updated_only_after_all_validators_passed=true
not_provider_accepted_latest=true
not_qlib_accepted_latest=true
not_trade_target_latest=true
```

## 7. 禁止事项自检

| 禁止项 | 结果 |
| --- | --- |
| 训练/调参/替换模型权重 | 未触发 |
| provider refresh / publish | 未触发 |
| provider accepted latest / qlib accepted latest | 未触发 |
| monitor config / scan / alerts | 未触发 |
| broker / quick-trade / orders | 未触发 |
| Agent prompt / tool / action 修改 | 未触发 |
| 前端默认展示接入 | 未触发 |
| 正式收益结论 replay | 未触发 |

## 8. 下一阶段 U3 前置条件

U2 已完成 validator-gated readonly chain。进入 U3 前建议审查者确认：

1. U2 latest pointer 仅更新 U2 专用 readonly latest 路径，不等于 provider accepted latest 或 qlib accepted latest。
2. U2 staging 产物未接入前端默认展示。
3. U3 若做自动脚本接入与前端/API 验收，必须重新做 network / console / route 只读审计。
4. U3 不能引入真实交易、monitor 写入或 Agent 扩权。
