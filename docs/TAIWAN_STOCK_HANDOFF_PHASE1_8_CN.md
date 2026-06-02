# 台股量化项目 Phase 1-8 交接总结

更新时间：2026-05-24

## 1. 给新窗口的接续指令

新开窗口后可以直接说：

```text
请读取 docs/TAIWAN_STOCK_HANDOFF_PHASE1_8_CN.md 和 docs/TW_STOCK_PHASE9_ACCEPTANCE_CN.md，并从 Phase 10A 继续。继续遵守：只做台股趋势研究、自动监控提醒和人工决策，不自动交易，不连接 broker，不启用 live。前端源码已在 /path/to/taiwan-stock-quant-platform-Vue；如果后续做正式 Vue 台股页面，应在该前端仓中推进，并使用独立前端 workflow，不要混入后端台股研究 CI。
```

当前仓库：`/path/to/taiwan-stock-quant-platform`

当前主线：把 QuantDinger 扩展为台股量化研究系统。现阶段重点是：

- 台股/ETF 数据获取与质量校验。
- 日线趋势研究。
- 自动监控提醒。
- 趋势历史与轻量可视化。
- Universe 到监控配置的人工审核链路。
- 离线安全审计、CI 验收和 PR checklist。
- 人工复盘、人工决策。

明确不要做：

- 不自动买卖。
- 不连接 IBKR 或任何 broker。
- 不提交 paper/live order。
- 不把系统输出当作投资建议。
- `AGENT_LIVE_TRADING_ENABLED` 保持 `false`。

## 2. 环境与安全配置

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

说明：`ENABLE_TW_STOCK_MONITOR_WORKER` 默认关闭。生产上更推荐用独立 cron 或 systemd worker 运行台股扫描，不建议让 API 进程同时承担后台扫描。

## 3. 数据来源与时效性

当前台股数据主要来自 FinMind：

- 日线：`TaiwanStockPrice`
- 除权息：`TaiwanStockDividendResult`
- 三大法人：`TaiwanStockInstitutionalInvestorsBuySell`
- 融资融券：`TaiwanStockMarginPurchaseShortSale`
- 月营收：`TaiwanStockMonthRevenue`
- 估值：`TaiwanStockPER`

真实性判断：这些是真实市场数据，适合日频研究和盘后趋势监控。

时效性边界：当前不是盘中实时行情系统。趋势分析基于日线 K 线，页面和 worker 的自动刷新也是日频趋势研究，不是秒级或分钟级行情。

官方校验：

- TWSE 上市样本已用官方 `STOCK_DAY_ALL` 做最新交易日对账。
- 最近验证到的官方最新交易日：`2026-05-22`。
- TPEx 官方 OpenAPI 在当前环境访问不稳定，TPEx 对账保持后置；如后续扩大上柜股票，建议继续补官方对账或由用户本地比对。

## 4. Phase 1-8 完成概览

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

当前使用原则：Phase 4 保留为未来可选能力，不在当前台股研究监控主线默认启用。

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

验收文档：`docs/TW_STOCK_PHASE5_ACCEPTANCE_CN.md`

### Phase 6：提醒、趋势历史、可视化和独立 worker

完成：

- Phase 6A：站内通知桥接，台股 alert 同步写入 `qd_strategy_notifications`。
- Phase 6B：趋势历史表 `qd_tw_stock_trend_history` 和 history API。
- Phase 6C：页面趋势分数曲线、提醒过滤、人工状态按钮。
- Phase 6D：独立脚本 `run_tw_stock_monitor_scan.py`，支持 cron `--once` 和 loop worker。

验收文档：`docs/TW_STOCK_PHASE6_ACCEPTANCE_CN.md`

### Phase 7：趋势研究产品化

完成：

- Phase 7A：页面 e2e / smoke 脚本 `check_tw_stock_monitor_page_e2e.py`。
- Phase 7B：可选 Webhook 外部提醒，默认关闭，失败不影响站内提醒或扫描。
- Phase 7C：universe 输出 research-only `monitor_config`，支持预检、dry-run 导入和人工审核后 apply。
- Phase 7D：扫描核心下沉到 `app.services.tw_stock_monitor`，并新增趋势历史/扫描日志清理脚本。
- 部署文档补 systemd、logrotate、cleanup cron、Webhook 和 universe 导入流程。

验收文档：`docs/TW_STOCK_PHASE7_ACCEPTANCE_CN.md`

