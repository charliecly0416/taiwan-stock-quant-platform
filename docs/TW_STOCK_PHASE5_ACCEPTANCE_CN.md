# Phase 5 台股趋势监控验收清单与剩余技术债

更新时间：2026-05-24

## 1. 验收结论

Phase 5 的目标已经从“自动交易”调整为“按需查询 + 自动监控提醒 + 人工决策”。当前实现已经满足这个目标：

- 可以按需查询台股/ETF 趋势。
- 可以在后端保存观察列表和提醒规则。
- 可以通过页面查看趋势和提醒。
- 可以手动触发服务器端扫描。
- 可以启用后台 worker 自动扫描。
- 可以查询扫描日志和提醒历史。
- 不自动下单，不连接 broker，不生成交易指令。

## 2. 已完成能力

### Phase 5A：趋势 API

- `GET /api/tw-stock/trend?symbol=2330&limit=120`
- `GET /api/tw-stock/trends?symbols=2330,0050,00878&limit=120`
- 返回趋势标签、趋势分数、收益率、均线、成交量、风险、数据质量。
- 返回 `trading.orders_enabled=false`。

### Phase 5B：趋势与监控面板

- `GET /api/tw-stock/monitor`
- 支持观察列表、日线数量、刷新频率、分数变化阈值。
- 页面显示趋势分数、收益、均线、量比、波动率、数据质量。
- 页面无买卖按钮。

### Phase 5C：配置和提醒持久化

- `qd_tw_stock_monitor_configs`
- `qd_tw_stock_monitor_alerts`
- `GET/POST /api/tw-stock/monitor/config`
- `GET/POST /api/tw-stock/monitor/alerts`
- `PUT /api/tw-stock/monitor/alerts/<id>`
- 支持已读、人工状态、备注。

### Phase 5D：后端扫描

- `qd_tw_stock_monitor_states`
- `POST /api/tw-stock/monitor/scan`
- `POST /api/tw-stock/monitor/scan-all`
- 支持首次建立基线，后续比较趋势标签、趋势分数、数据质量 warnings。

### Phase 5E：worker 和扫描日志

- `qd_tw_stock_monitor_scan_logs`
- `GET /api/tw-stock/monitor/scan-logs?limit=20`
- `ENABLE_TW_STOCK_MONITOR_WORKER`
- `TW_STOCK_MONITOR_INTERVAL_SEC`
- `TW_STOCK_MONITOR_FORCE_SCAN`
- worker 默认关闭，显式启用后自动执行 `scan-all`。

### Phase 5F：部署与运维手册

- `docs/TW_STOCK_MONITOR_DEPLOYMENT_CN.md`
- 覆盖启动、配置、扫描、worker、日志、数据质量、故障排查、清理 smoke 数据。

### Phase 5G：端到端演练

已完成从配置到 worker 的真实演练：

- 新建 `phase5g-e2e` 配置。
- 手动 `scan-all` 成功。
- 启用 worker 成功。
- worker 自动扫描成功。
- `scan-logs` 出现 `trigger_source=worker` 的成功记录。

## 3. 验收测试

最近一次 Phase 5 相关回归：

```bash
python -m pytest \
  backend/tests/test_tw_stock_trend_api.py \
  backend/tests/test_tw_stock_monitor_worker.py \
  backend/tests/test_tw_stock_kline_api.py \
  backend/tests/test_tw_stock_data_source.py \
  backend/tests/test_market_symbols_seed_sql.py -q
```

结果：`48 passed in 0.97s`。

真实演练摘要：

- 手动 scan-all：`count=4`、`total_scanned_count=10`、`total_alert_count=0`、`orders_enabled=false`。
- worker scan log：`trigger_source=worker`、`status=success`、`monitor_count=4`、`scanned_count=10`、`alert_count=0`。

`alert_count=0` 是合理结果，表示真实数据相对上次扫描没有触发新的趋势变化或数据质量提醒。

## 4. 上线前检查

上线或长期运行前，应逐项确认：

