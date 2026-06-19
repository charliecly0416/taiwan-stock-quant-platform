# Phase D7R 审查与 Phase D8 工作文档

生成日期：2026-06-17

## 1. D7R 审查结论

D7R 通过，可以进入 D8 最终收口。

结论：

```text
fixed window requires D7 index: pass
generated window requires D7 index: pass
missing D7 latest fails closed: pass
missing fixed index entry fails closed: pass
query response sources match index entry: pass
backend tests: pass
frontend static/E2E: pass
readonly safety boundary: pass
next phase: D8 final release bundle / acceptance closure
```

D7R 已修复 D7 的核心缺口：固定 `2026_ytd` 窗口不再绕过 D7 index。现在所有 readonly replay window 查询统一经过：

```text
ReplayWindowPolicy
  -> D7 latest pointer
  -> D7 index manifest
  -> windows[] index entry
  -> indexed audited artifact
```

如果 D7 latest 缺失，固定窗口与非固定窗口都会失败关闭。

## 2. 审查对象

handoff：

```text
docs/tw_modular_contracts/PHASED7R_FIXED_WINDOW_INDEX_GATE_REPAIR_REVIEW_HANDOFF_CN.md
```

执行报告：

```text
docs/tw_modular_contracts/PHASED7R_FIXED_WINDOW_INDEX_GATE_REPAIR_EXECUTION_REPORT_CN.md
```

核心实现：

```text
backend/app/services/readonly_replay_window.py
backend/app/services/readonly_replay_window_index.py
backend/app/routes/readonly_replay_window.py
backend/app/routes/readonly_replay_window_index.py
scripts/validate_tw_readonly_replay_window_query.py
backend/tests/test_tw_stock_readonly_replay_window_api.py
```

## 3. Findings

未发现阻塞问题。

### Low: D7R 已修复后端 gate，后续变更必须防止回退

当前修复已经到位，但这是产品化链路的关键安全门。后续 D8 或新增窗口时，不得再加入：

```text
fixed window direct D4 fallback
hard-coded window_index_manifest without actual index load
API handler on-demand replay generation
```

建议 D8 把 D7R 的负例纳入最终 release bundle，避免回归。

## 4. 已通过项

### 4.1 固定窗口 index gate

审查复现了上一轮的检查：将 D7 latest 指针在进程内指向不存在文件后查询：

```text
fixed err missing_artifact
generated err missing_artifact
```

说明 fixed/generated 两类窗口都依赖 D7 latest/index，不再存在固定窗口绕过。

### 4.2 Validator 补强

`scripts/validate_tw_readonly_replay_window_query.py` 已覆盖：

```text
fixed_standard_window_reads_indexed_artifact
query_response_window_index_matches_index_entry
fixed_standard_window_fails_when_d7_latest_missing
generated_window_reads_indexed_artifact
```

### 4.3 后端测试补强

新增并通过：

```text
test_fixed_window_requires_d7_index_latest
test_fixed_window_rejects_when_index_entry_missing
test_fixed_window_response_sources_match_index_entry
```

### 4.4 只读产品化边界

后端仍是 GET-only；前端仍只通过 GET 读取 index/detail；E2E network audit 通过。

## 5. 验证结果

本轮审查实际执行：

```text
python -m py_compile backend/app/services/readonly_replay_window.py backend/app/services/readonly_replay_window_index.py scripts/validate_tw_readonly_replay_window_query.py backend/tests/test_tw_stock_readonly_replay_window_api.py : pass
python scripts/validate_tw_readonly_replay_window_query.py --json : ok=true
python scripts/validate_tw_readonly_replay_window_index.py --json : ok=true
python scripts/validate_tw_readonly_replay_window_artifact.py --artifact data_tw/artifacts/readonly_replay_windows/d6/e4_frozen_qlib_2023_2025_ltr/top50_exit_one_worst_sell/20260102_20260507/order_intent_replay_result/manifest.json --json : ok=true
python -m pytest backend/tests/test_tw_stock_readonly_replay_window_api.py backend/tests/test_tw_stock_readonly_strategy_snapshot_api.py tests/unit/test_tw_modular_readonly_standard_artifact_index.py : 22 passed
cd frontend && node tests/unit/tw-stock-readonly-replay-window-check.mjs : ok
cd frontend && corepack pnpm build : pass
node frontend/tests/e2e/tw-stock-readonly-replay-window-readonly.mjs : pass
python scripts/run_tw_modular_contract_regression.py --json : ok=true
python scripts/validate_tw_modular_readonly_snapshot.py --latest --json : ok=true
```

