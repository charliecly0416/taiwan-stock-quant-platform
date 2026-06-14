# Phase R7 执行报告：Manual Review 浏览器只读验收

- 执行日期：2026-06-12
- 当前阶段：Phase R7
- recommended_gate：`manual_review_browser_readonly_acceptance_passed`

## 1. 当前阶段目标

建立 manual-review 专用浏览器只读验收入口和 Playwright smoke，证明人工复盘解释模块可以在浏览器中独立渲染，并且只触发 manual-review GET，不触发 portfolio replay POST 或任何台股业务写请求。

## 2. 执行范围

本轮完成：

- 在现有 `/tw-stock-monitor` 页面增加测试专用 query flag：`manual_review_readonly=1`。
- query flag 仅在测试 URL 生效，默认 `/tw-stock-monitor` 挂载流程保持原样。
- 测试模式只渲染 manual-review 最小区块，不挂载整页历史模拟链路。
- 新增 Playwright readonly smoke。
- 生成 network、console、summary、screenshot artifact。
- 执行静态检查、浏览器 smoke 和前端 build。

本轮未做：

- 未新增后端 route。
- 未新增业务 API。
- 未新增用户导航入口。
- 未新增复杂调试页面。
- 未修改真实 `/tw-stock-monitor` 默认挂载行为。
- 未禁用既有真实业务功能。
- 未实现上下文字段映射。
- 未新增数据源。
- 未联网拉数据或使用 token。
- 未训练模型。
- 未 provider refresh/publish。
- 未 accepted latest switching。
- 未 monitor config save、monitor scan、scan-all 或 alerts write。
- 未接 broker、quick-trade、orders。
- 未引入 target position 或 target weight。
- 未输出买卖、仓位、收益、上涨概率或胜率语义。

## 3. 修改文件清单

修改：

- `frontend/src/views/tw-stock-monitor/index.vue`
  - 增加 `manualReviewReadonlyTestMode` query flag 判断。
  - 测试模式下只渲染 manual-review 最小区块。
  - 测试模式 mounted 只调用 `loadManualReviewExplanation()`，不执行默认整页加载。

新增：

- `frontend/tests/e2e/tw-stock-manual-review-readonly.mjs`
  - Playwright readonly smoke。
  - 记录所有 request。
  - 对 manual-review GET 使用 fixture/mock response。
  - 对外部静态资源 URL 使用 Playwright route fulfill，避免真实外部资源依赖。
  - 危险请求只要发出即计数失败。
- `docs/tw_manual_review_explanation/PHASER7_EXECUTION_REPORT_CN.md`

生成 artifact：

- `data_tw/ops/manual_review_readonly_e2e/phase_r7/summary.json`
- `data_tw/ops/manual_review_readonly_e2e/phase_r7/network_audit.json`
- `data_tw/ops/manual_review_readonly_e2e/phase_r7/console_audit.json`
- `data_tw/ops/manual_review_readonly_e2e/phase_r7/manual_review_readonly.png`

## 4. 是否修改前端默认行为

否。

默认 `/tw-stock-monitor` 没有 query flag 时仍执行原 mounted 流程，包括既有页面加载逻辑。新增分支只在测试 URL 带 `manual_review_readonly=1` 或 `manualReviewReadonly=true` 时生效。

## 5. 是否新增后端 route/API

否。

本轮没有修改后端，也没有新增 API。manual-review 仍使用既有：

- `GET /api/tw-stock/manual-review/explanation`

## 6. 浏览器测试 URL

本轮浏览器 smoke 使用：

`http://127.0.0.1:5178/#/tw-stock-monitor?manual_review_readonly=1&symbol=2330`

服务方式：

- 先执行 `corepack pnpm build`，工作目录 `frontend`。
- 使用 `python -m http.server 5178 --bind 127.0.0.1` 在 `frontend/dist` 启动本地静态服务。
- Playwright 访问本地静态页面。
- 业务 API 均由 Playwright route mock/fulfill。
- 测试结束后已停止本地静态服务。

说明：尝试 `corepack pnpm dev --host 127.0.0.1 --port 5178` 与 `corepack pnpm preview --host 127.0.0.1 --port 5178` 时，系统文件 watcher 达到上限，报 `ENOSPC: System limit for number of file watchers reached`。因此改用已构建 `dist` 的本地静态服务，避免 watcher，不触发后端数据刷新。

## 7. Network 审查结果

Artifact：

- `data_tw/ops/manual_review_readonly_e2e/phase_r7/network_audit.json`
- `data_tw/ops/manual_review_readonly_e2e/phase_r7/summary.json`

最终 summary：

- `request_count=21`
- `forbidden_request_count=0`
- `manual_review_get_count=1`
- `portfolio_replay_post_count=0`
- `monitor_config_write_count=0`
- `monitor_scan_post_count=0`
- `monitor_alerts_write_count=0`
- `provider_or_accepted_latest_write_count=0`
- `broker_quick_trade_order_count=0`
- `unsafe_trading_semantics_count=0`
- `disallowed_api_request_count=0`
- `failed_response_count=0`
- `external_static_mock_count=5`

