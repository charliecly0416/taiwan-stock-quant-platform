# Phase X 模拟持仓策略与模拟账户应用路线总结报告

生成日期：2026-06-18

## 1. 路线背景

Phase X 的起点问题是：

```text
每天自动策略不能只基于空仓或固定假设给出买卖意图
策略应当能读取当前模拟账户持仓
基于当前模拟持仓生成纸面买卖决策
用户应能在前端确认后应用到模拟账户
用户也应能安全重置模拟账户，从新的模拟起点开始
```

因此 Phase X 不是新模型路线，也不是实盘交易路线，而是：

```text
paper portfolio strategy
simulation account apply/reset
frontend paper-only UX
```

核心原则：

```text
只影响模拟账户
不连接券商
不提交真实订单
不触发 quick-trade
不触发 provider publish / accepted latest switch
不触发 monitor 写入或扫描
```

## 2. 路线范围

Phase X 已覆盖：

```text
读取当前模拟账户持仓
基于当前模拟持仓生成 PaperPortfolioStateArtifact
基于 e4_frozen_qlib_2023_2025_ltr + top50_exit_one_worst_sell 生成 PaperOrderIntentArtifact
生成 PaperApplyPreviewArtifact
提供 paper-only apply API
提供 paper-only reset API
前端展示模拟策略预览
前端二次确认后应用到模拟账户
前端二次确认后重置模拟账户
浏览器 E2E 与 network denylist 验收
```

Phase X 未覆盖，也不应在本路线中覆盖：

```text
真实券商接入
真实下单
quick-trade
provider 外网拉取
provider publish
accepted latest 切换
monitor config / scan / alerts 写入
Agent action
新模型训练
新策略调参
每日自动脚本重构
```

## 3. 阶段回顾

### 3.1 X0 Paper Account Contract Audit

执行报告：

```text
docs/tw_modular_daily_update_productization/PHASEX0_PAPER_ACCOUNT_CONTRACT_AUDIT_EXECUTION_REPORT_CN.md
```

审查结论：

```text
X0 通过
现有 TW stock simulation account 路径可作为主路径
不得使用 /api/agent/v1/quick-trade/orders 作为前端入口
```

冻结主路径：

```text
backend/app/services/tw_stock_sim_account.py
backend/app/routes/tw_stock.py
qd_tw_sim_accounts
qd_tw_sim_positions
qd_tw_sim_orders
qd_tw_sim_trades
```

关键判断：

```text
模拟账户服务已有 simulation_only=true
sim_trading_flags 返回 real_orders_enabled=false / connects_to_broker=false
可在此基础上扩展 paper strategy apply/reset
```

### 3.2 X1 Paper Decision and Accounting Engine

执行报告：

```text
docs/tw_modular_daily_update_productization/PHASEX1_PAPER_DECISION_AND_ACCOUNTING_ENGINE_EXECUTION_REPORT_CN.md
```

X1 建立能力：

```text
读取模拟持仓
读取只读模型信号
按 top50_exit_one_worst_sell 生成 paper decision
生成 PaperPortfolioStateArtifact
生成 PaperOrderIntentArtifact
生成 PaperApplyPreviewArtifact
输出 forbidden_action_audit
```

审查发现：

```text
unavailable sell 错误释放仓位槽位
可能导致不该出现的 buy preview
```

因此进入 X1R。

### 3.3 X1R Paper Decision Preview Repair

执行报告：

```text
docs/tw_modular_daily_update_productization/PHASEX1R_PAPER_DECISION_PREVIEW_REPAIR_EXECUTION_REPORT_CN.md
```

修复结果：

```text
unavailable sell 不释放仓位槽位
unavailable sell 不释放现金
unavailable sell 不触发额外 buy slot
DB 路径保持 SELECT-only
```

验证命令：

```text
python -m py_compile scripts/build_tw_paper_portfolio_decision_artifact.py
python -m pytest backend/tests/test_build_tw_paper_portfolio_decision_artifact.py -q
```

