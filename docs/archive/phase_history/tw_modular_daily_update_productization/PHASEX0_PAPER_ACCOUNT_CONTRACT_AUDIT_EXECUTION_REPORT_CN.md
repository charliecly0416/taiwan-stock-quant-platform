# Phase X0 Paper Account 合同与安全边界审计执行报告

生成日期：2026-06-18

## 1. 执行范围与结论

本轮按 `PHASEX0_PAPER_PORTFOLIO_CONTRACT_AND_BOUNDARY_AUDIT_EXECUTION_REPORT_CN.md` 执行 X0：只做审计和合同冻结，不实现功能，不写账户，不 reset，不 apply 策略，不触发 daily update。

本轮未触发：

```text
真实 broker connection
quick-trade
真实 orders
paper/sim order 写入
paper/sim account reset
provider publish
provider accepted latest / qlib accepted latest switch
monitor config / scan / alerts writes
training / tuning / model replacement
Agent tool/action expansion
```

结论：

```text
可以进入 X1，但 X1 仅允许做 readonly PaperPortfolioStateArtifact / PaperOrderIntentArtifact / apply preview。
不得进入 X2 写接口，直到 paper_account_epoch、apply/reset 幂等表或 artifact、reset archive 规则完成实现并通过只写 sim/paper path 验证。
```

## 2. 已审计文件

按 X0 要求已读取：

```text
docs/tw_modular_daily_update_productization/PHASEX_REVIEW_AND_REVISION_SUGGESTION_CN.md
docs/tw_modular_daily_update_productization/PHASEX_PAPER_PORTFOLIO_STRATEGY_AND_SIMULATION_APP_WORK_CN.md
backend/app/routes/agent_v1/portfolio.py
backend/app/routes/agent_v1/quick_trade.py
backend/app/routes/agent_v1/admin.py
scripts/build_tw_daily_order_intent_artifact.py
scripts/run_tw_modular_daily_readonly_update.py
scripts/build_tw_modular_order_intent_artifact.py
configs/strategy_dependencies/top50_exit_one_worst_sell.yaml
```

补充读取：

```text
backend/app/services/tw_stock_sim_account.py
backend/app/routes/tw_stock.py
frontend/src/api/tw-stock.js
backend/app/utils/agent_auth.py
backend/app/utils/agent_jobs.py
backend/migrations/init.sql
backend/migrations/v3_1_0_agent_gateway.sql
docs/TW_STOCK_PRODUCT_ADAPTATION_AND_SIM_ACCOUNT_PLAN_CN.md
docs/TW_STOCK_PRODUCT_ADAPTATION_PHASE3_EXECUTION_CN.md
```

## 3. 现有 paper / sim account 来源

当前仓库存在两套“纸面 / 模拟”路径，Phase X 必须区分。

### 3.1 推荐作为 Phase X 主路径：TW stock sim account

现有实现：

```text
Service: backend/app/services/tw_stock_sim_account.py
Route:   backend/app/routes/tw_stock.py
Frontend API: frontend/src/api/tw-stock.js
Frontend page: frontend/src/views/tw-stock-sim-account/index.vue
```

现有表：

```text
qd_tw_sim_accounts
qd_tw_sim_positions
qd_tw_sim_orders
qd_tw_sim_trades
```

现有只读接口：

```text
GET /api/tw-stock/sim/accounts
GET /api/tw-stock/sim/accounts/:account_uid
GET /api/tw-stock/sim/accounts/:account_uid/positions
GET /api/tw-stock/sim/accounts/:account_uid/trades
```

现有模拟写接口：

```text
POST /api/tw-stock/sim/accounts
POST /api/tw-stock/sim/orders/draft
POST /api/tw-stock/sim/orders/:sim_order_uid/confirm
POST /api/tw-stock/sim/orders/:sim_order_uid/cancel
```

现有安全标志：

```text
simulation_only=true
trading.real_orders_enabled=false
trading.connects_to_broker=false
```

判断：这套路径已经具备账户、现金、持仓、草稿、确认模拟成交、成交记录、费用税费、持仓成本和安全标志，是 Phase X 接入“模拟账户策略”的合适底座。

### 3.2 不推荐作为 Phase X 新前端入口：Agent paper orders

现有实现：

```text
Route: backend/app/routes/agent_v1/portfolio.py
Route: backend/app/routes/agent_v1/quick_trade.py
Table: qd_agent_paper_orders
```

只读接口：

