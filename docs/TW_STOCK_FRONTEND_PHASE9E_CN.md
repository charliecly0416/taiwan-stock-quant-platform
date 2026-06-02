# 台股正式前端 Phase 9E 准备清单

更新时间：2026-05-25

## 1. 结论

Phase 9E 不在当前后端仓库直接实现正式 Vue 台股页面。

原因：后端仓库本身不包含 Vue 源码，Web 前端源码位于独立的 `QuantDinger-Vue` 仓库，当前后端仓通过 GHCR 预构建前端镜像部署。当前本机已确认前端源码仓库存在于相邻目录：`/path/to/taiwan-stock-quant-platform-Vue`（从后端仓看是 `../QuantDinger-Vue`）。台股研究栈现有 CI 是离线后端验收 workflow，不应混入 Node 安装、前端构建、浏览器安装或完整 e2e。

当前保持：

- Flask 托管轻量页面：`GET /api/tw-stock/monitor`。
- 后端只读/研究 API 已可供正式 Vue 页面调用。
- 页面 smoke 可用 `verify_tw_stock_research_stack.py --with-page-smoke` 本地手动执行。
- `.github/workflows/tw-stock-research.yml` 继续只做离线研究栈验收。

## 2. 正式 Vue 页面建议范围

建议在 `QuantDinger-Vue` 仓库新增独立页面或模块，首屏应是实际监控工作台，不做营销页。

基础视图：

- 台股观察列表，展示 symbol、趋势标签、趋势分数、最新日线日期、收盘价、质量 warning。
- 趋势分数历史图，读取 `GET /api/tw-stock/monitor/history`。
- 最近提醒列表，支持 unread 过滤、级别过滤和人工状态更新。
- 监控配置编辑：name、symbols、limit_bars、refresh_interval_sec、score_change_threshold、enabled、notes。
- scan-all 手动触发按钮，只显示研究扫描结果和 `orders_enabled=false`。

人工审核链路：

- 可上传或粘贴 `build_tw_stock_universe.py --monitor-config-json` 的输出。
- 前端只做展示、差异确认和调用配置保存 API；不自动启用新 symbols。
- 默认保留 `enabled=false`，需要用户明确切换。
- 页面文案应明确“研究提醒、人工决策”，不出现下单、买入、卖出、提交订单等交易执行按钮。

## 3. API 对接清单

只读趋势：

```text
GET /api/tw-stock/trend?symbol=2330&limit=120
GET /api/tw-stock/trends?symbols=2330,0050,00878&limit=120
```

监控配置：

```text
GET /api/tw-stock/monitor/config
POST /api/tw-stock/monitor/config
PUT /api/tw-stock/monitor/config
```

提醒与人工状态：

```text
GET /api/tw-stock/monitor/alerts?limit=50&unread_only=false
POST /api/tw-stock/monitor/alerts
PUT /api/tw-stock/monitor/alerts/<id>
```

扫描与日志：

```text
POST /api/tw-stock/monitor/scan
POST /api/tw-stock/monitor/scan-all
GET /api/tw-stock/monitor/scan-logs?limit=20
```

趋势历史：

```text
GET /api/tw-stock/monitor/history?symbol=2330&limit=120
```

每个可触发扫描的响应都应检查并显示：

- `trading.orders_enabled=false`
- `writes_production_data=false`，如响应或验收摘要包含该字段
- `connects_to_broker=false`，如响应或验收摘要包含该字段

## 4. 前端安全约束

正式 Vue 页面不得：

- 调用 quick-trade、broker、IBKR、paper order 或 live order API。
- 暴露自动买入、自动卖出、自动下单、提交订单按钮。
- 根据趋势标签自动生成订单。
- 默认启用 `AGENT_LIVE_TRADING_ENABLED` 或任何 worker。
- 把提醒文案包装成投资建议。

正式 Vue 页面应：

- 明确显示研究/提醒/人工决策定位。
- 对所有配置导入保留人工审核步骤。
- 对 scan 结果显示 `orders_enabled=false`。
- 将状态操作限定为 `pending`、`watch`、`acted`、`ignored` 这类人工复盘状态。

## 5. 独立前端 CI 建议

若在 `QuantDinger-Vue` 仓库实现正式台股页面，建议新增独立 frontend/e2e workflow，而不是修改当前 `.github/workflows/tw-stock-research.yml`。

建议 workflow：

- 安装 Node 与前端依赖。
- 使用 mock API 或测试后端，只返回台股研究 API 固定响应。
- 运行前端单测和 Playwright e2e。
- 检查页面无下单按钮、无 broker/IBKR 调用、scan 结果展示 `orders_enabled=false`。
- 对桌面和移动视口各截图一次，确保表格、图表、提醒过滤和配置表单不重叠。

当前后端仓 `.github/workflows/tw-stock-research.yml` 应继续保持：

- 不安装 Node/npm。
- 不构建前端。
- 不安装浏览器。
- 不运行 `--with-page-smoke`。
- 不启动服务。
- 不连接 broker。

## 6. 当前后端仓已完成的准备

- 后端 API 已覆盖趋势、批量趋势、监控配置、提醒、扫描、扫描日志和趋势历史。
- Flask 轻量页面可作为交互原型。
- `check_tw_stock_monitor_page_e2e.py` 提供页面 smoke 参考。
- `verify_tw_stock_research_stack.py` 提供离线验收入口。
- `test_tw_stock_research_workflow.py` 已增加静态断言，防止台股研究 CI 被误扩成前端/e2e workflow。

## 7. 后续触发条件

当前本机已经具备前端源码目录：

```bash
cd /path/to/taiwan-stock-quant-platform-Vue
```

因此新窗口可以读取和修改前端代码。但正式 Vue 台股页面仍应作为独立前端任务推进，不要把 Node/npm、前端构建或完整 e2e 混入后端仓的 `.github/workflows/tw-stock-research.yml`。

如果 Phase 10 先做上线前研究监控收口，建议优先做数据质量复核和 monitor config 样本。只有用户明确要求实现正式 Vue 页面时，才进入前端实现子阶段。

下一阶段可选命名：

- `Phase 10A`：真实使用前配置样本与数据质量复核。
- `Phase 10D`：正式 Vue 台股监控页面（在 `/path/to/taiwan-stock-quant-platform-Vue` 中实现）。
