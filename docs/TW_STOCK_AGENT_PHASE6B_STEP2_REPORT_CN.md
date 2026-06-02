---
created_at: 2026-06-02
status: review_breakpoint
scope: quantdinger_tw_stock_agent_phase6b_step2_deployment_docs_and_frontend_warnings
role_target: reviewer
executor: codex_executor
execution_instruction: docs/TW_STOCK_AGENT_PHASE6B_STEP2_EXECUTION_CN.md
previous_review_breakpoint: docs/TW_STOCK_AGENT_PHASE6B_STEP1_REPORT_CN.md
backend_project: /path/to/taiwan-stock-quant-platform
frontend_project: /path/to/taiwan-stock-quant-platform-Vue
qlib_project: /home/chuliyang/qlib
---

# 台股研究 Agent Phase 6B Step 2 执行报告

## 1. 执行摘要

本步骤按 `docs/TW_STOCK_AGENT_PHASE6B_STEP2_EXECUTION_CN.md` 执行，完成：

- 新增台股研究 Agent 部署说明文档。
- 清理前端低风险 build warning：locale dynamic/static import warning、部分 `/deep/` selector warning。
- 执行后端 Agent 回归、后端 mock smoke、前端静态检查、Agent Playwright e2e、前端 build。
- 保持 Agent research-only、安全边界和默认禁用 OpenAI 不变。

本步骤没有扩展 Agent 功能，没有保存聊天历史，没有触发 qlib ops、交易、订单、broker 或回测。

## 2. 新增/修改文件

后端项目 `/path/to/taiwan-stock-quant-platform`：

新增：

```text
docs/TW_STOCK_AGENT_DEPLOYMENT_CN.md
docs/TW_STOCK_AGENT_PHASE6B_STEP2_REPORT_CN.md
```

前端项目 `/path/to/taiwan-stock-quant-platform-Vue`：

修改：

```text
src/locales/index.js
src/layouts/BasicLayout.vue
src/views/indicator-ide/index.vue
src/views/trading-assistant/index.vue
```

## 3. 部署说明内容摘要

新增部署文档：

```text
docs/TW_STOCK_AGENT_DEPLOYMENT_CN.md
```

覆盖内容：

- `ENABLE_TW_STOCK_AGENT_OPENAI=false` 默认关闭。
- `OPENAI_API_KEY` 只设置在 QuantDinger 后端环境。
- `TW_STOCK_AGENT_OPENAI_BASE_URL` 只设置在后端，可用于 OpenAI-compatible endpoint。
- `TW_STOCK_AGENT_OPENAI_MODEL` 只设置在后端。
- `TW_STOCK_AGENT_OPENAI_TIMEOUT_SECONDS` 只设置在后端。
- 前端不得读取、保存、传递或展示 OpenAI key。
- 浏览器不得直连 OpenAI-compatible 服务。
- 未启用或缺 key 时使用 deterministic fallback。
- blocked intent 不进入模型。

安全边界：

- 不下单。
- 不生成仓位。
- 不触发 qlib refresh/publish/pipeline/scheduler/normal publish。
- 不运行回测。
- 不训练或调参 qlib 模型。
- qlib score 不是收益率、胜率、涨幅或买入概率。

部署前 checklist 包含：

```text
python backend/scripts/smoke_tw_stock_agent_phase6b.py --mock
ENABLE_TW_STOCK_AGENT_OPENAI=true OPENAI_API_KEY=<backend-only> TW_STOCK_AGENT_OPENAI_BASE_URL=<base_url> python backend/scripts/smoke_tw_stock_agent_phase6b.py
python -m pytest backend/tests/test_tw_stock_agent_context.py backend/tests/test_tw_stock_agent_chat.py -q
node tests/unit/tw-stock-agent-panel-e2e.mjs
corepack pnpm build
```

文档没有包含真实 key。

## 4. build warning 清理结果

已清理：

