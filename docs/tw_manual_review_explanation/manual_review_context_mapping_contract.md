# Manual Review 上下文字段映射合同

- 阶段：Phase R8
- 日期：2026-06-12
- 状态：设计合同，未实现代码

## 1. 目标

本合同定义人工复盘解释模块后续可接入的现有只读上下文字段，以及这些字段进入 `manual_review_explanation` 时的用户可见位置、文案限制、缺失 fallback 和 R9 实现建议。

R8 只做设计，不实现映射。

## 2. 输入边界

允许使用的现有只读来源：

- `GET /api/tw-stock/manual-review/explanation`
- `GET /api/tw-stock/rank-tech-cross/latest`
- `GET /api/tw-stock/quant/signals/latest`
- `GET /api/tw-stock/quant/signals/rank-changes`
- `GET /api/tw-stock/cross-analysis/latest`
- `GET /api/tw-stock/cross-analysis/symbol/<symbol>`
- 现有服务内只读输出：
  - `backend/app/services/tw_manual_review_explanation.py`
  - `backend/app/services/tw_stock_rank_tech_cross.py`
  - `backend/app/services/tw_stock_technical_status.py`
  - `backend/app/services/tw_stock_cross_analysis.py`
  - `backend/app/services/tw_stock_trend.py`

禁止：

- 新数据源。
- 联网或 token。
- 数据刷新、补数据或拉数据。
- 模型训练。
- provider refresh/publish。
- accepted latest switching。
- monitor 写入或扫描。
- alerts 写入。
- broker、quick-trade、orders。
- 买卖、仓位、收益、上涨概率或胜率语义。

## 3. 输出收敛规则

R9 实现时应保持：

- 默认每只股票最多 3 条主线索。
- 详情展开最多 5 条。
- `data_quality_notes` 只放用户能理解的数据缺口或时效提示。
- 不展示 raw rule id。
- 不展示 provider、gate、run id、IC、RankIC、训练指标。
- 不把 qlib score、trend score、技术指标解释成收益、胜率、上涨概率或买卖建议。

建议优先级：

1. 风险 / 冲突线索优先于支持线索。
2. 数据不足必须显式提示，不能强行解释。
3. 支持线索最多保留 1-2 条，避免堆字段。
4. 冻结规则卡只能作为 caution/review/background，不能作为自动 gate。

## 4. 字段映射表

