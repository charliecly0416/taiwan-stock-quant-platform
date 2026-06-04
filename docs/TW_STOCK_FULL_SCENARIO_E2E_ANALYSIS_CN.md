# 台股量化平台全功能 Playwright 场景测试与优化分析

生成时间：2026-06-03
测试环境：本机后端 `http://127.0.0.1:5000`，前端 `http://127.0.0.1:8000`
测试账号：`quantdinger`
证据目录：`data_tw/ops/e2e_full_scenario/2026-06-03_173921098Z/`

## 1. 测试边界

本次测试覆盖真实前后端服务、真实数据库与当前台股 qlib 产物，但刻意保持研究只读边界：

- 不连接 broker。
- 不提交 paper/live order。
- 不触发 quick trade 下单。
- 不触发 qlib 正式发布、EOD 发布、normal publish。
- 不触发 monitor scan-all 或生产状态批量写操作。

因此，本报告判断的是“平台功能可达、数据读链路完整、研究边界清晰、自动更新配置有效”，不是券商实盘交易验收。

## 2. Playwright 覆盖结果

执行脚本：

```bash
node data_tw/ops/e2e_full_scenario/full_scenario_check.mjs
```

第二轮有效结果：

```json
{
  "routes_ok": 16,
  "routes_total": 16,
  "api_ok": 15,
  "api_total": 15,
  "console_issue_count": 8,
  "page_error_count": 0,
  "failed_response_count": 0,
  "dangerous_request_count": 3,
  "screenshots": 19
}
```

### 前端路由

以下 16 个前端场景均可达，并完成截图：

- `/tw-stock-monitor`
- `/ai-asset-analysis`
- `/indicator-community`
- `/indicator-ide`
- `/strategy-live`
- `/trading-bot`
- `/broker-accounts`
- `/profile`
- `/billing`
- `/user-manage`
- `/agent-tokens`
- `/settings`
- `/dashboard`，重定向到 `/trading-bot`
- `/indicator-analysis`，重定向到 `/indicator-ide`
- `/backtest-center`，重定向到 `/indicator-ide`
- `/trading-assistant`，重定向到 `/strategy-live`

### 台股监控深度场景

`/tw-stock-monitor` 页面通过以下检查：

- 页面主视图可加载，显示 `台股趨勢監控`。
- qlib Option C 研究排序可见。
- `orders_enabled=false`、`Research`、`Human Review`、`Not order` 等研究边界提示可见。
- qlib 数据状态可见，当前 accepted asof 为 `2026-06-02`。
- qlib 历史 run 区块可见。
- Top 30 / Top 50 分桶切换可操作。
- Agent 面板可见，并尝试发送结构化研究问题。
- 交叉分析与趋势依赖说明可见。

### API 读链路

15 个 API 检查全部通过：

- `/api/health`
- `/api/tw-stock/quant/signals/health`
- `/api/tw-stock/quant/signals/latest?bucket=top30`
- `/api/tw-stock/quant/signals/latest?bucket=top50`
- `/api/tw-stock/quant/signals/runs`
- `/api/tw-stock/cross-analysis/latest`
- `/api/tw-stock/cross-analysis/symbol/2330`
- `/api/tw-stock/agent/context`
- `/api/tw-stock/trends?symbols=2330,0050,00878`
- `/api/tw-stock/monitor/config`
- `/api/tw-stock/monitor/alerts`
- `/api/tw-stock/monitor/scan-logs`
- `/api/tw-stock/monitor/history?symbol=2330`
- `/api/tw-stock/quant/ops/option-c/latest`
- `/api/indicator/backtest/tw-stock/templates`

关键数据状态：

- qlib latest：`accepted`
- qlib latest asof：`2026-06-02`
- latest run_id：`option_c_daily_signal_20260602_20260603T031450Z`
- Top30 数量：30
- Top50 数量：50
- runs 数量：18
- cross-analysis latest：`accepted`
- 所有 qlib / cross-analysis / ops latest 返回均带有研究边界 flags，例如 `orders_enabled=false`、`connects_to_broker=false`、`writes_orders=false`、`research_signal_not_order=true`。

## 3. 自动更新状态

当前 cron 已安装，内容位于：

```text
data_tw/ops/daily_auto_update/tw-daily-auto-update.installed.cron
```

服务器 cron 使用 UTC：

```cron
30 8,10,12,14,16,18,20 * * 1-5 ...
```

对应台北时间为周一至周五 16:30、18:30、20:30、22:30，以及跨午夜重试窗口 00:30、02:30、04:30。

最新手动自动更新 job：

```text
data_tw/ops/daily_auto_update/daily_tw_stock_auto_update_20260603_20260603T171533Z/job.json
```

状态：

- `status`: `fresh_data_wait`
- `asof`: `2026-06-03`
- FinMind daily raw 更新：成功
- FinMind archived_count：1200
- Yahoo/Scrapling：150/150 股票抓取成功
- Yahoo/Scrapling 最大日期：`2026-06-02`
- 目标日期 `2026-06-03` 缺失：150/150
- provider publish：未触发
- latest_signal_updated：false
- pending asof：`2026-06-03`

结论：自动化脚本已配置为全自动重试。当前没有发布 `2026-06-03` 是正确行为，因为 Yahoo/Scrapling 当时还未提供完整目标日期数据。系统保留 `pending_asof.json`，后续定时任务会继续补拉同一个 asof，而不是直接跳过。

## 4. 发现的问题与风险

### P1：交易相关页面会自动请求 quick-trade 只读历史

Playwright 记录到：

