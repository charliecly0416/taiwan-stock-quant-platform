# Phase P1 工作文档：Readonly Frontend Implementation

生成日期：2026-06-15

依据：

```text
docs/tw_ltr_orthogonal_features_controlled/PHASEP0_REVIEW_CN.md
docs/tw_ltr_orthogonal_features_controlled/PHASEP0_READONLY_PRODUCTIZATION_DESIGN_EXECUTION_REPORT_CN.md
```

## 1. P1 目标

P1 目标是在前端实现一个只读研究展示入口，用于展示 O4 orthogonal LTR 与 Phase1C simple LTR audit baseline。

P1 不改变默认策略，不接入交易，不触发数据刷新。

目标 gate：

```text
phase_p1_readonly_frontend_implementation_completed
```

## 2. 产品路线冻结

必须保持：

```text
default_strategy = fresh qlib / rank_rotate_top50_adaptive_score
ltr_research_candidate = O4 orthogonal LTR
legacy_simple_ltr = audit baseline
```

页面文案必须明确：

```text
当前默认策略仍为 fresh qlib；
O4 orthogonal LTR 仅为只读研究候选；
Phase1C simple LTR 仅为 frozen audit baseline；
历史回放不是交易建议。
```

## 3. 允许范围

P1 只允许：

```text
新增或调整只读前端展示组件；
读取 frozen evidence artifacts 或后端只读摘要；
展示 O4 vs Phase1C 数值；
展示风险、common universe、PIT/accounting、低覆盖说明；
新增 readonly E2E / static safety check。
```

若需要后端接口，只能是 GET/read-only，并且必须读取 frozen artifacts，不得触发计算、刷新、发布、切换或写入。

## 4. 禁止事项

P1 禁止：

```text
修改默认策略为 O4；
触发 provider refresh / publish；
切换 accepted latest；
触发 monitor scan/config/alerts；
触发 broker/orders/quick-trade；
生成 target position / target weight；
新增 POST/PUT/PATCH/DELETE；
新增买入/卖出/持仓建议语义；
承诺收益、胜率或上涨概率；
重训模型；
重跑 qlib；
改变 replay rule；
新增 filter/threshold/market gate。
```

## 5. 必须展示的固定数值

P1 不得重算新实验，只展示冻结值：

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

O4 top_symbol_abs_share = 0.102661
O4 top_day_abs_share = 0.069842
O4 max_abs_daily_nav_return = 0.038982
```

## 6. 必须展示的风险

必须醒目展示：

```text
O4 orthogonal LTR 回撤更深；
common universe 是审计闭环，不是独立稳健性证明；
所有结果是历史只读回放；
默认策略保持 fresh qlib；
不构成买卖建议、仓位建议或收益承诺。
```

## 7. 验证要求

P1 必须提供：

```text
代码 diff summary；
readonly safety static check；
前端 smoke / E2E 截图或日志；
确认无 POST/PUT/PATCH/DELETE；
确认无 provider/accepted latest/monitor/trading 请求；
确认默认策略显示仍为 fresh qlib。
```

## 8. 输出要求

执行者必须写：

```text
docs/tw_ltr_orthogonal_features_controlled/PHASEP1_READONLY_FRONTEND_IMPLEMENTATION_EXECUTION_REPORT_CN.md
```

报告必须说明：

```text
改了哪些文件；
是否改变默认策略；
是否只读；
是否触发任何禁止链路；
验证命令与结果；
剩余风险。
```
