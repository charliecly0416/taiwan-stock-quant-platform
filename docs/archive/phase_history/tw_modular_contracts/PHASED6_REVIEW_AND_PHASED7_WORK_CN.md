# Phase D6 审查与 Phase D7 工作文档

生成日期：2026-06-17

## 1. D6 审查结论

D6 通过，可以进入 D7。

结论：

```text
audited readonly replay artifact generation: pass
D6 artifact validator: pass
D6 query validator: pass
backend reads pre-generated artifact only: pass
no API on-demand replay generation: pass
illegal training / future / diagnostic windows rejected: pass
frontend readonly display: pass
readonly safety boundary: pass
next phase: D7 productization closure / multi-window index / E2E audit
```

D6 已把非固定窗口 replay 从 API 在线计算风险，收敛为“离线生成已审计 artifact + API 只读读取”的路径。当前验证窗口：

```text
model_id=e4_frozen_qlib_2023_2025_ltr
strategy_rule=top50_exit_one_worst_sell
start=2026-01-02
end=2026-05-07
```

对应 artifact：

```text
data_tw/artifacts/readonly_replay_windows/d6/e4_frozen_qlib_2023_2025_ltr/top50_exit_one_worst_sell/20260102_20260507/order_intent_replay_result/manifest.json
```

## 2. 审查对象

handoff：

```text
docs/tw_modular_contracts/PHASED6_READONLY_REPLAY_ARTIFACT_REVIEW_HANDOFF_CN.md
```

执行报告：

```text
docs/tw_modular_contracts/PHASED6_READONLY_REPLAY_ARTIFACT_EXECUTION_REPORT_CN.md
```

核心实现：

```text
scripts/build_tw_readonly_replay_window_artifact.py
scripts/validate_tw_readonly_replay_window_artifact.py
scripts/validate_tw_readonly_replay_window_query.py
backend/app/services/readonly_replay_window.py
backend/app/routes/readonly_replay_window.py
frontend/src/api/tw-stock.js
frontend/src/views/tw-stock-monitor/index.vue
```

测试：

```text
backend/tests/test_tw_stock_readonly_replay_window_api.py
frontend/tests/unit/tw-stock-readonly-replay-window-check.mjs
```

## 3. Findings

未发现阻塞问题。

### Low: D6 artifact 仍保留 baseline/legacy parity 字段，后续产品展示应避免误读

D6 manifest 中仍包含：

```text
baseline_manifest
legacy_replay_used_only_for_parity=true
```

这是因为 D6 builder 复用 D3RR forward-chain runner 与 source manifest 结构。当前 D6 结果本身由 `ReplayExecutionEngine` 从 `OrderIntentArtifact` 正向生成，validator 也通过。

后续前端/API 展示 D6 非固定窗口时，应优先展示：

```text
generated_by=replay_execution_engine
execution_input_source=order_intent_artifact
decision_source=order_intent_artifact
readonly_replay_manifest
checksum
ReplayWindowPolicy validation
```

不要把 `baseline_manifest` 或 legacy parity 字段展示为 D6 非固定窗口的主要证据。

## 4. 已通过项

### 4.1 离线生成链

`scripts/build_tw_readonly_replay_window_artifact.py` 当前链路：

```text
ReplayWindowPolicy validate
load source manifests
reuse D3RR forward-chain runner
restrict one model / one strategy / requested window
run_forward_chain
write readonly ReplayResultArtifact
write forbidden_scope_audit.json
write checksum_manifest.json
write validation_report.json
```

生成产物包含：

```text
artifact_type=replay_result
schema_version=readonly_replay_result_d6_v1
readonly_only=true
not_order=true
not_target_position=true
not_investment_advice=true
production_trade_enabled=false
generated_by=replay_execution_engine
execution_input_source=order_intent_artifact
decision_source=order_intent_artifact
not_generated_in_api_handler=true
```

### 4.2 后端只读读取

`backend/app/services/readonly_replay_window.py` 对非固定窗口执行：

```text
ReplayWindowPolicy validation
resolve D6 manifest path
load manifest
check safety/source flags
verify checksum
return readonly payload
```

API handler 不生成 replay。若 manifest 不存在，返回：

```text
no_audited_replay_artifact_for_window
```

### 4.3 拒绝项

已验证：

```text
training window rejected
future beyond latest signal rejected
diagnostic rule rejected as valid strategy evidence
POST/PUT/PATCH/DELETE rejected by route
frontend loader only calls GET wrapper
```

## 5. 验证结果

本轮审查实际执行：

