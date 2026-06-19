# Phase D4 Readonly Standard Artifact Index 执行报告

生成日期：2026-06-17

## 1. 执行结论

D4 已完成。本阶段没有继续修改 replay parity，也没有接入用户自选 date range；按审查建议采用固定 `2026_ytd` 标准产物展示路线，输出只读标准 artifact index 与 ReplayWindowPolicy metadata。

结论：

```text
D4 readonly standard artifact index: pass
ReplayWindowPolicy metadata: pass
fixed_window_only=true: pass
user_selectable_range_enabled=false: pass
D3RR standard artifact consumed read-only: pass
readonly / not order / not investment advice flags: pass
provider / accepted latest / monitor / broker / order boundary: pass
```

## 2. 修改范围

新增：

```text
configs/tw_replay_window_policy.yaml
scripts/build_tw_modular_readonly_standard_artifact_index.py
scripts/validate_tw_modular_readonly_standard_artifact_index.py
scripts/validate_tw_replay_window_policy.py
tests/unit/test_tw_modular_readonly_standard_artifact_index.py
docs/tw_modular_contracts/PHASED4_READONLY_STANDARD_ARTIFACT_INDEX_EXECUTION_REPORT_CN.md
docs/tw_modular_contracts/PHASED4_READONLY_STANDARD_ARTIFACT_INDEX_REVIEW_HANDOFF_CN.md
```

未修改、未触碰：

```text
frontend/**
backend/**
backend_api_python/src/api/**
scripts/run_daily_tw_stock_auto_update.py
scripts/publish_tw_modular_readonly_snapshot.py
scripts/run_tw_modular_config_replay_matrix.py
D3RR artifact 原始目录
formal_replay_manifest.json
provider / accepted latest / monitor / broker / quick-trade / order 相关路径
```

## 3. D4 产物

Readonly standard artifact index：

```text
data_tw/artifacts/readonly_standard_artifact_index/d4/manifest.json
```

latest pointer：

```text
data_tw/artifacts/readonly_standard_artifact_index/d4/latest.json
```

checksum manifest：

```text
data_tw/artifacts/readonly_standard_artifact_index/d4/checksum_manifest.json
```

ReplayWindowPolicy：

```text
configs/tw_replay_window_policy.yaml
```

D4 index 指向的 D3RR 标准产物：

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/order_intent_replay_d3/d3_order_intent_replay_parity_20260617T062610Z/manifest.json
```

## 4. 固定窗口策略

D4 明确不开放用户自选 range：

```text
fixed_window_only=true
user_selectable_range_enabled=false
available_window_metadata_only=true
fixed_window=2026_ytd
fixed_window_start=2026-01-01
fixed_window_end=2026-05-07
```

ReplayWindowPolicy validator 已确认：

```text
fixed_window_does_not_overlap_training_windows=pass
latest_available_signal_date_bounds_fixed_window=pass
allowed_replay_start_min_bounds_fixed_window=pass
required_models_present=pass
diagnostic_rule_not_valid_strategy_evidence=pass
```

## 5. Index 内容

D4 index 包含：

```text
order_intent_replay_parity_manifest
order_intent_replay_result_manifest
order_intent_artifact_manifests count=25
baseline_manifest
rules_present
methods_present
window
row_counts
parity_status
checksum_manifest
replay_window_policy_metadata
```

ReplayResult 仍保持 D3RR source proof：

```text
generated_by=replay_execution_engine
execution_input_source=order_intent_artifact
decision_source=order_intent_artifact
not_copied_from_legacy_replay=true
legacy_replay_used_only_for_parity=true
```

## 6. 测试与验证

已执行：

```text
python -m py_compile scripts/build_tw_modular_readonly_standard_artifact_index.py scripts/validate_tw_modular_readonly_standard_artifact_index.py scripts/validate_tw_replay_window_policy.py scripts/build_tw_modular_order_intent_artifact.py scripts/validate_tw_modular_order_intent_artifact.py scripts/run_tw_modular_order_intent_replay.py scripts/validate_tw_modular_order_intent_replay.py scripts/run_tw_modular_order_intent_replay_parity.py scripts/validate_tw_modular_order_intent_replay_parity.py
result: pass
```

```text
python scripts/build_tw_modular_readonly_standard_artifact_index.py --json
result: ok=true, manifest=data_tw/artifacts/readonly_standard_artifact_index/d4/manifest.json
```

```text
python scripts/validate_tw_replay_window_policy.py --json
result: ok=true
```

```text
python scripts/validate_tw_modular_readonly_standard_artifact_index.py --artifact data_tw/artifacts/readonly_standard_artifact_index/d4/manifest.json --json
result: ok=true
```

```text
python -m pytest tests/unit/test_tw_modular_readonly_standard_artifact_index.py
result: 6 passed
```

```text
python scripts/validate_tw_modular_order_intent_replay_parity.py --artifact data_tw/experiments/extended_oos_qlib_orthogonal_ltr/order_intent_replay_d3/d3_order_intent_replay_parity_20260617T062610Z/manifest.json --json
result: ok=true
```

```text
python scripts/run_tw_modular_contract_regression.py --json
result: ok=true
```

```text
python scripts/validate_tw_modular_readonly_snapshot.py --latest --json
result: ok=true
```

## 7. 安全边界

D4 不新增 API route，不新增前端展示，不接受用户传入 `start/end`。如果后续 D5 开启用户自选窗口，必须先接入后端 ReplayWindowPolicy validator，并拒绝训练期窗口。

本阶段输出仅为只读 index / metadata，不触发：

```text
provider publish
accepted latest switch
monitor config / scan / alerts write
broker / quick-trade / orders
target_position / target_weight
```