| 字段 | 现有来源文件/API/service | 是否已有字段 | 是否只读 | 是否需要新数据源 | 用户可见位置 | 文案限制 | 缺失 fallback | R9 建议 |
|---|---|---:|---:|---:|---|---|---|---|
| `symbol` | `manual-review/explanation` query；`rank-tech-cross/latest` item.`symbol`；`frontend/src/views/tw-stock-monitor/index.vue` | 是 | 是 | 否 | API 基础字段 / 标题 | 只显示股票代号，不附加行动语义 | 缺失则 manual-review API 返回 400；前端提示选择标的 | 实现 |
| `name` | query `name`；`rank-tech-cross/latest` item.`name`；前端 `displayStockName()` | 是 | 是 | 否 | 标题 | 仅展示名称 | 缺失则只显示 symbol | 实现 |
| `asof` | query `asof`；`rank-tech-cross/latest` item.`qlib.asof`；`quant/signals/latest` payload.`asof` | 是 | 是 | 否 | 详情 / 数据提示 | 只表示资料日期，不写成最新保证 | 缺失时不展示或进入数据提示 | 实现 |
| `qlib_rank.rank` | query `rank`；`rank-tech-cross/latest` item.`rank` / item.`qlib.rank`；`quant/signals/latest` signal.`rank` | 是 | 是 | 否 | 主线索 | “研究排名靠前/靠后”，不得写成买卖结论 | 缺失则 `data_quality_notes` 加“缺少研究排名” | 实现 |
| `qlib_rank.score` | `rank-tech-cross/latest` item.`qlib.score`；`quant/signals/latest` signal.`qlib_score` | 是，但当前 manual-review query 未接 | 是 | 否 | 详情，默认不进主线索 | 只能说明“横截面研究排序分数”，不得解释为收益、胜率、上涨概率 | 缺失不影响主线索 | R9 可接入详情，不建议主线索 |
| `qlib_rank.rank_tier` | query `rankTier`；`rank-tech-cross/latest` item.`rankTier`；service `rank_tier()` | 是 | 是 | 否 | 主线索 | 只用 Top10/Top30/Top50/Top50 外层级 | 缺失时由 rank 推导；rank 也缺失则数据不足 | 实现 |
| `qlib_rank_change` | `GET /api/tw-stock/quant/signals/rank-changes`；前端已有 `loadRankChanges()` | 有只读来源，但当前 manual-review 未接 | 是 | 否 | 详情 / 数据提示 | 只能描述“排名变化需要复盘”，不得写成行动提示 | 若接口无对应 symbol 或未加载，则暂不展示 | R9 暂缓或二阶段实现；需先设计前端如何取单标的变化 |
| `trend.trend_label` | query `trendLabel`；`rank-tech-cross/latest` item.`trend.label`；`cross-analysis/latest` item.`quantdinger.trend_label`；`tw_stock_trend.py` report.`trend.label` | 是 | 是 | 否 | 主线索 | “趋势偏强/转弱/中性”，不得写成看涨承诺 | 缺失则数据提示“缺少趋势状态” | 实现 |
| `trend.trend_score` | query `trendScore`；`rank-tech-cross/latest` item.`trend.score`；`cross-analysis/latest` item.`quantdinger.trend_score` | 是 | 是 | 否 | 详情，必要时辅助主线索 | 只作为趋势强弱分，不展示为概率或胜率 | 缺失时只用 label；label 也缺失则数据不足 | 实现 |
| `trend.latest_date` | `rank-tech-cross/latest` item.`trend.latest_date`；`cross-analysis/latest` item.`quantdinger.latest_date` | 是，但当前 manual-review query 未接 | 是 | 否 | 数据提示 / 详情 | 只表示 QuantDinger 原始日线最新日 | 缺失则提示趋势日期不可确认 | R9 可接入 |
| `trend.ret_5d` / `ret_20d` / `ret_60d` | 计划文档要求；前端趋势区存在 `selectedTrendItem.returns.ret_5d`；`rank-tech-cross/latest` item 未稳定暴露这些字段 | 部分页面已有，manual-review 当前不可达 | 是 | 否，若只用已有趋势 payload | 详情，默认不进主线索 | 只能说明近期涨跌背景，不得给收益预测 | 不在当前上下文时暂缓 | R9 暂缓；先确认 `rank-tech-cross/latest` 是否应携带 returns |
| `technical.status` | `rank-tech-cross/latest` item.`technical.status`；`tw_stock_rank_tech_cross.py`；`tw_stock_technical_status.py` | 是 | 是 | 否 | 主线索 / 详情 | “技术状态偏强/中性/偏弱/数据不足”，不得写成买卖信号 | 缺失则数据提示“缺少技术状态” | 实现 |
| `technical.summary` | `rank-tech-cross/latest` item.`technical.summary` | 是 | 是 | 否 | 详情 | 只汇总支持/中性/谨慎/不足数量，不展示指标堆叠 | 缺失则不展示 | R9 可接入详情 |
| `technical.strategies[].id/state/reason` | `rank-tech-cross/latest` item.`technical.strategies`；`tw_stock_technical_status.py` MA/RSI/MACD/Bollinger items | 是 | 是 | 否 | 详情，最多 5 条 | 展示 label/state/reason；不展示 raw 指标全量；不写行动建议 | 缺失则使用 `technical.status` | R9 可接入详情 |
| `technical.MA` | `technical.strategies` item id=`ma` | 是 | 是 | 否 | 详情 | 只能说明均线关系支持/中性/谨慎 | 缺失则不展示 | R9 可接入 |
| `technical.RSI` | `technical.strategies` item id=`rsi`，metrics.`rsi14` | 是 | 是 | 否 | 详情 / 风险线索 | RSI 偏热只能作为风险复盘线索，不得写成卖出提示 | 缺失则不展示 | R9 可接入 |
| `technical.MACD` | `technical.strategies` item id=`macd` | 是 | 是 | 否 | 详情 | 只说明动能状态，不给行动语义 | 缺失则不展示 | R9 可接入 |
| `technical.Bollinger` | `technical.strategies` item id=`bollinger` | 是 | 是 | 否 | 详情 / 风险线索 | 只说明布林区间位置，不给行动语义 | 缺失则不展示 | R9 可接入 |
| `positionRisk.status` | query `positionStatus`；`rank-tech-cross/latest` item.`positionRisk.status`；`technical.positionRisk.status` | 是 | 是 | 否 | 主线索 | 只描述位置风险，如偏高/合理/回调观察 | 缺失则数据提示“缺少价格位置风险” | 实现 |
| `positionRisk.label` | `rank-tech-cross/latest` item.`positionRisk.label` | 是 | 是 | 否 | 主线索 / 详情 | 使用既有用户可读标签 | 缺失由 status 映射；仍缺失则不展示 | R9 可接入 |
| `positionRisk.reason` | `rank-tech-cross/latest` item.`positionRisk.reason` | 是 | 是 | 否 | 详情 | 仅解释风险来源，不输出处理动作 | 缺失则使用简短默认文案 | R9 可接入 |
| `positionRisk.metrics.price_percentile_120d` | query `pricePercentile120d`；`rank-tech-cross/latest` item.`positionRisk.metrics.price_percentile_120d` | 是 | 是 | 否 | 详情 / 风险线索 | “接近区间高位”这类解释，不能写成收益或概率 | 缺失则不展示 | R9 可接入 |
| `positionRisk.metrics.distance_ma20_pct` / `distance_ma60_pct` | `rank-tech-cross/latest` item.`positionRisk.metrics.*` | 是，当前 query 未接 ma 距离 | 是 | 否 | 详情 | 只说明距离均线，不给行动建议 | 缺失则不展示 | R9 可接入详情 |
| `positionRisk.metrics.rsi14` | query `rsi14`；`rank-tech-cross/latest` metrics.`rsi14` | 是 | 是 | 否 | 详情 / 风险线索 | RSI 偏热是复盘风险，不是卖出信号 | 缺失则不展示 | 实现 |
| `positionRisk.metrics.bollinger_position` | `rank-tech-cross/latest` metrics.`bollinger_position` | 是 | 是 | 否 | 详情 | 只说明靠近/越过布林位置 | 缺失则不展示 | R9 可接入详情 |
| `positionRisk.metrics.return_5d_pct` / `return_20d_pct` | query `return5dPct`；`rank-tech-cross/latest` metrics.`return_5d_pct` / `return_20d_pct` | 是 | 是 | 否 | 详情 / 风险线索 | 只表示已发生涨跌，不承诺未来收益 | 缺失则不展示 | R9 可接入 |
| `frozen_rule_cards[].rule_id` | manual-review query `frozenRules`；service `FROZEN_RULE_TEXT` | 服务内已有映射；真实前端来源暂未接 | 是 | 否 | 主线索或详情，最多 1 条 | 不展示 raw rule id；只能 caution/review/background/auxiliary；不能作为 gate | 缺失则不展示 | 暂缓真实接入；R9 仅可支持显式上下文传入 |
| `data_quality.warnings` | `rank-tech-cross/latest` payload.`warnings`、item.`trend.warnings`、item.`technical.warnings`、positionRisk.`warnings`；`cross-analysis/latest` freshness.`warnings` | 是 | 是 | 否 | 数据提示 | 翻译成用户可懂提示，不展示内部路径或 run id | 缺失则 `data_quality_notes=[]` | 实现 |
| `cross.category` / `cross.alignment` | `cross-analysis/latest` item.`cross`；`cross-analysis/symbol/<symbol>` item.`cross` | 是，但 manual-review 当前未接 | 是 | 否 | 详情 / 背景 | 只说明 qlib 与趋势是否一致，不作为行动条件 | 缺失则不展示 | R9 暂缓，避免引入第二套解释主线 |
| `decision.code` / `actionPlan.code` | `rank-tech-cross/latest` item.`decision` / `actionPlan` | 是 | 是 | 否 | 禁止直接进用户文案；最多作为内部候选信号参考 | 禁止展示 raw code；不得输出自动行动、仓位或交易语义 | 缺失不影响 manual-review | R9 暂缓；如用，只转译为复盘状态 |

