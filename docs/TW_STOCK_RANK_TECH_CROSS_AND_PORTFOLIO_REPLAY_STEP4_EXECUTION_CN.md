# 台股排名技术交叉与组合回放 Step 4 执行文档：不落库组合规则历史回放

生成时间：2026-06-06

前置报告：`docs/TW_STOCK_RANK_TECH_CROSS_AND_PORTFOLIO_REPLAY_STEP3_REPORT_CN.md`

## 1. Step 3 审查结论

Step 3 主线基本正确：

- 已实现 observation-only 历史观察队列对照。
- 已区分 `qlib_only`、`qlib_plus_trend`、`qlib_plus_trend_indicators`。
- 已实现趋势和轻量技术状态的 point-in-time 截断。
- 没有输出收益、回撤、胜率、换手、资金曲线或交易列表。
- 没有写模拟账户、订单、持仓、monitor config、alerts。

需要补强的点：

- `TWStockObservationReplayService._daily_compare()` 应明确处理 `run_detail(ok=false)` 或空 signals 的情况，并把 `run_detail_blocked` / `empty_run_signals` 写入 `dataQuality.warnings`，避免用户把空队列误解为规则结果。
- 当前 `backend/app/routes/tw_stock.py` 的 diff 仍混有模拟账户 POST 等其它功能线改动。Step 4 report 必须继续区分本步改动与既有/其它功能线改动。
- Step 4 开始允许历史模拟绩效指标，但必须限定为“不落库组合规则历史回放”，不得接入真实交易、模拟账户写单或前端交易动作。

## 2. 本步目标

基于 Step 3 的 point-in-time observation variants，实现不落库组合规则历史回放。

本步回答：

- 过去若按同一套研究规则形成低换手组合，历史模拟总收益、最大回撤、动作次数和费用大概如何？
- `qlib_only`、`qlib_plus_trend`、`qlib_plus_trend_indicators` 三种规则的历史模拟差异是什么？
- 加入趋势和技术状态后，是否减少历史模拟动作、降低回撤或提高数据质量可解释性？

本步仍不回答：

- 今天应该真实买入或卖出什么。
- 目标仓位是多少。
- 未来收益、胜率或上涨概率是多少。

## 3. 明确禁止

本步不得执行：

- 不写 `qd_tw_sim_accounts`。
- 不写 `qd_tw_sim_orders`。
- 不写 `qd_tw_sim_trades`。
- 不写 `qd_tw_sim_positions`。
- 不保存 monitor config。
- 不触发 monitor scan。
- 不写 alerts。
- 不调用 broker。
- 不调用 quick-trade。
- 不提交真实 order。
- 不生成 target position / target weight。
- 不触发 qlib refresh、publish、provider mutation、accepted latest switching。
- 不运行 daily auto update。
- 不修改前端页面。
- 不把历史模拟动作写成真实交易建议。

允许：

- 读取 historical accepted qlib run artifacts。
- 读取 point-in-time 日线价格。
- 读取 Step 3 的 observation variants。
- 在内存中计算历史模拟现金、持有数量、净值曲线、费用税费和动作列表。
- 返回只读 JSON。

## 4. API 设计

新增只读计算 API：

```text
POST /api/tw-stock/rank-tech-cross/portfolio-replay
```

说明：本接口使用 POST 只是为了传入较复杂参数，不表示写入。必须强制：

```json
{
  "persist": false,
  "simulation_only": true,
  "writes_business_db": false
}
```

请求示例：

```json
{
  "startDate": "2025-12-01",
  "endDate": "2026-06-01",
  "initialCash": 1000000,
  "bucket": "top30",
  "maxItems": 30,
  "maxAddPerDay": 1,
  "maxRiskActionPerDay": 1,
  "maxHoldings": 10,
  "lotSize": 10,
  "profile": "balanced",
  "variant": "all",
  "technicalStrategies": ["ma", "rsi", "macd", "bollinger"],
  "persist": false
}
```

响应必须包含：

