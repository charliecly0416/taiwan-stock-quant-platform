# Phase P1R 工作文档：Readonly Implementation Scope Repair

生成日期：2026-06-15

依据：

```text
docs/tw_ltr_orthogonal_features_controlled/PHASEP1_READONLY_FRONTEND_IMPLEMENTATION_WORK_CN.md
docs/tw_ltr_orthogonal_features_controlled/PHASEP1_READONLY_FRONTEND_IMPLEMENTATION_EXECUTION_REPORT_CN.md
```

## 1. P1R 背景

P1 审查发现实现报告与实际工作区状态不闭合。

P1 报告声称本轮只改：

```text
frontend/src/views/tw-stock-monitor/index.vue
```

但工作区同时存在：

```text
backend/app/services/tw_ltr_optional_sim_strategy.py
```

的改动。

此外，前端改动中出现默认基线展示、今日模拟动作等逻辑，已经不只是 O4 orthogonal LTR evidence panel 的静态只读展示，需要重新界定范围。

因此 P1 暂不通过，必须执行 P1R 收口。

## 2. P1R 目标

P1R 只做一件事：

```text
修复 P1 实现范围与报告不一致的问题，并重新给出可审查的只读实现边界。
```

目标 gate：

```text
phase_p1r_readonly_implementation_scope_repaired
```

## 3. 必须先选择的收口路线

执行者必须二选一，不能混合。

### 路线 A：纯前端只读 P1

若选择路线 A，则 P1R 必须：

```text
只保留 frontend/src/views/tw-stock-monitor/index.vue 中与 orthogonal LTR readonly evidence panel 直接相关的改动；
不得包含 backend 改动；
不得改变既有 optional sim strategy service；
不得改变默认策略服务 payload；
不得新增今日模拟动作、默认基线动作解释或策略动作展示逻辑；
```

路线 A 的目标是：

```text
只在页面中展示 O4 orthogonal LTR vs Phase1C simple LTR frozen evidence；
默认策略仍显示 fresh qlib / rank_rotate_top50_adaptive_score；
不改变任何后端服务与既有策略 payload。
```

### 路线 B：前端 + 后端只读摘要

若执行者认为 backend 改动必须保留，则 P1R 必须改为路线 B，并补充完整审计。

路线 B 必须说明：

```text
为什么需要 backend/app/services/tw_ltr_optional_sim_strategy.py 改动；
改动是否只读；
是否改变默认策略 payload；
是否改变现有产品页面语义；
是否影响非 orthogonal LTR 面板；
是否会触发 provider/accepted latest/monitor/trading；
```

路线 B 仍然禁止：

```text
POST/PUT/PATCH/DELETE；
provider refresh / publish；
accepted latest switching；
monitor scan/config/alerts；
broker/orders/quick-trade；
target position / target weight；
把 O4 设置为默认策略；
输出买入/卖出/仓位建议；
承诺收益、胜率或上涨概率。
```

若路线 B 不能证明 backend 改动完全只读且不扩大产品语义，则必须退回路线 A。

## 4. 固定产品路线

无论路线 A 或 B，必须保持：

```text
default_strategy = fresh qlib / rank_rotate_top50_adaptive_score
ltr_research_candidate = O4 orthogonal LTR
legacy_simple_ltr = audit baseline
```

禁止把以下内容写成产品结论：

```text
O4 orthogonal LTR 是默认策略；
O4 orthogonal LTR 替代 fresh qlib；
O4 orthogonal LTR 产生今日交易动作；
O4 orthogonal LTR 给出买入/卖出/持仓建议。
```

## 5. 必须展示的冻结数值

如保留前端展示，必须只展示冻结值：

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

## 6. 必须保留的风险文案

必须明确展示：

```text
O4 orthogonal LTR 回撤更深；
common universe 是审计闭环，不是独立稳健性证明；
所有结果是历史只读回放；
默认策略保持 fresh qlib；
不构成买卖建议、仓位建议或收益承诺。
```

## 7. 禁止事项

P1R 禁止：

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
新增 filter/threshold/market gate；
把 backend 改动藏在“只改前端”的报告中。
```

## 8. 验证要求

P1R 必须重新提供：

```text
git diff summary；
实际改动文件清单；
路线 A 或路线 B 的选择；
readonly safety static check；
production build 结果；
无 POST/PUT/PATCH/DELETE 的证据；
无 provider/accepted latest/monitor/trading 请求的证据；
默认 fresh qlib 未改变的证据；
O4 未设置为默认的证据。
```

若浏览器 smoke 仍无法完成，必须说明环境原因，并至少提供：

```text
构建通过；
静态模板/代码审计通过；
新增面板无 click handler / submit / mutation request；
后续需要在可用浏览器环境补 E2E。
```

## 9. 输出要求

执行者必须写：

```text
docs/tw_ltr_orthogonal_features_controlled/PHASEP1R_IMPLEMENTATION_SCOPE_REPAIR_EXECUTION_REPORT_CN.md
```

报告必须包含：

```text
选择路线 A 还是路线 B；
最终实际改动文件；
每个改动文件的目的；
是否保留 backend 改动；
是否改变默认策略；
是否只读；
验证命令与结果；
剩余风险；
是否请求进入下一阶段。
```

P1R 未通过前，不允许进入 P2。
