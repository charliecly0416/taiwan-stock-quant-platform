# 台股排名技术交叉与组合回放 Step 5 执行文档：只读前端展示

生成时间：2026-06-06

前置报告：`docs/TW_STOCK_RANK_TECH_CROSS_AND_PORTFOLIO_REPLAY_STEP4_REPORT_CN.md`

## 1. Step 4 审查结论

Step 4 主线基本正确：

- 已新增不落库组合规则历史回放 service。
- 已新增 `POST /api/tw-stock/rank-tech-cross/portfolio-replay`，POST 仅用于复杂参数输入。
- 响应强制 `simulation_only=true`、`persist=false`、`writes_business_db=false`。
- 已补强 Step 3 的 `run_detail_blocked` / `empty_run_signals` 数据质量提示。
- 未接入 `TWStockSimAccountService`、`BacktestService`、broker、quick-trade、monitor 写入或 qlib ops。
- 未修改前端。

需要在 Step 5 注意的点：

- 当前 `backend/app/routes/tw_stock.py` 仍混有其它功能线的模拟账户路由，前端本步不得调用 `/api/tw-stock/sim/**`。
- `historicalActions` 是历史模拟解释，不是今日交易动作。前端普通用户第一屏不应直接展示完整动作列表。
- `totalReturn`、`maxDrawdown` 等只能标为“历史模拟表现”，不得写成未来收益、胜率、上涨概率或推荐依据。
- 前端安全测试必须把 `POST /api/tw-stock/rank-tech-cross/portfolio-replay` 作为只读计算 allowlist，同时继续拦截所有真正写入和交易路径。

## 2. 本步目标

在现有台股研究页面中增加只读展示，让普通用户能同时看到：

1. 今天先看什么。
2. 为什么进入新增观察、继续观察、风险复盘或人工复核。
3. 这套规则过去历史模拟表现如何。

本步只做展示和只读接口调用，不做任何交易、模拟账户写入、monitor 写入或 qlib ops。

## 3. 明确禁止

本步不得执行：

- 不调用 `/api/tw-stock/sim/**`。
- 不调用 `/api/quick-trade/**`。
- 不调用 `/api/broker/**`。
- 不调用任何真实 order API。
- 不调用 target position / target weight API。
- 不保存 monitor config。
- 不触发 monitor scan / scan-all。
- 不写 monitor alerts。
- 不调用 `/api/tw-stock/quant/ops/**` 的 POST。
- 不触发 qlib refresh、publish、provider mutation、accepted latest switching。
- 不运行 daily auto update。
- 不新增真实交易按钮、下单按钮、目标仓位输入、目标权重输入。
- 不把 `historical_add` / `historical_risk_reduce` 翻译成“买入/卖出/下单”。
- 不在普通用户第一屏展示工程字段、run id、内部 source context 或完整 historicalActions 明细。

允许：

- 调用 `GET /api/tw-stock/rank-tech-cross/latest`。
- 调用 `GET /api/tw-stock/rank-tech-cross/observation-replay`。
- 调用 `POST /api/tw-stock/rank-tech-cross/portfolio-replay`，但请求必须包含或等价归一化为 `persist=false`。
- 只读展示 `new_watch`、`continue_watch`、`risk_review`、`manual_review`、`observe_only`、`data_insufficient`。
- 只读展示三种 variant 的历史模拟 metrics。
- 展示数据质量 warning 和只读免责声明。

## 4. 前端范围

优先修改现有页面：

```text
frontend/src/views/tw-stock-monitor/index.vue
frontend/src/api/tw-stock.js
```

不新增独立路由，除非执行者确认现有页面过大导致维护风险过高。若必须新增页面，先停止并补 Step 5A 文档。

本步不修改：

```text
frontend/src/views/tw-stock-sim-account/*
backend/app/services/tw_stock_sim_account.py
backend/app/services/backtest.py
```

## 5. API 封装

在 `frontend/src/api/tw-stock.js` 新增只读函数：

