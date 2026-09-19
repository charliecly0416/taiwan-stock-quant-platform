# POLICY DOFUI: Daily Ops Freshness Frontend Route

生成日期：2026-07-17

## 1. 路线目标

本路线只修补 `/tw-stock-monitor` 前端首屏的信息表达，让用户打开页面后能直接看清：

- raw / 本地行情数据日期；
- qlib accepted 策略信号日期；
- readonly strategy snapshot 日期；
- Agent prompt / context 日期；
- 每日自动脚本已运行但策略 latest 未推进时的原因。

本路线不处理数据生产链路，不推进 latest，不修 provider，不改模型，不改变交易边界。

## 2. 当前背景

自然 cron evidence 显示：

- `2026-07-17` daily auto job 已运行并通过；
- FinMind raw / ops evidence 已覆盖目标 asof；
- qlib accepted latest、readonly snapshot latest、Agent prompt latest 仍停在 `2026-07-08`；
- 阻塞状态为 `RAW_READY_PROVIDER_STALE`，即 raw 已就绪，但 formal qlib provider view / canonical bridge 尚未形成可验证目标日输入。

用户当前最需要看到的不是工程日志，而是“raw 已更新”和“策略 latest 尚未推进”之间的区别。

## 3. 只读边界

允许：

- 修改前端展示；
- 复用现有 GET 状态接口；
- 运行前端 build、静态检查、只读 fixture E2E；
- 写执行报告和审查报告。

禁止：

- real Yahoo / FinMind pull；
- provider refresh / publish；
- qlib refresh；
- accepted latest switch；
- readonly snapshot latest publish；
- Agent prompt build / publish；
- OpenAI 调用；
- monitor config save / scan / alerts write；
- broker、quick-trade、order、target position、target weight。

## 4. 执行步骤

### DOFUI1 首屏状态条

在 `/tw-stock-monitor` 首屏加入 `数据链路状态` 模块，展示四个日期节点：

```text
Raw / 行情 -> Accepted 策略信号 -> Readonly snapshot -> Agent prompt
```

模块只读取现有页面状态，不新增写接口。

### DOFUI2 静态安全检查

补充 frontend unit static check：

- 首屏模块存在；
- 展示四个日期节点；
- refresh action 只调用状态读取；
- 模块不含 publish、provider refresh、accepted latest switch、order、broker、target position 等误导性动作。

### DOFUI3 Build / readonly acceptance

运行：

```text
node tests/unit/tw-stock-daily-auto-update-panel-check.mjs
corepack pnpm build
```

如需要，再运行 `/tw-stock-monitor` readonly fixture E2E。

## 5. 验收口径

通过条件：

- 首屏能直接说明 raw 与 accepted/snapshot/Agent 的日期是否一致；
- stale 或 lagging 状态以 warning/橙色表达；
- 长 run_id 不造成布局溢出；
- 移动端一列布局；
- 无新增 forbidden request；
- 不出现交易建议、下单、目标仓位、目标权重语义。

## 6. 与统一主线的关系

本路线属于 PCOM / daily ops observation 的前端可见性补丁。

它不关闭 provider bridge / canonical bridge 阻塞，也不改变“等待 150/150 自然累积”的状态。它只是让用户在日常使用前端时能正确理解当前链路状态。
