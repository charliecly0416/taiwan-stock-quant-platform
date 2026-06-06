# 台股 QuantDinger 15 分钟盘中观察设计方案

## 1. 背景与目标

当前台股功能已经形成两条主线：

- `qlib Option C`：以日线数据生成 Top30/Top50 研究排名，适合做选股、复盘和跨日研究。
- `QuantDinger 台股分析`：读取本地日线 K 线和技术趋势，辅助交叉分析、模拟账户和前端展示。

用户反馈“以一天为单位粒度可能太粗”，且原模板里存在 15 分钟间隔选项。这个诉求合理，但不能把 15 分钟数据直接混入 qlib 日线排名，否则会造成模型含义混乱。

本方案目标是：

1. 保持 qlib 相关功能继续使用日线，不改变 Top30/Top50 排名含义。
2. 新增 QuantDinger 单独的 15 分钟盘中观察能力，用于执行观察、风险提示和模拟账户辅助。
3. 前端表达必须简单、清晰、准确，不让用户误以为 15 分钟信号是自动交易建议。
4. 所有新增能力默认 research-only，不连接券商，不下真实订单。

## 2. 核心产品原则

### 2.1 日线负责“选哪些股票”

以下功能继续使用日线：

- qlib Top30/Top50 排名。
- qlib 分数与 accepted latest。
- qlib + QuantDinger 交叉分析。
- 今日/昨日排名变化。
- 模拟账户核心买入候选、卖出候选、保留观察、人工复核。

这些页面和接口不应该被 15 分钟数据改写。

### 2.2 15 分钟负责“今天怎么看”

15 分钟数据用于盘中执行观察，不用于替代日线研究结论。适合展示：

- 今日盘中是否放量。
- 是否跌破/站回短周期均线。
- 是否和日线趋势一致。
- 持仓是否出现盘中风险。
- 候选股是否适合等待回踩、分批模拟买入或人工复核。

### 2.3 不做伪实时交易系统

本阶段不做：

- 真实下单。
- 快速交易按钮。
- 自动卖出/自动买入。
- 目标仓位、目标权重。
- 承诺收益率、胜率、上涨概率。
- 把 15 分钟信号写成“建议马上买/卖”。

## 3. 推荐信息架构

### 3.1 台股研究页

新增一个独立模块：`盘中观察`。

建议位置：

- 放在 Top30/Top50 排名和交叉分析之后。
- 不放在页面最顶部，避免抢占“日线研究排名”的主线。
- K 线图区域可以增加时间周期切换：`日线 / 60分钟 / 15分钟`。

展示内容：

- 标的选择：支持 Top30、Top50、持仓、自选搜索。
- 当前周期：默认日线，用户手动切到 15 分钟。
- 盘中状态：强势延续、回踩观察、转弱预警、数据不足。
- 与日线关系：一致、短线偏弱、短线偏强、矛盾需复核。

### 3.2 模拟账户页

在候选面板旁新增：`盘中执行观察`。

不要改变核心候选列表的排序逻辑，只补充执行层提示：

- 买入候选：
  - 日线入选 + 15m 放量上行：可进入模拟观察。
  - 日线入选 + 15m 快速拉高：提示避免追高，等待回踩。
  - 日线入选 + 15m 转弱：转人工复核。

- 卖出候选：
  - 日线转弱 + 15m 跌破均线：风险提高。
  - 日线仍强 + 15m 回调：先保留观察。

按钮仍只能生成模拟草稿，不出现真实交易动作。

### 3.3 AI资产分析页

AI资产分析页当前已收敛为台股专用。后续可增加一个小型状态块：

- 当前标的。
- 日线研究结论。
- 15m 盘中状态。
- 是否与日线一致。

避免放入加密货币、美股、全球热力图等无关内容。

## 4. 数据设计

### 4.1 数据分层

建议新增独立 15m 数据表，不复用日线归档表。

