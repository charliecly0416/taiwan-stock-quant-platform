# Phase X2 Paper Apply / Reset API 执行报告

生成日期：2026-06-18

## 1. 新增/修改文件清单

本轮新增：

```text
backend/app/services/tw_stock_paper_portfolio.py
backend/tests/test_tw_stock_paper_portfolio_x2.py
docs/tw_modular_daily_update_productization/PHASEX2_PAPER_APPLY_RESET_API_EXECUTION_REPORT_CN.md
```

本轮修改：

```text
backend/app/routes/tw_stock.py
```

本轮未修改前端，未新增 X3 UX。

## 2. 执行范围与禁止边界

X2 是 paper 写路径，但只写模拟账户相关表。本轮未触达：

```text
真实 broker
/api/agent/v1/quick-trade/**
/api/quick-trade/**
real orders
provider publish
provider accepted latest / qlib accepted latest switch
monitor config / scan / alerts
Agent tool/action
training / tuning / model replacement
```

新增服务文件 `tw_stock_paper_portfolio.py` 没有导入 broker、quick-trade、orders、provider、monitor、Agent 或训练模块。

## 3. 数据库迁移 / 存储说明

X2 服务在 `ensure_schema()` 中幂等创建 / 补齐 paper-only schema：

```text
ALTER TABLE qd_tw_sim_accounts ADD COLUMN IF NOT EXISTS paper_account_epoch INTEGER NOT NULL DEFAULT 1
ALTER TABLE qd_tw_sim_accounts ADD COLUMN IF NOT EXISTS archived BOOLEAN NOT NULL DEFAULT FALSE

CREATE TABLE IF NOT EXISTS qd_tw_sim_apply_runs
CREATE TABLE IF NOT EXISTS qd_tw_sim_reset_runs
CREATE TABLE IF NOT EXISTS qd_tw_sim_audit_log
```

允许写入表：

```text
qd_tw_sim_accounts
qd_tw_sim_positions
qd_tw_sim_orders
qd_tw_sim_trades
qd_tw_sim_apply_runs
qd_tw_sim_reset_runs
qd_tw_sim_audit_log
```

未写 provider/latest/monitor/broker/Agent 相关表。

## 4. API 合同

新增后端接口：

```text
GET  /api/tw-stock/paper-portfolio/state
GET  /api/tw-stock/paper-portfolio/apply-runs
POST /api/tw-stock/paper-portfolio/apply-decision
POST /api/tw-stock/paper-portfolio/reset
```

接口均挂在 `tw_stock.py`，受 `login_required` 保护，使用 `_current_user_id()` 做 user_id 隔离。

所有响应保持模拟账户安全标志：

```text
simulation_only = true
trading.real_orders_enabled = false
trading.connects_to_broker = false
trading.simulation_only = true
```

错误状态补充映射：

```text
invalid_request
invalid_confirmation
invalid_artifact
stale_epoch
same_day_apply_rejected
idempotency_conflict
```

这些状态返回 400；`not_found` 返回 404。

## 5. Apply 合同与实现

`POST /paper-portfolio/apply-decision` 要求：

```text
paper_account_id
paper_account_epoch
decision_id
idempotency_key
input_checksum
confirmed_by_user=true
confirm_text 包含“模拟”
paper_order_intent payload
```

验证：

```text
readonly_decision_only = true
not_real_order = true
not_target_position = true
not_investment_advice = true
model_id = e4_frozen_qlib_2023_2025_ltr
strategy_rule = top50_exit_one_worst_sell
paper_account_id 匹配
paper_account_epoch 匹配当前账户 epoch
input_checksum 匹配 artifact
```

执行：

```text
只执行 applicability=applicable 的 paper_buy_intent / paper_sell_intent
paper_skip 进入 skipped_actions
unavailable action 进入 skipped_actions，不写成交
现金不足进入 rejected_actions，不写成交
卖出超过持仓进入 rejected_actions，不写成交
每个执行 action 写 qd_tw_sim_orders + qd_tw_sim_trades
持仓写 qd_tw_sim_positions
现金写 qd_tw_sim_accounts
apply run 写 qd_tw_sim_apply_runs
审计写 qd_tw_sim_audit_log
```

## 6. 幂等规则实现证据

Apply 幂等：

```text
qd_tw_sim_apply_runs UNIQUE(decision_id, paper_account_id, paper_account_epoch)
qd_tw_sim_apply_runs UNIQUE(user_id, idempotency_key)
```

服务逻辑：

```text
重复 idempotency_key + 相同 input_checksum 返回原 result，already_applied=true
重复 idempotency_key + 不同 input_checksum 返回 idempotency_conflict
重复 decision_id + paper_account_id + epoch 返回原 result，already_applied=true
同一 paper_account_id + epoch + asof 已存在不同 decision apply 时返回 same_day_apply_rejected
旧 epoch decision 返回 stale_epoch
```

Reset 幂等：

