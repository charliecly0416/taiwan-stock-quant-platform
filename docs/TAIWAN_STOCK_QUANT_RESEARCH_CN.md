# QuantDinger 台股量化研究与落地方案

本文面向“把 QuantDinger 改造成可研究、回测、运行台湾股票策略”的工程落地。结论先行：

- **最小可行路线**：新增 `TWStock` 市场类型和 `TWStockDataSource`，先支持台股日线 K 线、最新价、标的搜索、指标策略回测。
- **数据源优先级**：研究/回测用 FinMind 或自建 TWSE/TPEx 归档；当日盘后和市场广度用 TWSE/TPEx OpenAPI；实时和实盘行情优先 IBKR 或付费行情源。
- **实盘交易路线**：优先复用现有 IBKR 通道，增加台股合约映射、TWD 货币、TWSE 交易所、1000 股整股单位等约束。先纸面盘，再小资金。
- **不建议一开始做高频**：台股公开免费 API 更适合日线和盘后研究；分钟级、逐笔、盘口和低延迟实盘需要付费行情和更严格的撮合/风控工程。

截至 2026-05-23，本项目内未发现台股专用实现；已有 A 股、港股、美股、MOEX、Crypto、Forex、Futures 等数据源，台股适配可以沿用现有市场抽象。

---

## 1. 项目现状

QuantDinger 后端位于 `backend/`，是 Flask + PostgreSQL + Redis 的量化平台。核心链路如下：

```text
前端/Agent/API
  -> /api/kline, /api/backtest, /api/strategy, /api/ibkr
  -> KlineService / BacktestService / StrategyRuntime
  -> DataSourceFactory
  -> 各市场 DataSource
  -> 外部行情 API / Broker API
```

### 1.1 已有能力

- 多市场 K 线接口：`BaseDataSource.get_kline()` 统一返回：

```python
{"time": int, "open": float, "high": float, "low": float, "close": float, "volume": float}
```

- 数据源工厂：`backend/app/data_sources/factory.py`
  - 目前 canonical market 包括 `Crypto`、`Forex`、`Futures`、`USStock`、`CNStock`、`HKStock`、`MOEX`。
  - 回测和 K 线 API 都依赖请求里的 `market` 字段，不再根据 symbol 猜市场。

- K 线 API：`GET /api/kline?market=USStock&symbol=AAPL&timeframe=1D&limit=300`
- 回测 API：`POST /api/backtest`
  - 支持 `indicatorCode`、`symbol`、`market`、`timeframe`、`startDate`、`endDate`、手续费、滑点、杠杆、方向等参数。
  - 非 Crypto 市场默认走标准单周期回测。

- 策略形态：
  - `IndicatorStrategy`：基于 dataframe 生成 `buy` / `sell` 列，最适合先做台股日线因子和信号验证。
  - `ScriptStrategy`：逐 bar 事件驱动，适合后续实盘执行和状态化风控。

- 部署：
  - `docker-compose.yml` 启动 PostgreSQL、Redis、Backend、Frontend。
  - 默认前端使用 GHCR 预构建镜像，后端本地 build。

### 1.2 台股改造的最小入口

建议新增：

```text
backend/app/data_sources/tw_stock.py
```

并修改：

```text
backend/app/data_sources/factory.py
backend/migrations/init.sql 或新增迁移 SQL
backend/tests/test_tw_stock_data_source.py
```

前端若已经能手动输入市场和标的，后端支持后即可先通过 API 和 Agent 使用；若要完整 UI 体验，再改前端市场枚举和热门标的。

---

## 2. 台股市场工程约束

### 2.1 市场范围

台股至少分三类：

| 范围 | 说明 | QuantDinger 建议市场 |
|---|---|---|
| TWSE 上市 | 台湾证券交易所上市股票、ETF | `TWStock` |
| TPEx 上柜 | 证券柜台买卖中心上柜股票 | `TWStock`，内部字段 `exchange=TPEx` |
| TAIFEX 期货/选择权 | 台指期、小台、电子期、金融期、个股期货、选择权 | 后续单独做 `TWFutures` |

第一阶段只做 `TWStock`。TAIFEX 合约乘数、夜盘、保证金、结算日和期权行权价体系不同，不应混进股票数据源。

### 2.2 交易规则对回测的影响

台股策略不能简单套用美股或加密货币假设：

- 主要现货交易时段为台湾时间白天，日线策略应以 `Asia/Taipei` 作为交易日边界。
- 普通股整股通常以 1000 股为一张；零股有独立交易机制，初期建议回测和实盘都按整股。
- 涨跌幅限制会导致信号成交价不可达，回测需要至少支持“涨停买不进、跌停卖不出”的保守选项。
- T+2 交割、现金余额、融资融券、借券卖出、现股当冲资格都会影响真实可交易性。
- 股票、ETF、权证、受益证券的交易单位和风险特性不同，标的表应保存 `instrument_type`。

---

## 3. 数据源研究

### 3.1 官方数据源

#### TWSE OpenAPI

TWSE OpenAPI Swagger 的 base URL 为：

```text
https://openapi.twse.com.tw/v1
```

搜索结果和 Swagger 内容显示，常用端点包括：

```text
/exchangeReport/STOCK_DAY_ALL        上市个股日成交资讯
/exchangeReport/STOCK_DAY_AVG_ALL    上市个股日收盘价及月平均价
/exchangeReport/BWIBBU_ALL           本益比、殖利率、股价净值比
/exchangeReport/MI_INDEX             每日收盘行情-大盘统计资讯
/holidaySchedule/holidaySchedule     集中市场开休市日期
/indicesReport/TAI50I                台湾 50 指数历史资料
/indicesReport/MI_5MINS_HIST         加权指数历史资料
```

适用场景：

- 当日盘后行情。
- 市场宽度、指数、估值、融资融券、注意股、除权息预告等研究因子。
- 官方字段校验和数据对账。

局限：

- 单一端点多为“当天或指定报告”形态，不一定适合直接回补多年个股历史。
- 字段多为繁体中文，需要做稳定的字段映射。
- 免费公开接口不应高频轮询，需缓存和限速。

#### TPEx OpenAPI

TPEx OpenAPI 提供上柜、兴柜、债券、指数、财报等 API，Swagger 地址：

```text
https://www.tpex.org.tw/openapi/
```

常用端点包括：

```text
/tpex_mainboard_daily_close_quotes    上柜股票行情
/tpex_mainboard_quotes                上柜股票收盘行情
/tpex_mainboard_peratio_analysis      上柜本益比、殖利率、股价净值比
/tpex_3insti_daily_trading            上柜三大法人买卖明细
/tpex_index                           柜买指数历史资料
```

适用场景：

- 上柜股票日线、估值、三大法人、指数资料。
- 与 TWSE 组成完整台股现货研究池。

#### TAIFEX

TAIFEX 官网提供每日行情、三大法人、未平仓、大额交易人、交易日历、保证金等资料，并有 OpenAPI/下载入口。项目第一阶段不建议直接做实盘期货，但可以规划：

- `TWFuturesDataSource`：台指期、小台、个股期货日线/分钟线。
- `TWFuturesBroker`：独立风控，不复用股票整股逻辑。

### 3.2 FinMind

FinMind 是台股量化最实用的快速落地源之一，文档显示 `TaiwanStockPrice` 可通过：

```text
https://api.finmindtrade.com/api/v4/data
```

典型参数：

```text
dataset=TaiwanStockPrice
data_id=2330
start_date=2024-01-01
end_date=2024-12-31
token=<optional>
```

返回字段通常包含：

```text
date, stock_id, Trading_Volume, Trading_money, open, max, min, close, spread, Trading_turnover
```

适用场景：

- 快速获得多年日线历史。
- 台股基本面、月营收、法人、融资融券、筹码资料。
- 研究和回测阶段减少自己维护爬取逻辑。

注意：

- 生产系统要配置 token，并尊重请求频率。
- 所有第三方聚合数据都要定期与 TWSE/TPEx 官方盘后资料抽样对账。

### 3.3 yfinance

可作为兜底源：

```text
2330.TW  台积电
2317.TW  鸿海
2454.TW  联发科
0050.TW  元大台湾50
```

优点是接入成本低、全球访问稳定性通常较好；缺点是台股字段、复权、分钟历史和数据完整性不适合作为唯一生产源。

### 3.4 推荐数据源优先级

第一阶段：

```text
日线历史：FinMind TaiwanStockPrice
当日盘后：TWSE / TPEx OpenAPI
兜底：yfinance
```

第二阶段：

```text
本地 PostgreSQL 分区表归档
每天盘后自动增量更新
官方 OpenAPI 对账
```

第三阶段：

```text
IBKR 或授权行情商实时行情
分钟线/逐笔/盘口数据付费接入
```

---

## 4. 台股数据源实现设计

### 4.1 Symbol 规范

建议后端内部统一使用纯代码：

```text
2330
0050
2317
```

兼容输入：

```text
2330.TW
TWSE:2330
2330.TWSE
TPEX:6488
```

归一化结果：

```python
{
    "symbol": "2330",
    "exchange": "TWSE",
    "currency": "TWD",
    "instrument_type": "stock"
}
```

上柜标的可通过标的表判断 `exchange=TPEx`；若用户传 `TPEX:6488` 则优先使用显式 exchange。

### 4.2 `TWStockDataSource` 接口

文件：

```text
backend/app/data_sources/tw_stock.py
```

类：

```python
class TWStockDataSource(BaseDataSource):
    name = "TWStock/multi-source"

    def get_kline(self, symbol, timeframe, limit, before_time=None, after_time=None):
        ...

    def get_ticker(self, symbol):
        ...
```

支持范围：

| timeframe | 第一阶段 | 说明 |
|---|---:|---|
| `1D` | 支持 | 主路径 |
| `1W` | 支持 | 由日线重采样 |
| `1m`/`5m`/`15m`/`30m`/`1H`/`4H` | 暂不支持或 yfinance 兜底 | 不建议用于正式台股回测 |

### 4.3 日线获取逻辑

推荐顺序：

1. FinMind 拉取指定窗口。
2. 若窗口包含最近交易日，使用 TWSE/TPEx OpenAPI 更新当日盘后行情。
3. 若失败，尝试 yfinance。
4. 统一转换为 QuantDinger K 线格式。
5. 使用 `BaseDataSource.filter_and_limit()` 做时间过滤。

