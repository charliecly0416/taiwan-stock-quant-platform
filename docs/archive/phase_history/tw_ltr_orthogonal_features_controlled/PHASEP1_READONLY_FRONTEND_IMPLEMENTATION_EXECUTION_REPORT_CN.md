# Phase P1 执行报告：Readonly Frontend Implementation

生成时间：2026-06-15T12:42:00+00:00

## 1. Gate

P1 已完成只读前端实现。

推荐 gate：

```text
phase_p1_readonly_frontend_implementation_completed
```

## 2. 改动文件

本轮改动：

```text
frontend/src/views/tw-stock-monitor/index.vue
```

新增只读展示入口：

```text
data-testid="orthogonal-ltr-readonly-evidence"
```

新增内容：

- LTR 只读研究候选卡；
- 默认策略状态：fresh qlib / rank_rotate_top50_adaptive_score；
- O4 orthogonal LTR evidence card；
- Phase1C simple LTR audit baseline card；
- 风险与集中度说明；
- O5R common universe 审计说明；
- PIT / accounting 审计说明；
- 正交特征使用说明；
- 禁止链路标签。

## 3. 默认策略是否改变

否。

页面明确展示：

```text
默认策略 = fresh qlib / rank_rotate_top50_adaptive_score
O4 orthogonal LTR = LTR 研究候选
Phase1C simple LTR = frozen audit baseline
```

本轮没有把 O4 orthogonal LTR 设置为默认策略。

## 4. 只读实现方式

P1 面板使用前端静态冻结数值，不新增 API import，不新增 GET/POST/PUT/PATCH/DELETE，不触发后端计算或刷新。

展示冻结数值：

```text
window = 2025-07-01..2026-05-07

Phase1C return = 0.721631
O4 return = 0.800329
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

## 5. 风险展示

页面已展示：

```text
O4 orthogonal LTR 回撤更深；
common universe 是审计闭环，不是独立稳健性证明；
历史只读回放不是交易建议；
默认策略保持 fresh qlib；
不承诺未来收益、胜率或上涨概率。
```

## 6. 禁止链路审计

本轮未新增：

```text
provider refresh / publish
accepted latest switching
monitor scan / config / alerts
broker/orders/quick-trade
target position / target weight
POST/PUT/PATCH/DELETE
model training
qlib rerun
replay rule change
filter/threshold/market gate
```

静态扫描结果：

- 新增 `orthogonal-ltr-*` 面板没有新增 API 调用；
- 新增面板没有绑定 click handler；
- 新增面板没有提交、保存、扫描、刷新、下单或监控动作；
- 文件中现有 provider/monitor/trading 相关命中属于既有功能，不是 P1 新增链路。

## 7. 验证命令与结果

已执行：

```text
corepack pnpm build
```

结果：

```text
通过，Vite production build 成功。
```

尝试执行：

```text
node tests/unit/tw-stock-monitor-static-check.mjs
```

结果：

```text
未执行成功：当前工作区不存在 tests/unit/tw-stock-monitor-static-check.mjs。
```

尝试启动 Vite dev / preview 做浏览器 smoke：

```text
corepack pnpm dev --host 127.0.0.1 --port 5173
corepack pnpm preview --host 127.0.0.1 --port 5174
```

结果：

```text
均受系统 file watcher 上限 ENOSPC 限制退出。
```

改用无 watcher 静态服务：

```text
python -m http.server 5174 --bind 127.0.0.1 --directory dist
```

结果：

```text
静态服务可启动并已停止。
```

尝试 Playwright screenshot：

```text
npx playwright screenshot --wait-for-timeout=3000 http://127.0.0.1:5174/tw-stock-monitor /tmp/phasep1-tw-stock-monitor.png
```

结果：

```text
未完成：本机 Playwright browser executable 缺失，未下载浏览器二进制。
```

因此本轮可确认：

```text
production build 通过；
新增面板的静态代码审计通过；
浏览器截图因本地 watcher / Playwright browser 环境限制未完成。
```

## 8. 剩余风险

剩余风险：

- 未完成真实浏览器截图；
- 需要后续 P1 review 或 P2 时在可用浏览器环境补跑只读 E2E；
- 当前页面仍包含既有 monitor/config/scan 功能，P1 新增面板本身不触发这些链路，但整页安全审计仍应在后续 review 中区分“既有功能”和“新增面板”。

## 9. 边界声明

本轮没有：

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
