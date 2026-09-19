# Phase UI2-B 工作文档：候选名单与历史模拟工作区

生成日期：2026-06-19

## 1. 本阶段目标

Phase UI2-B 只执行 `PHASEUI2_STRATEGY_WORKBENCH_AGENT_UX_OPTIMIZATION_PLAN_CN.md` 中的两块：

```text
候选名单
历史模拟
```

目标是把 `ReadonlyStrategySnapshotPanel.vue` 和 `ReadonlyReplayWindowPanel.vue` 从工程审计面板整理成用户可扫描的策略工作区，并开始落实更新后主线文档中的 `frontend-design` 视觉要求。

本阶段不做模拟账户与 Agent 融合，不新增最终 Playwright UX audit；这些分别留给 UI2-C 和 UI2-D。

## 2. Frontend-design 先行要求

执行者写代码前，必须在执行报告中先给出一段简短设计计划。该计划不是营销页设计，而是策略工作台的产品视觉约束。

固定主题、受众、任务：

```text
主题：台湾股票量化研究策略工作台
受众：每天复盘模型信号、候选名单、模拟账户状态的研究型用户
页面任务：让用户在 1 分钟内理解今天策略状态，并能追问 Agent 解释候选、排名、阻断原因和数据新鲜度
```

设计计划必须包含：

```text
颜色 token：4-6 个命名色值
字体/字重角色：标题、正文、数据/代码类 caption
布局概念：候选名单、调出复核、历史模拟与顶部总览的层级关系
签名元素：一个可解释的视觉记忆点
自我批评：说明哪些选择避免了模板化默认 UI
```

推荐视觉方向：

```text
安静、精确、研究台风格；股票代码、日期、排名和状态是主角。
```

推荐签名元素：

```text
交易日状态轨道 / Signal -> Target -> Replay
```

在 UI2-B 中可以先轻量落地为：

- 候选名单用稳定的排名节奏和股票代码列形成扫描锚点。
- 历史模拟用“测试窗口 -> 指标 -> 覆盖状态”的顺序对应顶部总览的 signal/target 语义。
- 使用极少量状态色区分 ready / pending / review，不堆彩色 tag。

避免：

- 暖米色杂志风。
- 大面积深色霓虹金融终端风。
- 报纸式细线密排风。
- 大 hero、渐变背景、装饰光斑、无意义动效。
- 为了“高级感”牺牲信息密度和可扫描性。

## 3. 允许修改文件

优先范围：

```text
frontend/src/views/tw-stock-monitor/components/ReadonlyStrategySnapshotPanel.vue
frontend/src/views/tw-stock-monitor/components/ReadonlyReplayWindowPanel.vue
frontend/src/views/tw-stock-monitor/index.vue
```

如确需调整只读前端测试或静态检查，可新增或修改：

```text
frontend/tests/unit/*
frontend/tests/e2e/*
```

本阶段原则上不应修改：

```text
frontend/src/api/tw-stock.js
backend/**
scripts/**
```

除非只是修正前端 DTO 字段名兼容；如果需要改 API 或后端，停止并说明原因。

## 4. 严格禁止

本阶段禁止：

- 不改模型、策略、回放算法。
- 不改日更真实链路。
- 不触发 provider refresh / publish。
- 不切换 accepted latest。
- 不写 monitor config / scan / alerts。
- 不新增 broker / quick-trade / order。
- 不新增 target position / target weight 语义。
- 不让前端读取或传递 OpenAI key。
- 不让前端直连 OpenAI 或 OpenAI-compatible endpoint。
- 不把历史模拟写成收益承诺、胜率承诺、上涨概率承诺。

允许继续保留既有只读 GET 和既有只读展示。

## 5. UI2-B-1：候选名单

### 5.1 目标

将 `ReadonlyStrategySnapshotPanel.vue` 主体验改为：

```text
候选名单
```

副标题建议：

```text
根据当前模型排序生成，仅供研究复盘。
```

### 5.2 主界面结构

主界面分为两个子区：

```text
候选调入
调出复核
```

桌面可双列；平板/手机必须能自然单列，无横向滚动。

### 5.3 候选调入行式布局

每行以股票为中心，不以 manifest 或审计状态为中心。

推荐格式：

```text
#1 2330 台积电
LTR #1 · Qlib Top50 #3 · 全市场 #12
```

如果没有股票名称：

```text
#1 TW2330
LTR #1 · Qlib Top50 #3 · 全市场 #12
```

字段缺失时不要显示 `undefined/null`，用 `-` 或省略该段。

### 5.4 调出复核行式布局

推荐格式：

```text
2357
跌出 Qlib Top50 · 当前全市场 #67
```

文案要明确是“复核/观察”，不能写成卖出建议。

### 5.5 视觉节奏

候选列表应有明确扫描节奏：

- 第一列：排名或复核状态。
- 第二列：股票代码/名称。
- 第三列：LTR/Qlib/全市场排名摘要。
- 右侧最多一个状态标记，例如 `待复盘` 或 `候选`。

每行主信息不超过 2 行。不要堆 4 个以上 tag。

### 5.6 空态

必须有清楚空态：

```text
暂无候选调入。
暂无调出复核。
```

空态不要用情绪化文案；说明下一步可刷新或等待下一次只读 artifact。

### 5.7 技术详情

保留审计信息，但默认折叠到：

```text
查看技术详情
```

可包含：

```text
manifest
validation
checksum
source paths
readonly flags
schema_version
```

主界面不要常显这些字段。

## 6. UI2-B-2：历史模拟

### 6.1 目标

