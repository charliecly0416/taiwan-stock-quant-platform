# Phase D5 Readonly Replay Window 执行报告

生成日期：2026-06-17

## 1. 执行结论

D5 已完成。用户可在前端选择回放窗口，但窗口必须由后端 ReplayWindowPolicy validator 校验；训练期窗口、未来窗口、diagnostic rule、未审计窗口都会被后端拒绝。D5 不即时生成新 replay artifact，只返回已有 D4/D3RR 标准产物摘要。

结论：

```text
D5 readonly replay window query: pass
backend window validator: pass
illegal training window rejected by backend: pass
future beyond latest signal rejected by backend: pass
diagnostic rule not valid strategy evidence: pass
no on-demand replay generation: pass
readonly frontend display: pass
readonly safety boundary: pass
```

## 2. 修改范围

新增/修改：

```text
backend/app/services/readonly_replay_window.py
backend/app/routes/readonly_replay_window.py
backend/app/routes/__init__.py
backend/tests/test_tw_stock_readonly_replay_window_api.py
frontend/src/api/tw-stock.js
frontend/src/views/tw-stock-monitor/index.vue
frontend/tests/unit/tw-stock-readonly-replay-window-check.mjs
scripts/validate_tw_readonly_replay_window_query.py
docs/tw_modular_contracts/PHASED5_READONLY_REPLAY_WINDOW_EXECUTION_REPORT_CN.md
docs/tw_modular_contracts/PHASED5_READONLY_REPLAY_WINDOW_REVIEW_HANDOFF_CN.md
```

未修改、未触碰：

```text
scripts/run_daily_tw_stock_auto_update.py
scripts/publish_tw_modular_readonly_snapshot.py
D3RR artifact 原始目录
formal_replay_manifest.json
provider / accepted latest / monitor 写入 / broker / quick-trade / order 路径
```

## 3. 后端 API

新增 GET only：

```text
GET /api/tw-stock/readonly-replay-window?model_id=...&strategy_rule=...&start=YYYY-MM-DD&end=YYYY-MM-DD
```

合法标准窗口返回已有 D4/D3RR artifact 摘要：

```text
model_id=e4_frozen_qlib_2023_2025_ltr
strategy_rule=top50_exit_one_worst_sell
start=2026-01-01
end=2026-05-07
```

后端拒绝：

```text
2025-01-01..2025-12-31 -> requested_window_before_allowed_replay_start 或 training overlap
2026-01-01..2026-06-01 -> requested_window_beyond_latest_signal
one_sell_one_buy_buggy_e8r -> diagnostic_rule_not_valid_strategy_evidence
2026-01-02..2026-05-07 -> no_audited_replay_artifact_for_window
```

## 4. 前端展示

新增只读面板：

```text
frontend/src/views/tw-stock-monitor/index.vue
data-testid="readonly-replay-window-panel"
```

前端只调用：

```text
getTwStockReadonlyReplayWindow -> GET /api/tw-stock/readonly-replay-window
```

前端不做本地 replay，不保存配置，不调用 monitor scan，不调用交易/券商/quick-trade。

## 5. Validator

新增：

```text
scripts/validate_tw_readonly_replay_window_query.py
```

检查项：

```text
valid_standard_window_ok
readonly_only
backend_window_validator_exists
model_training_windows_traceable
replay_result_source_order_intent
checksum_ok
no_on_demand_generation
illegal_training_window_rejected_by_backend
future_beyond_signal_rejected_by_backend
diagnostic_rule_not_valid_strategy_evidence
unavailable_window_not_generated_on_demand
```

## 6. 验证结果

```text
python -m py_compile scripts/validate_tw_readonly_replay_window_query.py backend/app/services/readonly_replay_window.py backend/app/routes/readonly_replay_window.py
result: pass
```

```text
python scripts/validate_tw_readonly_replay_window_query.py --json
result: ok=true
```

```text
python -m pytest tests/unit/test_tw_modular_readonly_standard_artifact_index.py backend/tests/test_tw_stock_readonly_replay_window_api.py backend/tests/test_tw_stock_readonly_strategy_snapshot_api.py
result: 16 passed
```

```text
node tests/unit/tw-stock-readonly-replay-window-check.mjs
result: ok
```

```text
node tests/unit/tw-stock-readonly-strategy-snapshot-check.mjs
result: ok
```

```text
python scripts/validate_tw_replay_window_policy.py --json
result: ok=true
python scripts/validate_tw_modular_readonly_standard_artifact_index.py --artifact data_tw/artifacts/readonly_standard_artifact_index/d4/manifest.json --json
result: ok=true
python scripts/validate_tw_modular_order_intent_replay_parity.py --artifact data_tw/experiments/extended_oos_qlib_orthogonal_ltr/order_intent_replay_d3/d3_order_intent_replay_parity_20260617T062610Z/manifest.json --json
result: ok=true
python scripts/run_tw_modular_contract_regression.py --json
result: ok=true
python scripts/validate_tw_modular_readonly_snapshot.py --latest --json
result: ok=true
```

## 7. 安全边界

D5 仍不触发：

```text
provider publish / refresh
accepted latest switch
monitor config save / scan / alerts write
broker / quick-trade / orders
target_position / target_weight
```

前端 date picker 只是输入控件；非法窗口由后端拒绝。
