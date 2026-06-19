# Phase P1R 执行报告：Readonly Implementation Scope Repair

生成日期：2026-06-15

## 1. 路线选择

本轮选择路线 A：纯前端只读 P1。

执行边界：只保留 `frontend/src/views/tw-stock-monitor/index.vue` 中与 orthogonal LTR readonly evidence panel 直接相关的改动；不保留 backend 改动；不改变 optional sim strategy service；不改变默认策略 payload；不新增今日模拟动作、默认基线动作解释或策略动作展示逻辑。

## 2. 实际改动文件

| 文件 | 目的 |
|---|---|
| `frontend/src/views/tw-stock-monitor/index.vue` | 新增 O4 orthogonal LTR vs Phase1C simple LTR 的静态只读证据面板，并加入只读边界、风险、common universe、PIT/accounting 与正交特征使用说明。 |
| `docs/tw_ltr_orthogonal_features_controlled/PHASEP1R_IMPLEMENTATION_SCOPE_REPAIR_EXECUTION_REPORT_CN.md` | 本执行报告。 |

## 3. 后端改动处理

`backend/app/services/tw_ltr_optional_sim_strategy.py` 不属于路线 A 范围，P1R 中未保留该文件改动，已恢复到 git 基线。

确认命令：

```text
git diff -- backend/app/services/tw_ltr_optional_sim_strategy.py
```

结果：无 diff。

## 4. 默认策略与产品路线

保持固定产品路线：

```text
default_strategy = fresh qlib / rank_rotate_top50_adaptive_score
ltr_research_candidate = O4 orthogonal LTR
legacy_simple_ltr = Phase1C simple LTR audit baseline
```

前端新增面板明确展示：

```text
当前默认策略保持 fresh qlib / rank_rotate_top50_adaptive_score；
O4 orthogonal LTR 仅作为 LTR 研究候选；
Phase1C simple LTR 仅作为 frozen audit baseline。
```

未把 O4 设为默认策略，未替代 fresh qlib，未生成今日交易动作。

## 5. 冻结数值展示

新增面板只展示冻结审计值：

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

风险文案已展示：O4 回撤更深；common universe 是审计闭环，不是独立稳健性证明；所有结果是历史只读回放；默认策略保持 fresh qlib；不构成买卖建议、仓位建议或收益承诺。

## 6. Scope Repair 结果

已移除 P1 中越界的前端内容：

```text
todayDefaultSimAction / 今日模拟动作面板
默认基线动作解释
optional sim 默认选择改动
portfolio replay strategy 展示顺序改动
rank_rotate_top50_adaptive_score 文案替换
```

保留内容仅为 orthogonal LTR 静态证据面板、对应 computed 静态数组与 CSS。

## 7. 只读安全静态审计

新增面板无 click handler、无 submit、无 mutation request、无 API 调用、无状态写入。

静态检索：

```text
rg -n "todayDefaultSimAction|data-testid="today-default-sim-action"|defaultPortfolioReplayStrategy|latestPortfolioReplayDate|today-sim-action" frontend/src/views/tw-stock-monitor/index.vue
```

结果：无匹配。

新增面板边界标签明确展示：

```text
不改默认
不触发 provider
不切 accepted latest
不触发 monitor
不连接 broker/orders
不生成 target position/weight
```

本轮未新增 POST/PUT/PATCH/DELETE，未触发 provider refresh/publish，未切换 accepted latest，未触发 monitor scan/config/alerts，未连接 broker/orders/quick-trade，未生成 target position/target weight。

## 8. Git Diff Summary

```text
git diff --stat -- frontend/src/views/tw-stock-monitor/index.vue backend/app/services/tw_ltr_optional_sim_strategy.py
frontend/src/views/tw-stock-monitor/index.vue | 280 ++++++++++++++++++++++++++
1 file changed, 280 insertions(+)
```

P1R 路线 A 的产品实现实际只改前端页面文件；本报告文件另行新增用于审查闭环。

## 9. 验证命令与结果

生产构建：

```text
cd frontend
corepack pnpm build
```

结果：通过。

关键输出：

```text
vite v5.4.21 building for production...
✓ 2319 modules transformed.
✓ built in 24.01s
```

命令开头出现 `/bin/sh: 2: source: not found`，但构建进程继续执行并以 exit code 0 完成；该信息来自 shell 初始化环境，不影响本轮构建结果。

## 10. 剩余风险

浏览器 E2E/smoke 未在本轮执行；P1 前序已遇到环境 watcher/browser binary 限制。P1R 已完成 production build 与静态模板/代码审计。后续若具备浏览器环境，可补充只读页面截图与 network audit。

## 11. Gate

```text
phase_p1r_readonly_implementation_scope_repaired
```

P1R 已按路线 A 收口。请求审查，不请求进入下一阶段。
