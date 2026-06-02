---
created_at: 2026-06-01
status: implementation_design
scope: quantdinger_tw_stock_qlib_option_c_integration
source_doc: docs/quantdinger_tw_option_c_integration_guide_cn.md
source_project: ../qlib
target_project: QuantDinger
---

# QuantDinger 接入 qlib Option C 台股量化研究信号实施文档

本文档面向 QuantDinger 项目的执行者，说明如何把 `../qlib` 项目已经完成的台股 Option C 量化研究成果，接入 QuantDinger 现有台股趋势、监控、回测和前端展示体系。

结论先行：

```text
可以结合。
第一阶段应把 qlib Option C 接成只读 research signal source。
它适合配合 QuantDinger 做趋势观察、候选股排序、人工复盘和后续只读回测验证。
它不应直接接入订单、仓位、broker、paper/live trading 或自动买卖。
```

---

## 1. qlib Option C 提供了什么

`../qlib` 项目当前提供的是一条已经审查收尾的台股横截面研究信号链路。

核心能力：

1. 使用 Yahoo-only 台股数据构建 qlib provider。
2. 使用固定 Alpha158 + LightGBM 模型 recorder 生成横截面分数。
3. 对 150 支已验收台股 universe 生成 daily prediction。
4. 输出 top30 / top50 research signals。
5. 提供 daily signal wrapper，带 dry-run、formal validation、wait-state 和 local artifact 输出。

核心入口：

```text
/home/chuliyang/qlib/examples/tw/run_option_c_daily_signal.py
```

核心输出：

```text
/home/chuliyang/qlib/data_tw/experiments/option_c_daily_signal/latest_signal.json
/home/chuliyang/qlib/data_tw/experiments/option_c_daily_signal/<run_id>/top30_signals.csv
/home/chuliyang/qlib/data_tw/experiments/option_c_daily_signal/<run_id>/top50_signals.csv
/home/chuliyang/qlib/data_tw/experiments/option_c_daily_signal/<run_id>/signal_summary.json
/home/chuliyang/qlib/data_tw/experiments/option_c_daily_signal/<run_id>/run_metadata.json
```

当前固定模型和数据契约：

```text
recorder_id: 950741cfd5f14ee5a05464fec3e12e0a
config: configs/tw_yahoo_primary_alpha158.yaml
provider: data_tw/experiments/yahoo_adjusted_primary/qlib_bin
market: tw_liquid_dyn
benchmark: TWII
universe_count: 150
model: Yahoo-only Alpha158 + LightGBM
```

安全边界：

```text
research_signal_not_order=true
diagnostic_only=true
不交易
不下单
不生成目标仓位
不连接 broker
不重训
不调参
不切 FinMind fallback
不自动刷新 qlib provider
```

---

## 2. QuantDinger 当前已有基础

QuantDinger 目前已经具备可接入 qlib 信号的台股基础设施。

### 2.1 已有台股趋势服务

文件：

```text
backend/app/services/tw_stock_trend.py
backend/app/routes/tw_stock.py
```

已有 API：

```text
GET /api/tw-stock/trend?symbol=2330&limit=120
GET /api/tw-stock/trends?symbols=2330,0050,00878&limit=120
```

已有输出包含：

```text
latest close/date
trend label
trend score
MA5/MA20/MA60
ret_5d/20d/60d
volume ratio
risk volatility
quality warnings
trading.orders_enabled=false
```

这适合与 qlib 的横截面排名并列展示：

```text
qlib rank/score 负责“横截面相对排序”
QuantDinger trend score 负责“单标的趋势解释”
```

### 2.2 已有台股监控服务

文件：

```text
backend/app/services/tw_stock_monitor.py
backend/app/routes/tw_stock.py
```

已有能力：

```text
monitor config
trend history
alerts
scan logs
quality warning
人工 decision_status
orders_enabled=false
```

这适合接入 qlib top30/top50 后做：

```text
研究候选池
人工观察名单
趋势变化提醒
quality warning
人工复盘状态
```

### 2.3 已有台股只读回测

