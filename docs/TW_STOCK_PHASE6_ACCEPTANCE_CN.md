# 台股趋势监控 Phase 6 验收报告

更新时间：2026-05-24

## 1. 验收结论

Phase 6 可验收完成。

本阶段完成了“提醒推送与趋势可视化增强”的研究版能力，主线保持为：台股趋势研究、自动监控提醒、人工复盘和人工决策。不自动买卖，不连接 IBKR 或任何券商，不提交 paper/live order。

## 2. 已完成能力

### Phase 6A：站内通知桥接

- 台股监控 alert 写入 `qd_tw_stock_monitor_alerts` 后，同步写入 `qd_strategy_notifications`。
- 通知字段约定：`strategy_id=NULL`、`signal_type=tw_stock_monitor`、`channels=browser`、`title=台股趋势提醒`。
- 通知 payload 包含 alert id、monitor name、symbol、alert type、severity 和趋势快照。
- 通知写入采用 best-effort + PostgreSQL savepoint，通知失败不会破坏原始 alert 事务。

### Phase 6B：趋势历史 API

- 新增 `qd_tw_stock_trend_history`。
- 每次成功后端扫描都会追加趋势历史点。
- 历史点保存趋势标签、趋势分数、最新日线日期、最新收盘价、质量 warning、完整 snapshot 和扫描时间。
- 新增只读 API：`GET /api/tw-stock/monitor/history?symbol=2330&limit=120`。

### Phase 6C：页面可视化与人工复盘

- 监控页面新增趋势分数曲线 `canvas#trendChart`。
- 页面通过 history API 读取趋势历史点。
- 提醒区域支持全部/未读过滤。
- 每条提醒支持人工状态：`watch`、`ignored`、`acted`。
- 页面继续保留“只读：不下单”边界。

### Phase 6D：独立 worker / cron

- 新增独立脚本：`backend/scripts/run_tw_stock_monitor_scan.py`。
- 支持 `--once` 作为 cron 单次扫描。
- 支持 `--loop --interval-sec 900` 作为 systemd/supervisor 常驻 worker。
- 输出 JSON 摘要，包含 `orders_enabled=false`。
- 部署手册新增 cron 和常驻 worker 命令示例。

## 3. 验收测试

本轮 Phase 6 收尾回归测试：

```bash
python -m pytest   backend/tests/test_run_tw_stock_monitor_scan.py   backend/tests/test_tw_stock_trend_api.py   backend/tests/test_tw_stock_monitor_worker.py   backend/tests/test_tw_stock_kline_api.py   backend/tests/test_tw_stock_data_source.py   backend/tests/test_market_symbols_seed_sql.py -q
```

结果：`52 passed in 1.01s`。

额外 smoke：

- `run_tw_stock_monitor_scan.py --help` 成功，CLI 参数完整。
- 页面模板检查通过：`trendChart=True`、`history_api=True`、`alert_filter=True`、`manual_watch=True`、`read_only_copy=True`。
- 5000 端口无遗留监听。

此前分步 smoke 证据：

- Phase 6A PostgreSQL smoke：站内通知写入成功，smoke 数据已清理。
- Phase 6B PostgreSQL smoke：history API 读取 `phase6b-smoke` 历史点成功，smoke 数据已清理。
- Phase 6C Flask/PostgreSQL smoke：页面返回 200，关键控件存在。
- Phase 6D PostgreSQL smoke：独立脚本 `--once --force --trigger-source phase6d-smoke --no-log` 输出 `orders_enabled=false`。

## 4. 安全边界

验收期间确认：

- 没有提交 paper order。
- 没有提交 live order。
- 没有连接 IBKR。
- 没有调用 broker client。
- 没有调用 quick-trade 路径。
- `AGENT_LIVE_TRADING_ENABLED` 应继续保持 `false`。
- `ENABLE_TW_STOCK_MONITOR_WORKER` 默认关闭；生产推荐使用独立 cron/worker，避免 API 同进程后台任务。

所有 Phase 6 新能力均为研究提醒、趋势历史、页面复盘和运维调度，不构成投资建议或自动交易系统。

## 5. 部署入口

页面入口：

```text
GET /api/tw-stock/monitor
```

趋势历史 API：

```text
GET /api/tw-stock/monitor/history?symbol=2330&limit=120
```

独立 cron 单次扫描：

```bash
DATABASE_URL=postgresql://user:password@127.0.0.1:5432/quantdinger AGENT_LIVE_TRADING_ENABLED=false ENABLE_PENDING_ORDER_WORKER=false ENABLE_PORTFOLIO_MONITOR=false ENABLE_TW_STOCK_MONITOR_WORKER=false PYTHONPATH=backend python   backend/scripts/run_tw_stock_monitor_scan.py --once --trigger-source cron
```

## 6. 已知限制

- 当前仍是日线趋势研究，不是盘中实时行情系统。
- 趋势历史从 Phase 6B 之后的 scan 开始积累，不会自动还原过去未保存的扫描点。
- 页面仍是 Flask 托管轻量页面，不是正式 Vue 前端。
- 外部通知通道尚未实现：Telegram、Email、Webhook 仍为后续可选项。
- 独立脚本目前复用 route 层的 scan-all 函数；后续可把扫描核心下沉到 service 层。
- TPEx 官方 OpenAPI 对账在当前环境仍不稳定，不影响 TWSE/ETF 研究主线，但后续若扩大上柜股票，应继续补对账。

## 7. 后续建议

优先级建议：

1. Phase 7A：把台股监控页面接入正式前端或保留 Flask 页面但补 UI e2e 截图检查。
2. Phase 7B：选择一个外部通知通道，建议先做 Webhook，再做 Telegram/Email。
3. Phase 7C：扩大台股/ETF universe，同时补 TPEx 对账或由用户本地比对。
4. Phase 7D：把扫描核心从 route 层下沉到 service 层，降低 API 和脚本耦合。
