# Phase D7 审查与 Phase D7R 修复工作文档

生成日期：2026-06-17

## 1. D7 审查结论

D7 不能完全通过，必须进入 D7R。

结论：

```text
readonly replay window index exists: pass
D7 index validator: pass
D6 artifact validator: pass
query validator: partial pass
frontend static/E2E: pass
readonly safety boundary: pass
fixed window index-gate enforcement: fail
next phase: D7R fixed-window index-gate repair
```

D7 已建立 readonly replay window index，并且非固定窗口已经从 D7 index 读取已登记 D6 artifact。但固定 `2026_ytd` 窗口仍绕过 D7 index，直接读取 D4 standard artifact index。这个行为与 D7 的产品化目标不一致：

```text
API returns indexed audited artifacts only
```

因此 D7 需要一轮 D7R 修复后再进入最终收口。

## 2. 审查对象

handoff：

```text
docs/tw_modular_contracts/PHASED7_READONLY_REPLAY_PRODUCTIZATION_REVIEW_HANDOFF_CN.md
```

执行报告：

```text
docs/tw_modular_contracts/PHASED7_READONLY_REPLAY_PRODUCTIZATION_EXECUTION_REPORT_CN.md
```

核心实现：

```text
backend/app/services/readonly_replay_window.py
backend/app/services/readonly_replay_window_index.py
backend/app/routes/readonly_replay_window.py
backend/app/routes/readonly_replay_window_index.py
scripts/build_tw_readonly_replay_window_index.py
scripts/validate_tw_readonly_replay_window_index.py
scripts/validate_tw_readonly_replay_window_query.py
frontend/src/api/tw-stock.js
frontend/src/views/tw-stock-monitor/index.vue
```

产物：

```text
data_tw/artifacts/readonly_replay_windows/d7/manifest.json
data_tw/artifacts/readonly_replay_windows/d7/checksum_manifest.json
data_tw/artifacts/readonly_replay_windows/d7/latest.json
```

## 3. Findings

### High: 固定窗口绕过 D7 index gate，仍直接读取 D4 index

位置：

```text
backend/app/services/readonly_replay_window.py
```

当前逻辑：

```text
if start != fixed.start or end != fixed.end:
    return _load_indexed_replay_payload(...)

# fixed window branch:
load D4_INDEX directly
read order_intent_replay_result_manifest from D4 index
return payload with hard-coded window_index_manifest
```

这意味着 D7 index 只约束非固定窗口，不约束固定 `2026_ytd` 窗口。

审查中做了一个只读进程内检查：将 `readonly_replay_window_index.LATEST_PATH` 临时指向不存在路径，然后分别查询固定窗口和非固定窗口。

结果：

```text
fixed ok readonly_replay_window_api_d7_v1 data_tw/artifacts/readonly_replay_windows/d7/manifest.json
generated err missing_artifact
```

这说明：

```text
non-fixed window: 依赖 D7 index
fixed window: 不依赖 D7 index，仍然成功返回
```

影响：

- D7 index 不是所有 replay window 查询的统一 gate；
- 若 D7 index 删除或未登记 fixed window，固定窗口仍可返回；
- API 响应里的 `window_index_manifest` 对 fixed window 是硬编码来源字段，不是实际读取 index entry 的证明；
- 当前测试没有覆盖“fixed window 必须依赖 D7 index latest/entry”这个负例。

### Medium: D7 validator 只验证 index 自身，不验证 API 查询必须经 index

位置：

```text
scripts/validate_tw_readonly_replay_window_index.py
scripts/validate_tw_readonly_replay_window_query.py
```

`validate_tw_readonly_replay_window_index.py` 能检查 index schema、window count、checksum；`validate_tw_readonly_replay_window_query.py` 能检查 fixed/generated 查询结果和拒绝项。

但缺少：

```text
fixed_standard_window_requires_d7_index_entry
fixed_standard_window_fails_when_d7_latest_missing
fixed_standard_window_fails_when_d7_index_entry_missing
query_response_window_index_matches_loaded_index_entry
```

这就是当前固定窗口绕过没有被 validator/test 捕获的原因。

### Low: 现有前端/E2E 通过，但属于表层网络证明

前端确实先调用：

```text
GET /api/tw-stock/readonly-replay-window-index
GET /api/tw-stock/readonly-replay-window
```

E2E 也证明 replay panel 没有 POST/PUT/PATCH/DELETE。

但 E2E 使用 mock API，不验证后端固定窗口是否真的依赖 D7 index。该项不阻塞前端，只说明后端 D7R 需要补负例。

## 4. 已通过项

D7 已完成且可保留：

```text
D7 readonly replay window index artifact exists
index contains fixed_standard and generated_readonly windows
/readonly-replay-window-index GET route exists
/readonly-replay-window GET route remains GET-only
non-fixed window uses indexed D6 artifact
frontend reads index + detail via GET
frontend build passes
frontend E2E network audit passes
contract regression ok=true
readonly snapshot validator ok=true
```

## 5. 验证结果

本轮审查实际执行：