文件：

```text
backend/app/services/backtest.py
backend/app/routes/backtest.py
backend/app/services/tw_stock_backtest_templates.py
backend/tests/test_tw_stock_backtest.py
```

已有 API：

```text
GET  /api/indicator/backtest/tw-stock/templates
POST /api/indicator/backtest
```

已有约束：

```text
market=TWStock
timeframe=1D only
long-only cash-equity simulation
leverage=1
persist=false by default
orders_enabled=false
connects_to_broker=false
paper_orders_enabled=false
live_trading_enabled=false
quick_trade_enabled=false
writes_orders=false
writes_positions=false
```

已有内置模板：

```text
ma_cross_builtin
rsi_builtin
macd_builtin
bollinger_builtin
```

因此 qlib 信号不需要重造回测引擎。它应该先作为候选股筛选器，再调用 QuantDinger 已有回测接口验证某个标的上的技术指标模板表现。

---

## 3. 结合后的产品形态

建议把接入后的功能命名为：

```text
qlib Option C 台股研究排序
```

用户看到的含义：

```text
今天 qlib 模型在 150 支已验收台股 universe 中，相对更看好的 top30/top50。
```

它可以配合 QuantDinger 已有能力形成三个层次：

### 3.1 排序层

来源：qlib Option C。

展示：

```text
rank
symbol
instrument
qlib score
asof
recorder id
bucket: top30/top50
```

用途：

```text
从 150 支 universe 中快速找候选股。
```

### 3.2 趋势解释层

来源：QuantDinger `TWStockTrendService`。

展示：

```text
trend label
trend score
latest close/date
MA 状态
5/20/60 日收益
成交量变化
数据质量 warning
```

用途：

```text
解释 qlib 排名前列的个股目前趋势是否顺畅、数据是否可靠。
```

### 3.3 回测验证层

来源：QuantDinger `BacktestService`。

展示：

```text
选定 symbol + 时间区间 + 内置模板
total return
max drawdown
win rate
total trades
equity curve
trades
execution assumptions
dataQuality
```

用途：

```text
对 qlib 候选股做只读历史模拟，帮助用户人工判断是否值得继续观察。
```

---

## 4. 必须保持的边界

本接入不改变 QuantDinger 台股主线的安全边界。

禁止：

```text
自动交易
自动买入/卖出
提交订单
paper order
live trading
broker/IBKR/quick_trade 调用
根据 qlib rank 生成 target position
根据 qlib score 生成仓位比例
把 qlib score 解释为收益率、胜率或涨幅
在 QuantDinger 中重训 qlib 模型
在 QuantDinger 中修改 qlib provider
自动切换 FinMind 补 qlib 数据
```

允许：

```text
读取 qlib local artifacts
校验 accepted run
展示 top30/top50
把 top symbols 加入人工观察列表
调用现有 TWStock trend API 做解释
调用现有 TWStock read-only backtest 做历史模拟
保存 research signal run/import 记录
保存用户人工复盘状态
```

页面措辞必须使用：

```text
研究信号
研究排序
候选观察
历史模拟
人工复盘
```

避免使用：

```text
买入
卖出
下单
推荐买入
自动策略
目标仓位
实盘信号
```

---

## 5. 推荐总体架构

第一阶段采用只读文件接入。

```text
/home/chuliyang/qlib
  -> latest_signal.json
  -> top30_signals.csv / top50_signals.csv
  -> signal_summary.json / run_metadata.json

QuantDinger backend
  -> QlibOptionCSignalReader
  -> validation / normalization
  -> /api/tw-stock/quant/signals/latest
  -> optional DB import
  -> TWStockTrendService enrichment
  -> BacktestService read-only validation

QuantDinger Vue
  -> 台股监控页新增 qlib research ranking panel
  -> 点击 symbol 查看趋势 / 跳转只读回测
```

不建议第一阶段让 QuantDinger 直接运行 qlib daily wrapper。理由：

