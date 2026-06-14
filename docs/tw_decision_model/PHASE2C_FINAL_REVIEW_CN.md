# Decision Model Phase 2C 最终审查与方向判断

审查日期：2026-06-10

## 1. 最终结论

本轮 Entry Model v1 不建议继续。

经过 Phase 2、Phase 2B、Phase 2C 三轮执行与审查后，候选模型没有稳定超过当前 `baseline_qlib_rank`。Phase 2C 已按固定候选、固定基线、固定区间、固定 gate 做最后确认，结论为：

- `pass_phase3_gate=false`
- `archive_entry_model_v1_failed=true`
- 不进入 Phase 3
- 不继续 Phase 2D

这不等于“所有 Decision Model 方向都没有价值”，但已经证明当前 Entry Model v1 的定义、特征组合与训练方式不足以成为项目主线策略或前端产品功能。

## 2. 主要证据

Phase 2 初训发现：

- 原 ensemble 在 `main/test`、`main/forward`、`sensitivity/test` 均弱于 qlib rank。
- 只有 `sensitivity/forward` 有改善，不能作为放行依据。
- binary 模型在多个区间 RankIC/AUC 偏弱。
- regression 有局部信号，但不稳定。

Phase 2B 诊断发现：

- 修复 ensemble calibration 后，`ensemble_fixed_trainval` 和 `ensemble_fixed_same_asof` 仍未稳定通过。
- regression 在 `main/test` 与 `main/forward` 略有正向信号，但在 `sensitivity/test` 出现 top5/top10 负 delta。
- binary 模型不适合当前排序任务。
- feature group ablation 显示 `qlib + technical` 是最接近可用的方向，但仍不足以过 gate。

Phase 2C 最终确认：

| 候选 | main/test | main/forward | sensitivity/test | sensitivity/forward | 结论 |
|---|---|---|---|---|---|
| qlib + technical / ensemble_fixed_trainval | 部分通过 | 失败 | 失败 | 失败 | 不通过 |
| qlib + technical / regression | 失败 | 失败 | 通过 | 失败 | 不通过 |

失败不是单个指标的小波动，而是同一候选无法同时满足四个区间的 top5/top10、RankIC、NDCG@10、precision@5 稳定性要求。

## 3. 问题分析

### 3.1 当前模型没有学到稳定增量

qlib rank 本身已经是强基线。Entry Model v1 试图用 qlib score、技术指标、流动性、大盘连续特征做二次排序，但结果显示新增特征没有形成跨年份、跨市场阶段都稳定的增量。

局部提升更像市场阶段适配，而不是可泛化能力。

### 3.2 binary label 与排序目标不匹配

binary 模型的目标是判断是否达到动态正样本，但用户真正需要的是“今天候选里谁更值得优先研究”。这是排序问题，不是简单二分类问题。

Phase 2B 的 binary diagnostics 显示：

- main forward RankIC 明显为负。
- validation/forward 校准偏弱。
- best iteration 很早停止，说明二分类目标没有给模型提供足够稳定的可学习结构。

因此 binary 分支不应继续作为主线。

### 3.3 ensemble 不是自然增强，反而可能稀释信号

原始 ensemble 使用 split-part minmax，评估口径不够上线一致。Phase 2B 修复后仍失败，说明问题不只是校准方式。

binary 信号偏弱时，简单等权 ensemble 会把 regression 的少量有效信号稀释掉。当前不应继续用 binary + regression 的简单融合当主模型。

### 3.4 特征可能更适合做风险解释，而不是直接重排

技术指标、流动性、大盘状态在部分区间有用，但并没有稳定提高 top5/top10 收益排序。这说明它们可能更适合做：

- 风险标注
- 不确定性提示
- 排名结果解释
- 人工复盘优先级

而不是直接替代 qlib rank 做买入候选重排。

### 3.5 数据覆盖仍有结构性限制

当前样本缺 2024，训练/验证/测试分布不连续。虽然这不构成泄漏，也不影响本轮 gate 的合法性，但它会放大阶段性市场差异。

此外，FinMind 财务、月营收、估值、法人、融资融券等 point-in-time 特征因 `available_at` 不足被暂缓，没有进入 v1。当前模型主要依赖 qlib、OHLCV 派生技术、流动性 proxy、大盘 proxy，信息增量有限。

