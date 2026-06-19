# Phase U1 Daily Data / Feature / ModelSignal Artifact 接入执行报告

生成日期：2026-06-17

## 1. 执行范围

本阶段按 `PHASEU0_REVIEW_AND_PHASEU1_WORK_CN.md` 执行 U1：新增每日数据、特征、模型信号三类 staging artifact builder / validator，并提供 pass/fail golden samples。

本轮没有训练新模型，没有调参，没有替换冻结模型权重，没有生成 OrderIntentArtifact，没有生成 ReadonlyStrategySnapshot，没有更新 readonly latest pointer，没有触发 provider refresh / publish，没有切 provider accepted latest 或 qlib accepted latest，没有写 monitor config / scan / alerts，没有连接 broker / quick-trade / orders，没有修改 Agent prompt / tool / action。

## 2. 新增脚本

| 脚本 | 作用 |
| --- | --- |
| `scripts/build_tw_daily_data_ingestion_artifact.py` | 从本地 staging normalized CSV 构造 U1 DataIngestionArtifact，支持 `fresh_data_detected` 与 `no_new_data` |
| `scripts/validate_tw_daily_data_ingestion_artifact.py` | 校验 DataIngestionArtifact 必需文件、coverage、symbol mapping、freshness、forbidden action 与 no_latest_update |
| `scripts/build_tw_daily_feature_artifact.py` | 从 DataIngestionArtifact 派生只读 demo feature artifact，写 PIT 与 future-field audit |
| `scripts/validate_tw_daily_feature_artifact.py` | 校验 FeatureArtifact 的 `available_at <= signal_asof`、future field、必需文件与禁止标志 |
| `scripts/build_tw_daily_model_signal_artifact.py` | 从冻结既有 ModelSignalArtifact 按 asof 截取生成 U1 daily ModelSignalArtifact，不训练不重算 |
| `scripts/validate_tw_daily_model_signal_artifact.py` | 校验 daily ModelSignalArtifact core fields、source_feature/source_model、冻结 candidate、禁止标志与 no_latest_update |

## 3. 产物路径

### 3.1 Fresh data staging chain

```text
data_tw/artifacts/daily_data_ingestion/u1_fresh_data_detected_demo/manifest.json
data_tw/artifacts/daily_features/u1_fresh_features_demo/manifest.json
data_tw/artifacts/daily_model_signals/e4_frozen_qlib_2023_2025_ltr/u1_fresh_model_signal_demo/manifest.json
```

关键结果：

| Artifact | asof | row_count | freshness_status |
| --- | --- | ---: | --- |
| DataIngestionArtifact | 2026-03-27 | 640 | fresh_data_detected |
| FeatureArtifact | 2026-03-27 | 5 | fresh_data_detected |
| ModelSignalArtifact | 2026-03-27 | 50 | fresh_data_detected |

说明：本轮 fresh staging 数据来自本地 `data_tw/self_contained_demo/normalized/`；ModelSignal 来自冻结既有 `e4_frozen_qlib_2023_2025_ltr` artifact 的 asof 截取，不训练、不调参、不重算冻结模型权重。

### 3.2 No-new-data noop chain

```text
data_tw/artifacts/daily_data_ingestion/u1_no_new_data_noop_demo/manifest.json
data_tw/artifacts/daily_features/u1_no_new_data_features_noop_demo/manifest.json
data_tw/artifacts/daily_model_signals/e4_frozen_qlib_2023_2025_ltr/u1_no_new_data_model_signal_noop_demo/manifest.json
```

关键结果：

| Artifact | asof | row_count | freshness_status | updates_readonly_latest |
| --- | --- | ---: | --- | --- |
| DataIngestionArtifact | 2026-03-28 | 0 | no_new_data | false |
| FeatureArtifact | 2026-03-28 | 0 | no_new_data | false |
| ModelSignalArtifact | 2026-03-28 | 0 | no_new_data | false |

## 4. Golden samples

Golden root：

```text
data_tw/golden_samples/modular_daily_update/u1/
```

覆盖样本：

| 类型 | 样本 |
| --- | --- |
| pass | `data_ingestion/pass_fresh_data_minimal` |
| pass | `data_ingestion/pass_no_new_data_noop` |
| fail | `data_ingestion/fail_forbidden_action_marker_missing` |
| fail | `data_ingestion/fail_no_new_data_updates_latest` |
| pass | `feature_artifact/pass_fresh_data_minimal` |
| pass | `feature_artifact/pass_no_new_data_noop` |
| fail | `feature_artifact/fail_missing_available_at` |
| fail | `feature_artifact/fail_future_field_present` |
| pass | `model_signal/pass_fresh_data_minimal` |
| pass | `model_signal/pass_no_new_data_noop` |
| fail | `model_signal/fail_missing_available_at` |
| fail | `model_signal/fail_future_field_present` |
| fail | `model_signal/fail_forbidden_action_marker_missing` |

