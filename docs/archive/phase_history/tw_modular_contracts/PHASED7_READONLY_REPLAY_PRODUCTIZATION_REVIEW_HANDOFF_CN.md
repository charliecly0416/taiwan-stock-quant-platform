# Phase D7 Readonly Replay Productization Closure 审查交接

生成日期：2026-06-17

## 1. 审查结论建议

D7 可进入审查。执行侧已将 readonly replay window 产品化为 D7 index 驱动：后端只返回 index 登记过的已审计 artifact，前端只通过 GET 读取 index 和 replay detail。

```text
readonly replay window index exists=true
D7 index validator ok=true
D6 artifact validator ok=true
query validator ok=true
backend tests pass=true
frontend static check pass=true
E2E network audit pass=true
```

## 2. 审查对象

核心实现：

```text
backend/app/services/readonly_replay_window.py
backend/app/services/readonly_replay_window_index.py
backend/app/routes/readonly_replay_window.py
backend/app/routes/readonly_replay_window_index.py
frontend/src/api/tw-stock.js
frontend/src/views/tw-stock-monitor/index.vue
scripts/build_tw_readonly_replay_window_index.py
scripts/validate_tw_readonly_replay_window_index.py
```

测试：

```text
backend/tests/test_tw_stock_readonly_replay_window_api.py
frontend/tests/unit/tw-stock-readonly-replay-window-check.mjs
frontend/tests/e2e/tw-stock-readonly-replay-window-readonly.mjs
```

产物：

```text
data_tw/artifacts/readonly_replay_windows/d7/manifest.json
data_tw/artifacts/readonly_replay_windows/d7/checksum_manifest.json
data_tw/artifacts/readonly_replay_windows/d7/latest.json
```

开发规范：

```text
docs/tw_modular_contracts/READONLY_REPLAY_WINDOW_PRODUCTIZATION_GUIDE_CN.md
```

## 3. 审查重点

建议重点确认：

```text
1. /readonly-replay-window-index 和 /readonly-replay-window 都是 GET only。
2. 非固定窗口由 D7 index 命中，不再由服务层手拼 D6 路径。
3. D7 index 同时登记 D4 fixed_standard 与 D6 generated_readonly。
4. 未登记窗口仍返回 no_audited_replay_artifact_for_window。
5. 前端 replay panel 只读 index/detail，不调用 POST/PUT/PATCH/DELETE。
6. E2E network audit 无 replay panel 写请求。
```

## 4. 复跑命令

```bash
python scripts/validate_tw_readonly_replay_window_index.py --json
python scripts/validate_tw_readonly_replay_window_artifact.py --artifact data_tw/artifacts/readonly_replay_windows/d6/e4_frozen_qlib_2023_2025_ltr/top50_exit_one_worst_sell/20260102_20260507/order_intent_replay_result/manifest.json --json
python scripts/validate_tw_readonly_replay_window_query.py --json
python -m pytest backend/tests/test_tw_stock_readonly_replay_window_api.py backend/tests/test_tw_stock_readonly_strategy_snapshot_api.py tests/unit/test_tw_modular_readonly_standard_artifact_index.py
cd frontend && node tests/unit/tw-stock-readonly-replay-window-check.mjs
corepack pnpm build
node frontend/tests/e2e/tw-stock-readonly-replay-window-readonly.mjs
python scripts/run_tw_modular_contract_regression.py --json
python scripts/validate_tw_modular_readonly_snapshot.py --latest --json
```

## 5. 后续注意

后续新增任意非固定窗口，必须先离线生成 readonly ReplayResultArtifact，跑 artifact validator，再登记到 D7 index。禁止把 API handler 改回即时 replay 计算。

