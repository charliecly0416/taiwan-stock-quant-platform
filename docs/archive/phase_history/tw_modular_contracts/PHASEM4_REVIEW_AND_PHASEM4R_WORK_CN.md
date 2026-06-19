# Phase M4 审查与 Phase M4R 修复工作文档

生成日期：2026-06-17

## 1. 审查结论

Phase M4 暂不通过，不得进入 Phase M5。

M4 新增的 `ReadonlyStrategySnapshotPanel`、`ReadonlyReplayWindowPanel` 和 `ReplayAuditDetail` 组件边界基本成立；新增 readonly strategy snapshot / readonly replay window API wrapper 使用 GET；截图 artifact 存在；M4 validator 和 M3R script audit 复跑通过。

但 M4 的关键验收目标是证明 replay / strategy readonly workflow 只有 GET，且前端不得调用 POST/PUT/PATCH/DELETE 的 replay/strategy 路由。当前 `/tw-stock-monitor` 页面在 mounted / refreshAll 流程中仍会自动调用旧的 `runTwStockPortfolioReplay()`，该 API 是 POST `/api/tw-stock/rank-tech-cross/portfolio-replay`。M4 validator 和 E2E 没有把这个 POST replay 路由计入 forbidden request，因此执行报告中的 GET-only 结论不成立。

该问题需要进入 Phase M4R 修复。

## 2. 已通过部分

### 2.1 新增 readonly 展示组件边界成立

新增组件：

```text
frontend/src/views/tw-stock-monitor/components/ReadonlyStrategySnapshotPanel.vue
frontend/src/views/tw-stock-monitor/components/ReadonlyReplayWindowPanel.vue
frontend/src/views/tw-stock-monitor/components/ReplayAuditDetail.vue
```

审查确认：

```text
ReadonlyStrategySnapshotPanel 使用 ReplayAuditDetail
ReadonlyReplayWindowPanel 使用 ReplayAuditDetail
ReplayAuditDetail 默认折叠审计字段
主视图优先展示模型、策略、窗口、收益/回撤、交易次数、费用、覆盖状态、审计状态
```

### 2.2 新增 readonly API wrapper 是 GET-only

`frontend/src/api/tw-stock.js` 中新增/相关 wrapper：

```text
getTwStockReadonlyStrategySnapshot -> GET /api/tw-stock/readonly-strategy-snapshot
getTwStockReadonlyReplayWindowIndex -> GET /api/tw-stock/readonly-replay-window-index
getTwStockReadonlyReplayWindow -> GET /api/tw-stock/readonly-replay-window
```

### 2.3 复跑通过项

已复跑：

```bash
python -m py_compile scripts/validate_tw_frontend_readonly_m4.py scripts/run_tw_modular_contract_regression.py
python scripts/validate_tw_frontend_readonly_m4.py --json
python scripts/validate_tw_daily_orchestrator_m3.py --audit-script scripts/run_daily_tw_stock_auto_update.py --json
python scripts/run_tw_modular_contract_regression.py --json
```

结果：

```text
py_compile: pass
M4 validator: ok=true
M3R script audit: ok=true
contract regression: ok=true
```

Node 单元检查在 `frontend/` 工作目录下复跑通过：

```bash
cd frontend
node tests/unit/tw-stock-readonly-strategy-snapshot-check.mjs
node tests/unit/tw-stock-readonly-replay-window-check.mjs
```

结果：

```text
[readonly-strategy-snapshot-check] ok
[readonly-replay-window-check] ok
```

注意：从仓库根目录按报告字面路径运行 `node frontend/tests/unit/...` 会失败，因为测试脚本按 `process.cwd()` 读取 `src/...`。这不是功能阻断，但 M4R 报告必须把执行 cwd 写清楚。

### 2.4 截图 artifact 存在

报告列出的截图存在，尺寸正常：

```text
readonly_strategy_snapshot_desktop_collapsed.png 1440x4553
readonly_strategy_snapshot_desktop_expanded.png 1440x4553
readonly_strategy_snapshot_mobile.png 390x6953
readonly_replay_window_desktop_collapsed.png 1440x4230
readonly_replay_window_desktop_expanded.png 1440x4230
readonly_replay_window_mobile.png 390x6663
```

## 3. 阻塞问题

### M4-BLOCKER-1：页面初始化仍自动触发旧 replay POST，GET-only 结论不成立

严重级别：High

证据：

