# 台股量化项目 Phase 1-6 交接总结

> 更新提示：Phase 7 和 Phase 8 已完成，最新交接入口请优先读取 `docs/TAIWAN_STOCK_HANDOFF_PHASE1_8_CN.md`。本文保留为 Phase 1-6 历史交接记录。

更新时间：2026-05-24

## 1. 给新窗口的接续指令

新开窗口后可以直接说：

```text
请读取 docs/TAIWAN_STOCK_HANDOFF_PHASE1_6_CN.md，并从 Phase 7 继续。继续遵守：只做台股趋势研究、自动监控提醒和人工决策，不自动交易，不连接 broker，不启用 live。
```

当前仓库：`/path/to/taiwan-stock-quant-platform`

当前主线：把 QuantDinger 扩展为台股量化研究系统。现阶段重点已经从交易执行转为：

- 台股/ETF 数据获取与质量校验。
- 日线趋势研究。
- 自动监控提醒。
- 趋势历史与可视化。
- 人工复盘、人工决策。

明确不要做：

- 不自动买卖。
- 不连接 IBKR 或任何 broker。
- 不提交 paper/live order。
- 不把系统输出当作投资建议。
- `AGENT_LIVE_TRADING_ENABLED` 保持 `false`。

## 2. 环境与关键配置

工作目录：

```bash
cd /path/to/taiwan-stock-quant-platform
```

Python：

```bash
python
```

本地 PostgreSQL：

```bash
DATABASE_URL=postgresql://user:password@127.0.0.1:5432/quantdinger
```

推荐安全环境变量：

```bash
AGENT_LIVE_TRADING_ENABLED=false
ENABLE_PENDING_ORDER_WORKER=false
ENABLE_PORTFOLIO_MONITOR=false
ENABLE_TW_STOCK_MONITOR_WORKER=false
```

说明：`ENABLE_TW_STOCK_MONITOR_WORKER` 默认关闭。Phase 6D 已提供独立 cron/worker 脚本，生产上更推荐用独立脚本，不建议让 API 进程同时承担后台扫描。

## 3. 数据来源与时效性

当前台股数据主要来自 FinMind：

- 日线：`TaiwanStockPrice`
- 除权息：`TaiwanStockDividendResult`
- 三大法人：`TaiwanStockInstitutionalInvestorsBuySell`
- 融资融券：`TaiwanStockMarginPurchaseShortSale`
- 月营收：`TaiwanStockMonthRevenue`
- 估值：`TaiwanStockPER`

真实性判断：这些是真实市场数据，适合日频研究和盘后趋势监控。

时效性边界：当前不是盘中实时行情系统。趋势分析基于日线 K 线，页面和 worker 的自动刷新也是日频趋势研究，不是秒级/分钟级行情。

官方校验：

- TWSE 上市样本已用官方 `STOCK_DAY_ALL` 做最新交易日对账。
- 最近验证到的官方最新交易日：`2026-05-22`。
- TPEx 官方 OpenAPI 在当前环境访问不稳定，TPEx 对账保持后置；如后续扩大上柜股票，建议继续补官方对账或由用户本地比对。

## 4. Phase 1-6 完成概览

### Phase 1：台股日线研究与回测

完成：

- 新增 `TWStockDataSource`。
- 注册 `TWStock` 数据源和市场别名。
- 支持 `2330`、`2330.TW`、`TWSE:2330`、`TPEX:6488` 等格式。
- 支持 `1D` 和 `1W` K 线。
- 接入市场列表、Agent market list、可见市场配置、热门台股标的。
- 回测入口增加台股默认手续费、滑点、TWD、Asia/Taipei、lot size 等假设。

### Phase 2：数据归档与质量

完成：

- 新增日线归档、除权息、三大法人、融资融券、月营收、估值表。
- 新增盘后总控脚本 `update_tw_stock_daily.py`。
- 新增 Qlib normalized CSV 导出脚本 `export_tw_qlib_normalized.py`。
- 支持 raw / forward_adjusted / backward_adjusted 复权模式。
- TWSE 样本完成官方最新日交叉校验。

### Phase 3：Universe、排名、调仓和组合模拟

完成：

- 台股 universe 构建。
- 横截面排名。
- 再平衡计划。
- 组合模拟。
- ETF 和股票可扩展基础。