表名建议：`qd_tw_stock_intraday_bars`

字段建议：

```sql
symbol TEXT NOT NULL,
exchange TEXT DEFAULT '',
timeframe TEXT NOT NULL, -- 15m, 60m
bar_start TIMESTAMPTZ NOT NULL,
bar_end TIMESTAMPTZ,
open NUMERIC,
high NUMERIC,
low NUMERIC,
close NUMERIC,
volume BIGINT,
trading_money NUMERIC,
source TEXT NOT NULL,
quality_flags TEXT DEFAULT '',
raw_json JSONB,
updated_at TIMESTAMPTZ DEFAULT NOW(),
PRIMARY KEY (symbol, timeframe, bar_start, source)
```

索引：

```sql
CREATE INDEX idx_tw_intraday_symbol_tf_time
ON qd_tw_stock_intraday_bars(symbol, timeframe, bar_start DESC);
```

### 4.2 数据来源

候选来源按优先级：

1. 已有 QuantDinger 数据源能力，如果本地已有 15m K 线接口，优先复用。
2. FinMind 若当前方案可取得台股分钟级或 tick 级数据，再聚合为 15m。
3. Yahoo/Scrapling 若只能稳定提供日线，则不用于 15m。

实现前必须先做只读探测：

- 是否能拿到台股 15m 或更细数据。
- 是否有延迟。
- 是否需要付费 token。
- 是否能覆盖 Top30/Top50/持仓。
- 是否会遇到 API 频率限制。

### 4.3 数据保留周期

建议：

- 15m 原始数据保留 90 个自然日。
- 60m 聚合数据可由 15m 计算，也可保留 180 日。
- 不进入 qlib provider，不参与 accepted latest。

## 5. 后端设计

### 5.1 DataSource

新增或扩展：

- `TWStockIntradayDataSource`
- 或在 `TWStockDataSource.get_kline(symbol, timeframe, limit)` 中支持 `15m`、`60m`

推荐先独立实现 intraday adapter，降低对现有日线链路的影响。

### 5.2 Service

新增服务：`TWStockIntradaySignalService`

输入：

```text
symbol
asof_date
timeframe=15m
lookback_bars=80
```

输出字段建议：

```json
{
  "symbol": "2357",
  "timeframe": "15m",
  "latest_bar_time": "2026-06-05T13:15:00+08:00",
  "status": "intraday_pullback_watch",
  "trend_label": "short_term_strong",
  "volume_state": "above_recent_average",
  "ma_state": "above_ma20",
  "day_vs_intraday_alignment": "aligned",
  "confidence": 62,
  "warnings": []
}
```

状态枚举建议：

- `intraday_strong_continue`：短线强势延续。
- `intraday_pullback_watch`：回踩观察。
- `intraday_weak_warning`：短线转弱预警。
- `intraday_divergence_review`：与日线矛盾，人工复核。
- `intraday_data_insufficient`：样本不足。
- `intraday_market_closed`：非交易时间，仅展示最近数据。

### 5.3 API

新增只读 API：

```text
GET /api/tw-stock/intraday/kline?symbol=2357&timeframe=15m&limit=120
GET /api/tw-stock/intraday/signals?symbols=2357,2330&timeframe=15m
GET /api/tw-stock/intraday/overview?bucket=top30&timeframe=15m
```

禁止新增：

- POST 下单。
- quick-trade。
- broker。
- target position。
- target weight。

### 5.4 自动更新脚本

新增独立脚本，不混入日线 accepted latest：

```text
scripts/run_tw_stock_intraday_update.py
```

调度建议：

- 交易日 09:15-13:45：每 15 分钟尝试。
- 13:45-14:30：补最后一段数据。
- 非交易时间不拉盘中数据。
- 失败后记录状态，不阻塞日线自动更新。

Ops 状态目录：

```text
data_tw/ops/intraday_update/<job_id>/job.json
```

## 6. 前端设计