允许请求说明：

- 本地静态资源 GET。
- 必要应用壳层只读 GET：auth info、brand config、broker-market policy、notification unread-count，均由 Playwright mock。
- `GET /api/tw-stock/manual-review/explanation`，由 Playwright mock。

外部静态资源说明：

- 应用壳层会请求外部静态 SVG/Iconify URL。
- 本轮 Playwright 已用 route fulfill 本地返回，artifact 中记录为 `external_static_mock_count=5`。
- 这些请求不是台股业务 API，不涉及新数据源、provider、monitor 或交易路径。

## 8. Console 摘要

Artifact：

- `data_tw/ops/manual_review_readonly_e2e/phase_r7/console_audit.json`

结果：

- `console_issue_count=0`
- `page_error_count=0`
- `consoleMessages=[]`
- `pageErrors=[]`

## 9. 页面截图 / 文本摘要

截图：

- `data_tw/ops/manual_review_readonly_e2e/phase_r7/manual_review_readonly.png`

页面文本摘要：

```text
复盘线索
只读解释当前标的的研究线索。
2330
查看线索
需要人工复盘
2330 台积电
模型排名靠前，但仍需要人工确认趋势、位置与资料完整性。
模型排名靠前
位于 Top30，属于主要研究池。
资料待补
部分上下文字段尚未完整映射，需人工补看。
查看复盘重点
```

## 10. 验证命令与结果

已执行：

- `node frontend/tests/unit/tw-stock-manual-review-explanation-check.mjs`
  - 结果：通过，`tw-stock-manual-review-explanation-check passed`。
- `node frontend/tests/unit/tw-stock-monitor-static-check.mjs`
  - 结果：通过，`tw-stock-monitor static checks passed`。
- `node --check frontend/tests/e2e/tw-stock-manual-review-readonly.mjs`
  - 结果：通过。
- `corepack pnpm build`，工作目录 `frontend`
  - 结果：通过，Vite build 成功。
  - 备注：仍有既有 `/bin/sh: 2: source: not found` 提示，但命令退出码为 0。
- `TW_STOCK_MONITOR_BASE_URL=http://127.0.0.1:5178 TW_STOCK_MANUAL_REVIEW_E2E_ARTIFACT_DIR=../data_tw/ops/manual_review_readonly_e2e/phase_r7 node tests/e2e/tw-stock-manual-review-readonly.mjs`，工作目录 `frontend`
  - 结果：通过。

环境备注：

- 普通 sandbox 下多次出现 `bwrap: loopback: Failed RTM_NEWADDR`，因此本地只读检查和 Playwright smoke 使用了提升权限执行。
- Vite dev/preview 因系统 watcher 上限 `ENOSPC` 无法稳定启动，因此使用 `python -m http.server` 托管已构建 dist。

## 11. 用户第一性原则自查

- 简单：浏览器验收只打开 manual-review 最小测试模式，不加载整页复杂链路。
- 准确：Playwright 记录所有浏览器请求，并输出固定计数 artifact。
- 清晰：报告列出测试 URL、network 计数、console 结果和 artifact 路径。
- 实用：审查者可从 summary/network/console/screenshot 直接复核本轮验收结果。

## 12. 安全边界自查

本轮没有触发或实现：

- 新数据源。
- 真实联网拉数据或 token。
- 模型训练。
- qlib provider 写入。
- provider refresh/publish。
- accepted latest switching。
- monitor config 保存。
- monitor scan 或 scan-all。
- alerts 写入。
- broker、quick-trade、orders。
- target position 或 target weight。
- 买入、卖出、持有建议。
- 仓位建议、收益承诺、上涨概率或胜率承诺。

危险请求 gate 结果全部为 0。

## 13. 是否偏离主线 / 是否新增分支

未偏离主线。

未新增业务分支。

新增 query flag 是测试专用验收入口，不进入导航，不作为用户产品入口，不改变默认页面行为。

## 14. 风险与待审查问题

- 测试模式复用了 manual-review 展示逻辑，但为避免现有静态检查误扫，测试容器使用独立 class `manual-review-readonly-panel`；审查者可确认这不改变生产面板语义。
- 浏览器运行时应用壳层仍会发起外部静态资源 URL；本轮已用 Playwright route fulfill 本地 mock，并在 artifact 记录 `external_static_mock_count=5`。这不属于台股业务 API，但可由审查者决定后续是否需要前端层面彻底移除这些外部静态依赖。
- Vite dev/preview 因系统 watcher 上限无法使用，本轮改用 build 后静态服务完成 smoke。

## 15. 给审查者的结论

R7 已完成 manual-review 浏览器只读验收入口和 Playwright smoke。

建议 gate：

`manual_review_browser_readonly_acceptance_passed`