伪代码：

```python
def get_kline(self, symbol, timeframe, limit, before_time=None, after_time=None):
    norm = normalize_tw_symbol(symbol)
    if timeframe not in ("1D", "1W"):
        return self._fetch_yfinance_intraday_or_empty(norm, timeframe, limit, before_time, after_time)

    start, end = self._date_range(timeframe, limit, before_time, after_time)
    bars = self._fetch_finmind_daily(norm.symbol, start, end)

    if self._needs_latest_patch(end):
        latest = self._fetch_official_latest(norm)
        bars = merge_latest_bar(bars, latest)

    if not bars:
        bars = self._fetch_yfinance_daily(norm, start, end)

    if timeframe == "1W":
        bars = resample_daily_to_weekly(bars, tz="Asia/Taipei")

    return self.filter_and_limit(bars, limit, before_time, after_time, truncate=(after_time is None))
```

### 4.4 字段映射

FinMind:

| FinMind 字段 | QuantDinger 字段 |
|---|---|
| `date` | `time`，Asia/Taipei 日期 00:00 转 Unix 秒 |
| `open` | `open` |
| `max` | `high` |
| `min` | `low` |
| `close` | `close` |
| `Trading_Volume` | `volume` |

TWSE `STOCK_DAY_ALL` 常见字段需做繁体映射，建议按多候选字段解析：

```python
FIELD_CANDIDATES = {
    "code": ["Code", "證券代號", "股票代號"],
    "name": ["Name", "證券名稱", "股票名稱"],
    "volume": ["TradeVolume", "成交股數"],
    "open": ["OpeningPrice", "開盤價"],
    "high": ["HighestPrice", "最高價"],
    "low": ["LowestPrice", "最低價"],
    "close": ["ClosingPrice", "收盤價"],
}
```

### 4.5 时间和时区

项目 K 线 `time` 是 Unix 秒。台股日线建议固定为：

```text
Asia/Taipei 当日 00:00:00 -> Unix 秒
```

这样策略 dataframe 的日线索引稳定，不受服务器 UTC 或 Docker `TZ` 影响。显示层可再按用户时区渲染。

### 4.6 缓存策略

沿用 `KlineService` 的缓存，另在 `TWStockDataSource` 内加入轻量请求缓存：

- 日线历史：30 分钟到 6 小时。
- 当日盘后：交易日 14:30 后可缓存到下个交易日。
- 标的列表：每天更新一次。

若引入本地历史表，则 API 查询优先走数据库，外部 API 只用于补缺。

---

## 5. 标的池与数据库

现有 `qd_market_symbols` 已支持：

```text
market, symbol, name, exchange, currency, is_hot, sort_order
```

建议新增台股热门标的：

```sql
INSERT INTO qd_market_symbols (market, symbol, name, exchange, currency, is_hot, sort_order)
VALUES
('TWStock', '2330', '台積電', 'TWSE', 'TWD', 1, 1000),
('TWStock', '2317', '鴻海', 'TWSE', 'TWD', 1, 990),
('TWStock', '2454', '聯發科', 'TWSE', 'TWD', 1, 980),
('TWStock', '0050', '元大台灣50', 'TWSE', 'TWD', 1, 970),
('TWStock', '0056', '元大高股息', 'TWSE', 'TWD', 1, 960);
```

如需更严谨，新增字段：

```sql
ALTER TABLE qd_market_symbols ADD COLUMN IF NOT EXISTS instrument_type VARCHAR(32) DEFAULT '';
ALTER TABLE qd_market_symbols ADD COLUMN IF NOT EXISTS lot_size INTEGER DEFAULT 1;
ALTER TABLE qd_market_symbols ADD COLUMN IF NOT EXISTS price_tick_json TEXT DEFAULT '';
```

第一阶段也可以不改 schema，将 `lot_size` 和 `instrument_type` 放在代码映射或扩展表，避免迁移面过大。

---

## 6. 回测设计

### 6.1 第一阶段回测假设

台股日线回测建议默认：

```text
market=TWStock
timeframe=1D
commission=0.002925  # Phase 1 把券商费和卖出税折算进单一成本参数
tax_sell=folded_into_commission
slippage=0.001
lot_size=1000
trade_direction=long
leverage=1
```

说明：

- 证券交易税通常在卖出时收取；当前 Phase 1 已在 HTTP 回测入口对 `TWStock` 默认使用 `commission=0.002925`、`slippage=0.001`，并在 `executionAssumptions` 中标记 `sellTaxMode=folded_into_commission`。长期应扩展回测引擎支持 `sellTaxPct`。
- 若做 ETF，税率和费用可能不同，应通过策略配置或标的元数据区分。
- 台股现货初期默认 `tradeDirection=long`，避免融券、借券、当冲资格引入额外复杂性。
- 当前 Phase 1 的回测结果会暴露 `lotSize=1000` 和 `lotSizeEnforced=false`；也就是说已记录台股整股假设，但撮合引擎尚未强制把成交股数向下取整到 1000 股。这个限制必须在进入实盘或更严格组合回测前补齐。

### 6.2 回测数据完整性检查

每次回测前建议检查：

- 日期范围内交易日数量是否合理。
- `open/high/low/close` 是否为 0 或缺失。
- `high >= max(open, close)`，`low <= min(open, close)`。
- 成交量是否为非负数。
- 是否存在重复日期。
- 除权息前后是否需要复权。第一阶段可以使用未复权价格，但文档和 UI 必须标明；做长期趋势或收益比较时建议支持前复权。

### 6.3 台股策略开发路径

先使用 `IndicatorStrategy`：

```python
my_indicator_name = "TWStock MA Momentum"
my_indicator_description = "台股日线均线动量策略示例。"

# @param fast_len int 20 Fast MA
# @param slow_len int 60 Slow MA
# @param volume_len int 20 Volume MA
# @strategy stopLossPct 0.08
# @strategy takeProfitPct 0.20
# @strategy entryPct 0.9
# @strategy tradeDirection long

df = df.copy()
fast_len = int(params.get("fast_len", 20))
slow_len = int(params.get("slow_len", 60))
volume_len = int(params.get("volume_len", 20))

df["ma_fast"] = df["close"].rolling(fast_len).mean()
df["ma_slow"] = df["close"].rolling(slow_len).mean()
df["vol_ma"] = df["volume"].rolling(volume_len).mean()

trend = df["ma_fast"] > df["ma_slow"]
volume_ok = df["volume"] > df["vol_ma"]
raw_buy = trend & volume_ok & (df["ma_fast"].shift(1) <= df["ma_slow"].shift(1))
raw_sell = (df["ma_fast"] < df["ma_slow"]) & (df["ma_fast"].shift(1) >= df["ma_slow"].shift(1))

df["buy"] = raw_buy.fillna(False).astype(bool)
df["sell"] = raw_sell.fillna(False).astype(bool)

output = {
    "name": my_indicator_name,
    "plots": [
        {"name": "MA Fast", "data": df["ma_fast"].tolist()},
        {"name": "MA Slow", "data": df["ma_slow"].tolist()},
    ],
    "signals": []
}
```

### 6.4 中长期扩展

台股回测引擎应逐步补齐：

- `lotSize`：按 1000 股向下取整，现金不足不成交。
- `sellTaxPct`：卖出税独立计算。
- `priceLimitAware`：涨跌停成交约束。
- `corporateActionMode`：未复权、前复权、后复权。
- `cashSettlementDays`：T+2 现金可用约束。
- `universeBacktest`：多股票横截面轮动。

---

## 7. 测试方案

### 7.1 单元测试

新增：

```text
backend/tests/test_tw_stock_data_source.py
```

覆盖：

- symbol 归一化：
  - `2330`
  - `2330.TW`
  - `TWSE:2330`
  - `TPEX:6488`
- FinMind JSON 到 K 线转换。
- TWSE/TPEx 字段映射。
- 日线转周线。
- `before_time` / `after_time` 窗口过滤。
- 空数据、脏数据、逗号数字、`--`、停牌字段。

建议用 fixture 模拟 HTTP 响应，避免测试依赖外网。

### 7.2 集成测试

可增加一个需要外网和 token 的可选测试：

```bash
TW_STOCK_LIVE_TEST=1 FINMIND_TOKEN=xxx python -m pytest backend/tests/test_tw_stock_data_source.py
```

测试：

- `TWStock:2330` 最近 100 根日线。
- `TWStock:0050` 最近 100 根日线。
- `TWStock:6488` 上柜标的，如果标的表可识别 TPEx。

### 7.3 API 验证

启动后端后：

```bash
curl "http://localhost:5000/api/kline?market=TWStock&symbol=2330&timeframe=1D&limit=120"
```

预期：

```json
{
  "code": 1,
  "msg": "success",
  "data": [
    {"time": 1704067200, "open": 0, "high": 0, "low": 0, "close": 0, "volume": 0}
  ]
}
```

实际数值应非零，且按时间升序。

### 7.4 回测验证

用台积电：

```json
{
  "market": "TWStock",
  "symbol": "2330",
  "timeframe": "1D",
  "startDate": "2022-01-01",
  "endDate": "2025-12-31",
  "initialCapital": 1000000,
  "commission": 0.002925,
  "slippage": 0.001,
  "leverage": 1,
  "tradeDirection": "long",
  "enableMtf": false
}
```

验证：

- 回测能成功完成。
- 交易日期只落在有 K 线的交易日。
- 总交易数、胜率、最大回撤、权益曲线不是空值。
- 同一策略重复回测结果稳定。

---

## 8. 实盘与纸面盘

### 8.1 推荐路线：IBKR

项目已有 IBKR 文档和接口，当前文档写的是美股。台股可在同一通道上扩展合约：

```python
Stock(symbol="2330", exchange="TWSE", currency="TWD")
```

需要验证：

- 账户是否开通台湾市场交易权限。
- 是否订阅 TWSE/TPEx 实时或延迟行情。
- IBKR 是否支持目标标的所在交易所；部分上柜/兴柜标的可能不可交易。
- 订单单位、最小跳动、涨跌停、现金余额、TWD 换汇。

### 8.2 Broker 适配点