### 6.1 K 线周期切换

在台股研究页 K 线模块增加：

```text
日线 | 60分钟 | 15分钟
```

默认：`日线`。

只有用户切到 15 分钟时才请求 intraday API，避免打开页面就触发大量请求。

### 6.2 盘中观察卡片

卡片字段：

- 标的：`2357 华硕`
- 最新 15m 时间：`13:15`
- 15m 状态：`回踩观察`
- 与日线：`一致 / 矛盾 / 需复核`
- 量能：`高于近 20 根均量`
- 风险：`跌破 15m MA20`

文案示例：

```text
日线仍在研究池内，15分钟出现回踩但未破关键均线。适合继续观察，不构成交易建议。
```

不要写：

```text
立即买入
立即卖出
上涨概率 80%
必涨
```

### 6.3 模拟账户集成

在候选项里增加一行小字：

```text
盘中观察：15m 强势延续 / 回踩观察 / 转弱预警 / 暂无数据
```

排序仍以日线候选逻辑为主，15m 只影响提示和人工复核标记。

## 7. 风险与边界

主要风险：

- 分钟级数据源不稳定。
- 盘中数据延迟导致用户误判。
- 日线结论和 15m 结论矛盾。
- 页面信息过多，破坏“简单清晰”的原则。

对应控制：

- 明确标注“盘中观察”。
- 不改变 qlib 日线排名。
- 默认不展示 15m，用户主动切换。
- 所有盘中结论只用于模拟和人工复核。
- 数据不足时显示“暂无足够 15m 数据”，不强行给结论。

## 8. 分阶段实现计划

### Phase 1：数据可行性探测

目标：确认 15m 数据是否能稳定取得。

工作：

- 调研当前可用数据源。
- 做只读拉取脚本。
- 对 10 个标的测试 15m 覆盖率。
- 产出数据可用性报告。

验收：

- 至少覆盖 Top30 中 90% 标的。
- 单标的最近 3 个交易日至少有足够 15m bar。
- 不影响日线自动更新。

### Phase 2：后端 intraday 表和 API

目标：建立独立数据链路。

工作：

- 新增 intraday 表。
- 新增导入/更新脚本。
- 新增 kline/signals/overview API。
- 加单元测试和只读安全检查。

验收：

- `/intraday/kline` 可返回 15m K 线。
- `/intraday/signals` 可返回状态枚举。
- 不出现 broker/order/quick-trade 相关动作。

### Phase 3：前端 K 线周期切换

目标：先让用户能看 15m K 线。

工作：

- K 线模块增加周期切换。
- 15m 请求走独立 API。
- 数据不足有明确空态。

验收：

- 日线默认不变。
- 切到 15m 后展示盘中 K 线。
- 页面不混淆 qlib 日期和 15m 时间。

### Phase 4：盘中观察模块

目标：提供简单清晰的 15m 状态。

工作：

- 新增盘中观察卡片。
- 接入 intraday signals。
- 与日线状态做一致性提示。

验收：

- 用户能理解“日线选股、15m 观察”。
- 不出现交易指令式文案。
- 移动端不拥挤。

### Phase 5：模拟账户辅助

目标：把 15m 用到模拟执行观察。

工作：

- 买入/卖出候选项增加盘中状态。
- 矛盾项进入人工复核。
- 模拟草稿保留来源上下文。

验收：

- 候选列表不因 15m 频繁变化而大幅跳动。
- 核心候选排序仍来自日线。
- 15m 只做提示，不做真实交易动作。

## 9. 最终推荐

建议做，但要命名和边界清楚：

- 不叫“15分钟 qlib 更新”。
- 不叫“15分钟买卖建议”。
- 应叫“QuantDinger 15分钟盘中观察”。

产品主线应保持：

```text
日线 qlib：决定看哪些股票
QuantDinger 15m：辅助今天怎么观察
模拟账户：验证研究思路，不做真实交易
```
