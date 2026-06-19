# Phase D6 Audited Readonly Replay Artifact 生成执行报告

生成日期：2026-06-17

## 1. 执行结论

D6 已完成。非固定时间窗口不再由 API handler 即时计算 replay，而是由离线生成的 audited readonly ReplayResultArtifact 提供。后端查询仍保持只读，只会读取已落盘、已校验的 D6 artifact。

结论：

```text
D6 artifact build: pass
D6 artifact validator: pass
readonly replay window query: pass
illegal training window rejected: pass
future window rejected: pass
diagnostic rule rejected: pass
non-fixed window readonly lookup: pass
readonly safety boundary: pass
```

## 2. 修改范围

新增/修改：

```text
backend/app/services/readonly_replay_window.py
backend/app/routes/readonly_replay_window.py
backend/app/routes/__init__.py
backend/tests/test_tw_stock_readonly_replay_window_api.py
scripts/build_tw_readonly_replay_window_artifact.py
scripts/validate_tw_readonly_replay_window_artifact.py
scripts/validate_tw_readonly_replay_window_query.py
frontend/src/api/tw-stock.js
frontend/src/views/tw-stock-monitor/index.vue
frontend/tests/unit/tw-stock-readonly-replay-window-check.mjs
docs/tw_modular_contracts/PHASED6_READONLY_REPLAY_ARTIFACT_EXECUTION_REPORT_CN.md
docs/tw_modular_contracts/PHASED6_READONLY_REPLAY_ARTIFACT_REVIEW_HANDOFF_CN.md
```

本次 D6 生成的 artifact：

```text
data_tw/artifacts/readonly_replay_windows/d6/e4_frozen_qlib_2023_2025_ltr/top50_exit_one_worst_sell/20260102_20260507/order_intent_replay_result/manifest.json
```

## 3. D6 合约

D6 的目标不是把回放改成在线计算，而是建立可审计的只读 replay artifact 生成链：

```text
ReplayWindowPolicy 校验
  -> 选择/构建 order_intent_artifact
  -> ReplayExecutionEngine 只读运行
  -> 生成 readonly ReplayResultArtifact
  -> manifest / checksum / forbidden scope audit
  -> D5 API 仅读取已生成 artifact
```

明确禁止：

```text
API handler 内即时生成 replay
provider / accepted latest 写入
monitor / broker / order 写入
formal_replay_manifest.json 变更
D3RR 原始产物变更
前端本地 replay
```

## 4. 验证结果

```text
python scripts/validate_tw_readonly_replay_window_query.py --json
result: ok=true

python scripts/validate_tw_readonly_replay_window_artifact.py --artifact data_tw/artifacts/readonly_replay_windows/d6/e4_frozen_qlib_2023_2025_ltr/top50_exit_one_worst_sell/20260102_20260507/order_intent_replay_result/manifest.json --json
result: ok=true

python -m pytest backend/tests/test_tw_stock_readonly_replay_window_api.py backend/tests/test_tw_stock_readonly_strategy_snapshot_api.py tests/unit/test_tw_modular_readonly_standard_artifact_index.py
result: 18 passed

node tests/unit/tw-stock-readonly-replay-window-check.mjs
result: ok

python scripts/run_tw_modular_contract_regression.py --json
result: ok=true

python scripts/validate_tw_modular_readonly_snapshot.py --latest --json
result: ok=true
```

`python -m py_compile` 已对新增后端与脚本文件通过。

## 5. 产物说明

本次 D6 artifact 具备以下关键字段与校验：

```text
artifact_type=replay_result
schema_version=readonly_replay_result_d6_v1
readonly_only=true
not_order=true
not_target_position=true
not_investment_advice=true
generated_by=replay_execution_engine
execution_input_source=order_intent_artifact
decision_source=order_intent_artifact
forbidden_scope_audit=pass
checksum=pass
```

## 6. 只读边界

D6 不触发：

```text
provider publish / refresh
accepted latest switch
monitor config save / scan / alerts write
broker / quick-trade / orders
target_position / target_weight
```

后端 `GET /api/tw-stock/readonly-replay-window` 仍然只读；非固定窗口请求只会返回预生成 D6 artifact，不会在线计算。
