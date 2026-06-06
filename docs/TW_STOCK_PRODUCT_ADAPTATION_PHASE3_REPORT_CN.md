# 台股产品适配 Phase 3 Report：模拟账户前端 MVP

日期：2026-06-05

## 1. 执行结论

已按 `docs/TW_STOCK_PRODUCT_ADAPTATION_PHASE3_EXECUTION_CN.md` 完成 Phase 3 前端 MVP。新增 `/tw-stock-sim-account` 页面，用户可以查看或创建模拟账户、查看现金/持仓/权益、手动生成模拟买入/卖出草稿、查看参考价/费用/税费/warnings，并手动确认或取消模拟成交。

本阶段没有把 qlib Top30、Agent、cross-analysis 接到模拟草稿，也没有新增真实交易、券商连接、monitor scan、alerts write、qlib ops、provider refresh/publish 或 accepted latest switch 入口。

## 2. 新增/修改文件

新增：

- `frontend/src/views/tw-stock-sim-account/index.vue`
- `frontend/tests/unit/tw-stock-sim-account-check.mjs`
- `docs/TW_STOCK_PRODUCT_ADAPTATION_PHASE3_REPORT_CN.md`

修改：

- `frontend/src/api/tw-stock.js`
- `frontend/src/config/router.config.js`
- `frontend/src/locales/lang/zh-CN.js`
- `frontend/src/locales/lang/zh-TW.js`
- `frontend/src/locales/lang/en-US.js`

## 3. 页面入口和主要 UI

新增路由：`/tw-stock-sim-account`。

菜单文案：`台股模拟账户`。

页面固定边界提示已加入：

```text
本页面仅用于台股研究信号的历史与模拟验证，不连接券商，不提交真实订单，不构成投资建议。
```

页面主区块：

- 账户概览：账户名称、初始资金、现金、持仓市值、总权益、累计收益、累计收益率、`simulation_only=true`。
- 创建账户：无账户时显示名称和初始资金输入，默认 `台股研究模拟账户`、`1000000`。
- 手动模拟交易：账户、symbol、模拟买入/模拟卖出、quantity、固定 `source_type=manual`，价格说明为最新可用收盘价。
- 草稿详情：展示状态、标的、方向、数量、参考价、价格日期、成交金额、手续费、交易税、现金影响、source、warnings。
- 持仓列表：展示 symbol、quantity、avg_cost、latest_close、latest_date、market_value、unrealized_pnl。
- 成交记录：展示 symbol、side、quantity、price、price_date、fee、tax、net_cash_effect、source_type、created_at。

## 4. API 调用清单

前端只新增并调用以下模拟账户 helper：

- `getTwStockSimAccounts` -> `GET /api/tw-stock/sim/accounts`
- `createTwStockSimAccount` -> `POST /api/tw-stock/sim/accounts`
- `getTwStockSimAccount` -> `GET /api/tw-stock/sim/accounts/:account_uid`
- `getTwStockSimPositions` -> `GET /api/tw-stock/sim/accounts/:account_uid/positions`
- `getTwStockSimTrades` -> `GET /api/tw-stock/sim/accounts/:account_uid/trades`
- `draftTwStockSimOrder` -> `POST /api/tw-stock/sim/orders/draft`
- `confirmTwStockSimOrder` -> `POST /api/tw-stock/sim/orders/:sim_order_uid/confirm`
- `cancelTwStockSimOrder` -> `POST /api/tw-stock/sim/orders/:sim_order_uid/cancel`

## 5. 草稿、确认、取消、rejected 处理

- 生成草稿成功后展示后端返回的 `sim_order`、参考价、价格日期、费用、税、现金影响和 warnings。
- 只有 `draftOrder.status === 'draft'` 且没有安全错误时显示并允许点击 `确认模拟成交`。
- `rejected` 状态显示拒绝原因，不显示确认入口。
- 确认成功后刷新账户、持仓、成交记录。
- 取消成功后保留后端返回的取消状态，避免用户误以为已经成交。
- API 异常会显示页面 warning；如果异常响应包含模拟 payload，会先进行安全边界校验并展示草稿/拒绝信息。

## 6. 安全边界

前端已防御式检查：

- `simulation_only === true`
- `trading.simulation_only === true`
- `trading.real_orders_enabled === false`
- `trading.connects_to_broker === false`

如果后端返回异常 flags，页面会显示安全错误并禁止确认模拟成交。

静态检查确认新增页面未导入或调用：

- quick-trade
- broker
- real order/order APIs
- monitor scan
- alerts write
- qlib ops
- Agent chat

页面文案使用“模拟账户 / 模拟成交”，没有把本页面包装成真实交易终端。

## 7. 测试结果

已执行：

```bash
cd frontend
node tests/unit/tw-stock-sim-account-check.mjs
```

结果：通过。

已执行：

```bash
cd frontend
corepack pnpm build
```

结果：通过，Vite production build 成功。

备注：运行命令时环境会输出 `/bin/sh: 2: source: not found`，但命令退出码为 0，未影响测试与构建结果。

## 8. Playwright / Network Audit

本阶段执行文档把 Playwright smoke 标为建议项，不是必须项。本次没有启动前后端服务执行浏览器级 E2E，原因是 Phase 3 范围是前端 MVP 与静态安全边界；新增静态测试已经覆盖路由、菜单、页面文案、按钮、模拟 API helper、草稿/确认/取消流程、安全 flags 和禁止入口。

建议 Phase 4 在模拟账户与研究页联动前，补一个只读 Playwright smoke：登录后访问 `/tw-stock-sim-account`，拦截 network，确认仅出现 `/api/tw-stock/sim/**` GET/POST，且没有 quick-trade、broker、monitor scan、alerts write、qlib ops、Agent chat 请求。

## 9. 是否建议进入 Phase 4

建议进入 Phase 4。Phase 3 已经提供清晰、简单、可验证的模拟账户闭环，且没有越过研究与模拟验证边界。Phase 4 可以在继续保持安全边界的前提下，考虑增加更完整的绩效复盘、历史收益曲线、按研究日期回看模拟成交效果等功能。
