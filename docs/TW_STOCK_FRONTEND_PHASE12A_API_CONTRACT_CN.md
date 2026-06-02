# 台股正式 Vue 页面 Phase 12A API Contract

更新时间：2026-05-25

## 1. 定位与边界

本文件为 `/path/to/taiwan-stock-quant-platform-Vue` 中正式台股页面准备 API contract。当前后端仓只维护契约和离线验收，不在 `.github/workflows/tw-stock-research.yml` 中安装 Node、构建前端或运行完整 e2e。

正式页面定位仍是：台股趋势研究、自动监控提醒、人工复盘、人工决策。

禁止范围：

- 不调用 quick-trade、broker、IBKR、paper order、live order API。
- 不展示自动买入、自动卖出、自动下单、提交订单按钮。
- 不根据趋势标签自动生成订单。
- 不把提醒包装成投资建议。

## 2. 主要 API

### 趋势分析

`GET /api/tw-stock/trend?symbol=2330&limit=120`

核心字段：

- `data.symbol`
- `data.exchange`
- `data.latest.date`
- `data.latest.close`
- `data.trend.label`
- `data.trend.score`
- `data.quality.bar_count`
- `data.quality.stale_days`
- `data.quality.warnings`
- `data.trading.orders_enabled=false`

`GET /api/tw-stock/trends?symbols=2330,0050,00878&limit=120`

核心字段：

- `data.items[]`
- `data.rankings[]`
- `data.trading.orders_enabled=false`

### 监控配置

`GET /api/tw-stock/monitor/config?user_id=1&name=default`

`POST|PUT /api/tw-stock/monitor/config`

请求字段：

- `user_id`
- `name`
- `symbols`
- `limit_bars`
- `refresh_interval_sec`
- `score_change_threshold`
- `enabled`
- `notes`

前端要求：导入 universe 或样本配置时默认保留 `enabled=false`，需要用户明确切换才启用扫描。

### 提醒与人工状态

`GET /api/tw-stock/monitor/alerts?name=default&limit=50&unread_only=false`

核心字段：

- `data.items[].symbol`
- `data.items[].alert_type`
- `data.items[].severity`
- `data.items[].message`
- `data.items[].snapshot.alert_context.category`
- `data.items[].snapshot.alert_context.reason`
- `data.items[].snapshot.alert_context.human_action`
- `data.items[].snapshot.alert_context.orders_enabled=false`
- `data.items[].is_read`
- `data.items[].decision_status`
- `data.items[].user_note`

`PUT /api/tw-stock/monitor/alerts/<id>`

允许前端更新：

- `is_read`
- `decision_status`: `pending`、`watch`、`acted`、`ignored`
- `user_note`

### 趋势历史

`GET /api/tw-stock/monitor/history?symbol=2330&name=default&limit=120`

核心字段：

- `data.items[].label`
- `data.items[].score`
- `data.items[].latest_date`
- `data.items[].latest_close`
- `data.items[].warnings`
- `data.trading.orders_enabled=false`

### 扫描与健康度

`POST /api/tw-stock/monitor/scan`

`POST /api/tw-stock/monitor/scan-all`

前端必须展示：

- `data.trading.orders_enabled=false`
- `data.scanned_count` 或 `data.total_scanned_count`
- `data.alert_count` 或 `data.total_alert_count`

`GET /api/tw-stock/monitor/scan-logs?limit=20`

核心字段：

- `data.items[]`
- `data.health.status`
- `data.health.success_rate`
- `data.health.recent_failures[]`
- `data.health.orders_enabled=false`
- `data.health.writes_production_data=false`
- `data.health.connects_to_broker=false`

## 3. 只读报表脚本对应页面

正式 Vue 页面可以对齐以下后端脚本的输出结构，但不应在浏览器直接执行脚本：

- `build_tw_stock_data_quality_report.py`：质量门禁复核视图。
- `report_tw_stock_monitor_health.py`：扫描健康度视图。
- `report_tw_stock_alert_review.py`：提醒人工复盘视图。

## 4. 独立前端 Workflow 要求

若在 `QuantDinger-Vue` 仓新增正式页面，应新增独立 frontend/e2e workflow：

- 可以安装 Node、前端依赖和浏览器。
- 使用 mock API 或测试后端。
- 检查页面无 quick-trade、broker、IBKR、paper/live order 调用。
- 检查页面无自动买入、自动卖出、提交订单按钮。
- 检查 scan 和 alert 视图展示 `orders_enabled=false`。

后端仓 `.github/workflows/tw-stock-research.yml` 必须继续保持离线后端 CI：不安装 Node/npm、不构建前端、不安装浏览器、不启动服务、不运行完整 e2e。