```text
GET /api/agent/v1/portfolio/paper-orders
GET /api/agent/v1/portfolio/paper-positions
GET /api/agent/v1/portfolio/paper-summary
```

写接口：

```text
POST /api/agent/v1/quick-trade/orders
POST /api/agent/v1/quick-trade/kill-switch
```

判断：

```text
qd_agent_paper_orders 可以作为历史 paper order 读取来源和审计参考。
但 /quick-trade/orders 命名、scope 和交易语义不适合作为 Phase X 新 paper apply 入口。
Phase X 新前端不得调用 quick-trade。
```

## 4. 当前 daily strategy 是否读取模拟持仓

当前 daily readonly order intent 不读取当前模拟账户持仓。

证据：

```text
scripts/build_tw_daily_order_intent_artifact.py
portfolio_state_source = u2_staging_empty_portfolio_state
```

现有 `scripts/build_tw_modular_order_intent_artifact.py` 可按 strategy rule 基于 portfolio state 生成 buy/sell/hold/skip，但读取的是：

```text
legacy_replay_snapshot_for_d1_sample_only
legacy_replay_snapshot_for_d2_initial_state_sample_only
```

而不是 `qd_tw_sim_positions` 或 `qd_agent_paper_orders`。

因此 X1 的核心工作必须是：

```text
读取 qd_tw_sim_accounts / qd_tw_sim_positions 当前状态
生成 PaperPortfolioStateArtifact
再用默认 model + top50_exit_one_worst_sell 生成 PaperOrderIntentArtifact
```

X1 仍必须 readonly，不写 `qd_tw_sim_orders`、`qd_tw_sim_trades`、`qd_tw_sim_positions`。

## 5. Paper account identity 合同

Phase X 统一使用以下身份字段：

```text
paper_account_id      = qd_tw_sim_accounts.account_uid
user_id               = 当前登录用户 id
tenant/session 口径   = user_id 隔离；Phase X 不引入跨 tenant 共享账户
paper_account_epoch   = 新增 epoch 字段或独立 epoch artifact，默认从 1 开始
initial_cash          = qd_tw_sim_accounts.initial_cash
base_currency         = qd_tw_sim_accounts.currency，固定 TWD
market_scope          = TWStock
```

当前缺口：

```text
qd_tw_sim_accounts 当前没有 paper_account_epoch / archived / reset lineage 字段。
qd_tw_sim_orders 当前没有 decision_id / apply_id / idempotency_key / input_checksum 字段。
qd_tw_sim_trades 当前没有 apply_id 字段。
```

X2 前必须补最小方案：

```text
qd_tw_sim_accounts.paper_account_epoch INTEGER NOT NULL DEFAULT 1
qd_tw_sim_accounts.archived BOOLEAN NOT NULL DEFAULT FALSE
qd_tw_sim_apply_runs 或等价 artifact/table
qd_tw_sim_account_resets 或等价 artifact/table
qd_tw_sim_audit_log 或等价 artifact/table
```

如果不改既有表，也必须新增独立 artifact/table 将 `account_uid -> current_epoch` 固定下来，不能只靠前端状态推断。

## 6. PaperPortfolioStateArtifact 合同草案

```json
{
  "artifact_type": "PaperPortfolioStateArtifact",
  "schema_version": "phase_x.paper_portfolio_state.v1",
  "paper_account_id": "tw_sim_xxx",
  "user_id": 1,
  "paper_account_epoch": 1,
  "asof": "YYYY-MM-DD",
  "market_scope": "TWStock",
  "base_currency": "TWD",
  "cash": 1000000.0,
  "initial_cash": 1000000.0,
  "market_value": 0.0,
  "total_equity": 1000000.0,
  "positions": [],
  "source": {
    "account_table": "qd_tw_sim_accounts",
    "position_table": "qd_tw_sim_positions",
    "price_table": "qd_tw_stock_daily_bars",
    "service": "TWStockSimAccountService.positions"
  },
  "readonly_state_only": true,
  "not_real_order": true,
  "created_at": "ISO-8601",
  "checksum": "sha256:..."
}
```

`positions` 至少包含：

```json
{
  "instrument": "TW2330",
  "symbol": "2330",
  "quantity": 1000,
  "avg_cost": 600.0,
  "cost_value": 600000.0,
  "last_price": 620.0,
  "price_date": "YYYY-MM-DD",
  "market_value": 620000.0,
  "unrealized_paper_pnl": 20000.0,
  "source": "qd_tw_sim_positions + qd_tw_stock_daily_bars"
}
```

## 7. PaperOrderIntentArtifact 合同草案

