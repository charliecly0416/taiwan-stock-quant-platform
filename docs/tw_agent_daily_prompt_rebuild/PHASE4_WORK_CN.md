# Phase 4 工作文档：前端 Agent 面板简化

生成日期：2026-06-19

## 1. 本阶段范围

Phase 4 只做前端 Agent 面板简化，让前端展示后端 Simple Chat 的 answer、citations、warnings、mode、context digest 和 research-only disclaimer。

允许两种接入方式：

- 新增后端路由 `POST /api/tw-stock/agent/simple-chat`，前端调用该路由。
- 或在不破坏现有行为的前提下，让前端继续调用 `/api/tw-stock/agent/chat`，但本阶段必须清楚说明是否已经切到 Simple Chat 服务。

优先推荐新增 `/agent/simple-chat`，避免直接重写旧 `/agent/chat` 行为。

## 2. 明确不做什么

本阶段禁止：

- 不让前端读取、传递、保存或展示 OpenAI key。
- 不让前端直连 OpenAI、OpenAI-compatible endpoint 或 OpenAI SDK。
- 不新增下单按钮。
- 不新增仓位输入。
- 不新增 quick-trade 入口。
- 不新增 broker 入口。
- 不新增 provider publish / accepted latest / qlib refresh 操作。
- 不新增 monitor config/scan/alerts 操作。
- 不写 paper account。
- 不调用真实 OpenAI smoke。
- 不接入日更编排。
- 不训练模型、不调参、不跑回放收益筛选。

## 3. 执行者任务清单

1. 如需前端可调用，新增后端 simple chat 路由：

```text
POST /api/tw-stock/agent/simple-chat
```

路由只能调用 `TWStockAgentSimpleChatService`，不得绕过 artifact loader、validator 或 safety validation。

2. 更新前端 API 方法：

```text
frontend/src/api/tw-stock.js
```

建议新增：

```text
simpleChatTwStockAgent(...)
```

3. 更新前端 Agent 面板：

```text
frontend/src/views/tw-stock-monitor/index.vue
```

或拆出组件，但不得大范围重构无关页面。

4. 新增或更新前端静态检查：

```text
frontend/tests/unit/tw-stock-agent-simple-chat-check.mjs
```

5. 输出：

```text
docs/tw_agent_daily_prompt_rebuild/PHASE4_EXECUTION_REPORT_CN.md
```

## 4. 前端展示要求

Agent 面板应展示：

- answer
- citations
- warnings
- mode
- blocked 状态
- `signal_asof`
- `target_date`
- checksum
- `research_only_disclaimer`

推荐问题聚焦：

- 今天策略是什么？
- 明天关注哪些股票？
- 排名第一的是谁？
- 今天有哪些调入/调出观察？
- 2330 当前状态如何？
- 为什么模拟账户不能应用？
- 数据新鲜度如何？

文案必须使用研究观察语义：

- “只读策略观察”
- “拟调入/拟调出观察”
- “人工复盘”
- “数据复核”
- “不构成交易建议”

不得使用行动性交易语义：

- “买入”
- “卖出”
- “下单”
- “目标仓位”
- “自动交易”
- “收益保证”
- “上涨概率”

允许在 blocked/refusal 文案中出现这些词，用于说明不支持。

## 5. 后端路由要求

如果新增 `/agent/simple-chat`：

- 请求字段只允许：
  - `question`
  - `symbol`
  - `maxItems`
  - 可选测试/开发用 `artifactDir`，生产默认应不暴露或必须后端限制。
- 响应沿用 Phase 3 Simple Chat contract。
- blocked intent 不调用 OpenAI。
- missing artifact 返回 deterministic error/fallback。
- 不记录 OpenAI key。
- 不传任何 OpenAI 配置给前端。

如不新增路由，执行报告必须说明前端如何调用 Simple Chat，以及为什么不会影响旧 `/agent/chat`。

## 6. 必须测试的场景

前端静态检查至少覆盖：

- 前端没有 `OPENAI_API_KEY`、`@openai`、OpenAI SDK、`api.openai.com`、`chat/completions`。
- Agent 面板没有 quick-trade、broker、order submit、target position、target weight、monitor config/scan/alerts、provider publish、accepted latest 操作入口。
- Agent API 方法只调用 `/api/tw-stock/agent/*`。
- 推荐问题不包含下单、仓位、收益保证、自动交易。
- 面板展示 disclaimer、warnings、citations、mode、context digest。

后端如新增路由，后端测试至少覆盖：

- route 调用 Simple Chat service。
- blocked question 返回 blocked。
- 不暴露 OpenAI key。
- 不触发 provider/monitor/broker/order。

## 7. 必须运行的测试或静态检查

最低命令：

```bash
python -m py_compile backend/app/services/tw_stock_agent_daily_prompt.py backend/app/services/tw_stock_agent_simple_chat.py
python -m pytest backend/tests/test_tw_stock_agent_simple_chat.py -q
python -m pytest backend/tests/test_tw_stock_agent_daily_prompt_validator.py backend/tests/test_tw_stock_agent_daily_prompt_builder.py -q
cd frontend && corepack pnpm build
node frontend/tests/unit/tw-stock-agent-simple-chat-check.mjs
rg -n "OPENAI_API_KEY|api.openai.com|chat/completions|@openai" frontend/src frontend/tests
rg -n "quick-trade|broker|order submit|target-position|target_position|target_weight|monitor config|monitor scan|monitor alerts|provider publish|accepted latest|qlib refresh" frontend/src/views/tw-stock-monitor/index.vue frontend/src/api/tw-stock.js frontend/tests/unit/tw-stock-agent-simple-chat-check.mjs
```

说明：

- 静态检索如果命中既有 locale、denylist、blocked/refusal 文案或测试负样本，执行报告必须逐条归因。
- 如果普通沙箱下 frontend build 需要依赖安装或网络，必须按权限规则申请；不要绕过。

## 8. 执行报告必须包含

执行者必须输出：

```text
docs/tw_agent_daily_prompt_rebuild/PHASE4_EXECUTION_REPORT_CN.md
```

报告必须包含：

- 阶段目标。
- 实际完成内容。
- 改动文件列表。
- 是否新增后端路由；如新增，列出路径和行为。
- 前端 API 调用路径。
- 前端展示字段。
- 推荐问题列表。
- OpenAI key / SDK / endpoint 不暴露证据。
- 禁止操作入口静态检查结果。
- build / unit check / backend tests 结果。
- 只读安全边界说明。
- 未完成事项。
- 风险与需要审查的问题。
- 是否建议进入 Phase 5。

## 9. 审查者重点检查项

Phase 4 审查者必须检查：

- 前端是否只调用后端 `/api/tw-stock/agent/*`。
- 前端是否没有 OpenAI key、SDK、base URL 或 endpoint。
- 是否没有新增交易、broker、monitor、provider 操作入口。
- 推荐问题是否是研究观察问题。
- blocked/refusal 是否清楚。
- pending/warnings/citations/context digest 是否展示。
- UI 文案是否避免把 top candidates 写成买卖建议。

## 10. 停止条件

出现以下任一情况必须停止，不得进入 Phase 5：

- 前端直连 OpenAI 或 OpenAI-compatible endpoint。
- 前端读取/传递 OpenAI key。
- 前端新增下单、仓位、quick-trade、broker、provider、accepted latest、monitor 操作入口。
- 推荐问题或回答文案构成买卖建议、目标仓位或收益承诺。
- 后端路由绕过 Simple Chat safety validation。
- blocked 问题可能触发 OpenAI。
