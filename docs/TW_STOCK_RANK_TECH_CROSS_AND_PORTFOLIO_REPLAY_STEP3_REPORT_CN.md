# 台股排名技术交叉与组合回放 Step 3 执行报告

生成时间：2026-06-06

## 1. Step 2 审查修正说明

Step 2 的轻量技术状态主线保留：MA/RSI/MACD/Bollinger 仍只输出 `supportive`、`neutral`、`caution`、`data_insufficient`，不输出交易动作。

本步按用户第一性原则收敛为“历史观察队列是否更清晰”：只比较不同规则下的观察分类数量与 symbol 队列，不展示收益、回撤、胜率、换手或资金曲线，避免让用户误以为这是交易建议。

## 2. 修改文件清单

新增：

```text
backend/app/services/tw_stock_observation_replay.py
backend/tests/test_tw_stock_observation_replay.py
backend/tests/test_tw_stock_observation_replay_api.py
docs/TW_STOCK_RANK_TECH_CROSS_AND_PORTFOLIO_REPLAY_STEP3_REPORT_CN.md
```

修改：

```text
backend/app/services/tw_stock_technical_status.py
backend/app/services/tw_stock_rank_tech_cross.py
backend/app/services/tw_stock_trend.py
backend/app/routes/tw_stock.py
backend/tests/test_tw_stock_rank_tech_cross.py
```

未修改：

```text
frontend/*
backend/app/services/backtest.py
backend/app/services/tw_stock_sim_account.py
```

## 3. Point-in-Time 截断

技术状态：

```text
TWStockTechnicalStatusService.analyze_symbol(..., as_of=YYYY-MM-DD)
```

会先读取日线，再过滤：

```text
bar_date <= as_of
```

随后只使用过滤后的末尾 `limit` 根日线计算 MA/RSI/MACD/Bollinger。

趋势状态：

```text
TWStockTrendService.analyze_symbol(..., as_of=YYYY-MM-DD)
```

同样过滤：

```text
bar_date <= as_of
```

测试覆盖了 `as_of=2026-06-01` 时不会使用 `2026-06-02` 的 K 线。

## 4. 三种 Observation Variant

`qlib_only`：

```text
top10 -> 新增观察
top30 -> 继续观察
top50 -> 仅观察
```

不使用趋势和技术指标。

`qlib_plus_trend`：

```text
qlib ranking + point-in-time QuantDinger trend
```

技术 basis 为：

```text
quantdinger_trend_only
```

`qlib_plus_trend_indicators`：

```text
qlib ranking + point-in-time trend + point-in-time MA/RSI/MACD/Bollinger
```

技术 basis 为：

```text
quantdinger_trend_plus_daily_indicators
```

## 5. API 响应示例

```json
{
  "ok": true,
  "status": "accepted",
  "simulation_only": true,
  "research_signal_not_order": true,
  "replay_type": "observation_only",
  "performance_metrics_included": false,
  "range": {
    "startDate": "2026-06-01",
    "endDate": "2026-06-05",
    "runCount": 3
  },
  "comparison": {
    "qlib_only": {"new_watch_count": 30, "manual_review_count": 0, "data_insufficient_count": 0, "item_count": 90},
    "qlib_plus_trend": {"new_watch_count": 18, "manual_review_count": 7, "data_insufficient_count": 5, "item_count": 90},
    "qlib_plus_trend_indicators": {"new_watch_count": 12, "manual_review_count": 10, "data_insufficient_count": 8, "item_count": 90}
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
    "trend_point_in_time": true,
    "technical_point_in_time": true,
    "warnings": []
  },
  "trading": {
    "orders_enabled": false,
    "connects_to_broker": false,
    "quick_trade_enabled": false,
    "writes_orders": false,
    "writes_positions": false
  }
}
```

新增 API：

```text
GET /api/tw-stock/rank-tech-cross/observation-replay
```

## 6. 未包含的 Performance Metrics

本步明确不返回：

```text
totalReturn
annualReturn
maxDrawdown
winRate
turnover
feeAndTax
equityCurve
trades
holdings
target weight
target position
```

## 7. 测试命令与结果

```text
python -m py_compile backend/app/services/tw_stock_observation_replay.py backend/app/services/tw_stock_technical_status.py backend/app/services/tw_stock_rank_tech_cross.py backend/app/services/tw_stock_trend.py backend/app/routes/tw_stock.py
结果：通过
```

```text
python -m pytest backend/tests/test_tw_stock_observation_replay.py backend/tests/test_tw_stock_observation_replay_api.py backend/tests/test_tw_stock_technical_status.py backend/tests/test_tw_stock_rank_tech_cross.py backend/tests/test_tw_stock_rank_tech_cross_api.py -q
结果：21 passed in 2.53s
```

```text
python backend/scripts/verify_tw_stock_research_stack.py
结果：通过；内部 pytest 86 passed in 1.85s
备注：普通沙箱执行遇到 bwrap loopback 环境错误，已按规则提权重跑，脚本返回 ok=true。
```

## 8. 安全边界确认

本步只读读取：

```text
historical accepted qlib run artifacts
TWStock daily bars
```

确认未新增：

```text
portfolio replay 资金 API
BacktestService.run()
收益 / 回撤 / 胜率 / 换手
资金曲线
交易列表
持仓列表
模拟账户写入
模拟订单写入
模拟成交写入
模拟持仓写入
monitor config save
monitor scan
alerts 写入
qlib refresh / publish / accepted latest switching
daily auto update
broker / quick-trade / 真实 order
target position / target weight
```

文案保持观察语义：

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

## 9. 残余风险

- 当前 observation replay 只看观察队列分类变化，不说明投资收益，也不验证能否赚钱。
- `qlib_plus_trend_indicators` 的历史结果依赖本地日线覆盖度；历史样本不足时会增加 `data_insufficient`。
- 本步没有前端展示，用户暂时需要通过 API 或后续 UI 看到对照结果。

## 10. Step 4 建议

Step 4 可以在本步只读观察对照通过后，设计“不落库”的组合规则历史回放：仍不写模拟账户、不连接券商，只用同一套 point-in-time 分类契约生成低换手规则的历史模拟摘要。