结果：

```text
6 passed
```

审查结论：

```text
X1/X1R 只读 paper decision engine 通过
可以进入 X2 paper write path
```

### 3.4 X2 Paper Apply / Reset API

执行报告：

```text
docs/tw_modular_daily_update_productization/PHASEX2_PAPER_APPLY_RESET_API_EXECUTION_REPORT_CN.md
```

X2 建立能力：

```text
GET  /api/tw-stock/paper-portfolio/state
GET  /api/tw-stock/paper-portfolio/apply-runs
POST /api/tw-stock/paper-portfolio/apply-decision
POST /api/tw-stock/paper-portfolio/reset
```

写入范围：

```text
qd_tw_sim_accounts
qd_tw_sim_positions
qd_tw_sim_orders
qd_tw_sim_trades
qd_tw_sim_apply_runs
qd_tw_sim_reset_runs
qd_tw_sim_audit_log
```

X2 已实现：

```text
paper_account_epoch
apply idempotency
reset idempotency
reset archive snapshot
audit log
cash insufficient reject
oversell reject
unavailable action skip
old epoch stale reject
```

审查发现：

```text
apply-decision 只验证请求 payload 内部一致
没有从服务端 artifact store 读取 X1/X1R 产物
没有服务端重算 checksum
```

因此进入 X2R。

### 3.5 X2R Artifact Authority Repair

执行报告：

```text
docs/tw_modular_daily_update_productization/PHASEX2R_PAPER_APPLY_ARTIFACT_AUTHORITY_REPAIR_EXECUTION_REPORT_CN.md
```

X2R 修复：

```text
apply-decision 默认要求 paper_order_intent_artifact_path 或 decision_artifact_id
裸 paper_order_intent payload 默认拒绝
服务端读取 data_tw/artifacts/paper_portfolio/**/paper_order_intent.json
服务端读取同目录 paper_portfolio_state.json
服务端重算 input_checksum
拒绝 path traversal
拒绝 checksum mismatch
拒绝 same-day different decision
HTTP/API route 测试补齐
```

验证命令：

```text
python -m py_compile backend/app/services/tw_stock_paper_portfolio.py backend/app/routes/tw_stock.py scripts/build_tw_paper_portfolio_decision_artifact.py backend/tests/test_tw_stock_paper_portfolio_x2.py backend/tests/test_tw_stock_paper_portfolio_x2r_api.py
python -m pytest backend/tests/test_build_tw_paper_portfolio_decision_artifact.py backend/tests/test_tw_stock_paper_portfolio_x2.py backend/tests/test_tw_stock_paper_portfolio_x2r_api.py -q
```

结果：

```text
22 passed
```

审查结论：

```text
X2R 通过
可以进入 X3 前端 UX / E2E
```

### 3.6 X3 Frontend UX / E2E

执行报告：

```text
docs/tw_modular_daily_update_productization/PHASEX3_PAPER_PORTFOLIO_FRONTEND_UX_E2E_EXECUTION_REPORT_CN.md
```

X3 建立能力：

```text
新增前端 PaperPortfolioPanel
在 /#/tw-stock-monitor 展示模拟策略区域
展示模拟账户 ID / epoch / 现金 / 持仓数量
展示策略 asof / model_id / strategy_rule / decision_id
展示 paper_order_intent_artifact_path
展示预计模拟卖出 / 模拟买入 / 跳过与不可执行原因
二次确认后应用到模拟账户
二次确认后重置模拟账户
展示 apply result 与 reset result
```

新增只读 API：

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

正式前端 apply payload：

```text
paper_account_id
paper_account_epoch
decision_id
paper_order_intent_artifact_path
input_checksum
idempotency_key
confirmed_by_user=true
confirm_text includes 模拟
```

正式前端不提交：

```text
paper_order_intent
```

## 4. 最终验证

后端测试：

