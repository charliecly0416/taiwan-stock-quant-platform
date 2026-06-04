# 台股全场景 E2E 优化最终验收报告

生成时间：2026-06-04
对应文档：`docs/TW_STOCK_FULL_SCENARIO_E2E_OPT_FINAL_ACCEPTANCE_EXECUTION_CN.md`

## 1. 最终验收结论

`TW_STOCK_FULL_SCENARIO_E2E_OPT` 系列 Step1-Step5 已完成最终验收，可以收尾。

验收结果：

- 所有必跑测试通过。
- 全场景 E2E `overall_passed=true`。
- 网络审计禁止请求数量为 `0`。
- console 审计中除已知 Ant Design lazy-load notice 外无 warning/error。
- watchlist 草稿可回填到监控配置 drawer，且不保存、不扫描、不新增 alerts 写入。
- 每日自动更新状态 API 与前端面板保持只读展示边界。
- 报告已明确 fixture E2E 与真实数据更新验证的职责边界。

## 2. Step1-Step5 文件清单与功能摘要

### Step 1：全场景分析与优化计划

新增/涉及文档：

- `docs/TW_STOCK_FULL_SCENARIO_E2E_ANALYSIS_CN.md`
- `docs/TW_STOCK_FULL_SCENARIO_E2E_OPTIMIZATION_PLAN_CN.md`
- `docs/TW_STOCK_FULL_SCENARIO_E2E_OPT_STEP1_REPORT_CN.md`

功能摘要：

- 完成台股 `/tw-stock-monitor` 全功能全场景 Playwright 分析。
- 梳理 qlib accepted latest、daily auto update、watchlist、cross-analysis、Agent、console、E2E 入库的优化路线。

### Step 2：每日自动更新状态 API 与前端面板

新增/修改：

- `backend/app/routes/tw_stock.py`
- `backend/app/services/tw_stock_daily_auto_update_status.py`
- `backend/tests/test_tw_stock_daily_auto_update_status.py`
- `frontend/src/api/tw-stock.js`
- `frontend/src/views/tw-stock-monitor/index.vue`
- `frontend/tests/unit/tw-stock-daily-auto-update-panel-check.mjs`
- `docs/TW_STOCK_FULL_SCENARIO_E2E_OPT_STEP2_EXECUTION_CN.md`
- `docs/TW_STOCK_FULL_SCENARIO_E2E_OPT_STEP2_REPORT_CN.md`

功能摘要：

- 新增只读 daily auto update status API。
- 前端新增每日自动更新状态面板，展示 FinMind raw、Yahoo/Scrapling qlib、pending asof、latest accepted asof、next retry 等状态。
- 面板只读取状态，不触发拉数、publish、accepted latest 切换或交易。

### Step 3：console warning 清理

新增/修改：

- `frontend/src/views/tw-stock-monitor/index.vue`
- `frontend/src/views/agent-tokens/index.vue`
- `frontend/src/views/profile/index.vue`
- `frontend/tests/unit/tw-stock-console-clean-check.mjs`
- `docs/TW_STOCK_FULL_SCENARIO_E2E_OPT_STEP3_EXECUTION_CN.md`
- `docs/TW_STOCK_FULL_SCENARIO_E2E_OPT_STEP3_REPORT_CN.md`

功能摘要：

- 修复 Ant Design Vue DatePicker invalid moment value warning。
- 修复 Vue prop casing warning。
- 保留精确 allowlist：`[antd-pro] NOTICE: Antd use lazy-load.`。
- 未通过全局 console suppression 掩盖问题。

### Step 4：watchlist 草稿回填复核与修正

新增/修改：

- `frontend/src/views/tw-stock-monitor/index.vue`
- `frontend/tests/unit/tw-stock-monitor-local-smoke.mjs`
- `frontend/tests/unit/tw-stock-watchlist-draft-check.mjs`
- `docs/TW_STOCK_FULL_SCENARIO_E2E_OPT_STEP4_EXECUTION_CN.md`
- `docs/TW_STOCK_FULL_SCENARIO_E2E_OPT_STEP4_REPORT_CN.md`

功能摘要：

- 根因判断为测试缺陷：旧 smoke 读取不稳定 textarea。
- 新增稳定 `data-testid`：qlib table、加入观察、草稿、填入配置、config drawer、symbols textarea。
- smoke 改为读取 `monitor-config-symbols`。
- 回填动作不保存 monitor config，不触发 scan，不新增 alerts 写入。

### Step 5：全场景只读 Playwright E2E 入库

新增/修改：

- `frontend/tests/e2e/tw-stock-full-scenario-readonly.mjs`
- `frontend/tests/unit/tw-stock-monitor-local-smoke.mjs`
- `docs/TW_STOCK_FULL_SCENARIO_E2E_OPT_STEP5_EXECUTION_CN.md`
- `docs/TW_STOCK_FULL_SCENARIO_E2E_OPT_STEP5_REPORT_CN.md`

功能摘要：

- 新增项目内可重复运行的全场景只读 Playwright E2E。
- 输出 `summary.json`、`network_audit.json`、`console_audit.json` 和截图。
- 覆盖 qlib、daily auto update、TopN、历史 run、只读回测入口、cross-analysis、Agent、watchlist 回填、图表非空。
- 修正 Step 4 被放宽的中文危险文案检查与 range/window 断言。

## 3. 必跑命令与结果

### 后端

```bash
cd backend
python -m pytest tests/test_tw_stock_daily_auto_update_status.py -q
```

结果：

```text
5 passed in 1.14s
```

### 前端静态检查

