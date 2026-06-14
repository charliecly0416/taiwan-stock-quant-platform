# 台股人工复盘解释模块实现方案

## 1. 背景与主线切换

本方案是新的产品化方向，不是以下主线的延续：

- 不是 Entry Model v1 Phase 2D。
- 不是正交规则探索 Phase2E。
- 不是 fundamental PIT PhaseF0F/F1。
- 不是 Risk Filter Model。

已有结论：

- Entry Model v1 未稳定超过 `baseline_qlib_rank`，已归档失败。
- 法人筹码/融资融券规则有解释价值，但不足以作为模型 gate。
- fundamental PIT 主线因历史月营收 PIT 覆盖不足停止，不能进入样本或模型阶段。

因此当前最合理的方向是：

> 把已经验证可用或可冻结的只读研究信息，整理成用户能看懂的“人工复盘线索”，帮助用户理解为什么某只股票值得继续看、需要谨慎，或需要复盘，而不是生成买卖建议。

## 2. 用户第一性原则

模块必须符合：

1. 简单：用户不需要理解 qlib、PIT、factor、gate、IC 等工程概念。
2. 准确：所有线索必须来自已有只读数据或已冻结规则卡，不能夸大成模型结论。
3. 清晰：每只股票最多展示少量关键线索，明确“支持 / 冲突 / 风险 / 数据不足”。
4. 实用：帮助用户人工复盘，而不是替用户下决策。

## 3. 模块定位

模块名称建议：

- `人工复盘线索`
- 英文字段：`manual_review_explanation`

模块回答：

- 为什么这只股票需要人工复盘？
- 哪些信息互相支持？
- 哪些信息互相冲突？
- 有哪些风险不应忽略？
- 哪些信息只是背景，不足以单独支持结论？

模块不回答：

- 应不应该买入。
- 应不应该卖出。
- 买多少。
- 目标仓位是多少。
- 未来收益率是多少。
- 上涨概率是多少。

## 4. 可用输入

### 4.1 qlib 排名信息

可用字段：

- `symbol`
- `name`
- `asof`
- `rank`
- `qlib_score`
- `rank_tier`：Top10 / Top30 / Top50 / outside Top50
- 排名变化信息，若已有

解释用途：

- 模型研究排名靠前。
- 排名仍在 Top50。
- 跌出 Top50 需要复盘。

禁止：

- 把 qlib score 解释为预期收益率。
- 把 rank 高解释为“应该买入”。

### 4.2 QuantDinger 趋势

可用字段：

- `trend_label`
- `trend_score`
- `ret_5d`
- `ret_20d`
- `ret_60d`
- `ma5` / `ma20` / `ma60`
- `volume_ratio_to_avg20`
- `volatility_20d`

解释用途：

- 趋势偏强/偏弱。
- 短期反弹/回落。
- 量能是否配合。

### 4.3 技术状态

可用字段：

- MA 状态。
- RSI 状态。
- MACD 状态。
- Bollinger 状态。
- `technical_status`

解释用途：

- 技术支持。
- 技术中性。
- 技术转弱。
- 指标冲突。

### 4.4 价格位置风险

可用字段：

- `positionRisk.status`
- `price_percentile_120d`
- `distance_ma20_pct`
- `distance_ma60_pct`
- `rsi14`
- `bollinger_position`
- `return_5d_pct`
- `return_20d_pct`

解释用途：

- 排名强但位置偏高。
- 趋势强但短期涨幅过快。
- 回调到均线附近，可继续观察。
- 数据不足时不强行判断。

### 4.5 冻结的法人/融资融券解释规则卡

只能作为人工解释，不得升级为模型 gate 或自动过滤。

可用规则：

| rule_id | 允许用途 |
|---|---|
| `margin_crowding_top50_p85_caution` | 融资拥挤 caution 解释 |
| `flow_crowding_conflict_top50_p80_weak30_review` | 法人/拥挤冲突 review 解释 |
| `foreign_flow_non_crowded_top150_explanation` | 外资流向背景解释 |
| `margin_change_non_crowded_top150_auxiliary` | 融资变化辅助确认 |

禁止：

- 不得把这些规则作为 confirmed watch。
- 不得作为自动买卖。
- 不得作为模型训练 gate。
- 不得单独决定股票状态。

### 4.6 fundamental PIT 结果

当前 fundamental PIT 主线停止。

因此：

- 月营收/基本面暂不作为可用输入。
- 不得继续搜索月营收数据源。
- 不得用单期 TWSE current file 作为历史样本。
- 不得使用 FinMind `date/create_time` 作为公告日 proxy。

## 5. 输出设计

后端建议输出：

```json
{
  "symbol": "2330",
  "name": "台积电",
  "asof": "2026-06-10",
  "overall_status": "manual_review",
  "status_label": "需要人工复盘",
  "confidence": "medium",
  "summary": "模型排名仍靠前，但价格位置偏高且部分筹码线索提示谨慎，建议人工复盘。",
  "signals": [
    {
      "type": "support",
      "label": "模型排名靠前",
      "message": "位于 Top30，仍属于主要研究池。",
      "source": "qlib_rank",
      "severity": "info"
    },
    {
      "type": "risk",
      "label": "位置偏高",
      "message": "价格接近近 120 日高位，RSI 偏热。",
      "source": "position_risk",
      "severity": "caution"
    }
  ],
  "next_review_focus": [
    "确认趋势是否继续守住 MA20。",
    "观察 RSI 是否从偏热区回落。",
    "检查是否存在融资拥挤或法人撤退。"
  ],
  "research_only": true,
  "not_trading_advice": true
}
```