说明：多个 Python/Node 命令在普通沙箱中遇到 `bwrap: loopback: Failed RTM_NEWADDR: Operation not permitted`，已按环境规则重跑。Node 静态检查与前端 build 仍有 `/bin/sh: 2: source: not found` 的 shell 初始化噪声，但脚本、构建和 E2E 本身通过。

## 6. 只读安全边界

D7R 新增范围未发现真实危险写入口。

安全扫描命中的内容为：

```text
not_target_position
does_not_touch_provider_accepted_latest
does_not_touch_broker_or_orders
E2E forbidden request matcher
tests 中的 forbidden 列表
```

这些是只读否定字段或测试断言，不是实际 provider/monitor/broker/order 写入。

D7R 未新增：

```text
provider publish / refresh
accepted latest switch
monitor config save / scan / alerts write
broker / quick-trade / real orders
target_position / target_weight
API handler on-demand replay generation
frontend local replay
```

## 7. Phase D8 目标

D8 是最终 release bundle / acceptance closure，不应继续扩大功能范围。

D8 收口的闭合主链路为：

```text
D4 readonly standard artifact index
  -> D5 ReplayWindowPolicy 后端窗口校验
  -> D6 audited readonly replay artifact 离线生成
  -> D7 readonly replay window index
  -> D7R fixed/generated 窗口统一经 D7 index gate
  -> D8 final release bundle / acceptance closure
```

D8 建议名称：

```text
Phase D8 Final Readonly Replay Release Bundle
```

目标：

```text
freeze D4-D7R readonly replay artifacts and docs
produce final release manifest / acceptance report
run full validation bundle
link productization guide from module docs index
document new-window onboarding process
confirm no production writes / trading paths
```

D8 明确不新增：

```text
new model
new strategy
new replay rule
new user window generation path
new provider/accepted latest/monitor/trading integration
```

如后续需要新增窗口、模型、策略或 replay rule，必须另开独立阶段，并重新经过：

```text
ReplayWindowPolicy validation
offline artifact generation
artifact validator
window index registration
query validator
readonly API/frontend audit
```

## 8. D8 必做项

### 8.1 Release bundle

生成最终发布/验收文档，至少列出：

```text
D4 readonly standard artifact index manifest
D6 readonly replay artifact manifest
D7 readonly replay window index manifest
D7R query validator result
frontend static/E2E result
backend test result
contract regression result
readonly snapshot validator result
```

发布/验收报告必须新增一节：

```text
Final anti-regression evidence
```

该节至少列出：

```text
D7R fixed window index-gate negative tests
ReplayWindowPolicy illegal-window rejection results
D6 artifact validator result
D7 window index validator result
D7R query validator result
backend/frontend test results
readonly snapshot validator result
network/E2E GET-only audit result
```

D8 release bundle 必须包含 D7R 反回归硬门证据：

```text
fixed window requires D7 latest/index
generated window requires D7 latest/index
missing D7 latest fails closed
missing fixed index entry fails closed
query response window_index_manifest matches loaded D7 index entry
```

同时必须包含非法窗口/非法证据拒绝结果：

```text
training window rejected
future beyond latest signal rejected
diagnostic rule rejected as valid strategy evidence
missing indexed artifact rejected
```

### 8.2 文档入口

确认以下文档入口可被后续执行者找到：

```text
docs/tw_modular_contracts/READONLY_REPLAY_WINDOW_PRODUCTIZATION_GUIDE_CN.md
docs/tw_modular_contracts/TW_MODULAR_DECISION_REPLAY_DECOUPLING_WORK_CN.md
docs/tw_modular_contracts/TW_MODULAR_PIPELINE_FUTURE_DEVELOPMENT_GUIDE_CN.md
```

