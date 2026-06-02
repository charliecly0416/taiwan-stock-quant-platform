# 台股只读回测实施方案

更新时间：2026-05-25

## 1. 定位与边界

本文档说明后续如何把台股趋势研究扩展到可用的回测验证能力。目标是让用户可以对 `TWStock` 标的做历史模拟，验证指标或策略信号在过去数据上的表现，再由用户人工判断是否值得继续观察。

必须保持的边界：

- 只做台股趋势研究、自动监控提醒和人工决策。
- 回测是只读回测，不连接 broker。
- 不启用 live，不提交订单，不提交 paper order。
- 不调用 quick-trade、IBKR、MT5、Alpaca 或任何 broker 下单路径。
- 回测结果不能包装成投资建议，只能作为研究证据。

现状说明：后端 `BacktestService` 已有 `market=TWStock` 的基础 smoke 测试，能在 mocked 日线 K 线下跑出资金曲线、交易数和台股执行假设。但这还不是完整产品能力，因为真实数据归档、前端入口、结果解释、数据质量提示和经典指标模板仍需要补齐。

## 2. 最小目标

第一阶段只交付“能可信地跑台股日线回测”的闭环，不先追求复杂指标设计。

最小可用能力：

- API 接收 `market=TWStock`、`symbol`、`timeframe=1D`、日期区间、初始资金和策略来源。
- 策略来源可以是内置策略 ID，或指标 IDE 提供的 Python 指标代码。
- 后端只读取本地日线归档或受控数据源，不写持仓、不写订单、不触发执行 worker。
- 回测返回资金曲线、交易明细、核心指标、执行假设和数据质量提示。
- 前端可以从台股监控页或未来台股回测页发起回测，并显示“这是历史模拟，不是自动交易”。

建议第一阶段暂时只支持：

- 市场：`TWStock`
- 频率：`1D`
- 方向：现金股做多 `long`
- 撮合：信号确认后按下一根日线开盘价或当前引擎既有语义成交，必须在返回值中明确展示
- 仓位：按资金百分比模拟，不强制连接真实账户

## 3. 数据要求

台股回测不能依赖临时拉取少量 K 线。需要先建立稳定的本地日线归档。

数据层要求：

- 使用本地 `qd_tw_stock_daily_bars` 作为优先数据源。
- 外部 FinMind 只能作为补数来源，必须处理 token、限流、非 200 响应和数据延迟。
- 每个回测响应都带上 `dataQuality`：bar 数、起止日期、最新日期、缺口、是否 stale、数据来源、警告列表。
- 复权模式必须显式：默认可以先保持未复权，但返回 `adjustmentMode=raw`；后续支持除权息/拆并股调整时再增加 `adjusted`。
- 交易日历要按台股交易日处理，不能用自然日假设填充成交。
- 缺失成交量、价格为 0、未来日期、重复日期都应进入质量警告或直接拒绝回测。

归档优先级：

1. 先确保 0050、009816、00981A、00403A 和台股前 50 有稳定日线。
2. 再扩大到监控 universe。
3. 最后再考虑全市场批量归档和增量更新。

## 4. 后端实施路径

### 4.1 API contract

建议新增或规范化一个台股只读回测入口，也可以复用现有 `/api/indicator/backtest`，但必须对 `market=TWStock` 做清晰约束。

请求示例：

```json
{
  "market": "TWStock",
  "symbol": "2330",
  "timeframe": "1D",
  "startDate": "2024-01-01",
  "endDate": "2026-05-22",
  "initialCapital": 1000000,
  "strategyId": "ma_cross_builtin",
  "strategyConfig": {
    "position": { "entryPct": 1.0 }
  },
  "persist": false
}
```

响应至少包含：

- `metrics.totalReturn`
- `metrics.maxDrawdown`
- `metrics.winRate`
- `metrics.totalTrades`
- `metrics.exposure`
- `metrics.benchmarkReturn`
- `equityCurve[]`
- `trades[]`
- `executionAssumptions`
- `dataQuality`
- `trading.orders_enabled=false`
- `trading.connects_to_broker=false`

### 4.2 数据读取

优先复用并整理现有链路：

- `TWStockDataSource`：负责外部数据源规范化。
- `KlineService`：负责 `TWStock:1D` K 线获取和缓存。
- `BacktestService`：负责指标执行和历史模拟。

建议把“获取台股日线 + 质量检查”抽成一个可复用函数，供趋势页、监控扫描和回测共同使用。这样前端看到的走势图数据和回测用到的数据不会互相矛盾。

### 4.3 模拟执行假设

台股默认执行假设要显式返回：

- 币种：`TWD`
- 时区：`Asia/Taipei`
- 市场：`TWStock`
- 交易频率：`1D`
- 默认手续费/税费代理：当前可继续使用 `commission=0.002925`
- 默认滑点：例如 `slippage=0.001`
- 方向：现金股做多
- 融资、融券、借券、当冲：第一阶段不支持
- 整股/零股：第一阶段可以先不强制，但必须返回 `lotSize=1000`、`lotSizeEnforced=false`

