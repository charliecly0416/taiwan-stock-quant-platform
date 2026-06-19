# Phase D7R Fixed Window Index Gate Repair 执行报告

生成日期：2026-06-17

## 1. 执行结论

D7R 已完成。固定 `2026_ytd` replay window 不再绕过 D7 readonly replay window index；所有 readonly replay window 查询现在统一先经过：

```text
ReplayWindowPolicy -> D7 latest -> D7 manifest -> windows[] index entry -> indexed audited artifact
```

结论：

```text
fixed window requires D7 index: pass
generated window still requires D7 index: pass
missing D7 latest fails closed: pass
missing fixed index entry fails closed: pass
query response sources match loaded index entry: pass
readonly safety boundary: pass
```

## 2. 修复范围

```text
backend/app/services/readonly_replay_window.py
backend/tests/test_tw_stock_readonly_replay_window_api.py
scripts/validate_tw_readonly_replay_window_query.py
```

## 3. 后端修复

`backend/app/services/readonly_replay_window.py` 已改为统一 index gate：

```text
load_readonly_replay_window(...)
  -> ReplayWindowPolicy validation
  -> readonly_replay_window_index.load_readonly_replay_window_index()
  -> match entry by model_id / strategy_rule / start / end
  -> load artifact_manifest from matched entry
  -> validate readonly/source/checksum flags
  -> return response from indexed artifact
```

固定窗口处理方式：

```text
window_type=fixed_standard
artifact_manifest=data_tw/artifacts/readonly_standard_artifact_index/d4/manifest.json
order_intent_replay_result_manifest is read only from the indexed D4 artifact
```

非固定窗口处理方式：

```text
window_type=generated_readonly
artifact_manifest=data_tw/artifacts/readonly_replay_windows/d6/.../order_intent_replay_result/manifest.json
```

不再保留固定窗口直接读取 D4 index 的 fallback。

## 4. API 响应变化

readonly replay window query schema 升级为：

```text
readonly_replay_window_api_d7r_v1
```

响应新增或强化：

```text
window_index.window_type
sources.window_index_manifest
sources.window_index_entry_manifest
no_write_guarantees.fixed_window_requires_d7_index=true
no_write_guarantees.reads_indexed_audited_artifact_only=true
```

## 5. Validator 补强

`scripts/validate_tw_readonly_replay_window_query.py` 已新增 D7R gate 检查：

```text
fixed_standard_window_reads_indexed_artifact
query_response_window_index_matches_index_entry
fixed_standard_window_fails_when_d7_latest_missing
generated_window_reads_indexed_artifact
```

这些检查确保 fixed/generated 两类窗口都必须从 D7 index 返回，并且 fixed window 在 D7 latest 缺失时失败关闭。

## 6. 后端测试补强

`backend/tests/test_tw_stock_readonly_replay_window_api.py` 已新增：

```text
test_fixed_window_requires_d7_index_latest
test_fixed_window_rejects_when_index_entry_missing
test_fixed_window_response_sources_match_index_entry
```

覆盖：

```text
D7 latest missing -> fixed window returns missing_artifact
D7 index without fixed entry -> no_audited_replay_artifact_for_window
fixed response source fields match D7 index entry
```

## 7. 验证结果

已执行：

```text
python -m py_compile backend/app/services/readonly_replay_window.py backend/app/services/readonly_replay_window_index.py scripts/validate_tw_readonly_replay_window_query.py backend/tests/test_tw_stock_readonly_replay_window_api.py
result: pass

python scripts/validate_tw_readonly_replay_window_query.py --json
result: ok=true

python -m pytest backend/tests/test_tw_stock_readonly_replay_window_api.py backend/tests/test_tw_stock_readonly_strategy_snapshot_api.py tests/unit/test_tw_modular_readonly_standard_artifact_index.py
result: 22 passed

python scripts/validate_tw_readonly_replay_window_index.py --json
result: ok=true

cd frontend && node tests/unit/tw-stock-readonly-replay-window-check.mjs
result: ok

python scripts/validate_tw_readonly_replay_window_artifact.py --artifact data_tw/artifacts/readonly_replay_windows/d6/e4_frozen_qlib_2023_2025_ltr/top50_exit_one_worst_sell/20260102_20260507/order_intent_replay_result/manifest.json --json
result: ok=true

cd frontend && corepack pnpm build
result: pass

python scripts/run_tw_modular_contract_regression.py --json
result: ok=true

python scripts/validate_tw_modular_readonly_snapshot.py --latest --json
result: ok=true

node frontend/tests/e2e/tw-stock-readonly-replay-window-readonly.mjs
result: pass
```

说明：普通 sandbox 对部分 Python/Node 命令仍有 `bwrap: loopback: Failed RTM_NEWADDR: Operation not permitted` 限制，相关命令已按环境规则在沙箱外重跑。前端静态检查和构建需要在 `frontend` 工作目录执行；Node 静态检查与构建存在 `/bin/sh: 2: source: not found` 的 shell 初始化噪声，但脚本和构建本身通过。

## 8. 只读安全边界

D7R 未新增以下能力：

```text
provider publish / refresh
accepted latest switch
monitor config save / scan / alerts write
broker / quick-trade / real orders
target_position / target_weight
API handler on-demand replay generation
frontend local replay
```

安全关键词扫描命中主要为：

```text
not_order / no_order_action / not_target_position
does_not_generate_replay_on_demand
does_not_touch_broker_or_orders
order_intent_artifact source fields
E2E forbidden request matcher
既有 sim/orders API 区域
```

这些命中是只读声明、来源证明、测试断言或既有模拟订单 API，不是 D7R 新增真实写入口。

