---
created_at: 2026-06-02
status: execution_report
scope: quantdinger_tw_stock_frontend_ux_quality_phase7
role: executor
review_breakpoint: docs/TW_STOCK_FRONTEND_UX_QUALITY_PHASE7_REPORT_CN.md
backend_project: /path/to/taiwan-stock-quant-platform
frontend_project: /path/to/taiwan-stock-quant-platform-Vue
---

# 台股前端用户体验质量 Phase 7 执行报告

## 1. 执行摘要

已按 `docs/TW_STOCK_FRONTEND_UX_QUALITY_PHASE7_EXECUTION_CN.md` 执行到审核断点。

本轮只做前端 UX 工程质量优化：

- 诊断 `corepack pnpm build` chunk size 和 CSS minify warning。
- 对前端 vendor chunk 做低风险 `manualChunks` 拆分。
- 溯源并修复 `@ant-design-vue/pro-layout` 的非法 CSS selector warning。
- 回归验证台股监控页、交叉分析页、台股研究 Agent 面板。

未扩展 Agent，未接入新模型，未触发 qlib 运维，未触发交易、订单、broker 或回测。

## 2. 新增/修改文件

后端项目：

- 新增：`docs/TW_STOCK_FRONTEND_UX_QUALITY_PHASE7_REPORT_CN.md`

前端项目 `/path/to/taiwan-stock-quant-platform-Vue`：

- 修改：`vite.config.js`
- 新增：`src/shims/pro-layout/BasicLayout.less`

说明：前端仓库已有多项前序阶段未提交改动，本报告仅记录本轮实际触达的文件。

## 3. build 前后 warning/chunk 对比

基线 build：

- 命令：`corepack pnpm build`
- 结果：通过。
- 最大 JS chunk：`dist/assets/ant-design-vue-Bu6_OEnn.js`，`1,590.62 kB`，gzip `490.07 kB`。
- chunk size warning：1 类，提示存在超过 `1500 kB` 的 chunk。
- CSS minify warning：4 条，同源：
  - `.ant-pro-basicLayout:not('.ant-pro-basicLayout-mobile')`
- locale dynamic/static import warning：未出现。

最终 build：

- 命令：`corepack pnpm build`
- 结果：通过。
- 最大 JS chunk：`dist/assets/ant-design-vue-CwMk6ucP.js`，`1,464.39 kB`，gzip `447.37 kB`。
- 第二大 JS chunk：`dist/assets/charts-CVO6svEm.js`，`1,126.84 kB`，gzip `375.22 kB`。
- chunk size warning：0。
- CSS minify warning：0。
- locale dynamic/static import warning：0。

主要收益：

- 最大 JS chunk 从 `1,590.62 kB` 降到 `1,464.39 kB`，低于当前 `1500 kB` warning 阈值。
- 构建输出不再有 chunk size warning。
- 构建输出不再有 `.ant-pro-basicLayout:not(...)` CSS minify warning。

## 4. manualChunks/懒加载/CSS warning 处理说明

### manualChunks

`vite.config.js` 原本已有对象式拆包：

- `ant-design-vue`
- `echarts`
- `klinecharts`
- `codemirror`

本轮改为函数式 `manualChunks(id)`，按实际模块路径分组，避免把传递依赖当作 Rollup 显式入口：

- `vue-core`：`vue` / `vue-router` / `vuex` / `vue-i18n`
- `ant-design-vue`：`ant-design-vue` 和 `@ant-design/icons`
- `charts`：`echarts` / `@antv/data-set` / `viser-vue`
- `klinecharts`
- `codemirror`
- `moment`

中间验证曾尝试把 `@ant-design/icons-vue` 单独作为对象式入口，构建失败：

- `Could not resolve entry module "@ant-design/icons-vue"`

随后改为函数式路径分组；又发现 icons 单独拆分会产生循环 chunk 提示：

- `Circular chunk: ant-design-icons -> ant-design-vue -> ant-design-icons`

最终将 `@ant-design/icons` 保持在 `ant-design-vue` chunk 内，构建通过且无循环提示。

### 路由级懒加载

检查 `src/config/router.config.js` 后确认主要业务页面已使用：

- `component: () => import(...)`

本轮未重写路由，也未改变路由权限、默认首页或业务导航。

### CSS warning

已定位真实来源：

- `node_modules/@ant-design-vue/pro-layout/es/BasicLayout.less`
- `node_modules/@ant-design-vue/pro-layout/lib/BasicLayout.less`

依赖源码中写法为：

- `&:not('.ant-pro-basicLayout-mobile')`

Less 编译后形成非法 CSS selector，并触发 esbuild CSS minify warning。

处理方式：

