# Phase R6 审查结论与 Phase R7 工作文档

审查日期：2026-06-12

审查入口：

- `docs/tw_manual_review_explanation/PHASER6_EXECUTION_REPORT_CN.md`
- `docs/tw_manual_review_explanation/manual_review_browser_readonly_acceptance_plan.md`
- `docs/tw_manual_review_explanation/PHASER6_REVIEW_BASELINE_AND_NEXT_WORK_CN.md`
- `docs/TW_STOCK_MANUAL_REVIEW_EXPLANATION_NEXT_ROUND_PLAN_CN.md`
- 台股只读安全边界审查规则

## 1. 本步审核结论

Phase R6 通过。

接受 gate：

`request_phaser7_browser_readonly_acceptance_implementation`

执行者没有偏离主线，也没有新增分支：

- 本轮只做了浏览器只读验收入口方案设计。
- 未修改前端代码。
- 未修改后端代码。
- 未修改测试代码。
- 未新增 route。
- 未新增 API。
- 未新增数据源。
- 未训练模型。
- 未触发 provider refresh/publish。
- 未切换 accepted latest。
- 未触发 monitor config save、monitor scan、alerts write。
- 未接 broker、quick-trade、orders。
- 未实现上下文字段映射。
- 未输出买卖、仓位、收益或概率语义。

R6 推荐方案为“测试专用 query flag / test-only mode 挂载 manual-review 最小区块 + Playwright 严格网络计数审计”。该方向符合 R6 授权，允许进入 R7 的最小实现阶段。

## 2. 主线一致性审查

R6 延续了 R5 留下的问题：现有 `/tw-stock-monitor` 整页挂载会触发既有 `POST /api/tw-stock/rank-tech-cross/portfolio-replay`，导致无法证明 manual-review 浏览器链路本身是只读。

R6 没有把问题扩展为：

- 新页面产品化。
- 完整上下文字段映射。
- 复盘解释能力增强。
- 数据源补齐。
- 模型训练。
- provider/accepted latest 操作。
- monitor 自动化。
- 交易路径。

方案核心是让 R7 能在浏览器中单独验收 manual-review 区块，并得到可审计的 network 证据。这条线仍是“验收入口补齐”，不是业务能力扩展。

## 3. 用户第一性原则审查

通过。

- 简单：方案避免把整页复杂挂载链路带入 manual-review 验收。
- 准确：要求 R7 用 network 计数证明无危险请求，不接受口头说明。
- 清晰：区分了 allowlist、denylist、候选方案和停止条件。
- 实用：R7 执行者可以直接按推荐方案落地只读 smoke。

需要在 R7 继续保持：浏览器验收页面或测试模式不得变成面向用户的新说明页，不得增加复杂调试 UI。

## 4. 浏览器 / Network 审查

R6 未执行浏览器，原因合理：R6 只授权方案设计，不授权实现 smoke。

R6 方案已明确 R7 必须统计：

- `forbidden_request_count=0`
- `manual_review_get_count>=1`
- `portfolio_replay_post_count=0`
- `monitor_config_write_count=0`
- `monitor_scan_post_count=0`
- `monitor_alerts_write_count=0`
- `provider_or_accepted_latest_write_count=0`
- `broker_quick_trade_order_count=0`
- `unsafe_trading_semantics_count=0`

R7 必须额外注意一条硬约束：

危险请求不能通过 Playwright `abort`、`fulfill`、mock 或 intercept 处理后算作通过。只要浏览器发出危险请求，就必须计数并失败。Mock 只允许用于 manual-review GET 的稳定展示，不能用于隐藏非 manual-review 写请求。

## 5. 台股只读安全边界审查

### Findings

- Critical：无。
- High：无。
- Medium：无。
- Low：R6 未产生运行时 network artifact，原因符合阶段授权，不阻塞通过。

### Network Audit

未执行浏览器 network audit。R6 方案文档提供了 R7 的 allowlist、denylist 和计数 gate。

### Console Audit

未执行浏览器 console audit。R7 必须补齐 console error/warning 摘要。

### Text / Agent Semantics

R6 文档中出现 `买入`、`卖出`、`持有`、`收益`、`上涨概率`、`provider`、`accepted latest`、`broker`、`orders` 等词，仅用于禁止事项、denylist 和安全边界说明，不构成交易建议或动作入口。

### Verdict

只读研究安全边界通过。

## 6. 必须修复项

当前 R6 无必须修复项。

## 7. R7 必须收紧项

R7 实现时必须收紧以下细节：

- Query flag/test-only mode 只能影响测试 URL，默认 `/tw-stock-monitor` 行为不得改变。
- 不得新增后端 route 或业务 API。
- 不得新增用户导航入口。
- 不得把测试入口包装成用户可见的新产品页或调试台。
- 不得实现上下文字段映射。
- 不得使用新数据源、联网、token、模型训练、provider、accepted latest、monitor 写入或交易路径。
- 如使用 fixture/mock，只能服务于 `GET /api/tw-stock/manual-review/explanation` 的稳定展示。
- 任意台股业务 POST/PUT/PATCH/DELETE 只要发出就失败，不能被拦截后忽略。

## 8. 是否需要用户确认

不需要额外用户确认。

R6 已获得用户授权进入只读浏览器验收方向；R7 仅实现该验收入口与 smoke，不进入字段映射或业务增强。

## 9. 给执行者的下一步工作文档

### Phase R7：实现 manual-review 浏览器只读验收

你是执行者。本轮只允许实现 R6 已通过的浏览器只读验收入口和 Playwright smoke。

#### 目标

