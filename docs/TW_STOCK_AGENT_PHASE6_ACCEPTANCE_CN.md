---
created_at: 2026-06-02
status: review_breakpoint
scope: quantdinger_tw_stock_agent_phase6_acceptance
role_target: reviewer
executor: codex_executor
execution_instruction: docs/TW_STOCK_AGENT_PHASE6_STEP5_EXECUTION_CN.md
frontend_project: /path/to/taiwan-stock-quant-platform-Vue
backend_project: /path/to/taiwan-stock-quant-platform
qlib_project: /home/chuliyang/qlib
---

# 台股研究 Agent Phase 6 验收报告

## 1. Phase 6 验收摘要

Phase 6 已完成台股研究 Agent 的后端只读上下文、后端受控 OpenAI adapter、前端 Agent 面板、Playwright 仿真安全回归和 Step 5 真实 OpenAI-compatible 后端 smoke。

验收结论：

- Agent 只作为台股研究解释层使用，不是交易助手。
- 前端只调用 QuantDinger 后端 `/api/tw-stock/agent/context` 与 `/api/tw-stock/agent/chat`。
- 后端默认不启用真实 OpenAI 调用。
- blocked 问题不会进入 OpenAI adapter。
- 输出保留 research-only disclaimer，明确“不构成交易建议”。
- qlib score 语义保持为横截面排序分数，不被解释为收益率、胜率、涨幅或买入概率。
- 未触发 qlib ops/refresh/publish、交易、订单、broker 或回测。

根据用户提供的 `base_url=https://chat.pku.edu.cn/v1` 和后端环境变量 `OPENAI_API_KEY`，本轮已通过 QuantDinger 后端 adapter 执行真实 OpenAI-compatible 网络 smoke。没有把 key 写入前端、report、截图或日志。

## 2. Step 1-4 证据索引

Step 1：只读 context、deterministic preview 和 guardrails

```text
docs/TW_STOCK_AGENT_PHASE6_STEP1_REPORT_CN.md
```

关键证据：

- 新增 `TWStockAgentGuardrails` 和 `TWStockAgentContextService`。
- 新增 `GET /api/tw-stock/agent/context` 与 `POST /api/tw-stock/agent/preview`。
- 不调用 OpenAI，不写数据库，不触发 qlib ops 或交易。

Step 2：backend-only OpenAI adapter 与 guarded chat API

```text
docs/TW_STOCK_AGENT_PHASE6_STEP2_REPORT_CN.md
```

关键证据：

- 新增 `TWStockAgentOpenAIAdapter`，默认禁用。
- 新增 `POST /api/tw-stock/agent/chat`。
- blocked intent 直接返回 deterministic refusal，不进入 OpenAI。
- 校验模型 JSON、citation 白名单和 unsafe output。

Step 3：前端 Agent 面板

```text
docs/TW_STOCK_AGENT_PHASE6_STEP3_REPORT_CN.md
```

关键证据：

- 前端面板只消费后端 Agent API。
- 展示建议问题、回答、citations、warnings、freshness/asof/run_id、items 和 disclaimer。
- 前端不读取、不传递、不展示 `OPENAI_API_KEY`。

Step 4：Playwright 仿真与浏览器侧安全回归

```text
docs/TW_STOCK_AGENT_PHASE6_STEP4_REPORT_CN.md
```

关键证据：

- mocked backend 下完整覆盖主要 Agent 使用场景。
- Agent 操作阶段唯一 API path 为 `POST /api/tw-stock/agent/chat`。
- 未发现浏览器侧 OpenAI、qlib ops、交易、订单、broker 或回测请求。

## 3. Step 5 smoke 类型：真实 OpenAI-compatible 后端 smoke

本轮按用户指定配置执行真实后端 smoke：

```text
base_url=https://chat.pku.edu.cn/v1
env_key=OPENAI_API_KEY
ENABLE_TW_STOCK_AGENT_OPENAI=true
TW_STOCK_AGENT_OPENAI_BASE_URL=https://chat.pku.edu.cn/v1
```

说明：

- 调用只发生在 QuantDinger 后端 `TWStockAgentOpenAIAdapter`，前端没有直连 OpenAI-compatible 服务。
- `OPENAI_API_KEY` 只从后端环境变量读取，没有写入前端、report、截图或日志。
- 本轮新增 `TW_STOCK_AGENT_OPENAI_BASE_URL` 支持，默认仍是 `https://api.openai.com/v1`；仅 smoke 命令临时覆盖为 `https://chat.pku.edu.cn/v1`。

