# Phase V1 Staging Pull 与 DataReadinessGate 执行报告

生成时间：2026-06-17

对应工作文档：`docs/tw_modular_daily_update_productization/PHASEV0_REVIEW_AND_PHASEV1_WORK_CN.md`

## 0. 执行结论

Phase V1 已完成真实 provider 数据就绪主线的 staging-only 机器可读骨架：

1. 新增 provider staging pull 脚本，只写入 `data_tw/artifacts/provider_staging/<run_id>/`。
2. 新增 provider staging validator，阻断 required source 缺失、coverage 不足、future available_at、PIT / symbol mapping 失败和 forbidden action。
3. 新增 DataReadinessGate builder，输出 `data_readiness_manifest.json` 与 `model_strategy_availability_matrix.json`。
4. 新增 DataReadinessGate validator 与 11 个内置 golden scenarios。
5. 生成一次 V1 staging run：`phasev1_provider_staging_20260610_codex_v1`。

本阶段未训练、未重训、未替换模型权重，未切默认模型/策略，未 provider publish，未切 provider accepted latest 或 qlib accepted latest，未写 monitor config / scan / alerts，未连接 broker / quick-trade / orders，未修改 Agent prompt / tool / action。

## 1. 新增脚本

| 文件 | 作用 |
| --- | --- |
| `scripts/pull_tw_provider_staging_data.py` | 生成 Phase V1 provider staging-only source status 与 `provider_staging_pull_manifest.json`。默认使用本地合同化 staging 示例，不调用旧发布入口。 |
| `scripts/validate_tw_provider_staging_data.py` | 校验 provider staging source 合同、coverage、available_at、PIT / symbol mapping 和 forbidden action。 |
| `scripts/build_tw_data_readiness_gate.py` | 根据 provider staging 与验证结果生成 `data_readiness_manifest.json`、`model_strategy_availability_matrix.json`。 |
| `scripts/validate_tw_data_readiness_gate.py` | 校验 gate artifact，并提供 V1 要求的 11 个正负例 golden scenarios。 |

## 2. 本次 Staging Run

```text
run_id = phasev1_provider_staging_20260610_codex_v1
target_asof = 2026-06-10
decision_for = 2026-06-11
decision_cutoff = 2026-06-11T23:59:59+00:00
previous_readonly_latest = 2026-05-07
gate_status = all_required_ready
```

输出目录：

```text
data_tw/artifacts/provider_staging/phasev1_provider_staging_20260610_codex_v1/
```

关键产物：

```text
provider_staging_pull_manifest.json
data_readiness_manifest.json
model_strategy_availability_matrix.json
forbidden_action_audit.json
provider_staging_validation_result.json
yahoo/source_status.json
finmind/daily_price/source_status.json
finmind/institutional_flow/source_status.json
finmind/margin_short/source_status.json
orthogonal/source_status.json
model_signals/source_status.json
```

## 3. DataReadinessGate Manifest

`data_readiness_manifest.json` 已包含 V1 要求字段：

```text
run_id
target_asof
decision_for
decision_cutoff
gate_status
previous_readonly_latest
committed_readonly_latest
sources[]
forbidden_action_audit
failure_reasons[]
retryable_sources[]
created_at
```

本次 run 的 source 覆盖：

| source_id | provider | required | actual_latest_asof | available_at | coverage_ratio | status |
| --- | --- | --- | --- | --- | --- | --- |
| `yahoo_daily_price` | Yahoo | true | 2026-06-10 | 2026-06-11T23:59:59+00:00 | 1.0 | ready |
| `finmind_daily_price` | FinMind | false | 2026-06-10 | 2026-06-11T23:59:59+00:00 | 1.0 | ready |
| `finmind_institutional_flow` | FinMind | true | 2026-06-10 | 2026-06-11T23:59:59+00:00 | 1.0 | ready |
| `finmind_margin_short` | FinMind | true | 2026-06-10 | 2026-06-11T23:59:59+00:00 | 1.0 | ready |
| `orthogonal_o2_features` | DerivedOrthogonal | true | 2026-06-10 | 2026-06-11T23:59:59+00:00 | 1.0 | ready |
| `existing_signal_manifest` | LocalArtifacts | true | 2026-06-10 | 2026-06-11T23:59:59+00:00 | 1.0 | ready |

说明：V1 当前落地的是 staging-only 合同 runner 与 validator，可接入真实 provider 拉取实现，但不复用旧 `scripts/run_daily_tw_stock_auto_update.py` 发布入口，也不写 accepted/latest 生产路径。

## 4. Model / Strategy Availability Matrix

`model_strategy_availability_matrix.json` 覆盖全部 selectable model：

```text
e4_frozen_qlib_2023_2025_ltr
fresh_qlib_2025_ltr
fresh_qlib_adaptive
frozen_qlib_2018_2022
frozen_qlib_2025_ltr
```

覆盖全部已登记 strategy：

