# Phase D5 审查与 Phase D6 工作文档

生成日期：2026-06-17

## 1. D5 审查结论

D5 通过，可以进入 D6。

结论：

```text
readonly replay window query: pass
backend ReplayWindowPolicy validator: pass
illegal training window rejected by backend: pass
future beyond latest signal rejected by backend: pass
diagnostic rule rejected as valid strategy evidence: pass
no on-demand replay generation: pass
frontend date picker not only guard: pass
readonly safety boundary: pass
next phase: D6 audited readonly replay artifact generation, if needed
```

D5 已开放用户选择回放窗口，但只允许查询已有审计标准产物。后端先执行 ReplayWindowPolicy 校验，再读取 D4 index / D3RR ReplayResultArtifact；非固定窗口不会即时生成 replay，而是返回 `no_audited_replay_artifact_for_window`。

## 2. 审查对象

handoff：

```text
docs/tw_modular_contracts/PHASED5_READONLY_REPLAY_WINDOW_REVIEW_HANDOFF_CN.md
```

执行报告：

```text
docs/tw_modular_contracts/PHASED5_READONLY_REPLAY_WINDOW_EXECUTION_REPORT_CN.md
```

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

## 3. Findings

未发现阻塞问题。

### Low: 前端文件中存在历史模块的交易/monitor 词汇，审查必须限定 D5 新增范围

`frontend/src/views/tw-stock-monitor/index.vue` 是大文件，旧模块中存在 monitor、模拟交易、收益展示等词汇。D5 新增的 `readonly-replay-window` 面板和 `loadReadonlyReplayWindow` loader 范围内未发现写接口、交易动作或危险文案。

后续审查前端时应继续按功能块切片审查，不能用全文件关键词直接判定 D5 越界。

## 4. 已通过项

### 4.1 后端窗口校验

`backend/app/services/readonly_replay_window.py` 当前顺序正确：

```text
load policy
validate model_id / strategy_rule / start / end
reject diagnostic rule
reject before allowed replay start
reject beyond latest signal
reject qlib/LTR training overlap
load D4 readonly standard artifact index
only return fixed audited window
reject non-fixed window without on-demand generation
checksum D4 index files
return readonly payload
```

关键拒绝项已覆盖：

```text
2025-01-01..2025-12-31 -> requested_window_before_allowed_replay_start / training overlap
2026-01-01..2026-06-01 -> requested_window_beyond_latest_signal
one_sell_one_buy_buggy_e8r -> diagnostic_rule_not_valid_strategy_evidence
2026-01-02..2026-05-07 -> no_audited_replay_artifact_for_window
```

### 4.2 API 只读

路由为 GET only：

```text
GET /api/tw-stock/readonly-replay-window
```

后端测试确认 POST/PUT/PATCH/DELETE 返回 405。

### 4.3 前端只读

前端新增面板：

```text
data-testid="readonly-replay-window-panel"
```

只调用：

```text
getTwStockReadonlyReplayWindow -> GET /api/tw-stock/readonly-replay-window
```

前端 date picker 只是输入控件；非法窗口展示后端错误，不在前端本地 replay。

## 5. 验证结果

本轮审查实际执行：

```text
python -m py_compile scripts/validate_tw_readonly_replay_window_query.py backend/app/services/readonly_replay_window.py backend/app/routes/readonly_replay_window.py : pass
python scripts/validate_tw_readonly_replay_window_query.py --json : ok=true
python -m pytest backend/tests/test_tw_stock_readonly_replay_window_api.py backend/tests/test_tw_stock_readonly_strategy_snapshot_api.py tests/unit/test_tw_modular_readonly_standard_artifact_index.py : 16 passed
node tests/unit/tw-stock-readonly-replay-window-check.mjs : ok
python scripts/validate_tw_replay_window_policy.py --json : ok=true
python scripts/validate_tw_modular_readonly_standard_artifact_index.py --artifact data_tw/artifacts/readonly_standard_artifact_index/d4/manifest.json --json : ok=true
python scripts/validate_tw_modular_order_intent_replay_parity.py --artifact data_tw/experiments/extended_oos_qlib_orthogonal_ltr/order_intent_replay_d3/d3_order_intent_replay_parity_20260617T062610Z/manifest.json --json : ok=true
python scripts/run_tw_modular_contract_regression.py --json : ok=true
python scripts/validate_tw_modular_readonly_snapshot.py --latest --json : ok=true
```

