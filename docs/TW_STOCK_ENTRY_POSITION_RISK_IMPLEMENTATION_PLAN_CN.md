# 台股入场位置风险与追高风险实现方案

日期：2026-06-08

## 1. 结论

需要做，但不应该新增一个一级模块。

用户真正关心的不是“这支股票是不是上涨”，而是：

- 它为什么值得看？
- 现在的位置会不会太高？
- 如果已经持有，是继续观察还是风险复盘？
- 如果没有持有，是优先观察、等待回调，还是暂时跳过？

因此建议把“入场位置风险 / 追高风险”合并进现有 `技术状态 technical_status` 和 `排名 × 趋势 × 技术状态` 主链路，而不是再加一个新页面。

最终用户看到的表达应该收敛成简单标签：

- 位置合理
- 强势但偏高
- 过热，谨慎追高
- 回调观察
- 数据不足

这些标签只服务研究复盘和模拟验证，不是投资建议，不生成真实订单，不连接券商。

## 2. 用户第一准则

本功能必须坚持“清晰、简单、准确、有用”。

### 2.1 清晰

用户不应该被迫理解复杂指标。页面不要直接堆：价格百分位、MA 偏离、RSI、Bollinger z-score、20 日涨幅等工程字段。

普通用户第一眼只看：

```text
趋势：上升
位置：强势但偏高
原因：距离 20 日均线较远，RSI 偏热，靠近区间高位
动作语义：先观察或人工复核，不直接生成大量模拟草稿
```

### 2.2 简单

不新增一级入口，不新增“位置分析”大页面。

优先嵌入现有 4 个位置：

1. 台股研究页“今日复盘与历史模拟”。
2. 交叉分析表格。
3. 模拟账户的候选列表。
4. 组合规则历史回放。

### 2.3 准确

“上涨趋势”和“适合现在入场”必须分开。

系统不能把 `uptrend` 直接等价为“适合入手”。更准确的解释是：

```text
趋势回答方向，位置回答追高风险，排名回答研究优先级。
```

### 2.4 有用

功能输出必须影响用户实际复盘优先级：

- 趋势好且位置合理：提高优先观察级别。
- 趋势好但明显偏高：不再直接列为强候选，改为“强势但偏高 / 等待回调观察”。
- 排名高但位置过热：进入人工复核，而不是新增观察。
- 已持有且位置过热：提示风险复盘，不自动生成卖出动作。

## 3. 当前项目是否已经考虑

已有部分能力，但表达不完整。

### 3.1 已有能力

`backend/app/services/tw_stock_technical_status.py` 已经计算：

- MA：收盘价与 MA5/MA20 的关系。
- RSI：RSI14 是否偏热或偏冷。
- MACD：动能确认。
- Bollinger：是否偏离布林区间。

`backend/app/services/tw_stock_rank_tech_cross.py` 已经把 qlib 排名、QuantDinger 趋势、技术状态合成：

- 新增观察
- 继续观察
- 风险复盘
- 人工复核
- 仅观察
- 数据不足

模拟账户页也已经有买入候选、卖出候选、保留候选、人工复核和组合策略提示。

### 3.2 当前缺口

现有 `technical_status` 偏向判断“技术状态强弱”，但没有单独表达“位置是否太高”。

例如一支股票可能同时满足：

- 趋势上升。
- qlib 排名靠前。
- MACD 支持。
- 但价格距离 MA20 很远、RSI 偏热、处于 120 日高位附近。

当前系统可能仍把它归为技术偏强或新增观察，用户会误解为“上涨就值得动手”。这就是需要补的位置风险层。

## 4. 产品设计：不新增模块，合入现有主线

### 4.1 台股研究页

在“今日复盘与历史模拟”区块里，每个优先标的增加一个短标签：

```text
位置合理
强势但偏高
过热谨慎
回调观察
数据不足
```

展示方式：

```text
2357 华硕 · Top10 · 技术偏强 · 位置：强势但偏高
原因：趋势仍在，但 RSI 偏热且价格接近 120 日高位，适合人工复核。
```

不要新增很多指标列。点击展开或 hover 时再显示：

- RSI14。
- 距 MA20 偏离。
- 距 MA60 偏离。
- 120 日价格百分位。
- Bollinger 位置。

### 4.2 交叉分析

交叉分析目前回答 qlib 与 QuantDinger 是否一致。新增位置风险后，交叉分析应改成三层解释：

```text
排名：Top10
趋势：上升
位置：强势但偏高
结论：人工复核
```

这比单纯“qlib 高 + trend up = 好”更符合真实用户决策。