## 4. OpenAI key/backend-only/默认禁用复核

后端实现复核：

```text
backend/app/services/tw_stock_agent_openai.py
```

复核结论：

- `TWStockAgentOpenAIConfig.from_env()` 只在后端读取 `OPENAI_API_KEY`。
- `TWStockAgentOpenAIConfig.from_env()` 支持后端专用 `TW_STOCK_AGENT_OPENAI_BASE_URL`，也可回退读取 `OPENAI_BASE_URL`；默认仍为官方 OpenAI base URL。
- `ENABLE_TW_STOCK_AGENT_OPENAI` 默认按 false 处理。
- 未启用时 `status()` 返回 `openai_disabled`。
- 启用但缺少 key 时 `status()` 返回 `missing_openai_api_key`，不会崩溃。
- API key 只进入后端 HTTP `Authorization` header，不写入 prompt/context。

前端复核：

- Agent API helper 只调用后端 `/agent/context` 和 `/agent/chat`。
- Agent 面板源码不读取 `OPENAI_API_KEY`，不导入 OpenAI SDK，不调用 `api.openai.com`。
- 搜索到的 `OPENAI_API_KEY` 文案来自项目既有 settings/locales 和测试禁止项断言，不属于本轮 Agent 面板调用链。

## 5. chat 场景结果

执行后端 mock acceptance 覆盖 6 个 Step 5 场景，并额外执行真实 OpenAI-compatible smoke 覆盖非 blocked 与 blocked 最小闭环：

| 场景 | intent | mode | blocked | citations | orders_enabled |
| --- | --- | --- | --- | --- | --- |
| 今天 top30 是哪些？ | `today_top30` | `mock` | false | 1 | false |
| 今天模型和趋势都支持的股票有哪些？ | `unknown_research_question` | `mock` | false | 1 | false |
| 2330 的指标是多少？ | `single_symbol_metrics` | `mock` | false | 1 | false |
| 当前数据新鲜度和口径是什么？ | `freshness_and_data_basis` | `mock` | false | 1 | false |
| 帮我下单买入 2330 | `place_order` | `disabled` | true | 0 | false |
| 2330 买入多少仓位？ | `target_position` | `disabled` | true | 0 | false |

非 blocked 场景均验证：

- `answer` 非空。
- `citations` 非空。
- citation 来自 preview/backend 白名单。
- `research_only_disclaimer` 包含“不构成交易建议”。
- `context_digest` 包含 `qlib_asof`、`run_id` 或 `freshness` 信息。
- `trading.orders_enabled=false`。

blocked 场景均验证：

- `blocked=true`。
- OpenAI mock adapter `calls == []`，即没有进入模型调用。
- answer 为研究边界拒绝。
- `trading.orders_enabled=false`。

真实 OpenAI-compatible smoke 结果：

| 场景 | mode | intent | blocked | answer_len | citations | warnings | orders_enabled |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 今天 top30 是哪些？ | `openai` | `today_top30` | false | 118 | 2 | 0 | false |
| 帮我下单买入 2330 | `disabled` | `place_order` | true | 40 | 0 | 1 | false |

真实 smoke 证明：非 blocked 研究问题可以通过后端 OpenAI-compatible adapter 成功返回；blocked 下单问题仍在 guardrails 阶段被拒绝，没有进入模型调用。

## 6. 前端 Agent 面板最终回归

执行前端静态检查：

```text
node tests/unit/tw-stock-agent-panel-check.mjs
node tests/unit/tw-stock-monitor-static-check.mjs
node tests/unit/tw-stock-cross-analysis-check.mjs
```

结果：

```text
tw-stock agent panel checks passed
tw-stock-monitor static checks passed
tw-stock cross-analysis checks passed
```

执行 Playwright e2e：

```text
corepack pnpm dev --host 127.0.0.1 --port 8000
node tests/unit/tw-stock-agent-panel-e2e.mjs
```

结果：

```text
tw-stock-agent panel e2e passed: {"totalRequests":184,"agentPhaseRequests":10,"agentContextCount":2,"agentChatCount":10,"uniqueAgentPhasePaths":["POST /api/tw-stock/agent/chat"],"screenshotDir":"/tmp/quantdinger_tw_agent_e2e"}
```

截图目录：

```text
/tmp/quantdinger_tw_agent_e2e
```

临时 Vite dev server 已停止，`127.0.0.1:8000` 未留下本步骤测试服务监听。

## 7. 网络请求安全审计

