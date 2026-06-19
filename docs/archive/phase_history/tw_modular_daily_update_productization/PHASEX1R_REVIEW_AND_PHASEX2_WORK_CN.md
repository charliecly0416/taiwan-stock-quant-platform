# Phase X1R 审查与 Phase X2 Paper Apply / Reset 工作文档

生成日期：2026-06-18

## 1. X1R 审查结论

X1R 已通过。当前已具备只读能力：

```text
读取当前模拟持仓
读取 readonly model signal
读取 top50_exit_one_worst_sell 策略
生成 PaperPortfolioStateArtifact
生成 PaperOrderIntentArtifact
生成 PaperApplyPreviewArtifact
输出 forbidden_action_audit
```

X1R 已修复：

```text
unavailable sell 不释放仓位槽位
unavailable sell 不触发额外 buy slot
DB 路径只执行 SELECT
```

下一步可以进入 X2，但 X2 是 paper 写路径，必须单独冻结并实现安全边界。

## 2. Phase X2 目标

X2 只做：

```text
把 X1 生成的 PaperOrderIntentArtifact / PaperApplyPreviewArtifact
经用户确认后应用到模拟账户
并提供独立的模拟账户 reset 能力
```

X2 允许写：

```text
qd_tw_sim_accounts
qd_tw_sim_positions
qd_tw_sim_orders
qd_tw_sim_trades
qd_tw_sim_apply_runs
qd_tw_sim_reset_runs
qd_tw_sim_audit_log
data_tw/artifacts/paper_portfolio/**
```

X2 不允许写或触达：

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

## 3. 必须新增或冻结的后端接口

建议新增以下接口，命名必须包含 `paper` 或 `sim` 语义：

```text
GET  /api/tw-stock/paper-portfolio/state
GET  /api/tw-stock/paper-portfolio/apply-runs
POST /api/tw-stock/paper-portfolio/apply-decision
POST /api/tw-stock/paper-portfolio/reset
```

接口必须：

```text
login_required
user_id 隔离
只接受 qd_tw_sim_accounts.account_uid
返回 simulation_only=true
返回 trading.real_orders_enabled=false
返回 trading.connects_to_broker=false
```

不得复用前端可见的 quick-trade 命名。

## 4. Paper account epoch

X2 必须实现 epoch。允许两种方案：

### 4.1 推荐：表字段方案

新增：

```text
qd_tw_sim_accounts.paper_account_epoch INTEGER NOT NULL DEFAULT 1
qd_tw_sim_accounts.archived BOOLEAN NOT NULL DEFAULT FALSE
```

Reset 时：

```text
paper_account_epoch += 1
cash 恢复 initial_cash 或用户确认的 reset_initial_cash
positions 清空
open draft/cancelled 状态按规则归档或取消
```

### 4.2 备选：独立 artifact/table 方案

如果不改 `qd_tw_sim_accounts`，必须新增：

```text
qd_tw_sim_account_epochs
```

并能可靠映射：

```text
account_uid -> current_epoch
```

不得只靠前端状态推断 epoch。

## 5. 幂等存储

X2 必须新增 apply/reset 幂等存储。

### 5.1 Apply runs

建议表：

```text
qd_tw_sim_apply_runs(
  id,
  apply_id,
  decision_id,
  paper_account_id,
  user_id,
  paper_account_epoch,
  idempotency_key,
  input_checksum,
  status,
  already_applied,
  request_json,
  result_json,
  created_at,
  applied_at,
  UNIQUE(decision_id, paper_account_id, paper_account_epoch),
  UNIQUE(user_id, idempotency_key)
)
```

规则：

```text
同一个 decision_id + paper_account_id + paper_account_epoch 只能 apply 一次
重复 idempotency_key + 相同 input_checksum 返回原 result
重复 idempotency_key + 不同 input_checksum 拒绝
同一天多次 apply 默认拒绝，除非是同一 decision_id 幂等返回
旧 epoch 的 decision 不得 apply
```

### 5.2 Reset runs

建议表：

```text
qd_tw_sim_reset_runs(
  id,
  reset_id,
  paper_account_id,
  user_id,
  previous_epoch,
  new_epoch,
  idempotency_key,
  input_checksum,
  archive_snapshot_json,
  result_json,
  created_at,
  reset_at,
  UNIQUE(user_id, idempotency_key)
)
```

规则：

```text
reset 必须独立于 apply
reset 必须二次确认
reset 前必须 archive snapshot
reset 后旧 epoch decision 不可 apply
```

## 6. Apply 语义

`POST /api/tw-stock/paper-portfolio/apply-decision` 输入至少包含：

```text
paper_account_id
paper_account_epoch
decision_id
paper_order_intent artifact path or payload
input_checksum
idempotency_key
confirmed_by_user=true
confirm_text includes 模拟账户
```