检查并扩展：

```text
backend/app/routes/ibkr.py
backend/app/services/strategy_lifecycle.py
backend/app/utils/broker_session.py
backend/app/utils/local_brokers.py
```

目标：

- `marketType=TWStock` 时创建 TWSE/TWD 合约。
- 下单数量按 `lot_size=1000` 校验。
- 默认禁止 short。
- 对 `market` 订单增加保护：可选改为限价单，限价基于最新价和滑点。
- 在 pending order worker 中记录外部订单号、成交均价、部分成交状态。

### 8.3 纸面盘阶段

上线真实资金前必须经过：

1. 历史回测。
2. Replay/paper trading：用最新日线或分钟线模拟信号，不发真实订单。
3. IBKR paper account：真实 broker API，纸面账户。
4. 小资金、白名单标的、最大单笔金额、最大日交易次数。
5. 运行监控和手动 kill switch。

---

## 9. 部署方案

### 9.1 Docker 本地部署

复制环境文件：

```bash
cp backend/env.example backend/.env
```

配置建议：

```ini
SECRET_KEY=<生成强随机值>
TZ=Asia/Taipei
FINMIND_TOKEN=<可选但建议>
TW_STOCK_PROVIDER=finmind,twse,tpex,yfinance
```

启动：

```bash
docker compose pull
docker compose up -d
```

访问：

```text
Frontend: http://localhost:8888
Backend:  http://localhost:5000
```

### 9.2 生产部署

建议：

- PostgreSQL 使用持久化磁盘和每日备份。
- Redis 只做缓存，不能作为唯一行情存储。
- 后端容器设置 `TZ=Asia/Taipei`，但代码仍显式使用 `Asia/Taipei` 处理台股交易日。
- 外部 API token 只放 `.env` 或密钥管理，不写入代码。
- IBKR TWS/Gateway 与后端网络隔离，仅允许必要端口访问。
- 开启日志轮转和异常告警。

### 9.3 盘后任务

当前已实现脚本：

```text
backend/scripts/sync_tw_stock_symbols.py
backend/scripts/archive_tw_stock_daily.py
backend/scripts/archive_tw_stock_corporate_actions.py
backend/scripts/archive_tw_stock_institutional_trades.py
backend/scripts/archive_tw_stock_margin_trading.py
backend/scripts/archive_tw_stock_monthly_revenue.py
backend/scripts/archive_tw_stock_valuation.py
backend/scripts/validate_tw_stock_daily.py
backend/scripts/update_tw_stock_daily.py
```

用途：

- `sync_tw_stock_symbols.py`：从 TWSE `STOCK_DAY_ALL` 同步上市股票和 ETF 标的，默认 dry-run，`--apply` 写入 `qd_market_symbols`。
- `archive_tw_stock_daily.py`：从 FinMind `TaiwanStockPrice` 拉取日线并解析为 `qd_tw_stock_daily_bars` 记录，默认 dry-run，`--apply` 写入数据库。
- `archive_tw_stock_corporate_actions.py`：从 FinMind `TaiwanStockDividendResult` 拉取除权息结果，写入 `qd_tw_stock_corporate_actions`，并保存 `after_price / before_price` 推导出的复权因子。
- `archive_tw_stock_institutional_trades.py`：从 FinMind `TaiwanStockInstitutionalInvestorsBuySell` 拉取三大法人买卖数据，按 symbol/date 聚合外资、投信、自营商自行、自营商避险和总法人净买超，写入 `qd_tw_stock_institutional_trades`。
- `archive_tw_stock_margin_trading.py`：从 FinMind `TaiwanStockMarginPurchaseShortSale` 拉取融资融券数据，保留来源单位，写入 `qd_tw_stock_margin_trading`。
- `archive_tw_stock_monthly_revenue.py`：从 FinMind `TaiwanStockMonthRevenue` 拉取月营收，计算 MoM/YoY 增速，写入 `qd_tw_stock_monthly_revenue`。
- `archive_tw_stock_valuation.py`：从 FinMind `TaiwanStockPER` 拉取 PE、PB 和股利殖利率，写入 `qd_tw_stock_valuation`。
- `validate_tw_stock_daily.py`：用 TWSE 官方 `STOCK_DAY_ALL` 校验最新日线的收盘价和成交量，默认 dry-run，`--apply` 更新 `official_checked` / `official_match` / `quality_flags`。
- `update_tw_stock_daily.py`：盘后总控脚本，先归档日线，再校验 TWSE 最新日，并归档除权息、三大法人、融资融券、月营收与估值；可用 `--no-corporate-actions`、`--no-institutional`、`--no-margin`、`--no-monthly-revenue`、`--no-valuation` 跳过对应步骤。

手动 dry-run 示例：

```bash
cd /path/to/taiwan-stock-quant-platform
python backend/scripts/update_tw_stock_daily.py   --symbol 2330 --symbol 0050 --start 2026-05-20 --end 2026-05-22 --dry-run
```

写入数据库时必须设置 PostgreSQL `DATABASE_URL`，并显式加 `--apply`：

```bash
cd /path/to/taiwan-stock-quant-platform
DATABASE_URL=<postgres-url> python   backend/scripts/update_tw_stock_daily.py --apply
```

Cron 建议：

```text
10 15 * * 1-5 cd /path/to/taiwan-stock-quant-platform && python backend/scripts/update_tw_stock_daily.py --apply
00 06 * * 6   cd /path/to/taiwan-stock-quant-platform && python backend/scripts/sync_tw_stock_symbols.py --apply
```

时间均为 `Asia/Taipei`。如果 cron 机器不是台北时区，需要在 crontab 或服务环境中设置 `TZ=Asia/Taipei`。

注意：`update_tw_stock_daily.py` 的官方校验会把本次归档窗口内“每个标的最新一笔记录”与 TWSE 官方最新日资料对比。因此日常盘后任务应覆盖最新交易日；如果手动指定较早的 `--end`，而 TWSE 官方资料已经更新到更晚日期，脚本会返回 date mismatch，这属于预期的数据时效性保护。

复权模式：当前 API 默认继续返回未复权价格，避免无声改变既有回测结果。研究长期收益时可显式设置：

```bash
TW_STOCK_CORPORATE_ACTION_MODE=forward_adjusted   # 前复权，历史价格向当前口径调整
TW_STOCK_CORPORATE_ACTION_MODE=backward_adjusted  # 后复权，除权息日及之后价格向历史口径调整
TW_STOCK_CORPORATE_ACTION_MODE=raw_unadjusted     # 默认，未复权
```

当前复权因子来自 FinMind `TaiwanStockDividendResult` 的除权息参考价，计算方式为 `adjustment_factor = after_price / before_price`。长期绩效比较建议使用前复权；交易执行、下单模拟和官方对账仍应使用未复权价格。

### 9.4 Qlib normalized CSV 导出

已新增脚本：

```text
backend/scripts/export_tw_qlib_normalized.py
```

默认读取 `docs/data.txt` 的最低建议清单，并输出到：

```text
/home/chuliyang/qlib/data_tw/normalized/
```

输出列固定为：

```text
symbol,date,open,high,low,close,volume,vwap,factor
```

规则：

- 个股输出 symbol 为 `TW2330` 格式。
- 加权指数输出 symbol 为 `TWII`，但数据源查询代码为 FinMind `TAIEX`。
- 个股 `vwap` 优先使用 `Trading_money / Trading_Volume`。
- `TWII` 是指数，`Trading_money / Trading_Volume` 不是指数点位，因此 `vwap` 使用 OHLC4。
- 当前导出默认使用未复权价格，`factor=1.0`，适合先做 Qlib 流程验证；后续可把 `qd_tw_stock_corporate_actions` 的复权因子接进导出。

示例：

```bash
cd /path/to/taiwan-stock-quant-platform
python backend/scripts/export_tw_qlib_normalized.py \
  --start 2026-05-20 --end 2026-05-22 \
  --output-dir /home/chuliyang/qlib/data_tw/normalized \
  --continue-on-error
```

短窗口真实验证结果：`19` 个标的、`57` 行、无空标的、无失败、无质量 flag。

---

## 10. 阶段路线图

### Phase 1：台股日线研究与回测

- 新增 `TWStockDataSource`。
- 注册 `TWStock` 到 `DataSourceFactory`。
- 支持 `1D` / `1W`。
- 添加热门台股标的。
- 新增单元测试、API smoke test 和实时数据质量测试。
- 用 `2330`、`0050` 完成样例回测。
- HTTP 回测入口已为 `TWStock` 设置 Phase 1 默认成本：`commission=0.002925`、`slippage=0.001`、`tradeDirection=long`。
- 回测结果已暴露台股执行假设：TWD、Asia/Taipei、`lotSize=1000`、`lotSizeEnforced=false`、未复权价格、未建模涨跌停。

### Phase 2：数据归档与质量

- 建立本地 `qd_market_klines` 或台股专用历史表。
- 每日盘后增量更新。
- TWSE/TPEx 官方资料对账。
- 已新增除权息归档表 `qd_tw_stock_corporate_actions`、归档脚本和可选前/后复权计算；默认仍使用未复权价格。
- 已新增三大法人买卖超归档表 `qd_tw_stock_institutional_trades` 和归档脚本，可作为法人筹码因子基础。
- 已新增融资融券归档表 `qd_tw_stock_margin_trading` 和归档脚本，可作为杠杆情绪、券资比、筹码拥挤度因子基础。
- 已新增月营收归档表 `qd_tw_stock_monthly_revenue` 和归档脚本，可作为营收动量、成长因子基础。
- 已新增估值归档表 `qd_tw_stock_valuation` 和归档脚本，可作为价值、高股息筛选因子基础。

### Phase 3：多股票组合策略

### 10.1 Phase 3 Universe 构建器

已新增脚本：

```text
backend/scripts/build_tw_stock_universe.py
```

用途：

- 从 `qd_market_symbols` 或显式 `--symbol` 清单读取台股候选。
- 默认排除 ETF，可用 `--include-etf` 纳入 ETF。
- 拉取近期日线，计算：
  - `bars`
  - `last_trade_date`
  - `last_close`
  - `avg_volume`
  - `avg_trading_money`
