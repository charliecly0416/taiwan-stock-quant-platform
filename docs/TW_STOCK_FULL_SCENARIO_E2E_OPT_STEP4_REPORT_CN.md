# 全场景 E2E 优化 Step 4 报告：watchlist 草稿回填复核与修正

生成时间：2026-06-04
对应文档：`docs/TW_STOCK_FULL_SCENARIO_E2E_OPT_STEP4_EXECUTION_CN.md`

## 1. 本步目标

复核并修正 `/tw-stock-monitor` 中 qlib TopN 研究排序的观察草稿链路：

```text
qlib Top30 行 -> 加入观察 -> 研究观察草稿 -> 填入监控配置 -> monitor config symbols 包含目标股票
```

本步没有改动 qlib accepted latest、daily auto update、Agent、cross-analysis、数据拉取、自动更新调度或交易能力。

## 2. 新增/修改文件

修改：

- `frontend/src/views/tw-stock-monitor/index.vue`
- `frontend/tests/unit/tw-stock-monitor-local-smoke.mjs`

新增：

- `frontend/tests/unit/tw-stock-watchlist-draft-check.mjs`
- `docs/TW_STOCK_FULL_SCENARIO_E2E_OPT_STEP4_REPORT_CN.md`

## 3. 根因判断

判断结论：测试缺陷。

真实页面回填逻辑已经可用：`fillMonitorConfigFromQlibDraft()` 会合并既有 `config.symbols` 与 `qlibWatchDraft`，写入 `configForm.symbolsText`，并打开监控配置 drawer。

此前 smoke 失败的关键原因是测试读取方式不稳定：它通过 `document.querySelectorAll(textarea)` 或第一个 `textarea` 判断 symbols，页面中同时存在 Agent 输入框、notes textarea、配置 symbols textarea，容易读错输入框并误判为回填失败。

## 4. 修复说明

### 稳定选择器

新增以下 `data-testid`：

```text
data-testid="qlib-signal-table"
data-testid="qlib-watch-add"
data-testid="qlib-watch-draft"
data-testid="qlib-watch-fill-config"
data-testid="monitor-config-drawer"
data-testid="monitor-config-symbols"
```

测试现在优先使用 `getByTestId()`，不再依赖第一个 textarea 或页面文案顺序。

### smoke 更新

`frontend/tests/unit/tw-stock-monitor-local-smoke.mjs` 的草稿回填段已改为：

- 点击 `qlib-watch-add`。
- 截图记录回填前草稿。
- 点击 `qlib-watch-fill-config`。
- 等待 `monitor-config-drawer`。
- 只读取 `monitor-config-symbols` 的 input value。
- 断言回填动作没有保存配置、没有触发 scan、没有触碰 alerts、没有运行只读回测。

同时修正了原 smoke 中一处 alerts 计数断言参数错误，使其真正比较回填前后的 alerts 请求计数。

### 专项静态检查

新增 `frontend/tests/unit/tw-stock-watchlist-draft-check.mjs`，覆盖：

- 必要 `data-testid` 存在。
- smoke 使用稳定 test id。
- smoke 不再使用 `querySelectorAll(textarea)` 或 `locator(textarea)`。
- `fillMonitorConfigFromQlibDraft()` 存在。
- 回填方法只写 `symbolsText` 并打开 drawer。
- 回填方法不调用 save、scan、alerts、qlib ops、publish、broker、order、target position 等危险动作。

## 5. Playwright 复核结果

聚焦 Step 4 E2E：

```text
脚本：/tmp/quantdinger_tw_step4_watchlist_draft_e2e.mjs
URL：http://127.0.0.1:8000/#/tw-stock-monitor
目标股票：2330
配置 symbols：2330, 0050, 00878
```

输出摘要：

```json
{
  "targetSymbol": "2330",
  "configSymbolsText": "2330, 0050, 00878",
  "monitorConfigWriteCount": 0,
  "monitorScanPostCount": 0,
  "monitorAlertsRequestCount": 1,
  "readonlyBacktestPostCount": 0,
  "suspiciousRequests": []
}
```