如 docs index 或 README 尚未链接，应补链接。

### 8.3 最终验证 bundle

D8 必须运行：

```bash
python scripts/validate_tw_readonly_replay_window_query.py --json
python scripts/validate_tw_readonly_replay_window_index.py --json
python scripts/validate_tw_readonly_replay_window_artifact.py --artifact data_tw/artifacts/readonly_replay_windows/d6/e4_frozen_qlib_2023_2025_ltr/top50_exit_one_worst_sell/20260102_20260507/order_intent_replay_result/manifest.json --json
python scripts/validate_tw_replay_window_policy.py --json
python scripts/validate_tw_modular_readonly_standard_artifact_index.py --artifact data_tw/artifacts/readonly_standard_artifact_index/d4/manifest.json --json
python scripts/validate_tw_modular_order_intent_replay_parity.py --artifact data_tw/experiments/extended_oos_qlib_orthogonal_ltr/order_intent_replay_d3/d3_order_intent_replay_parity_20260617T062610Z/manifest.json --json
python -m pytest backend/tests/test_tw_stock_readonly_replay_window_api.py backend/tests/test_tw_stock_readonly_strategy_snapshot_api.py tests/unit/test_tw_modular_readonly_standard_artifact_index.py
cd frontend && node tests/unit/tw-stock-readonly-replay-window-check.mjs
cd frontend && corepack pnpm build
node frontend/tests/e2e/tw-stock-readonly-replay-window-readonly.mjs
python scripts/run_tw_modular_contract_regression.py --json
python scripts/validate_tw_modular_readonly_snapshot.py --latest --json
```

最终验证证据必须能证明：

```text
fixed/generated 查询均依赖 D7 latest/index
API 只读取 indexed audited artifact
非法训练窗口被后端拒绝
超过 latest signal 的未来窗口被后端拒绝
diagnostic rule 不被作为有效策略验收证据
缺失 indexed artifact 时失败关闭
```

### 8.4 最终安全审计

D8 必须确认：

```text
no POST/PUT/PATCH/DELETE in replay window workflow
no provider publish / refresh
no accepted latest switch
no monitor config / scan / alerts writes
no broker / quick-trade / orders
no target_position / target_weight
no frontend local replay
no API handler on-demand replay generation
```

D8 报告必须显式声明：

```text
D8 did not generate new replay results in API handler
D8 did not modify provider/accepted latest/monitor/broker/order paths
D8 did not change default strategy
D8 did not add new model/strategy/replay rule
```

前端/API 安全审计应限定在本阶段新增或变更的 replay window 功能块与对应 API 调用，重点确认：

```text
GET /api/tw-stock/readonly-replay-window-index
GET /api/tw-stock/readonly-replay-window
```

不得出现 replay window workflow 相关的：

```text
POST/PUT/PATCH/DELETE
provider publish / refresh
accepted latest switch
monitor config / scan / alerts writes
broker / quick-trade / orders
target_position / target_weight
```

## 9. D8 通过标准

```text
all validators ok=true
backend/frontend tests pass
frontend build pass
E2E network audit pass
release bundle doc created
docs index links updated if needed
readonly safety boundary preserved
Final anti-regression evidence section complete
D7R index-gate negative tests preserved
ReplayWindowPolicy illegal-window rejection evidence complete
fixed/generated windows require D7 latest/index
query response window_index_manifest matches loaded D7 index entry
no API handler on-demand replay generation
no new model/strategy/replay rule/user window generation path
```

如果以下任一项失败，D8 不得收口，应要求执行者进入修复轮：

```text
fixed 或 generated 查询绕过 D7 latest/index
API 读取未注册、未审计或缺失的 artifact
训练窗口或未来窗口被当作合法窗口接受
diagnostic rule 被当作有效策略验收证据
前端执行本地 replay
API handler 生成新的 replay result
新增 provider/accepted latest/monitor/broker/order 写入口
新增默认策略、模型、replay rule 或用户窗口生成路径
```

