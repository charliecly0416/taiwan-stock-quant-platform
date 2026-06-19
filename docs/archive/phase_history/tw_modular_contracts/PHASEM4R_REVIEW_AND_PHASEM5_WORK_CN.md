# Phase M4R 审查与 Phase M5 工作文档

生成日期：2026-06-17

## 1. 审查结论

Phase M4R 通过，允许进入 Phase M5。

M4R 已关闭 M4 审查指出的 GET-only 阻断项：`/tw-stock-monitor` 的 M4 readonly acceptance 自动路径不再调用旧的 `runTwStockPortfolioReplay()` 或 `runTwStockReadonlyBacktest()`，`mounted()`、`refreshAll()`、readonly strategy snapshot 和 readonly replay window 的加载/刷新路径保持 GET-only。

旧 replay/strategy POST wrapper 仍保留为显式人工研究入口，但已从 M4 readonly acceptance path 排除。M4R 未修改 `scripts/run_daily_tw_stock_auto_update.py`，未暴露 legacy provider gate，未扩展 Agent prompt/tool/action。

## 2. 复核范围

审查输入：

```text
docs/tw_modular_contracts/PHASEM4R_FRONTEND_READONLY_GET_ONLY_REPAIR_EXECUTION_REPORT_CN.md
frontend/src/views/tw-stock-monitor/index.vue
scripts/validate_tw_frontend_readonly_m4.py
frontend/tests/unit/tw-stock-readonly-strategy-snapshot-check.mjs
frontend/tests/unit/tw-stock-readonly-replay-window-check.mjs
frontend/tests/e2e/tw-stock-readonly-replay-window-readonly.mjs
frontend/tests/e2e/tw-stock-readonly-strategy-snapshot-readonly.mjs
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/m4_frontend_readonly/network_audit.json
```

审查重点：

```text
mounted / refreshAll 是否仍自动触发 replay/strategy POST
M4 acceptance entrypoints 是否引用旧 write path
validator 是否把 replay/strategy write 纳入 forbidden request
E2E 是否输出真实 network_audit.json
network audit 中 forbidden_request_count / replay_strategy_write_count 是否为 0
M3R daily script audit 是否仍通过
Agent prompt/tool/action 是否未扩展
```

## 3. 通过项

### 3.1 自动路径已移除旧 replay POST

`frontend/src/views/tw-stock-monitor/index.vue` 的 `mounted()` 现在调用 `loadRankTechCrossLatest()`，不再调用 `loadRankTechPortfolioPanel()`：

```text
mounted()
  loadReadonlyStrategySnapshot()
  loadReadonlyReplayWindowIndex()
  loadReadonlyReplayWindow()
  loadRankTechCrossLatest()
```

`refreshAll()` 同样只调用 `loadRankTechCrossLatest()`，不再自动触发 portfolio replay POST：

```text
refreshAll()
  Promise.all([... loadReadonlyReplayWindow(), loadRankTechCrossLatest(), ...])
```

这关闭了 M4 阻断项中“页面初始化自动调用 POST /api/tw-stock/rank-tech-cross/portfolio-replay”的问题。

### 3.2 Validator 已纳入 replay/strategy write gate

`scripts/validate_tw_frontend_readonly_m4.py` 已升级到：

```text
schema_version=m4.0.1
```

新增审计结果：

```text
replay_strategy_write_wrappers
m4_acceptance_path_audit
network_audit.replay_strategy_write_count
```

复跑结果：

```text
M4R validator: ok=true
readonly_workflow_only_get=true
forbidden_request_count=0
replay_strategy_write_count=0
legacy_provider_gate_not_exposed=true
```

同时 validator 仍识别旧 write wrapper，但标记为 manual-only：

```text
runTwStockPortfolioReplay -> manual_only_allowed=true
runTwStockReadonlyBacktest -> manual_only_allowed=true
```

### 3.3 E2E network audit 已真实落盘

