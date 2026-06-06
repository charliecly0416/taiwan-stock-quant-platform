# 台股排名技术交叉与组合回放 Step 1 执行文档：只读交叉分类契约

生成时间：2026-06-06

对应方案：`docs/TW_STOCK_RANK_TECH_CROSS_AND_PORTFOLIO_REPLAY_PLAN_CN.md`

## 1. 方案审查结论

方案总体合理，建议推进，但必须分步收敛。

合理点：

- qlib 排名回答“哪些股票进入研究池”，QuantDinger 趋势和 MA/RSI/MACD/Bollinger 回答“技术状态是否支持继续观察”，两者分层而不是混成黑盒分数，符合当前台股 research-only 主线。
- `qlib-only` 与 `qlib+tech` 对照适合放入组合规则历史回放，能解释技术确认是否降低换手、回撤或无效动作。
- 文档明确禁止真实买卖、目标仓位、上涨概率和收益承诺，方向正确。

需要修正的风险：

- 文案里的“每日最多买卖”“风险复盘卖出”容易被用户理解为交易执行。实现和 UI 中应统一改成“历史模拟新增动作”“历史模拟风险动作”或“复盘动作”，避免真实交易语义。
- `POST /api/tw-stock/sim/portfolio-replay` 虽然可用于计算型只读请求，但必须强制 `persist=false`，不得写模拟账户、订单、持仓或 monitor 配置。
- 第一版不能直接做完整组合回放。应先固化 `排名 × 趋势 × 技术状态` 的只读分类契约，再让后续 replay 复用同一套分类逻辑。

## 2. 本步目标

本步只实现和验收一个稳定后端契约：

```text
qlib ranking
  + QuantDinger daily trend
  + technical status placeholder/summary
  -> research-only cross decision
```

输出收敛为：

```text
new_watch
continue_watch
risk_review
manual_review
observe_only
data_insufficient
```

用户文案映射为：

```text
新增观察
继续观察
风险复盘
人工复核
仅观察
数据不足
```

本步不实现组合资金曲线，不做历史 replay，不新增前端页面。

## 3. 明确禁止

本步不得执行：

- 不新增真实交易 API。
- 不调用 broker、quick-trade、order、target position、target weight。
- 不写 `qd_tw_sim_orders`、`qd_tw_sim_trades`、`qd_tw_sim_positions`。
- 不保存 monitor config。
- 不触发 monitor scan。
- 不写 alerts。
- 不触发 qlib provider refresh、publish、accepted latest switching。
- 不运行 daily auto update。
- 不输出“买入/卖出/下单/目标仓位/上涨概率/收益承诺”作为行动建议。

允许：

- 读取 qlib latest accepted artifacts。
- 读取 `qd_tw_stock_daily_bars` 或现有 `KlineService:TWStock:1D`。
- 调用现有 `TWStockTrendService`。
- 读取内置技术策略模板元数据。
- 新增只读 service、只读 GET API、单元测试和文档。

## 4. 建议实现范围

### 4.1 新增或扩展 Service

优先新增独立 service，避免把组合回放逻辑塞进现有 `TWStockCrossAnalysisService`：

```text
backend/app/services/tw_stock_rank_tech_cross.py
```

职责：

- 读取 qlib latest Top30/Top50。
- 对每个 symbol 获取 QuantDinger 趋势摘要。
- 计算排名层级：`top10`、`top30`、`top50`、`outside_top50`。
- 计算技术状态：第一步可先由趋势状态映射得到，不跑重型单股回测。
- 输出统一分类和原因。

技术状态第一版允许保守实现：

```text
trend_label in uptrend/rebound      -> technical_strong
trend_label in sideways/unknown     -> technical_neutral
trend_label in downtrend/pullback   -> technical_weak
trend unavailable / stale / short   -> technical_data_insufficient
```

保留字段给后续 Step 2 接 MA/RSI/MACD/Bollinger：

```json
{
  "technical": {
    "status": "technical_neutral",
    "basis": "quantdinger_trend_only",
    "strategies": [],
    "warnings": []
  }
}
```

### 4.2 分类矩阵

本步应固化如下分类：

| rank tier | technical status | decision |
| --- | --- | --- |
| top10/top30 | technical_strong | new_watch |
| top10/top30 | technical_neutral | continue_watch |
| top10/top30 | technical_weak | manual_review |
| top50 | technical_strong | observe_only |
| top50 | technical_neutral/weak | observe_only |
| outside_top50 | technical_weak | risk_review |
| outside_top50 | technical_strong | manual_review |
| any | technical_data_insufficient | data_insufficient |

如果本步没有持仓输入，`outside_top50` 只作为 contract 支持，不强制从 latest top list 生成。

### 4.3 新增只读 API

建议新增：

```text
GET /api/tw-stock/rank-tech-cross/latest?bucket=top30&limit=120&maxItems=30
```

响应必须包含：

