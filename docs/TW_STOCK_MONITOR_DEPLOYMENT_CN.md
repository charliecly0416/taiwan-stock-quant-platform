# 台股趋势监控部署与运维手册

更新时间：2026-05-24

## 1. 定位与边界

本手册用于部署和运维 QuantDinger 的台股趋势监控链路。当前能力是研究和提醒：系统可以按需查询台股/ETF 趋势，可以自动扫描观察列表，可以生成趋势变化、分数变化和数据质量提醒。

明确边界：

- 不自动买卖。
- 不连接 IBKR 或其他 broker。
- 不提交 paper/live order。
- 买卖决策由用户人工完成。
- `AGENT_LIVE_TRADING_ENABLED` 应保持 `false`，除非未来单独进入实盘审批流程。

## 2. 已部署能力

后端页面：

- `GET /api/tw-stock/monitor`：台股趋势与监控面板。

趋势 API：

- `GET /api/tw-stock/trend?symbol=2330&limit=120`
- `GET /api/tw-stock/trends?symbols=2330,0050,00878&limit=120`

监控配置与提醒 API：

- `GET /api/tw-stock/monitor/config`
- `POST|PUT /api/tw-stock/monitor/config`
- `GET /api/tw-stock/monitor/alerts?limit=50&unread_only=false`
- `POST /api/tw-stock/monitor/alerts`
- `PUT /api/tw-stock/monitor/alerts/<id>`

后端扫描 API：

- `POST /api/tw-stock/monitor/scan`
- `POST /api/tw-stock/monitor/scan-all`
- `GET /api/tw-stock/monitor/history?symbol=2330&limit=120`
- `GET /api/tw-stock/monitor/scan-logs?limit=20`：包含最近扫描日志和 `health` 健康摘要。

## 3. 数据库表

启动后端时会自动应用 `backend/migrations/init.sql`。台股监控相关表：

- `qd_tw_stock_monitor_configs`：监控配置，包含观察列表、日线数量、刷新频率、分数变化阈值、启用状态。
- `qd_tw_stock_monitor_alerts`：提醒历史，包含 symbol、提醒类型、严重级别、消息、快照、已读状态、人工备注。
- `qd_tw_stock_monitor_states`：后端扫描状态，保存每个监控配置下每个 symbol 的上次趋势标签、分数、最新日期和质量提示。
- `qd_tw_stock_trend_history`：趋势历史点，保存每次成功扫描的趋势标签、分数、最新日线日期、收盘价和完整快照。
- `qd_strategy_notifications`：站内通知，台股提醒会以 `signal_type=tw_stock_monitor`、`channels=browser` 写入。
- `qd_tw_stock_monitor_scan_logs`：扫描运行日志，记录触发来源、状态、扫描配置数、扫描 symbol 数、提醒数、错误和耗时。

架构说明：扫描核心位于 `backend/app/services/tw_stock_monitor.py`；API route、可选 worker 和独立 cron 脚本通过兼容包装调用同一套 service 逻辑。

## 4. 推荐环境变量

本地只读研究模式：

```bash
DATABASE_URL=postgresql://user:password@127.0.0.1:5432/quantdinger
AGENT_LIVE_TRADING_ENABLED=false
ENABLE_PENDING_ORDER_WORKER=false
ENABLE_PORTFOLIO_MONITOR=false
ENABLE_TW_STOCK_MONITOR_WORKER=false
```

启用后台台股监控 worker：

```bash
ENABLE_TW_STOCK_MONITOR_WORKER=true
TW_STOCK_MONITOR_INTERVAL_SEC=900
TW_STOCK_MONITOR_FORCE_SCAN=false
```

说明：

- `ENABLE_TW_STOCK_MONITOR_WORKER=false` 是默认值；不显式开启时不会后台自动扫描。
- `TW_STOCK_MONITOR_INTERVAL_SEC` 默认 900 秒，代码限制最小 30 秒、最大 86400 秒。
- `TW_STOCK_MONITOR_FORCE_SCAN=false` 表示只扫描 `enabled=true` 的监控配置。
- worker 只调用趋势扫描和提醒落库，不下单。

外部 Webhook 提醒（Phase 7B，可选，默认关闭）：