M4R 生成：

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/m4_frontend_readonly/readonly_replay_window_network_audit.json
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/m4_frontend_readonly/readonly_strategy_snapshot_network_audit.json
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/m4_frontend_readonly/network_audit.json
```

审查复核 `network_audit.json`：

```text
forbidden_requests=[]
forbidden_request_count=0
monitor_config_write_count=0
monitor_scan_post_count=0
monitor_alerts_write_count=0
ops_provider_publish_refresh_accepted_latest_request_count=0
replay_strategy_write_count=0
broker_quick_trade_orders_request_count=0
failed_response_count=0
```

`all_requests` 中仅看到 GET 请求，包含 readonly snapshot/window、rank-tech latest、monitor GET、Agent context GET、qlib status GET 和静态资源 GET；未看到 replay/strategy POST。

### 3.4 复跑验证

已复跑：

```bash
python -m py_compile scripts/validate_tw_frontend_readonly_m4.py scripts/run_tw_modular_contract_regression.py
python scripts/validate_tw_frontend_readonly_m4.py --json
python scripts/validate_tw_daily_orchestrator_m3.py --audit-script scripts/run_daily_tw_stock_auto_update.py --json
python scripts/run_tw_modular_contract_regression.py --json
cd frontend && node tests/unit/tw-stock-readonly-strategy-snapshot-check.mjs
cd frontend && node tests/unit/tw-stock-readonly-replay-window-check.mjs
cd frontend && corepack pnpm build
cd frontend && TW_STOCK_MONITOR_BASE_URL=http://127.0.0.1:5173 node tests/e2e/tw-stock-readonly-replay-window-readonly.mjs
cd frontend && TW_STOCK_MONITOR_BASE_URL=http://127.0.0.1:5173 node tests/e2e/tw-stock-readonly-strategy-snapshot-readonly.mjs
```

结果：

```text
py_compile: pass
M4R validator: ok=true, schema_version=m4.0.1
M3R script audit: ok=true
contract regression: ok=true
frontend unit checks: pass
frontend build: pass
readonly replay window E2E: pass
readonly strategy snapshot E2E: pass
```

说明：本次 E2E 使用 `frontend/dist` 下 `python -m http.server 5173 --bind 127.0.0.1` 临时静态服务复跑，复跑后已停止服务。

## 4. 台股只读安全边界审查

### Findings

Critical：未发现 M4 readonly acceptance path 中的 broker/order/quick-trade/target-position、provider publish/refresh、accepted latest、replay/strategy POST。

High：M4 中发现的旧 portfolio replay POST 自动触发问题已修复；运行时 network audit 证明 `replay_strategy_write_count=0`。

Medium：旧 `runTwStockPortfolioReplay()` 和 `runTwStockReadonlyBacktest()` 仍保留为显式人工研究功能，不属于 M4/M5 自动验收路径。后续如继续保留，应在产品文案和审计中保持“历史模拟/只读研究”语义，不能变成默认策略证据。

Low：E2E 仍使用 route mock 后端响应；真实部署验收时应复跑相同 network audit。

### Verdict

M4R 通过。Frontend readonly display GET-only 阻断项已关闭。

## 5. 残余风险

1. 旧 replay/backtest POST 手动入口仍存在，M4R 只证明它们不在 readonly acceptance 自动路径中。
2. M4R 不改变 M3R legacy provider gate 的治理状态。
3. network audit 基于 Playwright mock，真实部署仍需按同一规则复验。
4. Agent context 仍为 GET-only placeholder，M5 不得借 smoke onboarding 改 Agent prompt/tool/action。

## 6. Phase M5 工作范围

M5 目标：在真正开发新模型、新策略前，用 smoke / dry-run 验证 onboarding 流程是否顺畅。

M5 仍不训练真实新模型，不产出策略收益结论，不切默认策略。

建议做两个 smoke：

```text
dummy_new_model_signal_adapter_smoke
dummy_new_strategy_dependency_smoke
```

所有 M5 smoke 产物必须标记：

```text
smoke_only=true
not_valid_strategy_evidence=true
no_replay_return_conclusion=true
not_default_candidate=true
```

M5 要证明以下流程可跑通：

```text
registry entry
contract reference
validator pass/fail
strategy dependency check
ModelSignalArtifact compatibility check
OrderIntentArtifact compatibility check, if applicable
no replay return conclusion
no default switch
```

## 7. M5 禁止事项

M5 不得做以下事项：

```text
不得训练真实新模型
不得调参或搜索真实模型
不得新增正式策略收益结论
不得运行会被解释为 alpha / return evidence 的 replay
不得切默认策略或 default candidate
不得触发 provider refresh / publish
不得切 accepted latest
不得写 monitor config / scan / alerts
不得连接 broker、quick-trade 或 orders
不得把 smoke artifact 接入前端默认展示
不得把 smoke artifact 写入 production latest pointer
不得修改 Agent prompt/tool/action
不得修改 scripts/run_daily_tw_stock_auto_update.py
```

允许：

```text
新增 smoke-only registry entry
新增 smoke-only model signal adapter fixture
新增 smoke-only strategy dependency fixture
新增/扩展 validator 以识别 smoke-only 标记
新增 golden positive/negative samples
复跑 M0-M4R regression
输出 M5 执行报告
```

## 8. M5 验收门槛

M5 完成后必须证明：

```text
新增模型 smoke 不需要改策略或回放引擎
新增策略 smoke 不需要改 replay execution 主体
registry regression 能识别 smoke-only
validator 能拒绝缺少 smoke_only / not_valid_strategy_evidence / no_replay_return_conclusion / not_default_candidate 的样例
ModelSignalArtifact compatibility check 通过
StrategyDependency check 通过
OrderIntentArtifact compatibility check 如适用则通过
没有 replay return conclusion
没有 default switch
没有 provider refresh/publish/accepted latest
没有 broker/order/quick-trade/monitor writes
Agent 未扩权
```

建议 M5 执行报告命名：

```text
docs/tw_modular_contracts/PHASEM5_DRY_RUN_ONBOARDING_SMOKE_EXECUTION_REPORT_CN.md
```

建议 M5 审查命令至少包括：

```bash
python scripts/run_tw_modular_contract_regression.py --json
python scripts/validate_tw_frontend_readonly_m4.py --json
python scripts/validate_tw_daily_orchestrator_m3.py --audit-script scripts/run_daily_tw_stock_auto_update.py --json
<M5 smoke validator command>
<M5 smoke golden sample tests>
```

如果 M5 产物中出现任何真实训练、真实收益结论、默认候选、latest pointer 更新或生产写入口，应直接判定 M5 不通过。