```json
{
  "ok": true,
  "status": "accepted",
  "simulation_only": true,
  "research_signal_not_order": true,
  "trading": {
    "orders_enabled": false,
    "connects_to_broker": false,
    "quick_trade_enabled": false,
    "writes_orders": false,
    "writes_positions": false
  },
  "items": [
    {
      "symbol": "2330",
      "rank": 1,
      "rankTier": "top10",
      "trend": {
        "label": "uptrend",
        "score": 72.4
      },
      "technical": {
        "status": "technical_strong",
        "basis": "quantdinger_trend_only",
        "strategies": []
      },
      "decision": {
        "code": "new_watch",
        "label": "新增观察",
        "priority": "high",
        "reason": "qlib Top10 且 QuantDinger 趋势偏强，进入优先复盘队列。"
      }
    }
  ],
  "summary": {
    "new_watch": 0,
    "continue_watch": 0,
    "risk_review": 0,
    "manual_review": 0,
    "observe_only": 0,
    "data_insufficient": 0
  }
}
```

注意：本 API 用 GET，避免第一步出现“POST 计算请求被误判为写请求”的审计噪声。组合 replay 的 POST 留到后续步骤。

## 5. 文件建议

建议新增：

```text
backend/app/services/tw_stock_rank_tech_cross.py
backend/tests/test_tw_stock_rank_tech_cross.py
backend/tests/test_tw_stock_rank_tech_cross_api.py
```

建议修改：

```text
backend/app/routes/tw_stock.py
```

本步不修改：

```text
frontend/src/views/tw-stock-monitor/index.vue
frontend/src/views/tw-stock-sim-account/index.vue
frontend/src/api/tw-stock.js
backend/app/services/tw_stock_sim_account.py
backend/app/services/backtest.py
```

如执行者认为必须修改前端，应停止并先提交下一步文档，不在 Step 1 扩范围。

## 6. 单元测试要求

### 6.1 Service 分类测试

覆盖：

- Top10 + technical strong -> `new_watch`
- Top30 + technical neutral -> `continue_watch`
- Top30 + technical weak -> `manual_review`
- Top50 + technical strong -> `observe_only`
- outside Top50 + technical weak -> `risk_review`
- trend unavailable -> `data_insufficient`
- qlib latest blocked -> 返回 blocked payload，不抛 500

### 6.2 API 安全测试

覆盖：

- `GET /api/tw-stock/rank-tech-cross/latest` 返回 200。
- 响应包含 `simulation_only=true`。
- 响应包含 `research_signal_not_order=true`。
- `trading.orders_enabled=false`。
- `trading.connects_to_broker=false`。
- `trading.writes_orders=false`。
- 不导入或调用 broker、quick_trade、order submission、target position。

### 6.3 文案语义测试

新增或扩展静态检查，确保本步新增文案不包含行动建议：

禁止出现在用户可见 decision label/reason 中：

```text
立即买入
立即卖出
自动买入
自动卖出
提交订单
连接券商
目标仓位
上涨概率
收益承诺
```

允许：

```text
新增观察
继续观察
风险复盘
人工复核
仅观察
历史模拟
只读
不是交易建议
```

## 7. 必跑命令

```text
python -m py_compile backend/app/services/tw_stock_rank_tech_cross.py backend/app/routes/tw_stock.py
python -m pytest backend/tests/test_tw_stock_rank_tech_cross.py backend/tests/test_tw_stock_rank_tech_cross_api.py -q
python backend/scripts/verify_tw_stock_research_stack.py
```

如果新增静态安全测试，补跑对应测试文件。

## 8. 验收标准

本步通过必须满足：

- 已有 qlib Top30/Top50 和 QuantDinger 趋势能输出统一 rank-tech decision。
- 分类结果只表达研究队列，不表达真实交易动作。
- API 为只读 GET。
- 不写模拟账户、订单、持仓、monitor config、alerts。
- 不触发 qlib ops、daily auto update、provider publish/refresh 或 accepted latest switching。
- 后端测试通过。
- `verify_tw_stock_research_stack.py` 通过。

## 9. 报告要求

执行完成后新增：

```text
docs/TW_STOCK_RANK_TECH_CROSS_AND_PORTFOLIO_REPLAY_STEP1_REPORT_CN.md
```

报告必须包含：

1. 修改文件清单。
2. rank tier 与 technical status 的分类契约。
3. API 响应示例。
4. 测试命令与结果。
5. 安全边界确认：无 broker、quick-trade、order、target position、monitor scan、alerts 写入、qlib ops。
6. 残余风险。
7. Step 2 建议：接入 MA/RSI/MACD/Bollinger 技术状态，仍不做组合 replay。

## 10. 审核断点

本步完成后停止，等待审查：

```text
docs/TW_STOCK_RANK_TECH_CROSS_AND_PORTFOLIO_REPLAY_STEP1_REPORT_CN.md
```

审查通过后，再编写 Step 2 执行文档。
