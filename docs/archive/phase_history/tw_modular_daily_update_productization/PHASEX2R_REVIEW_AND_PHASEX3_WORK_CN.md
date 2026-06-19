# Phase X2R 审查与 Phase X3 Paper Portfolio 前端 UX / E2E 工作文档

生成日期：2026-06-18

## 1. X2R 审查结论

X2R 通过，可以进入 X3。

X2R 已完成：

```text
apply-decision 默认要求服务端 artifact authority
裸 paper_order_intent payload 默认拒绝
服务端读取 data_tw/artifacts/paper_portfolio/**/paper_order_intent.json
服务端读取同目录 paper_portfolio_state.json
服务端重算 input_checksum
path traversal 被拒绝
same-day different decision 被拒绝，包括前一次 no_actions/skipped/rejected
HTTP/API route 测试补齐
```

已复跑：

```text
python -m py_compile backend/app/services/tw_stock_paper_portfolio.py backend/app/routes/tw_stock.py scripts/build_tw_paper_portfolio_decision_artifact.py backend/tests/test_tw_stock_paper_portfolio_x2.py backend/tests/test_tw_stock_paper_portfolio_x2r_api.py
python -m pytest backend/tests/test_build_tw_paper_portfolio_decision_artifact.py backend/tests/test_tw_stock_paper_portfolio_x2.py backend/tests/test_tw_stock_paper_portfolio_x2r_api.py -q
22 passed
```

X3 可以接前端，但只能接 X2R 已冻结的 paper-only API。

## 2. Phase X3 目标

X3 目标是把 X1/X2R 的纸面策略决策变成用户可理解、可确认、可应用、可重置的前端体验。

X3 只做：

```text
前端展示当前模拟账户状态
前端展示最新 PaperOrderIntent / PaperApplyPreview
前端提供“应用到模拟账户”按钮
前端提供“重置模拟账户”按钮
前端二次确认
前端展示应用结果、跳过原因、拒绝原因
前端展示已应用 / 已最新 / stale / 数据不可用状态
浏览器 E2E 和 network denylist
```

X3 不做：

```text
真实 broker 接入
quick-trade
真实订单
provider refresh / publish
accepted latest switch
monitor config / scan / alerts
Agent action
新模型训练
新策略调参
每天自动脚本改造
```

## 3. API 范围

前端只允许调用以下 paper portfolio API：

```text
GET  /api/tw-stock/paper-portfolio/state
GET  /api/tw-stock/paper-portfolio/apply-runs
POST /api/tw-stock/paper-portfolio/apply-decision
POST /api/tw-stock/paper-portfolio/reset
```

X3 允许读取已有只读展示 API，例如：

```text
readonly strategy snapshot
paper decision artifact index / manifest
daily readonly latest snapshot
```

但 X3 不允许调用：

```text
POST /api/quick-trade/**
POST /api/agent/v1/quick-trade/**
/api/broker/**
POST /api/tw-stock/monitor/config
POST /api/tw-stock/monitor/scan
POST /api/tw-stock/monitor/scan-all
POST /api/tw-stock/monitor/alerts
PUT/PATCH/DELETE /api/tw-stock/monitor/alerts/*
POST /api/tw-stock/quant/ops/** publish/refresh/provider/accepted
```

## 4. 用户第一性原则

X3 前端必须符合：

```text
简单
准确
实用
清晰
```

具体要求：

```text
用户一眼能看懂当前是“模拟账户”，不是实盘
用户一眼能看懂策略基于哪天数据、哪个模型、哪个规则
用户一眼能看懂将要模拟卖出什么、买入什么、跳过什么
用户一眼能看懂为什么不能应用
用户一眼能看懂应用后现金、持仓、成交模拟记录有什么变化
用户必须二次确认后才能 apply/reset
失败提示必须说人话，不能只展示错误码
```

禁止文案：

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

允许文案：

```text
应用到模拟账户
模拟卖出
模拟买入
纸面成交
只影响模拟账户
不是交易建议
```

## 5. 页面入口建议

优先在现有台股监控页面中增加一个紧凑的“模拟策略”区域，不要新做营销页。

建议入口：

```text
/tw-stock-monitor
```

可新增组件，但不要把页面改成复杂的多层卡片。

建议组件：

```text
PaperPortfolioPanel.vue
PaperApplyPreview.vue
PaperApplyResult.vue
PaperResetConfirmDialog.vue
```

如果项目现有风格不适合拆组件，可先在现有页面局部实现，但必须保持代码边界清晰。

## 6. 前端状态模型

前端至少区分以下状态：

```text
loading
no_account
no_decision
ready_to_apply
already_applied
stale_epoch
same_day_apply_rejected
invalid_artifact
data_unavailable
applying
applied
apply_failed
reset_confirming
resetting
reset_done
reset_failed
```

按钮状态：

```text
ready_to_apply -> 主按钮可用：应用到模拟账户
already_applied -> 按钮置灰：今天已应用
stale_epoch -> 按钮置灰：模拟账户已变化，请刷新策略
no_decision -> 按钮置灰：暂无可应用策略
data_unavailable -> 按钮置灰：策略数据不可用
applying/resetting -> loading，禁止重复点击
```

## 7. Apply UX 合同

点击“应用到模拟账户”前，前端必须展示：

```text
模拟账户名称或 ID
paper_account_epoch
asof
model_id = e4_frozen_qlib_2023_2025_ltr
strategy_rule = top50_exit_one_worst_sell
paper_order_intent_artifact_path 或 decision_artifact_id
预计模拟卖出列表
预计模拟买入列表
跳过列表
不可执行原因
```