### Phase 8：安全边界与持续验收自动化

完成：

- Phase 8A：安全审计测试，禁止台股监控研究路径导入或调用 quick-trade、IBKR、live trading、order submission 等交易层入口。
- Phase 8B：一键验收脚本 `verify_tw_stock_research_stack.py`，输出固定安全声明。
- Phase 8C：GitHub Actions workflow `.github/workflows/tw-stock-research.yml`。
- Phase 8D：PR 模板新增 `TWStock Research Safety` checklist。
- Phase 8E：CI path filter 覆盖 PR 模板、workflow 和静态测试本身。

验收文档：`docs/TW_STOCK_PHASE8_ACCEPTANCE_CN.md`

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

## 6. 常用运维命令

独立 cron 单次扫描：

```bash
DATABASE_URL=postgresql://user:password@127.0.0.1:5432/quantdinger AGENT_LIVE_TRADING_ENABLED=false ENABLE_PENDING_ORDER_WORKER=false ENABLE_PORTFOLIO_MONITOR=false ENABLE_TW_STOCK_MONITOR_WORKER=false PYTHONPATH=backend python   backend/scripts/run_tw_stock_monitor_scan.py --once --trigger-source cron
```

独立 loop worker：

```bash
DATABASE_URL=postgresql://user:password@127.0.0.1:5432/quantdinger AGENT_LIVE_TRADING_ENABLED=false ENABLE_PENDING_ORDER_WORKER=false ENABLE_PORTFOLIO_MONITOR=false ENABLE_TW_STOCK_MONITOR_WORKER=false PYTHONPATH=backend python   backend/scripts/run_tw_stock_monitor_scan.py --loop --interval-sec 900 --trigger-source systemd
```

扩大观察列表的人工审核链路：

```bash
PYTHONPATH=backend python   backend/scripts/build_tw_stock_universe.py   --include-etf --limit-candidates 200 --max-universe 50   --monitor-config-json /tmp/tw_stock_monitor_universe.json

PYTHONPATH=backend python   backend/scripts/preflight_tw_stock_monitor_config.py   --input-json /tmp/tw_stock_monitor_universe.json --limit 120

PYTHONPATH=backend python   backend/scripts/import_tw_stock_monitor_config.py   --input-json /tmp/tw_stock_monitor_universe.json --dry-run
```

确认后才使用 `--apply` 写入配置。

历史清理：

```bash
PYTHONPATH=backend python   backend/scripts/cleanup_tw_stock_monitor_history.py --help
```

## 7. 一键验收

推荐每个新窗口或较大变更后先运行：

```bash
PYTHONPATH=backend \
python \
  backend/scripts/verify_tw_stock_research_stack.py
```

最近结果：

- `ok=true`
- `46 passed`
- `orders_enabled=false`
- `writes_production_data=false`
- `connects_to_broker=false`

可选页面 smoke：

```bash
PYTHONPATH=backend \
python \
  backend/scripts/verify_tw_stock_research_stack.py   --with-page-smoke   --screenshot /tmp/tw_stock_monitor_phase8b.png
```

## 8. 关键文件

核心代码：

- `backend/app/data_sources/tw_stock.py`
- `backend/app/routes/tw_stock.py`
- `backend/app/services/tw_stock_trend.py`
- `backend/app/services/tw_stock_monitor.py`
- `backend/app/services/tw_stock_monitor_worker.py`
- `backend/scripts/run_tw_stock_monitor_scan.py`
- `backend/migrations/init.sql`

数据、universe 和运维脚本：

- `backend/scripts/sync_tw_stock_symbols.py`
- `backend/scripts/archive_tw_stock_daily.py`
- `backend/scripts/validate_tw_stock_daily.py`
- `backend/scripts/update_tw_stock_daily.py`
- `backend/scripts/export_tw_qlib_normalized.py`
- `backend/scripts/build_tw_stock_universe.py`
- `backend/scripts/preflight_tw_stock_monitor_config.py`
- `backend/scripts/import_tw_stock_monitor_config.py`
- `backend/scripts/cleanup_tw_stock_monitor_history.py`
- `backend/scripts/check_tw_stock_monitor_page_e2e.py`
- `backend/scripts/verify_tw_stock_research_stack.py`

重点测试：