```text
python -m py_compile scripts/build_tw_readonly_replay_window_artifact.py scripts/validate_tw_readonly_replay_window_artifact.py scripts/validate_tw_readonly_replay_window_query.py backend/app/services/readonly_replay_window.py backend/app/routes/readonly_replay_window.py : pass
python scripts/build_tw_readonly_replay_window_artifact.py --model-id e4_frozen_qlib_2023_2025_ltr --strategy-rule top50_exit_one_worst_sell --start 2026-01-02 --end 2026-05-07 --json : ok=true
python scripts/validate_tw_readonly_replay_window_artifact.py --artifact data_tw/artifacts/readonly_replay_windows/d6/e4_frozen_qlib_2023_2025_ltr/top50_exit_one_worst_sell/20260102_20260507/order_intent_replay_result/manifest.json --json : ok=true
python scripts/validate_tw_readonly_replay_window_query.py --json : ok=true
python -m pytest backend/tests/test_tw_stock_readonly_replay_window_api.py backend/tests/test_tw_stock_readonly_strategy_snapshot_api.py tests/unit/test_tw_modular_readonly_standard_artifact_index.py : 18 passed
node tests/unit/tw-stock-readonly-replay-window-check.mjs : ok
python scripts/run_tw_modular_contract_regression.py --json : ok=true
python scripts/validate_tw_modular_readonly_snapshot.py --latest --json : ok=true
python scripts/validate_tw_replay_window_policy.py --json : ok=true
```

说明：

```text
validate / build / regression / frontend static check
```

在普通沙箱中多次遇到 `bwrap: loopback: Failed RTM_NEWADDR: Operation not permitted`，已按环境规则重跑。Node 静态检查仍有 `/bin/sh: 2: source: not found` 的 shell 初始化噪声，但脚本输出 `[readonly-replay-window-check] ok` 且退出码为 0。

## 6. 只读安全边界

D6 新增范围安全扫描命中的是：

```text
not_target_position
no_provider_publish
no_accepted_latest_switch
no_monitor_broker_order
does_not_touch_broker_or_orders
tests 中的 forbidden 列表
```

这些是只读否定字段或测试断言，不是实际写入路径。

D6 未发现：

```text
provider publish / refresh
accepted latest switch
monitor config save / scan / alerts write
broker / quick-trade / orders
target_position / target_weight
API handler on-demand replay generation
frontend local replay
```

## 7. Phase D7 目标

D7 建议进入产品化收口，而不是继续扩大计算范围。

D7 建议名称：

```text
Phase D7 Readonly Replay Productization Closure
```

目标：

```text
multi-window readonly artifact index
API returns only indexed audited artifacts
frontend presents fixed + generated windows clearly
E2E network audit proves GET-only for replay panel
docs / development guide updated
release-readiness validation bundle
```

## 8. D7 必做项

### 8.1 多窗口索引

建立只读 replay window index，登记：

```text
model_id
strategy_rule
start
end
manifest
checksum
schema_version
created_at
ReplayWindowPolicy validation
readonly flags
```

D5/D6 API 后续应只从该 index 查找可展示窗口，避免手拼路径成为长期产品接口。

### 8.2 API/前端产品化收口

API 必须保持：

```text
GET only
returns indexed audited artifacts only
no replay generation in request handler
clear error for missing audited window
```

前端必须清楚区分：

```text
固定 D4 2026_ytd 标准窗口
D6 已审计非固定窗口
非法/未审计窗口
```

前端不得展示：

```text
目标仓位
交易指令
保证收益
胜率承诺
上涨概率承诺
```

### 8.3 E2E 与安全审计

D7 必须提供：

```text
network audit: replay panel only calls GET /readonly-replay-window
no POST/PUT/PATCH/DELETE in replay panel workflow
illegal window shows backend rejection
generated window shows D6 manifest/checksum/source
console audit no fatal error
```

### 8.4 文档与开发规范

更新开发规范，明确新增窗口时必须：

```text
先过 ReplayWindowPolicy
离线生成 readonly ReplayResultArtifact
运行 artifact validator
登记到 readonly replay window index
API 只读读取 index/artifact
前端不本地 replay
```

## 9. D7 验证命令建议

```bash
python -m py_compile <new_or_modified_scripts>
python <d7_build_readonly_replay_window_index.py> --json
python <d7_validate_readonly_replay_window_index.py> --json
python scripts/validate_tw_readonly_replay_window_query.py --json
python scripts/validate_tw_readonly_replay_window_artifact.py --artifact <d6_manifest> --json
python -m pytest <backend_readonly_replay_window_tests>
node <frontend_replay_window_static_or_e2e_check>
python scripts/run_tw_modular_contract_regression.py --json
python scripts/validate_tw_modular_readonly_snapshot.py --latest --json
```

预期：

```text
D7 index validator ok=true
D6 artifact validator ok=true
D5/D6 query validator ok=true
backend/frontend tests pass
network audit no forbidden writes
readonly safety scan no dangerous writes
```