这些样本覆盖工作文档要求的最低负例：

```text
fail_missing_available_at
fail_future_field_present
fail_forbidden_action_marker_missing
fail_no_new_data_updates_latest
```

## 5. Validator 阻断能力

U1 validator 当前可阻断：

- `available_at > signal_asof`；
- 缺 coverage audit；
- 缺 symbol mapping audit；
- 出现 `future_return` / `forward_return` / `label` / `realized_pnl` / `execution` / `position` / `order` 字段；
- 缺 `no_provider_publish` / `no_accepted_latest_switch` / `no_monitor_write` / `no_broker_order`；
- `no_new_data` artifact 声称更新 readonly latest；
- ModelSignal 缺 core fields；
- ModelSignal 未声明 `source_feature_artifact` / `source_model_artifact`；
- forbidden action audit 中 provider、accepted latest、monitor、broker/order、readonly latest update 任一动作置 true。

## 6. 验证结果

语法检查：

```text
python -m py_compile scripts/build_tw_daily_data_ingestion_artifact.py scripts/validate_tw_daily_data_ingestion_artifact.py scripts/build_tw_daily_feature_artifact.py scripts/validate_tw_daily_feature_artifact.py scripts/build_tw_daily_model_signal_artifact.py scripts/validate_tw_daily_model_signal_artifact.py
```

结果：通过。

Golden validator：

```text
python scripts/validate_tw_daily_data_ingestion_artifact.py --run-golden --json
python scripts/validate_tw_daily_feature_artifact.py --run-golden --json
python scripts/validate_tw_daily_model_signal_artifact.py --run-golden --json
```

结果：全部 `ok=true`，`status=passed`。

Direct artifact validation：

```text
python scripts/validate_tw_daily_data_ingestion_artifact.py --artifact-path data_tw/artifacts/daily_data_ingestion/u1_fresh_data_detected_demo --json
python scripts/validate_tw_daily_feature_artifact.py --artifact-path data_tw/artifacts/daily_features/u1_fresh_features_demo --json
python scripts/validate_tw_daily_model_signal_artifact.py --artifact-path data_tw/artifacts/daily_model_signals/e4_frozen_qlib_2023_2025_ltr/u1_fresh_model_signal_demo --json
```

结果：全部 `ok=true`，`status=passed`。

汇总文件：

```text
data_tw/experiments/modular_daily_update/u1_validation_summary.json
```

汇总结果：

```text
ok=true
status=passed
```

## 7. 冻结候选保持情况

U1 ModelSignalArtifact 保持 U0 冻结范围：

```text
model_id=e4_frozen_qlib_2023_2025_ltr
model_family=ltr
strategy_compatibility=top50_exit_one_worst_sell
candidate_k=50
readonly_only=true
updates_readonly_latest=false
no_training=true
no_tuning=true
no_score_recompute_outside_frozen_model=true
no_default_strategy_switch=true
no_provider_publish=true
no_accepted_latest_switch=true
```

## 8. 禁止事项自检

| 禁止项 | 结果 |
| --- | --- |
| 训练/调参/替换模型权重 | 未触发 |
| 生成 OrderIntentArtifact | 未触发 |
| 生成 ReadonlyStrategySnapshot | 未触发 |
| 更新 readonly latest pointer | 未触发 |
| provider refresh / publish | 未触发 |
| provider accepted latest / qlib accepted latest switch | 未触发 |
| monitor config / scan / alerts 写入 | 未触发 |
| broker / quick-trade / orders | 未触发 |
| Agent prompt / tool / action 修改 | 未触发 |
| 前端本地计算策略或 replay | 未触发 |

## 9. 下一阶段 U2 前置条件

U1 已生成可审计的 daily data / feature / model signal staging 链路。进入 U2 前建议审查者确认：

1. `no_new_data` noop 是否明确保持 readonly latest 不变；
2. U1 ModelSignal 是否只作为 readonly candidate 输入，不被解释为交易指令；
3. U2 若生成 OrderIntentArtifact，必须继续保持 `not_order=true`、`not_target_position=true`、`not_investment_advice=true`；
4. U2 若生成 ReadonlySnapshot / RunRegistry / latest pointer 行为验证，必须仍是 staging 或 validator-gated，不得切 provider accepted latest 或 qlib accepted latest。
