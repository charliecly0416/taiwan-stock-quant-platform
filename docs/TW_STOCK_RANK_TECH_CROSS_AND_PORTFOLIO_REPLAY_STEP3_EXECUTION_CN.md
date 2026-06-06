# 台股排名技术交叉与组合回放 Step 3 执行文档：点时点只读观察队列对照

生成时间：2026-06-06

前置报告：`docs/TW_STOCK_RANK_TECH_CROSS_AND_PORTFOLIO_REPLAY_STEP2_REPORT_CN.md`

## 1. Step 2 审查结论

Step 2 主线基本正确：

- 新增的是轻量日线技术状态。
- 没有调用 `BacktestService.run()`。
- 没有生成资金曲线、交易列表、组合收益、胜率或换手率。
- 没有前端页面改动。
- `rank-tech-cross/latest` 仍是只读 GET。

需要在后续补强的点：

- 当前技术状态只看最新日线。如果要做历史对照，必须避免用“今天的趋势/指标”解释过去的 qlib run。
- Step 3 应先建立 point-in-time 能力：对某个历史 `asof`，只使用该日期及以前的日线数据。
- 暂不进入 portfolio replay，不计算收益，不模拟成交，不写模拟账户。

## 2. 本步目标

实现一个只读历史观察队列对照，用来比较不同研究规则在历史 accepted qlib run 上产生的“观察队列变化”。

本步回答：

- 过去若只看 qlib ranking，会产生哪些观察队列？
- 加入 QuantDinger trend 后，哪些项目会变成继续观察、人工复核或数据不足？
- 加入 MA/RSI/MACD/Bollinger 后，观察队列是否更集中、更少分歧？
- 每个历史日期的分类数量如何变化？

本步不回答：

- 收益是多少。
- 最大回撤是多少。
- 胜率是多少。
- 换手率是多少。
- 应该买入或卖出什么。

## 3. 明确禁止

本步不得执行：

- 不新增 portfolio replay 资金 API。
- 不计算 totalReturn、annualReturn、maxDrawdown、winRate、turnover、feeAndTax。
- 不生成 equityCurve。
- 不生成 trades。
- 不生成 holdings。
- 不写 `qd_tw_sim_accounts`、`qd_tw_sim_orders`、`qd_tw_sim_trades`、`qd_tw_sim_positions`。
- 不保存 monitor config。
- 不触发 monitor scan。
- 不写 alerts。
- 不调用 broker、quick-trade、真实 order、target position、target weight。
- 不触发 qlib refresh、publish、provider mutation、accepted latest switching。
- 不运行 daily auto update。
- 不输出“买入/卖出/下单/目标仓位/上涨概率/收益承诺”作为行动建议。

允许：

- 读取 historical accepted qlib run artifacts。
- 读取本地日线 K 线。
- 读取或计算 point-in-time trend / technical status。
- 产出 observation-only comparison。
- 新增只读 service、只读 GET API、测试和文档。

## 4. Point-in-Time 前置要求

### 4.1 日线数据截断

必须保证历史日期 `asof=YYYY-MM-DD` 的趋势和技术状态只使用：

```text
trade_date <= asof
```

实现方式可以二选一：

1. 扩展 `TWStockTechnicalStatusService.analyze_symbol(..., as_of=...)`，内部从 `KlineService.get_kline(..., before_time=...)` 取数。
2. 新增内部 helper 直接查询 `qd_tw_stock_daily_bars`，限定 `trade_date <= asof`。

推荐优先使用现有 Kline/DataSource 口径，但测试必须证明不会读取 `asof` 之后的 bar。

### 4.2 趋势服务

如果 `TWStockTrendService` 暂时不能做 point-in-time 截断，不要在历史对照中标称为严格历史趋势。

可选处理：

- Step 3A：先扩展 `TWStockTrendService` 支持 point-in-time bars。
- 或 Step 3 中只对技术状态做 point-in-time，并把 trend 对照标记为 `trend_point_in_time_unavailable`。

