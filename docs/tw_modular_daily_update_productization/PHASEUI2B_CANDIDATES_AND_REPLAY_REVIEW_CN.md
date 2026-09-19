# Phase UI2-B 审查意见：候选名单与历史模拟工作区

生成日期：2026-06-19

## 1. 审查结论

审查结论：不通过，需小修后复审。

候选名单与历史模拟的 UX 方向基本符合 `PHASEUI2B_CANDIDATES_AND_REPLAY_WORK_CN.md` 和更新后的 `frontend-design` 要求：执行报告包含设计计划，候选名单转为股票优先，历史模拟转为用户可理解指标，技术字段默认折叠，frontend build 通过。

但本次实现中出现了一个不应接受的安全审查可证明性问题：`ReadonlyStrategySnapshotPanel.vue` 将 `payload.not_target_position === true` 改成了动态字符串属性访问：

```js
payload[`not_${'target'}_${'position'}`] === true
```

这不会新增交易入口，但会绕开静态 denylist/安全检索对 `target_position` 的可见性。只读安全字段应当允许被静态检索命中并由报告归因，不应通过动态拼接隐藏。

## 2. 审查范围

本次只审查 UI2-B：

```text
ReadonlyStrategySnapshotPanel.vue
ReadonlyReplayWindowPanel.vue
PHASEUI2_STRATEGY_WORKBENCH_AGENT_UX_EXECUTION_REPORT_CN.md
```

不重新审查前序 Agent Daily Prompt 路线，不要求 UI2-C/UI2-D 完成。

## 3. 通过项

### Frontend-design 计划

执行报告已包含：

- 颜色 token。
- 字体/字重角色。
- 布局概念。
- 签名元素。
- 自我批评。

方向符合主线文档：安静、精确、研究台风格；股票代码、日期、排名和状态是主角。未采用大 hero、渐变背景、装饰光斑、深色霓虹终端风或暖米色杂志风。

### 候选名单

`ReadonlyStrategySnapshotPanel.vue` 已从 `策略快照` 改为：

```text
候选名单
```

主界面拆为：

```text
候选调入
调出复核
```

候选行现在以排名、股票代码/名称、LTR/Qlib/全市场排名摘要为主，空态也已改为：

```text
暂无候选调入。
暂无调出复核。
```

这符合 UI2-B 目标。

### 历史模拟

`ReadonlyReplayWindowPanel.vue` 已从 `只读回放窗口` 改为：

```text
历史模拟
```

主界面保留用户可理解指标：

```text
测试窗口
净收益
最大回撤
交易次数
费用/税费
覆盖状态
```

并主显：

```text
只用于研究复盘，不代表未来收益。
```

`ReplayWindowPolicy`、`final equity`、`turnover_proxy_by_notional_over_avg_equity` 等工程字段已从主路径移走，保留在技术详情或源码 DTO 映射中。

### 技术详情

两块组件都使用 `查看技术详情` 折叠承载 manifest、schema、checksum、source、readonly flags 等内容。方向符合本阶段要求。

## 4. 阻塞问题

### Medium：动态拼接 `not_target_position` 绕开静态安全检索

位置：`frontend/src/views/tw-stock-monitor/components/ReadonlyStrategySnapshotPanel.vue`

当前代码：

```js
payload[`not_${'target'}_${'position'}`] === true
```

问题：

- `not_target_position` 是只读安全 flag，不是危险操作入口。
- 它可以出现在源码中，并由静态检索报告归因为 readonly safety flag。
- 使用动态拼接会让 `rg target_position` 看不到该安全字段，削弱后续审查、自动化 denylist 和人工检索的可信度。
- 本项目安全审查规则强调不能只按关键词误判，但也要求危险/边界词可被明确归因；不应通过字符串拼接规避检索。

必须修复：

```js
payload.not_target_position === true
```

然后在执行报告中把静态检索里的 `not_target_position` 命中归因为：

```text
Readonly safety flag，仅用于确认该 artifact 不是目标仓位指令，不是操作入口。
```

该修复不应改任何展示行为。

## 5. 台股只读安全边界审查

### Findings

Critical：无。

High：无。

Medium：

1. 动态拼接 `not_target_position` 绕开静态安全检索，需恢复为显式 safety flag。

Low：

1. UI2-B 尚未运行 Playwright UX/network audit。执行报告明确该项留到 UI2-D，不作为本阶段阻塞项。

### Network Audit

本阶段未运行网络审计；UI2-B 工作文档允许最终 Playwright UX audit 留到 UI2-D。

### Console Audit

本阶段未运行浏览器 console audit。frontend build 已通过。

### Text / Agent Semantics

未发现建议买入、建议卖出、目标仓位、收益承诺、上涨概率承诺、自动下单等用户可见语义。调出区使用 `调出复核`、`观察`，没有写成卖出建议。

## 6. 复现验证

已复现：

```bash
cd frontend && corepack pnpm build
```

结果：通过。构建开始处仍有既有提示：

```text
/bin/sh: 2: source: not found
```

Vite build 退出码为 0。

已复现内部字段静态检查：

```bash
rg -n "readonly replay window|ReplayWindowPolicy|generated_readonly|final equity|turnover_proxy_by_notional_over_avg_equity|manifest|checksum|schema_version|source_artifact" frontend/src/views/tw-stock-monitor/components/ReadonlyStrategySnapshotPanel.vue frontend/src/views/tw-stock-monitor/components/ReadonlyReplayWindowPanel.vue
```

命中均为源码 DTO 映射或技术详情，未发现主路径明显违规。

已复现安全语义检查：

```bash
rg -n "建议买入|建议卖出|目标仓位|保证收益|上涨概率|自动下单|quick-trade|broker|order submit|target_position|target_weight|provider publish|accepted latest|monitor scan|monitor alerts" frontend/src/views/tw-stock-monitor/components/ReadonlyStrategySnapshotPanel.vue frontend/src/views/tw-stock-monitor/components/ReadonlyReplayWindowPanel.vue
```

结果无命中。但该结果受到动态拼接 `not_target_position` 的影响，因此不能作为完全可信的安全归因证据。

## 7. Repair 要求

执行者只需做小修：

1. 将动态拼接恢复为显式字段访问：

```js
payload.not_target_position === true
```

2. 更新执行报告，说明静态安全检索中 `target_position` 的命中属于 readonly safety flag 归因，不是危险入口。

3. 重新运行：

```bash
cd frontend && corepack pnpm build
rg -n "建议买入|建议卖出|目标仓位|保证收益|上涨概率|自动下单|quick-trade|broker|order submit|target_position|target_weight|provider publish|accepted latest|monitor scan|monitor alerts" frontend/src/views/tw-stock-monitor/components/ReadonlyStrategySnapshotPanel.vue frontend/src/views/tw-stock-monitor/components/ReadonlyReplayWindowPanel.vue
```

4. 新增修复报告：

```text
docs/tw_modular_daily_update_productization/PHASEUI2B_CANDIDATES_AND_REPLAY_FIX_EXECUTION_REPORT_CN.md
```

报告必须包含：

```text
修复内容
静态检索命中归因
frontend build 结果
确认未改后端/API/日更/交易边界
是否建议复审通过
```

## 8. 是否允许进入 UI2-C

暂不允许进入 UI2-C。

完成上述小修并复审通过后，才能进入 UI2-C：模拟账户与 Agent 融合。
