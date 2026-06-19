# Phase P0 工作文档：Orthogonal LTR Readonly Productization Design

生成日期：2026-06-15

依据：

```text
docs/tw_ltr_orthogonal_features_controlled/PHASEO6_REVIEW_CN.md
docs/tw_ltr_orthogonal_features_controlled/PHASEO6_ORTHOGONAL_LTR_DECISION_EXECUTION_REPORT_CN.md
```

## 1. P0 目标

P0 只做产品化设计文档，不改产品代码。

目标：

```text
设计如何在只读研究界面中展示 O4 orthogonal LTR，
使其替代原 simple LTR 的 LTR 研究候选位置，
同时保持 fresh qlib 为默认策略。
```

目标 gate：

```text
phase_p0_readonly_productization_design_completed
```

## 2. 产品路线冻结

必须冻结为：

```text
默认策略：fresh qlib / rank_rotate_top50_adaptive_score
LTR 研究候选：O4 orthogonal LTR
Legacy simple LTR：保留为 audit baseline，不作为优先展示候选
```

允许说：

```text
orthogonal LTR 在历史同窗口回放中相对 simple LTR 有收益提升；
orthogonal LTR 可作为 LTR 线的新研究候选；
当前默认仍保持 fresh qlib。
```

禁止说：

```text
orthogonal LTR 是默认策略；
orthogonal LTR 已可替代 fresh qlib；
orthogonal LTR 给出买入/卖出建议；
orthogonal LTR 保证未来收益、胜率或上涨概率。
```

## 3. 设计内容

P0 必须输出一份只读产品化设计报告，至少包含：

```text
1. 页面/模块入口建议；
2. 默认策略保持 fresh qlib 的说明；
3. O4 orthogonal LTR evidence card；
4. Phase1C simple LTR audit baseline card；
5. 风险卡片；
6. O5R common universe 解释卡片；
7. 数据/PIT/next-day accounting 审计卡片；
8. 禁止接入链路清单；
9. 后续如要前端实现，需要另开工作文档和审查。
```

Evidence card 必须包含：

```text
return
max_drawdown
action_count
turnover_proxy
PnL concentration
low coverage impact
rank_ic / NDCG
feature importance summary
window
fee/tax/execution assumptions
```

## 4. 固定数值

P0 必须使用以下冻结数值，不得重算新实验：

```text
window = 2025-07-01..2026-05-07

Phase1C simple LTR return = 0.721631
O4 orthogonal LTR return = 0.800329
absolute improvement = +0.078698

Phase1C max_drawdown = -0.050830
O4 max_drawdown = -0.074962

Phase1C action_count = 405
O4 action_count = 403

Phase1C turnover_proxy = 40.328422
O4 turnover_proxy = 39.761877
```

风险标注必须包含：

```text
O4 orthogonal LTR 回撤更深；
common universe 是审计闭环，不是独立稳健性证明；
所有结果是历史只读回放，不是交易建议；
默认策略保持 fresh qlib。
```

## 5. 禁止事项

P0 禁止：

```text
修改前端代码；
修改 API；
修改 provider；
切换 accepted latest；
触发 monitor；
触发 broker/orders/quick-trade；
生成 target position/target weight；
重训模型；
重跑 qlib；
改变回放规则；
新增 filter/threshold/market gate；
把 O4 设置为默认策略。
```

## 6. 输出要求

执行者必须写：

```text
docs/tw_ltr_orthogonal_features_controlled/PHASEP0_READONLY_PRODUCTIZATION_DESIGN_EXECUTION_REPORT_CN.md
```

报告必须清楚回答：

```text
1. 默认策略是否仍为 fresh qlib？
2. O4 orthogonal LTR 在产品中扮演什么角色？
3. 原 simple LTR 如何保留为审计 baseline？
4. 哪些数值会展示？
5. 哪些风险必须展示？
6. 是否触碰任何前端/API/provider/monitor/trading 链路？
```

P0 完成后，若需要真实前端实现，必须另写 Phase P1 工作文档并等待审查确认。