```text
当前 qlib signal wrapper 已可人工或 cron 运行。
QuantDinger 第一阶段只需要稳定消费 accepted artifacts。
直接触发 qlib 命令会引入进程管理、环境、超时、日志和误触刷新边界。
```

---

## 6. 后端实施方案

### 6.1 新增 service：QlibOptionCSignalReader

建议新增：

```text
backend/app/services/tw_stock_qlib_option_c.py
```

职责：

1. 读取 qlib `latest_signal.json`。
2. 解析 `run_dir`。
3. 读取 `signal_summary.json`、`run_metadata.json`。
4. 校验 run 是 accepted normal run。
5. 读取 top30/top50 CSV。
6. 标准化 `TW2330 -> symbol=2330`。
7. 返回 QuantDinger API 结构。
8. 不写库、不调用 qlib 命令、不连接 broker。

环境变量：

```text
QLIB_TW_OPTION_C_ROOT=/home/chuliyang/qlib
QLIB_TW_OPTION_C_LATEST=data_tw/experiments/option_c_daily_signal/latest_signal.json
```

默认值可以写死为本地路径，但建议仍支持环境变量覆盖。

核心校验：

```text
latest_signal.exists
signal_summary.status == accepted
run_metadata.status == accepted
signal_summary.prediction_rows == 150
signal_summary.top30_rows == 30
signal_summary.top50_rows == 50
signal_summary.finite_prediction_share == 1.0
latest_signal.diagnostic_only == true
latest_signal.research_signal_not_order == true
signal_summary.diagnostic_only == true
signal_summary.research_signal_not_order == true
signal_summary.paper_trading_started == false
signal_summary.live_trading_started == false
signal_summary.target_trades_generated == false
signal_summary.executable_orders_generated == false
run_metadata.model_retraining_performed == false
run_metadata.model_tuning_performed == false
run_metadata.provider_switch_performed == false
run_metadata.FinMind_fallback_used == false
run_metadata.mixed_provider_fill_used == false
```

如果校验不通过，返回 degraded/blocked 状态，不返回 top signals 作为可用新信号。

建议返回对象：

```json
{
  "ok": true,
  "status": "accepted",
  "asof": "2026-06-01",
  "run_id": "option_c_daily_signal_20260601_20260601T121228Z",
  "source": {
    "root": "/home/chuliyang/qlib",
    "latest_signal": "data_tw/experiments/option_c_daily_signal/latest_signal.json",
    "run_dir": "data_tw/experiments/option_c_daily_signal/option_c_daily_signal_20260601_20260601T121228Z",
    "recorder_id": "950741cfd5f14ee5a05464fec3e12e0a"
  },
  "top30": [],
  "top50": [],
  "summary": {},
  "trading": {
    "orders_enabled": false,
    "connects_to_broker": false,
    "research_signal_not_order": true
  }
}
```

每条 signal：

```json
{
  "asof": "2026-06-01",
  "instrument": "TW3231",
  "symbol": "3231",
  "score": 0.133519245576231,
  "rank": 1,
  "bucket": "top30",
  "source_model_recorder": "950741cfd5f14ee5a05464fec3e12e0a",
  "diagnostic_only": true,
  "research_signal_not_order": true
}
```

### 6.2 新增 API

建议放在现有 `tw_stock_bp`：

```text
GET /api/tw-stock/quant/signals/latest
```

query 参数：

```text
bucket=top30|top50|all
enrichTrend=true|false
trendLimit=120
```

默认：

```text
bucket=top30
enrichTrend=false
trendLimit=120
```

不做趋势增强的响应只读 qlib 文件，速度快。

做趋势增强时，对返回 symbols 调用：

```text
TWStockTrendService.analyze_symbol(symbol=<symbol>, limit=<trendLimit>)
```

并把结果挂到每条 signal：

```json
{
  "symbol": "3231",
  "rank": 1,
  "score": 0.1335,
  "trend": {
    "ok": true,
    "label": "uptrend",
    "score": 68.2,
    "latest_date": "2026-06-01",
    "latest_close": 123.5,
    "warnings": []
  }
}
```