- 按流动性过滤并按 `avg_trading_money` 排序。
- 输出兼容现有 cross-sectional 配置的 `symbol_list`，格式为 `TWStock:2330`。

示例：

```bash
cd /path/to/taiwan-stock-quant-platform
python backend/scripts/build_tw_stock_universe.py \
  --symbol 2330,2317,2454,2308,2412 \
  --start 2026-05-20 --end 2026-05-22 \
  --min-bars 3 --min-avg-volume 1 --min-avg-trading-money 1 \
  --max-universe 5 \
  --output-json /tmp/tw_universe_smoke.json
```

真实 smoke 结果：5 个候选全部通过，输出排序为 `2330,2454,2308,2317,2412`，排序依据为平均成交金额。

- 建立 universe：市值、成交额、行业、ETF 分类。
- 支持横截面动量、低波动、高股息、法人筹码因子。
- 加入组合调仓、最大持仓数、单股权重、行业约束。

### 10.2 Phase 3 横截面排名脚本

已新增脚本：

```text
backend/scripts/rank_tw_stock_universe.py
```

用途：

- 读取 `build_tw_stock_universe.py` 输出的 `symbol_list`，或直接传入 `--symbol`。
- 拉取每个标的日线，计算：
  - 动量：`close[-1] / close[-window-1] - 1`
  - 波动率：最近收益率标准差
  - 流动性：平均成交金额
- 用分位分数合成 `composite_score`。默认权重：
  - 动量 `0.5`
  - 低波动 `0.3`
  - 流动性 `0.2`
- 输出 `rankings`，格式为 `TWStock:2454`，可作为后续 cross-sectional 策略输入。

示例：

```bash
python backend/scripts/rank_tw_stock_universe.py \
  --universe-json /tmp/tw_universe_smoke.json \
  --start 2026-04-01 --end 2026-05-22 \
  --momentum-window 20 --volatility-window 20 --min-bars 30 \
  --output-json /tmp/tw_universe_rank_smoke.json
```

真实 smoke 结果：5 个标的全部 eligible，排名为 `2454,2317,2330,2308,2412`。

### 10.3 Phase 3 调仓计划生成器

已新增脚本：

```text
backend/scripts/plan_tw_stock_rebalance.py
```

用途：

- 读取 `rank_tw_stock_universe.py` 的排名 JSON。
- 选择 Top N。
- 生成目标持仓权重，不下单。
- 第一版支持 long-only equal weight，并支持：
  - `--top-n`
  - `--cash-weight`
  - `--max-weight`

示例：

```bash
python backend/scripts/plan_tw_stock_rebalance.py \
  --ranking-json /tmp/tw_universe_rank_smoke.json \
  --top-n 3 --cash-weight 0.1 --max-weight 0.35 \
  --as-of 2026-05-22 \
  --output-json /tmp/tw_rebalance_plan_smoke.json
```

真实 smoke 结果：Top 3 为 `2454,2317,2330`，各 `30%`，保留现金 `10%`。

### 10.4 Phase 3 组合模拟器

已新增脚本：

```text
backend/scripts/simulate_tw_stock_portfolio.py
```

用途：

- 读取显式 `--symbol` 或 universe/ranking JSON。
- 拉取每个标的日线，并在每个调仓日用历史窗口重新排名。
- 复用调仓计划生成器，按 Top N、现金权重、单股最大权重生成持仓。
- 用 close-to-close 日收益推进组合净值。
- 按换手率扣减交易成本。
- 输出 `metrics`、`rebalance_events`、`equity_curve`。

当前假设：

- 研究模拟，不下单。
- long-only。
- 调仓时点按收盘价近似。
- 默认仍可使用权重模型，成本默认为 `0.003925`，可用 `--transaction-cost` 覆盖。
- 可用 `--enforce-lot-size` 启用台股 1000 股整股近似撮合，并用 `--initial-capital`、`--lot-size`、`--commission-rate`、`--sell-tax-rate` 控制资金规模、整股单位、手续费和卖出交易税。
- 整股模式会输出 `shares`、`cash_weight`、`buy_value`、`sell_value`、`buy_commission`、`sell_commission`、`sell_tax`。
- 可用 `--enforce-price-limit` 启用涨跌停保守约束：涨停不增加仓位，跌停不减少仓位；事件中输出 `blocked_buys`、`blocked_sells`。
- 涨跌停判断使用前一交易日收盘价与当前收盘价做近似，尚未接入逐笔委托簿或官方涨跌停价字段。

示例：

```bash
python backend/scripts/simulate_tw_stock_portfolio.py \
  --symbol 2330,2317,2454,2308,2412 \
  --start 2026-04-01 --end 2026-05-22 \
  --rebalance-frequency weekly \
  --lookback-days 45 \
  --momentum-window 10 --volatility-window 10 --min-bars 15 \
  --top-n 3 --cash-weight 0.1 --max-weight 0.35 \
  --transaction-cost 0.003925 \
  --output-json /tmp/tw_portfolio_sim_smoke.json
```

真实 smoke 结果：脚本成功拉取 FinMind 日线并完成周频模拟；区间 `2026-04-01` 至 `2026-05-22`，5 个候选标的，8 次调仓，最终净值 `1.49727736`，最大回撤 `-0.09394929`。这个短区间结果只用于链路验证，不代表策略有效性。

整股撮合 smoke：

```bash
python backend/scripts/simulate_tw_stock_portfolio.py \
  --symbol 2330,2317,2454,2308,2412 \
  --start 2026-04-01 --end 2026-05-22 \
  --rebalance-frequency weekly \
  --lookback-days 45 \
  --momentum-window 10 --volatility-window 10 --min-bars 15 \
  --top-n 3 --cash-weight 0.1 --max-weight 0.35 \
  --enforce-lot-size --initial-capital 5000000 --lot-size 1000 \
  --commission-rate 0.001425 --sell-tax-rate 0.003 \
  --output-json /tmp/tw_portfolio_lot_sim_smoke.json
```

结果：`rebalance_count=8`，`final_equity=0.99895233`，`max_drawdown=-0.01401118`，`average_turnover=0.31265454`。事件中已包含整股 `shares`、手续费和卖出税字段。这个结果同样只用于链路验证。

整股 + 涨跌停约束 smoke：

```bash
python backend/scripts/simulate_tw_stock_portfolio.py \
  --symbol 2330,2317,2454,2308,2412 \
  --start 2026-04-01 --end 2026-05-22 \
  --rebalance-frequency weekly \
  --lookback-days 45 \
  --momentum-window 10 --volatility-window 10 --min-bars 15 \
  --top-n 3 --cash-weight 0.1 --max-weight 0.35 \
  --enforce-lot-size --initial-capital 5000000 --lot-size 1000 \
  --commission-rate 0.001425 --sell-tax-rate 0.003 \
  --enforce-price-limit --price-limit-pct 0.10 \
  --output-json /tmp/tw_portfolio_limit_sim_smoke.json
```

结果：`rebalance_count=8`，`final_equity=0.99895233`，`max_drawdown=-0.01401118`，`average_turnover=0.31265454`。本样本未触发涨跌停阻断，`blocked_buys=[]`、`blocked_sells=[]`；离线测试已覆盖触发阻断的场景。

### Phase 4：纸面盘和实盘

- 扩展 IBKR 台股合约。
- 实现台股 lot size、TWD 现金、限价保护。
- Agent token 默认 paper-only。
- 实盘需要显式开启环境变量和账户白名单。

### 10.5 Phase 4 纸面订单预览器

已新增脚本：

```text
backend/scripts/preview_tw_stock_paper_orders.py
```

用途：

- 读取 `plan_tw_stock_rebalance.py` 的目标权重，或读取组合模拟器单次调仓事件。
- 读取当前持仓 JSON；未传入时视为空仓。
- 生成 paper-only 订单预览，不写数据库，不连接 IBKR，不下单。
- 输出 IBKR 台股合约字段：`secType=STK`、`exchange=TWSE`、`currency=TWD`。
- 强制台股整股单位，默认 `lot_size=1000`。
- 默认生成限价单，限价由参考价和 `--limit-buffer` 计算。
- 支持 `--max-order-value`、`--max-total-buy-value` 风控。
- 当目标权重不足买入一张时输出 `target_below_one_lot:<symbol>` warning。

示例：

```bash
python backend/scripts/preview_tw_stock_paper_orders.py \
  --plan-json /tmp/tw_rebalance_plan_smoke.json \
  --as-of 2026-05-22 \
  --portfolio-value 5000000 \
  --lot-size 1000 \
  --limit-buffer 0.005 \
  --max-order-value 2000000 \
  --max-total-buy-value 5000000 \
  --output-json /tmp/tw_paper_order_preview_smoke.json
```

真实 smoke 结果：生成 `1` 笔 paper-only 限价买入预览：`2317` 买入 `6000` 股，参考价 `250.0`，限价 `251.25`，预估名义金额 `1,500,000 TWD`，合约为 `STK 2317 TWSE TWD`。`2330` 和 `2454` 因目标权重对应金额不足一张而输出 warning。

主线审视：截至 Phase 4 第一步，工作仍沿着“台股数据真实性与归档 -> 多股票研究组合 -> 纸面执行 -> IBKR paper/live”推进，没有偏离到无关市场或高频实盘。当前 Phase 4 的代码仍保持 paper-only，不写订单、不连接 broker。

正式服务层补充：

- `backend/app/services/ibkr_trading/symbols.py` 已支持 `TWStock` 映射。
- `2330`、`2330.TW`、`TWSE:2330` 映射为 `2330 / TWSE / TWD`。
- `TPEX:6488`、`6488.TPEX` 映射为 `6488 / TPEX / TWD`。
- `backend/app/services/broker_market_policy.py` 已把 `ibkr + TWStock + spot + long` 纳入可路由矩阵。
- `preview_tw_stock_paper_orders.py` 已改为复用正式 IBKR symbol service，而不是自行拼合约。

Agent paper-only 接入：

