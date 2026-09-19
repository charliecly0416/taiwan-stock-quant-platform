# POLICY DAOV6: TW Stock Monitor Compact Surface And Status Export

route: DAOV_TW_STOCK_MONITOR_COMPACT_SURFACE_AND_STATUS_EXPORT
owner: coordinator
status: OPEN
created_at_utc: 2026-08-20
language: zh-CN
production_allowed: false
provider_pull_allowed: false
provider_publish_allowed: false
qlib_refresh_allowed: false
latest_pointer_write_allowed: false
cron_edit_allowed: false
daily_auto_manual_run_allowed: false
openai_call_allowed: false
db_write_allowed: false
monitor_write_allowed: false
broker_order_allowed: false
target_output_allowed: false

## 1. Goal

DAOV6 的目标是把 `/tw-stock-monitor` 从“功能完整但长页面”收敛成“首屏更紧凑、分区更清楚、只读摘要可导出”的研究工作台。

用户第一性原则：

- 清晰：打开页面先知道现在是什么状态，维护区在哪里，哪些是只读。
- 准确：展示内容继续只读读取现有 API / artifact，不引入猜测、fixture 代替或写入路径。
- 简单：首屏优先给出最重要的状态摘要，再给研究功能。
- 实用：支持快速跳转、快速对照和只读摘要导出，方便日常复盘和交接。

## 2. Non-goals

本路线不授权：

- provider pull / refresh / publish；
- qlib refresh；
- accepted latest switch；
- controlled signal / readonly snapshot / Agent prompt publish；
- protected latest pointer write；
- daily auto manual run；
- cron edit；
- OpenAI 调用；
- DB 写入；
- monitor / broker / order / target 输出；
- frontend/API production default switch；
- 新模型训练、新策略上线、新回测扩展。

## 3. Current Baseline / Facts

当前基线：

- `/tw-stock-monitor` 已可用，且包含数据链路状态、策略总览、readonly snapshot、回放、Qlib 研究排名、交叉分析、Agent 解释与监控相关只读面板。
- 当前首屏功能完整，但页面较长，维护性内容与研究主流程同页并列，用户需要较多滚动才能建立全局判断。
- 只读 ops status 已经存在，可继续作为首屏状态事实来源。

## 4. Required Prior Documents

执行者和审查者必须读取：

- `docs/tw_portfolio_decision_model/POLICY_DAOV_DAILY_AUTO_OPS_VISIBILITY_FRONTEND_READINESS_MAINLINE_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_DAOV4_CLOSURE_AND_OPS_HANDOFF_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_DAOV5_LIVE_FRESHNESS_REVALIDATION_AND_OPS_SURFACE_CHECK_MAINLINE_CN.md`
- `docs/tw_portfolio_decision_model/POLICY_DAOV5_LIVE_FRESHNESS_REVALIDATION_AND_OPS_SURFACE_CHECK_REVIEW_CN.md`
- `backend/app/services/tw_stock_readonly_ops_status.py`
- `backend/app/routes/tw_stock.py`
- `frontend/src/views/tw-stock-monitor/index.vue`
- `frontend/src/api/tw-stock-readonly.js`
- `frontend/tests/unit/tw-stock-monitor-static-check.mjs`
- `frontend/tests/unit/tw-stock-daily-auto-update-panel-check.mjs`

## 5. Required Skills / Specialist Workflows

- `coordinator-executor-reviewer-workflow`
- `tw-stock-frontend-workbench-ux-review`
- `tw-stock-data-freshness-diagnosis`
- `tw-stock-readonly-e2e-acceptance`
- `tw-stock-safety-boundary-review`
- `frontend-design`

## 6. Architecture / Module Boundaries

DAOV6 只允许围绕 `/tw-stock-monitor` 前端 surface 工作：

- 首屏压缩和信息层级重排；
- section rail / anchor jump；
- 只读状态摘要导出；
- 文案收敛；
- 只读空状态 / warning 状态优化；
- frontend static checks / build / readonly acceptance。

不允许触碰：

- 任何数据拉取逻辑；
- provider / qlib / latest pointer / cron 写入；
- broker / order / target / monitor 写入；
- OpenAI 前端直连；
- backend 默认开关。

## 7. Phase Plan

### DAOV6A_COMPACT_FIRST_SCREEN_AND_SECTION_NAVIGATION

实施前端收敛：

- 将首屏状态摘要压缩成更短、更快扫的布局；
- 增加页面内 section rail / anchor jump；
- 把维护型内容更明确地归入高级区域；
- 让页面更像“运维研究工作台”，而不是纯长表单页。

### DAOV6B_READONLY_STATUS_EXPORT

新增只读摘要导出：

- 从现有 readonly payload 生成 client-side 导出；
- 导出的内容必须是纯只读摘要，不包含可执行写入信息；
- 用于日常复盘、交接和故障定位。

### DAOV6C_READONLY_ACCEPTANCE_AND_CLOSURE

运行只读验收：

- frontend static checks；
- frontend build；
- 需要时重新跑 readonly screenshot / network / console audit；
- 审查 forbidden visible/action 边界。

## 8. Per-phase Executor Duties

执行者必须：

- 先读主线和 work doc；
- 只做当前 phase；
- 仅改 `/tw-stock-monitor` 前端展示与只读导出；
- 任何写入或默认 switch 需求都必须停止并报告；
- 写 execution report。

## 9. Per-phase Reviewer Duties

审查者必须：

- 独立读取主线、work doc、execution report；
- 审查用户第一性原则是否真的更清楚；
- 审查只读导出是否没有混入写入语义；
- 审查是否触碰 forbidden action；
- 输出 verdict 和单一下一步。

## 10. Forbidden Actions

整个 DAOV6 禁止：

- real provider pull / refresh / publish；
- qlib refresh；
- accepted latest switch；
- controlled signal / readonly snapshot / Agent prompt publish；
- protected latest pointer write；
- daily auto manual run；
- cron edit；
- OpenAI call；
- DB write；
- monitor config / scan / alerts write；
- broker / quick-trade / order；
- target_position / target_weight；
- frontend/API production default switch。

## 11. Stop Conditions

必须停止并报告：

- 只读导出会变成写入或同步入口；
- 需要 backend contract 改动才能完成前端收敛，而该改动不在本路线内；
- 页面简化会损坏现有只读功能；
- 无法在不引入交易语义的前提下改善信息层级。

## 12. Evidence And Validator Requirements

DAOV6 至少运行：

- `node frontend/tests/unit/tw-stock-monitor-static-check.mjs`
- `node frontend/tests/unit/tw-stock-daily-auto-update-panel-check.mjs`
- `corepack pnpm build`

如果 UI 改动明显，建议补跑：

- readonly Playwright desktop / tablet / mobile screenshots
- network audit
- console audit

## 13. Closure Criteria

DAOV6 通过的标准：

- 首屏更短更快扫；
- 维护项更清楚地归到高级区域；
- 用户能更快理解当前状态和下一步；
- 只读摘要可导出；
- 所有只读边界仍然成立。

## 14. First Executor Command

1. 读取当前 `tw-stock-monitor` 首屏模板与只读导出可行性。
2. 设计 compact surface + section rail + status export 的最小补丁。
3. 仅修改前端展示层与只读导出逻辑。

## 15. First Reviewer Command

审查 DAOV6A / DAOV6B execution report，确认：

- 页面是否更短更快扫；
- 只读导出是否安全；
- 是否需要额外 acceptance；
- 是否可以收口。