注意：`qlib score` 和 `trend.score` 是不同含义，API 字段不要都叫 `score` 而不区分。建议：

```text
qlib_score
qlib_rank
trend_score
trend_label
```

### 6.3 可选 API：单标的 qlib context

建议新增：

```text
GET /api/tw-stock/quant/signals/symbol/<symbol>
```

用途：

```text
在趋势页或回测页查看某个 symbol 是否在 latest top30/top50 中。
```

返回：

```json
{
  "symbol": "2330",
  "in_latest_universe": true,
  "in_top30": false,
  "in_top50": true,
  "qlib_rank": 42,
  "qlib_score": 0.0123,
  "asof": "2026-06-01",
  "run_id": "..."
}
```

### 6.4 可选落库

第一阶段可以不落库，直接只读文件。

如果要支持历史 run、人工复盘和 UI 对比，再新增表：

```text
qd_tw_quant_signal_runs
qd_tw_quant_signals
```

建议字段参考 qlib 文档，但第一阶段不要急于落库。更务实的做法：

```text
Phase Q1: readonly file API
Phase Q2: optional import-latest and DB history
```

如果落库，必须保持独立研究表，不复用：

```text
qd_strategy_positions
qd_strategy_trades
pending orders
broker/live trading tables
```

---

## 7. 与趋势预测的结合方式

QuantDinger 现有趋势服务是单标的技术趋势解释。qlib Option C 是横截面排序。两者结合后，不应简单相加成一个“买入分数”，而应做并列解释。

推荐展示组合：

| 维度 | 来源 | 含义 |
| --- | --- | --- |
| qlib_rank | qlib Option C | 在 150 支 universe 中的横截面排序 |
| qlib_score | qlib Option C | 模型排序分数，只用于排序 |
| trend_label | QuantDinger | 单标的趋势状态 |
| trend_score | QuantDinger | 单标的趋势强弱解释分 |
| quality_warnings | QuantDinger | 数据质量提示 |

推荐前端文案：

```text
qlib 排名靠前 + QuantDinger 趋势偏强：可加入人工重点观察。
qlib 排名靠前 + 趋势偏弱/数据 warning：先复核，不自动交易。
qlib 未入榜 + 趋势偏强：可作为趋势观察，不属于 qlib 今日 top 候选。
```

不要输出：

```text
综合买入分
买入概率
明日涨幅
建议仓位
自动买入
```

如确实需要一个页面排序，可以做 `research_priority`，但必须标记为展示排序而非交易建议。

示例规则：

```text
research_priority = qlib bucket/rank first, trend quality second
top30 且 trend ok 且无 stale warning 排在前面
top30 但 trend data stale 排在后面
top50 但非 top30 排在 top30 之后
```

---

## 8. 与回测的结合方式

qlib daily signal 本身是“某日横截面候选列表”，不是一套完整可回测交易规则。直接把 latest top30 当成历史买卖策略是不严谨的，因为当前 artifacts 只保留 daily latest run，不提供长期逐日 rank 历史。

因此第一阶段回测应采用以下方式：

```text
qlib signal 负责选股候选。
QuantDinger built-in templates 负责对候选股做历史技术规则模拟。
```

用户流程：

1. 打开 qlib top30/top50。
2. 选择一个 symbol。
3. 查看该 symbol 的 QuantDinger 趋势解释。
4. 点击“历史模拟/回测验证”。
5. 选择 MA/RSI/MACD/Bollinger 模板和日期区间。
6. 调用现有 `POST /api/indicator/backtest`：

```json
{
  "market": "TWStock",
  "symbol": "3231",
  "timeframe": "1D",
  "startDate": "2024-01-01",
  "endDate": "2026-06-01",
  "initialCapital": 1000000,
  "strategyId": "ma_cross_builtin",
  "strategyConfig": {
    "template": {
      "fastWindow": 5,
      "slowWindow": 20
    }
  },
  "persist": false,
  "enableMtf": false
}
```

回测结果只解释：

```text
这个 symbol 在过去一段时间内，用某个技术模板做历史模拟的结果。
```

不能解释成：