后续若要提高真实度，再增加：

- 卖出证券交易税单独建模
- 最小交易单位和零股策略
- 漲跌停无法成交
- 除权息现金流
- 成交量容量限制

### 4.4 存储策略

第一阶段建议默认 `persist=false`，只返回一次性结果，避免污染历史表。

当用户需要保存结果时，再写入：

- `qd_backtest_runs`
- `qd_backtest_trades`
- `qd_backtest_equity_points`

写入前必须确认：

- `run_type` 是 backtest/simulation，不是 order。
- 不写 `qd_user_positions`。
- 不写 pending order。
- 不调用任何 broker adapter。

## 5. 前端实施路径

前端建议分两步做。

第一步：把台股入口接到“只读回测”。

- 台股监控页选中股票后，提供“回测验证”入口。
- 入口只传 `market=TWStock`、`symbol`、日期区间、内置策略 ID 或当前指标代码。
- 页面显示数据质量、执行假设和结果，不出现交易按钮。
- 如果后端返回数据不足，页面直接显示需要先更新本地日线归档。

第二步：让指标 IDE 支持 `TWStock`。

- 市场选择支持 `TWStock`。
- 标的选择复用监控 universe。
- 时间框架只开放 `1D`。
- 默认资金单位显示 TWD。
- 回测按钮文案应强调“历史模拟”。
- 结果页显示手续费、滑点、复权模式、bar 数、数据最新日期。

AI 分析页后续可以恢复“回测验证”跳转，但必须满足：

- 只跳台股只读回测模式。
- 不让用户误以为是在验证 AI 报告本身，除非 AI 报告已经生成了明确可执行的指标规则。
- 页面展示策略来源：内置经典指标、用户指标代码、或 AI 生成临时指标。

## 6. 经典指标模板

具体参数设计可以后置，但建议先准备几个经典模板用于验证回测通路：

- 双均线交叉：MA5/MA20 或 MA20/MA60。
- RSI 反转：低位买入、高位卖出。
- MACD 金叉死叉。
- Bollinger 突破或均值回归。
- Donchian/channel breakout。
- 量价突破：价格突破区间高点且成交量高于均量。

这些模板的目标不是保证收益，而是验证：

- 指标能在 `TWStock` 日线数据上运行。
- 买卖信号能正确进入回测引擎。
- 交易明细、资金曲线和指标统计能被前端解释。

## 7. 测试与验收

后端测试：

- 使用 mocked bars 测试 `BacktestService` 跑 `TWStock`。
- 测试无数据时返回清晰错误。
- 测试台股默认手续费、滑点、方向和执行假设。
- 测试 `trading.orders_enabled=false`、`connects_to_broker=false`。
- 测试不写订单、不写持仓、不调用 broker。

前端测试：

- 静态检查台股回测页面没有 quick-trade、broker、paper/live order、提交订单按钮。
- smoke 测试选择 `TWStock 2330` 可以发起 mock 回测并渲染结果。
- smoke 测试无数据时显示“需要更新本地日线归档”。
- 检查执行假设和数据质量警告可见。

验收标准：

- 本地日线归档有数据时，`TWStock 2330` 可跑完 1D 回测。
- 数据不足时，错误清楚指向数据归档问题，不显示空白页。
- 回测结果包含收益、最大回撤、胜率、交易数、资金曲线和交易明细。
- 页面没有任何自动交易、broker 连接或 live 启用入口。
- CI 能证明台股研究栈仍保持只读研究边界。

## 8. 推荐阶段拆分

### Phase B1：只读回测 API 固化

- 固化 `TWStock` 回测请求/响应 contract。
- 补齐真实本地日线数据读取和质量提示。
- 默认 `persist=false`，只返回结果。
- 继续保留并扩展 `backend/tests/test_tw_stock_backtest.py`。

### Phase B2：前端台股回测结果页

- 新增台股只读回测页面或改造指标 IDE 的 `TWStock` 模式。
- 展示资金曲线、交易列表、指标摘要、执行假设和数据质量。
- 台股监控页“回测验证”跳转到该模式。

### Phase B3：经典指标模板

- 增加 MA、RSI、MACD、Bollinger、Donchian、量价突破模板。
- 模板只用于研究和回测，不自动下单。
- 支持用户复制模板后手动调整参数。

### Phase B4：保存和对比

- 允许用户保存回测结果。
- 支持不同指标、参数和日期区间对比。
- 支持与 0050 或对应产业 benchmark 对比。

## 9. 使用提醒

台股回测的价值是排除明显无效的想法、发现信号在不同市场阶段的表现，并辅助人工复盘。它不能证明未来收益，也不能替代实时风险控制。每次查看结果时，优先看数据质量、交易次数、最大回撤和样本区间，再看总收益。