```json
{
  "ok": true,
  "status": "accepted",
  "simulation_only": true,
  "research_signal_not_order": true,
  "replay_type": "portfolio_rule_historical_simulation",
  "persist": false,
  "writes_business_db": false,
  "trading": {
    "orders_enabled": false,
    "connects_to_broker": false,
    "quick_trade_enabled": false,
    "writes_orders": false,
    "writes_positions": false
  },
  "comparison": {
    "qlib_only": {
      "metrics": {
        "totalReturn": 0.052,
        "maxDrawdown": -0.081,
        "actionCount": 34,
        "feeAndTax": 12345.0
      }
    },
    "qlib_plus_trend": {"metrics": {}},
    "qlib_plus_trend_indicators": {"metrics": {}}
  },
  "dataQuality": {
    "point_in_time": true,
    "warnings": []
  }
}
```

禁止响应字段：

```text
targetWeight
targetPosition
orderInstruction
broker
quickTrade
```

## 5. Service 设计

建议新增：

```text
backend/app/services/tw_stock_portfolio_replay.py
```

职责：

- 调用或复用 `TWStockObservationReplayService` 获取 point-in-time daily variants。
- 对每个 variant 独立做内存组合历史模拟。
- 使用 `qd_tw_stock_daily_bars` 或现有 KlineService 获取 `trade_date <= asof` 的收盘价。
- 计算历史模拟净值和摘要指标。
- 不写任何数据库。

建议 public method：

```python
class TWStockPortfolioReplayService:
    def replay(self, *, config: dict) -> dict:
        ...
```

## 6. 历史模拟规则

### 6.1 资金与费用

默认：

```text
initialCash=1000000
feeRate=0.001425
sellTaxRate=0.003
lotSize=10
maxHoldings=10
maxAddPerDay=1
maxRiskActionPerDay=1
```

说明：

- 这里的 `sellTaxRate` 仅用于历史模拟费用估算，不代表真实税务建议。
- `lotSize=10` 继承当前研究模拟账户的最小单位语义。

### 6.2 观察队列到历史模拟动作

动作名称必须使用研究语义：

```text
historical_add
historical_risk_reduce
historical_hold
historical_skip
```

禁止使用用户可见动作：

```text
立即买入
立即卖出
下单
提交订单
目标仓位
```

建议规则：

- `new_watch`：若现金足够、未持有、持仓数未满，当日最多 `maxAddPerDay` 个 `historical_add`。
- `risk_review`：若已在历史模拟持有，当日最多 `maxRiskActionPerDay` 个 `historical_risk_reduce`。
- `manual_review`：不自动动作，只记录 `historical_skip`，reason 为人工复核。
- `continue_watch` / `observe_only`：默认 `historical_hold` 或 `historical_skip`。
- `data_insufficient`：不动作，记录数据不足。

### 6.3 持有数量

第一版建议：

```text
perActionCash = availableCash / remainingSlots
quantity = floor(perActionCash / close / lotSize) * lotSize
```

注意：

- 不输出目标权重。
- 不输出建议仓位。
- 只输出实际历史模拟数量和现金影响。

## 7. 输出字段

允许输出：

```text
metrics.totalReturn
metrics.maxDrawdown
metrics.actionCount
metrics.addActionCount
metrics.riskActionCount
metrics.feeAndTax
metrics.finalEquity
equityCurve[]
historicalActions[]
dataQuality
```

`historicalActions[]` 字段建议：

```json
{
  "date": "2026-06-01",
  "symbol": "2330",
  "action": "historical_add",
  "quantity": 100,
  "price": 125.0,
  "reason": "历史模拟：new_watch 且组合仍有现金与持有名额。",
  "simulation_only": true
}
```

禁止输出：

```text
order_id
order_uid
sim_order_uid
trade_uid
target_weight
target_position
broker_account
quick_trade
```

## 8. 文件建议

建议新增：

```text
backend/app/services/tw_stock_portfolio_replay.py
backend/tests/test_tw_stock_portfolio_replay.py
backend/tests/test_tw_stock_portfolio_replay_api.py
```

