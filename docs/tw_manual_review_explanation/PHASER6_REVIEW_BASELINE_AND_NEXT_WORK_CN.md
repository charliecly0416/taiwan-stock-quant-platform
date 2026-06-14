# Phase R6 审查基线与下一步工作文档

审查日期：2026-06-12

审查入口：

- `docs/TW_STOCK_MANUAL_REVIEW_EXPLANATION_NEXT_ROUND_PLAN_CN.md`
- `docs/tw_manual_review_explanation/NEXT_ROUND_REVIEWER_PROMPT_CN.md`
- `docs/tw_manual_review_explanation/PHASER5_FINAL_CLOSURE_REVIEW_CN.md`
- 台股只读安全边界审查规则

## 1. 当前基线结论

人工复盘解释模块 R0-R5 已收口，当前状态保持：

- `manual_review_explanation_module_acceptance_passed=true`
- `manual_review_explanation_closure_smoke_passed=true`
- `manual_review_handoff_done=true`
- `manual_review_mainline_closed=true`

R5 接受未执行浏览器 smoke 的原因：现有 `/tw-stock-monitor` 页面挂载链路会触发既有 `POST /api/tw-stock/rank-tech-cross/portfolio-replay`，该 POST 不是 manual-review 新增能力，但会干扰“只读浏览器验收”的网络审计。

因此，下一轮不能直接补跑浏览器 smoke，必须先设计一个干净、可审计、只覆盖 manual-review 模块的浏览器验收入口。

## 2. Phase R6 授权范围

Phase R6 只允许执行者做一件事：

设计 manual-review 专用浏览器只读验收入口方案。

本轮应保持 doc-only。允许：

- 阅读现有 manual-review API、前端挂载、测试与 R5 收口材料。
- 盘点现有页面为什么会触发 portfolio replay POST。
- 对比 2-3 种只读浏览器验收入口方案。
- 推荐一个最小、清晰、可审计的方案。
- 写出危险请求 denylist、允许请求 allowlist、验收 gate 与后续 R7 实现边界。
- 产出方案文档和执行报告。

本轮不授权实现。

## 3. Phase R6 禁止范围

执行者不得在 R6 做以下任何事项：

- 不实现上下文字段映射。
- 不新增、修改或接入新数据源。
- 不联网拉数据，不使用 token。
- 不训练模型。
- 不修改 qlib provider。
- 不触发 provider refresh/publish。
- 不切换 accepted latest。
- 不保存 monitor config。
- 不触发 monitor scan 或 scan-all。
- 不写 alerts。
- 不接 broker、quick-trade、orders。
- 不新增 target position 或 target weight 语义。
- 不输出买卖建议、仓位建议、收益承诺、上涨概率或胜率承诺。
- 不新增用户可见的复杂调试页面。
- 不为了测试禁用真实业务功能。
- 不修改前端、后端、API 或 Playwright 实现，除非先回到审查者并取得下一阶段授权。

如果执行者认为“不改代码无法设计清楚”，也只能在方案里列出建议，不得直接实现。

## 4. 用户第一性原则

R6 方案必须服务于“简单、准确、清晰、实用”：

- 简单：验收入口只验证 manual-review，不把整页复杂挂载链路带进来。
- 准确：网络审计要能证明没有危险写请求，不能用口头保证代替证据。
- 清晰：明确哪些请求允许、哪些请求必须拦截、哪些行为属于越权。
- 实用：R7 执行者拿到方案后，可以直接实现浏览器只读 smoke，而不用重新判断边界。

方案不能把问题扩展成新页面产品设计、数据增强、模型增强或交易闭环。

## 5. 浏览器与 Network 安全边界

R6 方案必须包含危险请求 denylist，至少覆盖：

- 任意 `POST`、`PUT`、`PATCH`、`DELETE`，除非方案明确说明是本地测试服务启动或静态资源加载之外的非业务请求；对台股业务 API 默认禁止。
- `POST /api/tw-stock/monitor/config`
- `POST /api/tw-stock/monitor/scan`
- `POST /api/tw-stock/monitor/scan-all`
- `POST /api/tw-stock/monitor/alerts`
- `PUT/PATCH/DELETE /api/tw-stock/monitor/alerts/*`
- `POST /api/tw-stock/quant/ops/**`
- 任意 provider refresh/publish/accepted latest 相关请求。
- `POST /api/quick-trade/**`
- 任意 `/api/broker/**`
- 任意包含 `order` 的业务请求。
- 任意包含 `target-position` 或 `target_weight` 的业务请求。
- 既有 `POST /api/tw-stock/rank-tech-cross/portfolio-replay`，在本次 manual-review 只读 smoke 中必须避免或拦截。

R6 方案必须定义允许请求 allowlist，建议仅包含：

- `GET /api/tw-stock/manual-review/explanation`
- 前端静态资源请求。
- 已有应用启动所需的只读 bootstrap/auth GET 请求；如确有需要，必须逐项说明为什么属于只读、为什么不会触发台股业务写入。

R6 方案必须要求 R7 的最终浏览器验收产物能报告：

- `forbidden_request_count=0`
- `manual_review_get_count>=1`
- `portfolio_replay_post_count=0`
- `monitor_config_write_count=0`
- `monitor_scan_post_count=0`
- `monitor_alerts_write_count=0`
- `provider_or_accepted_latest_write_count=0`
- `broker_quick_trade_order_count=0`
- `unsafe_trading_semantics_count=0`

