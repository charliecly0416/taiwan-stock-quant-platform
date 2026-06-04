# 全场景 E2E 优化 Step 5 报告：全场景只读 Playwright 仿真测试入库

生成时间：2026-06-04
对应文档：`docs/TW_STOCK_FULL_SCENARIO_E2E_OPT_STEP5_EXECUTION_CN.md`

## 1. 本步目标

将此前临时执行的台股全场景浏览器仿真整理为项目内可重复运行的只读 Playwright 脚本，覆盖 qlib accepted latest、FinMind/Yahoo 每日自动更新状态、TopN、历史 accepted run、只读回测入口、cross-analysis、Agent 上下文、watchlist 草稿回填和关键图表非空检查。

本步没有触发数据拉取、provider publish、accepted latest 切换、monitor scan、monitor config 保存、broker、quick-trade、order 或 target position。

## 2. 新增/修改文件

新增：

- `frontend/tests/e2e/tw-stock-full-scenario-readonly.mjs`
- `docs/TW_STOCK_FULL_SCENARIO_E2E_OPT_STEP5_REPORT_CN.md`

修改：

- `frontend/tests/unit/tw-stock-monitor-local-smoke.mjs`

继续沿用 Step 4 新增文件：

- `frontend/tests/unit/tw-stock-watchlist-draft-check.mjs`

## 3. Step 4 两处弱化点修正

### 中文危险交易文案检查

已恢复中文危险词检查，包含：

```text
下單
买入
買入
卖出
賣出
提交订单
提交訂單
```

为了避免误伤只读回测面板和 Agent 常见问题入口，检查时会从 DOM clone 中排除：

```text
.readonly-backtest-card
.tw-stock-agent-panel
```

原因：Step 5 同时要求 Agent 上下文可见，且 Agent 面板本身会出现“买入/卖出建议”类问题入口；只读回测也可能展示交易术语作为历史模拟字段。危险词检查仍覆盖主页面业务区域，防止真实交易入口泄漏。

### 30D range/window 断言

已移除 `waitForTimeout(500)` 作为关键 UI 断言。

现在的检查方式：

- 点击图表 toolbar 中的 `30D`。
- 等待 `30D` radio button 进入 checked 状态。
- 验证窗口信息仍可见。
- 验证价格 canvas 有尺寸且非空。

趋势表行点击后的等待也从固定 timeout 改为等待 `.selected-symbol-main strong` 的 symbol 发生变化。

## 4. 新增 E2E 脚本

脚本路径：

```text
frontend/tests/e2e/tw-stock-full-scenario-readonly.mjs
```

支持环境变量：

```text
TW_STOCK_MONITOR_BASE_URL
TW_STOCK_MONITOR_USERNAME
TW_STOCK_MONITOR_PASSWORD
TW_STOCK_FULL_E2E_ARTIFACT_DIR
```

默认值：

```text
TW_STOCK_MONITOR_BASE_URL=http://127.0.0.1:8000
TW_STOCK_MONITOR_USERNAME=quantdinger
TW_STOCK_MONITOR_PASSWORD=123456
TW_STOCK_FULL_E2E_ARTIFACT_DIR=../data_tw/ops/e2e_full_scenario/<timestamp>
```

产物目录位于 `data_tw/ops/e2e_full_scenario/...`，已被仓库 `.gitignore` 的 `/data_tw/` 覆盖，不会提交截图或临时 JSON。

## 5. E2E 覆盖场景

已覆盖：

- 登录并进入 `/#/tw-stock-monitor`。
- qlib accepted latest / health / TopN 表格。
- qlib accepted asof、run_id、status、rows。
- Top30/Top50 切换。
- 历史 accepted run 与 wait-state run 展示边界。
- qlib ops latest 状态面板可见，但不点击 dry-run。
- 每日自动更新状态面板，包括 FinMind raw、Yahoo/Scrapling qlib、pending asof、latest accepted asof。
- TopN row 加入观察草稿。
- 草稿填入监控配置 drawer，symbols 包含 `2330`。
- 只读回测入口打开，但不自动运行回测 POST。
- cross-analysis 区块可见。
- Agent 上下文面板可见。
- 价格 canvas 与趋势分数 canvas 非空。
- 趋势表点击后 selected symbol 从 `2330` 变为 `0050`。
- console/network 审计文件输出。

说明：E2E 使用本地前后端服务，同时对 qlib latest/health/runs、qlib ops latest、daily auto update status 使用 Playwright fixture route，避免测试依赖真实 qlib 产物实时状态；不会 mock 页面本体或前端交互。

## 6. 网络请求审计结果

产物：

```text
data_tw/ops/e2e_full_scenario/step5-current/network_audit.json
```

摘要：

```json
{
  "request_count": 192,
  "forbidden_request_count": 0,
  "forbidden_requests": [],
  "suspicious_requests": [],
  "monitor_config_write_count": 0,
  "monitor_scan_post_count": 0,
  "monitor_alerts_request_count": 1,
  "monitor_alerts_write_count": 0,
  "readonly_backtest_post_count": 0,
  "ops_dry_run_post_count": 0,
  "failed_response_count": 0
}
```