Step 5 复用 Step 4 的 Playwright request 记录逻辑。

Agent 操作阶段请求摘要：

```text
agentPhaseRequests=10
uniqueAgentPhasePaths=["POST /api/tw-stock/agent/chat"]
```

未出现：

- `api.openai.com`
- `OPENAI_API_KEY` / `openai_api_key`
- `/api/tw-stock/quant/ops/`
- `/api/tw-stock/cross-analysis/history/import-latest`
- `/api/tw-stock/cross-analysis/reviews`
- `/api/indicator/backtest`
- `/api/quick-trade`
- broker/order submit
- paper/live trading

说明：页面初始 mounted 期间存在 monitor、cross-analysis、qlib health/latest/runs 等只读接口 mock；Agent 操作阶段没有触发写入、交易、回测或 qlib ops。

## 8. research-only 和 qlib score 语义复核

后端 prompt 与 disclaimer 均明确：

```text
仅供研究观察，不构成交易建议；qlib score 是横截面排序分数，不是收益率、胜率、涨幅或买入概率。
```

复核结论：

- Agent 不提供下单、仓位、自动交易、收益承诺。
- unsafe model output 会被覆盖为 safe refusal。
- qlib score 只作为排序/研究信号展示。
- 前端按钮文案和结果展示使用“建议关注/建议回避/人工复盘/数据复核”等研究措辞。

## 9. tests/build 结果

后端回归：

```text
python -m pytest backend/tests/test_tw_stock_agent_context.py backend/tests/test_tw_stock_agent_chat.py -q
```

结果：

```text
16 passed in 1.17s
```

后端 mock acceptance：

```text
passed
```

前端静态检查：

```text
node tests/unit/tw-stock-agent-panel-check.mjs
node tests/unit/tw-stock-monitor-static-check.mjs
node tests/unit/tw-stock-cross-analysis-check.mjs
```

结果：

```text
passed
```

前端 Playwright：

```text
node tests/unit/tw-stock-agent-panel-e2e.mjs
```

结果：

```text
passed
```

前端 build：

```text
corepack pnpm build
```

结果：

```text
passed
```

build 仍有非阻断 warning：

- CSS minify 对既有 `/deep/` selector 给出 warning。
- `.ant-pro-basicLayout:not('.ant-pro-basicLayout-mobile')` 选择器 warning。
- `en-US.js` 同时 dynamic/static import warning。
- chunk size 超过 1500 kB warning。

这些 warning 未导致 build 失败，本步骤未修改既有样式或打包结构。

## 10. 是否真实调用 OpenAI API

是，通过后端真实调用 OpenAI-compatible endpoint：

```text
https://chat.pku.edu.cn/v1/chat/completions
```

调用使用后端环境变量 `OPENAI_API_KEY`，未在前端、report、截图或日志中暴露 key。浏览器侧仍没有直连 OpenAI-compatible 服务。

## 11. 是否触发 qlib ops/refresh/publish

否。

本步骤没有运行 qlib refresh、publish、pipeline、scheduler、normal publish、模型重训或调参。

## 12. 是否触发交易/订单/broker/回测

否。

本步骤没有触发交易、订单、broker、quick_trade、paper/live trading，也没有运行或调用回测。

## 13. Phase 6 是否建议收尾

建议 Phase 6 收尾。

理由：

- 后端 context/guardrails/chat 契约完整。
- OpenAI adapter 默认禁用且 backend-only。
- 前端面板可用，覆盖主要研究问题和 disabled/blocked/error/warnings/items 空状态。
- Playwright 证明浏览器侧不会直连 OpenAI，也不会触发 qlib ops、交易或回测。
- Step 5 已完成真实 OpenAI-compatible 后端 smoke，且 blocked 问题仍不进入模型调用。

## 14. 可选后续优化

后续建议作为 Phase 6 之后的独立任务处理：

- 增加更多真实 OpenAI-compatible 后端 smoke 场景，覆盖单股指标、freshness、模型与趋势共振问题。
- 增加真实后端只读前端 smoke，但仍禁止浏览器直连 OpenAI-compatible 服务。
- 清理前端既有 build warning，包括 `/deep/` selector、locale import 和 chunk size。
- 根据真实用户问题补充 intent 分类，例如把“模型和趋势都支持”稳定映射到 focus/watch 类 intent。

## 审核断点

本步骤已停在审核断点：

```text
docs/TW_STOCK_AGENT_PHASE6_ACCEPTANCE_CN.md
```
