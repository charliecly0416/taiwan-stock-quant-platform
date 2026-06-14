# LTR 主线 Phase2B 后续路线说明

生成日期：2026-06-13

## 1. 当前主线状态

当前主路线仍然可以定义为：

```text
qlib baseline
-> Phase1C qlib-preserving LTR rerank
-> Phase3 turnover / portfolio replay
```

但需要明确：`regime-aware gating` 目前不能作为已验证通过的主线环节。

Phase1C 已经通过的是排序层：

- 胜出方案是保守的 `qlib-preserving top50-only rerank`。
- 它不是全市场自由重排。
- 它保留 qlib Top50 集合，只在头部内部做有限重排。
- Phase1C gate 条件通过：
  - rank IC 高于 qlib；
  - NDCG@30 不低于 qlib；
  - Top30 future excess rank 不低于 qlib；
  - 不是只靠单一年份成立。

因此，Phase1C 可以作为当前 LTR 主线的有效成果。

## 2. 为什么 Phase2B 不被放行

Phase2B 不放行，不是因为 Phase1C 失败，而是因为 Phase2B 要验证的是另一个问题：

```text
在 normal / caution / risk_off 不同市场状态下，
regime gate 是否能提供稳定、可解释、非 no-op 的增量过滤效果，
且不降低 Phase1C 的核心 TopK 质量。
```

Phase2B 的总体指标看起来略好：

```text
Phase1C ndcg@30              = 0.541729
Phase2B selected ndcg@30     = 0.542685

Phase1C top30 future rank    = 0.527890
Phase2B selected top30 rank  = 0.528888
```

但它没有通过放行门槛，原因是增量效果集中在单一状态：

```text
caution:
  date_count = 52
  top30_changed_ratio = 0.0891
  gated_top30_median_qlib_rank: 17 -> 16
  top30_future_excess_delta = +0.0040

risk_off:
  date_count = 15
  top30_changed_ratio = 0.0
  gated_top30_median_qlib_rank: 17 -> 17
  top30_future_excess_delta = 0.0
```

也就是说：

- selected gate 是非 no-op；
- validation selection 没有用 independent_test 反选；
- 总体 TopK 没有被破坏；
- 但它只在 `caution` 下产生轻微效果；
- 在最需要风险控制的 `risk_off` 下没有实际过滤；
- `not_single_regime_only = false`。

所以 Phase2B 的停止结论是合理的。它说明：

```text
Phase1C LTR rerank 成立；
Phase2B regime-aware gating 尚未成立。
```

这两个结论不矛盾。

## 3. 对用户第一性原则的判断

用户第一性原则是：简单、准确、清晰、实用。

按这个原则，不能把 Phase2B 包装成“市场状态风控已经验证成功”，因为这会误导用户认为系统在 risk_off 状态下已经能有效规避风险。

当前更清晰的表达应该是：

- Phase1C 是当前已验证排序增强；
- regime 只能作为观察/解释字段；
- 不应作为正式 gate 控制层进入前端主推荐；
- 若进入组合回放，必须明确“不依赖已验证 regime gate”。

## 4. 后续可以尝试的路线

### 路线 A：严格收尾 Phase2

含义：

- 接受 Phase2/Phase2B 证据不足；
- 保留 Phase1C 作为当前 LTR 主线成果；
- 暂停 regime-aware gating；
- 不进入 Phase3。

适合目标：

- 希望研究证据最严格；
- 不接受任何 gate 放宽；
- 暂时不做组合层闭环。

缺点：

- 主线停在排序层，无法验证换手、交易成本和组合收益。

### 路线 B：绕过未验证 regime，进入 Phase3

含义：

- 用户明确接受 Phase2B 没有证明 regime gate；
- Phase3 只基于 Phase1C rerank + baseline rule 做 turnover / portfolio replay；
- regime 字段只作为只读诊断字段；
- 不得声称 regime-aware gating 已通过。

适合目标：

- 继续完成实用闭环；
- 验证 Phase1C 排序增强是否能在组合层产生实际价值；
- 重点关注换手、交易成本、动作次数、净值、回撤。

这是当前最推荐路线。

原因：

- Phase1C 已经有排序层证据；
- 用户真正关心的是最终组合层是否更实用；
- Phase2B 失败的是 regime gate，不应阻塞 Phase1C 去做组合层回放；
- 但必须在文档和验收里清楚标注 regime 未通过。

### 路线 C：做一次 risk_off-only 最终诊断

含义：

- 不进入 Phase3；
- 不扩大模型搜索；
- 不引入新数据；
- 只检查为什么 risk_off 下没有过滤效果。

适合目标：

- 想把 Phase2B 失败原因解释得更完整；
- 判断是样本数太少、状态定义太弱、还是 Phase1C 本身已经足够保守。

限制：

- 只能做诊断，不能继续无限调参；
- 若仍无证据，应正式关闭 regime gate。

### 路线 D：引入正交数据后再重启 regime

含义：

- 暂不继续当前 regime gate；
- 等法人筹码、融资融券、月营收公告日等 PIT-safe 数据进入后，再重新评估 regime / risk gate。

适合目标：

- 认为当前 OHLCV / qlib 派生信息不足；
- 希望用更正交的信息判断风险环境。

限制：

- 这是新数据主线，不应混入当前 Phase2B 放行判断。

## 5. 推荐决策

建议选择路线 B：

```text
用户显式确认：
Phase2B regime gate 未通过；
但允许以 Phase1C qlib-preserving LTR rerank 为排序输入进入 Phase3；
Phase3 只验证组合层 turnover / replay；
regime 字段只能作为诊断解释，不作为已验证 gate。
```

这样既不浪费 Phase1C 已通过的成果，也不把 Phase2B 的弱证据包装成成功。

## 6. 给执行者的下一步边界

若用户选择路线 B，执行者下一步应只做：

- 冻结 Phase1C rerank score；
- 使用 Phase1C rerank 与现有 baseline rule 做组合回放；
- 计算净值、换手、交易成本、动作次数、最大回撤、年度/状态分段；
- regime 只作为分组分析字段；
- 不把 regime gate 作为交易过滤前提；
- 不改前端主推荐；
- 不写 provider；
- 不触发 accepted latest switching；
- 不触碰 broker、orders、quick-trade、target position。

## 7. 给审查者的验收重点

审查者应重点确认：

- 执行者没有声称 Phase2B 通过；
- Phase3 没有依赖未验证的 regime gate；
- Phase1C score 没有被重新调参；
- 组合回放没有把 rank / NDCG 误写成收益承诺；
- 结果同时报告收益、成本、换手、动作次数、回撤和分段表现；
- 若组合层不优于 baseline，应停止而不是继续强推。

