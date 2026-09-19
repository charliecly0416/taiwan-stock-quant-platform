# Phase 4 执行报告：前端 Agent 面板简化

生成日期：2026-06-19

## 1. 阶段目标

按照 `PHASE4_WORK_CN.md`，本阶段只完成台股 Agent 前端面板简化，并接入 Phase 3 的 `TWStockAgentSimpleChatService`。目标是让前端展示 Simple Chat contract 中的 answer、citations、warnings、mode、blocked、context digest 与 research-only disclaimer。

本阶段未进入 Phase 5，未做日更编排，未调用真实 OpenAI smoke，未新增交易、broker、quick-trade、provider、accepted latest、monitor 写入口。

## 2. 实际完成内容

1. 新增后端路由：
   - `POST /api/tw-stock/agent/simple-chat`
   - route 只调用 `TWStockAgentSimpleChatService.chat(...)`。
   - 请求字段使用 `question`、`symbol`、`maxItems`，兼容 `max_items`。
   - `artifactDir/artifact_dir` 仅保留为测试/开发辅助字段；当 `FLASK_ENV=prod|production` 时后端忽略该字段并使用默认 latest artifact。
   - route 不读取、不记录、不返回 OpenAI key 或 OpenAI 配置。

2. 新增前端 API 方法：
   - `simpleChatTwStockAgent(...)`
   - 调用路径为 `BASE_URL + "/agent/simple-chat"`，即 `/api/tw-stock/agent/simple-chat`。
   - 前端只传递 question、symbol、maxItems，不传 OpenAI key、endpoint、model、artifactDir。

3. 更新台股监控页 Agent 面板：
   - 从旧 `chatTwStockAgent` 切换到 `simpleChatTwStockAgent`。
   - 面板文案调整为每日只读策略 Prompt artifact、排序、候选、模拟账户 gate 与数据状态。
   - 上下文摘要展示 `signal_asof`、`target_date`、checksum、状态 / 模式。
   - 继续展示 answer、citations、warnings、mode、blocked 与 `research_only_disclaimer`。

4. 推荐问题固定为研究观察语义：
   - 今天策略是什么？
   - 明天关注哪些股票？
   - 排名第一的是谁？
   - 今天有哪些调入调出观察？
   - 2330 当前状态如何？
   - 为什么模拟账户不能应用？
   - 数据新鲜度如何？

5. 新增/增强测试：
   - `backend/tests/test_tw_stock_agent_simple_chat.py` 增加 route 测试，覆盖 Simple Chat service 调用、blocked payload、响应不暴露 `OPENAI_API_KEY`、生产环境忽略 `artifactDir`。
   - `frontend/tests/unit/tw-stock-agent-simple-chat-check.mjs` 覆盖 Simple Chat API path、面板字段、推荐问题、OpenAI/危险入口 denylist。

## 3. 改动文件列表

- `backend/app/routes/tw_stock.py`
- `frontend/src/api/tw-stock.js`
- `frontend/src/views/tw-stock-monitor/index.vue`
- `backend/tests/test_tw_stock_agent_simple_chat.py`
- `frontend/tests/unit/tw-stock-agent-simple-chat-check.mjs`
- `docs/tw_agent_daily_prompt_rebuild/PHASE4_EXECUTION_REPORT_CN.md`

## 4. 前端展示字段

Agent 面板当前覆盖：answer、citations、warnings、mode、blocked、`signal_asof`、`target_date`、checksum、`research_only_disclaimer`。

## 5. OpenAI key / SDK / endpoint 不暴露证据

执行：

```bash
rg -n "OPENAI_API_KEY|api.openai.com|chat/completions|@openai" frontend/src frontend/tests
```

命中归因：

- `frontend/src/locales/lang/*`：既有 Settings 国际化字段，属于全局设置文案，不是本次 Agent 面板或 Simple Chat API。
- `frontend/tests/e2e/tw-stock-agent-openai-skills-network.mjs`、`frontend/tests/unit/tw-stock-agent-panel*.mjs`、`frontend/tests/unit/tw-stock-agent-simple-chat-check.mjs`：测试 denylist / assertion，用于确认不泄漏 OpenAI key 或 endpoint。
- 本次新增 `simpleChatTwStockAgent` API block 与 Agent 面板 block 未出现 OpenAI key、SDK、endpoint 或 `chat/completions`。