```bash
TW_STOCK_MONITOR_WEBHOOK_ENABLED=true
TW_STOCK_MONITOR_WEBHOOK_URL=https://example.com/your-webhook
# 可选：generic webhook HMAC、飞书/钉钉签名等复用 signal_notifier 的实现
TW_STOCK_MONITOR_WEBHOOK_SIGNING_SECRET=your-secret
```

说明：

- Webhook 只在台股 monitor alert 生成后 best-effort 推送；失败只写日志，不影响 alert 入库和站内通知。
- Payload 固定包含 `source=tw_stock_monitor`、`event=tw_stock_monitor_alert` 和 `trading.orders_enabled=false`。
- 也可在用户 `notification_settings` 中设置 `tw_stock_monitor_webhook_enabled=true` 和 `tw_stock_monitor_webhook_url`；环境变量优先。


## 4A. 持续验收与维护入口

每次修改台股研究栈、部署前、或新窗口接手前，优先运行一键离线验收：

```bash
PYTHONPATH=backend \
python \
  backend/scripts/verify_tw_stock_research_stack.py
```

预期输出：

- `ok=true`
- `orders_enabled=false`
- `writes_production_data=false`
- `connects_to_broker=false`

可选页面 smoke 验收：

```bash
PYTHONPATH=backend \
python \
  backend/scripts/verify_tw_stock_research_stack.py \
  --with-page-smoke \
  --screenshot /tmp/tw_stock_monitor_smoke.png
```

维护流程建议：

1. 先运行一键验收，确认台股研究栈离线测试通过。
2. 若扩大观察列表，必须先 `build_tw_stock_universe.py` 导出，再 `preflight_tw_stock_monitor_config.py` 只读预检，最后 `import_tw_stock_monitor_config.py --dry-run`，人工确认后才 `--apply`。
3. 涉及台股研究栈的 PR，检查 `.github/PULL_REQUEST_TEMPLATE.md` 中的 `TWStock Research Safety` checklist。
4. GitHub Actions `.github/workflows/tw-stock-research.yml` 会在台股相关代码、脚本、测试、文档、PR 模板或 workflow 变更时运行离线验收。
5. CI 和本地验收都不启动服务、不安装浏览器、不连接外部 broker、不提交 paper/live order。

如果一键验收输出中的 `orders_enabled`、`writes_production_data` 或 `connects_to_broker` 不是 `false`，应立即停止部署并排查。

## 4B. Phase 10A 使用前质量门禁

扩大或启用观察列表前，建议先运行只读质量门禁。它只调用趋势分析读取日线数据，输出样本覆盖和新鲜度结论；不会写数据库、不会触发扫描、不会创建提醒、不会提交订单。

```bash
PYTHONPATH=backend \
python \
  backend/scripts/preflight_tw_stock_monitor_config.py \
  --input-json /tmp/tw_stock_monitor_universe.json \
  --limit 120 \
  --min-bars 60 \
  --max-stale-days 5 \
  --fail-on-quality-gate
```

重点查看输出里的 `quality_gate`：

- `ready_for_manual_review=true`：数据长度和新鲜度满足进入人工审核的最低要求。
- `status=fail`：至少一个 symbol 存在日线不足、日线过旧、未来日期或趋势分析失败。
- `orders_enabled=false`、`db_written=false`：该门禁仍是研究只读流程。

如果 `--fail-on-quality-gate` 返回非零退出码，应先修复数据归档或缩小观察列表，再进入 dry-run import 和人工审核。

Universe 构建产物会同时输出 `manual_review` 区块，包含质量门禁、dry-run import 和人工批准后 apply 的命令模板。该区块只作为人工流程提示；`build_tw_stock_universe.py` 本身不会写入监控配置、不会触发扫描，也不会创建提醒。

## 4C. Phase 10C 保守配置样本 Runbook

仓库提供一份保守研究观察列表示例：`docs/examples/tw_stock_monitor_conservative_sample.json`。该样本默认 `enabled=false`，只用于人工审核和研究监控准备，不会自动启用扫描。

建议流程：

1. 先运行质量门禁：

```bash
PYTHONPATH=backend \
python \
  backend/scripts/preflight_tw_stock_monitor_config.py \
  --input-json docs/examples/tw_stock_monitor_conservative_sample.json \
  --limit 120 \
  --min-bars 60 \
  --max-stale-days 5 \
  --fail-on-quality-gate
```