该 artifact 由 StrategyDecisionEngine 只读生成，不写账户。

```json
{
  "artifact_type": "PaperOrderIntentArtifact",
  "schema_version": "phase_x.paper_order_intent.v1",
  "decision_id": "paper_decision_...",
  "model_id": "e4_frozen_qlib_2023_2025_ltr",
  "strategy_rule": "top50_exit_one_worst_sell",
  "paper_account_id": "tw_sim_xxx",
  "user_id": 1,
  "paper_account_epoch": 1,
  "asof": "YYYY-MM-DD",
  "source_portfolio_state_artifact": "path-or-id",
  "source_model_signal_artifact": "path-or-id",
  "input_checksum": "sha256:...",
  "readonly_decision_only": true,
  "not_real_order": true,
  "not_target_position": true,
  "not_investment_advice": true,
  "actions": [],
  "reason": "generated from current paper holdings and readonly model signal",
  "created_at": "ISO-8601"
}
```

`actions` 只允许使用 paper 命名：

```json
{
  "action_type": "paper_buy_intent",
  "instrument": "TW2330",
  "symbol": "2330",
  "quantity": 1000,
  "reason": "top50_exit_one_worst_sell_buy",
  "candidate_rank": 1,
  "buy_score": 0.123,
  "estimated_reference_price": 620.0,
  "estimated_fee": 883.5,
  "estimated_tax": 0.0,
  "cash_effect_preview": -620883.5,
  "applicability": "applicable"
}
```

允许的 `action_type`：

```text
paper_buy_intent
paper_sell_intent
paper_skip
```

禁止字段名：

```text
order
target_position
target_weight
quick_trade
broker
```

## 8. Apply / Result / Snapshot / AuditLog 合同草案

### 8.1 PaperApplyRequestArtifact

```json
{
  "artifact_type": "PaperApplyRequestArtifact",
  "schema_version": "phase_x.paper_apply_request.v1",
  "apply_id": "paper_apply_...",
  "decision_id": "paper_decision_...",
  "idempotency_key": "client-generated-key",
  "input_checksum": "sha256:...",
  "paper_account_id": "tw_sim_xxx",
  "user_id": 1,
  "paper_account_epoch": 1,
  "confirmed_by_user": true,
  "confirm_text": "确认应用到模拟账户",
  "created_at": "ISO-8601"
}
```

### 8.2 PaperApplyResultArtifact

```json
{
  "artifact_type": "PaperApplyResultArtifact",
  "schema_version": "phase_x.paper_apply_result.v1",
  "apply_id": "paper_apply_...",
  "decision_id": "paper_decision_...",
  "idempotency_key": "client-generated-key",
  "input_checksum": "sha256:...",
  "paper_account_id": "tw_sim_xxx",
  "user_id": 1,
  "paper_account_epoch": 1,
  "already_applied": false,
  "status": "applied",
  "paper_executions": [],
  "cash_before": 1000000.0,
  "cash_after": 379116.5,
  "positions_before": [],
  "positions_after": [],
  "fee_and_tax": 883.5,
  "created_at": "ISO-8601",
  "applied_at": "ISO-8601"
}
```

`paper_executions` 映射到 `qd_tw_sim_orders / qd_tw_sim_trades`，但对外命名必须是 `paper_executions` 或 `simulation_executions`，不得叫真实订单。

### 8.3 PaperPositionSnapshotArtifact

```json
{
  "artifact_type": "PaperPositionSnapshotArtifact",
  "schema_version": "phase_x.paper_position_snapshot.v1",
  "snapshot_id": "paper_snapshot_...",
  "paper_account_id": "tw_sim_xxx",
  "paper_account_epoch": 1,
  "source_apply_id": "paper_apply_...",
  "asof": "YYYY-MM-DD",
  "cash": 379116.5,
  "market_value": 620000.0,
  "total_equity": 999116.5,
  "positions": [],
  "realized_paper_pnl": 0.0,
  "fee_and_tax": 883.5,
  "created_at": "ISO-8601",
  "checksum": "sha256:..."
}
```

### 8.4 PaperAuditLogArtifact

```json
{
  "artifact_type": "PaperAuditLogArtifact",
  "schema_version": "phase_x.paper_audit_log.v1",
  "event_id": "paper_audit_...",
  "event_type": "apply_decision",
  "paper_account_id": "tw_sim_xxx",
  "paper_account_epoch": 1,
  "user_id": 1,
  "decision_id": "paper_decision_...",
  "apply_id": "paper_apply_...",
  "idempotency_key": "client-generated-key",
  "input_checksum": "sha256:...",
  "result_status": "applied",
  "created_at": "ISO-8601"
}
```

