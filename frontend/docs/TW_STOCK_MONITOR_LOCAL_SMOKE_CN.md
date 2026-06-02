# 台股趋势监控本地联调 Smoke

## 目的

本文件用于 `QuantDinger-Vue` 前端仓的本地人工联调。它不是后端台股研究 CI 的一部分，也不要求在 `.github/workflows/tw-stock-research.yml` 中安装 Node、pnpm、浏览器或启动前端页面。

联调范围仍限定为：台股趋势研究、监控提醒、人工复盘和人工决策。

禁止范围：不自动交易、不连接 broker、不连接 IBKR、不提交 paper/live order、不启用 live。

## 前置条件

后端仓：`/path/to/taiwan-stock-quant-platform`

前端仓：`/path/to/taiwan-stock-quant-platform-Vue`

前端 Vite dev server 默认端口为 `8000`，`/api` 代理默认指向 `http://localhost:5000`。如需调整后端地址，可在前端 `.env.development` 中设置：

```bash
VITE_DEV_PROXY_TARGET=http://localhost:5000
```

## 启动后端 API

在后端仓启动本地 API，保持台股 monitor worker、pending order worker、portfolio monitor 和 live trading 关闭：

```bash
cd /path/to/taiwan-stock-quant-platform
AGENT_LIVE_TRADING_ENABLED=false ENABLE_PENDING_ORDER_WORKER=false ENABLE_PORTFOLIO_MONITOR=false ENABLE_TW_STOCK_MONITOR_WORKER=false PYTHONPATH=backend uvicorn backend.app:app --host 127.0.0.1 --port 5000
```

如果本地项目使用其他 API 启动入口，以实际入口为准，但必须保持以上四个开关为 `false`，并确认没有 broker 连接或 live 执行。

## 启动前端页面

在前端仓启动 Vue dev server：

```bash
cd /path/to/taiwan-stock-quant-platform-Vue
corepack pnpm install --frozen-lockfile
corepack pnpm dev --host 127.0.0.1
```

访问：

```text
http://127.0.0.1:8000/#/tw-stock-monitor
```

## 自动 smoke 检查

在前后端都启动后，可运行本地浏览器 smoke：

```bash
node tests/unit/tw-stock-monitor-local-smoke.mjs
```

该脚本使用本地账号登录，打开 `/#/tw-stock-monitor`，检查只读边界、趋势页面、两个图表 canvas，并确认页面文本没有 broker、live、下单或自动买卖入口。

## 手动检查项

| 项目 | 检查方式 | 预期结果 |
| --- | --- | --- |
| 页面可打开 | 访问 `/#/tw-stock-monitor` | 页面加载台股趋势监控视图 |
| 只读边界 | 查看顶部标签 | 显示 `Research`、`orders_enabled=false`、`Human Review` |
| 趋势列表 | 等待 `/api/tw-stock/trends` 返回 | 展示趋势标签、分数、最新日期和质量提醒 |
| 扫描健康度 | 等待 `/api/tw-stock/monitor/scan-logs` 返回 | 展示 health status、success/failed/scanned/alerts |
| 提醒复盘 | 查询 `/api/tw-stock/monitor/alerts` | 可人工修改 `decision_status`，不触发下单 |
| 研究扫描 | 点击 `研究掃描` | 只调用 `/api/tw-stock/monitor/scan`，不调用订单或 broker API |
| 配置抽屉 | 打开配置并保存 | 只调用 `/api/tw-stock/monitor/config` |
| qlib Option C Ops Dry-run | 查看 ops 区块，点击 dry-run | 显示 `Dry-run only`、`Research ops`、`No latest update`、`No accepted artifact`、`No trading`；只调用 `/api/tw-stock/quant/ops/option-c/dry-run`，请求体只有 `asof`；可查看 latest job 和 stdout/stderr tail |
| qlib 研究观察草稿 | 点击 `加入觀察`，再点击 `填入監控配置` | 观察草稿是人工复盘用途；只填入配置表单，保存监控配置必须由用户手动点击；不自动扫描、不自动提醒、不自动交易 |
| 禁止交易 | 浏览页面、Network 和控制台 | 不出现 quick-trade、broker、IBKR、paper/live order、submit order、自动买卖 |

## 可选 curl 检查

后端 API 启动后，可在后端仓手动检查台股研究接口：

```bash
curl -s 'http://127.0.0.1:5000/api/tw-stock/trends?symbols=2330,0050,00878&limit=120'
curl -s 'http://127.0.0.1:5000/api/tw-stock/monitor/config?name=default'
curl -s 'http://127.0.0.1:5000/api/tw-stock/monitor/scan-logs?limit=20'
curl -s 'http://127.0.0.1:5000/api/tw-stock/quant/ops/option-c/latest'
curl -s -X POST 'http://127.0.0.1:5000/api/tw-stock/quant/ops/option-c/dry-run' -H 'Content-Type: application/json' -d '{"asof":"2026-06-01"}'
```

预期响应中应能看到研究数据或空列表结构，并继续保留 `orders_enabled=false`、`connects_to_broker=false` 或等价安全声明。

## CI 边界

本 smoke 只用于本地人工联调，不进入后端台股研究 workflow。

前端仓的独立 workflow `.github/workflows/tw-stock-monitor-frontend.yml` 只做：

- 安装前端依赖。
- 运行台股前端静态检查。
- 运行台股前端 workflow/文档检查。
- 执行 `pnpm build`。

后端仓 `.github/workflows/tw-stock-research.yml` 继续保持离线研究验收：不安装 Node/npm/pnpm、不安装浏览器、不启动 Vue、不运行页面 smoke、不连接 broker、不启用 live、不提交订单。

- qlib Option C 数据状态通过 `/api/tw-stock/quant/signals/health` 做 health 状态只读展示；不刷新 qlib provider、不重新生成 qlib 信号、不自动补数据。
