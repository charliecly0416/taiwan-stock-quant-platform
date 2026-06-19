# Phase R6 执行报告：Manual Review 浏览器只读验收入口方案

- 执行日期：2026-06-12
- 当前阶段：Phase R6
- recommended_gate：`request_phaser7_browser_readonly_acceptance_implementation`

## 1. 当前阶段目标

本阶段只设计 manual-review 专用浏览器只读验收入口方案，解决 R5 因现有 `/tw-stock-monitor` 挂载触发 `POST /api/tw-stock/rank-tech-cross/portfolio-replay` 而无法直接做严格只读浏览器 smoke 的问题。

本阶段不实现代码。

## 2. 本轮阅读材料

已阅读：

- `docs/TW_STOCK_MANUAL_REVIEW_EXPLANATION_MODULE_PLAN_CN.md`
- `docs/TW_STOCK_MANUAL_REVIEW_EXPLANATION_NEXT_ROUND_PLAN_CN.md`
- `docs/tw_manual_review_explanation/EXECUTOR_PROMPT_CN.md`
- `docs/tw_manual_review_explanation/NEXT_ROUND_EXECUTOR_PROMPT_CN.md`
- `docs/tw_manual_review_explanation/PHASER5_CLOSURE_SMOKE_REPORT_CN.md`
- `docs/tw_manual_review_explanation/PHASER5_FINAL_CLOSURE_REVIEW_CN.md`
- `docs/tw_manual_review_explanation/MANUAL_REVIEW_EXPLANATION_HANDOFF_CN.md`
- `docs/tw_manual_review_explanation/PHASER6_REVIEW_BASELINE_AND_NEXT_WORK_CN.md`

## 3. 执行范围

本轮完成：

- 复核 R5 未执行浏览器 smoke 的原因。
- 对比三类浏览器只读验收入口方案。
- 推荐一个最小、清晰、可审计的 R7 实现方案。
- 定义 R7 network allowlist。
- 定义 dangerous request denylist。
- 定义 R7 验收 gate。
- 输出 R6 方案文档和执行报告。

本轮未做：

- 未修改前端代码。
- 未修改后端代码。
- 未修改测试代码。
- 未新增 route。
- 未新增 API。
- 未新增数据源。
- 未训练模型。
- 未触发 provider/accepted latest。
- 未触发 monitor 写入或扫描。
- 未触发 broker、quick-trade、orders。
- 未实现上下文字段映射。

## 4. 新增/修改文件

新增文档：

- `docs/tw_manual_review_explanation/manual_review_browser_readonly_acceptance_plan.md`
- `docs/tw_manual_review_explanation/PHASER6_EXECUTION_REPORT_CN.md`

业务代码修改：无。

测试代码修改：无。

数据文件修改：无。

## 5. 推荐方案摘要

推荐 R7 使用：

> 测试专用 query flag / test-only mode 挂载 manual-review 最小区块，并由 Playwright 记录所有请求，用 allowlist/denylist 做严格计数审计。

选择原因：

- 不挂载会触发 portfolio replay 的整页链路。
- 不新增后端 API。
- 不新增用户可见产品入口。
- 可以证明 manual-review 浏览器验收只需要 `GET /api/tw-stock/manual-review/explanation`。
- 可以要求危险请求只要发出就失败，而不是被 mock/intercept 掩盖。

未推荐专用只读测试 route 的原因：

- 变更面更大，容易被误解为新增用户入口或复杂调试页面。

未推荐纯 Playwright route mock/intercept 的原因：

- 它可以拦截危险请求，但不能证明页面没有主动发出危险请求。

## 6. R7 建议验收指标

R7 最终报告必须满足：

- `forbidden_request_count=0`
- `manual_review_get_count>=1`
- `portfolio_replay_post_count=0`
- `monitor_config_write_count=0`
- `monitor_scan_post_count=0`
- `monitor_alerts_write_count=0`
- `provider_or_accepted_latest_write_count=0`
- `broker_quick_trade_order_count=0`
- `unsafe_trading_semantics_count=0`

## 7. 验证命令

本阶段为 doc-only，未运行前端、后端、Playwright 或 build。

已执行的只读检查：

- `sed -n` 阅读本阶段必读文档。
- `ls -la docs/tw_manual_review_explanation`
- `git status --short docs/tw_manual_review_explanation`

## 8. 浏览器 / Network 审查结果

本阶段未执行浏览器。

原因：R6 只授权方案设计，不授权实现浏览器 smoke 或修改测试入口。

方案文档已定义 R7 需要执行的 network allowlist、dangerous request denylist 和固定计数 gate。

## 9. 用户第一性原则自查

- 简单：推荐方案只验收 manual-review 最小区块，不把整页历史模拟链路带入验收。
- 准确：要求 R7 用 network 计数证明没有危险请求，不用口头保证替代证据。
- 清晰：方案明确了允许请求、禁止请求、候选路径差异和停下来讨论的条件。
- 实用：R7 执行者可直接按方案实现 readonly smoke 和报告指标。

## 10. 安全边界自查

本轮没有触发或实现：

- 新数据源。
- 联网或 token。
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

文档中出现这些词仅用于 denylist、非目标和安全边界说明，不构成实现或入口。

## 11. 是否偏离主线 / 是否新增分支

未偏离主线。

未新增分支。

本轮只围绕审查者授权的“manual-review 浏览器只读验收入口方案设计”展开，没有进入上下文字段映射、模型、新数据源、provider、monitor 或交易路径。

## 12. 风险与待审查问题

- R7 若实现 query flag / test-only mode，需要审查它是否只影响测试 URL，不改变真实 `/tw-stock-monitor` 默认行为。
- R7 若为了稳定展示使用 fixture 或 mock response，需要审查 mock 只服务于 manual-review GET，不掩盖任何危险请求。
- R7 需要严格区分“危险请求未发出”和“危险请求发出后被拦截”。推荐 gate 应以前者为通过条件。

## 13. 给审查者的结论

R6 已完成 doc-only 方案设计。

建议进入下一阶段：

`request_phaser7_browser_readonly_acceptance_implementation`