### Phase 4：Paper 执行链路与 IBKR 前置清单

完成：

- paper-only 订单预览、提交桥接、验证、报告 bundle。
- IBKR paper/live preflight 和文档。
- 但根据用户后续目标，自动交易和 IBKR live promotion 已暂停，不是当前主线。

当前使用原则：Phase 4 保留为未来可选能力，不在 Phase 7 默认启用。

### Phase 5：研究版台股趋势监控

完成：

- `GET /api/tw-stock/trend`
- `GET /api/tw-stock/trends`
- `GET /api/tw-stock/monitor` 轻量监控页面。
- 监控配置表：`qd_tw_stock_monitor_configs`
- 提醒表：`qd_tw_stock_monitor_alerts`
- 状态表：`qd_tw_stock_monitor_states`
- 扫描日志：`qd_tw_stock_monitor_scan_logs`
- 可选 API 同进程 worker：默认关闭。
- Phase 5 smoke 配置已清理，`default` 配置保留。

验收文档：`docs/TW_STOCK_PHASE5_ACCEPTANCE_CN.md`

### Phase 6：提醒、趋势历史、可视化和独立 worker

完成：

- Phase 6A：站内通知桥接，台股 alert 同步写入 `qd_strategy_notifications`。
- Phase 6B：趋势历史表 `qd_tw_stock_trend_history` 和 history API。
- Phase 6C：页面趋势分数曲线、提醒过滤、人工状态按钮。
- Phase 6D：独立脚本 `run_tw_stock_monitor_scan.py`，支持 cron `--once` 和 loop worker。

验收文档：`docs/TW_STOCK_PHASE6_ACCEPTANCE_CN.md`

## 5. 当前可用入口

趋势 API：

```text
GET /api/tw-stock/trend?symbol=2330&limit=120
GET /api/tw-stock/trends?symbols=2330,0050,00878&limit=120
```

监控页面：

```text
GET /api/tw-stock/monitor
```

监控配置：

```text
GET /api/tw-stock/monitor/config
POST /api/tw-stock/monitor/config
```

提醒：

```text
GET /api/tw-stock/monitor/alerts?limit=50&unread_only=false
POST /api/tw-stock/monitor/alerts
PUT /api/tw-stock/monitor/alerts/<id>
```

扫描：

```text
POST /api/tw-stock/monitor/scan
POST /api/tw-stock/monitor/scan-all
GET /api/tw-stock/monitor/scan-logs?limit=20
```

趋势历史：

```text
GET /api/tw-stock/monitor/history?symbol=2330&limit=120
```

独立 cron 单次扫描：

```bash
DATABASE_URL=postgresql://user:password@127.0.0.1:5432/quantdinger \
AGENT_LIVE_TRADING_ENABLED=false \
ENABLE_PENDING_ORDER_WORKER=false \
ENABLE_PORTFOLIO_MONITOR=false \
ENABLE_TW_STOCK_MONITOR_WORKER=false \
PYTHONPATH=backend \
python \
  backend/scripts/run_tw_stock_monitor_scan.py --once --trigger-source cron
```

独立 loop worker：

```bash
DATABASE_URL=postgresql://user:password@127.0.0.1:5432/quantdinger \
AGENT_LIVE_TRADING_ENABLED=false \
ENABLE_PENDING_ORDER_WORKER=false \
ENABLE_PORTFOLIO_MONITOR=false \
ENABLE_TW_STOCK_MONITOR_WORKER=false \
PYTHONPATH=backend \
python \
  backend/scripts/run_tw_stock_monitor_scan.py --loop --interval-sec 900 --trigger-source systemd
```

## 6. 关键文件

核心代码：

- `backend/app/data_sources/tw_stock.py`
- `backend/app/routes/tw_stock.py`
- `backend/app/services/tw_stock_trend.py`
- `backend/app/services/tw_stock_monitor_worker.py`
- `backend/scripts/run_tw_stock_monitor_scan.py`
- `backend/migrations/init.sql`

Phase 2 数据脚本：

- `backend/scripts/sync_tw_stock_symbols.py`
- `backend/scripts/archive_tw_stock_daily.py`
- `backend/scripts/validate_tw_stock_daily.py`
- `backend/scripts/update_tw_stock_daily.py`
- `backend/scripts/export_tw_qlib_normalized.py`

重点测试：