2. 再运行 dry-run import，确认将写入的配置内容：

```bash
PYTHONPATH=backend \
python \
  backend/scripts/import_tw_stock_monitor_config.py \
  --input-json docs/examples/tw_stock_monitor_conservative_sample.json \
  --dry-run
```

3. 人工确认 symbol、阈值、质量门禁和 dry-run 输出后，才允许 apply：

```bash
PYTHONPATH=backend \
python \
  backend/scripts/import_tw_stock_monitor_config.py \
  --input-json docs/examples/tw_stock_monitor_conservative_sample.json \
  --apply
```

说明：样本 apply 只写入研究监控配置，且保持 `enabled=false`；后续是否启用扫描仍需人工通过页面或配置明确决定。

## 4D. Phase 10D 数据质量复核报告

如果需要把质量门禁结果留档给人工复盘，可以生成 JSON 和 Markdown 报告：

```bash
PYTHONPATH=backend \
python \
  backend/scripts/build_tw_stock_data_quality_report.py \
  --input-json docs/examples/tw_stock_monitor_conservative_sample.json \
  --limit 120 \
  --min-bars 60 \
  --max-stale-days 5 \
  --output-json /tmp/tw_stock_quality_report.json \
  --output-md /tmp/tw_stock_quality_report.md \
  --fail-on-quality-gate
```

报告包含：

- `quality_gate` 总结。
- 每个 symbol 的最新日期、bar 数、stale days、趋势标签、趋势分数、warnings 和 failures。
- 固定安全字段：`orders_enabled=false`、`writes_production_data=false`、`connects_to_broker=false`、`scanned=false`、`alerts_created=0`。

该脚本只读趋势数据并写本地报告文件，不导入配置、不触发扫描、不创建提醒、不写生产数据。

## 5. 本地启动

在仓库根目录运行：

```bash
PYTHON_API_HOST=127.0.0.1 \
PYTHON_API_PORT=5000 \
DATABASE_URL=postgresql://user:password@127.0.0.1:5432/quantdinger \
AGENT_LIVE_TRADING_ENABLED=false \
ENABLE_PENDING_ORDER_WORKER=false \
ENABLE_PORTFOLIO_MONITOR=false \
ENABLE_TW_STOCK_MONITOR_WORKER=false \
python backend/run.py
```

启动后访问：

```text
http://127.0.0.1:5000/api/tw-stock/monitor
```

如果要启用后台 worker，把 `ENABLE_TW_STOCK_MONITOR_WORKER=false` 改为 `true`，并按需要设置扫描间隔。

## 6. 配置观察列表

通过页面配置最简单。也可以直接调用 API：

```bash
curl -s -X POST 'http://127.0.0.1:5000/api/tw-stock/monitor/config' \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "default",
    "symbols": ["2330", "0050", "00878"],
    "limit_bars": 120,
    "refresh_interval_sec": 300,
    "score_change_threshold": 8,
    "enabled": true,
    "notes": "default TWStock monitor"
  }'
```

读取配置：

```bash
curl -s 'http://127.0.0.1:5000/api/tw-stock/monitor/config?name=default'
```

## 7. 手动扫描

扫描单个配置：

```bash
curl -s -X POST 'http://127.0.0.1:5000/api/tw-stock/monitor/scan' \
  -H 'Content-Type: application/json' \
  -d '{"name":"default"}'
```

强制扫描单个配置，即使配置 disabled：

```bash
curl -s -X POST 'http://127.0.0.1:5000/api/tw-stock/monitor/scan' \
  -H 'Content-Type: application/json' \
  -d '{"name":"default", "force": true}'
```

扫描所有 enabled 配置：

```bash
curl -s -X POST 'http://127.0.0.1:5000/api/tw-stock/monitor/scan-all' \
  -H 'Content-Type: application/json' \
  -d '{}'
```

返回结果中应包含：

- `total_scanned_count`
- `total_alert_count`
- `trading.orders_enabled=false`

## 8. 查看提醒

查看最近提醒：

```bash
curl -s 'http://127.0.0.1:5000/api/tw-stock/monitor/alerts?name=default&limit=20'
```

只看未读提醒：