- 不修改 `node_modules`。
- 新增本地 shim：`src/shims/pro-layout/BasicLayout.less`。
- 内容基于依赖原始 Less，仅将 selector 修正为：
  - `&:not(.ant-pro-basicLayout-mobile)`
- 在 `vite.config.js` 新增 `proLayoutLessShim()` 插件，只拦截 `@ant-design-vue/pro-layout/es/BasicLayout.js` 中的 `./BasicLayout.less` 相对导入。

该处理是构建层兼容修复，不改变业务页面逻辑。

## 5. 用户体验收益判断

本轮满足 Phase 7 验收标准：

- 最大 JS chunk 从 `1,590.62 kB` 降到 `1,464.39 kB`。
- chunk size warning 从 1 类降到 0。
- CSS minify warning 从 4 条降到 0。
- 构建日志信噪比提升，后续部署/审核不再把依赖 CSS selector 问题误判为业务风险。
- 台股研究 Agent 面板、台股监控页、交叉分析页回归通过。

## 6. 前端测试和 build 结果

已执行：

- `node tests/unit/tw-stock-agent-panel-check.mjs`
  - 结果：通过，`tw-stock agent panel checks passed`
- `node tests/unit/tw-stock-monitor-static-check.mjs`
  - 结果：通过，`tw-stock-monitor static checks passed`
- `node tests/unit/tw-stock-cross-analysis-check.mjs`
  - 结果：通过，`tw-stock cross-analysis checks passed`
- `corepack pnpm build`
  - 结果：通过，无 CSS minify warning，无 chunk size warning。
- `node tests/unit/tw-stock-agent-panel-e2e.mjs`
  - 结果：通过。
  - 输出摘要：
    - `totalRequests`: 183
    - `agentPhaseRequests`: 10
    - `agentContextCount`: 2
    - `agentChatCount`: 10
    - `uniqueAgentPhasePaths`: `["POST /api/tw-stock/agent/chat"]`
    - `screenshotDir`: `/tmp/quantdinger_tw_agent_e2e`

e2e 期间临时启动：

- `corepack pnpm dev --host 127.0.0.1 --port 8000`

测试结束后已停止 Vite dev server，并确认 `127.0.0.1:8000` 无监听。

说明：e2e 期间 Vite 曾输出 `/api/settings/brand-config`、`/api/policy/broker-market`、`/api/strategies/notifications/unread-count` 的 proxy `ECONNREFUSED 127.0.0.1:5000` 日志，原因是没有启动完整业务后端；Agent e2e 已对目标接口进行审计并通过，不影响本轮结论。

## 7. 后端 Agent 回归结果

已执行：

- `python -m pytest backend/tests/test_tw_stock_agent_context.py backend/tests/test_tw_stock_agent_chat.py -q`
  - 结果：`17 passed in 1.15s`

- `python backend/scripts/smoke_tw_stock_agent_phase6b.py --mock`
  - 结果：通过。
  - 6 个场景全部 `ok=true`。
  - `orders_enabled=false`。
  - 下单/仓位类问题保持 `blocked_research_boundary`。

## 8. 是否触发 OpenAI browser call

否。

前端 e2e 网络审计显示 Agent 阶段唯一请求路径为：

- `POST /api/tw-stock/agent/chat`

未发现浏览器侧 OpenAI/OpenAI-compatible 调用。

## 9. 是否触发 qlib ops/refresh/publish

否。

本轮未执行 qlib refresh、publish、pipeline、ops、scheduler 或数据发布命令。

## 10. 是否触发交易/订单/broker/回测

否。

本轮未触发：

- trading
- order
- broker
- quick_trade
- paper/live trading
- backtest

Agent mock smoke 中交易/仓位意图继续被阻断。

## 11. 是否建议收尾

建议 Phase 7 收尾。

理由：

- 用户体验工程质量目标已达成。
- build warning 已清零。
- 最大 chunk 已低于当前阈值。
- 台股核心页面和 Agent 面板回归通过。
- 未越过 Agent、qlib、交易、回测安全边界。

## 12. 后续非阻塞事项

- `ant-design-vue` 仍是最大 vendor chunk，最终大小 `1,464.39 kB`，接近 `1500 kB` 阈值。进一步降低需要更系统的组件级按需引入评估，风险高于本轮低风险优化范围。
- `charts` chunk 为 `1,126.84 kB`。如后续要优化首屏，可进一步检查首页是否间接加载图表依赖；本轮未改路由或业务导入链。
- 多语言 locale chunk 仍较大，属于已有国际化资源体积问题；本轮未删除语言或改默认语言策略。
- 前端仓库仍存在前序阶段未提交改动，审核时应按文件维度区分本轮改动与历史改动。
