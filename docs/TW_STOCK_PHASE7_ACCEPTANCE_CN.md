# 台股趋势监控 Phase 7 验收报告

更新时间：2026-05-24

## 1. 验收结论

Phase 7 可验收完成。

本阶段围绕“趋势研究产品化”推进，完成页面 e2e、Webhook 外部提醒、universe 到监控配置的人工审核链路、扫描核心 service 化，以及运维清理/部署模板。安全边界保持不变：只做台股趋势研究、自动监控提醒、人工复盘和人工决策；不自动买卖，不连接 IBKR 或任何 broker，不提交 paper/live order。

## 2. 已完成能力

### Phase 7A：页面 e2e / smoke

- 新增 `backend/scripts/check_tw_stock_monitor_page_e2e.py`。
- 脚本启动 mock Flask 服务，不依赖真实 PostgreSQL 或 FinMind。
- 使用 Playwright CLI 打开 `/api/tw-stock/monitor`，等待趋势数据行后截图。
- 检查只读文案、无下单按钮、趋势行和截图 smoke。
- 新增 `backend/tests/test_tw_stock_monitor_page_e2e_script.py`。

### Phase 7B：Webhook 外部提醒

- 台股 monitor alert 生成后支持显式启用的 Webhook best-effort 推送。
- 默认关闭；启用方式：`TW_STOCK_MONITOR_WEBHOOK_ENABLED=true` + `TW_STOCK_MONITOR_WEBHOOK_URL=...`。
- 复用现有 `SignalNotifier._notify_webhook()`，支持 generic、飞书、钉钉、企微、Slack 等既有方言适配。
- Webhook 失败只写日志，不影响 alert 入库、站内通知或扫描。
- Payload 包含 `source=tw_stock_monitor`、`event=tw_stock_monitor_alert`、`trading.orders_enabled=false`。

### Phase 7C：扩大 universe 的人工审核链路

- `backend/scripts/build_tw_stock_universe.py` 输出新增 research-only `monitor_config`。
- 支持 `--monitor-config-json` 导出默认 disabled 的监控配置。
- 支持 `--include-etf`，继续从 `qd_market_symbols` 候选和近期流动性筛选。
- 新增 `backend/scripts/preflight_tw_stock_monitor_config.py`：导入前只读检查每个 symbol 的趋势和数据质量，不写库、不提醒、不下单。
- 新增 `backend/scripts/import_tw_stock_monitor_config.py`：默认 dry-run，`--apply` 才 upsert `qd_tw_stock_monitor_configs`，不触发扫描、不发提醒、不下单。

### Phase 7D：架构与运维收敛

- 新增 `backend/app/services/tw_stock_monitor.py`。
- 扫描核心下沉到 service：配置解析、提醒生成、状态更新、趋势历史写入、scan-all、扫描日志写入。
- Route 保留兼容包装，API、worker、cron 仍走同一逻辑，并保留现有测试 monkeypatch 行为。
- 新增 `backend/scripts/cleanup_tw_stock_monitor_history.py`：默认 dry-run，`--apply` 才清理旧趋势历史和扫描日志。
- 部署文档补充 systemd unit、logrotate、清理 cron、Webhook、universe 导出/预检/导入流程。

## 3. 验收测试

Phase 7 收尾回归：

```bash
python -m pytest   backend/tests/test_tw_stock_monitor_page_e2e_script.py   backend/tests/test_tw_stock_trend_api.py   backend/tests/test_tw_stock_monitor_worker.py   backend/tests/test_run_tw_stock_monitor_scan.py   backend/tests/test_tw_stock_monitor_service.py   backend/tests/test_cleanup_tw_stock_monitor_history.py   backend/tests/test_build_tw_stock_universe.py   backend/tests/test_import_tw_stock_monitor_config.py   backend/tests/test_preflight_tw_stock_monitor_config.py   -q
```

预期结果：全部通过。

页面 smoke：

```bash
PYTHONPATH=backend python   backend/scripts/check_tw_stock_monitor_page_e2e.py   --screenshot /tmp/tw_stock_monitor_phase7a.png
```

预期输出包含：`chartSmoke=true`、`rowCount=3`、`readonlyCopy=true`、`noOrderButton=true`、`orders_enabled=false`。

CLI smoke：

```bash
PYTHONPATH=backend python backend/scripts/import_tw_stock_monitor_config.py --input-json /tmp/tw_stock_monitor_phase7c.json --dry-run
PYTHONPATH=backend python backend/scripts/preflight_tw_stock_monitor_config.py --input-json /tmp/tw_stock_monitor_phase7c.json --limit 80
PYTHONPATH=backend python backend/scripts/cleanup_tw_stock_monitor_history.py --help
```

## 4. 安全边界

验收期间确认：

- 没有提交 paper order。
- 没有提交 live order。
- 没有连接 IBKR。
- 没有调用 broker client。
- 没有调用 quick-trade 路径。
- Webhook 只发送提醒 payload，不包含交易执行指令。
- Universe 导出、预检、导入均为人工审核链路，不触发扫描或下单。
- `AGENT_LIVE_TRADING_ENABLED` 应继续保持 `false`。
- `ENABLE_TW_STOCK_MONITOR_WORKER` 默认关闭；生产推荐使用独立 cron/worker。

## 5. 部署入口

页面：

```text
GET /api/tw-stock/monitor
```

Webhook 可选环境变量：

```bash
TW_STOCK_MONITOR_WEBHOOK_ENABLED=true
TW_STOCK_MONITOR_WEBHOOK_URL=https://example.com/your-webhook
TW_STOCK_MONITOR_WEBHOOK_SIGNING_SECRET=your-secret
```

扩大观察列表的人工审核链路：

```bash
PYTHONPATH=backend python   backend/scripts/build_tw_stock_universe.py   --include-etf --limit-candidates 200 --max-universe 50   --monitor-config-json /tmp/tw_stock_monitor_universe.json

PYTHONPATH=backend python   backend/scripts/preflight_tw_stock_monitor_config.py   --input-json /tmp/tw_stock_monitor_universe.json --limit 120

PYTHONPATH=backend python   backend/scripts/import_tw_stock_monitor_config.py   --input-json /tmp/tw_stock_monitor_universe.json --dry-run
```

确认后才使用 `--apply` 写入配置。

## 6. 已知限制

- 当前仍是日线趋势研究，不是盘中实时行情系统。
- 页面仍是 Flask 托管轻量页面，不是正式 Vue 前端。
- Playwright e2e 当前使用 CLI 截图 smoke，不是完整浏览器断言测试框架。
- Webhook 仅为最小外部通道；Telegram/Email 台股专用配置入口尚未实现。
- TPEx 官方 OpenAPI 对账仍不稳定；扩大上柜股票前需要补官方对账或由用户本地比对。
- Universe 扩大流程默认 disabled，需要人工审核后导入和启用。

## 7. 后续建议

1. 接入正式 Vue 前端或补更完整的 Playwright 测试框架。
2. 给正式前端增加台股 Webhook/通知配置入口。
3. 补 Telegram/Email 外部提醒。
4. 继续完善 TPEx 官方对账，再扩大上柜股票覆盖。
5. 根据真实使用量调整趋势历史和扫描日志保留期。

## 8. Phase 8 后续

Phase 8 的安全审计、一键验收、CI 和 PR checklist 已单独整理到 `docs/TW_STOCK_PHASE8_ACCEPTANCE_CN.md`。