二次确认必须包含明确文字：

```text
此操作只会写入模拟账户，不会提交真实订单。
```

请求 payload 必须包含：

```text
paper_account_id
paper_account_epoch
decision_id
paper_order_intent_artifact_path 或 decision_artifact_id
input_checksum
idempotency_key
confirmed_by_user=true
confirm_text 包含“模拟”
```

不得把裸 `paper_order_intent` payload 作为正式前端请求主体。

## 8. Reset UX 合同

点击“重置模拟账户”必须是危险操作样式，但文案仍然明确是模拟账户。

二次确认必须展示：

```text
当前现金
当前持仓数量
当前 paper_account_epoch
重置后 initial_cash
旧状态会进入 reset archive
```

二次确认文字必须包含：

```text
重置模拟账户
```

请求 payload 必须包含：

```text
paper_account_id
current_epoch
idempotency_key
input_checksum
confirmed_by_user=true
confirm_text 包含“重置模拟账户”
可选 reset_initial_cash
```

Reset 成功后：

```text
刷新 paper portfolio state
刷新 apply-runs
清空当前 apply preview 或提示需要重新生成策略
展示 new_epoch
```

## 9. Apply Result 展示

Apply 成功后必须展示：

```text
status
apply_id
asof
cash_before
cash_after
paper_executions
skipped_actions
rejected_actions
positions_after
```

对用户友好的解释：

```text
cash_insufficient -> 模拟现金不足，未执行
oversell -> 模拟持仓不足，未执行
action_unavailable -> 当前持仓或策略条件不满足，已跳过
same_day_apply_rejected -> 今天这个模拟账户已经应用过其他策略
stale_epoch -> 模拟账户已重置或变更，请重新加载策略
invalid_artifact -> 策略文件校验失败，请重新生成策略
idempotency_conflict -> 重复请求冲突，请刷新后重试
```

## 10. 前端数据来源

X3 必须明确从哪里拿最新 paper decision artifact。

允许方案：

```text
读取已有 paper portfolio artifact manifest/index
读取 daily readonly latest 中指向的 paper decision bundle
新增只读 paper decision latest/index API
```

如果当前没有稳定的只读 artifact index，X3 可以新增一个只读 API：

```text
GET /api/tw-stock/paper-portfolio/latest-decision
```

但该 API 只能读：

```text
data_tw/artifacts/paper_portfolio/**
```

不能写任何表，不能触发策略生成，不能触发 provider 更新。

返回建议：

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
warnings
simulation_only=true
trading.real_orders_enabled=false
trading.connects_to_broker=false
```

如果执行者新增该 API，必须补后端只读测试和 network audit。

## 11. E2E 验收

X3 必须新增浏览器 E2E 或等价 Playwright 检查。

至少覆盖：

```text
页面可打开
模拟策略区域可见
显示“模拟账户”语义
显示当前策略 asof / model / rule
应用按钮在 ready 状态可点击
点击 apply 前出现二次确认
确认后只 POST /paper-portfolio/apply-decision
成功后展示 applied / paper_executions / skipped / rejected
重复进入页面显示 already_applied 或按钮置灰
reset 按钮需要二次确认
确认 reset 后只 POST /paper-portfolio/reset
reset 成功后展示 new_epoch
```

必须导出：

```text
network_audit.json
console_audit.json
screenshot
```

Network audit 通过标准：

```text
forbidden_request_count = 0
quick_trade_request_count = 0
broker_request_count = 0
provider_ops_post_count = 0
monitor_config_write_count = 0
monitor_scan_post_count = 0
monitor_alerts_write_count = 0
target_position_write_count = 0
```

允许的 POST 只有：

```text
POST /api/tw-stock/paper-portfolio/apply-decision
POST /api/tw-stock/paper-portfolio/reset
```

## 12. 测试要求

X3 至少执行：

```text
python -m py_compile backend/app/services/tw_stock_paper_portfolio.py backend/app/routes/tw_stock.py
python -m pytest backend/tests/test_build_tw_paper_portfolio_decision_artifact.py backend/tests/test_tw_stock_paper_portfolio_x2.py backend/tests/test_tw_stock_paper_portfolio_x2r_api.py <新增后端测试> -q
```

前端按项目实际技术栈执行：

```text
npm / pnpm / node 对应 unit 或 static check
Playwright E2E
```

若启动后端或前端服务，报告必须写明：

```text
启动命令
端口
环境变量
测试 URL
是否登录
```

## 13. X3 执行报告要求

执行者必须提交：

```text
docs/tw_modular_daily_update_productization/PHASEX3_PAPER_PORTFOLIO_FRONTEND_UX_E2E_EXECUTION_REPORT_CN.md
```

报告必须包含：

```text
1. 修改文件清单
2. 前端入口和组件说明
3. 最新 paper decision 数据来源
4. apply UX 截图和状态说明
5. reset UX 截图和状态说明
6. 用户第一性原则自查
7. network audit
8. console audit
9. 后端/前端/浏览器测试命令与结果
10. forbidden action audit
11. 是否建议 X 路线收尾
```

## 14. 收尾判断

X3 通过后，X 路线才可以判断是否收尾。

X 路线收尾标准：

```text
能读取当前模拟账户持仓
能基于当前模拟持仓生成 paper decision
能预览模拟卖出 / 买入 / 跳过 / 拒绝
能经用户确认应用到模拟账户
能经用户确认重置模拟账户
前端简单、准确、实用、清晰
E2E 证明前端可运行且返回及时
network audit 证明没有真实交易或 provider/monitor 越界
```

若 X3 只完成 UI 但没有 E2E 或 network audit，不允许收尾。