```text
qlib 模型历史收益
qlib top30 策略收益
明天应该买入
```

### 8.1 后续如果要回测 qlib 本身

需要另开工作，不应混入第一阶段。

真正回测 qlib Option C 策略需要：

1. 保存每天 topN signals 历史。
2. 明确 rebalance 频率。
3. 明确持仓权重。
4. 明确交易成本、滑点、涨跌停、容量。
5. 明确退场规则。
6. 用历史逐日 signal 做组合级回测。
7. 单独审查，仍不自动交易。

在这些完成前，QuantDinger 不应声称“已回测 qlib top30 策略”。

---

## 9. 前端实施方案

目标页面：

```text
/path/to/taiwan-stock-quant-platform-Vue/src/views/tw-stock-monitor/index.vue
```

建议新增一个紧凑的 research ranking 区块：

```text
qlib Option C 研究排序
```

布局建议：

```text
顶部：asof、run_id、状态、research-only 标签
Tab：Top30 / Top50
表格列：rank、symbol、qlib_score、trend_label、trend_score、latest_close、quality
操作：查看趋势、历史模拟、加入观察
```

按钮限制：

```text
允许：查看趋势、历史模拟、加入观察、刷新读取
禁止：买入、卖出、下单、自动交易、连接 broker、paper/live
```

点击 symbol：

```text
更新当前趋势图 symbol
或跳转现有台股趋势详情
```

点击历史模拟：

```text
打开 TWStock read-only backtest 模式
预填 market=TWStock
预填 symbol
预填 timeframe=1D
默认 strategyId=ma_cross_builtin
默认 persist=false
```

状态处理：

| API status | UI 行为 |
| --- | --- |
| `accepted` | 展示 top30/top50 |
| `missing_latest_signal` | 显示 qlib 尚未生成信号 |
| `blocked_validation_failed` | 显示校验失败，不展示为今日信号 |
| `wait_state_data_refresh_needed` | 显示 qlib 数据需要刷新，不自动刷新 |
| `read_error` | 显示读取失败和路径 |

---

## 10. 测试方案

### 10.1 后端 service tests

新增：

```text
backend/tests/test_tw_stock_qlib_option_c_signals.py
```

测试项：

1. mock qlib latest + accepted run，reader 返回 top30/top50。
2. `TW3231` 正确规范化为 `symbol=3231`。
3. `signal_summary.status != accepted` 时拒绝作为可用信号。
4. `research_signal_not_order != true` 时拒绝。
5. `prediction_rows != 150` 时拒绝。
6. CSV 缺失时返回清晰错误。
7. latest path 穿越或绝对路径越界时拒绝，防止读取任意文件。
8. reader 不 import/call broker、quick_trade、live trading。

### 10.2 后端 route tests

新增或扩展：

```text
backend/tests/test_tw_stock_quant_signal_api.py
```

测试项：

1. `GET /api/tw-stock/quant/signals/latest` 返回 research-only flags。
2. `bucket=top30` 返回 30 条。
3. `bucket=top50` 返回 50 条。
4. `enrichTrend=true` 时调用趋势服务并保留 trend summary。
5. qlib blocked 状态时 API 不返回 usable top signals。
6. 响应包含：

```text
trading.orders_enabled=false
trading.connects_to_broker=false
trading.research_signal_not_order=true
```

### 10.3 回测结合测试

已有 `test_tw_stock_backtest.py` 可以继续保留。

新增测试重点：

1. 从 qlib signal symbol 发起 TWStock backtest 请求仍然 `persist=false`。
2. qlib rank 不会进入 `tradeDirection`、`leverage`、`target position`。
3. 回测响应仍包含 no-order trading flags。

### 10.4 前端静态测试

在 QuantDinger-Vue 增加或扩展台股页面静态检查：

1. 页面出现 qlib research-only 标签。
2. 页面不出现自动买入、自动卖出、提交订单、broker、paper/live 下单入口。
3. Top30/Top50 tab 存在。
4. 历史模拟按钮只跳转 read-only backtest。

---

## 11. 分阶段执行计划