## 9. Reset archive / epoch 合同草案

Reset 必须独立于 apply。

```json
{
  "artifact_type": "PaperAccountResetArtifact",
  "schema_version": "phase_x.paper_account_reset.v1",
  "reset_id": "paper_reset_...",
  "idempotency_key": "client-generated-key",
  "paper_account_id": "tw_sim_xxx",
  "user_id": 1,
  "previous_epoch": 1,
  "new_epoch": 2,
  "archive_snapshot": {
    "snapshot_id": "paper_archive_snapshot_...",
    "cash": 379116.5,
    "positions": [],
    "open_orders_or_drafts": [],
    "trades": [],
    "checksum": "sha256:..."
  },
  "initial_cash": 1000000.0,
  "base_currency": "TWD",
  "market_scope": "TWStock",
  "confirmed_by_user": true,
  "created_at": "ISO-8601"
}
```

规则：

```text
reset 前必须生成 archive snapshot。
reset 需要用户二次确认。
reset 后 paper_account_epoch + 1。
reset 后旧 epoch 的 decision_id 不得 apply。
reset 不影响 readonly latest。
reset 不影响 provider / qlib accepted latest。
reset 不影响真实账户。
reset 写 PaperAuditLogArtifact。
```

X2 最小实现建议：

```text
保留同一个 paper_account_id/account_uid，递增 paper_account_epoch。
旧 epoch 的 positions/orders/trades 通过 archive snapshot 冻结。
新 epoch cash/positions 按 initial_cash 和空持仓重建。
```

如果选择创建新 `account_uid`，也必须用 reset artifact 记录 old_account_uid、new_account_uid、previous_epoch、new_epoch 的 lineage。

## 10. 幂等规则

冻结规则：

```text
同一个 decision_id + paper_account_id + paper_account_epoch 只能 apply 一次。
重复 idempotency_key + 相同 input_checksum 返回已有 PaperApplyResultArtifact，already_applied=true。
重复 idempotency_key + 不同 input_checksum 必须拒绝。
同一天多次 apply 默认拒绝，除非是同一 decision_id 的幂等返回。
reset 使用独立 reset_id / idempotency_key。
reset 后旧 epoch 的 decision_id 不得再 apply。
apply 与 reset 的 idempotency namespace 必须分离。
```

当前既有 `with_idempotency(kind)` 只查询 `qd_agent_jobs`，主要服务 Agent async jobs；`quick_trade` 同步写入没有完整 `input_checksum` 持久化与 result replay 语义。Phase X 不应直接复用该实现作为 apply 幂等。

X2 最小表建议：

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

reset 独立：

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

## 11. Paper accounting policy

Phase X 冻结以下最低可复现口径，优先沿用 `TWStockSimAccountService`：

```text
fill_policy = paper_close_price_fill
price_source = qd_tw_stock_daily_bars latest valid close；X1 preview 可显式标记 price_date
fee_rate = 0.001425
sell_tax_rate = 0.003
slippage_rate = 0
base_currency = TWD
market_scope = TWStock
lot_size = 当前服务默认 10；X2 前必须决定是否改为台股整股 1000 或继续支持零股模拟
cash_insufficient_policy = reject
oversell_policy = reject
cost_basis_policy = weighted_average
same_day_apply_policy = reject except idempotent replay of same decision_id
equity_calculation_policy = cash + sum(quantity * latest valid close)
```

当前服务字段映射：

```text
cash                      -> qd_tw_sim_accounts.cash
initial_cash              -> qd_tw_sim_accounts.initial_cash
position quantity         -> qd_tw_sim_positions.quantity
avg_cost                  -> qd_tw_sim_positions.avg_cost
position_cost             -> qd_tw_sim_positions.cost_value
paper draft/fill          -> qd_tw_sim_orders
paper execution/fill      -> qd_tw_sim_trades
fee                       -> qd_tw_sim_orders.fee / qd_tw_sim_trades.fee
tax                       -> qd_tw_sim_orders.tax / qd_tw_sim_trades.tax
market_value              -> derived from qd_tw_stock_daily_bars close
unrealized_paper_pnl      -> market_value - cost_value
```

缺口：

```text
realized_paper_pnl 当前未在 qd_tw_sim_trades 或 positions 中显式累计。
same-day apply guard 当前不存在。
strategy batch apply 当前不存在。
epoch/reset archive 当前不存在。
```

