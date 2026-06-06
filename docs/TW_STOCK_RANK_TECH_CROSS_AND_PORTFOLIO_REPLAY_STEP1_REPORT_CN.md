# 台股排名技术交叉与组合回放 Step 1 执行报告

生成时间：2026-06-06

## 1. 执行结论

已完成 Step 1：新增后端只读 `排名 × 趋势 × 技术状态` 分类契约，并提供 GET API：

```text
GET /api/tw-stock/rank-tech-cross/latest?bucket=top30&limit=120&maxItems=30
```

本步未实现组合回放、资金曲线、前端页面或模拟账户写入。

## 2. 修改文件清单

新增：

```text
backend/app/services/tw_stock_rank_tech_cross.py
backend/tests/test_tw_stock_rank_tech_cross.py
backend/tests/test_tw_stock_rank_tech_cross_api.py
docs/TW_STOCK_RANK_TECH_CROSS_AND_PORTFOLIO_REPLAY_STEP1_REPORT_CN.md
```

修改：

```text
backend/app/routes/tw_stock.py
```

## 3. 分类契约

排名层级：

```text
rank <= 10  -> top10
rank <= 30  -> top30
rank <= 50  -> top50
rank > 50   -> outside_top50
```

技术状态第一版只使用 QuantDinger daily trend：

```text
uptrend/rebound      -> technical_strong
sideways/unknown     -> technical_neutral
downtrend/pullback   -> technical_weak
unavailable/stale/short/serious warning -> technical_data_insufficient
```

决策矩阵：

```text
top10/top30 + technical_strong  -> new_watch / 新增观察
top10/top30 + technical_neutral -> continue_watch / 继续观察
top10/top30 + technical_weak    -> manual_review / 人工复核
top50       + any available tech -> observe_only / 仅观察
outside_top50 + technical_weak   -> risk_review / 风险复盘
outside_top50 + technical_strong -> manual_review / 人工复核
any + technical_data_insufficient -> data_insufficient / 数据不足
```

## 4. API 响应示例

```json
{
  "ok": true,
  "status": "accepted",
  "simulation_only": true,
  "research_signal_not_order": true,
  "bucket": "top30",
  "limit": 120,
  "maxItems": 30,
  "items": [
    {
      "symbol": "2330",
      "rank": 1,
      "rankTier": "top10",
      "trend": {"label": "uptrend", "score": 72.4},
      "technical": {
        "status": "technical_strong",
        "basis": "quantdinger_trend_only",
        "strategies": [],
        "warnings": []
      },
      "decision": {
        "code": "new_watch",
        "label": "新增观察",
        "priority": "high",
        "reason": "qlib top10 且 QuantDinger 趋势偏强，进入优先复盘队列。"
      }
    }
  ],
  "summary": {
    "new_watch": 1,
    "continue_watch": 0,
    "risk_review": 0,
    "manual_review": 0,
    "observe_only": 0,
    "data_insufficient": 0
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

## 5. 测试命令与结果

```text
python -m py_compile backend/app/services/tw_stock_rank_tech_cross.py backend/app/routes/tw_stock.py
结果：通过
```

```text
python -m pytest backend/tests/test_tw_stock_rank_tech_cross.py backend/tests/test_tw_stock_rank_tech_cross_api.py -q
结果：8 passed in 1.25s
```

```text
python backend/scripts/verify_tw_stock_research_stack.py
结果：通过；内部 pytest 86 passed in 1.89s
备注：普通沙箱执行遇到 bwrap loopback 环境错误，已按规则提权重跑，脚本返回 ok=true。
```

## 6. 安全边界确认

本步新增 API 为 GET：

```text
/api/tw-stock/rank-tech-cross/latest
```

确认未新增：

```text
broker
quick-trade
真实 order submission
target position / target weight
qd_tw_sim_orders 写入
qd_tw_sim_trades 写入
qd_tw_sim_positions 写入
monitor config save
monitor scan
alerts 写入
qlib provider refresh/publish
accepted latest switching
daily auto update
```

新增文案只表达研究队列：

```text
新增观察
继续观察
风险复盘
人工复核
仅观察
数据不足
```

未输出行动建议、目标仓位、上涨概率或收益承诺。

## 7. 残余风险

- Step 1 的技术状态仍是 `quantdinger_trend_only`，尚未接入 MA/RSI/MACD/Bollinger 的独立技术策略结果。
- `outside_top50` 当前作为契约能力存在；由于本步没有持仓输入，不会从 latest top list 主动生成大量 Top50 外项目。
- qlib 与 QuantDinger 数据源口径仍可能有日期差或复权差，后续 UI 需要继续清晰展示数据来源与日期。

## 8. Step 2 建议

Step 2 建议接入 MA/RSI/MACD/Bollinger 技术状态，让 `technical.status` 从单一趋势映射升级为多指标摘要；仍保持只读，不做组合 replay、资金曲线或模拟账户写入。
