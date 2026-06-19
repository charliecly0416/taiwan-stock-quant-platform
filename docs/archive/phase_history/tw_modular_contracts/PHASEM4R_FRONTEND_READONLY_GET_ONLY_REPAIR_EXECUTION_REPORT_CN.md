# Phase M4R Frontend Readonly GET-only 修复执行报告

生成日期：2026-06-17

## 1. 修复结论

Phase M4R 已修复 M4 审查指出的 GET-only 阻断项。`/tw-stock-monitor` 的 M4 readonly acceptance 自动路径不再调用旧的 replay/strategy POST，`mounted()`、`refreshAll()`、readonly strategy snapshot 和 readonly replay window 查询/刷新路径均保持 GET-only。

旧 `runTwStockPortfolioReplay()` 和 `runTwStockReadonlyBacktest()` wrapper 仍保留，但仅作为显式人工操作入口，不属于 M4 readonly acceptance path。M4R 未修改 `scripts/run_daily_tw_stock_auto_update.py`，未触发 provider refresh / publish，未切 accepted latest，未修改 monitor config / scan / alerts，未连接 broker / quick-trade / orders，未扩展 Agent prompt/tool/action。

## 2. 修复内容

### 2.1 移除自动 replay POST

`frontend/src/views/tw-stock-monitor/index.vue` 修复：

```text
mounted(): loadRankTechPortfolioPanel() -> loadRankTechCrossLatest()
refreshAll(): loadRankTechPortfolioPanel() -> loadRankTechCrossLatest()
```

历史模拟参数变化不再自动调用 POST：

```text
handleRankTechReplayControlChange(): 只刷新 rank-tech latest GET
handlePortfolioReplayControlChange(): 清空旧模拟结果并提示手动运行
```

保留的旧历史模拟按钮仍可显式调用 `loadRankTechPortfolioPanel()`，但该人工操作不属于 M4 readonly acceptance 自动验收路径。

### 2.2 Validator 修复

`scripts/validate_tw_frontend_readonly_m4.py` 升级为 `schema_version=m4.0.1`，新增：

```text
replay_strategy_write_wrappers
m4_acceptance_path_audit
network_audit.replay_strategy_write_count
```

validator 现在会识别：

```text
runTwStockPortfolioReplay -> /rank-tech-cross/portfolio-replay -> write wrapper, manual_only_allowed=true
runTwStockReadonlyBacktest -> /api/indicator/backtest -> write wrapper, manual_only_allowed=true
```

并检查以下 M4 acceptance entrypoints 不引用 replay/strategy write path：

```text
mounted
refreshAll
loadReadonlyStrategySnapshot
loadReadonlyReplayWindowIndex
loadReadonlyReplayWindow
handleReadonlyReplayWindowSelect
```

结果：

```text
readonly_workflow_only_get=true
forbidden_request_count=0
replay_strategy_write_count=0
monitor_config_write_count=0
monitor_scan_post_count=0
monitor_alerts_write_count=0
ops_provider_publish_refresh_accepted_latest_request_count=0
broker_quick_trade_orders_request_count=0
legacy_provider_gate_not_exposed=true
```

### 2.3 E2E network audit 修复

两个 M4 readonly E2E 均新增运行时网络审计输出：

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/m4_frontend_readonly/readonly_replay_window_network_audit.json
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/m4_frontend_readonly/readonly_strategy_snapshot_network_audit.json
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/m4_frontend_readonly/network_audit.json
```

审计字段包含：

```text
all_requests
forbidden_requests
forbidden_request_count
monitor_config_write_count
monitor_scan_post_count
monitor_alerts_write_count
ops_provider_publish_refresh_accepted_latest_request_count
replay_strategy_write_count
broker_quick_trade_orders_request_count
failed_responses
failed_response_count
```

运行时结果：

```text
forbidden_request_count=0
replay_strategy_write_count=0
monitor_config_write_count=0
monitor_scan_post_count=0
monitor_alerts_write_count=0
ops_provider_publish_refresh_accepted_latest_request_count=0
broker_quick_trade_orders_request_count=0
failed_response_count=0
```

## 3. 复跑命令与结果

复跑命令：

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

`corepack pnpm build` 后使用 `frontend/dist` 下的 `python -m http.server 5173 --bind 127.0.0.1` 作为静态服务复跑 E2E。Vite dev/preview 在当前环境仍不适合使用，因为 watcher 资源限制会触发 ENOSPC。

## 4. 安全边界确认

M4R 未执行或暴露：

```text
provider refresh
provider publish
accepted latest switch
monitor config save
monitor scan
alerts write
broker
quick-trade
orders
training
new replay conclusion
default strategy switch
Agent prompt/tool/action expansion
--enable-legacy-provider-publish
TW_DAILY_AUTO_ENABLE_LEGACY_PROVIDER_PUBLISH
```

Agent 审计仍为：

```text
agent_related_changed_paths=[]
agent_implementation_untouched=true
agent_contract_placeholder_only=true
agent_forbidden_surface_hits=0
```

M3R script audit 仍保留 legacy provider warning，但默认路径不可达：

```text
default_provider_refresh_reachable=false
default_provider_publish_reachable=false
default_accepted_latest_reachable=false
```

## 5. 残余风险

1. 旧 `portfolio-replay` POST 和 indicator backtest POST 仍存在于手动研究功能中；M4R 只证明它们不在 M4 readonly acceptance 自动路径里。
2. 当前 E2E 使用 Playwright route mock 后端响应；真实部署环境仍应在 release acceptance 时复跑同一网络审计。
3. `scripts/run_daily_tw_stock_auto_update.py` 中 legacy provider gate 的治理状态未由 M4R 改变。

## 6. 结论

Phase M4R 修复完成。M4 readonly acceptance workflow 已满足 GET-only，validator 与 E2E 均能阻断 replay/strategy POST，运行时 network audit 证明 forbidden request count 和 replay strategy write count 均为 0。M4R 可重新提交审查。