- `backend/tests/test_tw_stock_trend_api.py`
- `backend/tests/test_tw_stock_monitor_worker.py`
- `backend/tests/test_run_tw_stock_monitor_scan.py`
- `backend/tests/test_tw_stock_monitor_service.py`
- `backend/tests/test_tw_stock_monitor_page_e2e_script.py`
- `backend/tests/test_build_tw_stock_universe.py`
- `backend/tests/test_import_tw_stock_monitor_config.py`
- `backend/tests/test_preflight_tw_stock_monitor_config.py`
- `backend/tests/test_cleanup_tw_stock_monitor_history.py`
- `backend/tests/test_tw_stock_monitor_safety_audit.py`
- `backend/tests/test_verify_tw_stock_research_stack.py`
- `backend/tests/test_tw_stock_research_workflow.py`
- `backend/tests/test_pr_template_safety_checklist.py`

核心文档：

- `docs/TAIWAN_STOCK_QUANT_RESEARCH_CN.md`
- `docs/TAIWAN_STOCK_PHASE_CHECKPOINT_CN.md`
- `docs/TW_STOCK_MONITOR_DEPLOYMENT_CN.md`
- `docs/TW_STOCK_PHASE5_ACCEPTANCE_CN.md`
- `docs/TW_STOCK_PHASE6_ACCEPTANCE_CN.md`
- `docs/TW_STOCK_PHASE7_ACCEPTANCE_CN.md`
- `docs/TW_STOCK_PHASE8_ACCEPTANCE_CN.md`
- `docs/TW_STOCK_PHASE9_ACCEPTANCE_CN.md`
- 本文档：`docs/TAIWAN_STOCK_HANDOFF_PHASE1_8_CN.md`

## 9. 已知限制和风险

- 当前不是盘中实时行情系统。
- 趋势历史从 Phase 6B 之后的 scan 开始积累。
- 页面仍是 Flask 托管轻量页面，不是正式 Vue 前端。
- Playwright e2e 当前使用 CLI 截图 smoke，不是完整浏览器断言测试框架。
- Webhook 仅为最小外部通道；Telegram/Email 台股专用配置入口尚未实现。
- TPEx 官方 OpenAPI 对账仍不稳定；扩大上柜股票前需要补官方对账或由用户本地比对。
- Universe 扩大流程默认 disabled，需要人工审核后导入和启用。
- 当前仓库有大量未提交改动和未跟踪文件，继续工作时不要随意 revert/reset。

## 10. Phase 9 建议路线

建议 Phase 9 继续围绕“交付可维护性”和“研究栈可复核性”，不要扩大交易链路。

当前进度：

- `Phase 9A` 已完成：新增 `docs/TAIWAN_STOCK_HANDOFF_PHASE1_8_CN.md`，旧 Phase 1-6 交接文档保留为历史入口并指向新文档。
- `Phase 9B` 已完成：部署手册新增持续验收与维护入口，README 文档导航补充一键验收、CI/PR 安全维护说明。
- `Phase 9C` 已完成：`docs/CHANGELOG.md` 新增台股研究栈 Phase 7-9 maintenance checkpoint，记录产品化、验收自动化和维护文档收敛。
- `Phase 9D` 已完成：运行 Phase 5/6/7/8 组合离线回归，结果 `87 passed in 1.44s`。
- `Phase 9E` 已完成：新增 `docs/TW_STOCK_FRONTEND_PHASE9E_CN.md`，明确正式 Vue 页面应在独立前端仓/独立 workflow 中推进；当前本机前端源码已在 `/path/to/taiwan-stock-quant-platform-Vue`，可供新窗口查看和改进；并补 workflow 静态测试防止台股研究 CI 混入前端 e2e。
- `Phase 9` 已验收：新增 `docs/TW_STOCK_PHASE9_ACCEPTANCE_CN.md`，一键验收结果 `ok=true`、`46 passed`、`orders_enabled=false`、`writes_production_data=false`、`connects_to_broker=false`。

可选子阶段：

1. `Phase 9A`：交接文档收敛
   - 已新增 Phase 1-8 交接文档。
   - 旧 Phase 1-6 交接文档保留为历史入口，并指向新文档。

2. `Phase 9B`：发布/维护文档收敛
   - 在部署文档和 README 中明确一键验收命令。
   - 把 CI、PR checklist、人工审核链路放到一个维护入口。

3. `Phase 9C`：Changelog 追加
   - 给 Phase 7/8/9 文档与研究栈安全自动化追加变更记录。