`frontend/src/views/tw-stock-monitor/index.vue` 在 mounted 中会调用 `loadRankTechPortfolioPanel()`，随后又调用 `refreshAll()`：

```text
frontend/src/views/tw-stock-monitor/index.vue:2520-2538
mounted()
  loadReadonlyStrategySnapshot()
  loadReadonlyReplayWindowIndex()
  loadReadonlyReplayWindow()
  loadRankTechPortfolioPanel()
  ...
  refreshAll()
```

`refreshAll()` 也会再次调用 `loadRankTechPortfolioPanel()`：

```text
frontend/src/views/tw-stock-monitor/index.vue:3890-3906
refreshAll()
  Promise.all([... loadReadonlyReplayWindow(), loadRankTechPortfolioPanel(), ...])
```

`loadRankTechPortfolioPanel()` 会调用 `loadPortfolioReplay()`：

```text
frontend/src/views/tw-stock-monitor/index.vue:3014-3016
async loadRankTechPortfolioPanel () {
  await Promise.all([this.loadRankTechCrossLatest(), this.loadPortfolioReplay()])
}
```

`loadPortfolioReplay()` 调用 `runTwStockPortfolioReplay()`：

```text
frontend/src/views/tw-stock-monitor/index.vue:2974-2991
const data = this.unwrap(await runTwStockPortfolioReplay({...}))
```

而 `runTwStockPortfolioReplay()` 是 POST：

```text
frontend/src/api/tw-stock.js:196-204
url: /api/tw-stock/rank-tech-cross/portfolio-replay
method: post
persist: false
```

这违反 M4 工作文档中的禁止事项：

```text
不得调用 POST/PUT/PATCH/DELETE 的 replay/strategy 路由
E2E/network audit 证明 replay/strategy readonly workflow 只有 GET
```

即使该 POST 标记为 `persist=false`、`simulation_only`，它仍然是 replay/strategy POST，不满足 M4 的 GET-only 前端验收门槛。

### M4-BLOCKER-2：M4 validator 和 E2E 未覆盖旧 replay POST，存在 false positive

严重级别：High

证据：

`scripts/validate_tw_frontend_readonly_m4.py` 的 GET-only 检查只覆盖三个新增 readonly API wrapper：

```text
scripts/validate_tw_frontend_readonly_m4.py:21-25
getTwStockReadonlyStrategySnapshot
getTwStockReadonlyReplayWindowIndex
getTwStockReadonlyReplayWindow
```

`network_audit.forbidden_request_count` 只统计 provider/broker，不包含 replay/strategy POST：

```text
scripts/validate_tw_frontend_readonly_m4.py:224-232
forbidden_request_count = provider_publish_refresh + broker_orders
```

因此 validator 返回：

```text
ok=true
readonly_workflow_only_get=true
forbidden_request_count=0
```

但它没有发现 `runTwStockPortfolioReplay()` 的 POST 路径。

E2E 也存在同样盲点。`frontend/tests/e2e/tw-stock-readonly-replay-window-readonly.mjs` 和 `frontend/tests/e2e/tw-stock-readonly-strategy-snapshot-readonly.mjs` 都 mock 了：

```text
**/api/tw-stock/rank-tech-cross/portfolio-replay**
```

但 forbidden request 捕获条件只拦截 readonly endpoint 非 GET、monitor write、broker、accepted_latest、provider_publish 等，不拦截 portfolio replay POST。因此页面即使自动发出 POST `/rank-tech-cross/portfolio-replay`，E2E 仍可能通过。

### M4-BLOCKER-3：执行报告的 network audit artifact 不等同于真实 E2E network audit

严重级别：Medium

报告将以下文件称为 GET-only network audit artifact：

```text
data_tw/experiments/extended_oos_qlib_orthogonal_ltr/modular_contract_regression/m4_frontend_readonly_validation.json
```

但该文件来自静态 validator，不是 E2E 运行时请求记录。实际 E2E 脚本只在内存中断言 `forbiddenRequests.length === 0`，没有输出包含完整 requests、method、url、forbidden_requests 的 `network_audit.json`。