- `backend/app/routes/agent_v1/quick_trade.py` 已支持 `market=TWStock` 的 paper-only 订单。
- 台股 quick-trade 要求 `order_type=limit` 和正数 `limit_price`，避免无保护市价单。
- `qty` 必须是 `lot_size` 的整数倍，默认 `1000`。
- `sell` 优先使用请求中的 `current_qty/currentQty/current_position/currentPosition`；如果请求未提供，则从服务端 `qd_user_positions` 按当前用户、`TWStock`、标准化 symbol 汇总持仓数量。仍然不足或查询失败时按 0 处理并拒绝，避免 paper 流程产生隐含放空。
- 价格获取优先使用台股日线最新收盘价兜底，避免 `1m` 不支持时 paper order 全部无成交。
- 该路径仍受 Agent T scope、paper_only 和 live kill switch 保护；当前不会调用 IBKR 下单。

纸面订单提交桥接：

已新增脚本：

```text
backend/scripts/submit_tw_stock_paper_orders.py
```

用途：

- 读取 `preview_tw_stock_paper_orders.py` 的输出。
- 默认 dry-run，只生成将要提交给 `/api/agent/v1/quick-trade/orders` 的 payload。
- 只选择 `status=preview` 的订单，跳过 blocked 订单。
- 显式传入 `--submit --agent-token <token>` 时才会 POST 到 Agent Gateway。
- 不传 `--submit` 时不会写数据库、不会访问后端、不会连接 broker。

示例 dry-run：

```bash
python backend/scripts/submit_tw_stock_paper_orders.py \
  --preview-json /tmp/tw_paper_order_preview_smoke.json \
  --output-json /tmp/tw_paper_order_submit_dry_run.json
```

真实 dry-run 结果：生成 `1` 个 quick-trade payload：`TWStock 2317 buy 6000 limit 251.25`，保留 warnings `target_below_one_lot:2330`、`target_below_one_lot:2454`，`submit_results=[]`。

一键 paper pipeline：

已新增脚本：

```text
backend/scripts/run_tw_stock_paper_pipeline.py
```

用途：

- 从调仓计划 JSON 直接生成订单预览和 quick-trade payload。
- 默认 dry-run，本地执行，不访问后端、不写数据库、不连接 broker。
- 支持分别输出 pipeline 总报告、preview JSON、submit dry-run JSON。
- 显式 `--submit --agent-token <token>` 时才调用 Agent Gateway。

示例 dry-run：

```bash
python backend/scripts/run_tw_stock_paper_pipeline.py \
  --plan-json /tmp/tw_rebalance_plan_smoke.json \
  --as-of 2026-05-22 \
  --portfolio-value 5000000 \
  --lot-size 1000 \
  --limit-buffer 0.005 \
  --max-order-value 2000000 \
  --max-total-buy-value 5000000 \
  --output-json /tmp/tw_paper_pipeline_smoke.json \
  --preview-output-json /tmp/tw_paper_pipeline_preview_smoke.json \
  --submit-output-json /tmp/tw_paper_pipeline_submit_smoke.json
```

真实 dry-run 结果：`preview.order_count=1`，`submit.submit_candidate_count=1`，生成 `2317 buy 6000 limit 251.25`，未提交到后端，`submit_results=[]`。

服务端持仓兜底校验补充：

- `backend/app/routes/agent_v1/quick_trade.py` 对 `TWStock` 卖单新增服务端持仓 fallback。
- 如果请求没有携带 `current_qty` 等持仓字段，会查询 `qd_user_positions` 中当前用户的 `TWStock` 标准化 symbol 持仓合计。
- 查询失败、表不可用或持仓不足时按 0 处理并拒绝卖出，保持 fail-safe。
- 该补充只影响 paper-only quick-trade 的卖出风控，不会连接 IBKR，也不会触发真实下单。

本步测试：

```bash
python -m pytest backend/tests/test_agent_v1_twstock_quick_trade.py -q
python -m py_compile backend/app/routes/agent_v1/quick_trade.py
```

结果：`8 passed in 1.00s`，语法检查通过。

提交前风控门槛：

- `--fail-on-warning`：存在 warning 时返回退出码 `3`。
- `--fail-on-blocked`：存在 blocked order 时返回退出码 `3`。
- `--max-submit-candidates N`：候选提交订单数超过 `N` 时返回退出码 `3`。
- 这些检查在 `--submit` 之前执行；如果失败，不会调用 Agent Gateway。

真实风控 smoke：同一调仓计划开启 `--fail-on-warning` 后，因为 `2330` 和 `2454` 目标资金不足一张，返回退出码 `3`，`guard_errors=["warnings_present"]`。

---

本地 API loopback 闭环：

已新增测试：

```text
backend/tests/test_tw_stock_paper_api_loopback.py
```

覆盖链路：

1. `submit_tw_stock_paper_orders.submit_payloads()` 构造 HTTP POST。
2. Flask test client 调用真实 `/api/agent/v1/quick-trade/orders` 路由。
3. 测试内 fake DB 捕获写入 `qd_agent_paper_orders` 的 paper order。
4. `verify_tw_stock_paper_orders.fetch_paper_orders()` 构造 HTTP GET。
5. Flask test client 调用真实 `/api/agent/v1/portfolio/paper-orders` 路由查回。
6. `verify_tw_stock_paper_orders.build_report()` 比对 `order_uid`，确认 matched、missing 结果正确。

测试结果：

```bash
python -m pytest backend/tests/test_tw_stock_paper_api_loopback.py -q
```

结果：`1 passed in 0.99s`。

环境说明：当前 shell 未配置 `DATABASE_URL`，且本机没有 `psql` 客户端，因此本轮不能声称已完成真实 PostgreSQL 入库查回。上述 loopback 是 API 级离线闭环验证，覆盖 submit 脚本、Agent quick-trade 路由、paper-orders 查回路由和 verify 脚本的拼接逻辑；真实 DB 闭环需要后续配置 PostgreSQL 后执行。


本地 PostgreSQL 配置补充：

- 已使用项目自带 `docker-compose.yml` 启动本地 PostgreSQL。
- 因本机 `127.0.0.1:5432` 已被 `maas-postgres` 占用，本项目 PostgreSQL 改用 `127.0.0.1:55432`。
- 项目根目录 `.env` 已设置 `DB_PORT=127.0.0.1:55432`。
- `backend/.env` 已设置 `DATABASE_URL=postgresql://user:password@127.0.0.1:5432/quantdinger`。
- `AGENT_LIVE_TRADING_ENABLED=false`，并关闭本地后台 worker，确保下一步真实 DB paper 闭环仍不会连接 broker。
- 当前 `quantdinger-db` 为 healthy，项目 Python 已验证关键 Agent 表存在。

验证：`test_db_bootstrap.py` + `test_agent_v1.py` 为 `15 passed, 2 warnings`。


真实 PostgreSQL paper 闭环补充：

- 已在本地 PostgreSQL 中写入一次性 Agent token：`scopes=R,T`、`markets=TWStock`、`paper_only=true`。
- 已启动本地 Flask API 并执行 `run_tw_stock_paper_pipeline.py --submit`。
- 使用固定价格 `/tmp/tw_db_loopback_prices.json`，`2317=250.0`，避免验证过程依赖外部行情网络。
- 输出文件：
  - `/tmp/tw_paper_pipeline_db_loopback.json`
  - `/tmp/tw_paper_pipeline_db_loopback_preview.json`
  - `/tmp/tw_paper_pipeline_db_loopback_submit.json`
  - `/tmp/tw_paper_order_verify_db_loopback.json`
- 真实提交结果：`TWStock 2317 buy 6000 limit 251.25`，Agent 返回 `paper-fill`，`order_uid=37be98e25f524a62a2b7e745257f7228`。
- `verify_tw_stock_paper_orders.py` 通过 `/api/agent/v1/portfolio/paper-orders` 查回成功：`matched_count=1`，`missing_count=0`。
- 直接查询 `qd_agent_paper_orders` 也确认该订单存在，字段为 `qty=6000`、`limit_price=251.25`、`fill_price=250.0`、`fill_value=1500000.0`、`status=filled`。
- Flask API 已在验证后停止；PostgreSQL 容器继续保持 healthy。

安全状态：`AGENT_LIVE_TRADING_ENABLED=false`，仍然 paper-only；没有连接 IBKR，也没有真实下单。


paper position 汇总补充：

- 新增 `/api/agent/v1/portfolio/paper-positions`。
- 该接口只读，从 `qd_agent_paper_orders` 的 `filled` paper orders 动态推导持仓，不写 `qd_user_positions`，避免污染手工持仓。
- 汇总规则：buy 增加数量和成本并计算加权平均成本；sell 按当前平均成本扣减成本；超卖只输出 warning，不生成负持仓。
- 新增测试 `backend/tests/test_agent_v1_paper_positions.py`。
- 真实 DB smoke 使用上一轮 `2317 buy 6000 @ 250.0` paper order，接口返回 `quantity=6000.0`、`avg_price=250.0`、`cost_value=1500000.0`、`warnings=[]`，输出 `/tmp/tw_paper_positions_db_smoke.json`。

验证：新增测试 `3 passed in 0.91s`；真实 DB smoke HTTP 200。


paper portfolio summary 补充：

- 新增 `/api/agent/v1/portfolio/paper-summary`。
- 该接口只读，从 `qd_agent_paper_orders` 的 `filled` paper orders 动态推导组合摘要，不写数据库。
- 支持 `initial_cash` query 参数，输出 `cash`、`gross_buy_value`、`gross_sell_value`、`realized_pnl`、`open_cost_value`、`equity_at_cost`、持仓列表和 warnings。
- 新增测试覆盖现金影响、成本口径权益、已实现盈亏和非法参数。
- 真实 DB smoke 使用上一轮 `2317 buy 6000 @ 250.0` paper order，`initial_cash=5000000`，返回 `cash=3500000.0`、`open_cost_value=1500000.0`、`equity_at_cost=5000000.0`、`warnings=[]`，输出 `/tmp/tw_paper_summary_db_smoke.json`。

验证：`test_agent_v1_paper_positions.py` 为 `6 passed in 0.90s`；真实 DB smoke HTTP 200。


主线复核与 paper execution report 补充：

