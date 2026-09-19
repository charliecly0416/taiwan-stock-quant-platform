# Phase UI2-D 工作文档：响应式与 Playwright 只读验收

生成日期：2026-06-19

## 1. 工作结论

UI2-C 已审查通过，允许进入 UI2-D。

本阶段只做验收与必要的小范围响应式修复，不再扩展产品功能。目标是证明 `/tw-stock-monitor` 已从工程调试面板收敛为可用的台股策略工作台，并且在桌面、平板、手机视口下保持只读安全边界。

## 2. 输入依据

必须遵循：

```text
docs/tw_modular_daily_update_productization/PHASEUI2_STRATEGY_WORKBENCH_AGENT_UX_OPTIMIZATION_PLAN_CN.md
docs/tw_modular_daily_update_productization/PHASEUI2C_PAPER_PORTFOLIO_AGENT_FUSION_REVIEW_CN.md
.agents/skills/frontend-design/SKILL.md
/home/chuliyang/.agents/skills/tw-stock-safety-boundary-review/SKILL.md
```

## 3. 本阶段范围

允许修改：

```text
frontend/src/views/tw-stock-monitor/index.vue
frontend/src/views/tw-stock-monitor/components/ReadonlyStrategySnapshotPanel.vue
frontend/src/views/tw-stock-monitor/components/ReadonlyReplayWindowPanel.vue
frontend/src/views/tw-stock-monitor/components/PaperPortfolioPanel.vue
frontend/tests/e2e/tw-stock-strategy-workbench-ux-readonly.mjs
docs/tw_modular_daily_update_productization/PHASEUI2_STRATEGY_WORKBENCH_AGENT_UX_EXECUTION_REPORT_CN.md
docs/tw_modular_daily_update_productization/PHASEUI2D_RESPONSIVE_PLAYWRIGHT_ACCEPTANCE_EXECUTION_REPORT_CN.md
```

只允许做：

```text
响应式布局修复
文本换行/溢出修复
按钮换行/紧凑化
Playwright 只读 UX/network/console audit
执行报告修正
```

## 4. 严禁事项

不得新增或修改：

```text
后端/API 行为
模型、策略、排序、回放算法
日更真实链路
provider refresh / publish
accepted latest 切换
monitor config / scan / alerts 写入
broker / quick-trade / order
真实交易、目标仓位、目标权重语义
OpenAI key 读取、传递或前端直连
```

不得把 Agent 做成交易助手，不得新增“买哪只、买多少、胜率、上涨概率、目标仓位”等推荐问题。

## 5. 必须修正的报告口径

UI2-C 审查发现执行报告中有一处不准确表述：

```text
未修改 frontend/src/api/tw-stock.js，未新增 API。
```

实际情况是前端存在 `simpleChatTwStockAgent()` helper，并且页面调用已切换到既有 `/agent/simple-chat`。

UI2-D 汇总报告必须修正为：

```text
未新增后端 API；前端 API helper/调用切换到既有 /agent/simple-chat，用于只读策略解释。
```

如该 helper 已是前序阶段产生，也必须在报告中说明当前状态，不得继续写“未修改 API”这类容易误导审查的句子。

## 6. Playwright 验收脚本要求

建议新增：

```text
frontend/tests/e2e/tw-stock-strategy-workbench-ux-readonly.mjs
```

脚本必须使用 fixture/route 拦截 API，不能依赖真实后端写接口，不能触发真实 provider、monitor、broker/order。

覆盖 URL：

```text
http://127.0.0.1:<port>/#/tw-stock-monitor
```

覆盖视口：

```text
desktop: 1440x980
tablet: 1024x768
mobile: 390x900
```

产物建议输出到：

```text
tmp/tw_ui2d_workbench_acceptance/
```

必须输出：

```text
desktop.png
tablet.png
mobile.png
audit.json
network_audit.json
console_audit.json
```

## 7. Network audit 规则

通过条件：

```text
forbidden_request_count=0
forbidden_requests=[]
suspicious_requests=[]
monitor_config_write_count=0
monitor_scan_post_count=0
monitor_alerts_write_count=0
ops_dry_run_post_count=0
failed_response_count=0
```

必须判定为 forbidden 的请求：

```text
POST /api/tw-stock/monitor/config
POST /api/tw-stock/monitor/scan
POST /api/tw-stock/monitor/scan-all
POST /api/tw-stock/monitor/alerts
PUT/PATCH/DELETE /api/tw-stock/monitor/alerts/*
POST /api/tw-stock/quant/ops/** publish/refresh/provider/accepted
POST /api/quick-trade/**
/api/broker/**
真实 order 写入
target-position / target_weight 写入
```

允许：

```text
GET /api/tw-stock/**
fixture-routed readonly status/context APIs
POST /api/tw-stock/agent/simple-chat
static assets
```

注意：`POST /api/tw-stock/agent/simple-chat` 允许仅限只读解释，不能携带交易执行字段，不能触发其他写链路。

## 8. Console / Page audit 规则

通过条件：

```text
console_error_count=0
page_error_count=0
failed_response_count=0
```

