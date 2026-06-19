# Phase D6 Audited Readonly Replay Artifact 审查交接

生成日期：2026-06-17

## 1. 审查结论建议

D6 可进入审查。它把非固定窗口 replay 从在线计算改成了预生成只读 artifact 读取路径，且保持了 readonly 安全边界。

```text
readonly replay artifact exists=true
artifact checksum ok=true
backend query remains readonly=true
illegal training window rejected=true
future window rejected=true
diagnostic rule rejected=true
no on-demand generation=true
no provider / accepted latest / monitor / broker / order writes=true
```

## 2. 审查对象

核心实现：

```text
backend/app/services/readonly_replay_window.py
backend/app/routes/readonly_replay_window.py
backend/app/routes/__init__.py
scripts/build_tw_readonly_replay_window_artifact.py
scripts/validate_tw_readonly_replay_window_artifact.py
scripts/validate_tw_readonly_replay_window_query.py
frontend/src/api/tw-stock.js
frontend/src/views/tw-stock-monitor/index.vue
```

测试：

```text
backend/tests/test_tw_stock_readonly_replay_window_api.py
frontend/tests/unit/tw-stock-readonly-replay-window-check.mjs
```

执行报告：

```text
docs/tw_modular_contracts/PHASED6_READONLY_REPLAY_ARTIFACT_EXECUTION_REPORT_CN.md
```

## 3. 审查重点

建议重点确认：

```text
1. 非固定窗口请求只读取已落盘的 D6 manifest。
2. D6 manifest 与 checksum 都通过校验。
3. API handler 没有即时生成 replay。
4. 前端没有本地 replay、目标仓位或交易指令展示。
5. 训练期、未来窗口、diagnostic rule 都会被后端拒绝。
6. 任何 provider / accepted latest / monitor / broker / order 写入都没有新增。
```

## 4. 复跑命令

```bash
python scripts/validate_tw_readonly_replay_window_query.py --json
python scripts/validate_tw_readonly_replay_window_artifact.py --artifact data_tw/artifacts/readonly_replay_windows/d6/e4_frozen_qlib_2023_2025_ltr/top50_exit_one_worst_sell/20260102_20260507/order_intent_replay_result/manifest.json --json
python -m pytest backend/tests/test_tw_stock_readonly_replay_window_api.py backend/tests/test_tw_stock_readonly_strategy_snapshot_api.py tests/unit/test_tw_modular_readonly_standard_artifact_index.py
cd frontend && node tests/unit/tw-stock-readonly-replay-window-check.mjs
python scripts/run_tw_modular_contract_regression.py --json
python scripts/validate_tw_modular_readonly_snapshot.py --latest --json
```

## 5. 后续注意

如果后续要支持新的非固定窗口，只能继续走离线生成 + checksum + validator + readonly API 读取的链路；禁止把在线 API 退回成即时 replay 计算。