推荐本步实现 `as_of` 支持，避免对照结果产生未来函数。

## 5. 建议新增 Service

建议新增：

```text
backend/app/services/tw_stock_observation_replay.py
```

职责：

- 读取一段时间内的 accepted qlib runs。
- 对每个 run 的 top30/top50 生成三套只读观察队列：
  - `qlib_only`
  - `qlib_plus_trend`
  - `qlib_plus_trend_indicators`
- 只输出分类数量、队列 symbol、分类原因和数据质量。
- 不计算价格收益。
- 不模拟交易动作。

建议 public method：

```python
class TWStockObservationReplayService:
    def compare(
        self,
        *,
        start_date: str,
        end_date: str,
        bucket: str = "top30",
        max_items: int = 30,
        technical_strategies: list[str] | None = None,
    ) -> dict:
        ...
```

## 6. 对照模式定义

### 6.1 qlib_only

只按 rank tier 生成观察队列：

```text
top10 -> new_watch
top30 -> continue_watch
top50 -> observe_only
```

不使用趋势，不使用指标。

### 6.2 qlib_plus_trend

使用 Step 1 的趋势映射：

```text
ranking + point-in-time QuantDinger trend -> decision
```

`technical.basis=quantdinger_trend_only`

### 6.3 qlib_plus_trend_indicators

使用 Step 2 的轻量指标：

```text
ranking + point-in-time trend + point-in-time indicators -> decision
```

`technical.basis=quantdinger_trend_plus_daily_indicators`

## 7. API 设计

新增只读 GET API：

```text
GET /api/tw-stock/rank-tech-cross/observation-replay
```

参数：

```text
startDate=2025-12-01
endDate=2026-06-01
bucket=top30
maxItems=30
technicalStrategies=ma,rsi,macd,bollinger
```

响应示例：

```json
{
  "ok": true,
  "status": "accepted",
  "simulation_only": true,
  "research_signal_not_order": true,
  "replay_type": "observation_only",
  "performance_metrics_included": false,
  "trading": {
    "orders_enabled": false,
    "connects_to_broker": false,
    "quick_trade_enabled": false,
    "writes_orders": false,
    "writes_positions": false
  },
  "range": {
    "startDate": "2025-12-01",
    "endDate": "2026-06-01",
    "runCount": 12
  },
  "comparison": {
    "qlib_only": {
      "new_watch_count": 30,
      "manual_review_count": 0,
      "data_insufficient_count": 0
    },
    "qlib_plus_trend": {
      "new_watch_count": 18,
      "manual_review_count": 7,
      "data_insufficient_count": 5
    },
    "qlib_plus_trend_indicators": {
      "new_watch_count": 12,
      "manual_review_count": 10,
      "data_insufficient_count": 8
    }
  },
  "daily": [
    {
      "asof": "2026-06-01",
      "run_id": "option_c_daily_signal_...",
      "variants": {
        "qlib_only": {"summary": {}},
        "qlib_plus_trend": {"summary": {}},
        "qlib_plus_trend_indicators": {"summary": {}}
      }
    }
  ],
  "dataQuality": {
    "point_in_time": true,
    "warnings": []
  }
}
```

## 8. 文件建议

建议新增：

```text
backend/app/services/tw_stock_observation_replay.py
backend/tests/test_tw_stock_observation_replay.py
backend/tests/test_tw_stock_observation_replay_api.py
```

建议修改：

```text
backend/app/services/tw_stock_technical_status.py
backend/app/services/tw_stock_rank_tech_cross.py
backend/app/services/tw_stock_trend.py
backend/app/routes/tw_stock.py
```

本步不修改：

```text
frontend/*
backend/app/services/backtest.py
backend/app/services/tw_stock_sim_account.py
```

## 9. 测试要求

### 9.1 Point-in-Time 测试