## 6. R6 方案必须比较的候选路径

执行者至少比较以下三类方案，允许补充但不得扩展业务目标：

1. Query flag 或测试模式挂载
   - 只在测试参数存在时挂载 manual-review 区块。
   - 必须说明是否会影响真实页面逻辑。
   - 必须说明如何避免 portfolio replay POST。

2. 专用只读测试 route
   - 只用于开发/测试环境，不作为用户入口宣传。
   - 页面只承载 manual-review 组件或最小容器。
   - 必须说明如何避免新增复杂调试产品。

3. Playwright route mock/intercept
   - 在 E2E 中拦截非 manual-review 请求。
   - 必须说明拦截是为了安全审计，不是掩盖真实危险请求。
   - 必须说明如何区分“主动发出了危险请求但被拦截”和“根本没有触发危险请求”。

每个方案必须写：

- 变更面。
- 用户可见性。
- 网络请求面。
- 安全风险。
- 是否需要前端改动。
- 是否需要后端改动。
- 是否能证明只测 manual-review。
- 是否适合进入 R7。

执行者必须推荐一个最小方案，并说明为什么不选择其他方案。

## 7. R6 交付物要求

执行者本轮必须产出：

- `docs/tw_manual_review_explanation/manual_review_browser_readonly_acceptance_plan.md`
- `docs/tw_manual_review_explanation/PHASER6_EXECUTION_REPORT_CN.md`

`manual_review_browser_readonly_acceptance_plan.md` 必须包含：

- 背景问题：为什么 R5 不直接做浏览器 smoke。
- 目标：只验证 manual-review 浏览器入口。
- 非目标：不做字段映射、不做数据源、不做模型、不做 provider/accepted latest、不做 monitor 写入、不做交易路径。
- 候选方案对比。
- 推荐方案。
- network allowlist。
- dangerous request denylist。
- R7 实现边界。
- R7 验收 gate。
- 必须停下来问审查者或用户的情况。

`PHASER6_EXECUTION_REPORT_CN.md` 必须包含：

- 本轮阅读材料。
- 本轮是否修改代码；预期答案应为否。
- 本轮新增/修改文档清单。
- 推荐方案摘要。
- 是否偏离主线。
- 是否新增分支。
- 安全边界自查。
- 给审查者的结论与 gate 建议。

## 8. 必须停下来讨论的情况

出现以下任一情况，执行者必须停止，不得自行继续：

- 认为必须新增前端 route、API route 或 Playwright 测试代码才能完成 R6。
- 方案需要真实联网、token、拉取数据或更新本地数据。
- 方案涉及 provider refresh/publish 或 accepted latest。
- 方案涉及 monitor config save、monitor scan、alerts write。
- 方案涉及 broker、quick-trade、orders。
- 方案需要引入买卖、仓位、收益、概率或胜率语义。
- 方案试图同时开启上下文字段映射。
- 方案需要改动真实页面业务逻辑或禁用既有业务功能。
- 方案变成“新产品页”或复杂调试台。

## 9. 本轮 Gate

R6 审查通过的唯一可接受 gate：

`request_phaser7_browser_readonly_acceptance_implementation`

R6 不通过时使用：

`phaser6_acceptance_plan_needs_repair`

如发现范围越权，使用：

`stop_manual_review_next_round_scope_invalid`

## 10. 给执行者的下一步工作文档

### Phase R6：浏览器只读验收入口方案设计

你是执行者。本轮只设计方案，不实现代码。

请完成：

1. 阅读 `docs/TW_STOCK_MANUAL_REVIEW_EXPLANATION_NEXT_ROUND_PLAN_CN.md`、`docs/tw_manual_review_explanation/NEXT_ROUND_EXECUTOR_PROMPT_CN.md`、`docs/tw_manual_review_explanation/PHASER5_FINAL_CLOSURE_REVIEW_CN.md` 和本文件。
2. 盘点 R5 为什么不能直接做浏览器 smoke，重点说明既有 portfolio replay POST 对只读验收的干扰。
3. 设计 manual-review 专用浏览器只读验收入口方案。
4. 至少比较 query flag/test-only mode、专用只读测试 route、Playwright route mock/intercept 三类方案。
5. 推荐一个最小、清晰、可审计的 R7 实现方案。
6. 写出 network allowlist、dangerous request denylist 和 R7 验收 gate。
7. 输出：
   - `docs/tw_manual_review_explanation/manual_review_browser_readonly_acceptance_plan.md`
   - `docs/tw_manual_review_explanation/PHASER6_EXECUTION_REPORT_CN.md`

本轮不要修改业务代码、测试代码、前端 route、后端 API 或数据文件。不要实现上下文字段映射。不要触发任何数据刷新、provider/accepted latest、monitor 写入或交易相关路径。

完成后，在执行报告中明确建议 gate：

- 若方案可进入实现：`request_phaser7_browser_readonly_acceptance_implementation`
- 若方案仍需修复：`phaser6_acceptance_plan_needs_repair`
- 若发现当前目标本身需要越权：`stop_manual_review_next_round_scope_invalid`
