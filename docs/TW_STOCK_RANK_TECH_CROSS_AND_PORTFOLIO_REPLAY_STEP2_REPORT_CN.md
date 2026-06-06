# 台股排名技术交叉与组合回放 Step 2 执行报告

生成时间：2026-06-06

## 1. Step 1 审查修正说明

Step 1 的 `rank-tech-cross/latest` 主线保持只读 GET 契约。本次继续沿用该 API，没有新增 portfolio replay、资金曲线或前端页面。

当前 `backend/app/routes/tw_stock.py` 的 diff 中包含模拟账户 POST、rank changes 等既有/其它功能线改动；这些不是 Step 2 新增范围。本步只在该文件中补充：

```text
_parse_technical_strategies()
/rank-tech-cross/latest 对 includeTechnicalStrategies 与 technicalStrategies 的解析和透传
```

## 2. 修改文件清单

新增：

```text
backend/app/services/tw_stock_technical_status.py
backend/tests/test_tw_stock_technical_status.py
docs/TW_STOCK_RANK_TECH_CROSS_AND_PORTFOLIO_REPLAY_STEP2_REPORT_CN.md
```

修改：

```text
backend/app/services/tw_stock_rank_tech_cross.py
backend/app/routes/tw_stock.py
backend/tests/test_tw_stock_rank_tech_cross.py
backend/tests/test_tw_stock_rank_tech_cross_api.py
```

未修改：

```text
frontend/*
backend/app/services/backtest.py
backend/app/services/tw_stock_sim_account.py
```

## 3. 技术状态规则

MA：

```text
close > MA5 > MA20 -> supportive
close < MA5 < MA20 -> caution
样本少于 20 根日线 -> data_insufficient
其它 -> neutral
```

RSI：

```text
40 <= RSI14 <= 65 -> supportive
RSI14 > 75 或 RSI14 < 25 -> caution
样本少于 15 根日线 -> data_insufficient
其它 -> neutral
```

MACD：

```text
DIF > DEA 且 histogram >= 0 -> supportive
DIF < DEA 且 histogram < 0 -> caution
样本少于 35 根日线 -> data_insufficient
其它 -> neutral
```

Bollinger：

```text
middle <= close <= upper -> supportive
close < lower 或 close > upper * 1.01 -> caution
样本少于 20 根日线 -> data_insufficient
其它 -> neutral
```

## 4. 汇总规则

轻量指标汇总：

```text
data_insufficient_count >= 3 -> technical_data_insufficient
caution_count >= 2 -> technical_weak
supportive_count >= 2 且 caution_count == 0 -> technical_strong
其它 -> technical_neutral
```

与 QuantDinger trend 合并：

```text
trend strong + indicators weak -> technical_neutral
trend weak + indicators strong -> technical_neutral
trend data insufficient -> 由指标状态决定，并保留 warnings
indicator data insufficient -> 暂以 trend 状态为主
```

## 5. API 响应示例

```json
{
  "ok": true,
  "status": "accepted",
  "simulation_only": true,
  "research_signal_not_order": true,
  "includeTechnicalStrategies": true,
  "technicalStrategies": ["ma", "rsi", "macd", "bollinger"],
  "items": [
    {
      "symbol": "2330",
      "rankTier": "top10",
      "technical": {
        "status": "technical_strong",
        "basis": "quantdinger_trend_plus_daily_indicators",
        "summary": {
          "supportive_count": 3,
          "neutral_count": 1,
          "caution_count": 0,
          "data_insufficient_count": 0
        },
        "strategies": [
          {
            "id": "ma",
            "label": "MA",
            "state": "supportive",
            "metrics": {"close": 125.0, "ma5": 123.4, "ma20": 120.1},
            "reason": "收盘价位于短中期均线上方，技术状态偏支持。"
          }
        ],
        "warnings": [],
        "reason": "趋势和轻量指标状态一致偏支持。"
      },
      "decision": {
        "code": "new_watch",
        "label": "新增观察",
        "priority": "high"
      }
    }
  ],
  "trading": {
    "orders_enabled": false,
    "connects_to_broker": false,
    "quick_trade_enabled": false,
    "writes_orders": false,
    "writes_positions": false
  }
}
```

## 6. 测试命令与结果

```text
python -m py_compile backend/app/services/tw_stock_technical_status.py backend/app/services/tw_stock_rank_tech_cross.py backend/app/routes/tw_stock.py
结果：通过
```

```text
python -m pytest backend/tests/test_tw_stock_technical_status.py backend/tests/test_tw_stock_rank_tech_cross.py backend/tests/test_tw_stock_rank_tech_cross_api.py -q
结果：16 passed in 2.46s
```

```text
python backend/scripts/verify_tw_stock_research_stack.py
结果：通过；内部 pytest 86 passed in 1.83s
备注：普通沙箱执行遇到 bwrap loopback 环境错误，已按规则提权重跑，脚本返回 ok=true。
```

## 7. 安全边界确认

本步新增的技术状态 service 只读取 `KlineService("TWStock", symbol, "1D")` 并做轻量指标计算。

确认未新增：

```text
portfolio replay API
BacktestService.run()
资金曲线
交易列表
组合收益 / 胜率 / 换手率
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

新增文案只表达：

```text
支持
中性
谨慎
观察
复盘
人工复核
数据不足
```

未输出真实交易行动、目标仓位、上涨概率或收益承诺。

## 8. 明确未做事项

本步未做：

```text
portfolio replay
backtest engine
组合资金曲线
交易列表
模拟账户写入
前端页面改动
```

## 9. 残余风险

- 指标状态是轻量规则，不等价于完整历史策略表现。
- RSI 在单边上涨或下跌时可能进入 `caution`，这符合“偏热/偏冷需谨慎”的规则，但 UI 后续需要解释清楚，避免用户误解为交易指令。
- 当前策略状态只看最近一根日线，后续 Step 3 若做对照实验，应验证这些状态是否真的降低无效换手或提升复盘质量。

## 10. Step 3 建议

Step 3 建议做只读对照实验设计：比较 `qlib only`、`qlib + trend`、`qlib + trend + indicators` 的历史观察队列变化，不接前端交易动作，不生成真实交易建议，不写模拟账户。