- `src/locales/index.js`：将动态 locale 加载从模板字符串 import 改为显式 `languageLoaders` map，清理 `en-US.js is dynamically imported but also statically imported` warning。
- `src/layouts/BasicLayout.vue`：将 build 明确报出的 logo 区域 `/deep/` selector 改为 `::v-deep`。
- `src/views/indicator-ide/index.vue`：将 build 明确报出的工作区 tabs `/deep/` selector 改为 `::v-deep`。
- `src/views/trading-assistant/index.vue`：将 build 明确报出的 strategy item 相关 `/deep/` selector 改为 `::v-deep`。

最终 build 中已不再出现：

```text
en-US.js dynamic/static import warning
/deep/ selector warning
```

仍保留：

- `.ant-pro-basicLayout:not(.ant-pro-basicLayout-mobile)` CSS minify warning。源码中未直接命中该字符串，疑似既有布局样式/依赖编译产物的选择器语法问题；本步骤未做大范围布局样式重写。
- chunk size 超过 1500 kB warning。该项需要拆包、路由懒加载或依赖拆分，按执行文档要求不在本步骤强行处理。

## 5. tests/build 结果

后端 pytest：

```text
python -m pytest backend/tests/test_tw_stock_agent_context.py backend/tests/test_tw_stock_agent_chat.py -q
```

结果：

```text
17 passed in 1.23s
```

后端 mock smoke：

```text
python backend/scripts/smoke_tw_stock_agent_phase6b.py --mock
```

结果：通过。6 个场景均 `orders_enabled=false`；blocked 下单/仓位场景保持 `mode=disabled`。

前端静态检查：

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

前端 Playwright e2e：

```text
corepack pnpm dev --host 127.0.0.1 --port 8000
node tests/unit/tw-stock-agent-panel-e2e.mjs
```

结果：

```text
tw-stock-agent panel e2e passed: {"totalRequests":183,"agentPhaseRequests":10,"agentContextCount":2,"agentChatCount":10,"uniqueAgentPhasePaths":["POST /api/tw-stock/agent/chat"],"screenshotDir":"/tmp/quantdinger_tw_agent_e2e"}
```

临时 Vite dev server 已停止，`127.0.0.1:8000` 未留下本步骤测试服务监听。

前端 build：

```text
corepack pnpm build
```

结果：通过。

剩余非阻断 warning：

```text
.ant-pro-basicLayout:not(.ant-pro-basicLayout-mobile) CSS minify warning
Some chunks are larger than 1500 kB after minification
```

## 6. 是否真实调用 OpenAI-compatible API

否。

本步骤只执行后端 mock smoke，没有执行真实 OpenAI-compatible 网络 smoke。没有读取、打印或写入真实 `OPENAI_API_KEY`。前端仍没有直连 OpenAI-compatible 服务。

## 7. 是否触发 qlib ops/refresh/publish

否。

本步骤没有运行 qlib refresh、publish、pipeline、scheduler、normal publish、模型重训或调参。

## 8. 是否触发交易/订单/broker/回测

否。

本步骤没有触发交易、订单、broker、quick_trade、paper/live trading，也没有运行或调用回测。

## 9. Phase 6B 是否建议收尾

建议 Phase 6B 收尾。

理由：

- Step 1 已完成 intent 优化和 smoke 增强。
- Step 2 已补充部署说明，明确后端 key、默认关闭、浏览器不直连和研究边界。
- 前端 Agent 静态检查、Playwright e2e、后端回归和 build 均通过。
- 低风险 build warning 已清理一部分；剩余项属于布局样式/拆包类工程质量任务，不阻塞 Agent 功能和安全验收。

## 10. 后续非阻塞优化

建议后续单独处理：

- 追踪 `.ant-pro-basicLayout:not(.ant-pro-basicLayout-mobile)` warning 的真实来源，必要时在布局样式层统一修复。
- 对超大 chunk 做前端工程优化，例如路由懒加载、manualChunks、按需拆分 ant-design-vue/echarts/codemirror。
- 将 `smoke_tw_stock_agent_phase6b.py --mock` 纳入部署前 CI/checklist；真实 OpenAI-compatible smoke 继续限定在后端受控环境。

## 审核断点

本步骤已停在审核断点：

```text
docs/TW_STOCK_AGENT_PHASE6B_STEP2_REPORT_CN.md
```
