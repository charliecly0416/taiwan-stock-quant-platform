# Phase D5 Readonly Replay Window 审查交接

生成日期：2026-06-17

## 1. 审查结论建议

执行侧建议：D5 可进入审查。D5 已实现用户可选回放窗口，但只通过 GET 查询已有审计 artifact，并由后端 ReplayWindowPolicy validator 拒绝训练期、未来、diagnostic 和未审计窗口。

```text
backend_window_validator_exists=true
illegal_training_window_rejected_by_backend=true
frontend_date_picker_not_only_guard=true
diagnostic_rule_not_valid_strategy_evidence=true
readonly_only=true
no_provider_publish=true
no_accepted_latest_switch=true
no_monitor_broker_order=true
```

## 2. 审查对象

核心实现：

```text
backend/app/services/readonly_replay_window.py
backend/app/routes/readonly_replay_window.py
backend/app/routes/__init__.py
frontend/src/api/tw-stock.js
frontend/src/views/tw-stock-monitor/index.vue
scripts/validate_tw_readonly_replay_window_query.py
```

测试：

```text
backend/tests/test_tw_stock_readonly_replay_window_api.py
frontend/tests/unit/tw-stock-readonly-replay-window-check.mjs
```

执行报告：

```text
docs/tw_modular_contracts/PHASED5_READONLY_REPLAY_WINDOW_EXECUTION_REPORT_CN.md
```

## 3. 审查重点

建议重点确认：

```text
1. /api/tw-stock/readonly-replay-window 只有 GET。
2. 2025 训练期窗口由后端拒绝。
3. 2026-05-07 之后窗口由后端拒绝。
4. diagnostic rule 不能作为有效策略查询。
5. 非固定标准窗口不会即时生成 replay。
6. 前端只展示 API 返回，不本地回放。
```

## 4. 复跑命令

```bash
python scripts/validate_tw_readonly_replay_window_query.py --json
python -m pytest backend/tests/test_tw_stock_readonly_replay_window_api.py backend/tests/test_tw_stock_readonly_strategy_snapshot_api.py
cd frontend && node tests/unit/tw-stock-readonly-replay-window-check.mjs
python scripts/validate_tw_replay_window_policy.py --json
python scripts/validate_tw_modular_readonly_standard_artifact_index.py --artifact data_tw/artifacts/readonly_standard_artifact_index/d4/manifest.json --json
python scripts/validate_tw_modular_order_intent_replay_parity.py --artifact data_tw/experiments/extended_oos_qlib_orthogonal_ltr/order_intent_replay_d3/d3_order_intent_replay_parity_20260617T062610Z/manifest.json --json
python scripts/run_tw_modular_contract_regression.py --json
python scripts/validate_tw_modular_readonly_snapshot.py --latest --json
```

## 5. 后续注意

如果下一阶段要为非固定窗口生成新的 readonly ReplayResultArtifact，必须另行审查生成目录、manifest/checksum、validator 和禁止 provider/accepted/latest/monitor/trading 的边界；D5 当前没有做 on-demand generation。
