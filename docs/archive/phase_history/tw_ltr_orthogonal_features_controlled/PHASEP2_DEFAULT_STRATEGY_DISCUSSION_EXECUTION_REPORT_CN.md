# Phase P2 执行报告：Default Strategy Discussion

生成日期：2026-06-15

## 1. 讨论范围

本轮只做默认策略讨论，不改默认策略、不改前端/API/backend、不触发 provider / accepted latest / monitor / broker / orders / quick-trade。

使用的冻结证据仅来自 P1：

```text
window = 2025-07-01..2026-05-07
fee_rate = 0.001425
tax_rate = 0.003
target_position_count = 10
next-day execution
```

## 2. 冻结结论

同窗口只读对比结果：

```text
repaired fresh qlib return = 0.801662
O4 orthogonal LTR return = 0.800329
O4 - fresh return diff = -0.001333

repaired fresh qlib max_drawdown = -0.085205
O4 max_drawdown = -0.074962

repaired fresh qlib action_count = 410
O4 action_count = 403

repaired fresh qlib turnover_proxy = 40.750969
O4 turnover_proxy = 39.761877
```

## 3. 最终建议

默认策略继续保持 `repaired fresh qlib / rank_rotate_top50_adaptive_score`。

理由很简单：repaired fresh qlib 在同窗口收益略高，且当前没有足够证据证明 O4 可以稳定替代默认；O4 虽然回撤更浅、动作更少、换手更低，但并没有在收益上超出 repaired fresh。

## 4. 回答问题

1. 当前默认策略是否应继续保持 repaired fresh qlib / rank_rotate_top50_adaptive_score？

应继续保持。

2. O4 orthogonal LTR 是否有足够理由替代默认？

没有。O4 的收益略低于 repaired fresh，不能直接替代默认。

3. 如果不替代，O4 在产品中应扮演什么角色？

O4 应继续作为只读研究候选 / 对照候选，供人工复盘和风险观察。

4. 是否需要把 O4 展示为低回撤/低换手研究候选？

需要。O4 的回撤更浅、动作更少、换手更低，适合保留为保守观察候选。

5. repaired fresh qlib 的回撤更深是否需要风险提示？

需要。虽然 repaired fresh 收益略高，但回撤更深，应明确提示风险。

6. 两者收益差异很小，是否需要更多窗口或用户确认？

需要更多窗口再看；若要做默认策略变更，必须由用户确认后另开变更工作文档。

7. 是否允许任何默认策略变更？

本轮不允许，也没有执行任何默认策略变更。

## 5. O4 的产品角色

O4 orthogonal LTR 的产品角色保持为：

- 只读研究候选；
- 风险较稳观察候选；
- 与 repaired fresh qlib 并列展示用于对照，不作为默认。

## 6. 风险提示

- repaired fresh qlib 回撤更深，必须保留风险提示。
- O4 虽然更稳一些，但收益略低，不能写成更优默认。
- 这两个结果都只是同窗口历史只读回放，不构成收益承诺、胜率承诺或上涨概率承诺。

## 7. 是否需要用户确认

当前不需要用户确认来维持现状，因为默认策略没有变更。

如果后续要把默认策略从 repaired fresh qlib 切换到 O4，必须先获得用户明确确认，并另开工作文档。

## 8. 是否执行了默认策略变更

没有。

## 9. 下一步建议

继续保持默认策略为 `repaired fresh qlib / rank_rotate_top50_adaptive_score`，同时把 O4 作为保守研究候选保留在只读产品中；若后续要讨论默认切换，先做更长窗口证据收集，再进入单独的变更流程。

## 10. Gate

```text
phase_p2_default_strategy_discussion_recorded
```
