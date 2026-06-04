# 全场景 E2E 优化 Step 2 执行文档：前端每日自动更新状态面板

## 1. 本步目标

基于 Step 1 已完成的只读后端 API：

```text
GET /api/tw-stock/quant/ops/daily-auto-update/status
```

在 `/tw-stock-monitor` 页面新增“每日自动更新状态”面板，让用户可以直接在前端看到：

- latest accepted 日期
- pending asof
- FinMind raw 数据是否已更新
- Yahoo/Scrapling qlib 数据是否已到目标日期
- 当前是否处于 `fresh_data_wait`
- 系统是否会继续自动重试

本步重点是提升闭环可见性，不做任何写操作。

## 2. 强制边界

本步不得引入：

- 下单按钮
- broker 连接按钮
- qlib publish / normal publish / EOD publish 按钮
- 自动 refresh provider 按钮
- 自动触发 FinMind/Yahoo 拉取的前端按钮
- 任何 POST 写操作

面板必须是只读展示。

必须继续展示或保留研究边界语义：

```text
orders_enabled=false
connects_to_broker=false
research_signal_not_order=true
```

## 3. 涉及文件建议

预计需要修改：

```text
frontend/src/api/tw-stock.js
frontend/src/views/tw-stock-monitor/index.vue
frontend/tests/unit/tw-stock-monitor-static-check.mjs
```

如有必要可新增：

```text
frontend/tests/unit/tw-stock-daily-auto-update-panel-check.mjs
```

完成后必须新增报告：

```text
docs/TW_STOCK_FULL_SCENARIO_E2E_OPT_STEP2_REPORT_CN.md
```

## 4. API Helper 要求

在 `frontend/src/api/tw-stock.js` 中新增 helper，例如：

```js
export function getTwStockDailyAutoUpdateStatus () {
  return request({
    url: '/tw-stock/quant/ops/daily-auto-update/status',
    method: 'get'
  })
}
```

要求：

- 只能使用 GET。
- helper 内不得引用 `publish`、`refresh`、`dry-run`、`broker`、`quick-trade`、`order` 等危险动作。
- 命名应清晰表达“daily auto update status”。

## 5. UI 面板位置

建议放在 `/tw-stock-monitor` 页面中 qlib 数据状态区域附近，原因：

- 用户看到 qlib latest 状态时，也能理解为什么 latest 没有更新到 pending 日期。
- `fresh_data_wait` 与 qlib provider/accepted latest 强相关。

建议标题：

```text
每日自动更新状态
```

或繁体页面保持：

```text
每日自動更新狀態
```

## 6. 面板展示字段

从 API 响应读取并展示以下字段：

### 核心状态

- `latest_asof`
- `latest_status`
- `latest_run_id`
- `pending_asof`
- `pending_reason`
- `last_job_status`
- `last_job_started_at`
- `last_job_finished_at`

### FinMind raw 状态

- `finmind_update_status`
- `finmind_archived_count`

建议文案：

```text
FinMind raw：success，archived_count=1200
```

### Yahoo/Scrapling qlib 状态

- `yahoo_target_asof`
- `yahoo_date_max`
- `yahoo_missing_asof_count`
- `fresh_data_wait`

建议文案：

```text
Yahoo/Scrapling qlib：目标 2026-06-03，当前最大日期 2026-06-02，缺失 150 支。
```

### 重试状态

- `next_retry_hint`
- `cron_installed_hint`

注意：`cron_installed_hint` 只是“检测到 cron 配置/日志痕迹”，不是严格系统 crontab 证明。前端文案不要写成“系统 cron 已绝对安装”。

推荐文案：

```text
检测到自动更新计划配置或日志，系统会继续按配置重试。
```

如果为 false：

```text
未检测到自动更新计划配置或日志，请检查 cron/systemd 安装。
```

## 7. fresh_data_wait 文案要求

当 `fresh_data_wait=true` 时，必须给出用户可理解解释：

```text
FinMind raw 数据已更新，但 Yahoo/Scrapling qlib 复权数据尚未到目标日期。系统会继续按定时任务重试 pending asof。当前 latest 不更新是正确的保护行为。
```

这个解释很重要，避免用户误以为系统失败。

## 8. 状态颜色建议

可使用 Ant Design tag 或 alert：

- `daily_auto_update_passed`：绿色
- `already_up_to_date`：绿色或蓝色
- `fresh_data_wait`：橙色
- `provider_publish_failed`：红色
- `accepted_latest_failed`：红色
- 无 latest / 无 job：灰色

颜色只是辅助，文本必须完整。

## 9. 空状态和异常状态

必须处理：

- API 请求失败
- 无 latest
- 无 pending
- 无 last job
- cron hint 为 false
- warnings 非空

要求：

- 页面不能崩溃。
- 不能显示 `undefined` / `null` 作为主要文案。
- warnings 可用小字或 tag 展示。

## 10. 测试要求

至少完成以下测试之一：

### 方案 A：扩展现有静态检查

修改：

```text
frontend/tests/unit/tw-stock-monitor-static-check.mjs
```

检查：

- API helper 名称存在。
- 页面包含“每日自动更新状态”相关文案。
- 页面包含 `fresh_data_wait` 解释文案。
- 页面不包含危险动作按钮或危险 endpoint。

### 方案 B：新增独立静态检查

新增：

```text
frontend/tests/unit/tw-stock-daily-auto-update-panel-check.mjs
```

检查内容同上。

### 推荐附加浏览器测试

如时间允许，基于 mock route 或真实后端跑 Playwright，确认：

- 面板可见。
- pending asof 可见。
- latest asof 可见。
- fresh_data_wait 文案可见。
- dangerous request count 为 0。

## 11. 必跑命令

执行者至少需要运行：

```bash
cd frontend
node tests/unit/tw-stock-monitor-static-check.mjs
node tests/unit/tw-stock-agent-panel-check.mjs
node tests/unit/tw-stock-cross-analysis-check.mjs
node tests/unit/tw-stock-monitor-qlib-ops-check.mjs
corepack pnpm build
```

如果新增了独立检查脚本，也要运行：

```bash
node tests/unit/tw-stock-daily-auto-update-panel-check.mjs
```

如修改了后端字段或 route，也要补跑：

```bash
cd ..
python -m pytest backend/tests/test_tw_stock_daily_auto_update_status.py -q
```

## 12. 验收标准

Step 2 完成必须满足：

1. `/tw-stock-monitor` 有每日自动更新状态面板。
2. 面板能展示 latest asof 和 pending asof。
3. `fresh_data_wait=true` 时有明确解释。
4. 能展示 FinMind raw 与 Yahoo/Scrapling qlib 的差异状态。
5. 能展示 next retry hint。
6. 页面不新增任何危险写操作入口。
7. 前端 build 通过。
8. 静态检查或 E2E 检查通过。

## 13. 报告要求

完成后写：

```text
docs/TW_STOCK_FULL_SCENARIO_E2E_OPT_STEP2_REPORT_CN.md
```

报告必须包含：

- 新增/修改文件列表
- 面板截图路径
- API 响应摘要
- UI 展示字段说明
- `fresh_data_wait` 文案截图或文字
- 网络请求审计：是否有 dangerous request
- 测试命令和结果
- 是否存在未解决问题

## 14. 不要提前做的事

本步不要做：

- console warning 清理，这属于 Step 3。
- watchlist 草稿回填修复，这属于 Step 4。
- full scenario E2E 脚本纳入项目，这属于 Step 5。
- 自动更新脚本调度逻辑改造，除非发现 Step 1 API 字段阻塞 Step 2。

本步只聚焦“前端可见的自动更新状态面板”。