### Phase Q1：只读 API 接入

目标：

```text
QuantDinger 后端可以读取 qlib latest accepted top30/top50，并通过 API 返回。
```

改动：

```text
backend/app/services/tw_stock_qlib_option_c.py
backend/app/routes/tw_stock.py
backend/tests/test_tw_stock_qlib_option_c_signals.py
backend/tests/test_tw_stock_quant_signal_api.py
```

验收：

```text
accepted run 可读
blocked/wait-state 不被当成新信号
research-only flags 完整
无交易路径调用
```

### Phase Q2：趋势增强

目标：

```text
API 支持 enrichTrend=true，把 qlib rank 与 QuantDinger trend summary 合并返回。
```

改动：

```text
复用 TWStockTrendService
避免修改 trend score 算法
避免把两个 score 合成交易分
```

验收：

```text
top symbols 有 trend_label/trend_score/quality_warnings
趋势数据失败时 qlib signal 仍可展示，但标记 trend_unavailable
```

### Phase Q3：前端展示

目标：

```text
台股监控页展示 qlib Option C 研究排序。
```

改动：

```text
QuantDinger-Vue/src/views/tw-stock-monitor/index.vue
前端 API client
前端静态/smoke tests
```

验收：

```text
可切 top30/top50
可查看趋势
可进入历史模拟
无交易按钮
research-only 文案清楚
```

### Phase Q4：回测联动

目标：

```text
从 qlib ranking 中选择 symbol，预填 TWStock 只读回测。
```

改动：

```text
前端跳转或面板内发起 /api/indicator/backtest
默认 strategyId=ma_cross_builtin
默认 persist=false
默认 timeframe=1D
```

验收：

```text
回测结果显示 metrics/equityCurve/trades/dataQuality/executionAssumptions
不显示任何交易执行入口
```

### Phase Q5：可选落库和历史

目标：

```text
保存 qlib signal runs，支持历史对比和人工复盘。
```

注意：

```text
这是可选阶段，不影响第一阶段使用。
仍然只写 research tables。
```

---

## 12. 风险和对应处理

### 12.1 qlib 数据不够新

风险：

```text
latest_signal.asof 落后于今天或最新交易日。
```

处理：

```text
显示历史信号 asof。
不复制旧信号成今日信号。
不自动触发 qlib data refresh。
```

### 12.2 qlib 和 QuantDinger 数据源不一致

qlib 当前是 Yahoo-only adjusted provider；QuantDinger 台股日线优先 `qd_tw_stock_daily_bars` / FinMind raw mode。

风险：

```text
qlib score 和 QuantDinger trend/backtest 使用的数据可能不完全一致。
```

处理：

```text
页面注明 qlib score 来自 qlib Yahoo-only provider。
QuantDinger trend/backtest 使用 QuantDinger 本地台股日线。
不要把两者合成一个精确交易结论。
```

### 12.3 用户误解为买卖建议

处理：

```text
页面固定显示“研究信号，不是买卖建议或订单”。
API 固定返回 research_signal_not_order=true。
测试禁止交易词和交易入口。
```

### 12.4 未来想扩展到全市场

当前 qlib universe 是 150 支。数量少不是接入阻塞，因为它是已验收、质量可控的预测 universe。

扩展到更多股票需要在 qlib 侧先完成：

```text
数据覆盖审查
universe policy
IC/RankIC 复核
provider rebuild
daily signal wrapper 更新
新的审查收尾
```

QuantDinger 不应自行扩大 qlib universe。

---

## 13. 推荐给执行者的一句话

先在 QuantDinger 后端实现 qlib Option C 只读 signal reader 和 `/api/tw-stock/quant/signals/latest`，只接受 `/home/chuliyang/qlib/data_tw/experiments/option_c_daily_signal/latest_signal.json` 指向的 `status=accepted`、`research_signal_not_order=true` 的 top30/top50，并可选用现有 `TWStockTrendService` 做趋势增强，禁止接入任何交易、订单、broker、重训、调参或 qlib 数据刷新路径。

