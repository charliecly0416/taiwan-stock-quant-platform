# Phase X3 Paper Portfolio 前端 UX / E2E 执行报告

生成日期：2026-06-18

## 1. 修改文件清单

后端：

```text
backend/app/services/tw_stock_paper_portfolio.py
backend/app/routes/tw_stock.py
backend/tests/test_tw_stock_paper_portfolio_x2.py
backend/tests/test_tw_stock_paper_portfolio_x2r_api.py
```

前端：

```text
frontend/src/api/tw-stock.js
frontend/src/views/tw-stock-monitor/index.vue
frontend/src/views/tw-stock-monitor/components/PaperPortfolioPanel.vue
frontend/tests/unit/tw-stock-paper-portfolio-panel-check.mjs
frontend/tests/e2e/tw-stock-paper-portfolio-panel-e2e.mjs
```

报告：

```text
docs/tw_modular_daily_update_productization/PHASEX3_PAPER_PORTFOLIO_FRONTEND_UX_E2E_EXECUTION_REPORT_CN.md
```

## 2. 前端入口和组件说明

入口：

```text
/#/tw-stock-monitor
```

新增组件：

```text
PaperPortfolioPanel.vue
```

位置：只读策略快照与只读 replay window 之后，作为紧凑的“模拟策略”区域。

组件能力：

```text
展示模拟账户 ID / epoch / 现金 / 持仓数量
展示策略 asof / model_id / strategy_rule / decision_id
展示 paper_order_intent_artifact_path
展示预计模拟卖出 / 模拟买入 / 跳过与不可执行原因
应用到模拟账户前二次确认
重置模拟账户前二次确认
展示 apply result: status / apply_id / asof / cash_before / cash_after / paper_executions / skipped_actions / rejected_actions
展示 reset result: new_epoch 与 reset archive 提示
```

## 3. 最新 Paper Decision 数据来源

X3 新增只读 API：

```text
GET /api/tw-stock/paper-portfolio/latest-decision
```

该 API 只读：

```text
data_tw/artifacts/paper_portfolio/**/manifest.json
data_tw/artifacts/paper_portfolio/**/paper_order_intent.json
data_tw/artifacts/paper_portfolio/**/paper_portfolio_state.json
data_tw/artifacts/paper_portfolio/**/paper_apply_preview.json
```

不写 DB，不生成策略，不触发 provider / monitor / broker / Agent / training。

返回字段覆盖：

```text
ok
status
asof
model_id
strategy_rule
decision_id
paper_account_id
paper_account_epoch
input_checksum
paper_order_intent_artifact_path
preview
intent
simulation_only=true
trading.real_orders_enabled=false
trading.connects_to_broker=false
```

前端正式 apply payload 只提交 artifact path，不提交裸 `paper_order_intent`。

## 4. Apply UX 截图和状态说明

截图：

```text
/tmp/quantdinger_tw_paper_portfolio_e2e/01_paper_panel_loaded.png
/tmp/quantdinger_tw_paper_portfolio_e2e/02_paper_applied.png
```

状态：

```text
ready_to_apply: 显示“应用到模拟账户”按钮
already_applied: 今天已应用，按钮置灰
stale_epoch: 模拟账户已变化，提示重新加载策略
apply_failed: 失败提示使用人话映射
applied: 展示 apply_id / 现金变化 / 纸面成交 / 跳过 / 拒绝
```

二次确认文案包含：

```text
此操作只会写入模拟账户，不会提交真实订单。
```

## 5. Reset UX 截图和状态说明

截图：

```text
/tmp/quantdinger_tw_paper_portfolio_e2e/03_paper_reset.png
```

Reset 二次确认展示：

```text
当前现金
当前持仓数量
当前 paper_account_epoch
重置后 initial_cash
旧状态会进入 reset archive
```

Reset 请求包含：

```text
paper_account_id
current_epoch
idempotency_key
input_checksum
confirmed_by_user=true
confirm_text 包含“重置模拟账户”
reset_initial_cash
```

Reset 成功后展示：

```text
new_epoch
旧状态已进入 reset archive，需要重新生成策略后再应用
```

## 6. 用户第一性原则自查

自查结果：

