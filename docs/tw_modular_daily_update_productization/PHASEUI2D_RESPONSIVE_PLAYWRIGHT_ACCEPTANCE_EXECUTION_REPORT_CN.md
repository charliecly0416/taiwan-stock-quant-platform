# Phase UI2-D 执行报告：响应式与 Playwright 只读验收

生成日期：2026-06-19

## 1. 改动文件

- `frontend/tests/e2e/tw-stock-strategy-workbench-ux-readonly.mjs`
- `frontend/src/views/tw-stock-monitor/index.vue`
- `frontend/src/views/tw-stock-monitor/components/ReadonlyReplayWindowPanel.vue`
- `frontend/src/views/tw-stock-monitor/components/PaperPortfolioPanel.vue`
- `docs/tw_modular_daily_update_productization/PHASEUI2C_PAPER_PORTFOLIO_AGENT_FUSION_EXECUTION_REPORT_CN.md`
- `docs/tw_modular_daily_update_productization/PHASEUI2_STRATEGY_WORKBENCH_AGENT_UX_EXECUTION_REPORT_CN.md`
- `docs/tw_modular_daily_update_productization/PHASEUI2D_RESPONSIVE_PLAYWRIGHT_ACCEPTANCE_EXECUTION_REPORT_CN.md`

## 2. UI2-C 报告口径修正

已修正 UI2-C 报告中不准确的 `未修改 frontend/src/api/tw-stock.js，未新增 API。` 表述。

当前口径为：

```text
未新增后端 API；前端使用 simpleChatTwStockAgent() helper 调用既有 /agent/simple-chat，用于只读策略解释。
```

## 3. Playwright 启动方式

执行：

```bash
node frontend/tests/e2e/tw-stock-strategy-workbench-ux-readonly.mjs
```

由于当前沙箱运行 Playwright 会触发 `bwrap: loopback: Failed RTM_NEWADDR`，脚本以授权方式在沙箱外运行。脚本使用 fixture/route 拦截 API，不依赖真实后端写接口。

覆盖 URL：

```text
http://127.0.0.1:8000/#/tw-stock-monitor
```

覆盖视口：

- desktop：1440x980
- tablet：1024x768
- mobile：390x900

## 4. Fixture / Route 覆盖说明

脚本拦截：

- auth / settings / policy 基础 GET。
- current strategy context。
- readonly strategy snapshot。
- readonly replay window index/window。
- paper portfolio latest/state/apply-runs。
- agent context。
- `POST /api/tw-stock/agent/simple-chat`。
- qlib health/latest/rank changes/runs。
- daily auto update readonly status。
- cross-analysis / rank-tech readonly endpoints。
- monitor config/history/alerts/scan-logs GET fixture。

唯一允许的 POST：

```text
POST /api/tw-stock/agent/simple-chat
```

该 POST 由点击模拟账户 `解释原因` 触发，payload 仅包含研究解释问题，不含交易执行字段。

## 5. 产物路径

原始产物：

```text
/home/chuliyang/tmp/tw_ui2d_workbench_acceptance/
```

已同步到工作区：

```text
tmp/tw_ui2d_workbench_acceptance/
```

截图：

- `tmp/tw_ui2d_workbench_acceptance/desktop.png`
- `tmp/tw_ui2d_workbench_acceptance/tablet.png`
- `tmp/tw_ui2d_workbench_acceptance/mobile.png`

Audit：

- `tmp/tw_ui2d_workbench_acceptance/audit.json`
- `tmp/tw_ui2d_workbench_acceptance/network_audit.json`
- `tmp/tw_ui2d_workbench_acceptance/console_audit.json`

## 6. UX / 响应式结果

`audit.json` 结果：

```text
desktop overflowX=false
tablet overflowX=false
mobile overflowX=false
required_text_passed=true
forbidden_visible_passed=true
button_overflow_passed=true
technical_details_default_collapsed=true
```

三个视口均检查到主界面必须出现文案：

- 今日策略总览
- 候选名单
- 历史模拟
- 模拟账户状态
- 策略解释助手
- 不构成交易建议
- 不连接券商
- 不提交真实订单

主界面未常显：

- 统一策略上下文
- YZ Clean E4 产品化
- clean registry
- execution_price_mode: next_open
- 只展示 Model A / Model B
- paper_order_intent_artifact_path
- ReplayWindowPolicy
- final equity
- turnover_proxy_by_notional_over_avg_equity