## 4. 是否已经证明没有效果

准确说法是：

当前 Entry Model v1 已证明“不足以稳定超过 qlib rank”，应归档失败。

不能说：

- Decision Model 总方向无效。
- 技术指标和大盘信息无效。
- 所有 meta model 都没有价值。

能说：

- 当前问题定义下，直接训练 Entry Model 去 rerank 候选，不适合进入 Phase 3。
- 当前 best candidate 只是局部有效，不满足产品化所需的稳定性。
- 继续 Phase 2D 搜索会有过拟合风险，不符合用户第一性原则。

## 5. 可复用资产

本轮不是白做。以下资产可以保留：

- Phase 0 数据审计框架。
- Phase 1 point-in-time 样本构建与 leakage audit。
- qlib score/rank/date percentile/date z-score 特征。
- 技术、流动性、大盘连续特征。
- gate delta、feature group ablation、失败归因模板。
- `qlib + technical` 是后续若重启时最值得优先检查的候选方向。

这些资产可以作为下一轮研究的基础，但不应直接接入前端或模拟账户。

## 6. 后续优化方向

### 方案 A：接受 qlib rank 主线，停止 Entry Model v1

这是默认建议。

做法：

- 保留现有 Top30/Top50/自适应 score/风控/连续转弱复盘策略。
- Entry Model v1 只作为研究归档，不进入产品。
- 后续前端仍以简单、清晰的组合策略和历史回放为主。

优点：

- 稳妥。
- 不制造虚假智能感。
- 避免把不稳定模型包装成用户建议。

### 方案 B：重启为“风险过滤模型”，不是“重排模型”

如果继续研究，建议改问题定义：

- 输入仍使用 qlib rank、技术、流动性、大盘。
- 输出不是重新排序所有股票。
- 输出改为对 qlib TopN 做风险标注，例如“正常观察 / 谨慎观察 / 暂缓观察 / 风险复盘”。

原因：

- 当前结果显示附加特征不稳定提升 top 排序。
- 但这些特征可能能识别追高、流动性、市场拖累、技术转弱风险。
- 这更符合小白用户需要：不要替用户制造复杂排序，而是告诉他“为什么这只虽然排名高但要谨慎”。

这条路需要重新写 Phase 0 级设计，不能作为 Phase 2D 延续。

### 方案 C：重启为“Exit / 持仓风险模型”

Entry 选股比 Exit 风险识别更难。对于模拟账户，用户更关心：

- 已持有标的是否明显转弱。
- 是否跌出 Top50 后需要复盘。
- 技术转弱是否只是短期波动。
- 是否需要减少研究优先级。

可以把模型目标改成预测未来 3 到 10 日的回撤风险、排名恶化风险、波动扩张风险。这个方向可能比 Entry rerank 更符合现有产品。

同样需要新设计，不得直接接 Phase 3。

### 方案 D：补齐 point-in-time FinMind 后再重启

如果要追求真正的信息增量，可以先补：

- 法人买卖超
- 融资融券
- 月营收
- 财报指标
- 估值指标

前提是必须有 `announcement_date` / `available_at`，否则会出现未来函数。

这条路工程成本较高，不建议作为短期默认方案。

## 7. 对用户第一性原则的判断

继续把当前 Entry Model v1 做成前端功能，不符合用户第一性原则。

原因：

- 不够准确：没有稳定超过 qlib rank。
- 不够清晰：用户会误以为“AI 二次排序更聪明”，但证据不支持。
- 不够实用：局部提升无法指导真实复盘流程。
- 不够简单：引入新模型会增加解释成本。

当前最符合用户第一性原则的做法是：

1. 归档 Entry Model v1。
2. 保留 qlib rank 与现有组合策略作为主线。
3. 后续如重启，优先做“风险过滤/持仓风险解释”，而不是继续追求全候选 rerank。

## 8. 最终建议

本轮 Phase 可以收尾。

建议不要继续 Phase 2D，也不要进入 Phase 3。若后续继续 Decision Model，应该由用户明确选择新研究方向，并从新的 Phase 0 设计开始。