建议修改：

```text
backend/app/routes/tw_stock.py
docs/TW_STOCK_RANK_TECH_CROSS_AND_PORTFOLIO_REPLAY_STEP4_REPORT_CN.md
```

本步不修改：

```text
frontend/*
backend/app/services/tw_stock_sim_account.py
backend/app/services/backtest.py
```

如执行者认为必须改前端，停止并先提交 Step 4A 前端文档。

## 9. 测试要求

### 9.1 Service 测试

必须覆盖：

- 三种 variant 都能独立返回 metrics。
- `persist=true` 输入会被拒绝或强制转为 false。
- 没有 accepted runs 时返回清晰 dataQuality warning。
- price 缺失时跳过动作并记录 warning。
- `manual_review` 不产生 add/reduce 动作。
- `data_insufficient` 不产生 add/reduce 动作。
- 输出包含 `equityCurve[]`，但不包含真实 order/trade ids。

### 9.2 API 测试

必须覆盖：

- `POST /api/tw-stock/rank-tech-cross/portfolio-replay` 返回 `simulation_only=true`。
- `persist=false`。
- `writes_business_db=false`。
- `trading.orders_enabled=false`。
- `trading.connects_to_broker=false`。
- `trading.quick_trade_enabled=false`。
- `trading.writes_orders=false`。
- `trading.writes_positions=false`。
- route slice 不含 `tw_stock_sim_account_service`、`draft(`、`confirm(`、`BacktestService`、`monitor scan`、`alerts`、`publish`、`refresh`。

### 9.3 安全静态测试

必须检查新增 service 不含：

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
```

### 9.4 文案测试

禁止用户可见文案包含：

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
order instruction
```

允许：

```text
历史模拟
观察队列
风险复盘
人工复核
simulation_only
not investment advice
```

## 10. 必跑命令

```text
python -m py_compile backend/app/services/tw_stock_portfolio_replay.py backend/app/services/tw_stock_observation_replay.py backend/app/routes/tw_stock.py
python -m pytest backend/tests/test_tw_stock_portfolio_replay.py backend/tests/test_tw_stock_portfolio_replay_api.py backend/tests/test_tw_stock_observation_replay.py backend/tests/test_tw_stock_observation_replay_api.py -q
python backend/scripts/verify_tw_stock_research_stack.py
```

如果本步修改了 trend、technical 或 rank-tech service，也补跑对应测试：

```text
python -m pytest backend/tests/test_tw_stock_technical_status.py backend/tests/test_tw_stock_rank_tech_cross.py backend/tests/test_tw_stock_rank_tech_cross_api.py -q
```

## 11. 验收标准

本步通过必须满足：

- portfolio replay 只在内存中计算。
- 三种 variant 都有历史模拟 metrics。
- 输出明确 `simulation_only=true`、`persist=false`、`writes_business_db=false`。
- 没有写模拟账户、订单、成交、持仓。
- 没有 broker、quick-trade、真实 order、monitor、alerts、qlib ops。
- 输出不包含目标仓位、目标权重、真实交易建议。
- 测试和 `verify_tw_stock_research_stack.py` 通过。

## 12. 报告要求

执行完成后新增：

```text
docs/TW_STOCK_RANK_TECH_CROSS_AND_PORTFOLIO_REPLAY_STEP4_REPORT_CN.md
```

报告必须包含：

1. Step 3 审查修正说明。
2. 修改文件清单。
3. 不落库保证说明。
4. 历史模拟规则。
5. 三种 variant 的 metrics 对照示例。
6. API 响应示例。
7. 禁止字段检查结果。
8. 测试命令与结果。
9. 安全边界确认。
10. 残余风险。
11. Step 5 建议：只读前端展示，不提供真实交易动作。

## 13. 审核断点

本步完成后停止，等待审查：

```text
docs/TW_STOCK_RANK_TECH_CROSS_AND_PORTFOLIO_REPLAY_STEP4_REPORT_CN.md
```

审查通过后，再编写 Step 5 执行文档。