### 4.3 模拟账户候选

模拟账户候选不要只按 qlib 排名和趋势给置信度。应把位置风险作为扣分项：

- 位置合理：候选置信度可正常保留。
- 强势但偏高：候选置信度降低，原因显示“等待回调更稳妥”。
- 过热谨慎：不放入高优先级候选，进入人工复核。
- 回调观察：如果趋势未破坏，可留在观察候选，不自动鼓励生成模拟草稿。

用户看到的是：

```text
买入候选：2357 华硕
置信度：62
原因：qlib Top10，趋势上升，但位置偏高，建议先小额模拟或等待回调验证。
```

注意：这里仍然是模拟账户语境，不能变成真实交易建议。

### 4.4 组合规则历史回放

组合规则历史回放必须纳入位置风险，否则页面说“不要追高”，历史模拟却仍在高位追入，前后口径会冲突。

新增对照规则：

1. `qlib_only`：只看 qlib 排名。
2. `qlib_plus_trend`：加入 QuantDinger 趋势。
3. `qlib_plus_trend_indicators`：加入现有技术指标。
4. `qlib_plus_trend_position_risk`：加入位置风险过滤。

用户只看到对照结果，不展示复杂参数：

```text
加入位置风险后：交易次数减少，最大回撤变化，总收益变化，费用变化。
```

如果位置风险过滤让收益下降但回撤明显降低，也要如实展示，不能只显示收益最高。

## 5. 后端设计

### 5.1 扩展 technical status，不新增独立服务作为主入口

建议在 `TWStockTechnicalStatusService.analyze_symbol()` 返回中新增：

```json
{
  "positionRisk": {
    "status": "elevated",
    "label": "强势但偏高",
    "score": 68,
    "reason": "距离 MA20 较远，RSI 偏热，处于近 120 日高位区间。",
    "metrics": {
      "close": 918,
      "ma20": 861.2,
      "ma60": 802.4,
      "distance_ma20_pct": 6.6,
      "distance_ma60_pct": 14.4,
      "rsi14": 72.3,
      "price_percentile_120d": 91.5,
      "bollinger_position": 0.93,
      "return_5d_pct": 8.1,
      "return_20d_pct": 18.4
    },
    "warnings": []
  }
}
```

字段语义：

- `score`: 0 到 100，越高代表追高风险越高，不是上涨概率。
- `status`: `reasonable | elevated | overheated | pullback_watch | data_insufficient`。
- `label`: 给用户看的短标签。
- `reason`: 一句话解释。
- `metrics`: 供调试、展开详情、测试和历史回放使用。

### 5.2 指标计算建议

位置风险不预测未来，只评估当前价格位置。

建议用这些只读日线指标：

| 指标 | 作用 | 用户解释 |
| --- | --- | --- |
| `distance_ma20_pct` | 短中期乖离 | 离 20 日均线越远，追高风险越高 |
| `distance_ma60_pct` | 中期乖离 | 离 60 日均线过远时，回撤空间可能变大 |
| `rsi14` | 短线热度 | RSI 过高代表偏热，不等于一定下跌 |
| `price_percentile_120d` | 区间位置 | 越接近近 120 日高位，越不适合盲目追 |
| `bollinger_position` | 布林位置 | 靠近或越过上轨时，追高风险上升 |
| `return_5d_pct` | 短线涨幅 | 近期涨太快时降低入场优先级 |
| `return_20d_pct` | 波段涨幅 | 波段涨幅过大时提示等待复核 |

### 5.3 默认阈值

第一版使用保守规则，避免过度拟合。

```text
数据不足：少于 60 根日线。
过热谨慎：price_percentile_120d >= 92 且 RSI14 >= 72，或 distance_ma20_pct >= 12%。
强势但偏高：price_percentile_120d >= 85，或 RSI14 >= 68，或 distance_ma20_pct >= 8%。
位置合理：趋势不弱，price_percentile_120d 介于 35 到 85，distance_ma20_pct 不超过 8%，RSI14 不超过 68。
回调观察：趋势未明显转弱，但 price_percentile_120d 从高位回落、价格接近 MA20 或 Bollinger 中轨。
```

阈值不要在第一版暴露给普通用户。后续可在高级配置里调整。

### 5.4 与 rank-tech decision 的融合

在 `TWStockRankTechCrossService.decision_for()` 上层新增融合逻辑，不直接替换原有技术状态。

建议规则：

