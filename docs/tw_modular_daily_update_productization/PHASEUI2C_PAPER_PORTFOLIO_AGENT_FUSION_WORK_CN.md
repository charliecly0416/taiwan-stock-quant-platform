# Phase UI2-C 工作文档：模拟账户与 Agent 融合

生成日期：2026-06-19

## 1. 工作结论

UI2-B repair 已复审通过，允许进入 UI2-C。

本阶段目标不是新增策略能力，也不是扩展交易链路，而是把 `/tw-stock-monitor` 里的模拟账户与 Agent 从“技术面板”整理为台股策略工作台的一条自然流程：

```text
今日策略 -> 候选名单 -> 历史模拟 -> 模拟账户状态 -> 策略解释助手
```

执行者必须严格遵循：

```text
docs/tw_modular_daily_update_productization/PHASEUI2_STRATEGY_WORKBENCH_AGENT_UX_OPTIMIZATION_PLAN_CN.md
.agents/skills/frontend-design/SKILL.md
```

## 2. 本阶段范围

允许修改：

```text
frontend/src/views/tw-stock-monitor/components/PaperPortfolioPanel.vue
frontend/src/views/tw-stock-monitor/index.vue
frontend/src/api/tw-stock.js
```

`frontend/src/api/tw-stock.js` 只允许在确有必要时清理旧路径主用引用或整理 simple-chat 调用，不得新增写接口。

不要求本阶段完成 UI2-D 的 Playwright 全量验收脚本，但必须保留后续可验收性。

## 3. 严禁事项

不得修改：

```text
后端/API 行为
模型、策略、排序、回放算法
日更真实链路
provider refresh / publish
accepted latest 切换
monitor config / scan / alerts 写入
broker / quick-trade / order
OpenAI key 读取、传递或前端直连
```

不得新增或主显以下语义：

```text
建议买入
建议卖出
目标仓位
保证收益
上涨概率
自动下单
连接券商
提交真实订单
```

允许在只读安全声明、拒绝语境、历史模拟、模拟账户二次确认中出现必要边界词，但必须清楚归因，不得形成真实交易入口或交易建议。

## 4. 开工前设计计划要求

执行者在编码前必须在执行报告中先写一段 `frontend-design` 设计计划，至少包含：

```text
主题：台股量化研究策略工作台
受众：每天复盘模型信号、候选名单、历史模拟、模拟账户状态的研究型用户
页面任务：让用户在 1 分钟内理解今天策略是否可进入模拟账户，并能追问 Agent 原因
颜色 token：4-6 个命名 hex
字体角色：标题/正文/数据/辅助说明
布局概念：模拟账户与 Agent 如何接在候选和历史模拟之后
签名元素：延续“交易日状态轨道 / Signal -> Target -> Replay -> Paper -> Explain”
自我批评：说明如何避免模板化营销页、工程调试台、深色霓虹终端风和装饰性渐变
```

设计方向必须是安静、精确、研究台风格。不要做 landing page、大 hero、装饰背景、渐变光斑、卡片套卡片。

## 5. `PaperPortfolioPanel.vue` 改造要求

### 5.1 标题与定位

将当前主标题：

```text
模拟策略
```

改为：

```text
模拟账户状态
```

主说明必须保留或等价表达：

```text
只影响模拟账户，不连接券商，不提交真实订单。
```

### 5.2 主界面字段

主界面只展示用户可理解字段：

```text
现金
持仓数
当前决策日期
可否应用
阻断原因
预计模拟调入
预计模拟调出
跳过与不可应用
```

不要在主界面主显：

```text
epoch
decision_id
model_id
strategy_rule
paper_order_intent_artifact_path
apply_id
raw action_type
paper_buy_intent
paper_sell_intent
initial_cash
```

这些字段如仍需保留，必须放入默认折叠的技术详情，例如：

```text
查看模拟账户技术详情
```

### 5.3 阻断原因用户化

将以下内部状态：

```text
next_open_unavailable
execution_price_pending
execution_price_unavailable
```

统一映射为用户文案：

```text
等待目标交易日开盘价，暂不能应用到模拟账户。
```

如果没有最新策略，使用：

```text
暂无可应用到模拟账户的策略。
```

如果账户 epoch 变化，使用：

```text
模拟账户已变化，请刷新后重新确认。
```

### 5.4 动作文案

主界面里的动作列表建议使用：

```text
预计模拟调出
预计模拟调入
跳过与不可应用
```

避免主界面标题使用：

```text
预计模拟买入
预计模拟卖出
```

如果源码 DTO 中仍需要识别 `paper_buy_intent` / `paper_sell_intent`，可以保留在代码映射和技术详情中，但不能成为主路径文案。

按钮可保留：

```text
应用到模拟账户
重置模拟账户
```

但必须满足：

- 不可用时显示明确原因。
- 二次确认文案继续包含“模拟账户”。
- 不新增自动应用。
- 不新增真实交易入口。
- 成功结果显示为“模拟账户已更新”或“模拟应用结果”，不要写成真实成交。

## 6. Agent block 改造要求

### 6.1 标题与角色

将当前：

```text
台股研究助手
```

改为：

```text
策略解释助手
```

副标题建议：

```text
基于今日只读策略 Prompt，解释候选、排名、模拟账户状态和数据新鲜度。
```

Agent 必须是解释助手，不是交易助手。

### 6.2 推荐问题

推荐问题应贴近工作台：

```text
今天策略是什么？
排名第一是谁？
今天有哪些候选调入？
今天有哪些调出复核？
为什么模拟账户不能应用？
2330 当前状态如何？
数据新鲜度如何？
```