- `GET /src/api/quick-trade.js`
- `GET /api/quick-trade/history?limit=5`

这不是下单请求，也没有触发 POST；但“全平台全场景”访问交易机器人页面时，前端会自动读取 quick-trade 历史。建议把 quick-trade 历史读取也纳入明确的只读安全审计列表，并在测试中区分 `GET history` 与下单类 POST，避免误报。

### P2：控制台存在 UI 警告

本次无页面崩溃，但控制台有 8 条警告/错误级日志：

- Ant Design lazy-load notice。
- DatePicker 收到 invalid moment value。
- Vue prop 使用 `readonly`，但组件声明为 `readOnly`，应使用 `read-only`。

这些不阻断主流程，但会降低长期可维护性，也会污染 E2E 质量门禁。建议优先修复 DatePicker value 与 `readonly` prop 命名。

### P2：Agent 真实回答能力依赖后端配置

页面 Agent 面板可见，`/agent/context` 可读；真实 chat 能否产生高质量回答取决于后端 LLM 配置。当前测试以结构化上下文和 UI 可用性为主，没有把外部 LLM 成功率作为硬性验收。

### P2：`cross-analysis/symbol/2330` 返回 `not_in_latest_qlib_top50`

接口本身 200 且语义正确，但从用户视角看，2330 是常见重点股票，当前不在 latest top50 时页面应提供更明确解释：这是模型当期排序结果，不是数据缺失，也不是股票不可分析。

### P3：现有本地 smoke 脚本存在 watchlist 草稿回填断言失败

此前运行 `frontend/tests/unit/tw-stock-monitor-local-smoke.mjs` 时失败在：

```text
draft symbols were not filled into monitor config form
```

这可能是测试断言滞后，也可能是 qlib 观察草稿到 monitor config 的 UI 回填存在真实问题。建议单独复核这个交互：从 qlib TopN 生成观察草稿后，打开配置表单，确认 symbols 是否被填入且不会误保存。

### P3：自动更新状态没有在前端形成完整运维视图

当前 `fresh_data_wait`、`pending_asof.json`、cron 下次重试时间都在文件和日志里可查，但前端没有一个一眼可见的“自动更新状态面板”。用户需要依赖命令行判断 Yahoo 是否会继续重试。

## 5. 优化建议

### 数据与自动化

- 增加“每日自动更新状态”前端面板：显示 latest asof、pending asof、上次 job、FinMind 状态、Yahoo 最大日期、下次 cron 预计时间。
- 给 `fresh_data_wait` 增加用户可读解释：说明 Yahoo 当前只有 `2026-06-02`，目标是 `2026-06-03`，系统会自动重试。
- 增加 cron/systemd 自检 API：检查 crontab 是否安装、lock 文件是否异常、最近 cron.log 是否有执行记录。
- 增加 Yahoo 与 FinMind 新鲜度对比：FinMind raw 已更新但 qlib Yahoo 未更新时，在 UI 上明确“raw 已到，复权 qlib 等待中”。
- 增加 pending asof 成功清除事件记录：方便确认跨午夜补拉最终闭环。

### 前端可测试性

- 为核心控件增加稳定 `data-testid`：Top30/Top50、历史 run 行、Agent 输入、配置抽屉、只读回测入口。
- 将危险动作按钮统一加安全属性，例如 `data-dangerous-action="order|publish|broker-connect"`，E2E 可以自动阻断。
- 建立 console clean 门禁：至少把 DatePicker invalid value 和 Vue prop casing 警告清掉。
- 增加移动端截图测试：台股监控页面信息密度高，移动端更容易出现表格、按钮和标签溢出。

### 研究工作流

- 增加“研究复盘日志”：用户可对 qlib TopN 标记观察、排除、复盘结论，并保留 asof/run_id。
- 增加“候选池标签”：例如 AI/半导体/金融/高波动/数据异常，支持导出 CSV。
- 增加“模型与趋势一致性看板”：按 focus_watch、model_trend_divergence、data_review_required 分组。
- 增加“信号稳定性”面板：展示同一股票最近 N 个 run 的 rank、score、bucket 变化。
- 增加“个股解释卡”：显示 qlib rank、趋势、数据新鲜度、风险提示、引用 run_id。

### 新功能方向

- 自动更新时间线：把 FinMind、Yahoo fetch、normalized validation、provider rebuild、accepted latest publish 串成一条可视化 timeline。
- 数据源 SLA 热力图：按股票显示 Yahoo/FinMind 是否当天可用、是否延迟、是否 fallback。
- Agent 引用约束：Agent 回答必须引用 `run_id`、`asof`、接口或 artifact，避免泛化回答。
- 安全 dry-run 队列：允许管理员触发只读 dry-run，但所有正式发布动作必须二次确认并记录审计。
- 研究订阅提醒：当 watched symbols 进入 Top30、出现趋势背离、或 latest asof 更新时通知用户。
- 回测预设入口：从 qlib row 打开只读回测模板，默认不下单、不联动 broker，只生成研究报告。

## 6. 建议的下一步

1. 修复控制台警告：DatePicker invalid value、`readonly` prop casing。
2. 复核 watchlist 草稿回填失败点，判断是测试需要更新还是 UI 真实缺陷。
3. 在前端加入自动更新状态面板，优先展示 `fresh_data_wait` 与下次重试时间。
4. 把 `full_scenario_check.mjs` 纳入本地或 CI smoke，但默认保持只读安全边界。
5. 为交易、发布、券商连接类动作建立统一危险动作拦截测试。