| qlib 层级 | technical status | position risk | 输出 |
| --- | --- | --- | --- |
| Top10/Top30 | strong | reasonable | 新增观察 |
| Top10/Top30 | strong | elevated | 继续观察 / 人工复核 |
| Top10/Top30 | strong | overheated | 人工复核 |
| Top10/Top30 | neutral | reasonable | 继续观察 |
| Top10/Top30 | weak | 任意 | 人工复核 |
| Top50 | strong | reasonable | 仅观察 |
| Top50 | strong | elevated/overheated | 仅观察 / 人工复核 |
| outside_top50 | weak | 任意 | 风险复盘 |
| 持仓 | 任意 | overheated | 风险复盘提示，但不自动生成卖出动作 |

返回 item 中新增：

```json
{
  "positionRisk": {...},
  "decision": {
    "code": "manual_review",
    "label": "人工复核",
    "reason": "模型排名靠前且趋势偏强，但位置偏高，先复核追高风险。"
  }
}
```

## 6. 前端设计

### 6.1 台股研究页首屏

只增加一个短标签和一句原因，不新增大表格。

当前位置：`frontend/src/views/tw-stock-monitor/index.vue`

推荐展示：

```text
[新增观察] [位置合理]
[继续观察] [强势但偏高]
[人工复核] [过热谨慎]
```

颜色建议：

- 位置合理：绿色。
- 强势但偏高：蓝色或金色。
- 过热谨慎：橙色。
- 回调观察：紫色或蓝色。
- 数据不足：灰色。

不要用红色表达“过热”作为卖出暗示，除非在持仓风险复盘区块中。

### 6.2 交叉分析表格

新增一列或并入“趋势/技术”列：

```text
位置：强势但偏高
```

如果列太多，优先并入现有技术摘要，不单独加列。用户第一屏信息密度比字段完整性更重要。

### 6.3 模拟账户页

当前位置：`frontend/src/views/tw-stock-sim-account/index.vue`

需要调整：

- `buyConfidence(item)`：位置风险 elevated/overheated 扣分。
- `buyReason(item, confidence)`：解释为什么降低候选优先级。
- `strategyReviewCandidates`：把 overheated 高排名标的纳入人工复核。
- `technicalStatus(item)` / `riskHint(item)`：能显示位置风险。

候选区保持固定高度滚动，不因为新增标签让页面变长。

### 6.4 文案

推荐文案：

- `强势但偏高，先观察回调或人工复核。`
- `位置合理，但仍需看资料日期和历史模拟。`
- `偏热谨慎，不把上涨趋势直接等同于适合入场。`

避免文案：

- `现在买入`
- `立即卖出`
- `必涨`
- `上涨概率`
- `目标仓位`
- `建议重仓`

## 7. 历史回放设计

### 7.1 为什么必须纳入历史回放

如果只在今日页面提示“不要追高”，但历史回放仍按 qlib 排名直接加入，用户会看到两个冲突系统。

因此 `TWStockPortfolioReplayService` 应新增一个 variant：

```text
qlib_plus_trend_position_risk
```

或把现有 `qlib_plus_trend_indicators` 扩展为包含 position risk，并在结果里明确说明。

更推荐新增一个对照 variant，因为用户能直观看到加入位置风险后对收益、回撤、动作次数和费用的影响。

### 7.2 回放规则

第一版规则：

- 新增观察候选必须不是 `overheated`。
- `elevated` 可以进入观察池，但降低排序优先级。
- `reasonable` 优先级正常。
- 持仓如果 `overheated`，不自动当作历史卖出条件，只记录风险复盘事件；是否计入减仓规则用后续高级配置决定。

这样避免把“高位”简单等同于“应该卖”，更符合金融常识。

### 7.3 输出

每个 variant 增加：

```json
{
  "positionRiskSummary": {
    "blocked_overheated_adds": 12,
    "deprioritized_elevated_adds": 21,
    "risk_review_events": 9
  }
}
```

前端只展示一句：

```text
位置过滤：避开 12 次过热新增，21 次候选降级。
```

## 8. API 兼容性

不建议新增一级 API。

优先扩展已有接口：

```text
GET /api/tw-stock/rank-tech-cross/latest
POST /api/tw-stock/rank-tech-cross/portfolio-replay
```

新增参数：

```text
includePositionRisk=true
positionRiskMode=balanced
```

默认：

- `includePositionRisk=true`，因为这是用户价值的一部分。
- 旧前端如果不读取 `positionRisk` 字段也不受影响。

## 9. 测试方案

### 9.1 后端单元测试

新增或扩展：