```text
python -m pytest backend/tests/test_build_tw_paper_portfolio_decision_artifact.py backend/tests/test_tw_stock_paper_portfolio_x2.py backend/tests/test_tw_stock_paper_portfolio_x2r_api.py -q
```

结果：

```text
24 passed
```

前端静态检查：

```text
cd frontend
node tests/unit/tw-stock-paper-portfolio-panel-check.mjs
```

结果：

```text
tw-stock-paper-portfolio-panel static checks passed
```

前端构建：

```text
cd frontend
corepack pnpm build
```

结果：

```text
vite build succeeded
```

浏览器 E2E：

```text
cd frontend
python -m http.server 5173 --bind 127.0.0.1 --directory dist
node tests/e2e/tw-stock-paper-portfolio-panel-e2e.mjs
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

Console audit：

```json
{
  "console_messages": [],
  "page_errors": []
}
```

E2E 截图：

```text
/tmp/quantdinger_tw_paper_portfolio_e2e/01_paper_panel_loaded.png
/tmp/quantdinger_tw_paper_portfolio_e2e/02_paper_applied.png
/tmp/quantdinger_tw_paper_portfolio_e2e/03_paper_reset.png
```

## 5. 安全边界结论

Phase X 全路线未允许触达：

```text
真实 broker
/api/agent/v1/quick-trade/**
/api/quick-trade/**
real orders
provider publish
provider accepted latest / qlib accepted latest switch
monitor config / scan / alerts 写入
Agent tool/action
training / tuning / model replacement
```

允许的写路径仅限：

```text
qd_tw_sim_accounts
qd_tw_sim_positions
qd_tw_sim_orders
qd_tw_sim_trades
qd_tw_sim_apply_runs
qd_tw_sim_reset_runs
qd_tw_sim_audit_log
```

前端允许的 POST 仅限：

```text
POST /api/tw-stock/paper-portfolio/apply-decision
POST /api/tw-stock/paper-portfolio/reset
```

安全语义已保持：

```text
simulation_only=true
real_orders_enabled=false
connects_to_broker=false
not_real_order=true
not_target_position=true
not_investment_advice=true
```

## 6. 用户第一性原则结论

前端已满足：

```text
简单
准确
实用
清晰
```

具体表现：

```text
页面区域命名为“模拟策略”
按钮命名为“应用到模拟账户”和“重置模拟账户”
二次确认明确“不会提交真实订单”
展示模型、策略、日期、artifact path、epoch
展示预计模拟卖出、模拟买入、跳过、不执行原因
展示 apply 后现金变化和纸面成交
展示 reset 后 new_epoch 与 archive 提示
失败原因映射成人话
```

未出现不当实盘语义：

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

## 7. 剩余注意事项

不阻塞 X 路线收尾，但后续维护应注意：

```text
前端静态检查命令需要在 frontend 目录执行
X3 浏览器 E2E 使用 mock API 验证用户态与 network denylist
真实后端联通由 X2R route/service 测试覆盖
若后续把 paper apply/reset 接入每日自动脚本，必须另开新阶段并重新审查安全边界
若后续要接真实券商，必须另开实盘合规路线，不能复用 X 路线的 paper-only 结论
```

## 8. 最终收尾判断

Phase X 可以收尾。

收尾理由：

```text
能读取当前模拟账户持仓
能基于当前模拟持仓生成 paper decision
能预览模拟卖出 / 买入 / 跳过 / 拒绝
能经用户确认应用到模拟账户
能经用户确认重置模拟账户
前端体验简单、准确、实用、清晰
后端测试、前端静态检查、前端 build、浏览器 E2E 均通过
network audit 证明没有真实交易或 provider/monitor 越界
```

最终结论：

```text
X 路线完成“模拟持仓策略 -> 模拟账户应用 -> 前端确认 -> 安全重置”的闭环。
该闭环可作为后续新模型、新策略进入模拟账户验证阶段的基础设施。
```