- `backend/tests/test_tw_stock_trend_api.py`
- `backend/tests/test_tw_stock_monitor_worker.py`
- `backend/tests/test_run_tw_stock_monitor_scan.py`
- `backend/tests/test_tw_stock_data_source.py`
- `backend/tests/test_tw_stock_kline_api.py`
- `backend/tests/test_market_symbols_seed_sql.py`

核心文档：

- `docs/TAIWAN_STOCK_QUANT_RESEARCH_CN.md`
- `docs/TAIWAN_STOCK_PHASE_CHECKPOINT_CN.md`
- `docs/TW_STOCK_MONITOR_DEPLOYMENT_CN.md`
- `docs/TW_STOCK_PHASE5_ACCEPTANCE_CN.md`
- `docs/TW_STOCK_PHASE6_ACCEPTANCE_CN.md`
- `docs/TW_STOCK_PHASE7_ACCEPTANCE_CN.md`
- `docs/TW_STOCK_PHASE8_ACCEPTANCE_CN.md`
- 本文档：`docs/TAIWAN_STOCK_HANDOFF_PHASE1_6_CN.md`

## 7. 最近验证命令

Phase 6 收尾回归：

```bash
python -m pytest   backend/tests/test_run_tw_stock_monitor_scan.py   backend/tests/test_tw_stock_trend_api.py   backend/tests/test_tw_stock_monitor_worker.py   backend/tests/test_tw_stock_kline_api.py   backend/tests/test_tw_stock_data_source.py   backend/tests/test_market_symbols_seed_sql.py -q
```

最近结果：`52 passed in 1.01s`

脚本 CLI smoke：

```bash
PYTHONPATH=backend python   backend/scripts/run_tw_stock_monitor_scan.py --help
```

页面模板 smoke：

- `trendChart=True`
- `history_api=True`
- `alert_filter=True`
- `manual_watch=True`
- `read_only_copy=True`

端口状态：验收时确认 `5000` 端口无遗留监听。

## 8. 已知限制和风险

不阻塞 Phase 7，但需要记住：

- 当前不是盘中实时行情系统。
- 趋势历史从 Phase 6B 之后的 scan 开始积累。
- 页面仍是 Flask 托管轻量页面，不是正式 Vue 前端。
- 外部 Telegram / Email / Webhook 尚未实现。
- 独立扫描脚本目前复用 route 层 scan-all 函数，后续可下沉到 service 层。
- TPEx 官方对账仍不稳定。
- 当前仓库有大量未提交改动和未跟踪文件，继续工作时不要随意 revert/reset。

## 9. Phase 7 建议路线

建议 Phase 7 不再扩大交易链路，继续围绕“趋势研究产品化”推进。

当前进度：

- `Phase 7A` 已启动：新增独立页面 e2e/smoke 脚本 `backend/scripts/check_tw_stock_monitor_page_e2e.py`。
- 该脚本启动 mock Flask 服务，不依赖真实 PostgreSQL 或 FinMind，用 Playwright CLI 打开 `/api/tw-stock/monitor` 并等待趋势数据行后生成截图；配套测试覆盖只读 API 契约。
- 新增测试 `backend/tests/test_tw_stock_monitor_page_e2e_script.py`，覆盖 mock 页面和只读 API 契约。
- `Phase 7B` 已启动：台股 monitor alert 生成后支持显式启用的 Webhook best-effort 推送，默认关闭，失败不影响站内提醒或扫描。
- `Phase 7D` 已启动：新增 `backend/app/services/tw_stock_monitor.py`，扫描核心下沉到 service；route 保留兼容包装给 API、worker、cron 调用。
- `Phase 7D` 运维补强：新增 `backend/scripts/cleanup_tw_stock_monitor_history.py`，支持 dry-run/apply 清理趋势历史和扫描日志；部署文档补 systemd、logrotate、清理 cron 示例。
- `Phase 7C` 已启动：`build_tw_stock_universe.py` 输出增加 research-only `monitor_config`，并支持 `--monitor-config-json` 导出默认 disabled 的监控配置，供人工审核后导入。
- `Phase 7C` 导入补强：新增 `backend/scripts/import_tw_stock_monitor_config.py`，默认 dry-run，`--apply` 才 upsert 监控配置；不会扫描、提醒或下单。
- `Phase 7C` 预检补强：新增 `backend/scripts/preflight_tw_stock_monitor_config.py`，导入前只读检查每个 symbol 的趋势和质量，输出 failed/warning 汇总；不写库、不提醒、不下单。
- `Phase 7` 已形成验收文档：`docs/TW_STOCK_PHASE7_ACCEPTANCE_CN.md`。
- `Phase 8A` 已启动：新增 `backend/tests/test_tw_stock_monitor_safety_audit.py`，自动审计台股监控研究路径不得导入/调用 quick_trade、IBKR、live trading、order submission 等交易层。
- `Phase 8B` 已启动：新增 `backend/scripts/verify_tw_stock_research_stack.py`，一键运行台股研究栈验收测试，可选 `--with-page-smoke` 跑 Playwright 截图 smoke。
- `Phase 8C` 已启动：新增 `.github/workflows/tw-stock-research.yml`，在台股相关代码/文档变更时运行离线一键验收；不安装浏览器、不启动服务、不启用 live/worker。
- `Phase 8D` 已启动：更新 `.github/PULL_REQUEST_TEMPLATE.md`，加入台股研究栈安全 checklist；新增 `test_pr_template_safety_checklist.py` 并纳入一键验收。
- `Phase 8E` 已启动：修正 `.github/workflows/tw-stock-research.yml` path filter，覆盖 PR 模板、PR 模板静态测试和 workflow 静态测试本身。
- `Phase 8` 已形成验收文档：`docs/TW_STOCK_PHASE8_ACCEPTANCE_CN.md`。