```bash
cd frontend
node tests/unit/tw-stock-monitor-static-check.mjs
node tests/unit/tw-stock-daily-auto-update-panel-check.mjs
node tests/unit/tw-stock-console-clean-check.mjs
node tests/unit/tw-stock-watchlist-draft-check.mjs
```

结果：全部通过。

输出：

```text
tw-stock-monitor static checks passed
tw-stock daily auto update panel checks passed
tw-stock console clean static checks passed
tw-stock watchlist draft checks passed
```

### 全场景 E2E

```bash
TW_STOCK_MONITOR_BASE_URL=http://127.0.0.1:8000 TW_STOCK_MONITOR_USERNAME=quantdinger TW_STOCK_MONITOR_PASSWORD=123456 TW_STOCK_FULL_E2E_ARTIFACT_DIR=../data_tw/ops/e2e_full_scenario/final-acceptance node tests/e2e/tw-stock-full-scenario-readonly.mjs
```

结果：通过，`overall_passed=true`。

### 前端构建

```bash
corepack pnpm build
```

结果：通过，`✓ built`。

补充：部分 Node 命令在默认沙箱中可能出现 `bwrap: loopback: Failed RTM_NEWADDR: Operation not permitted`，已按权限规则提升后重跑。

## 4. E2E 产物路径

产物目录：

```text
data_tw/ops/e2e_full_scenario/final-acceptance
```

JSON：

```text
data_tw/ops/e2e_full_scenario/final-acceptance/summary.json
data_tw/ops/e2e_full_scenario/final-acceptance/network_audit.json
data_tw/ops/e2e_full_scenario/final-acceptance/console_audit.json
```

截图：

```text
data_tw/ops/e2e_full_scenario/final-acceptance/qlib-health.png
data_tw/ops/e2e_full_scenario/final-acceptance/daily-auto-update.png
data_tw/ops/e2e_full_scenario/final-acceptance/ops-latest.png
data_tw/ops/e2e_full_scenario/final-acceptance/latest.png
data_tw/ops/e2e_full_scenario/final-acceptance/historical-accepted.png
data_tw/ops/e2e_full_scenario/final-acceptance/historical-blocked-or-wait-state.png
data_tw/ops/e2e_full_scenario/final-acceptance/watchlist-draft-before-fill.png
data_tw/ops/e2e_full_scenario/final-acceptance/watchlist-draft-after-fill.png
data_tw/ops/e2e_full_scenario/final-acceptance/readonly-backtest-linkage.png
```

## 5. summary.json 摘要

```json
{
  "base_url": "http://127.0.0.1:8000",
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

说明：E2E 中 qlib/daily-auto-update 使用 fixture route，所以 `latest_asof=2026-06-01` 是浏览器 fixture 场景值，不代表真实 accepted latest 的最新日期。

## 6. network_audit.json 摘要

```json
{
  "request_count": 194,
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

结论：全场景 E2E 没有触发保存、扫描、alerts 写、qlib dry-run/publish/refresh/provider、quick-trade、broker、order 或 target position。

## 7. console_audit.json 摘要

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

结论：仅有已知 Ant Design / antd-pro lazy-load notice；无非 allowlist warning/error，无 page error。

## 8. 真实只读数据检查结果

执行了两个只读 GET，不触发任何更新任务：

```text
GET http://127.0.0.1:5000/api/tw-stock/quant/ops/daily-auto-update/status
GET http://127.0.0.1:5000/api/tw-stock/quant/signals/latest?bucket=top30
```

返回摘要：

```json
{
  "daily_auto_update_status": {
    "ok": true,
    "status": "ok",
    "latest_asof": "2026-06-02",
    "latest_status": "accepted",
    "latest_run_id": "option_c_daily_signal_20260602_20260603T031450Z"
  },
  "latest_signals_top30": {
    "ok": true,
    "status": "accepted",
    "asof": "2026-06-02",
    "run_id": "option_c_daily_signal_20260602_20260603T031450Z",
    "bucket": "top30",
    "top30_count": 30,
    "top50_count": 50
  }
}
```

结论：真实只读 API 当前一致指向 `option_c_daily_signal_20260602_20260603T031450Z`，`asof/latest_asof=2026-06-02`，状态为 accepted。

## 9. Fixture E2E 与真实数据更新职责边界

最终验收明确以下边界：

- fixture E2E 验证前端闭环、交互稳定性、console/network 审计和只读安全边界。
- 真实 Yahoo/Scrapling/FinMind 是否更新到最新交易日，应由每日自动更新 runner、accepted latest 文件、daily auto update status API 的真实运行结果确认。
- 浏览器 E2E 不负责触发真实数据拉取、provider publish、accepted latest 切换或自动更新任务。
- 真实数据检查仅允许 GET；本次只读 GET 已确认 daily status 与 latest signals 当前一致。

## 10. 是否建议合并/提交/收尾

建议收尾，并可进入代码审查/提交阶段。

收尾依据：

- Step1-Step5 报告齐全。
- 后端只读状态 API 测试通过。
- 前端静态检查通过。
- 全场景只读 E2E 入库并通过。
- `summary.json` 显示 `overall_passed=true`。
- `network_audit.json` 显示禁止请求为 0。
- `console_audit.json` 显示非 allowlist issue 为 0。
- 真实只读 GET 显示 daily status 与 latest signals accepted run 一致。

注意：当前工作区仍包含 Step1-Step5 的未提交修改和新增文件，合并前应按项目流程 review diff 后统一提交。

## 11. 最终状态

最终验收通过。

没有发现未解决阻塞，也没有新增业务功能需求。