说明：当前环境的 `view_image` helper 也受同一 bwrap 限制，无法在对话内直接打开 PNG；截图文件已生成并可由审查者从上述路径打开。DOM audit 已验证无横向页面溢出、无按钮溢出、技术详情默认折叠。截图预期状态为：desktop 以工作台顺序展示总览/候选/历史模拟/模拟账户/Agent；tablet 无横向溢出；mobile 单列展示，Agent 推荐问题可换行。

## 7. Network Audit

`network_audit.json`：

```text
forbidden_request_count=0
forbidden_requests=[]
suspicious_requests=[]
monitor_config_write_count=0
monitor_scan_post_count=0
monitor_alerts_write_count=0
ops_dry_run_post_count=0
failed_response_count=0
simple_chat_request_count=1
```

未出现 provider refresh / publish、accepted latest 切换、monitor 写入、broker、quick-trade、order 或 target position/weight 写入。

## 8. Console / Page Audit

`console_audit.json`：

```text
console_error_count=0
page_error_count=0
console_messages=[]
page_errors=[]
```

## 9. 静态检索结果与归因

已运行：

```bash
cd frontend && corepack pnpm build
```

结果：通过，退出码 0。构建开始处仍有既有 shell 初始化提示：

```text
/bin/sh: 2: source: not found
```

但 Vite build 成功。

安全语义检索：

```bash
rg -n "建议买入|建议卖出|目标仓位|目标权重|保证收益|上涨概率|自动下单|quick-trade|broker|order submit|target_position|target_weight|provider publish|accepted latest|monitor scan|monitor alerts|连接券商|提交真实订单" frontend/src/views/tw-stock-monitor frontend/src/api/tw-stock.js
```

命中归因：

- `PaperPortfolioPanel.vue` 的 `不连接券商`、`不提交真实订单`：模拟账户安全声明和二次确认。
- `ReadonlyStrategySnapshotPanel.vue` / `index.vue` 的 `not_target_position`：readonly safety flag，用于确认 artifact 不是目标仓位指令。
- `index.vue` 的页面级只读声明、历史模拟声明、`connects_to_broker=false`/flags：安全边界说明。
- `accepted latest`：数据状态说明，不触发 accepted latest 切换。
- `tw-stock.js` 中的写接口 helper 为既有前端 API 定义，UI2-D Playwright 未调用这些 forbidden 写链路。

主路径内部字段检索：

```bash
rg -n "统一策略上下文|YZ Clean E4 产品化|clean registry|execution_price_mode: next_open|只展示 Model A / Model B|paper_order_intent_artifact_path|ReplayWindowPolicy|final equity|turnover_proxy_by_notional_over_avg_equity" frontend/src/views/tw-stock-monitor
```

命中归因：

- `paper_order_intent_artifact_path` 仅出现在源码 DTO、既有 payload 和 `查看模拟账户技术详情`。
- `turnover_proxy_by_notional_over_avg_equity` 出现在历史模拟/策略回放源码映射或技术详情，主路径不常显英文工程字段。
- 无 `统一策略上下文`、`YZ Clean E4 产品化`、`clean registry`、`ReplayWindowPolicy`、`final equity` 主路径命中。

## 10. 只读安全边界审查

Findings：

- Critical：无。
- High：无。
- Medium：无。
- Low：当前环境不能用 `view_image` 内联查看截图，但 PNG 已生成，DOM audit 已覆盖文案、溢出与折叠状态。

Network Audit：通过。

Console Audit：通过。

Text / Agent Semantics：Agent 标题为 `策略解释助手`，推荐问题不包含买哪只、买多少、胜率、上涨概率、目标仓位。simple-chat fixture 回答包含只读声明，不形成交易建议。

Verdict：通过。

## 11. 边界确认

本阶段未修改：

- 后端/API 行为。
- 模型、策略、排序、回放算法。
- 日更真实链路。
- provider refresh / publish。
- accepted latest 切换。
- monitor config / scan / alerts 写入。
- broker / quick-trade / order。
- 真实交易、目标仓位、目标权重语义。
- OpenAI key 读取、传递或前端直连。

## 12. 未解决问题

- 无阻塞问题。
- 截图文件已生成，但当前对话环境无法通过 `view_image` helper 内联查看 PNG；审查者可直接打开产物路径复核。

## 13. 是否建议最终审查通过

建议最终审查通过。UI2-D 的 build、Playwright fixture acceptance、desktop/tablet/mobile 响应式检查、network audit、console audit、静态安全检索均通过。
