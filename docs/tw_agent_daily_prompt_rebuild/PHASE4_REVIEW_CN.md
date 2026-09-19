# Phase 4 审查意见：前端 Agent 面板简化

生成日期：2026-06-19

## 1. 审查结论

审查结论：通过。

允许进入 Phase 5，但范围仅限“日更编排接入”。Phase 5 不得调用 OpenAI，不得触发 provider publish、accepted latest、monitor、broker/order/quick-trade，不得把 Agent prompt 构建变成日更硬依赖。

## 2. 主线一致性判断

Phase 4 执行符合路线：

```text
DailyAgentPromptArtifact
  -> Simple Chat 后端服务
  -> 前端只读展示
```

本阶段新增 `/api/tw-stock/agent/simple-chat`，前端新增 `simpleChatTwStockAgent(...)` 并将 Agent 面板问答切到该接口。旧 `/agent/chat` 未被改写，前端不直连 OpenAI。

## 3. 安全边界审查

已检查新增路由：

- `POST /api/tw-stock/agent/simple-chat` 只调用 `TWStockAgentSimpleChatService.chat(...)`。
- route 不读取、不返回 OpenAI key/base URL/model。
- `artifactDir` 在 `FLASK_ENV=prod|production` 时被忽略。
- 未发现 provider publish、accepted latest、monitor、broker/order/quick-trade 调用。

前端新增 API block：

- 只调用 `BASE_URL + "/agent/simple-chat"`。
- 只发送 `question`、`symbol`、`maxItems`。
- 不发送 OpenAI key、endpoint、model、artifactDir。

前端 Agent panel：

- 展示 answer、citations、warnings、mode、blocked、`signal_asof`、`target_date`、checksum、research-only disclaimer。
- 推荐问题为研究观察语义。
- 未新增下单、仓位、quick-trade、broker、provider、accepted latest、monitor 操作入口。

## 4. 测试与证据审查

已复现：

```bash
python -m py_compile backend/app/services/tw_stock_agent_daily_prompt.py backend/app/services/tw_stock_agent_simple_chat.py
python -m pytest backend/tests/test_tw_stock_agent_simple_chat.py -q
python -m pytest backend/tests/test_tw_stock_agent_daily_prompt_validator.py backend/tests/test_tw_stock_agent_daily_prompt_builder.py -q
```

结果：

```text
15 passed in 1.30s
9 passed in 0.11s
```

已复现前端 build：

```bash
cd frontend && corepack pnpm build
```

结果：通过。构建开始处仍有既有 shell 初始化提示：

```text
/bin/sh: 2: source: not found
```

但命令退出码为 0，Vite build 成功。

已复现前端静态检查：

```bash
node frontend/tests/unit/tw-stock-agent-simple-chat-check.mjs
```

结果：

```text
tw-stock-agent-simple-chat-check passed
```

普通沙箱下该 Node 检查出现 `bwrap` 限制；审查按权限规则提权重跑，命令只读工作区文件，不访问网络。

## 5. 静态检索归因

OpenAI 静态检索命中：

- `frontend/src/locales/lang/*` 中既有 Settings 国际化文案。
- 既有前端测试中的 denylist/assertion。
- 新增 `tw-stock-agent-simple-chat-check.mjs` 中的 denylist。

未在新增 Simple Chat API block 或 Agent panel block 中发现 OpenAI key、SDK、endpoint 或 `chat/completions`。

危险入口静态检索命中：

- `tw-stock-agent-simple-chat-check.mjs` denylist。
- 页面既有只读声明、trading flags、旧安全校验、cross-analysis unavailable 文案。

未在新增 Simple Chat API block 或 Agent panel block 中发现 quick-trade、broker、order submit、target position/weight、monitor config/scan/alerts、provider publish、accepted latest、qlib refresh 操作入口。

## 6. 发现的问题

### Low

1. 页面其他区域仍有既有 monitor、simulation、accepted latest、broker 安全声明或旧功能代码。
   本次 Agent panel block 未新增这些入口；后续 E2E denylist 应区分整页既有功能和 Agent 面板新增行为。

2. `/agent/simple-chat` 当前沿用同类 Agent route 的鉴权状态。
   不阻塞本路线；如产品需要统一鉴权，应单独设计，不在 Phase 4 修改。

## 7. 必须修复项

Phase 4 无阻塞性必须修复项。

进入 Phase 5 前仍必须遵守：

- 不调用 OpenAI。
- 不把 Agent prompt 构建作为日更成功硬依赖。
- 默认关闭或 dry-run。
- 失败保留 previous latest。
- 不触发 provider publish、accepted latest、monitor、broker/order/quick-trade。

## 8. 可后续优化项

- Phase 5 接入时为 Agent prompt 构建增加独立 env gate。
- Phase 6 E2E 应验证前端网络请求只走 `/api/tw-stock/agent/simple-chat`，并且 blocked 问题不会触发危险请求。
- 后续可移除旧 Agent 面板中的 `agentSkills` 展示分支，减少复杂 Agent/tool 误解；当前 Simple Chat 不返回该字段，不阻塞。

## 9. 是否允许进入 Phase 5

允许进入 Phase 5。

放行范围仅限：

```text
日更编排接入
```

不得提前进入真实 OpenAI smoke 或最终 E2E 验收。