```bash
curl -s 'http://127.0.0.1:5000/api/tw-stock/monitor/alerts?name=default&unread_only=true&limit=20'
```

标记已读并保存人工备注：

```bash
curl -s -X PUT 'http://127.0.0.1:5000/api/tw-stock/monitor/alerts/1' \
  -H 'Content-Type: application/json' \
  -d '{"is_read": true, "decision_status": "watch", "user_note": "人工观察，不自动交易"}'
```

Phase 11A 起，自动扫描生成的提醒 snapshot 会包含 `alert_context`：

- `category=trend_change`：趋势标签或趋势分数变化。
- `category=data_quality`：新增或首次出现的数据质量提示。
- `reason`：触发原因，例如 `trend_label_changed`、`trend_score_threshold_crossed`、`new_quality_warning`。
- `human_action`：建议的人工复盘动作。
- `orders_enabled=false`：提醒不是订单指令。

这些字段只帮助人工分类和复盘，不改变提醒入库 schema，不会触发交易。

## 8A. Phase 11B 扫描运行健康度

查看最近扫描日志和健康摘要：

```bash
curl -s 'http://127.0.0.1:5000/api/tw-stock/monitor/scan-logs?limit=20'
```

返回 `data.health` 包含：

- `status`：`healthy`、`degraded`、`failed` 或 `unknown`。
- `success_count` / `failed_count` / `success_rate`。
- `total_scanned_count` / `total_alert_count`。
- `avg_duration_ms`。
- `recent_failures`。
- 固定安全字段：`orders_enabled=false`、`writes_production_data=false`、`connects_to_broker=false`。

也可以在命令行只读查看健康度：

```bash
PYTHONPATH=backend \
python \
  backend/scripts/report_tw_stock_monitor_health.py \
  --limit 20
```

该脚本只读取 `qd_tw_stock_monitor_scan_logs`，不会运行扫描、不会创建提醒、不会写生产数据。

## 8B. Phase 11C 提醒人工复盘报表

每日或每次人工复盘前，可以生成只读提醒报表：

```bash
PYTHONPATH=backend \
python \
  backend/scripts/report_tw_stock_alert_review.py \
  --user-id 1 \
  --name default \
  --limit 100 \
  --output-md /tmp/tw_stock_alert_review.md
```

报表会汇总：

- `unread_count` 和 `needs_review_count`。
- 按 `data_quality` / `trend_change` / `other` 分类。
- 按 `alert_type`、`severity`、`decision_status` 分类。
- 每条提醒的 symbol、类别、类型、严重级别、人工状态、已读状态和消息。
- 固定安全字段：`orders_enabled=false`、`writes_production_data=false`、`connects_to_broker=false`。

该脚本只读取 `qd_tw_stock_monitor_alerts`，不会创建新提醒、不会发送通知、不会写生产数据。

`decision_status` 当前支持：

- `pending`
- `watch`
- `acted`
- `ignored`

## 8A. 扩大观察列表（人工审核）

可以先用 universe builder 根据 `qd_market_symbols` 和近期流动性筛选候选，并导出监控配置 JSON：

```bash
PYTHONPATH=backend \
python \
  backend/scripts/build_tw_stock_universe.py \
  --include-etf \
  --limit-candidates 200 \
  --max-universe 50 \
  --monitor-name default \
  --monitor-config-json /tmp/tw_stock_monitor_universe.json
```

导出的 `monitor_config` 默认 `enabled=false`，用于人工审核；确认后可以通过 API 写入，也可以用导入脚本 dry-run 后再 apply：

```bash
PYTHONPATH=backend \
python \
  backend/scripts/import_tw_stock_monitor_config.py \
  --input-json /tmp/tw_stock_monitor_universe.json \
  --dry-run
```

确认 `symbols`、`enabled` 和 `orders_enabled=false` 后，建议先做只读预检：

```bash
PYTHONPATH=backend \
python \
  backend/scripts/preflight_tw_stock_monitor_config.py \
  --input-json /tmp/tw_stock_monitor_universe.json \
  --limit 120
```

预检只调用趋势分析，不写数据库、不创建 alert、不扫描落库。确认 `failed_count=0` 后再写入：

```bash
PYTHONPATH=backend \
python \
  backend/scripts/import_tw_stock_monitor_config.py \
  --input-json /tmp/tw_stock_monitor_universe.json \
  --apply
```