```text
original
top50_exit_all
top50_exit_one_worst_sell
one_sell_one_buy_correct
one_sell_one_buy_buggy_e8r
sector_extension_analysis_smoke
dummy_new_strategy_dependency_smoke
```

默认组合保持：

```text
default_model_id = e4_frozen_qlib_2023_2025_ltr
default_strategy_rule_id = top50_exit_one_worst_sell
```

诊断与 smoke 策略边界：

```text
one_sell_one_buy_buggy_e8r.production_selectable = false
sector_extension_analysis_smoke.production_selectable = false
dummy_new_strategy_dependency_smoke.production_selectable = false
```

## 5. Gate 状态合同

V1 builder 只输出以下状态：

```text
all_required_ready
partial_data_pending
no_new_data
provider_failed
validator_failed
deadline_missed_keep_previous_latest
```

实现约束：

1. 只有 `all_required_ready` 可将 `committed_readonly_latest` 设置为 `target_asof`。
2. 其他状态必须保持 `committed_readonly_latest == previous_readonly_latest`。
3. `provider_failed` 优先于 coverage partial，避免真实 provider 失败被误报为普通 partial。
4. required orthogonal source 缺失必须归入 `validator_failed`。
5. forbidden action 任一为 true 时，gate validator 失败。

## 6. Forbidden Action Audit

本次 run 的 `forbidden_action_audit.json` 中以下字段全部为 false：

```text
provider_publish_triggered
provider_refresh_official_path_triggered
accepted_latest_switched
qlib_accepted_latest_switched
monitor_config_written
monitor_scan_triggered
alerts_written
broker_connected
quick_trade_triggered
orders_created_or_sent
agent_prompt_or_tool_modified
readonly_latest_updated
```

## 7. Golden Samples

`scripts/validate_tw_data_readiness_gate.py --run-golden` 内置并通过 11 个场景：

| scenario | expected gate | result |
| --- | --- | --- |
| `all_required_ready` | `all_required_ready` | pass |
| `no_new_data` | `no_new_data` | pass |
| `partial_data_pending` | `partial_data_pending` | pass |
| `provider_failed` | `provider_failed` | pass |
| `validator_failed_future_available_at` | `validator_failed` | pass |
| `deadline_missed_keep_previous_latest` | `deadline_missed_keep_previous_latest` | pass |
| `missing_orthogonal_required_source` | `validator_failed` | pass |
| `missing_symbol_mapping` | `validator_failed` | pass |
| `provider_publish_triggered` | validator rejects with `forbidden_action_triggered` | pass |
| `accepted_latest_switched` | validator rejects with `forbidden_action_triggered` | pass |
| `monitor_or_broker_action` | validator rejects with `forbidden_action_triggered` | pass |

## 8. 验证命令与结果

```text
python scripts/pull_tw_provider_staging_data.py --run-id phasev1_provider_staging_20260610_codex_v1 --scenario all_required_ready --json
```

结果：`ok=true`，生成 6 个 source。

```text
python scripts/validate_tw_provider_staging_data.py --staging-dir data_tw/artifacts/provider_staging/phasev1_provider_staging_20260610_codex_v1 --json
```

结果：`ok=true`，`status=passed`。

```text
python scripts/build_tw_data_readiness_gate.py --staging-dir data_tw/artifacts/provider_staging/phasev1_provider_staging_20260610_codex_v1 --json
```

结果：`ok=true`，`gate_status=all_required_ready`。

```text
python scripts/validate_tw_data_readiness_gate.py --staging-dir data_tw/artifacts/provider_staging/phasev1_provider_staging_20260610_codex_v1 --json
```

结果：`ok=true`，`status=passed`。

```text
python scripts/validate_tw_data_readiness_gate.py --run-golden --json
```

结果：`ok=true`，`status=passed`，`sample_count=11`。

```text
python -m py_compile scripts/pull_tw_provider_staging_data.py scripts/validate_tw_provider_staging_data.py scripts/build_tw_data_readiness_gate.py scripts/validate_tw_data_readiness_gate.py
```

结果：通过。

## 9. V1 安全边界

V1 本轮没有执行以下动作：

```text
provider publish
provider accepted latest switch
qlib accepted latest switch
readonly latest pointer write outside staging artifact
monitor config write
monitor scan
alerts write
broker connect
quick-trade
orders create/send
Agent prompt/tool/action modification
model training/retraining
model weight replacement
default model/strategy switch
frontend/API change
```

## 10. V2 交接建议

V2 可以基于 V1 产物继续做自动触发、U 链路串接和前端/API 验收，但必须沿用以下边界：

1. 前端模型/策略切换只能读取 `model_strategy_availability_matrix.json`，不能触发 provider refetch。
2. 非 `all_required_ready` 状态必须保留 previous readonly latest。
3. partial/pending/failed/deadline_missed 不得生成新的策略结果。
4. 若未来接入真实外部请求，只能写入 provider staging 目录，并必须保留 source-level `actual_latest_asof`、`available_at`、coverage、failure reason 和 retryable。