说明：多个 Python validator 和 Node 静态检查在普通沙箱中遇到 `bwrap: loopback: Failed RTM_NEWADDR: Operation not permitted`，已按环境规则重跑。Node 静态检查输出了 `/bin/sh: 2: source: not found` 的 shell 初始化噪声，但脚本本身输出 `[readonly-replay-window-check] ok` 且退出码为 0。

## 6. 只读安全边界

D5 新增范围未发现真实危险入口。

安全扫描命中的内容为：

```text
not_target_position
no_write_guarantees.does_not_touch_broker_or_orders
tests 中的 forbidden 列表
```

这些是只读否定字段或测试断言，不是实际交易/写入路径。

D5 仍不触发：

```text
provider publish / refresh
accepted latest switch
monitor config save / scan / alerts write
broker / quick-trade / orders
target_position / target_weight
on-demand replay generation
```

## 7. Phase D6 目标

D6 只有在需要支持非固定窗口结果时才应进入。D6 目标不是把 D5 的 GET 查询改成即时计算，而是建立“可审计的只读 replay artifact 生成链”。

D6 建议名称：

```text
Phase D6 Audited Readonly Replay Artifact Generation
```

目标链路：

```text
ReplayWindowPolicy validated request
  -> standard OrderIntentArtifact selection/build
  -> ReplayExecutionEngine readonly run
  -> new ReplayResultArtifact in research artifact dir
  -> manifest/checksum/validator
  -> D5 API only reads generated audited artifact
```

## 8. D6 必做项

### 8.1 生成边界

如果 D6 允许生成非固定窗口 replay artifact，必须满足：

```text
只写 data_tw/artifacts 或 data_tw/experiments 下的只读研究目录
不写 provider / accepted latest
不改 formal baseline
不改 D3RR 原始产物
不写 monitor config / scan / alerts
不触发 broker / quick-trade / order
```

### 8.2 Artifact 合同

每个新 ReplayResultArtifact 必须包含：

```text
artifact_type=replay_result
schema_version
created_by
readonly_only=true
not_order=true
not_target_position=true
not_investment_advice=true
generated_by=replay_execution_engine
execution_input_source=order_intent_artifact
decision_source=order_intent_artifact
ReplayWindowPolicy validation result
source OrderIntentArtifact manifests
row_counts
checksum_manifest
forbidden_scope_audit
```

### 8.3 Validator 与负例

D6 validator 必须拒绝：

```text
训练期窗口
未来窗口
diagnostic rule 作为有效策略
缺 checksum
缺 source manifest
ReplayResult copied from legacy replay
API on-demand 直接返回未审计临时结果
任何 provider / accepted latest / monitor / broker / order 写入
```

### 8.4 API/前端边界

D5 API 可以继续查询用户窗口，但 D6 后也必须只返回已落盘、已验证的 readonly ReplayResultArtifact。

禁止：

```text
请求进来后在 API handler 内直接计算并返回未审计结果
前端本地 replay
前端展示目标仓位/交易指令
```

## 9. D6 验证命令建议

```bash
python -m py_compile <new_or_modified_scripts>
python <d6_build_readonly_replay_artifact.py> --model-id <model> --strategy-rule <rule> --start <date> --end <date> --json
python <d6_validate_readonly_replay_artifact.py> --artifact <manifest> --json
python scripts/validate_tw_readonly_replay_window_query.py --json
python -m pytest <d6_backend_and_validator_tests>
node <frontend_readonly_replay_window_check>
python scripts/run_tw_modular_contract_regression.py --json
python scripts/validate_tw_modular_readonly_snapshot.py --latest --json
```

预期：

```text
D6 artifact validator ok=true
D5 query validator ok=true
illegal window tests pass
readonly safety scan no dangerous writes
```