## 5. R9 建议输入 contract

R9 若实现字段增强，建议后端 `TWManualReviewExplanationService.explain()` 接收统一 context：

```json
{
  "symbol": "2330",
  "name": "台积电",
  "asof": "2026-06-10",
  "qlib_rank": {
    "rank": 8,
    "score": 0.42,
    "rank_tier": "Top10",
    "rank_change": null
  },
  "trend": {
    "trend_label": "uptrend",
    "trend_score": 72,
    "latest_date": "2026-06-10",
    "ret_5d": null,
    "ret_20d": null,
    "ret_60d": null
  },
  "technical_status": {
    "technical_status": "technical_strong",
    "summary": {},
    "strategies": []
  },
  "position_risk": {
    "status": "elevated",
    "label": "强势但偏高",
    "reason": "处于近 120 日偏高区间。",
    "metrics": {}
  },
  "frozen_rule_cards": [],
  "data_quality_warnings": []
}
```

R9 不应把整个 `rank-tech-cross/latest` item 原样透传给用户；应在后端 service 内做白名单抽取。

## 6. 用户可见层级

### 主线索

只允许进入默认可见 `signals` 的字段：

- qlib rank / rank_tier。
- trend label / trend score 的简化判断。
- technical status 的简化判断。
- positionRisk status / label / reason 的简化判断。
- 1 条最重要的数据质量提示。
- 1 条冻结规则卡转译后的 caution/review/background 线索。

