# 台股排名技术交叉与组合回放 Step 4 执行报告

生成时间：2026-06-06

## 1. Step 3 审查修正说明

Step 3 的 observation-only 对照继续保留只读边界。本步补强了 `TWStockObservationReplayService` 对异常历史 run 的可解释性：

```text
run_detail(ok=false) -> dataQuality.warnings 包含 run_detail_blocked
empty signals -> dataQuality.warnings 包含 empty_run_signals
```

当前 `backend/app/routes/tw_stock.py` 的 diff 仍包含模拟账户等其它功能线改动；这些不是 Step 4 新增范围。本步新增范围是 portfolio replay service、portfolio replay POST API 和对应测试。

## 2. 修改文件清单

新增：

```text
backend/app/services/tw_stock_portfolio_replay.py
backend/tests/test_tw_stock_portfolio_replay.py
backend/tests/test_tw_stock_portfolio_replay_api.py
docs/TW_STOCK_RANK_TECH_CROSS_AND_PORTFOLIO_REPLAY_STEP4_REPORT_CN.md
```

修改：

```text
backend/app/services/tw_stock_observation_replay.py
backend/app/routes/tw_stock.py
backend/tests/test_tw_stock_observation_replay_api.py
backend/tests/test_tw_stock_rank_tech_cross_api.py
```

未修改：

```text
frontend/*
backend/app/services/tw_stock_sim_account.py
backend/app/services/backtest.py
```

## 3. 不落库保证

新增 service 只在内存中计算：

```text
cash
historical simulated quantity
equityCurve
historicalActions
metrics
```

响应强制：

```json
{
  "persist": false,
  "writes_business_db": false,
  "simulation_only": true
}
```

即使请求传入 `persist=true`，也会被归一化为 `persist=false`。

## 4. 历史模拟规则

默认参数：

```text
initialCash=1000000
feeRate=0.001425
sellTaxRate=0.003
lotSize=10
maxHoldings=10
maxAddPerDay=1
maxRiskActionPerDay=1
```

动作语义只使用历史模拟词：

```text
historical_add
historical_risk_reduce
historical_hold
historical_skip
```

规则：

```text
new_watch -> 有现金、有名额、未持有时，产生 historical_add
risk_review -> 已在历史模拟持有时，产生 historical_risk_reduce
manual_review -> historical_skip
data_insufficient -> historical_skip
continue_watch / observe_only -> historical_hold 或 historical_skip
```

## 5. Metrics 对照示例

```json
{
  "comparison": {
    "qlib_only": {
      "metrics": {
        "totalReturn": 0.012,
        "maxDrawdown": -0.021,
        "actionCount": 8,
        "addActionCount": 5,
        "riskActionCount": 3,
        "feeAndTax": 1234.5,
        "finalEquity": 1012000.0
      }
    },
    "qlib_plus_trend": {
      "metrics": {
        "totalReturn": 0.008,
        "maxDrawdown": -0.015,
        "actionCount": 5
      }
    },
    "qlib_plus_trend_indicators": {
      "metrics": {
        "totalReturn": 0.006,
        "maxDrawdown": -0.012,
        "actionCount": 4
      }
    }
  }
}
```

## 6. API 响应示例

新增 API：

```text
POST /api/tw-stock/rank-tech-cross/portfolio-replay
```

响应核心字段：

```json
{
  "ok": true,
  "status": "accepted",
  "simulation_only": true,
  "research_signal_not_order": true,
  "replay_type": "portfolio_rule_historical_simulation",
  "persist": false,
  "writes_business_db": false,
  "comparison": {
    "qlib_only": {
      "metrics": {},
      "equityCurve": [],
      "historicalActions": []
    }
  },
  "dataQuality": {
    "point_in_time": true,
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

## 7. 禁止字段检查结果

新增 service 静态检查未命中：

```text
INSERT INTO
UPDATE
DELETE
qd_tw_sim_orders
qd_tw_sim_trades
qd_tw_sim_positions
broker
quick_trade
target_position
target_weight
accepted_latest
provider_publish
立即买入 / 立即卖出 / 自动买入 / 自动卖出
下单 / 提交订单 / 目标仓位
上涨概率 / 收益承诺
order instruction
```

API route slice 未命中：

```text
tw_stock_sim_account_service
draft(
confirm(
BacktestService
monitor scan
alerts
publish
refresh
```

## 8. 测试命令与结果

```text
python -m py_compile backend/app/services/tw_stock_portfolio_replay.py backend/app/services/tw_stock_observation_replay.py backend/app/routes/tw_stock.py
结果：通过
```

```text
python -m pytest backend/tests/test_tw_stock_portfolio_replay.py backend/tests/test_tw_stock_portfolio_replay_api.py backend/tests/test_tw_stock_observation_replay.py backend/tests/test_tw_stock_observation_replay_api.py -q
结果：11 passed in 1.18s
```

```text
python -m pytest backend/tests/test_tw_stock_technical_status.py backend/tests/test_tw_stock_rank_tech_cross.py backend/tests/test_tw_stock_rank_tech_cross_api.py -q
结果：16 passed in 2.48s
```

```text
python backend/scripts/verify_tw_stock_research_stack.py
结果：通过；内部 pytest 86 passed in 1.88s
备注：普通沙箱执行遇到 bwrap loopback 环境错误，已按规则提权重跑，脚本返回 ok=true。
```

## 9. 安全边界确认

本步没有：

```text
写模拟账户
写模拟订单
写模拟成交
写模拟持仓
保存 monitor config
触发 monitor scan
写 alerts
连接 broker
调用 quick-trade
提交真实 order
生成 target position / target weight
触发 qlib refresh / publish / accepted latest switching
运行 daily auto update
修改前端页面
```

输出中的动作均为历史模拟动作，不是今日真实交易建议。

## 10. 残余风险

- 本步 metrics 是规则历史模拟，不代表真实投资收益。
- 价格来自本地日线数据，若日线缺失，会跳过动作并进入 `dataQuality.warnings`。
- 第一版按简单现金分配和固定 lotSize 估算，尚未覆盖真实滑点、撮合、流动性和完整税费细节。

## 11. Step 5 建议

Step 5 建议做只读前端展示：用简单表格展示三种 variant 的总收益、最大回撤、动作次数、费用和数据质量提示；不提供真实交易动作、目标仓位、下单入口或模拟账户写单入口。