## 12. API allowlist / denylist

### 12.1 X1 只读 allowlist

```text
GET /api/tw-stock/sim/accounts
GET /api/tw-stock/sim/accounts/:account_uid
GET /api/tw-stock/sim/accounts/:account_uid/positions
GET /api/tw-stock/sim/accounts/:account_uid/trades
GET /api/tw-stock/readonly-daily/latest 或既有 readonly daily latest 读取入口
```

X1 可新增只读候选：

```text
GET /api/tw-stock/paper-portfolio/state
GET /api/tw-stock/paper-portfolio/apply-preview
```

### 12.2 X2 写入 allowlist

仅允许新增 paper/sim 命名接口：

```text
POST /api/tw-stock/paper-portfolio/apply-decision
POST /api/tw-stock/paper-portfolio/reset
GET  /api/tw-stock/paper-portfolio/apply-runs
```

底层只允许写：

```text
qd_tw_sim_accounts
qd_tw_sim_positions
qd_tw_sim_orders
qd_tw_sim_trades
qd_tw_sim_apply_runs
qd_tw_sim_reset_runs
qd_tw_sim_audit_log
data_tw/artifacts/paper_portfolio/** 或等价 paper-only artifact path
```

### 12.3 denylist

Phase X 不得触达：

```text
/api/agent/v1/quick-trade/**
/api/quick-trade/**
/api/broker/**
/api/order
/api/orders
real broker clients: ibkr / alpaca / mt5
/api/tw-stock/monitor/config
/api/tw-stock/monitor/scan
/api/tw-stock/monitor/scan-all
/api/tw-stock/monitor/alerts POST/PUT
/api/tw-stock/quant/ops/**
provider publish
provider accepted latest switch
qlib accepted latest switch
Agent prompt/tool/action
training / tuning / model replacement
```

如果历史 `qd_agent_paper_orders` 需要读取，只允许作为 read-only historical paper source，不作为 Phase X apply 写入目标。

## 13. 前端 apply/reset 文案合同

X3 前端必须展示三层：

```text
当前模拟持仓
本次策略建议
应用后的模拟账户变化预览
```

允许按钮文案：

```text
应用到模拟账户
确认应用到模拟账户
取消模拟应用
重置模拟账户
确认重置模拟账户
刷新模拟账户
```

确认弹窗必须包含：

```text
仅模拟账户
不连接券商
不提交真实订单
不构成投资建议
reset 前将归档当前模拟账户状态
```

禁止文案：

```text
真实交易
快速交易
下单
目标仓位
买入/卖出按钮单独作为真实动作语义
```

状态展示：

```text
已应用：按钮置灰，显示“已应用到模拟账户”
不可应用：显示短原因，如“旧 epoch 决策不可应用”“现金不足”“卖出超过模拟持仓”“价格不可用”
重复点击：显示“该策略建议已应用，已返回原模拟结果”
reset 后：显示“已开启新的模拟账户 epoch”
```

## 14. 是否可以进入 X1

可以进入 X1，条件如下：

```text
X1 只读。
X1 使用 qd_tw_sim_accounts / qd_tw_sim_positions 作为当前模拟账户来源。
X1 生成 PaperPortfolioStateArtifact / PaperOrderIntentArtifact / apply preview。
X1 不写 qd_tw_sim_orders / qd_tw_sim_trades / qd_tw_sim_positions。
X1 不调用 /quick-trade/orders。
X1 不触发 provider/latest/monitor/broker/Agent/training。
```

不得进入 X2，直到以下缺口补齐：

```text
paper_account_epoch 实现方案
apply_runs 幂等存储
reset_runs 与 archive snapshot 存储
PaperAuditLogArtifact 存储
same-day apply guard
realized_paper_pnl 口径
lot_size 最终口径
X2 API network denylist 验证
```

## 15. X1 执行建议

X1 最小闭环：

```text
1. 新增只读 builder/service，读取一个 qd_tw_sim_accounts.account_uid。
2. 输出 PaperPortfolioStateArtifact。
3. 读取 readonly latest/default model signal 与 top50_exit_one_worst_sell.yaml。
4. 基于当前模拟持仓生成 paper_buy_intent / paper_sell_intent / paper_skip。
5. 生成 apply preview，但只计算现金/费用/税费/持仓变化预览。
6. 输出 forbidden_action_audit，证明无 write path、无 quick-trade、无 broker、无 monitor、无 provider latest。
```

X1 完成后再审查是否进入 X2。