如需导入后立即启用监控配置，加 `--enabled`；否则保持 JSON 中的 `enabled`，通常为 `false`。该流程只扩大研究观察列表，不触发扫描、不发提醒、不下单。

## 9. 查看扫描日志

```bash
curl -s 'http://127.0.0.1:5000/api/tw-stock/monitor/scan-logs?limit=20'
```

重点字段：

- `trigger_source`：`api` 或 `worker`。
- `status`：`success` 或 `failed`。
- `monitor_count`：扫描配置数。
- `scanned_count`：扫描 symbol 数。
- `alert_count`：生成提醒数。
- `duration_ms`：耗时。
- `error`：失败原因。



## 10A. 独立 worker / cron 推荐部署

生产上更推荐把台股监控扫描放到独立进程或 cron，而不是绑定在 API 进程内。独立脚本如下：

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

特点：

- `--once`：执行一次扫描后退出，适合 cron。
- `--loop`：常驻循环扫描，适合 systemd/supervisor。
- `--interval-sec 900`：循环模式扫描间隔，代码限制 30 到 86400 秒。
- `--force`：连 disabled 配置也扫描；日常不建议开启。
- `--trigger-source cron|systemd|worker`：写入扫描日志，便于区分来源。
- `--no-log`：不写扫描日志，仅建议测试时使用。
- 输出一行 JSON 摘要，包含 `total_scanned_count`、`total_alert_count`、`orders_enabled=false`。

cron 示例，每 15 分钟扫描 enabled 配置：

```cron
*/15 * * * * cd /path/to/taiwan-stock-quant-platform && DATABASE_URL=postgresql://user:password@127.0.0.1:5432/quantdinger AGENT_LIVE_TRADING_ENABLED=false ENABLE_PENDING_ORDER_WORKER=false ENABLE_PORTFOLIO_MONITOR=false ENABLE_TW_STOCK_MONITOR_WORKER=false PYTHONPATH=backend python backend/scripts/run_tw_stock_monitor_scan.py --once --trigger-source cron >> /tmp/quantdinger_tw_stock_monitor.log 2>&1
```

systemd/supervisor 常驻模式示例：

```bash
cd /path/to/taiwan-stock-quant-platform
DATABASE_URL=postgresql://user:password@127.0.0.1:5432/quantdinger \
AGENT_LIVE_TRADING_ENABLED=false \
ENABLE_PENDING_ORDER_WORKER=false \
ENABLE_PORTFOLIO_MONITOR=false \
ENABLE_TW_STOCK_MONITOR_WORKER=false \
PYTHONPATH=backend \
python \
  backend/scripts/run_tw_stock_monitor_scan.py --loop --interval-sec 900 --trigger-source systemd
```

部署建议：

- API 服务保持 `ENABLE_TW_STOCK_MONITOR_WORKER=false`。
- 只启用一个独立 worker 或 cron，避免多进程重复扫描同一配置。
- 任何模式都不会下单；如输出中 `orders_enabled` 不是 `false`，应立即停止并排查。

### systemd unit 示例

保存为 `/etc/systemd/system/quantdinger-tw-stock-monitor.service`，按实际路径和数据库密码调整：

```ini
[Unit]
Description=QuantDinger TWStock research monitor
After=network.target postgresql.service

[Service]
Type=simple
WorkingDirectory=/path/to/taiwan-stock-quant-platform
Environment=DATABASE_URL=postgresql://user:password@127.0.0.1:5432/quantdinger
Environment=AGENT_LIVE_TRADING_ENABLED=false
Environment=ENABLE_PENDING_ORDER_WORKER=false
Environment=ENABLE_PORTFOLIO_MONITOR=false
Environment=ENABLE_TW_STOCK_MONITOR_WORKER=false
Environment=PYTHONPATH=backend
ExecStart=python backend/scripts/run_tw_stock_monitor_scan.py --loop --interval-sec 900 --trigger-source systemd
Restart=always
RestartSec=15
StandardOutput=append:/var/log/quantdinger/tw-stock-monitor.log
StandardError=append:/var/log/quantdinger/tw-stock-monitor.err.log

[Install]
WantedBy=multi-user.target
```

启用：