4. `Phase 9D`：更广回归
   - 已运行旧 Phase 5/6 与 Phase 7/8 的组合测试集。
   - 结果：`87 passed in 1.44s`。
   - 继续保持离线、无 broker、无 order submission。

5. `Phase 9E`：正式前端准备
   - 已新增正式 Vue 台股页面准备清单：`docs/TW_STOCK_FRONTEND_PHASE9E_CN.md`。
   - 若接入 Vue 台股页面，新开独立 frontend/e2e workflow。
   - 不混入当前离线研究栈 CI。

## 11. 新窗口启动前检查

## 12. Phase 10-12 阶段性收尾

Phase 10 至 Phase 12 已完成阶段性动作，范围仍限定为台股趋势研究、自动监控提醒和人工复盘/人工决策，不扩大到自动交易链路。

### 12.1 后端研究栈增强

- `Phase 10A`：`preflight_tw_stock_monitor_config.py` 增加只读 quality gate，覆盖最小 K 线数、陈旧数据、趋势分析失败和未来日期。
- `Phase 10B`：universe 输出增加 `manual_review` 指引，串起 quality gate、dry-run import 和人工 apply。
- `Phase 10C`：新增保守样本配置 `docs/examples/tw_stock_monitor_conservative_sample.json`，默认 `enabled=false`。
- `Phase 10D`：新增 `build_tw_stock_data_quality_report.py`，输出只读数据质量 JSON/Markdown 报告。
- `Phase 11A`：台股提醒 payload 增加 `category`、`reason`、`human_action`、`orders_enabled=false`。
- `Phase 11B`：扫描日志 API 增加 `health` 摘要，并新增 `report_tw_stock_monitor_health.py` 只读报告脚本。
- `Phase 11C`：新增 `report_tw_stock_alert_review.py`，汇总提醒类别、类型、严重级别和人工决策状态。

### 12.2 正式 Vue 前端交付

- `Phase 12A`：后端仓新增 `docs/TW_STOCK_FRONTEND_PHASE12A_API_CONTRACT_CN.md`，定义正式 Vue 台股页面 API contract；后端 CI 只做静态契约检查。
- `Phase 12B`：正式台股趋势监控页面已在 `/path/to/taiwan-stock-quant-platform-Vue` 前端仓实现：
  - `src/views/tw-stock-monitor/index.vue`
  - `src/api/tw-stock.js`
  - 路由 `/#/tw-stock-monitor`
  - 菜单翻译和静态边界检查。
- `Phase 12C`：前端仓新增独立 workflow `.github/workflows/tw-stock-monitor-frontend.yml`，运行 Node/pnpm/Vite 构建和台股前端静态检查，不接入后端台股研究 CI。
- `Phase 12D`：前端仓新增 `docs/TW_STOCK_MONITOR_FRONTEND_ACCEPTANCE_CN.md`，记录人工验收清单和禁止交易/broker/live 边界。
- `Phase 12E`：前端仓新增 `docs/TW_STOCK_MONITOR_LOCAL_SMOKE_CN.md`，只作为本地手动联调 smoke，不进入后端 CI。
- `Phase 12F`：新增 `docs/TW_STOCK_PHASE12F_ACCEPTANCE_CN.md`，完成 Phase 10-12 阶段交接收尾。

### 12.3 当前固定边界

- 后端台股研究 CI 不安装 Node/npm/pnpm。
- 后端台股研究 CI 不安装浏览器。
- 后端台股研究 CI 不构建 Vue 前端。
- 后端台股研究 CI 不启动页面 smoke。
- 正式 Vue 台股页面只在 `QuantDinger-Vue` 前端仓推进，并使用独立前端 workflow。
- 台股功能继续保持 `orders_enabled=false`、`writes_production_data=false`、`connects_to_broker=false`。
- 不自动交易，不连接 broker，不连接 IBKR，不提交 paper/live order，不启用 live。

### 12.4 阶段性完成标准

当前阶段性动作完成。后续若继续推进，建议只从以下方向选择：

1. 前端人工验收截图和真实本地联调记录。
2. 数据质量报告的例行人工复核。
3. 监控提醒文本和人工决策流程微调。
4. 不触碰 broker/live/order 链路的研究报表增强。

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

如果需要确认安全边界，运行一键验收：

```bash
PYTHONPATH=backend \
python \
  backend/scripts/verify_tw_stock_research_stack.py
```

预期：输出包含 `orders_enabled=false`、`writes_production_data=false`、`connects_to_broker=false`。