- 本轮复核确认：工作仍沿着“台股数据真实性与归档 -> 多股票组合 -> paper-only 执行闭环 -> paper portfolio/报告 -> IBKR paper/live 评估”推进，没有偏离到无关市场、UI 或实盘交易。
- 新增 `backend/scripts/build_tw_stock_paper_execution_report.py`，把 pipeline、verify、paper summary 三类 JSON 汇总成可审计执行报告。
- 该脚本只读本地 JSON，不提交订单、不查询数据库、不连接 broker、不修改状态。
- 新增测试 `backend/tests/test_build_tw_stock_paper_execution_report.py`。
- 使用真实 DB paper 闭环产物生成：
  - `/tmp/tw_paper_execution_report_db_loopback.json`
  - `/tmp/tw_paper_execution_report_db_loopback.md`
- 报告结果：`status=pass`、`submitted_count=1`、`matched_count=1`、`missing_count=0`、`broker_connected=false`、`live_order_submitted=false`。

验证：新增测试 `4 passed in 0.04s`；真实报告生成成功。


pipeline execution report 集成补充：

- `run_tw_stock_paper_pipeline.py` 新增 `--verify-json`、`--portfolio-summary-json`、`--execution-report-json`、`--execution-report-md`。
- 当 verify 和 paper summary 输入同时存在时，一键 pipeline 可直接产出 JSON/Markdown execution report。
- 只提供其中一个输入时返回退出码 `2`，避免生成半成品报告。
- 本集成只读本地 JSON，不自动查 DB、不提交订单、不连接 broker；真实 submit 后仍需先运行 verify 和 paper summary，再生成完整审计报告。
- smoke 输出 `/tmp/tw_paper_pipeline_execution_report_smoke.json` 和 `/tmp/tw_paper_pipeline_execution_report_smoke.md`。

验证：pipeline/report 集成测试 `14 passed in 0.78s`；smoke 成功生成报告。


paper sell 闭环补充：

- 使用真实 DB 中已有的 `2317 buy 6000 @ 250.0` paper 持仓，构造目标权重 `2317=0.2`。
- pipeline 生成并提交 `2317 sell 2000 limit 248.75`，Agent 返回 `paper-fill`，`order_uid=50e69d31373c4c1ab4de87329c541a42`。
- verify 查回成功：`matched_count=1`、`missing_count=0`。
- paper positions 返回 `quantity=4000.0`、`avg_price=250.0`、`cost_value=1000000.0`。
- paper summary 返回 `cash=4000000.0`、`gross_sell_value=500000.0`、`realized_pnl=0.0`、`equity_at_cost=5000000.0`。
- 卖出执行报告输出：`/tmp/tw_paper_execution_report_sell_db_loopback.json` 和 `/tmp/tw_paper_execution_report_sell_db_loopback.md`。
- 已补充 preview 卖出订单生成测试。

注意：该问题已在后续 `sell current_qty 修复` 中处理，submit bridge 现在优先使用 preview 中的真实当前总持仓。


sell current_qty 修复补充：

- `preview_tw_stock_paper_orders.py` 的 order preview 新增 `current_qty` 字段，表示当前总持仓。
- `submit_tw_stock_paper_orders.py` 卖单 payload 优先使用 preview 的 `current_qty/currentQty`，旧 preview 才回退到 `qty`。
- 卖出 dry-run smoke 显示 `2317 sell 2000` 的 payload 已携带 `current_qty=6000`，输出 `/tmp/tw_paper_pipeline_sell_current_qty_fix_submit.json`。
- 局部测试 `16 passed in 0.80s`。



post-submit paper report bundle 补充：

- 新增 `backend/scripts/build_tw_stock_paper_report_bundle.py`，把真实 submit 后的订单查回、paper summary 查询和 execution report 生成合并成一个 post-submit 报告打包步骤。
- 输入为 `run_tw_stock_paper_pipeline.py` 或 submit bridge 产出的 pipeline/submit JSON，以及本地 Agent token；脚本只调用只读接口 `/api/agent/v1/portfolio/paper-orders` 和 `/api/agent/v1/portfolio/paper-summary`。
- 输出可同时包含 bundle JSON、verify JSON、summary JSON、execution report JSON 和 Markdown。
- 该脚本不提交订单、不写数据库、不连接 IBKR、不触发真实下单。
- 新增测试 `backend/tests/test_build_tw_stock_paper_report_bundle.py`，覆盖 summary API 调用、bundle 状态合成、summary 失败降级和 CLI 落盘。
- 真实本地 API 只读 smoke 使用已有 DB paper 订单生成：
  - `/tmp/tw_paper_report_bundle_buy_db_smoke.json`
  - `/tmp/tw_paper_report_bundle_buy_verify_smoke.json`
  - `/tmp/tw_paper_report_bundle_buy_summary_smoke.json`
  - `/tmp/tw_paper_report_bundle_buy_execution_smoke.json`
  - `/tmp/tw_paper_report_bundle_buy_execution_smoke.md`
- 主 smoke 结果：`status=pass`、`matched_count=1`、`missing_count=0`、`fetch_status_code=200`、paper summary 返回 `cash=4000000.0`、`position_count=1`、`equity_at_cost=5000000.0`。
- 兼容 smoke 也使用历史 sell pipeline 产物生成成功：`/tmp/tw_paper_report_bundle_sell_db_smoke.json` 等文件。

验证：`test_build_tw_stock_paper_report_bundle.py` + `test_verify_tw_stock_paper_orders.py` + `test_build_tw_stock_paper_execution_report.py` 为 `14 passed in 0.10s`；真实本地 API 只读 smoke 通过；临时 Flask API 已停止。

安全状态：仍然 paper-only；没有连接 IBKR，也没有真实下单。


multi-stock/ETF paper smoke 与限价修复补充：

- 本轮目标是验证 Phase 4 真实多标的 paper 链路，标的包含股票 `2330` 与 ETF `0050`、`00878`。
- 先创建隔离本地测试用户和 paper-only Agent token，避免报告混入旧 `2317` paper 状态。
- 初始 dry-run 使用固定价格 `2330=1000`、`0050=200`、`00878=25` 生成 3 笔订单；真实 submit 暴露问题：quick-trade paper fill 使用最新日线成交，但未检查买入限价是否可成交，导致 `2330` 以 `fill_price=2255.0` 高于 `limit_price=1005.0` 被记录为 filled。
- 已修复 `backend/app/routes/agent_v1/quick_trade.py`：TWStock paper limit order 现在执行限价成交约束，买入要求 `last_price <= limit_price`，卖出要求 `last_price >= limit_price`；不满足时记录为 `rejected`，并写入原因，不再伪造成交。
- 新增测试覆盖买入价高于限价、卖出价低于限价的拒绝场景。
- 随后用 `TWStockDataSource` 获取真实最新日线收盘价，输出 `/tmp/tw_multi_etf_latest_prices.json`：`2330=2255.0`、`0050=97.3`、`00878=28.27`。
- 使用 `portfolio_value=5000000` 时，`2330` 因整股 1000 股约束触发 `target_below_one_lot:2330`；这是预期的整张规则结果。
- 最终使用 `portfolio_value=10000000`，生成股票 + ETF 共 3 笔整股 paper 订单：
  - `0050 buy 30000 limit 97.79`，paper fill `97.3`。
  - `00878 buy 70000 limit 28.41`，paper fill `28.27`。
  - `2330 buy 1000 limit 2266.27`，paper fill `2255.0`。
- 最终 bundle 报告输出：
  - `/tmp/tw_multi_etf_clean_10m_pipeline_submit.json`
  - `/tmp/tw_multi_etf_clean_10m_preview_submit.json`
  - `/tmp/tw_multi_etf_clean_10m_submit.json`
  - `/tmp/tw_multi_etf_clean_10m_report_bundle.json`
  - `/tmp/tw_multi_etf_clean_10m_verify.json`
  - `/tmp/tw_multi_etf_clean_10m_summary.json`
  - `/tmp/tw_multi_etf_clean_10m_execution_report.json`
  - `/tmp/tw_multi_etf_clean_10m_execution_report.md`
  - `/tmp/tw_multi_etf_clean_10m_db_check.json`
- 最终结果：`status=pass`、`submitted_count=3`、`failed_submit_count=0`、`matched_count=3`、`missing_count=0`、`position_count=3`、`gross_buy_value=7152900.0`、`cash=2847100.0`、`equity_at_cost=10000000.0`。
- 直接 DB 核对 `limit_violations=[]`，三笔 filled buy 的 `fill_price` 均低于对应 `limit_price`。

验证：Phase 4 paper 相关测试 `56 passed in 1.37s`。真实本地 API smoke 成功；临时 Flask API 已停止。

安全状态：仍然 `AGENT_LIVE_TRADING_ENABLED=false`；全部为 Agent paper orders；没有连接 IBKR，也没有真实下单。修复前的异常隔离用户样本只作为问题发现记录，不作为最终通过依据。


multi-stock/ETF 后续调仓 smoke 补充：

- 本轮基于上一轮干净隔离用户的 `2330`、`0050`、`00878` paper 持仓，验证后续 rebalance 中的卖出、加仓和持仓汇总。
- 从 `/tmp/tw_multi_etf_clean_10m_summary.json` 生成当前持仓输入 `/tmp/tw_multi_etf_rebalance_positions.json`。
- 新调仓计划 `/tmp/tw_multi_etf_rebalance_plan.json`：`2330=50%`、`0050=10%`、`00878=20%`、现金约 `20%`。
- dry-run 输出 `/tmp/tw_multi_etf_rebalance_pipeline_dry_run.json`，结果为两笔订单：
  - `0050 sell 20000 limit 96.81`，preview `current_qty=30000`，用于 long-only 卖出校验。
  - `2330 buy 1000 limit 2266.27`。
  - `00878` 目标与当前整股数量一致，不产生订单。
- 真实 paper submit 输出：
  - `/tmp/tw_multi_etf_rebalance_pipeline_submit.json`
  - `/tmp/tw_multi_etf_rebalance_preview_submit.json`
  - `/tmp/tw_multi_etf_rebalance_submit.json`
- post-submit bundle 输出：
  - `/tmp/tw_multi_etf_rebalance_report_bundle.json`
  - `/tmp/tw_multi_etf_rebalance_verify.json`
  - `/tmp/tw_multi_etf_rebalance_summary.json`
  - `/tmp/tw_multi_etf_rebalance_execution_report.json`
  - `/tmp/tw_multi_etf_rebalance_execution_report.md`
  - `/tmp/tw_multi_etf_rebalance_db_check.json`
