# 台股排名技术交叉与组合回放 Step 5 执行报告：只读前端展示

生成时间：2026-06-06

## 1. Step 4 审查修正说明

Step 4 的只读组合回放契约继续保持：`portfolio-replay` 仅用于历史模拟计算，前端请求强制 `persist=false`，不接入模拟账户写入、broker、quick-trade、monitor 写入或 qlib ops。

本步实现时额外修正了一个前端响应式问题：`rankTechLatestPayload`、`portfolioReplayPayload` 等 Step 5 新状态必须预先声明在 Vue 2 `data()` 中，否则接口返回后组件状态有值但 computed 与模板不会刷新。该问题已修复。

## 2. 修改文件清单

- `frontend/src/api/tw-stock.js`
  - 新增 `getTwStockRankTechCrossLatest`。
  - 新增 `getTwStockObservationReplay`。
  - 新增 `runTwStockPortfolioReplay`，请求体强制 `persist:false`。
- `frontend/src/views/tw-stock-monitor/index.vue`
  - 新增“今日复盘与历史模拟”只读区块。
  - 新增 rank-tech latest、portfolio replay 独立 loading/error 状态。
  - 修正 `unwrap()`，优先解析前端 request 实际返回的 `{ code, msg, data }`。
- `frontend/tests/unit/tw-stock-rank-tech-portfolio-replay-check.mjs`
  - 新增 Step 5 API/页面/文案静态检查。
- `frontend/tests/e2e/tw-stock-rank-tech-portfolio-replay-readonly.mjs`
  - 新增 Playwright 只读网络 E2E。
- `frontend/tests/unit/tw-stock-monitor-static-check.mjs`
  - 更新既有断言以匹配当前“点击后运行只读回测”的产品行为。
- `frontend/tests/unit/tw-stock-cross-analysis-check.mjs`
  - 收窄方法正则范围，避免误捕获后续只读回测方法；允许“不是收益承诺”这类安全免责声明。

## 3. 前端展示结构

新增区块位于台股研究页首屏下方，标题为“今日复盘与历史模拟”，分三部分：

1. 今天先看什么
   - 展示 3 到 8 个优先标的。
   - 展示 symbol、中文名、Top 层级、决策标签、技术状态和简短原因。
   - 决策文案限定为：新增观察、继续观察、风险复盘、人工复核、仅观察、数据不足。

2. 为什么
   - 展示 qlib 层级、QuantDinger 趋势、MA/RSI/MACD/Bollinger 支持/中性/谨慎/数据不足数量。
   - 数据质量提示做成简短用户文案，不展示 run id、recorder id、source context 等工程字段。

3. 过去表现
   - 展示 qlib-only、qlib + trend、qlib + trend + indicators 三种规则。
   - 指标包括总收益、最大回撤、动作次数、费用税费估算、数据提示。
   - 默认不展示 `historicalActions` 明细，避免用户误解为今日动作。

页面显式展示：`只读历史模拟，不是投资建议，不连接券商，不生成订单。`

## 4. API 调用清单

允许并已实现：

- `GET /api/tw-stock/rank-tech-cross/latest`
- `GET /api/tw-stock/rank-tech-cross/observation-replay`
- `POST /api/tw-stock/rank-tech-cross/portfolio-replay`

`runTwStockPortfolioReplay` 在 API wrapper 层强制写入：

```js
persist: false
```

页面实际使用 `rank-tech-cross/latest` 与 `portfolio-replay`。`observation-replay` 已封装，供后续只读展开使用，本步不在首屏主动调用。

## 5. 只读网络 allowlist 与 forbidden request 统计

Playwright E2E 使用 mock API 验证网络行为，结果：

- `latest_request_count=3`
- `portfolio_replay_request_count=5`
- `portfolio_persist_false_count=5`
- `sim_request_count=1`
  - 该请求来自既有 K 线图模拟成交 marker 的只读 GET。
- `sim_write_request_count=0`
- `quick_trade_request_count=0`
- `broker_request_count=0`
- `real_order_request_count=0`
- `monitor_config_write_count=0`
- `monitor_scan_post_count=0`
- `monitor_alerts_write_count=0`
- `qlib_ops_post_count=0`
- `accepted_latest_switch_count=0`
- `provider_publish_refresh_count=0`
- `target_position_request_count=0`
- `target_weight_request_count=0`
- `forbidden_request_count=0`
- `page_error_count=0`

## 6. 文案安全检查结果

新增 Step 5 区块没有出现：

- 立即买入 / 立即卖出
- 自动买入 / 自动卖出
- 下单 / 提交订单
- 目标仓位 / 目标权重
- 上涨概率
- 收益承诺
- broker / quick-trade / real order 入口

历史模拟动作未被映射成买入/卖出/下单语义。首屏只展示聚合指标，不直接展示 `historicalActions`。

## 7. 测试命令与结果

已通过：

```bash
node frontend/tests/unit/tw-stock-rank-tech-portfolio-replay-check.mjs
TW_STOCK_MONITOR_BASE_URL=http://127.0.0.1:8010 node frontend/tests/e2e/tw-stock-rank-tech-portfolio-replay-readonly.mjs
node frontend/tests/unit/tw-stock-monitor-static-check.mjs
node frontend/tests/unit/tw-stock-cross-analysis-check.mjs
corepack pnpm build
```

说明：当前 8000 端口运行的是旧前端 bundle，不能代表本次源码修改。因此本次 Playwright E2E 临时启动当前源码 Vite 服务在 `http://127.0.0.1:8010/` 后执行。

## 8. 安全边界确认

本步未新增：

- 真实交易按钮。
- 模拟账户写入按钮。
- broker / quick-trade 调用。
- monitor config 保存。
- monitor scan / scan-all 触发。
- alert 写入。
- qlib ops POST。
- accepted latest 切换。
- provider publish / refresh。
- 目标仓位或目标权重输入。

`portfolio-replay` 虽然使用 POST，但仅用于复杂参数提交和只读计算，E2E 已验证所有请求均包含 `persist:false`。

## 9. 残余风险

- `observation-replay` 已封装但本步未在首屏主动展示；如果后续需要展开每日观察回放，应继续保持折叠和只读语义。
- 当前页面仍有其它历史功能线，例如模拟成交 marker 的只读 GET，会产生 `/api/tw-stock/sim/accounts` 读取请求；本步没有扩大为写入。
- 历史模拟指标依赖后端数据完整性，前端只做数据质量 warning 展示，不应被解释为未来收益。

## 10. Step 6 建议

进入最终验收与文档收口：

- 汇总 Step 1-5 API、页面、E2E 与安全边界。
- 对照最终用户第一性原则检查页面是否仍清晰、简单、准确、实用。
- 再跑一次只读 E2E 与 build，确认没有截图/JSON 临时产物需要提交。