### 详情

允许进入展开区或详情字段：

- qlib score，但必须写明只是排序分数。
- qlib rank change，若已加载且可匹配 symbol。
- trend latest_date。
- ret5 / ret20 / ret60，若已在现有上下文可达。
- MA/RSI/MACD/Bollinger 每项状态和 reason。
- positionRisk metrics 的少量关键项。
- cross category/alignment，若 R9 后续确认不造成解释分叉。

### 数据提示

进入 `data_quality_notes`：

- 缺少研究排名。
- 缺少趋势状态。
- 缺少技术状态。
- 缺少价格位置风险。
- trend quality warnings。
- technical warnings。
- position risk warnings。
- qlib 与 raw trend 日期差异提示。

### 暂缓

暂缓字段：

- qlib rank change：已有只读 API，但 manual-review 当前没有单标的映射链路。
- ret5/ret20/ret60：计划要求存在，但当前 manual-review/rank-tech item 未稳定暴露完整 returns。
- cross category/alignment：已有只读来源，但容易与 manual-review 主线重复，建议等 R9 基础映射稳定后再接。
- 冻结法人/融资融券规则卡真实来源：服务已有 rule id 转译，但前端当前没有真实规则卡上下文来源。
- decision/actionPlan raw code：只可内部参考，不建议直接映射。

## 7. 禁止进入用户可见文案的字段

禁止直接展示：

- raw rule id。
- provider。
- accepted latest。
- gate。
- run id。
- recorder id。
- IC、RankIC、训练指标。
- target horizon。
- target position。
- target weight。
- order、broker、quick-trade。
- expected return、win rate、upside probability。
- decision/actionPlan raw code。

这些词可以出现在开发文档的安全边界说明中，但不应进入普通用户可见 manual-review 面板。

## 8. Fallback 规则

R9 建议按以下顺序降级：

1. 有 rank + trend + technical + positionRisk：输出最多 3 条主线索，状态可为 `multi_source_support`、`manual_review`、`caution` 或 `conflict`。
2. 有 rank + trend，但无 technical/positionRisk：输出排名和趋势线索，同时加入数据提示。
3. 只有 rank：输出研究排名背景，`overall_status` 倾向 `data_insufficient` 或 `manual_review`，必须提示缺少趋势/技术/位置。
4. 无 rank：`overall_status=data_insufficient`，只输出数据质量线索。
5. 冻结规则卡存在但核心字段不足：规则卡只能作为背景或谨慎提示，不能单独把状态升级为支持。

## 9. R9 实现建议

建议 R9 最小实现顺序：

1. 后端 service 扩展白名单字段解析：qlib score、trend latest_date、technical summary/strategies、positionRisk label/reason/metrics、data_quality_warnings。
2. 后端测试覆盖字段增强但不增加信号数量上限。
3. 前端 `buildManualReviewParams()` 从当前页面已有 `rankTechSelectedRow` 或当前选中 row 中传入白名单字段。
4. 前端仍展示最多 3 条主线索；详情最多 5 条。
5. Playwright readonly smoke 复跑，确认 manual-review GET 仍是唯一台股业务请求。

R9 不建议同时接：

- rank change。
- cross category/alignment。
- 冻结规则卡真实来源。

这些可以等基础字段增强通过后再做小阶段。

## 10. R8 Gate 建议

建议进入：

`request_phaser9_context_mapping_implementation`