M4R 应补充真实 E2E network audit artifact，至少包括：

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
failed_response_count
```

## 4. 台股只读安全边界审查

### Findings

Critical：未发现 broker/order/quick-trade/target-position、provider publish/refresh、accepted latest 默认路径暴露在新增 readonly snapshot/window 组件中。

High：发现 `/tw-stock-monitor` 页面初始化流程仍自动触发 replay/strategy POST `/api/tw-stock/rank-tech-cross/portfolio-replay`，与 M4 GET-only 验收冲突。

Medium：M4 validator 和 E2E network audit 对 replay/strategy POST 覆盖不足，导致 false positive；报告中的 network audit artifact 不是完整运行时请求审计。

Low：M4 报告中的 Node 单元命令未明确 `frontend/` 工作目录，按仓库根目录复跑会失败。

### Verdict

M4 暂不通过。新增 readonly 组件本身可以保留，但 GET-only 验收 gate 必须修复。

## 5. Phase M4R 修复范围

M4R 目标：让 `/tw-stock-monitor` 的 M4 readonly acceptance workflow 真正满足 GET-only，并让 validator/E2E 能阻断所有 replay/strategy POST。

必须完成：

1. 移除 M4 readonly acceptance path 中的自动 POST。
   - `mounted()` 和 `refreshAll()` 不得自动调用 `loadRankTechPortfolioPanel()`，除非该方法已改为 GET-only。
   - `loadPortfolioReplay()` 不得在页面初始加载或 readonly refresh 中自动触发 POST。
   - 旧 portfolio replay POST 如需保留，必须改为显式人工按钮触发、从 M4 readonly acceptance path 排除，并在文案中保持历史模拟/只读语义；但 M4 的自动验收 workflow 仍必须只 GET。

2. 修复 M4 validator。
   - 将 `runTwStockPortfolioReplay`、`runTwStockReadonlyBacktest`、所有 replay/strategy POST wrapper 纳入 forbidden scan。
   - `forbidden_request_count` 必须包含 replay/strategy write count。
   - `readonly_workflow_only_get=true` 必须证明 mounted / refreshAll / readonly panels 的调用链没有 POST。
   - 如果页面保留旧写操作方法，validator 必须区分“非自动、非 M4 acceptance path”的手动操作和自动 workflow。

3. 修复 E2E network audit。
   - 捕获并输出完整 `network_audit.json`。
   - 禁止 POST/PUT/PATCH/DELETE `/api/tw-stock/rank-tech-cross/portfolio-replay`。
   - 禁止 POST `/api/indicator/backtest`。
   - 禁止 monitor config / scan / alerts writes。
   - 禁止 broker / quick-trade / orders。
   - 禁止 qlib provider refresh / publish / accepted latest。
   - `forbidden_request_count` 必须为 0。

4. 修复执行报告命令。
   - Node 单元检查必须明确 `cd frontend` 或把测试脚本改为基于仓库根目录解析路径。
   - E2E 命令必须说明工作目录、静态服务 URL 和 artifact 输出路径。

5. 保持 M3R 边界。
   - 不得修改 `scripts/run_daily_tw_stock_auto_update.py`。
   - 不得暴露 `--enable-legacy-provider-publish` 或 `TW_DAILY_AUTO_ENABLE_LEGACY_PROVIDER_PUBLISH`。
   - 不得修改 Agent prompt/tool/action。

## 6. M4R 验收门槛

M4R 完成后，至少复跑：

```bash
python -m py_compile scripts/validate_tw_frontend_readonly_m4.py scripts/run_tw_modular_contract_regression.py
python scripts/validate_tw_frontend_readonly_m4.py --json
python scripts/validate_tw_daily_orchestrator_m3.py --audit-script scripts/run_daily_tw_stock_auto_update.py --json
python scripts/run_tw_modular_contract_regression.py --json
cd frontend && node tests/unit/tw-stock-readonly-strategy-snapshot-check.mjs
cd frontend && node tests/unit/tw-stock-readonly-replay-window-check.mjs
corepack pnpm build
<run M4 readonly E2E and emit network_audit.json>
```

必须满足：

```text
M4 validator: ok=true
readonly_workflow_only_get=true
forbidden_request_count=0
replay_strategy_write_count=0
monitor_config_write_count=0
monitor_scan_post_count=0
monitor_alerts_write_count=0
ops_provider_publish_refresh_accepted_latest_request_count=0
broker_quick_trade_orders_request_count=0
legacy_provider_gate_not_exposed=true
Agent prompt/tool/action unchanged
M3R script audit still passed
```

如果页面加载 `/tw-stock-monitor` 或点击 M4 readonly refresh/query 控件时仍出现任何 replay/strategy POST，则 M4R 不通过。