- 真实结果：`submitted_count=2`、`failed_submit_count=0`、`matched_count=2`、`missing_count=0`。
- paper summary 累计 5 笔 filled paper orders 后：`cash=2538100.0`、`gross_buy_value=9407900.0`、`gross_sell_value=1946000.0`、`open_cost_value=7461900.0`、`equity_at_cost=10000000.0`。
- 最终持仓：`0050=10000`、`00878=70000`、`2330=2000`。
- DB 直接核对：`limit_violations=[]`，卖出 `0050` 的 `fill_price=97.3 >= limit_price=96.81`，买入 `2330` 的 `fill_price=2255.0 <= limit_price=2266.27`。

验证：Phase 4 paper 相关测试 `56 passed in 1.34s`。真实本地 API smoke 成功；临时 Flask API 已停止。

安全状态：仍然 `AGENT_LIVE_TRADING_ENABLED=false`；全部为 paper-only；没有连接 IBKR，也没有真实下单。


不可成交限价 rejected smoke 与报告状态补充：

- 本轮验证 TWStock paper limit order 在不可成交时不会进入持仓，并修复 execution report 对 rejected paper orders 的状态表达。
- `build_tw_stock_paper_execution_report.py` 新增 rejected submit result 检测：如果 submit HTTP 成功但 paper order `status=rejected`，execution report 和 bundle 状态为 `warning`，原因 `rejected_paper_orders`，不再误报为 `pass`。
- 新增测试覆盖 rejected submit result 报告状态。
- 创建隔离 paper-only 用户/token，构造 `/tmp/tw_rejected_limit_plan.json` 和 `/tmp/tw_rejected_limit_prices.json`：`2330` 参考价 `1000.0`，生成 `2330 buy 2000 limit 1005.0`。
- 真实 quick-trade 使用最新日线 `last_price=2255.0`，因此订单被记录为 `rejected`：`paper limit not marketable: last_price 2255.0 > buy limit 1005.0`。
- 输出文件：
  - `/tmp/tw_rejected_limit_pipeline_dry_run.json`
  - `/tmp/tw_rejected_limit_pipeline_submit.json`
  - `/tmp/tw_rejected_limit_preview_submit.json`
  - `/tmp/tw_rejected_limit_submit.json`
  - `/tmp/tw_rejected_limit_report_bundle.json`
  - `/tmp/tw_rejected_limit_verify.json`
  - `/tmp/tw_rejected_limit_summary.json`
  - `/tmp/tw_rejected_limit_execution_report.json`
  - `/tmp/tw_rejected_limit_execution_report.md`
  - `/tmp/tw_rejected_limit_db_check.json`
- 最终结果：bundle `status=warning`、`status_reasons=["rejected_paper_orders"]`、`matched_count=1`、`missing_count=0`、`rejected_submit_count=1`。
- paper summary 和 DB 直接核对均确认：`filled_order_count=0`、`position_count=0`、`cash=5000000.0`、`equity_at_cost=5000000.0`，rejected order 不进入持仓。

验证：Phase 4 paper 相关测试 `57 passed in 1.38s`。真实本地 API smoke 成功；临时 Flask API 已停止。

安全状态：仍然 `AGENT_LIVE_TRADING_ENABLED=false`；全部为 paper-only；没有连接 IBKR，也没有真实下单。


IBKR paper/live preflight 清单补充：

- 新增只读脚本 `backend/scripts/preflight_tw_stock_ibkr_live.py`，用于检查 Phase 4 进入 IBKR paper/live 前的本地安全条件。
- 该脚本默认不连接 IBKR TWS/Gateway，不查询账户，不提交订单，只检查本地配置、Agent token、broker policy 和 TWStock 合约映射。
- 检查项包括：
  - `IBKR + TWStock + spot + long` 是否被 `broker_market_policy.py` 接受。
  - `ALLOW_LOCAL_DESKTOP_BROKERS` 是否允许本地桌面 broker。
  - `AGENT_LIVE_TRADING_ENABLED` 在 paper preflight 中是否保持 `false`。
  - `IBKR_ORDER_CLIENT_ID` 是否避免使用 `1`，默认建议 `7`，避免和手工 UI session 冲突。
  - Agent token 是否 active、具备 `R,T` scope、允许 `TWStock`、paper preflight 中保持 `paper_only=true`。
  - `2330`、`0050`、`TPEX:6488` 是否能映射到 IBKR 合约字段 `symbol/exchange/currency`，例如 `2330/TWSE/TWD`、`6488/TPEX/TWD`。
- live promotion 红线写入报告：不能在 error 检查失败时启用 live；不能在无人工审批时使用 `paper_only=false` token；策略/order worker 不使用 clientId=1；TPEx 官方数据未完成对账前不建议实盘交易 TPEX 标的。
- 新增测试 `backend/tests/test_preflight_tw_stock_ibkr_live.py`，覆盖 paper preflight pass、paper 模式误开 live switch 的 warning、live 模式 token 仍 paper-only 的 fail、live kill switch 缺失 fail、非法台股 symbol fail 和 Markdown 输出。
- 真实只读 smoke：
  - 输入：`--symbol 2330,0050,TPEX:6488`，使用本地 paper-only Agent token。
  - 环境：`AGENT_LIVE_TRADING_ENABLED=false`、`ALLOW_LOCAL_DESKTOP_BROKERS=true`、`IBKR_ORDER_CLIENT_ID=7`。
  - 输出：`/tmp/tw_ibkr_preflight_paper_smoke.json` 和 `/tmp/tw_ibkr_preflight_paper_smoke.md`。
  - 结果：`status=pass`、`error_count=0`、`warning_count=0`、`connects_to_ibkr=false`、`submits_orders=false`。

验证：Phase 4/IBKR preflight 相关测试 `87 passed in 1.22s`。本步没有启动 Flask API，没有连接 IBKR，也没有真实下单。

安全状态：仍未进入 live；本步只是启用前置检查和操作清单。


IBKR live preflight fail-case smoke 补充：

- 本轮使用 `preflight_tw_stock_ibkr_live.py --require-live --require-ibkr-env` 做只读 fail-case 验证，证明缺少 live 条件时会阻止 live promotion。
- 命令仍然不连接 IBKR、不查询账户、不提交订单；预期退出码为 `1`，表示安全检查失败。
- 输入 symbol：`2330`、`0050`、`TPEX:6488`；使用本地 paper-only Agent token。
- 环境保持 `AGENT_LIVE_TRADING_ENABLED=false`、`ALLOW_LOCAL_DESKTOP_BROKERS=true`、`IBKR_ORDER_CLIENT_ID=7`，且不提供 `IBKR_HOST/IBKR_PORT`。
- 输出：
  - `/tmp/tw_ibkr_preflight_live_fail_smoke.json`
  - `/tmp/tw_ibkr_preflight_live_fail_smoke.md`
- 结果：`status=fail`、`error_count=4`、`warning_count=0`、`connects_to_ibkr=false`、`submits_orders=false`。
- 4 个阻断项：
  - `agent_live_kill_switch`：live promotion 要求 `AGENT_LIVE_TRADING_ENABLED=true`，当前为 `false`。
  - `ibkr_env_host`：未配置 IBKR host。
  - `ibkr_env_port`：未配置 IBKR port。
  - `agent_token:paper_only_mode`：当前 token 仍为 `paper_only=true`，live promotion 需要人工审批后的 `paper_only=false`。
- 已通过项仍包括 broker policy、strategy config、`ALLOW_LOCAL_DESKTOP_BROKERS=true`、`IBKR_ORDER_CLIENT_ID=7`、token `R,T` scope、`TWStock` market allowlist、TWSE/TPEX 合约映射。

验证：preflight/policy/symbol 测试 `68 passed in 1.16s`。本步没有启动 Flask API，没有连接 IBKR，也没有真实下单。

安全状态：live promotion 被正确拦截；这证明当前环境仍无法也不应进入 live。


IBKR 台股 paper/live 操作手册补充：

- 新增正式中文手册 `docs/IBKR_TWSTOCK_TRADING_GUIDE_CN.md`。
- 手册明确：它不是实盘授权；默认路径仍是 paper-only；任何 live promotion 都必须人工审批。
- 覆盖内容：当前支持状态、禁止条件、环境变量、TWS / IB Gateway 设置、paper/live preflight、paper 账户验证流程、live promotion 审批清单、最小 live 试单、回滚与禁用、当前未完成项和常用命令。
- 关键安全规则：
  - 任一 preflight error 不得启用 live。
  - 未经审批不得设置 `AGENT_LIVE_TRADING_ENABLED=true`。
  - 未经审批不得使用 `paper_only=false` token。
  - 策略/order worker 不使用 `clientId=1`。
  - TPEx 标的在官方数据未完成对账前不建议 live。
- 文档明确当前未完成项：本环境尚未连接真实 IBKR TWS / Gateway；尚未通过 IBKR paper account 做真实 broker paper order；Agent quick-trade 当前仍是本地 paper order，不是 IBKR broker order。

验证：手册关键章节检查通过，文档共 224 行。没有启动 Flask API，没有连接 IBKR，也没有真实下单。



## 10. Phase 5A：按需台股趋势查询与部署效果

根据当前需求，Phase 5 的近期目标从“自动监控并买卖”调整为“按需查询 + 自动监控提醒 + 人工决策”。因此部署后的直接效果应是一个研究和提醒服务：输入台股或 ETF 代码，系统返回趋势方向、趋势分数、收益、均线、成交量、波动率和数据质量；也可以定时刷新观察列表、发现趋势变化并提醒用户。但系统不自动下单，也不把结果解释为交易指令，买卖决策仍由用户人工判断。

后端接口：

- `GET /api/tw-stock/trend?symbol=2330&limit=120`
- `GET /api/tw-stock/trends?symbols=2330,0050,00878&limit=120`

当前返回字段覆盖：

- `latest`：最新日线日期、收盘价、成交量。
- `trend`：趋势标签、0-100 分数、中文摘要。
- `returns`：5/20/60 日收益率。
- `moving_averages`：MA5/MA20/MA60 与站上均线状态。
- `volume`：最新量、20/60 日均量、量比。
- `risk`：20 日年化波动率。
- `quality`：样本数、latest_date、stale_days、warnings、来源。
- `trading`：固定 `orders_enabled=false`、`signal=none`，用于明确这不是下单接口。