Apply 必须验证：

```text
PaperOrderIntentArtifact.readonly_decision_only=true
not_real_order=true
not_target_position=true
not_investment_advice=true
model_id=e4_frozen_qlib_2023_2025_ltr
strategy_rule=top50_exit_one_worst_sell
paper_account_id matches current user
paper_account_epoch matches current epoch
input_checksum matches artifact
no unavailable action is executed
```

Apply 执行规则：

```text
只执行 applicability=applicable 的 paper_buy_intent / paper_sell_intent
unavailable action 进入 result skipped/rejected，不写成交
paper_skip 不写成交
卖出超过当前模拟持仓必须拒绝该 action
现金不足必须拒绝该 action
每个 action 生成 simulation execution 记录
```

## 7. Paper accounting policy

X2 必须沿用或显式冻结：

```text
fill_policy = paper_close_price_fill
price_source = qd_tw_stock_daily_bars latest valid close 或 artifact reference price，经 validator 确认
fee_rate = 0.001425
sell_tax_rate = 0.003
slippage_rate = 0
base_currency = TWD
market_scope = TWStock
cost_basis_policy = weighted_average
cash_insufficient_policy = reject action
oversell_policy = reject action
same_day_apply_policy = reject except idempotent replay
```

必须决定并记录：

```text
lot_size = 10 还是 1000
```

如果沿用当前 sim account 服务默认 `10`，前端必须显示这是模拟账户单位，不得误称为真实整股交易单位。

## 8. Reset 语义

`POST /api/tw-stock/paper-portfolio/reset` 输入至少包含：

```text
paper_account_id
current_epoch
idempotency_key
confirmed_by_user=true
confirm_text includes 重置模拟账户
reset_initial_cash optional
```

Reset 必须：

```text
读取当前 cash / positions / orders / trades
生成 archive snapshot
写 qd_tw_sim_reset_runs
写 qd_tw_sim_audit_log
递增 epoch
清空 positions
恢复 cash
阻止旧 epoch decision apply
```

Reset 不得：

```text
删除历史审计证据
影响 readonly latest
影响真实账户
触发 provider / monitor / broker / Agent
```

## 9. PaperAuditLogArtifact / audit table

X2 必须记录 paper audit log。

至少包含：

```text
event_id
event_type: apply_decision / reset_account / duplicate_replay / rejected
paper_account_id
paper_account_epoch
user_id
decision_id optional
apply_id optional
reset_id optional
idempotency_key
input_checksum
result_status
created_at
```

## 10. 前端最小要求

X2 可以先做 API 和后端测试；如果触及前端，必须满足：

```text
按钮文案包含“模拟”
应用和重置分离
应用前展示 preview
应用前二次确认
重置前二次确认并提示 archive
已应用后置灰或显示已应用
不可应用显示短原因
```

不得使用：

```text
真实交易
快速交易
下单
目标仓位
```

## 11. Network denylist 验收

如果 X2 触及前端或 API E2E，必须输出 network audit，验证：

允许 POST 仅限：

```text
/api/tw-stock/paper-portfolio/apply-decision
/api/tw-stock/paper-portfolio/reset
```

禁止任何请求命中：

```text
/api/agent/v1/quick-trade/**
/api/quick-trade/**
/api/broker/**
/api/order
/api/orders
/api/tw-stock/monitor/config
/api/tw-stock/monitor/scan
/api/tw-stock/monitor/alerts
/api/tw-stock/quant/ops/**
```

## 12. 必测场景

X2 必须补测试：

```text
apply happy path: sell/buy applicable 写入 paper-only tables
apply duplicate same idempotency_key returns existing result
apply duplicate decision_id rejected or returns already_applied
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

## 13. 必跑验证

至少运行：

```text
python -m py_compile <新增/修改的后端服务与脚本>
python -m pytest <新增/修改的 X2 tests> -q
```

如果新增前端入口，还必须运行对应 E2E / static check，并输出 network audit。

## 14. 交付物

X2 执行者必须提交：

```text
docs/tw_modular_daily_update_productization/PHASEX2_PAPER_APPLY_RESET_API_EXECUTION_REPORT_CN.md
```

报告必须包含：

```text
1. 新增/修改文件清单
2. 数据库迁移或 artifact 存储说明
3. apply/reset API 合同
4. 幂等规则实现证据
5. epoch/reset archive 实现证据
6. PaperAuditLog 实现证据
7. accounting policy 与 lot_size 口径
8. forbidden action audit
9. 测试结果
10. 是否可以进入 X3 前端 UX 的判断
```

## 15. 收口判断

X2 通过后，才能进入 X3 前端 UX 与 E2E。

X2 不要求完成前端完整体验；X2 的核心是：

```text
paper apply/reset 写路径安全、幂等、可审计、可复现。
```