建立一个可审计的 manual-review 专用浏览器只读验收：

- 浏览器能渲染 manual-review 最小区块。
- 能看到 `复盘线索` 或等价的人工复盘解释内容。
- 页面会调用 `GET /api/tw-stock/manual-review/explanation`。
- 不触发 portfolio replay POST。
- 不触发任何台股业务写请求。
- 不出现买卖、仓位、收益、概率或胜率语义。

#### 允许修改

允许做最小实现：

- 在现有前端中加入测试专用 query flag / test-only mode，使测试 URL 只挂载 manual-review 最小区块或最小容器。
- 新增 Playwright readonly smoke。
- 新增 network audit summary artifact。
- 新增 R7 执行报告。
- 如确需稳定展示，可为 `GET /api/tw-stock/manual-review/explanation` 使用 fixture/mock response。

允许新增的建议文件：

- `frontend/tests/e2e/tw-stock-manual-review-readonly.mjs`
- `docs/tw_manual_review_explanation/PHASER7_EXECUTION_REPORT_CN.md`

如项目已有 E2E artifact 目录或命名规范，应沿用现有规范；不要为了本轮建立复杂新框架。

#### 禁止事项

本轮禁止：

- 新增后端 route。
- 新增业务 API。
- 新增用户可见导航入口。
- 新增复杂调试页面。
- 修改真实 `/tw-stock-monitor` 默认挂载行为。
- 禁用既有真实业务功能。
- 实现上下文字段映射。
- 新增数据源。
- 联网或使用 token，除本地前后端测试服务外。
- 训练模型。
- provider refresh/publish。
- accepted latest switching。
- materialize 到 qlib。
- monitor config save。
- monitor scan 或 scan-all。
- alerts write。
- broker、quick-trade、orders。
- target position 或 target weight。
- 买入、卖出、持有建议。
- 仓位建议、收益承诺、上涨概率或胜率承诺。

#### Network 审计要求

R7 必须记录浏览器发出的所有请求，并在报告中给出请求清单或 artifact 路径。

允许请求原则：

- `GET /api/tw-stock/manual-review/explanation`
- 前端静态资源。
- 必要的只读 bootstrap/auth GET；如出现，必须逐条说明。

危险请求必须失败，至少包括：

- 任意台股业务 `POST`、`PUT`、`PATCH`、`DELETE`。
- `POST /api/tw-stock/rank-tech-cross/portfolio-replay`
- `POST /api/tw-stock/monitor/config`
- `POST /api/tw-stock/monitor/scan`
- `POST /api/tw-stock/monitor/scan-all`
- `POST /api/tw-stock/monitor/alerts`
- `PUT/PATCH/DELETE /api/tw-stock/monitor/alerts/*`
- `POST /api/tw-stock/quant/ops/**`
- 任意 provider refresh/publish 请求。
- 任意 accepted latest switching 请求。
- `POST /api/quick-trade/**`
- 任意 `/api/broker/**`
- 任意包含 `order` 的业务请求。
- 任意包含 `target-position` 或 `target_weight` 的业务请求。

硬约束：危险请求只要由浏览器发出，即使被 Playwright 拦截、abort、fulfill 或 mock，也必须计数为失败。

#### R7 必跑验证

至少执行：

- manual-review 前端专项静态检查，如 `node frontend/tests/unit/tw-stock-manual-review-explanation-check.mjs`
- 全页台股 monitor 静态检查，如 `node frontend/tests/unit/tw-stock-monitor-static-check.mjs`
- 新增 Playwright readonly smoke
- 如本轮改动会影响构建，执行 `corepack pnpm build`，工作目录 `frontend`

如果 Playwright 需要本地前后端服务：

- 只能启动本地测试服务。
- 不得触发真实数据刷新。
- 不得触发 provider/accepted latest/monitor/交易路径。
- 报告中写清服务启动方式、URL 和退出状态。

#### R7 报告要求

新增：

- `docs/tw_manual_review_explanation/PHASER7_EXECUTION_REPORT_CN.md`

报告必须包含：

- 当前阶段目标。
- 修改文件清单。
- 是否修改前端默认行为。
- 是否新增后端 route/API。
- 浏览器测试 URL。
- network 请求清单或 artifact 路径。
- console 摘要。
- 页面截图或文本摘要。
- 验证命令与结果。
- 用户第一性原则自查。
- 安全边界自查。
- 是否偏离主线。
- 是否新增分支。
- 推荐 gate。

R7 报告必须显式给出：

- `forbidden_request_count`
- `manual_review_get_count`
- `portfolio_replay_post_count`
- `monitor_config_write_count`
- `monitor_scan_post_count`
- `monitor_alerts_write_count`
- `provider_or_accepted_latest_write_count`
- `broker_quick_trade_order_count`
- `unsafe_trading_semantics_count`

#### R7 Gate

R7 通过时建议 gate：

`manual_review_browser_readonly_acceptance_passed`

R7 需要修复时：

`phaser7_browser_readonly_acceptance_needs_repair`

如发现范围越权：

`stop_manual_review_next_round_scope_invalid`

#### 必须停下来讨论的情况

出现以下任一情况，立即停止：

- 必须新增后端 route 或业务 API。
- 必须改动真实页面默认挂载逻辑。
- 必须禁用既有业务功能才能通过测试。
- 浏览器仍发出 portfolio replay POST。
- 浏览器发出任意台股业务写请求。
- 需要联网、token、数据刷新、provider/accepted latest、monitor 写入或交易路径。
- 需要同时实现上下文字段映射。
- 页面或报告出现交易建议、仓位建议、收益承诺、上涨概率或胜率承诺。
