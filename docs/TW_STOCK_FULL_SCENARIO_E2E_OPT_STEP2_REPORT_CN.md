# 全场景 E2E 优化 Step 2 报告：前端每日自动更新状态面板

生成时间：2026-06-03
对应文档：`docs/TW_STOCK_FULL_SCENARIO_E2E_OPT_STEP2_EXECUTION_CN.md`

## 1. 本步目标

在 `/tw-stock-monitor` 页面新增“每日自动更新状态”只读面板，基于 Step 1 API 展示：

- latest accepted asof
- pending asof
- FinMind raw 更新状态
- Yahoo/Scrapling qlib 目标日期与当前最大日期
- `fresh_data_wait` 解释
- next retry hint
- 研究只读边界

本步没有新增任何写操作按钮，没有触发 qlib publish / normal publish / EOD publish，也没有连接 broker 或下单。

## 2. 新增/修改文件

修改：

- `frontend/src/api/tw-stock.js`
- `frontend/src/views/tw-stock-monitor/index.vue`

新增：

- `frontend/tests/unit/tw-stock-daily-auto-update-panel-check.mjs`
- `docs/TW_STOCK_FULL_SCENARIO_E2E_OPT_STEP2_REPORT_CN.md`

本轮继续依赖 Step 1 已完成文件：

- `backend/app/services/tw_stock_daily_auto_update_status.py`
- `backend/app/routes/tw_stock.py`
- `backend/tests/test_tw_stock_daily_auto_update_status.py`

## 3. API Helper

新增前端只读 helper：

```js
export function getTwStockDailyAutoUpdateStatus () {
  return request({
    url: `${BASE_URL}/quant/ops/daily-auto-update/status`,
    method: 'get'
  })
}
```

静态检查确认该 helper 只使用 GET，未引用 publish、refresh provider、dry-run、broker、quick-trade、order 等危险动作。

## 4. UI 展示字段

面板标题：

```text
每日自動更新狀態
```

展示字段：

- `latest_asof`
- `latest_status`
- `latest_run_id`
- `pending_asof`
- `pending_reason`
- `last_job_status`
- `last_job_started_at`
- `last_job_finished_at`
- `finmind_update_status`
- `finmind_archived_count`
- `yahoo_target_asof`
- `yahoo_date_max`
- `yahoo_missing_asof_count`
- `next_retry_hint`
- `cron_installed_hint`
- `orders_enabled=false`
- `connects_to_broker=false`
- `research_signal_not_order=true`

## 5. 当前真实 API 响应摘要

重启本地后端后，新增 API 返回 HTTP 200。当前真实状态摘要：

```json
{
  "latest_asof": "2026-06-02",
  "latest_status": "accepted",
  "latest_run_id": "option_c_daily_signal_20260602_20260603T031450Z",
  "pending_asof": "2026-06-03",
  "pending_reason": "fresh_data_wait",
  "last_job_status": "fresh_data_wait",
  "finmind_update_status": "success",
  "finmind_archived_count": 1200,
  "yahoo_target_asof": "2026-06-03",
  "yahoo_date_max": "2026-06-02",
  "yahoo_missing_asof_count": 150,
  "fresh_data_wait": true,
  "cron_installed_hint": true
}
```

## 6. fresh_data_wait 文案

面板在 `fresh_data_wait=true` 时展示：

```text
FinMind raw 数据已更新，但 Yahoo/Scrapling qlib 复权数据尚未到目标日期。系统会继续按定时任务重试 pending asof。当前 latest 不更新是正确的保护行为。
```

这能明确告诉用户：当前 latest 没更新到 `2026-06-03` 不是失败，而是 Yahoo/Scrapling 复权数据尚未到目标日期，系统会继续重试。

## 7. 截图路径

Playwright 真实页面截图：

```text
/tmp/quantdinger_tw_step2/tw-stock-daily-auto-update-panel.png
/tmp/quantdinger_tw_step2/tw-stock-daily-auto-update-panel-crop.png
```

截图验证的面板文本包含：

- `latest accepted asof 2026-06-02`
- `pending asof 2026-06-03`
- `fresh_data_wait`
- `FinMind raw success archived_count=1200`
- `Yahoo/Scrapling qlib 目标 2026-06-03，当前最大日期 2026-06-02`
- `缺失 150 支`
- `当前 latest 不更新是正确的保护行为`

## 8. 网络请求审计

Playwright 面板验证中记录危险写请求：

```json
{
  "dangerous_request_count": 0
}
```

本轮面板没有触发：

- quick-trade 下单
- broker 连接
- qlib normal publish
- qlib EOD publish
- refresh provider
- monitor scan-all
- POST/PUT/PATCH/DELETE 危险写请求

## 9. 测试命令与结果

新增 Step 2 静态检查：

```bash
cd frontend
node tests/unit/tw-stock-daily-auto-update-panel-check.mjs
```

结果：

```text
tw-stock daily auto update panel checks passed
```

既有静态检查：

```bash
node tests/unit/tw-stock-monitor-static-check.mjs
node tests/unit/tw-stock-agent-panel-check.mjs
node tests/unit/tw-stock-cross-analysis-check.mjs
node tests/unit/tw-stock-monitor-qlib-ops-check.mjs
```

结果：

```text
tw-stock-monitor static checks passed
tw-stock agent panel checks passed
tw-stock cross-analysis checks passed
tw-stock-monitor qlib ops checks passed
```

前端构建：

```bash
corepack pnpm build
```

结果：

```text
✓ built
```

后端 Step 1 API 回归：

```bash
python -m pytest backend/tests/test_tw_stock_daily_auto_update_status.py -q
```

结果：

```text
5 passed
```

Playwright 真实页面验证：

```text
面板可见；latest/pending/fresh_data_wait/FinMind/Yahoo 字段可见；dangerous_request_count=0。
```

## 10. 服务状态说明

为了让新增 Step 1 后端 API 在本地服务中生效，本轮重启了后端进程。

当前监听：

- 后端：`127.0.0.1:5000`
- 前端：`127.0.0.1:8000`

后端启动时仍使用只读验证边界相关环境变量：

- `ENABLE_PENDING_ORDER_WORKER=false`
- `ENABLE_PORTFOLIO_MONITOR=false`
- `ENABLE_TW_STOCK_MONITOR_WORKER=false`
- `DISABLE_RESTORE_RUNNING_STRATEGIES=true`
- `POSITION_SYNC_ENABLED=false`
- `USDT_PAY_ENABLED=false`

## 11. 未解决问题

本步未处理以下事项，因为执行文档明确要求不要提前做：

- console warning 清理，留到 Step 3。
- watchlist 草稿回填修复，留到 Step 4。
- full scenario E2E 脚本纳入项目，留到 Step 5。
- 自动更新调度逻辑改造。

当前未发现 Step 2 阻塞问题。

## 12. 验收结论

Step 2 已完成。

- `/tw-stock-monitor` 已新增每日自动更新状态面板。
- 面板能显示 latest asof 和 pending asof。
- `fresh_data_wait=true` 时有明确解释。
- 能展示 FinMind raw 与 Yahoo/Scrapling qlib 差异状态。
- 能展示 next retry hint。
- 页面未新增危险写操作入口。
- 前端 build 通过。
- 静态检查、后端回归、Playwright 真实页面验证均通过。
