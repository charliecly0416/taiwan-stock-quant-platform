# 台股产品适配 Phase 3 执行文档：模拟账户前端 MVP

日期：2026-06-05

## 1. Phase 2 审查结论

Phase 2 没有偏离主线，可以进入 Phase 3。

已完成内容符合“研究与模拟验证”主线：后端新增 `/api/tw-stock/sim/**` 模拟账户 API，支持创建模拟账户、手动模拟买入/卖出草稿、确认模拟成交、取消草稿、查看账户/持仓/成交。实现保持 `simulation_only=true`、`real_orders_enabled=false`、`connects_to_broker=false`，未接入 broker、quick-trade、真实订单、Agent、qlib ops、provider refresh/publish 或 accepted latest switch。

审查中需要延续到 Phase 3 的约束：

- Phase 3 只做前端模拟账户 MVP，不做 qlib Top30、Agent、cross-analysis 到模拟草稿的联动。
- 页面文案必须明确“模拟验证”，不能让用户理解为真实证券账户。
- 前端只能调用 `/api/tw-stock/sim/**`，不得调用 quick-trade、broker、真实订单、monitor scan、alerts write、qlib ops、OpenAI/Agent chat。
- `tw_stock.py` 中已有历史运维路由不是本阶段范围，Phase 3 不要新增入口去触发它们。

## 2. 本步目标

新增“台股模拟账户”前端页面，让用户能完成一个闭环：

1. 查看或创建模拟账户。
2. 查看现金、持仓市值、总权益、累计收益。
3. 手动填写股票代码、方向、数量。
4. 创建模拟交易草稿。
5. 查看成交参考价、费用、交易税、warning。
6. 用户手动确认或取消草稿。
7. 查看持仓和成交记录更新。

这是前端可用性 MVP，不追求复杂绩效归因。

## 3. 建议修改文件

优先复用现有项目结构：

```text
frontend/src/api/tw-stock.js
frontend/src/config/router.config.js
frontend/src/locales/lang/zh-CN.js
frontend/src/locales/lang/zh-TW.js
frontend/src/locales/lang/en-US.js
```

新增页面：

```text
frontend/src/views/tw-stock-sim-account/index.vue
```

新增测试：

```text
frontend/tests/unit/tw-stock-sim-account-check.mjs
```

如已有菜单或权限文件需要同步，按现有 `tw-stock-monitor` 写法最小改动。

## 4. API 封装要求

在 `frontend/src/api/tw-stock.js` 中新增模拟账户 API helper，命名保持清晰：

```text
getTwStockSimAccounts
createTwStockSimAccount
getTwStockSimAccount
getTwStockSimPositions
getTwStockSimTrades
draftTwStockSimOrder
confirmTwStockSimOrder
cancelTwStockSimOrder
```

只允许使用这些 endpoint：

```text
GET  /api/tw-stock/sim/accounts
POST /api/tw-stock/sim/accounts
GET  /api/tw-stock/sim/accounts/:account_uid
GET  /api/tw-stock/sim/accounts/:account_uid/positions
GET  /api/tw-stock/sim/accounts/:account_uid/trades
POST /api/tw-stock/sim/orders/draft
POST /api/tw-stock/sim/orders/:sim_order_uid/confirm
POST /api/tw-stock/sim/orders/:sim_order_uid/cancel
```

禁止新增或调用：

```text
/api/quick-trade
/api/broker
/api/order
/api/orders
/api/tw-stock/monitor/scan
/api/tw-stock/monitor/alerts POST/PUT
/api/tw-stock/quant/ops/**
/api/tw-stock/agent/chat
```

## 5. 页面入口与文案

新增路由：

```text
/tw-stock-sim-account
```

菜单文案：

```text
台股模拟账户
```

页面标题：

```text
台股模拟账户
```

固定边界提示：

```text
本页面仅用于台股研究信号的历史与模拟验证，不连接券商，不提交真实订单，不构成投资建议。
```

按钮文案只能使用：

```text
创建模拟账户
生成模拟买入草稿
生成模拟卖出草稿
确认模拟成交
取消草稿
刷新模拟账户
```

禁止文案：

```text
真实买入
真实卖出
一键买入
一键卖出
自动下单
连接券商
跟随 AI 买入
目标仓位
目标权重
实盘
live trading
paper trading
```

说明：本项目这里统一用“模拟账户 / 模拟成交”，不要使用容易和既有交易系统混淆的 paper trading。

## 6. 页面结构

页面保持 4 个主区块即可：

### 6.1 账户概览

展示：

- 账户名称。
- 初始资金。
- 现金。
- 持仓市值。
- 总权益。
- 累计收益金额。
- 累计收益率。
- `simulation_only=true` 状态说明。

没有账户时，提供创建账户表单：

- name，默认“台股研究模拟账户”。
- initial_cash，默认 1000000。