```bash
sudo mkdir -p /var/log/quantdinger
sudo systemctl daemon-reload
sudo systemctl enable --now quantdinger-tw-stock-monitor.service
sudo systemctl status quantdinger-tw-stock-monitor.service
```

### logrotate 示例

保存为 `/etc/logrotate.d/quantdinger-tw-stock-monitor`：

```text
/var/log/quantdinger/tw-stock-monitor*.log {
    daily
    rotate 14
    compress
    missingok
    notifempty
    copytruncate
}
```

### 历史清理

新增脚本 `backend/scripts/cleanup_tw_stock_monitor_history.py`，默认 dry-run：

```bash
DATABASE_URL=postgresql://user:password@127.0.0.1:5432/quantdinger \
AGENT_LIVE_TRADING_ENABLED=false \
ENABLE_PENDING_ORDER_WORKER=false \
ENABLE_PORTFOLIO_MONITOR=false \
ENABLE_TW_STOCK_MONITOR_WORKER=false \
PYTHONPATH=backend \
python \
  backend/scripts/cleanup_tw_stock_monitor_history.py \
  --trend-retention-days 365 --scan-log-retention-days 90
```

确认输出后再加 `--apply` 删除旧记录。cron 示例，每天凌晨 03:20 清理：

```cron
20 3 * * * cd /path/to/taiwan-stock-quant-platform && DATABASE_URL=postgresql://user:password@127.0.0.1:5432/quantdinger AGENT_LIVE_TRADING_ENABLED=false ENABLE_PENDING_ORDER_WORKER=false ENABLE_PORTFOLIO_MONITOR=false ENABLE_TW_STOCK_MONITOR_WORKER=false PYTHONPATH=backend python backend/scripts/cleanup_tw_stock_monitor_history.py --trend-retention-days 365 --scan-log-retention-days 90 --apply >> /tmp/quantdinger_tw_stock_cleanup.log 2>&1
```

清理脚本只删除 `qd_tw_stock_trend_history.scanned_at` 和 `qd_tw_stock_monitor_scan_logs.created_at` 超过保留期的记录，不删除 alert、state、config，不触碰订单或 broker。

## 10. 启用后台 worker

启动命令示例：

```bash
PYTHON_API_HOST=127.0.0.1 \
PYTHON_API_PORT=5000 \
DATABASE_URL=postgresql://user:password@127.0.0.1:5432/quantdinger \
AGENT_LIVE_TRADING_ENABLED=false \
ENABLE_PENDING_ORDER_WORKER=false \
ENABLE_PORTFOLIO_MONITOR=false \
ENABLE_TW_STOCK_MONITOR_WORKER=true \
TW_STOCK_MONITOR_INTERVAL_SEC=900 \
TW_STOCK_MONITOR_FORCE_SCAN=false \
python backend/run.py
```

启动日志应包含：

```text
TWStock monitor worker started: interval=900s force=False
```

关闭 worker：

```bash
ENABLE_TW_STOCK_MONITOR_WORKER=false
```

然后重启 API。

## 11. 数据质量与时效性

当前趋势接口使用 `KlineService:TWStock:1D`，底层来自已接入的台股日线数据源。它适合日频趋势研究，不是盘中实时行情。

质量字段：

- `quality.bar_count`
- `quality.latest_date`
- `quality.stale_days`
- `quality.warnings`
- `quality.source`

常见 warnings：

- `stale_daily_bar`：日线数据过旧。
- `latest_bar_in_future`：数据日期异常在未来。
- `short_history_below_60_bars`：历史样本过短。
- `history_below_120_bars`：少于 120 根日线。

## 12. 故障排查

数据库连接失败：

- 检查 `DATABASE_URL`。
- 确认 PostgreSQL 在 `127.0.0.1:55432` 监听。
- 查看启动日志是否有 `PostgreSQL connection verified`。

表不存在：

- 正常启动会自动应用 `migrations/init.sql`。
- 查看日志是否有 `Applied init.sql`。
- 如果设置了 `SKIP_AUTO_MIGRATE=true`，需要手动应用 schema。

页面无法打开：

- 确认 API 进程正在监听 `127.0.0.1:5000`。
- 访问 `http://127.0.0.1:5000/api/tw-stock/monitor`。

扫描没有产生提醒：