数据时效说明：该接口沿用 `KlineService:TWStock:1D`，底层数据来自已接入的台股日线数据源。它适合日频趋势研究，不是盘中实时流。2026-05-24 本地 smoke 中，`2330`、`0050`、`00878` 返回的最新交易日为 `2026-05-21`，`stale_days=3`，无质量告警。

部署后的用户体验建议：

- 后端先提供只读 API，供脚本、前端、定时监控任务或后续 Agent 查询。
- 前端 Phase 5B 应做成一个台股趋势与监控面板，而不是下单面板。
- 面板核心控件：代码输入、观察列表、趋势分数排序、最新日期/数据质量提示、收益/均线/量能/风险区块、监控开关、刷新频率和提醒规则。
- 买卖按钮、自动下单、实盘 broker 连接暂不放在主界面；自动监控可以放在主界面，但输出应是提醒和解释，不是买卖决策。

本轮验证：`test_tw_stock_trend_api.py`、`test_tw_stock_kline_api.py`、`test_tw_stock_data_source.py` 合计 `29 passed in 0.92s`；真实本地 API smoke 通过；没有连接 IBKR，没有提交 paper order，没有真实下单。




## 10.1 Phase 5B：趋势与监控面板

当前仓库没有独立前端工程，因此先用 Flask 托管一个轻量页面：`GET /api/tw-stock/monitor`。该页面直接调用 `GET /api/tw-stock/trends`，实现台股趋势可视化和浏览器端自动监控。

面板定位：

- 面向研究和提醒，不是下单终端。
- 可以自动刷新观察列表并提示趋势标签、趋势分数或数据质量变化。
- 买卖决策仍由用户人工完成。
- 不显示买卖按钮，不连接 broker，不提交 paper/live order。

已实现控件：观察列表、日线数量、刷新频率、分数变化提醒阈值、手动刷新、启动/停止监控。

已实现展示：趋势标签、趋势分数、最新日期/收盘价、5/20/60 日收益、MA20/MA60、量比、年化波动率、数据质量状态。

本轮验证：页面 HTTP smoke 返回 `200 OK`；真实趋势 API 返回 `2330`、`0050`、`00878` 三个标的；Playwright 截图成功；相关测试 `30 passed in 0.95s`。

Phase 5C 建议：把观察列表、提醒规则和提醒历史从浏览器内存推进到后端持久化，并增加“人工确认/标记已读/备注”流程。




## 10.2 Phase 5C：监控配置与提醒历史持久化

Phase 5C 将趋势监控从浏览器内存推进到本地 PostgreSQL。系统现在可以保存台股观察列表、日线数量、刷新频率、分数变化阈值、启用状态和提醒历史，并支持用户对提醒做已读确认和人工备注。

新增表：

- `qd_tw_stock_monitor_configs`：保存每个用户/监控名称的观察列表和监控参数。
- `qd_tw_stock_monitor_alerts`：保存趋势标签变化、趋势分数变化、数据质量提示等提醒历史。

新增 API：`/api/tw-stock/monitor/config` 和 `/api/tw-stock/monitor/alerts`。这些 API 只保存研究提醒状态，不生成订单，不连接 broker，不参与自动交易。

页面变化：`/api/tw-stock/monitor` 会优先读取后端配置；配置变化时保存后端；监控发现变化时写入提醒历史；最近提醒可在页面上标记已读并附带人工判断状态。

本轮验证：Phase 5C 相关测试 `43 passed in 0.92s`；真实 PostgreSQL smoke 完成配置保存、配置读取、提醒创建、提醒查询和已读确认；Playwright 截图成功 `/tmp/tw_stock_monitor_phase5c.png`。

后续建议：Phase 5D 增加后端定时监控 worker 或手动扫描 API，使提醒生成不依赖浏览器页面保持打开。




## 10.3 Phase 5D：后端扫描与趋势状态比较

Phase 5D 增加后端扫描能力：系统可以读取保存的台股监控配置，主动拉取趋势报告，与上次扫描状态比较，并把趋势变化、分数变化或新增数据质量提示写入提醒历史。这样提醒生成不再必须依赖浏览器页面一直打开。

新增表：`qd_tw_stock_monitor_states`，用于保存每个用户、监控名称和 symbol 的上次趋势标签、分数、最新日期、质量提示和完整快照。

新增 API：

- `POST /api/tw-stock/monitor/scan`
- `POST /api/tw-stock/monitor/scan-all`

扫描只产生研究提醒，不产生交易指令。返回结果包含 `trading.orders_enabled=false`。页面新增“后端扫描”按钮，用于人工触发服务器端扫描。

本轮验证：相关测试 `45 passed in 0.94s`；真实 PostgreSQL smoke 对 `phase5d-smoke` 配置扫描 `2330`、`0050`、`00878`，两次扫描均成功，真实数据未发生变化所以 `alert_count=0`；Playwright 截图成功 `/tmp/tw_stock_monitor_phase5d.png`。

后续建议：Phase 5E 将 `scan-all` 接入可选后台 worker 或部署级 cron，并增加扫描日志、失败重试和数据源异常可视化。




## 10.4 Phase 5E：可选后台 worker 与扫描日志

Phase 5E 增加可部署的自动监控基础设施。系统现在可以通过 `ENABLE_TW_STOCK_MONITOR_WORKER=true` 启动后台 worker，定时执行 `scan-all`，扫描已启用的台股监控配置，并把每次运行写入 `qd_tw_stock_monitor_scan_logs`。

关键环境变量：

- `ENABLE_TW_STOCK_MONITOR_WORKER`：默认 `false`，设为 `true` 后启动 worker。
- `TW_STOCK_MONITOR_INTERVAL_SEC`：扫描间隔，默认 `900` 秒。
- `TW_STOCK_MONITOR_FORCE_SCAN`：默认 `false`，只扫描 enabled 配置。

新增查询 API：`GET /api/tw-stock/monitor/scan-logs?limit=20`，用于查看最近扫描是否成功、扫描了多少配置/标的、产生多少提醒、耗时多久以及错误信息。

本轮真实 smoke：默认 worker 关闭时启动日志明确提示 disabled；手动 `scan-all` 扫描本地 3 个启用配置、共 8 个 symbol，`alert_count=0`，并成功写入 scan log。返回和日志均保持 `orders_enabled=false`。

后续建议：Phase 5F 整理部署和运维手册，把 PostgreSQL、API、worker、趋势面板、扫描日志、关闭流程和 smoke 数据清理流程串起来。




## 10.5 Phase 5F：部署与运维手册

Phase 5F 新增独立中文手册：`docs/TW_STOCK_MONITOR_DEPLOYMENT_CN.md`。该手册把台股趋势监控从开发断点整理为可执行的部署/运维流程。

覆盖内容：

- 当前能力边界：研究与提醒，不自动交易。
- 本地 PostgreSQL/API 启动方式。
- 趋势面板访问方式。
- 监控配置 API、提醒 API、后端扫描 API 和扫描日志 API。
- 可选后台 worker 环境变量：`ENABLE_TW_STOCK_MONITOR_WORKER`、`TW_STOCK_MONITOR_INTERVAL_SEC`、`TW_STOCK_MONITOR_FORCE_SCAN`。
- 数据质量字段和常见 warnings。
- 故障排查、关闭 worker、清理 smoke 数据、部署后自检清单。

手册入口已加入 `docs/README_CN.md` 文档导航。




## 10.6 Phase 5G：端到端 worker 演练

Phase 5G 按部署手册完成了一次真实端到端演练：新建 `phase5g-e2e` 监控配置，手动执行 `scan-all`，查询扫描日志，再启用 `ENABLE_TW_STOCK_MONITOR_WORKER=true` 让后台 worker 自动扫描。

演练结果：

- 手动 scan-all：`count=4`、`total_scanned_count=10`、`total_alert_count=0`、`orders_enabled=false`。
- API 扫描日志：`trigger_source=api`、`status=success`、`monitor_count=4`、`scanned_count=10`、`alert_count=0`。
- worker 启动日志：`TWStock monitor worker started: interval=30s force=False`。
- worker 扫描日志：`trigger_source=worker`、`status=success`、`monitor_count=4`、`scanned_count=10`、`alert_count=0`。
- 回归测试：`48 passed in 0.97s`。

由于真实数据相对上次扫描没有变化，`alert_count=0` 属于预期结果。整个演练没有连接 broker，没有提交订单。




## 10.7 Phase 5H：最终验收清单与剩余技术债

Phase 5H 新增独立验收文档：`docs/TW_STOCK_PHASE5_ACCEPTANCE_CN.md`。

该文档确认 Phase 5 可视为“研究版台股趋势监控”完成，覆盖：

- Phase 5A-5G 已完成能力。
- 最近测试和真实 worker 演练结果。
- 上线前检查清单。
- 数据质量验收。
- 安全验收。
- 剩余技术债。
- 后续优先级建议。

核心结论：当前系统可以按需查询台股趋势、自动监控观察列表、保存提醒、运行后台 worker 和查看扫描日志；但它不是实时行情系统、自动交易系统、实盘下单系统，也不是已验证可盈利策略。


## 11. 外部资料

- TWSE OpenAPI Swagger：`https://openapi.twse.com.tw/`
- TWSE OpenAPI OAS：`https://openapi.twse.com.tw/v1/swagger.json`
- TPEx OpenAPI Swagger：`https://www.tpex.org.tw/openapi/`
- FinMind 快速开始：`https://finmind.github.io/quickstart/`
- FinMind API Swagger：`https://api.finmindtrade.com/docs`
- TAIFEX 官网：`https://www.taifex.com.tw/enl/eIndex`
- IBKR TWS API：`https://interactivebrokers.github.io/tws-api/`
- IBKR 台股 Paper / Live 操作手册：`docs/IBKR_TWSTOCK_TRADING_GUIDE_CN.md`
- 台股趋势监控部署与运维手册：`docs/TW_STOCK_MONITOR_DEPLOYMENT_CN.md`
- Phase 5 台股趋势监控验收清单：`docs/TW_STOCK_PHASE5_ACCEPTANCE_CN.md`

