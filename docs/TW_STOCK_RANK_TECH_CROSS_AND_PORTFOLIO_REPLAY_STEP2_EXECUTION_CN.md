# 台股排名技术交叉与组合回放 Step 2 执行文档：轻量技术状态接入

生成时间：2026-06-06

前置报告：`docs/TW_STOCK_RANK_TECH_CROSS_AND_PORTFOLIO_REPLAY_STEP1_REPORT_CN.md`

## 1. Step 1 审查结论

Step 1 主线基本正确：已新增只读 `排名 × 趋势 × 技术状态` 分类契约和 GET API，没有实现组合回放、资金曲线或前端页面。

需要补强的点：

- 当前 worktree 中 `backend/app/routes/tw_stock.py` 还包含模拟账户 POST 路由等其它功能线改动。若这些不是 Step 1 本次新增，Step 2 report 需明确“既有/其它功能线改动，不属于本步”；若是 Step 1 引入，则属于范围偏离，必须拆出本功能线。
- Step 1 技术状态仍是 `quantdinger_trend_only`，符合第一步目标，但还没有接入 MA/RSI/MACD/Bollinger。
- Step 2 不能调用现有 backtest engine 跑单股资金曲线，否则会提前进入“历史回放/回测”阶段。应只做轻量指标状态计算。

## 2. 本步目标

把 `technical.status` 从单一趋势映射升级为：

```text
QuantDinger trend
  + MA status
  + RSI status
  + MACD status
  + Bollinger status
  -> technical summary
```

本步仍只服务于“今天研究队列分类”，不做组合回放。

输出继续收敛为：

```text
technical_strong
technical_neutral
technical_weak
technical_data_insufficient
```

每个策略只输出状态和解释，不输出交易动作。

## 3. 明确禁止

本步不得执行：

- 不新增 portfolio replay API。
- 不调用 `/api/indicator/backtest` 或 `BacktestService.run()`。
- 不生成资金曲线。
- 不生成交易列表。
- 不计算组合收益、胜率、换手率。
- 不写模拟账户、模拟订单、模拟成交、模拟持仓。
- 不保存 monitor config，不触发 monitor scan，不写 alerts。
- 不触发 qlib refresh、publish、accepted latest switching、daily auto update。
- 不连接 broker、quick-trade、真实 order、target position、target weight。
- 不输出“买入/卖出/下单/目标仓位/上涨概率/收益承诺”作为行动建议。

允许：

- 读取日线 K 线。
- 计算 MA、RSI、MACD、Bollinger 的当前状态。
- 扩展现有 `rank-tech-cross/latest` GET 响应。
- 新增只读 service、测试和文档。

## 4. 建议实现范围

### 4.1 新增轻量技术状态 Service

建议新增：

```text
backend/app/services/tw_stock_technical_status.py
```

职责：

- 从 `KlineService("TWStock", symbol, "1D")` 获取日线。
- 计算最近一根 K 线的技术状态。
- 返回结构化摘要。
- 不运行 backtest engine。
- 不生成 buy/sell signals。

建议 public method：

```python
class TWStockTechnicalStatusService:
    def analyze_symbol(self, *, symbol: str, limit: int = 120, strategies: list[str] | None = None) -> dict:
        ...
```

### 4.2 策略状态定义

策略状态只能使用研究语义：

```text
supportive
neutral
caution
data_insufficient
```

禁止使用：

```text
buy
sell
entry
exit
long
short
target
```

### 4.3 MA 状态

默认参数：

```text
fast=5
slow=20
```

建议规则：

- close > MA5 > MA20：`supportive`
- close < MA5 < MA20：`caution`
- 样本不足：`data_insufficient`
- 其它：`neutral`

### 4.4 RSI 状态

默认参数：

```text
period=14
```

建议规则：

- 40 <= RSI <= 65：`supportive`
- RSI > 75 或 RSI < 25：`caution`
- 样本不足：`data_insufficient`
- 其它：`neutral`

说明：不要把 RSI 写成“超买卖点”，只表达状态偏热、偏冷或可观察。

### 4.5 MACD 状态

默认参数：

```text
fast=12
slow=26
signal=9
```

建议规则：

- DIF > DEA 且 histogram >= 0：`supportive`
- DIF < DEA 且 histogram < 0：`caution`
- 样本不足：`data_insufficient`
- 其它：`neutral`

### 4.6 Bollinger 状态

默认参数：

```text
period=20
stdDev=2
```

建议规则：

- close 在 middle 和 upper 之间：`supportive`
- close 跌破 lower 或明显高于 upper：`caution`
- 样本不足：`data_insufficient`
- 其它：`neutral`

### 4.7 汇总状态

建议汇总：

```text
supportive_count >= 2 且 caution_count == 0 -> technical_strong
caution_count >= 2 -> technical_weak
data_insufficient_count >= 3 -> technical_data_insufficient
其它 -> technical_neutral
```

如果 QuantDinger trend 和策略状态冲突：

- trend strong + strategies weak -> `technical_neutral`，reason 写“趋势与指标分歧，人工复核优先”
- trend weak + strategies strong -> `technical_neutral`，reason 写“指标修复但趋势仍需确认”
- trend data insufficient -> 由策略状态决定，但 warnings 保留数据质量提示

