# Phase UI2-D 审查报告：响应式与 Playwright 只读验收

生成日期：2026-06-19

## 1. 审查结论

审查结论：通过。

UI2-D 已完成响应式与 Playwright 只读验收：desktop/tablet/mobile 三个视口均无横向溢出，主界面必需文案齐全，技术详情默认折叠，network audit 与 console/page audit 均通过，未发现真实交易、券商、quick-trade、order、target position/weight、provider publish/refresh、accepted latest 切换或 monitor 写入请求。

本轮 Phase UI2 可以收口。

## 2. 审查范围

本次审查：

```text
docs/tw_modular_daily_update_productization/PHASEUI2D_RESPONSIVE_PLAYWRIGHT_ACCEPTANCE_EXECUTION_REPORT_CN.md
docs/tw_modular_daily_update_productization/PHASEUI2_STRATEGY_WORKBENCH_AGENT_UX_EXECUTION_REPORT_CN.md
frontend/tests/e2e/tw-stock-strategy-workbench-ux-readonly.mjs
tmp/tw_ui2d_workbench_acceptance/audit.json
tmp/tw_ui2d_workbench_acceptance/network_audit.json
tmp/tw_ui2d_workbench_acceptance/console_audit.json
tmp/tw_ui2d_workbench_acceptance/desktop.png
tmp/tw_ui2d_workbench_acceptance/tablet.png
tmp/tw_ui2d_workbench_acceptance/mobile.png
```

并复核相关静态检索与 frontend build。

## 3. Playwright 产物核对

产物存在：

```text
tmp/tw_ui2d_workbench_acceptance/desktop.png
tmp/tw_ui2d_workbench_acceptance/tablet.png
tmp/tw_ui2d_workbench_acceptance/mobile.png
tmp/tw_ui2d_workbench_acceptance/audit.json
tmp/tw_ui2d_workbench_acceptance/network_audit.json
tmp/tw_ui2d_workbench_acceptance/console_audit.json
```

当前对话环境的 `view_image` 仍受 bwrap 限制：

```text
bwrap: loopback: Failed RTM_NEWADDR: Operation not permitted
```

因此无法在对话内直接打开 PNG 做人工视觉确认。该限制与执行报告描述一致。审查已改用以下证据补强：

- PNG 文件存在且为非空大文件。
- Playwright 脚本包含 `page.screenshot({ fullPage: true })`。
- `audit.json` 覆盖三视口 DOM 溢出、按钮溢出、必需文案、禁显文案和技术详情折叠。
- 脚本末尾包含断言，任何关键指标失败都会让脚本失败。

该项列为低风险残留，不阻塞通过。

## 4. UX / 响应式审查

`audit.json` 显示：

```text
desktop overflowX=false
tablet overflowX=false
mobile overflowX=false
required_text_passed=true
forbidden_visible_passed=true
button_overflow_passed=true
technical_details_default_collapsed=true
```

三个视口均未缺失：

```text
今日策略总览
候选名单
历史模拟
模拟账户状态
策略解释助手
不构成交易建议
不连接券商
不提交真实订单
```

主界面未常显：

```text
统一策略上下文
YZ Clean E4 产品化
clean registry
execution_price_mode: next_open
只展示 Model A / Model B
paper_order_intent_artifact_path
ReplayWindowPolicy
final equity
turnover_proxy_by_notional_over_avg_equity
```

符合 UI2-D 验收要求。

## 5. Network Audit

`network_audit.json`：

```text
request_count=64
simple_chat_request_count=1
forbidden_request_count=0
forbidden_requests=[]
suspicious_requests=[]
monitor_config_write_count=0
monitor_scan_post_count=0
monitor_alerts_write_count=0
ops_dry_run_post_count=0
failed_response_count=0
```

唯一允许的 POST 是：

```text
POST /api/tw-stock/agent/simple-chat
```

Playwright 脚本断言该 payload 只包含：

```text
为什么模拟账户不能应用？
```

并明确断言不含：

```text
target_position
target_weight
```

未发现 provider refresh/publish、accepted latest 切换、monitor 写入、broker、quick-trade、order 或 target position/weight 写入。

## 6. Console / Page Audit

`console_audit.json`：

```text
console_error_count=0
page_error_count=0
console_messages=[]
console_errors=[]
page_errors=[]
```

通过。

## 7. 静态检索复核

已复核安全语义检索：

```bash
rg -n "建议买入|建议卖出|目标仓位|目标权重|保证收益|上涨概率|自动下单|quick-trade|broker|order submit|target_position|target_weight|provider publish|accepted latest|monitor scan|monitor alerts|连接券商|提交真实订单" frontend/src/views/tw-stock-monitor frontend/src/api/tw-stock.js
```

命中归因：

- `不连接券商`、`不提交真实订单`：安全声明或二次确认。
- `not_target_position`：readonly safety flag。
- `connects_to_broker=false`、`orders_enabled=false`：只读边界 flags。
- `accepted latest`：既有数据状态说明。
- `writes_orders` / `writes_positions`：只读边界检查字段，不是写入口。

未发现交易建议、真实交易入口、自动下单、目标仓位/目标权重指令、收益承诺或上涨概率承诺。

已复核主路径内部字段检索：

```bash
rg -n "统一策略上下文|YZ Clean E4 产品化|clean registry|execution_price_mode: next_open|只展示 Model A / Model B|paper_order_intent_artifact_path|ReplayWindowPolicy|final equity|turnover_proxy_by_notional_over_avg_equity" frontend/src/views/tw-stock-monitor
```

命中归因：

- `paper_order_intent_artifact_path`：源码 DTO、API payload 或 `查看模拟账户技术详情`。
- `turnover_proxy_by_notional_over_avg_equity`：源码映射或技术详情。
- 未发现旧工程标题或禁显字段主路径常显。

## 8. Frontend Build

已重新运行：

```bash
cd frontend && corepack pnpm build
```

结果：通过，退出码 0。

构建开始处仍有既有 shell 初始化提示：

```text
/bin/sh: 2: source: not found
```

未阻断 Vite build。

## 9. 台股只读安全边界审查

### Findings

Critical：无。

High：无。

Medium：无。

Low：

1. 当前对话环境无法通过 `view_image` 内联查看 PNG 截图；已通过文件存在、Playwright DOM audit、脚本断言和 JSON 产物复核降低风险。

### Network Audit

通过。`forbidden_request_count=0`，monitor config/scan/alerts 写入计数均为 0，`ops_dry_run_post_count=0`。

### Console Audit

通过。console/page error 均为 0。

### Text / Agent Semantics

Agent 标题为 `策略解释助手`，推荐问题聚焦策略、候选、调出复核、模拟账户阻断原因和数据新鲜度。未出现买哪只、买多少、胜率、上涨概率、目标仓位等交易助手问题。

## 10. 审查结论

UI2-D 通过，Phase UI2 可最终接受。

当前 `/tw-stock-monitor` 已满足本轮目标：

- 首屏从工程调试对象收敛为 `今日策略总览`。
- 候选名单以股票和排名为主。
- 历史模拟不承诺未来收益。
- 模拟账户明确只影响模拟账户，不连接券商，不提交真实订单。
- Agent 是策略解释助手，不是交易助手。
- 技术详情仍可查，但默认折叠。
- desktop/tablet/mobile Playwright DOM audit 通过。
- network/console/page audit 通过。
- 未改模型、策略、回放算法、日更真实链路或交易边界。