说明：`monitorAlertsRequestCount=1` 来自页面初始只读 alerts 读取；回填前后计数相等，回填动作没有新增 alerts 请求，也没有 alerts 写操作。

完整 local smoke 也已通过：

```json
{
  "watchDraftVisible": true,
  "monitorConfigWriteCount": 0,
  "monitorScanPostCount": 0,
  "monitorAlertsRequestCount": 1,
  "opsDryRunPostCount": 1,
  "qlibLatestVisible": true,
  "qlibHistoryVisible": true,
  "qlibOpsVisible": true,
  "qlibHealthVisible": true,
  "readonlyBacktestPanelVisible": true,
  "rowClickChangedSymbol": true
}
```

## 6. 截图路径

聚焦 Step 4 截图：

```text
/tmp/quantdinger_tw_step4_focus/watchlist-draft-before-fill.png
/tmp/quantdinger_tw_step4_focus/watchlist-draft-after-fill.png
```

完整 smoke 截图：

```text
/tmp/quantdinger_tw_step4/watchlist-draft-before-fill.png
/tmp/quantdinger_tw_step4/watchlist-draft-after-fill.png
/tmp/quantdinger_tw_step4/latest.png
/tmp/quantdinger_tw_step4/historical-accepted.png
/tmp/quantdinger_tw_step4/historical-blocked-or-wait-state.png
/tmp/quantdinger_tw_step4/readonly-backtest-linkage.png
```

## 7. 网络请求审计

禁止请求检查结果：通过。

未出现：

```text
POST /api/tw-stock/monitor/config
POST /api/tw-stock/monitor/scan
POST /api/tw-stock/quant/ops/* publish/refresh/provider
POST /api/quick-trade/*
POST /api/broker/*
POST /api/*order*
```

回填动作没有：

- 保存 monitor config。
- 触发 monitor scan。
- 触发 alerts 写操作。
- 触发 qlib publish / refresh provider。
- 触发 broker、quick-trade、order、target position。

## 8. 测试命令与结果

静态检查：

```bash
cd frontend
node tests/unit/tw-stock-monitor-static-check.mjs
node tests/unit/tw-stock-daily-auto-update-panel-check.mjs
node tests/unit/tw-stock-console-clean-check.mjs
node tests/unit/tw-stock-agent-panel-check.mjs
node tests/unit/tw-stock-cross-analysis-check.mjs
node tests/unit/tw-stock-monitor-qlib-ops-check.mjs
node tests/unit/tw-stock-watchlist-draft-check.mjs
```

结果：全部通过。

前端构建：

```bash
corepack pnpm build
```

结果：通过，`✓ built`。

Playwright：

```bash
TW_STOCK_MONITOR_BASE_URL=http://127.0.0.1:8000 TW_STOCK_MONITOR_USERNAME=quantdinger TW_STOCK_MONITOR_PASSWORD=123456 TW_STOCK_MONITOR_SCREENSHOT_DIR=/tmp/quantdinger_tw_step4 node tests/unit/tw-stock-monitor-local-smoke.mjs
```

结果：通过。

补充：部分 Node 命令在默认沙箱中出现 `bwrap: loopback: Failed RTM_NEWADDR: Operation not permitted`，已按权限规则提升后重跑并通过。

## 9. 是否仍有未解决问题

本步目标范围内没有未解决问题。

观察草稿回填真实可用，测试选择器已稳定化，Playwright 与静态检查均验证回填不产生保存、扫描、发布、下单等危险写操作。

## 10. 验收结论

Step 4 已完成。

- qlib TopN 可以加入观察草稿。
- 点击「填入監控配置」后，monitor config symbols 包含目标股票 `2330`。
- 回填动作不保存配置。
- 回填动作不触发 scan。
- 回填动作不触发 alerts 写操作。
- 测试不再依赖不稳定 textarea 顺序。
- 前端 build 通过。
- 没有改变 qlib accepted latest、daily auto update、Agent、cross-analysis 业务逻辑。