将 `ReadonlyReplayWindowPanel.vue` 主标题改为：

```text
历史模拟
```

说明必须包含：

```text
只用于研究复盘，不代表未来收益。
```

### 6.2 主界面字段

主界面只展示用户可理解指标：

```text
测试窗口
净收益
最大回撤
交易次数
费用/税费
覆盖状态
```

不要把内部 policy 和 artifact 名称作为主视觉。

### 6.3 用户化文案替换

将技术词替换到主界面之外：

```text
readonly replay window -> 历史模拟
ReplayWindowPolicy -> 测试窗口规则
generated_readonly -> 已审计窗口
final equity -> 期末模拟资产
turnover_proxy_by_notional_over_avg_equity -> 换手强度
```

后两项可以在技术详情或次级说明中出现，不要抢主路径。

### 6.4 交易日状态轨道轻量落地

历史模拟区可以使用轻量结构表达：

```text
测试窗口 -> 费用/税费 -> 结果指标 -> 覆盖状态
```

这个结构要服务于理解，不要做装饰时间轴，不要新增动画或复杂图形。

### 6.5 安全文案

必须保留并主显：

```text
历史模拟不代表未来收益。
```

不得出现：

```text
保证收益
胜率承诺
上涨概率
建议买入
建议卖出
自动下单
目标仓位
```

### 6.6 技术详情

保留原始 replay policy、request params、manifest/checksum/source 等技术信息，但默认折叠到 `查看技术详情`。

## 7. 视觉与响应式要求

候选名单：

- 股票列表行式、紧凑、可扫描。
- 每行主信息不超过 2 行。
- 不用大量 tag 堆叠。
- 不做卡片套卡片。
- 卡片圆角不超过 8px。
- 股票代码、日期、排名和状态是主角。

历史模拟：

- 指标可以横排；手机必须单列或自然换行。
- 数字和标签要在同一块里清楚对应。
- 不使用大 hero、不新增装饰背景、不做大面积渐变。
- 不把净收益等指标设计成收益承诺。

响应式最低要求：

```text
desktop：候选/调出双列，历史模拟指标横排
tablet：候选可窄双列或单列，按钮可换行
mobile：全部单列，无横向滚动，文字不重叠
```

## 8. 必跑验证

至少运行：

```bash
cd frontend && corepack pnpm build
```

静态检查建议：

```bash
rg -n "readonly replay window|ReplayWindowPolicy|generated_readonly|final equity|turnover_proxy_by_notional_over_avg_equity|manifest|checksum|schema_version|source_artifact" frontend/src/views/tw-stock-monitor/components/ReadonlyStrategySnapshotPanel.vue frontend/src/views/tw-stock-monitor/components/ReadonlyReplayWindowPanel.vue
```

说明：命中不一定失败，但执行报告必须归因：主界面命中要修；技术详情折叠区命中可接受。

安全语义检查建议：

```bash
rg -n "建议买入|建议卖出|目标仓位|保证收益|上涨概率|自动下单|quick-trade|broker|order submit|target_position|target_weight|provider publish|accepted latest|monitor scan|monitor alerts" frontend/src/views/tw-stock-monitor/components/ReadonlyStrategySnapshotPanel.vue frontend/src/views/tw-stock-monitor/components/ReadonlyReplayWindowPanel.vue
```

同样：只读声明里的 broker/order 字样需要按上下文归因；真实操作入口或行动建议必须修。

## 9. 执行报告要求

执行者完成后更新执行报告：

```text
docs/tw_modular_daily_update_productization/PHASEUI2_STRATEGY_WORKBENCH_AGENT_UX_EXECUTION_REPORT_CN.md
```

报告必须包含：

```text
1. 本次阶段：UI2-B 候选名单与历史模拟
2. frontend-design 设计计划：颜色 token、字体/字重、布局概念、签名元素、自我批评
3. 改动文件
4. 候选名单主界面字段
5. 调出复核主界面字段
6. 历史模拟主界面字段
7. 移入技术详情的字段清单
8. 空态处理
9. 响应式处理
10. frontend build 命令与结果
11. 静态 denylist / 内部字段检索结果与归因
12. 安全边界声明
13. 未完成事项，明确 UI2-C/UI2-D 仍未执行
```

## 10. 停止条件

出现以下任一情况必须停止并找审查者/统筹确认：

- 需要改后端 API 才能完成展示。
- 需要改模型、策略或回放算法。
- 需要新增真实交易、目标仓位、自动下单语义。
- 需要触发 provider publish、accepted latest、monitor、broker/order。
- 技术详情无法低风险从主界面拆出。
- 手机端布局无法避免明显横向溢出或重叠。
- 为了追求视觉效果需要牺牲信息密度或可扫描性。

## 11. 审查者验收口径

审查者只审查 UI2-B，不要求 UI2-C/UI2-D 完成。

通过条件：

- 执行报告包含 frontend-design 设计计划，且不是模板化营销设计。
- 候选名单以股票和排名为主。
- 调出复核不被写成卖出建议。
- 历史模拟主界面用户可理解且不承诺未来收益。
- manifest/checksum/schema/source/replay policy 等技术信息默认折叠。
- frontend build 通过。
- 无新增 OpenAI、provider、accepted latest、monitor、broker/order/quick-trade 入口。
- 布局在代码层面具备 desktop/tablet/mobile 响应式约束；最终截图验收留到 UI2-D。

若候选名单仍像 artifact 审计面板，或历史模拟仍以 `ReplayWindowPolicy`/manifest/checksum 为主视觉，不得通过。