不得加入：

```text
要买哪只？
买多少？
胜率多少？
目标仓位多少？
上涨概率多少？
```

### 6.3 回答展示

主界面展示：

```text
回答
相关标的
提示 / warning
只读声明
```

默认折叠：

```text
citations
checksum
mode
signal_asof
target_date
invoked_skills
raw context digest
```

checksum 只显示短码即可，例如：

```text
sha256:abcd...
```

### 6.4 快捷联动

至少完成模拟账户到 Agent 的快捷入口：

```text
解释原因
```

位置：模拟账户阻断原因旁或模拟账户状态区域内。

点击后只允许：

```text
预填/发送：为什么模拟账户不能应用？
调用现有 /agent/simple-chat
```

不得触发：

```text
交易
monitor
provider
accepted latest
日更
```

如果低风险，也可以在候选名单标题旁或排名第一行旁加入快捷问题入口；但如果会牵涉跨组件大改，本阶段优先完成模拟账户联动，候选联动可留到 UI2-D/后续。

## 7. `index.vue` 集成要求

如果 `PaperPortfolioPanel.vue` 需要触发 Agent，优先使用 Vue 事件向 `index.vue` 上抛，例如：

```text
@ask-agent="useAgentSuggestion"
```

或新增轻量 handler：

```text
askAgentFromWorkbench(question)
```

要求：

- 不在 `PaperPortfolioPanel.vue` 内重复实现 simple-chat API。
- 不把 OpenAI key 或后端内部配置暴露到前端。
- 不新增后端接口。
- 不破坏当前 `loadTwStockAgentContext` 与 `simpleChatTwStockAgent` 调用。

## 8. 样式与响应式底线

本阶段不要求完整 Playwright 截图验收，但实现必须为 UI2-D 留好基础：

- 桌面端：模拟账户与 Agent 可上下堆叠或双列，但阅读顺序必须清楚。
- 平板/手机：单列，按钮可换行，文本不能溢出按钮或卡片。
- 卡片圆角不得超过现有体系；不要卡片套卡片。
- 避免一屏出现过多 tag；优先使用状态短句。
- 数据字段要有稳定尺寸，避免 loading、空态、长股票名造成布局跳动。

## 9. 必跑验证

执行者完成后必须运行：

```bash
cd frontend && corepack pnpm build
```

必须运行静态安全检索：

```bash
rg -n "建议买入|建议卖出|目标仓位|保证收益|上涨概率|自动下单|quick-trade|broker|order submit|target_position|target_weight|provider publish|accepted latest|monitor scan|monitor alerts|连接券商|提交真实订单" frontend/src/views/tw-stock-monitor/index.vue frontend/src/views/tw-stock-monitor/components/PaperPortfolioPanel.vue frontend/src/api/tw-stock.js
```

如果命中来自安全声明或只读/模拟语境，必须逐条归因；如果命中形成交易入口或交易建议，必须修复。

建议额外运行主界面内部字段检索：

```bash
rg -n "paper_order_intent_artifact_path|decision_id|apply_id|paper_buy_intent|paper_sell_intent|initial_cash|strategy_rule|model_id|epoch|checksum|schema_version|manifest" frontend/src/views/tw-stock-monitor/components/PaperPortfolioPanel.vue frontend/src/views/tw-stock-monitor/index.vue
```

命中可以存在于源码 DTO、技术详情、折叠详情中，但不得作为主路径文案。

## 10. 执行报告要求

完成后新增或更新：

```text
docs/tw_modular_daily_update_productization/PHASEUI2_STRATEGY_WORKBENCH_AGENT_UX_EXECUTION_REPORT_CN.md
```

建议同时新增独立报告：

```text
docs/tw_modular_daily_update_productization/PHASEUI2C_PAPER_PORTFOLIO_AGENT_FUSION_EXECUTION_REPORT_CN.md
```

报告必须包含：

```text
frontend-design 设计计划
改动文件
模拟账户主界面字段变化
模拟账户阻断原因映射
被折叠的技术字段清单
Agent 标题/副标题/推荐问题变化
快捷联动说明
frontend build 结果
静态 denylist 结果与逐条归因
确认未改后端/API/模型/策略/日更/交易边界
未解决问题
是否建议审查通过
```

## 11. 审查通过标准

UI2-C 只有同时满足以下条件才可通过：

1. 模拟账户看起来是“模拟账户状态”，不再像 paper artifact 调试器。
2. 主界面清楚展示现金、持仓数、当前决策日期、可否应用、阻断原因、预计模拟调入/调出。
3. `next_open_unavailable` / `execution_price_pending` 等内部原因已用户化。
4. 真实交易边界清楚：不连接券商，不提交真实订单。
5. Agent 标题、推荐问题和回答区域都体现“策略解释助手”，不是交易助手。
6. 模拟账户可以快捷追问 Agent，且只调用现有 simple-chat。
7. 技术字段默认折叠，不抢占主路径。
8. `corepack pnpm build` 通过。
9. 静态安全检索没有未归因危险命中。
10. 没有改后端/API、模型、策略、回放算法、日更真实链路或交易边界。

## 12. 停止条件

出现以下任一情况必须停止并反馈：

- 需要改后端 DTO 才能完成基础文案映射。
- 需要新增真实交易、目标仓位、券商连接或订单语义。
- Agent 快捷联动需要新增后端接口。
- 前端需要接触 OpenAI key。
- 模拟账户写接口边界不清，无法确认只影响模拟账户。
- 移动端在当前结构下出现明显文字重叠或按钮溢出。
