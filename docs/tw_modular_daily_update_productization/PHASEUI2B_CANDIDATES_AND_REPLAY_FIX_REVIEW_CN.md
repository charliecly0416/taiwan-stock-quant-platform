# Phase UI2-B Repair 复审报告：候选名单与历史模拟工作区

生成日期：2026-06-19

## 1. 复审结论

复审结论：通过。

执行者已按 `PHASEUI2B_CANDIDATES_AND_REPLAY_REVIEW_CN.md` 的 repair 要求完成小修：`ReadonlyStrategySnapshotPanel.vue` 中的动态拼接字段访问已恢复为显式 `payload.not_target_position === true`。该字段现在可以被静态安全检索直接命中，并可明确归因为 readonly safety flag。

允许进入下一阶段：UI2-C，模拟账户与 Agent 融合。

## 2. 复审范围

本次只复审 UI2-B repair：

```text
docs/tw_modular_daily_update_productization/PHASEUI2B_CANDIDATES_AND_REPLAY_FIX_EXECUTION_REPORT_CN.md
frontend/src/views/tw-stock-monitor/components/ReadonlyStrategySnapshotPanel.vue
frontend/src/views/tw-stock-monitor/components/ReadonlyReplayWindowPanel.vue
```

不重新审查 Phase UI2-A，也不提前审查 UI2-C/UI2-D。

## 3. Repair 核对

### 3.1 动态拼接已移除

当前源码为：

```js
payload.not_target_position === true &&
```

未发现继续使用：

```js
payload[`not_${'target'}_${'position'}`]
```

该修复不改变展示行为，也不改变候选名单、历史模拟、API 调用或后端逻辑。

### 3.2 静态检索命中可归因

重新检索：

```bash
rg -n "建议买入|建议卖出|目标仓位|保证收益|上涨概率|自动下单|quick-trade|broker|order submit|target_position|target_weight|provider publish|accepted latest|monitor scan|monitor alerts" frontend/src/views/tw-stock-monitor/components/ReadonlyStrategySnapshotPanel.vue frontend/src/views/tw-stock-monitor/components/ReadonlyReplayWindowPanel.vue
```

结果仅命中：

```text
frontend/src/views/tw-stock-monitor/components/ReadonlyStrategySnapshotPanel.vue:130:        payload.not_target_position === true &&
```

归因：这是只读安全 flag，用于确认 artifact 不是目标仓位指令，不是交易入口，不是仓位生成或下单路径。

## 4. Frontend Build

已重新运行：

```bash
cd frontend && corepack pnpm build
```

结果：通过，退出码 0。

构建开始处仍出现既有 shell 初始化提示：

```text
/bin/sh: 2: source: not found
```

该提示未阻断 Vite build。

## 5. 台股只读安全边界审查

### Findings

Critical：无。

High：无。

Medium：无。

Low：

1. 本阶段仍未运行 Playwright UX/network audit；按主线计划该项可留到 UI2-D 汇总验收，不阻塞 UI2-B repair 通过。

### Network Audit

本次 repair 未运行网络审计。源码核对未发现新增 broker、quick-trade、order、provider publish/refresh、accepted latest 切换、monitor config/scan/alerts 写入口。

### Console Audit

本次 repair 未运行浏览器 console audit。frontend build 已通过。

### Text / Agent Semantics

未发现用户可见的建议买入、建议卖出、目标仓位、保证收益、上涨概率承诺、自动下单、连接券商等语义。`调出复核`、`观察`、`只用于研究复盘，不代表未来收益` 等表述符合只读研究边界。

## 6. Frontend-design 复核

repair 本身没有改变 UI 设计结构。UI2-B 现状仍符合当前主线要求：

- 候选名单以股票、排名、候选调入、调出复核为主。
- 历史模拟以测试窗口、净收益、最大回撤、交易次数、费用/税费、覆盖状态为主。
- manifest、schema、checksum、DTO 字段保留在 `查看技术详情`。
- 未引入大 hero、装饰渐变、模板化营销布局或卡片嵌套问题。

## 7. 是否放行 UI2-C

放行 UI2-C。

下一阶段执行者应继续严格遵循：

```text
docs/tw_modular_daily_update_productization/PHASEUI2_STRATEGY_WORKBENCH_AGENT_UX_OPTIMIZATION_PLAN_CN.md
```

UI2-C 范围应聚焦：

```text
模拟账户与 Agent 融合
```

不得引入真实交易、券商连接、quick-trade、order submit、目标仓位写入、provider publish/refresh、accepted latest 切换、monitor config/scan/alerts 写入，技术字段仍应默认折叠，主路径继续使用用户可理解的研究工作台语言。