```text
qd_tw_sim_reset_runs UNIQUE(user_id, idempotency_key)
重复 idempotency_key + 相同 input_checksum 返回原 result，already_reset=true
重复 idempotency_key + 不同 input_checksum 返回 idempotency_conflict
```

测试覆盖：

```text
test_apply_duplicate_same_idempotency_returns_existing_result_and_conflict_rejected
test_duplicate_decision_returns_already_applied_and_stale_epoch_rejected
test_reset_archives_previous_state_increments_epoch_and_duplicate_replays
```

## 7. Epoch / Reset Archive 实现证据

Epoch 方案：采用推荐表字段方案。

```text
qd_tw_sim_accounts.paper_account_epoch
qd_tw_sim_accounts.archived
```

Reset 执行：

```text
读取 account / positions / orders / trades
生成 archive_snapshot
写 qd_tw_sim_reset_runs
写 qd_tw_sim_audit_log
DELETE qd_tw_sim_positions 当前账户持仓
取消 draft orders
qd_tw_sim_accounts.cash 恢复 initial_cash 或 reset_initial_cash
qd_tw_sim_accounts.paper_account_epoch += 1
```

旧 epoch decision apply 会被 `stale_epoch` 拒绝。

测试覆盖：

```text
test_reset_archives_previous_state_increments_epoch_and_duplicate_replays
```

断言包含：

```text
archive_snapshot.positions 非空
new_epoch = 2
positions 清空
重复 reset 返回 already_reset=true
reset 后 old epoch apply 返回 stale_epoch
```

## 8. PaperAuditLog 实现证据

新增表：

```text
qd_tw_sim_audit_log
```

字段覆盖：

```text
event_id
event_type
paper_account_id
paper_account_epoch
user_id
decision_id
apply_id
reset_id
idempotency_key
input_checksum
result_status
created_at
```

Apply 写：

```text
event_type = apply_decision
```

Reset 写：

```text
event_type = reset_account
```

幂等重放写：

```text
event_type = duplicate_replay
result_status = already_applied / already_reset
```

可定位账户的拒绝写：

```text
event_type = rejected
result_status = stale_epoch / same_day_apply_rejected / idempotency_conflict
```

测试覆盖：

```text
test_apply_happy_path_writes_paper_only_tables_and_audit
test_apply_duplicate_same_idempotency_returns_existing_result_and_conflict_rejected
test_duplicate_decision_returns_already_applied_and_stale_epoch_rejected
test_reset_archives_previous_state_increments_epoch_and_duplicate_replays
```

## 9. Accounting Policy 与 lot_size 口径

X2 冻结并实现：

```text
fill_policy = paper_close_price_fill
price_source = artifact_reference_price
fee_rate = 0.001425
sell_tax_rate = 0.003
slippage_rate = 0
base_currency = TWD
market_scope = TWStock
cost_basis_policy = weighted_average
cash_insufficient_policy = reject action
oversell_policy = reject action
same_day_apply_policy = reject except idempotent replay
lot_size = 10
```

说明：`lot_size=10` 沿用当前 `TWStockSimAccountService.DEFAULT_LOT_SIZE`。X3 前端必须说明这是模拟账户单位，不得误称真实整股交易单位。

## 10. Forbidden Action Audit

本轮未触发：

```text
quick-trade
broker
real orders
provider publish
accepted latest switch
monitor write / scan / alerts
Agent action
training / tuning
```

测试 `test_apply_happy_path_writes_paper_only_tables_and_audit` 汇总 fake DB SQL，断言未出现：

```text
quick-trade
quick_trade
broker
provider_publish
monitor/scan
```

X2 未触及前端，因此未产生浏览器 network audit。X3 若接前端必须补 network denylist 验收。

## 11. 测试结果

已执行：

```text
python -m py_compile backend/app/services/tw_stock_paper_portfolio.py backend/app/routes/tw_stock.py scripts/build_tw_paper_portfolio_decision_artifact.py
python -m pytest backend/tests/test_build_tw_paper_portfolio_decision_artifact.py backend/tests/test_tw_stock_paper_portfolio_x2.py -q
```

结果：

```text
12 passed in 0.94s
```

X2 必测场景覆盖：

```text
apply happy path: sell/buy applicable 写入 paper-only tables
apply duplicate same idempotency_key returns existing result
apply duplicate decision_id returns already_applied
apply same-day different decision rejected
apply stale epoch rejected
apply unavailable action not executed
apply cash insufficient action rejected
apply oversell action rejected
reset archives previous state
reset increments epoch
reset duplicate idempotency returns existing result
old epoch decision cannot apply after reset
no broker / quick-trade / real orders path called
```

## 12. 是否可以进入 X3

可以进入 X3 前端 UX 与 E2E 准备，但 X3 必须补：

```text
前端“模拟”文案
apply/reset 二次确认
已应用状态
不可应用原因展示
reset archive 提示
network audit，只允许 /api/tw-stock/paper-portfolio/apply-decision 和 /api/tw-stock/paper-portfolio/reset 两个 POST
禁止 quick-trade / broker / orders / monitor / provider ops 请求
```