### 6.2 持仓列表

展示：

- symbol。
- quantity。
- avg_cost。
- latest_close。
- latest_date。
- market_value。
- unrealized_pnl。

如果 `latest_date` 为空或接口返回 warning，要显示“数据日期需复核”，不要显示为实时价。

### 6.3 手动模拟交易

字段：

- account。
- symbol。
- side：模拟买入 / 模拟卖出。
- quantity，默认 1000，提示需为 1000 股倍数。
- source_type 固定 manual，不给用户切换。
- price type 固定“最新可用收盘价”。

交互流程：

1. 用户点击“生成模拟买入草稿”或“生成模拟卖出草稿”。
2. 前端调用 `/sim/orders/draft`。
3. 展示后端返回的 reference_price、price_date、fee、tax、gross_amount、net_cash_effect、warnings。
4. 只有当草稿 `status=draft` 时显示“确认模拟成交”。
5. rejected 状态只显示原因，不显示确认按钮。
6. 确认后刷新账户、持仓、成交记录。

### 6.4 成交记录

展示：

- symbol。
- side。
- quantity。
- price。
- price_date。
- fee。
- tax。
- net_cash_effect。
- source_type。
- created_at。

只展示模拟成交，不展示真实订单 ID、券商账号、exchange order id。

## 7. 状态与错误处理

必须覆盖这些状态：

- 初始加载中。
- 无账户。
- 创建账户成功/失败。
- 草稿生成成功。
- 草稿 rejected：现金不足、缺少价格、数量不合法、卖空拦截。
- 确认成功。
- 取消成功。
- API 失败。

如果后端返回：

```text
simulation_only=false
real_orders_enabled=true
connects_to_broker=true
```

前端必须显示安全错误，并禁止继续确认。虽然后端当前不会这样返回，但前端需要做防御式校验。

## 8. 视觉与交互要求

页面应延续 `tw-stock-monitor` 的研究风格，避免做成券商交易终端：

- 信息密度适中，优先清晰展示账户状态和草稿确认。
- 不使用刺激交易的颜色和文案。
- 买入/卖出用普通 segmented/radio 控件即可，不做大面积红绿交易按钮。
- 移动端表格需要可横向滚动或卡片化，文字不能溢出。
- “确认模拟成交”必须在草稿详情之后出现，避免误点。

## 9. 必跑测试

执行者必须新增静态测试：

```bash
cd frontend
node tests/unit/tw-stock-sim-account-check.mjs
```

测试至少检查：

- 路由 `/tw-stock-sim-account` 存在。
- 菜单文案“台股模拟账户”存在。
- 页面包含固定研究边界提示。
- API helper 只包含 `/api/tw-stock/sim/**`。
- 页面不包含禁止文案。
- 页面不导入 `quick-trade`、`broker`、真实 order API、Agent chat。
- 页面包含草稿确认/取消流程。
- 页面会检查 `simulation_only` 和 `trading` flags。

构建验证：

```bash
cd frontend
corepack pnpm build
```

建议补充本地 Playwright smoke。如果本地前后端可用，则新增并执行：

```bash
cd frontend
TW_STOCK_MONITOR_BASE_URL=http://127.0.0.1:8000 node tests/e2e/tw-stock-sim-account-smoke.mjs
```

Smoke 至少覆盖：

- 打开 `/tw-stock-sim-account`。
- fixture 或真实后端返回一个模拟账户。
- 生成买入草稿。
- rejected 状态不会出现确认按钮。
- draft 状态可以确认并刷新持仓。
- network audit 中没有 quick-trade、broker、monitor scan、alerts write、qlib ops、agent chat。

如果本阶段无法新增 E2E，报告中必须说明原因，并至少完成静态检查和 build。

## 10. 明确不做

Phase 3 不做：

- 从 Top30/Top50 一键生成模拟草稿。
- 从 Agent 回答生成模拟草稿。
- 从 cross-analysis 生成模拟草稿。
- 自动买入/自动卖出。
- 目标仓位或目标权重。
- 真实券商连接。
- nav snapshot、最大回撤、基准比较。
- 数据拉取、daily auto update、qlib accepted latest 切换。

这些内容分别留到 Phase 4 或 Phase 5，并且仍必须保持用户手动确认。

## 11. 报告断点

完成后提交：

```text
docs/TW_STOCK_PRODUCT_ADAPTATION_PHASE3_REPORT_CN.md
```

报告必须包含：

- 新增/修改文件清单。
- 页面入口和主要 UI 说明。
- API 调用清单。
- 草稿、确认、取消、rejected 的处理说明。
- 是否检查 `simulation_only` / `trading` flags。
- 是否出现真实交易文案或真实交易 API。
- 测试命令和结果。
- 如果跑了 Playwright，给出 network audit 结论。
- 是否建议进入 Phase 4。