- PostgreSQL 可用，`DATABASE_URL` 正确。
- API 启动日志出现 `PostgreSQL connection verified`。
- API 启动日志出现 `Applied init.sql`，或确认 schema 已手动应用。
- `AGENT_LIVE_TRADING_ENABLED=false`。
- `ENABLE_PENDING_ORDER_WORKER=false`，除非未来明确需要订单 worker。
- `ENABLE_PORTFOLIO_MONITOR=false`，除非未来明确需要组合监控。
- `ENABLE_TW_STOCK_MONITOR_WORKER=true` 只在确认监控配置无误后开启。
- `TW_STOCK_MONITOR_INTERVAL_SEC` 不要设置过短；建议先用 900 秒。
- 趋势面板可以打开：`/api/tw-stock/monitor`。
- `scan-all` 返回 `trading.orders_enabled=false`。
- `scan-logs` 能看到 `success` 记录。
- 没有 IBKR/TWS/Gateway 连接日志。
- 没有 paper/live order 新增。

## 5. 数据质量验收

当前数据是日频研究数据，不是盘中实时流。

必须关注：

- `quality.latest_date`
- `quality.stale_days`
- `quality.warnings`
- `quality.bar_count`

上线时建议至少抽查：

```bash
curl -s 'http://127.0.0.1:5000/api/tw-stock/trend?symbol=2330&limit=120'
curl -s 'http://127.0.0.1:5000/api/tw-stock/trends?symbols=2330,0050,00878&limit=120'
```

如果 `warnings` 出现 `stale_daily_bar`，应先确认数据源更新，再判断趋势。

## 6. 安全验收

必须保持：

- 所有趋势和监控接口只用于研究提醒。
- 返回中保留 `orders_enabled=false`。
- 页面不提供买卖按钮。
- worker 不调用任何 broker client。
- 不开启 IBKR live promotion。
- 不把趋势标签直接解释为买卖指令。

## 7. 剩余技术债

### 数据源与质量

- TPEx 官方 OpenAPI 在当前环境无法稳定对账；TPEx 标的仍可通过 FinMind 获取，但官方交叉验证未完成。
- 当前趋势数据是日线，不是盘中实时或逐笔数据。
- 需要长期观察 FinMind 更新延迟、节假日、停牌、除权息后价格解释。

### 监控与提醒

- worker 当前只记录数据库提醒，不支持 Telegram/Email/Webhook 推送。
- 提醒去重策略较基础；同一趋势变化在边界条件下可能重复出现。
- 扫描日志只有概要，没有逐 symbol 错误明细表。
- 观察列表还没有分组、标签、权重或优先级。

### 前端体验

- 当前页面由 Flask 直接托管，适合轻量使用；如果未来接入正式 Vue 前端，需要迁移为产品化页面。
- 图表仍是指标表格，没有 K 线图、趋势曲线或历史分数曲线。
- 人工备注能力有 API 和基础页面按钮，但还不是完整研究日志系统。

### 运维

- worker 与 API 同进程运行；更稳妥的生产模式是独立 worker 进程或外部 cron。
- smoke 配置仍留在本地 DB 中，需要按手册清理。
- 缺少 Prometheus/Grafana 等外部监控指标。

### 策略研究

- 当前趋势分数是解释型启发式，不是已验证的盈利模型。
- 没有把 Phase 3 的横截面组合模拟结果接入趋势面板。
- 没有对提醒后的人工决策结果做绩效归因。

## 8. 后续建议

优先级建议：

1. 清理 smoke 配置，保留 `default` 监控配置。
2. 用真实自选台股/ETF 建立默认观察列表。
3. 连续运行 worker 至少 3 个交易日，观察 `latest_date`、`warnings` 和扫描日志。
4. 增加提醒推送渠道，例如 Telegram 或 webhook。
5. 增加趋势分数历史曲线和 K 线图。
6. 再决定是否恢复 paper trading 或 IBKR 相关主线。

## 9. 验收状态

Phase 5 可以视为“研究版台股趋势监控”完成。

尚不应视为完成：

- 实时行情系统。
- 自动交易系统。
- 实盘下单系统。
- 已验证可盈利策略。
- 正式投顾或投资建议系统。