```text
简单：区域只保留模拟账户、策略、预览、结果、两个确认动作。
准确：明确 model_id / strategy_rule / asof / artifact path / epoch。
实用：用户能看到模拟卖出、模拟买入、跳过、拒绝和现金变化。
清晰：所有主按钮包含“模拟账户”，失败原因映射成人话。
```

避免文案：

```text
实盘下单
真实买入
真实卖出
自动交易
连接券商
保证收益
上涨概率
目标仓位
```

采用文案：

```text
应用到模拟账户
模拟卖出
模拟买入
纸面成交
只影响模拟账户
不是交易建议
不接入任何券商通道
```

## 7. Network Audit

输出文件：

```text
/tmp/quantdinger_tw_paper_portfolio_e2e/network_audit.json
```

结果：

```json
{
  "forbidden_request_count": 0,
  "quick_trade_request_count": 0,
  "broker_request_count": 0,
  "provider_ops_post_count": 0,
  "monitor_config_write_count": 0,
  "monitor_scan_post_count": 0,
  "monitor_alerts_write_count": 0,
  "target_position_write_count": 0,
  "allowed_paper_apply_post_count": 1,
  "allowed_paper_reset_post_count": 1,
  "unexpected_post_count": 0
}
```

允许 POST 仅命中：

```text
POST /api/tw-stock/paper-portfolio/apply-decision
POST /api/tw-stock/paper-portfolio/reset
```

## 8. Console Audit

输出文件：

```text
/tmp/quantdinger_tw_paper_portfolio_e2e/console_audit.json
```

结果：

```json
{
  "console_messages": [],
  "page_errors": []
}
```

## 9. 后端 / 前端 / 浏览器测试命令与结果

后端：

```text
python -m py_compile backend/app/services/tw_stock_paper_portfolio.py backend/app/routes/tw_stock.py scripts/build_tw_paper_portfolio_decision_artifact.py
python -m pytest backend/tests/test_build_tw_paper_portfolio_decision_artifact.py backend/tests/test_tw_stock_paper_portfolio_x2.py backend/tests/test_tw_stock_paper_portfolio_x2r_api.py -q
```

结果：

```text
24 passed in 1.25s
```

前端静态：

```text
node tests/unit/tw-stock-paper-portfolio-panel-check.mjs
```

结果：

```text
tw-stock-paper-portfolio-panel static checks passed
```

前端 build：

```text
corepack pnpm build
```

结果：

```text
vite build succeeded
```

浏览器 E2E：

启动服务：

```text
python -m http.server 5173 --bind 127.0.0.1 --directory dist
```

测试 URL：

```text
http://127.0.0.1:5173/#/tw-stock-monitor
```

执行：

```text
TW_STOCK_MONITOR_BASE_URL=http://127.0.0.1:5173 \
TW_STOCK_PAPER_PORTFOLIO_E2E_DIR=/tmp/quantdinger_tw_paper_portfolio_e2e \
node tests/e2e/tw-stock-paper-portfolio-panel-e2e.mjs
```

结果：通过，输出 network / console audit 与截图。

说明：`vite dev` 与 `vite preview` 在本机因系统 watcher 数量限制 `ENOSPC` 失败，改用已构建 `dist` 的静态服务器完成浏览器验收。

## 10. Forbidden Action Audit

X3 未新增或触达：

```text
真实 broker
/api/agent/v1/quick-trade/**
/api/quick-trade/**
real orders
provider refresh / publish
accepted latest switch
monitor config / scan / alerts 写入
Agent action
新模型训练
新策略调参
每天自动脚本改造
```

静态检查确认 paper panel/API helper 不包含 forbidden POST 入口；浏览器 network audit 确认 forbidden request count 为 0。

## 11. 是否建议 X 路线收尾

建议 X 路线进入收尾判断。

当前已满足：

```text
能读取当前模拟账户持仓
能基于当前模拟持仓读取 paper decision
能预览模拟卖出 / 买入 / 跳过 / 拒绝
能经用户确认应用到模拟账户
能经用户确认重置模拟账户
前端简单、准确、实用、清晰
E2E 证明前端可运行且返回及时
network audit 证明没有真实交易或 provider/monitor 越界
```