```js
export function getTwStockRankTechCrossLatest (params) {
  return request({
    url: `${BASE_URL}/rank-tech-cross/latest`,
    method: 'get',
    params
  })
}

export function getTwStockObservationReplay (params) {
  return request({
    url: `${BASE_URL}/rank-tech-cross/observation-replay`,
    method: 'get',
    params
  })
}

export function runTwStockPortfolioReplay (data) {
  return request({
    url: `${BASE_URL}/rank-tech-cross/portfolio-replay`,
    method: 'post',
    data: {
      ...data,
      persist: false
    }
  })
}
```

要求：

- `runTwStockPortfolioReplay` 不得引用 sim account API。
- 不得把 portfolio replay 放在 `/sim/` 命名空间。
- 参数默认值在前端和后端保持一致：`bucket=top30`、`maxItems=30`、`initialCash=1000000`、`maxHoldings=10`、`lotSize=10`。

## 6. 页面结构

建议在 `tw-stock-monitor` 第一屏或第一屏下方新增一个只读区块：

```text
今日复盘与历史模拟
```

区块包含三部分。

### 6.1 今日优先复盘

数据源：

```text
GET /api/tw-stock/rank-tech-cross/latest
```

展示：

- 3 到 10 支优先标的。
- symbol / name。
- rank tier。
- decision label。
- 技术状态：强 / 中性 / 弱 / 数据不足。
- 简短 reason。

用户文案只使用：

```text
新增观察
继续观察
风险复盘
人工复核
仅观察
数据不足
```

禁止出现：

```text
立即买入
立即卖出
下单
提交订单
目标仓位
上涨概率
收益承诺
```

### 6.2 为什么

数据源仍来自 `rank-tech-cross/latest`。

展示为紧凑解释，不展示工程字段：

- qlib 层级：Top10 / Top30 / Top50。
- QuantDinger 趋势：偏强 / 中性 / 偏弱 / 数据不足。
- MA/RSI/MACD/Bollinger：支持 / 中性 / 谨慎 / 数据不足的数量。
- 数据质量提示。

不在普通第一屏展示：

```text
run_id
recorder_id
target_horizon
source_context
internal strategy id
```

### 6.3 过去表现

数据源：

```text
POST /api/tw-stock/rank-tech-cross/portfolio-replay
```

展示三列对照：

```text
qlib-only
qlib + trend
qlib + trend + indicators
```

每列展示：

- 总收益：`metrics.totalReturn`。
- 最大回撤：`metrics.maxDrawdown`。
- 动作次数：`metrics.actionCount`。
- 费用税费估算：`metrics.feeAndTax`。
- 数据质量提示。

可展示一条小型 equity curve，但不要把它做成交易入口。

默认不展示 `historicalActions`。如需要展开，必须使用折叠区，标题为：

```text
历史模拟动作明细
```

动作文案映射：

| API action | 前端文案 |
| --- | --- |
| `historical_add` | 历史模拟新增 |
| `historical_risk_reduce` | 历史模拟风险降低 |
| `historical_hold` | 历史模拟保留 |
| `historical_skip` | 历史模拟跳过 |

禁止映射为：

```text
买入
卖出
下单
成交
委托
```

## 7. 交互要求

只允许这些控件：

- bucket：Top30 / Top50 segmented control。
- 时间范围：近半年 / 近一年 / 自定义。
- variant：全部 / qlib-only / qlib+trend / qlib+trend+indicators。
- 刷新按钮。
- 数据质量 warning 展开。

不允许这些控件：

- 创建模拟账户。
- 生成模拟订单草稿。
- 确认模拟成交。
- 目标仓位 / 目标权重输入。
- 连接券商。
- 自动交易开关。
- monitor scan 触发按钮。
- qlib ops publish / refresh / accepted latest switch。

## 8. 状态处理

必须覆盖：

- loading。
- API blocked / read_error。
- no accepted runs。
- empty_run_signals。
- run_detail_blocked。
- missing_close。
- data_insufficient。
- 部分 variant 无结果。

当组合回放不可用时，页面仍应展示今日优先复盘；不要因为 portfolio replay 失败隐藏 rank-tech-cross/latest。

## 9. 测试要求

### 9.1 API 封装静态测试

新增或扩展 unit test，检查：

- `getTwStockRankTechCrossLatest` 使用 GET。
- `getTwStockObservationReplay` 使用 GET。
- `runTwStockPortfolioReplay` 使用 POST。
- `runTwStockPortfolioReplay` 强制 `persist=false`。
- 文件中本步新增函数不包含 `/sim/`、`quick-trade`、`broker`、`target_position`、`targetWeight`。

