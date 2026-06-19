# Phase D7 Readonly Replay Productization Closure 执行报告

生成日期：2026-06-17

## 1. 执行结论

D7 已完成。readonly replay window 已从 D6 的单 artifact 读取收口为 D7 多窗口索引读取：API 先过 ReplayWindowPolicy，再只读取 D7 index 登记过的已审计窗口。

结论：

```text
D7 readonly replay window index: pass
API returns indexed audited artifacts only: pass
fixed D4 2026_ytd window: pass
D6 generated non-fixed window: pass
frontend index-driven display: pass
E2E network audit GET-only: pass
readonly safety boundary: pass
```

## 2. 新增产物

```text
data_tw/artifacts/readonly_replay_windows/d7/manifest.json
data_tw/artifacts/readonly_replay_windows/d7/checksum_manifest.json
data_tw/artifacts/readonly_replay_windows/d7/latest.json
```

D7 index 当前登记：

```text
fixed_standard:
  model_id=e4_frozen_qlib_2023_2025_ltr
  strategy_rule=top50_exit_one_worst_sell
  start=2026-01-01
  end=2026-05-07
  manifest=data_tw/artifacts/readonly_standard_artifact_index/d4/manifest.json

generated_readonly:
  model_id=e4_frozen_qlib_2023_2025_ltr
  strategy_rule=top50_exit_one_worst_sell
  start=2026-01-02
  end=2026-05-07
  manifest=data_tw/artifacts/readonly_replay_windows/d6/e4_frozen_qlib_2023_2025_ltr/top50_exit_one_worst_sell/20260102_20260507/order_intent_replay_result/manifest.json
```

## 3. 修改范围

```text
backend/app/services/readonly_replay_window.py
backend/app/services/readonly_replay_window_index.py
backend/app/routes/readonly_replay_window.py
backend/app/routes/readonly_replay_window_index.py
backend/app/routes/__init__.py
backend/tests/test_tw_stock_readonly_replay_window_api.py
frontend/src/api/tw-stock.js
frontend/src/views/tw-stock-monitor/index.vue
frontend/tests/unit/tw-stock-readonly-replay-window-check.mjs
frontend/tests/e2e/tw-stock-readonly-replay-window-readonly.mjs
scripts/build_tw_readonly_replay_window_index.py
scripts/validate_tw_readonly_replay_window_index.py
scripts/validate_tw_readonly_replay_window_query.py
docs/tw_modular_contracts/READONLY_REPLAY_WINDOW_PRODUCTIZATION_GUIDE_CN.md
```

## 4. 后端行为

新增 GET only：

```text
GET /api/tw-stock/readonly-replay-window-index
```

查询接口保持：

```text
GET /api/tw-stock/readonly-replay-window
```

非固定窗口不再手拼 D6 路径，而是要求 D7 index 命中；未登记窗口返回：

```text
no_audited_replay_artifact_for_window
```

## 5. 前端行为

readonly replay panel 现在先读取 index：

```text
getTwStockReadonlyReplayWindowIndex -> GET /readonly-replay-window-index
getTwStockReadonlyReplayWindow -> GET /readonly-replay-window
```

前端展示区明确区分：

```text
D4 固定标准窗口
D6 已审计非固定窗口
未登记/非法窗口后端拒绝
```

前端仍不执行本地 replay，不展示目标仓位、交易指令、收益承诺或上涨概率。

## 6. 验证结果

```text
python scripts/build_tw_readonly_replay_window_index.py --json
result: ok=true, window_count=2

python scripts/validate_tw_readonly_replay_window_index.py --json
result: ok=true

python scripts/validate_tw_readonly_replay_window_artifact.py --artifact data_tw/artifacts/readonly_replay_windows/d6/e4_frozen_qlib_2023_2025_ltr/top50_exit_one_worst_sell/20260102_20260507/order_intent_replay_result/manifest.json --json
result: ok=true

python scripts/validate_tw_readonly_replay_window_query.py --json
result: ok=true

python -m pytest backend/tests/test_tw_stock_readonly_replay_window_api.py backend/tests/test_tw_stock_readonly_strategy_snapshot_api.py tests/unit/test_tw_modular_readonly_standard_artifact_index.py
result: 19 passed

node tests/unit/tw-stock-readonly-replay-window-check.mjs
result: ok

corepack pnpm build
result: pass

node frontend/tests/e2e/tw-stock-readonly-replay-window-readonly.mjs
result: pass

python scripts/run_tw_modular_contract_regression.py --json
result: ok=true

python scripts/validate_tw_modular_readonly_snapshot.py --latest --json
result: ok=true

python scripts/validate_tw_replay_window_policy.py --json
result: ok=true
```

说明：普通 sandbox 对部分命令仍有 `bwrap: loopback: Failed RTM_NEWADDR: Operation not permitted` 限制，相关 validator、build、node 检查与 E2E 已按环境规则在沙箱外重跑。

## 7. 只读边界

D7 未新增以下路径：

```text
provider publish / refresh
accepted latest switch
monitor config save / scan / alerts write
broker / quick-trade / orders
target_position / target_weight
API handler on-demand replay generation
frontend local replay
```