### 5.1 overall_status

允许值：

- `multi_source_support`：多源支持，但仍是研究线索。
- `manual_review`：需要人工复盘。
- `caution`：谨慎观察。
- `conflict`：信息冲突。
- `data_insufficient`：数据不足。

禁止值：

- `buy`
- `sell`
- `hold`
- `strong_buy`
- `target_position`
- `order_ready`

### 5.2 signals

每只股票最多展示 3 到 5 条关键线索。

类型：

- `support`
- `risk`
- `conflict`
- `background`
- `data_quality`

严重度：

- `info`
- `watch`
- `caution`
- `review`

### 5.3 文案原则

推荐文案：

- “模型排名靠前，属于研究池。”
- “趋势偏强，但价格位置偏高，适合人工复盘。”
- “技术指标与排名存在分歧。”
- “融资拥挤规则仅作为谨慎线索，不作为自动判断。”

禁止文案：

- “建议买入。”
- “建议卖出。”
- “强烈看涨。”
- “上涨概率 xx%。”
- “目标仓位 xx%。”
- “预计收益 xx%。”

## 6. 后端实现建议

新增服务：

- `backend/app/services/tw_stock_manual_review_explanation.py`

职责：

- 聚合 qlib rank、trend、technical status、position risk、冻结规则卡。
- 输出统一 explanation schema。
- 不写数据库。
- 不触发 provider。
- 不调用外部网络。
- 不训练模型。

建议 API：

- `GET /api/tw-stock/manual-review/explanations?bucket=top30`
- `GET /api/tw-stock/manual-review/explanations/{symbol}`

第一阶段可以只做服务层和只读 API contract，不急于前端。

## 7. 前端实现建议

如果后续接前端，建议合并到现有台股研究页面或模拟账户页面，不新增复杂页面。

UI 形态：

- 标题：`复盘线索`
- 每只股票显示：
  - 一个状态标签。
  - 一句摘要。
  - 最多 3 条线索。
  - 一个“查看详情”展开区。

不要展示：

- raw rule id。
- 内部 gate。
- IC / RankIC。
- run id。
- provider 信息。
- 复杂训练指标。

## 8. 分阶段执行计划

### Phase R0：Proposal 与 Contract

目标：

- 设计 explanation schema。
- 盘点输入来源。
- 明确冻结规则卡如何只读接入。
- 不写业务逻辑。
- 不接前端。

产物：

- `docs/tw_manual_review_explanation/PHASER0_EXECUTION_REPORT_CN.md`
- `docs/tw_manual_review_explanation/manual_review_explanation_contract.md`

Gate：

- schema 不含交易语义。
- 输入来源均为已有只读数据。
- 不继续 fundamental / 正交数据源探索。

### Phase R1：后端只读服务

目标：

- 实现服务层。
- 支持单 symbol 和 bucket 聚合。
- 输出 explanation schema。
- 添加后端单元测试。

Gate：

- 不写数据库。
- 不调用外部网络。
- 不触发 provider。
- 测试覆盖强排名+位置偏高、排名弱+技术弱、信息冲突、数据不足。

### Phase R2：只读 API

目标：

- 暴露只读 API。
- 添加 API 测试。
- 确认无 POST/PUT/PATCH/DELETE。

Gate：

- API 仅 GET。
- 响应不含买卖/仓位/收益承诺。

### Phase R3：前端轻量展示

目标：

- 在台股研究或模拟账户页面增加“复盘线索”轻量区块。
- 不新增复杂页面。
- 不影响现有主流程。

Gate：

- 页面清晰。
- 每只股票最多显示少量关键信息。
- 不出现交易建议。

### Phase R4：只读验收

目标：

- 后端测试。
- 前端静态检查。
- Playwright 只读检查。
- 安全文案扫描。

Gate：

- 无危险请求。
- 无 provider/accepted latest/monitor/交易路径。
- 用户能理解该模块是复盘线索，不是买卖建议。

## 9. 执行与审查机制

继续采用双窗口：

1. 审查者先给下一步工作文档。
2. 执行者只执行该文档。
3. 执行者完成后写执行报告。
4. 审查者审查代码、报告、测试和安全边界。
5. 审查者给出下一步工作文档。
6. 如需前端/API、改变目标、引入新数据、模型训练，必须停下来问用户。

## 10. 当前建议

下一步从 Phase R0 开始。

第一轮审查者应创建：

`docs/tw_manual_review_explanation/PHASER0_REVIEW_BASELINE_AND_NEXT_WORK_CN.md`

只允许执行者做 proposal、contract、输入来源盘点，不允许编码业务服务、前端、API、模型、新数据源或联网。