```text
python -m py_compile scripts/build_tw_readonly_replay_window_index.py scripts/validate_tw_readonly_replay_window_index.py scripts/validate_tw_readonly_replay_window_query.py backend/app/services/readonly_replay_window.py backend/app/services/readonly_replay_window_index.py backend/app/routes/readonly_replay_window.py backend/app/routes/readonly_replay_window_index.py : pass
python scripts/build_tw_readonly_replay_window_index.py --json : ok=true
python scripts/validate_tw_readonly_replay_window_index.py --json : ok=true
python scripts/validate_tw_readonly_replay_window_artifact.py --artifact data_tw/artifacts/readonly_replay_windows/d6/e4_frozen_qlib_2023_2025_ltr/top50_exit_one_worst_sell/20260102_20260507/order_intent_replay_result/manifest.json --json : ok=true
python scripts/validate_tw_readonly_replay_window_query.py --json : ok=true
python -m pytest backend/tests/test_tw_stock_readonly_replay_window_api.py backend/tests/test_tw_stock_readonly_strategy_snapshot_api.py tests/unit/test_tw_modular_readonly_standard_artifact_index.py : 19 passed
node tests/unit/tw-stock-readonly-replay-window-check.mjs : ok
corepack pnpm build : pass
node frontend/tests/e2e/tw-stock-readonly-replay-window-readonly.mjs : pass
python scripts/run_tw_modular_contract_regression.py --json : ok=true
python scripts/validate_tw_modular_readonly_snapshot.py --latest --json : ok=true
```

说明：多个 Python/Node 命令在普通沙箱中遇到 `bwrap: loopback: Failed RTM_NEWADDR: Operation not permitted`，已按环境规则重跑。Node 静态检查仍有 `/bin/sh: 2: source: not found` 的 shell 初始化噪声，但脚本本身通过。

## 6. 只读安全边界

D7 新增范围未发现真实危险写入口。

安全扫描命中的内容为：

```text
not_target_position
does_not_touch_provider_accepted_latest
does_not_touch_broker_or_orders
E2E forbidden request matcher
tests 中的 forbidden 列表
```

这些是只读否定字段或测试断言，不是实际 provider/monitor/broker/order 写入。

D7 的问题是 index gate 语义不完整，不是只读越界。

## 7. D7R 修复目标

D7R 目标：

```text
所有 readonly replay window 查询，包括 fixed_standard 和 generated_readonly，都必须先命中 D7 index entry。
```

修复后服务层应满足：

```text
ReplayWindowPolicy validate
load D7 latest pointer
load D7 index manifest
find matching index entry by model_id / strategy_rule / start / end
validate entry artifact checksum/source flags
return payload based on matched entry
```

不得为 fixed window 保留绕过 D7 index 的直接 D4 fallback。

## 8. D7R 必做项

### 8.1 后端服务修复

`backend/app/services/readonly_replay_window.py` 应统一走 `load_index_entry(...)`。

建议：

```text
load_readonly_replay_window(...)
  -> ReplayWindowPolicy validation
  -> load_index_entry(model_id, strategy_rule, start, end)
  -> if entry.window_type == fixed_standard: load D4 standard artifact via entry.artifact_manifest
  -> if entry.window_type == generated_readonly: load D6 replay artifact via entry.artifact_manifest
  -> verify checksum from index service
  -> return payload
```

不允许：

```text
fixed window branch direct load D4_INDEX without D7 index
hard-coded window_index_manifest without actual index load
fallback to D4 when D7 index/latest missing
```

### 8.2 Validator 补强

`scripts/validate_tw_readonly_replay_window_query.py` 必须新增：

```text
fixed_standard_window_reads_indexed_artifact
fixed_standard_window_requires_d7_index
fixed_standard_window_fails_when_d7_latest_missing
generated_window_reads_indexed_artifact
query_response_window_index_matches_index_entry
```

### 8.3 测试补强

新增后端负例：

```text
test_fixed_window_requires_d7_index_latest
test_fixed_window_rejects_when_index_entry_missing
test_fixed_window_response_sources_match_index_entry
```

实现方式可以 monkeypatch `readonly_replay_window_index.LATEST_PATH` 或构造临时 index，确保 fixed window 不再绕过 index。

### 8.4 前端与 E2E

前端现有逻辑可以保留，但 E2E/静态检查应继续确认：

```text
GET /readonly-replay-window-index
GET /readonly-replay-window
no replay panel POST/PUT/PATCH/DELETE
fixed_standard / generated_readonly 文案清晰
```

## 9. D7R 验证命令

```bash
python -m py_compile backend/app/services/readonly_replay_window.py backend/app/services/readonly_replay_window_index.py scripts/validate_tw_readonly_replay_window_query.py
python scripts/validate_tw_readonly_replay_window_index.py --json
python scripts/validate_tw_readonly_replay_window_query.py --json
python -m pytest backend/tests/test_tw_stock_readonly_replay_window_api.py backend/tests/test_tw_stock_readonly_strategy_snapshot_api.py tests/unit/test_tw_modular_readonly_standard_artifact_index.py
cd frontend && node tests/unit/tw-stock-readonly-replay-window-check.mjs
corepack pnpm build
node frontend/tests/e2e/tw-stock-readonly-replay-window-readonly.mjs
python scripts/run_tw_modular_contract_regression.py --json
python scripts/validate_tw_modular_readonly_snapshot.py --latest --json
```

预期：

```text
fixed window cannot bypass D7 index
generated window still reads indexed D6 artifact
invalid/missing index fails closed
readonly safety scan no dangerous writes
```

