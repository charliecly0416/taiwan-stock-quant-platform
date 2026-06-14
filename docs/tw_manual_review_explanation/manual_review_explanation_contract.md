# Manual Review Explanation Contract

## 1. 模块定位

`manual_review_explanation` 是台股只读人工复盘解释模块。它把已有只读研究信息整理成用户能理解的复盘线索，帮助用户判断下一步人工检查重点。

它不是模型训练、不是自动 gate、不是交易建议、不是买卖信号、不是仓位建议。

用户第一性原则：简单、准确、清晰、实用。

## 2. 输入来源清单

允许进入 contract 的输入类型：

| 输入组 | 用途 | R1 边界 |
|---|---|---|
| qlib rank / score / rank tier | 解释是否仍在研究池、排名层级、排名变化 | 只读接入；不得解释为收益预测 |
| QuantDinger trend | 解释趋势偏强/偏弱、量能是否配合 | 只读接入；不得解释为看涨承诺 |
| 技术状态 | 解释技术支持、中性、转弱或冲突 | 只读接入；避免指标堆叠 |
| 价格位置风险 | 解释位置偏高、短期过热、回调位置等复盘风险 | 只读接入；不得变成卖出提示 |
| 冻结的法人/融资融券规则卡 | 仅作为人工 caution/review/background/auxiliary 线索 | 不得升级为自动 gate 或 confirmed watch |
| 数据不足状态 | 显式提示缺失或过期，避免强行解释 | 只输出用户可懂原因 |

禁止输入：

- fundamental 月营收/基本面。
- 单期 TWSE current file。
- FinMind `date/create_time` proxy。
- 新外部数据源。
- token 或联网来源。
- 任何买卖、仓位、收益、概率字段。

## 3. 输出 JSON Schema

```json
{
  "symbol": "2330",
  "name": "台积电",
  "asof": "2026-06-10",
  "overall_status": "manual_review",
  "status_label": "需要人工复盘",
  "confidence": "medium",
  "summary": "模型研究排名仍靠前，但价格位置偏高且部分线索提示谨慎，适合人工复盘。",
  "signals": [
    {
      "type": "support",
      "label": "研究排名靠前",
      "message": "位于 Top30，仍属于主要研究池。",
      "source": "qlib_rank",
      "severity": "info"
    }
  ],
  "next_review_focus": [
    "确认趋势是否继续守住 MA20。",
    "观察价格位置是否仍偏高。"
  ],
  "research_only": true,
  "not_trading_advice": true,
  "data_quality_notes": []
}
```

字段约束：

| 字段 | 类型 | 要求 |
|---|---|---|
| `symbol` | string | 股票代号 |
| `name` | string/null | 股票名称，缺失时可为空 |
| `asof` | string | 资料日期 |
| `overall_status` | enum | 只能使用允许值 |
| `status_label` | string | 用户可读短标签 |
| `confidence` | enum | `low` / `medium` / `high`，只表示解释完整度，不表示胜率 |
| `summary` | string | 一句话摘要，不超过一个复合判断 |
| `signals` | array | 3 到 5 条关键线索；数据不足时可更少 |
| `next_review_focus` | array | 1 到 3 条人工复盘关注点 |
| `research_only` | boolean | 必须为 true |
| `not_trading_advice` | boolean | 必须为 true |
| `data_quality_notes` | array | 数据缺失、过期、不可解释原因 |

## 4. `overall_status` 允许值

| 值 | 用户标签建议 | 含义 |
|---|---|---|
| `multi_source_support` | 多源支持，仍需人工复盘 | 多类只读线索方向一致 |
| `manual_review` | 需要人工复盘 | 有支持线索，也有需要确认的问题 |
| `caution` | 谨慎观察 | 风险线索较突出 |
| `conflict` | 信息冲突 | 排名、趋势、技术或风险信息不一致 |
| `data_insufficient` | 数据不足 | 关键输入缺失或过期 |

## 5. `signals` 允许值

`signals.type` 只能是：

- `support`
- `risk`
- `conflict`
- `background`
- `data_quality`

`signals.severity` 只能是：

- `info`
- `watch`
- `caution`
- `review`

`signals.source` 建议只使用用户可理解或可审计的来源名：

- `qlib_rank`
- `trend`
- `technical_status`
- `position_risk`
- `frozen_rule_card`
- `data_quality`

不得在用户可见文案中展示 raw rule id、复杂 run id、gate、provider 或 accepted latest。

## 6. 允许文案示例

- “研究排名靠前，仍属于主要研究池。”
- “趋势偏强，但价格位置偏高，适合人工复盘。”
- “技术状态与研究排名存在分歧，需要确认趋势是否延续。”
- “融资拥挤只作为谨慎线索，不作为自动判断。”
- “部分数据不足，本次解释只保留可确认线索。”

## 7. 禁止文案示例

- “建议买入。”
- “建议卖出。”
- “建议持有。”
- “强烈看涨。”
- “上涨概率为 70%。”
- “预计收益 10%。”
- “目标仓位 20%。”
- “已满足下单条件。”
- “自动过滤通过。”

## 8. 安全边界

R0/R1 必须保持只读研究边界：

- 不训练模型。
- 不新增数据源。
- 不联网或使用 token，除非未来阶段另行授权。
- 不写 provider。
- 不 refresh/publish。
- 不切 accepted latest。
- 不写 monitor config。
- 不触发 monitor scan。
- 不写 alerts。
- 不接 broker、quick-trade、orders。
- 不输出 target position 或 target weight。
- 不输出收益承诺或上涨概率承诺。

冻结规则卡只能作为人工解释线索，不能作为自动 gate、confirmed watch、风险过滤或模型训练标签。

## 9. 数据不足处理

当关键输入不足时：

- `overall_status=data_insufficient`。
- `status_label=数据不足`。
- `summary` 明确说明哪些信息缺失。
- `signals` 至少包含一条 `type=data_quality` 的线索。
- `next_review_focus` 建议用户补看趋势、技术或筹码数据，但不建议任何交易动作。

示例：

```json
{
  "overall_status": "data_insufficient",
  "status_label": "数据不足",
  "summary": "当前缺少趋势和技术状态，只能展示研究排名，暂不形成完整复盘线索。",
  "signals": [
    {
      "type": "data_quality",
      "label": "趋势资料不足",
      "message": "缺少趋势与技术状态，本次不强行判断。",
      "source": "data_quality",
      "severity": "review"
    }
  ]
}
```

## 10. R1 服务实现边界

R1 只能实现后端只读服务，且必须另经审查者授权。R1 不得自动接 API 或前端。

R1 允许做：

- 从既有只读本地上下文或既有服务读取字段。
- 根据本 contract 组装解释 JSON。
- 做字段枚举校验和禁止语义校验。
- 增加单元测试，验证无交易语义。

R1 禁止做：

- 新数据源。
- 联网或 token。
- 训练模型。
- 写 provider。
- refresh/publish。
- accepted latest switching。
- API、前端、monitor、broker、orders。
- 把解释规则升级为自动 gate。