### 9.2 页面静态测试

新增或扩展：

```text
frontend/tests/unit/tw-stock-rank-tech-portfolio-replay-check.mjs
```

检查：

- 页面包含只读免责声明。
- 页面不包含“立即买入 / 立即卖出 / 自动买入 / 自动卖出 / 下单 / 提交订单 / 目标仓位 / 上涨概率 / 收益承诺”。
- 页面新增区块不引用 `draftTwStockSimOrder`、`confirmTwStockSimOrder`、`createTwStockSimAccount`。
- 页面新增区块不调用 `scanTwStockMonitor`、`scanAllTwStockMonitors`、`saveTwStockMonitorConfig`、`saveTwStockCrossAnalysisReview`。

### 9.3 只读网络 E2E

新增或扩展 Playwright 测试：

```text
frontend/tests/e2e/tw-stock-rank-tech-portfolio-replay-readonly.mjs
```

允许请求：

```text
GET /api/tw-stock/rank-tech-cross/latest
GET /api/tw-stock/rank-tech-cross/observation-replay
POST /api/tw-stock/rank-tech-cross/portfolio-replay
```

其中 portfolio replay POST 必须断言请求体：

```json
{
  "persist": false
}
```

禁止请求：

```text
/api/tw-stock/sim/**
/api/quick-trade/**
/api/broker/**
POST /api/tw-stock/monitor/config
POST /api/tw-stock/monitor/scan
POST /api/tw-stock/monitor/scan-all
POST /api/tw-stock/monitor/alerts
PUT /api/tw-stock/monitor/alerts/*
POST /api/tw-stock/quant/ops/**
accepted-latest switch
provider publish / refresh
target_position
targetWeight
```

验收计数：

```text
sim_request_count=0
quick_trade_request_count=0
broker_request_count=0
real_order_request_count=0
monitor_config_write_count=0
monitor_scan_post_count=0
monitor_alerts_write_count=0
qlib_ops_post_count=0
accepted_latest_switch_count=0
provider_publish_refresh_count=0
```

`portfolio_replay_request_count` 可以为 1，但必须满足：

```text
persist=false
simulation_only response=true
writes_business_db response=false
orders_enabled response=false
connects_to_broker response=false
```

## 10. 必跑命令

```text
node frontend/tests/unit/tw-stock-rank-tech-portfolio-replay-check.mjs
corepack pnpm build
```

如新增 Playwright E2E，则补跑：

```text
node frontend/tests/e2e/tw-stock-rank-tech-portfolio-replay-readonly.mjs
```

如果本步修改 `frontend/src/api/tw-stock.js`，也跑已有台股相关静态测试：

```text
node frontend/tests/unit/tw-stock-monitor-static-check.mjs
node frontend/tests/unit/tw-stock-cross-analysis-check.mjs
```

## 11. 验收标准

本步通过必须满足：

- 普通用户第一屏能看到今日优先复盘、原因和历史模拟表现。
- 所有新增展示都是只读研究语义。
- portfolio replay POST 请求体强制 `persist=false`。
- 不调用 `/sim/**`、broker、quick-trade、真实 order、monitor 写入、qlib ops。
- 不出现目标仓位、目标权重、上涨概率、收益承诺或自动交易暗示。
- 数据质量 warning 能被看见。
- build 和前端安全测试通过。

## 12. 报告要求

执行完成后新增：

```text
docs/TW_STOCK_RANK_TECH_CROSS_AND_PORTFOLIO_REPLAY_STEP5_REPORT_CN.md
```

报告必须包含：

1. Step 4 审查修正说明。
2. 修改文件清单。
3. 前端展示结构。
4. API 调用清单。
5. 只读网络 allowlist 与 forbidden request 统计。
6. 文案安全检查结果。
7. 测试命令与结果。
8. 安全边界确认。
9. 残余风险。
10. Step 6 建议：最终验收与文档收口。

## 13. 审核断点

本步完成后停止，等待审查：

```text
docs/TW_STOCK_RANK_TECH_CROSS_AND_PORTFOLIO_REPLAY_STEP5_REPORT_CN.md
```

审查通过后，再编写 Step 6 最终验收文档。