结论：全程没有触发保存配置、扫描、alerts 写入、qlib dry-run/publish/refresh/provider、quick-trade、broker、order 或 target position 写请求。

## 7. Console 审计结果

产物：

```text
data_tw/ops/e2e_full_scenario/step5-current/console_audit.json
```

摘要：

```json
{
  "console_issue_count": 1,
  "console_issues": [
    {
      "type": "warning",
      "text": "[antd-pro] NOTICE: Antd use lazy-load."
    }
  ],
  "non_allowed_console_issue_count": 0,
  "page_error_count": 0
}
```

结论：仅保留 Step 3 已记录的 Ant Design / antd-pro lazy-load notice；没有非 allowlist warning/error，没有 page error。

## 8. Summary 与截图产物

Summary：

```text
data_tw/ops/e2e_full_scenario/step5-current/summary.json
```

摘要：

```json
{
  "latest_asof": "2026-06-01",
  "selected_symbol": "0050",
  "topn_visible": true,
  "daily_auto_update_visible": true,
  "cross_analysis_visible": true,
  "agent_context_visible": true,
  "watchlist_refill_ok": true,
  "chart_nonblank_ok": true,
  "forbidden_request_count": 0,
  "console_error_count": 0,
  "non_allowed_console_issue_count": 0,
  "overall_passed": true
}
```

截图：

```text
data_tw/ops/e2e_full_scenario/step5-current/qlib-health.png
data_tw/ops/e2e_full_scenario/step5-current/daily-auto-update.png
data_tw/ops/e2e_full_scenario/step5-current/ops-latest.png
data_tw/ops/e2e_full_scenario/step5-current/latest.png
data_tw/ops/e2e_full_scenario/step5-current/historical-accepted.png
data_tw/ops/e2e_full_scenario/step5-current/historical-blocked-or-wait-state.png
data_tw/ops/e2e_full_scenario/step5-current/watchlist-draft-before-fill.png
data_tw/ops/e2e_full_scenario/step5-current/watchlist-draft-after-fill.png
data_tw/ops/e2e_full_scenario/step5-current/readonly-backtest-linkage.png
```

## 9. 服务与账号

本轮使用现有本地服务：

```text
frontend: http://127.0.0.1:8000
backend:  http://127.0.0.1:5000
```

测试账号：

```text
TW_STOCK_MONITOR_USERNAME=quantdinger
TW_STOCK_MONITOR_PASSWORD=123456
```

未重新启动服务；执行前确认 `127.0.0.1:8000` 和 `127.0.0.1:5000` 均在监听。

## 10. 测试命令与结果

必跑静态检查：

```bash
cd frontend
node tests/unit/tw-stock-monitor-static-check.mjs
node tests/unit/tw-stock-daily-auto-update-panel-check.mjs
node tests/unit/tw-stock-console-clean-check.mjs
node tests/unit/tw-stock-watchlist-draft-check.mjs
```

结果：全部通过。

新增 E2E：

```bash
TW_STOCK_MONITOR_BASE_URL=http://127.0.0.1:8000 TW_STOCK_MONITOR_USERNAME=quantdinger TW_STOCK_MONITOR_PASSWORD=123456 TW_STOCK_FULL_E2E_ARTIFACT_DIR=../data_tw/ops/e2e_full_scenario/step5-current node tests/e2e/tw-stock-full-scenario-readonly.mjs
```

结果：通过，`overall_passed=true`。

前端构建：

```bash
corepack pnpm build
```

结果：通过，`✓ built`。

补充验证：

```bash
TW_STOCK_MONITOR_BASE_URL=http://127.0.0.1:8000 TW_STOCK_MONITOR_USERNAME=quantdinger TW_STOCK_MONITOR_PASSWORD=123456 TW_STOCK_MONITOR_SCREENSHOT_DIR=/tmp/quantdinger_tw_step5_local_smoke node tests/unit/tw-stock-monitor-local-smoke.mjs
```

结果：通过。

补充：部分 Node 命令在默认沙箱中可能出现 `bwrap: loopback: Failed RTM_NEWADDR: Operation not permitted`，已按权限规则提升后重跑。

## 11. 未覆盖或需人工确认

本步没有未解决的验收问题。

仍需人工确认的边界：

- 新增 E2E 使用 fixture route 固定 qlib/daily-auto-update 状态，因此它验证前端闭环和安全边界，不验证当天真实 Yahoo/Scrapling/FinMind 产物是否最新。
- Agent 不调用真实 OpenAI，只验证上下文面板与只读入口。
- E2E 不点击任何保存、扫描、publish、refresh、dry-run 或下单入口。

## 12. 验收结论

Step 5 已完成。

- 全场景只读 Playwright 脚本已入库。
- Step 4 两处弱化点已修正。
- E2E 可重复输出 summary/network/console/screenshot 产物。
- E2E 覆盖 qlib、daily auto update、TopN、历史 run、只读回测入口、cross-analysis、Agent、watchlist 回填和图表非空。
- 网络审计禁止请求为 0。
- console 审计非 allowlist issue 为 0。
- 前端 build 通过。