## 5. API 契约调整

继续使用 Step 1 API：

```text
GET /api/tw-stock/rank-tech-cross/latest
```

新增可选参数：

```text
includeTechnicalStrategies=true|false
technicalStrategies=ma,rsi,macd,bollinger
```

默认：

```text
includeTechnicalStrategies=true
technicalStrategies=ma,rsi,macd,bollinger
```

响应中 `technical` 从 Step 1 的占位结构升级为：

```json
{
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
      "metrics": {"ma5": 123.4, "ma20": 120.1, "close": 125.0},
      "reason": "收盘价位于短中期均线上方，技术状态偏支持。"
    }
  ],
  "warnings": []
}
```

## 6. 文件建议

建议新增：

```text
backend/app/services/tw_stock_technical_status.py
backend/tests/test_tw_stock_technical_status.py
```

建议修改：

```text
backend/app/services/tw_stock_rank_tech_cross.py
backend/app/routes/tw_stock.py
backend/tests/test_tw_stock_rank_tech_cross.py
backend/tests/test_tw_stock_rank_tech_cross_api.py
```

本步不修改：

```text
frontend/src/views/tw-stock-monitor/index.vue
frontend/src/views/tw-stock-sim-account/index.vue
frontend/src/api/tw-stock.js
backend/app/services/backtest.py
backend/app/services/tw_stock_sim_account.py
```

## 7. 测试要求

### 7.1 技术状态单元测试

覆盖：

- MA supportive / neutral / caution / data_insufficient。
- RSI supportive / caution / data_insufficient。
- MACD supportive / caution / data_insufficient。
- Bollinger supportive / caution / data_insufficient。
- 汇总 supportive_count >= 2 -> `technical_strong`。
- caution_count >= 2 -> `technical_weak`。
- 样本不足 -> `technical_data_insufficient`。

### 7.2 Rank-Tech 集成测试

覆盖：

- `includeTechnicalStrategies=true` 时 `technical.basis=quantdinger_trend_plus_daily_indicators`。
- `strategies` 含 MA/RSI/MACD/Bollinger。
- trend strong + indicators weak 不直接输出 `new_watch`，应进入 `manual_review` 或 `continue_watch`。
- trend weak + indicators strong 不直接输出 `new_watch`。
- strategy warnings 会进入 item `technical.warnings`。

### 7.3 API 安全测试

覆盖：

- API 仍是 GET。
- 响应仍包含 `simulation_only=true`。
- 响应仍包含 `research_signal_not_order=true`。
- `trading.orders_enabled=false`。
- `trading.connects_to_broker=false`。
- `trading.quick_trade_enabled=false`。
- `trading.writes_orders=false`。
- `trading.writes_positions=false`。
- route slice 不含 `POST`、`draft`、`confirm`、`BacktestService`、`portfolio-replay`、`monitor scan`、`alerts`、`publish`、`refresh`。

### 7.4 文案安全测试

新增静态断言，检查新增 service 和 response reason 不含：

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
buy signal
sell signal
entry
exit
target weight
target position
```

允许：

```text
支持
中性
谨慎
观察
复盘
人工复核
数据不足
历史模拟
只读
```

## 8. 必跑命令

```text
python -m py_compile backend/app/services/tw_stock_technical_status.py backend/app/services/tw_stock_rank_tech_cross.py backend/app/routes/tw_stock.py
python -m pytest backend/tests/test_tw_stock_technical_status.py backend/tests/test_tw_stock_rank_tech_cross.py backend/tests/test_tw_stock_rank_tech_cross_api.py -q
python backend/scripts/verify_tw_stock_research_stack.py
```

如果触及任何前端文件，说明范围已经扩大，应停止并先补充 Step 2A 前端执行文档。

## 9. 验收标准

本步通过必须满足：

- 技术状态已包含 MA/RSI/MACD/Bollinger 的轻量日线摘要。
- 没有调用 backtest engine。
- 没有组合资金曲线、交易列表、组合收益或换手率。
- rank-tech decision 继续只表达研究队列。
- API 仍为只读 GET。
- 不写模拟账户、订单、持仓、monitor config、alerts。
- 不触发 broker、quick-trade、qlib ops、daily auto update。
- 测试和 `verify_tw_stock_research_stack.py` 通过。

## 10. 报告要求

执行完成后新增：

```text
docs/TW_STOCK_RANK_TECH_CROSS_AND_PORTFOLIO_REPLAY_STEP2_REPORT_CN.md
```

报告必须包含：

1. Step 1 审查修正说明。
2. 修改文件清单。
3. MA/RSI/MACD/Bollinger 状态规则。
4. 技术状态汇总规则。
5. API 响应示例。
6. 测试命令与结果。
7. 安全边界确认。
8. 明确说明未做 portfolio replay、未跑 backtest engine、未写模拟账户。
9. 残余风险。
10. Step 3 建议：只读对照实验设计，仍不接前端交易动作。

## 11. 审核断点

本步完成后停止，等待审查：

```text
docs/TW_STOCK_RANK_TECH_CROSS_AND_PORTFOLIO_REPLAY_STEP2_REPORT_CN.md
```

审查通过后，再编写 Step 3 执行文档。