Phase 7A 验证命令：

```bash
PYTHONPATH=backend \
python \
  backend/scripts/check_tw_stock_monitor_page_e2e.py \
  --screenshot /tmp/tw_stock_monitor_phase7a.png
```

测试：

```bash
python -m pytest \
  backend/tests/test_tw_stock_monitor_page_e2e_script.py \
  backend/tests/test_tw_stock_trend_api.py \
  backend/tests/test_run_tw_stock_monitor_scan.py \
  -q
```

可选子阶段：

1. `Phase 7A`：正式前端或更可靠的页面 e2e
   - 给 `/api/tw-stock/monitor` 做 Playwright 截图和 canvas 非空检查。
   - 或接入正式 Vue 前端。

2. `Phase 7B`：外部通知通道
   - Webhook 已有最小实现：`TW_STOCK_MONITOR_WEBHOOK_ENABLED=true` + `TW_STOCK_MONITOR_WEBHOOK_URL=...`。
   - 后续再做 Telegram / Email，或给正式前端增加台股 Webhook 配置入口。
   - 仍然只提醒，不自动交易。

3. `Phase 7C`：扩大股票和 ETF universe
   - Universe builder 已支持从 `qd_market_symbols` 候选按流动性筛选，并输出 `monitor_config`。
   - 可用 `--include-etf` 纳入 ETF，用 `--monitor-config-json /tmp/tw_stock_monitor.json` 导出默认 disabled 的监控配置，人工审核后可 POST 到 `/api/tw-stock/monitor/config`，先用 `preflight_tw_stock_monitor_config.py` 预检，再用 `import_tw_stock_monitor_config.py --dry-run/--apply` 导入。
   - TPEx 上柜股票先保持谨慎，补官方对账或由用户本地比对。

4. `Phase 7D`：架构收敛
   - 扫描核心已下沉到 `app.services.tw_stock_monitor`。
   - API、worker、cron 仍通过 route 兼容包装调用，包装内部统一委托 service，保留现有测试 monkeypatch 行为。
   - systemd unit 模板、日志轮转和历史清理策略已补在 `docs/TW_STOCK_MONITOR_DEPLOYMENT_CN.md`。

## 10. 新窗口启动前检查

新窗口继续前，建议先运行：

```bash
git status --short
```

不要执行：

```bash
git reset --hard
git checkout -- .
```

除非用户明确要求清理工作区。

如果需要确认安全边界，检索：

```bash
rg -n "orders_enabled|quick_trade|broker|IBKR|run_tw_stock_monitor_scan"   backend/app/routes/tw_stock.py   backend/app/services/tw_stock_monitor_worker.py   backend/scripts/run_tw_stock_monitor_scan.py
```

预期：台股趋势监控路径只出现 `orders_enabled=false` 和“不连接 broker/IBKR”的文档或注释，不应出现实际下单调用。
