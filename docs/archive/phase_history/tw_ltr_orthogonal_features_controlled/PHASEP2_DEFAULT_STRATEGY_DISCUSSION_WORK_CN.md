# Phase P2 工作文档：Default Strategy Discussion

生成日期：2026-06-15

依据：

```text
docs/tw_ltr_orthogonal_features_controlled/PHASEP1_O4_VS_REPAIRED_FRESH_QLIB_SAME_WINDOW_REVIEW_CN.md
docs/tw_ltr_orthogonal_features_controlled/PHASEP1_O4_VS_REPAIRED_FRESH_QLIB_SAME_WINDOW_EXECUTION_REPORT_CN.md
```

## 1. P2 目标

P2 只做默认策略讨论，不改默认策略。

目标：

```text
基于 repaired fresh qlib vs O4 orthogonal LTR 的同窗口证据，
形成默认策略是否继续保持 fresh qlib 的讨论记录。
```

目标 gate：

```text
phase_p2_default_strategy_discussion_recorded
```

## 2. 固定证据

P2 必须只使用 P1 冻结证据：

```text
window = 2025-07-01..2026-05-07
fee_rate = 0.001425
tax_rate = 0.003
target_position_count = 10
next-day execution
```

主结果：

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

## 3. 必须回答的问题

P2 报告必须回答：

```text
1. 当前默认策略是否应继续保持 repaired fresh qlib / rank_rotate_top50_adaptive_score？
2. O4 orthogonal LTR 是否有足够理由替代默认？
3. 如果不替代，O4 在产品中应扮演什么角色？
4. 是否需要把 O4 展示为低回撤/低换手研究候选？
5. repaired fresh qlib 的回撤更深是否需要风险提示？
6. 两者收益差异很小，是否需要更多窗口或用户确认？
7. 是否允许任何默认策略变更？
```

## 4. 决策边界

P2 默认建议应倾向保守：

```text
默认策略继续保持 repaired fresh qlib；
O4 orthogonal LTR 作为只读研究候选 / 风险较稳替代观察；
不直接切换默认。
```

只有在用户明确确认后，才允许后续另开默认策略变更工作文档。

P2 不得自行切换：

```text
frontend default strategy
API default method
accepted latest
provider artifact
monitor config
```

## 5. 禁止事项

P2 禁止：

```text
训练 qlib；
训练 LTR；
调参；
新增实验；
改前端/API/backend；
provider refresh / publish；
accepted latest switching；
monitor scan/config/alerts；
broker/orders/quick-trade；
target position / target weight；
输出真实买卖建议；
承诺收益、胜率或上涨概率。
```

## 6. 输出要求

执行者必须写：

```text
docs/tw_ltr_orthogonal_features_controlled/PHASEP2_DEFAULT_STRATEGY_DISCUSSION_EXECUTION_REPORT_CN.md
```

报告必须包含：

```text
最终建议；
保留 fresh qlib 或讨论切换的理由；
O4 的产品角色；
风险提示；
是否需要用户确认；
明确说明没有执行默认策略变更；
下一步建议。
```

P2 结束后，如需实际默认策略变更，必须另开工作文档并等待用户确认。
