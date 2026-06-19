# Phase3B 审查意见与 Phase3C 只读解释 Payload 工作文档

生成时间：2026-06-14

主线依据：`docs/TW_STOCK_LTR_RERANK_REGIME_AND_TURNOVER_PLAN_CN.md`

审查入口：`docs/tw_ltr_rerank_regime_turnover/PHASE3B_READONLY_EXPLANATION_EXECUTION_REPORT_CN.md`

---

## 1. 审查结论

Phase3B 通过。

执行者按要求把 Phase3A2C 的同口径回放结果收敛成了只读解释字段草案，没有进入前端、API、backend service、monitor、database、provider 或任何交易相关模块，也没有把方法包装成未来收益判断。

通过点：

- 解释字段范围收敛，符合“简单、准确、清晰、实用”；
- `research_role` 分层清楚；
- `relative_to_top50_adaptive` 只描述历史回放差异；
- `why_no_action` 围绕预算、持有期、数据质量和候选差距；
- `readonly_disclaimer` 明确不是交易建议、不是订单、不是配置比例；
- Schema 文档与执行报告都保持只读边界。

本轮可以结束 explanation scope 设计，进入下一步“只读 explanation payload 物化”。

---

## 2. 是否偏离主线或新增分支

未发现偏离主线或新增分支。

本轮没有：

- 新模型；
- 新数据源；
- 联网；
- provider refresh / publish；
- accepted latest switching；
- 前端/API 接入；
- 真实交易或目标仓位语义。

这仍然属于 Stage 5 的准备工作，而不是产品化接入。

---

## 3. 低风险改进点

### L1：示例数值仍偏原始，不适合直接用户化

当前 schema 示例里出现：

```text
40.018220
15.963677
-0.402422
```

作为离线 schema 草案可以接受，但进入任何产品层前必须转换成明确的人类可读表述，例如：

- “历史回放费用后净值变化约为 +40.02”
- 或“历史回放费用后净值约增加 40.02 倍/4001.82%”

但必须固定一种语义，不得让用户误读。

这不是阻塞 Phase3B 通过的问题，但 Phase3C 必须处理。

### L2：示例文案不能滑向“收益高所以更好”

Schema 里对 `phase1c_ltr_simple_daily` 的示例已经比较克制，但进入 payload 物化时，必须把“历史回放收益高但换手也高”的 tradeoff 一并写清楚，不能只保留高收益信息。

---

## 4. 安全边界审查

安全边界通过。

本轮文档未发现：

- broker / quick-trade / order / target position / target weight；
- monitor config save / scan / alerts write；
- provider refresh / publish；
- accepted latest switching；
- 自动交易；
- 上涨概率、胜率、预期收益承诺。

文案扫描结果显示禁止词未实际出现在 schema 或执行报告中，命中的仅是审查规则自身。

---

## 5. Phase3C 本轮唯一目标

只做一件事：

```text
把 Phase3B 的解释字段草案，
物化成一份固定结构的只读 explanation payload artifact，
供后续前端/API 接入审查使用。
```

注意：

- 本轮不是前端实现；
- 本轮不是 API 接入；
- 本轮不是页面联调；
- 本轮不是推荐层；
- 本轮不是策略再评估。

---

## 6. 允许改动范围

允许新增：

- `data_tw/experiments/ltr_rerank_regime_turnover/phase3c_readonly_explanation_payload/`
- `docs/tw_ltr_rerank_regime_turnover/PHASE3C_READONLY_PAYLOAD_EXECUTION_REPORT_CN.md`

允许新增的 artifact 类型：

- JSON payload
- CSV mapping
- Markdown contract 说明

允许只读读取：

- Phase3A2C 产物
- `PHASE3B_READONLY_EXPLANATION_SCHEMA_CN.md`
- `PHASE3B_READONLY_EXPLANATION_EXECUTION_REPORT_CN.md`

默认不允许修改：

- frontend；
- backend API；
- backend service；
- monitor；
- database；
- provider；
- accepted latest；
- Phase1C 模型；
- replay 脚本；
- 任何交易相关模块。

---

## 7. Payload 必须满足的结构

执行者必须生成一份固定 schema 的只读 payload，建议至少包含：

```text
as_of_scope
data_quality
methods[]
summary_notes[]
readonly_disclaimer
```

其中 `methods[]` 每项至少包含：

```text
method_key
method_label
research_role
net_return_summary
drawdown_summary
action_count_summary
turnover_summary
relative_to_top50_adaptive
why_more_aggressive
why_more_conservative
why_no_action
data_quality_note
readonly_disclaimer
```

要求：

- 所有字段都来自 Phase3A2C 产物或固定离线映射；
- 不得在 payload 里重新计算模型分数；
- 不得把 score 当作收益率、概率或仓位；
- `summary_notes[]` 只能总结 tradeoff，不得下判断。

---

## 8. 文案规范

Phase3C 必须把数值文案规范化：

1. return 表述必须固定成一种人类可读格式；
2. 回撤表述必须显式写“历史回放最大回撤”；
3. action 表述必须显式写“历史回放动作次数”；
4. turnover 表述必须显式写“历史回放 notional turnover proxy”；
5. 所有 `relative_to_top50_adaptive` 文案必须同时保留收益与换手/动作/回撤中的至少一个 tradeoff。

禁止文案继续沿用生硬原始浮点数而没有任何语义包装。

---

## 9. 禁止事项

本轮禁止：

- 接前端；
- 接 API；
- 生成页面文案最终稿；
- 引入新数据源；
- 联网；
- provider refresh / publish；
- accepted latest switching；
- 重新训练 LTR；
- 重新回放；
- 输出买入/卖出/仓位/目标权重/收益承诺/胜率/上涨概率。

---

## 10. 必做验证

执行者必须验证：

1. payload 全字段可追溯到 Phase3A2C 产物；
2. 无新数据源；
3. 无联网；
4. 无 frontend / API / backend service 修改；
5. 禁止语义扫描通过；
6. `readonly_disclaimer` 固定存在；
7. 所有方法都保留 tradeoff 信息，不允许只写收益。

---

## 11. 验收门槛

Phase3C 通过的最低门槛：

1. 交付固定结构的只读 explanation payload artifact；
2. 字段来源可追溯；
3. 文案比 Phase3B schema 更用户化，但仍保持研究语义；
4. 不出现未来收益判断；
5. 不进入前端/API；
6. 不越过 readonly / research-only 边界。

如果执行者希望直接把 payload 接入页面或 API，必须停止并回到审查者重新写下一轮文档。

---

## 12. 执行报告要求

执行者下一轮报告固定写入：

```text
docs/tw_ltr_rerank_regime_turnover/PHASE3C_READONLY_PAYLOAD_EXECUTION_REPORT_CN.md
```

报告必须包含：

1. 本轮目标；
2. 输入产物清单；
3. payload 路径；
4. payload schema；
5. 每个方法的示例 payload；
6. 文案规范化方式；
7. 禁止语义自查结果；
8. 安全边界声明；
9. 是否需要进入下一轮前端/API 只读接入审查。