- 这通常是正常情况，表示相对上次扫描没有趋势标签变化、分数变化未超过阈值、没有新增质量 warning。
- 可以降低 `score_change_threshold`，但不要把短期波动误解为交易指令。

worker 没启动：

- 检查 `ENABLE_TW_STOCK_MONITOR_WORKER=true`。
- 查看日志是否显示 disabled。
- Debug reloader 模式下，父进程会跳过 worker，子进程才启动。

## 13. 清理 smoke 数据

如果需要清理本地 smoke 配置和提醒，可连接 PostgreSQL 后执行类似 SQL。请先确认只清理测试名称：

```sql
DELETE FROM qd_tw_stock_monitor_alerts WHERE monitor_name IN ('phase5c-smoke', 'phase5d-smoke', 'phase5e-smoke', 'phase5g-e2e');
DELETE FROM qd_tw_stock_monitor_states WHERE monitor_name IN ('phase5c-smoke', 'phase5d-smoke', 'phase5e-smoke', 'phase5g-e2e');
DELETE FROM qd_tw_stock_monitor_configs WHERE name IN ('phase5c-smoke', 'phase5d-smoke', 'phase5e-smoke', 'phase5g-e2e');
DELETE FROM qd_tw_stock_monitor_scan_logs WHERE trigger_source IN ('api', 'worker') AND created_at < NOW() - INTERVAL '7 days';
```

不要清理 `default`，除非你确认不再需要默认观察列表。

## 14. 运维自检清单

每次部署或重启后建议先跑离线一键验收，再检查本地 API：

```bash
PYTHONPATH=backend \
python \
  backend/scripts/verify_tw_stock_research_stack.py
```

然后检查运行中的 API：

```bash
curl -s 'http://127.0.0.1:5000/api/tw-stock/trend?symbol=2330&limit=120'
curl -s 'http://127.0.0.1:5000/api/tw-stock/monitor/config?name=default'
curl -s -X POST 'http://127.0.0.1:5000/api/tw-stock/monitor/scan-all' -H 'Content-Type: application/json' -d '{}'
curl -s 'http://127.0.0.1:5000/api/tw-stock/monitor/scan-logs?limit=5'
```

确认：

- 趋势 API 返回 `code=1`。
- 监控配置存在或返回默认配置。
- `scan-all` 返回 `trading.orders_enabled=false`。
- `scan-logs` 能看到最近运行记录。
- 没有 IBKR 连接日志。
- 没有 paper/live order 提交记录。


## 15. 端到端演练记录

2026-05-24 已完成一次从配置到 worker 的真实演练：

- 新建配置 `phase5g-e2e`，观察 `2330`、`0050`。
- 手动 `scan-all` 成功：`monitor_count=4`、`scanned_count=10`、`alert_count=0`。
- 启用 worker：`ENABLE_TW_STOCK_MONITOR_WORKER=true`、`TW_STOCK_MONITOR_INTERVAL_SEC=30`。
- worker 自动扫描成功：`trigger_source=worker`、`status=success`、`monitor_count=4`、`scanned_count=10`、`alert_count=0`。
- 回归测试：`48 passed in 0.97s`。

`alert_count=0` 表示真实数据没有触发新的趋势变化或质量 warning，不代表扫描失败。确认 `orders_enabled=false`，没有产生任何交易动作。


## 16. 最终验收与技术债

Phase 5 的最终验收清单和剩余技术债已整理到：

- `docs/TW_STOCK_PHASE5_ACCEPTANCE_CN.md`

部署前建议先阅读该文档中的上线前检查、数据质量验收和安全验收，确认本系统当前定位仍是研究提醒，而不是自动交易。


## 17. Smoke 配置清理记录

2026-05-24 已清理 Phase 5 smoke 监控配置：`phase5c-smoke`、`phase5d-smoke`、`phase5e-smoke`、`phase5g-e2e`。

结果：

- 删除 `qd_tw_stock_monitor_states` 7 行。
- 删除 `qd_tw_stock_monitor_configs` 3 行。
- 删除 `qd_tw_stock_monitor_alerts` 0 行。
- `default` 配置仍保留。

未清理 `qd_tw_stock_monitor_scan_logs`，因为扫描日志没有 `monitor_name` 字段，无法按配置名精准删除。为避免误删真实运行日志，本次保留。