必须覆盖：

- 技术状态 `as_of=2026-06-01` 不读取 `2026-06-02` 之后的 bars。
- 趋势状态 `as_of=2026-06-01` 不读取未来 bars，若实现趋势 point-in-time。
- 如果历史日线不足，输出 `data_insufficient`，不强行分类为支持或谨慎。

### 9.2 Observation Replay 测试

必须覆盖：

- 只读读取多个 accepted qlib runs。
- `qlib_only`、`qlib_plus_trend`、`qlib_plus_trend_indicators` 三个 variant 都存在。
- 每日 summary 和总 comparison summary 可解释。
- 不返回 `totalReturn`、`maxDrawdown`、`winRate`、`turnover`、`equityCurve`、`trades`。
- 没有 portfolio holdings 或 target weights。

### 9.3 API 安全测试

必须覆盖：

- API 是 GET。
- `simulation_only=true`。
- `research_signal_not_order=true`。
- `performance_metrics_included=false`。
- `trading.orders_enabled=false`。
- `trading.connects_to_broker=false`。
- `trading.quick_trade_enabled=false`。
- `trading.writes_orders=false`。
- `trading.writes_positions=false`。
- route slice 不含 `POST`、`BacktestService`、`sim/orders`、`portfolio-replay`、`monitor scan`、`alerts`、`publish`、`refresh`。

### 9.4 文案安全测试

新增或扩展静态断言，禁止观察 replay 输出或文案包含：

```text
立即买入
立即卖出
自动买入
自动卖出
下单
提交订单
目标仓位
上涨概率
收益承诺
target weight
target position
order instruction
```

允许：

```text
观察队列
新增观察
继续观察
风险复盘
人工复核
数据不足
只读
历史观察
```

## 10. 必跑命令

```text
python -m py_compile backend/app/services/tw_stock_observation_replay.py backend/app/services/tw_stock_technical_status.py backend/app/services/tw_stock_rank_tech_cross.py backend/app/services/tw_stock_trend.py backend/app/routes/tw_stock.py
python -m pytest backend/tests/test_tw_stock_observation_replay.py backend/tests/test_tw_stock_observation_replay_api.py backend/tests/test_tw_stock_technical_status.py backend/tests/test_tw_stock_rank_tech_cross.py backend/tests/test_tw_stock_rank_tech_cross_api.py -q
python backend/scripts/verify_tw_stock_research_stack.py
```

如果本步触及前端，停止并先提交单独前端 Step 文档。

## 11. 验收标准

本步通过必须满足：

- 历史观察对照使用 point-in-time 日线数据。
- 输出三种 variant：`qlib_only`、`qlib_plus_trend`、`qlib_plus_trend_indicators`。
- 只输出观察队列和分类数量。
- 不输出收益、回撤、胜率、换手、资金曲线、交易列表。
- 不写任何业务表。
- 不触发 broker、quick-trade、order、monitor、alerts、qlib ops。
- 测试和 `verify_tw_stock_research_stack.py` 通过。

## 12. 报告要求

执行完成后新增：

```text
docs/TW_STOCK_RANK_TECH_CROSS_AND_PORTFOLIO_REPLAY_STEP3_REPORT_CN.md
```

报告必须包含：

1. Step 2 审查修正说明。
2. 修改文件清单。
3. point-in-time 截断实现说明。
4. 三种 observation variant 的定义。
5. API 响应示例。
6. 明确列出未包含的 performance metrics。
7. 测试命令与结果。
8. 安全边界确认。
9. 残余风险。
10. Step 4 建议：在只读观察对照通过后，再设计不落库的组合规则历史回放。

## 13. 审核断点

本步完成后停止，等待审查：

```text
docs/TW_STOCK_RANK_TECH_CROSS_AND_PORTFOLIO_REPLAY_STEP3_REPORT_CN.md
```

审查通过后，再编写 Step 4 执行文档。
