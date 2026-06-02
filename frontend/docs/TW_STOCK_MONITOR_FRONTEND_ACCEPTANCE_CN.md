# 台股趋势监控前端人工验收记录

## 范围

本记录覆盖 `QuantDinger-Vue` 前端仓中的台股趋势监控页面：

- 页面入口：`/#/tw-stock-monitor`
- 路由文件：`src/config/router.config.js`
- 页面源码：`src/views/tw-stock-monitor/index.vue`
- 前端 API：`src/api/tw-stock.js`
- 独立前端 workflow：`.github/workflows/tw-stock-monitor-frontend.yml`

本页面只用于台股趋势研究、监控提醒和人工复盘。页面不得提供自动交易、broker 连接、IBKR 连接、paper/live 下单或自动买卖能力。

## 人工验收清单

| 项目 | 预期结果 | 状态 |
| --- | --- | --- |
| 页面入口 | 可通过 `/#/tw-stock-monitor` 进入台股趋势监控页面 | 待人工确认 |
| 顶部边界标识 | 页面显示 `Research`、`orders_enabled=false`、`Human Review` | 待人工确认 |
| 趋势列表 | 可展示台股趋势标签、分数、最新日期、收盘价和数据质量提醒 | 待人工确认 |
| 扫描健康度 | 可展示扫描状态、成功/失败数量、扫描数量和提醒数量 | 待人工确认 |
| 提醒复盘 | 可查看提醒并人工更新 `decision_status` | 待人工确认 |
| 监控配置 | 可编辑观察标的、K 线数量、刷新间隔、分数变化阈值和备注 | 待人工确认 |
| qlib Option C Ops Dry-run | 显示 `qlib Option C Ops Dry-run`、`Dry-run only`、`Research ops`、`No latest update`、`No accepted artifact`、`No trading`；可手动触发 `/api/tw-stock/quant/ops/option-c/dry-run`，请求体只有 `asof`；只展示 job、stdout/stderr tail、latest_signal_updated=false 和 no-trading flags | 待人工确认 |
| qlib 研究观察草稿 | `加入觀察` 只进入本地草稿；观察草稿是人工复盘用途；`填入監控配置` 只更新配置表单，保存监控配置必须由用户手动点击，不自动扫描、不自动提醒、不自动交易 | 待人工确认 |
| 研究扫描 | `研究掃描` 只调用台股监控扫描 API，不提交订单 | 待人工确认 |
| 禁止交易入口 | 页面不出现 quick-trade、broker、IBKR、paper/live order、自动买卖或提交订单入口 | 待人工确认 |
| 前端 workflow | 台股前端验收只在 `QuantDinger-Vue` 内运行 Node/pnpm/Vite，不调用后端研究 CI | 已静态检查 |
| 本地浏览器 smoke | 可用本地账号登录并打开台股页面，检查图表 canvas 和只读边界 | 已补脚本 |

## API 边界

`src/api/tw-stock.js` 只允许使用 `/api/tw-stock` 前缀下的研究与监控接口：

- `GET /api/tw-stock/trends`
- `GET /api/tw-stock/monitor/config`
- `POST /api/tw-stock/monitor/config`
- `GET /api/tw-stock/monitor/alerts`
- `PUT /api/tw-stock/monitor/alerts/{id}`
- `GET /api/tw-stock/monitor/history`
- `POST /api/tw-stock/monitor/scan`
- `POST /api/tw-stock/monitor/scan-all`
- `GET /api/tw-stock/monitor/scan-logs`


qlib Option C ops 运维接口仅用于 dry-run 状态展示和手动 dry-run：

- `POST /api/tw-stock/quant/ops/option-c/dry-run`，请求体只能包含 `asof`。
- `GET /api/tw-stock/quant/ops/option-c/latest`。
- `GET /api/tw-stock/quant/ops/option-c/jobs/{job_id}`。
- `GET /api/tw-stock/quant/ops/option-c/jobs/{job_id}/logs?stream=stdout|stderr`。

页面必须显示 `qlib Option C Ops Dry-run`、`Dry-run only`、`Research ops`、`No latest update`、`No accepted artifact`、`No trading`，并确认不触发 refresh/publish/provider mutation。

不得在台股前端页面或台股 API client 中引入以下能力：

- broker account / broker connect
- IBKR / Alpaca / MT5 连接
- quick trade
- paper order / live order
- submit order
- auto buy / auto sell
- 中文下单、买入、卖出、提交订单入口

## 验证命令

在 `QuantDinger-Vue` 前端仓执行：

```bash
node tests/unit/tw-stock-monitor-static-check.mjs
node tests/unit/tw-stock-monitor-workflow-check.mjs
node tests/unit/tw-stock-monitor-qlib-ops-check.mjs
corepack pnpm build

# 前后端本地服务启动后可选执行
node tests/unit/tw-stock-monitor-local-smoke.mjs
```

预期结果：

- 两个 Node 静态检查均通过。
- Vite build 成功。
- 若出现既有 `/deep/` CSS 或 chunk size warning，只要构建退出码为 0，不视为本页面验收失败。

## CI 边界

`.github/workflows/tw-stock-monitor-frontend.yml` 是独立前端 workflow，只运行前端依赖安装、台股前端静态检查和 Vite build。

后端台股研究 CI 仍保持离线研究栈边界：

- 不安装 Node/npm/pnpm。
- 不安装浏览器。
- 不启动前端页面 smoke。
- 不连接 broker。
- 不启用 live。
- 不执行任何订单提交。

- qlib Option C 数据状态通过 `/api/tw-stock/quant/signals/health` 做 health 状态只读展示；不刷新 qlib provider、不重新生成 qlib 信号、不自动补数据。