## 6. 禁止操作入口静态检查结果

执行：

```bash
rg -n "quick-trade|broker|order submit|target-position|target_position|target_weight|monitor config|monitor scan|monitor alerts|provider publish|accepted latest|qlib refresh" frontend/src/views/tw-stock-monitor/index.vue frontend/src/api/tw-stock.js frontend/tests/unit/tw-stock-agent-simple-chat-check.mjs
```

命中归因：

- `frontend/tests/unit/tw-stock-agent-simple-chat-check.mjs`：denylist 断言命中。
- `frontend/src/views/tw-stock-monitor/index.vue` 既有只读声明、只读 trading flags、cross-analysis unavailable 文案与旧模拟/安全校验代码命中；不是本次新增 Agent 面板入口。
- 本次新增 Simple Chat API block 不含 quick-trade、broker、order submit、target position/weight、monitor config/scan/alerts、provider publish、accepted latest、qlib refresh。
- 本次新增推荐问题不含下单、仓位、收益保证、自动交易或目标仓位语义。

## 7. 测试结果

已运行：

```bash
python -m py_compile backend/app/services/tw_stock_agent_daily_prompt.py backend/app/services/tw_stock_agent_simple_chat.py
```

结果：通过。

```bash
python -m pytest backend/tests/test_tw_stock_agent_simple_chat.py -q
```

结果：`15 passed in 1.33s`。

```bash
python -m pytest backend/tests/test_tw_stock_agent_daily_prompt_validator.py backend/tests/test_tw_stock_agent_daily_prompt_builder.py -q
```

结果：`9 passed in 0.12s`。

```bash
cd frontend && corepack pnpm build
```

结果：通过，Vite build 成功。命令开始处出现既有 shell 初始化提示 `/bin/sh: 2: source: not found`，但退出码为 0，不影响构建。

```bash
node frontend/tests/unit/tw-stock-agent-simple-chat-check.mjs
```

结果：`tw-stock-agent-simple-chat-check passed`。普通沙箱下该 Node 检查曾因 `bwrap: loopback: Failed RTM_NEWADDR: Operation not permitted` 启动失败，已按权限规则在沙箱外重跑通过。

## 8. 只读安全边界说明

- 前端仍只调用后端 `/api/tw-stock/agent/simple-chat`。
- 前端不读取、不传递、不展示 OpenAI key、SDK、base URL 或 endpoint。
- 后端 route 只转接 `TWStockAgentSimpleChatService`，不绕过 artifact loader、validator 或 Simple Chat safety validation。
- blocked intent 逻辑仍由 Simple Chat service 处理；route 测试覆盖 blocked payload。
- 本阶段未新增 broker、quick-trade、order、target-position/target-weight、monitor config/scan/alerts、provider publish、accepted latest 或 qlib refresh 操作入口。
- `artifactDir` 在 production 环境被 route 忽略，避免生产请求选择任意 artifact 路径。

## 9. 未完成事项

无 Phase 4 范围内必须项未完成。

## 10. 风险与需要审查的问题

1. 页面其它区域仍存在既有只读声明、模拟账户安全校验、cross-analysis unavailable 文案中的 `broker`、`accepted latest` 等字符串；本次未改动这些区域，需要审查者按上下文区分只读声明和真实操作入口。
2. Simple Chat route 当前未加登录装饰器，保持与现有 `/agent/chat` 同类 route 一致；如后续产品需要统一鉴权，应作为单独阶段处理。
3. Phase 4 未做真实 OpenAI smoke，符合本阶段禁止项；真实 OpenAI 验收必须等待后续阶段文档允许。

## 11. 是否建议进入 Phase 5

建议等待 Phase 4 审查通过后再进入 Phase 5。当前执行结果满足 Phase 4 工作文档要求，但不应在本报告后直接进入 Phase 5。
