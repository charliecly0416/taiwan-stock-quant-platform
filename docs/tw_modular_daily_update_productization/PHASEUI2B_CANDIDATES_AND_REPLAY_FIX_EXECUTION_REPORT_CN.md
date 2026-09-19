# Phase UI2-B Repair 执行报告：候选名单与历史模拟工作区

生成日期：2026-06-19

## 1. 修复内容

根据 `PHASEUI2B_CANDIDATES_AND_REPLAY_REVIEW_CN.md` 的审查意见，本次只做一项小修：

```js
payload[`not_${'target'}_${'position'}`] === true
```

已恢复为显式只读安全字段：

```js
payload.not_target_position === true
```

修复文件：

- `frontend/src/views/tw-stock-monitor/components/ReadonlyStrategySnapshotPanel.vue`

该修复不改变展示行为、不改变候选名单/历史模拟 UI、不改变任何 API 调用，只恢复安全审查的静态可检索性。

## 2. 静态检索命中归因

重新运行安全语义检索后，预期会命中：

```text
payload.not_target_position === true
```

归因：这是 readonly safety flag，仅用于确认该 artifact 不是目标仓位指令，不是操作入口。它不生成仓位、不保存仓位、不提交订单、不连接券商，也不向用户展示为交易建议。

重新运行安全语义检索：

```bash
rg -n "建议买入|建议卖出|目标仓位|保证收益|上涨概率|自动下单|quick-trade|broker|order submit|target_position|target_weight|provider publish|accepted latest|monitor scan|monitor alerts" frontend/src/views/tw-stock-monitor/components/ReadonlyStrategySnapshotPanel.vue frontend/src/views/tw-stock-monitor/components/ReadonlyReplayWindowPanel.vue
```

结果：仅 1 处命中：

```text
frontend/src/views/tw-stock-monitor/components/ReadonlyStrategySnapshotPanel.vue:130:        payload.not_target_position === true &&
```

归因：该命中为 readonly safety flag，仅用于校验只读 artifact 不含目标仓位指令。


## 3. Frontend Build 结果

已重新运行：

```bash
cd frontend && corepack pnpm build
```

结果：通过，退出码 0。构建开始处仍有既有 shell 初始化提示：

```text
/bin/sh: 2: source: not found
```

但 Vite build 成功。

## 4. 边界确认

本次 repair 未修改：

- 后端/API。
- 模型、策略、回放算法。
- 日更真实链路。
- provider refresh / publish。
- accepted latest 切换。
- monitor config / scan / alerts 写入。
- broker / quick-trade / order。
- OpenAI key 读取、传递或前端直连。

## 5. 是否建议复审通过

建议复审通过。审查指出的动态拼接问题已恢复为显式字段访问；后续静态检索可直接命中并进行 readonly safety flag 归因。