如存在 warning，可记录但不必阻塞；如 warning 指向布局异常、API fallback 错误或安全边界不清，必须修复或解释。

## 9. UX / 响应式检查

每个视口必须检查：

```text
overflowX=false
无明显文字重叠
按钮文字不溢出
卡片内文本不遮挡
Agent 推荐问题可换行
模拟账户动作列在手机端单列
候选名单在手机端单列
历史模拟轨道在手机端单列
技术详情默认折叠
```

主界面必须出现：

```text
今日策略总览
候选名单
历史模拟
模拟账户状态
策略解释助手
不构成投资建议 或 不构成交易建议
不连接券商
不提交真实订单
```

主界面不得出现或不得常显：

```text
统一策略上下文
YZ Clean E4 产品化
clean registry
execution_price_mode: next_open
只展示 Model A / Model B
paper_order_intent_artifact_path
decision_id
apply_id
raw action_type
ReplayWindowPolicy
final equity
turnover_proxy_by_notional_over_avg_equity
```

这些内部字段如存在，必须只在默认折叠技术详情中出现，或只存在于源码 DTO。

## 10. 静态检索要求

必须运行：

```bash
cd frontend && corepack pnpm build
```

必须运行安全语义检索：

```bash
rg -n "建议买入|建议卖出|目标仓位|目标权重|保证收益|上涨概率|自动下单|quick-trade|broker|order submit|target_position|target_weight|provider publish|accepted latest|monitor scan|monitor alerts|连接券商|提交真实订单" frontend/src/views/tw-stock-monitor frontend/src/api/tw-stock.js
```

命中必须逐条归因。允许安全声明、只读 flags、拒绝语境、历史模拟语境；不允许交易入口、交易建议、真实下单、目标仓位/权重指令。

必须运行主路径内部字段检索：

```bash
rg -n "统一策略上下文|YZ Clean E4 产品化|clean registry|execution_price_mode: next_open|只展示 Model A / Model B|paper_order_intent_artifact_path|ReplayWindowPolicy|final equity|turnover_proxy_by_notional_over_avg_equity" frontend/src/views/tw-stock-monitor
```

命中如来自折叠详情或源码 DTO，必须归因；如来自主界面常显，必须修复。

## 11. 必须人工核对截图

执行者不能只提交 JSON。必须查看三张截图，并在报告中用文字说明：

```text
desktop 截图是否可一屏理解今日策略、候选、历史模拟、模拟账户、Agent
tablet 是否无横向溢出、无文字挤压
mobile 是否单列、按钮可换行、Agent 推荐问题不溢出
```

如截图显示页面仍像工程调试台，或主路径被技术字段占据，不得建议通过。

## 12. 执行报告要求

新增：

```text
docs/tw_modular_daily_update_productization/PHASEUI2D_RESPONSIVE_PLAYWRIGHT_ACCEPTANCE_EXECUTION_REPORT_CN.md
```

并更新：

```text
docs/tw_modular_daily_update_productization/PHASEUI2_STRATEGY_WORKBENCH_AGENT_UX_EXECUTION_REPORT_CN.md
```

报告必须包含：

```text
改动文件
UI2-C 报告口径修正
Playwright 启动方式
fixture/route 覆盖说明
desktop/tablet/mobile 截图路径
audit.json 路径
network_audit.json 路径
console_audit.json 路径
overflowX 结果
console/page error 结果
forbidden request 结果
主界面必须出现文案检查
主界面不得常显字段检查
静态 denylist 检索结果与逐条归因
frontend build 结果
未修改后端/API/模型/策略/日更/交易边界声明
未解决问题
是否建议最终审查通过
```

## 13. 审查通过标准

UI2-D 只有同时满足以下条件才可通过：

1. `corepack pnpm build` 通过。
2. Playwright desktop/tablet/mobile 截图齐全。
3. 三个视口 `overflowX=false`。
4. 无明显文字重叠、按钮溢出、卡片遮挡。
5. `console_error_count=0`。
6. `page_error_count=0`。
7. `failed_response_count=0`。
8. `forbidden_request_count=0`。
9. `monitor_config_write_count=0`。
10. `monitor_scan_post_count=0`。
11. `monitor_alerts_write_count=0`。
12. `ops_dry_run_post_count=0`。
13. 主界面出现今日策略总览、候选名单、历史模拟、模拟账户状态、策略解释助手。
14. 主界面清楚展示不连接券商、不提交真实订单、不构成交易建议/投资建议。
15. Agent 仍是策略解释助手，不是交易助手。
16. 技术详情默认折叠。
17. 没有改后端/API、模型、策略、回放算法、日更真实链路或交易边界。

## 14. 停止条件

出现以下任一情况必须停止并反馈：

- Playwright 需要触发真实 provider、monitor、broker/order 才能跑通。
- 页面出现 forbidden request。
- 移动端明显重叠或横向溢出，需要大范围重构。
- Agent simple-chat 出现交易建议或目标仓位语义。
- 需要改后端 DTO 或 API 才能完成验收。
- 无法生成或查看截图。