```text
backend/tests/test_tw_stock_technical_status.py
backend/tests/test_tw_stock_rank_tech_cross.py
backend/tests/test_tw_stock_portfolio_replay.py
```

覆盖场景：

- 趋势强但 RSI 高、价格靠近 120 日高位 -> `positionRisk.status=overheated/elevated`。
- 趋势强且价格靠近 MA20、RSI 正常 -> `reasonable`。
- 样本少于 60 根 -> `data_insufficient`。
- Top10 + technical strong + overheated -> decision 降为人工复核。
- Top10 + technical strong + reasonable -> 仍为新增观察。
- portfolio replay 中 overheated 新增被阻止或降级。

### 9.2 前端静态测试

扩展：

```text
frontend/tests/unit/tw-stock-rank-tech-portfolio-replay-check.mjs
frontend/tests/unit/tw-stock-sim-account-check.mjs
frontend/tests/unit/tw-stock-cross-analysis-check.mjs
```

检查：

- 页面包含位置风险标签。
- 页面不新增一级导航入口。
- 文案不包含真实交易暗示。
- 模拟账户候选会显示位置风险原因。

### 9.3 Playwright 只读 E2E

扩展已有只读 E2E：

```text
frontend/tests/e2e/tw-stock-rank-tech-portfolio-replay-readonly.mjs
```

断言：

- `positionRisk` 渲染为“强势但偏高 / 过热谨慎”。
- 高排名但过热标的出现在人工复核，而不是最高优先新增观察。
- portfolio replay 请求仍然 `persist=false`。
- `forbidden_request_count=0`。
- 不触发 `/api/tw-stock/sim/**` 写请求。
- 不触发 broker、quick-trade、orders、target position、accepted latest switch、provider publish/refresh。

## 10. 实施步骤

### Step 1：后端 positionRisk 指标

修改：

- `backend/app/services/tw_stock_technical_status.py`
- `backend/tests/test_tw_stock_technical_status.py`

目标：在 `analyze_symbol()` 返回 `positionRisk`，不改变现有 `status` 的含义。

### Step 2：rank-tech 决策融合

修改：

- `backend/app/services/tw_stock_rank_tech_cross.py`
- `backend/tests/test_tw_stock_rank_tech_cross.py`
- `backend/tests/test_tw_stock_rank_tech_cross_api.py`

目标：TopN + 技术强 + 位置过热时不再直接归为新增观察，而是人工复核或继续观察。

### Step 3：前端研究页展示

修改：

- `frontend/src/views/tw-stock-monitor/index.vue`
- `frontend/tests/unit/tw-stock-rank-tech-portfolio-replay-check.mjs`

目标：在“今日复盘与历史模拟”和交叉分析里显示位置风险短标签，不增加页面复杂度。

### Step 4：模拟账户候选融合

修改：

- `frontend/src/views/tw-stock-sim-account/index.vue`
- `frontend/tests/unit/tw-stock-sim-account-check.mjs`

目标：候选置信度纳入位置风险，高位候选降低优先级或进入人工复核。

### Step 5：组合回放纳入位置风险

修改：

- `backend/app/services/tw_stock_portfolio_replay.py`
- `backend/tests/test_tw_stock_portfolio_replay.py`
- `frontend/src/views/tw-stock-monitor/index.vue`

目标：新增位置风险过滤 variant，并展示其对收益、回撤、动作次数和费用的影响。

### Step 6：最终只读验收

执行：

- 后端 pytest。
- 前端静态测试。
- Playwright 只读 E2E。
- 前端 build。
- 只读安全边界审查。

通过标准：

- 用户第一屏仍能回答“今天看什么、为什么、过去表现如何”。
- 没有新增一级模块。
- 没有真实交易语义。
- 没有 broker、quick-trade、orders、target position。
- portfolio replay 仍为 `persist=false`。

## 11. 不做事项

第一版不做：

- 自动真实买卖。
- 目标仓位或目标权重。
- 预测上涨概率。
- 收益承诺。
- 复杂参数调参页面。
- 新增“位置风险”一级导航。
- 把过热直接解释成必须卖出。

## 12. 最终用户体验

用户不需要学习一套新系统。

原来看到：

```text
华硕：Top10，趋势上升，技术偏强
```

改造后看到：

```text
华硕：Top10，趋势上升，技术偏强，位置：强势但偏高
原因：模型排名靠前，但价格接近近 120 日高位且 RSI 偏热，先人工复核，不把上涨趋势直接等同于适合入场。
```

这才符合金融小白真正需要的决策辅助：

```text
不是告诉我涨了，而是告诉我现在看它时应该注意什么风险。
```
